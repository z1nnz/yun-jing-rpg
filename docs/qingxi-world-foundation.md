# 青溪初始世界雛形 v1

這是一個可供決定比例、視線與遊玩路線的**大世界第一塊區域**，不是完整州域或完成美術。以先前選定的 [世界方向圖](../art/references/world-master-v1/yun-jing-starting-world-master.png) 為基準，先讓村落與河對岸有明確的空間關係。

![青溪世界俯視雛形](../art/previews/qingxi-world-v1/qingxi-world-blockout-v1.png)

![村落與跨溪路線](../art/previews/qingxi-world-v1/qingxi-village-crossing-v1.png)

## 這一版的空間

場景基底約 **180 × 140 公尺**，Unity 與 Blender 預覽採相同座標（平面 X／Z 對應 Blender X／Y）：

| 區域 | 大約位置 | 在前十日的用途 |
|---|---|---|
| 村口／起點 | (0, -7) | 出生後自由開始，不強迫順序任務 |
| 村屋與小型服務 | 西側 | 將來放交易、休息、煉氣訣與 NPC |
| 藥田與採集邊地 | 西南 | 種植與資源教學的空間 |
| 古樹與測資廣場 | (-13, 27)／(0, 29) | 世界地標；正式測資揭示仍遵守創角後十個現實日 |
| 青溪木橋 | (25, 5) | 從村落到東側林地的主要跨河動線 |
| 東側林地 | (38–86, -47–45) | 將來放低級獵物、採集與環境探索 |
| 洞口 | (73, 48) | 後續事件入口，目前只是尺度佔位 |
| 北側遠山 | Z 約 65 | 宗門方向的遠景；十日前不要求認識宗門 |

從起點可直接走向村屋、田地、廣場或跨橋至林地。此版不加入在線時長獎勵或強迫每幾分鐘完成的流程。宗門選比仍由服務端創角時間判定，場景外觀不改動規則。

## 已製作的模型

依使用者指定順序，先生成並檢視 [木橋三視圖](../art/references/qingxi-world-v1/timber-bridge-three-view.png) 與 [古樹三視圖](../art/references/qingxi-world-v1/sacred-tree-three-view.png)，才用 Blender 建模。兩件模型均有 `.blend`、`.fbx`、`.glb`；FBX 已複製到 Unity 專案。

| 模型 | 尺度 | Blender 檢查 | FBX 往返 |
|---|---:|---|---|
| 主木橋 | 約 12.22 × 4.25 × 2.90 m，1,608 三角面 | 無錯誤／警告 | 原檔 134 個可替換零件；遊戲 FBX 合併為 3 網格，尺寸吻合 |
| 村中古樹 | 約 11.82 × 12.23 × 13.91 m，648 三角面 | 無錯誤／警告 | 原檔 30 個零件；遊戲 FBX 合併為 5 網格，尺寸吻合 |

原有測資廣場已有自己的三視圖與模型。房舍、一般樹、山石、洞口、道路和水面在本輪均是**灰盒**，供確認方位、比例與可通行性；尚未宣稱完成模型。下一輪若正式製作，仍須各自先生成、檢視並保存三視圖。

## 開啟與重製

- 預覽圖片：`art/previews/qingxi-world-v1/`；可直接打開 PNG。
- 無 Unity 授權時的動線試走：直接以瀏覽器打開 `tools/world-preview/index.html`。WASD／方向鍵移動、E 查看地標；也有觸控方向鍵。這是同座標的**俯視動線稿**，只檢查距離、道路與過橋位置，不是正式遊戲客戶端，也沒有存檔或伺服器資產操作。
- 可編輯的 Blender 世界雛形：`art/source/qingxi-world-blockout-v1.blend`。
- 已存的 AI 三視圖及檢視記錄：`art/references/qingxi-world-v1/`。
- 模型生成：`blender -b --factory-startup -P tools/art/build_qingxi_landmarks.py`。
- Blender 世界預覽：`blender -b --factory-startup -P tools/art/render_qingxi_world_preview.py`。
- Unity 授權就緒後：`./tools/unity.ps1 -Target WorldPreview`，或 Unity 選單 `Yun Jing > Generate Qingxi world preview`；目標場景 `Assets/YunJing/Generated/QingxiWorldPreview.unity`。

Unity 生成器會沿用現有青溪開發場景的網路服務和角色，再擴展到世界雛形；木橋有獨立步行碰撞面與兩側引道，溪流其他位置有暫時性的不可見越界碰撞。此處只驗證基本空間路線；世界互動、山兔 AI、採集與交易尚未接到這些座標。

俯視動線稿已用真實瀏覽器試走：從村口走到木橋，穿過到達河東；在橋外直接往東會被溪流擋住。此測試只證明 HTML 試走稿的路線邏輯，不替代 Unity 場景碰撞測試。

**Unity 本輪仍未驗證。** 2026-10-25 批次啟動 `WorldPreview` 時，Unity `6000.0.82f1` 因沒有有效 Editor 授權，以代碼 198 結束，未進入 C# 編譯或場景生成。Blender 渲染和模型檢查已完成；手機幀率、12 人同場與 Unity 內實際步行均尚未測試。

## 接下來的製作順序

1. Unity 授權就緒後，先生成場景並確認角色可從村口到田地、廣場、橋與洞口；修正模型朝向／碰撞。
2. 針對一棟新手村屋、一種普通樹、一組山石和溪岸模組，分別完成 AI 三視圖後再做正式模型與 LOD。
3. 把山兔、採集點和商販按遊玩路線放進林緣與村內，接服務端距離判定及資產帳本。
4. 有實際手機測試數據後，檢查目前按材質合併的木橋／古樹網格、建立 LOD，調整林地密度與視距。
