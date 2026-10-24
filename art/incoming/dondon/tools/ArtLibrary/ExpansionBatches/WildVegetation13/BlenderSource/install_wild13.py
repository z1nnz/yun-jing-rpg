"""Install only verified results: copy batch outputs to the master Models/ and ArtLibrary/Turnarounds,
check byte-identical copies, build contact sheets, overview, batch gallery and catalog entries.
Run after verify_wild13.py with Python + Pillow, e.g.  uv run --with pillow python install_wild13.py
No Blender or Git mutations. Earlier indexes are backed up once to ArtLibrary/History/BeforeWildVegetation13.
"""
from pathlib import Path
import json, shutil, hashlib, html, math
from PIL import Image,ImageDraw,ImageFont
BATCH=Path(__file__).resolve().parents[1];ROOT=BATCH.parents[2];LIB=ROOT/'ArtLibrary'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def font(size):
    for f in ['C:/Windows/Fonts/msjh.ttc','/System/Library/Fonts/STHeiti Medium.ttc','/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']:
        try:return ImageFont.truetype(f,size)
        except OSError:pass
    return ImageFont.load_default()
F=font(24)
report=read(BATCH/'validation.json');assert len(report['assets'])==5
entries=[];inventory=[];cards=[];thumbs=[];ver='v001'
for result in report['assets']:
    aid=result['asset'];bm=BATCH/'Models'/aid/ver;bt=BATCH/'ArtLibrary/Turnarounds'/f'{aid}_{ver}'
    assert sha(bm/f'{aid}_{ver}.blend')==result['blend_sha256'] and sha(bm/f'{aid}_{ver}.fbx')==result['fbx_sha256']
    m=ROOT/'Models'/aid/ver;t=LIB/'Turnarounds'/f'{aid}_{ver}'
    if m.exists() and sha(m/f'{aid}_{ver}.blend')!=result['blend_sha256']:raise SystemExit(f'{m} already holds a different {aid}; not overwriting')
    shutil.copytree(bm,m,dirs_exist_ok=True);shutil.copytree(bt,t,dirs_exist_ok=True)
    for ext in ['blend','fbx']:assert sha(m/f'{aid}_{ver}.{ext}')==sha(bm/f'{aid}_{ver}.{ext}')
    for f in bt.iterdir():assert sha(f)==sha(t/f.name)
    info=read(bm/'model_info.json');views=read(bt/'views.json')['views'];name=info['name_zh']
    sheet=Image.new('RGB',(1500,660),(237,240,233));draw=ImageDraw.Draw(sheet);draw.text((16,8),f'{name} | {aid} {ver}',font=F,fill='#243d34')
    for i,v in enumerate(views):
        im=Image.open(bt/v['file']).convert('RGB');im.thumbnail((290,290));sheet.paste(im,((i%5)*300+5,48+(i//5)*305))
    sheet.save(BATCH/f'{aid}_10views.jpg',quality=91)
    thumbs.append((name,bt/'05_front_right.png'))
    entries.append({'id':aid,'name':name,'category':info['category'],'source_version':ver,'source_path':f'Models/{aid}/{ver}','blend':f'../Models/{aid}/{ver}/{aid}_{ver}.blend','fbx':f'../Models/{aid}/{ver}/{aid}_{ver}.fbx','preview':f'Turnarounds/{aid}_{ver}/05_front_right.png','views':[f'Turnarounds/{aid}_{ver}/'+v['file'] for v in views],'status':'程序化外觀原型；待引擎驗證','unreal_import_verified':False,'uv_baked':False,'collision_ready':False,'lod_ready':False})
    inventory.append({'asset':aid,'name_zh':name,'version':ver,'views':10,'dimensions_m':info['dimensions_m'],'triangles':info['triangles'],'blend_sha256':result['blend_sha256'],'fbx_sha256':result['fbx_sha256']})
    images=''.join(f'<a href="ArtLibrary/Turnarounds/{aid}_{ver}/{v["file"]}"><img loading="lazy" src="ArtLibrary/Turnarounds/{aid}_{ver}/{v["file"]}" alt="{v["file"]}"></a>' for v in views)
    dims=' × '.join(f'{x:.2f}' for x in info['dimensions_m'])
    cards.append(f'<section><h2>{html.escape(name)} <small>{aid}</small></h2><p>{dims} m · {info["triangles"]:,} 三角面 · {info["mesh_objects"]} 分件</p><p><a href="Models/{aid}/{ver}/{aid}_{ver}.blend">Blender</a> · <a href="Models/{aid}/{ver}/{aid}_{ver}.fbx">FBX</a> · <a href="Models/{aid}/{ver}/model_info.json">模型資料</a></p><img class="sheet" src="{aid}_10views.jpg" alt="{html.escape(name)}十視圖"><details><summary>十張原圖</summary><div class="views">{images}</div></details></section>')
cols=3;rows=math.ceil(len(thumbs)/cols);sheet=Image.new('RGB',(1500,rows*535+60),(237,240,233));draw=ImageDraw.Draw(sheet);draw.text((16,15),'野外植被與岩石 13｜普通松・竹叢・野灌木・苔石組・碎石堆',font=F,fill='#243d34')
for i,(name,p) in enumerate(thumbs):
    im=Image.open(p).convert('RGB');im.thumbnail((490,490));x=(i%cols)*500;y=60+(i//cols)*535;sheet.paste(im,(x,y));draw.text((x+12,y+495),name,font=F,fill='#243d34')
sheet.save(BATCH/'overview.jpg',quality=92)
write(BATCH/'inventory.json',{'batch':'WildVegetation13','date':'2026-10-22','asset_type':'wild vegetation and rocks','new_asset_sets':len(entries),'new_views':10*len(entries),'modeling_method':'procedural Python, seeded','assets':inventory})
style='<style>body{margin:0;background:#edf0e9;color:#243d34;font:16px/1.65 system-ui,"Microsoft JhengHei",sans-serif}main{max-width:1200px;margin:auto;padding:30px 16px}section{background:white;padding:24px;border-radius:16px;margin:24px 0}small{color:#6b7f75;font-weight:400}a{color:#366c59}.sheet,.hero{width:100%}.views{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}.views img{width:100%}summary{cursor:pointer}</style>'
page=f'<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>野外植被與岩石 13</title>{style}<main><h1>野外植被與岩石 13</h1><p>補齊清單 D 區的普通松、竹子、灌木與小岩石／碎石。五組皆以 Python 程序化建模（固定亂數種子，可重建），沿用山景 07 的玉灰岩、深綠植被與暖木色。每件 10 張 1024px 原圖，共 50 張。</p><p><a href="README.md">說明</a> · <a href="validation.json">實際驗證結果</a> · <a href="../../index.html">回主圖庫</a></p><p>外觀原型：植被為靜態網格，沒有風動形態鍵；竹葉為單面葉片，引擎需雙面材質。UV 烘焙、碰撞、LOD 與 Unreal 驗證尚未完成。</p><img class="hero" src="overview.jpg" alt="五組總覽">'+''.join(cards)+'</main></html>'
(BATCH/'index.html').write_text(page,encoding='utf-8')
hist=LIB/'History/BeforeWildVegetation13';hist.mkdir(parents=True,exist_ok=True)
for rel in ['asset_catalog.json','index.html','完整建模清單.md']:
    dest=hist/rel
    if not dest.exists():shutil.copy2(LIB/rel,dest)
catalog=read(LIB/'asset_catalog.json');ids={e['id'] for e in entries}
catalog['entries']=[e for e in catalog['entries'] if e['id'] not in ids]+entries
old_sets,old_views=catalog['model_asset_sets'],catalog['consistent_turnaround_images']
catalog['model_asset_sets']=sum(bool(e.get('views')) for e in catalog['entries']);catalog['consistent_turnaround_images']=sum(len(e.get('views',[])) for e in catalog['entries'])
catalog['updated']='2026-10-22';link='ExpansionBatches/WildVegetation13/index.html'
catalog.setdefault('supplemental_batches',[])
if link not in catalog['supplemental_batches']:catalog['supplemental_batches'].append(link)
write(LIB/'asset_catalog.json',catalog)
p=LIB/'index.html';s=p.read_text(encoding='utf-8')
s=s.replace(f'{old_sets} 組素材各有 10 張參考圖，共 {old_views} 張',f'{catalog["model_asset_sets"]} 組素材各有 10 張參考圖，共 {catalog["consistent_turnaround_images"]} 張')
if link not in s:
    s=s.replace('</nav>',f' · <a href="{link}">野外植被 13</a></nav><section><h2>野外植被與岩石 13</h2><p>普通松、竹叢、野灌木、苔石組、碎石堆，共 5 組／50 張十視圖。</p><a href="{link}">開啟批次圖庫</a><img class="hero" src="{link.rsplit("/",1)[0]}/overview.jpg" alt="野外植被與岩石總覽"></section>',1)
p.write_text(s,encoding='utf-8')
print('INSTALLED',len(entries),'assets; catalog',old_sets,'->',catalog['model_asset_sets'],'sets,',old_views,'->',catalog['consistent_turnaround_images'],'views')
