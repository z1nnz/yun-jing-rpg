using System;
using System.Collections.Generic;
using System.Linq;

namespace YunJing
{
    // C# port of tools/body-training-lesson/lesson.mjs: 沈岳的第一堂練體課 (stance, block, dodge). Pure and time-driven
    // (seconds), numbers from packages/content/body-training-lesson-1.json (copied to Resources by parity.mjs);
    // QingxiBodyLessonSmoke checks parity against recorded runs. A failed stage only restarts that stage, and nothing here
    // grants anything: the server (core team) decides what a passed lesson gives.
    public static class QingxiBodyLessonRules
    {
        [Serializable]
        public sealed class StageConfig
        {
            public string id, kind, label;
            public double leadIn, holdSeconds, zone, limit, rise, fall, swayA, swayB, swayRateA, swayRateB;
            public int count, required;
            public double firstAt, jitter, windup, perfectWindow, goodWindow, stiffSeconds, dodgeBefore, dodgeAfter, recoverSeconds, stumbleSeconds;
            public double[] gaps;
        }

        [Serializable] public sealed class DemoTexts { public string stance, block, dodge; }
        [Serializable] public sealed class TipTexts { public string stance, stanceDrift, stanceReset, block, blockEarly, dodge, dodgeEarly; }
        [Serializable] public sealed class JudgeTexts { public string perfect, good, hit, dodged, swept; }
        [Serializable] public sealed class ButtonTexts { public string hold, block, left, right, retry, leave; }
        [Serializable]
        public sealed class Texts
        {
            public string prompt, stagePassed, stageFailed, passed;
            public DemoTexts demo; public TipTexts tip; public JudgeTexts judge; public ButtonTexts button;
        }
        [Serializable] public sealed class ResultInfo { public string discipline, label; }

        [Serializable]
        public sealed class Content
        {
            public string id, title, teacher;
            public int day;
            public double demoSeconds;
            public ResultInfo result;
            public StageConfig[] stages;
            public Texts texts;
        }

        const double Step = 1.0 / 120;

        static void Clock(double now, double last)
        {
            if (double.IsNaN(now) || double.IsInfinity(now) || now < last) throw new ArgumentException("time must be finite and monotonic");
        }

        // Same generator as the training drills, fixed per seed so a run can be replayed.
        sealed class Rng
        {
            uint s;
            public Rng(uint seed) { s = seed; }
            public double Next() { s = unchecked(1664525u * s + 1013904223u); return s / 4294967296.0; }
        }

        public static double[] Schedule(StageConfig c, uint seed)
        {
            var rnd = new Rng(seed);
            var times = new double[c.count];
            double at = c.firstAt;
            for (int i = 0; i < c.count; i++)
            {
                double jitter = (rnd.Next() * 2 - 1) * c.jitter;
                times[i] = Math.Round((at + jitter) * 1e6, MidpointRounding.AwayFromZero) / 1e6;
                at += i < c.gaps.Length ? c.gaps[i] : c.gaps[c.gaps.Length - 1];
            }
            return times;
        }

        public abstract class Stage
        {
            public bool done;
            public abstract bool Passed { get; }
            public abstract void Update(double now);
        }

        // One press-to-rise bar that has to stay in the middle. Leaving the limit starts the count over.
        public sealed class StanceStage : Stage
        {
            readonly StageConfig c;
            readonly double phaseA, phaseB;
            double t, last, pending;
            public bool held;
            public double value, count;
            public int resets;
            bool passed;

            public StanceStage(StageConfig config, uint seed = 7)
            {
                c = config;
                var rnd = new Rng(seed);
                phaseA = rnd.Next() * Math.PI * 2;
                phaseB = rnd.Next() * Math.PI * 2;
                t = -c.leadIn;
            }

            public override bool Passed => passed;
            public double Lead => t;
            public bool InZone => Math.Abs(value) <= c.zone;
            public void SetHeld(bool h) { if (!done) held = h; }

            public override void Update(double now)
            {
                Clock(now, last);
                pending += now - last;
                last = now;
                // Fixed steps: a phone at 30 fps and a desktop at 144 fps get the same bar.
                while (!done && pending >= Step - 1e-9)
                {
                    pending -= Step;
                    t += Step;
                    if (t < 0) continue;
                    double sway = c.swayA * Math.Sin(c.swayRateA * t + phaseA) + c.swayB * Math.Sin(c.swayRateB * t + phaseB);
                    value += (sway + (held ? c.rise : -c.fall)) * Step;
                    if (Math.Abs(value) > c.limit)
                    {
                        value = 0; count = 0; resets++;
                    }
                    else if (InZone)
                    {
                        count += Step;
                        if (count >= c.holdSeconds) { count = c.holdSeconds; done = true; passed = true; }
                    }
                }
            }
        }

        // Punches on a timing window. A press with nothing arriving stiffens the stance, and pressing again extends it,
        // so mashing never lands.
        public sealed class BlockStage : Stage
        {
            readonly StageConfig c;
            public readonly double[] strikes;
            public readonly List<string> results = new List<string>();
            public int index;
            public double stiffUntil = double.NegativeInfinity, last;
            public string lastEvent;

            public BlockStage(StageConfig config, uint seed = 7) { c = config; strikes = Schedule(c, seed); }

            public double? Next => done ? (double?)null : strikes[index];
            public int Blocked => results.Count(r => r == "perfect" || r == "good");
            public override bool Passed => done && Blocked >= c.required;

            void Record(string result)
            {
                results.Add(result); lastEvent = result; index++;
                if (index >= strikes.Length) done = true;
            }

            public override void Update(double now)
            {
                Clock(now, last);
                last = now;
                while (!done && now > strikes[index] + c.goodWindow) Record("hit");
            }

            public string Press(double now)
            {
                Update(now);
                if (done) return null;
                double offset = now - strikes[index];
                if (now < stiffUntil || Math.Abs(offset) > c.goodWindow)
                {
                    stiffUntil = now + c.stiffSeconds; lastEvent = "early";
                    return "early";
                }
                string result = Math.Abs(offset) <= c.perfectWindow ? "perfect" : "good";
                Record(result);
                return result;
            }
        }

        // Sweeps resolved at the moment they arrive: dodged if a sideways step started inside the window before it.
        public sealed class DodgeStage : Stage
        {
            readonly StageConfig c;
            public readonly double[] sweeps;
            public readonly List<string> results = new List<string>();
            public int index;
            public double stepAt = double.NegativeInfinity, readyAt = double.NegativeInfinity, last;
            public string stepSide, lastEvent;

            public DodgeStage(StageConfig config, uint seed = 7) { c = config; sweeps = Schedule(c, seed); }

            public double? Next => done ? (double?)null : sweeps[index];
            public int Dodged => results.Count(r => r == "dodged");
            public override bool Passed => done && Dodged >= c.required;

            bool Covers(double at) => stepAt >= at - c.dodgeBefore && stepAt <= at + c.dodgeAfter;

            void Record(string result)
            {
                results.Add(result); lastEvent = result; index++;
                if (index >= sweeps.Length) done = true;
            }

            public override void Update(double now)
            {
                Clock(now, last);
                last = now;
                while (!done && now > sweeps[index] + c.dodgeAfter) Record(Covers(sweeps[index]) ? "dodged" : "swept");
            }

            public string StepTo(string side, double now)
            {
                Update(now);
                if (done || now < readyAt || (side != "left" && side != "right")) return null;
                stepAt = now; stepSide = side;
                bool inWindow = Math.Abs(now - sweeps[index] + (c.dodgeBefore - c.dodgeAfter) / 2) <= (c.dodgeBefore + c.dodgeAfter) / 2;
                readyAt = now + (inWindow ? c.recoverSeconds : c.stumbleSeconds);
                lastEvent = inWindow ? "step" : "early";
                return lastEvent;
            }
        }

        static Stage MakeStage(StageConfig c, uint seed)
        {
            switch (c.kind)
            {
                case "stance": return new StanceStage(c, seed);
                case "block": return new BlockStage(c, seed);
                case "dodge": return new DodgeStage(c, seed);
                default: throw new ArgumentException("unknown stage kind " + c.kind);
            }
        }

        // The whole lesson. phase: "demo" (the teacher shows it, input ignored), "play", "stage-failed" (Retry restarts
        // this stage straight away, nothing is taken), "done" (all three stages passed). Times are absolute and monotonic.
        public sealed class Lesson
        {
            public readonly Content content;
            readonly uint seed;
            public readonly int[] attempts;
            public int stageIndex;
            public string phase;
            public double now, phaseStart;
            public Stage stage;

            public Lesson(Content content, uint seed = 7)
            {
                this.content = content; this.seed = seed;
                attempts = new int[content.stages.Length];
                Begin(0);
            }

            void Begin(double at)
            {
                now = at; phase = "demo"; phaseStart = at; stage = null;
                attempts[stageIndex]++;
            }

            public StageConfig Config => content.stages[stageIndex];
            public bool Passed => phase == "done";
            public double Elapsed => now - phaseStart;

            public void Update(double at)
            {
                Clock(at, now);
                now = at;
                if (phase == "demo")
                {
                    if (at - phaseStart < content.demoSeconds) return;
                    phase = "play";
                    phaseStart += content.demoSeconds;
                    // A new layout each attempt, so a retry is not a memory test; still fixed per seed.
                    stage = MakeStage(Config, unchecked(seed + (uint)stageIndex * 101u + (uint)attempts[stageIndex] * 7u));
                }
                if (phase != "play") return;
                stage.Update(at - phaseStart);
                if (stage.done) FinishStage();
            }

            void FinishStage()
            {
                if (!stage.Passed) { phase = "stage-failed"; return; }
                if (stageIndex == content.stages.Length - 1) { phase = "done"; return; }
                stageIndex++;
                Begin(now);
            }

            public void SetHeld(bool held) { if (phase == "play" && stage is StanceStage s) s.SetHeld(held); }

            public string Press(double at)
            {
                Update(at);
                if (phase != "play" || !(stage is BlockStage b)) return null;
                var result = b.Press(at - phaseStart);
                if (b.done) FinishStage();
                return result;
            }

            public string StepTo(string side, double at)
            {
                Update(at);
                if (phase != "play" || !(stage is DodgeStage d)) return null;
                return d.StepTo(side, at - phaseStart);
            }

            // After a failed stage: start that same stage again. Earlier stages stay passed; nothing is taken.
            public bool Retry(double at)
            {
                if (phase != "stage-failed") return false;
                Begin(at);
                return true;
            }
        }
    }
}
