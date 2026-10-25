# 青溪河岸與古樹視覺樣片 v8

這一版處理河岸草列、樹根與水面。可直接看 [水位基準畫面](../art/previews/qingxi-world-v8/riverbank-flow-frame-001.png)、[微漲畫面](../art/previews/qingxi-world-v8/riverbank-flow-frame-036.png)、[微退畫面](../art/previews/qingxi-world-v8/riverbank-flow-frame-078.png)。三張是 Blender 動畫第 1、36、78 幀的實際渲染，並非 Unity 截圖。

## 可重複擺放的零件

先保存並檢視 [草／花／河石三視圖](../art/references/qingxi-prop-kit-v1/three-view.png)，再建立 [可編輯母稿](../art/source/qingxi-prop-kit-v1.blend)。草叢 82 三角面、野花叢 112 三角面、河石 80 三角面；各有獨立 GLB，位於 `art/exports/qingxi-prop-kit-v1/`。它們可以獨立改大小、旋轉和位置，固定亂數種子便於比較版次。

樣片移除了七段河岸原本整齊的草列，重新擺放 313 叢草、57 叢花和 53 塊石頭。這是場景擺位數，不表示 423 次獨立繪製呼叫已經可接受；需在 Unity 使用實例化或合批並實測。

Blender 原稿與 GLB 往返的幾何 QA：三種零件均通過，無錯誤。草葉與花葉平面投影的 UV 重疊屬共用材質用法，不能直接拿來烘焙獨立貼圖；GLB 另有頂點拆分警告。報告在 `art/exports/qingxi-prop-kit-v1/`。目前花草外觀仍是低面數初版，尤其近鏡頭葉片、花朵與河石紋理還需要精修。

## 樹根

先保存並檢視 [根部銜接三視圖](../art/references/qingxi-root-transition-v1/three-view.png)。場景中的樹來自本機 `elder-tree-esg/其他工作副本/app-ready-20260828/art-source/blender/生命樹庭園_母稿.blend` 的樹幹、樹枝、樹冠與盤根集合；沒有讀取樹伴正式資料或憑證。移植來源與範圍見 `art/exports/elder-world-tree-hero-v1/provenance.json`。

在 [v8 可編輯場景](../art/source/qingxi-world-flora-water-v8.blend) 中，樹從河沿移到岸內 `(12, 5)` 公尺；距離樹底 2.7 公尺以下的外伸根按高度逐步收攏，根部接入不規則草土丘，周圍以小草與石塊銜接。這是場景版修整，原始移植樹 GLB 仍保留。原始樹 GLB 為 147,222 三角面，現有幾何 QA 未通過：大量獨立葉片被判為游離島，另有少量樹冠面重疊。正式手機資產仍需 LOD、碰撞代理、葉片檢查和實機效能驗證。

## 河流動畫

七段河岸共有 14 個淺水／深水網格與 7 條岸線泡沫。Blender 動畫讓紋理沿河道移動，表面採兩組錯相起伏形態，水位在一個 121 幀循環中最高比基準高 3.2 公分、最低低 1.8 公分；泡沫岸線左右約移動 7 公分。水位使用場景原始標高為基準，避免退水時露出下方灰盒河面。動畫參數與擺位數見 `art/previews/qingxi-world-v8/build-report.json`。

這是可檢視的 Blender 視覺原型。Unity 對應水材質、流向、岸邊碰撞、游泳／浮力、手機效能尚未實作與驗證；目前 Unity Editor 授權仍阻止編譯和試玩。世界其餘地面、房屋周邊道路和遠景也仍有灰盒區域，不能將這三張預覽解讀為全世界已完成。

## 產製與重建

先執行 `tools/art/build_qingxi_prop_kit_v1.py`，再以 `art/source/qingxi-world-lookdev-v7.blend` 為起點執行 `tools/art/integrate_qingxi_world_v8.py`。兩個腳本皆需 Blender 5.2。零件 QA 由 `tools/art/qa_qingxi_prop_kit_v1.py` 分別檢查原稿及 GLB。原本的樹與河岸依賴 `tools/art/extract_elder_tree_garden_hero.py`、`tools/art/build_qingxi_riverbank_v2.py` 與 `tools/art/integrate_qingxi_world_v7.py`。
