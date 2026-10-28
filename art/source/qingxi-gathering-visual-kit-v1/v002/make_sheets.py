"""Three-view sheets with sizes + the gallery page, from render_views.py output (no Blender needed).
uv run --no-project --with pillow python make_sheets.py
Writes references/.../threeview_semireal_v002/<key>_threeview.png and previews/.../index.html.
"""
import json,html
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
REPO=Path(__file__).resolve().parents[4];ART=REPO/'art'
VIEWS=ART/'references/qingxi-gathering-visual-kit-v1/views_v002';SHEETS=ART/'references/qingxi-gathering-visual-kit-v1/threeview_semireal_v002'
EXP=ART/'exports/qingxi-gathering-visual-kit-v1';GAL=ART/'previews/qingxi-gathering-visual-kit-v1'
ORDER=['QX_GatheringLandmark','QX_SpiritHerb_Qinglan_pre','QX_SpiritHerb_Qinglan_post','QX_SpiritHerb_Chilu_pre','QX_SpiritHerb_Chilu_post',
       'QX_EmbeddedOre_Yumai_pre','QX_EmbeddedOre_Yumai_post','QX_CreekSteppingPlank','QX_WaterReeds']
def font(sz):
    for f in ('C:/Windows/Fonts/msjh.ttc','C:/Windows/Fonts/msyh.ttc','/System/Library/Fonts/PingFang.ttc'):
        try:return ImageFont.truetype(f,sz)
        except OSError:pass
    return ImageFont.load_default()
F,FS,FB=font(22),font(17),font(30)
INK=(30,34,32);DIM=(190,60,40)

def dim_h(d,x0,x1,y,label):
    d.line([(x0,y),(x1,y)],fill=DIM,width=2)
    for x in (x0,x1):d.line([(x,y-8),(x,y+8)],fill=DIM,width=2)
    w=d.textlength(label,font=FS);d.rectangle([(x0+x1)/2-w/2-4,y+6,(x0+x1)/2+w/2+4,y+30],fill=(255,255,255));d.text(((x0+x1)/2-w/2,y+7),label,font=FS,fill=DIM)
def dim_v(d,x,y0,y1,label):
    d.line([(x,y0),(x,y1)],fill=DIM,width=2)
    for y in (y0,y1):d.line([(x-8,y),(x+8,y)],fill=DIM,width=2)
    w=d.textlength(label,font=FS);tx=x-w-14;ty=(y0+y1)/2-12
    d.rectangle([tx-4,ty-1,tx+w+4,ty+23],fill=(255,255,255));d.text((tx,ty),label,font=FS,fill=DIM)

def sheet(key):
    v=json.loads((VIEWS/key/'views.json').read_text('utf-8'));val=json.loads((VIEWS/key/'validation.json').read_text('utf-8'))
    lo=val['measured']['bounds_min_m'];ext=val['measured']['dimensions_m'];hi=[a+b for a,b in zip(lo,ext)];c=[(a+b)/2 for a,b in zip(lo,hi)]
    S=620;scale=v['orthographic'][0]['ortho_scale_m'];mpp=scale/S;pad=70
    W=3*S+4*pad;H=S+pad*2+90;im=Image.new('RGB',(W,H),(236,236,230));d=ImageDraw.Draw(im)
    d.text((pad,18),f"{v['name_zh']}　{v['state_zh']}　{key}",font=FB,fill=INK)
    d.text((pad,58),f"寬 {ext[0]:.2f} m × 深 {ext[1]:.2f} m × 高 {ext[2]:.2f} m　·　1 單位 = 1 m，正面 -Y，原點：底部中心　·　三圖同比例（{scale:.2f} m／框寬）",font=FS,fill=INK)
    px=lambda a,ca:S/2+(a-ca)/mpp
    for i,(o,title) in enumerate(zip(v['orthographic'],('正視（-Y 看向 +Y）','側視（從 +X 看）','頂視'))):
        x0=pad+i*(S+pad);y0=100;img=Image.open(VIEWS/key/o['file']).convert('RGB').resize((S,S));im.paste(img,(x0,y0))
        d.text((x0,y0+S+8),title,font=F,fill=INK)
        if i==0:   # width along x, height along z
            dim_h(d,x0+px(lo[0],c[0]),x0+px(hi[0],c[0]),y0+S-44,f'{ext[0]:.2f} m');dim_v(d,x0+min(S-60,px(hi[0],c[0])+14),y0+S-px(hi[2],c[2]),y0+S-px(lo[2],c[2]),f'{ext[2]:.2f} m')
        if i==1:   # depth along y (image right = +Y), height along z
            dim_h(d,x0+px(lo[1],c[1]),x0+px(hi[1],c[1]),y0+S-44,f'{ext[1]:.2f} m')
        if i==2:   # top: x right, y up
            dim_h(d,x0+px(lo[0],c[0]),x0+px(hi[0],c[0]),y0+S-44,f'{ext[0]:.2f} m');dim_v(d,x0+min(S-60,px(hi[0],c[0])+14),y0+S-px(hi[1],c[1]),y0+S-px(lo[1],c[1]),f'{ext[1]:.2f} m')
    SHEETS.mkdir(parents=True,exist_ok=True);p=SHEETS/f'{key}_threeview.png';im.save(p);return p

def gallery(keys):
    rel=lambda p:Path(p).relative_to(ART).as_posix()
    cards=[]
    for key in keys:
        v=json.loads((VIEWS/key/'views.json').read_text('utf-8'));val=json.loads((VIEWS/key/'validation.json').read_text('utf-8'))
        aid=key.replace('_pre','').replace('_post','');info=json.loads((EXP/aid/'v002'/f'{key}_model_info.json').read_text('utf-8'))
        ok=''.join(f"<li class={'ok' if b else 'bad'}>{'通過' if b else '未通過'}　{html.escape(k)}</li>" for k,b in val['checks'].items())
        ten=''.join(f"<figure><img loading=lazy src='../../{rel(VIEWS/key/x['file'])}'><figcaption>{x['file'][:-4]}</figcaption></figure>" for x in v['ten_views'])
        eye=''.join(f"<figure class=wide><img loading=lazy src='../../{rel(VIEWS/key/x['file'])}'><figcaption>{x['file'][:-4]}（眼高 1.6 m）</figcaption></figure>" for x in v['eye_height'])
        files=' · '.join(f"<a href='../../{rel(EXP/aid/'v002'/n)}'>{n}</a>" for n in (f'{key}.glb',f'{key}.fbx',f'{key}.blend',f'{key}_model_info.json'))
        cards.append(f"""<section id='{key}'><h2>{html.escape(v['name_zh'])}<small>{v['state_zh']}　{key}</small></h2>
<p class=meta>尺寸 {' × '.join(f'{x:.2f}' for x in info['dimensions_m'])} m（寬×深×高）　·　遊戲面數 {info['game_triangles']:,} 三角形　·　貼圖 {info['texture_size_px']} px × 4　·　{files}</p>
<p>{html.escape(info['design'])}</p><p class=dim>材質方向：{html.escape(info['material_direction'])}</p>
<img class=sheet loading=lazy src='../../{rel(SHEETS/f'{key}_threeview.png')}'>
<div class=grid>{ten}</div><div class=grid2>{eye}</div>
<details><summary>回匯檢查（{'全部通過' if val['all_passed'] else '有未通過項'}）</summary><ul>{ok}</ul><p class=dim>未檢查：{'、'.join(val['not_checked'])}</p></details></section>""")
    nav=''.join(f"<a href='#{k}'>{k}</a>" for k in keys)
    page=f"""<!doctype html><html lang=zh-Hant><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>青溪採集素材 v002</title>
<style>:root{{--bg:#f1f0ea;--ink:#1f2523;--dim:#66706b;--line:#d5d6cc}}@media (prefers-color-scheme:dark){{:root{{--bg:#1b1f1e;--ink:#e9ebe4;--dim:#9aa59f;--line:#333a37}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 "Microsoft JhengHei","Noto Sans TC",sans-serif}}main{{max-width:1280px;margin:auto;padding:16px}}
nav{{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:13px}}a{{color:inherit}}section{{border-top:1px solid var(--line);padding:18px 0}}h2 small{{font-size:14px;color:var(--dim);margin-left:12px;font-weight:400}}
.meta,.dim{{color:var(--dim);font-size:13px}}img{{max-width:100%;display:block;border-radius:4px}}.sheet{{margin:10px 0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px}}.grid2{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:8px;margin-top:8px}}
figure{{margin:0}}figcaption{{font-size:12px;color:var(--dim)}}.ok{{color:#3c8a5f}}.bad{{color:#c0503a}}</style>
<main><h1>青溪採集路段素材 v002（半寫實，遊戲模型回匯渲染）</h1>
<p class=dim>所有圖片都由匯出的 GLB 重新匯入 Blender 後渲染（Cycles）。三視圖同比例並標註尺寸；十視圖為同一模型；平視圖相機高 1.6 m。只列出實際執行過的檢查。</p><nav>{nav}</nav>{''.join(cards)}</main></html>"""
    GAL.mkdir(parents=True,exist_ok=True);(GAL/'index.html').write_text(page,encoding='utf-8');return GAL/'index.html'

if __name__=='__main__':
    keys=[k for k in ORDER if (VIEWS/k/'views.json').exists()]
    for k in keys:print('SHEET',sheet(k))
    print('GALLERY',gallery(keys),len(keys),'states')
