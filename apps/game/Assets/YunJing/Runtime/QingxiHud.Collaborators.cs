using System.Linq;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace YunJing
{
    // HUD panels for the collaborator zones: Johnnnny0823's forest encounter read-out and
    // Eli-0731's return sorting table. Both show local rehearsal state only.
    public sealed partial class QingxiHud
    {
        public QingxiForestEncounter forest;
        public QingxiAbcStations stations;

        GameObject encounterPanel, sortingPanel;
        Text encounterState, encounterHp, encounterMessage, sortingBody, sortingMessage;
        bool sortingOpen;

        void BuildCollaboratorPanels()
        {
            // Journal shortcuts to the three collaborator zones (spots added by the novice-village builder).
            var journalPage = journal.GetComponent<RectTransform>();
            journalPage.sizeDelta += new Vector2(0, 64);
            var zones = new[] { "林地遭遇", "溪畔丹房", "回村分揀桌" };
            for (int i = 0; i < zones.Length; i++)
            {
                var index = System.Array.IndexOf(walker.spotNames, zones[i]);
                if (index < 0) continue;
                Action("Go " + zones[i], journalPage, zones[i], new Vector2(0, 0), new Vector2(28 + i * 152, 87),
                    new Vector2(140, 46), () => { walker.Teleport(index); ToggleJournal(); });
            }

            if (forest != null)
            {
                var panel = Panel("Forest Encounter", safe, new Vector2(.5f, 1), new Vector2(.5f, 1),
                    new Vector2(0, -92), new Vector2(600, 140), new Color(.035f, .07f, .09f, .84f));
                Label("Encounter Title", panel, "林地山兔遭遇 · 本機演練（A：Johnnnny0823）", 17, FontStyle.Bold,
                    new Vector2(16, -9), new Vector2(570, 26), new Color(.94f, .87f, .66f));
                encounterState = Label("Encounter State", panel, "", 16, FontStyle.Normal,
                    new Vector2(16, -37), new Vector2(570, 44), new Color(.9f, .93f, .88f));
                encounterHp = Label("Encounter HP", panel, "", 15, FontStyle.Bold,
                    new Vector2(16, -80), new Vector2(150, 24), new Color(.95f, .62f, .52f));
                encounterMessage = Label("Encounter Message", panel, "", 14, FontStyle.Normal,
                    new Vector2(166, -80), new Vector2(420, 24), new Color(.67f, .87f, .83f));
                Label("Encounter Keys", panel, "J／左鍵 攻擊 · Q 試招 · 按住 K／右鍵 格擋 · C 閃避 · R 回安全點", 13, FontStyle.Normal,
                    new Vector2(16, -108), new Vector2(570, 24), new Color(.75f, .8f, .78f));
                encounterPanel = panel.gameObject;
                encounterPanel.SetActive(false);
            }

            if (stations != null)
            {
                var page = Panel("Return Sorting", safe, new Vector2(.5f, .5f), new Vector2(.5f, .5f),
                    Vector2.zero, new Vector2(620, 420), new Color(.055f, .095f, .10f, .97f));
                Label("Sorting Title", page, "回村分揀桌 · 本機展示（C：Eli-0731）", 24, FontStyle.Bold,
                    new Vector2(26, -20), new Vector2(570, 36), new Color(.94f, .87f, .65f));
                sortingBody = Label("Sorting Body", page, "", 16, FontStyle.Normal,
                    new Vector2(26, -62), new Vector2(570, 120), new Color(.9f, .92f, .87f));
                sortingMessage = Label("Sorting Message", page, "", 15, FontStyle.Normal,
                    new Vector2(26, -186), new Vector2(570, 26), new Color(.67f, .87f, .83f));
                var samples = QingxiReturnSorting.Samples;
                for (int i = 0; i < samples.Length; i++)
                {
                    var id = samples[i].id;
                    Action("Pick " + id, page, samples[i].symbol + " " + samples[i].name, new Vector2(0, 0),
                        new Vector2(26 + i * 192, 150), new Vector2(180, 46), () => Sort(QingxiReturnSorting.Session.Select(id)));
                }
                var destinations = QingxiReturnSorting.Destinations;
                for (int i = 0; i < destinations.Length; i++)
                {
                    var id = destinations[i].id;
                    Action("Put " + id, page, destinations[i].label, new Vector2(0, 0),
                        new Vector2(26 + i * 192, 92), new Vector2(180, 46), () => Sort(QingxiReturnSorting.Session.MoveTo(id)));
                }
                Action("Undo Sorting", page, "取消最近一次", new Vector2(0, 0), new Vector2(26, 26),
                    new Vector2(180, 46), () => Sort(QingxiReturnSorting.Session.Undo()));
                Action("Close Sorting", page, "收起分揀桌", new Vector2(0, 0), new Vector2(410, 26),
                    new Vector2(180, 46), () => SetSorting(false));
                sortingPanel = page.gameObject;
                sortingPanel.SetActive(false);
                stations.SortingRequested += () => SetSorting(true);
                RefreshSorting("選一份樣本，再選去向；三個選項都自由，沒有每日清單。");
            }
            BuildWaterPanel();
        }

        void UpdateCollaboratorPanels()
        {
            if (encounterPanel != null)
            {
                bool show = forest.PlayerInside && !open && !sortingOpen;
                if (encounterPanel.activeSelf != show) encounterPanel.SetActive(show);
                if (show && forest.Rules != null)
                {
                    var r = forest.Rules;
                    var timing = r.WindupLeft > 0 ? $"（{r.WindupLeft:0.0} 秒後衝刺）" : r.OpeningLeft > 0 ? $"（破綻剩 {r.OpeningLeft:0.0} 秒）" : "";
                    encounterState.text = (forest.Climbed ? "觀察台上：山兔碰不到你。" : "") + forest.StateLabel + timing;
                    encounterHp.text = "氣血 " + new string('●', Mathf.Max(0, r.player.hp)) + new string('○', Mathf.Max(0, r.P.playerHp - r.player.hp));
                    encounterMessage.text = forest.MessageFresh ? forest.Message : "";
                }
            }
            UpdateWaterPanel();
            if (sortingOpen && UnityEngine.InputSystem.Keyboard.current != null && UnityEngine.InputSystem.Keyboard.current.escapeKey.wasPressedThisFrame)
                SetSorting(false);
        }

        void SetSorting(bool value)
        {
            if (sortingPanel == null || sortingOpen == value) return;
            sortingOpen = value;
            sortingPanel.SetActive(value);
            stations.SortingOpen = value;
            walker.SetMenuOpen(value);
            if (EventSystem.current != null)
                EventSystem.current.SetSelectedGameObject(value ? sortingPanel.transform.Find("Close Sorting")?.gameObject : journalButton.gameObject);
        }

        void Sort(QingxiReturnSorting.Result result) => RefreshSorting(result.message);

        void RefreshSorting(string message)
        {
            var s = QingxiReturnSorting.Session;
            var lines = QingxiReturnSorting.Samples.Select(x =>
                (s.Selected == x.id ? "▶ " : "　") + $"{x.name}　來源：{x.source}　目前：{QingxiReturnSorting.Label(s.Placements[x.id])}");
            var recent = s.Journal.Skip(System.Math.Max(0, s.Journal.Count - 2))
                .Select(e => (e.kind == "undo" ? "取消→" : "→") + QingxiReturnSorting.Find(e.sample).symbol + QingxiReturnSorting.Label(e.to));
            sortingBody.text = string.Join("\n", lines) + "\n手札：" + (s.Journal.Count == 0 ? "尚無紀錄" : string.Join("　", recent))
                + "\n（樣本是固定展示身分，不是背包材料；交委託只放進封條盒，不完成委託或給獎）";
            sortingMessage.text = message;
        }
    }
}
