using System.Collections.Generic;
using UnityEngine;

namespace YunJing
{
    // D3 upstream valley (Johnnnny0823's PR #45): the places where the newcomer reads why the creek stopped.
    // Lives in the streamed D3 block scene and registers itself, so the village's F-key stations can ask it while
    // it is loaded. Each clue is kept on this device and sent as `observe-upstream` (the server keeps them per player).
    public sealed class QingxiUpstreamClues : MonoBehaviour
    {
        [System.Serializable] public class Clue { public string id; public Transform at; }

        public Clue[] points = new Clue[0];
        public GameObject siltBlocked, siltCleared;   // A04 silt bar, before and after the newcomer chose to clear it
        const float Reach = 2.6f;
        const string Saved = "yj.upstream";

        public static QingxiUpstreamClues Current { get; private set; }

        // What the newcomer sees, nothing more: no causes, no future.
        static readonly Dictionary<string, (string prompt, string seen)> Words = new Dictionary<string, (string, string)>
        {
            ["cracked_sluice"] = ("F 蹲下看看這道舊石槽", "石槽側面裂了一道縫，水從縫裡滲進土裡，流到下面就沒了。"),
            ["silt_buildup"] = ("F 看看溪水變窄的地方", "泥沙在窄口堆成一道矮坎，水被擋在後面，只剩細細一股漫過去。"),
            ["nursery_tracks"] = ("F 看看濕泥上的痕跡", "濕泥上有一串小小的蹄印，往淺灘那頭去了。附近有小獸在這裡喝水。"),
        };

        void OnEnable()
        {
            Current = this;
            bool cleared = QingxiWaterworksSite.Chosen == "clear_silt";
            if (siltBlocked != null) siltBlocked.SetActive(!cleared);
            if (siltCleared != null) siltCleared.SetActive(cleared);
        }
        void OnDisable() { if (Current == this) Current = null; }

        static float Flat(Vector3 a, Vector3 b) => Vector2.Distance(new Vector2(a.x, a.z), new Vector2(b.x, b.z));

        public static HashSet<string> Seen()
        {
            var seen = new HashSet<string>();
            try { foreach (var id in PlayerPrefs.GetString(Saved, "").Split(',')) if (id.Length > 0) seen.Add(id); } catch { }
            if (QingxiServerLink.Online && QingxiServerLink.Current.api.State.player.upstream != null)
                foreach (var id in QingxiServerLink.Current.api.State.player.upstream) seen.Add(id);
            return seen;
        }

        Clue Near(Vector3 position)
        {
            foreach (var c in points) if (c.at != null && Flat(position, c.at.position) <= Reach) return c;
            return null;
        }

        public string Prompt(Vector3 position)
        {
            var c = Near(position);
            if (c == null || !Words.TryGetValue(c.id, out var w)) return null;
            return Seen().Contains(c.id) ? w.prompt.Replace("F ", "F 再") : w.prompt;
        }

        public bool TryInteract(Vector3 position, out string message)
        {
            message = null;
            var c = Near(position);
            if (c == null || !Words.TryGetValue(c.id, out var w)) return false;
            var seen = Seen();
            bool first = seen.Add(c.id);
            message = w.seen;
            if (!first) return true;
            try { PlayerPrefs.SetString(Saved, string.Join(",", seen)); PlayerPrefs.Save(); } catch { }
            QingxiServerLink.Current?.Submit(new GameAction { kind = "observe-upstream", observation = c.id });
            if (seen.Count == 2) message += "\n看到的事情夠多了，可以回村裡跟大家說說。";
            return true;
        }
    }
}
