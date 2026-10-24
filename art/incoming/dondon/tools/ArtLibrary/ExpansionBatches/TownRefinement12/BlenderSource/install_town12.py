"""Install only fully verified results; maintain master/batch byte-identical copies.
Run with Python + Pillow after verify_town12.py. No Blender or Git mutations.
"""
from pathlib import Path
import json, shutil, hashlib, html, math
from PIL import Image,ImageDraw,ImageFont
BATCH=Path(__file__).resolve().parents[1];ROOT=BATCH.parents[2]
def read(p):return json.loads(p.read_text())
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
report=read(BATCH/'validation.json');assert len(report['assets'])==18
fontpath='/System/Library/Fonts/STHeiti Medium.ttc'
try:font=ImageFont.truetype(fontpath,24)
except OSError:font=ImageFont.load_default()
entries=[];inventory=[];cards=[];thumbs=[]
for result in report['assets']:
 aid=result['asset'];ver='v002';m=ROOT/'Models'/aid/ver;t=ROOT/'ArtLibrary/Turnarounds'/f'{aid}_{ver}'
 assert sha(m/f'{aid}_{ver}.blend')==result['blend_sha256'] and sha(m/f'{aid}_{ver}.fbx')==result['fbx_sha256']
 bm=BATCH/'Models'/aid/ver;bt=BATCH/'ArtLibrary/Turnarounds'/f'{aid}_{ver}'
 shutil.copytree(m,bm,dirs_exist_ok=True);shutil.copytree(t,bt,dirs_exist_ok=True)
 for ext in ['blend','fbx']:assert sha(m/f'{aid}_{ver}.{ext}')==sha(bm/f'{aid}_{ver}.{ext}')
 info=read(m/'model_info.json');views=read(t/'views.json')['views'];name=info['name_zh']
 sheet=Image.new('RGB',(1500,660),(237,240,233));draw=ImageDraw.Draw(sheet);draw.text((16,8),name+' | v002',font=font,fill='#243d34')
 for i,v in enumerate(views):
  im=Image.open(t/v['file']).convert('RGB');im.thumbnail((290,290));sheet.paste(im,((i%5)*300+5,48+(i//5)*305))
 sheet.save(BATCH/f'{aid}_10views.jpg',quality=91)
 thumbs.append((name,t/'05_front_right.png'))
 new={'id':aid,'name':name,'category':info.get('category','小鎮素材'),'source_version':ver,'source_path':f'Models/{aid}/{ver}','blend':f'../Models/{aid}/{ver}/{aid}_{ver}.blend','fbx':f'../Models/{aid}/{ver}/{aid}_{ver}.fbx','preview':f'Turnarounds/{aid}_{ver}/05_front_right.png','views':[f'Turnarounds/{aid}_{ver}/'+v['file'] for v in views],'status':'沿用宗門畫風的外觀原型；待引擎驗證','unreal_import_verified':False,'uv_baked':False,'collision_ready':False,'lod_ready':False}
 entries.append(new);inventory.append({'asset':aid,'name_zh':name,'version':ver,'views':10,'style_reference':'SectCore04','blend_sha256':result['blend_sha256'],'fbx_sha256':result['fbx_sha256']})
 images=''.join(f'<a href="ArtLibrary/Turnarounds/{aid}_{ver}/{v["file"]}"><img loading="lazy" src="ArtLibrary/Turnarounds/{aid}_{ver}/{v["file"]}" alt="{v["file"]}"></a>' for v in views)
 cards.append(f'<section><h2>{html.escape(name)}</h2><p><a href="Models/{aid}/{ver}/{aid}_{ver}.blend">Blender</a> · <a href="Models/{aid}/{ver}/{aid}_{ver}.fbx">FBX</a> · <a href="Models/{aid}/{ver}/model_info.json">模型資料</a></p><img class="sheet" src="{aid}_10views.jpg" alt="{html.escape(name)}十視圖"><details><summary>十張原圖</summary><div class="views">{images}</div></details></section>')
rows=math.ceil(len(thumbs)/3);sheet=Image.new('RGB',(1500,rows*535+60),(237,240,233));draw=ImageDraw.Draw(sheet);draw.text((16,15),'小鎮畫風修整 12｜青綠瓦・暖木・淺石・淡玉',font=font,fill='#243d34')
for i,(name,p) in enumerate(thumbs):
 im=Image.open(p).convert('RGB');im.thumbnail((490,490));x=(i%3)*500;y=60+(i//3)*535;sheet.paste(im,(x,y));draw.text((x+12,y+495),name,font=font,fill='#243d34')
sheet.save(BATCH/'overview.jpg',quality=92)
# Scene gets its own ten views; these never inflate the independent asset count.
sm=ROOT/'Models/TownLayout/v004';st=ROOT/'ArtLibrary/Turnarounds/TownLayout_v004'
shutil.copytree(sm,BATCH/'Models/TownLayout/v004',dirs_exist_ok=True);shutil.copytree(st,BATCH/'ArtLibrary/Turnarounds/TownLayout_v004',dirs_exist_ok=True)
write(BATCH/'inventory.json',{'batch':'TownRefinement12','date':'2026-10-18','source_commit':'70d3fa4d261bd9bbd7cc0cd7180ca08c6a7ba7cc','assets':inventory,'independent_asset_views':180,'scene':'TownLayout/v004','additional_scene_views':10})
style='<style>body{margin:0;background:#edf0e9;color:#243d34;font:16px/1.65 system-ui}main{max-width:1200px;margin:auto;padding:30px}section{background:white;padding:24px;border-radius:16px;margin:24px 0}a{color:#366c59}.sheet{width:100%}.views{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}.views img{width:100%}summary{cursor:pointer}</style>'
sceneviews=''.join(f'<a href="ArtLibrary/Turnarounds/TownLayout_v004/{v["file"]}"><img loading="lazy" src="ArtLibrary/Turnarounds/TownLayout_v004/{v["file"]}" alt="{v["file"]}"></a>' for v in read(st/'views.json')['views'])
page=f'<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>小鎮畫風修整 12</title>{style}<main><h1>小鎮畫風修整 12</h1><p>依既有宗門畫風修整 Claude 小鎮使用的 18 項素材：暖木、青綠瓦、淺灰石與淡玉色。每件有 10 張 1024px 原圖，共 180 張；小鎮另有 10 張場景視圖及 4 張近景／總覽。</p><p><a href="README.md">修改說明</a> · <a href="validation.json">實際驗證結果</a> · <a href="../../index.html">回主圖庫</a></p><p>保留來源版本；目前為外觀原型，尚未完成 UV 烘焙、碰撞、LOD、導航與 Unreal 驗證。</p><section><h2>小鎮 v004</h2><p>牌樓入口加寬、庭院東移避開道路、角柱對齊、重複欄柱移除，以及門前鋪面銜接。</p><p><a href="Models/TownLayout/v004/TownLayout_v004.blend">Blender 場景</a> · <a href="Models/TownLayout/v004/TownLayout_v004.fbx">FBX</a></p><img class="sheet" src="Models/TownLayout/v004/01_town_overview.png" alt="小鎮總覽"><details><summary>場景十視圖</summary><div class="views">{sceneviews}</div></details></section>'+''.join(cards)+'</main></html>'
(BATCH/'index.html').write_text(page,encoding='utf-8')
# Backup prior indexes once, preserving user history on reruns.
hist=ROOT/'History/BeforeTownRefinement12';hist.mkdir(parents=True,exist_ok=True)
for rel in ['ArtLibrary/asset_catalog.json','ArtLibrary/index.html','ArtLibrary/完整建模清單.md','HANDOFF.md']:
 dest=hist/rel;dest.parent.mkdir(parents=True,exist_ok=True)
 if not dest.exists():shutil.copy2(ROOT/rel,dest)
catalog=read(ROOT/'ArtLibrary/asset_catalog.json');ids={e['id'] for e in entries}
catalog['entries']=[e for e in catalog['entries'] if e['id'] not in ids]+entries
for e in catalog['entries']:
 if e['id']=='TownLayout':e.update(name='小鎮配置｜沿用宗門畫風',source_version='v004',source_path='Models/TownLayout/v004',blend='../Models/TownLayout/v004/TownLayout_v004.blend',fbx='../Models/TownLayout/v004/TownLayout_v004.fbx',preview='../Models/TownLayout/v004/01_town_overview.png',views=[],scene_views=[f'Turnarounds/TownLayout_v004/{v["file"]}' for v in read(st/'views.json')['views']])
# Count only independent ten-view entries, preserving the existing scene classification.
catalog['model_asset_sets']=sum(bool(e.get('views')) for e in catalog['entries']);catalog['consistent_turnaround_images']=sum(len(e.get('views',[])) for e in catalog['entries'])
catalog['updated']='2026-10-18';link='ExpansionBatches/TownRefinement12/index.html'
if link not in catalog['supplemental_batches']:catalog['supplemental_batches'].append(link)
catalog['town_refinement_note']='18 Claude town assets restyled to SectCore04; TownLayout v004 has 10 additional scene views excluded from independent asset total. Other Claude branch assets remain outside this local catalog.'
write(ROOT/'ArtLibrary/asset_catalog.json',catalog)
p=ROOT/'ArtLibrary/index.html';s=p.read_text()
s=s.replace('66 組素材各有 10 張參考圖，共 660 張','84 組素材各有 10 張參考圖，共 840 張').replace('另有小鎮與宗門兩組配置場景','另有小鎮、宗門與山景三組配置場景')
if 'TownRefinement12/index.html' not in s:
 s=s.replace('</nav>',' · <a href="ExpansionBatches/TownRefinement12/index.html">小鎮畫風修整 12</a></nav><section><h2>最新小鎮畫風修整</h2><p>18 項素材沿用宗門畫風；180 張素材圖，另有小鎮 v004 場景。舊版配置仍保留於下方。</p><a href="ExpansionBatches/TownRefinement12/index.html">開啟新版完整圖庫</a><img class="hero" src="../Models/TownLayout/v004/03_north_street_archway.png" alt="新版小鎮牌樓"></section>',1)
p.write_text(s,encoding='utf-8')
print('INSTALLED',len(entries),'assets; catalog',catalog['model_asset_sets'],catalog['consistent_turnaround_images'])
