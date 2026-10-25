# 青溪世界組裝樣片 v2

這一版直接使用協作者從 `joshsu54/dondon2.0` 交付的現成模型，組成村落、古樹廣場、跨溪道路、東側林地與北側峭壁。不是把五張方向圖的所有山脈、湖泊與宗門一次建完。

![青溪區域總覽](../art/previews/qingxi-world-v2/qingxi-assembled-overview-v2.png)

![古樹、村落與跨溪路線](../art/previews/qingxi-world-v2/qingxi-assembled-village-v2.png)

![河東林地與峭壁](../art/previews/qingxi-world-v2/qingxi-assembled-forest-v2.png)

## 已實際組裝

- Blender 場景：[qingxi-world-assembled-v2.blend](../art/source/qingxi-world-assembled-v2.blend)。腳本 [assemble_qingxi_world_v2.py](../tools/art/assemble_qingxi_world_v2.py) 可重製；[placements.json](../art/previews/qingxi-world-v2/placements.json) 記錄每件來源、位置、方向及縮放。
- 使用 18 種協作者素材、102 個模型擺位。包含 `TownLayout v004`、`StarterHouse v004`、`CommonPine`、`BambooClump`、`MossBoulderSet`、`LayeredCliff`、`StoneArchBridge`、`MountainStreamBend`、`SectGate`、`QCaveEntrance` 等。兩件自行製作的木橋與古樹在前一版已先存 AI 三視圖並完成建模檢查；本輪沒有自行新做單件模型。
- 地形平板、河面、道路、廣場基底、峭壁托座與田地土塊仍是**場景灰盒**。這些只決定位置與尺度，不算完成地形或水體美術。
- Blender 檢視已完成；圖中模型尺寸、視線與道路布局可供討論，但未驗證碰撞、角色通行、手機效能或多人。

## Unity 進入順序

`apps/game/Assets/YunJing/Models/CollaboratorWorldV1/` 收進 12 種挑選的原始 FBX。`QingxiWorldBuilder` 已把第一批房屋、石橋、溪流、峭壁、松竹及洞口放到原有世界預覽場景，替換部分灰盒。**整套 TownLayout 僅供 Blender 構圖，不直接進 Unity**：它約 90.7 萬三角面、3,877 個網格物件；單棟 `StarterHouse` 也約 10.6 萬三角面。這些數值來自交接資料，足以說明先做 LOD、合批與真機測試的必要，不能據此宣稱已達手機性能。

協作者素材保留來源資料於 [art/incoming/dondon](../art/incoming/dondon/README.md)。來源儲存庫未附授權檔；本輪依專案擁有者明確要求在《雲境》專案內試用。公開發行前，應將協作者的使用範圍與可修改、可再散布條件寫入雙方可查的授權紀錄。

## 下一段工作

1. Unity 授權恢復後，執行 `./tools/unity.ps1 -Target WorldPreview`，檢查 FBX／URP 材質、比例、碰撞與出生到橋／林地的步行路線。2026-10-25 再次執行，Editor 因沒有有效授權以代碼 198 退出；尚未通過 Unity 編譯。
2. 把 `TownLayout` 拆為房屋、牌坊、牆、道路等可重用模組；為高面數房屋和松竹做 LOD、簡化碰撞與手機畫面密度測試。
3. 把平板地形換成河岸與坡地網格，製作水道與低層瀑布、植物分布和照明。若自行新做物件，先依規則生成、檢視並保存該物件的 AI 三視圖。
4. 把採藥、低級獵物和商販放進確定的區域，接服務端位置與資產規則；不要讓世界只是一張可觀看的佈景。
