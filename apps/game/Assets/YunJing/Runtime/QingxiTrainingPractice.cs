using System.Collections.Generic;
using QingxiWorld;
using UnityEngine;
using UnityEngine.InputSystem;
using Rules = YunJing.QingxiTrainingPracticeRules;

namespace YunJing
{
    // Johnnnny0823's two training-yard drills (tools/training-yard-demo) on his posts in the novice village:
    // F at the qi striking post starts 引氣呼吸, F at the agility post starts 武技格擋. Rules are the C# port
    // QingxiTrainingPracticeRules; the presentation follows his web demo (app.mjs, style.css, audio.mjs):
    // the camera glides to the post, the breath ring (gold guide, jade qi) with 吸／停／呼／歇, rope bands and
    // the jade disc glowing with qi and spirit motes drawn in; the wooden arms wind up and strike, approach
    // rings close on the block buttons, sparks, hit-stop, camera shake and a red flash when hit; synthesized
    // sound (QingxiTrainingSfx). Keyboard, mouse and touch; Esc leaves. Local only: the result card is
    // feedback for this round and never becomes cultivation.
    public sealed class QingxiTrainingPractice : MonoBehaviour
    {
        const float Reach = 1.9f, Eye = 1.64f;
        public Transform qiPost, blockPost;
        public string qiLabel = "氣勁木樁";
        public QingxiFirstPerson walker;
        public Material glowLine, glowDot;   // additive URP particle materials (made by the scene builders)

        public Rules.BreathSession Breath { get; private set; }
        public Rules.BlockSession Block { get; private set; }
        public bool Active => Breath != null || Block != null || showingResult || (Lesson != null && Lesson.Running);
        public string LastResult { get; private set; }
        public bool Frozen { get; private set; }
        public static bool Practising { get; private set; }   // a drill or its result card is on screen

        double clock;
        bool touchHeld, showingResult;
        string pendingTouchSide, lastKind, toast;
        float toastUntil;

        QingxiBodyLesson lesson;
        // 沈岳的第一堂練體課 runs on the agility post until it has been passed once; after that the post is the plain drill.
        QingxiBodyLesson Lesson
        {
            get
            {
                if (lesson != null || blockPost == null) return lesson;
                lesson = GetComponent<QingxiBodyLesson>();
                if (lesson == null) lesson = gameObject.AddComponent<QingxiBodyLesson>();
                lesson.training = this;
                return lesson;
            }
        }

        static float Flat(Vector3 a, Vector3 b) => Vector2.Distance(new Vector2(a.x, a.z), new Vector2(b.x, b.z));

        public string Prompt(Vector3 position)
        {
            if (Active) return null;
            if (qiPost != null && Flat(position, qiPost.position) <= Reach) return $"F 引氣呼吸・{qiLabel}";
            if (blockPost != null && Flat(position, blockPost.position) <= Reach)
                return Lesson != null && !Lesson.EverPassed && Lesson.PromptText != null ? Lesson.PromptText : "F 武技格擋・身法木樁";
            return null;
        }

        public bool TryInteract(Vector3 position, out string message)
        {
            message = null;
            if (Active) return false;
            if (qiPost != null && Flat(position, qiPost.position) <= Reach) { StartQi(); message = "凝神：金圈擴張時按住，收回時放開"; return true; }
            if (blockPost != null && Flat(position, blockPost.position) <= Reach)
            {
                if (Lesson != null && !Lesson.EverPassed && Lesson.Begin()) return true;
                StartBlock(); message = "木臂蓄勢：光圈收到時按 A／S／D 格擋"; return true;
            }
            return false;
        }

        // Local practice has no birth record, so the spirit-root gate stays open here.
        public void StartQi()
        {
            Stop(false); clock = 0; lastKind = "qi";
            Breath = new Rules.BreathSession(true, 3, 0);
            cycleSeen = 0;
            Freeze(true); BeginCamera(qiPost, 1.65f); SetUpQiEffects();
            Sfx.BreathStart();
        }

        public void StartBlock()
        {
            Stop(false); clock = 0; lastKind = "body";
            Block = new Rules.BlockSession((uint)(7 + Random.Range(0, 5)), 0);
            lastJudged = 0; ticked = -1; hitStop = 0;
            Freeze(true); BeginCamera(blockPost, 2.3f); SetUpArms();
        }

        // Leaves at once (Esc, or the smoke test): no result card, walker free again.
        public void End() => Stop(true);

        void Stop(bool release)
        {
            Breath = null; Block = null; showingResult = false; touchHeld = false; pendingTouchSide = null;
            if (sfx != null) sfx.BreathStop();
            HideEffects(); RestArms();
            if (release) { RestoreCamera(); Freeze(false); }
        }

        // Same pause the travel journal uses: no walking or F/E while drilling, and the cursor is free for the
        // on-screen buttons. The walker stays enabled so QingxiFirstPerson.Current keeps working.
        void Freeze(bool on)
        {
            if (walker == null) walker = QingxiFirstPerson.Current;
            if (walker != null && Frozen != on) walker.SetMenuOpen(on);
            Frozen = on; Practising = on;
            // First person at the post: hide the player's own body, which would stand between camera and post.
            if (walker != null)
                foreach (var r in walker.GetComponentsInChildren<Renderer>(true))
                    if (r is not ParticleSystemRenderer && r is not LineRenderer && (Camera.main == null || !r.transform.IsChildOf(Camera.main.transform)))
                    {
                        if (on && r.enabled) { r.enabled = false; hiddenBody.Add(r); }
                    }
            if (!on) { foreach (var r in hiddenBody) if (r != null) r.enabled = true; hiddenBody.Clear(); }
        }

        readonly List<Renderer> hiddenBody = new List<Renderer>();
        QingxiTrainingSfx sfx;
        QingxiTrainingSfx Sfx => sfx != null ? sfx : sfx = gameObject.AddComponent<QingxiTrainingSfx>();

        // Review hook: --drill-qi / --drill-block (or ?drill=qi / ?drill=block in the browser) walks to the
        // post and starts that drill; --drill-shots also saves screenshots next to the player and quits.
        System.Collections.IEnumerator Start()
        {
            string args = string.Join(" ", System.Environment.GetCommandLineArgs()) + " " + Application.absoluteURL;
            bool qi = args.Contains("drill-qi") || args.Contains("drill=qi"), body = args.Contains("drill-block") || args.Contains("drill=block");
            bool lessonHook = args.Contains("drill-lesson") || args.Contains("drill=lesson");
            if (!qi && !body && !lessonHook) yield break;
            yield return new WaitForSeconds(1.5f);
            var post = qi && !lessonHook ? qiPost : blockPost;
            if (post == null) yield break;
            if (walker == null) walker = QingxiFirstPerson.Current;
            var cc = walker != null ? walker.GetComponent<CharacterController>() : null;
            if (cc != null) { cc.enabled = false; walker.transform.position = post.position + Vector3.back * 1.6f + Vector3.up * .1f; cc.enabled = true; }
            yield return null;
            if (lessonHook) { Lesson?.Begin(); yield break; }
            if (qi) StartQi(); else StartBlock();
            if (!args.Contains("drill-shots")) yield break;
            var folder = System.IO.Path.GetDirectoryName(Application.dataPath);
            // Read the finished frame back (HUD included) at the end of the frame.
            System.Collections.IEnumerator Grab(int i)
            {
                yield return new WaitForEndOfFrame();
                var tex = new Texture2D(Screen.width, Screen.height, TextureFormat.RGB24, false);
                tex.ReadPixels(new Rect(0, 0, Screen.width, Screen.height), 0, 0); tex.Apply();
                System.IO.File.WriteAllBytes(System.IO.Path.Combine(folder, $"drill-{(qi ? "qi" : "block")}-{i}.png"), tex.EncodeToPNG());
                Destroy(tex);
            }
            void Shot(int i) => StartCoroutine(Grab(i));
            if (qi)
            {
                // Lead-in, mid inhale (held), exhale (released).
                yield return new WaitForSeconds(1.2f); Shot(0);
                touchHeld = true; yield return new WaitForSeconds(2.4f); Shot(1);
                yield return new WaitForSeconds(1.2f); touchHeld = false; yield return new WaitForSeconds(2.4f); Shot(2);
            }
            else
            {
                // First wind-up; a block right on the strike (judgement, sparks); the next wind-up.
                yield return new WaitForSeconds(1.6f); Shot(0);
                while (Block != null && Block.Next.HasValue && Block.Next.Value.at - Block.Elapsed > .02) yield return null;
                if (Block != null && Block.Next.HasValue) pendingTouchSide = Block.Next.Value.side;
                yield return new WaitForSeconds(.12f); Shot(1);
                yield return new WaitForSeconds(.8f); Shot(2);
            }
            yield return new WaitForSeconds(1);
            Application.Quit();
        }

        // ------------------------------------------------------------------ frame
        void Update()
        {
            var kb = Keyboard.current; var mouse = Mouse.current;
            if (showingResult)
            {
                if (kb != null && kb.escapeKey.wasPressedThisFrame) End();
                return;
            }
            if (Breath == null && Block == null) return;
            if (kb != null && kb.escapeKey.wasPressedThisFrame) { Toast("中途收功"); LastResult = "中途收功"; End(); return; }
            float dt = Mathf.Min(Time.deltaTime, .1f);
            shake = Mathf.Max(0, shake - dt * .6f);
            hitFlash = Mathf.Max(0, hitFlash - dt * 4);
            if (Breath != null) UpdateQi(kb, mouse, dt);
            else UpdateBlock(kb, dt);
        }

        void UpdateQi(Keyboard kb, Mouse mouse, float dt)
        {
            clock += dt;
            bool held = touchHeld || (kb != null && kb.spaceKey.isPressed) || (mouse != null && mouse.leftButton.isPressed);
            Breath.SetHeld(held);
            Breath.Update(clock);
            var scores = Breath.FinishedScores;
            if (scores.Length > cycleSeen)
            {
                if (Rules.GradeBreath(scores[scores.Length - 1]) != "散亂") Sfx.Chime(1 + cycleSeen * .12f);
                cycleSeen = scores.Length;
            }
            float qi = (float)Breath.qi, sync = (float)Breath.Sync;
            int cycle = Breath.CurrentGuide.cycle;
            // Completed bands stay lit by their grade; the current one breathes with qi; the disc glows with sync.
            for (int i = 0; i < bands.Count; i++)
            {
                float target = i < scores.Length ? (scores[i] >= .85 ? .75f : scores[i] >= .7 ? .45f : .08f) : i == cycle ? qi * .4f : 0;
                bandGlow[i] = Mathf.Lerp(bandGlow[i], target, Mathf.Min(1, dt * 6));
                Tint(bands[i], Jade, bandGlow[i]);
            }
            if (disc != null)
            {
                Tint(disc, Jade, .15f + .6f * qi * sync);
                disc.transform.localScale = Vector3.one * (.85f + .35f * qi);
            }
            UpdateMotes(Time.time, .35f + .6f * qi, sync);
            Sfx.BreathSet(qi, sync);
            if (Breath.done)
            {
                var s = Breath.FinishedScores;
                int h = Breath.Harmonised;
                ShowResult("引氣呼吸・" + qiLabel, h == 3 ? "三息調和" : h > 0 ? $"{h} 息調和" : "氣息未定",
                    $"三息：{string.Join("・", System.Array.ConvertAll(s, Rules.GradeBreath))}。繩圈亮起代表該息跟上節奏；跟不上可再練一次。");
            }
        }

        void UpdateBlock(Keyboard kb, float dt)
        {
            string side = pendingTouchSide;
            pendingTouchSide = null;
            if (kb != null)
            {
                if (kb.aKey.wasPressedThisFrame || kb.leftArrowKey.wasPressedThisFrame) side = "left";
                if (kb.sKey.wasPressedThisFrame || kb.downArrowKey.wasPressedThisFrame) side = "low";
                if (kb.dKey.wasPressedThisFrame || kb.rightArrowKey.wasPressedThisFrame) side = "right";
            }
            // Freeze frames on a clean block; a press during them is kept for the next frame.
            if (hitStop > 0) { hitStop -= dt; if (side != null) pendingTouchSide = side; return; }
            clock += dt;
            if (side != null)
            {
                pressedUntil[side] = Time.time + .12f;
                var judged = Block.Input(side, clock);
                if (judged.HasValue) ShowJudge(judged.Value, side);
            }
            else
            {
                Block.Update(clock);
                if (Block.results.Count > lastJudged) ShowJudge(Block.results[Block.results.Count - 1], null);
            }
            lastJudged = Block.results.Count;
            PoseArms();
            var next = Block.Next;
            if (next.HasValue && next.Value.at - Block.Elapsed < .6 && ticked != Block.results.Count)
            {
                Sfx.Tick(next.Value.side == "low");
                ticked = Block.results.Count;
            }
            if (Block.done)
                ShowResult("武技格擋・身法木樁", Block.Grade,
                    $"擋下 {Block.Blocked}／{Block.strikes.Count}（精準 {Block.Perfect}），最高連擋 {Block.bestCombo}，散架 {Block.flinches} 次。");
        }

        void ShowJudge(Rules.Judged j, string pressed)
        {
            judge = j.result; judgeAt = Time.time;
            var tip = ArmTip(j.side ?? pressed ?? "left");
            if (j.result == "perfect" || j.result == "good")
            {
                Sfx.Clack(j.result == "perfect" ? 1 : .7f);
                if (j.result == "perfect") Sfx.Chime(1.5f);
                Burst(tip, j.result == "perfect" ? new Color(1, .88f, .63f) : new Color(1, .95f, .86f));
                hitStop = .07f; shake = .05f;
                blockTip = "保持節奏";
            }
            else if (j.result == "hit")
            {
                Sfx.Thud(); shake = .14f; hitFlash = 1;
                blockTip = string.IsNullOrEmpty(j.reason) ? "中招，看清木臂後擺的方向" : j.reason;
            }
            else { Sfx.Tick(false); shake = .03f; blockTip = "沒有來勢時別出手，架勢會散"; }
        }

        void ShowResult(string kind, string grade, string detail)
        {
            // A passed drill counts as one basic practice on the server (qi needs a spirit root; the server decides).
            bool passed = Breath != null ? Breath.Harmonised >= 1 : Block != null && Block.Blocked >= 8;
            if (passed) QingxiServerLink.Current?.Submit(new GameAction { kind = "practice-basic", discipline = Breath != null ? "qi" : "body" });
            Sfx.BreathStop();
            Breath = null; Block = null;
            HideEffects(); RestArms();
            resultKind = kind; resultGrade = grade; resultDetail = detail; showingResult = true;
            LastResult = $"{kind}：{grade}";
        }

        void Toast(string text) { toast = text; toastUntil = Time.time + 2.5f; }

        // ------------------------------------------------------------------ lent to QingxiBodyLesson (same camera, arms, sound and HUD as the drills)
        internal void LessonStyles() => Styles();
        internal void LessonHold(bool on)
        {
            if (on) { Stop(false); Freeze(true); BeginCamera(blockPost, 3.1f); }
            else { RestArms(); RestoreCamera(); Freeze(false); LastResult = "練體課"; }
        }
        internal void LessonTick(float dt) { shake = Mathf.Max(0, shake - dt * .6f); }
        internal void LessonArmsSetUp() => SetUpArms();
        internal void LessonArmsRest() => RestArms();
        internal void LessonArmPose(string side, double eta)
        {
            RestArms();
            if (eta >= -.35 && arms.TryGetValue(side, out var arm)) arm.t.RotateAround(arm.pivot, arm.axis, arm.degrees * ArmAmount(eta));
        }
        // A sideways step: the camera slides off and back, so the dodge reads without a player model.
        internal void LessonStep(string side) { stepOffset = (side == "left" ? -1 : 1) * .55f; Sfx.Tick(true); }
        float stepOffset;
        internal void LessonEffects(string kind, string side)
        {
            switch (kind)
            {
                case "perfect": Sfx.Clack(1); Sfx.Chime(1.5f); Burst(ArmTip(side), new Color(1, .88f, .63f)); shake = .05f; break;
                case "good": Sfx.Clack(.7f); Burst(ArmTip(side), new Color(1, .95f, .86f)); shake = .05f; break;
                case "hit": Sfx.Thud(); shake = .14f; break;
                case "tick": Sfx.Tick(false); shake = .03f; break;
                case "chime": Sfx.Chime(1.2f); break;
            }
        }

        // ------------------------------------------------------------------ camera
        Transform cam;
        Vector3 camLocalPos, camFrom, camTo, lookAt;
        Quaternion camLocalRot, camFromRot;
        float camT, shake, hitFlash, hitStop;
        bool camHeld;

        void BeginCamera(Transform post, float distance)
        {
            if (post == null) return;
            var main = Camera.main;
            if (main == null) return;
            if (!camHeld) { cam = main.transform; camLocalPos = cam.localPosition; camLocalRot = cam.localRotation; camHeld = true; }
            camFrom = cam.position; camFromRot = cam.rotation; camT = 0;
            // Stand on the side the player came from, at the distance of his practice poses.
            var away = cam.position - post.position; away.y = 0;
            if (away.sqrMagnitude < .01f) away = -post.forward;
            away.y = 0; away.Normalize();
            var bounds = Bounds(post, null);
            var focus = post == qiPost ? Bounds(post, "jade_disc") : Bounds(post, "arm_");
            // Face the post's working side: the jade disc, or the side the wooden arms reach toward.
            var facing = focus.center - bounds.center; facing.y = 0;
            if (focus.size != Vector3.zero && facing.sqrMagnitude > .0025f) away = facing.normalized;
            camTo = new Vector3(bounds.center.x, post.position.y + Eye - .06f, bounds.center.z) + away * distance;
            lookAt = focus.size == Vector3.zero ? bounds.center + Vector3.up * .3f : focus.center;
            viewDir = -away;
        }

        void RestoreCamera()
        {
            if (!camHeld || cam == null) return;
            cam.localPosition = camLocalPos; cam.localRotation = camLocalRot;
            camHeld = false;
        }

        void LateUpdate()
        {
            if (!camHeld || cam == null) return;
            camT = Mathf.Min(1, camT + Time.deltaTime / .9f);
            float e = camT * camT * (3 - 2 * camT);
            cam.position = Vector3.Lerp(camFrom, camTo, e);
            cam.rotation = Quaternion.Slerp(camFromRot, Quaternion.LookRotation(lookAt - camTo), e);
            if (shake > 0) cam.position += cam.right * ((Random.value - .5f) * shake) + cam.up * ((Random.value - .5f) * shake);
            if (stepOffset != 0)
            {
                cam.position += cam.right * stepOffset;
                stepOffset = Mathf.MoveTowards(stepOffset, 0, Time.deltaTime * 1.1f);
            }
            if (disc != null && cam != null) disc.transform.rotation = Quaternion.LookRotation(disc.transform.position - cam.position);
        }

        static Bounds Bounds(Transform root, string part)
        {
            bool any = false; var b = new Bounds(root.position, Vector3.zero);
            foreach (var r in root.GetComponentsInChildren<Renderer>())
            {
                if (part != null && !r.name.Contains(part)) continue;
                if (r is ParticleSystemRenderer || r is LineRenderer) continue;
                if (!any) { b = r.bounds; any = true; } else b.Encapsulate(r.bounds);
            }
            return any ? b : new Bounds(root.position, Vector3.zero);
        }

        // ------------------------------------------------------------------ wooden arms
        struct Arm { public Transform t; public Vector3 restPos, pivot, axis; public Quaternion restRot; public float degrees; }
        readonly Dictionary<string, Arm> arms = new Dictionary<string, Arm>();
        Vector3 viewDir = Vector3.forward;

        void SetUpArms()
        {
            arms.Clear();
            if (blockPost == null) return;
            var centre = Bounds(blockPost, null).center;
            foreach (var side in Rules.Sides)
            {
                Transform node = null;
                foreach (var r in blockPost.GetComponentsInChildren<Renderer>()) if (r.name.Contains("arm_" + side)) { node = r.transform; break; }
                if (node == null) continue;
                var b = node.GetComponent<Renderer>().bounds;
                // Hinge on the face of the arm nearest the post's axis; the arm's centre stands in for its tip.
                var pivot = b.ClosestPoint(new Vector3(centre.x, b.center.y, centre.z));
                var tip = b.center - pivot;
                // Side arms lift and chop in the plane facing the player; the low arm pulls back and thrusts.
                var axis = side == "low" ? Vector3.Cross(Vector3.up, viewDir).normalized : viewDir;
                float degrees = side == "low" ? 28.6f : 40f;
                var test = Quaternion.AngleAxis(10, axis) * tip;
                bool rightWay = side == "low" ? Vector3.Dot(test, viewDir) > Vector3.Dot(tip, viewDir) : test.y > tip.y;
                arms[side] = new Arm { t = node, restPos = node.localPosition, restRot = node.localRotation, pivot = pivot, axis = axis, degrees = rightWay ? degrees : -degrees };
            }
        }

        void RestArms()
        {
            foreach (var a in arms.Values) if (a.t != null) { a.t.localPosition = a.restPos; a.t.localRotation = a.restRot; }
        }

        // eta: seconds until impact. Wind back from 0.65 s, swing through at 0, recover by -0.35 s.
        static float ArmAmount(double eta)
        {
            if (eta > .65) return 0;
            if (eta > .12) return Mathf.SmoothStep(0, 1, (float)((.65 - eta) / .53));
            if (eta > 0) return 1 - 1.8f * (1 - (float)eta / .12f);
            return Mathf.Lerp(-.8f, 0, Mathf.Clamp01((float)(-eta / .35)));
        }

        void PoseArms()
        {
            RestArms();
            var posed = new HashSet<string>();
            double now = Block.Elapsed;
            for (int i = Mathf.Max(0, Block.index - 1); i < Block.strikes.Count && posed.Count < 3; i++)
            {
                var s = Block.strikes[i];
                double eta = s.at - now;
                if (eta < -.35 || posed.Contains(s.side) || !arms.TryGetValue(s.side, out var arm)) continue;
                posed.Add(s.side);
                arm.t.RotateAround(arm.pivot, arm.axis, arm.degrees * ArmAmount(eta));
            }
        }

        Vector3 ArmTip(string side) =>
            arms.TryGetValue(side, out var a) && a.t != null ? a.t.GetComponent<Renderer>().bounds.center - viewDir * .15f : lookAt;

        // ------------------------------------------------------------------ glow, motes, sparks
        static readonly Color Jade = new Color(.37f, .88f, .74f);
        readonly List<LineRenderer> bands = new List<LineRenderer>();
        readonly List<float> bandGlow = new List<float>();
        LineRenderer disc;
        ParticleSystem motes, sparks;
        ParticleSystem.Particle[] moteBuffer;
        Vector3 moteCentre;
        int cycleSeen, lastJudged, ticked;

        void SetUpQiEffects()
        {
            HideEffects();
            if (qiPost == null || glowLine == null) return;
            if (bands.Count == 0)
                foreach (var r in qiPost.GetComponentsInChildren<Renderer>())
                {
                    if (!r.name.Contains("rope_band")) continue;
                    var b = r.bounds;
                    bands.Add(Ring("BandGlow", b.center, Mathf.Max(b.extents.x, b.extents.z) + .035f, .05f, Vector3.up));
                    bandGlow.Add(0);
                }
            var d = Bounds(qiPost, "jade_disc");
            if (disc == null && d.size != Vector3.zero) disc = Ring("DiscGlow", d.center, Mathf.Max(d.extents.x, d.extents.y, d.extents.z) * 1.25f, .045f, Vector3.forward);
            moteCentre = d.size != Vector3.zero ? d.center : qiPost.position + Vector3.up * 1.4f;
            if (motes == null) motes = Particles("QiMotes", 140, .045f);
        }

        LineRenderer Ring(string name, Vector3 centre, float radius, float width, Vector3 normal)
        {
            var go = new GameObject(name);
            go.transform.position = centre;   // the disc halo is turned to face the camera in LateUpdate
            var line = go.AddComponent<LineRenderer>();
            line.useWorldSpace = false; line.loop = true; line.positionCount = 40;
            line.widthMultiplier = width; line.sharedMaterial = glowLine;
            line.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; line.receiveShadows = false;
            for (int i = 0; i < 40; i++)
            {
                float a = i / 40f * Mathf.PI * 2;
                // Bands lie flat around the post (XZ); the disc halo stands in the plane facing the camera (XY).
                line.SetPosition(i, normal == Vector3.up ? new Vector3(Mathf.Cos(a) * radius, 0, Mathf.Sin(a) * radius) : new Vector3(Mathf.Cos(a) * radius, Mathf.Sin(a) * radius, 0));
            }
            Tint(line, Jade, 0);
            return line;
        }

        static void Tint(LineRenderer line, Color colour, float opacity)
        {
            if (line == null) return;
            var c = colour * Mathf.Clamp01(opacity); c.a = Mathf.Clamp01(opacity);
            line.startColor = c; line.endColor = c;
        }

        ParticleSystem Particles(string name, int max, float size)
        {
            if (glowDot == null) return null;
            var go = new GameObject(name);
            var ps = go.AddComponent<ParticleSystem>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main;
            main.loop = true; main.playOnAwake = false; main.maxParticles = max; main.duration = 1;
            main.simulationSpace = ParticleSystemSimulationSpace.World; main.startSize = size; main.startLifetime = 1;
            var emission = ps.emission; emission.enabled = false;
            var shape = ps.shape; shape.enabled = false;
            var r = go.GetComponent<ParticleSystemRenderer>();
            r.sharedMaterial = glowDot; r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            ps.Play();
            return ps;
        }

        void UpdateMotes(float t, float strength, float sync)
        {
            if (motes == null) return;
            if (moteBuffer == null) moteBuffer = new ParticleSystem.Particle[140];
            var colour = new Color(.62f, 1, .88f, Mathf.Clamp01(strength));
            for (int i = 0; i < moteBuffer.Length; i++)
            {
                float s = (i * .618034f) % 1, life = (t * (.25f + s * .2f) + s) % 1, k = sync > .6f ? life : life * .35f;
                float ang = s * 40 + t * (.6f + s) + life * 4, rad = (1 - k) * (.6f + s * .9f);
                var p = moteCentre + new Vector3(Mathf.Cos(ang) * rad, (s - .5f) * 1.6f * (1 - k) + Mathf.Sin(t * 2 + s * 9) * .05f, Mathf.Sin(ang) * rad * .7f) - viewDir * (1 - k) * .3f;
                moteBuffer[i].position = p; moteBuffer[i].startSize = .045f; moteBuffer[i].startColor = colour;
                moteBuffer[i].remainingLifetime = 1; moteBuffer[i].startLifetime = 1;
            }
            motes.SetParticles(moteBuffer, moteBuffer.Length);
        }

        void Burst(Vector3 at, Color colour)
        {
            if (sparks == null)
            {
                sparks = Particles("BlockSparks", 120, .05f);
                if (sparks == null) return;
                var main = sparks.main; main.gravityModifier = .61f; main.startLifetime = .45f;
                var fade = sparks.colorOverLifetime; fade.enabled = true;
                var g = new Gradient();
                g.SetKeys(new[] { new GradientColorKey(Color.white, 0), new GradientColorKey(Color.white, 1) }, new[] { new GradientAlphaKey(1, 0), new GradientAlphaKey(0, 1) });
                fade.color = g;
            }
            var right = Vector3.Cross(Vector3.up, viewDir);
            for (int i = 0; i < 60; i++)
            {
                var v = (right * (Random.value - .5f) + Vector3.up * Random.value * .8f + -viewDir * (Random.value - .2f)).normalized * (1.5f + Random.value * 2.5f);
                sparks.Emit(new ParticleSystem.EmitParams { position = at, velocity = v, startColor = colour, startSize = .05f, startLifetime = .45f, applyShapeToPosition = false }, 1);
            }
        }

        void HideEffects()
        {
            for (int i = 0; i < bands.Count; i++) { bandGlow[i] = 0; Tint(bands[i], Jade, 0); }
            Tint(disc, Jade, 0);
            if (motes != null) motes.Clear();
        }

        // ------------------------------------------------------------------ HUD (ink panels, gold lines, jade glow)
        string judge, blockTip, resultKind, resultGrade, resultDetail;
        float judgeAt;
        readonly Dictionary<string, float> pressedUntil = new Dictionary<string, float> { { "left", 0 }, { "low", 0 }, { "right", 0 } };
        internal static Texture2D ringTex, dashTex, discTex, softTex, barTex, vignetteTex, panelTex, pillTex;
        internal GUIStyle small, body, serifBig, serifMid, title, eyebrow;
        static readonly Color Ink = new Color(.055f, .1f, .09f, .82f), Gold = new Color(.84f, .7f, .42f), Gold2 = new Color(.95f, .84f, .59f),
            Paper = new Color(.94f, .9f, .82f), Muted = new Color(.73f, .69f, .61f), Red = new Color(.88f, .34f, .25f);

        void Styles()
        {
            if (small != null) return;
            GUIStyle S(Font f, int size, Color c, TextAnchor a, FontStyle fs = FontStyle.Normal) =>
                new GUIStyle { font = f, fontSize = size, alignment = a, fontStyle = fs, normal = { textColor = c }, wordWrap = true, richText = true };
            var ui = QingxiFonts.Ui; var serif = QingxiFonts.Title;
            small = S(ui, 13, Paper, TextAnchor.MiddleCenter);
            body = S(ui, 16, Paper, TextAnchor.MiddleLeft);
            serifBig = S(serif, 64, Color.white, TextAnchor.MiddleCenter, FontStyle.Bold);
            serifMid = S(serif, 30, Paper, TextAnchor.MiddleLeft, FontStyle.Bold);
            title = S(serif, 30, Paper, TextAnchor.UpperLeft, FontStyle.Bold);
            eyebrow = S(ui, 12, Gold2, TextAnchor.UpperLeft);
            if (ringTex == null)
            {
                ringTex = Circle(256, 120, 7, false, 1);
                dashTex = Circle(256, 120, 5, true, 1);
                discTex = Circle(256, 124, 0, false, 1);
                softTex = Circle(128, 40, 0, false, 24);
                barTex = Rounded(32, 15, Color.white, Color.white);
                vignetteTex = Vignette(256);
                panelTex = Rounded(64, 14, Ink, new Color(Gold.r, Gold.g, Gold.b, .45f));
                pillTex = Rounded(48, 23, Ink, new Color(Gold.r, Gold.g, Gold.b, .45f));
            }
        }

        // Anti-aliased circle: a ring of the given stroke, a dashed ring, or a filled disc (stroke 0); feather
        // softens the edge (large feather = glow).
        static Texture2D Circle(int size, float radius, float stroke, bool dashed, float feather)
        {
            var tex = new Texture2D(size, size, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp };
            var px = new Color32[size * size];
            float c = size / 2f - .5f;
            for (int y = 0; y < size; y++)
                for (int x = 0; x < size; x++)
                {
                    float dx = x - c, dy = y - c, d = Mathf.Sqrt(dx * dx + dy * dy);
                    float a = stroke > 0 ? Mathf.Clamp01((stroke / 2 + .5f - Mathf.Abs(d - radius)) / Mathf.Max(1, feather)) : Mathf.Clamp01((radius - d) / feather + .5f);
                    if (dashed && stroke > 0) { float ang = Mathf.Atan2(dy, dx) / (Mathf.PI * 2) * 48; if (ang - Mathf.Floor(ang) > .55f) a = 0; }
                    px[y * size + x] = new Color32(255, 255, 255, (byte)(a * 255));
                }
            tex.SetPixels32(px); tex.Apply();
            return tex;
        }

        static Texture2D Vignette(int size)
        {
            var tex = new Texture2D(size, size, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp };
            var px = new Color32[size * size];
            for (int y = 0; y < size; y++)
                for (int x = 0; x < size; x++)
                {
                    float dx = (x - size / 2f) / (size / 2f), dy = (y - size / 2f) / (size / 2f);
                    float a = Mathf.SmoothStep(0, 1, Mathf.InverseLerp(.5f, 1.15f, Mathf.Sqrt(dx * dx + dy * dy)));
                    px[y * size + x] = new Color32(255, 255, 255, (byte)(a * 255));
                }
            tex.SetPixels32(px); tex.Apply();
            return tex;
        }

        static Texture2D Rounded(int size, float radius, Color fill, Color border)
        {
            var tex = new Texture2D(size, size, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp };
            var px = new Color[size * size];
            for (int y = 0; y < size; y++)
                for (int x = 0; x < size; x++)
                {
                    float qx = Mathf.Max(Mathf.Abs(x + .5f - size / 2f) - (size / 2f - radius), 0), qy = Mathf.Max(Mathf.Abs(y + .5f - size / 2f) - (size / 2f - radius), 0);
                    float d = Mathf.Sqrt(qx * qx + qy * qy) - radius;   // signed distance to the rounded edge
                    float inside = Mathf.Clamp01(.5f - d), edge = Mathf.Clamp01(1 - Mathf.Abs(d + .75f));
                    var c = Color.Lerp(fill, border, edge); c.a = Mathf.Max(fill.a, edge * border.a) * inside;
                    px[y * size + x] = c;
                }
            tex.SetPixels(px); tex.Apply();
            return tex;
        }

        internal static void Draw(Rect r, Texture tex, Color colour)
        {
            var old = GUI.color; GUI.color = colour; GUI.DrawTexture(r, tex); GUI.color = old;
        }

        internal static void Panel(Rect r, Texture2D tex, int border)
        {
            var style = new GUIStyle { normal = { background = tex }, border = new RectOffset(border, border, border, border) };
            if (Event.current.type == EventType.Repaint) style.Draw(r, false, false, false, false);
        }

        // Rounded strip that keeps its round ends at any length (9-slice), tinted.
        internal static void Sliced(Rect r, Texture2D tex, int border, Color colour)
        {
            if (Event.current.type != EventType.Repaint) return;
            var old = GUI.color; GUI.color = colour;
            new GUIStyle { normal = { background = tex }, border = new RectOffset(border, border, border, border) }.Draw(r, false, false, false, false);
            GUI.color = old;
        }

        internal static Rect Centred(Vector2 c, float size) => new Rect(c.x - size / 2, c.y - size / 2, size, size);

        void Text(Rect r, string s, GUIStyle style, Color glow)
        {
            if (glow.a > 0)
            {
                var g = new GUIStyle(style) { normal = { textColor = glow } };
                for (int i = 0; i < 4; i++) GUI.Label(new Rect(r.x + (i % 2 * 2 - 1) * 1.5f, r.y + (i / 2 * 2 - 1) * 1.5f, r.width, r.height), s, g);
            }
            GUI.Label(r, s, style);
        }

        void OnGUI()
        {
            QingxiFonts.ApplyImgui();
            Styles();
            float scale = Mathf.Clamp(Screen.height / 720f, .7f, 2f);
            var previous = GUI.matrix;
            GUI.matrix = Matrix4x4.Scale(Vector3.one * scale);
            float w = Screen.width / scale, h = Screen.height / scale;
            if (Lesson != null && Lesson.Running) { GUI.matrix = previous; return; }
            if (!Active)
            {
                if (toast != null && Time.time < toastUntil) { var r = new Rect(w / 2 - 110, h * .2f, 220, 40); Panel(r, pillTex, 20); GUI.Label(r, toast, small); }
                GUI.matrix = previous;
                return;
            }
            // Vignette: deep teal while breathing, a red flash when a strike lands.
            if (Breath != null) Draw(new Rect(0, 0, w, h), vignetteTex, new Color(.04f, .16f, .13f, .55f));
            if (hitFlash > 0) Draw(new Rect(0, 0, w, h), vignetteTex, new Color(.67f, .12f, .08f, .6f * hitFlash));
            // Title block, top left.
            GUI.Label(new Rect(20, 14, 400, 18), "承天・青溪新手村", eyebrow);
            GUI.Label(new Rect(18, 30, 400, 40), "公 共 演 武 區", title);
            var notice = new Rect(20, 74, 250, 26); Panel(notice, pillTex, 12); GUI.Label(notice, Rules.Notice, small);
            if (Breath != null) DrawQi(w, h);
            else if (Block != null) DrawBlock(w, h);
            if (showingResult) DrawResult(w, h);
            GUI.matrix = previous;
        }

        void DrawQi(float w, float h)
        {
            float size = Mathf.Min(h * .42f, 300);
            var c = new Vector2(w - w * .09f - size / 2, h / 2);
            Draw(Centred(c, size), discTex, new Color(.04f, .09f, .08f, .35f));
            Draw(Centred(c, size), ringTex, new Color(1, 1, 1, .12f));
            float guide = (float)Breath.GuideValue, qi = (float)Breath.qi;
            // Same proportions as his SVG: guide radius 26 + 62g, qi radius 18 + 70q (of 100).
            float gr = size * (26 + 62 * guide) / 100, qr = size * (18 + 70 * qi) / 100;
            Draw(Centred(c, qr * 1.12f), softTex, new Color(Jade.r, Jade.g, Jade.b, .22f));
            Draw(Centred(c, qr), discTex, new Color(Jade.r, Jade.g, Jade.b, .16f));
            Draw(Centred(c, qr), ringTex, new Color(Jade.r, Jade.g, Jade.b, .95f));
            Draw(Centred(c, gr), dashTex, new Color(Gold.r, Gold.g, Gold.b, .95f));
            string label = Breath.Elapsed < 0 ? "凝" : Breath.CurrentGuide.label;
            Text(Centred(c, size), label, serifBig, new Color(Jade.r, Jade.g, Jade.b, .35f));

            // Left column: the three breaths, the instruction, sync.
            float x = w * .06f, y = h / 2 - 70, colW = Mathf.Min(300, w * .34f);
            var scores = Breath.FinishedScores;
            int cycle = Breath.CurrentGuide.cycle;
            for (int i = 0; i < 3; i++)
            {
                var pill = new Rect(x + i * 46, y, 36, 12);
                Color fill = i < scores.Length ? (scores[i] >= .85 ? Jade : scores[i] >= .7 ? Gold : new Color(.5f, .25f, .2f)) : new Color(0, 0, 0, .35f);
                Sliced(pill, barTex, 6, fill);
                if (i == cycle && i >= scores.Length) Draw(new Rect(pill.x - 2, pill.y - 2, pill.width + 4, pill.height + 4), ringTex, Gold2);
            }
            var phase = Breath.CurrentGuide.phase;
            string tip = Breath.Elapsed < 0 ? "凝神。金圈開始擴張時按住。" : phase == "inhale" ? "吸——按住，讓玉圈跟著金圈長大" :
                phase == "hold" ? "停——繼續按住" : phase == "exhale" ? "呼——放開，讓氣緩緩散回" : "歇——放鬆，準備下一息";
            var tipRect = new Rect(x, y + 26, colW, 44); Panel(tipRect, panelTex, 14);
            GUI.Label(new Rect(tipRect.x + 14, tipRect.y, tipRect.width - 20, tipRect.height), tip, body);
            GUI.Label(new Rect(x, y + 82, colW, 18), $"同步  {Breath.Sync:P0}", new GUIStyle(body) { fontSize = 13, normal = { textColor = Muted } });
            var bar = new Rect(x, y + 104, colW, 8);
            Sliced(bar, barTex, 4, new Color(0, 0, 0, .4f));
            Sliced(new Rect(bar.x, bar.y, Mathf.Max(bar.height, bar.width * (float)Breath.Sync), bar.height), barTex, 4, Jade);

            // Hold button (touch and mouse), bottom right.
            var hold = new Rect(w - 30 - 132, h - 30 - 132, 132, 132);
            var e = Event.current;
            if (e.type == EventType.MouseDown && hold.Contains(e.mousePosition)) { touchHeld = true; e.Use(); }
            if (e.type == EventType.MouseUp) touchHeld = false;
            Draw(hold, discTex, touchHeld ? new Color(Jade.r * .5f, Jade.g * .5f, Jade.b * .5f, .9f) : Ink);
            Draw(hold, ringTex, touchHeld ? Jade : Gold);
            if (touchHeld) Draw(new Rect(hold.x - 14, hold.y - 14, hold.width + 28, hold.height + 28), softTex, new Color(Jade.r, Jade.g, Jade.b, .35f));
            GUI.Label(new Rect(hold.x, hold.y + 34, hold.width, 40), "按住", new GUIStyle(serifMid) { alignment = TextAnchor.MiddleCenter });
            GUI.Label(new Rect(hold.x, hold.y + 76, hold.width, 20), "空白鍵／滑鼠", new GUIStyle(small) { fontSize = 11, normal = { textColor = Muted } });
        }

        void DrawBlock(float w, float h)
        {
            // Combo, left.
            GUI.Label(new Rect(w * .06f, h * .4f, 160, 70), Block.combo.ToString(), new GUIStyle(serifBig) { alignment = TextAnchor.MiddleLeft, fontSize = 56 });
            GUI.Label(new Rect(w * .06f + 4, h * .4f + 64, 160, 20), "連擋", new GUIStyle(body) { fontSize = 13, normal = { textColor = Gold2 } });
            GUI.Label(new Rect(w / 2 - 120, 18, 240, 20), $"第 {Mathf.Min(Block.results.Count + 1, Block.strikes.Count)}／{Block.strikes.Count} 擊", small);

            // Judgement, centre: pops in, fades after 0.6 s.
            if (judge != null && Time.time - judgeAt < .8f)
            {
                float k = Time.time - judgeAt, pop = Mathf.Lerp(1.3f, 1, Mathf.Clamp01(k / .15f)), fade = 1 - Mathf.Clamp01((k - .5f) / .3f);
                string text = judge == "perfect" ? "精準" : judge == "good" ? "擋下" : judge == "hit" ? "中招" : "散架";
                var colour = judge == "perfect" ? Gold2 : judge == "good" ? Color.white : judge == "hit" ? Red : Muted;
                colour.a = fade;
                var style = new GUIStyle(serifBig) { fontSize = Mathf.RoundToInt(58 * pop), normal = { textColor = colour } };
                Text(new Rect(w / 2 - 200, h * .3f - 40, 400, 80), text, style, new Color(0, 0, 0, .35f * fade));
            }

            // Three block buttons, bottom centre, judged on press; the approach ring closes on the moment.
            string[] sides = { "left", "low", "right" }; string[] labels = { "← 左臂", "↓ 下樁", "右臂 →" }; string[] keys = { "A", "S", "D" };
            float size = 108, gap = 26, x0 = w / 2 - (size * 3 + gap * 2) / 2, y = h - size - 52;
            var e = Event.current;
            double now = Block.Elapsed;
            for (int i = 0; i < 3; i++)
            {
                var r = new Rect(x0 + i * (size + gap), y, size, size);
                if (e.type == EventType.MouseDown && r.Contains(e.mousePosition)) { pendingTouchSide = sides[i]; e.Use(); }
                bool pressed = Time.time < pressedUntil[sides[i]];
                var shown = pressed ? Centred(r.center, size * .94f) : r;
                double eta = double.MaxValue;
                for (int s = Block.index; s < Block.strikes.Count && s < Block.index + 4; s++)
                    if (Block.strikes[s].side == sides[i]) { eta = Block.strikes[s].at - now; break; }
                bool armed = eta < .9 && eta > -Rules.GoodWindow;
                Draw(shown, discTex, Ink);
                Draw(shown, ringTex, armed ? Gold2 : new Color(Gold.r, Gold.g, Gold.b, .6f));
                if (armed)
                {
                    float k = Mathf.Max(0, (float)eta) / .9f;
                    Draw(Centred(r.center, size * (1 + k * .9f)), ringTex, new Color(Gold2.r, Gold2.g, Gold2.b, 1 - k * .6f));
                    Draw(Centred(r.center, size * 1.2f), softTex, new Color(Gold.r, Gold.g, Gold.b, .18f * (1 - k)));
                }
                GUI.Label(new Rect(shown.x, shown.y + size * .32f, shown.width, 26), labels[i], new GUIStyle(body) { alignment = TextAnchor.MiddleCenter, fontSize = 18 });
                GUI.Label(new Rect(shown.x, shown.y + size * .58f, shown.width, 18), keys[i], new GUIStyle(small) { fontSize = 12, normal = { textColor = Muted } });
            }
            if (!string.IsNullOrEmpty(blockTip))
                GUI.Label(new Rect(w / 2 - 260, h - 40, 520, 22), blockTip, new GUIStyle(small) { fontSize = 14 });
        }

        void DrawResult(float w, float h)
        {
            var card = new Rect(w / 2 - 270, h / 2 - 135, 540, 270);
            Panel(card, panelTex, 14);
            GUI.Label(new Rect(card.x + 26, card.y + 22, 480, 20), resultKind, eyebrow);
            GUI.Label(new Rect(card.x + 24, card.y + 44, 480, 48), resultGrade, new GUIStyle(serifMid) { fontSize = 32 });
            GUI.Label(new Rect(card.x + 26, card.y + 98, 488, 60), resultDetail, new GUIStyle(body) { fontSize = 15, alignment = TextAnchor.UpperLeft });
            GUI.Label(new Rect(card.x + 26, card.y + 158, 488, 20), "成績只供本輪參考。" + Rules.Notice, new GUIStyle(body) { fontSize = 12, normal = { textColor = Muted } });
            var again = new Rect(card.x + 26, card.y + 200, 150, 44); var leave = new Rect(card.x + 190, card.y + 200, 150, 44);
            Sliced(again, barTex, 15, Gold); Panel(leave, pillTex, 20);
            if (GUI.Button(again, "再練一次", new GUIStyle(body) { alignment = TextAnchor.MiddleCenter, fontStyle = FontStyle.Bold, normal = { textColor = new Color(.06f, .11f, .1f) } }))
            { if (lastKind == "qi") StartQi(); else StartBlock(); }
            if (GUI.Button(leave, "收功離開", new GUIStyle(body) { alignment = TextAnchor.MiddleCenter })) End();
        }
    }
}
