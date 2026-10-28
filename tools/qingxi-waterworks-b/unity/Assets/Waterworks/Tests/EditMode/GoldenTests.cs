// Replays tools/qingxi-waterworks-b/tests/scenarios.json through the C# rules and compares every step with golden.json
// (written by the JS core). Same projection as tests/replay.mjs, so any drift between the two ports fails here.
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using NUnit.Framework;
using UnityEngine;
using static Qingxi.Waterworks.MiniJson;

namespace Qingxi.Waterworks.Tests
{
    public class GoldenTests
    {
        static string TestsDir => Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "tests"));
        static Site site;
        static Site LoadSite() => site ??= Site.FromJson(Resources.Load<TextAsset>("waterworks-site").text);

        static object Issue(Issue i) => new Dictionary<string, object> { ["code"] = i.Code, ["at"] = i.At?.Cast<object>().ToList(), ["side"] = i.Side, ["message"] = i.Message };
        static object Leak(Leak l, bool side) { var d = new Dictionary<string, object> { ["at"] = l.At.Cast<object>().ToList(), ["q"] = l.Q, ["why"] = l.Why }; if (side) d["side"] = l.Side; return d; }
        static object Counts(Dictionary<string, int> c) => c.ToDictionary(kv => kv.Key, kv => (object)kv.Value);

        static object Receipt(Receipt r) => r == null ? null : new Dictionary<string, object>
        {
            ["requestId"] = r.RequestId, ["attempt"] = r.Attempt, ["outcomeId"] = r.OutcomeId, ["spent"] = Counts(r.Spent),
            ["result"] = new Dictionary<string, object> { ["fieldsFlow"] = r.FieldsFlow, ["fieldsSupplyPct"] = r.FieldsSupplyPct, ["creekFlow"] = r.CreekFlow,
                ["nursery"] = r.Nursery, ["nurseryScore"] = r.NurseryScore, ["leaks"] = r.Leaks.Select(l => Leak(l, false)).ToList() },
            ["surprises"] = r.Surprises.Cast<object>().ToList(),
            ["plan"] = r.Plan.Select(p => (object)new Dictionary<string, object> { ["seg"] = p.Seg, ["cell"] = p.Cell, ["type"] = p.Type, ["model"] = p.Model, ["rot"] = p.Rot, ["open"] = p.Open }).ToList(),
        };

        static object Project(Rules R, GameState s, Result res)
        {
            var sim = R.Simulate(s); var c = R.Check(s); var q = R.Quote(s);
            return new Dictionary<string, object>
            {
                ["res"] = new Dictionary<string, object> { ["ok"] = res.Ok, ["code"] = res.Code, ["message"] = res.Message, ["open"] = res.Open, ["replay"] = res.Replay,
                    ["receipt"] = Receipt(res.Receipt), ["issues"] = (res.Issues ?? new List<Issue>()).Select(Issue).ToList() },
                ["sim"] = new Dictionary<string, object>
                {
                    ["fields"] = sim.Fields, ["creek"] = sim.Creek, ["supply"] = sim.Supply,
                    ["nursery"] = new Dictionary<string, object> { ["score"] = sim.Nursery.Score, ["level"] = sim.Nursery.Level, ["text"] = sim.Nursery.Text },
                    ["wet"] = sim.Wet.ToDictionary(kv => kv.Key, kv => (object)kv.Value), ["risks"] = sim.Risks.Cast<object>().ToList(),
                    ["issues"] = sim.Issues.Select(Issue).ToList(), ["leaks"] = sim.Leaks.Select(l => Leak(l, true)).ToList(),
                },
                ["check"] = c.Issues.Select(i => (object)i.Code).ToList(), ["need"] = Counts(q.Need),
                ["short"] = q.Short.Select(x => (object)new Dictionary<string, object> { ["material"] = x.material, ["need"] = x.need, ["have"] = x.have }).ToList(),
                ["stock"] = Counts(s.Stock), ["requestId"] = Rules.RequestIdFor(s), ["finished"] = s.Finished, ["direction"] = s.Direction,
                ["pieces"] = s.Pieces.Entries.Select(e => (object)new Dictionary<string, object> { ["cell"] = e.Key, ["type"] = e.Value.Type, ["rot"] = e.Value.Rot, ["seg"] = e.Value.Seg, ["open"] = e.Value.Open }).ToList(),
            };
        }

        static Result Do(Rules R, GameState s, Dictionary<string, object> a)
        {
            int X() => I(a["x"]); int Y() => I(a["y"]);
            switch (S(a["op"]))
            {
                case "place": return R.Place(s, X(), Y(), S(a["type"]), a.TryGetValue("rot", out var r) ? I(r) : 0);
                case "rotate": return R.Rotate(s, X(), Y());
                case "remove": return R.Remove(s, X(), Y());
                case "gate": return R.ToggleGate(s, X(), Y());
                case "direction": return R.SetDirection(s, S(a["dir"]));
                case "undo": return R.Undo(s);
                case "redo": return R.Redo(s);
                case "finish": return R.Finish(s);
                case "retry": return R.Retry(s);
            }
            throw new System.ArgumentException(S(a["op"]));
        }

        /// <summary>Deep equality where a missing key equals null and numbers compare by value.</summary>
        static string Diff(object want, object got, string path)
        {
            if (want == null || got == null)
            {
                bool emptyW = want == null, emptyG = got == null;
                return emptyW && emptyG ? null : $"{path}: want {Write(want)} got {Write(got)}";
            }
            if (want is double || want is int)
                return (got is double || got is int) && System.Math.Abs(D(want) - D(got)) < 1e-9 ? null : $"{path}: want {Write(want)} got {Write(got)}";
            if (want is IDictionary wd)
            {
                if (!(got is IDictionary gd)) return $"{path}: want object got {Write(got)}";
                foreach (var k in wd.Keys.Cast<object>().Concat(gd.Keys.Cast<object>()).Distinct())
                {
                    var d = Diff(wd.Contains(k) ? wd[k] : null, gd.Contains(k) ? gd[k] : null, $"{path}.{k}"); if (d != null) return d;
                }
                return null;
            }
            if (want is IList wl)
            {
                if (!(got is IList gl)) return $"{path}: want list got {Write(got)}";
                if (wl.Count != gl.Count) return $"{path}: want {wl.Count} items got {gl.Count}: {Write(got)}";
                for (int i = 0; i < wl.Count; i++) { var d = Diff(wl[i], gl[i], $"{path}[{i}]"); if (d != null) return d; }
                return null;
            }
            return Equals(want, got) ? null : $"{path}: want {Write(want)} got {Write(got)}";
        }

        static IEnumerable<string> ScenarioIds() =>
            L(O(Parse(File.ReadAllText(Path.Combine(TestsDir, "scenarios.json"))))["scenarios"]).Select(x => S(O(x)["id"]));

        [TestCaseSource(nameof(ScenarioIds))]
        public void MatchesJsCore(string id)
        {
            var R = new Rules(LoadSite());
            var sc = L(O(Parse(File.ReadAllText(Path.Combine(TestsDir, "scenarios.json"))))["scenarios"]).Select(O).First(x => S(x["id"]) == id);
            var want = L(O(O(Parse(File.ReadAllText(Path.Combine(TestsDir, "golden.json"))))["scenarios"])[id]);
            var s = R.NewGame(R.Site.Fixtures[S(sc["fixture"])].ObservationIds, id);
            var got = new List<object> { Project(R, s, Result.Yes()) };
            foreach (var a in L(sc["steps"])) got.Add(Project(R, s, Do(R, s, O(a))));
            for (int i = 0; i < want.Count; i++)
            {
                var d = Diff(want[i], Parse(Write(got[i])), $"step{i}");
                Assert.IsNull(d, $"{id} {(i == 0 ? "start" : Write(L(sc["steps"])[i - 1]))}\n{d}");
            }
            Assert.AreEqual(want.Count, got.Count);
        }

        [Test]
        public void FinishTwiceDeductsOnce()
        {
            var R = new Rules(LoadSite()); var s = R.NewGame(R.Site.Fixtures["all"].ObservationIds, "t");
            foreach (var y in new[] { 1, 2, 3, 4 }) Assert.IsTrue(R.Place(s, 3, y, "worn").Ok);
            Assert.IsTrue(R.Place(s, 3, 5, "apron").Ok); Assert.IsTrue(R.SetDirection(s, "restore_channel").Ok);
            var a = R.Finish(s); var stock = new Dictionary<string, int>(s.Stock); var b = R.Finish(s);
            Assert.IsFalse(a.Replay.Value); Assert.IsTrue(b.Replay.Value); Assert.AreSame(a.Receipt, b.Receipt);
            CollectionAssert.AreEqual(stock, s.Stock); Assert.AreEqual("channel_restored_direct", a.Receipt.OutcomeId);
        }
    }
}
