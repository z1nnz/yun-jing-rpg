# 2026-10-26 分支與驗證紀錄

本輪以 `origin/main` 為底，合併 `origin/feature/qingxi-reuse-world-v2`、`origin/very-strong`、`origin/feature/qingxi-hunt-graybox-johnny`。前者帶入青溪美術原稿與河岸，後兩者帶入鎮區和採獵灰盒。整合提交由 z1nnz 身分建立；其他人的來源仍依各自原提交與 [工作登記](work-ownership.md) 保留。

衝突處理：兩個同名採獵 Builder 以 `QingxiHuntStandaloneBuilder` 區分；FishNet 固定在 4.7.4R；專案 Unity 版本保留 6000.0.82f1；角色輸入檔保留第三人稱實際操作邏輯。沒有刪去任何一方的獨立場景工作。

`origin/assets/dondon-import`、`origin/very-string-donon` 為舊版素材快照，與目前 main 的較新 Dondon 交接檔衝突，沒有整枝覆蓋。`origin/chore/collaboration-workflow` 的功能已在 main 的 `CONTRIBUTING.md`，沒有把舊版流程覆蓋上去。其他分支未因此宣稱完成整合。

驗證界線：API／持久化測試可在本機執行；PWA 圖片頁與既有玩法頁以瀏覽器檢查。Unity 編譯曾受 Editor 授權錯誤 198 阻擋，且使用者此輪要求先以 PWA 驗證，所以此整合版**沒有 Unity 編譯、玩家建置、即時多人或手機原生效能通過證據**。Blender 圖片只是建模畫面，不是可玩遊戲截圖。
