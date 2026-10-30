# TI18 新手領地屋內互動展示（Unity 6000.0.85f1）

展示用場景：物品、丹藥品階都只在本場景內，不入正式存檔；正式的物品、修為、世界狀態由伺服器決定，核心組來接。

## 房間介面
- 淨尺寸 7 m 寬 × 5 m 深 × 3.2 m 高，前後門各 1.2 m 寬 × 2.2 m 高，置中。
- 房殼為佔位幾何（`Room_Placeholder_Not_Delivered`），不屬交付素材。

## 家具格位（工作單 02-B §3）
與 Blender 審圖（`art/previews/territory-interior-b/room/layout_check.json`）同一套擺法。三處照實際尺寸讓位：

| 格位 | 工作單 | 場景 | 原因 |
|---|---|---|---|
| `TI_Shelf` | (3.25, −0.6) 面向 −x | 相同 | |
| `TI_Desk` | (−2.6, −1.6) 面向 +x | 相同 | |
| `TI_Furnace` | (2.7, −1.9) 面向 −x | 相同 | |
| `TI_Lamp_1` | (−1.6, 2.1) | 相同 | |
| `TI_Lamp_2` | (1.9, −2.1) | (1.45, −2.1) | 1.9 會擋住丹爐前方的站位；左移 0.45 m 留出 0.6 m 站位 |
| `TI_Screen` | (−1.4, 0.4) | (−1.2, 0.4) | 床長 2.12 m，−1.4 會和床尾重疊 15 cm；右移後留 6 cm 空隙。畫面朝書案，背面朝床 |
| `TI_Rug` | (0.6, 0.0) | 相同 | |
| `TI_Curtain_F`／`_B` | 前、後門 | 前門 z −2.5、後門 z 2.5 | 前門簾加一個只給鏡頭用的碰撞盒，鏡頭停在簾內，不會從屋外穿看進來 |
| 床 | (−2.75, 1.0) 朝向 90° | 位置相同，長邊沿左牆 | 床長 2.12 m、中心離牆 0.75 m，轉 90° 會穿牆 0.31 m |
| 儲物箱 | (2.6, 1.9) 180° | 相同 | |
| 蒲團 | (1.2, −0.2) 0° | 相同 | |

## 旅途手札
- 書案前按 E：鏡頭先看向桌上的手札，再出現一本線裝書；封面翻開、紙頁一頁一頁翻、合上都有動畫。
- 書脊在右，跟舊式線裝書一樣，從右頁讀到左頁，紙頁由左往右翻。共 8 頁（4 個對頁），目前每頁都是空白的朱絲欄紙，只有頁碼。
- 頁面文字放在 `JournalDesk.pageText`（第 1 頁＝索引 0），之後世界觀介紹寫好，填進去就會顯示；要做成自動播放的介紹動畫，可以直接用 `Journal` 的翻頁時序。

## 操作
| 動作 | 鍵盤滑鼠 | 橫向觸控 |
|---|---|---|
| 走動 | WASD（相對鏡頭） | 左半螢幕按住拖曳＝浮動搖桿 |
| 轉視角 | 滑鼠（按住 Alt 放開游標）、滾輪拉近 | 右半螢幕拖曳 |
| 互動 | E | 右下互動鈕（字樣跟隨提示） |
| 收藏架 | E 打開；點乾坤袋裡一件再點空格＝擺上；點架上一格再點空格＝換格；選格後「拿下」 | 同左（點按） |
| 旅途手札 | 書案前按 E 翻開；→／D 下一頁，←／A 上一頁 | 書下方的按鈕 |
| 關箱子／收藏架／手札／離開丹爐 | Esc 或面板按鈕（手札也可按 E） | 面板按鈕 |
| 丹爐快轉 | 按住 F | — |

觸控介面在偵測到第一次觸控後才出現；鍵鼠遊玩不受影響。行動版設定只允許橫向。

## 程式結構
- `Assets/Scripts/Logic/`（組件 `TI18.Logic`）：純狀態邏輯，不碰場景。
  - `Items.cs`：疊放（上限 99）、容量、取出、整理排序、分類分頁。
  - `HomeAlchemy.cs`：煉丹爐規則，沿用 Alchemy V2 常數與評分。
  - `TouchStick.cs`：觸控左右分區、搖桿死區、視角拖曳換算。
  - `Shelf.cs`：收藏架 8 格規則（從乾坤袋擺上、換格、拿下；同一件不會在兩格、拿下再放不會複製、重送不重複）。
  - `Journal.cs`：旅途手札的翻開、翻頁、合上（動畫進行中不接受操作；頁數補成整數對頁）。
- `Assets/Scripts/`：畫面與互動（箱子、收藏架、手札、丹爐、燈、床、鏡頭、介面、觸控覆蓋層）。
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
"$U" -batchmode -quit -projectPath "$(cygpath -w $PWD)" -executeMethod DemoRecorder.RecordShort -logFile Logs/short.log   # 1 分鐘內短版
```

## 已驗證／未驗證
- 已驗證：EditMode 30 項測試通過（2026-10-30，含收藏架 9 項、手札 5 項）；批次建置場景與錄影；場景家具外框與 `art/previews/territory-interior-b/room/layout_check.json` 數字一致。
- 未驗證：實機觸控（目前只有邏輯測試與程式路徑，未在手機或平板上實測）、效能、打包。
- 伺服器接線提案見 [CONTRACT.md](CONTRACT.md)。

## 尚未完成（對照工作單 02-B）
- 手札的世界觀介紹內容與動畫（等世界觀定稿）。
- 與 Codex C2 室內套件的並排比較（等 C2 交件）。
- 文字搬到 `packages/content`（核心組決定格式後）。

## 錄影
`art/previews/territory-interior-b/demo/` 下有兩支：
- `TI18_InteriorShort_v001.mp4`：工作單要的 1 分鐘內短版。依序是推門（角色穿過前門簾，門簾被推開後擺回）、點燈、把卷軸擺上收藏架、添柴點丹爐。
- `TI18_InteriorDemo_v009.mp4`：完整走一遍，包含箱子、收藏架、煉丹、燈、手札、床。

門簾的擺動是 `CurtainSway`：角色穿過門口時，門簾往角色行進的方向推開，再像彈簧一樣擺回靜止。遊玩時活動範圍只到門內，走近門口時門簾會被推動，但走不出去。
