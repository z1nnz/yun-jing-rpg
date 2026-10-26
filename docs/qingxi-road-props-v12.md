# 青溪道路與小物件 v12

**製作：z1nnz 指導／Codex 實作；日期：2026-10-26。** 原稿 [qingxi-road-props-v12.blend](../art/source/qingxi-road-props-v12.blend)、[重建腳本](../tools/art/build_qingxi_road_props_v12.py)、[來源與三視圖](../art/references/qingxi-road-props-v12.md)。這是可供場景組裝的 Blender 美術資產，不是已接入的 PWA 3D 場景或 Unity 可玩內容。

可用 [手機／桌面 PWA 圖片檢視頁](../tools/art-preview-v12/index.html)並列參考與實際模型；從儲存庫根目錄啟動靜態 HTTP 伺服器後開啟 `/tools/art-preview-v12/`。協作者 C 的動線試走頁保持獨立。

| 資產 | 用途 | 三角面／網格 | 預覽 |
|---|---|---:|---|
| 不規則土路 v2 | 12 m 拼接樣片；草地、石子、花草與散置岩塊 | 12,320／115 | [斜視](../art/previews/qingxi-road-props-v12/road-oblique.png) · [俯視](../art/previews/qingxi-road-props-v12/road-top.png) |
| 橋邊木欄 | 木橋兩側可重複擺放的 2.4 m 單段 | 744／10 | [預覽](../art/previews/qingxi-road-props-v12/bridge-rail.png) |
| 採藥晾架 | 村屋與靈田附近的生活道具 | 1,004／51 | [預覽](../art/previews/qingxi-road-props-v12/herb-rack.png) |
| 苔石路標 | 岔路導引，牌面留給區域文字 | 384／6 | [預覽](../art/previews/qingxi-road-props-v12/waymarker.png) |

表中是匯出 GLB 後**重新匯入量得**的三角面與網格數；[往返報告](../art/exports/qingxi-road-props-v12/roundtrip-report.json)保存在輸出目錄。各資產獨立 GLB，原稿保留四個獨立 Collection。路面中心通行帶約 2.4 m；道路首尾輪廓可接，但這版未量測連續拼接時植被與高度的視覺接縫。

[QA 報告](../art/exports/qingxi-road-props-v12/qa-report.json)由 Blender 5.2 game profile 對四個資產組分開檢查，均 **0 錯誤**。仍有警告：草花片面共用 UV、木圓柱端面是 n-gon、部分接合處有隱藏背對背面，橋欄與晾架後續可再減面。道路岩石、草叢和新物件的質感仍比五張世界方向圖簡化得多；要接近使用者希望的精細開放世界效果，仍需美術雕塑／貼圖烘焙、LOD、碰撞、光照、動作手感、技能特效和真機長時間效能測試。這版沒有完成《原神》同等畫質或操作。

**分工邊界：**此件是核心組在既有 S 型土路上做近景材質與裝飾變體；協作者 B 的三段可交換道路、橋頭與河岸銜接件維持獨立任務，不能用這件代替 B 的交付。協作者 C 維護 `tools/world-preview/` 互動動線；本批圖片可供其引用，但核心組不覆寫 C 的頁面。
