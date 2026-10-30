using System.Collections.Generic;
using UnityEngine;

/// Storage chest: E opens the lid and the put/take panel. Slots stack same-name items (Items.StackMax);
/// items with a visual show up inside the box and fly between the player's hands and the box.
public class ChestStorage : Interactable
{
    public Transform lidPivot;
    public float closedAngle, openAngle;        // lid angles about hingeAxis, applied on top of lidRest
    public Quaternion lidRest = Quaternion.identity;
    public Vector3 hingeAxis = Vector3.right;   // local axis of lidPivot
    public int capacity = 30;
    public List<ItemStack> contents = new List<ItemStack>();
    public string[] itemNames;                  // items with a visual parked inside the box
    public GameObject[] itemVisuals;
    public bool isOpen;
    float openT;

    // one item in flight between the player's hands and its place in the box
    int flyIndex = -1; float flyT; bool flyIn; Transform flyPlayer;
    Vector3[] homeLocal, homeScale; Quaternion[] homeRot;

    public override string Prompt => isOpen ? "" : "[E] 打開儲物箱";
    public override bool HoldsCamera => isOpen;

    public override void Interact(PlayerAvatar player)
    {
        if (isOpen) return;
        isOpen = true;
        if (InteriorUI.Instance) InteriorUI.Instance.ShowStorage(this, player);
    }

    /// Moves a whole stack (or as much as fits) from the bag into the chest.
    public int Put(ItemStack s, PlayerAvatar player)
    {
        string n = s.name;
        int moved = Items.Add(contents, n, s.count, capacity);
        if (moved == 0) { Toast("箱子塞不下了"); return 0; }
        Items.Remove(player.inventory, n, moved);
        RefreshVisuals(); StartFlight(n, player, true);
        Toast($"放入了「{n}」×{moved}");
        return moved;
    }

    public int Take(ItemStack s, PlayerAvatar player)
    {
        string n = s.name;
        int moved = Items.Add(player.inventory, n, s.count, player.bagCapacity);
        if (moved == 0) { Toast("乾坤袋裝不下了"); return 0; }
        Items.Remove(contents, n, moved);
        StartFlight(n, player, false);
        Toast($"取出了「{n}」×{moved}");
        return moved;
    }

    static void Toast(string s) { if (InteriorUI.Instance) InteriorUI.Instance.Toast(s); }

    public void Close()
    {
        isOpen = false;
        if (InteriorUI.Instance) InteriorUI.Instance.HideStorage();
    }

    public void RefreshVisuals()
    {
        if (itemNames == null) return;
        CacheHomes();
        for (int i = 0; i < itemNames.Length; i++)
            if (itemVisuals[i] && i != flyIndex) itemVisuals[i].SetActive(Items.Count(contents, itemNames[i]) > 0);
    }

    void CacheHomes()
    {
        if (homeLocal != null && homeLocal.Length == itemVisuals.Length) return;
        homeLocal = new Vector3[itemVisuals.Length]; homeScale = new Vector3[itemVisuals.Length]; homeRot = new Quaternion[itemVisuals.Length];
        for (int i = 0; i < itemVisuals.Length; i++)
            if (itemVisuals[i]) { homeLocal[i] = itemVisuals[i].transform.localPosition; homeRot[i] = itemVisuals[i].transform.localRotation; homeScale[i] = itemVisuals[i].transform.localScale; }
    }

    void StartFlight(string item, PlayerAvatar player, bool into)
    {
        CacheHomes();
        if (flyIndex >= 0) LandFlight();
        flyIndex = System.Array.IndexOf(itemNames, Items.BaseName(item));
        if (flyIndex < 0 || !itemVisuals[flyIndex]) { flyIndex = -1; return; }
        flyT = 0f; flyIn = into; flyPlayer = player.transform;
        itemVisuals[flyIndex].SetActive(true);
    }

    void LandFlight()
    {
        var v = itemVisuals[flyIndex];
        v.transform.localPosition = homeLocal[flyIndex]; v.transform.localRotation = homeRot[flyIndex]; v.transform.localScale = homeScale[flyIndex];
        v.SetActive(Items.Count(contents, itemNames[flyIndex]) > 0);
        flyIndex = -1;
    }

    public override void Tick(float dt)
    {
        openT = Mathf.MoveTowards(openT, isOpen ? 1f : 0f, dt / 0.6f);
        float s = openT * openT * (3f - 2f * openT);
        if (lidPivot) lidPivot.localRotation = lidRest * Quaternion.AngleAxis(Mathf.Lerp(closedAngle, openAngle, s), hingeAxis);

        if (flyIndex >= 0)
        {
            flyT += dt / .75f;
            float u = Mathf.SmoothStep(0f, 1f, Mathf.Clamp01(flyT));
            var v = itemVisuals[flyIndex].transform;
            Vector3 hand = flyPlayer.position + Vector3.up * .85f + flyPlayer.forward * .3f;
            Vector3 home = transform.TransformPoint(homeLocal[flyIndex]);
            float k = flyIn ? u : 1f - u;
            v.position = Vector3.Lerp(hand, home, k) + Vector3.up * Mathf.Sin(k * Mathf.PI) * .45f;
            v.rotation = transform.rotation * homeRot[flyIndex] * Quaternion.Euler(0f, (1f - k) * 220f, 0f);
            v.localScale = homeScale[flyIndex] * Mathf.Lerp(.8f, 1f, k);
            if (flyT >= 1f) LandFlight();
        }
    }
}
