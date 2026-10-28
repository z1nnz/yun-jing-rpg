# 青溪古水路修復 · 本機玩法測試

把青溪水工 B 套件的真模型照接口接起來，把水從溪邊水源送到村田。

**正式的玩法測試在 Unity**（`unity/`，獨立測試專案，不動 `apps/game`）。Blender 版（`blender/`）留著當美術預覽和錄影工具。規則只有一份：JS 的 `src/waterworks-core.mjs`。Unity 用的 C# 版每一步都要和 JS 版產生的 `tests/golden.json` 完全一致，伺服器之後也照同一套規則（`CONTRACT.md`）。

## Unity（Unity 6000.0.85f1，Built-in 管線）

```
Unity -batchmode -projectPath tools/qingxi-waterworks-b/unity -executeMethod Qingxi.Waterworks.EditorTools.BuildTools.BuildWindows -quit
tools/qingxi-waterworks-b/unity/Builds/Win64/QingxiWaterworks.exe -fixture all
```

- 第一次開專案前，先執行選單 **Waterworks › Sync Kit**（上面的 Build 也會自動做）。它會把 `art/exports/qingxi-waterworks-b` 的 FBX、貼圖和 model_info 複製到 `Assets/Resources/Kit/`。這個資料夾不進版控，exports 才是唯一來源。
- 在編輯器裡測：選單 **Waterworks › Make Scene**，打開 `Assets/Scenes/Waterworks.unity`，按 Play。
- `-fixture` 可以是 `all`、`two`（漏看育幼足跡）、`one`（只看到破槽）或 `none`。遊戲裡也能點右側卡片換線索。
- `-demo <資料夾>`：自動玩一輪，內容包含錯接、修正、開關閘、三個方案、完成兩次、撤回／重做、重試。過程會存截圖，以及 `receipts.json`、`marks.json`、`axes.txt`，跑完自動關閉。
- 測試：`Unity -batchmode -projectPath tools/qingxi-waterworks-b/unity -runTests -testPlatform EditMode -testResults <xml>`

### 怎麼玩

畫面上會提示每一步，不看這份說明也玩得完。

- **左下規劃板**：
  - 最上面是處理方向（修復舊渠／先清淤／保護育幼區），下一排是閘板、撤回、重做、完成方案、重試，再往下是 7 種槽件。
  - 點格子放下槽件，再點一次旋轉；右鍵或長按拆除。
  - 鍵盤：方向鍵移游標、Enter 放置、R 旋轉、X 拆除、G 轉閘輪、1–7 選槽件、Z 撤回、Y 重做。
- **3D 畫面**：從 B01 水源開始，沿著規則核心算出的連通樹，照接口把真的 FBX 吸附起來。
  - 有水的槽會看到水流和每段的 L/s。
  - 接口開著、舊渠破槽、沙坡滲漏的地方會噴水；沒接上水的段標紅色「未接水」。
  - B05 閘板升降時，裝在東岸的 B06 閘輪跟著轉。
  - 拖曳空白處轉視角，中鍵平移，滾輪或雙指縮放。
- **右側狀態卡**：步驟、觀察線索與未知風險、處理方向、水量、待處理問題（會點名斷掉的接口和修法）、展示材料，以及收據。

### 接口吸附怎麼對到 Unity 座標

FBX 裡有 `SOCKET_<接口名>` 空物件，model_info.json 有同樣的接口位置和法線（Blender 座標）。`Kit.cs` 用 B04 的三個接口，解出 Blender 到 Unity 的軸向對應（找最吻合的帶正負號軸置換），所有接口和閘輪軸都經過這個對應轉換，不用手寫座標換算。殘差寫在 demo 輸出的 `axes.txt`。

## 三個可以完成的方案

| 方向 | outcomeId | 到村田 | 育幼區 |
|---|---|---|---|
| 修復舊渠（直通村田） | `channel_restored_direct` | 68.6 L/s（86%） | 受驚擾 |
| 保護育幼區（繞西側沙坡） | `nursery_protected_detour` | 55.5 L/s（69%） | 安全 |
| 先清淤（三通分一支回溪道） | `silt_cleared_temporary_diversion` | 29.1 L/s（36%），回溪 48 L/s | 輕擾 |

直通方案的數字是用四段磨損直槽算的。如果在 S01 換成閘板，到村田是 70 L/s（87%）。

## 結構

- **`src/waterworks-core.mjs`**：規則本體，是純函式，不用時鐘也不用亂數。
- **`src/site.mjs`**：場地格子和槽件目錄。
- **`src/fixtures.mjs`**：本機 observationIds，用來代替 A 的匯出。
- **`src/tables.mjs`**：給客戶端用的完整表格匯出。
- **`src/cli.mjs`**：Blender 呼叫規則用的橋（stdin 收 JSON，stdout 回 JSON）。
- **`tests/*.test.mjs`**：規則、錯接訊息、完成兩次不重複扣料、重試換請求編號、CLI 橋，以及 golden 檔是否最新。
- **`tests/scenarios.json` → `tests/golden.json`**：7 個情境的每一步結果，由 `make-golden.mjs` 產生，Unity 測試逐步比對。
- **`unity/`**：
  - `Assets/Waterworks/Runtime/Rules.cs`：C# 版規則。
  - `Site.cs`：讀 `Resources/waterworks-site.json`，也就是 JS 匯出的表格。
  - `Kit.cs`：接口與軸向。
  - `WaterworksGame.cs`：畫面、輸入和動畫。
  - `Tests/EditMode/GoldenTests.cs`：和 golden 檔逐步比對的測試。
- **`blender/play.py`、`blender/encode_frames.py`**：Blender 預覽場景，以及把截圖轉成 mp4 的工具。
- **`CONTRACT.md`**：伺服器串接提案，包含 Idempotency-Key 和收據格式。現有 API 和帳本都沒有改。

```
node --test tools/qingxi-waterworks-b/tests/*.test.mjs
node tools/qingxi-waterworks-b/tests/make-golden.mjs     # 改了規則或場地之後重新產生
```

## 限制（未驗證的事情）

- Unity 測試是獨立專案，沒有接進 `apps/game` 主場景，也沒有用 URP。只在 Windows 播放器和 EditMode 測試驗證過。
- 手機、觸控實機和多人連線都沒有驗證。觸控長按拆除和雙指縮放有寫，但只在桌面用滑鼠模擬過。
- 材料是展示用的，不會接到正式背包。「完成」只在本機產生收據，不會送到伺服器。
- 村田背景是場景裡用方塊搭的簡單田塊。`art/exports/irrigation-v2/*.glb` 在這份工作副本裡只是 Git LFS 指標檔，沒有載入。
