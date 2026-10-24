# 玩家（男）（QPlayerMale v006）

《雲境》交接第 1 批 · 男女玩家。來源：[joshsu54/dondon2.0](https://github.com/joshsu54/dondon2.0) `Models/QPlayerMale/v006`，提交 `4644558`；檔案與來源逐一比對 SHA-256 相同。

## 檔案

| 檔案 | 用途 |
| --- | --- |
| `anim/idle_front_01.png` | 建模後動作影格（Blender 渲染） |
| `anim/idle_front_02.png` | 建模後動作影格（Blender 渲染） |
| `anim/idle_front_03.png` | 建模後動作影格（Blender 渲染） |
| `anim/idle_front_04.png` | 建模後動作影格（Blender 渲染） |
| `anim/walk_side_01.png` | 建模後動作影格（Blender 渲染） |
| `anim/walk_side_02.png` | 建模後動作影格（Blender 渲染） |
| `anim/walk_side_03.png` | 建模後動作影格（Blender 渲染） |
| `anim/walk_side_04.png` | 建模後動作影格（Blender 渲染） |
| `anim/walk_side_05.png` | 建模後動作影格（Blender 渲染） |
| `anim/walk_side_06.png` | 建模後動作影格（Blender 渲染） |
| `anim/walk_side_07.png` | 建模後動作影格（Blender 渲染） |
| `anim/walk_side_08.png` | 建模後動作影格（Blender 渲染） |
| `model_info.json` | 來源模型資料 |
| `QPlayerMale_v006.blend` | 可編輯原檔 |
| `QPlayerMale_v006.fbx` | 引擎交換檔 |
| `validation.json` | 來源批次驗證報告中本素材的那一筆，原樣抽出 |
| `handoff_check.json` | 本次交接在 Blender 實際重開與 FBX 回匯的結果 |
| `previews/QPlayerMale_v006_render_512.png` | 建模後渲染圖（縮為 512 px），不是設計參考 |

## 規格（本次在 Blender 實測）

- 單位：公尺；正面 -Y；Z 向上。FBX 以 -Z forward / Y up 匯出（Blender 預設）。
- 尺寸：0.66 × 0.61 × 1.45 m；底部中心原點：是。
- 匯出網格物件 88 個、三角面 30,588、材質 21 種。
- UV：88 個網格沒有 UV 圖層；有 UV 的網格也只是自動產生，**沒有整理或烘焙**。
- 貼圖：無外部貼圖，材質為程序／純色材質，尚未烘焙成貼圖；FBX 只帶得出基本顏色。
- 外部連結檔：無。
- LOD：無。碰撞：無專用碰撞網格。

## 骨架與動畫

- 骨架：17 根骨頭（root, pelvis, spine, neck, head, upperarm_l, lowerarm_l, hand_l, upperarm_r, lowerarm_r, hand_r, thigh_l, calf_l, foot_l, thigh_r, calf_r, foot_r），物件名 `Armature`；角色左側為 +X。
- 蒙皮：頭、手、手持道具、鞋為剛性；袖子在手肘、腿在膝蓋與腳踝、袍子在腰與大腿混合。頭髮與袍子沒有物理擺動。

| 動作 | 影格 | FPS | 循環 | 根運動 |
| --- | --- | --- | --- | --- |
| Idle | 1–49 | 24 | 是（末格＝首格） | 無（原地） |
| Walk | 1–25 | 24 | 是（末格＝首格） | 無（原地） |

- **沒有的動作（待製作）：** 奔跑、攻擊、受擊、死亡、採集、打坐。
- FBX（v006）以公分寫出、無節點縮放：這是為了 Unreal（v005 的公尺 FBX 在 UE 裡骨架小 100 倍）。玩家男女已實際在 UE 5.8 的 TownLayout_13 當玩家角色播放待機與走路；Unity 尚未測試。

## 驗證

本次（Blender 5.2.2 LTS）：重新開啟 .blend 成功；`QPlayerMale_v006.fbx` 回匯 88 個網格、尺寸差 0.0 mm、1 個骨架、動作 Idle, Walk。
來源批次另有驗證紀錄，見 `validation.json`（只宣稱其中實際列出的檢查）。

**未做：** Unity 匯入、URP 材質、手機效能、LOD、碰撞、UV 烘焙、Unity 動畫重定向。Blender 能開、FBX 能回匯，不代表 Unity 已驗收。

## 設計參考

- 沒有建模前的 AI 三視圖。造型是依使用者在對話中提供的一張動漫 Q 版人偶參考圖與多輪口頭回饋，用程序腳本直接建模；該參考圖未存入來源儲存庫，因此未附。

## 製作工具

見 `tools/ArtLibrary/ExpansionBatches/QCharacters17/BlenderSource/`（原樣複製）。腳本依 dondon2.0 的目錄結構讀寫，重建需在來源儲存庫的對應位置執行。

重建順序：`QCHAR_VERSION=v004` 執行 `build_qchar17.py`（外觀，讀 `qchar17_v004.py`）→ `QRIG_VERSION=v006` 執行 `rig_qchar17.py`（讀 v004 的 .blend，加骨架、權重、動作並匯出公分 FBX）→ `verify_rig17.py` 驗證。

## 來源與授權

- 作者：dondon2.0 專案（joshsu54），由 AI 程式助理以 Blender Python 程序化建模；沒有使用外部模型、貼圖或素材庫。
- 授權：**來源儲存庫沒有授權檔**；轉入《雲境》的使用條件需由 joshsu54 與 z1nnz 確認。
