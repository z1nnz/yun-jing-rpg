# 青溪地形改造｜現有模型盤點

由 `node tools/qingxi-terrain/asset-inventory.mjs` 從 `art/exports/**/*.glb` 與 Unity FBX 量測產生，共 106 件（LOD 檔不重複計）。尺寸單位為公尺，Y 為高度。
「分類」先由名稱與比例自動判斷，再以表內「人工判斷」覆寫；**這是給地形整合的起點，不是最終決定**，擺進新地形後仍要看玩家視角。

| 分類 | 件數 | 在新地形上怎麼用 |
|---|---:|---|
| 直接擺放 | 71 | 原點在底部中心，依地形高度放上即可 |
| 調整接地 | 2 | 可以用，但底部或中心偏離原點；擺放時補位移，或請原作者重設原點 |
| 散布件 | 6 | 小叢草、花、石；由道路遮罩外的散布規則自動放 |
| 結構件（保留模型） | 17 | 橋、台階、平台、水渠；地形塑形去接它，接口高度要對齊路線 |
| 交給地形 | 10 | 道路、獸徑、地形磚、河岸面；改由地形高度＋材質處理，原件作為造型與配色參考 |

| 資產 | 作者 | 分類 | 尺寸 X×Y×Z | 底部 | 三角面 | 材質 | 說明 |
|---|---|---|---|---:|---:|---:|---|
| `aptitude-plaza-v1/aptitude-plaza-v1` | z1nnz | 結構件（保留模型）＊ | 18.00×3.75×20.10 | 0.00 | 16352 | 5 | 人工判斷：鋪石廣場是硬質地坪，保留模型，周圍地形壓平接上 |
| `elder-world-tree-hero-v1/elder-world-tree-hero-v1` | z1nnz | 直接擺放 | 9.63×9.78×6.77 | 0.00 | 147222 | 2 |  |
| `giant-tree-v1/giant-tree` | z1nnz | 直接擺放 | 90.56×62.35×69.77 | 0.00 | 44420 | 7 |  |
| `irrigation-v1/cistern` | z1nnz | 結構件（保留模型） | 2.00×1.10×2.28 | 0.00 | 1816 | 7 |  |
| `irrigation-v1/spirit-bed` | z1nnz | 結構件（保留模型）＊ | 2.41×0.40×3.22 | 0.00 | 3404 | 8 | 人工判斷：舊版靈田，同上；可能含地面底板：Rich soil |
| `irrigation-v1/water-channel` | z1nnz | 結構件（保留模型） | 0.60×0.24×2.00 | 0.00 | 540 | 6 |  |
| `irrigation-v2/cistern` | z1nnz | 結構件（保留模型） | 2.00×1.10×2.28 | 0.00 | 1816 | 2 |  |
| `irrigation-v2/spirit-bed` | z1nnz | 結構件（保留模型）＊ | 2.41×0.40×3.22 | 0.00 | 3404 | 1 | 人工判斷：靈田有田埂，需要地形挖平一塊再放 |
| `irrigation-v2/water-channel` | z1nnz | 結構件（保留模型） | 0.60×0.24×2.00 | 0.00 | 540 | 2 |  |
| `qingxi-alchemy-b/B01_BronzeFurnace/v001/B01_BronzeFurnace_cold` | joshsu54 | 直接擺放 | 0.74×0.89×0.77 | 0.00 | 14912 | 1 |  |
| `qingxi-alchemy-b/B01_BronzeFurnace/v001/B01_BronzeFurnace_heating` | joshsu54 | 直接擺放 | 0.74×0.89×0.77 | 0.00 | 14912 | 1 |  |
| `qingxi-alchemy-b/B02_FurnaceLid/v001/B02_FurnaceLid` | joshsu54 | 直接擺放 | 0.54×0.28×0.54 | 0.00 | 6216 | 1 |  |
| `qingxi-alchemy-b/B02_FurnaceLid/v001/B02_FurnaceLid_heating` | joshsu54 | 直接擺放 | 0.54×0.28×0.54 | 0.00 | 6216 | 1 |  |
| `qingxi-alchemy-b/B03_StoneMortar/v001/B03_StoneMortar` | joshsu54 | 直接擺放 | 0.34×0.21×0.32 | 0.00 | 2276 | 1 |  |
| `qingxi-alchemy-b/B04_BambooSortingTrays/v001/B04_BambooSortingTrays` | joshsu54 | 直接擺放 | 0.63×0.67×0.47 | 0.00 | 7824 | 1 |  |
| `qingxi-alchemy-b/B05_HerbDrawerCabinet/v001/B05_HerbDrawerCabinet` | joshsu54 | 直接擺放 | 0.76×0.94×0.48 | 0.00 | 7000 | 1 |  |
| `qingxi-alchemy-b/B06_CeramicWaterJar/v001/B06_CeramicWaterJar` | joshsu54 | 直接擺放 | 0.55×0.55×0.47 | 0.00 | 4544 | 1 |  |
| `qingxi-alchemy-b/B07_WoodenFuelBox/v001/B07_WoodenFuelBox` | joshsu54 | 直接擺放 | 0.69×0.46×0.43 | 0.00 | 5068 | 1 |  |
| `qingxi-alchemy-b/B08_VentilatedDryingBasket/v001/B08_VentilatedDryingBasket` | joshsu54 | 直接擺放 | 0.73×0.21×0.65 | 0.00 | 8956 | 1 |  |
| `qingxi-alchemy-b/B09_ClothFilterFrame/v001/B09_ClothFilterFrame` | joshsu54 | 直接擺放 | 0.62×0.93×0.42 | 0.00 | 6996 | 1 |  |
| `qingxi-alchemy-b/B10_WaxSealedBottle/v001/B10_WaxSealedBottle_empty` | joshsu54 | 直接擺放 | 0.11×0.11×0.08 | 0.00 | 1036 | 2 |  |
| `qingxi-alchemy-b/B10_WaxSealedBottle/v001/B10_WaxSealedBottle_filled` | joshsu54 | 直接擺放 | 0.07×0.12×0.08 | 0.00 | 2612 | 3 |  |
| `qingxi-alchemy-b/B11_BambooRecipeStand/v001/B11_BambooRecipeStand` | joshsu54 | 直接擺放 | 0.57×0.46×0.36 | 0.00 | 4064 | 1 |  |
| `qingxi-alchemy-b/B12_WorkshopChimney/v001/B12_WorkshopChimney` | joshsu54 | 直接擺放 | 0.76×1.95×0.74 | 0.00 | 6144 | 1 |  |
| `qingxi-detail-props-v2/qingxi-fern-flower-v2` | z1nnz | 散布件 | 1.21×0.49×1.23 | -0.02 | 1450 | 6 | 根部帶小土堆，散布時有助接地，不算底板 |
| `qingxi-detail-props-v2/qingxi-moss-boulder-v2` | z1nnz | 直接擺放＊ | 1.88×0.74×1.55 | -0.03 | 408 | 4 | 人工判斷：大石，手放後依地形高度下沉一點；底部在原點下方 0.03 m |
| `qingxi-detail-props-v2/qingxi-river-reed-v2` | z1nnz | 散布件 | 1.47×1.50×1.36 | -0.02 | 576 | 4 | 根部帶小土堆，散布時有助接地，不算底板 |
| `qingxi-detail-props-v2/qingxi-trail-lantern-v2` | z1nnz | 直接擺放＊ | 1.18×1.94×0.66 | 0.00 | 468 | 5 | 人工判斷：路燈，名稱含 trail 被誤判 |
| `qingxi-encounter-a/A01_SlopeTile` | Johnnnny0823 | 交給地形 | 4.40×1.54×4.29 | 0.00 | 11276 | 1 | 人工判斷：坡度改由地形做；表面貼圖可轉成地形材質層 |
| `qingxi-encounter-a/A02_HollowTile` | Johnnnny0823 | 交給地形 | 6.39×1.06×6.43 | 0.00 | 19996 | 1 | 人工判斷：兔穴凹地是玩法位置，地形照它的尺寸挖出凹地；邊緣樹根可拆成單件擺放 |
| `qingxi-encounter-a/A03_FallenLog` | Johnnnny0823 | 直接擺放 | 5.90×1.46×2.15 | 0.00 | 8150 | 1 |  |
| `qingxi-encounter-a/A04_MossBoulderCover` | Johnnnny0823 | 直接擺放 | 2.52×1.40×1.86 | 0.00 | 4900 | 1 |  |
| `qingxi-encounter-a/A05_LayeredRockCover` | Johnnnny0823 | 直接擺放 | 2.92×2.10×1.75 | 0.00 | 4742 | 1 |  |
| `qingxi-encounter-a/A06_RootStump` | Johnnnny0823 | 直接擺放 | 2.87×0.45×2.59 | 0.00 | 6312 | 1 |  |
| `qingxi-encounter-a/A07_RabbitTrailTile` | Johnnnny0823 | 交給地形 | 2.08×0.45×4.08 | 0.00 | 9100 | 1 | 人工判斷：兔徑改為路線資料中的窄徑，地形上畫材質 |
| `qingxi-encounter-a/A08_BrokenBambooFence` | Johnnnny0823 | 直接擺放 | 3.08×1.33×1.03 | 0.00 | 9984 | 1 |  |
| `qingxi-encounter-a/A09_StoneShelter` | Johnnnny0823 | 直接擺放 | 2.88×2.55×2.29 | 0.00 | 18056 | 1 |  |
| `qingxi-encounter-a/A10_WatchPlatform` | Johnnnny0823 | 直接擺放 | 2.18×2.75×2.80 | 0.00 | 6488 | 1 |  |
| `qingxi-encounter-a/A11_WarningClothRack` | Johnnnny0823 | 直接擺放 | 1.64×1.90×0.62 | 0.00 | 3876 | 1 |  |
| `qingxi-encounter-a/A12_VineDummy` | Johnnnny0823 | 直接擺放 | 0.96×1.64×0.65 | 0.00 | 8128 | 1 |  |
| `qingxi-encounter-a/A12_VineDummy_worn` | Johnnnny0823 | 直接擺放 | 0.86×1.64×0.82 | 0.00 | 5928 | 1 |  |
| `qingxi-entry-assets-v13/herb-basket-v13` | z1nnz | 調整接地 | 0.54×0.47×0.36 | 0.06 | 16776 | 3 | 底部在原點上方 0.05 m |
| `qingxi-entry-assets-v13/novice-cultivator-v13` | z1nnz | 直接擺放＊ | 0.98×1.73×0.36 | 0.03 | 3716 | 8 | 人工判斷：角色樣片，不參與地形；底部在原點上方 0.03 m |
| `qingxi-entry-assets-v13/road-dressing-v13` | z1nnz | 交給地形 | 2.43×0.27×1.34 | -0.00 | 4040 | 4 | 人工判斷：路邊點綴整片相連，拆成單叢後當散布件 |
| `qingxi-entry-assets-v13/village-gate-v13` | z1nnz | 結構件（保留模型） | 5.81×3.69×1.57 | 0.00 | 33204 | 6 |  |
| `qingxi-gathering-visual-kit-v1/QX_CreekSteppingPlank/v001/QX_CreekSteppingPlank` | joshsu54 | 結構件（保留模型） | 0.98×0.63×0.80 | 0.00 | 10960 | 1 |  |
| `qingxi-gathering-visual-kit-v1/QX_EmbeddedOre_Yumai/v001/QX_EmbeddedOre_Yumai_post` | joshsu54 | 直接擺放 | 2.34×0.83×2.03 | -0.02 | 44720 | 1 |  |
| `qingxi-gathering-visual-kit-v1/QX_EmbeddedOre_Yumai/v001/QX_EmbeddedOre_Yumai_pre` | joshsu54 | 直接擺放 | 2.34×1.13×2.03 | -0.01 | 46332 | 1 |  |
| `qingxi-gathering-visual-kit-v1/QX_GatheringLandmark/v001/QX_GatheringLandmark` | joshsu54 | 直接擺放 | 4.40×4.46×2.90 | -0.01 | 59882 | 1 |  |
| `qingxi-gathering-visual-kit-v1/QX_SpiritHerb_Chilu/v001/QX_SpiritHerb_Chilu_post` | joshsu54 | 直接擺放 | 1.04×0.32×0.94 | -0.01 | 71716 | 1 |  |
| `qingxi-gathering-visual-kit-v1/QX_SpiritHerb_Chilu/v001/QX_SpiritHerb_Chilu_pre` | joshsu54 | 直接擺放 | 1.03×0.32×0.94 | -0.01 | 84544 | 1 |  |
| `qingxi-gathering-visual-kit-v1/QX_SpiritHerb_Qinglan/v001/QX_SpiritHerb_Qinglan_post` | joshsu54 | 直接擺放 | 0.82×0.30×0.76 | -0.01 | 23596 | 1 |  |
| `qingxi-gathering-visual-kit-v1/QX_SpiritHerb_Qinglan/v001/QX_SpiritHerb_Qinglan_pre` | joshsu54 | 直接擺放 | 0.86×0.51×0.76 | -0.01 | 35320 | 1 |  |
| `qingxi-gathering-visual-kit-v1/QX_WaterReeds/v001/QX_WaterReeds` | joshsu54 | 散布件 | 1.25×1.91×1.08 | -0.12 | 35166 | 1 | 底部在原點下方 0.12 m |
| `qingxi-listening-terrace-v1` | z1nnz | 結構件（保留模型） | 8.84×4.57×7.66 | -0.25 | 9612 | 10 | 人工判斷：聽風台是有台階的建築平台，保留模型，地形做到台基邊；底部在原點下方 0.25 m |
| `qingxi-mountain-rabbit-v003/QingxiMountainRabbit_v003` | Codex | 直接擺放 | 0.47×0.76×0.69 | 0.00 | 22192 | 1 | 人工判斷：角色模型，由遊戲邏輯放到地面 |
| `qingxi-prop-kit-v1/qingxi-cobble-v1` | z1nnz | 散布件 | 0.89×0.34×0.66 | 0.01 | 80 | 1 |  |
| `qingxi-prop-kit-v1/qingxi-grass-v1` | z1nnz | 散布件 | 0.62×0.33×0.66 | 0.00 | 82 | 2 | 根部帶小土堆，散布時有助接地，不算底板 |
| `qingxi-prop-kit-v1/qingxi-wildflower-v1` | z1nnz | 散布件 | 0.44×0.35×0.46 | 0.00 | 112 | 4 | 根部帶小土堆，散布時有助接地，不算底板 |
| `qingxi-return-c/C01` | Eli | 直接擺放 | 0.48×0.60×0.39 | 0.00 | 1956 | 3 |  |
| `qingxi-return-c/C02` | Eli | 直接擺放 | 1.15×0.66×0.64 | 0.00 | 1512 | 2 |  |
| `qingxi-return-c/C03` | Eli | 直接擺放 | 0.48×0.28×0.33 | 0.00 | 2400 | 4 |  |
| `qingxi-return-c/C04` | Eli | 直接擺放 | 0.35×0.16×0.30 | 0.00 | 712 | 3 |  |
| `qingxi-return-c/C05` | Eli | 直接擺放 | 0.40×0.25×0.29 | 0.00 | 816 | 4 |  |
| `qingxi-return-c/C06` | Eli | 直接擺放 | 0.80×0.45×0.34 | 0.00 | 972 | 2 |  |
| `qingxi-return-c/C07` | Eli | 直接擺放 | 0.28×0.59×0.28 | 0.00 | 1044 | 5 |  |
| `qingxi-return-c/C08` | Eli | 直接擺放 | 0.38×0.10×0.29 | 0.00 | 1188 | 5 |  |
| `qingxi-riverbank-v2/qingxi-riverbank-v2` | z1nnz | 交給地形 | 11.86×1.24×12.09 | -0.31 | 8716 | 10 | 人工判斷：河岸高差由地形做；石塊與蘆葦拆成散布件或結構件；底部在原點下方 0.31 m |
| `qingxi-riverside-house-v1/qingxi-riverside-house-v1` | z1nnz | 直接擺放 | 10.80×6.64×9.49 | 0.00 | 11128 | 11 |  |
| `qingxi-road-props-v12/qingxi-bridge-rail-v12` | z1nnz | 結構件（保留模型） | 2.44×1.06×0.23 | 0.00 | 744 | 3 |  |
| `qingxi-road-props-v12/qingxi-herb-rack-v12` | z1nnz | 直接擺放 | 1.26×1.55×0.48 | 0.00 | 1004 | 4 |  |
| `qingxi-road-props-v12/qingxi-road-v12` | z1nnz | 交給地形 | 7.97×0.40×12.00 | 0.00 | 12320 | 9 | 人工判斷：泥土路改由路線＋地形材質；v13 已取代本件 |
| `qingxi-road-props-v12/qingxi-waymarker-v12` | z1nnz | 直接擺放 | 0.72×1.00×0.43 | 0.00 | 384 | 3 |  |
| `qingxi-road-props-v13/qingxi-road-v13` | z1nnz | 交給地形 | 8.73×0.40×12.00 | 0.00 | 12960 | 9 | 人工判斷：泥土路改由路線＋地形材質；路面與路緣貼圖可轉成地形材質層，作為配色基準 |
| `qingxi-training-yard-v1/agility-post` | Johnnnny0823 | 直接擺放 | 1.21×1.67×1.10 | 0.00 | 3676 | 1 |  |
| `qingxi-training-yard-v1/engraved-training-stone` | Johnnnny0823 | 直接擺放 | 2.08×0.28×1.67 | 0.00 | 3072 | 1 |  |
| `qingxi-training-yard-v1/qi-striking-post` | Johnnnny0823 | 直接擺放 | 0.78×1.65×0.79 | 0.00 | 9744 | 1 |  |
| `qingxi-training-yard-v1/training-banner` | Johnnnny0823 | 直接擺放 | 0.84×2.66×0.55 | 0.00 | 5996 | 1 |  |
| `qingxi-training-yard-v1/training-shelter` | Johnnnny0823 | 直接擺放 | 7.12×4.33×6.04 | 0.00 | 61278 | 1 |  |
| `qingxi-training-yard-v1/weapon-rack` | Johnnnny0823 | 直接擺放 | 1.90×1.65×0.65 | 0.00 | 2688 | 1 |  |
| `qingxi-village-signs-v1/Q01` | Eli | 直接擺放 | 1.25×1.76×0.55 | 0.00 | 4248 | 5 |  |
| `qingxi-village-signs-v1/Q02` | Eli | 直接擺放 | 0.48×0.83×0.36 | 0.00 | 376 | 2 |  |
| `qingxi-village-signs-v1/Q03` | Eli | 直接擺放 | 0.25×1.05×0.22 | 0.00 | 1136 | 6 | 人工判斷：ground_stone 是木樁底下的墊石，屬於本件，不是地面；可能含地面底板：ground_stone、ground_stone.001、ground_stone.002 |
| `qingxi-village-signs-v1/Q04` | Eli | 直接擺放 | 0.85×1.24×0.42 | 0.00 | 3488 | 5 |  |
| `qingxi-winding-road-v1/qingxi-winding-road-v1` | z1nnz | 交給地形 | 7.00×0.47×12.00 | 0.01 | 5332 | 4 | 人工判斷：彎路造型可當路線形狀參考；路面交給地形 |
| `qingxi-world-v1/qingxi-sacred-tree-v1` | z1nnz | 直接擺放 | 11.82×13.91×12.23 | -0.01 | 648 | 5 |  |
| `qingxi-world-v1/qingxi-timber-bridge-v1` | z1nnz | 結構件（保留模型） | 12.22×2.90×4.25 | 0.00 | 1608 | 3 |  |
| `CollaboratorNoviceV1/alchemy-furnace`（Unity FBX） | z1nnz | 直接擺放 | 0.74×0.89×0.77 | 0.00 | 14912 | 1 |  |
| `CollaboratorNoviceV1/forest-fallen-log`（Unity FBX） | z1nnz | 調整接地 | 5.90×1.52×2.15 | -0.05 | 14700 | 1 | 底部在原點下方 0.05 m |
| `CollaboratorNoviceV1/forest-layered-rock`（Unity FBX） | z1nnz | 直接擺放 | 2.96×2.10×1.75 | 0.00 | 8704 | 1 |  |
| `CollaboratorNoviceV1/forest-moss-cover`（Unity FBX） | z1nnz | 直接擺放 | 2.52×1.48×1.86 | 0.00 | 9016 | 1 |  |
| `CollaboratorNoviceV1/forest-root-stump`（Unity FBX） | z1nnz | 直接擺放 | 2.87×0.47×2.59 | -0.01 | 12320 | 1 |  |
| `CollaboratorNoviceV1/return-table`（Unity FBX） | z1nnz | 直接擺放 | 1.15×0.66×0.64 | 0.00 | 1512 | 2 |  |
| `CollaboratorNoviceV1/village-board`（Unity FBX） | z1nnz | 直接擺放 | 1.25×1.76×0.55 | 0.00 | 4248 | 5 |  |
| `CollaboratorWorldV1/BambooClump_v001`（Unity FBX） | z1nnz | 交給地形 | 3.88×5.98×3.81 | 0.00 | 22136 | 6 | 草石成片，應拆成單叢交給散布 |
| `CollaboratorWorldV1/CliffBoardwalk_v001`（Unity FBX） | z1nnz | 結構件（保留模型） | 3.21×2.35×6.23 | 0.00 | 5400 | 2 |  |
| `CollaboratorWorldV1/CommonPine_v001`（Unity FBX） | z1nnz | 直接擺放 | 5.82×7.29×5.54 | 0.00 | 17864 | 3 |  |
| `CollaboratorWorldV1/LayeredCliff_v001`（Unity FBX） | z1nnz | 結構件（保留模型） | 36.13×25.00×16.25 | 0.00 | 13178 | 3 |  |
| `CollaboratorWorldV1/MossBoulderSet_v001`（Unity FBX） | z1nnz | 直接擺放 | 3.30×1.52×2.16 | 0.00 | 2656 | 1 |  |
| `CollaboratorWorldV1/MountainStonePath_v001`（Unity FBX） | z1nnz | 交給地形 | 3.25×0.32×6.00 | 0.00 | 5292 | 2 |  |
| `CollaboratorWorldV1/MountainStoneStairs_v001`（Unity FBX） | z1nnz | 結構件（保留模型） | 3.19×3.55×5.03 | 0.00 | 3888 | 3 |  |
| `CollaboratorWorldV1/MountainStreamBend_v001`（Unity FBX） | z1nnz | 直接擺放 | 6.80×1.45×10.31 | 0.00 | 10724 | 6 |  |
| `CollaboratorWorldV1/QCaveEntrance_v003`（Unity FBX） | z1nnz | 直接擺放 | 2.81×3.27×0.81 | 0.00 | 4072 | 4 |  |
| `CollaboratorWorldV1/SectGate_v001`（Unity FBX） | z1nnz | 結構件（保留模型） | 9.14×5.72×4.54 | 0.00 | 62604 | 9 |  |
| `CollaboratorWorldV1/StarterHouse_v004`（Unity FBX） | z1nnz | 直接擺放 | 9.05×5.62×8.19 | 0.00 | 105928 | 16 |  |
| `CollaboratorWorldV1/StoneArchBridge_v001`（Unity FBX） | z1nnz | 結構件（保留模型） | 3.94×3.28×9.75 | 0.00 | 9618 | 3 |  |

＊ 人工判斷與自動分類不同。

## 限制

- GLB 從 `art/exports` 量測；只存在 Unity `Assets/YunJing/Models` 的 FBX 讀 `tools/qingxi-terrain/unity-models.json`（由 `check-grounding.ps1 -Inventory` 在 Unity 內量測），標「（Unity FBX）」。這些 FBX 沒有節點名稱資料，無法判斷是否含地面底板。
- 骨架模型以綁定姿勢量測；動畫中的範圍可能更大。
- 「可能含地面底板」只看節點、網格與材質名稱，需要開預覽確認。
- 「作者」是第一次把檔案加入 Git 的提交者，不一定等於建模者；以各資產 README 為準。
