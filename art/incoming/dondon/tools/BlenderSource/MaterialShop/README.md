# 雜貨／材料鋪

由新手民宅 v004 衍生的店鋪外觀，原民宅檔案保持不變。主要區別為左側售貨窗與櫃台、赭色布棚、右側商品架和錢幣招牌。

新增物件包含藥罐、軟木塞、材料袋、靈草托盤和原礦示意；這些是商品造型原型，不是完整物品種類。

- 主根節點：`MaterialShop_ROOT`。
- 櫃台根節點：`Sales_Counter_ROOT`。
- 貨架根節點：`Goods_Shelf_ROOT`。
- `08_Shop_Counter_Shelves_Goods`：新增售貨窗、櫃台、貨架與商品。
- `09_Shop_Cloth_Awning_Sign`：布棚、支柱、腳座與招牌。
- 其餘牆體、屋頂和門軸沿用民宅分組；模型正面朝 Blender -Y。

使用 Blender 背景執行 `build_material_shop.py` 會新增版本化 `.blend`、`.fbx` 與總覽。固定十視圖由 `BlenderSource/render_asset_turnarounds.py -- MaterialShop` 產生，集中放在 `ArtLibrary/Turnarounds`。

目前以 Unreal 為後續引擎方向，但尚未在 Unreal 驗證；FBX 只有基本材質色，還需要 UV、貼圖、碰撞與效能整理。本版沒有買賣、物品數量、角色互動或完整室內。
