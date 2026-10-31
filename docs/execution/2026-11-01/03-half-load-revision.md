# 工作包重排｜跟著新手十日的進度（每人都是模型＋玩法）

> 2026-10-31，Claude Code（核心組）依 z1nnz 指示：「從今天開始工作量先減半」「做符合我們進度的內容」「C 也可以交給他像 A、B 一樣的工作，反而可以交給 A、B 更多玩法上的開發」「A、B 的工作量再加一點點」「做模型也做玩法」。
> 這份**取代** 10/31 三份工作包的「要交的東西」和 11/01 兩份工作包。交件規則（資料夾、PR 範本、不改別人的東西）照舊。
> 美術標準和 AI 提示詞照 [美術風格指南](../art-style-guide-v1.md)。

## 0. 我們做到哪裡

遊戲照 [新手十日](../../story/outline-v1.md) 一天一天做：

| 天 | 內容 | 狀態 |
|---|---|---|
| 1 | 官道茶亭喝茶、拿梅苗、分到空屋、種梅、睡覺 | 流程已做好；**茶亭、茶攤、茶爐還是預留框，也還沒有泡茶玩法** |
| 2 | 院子種第一塊田；練功場找沈岳學練體；村口夜裡多一盞燈 | **下一步**；種田已接伺服器，**田床、柴門、練體課、村口燈還沒有** |
| 3 | 上游看溪為什麼停 | 已有 |

這一輪每個人都做「一個玩法＋那個玩法要用的模型」，都是第 1、2 天馬上要用的。11/01 的上游擺設、10/31 其他院子和屋內件**延後**。

模型的共同規則：每件先做 AI 三視圖（提示詞整段貼上，後面接風格指南 5.2 固定風格段，負面欄貼 5.3）；三級 LOD、`model_info.json`；要擋人的附 `_Collision`；四視圖加 1.75 m 人形尺，和既有作品並排比較。
玩法的共同規則：規則資料放 `packages/content/`、規則程式是純邏輯並附單元測試、Unity 端照你原本的元件寫法、手機觸控和鍵盤都能玩、交實際玩過的錄影並寫出手感問題。NPC 模型、對白、伺服器端由核心組照你的規則資料接。

## A｜鄭翔元 John（約 17 小時）：第 2 天・院子和沈岳的第一堂練體課

**玩法（約 11 小時）**：沿用你的練功試招（`QingxiTrainingPractice`），做成一堂有老師帶的課。第 2 天到練功場，沈岳示範一次，叫你照做：
1. **站樁**：撐住 15 秒，氣息條穩在中間區域，太偏就重來。
2. **格擋**：沈岳出 5 拳，看準時機格擋，至少擋下 3 拳。
3. **閃避**：沈岳掃腿 3 次，往側邊閃，至少閃過 2 次。

三段都過得到「練體」入門；沒過馬上再來，不扣東西。交：`body-training-lesson-1.json`、規則程式＋測試、接到練功場木樁的課程元件（沈岳先用格位框）、錄影。

**模型（約 6 小時）**：第 2 天院子要用的，格位和尺寸照 [10/31 A 包](../2026-10-31/01-A-territory-backyard.md)。

| 編號 | 東西 |
|---|---|
| TY01 | 領地靈田（乾土／濕土兩種狀態） |
| TY07 | 柴門（開／關），圍籬延後 |

```
TY01  Three-view orthographic turnaround sheet of a small hand-tended spirit herb field bed, about 2.6 m wide, 3.4 m long and 0.5 m tall, made of dark tilled soil framed by a low earth ridge with fitted stones and four short wooden stakes at the corners, a small water inlet notch on one side, showing footprints, a dropped hand trowel, moss on the stones, used in the backyard of a newcomer's house in a mountain valley. Layout: front view, side view and back view side by side in one image, all at the same scale and aligned on the same ground line, orthographic (no perspective), centred, full object visible with margin around it, plain light warm-grey background, even soft studio lighting so shapes and materials read clearly, no cast shadows on the background, one object only.

TY07  Three-view orthographic turnaround sheet of a rustic wicker and bamboo garden gate between two weathered wooden posts, about 3.0 m wide and 2.4 m tall, made of split bamboo, old wood and hemp rope with a few stones stacked at the post feet, showing one gate leaf slightly sagging and a newer rope tie, used as the gate of a newcomer's yard in a mountain hollow; shown closed. Layout: front view, side view and back view side by side in one image, all at the same scale and aligned on the same ground line, orthographic (no perspective), centred, full object visible with margin around it, plain light warm-grey background, even soft studio lighting so shapes and materials read clearly, no cast shadows on the background, one object only.
```

## B｜蘇奕安 Josh（約 17 小時）：第 1 天・在家泡茶

**玩法（約 11 小時）**：用你煉丹玩法的思路，但要輕鬆、短。茶亭老人教過以後，回家在茶爐泡茶：
1. **煮水**：火候三段（小／中／大），看壺口的蒸汽判斷水溫。
2. **投茶**：兩種茶葉（青溪野茶、梅花茶），控制分量。
3. **出湯**：太早淡、太晚苦。

結果分「淡、好、苦」，泡得好的茶讓躺床療傷時恢復快一點（先寫成參數）；永遠不會浪費東西。交：`tea-brewing-v1.json`、規則程式＋測試、接到屋內茶爐格位 `TI_TeaStove` 的泡茶面板、錄影。

**模型（約 6 小時）**：

| 編號 | 東西 | 格位 | 尺寸上限 |
|---|---|---|---|
| TI09 | 家用茶爐（你的泡茶玩法用） | 屋內 `TI_TeaStove` | 0.7 × 0.7 × 0.9 |
| RK04 | 茶亭旁的小茶攤 | `A2_TeaStall` (−12.5, −110)，yaw 90 | 3 × 2 × 2.6 |

```
TI09  Three-view orthographic turnaround sheet of a small clay charcoal tea stove for a home, about 0.6 m wide and 0.85 m tall with its kettle, made of reddish-brown fired clay with a round firebox opening, a black iron kettle on top, a bamboo fan leaning against it, showing soot around the opening and a small chip on the rim, used in the main room of a newcomer's house. Layout: front view, side view and back view side by side in one image, all at the same scale and aligned on the same ground line, orthographic (no perspective), centred, full object visible with margin around it, plain light warm-grey background, even soft studio lighting so shapes and materials read clearly, no cast shadows on the background, one object only.

RK04  Three-view orthographic turnaround sheet of a small wooden tea stall beside a tea pavilion, about 3 m wide, 2 m deep and 2.6 m tall, made of old timber with a cloth awning, shelves of clay teapots, cups and jars of tea leaves, a bamboo basket of dried tea, a copper kettle, showing worn edges and a patched awning, used on a country road outside a valley village. Layout: front view, side view and back view side by side in one image, all at the same scale and aligned on the same ground line, orthographic (no perspective), centred, full object visible with margin around it, plain light warm-grey background, even soft studio lighting so shapes and materials read clearly, no cast shadows on the background, one object only.
```

## C｜Eli-0731（約 14 小時）：第 1 天的茶亭、第 2 天的村口燈

**模型（約 9 小時）**：

| 編號 | 東西 | 格位（世界座標 m） | 尺寸上限 |
|---|---|---|---|
| RK03 | 官道邊的茶亭（走得進去，簷下一張茶桌、兩張長凳） | `A2_TeaPavilion` (−18, −108.5)，yaw 90 | 6 × 5 × 4.5 |
| G01 | 村口石燈（一款，左右各一座；亮／不亮兩種狀態，燈室是獨立發光材質） | `Gate_Lantern_L` (−3.6, −27)、`_R` (3.6, −27) | 0.6 × 0.6 × 2.2 |

```
RK03  Architectural concept of a small open roadside tea pavilion on a country road outside a valley village, run by a kind old tea master who welcomes every newcomer, footprint about 6 m wide and 5 m deep, ridge 4.5 m high, timber post-and-beam frame with gently upturned eave corners, blue-grey clay tile roof with moss on the ridge, open on three sides with a low wooden railing, worn stone plinth with two steps, details: a square wooden tea table with two benches under the eaves, a small charcoal tea stove and a clay kettle, paper lanterns, a bamboo blind rolled up, a wooden signboard without text, weathering: sun-faded timber, a repaired roof corner with newer tiles. Layout: one three-quarter view from slightly above at eye height of a person, plus front, side and back orthographic views on the same sheet at the same scale, plain light warm-grey background, even soft lighting, building only (no landscape around it except a small ground patch).

G01   Three-view orthographic turnaround sheet of a tall stone lantern standing at a village gate, about 0.6 m wide and 2.2 m tall, made of weathered warm-grey granite with a square light chamber and paper windows, a small roof cap, moss on the base, showing soot inside the chamber and worn carved edges, used in pairs at the gate of a valley village; shown unlit. Layout: front view, side view and back view side by side in one image, all at the same scale and aligned on the same ground line, orthographic (no perspective), centred, full object visible with margin around it, plain light warm-grey background, even soft studio lighting so shapes and materials read clearly, no cast shadows on the background, one object only.
```

**玩法（約 5 小時）**：沿用你做過的回村手札和村民回應。
1. **村口多的那盞燈**：從第 2 天起，夜裡村口左邊那座石燈會亮（第 1 天夜裡是暗的），依遊戲的晝夜時間。靠近按 F，只顯示一句觀察（例：「燈芯是新換的。」），不解釋是誰點的。
2. **旅途手札的「今天」**：手札裡每一天記一行玩家做過的事（第 1 天：喝了茶、分到屋子、種了梅；第 2 天：種田、練體、看見那盞燈），用 `QingxiNoviceDays` 已經記下的事件。

交：燈和手札的規則資料、程式＋測試、錄影。文字先用上面的例句，正式文字由核心組寫。

## 共同

- 三份互不依賴：玩法先用格位框和假資料跑，不用等別人的模型；模型也不用等玩法。
- 有問題直接問核心組。一次交齊，不分批。
