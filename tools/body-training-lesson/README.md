# 沈岳的第一堂練體課

依工作包 `docs/execution/2026-11-01/03-half-load-revision.md` 的 A 包（在分支 `feature/qingxi-creek-chapter`）。沿用自己的練功試招，做成一堂有老師帶的課，接在練功場的身法木樁上。

## 一堂課

| 段 | 要做的 | 過關 | 沒過 |
|---|---|---|---|
| 站樁 | 按住提氣、放開沉氣，讓氣息條停在中間區域 | 累積 15 秒 | 超出邊界，秒數從頭算 |
| 格擋 | 沈岳出 5 拳，拳到才按 | 擋下至少 3 拳 | 馬上重來這一段 |
| 閃避 | 沈岳掃腿 3 次，往左或往右閃 | 閃過至少 2 次 | 馬上重來這一段 |

- 每段開始前有 3 秒示範。三段都過得到「練體入門」。
- 沒過不扣東西，已經過的段不用重來；每次重來的節奏會換，不是背答案。
- 亂按沒用：
  - 格擋：沒有拳時按會僵住，再按僵得更久，所以連按永遠擋不到。
  - 閃避：太早閃會踉蹌 1.6 秒。
- 站樁用固定步長計算，手機 30 fps 和電腦 144 fps 的結果一樣。

## 操作

| 動作 | 鍵盤滑鼠 | 觸控 |
|---|---|---|
| 開始 | 走到身法木樁旁按 F | 互動鍵 |
| 站樁提氣 | 按住空白鍵、滑鼠左鍵或「提氣」鈕 | 按住「提氣」 |
| 格擋 | 空白鍵、F 或「格擋」鈕 | 「格擋」 |
| 閃避 | A／D、←／→ 或左右鈕 | 「左閃」「右閃」 |
| 再來一次 | F、Enter 或按鈕 | 按鈕 |
| 離開 | Esc | 「收功離開」 |

## 檔案

| 檔案 | 用途 |
|---|---|
| `packages/content/body-training-lesson-1.json` | 規則資料與介面文字（每行不超過 16 字） |
| `tools/body-training-lesson/lesson.mjs` | 規則程式（純邏輯，不碰畫面和網路） |
| `tools/body-training-lesson/lesson.test.mjs` | 單元測試 |
| `tools/body-training-lesson/parity.mjs` | 把資料複製給 Unity，並錄下跑法給 C# 對照 |
| `apps/game/Assets/YunJing/Runtime/QingxiBodyLessonRules.cs` | 規則的 C# 版 |
| `apps/game/Assets/YunJing/Runtime/QingxiBodyLesson.cs` | 課程元件：畫面、輸入、沈岳格位框 |
| `apps/game/Assets/YunJing/Runtime/QingxiTrainingPractice.cs` | 改了這一個既有檔案，是我自己的練功元件：木樁上還沒過課時，F 開始課程 |
| `apps/game/Assets/YunJing/Editor/QingxiBodyLessonSmoke.cs` | 在 Unity 裡重播 `parity.mjs` 的跑法，結果要和 JS 一致 |
| `apps/game/Assets/YunJing/Resources/QingxiBodyLesson/` | 規則資料的複本，測試會檢查和 `packages/content` 相同 |

```powershell
node --test tools/body-training-lesson/lesson.test.mjs   # 規則測試
node tools/body-training-lesson/parity.mjs               # 改了 JSON 或規則後重跑
```

## 給核心組接的地方

- **過關通知**：`QingxiBodyLesson.Passed` 事件，參數是課程 id。這裡沒有呼叫伺服器，也不發任何東西。
- **目前的過關紀錄**只存在本機 `PlayerPrefs`，過了之後木樁變回一般的武技格擋。正式要不要開課、第幾天開，由伺服器決定。
- **沈岳**：`BodyLesson_Teacher_Slot` 是 0.6 × 0.6 × 1.75 m 的格位框，放在木樁右側 1.2 m；模型和對白換上後可以拿掉。
- **示範**：現在只有一行字，加上木樁的手臂示範一次（站樁是氣息條自己動）。真正的示範動作要等沈岳的模型。

## 驗證

- 規則測試 19／19。
- Unity 6000.0.82f1：編譯通過；`QingxiBodyLessonSmoke` 重播 4 種跑法，C# 和 JS 結果一致。
- 新手村 Windows 版實際跑完一次：`passed=True attempts=1-2-1`，沒有錯誤。

**錄影**：`video/lesson_desktop_scripted.mp4`，約 60 秒。

- 這是**腳本自動操作**（`--lesson-auto --lesson-fail-first`），走的是和按鈕相同的輸入路徑；不是人玩的。
- 重錄方式：

  ```powershell
  YunJingNoviceVillage.exe -screen-fullscreen 0 -screen-width 1280 -screen-height 720 --drill-lesson --lesson-auto --lesson-fail-first --lesson-capture
  ```

## 還沒做到

- **人實際玩過的錄影**（電腦與手機）：要人來玩。手機版也還沒有在真機上跑過。
- **手感**：要人玩過才能判斷。下面是看錄影想到的，還沒有驗證：
  - 站樁 15 秒只有一條氣息條可看，可能偏悶。
  - 格擋的預告只有木樁手臂和按鈕上的光圈，手機上視線可能顧不到兩邊。
  - 閃避沒有角色動作，只有鏡頭往旁邊滑一下。
  - 滑鼠左鍵按住提氣時，如果按在其他按鈕上不算。
