// Scene + player build for the waterworks test project.
//   Unity -batchmode -projectPath tools/qingxi-waterworks-b/unity -executeMethod Qingxi.Waterworks.EditorTools.BuildTools.BuildWindows -quit
// Syncs the kit from art/exports, (re)creates Assets/Scenes/Waterworks.unity and builds Builds/Win64/QingxiWaterworks.exe.
using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace Qingxi.Waterworks.EditorTools
{
    public static class BuildTools
    {
        public const string ScenePath = "Assets/Scenes/Waterworks.unity", MatDir = "Assets/Waterworks/Materials";

        static Material Mat(string name, Color c, string shader = "Standard", float gloss = 0.15f)
        {
            Directory.CreateDirectory(MatDir); var path = $"{MatDir}/{name}.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m == null) { m = new Material(Shader.Find(shader)); AssetDatabase.CreateAsset(m, path); }
            m.shader = Shader.Find(shader); m.color = c; if (m.HasProperty("_Glossiness")) m.SetFloat("_Glossiness", gloss);
            EditorUtility.SetDirty(m); return m;
        }

        static void Transparent(Material m)                                                                  // Standard shader, Rendering Mode = Transparent
        {
            m.SetFloat("_Mode", 3); m.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.One); m.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
            m.SetInt("_ZWrite", 0); m.DisableKeyword("_ALPHATEST_ON"); m.DisableKeyword("_ALPHABLEND_ON"); m.EnableKeyword("_ALPHAPREMULTIPLY_ON");
            m.renderQueue = (int)UnityEngine.Rendering.RenderQueue.Transparent; EditorUtility.SetDirty(m);
        }

        [MenuItem("Waterworks/Make Scene")]
        public static void MakeScene()
        {
            KitSync.Sync();
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var cam = new GameObject("Main Camera", typeof(Camera), typeof(AudioListener)).GetComponent<Camera>(); cam.tag = "MainCamera";
            cam.clearFlags = CameraClearFlags.SolidColor; cam.backgroundColor = new Color(0.62f, 0.70f, 0.76f); cam.fieldOfView = 45; cam.nearClipPlane = 0.05f; cam.farClipPlane = 200;
            var sun = new GameObject("Sun", typeof(Light)).GetComponent<Light>(); sun.type = LightType.Directional; sun.intensity = 1.15f; sun.shadows = LightShadows.Soft;
            sun.transform.rotation = Quaternion.Euler(48, -35, 0); sun.color = new Color(1, 0.96f, 0.88f);
            var g = new GameObject("Waterworks").AddComponent<WaterworksGame>();
            g.ground = Mat("ww_ground", new Color(0.36f, 0.40f, 0.25f)); g.creek = Mat("ww_creek", new Color(0.16f, 0.42f, 0.55f), gloss: 0.8f);
            g.soil = Mat("ww_soil", new Color(0.36f, 0.25f, 0.16f)); g.crop = Mat("ww_crop", new Color(0.36f, 0.60f, 0.22f));
            g.rock = Mat("ww_rock", new Color(0.46f, 0.46f, 0.43f)); g.grass = Mat("ww_grass", new Color(0.22f, 0.42f, 0.16f));
            g.sand = Mat("ww_sand", new Color(0.70f, 0.60f, 0.40f)); g.oldBed = Mat("ww_oldbed", new Color(0.30f, 0.29f, 0.27f));
            g.fleck = Mat("ww_fleck", new Color(0.45f, 0.75f, 1.0f), "Unlit/Color"); g.spray = Mat("ww_spray", new Color(0.85f, 0.95f, 1.0f), "Unlit/Color");
            g.water = Mat("ww_water", new Color(0.20f, 0.46f, 0.52f, 0.62f), gloss: 0.92f); Transparent(g.water);
            Directory.CreateDirectory(Path.GetDirectoryName(ScenePath));
            EditorSceneManager.SaveScene(scene, ScenePath); AssetDatabase.SaveAssets();
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
            Debug.Log($"[Waterworks] scene written: {ScenePath}");
        }

        [MenuItem("Waterworks/Build Windows Player")]
        public static void BuildWindows()
        {
            MakeScene();
            PlayerSettings.companyName = "YunJing"; PlayerSettings.productName = "Qingxi Waterworks B Test";
            PlayerSettings.fullScreenMode = FullScreenMode.Windowed; PlayerSettings.defaultScreenWidth = 1600; PlayerSettings.defaultScreenHeight = 900;
            PlayerSettings.resizableWindow = true; PlayerSettings.runInBackground = true;
            PlayerSettings.defaultInterfaceOrientation = UIOrientation.AutoRotation;                     // landscape only on touch devices
            PlayerSettings.allowedAutorotateToPortrait = false; PlayerSettings.allowedAutorotateToPortraitUpsideDown = false;
            PlayerSettings.allowedAutorotateToLandscapeLeft = true; PlayerSettings.allowedAutorotateToLandscapeRight = true;
            var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = new[] { ScenePath }, locationPathName = "Builds/Win64/QingxiWaterworks.exe", target = BuildTarget.StandaloneWindows64, options = BuildOptions.None,
            });
            Debug.Log($"[Waterworks] build {report.summary.result}: {report.summary.outputPath} ({report.summary.totalSize / 1048576f:0.0} MB, {report.summary.totalErrors} errors)");
            if (Application.isBatchMode && report.summary.result != BuildResult.Succeeded) EditorApplication.Exit(1);
        }
    }
}
