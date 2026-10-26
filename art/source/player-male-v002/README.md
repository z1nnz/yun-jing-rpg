# 男性主角 v002：分段建模母稿

2026-10-27。狀態：上身比例／構造稿，尚未完成高精度人物。本次提交為 Draft PR 審閱素材，尚不可接入遊戲。

## 基準與來源

依使用者已確認的男性三視圖、五視圖、A-Pose 與服裝局部圖製作。參考存於 `../../references/player-character-redesign-review/`，來源為 AI 概念設計，不是真人照片。沒有使用 Dondon 原件或遭否決的 v001 整身幾何。

提交／委託者：Johnnnny0823；幾何與腳本由 Codex 在本輪實際製作；造型方向及製作順序由使用者指定。Blender 5.2.2 LTS 背景 CLI 實際執行，未使用 Blender MCP。沒有修改使用者正在開啟的場景。

## 已保存的檢查點

- `Male_Stage01_Anatomy.blend`：胸廓、腰腹、骨盆與頸部接合區。
- `Male_Stage01_TorsoAndCollar.blend`：軀幹、肩部衣片、交領、腰帶。
- `Male_Stage02_ArmsAndSleeves.blend`：由軀幹邊界延伸的肩臂；連續上衣與衣袖、袖口、內袖、護腕及纏帶。
- `stage01_torso.py`、`stage02_arms.py`：依序執行可重建本地檢查點。只能在獨立 Blender 背景程序執行，stage01 會清空該程序場景。
- `validate_stage01.py`、`validate_stage02.py`：依賴外部 blender-asset-qa skill；可用 BLENDER_ASSET_QA_SCRIPTS 指定其 scripts 路徑，未隨 PR 內嵌此工具。

## 實際驗證

`../../previews/player-male-v002/stage02/review.html` 提供實際 Blender 正／側／背／45° 渲染、線框與概念圖對照。

Stage02 控制網格 QA：pass=True，錯誤 0，警告 2。設定為 render profile、no_modifiers=True、uv=False、eps=0.0001；這不代表細分後自交、動作變形或遊戲匯出驗證通過。

保留的警告：
- 腰帶與領邊有 34 組遮蔽的相背三角面；造型稿保留布片完整性，低模時刪除看不到的面。
- 最低點 z=0.9 m：目前僅上身，尚未建腿與腳，不是浮空角色驗收。

目視已檢查正、側、背與線框。領口轉折仍偏硬，局部布料摺痕尚未達到參考精細度；肩腋拓樸只經靜態檢查，還不能稱為適合最終蒙皮。手腕和骨盆刻意留接合截面。

尺度暫以角色總高 1.78 m 推定；不是從參考圖片測得的實際身高。當前控制網格共 16 個 mesh，35,298 頂點，66,980 等效三角面（未計細分／厚度）；不是手機低模面數。

| 物件 | 控制頂點 | 控制等效三角面 |
| --- | ---: | ---: |
| BackCentreSeam | 162 | 160 |
| ForearmWrap_L | 1200 | 2304 |
| ForearmWrap_R | 1200 | 2304 |
| InnerRobe_ChestPanel | 825 | 1536 |
| InnerRobe_ContinuousCollar | 1449 | 2560 |
| InnerSleeve_L | 1200 | 2304 |
| InnerSleeve_R | 1200 | 2304 |
| OuterRobe_ConnectedSleeves | 11574 | 22772 |
| OuterRobe_ContinuousBinding | 1449 | 2560 |
| Torso_ConnectedArms_Cage | 8130 | 16032 |
| Undershirt_ContinuousCollar | 1449 | 2560 |
| WaistSash_WovenBand | 2176 | 4096 |
| WrapStrap_L | 442 | 440 |
| WrapStrap_R | 442 | 440 |
| WristBinding_L | 1200 | 2304 |
| WristBinding_R | 1200 | 2304 |

## 尚未完成

1. 領口貼合、服裝裁片、布褶、腰帶結與垂帶精修。
2. 手掌與手指、腿腳、分層袍擺；之後才是頭髮配件，臉部最後。
3. 最終重拓樸、完整 UV、PBR 貼圖與手機／Windows LOD。
4. Humanoid 骨架、權重、表情、IK/FK、全部動畫與姿勢測試。
5. FBX／GLB 匯出回匯、Unity Avatar／Prefab／Animator／移動接入、手機效能。

當前不提供最終 FBX／GLB，也不宣稱 Unity 可玩。

## 審閱與重現

此稿供核心組評估男性造型，不修改 main 的角色分工、Heroine-01、Unity Builder、Packages 或執行期程式。請先看預覽與母檔，尚不要求核心組接入；未來完成低模、骨架及交換格式後才交付整合。

下載需 `git lfs pull`。以獨立 Blender 背景程序檢查：

```powershell
$env:BLENDER_ASSET_QA_SCRIPTS = 'C:/path/to/blender-asset-qa/scripts'
& 'C:/path/to/blender.exe' --background --factory-startup --python-exit-code 1 --python art/source/player-male-v002/validate_stage02.py
```

此命令會重跑控制網格檢查並更新 QA 報告與線框預覽，不修改 Blender 母檔。已在本次最新 main 的獨立 checkout 執行；不代表 Unity 編譯通過。
