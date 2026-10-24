# 洞府灌溉模型 · 2026-10-24

## 測資廣場 v1 · 2026-10-25

依已選定的 A 河谷骨架＋D 古木青溪氣質，先生成並檢視
`references/world-master-v1/aptitude-plaza-three-view.png`，再建立測資廣場模型。

- Blender 母檔：`source/aptitude-plaza-v1.blend`
- GLB：`exports/aptitude-plaza-v1/aptitude-plaza-v1.glb`
- Unity FBX：`../apps/game/Assets/YunJing/Models/AptitudePlazaV1/aptitude-plaza-v1.fbx`
- 實際 Blender 預覽：`previews/aptitude-plaza-v1.png`
- 建模與驗證腳本：`../tools/build-aptitude-plaza.py`、`../tools/validate-aptitude-plaza.py`

模型包含分層圓台、同心金屬環、中央靈晶、四向標柱及對向階梯。母檔基礎網格為
7,840 三角面；套用非破壞倒角後，GLB 與 FBX 均為 16,352 三角面，尺寸皆為
18 × 20.1 × 3.745 公尺。Blender 重新匯入驗證已通過。尚未取得 Unity 編譯與場景驗證，
因此目前只視為已驗證的美術素材，不稱為 Unity 可運行場景。

## 最新交付 v2

沿用下列已先生成、檢視並保存的 AI 三視圖，保留 v1 母檔，另存 v2。新增木材／石材／土壤的程序材質，烘焙為每件 1024px 顏色與切線法線貼圖；6 張 PNG 已隨模型保存。這批改的是同三件物品，沒有新增未先做三視圖的模型。

- [新版 Blender 母檔（貼圖已打包）](source/irrigation-v2.blend)
- [新版總覽](previews/irrigation-v2.png)、[空田](previews/spirit-bed-empty-v2.png)、[空水池](previews/cistern-empty-v2.png)
- 個別預覽：[靈田](previews/spirit-bed-v2.png)、[蓄水池](previews/cistern-v2.png)、[水渠](previews/water-channel-v2.png)
- GLB（內嵌貼圖）：`art/exports/irrigation-v2`；FBX 與貼圖：`apps/game/Assets/YunJing/Models/IrrigationV2`。
- [模型統計及參考圖雜湊](exports/irrigation-v2/report.json)、[驗證報告](exports/irrigation-v2/validation.json)。

每件分成兩個網格、每網格一個材質槽。田體與幼苗分離，可以顯示空田；池／渠本體與水面分離，可以顯示乾涸狀態。完整 LOD0 共 5,760 三角面，LOD1 共 2,892；近遠模型均另存 FBX、GLB。這不是成熟靈草的獨立造型，也沒有做動畫。

`IrrigationAssets.cs` 已加入 URP 貼圖與法線設定、LODGroup、簡單碰撞、可重用 prefab 的產生程式；`IrrigationVisual.cs` 提供植物與水面顯示開關。**Unity 2026-10-24 實際啟動仍因授權 exit 198，prefab 尚未實際生成、程式未編譯、未與個人洞府存檔串接。** 碰撞是簡化實心盒，不能當成池內可行走碰撞；不宣稱手機效能通過。

新版驗證：12 個匯出檔重新匯入 Blender，確認尺寸、有限頂點、UV 範圍、每網格單材質、分層名稱與 LOD 面數下降；6 張貼圖尺寸及非空檢查通過，GLB 的兩張貼圖內嵌檢查通過。已檢視實際渲染總覽和空田／空池。

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --factory-startup --python-exit-code 1 --python tools/finish-irrigation-models.py
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --factory-startup --python-exit-code 1 --python tools/validate-irrigation-v2.py
```

重建會覆寫 v2 生成檔，手工修改請另存。Unity 取得有效授權後再執行 `tools/unity.ps1 -Target Generate`，驗證貼圖方向、LOD 切換及碰撞；這些目前仍是必要的未完成驗收。

## v1 製作來源與歷史紀錄

依使用者要求，三件物品均先使用內建 image_gen 生成各自的正面、右側、頂面三視圖，檢視並保存後，才撰寫與執行 Blender 建模腳本。沒有使用現成外部模型；AI 圖作為造型參考，並非把圖片直接當成 3D 模型。

- [AI 三視圖與完整提示詞](references/irrigation-v1/prompts.json)
- [靈田三視圖](references/irrigation-v1/spirit-bed.png)
- [蓄水池三視圖](references/irrigation-v1/cistern.png)
- [導水渠三視圖](references/irrigation-v1/water-channel.png)
- [Blender 原始檔](source/irrigation-v1.blend)
- [實際模型渲染預覽](previews/irrigation-v1.png)
- [匯出統計](exports/irrigation-v1/report.json)、[重新匯入驗證](exports/irrigation-v1/validation.json)

## 模型

| 名稱 | 三角面 | 原型結構 |
|---|---:|---|
| spirit-bed 靈田 | 3,404 | 木框、角柱、銅箍、四壟土與幼苗 |
| cistern 蓄水池 | 1,816 | 石砌中空池體、水面、空心銅出水口、木柄 |
| water-channel 導水渠 | 540 | 兩端開放的 U 形石渠、獨立水面 |

Blender 5.2.2 LTS；公尺單位、地面中心原點。Blender 正面為 -Y；FBX 匯出採 -Z forward / Y up。個別 GLB 在 `art/exports/irrigation-v1`，Unity FBX 在 `apps/game/Assets/YunJing/Models/Irrigation`。原始檔中的橫向排列僅供預覽，單件匯出仍位於原點。FBX 三件合計 188,772 bytes。

AI 參考圖帶有輕微透視、面向和標註不一致，因此依結構重建：田框以 2.4 × 3.2 m 為基準，銅箍與幼苗令實際包圍盒達約 2.414 × 3.222 × 0.403 m；蓄水池主體 2 × 2 × 1.1 m，出水口使深度增至 2.28 m；石渠 0.6 × 2 × 0.24 m，保持兩端可銜接。參考圖不作工程精確投影使用。

## 重建與驗證

在專案根目錄執行（重建會覆寫本批生成素材；手工修改請另存版本）：

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --factory-startup --python tools/build-irrigation-models.py
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --factory-startup --python tools/validate-irrigation-models.py
```

建模腳本會先確認三張參考圖存在。驗證重新匯入六個檔案（3 GLB＋3 FBX），檢查包圍盒、有限頂點座標、UV、三角面預算；本次全部通過。已人工檢視 Blender 渲染預覽。

Unity 場景產生器已寫入 FBX 載入、URP 基本材質轉換與簡單碰撞盒，尚未執行 Unity 編譯或場景驗證。靈田幼苗是靜態展示；蓄水池與水渠亦是美術展示，尚未與角色存檔中的建造狀態同步。

目前使用基本色材質及自動 UV，沒有完成繪製貼圖、材質合圖、LOD、生長階段、動畫、水流 shader 或手機效能驗證。多材質仍需後續整理；低面數不等於已證明手機流暢。未製作角色模型。
