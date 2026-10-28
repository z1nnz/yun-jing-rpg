# 青溪古水路修復：服務端接線說明（草案）

本機原型（`tools/qingxi-waterworks-b/`）只用**展示材料**，不讀寫正式背包、帳本或貢獻。本文件寫給核心組：之後要把「完成導水方案」接到服務端時，請求和收據該長什麼樣，以及重送時怎樣保證不重複扣料、不重複加貢獻。

**本包沒有改任何現有 API、帳本或 `packages/content`。** 下面的端點與欄位都是提案，名稱由核心組決定。

## 1. 名詞

| 欄位 | 意思 | 本機原型的值 |
|---|---|---|
| `projectId` | 公共工程 ID：同一段公共水路是同一個工程，多人可各自貢獻 | `qingxi-waterworks-b:public-channel` |
| `attempt` | 同一玩家對這個工程的第幾次方案（按「重試」加一） | `1, 2, …` |
| `requestId` | 一次「完成」請求的唯一 ID。**由客戶端在進入確認畫面時產生，重送沿用同一個** | `ww-<sessionId>-a<attempt>` |
| `role` | 玩家在工程中的角色 | `waterworks_builder` |
| `direction` | 處理方向 | `clear_silt` / `restore_channel` / `protect_nursery` |
| `outcomeId` | 結果 ID，給 C 組回村展示讀取 | `silt_cleared_temporary_diversion` / `channel_restored_direct` / `nursery_protected_detour` |
| `observationIds` | 玩家帶來的 A 組線索 | `cracked_sluice` / `silt_buildup` / `nursery_tracks` 的子集 |

## 2. 請求（提案）

```http
POST /v1/projects/{projectId}/contributions
Idempotency-Key: {requestId}
```

```json
{
  "requestId": "ww-3f2a…-a1",
  "projectId": "qingxi-waterworks-b:public-channel",
  "attempt": 1,
  "role": "waterworks_builder",
  "direction": "restore_channel",
  "observationIds": ["cracked_sluice", "silt_buildup", "nursery_tracks"],
  "plan": [
    { "seg": "S01", "cell": "3,1", "type": "worn", "model": "B02-V02_WornStraight", "rot": 0 },
    { "seg": "S05", "cell": "3,5", "type": "apron", "model": "B02-V05_SpillApron", "rot": 0 }
  ],
  "materialBatches": [
    { "batchId": "<server batch id>", "item": "<server item id>", "qty": 7 }
  ]
}
```

- `plan` 只送擺法，不送結果。**水量、供水、育幼區影響由服務端用同一套規則重算**（規則在 `src/waterworks-core.mjs`，純函式、無亂數、無時鐘，可直接移植或當參考實作），客戶端算的數字只作預覽。
- `materialBatches` 指定要扣哪幾批材料。服務端以自己的庫存為準：批次不存在、數量不足或已綁定時拒絕，**不部分扣料**。
- 本機原型的材料（石料、杉木、銅箍、補石、清淤篩）是展示用名稱，沒有對應的正式物品 ID，對照表留給核心組指定。

## 3. 收據（提案）

```json
{
  "requestId": "ww-3f2a…-a1",
  "projectId": "qingxi-waterworks-b:public-channel",
  "attempt": 1,
  "outcomeId": "channel_restored_direct",
  "result": { "fieldsFlow": 68.6, "fieldsSupplyPct": 86, "creekFlow": 0, "nursery": "受驚擾", "leaks": [] },
  "materials": { "spent": [{ "batchId": "…", "qty": 7 }] },
  "contribution": { "role": "waterworks_builder", "points": 5 },
  "ledgerEntryIds": ["…"],
  "replay": false
}
```

## 4. 重送與冪等

1. 服務端以 `(playerId, projectId, requestId)` 為唯一鍵，在**同一個交易**裡：寫入收據、扣材料、加貢獻。
2. 同一 `requestId` 再送（網路逾時重送、玩家連按「完成」）：不再扣料、不再加貢獻，直接回傳第一次的收據，`replay: true`。
3. 同一 `requestId` 但內容不同（`plan` 或 `materialBatches` 被改過）：回 `409 Conflict`，不覆寫第一次的結果。
4. 玩家按「重試」：客戶端把 `attempt` 加一並產生新的 `requestId`。是否允許同一工程多次計入貢獻、間隔多久，由核心組決定。
5. 失敗（規則不通過、材料不足）不寫入收據，同一 `requestId` 可以修正後再送。

本機原型照第 1、2 點實作：`finish(state, requestId)` 對已存在的 `requestId` 回傳同一張收據且不再扣展示材料，見 `tests/waterworks-core.test.mjs`「pressing finish twice…」。

## 5. 不在本包範圍

- 正式材料 ID 對照、貢獻點數換算、跨場景狀態（A → B → C）與多人同時修同一工程的合併規則。
- 寫入正式世界狀態（例如水路在共同世界中變成已修好）。原型只改本機畫面。
