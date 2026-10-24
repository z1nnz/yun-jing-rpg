# 雲境 · 青溪開發版

獨立專案：`D:\yun-jing-rpg`。不依賴樹伴的程式、資料庫或登入憑證。

共同開發請先讀 [協作流程](CONTRIBUTING.md)：`@joshsu54` 接受邀請後，可開分支、提交 PR，通過自動檢查後自行合併，不必等待擁有者審查。素材交付依 [素材交接清單](docs/素材交接清單-dondon.md)。

目前交付的是第一段**可操作且會保存的玩法驗證**：出生 → 調查 → 種植 → 煉製 → 修復青溪 → 師承修行 → 啟蒙試煉。完整 3D 遊戲仍在開發。

2026-10-24 更新 v0.4：新角色自動分配先天，創角滿十個現實日後才能在廣場揭露資質；入宗前可練煉氣訣、基礎武技與採集，入宗後取得種植使用權。既有測試角色保留原進度。參見 [完整玩法修訂與建議](docs/gameplay-revision-v0.2.md)。

三件洞府模型已完成 v2 貼圖、植物／水面分層和近遠 LOD：[模型預覽與製作紀錄](art/README.md)。Unity 仍因有效授權缺失而未完成編譯驗證。

## 在這台電腦啟動

```powershell
cd D:\yun-jing-rpg
powershell -ExecutionPolicy Bypass -File .\tools\start-local.ps1
```

開啟 <http://127.0.0.1:4310>。使用 `traveler-a`、`traveler-b` 等不同測試身分；相同身分會載入原本進度並交接登入。這是 loopback 專用測試登入，不是正式帳號。

- 存檔：`.data/postgres`，關閉 API 後仍保留。不要在服務執行中複製資料目錄作備份。
- 本機生長加速 60 倍：青靈草 30 秒、淨水蓮 4 分鐘、煉製 1 秒。正式模式強制 1 倍。
- 頁面是開發驗證工具，並非最終美術或遊戲介面。
- 不同玩家各自擁有天賦、物品及田地，共用水渠和環境成果。
- 新角色不必按出生抽選：創角即分配且先隱藏確切資料。十日內可先練基礎武技／煉氣訣、採集、詢問導師、領取「問道之前」手札成果。滿十日後廣場測資再選宗；本機種植加速不縮短十日。
- 基礎材料可種植、採集或用遊戲內靈石購買；補給商人不出售天賦或突破資格。
- 入宗取得田地後，採石兩次可湊齊建池所需 6 陣基石，另需 4 靈石。蓄水池可供兩畦細流催生，或一畦深灌養根；在空田選水路後播種。未成熟作物可用青靈草照料一次增產。
- 請勿把本機服務透過通道公開到網際網路。

## Unity

用 Unity Hub 加入 `D:\yun-jing-rpg\apps\game`，版本 `6000.0.82f1`。URP、FishNet 和 Input System 由固定版本的 manifest 安裝。

```powershell
.\tools\unity.ps1 -Target Generate
.\tools\unity.ps1 -Target Windows
.\tools\start-room.ps1
```

`Generate` 產生青溪灰盒院落、URP 設定、角色 prefab、出生清單及場景。再啟動兩個 `artifacts/windows/YunJing.exe`，以不同本機身分登入，各自選擇 Join dedicated Qingxi server。角色控制為 WASD 或畫面方向鍵。

**目前 Unity Editor 啟動被有效授權檢查阻擋，這套場景產生與多人程式尚未通過 Unity 編譯／執行。** `start-room` 要等建置成功才可用。Linux Dedicated Server 模組也尚未安裝。手機真機、效能、延遲與丟包測試均待辦。Unity 開發介面暫用英文，以免未配置中文字型時無法操作。

## 驗證

```powershell
npm ci
npm test
# API 啟動後，建立一個 smoke-* 本機測試角色
npm run smoke
```

Node 22；這台電腦若找不到 npm，將 `D:\DevTools\node-v22.23.3-win-x64` 加入該終端機 PATH，或使用啟動腳本。

## 目錄

| 路徑 | 用途 |
|---|---|
| `apps/game` | Unity 原生客戶端、區域伺服器程式、Editor 場景工具 |
| `apps/inspector` | 真實 API／存檔的本機玩法驗證頁 |
| `services/api` | NestJS 身分、存檔、生產、帳本與輸送服務 |
| `packages/content` | 出生、作物、配方、宗門與道具定義 |
| `packages/contracts` | TypeScript 契約；Unity DTO 在 GameApi.cs |
| `tests` | 並行、持久保存、權限、玩法與故障邊界測試 |
| `infra` | PostgreSQL 開發容器設定 |
| `tools` | 啟動、建置與煙霧測試 |
| `art` | AI 三視圖、Blender 母檔、GLB、模型驗證與渲染預覽 |
| `docs` | 已核准設計摘要、實作狀態、架構與驗收 |

先讀 [實作狀態](docs/status.md)，再讀 [設計基準](docs/approved-plan.md) 與 [工程說明](docs/architecture.md)。完整原始方案保留在本次對話；文件中的設計摘要不是把未實作功能宣稱完成。
