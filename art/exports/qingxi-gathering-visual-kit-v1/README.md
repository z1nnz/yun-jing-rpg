# 青溪採集路段素材 v001（半寫實）

> **v002 已依建模前 AI 三視圖重建，見 [`README_v002.md`](README_v002.md)。** 本檔描述 v001，保留不改。

> **暫存素材，尚未通過正式美術驗收。** z1nnz 於 2026-10-28 指示先合併協作者已交付的素材，後續再補三視圖與修訂模型。本次只收入模型、貼圖、母稿及檢視圖；獨立採集展示與其非正式 API 接線未併入。下述建模前缺少 AI 三視圖的事實保留，不把建模後渲染圖寫成前置參考。

## 作者與來源

- **實際作者**：Claude（Anthropic，Claude Code）依使用者 joshsu54 的工單撰寫 Blender Python 程序化建模腳本並生成。
  - 沒有使用 AI 3D 生成、外部模型、掃描或素材庫；所有幾何與材質都由 `art/source/qingxi-gathering-visual-kit-v1/` 的腳本產生。
- **工具**：Blender 5.2（Cycles CPU 烘焙）。示範使用 Three.js 0.170.0（CDN）。
- **三視圖**：建模前**沒有** AI 生成的三視圖，與 `AGENTS.md` 及工單 B 第 1.5 小時的要求不符。
  - `art/references/qingxi-gathering-visual-kit-v1/threeview_semireal_v001/` 是建模後由同一模型渲染的正／側／頂視圖（附尺寸），不是建模前的設計參考。

## 規格

- 1 單位 = 1 m，正面 -Y（GLB 為 +Y 朝上，正面在 glTF 空間朝 +Z）。
- 原點在底部中心。
  - 青溪蘭、赤露參、玉脈石、山門、蘆草：原點在地面高度，地面融合邊緣略低於 0。
  - 踏板：原點在包圍盒底部中心，也就是卵石底。
- 每個狀態都是 1 網格 1 材質，貼圖 4 張：BaseColor／Roughness／Normal（OpenGL 切線空間）／Emission。
  - 山門與玉脈石為 2048 px，其餘 1024 px。

| 狀態 | 寬×深×高（m） | 遊戲三角形 |
|---|---|---|
| 採藥山門（地標） | 4.40 × 2.90 × 4.46 | 59,882 |
| 青溪蘭 採前／採後 | 0.86 × 0.76 × 0.51 ／ 0.82 × 0.76 × 0.30 | 35,320 ／ 23,596 |
| 赤露參 採前／採後 | 1.03 × 0.94 × 0.32 ／ 1.04 × 0.94 × 0.32 | 84,544 ／ 71,716 |
| 嵌地玉脈石 採前／採後 | 2.34 × 2.03 × 1.13 ／ 2.34 × 2.03 × 0.83 | 46,332 ／ 44,720 |
| 渡溪踏板 | 0.98 × 0.79 × 0.63（板面 0.732 × 0.72，高 0.62） | 10,960 |
| 水邊蘆草 | 1.25 × 1.08 × 1.91 | 35,166 |

- **路寬**：示範主路 1.6 m；踏板段由 6 個模組按板面寬首尾相接（4.39 m），板面連續無縫。

## 檔案

- `<Asset>/v001/`：每個狀態的 `.glb`（貼圖內嵌）、`.fbx`（貼圖在 `textures/`）、`.blend`（程序化原始模型＋遊戲網格）、`_model_info.json`（尺寸、面數、雜湊、烘焙參數）。
- `QX_QingxiGatheringKit_master_v001.blend`：Blender 母檔，前排為全部程序化原始模型，後排（y = 6 m）為回匯的遊戲 GLB。
- 圖庫：`art/previews/qingxi-gathering-visual-kit-v1/index.html`。
- 十視圖、三視圖、平視圖：`art/references/qingxi-gathering-visual-kit-v1/views_v001/`、`threeview_semireal_v001/`。
- 示範走查截圖：`art/references/qingxi-gathering-visual-kit-v1/walkthrough_v001/`。

## 重建命令

在 `art/source/qingxi-gathering-visual-kit-v1/` 執行：

```bash
blender -b --python-exit-code 1 --python bake_export.py
```

```bash
blender -b --python-exit-code 1 --python bake_export.py -- --master
```

```bash
blender -b --python-exit-code 1 --python render_views.py
```

```bash
uv run --no-project --with pillow python make_sheets.py
```

## 已實際檢查

- 每個 GLB 都回匯 Blender 檢查：網格／材質／貼圖數、尺寸與 model_info 誤差 < 1 mm、三角形數、原點。結果在各 `validation.json`。
- 協作者原分支曾在瀏覽器走查獨立展示；本次僅合併素材，該展示不屬於 `main` 交付內容。

## 尚未接入／未驗證

- 沒有匯入 Unity、Unreal 或 Godot；碰撞體、LOD、導航網格都沒做。
- 遊戲材質不含背光透射、次表面散射、水晶透射與金屬度（已烘成顏色）。
- 面數偏高，特別是赤露參約 8.5 萬三角形，草叢應改用插片或實例化草。
- 沒有接正式伺服器、存檔或背包系統。本次未合併獨立展示；任何正式採集交互都須使用現有服務端契約與資產帳本。
- 尚未放進 v12 村口實景測試遠看效果：只做了平地 40 m 平視圖與示範內的遠景。
