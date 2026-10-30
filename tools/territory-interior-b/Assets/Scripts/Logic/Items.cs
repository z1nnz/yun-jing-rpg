using System.Collections.Generic;

/// One inventory slot: same-name items stack up to Items.StackMax.
[System.Serializable]
public class ItemStack
{
    public string name;
    public int count;
    public ItemStack(string n, int c) { name = n; count = c; }
}

/// Slot-based storage helpers shared by the bag and the chest.
public static class Items
{
    public const int StackMax = 99;
    public static readonly string[] Tabs = { "全部", "藥材", "丹藥", "材料", "器物" };

    /// Pills carry their grade after "・" (回春丹・上品); icons and categories use the base name.
    public static string BaseName(string n) { int i = n.IndexOf('・'); return i < 0 ? n : n.Substring(0, i); }

    public static string Category(string n)
    {
        switch (BaseName(n))
        {
            case "青靈草": case "淨水蓮": return "藥材";
            case "回春丹": case "聚氣丹": return "丹藥";
            case "松柴": return "材料";
            default: return "器物";
        }
    }

    public static bool InTab(string n, int tab) => tab <= 0 || Category(n) == Tabs[tab];

    public static int Count(List<ItemStack> slots, string n)
    {
        int c = 0; foreach (var s in slots) if (s.name == n) c += s.count; return c;
    }

    /// Tops up existing stacks first, then opens new slots while capacity allows. Returns how many fitted.
    public static int Add(List<ItemStack> slots, string n, int c, int capacity)
    {
        int left = c;
        foreach (var s in slots)
            if (s.name == n && s.count < StackMax) { int k = System.Math.Min(left, StackMax - s.count); s.count += k; left -= k; if (left == 0) return c; }
        while (left > 0 && slots.Count < capacity) { int k = System.Math.Min(left, StackMax); slots.Add(new ItemStack(n, k)); left -= k; }
        return c - left;
    }

    /// Takes from the last stacks first; empty slots are removed. Returns how many were taken.
    public static int Remove(List<ItemStack> slots, string n, int c)
    {
        int left = c;
        for (int i = slots.Count - 1; i >= 0 && left > 0; i--)
        {
            if (slots[i].name != n) continue;
            int k = System.Math.Min(left, slots[i].count); slots[i].count -= k; left -= k;
            if (slots[i].count == 0) slots.RemoveAt(i);
        }
        return c - left;
    }

    /// Merge partial stacks and order by tab, then name.
    public static void Sort(List<ItemStack> slots, int capacity)
    {
        var totals = new List<KeyValuePair<string, int>>();
        foreach (var s in slots)
        {
            int i = totals.FindIndex(p => p.Key == s.name);
            if (i < 0) totals.Add(new KeyValuePair<string, int>(s.name, s.count)); else totals[i] = new KeyValuePair<string, int>(s.name, totals[i].Value + s.count);
        }
        totals.Sort((a, b) =>
        {
            int ca = System.Array.IndexOf(Tabs, Category(a.Key)), cb = System.Array.IndexOf(Tabs, Category(b.Key));
            return ca != cb ? ca.CompareTo(cb) : string.CompareOrdinal(a.Key, b.Key);
        });
        slots.Clear();
        foreach (var p in totals) Add(slots, p.Key, p.Value, capacity);
    }
}
