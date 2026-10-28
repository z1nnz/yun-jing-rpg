# 青溪場景與協作者素材接入表

更新：2026-10-28。這裡把「收到模型」「放入某個 Unity 場景」「出現在目前試玩版」「完成玩法」分開。詳細產品順序見[開發進度表](development-roadmap.md)。來源欄是原作者；z1nnz／Codex 對採用、接線和整合負責，不把協作者建模記成核心組原創。

| 素材／工作 | 原作者及位置 | 進儲存庫 | 進 Unity | 進目前入口試玩 | 遊戲互動 |
|---|---|---|---|---|---|
| TownLayout v004，48×54 m 街區原件 | joshsu54／Dondon，`art/incoming/dondon/TownLayout/v004/` | 是 | 整包未直接用在小入口 | 否 | 否；整包高面數，待拆件、LOD、碰撞 |
| 較大青溪鎮，151 筆配置 | joshsu54 交接模型＋核心組場景配置，`apps/game/Assets/QingxiWorld/` | 是 | 是，原獨立生成器加上 PR #27 的統一場景 | 是，統一 Windows 試玩版已顯示城鎮 | 本機走路與兔子替身；正式採獵／背包未接 |
| StarterHouse v004、StoneArchBridge、MountainStreamBend、MountainStonePath／Stairs、CliffBoardwalk、QCaveEntrance、SectGate、LayeredCliff、CommonPine、BambooClump、MossBoulderSet | joshsu54／Dondon 原件；選入 `apps/game/Assets/YunJing/Models/CollaboratorWorldV1/` | 是 | 是，`YunJing.Editor.QingxiWorldBuilder` 已逐件排放 | 是，視野與距離依角色位置 | 基本場景模型；不是可開門、交易或採集的成品 |
| 原創臨水客舍 v1、D02 木造梁橋 | 客舍：z1nnz 指導／Codex 製作；D02：joshsu54，來源為 `EnvironmentTransitionKit/v001` | 是；來源母稿與匯出檔均保留 | 是，`QingxiWorldPreview` 的河邊客舍與主跨河橋已改用這兩件；舊 v1 俯視圖未同步重繪 | 是，重新生成 Preview 後可見；Unity 接地與過橋路線檢查通過 | 客舍為場景物；橋用獨立步行碰撞面，尚未完成玩家視角人工檢視 |
| 原創聽風台與入口支路 | z1nnz 指導／Codex 製作，PR #27 | 在草稿 PR | 是，小入口與統一場景 | 是；統一版將聽風台放在較大城鎮入口 | 石構件有碰撞；未完整人工走位驗收 |
| 道路／河岸／橋頭 31 件 EnvironmentTransitionKit | joshsu54，`art/incoming/dondon/EnvironmentTransitionKit/v001/`，PR #29 | **已合入 main** | 尚未整批匯入可玩場景 | 否 | 否；下一步按路段挑選、設材質和碰撞 |
| 山兔 v003 骨架、動畫、LOD | Johnny0823／Codex，PR #21 | 是 | 模型交接；目前入口未接戰鬥 | 否 | 服務端掉落規則另有原型，兩者尚未接通 |
| 演武棚等六件公共演武區模型 | Johnnnny0823／Codex，PR #32 | **已合入 main** | 演武棚已轉 FBX 擺入統一城鎮；其餘待接 | 演武棚與練功石已在入口 PWA 可見 | 正式修行與獎勵未接 |
| 溪畔採集六件模型、九種狀態 | joshsu54／Claude Code，PR #31 的素材部分 | **已合入 main，暫存待修訂**；建模前缺 AI 三視圖，依 z1nnz 本輪指示先收入 | 否；高面數、LOD／碰撞待補 | 否；獨立展示未合併 | 否；正式採集 API 未接 |
| 村口告示與三處線索 | Eli-0731／Codex，PR #34 | 已合入 main | Q01 已轉 FBX 擺入統一城鎮 | Q01–Q04 已在入口 PWA 可見 | 入口有本機告示；正式線索存檔未接 |
| 回村八件道具與整理玩法 | Eli-0731／Codex，PR #35 | 已合入 main | C02 已轉 FBX 擺入統一城鎮 | C01–C03 已在入口 PWA 可見，另有獨立整理頁 | 正式背包與委託未接 |
| 溪畔煉製工坊 | joshsu54／Codex，PR #36 | 已合入 main | B01 已轉 FBX 擺入統一城鎮 | B01／B03／B05 已在入口 PWA 可見，另有獨立煉製頁 | 正式服務端煉製與收據未接 |

**統一場景目前包含什麼：** `QingxiWorld.Editor.QingxiWorldBuilder` 在 `apps/game/Assets/QingxiWorld/` 建較大的小鎮和狩獵區；PR #27 的 `YunJing.Editor.QingxiUnifiedWorldBuilder` 加入原創聽風台並建置新的 Windows 試玩版。舊小入口試走仍可單獨生成，沒有被刪掉。TownLayout v004 整包和 31 件新交接模組尚未全部放進統一場景。

**每件交付的接入流程：** 協作者交原件與來源 → PR 檢查並合併 → 匯入標準場景和設定比例／材質／LOD／碰撞 → 放進玩家行走路線 → 如有玩法才連服務端、背包、保存並測重送。只有走到相應步驟，表格才能向右更新。

z1nnz 已說明提供的外來模型取得原作者授權，可在《雲境》改造。改造版仍記原作者、來源與修改者；公開交付時保留可查的授權範圍紀錄。自製新模型沿用先生成、檢視並保存 AI 三視圖的順序。

**2026-10-28 入口接入：** [四件 Unity＋十二件 PWA 的實際範圍、來源及限制](qingxi-collaborator-world-integration.md)。表中的「進 Unity」指生成器可擺出模型，不等於已做正式互動或手機驗收。
