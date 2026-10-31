using System;
using UnityEngine;
using UnityEngine.InputSystem;
using Rules = YunJing.QingxiBodyLessonRules;

namespace YunJing
{
    // 沈岳的第一堂練體課 on the agility post: stance, block, dodge. Rules and numbers are QingxiBodyLessonRules and
    // packages/content/body-training-lesson-1.json. QingxiTrainingPractice starts it and lends the camera, the wooden arms,
    // the sound and the HUD textures, so this looks and plays like the drills. Shen Yue is a slot frame until the core team's
    // model and lines arrive. Keyboard, mouse and touch; Esc leaves. Local only: a pass raises Passed for the server side to
    // act on and grants nothing here; failing costs nothing and restarts the stage.
    public sealed class QingxiBodyLesson : MonoBehaviour
    {
        const string ContentPath = "QingxiBodyLesson/body-training-lesson-1";
        const string PassedKey = "qingxi.body-lesson-1.passed";

        public QingxiTrainingPractice training;
        public static event Action<string> Passed;     // the lesson id, once per pass

        public Rules.Lesson Lesson { get; private set; }
        public bool Running => Lesson != null;
        public bool EverPassed => PlayerPrefs.GetInt(PassedKey, 0) == 1;
        public string PromptText => Content?.texts.prompt;

        Rules.Content content;
        Rules.Content Content
        {
            get
            {
                if (content != null) return content;
                var text = Resources.Load<TextAsset>(ContentPath);
                if (text != null) content = JsonUtility.FromJson<Rules.Content>(text.text);
                return content;
            }
        }

        double clock;
        bool touchHeld, touchPress, armsReady, announced;
        string touchSide, judgeText, lastPhase;
        int lastStage = -1, lastResults;
        float judgeAt, hitFlash;
        Color judgeColour;
        LineRenderer frame;

        public bool Begin()
        {
            if (Content == null || training == null) return false;
            uint seed = (uint)UnityEngine.Random.Range(1, 100000);
            Lesson = new Rules.Lesson(Content, seed);
            clock = 0; lastStage = -1; lastResults = 0; lastPhase = null; judgeText = null; touchHeld = false; touchPress = false; touchSide = null; announced = false;
            armsReady = false;
            training.LessonHold(true);
            ShowFrame(true);
            StartReviewHooks();
            return true;
        }

        public void End()
        {
            if (Lesson == null) return;
            Lesson = null;
            training.LessonArmsRest();
            training.LessonHold(false);
            ShowFrame(false);
        }

        void Update()
        {
            if (Lesson == null) return;
            var kb = Keyboard.current; var mouse = Mouse.current;
            if (kb != null && kb.escapeKey.wasPressedThisFrame) { End(); return; }
            float dt = Mathf.Min(Time.deltaTime, .1f);
            hitFlash = Mathf.Max(0, hitFlash - dt * 4);
            training.LessonTick(dt);

            if (auto) AutoEnd();
            if (Lesson == null) return;
            if (Lesson.phase == "stage-failed" || Lesson.phase == "done")
            {
                if (Lesson.phase == "stage-failed" && kb != null && (kb.fKey.wasPressedThisFrame || kb.enterKey.wasPressedThisFrame)) Retry();
                else if (Lesson.phase == "done" && kb != null && (kb.fKey.wasPressedThisFrame || kb.enterKey.wasPressedThisFrame)) End();
                return;
            }

            clock += dt;
            Lesson.Update(clock);
            Advance();
            if (Lesson == null || Lesson.phase != "play") { PoseArms(); return; }
            if (auto) AutoPlay();
            switch (Lesson.stage)
            {
                case Rules.StanceStage _:
                    Lesson.SetHeld(touchHeld || (kb != null && kb.spaceKey.isPressed) || (mouse != null && mouse.leftButton.isPressed && !OverButton(mouse)));
                    break;
                case Rules.BlockStage _:
                    if (touchPress || (kb != null && (kb.spaceKey.wasPressedThisFrame || kb.fKey.wasPressedThisFrame)))
                    {
                        var r = Lesson.Press(clock);
                        if (r == "early") { Judge(Content.texts.tip.blockEarly, Muted); training.LessonEffects("tick", "right"); }
                    }
                    break;
                case Rules.DodgeStage _:
                    string side = touchSide;
                    if (kb != null && (kb.aKey.wasPressedThisFrame || kb.leftArrowKey.wasPressedThisFrame)) side = "left";
                    if (kb != null && (kb.dKey.wasPressedThisFrame || kb.rightArrowKey.wasPressedThisFrame)) side = "right";
                    if (side != null)
                    {
                        var r = Lesson.StepTo(side, clock);
                        if (r != null) training.LessonStep(side);
                        if (r == "early") Judge(Content.texts.tip.dodgeEarly, Muted);
                    }
                    break;
            }
            touchPress = false; touchSide = null;
            Advance();
            PoseArms();
        }

        public void Retry()
        {
            if (Lesson != null && Lesson.Retry(clock)) { judgeText = null; lastResults = 0; }
        }

        bool OverButton(Mouse mouse)
        {
            var p = mouse.position.ReadValue();
            float scale = Scale;
            return HoldRect(Screen.width / scale, Screen.height / scale).Contains(new Vector2(p.x / scale, (Screen.height - p.y) / scale));
        }

        static float Scale => Mathf.Clamp(Screen.height / 720f, .7f, 2f);

        // Judgement text, sound and effects from whatever just changed in the rules.
        void Advance()
        {
            if (Lesson == null) return;
            if (Lesson.stageIndex != lastStage) { lastStage = Lesson.stageIndex; lastResults = 0; armsReady = false; training.LessonArmsRest(); }
            if (Lesson.phase == "play" && !armsReady && !(Lesson.stage is Rules.StanceStage)) { training.LessonArmsSetUp(); armsReady = true; }
            var results = Lesson.stage is Rules.BlockStage b ? b.results : Lesson.stage is Rules.DodgeStage d ? d.results : null;
            if (results != null && results.Count > lastResults)
            {
                var r = results[results.Count - 1];
                lastResults = results.Count;
                var j = Content.texts.judge;
                switch (r)
                {
                    case "perfect": Judge(j.perfect, Gold2); training.LessonEffects("perfect", "right"); break;
                    case "good": Judge(j.good, Color.white); training.LessonEffects("good", "right"); break;
                    case "hit": Judge(j.hit, Red); hitFlash = 1; training.LessonEffects("hit", "right"); break;
                    case "dodged": Judge(j.dodged, Gold2); training.LessonEffects("good", "low"); break;
                    case "swept": Judge(j.swept, Red); hitFlash = 1; training.LessonEffects("hit", "low"); break;
                }
            }
            if (Lesson.phase != lastPhase)
            {
                if (lastPhase == "play" && Lesson.phase == "demo") { Judge(Content.texts.stagePassed, Gold2); }
                if (Lesson.phase == "done" && !announced)
                {
                    announced = true;
                    PlayerPrefs.SetInt(PassedKey, 1); PlayerPrefs.Save();
                    Passed?.Invoke(Content.id);
                    training.LessonEffects("chime", "right");
                }
                lastPhase = Lesson.phase;
            }
        }

        void Judge(string text, Color colour) { judgeText = text; judgeColour = colour; judgeAt = Time.time; }

        void PoseArms()
        {
            if (Lesson == null || !armsReady) return;
            if (Lesson.stage is Rules.BlockStage b && b.Next.HasValue) training.LessonArmPose("right", b.Next.Value - (clock - Lesson.phaseStart));
            else if (Lesson.stage is Rules.DodgeStage d && d.Next.HasValue) training.LessonArmPose("low", d.Next.Value - (clock - Lesson.phaseStart));
            else training.LessonArmsRest();
        }

        // ------------------------------------------------------------------ review hooks: --lesson-auto plays with the same inputs the buttons
        // send (scripted, not a person), --lesson-fail-first misses the first attempt at the block stage to show a retry,
        // --lesson-capture saves 30 fps frames beside the player (for the video) and quits after the lesson.
        bool auto, failFirst, capture;
        float endTimer;
        int frameIndex;

        void StartReviewHooks()
        {
            string args = string.Join(" ", Environment.GetCommandLineArgs()) + " " + Application.absoluteURL;
            auto = args.Contains("lesson-auto");
            failFirst = args.Contains("lesson-fail-first");
            capture = args.Contains("lesson-capture");
            if (capture) { Time.captureFramerate = 30; StartCoroutine(Capture()); }
        }

        void AutoPlay()
        {
            double local = clock - Lesson.phaseStart;
            switch (Lesson.stage)
            {
                case Rules.StanceStage s: touchHeld = s.value < 0; break;
                case Rules.BlockStage b:
                    if (failFirst && Lesson.attempts[Lesson.stageIndex] == 1) break;
                    if (b.Next.HasValue && b.Next.Value - local < .03) touchPress = true;
                    break;
                case Rules.DodgeStage d:
                    if (d.Next.HasValue && d.Next.Value - local < .25 && local >= d.readyAt) touchSide = d.index % 2 == 0 ? "left" : "right";
                    break;
            }
        }

        void AutoEnd()
        {
            if (Lesson.phase != "stage-failed" && Lesson.phase != "done") { endTimer = 0; return; }
            endTimer += Time.deltaTime;
            if (Lesson.phase == "stage-failed" && endTimer > 2.5f) { Retry(); endTimer = 0; }
            else if (Lesson.phase == "done" && endTimer > 3.5f)
            {
                Debug.Log($"QINGXI_BODY_LESSON_RUN passed={Lesson.Passed} attempts={string.Join("-", Lesson.attempts)} frames={frameIndex}");
                End();
                Application.Quit();
            }
        }

        System.Collections.IEnumerator Capture()
        {
            var folder = System.IO.Path.Combine(System.IO.Path.GetDirectoryName(Application.dataPath), "lesson-frames");
            System.IO.Directory.CreateDirectory(folder);
            while (Lesson != null)
            {
                yield return new WaitForEndOfFrame();
                var tex = new Texture2D(Screen.width, Screen.height, TextureFormat.RGB24, false);
                tex.ReadPixels(new Rect(0, 0, Screen.width, Screen.height), 0, 0); tex.Apply();
                System.IO.File.WriteAllBytes(System.IO.Path.Combine(folder, $"f{frameIndex++:00000}.jpg"), tex.EncodeToJPG(90));
                Destroy(tex);
            }
        }

        // ------------------------------------------------------------------ Shen Yue's slot frame (core team's model replaces it)
        void ShowFrame(bool on)
        {
            if (!on) { if (frame != null) frame.gameObject.SetActive(false); return; }
            var post = training.blockPost;
            if (post == null) return;
            if (frame == null)
            {
                var go = new GameObject("BodyLesson_Teacher_Slot");
                frame = go.AddComponent<LineRenderer>();
                frame.useWorldSpace = false; frame.widthMultiplier = .025f; frame.sharedMaterial = training.glowLine;
                frame.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; frame.receiveShadows = false;
                frame.startColor = frame.endColor = new Color(.84f, .7f, .42f, .9f);
                // A 0.6 x 0.6 x 1.75 m box walked as one continuous line.
                var points = new[] {
                    new Vector3(-.3f, 0, -.3f), new Vector3(.3f, 0, -.3f), new Vector3(.3f, 0, .3f), new Vector3(-.3f, 0, .3f), new Vector3(-.3f, 0, -.3f),
                    new Vector3(-.3f, 1.75f, -.3f), new Vector3(.3f, 1.75f, -.3f), new Vector3(.3f, 0, -.3f), new Vector3(.3f, 1.75f, -.3f),
                    new Vector3(.3f, 1.75f, .3f), new Vector3(.3f, 0, .3f), new Vector3(.3f, 1.75f, .3f),
                    new Vector3(-.3f, 1.75f, .3f), new Vector3(-.3f, 0, .3f), new Vector3(-.3f, 1.75f, .3f), new Vector3(-.3f, 1.75f, -.3f) };
                frame.positionCount = points.Length;
                frame.SetPositions(points);
            }
            frame.transform.position = post.position + post.right * 1.2f;
            frame.transform.rotation = post.rotation;
            frame.gameObject.SetActive(true);
        }

        // ------------------------------------------------------------------ HUD (same ink, gold and jade as the drills)
        static readonly Color Jade = new Color(.37f, .88f, .74f), Gold = new Color(.84f, .7f, .42f), Gold2 = new Color(.95f, .84f, .59f),
            Muted = new Color(.73f, .69f, .61f), Red = new Color(.88f, .34f, .25f), Ink = new Color(.055f, .1f, .09f, .82f);

        static Rect HoldRect(float w, float h) => new Rect(w - 30 - 132, h - 30 - 132, 132, 132);

        void OnGUI()
        {
            if (Lesson == null) return;
            QingxiFonts.ApplyImgui();
            training.LessonStyles();
            float scale = Scale;
            var previous = GUI.matrix;
            GUI.matrix = Matrix4x4.Scale(Vector3.one * scale);
            float w = Screen.width / scale, h = Screen.height / scale;
            var tx = Content.texts;

            if (hitFlash > 0) QingxiTrainingPractice.Draw(new Rect(0, 0, w, h), QingxiTrainingPractice.vignetteTex, new Color(.67f, .12f, .08f, .6f * hitFlash));
            GUI.Label(new Rect(20, 14, 400, 18), $"{Content.teacher}・第 {Content.day} 天", training.eyebrow);
            GUI.Label(new Rect(18, 30, 400, 40), Content.title, training.title);
            DrawStagePips(w);
            TeacherLabel(scale);

            string phase = Lesson.phase;
            if (phase == "demo") DrawDemo(w, h);
            else if (phase == "play") DrawPlay(w, h);
            else if (phase == "stage-failed") DrawCard(w, h, tx.stageFailed, Lesson.Config.label, tx.button.retry, Retry);
            else if (phase == "done") DrawCard(w, h, tx.passed, Content.title, tx.button.leave, End);

            if (judgeText != null && Time.time - judgeAt < .9f && phase != "stage-failed" && phase != "done")
            {
                float k = Time.time - judgeAt, fade = 1 - Mathf.Clamp01((k - .55f) / .35f), pop = Mathf.Lerp(1.25f, 1, Mathf.Clamp01(k / .15f));
                var c = judgeColour; c.a = fade;
                var style = new GUIStyle(training.serifBig) { fontSize = Mathf.RoundToInt(50 * pop), normal = { textColor = c } };
                GUI.Label(new Rect(w / 2 - 220, h * .26f - 40, 440, 80), judgeText, style);
            }
            GUI.matrix = previous;
        }

        void DrawStagePips(float w)
        {
            var stages = Content.stages;
            float x = w / 2 - 66 * stages.Length / 2f;
            for (int i = 0; i < stages.Length; i++)
            {
                var r = new Rect(x + i * 66, 22, 58, 26);
                bool passed = i < Lesson.stageIndex || Lesson.phase == "done", now = i == Lesson.stageIndex && Lesson.phase != "done";
                QingxiTrainingPractice.Sliced(r, QingxiTrainingPractice.barTex, 13, passed ? new Color(Jade.r, Jade.g, Jade.b, .85f) : now ? new Color(Gold.r, Gold.g, Gold.b, .9f) : new Color(0, 0, 0, .45f));
                GUI.Label(r, stages[i].label, new GUIStyle(training.small) { normal = { textColor = passed || now ? new Color(.06f, .11f, .1f) : Muted } });
            }
        }

        // A world-space name on the frame, until the model arrives.
        void TeacherLabel(float scale)
        {
            if (frame == null || !frame.gameObject.activeSelf || Camera.main == null) return;
            var p = Camera.main.WorldToScreenPoint(frame.transform.position + Vector3.up * 1.95f);
            if (p.z <= 0) return;
            GUI.Label(new Rect(p.x / scale - 60, (Screen.height - p.y) / scale - 12, 120, 24), Content.teacher, training.small);
        }

        void Tip(float w, float h, string text)
        {
            var r = new Rect(w / 2 - 170, h - 44, 340, 30);
            QingxiTrainingPractice.Panel(r, QingxiTrainingPractice.pillTex, 14);
            GUI.Label(r, text, new GUIStyle(training.small) { fontSize = 14 });
        }

        void DrawDemo(float w, float h)
        {
            var d = Content.texts.demo;
            string line = Lesson.Config.kind == "stance" ? d.stance : Lesson.Config.kind == "block" ? d.block : d.dodge;
            GUI.Label(new Rect(w / 2 - 240, h * .42f, 480, 60), line, new GUIStyle(training.serifMid) { alignment = TextAnchor.MiddleCenter });
            // The demonstration itself: the frame's post shows one beat, the stance bar stays in the middle.
            if (Lesson.Config.kind == "stance") StanceBar(w, h, (float)(Mathf.Sin(Time.time * 2.2f) * Lesson.Config.zone * .7f), 0, true);
            else if (armsReadyForDemo()) training.LessonArmPose(Lesson.Config.kind == "block" ? "right" : "low", Lesson.content.demoSeconds * .75 - Lesson.Elapsed);
        }

        bool armsReadyForDemo()
        {
            if (!armsReady) { training.LessonArmsSetUp(); armsReady = true; }
            return true;
        }

        void DrawPlay(float w, float h)
        {
            var tip = Content.texts.tip;
            var e = Event.current;
            switch (Lesson.stage)
            {
                case Rules.StanceStage s:
                {
                    StanceBar(w, h, (float)s.value, (float)(s.count / Lesson.Config.holdSeconds), s.InZone);
                    GUI.Label(new Rect(w / 2 - 100, h * .36f - 36, 200, 30), $"{s.count:0.0}／{Lesson.Config.holdSeconds:0} 秒", new GUIStyle(training.small) { fontSize = 20 });
                    Tip(w, h, s.Lead < 0 ? tip.stance : s.resets > 0 && s.count < 1 ? tip.stanceReset : s.InZone ? tip.stance : tip.stanceDrift);
                    var hold = HoldRect(w, h);
                    if (e.type == EventType.MouseDown && hold.Contains(e.mousePosition)) { touchHeld = true; e.Use(); }
                    if (e.type == EventType.MouseUp) touchHeld = false;
                    RoundButton(hold, Content.texts.button.hold, "空白鍵", touchHeld, touchHeld ? 0 : -1);
                    break;
                }
                case Rules.BlockStage b:
                {
                    Tally(w, h, b.Blocked, Lesson.Config.required, Lesson.Config.count, b.results.Count);
                    Tip(w, h, tip.block);
                    var r = new Rect(w - 30 - 132, h - 30 - 132, 132, 132);
                    if (e.type == EventType.MouseDown && r.Contains(e.mousePosition)) { touchPress = true; e.Use(); }
                    double eta = b.Next.HasValue ? b.Next.Value - (clock - Lesson.phaseStart) : 9;
                    RoundButton(r, Content.texts.button.block, "空白鍵／F", false, eta < Lesson.Config.windup ? (float)(Math.Max(0, eta) / Lesson.Config.windup) : -1);
                    break;
                }
                case Rules.DodgeStage d:
                {
                    Tally(w, h, d.Dodged, Lesson.Config.required, Lesson.Config.count, d.results.Count);
                    Tip(w, h, tip.dodge);
                    float size = 120, y = h - size - 30;
                    var left = new Rect(30, y, size, size); var right = new Rect(w - 30 - size, y, size, size);
                    if (e.type == EventType.MouseDown && left.Contains(e.mousePosition)) { touchSide = "left"; e.Use(); }
                    if (e.type == EventType.MouseDown && right.Contains(e.mousePosition)) { touchSide = "right"; e.Use(); }
                    double eta = d.Next.HasValue ? d.Next.Value - (clock - Lesson.phaseStart) : 9;
                    float k = eta < Lesson.Config.windup ? (float)(Math.Max(0, eta) / Lesson.Config.windup) : -1;
                    RoundButton(left, "← " + Content.texts.button.left, "A", false, k);
                    RoundButton(right, Content.texts.button.right + " →", "D", false, k);
                    break;
                }
            }
        }

        void StanceBar(float w, float h, float value, float progress, bool inZone)
        {
            var cfg = Lesson.Config;
            float barW = Mathf.Min(w * .6f, 520), x = w / 2 - barW / 2, y = h * .36f;
            var bar = new Rect(x, y, barW, 18);
            QingxiTrainingPractice.Sliced(bar, QingxiTrainingPractice.barTex, 9, new Color(0, 0, 0, .5f));
            float mid = x + barW / 2, half = barW / 2;
            float zone = (float)(cfg.zone / cfg.limit) * half;
            QingxiTrainingPractice.Sliced(new Rect(mid - zone, y, zone * 2, 18), QingxiTrainingPractice.barTex, 9, new Color(Jade.r, Jade.g, Jade.b, .55f));
            float at = mid + Mathf.Clamp(value / (float)cfg.limit, -1, 1) * half;
            QingxiTrainingPractice.Draw(QingxiTrainingPractice.Centred(new Vector2(at, y + 9), 32), QingxiTrainingPractice.discTex, inZone ? Gold2 : Red);
            var fill = new Rect(x, y + 26, barW, 6);
            QingxiTrainingPractice.Sliced(fill, QingxiTrainingPractice.barTex, 3, new Color(0, 0, 0, .4f));
            if (progress > 0) QingxiTrainingPractice.Sliced(new Rect(x, y + 26, Mathf.Max(6, barW * progress), 6), QingxiTrainingPractice.barTex, 3, Jade);
        }

        void Tally(float w, float h, int got, int need, int total, int seen)
        {
            GUI.Label(new Rect(w / 2 - 160, h * .36f - 30, 320, 30), $"{got}／{need}", new GUIStyle(training.serifMid) { alignment = TextAnchor.MiddleCenter });
            float x = w / 2 - 28 * total / 2f;
            for (int i = 0; i < total; i++)
                QingxiTrainingPractice.Draw(new Rect(x + i * 28 + 5, h * .36f + 6, 18, 18), QingxiTrainingPractice.discTex, i < seen ? Muted : new Color(0, 0, 0, .45f));
        }

        // closing < 0: nothing incoming; otherwise the approach ring closes on the moment (1 = just started, 0 = now).
        void RoundButton(Rect r, string label, string hint, bool down, float closing)
        {
            QingxiTrainingPractice.Draw(r, QingxiTrainingPractice.discTex, down ? new Color(Jade.r * .5f, Jade.g * .5f, Jade.b * .5f, .9f) : Ink);
            QingxiTrainingPractice.Draw(r, QingxiTrainingPractice.ringTex, closing >= 0 ? Gold2 : down ? Jade : new Color(Gold.r, Gold.g, Gold.b, .7f));
            if (closing >= 0) QingxiTrainingPractice.Draw(QingxiTrainingPractice.Centred(r.center, r.width * (1 + closing * .9f)), QingxiTrainingPractice.ringTex, new Color(Gold2.r, Gold2.g, Gold2.b, 1 - closing * .6f));
            GUI.Label(new Rect(r.x, r.y + r.height * .3f, r.width, 34), label, new GUIStyle(training.serifMid) { alignment = TextAnchor.MiddleCenter, fontSize = 22 });
            GUI.Label(new Rect(r.x, r.y + r.height * .62f, r.width, 20), hint, new GUIStyle(training.small) { fontSize = 11, normal = { textColor = Muted } });
        }

        void DrawCard(float w, float h, string heading, string eyebrowText, string primary, Action action)
        {
            var card = new Rect(w / 2 - 240, h / 2 - 105, 480, 210);
            QingxiTrainingPractice.Panel(card, QingxiTrainingPractice.panelTex, 14);
            GUI.Label(new Rect(card.x + 26, card.y + 22, 420, 20), eyebrowText, training.eyebrow);
            GUI.Label(new Rect(card.x + 24, card.y + 46, 430, 56), heading, new GUIStyle(training.serifMid) { fontSize = 32 });
            var a = new Rect(card.x + 26, card.y + 136, 170, 48);
            QingxiTrainingPractice.Sliced(a, QingxiTrainingPractice.barTex, 15, Gold);
            if (GUI.Button(a, primary, new GUIStyle(training.body) { alignment = TextAnchor.MiddleCenter, fontStyle = FontStyle.Bold, normal = { textColor = new Color(.06f, .11f, .1f) } })) action();
            if (Lesson != null && Lesson.phase == "stage-failed")
            {
                var b = new Rect(card.x + 210, card.y + 136, 170, 48);
                QingxiTrainingPractice.Panel(b, QingxiTrainingPractice.pillTex, 20);
                if (GUI.Button(b, Content.texts.button.leave, new GUIStyle(training.body) { alignment = TextAnchor.MiddleCenter })) End();
            }
        }
    }
}
