# 青溪水工 B：AI 正／側／背三視圖

完成日期：2026-10-28。依使用者最後指示，本次僅製作 B01–B12 的 AI 參考圖，不包含模型、GLB／FBX、路線場景、玩法、API 變更或操作錄影。

- 創作／整理：Codex；圖像生成：OpenAI 內建 image_gen；依使用者青溪水工 B 工作包製作。
- 12 件均為本輪新生成的外觀設計；沒有複製 irrigation-v2/water-channel 或其他既有模型。
- 已逐張目視檢視，修正五件圖的明顯開口／方向／尺寸問題。這是概念三視圖，部分主視圖仍有輕微俯視或展示姿態；不是精密 CAD 正投影或完成接合驗收的模型。
- 標註尺寸為設計提案，未經實物／模型量測。尺寸與圖像比例衝突時，以本文件數值為準。每件的具體注意事項見 image-manifest.json。
- 提示詞見 prompts.json；修圖提示見 revision-prompts.json；drafts/ 僅留存五張被取代的初稿，不作建模依據。
- 主要 GitHub 上傳位置依使用者指定為 https://github.com/z1nnz/yun-jing-rpg ，依 CONTRIBUTING.md 經分支與 PR。此次檔案只保存本機，尚未上傳；目前工作資料夾沒有 .git。

## 圖片與尺寸

| ID | 物件／最終三視圖 | 設計尺寸 | 作者與狀態 |
|---|---|---|---|
| B01 | [舊水路方形基座](B01_three_view.png) | 140 × 140 × 40 cm；前後接口外寬60 cm、淨寬40 cm | Codex／OpenAI image_gen；已生成及檢視，未建模 |
| B02 | [可拼接直線石槽](B02_three_view.png) | 100 × 60 × 40 cm；兩端開放 | Codex／OpenAI image_gen；已生成及檢視，未建模 |
| B03 | [可拼接彎角石槽](B03_three_view.png) | 100 × 100 × 40 cm；90°轉彎 | Codex／OpenAI image_gen；已生成及檢視，未建模 |
| B04 | [分流三通石槽](B04_three_view.png) | 120 × 100 × 40 cm；前進左右出 | Codex／OpenAI image_gen；已生成及檢視，未建模 |
| B05 | [木製手動閘板](B05_three_view.png) | 框80 × 30 × 150 cm；閘板44 × 40 × 5 cm；上提32 cm | Codex／OpenAI image_gen；已生成及檢視，未建模 |
| B06 | [青銅水位閘輪](B06_three_view.png) | 輪徑50 cm；軸長35 cm；方軸20 mm；軸心距地90 cm | Codex／OpenAI image_gen；已生成及檢視，未建模 |
| B07 | [漏水裂縫補石](B07_three_view.png) | 補石45 × 20 × 8 cm；A接口待核對 | Codex／OpenAI image_gen；已生成及檢視，未建模 |
| B08 | [河底清淤篩](B08_three_view.png) | 篩框60 × 45 × 12 cm；柄110 cm；網孔10 mm | Codex／OpenAI image_gen；已生成及檢視，未建模 |
| B09 | [測流浮標](B09_three_view.png) | 浮體25 × 12 × 10 cm；桅20 cm；繩60 cm | Codex／OpenAI image_gen；已生成及檢視，未建模 |
| B10 | [壓水木樁組](B10_three_view.png) | 樁截面12 × 12 cm；總長80 cm、入土30 cm；梁100 × 16 × 16 cm | Codex／OpenAI image_gen；已生成及檢視，未建模 |
| B11 | [水工材料推車](B11_three_view.png) | 總長180 cm、寬85 cm；車床120 × 75 cm；輪徑60 cm | Codex／OpenAI image_gen；已生成及檢視，未建模 |
| B12 | [公共工程完工碑座](B12_three_view.png) | 底座80 × 60 × 25 cm；含底座總高110 cm | Codex／OpenAI image_gen；已生成及檢視，未建模 |

## 共用接口與操作高度

- B01–B04 石槽接口：外寬60 cm、總高40 cm、淨寬40 cm、底厚10 cm、左右壁厚各10 cm；提案水深18 cm。端面平齊、槽底連續，不在水道中加封端石。
- 接縫提案：20 mm密封墊與20 mm承座凹槽。這是外觀及尺寸意圖，壓縮量、公差、防漏與碰撞尚未設計／驗證。
- B02 是100 cm短模組，與舊 irrigation-v2 的200 × 60 × 24 cm 長槽不同。
- B05 閘板淨跨40 cm，板寬44 cm含兩側各2 cm導槽；關閉時板底在槽底距地10 cm，開啟上提32 cm。
- B06 軸心距地90 cm、輪緣65–115 cm；B05 操作握把105 cm；B08 操作握柄約95 cm；B11 推車握柄95 cm。以175 cm角色檢查時應在站姿可及範圍，仍須後續模型／操作驗證。
- B10 支撐梁頂50 cm適用局部高程支撐，不能直接把它塞在地面槽段下造成水路跳高；以同高程路線或地形落差安裝。樁根入土30 cm。
- B12 含底座總高110 cm，底座25 cm，上方碑體85 cm。
- 人物剪影多為獨立比例參考，不代表各張主圖皆與人物按同一像素比例繪製。B01高40 cm約為175 cm角色身高23%；B05高150 cm約86%；B12高110 cm約63%。

## 既有灌溉素材與背景

只讀取既有 irrigation-v1 的文字提示與 irrigation-v2 報告來理解材質語彙。本機舊 PNG／模型為 Git LFS 指標，未假稱已看過其實際內容。沒有匯入、重製或計入任何既有模型作本次新件。

B05／B06／B07／B08／B09／B10 中的槽段或安裝環境是新生成的說明背景，不屬各物件新增數量。B07 的「A破槽」僅示意，尚缺精確來源與接口尺寸。

## 最終圖片索引

### B01 舊水路方形基座

![B01 舊水路方形基座 正側背三視圖](B01_three_view.png)

### B02 可拼接直線石槽

![B02 可拼接直線石槽 正側背三視圖](B02_three_view.png)

### B03 可拼接彎角石槽

![B03 可拼接彎角石槽 正側背三視圖](B03_three_view.png)

### B04 分流三通石槽

![B04 分流三通石槽 正側背三視圖](B04_three_view.png)

### B05 木製手動閘板

![B05 木製手動閘板 正側背三視圖](B05_three_view.png)

### B06 青銅水位閘輪

![B06 青銅水位閘輪 正側背三視圖](B06_three_view.png)

### B07 漏水裂縫補石

![B07 漏水裂縫補石 正側背三視圖](B07_three_view.png)

### B08 河底清淤篩

![B08 河底清淤篩 正側背三視圖](B08_three_view.png)

### B09 測流浮標

![B09 測流浮標 正側背三視圖](B09_three_view.png)

### B10 壓水木樁組

![B10 壓水木樁組 正側背三視圖](B10_three_view.png)

### B11 水工材料推車

![B11 水工材料推車 正側背三視圖](B11_three_view.png)

### B12 公共工程完工碑座

![B12 公共工程完工碑座 正側背三視圖](B12_three_view.png)
