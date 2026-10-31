using System;
using System.Collections.Generic;

namespace YunJing.Tea
{
    [Serializable] public class TeaEvent { public int t; public string k; public int v; }

    // Values from packages/content/tea-brewing-v1.json; tests/tea.test.ts fails if they drift apart.
    public static class TeaContent
    {
        public const double step = 0.1, ambient = 20, boil = 100, cooling = 0.012, steepCooling = 0.02;
        public const double base_ = 1.0, perDegree = 0.015, minFactor = 0.2, coldBelow = 60, coldRate = 0.25, scorchPerDegree = 0.8;
        public const int maxLogSeconds = 240, minScoops = 1, maxScoops = 5, restBonusMinutes = 30;
        public static readonly double[] fireHeat = { 0, 1.1, 2.2, 4.0 };
        public static readonly string[] fireLabels = { "熄火", "小火", "中火", "大火" };
        public static readonly (string id, string label, double from, string hint)[] steam =
        {
            ("still", "無聲無煙", 0, "水還涼，壺口沒有動靜"),
            ("whisper", "壺口微煙", 55, "壺底冒出細如蝦眼的小泡"),
            ("fisheye", "一沸・魚目", 72, "泡如魚眼，壺口一縷細白煙"),
            ("pearls", "二沸・連珠", 85, "邊緣湧泉連珠，白煙成束"),
            ("roaring", "三沸・騰波", 96, "水面翻滾，壺蓋輕跳，煙勢大"),
        };
        public static readonly TeaKind[] teas =
        {
            new TeaKind("qingxi-wild-tea", "青溪野茶", 85, 96, 3, 22, 36, "野茶耐泡，水要二沸，三匙恰好",
                "湯色淺黃，入口只有水味", "湯色金黃，山野清香回甘", "湯色發暗，苦澀壓住了香氣"),
            new TeaKind("plum-blossom-tea", "梅花茶", 72, 86, 2, 16, 28, "梅花嬌嫩，魚目時就該投茶，兩匙即可",
                "梅香若有似無，湯淡如水", "梅香清幽，湯色微粉", "花瓣燙熟，香氣轉澀"),
        };
        public static readonly (string id, string label, double rest)[] results = { ("weak", "淡", 1.05), ("good", "好", 1.25), ("bitter", "苦", 1.0) };
        public const string adviceEarly = "出湯太早，多等幾息再倒", adviceCold = "水溫不夠，茶葉沒有舒展，看到魚目再投茶", adviceLight = "茶葉少了，下次多一匙";
        public const string adviceLate = "出湯太晚，茶葉悶久就苦", adviceHot = "水太滾，嫩葉燙傷，火關小或早點投茶", adviceHeavy = "茶葉太多，下次少一匙";

        public static int SteamStage(double temperature)
        {
            int stage = 0;
            for (int i = 0; i < steam.Length; i++) if (temperature >= steam[i].from) stage = i;
            return stage;
        }
    }

    public sealed class TeaKind
    {
        public readonly string id, label, hint, weak, good, bitter; public readonly double low, high, weakBelow, bitterAbove; public readonly int idealScoops;
        public TeaKind(string id, string label, double low, double high, int idealScoops, double weakBelow, double bitterAbove, string hint, string weak, string good, string bitter)
        { this.id = id; this.label = label; this.low = low; this.high = high; this.idealScoops = idealScoops; this.weakBelow = weakBelow; this.bitterAbove = bitterAbove; this.hint = hint; this.weak = weak; this.good = good; this.bitter = bitter; }
    }

    public sealed class TeaJudgement { public string result, label, describe; public int score; public double strength, brewTemp, steepSeconds, restMultiplier; public List<string> reasons = new List<string>(); }

    // Presentation port of services/api/src/tea.ts simulate()/judge(): the same tick order and arithmetic,
    // so what the player sees at the stove matches the server replay of the same event log.
    public sealed class TeaPot
    {
        readonly TeaKind tea; readonly int scoops; readonly double mid, dose;
        public double T = TeaContent.ambient, Peak = TeaContent.ambient, Strength, Scorch; public double? BrewTemp;
        public int Tick, Fire, LeavesTick; public bool Poured;
        public readonly List<TeaEvent> Log = new List<TeaEvent>();

        public TeaPot(TeaKind tea, int scoops) { this.tea = tea; this.scoops = scoops; mid = (tea.low + tea.high) / 2; dose = (double)scoops / tea.idealScoops; }
        public TeaKind Kind => tea;
        public int Scoops => scoops;
        public double SteepSeconds => BrewTemp == null ? 0 : (Tick - LeavesTick) / 10.0;
        public bool CanContinue => !Poured && Tick < TeaContent.maxLogSeconds * 10 - 1;

        // Events land on the current tick before it is integrated, exactly like the server's while-loop.
        public void SetFire(int level) { if (Poured || level == Fire) return; Fire = level; Log.Add(new TeaEvent { t = Tick, k = "fire", v = level }); }
        public void AddLeaves()
        {
            if (Poured || BrewTemp != null) return;
            if (Fire != 0) SetFire(0);   // the kettle comes off the stove when the water goes onto the leaves
            BrewTemp = T; LeavesTick = Tick; Log.Add(new TeaEvent { t = Tick, k = "leaves" });
            Scorch = Math.Max(0, T - tea.high) * TeaContent.scorchPerDegree; Strength += Scorch;
        }
        public TeaJudgement Pour() { if (BrewTemp == null || Poured) return null; Poured = true; Log.Add(new TeaEvent { t = Tick, k = "pour" }); return Judge(); }

        public void Step()
        {
            if (!CanContinue) return;
            if (BrewTemp == null)
            {
                T = Math.Min(TeaContent.boil, T + (TeaContent.fireHeat[Fire] - TeaContent.cooling * (T - TeaContent.ambient)) * TeaContent.step);
                if (T > Peak) Peak = T;
            }
            else
            {
                T = T - TeaContent.steepCooling * (T - TeaContent.ambient) * TeaContent.step;
                double rate = dose * Math.Max(TeaContent.minFactor, TeaContent.base_ + TeaContent.perDegree * (T - mid));
                if (BrewTemp.Value < TeaContent.coldBelow) rate *= TeaContent.coldRate;
                Strength += rate * TeaContent.step;
            }
            Tick++;
        }

        public TeaJudgement Judge()
        {
            double brew = BrewTemp ?? TeaContent.ambient, s = Math.Round(Strength * 10000) / 10000;
            var j = new TeaJudgement { strength = s, brewTemp = Math.Round(brew * 10) / 10, steepSeconds = SteepSeconds };
            int r = s < tea.weakBelow ? 0 : s > tea.bitterAbove ? 2 : 1;
            if (r == 0)
            {
                if (brew < TeaContent.coldBelow) j.reasons.Add(TeaContent.adviceCold);
                if (scoops < tea.idealScoops) j.reasons.Add(TeaContent.adviceLight);
                if (j.reasons.Count == 0) j.reasons.Add(TeaContent.adviceEarly);
            }
            else if (r == 2)
            {
                if (brew > tea.high) j.reasons.Add(TeaContent.adviceHot);
                if (scoops > tea.idealScoops) j.reasons.Add(TeaContent.adviceHeavy);
                if (j.reasons.Count == 0) j.reasons.Add(TeaContent.adviceLate);
            }
            double centre = (tea.weakBelow + tea.bitterAbove) / 2, half = (tea.bitterAbove - tea.weakBelow) / 2, off = Math.Abs(s - centre) / half;
            j.score = r == 1 ? (int)Math.Round(100 - 30 * off, MidpointRounding.AwayFromZero) : Math.Max(10, (int)Math.Round(60 - 25 * (off - 1), MidpointRounding.AwayFromZero));
            j.result = TeaContent.results[r].id; j.label = TeaContent.results[r].label; j.restMultiplier = TeaContent.results[r].rest;
            j.describe = r == 0 ? tea.weak : r == 1 ? tea.good : tea.bitter;
            return j;
        }
    }
}
