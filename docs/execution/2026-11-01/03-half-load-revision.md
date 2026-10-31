# 11/01 工作包調整｜工作量減半（A、B）

> 2026-10-31，Claude Code（核心組）依 z1nnz 指示：「從今天開始工作量先減半」。
> 這份取代 [01-A](01-A-world-nature-kit.md)、[02-B](02-B-world-ruins-kit.md) 的第 3 節（要交的東西）和第 7 節（兩批交付），其他規則不變。
> 美術標準和 AI 提示詞照 [美術風格指南](../art-style-guide-v1.md)，下面每件已經把提示詞的【】欄位填好，**直接整段貼上就好，不要改字**。

## 0. 為什麼減半

- 核心組已經做好七種樹（樟、楓、銀杏、柳、梅、松、圓柏）和枯樹，A 包原本的 N01–N03 不用做了。
- 草地和野花也由核心組的地被系統處理，N08 不用做。
- 其餘的件數各砍一半，小場景每人只做一個，先求做好。

## A｜鄭翔元 John（約 14 小時）

| 編號 | 東西 | 數量 | 尺寸 | 說明 |
|---|---|---|---|---|
| N04 | 樹樁 | 1 種（折斷的參差口） | 直徑 0.5–0.8 m | 長苔 |
| N05 | 倒木 | 1 種 | 長 4 m | 半埋、長苔、有蕈；附 `_Collision` |
| N06 | 灌木 | 2 種（圓叢、帶小紅果） | 高 0.6–1.4 m | |
| 小場景 | `D3_FallenShrine` | 1 個 | 1.6 × 1.4 × 1.8 | 倒在路邊的土地公小廟（原 3.2 節） |

不做：N01–N03（核心組已做）、N07 蕨、N08 野花、`D3_HunterCamp`、`A2_RestPavilionRuin`（之後再排）。
交付：一次交齊，不分批。

### A 的提示詞（接風格指南 5.2 固定風格段，負面欄貼 5.3）

N04 樹樁：
```
Three-view orthographic turnaround sheet of an old broken tree stump with a jagged splintered top where the trunk snapped in a storm, about 0.65 m wide and 0.7 m tall, made of weathered grey-brown wood with cracked bark, showing thick green moss on the north side, a few small mushrooms at the base, roots gripping and diving into the soil, used in an upstream valley where the creek has dried. Layout: front view, side view and back view side by side in one image, all at the same scale and aligned on the same ground line, orthographic (no perspective), centred, full object visible with margin around it, plain light warm-grey background, even soft studio lighting so shapes and materials read clearly, no cast shadows on the background, one object only.
```

N05 倒木：
```
Three-view orthographic turnaround sheet of a fallen old tree trunk lying on the ground, half sunk into the soil, about 4 m long and 0.6 m thick, made of weathered grey-brown wood with peeling bark and one broken branch stub, showing moss along the top, shelf mushrooms on one side, small ferns growing beside it, used in an old forest edge. Layout: front view, side view and back view side by side in one image, all at the same scale and aligned on the same ground line, orthographic (no perspective), centred, full object visible with margin around it, plain light warm-grey background, even soft studio lighting so shapes and materials read clearly, no cast shadows on the background, one object only.
```

N06 灌木（兩種各生一張，換【】內文字）：
```
Three-view orthographic turnaround sheet of 【a round dense shrub of small oval leaves / a loose shrub with small red berries among its leaves】, about 1.2 m wide and 1.1 m tall, made of many small leaves in warm sunlit yellow-green on top and cool teal-green underneath on thin woody stems, showing a few dry leaves and a slightly uneven outline, used at the edge of a meadow in a mountain valley. Layout: front view, side view and back view side by side in one image, all at the same scale and aligned on the same ground line, orthographic (no perspective), centred, full object visible with margin around it, plain light warm-grey background, even soft studio lighting so shapes and materials read clearly, no cast shadows on the background, one object only.
```

小場景 `D3_FallenShrine`：
```
Three-view and three-quarter concept of a small fallen roadside shrine to the earth god, about 1.5 m wide, 1.3 m deep and 1.7 m tall, made of weathered warm-grey stone blocks with a tiny tiled roof, with details: the stone niche tilted to one side, a bronze incense burner knocked over beside it, a small bundle of half-burnt incense sticks still inside, moss along the base, a little grass growing from the roof joints. Layout: one three-quarter view, plus front, side and top orthographic views of the structure alone on a plain light warm-grey background, same scale.
```

## B｜蘇奕安 Josh（約 14 小時）

| 編號 | 東西 | 數量 | 尺寸 | 說明 |
|---|---|---|---|---|
| R01 | 乾砌石牆 | 直段 3 m、轉角 | 高 0.9 m | 可以首尾相接（原本的斷段不用） |
| R02 | 竹籬笆 | 直段 2 m | 高 1.1 m | 可以首尾相接 |
| R04 | 石燈籠 | 1 種（缺燈頂的舊燈） | 高 1.5 m | |
| 小場景 | `D3_DryWell` | 1 個 | 1.8 × 1.8 × 2.2 | 枯井（原 3.2 節） |

不做：R03 柴堆、R05 里程石、`D3_AbandonedHut`、`A2_OverturnedCart`（之後再排）。
交付：一次交齊，不分批。

### B 的提示詞（接風格指南 5.2 固定風格段，負面欄貼 5.3）

R01 石牆：
```
Three-view orthographic turnaround sheet of a modular dry-stacked stone field wall, one straight 3 m section and one corner piece, about 0.9 m tall and 0.6 m thick, made of rounded warm-grey fieldstones of different sizes fitted without mortar, flat capstones on top, showing moss and small grass tufts in the joints, a few stones slightly shifted, used along the fields of a mountain valley village. Layout: front view, side view and back view side by side in one image, all at the same scale and aligned on the same ground line, orthographic (no perspective), centred, full object visible with margin around it, plain light warm-grey background, even soft studio lighting so shapes and materials read clearly, no cast shadows on the background.
```

R02 竹籬：
```
Three-view orthographic turnaround sheet of a modular bamboo fence section 2 m long and 1.1 m tall, made of weathered pale yellow-grey bamboo poles tied with brown hemp rope to two horizontal rails, showing a few poles of uneven height, one rope newly retied, moss at the feet of the posts, used around a vegetable garden in a mountain valley village. Layout: front view, side view and back view side by side in one image, all at the same scale and aligned on the same ground line, orthographic (no perspective), centred, full object visible with margin around it, plain light warm-grey background, even soft studio lighting so shapes and materials read clearly, no cast shadows on the background, one object only.
```

R04 石燈籠：
```
Three-view orthographic turnaround sheet of an old roadside stone lantern whose top cap has fallen off and lies at its foot, about 1.5 m tall, made of warm-grey granite with soft worn edges, showing lichen spots, moss on the base, a cracked light chamber with a little soot inside, used beside a country road leading to a valley village. Layout: front view, side view and back view side by side in one image, all at the same scale and aligned on the same ground line, orthographic (no perspective), centred, full object visible with margin around it, plain light warm-grey background, even soft studio lighting so shapes and materials read clearly, no cast shadows on the background, one object only.
```

小場景 `D3_DryWell`：
```
Three-view and three-quarter concept of an old dried-up village well, about 1.7 m wide and 2.1 m tall including its wooden frame, made of a ring of fitted warm-grey stone blocks with one block missing from the rim, an old wooden crossbeam frame with a pulley, with details: the well rope snapped halfway and hanging, a cracked wooden bucket on the ground beside it, dry cracked earth and dead leaves at the bottom of the shaft, moss on the shaded side. Layout: one three-quarter view, plus front, side and top orthographic views of the structure alone on a plain light warm-grey background, same scale.
```

## 共同（不變）

- 每件三級 LOD、`model_info.json`、`_Collision`（要擋人的才附）。
- 審圖：四視圖加 1.75 m 人形尺，和既有作品並排比較。
- 提示詞和生成的三視圖存在 `art/references/<件名>/prompt.txt`。
- 兩份互不依賴，有問題直接問核心組。
