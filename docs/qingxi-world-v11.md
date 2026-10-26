# 青溪 v11：樹伴原樹葉冠移植

樹伴 Unity 實景的來源是 z1nnz 的生命樹庭園。先前 v10 將三個合併網格旋轉 90 度，再複製兩組葉片補右側；這改變了鏡頭中的葉冠剪影，也失去原檔的物件階層。v11 已取消這套做法。

目前可直接比較[樹伴 Unity 實景](../art/references/elder-world-tree-faithful-v11/tree-companion-unity-capture.png)及[青溪 Blender 畫面](../art/previews/qingxi-world-v11/original-tree-in-world.png)。青溪場景取用[原版母稿副本](../art/source/elder-world-tree-garden-original.blend)，保留原樹 96 個物件、16 組葉冠、枝條及根系，不旋轉或複製葉片，只將整體移到青溪位置並使主幹進入地面。[可編輯的材質對照稿](../art/source/elder-world-tree-faithful-v11.blend)保留樹伴樹皮與浮島貼圖，葉片使用原「葉色」頂點色；Blender 對樹伴 Unity 葉片著色的近似不代表兩邊畫面完全一致。

重建：

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' -b art/source/elder-world-tree-garden-original.blend --python-exit-code 1 --python tools/art/restore_elder_tree_v11.py
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' -b art/source/qingxi-world-detailed-v9.blend --python-exit-code 1 --python tools/art/integrate_elder_tree_v11.py
```

這只驗證模型資料與 Blender 畫面。Unity 編譯、原本的風動葉片材質、碰撞、手機 LOD 與效能仍待測試。樹皮細節可與樹伴不同；後續優先保持葉片和樹冠輪廓一致。
