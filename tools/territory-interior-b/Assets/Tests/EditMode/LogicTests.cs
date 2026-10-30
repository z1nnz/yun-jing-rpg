using System.Collections.Generic;
using NUnit.Framework;
using UnityEngine;

/// State logic only (no scene): storage stacking, home-furnace rules and the touch stick.
public class ItemsTests
{
    [Test]
    public void AddStacksThenOpensSlots()
    {
        var s = new List<ItemStack>();
        Assert.AreEqual(150, Items.Add(s, "松柴", 150, 30));
        Assert.AreEqual(2, s.Count);
        Assert.AreEqual(99, s[0].count);
        Assert.AreEqual(51, s[1].count);
        Assert.AreEqual(10, Items.Add(s, "松柴", 10, 30));
        Assert.AreEqual(2, s.Count, "partial stack is topped up before a new slot opens");
    }

    [Test]
    public void AddStopsAtCapacity()
    {
        var s = new List<ItemStack> { new ItemStack("木匣", 1) };
        Assert.AreEqual(99, Items.Add(s, "松柴", 300, 2));
        Assert.AreEqual(2, s.Count);
        Assert.AreEqual(0, Items.Add(s, "卷軸", 1, 2));
    }

    [Test]
    public void RemoveTakesFromLastAndDropsEmptySlots()
    {
        var s = new List<ItemStack> { new ItemStack("青靈草", 3), new ItemStack("卷軸", 1), new ItemStack("青靈草", 2) };
        Assert.AreEqual(4, Items.Remove(s, "青靈草", 4));
        Assert.AreEqual(2, s.Count);
        Assert.AreEqual(1, Items.Count(s, "青靈草"));
        Assert.AreEqual(1, Items.Remove(s, "青靈草", 5), "only what is there is taken");
    }

    [Test]
    public void SortMergesAndOrdersByTab()
    {
        var s = new List<ItemStack>
        {
            new ItemStack("木匣", 1), new ItemStack("松柴", 40), new ItemStack("回春丹・凡品", 2),
            new ItemStack("松柴", 30), new ItemStack("青靈草", 6),
        };
        Items.Sort(s, 30);
        CollectionAssert.AreEqual(new[] { "青靈草", "回春丹・凡品", "松柴", "木匣" }, s.ConvertAll(x => x.name));
        Assert.AreEqual(70, s[2].count);
    }

    [Test]
    public void GradedPillUsesBaseNameForCategory()
    {
        Assert.AreEqual("回春丹", Items.BaseName("回春丹・上品"));
        Assert.AreEqual("丹藥", Items.Category("回春丹・上品"));
        Assert.IsTrue(Items.InTab("青靈草", 1));
        Assert.IsFalse(Items.InTab("青靈草", 2));
        Assert.IsTrue(Items.InTab("青靈草", 0));
    }
}

public class HomeAlchemyTests
{
    static HomeAlchemy.Furnace Charged(bool water = true, bool rightOrder = true)
    {
        var f = new HomeAlchemy.Furnace();
        f.Lid(false);
        if (rightOrder)
        {
            if (water) { f.Water(); f.Water(); }
            f.Charge(HomeAlchemy.Minor); f.Charge(HomeAlchemy.Lead);
        }
        else
        {
            f.Charge(HomeAlchemy.Lead); f.Charge(HomeAlchemy.Minor);
            if (water) { f.Water(); f.Water(); }
        }
        f.Lid(true);
        return f;
    }

    /// Keeps one log on a shut vent for 文火 and two logs at a quarter vent for 中火, refuelling as logs burn out.
    static void Tend(HomeAlchemy.Furnace f, double maxSeconds, System.Func<HomeAlchemy.Furnace, bool> until)
    {
        for (int i = 0; i < maxSeconds * 10 && !until(f); i++)
        {
            bool gentle = f.PhaseIndex == 0;
            int want = gentle ? 1 : 2;
            f.SetVent(gentle ? 0 : .25);
            while (f.Burning + f.Loaded < want) f.AddFuel();
            if (f.Loaded > 0) f.Ignite();
            f.StepTick();
        }
    }

    [Test]
    public void SteadyFireAndTimelyCondenseMakesAPill()
    {
        var f = Charged();
        Tend(f, 120, x => x.CompleteTick != null);
        Assert.IsNotNull(f.CompleteTick, "both fire phases complete");
        Tend(f, 10, x => x.SinceComplete >= 3.5);
        f.Condense();
        var o = HomeAlchemy.Judge(f);
        Assert.IsTrue(o.success);
        Assert.GreaterOrEqual(o.score, 65, "steady fire, right order and water → at least 良品");
        Assert.AreEqual(1.0, o.condense, 1e-9);
    }

    [Test]
    public void NoWaterBurnsDry()
    {
        var f = Charged(water: false);
        Tend(f, 60, x => x.CompleteTick != null);
        f.Condense();
        var o = HomeAlchemy.Judge(f);
        Assert.IsFalse(o.success);
        StringAssert.Contains("乾裂", o.reasons[0]);
    }

    [Test]
    public void WrongOrderCostsPrep()
    {
        var a = Charged(); var b = Charged(rightOrder: false);
        foreach (var f in new[] { a, b }) { Tend(f, 120, x => x.CompleteTick != null); Tend(f, 10, x => x.SinceComplete >= 3.5); f.Condense(); }
        var oa = HomeAlchemy.Judge(a); var ob = HomeAlchemy.Judge(b);
        Assert.Less(ob.prep, oa.prep);
        Assert.Less(ob.score, oa.score);
    }

    [Test]
    public void LeavingThePillTooLongOvercooks()
    {
        var f = Charged();
        Tend(f, 120, x => x.CompleteTick != null);
        Tend(f, 40, x => x.SinceComplete >= HomeAlchemy.Overcook + 1);
        f.Condense();
        Assert.IsFalse(HomeAlchemy.Judge(f).success);
    }

    [Test]
    public void RoaringFireScorches()
    {
        var f = Charged();
        f.SetVent(1);
        for (int i = 0; i < HomeAlchemy.MaxBurning; i++) f.AddFuel();
        f.Ignite();
        for (int i = 0; i < 600; i++) f.StepTick();
        Assert.Greater(f.Scorch, HomeAlchemy.ScorchLimitSeconds);
        f.Condense();
        var o = HomeAlchemy.Judge(f);
        Assert.IsFalse(o.success);
        StringAssert.Contains("焦糊", o.reasons[0]);
    }

    [Test]
    public void OpenLidDoesNotAdvanceAPhase()
    {
        var f = Charged();
        f.Lid(false);
        Tend(f, 60, x => false);
        Assert.AreEqual(0, f.PhaseIndex);
        Assert.AreEqual(0, f.Progress[0], 1e-9);
    }

    [Test]
    public void NextBatchKeepsTheFire()
    {
        var f = Charged();
        f.AddFuel(); f.Ignite();
        for (int i = 0; i < 50; i++) f.StepTick();
        var n = f.Next();
        Assert.AreEqual(f.Burning, n.Burning);
        Assert.AreEqual(f.T, n.T, 1e-9);
        Assert.AreEqual(0, n.OrderLog.Count);
    }
}

public class TouchStickTests
{
    [Test]
    public void LeftHalfMovesRightHalfLooks()
    {
        Assert.IsTrue(TouchStick.IsMoveSide(new Vector2(100, 300), 1920));
        Assert.IsFalse(TouchStick.IsMoveSide(new Vector2(1500, 300), 1920));
    }

    [Test]
    public void DeadZoneAndClamp()
    {
        var o = new Vector2(200, 200);
        Assert.AreEqual(Vector2.zero, TouchStick.Evaluate(o, o + new Vector2(5, 0), 100));
        var full = TouchStick.Evaluate(o, o + new Vector2(0, 400), 100);
        Assert.AreEqual(1f, full.magnitude, 1e-4f);
        Assert.AreEqual(1f, full.y, 1e-4f, "finger up = walk forward");
        var half = TouchStick.Evaluate(o, o + new Vector2(56, 0), 100);
        Assert.AreEqual(.5f, half.x, 1e-3f);
    }

    [Test]
    public void KnobStaysOnTheRing()
    {
        var o = Vector2.zero;
        Assert.AreEqual(100f, TouchStick.Knob(o, new Vector2(300, 0), 100).magnitude, 1e-4f);
        Assert.AreEqual(new Vector2(30, 40), TouchStick.Knob(o, new Vector2(30, 40), 100));
    }

    [Test]
    public void DragTurnsTheCamera()
    {
        var l = TouchStick.Look(new Vector2(1080, 540), 1080);
        Assert.AreEqual(180f, l.x, 1e-4f);
        Assert.AreEqual(-90f, l.y, 1e-4f, "drag up looks up (pitch decreases)");
    }
}
