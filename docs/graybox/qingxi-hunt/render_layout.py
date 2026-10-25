"""Render a coordinate plan, NOT a Unity screenshot. Requires Pillow, not Unity.
Usage: python render_layout.py [--font /path/to/CJK-font.ttc]
"""
import argparse,json,hashlib,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

here=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--font',default='C:/Windows/Fonts/msjh.ttc');args=parser.parse_args()
if not Path(args.font).is_file():raise SystemExit('Supply --font with a CJK font; no substitute font is downloaded.')
d=json.loads((here/'layout.json').read_text(encoding='utf-8'))
report=json.loads((here/'validation.json').read_text(encoding='utf-8'))
sha=hashlib.sha256((here/'layout.json').read_bytes()).hexdigest()
assert report['layoutSha256']==sha,'Run validate_layout.py after changing layout.json'
W,H=2400,1570;img=Image.new('RGB',(W,H),'#f2f2e8');draw=ImageDraw.Draw(img)
def font(n):return ImageFont.truetype(args.font,n)
def text(pos,s,n=25,fill='#243c39'):draw.text(pos,s,font=font(n),fill=fill)
left,top,scale=100,220,7.5
def pos(p):return left+p['x']*scale,top+(160-p['z'])*scale
def point(x,z):return pos({'x':x,'z':z})
text((100,52),'青溪狩獵區  /  220 × 160 m',50)
text((100,120),'Issue #9  ·  座標配置圖，非 Unity 截圖  ·  公尺／Y 向上／+Z 向北',28)
text((1830,60),'獨立灰盒配置',37)
text((1830,118),'主路、採藥與替代回程',25)
draw.rectangle((left,top,left+220*scale,top+160*scale),fill='#e5e9db',outline='#415f53',width=3)
zonecolors=['#d9d9c3','#e9e0cc','#d2dfcb','#dfe7b9','#cce3df','#d4e4da']
for zone,color in zip(d['zones'],zonecolors):
    x,z=zone['center']['x'],zone['center']['z'];a=point(x-zone['width']/2,z+zone['depth']/2);b=point(x+zone['width']/2,z-zone['depth']/2)
    draw.rectangle((*a,*b),fill=color,outline='#bdc9b6',width=2)
for x in range(0,221,20):
    a,b=point(x,0),point(x,160);draw.line((a,b),fill='#cad3c3');text((a[0]-12,a[1]+12),str(x),20)
for z in range(0,161,20):
    a,b=point(0,z),point(220,z);draw.line((a,b),fill='#cad3c3');text((a[0]-48,a[1]-12),str(z),20)
for route in d['routes']:
    if route['name'] not in ('MainDiscovery','AlternativeReturn','HerdConnector'):continue
    color={'MainDiscovery':'#cc8d35','AlternativeReturn':'#408e8a','HerdConnector':'#acb780'}[route['name']]
    pts=[pos(p) for p in route['points']];draw.line(pts,fill=color,width=int(route['width']*scale),joint='curve')
    for x,y in pts:draw.ellipse((x-5,y-5,x+5,y+5),fill=color)
for obstacle in d['obstacles']:
    if obstacle['kind']=='boundary':continue
    p,s=obstacle['position'],obstacle['size'];a=point(p['x']-s['x']/2,p['z']+s['z']/2);b=point(p['x']+s['x']/2,p['z']-s['z']/2)
    color={'deepWater':'#57859b','tree':'#55775a','building':'#8e7257'}.get(obstacle['kind'],'#78827b')
    draw.rectangle((*a,*b),fill=color,outline='#42564d',width=2)
for group in 'ABC':
    pts=[pos(m['position']) for m in d['markers'] if m['kind']=='flee' and m['group']==group]
    draw.line(pts+[pts[0]],fill='#bb6849',width=2)
for m in d['markers']:
    kind=m['kind'];x,y=pos(m['position']);name=m['name']
    if kind in ('cameraBlocker','boundary'):continue
    short={'player':'P'+name[-1],'merchant':'M','return':'S','herb':'H'+name[-2:],'clue':'T'+name[-2:],'rabbit':name[-3:].replace('0',''),'flee':'F'+name[-3:].replace('0','')}[kind]
    color={'player':'#3e76bb','merchant':'#bd792c','return':'#246c66','herb':'#388c45','clue':'#b57a26','rabbit':'#b44b26','flee':'#c66844'}[kind]
    radius=7 if kind=='flee' else 9
    draw.ellipse((x-radius,y-radius,x+radius,y+radius),fill='#f9f5e8' if kind=='flee' else color,outline=color,width=3)
    dx,dy=10,-29
    if kind=='merchant':dx,dy=-6,15
    if kind=='player' and name.endswith('02'):dx,dy=6,-45
    text((x+dx,y+dy),short,22,color)
# Region labels are placed in open space to keep routes and markers readable.
for x,z,label in [(6,36,'01 聚落出口'),(45,43,'02 山道'),(29,121,'03 採藥林'),(128,150,'04 山兔草坡'),(121,24,'05 溪流淺灘'),(52,5,'06 回村捷徑')]:text(point(x,z),label,31)
text(point(166,54),'深水封閉',26,'#f8f4e8')
text(point(72,68),'地形遮擋 7 m',22,'#ffffff')
text(point(89,144),'林脊遮擋',22)
x=1830;y=225
for title,lines in [
 ('六個分區',['聚落 30 × 24 m','山道 60.2 m，主路寬 6 m','採藥林 50 × 40 m','兔坡 80 × 60 m，最高 +2.4 m','淺灘 40 × 30 m，水深 0.12 m','捷徑段 72.4 m，回程寬 8 m']),
 ('路線估算（步速 4 m/s）',[f"首線索 {report['measurements']['first_clue_arrival_seconds']:.1f} 秒",f"兔子初次幾何可視 {report['measurements']['first_rabbit_geometric_line_of_sight_seconds']:.1f} 秒",'完整主路 291.6 m／72.9 秒','回程 225.8 m／56.4 秒','按示意主路估算，可自由抄近路']),
 ('圖例',['P 玩家出生　M 材料商販','T 腳印線索　H 青靈草標記','A1–C2 山兔出生，共 6 點','FA1–FC3 逃跑點，共 9 點','S 安全回村　灰塊：簡化阻擋']),
 ('驗證範圍',['座標／方盒碰撞／格網路徑預檢','不是 Unity／NavMesh 實測','實際結果請看 README 與驗證報告'])]:
    text((x,y),title,30);y+=48
    for line in lines:text((x,y),line,23);y+=35
    y+=23
text((100,1490),'橙色：探索主路　　青色：替代回程　　紅色三角：兔群逃跑點連通參考（不是 AI 行為）',25)
text((100,1530),'來源：layout.json  ·  SHA-256 '+sha[:24]+'…  ·  +X 向右，+Z 向上',22)
img.save(here/'layout.png')
lines=['# 灰盒標記座標表','','由 `layout.json` 產生；Unity 世界座標、公尺、Y 向上。這是配置資料，不是執行驗證。','', '| 名稱 | 類別 | X | Y | Z |','| --- | --- | ---: | ---: | ---: |']
for m in d['markers']:lines.append('| '+m['name']+' | '+m['kind']+' | '+' | '.join(str(m['position'][k]) for k in 'xyz')+' |')
lines+=['','## 簡化阻擋體','','| 名稱 | 中心 X / Y / Z | 尺寸 X / Y / Z |','| --- | --- | --- |']
for o in d['obstacles']:lines.append('| '+o['name']+' | '+' / '.join(str(o['position'][k]) for k in 'xyz')+' | '+' / '.join(str(o['size'][k]) for k in 'xyz')+' |')
(here/'coordinates.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('Wrote layout.png and coordinates.md; no game screenshot generated.')
