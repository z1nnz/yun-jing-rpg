# 青溪工作與來源登記

更新：2026-10-26。此表用來避免重做；「z1nnz／Codex 協作」表示由 z1nnz 指導、Codex 在其專案中製作或整合，不把協作者原創誤記為 z1nnz 獨作。

| 內容 | 原始製作／來源 | 本輪整合與狀態 | 下一位可做的事 |
|---|---|---|---|
| 樹伴成樹 | z1nnz 的 `elder-tree-esg`，母稿保存在 [原檔副本](../art/source/elder-world-tree-garden-original.blend) | z1nnz 原作／Codex 移植：v11 將完整原樹 96 個物件、16 組葉冠放入青溪，保留原方向與樹形，取消 v10 補葉；[實際畫面](../art/previews/qingxi-world-v11/original-tree-in-world.png) | 葉色與樹伴 Unity 渲染仍未完全一致；需做材質、LOD、碰撞及引擎驗證，不要重新生成或複製葉冠。 |
| 青溪河岸與流動水樣片 | z1nnz／Codex 協作；既有 v8 | Blender 動畫及畫面已保存，水位／泡沫為樣片 | 實際遊戲水材質、遮擋和手機效能。 |
| 河岸蘆葦、蕨草花叢、苔石、木路燈 v2 | z1nnz／Codex 協作；先有 [AI 三視圖](../art/references/qingxi-detail-props-v2/three-view.png) | 有獨立 Blender 原稿、GLB 和近景預覽；質感仍是初版 | 精修紋理、近景細節及 LOD；不要做重名初版。 |
| 客舍及鎮區模型 | z1nnz／Codex 的客舍 v1；joshsu54／Dondon 的模型依來源分別登記 | 已放入青溪組裝及協作者鎮區分支，兩者不能互稱原創 | 選用時保留來源，修改不要覆寫交接原件。 |
| 青溪鎮與採獵區 Unity 場景 | joshsu54 分支 `very-strong`、Johnny 分支 `feature/qingxi-hunt-graybox-johnny` | 已在整合分支合併，保留兩個獨立 builder；Unity 整合版尚未編譯 | 待可用 Editor 再驗證，避免同時改同一生成場景。 |
| 山兔掉落與售出 API | z1nnz／Codex 協作 | 服務端原型及冪等測試完成 | 協作者 A 做模型／動畫；區域程序仍需實際命中、距離及死亡事件接線。 |
| 青溪視覺檢視 PWA | z1nnz／Codex 協作 | 圖片和現有玩法測試頁可在瀏覽器查看；不等於 3D 客戶端 | 協作者 C 做獨立行走鏡頭樣片，不改登入 API。 |

對 [三位協作者 14 小時任務](execution/2026-10-26/06-three-collaborators-14h.md)，A 管山兔、B 管路岸拼件、C 管 PWA 行走。核心組保留樹伴成樹、主場景整合、服務端資產帳本與驗收。新交付先看此表與分支，再開始製作。
