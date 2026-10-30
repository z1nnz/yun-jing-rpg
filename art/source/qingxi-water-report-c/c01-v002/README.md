# C01 村民議事矮桌 v002 — 品質樣本

作者：Eli-0731 · Blender 4.5.3 LTS（可攜版）· 2026-10-30
參考：[C01 AI 三視圖](../../../references/qingxi-water-report-c/C01-three-view.png)（2026-10-29 已生成、檢視並保存，本版未新增設計，只依該圖重建）。
v001（`../build.py`、`exports/.../C01.glb`）完全保留未改。

## 為何選 C01

| 候選 | 視覺影響 30 | 參考完整 20 | 可行 20 | 重用 15 | 驗證便利 15 | 合計 |
|---|---:|---:|---:|---:|---:|---:|
| **C01 議事矮桌** | 27（村角中心，眼高可見全貌） | 19（正側背＋俯視＋7 張細節） | 17 | 11（扇形木板、銅嵌、繩綁可重用） | 13 | **87** |
| C03 水桶組 | 20 | 18 | 18 | 14 | 13 | 83 |
| C08 共修石牌 | 18 | 15 | 18 | 8 | 14 | 73 |
| C02 水情告示 | 18 | 14 | 15 | 9 | 13 | 69 |

## 檔案

| 類別 | 路徑 |
|---|---|
| Source | `C01_CouncilTable_v002.blend`：`C01_v002_Parts_LOD0/1/2` 為各級具名零件（平鋪來源材質），`C01_CouncilTable_Export_LOD*` 為烘焙後單一材質 |
| 腳本 | `build_c01_v002.py`（三級幾何＋平鋪材質）→ `bake_c01_v002.py`（獨立 UV 烘焙、匯出）；`render_rig.py`（固定鏡頭／燈光，`--ruler` 加 1.75 m 人形尺） |
| Export | `art/exports/qingxi-water-report-c/c01-v002/C01_CouncilTable_v002.fbx`（Unity：LOD0/1/2＋Collider）、`.glb`（PWA：LOD0）、`-report.json` |
| Textures | `art/textures/qingxi-water-report-c/c01-v002/C01_CouncilTable_v002_{Albedo,Normal,MaskURP,ORM}.png`（1024²）；`C01_*_albedo/normal.png` 為平鋪來源 |
| Preview | `art/previews/qingxi-water-report-c/c01-v002/`：`before-v001/`、`after-v002/`（含 `ruler/`）、`before-after-threequarter.png` |

## 技術數據（實測，匯出檔）

| 項目 | LOD0 | LOD1 | LOD2 | Collider |
|---|---:|---:|---:|---:|
| Triangles | 6,932 | 2,528 | 708 | 44 |
| 比例 | 100% | 36% | 10% | — |
| Materials | 1 | 1 | 1 | 0 |

- 尺寸 1.09 × 1.10 × 0.625 m（三視圖 1.10 × 0.62 m），原點在地面中心；FBX 以專案既有設定 `-Z forward / Y up / FBX_SCALE_ALL` 輸出，三角化後再算切線。
- **LOD 為手工分級**（`build_c01_v002.py` 的 `LODS`）：LOD1 去掉蝴蝶榫、托木、銅片，四圈繩綁改為一條繩帶、圓弧段數減少；LOD2 再去掉符號與繩、嵌片簡化成圓片。LOD1／LOD2 以 UV 轉移共用 LOD0 的烘焙貼圖。
- **烘焙材質**：一張材質、四張 1024²：Albedo（含 AO、邊緣磨亮、桌面中圈手摸磨亮、刀痕與杯印、腳下沾泥）、Normal（切線空間）、MaskURP（R 金屬、G AO、A 光滑度，給 URP Lit）、ORM（glTF）。
- 開放邊 0；UV 全在 0–1。

### 手機預算（估計值，未經實機）

LOD0 ≈ 7k（3 m 內）、LOD1 ≈ 2.5k（村角常態距離）、LOD2 ≈ 0.7k（15 m 外）；建議 LODGroup 切換 25%／8%／2% 螢幕高。單一材質＝每級 1 個 draw call；無透明材質。貼圖建議 ASTC 6×6。

## Visual Review

**第 1 輪（v001 基準）**
- Asset：C01｜Stage：Blockout／現況｜Render：`before-v001/`
- Issue 1：桌面薄、邊緣銳利、腿為細圓棍，剪影像一般現代家具；參考圖是厚實扇形桌面、方截面粗腿、繩綁、河石腳。
- Issue 2：三個選項嵌片像淺色貼紙，中心是黑洞而非青銅圓盤；符號無法辨認。
- Issue 3：單色材質，無木紋方向、無邊緣磨損；石腳是方塊。
- Gate：FAIL

**第 2 輪（v002a）**
- Fixes：重做六片扇形桌面（56 mm 厚、倒角、接縫）、蝴蝶榫、桌底三條托木、青銅中心盤、三處嵌片＋凸起符號、削切方截面外撇腿＋繩綁＋銅片、三角橫撐＋兩端繩綁、河石腳；木紋依每片徑向投影。
- 新 Issue 1：嵌片埋入木面幾乎不可見。Issue 2：木紋過密過橘，銅鏽過綠。Issue 3：接縫倒角過大、石腳偏小。
- Gate：FAIL（剪影已過）

**第 3 輪（v002b → v002c）**
- Fixes：嵌片提高至木面上方 1.5–5.5 mm、符號放大 1.25×；木紋降頻降對比、去飽和；接縫倒角 11→6.5 mm；石腳加大；凹槽改深色獨立材質；銅降金屬度防止變金色；麻繩加深；繩環段數下修（7,628→6,860 三角面）。
- 新 Issue：桌面木紋扭曲成大理石狀。
- Gate：FAIL → 修正

**第 4 輪（最終 v002）**
- Fixes：木紋擾動 1.6→0.45，每片 UV 偏移避免六片相同。
- Before / After：`before-after-threequarter.png`
- 結果：剪影、比例、扇形接縫、中心青銅盤、三個可讀符號（水滴／木槌／新芽）、繩綁腿、河石腳均與三視圖一致；中性光與風格光下結構仍清楚。
- Gate：**Stage 1 PASS、Stage 2 PASS（原型品質）**；Stage 3／4 部分完成；Stage 5 僅 Exported。

## 品質狀態

| 項目 | 狀態 |
|---|---|
| 已完成 | 依三視圖重建、手工三級 LOD、碰撞代理、單一烘焙材質、FBX／GLB |
| 技術驗證 | 尺寸、開放邊 0、UV 範圍、FBX 回匯 |
| 視覺驗證 | Blender Cycles 固定鏡頭，正／側／背／三分之四、線框、1.75 m 人形尺（已逐輪檢視渲染圖） |
| 引擎測試 | **未做**：這台電腦沒有安裝 Unity Editor；URP 外觀、LODGroup、手機效能皆未驗證 |

### 已知限制

1. 桌面刀痕、杯印、磨亮與沾泥是程序生成的貼圖，近看仍比手繪貼圖規律。
2. 腿頂繩綁是環狀疊放，非連續螺旋。
3. 桌底托木與第三條腿位於後方中心，依三視圖推定。
4. FBX 的貼圖為相對路徑引用；匯入 Unity 時需連同 `art/textures/.../c01-v002/` 一起帶入，並把 MaskURP 指定給 URP Lit 的 Metallic／Occlusion。
5. PWA 村角仍使用 v001。

## 重建

```bash
blender -b --factory-startup -P art/source/qingxi-water-report-c/c01-v002/build_c01_v002.py
blender -b --factory-startup -P art/source/qingxi-water-report-c/c01-v002/bake_c01_v002.py
blender -b --factory-startup -P art/source/qingxi-water-report-c/c01-v002/render_rig.py -- --glb <abs>/C01_CouncilTable_v002.glb --out <abs>/after-v002 --wire [--ruler]
```
`--out` 請使用絕對路徑。
