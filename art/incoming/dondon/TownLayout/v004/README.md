# TownLayout（TownLayout v004）

《雲境》交接第 2 批 · 場景配置參考。來源：[joshsu54/dondon2.0](https://github.com/joshsu54/dondon2.0) `Models/TownLayout/v004`，提交 `4644558`；檔案與來源逐一比對 SHA-256 相同。

## 檔案

| 檔案 | 用途 |
| --- | --- |
| `01_town_overview.png` | 建模後渲染圖 |
| `02_town_top_plan.png` | 建模後渲染圖 |
| `03_north_street_archway.png` | 建模後渲染圖 |
| `04_garden_connection.png` | 建模後渲染圖 |
| `layout_info.json` | 場景配置資料 |
| `TownLayout_v004.blend` | 可編輯原檔 |
| `TownLayout_v004.fbx` | 引擎交換檔 |
| `handoff_check.json` | 本次交接在 Blender 實際重開與 FBX 回匯的結果 |
| `previews/TownLayout_v004_render_512.png` | 建模後渲染圖（縮為 512 px），不是設計參考 |
| `placements.json` | 本次從 .blend 讀出的物件擺放：名稱、集合、位置、旋轉、縮放、父物件 |

## 規格（本次在 Blender 實測）

- 單位：公尺；正面 -Y；Z 向上。FBX 以 -Z forward / Y up 匯出（Blender 預設）。
- 尺寸：48.26 × 53.70 × 12.29 m；底部中心原點：否（見 handoff_check.json 的 bounds）。
- 匯出網格物件 3877 個、三角面 906,568、材質 125 種。
- UV：2620 個網格沒有 UV 圖層；有 UV 的網格也只是自動產生，**沒有整理或烘焙**。
- 貼圖：見 handoff_check.json 的 images（含是否打包）。
- 外部連結檔：無。
- LOD：無。碰撞：無專用碰撞網格。

## 驗證

本次（Blender 5.2.2 LTS）：重新開啟 .blend 成功；`TownLayout_v004.fbx` 回匯 3877 個網格、尺寸差 0.0 mm。

**未做：** Unity 匯入、URP 材質、手機效能、LOD、碰撞、UV 烘焙。Blender 能開、FBX 能回匯，不代表 Unity 已驗收。

## 設計參考

- 沒有建模前的 AI 三視圖或概念圖可附。包內的圖片都是建模後的渲染。

## 製作工具

見 `tools/ArtLibrary/ExpansionBatches/TownRefinement12/BlenderSource/`（原樣複製）。腳本依 dondon2.0 的目錄結構讀寫，重建需在來源儲存庫的對應位置執行。

## 來源與授權

- 作者：dondon2.0 專案（joshsu54），由 AI 程式助理以 Blender Python 程序化建模；沒有使用外部模型、貼圖或素材庫。
- 授權：**來源儲存庫沒有授權檔**；轉入《雲境》的使用條件需由 joshsu54 與 z1nnz 確認。
