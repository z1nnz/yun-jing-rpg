# 新手領地後院（A）：第一批

依 `docs/execution/2026-10-31/01-A-territory-backyard.md`（分支 `feature/qingxi-main-scene-abc-v1`）。第一批交付內容：
- TY01–TY04 的 AI 參考圖：`art/references/territory-backyard-a/`。
- TY01 靈田的成品。
- TY02 青靈草四階段的成品。

TY03–TY10 與後院展示在第二批。

## 檔案

| 檔案 | 用途 |
|---|---|
| `build_backyard.py` | 幾何、材質、烘焙、LOD、匯出、回匯驗證；`-- --sheets` 從匯出的 GLB 算審圖 |
| `kitlib.py` | 從 #45 的 `qingxi-waterhead-a/kitlib.py` 複製，只改套件名 |
| `blend/<檔名>.blend` | 每件一個：程序分件（隱藏）＋烘焙遊戲網格＋LOD |

```powershell
blender -b --python-exit-code 1 --python art/source/territory-backyard-a/build_backyard.py            # 全部重建
blender -b --python-exit-code 1 --python art/source/territory-backyard-a/build_backyard.py -- --sheets  # 審圖
```

## 共同約定

- **單位與方向**：1 單位 = 1 m。Blender 是 Z 向上、正面 −Y；GLB 是 Y 向上。原點在腳印中心，底部高度 0，不附地面底板（接地規格）。
- **命名**：
  - 檔名帶版本號，例如 `TY01_SpiritField_v001`，改版不會覆蓋舊檔。
  - 物件名 `SM_TY_<名稱>_LOD0/1/2`，材質名 `M_TY_<名稱>`（建模規格第 7、3 節）。
- **LOD**：每個網格都有 LOD1（約 50%）和 LOD2（約 15%），和 LOD0 放在同一個 GLB／FBX。水面只有 176 面，只做一級，每一級 LOD 都顯示它。
- **貼圖**：
  - 烘焙成 BaseColor（sRGB）／ORM（R=AO、G=Roughness、B=Metallic）／Normal（OpenGL），會發光的另有 Emissive。
  - GLB 用 WebP，FBX 用 PNG。
- **水面**：`T_WW_Water_Normal` 和 B 組水利套件、#45 河段是同一張，SHA-256 開頭 `EFF5A830`，三個套件可以共用一個水 Shader。

## TY01 領地靈田 `TY01_SpiritField_v001`

- **格位**：`TY_Field_1` (−2.8, 6.7)、`TY_Field_2` (2.8, 6.7)，上限 2.6 × 3.4 × 0.5 m。
- **實際尺寸**：2.59 × 3.28 × 0.48 m（含引水竹管與木樁）。
- **擺放**：
  - 長邊沿場景的 z 方向。
  - 引水口在模型 +X 長邊。`TY_Field_2` 要繞垂直軸轉 180°，兩塊田的引水口才會都朝向 x = 0 的小徑。
- **構造**：
  - 夯土田埂高 0.30 m，外側有一層層夯實的痕跡，腳下較暗。
  - 頂上一圈灰青蓋石，外側再一圈斜靠的大石，石頭大小刻意不一。
  - 四角舊木樁綁三圈麻繩。
  - 長邊有一塊開了缺口的石頭，上面架一截劈開的竹管當引水口（附 `SOCKET_inlet`）。
- **田土**：
  - 三條平頂的壟，壟間有溝；壟面有耙痕、土塊與小石子。
  - 種植位置是 3 × 4：x = −0.62／0／0.62，y = ±0.32／±0.96（田的局部座標）。
- **三種狀態**（同一個網格，只換材質或開關水面）：
  - 乾土：`M_TY_SpiritField`，貼圖 `T_TY01_SpiritField_Dry_*`。
  - 濕土：換成 `T_TY01_SpiritField_Wet_BaseColor` 與 `_Wet_ORM`。田土變深、變亮，其他部分不變；法線圖和乾土共用。
  - 積水（淨水蓮用）：濕土材質，再顯示 `SM_TY_SpiritField_Water`。水面高 0.29 m，比壟頂高約 2 cm，溝裡約 12 cm 深。
    - 水色用規格的 `#1A5659`，但亮度壓暗到約 45%，透明度 50%（規格是約 70%）。
    - 原因：照規格的數值，這層幾公分深的水在暗色田土上看起來像一塊不透明的藍綠塑膠布，看不到底下的壟。
- **面數**：

  | 節點 | LOD0 | LOD1 | LOD2 |
  |---|---:|---:|---:|
  | `SM_TY_SpiritField` | 29,354 | 14,677 | 4,402 |
  | `SM_TY_SpiritField_Water` | 176 | 176 | 176 |

  大部分面數在石頭上（約 100 顆）。依規格「品質優先」，LOD0 沒有為了面數減少石頭。
- **碰撞**：盒 2.4 × 3.2 × 0.3 m。田埂不是給人走過去的，種植與收成從田邊操作。

## TY02 青靈草 `TY02_QinglingGrass_v001`

- **擺放**：每個階段一個網格，涵蓋一整塊田的 12 叢。原點與 TY01 相同，直接放在同一個位置。
- **階段**（照工作包第 6 節的門檻）：

  | 節點 | 生長進度 t | 高度 | LOD0 | LOD1 | LOD2 |
  |---|---|---:|---:|---:|---:|
  | `SM_TY_QinglingGrass_S1`（嫩芽） | t < 0.25 | 0.08 m | 432 | 216 | 64 |
  | `SM_TY_QinglingGrass_S2`（幼株） | 0.25 ≤ t < 0.6 | 0.22 m | 2,448 | 1,224 | 365 |
  | `SM_TY_QinglingGrass_S3`（成株） | 0.6 ≤ t < 1 | 0.40 m | 7,920 | 3,960 | 1,176 |
  | `SM_TY_QinglingGrass_S4`（成熟） | t ≥ 1 | 0.48 m | 9,936 | 4,968 | 1,477 |

- **葉片**：
  - 每片葉子是對摺的帶狀網格，從根部往外彎；根部是深色葉鞘，中肋較淺，有細脈與少量乾斑。
  - 叢形有三種（直立、側傾、開散），12 叢交錯使用，每叢的葉片數、長度與彎度都隨機，看起來不會像複製貼上。
- **成熟微光**：
  - 只有成熟期葉尖最後約 10% 會發光，顏色是規格的靈氣青 `#7FE0D4`。
  - 這些面用獨立材質 `M_TY_QinglingGrass_Glow`（Emissive 強度 2），引擎可以單獨調。其他面用 `M_TY_QinglingGrass`。
- **材質**：雙面渲染（關閉背面剔除）。

## 審圖（`art/previews/territory-backyard-a/`）

- **TY01**：
  - 正交正面、側面、背面，以及 3/4 透視（50 mm），每張旁邊都有 1.75 m 人形尺。
  - 引水口近景。
  - 乾土、濕土、積水三態並排。
  - 和村裡公用靈田 `irrigation-v2/spirit-bed` 的並排比較。
- **TY02**：
  - 四個階段並排（各放在一塊田裡）。
  - 一塊成熟田的俯視配置圖。
  - 成熟田近景。
  - 1.7 m 眼高的成熟田。
- **燈光**：照建模規格第 8 節。EEVEE，世界貼圖用 Poly Haven 的 `kloofendal_48d_partly_cloudy_puresky`（CC0，2K），強度 1.0，色彩管理 AgX、Medium High Contrast。
  - HDRI 不放進倉庫。腳本預設讀 `~/.cache/yunjing/hdri/kloofendal_48d_partly_cloudy_puresky_2k.hdr`，也可以用環境變數 `YJ_HDRI` 指定，找不到就停止出圖。

## 尚未完成或未驗證

- 第二批：TY03–TY10 的成品與後院展示。
- 遊戲內 1.7 m 截圖：要放進 `QingxiLodgingInterior` 場景才能拍，目前只有 Blender 裡的 1.7 m 眼高圖。
- 以下都還沒驗證：Unity 匯入、遊戲內光線、手機效能、LOD 切換距離。
