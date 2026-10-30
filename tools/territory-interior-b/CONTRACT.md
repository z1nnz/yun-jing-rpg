# 新手領地屋內：收藏架的伺服器接線說明（提案）

狀態：**提案，尚未接線**。本工作包沒有修改 `services/api`、`packages/contracts`、`packages/content`、主場景或 HUD。屋內展示（`tools/territory-interior-b/`，Unity）裡的物品、丹藥品階只存在本場景記憶體，畫面標示「展示試玩（物品只在本場景，不入正式存檔）」，不入正式乾坤袋。正式的物品、修為、世界狀態由伺服器決定，核心組來接。

## 1. 原則

- **以伺服器結果為準。** 前端只上傳「哪一格、放哪一件（伺服器庫存裡的那一筆）」，不上傳數量、品階或結果。
- **沿用現有的 `POST /v1/actions`** 與 `Game.act()` 的收據機制，不另開 API：
  - 同一個 `requestId` 加同一個內容，回傳原收據（重送不重複）。
  - 同一個 `requestId` 但內容不同，回 `409 IDEMPOTENCY_CONFLICT`。
- **擺上架不是消耗。** 收藏品仍屬於玩家，只是位置從乾坤袋移到架上；帳本記「移動」，不記「扣除」。
- **規則是決定性的。** 不用亂數、不讀時鐘。

## 2. 收藏架格位

- 收藏架 TI01 共 8 格，編號 `1`–`8`，對應模型的放置點 `SOCKET_slot_1`–`_8`（見 `art/exports/territory-interior-b/TI01_BoguShelf/model_info.json`）。
- 每格放得下收藏尺寸 0.35 × 0.3 × 0.35 m 的見聞道具；一格只放一件。

## 3. 操作

### 3.1 `place-collectible`（放上架，或換格）

```jsonc
POST /v1/actions
{
  "requestId": "tib-…-uuid",            // 每次放置一個；網路重試沿用同一個
  "action": {
    "kind": "place-collectible",
    "slot": 3,                          // 1–8
    "stackId": "<伺服器庫存那一筆>"       // 不是物品名稱，也不是數量
  }
}
```

伺服器依序檢查：

1. **收據先查。** 已有 `(actor_id, requestId)`：內容相同回原收據（`replayed: true`），不同回 `409`。這一步在任何移動之前。
2. `slot` 不在 1–8：`400 BAD_SLOT`。
3. `stackId` 不屬於此角色，或不是收藏類物品：`400 NOT_OWNED`。只能放乾坤袋裡真的有的東西。
4. 這件已經在**另一格**：視為「換格」，先清空舊格再放新格，同一交易內完成；**同一件不能同時在兩格**。
5. 目標格已有別件：`409 SLOT_TAKEN`（前端先拿下再放，避免互換時誤覆蓋）。
6. 寫入 `territory.shelf[slot] = stackId`，乾坤袋該筆標記為「在架上」；寫 `ledger`（kind: `move`）與 `receipts`，回傳 Snapshot。

### 3.2 `take-collectible`（拿下架，回乾坤袋）

```jsonc
{ "requestId": "tib-…", "action": { "kind": "take-collectible", "slot": 3 } }
```

1. 收據先查（同上）。
2. 該格是空的：`400 SLOT_EMPTY`。
3. 清空該格，物品回乾坤袋。乾坤袋已滿時回 `409 BAG_FULL`，**不清空架子**（物品不會消失，也不會複製）。

回應附上整個收藏架：

```jsonc
{ "…Snapshot": "…", "shelf": { "1": null, "2": "<stackId>", "3": "<stackId>", "…": null, "8": null }, "replayed": false }
```

## 4. 重送與邊界

| 情境 | 伺服器行為 |
|---|---|
| 逾時後重送同一個 `requestId` | 回原收據；架子與乾坤袋不再變動 |
| 同一件連放兩格 | 第二次視為換格，舊格清空；任何時候一件只在一格 |
| 拿下再放回 | 物品數量不變，不複製 |
| 乾坤袋滿時拿下 | `409 BAG_FULL`，物品留在架上 |
| 兩台裝置同時操作 | 依 `players.version` 樂觀鎖；收據表保證同一請求只成立一筆 |

## 5. 燈、丹爐、手札

- **燈（熄／亮）**：純畫面狀態，跟晝夜系統走；不建議上伺服器。
- **小丹爐（冷／燒）**：展示裡沿用煉丹玩法 V2 的常數與評分（`Assets/Scripts/Logic/HomeAlchemy.cs`）。若要接正式煉丹，由伺服器照 V2 規則重算，展示裡的品階不採用。
- **旅途手札**：內容來源由核心組決定（見聞、主線紀錄）。

## 6. 等核心組決定或接線的項目

| # | 項目 | 目前狀態 |
|---|---|---|
| 1 | 收藏品的 item 類別 | 展示用示意道具（TI08 盒、卷軸、小罐）；正式見聞道具由 C 做 |
| 2 | `territory.shelf` 存放位置 | 建議放玩家個人存檔，非 `world` 共用 |
| 3 | 收藏架擺放的 Unity 互動 | 展示已實作，規則在 `Assets/Scripts/Logic/Shelf.cs`，測試在 `Assets/Tests/EditMode/ShelfTests.cs` |
| 4 | 文字放 `packages/content/*.json` | 展示文字目前寫在程式裡，待搬 |
