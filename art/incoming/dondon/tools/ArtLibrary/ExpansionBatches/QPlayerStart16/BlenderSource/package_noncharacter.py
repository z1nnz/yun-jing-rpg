"""Install validated non-character artifacts, build gallery, and update catalog once.
Run with standard Python (UTF-8). Never copies or registers paused character assets.
"""
import json,hashlib,shutil,html,re
from pathlib import Path
BATCH=Path(__file__).resolve().parents[1];ROOT=BATCH.parents[2]
report=json.loads((BATCH/'noncharacter_validation.json').read_text(encoding='utf-8'))
assert report['active_asset_count']==10
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy_checked(src,dst):
    dst.parent.mkdir(parents=True,exist_ok=True)
    if dst.exists():assert sha(src)==sha(dst),'Refusing overwrite: '+str(dst)
    else:shutil.copy2(src,dst)
    assert sha(src)==sha(dst)

cards=[];installed=[];entries=[]
for row in report['assets']:
    aid=row['asset'];v=row['version'];name=row['name_zh']
    assert aid not in {'QMaleBase','QFemaleBase','QTopknotHair','QDoubleBunHair','QMaleNoviceOutfit','QFemaleNoviceOutfit'}
    out=BATCH/'Models'/aid/v;ref=BATCH/'ArtLibrary/Turnarounds'/f'{aid}_{v}'
    for f in out.iterdir():
        if f.is_file():copy_checked(f,ROOT/'Models'/aid/v/f.name)
    for f in ref.iterdir():
        if f.is_file():copy_checked(f,ROOT/'ArtLibrary/Turnarounds'/f'{aid}_{v}'/f.name)
    manifest=json.loads((ref/'views.json').read_text());files=[x['file'] for x in manifest['views']]
    dims=' × '.join(f'{x:.2f}' for x in row['dimensions_m'])+' m'
    views=''.join(f'<a href="ArtLibrary/Turnarounds/{aid}_{v}/{f}"><img loading="lazy" src="ArtLibrary/Turnarounds/{aid}_{v}/{f}" alt="{html.escape(name)} {f[:2]} 視角"></a>' for f in files)
    anim=f'<a href="Models/{aid}/{v}/{aid}_open_close_v002.fbx">開合動畫 FBX</a>' if aid=='QCaveDoor' else ''
    cards.append(f'''<article id="{aid}"><a href="ArtLibrary/Turnarounds/{aid}_{v}/05_front_right.png"><img class="asset" loading="lazy" src="ArtLibrary/Turnarounds/{aid}_{v}/05_front_right.png" alt="{name}"></a><div class="body"><small>{aid} · {v}</small><h2>{name}</h2><p>{dims}</p><nav><a href="Models/{aid}/{v}/{aid}_{v}.blend">Blender 原檔</a><a href="Models/{aid}/{v}/{aid}_{v}.fbx">FBX</a>{anim}</nav><details><summary>展開同模型十視圖</summary><div class="views">{views}</div></details></div></article>''')
    category='Q版獵物' if aid in ('QMountainRabbit','QMountainBoar') else '洞府模組' if aid.startswith('QCave') else '修煉道具'
    entries.append({'id':aid,'name':name,'category':category,'source_version':v,'source_path':f'Models/{aid}/{v}',
      'blend':f'../Models/{aid}/{v}/{aid}_{v}.blend','fbx':f'../Models/{aid}/{v}/{aid}_{v}.fbx',
      'preview':f'Turnarounds/{aid}_{v}/05_front_right.png','views':[f'Turnarounds/{aid}_{v}/{f}' for f in files],
      'status':'可編輯非人物外觀原型；UV、碰撞、LOD 與 UE 驗證待做','unreal_import_verified':False,'uv_baked':False,'collision_ready':False,'lod_ready':False})
    installed.append({'asset':aid,'version':v,'blend_sha256':row['blend_sha256'],'fbx_sha256':row['fbx_sha256'],'installed_hashes_match':True})

scene_src=BATCH/'Scenes/QCaveResidence/v002'
for f in scene_src.iterdir():
    if f.is_file():copy_checked(f,ROOT/'Models/QCaveResidence/v002'/f.name)
scene_views=''.join(f'<a href="Previews/CaveResidence_v002/{r["file"]}"><img loading="lazy" src="Previews/CaveResidence_v002/{r["file"]}" alt="洞府配置 {i+1}"></a>' for i,r in enumerate(json.loads((BATCH/'Previews/CaveResidence_v002/views.json').read_text())['views']))
page='''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>洞府與修煉生活｜非人物模型第一批</title><style>
*{box-sizing:border-box}body{margin:0;background:#f3f0e7;color:#253a32;font:16px/1.7 system-ui,"Microsoft JhengHei",sans-serif}main{max-width:1320px;margin:auto;padding:48px 28px}header{max-width:920px;margin-bottom:34px}.eyebrow{letter-spacing:.18em;color:#708274;font-size:13px}h1{font-size:clamp(32px,4vw,52px);line-height:1.25;margin:12px 0}h2{font-size:24px;margin:4px 0}p{margin:10px 0;color:#5b6b60}.stats{display:flex;gap:34px;margin:25px 0}.stats b{font-size:32px;display:block;line-height:1.1}.hero{display:grid;grid-template-columns:1.5fr 1fr;gap:32px;align-items:center;background:#e7e8dc;padding:22px;border-radius:20px;margin-bottom:28px}.hero img{width:100%;border-radius:12px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:22px}article{background:#fffdf6;border:1px solid #d9ded1;border-radius:16px;overflow:hidden}.asset{display:block;width:100%;aspect-ratio:1;object-fit:contain}.body{padding:20px}small{font-size:11px;letter-spacing:.03em;color:#768277}nav{display:flex;flex-wrap:wrap;gap:10px;margin-top:15px}a{color:#2c6550;text-underline-offset:4px}nav a{border:1px solid #c9d6c7;padding:5px 10px;border-radius:8px;text-decoration:none;font-size:13px}.views{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:14px 0}.views img{width:100%;border-radius:6px}details{margin-top:18px}summary{cursor:pointer;color:#32634e}footer{padding:40px 0 8px;font-size:14px} @media(max-width:900px){.grid{grid-template-columns:repeat(2,1fr)}.hero{grid-template-columns:1fr}}@media(max-width:560px){main{padding:24px 16px}.grid{grid-template-columns:1fr}.stats{gap:20px}}
</style><main><header><div class="eyebrow">修仙生活 · ART PROTOTYPES · 2026.10.24</div><h1>洞府、獵物與修煉物品</h1><p>第一批非人物模型。淡玉、暖木與淺石色調，先完成可編輯外觀與配置，再接入遊戲。</p><div class="stats"><span><b>10</b>獨立模型</span><span><b>100</b>模型十視圖</span><span><b>1</b>洞府配置</span></div><p>人物、髮型與服裝已停工，本頁不包含人物成果。</p></header><section class="hero"><a href="Previews/CaveResidence_v002/05_front_right.png"><img src="Previews/CaveResidence_v002/05_front_right.png" alt="洞府與靈田配置初模"></a><div><div class="eyebrow">CAVE RESIDENCE / CUTAWAY</div><h2>居住、收納、修煉與靈田</h2><p>使用新洞府模組，搭配既有床、箱、工作台、丹爐、蒲團與靈藥圃。為方便查看內部，側牆降低並省略洞頂。</p><nav><a href="Scenes/QCaveResidence/v002/QCaveResidence_v002.blend">開啟配置原檔</a><a href="Scenes/QCaveResidence/v002/QCaveResidence_v002.fbx">配置 FBX</a></nav><details><summary>查看 10 張配置預覽</summary><div class="views">'''+scene_views+'''</div></details><p>配置預覽另計，不抵充獨立模型十視圖。</p></div></section><section class="grid">'''+''.join(cards)+'''</section><footer><p><a href="README.md">交付說明</a> · <a href="noncharacter_validation.json">驗證紀錄</a> · <a href="noncharacter_inventory.json">素材清單</a></p><p>Blender 重開、FBX 尺寸與圖片檢查已通過。獵物尚無骨架動畫；UV、碰撞、LOD、導航與 Unreal 整合仍待製作。洞府門具有 Blender 開合預覽與動畫 FBX，尚未接入遊戲互動。</p></footer></main></html>'''
(BATCH/'index.html').write_text(page,encoding='utf-8')
inventory={'batch':'QPlayerStart16_noncharacter','date':'2026-10-24','active_assets':installed,'model_count':10,'same_model_images':100,'door_extra_pose_images':1,'scene_preview_images':10,'new_ai_concept_images_this_batch':0,'paused_character_assets_excluded':True,'validation':'noncharacter_validation.json'}
(BATCH/'noncharacter_inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding='utf-8')

# Register only the selected current non-character versions. Back up the prior index first.
context=BATCH/'Context';context.mkdir(exist_ok=True)
catpath=ROOT/'ArtLibrary/asset_catalog.json';indexpath=ROOT/'ArtLibrary/index.html'
for src in (catpath,indexpath):
    dst=context/('before_noncharacter_'+src.name)
    if not dst.exists():shutil.copy2(src,dst)
cat=json.loads(catpath.read_text(encoding='utf-8'));existing={e['id'] for e in cat['entries']};added=[]
for e in entries:
    if e['id'] not in existing:cat['entries'].append(e);added.append(e)
    else:assert next(x for x in cat['entries'] if x['id']==e['id'])['source_version']==e['source_version']
cat['model_asset_sets']+=len(added);cat['consistent_turnaround_images']+=10*len(added)
if 'QCaveResidence' not in existing:
    cat['entries'].append({'id':'QCaveResidence','name':'私人洞府與靈田配置初模','category':'場景組合','source_version':'v002','source_path':'Models/QCaveResidence/v002','blend':'../Models/QCaveResidence/v002/QCaveResidence_v002.blend','fbx':'../Models/QCaveResidence/v002/QCaveResidence_v002.fbx','preview':'ExpansionBatches/QPlayerStart16/Previews/CaveResidence_v002/05_front_right.png','views':[],'status':'非人物剖面配置預覽；非完整可玩關卡','unreal_import_verified':False})
    cat['assembled_scenes']+=1
batchlink='ExpansionBatches/QPlayerStart16/index.html'
if batchlink not in cat['supplemental_batches']:cat['supplemental_batches'].append(batchlink)
cat['updated']='2026-10-24';cat['qplayer_noncharacter_note']='Added ten non-character prototypes only; six paused human base/hair/outfit prototypes are NOT registered. LingyunValley15 separate camp assets remain outside catalog totals.'
catpath.write_text(json.dumps(cat,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
index=indexpath.read_text(encoding='utf-8')
if batchlink not in index:
    snippet='<section><h2>洞府與修煉生活：非人物模型第一批</h2><p>10 組可編輯模型、100 張十視圖與洞府配置預覽；人物部分已停工。</p><a href="'+batchlink+'">瀏覽本批圖庫與模型</a><img class="hero" src="ExpansionBatches/QPlayerStart16/Previews/CaveResidence_v002/05_front_right.png" alt="洞府配置"></section>'
    assert '<main>' in index;index=index.replace('<main>','<main>'+snippet,1);indexpath.write_text(index,encoding='utf-8')
print(json.dumps({'installed_models':len(installed),'catalog_added':len(added),'catalog_model_sets':cat['model_asset_sets'],'catalog_views':cat['consistent_turnaround_images']},ensure_ascii=False))
