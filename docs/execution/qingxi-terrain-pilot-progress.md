# 青溪入口地形試點進度（2026-10-29）

本輪只改 `QingxiWorldPreview` 的 180 × 140 m 入口片區。`QingxiUnifiedWorld` 的大城鎮仍使用原本 Blender 匯出的 `Town_Terrain`，**尚未換成這套 Terrain**；不能把兩個場景的測試當成同一張已整合地圖。

實際 Unity 場景的當前俯視截圖是 [`current-unity-overhead.png`](../../art/previews/qingxi-terrain-pilot-v1/current-unity-overhead.png)。這張圖不是早期 `qingxi-world-blockout-v1.png`；它顯示地形試點已生成，也顯示資產仍稀疏，並非完成的大世界。原始 Dondon FBX 在此 Preview 中曾以厘米單位縮到 0.01 倍，修正後只對 `CollaboratorWorldV1` 匯入件補 100 倍；原創客舍和 D02 橋保持原尺寸。

截至本紀錄，協作者 PR #45（上游水路模型與線索）和 #47（回村道具與互動）仍未合併到 `main`，也未接入這個 Preview 生成器；不能把它們算作俯視圖中已擺好的物件。已合併的模型也須個別擺進場景。整合時保留原作者署名，並以實際場景截圖確認尺寸與位置。

## 已實作

- `tools/qingxi-terrain/routes.json` 統一描述村口、分岔、古樹前、橋頭等路線；腳本由它產生接地驗收座標。
- Preview 的平面地基與五塊互相重疊的道路方塊換成 Unity Terrain。高度、四層地表材質、路口合併遮罩、路內不長草、NavMesh 都由腳本重建。
- 移除擋路的 `Broken array`；保留 FBX 匯入旋轉並把擺放模型的視覺底部落到地形。古樹前檢查點移至樹幹外；橋面兩端的碰撞坡道改為約 18°。
- 驗收工具要求至少載入 30 件擺放模型，避免 Git LFS 尚未取回時產生「零失敗」假象。
- 入口河邊的早期替代房舍改為已完成三視圖及 Blender 母稿的原創臨水客舍；主跨河橋改用 joshsu54 的 D02 木造梁橋。兩件均從既有來源複製為 Unity 可匯入 FBX，保留原作者與來源，生成器並檢查它們的可見包圍盒。

## 本機驗證

- 固定 Unity `6000.0.82f1`：`./tools/unity.ps1 -Target WorldPreview` 成功。
- `./tools/qingxi-terrain/check-grounding.ps1`：接入客舍與 D02 橋後**失敗 0、警告 3、通過 18**；34 件模型接地、0 組平面路面疊面、路內沒有草；四段村口／古樹／橋頭直線膠囊試走及 NavMesh 路徑均通過。報告在本機 `artifacts/terrain-check/qingxi-world-preview.md`。
- `node --test tools/qingxi-terrain/*.test.mjs`：9/9 通過。
- 拉回既有 Git LFS 城鎮素材後，`./tools/unity.ps1 -Target UnifiedWorldWindows` 生成及 Windows 建置成功；原城鎮路線報告 0 失敗，`QingxiLocalForagingSmoke` 通過。另以 `QingxiPlaySmoke.Run` 實際 Play Mode 驗證山兔逃跑、抓取，結果 PASS。這證明既有玩法沒有在本輪失效，**不代表新 Terrain 已套入 UnifiedWorld**。

剩餘警告為兩座橋的視覺包圍盒低於岸邊地面，以及橋頭道路橫向最高碰撞面差異。前者是橋跨水道的已知情況；後者須在玩家視角確認橋頭兩側是否真的有會絆倒角色的碰撞體，不能直接忽略。

## 下一段工作

先在有畫面的 Unity Editor 以 1.7 m 玩家視角檢查村口、分岔、古樹、橋頭，處理橋頭橫坡警告並保存截圖。之後須為 UnifiedWorld 鎮區的既有地形網格定義局部替換邊界，移除邊界內舊網格表面，再套入同一套道路／草遮罩與高度規則，重烘焙鎮區 NavMesh，跑山兔、採集和全路線試走。不能直接把 Preview Terrain 疊在 Town_Terrain 上，否則會重現疊面與碰撞問題。完成該片區後，才擴到小鎮、林地和山路。

手機效能、人工完整試玩與 UnifiedWorld 地形替換均未驗證。
