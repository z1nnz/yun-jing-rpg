using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;

namespace YunJing.Tea
{
    // Scripted player for the tea room build (-teaPlaytest). It presses the panel's own buttons (SelectTea, SetScoops,
    // Begin, SetFire, AddLeaves, Pour) at real time; it is not physical keyboard or mouse input. It reads the steam
    // stage like a player would and, for the "good" pot, pours when the liquor is in the middle of the window.
    // Every -teaFrameEvery seconds it saves a frame, so the run can be assembled into a recording.
    public sealed class TeaPlaytest : MonoBehaviour
    {
        [Serializable] class Step { public int index; public string name; public bool pass; public string note; public float seconds; public string shot; }
        [Serializable] class Report { public string started, resolution; public bool pass; public float frameEvery; public int frames; public List<Step> steps = new List<Step>(); public List<string> logs = new List<string>(); }

        TeaBrewingPanel panel; string outDir; readonly Report report = new Report(); float t0, nextFrame; int index, frame; bool capturing;

        static string Arg(string name)
        {
            var args = Environment.GetCommandLineArgs(); int i = Array.IndexOf(args, name);
            return i >= 0 && i + 1 < args.Length ? args[i + 1] : null;
        }

        void Start()
        {
            if (!Environment.GetCommandLineArgs().Contains("-teaPlaytest")) { enabled = false; return; }
            Application.runInBackground = true;
            panel = GetComponent<TeaBrewingPanel>();
            outDir = Arg("-teaOut") ?? Path.Combine(Application.persistentDataPath, "tea-playtest");
            Directory.CreateDirectory(Path.Combine(outDir, "frames"));
            report.frameEvery = float.TryParse(Arg("-teaFrameEvery"), out var every) ? every : .2f;
            report.started = DateTime.Now.ToString("s"); report.resolution = Screen.width + "x" + Screen.height;
            StartCoroutine(Run());
        }

        void LateUpdate() { if (capturing && Time.realtimeSinceStartup >= nextFrame) { nextFrame += report.frameEvery; StartCoroutine(Save(Path.Combine("frames", $"{frame++:0000}.png"))); } }

        IEnumerator Save(string file)
        {
            yield return new WaitForEndOfFrame();
            var tex = new Texture2D(Screen.width, Screen.height, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, Screen.width, Screen.height), 0, 0); tex.Apply();
            File.WriteAllBytes(Path.Combine(outDir, file), tex.EncodeToPNG()); Destroy(tex);
        }

        IEnumerator Shot(string name) { var file = $"{index:00}_{name}.png"; report.steps[report.steps.Count - 1].shot = file; yield return Save(file); }

        void Mark(string name, bool pass, string note = "")
        {
            report.steps.Add(new Step { index = ++index, name = name, pass = pass, note = note, seconds = Time.realtimeSinceStartup - t0 });
            Debug.Log($"TEA_PLAYTEST {(pass ? "PASS" : "FAIL")} {index:00} {name} {note}");
        }

        IEnumerator Until(Func<bool> condition, float timeout)
        {
            float end = Time.realtimeSinceStartup + timeout; while (!condition() && Time.realtimeSinceStartup < end) yield return null;
        }
        IEnumerator Wait(float seconds) { yield return new WaitForSeconds(seconds); }

        int Stage => panel.Pot == null ? 0 : TeaContent.SteamStage(panel.Pot.T);

        /// <summary>One pot: choose, boil to a steam stage, add leaves, pour by liquor target (fraction of the good window).</summary>
        IEnumerator Brew(string label, int tea, int scoops, int fire, string steamId, double pourAt, string expect)
        {
            int target = Array.FindIndex(TeaContent.steam, s => s.id == steamId);
            panel.Show(); yield return Wait(.8f);
            panel.SelectTea(tea); yield return Wait(.6f); panel.SetScoops(scoops); yield return Wait(.8f);
            Mark(label + "_choose", panel.Stage == TeaBrewingPanel.Phase.Choose, $"{TeaContent.teas[tea].label} {scoops} 匙"); yield return Shot(label + "_choose");
            bool begun = panel.Begin(); yield return Wait(.6f);
            panel.SetFire(fire);
            Mark(label + "_boil", begun && panel.Stage == TeaBrewingPanel.Phase.Boil, TeaContent.fireLabels[fire]);
            for (int s = 1; s <= target; s++)
            {
                yield return Until(() => Stage >= s, 120);
                if (s == target || s == 2) { Mark($"{label}_steam_{TeaContent.steam[s].id}", Stage >= s, TeaContent.steam[s].label); yield return Shot($"{label}_steam_{TeaContent.steam[s].id}"); }
            }
            yield return Wait(.4f);
            panel.AddLeaves(); var kind = panel.Pot.Kind;
            Mark(label + "_leaves", panel.Stage == TeaBrewingPanel.Phase.Steep, $"投茶水溫 {panel.Pot.BrewTemp:0.0}"); yield return Shot(label + "_leaves");
            double goal = kind.weakBelow + (kind.bitterAbove - kind.weakBelow) * pourAt;
            yield return Until(() => panel.Pot.Strength >= goal || !panel.Pot.CanContinue, 200);
            yield return Shot(label + "_liquor");
            panel.Pour(); yield return Wait(.3f);
            var j = panel.Last;
            Mark(label + "_result", j != null && j.result == expect, j == null ? "no result" : $"{j.label} {j.score} 分 浸 {j.steepSeconds:0.0}s 理由：{string.Join("／", j.reasons)}");
            report.logs.Add(string.Join(",", panel.Pot.Log.Select(e => $"{e.t}:{e.k}{(e.k == "fire" ? e.v.ToString() : "")}")));
            yield return Shot(label + "_result");
            yield return Wait(2.2f);
            panel.Close(); yield return Wait(.8f);
        }

        IEnumerator Run()
        {
            yield return Wait(1.5f);
            t0 = Time.realtimeSinceStartup; nextFrame = t0; capturing = true;
            Mark("start", panel != null && panel.stove != null, "茶爐與面板就緒");
            int wildBefore = panel.Leaves["qingxi-wild-tea"];
            // 1. Wild tea, medium fire to second boil, three scoops, poured in the middle of the window: good.
            yield return Brew("1_wild_good", 0, 3, 2, "pearls", .5, "good");
            // 2. Plum blossom, large fire to a rolling boil: scorched and bitter.
            yield return Brew("2_plum_scorched", 1, 2, 3, "roaring", 1.2, "bitter");
            // 3. Plum blossom at fish-eye, poured early: weak.
            yield return Brew("3_plum_early", 1, 2, 2, "fisheye", -.6, "weak");
            // Abandon before the leaves go in: the leaves come back.
            panel.Show(); panel.SelectTea(0); panel.SetScoops(1); panel.Begin(); yield return Wait(.5f);
            int during = panel.Leaves["qingxi-wild-tea"]; panel.Close(); yield return Wait(.5f);
            Mark("abandon_returns_leaves", panel.Leaves["qingxi-wild-tea"] == during + 1 && during + 1 == wildBefore - 3, $"野茶 {during} → {panel.Leaves["qingxi-wild-tea"]}");
            capturing = false; yield return Wait(.5f);
            report.frames = frame; report.pass = report.steps.All(s => s.pass);
            File.WriteAllText(Path.Combine(outDir, "tea-playtest.json"), JsonUtility.ToJson(report, true));
            Debug.Log("TEA_PLAYTEST_DONE pass=" + report.pass + " frames=" + frame);
            Application.Quit(report.pass ? 0 : 1);
        }
    }
}
