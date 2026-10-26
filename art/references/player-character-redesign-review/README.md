# 男性角色參考：已確認造型方向

使用者指定以男性原三視圖為準，再確認五視圖、A-Pose 與局部圖後授權分段建模。本 PR 只提供獨立男性候選稿供核心組審閱，不取代 main 的 Heroine-01 角色計畫。

## 參考與來源

- `male-three-view.png`：先前由 AI 生成並獲使用者確認的男性原始概念方向。
- `male-five-view-provisional.png`：正、左側、背、右側、45°。
- `male-a-pose-provisional.png`：正背 A-Pose。
- `male-face-hair-provisional.png`：五官與髮型局部；臉部安排最後製作。
- `male-garment-provisional.png`：交領、袖口、腰帶與袍擺。
- `male-accessories-provisional.png`：髮簪、青珠與布帶結。

新圖以原三視圖作為 image_gen 參考，提示詞見 [prompts.md](prompts.md)，檔案雜湊與尺寸見 [image-manifest.json](image-manifest.json)，比例與限制見 [male-review-spec.md](male-review-spec.md)。`provisional` 保留生成時檔名，現已確認為製作方向。

這些是 AI 設計圖，並非模型渲染或真人照片。另一側、背面遮蔽處及接縫為 AI 補充；沒有原始真人影像可證明細節。未加入花朵、耳環與珠鏈。女性概念及 Dondon 既有 Q 版素材不在此 PR 範圍內。

## 製作順序

軀幹胸廓 → 肢體與服裝 → 頭髮配件 → 臉部。遭使用者否決的 v001 整身比例稿未作為本版幾何底稿。
