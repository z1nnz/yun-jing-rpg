# qingxi-world-ruins-b：人造邊界套件＋破舊建築小場景

工作單「B｜蘇奕安 Josh：人造邊界套件＋三個破舊建築小場景」，分支 `feature/world-ruins-kit-b`。
另依使用者要求加做八款破舊房屋 H01–H08（第一次 PR 只放 H01，其餘下次另開 PR）（參考圖：`art/references/qingxi-world-ruins-b/house-variants/`，計畫見 [HOUSES_PLAN.md](HOUSES_PLAN.md)）。

全部用 Blender 5.2 程序化建模（`build.py` 由程式產生模型、烘焙貼圖、匯出、驗證、出圖），沒有使用 AI 3D 生成或外部素材。
依 AGENTS.md，每個物件建模前都先用 AI 產生三視圖參考並存檔（`art/references/qingxi-world-ruins-b/`）。

## 目錄

| 位置 | 內容 |
|---|---|
| `art/source/qingxi-world-ruins-b/` | 產生器原始碼（本資料夾） |
| `art/exports/qingxi-world-ruins-b/<ID>/` | `<ID>_v001.fbx`（LOD0／LOD1／LOD2＋_Collision）、`<ID>_v001.glb`（LOD0＋_Collision）、`Textures/`、`model_info.json`、`validation.json` |
| `art/previews/qingxi-world-ruins-b/<ID>/` | 四視圖（正、側、背、3/4，旁有 1.75 m 人形與 0.25 m 刻度尺）、hero、特寫、LOD 對照 |
| `art/previews/qingxi-world-ruins-b/_compare/` | 與既有資產並排的比例／風格對照 |
| `art/previews/qingxi-world-ruins-b/demo/` | three.js WASD 試走頁 |
| `art/references/qingxi-world-ruins-b/` | AI 三視圖參考與提示詞、批次審查紀錄 |

## 資產清單

**第一次 PR 只包含下表 16 個資產（非房屋資產＋H01）。** H02–H08 與 D3_AbandonedHut 仍是舊的 2048 貼圖版本，不在這次 PR 內，之後改用新貼圖預算重建，再另開 PR 上傳。

| ID | 名稱 | 尺寸 x × y × 高（m） | 三角面 LOD0 / LOD1 / LOD2 | 貼圖 | 碰撞 | GLB |
|---|---|---|---|---|---|---|
| A2_OverturnedCart | 翻覆推車 | 3.43 × 1.78 × 1.56 | 27,292 / 13,644 / 4,092 | 2 組 × 2048 | 6 | 3.8 MB |
| D3_DryWell | 枯井 | 1.77 × 1.47 × 2.10 | 73,236 / 36,617 / 10,985 | 2 組 × 2048 | 14 | 5.8 MB |
| H01_StoneTimberHouse | 厚重石木屋（炭青陶瓦） | 5.46 × 4.35 × 3.79 | 126,870 / 63,435 / 19,029 | 4 組 × 1024 | 14 | 6.9 MB |
| R01_DryStoneWall_Collapsed | 乾砌石牆・塌了一半的斷段 | 3.00 × 1.90 × 0.95 | 36,828 / 18,414 / 5,524 | 1 組 × 2048 | 3 | 3.8 MB |
| R01_DryStoneWall_Corner | 乾砌石牆・轉角 | 1.82 × 1.80 × 0.96 | 34,956 / 17,478 / 5,242 | 1 組 × 2048 | 2 | 3.8 MB |
| R01_DryStoneWall_EndCap | 乾砌石牆・收頭（加做） | 0.51 × 0.58 × 0.95 | 6,028 / 3,014 / 904 | 1 組 × 1024 | 1 | 0.9 MB |
| R01_DryStoneWall_Straight | 乾砌石牆・直段 3 m | 3.00 × 0.62 × 0.95 | 39,712 / 19,856 / 5,956 | 1 組 × 2048 | 1 | 4.0 MB |
| R02_BambooFence_Corner | 竹籬笆・轉角 | 1.26 × 1.22 × 1.16 | 50,808 / 25,404 / 7,620 | 1 組 × 1024 | 2 | 2.3 MB |
| R02_BambooFence_EndPost | 竹籬笆・端柱（加做） | 0.14 × 0.22 × 1.16 | 6,520 / 3,260 / 978 | 1 組 × 512 | 1 | 0.4 MB |
| R02_BambooFence_Leaning | 竹籬笆・歪倒的一段 | 2.20 × 1.88 × 1.16 | 41,664 / 20,832 / 6,248 | 1 組 × 1024 | 1 | 2.0 MB |
| R02_BambooFence_Straight | 竹籬笆・直段 2 m | 2.14 × 0.22 × 1.16 | 45,200 / 22,600 / 6,780 | 1 組 × 1024 | 1 | 2.1 MB |
| R03_FirewoodNeat | 柴堆（整齊） | 1.64 × 0.78 × 0.96 | 60,148 / 30,074 / 9,022 | 1 組 × 2048 | 1 | 4.4 MB |
| R03_FirewoodScattered | 柴堆（散亂） | 2.78 × 2.06 × 0.73 | 32,008 / 16,004 / 4,800 | 1 組 × 1024 | 3 | 1.8 MB |
| R04_StoneLanternBroken | 石燈籠（殘損） | 0.58 × 0.58 × 1.24 | 36,032 / 18,010 / 5,402 | 1 組 × 1024 | 3 | 1.8 MB |
| R04_StoneLanternIntact | 石燈籠（完整） | 0.68 × 0.68 × 1.65 | 33,280 / 16,640 / 4,992 | 1 組 × 1024 | 3 | 1.7 MB |
| R05_Milestone | 里程石 | 0.81 × 0.49 × 1.35 | 11,036 / 5,518 / 1,654 | 1 組 × 512 | 1 | 0.4 MB |

尺寸為地面以上；FBX 含三個 LOD，GLB 只含 LOD0（給預覽用）。每組貼圖 = BaseColor、Normal、ORM 三張。
這 16 個 GLB 合計 **46 MB**（47,160 KB），在瀏覽器首次下載 50 MB 預算內（舊版整套 679 MB）。

## R01／R02 介面

`model_info.json` 的 `interfaces` 記錄每段的接點（Blender 座標，公尺，前方 -Y）：

- R01 乾砌石牆：直段與崩塌段長 3 m，`start (-1.5, 0, 0)` → `end (1.5, 0, 0)`；轉角 `start (-1.5, 0, 0)` → `end (0, 1.5, 0)`（向 +Y 轉 90°）；端頭只有 `start (-0.25, 0, 0)`。
- R02 竹籬：直段與傾倒段長 2 m，`start (-1, 0, 0)` → `end (1, 0, 0)`；轉角 `end (0, 1, 0)`；端柱為單根柱。
- 串接方式：下一段的 `start` 對齊上一段的 `end`，方向一致。示範頁就是用這個規則排出 36 m 石牆與 34 m 竹籬。

## 建置

```bash
"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python art/source/qingxi-world-ruins-b/build.py -- <ID>
```

- 每個資產必須通過 `validation.json` 全部檢查（尺寸上限、埋入深度、原點、LOD 比例、貼圖密度 ≥ 256 px/m 等）才算完成。
- 比較圖：`blender -b --factory-startup --python art/source/qingxi-world-ruins-b/compare.py`
- 快速材質預覽（不烘焙）：`blender -b --factory-startup --python art/source/qingxi-world-ruins-b/quicklook.py -- <ID> <輸出資料夾>`

## WASD 試走

從儲存庫根目錄啟動本機伺服器（僅綁 127.0.0.1）：

```bash
uv run --no-project python -m http.server 8765 --bind 127.0.0.1
```

開啟 `http://127.0.0.1:8765/art/previews/qingxi-world-ruins-b/demo/`。點畫面鎖定滑鼠，WASD 移動、Shift 跑、F 切換飛行。
three.js 固定 0.160.0（unpkg）。碰撞以各資產 `_Collision` 的包圍盒近似；示範用 LOD0，不切 LOD。
這是預覽工具，不是遊戲內容，沒有接入 `apps/game`。

## 放置注意

- **D3_DryWell** 井筒建到地下 1.6 m。放進場景時地形要挖一個直徑約 0.9 m 的洞（示範頁的地面就是挖了洞的）。
- **A2_OverturnedCart** 的翻倒姿勢是把立正的車當剛體，在往 -Y 滾的穩定凸包邊中，選最接近側躺（90°）的那一條，所以車是真的側翻，不是只傾斜；麻袋再用剛體模擬靠著車身落定。
- **R03_FirewoodScattered** 是 48 根柴分批落下、用剛體模擬堆成的小丘，柴堆本體約 1.9 × 1.3 × 0.7 m，連同滾開的幾根，佔地約 2.8 × 2.1 m。
- 房屋都可走入：門 ≥ 0.9 × 1.9 m、室內留 2 × 2 m 淨空。

## 貼圖預算

- GLB 內的貼圖一律存成 WebP（Blender glTF 匯出內建的 `EXT_texture_webp`，品質 90）；`Textures/` 資料夾保留 PNG 給 Unity 匯入。
- 房屋改為 4 組 × 1024 貼圖。在這個解析度下，房屋的貼圖密度下限從 256 px/m 降為 **125 px/m**（`assets.py` 的 `min_texel`）；其他資產維持 256 px/m。
  這是為了預算而放寬的規格，近看房屋牆面時會比其他資產略糊。

## 目前狀態（2026-10-31，誠實紀錄）

這 16 個資產都已用目前的程式重建，`validation.json` 檢查全部通過（16／16）。自評如下，**還有多項沒到 95 分的交付門檻**，所以這一版仍是進行中。

| 資產 | 自評 | 主要不足 |
|---|---|---|
| H01_StoneTimberHouse | 約 95 | 1024 貼圖下近看牆面略糊（預算取捨） |
| R04 石燈籠・完整 | 約 95 | — |
| R04 石燈籠・殘損 | 約 94 | 斷面邊緣仍略整齊 |
| A2_OverturnedCart | 約 94 | 麻袋布料近看偏光滑 |
| R03 柴堆・散落 | 約 94 | 少數柴枝的接觸陰影偏弱 |
| R05 里程石 | 約 93–94 | 鑿面與地衣層次仍弱於參考圖 |
| R01 乾砌石牆（4 種） | 約 93–94 | 石塊大小節奏仍略平均 |
| R02 竹籬（4 種） | 約 93–94 | 竹節顏色變化偏少 |
| R03 柴堆・整齊 | 約 93 | 端面劈裂紋路遠看仍偏規則 |
| D3_DryWell | 約 92–93 | 井架木料與繩子細節仍弱 |

## 已知問題與待決事項

1. **貼圖預算。** 這次 PR 的 16 個資產共 21 組貼圖（8 組 2048、11 組 1024、2 組 512，每組 3 張），含 mipmap 約 1.8 億像素。
   Unity 用 BC7／ASTC 這類每像素約 1 byte 的壓縮格式時約 180 MB，在 300 MB 貼圖記憶體預算內。
   但 three.js 示範頁的 WebP 會解成未壓縮的 RGBA，同時全部載入時顯示記憶體約 0.7 GB；這只影響預覽頁，不代表遊戲內的用量。
   房屋另外八棟（H02–H08、D3_AbandonedHut）要改成 4 × 1024 之後，才能放進下一個 PR。
2. **風格落差。** 既有的 StarterHouse_v004、StoneArchBridge_v001、CommonPine 是低面數平塗風格，這套是半寫實風格（見 `_compare/`）。混放前要確認目標風格。
3. **WASD 示範只驗證了載入與畫面。** 在內建瀏覽器中整頁載入成功（16 種資產、41 個擺放，約 46 MB），場景顯示正常。
   自動化環境拿不到滑鼠鎖定（pointer lock），所以實際走動和碰撞沒有實測，請用一般瀏覽器確認。
   載入方式改成先用 `fetch` 下載完整檔案，再交給 `GLTFLoader.parseAsync`；原本的串流下載遇到連線重置時，promise 會一直卡住、不會結束。
   可加 `?lite`（略過房屋）或 `?only=R01,R02` 只載入部分資產。
4. **A2 參考圖不合格。** A2 的 AI 三視圖（v002，評 81 分）各視圖彼此不一致，沒有被當成核准的建模依據；車的零件照參考圖，姿勢由剛體翻倒計算決定。
5. **D3_DryWell 需要地形開洞**（見上方「放置注意」）。
6. **這一輪修正：**
   - GLB 內貼圖改存 WebP，房屋改 4 × 1024，整體 GLB 從 679 MB 降到 46 MB（這次 PR 的範圍）。
   - 石燈籠：火袋改成四角柱＋退縮窗框＋燈座，殘損版的楣石不再因布林運算消失。
   - 里程石：頂部改成多面鑿削，加正面鑿平的邊框與凹面，地衣改為有分瓣邊緣的圓斑。
   - 乾砌石牆：石塊改圓潤的田野石，縫中多塞卵石，統一灰綠色調加地衣。
   - 竹籬：每個交叉點改成纏繞＋雙層 X 綁法，竹子改成褪色的橄欖灰。
   - 枯井：井圈改四層較小的石塊，橫樑改為手斧削的原木；柴堆端面加放射狀乾裂紋。
   - 法線與 ORM 貼圖從 16-bit 改 8-bit。
7. 未在 Unity 內匯入測試，未做手機效能實測。
