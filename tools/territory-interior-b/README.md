# TI18 新手領地屋內互動展示（Unity 6000.0.85f1）

展示用場景：物品、丹藥品階都只在本場景內，不入正式存檔；正式的物品、修為、世界狀態由伺服器決定，核心組來接。

## 房間介面
- 淨尺寸 7 m 寬 × 5 m 深 × 3.2 m 高，前後門各 1.2 m 寬 × 2.2 m 高，置中。
- 房殼為佔位幾何（`Room_Placeholder_Not_Delivered`），不屬交付素材。

## 操作
| 動作 | 鍵盤滑鼠 | 橫向觸控 |
|---|---|---|
| 走動 | WASD（相對鏡頭） | 左半螢幕按住拖曳＝浮動搖桿 |
| 轉視角 | 滑鼠（按住 Alt 放開游標）、滾輪拉近 | 右半螢幕拖曳 |
| 互動 | E | 右下互動鈕（字樣跟隨提示） |
| 收藏架 | E 打開；點乾坤袋裡一件再點空格＝擺上；點架上一格再點空格＝換格；選格後「拿下」 | 同左（點按） |
| 關箱子／收藏架／離開丹爐 | Esc 或面板按鈕 | 面板按鈕 |
| 丹爐快轉 | 按住 F | — |

觸控介面在偵測到第一次觸控後才出現；鍵鼠遊玩不受影響。行動版設定只允許橫向。

## 程式結構
- `Assets/Scripts/Logic/`（組件 `TI18.Logic`）：純狀態邏輯，不碰場景。
  - `Items.cs`：疊放（上限 99）、容量、取出、整理排序、分類分頁。
  - `HomeAlchemy.cs`：煉丹爐規則，沿用 Alchemy V2 常數與評分。
  - `TouchStick.cs`：觸控左右分區、搖桿死區、視角拖曳換算。
  - `Shelf.cs`：收藏架 8 格規則（從乾坤袋擺上、換格、拿下；同一件不會在兩格、拿下再放不會複製、重送不重複）。
- `Assets/Scripts/`：畫面與互動（箱子、丹爐、燈、床、鏡頭、介面、觸控覆蓋層）。
- `Assets/Tests/EditMode/`：上述邏輯的自動測試。

## 指令
第一次打開前，先把模型與貼圖從 `art/exports/territory-interior-b/`、`art/incoming/dondon/` 複製進來（只複製本體，`.meta` 已在版本庫）：
```powershell
powershell -ExecutionPolicy Bypass -File tools/territory-interior-b/sync_art.ps1
```
以下在 `tools/territory-interior-b/` 下執行（Git Bash）：
```bash
U="C:/Program Files/Unity/Hub/Editor/6000.0.85f1/Editor/Unity.exe"
"$U" -batchmode -projectPath "$(cygpath -w $PWD)" -runTests -testPlatform EditMode -testResults "$(cygpath -w $PWD)/Logs/editmode_results.xml" -logFile Logs/tests.log
"$U" -batchmode -quit -projectPath "$(cygpath -w $PWD)" -executeMethod DemoRecorder.Preview -logFile Logs/preview.log
"$U" -batchmode -quit -projectPath "$(cygpath -w $PWD)" -executeMethod DemoRecorder.Record -logFile Logs/record.log
```

## 已驗證／未驗證
- 已驗證：EditMode 25 項測試通過（2026-10-30，含收藏架 9 項）；批次建置場景與錄影。
- 未驗證：實機觸控（目前只有邏輯測試與程式路徑，未在手機或平板上實測）、效能、打包。
- 伺服器接線提案見 [CONTRACT.md](CONTRACT.md)。

## 尚未完成（對照工作單 02-B）
- 打開書案上的旅途手札。
- 格位照工作單：`TI_Lamp_2` (1.9, −2.1)、`TI_Screen` (−1.4, 0.4)、前門門簾 `TI_Curtain_F`；床朝向 90°。
- 錄影縮到 1 分鐘內（推門、點燈、擺收藏、點丹爐）。
- 模型 LOD1／LOD2 比例調到約 50%／15%；四向審圖加 1.75 m 人形比例尺。
