using System.Collections.Generic;
using QingxiWorld;
using UnityEngine;

namespace YunJing
{
    // Day 1's places (QingxiNoviceDays): the tea pavilion on the road in A2, where the old man pours a cup and hands
    // over a plum seedling, and the spot in front of the house in the newcomer's own plot where it is planted. Each
    // streamed scene carries its own spots; QingxiAbcStations asks all of them. What the old man says is kept short:
    // he offers tea, gives the seedling with the one thing he asks, and points the way. He explains nothing.
    public sealed class QingxiDayOneSpots : MonoBehaviour
    {
        public Transform teaPoint, plumPoint;
        public GameObject plumTree;   // the planted seedling, shown once day 1's planting is done
        const float Reach = 2.6f;

        static readonly List<QingxiDayOneSpots> all = new List<QingxiDayOneSpots>();
        public static IReadOnlyList<QingxiDayOneSpots> All => all;

        static readonly string[] TeaLines =
        {
            "茶亭老人倒了一杯茶，推到你面前：「客人，喝杯茶再走吧，路還長。」",
            "你喝完茶，他從簷下拿出一株梅苗，用草繩綁好遞給你：「種著吧。哪天你要走了，折一枝寄回來。」",
            "他指了指官道盡頭：「村裡空屋多。借住處的老闆會給你一間。」",
        };
        int teaLine;
        string spoken; float spokenUntil;

        void OnEnable() { all.Add(this); Refresh(); QingxiNoviceDays.Changed += Refresh; }
        void OnDisable() { all.Remove(this); QingxiNoviceDays.Changed -= Refresh; }
        void Refresh() { if (plumTree != null) plumTree.SetActive(QingxiNoviceDays.Has("plum")); }

        static float Flat(Vector3 a, Vector3 b) => Vector2.Distance(new Vector2(a.x, a.z), new Vector2(b.x, b.z));

        public string Prompt(Vector3 p)
        {
            if (teaPoint != null && Flat(p, teaPoint.position) <= Reach)
                return QingxiNoviceDays.Has("tea") ? "F 跟茶亭老人說說話" : "F 在茶亭坐下";
            if (plumPoint != null && Flat(p, plumPoint.position) <= Reach && QingxiNoviceDays.Has("tea") && !QingxiNoviceDays.Has("plum"))
                return "F 把梅苗種在這裡";
            return null;
        }

        public bool TryInteract(Vector3 p, out string message)
        {
            message = null;
            if (teaPoint != null && Flat(p, teaPoint.position) <= Reach)
            {
                if (QingxiNoviceDays.Has("tea") && teaLine == 0) teaLine = TeaLines.Length - 1;   // a later visit
                message = TeaLines[Mathf.Min(teaLine, TeaLines.Length - 1)];
                if (teaLine == 1) QingxiNoviceDays.Mark("tea");
                teaLine = Mathf.Min(teaLine + 1, TeaLines.Length - 1);
                Say(message);
                return true;
            }
            if (plumPoint != null && Flat(p, plumPoint.position) <= Reach && QingxiNoviceDays.Has("tea") && !QingxiNoviceDays.Has("plum"))
            {
                QingxiNoviceDays.Mark("plum");
                message = "你在屋前挖了個坑，把梅苗放進去，用手把土壓實。";
                Say(message);
                return true;
            }
            return false;
        }

        void Say(string line) { spoken = line; spokenUntil = Time.unscaledTime + 7f; }

        // The old man's words in a box at the bottom of the screen, long enough to read.
        void OnGUI()
        {
            if (spoken == null || Time.unscaledTime > spokenUntil) return;
            QingxiFonts.ApplyImgui();
            float scale = Mathf.Clamp(Screen.height / 720f, .7f, 2f);
            var previous = GUI.matrix;
            GUI.matrix = Matrix4x4.Scale(Vector3.one * scale);
            float w = Screen.width / scale, h = Screen.height / scale;
            var style = new GUIStyle(GUI.skin.box) { wordWrap = true, fontSize = 18, alignment = TextAnchor.MiddleLeft, padding = new RectOffset(18, 18, 12, 12) };
            GUI.Box(new Rect(w * .5f - 330, h - 150, 660, 96), spoken, style);
            GUI.matrix = previous;
        }
    }

    // A newcomer's first arrival: on the road south of the tea pavilion instead of at the village gate. The road is in
    // the streamed A2 block, so the player is held still until its ground is under them.
    public sealed class QingxiNoviceArrival : MonoBehaviour
    {
        public Vector3 arrival = new Vector3(2, 0, -124);
        public float yaw = -20;

        System.Collections.IEnumerator Start()
        {
            string args = string.Join(" ", System.Environment.GetCommandLineArgs()) + " " + Application.absoluteURL;
            if (args.Contains("smoke") || args.Contains("shots") || QingxiNoviceDays.Has("arrived")) yield break;
            var walker = GetComponent<QingxiFirstPerson>();
            var body = GetComponent<CharacterController>();
            if (walker == null || body == null) yield break;
            body.enabled = false;
            walker.SetMenuOpen(true);
            transform.position = arrival + Vector3.up * 2f;
            transform.rotation = Quaternion.Euler(0, yaw, 0);
            float give = Time.realtimeSinceStartup + 20f;
            while (Time.realtimeSinceStartup < give && !Physics.Raycast(arrival + Vector3.up * 200, Vector3.down, out _, 400)) yield return null;
            if (Physics.Raycast(arrival + Vector3.up * 200, Vector3.down, out var hit, 400)) transform.position = hit.point + Vector3.up * .05f;
            body.enabled = true;
            walker.SetMenuOpen(false);
            QingxiNoviceDays.Mark("arrived");
        }
    }
}
