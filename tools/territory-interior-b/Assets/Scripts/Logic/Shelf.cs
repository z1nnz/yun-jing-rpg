using System.Collections.Generic;

/// Collection shelf (TI01): 8 slots, one piece per slot. Mirrors the place-collectible / take-collectible
/// proposal in CONTRACT.md: a piece comes off the bag when it goes up and back into the bag when taken down,
/// so it is never in two places; moving between slots never touches the bag; a repeated requestId replays.
public sealed class Shelf
{
    public const int Slots = 8;
    /// Display pieces that can go on the shelf (TI08 stand-ins until C's 見聞 items arrive).
    public static readonly string[] Collectibles = { "木匣", "卷軸", "青瓷罐", "藥罐" };

    public enum Result { Placed, Moved, Taken, Replayed, BadSlot, NotOwned, SlotTaken, SlotEmpty, BagFull, Conflict }

    readonly string[] slots = new string[Slots];
    readonly Dictionary<string, (string fingerprint, Result result)> receipts = new Dictionary<string, (string, Result)>();

    public static bool IsCollectible(string item) => System.Array.IndexOf(Collectibles, item) >= 0;
    public static bool InRange(int slot) => slot >= 1 && slot <= Slots;

    /// Item in a 1-based slot, or null.
    public string this[int slot] => InRange(slot) ? slots[slot - 1] : null;

    public int Filled { get { int n = 0; foreach (var s in slots) if (s != null) n++; return n; } }

    public int Count(string item) { int n = 0; foreach (var s in slots) if (s == item) n++; return n; }

    /// Bag → empty slot. Only collectibles the bag really holds.
    public Result Place(int slot, string item, List<ItemStack> bag, string requestId = null) =>
        Once(requestId, $"place|{slot}|{item}", () =>
        {
            if (!InRange(slot)) return Result.BadSlot;
            if (!IsCollectible(item) || Items.Count(bag, item) < 1) return Result.NotOwned;
            if (slots[slot - 1] != null) return Result.SlotTaken;
            Items.Remove(bag, item, 1);
            slots[slot - 1] = item;
            return Result.Placed;
        });

    /// Slot → another empty slot; the bag is not involved.
    public Result Move(int from, int to, string requestId = null) =>
        Once(requestId, $"move|{from}|{to}", () =>
        {
            if (!InRange(from) || !InRange(to)) return Result.BadSlot;
            if (slots[from - 1] == null) return Result.SlotEmpty;
            if (from == to) return Result.Moved;
            if (slots[to - 1] != null) return Result.SlotTaken;
            slots[to - 1] = slots[from - 1]; slots[from - 1] = null;
            return Result.Moved;
        });

    /// Slot → bag. A full bag leaves the piece on the shelf.
    public Result Take(int slot, List<ItemStack> bag, int bagCapacity, string requestId = null) =>
        Once(requestId, $"take|{slot}", () =>
        {
            if (!InRange(slot)) return Result.BadSlot;
            var item = slots[slot - 1];
            if (item == null) return Result.SlotEmpty;
            if (Items.Add(bag, item, 1, bagCapacity) == 0) return Result.BagFull;
            slots[slot - 1] = null;
            return Result.Taken;
        });

    /// Same requestId + same content → the first answer again with nothing changed; different content → Conflict.
    Result Once(string requestId, string fingerprint, System.Func<Result> run)
    {
        if (requestId != null && receipts.TryGetValue(requestId, out var r))
            return r.fingerprint == fingerprint ? Result.Replayed : Result.Conflict;
        var result = run();
        if (requestId != null) receipts[requestId] = (fingerprint, result);
        return result;
    }
}
