# 第 1 天・在家泡茶 v1（工作包 B，joshsu54）

輕鬆、短的泡茶玩法。茶亭老人教過以後，回家在茶爐（格位 `TI_TeaStove`，模型 TI09）泡一壺茶：

1. **選茶與分量**：可選青溪野茶或梅花茶，放 1–5 匙。
2. **煮水**：火候分小、中、大三段（也可以熄火）。面板不顯示溫度，只描述壺口的蒸汽：
   - 無聲無煙
   - 壺口微煙
   - 一沸・魚目
   - 二沸・連珠
   - 三沸・騰波
3. **投茶**：水沖進壺裡，開始浸泡。投茶當下的水溫就是沖泡溫度，看蒸汽判斷。
4. **出湯**：看湯色決定什麼時候倒。太早倒會淡，太晚倒會苦。

結果分成淡、好、苦三種，每杯都會喝下並得到休息加成，不會浪費任何東西。還沒投茶就放棄的話，茶葉會全部退回。

## 交付檔案

| 檔案 | 內容 |
|---|---|
| `packages/content/tea-brewing-v1.json` | 全部參數：火候、蒸汽分段、兩種茶的理想水溫／分量／濃度窗、萃取、結果加成、建議文字 |
| `services/api/src/tea.ts` | 規則：`validateLog`、`simulate`（每 0.1 秒一格的固定步長重播）、`judge`、`steamAt` |
| `services/api/src/game.ts` | 動作：`tea-lesson`、`tea-begin`、`tea-abandon`、`tea-finish`；快照中的 `tea` 檢視 |
| `packages/contracts/types.ts` | `TeaState`、`TeaView`、`TeaBrew` 型別 |
| `tests/tea.test.ts`、`tests/tea-cases.ts` | 7 項測試，見下方「已驗證」 |
| `tests/fixtures/tea-trace.json`、`tools/tea-fixture.ts` | 9 組重播案例，由 TS 產生，Unity 拿來檢查 C# 版本 |
| `apps/game/Assets/YunJing/Runtime/Tea/TeaSim.cs` | `simulate`／`judge` 的 C# 移植（`TeaPot`），與伺服器的運算順序相同 |
| `apps/game/Assets/YunJing/Runtime/Tea/TeaBrewingPanel.cs` | 泡茶面板：選茶 → 煮水 → 浸泡 → 結果；壺口蒸汽粒子會隨分段變化 |
| `apps/game/Assets/YunJing/Runtime/Tea/TeaPlaytest.cs` | `-teaPlaytest` 腳本試玩：泡三壺，加上一次放棄，邊玩邊存影格 |
| `apps/game/Assets/YunJing/Editor/TeaRoomBuilder.cs` | 產生茶室場景、執行 `VerifySim`、建置 Windows 版 |
| `QingxiAbcStations.cs`、`QingxiLodgingInteriorBuilder.cs` | 借住處內新增 `TI_TeaStove` 格位（x .3、z 2.0、yaw 180，靠後牆）。走近按 F 打開面板；喝過茶再躺床，提示文字會帶出恢復倍率 |
| `art/exports/tea-brewing-b/` | TI09、RK04、TI10 的 FBX、貼圖、model_info、validation |

## 數值（tea-brewing-v1.json）

**煮水到各分段需要的秒數**（起始 20 °C）：

| 火候 | 微煙 55 °C | 魚目 72 °C | 連珠 85 °C | 騰波 96 °C |
|---|---|---|---|---|
| 小火 | 40 s | 70 s | 103 s | 147 s |
| 中火 | 18 s | 28 s | 37 s | 45 s |
| 大火 | 9 s | 14 s | 18 s | 22 s |

**兩種茶的設定**：

| 茶 | 理想水溫 | 理想分量 | 好的浸泡秒數 |
|---|---|---|---|
| 青溪野茶 | 85–96 °C（二沸） | 3 匙 | 中火煮到 90 °C 再投茶時：3 匙 31–72 s；4 匙 21–40 s；2 匙 60 s 以上 |
| 梅花茶 | 72–86 °C（魚目） | 2 匙 | 78 °C 投茶時：2 匙 20–38 s；3 匙 13–22 s；1 匙 48 s 以上 |

**規則細節**：
- **燙傷**：投茶時水溫高於該茶上限，每多 1 °C，濃度一次加 0.8。用滾水泡梅花茶，會把原本「好」的浸泡時間推成「苦」。
- **水太冷**：投茶時低於 60 °C，萃取只剩四分之一，怎麼泡都是淡，建議文字為「水溫不夠」。

**結果與休息加成**：好 ×1.25、淡 ×1.05、苦 ×1.0，持續 30 分鐘（`restBonusMinutes`，以遊戲速度換算）。
- 目前只是參數：存在 `player.tea.restBonus`，快照中可讀到。
- 躺床療傷尚未接上，借住處的床只會顯示倍率提示。

**建議文字**：
- 淡：依原因顯示「出湯太早」「水溫不夠」「茶葉少了」。
- 苦：依原因顯示「出湯太晚」「水太滾」「茶葉太多」。

## 伺服器流程

1. `tea-lesson`：茶亭老人教學，發給青溪野茶與梅花茶各 4 份（綁定），只能領一次。
2. `tea-begin { tea, scoops }`：必須先學過，扣掉茶葉，鎖定這一壺。
3. `tea-finish { log }`：檢查紀錄合法、紀錄時長不超過實際經過的時間，伺服器重算結果並記錄，休息加成換成這一杯的倍率。
4. `tea-abandon`：茶葉全部退回。

紀錄格式：`[{t, k:'fire', v:0..3}, …, {t, k:'leaves'}, {t, k:'pour'}]`，`t` 以 0.1 秒為單位。

## 執行

```bash
npm test
```

```bash
"C:/Program Files/Unity/Hub/Editor/6000.0.85f1/Editor/Unity.exe" -batchmode -quit -projectPath apps/game -executeMethod YunJing.Editor.TeaRoomBuilder.BuildWindows -logFile artifacts/unity-tea-build.log
```

```bash
artifacts/tea-windows/YunJingTea.exe -screen-width 1280 -screen-height 720 -screen-fullscreen 0 -teaPlaytest -teaOut artifacts/tea-playtest
```

面板操作：
- **選茶**：Q／E 換茶，A／D 調分量，空白鍵上爐。
- **煮水**：1–4 對應熄火／小火／中火／大火，空白鍵投茶。
- **浸泡**：空白鍵出湯。
- **任何時候**：Esc 離開；還沒投茶的話，茶葉會退回。

## 已驗證

- `npm test` 全部 82 項通過，其中 7 項是泡茶：
  - 紀錄格式檢查。
  - 三段火候的快慢與蒸汽分段。
  - 太早淡、適時好、太晚苦，結果只會依序前進。
  - 水溫與分量造成的結果和建議文字。
  - 伺服器流程：學習、開始、放棄退回、好與苦都計入、加成到期。
  - 重播案例與 TS 一致。
  - C# 常數與 JSON 一致。
- Unity 6000.0.85f1 批次模式：
  - `TEA_SIM_PASS 9/9`：C# 的 TeaPot 重播 9 組案例，結果、分數、濃度、沖泡水溫與 TS 一致。
  - `TEA_BUILD_PASS`：產生 `YunJingTea.exe`。
- Windows 建置執行 `-teaPlaytest`，1280×720，19 項全部通過：
  1. 青溪野茶 3 匙，中火煮到二沸，85.6 °C 投茶，浸泡 52.8 s 後出湯：好，100 分。
  2. 梅花茶 2 匙，大火煮到三沸，97.4 °C 投茶：苦，建議為「水太滾」。
  3. 梅花茶在魚目時投茶，浸泡 10.7 s 就出湯：淡，建議為「出湯太早」。
  4. 還沒投茶就放棄：茶葉退回。
- 錄影與截圖在 `docs/execution/tea-brewing-v1-playtest/`：
  - `tea-brewing-v1-playtest.mp4`：每 0.2 秒存一張影格，共 950 張，以 10 fps 合成，等於 2 倍速。
  - 各步驟的截圖。
  - `tea-playtest.json`：試玩報告。
- 試玩畫面是獨立的茶室場景（`TeaRoomBuilder`），擺的是 TI09 模型。借住處裡的 `TI_TeaStove` 格位與按 F 打開面板的程式已經寫好，但這輪沒有重新產生借住處場景，也沒有實際走過去按鍵。

## 未驗證／待辦

- 借住處的室內場景還是本機演練，沒有接到伺服器。
  - 面板的茶葉庫存是本機副本。
  - 面板記下的紀錄格式和 `tea-finish` 相同，但還沒送出。

## 不在本次範圍

- **躺床療傷系統**：工作包寫「先寫成參數」，本次只交 `player.tea.restBonus`，療傷系統由之後實作的人讀取。
- **茶亭老人 NPC**：工作包只把它當玩法前提，B 包要交的東西裡沒有它。之後做 NPC 的人接上 `tea-lesson` 這個入口即可。
- TI09 茶爐模型自評 88 分，美術還沒達到 95 分的標準；RK04、TI10 也還沒擺進 Unity 場景。
- 試玩是腳本按面板按鈕，不是實體鍵鼠或觸控輸入。
