"""Blockout of the Qingxi starter settlement from art/references/qingxi-town-v1/concept.png.

  blender --background --factory-startup --python-exit-code 1 --python tools/build-qingxi-town-blockout.py
  uv run --no-project --with pillow python tools/annotate-qingxi-town-blockout.py

Existing models are LINKED (relative paths) from art/incoming/dondon/<ID>/<version>/ and placed as collection instances;
terrain, water and every element still to be made are simple placeholder shapes. No new asset is modelled here: per
AGENTS.md each new item needs its own AI three-view before modelling. Units metres, Z up, X east, Y north; the concept is
seen from the south, so models keep their front (-Y) towards that camera.
Writes art/source/qingxi-town-blockout-v1.blend, art/exports/qingxi-town-blockout-v1/layout.json and the raw previews
art/previews/qingxi-town-blockout-v1-{concept-angle,plan,plaza}.png (the annotate script adds labels / comparison).
"""
import bpy,bmesh,json,math,random,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
REPO=Path(__file__).resolve().parents[1];SRC=REPO/'art/incoming/dondon'
OUT_BLEND=REPO/'art/source/qingxi-town-blockout-v1.blend';OUT_JSON=REPO/'art/exports/qingxi-town-blockout-v1/layout.json'
PREV=REPO/'art/previews';NAME='qingxi-town-blockout-v1'
VERS={'StarterHouse':'v004','HerbalStall':'v001','MaterialShop':'v001','Blacksmith':'v001','SpawnAltar':'v002','NoticeBoard':'v002',
      'QCaveEntrance':'v003','LayeredCliff':'v001','SpiritHerbGarden':'v001','HerbPlanter':'v001','DryingRack':'v001','StoneArchBridge':'v001',
      'MountainStonePath':'v001','MountainStoneStairs':'v001','BambooClump':'v001','CommonPine':'v001','WildShrub':'v001','MossBoulderSet':'v001',
      'ScriptureLibrary':'v001','AlchemyHall':'v001','SectGate':'v001','SectGrandHall':'v001','QPlayerMale':'v006','QSectElder':'v006',
      'QHerbalist':'v006','QShopkeeper':'v006','QBlacksmith':'v006','QInnkeeper':'v006'}
rng=random.Random(20261024)
layout=[];labels=[]

def blend_path(aid):return SRC/aid/VERS[aid]/f'{aid}_{VERS[aid]}.blend'

# ------------------------------------------------------------------ pass 1: what to link from each asset file
# Most files keep the model in top-level collections beside studio / concept-reference ones; the QPlayerStart16 files keep
# loose objects in the scene collection with their preview camera and lights.
SKIP=('Studio','Not_Export','Concept','Reference')
EXPORT={}
for aid in VERS:
    bpy.ops.wm.open_mainfile(filepath=str(blend_path(aid)));sc=bpy.context.scene
    cols=[c.name for c in sc.collection.children if not any(k in c.name for k in SKIP)]
    EXPORT[aid]=('collections',cols) if cols else ('objects',[o.name for o in sc.collection.objects if o.type in ('MESH','EMPTY','ARMATURE','CURVE')])
    assert EXPORT[aid][1],aid

# ------------------------------------------------------------------ pass 2: build
bpy.ops.wm.read_factory_settings(use_empty=True);S=bpy.context.scene;S.unit_settings.system='METRIC'
OUT_BLEND.parent.mkdir(parents=True,exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))   # saved first so links can be relative
def coll(name):
    c=bpy.data.collections.new(name);S.collection.children.link(c);return c
C_TERRAIN,C_WATER,C_ASSETS,C_TODO,C_BG,C_CAM=(coll(n) for n in ('10_Terrain','20_Water','30_Existing_Assets_Linked','40_ToDo_Placeholders','50_Background','90_Cameras_Lights'))

WRAP={}
def asset_collection(aid):
    if aid in WRAP:return WRAP[aid]
    kind,names=EXPORT[aid]
    with bpy.data.libraries.load(str(blend_path(aid)),link=True,relative=True) as (src,dst):setattr(dst,kind,names)
    w=bpy.data.collections.new(f'ASSET_{aid}_{VERS[aid]}')
    for d in getattr(dst,kind):(w.children if kind=='collections' else w.objects).link(d)
    WRAP[aid]=w;return w

def place(aid,x,y,z=None,yaw=0.,s=1.,role='',status='已有',label=None):
    z=height(x,y) if z is None else z
    e=bpy.data.objects.new(f'{aid}',None);e.instance_type='COLLECTION';e.instance_collection=asset_collection(aid)
    e.location=(x,y,z);e.rotation_euler=(0,0,math.radians(yaw));e.scale=(s,s,s);C_ASSETS.objects.link(e)
    e['asset_id']=aid;e['status']=status;e['role']=role
    layout.append({'kind':'asset','asset_id':aid,'version':VERS[aid],'source':str(blend_path(aid).relative_to(REPO)).replace('\\','/'),
                   'location_m':[round(x,2),round(y,2),round(z,2)],'yaw_deg':yaw,'scale':s,'status':status,'role':role})
    if label:labels.append({'text':label,'status':status,'world':[x,y,z]})
    return e

MATS={}
def mat(name,c,rough=.8,emit=0.,alpha=1.):
    if name in MATS:return MATS[name]
    m=bpy.data.materials.new(name);m.use_nodes=True;b=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value=(*c,1);b.inputs['Roughness'].default_value=rough;m.diffuse_color=(*c,alpha)
    if emit:b.inputs['Emission Color'].default_value=(*c,1);b.inputs['Emission Strength'].default_value=emit
    if alpha<1:b.inputs['Alpha'].default_value=alpha;m.surface_render_method='BLENDED' if hasattr(m,'surface_render_method') else None
    MATS[name]=m;return m

def mesh_obj(name,bm,m,col,todo=None,role=''):
    me=bpy.data.meshes.new(name);bm.to_mesh(me);bm.free();me.materials.append(m)
    for p in me.polygons:p.use_smooth=True
    o=bpy.data.objects.new(name,me);col.objects.link(o)
    if todo:o['status']=todo;o['role']=role
    return o
def T(x,y,z,yaw=0.,sx=1.,sy=1.,sz=1.,pitch=0.,roll=0.):
    return Matrix.Translation((x,y,z))@Matrix.Rotation(math.radians(yaw),4,'Z')@Matrix.Rotation(math.radians(pitch),4,'X')@Matrix.Rotation(math.radians(roll),4,'Y')@Matrix.Diagonal((sx,sy,sz,1))
def box(bm,M):bmesh.ops.create_cube(bm,size=1,matrix=M@Matrix.Translation((0,0,.5)))
def cyl(bm,M,r1,r2,h,seg=24):bmesh.ops.create_cone(bm,cap_ends=True,segments=seg,radius1=r1,radius2=r2,depth=h,matrix=M@Matrix.Translation((0,0,h/2)))
def ball(bm,M,r,sub=2):bmesh.ops.create_icosphere(bm,subdivisions=sub,radius=r,matrix=M)
def ring(bm,M,R,r,seg=48,sides=8):
    vs=[[bm.verts.new(M@Vector(((R+r*math.cos(b))*math.cos(a),(R+r*math.cos(b))*math.sin(a),r*math.sin(b)))) for b in [2*math.pi*j/sides for j in range(sides)]] for a in [2*math.pi*i/seg for i in range(seg)]]
    for i in range(seg):
        for j in range(sides):bm.faces.new((vs[i][j],vs[(i+1)%seg][j],vs[(i+1)%seg][(j+1)%sides],vs[i][(j+1)%sides]))

def todo(name,build,m,x,y,role,status='待做',label=None,z=None):
    """Placeholder for an element that has no model yet; build(bm) draws it around the local origin."""
    bm=bmesh.new();build(bm);o=mesh_obj(f'TODO_{name}',bm,m,C_TODO,status,role);z=height(x,y) if z is None else z;o.location=(x,y,z)
    layout.append({'kind':'placeholder','name':name,'location_m':[round(x,2),round(y,2),round(z,2)],'status':status,'role':role})
    if label:labels.append({'text':label,'status':status,'world':[x,y,z]})
    return o

# ------------------------------------------------------------------ terrain and water
def sstep(a,b,x):t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3-2*t)
LAKES=[(0,-38,72,36),(-48,-8,24,16),(46,-6,30,14),(66,22,9,28),(-30,-82,28,14)]   # (cx, cy, rx, ry) ellipses of water
ISLES=[(-22,-42,9,6),(26,-48,10,6),(4,-66,7,5)]
def inside(x,y,es,pad=0.):return max(1-((x-cx)/(rx+pad))**2-((y-cy)/(ry+pad))**2 for cx,cy,rx,ry in es)
PLAZA=(0,25,17.)
# Dry shore under the market (east) and the west lodging so they are not under the -0.9 m water; kept out of ISLES so the
# seeded scatter below (lily pads, trees, shrubs) draws the same random numbers as before.
LAND=[(52,-36,26,15),(-54,-22,13,9)]
def height(x,y):
    h=.35*math.sin(x*.07)*math.cos(y*.05)+.2*math.sin(x*.19+y*.13)
    h+=8*sstep(52,34,math.hypot(x,y-88))                                    # tree mound
    h+=17*sstep(55,20,math.hypot(x+95,y-100))                               # ruins hill (west)
    h+=min(28,max(0,(y-150)*.3))                                            # rising ground behind the tree
    h+=5*sstep(88,104,x)                                                    # foot of the east cliffs
    if math.hypot(x-PLAZA[0],y-PLAZA[1])<PLAZA[2]+4:h=max(h,1.8)
    lake=sstep(0,.25,inside(x,y,LAKES));isle=max(sstep(0,.3,inside(x,y,ISLES)),sstep(0,.3,inside(x,y,LAND)))
    return h-3*lake*(1-isle)
bm=bmesh.new();N=200;SZ=420.
bmesh.ops.create_grid(bm,x_segments=N,y_segments=N,size=SZ/2)
for v in bm.verts:v.co.z=height(v.co.x,v.co.y)
mesh_obj('Terrain',bm,mat('Grass',(.30,.42,.18)),C_TERRAIN)
bm=bmesh.new();bmesh.ops.create_grid(bm,x_segments=1,y_segments=1,size=170,matrix=Matrix.Translation((0,-20,-.9)))
mesh_obj('Water_Qingxi',bm,mat('Water',(.10,.48,.46),rough=.08),C_WATER)
for cx,cy in ((-22,9),(22,9),(56,30)):    # small cascades from the plaza terrace / east stream (to do)
    todo(f'小瀑布_{cx}',lambda bm:box(bm,T(0,0,-.9,sx=7,sy=.6,sz=3)),mat('Fall',(.75,.88,.9),emit=.3),cx,cy,'分層小瀑布；斷流前後對比','需改版',None,z=0)
labels.append({'text':'分層小瀑布（需改版）','status':'需改版','world':[22,9,1]})
lily=mat('Lily',(.20,.50,.20))
for i in range(60):
    while True:
        x,y=rng.uniform(-70,70),rng.uniform(-75,-5)
        if inside(x,y,LAKES)>.15 and inside(x,y,ISLES)<0:break
    r=rng.uniform(.7,1.6);todo(f'荷葉_{i}',lambda bm,r=r:cyl(bm,T(0,0,0),r,r,.05,12),lily,x,y,'荷葉與水蓮：青溪事件、採集物',z=-.86)
labels.append({'text':'荷葉／水蓮（待做）','status':'待做','world':[-30,-30,0]})

# ------------------------------------------------------------------ giant tree, halls under it, plaza
bark,leaf=mat('Bark',(.30,.20,.12)),mat('Leaves',(.22,.42,.16))
def tree(bm):
    cyl(bm,T(0,0,0),11,6,36,32)
    for i in range(7):a=i*51.4;cyl(bm,T(0,0,0,yaw=a,pitch=72)@Matrix.Translation((0,0,0)),4,1,18,12)
    for i in range(10):
        a=math.radians(i*36);ball(bm,T(22*math.cos(a)*rng.uniform(.6,1),22*math.sin(a)*rng.uniform(.6,1),48+rng.uniform(-4,10),sx=1.2,sz=.75),rng.uniform(13,19))
    ball(bm,T(0,0,62,sz=.7),22)
o=todo('巨大古樹',tree,bark,0,92,'聚落地標、視覺中心',label='巨大古樹（待做）');o.data.materials.append(leaf)
for p in o.data.polygons:p.material_index=1 if p.center.z>36 else 0
place('SectGrandHall',0,64,yaw=0,role='樹下樓閣：傳授煉氣訣、講法（以宗門大殿暫代）',status='需改版',label='樹下樓閣（宗門大殿暫代，需改版）')
place('ScriptureLibrary',-30,72,yaw=20,role='樹下樓閣（藏經閣暫代）',status='需改版')
place('AlchemyHall',30,73,yaw=-20,role='樹下樓閣（丹房暫代）',status='需改版')
stone=mat('PlazaStone',(.62,.60,.54))
todo('圓形石廣場',lambda bm:cyl(bm,T(0,0,0),PLAZA[2],PLAZA[2],2.,64),stone,PLAZA[0],PLAZA[1],'滿十天後測資、宗門選比',label='圓形石廣場（待做）',z=0)
todo('廣場陣紋',lambda bm:[ring(bm,T(0,0,2.02),R,.25,64,6) for R in (5,9,13)],mat('Rune',(.80,.66,.32),emit=.4),PLAZA[0],PLAZA[1],'廣場同心圓陣紋',z=0)
red=mat('Pillar',(.55,.10,.07))
for sx in (-1,1):todo(f'廣場立柱_{sx}',lambda bm:cyl(bm,T(0,0,2),.6,.6,8,16),red,sx*13,36,'廣場立柱、幡旗',z=0)
labels.append({'text':'廣場立柱（待做）','status':'待做','world':[13,36,2]})
place('SpawnAltar',0,25,2.,role='廣場中央陣台（測資）',label='中央陣台 SpawnAltar')
place('NoticeBoard',13,13,2.,yaw=30,role='委託與事件公告',label='公告欄')
for i,(y,z) in enumerate(((44.5,2.),(49.5,5.))):place('MountainStoneStairs',0,y,z,s=1.,role='廣場往古樹的石階')
place('MountainStoneStairs',0,5.5,-.9,yaw=180,s=.85,role='棧道上廣場的石階')

# ------------------------------------------------------------------ boardwalks over the water, lanterns
wood=mat('Boardwalk',(.42,.29,.17));lamp=mat('Lantern',(1.,.62,.25),emit=6.)
WALKS=[[(-118,-112),(-80,-90),(-50,-95),(-26,-66),(-9,-40),(0,-14),(0,3)],[(80,-82),(50,-66),(30,-62),(14,-38),(0,-14)],
       [(-46,-14),(-28,-6),(-14,12)],[(16,20),(42,14),(62,-8)]]
for wi,pts in enumerate(WALKS):
    for a,b in zip(pts,pts[1:]):
        (x0,y0),(x1,y1)=a,b;L=math.hypot(x1-x0,y1-y0);yaw=math.degrees(math.atan2(-(x1-x0),y1-y0))
        def walk(bm,L=L,yaw=yaw):
            box(bm,T(0,0,.45,yaw,sx=3,sy=L+3,sz=.25))
            for t in range(int(L//4)+1):
                for s in (-1,1):box(bm,T(0,0,0,yaw)@Matrix.Translation((s*1.4,-L/2+t*4,-2)) @Matrix.Diagonal((.25,.25,2.5,1)))
        todo(f'水上棧道_{wi}_{x0}_{y0}',walk,wood,(x0+x1)/2,(y0+y1)/2,'水上木棧道：主要動線','需改版',z=0)
        for t in range(1,int(L//14)+1):
            f=t*14/L;x,y=x0+(x1-x0)*f,y0+(y1-y0)*f;s=1 if t%2 else -1;nx,ny=(y1-y0)/L*s*1.9,-(x1-x0)/L*s*1.9
            def post(bm):cyl(bm,T(0,0,.5),.12,.12,3.2,8);box(bm,T(0,0,3.3,sx=.45,sy=.45,sz=.6))
            todo(f'燈籠柱_{wi}_{x:.0f}_{y:.0f}',post,lamp,x+nx,y+ny,'木柱吊燈籠：照明、路線引導',z=0)
labels+= [{'text':'水上棧道（需改版）','status':'需改版','world':[-26,-66,0]},{'text':'燈籠柱（待做）','status':'待做','world':[50,-66,0]}]
place('StoneArchBridge',-34,-11,-.8,yaw=-60,role='跨溪石拱橋',label='石拱橋')

# ------------------------------------------------------------------ west: bamboo, stone path, borrowed huts, ruins
for i in range(26):
    while True:
        x,y=rng.uniform(-132,-92),rng.uniform(-80,60)
        if abs(x+102)>5:break
    place('BambooClump',x,y,yaw=rng.uniform(0,360),s=rng.uniform(.9,1.4),role='竹林：採集區、入口')
labels.append({'text':'竹林 BambooClump','status':'已有','world':[-115,-10,0]})
for i in range(22):place('MountainStonePath',-102,-82+i*6,yaw=0,role='竹林旁石板小徑')
for y in range(-80,60,16):todo(f'燈籠柱_竹徑_{y}',lambda bm:(cyl(bm,T(0,0,0),.12,.12,3.2,8),box(bm,T(0,0,3.2,sx=.45,sy=.45,sz=.6))),lamp,-98.5,y,'竹徑燈籠柱')
for x,y,yaw in ((-56,-26,35),(-72,-2,50),(-40,36,70)):place('StarterHouse',x,y,yaw=yaw,role='借住小屋：床、箱子、修煉位')
labels.append({'text':'借住小屋 StarterHouse ×3','status':'已有','world':[-58,-4,0]})
place('QInnkeeper',-50,-18,role='聚落 NPC')
ruin=mat('RuinStone',(.55,.55,.50))
def gate(bm):
    for s in (-1,1):box(bm,T(s*3.2,0,0,sx=1.6,sy=1.6,sz=9))
    box(bm,T(0,0,9,sx=9,sy=2,sz=1.4))
for i,(x,y,yaw) in enumerate(((-96,102,10),(-80,112,-5),(-108,90,25))):todo(f'石門遺跡_{i}',gate,ruin,x,y,'古代石門遺跡：青溪「破陣」調查點',label='石門遺跡（待做）' if i==0 else None)
for i in range(6):todo(f'殘柱_{i}',lambda bm:box(bm,T(0,0,0,sx=1.4,sy=1.4,sz=rng.uniform(2,6))),ruin,-100+rng.uniform(-14,14),100+rng.uniform(-12,12),'遺跡殘柱')
for i,(x,y) in enumerate(((-78,58),(-82,64),(-86,70),(-90,76))):place('MountainStoneStairs',x,y,yaw=35,s=1.,role='通往遺跡的石階')
todo('山坡瀑布',lambda bm:box(bm,T(0,0,-1,sx=5,sy=.6,sz=16)),mat('Fall',(.75,.88,.9),emit=.3),-64,96,'遺跡旁瀑布（dondon 有 WaterfallCliff，未交付）','dondon 未交付',label='山坡瀑布（dondon 未交付）')

# ------------------------------------------------------------------ east: cliffs and caves, water wheel, market, fields
for x,y,s in ((110,28,1.25),(114,66,1.4),(104,-8,1.0)):place('LayeredCliff',x,y,0,yaw=-90,s=s,role='東側山壁')
labels.append({'text':'山壁 LayeredCliff','status':'已有','world':[110,40,20]})
for x,y,z in ((97,22,0),(99,62,0)):
    place('QCaveEntrance',x,y,z+4.5,yaw=-90,s=1.6,role='洞窟入口：洞府／礦洞／妖獸育幼地',label='洞窟入口 QCaveEntrance')
    todo(f'洞內暖光_{y}',lambda bm:box(bm,T(0,0,0,sx=.3,sy=3,sz=4)),mat('CaveGlow',(1.,.55,.2),emit=8.),x+1.5,y,'洞內暖光',z=4.5)
place('StarterHouse',84,-22,yaw=-70,role='水車木屋（房屋可用民宅）',status='已有')
todo('水車',lambda bm:(ring(bm,T(0,0,0,pitch=90,yaw=90),4.6,.35,40,6),[box(bm,T(0,0,0,yaw=90,pitch=90+a,sx=.25,sy=9,sz=.25)) for a in range(0,180,30)]),wood,73,-18,'水車：磨坊、斷流事件的可見指標',label='水車（待做）',z=4.2)
for x,y,yaw in ((36,-40,10),(44,-38,10)):place('HerbalStall',x,y,yaw=yaw,role='坊市攤位')
place('MaterialShop',60,-31,yaw=-20,role='坊市：賣材料、買丹藥裝備',label='坊市（藥攤、雜貨店）')
place('Blacksmith',76,-47,yaw=-30,role='鐵匠鋪',label='鐵匠鋪')
place('DryingRack',40,-45,yaw=0,role='攤位雜物')
for aid,x,y,yaw in (('QHerbalist',38,-36,0),('QShopkeeper',58,-26,0),('QBlacksmith',72,-42,-20)):place(aid,x,y,yaw=yaw,role='聚落 NPC')
for i in range(3):
    for j in range(2):place('SpiritHerbGarden',44+i*9,-74-j*8,yaw=0,role='NPC 藥圃：種植教學',label='藥圃 SpiritHerbGarden' if i==j==0 else None)
for i in range(5):place('HerbPlanter',40+i*2.5,-88,role='藥圃花盆')
fence=mat('Fence',(.50,.38,.22))
todo('藥圃籬笆',lambda bm:[box(bm,T(x,y,0,sx=sx,sy=sy,sz=1.1)) for x,y,sx,sy in ((53,-60,30,.2),(53,-92,30,.2),(38,-76,.2,32),(68,-76,.2,32))],fence,0,0,'籬笆（dondon 有 BambooFence／FenceGate，未交付）','dondon 未交付',z=0)

# ------------------------------------------------------------------ plants, willows, people
for i in range(40):
    while True:
        x,y=rng.uniform(-150,150),rng.uniform(-110,150)
        if inside(x,y,LAKES,8)<0 and math.hypot(x,y-88)>40 and math.hypot(x,y-25)>24 and not(-135<x<-90 and -82<y<62) and not(30<x<90 and -95<y<-20):break
    place('CommonPine',x,y,yaw=rng.uniform(0,360),s=rng.uniform(1.,1.8),role='松樹')
for i in range(30):
    a=rng.uniform(0,2*math.pi);cx,cy,rx,ry=rng.choice(LAKES);x,y=cx+(rx+3)*math.cos(a),cy+(ry+3)*math.sin(a)
    if inside(x,y,LAKES)<0:place(rng.choice(['WildShrub','MossBoulderSet']),x,y,yaw=rng.uniform(0,360),s=rng.uniform(1,1.6),role='水岸灌木、苔石')
willow=mat('Willow',(.45,.60,.22))
for i,(x,y) in enumerate(((-30,-6),(30,-2),(-62,-36),(64,-40),(-8,-78),(20,6),(48,12),(-44,-60))):
    todo(f'垂柳_{i}',lambda bm:(cyl(bm,T(0,0,0),.6,.4,6,10),ball(bm,T(0,0,8,sx=1,sy=1,sz=1.5),4.5)),willow,x,y,'水岸垂柳',label='垂柳（待做）' if i==0 else None)
place('QSectElder',0,34,2.,yaw=180,role='廣場測資、選比的長老')
place('QPlayerMale',-3,17,2.,yaw=180,role='比例參考：玩家身高約 1.45 m',label='玩家（1.45 m，比例參考）')

# ------------------------------------------------------------------ background: karst peaks and the sect on a far peak
rockm=mat('KarstRock',(.45,.50,.46));misty=mat('FarHill',(.38,.50,.40))
for i in range(26):
    x,y=rng.uniform(-330,330),rng.uniform(230,420);h=rng.uniform(70,170);r=h*rng.uniform(.22,.32)
    o=todo(f'遠景奇峰_{i}',lambda bm,r=r,h=h:(cyl(bm,T(0,0,0),r,r*.35,h,14),ball(bm,T(0,0,h,sx=1,sy=1,sz=.7),r*.42,1)),rockm,x,y,'遠景奇峰（dondon 有 CloudpiercerPeak，未交付）','dondon 未交付',z=0)
    o.parent=None;C_TODO.objects.unlink(o);C_BG.objects.link(o)
peak=todo('宗門主峰',lambda bm:cyl(bm,T(0,0,0),45,26,120,20),rockm,70,300,'遠景宗門所在山峰','dondon 未交付',label='遠景奇峰與宗門（dondon 未交付／需低面數）',z=0)
C_TODO.objects.unlink(peak);C_BG.objects.link(peak)
place('SectGrandHall',70,300,120,s=1.6,role='遠景宗門（需低面數替身）',status='需改版');place('SectGate',70,282,120,s=1.6,role='遠景宗門山門',status='需改版')
for i in range(8):
    x,y=-260+i*75,rng.uniform(160,210);o=todo(f'中景山丘_{i}',lambda bm:ball(bm,T(0,0,0,sx=1.6,sy=1,sz=.55),40,2),misty,x,y,'中景山丘',z=0);C_TODO.objects.unlink(o);C_BG.objects.link(o)

# ------------------------------------------------------------------ light, cameras, render
w=bpy.data.worlds.new('Sky');w.use_nodes=True;S.world=w;bg=next(n for n in w.node_tree.nodes if n.type=='BACKGROUND')
bg.inputs[0].default_value=(.62,.74,.86,1);bg.inputs[1].default_value=1.1
sun=bpy.data.objects.new('Sun_morning',bpy.data.lights.new('Sun_morning','SUN'));sun.data.energy=4.2;sun.data.color=(1.,.93,.80);sun.data.angle=math.radians(2)
sun.rotation_euler=(math.radians(55),0,math.radians(-135));C_CAM.objects.link(sun)   # low morning sun from the north-west (upper left of the view)
def camera(name,loc,target,lens=28,ortho=None):
    c=bpy.data.objects.new(name,bpy.data.cameras.new(name));C_CAM.objects.link(c);c.location=loc;c.data.clip_end=3000
    c.rotation_euler=(Vector(target)-Vector(loc)).to_track_quat('-Z','Y').to_euler();c.data.lens=lens
    if ortho:c.data.type='ORTHO';c.data.ortho_scale=ortho
    return c
cams={'concept-angle':camera('Cam_concept_angle',(-12,-205,92),(6,45,6),26),'plan':camera('Cam_plan',(0,5,600),(0,5.001,0),ortho=330),
      'plaza':camera('Cam_plaza',(-6,-30,9),(0,40,10),24)}
for eng in ('BLENDER_EEVEE','BLENDER_EEVEE_NEXT'):
    try:S.render.engine=eng;break
    except TypeError:pass
S.view_settings.view_transform='AgX';S.render.image_settings.file_format='PNG';PREV.mkdir(parents=True,exist_ok=True)
from bpy_extras.object_utils import world_to_camera_view
shots={}
for key,cam in cams.items():
    S.camera=cam;S.render.resolution_x,S.render.resolution_y=((1600,1600) if key=='plan' else (1672,941));S.render.resolution_percentage=100
    S.render.filepath=str(PREV/f'{NAME}-{key}.png');bpy.ops.render.render(write_still=True)
    shots[key]=[dict(l,screen=list(world_to_camera_view(S,cam,Vector(l['world'])))[:2]) for l in labels]
    print('RENDERED',key,flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND),relative_remap=True)
OUT_JSON.parent.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
OUT_JSON.write_text(json.dumps({'scene':'qingxi-town-blockout-v1','concept':'art/references/qingxi-town-v1/concept.png','concept_sha256':sha(REPO/'art/references/qingxi-town-v1/concept.png'),
    'units':'metres','axes':'Z up, X east, Y north; models face -Y (south, towards the concept camera); yaw in degrees about Z',
    'blender':bpy.app.version_string,'linked_libraries':sorted(l.filepath for l in bpy.data.libraries),
    'counts':{k:sum(1 for e in layout if e['status']==k) for k in ('已有','需改版','待做','dondon 未交付')},
    'placements':layout,'labels':shots},ensure_ascii=False,indent=1),encoding='utf-8')
print('DONE',len(layout),'placements',len(bpy.data.libraries),'libraries',flush=True)
