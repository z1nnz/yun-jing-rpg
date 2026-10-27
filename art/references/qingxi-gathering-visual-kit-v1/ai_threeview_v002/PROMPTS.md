# 青溪採集路段 v002：建模前 AI 三視圖提示詞

PR #31 整合檢查要求：v001 六件模型在沒有預先 AI 三視圖的情況下建成。本資料夾保存 v002 修訂前**先生成、經檢視**的 AI 參考圖。修訂版 v002 模型必須在這些圖存入並檢視之後才建。

## 生成方式

- **工具**：ChatGPT 或 Codex 的圖像生成，由使用者 joshsu54 操作。Claude Code 本身沒有生圖工具，只負責撰寫提示詞、檢視圖片、依圖建模。
- **每件一張圖**：同一張畫布由左到右畫「正面／右側面／背面」三視圖，正交投影，三圖同比例並排、底線對齊。
- 青溪蘭、赤露參、玉脈石另有一張**採後狀態**圖。建議生成，非必須。
- 每張存成 PNG，用下表檔名放進本資料夾：
  - `art/references/qingxi-gathering-visual-kit-v1/ai_threeview_v002/`
- 若某張要重生，舊圖保留並改名加 `_rejected1`，新圖用原檔名。檢視紀錄會寫明採用哪一張。

| 檔名 | 物件 | 必要 |
|---|---|---|
| `R01_QX_SpiritHerb_Qinglan.png` | 青溪蘭（採前） | 是 |
| `R01b_QX_SpiritHerb_Qinglan_post.png` | 青溪蘭（採後） | 建議 |
| `R02_QX_SpiritHerb_Chilu.png` | 赤露參（採前） | 是 |
| `R02b_QX_SpiritHerb_Chilu_post.png` | 赤露參（採後） | 建議 |
| `R03_QX_EmbeddedOre_Yumai.png` | 嵌地玉脈石（採前） | 是 |
| `R03b_QX_EmbeddedOre_Yumai_post.png` | 嵌地玉脈石（採後） | 建議 |
| `R04_QX_GatheringLandmark.png` | 採藥山門 | 是 |
| `R05_QX_CreekSteppingPlank.png` | 渡溪踏板 | 是 |
| `R06_QX_WaterReeds.png` | 水邊蘆草 | 是 |

## 共用風格段（每段提示詞已內含，不用另貼）

> Semi-realistic anime-style 3D game environment asset concept, production model sheet. Orthographic three-view turnaround on one canvas, left to right: FRONT view, RIGHT SIDE view, BACK view. All three views at identical scale, bottoms aligned on one ground line, evenly spaced, no perspective, no camera tilt. Plain flat light-grey background, soft even studio lighting, no cast shadow on background. Painterly but grounded materials: hand-painted texture feel with realistic form, clear big/medium/small shape hierarchy, subtle ambient occlusion and edge wear. Palette anchored on Chinese xianxia mountain-village tones: celadon / jade green accents, warm aged wood, pale grey stone, soft moss. No characters, no text, no labels, no watermark, no UI, no scenery behind the object. Small natural ground blend at the base only (a thin irregular patch of soil and grass that fades out), not a display plinth or a thick soil slab.

---

## R01 青溪蘭（靈草一，採前）

尺寸目標：寬約 0.85 m × 深約 0.75 m × 高約 0.50 m。

```
Semi-realistic anime-style 3D game environment asset concept, production model sheet. Orthographic three-view turnaround on one canvas, left to right: FRONT view, RIGHT SIDE view, BACK view, identical scale, bottoms aligned on one ground line, no perspective. Plain flat light-grey background, soft even studio lighting. No text, no labels, no watermark, no characters.

Subject: "Qingxi Orchid", a gatherable spirit herb by a mountain creek, about 0.85 m wide, 0.75 m deep, 0.5 m tall. A single clump of long, arching, strap-like dark green orchid leaves (cymbidium-like, 20 to 30 leaves) fanning out in a graceful fountain shape, leaf tips slightly drooping, a few leaves with pale yellow-brown dry tips. From the centre rise 3 to 4 thin flower spikes carrying small pale white-jade flowers with a faint cool cyan glow at their throats, the glow subtle and readable as "harvestable". At the base: a few round pseudobulbs, a small flat grey creek stone partly behind the clump on the back-left, a few short grass tufts and fallen dry leaves. Material: leaves have a slight waxy sheen and colour gradient from dark base to lighter tips. Thin irregular ground blend of damp dark soil, moss and pebbles that fades out at the edges, not a plinth.

Semi-realistic Chinese xianxia mountain-village style, celadon and jade accents, painterly but grounded, clear silhouette readable from 3 m away.
```

## R01b 青溪蘭（採後）

```
Same orchid clump as the reference "Qingxi Orchid", same orthographic three-view layout (FRONT, RIGHT SIDE, BACK), identical scale, light-grey background, no text.

State: AFTER HARVEST. The flower spikes have been cut: short cut stalk stubs with clean pale cut ends, no flowers, no glow. About a third of the leaves are trimmed or bent down, the clump is lower (about 0.3 m tall) and looks sparse but still alive. A few cut leaf pieces and petals lie on the soil. The small creek stone, grass tufts and ground blend are unchanged so the spot stays recognisable.

Semi-realistic Chinese xianxia mountain-village style, painterly but grounded.
```

## R02 赤露參（靈草二，採前）

尺寸目標：寬約 1.0 m × 深約 0.9 m × 高約 0.32 m。

```
Semi-realistic anime-style 3D game environment asset concept, production model sheet. Orthographic three-view turnaround on one canvas, left to right: FRONT view, RIGHT SIDE view, BACK view, identical scale, bottoms aligned, no perspective. Plain flat light-grey background, soft even studio lighting. No text, no labels, no watermark, no characters.

Subject: "Red Dew Ginseng", a low gatherable spirit herb patch in a forest-edge meadow, about 1.0 m wide, 0.9 m deep, only 0.32 m tall. One ginseng-like plant in the centre: a short upright stem with 3 to 5 palmate compound leaves (five broad serrated leaflets each) held flat like an umbrella, and on top a tight round cluster of glossy bright red berries with tiny dew drops, the clear focal point. One or two smaller ginseng plants with smaller berry clusters nearby. Around it a LOW, SPARSE ring of meadow grass in a few distinct clumps with gaps of bare soil and moss between them, so the ginseng leaves and berries are never hidden; grass shorter than the ginseng. A hint of a pale root crown visible at the soil. Thin irregular ground blend of dark soil, moss and a few pebbles that fades out at the edges, not a plinth.

Semi-realistic Chinese xianxia style, celadon and jade green with the red berries as the only saturated accent, painterly but grounded, readable from 3 m.
```

## R02b 赤露參（採後）

```
Same "Red Dew Ginseng" patch, same orthographic three-view layout (FRONT, RIGHT SIDE, BACK), identical scale, light-grey background, no text.

State: AFTER HARVEST. The central ginseng plant has been dug up: a small fresh hole of loose turned dark soil with a few root hairs, the stem gone, two or three torn leaflets lying beside it, no red berries left. The smaller side plants and the grass clumps remain unchanged so the spot stays recognisable. Overall height and footprint about the same.

Semi-realistic Chinese xianxia style, painterly but grounded.
```

## R03 嵌地玉脈石（石礦，採前）

尺寸目標：寬約 2.3 m × 深約 2.0 m × 高約 1.1 m。

```
Semi-realistic anime-style 3D game environment asset concept, production model sheet. Orthographic three-view turnaround on one canvas, left to right: FRONT view, RIGHT SIDE view, BACK view, identical scale, bottoms aligned, no perspective. Plain flat light-grey background, soft even studio lighting. No text, no labels, no watermark, no characters.

Subject: "Jade Vein Ore", a gatherable mining node half-buried in the ground, about 2.3 m wide, 2.0 m deep, 1.1 m tall. Two large weathered pale-grey granite boulders sunk into the earth, with layered strata lines, cracks, rounded worn edges and moss on their tops and north faces. Between the boulders, a cluster of translucent pale jade-celadon crystals grows out of a split: one tall main crystal (about 1 m) and 4 to 6 smaller ones at different angles, hexagonal, slightly frosted with a soft inner glow, the clear focal point. A visible jade vein runs as a thin glowing seam across the boulder faces. A few small rock chips and crystal shards at the base, a couple of grass tufts. Boulders clearly sink into the soil with a thin ground blend of soil, gravel and moss, not sitting on a plinth.

Semi-realistic Chinese xianxia style, pale stone with celadon jade accents, painterly but grounded, strong readable silhouette from 8 m.
```

## R03b 嵌地玉脈石（採後）

```
Same "Jade Vein Ore" boulders, same orthographic three-view layout (FRONT, RIGHT SIDE, BACK), identical scale, light-grey background, no text.

State: AFTER MINING. The jade crystal cluster has been chipped out: only short broken crystal stumps with rough fresh fracture faces remain in the split, the inner glow is gone and the vein seam is dull. Fresh pale chisel marks and scattered rock chips around the split. Boulders, moss and ground are unchanged. Overall height lower (about 0.8 m).

Semi-realistic Chinese xianxia style, painterly but grounded.
```

## R04 採藥山門（採集地標）

尺寸目標：寬約 4.4 m × 深約 2.9 m × 高約 4.5 m，門洞淨寬約 2.2 m，讓 1.6 m 主路與角色通過。

```
Semi-realistic anime-style 3D game environment asset concept, production model sheet. Orthographic three-view turnaround on one canvas, left to right: FRONT view, RIGHT SIDE view, BACK view, identical scale, bottoms aligned, no perspective. Plain flat light-grey background, soft even studio lighting. No text, no labels, no watermark, no characters.

Subject: "Herb-gatherers' Gate", a small rustic Chinese timber paifang gateway marking the entrance to a herb-gathering trail, about 4.4 m wide, 2.9 m deep including side braces, 4.5 m tall, with a walk-through opening about 2.2 m wide and 2.6 m high. Two hewn weathered wooden posts standing in carved stone clamp blocks with dark iron hoops, each post braced front and back by raking timber struts. A tie beam with through-tenons and wooden wedges, a framed jade-green wooden plaque in the centre carved with a simple leaf-and-drop herb emblem (no readable characters). Above, a lintel with carved bracket blocks, topped by a small grey tile hip roof with upturned eave corners, rolled ridge tiles, moss on the tiles, and a pale jade pearl ornament on a lotus base at the ridge centre. Two long celadon cloth banners with the herb emblem hang from the roof overhangs, a warm paper lantern hangs on one side, dried herb bundles hang from the tie beam, a woven herb basket rests at the foot of one post. Aged warm wood, pale grey stone, celadon accents; the back view shows the plain back of the plaque and the bracing.

Semi-realistic Chinese xianxia mountain-village style, painterly but grounded, readable landmark silhouette from 14 m.
```

## R05 渡溪踏板（模組）

尺寸目標：寬約 0.98 m × 深約 0.79 m × 高約 0.63 m；板面約 0.73 × 0.72 m，可首尾相接。

```
Semi-realistic anime-style 3D game environment asset concept, production model sheet. Orthographic three-view turnaround on one canvas, left to right: FRONT view, RIGHT SIDE view, BACK view, identical scale, bottoms aligned, no perspective. Plain flat light-grey background, soft even studio lighting. No text, no labels, no watermark, no characters.

Subject: "Creek Stepping Plank", one repeatable module of a simple rustic footbridge across a shallow mountain creek, about 1.0 m wide, 0.8 m deep, 0.63 m tall. Two short round wooden piles, each set in a small pile of grey river cobbles, with a green damp algae band and darker wet wood on the lower third. Each pile carries a short round cross-log, lashed with dark rope and an iron staple. On top, three thick hand-split wooden boards laid side by side across the cross-logs, forming a flat walking deck about 0.73 m long and 0.72 m wide, the board ends flush so modules can be chained end to end. Boards weathered silver-brown with grain, small square iron nail heads, slight wear in the middle where people walk. Front and back views look the same; side view shows the board length.

Semi-realistic Chinese xianxia mountain-village style, warm aged wood and pale stone, painterly but grounded.
```

## R06 水邊蘆草

尺寸目標：寬約 1.25 m × 深約 1.1 m × 高約 1.9 m。

```
Semi-realistic anime-style 3D game environment asset concept, production model sheet. Orthographic three-view turnaround on one canvas, left to right: FRONT view, RIGHT SIDE view, BACK view, identical scale, bottoms aligned, no perspective. Plain flat light-grey background, soft even studio lighting. No text, no labels, no watermark, no characters.

Subject: "Creekside Reeds", one clump of waterside reeds and cattails on a muddy creek bank, about 1.25 m wide, 1.1 m deep, 1.9 m tall. Tall thin straight reed stems with long narrow ribbon leaves bending outward in layers, a mix of fresh green and pale straw-yellow dry leaves. Three or four brown cylindrical cattail heads on stiff stalks, one split open with white fluff, and two or three feathery pale reed plumes arching at the top. Lower, shorter blades and a few broken bent stems for a natural irregular silhouette, denser at the base and open at the top with clear gaps. At the base, a thin irregular patch of wet grey-brown mud with a few pebbles and short grass, fading out, not a plinth.

Semi-realistic Chinese xianxia mountain-village style, soft greens and straw tones, painterly but grounded, readable from 8 m.
```
