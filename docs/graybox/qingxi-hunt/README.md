# 青溪狩獵區灰盒（Issue #9）

220 × 160 m 的獨立灰盒，用來確認以下幾件事：

- 玩家走得通，能看懂腳印與草動線索。
- 三群山兔各有可達的逃跑點。
- 有回村捷徑。
- 手機鏡頭不被牆或樹卡住。

這不是美術場景，也不是正式的 `Qingxi.unity`。

## 檔案

| 檔案 | 用途 |
| --- | --- |
| `layout.json` | 唯一座標來源：分區、標記、簡化阻擋體、路線、鏡頭書籤。單位公尺，Unity 座標（Y 向上）。 |
| `validate_layout.py` → `validation.json` | 離線預檢，只用 Python 標準函式庫。檢查座標、方盒碰撞、格網路徑、時間、視線，共 35 項。 |
| `render_layout.py` → `layout.png`、`coordinates.md` | 配置圖與座標表，需要 Pillow。不是遊戲截圖。 |
| `apps/game/Assets/YunJing/Editor/QingxiHuntGrayboxBuilder.cs` | Unity 產生器：產生 `Assets/YunJing/Generated/QingxiHuntGraybox.unity`，並做幾何、NavMesh、兩人控制器檢查。 |
| `blender/` | 由 layout 產生的 Blender 副本、渲染與幾何驗證（15 項）。 |
| `blender/demo/` | 用替身模型照路線排好的走位演練與影片，不是遊戲實機。 |
| `blender/art-preview/` | 美術補件 v001 的草叢、接岸比例試擺。 |
| `concepts/`、`art-requirements.md` | 六區概念圖提示詞，以及美術化需求。 |

## 重建與驗證

Unity 版本是 **6000.0.85f1**（2026-10-25 起，全專案改用此版）。FishNet 固定為 4.7.2。

```powershell
python docs/graybox/qingxi-hunt/validate_layout.py
python docs/graybox/qingxi-hunt/render_layout.py
& 'C:\Program Files\Unity\Hub\Editor\6000.0.85f1\Editor\Unity.exe' -batchmode -quit -projectPath apps/game -executeMethod YunJing.Editor.QingxiHuntGrayboxBuilder.ValidateBatch -logFile artifacts/unity-graybox-validate.log
```

在 Unity 編輯器裡也可以從選單 **Yun Jing → Graybox** 逐項執行：

1. Generate isolated Qingxi hunt draft
2. Check isolated geometry (not NavMesh)
3. Bake and check isolated NavMesh profiles
4. Rehearse two temporary controllers
5. Select bird's-eye view

結果寫到 `artifacts/qingxi-hunt-graybox/`，這個資料夾不進版控。

## 2026-10-25 實測結果（Unity 6000.0.85f1，`ValidateBatch`）

| 項目 | 結果 |
| --- | --- |
| 幾何 | 50 個標記沒有和阻擋體重疊；6 個鏡頭書籤在 3.5、6 m 都沒有被遮擋。 |
| NavMesh | 玩家與山兔兩組共 65 條路徑，全部是 PathComplete。 |
| 兩個 CharacterController | 主路 72.6 秒走完，兩人最近 1.59 m；替代回程 57.0 秒，最近 0.89 m。 |
| 離線預檢 | 35／35。第一個線索沿設計路線 26.5 秒；首次看見兔子 61.2 秒。 |

同一份 layout 在本機整合世界（青溪小鎮＋本區）中，以最短 NavMesh 路徑量到：

- 出生點 1 到第一個線索 23.3 秒，出生點 2 是 21.1 秒，都在 20–30 秒內。
- 6 個兔子重生點彼此最近 10 m，離任何玩家重生點至少 118 m。

## 本輪配置修改

- **封住抄近路：**
  - 新增 `NavBlocker_WestRidge` 與 `NavBlocker_TrailInnerRidge`，都已配對 CameraBlocker。
  - 原本可以從入口崖壁西側或山道內側抄近路，15 秒就走到第一個線索。
- **線索位置：**
  - `TrailClue_01` 從 (47, 68) 移到主路節點 (35, 78)。
  - `TrailClue_02` 從 (35, 82) 移到主路節點 (28, 95)，與第一個線索相距 18.4 m。

## 已知限制

- **結束時崩潰：** Unity 跑完 `ValidateBatch` 並印出 `QINGXI_GRAYBOX_VALIDATION_PASSED` 後才崩潰（MonoManager NULL，exit 21），原因未查明。CI 若看結束碼，會判為失敗。
- **路線條外觀：** 路線條是水平方塊，在兔坡上最多埋進地面 0.27 m。只影響外觀，沒有碰撞。
- **還沒驗證的：** 沒有 FishNet 雙端連線、可操控的玩家、山兔 AI、手機鏡頭與效能測試。
