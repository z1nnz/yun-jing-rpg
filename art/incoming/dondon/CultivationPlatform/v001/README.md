# 修煉台／聚靈陣（CultivationPlatform v001）

《雲境》交接第 1 批 · 洞府家具與修煉。來源：[joshsu54/dondon2.0](https://github.com/joshsu54/dondon2.0) `Models/CultivationPlatform/v001`，提交 `4644558`；檔案與來源逐一比對 SHA-256 相同。

說明：Static cultivation dais with jade inlay, stone sockets and woven seat; no gameplay or VFX.

## 檔案

| 檔案 | 用途 |
| --- | --- |
| `CultivationPlatform_v001.blend` | 可編輯原檔 |
| `CultivationPlatform_v001.fbx` | 引擎交換檔 |
| `model_info.json` | 來源模型資料 |
| `validation.json` | 來源批次驗證報告中本素材的那一筆，原樣抽出 |
| `handoff_check.json` | 本次交接在 Blender 實際重開與 FBX 回匯的結果 |
| `previews/CultivationPlatform_v001_render_512.png` | 建模後渲染圖（縮為 512 px），不是設計參考 |

## 規格（本次在 Blender 實測）

- 單位：公尺；正面 -Y；Z 向上。FBX 以 -Z forward / Y up 匯出（Blender 預設）。
- 尺寸：5.58 × 5.84 × 1.55 m；底部中心原點：是。
- 匯出網格物件 43 個、三角面 29,756、材質 8 種。
- UV：1 個網格沒有 UV 圖層；有 UV 的網格也只是自動產生，**沒有整理或烘焙**。
- 貼圖：無外部貼圖，材質為程序／純色材質，尚未烘焙成貼圖；FBX 只帶得出基本顏色。
- 外部連結檔：無。
- LOD：無。碰撞：無專用碰撞網格。

## 驗證

本次（Blender 5.2.2 LTS）：重新開啟 .blend 成功；`CultivationPlatform_v001.fbx` 回匯 43 個網格、尺寸差 0.0 mm。
來源批次另有驗證紀錄，見 `validation.json`（只宣稱其中實際列出的檢查）。

**未做：** Unity 匯入、URP 材質、手機效能、LOD、碰撞、UV 烘焙。Blender 能開、FBX 能回匯，不代表 Unity 已驗收。

## 設計參考

- 沒有建模前的 AI 三視圖或概念圖可附。包內的圖片都是建模後的渲染。

## 製作工具

見 `tools/ArtLibrary/ExpansionBatches/SectCore04/BlenderSource/`（原樣複製）。腳本依 dondon2.0 的目錄結構讀寫，重建需在來源儲存庫的對應位置執行。

## 來源與授權

- 作者：dondon2.0 專案（joshsu54），由 AI 程式助理以 Blender Python 程序化建模；沒有使用外部模型、貼圖或素材庫。
- 授權：**來源儲存庫沒有授權檔**；轉入《雲境》的使用條件需由 joshsu54 與 z1nnz 確認。
