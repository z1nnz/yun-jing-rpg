// Qingxi waterworks repair — Unity test scene (local demo, display stock only, never the real inventory).
//
// Gameplay is decided by Rules (C# port of the JS core, checked against tests/golden.json); this component only draws
// and takes input:
//   * planning board (bottom left): tap/click a cell to lay the selected trough, again to rotate, right click or long
//     press to take it out; arrows + Enter / R / X / G / 1-7 / Z / Y from the keyboard;
//   * the 3D view snaps the real kit FBXs port to port along the rule core's reach tree, runs water through it, sprays
//     at open ports / cracks / seepage, and turns the side-mounted gate wheel;
//   * a status card (right) with steps, clues and unknown risks, meters, issues, display stock and the receipt.
// Command line: -fixture all|two|one|none, -demo <dir> (scripted session saving frames, receipts.json, marks.json).
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;

namespace Qingxi.Waterworks
{
    public sealed class WaterworksGame : MonoBehaviour
    {
        public Material ground, creek, soil, crop, rock, grass, sand, oldBed, fleck, spray, water;

        static readonly string[] KEYS = { "straight", "worn", "bendR", "bendL", "tee", "gate", "apron" };
        static readonly Dictionary<string, Vector3> DIR = new Dictionary<string, Vector3> { ["N"] = Vector3.forward, ["E"] = Vector3.right, ["S"] = Vector3.back, ["W"] = Vector3.left };
        const float WATER_Y = 0.30f, VH = 900f;

        Site site; Rules R; GameState st; Sim sim; Check chk; Quote quote;
        string fixture = "all", sel = "worn"; int rot; Vector2Int cursor = new Vector2Int(3, 1); Vector2Int? hover;
        string toast = ""; float toastAt = -99; bool toastBad;
        Receipt receipt; bool replayed; readonly List<Receipt> receipts = new List<Receipt>();

        sealed class View
        {
            public string Key, Seg, Type, InPort; public KitModel Km; public Vector3 Pos; public float Yaw; public double Q; public bool Loose;
            public Transform Gate, Drive, Wheel; public Vector3 GateBase, Axis; public Quaternion DriveBase, WheelBase;
            public List<Renderer> Water = new List<Renderer>();
        }
        readonly Dictionary<string, View> views = new Dictionary<string, View>(); View source;
        readonly Dictionary<string, float> gateT = new Dictionary<string, float>();
        readonly List<(Vector3[] pts, float len)> paths = new List<(Vector3[], float)>();
        readonly List<(Vector3 pos, Vector3 n)> sprays = new List<(Vector3, Vector3)>();
        readonly List<(Transform t, int path, float ph)> flecks = new List<(Transform, int, float)>();
        readonly List<(Transform t, int spray, int j)> drops = new List<(Transform, int, int)>();
        Transform envRoot, buildRoot, fxRoot; float srcPortZ = 0.7f;

        Camera cam; Vector3 camTarget = new Vector3(-0.6f, 0.3f, 2.9f); float camYaw = -18, camPitch = 40, camDist = 10.5f;
        Font font; readonly Dictionary<int, GUIStyle> styles = new Dictionary<int, GUIStyle>();
        readonly List<(Rect r, Action<int> act)> hot = new List<(Rect, Action<int>)>(); readonly List<Rect> blockers = new List<Rect>();
        bool dragCam, longFired; float pressAt; Vector2 pressPos;

        // ================================================================== lifecycle
        void Start()
        {
            var args = Environment.GetCommandLineArgs();
            string Arg(string n) { int i = Array.IndexOf(args, n); return i >= 0 && i + 1 < args.Length ? args[i + 1] : null; }
            if (Application.isMobilePlatform) { Screen.orientation = ScreenOrientation.AutoRotation; Screen.autorotateToPortrait = Screen.autorotateToPortraitUpsideDown = false; }
            site = Site.FromJson(Resources.Load<TextAsset>("waterworks-site").text); R = new Rules(site);
            fixture = Arg("-fixture") ?? "all"; if (!site.Fixtures.ContainsKey(fixture)) fixture = "all";
            font = Font.CreateDynamicFontFromOSFont(new[] { "Microsoft JhengHei UI", "Microsoft JhengHei", "Noto Sans TC", "PingFang TC", "Arial" }, 16);
            cam = Camera.main; envRoot = new GameObject("Env").transform; buildRoot = new GameObject("Build").transform; fxRoot = new GameObject("Fx").transform;
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(0.72f, 0.78f, 0.86f); RenderSettings.ambientEquatorColor = new Color(0.52f, 0.55f, 0.50f); RenderSettings.ambientGroundColor = new Color(0.25f, 0.24f, 0.20f);
            NewGame(fixture);
            var demo = Arg("-demo"); if (demo != null) StartCoroutine(Demo(demo));
        }

        void NewGame(string f)
        {
            fixture = f; st = R.NewGame(site.Fixtures[f].ObservationIds, "unity"); receipt = null; gateT.Clear();
            Refresh(); BuildEnv();
            Say($"線索：{site.Fixtures[f].Label}。先選處理方向，再從水源（南邊 B01）往北鋪槽。");
        }

        void Refresh() { sim = R.Simulate(st); chk = R.Check(st); quote = R.Quote(st); Rebuild(); }

        void Say(string t, bool bad = false) { toast = t; toastAt = Time.unscaledTime; toastBad = bad; }

        Piece PieceAt(int x, int y) => st.Pieces.Get(Site.Key(x, y));

        Result Act(Func<Result> f, string okText = null)
        {
            var r = f();
            if (!r.Ok) Say(r.Message ?? string.Join("；", (r.Issues ?? new List<Issue>()).Take(2).Select(i => i.Message)), true);
            Refresh();
            if (r.Ok) { if (okText != null) Say(okText); else Explain(); }
            return r;
        }

        void Explain()
        {
            var iss = sim.Issues;
            if (iss.Count > 0) Say(iss[0].Message, iss[0].Code == "PORT_MISMATCH" || iss[0].Code == "APRON_MISPLACED" || iss[0].Code == "LOOP");
            else if (st.Direction == null) Say($"水已經到村田 {Rules.Num(sim.Fields)} L/s。選一個處理方向，再按「完成方案」。");
            else Say($"水路接通：村田 {Rules.Num(sim.Fields)} L/s（{sim.Supply}%），育幼區{sim.Nursery.Text}。可以按「完成方案」。");
        }

        // ------------------------------------------------------------------ player actions (mouse, touch, keys and the demo all go through these)
        void Click(int x, int y) { cursor = new Vector2Int(x, y); if (PieceAt(x, y) != null) Act(() => R.Rotate(st, x, y)); else Act(() => R.Place(st, x, y, sel, rot)); }
        void RemoveAt(int x, int y) { cursor = new Vector2Int(x, y); Act(() => R.Remove(st, x, y)); }
        void Select(string t) { sel = t; Say($"選了「{site.Pieces[t].Label}」。點規劃板格子放下。"); }
        void SetDir(string d) => Act(() => R.SetDirection(st, d), $"處理方向：{site.Directions[d].Label}。{site.Directions[d].Text}");
        void Undo() => Act(() => R.Undo(st));
        void Redo() => Act(() => R.Redo(st));

        void Gate(int? gx = null, int? gy = null)
        {
            int x = gx ?? cursor.x, y = gy ?? cursor.y; var p = PieceAt(x, y);
            if (p == null || !site.Pieces[p.Type].Gate)
            {
                var g = st.Pieces.Entries.FirstOrDefault(e => site.Pieces[e.Value.Type].Gate);
                if (g.Key == null) { Say("還沒有閘板。按 6 選閘板，放在水路上。", true); return; }
                (x, y) = Site.Cell(g.Key);
            }
            var r = Act(() => R.ToggleGate(st, x, y));
            if (r.Ok) Say(r.Open == true ? "閘板升起，水放行。" : "閘板放下，水被擋住。");
        }

        void Finish()
        {
            var r = R.Finish(st);
            if (r.Ok) { receipt = r.Receipt; replayed = r.Replay == true; if (!replayed) receipts.Add(r.Receipt); Say(replayed ? "同一個請求重送：回傳原收據，展示材料沒有重複扣。" : $"方案完成：{r.Receipt.OutcomeId}"); }
            else Say(r.Message ?? string.Join("；", r.Issues.Take(2).Select(i => i.Message)), true);
            sim = R.Simulate(st); chk = R.Check(st); quote = R.Quote(st);
        }

        void Retry() { Act(() => R.Retry(st), "新方案：展示材料重置，請求編號換新。現有槽件保留，可以拆掉重鋪。"); receipt = null; }
        void NextFixture() { var k = site.Fixtures.Keys.ToList(); NewGame(k[(k.IndexOf(fixture) + 1) % k.Count]); }

        // ================================================================== 3D: environment, snapped kit, water
        Vector3 CellWorld(float x, float y) => new Vector3((x - 3) * 1f, 0, srcPortZ + (y - 0.5f));

        GameObject Prim(PrimitiveType t, string name, Vector3 c, Vector3 s, Material m, Transform parent)
        {
            var g = GameObject.CreatePrimitive(t); g.name = name; Destroy(g.GetComponent<Collider>());
            g.transform.SetParent(parent, false); g.transform.localPosition = c; g.transform.localScale = s; g.GetComponent<Renderer>().sharedMaterial = m; return g;
        }

        void BuildEnv()
        {
            foreach (Transform c in envRoot) Destroy(c.gameObject);
            var T = site.Terrain; var E = envRoot;
            Prim(PrimitiveType.Cube, "Ground", new Vector3(0, -0.06f, 3), new Vector3(16, 0.10f, 16), ground, E);
            Prim(PrimitiveType.Cube, "CreekS", new Vector3(-1, 0, -1.25f), new Vector3(9.5f, 0.04f, 0.9f), creek, E);   // creek feeding the source plinth
            Prim(PrimitiveType.Cube, "CreekW", new Vector3(-4.05f, 0, 2.4f), new Vector3(0.9f, 0.04f, 8.2f), creek, E);   // and back up the west side
            foreach (var (x, y) in T["seep"]) Prim(PrimitiveType.Cube, $"Seep_{x}_{y}", CellWorld(x, y) + new Vector3(0, -0.005f, 0), new Vector3(0.98f, 0.02f, 0.98f), sand, E);
            foreach (var (x, y) in T["oldChannel"]) Prim(PrimitiveType.Cube, $"OldBed_{x}_{y}", CellWorld(x, y) + new Vector3(0, -0.005f, 0), new Vector3(0.9f, 0.02f, 0.98f), oldBed, E);
            foreach (var (x, y) in T["rock"])
            {
                var c = CellWorld(x, y);
                Prim(PrimitiveType.Sphere, $"Rock_{x}_{y}", c + new Vector3(0, 0.25f, 0), new Vector3(1.1f, 0.7f, 1.1f), rock, E);
                Prim(PrimitiveType.Sphere, $"Rock2_{x}_{y}", c + new Vector3(0.32f, 0.12f, -0.25f), new Vector3(0.56f, 0.4f, 0.56f), rock, E);
            }
            int i = 0;
            foreach (var (x, y) in T["nursery"])                                                              // tall grass over the den
            {
                var c = CellWorld(x, y);
                for (int j = 0; j < 5; j++, i++) { float a = i * 2.39996f, r = (0.18f + 0.07f * (j % 3)) * 1.6f; Prim(PrimitiveType.Sphere, $"Tuft_{x}_{y}_{j}", c + new Vector3(Mathf.Cos(a) * r, 0.25f, Mathf.Sin(a) * r), new Vector3(0.42f, 0.7f, 0.42f), grass, E); }
            }
            Prim(PrimitiveType.Sphere, "Burrow", CellWorld(4.5f, 3.5f) + new Vector3(0, 0.02f, 0), new Vector3(0.6f, 0.2f, 0.6f), soil, E);
            float top = CellWorld(2, 5).z + 0.5f;                                                             // village field beds north of row 5
            for (int b = 0; b < 3; b++)
            {
                float z0 = top + 0.9f + b * 1.3f;
                Prim(PrimitiveType.Cube, $"Bund_{b}", new Vector3(-1, 0.06f, z0), new Vector3(3.6f, 0.12f, 1.15f), soil, E);
                for (int r = 0; r < 5; r++) Prim(PrimitiveType.Cube, $"Crop_{b}_{r}", new Vector3(-2.5f + r * 0.75f, 0.16f, z0), new Vector3(0.14f, 0.10f, 0.95f), crop, E);
            }
            Prim(PrimitiveType.Cube, "FieldInlet", new Vector3(-1, 0.01f, top + 0.3f), new Vector3(3, 0.03f, 0.3f), creek, E);
        }

        View Spawn(string model, Vector3 pos, float yaw, string tag)
        {
            var km = Kit.Get(model); var holder = new GameObject($"{tag}_{model}").transform; holder.SetParent(buildRoot, false);
            holder.SetPositionAndRotation(pos, Quaternion.Euler(0, yaw, 0));
            var inst = Instantiate(km.Prefab, holder, false);
            var v = new View { Km = km, Pos = pos, Yaw = yaw, Axis = Kit.Dir(yaw, Kit.Axes.MultiplyVector(Vector3.right)).normalized };
            foreach (var t in inst.GetComponentsInChildren<Transform>(true))
            {
                var n = t.name;
                if (n.EndsWith("_Gate_LOD0")) { v.Gate = t; v.GateBase = t.position; }
                else if (n.EndsWith("_Drive_LOD0")) { v.Drive = t; v.DriveBase = t.rotation; }
                else if (model == "B06_GateWheel" && n.EndsWith("_LOD0")) { v.Wheel = t; v.WheelBase = t.rotation; }
                if (n.Contains("_Water") && t.TryGetComponent<Renderer>(out var r))
                {
                    v.Water.Add(r);                                                                    // the kit's blended Blender water imports opaque; use a transparent one
                    if (water) r.sharedMaterials = Enumerable.Repeat(water, r.sharedMaterials.Length).ToArray();
                }
            }
            return v;
        }

        Vector3 PortPos(View v, string port) => Kit.World(v.Pos, v.Yaw, v.Km.Ports[port].Pos);
        Vector3 PortNormal(View v, string port) => Kit.Dir(v.Yaw, v.Km.Ports[port].Normal);

        void Rebuild()
        {
            foreach (Transform c in buildRoot) Destroy(c.gameObject);
            views.Clear();
            var src = Kit.Get(site.SourceModel); var srcN = src.Ports[site.SourcePort].Normal;
            source = Spawn(site.SourceModel, Vector3.zero, Vector3.SignedAngle(new Vector3(srcN.x, 0, srcN.z), Vector3.forward, Vector3.up), "S00");
            srcPortZ = PortPos(source, site.SourcePort).z;
            foreach (var kv in sim.Reach.OrderBy(r => r.Value.Order))
            {
                var p = st.Pieces.Get(kv.Key); var spec = site.Pieces[p.Type]; var km = Kit.Get(spec.Model);
                var sides = site.SidesOf(p); var inPort = spec.Ports[Array.IndexOf(sides, kv.Value.InSide)];
                Vector3 pa, na;
                if (kv.Value.From == "source") { pa = PortPos(source, site.SourcePort); na = PortNormal(source, site.SourcePort); }
                else
                {
                    var parent = views[kv.Value.From]; var pp = st.Pieces.Get(kv.Value.From); var (px, py) = Site.Cell(kv.Value.From); var (x, y) = Site.Cell(kv.Key);
                    var side = Site.SIDES.First(s => px + Site.STEP[s].dx == x && py + Site.STEP[s].dy == y);
                    var outPort = site.Pieces[pp.Type].Ports[Array.IndexOf(site.SidesOf(pp), side)];
                    pa = PortPos(parent, outPort); na = PortNormal(parent, outPort);
                }
                var (pos, yaw) = Kit.Snap(pa, na, km, inPort);
                views[kv.Key] = Dress(Spawn(spec.Model, pos, yaw, p.Seg), kv.Key, p, inPort, sim.Wet.TryGetValue(kv.Key, out var q) ? q : 0, false);
            }
            foreach (var e in st.Pieces.Entries)
            {
                if (views.ContainsKey(e.Key)) continue;
                var (x, y) = Site.Cell(e.Key); var spec = site.Pieces[e.Value.Type]; var km = Kit.Get(spec.Model);
                var want = DIR[Site.RotSide(spec.Sides[0], e.Value.Rot)]; var n0 = km.Ports[spec.Ports[0]].Normal;
                float yaw = Vector3.SignedAngle(new Vector3(n0.x, 0, n0.z), want, Vector3.up);
                views[e.Key] = Dress(Spawn(spec.Model, CellWorld(x, y) - Quaternion.Euler(0, yaw, 0) * km.Centre, yaw, e.Value.Seg), e.Key, e.Value, null, 0, true);
            }
            BuildFx();
        }

        View Dress(View v, string key, Piece p, string inPort, double q, bool loose)
        {
            v.Key = key; v.Seg = p.Seg; v.Type = p.Type; v.InPort = inPort; v.Q = q; v.Loose = loose;
            foreach (var w in v.Water) w.enabled = q > 0;
            if (site.Pieces[p.Type].Gate)
            {
                var sk = v.Km.Sockets["WheelMount"]; var wheel = Spawn("B06_GateWheel", Kit.World(v.Pos, v.Yaw, sk.Pos), v.Yaw, p.Seg + "W");
                v.Wheel = wheel.Wheel; v.WheelBase = wheel.WheelBase;
                if (!gateT.ContainsKey(key)) gateT[key] = p.Open == false ? 0 : 1;
            }
            return v;
        }

        static Vector3? Meet(Vector3 a, Vector3 da, Vector3 b, Vector3 db)
        {
            float cr = da.x * db.z - da.z * db.x; if (Mathf.Abs(cr) < 1e-4f) return null;
            float s = ((b.x - a.x) * db.z - (b.z - a.z) * db.x) / cr; return a + da * s;
        }

        void BuildFx()
        {
            foreach (Transform c in fxRoot) Destroy(c.gameObject);
            paths.Clear(); sprays.Clear(); flecks.Clear(); drops.Clear();
            foreach (var v in views.Values)
            {
                if (v.Loose || v.Q <= 0) continue;
                var spec = site.Pieces[v.Type];
                if (spec.Gate && gateT.TryGetValue(v.Key, out var gt) && gt < 0.5f) continue;
                var a = PortPos(v, v.InPort); a.y = WATER_Y; var na = PortNormal(v, v.InPort);
                var outs = spec.Ports.Where(n => n != v.InPort).ToList();
                if (spec.Outlet != null)                                                                      // apron: pool, then over the lip
                    AddPath(new[] { a, Kit.World(v.Pos, v.Yaw, Kit.Axes.MultiplyVector(new Vector3(0, 0, WATER_Y))), Kit.World(v.Pos, v.Yaw, Kit.Axes.MultiplyVector(new Vector3(0, -0.42f, 0.20f))),
                        Kit.World(v.Pos, v.Yaw, Kit.Axes.MultiplyVector(new Vector3(0, -0.62f, 0.02f))) }, v.Q);
                foreach (var o in outs)
                {
                    var b = PortPos(v, o); b.y = WATER_Y; var nb = PortNormal(v, o);
                    var m = Meet(a, -na, b, -nb); var mid = m.HasValue ? new Vector3(m.Value.x, WATER_Y, m.Value.z) : (a + b) / 2;
                    AddPath(new[] { a, mid, b }, v.Q / Math.Max(1, outs.Count));
                }
            }
            foreach (var l in sim.Leaks)
            {
                var k = Site.Key(l.At[0], l.At[1]); if (!views.TryGetValue(k, out var v)) continue;
                Vector3 pos, n;
                if (l.Why == "open" && l.Side != null) { var p = st.Pieces.Get(k); var port = site.Pieces[p.Type].Ports[Array.IndexOf(site.SidesOf(p), l.Side)]; pos = PortPos(v, port); pos.y = WATER_Y; n = PortNormal(v, port); }
                else { pos = v.Pos + new Vector3(0, 0.12f, 0); n = Kit.Dir(v.Yaw, Kit.Axes.MultiplyVector(Vector3.right)); }
                sprays.Add((pos, n.normalized));
                for (int j = 0; j < Mathf.Clamp(Mathf.RoundToInt((float)l.Q / 3), 3, 10); j++)
                    drops.Add((Prim(PrimitiveType.Sphere, "Drop", pos, Vector3.one * 0.06f, spray, fxRoot).transform, sprays.Count - 1, j));
            }
        }

        void AddPath(Vector3[] pts, double q)
        {
            float len = 0; for (int i = 1; i < pts.Length; i++) len += Vector3.Distance(pts[i - 1], pts[i]);
            paths.Add((pts, Mathf.Max(0.01f, len))); int n = Mathf.Clamp(Mathf.RoundToInt((float)q / 6), 2, 14);
            for (int j = 0; j < n; j++) flecks.Add((Prim(PrimitiveType.Sphere, "Fleck", pts[0], Vector3.one * 0.07f, fleck, fxRoot).transform, paths.Count - 1, j / (float)n));
        }

        static Vector3 Along(Vector3[] pts, float len, float t)
        {
            float s = t * len;
            for (int i = 1; i < pts.Length; i++) { float l = Vector3.Distance(pts[i - 1], pts[i]); if (s <= l) return Vector3.Lerp(pts[i - 1], pts[i], l > 0 ? s / l : 0); s -= l; }
            return pts[pts.Length - 1];
        }

        // ================================================================== per frame: animation, camera, keys, long press
        void Update()
        {
            if (st == null) return;
            float now = Time.time;
            foreach (var (t, i, ph) in flecks) { var (pts, len) = paths[i]; t.position = Along(pts, len, (ph + now * 0.55f / len) % 1f); }
            foreach (var (t, i, j) in drops)
            {
                var (pos, n) = sprays[i]; float u = (now * 1.3f + j * 0.37f) % 1f; var side = Vector3.Cross(Vector3.up, n) * (((j * 7) % 5 - 2) * 0.03f);
                t.position = pos + n * (0.55f * u) + side + Vector3.up * (0.25f * u - 0.9f * u * u);
            }
            bool fxDirty = false;
            foreach (var v in views.Values.Where(v => site.Pieces[v.Type].Gate))
            {
                var p = st.Pieces.Get(v.Key); if (p == null) continue;
                float want = p.Open == false ? 0 : 1, t = gateT.TryGetValue(v.Key, out var g) ? g : want, before = t;
                t = Mathf.MoveTowards(t, want, Time.deltaTime / 1.2f); gateT[v.Key] = t;
                if ((before < 0.5f) != (t < 0.5f)) fxDirty = true;
                if (v.Gate) v.Gate.position = v.GateBase + Vector3.up * 0.32f * t;
                var turn = Quaternion.AngleAxis(10f * Mathf.Rad2Deg * t, v.Axis);
                if (v.Drive) v.Drive.rotation = turn * v.DriveBase;
                if (v.Wheel) v.Wheel.rotation = turn * v.WheelBase;
                foreach (var w in v.Water.OfType<SkinnedMeshRenderer>())
                {
                    int k = w.sharedMesh ? w.sharedMesh.GetBlendShapeIndex("Open") : -1; if (k >= 0) w.SetBlendShapeWeight(k, 100 * t);
                }
            }
            if (fxDirty) BuildFx();
            foreach (var v in views.Values.Append(source))
                foreach (var w in v.Water.OfType<SkinnedMeshRenderer>())
                    for (int k = 0; w.sharedMesh && k < w.sharedMesh.blendShapeCount; k++)
                    {
                        var n = w.sharedMesh.GetBlendShapeName(k);
                        if (n.StartsWith("Ripple")) w.SetBlendShapeWeight(k, 50 + 50 * Mathf.Sin(now * 2.2f + (n.EndsWith("1") ? 1.6f : 0)));
                    }
            Keys(); CameraInput(); LongPress();
            var rotq = Quaternion.Euler(camPitch, camYaw, 0);
            cam.transform.SetPositionAndRotation(camTarget - rotq * Vector3.forward * camDist, rotq);
        }

        void Keys()
        {
            if (Input.GetKeyDown(KeyCode.UpArrow)) Move(0, 1); if (Input.GetKeyDown(KeyCode.DownArrow)) Move(0, -1);
            if (Input.GetKeyDown(KeyCode.LeftArrow)) Move(-1, 0); if (Input.GetKeyDown(KeyCode.RightArrow)) Move(1, 0);
            if (Input.GetKeyDown(KeyCode.Return) || Input.GetKeyDown(KeyCode.KeypadEnter) || Input.GetKeyDown(KeyCode.Space)) Click(cursor.x, cursor.y);
            if (Input.GetKeyDown(KeyCode.R)) { if (PieceAt(cursor.x, cursor.y) != null) Act(() => R.Rotate(st, cursor.x, cursor.y)); else { rot = (rot + 1) % 4; Say($"下一件旋轉 {rot * 90}°"); } }
            if (Input.GetKeyDown(KeyCode.X) || Input.GetKeyDown(KeyCode.Delete) || Input.GetKeyDown(KeyCode.Backspace)) RemoveAt(cursor.x, cursor.y);
            if (Input.GetKeyDown(KeyCode.G)) Gate();
            if (Input.GetKeyDown(KeyCode.Z)) Undo();
            if (Input.GetKeyDown(KeyCode.Y)) Redo();
            for (int i = 0; i < KEYS.Length; i++) if (Input.GetKeyDown(KeyCode.Alpha1 + i) || Input.GetKeyDown(KeyCode.Keypad1 + i)) Select(KEYS[i]);
        }

        void Move(int dx, int dy) { cursor = new Vector2Int(Mathf.Clamp(cursor.x + dx, 0, site.W - 1), Mathf.Clamp(cursor.y + dy, 0, site.H - 1)); hover = cursor; }

        float UiScale => Mathf.Max(0.5f, Screen.height / VH);
        Vector2 GuiMouse => new Vector2(Input.mousePosition.x, Screen.height - Input.mousePosition.y) / UiScale;
        bool OverUi(Vector2 p) => blockers.Any(r => r.Contains(p)) || hot.Any(h => h.r.Contains(p));

        void CameraInput()
        {
            if (Input.touchCount == 2)                                                                       // pinch zoom, two-finger orbit
            {
                Touch a = Input.GetTouch(0), b = Input.GetTouch(1);
                float d0 = ((a.position - a.deltaPosition) - (b.position - b.deltaPosition)).magnitude, d1 = (a.position - b.position).magnitude;
                camDist = Mathf.Clamp(camDist * (d0 / Mathf.Max(1, d1)), 3, 22); camYaw += (a.deltaPosition.x + b.deltaPosition.x) * 0.1f; dragCam = false; return;
            }
            if (Input.GetMouseButtonDown(0) || Input.GetMouseButtonDown(1) || Input.GetMouseButtonDown(2)) dragCam = !OverUi(GuiMouse);
            if (!Input.GetMouseButton(0) && !Input.GetMouseButton(1) && !Input.GetMouseButton(2)) dragCam = false;
            if (dragCam)
            {
                float mx = Input.GetAxis("Mouse X"), my = Input.GetAxis("Mouse Y");
                if (Input.touchCount == 1) { var dlt = Input.GetTouch(0).deltaPosition; mx = dlt.x * 0.05f; my = dlt.y * 0.05f; }
                if (Input.GetMouseButton(2)) camTarget -= Quaternion.Euler(0, camYaw, 0) * new Vector3(mx, 0, my) * camDist * 0.04f;
                else { camYaw += mx * 3; camPitch = Mathf.Clamp(camPitch - my * 3, 12, 85); }
            }
            if (!OverUi(GuiMouse)) camDist = Mathf.Clamp(camDist - Input.mouseScrollDelta.y * 0.8f, 3, 22);
        }

        void LongPress()                                                                                     // touch: hold a placed piece to take it out
        {
            if (Input.GetMouseButtonDown(0)) { pressAt = Time.unscaledTime; pressPos = GuiMouse; longFired = false; }
            if (!Input.GetMouseButton(0) || longFired || Time.unscaledTime - pressAt < 0.6f || (GuiMouse - pressPos).magnitude > 12) return;
            var c = BoardCell(pressPos);
            if (c.HasValue && PieceAt(c.Value.x, c.Value.y) != null) { longFired = true; RemoveAt(c.Value.x, c.Value.y); }
        }

        // ================================================================== IMGUI overlay
        GUIStyle Style(int size)
        {
            if (!styles.TryGetValue(size, out var s)) styles[size] = s = new GUIStyle { font = font, fontSize = size, wordWrap = true, richText = false, normal = { textColor = Color.black } };
            return s;
        }

        static readonly Color INK = new Color(0.12f, 0.11f, 0.10f), PAPER = new Color(0.96f, 0.94f, 0.88f, 0.95f), JADE = new Color(0.25f, 0.44f, 0.38f), AMBER = new Color(0.80f, 0.50f, 0.18f),
            BAD = new Color(0.86f, 0.22f, 0.15f), WET = new Color(0.25f, 0.60f, 0.95f), DRY = new Color(0.80f, 0.77f, 0.70f), DIM = new Color(0.45f, 0.43f, 0.40f);

        static void Fill(Rect r, Color c) => GUI.DrawTexture(r, Texture2D.whiteTexture, ScaleMode.StretchToFill, true, 0, c, 0, 0);
        static void Frame(Rect r, Color c, float t = 2) { Fill(new Rect(r.x, r.y, r.width, t), c); Fill(new Rect(r.x, r.yMax - t, r.width, t), c); Fill(new Rect(r.x, r.y, t, r.height), c); Fill(new Rect(r.xMax - t, r.y, t, r.height), c); }

        void Text(Rect r, string s, int size, Color c, TextAnchor a = TextAnchor.UpperLeft, bool shadow = false)
        {
            var st2 = Style(size); st2.alignment = a;
            if (shadow) { st2.normal.textColor = new Color(0, 0, 0, 0.85f); GUI.Label(new Rect(r.x + 1, r.y + 1, r.width, r.height), s, st2); }
            st2.normal.textColor = c; GUI.Label(r, s, st2);
        }

        void Button(Rect r, string label, Action act, bool on = false, bool accent = false, string sub = null)
        {
            Fill(new Rect(r.x + 2, r.y + 2, r.width - 4, r.height - 4), on ? JADE : accent ? AMBER : PAPER);
            var fg = on || accent ? Color.white : INK;
            if (sub == null) Text(r, label, 13, fg, TextAnchor.MiddleCenter);
            else { Text(new Rect(r.x, r.y + 2, r.width, r.height * 0.58f), label, 13, fg, TextAnchor.MiddleCenter); Text(new Rect(r.x, r.y + r.height * 0.52f, r.width, r.height * 0.45f), sub, 10, on ? new Color(0.9f, 0.95f, 0.9f) : DIM, TextAnchor.MiddleCenter); }
            hot.Add((r, b => { if (b == 0) act(); }));
        }

        // board geometry (virtual 900-high GUI space, y down)
        const float C = 48, BAND = 14, PH = 36;
        float BoardX => 84; float BoardBottom => VH - 52; float BoardTop => BoardBottom - site.H * C;
        Rect CellRect(int x, int y) => new Rect(BoardX + x * C, BoardBottom - (y + 1) * C, C, C);
        Vector2Int? BoardCell(Vector2 p)
        {
            int x = Mathf.FloorToInt((p.x - BoardX) / C), y = Mathf.FloorToInt((BoardBottom - p.y) / C);
            return x >= 0 && y >= 0 && x < site.W && y < site.H ? new Vector2Int(x, y) : (Vector2Int?)null;
        }

        void OnGUI()
        {
            if (st == null) return;
            GUI.matrix = Matrix4x4.Scale(new Vector3(UiScale, UiScale, 1));
            var e = Event.current; hot.Clear(); blockers.Clear();
            Labels(); Board(); Status();
            float vw = Screen.width / UiScale;
            Text(new Rect(0, 10, vw, 24), "本機演示 · 展示材料，不入正式背包", 16, new Color(1, 0.86f, 0.75f), TextAnchor.MiddleCenter, true);
            if (toast.Length > 0 && Time.unscaledTime - toastAt < 9)
            {
                float w = Mathf.Min(vw - 40, 640); var s = Style(16); float h = s.CalcHeight(new GUIContent(toast), w - 24) + 16;
                var r = new Rect((vw - w) / 2, 40, w, h); Fill(r, toastBad ? new Color(0.97f, 0.87f, 0.84f, 0.96f) : PAPER);
                Text(new Rect(r.x + 12, r.y + 8, w - 24, h), toast, 16, toastBad ? BAD : INK);
            }
            if (e.type == EventType.MouseMove || e.type == EventType.MouseDrag) hover = BoardCell(e.mousePosition);
            if (e.type == EventType.MouseDown && OverUi(e.mousePosition)) e.Use();
            if (e.type == EventType.MouseUp)
            {
                if (longFired) { longFired = false; e.Use(); return; }
                var h = hot.LastOrDefault(x => x.r.Contains(e.mousePosition));
                if (h.act != null) { h.act(e.button); e.Use(); }
            }
        }

        void Labels()
        {
            Vector2? At(Vector3 w) { var p = cam.WorldToScreenPoint(w); if (p.z <= 0) return null; return new Vector2(p.x, Screen.height - p.y) / UiScale; }
            void Tag(Vector3 w, string s, int size, Color c) { var p = At(w); if (p.HasValue) Text(new Rect(p.Value.x - 120, p.Value.y - 12, 240, 24), s, size, c, TextAnchor.MiddleCenter, true); }
            var bad = new HashSet<string>(sim.Issues.Where(i => i.At != null).Select(i => Site.Key(i.At[0], i.At[1])));
            foreach (var v in views.Values)
            {
                var top = v.Pos + Vector3.up * 1.15f;
                Tag(top, $"{v.Seg} {site.Pieces[v.Type].Label}{(v.Loose ? "（未接水）" : "")}", 14, bad.Contains(v.Key) || v.Loose ? BAD : Color.white);
                if (!v.Loose && v.Q > 0) Tag(top - Vector3.up * 0.16f, $"{v.Q:0} L/s", 12, new Color(0.75f, 0.9f, 1));
            }
            foreach (var (what, label) in new[] { ("crack", "破槽"), ("silt", "泥沙") })
                foreach (var (x, y) in site.Terrain[what]) Tag(CellWorld(x, y) + new Vector3(0.75f, 0.5f, 0), st.Known[what] ? label : "？未確認", 13, st.Known[what] ? new Color(1, 0.7f, 0.5f) : new Color(0.9f, 0.9f, 0.85f));
            Tag(CellWorld(4.5f, 3.5f) + Vector3.up * 0.9f, st.Known["nursery"] ? "育幼區（幼獸足跡）" : "？草叢", 14, st.Known["nursery"] ? new Color(1, 0.75f, 0.65f) : new Color(0.9f, 0.9f, 0.85f));
            Tag(new Vector3(-1, 0.4f, CellWorld(2, 5).z + 1.2f), "村田進水口", 14, new Color(0.85f, 0.95f, 1));
            Tag(new Vector3(-4, 0.3f, 1.7f), "溪道回流口", 14, new Color(0.85f, 0.95f, 1));
            Tag(new Vector3(0, 1.0f, 0), "水源 B01", 14, new Color(0.85f, 0.95f, 1));
        }

        void Board()
        {
            float bw = site.W * C, palY = BoardTop - BAND - 6 - 2 * PH, ctlY = palY - 8 - 2 * PH;
            var panel = new Rect(BoardX - BAND - 8, ctlY - 8, bw + BAND + 16, VH - 12 - (ctlY - 8)); Fill(panel, new Color(0.12f, 0.13f, 0.11f, 0.82f)); blockers.Add(panel);
            int i = 0;                                                                                       // treatment direction
            foreach (var d in site.Directions.Values)
            {
                var id = d.Id; Button(new Rect(BoardX + i++ * bw / 3, ctlY, bw / 3, PH), d.Label, () => SetDir(id), st.Direction == id, sub: string.Join(" ", d.Cost.Select(c => $"{site.StockZh[c.Key]}{c.Value}")));
            }
            var tools = new (string, Action, bool)[] { ("閘板 G", () => Gate(), false), ("撤回 Z", Undo, false), ("重做 Y", Redo, false), ("完成方案", Finish, true), ("重試", Retry, false) };
            for (i = 0; i < tools.Length; i++) Button(new Rect(BoardX + i * bw / 5, ctlY + PH, bw / 5, PH), tools[i].Item1, tools[i].Item2, accent: tools[i].Item3);
            for (i = 0; i < KEYS.Length; i++)                                                                // pieces
            {
                var t = KEYS[i]; var spec = site.Pieces[t];
                Button(new Rect(BoardX + (i % 4) * bw / 4, palY + (i / 4) * PH, bw / 4, PH), $"{i + 1} {spec.Label}", () => Select(t), sel == t, sub: string.Join(" ", spec.Cost.Select(c => $"{site.StockZh[c.Key].Substring(0, 1)}{c.Value}")));
            }
            foreach (var tg in site.Targets)
                foreach (var (x, y) in tg.Cells)
                {
                    var r = CellRect(x, y);
                    Fill(tg.Side == "N" ? new Rect(r.x, r.y - BAND, C, BAND) : new Rect(r.x - BAND, r.y, BAND, C), tg.Id == "fields" ? new Color(0.38f, 0.62f, 0.25f) : new Color(0.18f, 0.45f, 0.66f));
                }
            Text(new Rect(BoardX + C, BoardTop - BAND - 1, 3 * C, BAND + 2), "村田進水口", 10, new Color(0.9f, 1, 0.85f), TextAnchor.MiddleCenter);
            for (int y = 0; y < site.H; y++)
                for (int x = 0; x < site.W; x++)
                {
                    var r = CellRect(x, y); var col = new Color(0.36f, 0.40f, 0.27f, 0.95f); string tag = null;
                    if (site.Has("oldChannel", x, y)) col = new Color(0.44f, 0.40f, 0.32f, 0.95f);
                    if (site.Has("seep", x, y)) { col = new Color(0.74f, 0.63f, 0.40f, 0.95f); tag = "沙坡"; }
                    if (site.Has("rock", x, y)) { col = new Color(0.30f, 0.30f, 0.30f, 0.95f); tag = "大石"; }
                    if (site.Has("nursery", x, y)) { col = st.Known["nursery"] ? new Color(0.66f, 0.36f, 0.30f, 0.95f) : new Color(0.22f, 0.40f, 0.18f, 0.95f); tag = st.Known["nursery"] ? "育幼" : "草叢"; }
                    if (site.Has("crack", x, y) && st.Known["crack"]) tag = "裂";
                    if (site.Has("silt", x, y) && st.Known["silt"]) tag = "淤";
                    Fill(new Rect(r.x + 1, r.y + 1, C - 2, C - 2), col);
                    if (tag != null) Text(new Rect(r.x + 3, r.yMax - 16, C, 14), tag, 10, new Color(1, 1, 1, 0.85f));
                    int cx = x, cy = y; hot.Add((r, b => { if (b == 0) Click(cx, cy); else if (b == 1) RemoveAt(cx, cy); }));
                }
            var sr = CellRect(site.SourceX, site.SourceY);
            Fill(new Rect(sr.x + C * 0.15f, sr.y + C * 0.15f, C * 0.7f, C * 0.7f), new Color(0.18f, 0.45f, 0.66f)); Text(sr, "B01", 12, Color.white, TextAnchor.MiddleCenter);
            Fill(new Rect(sr.x + C * 0.36f, sr.y, C * 0.28f, C * 0.15f), WET);
            var badCells = new HashSet<string>(sim.Issues.Where(i2 => i2.At != null).Select(i2 => Site.Key(i2.At[0], i2.At[1])));
            foreach (var kv in st.Pieces.Entries)
            {
                var (x, y) = Site.Cell(kv.Key); var r = CellRect(x, y);
                Glyph(r, kv.Value, sim.Wet.TryGetValue(kv.Key, out var q) && q > 0, 1);
                if (badCells.Contains(kv.Key)) Frame(new Rect(r.x + 1, r.y + 1, C - 2, C - 2), BAD, 3);
            }
            if (hover.HasValue && PieceAt(hover.Value.x, hover.Value.y) == null && st.Finished == null)
                Glyph(CellRect(hover.Value.x, hover.Value.y), new Piece { Type = sel, Rot = rot, Open = true }, false, 0.45f);
            Frame(CellRect(cursor.x, cursor.y), new Color(1, 0.85f, 0.2f), 3);
            Text(new Rect(BoardX - BAND, BoardBottom + 8, bw + 300, 20), $"旋轉 {rot * 90}°（R）· 點格子放／再點旋轉 · 右鍵或長按拆除 · 方向鍵+Enter · G 閘板 · Z 撤回 · Y 重做 · 拖曳空白處轉視角", 12, new Color(0.92f, 0.9f, 0.85f));
        }

        void Glyph(Rect r, Piece p, bool wet, float a)
        {
            var spec = site.Pieces[p.Type]; var col = wet ? WET : DRY; col.a = a; float w = C * 0.30f; var m = r.center;
            var sides = site.SidesOf(p);
            foreach (var s in sides)
            {
                var (dx, dy) = Site.STEP[s];
                if (dx != 0) Fill(new Rect(dx > 0 ? m.x : m.x - C / 2, m.y - w / 2, C / 2, w), col);
                else Fill(new Rect(m.x - w / 2, dy > 0 ? m.y - C / 2 : m.y, w, C / 2), col);
            }
            Fill(new Rect(m.x - w / 2, m.y - w / 2, w, w), col);
            if (spec.Outlet != null)
            {
                var (dx, dy) = Site.STEP[Site.RotSide(spec.Outlet, p.Rot)]; var tip = m + new Vector2(dx, -dy) * C * 0.42f;
                var c2 = wet ? new Color(WET.r, WET.g, WET.b, 0.65f * a) : col; Fill(new Rect(tip.x - C * 0.14f, tip.y - C * 0.14f, C * 0.28f, C * 0.28f), c2);
            }
            if (spec.Gate)
            {
                var (dx, _) = Site.STEP[sides[0]]; var bar = p.Open == false ? new Color(0.85f, 0.2f, 0.15f, a) : new Color(AMBER.r, AMBER.g, AMBER.b, a);
                Fill(dx != 0 ? new Rect(m.x - C * 0.06f, m.y - C * 0.32f, C * 0.12f, C * 0.64f) : new Rect(m.x - C * 0.32f, m.y - C * 0.06f, C * 0.64f, C * 0.12f), bar);
            }
            if (p.Seg != null) Text(new Rect(r.xMax - 26, r.y + 1, 26, 14), p.Seg, 9, new Color(1, 1, 1, 0.9f));
        }

        void Status()
        {
            float vw = Screen.width / UiScale, w = 340, x = vw - w - 16, y = 84, pad = 12, tw = w - 2 * pad;
            var rows = new List<(string text, Color col, int size, Action act, float bar)>();
            void Row(string s, Color c, int size = 13) => rows.Add((s, c, size, null, -1));
            var steps = new[] { ("看線索", true), ("選處理方向", st.Direction != null), ("從水源鋪到村田", sim.Fields > 0 && sim.Issues.Count == 0), ("開閘看水", sim.Fields > 0), ("完成方案", st.Finished != null) };
            int now = Array.FindIndex(steps, s => !s.Item2);
            Row(string.Join("  ", steps.Select((s, i) => $"{(s.Item2 ? "■" : i == now ? "▶" : "□")}{i + 1}{s.Item1}")), INK, 13);
            rows.Add(($"線索：{site.Fixtures[fixture].Label}（點這裡換）", INK, 13, NextFixture, -1));
            Row(string.Join("  ", site.Observations.Values.Select(o => $"{o.Label}：{(st.ObservationIds.Contains(o.Id) ? "看到" : "沒看到")}")), DIM, 12);
            foreach (var r in sim.Risks) Row("未知風險：" + r, new Color(0.62f, 0.40f, 0.08f), 12);
            Row($"處理方向：{(st.Direction != null ? site.Directions[st.Direction].Label : "還沒選")}", INK, 14);
            Row($"到村田 {Rules.Num(sim.Fields)} L/s（{sim.Supply}%，需求 {site.FieldDemand}）", INK, 14);
            rows.Add((null, WET, 0, null, sim.Supply / 100f));
            Row($"回溪道 {Rules.Num(sim.Creek)} L/s　漏失 {sim.Leaks.Sum(l => l.Q):0.0} L/s", INK, 13);
            Row($"育幼區：{sim.Nursery.Text}{(st.Known["nursery"] ? "" : "（線索沒看到，只是預估）")}", sim.Nursery.Level == 2 ? BAD : INK, 13);
            if (st.Finished == null && chk.Issues.Count > 0) { Row($"還要處理 {chk.Issues.Count} 件：", BAD, 14); foreach (var iss in chk.Issues.Take(3)) Row("・" + iss.Message, BAD, 12); }
            else Row(st.Finished == null ? "沒有問題，可以按「完成方案」。" : "已完成；再按一次只會拿回同一張收據。", JADE, 13);
            Row("展示材料（不是正式背包）需要／現有：", DIM, 12);
            Row(string.Join("  ", st.Stock.Select(kv => $"{site.StockZh[kv.Key]}{(quote.Need.TryGetValue(kv.Key, out var n) ? n : 0)}/{kv.Value}")), INK, 13);
            Row($"請求編號 {Rules.RequestIdFor(st)}", DIM, 11);
            if (receipt != null)
            {
                Row(replayed ? "重送：同一張收據，沒有重複扣料" : "收據", JADE, 14);
                Row($"outcomeId：{receipt.OutcomeId}", INK, 12);
                Row($"村田 {Rules.Num(receipt.FieldsFlow)} L/s（{receipt.FieldsSupplyPct}%）　溪道 {Rules.Num(receipt.CreekFlow)} L/s　育幼區：{receipt.Nursery}", INK, 12);
                Row("扣料：" + string.Join(" ", receipt.Spent.Select(kv => $"{site.StockZh[kv.Key]}{kv.Value}")), INK, 12);
                foreach (var s in receipt.Surprises) Row(s, new Color(0.62f, 0.40f, 0.08f), 12);
            }
            float H(int i) { var r = rows[i]; return r.bar >= 0 ? 10 : r.act != null ? 30 : Style(r.size).CalcHeight(new GUIContent(r.text), tw) + 3; }
            float total = 40 + Enumerable.Range(0, rows.Count).Sum(H) + pad;
            var card = new Rect(x, y, w, total); Fill(card, PAPER); blockers.Add(card);
            Text(new Rect(x + pad, y + 10, tw, 24), "青溪古水路修復", 17, INK); float cy = y + 40;
            for (int i = 0; i < rows.Count; i++)
            {
                var r = rows[i]; float h = H(i);
                if (r.bar >= 0) { Fill(new Rect(x + pad, cy + 2, tw, 6), new Color(0.85f, 0.82f, 0.74f)); Fill(new Rect(x + pad, cy + 2, tw * Mathf.Clamp01(r.bar), 6), WET); }
                else if (r.act != null) Button(new Rect(x + pad - 4, cy, tw + 8, h - 2), r.text, r.act);
                else Text(new Rect(x + pad, cy, tw, h), r.text, r.size, r.col);
                cy += h;
            }
        }

        // ================================================================== scripted session (operation recording)
        IEnumerator Demo(string dir)
        {
            var frames = Path.Combine(dir, "frames"); Directory.CreateDirectory(frames);
            foreach (var f in Directory.GetFiles(frames, "*.png")) File.Delete(f);
            int n = 0; var marks = new List<object>(); bool done = false;
            IEnumerator Shooter() { while (!done) { ScreenCapture.CaptureScreenshot(Path.Combine(frames, $"f{n++:00000}.png")); yield return new WaitForSecondsRealtime(0.25f); } }
            StartCoroutine(Shooter());
            var steps = new List<(float secs, Action act, string mark)>();
            void Add(float s, Action a, string m = null) => steps.Add((s, a, m));
            Action P(int x, int y, string t, int r = 0) => () => { sel = t; rot = r; Click(x, y); };
            Add(2.0f, () => NewGame("two"), "start_missed_nursery_clue");
            Add(1.5f, () => SetDir("restore_channel"), "direction_restore");
            Add(1.2f, P(3, 1, "gate")); Add(1.0f, P(3, 2, "worn"));
            Add(2.5f, P(3, 3, "worn", 1), "misconnection_port_named");
            Add(2.0f, () => Click(3, 3), "rotated_fixed");
            Add(1.0f, P(3, 4, "worn")); Add(3.0f, P(3, 5, "apron"), "water_reaches_fields");
            Add(3.0f, () => Gate(3, 1), "gate_closed"); Add(3.0f, () => Gate(3, 1), "gate_open");
            Add(3.0f, Finish, "finish_direct"); Add(2.5f, Finish, "finish_again_same_receipt");
            Add(1.5f, Retry, "retry");
            foreach (var yy in new[] { 5, 4, 3, 2, 1 }) { int y = yy; Add(0.4f, () => RemoveAt(3, y)); }
            Add(1.5f, Undo, "undo"); Add(1.5f, Redo, "redo");
            Add(1.2f, () => SetDir("protect_nursery"));
            foreach (var (x, y, t, r) in new[] { (3, 1, "bendL", 0), (2, 1, "straight", 1), (1, 1, "bendR", 3), (1, 2, "straight", 0), (1, 3, "straight", 0), (1, 4, "straight", 0) }) Add(0.6f, P(x, y, t, r));
            Add(3.0f, P(1, 5, "apron"), "detour_flowing"); Add(3.0f, Finish, "finish_detour");
            Add(1.0f, Retry);
            foreach (var (x, y) in new[] { (1, 5), (1, 4), (1, 3), (1, 2), (1, 1), (2, 1), (3, 1) }) { int a = x, b = y; Add(0.3f, () => RemoveAt(a, b)); }
            Add(1.2f, () => SetDir("clear_silt"));
            foreach (var (x, y, t, r) in new[] { (3, 1, "tee", 1), (2, 1, "straight", 1), (1, 1, "straight", 1), (0, 1, "apron", 3), (3, 2, "worn", 0), (3, 3, "worn", 0), (3, 4, "worn", 0) }) Add(0.6f, P(x, y, t, r));
            Add(3.0f, P(3, 5, "apron"), "divert_split_flowing"); Add(3.5f, Finish, "finish_divert");
            yield return new WaitForSecondsRealtime(1.5f);
            string pending = null;
            foreach (var (secs, act, mark) in steps)
            {
                if (pending != null) { marks.Add(new Dictionary<string, object> { ["frame"] = n, ["mark"] = pending, ["toast"] = toast }); }
                act(); pending = mark; yield return new WaitForSecondsRealtime(secs);
            }
            if (pending != null) marks.Add(new Dictionary<string, object> { ["frame"] = n, ["mark"] = pending, ["toast"] = toast });
            done = true; yield return new WaitForSecondsRealtime(0.5f);
            File.WriteAllText(Path.Combine(dir, "marks.json"), MiniJson.Write(marks));
            File.WriteAllText(Path.Combine(dir, "receipts.json"), MiniJson.Write(receipts.Select(r => (object)new Dictionary<string, object>
            {
                ["requestId"] = r.RequestId, ["outcomeId"] = r.OutcomeId, ["fieldsFlow"] = r.FieldsFlow, ["fieldsSupplyPct"] = r.FieldsSupplyPct, ["creekFlow"] = r.CreekFlow,
                ["nursery"] = r.Nursery, ["spent"] = r.Spent.ToDictionary(kv => kv.Key, kv => (object)kv.Value), ["surprises"] = r.Surprises.Cast<object>().ToList(),
                ["plan"] = r.Plan.Select(p => (object)$"{p.Seg} {p.Cell} {p.Model} r{p.Rot}").ToList(),
            }).ToList()));
            File.WriteAllText(Path.Combine(dir, "axes.txt"), $"axis map Blender->Unity\n{Kit.Axes}\nresidual {Kit.AxisSolveError:0.0000} m\n");
            Application.Quit();
        }
    }
}
