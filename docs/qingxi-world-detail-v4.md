# 青溪世界：房屋細化與既有樹素材 v4

本輪從大範圍擺位轉進第一棟可重複製作的近景房屋。目標是逐步建立有層次的仙俠村落，而非把五張方向圖直接當作遊戲畫面。使用者提出的《原神》大世界是品質與探索感目標；目前圖像仍是 Blender 視覺樣片，距離完整遊戲還有地形、水體、材質、角色、互動及真機驗證工作。

![青溪客舍與移植成樹](../art/previews/qingxi-world-v4/qingxi-detailed-house-and-reused-tree-v4.png)

## 這次已做的實體內容

- 先生成、檢視並保存 [青溪客舍三視圖](../art/references/qingxi-riverside-house-v1/three-view.png)，再依統一尺寸建模。
- 建出石基座 9.35 × 7.35 公尺、含屋檐與翹角整體約 10.8 × 9.49 × 6.64 公尺的臨水客舍：逐片起伏瓦面、屋脊與翹角、前廊、木柱斗拱、雙扇門、格窗、燈籠、石基座與台階。可編輯原稿是 [Blender 檔](../art/source/qingxi-riverside-house-v1.blend)；[建模腳本](../tools/art/build_qingxi_riverside_house.py)可重建。
- 原稿保留 360 個可單獨替換的網格部件；FBX／GLB 匯出按材質合併為 9 個網格，約 11,128 個三角面。匯出檔位於 `art/exports/qingxi-riverside-house-v1/`。
- 從 `elder-tree-esg` 的**美術素材**複製生長階段 GLB，記錄來源雜湊，選其成樹作村落近景。未移植整座生命樹浮島。其來源及現階段限制見 [素材記錄](../art/incoming/elder-tree-esg/README.md)。
- 在 [v3 場景](../art/source/qingxi-world-art-directed-v3.blend)替換一處舊房並放入移植成樹，保存 [v4 可編輯場景](../art/source/qingxi-world-detail-v4.blend)。

房屋單獨檢視：[斜前方](../art/previews/qingxi-riverside-house-v1/front-three-quarter.png) · [正面](../art/previews/qingxi-riverside-house-v1/front-elevation.png) · [屋頂與前廊](../art/previews/qingxi-riverside-house-v1/roof-and-veranda.png)。

## 驗證與限制

- Blender 5.2.2 順利重建、匯出 FBX／GLB 並重新匯入 GLB；可編輯原稿和匯出檔的 `blender-asset-qa` 均為 `pass: true`、零錯誤。結果分別在 `qa-report.json` 和 `export-qa-report.json`。
- 原稿剩下兩處台階相貼的隱藏背面和燈籠套內的封閉構件警告，屬目前不可見的接合／結構；正式效能整理時應刪除無用面。
- 匯出檔 UV 有重疊、合併網格有未焊接的零件頂點。這版使用純色材質與模型細節，尚未烘焙貼圖；在製作正式材質圖集之前，不能直接用這份 UV 做 AO／法線烘焙。
- 移植成樹未做 LOD、碰撞、風動或手機效能測試。房屋亦未完成貼圖圖集、LOD、物理碰撞與 Unity 匯入測試；Unity 授權問題仍讓編譯及試玩無法驗證。
- v4 圖中的地面、河道、岸線和懸崖仍屬灰盒／既有低細節素材；沒有宣稱達到《原神》的視覺品質。

## 往下怎麼製作

1. 以這棟房為樣板，把屋瓦、屋角、門窗、廊柱和石基拆成可複用規格；做兩種尺寸與一種功能建築變體，村落不再只複製同一棟房。
2. 先做青溪溪岸的地形過渡、石岸、道路、土坡、植被與水體，使房屋不再站在平板上。每一種新模型仍需先保存 AI 三視圖。
3. 對常見樹、移植成樹、石塊、橋梁與房屋建立 LOD、碰撞和材質圖集；優先看玩家步行視角的近景質量，再處理遠景山門。
4. Unity 授權可用後，把一小段「客舍 → 橋 → 古樹」做成可走路的區域，量測手機 30 分鐘的幀時、記憶體與熱狀態，再擴大片區。

在可步行切片之前，暫不量產整個州域。真正的精細大世界靠同一套建築、植被、石頭、地形和光照規格反覆迭代，而不是逐一做完每棟獨一無二的房屋。
