# 青溪狩獵區美術補件 v001

日期：2026-10-25。範圍：6 張區域概念圖、3 張建模前 AI 三視圖、3 張透明貼圖、3 套可編輯環境模型。人物與既有山兔未修改。

[開啟圖庫](index.html)

## 已完成

- 12 張 AI 圖使用內建 image_gen 生成並保留原尺寸；其中 V01、V02 是上次中斷後保留下來的生成結果，已在建模前檢視。提示詞見 prompts.json、concept-prompts.json、reference-prompts.json。
- 低草叢、倒伏草叢與淺灘接岸的 Blender 原檔，各含 LOD0／LOD1／LOD2；每級各有 FBX 與 GLB。另有接岸簡化碰撞 FBX。
- 三套模型共用 1 個材質與 128 × 128 色盤貼圖 T04。T04 為 Blender 產生的輔助材質圖，不是第 13 張 AI 生圖。
- Blender 5.2.2 LTS 幾何 QA：9 個顯示網格與 1 個碰撞網格通過。完整報告見 reports/model-manifest.json。
- 3 個 .blend 已重開，10 個 FBX 已在全新場景逐一重新匯入，尺寸誤差小於 1 mm，比例、UV、材質及貼圖路徑檢查通過；9 個 GLB 均包含單一網格、材質及內嵌貼圖。見 reports/export-verification.json。
- 已檢視 LOD0 的材質實際渲染與線框，以及各低階 LOD 的多角度圖。previews/ 內圖片皆為 Blender 渲染，不是 Unity 截圖。

## 模型規格

| 模型 | 尺寸（Blender X/Y/Z，公尺） | LOD0 / LOD1 / LOD2 三角面 | 材質 |
| --- | --- | --- | --- |
| LowGrass | 0.90 × 0.70 × 0.36 | 1,212 / 552 / 248 | 1 |
| TrampledGrass | 1.50 × 0.90 × 0.28 | 2,452 / 1,116 / 492 | 1 |
| StreamBank | 4.00 × 4.00 × 約 0.429，含岸石 | 736 / 464 / 288 | 1 |

接岸中央行走面從前緣 0.03 m 上升至後緣 0.33 m，4 m 長度上升 0.30 m，坡度約 4.29°。岸石位於兩側。COL_StreamBank 是獨立的簡化坡道網格，非顯示模型碰撞；草叢為無碰撞裝飾物。所有資產原點為底部中心，模型比例 1，Blender 前方 -Y。

## 圖片用途

- concepts/C01–C06：聚落出口、山道、採藥林、兔坡、淺灘、捷徑的視覺方向。概念圖中的遠景、建築、兔子數目或路面細節不能取代 layout.json 的座標和生成規格。例如兔坡圖顯示三群兔，但實際出生點仍為每群 2 個。
- references/V01–V03：建模前的三視圖。接岸圖有輕微透視與坡度誇張，模型以本文件公尺尺寸校正，沒有依圖面測量導航坡度。
- textures/T01、T02：各四格的兔足跡、泥土擾動圖集，可作地面線索。
- textures/T03：四片草葉的透明圖集，供後續製作草卡／材質使用。這版模型採實體低面數葉片及 T04 色盤，尚未使用草卡。
- 三張 AI 貼圖原檔為 1254 × 1254 RGBA，已確認有真正 alpha 透明度；原先清單的 1024 是建議引擎輸入尺寸，可在 Unity Import Settings 設 Max Size 1024。沒有冒稱原檔為 1024。

## Unity 匯入方式（待實測）

1. 複製 models/ 中所需 FBX 及 textures/T04_model-palette.png 到指定美術資源目錄，保留來源檔案供修改。FBX 使用 Unity 靜態網格軸向設定匯出，Model Scale Factor 建議 1、Convert Units 開啟。
2. 建立 URP/Lit 材質，將 T04 指定為 Base Map（sRGB），Metallic 0、Smoothness 約 0.12。將每個網格的 M_QingxiPalette 重新映射到此共用材質；不要依賴 FBX 自動建立正確 URP 材質。
3. 每套 LOD 是分檔 FBX，需要整合方建立 Prefab／LODGroup；目前沒有宣稱已建立 Unity Prefab 或自動切換。
4. 草叢不新增 Collider。接岸將 COL_StreamBank 用作獨立簡化 MeshCollider，顯示網格不掛高面數碰撞；確認中央可走通、岸邊與現有地形接縫無台階。
5. T01/T02 依選用的 URP 貼花或貼地平面流程處理 alpha，驗證邊緣混色。草葉圖集尚需整合方按圖案實際邊界設定 UV，不能假定每片葉子精準位於等寬格子內。

## 已接受的 QA 提醒與限制

- UV0 刻意疊放到共用色盤區域，QA 因而回報 UV overlap。這是顏色圖集的重用，不適合用作獨立細節烘焙或 lightmap；需要靜態光照時另產生不重疊 UV2。
- LowGrass LOD0 有 1 對內部背對背接觸面提醒，位於葉片接觸處；保留封閉葉片體積，並非同方向共面閃爍。其餘幾何錯誤均已修正；倒伏葉片原本的 z-fighting 已透過分離葉片路徑解決。
- 低階 LOD 減少葉片與岸石，細部與輪廓會變簡單，切換距離需在遊戲鏡頭實測後設定。
- 這是第一版低面數環境資產；沒有風動、草動觸發、兔 AI、音效、採集或交易程式。
- **Unity 未匯入驗證、未測 NavMesh、手機效能與多人行走。** Blender 回匯通過不代表已通過 Unity 驗收。

## 重建與驗證

需 Blender 5.2.2 及本機已安裝的 EL4CTEO/blender-skills（來源版本 71d031dab8bc6729504d11a78cbe91945401045f）。預設讀取 ~/.codex/skills，可用 QINGXI_SKILLS 指向其他安裝位置。

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --factory-startup --python-exit-code 1 --python .\tools\build_assets.py
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --factory-startup --python-exit-code 1 --python .\tools\verify_exports.py
```

工具僅在新背景 Blender 程序執行，重建本版本內的產物，不修改使用者已開啟的 Blender 場景。若要開始新版，先複製成新版本目錄，避免覆寫人工修改。
