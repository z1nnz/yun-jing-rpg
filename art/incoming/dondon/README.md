# dondon2.0 → 《雲境》素材交接

來源：[joshsu54/dondon2.0](https://github.com/joshsu54/dondon2.0) 提交 `4644558afb5d7d2dce59614768f8dabaca16e1c5`。依〈《雲境》素材交接清單〉（2026-10-24）挑選；每個素材資料夾內有自己的 README（檔案、規格、骨架與動作、驗證、參考來源、缺項）。

以下為實際狀態，**不是 Unity 匯入結論**：本包只在 Blender 5.2.2 重開 .blend 並回匯 FBX；Unity、URP、手機效能都沒有測試。

## 共通狀態

- 單位公尺、正面 -Y、Z 向上、底部中心原點（場景配置除外）。FBX 為 -Z forward / Y up。
- 材質為程序／純色材質，**沒有貼圖、沒有 UV 烘焙**；FBX 只帶基本顏色。
- **全部沒有 LOD、沒有專用碰撞。**
- 角色（Q 版人物 17 v006）有 17 骨骼骨架與 Idle（49 格）、Walk（25 格）兩段 24 fps 原地循環；其餘動作待製作。山兔、山豬未綁骨架、無動作。洞府門 QCaveDoor 另有開關門 FBX。
- 建模前 AI 參考圖只有：HerbalStall（image_gen 概念圖＋提示詞）、Blacksmith（image_gen 10 張，對應關係未明文記錄）。SpawnAltar、NoticeBoard 的建模前參考是草模渲染、不是 AI 圖。其餘沒有建模前參考，包內圖片都是建模後渲染。
- 授權：來源儲存庫沒有授權檔；作者為 dondon2.0 專案（joshsu54），全部程序化建模，沒有外部素材。轉入《雲境》的使用條件請雙方確認。

## 第一批：已交付 38 項，未交付 0 項

| 用途 | 素材 | 版本 | 三角面 | 材質 | 骨架／動作 | 建模前參考 | 本次檢查 |
| --- | --- | --- | ---: | ---: | --- | --- | --- |
| 男女玩家 | [玩家（男）](QPlayerMale/v006/README.md) | v006 | 30,588 | 21 | 17 骨／Idle, Walk | 無 | 通過 |
| 男女玩家 | [玩家（女）](QPlayerFemale/v006/README.md) | v006 | 32,460 | 19 | 17 骨／Idle, Walk | 無 | 通過 |
| 關鍵 NPC | [宗門長老](QSectElder/v006/README.md) | v006 | 25,296 | 12 | 17 骨／Idle, Walk | 無 | 通過 |
| 關鍵 NPC | [藥師](QHerbalist/v006/README.md) | v006 | 31,912 | 22 | 17 骨／Idle, Walk | 無 | 通過 |
| 關鍵 NPC | [雜貨店主](QShopkeeper/v006/README.md) | v006 | 24,648 | 13 | 17 骨／Idle, Walk | 無 | 通過 |
| 關鍵 NPC | [鐵匠](QBlacksmith/v006/README.md) | v006 | 30,476 | 20 | 17 骨／Idle, Walk | 無 | 通過 |
| 關鍵 NPC | [客棧老闆娘](QInnkeeper/v006/README.md) | v006 | 32,376 | 21 | 17 骨／Idle, Walk | 無 | 通過 |
| 修煉與測資 | [煉氣訣書冊](QQiManual/v002/README.md) | v002 | 3,868 | 4 | 無 | 無 | 通過 |
| 修煉與測資 | [測靈晶石](QAptitudeCrystal/v002/README.md) | v002 | 316 | 4 | 無 | 無 | 通過 |
| 修煉與測資 | [靈石](QSpiritStone/v002/README.md) | v002 | 84 | 2 | 無 | 無 | 通過 |
| 修煉與測資 | [丹瓶](QPillBottle/v002/README.md) | v002 | 1,970 | 6 | 無 | 無 | 通過 |
| 採集與狩獵 | [山兔](QMountainRabbit/v002/README.md) | v002 | 22,192 | 5 | 無 | 無 | 通過 |
| 採集與狩獵 | [山豬](QMountainBoar/v002/README.md) | v002 | 18,552 | 9 | 無 | 無 | 通過 |
| 採集與狩獵 | [基礎法劍](BasicSword01/v001/README.md) | v001 | 498 | 3 | 無 | 無 | 通過 |
| 靈草生長階段 | [靈草幼苗](SpiritHerbSeedling/v001/README.md) | v001 | 1,800 | 3 | 無 | 無 | 通過 |
| 靈草生長階段 | [靈草成長株](SpiritHerbYoung/v001/README.md) | v001 | 2,724 | 3 | 無 | 無 | 通過 |
| 靈草生長階段 | [靈草成熟株](SpiritHerbMature/v001/README.md) | v001 | 8,664 | 4 | 無 | 無 | 通過 |
| 初期生活場景 | [StarterHouse](StarterHouse/v004/README.md) | v004 | 105,928 | 16 | 無 | 無 | 通過 |
| 初期生活場景 | [SpawnTown](SpawnTown/v001/README.md) | v001 | 230,194 | 17 | 無 | 無 | 通過 |
| 初期生活場景 | [出生石台](SpawnAltar/v002/README.md) | v002 | 3,636 | 7 | 無 | 草模渲染（非 AI） | 通過 |
| 初期生活場景 | [小鎮公告板](NoticeBoard/v002/README.md) | v002 | 7,564 | 6 | 無 | 草模渲染（非 AI） | 通過 |
| 初期生活場景 | [藥草攤](HerbalStall/v001/README.md) | v001 | 35,480 | 7 | 無 | AI | 通過 |
| 初期生活場景 | [MaterialShop](MaterialShop/v001/README.md) | v001 | 118,064 | 23 | 無 | 無 | 通過 |
| 初期生活場景 | [Blacksmith](Blacksmith/v001/README.md) | v001 | 86,854 | 21 | 無 | AI | 通過 |
| 入宗洞府 | [QCaveResidence](QCaveResidence/v002/README.md) | v002 | 276,018 | 92 | 無 | 無 | 通過 |
| 入宗洞府 | [洞府入口](QCaveEntrance/v003/README.md) | v003 | 4,136 | 4 | 無 | 無 | 通過 |
| 入宗洞府 | [洞府地板](QCaveFloor/v002/README.md) | v002 | 3,008 | 2 | 無 | 無 | 通過 |
| 入宗洞府 | [洞府直牆](QCaveWall/v002/README.md) | v002 | 5,076 | 3 | 無 | 無 | 通過 |
| 入宗洞府 | [洞府門](QCaveDoor/v002/README.md) | v002 | 6,032 | 4 | 物件動畫 Door_Leaf_LeftAction, Door_Leaf_RightAction | 無 | 通過 |
| 洞府家具與修煉 | [弟子床鋪](DiscipleBed/v001/README.md) | v001 | 2,256 | 6 | 無 | 無 | 通過 |
| 洞府家具與修煉 | [宗門儲物箱](StorageChest/v001/README.md) | v001 | 6,260 | 4 | 無 | 無 | 通過 |
| 洞府家具與修煉 | [打坐蒲團](MeditationCushion/v001/README.md) | v001 | 63,804 | 4 | 無 | 無 | 通過 |
| 洞府家具與修煉 | [修煉台／聚靈陣](CultivationPlatform/v001/README.md) | v001 | 29,756 | 8 | 無 | 無 | 通過 |
| 種植與煉丹 | [靈藥圃](SpiritHerbGarden/v001/README.md) | v001 | 83,416 | 8 | 無 | 無 | 通過 |
| 種植與煉丹 | [靈草盆](HerbPlanter/v001/README.md) | v001 | 12,832 | 6 | 無 | 無 | 通過 |
| 種植與煉丹 | [丹爐](AlchemyFurnace/v001/README.md) | v001 | 19,484 | 3 | 無 | 無 | 通過 |
| 種植與煉丹 | [晾藥架](DryingRack/v001/README.md) | v001 | 28,972 | 5 | 無 | 無 | 通過 |
| 種植與煉丹 | [研缽與杵](MortarPestle/v001/README.md) | v001 | 4,188 | 4 | 無 | 無 | 通過 |

## 第二批：已交付 29 項，未交付 0 項

| 用途 | 素材 | 版本 | 三角面 | 材質 | 骨架／動作 | 建模前參考 | 本次檢查 |
| --- | --- | --- | ---: | ---: | --- | --- | --- |
| 宗門建築與設施 | [宗門山門](SectGate/v001/README.md) | v001 | 62,604 | 9 | 無 | 無 | 通過 |
| 宗門建築與設施 | [宗門大殿](SectGrandHall/v001/README.md) | v001 | 130,536 | 11 | 無 | 無 | 通過 |
| 宗門建築與設施 | [演武場](TrainingGround/v001/README.md) | v001 | 62,572 | 8 | 無 | 無 | 通過 |
| 宗門建築與設施 | [藏經閣](ScriptureLibrary/v001/README.md) | v001 | 349,096 | 12 | 無 | 無 | 通過 |
| 宗門建築與設施 | [宗門倉庫](SectStorehouse/v001/README.md) | v001 | 97,032 | 12 | 無 | 無 | 通過 |
| 宗門建築與設施 | [煉丹房](AlchemyHall/v001/README.md) | v001 | 121,752 | 15 | 無 | 無 | 通過 |
| 宗門建築與設施 | [演武木樁](TrainingDummy/v001/README.md) | v001 | 8,428 | 4 | 無 | 無 | 通過 |
| 弟子角色 | [劍修弟子](QDiscipleSword/v006/README.md) | v006 | 30,072 | 22 | 17 骨／Idle, Walk | 無 | 通過 |
| 弟子角色 | [丹修弟子](QDiscipleAlchemy/v006/README.md) | v006 | 33,064 | 23 | 17 骨／Idle, Walk | 無 | 通過 |
| 弟子角色 | [體修弟子](QDiscipleFarmer/v006/README.md) | v006 | 29,548 | 20 | 17 骨／Idle, Walk | 無 | 通過 |
| 煉器工具與材料 | [鐵砧與底座](SmithAnvil/v001/README.md) | v001 | 1,636 | 3 | 無 | 無 | 通過 |
| 煉器工具與材料 | [工作台](SmithWorkbench/v001/README.md) | v001 | 972 | 2 | 無 | 無 | 通過 |
| 煉器工具與材料 | [鐵鎚](SmithHammer/v001/README.md) | v001 | 296 | 2 | 無 | 無 | 通過 |
| 煉器工具與材料 | [淬火桶](QuenchBarrel/v001/README.md) | v001 | 1,464 | 3 | 無 | 無 | 通過 |
| 煉器工具與材料 | [火鉗](SmithTongs/v001/README.md) | v001 | 5,028 | 1 | 無 | 無 | 通過 |
| 煉器工具與材料 | [鐵錠](IronIngot01/v001/README.md) | v001 | 108 | 1 | 無 | 無 | 通過 |
| 煉器工具與材料 | [靈礦原石](JadeOre01/v001/README.md) | v001 | 20 | 1 | 無 | 無 | 通過 |
| 自然環境 | [普通松](CommonPine/v001/README.md) | v001 | 17,864 | 3 | 無 | 無 | 通過 |
| 自然環境 | [竹叢](BambooClump/v001/README.md) | v001 | 22,166 | 6 | 無 | 無 | 通過 |
| 自然環境 | [野灌木](WildShrub/v001/README.md) | v001 | 6,124 | 4 | 無 | 無 | 通過 |
| 自然環境 | [苔石組](MossBoulderSet/v001/README.md) | v001 | 2,656 | 1 | 無 | 無 | 通過 |
| 自然環境 | [層岩峭壁](LayeredCliff/v001/README.md) | v001 | 13,178 | 3 | 無 | 無 | 通過 |
| 探索道路與水景 | [青石古道路段](MountainStonePath/v001/README.md) | v001 | 5,292 | 2 | 無 | 無 | 通過 |
| 探索道路與水景 | [青石登山階梯](MountainStoneStairs/v001/README.md) | v001 | 3,888 | 3 | 無 | 無 | 通過 |
| 探索道路與水景 | [峭壁木棧道](CliffBoardwalk/v001/README.md) | v001 | 5,400 | 2 | 無 | 無 | 通過 |
| 探索道路與水景 | [拱形石橋](StoneArchBridge/v001/README.md) | v001 | 9,618 | 3 | 無 | 無 | 通過 |
| 探索道路與水景 | [彎曲山溪](MountainStreamBend/v001/README.md) | v001 | 10,724 | 6 | 無 | 無 | 通過 |
| 場景配置參考 | [TownLayout](TownLayout/v004/README.md) | v004 | 906,568 | 125 | 無 | 無 | 通過 |
| 場景配置參考 | [SectLayout](SectLayout/v003/README.md) | v003 | 2,474,324 | 116 | 無 | 無 | 通過 |

## 場景配置

`TownLayout/v004`、`SectLayout/v003` 是 Blender 組合場景（.blend＋整場景 FBX）。`placements.json` 由本次從 .blend 讀出：每個根物件的名稱、所屬集合、位置（公尺）、旋轉（度，XYZ Euler）、縮放與子物件數，座標系同 Blender（Z 向上、正面 -Y）。SectLayout 的 `layout_info.json` 內 `source` 欄位是原作者電腦上的絕對路徑，僅供辨識素材名稱；實際對應以素材資料夾名稱為準。

## 製作工具

`tools/` 依來源路徑保留各批次的生成、綁骨架與匯出腳本（原樣複製）。人物腳本：`tools/ArtLibrary/ExpansionBatches/QCharacters17/BlenderSource/`（`qchar17_v004.py`、`rig_qchar17.py` 及其引用的 `build_qchar17.py`、驗證用 `verify_rig17.py`）。這些腳本按 dondon2.0 的目錄結構讀寫，需在來源儲存庫內執行；交接包本身不需要它們就能使用模型。Unreal 專用的程式（例如角色動作切換 `QCharacterAnimDriver`）依清單不交付。

## 未交付或待製作

- 角色：奔跑、攻擊、受擊、死亡、採集、打坐動作。山兔、山豬的骨架與動作。
- 全部素材：UV 烘焙與貼圖、LOD、碰撞、Unity／URP 匯入與手機效能驗證。
- 人物造型的原始參考圖（使用者在對話中提供，未存入來源儲存庫）。

## 重新產生本包

在 dondon2.0 根目錄依序執行 `Tools/Handoff/yunjing/` 的 `stage_yunjing.py stage`、`check_yunjing.py`（Blender）、`stage_yunjing.py docs`，詳見腳本開頭說明。
