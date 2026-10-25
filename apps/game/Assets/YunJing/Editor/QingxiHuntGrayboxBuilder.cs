// Issue #9. Isolated greybox draft: no combat, API, network, or production-scene changes.
// NOT COMPILED IN UNITY. See docs/graybox/qingxi-hunt/README.md before using.
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace YunJing.Editor
{
    public static class QingxiHuntGrayboxBuilder
    {
        const string ScenePath = "Assets/YunJing/Generated/QingxiHuntGraybox.unity";
        const string AssetRoot = "Assets/YunJing/Generated/QingxiHuntGrayboxData";
        const string RootName = "QingxiHuntGraybox_ROOT";
        const string RequiredVersion = "6000.0.85f1";

        [Serializable] public class Extent { public float width, depth, grid; }
        [Serializable] public class Hill { public float centerX, centerZ, halfWidth, halfDepth, height; }
        [Serializable] public class Agent { public float speed, radius, height, maxSlope, stepHeight; }
        [Serializable] public class CameraSpec { public float minDistance, maxDistance, probeRadius, targetHeight, elevationDegrees; public int width, height; }
        [Serializable] public class Zone { public string name, label; public Vector3 center; public float width, depth; }
        [Serializable] public class Marker { public string name, kind, group, note; public Vector3 position; }
        [Serializable] public class Obstacle { public string name, kind; public Vector3 position, size; }
        [Serializable] public class Route { public string name; public float width; public Vector3[] points; }
        [Serializable] public class View { public string name; public Vector3 target; public float yaw, distance; }
        [Serializable] public class Layout
        {
            public int schemaVersion;
            public string name, unit, unityVersion, validationStatus;
            public Extent bounds; public Hill hill; public Agent player, rabbit; public CameraSpec camera;
            public Zone[] zones; public Marker[] markers; public Obstacle[] obstacles; public Route[] routes; public View[] views;
        }
        [Serializable] public class GeometryReport
        {
            public string unityVersion, layoutSha256, status = "geometry_only_navmesh_not_tested";
            public string[] blockedMarkers, cameraObstructions;
            public int markerCount, simplifiedBlockers, groundTriangles;
            public bool navMeshMeasured = false, multiplayerMeasured = false;
        }

        static string RepoRoot => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string LayoutPath => Path.Combine(RepoRoot, "docs/graybox/qingxi-hunt/layout.json");
        static Layout ReadLayout()
        {
            if (Application.unityVersion != RequiredVersion)
                throw new InvalidOperationException("Use pinned Unity " + RequiredVersion + "; do not upgrade project settings for this task.");
            var d = JsonUtility.FromJson<Layout>(File.ReadAllText(LayoutPath));
            if (d == null || d.schemaVersion != 1 || d.unit != "metre" || d.unityVersion != RequiredVersion ||
                d.bounds == null || d.bounds.grid <= 0 || d.zones == null || d.zones.Length != 6 ||
                d.markers == null || d.obstacles == null || d.routes == null || d.views == null || d.views.Length != 6)
                throw new InvalidDataException("Invalid layout. Run the offline validator first.");
            if (d.markers.Select(m => m.name).Distinct().Count() != d.markers.Length)
                throw new InvalidDataException("Duplicate marker IDs.");
            return d;
        }
        static float Ground(Layout d, float x, float z) => d.hill.height *
            Mathf.Max(0, 1 - Mathf.Abs(x - d.hill.centerX) / d.hill.halfWidth) *
            Mathf.Max(0, 1 - Mathf.Abs(z - d.hill.centerZ) / d.hill.halfDepth);
        static void EnsureFolder(string path)
        {
            if (AssetDatabase.IsValidFolder(path)) return;
            var parent = path.Substring(0, path.LastIndexOf('/')); EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, path.Substring(path.LastIndexOf('/') + 1));
        }
        static Material Mat(string name, Color color)
        {
            string path = AssetRoot + "/" + name + ".mat";
            var result = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (result == null)
            {
                var shader = Shader.Find(GraphicsSettings.currentRenderPipeline != null ? "Universal Render Pipeline/Lit" : "Standard");
                if (shader == null) throw new InvalidOperationException("No supported shader found; production render settings were not changed.");
                result = new Material(shader); AssetDatabase.CreateAsset(result, path);
            }
            result.color = color; EditorUtility.SetDirty(result); return result;
        }
        static GameObject Empty(string name, Transform parent, Vector3 position)
        {
            var obj = new GameObject(name); obj.transform.SetParent(parent, false); obj.transform.position = position; return obj;
        }
        static GameObject Primitive(string name, PrimitiveType type, Transform parent, Vector3 position, Vector3 size, Material material, bool solid)
        {
            var obj = GameObject.CreatePrimitive(type); obj.name = name; obj.transform.SetParent(parent, false);
            obj.transform.position = position; obj.transform.localScale = size;
            obj.GetComponent<Renderer>().sharedMaterial = material;
            if (!solid) UnityEngine.Object.DestroyImmediate(obj.GetComponent<Collider>());
            return obj;
        }
        static void GroundMesh(Layout d, Transform root, Material material)
        {
            int nx = Mathf.RoundToInt(d.bounds.width / d.bounds.grid), nz = Mathf.RoundToInt(d.bounds.depth / d.bounds.grid);
            var vertices = new Vector3[(nx + 1) * (nz + 1)]; var triangles = new int[nx * nz * 6];
            for (int z = 0; z <= nz; z++) for (int x = 0; x <= nx; x++)
            {
                float px = x * d.bounds.grid, pz = z * d.bounds.grid;
                vertices[z * (nx + 1) + x] = new Vector3(px, Ground(d, px, pz), pz);
            }
            int t = 0;
            for (int z = 0; z < nz; z++) for (int x = 0; x < nx; x++)
            {
                int a = z * (nx + 1) + x, b = a + nx + 1;
                triangles[t++] = a; triangles[t++] = b; triangles[t++] = a + 1;
                triangles[t++] = a + 1; triangles[t++] = b; triangles[t++] = b + 1;
            }
            string path = AssetRoot + "/Ground.asset";
            var mesh = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if (mesh == null) { mesh = new Mesh(); AssetDatabase.CreateAsset(mesh, path); }
            mesh.Clear(); mesh.name = "Ground_5m_grid"; mesh.vertices = vertices; mesh.triangles = triangles;
            mesh.RecalculateBounds(); mesh.RecalculateNormals(); EditorUtility.SetDirty(mesh);
            var obj = Empty("Ground_1485_vertices_2816_triangles", root, Vector3.zero);
            obj.AddComponent<MeshFilter>().sharedMesh = mesh; obj.AddComponent<MeshRenderer>().sharedMaterial = material;
            // The single coarse ground mesh is the only MeshCollider. Props use boxes.
            obj.AddComponent<MeshCollider>().sharedMesh = mesh;
        }
        static Color MarkerColor(string kind)
        {
            switch (kind)
            {
                case "player": return new Color(.4f, .7f, 1);
                case "rabbit": return new Color(1, .72f, .3f);
                case "flee": return new Color(1, .4f, .3f);
                case "herb": return new Color(.3f, .9f, .45f);
                case "merchant": return new Color(1, .85f, .35f);
                default: return new Color(.65f, .7f, .7f);
            }
        }

        [MenuItem("Yun Jing/Graybox/Generate isolated Qingxi hunt draft")]
        public static void Generate()
        {
            Layout d = ReadLayout();
            if (SceneManager.GetSceneByPath(ScenePath).isLoaded)
                throw new InvalidOperationException("Close only QingxiHuntGraybox before rebuilding. No open scene was discarded.");
            EnsureFolder(AssetRoot);
            // Additive keeps the user's open scenes; it is not allowed while the only scene is the untitled default (always so in batch mode).
            var active = SceneManager.GetActiveScene();
            bool untitledOnly = SceneManager.sceneCount == 1 && string.IsNullOrEmpty(active.path) && !active.isDirty;
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, untitledOnly ? NewSceneMode.Single : NewSceneMode.Additive);
            SceneManager.SetActiveScene(scene);
            var root = new GameObject(RootName).transform;
            var ground = Mat("Ground", new Color(.35f, .43f, .36f));
            var cliff = Mat("Cliff", new Color(.42f, .45f, .46f));
            var foliage = Mat("TreeProxy", new Color(.21f, .36f, .29f));
            var water = Mat("WaterProxy", new Color(.23f, .54f, .65f));
            var road = Mat("MainRoute", new Color(.72f, .61f, .41f));
            var shortcut = Mat("ReturnRoute", new Color(.41f, .66f, .64f));
            GroundMesh(d, root, ground);
            var areas = Empty("Areas", root, Vector3.zero).transform;
            foreach (var zone in d.zones) Empty("Area_" + zone.name + "_" + zone.width + "x" + zone.depth + "m", areas, zone.center);
            var props = Empty("SimplifiedColliders", root, Vector3.zero).transform;
            foreach (var o in d.obstacles)
            {
                var obj = Primitive(o.name, PrimitiveType.Cube, props, o.position, o.size, o.kind == "tree" ? foliage : o.kind == "deepWater" ? water : cliff, true);
                // Deep water is closed for both agents. A separate shallow strip has no water collider.
                if (o.kind == "boundary") obj.GetComponent<Renderer>().enabled = false;
            }
            Primitive("ShallowWater_depth_0.12m", PrimitiveType.Cube, root, new Vector3(140, .06f, 45), new Vector3(40, .12f, 30), water, false);
            var roads = Empty("RouteReferences_no_countdown_no_arrows", root, Vector3.zero).transform;
            foreach (var r in d.routes.Where(r => r.name == "MainDiscovery" || r.name == "AlternativeReturn" || r.name == "HerdConnector"))
                for (int i = 1; i < r.points.Length; i++)
                {
                    Vector3 a = r.points[i - 1], b = r.points[i]; float length = Vector3.Distance(a, b);
                    int steps = Mathf.Max(1, Mathf.CeilToInt(length / 2));
                    for (int j = 0; j < steps; j++)
                    {
                        Vector3 p = Vector3.Lerp(a, b, (j + .5f) / steps); p.y = Ground(d, p.x, p.z) + .025f;
                        var strip = Primitive(r.name + "_" + i + "_" + j, PrimitiveType.Cube, roads, p, new Vector3(r.width, .04f, length / steps + .05f), r.name == "AlternativeReturn" ? shortcut : road, false);
                        strip.transform.rotation = Quaternion.LookRotation(new Vector3(b.x - a.x, 0, b.z - a.z));
                    }
                }
            var markers = Empty("Markers", root, Vector3.zero).transform;
            foreach (var m in d.markers)
            {
                var anchor = Empty(m.name, markers, m.position).transform;
                if (m.kind == "boundary" || m.kind == "cameraBlocker") continue;
                var material = Mat("Marker_" + m.kind, MarkerColor(m.kind));
                Primitive("Location_only", PrimitiveType.Cylinder, anchor, m.position + Vector3.up * .04f, new Vector3(.6f, .04f, .6f), material, false);
                var label = Empty("Label", anchor, m.position + Vector3.up * 1.4f).AddComponent<TextMesh>();
                label.text = m.name; label.anchor = TextAnchor.MiddleCenter; label.characterSize = .08f; label.fontSize = 36;
                label.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");   // a TextMesh added from code has no font and draws nothing
                label.GetComponent<MeshRenderer>().sharedMaterial = label.font.material;
                if (m.kind == "rabbit") Primitive("Rabbit_PROXY_not_enemy", PrimitiveType.Capsule, anchor, m.position + Vector3.up * .4f, new Vector3(.5f, .4f, .5f), material, false);
                if (m.kind == "player") Primitive("Player_PROXY_not_networked", PrimitiveType.Capsule, anchor, m.position + Vector3.up, new Vector3(.7f, 1, .7f), material, false);
                if (m.kind == "clue")
                    for (int j = 0; j < 4; j++) Primitive("Footprint_" + j, PrimitiveType.Cube, anchor, m.position + new Vector3(j % 2 == 0 ? -.15f : .15f, .035f, j * .3f), new Vector3(.12f, .035f, .2f), material, false);
            }
            var bookmarks = Empty("CameraBookmarks_3.5_to_6m", root, Vector3.zero).transform;
            foreach (var view in d.views)
            {
                var cam = Empty("View_" + view.name, bookmarks, CameraPosition(d, view, view.distance)).AddComponent<Camera>();
                cam.transform.LookAt(view.target + Vector3.up * d.camera.targetHeight); cam.fieldOfView = 60;
                cam.aspect = (float)d.camera.width / d.camera.height; cam.nearClipPlane = .1f; cam.farClipPlane = 300; cam.enabled = false;
            }
            var preview = Empty("GrayboxPreviewCamera", root, CameraPosition(d, d.views[0], 5)).AddComponent<Camera>();
            preview.transform.LookAt(d.views[0].target + Vector3.up * d.camera.targetHeight); preview.fieldOfView = 60; preview.farClipPlane = 300;
            var sun = Empty("GrayboxSun", root, Vector3.zero).AddComponent<Light>(); sun.type = LightType.Directional; sun.intensity = 1.2f; sun.transform.rotation = Quaternion.Euler(50, -30, 0);
            RenderSettings.ambientLight = new Color(.65f, .65f, .65f);
            if (!EditorSceneManager.SaveScene(scene, ScenePath)) throw new IOException("Could not save isolated greybox scene.");
            AssetDatabase.SaveAssets(); Selection.activeGameObject = root.gameObject;
            Debug.Log("Generated geometry only. No NavMesh bake, playable controller, multiplayer, combat, or rewards. Close other scenes before previewing.");
        }
        static Vector3 CameraPosition(Layout d, View view, float distance)
        {
            float pitch = d.camera.elevationDegrees * Mathf.Deg2Rad;
            Vector3 forward = Quaternion.Euler(0, view.yaw, 0) * Vector3.forward;
            return view.target + Vector3.up * d.camera.targetHeight - forward * (distance * Mathf.Cos(pitch)) + Vector3.up * (distance * Mathf.Sin(pitch));
        }
        static Transform LoadedRoot()
        {
            var scene = SceneManager.GetSceneByPath(ScenePath);
            if (!scene.isLoaded) throw new InvalidOperationException("Open QingxiHuntGraybox first.");
            return scene.GetRootGameObjects().Single(x => x.name == RootName).transform;
        }
        [MenuItem("Yun Jing/Graybox/Check isolated geometry (not NavMesh)")]
        public static void CheckGeometry()
        {
            var d = ReadLayout(); var root = LoadedRoot(); Physics.SyncTransforms();
            var blocked = d.markers.Where(m => m.kind == "player" || m.kind == "rabbit" || m.kind == "flee" || m.kind == "herb" || m.kind == "merchant")
                .Where(m => {
                    var agent = m.kind == "rabbit" || m.kind == "flee" ? d.rabbit : d.player;
                    Vector3 bottom = m.position + Vector3.up * (agent.radius + .05f), top = m.position + Vector3.up * (agent.height - agent.radius);
                    return Physics.OverlapCapsule(bottom, top, agent.radius).Any(c => c.transform.IsChildOf(root));
                }).Select(m => m.name).ToArray();
            var cameraHits = d.views.SelectMany(v => new[] { d.camera.minDistance, d.camera.maxDistance }.Select(distance => {
                Vector3 target = v.target + Vector3.up * d.camera.targetHeight, delta = CameraPosition(d, v, distance) - target;
                return Physics.SphereCastAll(target, d.camera.probeRadius, delta.normalized, delta.magnitude)
                    .Any(hit => hit.collider.transform.IsChildOf(root)) ? v.name + "@" + distance + "m" : null;
            })).Where(x => x != null).ToArray();
            var hash = System.Security.Cryptography.SHA256.Create();
            var report = new GeometryReport { unityVersion = Application.unityVersion, layoutSha256 = BitConverter.ToString(hash.ComputeHash(File.ReadAllBytes(LayoutPath))).Replace("-", "").ToLowerInvariant(),
                markerCount = d.markers.Length, simplifiedBlockers = d.obstacles.Length, groundTriangles = 2816, blockedMarkers = blocked, cameraObstructions = cameraHits };
            hash.Dispose(); string dir = Path.Combine(RepoRoot, "artifacts/qingxi-hunt-graybox"); Directory.CreateDirectory(dir);
            File.WriteAllText(Path.Combine(dir, "unity-geometry.json"), JsonUtility.ToJson(report, true));
            if (blocked.Length + cameraHits.Length > 0) throw new InvalidOperationException("Geometry conflicts found; inspect unity-geometry.json.");
            Debug.Log("Geometry checks only. NavMesh and two-player movement remain unmeasured.");
        }
        [MenuItem("Yun Jing/Graybox/Select bird's-eye view")]
        public static void BirdEye()
        {
            LoadedRoot(); if (SceneView.lastActiveSceneView == null) throw new InvalidOperationException("Open a Scene view first.");
            SceneView.lastActiveSceneView.LookAt(new Vector3(110, 0, 80), Quaternion.Euler(90, 0, 0), 135, true);
        }

        [Serializable] public class NavigationPathResult { public string profile, from, to, status; public float length; }
        [Serializable] public class NavigationReport
        {
            public string status, unityVersion; public bool measuredInUnity;
            public List<NavigationPathResult> paths = new List<NavigationPathResult>();
            public string registration = "Each profile is registered separately during validation; not production NavMesh/agent integration.";
        }
        static string EvidenceDirectory()
        {
            string dir = Path.Combine(RepoRoot, "artifacts/qingxi-hunt-graybox"); Directory.CreateDirectory(dir); return dir;
        }
        // Resolve the built-in AI module at Editor runtime. This isolated tool must not edit the
        // production Packages/manifest.json or global agent settings to gain an AI Navigation dependency.
        static Type AiType(string name)
        {
            var type = Type.GetType("UnityEngine.AI." + name + ", UnityEngine.AIModule");
            if (type == null) throw new NotSupportedException("Built-in Unity AI module unavailable: " + name + ". NavMesh has NOT been validated.");
            return type;
        }
        static void Set(object obj, string property, object value)
        {
            var p = obj.GetType().GetProperty(property, BindingFlags.Public | BindingFlags.Instance);
            if (p == null || !p.CanWrite) throw new MissingMemberException(obj.GetType().FullName, property);
            p.SetValue(obj, value);
        }
        static object Get(object obj, string property) => obj.GetType().GetProperty(property).GetValue(obj);
        static MethodInfo StaticMethod(Type type, string name, params Type[] arguments) => type.GetMethod(name, BindingFlags.Public | BindingFlags.Static, null, arguments, null) ?? throw new MissingMethodException(type.FullName, name);

        [MenuItem("Yun Jing/Graybox/Bake and check isolated NavMesh profiles")]
        public static void CheckNavigation()
        {
            var d = ReadLayout(); var root = LoadedRoot();
            if (SceneManager.sceneCount != 1) throw new InvalidOperationException("Validate with ONLY the isolated greybox open; other scenes' navigation must not affect the result.");
            var nav = AiType("NavMesh"); var builder = AiType("NavMeshBuilder"); var sourceType = AiType("NavMeshBuildSource");
            var shape = AiType("NavMeshBuildSourceShape"); var settingsType = AiType("NavMeshBuildSettings");
            var dataType = AiType("NavMeshData"); var hitType = AiType("NavMeshHit"); var pathType = AiType("NavMeshPath");
            var listType = typeof(List<>).MakeGenericType(sourceType); var sources = (IList)Activator.CreateInstance(listType);
            foreach (var collider in root.GetComponentsInChildren<Collider>())
            {
                object source = Activator.CreateInstance(sourceType);
                if (collider is MeshCollider floor)
                {
                    Set(source, "shape", Enum.Parse(shape, "Mesh")); Set(source, "sourceObject", floor.sharedMesh);
                    Set(source, "transform", floor.transform.localToWorldMatrix); Set(source, "area", 0);
                }
                else if (collider is BoxCollider box)
                {
                    Set(source, "shape", Enum.Parse(shape, "Box")); Set(source, "size", box.size);
                    Set(source, "transform", box.transform.localToWorldMatrix * Matrix4x4.Translate(box.center)); Set(source, "area", 1);
                }
                else continue;
                sources.Add(source);
            }
            var bounds = new Bounds(new Vector3(110, 5, 80), new Vector3(222, 30, 162));
            var report = new NavigationReport { status = "running", unityVersion = Application.unityVersion, measuredInUnity = true };
            var calculate = StaticMethod(nav, "CalculatePath", typeof(Vector3), typeof(Vector3), typeof(int), pathType);
            var sample = StaticMethod(nav, "SamplePosition", typeof(Vector3), hitType.MakeByRefType(), typeof(float), typeof(int));
            foreach (string profile in new[] { "Player", "Rabbit" })
            {
                var agent = profile == "Player" ? d.player : d.rabbit;
                object settings = StaticMethod(nav, "GetSettingsByID", typeof(int)).Invoke(null, new object[] { 0 });
                Set(settings, "agentTypeID", 0); Set(settings, "agentRadius", agent.radius); Set(settings, "agentHeight", agent.height);
                Set(settings, "agentSlope", agent.maxSlope); Set(settings, "agentClimb", agent.stepHeight);
                Set(settings, "overrideVoxelSize", true); Set(settings, "voxelSize", .1f); Set(settings, "minRegionArea", .5f);
                var data = (UnityEngine.Object)StaticMethod(builder, "BuildNavMeshData", settingsType, listType, typeof(Bounds), typeof(Vector3), typeof(Quaternion))
                    .Invoke(null, new object[] { settings, sources, bounds, Vector3.zero, Quaternion.identity });
                if (data == null) throw new InvalidOperationException(profile + " NavMesh bake returned null.");
                data.name = "QingxiHunt_" + profile;
                string assetPath = AssetRoot + "/NavMesh" + profile + ".asset";
                var previous = AssetDatabase.LoadAssetAtPath<UnityEngine.Object>(assetPath);
                if (previous != null) { EditorUtility.CopySerialized(data, previous); UnityEngine.Object.DestroyImmediate(data); data = previous; EditorUtility.SetDirty(data); }
                else AssetDatabase.CreateAsset(data, assetPath);
                object registration = StaticMethod(nav, "AddNavMeshData", dataType).Invoke(null, new object[] { data });
                try
                {
                    var pairs = new List<Tuple<string, Vector3, string, Vector3>>();
                    if (profile == "Rabbit")
                    {
                        foreach (string group in new[] { "A", "B", "C" })
                        {
                            var nodes = d.markers.Where(m => m.group == group).ToArray();
                            for (int i = 0; i < nodes.Length; i++) for (int j = i + 1; j < nodes.Length; j++)
                                pairs.Add(Tuple.Create(nodes[i].name, nodes[i].position, nodes[j].name, nodes[j].position));
                        }
                    }
                    else
                    {
                        foreach (var route in d.routes.Where(r => r.name == "MainDiscovery" || r.name == "AlternativeReturn"))
                            for (int i = 1; i < route.points.Length; i++) pairs.Add(Tuple.Create(route.name + "_" + (i - 1), route.points[i - 1], route.name + "_" + i, route.points[i]));
                        foreach (var marker in d.markers.Where(m => m.kind == "player" || m.kind == "herb" || m.kind == "merchant"))
                            pairs.Add(Tuple.Create("SafeReturn_01", d.markers.Single(m => m.name == "SafeReturn_01").position, marker.name, marker.position));
                    }
                    foreach (var pair in pairs)
                    {
                        var a = new object[] { pair.Item2 + Vector3.up * .1f, Activator.CreateInstance(hitType), .6f, -1 };
                        var b = new object[] { pair.Item4 + Vector3.up * .1f, Activator.CreateInstance(hitType), .6f, -1 };
                        bool foundA = (bool)sample.Invoke(null, a), foundB = (bool)sample.Invoke(null, b);
                        object path = Activator.CreateInstance(pathType); string status = "endpoint_not_on_navmesh"; float length = 0;
                        if (foundA && foundB && (bool)calculate.Invoke(null, new object[] { Get(a[1], "position"), Get(b[1], "position"), -1, path }))
                        {
                            status = Get(path, "status").ToString(); var corners = (Vector3[])Get(path, "corners");
                            for (int i = 1; i < corners.Length; i++) length += Vector3.Distance(corners[i - 1], corners[i]);
                        }
                        report.paths.Add(new NavigationPathResult { profile = profile, from = pair.Item1, to = pair.Item3, status = status, length = length });
                    }
                }
                finally { registration.GetType().GetMethod("Remove").Invoke(registration, null); }
            }
            report.status = report.paths.All(p => p.status == "PathComplete") ? "passed" : "failed";
            AssetDatabase.SaveAssets(); File.WriteAllText(Path.Combine(EvidenceDirectory(), "unity-navigation.json"), JsonUtility.ToJson(report, true));
            if (report.status != "passed") throw new InvalidOperationException("NavMesh path validation failed; inspect unity-navigation.json.");
        }

        [Serializable] public class WalkResult { public string route; public bool completed; public int steps; public float simulatedSeconds, minimumSeparation, maxTargetError; }
        [Serializable] public class WalkReport { public string status, unityVersion; public string method = "Two temporary CharacterControllers, synchronous fixed steps in Editor; not two human/network clients."; public List<WalkResult> routes = new List<WalkResult>(); }
        [MenuItem("Yun Jing/Graybox/Rehearse two temporary controllers")]
        public static void RehearseControllers()
        {
            var d = ReadLayout(); LoadedRoot(); var report = new WalkReport { unityVersion = Application.unityVersion };
            foreach (var route in d.routes.Where(r => r.name == "MainDiscovery" || r.name == "AlternativeReturn"))
            {
                var controllers = new CharacterController[2]; var indices = new[] { 1, 1 }; var vertical = new float[2];
                try
                {
                    for (int i = 0; i < 2; i++)
                    {
                        var obj = new GameObject("TemporaryGeometryWalker_" + i) { hideFlags = HideFlags.HideAndDontSave };
                        Vector3 start = route.name == "MainDiscovery" ? d.markers.Single(m => m.name == "PlayerSpawn_0" + (i + 1)).position : route.points[0] + new Vector3(i * 2 - 1, 0, 0);
                        start.y = Ground(d, start.x, start.z) + .1f; obj.transform.position = start;
                        var cc = obj.AddComponent<CharacterController>(); cc.radius = d.player.radius; cc.height = d.player.height; cc.center = Vector3.up;
                        cc.slopeLimit = d.player.maxSlope; cc.stepOffset = d.player.stepHeight; cc.skinWidth = .03f; cc.minMoveDistance = 0; controllers[i] = cc;
                    }
                    var result = new WalkResult { route = route.name, minimumSeparation = float.MaxValue };
                    for (int step = 0; step < 6500; step++)
                    {
                        Physics.SyncTransforms();
                        for (int i = 0; i < 2; i++)
                        {
                            if (indices[i] >= route.points.Length) continue;
                            int index = indices[i]; Vector3 tangent = route.points[index] - route.points[index - 1]; tangent.y = 0; tangent.Normalize();
                            Vector3 target = route.points[index] + new Vector3(tangent.z, 0, -tangent.x) * (i == 0 ? -.8f : .8f);
                            Vector3 delta = target - controllers[i].transform.position; delta.y = 0;
                            if (delta.magnitude < .2f) { indices[i]++; continue; }
                            vertical[i] = controllers[i].isGrounded ? -2 : Mathf.Max(-20, vertical[i] - 9.81f * .02f);
                            controllers[i].Move(delta.normalized * (d.player.speed * .02f) + Vector3.up * (vertical[i] * .02f));
                        }
                        result.minimumSeparation = Mathf.Min(result.minimumSeparation, Vector3.Distance(controllers[0].transform.position, controllers[1].transform.position));
                        result.steps = step + 1;
                        if (indices.All(index => index >= route.points.Length)) { result.completed = true; break; }
                    }
                    result.simulatedSeconds = result.steps * .02f;
                    result.maxTargetError = controllers.Max(c => Vector3.Distance(c.transform.position, route.points.Last()));
                    report.routes.Add(result);
                }
                finally { foreach (var c in controllers) if (c != null) UnityEngine.Object.DestroyImmediate(c.gameObject); }
            }
            report.status = report.routes.All(r => r.completed && r.minimumSeparation >= d.player.radius * 2 - .04f && r.maxTargetError < 1.5f) ? "passed" : "failed";
            File.WriteAllText(Path.Combine(EvidenceDirectory(), "unity-walking.json"), JsonUtility.ToJson(report, true));
            if (report.status != "passed") throw new InvalidOperationException("Two-controller geometry rehearsal failed; inspect unity-walking.json.");
        }

        public static void ValidateBatch()
        {
            if (!Application.isBatchMode) throw new InvalidOperationException("This entry point is for a separate batch Editor only.");
            Generate(); EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            CheckGeometry(); CheckNavigation(); RehearseControllers();
            Debug.Log("QINGXI_GRAYBOX_VALIDATION_PASSED");
        }
    }
}
