# 《雲境》共同開發流程

儲存庫：<https://github.com/z1nnz/yun-jing-rpg>

## 權限與合併方式

- `@z1nnz` 是擁有者，保留管理與合併權限。
- `@joshsu54` 是獲准自行合併的協作者，使用 Write 權限。接受邀請後，可以推送自己的分支、建立 PR，檢查通過後自行合併，**不必等待 z1nnz 審查或核准**。
- 其他人不授予 Write／Maintain／Admin 權限；可透過 fork 提出 PR，但不能自行合併。
- `main` 透過 PR 更新，不直接推送、不強制推送、不刪除。每個 PR 只處理一項可驗收工作。
- 必須通過 `API and persistence tests` 與 `LFS asset integrity`，處理完討論並同步最新 main，才合併。

目前的「只有 joshsu54 可自行合併」由協作者權限名單實現，並非 GitHub 對該帳號設定了個人合併例外。**日後不要直接新增其他 Write／Maintain／Admin 協作者**：這會讓對方也能在相同規則下合併，必須先重新設計權限。擁有者不設定跳過 main 規則的例外。

本流程參考 [Nudge 協作流程](https://github.com/z1nnz/graduation-project-nudge/blob/main/CONTRIBUTING.md)，保留分支、PR、檢查與同步方式；依本專案擁有者要求取消人工核准門檻。

## 第一次加入

1. 用 `joshsu54` 登入 GitHub，接受 [協作邀請](https://github.com/z1nnz/yun-jing-rpg/invitations)。邀請未接受前仍無法推送。
2. 安裝 Git、Git LFS、Node.js 22。GitHub 推送使用自己的 GitHub 登入授權，不使用帳號密碼或別人的 Token。
3. 在自己選擇的工作目錄執行：

```powershell
git lfs install
git clone https://github.com/z1nnz/yun-jing-rpg.git
cd yun-jing-rpg
git config user.name "你的名字"
git config user.email "你的 GitHub 驗證信箱或 noreply 信箱"
git config pull.ff only
git lfs pull
npm ci
npm test
```

GitHub CLI 可選：安裝後執行 `gh auth login`，選擇 GitHub.com、HTTPS 與瀏覽器登入。不要把權杖貼進聊天或提交進儲存庫。

先讀 [AGENTS.md](AGENTS.md)、[目前狀態](docs/status.md)、[核准方案](docs/approved-plan.md)。素材工作另讀 [素材交接清單](docs/素材交接清單-dondon.md)。

## 開始工作

先確認沒有尚未處理的本機修改，再從最新 main 開分支：

```powershell
git status
git switch main
git pull --ff-only origin main
git switch -c assets/dondon-import
```

第一次交付素材可用 `assets/dondon-import`。往後每項工作另開新名稱，例如：

- `assets/joshsu54-player-animation`
- `feature/joshsu54-cave-storage`
- `fix/joshsu54-herb-material`

開工前在 Issue 或 PR 說明這次要改哪些檔案。兩人不要同時修改同一個 Blender 檔案或 Unity 場景；二進位檔案無法像程式碼逐行合併。

## 朋友的素材如何交付

原始素材放在 `art/incoming/dondon/<素材名稱>/<版本>/`，依 [交接清單](docs/素材交接清單-dondon.md)附 `.blend`、FBX、貼圖、骨架動畫、參考圖、來源與驗證紀錄。先交付原始素材，之後再用另一個 PR 整合進 Unity，避免整包覆蓋現有遊戲。

- `.blend`、`.fbx`、`.glb`、`.png` 等依根目錄 `.gitattributes` 使用 LFS。不要用瀏覽器拖拉大型素材代替本機 Git LFS 推送。
- 已有素材缺少建模前 AI 參考時如實註明；在本專案自行製作模型，必須先用 AI 生成該物品三視圖，檢視並保存後再建模。
- 將資源正式放進 Unity `Assets` 時，連同對應 `.meta` 提交；移動或改名時保留 GUID，不把 `Library`、`Temp` 或建置產物提交。
- 不能提交憑證、私鑰、真實使用者資料、樹伴正式資料或本機資料庫。

例如只加入這次的兩個角色素材資料夾：

```powershell
git add art/incoming/dondon/QPlayerMale art/incoming/dondon/QPlayerFemale
git diff --cached --stat
git diff --cached
git lfs status
git commit -m "assets: add player source models and animations"
git lfs fsck
git push -u origin assets/dondon-import
```

上例的資料夾必須已存在；不同任務請換成實際路徑。不要直接使用 `git add .` 把無關修改一起加入。LFS 檔案必須成功上傳，不能只提交指標。

## 開 PR、檢查與自行合併

1. 在 GitHub 點 **Compare & pull request**，Base 選 `main`，Compare 選自己的分支。
2. 填寫 PR 範本，說明做了什麼、驗證結果和未完成項目。模型附預覽，操作功能附重現步驟。
3. 等待兩個 GitHub Actions 檢查通過：
   - `API and persistence tests`：安裝 Node 依賴、編譯 TypeScript、執行測試。
   - `LFS asset integrity`：下載該提交所需的大檔案並檢查 LFS 完整性。
4. 如果 main 已更新，先依下一節同步並重新跑檢查。處理所有未解決的 PR 討論。
5. `@joshsu54` 或 `@z1nnz` 可按 **Squash and merge** 並確認。**不需要另一個人的 Approve，也不需要指定 z1nnz 為 Reviewer。**
6. 合併後可在 GitHub 刪除已合併分支。下一項工作從最新 main 重新開分支。

若只有檢查顯示排隊，等待即可；若失敗，查看 Actions 日誌，修正後推送到同一分支。不要用刪除測試、停用規則或強制推送來繞過。

使用 GitHub CLI 也可以建立與合併 PR：

```powershell
gh pr create --base main
gh pr checks --watch
gh pr merge --squash
```

## 同步 main 與修正衝突

在自己的工作分支執行：

```powershell
git fetch origin
git merge origin/main
# 如有衝突，處理後只加入已確認的檔案，再提交
npm test
git push
```

不要使用 `git push --force`。模型衝突先與另一位製作者確認採用哪一份，不要無條件選 ours/theirs。需要取消尚未完成的衝突合併時，可執行 `git merge --abort`。

PR 合併後：

```powershell
git switch main
git pull --ff-only origin main
git lfs pull
```

Squash 合併後，舊工作分支的 commit ID 不會等同 main；不必為了清理本機分支而使用強制刪除，可先保留。

## 本機開發與驗證

Windows 在儲存庫根目錄執行：

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\start-local.ps1
```

開啟 <http://127.0.0.1:4310>。每位開發者使用自己的 `.data`；測試身分只允許 local 模式及 loopback，不把服務公開到網際網路。啟動腳本會建立本機金鑰，不需要向另一位開發者索取。

程式修改至少執行 `npm test`。模型修改依交接清單檢查原檔、匯出、貼圖與動畫；LFS 檢查成功不代表模型美術或動畫已驗收。

Unity 使用 `6000.0.82f1`，開啟 `apps/game`；URP、FishNet 等版本以 `Packages/manifest.json` 為準，不自行升級。Editor 安裝在不同位置時可指定路徑：

```powershell
.\tools\unity.ps1 -Target Generate -EditorPath 'C:\你的Unity安裝目錄\Editor\Unity.exe'
```

目前 GitHub Actions **不包含 Unity 編譯、即時多人、Android／iOS 真機或手機效能驗證**。修改 Unity 程式時另附編譯／操作結果；授權或環境阻擋時明示未驗證，不能以 API 測試綠燈宣稱遊戲可運行。

## 出問題時怎麼還原

先停下相關修改，在 GitHub 對已合併 PR 使用 **Revert** 建立還原 PR，或在新分支對相應提交執行 `git revert`。仍經檢查再合併，不改寫 main 歷史。

如果涉及資料庫或資產格式變動，PR 必須另外說明資料遷移與回復方式；還原程式不會自動還原已變動的資料。
