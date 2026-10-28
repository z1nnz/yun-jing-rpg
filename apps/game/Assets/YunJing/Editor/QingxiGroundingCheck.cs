using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.AI;

namespace YunJing.Editor
{
    /// <summary>
    /// Acceptance checks for the Qingxi terrain rework, run against a generated scene:
    /// placed models resting on the ground, no grass inside road corridors, walkable road grades,
    /// overlapping flat road meshes (the z-fighting the old block roads produce), and a walk between
    /// named checkpoints. Reads a config from tools/qingxi-terrain/checks/*.json; writes a report to
    /// artifacts/terrain-check/. Does not modify the scene.
    /// </summary>
    public static class QingxiGroundingCheck
    {
        [Serializable] public class Road { public string id; public float width = 3f; public float[] points = new float[0]; }
        [Serializable] public class Checkpoint { public string name; public string target; public float x, y, z; }
        [Serializable]
        public class Config
        {
            public string scene;
            public string navMeshAsset;
            public float groundTolerance = .05f;   // a base more than this above the ground is floating
            public float buriedLimit = .5f;        // sinking deeper than this is reported as a warning
            public float maxWalkSlope = 35f;       // CharacterController.slopeLimit used by the walkers
            public float comfortSlope = 20f;
            public float stepHeight = .3f;
            public float roadEdgeAllowance = .15f; // grass may lean this far into the road edge
            public string grassPattern = "grass|fern|flower|reed|clump|草";
            public string roadMeshPattern = "road|path|trail|approach|路";
            public string ignorePattern = "^$";
            public int minPlacedModels;
            public Road[] roads = new Road[0];
            public Checkpoint[] checkpoints = new Checkpoint[0];
            public string[] route = new string[0];
        }

        class Report
        {
            public readonly List<string> failures = new(), warnings = new(), passes = new();
            public void Fail(string s) => failures.Add(s);
            public void Warn(string s) => warnings.Add(s);
            public void Pass(string s) => passes.Add(s);
        }

        static string ProjectRoot => Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", ".."));

        public static void Run()
        {
            string configPath = Arg("-groundingConfig") ?? Path.Combine(ProjectRoot, "tools/qingxi-terrain/checks/qingxi-world-preview.json");
            int failures = RunWith(configPath);
            if (Application.isBatchMode) EditorApplication.Exit(failures > 0 ? 1 : 0);
        }

        [MenuItem("Yun Jing/Qingxi/Check Terrain Grounding")]
        static void RunFromMenu() => RunWith(Path.Combine(ProjectRoot, "tools/qingxi-terrain/checks/qingxi-world-preview.json"));

        public static int RunWith(string configPath)
        {
            var config = JsonUtility.FromJson<Config>(File.ReadAllText(configPath));
            if (!string.IsNullOrEmpty(config.scene)) EditorSceneManager.OpenScene(config.scene, OpenSceneMode.Single);
            Physics.SyncTransforms();
            var report = new Report();
            CheckGrounding(config, report);
            CheckGrass(config, report);
            CheckRoadGrades(config, report);
            CheckRoadMeshOverlap(config, report);
            var navMesh = string.IsNullOrEmpty(config.navMeshAsset) ? null : AssetDatabase.LoadAssetAtPath<NavMeshData>(config.navMeshAsset);
            if (!string.IsNullOrEmpty(config.navMeshAsset) && navMesh == null)
                report.Fail("找不到地形路線 NavMesh：" + config.navMeshAsset);
            if (navMesh != null)
            {
                var instance = NavMesh.AddNavMeshData(navMesh);
                try { CheckRoute(config, report); }
                finally { if (instance.valid) instance.Remove(); }
            }
            else CheckRoute(config, report);
            Write(configPath, config, report);
            return report.failures.Count;
        }

        // Highest non-trigger collider under (x, z), skipping colliders that belong to `self`.
        static bool Ground(float x, float z, Transform self, out float height)
        {
            height = float.NegativeInfinity;
            foreach (var hit in Physics.RaycastAll(new Vector3(x, 500f, z), Vector3.down, 1000f, ~0, QueryTriggerInteraction.Ignore))
            {
                if (self != null && hit.collider.transform.IsChildOf(self)) continue;
                height = Mathf.Max(height, hit.point.y);
            }
            return !float.IsNegativeInfinity(height);
        }

        static bool VisualBounds(GameObject go, out Bounds bounds)
        {
            bounds = default;
            bool any = false;
            foreach (var r in go.GetComponentsInChildren<Renderer>())
            {
                if (!r.enabled || r is ParticleSystemRenderer || r is LineRenderer) continue;
                if (!any) { bounds = r.bounds; any = true; } else bounds.Encapsulate(r.bounds);
            }
            return any;
        }

        static IEnumerable<GameObject> PlacedModels(Config config)
        {
            var ignore = new Regex(config.ignorePattern, RegexOptions.IgnoreCase);
            foreach (var root in EditorSceneManager.GetActiveScene().GetRootGameObjects())
            foreach (var t in root.GetComponentsInChildren<Transform>(true))
                if (t.gameObject.activeInHierarchy && PrefabUtility.IsOutermostPrefabInstanceRoot(t.gameObject) && !ignore.IsMatch(t.name))
                    yield return t.gameObject;
        }

        static void CheckGrounding(Config config, Report report)
        {
            int checkedCount = 0;
            foreach (var go in PlacedModels(config))
            {
                if (!VisualBounds(go, out var b)) continue;
                checkedCount++;
                // Z-up FBX roots carry an import rotation; replacing it with a yaw-only rotation lays the model on its side.
                var source = PrefabUtility.GetCorrespondingObjectFromSource(go);
                float tilt = source != null ? Vector3.Angle(go.transform.rotation * Quaternion.Inverse(source.transform.localRotation) * Vector3.up, Vector3.up) : 0;
                if (tilt > 1f) report.Fail($"躺倒：{go.name} 的根節點匯入旋轉被覆蓋，模型傾斜 {tilt:0}°（{Fmt(go.transform.position)}）");
                var samples = new List<float>();
                foreach (var (fx, fz) in new[] { (0f, 0f), (-.35f, -.35f), (.35f, -.35f), (-.35f, .35f), (.35f, .35f) })
                    if (Ground(b.center.x + fx * b.size.x, b.center.z + fz * b.size.z, go.transform, out var h)) samples.Add(h);
                if (samples.Count == 0) { report.Fail($"懸空：{go.name} 底下沒有任何地面（{Fmt(b.center)}）"); continue; }
                float gap = b.min.y - samples.Max();
                if (gap > config.groundTolerance) report.Fail($"懸空：{go.name} 底部比腳印內最高的地面還高 {gap:0.00} m（{Fmt(b.center)}）");
                else if (b.min.y < samples.Min() - config.buriedLimit) report.Warn($"埋太深：{go.name} 底部低於地面 {samples.Min() - b.min.y:0.00} m（{Fmt(b.center)}）");
            }
            if (checkedCount < config.minPlacedModels)
                report.Fail($"擺放模型只載入 {checkedCount} 件，低於要求的 {config.minPlacedModels} 件；請先取回 Git LFS 素材");
            else report.Pass($"檢查了 {checkedCount} 個擺放模型的接地");
        }

        static float DistanceToRoad(Vector2 p, Road road, out bool inside)
        {
            float best = float.PositiveInfinity;
            for (int i = 0; i + 3 < road.points.Length; i += 2)
            {
                var a = new Vector2(road.points[i], road.points[i + 1]);
                var c = new Vector2(road.points[i + 2], road.points[i + 3]);
                var ab = c - a;
                float t = ab.sqrMagnitude < 1e-6f ? 0 : Mathf.Clamp01(Vector2.Dot(p - a, ab) / ab.sqrMagnitude);
                best = Mathf.Min(best, Vector2.Distance(p, a + ab * t));
            }
            inside = best < road.width * .5f;
            return best;
        }

        static string RoadAt(Config config, Vector2 p, float allowance)
        {
            foreach (var road in config.roads)
                if (DistanceToRoad(p, road, out _) < road.width * .5f - allowance) return road.id;
            return null;
        }

        static void CheckGrass(Config config, Report report)
        {
            var grass = new Regex(config.grassPattern, RegexOptions.IgnoreCase);
            int instances = 0, inRoad = 0;
            foreach (var r in UnityEngine.Object.FindObjectsByType<Renderer>(FindObjectsSortMode.None))
            {
                if (!r.enabled || !grass.IsMatch(r.name) && !grass.IsMatch(r.transform.parent ? r.transform.parent.name : "")) continue;
                instances++;
                var c = r.bounds.center;
                string road = RoadAt(config, new Vector2(c.x, c.z), config.roadEdgeAllowance);
                if (road != null && ++inRoad <= 20) report.Fail($"路上有草：{r.name} 在道路 {road} 內（{Fmt(c)}）");
            }
            int detailCells = 0, detailInRoad = 0;
            foreach (var terrain in Terrain.activeTerrains)
            {
                var data = terrain.terrainData;
                for (int layer = 0; layer < data.detailPrototypes.Length; layer++)
                {
                    var map = data.GetDetailLayer(0, 0, data.detailWidth, data.detailHeight, layer);
                    for (int y = 0; y < data.detailHeight; y++)
                    for (int x = 0; x < data.detailWidth; x++)
                    {
                        if (map[y, x] == 0) continue;
                        detailCells++;
                        var world = terrain.transform.position + new Vector3((x + .5f) / data.detailWidth * data.size.x, 0, (y + .5f) / data.detailHeight * data.size.z);
                        string road = RoadAt(config, new Vector2(world.x, world.z), config.roadEdgeAllowance);
                        if (road != null && ++detailInRoad <= 20) report.Fail($"路上有草：地形細節層 {layer} 在道路 {road} 內（{Fmt(world)}）");
                    }
                }
            }
            if (inRoad > 20 || detailInRoad > 20) report.Fail($"路上有草：共 {inRoad} 個物件、{detailInRoad} 格地形細節（上面只列前 20 筆）");
            report.Pass($"檢查了 {instances} 個草類物件與 {detailCells} 格地形細節");
        }

        static void CheckRoadGrades(Config config, Report report)
        {
            foreach (var road in config.roads)
            {
                float worstGrade = 0, worstCross = 0; Vector3 worstAt = default; int missing = 0;
                for (int i = 0; i + 3 < road.points.Length; i += 2)
                {
                    var a = new Vector2(road.points[i], road.points[i + 1]);
                    var c = new Vector2(road.points[i + 2], road.points[i + 3]);
                    var dir = (c - a).normalized; var side = new Vector2(-dir.y, dir.x) * road.width * .4f;
                    int steps = Mathf.Max(1, Mathf.CeilToInt(Vector2.Distance(a, c) / .5f));
                    float? previous = null;
                    for (int s = 0; s <= steps; s++)
                    {
                        var p = Vector2.Lerp(a, c, s / (float)steps);
                        if (!Ground(p.x, p.y, null, out var h)) { missing++; previous = null; continue; }
                        if (previous.HasValue)
                        {
                            float grade = Mathf.Atan2(Mathf.Abs(h - previous.Value), Vector2.Distance(a, c) / steps) * Mathf.Rad2Deg;
                            if (grade > worstGrade) { worstGrade = grade; worstAt = new Vector3(p.x, h, p.y); }
                        }
                        previous = h;
                        var l = p + side; var r = p - side;
                        if (Ground(l.x, l.y, null, out var hl) && Ground(r.x, r.y, null, out var hr))
                            worstCross = Mathf.Max(worstCross, Mathf.Atan2(Mathf.Abs(hl - hr), road.width * .8f) * Mathf.Rad2Deg);
                    }
                }
                if (missing > 0) report.Fail($"道路 {road.id}：{missing} 個取樣點下方沒有地面");
                if (worstGrade > config.maxWalkSlope) report.Fail($"道路 {road.id}：最陡 {worstGrade:0}°，超過可走坡度 {config.maxWalkSlope:0}°（{Fmt(worstAt)}）");
                else if (worstGrade > config.comfortSlope) report.Warn($"道路 {road.id}：最陡 {worstGrade:0}°，可走但偏陡（{Fmt(worstAt)}）");
                if (worstCross > config.comfortSlope) report.Warn($"道路 {road.id}：橫向傾斜 {worstCross:0}°，路面左右高差偏大");
                report.Pass($"道路 {road.id}：縱坡最大 {worstGrade:0.0}°、橫坡最大 {worstCross:0.0}°");
            }
        }

        // Flat road-like meshes stacked on each other within a few centimetres flicker and spike through.
        static void CheckRoadMeshOverlap(Config config, Report report)
        {
            var pattern = new Regex(config.roadMeshPattern, RegexOptions.IgnoreCase);
            var flats = UnityEngine.Object.FindObjectsByType<Renderer>(FindObjectsSortMode.None)
                .Where(r => r.enabled && (pattern.IsMatch(r.name) || r.transform.parent && pattern.IsMatch(r.transform.parent.name)))
                .Where(r => r.bounds.size.y < .5f && r.bounds.size.x * r.bounds.size.z > 1f)
                .ToList();
            int pairs = 0;
            for (int i = 0; i < flats.Count; i++)
            for (int j = i + 1; j < flats.Count; j++)
            {
                Bounds a = flats[i].bounds, b = flats[j].bounds;
                float ox = Mathf.Min(a.max.x, b.max.x) - Mathf.Max(a.min.x, b.min.x);
                float oz = Mathf.Min(a.max.z, b.max.z) - Mathf.Max(a.min.z, b.min.z);
                if (ox <= .05f || oz <= .05f || Mathf.Abs(a.max.y - b.max.y) > .06f) continue;
                if (++pairs <= 20) report.Warn($"路面疊面：{flats[i].name} 與 {flats[j].name} 重疊 {ox:0.0}×{oz:0.0} m，頂面高差 {Mathf.Abs(a.max.y - b.max.y) * 100:0} cm");
            }
            report.Pass($"檢查了 {flats.Count} 個平面路面網格，{pairs} 組可能疊面");
        }

        static bool Resolve(Checkpoint cp, out Vector3 position)
        {
            position = new Vector3(cp.x, cp.y, cp.z);
            if (string.IsNullOrEmpty(cp.target)) return true;
            var go = GameObject.Find(cp.target);
            if (go == null) return false;
            position = go.transform.position;
            return true;
        }

        // Straight-line walk between consecutive checkpoints with the player capsule (r .35 m, h 1.4 m).
        static void CheckRoute(Config config, Report report)
        {
            var points = new List<(string name, Vector3 pos)>();
            foreach (var name in config.route)
            {
                var cp = config.checkpoints.FirstOrDefault(c => c.name == name);
                if (cp == null || !Resolve(cp, out var pos)) { report.Fail($"路線：找不到檢查點 {name}"); return; }
                points.Add((name, pos));
            }
            bool navMesh = NavMesh.CalculateTriangulation().vertices.Length > 0;
            for (int i = 0; i + 1 < points.Count; i++)
            {
                var (fromName, from) = points[i]; var (toName, to) = points[i + 1];
                string leg = $"{fromName} → {toName}";
                int steps = Mathf.Max(1, Mathf.CeilToInt(Vector2.Distance(new Vector2(from.x, from.z), new Vector2(to.x, to.z)) / .4f));
                float? previous = null; string problem = null;
                for (int s = 0; s <= steps && problem == null; s++)
                {
                    var p = Vector3.Lerp(from, to, s / (float)steps);
                    if (!Ground(p.x, p.z, null, out var h)) { problem = $"沒有地面（{Fmt(p)}）"; break; }
                    if (previous.HasValue)
                    {
                        float rise = h - previous.Value, run = Vector3.Distance(from, to) / steps;
                        if (rise > config.stepHeight && Mathf.Atan2(rise, run) * Mathf.Rad2Deg > config.maxWalkSlope) problem = $"一步高差 {rise:0.00} m 走不上去（{Fmt(new Vector3(p.x, h, p.z))}）";
                    }
                    var bottom = new Vector3(p.x, h + .35f + config.stepHeight, p.z);
                    var top = new Vector3(p.x, h + 1.4f - .35f, p.z);
                    if (problem == null && Physics.CheckCapsule(bottom, Vector3.Max(top, bottom), .3f, ~0, QueryTriggerInteraction.Ignore))
                    {
                        var blocker = Physics.OverlapCapsule(bottom, Vector3.Max(top, bottom), .3f, ~0, QueryTriggerInteraction.Ignore).FirstOrDefault();
                        problem = $"被 {(blocker ? blocker.name : "碰撞體")} 擋住（{Fmt(new Vector3(p.x, h, p.z))}）";
                    }
                    previous = h;
                }
                if (problem != null) report.Fail($"路線 {leg}：{problem}");
                else report.Pass($"路線 {leg}：直線試走通過");
                if (!navMesh) continue;
                var path = new NavMeshPath();
                bool snapped = NavMesh.SamplePosition(from, out var a, 3f, NavMesh.AllAreas) & NavMesh.SamplePosition(to, out var b, 3f, NavMesh.AllAreas);
                if (!snapped || !NavMesh.CalculatePath(a.position, b.position, NavMesh.AllAreas, path) || path.status != NavMeshPathStatus.PathComplete)
                    report.Fail($"路線 {leg}：NavMesh 找不到完整路徑");
                else report.Pass($"路線 {leg}：NavMesh 路徑長 {PathLength(path):0.0} m");
            }
            if (!navMesh && points.Count > 1) report.Warn("場景沒有烘焙 NavMesh，路線只做了直線膠囊試走");
        }

        static float PathLength(NavMeshPath path)
        {
            float length = 0;
            for (int i = 1; i < path.corners.Length; i++) length += Vector3.Distance(path.corners[i - 1], path.corners[i]);
            return length;
        }

        static void Write(string configPath, Config config, Report report)
        {
            string dir = Path.Combine(ProjectRoot, "artifacts", "terrain-check");
            Directory.CreateDirectory(dir);
            string name = Path.GetFileNameWithoutExtension(configPath);
            var md = new StringBuilder();
            md.AppendLine($"# 地形驗收：{name}").AppendLine();
            md.AppendLine($"場景 `{config.scene}`；{DateTime.Now:yyyy-MM-dd HH:mm}。失敗 {report.failures.Count}、警告 {report.warnings.Count}、通過 {report.passes.Count}。").AppendLine();
            void Section(string title, List<string> lines) { if (lines.Count == 0) return; md.AppendLine($"## {title}").AppendLine(); foreach (var l in lines) md.AppendLine("- " + l); md.AppendLine(); }
            Section("失敗", report.failures); Section("警告", report.warnings); Section("通過", report.passes);
            File.WriteAllText(Path.Combine(dir, name + ".md"), md.ToString(), new UTF8Encoding(false));
            Debug.Log($"[QingxiGroundingCheck] {name}: {report.failures.Count} failures, {report.warnings.Count} warnings\n" + md);
        }

        /// <summary>Measures the FBX models Unity actually uses, so the Node inventory can cover files that have no GLB export.</summary>
        public static void InventoryModels()
        {
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var rows = new List<string>();
            foreach (var guid in AssetDatabase.FindAssets("t:Model", new[] { "Assets/YunJing/Models" }).OrderBy(AssetDatabase.GUIDToAssetPath))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                if (!path.EndsWith(".fbx", StringComparison.OrdinalIgnoreCase) || Regex.IsMatch(path, @"[-_]lod\d\.fbx$", RegexOptions.IgnoreCase)) continue;
                var asset = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (asset == null) continue;
                var go = (GameObject)PrefabUtility.InstantiatePrefab(asset);
                // Keep the importer's root rotation (Z-up FBX roots carry -90° X); only the position is reset.
                go.transform.position = Vector3.zero;
                if (VisualBounds(go, out var b))
                {
                    int tris = go.GetComponentsInChildren<MeshFilter>().Where(f => f.sharedMesh).Sum(f => (int)(f.sharedMesh.triangles.Length / 3));
                    int mats = go.GetComponentsInChildren<Renderer>().SelectMany(r => r.sharedMaterials).Where(m => m).Distinct().Count();
                    rows.Add(string.Format(System.Globalization.CultureInfo.InvariantCulture,
                        "  {{\"path\": \"{0}\", \"size\": [{1:0.###}, {2:0.###}, {3:0.###}], \"bottom\": {4:0.###}, \"centreOffset\": {5:0.###}, \"triangles\": {6}, \"materials\": {7}}}",
                        path, b.size.x, b.size.y, b.size.z, b.min.y, new Vector2(b.center.x, b.center.z).magnitude, tris, mats));
                }
                UnityEngine.Object.DestroyImmediate(go);
            }
            string output = Path.Combine(ProjectRoot, "tools/qingxi-terrain/unity-models.json");
            File.WriteAllText(output, "[\n" + string.Join(",\n", rows) + "\n]\n", new UTF8Encoding(false));
            Debug.Log($"[QingxiGroundingCheck] measured {rows.Count} FBX models -> {output}");
            if (Application.isBatchMode) EditorApplication.Exit(0);
        }

        static string Fmt(Vector3 v) => $"{v.x:0.0}, {v.y:0.0}, {v.z:0.0}";

        static string Arg(string name)
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, name);
            return i >= 0 && i + 1 < args.Length ? args[i + 1] : null;
        }
    }
}
