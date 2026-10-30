using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using QingxiWorld;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;
using UnityEngine.SceneManagement;

namespace YunJing
{
    // Opt-in check of a built Qingxi scene (--abc-smoke): walks the player through the three
    // collaborator zones, the alchemy-room door and back. Local rehearsal only; writes a report and quits.
    public sealed class QingxiAbcSmoke : MonoBehaviour
    {
        readonly List<string> results = new List<string>();
        bool passed = true;
        static bool running;   // the reloaded village scene carries its own copy of this component

        IEnumerator Start()
        {
            // --abc-smoke on the command line, or ?abc-smoke in the browser (WebGL/PWA build).
            bool requested = Array.IndexOf(Environment.GetCommandLineArgs(), "--abc-smoke") >= 0 || Application.absoluteURL.Contains("abc-smoke");
            if (running || !requested) yield break;
            running = true;
            Application.targetFrameRate = 60;
            DontDestroyOnLoad(gameObject);
            yield return new WaitForSecondsRealtime(1f);
            var home = SceneManager.GetActiveScene().name;
            var walker = QingxiFirstPerson.Current;
            var foraging = walker.GetComponent<QingxiLocalForaging>();
            var stations = walker.GetComponent<QingxiAbcStations>();
            var forest = FindFirstObjectByType<QingxiForestEncounter>();
            var body = walker.GetComponent<CharacterController>();

            // The village stands on a Unity Terrain: its collider must hold the walker up in the built player.
            var terrain = Terrain.activeTerrain;
            var groundCollider = terrain != null ? terrain.GetComponent<TerrainCollider>() : null;
            var groundRay = Physics.RaycastAll(new Vector3(0, 60, -22), Vector3.down, 200f, ~0, QueryTriggerInteraction.Ignore).FirstOrDefault(h => h.collider is TerrainCollider);
            bool groundHit = groundRay.collider != null;
            Debug.Log($"[QingxiAbcSmoke] terrain={(terrain != null ? terrain.name : "none")} collider={(groundCollider != null ? groundCollider.enabled.ToString() : "none")} data={(groundCollider != null && groundCollider.terrainData != null ? groundCollider.terrainData.heightmapResolution.ToString() : "none")} ray={groundHit} {(groundHit ? groundRay.collider.name + " y=" + groundRay.point.y.ToString("0.00") : "")}");
            if (terrain != null) Check($"terrain collider holds the ground (ray hit {(groundHit ? groundRay.collider.name : "nothing")})", groundHit && groundRay.collider is TerrainCollider);

            // The real input path: hold W through the Input System and the walker must walk. (A headless run has
            // no keyboard, so a virtual one is added.) This failed silently while the legacy input handler was active.
            Spot(walker, "村口");
            yield return Frames(10);
            var keyboard = Keyboard.current ?? InputSystem.AddDevice<Keyboard>();
            var start = walker.transform.position;
            InputSystem.QueueStateEvent(keyboard, new KeyboardState(Key.W));
            yield return new WaitForSecondsRealtime(1f);
            InputSystem.QueueStateEvent(keyboard, new KeyboardState());
            yield return Frames(3);
            float walked = Vector2.Distance(new Vector2(start.x, start.z), new Vector2(walker.transform.position.x, walker.transform.position.z));
            Check($"holding W walks the player ({walked:0.0} m, keyboard {(Keyboard.current != null ? "present" : "missing")})", walked > 1f);

            // C: sorting table opens and keeps a choice.
            Spot(walker, "回村分揀桌");
            yield return Frames(10);
            bool sortingOpened = false; stations.SortingRequested += () => sortingOpened = true;
            Check("return prompt", (foraging.Prompt(walker.transform.position) ?? "").Contains("分揀"));
            foraging.TryInteract(walker.transform.position, out _);
            Check("return table opens sorting", sortingOpened);
            QingxiReturnSorting.Session.Select("herb"); QingxiReturnSorting.Session.MoveTo("save");
            walker.SetMenuOpen(false);

            // A: walking up the rabbit trail must draw a readable tell (alert -> windup) from the rabbit.
            Spot(walker, "林地遭遇");
            yield return Frames(20);
            Check("forest zone active", forest.PlayerInside);
            var burrow = forest.transform.TransformPoint(new Vector3((float)forest.Rules.world.burrow.x, 0, (float)forest.Rules.world.burrow.z));
            var seen = new HashSet<string>();
            for (float until = Time.realtimeSinceStartup + 15f; Time.realtimeSinceStartup < until && !seen.Contains("windup");)
            {
                var to = burrow - walker.transform.position; to.y = 0;
                if (to.magnitude > 3.6f) body.Move(to.normalized * 3.2f * Time.deltaTime + Vector3.down * .5f * Time.deltaTime);
                seen.Add(forest.Rules.rabbit.state);
                yield return null;
            }
            Check($"rabbit alert then windup (seen {string.Join("/", seen)}, {Vector3.Distance(walker.transform.position, burrow):F1} m from burrow)", seen.Contains("alert") && seen.Contains("windup"));
            forest.ReturnToSafePoint();
            yield return Frames(10);
            Check("back at the A09 safe point", forest.Rules.InSafeZone());
            var data = QingxiAbcZoneData.Parse(forest.zoneData.text);
            var ladder = forest.transform.TransformPoint(new Vector3(data.forest.platform.ladder.x, 0, data.forest.platform.ladder.z));
            Teleport(walker, ladder);
            yield return Frames(5);
            foraging.TryInteract(walker.transform.position, out _);
            Check("climb the A10 watch platform", forest.Climbed && forest.Rules.InSafeZone());
            foraging.TryInteract(walker.transform.position, out _);
            Check("climb down again", !forest.Climbed && body.enabled);

            // Gather one herb so the trip through the alchemy room can prove the counts come back. Wait for the
            // server link to settle first, so an online run can check the server kept the herb (K7).
            var link = QingxiServerLink.Current;
            float settle = Time.realtimeSinceStartup + 10;
            while (link != null && link.Connecting && Time.realtimeSinceStartup < settle) yield return null;
            int serverHerbs = QingxiServerLink.Online ? link.Quantity("chilu-ginseng") : 0;
            Teleport(walker, foraging.herbNodes[0].position);
            yield return Frames(5);
            foraging.TryInteract(walker.transform.position, out _);
            int herbs = foraging.Herbs;
            Check("herb gathered", herbs == 1);
            if (QingxiServerLink.Online)
            {
                float until = Time.realtimeSinceStartup + 6;
                while (link.Quantity("chilu-ginseng") <= serverHerbs && Time.realtimeSinceStartup < until) yield return null;
                Check("the server keeps the gathered herb", link.Quantity("chilu-ginseng") == serverHerbs + 1);
            }
            yield return Frames(2);
            var herbVisual = foraging.herbNodes[0].GetComponent<QingxiHerbVisual>();
            Check("herb switches to its harvested model", herbVisual != null && herbVisual.post.activeSelf && !herbVisual.pre.activeSelf);

            // The herbal stall is the market; only read the prompt so the herb count stays for the carry check.
            if (foraging.marketEntrance != null)
            {
                Teleport(walker, foraging.marketEntrance.position);
                yield return Frames(5);
                Check("market stall offers trade", (foraging.Prompt(walker.transform.position) ?? "").Contains("交換"));
            }

            // A: Johnnnny0823's training posts start his drills and give movement back afterwards.
            var training = stations.training;
            if (training != null)
            {
                Teleport(walker, training.qiPost.position + training.qiPost.forward * -1.1f);
                yield return Frames(5);
                Check("qi post offers breathing", (foraging.Prompt(walker.transform.position) ?? "").Contains("引氣呼吸"));
                foraging.TryInteract(walker.transform.position, out _);
                Check("breathing drill starts and holds the walker", training.Breath != null && training.Frozen);
                yield return Frames(30);
                Check("breathing guide advances", training.Breath != null && training.Breath.Elapsed > -1.4);
                training.End();
                Teleport(walker, training.blockPost.position + training.blockPost.forward * -1.1f);
                yield return Frames(5);
                Check("agility post offers blocking", (foraging.Prompt(walker.transform.position) ?? "").Contains("武技格擋"));
                foraging.TryInteract(walker.transform.position, out _);
                Check("block drill starts", training.Block != null && training.Block.strikes.Count == 12);
                training.End();
                Check("walker free after the drill", !training.Frozen && walker.enabled);
            }

            // 機緣 (K4/K7): a hidden find is revealed through the same F key, counted for the journal and, when the
            // game server is reachable, settled there. Uses a find this character has not found yet (a server
            // keeps finds across runs, so clearing the device record is not enough).
            var fortunes = stations.fortunes;
            if (fortunes != null && fortunes.fortunes.Length > 0)
            {
                QingxiFortunes.Fortune first = null;
                foreach (var f in fortunes.fortunes)
                {
                    try { PlayerPrefs.DeleteKey("yj.fortune." + f.id); } catch { }
                    if (!QingxiFortunes.IsFound(f)) { first = f; break; }
                }
                if (first == null) Check("every hidden find is already settled on the server", fortunes.Found == fortunes.fortunes.Length);
                else
                {
                    int before = fortunes.Found;
                    if (first.nightOnly) QingxiDayNight.Current?.SetHour(22);
                    Teleport(walker, first.position + Vector3.back * .6f);
                    yield return Frames(5);
                    Check("a hidden find glints and can be examined", (foraging.Prompt(walker.transform.position) ?? "").Contains("微光"));
                    foraging.TryInteract(walker.transform.position, out _);
                    Check("the find is revealed and counted", QingxiFortunes.IsFound(first) && fortunes.Found == before + 1 && fortunes.JournalText().Contains(first.title));
                    QingxiDayNight.Current?.SetHour(10);
                    if (QingxiServerLink.Online)
                    {
                        float until = Time.realtimeSinceStartup + 6;
                        while (!QingxiServerLink.Current.HasFortune(first.id) && Time.realtimeSinceStartup < until) yield return null;
                        Check("the server settles the find", QingxiServerLink.Current.HasFortune(first.id));
                    }
                }
            }

            // K11: the clock. Automated runs start at 10:00; at 22:00 the night lights are on and the third
            // lantern's find shows; back at 10:00 they are off again.
            var dayNight = QingxiDayNight.Current;
            Check("day and night runs (fixed at 10:00 for checks)", dayNight != null && Mathf.Abs(dayNight.Hour - 10) < .01f && !QingxiDayNight.IsNight);
            if (dayNight != null)
            {
                float noonSun = dayNight.sun != null ? dayNight.sun.intensity : 0;
                dayNight.SetHour(22);
                yield return Frames(2);
                bool lit = dayNight.nightLights.Length > 0 && Array.TrueForAll(dayNight.nightLights, l => l == null || l.enabled);
                Check($"at 22:00 it is night: sun dims ({noonSun:0.00} → {(dayNight.sun ? dayNight.sun.intensity : 0):0.00}) and {dayNight.nightLights.Length} night lights are on",
                    QingxiDayNight.IsNight && lit && dayNight.sun != null && dayNight.sun.intensity < noonSun * .4f);
                var third = fortunes != null ? Array.Find(fortunes.fortunes, f => f.nightOnly) : null;
                if (third != null && !QingxiFortunes.IsFound(third))
                {
                    Teleport(walker, third.position + Vector3.back * .6f);
                    yield return Frames(3);
                    bool atNight = (foraging.Prompt(walker.transform.position) ?? "").Contains("微光");
                    dayNight.SetHour(10);
                    yield return Frames(3);
                    bool byDay = (foraging.Prompt(walker.transform.position) ?? "").Contains("微光");
                    Check("the third lantern's find shows only at night", atNight && !byDay);
                }
                dayNight.SetHour(10);
                yield return Frames(2);
                Check("back at 10:00 the night lights are off", !QingxiDayNight.IsNight && Array.TrueForAll(dayNight.nightLights, l => l == null || !l.enabled));
            }

            // K5: walking to the south edge streams in block A2; its terrain holds the walker on the far side.
            var streamer = QingxiBlockStreamer.Current;
            var a2 = streamer != null ? streamer.blocks.FirstOrDefault(b => b.id == "A2") : null;
            if (a2 != null && Application.CanStreamedLevelBeLoaded(a2.scene))
            {
                var edge = Physics.RaycastAll(new Vector3(0, 60, -45), Vector3.down, 200f, ~0, QueryTriggerInteraction.Ignore).FirstOrDefault(h => h.collider is TerrainCollider);
                Teleport(walker, new Vector3(0, edge.collider != null ? edge.point.y : 1, -45));
                float until = Time.realtimeSinceStartup + 15;
                while (!streamer.IsLoaded("A2") && Time.realtimeSinceStartup < until) yield return null;
                Check("walking to the south edge streams in block A2", streamer.IsLoaded("A2"));
                yield return Frames(3);
                var far = Physics.RaycastAll(new Vector3(0, 60, -80), Vector3.down, 200f, ~0, QueryTriggerInteraction.Ignore).FirstOrDefault(h => h.collider is TerrainCollider);
                bool onA2 = far.collider != null && far.collider.name.Contains("BlockTerrain_A2");
                if (onA2) { Teleport(walker, far.point); yield return Frames(30); }
                Check($"block A2's ground holds the walker ({(onA2 ? "y " + walker.transform.position.y.ToString("0.0") + " on " + far.point.y.ToString("0.0") : "no A2 terrain")})",
                    onA2 && Mathf.Abs(walker.transform.position.y - far.point.y) < 1.5f);
                Spot(walker, "村口");
                yield return Frames(5);
            }

            // D3 upstream valley (PR #45): through A3's north path; the brook tiles and the clue spots stream in.
            var d3 = streamer != null ? streamer.blocks.FirstOrDefault(b => b.id == "D3") : null;
            if (d3 != null && Application.CanStreamedLevelBeLoaded(d3.scene))
            {
                Teleport(walker, new Vector3(-48, 2, 8));
                float until = Time.realtimeSinceStartup + 15;
                while (!streamer.IsLoaded("A3") && Time.realtimeSinceStartup < until) yield return null;
                yield return Frames(3);
                var north = Physics.RaycastAll(new Vector3(-66, 60, 46), Vector3.down, 200f, ~0, QueryTriggerInteraction.Ignore).FirstOrDefault(h => h.collider is TerrainCollider);
                if (north.collider != null) Teleport(walker, north.point);
                until = Time.realtimeSinceStartup + 20;
                while ((!streamer.IsLoaded("D3") || QingxiUpstreamClues.Current == null) && Time.realtimeSinceStartup < until) yield return null;
                Check("walking up A3's north path streams in the upstream valley D3", streamer.IsLoaded("D3") && QingxiUpstreamClues.Current != null);
                Check("the upstream brook is laid with PR #45 river tiles", GameObject.Find("UpstreamBrook (creekKit, PR #45)") is GameObject brook && brook.transform.childCount >= 15);
                var clues = QingxiUpstreamClues.Current;
                if (clues != null)
                {
                    foreach (var id in new[] { "cracked_sluice", "nursery_tracks" })
                    {
                        var spot = clues.points.First(p => p.id == id).at.position;
                        var ground = Physics.RaycastAll(spot + Vector3.up * 40, Vector3.down, 80f, ~0, QueryTriggerInteraction.Ignore).Where(h => !h.collider.isTrigger).OrderByDescending(h => h.point.y).FirstOrDefault();
                        Teleport(walker, ground.collider != null ? ground.point : spot);
                        yield return Frames(20);
                        var prompt = stations.Prompt(walker.transform.position);
                        bool read = stations.TryInteract(walker.transform.position, out var reading);
                        Check($"upstream clue {id}: prompt \"{prompt}\", reads \"{reading}\"", read && !string.IsNullOrEmpty(reading) && QingxiUpstreamClues.Seen().Contains(id));
                    }
                }
                Spot(walker, "村口");
                yield return Frames(5);
            }

            // B: the door loads joshsu54's AlchemyRoom scene; Backspace / the button returns to the door.
            Spot(walker, "溪畔丹房");
            yield return Frames(5);
            var door = stations.alchemyDoor.position;
            foraging.TryInteract(walker.transform.position, out _);
            yield return new WaitForSecondsRealtime(2f);
            Check("alchemy room loaded", SceneManager.GetActiveScene().name == QingxiAbcStations.AlchemyScene && FindFirstObjectByType<QingxiSceneReturn>() != null);
            Check("alchemy workshop present", GameObject.Find("AlchemyServices") != null);
            FindFirstObjectByType<QingxiSceneReturn>().Leave();
            yield return new WaitForSecondsRealtime(2f);
            walker = QingxiFirstPerson.Current;
            foraging = walker.GetComponent<QingxiLocalForaging>();
            Check("back in " + home, SceneManager.GetActiveScene().name == home);
            Check($"returned to the alchemy door (at {walker.transform.position}, door {door})", Vector3.Distance(walker.transform.position, door) < 1.5f);
            Check("rehearsal counts carried", foraging.Herbs == herbs);
            Check("sorting kept", QingxiReturnSorting.Session.Placements["herb"] == "save");

            // Lodging: the house door fades into the interior scene; the exit door brings the player back out.
            stations = walker.GetComponent<QingxiAbcStations>();
            if (stations.lodgingDoor != null)
            {
                var lodgingDoor = stations.lodgingDoor.position;
                Teleport(walker, lodgingDoor);
                yield return Frames(5);
                Check("lodging door prompt", (foraging.Prompt(walker.transform.position) ?? "").Contains("領地"));
                foraging.TryInteract(walker.transform.position, out _);
                yield return new WaitForSecondsRealtime(2.5f);
                walker = QingxiFirstPerson.Current;
                var inside = walker != null ? walker.GetComponent<QingxiAbcStations>() : null;
                Check("lodging interior loaded", SceneManager.GetActiveScene().name == QingxiAbcStations.LodgingScene && inside != null && inside.exitDoor != null);
                if (inside != null && inside.exitDoor != null)
                {
                    var indoorForaging = walker.GetComponent<QingxiLocalForaging>();
                    Check("counts carried indoors", indoorForaging.Herbs == herbs);
                    Teleport(walker, inside.bed.position + Vector3.right * 1.3f);
                    yield return Frames(5);
                    Check("bed offers rest", (indoorForaging.Prompt(walker.transform.position) ?? "").Contains("歇息"));
                    Teleport(walker, inside.chest.position + Vector3.left * 1.1f);
                    yield return Frames(5);
                    Check("chest can be opened", (indoorForaging.Prompt(walker.transform.position) ?? "").Contains("儲物箱"));
                    Teleport(walker, inside.training.qiPost.position + Vector3.back * .9f);
                    yield return Frames(5);
                    Check("cushion offers breathing", (indoorForaging.Prompt(walker.transform.position) ?? "").Contains("蒲團"));
                    // The room's door opens onto the hollow in front of the house; the house door leads back in.
                    if (inside.roomDoor != null && inside.houseDoor != null)
                    {
                        Teleport(walker, inside.roomDoor.position);
                        yield return Frames(5);
                        Check("the room door leads out to the yard", (indoorForaging.Prompt(walker.transform.position) ?? "").Contains("院子"));
                        indoorForaging.TryInteract(walker.transform.position, out _);
                        yield return new WaitForSecondsRealtime(1.4f);
                        Check($"out in front of the house (at {walker.transform.position}, door {inside.houseDoor.position})", Vector3.Distance(walker.transform.position, inside.houseDoor.position) < 1.5f);
                        Check("the house door leads in", (indoorForaging.Prompt(walker.transform.position) ?? "").Contains("進屋"));
                    }
                    // K23 territory: the hollow has two spirit fields and the practice post.
                    var fields = inside.fields;
                    Check("the territory has two spirit fields", fields != null && fields.fields.Length == 2);
                    if (fields != null && fields.fields.Length == 2)
                    {
                        Teleport(walker, fields.fields[0].bed.position + Vector3.back * 1.9f);
                        yield return Frames(5);
                        var fieldPrompt = indoorForaging.Prompt(walker.transform.position) ?? "";
                        Check($"the field offers planting, growth or harvest ({fieldPrompt})", fieldPrompt.Contains("種下") || fieldPrompt.Contains("生長中") || fieldPrompt.Contains("收成"));
                        if (fieldPrompt.Contains("種下"))
                        {
                            indoorForaging.TryInteract(walker.transform.position, out _);
                            yield return Frames(3);
                            Check("planting shows a growing crop", (indoorForaging.Prompt(walker.transform.position) ?? "").Contains("生長中") && fields.fields[0].crop.gameObject.activeSelf);
                            if (QingxiServerLink.Online)
                            {
                                float give = Time.realtimeSinceStartup + 10;
                                bool kept = false;
                                while (!kept && Time.realtimeSinceStartup < give)
                                {
                                    var plots = QingxiServerLink.Current.api.State.player.plots;
                                    if (plots != null) foreach (var plot in plots) if (plot.index == 0) kept = true;
                                    yield return null;
                                }
                                Check("the server keeps the planting", kept);
                            }
                        }
                        Teleport(walker, inside.training.blockPost.position + Vector3.back * 1.4f);
                        yield return Frames(5);
                        Check("the practice ground post offers blocking", (indoorForaging.Prompt(walker.transform.position) ?? "").Contains("武技格擋"));
                    }
                    Teleport(walker, inside.exitDoor.position);
                    yield return Frames(5);
                    indoorForaging.TryInteract(walker.transform.position, out _);
                    yield return new WaitForSecondsRealtime(2.5f);
                    walker = QingxiFirstPerson.Current;
                    foraging = walker.GetComponent<QingxiLocalForaging>();
                    Check($"back outside the lodging (at {walker.transform.position}, door {lodgingDoor})", SceneManager.GetActiveScene().name == home && Vector3.Distance(walker.transform.position, lodgingDoor) < 1.5f);
                    Check("counts carried back out", foraging.Herbs == herbs);
                }
            }

            var report = $"QINGXI_ABC_SMOKE {(passed ? "PASS" : "FAIL")}: " + string.Join("; ", results);
            Debug.Log(report);
            File.WriteAllText(Path.Combine(Application.persistentDataPath, "abc-smoke.txt"), report);
            Application.Quit(passed ? 0 : 1);
        }

        void Check(string what, bool ok) { results.Add((ok ? "ok " : "FAILED ") + what); passed &= ok; }

        static IEnumerator Frames(int n) { for (int i = 0; i < n; i++) yield return null; }

        static void Spot(QingxiFirstPerson walker, string name)
        {
            var index = Array.IndexOf(walker.spotNames, name);
            if (index < 0) throw new InvalidOperationException("No teleport spot " + name);
            walker.Teleport(index);
        }

        static void Teleport(QingxiFirstPerson walker, Vector3 position)
        {
            var body = walker.GetComponent<CharacterController>();
            body.enabled = false; walker.transform.position = position + Vector3.up * .1f; body.enabled = true;
        }
    }
}
