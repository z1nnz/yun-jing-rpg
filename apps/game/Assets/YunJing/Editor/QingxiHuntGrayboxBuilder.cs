using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace YunJing.Editor
{
    // Isolated editor-only draft; no network actors, rewards or production scene changes.
    public static class QingxiHuntGrayboxBuilder
    {
        const string Source = "Assets/YunJing/Editor/QingxiHuntGraybox.json";
        const string Output = "Assets/YunJing/Generated/QingxiHuntGraybox.unity";
        const string Materials = "Assets/YunJing/Generated/HuntGrayboxMaterials";

        [Serializable] public class Box { public string name; public Vector3 position; public Vector3 size; public string kind; }
        [Serializable] public class Marker { public string name; public Vector3 position; }
        [Serializable] public class Route { public string name; public float width; public Vector3[] points; }
        [Serializable] public class Layout { public Box[] zones; public Box[] blockers; public Marker[] markers; public Route[] routes; }

        // Batch regression: exercise generation, saved-scene reload and rebuilding in one Editor run.
        public static void Verify()
        {
            if (!Application.isBatchMode) throw new InvalidOperationException("Run Verify in a dedicated batchmode Editor.");
            var layout = JsonUtility.FromJson<Layout>(File.ReadAllText(Source));
            for (int run = 0; run < 2; run++)
            {
                Generate();
                var scene = EditorSceneManager.OpenScene(Output, OpenSceneMode.Single);
                var root = Array.Find(scene.GetRootGameObjects(), obj => obj.name == "QingxiHuntGraybox");
                if (root == null) throw new InvalidDataException("Missing graybox root after reload.");
                foreach (var marker in layout.markers)
                {
                    var found = root.transform.Find(marker.name);
                    if (found == null || Vector3.Distance(found.position, marker.position) > .001f)
                        throw new InvalidDataException("Marker mismatch: " + marker.name);
                }
                foreach (var blocker in layout.blockers)
                {
                    var found = root.transform.Find(blocker.name);
                    if (found == null || found.GetComponent<BoxCollider>() == null ||
                        Vector3.Distance(found.position, blocker.position) > .001f ||
                        Vector3.Distance(found.localScale, blocker.size) > .001f)
                        throw new InvalidDataException("Blocker mismatch: " + blocker.name);
                }
                if (root.GetComponentInChildren<MeshCollider>() != null)
                    throw new InvalidDataException("Unexpected MeshCollider in graybox.");
            }
            Debug.Log("GRAYBOX_VERIFY_PASS: two builds and reloads; " + layout.markers.Length + " markers; " +
                layout.blockers.Length + " box blockers. No gameplay or NavMesh validation claimed.");
        }

        [MenuItem("Yun Jing/Generate independent Qingxi hunt graybox")]
        public static void Generate()
        {
            if (!Application.isBatchMode && !EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            var layout = JsonUtility.FromJson<Layout>(File.ReadAllText(Source));
            if (layout == null || layout.markers == null || layout.zones == null || layout.blockers == null || layout.routes == null)
                throw new InvalidDataException("Incomplete hunt graybox layout.");
            Directory.CreateDirectory(Materials);
            AssetDatabase.Refresh();
            var shader = Shader.Find("Universal Render Pipeline/Lit");
            if (shader == null) throw new InvalidOperationException("Pinned URP package must import successfully first.");
            var floor = Material("Floor", new Color(.32f, .40f, .29f), shader);
            var trail = Material("Trail", new Color(.61f, .52f, .34f), shader);
            var stone = Material("Blocker", new Color(.36f, .39f, .42f), shader);
            var water = Material("ShallowWater", new Color(.25f, .55f, .62f), shader);
            var markerMaterial = Material("Marker", new Color(.95f, .74f, .25f), shader);
            var previous = UnityEngine.SceneManagement.SceneManager.GetSceneByPath(Output);
            if (previous.IsValid() && previous.isLoaded)
            {
                if (previous.isDirty) throw new InvalidOperationException("Save or close the edited graybox before rebuilding.");
                if (UnityEngine.SceneManagement.SceneManager.sceneCount == 1)
                    EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
                else EditorSceneManager.CloseScene(previous, true);
            }
            // Unity rejects additive creation beside an untitled scene, even on a fresh batch launch.
            var active = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
            bool untitled = UnityEngine.SceneManagement.SceneManager.sceneCount == 1 && string.IsNullOrEmpty(active.path);
            if (untitled && active.isDirty) throw new InvalidOperationException("Save the untitled scene before generating.");
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, untitled ? NewSceneMode.Single : NewSceneMode.Additive);
            var root = new GameObject("QingxiHuntGraybox");
            UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(root, scene);
            var boundary = new GameObject("AreaBoundary_Hunt");
            boundary.transform.SetParent(root.transform, false);
            var bounds = boundary.AddComponent<BoxCollider>();
            bounds.isTrigger = true; bounds.size = new Vector3(220, 20, 160); bounds.center = new Vector3(0, 8, 0);
            Cube("Ground_220x160", new Vector3(0, -.5f, 0), new Vector3(220, 1, 160), floor, root.transform, true);
            foreach (var zone in layout.zones)
                Cube(zone.name, zone.position, zone.size, zone.kind == "water" ? water : floor, root.transform, false);
            foreach (var route in layout.routes)
            {
                var group = new GameObject(route.name); group.transform.SetParent(root.transform, false);
                for (int i = 1; i < route.points.Length; i++)
                {
                    var a = route.points[i - 1]; var b = route.points[i]; var delta = b - a;
                    var strip = Cube("Segment_" + i, (a + b) * .5f + Vector3.up * .035f,
                        new Vector3(route.width, .02f, delta.magnitude + .15f), trail, group.transform, false);
                    strip.transform.rotation = Quaternion.LookRotation(delta, Vector3.up);
                }
            }
            foreach (var blocker in layout.blockers)
            {
                var obj = Cube(blocker.name, blocker.position, blocker.size, stone, root.transform, true);
                var cameraTag = new GameObject(blocker.name.Replace("NavBlocker_", "CameraBlocker_"));
                cameraTag.transform.SetParent(obj.transform, false);
                // Child is a searchable annotation; the parent's BoxCollider serves both roles.
            }
            foreach (var marker in layout.markers)
            {
                var obj = new GameObject(marker.name); obj.transform.SetParent(root.transform, false);
                obj.transform.position = marker.position;
                Cube("Locator", marker.position + Vector3.up * .08f, new Vector3(.6f, .1f, .6f), markerMaterial, obj.transform, false);
            }
            var sun = new GameObject("GrayboxSun").AddComponent<Light>(); sun.transform.SetParent(root.transform, false);
            sun.type = LightType.Directional; sun.intensity = 1.2f; sun.transform.rotation = Quaternion.Euler(50, -30, 0);
            var camera = new GameObject("GrayboxOverview", typeof(Camera)).GetComponent<Camera>();
            camera.transform.SetParent(root.transform, false); camera.transform.position = new Vector3(0, 180, 0);
            camera.transform.rotation = Quaternion.Euler(90, 0, 0); camera.orthographic = true;
            camera.orthographicSize = 90; camera.farClipPlane = 300;
            if (!EditorSceneManager.SaveScene(scene, Output)) throw new IOException("Could not save " + Output);
            AssetDatabase.SaveAssets();
            Debug.Log("Generated draft " + Output + "; NavMesh, gameplay and camera clearance remain unverified.");
        }

        static Material Material(string name, Color color, Shader shader)
        {
            var path = Materials + "/" + name + ".mat";
            var material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (material == null) { material = new Material(shader); AssetDatabase.CreateAsset(material, path); }
            material.color = color; EditorUtility.SetDirty(material); return material;
        }

        static GameObject Cube(string name, Vector3 position, Vector3 size, Material material, Transform parent, bool solid)
        {
            var obj = GameObject.CreatePrimitive(PrimitiveType.Cube); obj.name = name;
            obj.transform.SetParent(parent, false); obj.transform.position = position; obj.transform.localScale = size;
            obj.GetComponent<Renderer>().sharedMaterial = material;
            if (!solid) UnityEngine.Object.DestroyImmediate(obj.GetComponent<Collider>());
            return obj;
        }
    }
}
