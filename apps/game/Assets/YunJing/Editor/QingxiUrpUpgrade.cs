using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace YunJing.Editor
{
    // The YunJing scenes (ProjectBuilder, joshsu54's alchemy room) render with URP, and the novice village links
    // into the alchemy room, so it uses the same project URP asset. FBX files first imported under the built-in
    // pipeline still carry Standard materials; those get URP Lit copies (source files unchanged).
    public static class QingxiUrpUpgrade
    {
        const string Root = "Assets/YunJing/Generated";   // same assets ProjectBuilder creates
        const string Converted = "Assets/QingxiWorld/Generated/Materials/URP";

        public static UniversalRenderPipelineAsset EnsurePipeline()
        {
            Directory.CreateDirectory(Root);
            var renderer = AssetDatabase.LoadAssetAtPath<UniversalRendererData>(Root + "/Renderer.asset");
            if (renderer == null) { renderer = ScriptableObject.CreateInstance<UniversalRendererData>(); AssetDatabase.CreateAsset(renderer, Root + "/Renderer.asset"); }
            var pipeline = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(Root + "/URP.asset");
            if (pipeline == null)
            {
                pipeline = UniversalRenderPipelineAsset.Create(renderer); AssetDatabase.CreateAsset(pipeline, Root + "/URP.asset");
                pipeline.renderScale = 1; pipeline.shadowDistance = 35;
            }
            // Soft shadows and two cascades: a single hard 2048 map stair-stepped every shadow near the camera.
            var so = new SerializedObject(pipeline);
            so.FindProperty("m_SoftShadowsSupported").boolValue = true;
            so.FindProperty("m_SoftShadowQuality").intValue = 2;   // medium
            so.FindProperty("m_ShadowCascadeCount").intValue = 2;
            so.FindProperty("m_MainLightShadowmapResolution").intValue = 2048;
            so.ApplyModifiedPropertiesWithoutUndo();
            GraphicsSettings.defaultRenderPipeline = pipeline; QualitySettings.renderPipeline = pipeline;
            AssetDatabase.SaveAssets();
            return pipeline;
        }

        public static int UpgradeSceneMaterials()
        {
            Directory.CreateDirectory(Converted);
            var lit = Shader.Find("Universal Render Pipeline/Lit");
            var cache = new Dictionary<Material, Material>();
            int swapped = 0;
            foreach (var renderer in Object.FindObjectsByType<Renderer>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                var materials = renderer.sharedMaterials;
                bool changed = false;
                for (int i = 0; i < materials.Length; i++)
                {
                    var source = materials[i];
                    if (source == null || !BuiltIn(source.shader)) continue;
                    if (!cache.TryGetValue(source, out var copy)) cache[source] = copy = Convert(source, lit);
                    materials[i] = copy; changed = true; swapped++;
                }
                if (changed) renderer.sharedMaterials = materials;
            }
            AssetDatabase.SaveAssets();
            Debug.Log($"QINGXI_URP_UPGRADE: {cache.Count} built-in materials converted, {swapped} renderer slots updated");
            return cache.Count;
        }

        static bool BuiltIn(Shader shader) => shader != null && (shader.name == "Standard" || shader.name == "Standard (Specular setup)" ||
            shader.name.StartsWith("Legacy Shaders/") || shader.name == "Hidden/InternalErrorShader");

        static Material Convert(Material source, Shader lit)
        {
            var sourcePath = AssetDatabase.GetAssetPath(source);
            var key = (string.IsNullOrEmpty(sourcePath) ? "scene" : Path.GetFileNameWithoutExtension(sourcePath)) + "_" + source.name;
            var path = $"{Converted}/{string.Concat(key.Select(c => char.IsLetterOrDigit(c) || c == '_' || c == '-' ? c : '_'))}.mat";
            var copy = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (copy == null) { copy = new Material(lit); AssetDatabase.CreateAsset(copy, path); }
            copy.shader = lit;
            var color = source.HasProperty("_Color") ? source.color : Color.white;
            copy.SetColor("_BaseColor", color);
            if (source.HasProperty("_MainTex") && source.mainTexture != null)
            {
                copy.SetTexture("_BaseMap", source.mainTexture);
                copy.SetTextureScale("_BaseMap", source.mainTextureScale); copy.SetTextureOffset("_BaseMap", source.mainTextureOffset);
            }
            if (source.HasProperty("_BumpMap") && source.GetTexture("_BumpMap") != null) { copy.SetTexture("_BumpMap", source.GetTexture("_BumpMap")); copy.EnableKeyword("_NORMALMAP"); }
            copy.SetFloat("_Metallic", source.HasProperty("_Metallic") ? source.GetFloat("_Metallic") : 0);
            // URP highlights read stronger than built-in Standard at the same gloss; keep the town matte.
            copy.SetFloat("_Smoothness", Mathf.Min(.25f, source.HasProperty("_Glossiness") ? source.GetFloat("_Glossiness") : .2f));
            if (source.IsKeywordEnabled("_EMISSION") && source.HasProperty("_EmissionColor"))
            {
                copy.SetColor("_EmissionColor", source.GetColor("_EmissionColor")); copy.EnableKeyword("_EMISSION");
            }
            bool transparent = (source.HasProperty("_Mode") && source.GetFloat("_Mode") >= 2) || color.a < .99f;
            copy.SetFloat("_Surface", transparent ? 1 : 0);
            copy.SetFloat("_ZWrite", transparent ? 0 : 1);
            copy.SetFloat("_SrcBlend", (float)(transparent ? BlendMode.SrcAlpha : BlendMode.One));
            copy.SetFloat("_DstBlend", (float)(transparent ? BlendMode.OneMinusSrcAlpha : BlendMode.Zero));
            if (transparent) copy.EnableKeyword("_SURFACE_TYPE_TRANSPARENT"); else copy.DisableKeyword("_SURFACE_TYPE_TRANSPARENT");
            copy.renderQueue = transparent ? (int)RenderQueue.Transparent : -1;
            EditorUtility.SetDirty(copy);
            return copy;
        }
    }
}
