using System;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace YunJing.Editor
{
    // Meadow ground cover (tools/art/build_ground_kit_v1.py, art/exports/qingxi-ground-v1): lush, tall and dry grass
    // clumps and white, yellow and blue flowers, drawn as instanced terrain details with YunJing/QingxiGrass
    // (vertex-coloured blades, wind toward the tip, backlit tips). Copied into a gitignored model folder.
    public static class QingxiGroundKit
    {
        const string Models = "Assets/YunJing/Models/QingxiGroundV1";   // copied from art/exports, gitignored
        const string MaterialFolder = "Assets/QingxiWorld/Generated/Materials/Ground";

        /// <summary>Detail layers in order; the terrain fills them by index. Height (m) drives the shader's wind.</summary>
        public static readonly (string name, float height, float wind)[] Kinds =
        {
            ("GrassLush", .3f, .05f), ("GrassTall", .48f, .08f), ("GrassDry", .26f, .05f),
            ("FlowerWhite", .3f, .04f), ("FlowerYellow", .3f, .04f), ("FlowerBlue", .3f, .04f),
            ("Pebbles", .2f, 0f), ("StonesMossy", .4f, 0f),
        };

        static bool copied;

        public static DetailPrototype[] Prototypes()
        {
            if (!copied) { Copy(); copied = true; }
            var result = new DetailPrototype[Kinds.Length];
            for (int i = 0; i < Kinds.Length; i++)
            {
                var model = AssetDatabase.LoadAssetAtPath<GameObject>($"{Models}/{Kinds[i].name}.fbx");
                if (model == null) throw new FileNotFoundException("Ground kit clump missing (Git LFS pulled?)", Kinds[i].name);
                result[i] = new DetailPrototype
                {
                    prototype = model, usePrototypeMesh = true, renderMode = DetailRenderMode.VertexLit, useInstancing = true,
                    minWidth = .8f, maxWidth = 1.3f, minHeight = .8f, maxHeight = 1.3f, healthyColor = Color.white, dryColor = Color.white,
                };
            }
            return result;
        }

        // Stones: lit like the boulders (warm grey, matte), not with the grass shader's soft upward light.
        static Material Stone()
        {
            var path = $"{MaterialFolder}/GroundStone_URP.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null) { mat = new Material(Shader.Find("Universal Render Pipeline/Lit")); AssetDatabase.CreateAsset(mat, path); }
            mat.SetColor("_BaseColor", new Color(.38f, .37f, .33f)); mat.SetFloat("_Smoothness", .05f); mat.enableInstancing = true;
            EditorUtility.SetDirty(mat);
            return mat;
        }

        static void Copy()
        {
            string repo = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", ".."));
            string src = Path.Combine(repo, "art/exports/qingxi-ground-v1"), dst = Path.Combine(repo, "apps/game", Models);
            Directory.CreateDirectory(dst);
            foreach (var file in Directory.GetFiles(src, "*.fbx"))
            {
                if (new FileInfo(file).Length < 200) throw new InvalidOperationException("Git LFS pointer instead of asset; run git lfs pull: " + file);
                var target = Path.Combine(dst, Path.GetFileName(file));
                if (!File.Exists(target) || new FileInfo(target).Length != new FileInfo(file).Length) File.Copy(file, target, true);
            }
            AssetDatabase.Refresh();
            Directory.CreateDirectory(Path.Combine(repo, "apps/game", MaterialFolder));
            var shader = Shader.Find("YunJing/QingxiGrass");
            if (shader == null) throw new InvalidOperationException("YunJing/QingxiGrass shader missing");
            foreach (var (name, height, wind) in Kinds)
            {
                var path = $"{MaterialFolder}/{name}_Grass.mat";
                var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (mat == null) { mat = new Material(shader); AssetDatabase.CreateAsset(mat, path); }
                mat.shader = shader; mat.enableInstancing = true;
                mat.SetFloat("_Height", height); mat.SetFloat("_Wind", wind); mat.SetColor("_Tint", Color.white);
                // The meadow turf's colour (QingxiVillageTerrain layer 0, or the sun-dried layer for dry grass).
                mat.SetColor("_Ground", name == "GrassDry" ? new Color(.5f, .52f, .28f) : name.StartsWith("Pebbles") || name.StartsWith("Stones") ? new Color(.42f, .4f, .36f) : new Color(.32f, .5f, .22f));
                EditorUtility.SetDirty(mat);
                var importer = (ModelImporter)AssetImporter.GetAtPath($"{Models}/{name}.fbx");
                importer.bakeAxisConversion = true; importer.importAnimation = false; importer.importCameras = false; importer.importLights = false;
                importer.importNormals = ModelImporterNormals.Import;
                importer.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
                importer.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), "QingxiGrass"), mat);
                importer.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), "QingxiStone"), Stone());
                importer.SaveAndReimport();
            }
            AssetDatabase.SaveAssets();
        }
    }
}
