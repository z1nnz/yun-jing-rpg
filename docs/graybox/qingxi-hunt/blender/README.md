# 青溪狩獵區：Blender 灰盒模型

日期：2026-10-25。只依 [layout.json](../layout.json) 產生，規則與 `apps/game/Assets/YunJing/Editor/QingxiHuntGrayboxBuilder.cs` 相同：

- 5 m 網格地面與帳篷形山丘。
- 每個阻擋體一個方盒。
- 0.12 m 淺水板。
- 每 2 m 一段路線條。
- 標記圓片，以及玩家、山兔、腳印的替代物。
- 六個鏡頭書籤。

這是在 Blender 看配置、做幾何檢查用的副本，**不是 Unity 場景**。**未經 Unity 編譯，NavMesh、CharacterController、兩人實玩、手機鏡頭都未實測**；渲染圖也不能當作 Unity 截圖。

## 重建

```sh
blender --background --factory-startup --python-exit-code 1 --python docs/graybox/qingxi-hunt/blender/build_blender_graybox.py
blender --background --factory-startup --python-exit-code 1 --python docs/graybox/qingxi-hunt/blender/validate_blender_graybox.py
```

改動 `layout.json` 後兩支都要重跑；驗證會比對 layout 的 SHA-256，舊模型會直接判為不合格。

## 內容

| 檔案 | 說明 |
| --- | --- |
| `QingxiHuntGraybox_blockout.blend` | 座標換算：Unity (x, y, z) → Blender (X = x, Y = z, Z = y)；單位公尺。 |
| `renders/birdseye.png` | 正交鳥瞰。 |
| `renders/overview.png` | 斜向總覽。 |
| `renders/view_01_exit.png`–`view_06_shortcut.png` | 六個路段視角，1950 × 900，垂直視角 60°、距離 5 m，與 Builder 書籤相同。 |
| `blender-validation.json` | 15 項幾何檢查。 |

`.blend` 內的集合：

- `QingxiHuntGraybox_ROOT`：與 Unity Builder 對應的內容。
- `95_Preview_Only`：分區外框、大圓環、平放標籤與預覽鏡頭。這些只在 Blender 存在，方便鳥瞰時辨識，Unity 場景裡沒有。

物件名稱沿用 layout 的標記名，例如 `RabbitSpawn_A01`、`NavBlocker_DeepWater`。每個物件帶有 `collider` 自訂屬性：地面是唯一的 MeshCollider，其餘阻擋體都是 Box。

## 驗證結果（Blender 5.2.2，15／15 通過）

| 項目 | 結果 |
| --- | --- |
| 標記與阻擋體 | 48 個標記（含 16 個 CameraBlocker 與邊界）全部存在，位置一致；16 個阻擋體尺寸一致。 |
| 地面網格 | 1,485 個頂點、2,816 個三角面，220 × 160 m，最高 2.4 m，最大坡度 5.7°。 |
| 玩家出生點 | P1 與 P2 相距 9 m，不重疊。 |
| 山兔出生點 | 最近兩點相距 10.0 m。 |
| 膠囊體碰撞 | 玩家、山兔、逃跑點、採藥點、商販的膠囊體都沒有碰到阻擋體。 |
| 鏡頭探針 | 六個書籤在 3.5、5、6 m 都沒有被地面或阻擋體擋住（以 0.2 m 探針、9 條射線近似）。 |
| 聚落視線 | 從 PlayerSpawn_01 看不到任何兔子出生點。 |

## 檢查時發現（給 Builder／配置負責人）

- **標記高度與網格不完全一致：** layout 的高度用山丘公式精算，5 m 三角面則是平面，所以在格子內會有誤差。RabbitSpawn_C01 比網格高 1.2 cm，RabbitFlee_A01 低 1.2 cm。驗證容差設 5 cm，結果通過，但 Unity 放置標記時最好改用射線取地面高度。
- **路線條在山丘上下陷：** 路線條是不跟坡度傾斜的平方盒，在兔坡上兩端會埋進地面。最深處：替代回程 0.27 m、兔群連線 0.23 m、主路 0.04 m。這只影響外觀，它們沒有碰撞。渲染圖裡的鋸齒就是這個原因。
- **淺灘視角被深水擋住一半：** `05_shallow` 的目標點緊貼 `NavBlocker_DeepWater`，畫面左半是深水阻擋盒。鏡頭本身沒有被遮擋，但這個視角看不太出淺灘。
- 依 layout 設計，林木、岩石只放了少量阻擋盒，所以渲染圖看起來很空，美術化前不能拿來判斷視線遮蔽是否足夠。

## 未做

- Unity 匯入、NavMesh 烘焙與實際行走。
- 第三人稱跟隨鏡頭的連續測試，以及兩人連線演練。
- 六區概念圖：提示詞在 [concepts/](../concepts/README.md)，圖片尚未生成。
- 既有交接素材（CommonPine、LayeredCliff 等）沒有放進這個模型，等驗收後再替換。
