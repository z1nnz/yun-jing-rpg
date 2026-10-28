# 青溪地形改造｜盤點與驗收工具

2026-10-29，z1nnz 指導、Claude Code 實作。青溪入口要從「平坦方塊＋道路網格」改成連續地形、路線資料與散布（由 Codex 實作，見 `apps/game/Assets/YunJing/Editor/QingxiWorldBuilder.cs`）。這個資料夾只放**量測與檢查工具**，不改任何場景生成器或協作者模型。

| 欄位 | 內容 |
|---|---|
| 玩家目標 | 從村口走過分岔、到古樹與橋頭，路面與草不疊面、模型不懸空 |
| 輸入 | `art/exports/**/*.glb`、Unity `Assets/YunJing/Models/**/*.fbx`、生成後的場景 |
| 輸出 | 模型盤點表、Unity 驗收報告、協作者接地規格（[`2026-10-29/14`](../../docs/execution/2026-10-29/14-grounding-spec.md)）、[給 Codex 的下一步](../../docs/execution/qingxi-terrain-next-steps.md) |
| 邊界 | 唯讀；不修改場景、生成器、母稿或 `tools/unity.ps1` |
| 完成條件 | 地形示範區的驗收報告「失敗」為 0，警告逐條說明理由 |

## 模型盤點

```powershell
node tools/qingxi-terrain/asset-inventory.mjs           # 產生 asset-inventory.json 與 docs/execution/qingxi-terrain-asset-inventory.md
node tools/qingxi-terrain/asset-inventory.mjs --check   # 輸出是否過期
node --test tools/qingxi-terrain/asset-inventory.test.mjs
./tools/qingxi-terrain/check-grounding.ps1 -Inventory   # 在 Unity 量測只有 FBX 的模型，寫 unity-models.json
```

每件模型分成：直接擺放、調整接地、散布件、結構件（保留模型）、交給地形。結果見 [`docs/execution/qingxi-terrain-asset-inventory.md`](../../docs/execution/qingxi-terrain-asset-inventory.md)。

## Unity 驗收

```powershell
./tools/unity.ps1 -Target WorldPreview                  # 先生成場景
./tools/qingxi-terrain/check-grounding.ps1              # 預設設定 checks/qingxi-world-preview.json
```

報告寫到 `artifacts/terrain-check/<設定名>.md`；有失敗時結束碼為 1。檢查項目：

| 檢查 | 失敗條件 |
|---|---|
| 躺倒 | 擺放的 FBX 根節點匯入旋轉被覆蓋（Z 軸向上的 FBX 會因此倒下） |
| 懸空 | 模型底部比腳印內最高的地面還高 5 cm 以上 |
| 路上有草 | 草類物件或地形細節落在道路寬度內（邊緣容許 0.15 m） |
| 道路坡度 | 沿路取樣，縱坡超過 35°（20° 以上為警告） |
| 路面疊面 | 兩個平面路面網格重疊且頂面高差在 6 cm 內（警告） |
| 路線試走 | 檢查點之間以角色膠囊（半徑 0.3 m）直線試走：沒有地面、一步高差過大或被碰撞體擋住；有 NavMesh 時另算完整路徑 |

道路、檢查點與路線寫在 `checks/*.json`。Codex 的路線資料定案後，請改由路線資料產生這份設定，兩邊才不會各寫一套。

### 已知誤報

- **埋太深（警告）**：橋梁的走道碰撞是另一個物件，高於橋身底部，所以橋會被報成埋太深。結構件的這類警告可以忽略。
- **道路坡度**：「地面」取的是最高的碰撞體，路上若有障礙物，坡度會一起變陡；這通常代表路被擋住，仍值得看。
- 草類物件以名稱判斷（`grassPattern`），沒命名的草不會被檢查到。

## 改造前基準（2026-10-29，現行 `QingxiWorldPreview`）

失敗 38、警告 11。主要發現：

1. **CollaboratorWorldV1 共 26 件可能躺倒**（房屋、石橋、石階、山路、崖壁、宗門、洞口、松、竹、苔石）。`QingxiWorldBuilder.cs:72` 用 `Quaternion.Euler(0, yaw, 0)` 覆蓋了 FBX 根節點的匯入旋轉。照原旋轉量測這些模型都是正立、底部在 0；去掉旋轉後，例如石板山路會變成 6 m 高、0.32 m 厚。建議改成 `Quaternion.Euler(0, yaw, 0) * source.transform.rotation`。**尚未用畫面確認**：我在 batchmode 的截圖裡完全看不到這批模型，原因待查。
2. 三座崖壁與北邊觀景棧道放在離地約 2 m 處，底下沒有地面。
3. 開發場景的 `Broken array`（`ProjectBuilder.cs:75`，2×0.8×2 m 方塊）正好擋在分岔往橋的路上。
4. 五組平面路面互相重疊，頂面高差 0–1 cm，這就是會閃爍、穿插的疊面。
5. 橋頭坡道接主路處縱坡 36°，略超過可走上限。
6. 場景沒有 NavMesh，路線只做直線試走。

## 尚未驗證

- 沒有在有圖形裝置的 Editor 或建置版中目視確認「躺倒」。
- 盤點分類是名稱與比例的自動判斷加少量人工判斷，擺到新地形後仍要看玩家視角。
- 沒有手機效能量測。
