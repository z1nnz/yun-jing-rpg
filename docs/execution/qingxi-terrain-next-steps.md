# 青溪地形示範區｜給 Codex 的建議步驟

2026-10-29，Claude Code 依盤點與驗收基準整理，供 Codex 實作參考；方向與完成標準以 Codex 和 z1nnz 的決定為準。

**第一個完成標準（Codex 提出）：** 角色能從村口走過分岔，到古樹和橋頭；路與草沒有疊面尖刺，房屋與石頭不懸空，山兔和互動點仍可用。做通後才用相同規則擴到小鎮、林地和山路。

驗收工具：`./tools/qingxi-terrain/check-grounding.ps1 -Config <設定>`，說明見 [`tools/qingxi-terrain/README.md`](../../tools/qingxi-terrain/README.md)。現行入口的改造前基準是失敗 38、警告 11。

## 先講好：示範區在哪個場景

兩個生成器都叫 `QingxiWorldBuilder`，內容不同：

| 生成器 | 場景 | 有什麼 |
|---|---|---|
| `YunJing.Editor.QingxiWorldBuilder`（`Assets/YunJing/Editor`） | `QingxiWorldPreview` | 村口路、分岔、古樹、木橋、平坦大方塊地基；**沒有山兔和採集互動** |
| `QingxiWorld.Editor.QingxiWorldBuilder`＋`QingxiUnifiedWorldBuilder` | `QingxiUnifiedWorld`（PR #27 已進 main） | 小鎮地形、狩獵區山兔、採草與線索、聽風台；有 NavMesh 與 `QingxiPlaySmoke` |

完成標準裡的「山兔和互動點仍可用」只存在第二個場景。建議：**地形系統寫成獨立模組，先在 `QingxiWorldPreview` 的入口一小區做通，再套進 `QingxiUnifiedWorld` 驗收山兔與互動點。** 若要直接在 UnifiedWorld 做也可以，但要先和 z1nnz 確認，避免兩個場景各改一套地面。

## 建議步驟

每一步做完都跑一次驗收，失敗數只能往下降。

### 0. 先修現有錯誤（約半天，改動小）

- `YunJing/Editor/QingxiWorldBuilder.cs:72` 的 `instance.transform.rotation = Quaternion.Euler(0, yaw, 0)` 覆蓋了 FBX 根節點的匯入旋轉，CollaboratorWorldV1 共 26 件可能因此倒下。改成 `Quaternion.Euler(0, yaw, 0) * source.transform.rotation`。順便在 Editor 裡確認這批模型看得見：我在 batchmode 截圖裡看不到它們，原因還沒查到。
- `ProjectBuilder.cs:75` 的 `Broken array` 方塊擋在分岔往橋的路上；預覽場景移除它，或把路線繞開。
- **驗收：** 「躺倒」0 項，「分岔 → 橋頭」試走通過。

### 1. 路線資料（地形之前先做）

- 新增一份路線資料（JSON），記錄每條路的中心點、寬度、表面（泥土／石板）和分岔關係，以及檢查點：村口、分岔、古樹前、橋頭。
- PWA 入口的道路資料（`tools/qingxi-trial/road-tiles.mjs`、`scene-content.mjs`）最好也讀這份，或從它產生，避免網頁版和 Unity 版的路不一樣。
- 改由這份資料產生 `tools/qingxi-terrain/checks/*.json`，驗收就不用另外手寫道路座標。
- **驗收：** 路線資料有 node 測試，至少檢查寬度大於 0、分岔有三條連到同一點、檢查點都落在路上。

### 2. 連續地形取代平坦方塊

- 用 Unity Terrain 取代 `QingxiWorldBuilder.cs:158` 的 `Walkable valley foundation`。高度由腳本產生：緩坡加河岸高差，不靠手刷，才能重建。
- 沿路線把地形壓平並順坡：路面縱坡不超過 20°，橫坡接近 0。分岔處先把三條路的範圍合併成一塊，再一次處理地表。
- 房屋地基、木橋兩端、聽風台台基周圍壓成平台，高度對齊模型底部（盤點表裡這些是「結構件」）。
- 刪掉 `Village to … path`、`approach` 這幾個平面路面方塊，基準報告裡 5 組疊面都來自它們。
- 重新烘焙 NavMesh。
- **驗收：** 道路坡度沒有失敗，「路面疊面」0 組，NavMesh 路徑能走完整條路線。

### 3. 地形材質

- 地形材質先控制在 4 層以內：草地、泥土路、碎石、河岸濕土。泥土路依路線資料自動塗上，邊緣用雜訊做不規則過渡。
- 可以參考 `art/exports/qingxi-road-props-v13` 路面貼圖的配色，當作泥土層的基準。
- **驗收：** 1.7 m 眼高截圖村口、分岔、橋頭各一張，看得出路，交界不是一刀切。

### 4. 草與小石散布

- 散布件用盤點表中的「散布件」：`qingxi-grass-v1`、`qingxi-wildflower-v1`、`qingxi-cobble-v1`、`qingxi-fern-flower-v2` 等。
- 依泥土層遮罩：路面內不長草，路緣變稀變矮，路外正常密度。手機先設保守的密度和顯示距離。
- **驗收：** 「路上有草」0 項，並記錄散布數量與 draw call。

### 5. 把模型放回地形

- 擺放件依地形高度落地：用腳印內最高點，再依盤點表的「設計埋入深度」往下沉。
- 崖壁與北邊觀景棧道要嘛讓地形長到它們底下，要嘛降到地面；目前它們離地 2 m。
- **驗收：** 「懸空」0 項；「埋太深」只剩橋梁這類已知誤報，在報告裡逐條說明。

### 6. 接回玩法（在 `QingxiUnifiedWorld`）

- 把同一套地形模組套進 UnifiedWorld，換掉它目前的鎮區地面，保留狩獵區、聽風台和採集點。
- 跑 `QingxiPlaySmoke`（山兔逃跑與捕捉）和 `QingxiLocalForagingSmoke`（採草與線索），以及 UnifiedWorld 的 Windows 建置。
- **驗收：** 兩個 smoke 都通過；驗收報告失敗 0；附玩家視角試走錄影或截圖。真機與手機效能如果沒測，就寫「未驗」。

## 不建議這一輪做的事

- 不要一次擴到整個小鎮、林地、山路。示範區做通、規則寫成資料之後再擴。
- 不要改協作者的母稿或 FBX；需要調整原點的件，擺放時補位移，再請原作者在下一版修。
- 不要把 TerrainData 這種大型二進位資產當成唯一來源；生成腳本加路線資料才是來源。

## 我（Claude Code）可以接著做的

- Codex 每完成一步，就跑驗收並把報告整理給 z1nnz；也可以審 PR 時對照本頁與 `CLAUDE_CODE_WORKFLOW.md`。
- 路線資料格式定下來後，寫一個轉換腳本，從路線資料產生驗收設定。
- 依新地形更新盤點表的分類，例如哪些結構件需要地形配合挖平。
