# 雲境

手機優先、Windows 共用角色的多人修仙生活 RPG。遊戲仍在原型階段。

## 目前能跑的內容

- NestJS API、PGlite 本機存檔與玩法驗證頁。
- 創角時唯一分配先天；十個現實日後才能正式測資。
- 採集、種植、煉製、共同工程、兩宗基礎師承與資產帳本原型。
- 45 項 API／持久化測試。

Unity 專案尚未通過 Editor 編譯、多人連線或手機效能驗證。詳見 [目前狀態](docs/status.md)。

## 本機啟動

```powershell
cd D:\yun-jing-rpg
powershell -ExecutionPolicy Bypass -File .\tools\start-local.ps1
```

開啟 <http://127.0.0.1:4310>。`traveler-a`、`traveler-b` 是只允許 loopback 的測試身分。不要把本機服務公開到網際網路。

```powershell
npm ci
npm test
npm run smoke
```

Unity 專案位於 `apps/game`，固定使用 `6000.0.82f1`。建置前必須先取得有效 Unity 授權。

## 主要目錄

| 路徑 | 內容 |
|---|---|
| `apps/game` | Unity 客戶端、專用區域程序與 Editor 工具 |
| `apps/inspector` | 本機玩法驗證頁 |
| `services/api` | 帳號、角色、資產與生產 API |
| `packages/content` | 道具、配方與內容定義 |
| `packages/contracts` | 共用資料契約 |
| `art` | 三視圖、Blender 母檔、匯出與驗證 |
| `tests` | API、並行、持久化與故障測試 |

開工前讀 [開發規則](AGENTS.md)、[設計基準](docs/approved-plan.md)、[目前狀態](docs/status.md)及[協作流程](CONTRIBUTING.md)。
