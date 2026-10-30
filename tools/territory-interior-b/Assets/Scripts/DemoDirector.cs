using System;
using System.Collections.Generic;
using UnityEngine;

/// Scripted walkthrough that drives the same interaction code a player uses
/// (walk, E prompts, chest panel clicks, adding wood, lamp toggle, lying on the bed).
/// Time is stepped explicitly so the recorder can render frame by frame; tick autoPlay to watch it in play mode.
public class DemoDirector : MonoBehaviour
{
    public static bool Driving;

    public bool autoPlay;
    public PlayerAvatar player;
    public ChestStorage chest;
    public FurnaceFire furnace;
    public PaperLamp lamp;
    public BedRest bed;
    public InteriorUI ui;
    public CameraRig rig;
    public Interactable[] interactables;
    public Light sun;
    public ShelfDisplay shelf;
    public PaperLamp sideLamp;      // TI_Lamp_1 by the bed, lit when night falls
    public JournalDesk journal;
    public Color dayAmbient = new Color(.36f, .33f, .30f), nightAmbient = new Color(.13f, .14f, .19f);
    public float daySun = .85f, nightSun = .14f;

    class Act { public Action begin; public Func<float, bool> step; }
    readonly List<Act> acts = new List<Act>();
    int index; bool begun;
    public float Time { get; private set; }
    public bool Finished => index >= acts.Count;
    float night;            // 0 = dusk, 1 = night
    Vector2 cursorPos = new Vector2(900, 300);

    void Start() { if (autoPlay) BeginDemo(); }
    void Update() { if (autoPlay && Driving && !Finished) Step(UnityEngine.Time.deltaTime); }
    void OnDisable() { Driving = false; }

    public void BeginDemo()
    {
        Driving = true; acts.Clear(); index = 0; begun = false; Time = 0f;
        if (shelf) shelf.Fill();
        Script();
        SetNight(0f);
    }

    public void Step(float dt)
    {
        Time += dt;
        float frameDt = dt;
        while (!Finished)
        {
            var a = acts[index];
            if (!begun) { a.begin?.Invoke(); begun = true; }
            if (a.step == null || a.step(dt)) { index++; begun = false; dt = 0f; continue; }
            break;
        }
        LateTick(frameDt);
        player.Tick(frameDt);
        foreach (var it in interactables) it.Tick(frameDt);
        if (sideLamp) sideLamp.Tick(frameDt);
        ui.Tick(frameDt);
        ui.SetStatus(PlayerController.StatusLine(interactables));
        rig.Tick(frameDt);
        if (Finished) Driving = false;
    }

    // ---------------------------------------------------------------- the walkthrough
    void Script()
    {
        Do(() => { Overview(); ui.SetCaption("領地小屋的家具照工作單格位擺好；鏡頭在角色背後跟隨（滑鼠轉視角、遇牆自動拉近）"); });
        Wait(2.8f);
        Do(() => { Follow(); ui.SetCaption("① 走到儲物箱（背後跟隨鏡頭）"); });
        Walk(new Vector3(.6f, 0, .2f), new Vector3(2.0f, 0, .75f), new Vector3(2.95f, 0, .8f));
        Face(new Vector3(-.35f, 0, 1f));
        Press(chest);
        Do(() => ui.SetCaption("② 箱子：同種疊放、分類分頁、可捲動、一鍵整理"));
        Wait(1.0f);
        CursorTo(() => ui.BagSlot("青瓷罐"), .7f); Click(() => ui.SelectBag("青瓷罐")); Wait(.35f);
        CursorTo(() => ui.PutButton, .55f); Click(() => ui.DoPut()); Wait(1.1f);
        CursorTo(() => ui.Tab(4), .6f); Click(() => ui.SetTab(4)); Wait(.6f);
        CursorTo(() => ui.ChestSlot("藥罐"), .55f); Click(() => ui.SelectChest("藥罐")); Wait(.35f);
        CursorTo(() => ui.TakeButton, .55f); Click(() => ui.DoTake()); Wait(1.1f);
        CursorTo(() => ui.Tab(0), .6f); Click(() => ui.SetTab(0)); Wait(.4f);
        CursorTo(() => ui.SortButton, .6f); Click(() => ui.DoSort()); Wait(1.2f);
        CursorTo(() => ui.ScrollDownButton, .6f); Click(() => ui.Scroll(1)); Wait(.6f); Click(() => ui.Scroll(1)); Wait(.8f);
        CursorTo(() => ui.ScrollUpButton, .5f); Click(() => ui.Scroll(-2)); Wait(.5f);
        CursorTo(() => ui.CloseButton, .6f); Click(() => chest.Close()); Wait(.3f);
        Do(() => ui.SetCursor(false, cursorPos)); Wait(.6f);

        Do(() => { Follow(); ui.SetCaption("③ 收藏架：從乾坤袋選一件擺上去，也能換格、拿下"); });
        Walk(new Vector3(2.35f, 0, .45f));
        Face(new Vector3(1f, 0, -.45f));
        Press(shelf);
        Wait(1.0f);
        CursorTo(() => ui.ShelfBagSlot("卷軸"), .7f); Click(() => ui.SelectPiece("卷軸")); Wait(.35f);
        CursorTo(() => ui.ShelfSlot(4), .55f); Click(() => ui.DoShelfSlot(4)); Wait(1.1f);
        CursorTo(() => ui.ShelfBagSlot("藥罐"), .6f); Click(() => ui.SelectPiece("藥罐")); Wait(.35f);
        CursorTo(() => ui.ShelfSlot(6), .55f); Click(() => ui.DoShelfSlot(6)); Wait(1.1f);
        CursorTo(() => ui.ShelfSlot(6), .4f); Click(() => ui.DoShelfSlot(6)); Wait(.35f);
        CursorTo(() => ui.ShelfSlot(3), .55f); Click(() => ui.DoShelfSlot(3)); Wait(1.1f);
        CursorTo(() => ui.ShelfSlot(2), .55f); Click(() => ui.DoShelfSlot(2)); Wait(.35f);
        CursorTo(() => ui.ShelfTakeButton, .55f); Click(() => ui.DoShelfTake()); Wait(1.2f);
        CursorTo(() => ui.ShelfCloseButton, .6f); Click(() => shelf.Close()); Wait(.3f);
        Do(() => ui.SetCursor(false, cursorPos)); Wait(.5f);

        Do(() => { Follow(); ui.SetCaption("④ 丹爐煉回春丹：材料取自乾坤袋"); });
        Walk(new Vector3(1.9f, 0, -.3f), new Vector3(2.2f, 0, -1.2f));
        Face(new Vector3(.5f, 0, -.7f));
        Press(furnace);
        Wait(1.0f);
        foreach (var k in new[] { "lid", "water", "water", "minor", "lead", "fuel", "ignite", "ventDown", "ventDown", "lid" }) Alc(k, .5f);
        Do(() => ui.SetCaption("④ 文火溫藥：一根柴、風門全關，爐溫守住火候"));
        Do(() => furnace.speed = 3f);
        WaitUntil(() => furnace.sim.PhaseIndex >= 1, 30f);
        Do(() => { furnace.speed = 1f; ui.SetCaption("④ 中火融藥：添柴、開風門，柴快燒完要補"); });
        Alc("fuel", .5f); Alc("ventUp", .5f);
        Do(() => furnace.speed = 3f);
        WaitUntil(() => furnace.sim.PhaseIndex >= 2 || furnace.sim.Burning < 2, 40f);
        Do(() => furnace.speed = 1f);
        AlcIf(() => furnace.sim.PhaseIndex < 2, "fuel", .5f);
        Do(() => furnace.speed = 3f);
        WaitUntil(() => furnace.sim.PhaseIndex >= 2, 40f);
        Do(() => { furnace.speed = 1f; ui.SetCaption("④ 丹香已起：丹香正濃時收丹"); });
        WaitUntil(() => furnace.sim.SinceComplete >= 3.4, 10f);
        Alc("condense", .3f);
        Wait(3.2f);
        Alc("exit", .3f);   // 裝瓶收下
        Wait(1.4f);
        Alc("exit", .3f);   // 離開
        Do(() => ui.SetCursor(false, cursorPos)); Wait(.5f);

        Do(() => { Follow(); ui.SetCaption("⑤ 開燈、關燈（天色轉暗）"); });
        Fade(1f, 2.2f);
        Do(() => { if (sideLamp) sideLamp.on = true; });
        Walk(new Vector3(1.6f, 0, -1.0f), new Vector3(1.0f, 0, -1.5f));
        Face(new Vector3(.45f, 0, -.6f));
        Press(lamp); Wait(1.3f);
        Press(lamp); Wait(1.1f);
        Press(lamp); Wait(1.3f);

        Do(() => { Follow(); ui.SetCaption("⑥ 書案上的旅途手札：翻開、翻頁、合上"); });
        Walk(new Vector3(-.4f, 0, -.9f), new Vector3(-1.75f, 0, -.85f));
        Face(new Vector3(-1f, 0, -.6f));
        Press(journal);
        WaitUntil(() => journal.book != null && journal.book.State == Journal.Phase.Open, 4f);
        Wait(.6f);
        Page(() => ui.JournalNextButton, () => journal.Next());
        Page(() => ui.JournalNextButton, () => journal.Next());
        Page(() => ui.JournalPrevButton, () => journal.Prev());
        CursorTo(() => ui.JournalCloseButton, .5f); Click(() => journal.Close());
        WaitUntil(() => !journal.isOpen, 3f);
        Do(() => ui.SetCursor(false, cursorPos)); Wait(.5f);

        Do(() => { Follow(); ui.SetCaption("⑦ 回床上休息：躺下後蓋好被子，頭露在外面"); });
        Walk(new Vector3(.05f, 0, -.4f), new Vector3(.05f, 0, .95f), new Vector3(-1.75f, 0, 1.0f));
        Face(Vector3.left);
        Press(bed, "[E] 躺下休息"); Wait(4.6f);
        Press(bed, "[E] 起身"); Wait(2.7f);
        Do(() => { Overview(); ui.SetCaption("測試完成：箱子疊放／分類／整理、收藏架擺放／換格／拿下、乾坤袋材料煉丹、開關燈、翻手札、躺床蓋被"); });
        Wait(2.6f);
    }

    // ---------------------------------------------------------------- act builders
    void Do(Action a) => acts.Add(new Act { begin = a });
    void Wait(float d) { float t = 0; acts.Add(new Act { begin = () => t = 0, step = dt => (t += dt) >= d }); }

    void Walk(params Vector3[] pts)
    {
        foreach (var p in pts)
        {
            var target = p;
            acts.Add(new Act
            {
                begin = () => ui.SetPrompt(""),
                step = dt =>
                {
                    Vector3 d = target - player.transform.position; d.y = 0;
                    float step = player.walkSpeed * dt;
                    if (d.magnitude <= step + 1e-4f) { if (step > 0f) player.Move(d / step, dt); return true; }
                    player.Move(d / Mathf.Max(d.magnitude, 1e-4f), dt);
                    return false;
                }
            });
        }
    }

    void Face(Vector3 dir)
    {
        float t = 0;
        acts.Add(new Act { begin = () => t = 0, step = dt => { player.Face(dir, dt); return (t += dt) >= .45f; } });
    }

    /// Show the item's own prompt, then press E (calls the same Interact a player would).
    void Press(Interactable it, string promptOverride = null)
    {
        float t = 0;
        acts.Add(new Act
        {
            begin = () => { t = 0; ui.SetPrompt(promptOverride ?? it.Prompt); },
            step = dt => (t += dt) >= .9f
        });
        Do(() => { it.Interact(player); ui.SetPrompt(""); });
    }

    void CursorTo(Func<RectTransform> target, float d)
    {
        float t = 0; Vector2 from = Vector2.zero, to = Vector2.zero;
        acts.Add(new Act
        {
            begin = () => { t = 0; from = cursorPos; var rt = target(); to = rt ? ui.CanvasPos(rt) + new Vector2(-6, -4) : from; },
            step = dt =>
            {
                t += dt; float s = Mathf.SmoothStep(0, 1, Mathf.Clamp01(t / d));
                cursorPos = Vector2.Lerp(from, to, s); ui.SetCursor(true, cursorPos);
                return t >= d;
            }
        });
    }

    void Click(Action a) => Do(() => { ui.Click(); a(); });

    /// Starts a dusk-to-night fade that runs alongside the following acts.
    void Fade(float to, float d) => Do(() => { fadeFrom = night; fadeTo = to; fadeDur = d; fadeT = 0; });
    float fadeFrom = -1, fadeTo, fadeDur, fadeT;

    void SetNight(float n)
    {
        night = n;
        RenderSettings.ambientLight = Color.Lerp(dayAmbient, nightAmbient, n);
        if (sun) sun.intensity = Mathf.Lerp(daySun, nightSun, n);
    }

    void LateTick(float dt)
    {
        if (fadeFrom < 0) return;
        fadeT += dt; SetNight(Mathf.Lerp(fadeFrom, fadeTo, Mathf.Clamp01(fadeT / fadeDur)));
        if (fadeT >= fadeDur) fadeFrom = -1;
    }

    /// Shoulder follow (the rig still hands over to an item's close-up while it holds the camera).
    void Follow() { rig.useOverride = false; rig.autoBehind = true; rig.distance = 2.2f; rig.pitch = 16f; }
    /// Wide establishing shot from the front-left corner, inside the closed room.
    void Overview() { rig.useOverride = true; rig.focusOverride = new Vector3(.2f, .7f, .4f); rig.targetDistance = 3.6f; rig.targetYaw = 38f; rig.targetPitch = 30f; rig.targetFov = 64f; }

    /// Move the demo cursor to a furnace-panel button and press it.
    void Alc(string key, float after)
    {
        CursorTo(() => ui.AlchemyButton(key), .45f);
        Click(() => ui.AlchemyButton(key).GetComponent<UnityEngine.UI.Button>().onClick.Invoke());
        Wait(after);
    }
    void AlcIf(Func<bool> cond, string key, float after)
    {
        bool go = false;
        Do(() => go = cond());
        CursorTo(() => go ? ui.AlchemyButton(key) : null, .45f);
        Do(() => { if (go) { ui.Click(); ui.AlchemyButton(key).GetComponent<UnityEngine.UI.Button>().onClick.Invoke(); } });
        Wait(after);
    }
    /// Click a journal page button and let the leaf finish turning.
    void Page(Func<RectTransform> button, Action turn)
    {
        CursorTo(button, .45f); Click(turn);
        WaitUntil(() => journal.book.State == Journal.Phase.Open, 2f);
        Wait(.7f);
    }
    void WaitUntil(Func<bool> cond, float timeout) { float t = 0; acts.Add(new Act { begin = () => t = 0, step = dt => cond() || (t += dt) >= timeout }); }
}
