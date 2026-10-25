# 青溪世界視覺樣片 v3

以 [五張世界方向圖](../art/references/world-vision-v2/README.md)中的古樹村落、跨溪路線與山門遠景為構圖目標，在 [v2 組裝場景](qingxi-world-assembled-v2.md)上繼續擺放協作者已交付的模型。這是第一塊區域的立體視覺樣片，尚非完整大世界或 Unity 遊戲畫面。

![古樹與村落](../art/previews/qingxi-world-v3/qingxi-ancient-tree-village-v3.png)

![青溪與橋梁](../art/previews/qingxi-world-v3/qingxi-river-crossing-v3.png)

![山門遠景](../art/previews/qingxi-world-v3/qingxi-northern-sect-v3.png)

## 本輪具體製作

- 新增 126 個現成模型擺位，以共用網格的方式拼出溪岸棧道、第三座橋、北側崖壁、松林、竹林、苔石和山頂樹線；擺位見 [added-placements.json](../art/previews/qingxi-world-v3/added-placements.json)。
- 修正既有古樹 FBX 的材質節點顏色及場景縮放，使它在村落中心形成清楚的地標。現有模型的網格形狀沒有重新設計。
- 設定午後側光、輕霧、三個透視鏡頭，輸出 1920 × 1080 圖片。可編輯場景在 [qingxi-world-art-directed-v3.blend](../art/source/qingxi-world-art-directed-v3.blend)，重製腳本在 [art_direct_qingxi_world_v3.py](../tools/art/art_direct_qingxi_world_v3.py)。
- 沒有新製作獨立物件模型；新增形體全部來自交接素材的實例，所以沒有跳過「先生成 AI 三視圖，再自行建模」的規則。

## 驗證與現階段邊界

Blender 5.2.2 已完成三張渲染並重開 `.blend`；場景檢查顯示公尺單位、無遺失貼圖或連結路徑、無場景組織問題。古樹的幾何 QA 通過，沒有重疊閃爍或脫離零件。其 UV 有高度重疊，因本輪使用純色材質、未烘焙貼圖，暫時接受；將來若做貼圖烘焙須重新展 UV。古樹最低點在 0.8 公尺，因它站在 0.8 公尺的廣場土丘上，屬於場景擺位。

圖片裡的大片地面、筆直河槽、廣場基底與部分路面仍是灰盒。崖壁是現成模組的重複擺放，之後需做真正的坡地過渡、瀑布、水體材質與可行走碰撞。這些圖只驗證造型與視線，沒有手機效能或 Unity 編譯結論。
