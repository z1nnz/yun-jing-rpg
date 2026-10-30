using System;
using System.Collections.Generic;

/// Home-furnace alchemy rules, ported from Alchemy V2 (yun-jing-rpg: packages/content/alchemy.json,
/// services/api/src/alchemy.ts simulate()/judge(), apps/game/.../AlchemySim.cs). Same constants, tick order and
/// scoring so the home furnace plays like the workshop. Home version: one recipe (回春丹) and the herbs arrive
/// already prepared (青靈草 研末, 淨水蓮 陰乾), so the grinding / drying stations are not part of this room.
public static class HomeAlchemy
{
    public class Phase { public string label; public double low, high, seconds; }

    // fire constants (alchemy.json "fire")
    public const double Step = .1, Ambient = 15, PiecePower = 4.3, VentPowerBase = .45, VentPowerScale = .55, LossBase = .12, LossVent = .03,
        LossLidOpen = .25, BurnSeconds = 20, VentBurnBase = .7, VentBurnScale = .6, ScorchLine = 95, ScorchLimitSeconds = 4,
        StabilityFloor = .4, StabilityFull = .95;
    public const int MaxBurning = 6;

    // recipe huichun
    public const string Recipe = "回春丹", Lead = "青靈草", Minor = "淨水蓮", Fuel = "松柴";
    public const int LeadQty = 2, MinorQty = 1, Water = 2;
    public static readonly string[] Order = { "water", Minor, Lead };
    public static readonly Phase[] Phases =
    {
        new Phase { label = "文火溫藥", low = 22, high = 40, seconds = 10 },
        new Phase { label = "中火融藥", low = 45, high = 62, seconds = 12 },
    };
    public const double CondenseBest0 = 2, CondenseBest1 = 6, CondenseZero0 = -1, CondenseZero1 = 14, Overcook = 22;

    static readonly (string label, int min)[] Grades = { ("凡品", 45), ("良品", 65), ("上品", 80), ("極品", 92) };

    /// Furnace state stepped in fixed 0.1 s ticks (AlchemySim.Furnace).
    public sealed class Furnace
    {
        readonly List<double> burning = new List<double>();
        readonly HashSet<string> charged = new HashSet<string>();
        public double T = Ambient, Peak = Ambient, InBand, Active, Scorch, Vent = .5;
        public bool LidClosed = true, Ignited, Warmed;
        public int Loaded, FuelUsed, WaterAdded, PhaseIndex, Tick = -1;
        public double[] Progress = new double[Phases.Length];
        public int? CompleteTick, CondenseTick;
        public readonly List<string> OrderLog = new List<string>();
        public int Burning => burning.Count;
        public bool IsCharged(string h) => charged.Contains(h);
        public bool AllCharged => charged.Contains(Lead) && charged.Contains(Minor);
        public double BurnLeft { get { double m = 0; foreach (var b in burning) m = Math.Max(m, b); return m; } }

        /// Fresh batch that keeps the fire already burning in the hearth.
        public Furnace Next()
        {
            var f = new Furnace { T = T, Peak = T, Vent = Vent, LidClosed = LidClosed, Ignited = Ignited };
            f.burning.AddRange(burning); return f;
        }

        public void Water() { if (!OrderLog.Contains("water")) OrderLog.Add("water"); WaterAdded++; }
        public void Charge(string herb) { charged.Add(herb); OrderLog.Add(herb); }
        public void Lid(bool closed) { LidClosed = closed; }
        public void AddFuel() { FuelUsed++; if (Ignited && burning.Count > 0 && burning.Count < MaxBurning) burning.Add(BurnSeconds); else Loaded++; }
        public void SetVent(double v) { Vent = v; }
        public void Ignite() { if (Loaded > 0) { Ignited = true; while (Loaded > 0 && burning.Count < MaxBurning) { burning.Add(BurnSeconds); Loaded--; } } }
        public void Condense() { if (CondenseTick == null) CondenseTick = Tick; }

        public void StepTick()
        {
            Tick++;
            double dt = Step;
            double power = burning.Count * PiecePower * (VentPowerBase + VentPowerScale * Vent);
            double loss = LossBase + LossVent * Vent + (LidClosed ? 0 : LossLidOpen);
            T = T + (power - loss * (T - Ambient)) * dt;
            double burn = dt * (VentBurnBase + VentBurnScale * Vent);
            for (int i = burning.Count - 1; i >= 0; i--) { burning[i] -= burn; if (!(burning[i] > 1e-9)) burning.RemoveAt(i); }
            if (T > Peak) Peak = T;
            if (CondenseTick != null) return;           // the batch is judged; the hearth keeps burning for show
            bool all = AllCharged;
            if (all && T > ScorchLine) Scorch += dt;
            if (all && Ignited && PhaseIndex < Phases.Length)
            {
                var p = Phases[PhaseIndex]; bool inside = T >= p.low && T <= p.high;
                if (inside) Warmed = true;
                if (Warmed) Active += dt;
                if (inside)
                {
                    InBand += dt;
                    if (LidClosed) { Progress[PhaseIndex] += dt; if (Progress[PhaseIndex] >= p.seconds - 1e-9) { PhaseIndex++; if (PhaseIndex == Phases.Length) CompleteTick = Tick; } }
                }
            }
        }

        public double SinceComplete => CompleteTick == null ? -1 : ((CondenseTick ?? Tick) - CompleteTick.Value) / 10.0;
    }

    public class Outcome { public bool success; public string label = "失敗"; public int score; public double ratio, prep, fire, condense; public List<string> reasons = new List<string>(); }

    /// judge() for the home recipe (no talent / root / sect modifiers).
    public static Outcome Judge(Furnace f)
    {
        var o = new Outcome();
        int mismatch = 0; for (int i = 0; i < Order.Length; i++) if (i >= f.OrderLog.Count || f.OrderLog[i] != Order[i]) mismatch++;
        double order = Math.Max(0, 1 - mismatch / (double)Order.Length);
        if (mismatch > 0) o.reasons.Add("藥液渾濁，不見清亮。");
        double water = f.WaterAdded == Water ? 1 : Math.Abs(f.WaterAdded - Water) == 1 ? .5 : 0;
        if (water < 1) o.reasons.Add(f.WaterAdded < Water ? "爐底的藥液偏稠，黏著爐壁。" : "爐底的藥液偏稀，丹面起了水紋。");
        o.ratio = 1;                                    // fixed 2:1 portion from the recipe card
        o.prep = 1 * .6 + order * .25 + water * .15;    // herbs come prepared
        double held = f.Active > 0 ? Math.Min(1, f.InBand / f.Active) : 0;
        o.fire = Math.Max(0, Math.Min(1, (held - StabilityFloor) / (StabilityFull - StabilityFloor)));
        if (f.WaterAdded == 0) { o.reasons.Insert(0, "爐底乾裂，藥材燒成黑炭。"); return o; }
        if (f.Scorch > ScorchLimitSeconds) { o.reasons.Insert(0, "爐裡冒出黑煙，藥材焦糊，嗆得睜不開眼。"); return o; }
        if (f.CompleteTick == null) { o.reasons.Insert(0, f.CondenseTick != null ? "收起的只是一團軟泥。" : "爐中藥液還在翻滾。"); return o; }
        if (f.CondenseTick == null) { o.reasons.Insert(0, "香氣轉焦，爐裡只剩焦黑的丹殼。"); return o; }
        double d = f.SinceComplete;
        if (d >= Overcook) { o.reasons.Insert(0, "香氣轉焦，爐裡只剩焦黑的丹殼。"); return o; }
        o.condense = d >= CondenseBest0 && d <= CondenseBest1 ? 1
            : d < CondenseBest0 ? Math.Max(0, (d - CondenseZero0) / (CondenseBest0 - CondenseZero0))
            : Math.Max(0, 1 - (d - CondenseBest1) / (CondenseZero1 - CondenseBest1));
        if (o.condense < 1) o.reasons.Add(d < CondenseBest0 ? "丹體還軟，邊緣不圓。" : "丹紋暗沉，帶著焦味。");
        if (held < .9) o.reasons.Add("丹面有幾處斑駁。");
        o.score = (int)Math.Round(25 * o.ratio + 25 * o.prep + 35 * o.fire + 15 * o.condense);
        for (int i = Grades.Length - 1; i >= 0; i--) if (o.score >= Grades[i].min) { o.success = true; o.label = Grades[i].label; break; }
        if (!o.success) o.reasons.Insert(0, "藥氣散開，沒有凝成丹。");
        return o;
    }
}
