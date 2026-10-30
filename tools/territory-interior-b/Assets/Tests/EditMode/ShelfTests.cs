using System.Collections.Generic;
using NUnit.Framework;

/// Collection shelf rules (work pack 02-B §8): one piece never sits in two slots, take-then-place never duplicates.
public class ShelfTests
{
    static List<ItemStack> Bag() => new List<ItemStack> { new ItemStack("卷軸", 1), new ItemStack("藥罐", 1), new ItemStack("青靈草", 4) };

    static int Total(Shelf s, List<ItemStack> bag, string item) => s.Count(item) + Items.Count(bag, item);

    [Test]
    public void PlaceTakesThePieceOutOfTheBag()
    {
        var s = new Shelf(); var bag = Bag();
        Assert.AreEqual(Shelf.Result.Placed, s.Place(4, "卷軸", bag));
        Assert.AreEqual("卷軸", s[4]);
        Assert.AreEqual(0, Items.Count(bag, "卷軸"));
        Assert.AreEqual(1, s.Filled);
    }

    [Test]
    public void SamePieceCannotGoInTwoSlots()
    {
        var s = new Shelf(); var bag = Bag();
        s.Place(1, "卷軸", bag);
        Assert.AreEqual(Shelf.Result.NotOwned, s.Place(2, "卷軸", bag), "the only scroll is already on the shelf");
        Assert.AreEqual(1, s.Count("卷軸"));
        Assert.IsNull(s[2]);
    }

    [Test]
    public void OnlyCollectiblesTheBagHolds()
    {
        var s = new Shelf(); var bag = Bag();
        Assert.AreEqual(Shelf.Result.NotOwned, s.Place(1, "木匣", bag), "not in the bag");
        Assert.AreEqual(Shelf.Result.NotOwned, s.Place(1, "青靈草", bag), "herbs are not collectibles");
        Assert.AreEqual(0, s.Filled);
        Assert.AreEqual(4, Items.Count(bag, "青靈草"));
    }

    [Test]
    public void OccupiedSlotAndBadSlotAreRefused()
    {
        var s = new Shelf(); var bag = Bag();
        s.Place(3, "卷軸", bag);
        Assert.AreEqual(Shelf.Result.SlotTaken, s.Place(3, "藥罐", bag));
        Assert.AreEqual(1, Items.Count(bag, "藥罐"), "refused placement keeps the piece in the bag");
        Assert.AreEqual(Shelf.Result.BadSlot, s.Place(0, "藥罐", bag));
        Assert.AreEqual(Shelf.Result.BadSlot, s.Place(9, "藥罐", bag));
    }

    [Test]
    public void MoveChangesSlotWithoutTouchingTheBag()
    {
        var s = new Shelf(); var bag = Bag();
        s.Place(6, "藥罐", bag); s.Place(3, "卷軸", bag);
        Assert.AreEqual(Shelf.Result.Moved, s.Move(6, 8));
        Assert.IsNull(s[6]);
        Assert.AreEqual("藥罐", s[8]);
        Assert.AreEqual(Shelf.Result.SlotTaken, s.Move(8, 3));
        Assert.AreEqual(Shelf.Result.SlotEmpty, s.Move(1, 2));
        Assert.AreEqual(1, Total(s, bag, "藥罐"));
        Assert.AreEqual(0, Items.Count(bag, "藥罐"));
    }

    [Test]
    public void TakeThenPlaceAgainNeverDuplicates()
    {
        var s = new Shelf(); var bag = Bag();
        for (int i = 0; i < 5; i++)
        {
            Assert.AreEqual(Shelf.Result.Placed, s.Place(1 + i, "卷軸", bag));
            Assert.AreEqual(Shelf.Result.Taken, s.Take(1 + i, bag, 15));
            Assert.AreEqual(1, Total(s, bag, "卷軸"));
        }
        Assert.AreEqual(Shelf.Result.SlotEmpty, s.Take(1, bag, 15));
    }

    [Test]
    public void FullBagKeepsThePieceOnTheShelf()
    {
        var s = new Shelf(); var bag = new List<ItemStack> { new ItemStack("卷軸", 1), new ItemStack("青靈草", 1) };
        s.Place(2, "卷軸", bag);
        bag.Add(new ItemStack("松柴", 1));                  // bag now full at capacity 2
        Assert.AreEqual(Shelf.Result.BagFull, s.Take(2, bag, 2));
        Assert.AreEqual("卷軸", s[2]);
        Assert.AreEqual(1, Total(s, bag, "卷軸"));
    }

    [Test]
    public void RepeatedRequestReplaysWithoutChange()
    {
        var s = new Shelf(); var bag = new List<ItemStack> { new ItemStack("卷軸", 2) };
        Assert.AreEqual(Shelf.Result.Placed, s.Place(1, "卷軸", bag, "req-1"));
        Assert.AreEqual(Shelf.Result.Replayed, s.Place(1, "卷軸", bag, "req-1"));
        Assert.AreEqual(1, Items.Count(bag, "卷軸"), "the retry does not take a second scroll");
        Assert.AreEqual(Shelf.Result.Conflict, s.Place(2, "卷軸", bag, "req-1"));
        Assert.IsNull(s[2]);
        Assert.AreEqual(Shelf.Result.Taken, s.Take(1, bag, 15, "req-2"));
        Assert.AreEqual(Shelf.Result.Replayed, s.Take(1, bag, 15, "req-2"));
        Assert.AreEqual(2, Items.Count(bag, "卷軸"));
    }

    [Test]
    public void AllEightSlotsFill()
    {
        var s = new Shelf(); var bag = new List<ItemStack> { new ItemStack("青瓷罐", 8) };
        for (int i = 1; i <= Shelf.Slots; i++) Assert.AreEqual(Shelf.Result.Placed, s.Place(i, "青瓷罐", bag));
        Assert.AreEqual(Shelf.Slots, s.Filled);
        Assert.AreEqual(0, Items.Count(bag, "青瓷罐"));
    }
}
