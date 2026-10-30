using System.Linq;
using UnityEngine;

namespace YunJing
{
    // The old channel south of the creek bend (joshsu54's PR #52 pieces): talking it over beside the gate opens the
    // three ways to bring the water back (packages/content/waterline.json). The choice is sent as waterworks-commit;
    // the server checks the upstream clues and the stone and keeps the outcome. Offline, the choice is kept on this
    // device. Once chosen, the new troughs, the water and the completion stele show.
    public sealed class QingxiWaterworksSite : MonoBehaviour
    {
        public Transform point;
        public GameObject repaired;
        const float Reach = 2.6f;
        const string Saved = "yj.waterworks";
        const int MinClues = 2;   // waterline.json minObservations

        public static QingxiWaterworksSite Current { get; private set; }
        public static readonly (string id, string label, string line)[] Choices =
        {
            ("clear_silt", "先清淤", "先把上游的泥沙清掉，今天田裡還沒有水，往後水會比較足。"),
            ("restore_channel", "修回舊渠", "補好裂開的舊槽，水今天就能流到田裡，只是會經過育幼區旁邊。"),
            ("protect_nursery", "保護育幼區", "繞開育幼區另接一段新渠，要多搬很多石頭，水也會少一點。"),
        };

        void OnEnable() { Current = this; }
        void OnDisable() { if (Current == this) Current = null; }
        void Start() { Show(); }

        public static string Chosen
        {
            get
            {
                if (QingxiServerLink.Online && QingxiServerLink.Current.api.State.player.milestones != null)
                    foreach (var m in QingxiServerLink.Current.api.State.player.milestones)
                        if (m.StartsWith("waterworks:")) return m.Substring("waterworks:".Length);
                try { var s = PlayerPrefs.GetString(Saved, ""); return s.Length > 0 ? s : null; } catch { return null; }
            }
        }

        void Show() { if (repaired != null) repaired.SetActive(Chosen != null); }

        static float Flat(Vector3 a, Vector3 b) => Vector2.Distance(new Vector2(a.x, a.z), new Vector2(b.x, b.z));
        public bool Near(Vector3 position) => point != null && Flat(position, point.position) <= Reach;

        public string Prompt(Vector3 position) =>
            !Near(position) ? null : Chosen != null ? "F 看看修好的水路" : "F 和大家商量怎麼修這條舊水路";

        /// <summary>Why the choice can't be made yet, or null when it can.</summary>
        public static string NotYet()
        {
            if (Chosen != null) return null;
            int seen = QingxiUpstreamClues.Seen().Count;
            return seen < MinClues ? "工匠搖搖頭：「上游到底怎麼了，你先去看看再說。」" : null;
        }

        public string Choose(string id)
        {
            var choice = Choices.FirstOrDefault(c => c.id == id);
            if (choice.id == null) return null;
            if (Chosen != null) return "這條水路已經修好了。";
            var wait = NotYet(); if (wait != null) return wait;
            try { PlayerPrefs.SetString(Saved, id); PlayerPrefs.Save(); } catch { }
            QingxiServerLink.Current?.Submit(new GameAction { kind = "waterworks-commit", choice = id });
            Show();
            return "大家一起動手。" + (id == "clear_silt" ? "上游的泥沙清開了。" : "舊槽補好了，水順著新槽往田裡去。");
        }
    }
}
