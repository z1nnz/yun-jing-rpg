"""Pack one review pass into two sheets: uv run --no-project --with pillow python review_sheet.py <pass> <key> <outdir>"""
import sys
from pathlib import Path
from PIL import Image
REV=Path(__file__).resolve().parents[4]/'art/references/qingxi-gathering-visual-kit-v1/review'
pas,k,out=sys.argv[1],sys.argv[2],Path(sys.argv[3]);d=REV/pas
b=Image.open(d/f'{k}_beauty34.png').convert('RGB').resize((1200,750));c=Image.open(d/f'{k}_closeup.png').convert('RGB').resize((1200,750))
s=Image.new('RGB',(1200,1500));s.paste(b,(0,0));s.paste(c,(0,750));s.save(out/f'{pas}_{k}_a.jpg',quality=90)
ims=[Image.open(d/f'{k}_{v}.png').convert('RGB').resize((600,600)) for v in ('front','right','top')]
s=Image.new('RGB',(1800,1200));[s.paste(im,(i*600,0)) for i,im in enumerate(ims)]
s.paste(Image.open(d/f'{k}_beauty_back.png').convert('RGB').resize((960,600)),(0,600));s.paste(Image.open(d/f'{k}_far12m.png').convert('RGB').resize((960,600)).crop((120,0,960,600)),(960,600))
s.save(out/f'{pas}_{k}_b.jpg',quality=88);print('ok')
