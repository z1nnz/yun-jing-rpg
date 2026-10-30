using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace YunJing
{
    // The creek chapter's two choice panels: the old channel (three ways to bring the water back, PR #52 pieces)
    // and the water-council corner (three things to tell the village, PR #47 corner). One panel, three options,
    // filled from QingxiWaterworksSite / QingxiVillageReport when a station opens it.
    public sealed partial class QingxiHud
    {
        GameObject waterPanel;
        Text waterTitle, waterBody, waterMessage;
        readonly Text[] waterCaptions = new Text[3];
        string waterKind;
        bool waterOpen;

        void BuildWaterPanel()
        {
            if (stations == null) return;
            var page = Panel("Creek Choice", safe, new Vector2(.5f, .5f), new Vector2(.5f, .5f),
                Vector2.zero, new Vector2(620, 380), new Color(.055f, .095f, .10f, .97f));
            waterTitle = Label("Creek Choice Title", page, "", 24, FontStyle.Bold, new Vector2(26, -20), new Vector2(570, 36), new Color(.94f, .87f, .65f));
            waterBody = Label("Creek Choice Body", page, "", 16, FontStyle.Normal, new Vector2(26, -62), new Vector2(570, 70), new Color(.9f, .92f, .87f));
            for (int i = 0; i < 3; i++)
            {
                int index = i;
                var button = Action("Creek Option " + i, page, "", new Vector2(0, 0), new Vector2(26, 238 - i * 58), new Vector2(570, 48), () => ChooseWater(index));
                waterCaptions[i] = button.GetComponentInChildren<Text>();
            }
            waterMessage = Label("Creek Choice Message", page, "", 15, FontStyle.Normal, new Vector2(26, -300), new Vector2(570, 48), new Color(.67f, .87f, .83f));
            Action("Close Creek Choice", page, "先不決定", new Vector2(0, 0), new Vector2(410, 22), new Vector2(180, 40), () => SetWater(null));
            waterPanel = page.gameObject;
            waterPanel.SetActive(false);
            stations.ChoiceRequested += SetWater;
        }

        void SetWater(string kind)
        {
            if (waterPanel == null) return;
            bool open = kind != null;
            waterKind = kind;
            if (open)
            {
                bool works = kind == "waterworks";
                waterTitle.text = works ? "舊水路・怎麼把水引回來" : "議水桌・說說上游看到的事";
                waterBody.text = works ? "工匠和村民圍在閘門旁。三個做法都可以，選了就動工。" : "桌邊坐著洗衣的阿嬸、老石匠，還有一個蹲在旁邊的小孩。";
                for (int i = 0; i < 3; i++)
                    waterCaptions[i].text = works ? QingxiWaterworksSite.Choices[i].label + "：" + QingxiWaterworksSite.Choices[i].line : QingxiVillageReport.Reports[i].label;
                foreach (var t in waterCaptions) { t.fontSize = 15; t.fontStyle = FontStyle.Normal; }
                waterMessage.text = works ? QingxiWaterworksSite.NotYet() ?? "" : QingxiVillageReport.NotYet() ?? "";
            }
            if (waterOpen == open) return;
            waterOpen = open;
            waterPanel.SetActive(open);
            stations.SortingOpen = open;   // the stations stay quiet while a panel is up
            walker.SetMenuOpen(open);
            if (EventSystem.current != null)
                EventSystem.current.SetSelectedGameObject(open ? waterPanel.transform.Find("Creek Option 0")?.gameObject : journalButton.gameObject);
        }

        void ChooseWater(int index)
        {
            string message = waterKind == "waterworks"
                ? QingxiWaterworksSite.Current?.Choose(QingxiWaterworksSite.Choices[index].id)
                : QingxiVillageReport.Current?.Tell(QingxiVillageReport.Reports[index].id);
            if (message != null) waterMessage.text = message;
        }

        void UpdateWaterPanel()
        {
            if (waterOpen && UnityEngine.InputSystem.Keyboard.current != null && UnityEngine.InputSystem.Keyboard.current.escapeKey.wasPressedThisFrame)
                SetWater(null);
        }
    }
}
