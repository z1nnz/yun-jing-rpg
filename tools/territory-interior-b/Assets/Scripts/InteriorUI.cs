using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

/// Screen UI built in code: interaction prompt, status line, toasts, the chest storage panel, the furnace
/// alchemy panel and a demo cursor. Built on enable (play mode) or by DemoDirector/SceneBuilder (edit mode).
[RequireComponent(typeof(Canvas))]
public class InteriorUI : MonoBehaviour
{
    public static InteriorUI Instance;

    Text prompt, caption, status, toast, title;
    Image promptBg, toastBg;
    RectTransform cursor, cursorRing;
    float toastT, clickT = -1f;
    static Font font;

    static readonly Color Panel = new Color(.09f, .10f, .10f, .9f), Line = new Color(.55f, .75f, .66f, 1f),
        Ink = new Color(.93f, .90f, .83f), Dim = new Color(.62f, .60f, .55f), Gold = new Color(.95f, .80f, .45f),
        Row = new Color(.18f, .19f, .19f, .9f), Empty = new Color(.12f, .12f, .12f, .9f), Frame = new Color(.32f, .32f, .30f, .9f),
        Btn = new Color(.42f, .30f, .16f, .95f), BtnOff = new Color(.25f, .22f, .19f, .9f), Bad = new Color(.85f, .35f, .25f, 1f);

    void OnEnable() { Build(); }

    public static Font GetFont()
    {
        if (font == null)
            font = Font.CreateDynamicFontFromOSFont(new[] { "Microsoft JhengHei UI", "Microsoft JhengHei", "Microsoft YaHei", "Arial" }, 32);
        return font;
    }

    public void Build()
    {
        Instance = this;
        for (int i = transform.childCount - 1; i >= 0; i--) DestroyImmediate(transform.GetChild(i).gameObject);
        bagSlots.Clear(); chestSlots.Clear(); tabs.Clear(); alcButtons.Clear(); shelfBagSlots.Clear(); shelfSlots.Clear();

        var band = MakeImage("TitleBand", transform, new Color(0, 0, 0, .45f));
        Place(band.rectTransform, new Vector2(0, 1), new Vector2(0, 0), new Vector2(1280, 88));
        title = MakeText("Title", transform, "雲境・新手領地｜展示試玩（物品只在本場景，不入正式存檔）", 22, TextAnchor.UpperLeft, Ink);
        Place(title.rectTransform, new Vector2(0, 1), new Vector2(24, -18), new Vector2(760, 34));
        caption = MakeText("Caption", transform, "", 18, TextAnchor.UpperLeft, Dim);
        Place(caption.rectTransform, new Vector2(0, 1), new Vector2(24, -50), new Vector2(760, 30));
        status = MakeText("Status", transform, "", 18, TextAnchor.UpperRight, Ink);
        Place(status.rectTransform, new Vector2(1, 1), new Vector2(-24, -20), new Vector2(520, 30));

        promptBg = MakeImage("PromptBg", transform, Panel);
        Place(promptBg.rectTransform, new Vector2(.5f, 0), new Vector2(0, 70), new Vector2(320, 52));
        prompt = MakeText("Prompt", promptBg.transform, "", 24, TextAnchor.MiddleCenter, Ink);
        Fill(prompt.rectTransform);
        toastBg = MakeImage("ToastBg", transform, new Color(.12f, .16f, .14f, .9f));
        Place(toastBg.rectTransform, new Vector2(.5f, 1), new Vector2(0, -96), new Vector2(440, 48));
        toast = MakeText("Toast", toastBg.transform, "", 22, TextAnchor.MiddleCenter, Ink);
        Fill(toast.rectTransform);

        BuildStorage();
        BuildAlchemy();
        BuildShelf();
        BuildTouch();

        // demo cursor (only the director moves it)
        cursorRing = MakeImage("CursorRing", transform, new Color(1, 1, 1, 0)).rectTransform;
        Place(cursorRing, new Vector2(0, 0), Vector2.zero, new Vector2(36, 36)); cursorRing.pivot = new Vector2(.5f, .5f);
        var c = MakeImage("Cursor", transform, Color.white); cursor = c.rectTransform;
        Place(cursor, new Vector2(0, 0), Vector2.zero, new Vector2(16, 16)); cursor.pivot = new Vector2(0, 1);
        cursor.localRotation = Quaternion.Euler(0, 0, 45); c.gameObject.AddComponent<Outline>().effectColor = new Color(0, 0, 0, .8f);
        cursor.gameObject.SetActive(false); cursorRing.gameObject.SetActive(false);
        SetPrompt(""); toastBg.gameObject.SetActive(false);
    }

    // ---------------------------------------------------------------- general API
    public string PromptText => prompt ? prompt.text : "";
    public void SetPrompt(string s) { prompt.text = s; promptBg.gameObject.SetActive(!string.IsNullOrEmpty(s)); }
    public void SetCaption(string s) { caption.text = s; }
    public void SetStatus(string s) { status.text = s; }
    public void Toast(string s) { toast.text = s; toastBg.gameObject.SetActive(true); toastT = 2.2f; }

    /// Demo cursor: screen position in canvas units (bottom-left origin); click plays a ring pulse.
    public void SetCursor(bool visible, Vector2 pos)
    {
        cursor.gameObject.SetActive(visible); cursorRing.gameObject.SetActive(visible && clickT >= 0f);
        cursor.anchoredPosition = pos; cursorRing.anchoredPosition = pos;
    }
    public void Click() { clickT = 0f; }

    /// Centre of a UI element in canvas units (bottom-left origin).
    public Vector2 CanvasPos(RectTransform rt)
    {
        var canvasRt = (RectTransform)transform;
        Vector3 w = rt.TransformPoint(rt.rect.center);
        Vector3 l = canvasRt.InverseTransformPoint(w);
        return new Vector2(l.x + canvasRt.rect.width / 2f, l.y + canvasRt.rect.height / 2f);
    }

    public void Tick(float dt)
    {
        if (toastT > 0f)
        {
            toastT -= dt;
            float a = Mathf.Clamp01(toastT / .4f);
            toast.color = new Color(Ink.r, Ink.g, Ink.b, a); toastBg.color = new Color(.12f, .16f, .14f, .9f * a);
            if (toastT <= 0f) toastBg.gameObject.SetActive(false);
        }
        if (clickT >= 0f)
        {
            clickT += dt; float k = clickT / .35f;
            var img = cursorRing.GetComponent<Image>();
            img.color = new Color(1f, .9f, .6f, .8f * (1f - k)); cursorRing.localScale = Vector3.one * (.4f + 1.2f * k);
            cursorRing.gameObject.SetActive(cursor.gameObject.activeSelf);
            if (k >= 1f) { clickT = -1f; cursorRing.gameObject.SetActive(false); }
        }
        if (AlchemyOpen) RefreshAlchemy();
    }

    void Update()
    {
        if (DemoDirector.Driving) return;
        if (StorageOpen && Input.mouseScrollDelta.y != 0f) Scroll(Input.mouseScrollDelta.y > 0 ? -1 : 1);
        Tick(Time.deltaTime);
    }

    // ================================================================ storage panel
    // Bag (15 slots) on the left, chest (30 slots, 6 per row, 3 rows visible + scroll, category tabs) on the right.
    // Same-name items stack (×count); 整理 merges partial stacks and orders them by category.
    const float S = 64f, G = 8f;
    const int BagCols = 5, ChestCols = 6, VisibleRows = 3;
    GameObject storagePanel;
    RectTransform bagGrid, chestGrid, scrollThumb, scrollTrack;
    Text bagHeader, chestHeader, detail;
    readonly List<(RectTransform rt, ItemStack stack)> bagSlots = new List<(RectTransform, ItemStack)>(), chestSlots = new List<(RectTransform, ItemStack)>();
    readonly List<RectTransform> tabs = new List<RectTransform>();
    ChestStorage chest; PlayerAvatar player;
    ItemStack selBag, selChest;
    int tab, scrollRow;
    public RectTransform PutButton { get; private set; }
    public RectTransform TakeButton { get; private set; }
    public RectTransform SortButton { get; private set; }
    public RectTransform CloseButton { get; private set; }
    public RectTransform ScrollUpButton { get; private set; }
    public RectTransform ScrollDownButton { get; private set; }

    void BuildStorage()
    {
        var panel = MakeImage("StoragePanel", transform, Panel);
        storagePanel = panel.gameObject;
        Place(panel.rectTransform, new Vector2(.5f, 0), new Vector2(0, 14), new Vector2(1010, 296));
        var p = panel.transform; var tl = new Vector2(0, 1);
        var t = MakeText("Header", p, "儲物箱", 22, TextAnchor.MiddleLeft, Ink); Place(t.rectTransform, tl, new Vector2(22, -10), new Vector2(100, 30));
        detail = MakeText("Detail", p, "", 17, TextAnchor.MiddleLeft, Dim); Place(detail.rectTransform, tl, new Vector2(120, -10), new Vector2(560, 30));
        bagHeader = MakeText("BagHeader", p, "乾坤袋", 17, TextAnchor.MiddleLeft, Line); Place(bagHeader.rectTransform, tl, new Vector2(22, -44), new Vector2(352, 24));
        bagGrid = MakeRect("BagGrid", p); Place(bagGrid, tl, new Vector2(22, -74), new Vector2(BagCols * S + (BagCols - 1) * G, VisibleRows * S + (VisibleRows - 1) * G));

        PutButton = MakeButton("PutButton", p, "放入 →", () => DoPut()); Place(PutButton, tl, new Vector2(394, -96), new Vector2(116, 44));
        TakeButton = MakeButton("TakeButton", p, "← 取出", () => DoTake()); Place(TakeButton, tl, new Vector2(394, -152), new Vector2(116, 44));
        SortButton = MakeButton("SortButton", p, "整理箱子", () => DoSort()); Place(SortButton, tl, new Vector2(394, -208), new Vector2(116, 44));

        for (int i = 0; i < Items.Tabs.Length; i++)
        {
            int k = i;
            var b = MakeButton("Tab_" + i, p, Items.Tabs[i], () => SetTab(k)); Place(b, tl, new Vector2(530 + i * 66, -40), new Vector2(62, 28));
            b.GetComponentInChildren<Text>().fontSize = 16; tabs.Add(b);
        }
        chestHeader = MakeText("ChestHeader", p, "箱內", 17, TextAnchor.MiddleRight, Line); Place(chestHeader.rectTransform, tl, new Vector2(860, -42), new Vector2(128, 24));
        chestGrid = MakeRect("ChestGrid", p); Place(chestGrid, tl, new Vector2(530, -74), new Vector2(ChestCols * S + (ChestCols - 1) * G, VisibleRows * S + (VisibleRows - 1) * G));
        ScrollUpButton = MakeButton("ScrollUp", p, "▲", () => Scroll(-1)); Place(ScrollUpButton, tl, new Vector2(964, -74), new Vector2(28, 30));
        ScrollDownButton = MakeButton("ScrollDown", p, "▼", () => Scroll(1)); Place(ScrollDownButton, tl, new Vector2(964, -252), new Vector2(28, 30));
        ScrollUpButton.GetComponentInChildren<Text>().fontSize = 14; ScrollDownButton.GetComponentInChildren<Text>().fontSize = 14;
        scrollTrack = MakeImage("ScrollTrack", p, Empty).rectTransform; Place(scrollTrack, tl, new Vector2(970, -108), new Vector2(16, 140));
        scrollThumb = MakeImage("ScrollThumb", scrollTrack, Line).rectTransform; Place(scrollThumb, tl, Vector2.zero, new Vector2(16, 80));
        CloseButton = MakeButton("CloseButton", p, "關閉", () => { if (chest) chest.Close(); }); Place(CloseButton, new Vector2(1, 1), new Vector2(-14, -8), new Vector2(84, 30));
        storagePanel.SetActive(false);
    }

    public void ShowStorage(ChestStorage c, PlayerAvatar p)
    {
        chest = c; player = p; selBag = selChest = null; tab = 0; scrollRow = 0;
        storagePanel.SetActive(true); RefreshStorage();
    }
    public void HideStorage() { storagePanel.SetActive(false); chest = null; }
    public bool StorageOpen => storagePanel != null && storagePanel.activeSelf;

    List<ItemStack> ChestView()
    {
        var v = new List<ItemStack>();
        foreach (var s in chest.contents) if (Items.InTab(s.name, tab)) v.Add(s);
        return v;
    }
    int ChestRows(int viewCount) => Mathf.Max(VisibleRows, tab == 0 ? Mathf.CeilToInt(chest.capacity / (float)ChestCols) : Mathf.CeilToInt(viewCount / (float)ChestCols));

    public void RefreshStorage()
    {
        if (!chest) return;
        if (selBag != null && !player.inventory.Contains(selBag)) selBag = null;
        if (selChest != null && !chest.contents.Contains(selChest)) selChest = null;
        // bag: every slot up to capacity
        Clear(bagGrid); bagSlots.Clear();
        for (int i = 0; i < player.bagCapacity; i++)
        {
            var s = i < player.inventory.Count ? player.inventory[i] : null;
            bagSlots.Add((Slot(bagGrid, i % BagCols, i / BagCols, s, s != null && s == selBag, () => { selBag = s; RefreshStorage(); }), s));
        }
        bagHeader.text = $"乾坤袋　{player.inventory.Count}／{player.bagCapacity} 格";
        // chest: filtered view, scrolled by rows
        var view = ChestView();
        int rows = ChestRows(view.Count); scrollRow = Mathf.Clamp(scrollRow, 0, rows - VisibleRows);
        Clear(chestGrid); chestSlots.Clear();
        for (int i = 0; i < VisibleRows * ChestCols; i++)
        {
            int idx = scrollRow * ChestCols + i;
            if (tab == 0 && idx >= chest.capacity) break;
            var s = idx < view.Count ? view[idx] : null;
            chestSlots.Add((Slot(chestGrid, i % ChestCols, i / ChestCols, s, s != null && s == selChest, () => { selChest = s; RefreshStorage(); }), s));
        }
        chestHeader.text = $"箱內　{chest.contents.Count}／{chest.capacity} 格";
        for (int i = 0; i < tabs.Count; i++) tabs[i].GetComponent<Image>().color = i == tab ? new Color(.30f, .48f, .40f, .95f) : BtnOff;
        float frac = VisibleRows / (float)rows, h = scrollTrack.rect.height;
        scrollThumb.sizeDelta = new Vector2(16, h * frac);
        scrollThumb.anchoredPosition = new Vector2(0, -(h - h * frac) * (rows > VisibleRows ? scrollRow / (float)(rows - VisibleRows) : 0f));
        var sel = selChest ?? selBag;
        detail.text = sel == null ? "" : $"{sel.name} ×{sel.count}";
    }

    RectTransform Slot(RectTransform grid, int col, int row, ItemStack s, bool selected, System.Action pick)
    {
        var frame = MakeImage($"Slot_{row}_{col}", grid, selected ? Line : Frame);
        Place(frame.rectTransform, new Vector2(0, 1), new Vector2(col * (S + G), -row * (S + G)), new Vector2(S, S));
        var bg = MakeImage("Bg", frame.transform, s != null ? Row : Empty);
        Fill(bg.rectTransform); bg.rectTransform.offsetMin = new Vector2(3, 3); bg.rectTransform.offsetMax = new Vector2(-3, -3);
        if (s == null) return frame.rectTransform;
        var tex = Icon(s.name);
        if (tex)
        {
            var ri = new GameObject("Icon", typeof(RectTransform)).AddComponent<RawImage>();
            ri.transform.SetParent(bg.transform, false); ri.texture = tex; Fill(ri.rectTransform);
            ri.rectTransform.offsetMin = new Vector2(4, 4); ri.rectTransform.offsetMax = new Vector2(-4, -4);
        }
        else
        {
            var nm = MakeText("Name", bg.transform, Items.BaseName(s.name), 14, TextAnchor.MiddleCenter, Ink); Fill(nm.rectTransform);
        }
        if (s.name.Contains("・"))
        {
            var g = MakeText("Grade", bg.transform, s.name.Substring(s.name.IndexOf('・') + 1), 12, TextAnchor.UpperLeft, Gold);
            Place(g.rectTransform, new Vector2(0, 1), new Vector2(3, -1), new Vector2(40, 16)); g.gameObject.AddComponent<Outline>().effectColor = new Color(0, 0, 0, .9f);
        }
        if (s.count > 1)
        {
            var n = MakeText("Count", bg.transform, "×" + s.count, 15, TextAnchor.LowerRight, Ink);
            Place(n.rectTransform, new Vector2(1, 0), new Vector2(-3, 1), new Vector2(50, 18)); n.gameObject.AddComponent<Outline>().effectColor = new Color(0, 0, 0, .9f);
        }
        frame.gameObject.AddComponent<Button>().onClick.AddListener(() => pick());
        return frame.rectTransform;
    }

    // storage actions (buttons, demo director)
    public RectTransform BagSlot(string name) { foreach (var s in bagSlots) if (s.stack != null && s.stack.name == name) return s.rt; return null; }
    public RectTransform ChestSlot(string name) { foreach (var s in chestSlots) if (s.stack != null && s.stack.name == name) return s.rt; return null; }
    public RectTransform Tab(int i) => i >= 0 && i < tabs.Count ? tabs[i] : null;
    public void SelectBag(string name) { selBag = player.inventory.Find(s => s.name == name); selChest = null; RefreshStorage(); }
    public void SelectChest(string name) { selChest = chest.contents.Find(s => s.name == name); selBag = null; RefreshStorage(); }
    public void SetTab(int i) { tab = i; scrollRow = 0; RefreshStorage(); }
    public void Scroll(int d) { scrollRow += d; RefreshStorage(); }
    public void DoPut() { if (chest && selBag != null) { chest.Put(selBag, player); selBag = null; RefreshStorage(); } }
    public void DoTake() { if (chest && selChest != null) { chest.Take(selChest, player); selChest = null; RefreshStorage(); } }
    public void DoSort() { if (!chest) return; Items.Sort(chest.contents, chest.capacity); selChest = null; Toast("箱裡的東西歸攏好了"); RefreshStorage(); }

    // ================================================================ collection shelf panel
    // Left side, so the shelf stays in view on the right. Pick a piece from the bag, then an empty slot;
    // pick a filled slot, then an empty one to move it, or 拿下 to take it back.
    const int ShelfCols = 2;          // the TI01 cells are two columns by four shelves, numbered row by row from the top left
    GameObject shelfPanel;
    RectTransform shelfBagGrid, shelfGrid;
    Text shelfDetail, shelfCount;
    ShelfDisplay shelfDisplay;
    readonly List<(RectTransform rt, string item)> shelfBagSlots = new List<(RectTransform, string)>();
    readonly List<RectTransform> shelfSlots = new List<RectTransform>();
    string selPiece; int selSlot;
    public RectTransform ShelfTakeButton { get; private set; }
    public RectTransform ShelfCloseButton { get; private set; }

    void BuildShelf()
    {
        var panel = MakeImage("ShelfPanel", transform, Panel);
        shelfPanel = panel.gameObject;
        Place(panel.rectTransform, new Vector2(0, .5f), new Vector2(16, -24), new Vector2(340, 410));
        var p = panel.transform; var tl = new Vector2(0, 1);
        var t = MakeText("Header", p, "收藏架", 22, TextAnchor.MiddleLeft, Ink); Place(t.rectTransform, tl, new Vector2(20, -12), new Vector2(120, 30));
        shelfCount = MakeText("Count", p, "", 17, TextAnchor.MiddleRight, Line); Place(shelfCount.rectTransform, tl, new Vector2(200, -14), new Vector2(120, 26));
        shelfDetail = MakeText("Detail", p, "", 17, TextAnchor.MiddleLeft, Dim); Place(shelfDetail.rectTransform, tl, new Vector2(20, -46), new Vector2(300, 24));
        var b = MakeText("BagHeader", p, "乾坤袋", 17, TextAnchor.MiddleLeft, Line); Place(b.rectTransform, tl, new Vector2(184, -78), new Vector2(136, 22));
        shelfBagGrid = MakeRect("ShelfBagGrid", p); Place(shelfBagGrid, tl, new Vector2(184, -104), new Vector2(2 * S + G, 2 * S + G));
        var s = MakeText("ShelfHeader", p, "架上", 17, TextAnchor.MiddleLeft, Line); Place(s.rectTransform, tl, new Vector2(20, -78), new Vector2(136, 22));
        shelfGrid = MakeRect("ShelfGrid", p); Place(shelfGrid, tl, new Vector2(20, -104), new Vector2(ShelfCols * S + (ShelfCols - 1) * G, 4 * S + 3 * G));
        ShelfTakeButton = MakeButton("ShelfTake", p, "拿下", () => DoShelfTake()); Place(ShelfTakeButton, tl, new Vector2(184, -260), new Vector2(136, 44));
        ShelfCloseButton = MakeButton("ShelfClose", p, "關閉", () => { if (shelfDisplay) shelfDisplay.Close(); }); Place(ShelfCloseButton, tl, new Vector2(184, -314), new Vector2(136, 44));
        shelfPanel.SetActive(false);
    }

    public void ShowShelf(ShelfDisplay d, PlayerAvatar p) { shelfDisplay = d; player = p; selPiece = null; selSlot = 0; shelfPanel.SetActive(true); RefreshShelf(); }
    public void HideShelf() { shelfPanel.SetActive(false); shelfDisplay = null; }
    public bool ShelfOpen => shelfPanel != null && shelfPanel.activeSelf;

    public void RefreshShelf()
    {
        if (!shelfDisplay) return;
        var sh = shelfDisplay.shelf;
        Clear(shelfBagGrid); shelfBagSlots.Clear();
        var pieces = new List<string>();
        foreach (var st in player.inventory) if (Shelf.IsCollectible(st.name) && !pieces.Contains(st.name)) pieces.Add(st.name);
        for (int i = 0; i < 4; i++)
        {
            string n = i < pieces.Count ? pieces[i] : null;
            var stack = n != null ? new ItemStack(n, Items.Count(player.inventory, n)) : null;
            shelfBagSlots.Add((Slot(shelfBagGrid, i % 2, i / 2, stack, n != null && n == selPiece, () => { selPiece = n; selSlot = 0; RefreshShelf(); }), n));
        }
        Clear(shelfGrid); shelfSlots.Clear();
        for (int i = 1; i <= Shelf.Slots; i++)
        {
            int k = i; string item = sh[i];
            var rt = Slot(shelfGrid, (i - 1) % ShelfCols, (i - 1) / ShelfCols, item != null ? new ItemStack(item, 1) : null, selSlot == i, () => DoShelfSlot(k));
            if (item == null) rt.gameObject.AddComponent<Button>().onClick.AddListener(() => DoShelfSlot(k));
            var num = MakeText("No", rt, i.ToString(), 13, TextAnchor.UpperLeft, Dim); Place(num.rectTransform, new Vector2(0, 1), new Vector2(6, -3), new Vector2(20, 16));
            shelfSlots.Add(rt);
        }
        shelfCount.text = $"{sh.Filled}／{Shelf.Slots} 格";
        shelfDetail.text = selPiece != null ? selPiece : selSlot > 0 ? $"第 {selSlot} 格：{sh[selSlot]}" : "";
        ShelfTakeButton.GetComponent<Image>().color = selSlot > 0 ? Btn : BtnOff;
    }

    // shelf actions (buttons, demo director)
    public RectTransform ShelfBagSlot(string name) { foreach (var s in shelfBagSlots) if (s.item == name) return s.rt; return null; }
    public RectTransform ShelfSlot(int slot) => slot >= 1 && slot <= shelfSlots.Count ? shelfSlots[slot - 1] : null;
    public void SelectPiece(string name) { selPiece = name; selSlot = 0; RefreshShelf(); }
    public void DoShelfSlot(int slot)
    {
        if (!shelfDisplay) return;
        var item = shelfDisplay.shelf[slot];
        if (selPiece != null && item == null) { shelfDisplay.Place(slot, selPiece); selPiece = null; }
        else if (selSlot > 0 && item == null) { shelfDisplay.Move(selSlot, slot); selSlot = 0; }
        else if (item != null) { selSlot = selSlot == slot ? 0 : slot; selPiece = null; }
        RefreshShelf();
    }
    public void DoShelfTake() { if (shelfDisplay && selSlot > 0) { shelfDisplay.Take(selSlot); selSlot = 0; RefreshShelf(); } }

    // ================================================================ alchemy panel
    GameObject alcPanel, resultCard;
    Text alcTemp, alcPhase0, alcPhase1, alcCondense, alcBag, alcFast, resTitle, resBody;
    RectTransform gauge, gaugeBand, gaugeNeedle, ph0Fill, ph1Fill, condFill, condMark;
    readonly Dictionary<string, RectTransform> alcButtons = new Dictionary<string, RectTransform>();
    FurnaceFire furnace;
    const float GaugeMax = 110f, GaugeW = 390f;

    void BuildAlchemy()
    {
        var panel = MakeImage("AlchemyPanel", transform, Panel);
        alcPanel = panel.gameObject;
        Place(panel.rectTransform, new Vector2(1, .5f), new Vector2(-16, -28), new Vector2(430, 590));
        var p = panel.transform; var tl = new Vector2(0, 1);
        var t = MakeText("Title", p, "守溫小丹爐", 22, TextAnchor.UpperLeft, Ink); Place(t.rectTransform, tl, new Vector2(20, -14), new Vector2(390, 30));
        alcFast = MakeText("Fast", p, "", 16, TextAnchor.UpperRight, Gold); Place(alcFast.rectTransform, new Vector2(1, 1), new Vector2(-16, -18), new Vector2(140, 24));
        var r = MakeText("Recipe", p, "回春丹方：青靈草二，研末；淨水蓮一，陰乾；水二瓢。\n先水，次淨水蓮，後青靈草。文火十息，中火十二息。", 15, TextAnchor.UpperLeft, Dim);
        Place(r.rectTransform, tl, new Vector2(20, -50), new Vector2(390, 66));

        alcTemp = MakeText("Temp", p, "", 18, TextAnchor.UpperLeft, Ink); Place(alcTemp.rectTransform, tl, new Vector2(20, -124), new Vector2(390, 26));
        gauge = MakeImage("Gauge", p, Empty).rectTransform; Place(gauge, tl, new Vector2(20, -154), new Vector2(GaugeW, 20));
        var scorch = MakeImage("Scorch", gauge, new Color(.75f, .2f, .15f, .7f)).rectTransform;
        Place(scorch, tl, new Vector2(GaugeW * (float)HomeAlchemy.ScorchLine / GaugeMax, 0), new Vector2(GaugeW * (GaugeMax - (float)HomeAlchemy.ScorchLine) / GaugeMax, 20));
        gaugeBand = MakeImage("Band", gauge, new Color(.35f, .7f, .45f, .75f)).rectTransform; Place(gaugeBand, tl, Vector2.zero, new Vector2(10, 20));
        gaugeNeedle = MakeImage("Needle", gauge, Color.white).rectTransform; Place(gaugeNeedle, tl, Vector2.zero, new Vector2(4, 28));
        gaugeNeedle.anchoredPosition = new Vector2(0, 4);

        alcPhase0 = PhaseRow(p, -186, out ph0Fill);
        alcPhase1 = PhaseRow(p, -214, out ph1Fill);
        alcCondense = MakeText("Condense", p, "", 16, TextAnchor.UpperLeft, Dim); Place(alcCondense.rectTransform, tl, new Vector2(20, -242), new Vector2(390, 22));
        var cb = MakeImage("CondBar", p, Empty).rectTransform; Place(cb, tl, new Vector2(20, -266), new Vector2(GaugeW, 10));
        condFill = MakeImage("Fill", cb, new Color(1, 1, 1, .25f)).rectTransform; Place(condFill, tl, Vector2.zero, new Vector2(0, 10));
        condMark = MakeImage("Mark", cb, Gold).rectTransform; Place(condMark, tl, Vector2.zero, new Vector2(4, 16)); condMark.anchoredPosition = new Vector2(0, 3);

        var defs = new (string key, string label, UnityEngine.Events.UnityAction a)[]
        {
            ("lid", "掀蓋", () => furnace.ToggleLid()), ("water", "注水一瓢", () => furnace.AddWater()),
            ("minor", "投淨水蓮", () => furnace.Charge(HomeAlchemy.Minor)), ("lead", "投青靈草", () => furnace.Charge(HomeAlchemy.Lead)),
            ("fuel", "添柴", () => furnace.AddFuel()), ("ignite", "點火", () => furnace.Ignite()),
            ("ventDown", "風門 －", () => furnace.Vent(-1)), ("ventUp", "風門 ＋", () => furnace.Vent(1)),
            ("condense", "收丹", () => furnace.Condense()), ("exit", "離開", () => { if (furnace.Condensed && !furnace.claimed) furnace.Claim(); else furnace.Leave(); }),
        };
        for (int i = 0; i < defs.Length; i++)
        {
            var b = MakeButton("Alc_" + defs[i].key, p, defs[i].label, defs[i].a);
            Place(b, tl, new Vector2(20 + (i % 2) * 199, -290 - (i / 2) * 48), new Vector2(191, 40));
            alcButtons[defs[i].key] = b;
        }
        alcBag = MakeText("Bag", p, "", 15, TextAnchor.UpperLeft, Dim); Place(alcBag.rectTransform, tl, new Vector2(20, -536), new Vector2(390, 44));
        alcPanel.SetActive(false);

        // result card on the left, beside the furnace
        var card = MakeImage("ResultCard", transform, new Color(.08f, .09f, .08f, .92f));
        resultCard = card.gameObject;
        Place(card.rectTransform, new Vector2(0, .5f), new Vector2(28, -150), new Vector2(420, 236));
        card.gameObject.AddComponent<Outline>().effectColor = new Color(Gold.r, Gold.g, Gold.b, .6f);
        resTitle = MakeText("ResTitle", card.transform, "", 30, TextAnchor.UpperLeft, Gold); Place(resTitle.rectTransform, tl, new Vector2(20, -14), new Vector2(380, 40));
        resBody = MakeText("ResBody", card.transform, "", 16, TextAnchor.UpperLeft, Ink); Place(resBody.rectTransform, tl, new Vector2(20, -62), new Vector2(380, 170));
        resultCard.SetActive(false);
    }

    Text PhaseRow(Transform p, float y, out RectTransform fill)
    {
        var tl = new Vector2(0, 1);
        var t = MakeText("Phase", p, "", 16, TextAnchor.UpperLeft, Dim); Place(t.rectTransform, tl, new Vector2(20, y), new Vector2(200, 22));
        var bar = MakeImage("PhaseBar", p, Empty).rectTransform; Place(bar, tl, new Vector2(300, y - 4), new Vector2(110, 14));
        fill = MakeImage("Fill", bar, Line).rectTransform; Place(fill, tl, Vector2.zero, new Vector2(0, 14));
        return t;
    }

    public void ShowAlchemy(FurnaceFire f, PlayerAvatar p) { furnace = f; player = p; alcPanel.SetActive(true); RefreshAlchemy(); }
    public void HideAlchemy() { alcPanel.SetActive(false); resultCard.SetActive(false); furnace = null; }
    public bool AlchemyOpen => alcPanel != null && alcPanel.activeSelf && furnace != null;
    public RectTransform AlchemyButton(string key) => alcButtons.TryGetValue(key, out var b) ? b : null;

    void RefreshAlchemy()
    {
        var f = furnace.sim;
        alcTemp.text = $"爐溫 {f.T:0}°　燃柴 {f.Burning}{(f.Loaded > 0 ? $"（待點 {f.Loaded}）" : "")}　風門 {f.Vent * 100:0}%　{(f.LidClosed ? "爐蓋合" : "爐蓋開")}";
        alcFast.text = furnace.speed > 1.01f ? $"▶▶ 快轉 ×{furnace.speed:0}" : "";
        int ph = Mathf.Min(f.PhaseIndex, HomeAlchemy.Phases.Length - 1);
        var band = HomeAlchemy.Phases[ph];
        gaugeBand.anchoredPosition = new Vector2(GaugeW * (float)band.low / GaugeMax, 0);
        gaugeBand.sizeDelta = new Vector2(GaugeW * (float)(band.high - band.low) / GaugeMax, 20);
        gaugeBand.gameObject.SetActive(f.PhaseIndex < HomeAlchemy.Phases.Length);
        gaugeNeedle.anchoredPosition = new Vector2(Mathf.Clamp(GaugeW * (float)f.T / GaugeMax, 0, GaugeW) - 2, 4);
        bool inside = f.PhaseIndex < HomeAlchemy.Phases.Length && f.T >= band.low && f.T <= band.high;
        gaugeNeedle.GetComponent<Image>().color = f.T > HomeAlchemy.ScorchLine ? Bad : inside ? Color.white : Gold;
        PhaseText(alcPhase0, ph0Fill, f, 0); PhaseText(alcPhase1, ph1Fill, f, 1);

        double d = f.SinceComplete;
        if (d < 0) { alcCondense.text = "爐裡只有藥湯的苦味"; alcCondense.color = Dim; }
        else if (furnace.Condensed) { alcCondense.text = "丹已收起"; alcCondense.color = Ink; }
        else if (d < HomeAlchemy.CondenseBest0) { alcCondense.text = "一縷淡淡的丹香飄出爐口"; alcCondense.color = Ink; }
        else if (d <= HomeAlchemy.CondenseBest1) { alcCondense.text = "丹香正濃，爐蓋輕輕顫動"; alcCondense.color = Gold; }
        else { alcCondense.text = "香氣裡透出一絲焦味"; alcCondense.color = Bad; }
        float dd = Mathf.Clamp((float)System.Math.Max(0, d), 0, (float)HomeAlchemy.Overcook);
        condFill.sizeDelta = new Vector2(GaugeW * dd / (float)HomeAlchemy.Overcook, 10);
        condMark.anchoredPosition = new Vector2(GaugeW * dd / (float)HomeAlchemy.Overcook - 2, 3);

        Label("lid", f.LidClosed ? "掀開爐蓋" : "合上爐蓋", true);
        Label("water", $"注水一瓢（{f.WaterAdded}／{HomeAlchemy.Water}）", !f.LidClosed);
        Label("minor", f.IsCharged(HomeAlchemy.Minor) ? "淨水蓮 ✓" : "投淨水蓮 ×1", !f.LidClosed && !f.IsCharged(HomeAlchemy.Minor));
        Label("lead", f.IsCharged(HomeAlchemy.Lead) ? "青靈草 ✓" : "投青靈草 ×2", !f.LidClosed && !f.IsCharged(HomeAlchemy.Lead));
        Label("fuel", "添一根松柴", furnace.BagCount(HomeAlchemy.Fuel) + furnace.ChestCount(HomeAlchemy.Fuel) > 0);
        Label("ignite", "點火", f.Loaded > 0);
        Label("ventDown", "風門 －", f.Vent > 0); Label("ventUp", "風門 ＋", f.Vent < 1);
        Label("condense", "收丹", furnace.Batching && !furnace.Condensed);
        Label("exit", furnace.Condensed && !furnace.claimed ? "裝瓶收下" : "離開", true);
        string Have(string n) { int c = furnace.ChestCount(n); return $"{n} ×{furnace.BagCount(n)}" + (c > 0 ? $"（箱 +{c}）" : ""); }
        alcBag.text = $"乾坤袋：{Have(HomeAlchemy.Lead)}　{Have(HomeAlchemy.Minor)}\n{Have(HomeAlchemy.Fuel)}";

        var o = furnace.outcome;
        resultCard.SetActive(o != null && !furnace.claimed);
        if (o != null)
        {
            resTitle.text = o.success ? $"{HomeAlchemy.Recipe}・{o.label}" : "沒有成丹";
            resTitle.color = o.success ? Gold : Bad;
            resBody.text = (o.reasons.Count > 0 ? string.Join("\n", o.reasons) : "丹體圓潤，透著溫溫的光。") +
                "\n\n（展示用：品階只在本場景，不入正式存檔）";
        }
    }

    static void PhaseText(Text t, RectTransform fill, HomeAlchemy.Furnace f, int i)
    {
        var p = HomeAlchemy.Phases[i];
        double prog = f.Progress[i];
        bool done = f.PhaseIndex > i, cur = f.PhaseIndex == i;
        t.text = $"{(done ? "✓" : cur ? "▶" : "・")} {p.label} {p.low:0}–{p.high:0}°  {prog:0.0}/{p.seconds:0}";
        t.color = done ? Line : cur ? Ink : Dim;
        fill.sizeDelta = new Vector2(110f * (float)System.Math.Min(1, prog / p.seconds), 14);
    }

    void Label(string key, string s, bool enabled)
    {
        var b = alcButtons[key];
        b.GetComponentInChildren<Text>().text = s;
        b.GetComponent<Image>().color = enabled ? Btn : BtnOff;
        b.GetComponentInChildren<Text>().color = enabled ? Ink : Dim;
    }

    // ================================================================ icons & builders
    /// Item thumbnails rendered by SceneBuilder (base name -> texture).
    public string[] iconNames;
    public Texture2D[] icons;
    Texture2D Icon(string item)
    {
        if (iconNames == null) return null;
        int i = System.Array.IndexOf(iconNames, Items.BaseName(item));
        return i >= 0 && i < icons.Length ? icons[i] : null;
    }

    // ================================================================ touch overlay (hidden until a touch is seen)
    void BuildTouch()
    {
        var ring = MakeImage("TouchStick", transform, new Color(1, 1, 1, .12f)).rectTransform;
        Place(ring, Vector2.zero, Vector2.zero, new Vector2(140, 140)); ring.pivot = new Vector2(.5f, .5f);
        ring.gameObject.AddComponent<Outline>().effectColor = new Color(1, 1, 1, .35f);
        var knob = MakeImage("Knob", ring, new Color(1, 1, 1, .45f)).rectTransform;
        Place(knob, new Vector2(.5f, .5f), Vector2.zero, new Vector2(56, 56));
        var act = MakeButton("TouchInteract", transform, "", () => { });
        Place(act, new Vector2(1, 0), new Vector2(-40, 150), new Vector2(150, 64));
        var tc = GetComponent<TouchControls>();
        if (!tc) tc = gameObject.AddComponent<TouchControls>();
        tc.Build(ring, knob, act);
    }

    static void Clear(RectTransform rt) { for (int i = rt.childCount - 1; i >= 0; i--) DestroyImmediate(rt.GetChild(i).gameObject); }

    RectTransform MakeButton(string name, Transform parent, string label, UnityEngine.Events.UnityAction onClick)
    {
        var img = MakeImage(name, parent, Btn);
        Place(img.rectTransform, new Vector2(.5f, .5f), Vector2.zero, new Vector2(120, 44));
        var b = img.gameObject.AddComponent<Button>(); b.onClick.AddListener(onClick);
        var tx = MakeText("Label", img.transform, label, 19, TextAnchor.MiddleCenter, Ink); Fill(tx.rectTransform);
        return img.rectTransform;
    }

    static RectTransform MakeRect(string name, Transform parent)
    {
        var go = new GameObject(name, typeof(RectTransform)); go.transform.SetParent(parent, false);
        return (RectTransform)go.transform;
    }

    static Image MakeImage(string name, Transform parent, Color c)
    {
        var rt = MakeRect(name, parent); var img = rt.gameObject.AddComponent<Image>(); img.color = c; return img;
    }

    static Text MakeText(string name, Transform parent, string s, int size, TextAnchor anchor, Color c)
    {
        var rt = MakeRect(name, parent); var t = rt.gameObject.AddComponent<Text>();
        t.font = GetFont(); t.fontSize = size; t.alignment = anchor; t.color = c; t.text = s;
        t.horizontalOverflow = HorizontalWrapMode.Overflow; t.verticalOverflow = VerticalWrapMode.Overflow;
        return t;
    }

    /// Anchor + pivot at the same corner, then position/size in canvas units.
    static void Place(RectTransform rt, Vector2 anchor, Vector2 pos, Vector2 size)
    {
        rt.anchorMin = rt.anchorMax = anchor; rt.pivot = anchor;
        rt.anchoredPosition = pos; rt.sizeDelta = size;
    }

    static void Fill(RectTransform rt) { rt.anchorMin = Vector2.zero; rt.anchorMax = Vector2.one; rt.offsetMin = rt.offsetMax = Vector2.zero; }
}
