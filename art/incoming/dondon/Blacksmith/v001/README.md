# Blacksmith（Blacksmith v001）

《雲境》交接第 1 批 · 初期生活場景。來源：[joshsu54/dondon2.0](https://github.com/joshsu54/dondon2.0) `Models/Blacksmith/v001`，提交 `4644558`；檔案與來源逐一比對 SHA-256 相同。

## 檔案

| 檔案 | 用途 |
| --- | --- |
| `01_smithy_overview.png` | 建模後渲染圖 |
| `02_workshop_roof_hidden.png` | 建模後渲染圖 |
| `03_smithy_rear.png` | 建模後渲染圖 |
| `Blacksmith_v001.blend` | 可編輯原檔 |
| `Blacksmith_v001.fbx` | 引擎交換檔 |
| `model_info.json` | 來源模型資料 |
| `validation.json` | 來源驗證報告 |
| `handoff_check.json` | 本次交接在 Blender 實際重開與 FBX 回匯的結果 |
| `previews/Blacksmith_v001_render_512.png` | 建模後渲染圖（縮為 512 px），不是設計參考 |

## 規格（本次在 Blender 實測）

- 單位：公尺；正面 -Y；Z 向上。FBX 以 -Z forward / Y up 匯出（Blender 預設）。
- 尺寸：7.43 × 5.72 × 5.36 m；底部中心原點：否（見 handoff_check.json 的 bounds）。
- 匯出網格物件 422 個、三角面 86,854、材質 21 種。
- UV：77 個網格沒有 UV 圖層；有 UV 的網格也只是自動產生，**沒有整理或烘焙**。
- 貼圖：無外部貼圖，材質為程序／純色材質，尚未烘焙成貼圖；FBX 只帶得出基本顏色。
- 外部連結檔：無。
- LOD：無。碰撞：無專用碰撞網格。

## 驗證

本次（Blender 5.2.2 LTS）：重新開啟 .blend 成功；`Blacksmith_v001.fbx` 回匯 422 個網格、尺寸差 0.0 mm。

**未做：** Unity 匯入、URP 材質、手機效能、LOD、碰撞、UV 烘焙。Blender 能開、FBX 能回匯，不代表 Unity 已驗收。

## 設計參考

- `references/`（來源 `ArtReferences/Blacksmith_10Views`）：內建 image_gen 生成的 10 張建模前參考圖與提示詞；來源專案把它歸為另一種畫風（Legacy_AlternateStyle），原始檔沒有明文記錄 Blacksmith v001 依哪幾張建模。

## 製作工具

見 `tools/BlenderSource/Blacksmith/`（原樣複製）。腳本依 dondon2.0 的目錄結構讀寫，重建需在來源儲存庫的對應位置執行。

## 來源與授權

- 作者：dondon2.0 專案（joshsu54），由 AI 程式助理以 Blender Python 程序化建模；沒有使用外部模型、貼圖或素材庫。
- 授權：**來源儲存庫沒有授權檔**；轉入《雲境》的使用條件需由 joshsu54 與 z1nnz 確認。
