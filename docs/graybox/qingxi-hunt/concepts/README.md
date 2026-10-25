# 青溪狩獵區：六區概念圖

日期：2026-10-25。對應 [圖稿與模型需求](../art-requirements.md) 的 C01–C06，每區一張。

**狀態：C01–C06 已由內建 image_gen 生成並檢視。** 正式原圖保存在 [美術補件 v001](../../../../art/authored/qingxi-hunt/v001/index.html) 的 concepts/，實際使用提示詞見該批 concept-prompts.json；下表保留原始策劃提示詞。概念圖只定氣氛、材質語言與視線，不作尺寸或導航依據；尺寸以 [layout.json](../layout.json) 為準，灰盒模型見 [blender/](../blender/README.md)。

## 共用風格（每則提示詞後面都要接上）

> stylized hand-painted 3D environment concept for a mobile-first third-person xianxia RPG, warm river valley blended with ancient forest wetland (Yun Jing Qingxi starting region), soft morning light, readable walkable paths, restrained magic, low-poly-friendly shapes, no characters in the foreground, no UI, no text, no labels, no arrows

## 六張圖

| 檔名 | 區域（layout.json 尺寸） | 提示詞 |
| --- | --- | --- |
| `C01_settlement-exit.png` | 聚落出口 30 × 24 m | Eye-level third-person view from a small village exit square: packed-earth clearing, a simple wooden material-trader stall with hides and herbs, a weathered notice board, a stone path curving uphill out of frame; the far hunting meadow is hidden behind a tree-covered ridge; tiny silhouette of one traveller for scale. |
| `C02_mountain-trail.png` | 過渡山道長約 60 m、寬 5–10 m | A 6 m wide dirt-and-stone mountain trail bending between a grey rock ridge and pine trees; small rabbit footprints in soft mud at the trail edge and one clump of grass visibly pressed down; open space around the bend for a camera behind the player. |
| `C03_herb-forest.png` | 採藥林 50 × 40 m | Sparse pine and bamboo grove with dappled light; six small glowing pale-green spirit-herb clumps spread across mossy ground, each readable from a distance; one large mossy rock you can walk around; wide gaps between trunks, peaceful gathering mood, no combat. |
| `C04_rabbit-meadow.png` | 山兔草坡 80 × 60 m，最高 +2.4 m | Gentle open grassy slope with low grass and a few taller tufts; three small groups of round mountain rabbits grazing far apart; two grey boulders and one lone tree; trampled lines in the grass hint at escape routes; dense trees only at the edges so rabbits stay visible. |
| `C05_shallow-stream.png` | 溪流淺灘 40 × 30 m | Wide clear shallow stream about ankle deep with a pebble bed, smooth bank stones you can step across, gentle sloped banks; a darker deep pool on one side closed off by large rocks; a dirt path continues downstream toward the village. |
| `C06_return-shortcut.png` | 回村捷徑長約 70 m | Wide valley-floor path leading back toward distant village roofs and smoke; stone path pieces, pines and a low layered cliff on one side; the route is obvious from the landscape alone, no signs or arrows. |

生成後請保持原檔，不要裁切或覆寫；若重生，用 `_v002` 等版本號另存。
