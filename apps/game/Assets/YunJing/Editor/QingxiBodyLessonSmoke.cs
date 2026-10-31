using System;
using System.IO;
using System.Linq;
using UnityEngine;
using Rules = YunJing.QingxiBodyLessonRules;

namespace YunJing.Editor
{
    // Replays the runs recorded from tools/body-training-lesson/lesson.mjs (parity.mjs) on the C# port and requires the same
    // schedules, judgements and outcomes.
    //   Unity -batchmode -nographics -quit -projectPath apps/game -executeMethod YunJing.Editor.QingxiBodyLessonSmoke.Run
    public static class QingxiBodyLessonSmoke
    {
        [Serializable] class Schedule { public uint seed; public double[] block, dodge; }
        [Serializable] class InputData { public int frame; public string kind, side; }
        [Serializable] class RunData { public string name; public uint seed; public double step; public int frames; public InputData[] inputs; public string[] log; public int retries; public string phase; public int[] attempts; public double end; }
        [Serializable] class Parity { public Schedule[] schedules; public RunData[] runs; }

        public static void Run() => Debug.Log(Verify());

        public static string Verify()
        {
            var text = Resources.Load<TextAsset>("QingxiBodyLesson/body-training-lesson-1");
            if (text == null) throw new InvalidDataException("Resources/QingxiBodyLesson/body-training-lesson-1 missing");
            var content = JsonUtility.FromJson<Rules.Content>(text.text);
            var path = Path.Combine(Application.dataPath, "YunJing/Data/QingxiBodyLessonParity.json");
            var data = JsonUtility.FromJson<Parity>(File.ReadAllText(path));
            if (data?.runs == null || data.schedules == null) throw new InvalidDataException("Body lesson parity data missing");

            var blockCfg = content.stages.First(s => s.id == "block");
            var dodgeCfg = content.stages.First(s => s.id == "dodge");
            foreach (var s in data.schedules)
            {
                Same("block", Rules.Schedule(blockCfg, s.seed), s.block, s.seed);
                Same("dodge", Rules.Schedule(dodgeCfg, s.seed), s.dodge, s.seed);
            }

            foreach (var r in data.runs)
            {
                var lesson = new Rules.Lesson(content, r.seed);
                int next = 0, logged = 0;
                double t = 0;
                int frame = 0;
                while (frame < r.frames)
                {
                    frame++;
                    t += r.step;
                    lesson.Update(t);
                    for (; next < r.inputs.Length && r.inputs[next].frame == frame; next++)
                    {
                        var i = r.inputs[next];
                        if (i.kind == "hold") lesson.SetHeld(i.side == "on");
                        else if (i.kind == "retry") lesson.Retry(t);
                        else
                        {
                            string got = i.kind == "press" ? lesson.Press(t) : lesson.StepTo(i.side, t);
                            string want = r.log[logged++];
                            string have = $"{(i.kind == "press" ? "block" : "dodge")}:{got}";
                            if (have != want) throw new InvalidOperationException($"run {r.name} frame {frame}: C# {have}, JS {want}");
                        }
                    }
                }
                if (lesson.phase != r.phase || !lesson.attempts.SequenceEqual(r.attempts))
                    throw new InvalidOperationException($"run {r.name}: C# {lesson.phase}/{string.Join("-", lesson.attempts)}, JS {r.phase}/{string.Join("-", r.attempts)}");
            }
            var summary = $"QINGXI_BODY_LESSON_PARITY PASS {data.schedules.Length} schedules, runs {string.Join(" ", data.runs.Select(r => $"{r.name}:{r.phase}/{string.Join("-", r.attempts)}"))}";
            return summary;
        }

        static void Same(string what, double[] a, double[] b, uint seed)
        {
            if (a.Length != b.Length) throw new InvalidOperationException($"{what} seed {seed}: {a.Length} vs {b.Length}");
            for (int i = 0; i < a.Length; i++)
                if (Math.Abs(a[i] - b[i]) > 1e-5) throw new InvalidOperationException($"{what} seed {seed} #{i}: C# {a[i]}, JS {b[i]}");
        }
    }
}
