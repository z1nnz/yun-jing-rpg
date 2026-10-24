# 青溪鎮鐵匠鋪

半開放青瓦木棚，風格延續出生廣場與新手民宅。這一批同時提供獨立鐵匠鋪與已配置鐵匠鋪的小鎮場景，不覆寫先前版本。

## 內容與分組

| Blender 集合 | 模型 |
| --- | --- |
| 01_Smithy_Foundation | 6.8 × 5.6 公尺石板地基，地板高 0.18 公尺 |
| 02_Open_Timber_Shelter | 木柱、橫梁、斜撐、後側與左側矮牆 |
| 03_Smithy_Tile_Roof | 彎曲青瓦棚頂、屋脊、煙囪穿孔；可單獨隱藏 |
| 04_Masonry_Forge_Chimney | 拱形爐口、煤床、集煙罩、空心煙囪與發光炭塊 |
| 05_Anvil_Hammer_Tongs | 木墩、收腰鐵砧、錐形砧角、錘子與火鉗 |
| 06_Workbench_Ingots | 木製工作台、下層置物板、金屬錠 |
| 07_Weapon_Rack | 木架與 3 把分件展示劍 |
| 08_Quench_Barrel_Coal | 淬火水桶、水面、鐵箍、備用煤塊 |
| 90_Smithy_Studio_Not_Exported | 渲染地面、鏡頭與燈光；不匯出 FBX |

選取 `Blacksmith_ROOT` 可移動整間鋪子。鐵砧、工作台、武器架、水桶各有獨立根節點；每把展示劍另有根節點，方便後續拆成遊戲物件。展示劍目前沒有武器數值、碰撞或裝備功能。

## 生成與交付

- `build_blacksmith.py`：新增 `Models/Blacksmith/vNNN`，輸出 Blender、FBX、模型資料與 3 張實際渲染圖。
- `02_workshop_roof_hidden.png`：為了查看工作區而隱藏屋頂的檢視圖；儲存的 Blender 檔仍顯示完整屋頂。
- `verify_blacksmith.py`：重新開啟模型，檢查瓦片法線、道具根節點，以及 FBX 匯回 Blender 後的模型數量與世界尺寸。
- `place_blacksmith_in_town.py`：從第一版小鎮配置與最新已儲存鐵匠鋪建立新的 `Models/TownLayout/vNNN`。

## 小鎮配置

鐵匠鋪根節點在 Blender `(12, 8, 0.24)`，朝西、面向小鎮。鋪內地板世界高度為 0.42 公尺。民宅北側的新步道寬 2.35 公尺；新增 6 階、每階高 0.18 公尺的回接階梯，銜接牌樓後的高處主街。

路線構成「出生廣場 → 民宅前 → 鐵匠鋪 → 回接階梯 → 牌樓 → 出生廣場」的小環線。此處指模型空間配置，並未加入導航或角色控制。

生成時抽樣檢查 18 個店鋪步道地面點及 6 個階梯高度；這些不能取代 Unity 角色碰撞、鏡頭遮擋與尋路測試。

## 本版限制

目前是外觀與道具原型，沒有鍛造、買賣、NPC、火焰模擬、動畫、碰撞、UV 烘焙或 LOD。爐內炭塊使用 Blender 發光材質，燈光僅用於預覽；FBX 內需要在 Unity 重建材質與爐火效果。尚未驗證 Unity 匯入與遊戲效能。
