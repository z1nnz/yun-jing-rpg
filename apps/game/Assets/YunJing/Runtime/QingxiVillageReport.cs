using System.Linq;
using UnityEngine;

namespace YunJing
{
    // The water-council corner on the plaza (Eli-0731's PR #47 corner): after going upstream the newcomer tells
    // the village what they saw (packages/content/waterline.json reports). A report changes nothing and grants
    // nothing; changing your mind is fine. Each report gets an answer from a different villager, in their own words:
    // only what they see and care about, never the cause or what comes next.
    public sealed class QingxiVillageReport : MonoBehaviour
    {
        public Transform point;
        const float Reach = 3.2f;
        const string Saved = "yj.waterReport";

        public static QingxiVillageReport Current { get; private set; }

        // Answered by villagers who already live in the village (the innkeeper, the smith, the herbalist), each about
        // what they care for: water for the inn, stone and tools, the slope where the herbs and the young beasts are.
        public static readonly (string id, string label, string before, string after)[] Reports =
        {
            ("tell_shortage", "告訴大家水少了的事",
                "客棧老闆停下腳步：「難怪這幾天井水都帶泥。我先跟客人說一聲，茶水省著點泡。」",
                "客棧老闆提著水桶經過：「水回來了，今天的茶總算泡得清了。」"),
            ("inspect_crack", "請鐵匠去看看裂開的舊槽",
                "鐵匠擦了擦手：「裂在側面？那是老毛病了。明天我帶鑿子上去看看。」",
                "鐵匠摸著新補的石鞍：「補得不錯。這塊石頭，可以撐很多年。」"),
            ("protect_nursery", "請大家別去吵溪邊的小獸",
                "藥農點點頭：「那片坡上的小獸？牠們常去吃落下的果子。我會跟孩子們說，別去追。」",
                "藥農小聲說：「牠們又回來喝水了，蹄印一路到溪邊。」"),
        };

        void OnEnable() { Current = this; }
        void OnDisable() { if (Current == this) Current = null; }

        static float Flat(Vector3 a, Vector3 b) => Vector2.Distance(new Vector2(a.x, a.z), new Vector2(b.x, b.z));
        public bool Near(Vector3 position) => point != null && Flat(position, point.position) <= Reach;
        public string Prompt(Vector3 position) => Near(position) ? "F 在議水桌旁說說上游看到的事" : null;

        public static string Reported
        {
            get
            {
                if (QingxiServerLink.Online && !string.IsNullOrEmpty(QingxiServerLink.Current.api.State.player.waterReport))
                    return QingxiServerLink.Current.api.State.player.waterReport;
                try { var s = PlayerPrefs.GetString(Saved, ""); return s.Length > 0 ? s : null; } catch { return null; }
            }
        }

        /// <summary>Before the newcomer has been upstream there is nothing to tell.</summary>
        public static string NotYet() => QingxiUpstreamClues.Seen().Count == 0 ? "桌邊的人看了你一眼：「你上游去過了嗎？」" : null;

        public string Tell(string id)
        {
            var report = Reports.FirstOrDefault(r => r.id == id);
            if (report.id == null) return null;
            var wait = NotYet(); if (wait != null) return wait;
            try { PlayerPrefs.SetString(Saved, id); PlayerPrefs.Save(); } catch { }
            QingxiServerLink.Current?.Submit(new GameAction { kind = "village-report", report = id });
            return QingxiWaterworksSite.Chosen != null ? report.after : report.before;
        }
    }
}
