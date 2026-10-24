# 出生石台（SpawnAltar v002）

《雲境》交接第 1 批 · 初期生活場景。來源：[joshsu54/dondon2.0](https://github.com/joshsu54/dondon2.0) `Models/SpawnAltar/v002`，提交 `4644558`；檔案與來源逐一比對 SHA-256 相同。

說明：Two-tier octagonal stone spawn altar with front steps, inlaid jade and gold rings with rune tiles, a lotus pedestal holding a floating jade spirit stone with halo, and four corner lanterns.

## 檔案

| 檔案 | 用途 |
| --- | --- |
| `model_info.json` | 來源模型資料 |
| `SpawnAltar_v002.blend` | 可編輯原檔 |
| `SpawnAltar_v002.fbx` | 引擎交換檔 |
| `validation.json` | 來源批次驗證報告中本素材的那一筆，原樣抽出 |
| `handoff_check.json` | 本次交接在 Blender 實際重開與 FBX 回匯的結果 |
| `previews/SpawnAltar_v002_render_512.png` | 建模後渲染圖（縮為 512 px），不是設計參考 |

## 規格（本次在 Blender 實測）

- 單位：公尺；正面 -Y；Z 向上。FBX 以 -Z forward / Y up 匯出（Blender 預設）。
- 尺寸：3.23 × 3.77 × 1.92 m；底部中心原點：是。
- 匯出網格物件 29 個、三角面 3,636、材質 7 種。
- UV：29 個網格沒有 UV 圖層；有 UV 的網格也只是自動產生，**沒有整理或烘焙**。
- 貼圖：見 handoff_check.json 的 images（含是否打包）。
- 外部連結檔：無。
- LOD：無。碰撞：無專用碰撞網格。

## 驗證

本次（Blender 5.2.2 LTS）：重新開啟 .blend 成功；`SpawnAltar_v002.fbx` 回匯 29 個網格、尺寸差 0.0 mm。
來源批次另有驗證紀錄，見 `validation.json`（只宣稱其中實際列出的檢查）。

**未做：** Unity 匯入、URP 材質、手機效能、LOD、碰撞、UV 烘焙。Blender 能開、FBX 能回匯，不代表 Unity 已驗收。

## 設計參考

- `references/`（來源 `ArtLibrary/ExpansionBatches/TownRefinement12/SourceSnapshot/ArtReferences/SpawnAltar_10Views`）：建模前的概念參考，但不是 AI 繪圖：先依提示詞寫設計規格，排出暫存草模，再以柔光棚拍渲染 10 個角度；提示詞保留在 prompts.json。

## 製作工具

見 `tools/ArtLibrary/ExpansionBatches/TownRefinement12/BlenderSource/`（原樣複製）。腳本依 dondon2.0 的目錄結構讀寫，重建需在來源儲存庫的對應位置執行。

## 來源與授權

- 作者：dondon2.0 專案（joshsu54），由 AI 程式助理以 Blender Python 程序化建模；沒有使用外部模型、貼圖或素材庫。
- 授權：**來源儲存庫沒有授權檔**；轉入《雲境》的使用條件需由 joshsu54 與 z1nnz 確認。
