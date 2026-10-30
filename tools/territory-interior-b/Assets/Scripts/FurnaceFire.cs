using System.Collections.Generic;
using UnityEngine;

/// Home furnace (TI02) as a small alchemy station, following Alchemy V2:
/// open lid → water ×2 → 淨水蓮 → 青靈草 → load firewood → ignite → close lid → hold each fire band → condense in the window.
/// The furnace physics run in fixed 0.1 s ticks (HomeAlchemy.Furnace); fire mesh, emission and light follow its temperature.
public class FurnaceFire : Interactable
{
    public GameObject[] fireObjects;            // TI02 *_Fire_LODn meshes
    public Material[] emissiveMats;
    public Light fireLight;
    public Transform mouth;                     // SOCKET_fire_light
    public Vector3 mouthOutward = Vector3.forward;
    public Transform[] lidParts;                // TI02 *_Lid_LODn, lifted aside while open
    public Vector3 lidOpenOffset = new Vector3(0f, .16f, 0f);
    public Vector3 lidTiltAxis = Vector3.right;
    public GameObject logPrefab, waterPrefab, herbPrefab, pillPrefab;
    public Color emitColor = new Color(1f, .45f, .12f);
    public float speed = 1f;                    // furnace-time multiplier (demo fast-forward / hold F in play)

    public HomeAlchemy.Furnace sim = new HomeAlchemy.Furnace();
    public HomeAlchemy.Outcome outcome;         // set when the batch is condensed
    public bool panelOpen, claimed;
    PlayerAvatar user;
    float time, lidT, acc;
    Vector3[] lidHome; Quaternion[] lidHomeRot;

    class Flyer { public GameObject go; public Vector3 a, b; public float t, dur, arc; public bool keep; }
    readonly List<Flyer> flyers = new List<Flyer>();

    public override string Prompt => panelOpen ? "" : "[E] 守爐煉丹";
    public override bool HoldsCamera => panelOpen;
    public bool Batching => sim.OrderLog.Count > 0 && !claimed;
    public bool Condensed => sim.CondenseTick != null;

    public override void Interact(PlayerAvatar player)
    {
        if (panelOpen) return;
        user = player; panelOpen = true;
        if (InteriorUI.Instance) InteriorUI.Instance.ShowAlchemy(this, player);
    }

    public void Leave()
    {
        panelOpen = false; speed = 1f;
        if (InteriorUI.Instance) InteriorUI.Instance.HideAlchemy();
    }

    // ---------------------------------------------------------------- actions (buttons)
    static void Toast(string s) { if (InteriorUI.Instance) InteriorUI.Instance.Toast(s); }
    Vector3 Top => mouth.position + Vector3.up * .45f;
    Vector3 Hand => user.transform.position + Vector3.up * .85f + user.transform.forward * .25f;

    /// Materials come from the player's bag first; with usePantry, a shortfall is topped up from the room's chest.
    public ChestStorage pantryChest;
    public bool usePantry = true;
    bool pantry => usePantry && pantryChest != null;
    public int BagCount(string item) => Items.Count(user.inventory, item);
    public int ChestCount(string item) => pantry ? Items.Count(pantryChest.contents, item) : 0;
    int Available(string item) => BagCount(item) + ChestCount(item);
    int Consume(string item, int n)
    {
        int fromBag = Items.Remove(user.inventory, item, n);
        return pantry && fromBag < n ? Items.Remove(pantryChest.contents, item, n - fromBag) : 0;
    }

    void NewBatchIfDone() { if (claimed || Condensed) { sim = sim.Next(); outcome = null; claimed = false; } }

    public void ToggleLid()
    {
        sim.Lid(!sim.LidClosed);
        Toast(sim.LidClosed ? "爐蓋合上，悶悶一聲" : "掀開爐蓋，熱氣撲面");
    }

    public void AddWater()
    {
        NewBatchIfDone();
        if (sim.LidClosed) { Toast("爐蓋還合著"); return; }
        sim.Water(); Fly(waterPrefab, Hand, Top - Vector3.up * .3f, .7f, .25f);
        Toast("嘩——一瓢清水倒進爐裡");
    }

    public void Charge(string herb)
    {
        NewBatchIfDone();
        int need = herb == HomeAlchemy.Lead ? HomeAlchemy.LeadQty : HomeAlchemy.MinorQty;
        if (sim.LidClosed) { Toast("爐蓋還合著"); return; }
        if (sim.IsCharged(herb)) { Toast($"爐裡已經有{herb}了"); return; }
        if (Available(herb) < need) { Toast($"{herb}不夠了"); return; }
        int fromChest = Consume(herb, need);
        sim.Charge(herb); Fly(herbPrefab, Hand, Top - Vector3.up * .3f, .8f, .3f);
        Toast(fromChest > 0 ? $"乾坤袋裡不夠，從箱裡抓了{herb}投進去" : $"{herb}落進爐中，沙沙作響");
    }

    public void AddFuel()
    {
        if (Available(HomeAlchemy.Fuel) < 1) { Toast("沒有松柴了"); return; }
        if (sim.Burning >= HomeAlchemy.MaxBurning) { Toast("爐膛塞滿了"); return; }
        Consume(HomeAlchemy.Fuel, 1);
        sim.AddFuel();
        Fly(logPrefab, mouth.position + mouthOutward * .55f + Vector3.up * .45f, mouth.position - Vector3.up * .05f, .9f, .12f, true);
        Toast(sim.Ignited ? "添了一根柴，火舌竄高" : "松柴架進爐膛");
    }

    public void Ignite()
    {
        if (sim.Loaded == 0) { Toast(sim.Ignited ? "火正旺" : "爐膛裡沒有柴"); return; }
        sim.Ignite(); Toast("嚓——火點著了");
    }

    public void Vent(int dir)
    {
        double v = System.Math.Round(System.Math.Max(0, System.Math.Min(1, sim.Vent + .25 * dir)), 2);
        sim.SetVent(v); Toast(dir > 0 ? "風門推開，呼呼進風" : "風門拉上，火聲低了");
    }

    public void Condense()
    {
        if (Condensed || sim.OrderLog.Count == 0) return;
        sim.Condense();
        outcome = HomeAlchemy.Judge(sim);
        if (outcome.success) Fly(pillPrefab, Top, Hand, 1.1f, .35f);
        Toast(outcome.success ? "一顆丹藥滾出爐口" : "爐裡只剩焦黑的渣");
    }

    /// Bottle the pill into the bag (or clear the failed batch).
    public void Claim()
    {
        if (!Condensed || claimed) return;
        claimed = true;
        if (outcome.success)
        {
            string n = $"{HomeAlchemy.Recipe}・{outcome.label}";
            Items.Add(user.inventory, n, 1, user.bagCapacity);
            Toast($"「{n}」裝進瓶裡，收入乾坤袋");
        }
        else Items.Add(user.inventory, "丹渣", 1, user.bagCapacity);
    }

    // ---------------------------------------------------------------- ticking
    void Fly(GameObject prefab, Vector3 a, Vector3 b, float dur, float arc, bool log = false)
    {
        if (!prefab) return;
        var go = Instantiate(prefab); go.SetActive(true); go.name = prefab.name + "_Flying";
        go.transform.position = a;
        if (log) go.transform.rotation = Quaternion.LookRotation(mouthOutward) * Quaternion.Euler(90f, 0f, 0f);
        flyers.Add(new Flyer { go = go, a = a, b = b, dur = dur, arc = arc });
    }

    public override void Tick(float dt)
    {
        time += dt;
        acc += dt * speed;
        while (acc >= (float)HomeAlchemy.Step) { acc -= (float)HomeAlchemy.Step; sim.StepTick(); }

        for (int i = flyers.Count - 1; i >= 0; i--)
        {
            var f = flyers[i]; f.t += dt / f.dur; float s = Mathf.Clamp01(f.t);
            f.go.transform.position = Vector3.Lerp(f.a, f.b, s) + Vector3.up * Mathf.Sin(s * Mathf.PI) * f.arc;
            f.go.transform.Rotate(0f, 0f, dt * 60f, Space.Self);
            if (f.t >= 1f) { DestroyImmediate(f.go); flyers.RemoveAt(i); }
        }

        // lid: lift and tip aside while open
        if (lidParts != null && lidParts.Length > 0)
        {
            if (lidHome == null)
            {
                lidHome = new Vector3[lidParts.Length]; lidHomeRot = new Quaternion[lidParts.Length];
                for (int i = 0; i < lidParts.Length; i++) { lidHome[i] = lidParts[i].position; lidHomeRot[i] = lidParts[i].rotation; }
            }
            lidT = Mathf.MoveTowards(lidT, sim.LidClosed ? 0f : 1f, dt / .45f);
            float s = lidT * lidT * (3f - 2f * lidT);
            for (int i = 0; i < lidParts.Length; i++)
            {
                lidParts[i].position = lidHome[i] + lidOpenOffset * s;
                lidParts[i].rotation = Quaternion.AngleAxis(-28f * s, lidTiltAxis) * lidHomeRot[i];
            }
        }

        float heat = Mathf.Clamp01(((float)sim.T - 15f) / 70f);
        bool on = sim.Burning > 0;
        foreach (var f in fireObjects) if (f && f.activeSelf != on) f.SetActive(on);
        float flick = .82f + .36f * Mathf.PerlinNoise(time * 6.5f, .3f);
        float level = on ? .35f + .9f * heat + .08f * sim.Burning : heat * .3f;
        if (fireLight) { fireLight.enabled = level > .02f; fireLight.intensity = level * 3.0f * flick; }
        SetEmission(emissiveMats, emitColor * (level * 3.2f * flick));
    }

    public string Status => sim.Burning == 0 && sim.T < 20 ? "爐火：熄" : $"爐溫 {sim.T:0}°（燃柴 {sim.Burning}）";
}
