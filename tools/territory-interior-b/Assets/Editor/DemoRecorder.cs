using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

/// Batch-mode entry points:
///   -executeMethod DemoRecorder.Preview   builds the scene and writes a handful of stills (Recording/preview_*.png)
///   -executeMethod DemoRecorder.Record    builds the scene and writes every frame at 30 fps (Recording/frames/)
///   -executeMethod DemoRecorder.RecordShort   the same for the under-a-minute cut (door, lamp, shelf, furnace)
/// Time is stepped by DemoDirector, so the result does not depend on editor frame rate.
public static class DemoRecorder
{
    const int W = 1280, H = 720, Fps = 30;

    /// Still times in seconds; TI18_STILLS="1,24,27" overrides them.
    public static void Preview()
    {
        var env = System.Environment.GetEnvironmentVariable("TI18_STILLS");
        var times = string.IsNullOrEmpty(env) ? new[] { 1f, 24f, 27f, 30f, 33f, 36f, 39f }
            : env.Split(',').Select(s => float.Parse(s, System.Globalization.CultureInfo.InvariantCulture)).ToArray();
        Run(times, false);
    }
    public static void Record() => Run(null, true);
    /// The under-a-minute cut (brief 02-B §10); TI18_STILLS set → stills only.
    public static void RecordShort()
    {
        var env = System.Environment.GetEnvironmentVariable("TI18_STILLS");
        if (string.IsNullOrEmpty(env)) Run(null, true, true);
        else Run(env.Split(',').Select(s => float.Parse(s, System.Globalization.CultureInfo.InvariantCulture)).ToArray(), false, true);
    }

    static void Run(float[] stills, bool all, bool shortCut = false)
    {
        var root = Path.GetFullPath("Recording");
        Directory.CreateDirectory(root);
        var framesDir = Path.Combine(root, "frames");
        if (all) { if (Directory.Exists(framesDir)) Directory.Delete(framesDir, true); Directory.CreateDirectory(framesDir); }

        var dir = SceneBuilder.Build().GetComponent<DemoDirector>();
        File.WriteAllLines(Path.Combine(root, "build_report.txt"), SceneBuilder.Report);
        dir.ui.Build();
        dir.shortCut = shortCut;
        dir.BeginDemo();

        var cam = dir.rig.GetComponent<Camera>();
        var rt = new RenderTexture(W, H, 24, RenderTextureFormat.ARGB32) { antiAliasing = 8 };
        var tex = new Texture2D(W, H, TextureFormat.RGB24, false);
        cam.targetTexture = rt;
        int frame = 0, next = 0;
        float dt = 1f / Fps;
        while (!dir.Finished && frame < Fps * 120)
        {
            dir.Step(dt);
            frame++;
            bool shoot = all || (stills != null && next < stills.Length && dir.Time >= stills[next]);
            if (!shoot) continue;
            Canvas.ForceUpdateCanvases();
            cam.Render();
            RenderTexture.active = rt;
            tex.ReadPixels(new Rect(0, 0, W, H), 0, 0); tex.Apply();
            RenderTexture.active = null;
            string name = all ? Path.Combine(framesDir, $"f_{frame:00000}.png") : Path.Combine(root, $"preview_{next:00}_{dir.Time:00.0}s.png");
            File.WriteAllBytes(name, tex.EncodeToPNG());
            if (!all) next++;
        }
        File.AppendAllLines(Path.Combine(root, "build_report.txt"), new[] { $"frames {frame}, duration {dir.Time:0.00}s, finished {dir.Finished}" });
        cam.targetTexture = null;
        DemoDirector.Driving = false;
        Debug.Log($"DEMO_RECORD_DONE frames={frame} t={dir.Time:0.00}");
    }
}
