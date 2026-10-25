# 灰盒標記座標表

由 `layout.json` 產生；Unity 世界座標、公尺、Y 向上。這是配置資料，不是執行驗證。

| 名稱 | 類別 | X | Y | Z |
| --- | --- | ---: | ---: | ---: |
| PlayerSpawn_01 | player | 20 | 0.0 | 20 |
| PlayerSpawn_02 | player | 29 | 0.0 | 20 |
| Merchant_Material | merchant | 25 | 0.0 | 20 |
| TrailClue_01 | clue | 35 | 0.0 | 78 |
| TrailClue_02 | clue | 28 | 0.0 | 95 |
| TrailClue_03 | clue | 39 | 0.0 | 112 |
| TrailClue_04 | clue | 78 | 0.0 | 102 |
| TrailClue_05 | clue | 110 | 0.0 | 88 |
| TrailClue_06 | clue | 126 | 0.8 | 115 |
| RabbitSpawn_A01 | rabbit | 120 | 0.4 | 100 |
| RabbitSpawn_A02 | rabbit | 128 | 0.936 | 106 |
| RabbitSpawn_B01 | rabbit | 150 | 1.92 | 116 |
| RabbitSpawn_B02 | rabbit | 160 | 1.2 | 120 |
| RabbitSpawn_C01 | rabbit | 178 | 0.672 | 112 |
| RabbitSpawn_C02 | rabbit | 180 | 0.28 | 126 |
| RabbitFlee_A01 | flee | 118 | 0.368 | 117 |
| RabbitFlee_A02 | flee | 131 | 0.714 | 123 |
| RabbitFlee_A03 | flee | 138 | 1.12 | 100 |
| RabbitFlee_B01 | flee | 145 | 0.7 | 130 |
| RabbitFlee_B02 | flee | 159 | 0.372 | 134 |
| RabbitFlee_B03 | flee | 166 | 1.44 | 110 |
| RabbitFlee_C01 | flee | 173 | 0.238 | 133 |
| RabbitFlee_C02 | flee | 185 | 0.05 | 135 |
| RabbitFlee_C03 | flee | 188 | 0.096 | 104 |
| HerbNode_01 | herb | 35 | 0.0 | 87 |
| HerbNode_02 | herb | 32 | 0.0 | 101 |
| HerbNode_03 | herb | 45 | 0.0 | 107 |
| HerbNode_04 | herb | 59 | 0.0 | 105 |
| HerbNode_05 | herb | 69 | 0.0 | 97 |
| HerbNode_06 | herb | 77 | 0.0 | 88 |
| SafeReturn_01 | return | 33 | 0.0 | 20 |
| AreaBoundary_Hunt | boundary | 110 | 0.0 | 80 |
| CameraBlocker_EntryScreen | cameraBlocker | 40 | 0.0 | 45 |
| CameraBlocker_ForestRidge | cameraBlocker | 95 | 0.0 | 110 |
| CameraBlocker_ShallowScreen | cameraBlocker | 107 | 0.0 | 66 |
| CameraBlocker_FarRidge | cameraBlocker | 205 | 0.0 | 110 |
| CameraBlocker_ForestTree01 | cameraBlocker | 48 | 0.0 | 92 |
| CameraBlocker_ForestTree02 | cameraBlocker | 65 | 0.0 | 79 |
| CameraBlocker_ForestRock | cameraBlocker | 64 | 0.0 | 102 |
| CameraBlocker_SlopeRock01 | cameraBlocker | 149 | 1.638 | 101 |
| CameraBlocker_SlopeRock02 | cameraBlocker | 133 | 0.276 | 134 |
| CameraBlocker_SlopeTree01 | cameraBlocker | 180 | 0.24 | 92 |
| CameraBlocker_MerchantStall | cameraBlocker | 13 | 0.0 | 26 |
| CameraBlocker_DeepWater | cameraBlocker | 177 | 0.0 | 45 |
| CameraBlocker_WestRidge | cameraBlocker | 17.5 | 0.0 | 66 |
| CameraBlocker_TrailInnerRidge | cameraBlocker | 50.5 | 0.0 | 44 |
| CameraBlocker_BoundaryWest | cameraBlocker | -0.5 | 0.0 | 80 |
| CameraBlocker_BoundaryEast | cameraBlocker | 220.5 | 0.0 | 80 |
| CameraBlocker_BoundarySouth | cameraBlocker | 110 | 0.0 | -0.5 |
| CameraBlocker_BoundaryNorth | cameraBlocker | 110 | 0.0 | 160.5 |

## 簡化阻擋體

| 名稱 | 中心 X / Y / Z | 尺寸 X / Y / Z |
| --- | --- | --- |
| NavBlocker_EntryScreen | 40 / 3.0 / 45 | 10 / 6 / 40 |
| NavBlocker_ForestRidge | 95 / 3.5 / 110 | 12 / 7 / 60 |
| NavBlocker_ShallowScreen | 107 / 3.5 / 66 | 74 / 7 / 6 |
| NavBlocker_FarRidge | 205 / 4.5 / 110 | 8 / 9 / 65 |
| NavBlocker_ForestTree01 | 48 / 3.0 / 92 | 2 / 6 / 2 |
| NavBlocker_ForestTree02 | 65 / 3.0 / 79 | 2 / 6 / 2 |
| NavBlocker_ForestRock | 64 / 1.0 / 102 | 4 / 2 / 8 |
| NavBlocker_SlopeRock01 | 149 / 2.338 / 101 | 6 / 1.4 / 6 |
| NavBlocker_SlopeRock02 | 133 / 0.876 / 134 | 4 / 1.2 / 4 |
| NavBlocker_SlopeTree01 | 180 / 2.74 / 92 | 2 / 5 / 2 |
| NavBlocker_MerchantStall | 13 / 1.5 / 26 | 6 / 3 / 4 |
| NavBlocker_DeepWater | 177 / 1.0 / 45 | 34 / 2 / 50 |
| NavBlocker_WestRidge | 17.5 / 3.0 / 66 | 35 / 6 / 6 |
| NavBlocker_TrailInnerRidge | 50.5 / 3.0 / 44 | 11 / 6 / 22 |
| NavBlocker_BoundaryWest | -0.5 / 2.5 / 80 | 1 / 5 / 162 |
| NavBlocker_BoundaryEast | 220.5 / 2.5 / 80 | 1 / 5 / 162 |
| NavBlocker_BoundarySouth | 110 / 2.5 / -0.5 | 220 / 5 / 1 |
| NavBlocker_BoundaryNorth | 110 / 2.5 / 160.5 | 220 / 5 / 1 |
