# 《承天》美術風格指南 v1（含 AI 提示詞）

> 2026-10-30，Claude Code，依 z1nnz 的方向整理。z1nnz：「我們的風格是這樣的，不要抄原神的，但要做到他那樣。」「生成的標準也要照這個來，協作者的也是，所以記得給他們提示詞。」
> 方向圖：`art/references/world-directions-v1/`（A 暖陽河谷、B 雲瀑山門、C 斷脈靈湖、D 古林），以及 z1nnz 2026-10-30 貼的五張方向圖（河谷聚落、雲瀑山門、斷脈靈湖、古樹聚落、大樹廣場）。
> 所有人（核心組、A、B、C、Codex、用 AI 出圖的人）照這份做。AI 三視圖、概念圖、貼圖都用第五節的提示詞骨架。之後每個工作包都附上這份（z1nnz：「之後含在工作包裡給他們就好」）。

## 一、一句話

**手繪質感的東方仙俠 3D：金色晨光、層層白霧、青碧的水、遠山峰林與瀑布，草木細密、生活感濃。** 精細程度要到原神那個等級（滿地的草、花、雲、層次），但長相照我們的方向圖，不抄原神。

## 二、五個要點

| 要點 | 要做到 | 不要 |
|---|---|---|
| **光** | 溫暖偏低的太陽（清晨或傍晚），逆光讓樹冠和屋簷鑲一圈金邊；陰影偏藍紫、柔和 | 正午的平光；死黑的陰影；冷白的光 |
| **霧** | 山腳、水面、遠處一層層白霧，把遠近分開；越遠越淡越藍 | 整片灰濛濛；完全沒有空氣感 |
| **水** | 青碧、透亮，淺處看得到石頭，激流處有白色水花；瀑布多 | 深藍色塑膠感的水；死水 |
| **草木** | 每種樹自己的樹形和葉形；地面鋪滿草、花、蕨、苔石；竹林、柳、蓮、花圃 | 光禿的地面；一種樹種滿全世界；根像腿撐在地上 |
| **人造物** | 木構、青瓦、石階、木棧道、燈籠、水車、晾架，有生活痕跡（磨損、苔、補丁） | 嶄新無痕的方塊建築；現代物件 |

## 三、顏色

| 用途 | 色票 | 說明 |
|---|---|---|
| 草地 | `#3e6a2a` → `#6fa443` → `#b8d468` | 根部深，葉尖亮，帶暖黃 |
| 樹冠 | `#1d4a46`（陰面，偏青）→ `#4a8650` → `#b6d07c`（受光面，偏黃） | 同一棵樹裡就要有冷暖 |
| 泥土小路 | `#8a6a44` → `#b8955e` | 暖褐，邊緣被草吃進去 |
| 岩石 | `#8a8478` → `#b8b0a0` | 暖灰，帶地衣綠點 |
| 水 | `#2e8a8a`（深）→ `#7cd0c4`（淺）→ 白色水花 | 青碧，不是深藍 |
| 天空 | `#4a86c8`（天頂）→ `#c8dcea`（地平線）+ 白雲 | 地平線偏暖白的霧 |
| 霧 | `#e8e4d8` | 暖白 |
| 木構 | `#6a4630` → `#a87a50` | 舊木頭，帶灰 |
| 屋瓦 | `#3e4e58`（青瓦）、`#2c3640` | 青灰，不是純黑 |

不用純黑 `#000`、純白 `#fff`；飽和度高但不刺眼。

## 四、模型與貼圖的標準

- **形**：輪廓先好看。屋簷要翹，樹要有姿態（傾、扭、分叉），石頭要圓潤帶稜，不要方塊。
- **細節**：品質優先，不為了面數犧牲造型。一定要做三層細節（LOD0 近、LOD1 中、LOD2 遠）。
- **貼圖**：手繪質感：大塊柔和的漸層加少量筆觸，不要照片貼圖，也不要整片細碎雜訊。暗部偏冷、亮部偏暖。
- **磨損**：邊角磨亮、縫裡有苔和土、木頭有裂紋。
- **尺寸**：照真實尺寸（門 2.2 m、欄杆 1 m、一般樹 8～16 m）。
- **根和地面**：樹幹接地只微微變寬，根露出一點就鑽進土裡；石頭要半埋。
- **交件前**：在遊戲裡（不是只在 Blender）截圖，跟方向圖放在一起比。

## 五、AI 提示詞

先做 AI 三視圖再建模。**提示詞不要自己從頭寫**：照下面的骨架，只改【】裡的欄位，其他字一個都不要動。這樣不管誰來生成，光線、鏡頭、畫風、細節程度都一樣。生成的圖和最後用的那一段提示詞，一起存進 `art/references/<件名>/prompt.txt`。

### 5.1 用法

1. 選類別（5.4～5.12），複製整段英文提示詞（英文效果最穩定；中文版本給不熟英文的人對照）。
2. 只填【】欄位，每一欄都要填，不要留空；不知道填什麼，就照該類的範例改。
3. 後面一定接 **5.2 固定風格段**；負面提示欄一定貼 **5.3 固定負面提示**。
4. 照 **5.13 生成設定**，同一件至少出 4 張，挑最好的；挑不出來就改【】欄位重出，不要改固定段。
5. 交件時附上：提示詞、選中的圖、沒選的圖（看得出取捨）。

### 5.2 固定風格段（每一個提示詞最後都接這一整段，一字不改）

```
Art direction: stylized hand-painted 3D game art for an Eastern xianxia fantasy world (Chinese immortal-cultivation setting), warm golden morning light from a low sun, soft warm rim light on edges and silhouettes, gentle blue-violet shadows (never pure black), layered soft white mist in the distance, painterly textures made of large soft colour gradients with a few visible brush strokes, rich but natural colour palette (sunlit warm yellow-greens, cool teal shade greens, warm grey stone, aged brown timber, blue-grey roof tiles, turquoise water), lived-in details: wear on edges, moss and soil in the joints, patched and repaired parts, small cracks, weathered wood grain, high level of detail with clear readable shapes and a strong silhouette, real-world scale and proportions, cohesive with a hand-painted xianxia valley village, game-ready asset look, high quality, masterpiece.
```

中文對照（給看不懂英文的人確認意思，生成時用英文）：
```
美術方向：東方仙俠（修仙世界）的手繪質感 3D 遊戲美術；偏低的太陽打出溫暖的金色晨光；邊緣和輪廓有柔和的暖色逆光金邊；陰影是柔和的藍紫色（絕不死黑）；遠處有層層柔和白霧；貼圖是大塊柔和漸層加少量可見筆觸；顏色飽滿但自然（受光的暖黃綠、陰影的青綠、暖灰石頭、陳舊的褐色木頭、青灰屋瓦、青碧的水）；有生活痕跡：邊角磨損、縫裡的苔和土、修補過的地方、小裂紋、風化木紋；細節豐富但形體清楚、剪影強；真實尺寸和比例；跟手繪仙俠河谷村落是同一個世界；遊戲美術資產的完成度；高品質。
```

### 5.3 固定負面提示（貼在 negative prompt 欄；沒有這一欄的工具，接在提示詞最後，前面加 "Avoid:"）

```
photorealistic, photograph, photo texture, scanned texture, realistic PBR, plastic, glossy, shiny, chrome, pure black shadows, harsh contrast, neon colours, oversaturated, flat lighting, noon lighting, modern objects, cars, wires, concrete, glass windows, text, letters, Chinese characters, signature, logo, UI, watermark, frame, border, anime screenshot, cel-shaded flat colour, Genshin Impact, Mihoyo, copy of an existing game asset, blocky low-poly, voxel, cartoon chibi, noisy texture, blurry, low resolution, cropped, cut off, duplicate objects, extra limbs, floating parts, distorted perspective, fisheye
```

### 5.4 單件道具：三視圖（例：晾藥架、木桶、燈籠、木樁）

```
Three-view orthographic turnaround sheet of 【物件，英文，一句話描述，例：a weathered wooden herb drying rack with three bamboo rails and bundles of drying herbs hanging from them】, 【尺寸，例：about 2.0 m wide, 0.8 m deep, 1.8 m tall】, made of 【材質，例：old grey-brown cedar wood, split bamboo, linen and hemp rope ties】, showing 【磨損與生活痕跡，例：rope-worn notches, a repaired leg tied with fresh rope, moss at the feet, dried leaves fallen on the base】, used in 【所在地，例：the backyard of a newcomer's house in a mountain valley village】.
Layout: front view, side view and back view side by side in one image, all at the same scale and aligned on the same ground line, orthographic (no perspective), centred, full object visible with margin around it, plain light warm-grey background, even soft studio lighting so shapes and materials read clearly, no cast shadows on the background, one object only.
【接 5.2 固定風格段】
```

範例（已填好，可以直接照抄改字）：
```
Three-view orthographic turnaround sheet of a weathered wooden water bucket with two iron hoops and a rope handle, about 0.45 m wide and 0.5 m tall, made of old cedar staves, darkened iron hoops, hemp rope, showing water stains on the lower staves, a dent in one hoop, moss at the base, used in a creek-side courtyard of a mountain valley village. Layout: front view, side view and back view side by side ... 【5.2】
```

### 5.5 建築：三視圖加一張四分之三視角

```
Architectural concept of 【建築，例：a small two-room riverside teahouse with an open front veranda】 for 【用途與主人，例：an old tea master who welcomes every newcomer】, footprint 【尺寸，例：about 9 m wide and 7 m deep, single storey, ridge 5.5 m high】, timber post-and-beam frame with gently upturned eave corners, 【屋頂，例：blue-grey clay tile roof with a moss-covered ridge】, 【牆與窗，例：plastered lower walls, paper lattice windows, sliding wooden doors】, 【基座，例：worn stone plinth with three steps】, details: 【細節，例：hanging paper lanterns, a tea stove under the eaves, bamboo blinds, potted herbs, a hand-carved wooden sign without text】, weathering: 【磨損，例：sun-faded timber, a repaired roof corner with newer tiles, moss on the north side】.
Layout: one three-quarter view from slightly above at eye height of a person, plus front, side and back orthographic views on the same sheet at the same scale, plain light warm-grey background, even soft lighting, building only (no landscape around it except a small ground patch).
【接 5.2 固定風格段】
```

### 5.6 樹：三視圖

```
Three-view turnaround of a single 【樹種與年紀，例：centuries-old camphor tree】, about 【高度，例：12 m tall with a crown 10 m wide】, silhouette: 【姿態，例：a short massive trunk splitting into five great limbs that spread into a wide round crown】, bark: 【樹皮，例：deeply furrowed warm brown bark with grey lichen patches】, foliage: 【葉，例：dense crown of many small glossy oval leaves, warm sunlit yellow-green on top and cool teal-green underneath】, base: the trunk only slightly widens where it meets the ground and a few roots show briefly before diving into the soil (no swollen base, no roots lying on the ground, no exposed root legs), 【特色，例：a few broken twigs and a bird's nest in a fork】.
Layout: front, side and top-down views side by side, same scale, aligned on one ground line, plain light warm-grey background, even soft lighting, one tree only.
【接 5.2 固定風格段】
```

各樹種的【姿態】【葉】參考（照抄）：
- 樟：short massive trunk splitting into five great limbs, wide round crown / dense small glossy oval leaves
- 楓：stout leaning trunk, limbs spreading wide and flat like an umbrella / five-lobed palmate leaves in deep red to orange-gold
- 銀杏：one straight leader to the top with short level branches, narrow upright crown / fan-shaped leaves, golden yellow
- 柳：thick short trunk, limbs arching up then long curtains of hanging thin branches / narrow lance leaves, fresh yellow-green
- 梅：zigzag gnarled dark trunk, angular horizontal limbs, straight thin shoots / five-petal pale pink and white blossoms, no leaves
- 柏：straight tall trunk, dense rising branches forming a narrow pointed cone / flat sprays of tiny scale leaves, dark teal-green
- 枯樹：thick twisted dead trunk that forks, snapped limbs, a fine net of bare twigs against the sky / a few curled brown leaves

### 5.7 石頭、岩壁、地形件

```
Three-view turnaround of 【石或岩，例：a cluster of three rounded river boulders】, about 【尺寸，例：the largest 1.6 m long and 1.0 m tall】, form: 【形，例：rounded water-worn shapes with a few soft chipped edges, half buried in the ground】, surface: 【表面，例：warm grey stone with darker cracks, yellow-green lichen spots and thick moss on the top surfaces where rain falls】, 【周邊，例：small ferns and grass tufts growing at the base】.
Layout: front, side and top views, same scale, plain light warm-grey background, even soft lighting.
【接 5.2 固定風格段】
```

### 5.8 水邊與橋、棧道、水利

```
Three-view and three-quarter concept of 【物件，例：an old arched stone footbridge over a creek about 4 m wide】, 【尺寸，例：span 6 m, deck 1.4 m wide, arch 2.2 m above the water】, made of 【材質，例：fitted warm-grey granite blocks, worn smooth on the walking surface】, with 【細節，例：low stone railings, a carved but text-free keystone, moss along the waterline, ferns in the joints】, water: clear turquoise creek water, pebbles visible in the shallows, white foam where it flows around stones.
Layout: one three-quarter view with the water, plus front, side and top orthographic views of the structure alone on a plain light warm-grey background, same scale.
【接 5.2 固定風格段】
```

### 5.9 室內與家具

```
Interior concept of 【房間，例：the main room of a newcomer's borrowed old house】, about 【尺寸，例：7 m wide, 5 m deep, 3.2 m high】, containing 【家具，例：a simple wooden bed with a quilted cover, a writing desk with brush and inkstone, a meditation cushion on a woven mat, a small herb shelf, a storage chest】, light: warm morning sunlight through paper lattice windows making soft light shafts, plus a warm paper lantern, weathering: 【磨損，例：worn floorboards, a patched paper window, dried herbs hanging from a beam】.
Layout: one wide view from the doorway at eye height, plus a top-down floor plan of the furniture layout on the same sheet.
【接 5.2 固定風格段】
```

單件家具用 5.4 的三視圖骨架。

### 5.10 地面、牆、石材貼圖

```
Seamless tileable square texture of 【材質，例：a packed earth footpath with small scattered pebbles, dry cracks in a few places and grass creeping in at the edges】, viewed straight from above, real-world scale about 【範圍，例：2 m by 2 m】, hand-painted: large soft colour variation 【顏色，例：warm brown #8a6a44 to light tan #b8955e】, a few painterly brush strokes, small details readable but not noisy, even flat lighting (no shadows, no highlights baked in), edges must tile seamlessly on all four sides.
【接 5.2 固定風格段】
```

### 5.11 人物（村民、弟子、NPC）

```
Character turnaround sheet of 【人物，例：the old tea master of a valley village, a kind man in his seventies】, 【體型與身高，例：about 1.65 m tall, slightly stooped, thin】, wearing 【服裝，例：layered faded indigo cotton robes with a brown apron, cloth shoes, a bamboo hat hanging on his back】, carrying 【隨身物，例：a clay teapot and a cloth bundle】, expression and pose: 【表情與姿勢，例：gentle smile, neutral standing A-pose for modelling】, wear: 【磨損，例：patched elbows, tea stains on the apron, frayed hems】.
Layout: front, side and back full-body views at the same scale side by side, plus one face close-up, plain light warm-grey background, even soft lighting, one character only, no weapons unless written above.
【接 5.2 固定風格段】
```

### 5.12 場景概念（區塊、地標）

```
Wide aerial three-quarter view of 【場景，例：the upstream valley where the creek stopped flowing】, showing 【主要內容，例：a dry rocky creek bed with a cracked old sluice gate, a stand of red maples on the slopes, a small ruined shrine, a hunter's camp】, terrain: 【地形，例：rolling grassy hills that rise to grey cliffs, a waterfall that has dried to a trickle】, vegetation: 【植被，例：red maple groves, scattered pines, tall meadow grass with small white and yellow flowers】, mood: 【氣氛，例：quiet and a little melancholy, but sunlit】, distance: distant karst peaks with sect towers fading into layered mist.
Layout: 16:9 landscape, camera about 40 m above the ground looking across the valley, clear readable paths and landmarks.
【接 5.2 固定風格段】
```

### 5.13 生成設定

| 項目 | 設定 |
|---|---|
| 比例 | 三視圖、單件：3:2 或 16:9 橫幅；場景：16:9；貼圖：1:1 |
| 解析度 | 能選就選最高（至少 1536 px 寬） |
| 張數 | 同一段提示詞至少 4 張，挑最好的 |
| 種子 | 記下選中那張的 seed（工具有的話），寫進 `prompt.txt` |
| 參考圖 | 工具能放參考圖時，放 `art/references/world-directions-v1/` 裡最接近的一張，權重設低（只取光和色，不取構圖） |
| 不要改 | 5.2 固定風格段、5.3 負面提示、每類的 Layout 那一句 |

### 5.14 常見的錯（看到就重出）

- 光變成正午平光、陰影死黑 → 檢查有沒有接 5.2。
- 變成照片或寫實材質 → 負面提示沒貼。
- 三視圖三張大小不同、有透視 → Layout 那一句被改了。
- 冒出文字、招牌上有字 → 負面提示裡的 text 被刪了；招牌要寫 "without text"。
- 樹根像腳一樣撐在地上、樹底腫一大圈 → 5.6 的 base 那一句被刪了。
- 一張圖裡出現好幾個物件 → 加 "one object only"。

## 六、交件前自己檢查

- [ ] 輪廓好看（剪影測試：塗黑還認得出來）
- [ ] 顏色在第三節的色票範圍內，暗部冷、亮部暖
- [ ] 有磨損、苔、土、生活痕跡
- [ ] 真實尺寸；樹根和石頭有埋進地面
- [ ] 三層細節（LOD0/1/2）
- [ ] 在遊戲裡截圖，跟方向圖並排比過
- [ ] 提示詞（照第五節骨架、只改【】欄位）和三視圖存在 `art/references/<件名>/`
