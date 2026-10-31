using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using YunJing.Tea;

namespace YunJing.Editor
{
    // Small playable room for work pack B's home tea brewing: joshsu54's TI09 tea stove (art/exports/tea-brewing-b),
    // the tea panel and the scripted playtest. The same panel is wired to TI_TeaStove in QingxiLodgingInteriorBuilder.
    public static class TeaRoomBuilder
    {
        const string Scene = "Assets/YunJing/Generated/TeaRoom.unity";
        const string Models = "Assets/YunJing/Models/TeaBrewingB";   // copied from art/exports/tea-brewing-b, gitignored
        static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", ".."));

        [Serializable] class Fixture { public Case[] cases; }
        [Serializable] class Case { public string name, tea, result; public int scoops, score; public double strength, brewTemp; public TeaEvent[] log; }

        static void CopyStove()
        {
            var src = Path.Combine(Repo, "art", "exports", "tea-brewing-b", "TI09_TeaStove", "v001");
            var dst = Path.Combine(Repo, "apps", "game", Models);
            Directory.CreateDirectory(Path.Combine(dst, "Textures"));
            File.Copy(Path.Combine(src, "TI09_TeaStove_v001.fbx"), Path.Combine(dst, "TI09_TeaStove_v001.fbx"), true);
            foreach (var tex in Directory.GetFiles(Path.Combine(src, "Textures"), "*.png")) File.Copy(tex, Path.Combine(dst, "Textures", Path.GetFileName(tex)), true);
            AssetDatabase.Refresh();
            var normal = (TextureImporter)AssetImporter.GetAtPath($"{Models}/Textures/TI09_TeaStove_Normal.png");
            if (normal.textureType != TextureImporterType.NormalMap) { normal.textureType = TextureImporterType.NormalMap; normal.SaveAndReimport(); }
            foreach (var linear in new[] { "MetallicSmoothness", "Roughness", "Metallic" })
            {
                var imp = (TextureImporter)AssetImporter.GetAtPath($"{Models}/Textures/TI09_TeaStove_{linear}.png");
                if (imp.sRGBTexture) { imp.sRGBTexture = false; imp.SaveAndReimport(); }
            }
        }

        static Material StoveMaterial()
        {
            var path = $"{Models}/TI09_TeaStove_Lit.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m == null) { m = new Material(Shader.Find("Universal Render Pipeline/Lit")); AssetDatabase.CreateAsset(m, path); }
            Texture2D T(string slot) => AssetDatabase.LoadAssetAtPath<Texture2D>($"{Models}/Textures/TI09_TeaStove_{slot}.png");
            m.SetTexture("_BaseMap", T("BaseColor")); m.SetColor("_BaseColor", Color.white);
            m.SetTexture("_BumpMap", T("Normal")); m.EnableKeyword("_NORMALMAP");
            m.SetTexture("_MetallicGlossMap", T("MetallicSmoothness")); m.EnableKeyword("_METALLICSPECGLOSSMAP"); m.SetFloat("_Smoothness", 1);
            m.SetTexture("_EmissionMap", T("Emission")); m.SetColor("_EmissionColor", Color.white * 1.2f); m.EnableKeyword("_EMISSION");
            m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
            EditorUtility.SetDirty(m); return m;
        }

        static Material Plain(string name, Color c)
        {
            var m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = name }; m.SetColor("_BaseColor", c); m.SetFloat("_Smoothness", .15f); return m;
        }

        [MenuItem("Yun Jing/Generate tea room")]
        public static void Generate()
        {
            QingxiUrpUpgrade.EnsurePipeline();
            CopyStove();
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var room = new GameObject("TeaRoom").transform;
            var floor = GameObject.CreatePrimitive(PrimitiveType.Cube); floor.name = "Floor"; floor.transform.SetParent(room);
            floor.transform.localScale = new Vector3(6, .1f, 6); floor.transform.position = new Vector3(0, -.05f, 0);
            floor.GetComponent<Renderer>().sharedMaterial = Plain("Floor_Wood", new Color(.36f, .25f, .16f));
            var wall = GameObject.CreatePrimitive(PrimitiveType.Cube); wall.name = "BackWall"; wall.transform.SetParent(room);
            wall.transform.localScale = new Vector3(6, 3, .1f); wall.transform.position = new Vector3(0, 1.5f, 1.2f);
            wall.GetComponent<Renderer>().sharedMaterial = Plain("Wall_Plaster", new Color(.78f, .72f, .6f));

            var source = AssetDatabase.LoadAssetAtPath<GameObject>($"{Models}/TI09_TeaStove_v001.fbx");
            if (source == null) throw new FileNotFoundException("TI09 tea stove missing (Git LFS pulled?)", Models);
            var stove = (GameObject)PrefabUtility.InstantiatePrefab(source); stove.name = "TI09_TeaStove - joshsu54"; stove.transform.SetParent(room, false);
            stove.transform.localRotation = Quaternion.Euler(0, 180, 0) * source.transform.localRotation;   // FBX front (-Y in Blender) lands on +Z; face the camera
            var mat = StoveMaterial();
            foreach (var r in stove.GetComponentsInChildren<Renderer>()) r.sharedMaterials = Enumerable.Repeat(mat, r.sharedMaterials.Length).ToArray();
            // LOD1/LOD2 and the collision proxy stay hidden in this close-up room.
            foreach (var t in stove.GetComponentsInChildren<Transform>(true))
                if (t.name.Contains("_LOD1") || t.name.Contains("_LOD2") || t.name.EndsWith("_Collision")) t.gameObject.SetActive(false);
            var spout = stove.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name.StartsWith("SOCKET_steam"));

            var sun = new GameObject("Sun").AddComponent<Light>(); sun.type = LightType.Directional; sun.intensity = 1.1f; sun.color = new Color(1, .95f, .86f);
            sun.transform.rotation = Quaternion.Euler(40, -30, 0); sun.shadows = LightShadows.Soft;
            var fire = new GameObject("FireGlow").AddComponent<Light>(); fire.type = LightType.Point; fire.range = .9f; fire.intensity = .25f; fire.color = new Color(1, .55f, .2f); fire.shadows = LightShadows.None;
            fire.transform.position = new Vector3(0, .24f, -.42f);   // just outside the firebox mouth
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat; RenderSettings.ambientLight = new Color(.42f, .4f, .38f);

            var cam = new GameObject("Main Camera").AddComponent<Camera>(); cam.tag = "MainCamera";
            cam.clearFlags = CameraClearFlags.SolidColor; cam.backgroundColor = new Color(.2f, .21f, .22f); cam.fieldOfView = 40;
            cam.transform.position = new Vector3(.75f, 1.05f, -1.75f); cam.transform.LookAt(new Vector3(.38f, .5f, 0));

            var holder = new GameObject("TeaStove_Station");
            var panel = holder.AddComponent<TeaBrewingPanel>();
            panel.stove = spout != null ? spout : stove.transform; panel.spoutHeight = spout != null ? 0 : .82f;
            holder.AddComponent<TeaPlaytest>();

            Directory.CreateDirectory(Path.GetDirectoryName(Path.Combine(Repo, "apps", "game", Scene)));
            EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(), Scene);
            AssetDatabase.SaveAssets();
            Debug.Log($"TEA_ROOM_GENERATED {Scene} spout={(spout != null ? spout.name : "none")}");
        }

        /// <summary>Replays tests/fixtures/tea-trace.json (written from services/api/src/tea.ts) through TeaPot.</summary>
        public static void VerifySim()
        {
            var fx = JsonUtility.FromJson<Fixture>(File.ReadAllText(Path.Combine(Repo, "tests", "fixtures", "tea-trace.json")));
            int pass = 0;
            foreach (var c in fx.cases)
            {
                var pot = new TeaPot(TeaContent.teas.First(t => t.id == c.tea), c.scoops); TeaJudgement j = null;
                int e = 0, end = c.log[c.log.Length - 1].t;
                for (int tick = 0; tick <= end; tick++)
                {
                    while (e < c.log.Length && c.log[e].t == tick)
                    {
                        var ev = c.log[e++];
                        if (ev.k == "fire") pot.SetFire(ev.v); else if (ev.k == "leaves") pot.AddLeaves(); else if (ev.k == "pour") j = pot.Pour();
                    }
                    if (tick < end) pot.Step();
                }
                bool ok = j != null && j.result == c.result && j.score == c.score && Math.Abs(j.strength - c.strength) < 1e-4 && Math.Abs(j.brewTemp - c.brewTemp) < 1e-6;
                if (!ok) throw new Exception($"TEA_SIM_MISMATCH {c.name}: C# {j?.result} {j?.score} {j?.strength} {j?.brewTemp} vs TS {c.result} {c.score} {c.strength} {c.brewTemp}");
                pass++;
            }
            Debug.Log($"TEA_SIM_PASS {pass}/{fx.cases.Length}");
        }

        public static void Verify() { Generate(); VerifySim(); }

        public static void BuildWindows()
        {
            Generate(); VerifySim();
            var path = Path.Combine(Repo, "artifacts", "tea-windows", "YunJingTea.exe");
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            var options = new BuildPlayerOptions { scenes = new[] { Scene }, target = BuildTarget.StandaloneWindows64, locationPathName = path, options = BuildOptions.Development };
            var report = BuildPipeline.BuildPlayer(options);
            if (report.summary.result != BuildResult.Succeeded) throw new Exception("Build failed: " + report.summary.result);
            Debug.Log("TEA_BUILD_PASS " + path + " " + report.summary.totalSize + " bytes");
        }
    }
}
