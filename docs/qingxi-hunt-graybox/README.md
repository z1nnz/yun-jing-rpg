# 青溪狩獵區灰盒：協作者 B

對應 [Issue #9](https://github.com/z1nnz/yun-jing-rpg/issues/9)。交付日期：2026-10-25。

**Unity 6000.0.82f1 編譯、灰盒生成、兩次重建與重新載入驗證已通過；NavMesh 未實測。** 本次交付六區配置、座標、獨立 Builder 與靜態幾何檢查。尚未配置可遊玩角色，不能宣稱完整遊玩驗收完成。

## 檔案與範圍

- `apps/game/Assets/YunJing/Editor/QingxiHuntGraybox.json`：唯一座標來源；公尺、Y 向上、+Z 為北。含六區、31 個互動／出生／線索標記、11 個阻擋體及路線。
- 同目錄 `QingxiHuntGrayboxBuilder.cs`：獨立 Editor 產生器，內建 Cube、簡單 BoxCollider 與無碰撞定位片。附兩個資產的 `.meta`。
- `layout.png`：由相同 JSON 繪製的帶比例配置示意，**不是 Unity Scene／遊玩截圖**。
- `validate.py`：不需 Unity 的靜態幾何檢查與選用繪圖工具。

沒有新增自製模型。Issue #9 明確允許 primitive 並豁免此類灰盒的三視圖要求。未匯入或宣稱驗收交接模型；未變更正式 `ProjectBuilder.cs`、Qingxi 場景、戰鬥、API 或其他協作者檔案。

## 配置、入口與路線

總占地 220 × 160 m：X ∈ [-110,110]、Z ∈ [-80,80]；四周厚 2 m 邊界阻擋。所有可行走面 Y=0，主要路線坡度 0°，沒有高於 0.4 m 的可走落差。山兔「草坡」目前為平地代理，坡地與真實地形需 Unity 階段再驗證。

| 區域 | 配置／尺寸 | 入口或用途 |
| --- | --- | --- |
| 聚落出口 | 中心 (-85,-55)，30 × 24 m | 雙人出生 (-85,-55)、(-85,-64)，相距 9 m；商販 (-78,-59) |
| 過渡山道 | (-70,-35) → (-45,-35) → (-45,0)，中心線 60 m、寬 5 m | 村口屏障引導繞到西側，第一線索在 (-70,-35) |
| 採藥林 | 中心 (-20,20)，50 × 40 m | 西側 (-45,20) 進入；6 個採集位置，尚未接收益系統 |
| 山兔草坡 | 中心 (60,35)，80 × 60 m | 西北側 (35,45)；A/B/C 三群各 2 出生、3 逃跑點 |
| 溪流淺灘 | 中心 (65,-35)，40 × 30 m | 從 (65,5) 南下；水色薄片下為連續實心地面；東側深水以阻擋體封閉 |
| 回村捷徑 | (20,-35) → (-20,-55) → (-45,-55)，69.72 m、寬 6 m | 向西經 SafeReturn_01 回村；一開始就可走，不需要獎勵或解鎖邏輯 |

JSON 的山道／捷徑 zone 是配置外框，實際路徑以 `routes` 折線為準。5 m 主路與 6 m 回程保留會車空間，兔群測試迴圈寬 2.5 m；這些尺寸並不等於已完成四人通行實測。

`NavBlocker_*` 物件使用簡化 BoxCollider；其下 `CameraBlocker_*` 為同一阻擋體的搜尋標記，沒有重複 collider。`AreaBoundary_Hunt` 是 Builder 固定產生的 220 × 20 × 160 m 觸發範圍。其餘所有必要標記在 JSON，使用原始命名。小型無碰撞黃色定位片方便在 Scene 視圖定位；它們不是正式腳印、草動、兔子或採集互動。

## 節奏估算與限制

現有 `Cultivator.cs` 水平移速為 4 m/s。採這個速度計算指定探索折線：第一線索 29.79 秒、第一兔出生點 72.37 秒；由該出生點沿溪流與捷徑回出生點 61.18 秒。這是路長除速度的估算，**不是玩家實測，也不保證自由探索時序**。全圖為平地，玩家可能繞過提示路線；先觀察遊玩結果再調整，不以箭頭或倒數強迫走法。

村口與中央屏障提供預期視線遮擋，林中岩塊和兔群迴圈提供辨向參考；未完成可視性與追丟後辨向測試。高牆附近可能擋住 6 m 相機，須實機確認。兔群位置在同一靜態可達區，各組逃跑迴圈未穿過方形障礙；尚無 AI、NavMesh、戰鬥或出售互動。

## 重建與檢查

在儲存庫根目錄執行：

```powershell
python docs/qingxi-hunt-graybox/validate.py
# Optional: Pillow is required only to regenerate the diagram.
python docs/qingxi-hunt-graybox/validate.py --render
# Compile, generate twice and validate the saved scenes using the pinned Unity Editor.
powershell -NoProfile -ExecutionPolicy Bypass -File tools/verify-unity-graybox.ps1
npm ci
npm test
```

指定 Unity：**6000.0.82f1**，2026-10-25 已實際啟動並確認 Unity Personal 授權。

### 編譯阻擋的原因與修正

原先 FishNet `4.7.4` tag（`a3627529c1875ebe6313c2fc9e2326cbd5d76719`）的公開原始碼殘留不完整 Yak 呼叫：`IterateIncoming`、`SendToServer`、`SendToClient`、`OnLocalServerConnectionState`，造成五個 CS1061／CS0103 錯誤。本機快取與官方該 tag 的錯誤檔案逐一比對一致，並非本機快取損壞。

改為固定官方 [4.7.4R 發布 commit](https://github.com/FirstGearGames/FishNet/commit/a2e2c3e12f5f4e18c96e402113e14030ae7849f0)，套件內版本仍為 `4.7.4`，不追蹤浮動 main；同時提交 Unity 產生的 `packages-lock.json` 固定解析結果。此發布清理了不完整的 Pro 程式殘留，未自行補寫或啟用 Yak 功能。專案使用的 Tugboat 原始碼在兩個 commit 間無差異；未宣稱其他 FishNet 功能已有網路實測。

快速重現使用 Unity 的 Roslyn 編譯器與實際 `FishNet.Runtime.rsp`：原始 tag 穩定失敗，替換成官方發布來源後成功。完整 Unity 執行接著發現 Builder 在未命名空場景下不能 additive 建立場景；已改為僅在未修改的未命名場景使用 Single 模式，已保存場景仍採 additive；未保存修改的場景受到保護。

### Unity 實際驗證

以 `-batchmode -nographics -quit -executeMethod YunJing.Editor.QingxiHuntGrayboxBuilder.Verify` 執行，退出碼 **0**。驗證入口只允許 batchmode，會連續兩次生成、保存並重新載入灰盒，檢查 31 個標記位置、11 個 BoxCollider 位置與尺寸，以及沒有 MeshCollider。實際訊息：

```text
GRAYBOX_VERIFY_PASS: two builds and reloads; 31 markers; 11 box blockers. No gameplay or NavMesh validation claimed.
```

已在本機產生 `Assets/YunJing/Generated/QingxiHuntGraybox.unity`。完整日誌：`artifacts/unity-hunt-verify.log`。產物與日誌不提交；首次匯入對其他 ProjectSettings 的自動改動已另存於 artifacts 後回復，不混入本次提交。其他自動產生的資產 meta 保留本機但不加入提交。

有指定版本的環境：

1. 開啟 `apps/game`，完成授權及套件匯入，先解決所有 Editor 編譯錯誤。
2. 執行選單 `Yun Jing > Generate independent Qingxi hunt graybox`；或 batchmode 的 `-executeMethod YunJing.Editor.QingxiHuntGrayboxBuilder.Generate`。
3. 產生 `Assets/YunJing/Generated/QingxiHuntGraybox.unity` 及其專用材質。產生器不修改 Build Settings 或全域 URP 設定；若專案尚未設定渲染管線，需於測試環境另行設定才能評估視覺。
4. 已保存場景旁以 additive 開啟；未修改的未命名初始場景以 Single 取代。重建前需保存或關閉此灰盒的手動修改；其關鍵內容應回寫 JSON／Builder。僅有乾淨的上次灰盒場景會被關閉並重建。
5. 產物、材質及其 meta 不加入本次提交。產生器不配置玩家、網路服務或 NavMesh，因此不能直接按 Play 當作遊戲測試。

## 驗證紀錄及下一次 Unity 驗收

本次修正後執行結果：Unity 編譯與兩次生成／重新載入驗證通過；`npm test` 53/53 通過；`git lfs fsck` 通過；靜態檢查通過（30,750 個可達網格）。另以重疊出生點、堵住主路、移除必要標記三個負向案例確認檢查會拒絕錯誤配置。

靜態驗證：31 個唯一必要標記、六區、所有出生點至少 8 m 間距、主要／回程／兔群迴圈的整個走廊寬度、標記未落在阻擋中、主要坡度限制與路程時間。採 1 m 四鄰接網格，障礙膨脹角色半徑及格子半對角線，驗證所有標記位於同一連通區。此檢查只證明 JSON 的平面方盒幾何，不代表 Unity Collider 或 NavMesh 結果。

後續驗收清單：

- 已完成：Editor 編譯、場景生成兩次、保存後重新載入及標記／阻擋體尺寸一致性。
- 以玩家半徑 0.35 m、山兔預期半徑 0.25 m 烘焙／查詢導航；逐群檢查出生到三個逃跑點以及點間 `PathComplete`。目前專案未加入 AI Navigation 依賴，本次不自行變更套件版本。
- 兩個角色占位物走主路、林區、兔群迴圈、淺灘及回程，記錄碰撞和互相阻擋；這不是即時多人連線驗收。
- 在 16:9／20:9 視窗，以 3.5、4.75、6 m 相機距離逐轉角記錄遮擋，特別檢查村口折返及中央屏障。
- 保存真正的 Scene 鳥瞰，以及聚落出口、山道、採藥林、兔坡、淺灘、捷徑六處遊玩視角截圖，並附操作路線和實測時間。
- 未驗證手機效能、正式收益、即時多人與素材相容性。不得以 API 測試通過代替上述驗收。
