# 工作包重排｜跟著新手十日的進度（A、B 做玩法，C 做模型）

> 2026-10-31，Claude Code（核心組）依 z1nnz 指示：「從今天開始工作量先減半」「做符合我們進度的內容」「C 也可以交給他像 A、B 一樣的工作，反而可以交給 A、B 更多玩法上的開發」「A、B 的工作量再加一點點」。
> 這份**取代** 10/31 三份工作包的「要交的東西」和 11/01 兩份工作包。交件規則（資料夾、PR 範本、不改別人的東西）照舊。
> 美術標準和 AI 提示詞照 [美術風格指南](../art-style-guide-v1.md)。

## 0. 我們做到哪裡

遊戲照 [新手十日](../../story/outline-v1.md) 一天一天做：

| 天 | 內容 | 狀態 |
|---|---|---|
| 1 | 官道茶亭喝茶、拿梅苗、分到空屋、種梅、睡覺 | 流程已做好；**茶亭、茶爐還是預留框，也還沒有泡茶玩法** |
| 2 | 院子種第一塊田；練功場找沈岳學練體；村口夜裡多一盞燈 | **下一步**；種田已接伺服器，**練體課、村口燈還沒有** |
| 3 | 上游看溪為什麼停 | 已有 |

這一輪：A、B 各做一個第 1、2 天要用的玩法，C 做第 1、2 天缺的模型。11/01 的上游擺設、10/31 的院子和屋內件**延後**。

## A｜鄭翔元 John（約 17 小時）：第 2 天・沈岳的第一堂練體課

你做過練功場和格擋、閃避的試招（`QingxiTrainingPractice`），這次把它做成一堂有老師帶的課。

**玩家會經歷什麼**：第 2 天到練功場，沈岳話不多，示範一次，叫你照做。三個段落：
1. **站樁**：撐住 15 秒，畫面上的氣息條穩在中間區域（左右搖桿或方向鍵微調），太偏就重來。
2. **格擋**：沈岳出 5 拳，看準時機按格擋，至少擋下 3 拳。
3. **閃避**：沈岳掃腿 3 次，往側邊閃，至少閃過 2 次。

三段都過，沈岳說一句短話（核心組寫），玩家得到「練體」入門。沒過可以馬上再來，不扣東西、不罰時間。

**要交的**：
- 規則資料 `packages/content/body-training-lesson-1.json`：三段的時間、次數、判定窗口、過關條件（核心組會接到伺服器）。
- 規則程式（純邏輯、不碰畫面）＋單元測試：輸入玩家按鍵的時間序列，輸出每段是否通過。手機觸控和鍵盤都要能玩。
- Unity 端的課程元件，照你原本 `QingxiTrainingPractice` 的寫法，接到練功場的木樁；沈岳先用格位框代替（NPC 由核心組做）。
- 一段手機和電腦上實際玩過的錄影或截圖，寫出你測到的手感問題。

不做：沈岳的模型和對白（核心組）、伺服器端（核心組照你的規則資料接）。

## B｜蘇奕安 Josh（約 17 小時）：第 1 天・在家泡茶

你做過煉丹的玩法（火候、投料、成丹判定），泡茶用同一套思路，但要輕鬆、短。

**玩家會經歷什麼**：茶亭老人教過以後，回家在茶爐泡茶：
1. **煮水**：火候三段（小／中／大），水溫上升，看壺口的蒸汽判斷。
2. **投茶**：選一種茶葉（先做兩種：青溪野茶、梅花茶），控制分量。
3. **出湯**：在對的時機倒出。太早淡、太晚苦。

結果分「淡、好、苦」三種，泡得好的茶喝了以後，躺床療傷時恢復變快一點（數值由核心組定，你先寫成參數）。泡茶永遠不失敗到浪費東西，最差也能喝。

**要交的**：
- 規則資料 `packages/content/tea-brewing-v1.json`：火候對水溫的曲線、兩種茶的最佳水溫和出湯時間、三種結果的判定。
- 規則程式（純邏輯）＋單元測試。
- Unity 端的泡茶面板，照你原本煉丹面板的寫法，接到屋內的茶爐格位 `TI_TeaStove`；手機觸控和鍵盤都要能操作。
- 實際玩過的錄影或截圖，寫出手感問題。

不做：茶爐模型（C 做）、茶亭老人教泡茶的劇情（核心組）、伺服器端（核心組照你的規則資料接）。

## C｜Eli-0731（約 14 小時）：第 1、2 天缺的模型

| 編號 | 東西 | 格位（世界座標 m） | 尺寸上限 | 第幾天用 |
|---|---|---|---|---|
| RK03 | 官道邊的茶亭（走得進去，簷下一張茶桌、兩張長凳） | `A2_TeaPavilion` (−18, −108.5)，yaw 90 | 6 × 5 × 4.5 | 第 1 天 |
| RK04 | 茶亭旁的小茶攤 | `A2_TeaStall` (−12.5, −110)，yaw 90 | 3 × 2 × 2.6 | 第 1 天 |
| TI09 | 家用茶爐（B 的泡茶玩法用） | 屋內 `TI_TeaStove` | 0.7 × 0.7 × 0.9 | 第 1 天 |
| G01 | 村口石燈（一款，左右各擺一座；亮／不亮兩種狀態，燈室是獨立發光材質） | `Gate_Lantern_L` (−3.6, −27)、`_R` (3.6, −27) | 0.6 × 0.6 × 2.2 | 第 2 天 |

規則：每件先做 AI 三視圖（下面的提示詞整段貼上，後面接風格指南 5.2 固定風格段，負面欄貼 5.3）；三級 LOD、`model_info.json`；要擋人的附 `_Collision`；四視圖加 1.75 m 人形尺；和借住處 `StarterHouse_v004`、你的議水角落並排比較。不做（延後）：#47 收尾、12 則見聞。

```
RK03  Architectural concept of a small open roadside tea pavilion on a country road outside a valley village, run by a kind old tea master who welcomes every newcomer, footprint about 6 m wide and 5 m deep, ridge 4.5 m high, timber post-and-beam frame with gently upturned eave corners, blue-grey clay tile roof with moss on the ridge, open on three sides with a low wooden railing, worn stone plinth with two steps, details: a square wooden tea table with two benches under the eaves, a small charcoal tea stove and a clay kettle, paper lanterns, a bamboo blind rolled up, a wooden signboard without text, weathering: sun-faded timber, a repaired roof corner with newer tiles. Layout: one three-quarter view from slightly above at eye height of a person, plus front, side and back orthographic views on the same sheet at the same scale, plain light warm-grey background, even soft lighting, building only (no landscape around it except a small ground patch).

RK04  Three-view orthographic turnaround sheet of a small wooden tea stall beside a tea pavilion, about 3 m wide, 2 m deep and 2.6 m tall, made of old timber with a cloth awning, shelves of clay teapots, cups and jars of tea leaves, a bamboo basket of dried tea, a copper kettle, showing worn edges and a patched awning, used on a country road outside a valley village. Layout: front view, side view and back view side by side in one image, all at the same scale and aligned on the same ground line, orthographic (no perspective), centred, full object visible with margin around it, plain light warm-grey background, even soft studio lighting so shapes and materials read clearly, no cast shadows on the background, one object only.

TI09  Three-view orthographic turnaround sheet of a small clay charcoal tea stove for a home, about 0.6 m wide and 0.85 m tall with its kettle, made of reddish-brown fired clay with a round firebox opening, a black iron kettle on top, a bamboo fan leaning against it, showing soot around the opening and a small chip on the rim, used in the main room of a newcomer's house. Layout: front view, side view and back view side by side in one image, all at the same scale and aligned on the same ground line, orthographic (no perspective), centred, full object visible with margin around it, plain light warm-grey background, even soft studio lighting so shapes and materials read clearly, no cast shadows on the background, one object only.

G01   Three-view orthographic turnaround sheet of a tall stone lantern standing at a village gate, about 0.6 m wide and 2.2 m tall, made of weathered warm-grey granite with a square light chamber and paper windows, a small roof cap, moss on the base, showing soot inside the chamber and worn carved edges, used in pairs at the gate of a valley village; shown unlit. Layout: front view, side view and back view side by side in one image, all at the same scale and aligned on the same ground line, orthographic (no perspective), centred, full object visible with margin around it, plain light warm-grey background, even soft studio lighting so shapes and materials read clearly, no cast shadows on the background, one object only.
```

## 共同

- 三份互不依賴：A、B 的玩法都先用格位框和假資料跑，不用等 C 的模型；C 的模型不用等玩法。
- 有問題直接問核心組。一次交齊，不分批。
