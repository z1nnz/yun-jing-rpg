using System.Collections.Generic;
using UnityEngine;

/// Collection shelf (TI01): E opens the shelf panel; pieces from the bag go onto the 8 sockets
/// (SOCKET_slot_1…8), can be moved between slots or taken back down. Rules live in Shelf (Logic);
/// this keeps one model per filled slot and flies pieces between the hand and the socket.
public class ShelfDisplay : Interactable
{
    public Transform[] sockets = new Transform[Shelf.Slots];   // index 0 = slot 1
    public string[] pieceNames;                                // collectible → template (hidden) model
    public GameObject[] pieceTemplates;
    public string[] startSlots = new string[Shelf.Slots];      // what is already on the shelf when the scene starts
    public bool isOpen;
    public readonly Shelf shelf = new Shelf();
    PlayerAvatar user;

    readonly GameObject[] shown = new GameObject[Shelf.Slots];
    class Flight { public GameObject go; public Vector3 a, b; public Quaternion ra, rb; public float t; public int slot; public bool down, move; public Vector3 scale = Vector3.one; }
    readonly List<Flight> flights = new List<Flight>();

    public override string Prompt => isOpen ? "" : "[E] 看看收藏架";
    public override bool HoldsCamera => isOpen;

    void Start() { Fill(); }

    /// Puts the starting pieces up (no bag involved).
    public void Fill()
    {
        if (shelf.Filled > 0) return;
        var seed = new List<ItemStack>();
        for (int i = 0; i < Shelf.Slots; i++)
            if (!string.IsNullOrEmpty(startSlots[i])) { seed.Add(new ItemStack(startSlots[i], 1)); shelf.Place(i + 1, startSlots[i], seed); }
        for (int i = 1; i <= Shelf.Slots; i++) Show(i);
    }

    public override void Interact(PlayerAvatar player)
    {
        if (isOpen) return;
        user = player; isOpen = true;
        if (InteriorUI.Instance) InteriorUI.Instance.ShowShelf(this, player);
    }

    public void Close()
    {
        isOpen = false;
        if (InteriorUI.Instance) InteriorUI.Instance.HideShelf();
    }

    static void Toast(string s) { if (InteriorUI.Instance) InteriorUI.Instance.Toast(s); }

    public Shelf.Result Place(int slot, string item)
    {
        var r = shelf.Place(slot, item, user.inventory);
        if (r == Shelf.Result.Placed) { Show(slot); Fly(slot, false); Toast($"{item}擺上了第 {slot} 格"); }
        else Refuse(r);
        return r;
    }

    public Shelf.Result Move(int from, int to)
    {
        var r = shelf.Move(from, to);
        if (r == Shelf.Result.Moved && from != to)
        {
            var go = shown[from - 1]; shown[from - 1] = null; shown[to - 1] = go;
            if (go) flights.Add(new Flight { go = go, a = go.transform.position, b = sockets[to - 1].position, ra = go.transform.rotation, rb = Rest(to), slot = to, move = true, scale = go.transform.localScale });
            Toast($"把{shelf[to]}挪到第 {to} 格");
        }
        else if (r != Shelf.Result.Moved) Refuse(r);
        return r;
    }

    public Shelf.Result Take(int slot)
    {
        string item = shelf[slot];
        var r = shelf.Take(slot, user.inventory, user.bagCapacity);
        if (r == Shelf.Result.Taken) { Fly(slot, true); Toast($"{item}收回乾坤袋"); }
        else Refuse(r);
        return r;
    }

    static void Refuse(Shelf.Result r)
    {
        switch (r)
        {
            case Shelf.Result.SlotTaken: Toast("那一格已經擺了東西"); break;
            case Shelf.Result.BagFull: Toast("乾坤袋裝不下了"); break;
            case Shelf.Result.NotOwned: Toast("乾坤袋裡沒有這件"); break;
        }
    }

    Quaternion Rest(int slot) => transform.rotation * Quaternion.Euler(0f, (slot % 3 - 1) * 14f, 0f);

    GameObject Template(string item)
    {
        int i = System.Array.IndexOf(pieceNames, item);
        return i >= 0 ? pieceTemplates[i] : null;
    }

    /// Makes the model in a slot match the shelf.
    void Show(int slot)
    {
        var item = shelf[slot];
        if (shown[slot - 1]) { DestroyImmediate(shown[slot - 1]); shown[slot - 1] = null; }
        var tpl = item != null ? Template(item) : null;
        if (!tpl || !sockets[slot - 1]) return;
        var go = Instantiate(tpl);
        go.name = $"Shelf_{slot}_{item}"; go.SetActive(true);
        go.transform.SetPositionAndRotation(sockets[slot - 1].position, Rest(slot));
        shown[slot - 1] = go;
    }

    Vector3 Hand => user.transform.position + Vector3.up * .95f + user.transform.forward * .3f;

    /// Up from the hand into the slot, or down from the slot into the hand (the model then goes).
    void Fly(int slot, bool down)
    {
        var go = shown[slot - 1];
        if (!go) return;
        var s = sockets[slot - 1].position;
        var f = new Flight { go = go, slot = slot, down = down, ra = go.transform.rotation, rb = go.transform.rotation, scale = go.transform.localScale };
        if (down) { f.a = s; f.b = Hand; shown[slot - 1] = null; }
        else { f.a = Hand; f.b = s; go.transform.position = Hand; }
        flights.Add(f);
    }

    public override void Tick(float dt)
    {
        for (int i = flights.Count - 1; i >= 0; i--)
        {
            var f = flights[i];
            if (!f.go) { flights.RemoveAt(i); continue; }
            f.t += dt / .7f;
            float u = Mathf.SmoothStep(0f, 1f, Mathf.Clamp01(f.t));
            f.go.transform.position = Vector3.Lerp(f.a, f.b, u) + Vector3.up * Mathf.Sin(u * Mathf.PI) * .25f;
            f.go.transform.rotation = Quaternion.Slerp(f.ra, f.rb, u);
            f.go.transform.localScale = f.move ? f.scale : f.scale * (f.down ? Mathf.Lerp(1f, .5f, u) : Mathf.Lerp(.6f, 1f, u));
            if (f.t >= 1f)
            {
                if (f.down) DestroyImmediate(f.go);
                flights.RemoveAt(i);
            }
        }
    }
}
