// C# port of tools/qingxi-waterworks-b/src/waterworks-core.mjs for the Unity test scene.
//
// Same rules, same messages, same numbers: the EditMode tests replay tests/scenarios.json and compare every step with
// tests/golden.json, which the JS core writes. Pure and deterministic (no clock, no random). Materials are local
// display stock only; nothing here talks to the real inventory or the server (see ../../../../CONTRACT.md).
using System;
using System.Collections.Generic;
using System.Linq;

namespace Qingxi.Waterworks
{
    public sealed class Piece
    {
        public string Type, Seg; public int Rot; public bool? Open;
        public Piece Clone() => new Piece { Type = Type, Seg = Seg, Rot = Rot, Open = Open };
    }

    /// <summary>Cell key -> piece, keeping JS object key order (a replaced key keeps its slot; issues come out in this order).</summary>
    public sealed class Pieces
    {
        readonly List<string> order = new List<string>(); readonly Dictionary<string, Piece> map = new Dictionary<string, Piece>();
        public Piece Get(string k) => map.TryGetValue(k, out var p) ? p : null;
        public void Set(string k, Piece p) { if (!map.ContainsKey(k)) order.Add(k); map[k] = p; }
        public void Remove(string k) { if (map.Remove(k)) order.Remove(k); }
        public int Count => order.Count;
        public IEnumerable<KeyValuePair<string, Piece>> Entries => order.Select(k => new KeyValuePair<string, Piece>(k, map[k]));
        public Pieces Clone() { var c = new Pieces(); foreach (var k in order) c.Set(k, map[k].Clone()); return c; }
    }

    public sealed class Issue { public string Level = "error", Code, Side, Message; public int[] At; }
    public sealed class Leak { public int[] At; public double Q; public string Why, Side; }
    public sealed class ReachInfo { public string From, InSide; public int Order; }
    public sealed class NurseryImpact { public int Score, Level; public string Text; }

    public sealed class Sim
    {
        public Dictionary<string, double> Wet = new Dictionary<string, double>();
        public List<(string a, string b)> Links = new List<(string, string)>();
        public Dictionary<string, ReachInfo> Reach = new Dictionary<string, ReachInfo>();
        public List<Issue> Issues = new List<Issue>();
        public List<string> Risks = new List<string>();
        public double Fields, Creek; public int Supply;
        public List<Leak> Leaks = new List<Leak>();
        public NurseryImpact Nursery;
    }

    public sealed class Quote { public Dictionary<string, int> Need = new Dictionary<string, int>(); public List<(string material, int need, int have)> Short = new List<(string, int, int)>(); }
    public sealed class Check { public bool Ok; public List<Issue> Issues; public Sim Sim; }

    public sealed class PlanEntry { public string Seg, Cell, Type, Model; public int Rot; public bool? Open; }
    public sealed class Receipt
    {
        public string RequestId, ProjectId = "qingxi-waterworks-b:public-channel", OutcomeId, Direction, Role = "waterworks_builder";
        public int Attempt; public List<string> ObservationIds; public Dictionary<string, int> Spent;
        public List<PlanEntry> Plan; public double FieldsFlow, CreekFlow; public int FieldsSupplyPct, NurseryScore; public string Nursery;
        public List<Leak> Leaks; public List<string> Surprises;
    }

    public sealed class Result
    {
        public bool Ok; public string Code, Message; public bool? Open, Replay; public Receipt Receipt; public List<Issue> Issues;
        public static Result Yes() => new Result { Ok = true };
        public static Result No(string code, string msg) => new Result { Ok = false, Code = code, Message = msg };
    }

    public sealed class GameState
    {
        public List<string> ObservationIds; public Dictionary<string, bool> Known;
        public Pieces Pieces = new Pieces(); public string Direction; public int NextSeg = 1;
        public List<(Pieces pieces, string direction, int nextSeg)> History = new List<(Pieces, string, int)>(), Future = new List<(Pieces, string, int)>();
        public string SessionId; public int Attempt = 1; public Dictionary<string, int> Stock;
        public Dictionary<string, Receipt> Receipts = new Dictionary<string, Receipt>(); public string Finished; public List<string> Log = new List<string>();
    }

    public sealed class Rules
    {
        public readonly Site Site;
        const double FAST = 40;
        static readonly string[] NURSERY_ZH = { "安全", "輕擾", "受驚擾" };
        public Rules(Site site) { Site = site; }

        static double JsRound(double v) => Math.Floor(v + 0.5);
        static double R1(double v) => JsRound(v * 10) / 10;

        public Dictionary<string, bool> KnownHazards(IEnumerable<string> ids)
        {
            var set = new HashSet<string>(ids.Where(Site.Observations.ContainsKey));
            return Site.Observations.Values.ToDictionary(o => o.Reveals, o => set.Any(id => Site.Observations[id].Reveals == o.Reveals));
        }

        public GameState NewGame(IEnumerable<string> observationIds, string sessionId = "local") => new GameState
        {
            ObservationIds = observationIds.ToList(), Known = KnownHazards(observationIds), SessionId = sessionId, Stock = new Dictionary<string, int>(Site.Stock),
        };

        public string PieceName(Piece p) => $"{p.Seg} {Site.Pieces[p.Type].Label}";
        string PortName(Piece p, string side) { int i = Array.IndexOf(Site.SidesOf(p), side); return $"{Site.SIDE_ZH[side]}接口（{Site.Pieces[p.Type].Ports[i]}）"; }
        static (Pieces, string, int) Snap(GameState s) => (s.Pieces.Clone(), s.Direction, s.NextSeg);
        static void Commit(GameState s, string label) { s.History.Add(Snap(s)); s.Future.Clear(); s.Log.Add(label); }
        static Result Locked(GameState s) => s.Finished != null ? Result.No("FINISHED", "這個方案已完成。按「重試」開一個新方案。") : null;
        static void Restore(GameState s, (Pieces pieces, string direction, int nextSeg) v) { s.Pieces = v.pieces; s.Direction = v.direction; s.NextSeg = v.nextSeg; }

        // ------------------------------------------------------------------ edits (all undoable)
        public Result Place(GameState s, int x, int y, string type, int rot = 0)
        {
            var l = Locked(s); if (l != null) return l;
            if (type == null || !Site.Pieces.ContainsKey(type)) return Result.No("NO_PIECE", $"沒有「{type}」這種件");
            if (!Site.SlotOpen(x, y)) return Result.No("NO_SLOT", Site.Inside(x, y) && Site.Has("rock", x, y) ? "這格有大石，放不下槽件" : "這裡不能放");
            if (s.Direction == "protect_nursery" && (Site.Has("nursery", x, y) || Site.NearNursery(x, y)))
                return Result.No("NURSERY_FORBIDDEN", "已選「保護育幼區」：育幼區和它旁邊一圈不施工");
            Commit(s, $"place {type} {x},{y} r{rot}");
            var old = s.Pieces.Get(Site.Key(x, y));
            var seg = old?.Seg ?? $"S{s.NextSeg++:00}";
            s.Pieces.Set(Site.Key(x, y), new Piece { Type = type, Rot = ((rot % 4) + 4) % 4, Seg = seg, Open = Site.Pieces[type].Gate ? true : (bool?)null });
            return Result.Yes();
        }

        public Result Rotate(GameState s, int x, int y)
        {
            var l = Locked(s); if (l != null) return l;
            var p = s.Pieces.Get(Site.Key(x, y)); if (p == null) return Result.No("EMPTY", "這格沒有槽件");
            Commit(s, $"rotate {x},{y}"); s.Pieces.Get(Site.Key(x, y)).Rot = (p.Rot + 1) % 4; return Result.Yes();
        }

        public Result Remove(GameState s, int x, int y)
        {
            var l = Locked(s); if (l != null) return l;
            if (s.Pieces.Get(Site.Key(x, y)) == null) return Result.No("EMPTY", "這格沒有槽件");
            Commit(s, $"remove {x},{y}"); s.Pieces.Remove(Site.Key(x, y)); return Result.Yes();
        }

        public Result ToggleGate(GameState s, int x, int y)
        {
            var l = Locked(s); if (l != null) return l;
            var p = s.Pieces.Get(Site.Key(x, y)); if (p == null || !Site.Pieces[p.Type].Gate) return Result.No("NO_GATE", "這格不是閘板");
            Commit(s, $"gate {x},{y}"); p = s.Pieces.Get(Site.Key(x, y)); p.Open = !(p.Open ?? true); return new Result { Ok = true, Open = p.Open };
        }

        public Result SetDirection(GameState s, string dir)
        {
            var l = Locked(s); if (l != null) return l;
            if (dir == null || !Site.Directions.ContainsKey(dir)) return Result.No("NO_DIRECTION", "沒有這個處理方向");
            if (dir == "protect_nursery")
            {
                var bad = s.Pieces.Entries.Where(e => { var (x, y) = Site.Cell(e.Key); return Site.Has("nursery", x, y) || Site.NearNursery(x, y); }).ToList();
                if (bad.Count > 0) return Result.No("NURSERY_FORBIDDEN", $"先移走育幼區旁的 {string.Join("、", bad.Select(b => b.Value.Seg))}，才能選「保護育幼區」");
            }
            Commit(s, $"direction {dir}"); s.Direction = dir; return Result.Yes();
        }

        public Result Undo(GameState s)
        {
            if (s.Finished != null) return Result.No("FINISHED", "已完成的方案不能撤回；按「重試」開新方案");
            if (s.History.Count == 0) return Result.No("NOTHING", "沒有可撤回的步驟");
            s.Future.Add(Snap(s)); var h = s.History[s.History.Count - 1]; s.History.RemoveAt(s.History.Count - 1); Restore(s, h); s.Log.Add("undo"); return Result.Yes();
        }

        public Result Redo(GameState s)
        {
            if (s.Finished != null) return Result.No("FINISHED", "已完成的方案不能重做");
            if (s.Future.Count == 0) return Result.No("NOTHING", "沒有可重做的步驟");
            s.History.Add(Snap(s)); var f = s.Future[s.Future.Count - 1]; s.Future.RemoveAt(s.Future.Count - 1); Restore(s, f); s.Log.Add("redo"); return Result.Yes();
        }

        // ------------------------------------------------------------------ water
        sealed class Node { public int X, Y; public Piece P; public string InSide; public List<Kid> Kids = new List<Kid>(); }
        sealed class Kid { public string Side, Kind, Target; public Node Node; }

        public Sim Simulate(GameState s, bool real = false)
        {
            var S = Site; var sim = new Sim(); double outFields = 0, outCreek = 0;
            var k0 = real ? new Dictionary<string, bool> { ["crack"] = true, ["silt"] = true, ["nursery"] = true } : s.Known;
            bool hzCrack = k0["crack"] && s.Direction != "restore_channel", hzSilt = k0["silt"] && s.Direction != "clear_silt", hzNursery = k0["nursery"];
            var st = Site.STEP[S.SourceOut]; int fx = S.SourceX + st.dx, fy = S.SourceY + st.dy;
            var p0 = s.Pieces.Get(Site.Key(fx, fy));
            bool rooted = p0 != null && S.SidesOf(p0).Contains(Site.OPP[S.SourceOut]);
            if (!rooted)
                sim.Issues.Add(new Issue { Code = "SOURCE_OPEN", At = new[] { fx, fy }, Message = p0 != null
                    ? $"水源 B01 的出水口（北，Out_Front）對著 {PieceName(p0)} 的側牆。把 {p0.Seg} 轉到南面有接口。"
                    : "水源 B01 的出水口（北，Out_Front）還沒接上。在它正北那格放一段南面有接口的槽。" });
            var seen = new HashSet<string>(); var tree = new List<Node>();

            Node Walk(int x, int y, string inSide, string from)
            {
                var k = Site.Key(x, y); var p = s.Pieces.Get(k);
                if (seen.Contains(k)) { sim.Issues.Add(new Issue { Code = "LOOP", At = new[] { x, y }, Message = $"{PieceName(p)} 讓水路繞回自己，拆掉其中一段" }); return null; }
                seen.Add(k); var node = new Node { X = x, Y = y, P = p, InSide = inSide }; tree.Add(node);
                sim.Reach[k] = new ReachInfo { From = from, InSide = inSide, Order = sim.Reach.Count };
                var spec = S.Pieces[p.Type]; var outlet = spec.Outlet != null ? Site.RotSide(spec.Outlet, p.Rot) : null;
                foreach (var side in outlet != null ? new[] { outlet } : S.SidesOf(p))
                {
                    if (side == inSide) continue;
                    var d = Site.STEP[side]; int nx = x + d.dx, ny = y + d.dy; var q = S.Inside(nx, ny) ? s.Pieces.Get(Site.Key(nx, ny)) : null;
                    if (outlet != null)
                    {
                        var t = q != null ? null : S.TargetAt(x, y, side);
                        if (t != null) { node.Kids.Add(new Kid { Side = side, Kind = "target", Target = t.Id }); continue; }
                        sim.Issues.Add(new Issue { Code = "APRON_MISPLACED", At = new[] { x, y }, Side = side, Message = q != null
                            ? $"{PieceName(p)} 的出水口朝{Site.SIDE_ZH[side]}，被 {PieceName(q)} 擋住。"
                            : $"{PieceName(p)} 的出水口朝{Site.SIDE_ZH[side]}，{(S.Inside(nx, ny) ? "對著空地" : "對著場地邊")}；收尾溢流台要放在村田進水口（北緣）或溪道回流口（西緣），出水口朝外。" });
                        node.Kids.Add(new Kid { Side = side, Kind = "leak" }); continue;
                    }
                    if (q != null && S.SidesOf(q).Contains(Site.OPP[side]))
                    {
                        sim.Links.Add((k, Site.Key(nx, ny))); var c = Walk(nx, ny, Site.OPP[side], k);
                        if (c != null) node.Kids.Add(new Kid { Side = side, Kind = "pipe", Node = c });
                        continue;
                    }
                    if (q != null)
                    {
                        sim.Issues.Add(new Issue { Code = "PORT_MISMATCH", At = new[] { x, y }, Side = side, Message =
                            $"{PieceName(p)} 的{PortName(p, side)}對著 {PieceName(q)} 的側牆，沒有接口。把 {q.Seg} 轉向讓接口朝{Site.SIDE_ZH[Site.OPP[side]]}，或換一種槽件。" });
                        node.Kids.Add(new Kid { Side = side, Kind = "leak" }); continue;
                    }
                    var tg = S.TargetAt(x, y, side);
                    var where = tg != null ? $"直接沖進{tg.Label}會沖壞田埂／岸邊，要放收尾溢流台" : !S.Inside(nx, ny) ? "對著場地邊" : S.Has("rock", nx, ny) ? "對著大石" : "開著沒接東西";
                    sim.Issues.Add(new Issue { Code = "OPEN_END", At = new[] { x, y }, Side = side, Message = $"{PieceName(p)} 的{PortName(p, side)}{where}，水會從這裡流掉。接上下一段或放收尾溢流台。" });
                    node.Kids.Add(new Kid { Side = side, Kind = "leak" });
                }
                return node;
            }

            var root = rooted ? Walk(fx, fy, Site.OPP[S.SourceOut], "source") : null;

            bool Open(Node n)
            {
                if (S.Pieces[n.P.Type].Gate && n.P.Open == false) return false;
                return n.Kids.Any(c => c.Kind != "pipe" || Open(c.Node));
            }

            void Flow(Node n, double q)
            {
                int x = n.X, y = n.Y;
                q *= 1 - (n.P.Type == "worn" && !S.Has("oldChannel", x, y) ? 0.05 : S.Pieces[n.P.Type].Loss);
                if (hzCrack && S.Has("crack", x, y)) { sim.Leaks.Add(new Leak { At = new[] { x, y }, Q = R1(q * S.Loss["crack"]), Why = "crack" }); q *= 1 - S.Loss["crack"]; }
                if (hzSilt && S.Has("silt", x, y)) q *= 1 - S.Loss["silt"];
                if (S.Has("seep", x, y)) { sim.Leaks.Add(new Leak { At = new[] { x, y }, Q = R1(q * S.Loss["seep"]), Why = "seep" }); q *= 1 - S.Loss["seep"]; }
                sim.Wet[Site.Key(x, y)] = R1(q);
                if (S.Pieces[n.P.Type].Gate && n.P.Open == false) return;
                var ways = n.Kids.Where(c => c.Kind != "pipe" || Open(c.Node)).ToList();
                foreach (var c in ways)
                {
                    var share = q / ways.Count;
                    if (c.Kind == "pipe") Flow(c.Node, share);
                    else if (c.Kind == "target") { if (c.Target == "fields") outFields += share; else outCreek += share; }
                    else sim.Leaks.Add(new Leak { At = new[] { x, y }, Side = c.Side, Q = R1(share), Why = "open" });
                }
            }

            if (root != null) Flow(root, S.SourceFlow);
            foreach (var e in s.Pieces.Entries)
                if (!seen.Contains(e.Key)) { var (x, y) = Site.Cell(e.Key); sim.Issues.Add(new Issue { Code = "DRY", At = new[] { x, y }, Message = $"{PieceName(e.Value)} 沒有接到水（孤立的一段）。接回水路，或把它拆掉。" }); }
            foreach (var n in tree)
                if (S.Pieces[n.P.Type].Gate && n.P.Open == false && outFields == 0)
                    sim.Issues.Add(new Issue { Code = "GATE_CLOSED", At = new[] { n.X, n.Y }, Message = $"{PieceName(n.P)} 關著，水到不了村田。轉動閘輪把它打開（G）。" });
            int nursery = 0;
            if (hzNursery || real)
            {
                foreach (var e in s.Pieces.Entries)
                {
                    var (x, y) = Site.Cell(e.Key);
                    if (S.Has("nursery", x, y)) nursery += 3;
                    else if (S.NearNursery(x, y)) nursery += 1 + ((sim.Wet.TryGetValue(e.Key, out var w) ? w : 0) > FAST ? 1 : 0);
                }
                if (s.Direction == "clear_silt") nursery += 1;
            }
            int level = nursery == 0 ? 0 : nursery < 4 ? 1 : 2;
            bool WetIn(string terrain) => sim.Wet.Keys.Any(k => { var (x, y) = Site.Cell(k); return S.Has(terrain, x, y); });
            if (!s.Known["crack"] && WetIn("crack")) sim.Risks.Add(S.Unknown["crack"]);
            if (!s.Known["silt"] && WetIn("silt")) sim.Risks.Add(S.Unknown["silt"]);
            if (!s.Known["nursery"] && s.Pieces.Entries.Any(e => { var (x, y) = Site.Cell(e.Key); return S.Has("nursery", x, y) || S.NearNursery(x, y); })) sim.Risks.Add(S.Unknown["nursery"]);
            sim.Fields = R1(outFields); sim.Creek = R1(outCreek);
            sim.Supply = (int)Math.Min(100, JsRound(outFields / S.FieldDemand * 100));
            sim.Nursery = new NurseryImpact { Score = nursery, Level = level, Text = NURSERY_ZH[level] };
            return sim;
        }

        // ------------------------------------------------------------------ cost, checks, finish
        public Quote Quote(GameState s)
        {
            var q = new Quote();
            void Add(Dictionary<string, int> c) { foreach (var kv in c) q.Need[kv.Key] = (q.Need.TryGetValue(kv.Key, out var n) ? n : 0) + kv.Value; }
            foreach (var e in s.Pieces.Entries)
            {
                var (x, y) = Site.Cell(e.Key);
                Add(e.Value.Type == "worn" && !Site.Has("oldChannel", x, y) ? new Dictionary<string, int> { ["stone"] = 2 } : Site.Pieces[e.Value.Type].Cost);
            }
            if (s.Direction != null) Add(Site.Directions[s.Direction].Cost);
            foreach (var kv in q.Need)
            {
                int have = s.Stock.TryGetValue(kv.Key, out var h) ? h : 0;
                if (kv.Value > have) q.Short.Add((kv.Key, kv.Value, have));
            }
            return q;
        }

        public Check Check(GameState s)
        {
            var sim = Simulate(s); var issues = new List<Issue>(sim.Issues);
            if (s.Direction == null) issues.Add(new Issue { Code = "NO_DIRECTION", Message = "還沒選處理方向：修復舊渠、先清淤，或保護育幼區。" });
            if (sim.Issues.Count == 0 && sim.Fields <= 0) issues.Add(new Issue { Code = "NO_FIELDS", Message = "水沒有送到村田進水口（北緣）。" });
            if (s.Direction == "clear_silt" && sim.Creek <= 0)
                issues.Add(new Issue { Code = "NO_DIVERSION", Message = "清淤期間要暫時導流：用三通分一支水到溪道回流口（西緣），出口放收尾溢流台。" });
            foreach (var (m, need, have) in Quote(s).Short)
                issues.Add(new Issue { Code = "NOT_ENOUGH", Message = $"{Site.StockZh[m]}不夠：需要 {need}，展示材料只有 {have}。" });
            return new Check { Ok = issues.Count == 0, Issues = issues, Sim = sim };
        }

        public static string RequestIdFor(GameState s) => $"ww-{s.SessionId}-a{s.Attempt}";

        /// <summary>Finish once per requestId: a resend returns the stored receipt and never deducts materials twice.</summary>
        public Result Finish(GameState s, string requestId = null)
        {
            requestId ??= RequestIdFor(s);
            if (s.Receipts.TryGetValue(requestId, out var stored)) return new Result { Ok = true, Replay = true, Receipt = stored };
            if (s.Finished != null) return new Result { Ok = false, Code = "ALREADY_FINISHED", Message = "這個方案已用另一個請求完成。", Receipt = s.Receipts[s.Finished] };
            var c = Check(s); if (!c.Ok) return new Result { Ok = false, Code = "NOT_READY", Issues = c.Issues };
            var real = Simulate(s, real: true); var need = Quote(s).Need;
            foreach (var kv in need) s.Stock[kv.Key] -= kv.Value;
            var surprises = new List<string>();
            if (real.Fields < c.Sim.Fields) surprises.Add($"實際到村田 {Num(real.Fields)} L/s，比預估 {Num(c.Sim.Fields)} 少：{(real.Leaks.Any(l => l.Why == "crack") ? "舊渠破槽在漏水" : "泥沙擋住了水")}。");
            if (real.Nursery.Level > c.Sim.Nursery.Level) surprises.Add($"東側原來是育幼區，施工驚擾了牠們（{real.Nursery.Text}）。");
            var receipt = new Receipt
            {
                RequestId = requestId, Attempt = s.Attempt, OutcomeId = Site.Outcomes[s.Direction], Direction = s.Direction, ObservationIds = s.ObservationIds.ToList(),
                Spent = new Dictionary<string, int>(need),
                Plan = s.Pieces.Entries.Select(e => new PlanEntry { Seg = e.Value.Seg, Cell = e.Key, Type = e.Value.Type, Model = Site.Pieces[e.Value.Type].Model, Rot = e.Value.Rot, Open = e.Value.Open })
                    .OrderBy(p => p.Seg, StringComparer.Ordinal).ToList(),
                FieldsFlow = real.Fields, FieldsSupplyPct = real.Supply, CreekFlow = real.Creek, Nursery = real.Nursery.Text, NurseryScore = real.Nursery.Score,
                Leaks = real.Leaks.Select(l => new Leak { At = l.At, Q = l.Q, Why = l.Why }).ToList(), Surprises = surprises,
            };
            s.Receipts[requestId] = receipt; s.Finished = requestId; s.Log.Add($"finish {requestId}");
            return new Result { Ok = true, Replay = false, Receipt = receipt };
        }

        /// <summary>New attempt: same session, fresh local display stock, new requestId. Earlier receipts stay for comparison.</summary>
        public Result Retry(GameState s)
        {
            s.Attempt += 1; s.Finished = null; s.Stock = new Dictionary<string, int>(Site.Stock); s.History.Clear(); s.Future.Clear(); s.Log.Add($"retry a{s.Attempt}");
            return Result.Yes();
        }

        /// <summary>Number as JS prints it in a template string (68.6, 70, 0.5).</summary>
        public static string Num(double v) => v.ToString("R", System.Globalization.CultureInfo.InvariantCulture);
    }
}
