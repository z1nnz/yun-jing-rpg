using System.Collections.Generic;
using QingxiWorld;
using UnityEngine;
using UnityEngine.InputSystem;

namespace YunJing.Tea
{
    // 第 1 天・在家泡茶 at the home tea stove (TI_TeaStove). Choose a tea and scoops, boil on small / medium / large
    // fire reading the steam, add the leaves, pour. TeaPot replays the server rules; the event log it records is
    // what the server's tea-finish action takes. Offline in the lodging interior (like the bed), so the leaf stock
    // here is a local drill copy of what the tea-pavilion lesson grants.
    public sealed class TeaBrewingPanel : MonoBehaviour
    {
        public static TeaBrewingPanel Current { get; private set; }
        public static double RestMultiplier = 1; public static float RestUntil;   // read by the bed

        public Transform stove;                 // steam rises from here (TI_TeaStove kettle spout height)
        public float spoutHeight = .82f;
        public bool Open { get; private set; }
        public TeaPot Pot { get; private set; }
        public TeaJudgement Last { get; private set; }
        public enum Phase { Choose, Boil, Steep, Result }
        public Phase Stage { get; private set; }
        public readonly Dictionary<string, int> Leaves = new Dictionary<string, int> { { "qingxi-wild-tea", 4 }, { "plum-blossom-tea", 4 } };

        int teaIndex, scoops = 3, openedFrame = -1; float acc; ParticleSystem steam; ParticleSystem.EmissionModule emission; ParticleSystem.MainModule steamMain;

        void Awake() { Current = this; }

        public void Show()
        {
            Open = true; openedFrame = Time.frameCount; Stage = Phase.Choose; Pot = null; Last = null; teaIndex = Mathf.Clamp(teaIndex, 0, TeaContent.teas.Length - 1);
            scoops = TeaContent.teas[teaIndex].idealScoops;
            QingxiFirstPerson.Current?.SetMenuOpen(true);
        }

        public void Close()
        {
            if (Stage == Phase.Boil) Abandon();
            Open = false; Pot = null; Stage = Phase.Choose; SetSteam(0);
            QingxiFirstPerson.Current?.SetMenuOpen(false);
        }

        public bool Begin()
        {
            var kind = TeaContent.teas[teaIndex];
            if (Leaves[kind.id] < scoops) return false;
            Leaves[kind.id] -= scoops; Pot = new TeaPot(kind, scoops); Stage = Phase.Boil; acc = 0; return true;
        }
        public void Abandon() { if (Pot != null && Pot.BrewTemp == null) Leaves[Pot.Kind.id] += Pot.Scoops; Pot = null; Stage = Phase.Choose; }
        public void SetFire(int level) { if (Stage == Phase.Boil) Pot.SetFire(level); }
        public void AddLeaves() { if (Stage != Phase.Boil) return; Pot.AddLeaves(); Stage = Phase.Steep; }
        public void Pour()
        {
            if (Stage != Phase.Steep) return;
            Last = Pot.Pour(); Stage = Phase.Result;
            RestMultiplier = Last.restMultiplier; RestUntil = Time.time + TeaContent.restBonusMinutes * 60f;
        }
        public void SelectTea(int index) { if (Stage == Phase.Choose) { teaIndex = index; scoops = TeaContent.teas[index].idealScoops; } }
        public void SetScoops(int value) { if (Stage == Phase.Choose) scoops = Mathf.Clamp(value, TeaContent.minScoops, TeaContent.maxScoops); }

        /// <summary>Advance the pot by whole 0.1 s ticks (also used by the scripted playtest).</summary>
        public void Advance(int ticks) { for (int i = 0; i < ticks && Pot != null && Pot.CanContinue; i++) Pot.Step(); }

        void Update()
        {
            if (!Open) return;
            if (Pot != null && (Stage == Phase.Boil || Stage == Phase.Steep))
            {
                acc += Time.deltaTime;
                while (acc >= (float)TeaContent.step) { acc -= (float)TeaContent.step; Advance(1); }
                if (Stage == Phase.Steep && !Pot.CanContinue) Pour();   // the pot is never left forever: it pours itself at the log limit
            }
            SetSteam(Pot != null && Stage == Phase.Boil ? TeaContent.SteamStage(Pot.T) : Stage == Phase.Steep ? 1 : 0);
            var kb = Keyboard.current; if (kb == null || Time.frameCount == openedFrame) return;   // the F that opened the panel is not a choice
            if (kb.escapeKey.wasPressedThisFrame) { Close(); return; }
            switch (Stage)
            {
                case Phase.Choose:
                    if (kb.qKey.wasPressedThisFrame) SelectTea(0);
                    if (kb.eKey.wasPressedThisFrame) SelectTea(1);
                    if (kb.aKey.wasPressedThisFrame) SetScoops(scoops - 1);
                    if (kb.dKey.wasPressedThisFrame) SetScoops(scoops + 1);
                    if (kb.spaceKey.wasPressedThisFrame || kb.fKey.wasPressedThisFrame) Begin();
                    break;
                case Phase.Boil:
                    for (int i = 0; i < 4; i++) if (kb[(Key)((int)Key.Digit1 + i)].wasPressedThisFrame) SetFire(i);
                    if (kb.spaceKey.wasPressedThisFrame) AddLeaves();
                    break;
                case Phase.Steep: if (kb.spaceKey.wasPressedThisFrame) Pour(); break;
                case Phase.Result: if (kb.spaceKey.wasPressedThisFrame || kb.fKey.wasPressedThisFrame) Close(); break;
            }
        }

        // Steam at the spout follows the stage the player is meant to read: none, wisp, fish-eye, pearls, roaring.
        void SetSteam(int stage)
        {
            if (stove == null) return;
            if (steam == null)
            {
                var go = new GameObject("TeaSteam"); go.transform.SetParent(stove, false); go.transform.localPosition = Vector3.up * spoutHeight;
                steam = go.AddComponent<ParticleSystem>(); steam.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
                steamMain = steam.main; steamMain.loop = true; steamMain.startLifetime = 1.8f; steamMain.startSpeed = .2f; steamMain.startSize = .08f;
                steamMain.startColor = new Color(.96f, .96f, .98f, .8f); steamMain.simulationSpace = ParticleSystemSimulationSpace.World; steamMain.gravityModifier = -.03f;
                var shape = steam.shape; shape.shapeType = ParticleSystemShapeType.Cone; shape.angle = 8; shape.radius = .015f;
                shape.rotation = new Vector3(-90, 0, 0);
                var size = steam.sizeOverLifetime; size.enabled = true; size.size = new ParticleSystem.MinMaxCurve(1, AnimationCurve.Linear(0, .6f, 1, 3f));
                var fade = steam.colorOverLifetime; fade.enabled = true;
                var g = new Gradient(); g.SetKeys(new[] { new GradientColorKey(Color.white, 0), new GradientColorKey(Color.white, 1) },
                    new[] { new GradientAlphaKey(0, 0), new GradientAlphaKey(.75f, .15f), new GradientAlphaKey(0, 1) });
                fade.color = g;
                var r = steam.GetComponent<ParticleSystemRenderer>();
                var shader = Shader.Find("Universal Render Pipeline/Particles/Unlit") ?? Shader.Find("Sprites/Default");
                var puff = new Material(shader) { color = new Color(1, 1, 1, .5f), mainTexture = SoftDot() };
                if (puff.HasProperty("_BaseMap")) puff.SetTexture("_BaseMap", puff.mainTexture);
                if (puff.HasProperty("_Surface")) { puff.SetFloat("_Surface", 1); puff.SetFloat("_Blend", 0); puff.EnableKeyword("_SURFACE_TYPE_TRANSPARENT"); }
                puff.SetOverrideTag("RenderType", "Transparent"); puff.renderQueue = 3000;
                puff.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha); puff.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha); puff.SetInt("_ZWrite", 0);
                r.sharedMaterial = puff;
                emission = steam.emission; steam.Play();
            }
            emission.rateOverTime = new[] { 0f, 4f, 10f, 22f, 40f }[stage];
            steamMain.startSpeed = new[] { 0f, .08f, .13f, .2f, .3f }[stage];
        }

        // Round puff with a soft edge, so steam reads as vapour instead of square sprites.
        static Texture2D SoftDot()
        {
            const int n = 64; var t = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp };
            for (int y = 0; y < n; y++) for (int x = 0; x < n; x++)
            {
                float d = Vector2.Distance(new Vector2(x + .5f, y + .5f), new Vector2(n / 2f, n / 2f)) / (n / 2f);
                t.SetPixel(x, y, new Color(1, 1, 1, Mathf.Pow(Mathf.Clamp01(1 - d), 2)));
            }
            t.Apply(); return t;
        }

        static GUIStyle big, wrap;
        static Texture2D swatch;
        void OnGUI()
        {
            if (!Open) return;
            QingxiFonts.ApplyImgui();
            big ??= new GUIStyle(GUI.skin.label) { fontSize = 34, alignment = TextAnchor.MiddleCenter };
            wrap ??= new GUIStyle(GUI.skin.label) { wordWrap = true, fontSize = 15 };
            float scale = Mathf.Clamp(Screen.height / 720f, .7f, 2f);
            var previous = GUI.matrix; GUI.matrix = Matrix4x4.Scale(Vector3.one * scale);
            float w = 420, h = 330, x = Screen.width / scale - w - 24, y = 24;
            GUI.Box(new Rect(x, y, w, h), "茶爐・泡茶");
            GUILayout.BeginArea(new Rect(x + 14, y + 26, w - 28, h - 36));
            switch (Stage)
            {
                case Phase.Choose: DrawChoose(); break;
                case Phase.Boil: DrawBoil(); break;
                case Phase.Steep: DrawSteep(); break;
                case Phase.Result: DrawResult(); break;
            }
            GUILayout.EndArea();
            GUI.matrix = previous;
        }

        void DrawChoose()
        {
            var kind = TeaContent.teas[teaIndex];
            GUILayout.Label("選茶（Q／E）", wrap);
            GUILayout.BeginHorizontal();
            for (int i = 0; i < TeaContent.teas.Length; i++)
            {
                var t = TeaContent.teas[i];
                if (GUILayout.Toggle(i == teaIndex, $"{t.label}　剩 {Leaves[t.id]}", "Button", GUILayout.Height(34))) SelectTea(i);
            }
            GUILayout.EndHorizontal();
            GUILayout.Space(6);
            GUILayout.BeginHorizontal();
            GUILayout.Label($"分量（A／D）：{scoops} 匙", wrap, GUILayout.Width(170));
            if (GUILayout.Button("－", GUILayout.Width(44), GUILayout.Height(30))) SetScoops(scoops - 1);
            if (GUILayout.Button("＋", GUILayout.Width(44), GUILayout.Height(30))) SetScoops(scoops + 1);
            GUILayout.EndHorizontal();
            GUILayout.Label("老人說：" + kind.hint, wrap);
            GUILayout.FlexibleSpace();
            bool enough = Leaves[kind.id] >= scoops;
            GUI.enabled = enough;
            if (GUILayout.Button(enough ? "取水上爐（空白鍵）" : "茶葉不夠", GUILayout.Height(40))) Begin();
            GUI.enabled = true;
            if (GUILayout.Button("離開（Esc）", GUILayout.Height(28))) Close();
        }

        void DrawBoil()
        {
            var s = TeaContent.steam[TeaContent.SteamStage(Pot.T)];
            GUILayout.Label($"{Pot.Kind.label}・{Pot.Scoops} 匙", wrap);
            GUILayout.Label("壺口：" + s.label, big, GUILayout.Height(46));
            GUILayout.Label(s.hint, wrap);
            GUILayout.Space(6);
            GUILayout.Label("火候（1–4）", wrap);
            GUILayout.BeginHorizontal();
            for (int i = 0; i < 4; i++)
                if (GUILayout.Toggle(Pot.Fire == i, TeaContent.fireLabels[i], "Button", GUILayout.Height(34))) SetFire(i);
            GUILayout.EndHorizontal();
            GUILayout.FlexibleSpace();
            if (GUILayout.Button("投茶，沖水入壺（空白鍵）", GUILayout.Height(40))) AddLeaves();
            if (GUILayout.Button("不泡了，茶葉收回（Esc）", GUILayout.Height(28))) Close();
        }

        void DrawSteep()
        {
            GUILayout.Label($"{Pot.Kind.label} 在壺裡舒展", wrap);
            float k = Mathf.Clamp01((float)(Pot.Strength / (Pot.Kind.bitterAbove * 1.15)));
            var liquor = Color.Lerp(new Color(.93f, .9f, .72f), new Color(.42f, .22f, .06f), k);
            if (Pot.Kind.id == "plum-blossom-tea") liquor = Color.Lerp(new Color(.97f, .9f, .86f), new Color(.55f, .25f, .2f), k);
            swatch ??= new Texture2D(1, 1); swatch.SetPixel(0, 0, liquor); swatch.Apply();
            var r = GUILayoutUtility.GetRect(380, 90);
            GUI.DrawTexture(new Rect(r.x + 120, r.y + 4, 140, 82), swatch);
            GUILayout.Label("看湯色，覺得剛好就出湯。", wrap);
            GUILayout.FlexibleSpace();
            if (GUILayout.Button("出湯（空白鍵）", GUILayout.Height(44))) Pour();
        }

        void DrawResult()
        {
            GUILayout.Label($"{Pot.Kind.label}：{Last.label}", big, GUILayout.Height(48));
            GUILayout.Label(Last.describe, wrap);
            foreach (var reason in Last.reasons) GUILayout.Label("・" + reason, wrap);
            GUILayout.Space(4);
            GUILayout.Label($"喝下這杯茶。躺床療傷恢復 ×{Last.restMultiplier:0.00}（{TeaContent.restBonusMinutes} 分鐘）", wrap);
            GUILayout.FlexibleSpace();
            if (GUILayout.Button("好（空白鍵）", GUILayout.Height(40))) Close();
        }
    }
}
