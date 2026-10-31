# 工作包重排｜跟著新手十日的進度，工作量減半（A、B、C）

> 2026-10-31，Claude Code（核心組）依 z1nnz 指示：「從今天開始工作量先減半」「做符合我們進度的內容」。
> 這份**取代** 10/31 三份工作包的「要交的東西」和 11/01 兩份工作包。舊的格位、尺寸、交件規則照舊。
> 美術標準和 AI 提示詞照 [美術風格指南](../art-style-guide-v1.md)。下面每件的提示詞已經填好，整段貼上，後面接風格指南 5.2 固定風格段，負面欄貼 5.3。

## 0. 我們做到哪裡

遊戲照 [新手十日](../../story/outline-v1.md) 一天一天做：

| 天 | 內容 | 狀態 |
|---|---|---|
| 1 | 官道茶亭喝茶、拿梅苗、分到空屋、種梅、睡覺 | **流程已做好**，茶亭、茶爐還是預留框 |
| 2 | 院子種第一塊田；練功場找沈岳；村口夜裡多一盞燈 | **下一步**，田、燈、柴門缺模型 |
| 3 | 上游看溪為什麼停 | 已有（上游河段、水工） |

所以這一輪只做第 1、2 天馬上要用的東西。11/01 的上游擺設（倒木、石牆、小廟、枯井…）**延後**，等第 3 天以後再排。

## A｜鄭翔元 John（約 14 小時）：第 2 天的院子

格位、尺寸照 [10/31 A 包](../2026-10-31/01-A-territory-backyard.md) 第二部分。

| 編號 | 東西 | 第幾天用 |
|---|---|---|
| TY01 | 領地靈田（乾土／濕土兩種狀態，積水先不做） | 第 2 天種田 |
| TY02 | 青靈草 4 個生長階段 | 第 2 天種下、第 4 天收成 |
| TY04 | 院角舊石燈（守燈，5 段亮度） | 第 1 天就在院子裡 |
| TY07 | **只做柴門**（開／關），圍籬模組延後 | 第 1 天進出領地 |

不做（延後）：#45 收尾、TY03 淨水蓮、TY05–06 練功地與器材、TY08 晾藥架、TY09 雜物、TY10 小徑、11/01 自然套件。

提示詞：
```
TY01  Three-view orthographic turnaround sheet of a small hand-tended spirit herb field bed, about 2.6 m wide, 3.4 m long and 0.5 m tall, made of dark tilled soil framed by a low earth ridge with fitted stones and four short wooden stakes at the corners, a small water inlet notch on one side, showing footprints, a dropped hand trowel, moss on the stones, used in the backyard of a newcomer's house in a mountain valley. Layout: front view, side view and back view side by side in one image, all at the same scale and aligned on the same ground line, orthographic (no perspective), centred, full object visible with margin around it, plain light warm-grey background, even soft studio lighting so shapes and materials read clearly, no cast shadows on the background, one object only.

TY02  Growth stage sheet of a magical spirit herb (qing-ling grass) in four stages side by side: tiny sprout, young plant, full plant, mature plant whose leaf tips glow faintly cyan, each about 0.2 / 0.35 / 0.5 / 0.6 m tall, slender serrated leaves in fresh jade green, soil at the base, plain light warm-grey background, orthographic side views at the same scale on one ground line, even soft lighting.

TY04  Three-view orthographic turnaround sheet of an old stone garden lantern in a yard corner, about 0.9 m wide and 2.0 m tall, made of blue-grey stone with moss, a light chamber with paper windows, a tiny crescent-moon mark carved low on the base, showing worn edges and lichen, used in the corner of a newcomer's backyard; shown once unlit. Layout: front view, side view and back view side by side in one image, all at the same scale and aligned on the same ground line, orthographic (no perspective), centred, full object visible with margin around it, plain light warm-grey background, even soft studio lighting so shapes and materials read clearly, no cast shadows on the background, one object only.

TY07  Three-view orthographic turnaround sheet of a rustic wicker and bamboo garden gate between two weathered wooden posts, about 3.0 m wide and 2.4 m tall, made of split bamboo, old wood and hemp rope with a few stones stacked at the post feet, showing one gate leaf slightly sagging and a newer rope tie, used as the gate of a newcomer's yard in a mountain hollow; shown closed. Layout: front view, side view and back view side by side in one image, all at the same scale and aligned on the same ground line, orthographic (no perspective), centred, full object visible with margin around it, plain light warm-grey background, even soft studio lighting so shapes and materials read clearly, no cast shadows on the background, one object only.
```

## B｜蘇奕安 Josh（約 14 小時）：第 1 天的茶亭、第 2 天的村口燈

| 編號 | 東西 | 格位（世界座標 m） | 尺寸上限 | 第幾天用 |
|---|---|---|---|---|
| RK03 | 官道邊的茶亭 | `A2_TeaPavilion` (−18, −108.5)，yaw 90 | 6 × 5 × 4.5 | 第 1 天：茶亭老人請喝茶 |
| RK04 | 茶亭旁的小茶攤 | `A2_TeaStall` (−12.5, −110)，yaw 90 | 3 × 2 × 2.6 | 第 1 天 |
| TI09 | 茶爐 | 屋內 `TI_TeaStove` | 0.7 × 0.7 × 0.9 | 第 1 天學泡茶後放在家裡 |
| G01 | 村口石燈（一款，左右各擺一座） | `Gate_Lantern_L` (−3.6, −27)、`_R` (3.6, −27) | 0.6 × 0.6 × 2.2 | 第 2 天：村口夜裡多一盞燈（亮／不亮兩種狀態，燈室是獨立發光材質） |

茶亭要走得進去，簷下有一張茶桌和兩張長凳，玩家可以坐在桌邊。不做（延後）：#52 收尾、10/31 屋內（TI01–TI08）、11/01 人造邊界套件。

提示詞：
```
RK03  Architectural concept of a small open roadside tea pavilion on a country road outside a valley village, run by a kind old tea master who welcomes every newcomer, footprint about 6 m wide and 5 m deep, ridge 4.5 m high, timber post-and-beam frame with gently upturned eave corners, blue-grey clay tile roof with moss on the ridge, open on three sides with a low wooden railing, worn stone plinth with two steps, details: a square wooden tea table with two benches under the eaves, a small charcoal tea stove and a clay kettle, paper lanterns, a bamboo blind rolled up, a wooden signboard without text, weathering: sun-faded timber, a repaired roof corner with newer tiles. Layout: one three-quarter view from slightly above at eye height of a person, plus front, side and back orthographic views on the same sheet at the same scale, plain light warm-grey background, even soft lighting, building only (no landscape around it except a small ground patch).

RK04  Three-view orthographic turnaround sheet of a small wooden tea stall beside a tea pavilion, about 3 m wide, 2 m deep and 2.6 m tall, made of old timber with a cloth awning, shelves of clay teapots, cups and jars of tea leaves, a bamboo basket of dried tea, a copper kettle, showing worn edges and a patched awning, used on a country road outside a valley village. Layout: front view, side view and back view side by side in one image, all at the same scale and aligned on the same ground line, orthographic (no perspective), centred, full object visible with margin around it, plain light warm-grey background, even soft studio lighting so shapes and materials read clearly, no cast shadows on the background, one object only.

TI09  Three-view orthographic turnaround sheet of a small clay charcoal tea stove for a home, about 0.6 m wide and 0.85 m tall with its kettle, made of reddish-brown fired clay with a round firebox opening, a black iron kettle on top, a bamboo fan leaning against it, showing soot around the opening and a small chip on the rim, used in the main room of a newcomer's house. Layout: front view, side view and back view side by side in one image, all at the same scale and aligned on the same ground line, orthographic (no perspective), centred, full object visible with margin around it, plain light warm-grey background, even soft studio lighting so shapes and materials read clearly, no cast shadows on the background, one object only.

G01   Three-view orthographic turnaround sheet of a tall stone lantern standing at a village gate, about 0.6 m wide and 2.2 m tall, made of weathered warm-grey granite with a square light chamber and paper windows, a small roof cap, moss on the base, showing soot inside the chamber and worn carved edges, used in pairs at the gate of a valley village; shown unlit. Layout: front view, side view and back view side by side in one image, all at the same scale and aligned on the same ground line, orthographic (no perspective), centred, full object visible with margin around it, plain light warm-grey background, even soft studio lighting so shapes and materials read clearly, no cast shadows on the background, one object only.
```

## C｜Eli-0731（約 14 小時）：沿新手前三天路線的見聞

照 [10/31 C 包](../2026-10-31/03-C-qingxi-sightings.md) 第二部分，12 則減為 **6 則**：只做玩家第 1–3 天會走到的地方（A2 官道、A1 村內、D3 上游）。不做（延後）：#47 收尾、其餘 6 則。

## 共同（不變）

- 每件三級 LOD、`model_info.json`；要擋人的附 `_Collision`。
- 審圖：四視圖加 1.75 m 人形尺，和既有作品並排比較。
- 提示詞和生成的三視圖存在 `art/references/<件名>/prompt.txt`。
- 三份互不依賴，有問題直接問核心組。一次交齊，不分批。
