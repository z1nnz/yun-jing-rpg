# 青溪世界：小鎮＋狩獵區（第一人稱本機演練）

日期：2026-10-25。Unity **6000.0.85f1**。

青溪起始小鎮和青溪狩獵區灰盒接成同一個場景。場景裡擺了 dondon 交接模型和美術補件 v001，另外有路線測試，以及一個可以在 Play 模式行走的第一人稱角色。

這是**本機演練**，有以下限制：
- 不是 FishNet 連線版的 `Cultivator`，不會寫入伺服器。
- 山兔只是替身：會逃跑、可以抓、會重生，但沒有戰鬥和掉落。

## 檔案

| 位置 | 說明 |
| --- | --- |
| `apps/game/Assets/QingxiWorld/Editor/QingxiWorldBuilder.cs` | 選單 **Qingxi World → Build world and run route tests**：生成 `Assets/QingxiWorld/Generated/QingxiWorld.unity`（不進版控）、烘焙玩家與山兔兩組 NavMesh、跑路線測試並拍截圖。 |
| `apps/game/Assets/QingxiWorld/Editor/QingxiPlaySmoke.cs` | 批次 Play 模式煙霧測試。 |
| `apps/game/Assets/QingxiWorld/Runtime/` | `QingxiFirstPerson`（第一人稱、傳送、畫面資訊）、`QingxiRabbit`（逃跑與 90 秒重生）。 |
| `apps/game/Assets/QingxiWorld/Models/` | 30 個 dondon 交接 FBX（複製自 `art/incoming/dondon`）、小鎮地形／湖／占位物 FBX、美術補件 v001 草叢與接岸。 |
| `apps/game/Assets/QingxiWorld/Data/town_world.json` | 小鎮擺放資料，由 `tools/export-qingxi-town-for-unity.py` 從 `art/source/qingxi-town-blockout-v1.blend` 匯出。 |

狩獵區直接讀 `docs/graybox/qingxi-hunt/layout.json`；美術試擺讀 `docs/graybox/qingxi-hunt/blender/art-preview/placement.json`。

## 重建與測試

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' -b art\source\qingxi-town-blockout-v1.blend --python-exit-code 1 --python tools\export-qingxi-town-for-unity.py
& 'C:\Program Files\Unity\Hub\Editor\6000.0.85f1\Editor\Unity.exe' -batchmode -quit -projectPath apps\game -executeMethod QingxiWorld.Editor.QingxiWorldBuilder.BuildAndTest -logFile artifacts\qingxi-world\unity-build.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.85f1\Editor\Unity.exe' -batchmode -projectPath apps\game -executeMethod QingxiWorld.Editor.QingxiPlaySmoke.Run -logFile artifacts\qingxi-world\unity-smoke.log
```

結果寫到 `artifacts/qingxi-world/`：`route_test.json`、`play_smoke.txt`、`screens/*.png`。這個資料夾不進版控。

## 第一人稱操作

在 Unity 開啟生成的場景後按 Play，點畫面鎖定滑鼠。

| 按鍵 | 功能 |
| --- | --- |
| WASD | 走路，4 m/s，同遊戲設定 |
| Shift | 跑步，7 m/s |
| 空白鍵 | 跳 |
| 滑鼠 | 轉視角 |
| V | 切換第一／第三人稱 |
| 1–8 | 傳送：小鎮廣場、棧道入口、狩獵區出生點、山道、採藥林、兔坡、淺灘、安全回村 |
| F | 抓 2.2 m 內的兔子 |
| L | 顯示／隱藏測試路線與導航網格 |
| H | 隱藏說明 |
| Esc | 放開滑鼠 |

## 世界怎麼接

- **狩獵區位置：** 旋轉 180°，放在小鎮西南角。座標換算是：狩獵區內部座標 (x, z) 對應世界座標 (-98 - x, -108 - z)。
- **連接處：** 小鎮湖上棧道的盡頭 (-118, -112) 直接進入狩獵區的聚落出口；狩獵區南牆在這裡留了 28 m 的開口。
- **重疊處理：** 和狩獵區重疊的小鎮地形與水面已移除，交界保留 2 m 重疊。
- **方向核對：** 小鎮 FBX 匯入後，三個取樣點的地面高度與 Blender 一致。

## 路線測試項目（全部要通過）

- **重生點：** 玩家重生點（小鎮廣場、狩獵區兩個出生點、安全回村點、商販）都在導航網格上，周圍沒有障礙物擋住角色。
- **第一個線索：** 以最短 NavMesh 路徑計算，兩個出生點到第一個線索都要在 20–30 秒內。
- **路線互通：** 小鎮 ↔ 狩獵區、主路、替代回程、各群兔子 → 安全回村點都走得通。小鎮廣場到坊市材料店旁也要走得通。
- **兩人走路：** 兩個 CharacterController 並排走三段路，都要走完、不卡住。
- **兔子逃跑：** 三群兔子的出生點和逃跑點兩兩互通，逃跑點都在 28 m 牽繩範圍內。
- **兔子重生點：** 彼此相距 ≥ 8 m，離任何玩家重生點 ≥ 30 m。

## 已知限制

- **材質：** 模型材質是 FBX 帶的基本色；Unity 內建渲染管線，未轉 URP 材質。
- **效能：** 草叢約 35 萬三角面；手機效能未測。
- **地形：** 淺灘接岸以下沉 0.30 m 處理，溪床還沒有挖出來。
