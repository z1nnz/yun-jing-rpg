// Integrated Qingxi world (Unity 6000.0.85f1): the town blockout exported by tools/export-qingxi-town-for-unity.py plus the
// 220 x 160 m hunt graybox from docs/graybox/qingxi-hunt/layout.json, rotated 180 degrees south-west of the town, dressed
// with the dondon handoff FBX models. Bakes separate player / rabbit NavMesh data, runs route tests, writes screenshots to
// artifacts/qingxi-world and adds a local first-person walker. Scripted checks only: no rabbit AI on the server, combat,
// drops, network or phone test. See docs/qingxi-world/README.md.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.AI;

namespace QingxiWorld.Editor
{
    public static class QingxiWorldBuilder
    {
        const string Root = "Assets/QingxiWorld";
        const string ScenePath = Root + "/Generated/QingxiWorld.unity";
        static string RepoRoot => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string Reports => Path.Combine(RepoRoot, "artifacts/qingxi-world");

        // ---------------------------------------------------------------- data
        [Serializable] public class Placement { public string asset, role; public float x, y, z, yaw_deg, scale; }
        [Serializable] public class Hunt { public float[] origin_xy; }
        [Serializable] public class TownWorld { public float water_level; public Hunt hunt; public Placement[] placements; }
        [Serializable] public class HuntAgent { public float speed, radius, height, maxSlope, stepHeight; }
        [Serializable] public class HuntHill { public float centerX, centerZ, halfWidth, halfDepth, height; }
        [Serializable] public class HuntExtent { public float width, depth, grid; }
        [Serializable] public class HuntMarker { public string name, kind, group; public Vector3 position; }
        [Serializable] public class HuntObstacle { public string name, kind; public Vector3 position, size; }
        [Serializable] public class HuntRoute { public string name; public float width; public Vector3[] points; }
        [Serializable] public class HuntZone { public string name, label; public Vector3 center; public float width, depth; }
        [Serializable] public class HuntLayout { public HuntExtent bounds; public HuntHill hill; public HuntAgent player, rabbit; public HuntZone[] zones; public HuntMarker[] markers; public HuntObstacle[] obstacles; public HuntRoute[] routes; }
        [Serializable] public class ArtInstance { public string @object, source; public float[] blender_xy; public float yaw_deg, scale, z_offset; }
        [Serializable] public class ArtPlacement { public ArtInstance[] instances; }

        // ---------------------------------------------------------------- report
        [Serializable] public class PointCheck { public string name, profile; public bool onNavMesh, capsuleClear; public float snapDistance, edgeClearance; public string[] blockers; }
        [Serializable] public class PathCheck { public string profile, from, to, status; public float length, straight, seconds; public int legs; public Vector3 end; }
        [Serializable] public class WalkCheck { public string route; public bool completed; public float simulatedSeconds, minimumSeparation, finalError, longestStallSeconds; }
        [Serializable] public class GroupCheck { public string group; public bool allPairsConnected, fleeWithinLeash; public float longestFleePath, longestFleeSeconds; }
        [Serializable] public class Report
        {
            public string unityVersion, scope = "Local Unity 6000.0.85f1 copy inside dondon2.0-main. Scripted NavMesh paths and two CharacterController walks; no rabbit AI, combat, drops, multiplayer or device test.";
            public string status; public List<string> failures = new List<string>(); public List<string> notes = new List<string>();
            public List<string> mappingCheck = new List<string>();
            public List<PointCheck> points = new List<PointCheck>(); public List<PathCheck> paths = new List<PathCheck>();
            public List<WalkCheck> walks = new List<WalkCheck>(); public List<GroupCheck> rabbitGroups = new List<GroupCheck>();
            public float minRabbitRespawnSpacing, minRespawnToPlayerSpawn; public List<string> respawnVisibleFromPlayerSpawn = new List<string>();
            public int navTrianglesPlayer, navTrianglesRabbit; public List<string> screenshots = new List<string>();
        }
        static Report report;

        // ---------------------------------------------------------------- helpers
        static T Json<T>(string file) => JsonUtility.FromJson<T>(File.ReadAllText(Path.Combine(Application.dataPath, "QingxiWorld/Data", file)));
        static T RepoJson<T>(string path) => JsonUtility.FromJson<T>(File.ReadAllText(Path.Combine(RepoRoot, path)));
        static Material Mat(string name, Color c, bool transparent = false)
        {
            string path = Root + "/Generated/Materials/" + name + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m == null) { m = new Material(Shader.Find(transparent ? "Sprites/Default" : "Standard")); AssetDatabase.CreateAsset(m, path); }
            m.color = c; EditorUtility.SetDirty(m); return m;
        }
        static GameObject Node(string name, Transform parent) { var g = new GameObject(name); g.transform.SetParent(parent, false); return g; }
        static GameObject Model(string file, Transform parent)
        {
            var src = AssetDatabase.LoadAssetAtPath<GameObject>(Root + "/Models/" + file);
            if (src == null) throw new FileNotFoundException("Missing model " + file);
            var g = (GameObject)PrefabUtility.InstantiatePrefab(src); g.transform.SetParent(parent, false); return g;
        }
        static Bounds LocalBounds(Transform pivot)
        {
            var rs = pivot.GetComponentsInChildren<Renderer>(); var b = new Bounds(Vector3.zero, Vector3.zero); bool first = true;
            foreach (var r in rs)
            {
                var e = r.bounds.extents; var c = r.bounds.center;
                for (int i = 0; i < 8; i++)
                {
                    var p = pivot.InverseTransformPoint(c + Vector3.Scale(e, new Vector3(i % 2 == 0 ? -1 : 1, (i / 2) % 2 == 0 ? -1 : 1, i / 4 == 0 ? -1 : 1)));
                    if (first) { b = new Bounds(p, Vector3.zero); first = false; } else b.Encapsulate(p);
                }
            }
            return b;
        }
        static readonly HashSet<Collider> Walkable = new HashSet<Collider>();
        static void AddBox(GameObject pivot) { var b = LocalBounds(pivot.transform); var c = pivot.AddComponent<BoxCollider>(); c.center = b.center; c.size = b.size; }
        static void AddCapsule(GameObject pivot, float radius, float height) { var c = pivot.AddComponent<CapsuleCollider>(); c.radius = radius; c.height = height; c.center = Vector3.up * height / 2; }
        static void AddMeshColliders(GameObject g, bool walkable)
        {
            foreach (var mf in g.GetComponentsInChildren<MeshFilter>())
            {
                var c = mf.gameObject.AddComponent<MeshCollider>(); c.sharedMesh = mf.sharedMesh;
                if (walkable) Walkable.Add(c);
            }
        }
        // Blender-exported FBX: model front -Y and +X arrive turned 180 degrees about up, so Blender yaw t becomes 180 - t.
        static GameObject PlaceBlenderModel(string file, Transform parent, Vector3 unityPos, float blenderYaw, float scale, string name)
        {
            var pivot = Node(name, parent); pivot.transform.localPosition = unityPos;
            pivot.transform.localRotation = Quaternion.Euler(0, 180 - blenderYaw, 0); pivot.transform.localScale = Vector3.one * scale;
            Model(file, pivot.transform); return pivot;
        }

        // ---------------------------------------------------------------- build
        [MenuItem("Qingxi World/Build world and run route tests")]
        public static void BuildAndTest()
        {
            report = new Report { unityVersion = Application.unityVersion }; Walkable.Clear();
            AssetDatabase.DeleteAsset(Root + "/Generated"); AssetDatabase.CreateFolder(Root, "Generated"); AssetDatabase.CreateFolder(Root + "/Generated", "Materials");
            Directory.CreateDirectory(Reports); Directory.CreateDirectory(Path.Combine(Reports, "screens"));
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var world = new GameObject("QingxiWorld_ROOT").transform;
            var town = Json<TownWorld>("town_world.json"); var hunt = RepoJson<HuntLayout>("docs/graybox/qingxi-hunt/layout.json");

            BuildTown(world, town);
            MappingCheck();
            var huntRoot = BuildHunt(world, town, hunt);
            Lighting(world);

            // NavMesh: player over the whole world, rabbit over the hunt area only
            var playerData = Bake(world, new Bounds(new Vector3(-50, 20, -30), new Vector3(560, 120, 520)), hunt.player, .2f, "Player", town);
            var rabbitBounds = new Bounds(huntRoot.TransformPoint(new Vector3(110, 0, 80)), new Vector3(230, 40, 170));
            var rabbitData = Bake(world, rabbitBounds, hunt.rabbit, .1f, "Rabbit", town);

            var markers = hunt.markers.ToDictionary(m => m.name, m => huntRoot.TransformPoint(m.position));
            markers["PlayerSpawn_Town"] = SnapDown(new Vector3(-3, 30, 17));
            Node("PlayerSpawn_Town", world).transform.position = markers["PlayerSpawn_Town"];

            var lines = Node("RouteTest_Lines", world).transform;
            using (var inst = new NavInstance(playerData)) { report.navTrianglesPlayer = Preview(world, "NavMeshPreview_Player", new Color(.2f, .5f, 1f, .35f), .06f); PlayerTests(hunt, huntRoot, markers, lines); }
            using (var inst = new NavInstance(rabbitData)) { report.navTrianglesRabbit = Preview(world, "NavMeshPreview_Rabbit", new Color(1f, .55f, .1f, .45f), .1f); RabbitTests(hunt, markers, lines); }

            Screens(world, huntRoot);
            AddPlayer(world, huntRoot, hunt, markers, rabbitData);
            report.status = report.failures.Count == 0 ? "passed" : "failed";
            File.WriteAllText(Path.Combine(Reports, "route_test.json"), JsonUtility.ToJson(report, true));
            Directory.CreateDirectory(Path.GetDirectoryName(ScenePath));
            EditorSceneManager.SaveScene(scene, ScenePath); AssetDatabase.SaveAssets();
            Debug.Log("QINGXI_WORLD " + report.status + " failures=" + report.failures.Count);
        }

        static void BuildTown(Transform world, TownWorld town)
        {
            var t = Node("Town", world).transform;
            var ground = Node("TownGround", t).transform;
            foreach (var part in new[] { "Town_Terrain", "Town_LakeBed", "Town_Water", "Town_Placeholders", "Town_Background" })
            {
                var g = PlaceBlenderModel("Town/" + part + ".fbx", ground, Vector3.zero, 0, 1, part);
                if (part == "Town_Terrain") AddMeshColliders(g, true);
                if (part == "Town_LakeBed") AddMeshColliders(g, false);   // area NotWalkable via markup
                if (part == "Town_Placeholders")
                    foreach (Transform child in g.GetComponentsInChildren<Transform>().Where(x => x.GetComponent<MeshFilter>() != null))
                    {
                        string n = child.name;
                        if (n.StartsWith("荷葉") || n.Contains("瀑布") || n.StartsWith("洞內暖光")) continue;
                        if (n.StartsWith("垂柳")) { var c = child.gameObject.AddComponent<CapsuleCollider>(); c.radius = .5f; c.height = 6; continue; }
                        if (n.StartsWith("燈籠柱") || n.StartsWith("殘柱") || n.StartsWith("廣場立柱")) { child.gameObject.AddComponent<BoxCollider>(); continue; }
                        var mc = child.gameObject.AddComponent<MeshCollider>(); mc.sharedMesh = child.GetComponent<MeshFilter>().sharedMesh;
                        if (n.StartsWith("水上棧道") || n.StartsWith("圓形石廣場") || n.StartsWith("廣場陣紋")) Walkable.Add(mc);
                    }
            }
            var assets = Node("TownAssets", t).transform;
            foreach (var p in town.placements)
            {
                var g = PlaceBlenderModel("Dondon/" + p.asset + ".fbx", assets, new Vector3(p.x, p.z, p.y), p.yaw_deg, p.scale, p.asset);
                Dress(g, p.asset);
            }
        }
        static readonly string[] BoxAssets = { "StarterHouse", "SectGrandHall", "ScriptureLibrary", "AlchemyHall", "HerbalStall", "MaterialShop", "Blacksmith", "NoticeBoard", "MossBoulderSet", "SpiritHerbGarden", "HerbPlanter", "SectGate" };
        static readonly string[] MeshAssets = { "MountainStoneStairs", "StoneArchBridge", "SpawnAltar", "LayeredCliff", "QCaveEntrance" };
        static void Dress(GameObject pivot, string asset)
        {
            if (BoxAssets.Contains(asset)) AddBox(pivot);
            else if (MeshAssets.Contains(asset)) AddMeshColliders(pivot, asset != "LayeredCliff");
            else if (asset == "CommonPine") AddCapsule(pivot, .45f, 5);
            else if (asset == "BambooClump") AddCapsule(pivot, .8f, 5);
            else if (asset.StartsWith("Q") && asset != "QPlayerMale" && asset != "QPlayerFemale" && asset != "QMountainRabbit") AddCapsule(pivot, .35f, 1.4f);
        }

        // town FBX orientation check against heights sampled in Blender by export_town_for_unity.py
        static void MappingCheck()
        {
            Physics.SyncTransforms();
            foreach (var (x, z, e) in new[] { (0f, 25f, 1.8f), (-118f, -106f, .016f), (-110f, -100f, -.215f) })
            {
                var hit = Physics.RaycastAll(new Vector3(x, 200, z), Vector3.down, 400).Where(h => h.collider.transform.IsChildOf(GameObject.Find("Town_Terrain").transform)).OrderBy(h => h.distance).FirstOrDefault();
                float got = hit.collider != null ? hit.point.y : float.NaN;
                report.mappingCheck.Add(x + "," + z + ": Blender " + e + " m, Unity " + got.ToString("0.000") + " m");
                if (float.IsNaN(got) || Mathf.Abs(got - e) > .3f) report.failures.Add("Town FBX mapping mismatch at " + x + "," + z);
            }
        }
        static float HuntGround(HuntLayout d, float x, float z) => d.hill.height *
            Mathf.Max(0, 1 - Mathf.Abs(x - d.hill.centerX) / d.hill.halfWidth) * Mathf.Max(0, 1 - Mathf.Abs(z - d.hill.centerZ) / d.hill.halfDepth);
        static Transform BuildHunt(Transform world, TownWorld town, HuntLayout d)
        {
            var root = Node("HuntArea_rotated180", world).transform;
            root.position = new Vector3(town.hunt.origin_xy[0], 0, town.hunt.origin_xy[1]); root.rotation = Quaternion.Euler(0, 180, 0);
            // ground: the Builder's 5 m grid with the tent hill
            int nx = Mathf.RoundToInt(d.bounds.width / d.bounds.grid), nz = Mathf.RoundToInt(d.bounds.depth / d.bounds.grid);
            var v = new Vector3[(nx + 1) * (nz + 1)]; var tri = new List<int>();
            for (int z = 0; z <= nz; z++) for (int x = 0; x <= nx; x++) { float px = x * d.bounds.grid, pz = z * d.bounds.grid; v[z * (nx + 1) + x] = new Vector3(px, HuntGround(d, px, pz), pz); }
            for (int z = 0; z < nz; z++) for (int x = 0; x < nx; x++) { int a = z * (nx + 1) + x, b = a + nx + 1; tri.AddRange(new[] { a, b, a + 1, a + 1, b, b + 1 }); }
            var mesh = new Mesh { name = "HuntGround" }; mesh.vertices = v; mesh.triangles = tri.ToArray(); mesh.RecalculateNormals(); mesh.RecalculateBounds();
            AssetDatabase.CreateAsset(mesh, Root + "/Generated/HuntGround.asset");
            var g = Node("HuntGround", root); g.AddComponent<MeshFilter>().sharedMesh = mesh; g.AddComponent<MeshRenderer>().sharedMaterial = Mat("HuntGround", new Color(.42f, .52f, .36f));
            Walkable.Add(g.AddComponent<MeshCollider>());
            var cliff = Mat("HuntCliff", new Color(.45f, .47f, .46f)); var water = Mat("HuntWater", new Color(.25f, .55f, .66f));
            var blockers = Node("SimplifiedColliders", root).transform;
            foreach (var o in d.obstacles)
            {
                // the south wall faces the town: leave a 28 m opening where the boardwalk enters the settlement exit
                if (o.name == "NavBlocker_BoundarySouth") { Wall(blockers, "NavBlocker_BoundarySouth_W", 0, 8, o, cliff); Wall(blockers, "NavBlocker_BoundarySouth_E", 36, 220, o, cliff); continue; }
                var box = GameObject.CreatePrimitive(PrimitiveType.Cube); box.name = o.name; box.transform.SetParent(blockers, false);
                box.transform.localPosition = o.position; box.transform.localScale = o.size;
                box.GetComponent<Renderer>().sharedMaterial = o.kind == "deepWater" ? water : cliff;
                if (o.kind == "boundary" || o.kind == "tree" || o.kind == "rock" || o.kind == "building") box.GetComponent<Renderer>().enabled = false;   // dressed below
            }
            var shallow = GameObject.CreatePrimitive(PrimitiveType.Cube); shallow.name = "ShallowWater_0.12m"; shallow.transform.SetParent(root, false);
            shallow.transform.localPosition = new Vector3(140, .06f, 45); shallow.transform.localScale = new Vector3(40, .12f, 30);
            UnityEngine.Object.DestroyImmediate(shallow.GetComponent<Collider>()); shallow.GetComponent<Renderer>().sharedMaterial = Mat("HuntShallow", new Color(.35f, .65f, .7f));

            // dressing with dondon handoff models (layout is Unity-style: model yaw given here directly in Blender terms)
            var dress = Node("Dressing", root).transform; var rng = new System.Random(20261025);
            foreach (var o in d.obstacles)
            {
                var p = new Vector3(o.position.x, o.position.y - o.size.y / 2, o.position.z);
                if (o.kind == "tree") PlaceBlenderModel("Dondon/CommonPine.fbx", dress, p, rng.Next(360), 1.1f, "Tree_" + o.name);
                if (o.kind == "rock") PlaceBlenderModel("Dondon/MossBoulderSet.fbx", dress, p, rng.Next(360), Mathf.Min(o.size.x, o.size.z) / 3f, "Rock_" + o.name);
                if (o.kind == "building") PlaceBlenderModel("Dondon/MaterialShop.fbx", dress, p, 180, .7f, "Stall_" + o.name);
            }
            PlaceBlenderModel("Dondon/NoticeBoard.fbx", dress, new Vector3(10, 0, 12), 200, 1, "NoticeBoard_SettlementExit");
            // forest and trail trees kept clear of routes, markers and boxes; capsule trunks so the route test sees them
            var routeSegs = d.routes.Where(r => r.name == "MainDiscovery" || r.name == "AlternativeReturn" || r.name == "HerdConnector").SelectMany(r => r.points.Zip(r.points.Skip(1), (a, b) => (a, b))).ToList();
            float SegDist(Vector3 p) => routeSegs.Min(s => { var ab = s.b - s.a; ab.y = 0; var ap = p - s.a; ap.y = 0; float t = Mathf.Clamp01(Vector3.Dot(ap, ab) / ab.sqrMagnitude); return (ap - ab * t).magnitude; });
            bool Clear(Vector3 p, float r) => SegDist(p) > 5f && d.markers.All(m => (new Vector3(m.position.x, 0, m.position.z) - p).magnitude > 3.5f)
                && d.obstacles.All(o => Mathf.Abs(p.x - o.position.x) > o.size.x / 2 + r + 2 || Mathf.Abs(p.z - o.position.z) > o.size.z / 2 + r + 2);
            int placed = 0;
            foreach (var z in d.zones.Where(z => z.name == "HerbForest" || z.name == "MountainTrail"))
                for (int k = 0; k < (z.name == "HerbForest" ? 120 : 60) && placed < 60; k++)
                {
                    var p = new Vector3(z.center.x + (float)(rng.NextDouble() - .5) * z.width, 0, z.center.z + (float)(rng.NextDouble() - .5) * z.depth);
                    bool bamboo = rng.NextDouble() < .35; if (!Clear(p, bamboo ? .8f : .45f)) continue;
                    p.y = HuntGround(d, p.x, p.z);
                    var tr = PlaceBlenderModel(bamboo ? "Dondon/BambooClump.fbx" : "Dondon/CommonPine.fbx", dress, p, rng.Next(360), .9f + (float)rng.NextDouble() * .4f, (bamboo ? "Bamboo_" : "Pine_") + placed++);
                    AddCapsule(tr, bamboo ? .8f : .45f, 5);
                }
            report.notes.Add("Hunt dressing: " + placed + " forest/trail trees with capsule trunks, kept 5 m from route centre lines and 3.5 m from markers.");
            foreach (var z in d.zones.Where(z => z.name == "RabbitSlope"))
                for (int k = 0; k < 14; k++)
                {
                    var p = new Vector3(z.center.x + (float)(rng.NextDouble() - .5) * z.width, 0, z.center.z + (float)(rng.NextDouble() - .5) * z.depth);
                    if (!Clear(p, .5f)) continue; p.y = HuntGround(d, p.x, p.z);
                    PlaceBlenderModel("Dondon/WildShrub.fbx", dress, p, rng.Next(360), 1, "Shrub_" + k);
                }
            // art batch v001: low grass, trampled grass on clues, stream banks (visual only)
            var art = RepoJson<ArtPlacement>("docs/graybox/qingxi-hunt/blender/art-preview/placement.json"); var artNode = Node("ArtV001", root).transform;
            foreach (var a in art.instances)
            {
                if (a.source.StartsWith("COL_") || a.@object.StartsWith("Lineup")) continue;
                float x = a.blender_xy[0], z = a.blender_xy[1];   // banks carry z_offset -0.30 so their 0.33 m back edge meets the flat ground
                PlaceBlenderModel("ArtV001/" + a.source + ".fbx", artNode, new Vector3(x, HuntGround(d, x, z) + a.z_offset, z), a.yaw_deg, a.scale, a.@object);
            }
            // stand-ins: rabbits on every respawn point, the two players on their spawns
            var actors = Node("StandIns", root).transform;
            foreach (var m in d.markers)
            {
                if (m.kind == "rabbit") PlaceBlenderModel("Dondon/QMountainRabbit.fbx", actors, m.position, rng.Next(360), 1, "Rabbit_" + m.name);
                if (m.name == "PlayerSpawn_01") PlaceBlenderModel("Dondon/QPlayerMale.fbx", actors, m.position, 90, 1, "Player1_StandIn");
                if (m.name == "PlayerSpawn_02") PlaceBlenderModel("Dondon/QPlayerFemale.fbx", actors, m.position, 90, 1, "Player2_StandIn");
            }
            var mk = Node("Markers", root).transform;
            foreach (var m in d.markers)
            {
                var e = Node(m.name, mk); e.transform.localPosition = m.position;
                if (m.kind == "boundary" || m.kind == "cameraBlocker") continue;
                var disc = GameObject.CreatePrimitive(PrimitiveType.Cylinder); disc.name = "Disc"; disc.transform.SetParent(e.transform, false);
                disc.transform.localPosition = Vector3.up * .05f; disc.transform.localScale = new Vector3(m.kind == "flee" ? 1.2f : 1.6f, .05f, m.kind == "flee" ? 1.2f : 1.6f);
                UnityEngine.Object.DestroyImmediate(disc.GetComponent<Collider>());
                disc.GetComponent<Renderer>().sharedMaterial = Mat("Marker_" + m.kind, m.kind == "player" ? new Color(.3f, .6f, 1) : m.kind == "rabbit" ? new Color(1, .75f, .2f) : m.kind == "flee" ? new Color(1, .35f, .25f) : m.kind == "herb" ? new Color(.3f, .9f, .4f) : m.kind == "clue" ? new Color(.9f, .9f, .85f) : new Color(.8f, .5f, .9f));
            }
            return root;
        }
        static void Wall(Transform parent, string name, float x0, float x1, HuntObstacle o, Material m)
        {
            var w = GameObject.CreatePrimitive(PrimitiveType.Cube); w.name = name; w.transform.SetParent(parent, false);
            w.transform.localPosition = new Vector3((x0 + x1) / 2, o.position.y, o.position.z); w.transform.localScale = new Vector3(x1 - x0, o.size.y, o.size.z);
            w.GetComponent<Renderer>().enabled = false;
        }
        static void Lighting(Transform world)
        {
            var sun = Node("Sun", world).AddComponent<Light>(); sun.type = LightType.Directional; sun.intensity = 1.25f; sun.shadows = LightShadows.Soft;
            sun.transform.rotation = Quaternion.Euler(50, -35, 0);
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(.62f, .7f, .78f); RenderSettings.ambientEquatorColor = new Color(.55f, .58f, .52f); RenderSettings.ambientGroundColor = new Color(.32f, .3f, .26f);
        }

        // ---------------------------------------------------------------- NavMesh
        sealed class NavInstance : IDisposable
        {
            NavMeshDataInstance inst; public NavInstance(NavMeshData d) { inst = NavMesh.AddNavMeshData(d); }
            public void Dispose() { inst.Remove(); }
        }
        static NavMeshData Bake(Transform world, Bounds bounds, HuntAgent a, float voxel, string profile, TownWorld town)
        {
            var markups = new List<NavMeshBuildMarkup>();
            var bed = world.GetComponentsInChildren<Transform>().FirstOrDefault(t => t.name == "Town_LakeBed");
            if (bed != null) markups.Add(new NavMeshBuildMarkup { root = bed, overrideArea = true, area = 1 });
            foreach (var t in world.GetComponentsInChildren<Transform>().Where(t => t.name.StartsWith("NavMeshPreview") || t.name == "RouteTest_Lines"))
                markups.Add(new NavMeshBuildMarkup { root = t, ignoreFromBuild = true });
            var sources = new List<NavMeshBuildSource>();
            NavMeshBuilder.CollectSources(bounds, ~0, NavMeshCollectGeometry.PhysicsColliders, 0, markups, sources);
            var s = NavMesh.GetSettingsByID(0);
            s.agentRadius = a.radius; s.agentHeight = a.height; s.agentSlope = a.maxSlope; s.agentClimb = a.stepHeight;
            s.overrideVoxelSize = true; s.voxelSize = voxel; s.minRegionArea = 1;
            var data = NavMeshBuilder.BuildNavMeshData(s, sources, bounds, Vector3.zero, Quaternion.identity);
            if (data == null) throw new InvalidOperationException(profile + " NavMesh bake failed");
            data.name = "QingxiWorld_" + profile; AssetDatabase.CreateAsset(data, Root + "/Generated/NavMesh_" + profile + ".asset");
            report.notes.Add(profile + " NavMesh: " + sources.Count + " collider sources, radius " + a.radius + " m, height " + a.height + " m, climb " + a.stepHeight + " m, slope " + a.maxSlope + " deg, voxel " + voxel + " m.");
            return data;
        }
        static int Preview(Transform world, string name, Color c, float lift)
        {
            var tri = NavMesh.CalculateTriangulation(); var m = new Mesh { name = name, indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
            m.vertices = tri.vertices.Select(v => v + Vector3.up * lift).ToArray(); m.triangles = tri.indices; m.RecalculateNormals();
            AssetDatabase.CreateAsset(m, Root + "/Generated/" + name + ".asset");
            var g = Node(name, world); g.AddComponent<MeshFilter>().sharedMesh = m; g.AddComponent<MeshRenderer>().sharedMaterial = Mat(name, c, true);
            return tri.indices.Length / 3;
        }
        static Vector3 SnapDown(Vector3 p)
        {
            var hits = Physics.RaycastAll(p + Vector3.up * 50, Vector3.down, 200).Where(h => Walkable.Contains(h.collider)).OrderBy(h => h.distance);
            return hits.Any() ? hits.First().point : p;
        }

        // ---------------------------------------------------------------- tests
        static PointCheck Point(string name, Vector3 p, HuntAgent a, string profile)
        {
            var pc = new PointCheck { name = name, profile = profile };
            pc.onNavMesh = NavMesh.SamplePosition(p, out var hit, 1f, NavMesh.AllAreas) && Mathf.Abs(hit.position.y - p.y) < .6f;
            pc.snapDistance = pc.onNavMesh ? Vector3.Distance(hit.position, p) : -1;
            pc.edgeClearance = pc.onNavMesh && NavMesh.FindClosestEdge(hit.position, out var edge, NavMesh.AllAreas) ? edge.distance : -1;
            var basePos = pc.onNavMesh ? hit.position : p;
            pc.blockers = Physics.OverlapCapsule(basePos + Vector3.up * (a.radius + .1f), basePos + Vector3.up * (a.height - a.radius), a.radius)
                .Where(c => !Walkable.Contains(c)).Select(c => c.name).Distinct().ToArray();
            pc.capsuleClear = pc.blockers.Length == 0; report.points.Add(pc);
            if (!pc.onNavMesh) report.failures.Add(profile + " point off NavMesh: " + name);
            if (!pc.capsuleClear) report.failures.Add(profile + " point blocked: " + name + " by " + string.Join(",", pc.blockers));
            return pc;
        }
        static NavMeshPath RoutePath(string profile, string from, Vector3 a, string to, Vector3 b, float speed, Transform lines, Color c, float width, bool mustPass = true)
        {
            var pc = new PathCheck { profile = profile, from = from, to = to, straight = Vector3.Distance(a, b) };
            var path = new NavMeshPath(); bool okA = NavMesh.SamplePosition(a, out var ha, 1.5f, NavMesh.AllAreas), okB = NavMesh.SamplePosition(b, out var hb, 1.5f, NavMesh.AllAreas);
            if (okA && okB && NavMesh.CalculatePath(ha.position, hb.position, NavMesh.AllAreas, path))
            {
                // A long single query can stop early on the search node limit (PathPartial although connected); continue from
                // where it stopped, up to three more legs. Reaching the target this way still proves one connected NavMesh region.
                var corners = path.corners.ToList(); int legs = 1;
                while (path.status == NavMeshPathStatus.PathPartial && legs < 4 && Vector3.Distance(corners.Last(), hb.position) > .5f)
                {
                    var next = new NavMeshPath();
                    if (!NavMesh.CalculatePath(corners.Last(), hb.position, NavMesh.AllAreas, next) || next.corners.Length < 2 || Vector3.Distance(next.corners.Last(), corners.Last()) < .5f) break;
                    corners.AddRange(next.corners.Skip(1)); path = next; legs++;
                }
                pc.status = path.status.ToString() + (legs > 1 ? " (" + legs + " legs)" : "");
                if (legs > 1 && path.status == NavMeshPathStatus.PathComplete) pc.status = "PathComplete";
                pc.legs = legs;
                for (int i = 1; i < corners.Count; i++) pc.length += Vector3.Distance(corners[i - 1], corners[i]);
                pc.seconds = pc.length / speed; pc.end = corners.Last();
                var lr = Node(profile + "_" + from + "_to_" + to, lines).AddComponent<LineRenderer>();
                lr.positionCount = corners.Count; lr.SetPositions(corners.Select(p => p + Vector3.up * .35f).ToArray());
                lr.startWidth = lr.endWidth = width; lr.sharedMaterial = Mat("Line_" + ColorUtility.ToHtmlStringRGB(c), c, true);
            }
            else pc.status = okA && okB ? "NoPath" : "EndpointOffNavMesh";
            pc.length = (float)Math.Round(pc.length, 2); pc.seconds = (float)Math.Round(pc.seconds, 1); pc.straight = (float)Math.Round(pc.straight, 2);
            report.paths.Add(pc);
            if (mustPass && pc.status != "PathComplete") report.failures.Add(profile + " path " + from + " -> " + to + ": " + pc.status);
            return path;
        }
        static void PlayerTests(HuntLayout d, Transform huntRoot, Dictionary<string, Vector3> M, Transform lines)
        {
            var a = d.player; var blue = new Color(.2f, .45f, 1f); var green = new Color(.2f, .8f, .5f); var purple = new Color(.7f, .35f, .9f);
            foreach (var n in new[] { "PlayerSpawn_Town", "PlayerSpawn_01", "PlayerSpawn_02", "SafeReturn_01", "Merchant_Material" }) Point(n, M[n], a, "player");
            float gap = Vector3.Distance(M["PlayerSpawn_01"], M["PlayerSpawn_02"]);
            if (gap < 2 * a.radius + .1f) report.failures.Add("Player spawns overlap");
            report.notes.Add("Player spawn spacing PlayerSpawn_01-02: " + gap.ToString("0.0") + " m.");
            // town <-> hunt
            RoutePath("player", "PlayerSpawn_Town", M["PlayerSpawn_Town"], "PlayerSpawn_01", M["PlayerSpawn_01"], a.speed, lines, purple, .5f);
            RoutePath("player", "PlayerSpawn_Town", M["PlayerSpawn_Town"], "Merchant_Material", M["Merchant_Material"], a.speed, lines, purple, .5f);
            var shop = GameObject.Find("TownAssets").transform.Cast<Transform>().FirstOrDefault(t => t.name == "MaterialShop");
            if (shop != null)   // market lifted above the lake 2026-10-25: reachable from at least one side, 1.5 m outside its box
            {
                var box = shop.GetComponent<BoxCollider>(); float r = Mathf.Max(box.size.x, box.size.z) * shop.lossyScale.x / 2 + 1.5f;
                var probe = new NavMeshPath(); NavMesh.SamplePosition(M["PlayerSpawn_Town"], out var hs, 1.5f, NavMesh.AllAreas);
                var c0 = shop.TransformPoint(box.center); c0.y = shop.position.y;   // probe at ground height, not the box centre
                var side = Enumerable.Range(0, 16).Select(k => c0 + Quaternion.Euler(0, k * 22.5f, 0) * Vector3.forward * r)
                    .FirstOrDefault(q => NavMesh.SamplePosition(q, out var hq, 2f, NavMesh.AllAreas) && NavMesh.CalculatePath(hs.position, hq.position, NavMesh.AllAreas, probe) && probe.status == NavMeshPathStatus.PathComplete);
                RoutePath("player", "PlayerSpawn_Town", M["PlayerSpawn_Town"], "TownMaterialShop_side", side == Vector3.zero ? shop.position : side, a.speed, lines, purple, .3f);
            }
            // hunt: spawn to every clue, herb, rabbit group and the return point
            foreach (var n in M.Keys.Where(k => k.StartsWith("TrailClue_") || k.StartsWith("HerbNode_") || k.EndsWith("01") && k.StartsWith("RabbitSpawn_")).OrderBy(k => k))
                RoutePath("player", "PlayerSpawn_01", M["PlayerSpawn_01"], n, M[n], a.speed, lines, blue, .25f);
            var clue = report.paths.First(p => p.to == "TrailClue_01");
            report.notes.Add("First clue from PlayerSpawn_01: " + clue.length + " m = " + clue.seconds + " s at " + a.speed + " m/s (target 20-30 s, shortest NavMesh path).");
            if (clue.seconds < 20 || clue.seconds > 30) report.failures.Add("First clue " + clue.seconds + " s on the shortest NavMesh path; brief wants 20-30 s");
            foreach (var ps in new[] { "PlayerSpawn_02" })   // the second spawn must not be a shortcut either
            {
                var q = RoutePath("player", ps, M[ps], "TrailClue_01", M["TrailClue_01"], a.speed, lines, blue, .25f);
                var r = report.paths.Last(); report.notes.Add("First clue from " + ps + ": " + r.length + " m = " + r.seconds + " s.");
                if (r.seconds < 20 || r.seconds > 30) report.failures.Add("First clue from " + ps + " " + r.seconds + " s; brief wants 20-30 s");
            }
            foreach (var g in new[] { "A01", "B01", "C01" }) RoutePath("player", "RabbitSpawn_" + g, M["RabbitSpawn_" + g], "SafeReturn_01", M["SafeReturn_01"], a.speed, lines, green, .4f);
            RoutePath("player", "SafeReturn_01", M["SafeReturn_01"], "PlayerSpawn_Town", M["PlayerSpawn_Town"], a.speed, lines, purple, .3f);
            // route chains: NavMesh length versus the layout polyline
            foreach (var r in d.routes.Where(r => r.name == "MainDiscovery" || r.name == "AlternativeReturn"))
            {
                float nav = 0, poly = 0;
                for (int i = 1; i < r.points.Length; i++)
                {
                    var p = RoutePath("player", r.name + "_" + (i - 1), huntRoot.TransformPoint(r.points[i - 1]), r.name + "_" + i, huntRoot.TransformPoint(r.points[i]), a.speed, lines, r.name == "MainDiscovery" ? blue : green, .5f);
                    nav += report.paths.Last().length; poly += Vector3.Distance(r.points[i - 1], r.points[i]);
                }
                report.notes.Add(r.name + ": NavMesh " + nav.ToString("0.0") + " m vs layout polyline " + poly.ToString("0.0") + " m = " + (nav / a.speed).ToString("0.0") + " s at " + a.speed + " m/s.");
            }
            // two CharacterControllers walking NavMesh corners
            Walk("Town spawn -> hunt merchant", M["PlayerSpawn_Town"], M["Merchant_Material"], a);
            Walk("Hunt spawns -> rabbit group A", M["PlayerSpawn_01"], M["RabbitSpawn_A01"], a);
            Walk("Rabbit group C -> safe return", M["RabbitSpawn_C01"], M["SafeReturn_01"], a);
        }
        static void Walk(string label, Vector3 from, Vector3 to, HuntAgent a)
        {
            var w = new WalkCheck { route = label, minimumSeparation = float.MaxValue }; var cc = new CharacterController[2]; var pos = new List<Vector3>[2];
            try
            {
                for (int i = 0; i < 2; i++)
                {
                    var start = from + (i == 0 ? Vector3.zero : new Vector3(1.6f, 0, 0));
                    NavMesh.SamplePosition(start, out var hs, 2f, NavMesh.AllAreas); var path = new NavMeshPath(); NavMesh.SamplePosition(to + (i == 0 ? Vector3.zero : new Vector3(1.6f, 0, 0)), out var ht, 2f, NavMesh.AllAreas);   // side by side at both ends
                    NavMesh.CalculatePath(hs.position, ht.position, NavMesh.AllAreas, path); pos[i] = path.corners.ToList();
                    if (path.status != NavMeshPathStatus.PathComplete || pos[i].Count < 2) { report.failures.Add("Walk has no complete path: " + label); report.walks.Add(w); return; }
                    var g = new GameObject("TempWalker_" + i) { hideFlags = HideFlags.HideAndDontSave }; g.transform.position = hs.position + Vector3.up * .1f;
                    cc[i] = g.AddComponent<CharacterController>(); cc[i].radius = a.radius; cc[i].height = a.height; cc[i].center = Vector3.up * a.height / 2;
                    cc[i].slopeLimit = a.maxSlope; cc[i].stepOffset = a.stepHeight; cc[i].skinWidth = .03f; cc[i].minMoveDistance = 0;
                }
                int[] idx = { 1, 1 }; float[] vy = { 0, 0 }; float[] stall = { 0, 0 }; Vector3[] last = { cc[0].transform.position, cc[1].transform.position }; float t = 0;
                for (int step = 0; step < 30000; step++)
                {
                    Physics.SyncTransforms(); t += .02f; bool done = true;
                    for (int i = 0; i < 2; i++)
                    {
                        if (idx[i] >= pos[i].Count) continue; done = false;
                        var target = pos[i][idx[i]]; var delta = target - cc[i].transform.position; delta.y = 0;
                        if (delta.magnitude < (idx[i] == pos[i].Count - 1 ? .6f : .3f)) { idx[i]++; continue; }
                        vy[i] = cc[i].isGrounded ? -2 : Mathf.Max(-20, vy[i] - 9.81f * .02f);
                        cc[i].Move(delta.normalized * a.speed * .02f + Vector3.up * vy[i] * .02f);
                        if (step % 50 == 0) { float moved = Vector3.Distance(cc[i].transform.position, last[i]); stall[i] = moved < .5f ? stall[i] + 1 : 0; w.longestStallSeconds = Mathf.Max(w.longestStallSeconds, stall[i]); last[i] = cc[i].transform.position; }
                    }
                    w.minimumSeparation = Mathf.Min(w.minimumSeparation, Vector3.Distance(cc[0].transform.position, cc[1].transform.position));
                    if (done) { w.completed = true; break; }
                    if (stall[0] > 6 || stall[1] > 6) break;
                }
                w.simulatedSeconds = (float)Math.Round(t, 1);
                w.finalError = (float)Math.Round(Mathf.Max(Vector3.Distance(cc[0].transform.position, pos[0].Last()), Vector3.Distance(cc[1].transform.position, pos[1].Last())), 2);
                w.minimumSeparation = (float)Math.Round(w.minimumSeparation, 2);
                if (!w.completed || w.finalError > 1.5f) report.failures.Add("Walk did not finish: " + label);
            }
            finally { foreach (var c in cc) if (c != null) UnityEngine.Object.DestroyImmediate(c.gameObject); }
            report.walks.Add(w);
        }
        static void RabbitTests(HuntLayout d, Dictionary<string, Vector3> M, Transform lines)
        {
            var a = d.rabbit; var orange = new Color(1f, .5f, .1f); const float Leash = 28f, FleeSpeed = 5f;
            foreach (var m in d.markers.Where(m => m.kind == "rabbit" || m.kind == "flee")) Point(m.name, M[m.name], a, "rabbit");
            foreach (var g in new[] { "A", "B", "C" })
            {
                var nodes = d.markers.Where(m => m.group == g).Select(m => m.name).ToList(); var gc = new GroupCheck { group = g, allPairsConnected = true, fleeWithinLeash = true };
                for (int i = 0; i < nodes.Count; i++) for (int j = i + 1; j < nodes.Count; j++)
                    {
                        RoutePath("rabbit", nodes[i], M[nodes[i]], nodes[j], M[nodes[j]], FleeSpeed, lines, orange, .18f);
                        var p = report.paths.Last(); if (p.status != "PathComplete") gc.allPairsConnected = false;
                        if (nodes[i].StartsWith("RabbitSpawn") && nodes[j].StartsWith("RabbitFlee")) { gc.longestFleePath = Mathf.Max(gc.longestFleePath, p.length); gc.longestFleeSeconds = Mathf.Max(gc.longestFleeSeconds, p.seconds); if (p.straight > Leash) gc.fleeWithinLeash = false; }
                    }
                if (!gc.fleeWithinLeash) report.failures.Add("Rabbit group " + g + " has a flee point beyond the " + Leash + " m leash");
                report.rabbitGroups.Add(gc);
            }
            // respawn: hunting.json respawns a rabbit after 90 s at its spawn point, so the spawn markers are the respawn points
            var spawns = d.markers.Where(m => m.kind == "rabbit").ToList(); float min = float.MaxValue, minP = float.MaxValue;
            for (int i = 0; i < spawns.Count; i++)
            {
                for (int j = i + 1; j < spawns.Count; j++) min = Mathf.Min(min, Vector3.Distance(M[spawns[i].name], M[spawns[j].name]));
                foreach (var ps in new[] { "PlayerSpawn_01", "PlayerSpawn_02", "PlayerSpawn_Town", "SafeReturn_01" }) minP = Mathf.Min(minP, Vector3.Distance(M[spawns[i].name], M[ps]));
                var eye = M["PlayerSpawn_01"] + Vector3.up * 1.4f; var target = M[spawns[i].name] + Vector3.up * .4f;
                if (!Physics.Linecast(eye, target, out _)) report.respawnVisibleFromPlayerSpawn.Add(spawns[i].name);
            }
            report.minRabbitRespawnSpacing = (float)Math.Round(min, 2); report.minRespawnToPlayerSpawn = (float)Math.Round(minP, 1);
            if (min < 8) report.failures.Add("Rabbit respawn points closer than 8 m");
            if (minP < 30) report.failures.Add("Rabbit respawn point within 30 m of a player spawn");
        }

        // ---------------------------------------------------------------- play mode: first-person walker and fleeing rabbits
        static float YawTo(Vector3 a, Vector3 b) => Mathf.Atan2(b.x - a.x, b.z - a.z) * Mathf.Rad2Deg;
        static void AddPlayer(Transform world, Transform hunt, HuntLayout d, Dictionary<string, Vector3> M, NavMeshData rabbitData)
        {
            Vector3 H(float x, float z) => SnapDown(hunt.TransformPoint(new Vector3(x, 0, z)));
            var spots = new List<(string, Vector3, float)>
            {
                ("小鎮廣場", M["PlayerSpawn_Town"], 180),
                ("棧道入口", SnapDown(new Vector3(-108, 30, -100)), YawTo(new Vector3(-108, 0, -100), M["PlayerSpawn_01"])),
                ("狩獵區出生點", M["PlayerSpawn_01"], YawTo(M["PlayerSpawn_01"], hunt.TransformPoint(new Vector3(50, 0, 20)))),
                ("山道", H(62, 38), YawTo(hunt.TransformPoint(new Vector3(62, 0, 38)), hunt.TransformPoint(new Vector3(62, 0, 56)))),
                ("採藥林", H(45, 100), YawTo(hunt.TransformPoint(new Vector3(45, 0, 100)), hunt.TransformPoint(new Vector3(59, 0, 105)))),
                ("兔坡", H(108, 86), YawTo(hunt.TransformPoint(new Vector3(108, 0, 86)), M["RabbitSpawn_A01"])),
                ("淺灘", H(155, 56), YawTo(hunt.TransformPoint(new Vector3(155, 0, 56)), hunt.TransformPoint(new Vector3(155, 0, 40)))),
                ("安全回村", M["SafeReturn_01"], YawTo(M["SafeReturn_01"], M["PlayerSpawn_01"])),
            };
            var player = new GameObject("Player_FirstPerson"); player.transform.SetParent(world, false);
            player.transform.position = spots[0].Item2 + Vector3.up * .05f; player.transform.rotation = Quaternion.Euler(0, spots[0].Item3, 0);
            var cc = player.AddComponent<CharacterController>(); cc.radius = .35f; cc.height = 1.4f; cc.center = Vector3.up * .7f; cc.slopeLimit = 35; cc.stepOffset = .3f; cc.skinWidth = .03f;
            var camGo = new GameObject("PlayerCamera") { tag = "MainCamera" }; camGo.transform.SetParent(player.transform, false); camGo.transform.localPosition = Vector3.up * 1.2f;
            var cam = camGo.AddComponent<Camera>(); cam.fieldOfView = 70; cam.nearClipPlane = .05f; cam.farClipPlane = 1500; camGo.AddComponent<AudioListener>();
            var body = PlaceBlenderModel("Dondon/QPlayerMale.fbx", player.transform, Vector3.zero, 180, 1, "Body_QPlayerMale");
            var fp = player.AddComponent<QingxiWorld.QingxiFirstPerson>(); fp.cam = cam; fp.body = body; fp.rabbitNavMesh = rabbitData;
            fp.spotNames = spots.Select(s => s.Item1).ToArray(); fp.spotPositions = spots.Select(s => s.Item2).ToArray(); fp.spotYaws = spots.Select(s => s.Item3).ToArray();
            fp.huntRoot = hunt; fp.zoneLabels = d.zones.Select(z => z.label).ToArray(); fp.zoneRects = d.zones.Select(z => new Vector4(z.center.x, z.center.z, z.width, z.depth)).ToArray();
            var poi = hunt.Find("Markers").Cast<Transform>().Where(t => !t.name.StartsWith("CameraBlocker") && !t.name.StartsWith("AreaBoundary")).ToList();
            poi.Add(GameObject.Find("PlayerSpawn_Town").transform); fp.pointsOfInterest = poi.ToArray();
            foreach (var m in d.markers.Where(m => m.kind == "rabbit"))
            {
                var stand = hunt.Find("StandIns/Rabbit_" + m.name); var r = stand.gameObject.AddComponent<QingxiWorld.QingxiRabbit>(); r.spawnName = m.name.Replace("RabbitSpawn_", "");
                r.fleePoints = d.markers.Where(f => f.kind == "flee" && f.group == m.group).Select(f => M[f.name]).ToArray();
            }
            report.notes.Add("Play mode: Player_FirstPerson (CharacterController r 0.35 h 1.4, eye 1.2 m, 4 m/s) with " + spots.Count + " teleport spots; 6 rabbit stand-ins flee on the rabbit NavMesh and respawn after 90 s.");
        }

        // ---------------------------------------------------------------- screenshots
        static void Screens(Transform world, Transform hunt)
        {
            var navP = GameObject.Find("NavMeshPreview_Player"); var navR = GameObject.Find("NavMeshPreview_Rabbit"); var lines = GameObject.Find("RouteTest_Lines");
            void Shot(string name, Vector3 pos, Vector3 look, bool ortho, float size, bool overlays, int w = 1600, int h = 900)
            {
                navP.SetActive(overlays); navR.SetActive(overlays); lines.SetActive(true);
                var cam = new GameObject("ShotCam").AddComponent<Camera>(); cam.transform.position = pos; cam.transform.LookAt(look);
                cam.orthographic = ortho; cam.orthographicSize = size; cam.fieldOfView = 50; cam.nearClipPlane = .3f; cam.farClipPlane = 1500;
                cam.clearFlags = CameraClearFlags.SolidColor; cam.backgroundColor = new Color(.72f, .8f, .86f);
                var rt = new RenderTexture(w, h, 24) { antiAliasing = 4 }; cam.targetTexture = rt; cam.Render(); RenderTexture.active = rt;
                var tex = new Texture2D(w, h, TextureFormat.RGB24, false); tex.ReadPixels(new Rect(0, 0, w, h), 0, 0); tex.Apply();
                File.WriteAllBytes(Path.Combine(Reports, "screens", name + ".png"), tex.EncodeToPNG());
                RenderTexture.active = null; cam.targetTexture = null; UnityEngine.Object.DestroyImmediate(rt); UnityEngine.Object.DestroyImmediate(tex); UnityEngine.Object.DestroyImmediate(cam.gameObject);
                report.screenshots.Add("screens/" + name + ".png");
            }
            Vector3 H(float x, float y, float z) => hunt.TransformPoint(new Vector3(x, y, z));
            Shot("01_world_birdseye_routes", new Vector3(-50, 600, -30), new Vector3(-50, 0, -29.9f), true, 265, true, 1800, 1800);
            Shot("02_town_plaza", new Vector3(-6, 14, -18), new Vector3(0, 3, 30), false, 0, false);
            Shot("03_town_to_hunt_boardwalk", new Vector3(-70, 18, -70), new Vector3(-118, 0, -114), false, 0, true);
            Shot("04_hunt_settlement_exit", H(40, 9, 2), H(18, 0, 24), false, 0, true);
            Shot("05_hunt_meadow_flee_routes", H(150, 70, 60), H(150, 0, 112), false, 0, true);
            Shot("06_hunt_birdseye_routes", H(110, 400, 80), H(110, 0, 80.1f), true, 92, true, 1800, 1300);
            Shot("07_herb_forest", H(30, 10, 82), H(55, 1, 100), false, 0, false);
            Shot("08_market_navmesh", new Vector3(60, 300, -40), new Vector3(60, 0, -39.9f), true, 45, true, 1600, 1200);
            navP.SetActive(true); navR.SetActive(true);
        }
    }
}
