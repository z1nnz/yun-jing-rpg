using System;
using QingxiWorld;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.UI;
using UnityEngine.UI;

namespace YunJing
{
    // Local Qingxi walkthrough UI. No account, inventory or reward authority.
    public sealed partial class QingxiHud : MonoBehaviour
    {
        public QingxiFirstPerson walker;
        public QingxiLocalForaging foraging;
        public Material uiMaterial;

        RectTransform safe;
        GameObject journal;
        Text place;
        Text foragingText;
        Text interactionText;
        Text activityResult;
        Button journalButton;
        Font font;
        Canvas hudCanvas;
        Text fortuneText, guideTitle, guideBody;
        bool open;
        int width, height;

        void Start()
        {
            if (walker == null) { enabled = false; return; }
            font = QingxiFonts.Ui != null ? QingxiFonts.Ui : Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            var canvas = new GameObject("Qingxi HUD Canvas", typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
            canvas.transform.SetParent(transform, false);
            var cv = canvas.GetComponent<Canvas>();
            hudCanvas = cv;
            cv.renderMode = RenderMode.ScreenSpaceOverlay;
            cv.sortingOrder = 20;
            var scaler = canvas.GetComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1280, 720);
            scaler.screenMatchMode = CanvasScaler.ScreenMatchMode.MatchWidthOrHeight;
            scaler.matchWidthOrHeight = .5f;

            safe = Rect("Safe Area", canvas.transform, Vector2.zero, Vector2.one, Vector2.zero,
                Vector2.zero, Vector2.zero);
            SafeArea();
            EnsureEventSystem();

            var header = Panel("Place Header", safe, new Vector2(0, 1), new Vector2(0, 1),
                new Vector2(22, -22), new Vector2(330, 78), new Color(.035f, .07f, .09f, .81f));
            var edge = Panel("Turquoise Rule", header, new Vector2(0, 0), new Vector2(0, 1),
                Vector2.zero, new Vector2(4, 0), new Color(.24f, .67f, .66f));
            edge.SetAsFirstSibling();
            place = Label("Place", header, "青溪小鎮", 24, FontStyle.Bold,
                new Vector2(18, -10), new Vector2(280, 34), new Color(.94f, .92f, .81f));
            Label("Subtitle", header, "臨水初入世 · 自由探索", 14, FontStyle.Normal,
                new Vector2(18, -47), new Vector2(280, 25), new Color(.67f, .79f, .76f));

            var guide = Panel("Freedom Guide", safe, new Vector2(1, 1), new Vector2(1, 1),
                new Vector2(-22, -22), new Vector2(312, 108), new Color(.035f, .07f, .09f, .78f));
            guideTitle = Label("Guide Title", guide, "現在可以做", 19, FontStyle.Bold,
                new Vector2(16, -12), new Vector2(270, 28), new Color(.94f, .87f, .66f));
            guideBody = Label("Guide Body", guide, "觀察線索 · 練氣 · 採藥 · 煉製 · 追兔 · 逛坊市", 15, FontStyle.Normal,
                new Vector2(16, -48), new Vector2(280, 44), new Color(.88f, .91f, .88f));

            journalButton = Action("Journey Button", safe, "旅途手札  [M]", new Vector2(1, 1),
                new Vector2(-22, -145), new Vector2(186, 46), ToggleJournal);
            var hint = Panel("Control Hint", safe, new Vector2(0, 0), new Vector2(0, 0),
                new Vector2(22, 22), new Vector2(388, 62), new Color(.035f, .07f, .09f, .72f));
            Label("Control Text", hint, "WASD 行走  ·  Shift 奔跑  ·  空白鍵跳躍\n滑鼠看向四周  ·  Esc 顯示游標", 15,
                FontStyle.Normal, new Vector2(14, -9), new Vector2(358, 48), new Color(.85f, .9f, .87f));

            if (foraging != null)
            {
                var activity = Panel("Local Foraging", safe, new Vector2(1, 0), new Vector2(1, 0),
                    new Vector2(-22, 22), new Vector2(330, 154), new Color(.035f, .07f, .09f, .81f));
                Label("Activity Title", activity, "青溪採獵 · 本機試玩", 18, FontStyle.Bold,
                    new Vector2(14, -9), new Vector2(300, 27), new Color(.94f, .87f, .66f));
                foragingText = Label("Activity Counts", activity, "", 15, FontStyle.Normal,
                    new Vector2(14, -40), new Vector2(300, 46), new Color(.88f, .91f, .88f));
                interactionText = Label("Interaction Prompt", activity, "", 14, FontStyle.Normal,
                    new Vector2(14, -87), new Vector2(300, 32), new Color(.67f, .87f, .83f));
                activityResult = Label("Activity Result", activity, "", 13, FontStyle.Normal,
                    new Vector2(14, -120), new Vector2(300, 28), new Color(.94f, .87f, .66f));
                RefreshForaging();
                foraging.Changed += RefreshForaging;
            }

            journal = Panel("Journey Journal", safe, new Vector2(.5f, .5f), new Vector2(.5f, .5f),
                Vector2.zero, new Vector2(510, 470), new Color(.055f, .095f, .10f, .96f)).gameObject;
            var page = journal.GetComponent<RectTransform>();
            Label("Journal Title", page, "青溪 · 初入世", 29, FontStyle.Bold,
                new Vector2(28, -26), new Vector2(450, 42), new Color(.94f, .87f, .65f));
            Label("Journal Body", page,
                "青溪沒有必做的每日任務。\n\n可觀察山道線索，回聽風台練氣；\n採草後在坊市交換，或煉調息散。\n想活動筋骨，也可追蹤山兔。",
                18, FontStyle.Normal, new Vector2(28, -85), new Vector2(450, 143),
                new Color(.9f, .92f, .87f));
            // 機緣 (K4): found finds by title; the rest only as a count.
            fortuneText = Label("Journal Fortunes", page, "", 15, FontStyle.Normal, new Vector2(28, -236), new Vector2(450, 150),
                new Color(.93f, .84f, .62f));
            Action("Go Plaza", page, "回廣場", new Vector2(0, 0), new Vector2(28, 25),
                new Vector2(128, 48), () => { walker.Teleport(0); ToggleJournal(); });
            if (walker.spotNames.Length > 8)
                Action("Go Terrace", page, "聽風台入口", new Vector2(0, 0), new Vector2(172, 25),
                    new Vector2(146, 48), () => { walker.Teleport(8); ToggleJournal(); });
            Action("Close Journal", page, "繼續探索", new Vector2(0, 0), new Vector2(334, 25),
                new Vector2(148, 48), ToggleJournal);
            journal.SetActive(false);
            walker.useDesignedHud = true;
            walker.LocationChanged += OnLocation;
            OnLocation("青溪小鎮");
            BuildCollaboratorPanels();
        }

        void OnDestroy()
        {
            if (walker != null) walker.LocationChanged -= OnLocation;
            if (foraging != null) foraging.Changed -= RefreshForaging;
        }

        // With on-screen controls the lower corners belong to the joystick and the button arc: the keyboard
        // hint goes away and the foraging panel moves up under the journal button.
        bool touchLayout;
        void TouchLayout(bool touch)
        {
            touchLayout = touch;
            var hint = hudCanvas != null ? hudCanvas.transform.Find("Safe Area/Control Hint") ?? FindDeep(hudCanvas.transform, "Control Hint") : null;
            if (hint != null) hint.gameObject.SetActive(!touch);
            var activity = hudCanvas != null ? FindDeep(hudCanvas.transform, "Local Foraging") as RectTransform : null;
            if (activity == null) return;
            var corner = touch ? new Vector2(1, 1) : new Vector2(1, 0);
            activity.anchorMin = activity.anchorMax = activity.pivot = corner;
            activity.anchoredPosition = touch ? new Vector2(-22, -205) : new Vector2(-22, 22);
        }

        static Transform FindDeep(Transform root, string name)
        {
            foreach (var t in root.GetComponentsInChildren<Transform>(true)) if (t.name == name) return t;
            return null;
        }

        void Update()
        {
            // Johnnnny0823's drills take the whole screen, as in his web demo.
            if (hudCanvas != null) hudCanvas.enabled = !QingxiTrainingPractice.Practising;
            if (QingxiTouchControls.Active != touchLayout) TouchLayout(QingxiTouchControls.Active);
            if (Screen.width != width || Screen.height != height) SafeArea();
            if (Keyboard.current != null && Keyboard.current.mKey.wasPressedThisFrame) ToggleJournal();
            if (foraging != null && interactionText != null)
                interactionText.text = foraging.Prompt(walker.transform.position);
            UpdateCollaboratorPanels();
            // The novice days (QingxiNoviceDays): today's thread, when there is one.
            var today = QingxiNoviceDays.Objective;
            if (guideTitle != null) guideTitle.text = today != null ? $"新手第 {QingxiNoviceDays.Day} 天" : "現在可以做";
            if (guideBody != null) guideBody.text = today ?? "觀察線索 · 練氣 · 採藥 · 煉製 · 追兔 · 逛坊市";
        }

        void RefreshForaging()
        {
            if (foragingText != null)
                foragingText.text = $"靈草 {foraging.Herbs} · 山兔 {foraging.Rabbits} · 練習靈石 {foraging.PracticeStones}\n線索 {foraging.ObservedClues} · 調息散 {foraging.PracticePellets} · 領悟 {foraging.Insights}";
            if (activityResult != null) activityResult.text = foraging.LastMessage;
        }

        void OnLocation(string location)
        {
            if (place == null) return;
            place.text = location == "Entrance_ListeningTerrace" ? "聽風台入口" :
                location == "Entrance_MaterialShop" ? "坊市入口" : location;
        }

        void ToggleJournal()
        {
            open = !open;
            journal.SetActive(open);
            walker.SetMenuOpen(open);
            if (open && fortuneText != null) fortuneText.text = QingxiFortunes.Current != null ? QingxiFortunes.Current.JournalText() : "";
            if (open && EventSystem.current != null)
            {
                var button = journal.transform.Find("Close Journal")?.gameObject;
                EventSystem.current.SetSelectedGameObject(button);
            }
            else if (EventSystem.current != null) EventSystem.current.SetSelectedGameObject(journalButton.gameObject);
        }

        void SafeArea()
        {
            width = Screen.width; height = Screen.height;
            var s = Screen.safeArea;
            safe.anchorMin = new Vector2(s.xMin / width, s.yMin / height);
            safe.anchorMax = new Vector2(s.xMax / width, s.yMax / height);
        }

        static RectTransform Rect(string name, Transform parent, Vector2 min, Vector2 max,
            Vector2 anchored, Vector2 size, Vector2 pivot)
        {
            var go = new GameObject(name, typeof(RectTransform));
            go.transform.SetParent(parent, false);
            var rect = go.GetComponent<RectTransform>();
            rect.anchorMin = min; rect.anchorMax = max; rect.pivot = pivot;
            rect.anchoredPosition = anchored; rect.sizeDelta = size;
            return rect;
        }

        RectTransform Panel(string name, Transform parent, Vector2 anchorMin, Vector2 anchorMax,
            Vector2 anchored, Vector2 size, Color color)
        {
            var pivot = anchorMin == new Vector2(1, 1) ? new Vector2(1, 1) :
                anchorMin == new Vector2(1, 0) ? new Vector2(1, 0) :
                anchorMin == new Vector2(0, 1) ? new Vector2(0, 1) :
                anchorMin == new Vector2(0, 0) ? new Vector2(0, 0) : new Vector2(.5f, .5f);
            var rect = Rect(name, parent, anchorMin, anchorMax, anchored, size, pivot);
            var image = rect.gameObject.AddComponent<UnityEngine.UI.Image>();
            image.color = color;
            if (uiMaterial != null) image.material = uiMaterial;
            return rect;
        }

        Text Label(string name, Transform parent, string value, int size, FontStyle style,
            Vector2 offset, Vector2 bounds, Color color)
        {
            var rect = Rect(name, parent, new Vector2(0, 1), new Vector2(0, 1), offset, bounds,
                new Vector2(0, 1));
            var t = rect.gameObject.AddComponent<Text>();
            t.font = style == FontStyle.Bold && size >= 18 && QingxiFonts.Title != null ? QingxiFonts.Title : font; t.text = value; t.fontSize = size; t.fontStyle = style;
            if (uiMaterial != null) t.material = uiMaterial;
            t.color = color; t.alignment = TextAnchor.UpperLeft;
            t.horizontalOverflow = HorizontalWrapMode.Wrap;
            t.verticalOverflow = VerticalWrapMode.Overflow;
            return t;
        }

        Button Action(string name, Transform parent, string title, Vector2 anchor, Vector2 offset,
            Vector2 size, UnityEngine.Events.UnityAction clicked)
        {
            var rect = Panel(name, parent, anchor, anchor, offset, size, new Color(.13f, .31f, .33f, .94f));
            var button = rect.gameObject.AddComponent<Button>();
            button.onClick.AddListener(clicked);
            var text = Label("Caption", rect, title, 17, FontStyle.Bold, new Vector2(10, -10),
                size - new Vector2(20, 12), new Color(.95f, .94f, .84f));
            text.alignment = TextAnchor.MiddleCenter;
            return button;
        }

        static void EnsureEventSystem()
        {
            if (EventSystem.current != null) return;
            var go = new GameObject("Qingxi UI Event System", typeof(EventSystem), typeof(InputSystemUIInputModule));
            go.GetComponent<EventSystem>().sendNavigationEvents = true;
            go.GetComponent<InputSystemUIInputModule>().AssignDefaultActions();
        }
    }
}
