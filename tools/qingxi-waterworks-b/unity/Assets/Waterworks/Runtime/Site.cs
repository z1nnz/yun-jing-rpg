// Site and piece tables, loaded from Resources/waterworks-site.json — the JS core's own export (tests/make-golden.mjs),
// so the board, costs and terrain are never retyped here.
using System.Collections.Generic;
using System.Linq;
using static Qingxi.Waterworks.MiniJson;

namespace Qingxi.Waterworks
{
    public sealed class PieceSpec
    {
        public string Id, Label, Model, Note, Outlet;
        public string[] Sides, Ports;
        public Dictionary<string, int> Cost;
        public double Loss;
        public bool Gate;
    }

    public sealed class DirectionSpec { public string Id, Label, Text; public Dictionary<string, int> Cost; }
    public sealed class TargetSpec { public string Id, Label, Side; public List<(int x, int y)> Cells; }
    public sealed class FixtureSpec { public string Id, Label; public List<string> ObservationIds; }
    public sealed class ObservationSpec { public string Id, Label, Reveals, Text; }

    public sealed class Site
    {
        public int W, H, FieldDemand;
        public readonly Dictionary<string, PieceSpec> Pieces = new Dictionary<string, PieceSpec>();
        public readonly Dictionary<string, DirectionSpec> Directions = new Dictionary<string, DirectionSpec>();
        public readonly List<TargetSpec> Targets = new List<TargetSpec>();
        public readonly Dictionary<string, List<(int x, int y)>> Terrain = new Dictionary<string, List<(int x, int y)>>();
        public readonly Dictionary<string, double> Loss = new Dictionary<string, double>();
        public readonly Dictionary<string, FixtureSpec> Fixtures = new Dictionary<string, FixtureSpec>();
        public readonly Dictionary<string, ObservationSpec> Observations = new Dictionary<string, ObservationSpec>();
        public readonly Dictionary<string, string> Unknown = new Dictionary<string, string>();
        public readonly Dictionary<string, int> Stock = new Dictionary<string, int>();
        public readonly Dictionary<string, string> StockZh = new Dictionary<string, string>();
        public readonly Dictionary<string, string> Outcomes = new Dictionary<string, string>();
        public int SourceX, SourceY, SourceFlow; public string SourceOut, SourceModel, SourcePort;

        public static readonly string[] SIDES = { "N", "E", "S", "W" };
        public static readonly Dictionary<string, (int dx, int dy)> STEP = new Dictionary<string, (int, int)> { ["N"] = (0, 1), ["E"] = (1, 0), ["S"] = (0, -1), ["W"] = (-1, 0) };
        public static readonly Dictionary<string, string> OPP = new Dictionary<string, string> { ["N"] = "S", ["E"] = "W", ["S"] = "N", ["W"] = "E" };
        public static readonly Dictionary<string, string> SIDE_ZH = new Dictionary<string, string> { ["N"] = "北", ["E"] = "東", ["S"] = "南", ["W"] = "西" };

        static Dictionary<string, int> Costs(object v) => O(v).ToDictionary(kv => kv.Key, kv => I(kv.Value));
        static List<(int, int)> Cells(object v) => L(v).Select(c => (I(L(c)[0]), I(L(c)[1]))).ToList();

        public static Site FromJson(string json)
        {
            var j = O(Parse(json)); var s = new Site { W = I(j["W"]), H = I(j["H"]), FieldDemand = I(j["FIELD_DEMAND"]) };
            foreach (var kv in O(j["PIECES"]))
            {
                var p = O(kv.Value);
                s.Pieces[kv.Key] = new PieceSpec
                {
                    Id = kv.Key, Label = S(p["label"]), Model = S(p["model"]), Note = p.TryGetValue("note", out var n) ? S(n) : null,
                    Outlet = p.TryGetValue("outlet", out var o) ? S(o) : null, Sides = L(p["sides"]).Select(S).ToArray(), Ports = L(p["ports"]).Select(S).ToArray(),
                    Cost = Costs(p["cost"]), Loss = D(p["loss"]), Gate = p.TryGetValue("gate", out var g) && (bool)g,
                };
            }
            foreach (var kv in O(j["DIRECTIONS"])) { var d = O(kv.Value); s.Directions[kv.Key] = new DirectionSpec { Id = kv.Key, Label = S(d["label"]), Text = S(d["text"]), Cost = Costs(d["cost"]) }; }
            foreach (var t in L(j["TARGETS"])) { var d = O(t); s.Targets.Add(new TargetSpec { Id = S(d["id"]), Label = S(d["label"]), Side = S(d["side"]), Cells = Cells(d["cells"]) }); }
            foreach (var kv in O(j["TERRAIN"])) s.Terrain[kv.Key] = Cells(kv.Value);
            foreach (var kv in O(j["LOSS"])) s.Loss[kv.Key] = D(kv.Value);
            foreach (var kv in O(j["FIXTURES"])) { var d = O(kv.Value); s.Fixtures[kv.Key] = new FixtureSpec { Id = S(d["id"]), Label = S(d["label"]), ObservationIds = L(d["observationIds"]).Select(S).ToList() }; }
            foreach (var kv in O(j["OBSERVATIONS"])) { var d = O(kv.Value); s.Observations[kv.Key] = new ObservationSpec { Id = kv.Key, Label = S(d["label"]), Reveals = S(d["reveals"]), Text = S(d["text"]) }; }
            foreach (var kv in O(j["UNKNOWN"])) s.Unknown[kv.Key] = S(kv.Value);
            foreach (var kv in O(j["STOCK"])) s.Stock[kv.Key] = I(kv.Value);
            foreach (var kv in O(j["STOCK_ZH"])) s.StockZh[kv.Key] = S(kv.Value);
            foreach (var kv in O(j["OUTCOMES"])) s.Outcomes[kv.Key] = S(kv.Value);
            var src = O(j["SOURCE"]);
            s.SourceX = I(src["x"]); s.SourceY = I(src["y"]); s.SourceOut = S(src["out"]); s.SourceModel = S(src["model"]); s.SourcePort = S(src["port"]); s.SourceFlow = I(src["flow"]);
            return s;
        }

        public static string Key(int x, int y) => $"{x},{y}";
        public static (int x, int y) Cell(string key) { var p = key.Split(','); return (int.Parse(p[0]), int.Parse(p[1])); }
        public bool Has(string terrain, int x, int y) => Terrain[terrain].Contains((x, y));
        public bool Inside(int x, int y) => x >= 0 && y >= 0 && x < W && y < H;
        public static string RotSide(string side, int r) => SIDES[(System.Array.IndexOf(SIDES, side) + r) % 4];
        public string[] SidesOf(Piece p) => Pieces[p.Type].Sides.Select(s => RotSide(s, p.Rot)).ToArray();
        public bool NearNursery(int x, int y) => Terrain["nursery"].Any(c => System.Math.Abs(c.x - x) + System.Math.Abs(c.y - y) == 1);
        public bool SlotOpen(int x, int y) => Inside(x, y) && !Has("rock", x, y) && !(x == SourceX && y == SourceY);
        public TargetSpec TargetAt(int x, int y, string side) => Targets.FirstOrDefault(t => t.Side == side && t.Cells.Contains((x, y)));
    }
}
