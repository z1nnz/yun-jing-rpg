using System.IO;
using System.Linq;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace YunJing.Editor
{
    // Review renders of the generated novice village. Needs a graphics device (run Unity in
    // -batchmode without -nographics). Output: artifacts/qingxi-novice-village/*.png
    public static class QingxiCollaboratorZonesCapture
    {
        // Novice village review: an overview, the player's view from the gate and each zone.
        public static void CaptureVillage()
        {
            EditorSceneManager.OpenScene(QingxiNoviceVillageBuilder.ScenePath);
            var dir = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "..", "artifacts", "qingxi-novice-village"));
            Directory.CreateDirectory(dir);
            var camera = new GameObject("Review Camera").AddComponent<Camera>();
            camera.fieldOfView = 50; camera.nearClipPlane = .05f; camera.farClipPlane = 400;
            UnityEngine.Rendering.Universal.CameraExtensions.GetUniversalAdditionalCameraData(camera).renderPostProcessing = true;
            var target = new RenderTexture(1600, 900, 24) { antiAliasing = 4 };
            camera.targetTexture = target;
            // Heights below are above the local ground, so the shots follow the terrain relief.
            var terrain = Terrain.activeTerrain;
            System.Func<Vector3, Vector3> Lift = p => terrain ? p + Vector3.up * QingxiVillageTerrain.Ground(terrain, p.x, p.z) : p;
            void Shot(string file, Vector3 from, Vector3 at)
            {
                camera.transform.position = Lift(from); camera.transform.LookAt(Lift(at)); camera.Render();
                RenderTexture.active = target;
                var image = new Texture2D(target.width, target.height, TextureFormat.RGB24, false);
                image.ReadPixels(new Rect(0, 0, target.width, target.height), 0, 0); image.Apply();
                File.WriteAllBytes(Path.Combine(dir, file + ".png"), image.EncodeToPNG());
                RenderTexture.active = null; Object.DestroyImmediate(image);
            }
            Shot("00-overview", new Vector3(0, 46, -46), new Vector3(0, 0, 2));
            Shot("01-gate-view", new Vector3(0, 1.7f, -25), new Vector3(0, 1.2f, 0));
            Shot("02-plaza-return-C", new Vector3(1f, 3.2f, -5), new Vector3(5.5f, .5f, 2.2f));
            Shot("03-alchemy-B", new Vector3(-8, 4.5f, -6), new Vector3(-15, .6f, -2));
            Shot("04-training-yard", new Vector3(8, 5, -8), new Vector3(15, 1, -1));
            Shot("05-forest-A", new Vector3(0, 9, 4), new Vector3(0, 0, 20));
            Shot("06-forest-A-close", new Vector3(-4, 2.2f, 13), new Vector3(1, .6f, 22));
            Shot("07-plaza-to-forest-eye", new Vector3(0, 1.7f, 3), new Vector3(0, 1.2f, 16));
            Shot("08-plaza-to-alchemy-eye", new Vector3(-3, 1.7f, -2), new Vector3(-14, 1.2f, -2));
            Shot("09-plaza-to-yard-eye", new Vector3(3, 1.7f, -2), new Vector3(14, 1.2f, -2));
            Shot("10-lodging", new Vector3(4, 4.5f, -26), new Vector3(17, 1.5f, -19));
            Shot("11-market", new Vector3(-2, 3.5f, -20), new Vector3(-11, 1, -14));
            Shot("12-fields", new Vector3(-14, 6, -14), new Vector3(-25, 0, -24));
            Shot("13-herb-close", new Vector3(-18f, 1.4f, 7.5f), new Vector3(-19.5f, .2f, 9));
            Shot("14-creek-crossing-eye", new Vector3(-19.5f, 1.7f, 2.5f), new Vector3(-27f, .3f, 4.5f));
            Shot("15-creek-above", new Vector3(-12f, 14f, -16f), new Vector3(-30f, 0f, 2f));
            Shot("16-plan-overview", new Vector3(0, 78, -62), new Vector3(0, 0, -2));
            Shot("17-gate-square", new Vector3(6, 5, -40), new Vector3(0, 1, -28));
            Shot("18-homes-ne", new Vector3(14, 9, -2), new Vector3(27, 1, 18));
            Shot("19-smithy-shops", new Vector3(18, 9, -14), new Vector3(33, 1, -15));
            // K5: the neighbouring blocks open next to the village, to check the seams and the far side.
            foreach (var (id, _) in QingxiBlockBuilder.Blocks)
                if (File.Exists(QingxiBlockBuilder.ScenePath(id))) EditorSceneManager.OpenScene(QingxiBlockBuilder.ScenePath(id), OpenSceneMode.Additive);
            Physics.SyncTransforms();
            Lift = p => { var hits = Physics.RaycastAll(new Vector3(p.x, 200, p.z), Vector3.down, 400).Where(h => h.collider is TerrainCollider).ToArray(); float g = hits.Length > 0 ? hits.Max(h => h.point.y) : 0; return p + Vector3.up * g; };
            Shot("20-a1-to-a2-seam", new Vector3(14, 12, -36), new Vector3(0, 0, -62));
            Shot("21-a2-road-eye", new Vector3(1, 1.7f, -120), new Vector3(-6, 1.5f, -100));
            Shot("22-a2-view-to-village", new Vector3(-6, 1.7f, -66), new Vector3(0, 2, -28));
            Shot("23-a3-bridge-mill", new Vector3(-108, 8, -6), new Vector3(-88, 1, 14));
            Shot("24-a1-to-a3-seam", new Vector3(-36, 12, 22), new Vector3(-62, 0, 6));
            Debug.Log($"QINGXI_VILLAGE_CAPTURED to {dir} (pipeline: {(GraphicsSettings.currentRenderPipeline != null ? GraphicsSettings.currentRenderPipeline.name : "built-in")})");
        }

        // The creek chapter in the village: the old channel before and after the repair (PR #52), the council corner (PR #47).
        public static void CaptureCreekChapter()
        {
            EditorSceneManager.OpenScene(QingxiNoviceVillageBuilder.ScenePath);
            Physics.SyncTransforms();
            var dir = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "..", "artifacts", "qingxi-creek-chapter"));
            Directory.CreateDirectory(dir);
            var camera = new GameObject("Review Camera").AddComponent<Camera>();
            camera.fieldOfView = 50; camera.nearClipPlane = .05f; camera.farClipPlane = 400;
            UnityEngine.Rendering.Universal.CameraExtensions.GetUniversalAdditionalCameraData(camera).renderPostProcessing = true;
            var target = new RenderTexture(1600, 900, 24) { antiAliasing = 4 };
            camera.targetTexture = target;
            void Shot(string file, Vector3 from, Vector3 at)
            {
                camera.transform.position = from; camera.transform.LookAt(at); camera.Render();
                RenderTexture.active = target;
                var image = new Texture2D(target.width, target.height, TextureFormat.RGB24, false);
                image.ReadPixels(new Rect(0, 0, target.width, target.height), 0, 0); image.Apply();
                File.WriteAllBytes(Path.Combine(dir, file + ".png"), image.EncodeToPNG());
                RenderTexture.active = null; Object.DestroyImmediate(image);
            }
            var site = Object.FindFirstObjectByType<QingxiWaterworksSite>();
            var council = Object.FindFirstObjectByType<QingxiVillageReport>();
            var p = site.point.position;
            Shot("00-warmup", p + new Vector3(0, 30, -10), p);   // the first render has no ambient light yet
            File.Delete(Path.Combine(dir, "00-warmup.png"));
            site.repaired.SetActive(false);
            Shot("01-old-channel-before", p + new Vector3(-3.5f, 2.2f, 1.5f), p + new Vector3(1.2f, 0, -1.5f));
            site.repaired.SetActive(true);
            Shot("02-old-channel-after", p + new Vector3(-3.5f, 2.2f, 1.5f), p + new Vector3(1.2f, 0, -1.5f));
            Shot("03-channel-to-fields", p + new Vector3(1.5f, 6f, 6f), p + new Vector3(1.2f, 0, -4f));
            var c = council.point.position;
            Shot("04-council-corner", c + new Vector3(-4f, 2.4f, -4f), c);
            Shot("05-council-eye", c + new Vector3(0, 1.6f, -4.5f), c + new Vector3(0, .6f, 0));
            Shot("06-channel-top", p + new Vector3(1.2f, 9f, -2.5f), p + new Vector3(1.2f, 0, -2.4f));
            Debug.Log($"QINGXI_CREEK_CHAPTER_CAPTURED to {dir}");
        }

        // D3 upstream valley (PR #45): the brook tiles, the clue spots and the way in from A3, in the editor.
        public static void CaptureUpstream()
        {
            EditorSceneManager.OpenScene(QingxiNoviceVillageBuilder.ScenePath);
            foreach (var id in new[] { "A2", "A3", "D3" }) EditorSceneManager.OpenScene(QingxiBlockBuilder.ScenePath(id), OpenSceneMode.Additive);
            Physics.SyncTransforms();
            var dir = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "..", "artifacts", "qingxi-upstream-d3"));
            Directory.CreateDirectory(dir);
            var camera = new GameObject("Review Camera").AddComponent<Camera>();
            camera.fieldOfView = 55; camera.nearClipPlane = .05f; camera.farClipPlane = 400;
            UnityEngine.Rendering.Universal.CameraExtensions.GetUniversalAdditionalCameraData(camera).renderPostProcessing = true;
            var target = new RenderTexture(1600, 900, 24) { antiAliasing = 4 };
            camera.targetTexture = target;
            // Heights are above whatever is underfoot (terrain or the river tiles), so eye-level shots stand on the bank.
            Vector3 Lift(Vector3 p)
            {
                var hits = Physics.RaycastAll(new Vector3(p.x, 200, p.z), Vector3.down, 400).Where(h => !h.collider.isTrigger).ToArray();
                return p + Vector3.up * (hits.Length > 0 ? hits.Max(h => h.point.y) : 0);
            }
            void Shot(string file, Vector3 from, Vector3 at)
            {
                camera.transform.position = Lift(from); camera.transform.LookAt(Lift(at)); camera.Render();
                RenderTexture.active = target;
                var image = new Texture2D(target.width, target.height, TextureFormat.RGB24, false);
                image.ReadPixels(new Rect(0, 0, target.width, target.height), 0, 0); image.Apply();
                File.WriteAllBytes(Path.Combine(dir, file + ".png"), image.EncodeToPNG());
                RenderTexture.active = null; Object.DestroyImmediate(image);
            }
            Shot("00-overview", new Vector3(-40, 60, 30), new Vector3(-92, 0, 98));
            Shot("01-way-in-from-a3", new Vector3(-66, 1.7f, 40), new Vector3(-72, 1.2f, 66));
            Shot("02-brook-downstream-eye", new Vector3(-56, 1.7f, 56), new Vector3(-66, .5f, 72));
            Shot("03-silt-narrows", new Vector3(-66, 3.5f, 68), new Vector3(-74, 0, 82));
            Shot("04-cracked-sluice", new Vector3(-82, 2.5f, 77), new Vector3(-86.1f, .3f, 83.1f));
            Shot("05-gauge-and-marker", new Vector3(-72, 2.2f, 66), new Vector3(-77.5f, .6f, 68.1f));
            Shot("06-crossing-to-nursery", new Vector3(-94, 2.5f, 96), new Vector3(-86, .3f, 108));
            Shot("07-nursery-tracks", new Vector3(-82, 2.2f, 106), new Vector3(-85.6f, 0, 110.3f));
            Shot("08-ruin-to-source", new Vector3(-110, 4, 98), new Vector3(-128, 1, 120));
            Shot("09-resonance-stone", new Vector3(-126, 2, 117), new Vector3(-129.2f, .4f, 122.6f));
            Shot("10-brook-above", new Vector3(-70, 22, 70), new Vector3(-95, 0, 102));
            // The dressing in the other built blocks (world-dressing.json).
            Shot("11-a3-creek-dressing", new Vector3(-84, 3, 26), new Vector3(-100, 0, 4));
            Shot("12-a3-above", new Vector3(-60, 30, 10), new Vector3(-105, 0, 0));
            Shot("13-a2-road-dressing", new Vector3(4, 2, -112), new Vector3(-2, .5f, -80));
            Shot("14-a2-above", new Vector3(30, 30, -70), new Vector3(-5, 0, -110));
            Debug.Log($"QINGXI_UPSTREAM_CAPTURED to {dir}");
        }
    }
}
