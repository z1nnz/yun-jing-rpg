# 2026-10-26 分支與 PR 整合檢查

檢查基準：`main` 的 `faf2094`。已列出當時所有遠端分支，對每個分支自分叉點以來修改的檔案逐一比對與 `main` 的 blob；「同檔」表示位元內容相同，不代表原 PR 已正式合併。此次沒有以覆寫新版主線的方式強制合併舊分支。

| 分支／PR | 自分叉點的變更檔 | 與 main 同檔 | 尚有差異 | 結論 |
|---|---:|---:|---:|---|
| `feature/qingxi-hunt-graybox`／[#13](https://github.com/z1nnz/yun-jing-rpg/pull/13) | 162 | 162 | 0 | 已經由 #17 帶入；留言後關閉重複 PR。 |
| `feature/qingxi-hunt-graybox-johnny`／[#14](https://github.com/z1nnz/yun-jing-rpg/pull/14) | 10 | 5 | 5 | 保持草稿；舊 Builder 會覆蓋目前較完整配置，manifest 亦有差異。已留言修正要求。 |
| `chore/unity-6000.0.85f1`／[#15](https://github.com/z1nnz/yun-jing-rpg/pull/15) | 51 | 45 | 6 | 保持開啟；Unity／FishNet 固定版本與現行主線不同，工具腳本也會移除 WorldPreview。已留言要求基於新版主線重整。 |
| `assets/joshsu54-qingxi-town-concept`／[#16](https://github.com/z1nnz/yun-jing-rpg/pull/16) | 29 | 29 | 0 | 已經由 #17 帶入；留言後關閉重複 PR。 |
| `assets/dondon-import` | 0 | 0 | 0 | 原工作已在主線。 |
| `chore/collaboration-workflow` | 4 | 2 | 2 | 其餘是過時的 README／CONTRIBUTING 內容，不回退主線文件。 |
| `feature/qingxi-rabbit-hunt` | 0 | 0 | 0 | 原工作已在主線。 |
| `feature/qingxi-reuse-world-v2` | 139 | 137 | 2 | 只剩 `.gitignore` 與進度文件的舊版本差異；保留主線。 |
| `feature/qingxi-world-foundation-v1` | 28 | 25 | 3 | Builder、忽略規則、進度文件已有後續版本；不覆寫。 |
| `integration/20261026` | 528 | 528 | 0 | 已經由 #17 帶入。 |
| `very-string-donon` | 0 | 0 | 0 | 素材交接已在主線。 |
| `very-strong` | 342 | 334 | 8 | 主要是舊版 Unity 設定、工具與狀態文件；第一人稱程式與現行主線不同，不整批覆寫。 |
| `docs/daily-14h-20261026` | 1 | 1 | 0 | 已經由 #18 帶入。 |

PR #13–#16 的當時 `API and persistence` 工作流程均回報成功；這些檢查不等於目前主線的 Unity 編譯、FishNet 雙端連線或手機效能通過。#14 為草稿且尚有整合衝突；#15 的剩餘差異需在最新版 `main` 上重新驗證。下一次每日檢查須先重新抓取分支和 PR，再判斷是否有新提交，不沿用本表當作新變更的測試結果。
