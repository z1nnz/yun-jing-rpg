"""Build a local offline image/model index, without editing generated images."""
from pathlib import Path
import json,html
ROOT=Path(__file__).resolve().parents[1]
names=['聚落出口','過渡山道','採藥林','山兔草坡','溪流淺灘','回村捷徑']
models=[('LowGrass','低矮草叢','1,212 / 552 / 248'),('TrampledGrass','倒伏草叢','2,452 / 1,116 / 492'),('StreamBank','淺灘接岸','736 / 464 / 288')]
def imagecard(path,label,extra=''):
 p=path.as_posix();return f'<article><a href="{p}" target="_blank"><img loading="lazy" src="{p}" alt="{html.escape(label)}"></a><div class="caption"><h3>{label}</h3>{extra}</div></article>'
parts=['''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>青溪 · 狩獵區美術補件</title>
<style>*{box-sizing:border-box}body{margin:0;background:#101d1b;color:#ecf0e6;font:16px/1.7 system-ui,"Microsoft JhengHei",sans-serif}header,main,footer{max-width:1280px;margin:auto;padding:32px}header{padding-top:60px}small{color:#b5ceae;letter-spacing:.18em}h1{font-size:42px;line-height:1.2;margin:14px 0}h2{margin:48px 0 16px;font-size:25px}p{color:#b8c5bd}a{color:#d7dba3;text-decoration:none}nav{display:flex;gap:24px;flex-wrap:wrap;margin-top:24px}.stats{display:flex;gap:40px;border-top:1px solid #34453c;border-bottom:1px solid #34453c;padding:24px 0;margin-top:28px}.stats b{font-size:30px;color:#e0d6a8}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px}.concepts{grid-template-columns:repeat(2,minmax(0,1fr))}article{background:#1a2a25;border:1px solid #35483e;border-radius:12px;overflow:hidden}img{display:block;width:100%;height:270px;object-fit:contain;background:#d9ddd2}.concepts img{height:320px;object-fit:cover}.caption{padding:14px 20px}h3{margin:0 0 8px;font-size:18px}.caption p{margin:0;font-size:14px}.links{display:flex;gap:15px;margin-top:12px}.badge{display:inline-block;color:#cfe5b9;background:#2b4334;padding:6px 14px;border-radius:30px;font-size:14px}.note{padding:18px 22px;border-left:3px solid #c4bf7c;background:#203029}footer{color:#9aafa4;font-size:14px}@media(max-width:800px){.grid,.concepts{grid-template-columns:1fr}h1{font-size:32px}.stats{gap:20px;flex-wrap:wrap}header,main{padding:22px}}</style>
<header><small>YUN JING / QINGXI · ASSET STUDY 01</small><h1>青溪狩獵區<br>圖稿與環境模型</h1><p>六區視覺方向、建模前參考與第一版可編輯模型。2026.10.25</p><span class="badge">Blender 幾何與 FBX 回匯已驗證</span><div class="stats"><div><b>12</b> 張 AI 圖</div><div><b>3</b> 套模型</div><div><b>3</b> 級 LOD／套</div><div><b>10</b> 個 FBX 回匯</div></div><nav><a href="#models">環境模型</a><a href="#concepts">區域概念</a><a href="#references">三視圖</a><a href="#textures">透明貼圖</a><a href="README.md">交接說明</a></nav></header><main><div class="note">Unity 匯入、導航與手機效能仍待測。以下概念圖是 AI 設計參考；模型預覽來自 Blender，皆非 Unity 實機截圖。</div><h2 id="models">01 / 環境模型</h2><div class="grid">''']
for stem,label,tris in models:
 extra=f'<p>LOD0 / 1 / 2：{tris} 三角面<br>單一共用材質 · 可編輯原檔</p><div class="links"><a href="models/{stem}.blend">Blender</a><a href="models/SM_{stem}_LOD0.fbx">FBX</a><a href="models/SM_{stem}_LOD0.glb">GLB</a><a href="previews/{stem}_wire.png">線框</a></div>'
 parts.append(imagecard(Path('previews')/f'{stem}_beauty.png',label,extra))
parts.append('</div><h2 id="concepts">02 / 六區概念圖</h2><div class="grid concepts">')
for p,name in zip(sorted((ROOT/'concepts').glob('*.png')),names):parts.append(imagecard(p.relative_to(ROOT),name))
parts.append('</div><h2 id="references">03 / 建模前 AI 三視圖</h2><div class="grid">')
for p,(_,label,_) in zip(sorted((ROOT/'references').glob('*.png')),models):parts.append(imagecard(p.relative_to(ROOT),label))
parts.append('</div><h2 id="textures">04 / 遊戲用透明貼圖</h2><div class="grid">')
for p,label in zip(sorted((ROOT/'textures').glob('T0[123]*.png')),['兔腳印圖集','泥土擾動圖集','草葉圖集']):parts.append(imagecard(p.relative_to(ROOT),label,'<p>原始 RGBA PNG · 保留透明度</p>'))
parts.append('</div><h2>驗證與限制</h2><p>模型採色盤 UV 共用，重疊為刻意設計；烘焙光照需另做 UV2。低草叢有一對內部接觸面提醒，詳見交接說明。無人物新作、無山兔修改。</p><nav><a href="reports/model-manifest.json">模型 QA</a><a href="reports/export-verification.json">匯出檢查</a><a href="reports/image-verification.json">圖片檢查</a><a href="prompts.json">生成提示詞</a></nav></main><footer>來源與製作紀錄完整保留。圖稿用來定視覺方向，地圖配置以版本化座標為準。</footer></html>')
(ROOT/'index.html').write_text(''.join(parts),encoding='utf-8')
print(ROOT/'index.html')
