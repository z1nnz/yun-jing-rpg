"""Compose review sheets with Pillow (no Blender needed).
uv run --no-project --with pillow python compose_sheets.py threeview|turnaround|demo
"""
import json,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
REPO=Path(__file__).resolve().parents[4];KIT='qingxi-gathering-visual-kit-v1'
REF=REPO/'art/references'/KIT;PRE=REPO/'art/previews'/KIT
FONT='C:/Windows/Fonts/msjh.ttc'
def font(sz):
    try:return ImageFont.truetype(FONT,sz)
    except OSError:return ImageFont.load_default()

def threeview():
    src=REF/'threeview';stats=json.loads((src/'threeview_stats.json').read_text('utf-8'));T=320;pad=8;head=54
    sheet=Image.new('RGB',(pad+(T+pad)*3+260,pad+(T+head+pad)*len(stats)),(28,31,33));d=ImageDraw.Draw(sheet)
    for r,(key,info) in enumerate(stats.items()):
        y=pad+r*(T+head+pad)
        d.text((pad,y+4),f"{info['name_zh']} · {info['state_zh']}　{key}",fill=(230,236,230),font=font(22))
        for c,v in enumerate(('front','side','top')):
            im=Image.open(src/f'{key}_{v}.png').convert('RGB').resize((T,T));sheet.paste(im,(pad+c*(T+pad),y+head-10))
            d.text((pad+c*(T+pad)+6,y+head-6),{'front':'正面 -Y','side':'右側 +X','top':'頂視'}[v],fill=(200,210,200),font=font(16))
        dx,dy,dz=info['dimensions_m'];x=pad+3*(T+pad)+6
        for k,line in enumerate([f'寬 X {dx:.2f} m',f'深 Y {dy:.2f} m',f'高 Z {dz:.2f} m',f"三角面 {info['triangles']:,}",f"分件 {info['mesh_objects']}",f"來源材質 {len(info['source_materials'])}"]):
            d.text((x,y+head+k*28),line,fill=(220,226,220),font=font(19))
    sheet.save(REF/'threeview_sheet.jpg',quality=88);print('SHEET',REF/'threeview_sheet.jpg',sheet.size)

def turnaround():
    for folder in sorted((PRE/'turnarounds').iterdir()):
        ims=sorted(folder.glob('*.png'))
        if len(ims)!=10:continue
        T=300;sheet=Image.new('RGB',(T*5,T*2+40),(28,31,33));d=ImageDraw.Draw(sheet);d.text((8,6),folder.name,fill=(230,236,230),font=font(22))
        for i,p in enumerate(ims):sheet.paste(Image.open(p).convert('RGB').resize((T,T)),((i%5)*T,40+(i//5)*T))
        sheet.save(PRE/'turnarounds'/f'{folder.name}_10views.jpg',quality=86);print('SHEET',folder.name)

if __name__=='__main__':{'threeview':threeview,'turnaround':turnaround}[sys.argv[1]]()
