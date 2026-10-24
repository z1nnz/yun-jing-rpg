# 共同開發

儲存庫：<https://github.com/z1nnz/yun-jing-rpg>

## 規則

- `main` 只透過 Pull Request 更新，不直接推送或強制推送。
- 一個 PR 只處理一件可驗收工作。
- 合併前必須通過 `API and persistence tests` 與 `LFS asset integrity`。
- `@joshsu54` 有 Write 權限，可在檢查通過後自行 squash merge，不需要另一人 Approve。
- 其他協作者在權限確定前使用 fork 或由擁有者建立分支，不直接增加 Write 權限。
- 不同人不要同時修改同一個 `.blend`、Unity 場景或其他二進位檔。

## 第一次設定

```powershell
git lfs install
git clone https://github.com/z1nnz/yun-jing-rpg.git
cd yun-jing-rpg
git config pull.ff only
git lfs pull
npm ci
npm test
```

使用自己的 GitHub 登入，不分享 Token。開工前讀 [AGENTS.md](AGENTS.md)、[目前狀態](docs/status.md)和任務 Issue。

## 每項工作

```powershell
git switch main
git pull --ff-only origin main
git switch -c feature/短名稱
```

只加入本次檔案：

```powershell
git add path/to/file
git diff --cached --stat
git lfs status
git commit -m "type: concise change"
git push -u origin feature/短名稱
```

PR 需寫明：完成內容、驗證方式、尚未完成項目。模型附預覽、來源、三視圖、尺寸、面數、LOD、碰撞及動畫清單。

```powershell
gh pr create --base main
gh pr checks --watch
gh pr merge --squash
```

檢查失敗就修正同一分支，不刪測試、不關規則、不強制推送。main 更新時執行 `git fetch origin`、`git merge origin/main`、重新測試再推送。

## 素材

- `.blend`、`.fbx`、`.glb`、圖片與音訊使用 Git LFS。
- 新模型必須先保存經檢視的 AI 三視圖，再開始建模。
- 外部素材必須附作者、來源、授權與必要標示。
- Unreal 快取、Unity 快取、建置產物、私鑰、正式資料及本機資料庫不得提交。
- `dondon2.0` 交付格式見 [素材清單](docs/素材交接清單-dondon.md)。

程式修改至少執行 `npm test`。Unity 修改必須附 Editor 編譯或明示尚未驗證；GitHub 的 API CI 不包含 Unity、手機或多人實測。
