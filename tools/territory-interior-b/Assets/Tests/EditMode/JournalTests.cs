using NUnit.Framework;

public class JournalTests
{
    static void Run(Journal j, float seconds) { for (float t = 0; t < seconds; t += .05f) j.Tick(.05f); }

    [Test]
    public void OpensThenSettlesOnTheFirstSpread()
    {
        var j = new Journal(8);
        Assert.AreEqual(Journal.Phase.Closed, j.State);
        Assert.IsTrue(j.Open());
        Assert.AreEqual(Journal.Phase.Opening, j.State);
        Run(j, Journal.OpenTime + .1f);
        Assert.AreEqual(Journal.Phase.Open, j.State);
        Assert.AreEqual(0, j.Spread);
    }

    [Test]
    public void PagesTurnOnlyWhileOpen()
    {
        var j = new Journal(8);
        Assert.IsFalse(j.Next(), "closed book");
        j.Open();
        Assert.IsFalse(j.Next(), "still opening");
        Run(j, 1f);
        Assert.IsTrue(j.Next());
        Assert.IsFalse(j.Next(), "already turning");
        Run(j, Journal.TurnTime + .1f);
        Assert.AreEqual(1, j.Spread);
    }

    [Test]
    public void StopsAtTheFirstAndLastSpread()
    {
        var j = new Journal(8);
        j.Open(); Run(j, 1f);
        Assert.IsFalse(j.Prev(), "first spread");
        for (int i = 0; i < 10; i++) { j.Next(); Run(j, 1f); }
        Assert.AreEqual(j.Spreads - 1, j.Spread);
        Assert.IsFalse(j.CanNext);
        Assert.IsTrue(j.Prev()); Run(j, 1f);
        Assert.AreEqual(j.Spreads - 2, j.Spread);
    }

    [Test]
    public void ClosesFromAnySpreadAndReopensAtTheStart()
    {
        var j = new Journal(8);
        j.Open(); Run(j, 1f); j.Next(); Run(j, 1f);
        Assert.IsTrue(j.Close());
        Assert.IsTrue(j.Shown, "closing animation still on screen");
        Run(j, Journal.CloseTime + .1f);
        Assert.AreEqual(Journal.Phase.Closed, j.State);
        Assert.IsFalse(j.Shown);
        j.Open(); Run(j, 1f);
        Assert.AreEqual(0, j.Spread);
    }

    [Test]
    public void PageCountRoundsUpToWholeSpreads()
    {
        Assert.AreEqual(8, new Journal(7).Pages);
        Assert.AreEqual(2, new Journal(0).Pages);
        Assert.AreEqual(4, new Journal(8).Spreads);
    }
}
