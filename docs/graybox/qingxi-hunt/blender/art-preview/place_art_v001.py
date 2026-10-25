"""Scale check: put the v001 art batch (LowGrass, TrampledGrass, StreamBank) into a copy of the Blender graybox.

  blender --background --factory-startup --python-exit-code 1 --python docs/graybox/qingxi-hunt/blender/art-preview/place_art_v001.py

Opens ../QingxiHuntGraybox_blockout.blend and saves a NEW file beside this script (QingxiHuntGraybox_art_v001.blend); the
graybox and art/authored/qingxi-hunt/v001 are not modified. LOD0 meshes are appended once and placed as linked
duplicates; QPlayerMale v006 and QMountainRabbit v002 are appended as scale references. Writes renders/*.png and
placement.json. Positions are a visual trial, not layout data: layout.json stays the only coordinate source.
"""
import bpy,bmesh,json,math,random
from pathlib import Path
from mathutils import Vector,Matrix

HERE=Path(__file__).resolve().parent;GRAYBOX=HERE.parent/'QingxiHuntGraybox_blockout.blend';LAYOUT=HERE.parents[1]/'layout.json'
REPO=HERE.parents[4];ART=REPO/'art/authored/qingxi-hunt/v001';DONDON=REPO/'art/incoming/dondon'
OUT=HERE/'QingxiHuntGraybox_art_v001.blend';RENDERS=HERE/'renders';RENDERS.mkdir(parents=True,exist_ok=True)
D=json.loads(LAYOUT.read_text(encoding='utf-8'));M={m['name']:m for m in D['markers']}
def XY(name):p=M[name]['position'];return Vector((p['x'],p['z']))

bpy.ops.wm.open_mainfile(filepath=str(GRAYBOX));S=bpy.context.scene;O=bpy.data.objects
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))   # from here on only the new file is written
G=next(o for o in O if o.name.startswith('Ground_'))
from mathutils.bvhtree import BVHTree
GB=BVHTree.FromPolygons([G.matrix_world@v.co for v in G.data.vertices],[list(p.vertices) for p in G.data.polygons])
def gz(x,y):h=GB.ray_cast(Vector((x,y,60)),Vector((0,0,-1)),120);return h[0].z if h[0] else 0.

ARTCOL=bpy.data.collections.new('70_Art_v001_ScaleTrial');S.collection.children.link(ARTCOL)
def load_meshes(blend,names):
    with bpy.data.libraries.load(str(blend),link=False) as (src,dst):dst.objects=names
    objs=list(dst.objects)
    for o in objs:
        for slot in o.material_slots:   # appended relative texture paths: point them at the batch on disk
            for n in (slot.material.node_tree.nodes if slot.material and slot.material.node_tree else []):
                if n.type=='TEX_IMAGE' and n.image and not Path(bpy.path.abspath(n.image.filepath)).is_file():
                    n.image.filepath=str(ART/'textures'/Path(n.image.filepath.replace('\\','/')).name);n.image.reload()
    return objs
LOW,LOW1=load_meshes(ART/'models/LowGrass.blend',['SM_LowGrass_LOD0','SM_LowGrass_LOD1'])
TRAMP,=load_meshes(ART/'models/TrampledGrass.blend',['SM_TrampledGrass_LOD0'])
BANK,COL=load_meshes(ART/'models/StreamBank.blend',['SM_StreamBank_LOD0','COL_StreamBank'])
PLACED=[]
def inst(src,name,x,y,yaw=0.,s=1.,z=None,col=ARTCOL,dz=0.):
    o=src.copy();o.name=name;col.objects.link(o);o.location=(x,y,(gz(x,y) if z is None else z)+dz);o.rotation_euler=(0,0,yaw);o.scale=(s,s,s)
    PLACED.append({'object':name,'source':src.name,'blender_xy':[round(x,2),round(y,2)],'yaw_deg':round(math.degrees(yaw),1),'scale':round(s,3),'z_offset':dz})
    return o

rng=random.Random(2026)
# low grass: cover around every flee point and loose tufts near each rabbit spawn
for m in [n for n in M if M[n]['kind']=='flee']:
    c=XY(m)
    for k in range(14):
        a=rng.uniform(0,2*math.pi);r=rng.uniform(1.2,5.);inst(LOW,f'LowGrass_{m[-3:]}_{k}',c.x+r*math.cos(a),c.y+r*math.sin(a),rng.uniform(0,6.28),rng.uniform(.85,1.25))
for m in [n for n in M if M[n]['kind']=='rabbit']:
    c=XY(m)
    for k in range(8):
        a=rng.uniform(0,2*math.pi);r=rng.uniform(2.,6.);inst(LOW,f'LowGrass_{m[-3:]}_{k}',c.x+r*math.cos(a),c.y+r*math.sin(a),rng.uniform(0,6.28),rng.uniform(.85,1.25))
# loose LOD1 tufts across the rabbit slope, off the route centre lines, markers and boxes (low grass keeps rabbits visible)
segs=[(Vector((a['x'],a['z'])),Vector((b['x'],b['z']))) for r in D['routes'] if r['name'] in ('MainDiscovery','AlternativeReturn','HerdConnector') for a,b in zip(r['points'],r['points'][1:])]
def seg_d(p):return min((a+(b-a)*max(0,min(1,(p-a).dot(b-a)/(b-a).length_squared))-p).length for a,b in segs)
z_=next(z for z in D['zones'] if z['name']=='RabbitSlope');cx,cz=z_['center']['x'],z_['center']['z'];n_=0
for k in range(700):
    p=Vector((cx+rng.uniform(-.5,.5)*z_['width'],cz+rng.uniform(-.5,.5)*z_['depth']))
    if seg_d(p)<2.5 or any((XY(m)-p).length<1.5 for m in M if M[m]['kind'] not in ('boundary','cameraBlocker')):continue
    if any(abs(p.x-o['position']['x'])<o['size']['x']/2+1 and abs(p.y-o['position']['z'])<o['size']['z']/2+1 for o in D['obstacles']):continue
    inst(LOW1,f'LowGrassLOD1_{n_}',p.x,p.y,rng.uniform(0,6.28),rng.uniform(.8,1.3));n_+=1
    if n_>=220:break
# trampled grass on each footprint clue, long side along the main route
main=[Vector((p['x'],p['z'])) for p in next(r for r in D['routes'] if r['name']=='MainDiscovery')['points']]
def route_dir(p):
    best=None
    for a,b in zip(main,main[1:]):
        ab=b-a;t=max(0,min(1,(p-a).dot(ab)/ab.length_squared));d=(a+ab*t-p).length
        if best is None or d<best[0]:best=(d,ab.normalized())
    return best[1]
for i in range(1,7):
    n=f'TrailClue_{i:02}';c=XY(n);d=route_dir(c);inst(TRAMP,f'TrampledGrass_{n[-2:]}',c.x+.9,c.y,math.atan2(d.y,d.x))
# stream banks: low edge (front, -Y) at the shallow-water edge where the alternative return enters and leaves the water
for name,x,y,yaw in [('North_RouteEntry',155,62,0.),('West_RouteExit',118,32,math.pi/2),('South_Side',140,28,math.pi)]:
    # sunk 0.30 m: the back edge (0.33 m) meets the flat graybox ground instead of standing up as a step; a carved stream bed is art-pass work
    inst(BANK,'StreamBank_'+name,x,y,yaw,dz=-.30);c=inst(COL,'COL_StreamBank_'+name,x,y,yaw,dz=-.30);c.display_type='WIRE';c.hide_render=True

# scale references (static first frame): chibi players and the rabbit
def append_col(blend,col_name):
    with bpy.data.libraries.load(str(blend),link=False) as (src,dst):dst.collections=[col_name]
    c=dst.collections[0];ARTCOL.children.link(c);return c
def append_rabbit():
    with bpy.data.libraries.load(str(DONDON/'QMountainRabbit/v002/QMountainRabbit_v002.blend'),link=False) as (src,dst):dst.objects=list(src.objects)
    keep=[o for o in dst.objects if o and o.type not in ('CAMERA','LIGHT')]
    for o in keep:ARTCOL.objects.link(o)
    for o in [o for o in dst.objects if o and o.type in ('CAMERA','LIGHT')]:bpy.data.objects.remove(o)
    return next(o for o in keep if o.name.startswith('QMountainRabbit_ROOT'))
def copy_tree(root):
    def rec(o,parent):
        c=o.copy();ARTCOL.objects.link(c);c.parent=parent
        for md in getattr(c,'modifiers',[]):   # skinned parts must follow the copied armature, not the original
            if md.type=='ARMATURE' and md.object is root:md.object=new_root[0]
        for ch in o.children:rec(ch,c)
        return c
    new_root=[None];new_root[0]=root.copy();ARTCOL.objects.link(new_root[0])
    for ch in root.children:rec(ch,new_root[0])
    return new_root[0]
pc=append_col(DONDON/'QPlayerMale/v006/QPlayerMale_v006.blend','01_Editable_Asset')
PLAYER=next(o for o in pc.all_objects if o.type=='ARMATURE')
RAB=append_rabbit()
def put(root,x,y,yaw):root.location=(x,y,gz(x,y));root.rotation_euler=(0,0,yaw)
for o in O:   # the capsule proxies at player / rabbit spawns would stand inside the references
    if o.name.endswith('_proxy') and o.parent and o.parent.get('kind') in ('player','rabbit'):o.hide_render=True

# lineup on flat ground (Unity x 60-75, z 140), 1 m posts for reading heights
LX,LY=60.,145.
put(PLAYER,LX,LY,0.)
put(RAB,LX+2.,LY,0.)
inst(LOW,'Lineup_LowGrass',LX+4.,LY);inst(TRAMP,'Lineup_TrampledGrass',LX+6.5,LY);inst(BANK,'Lineup_StreamBank',LX+11.,LY+1.,math.pi/2)
post_m=bpy.data.materials.new('RulerPost');post_m.diffuse_color=(.9,.2,.15,1);post_m.use_nodes=True
next(n for n in post_m.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'].default_value=(.8,.08,.05,1)
white=bpy.data.materials.new('RulerWhite');white.use_nodes=True;next(n for n in white.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'].default_value=(.95,.95,.92,1)
bm=bmesh.new()
for x in (LX-1.5,LX+14.):
    for k in range(2):   # 2 m post, alternating 0.25 m red/white bands
        for j in range(4):
            bmesh.ops.create_cube(bm,size=1.,matrix=Matrix.LocRotScale(Vector((x,LY,gz(x,LY)+k+j*.25+.125)),None,Vector((.06,.06,.25))))
me=bpy.data.meshes.new('RulerPosts');bm.to_mesh(me);bm.free();me.materials.append(post_m);me.materials.append(white)
for i,p in enumerate(me.polygons):p.material_index=(i//6)%2
ro=bpy.data.objects.new('RulerPosts_2m',me);ARTCOL.objects.link(ro)

# second player + rabbits in the field views
P2=copy_tree(PLAYER);R2=copy_tree(RAB);R3=copy_tree(RAB);P3=copy_tree(PLAYER);P4=copy_tree(PLAYER)
a01=XY('RabbitSpawn_A01');put(P2,a01.x-4.,a01.y-5.,math.atan2(4.,-5.)-math.pi)
put(R2,a01.x,a01.y,.6)
t1=XY('TrailClue_01');put(P3,t1.x-1.4,t1.y-1.6,-.6);put(R3,t1.x+2.2,t1.y+1.,2.)
put(P4,155.,61.,math.pi)   # on the sunk north bank, which now meets the ground; facing the water

# ------------------------------------------------------------------ cameras and renders
for o in O:   # map-reading helpers from the graybox build (labels, rings, zone outlines) are not part of the scene
    if o.name.startswith(('Label_','ZoneLabel_','Ring_','ZoneOutline_')):o.hide_render=True
def cam(name,loc,look,lens=None,ortho=None):
    cd=bpy.data.cameras.new(name);c=bpy.data.objects.new(name,cd);ARTCOL.objects.link(c);c.location=loc
    c.rotation_euler=(Vector(look)-Vector(loc)).to_track_quat('-Z','Y').to_euler();cd.clip_start=.05;cd.clip_end=400
    if ortho:cd.type='ORTHO';cd.ortho_scale=ortho
    else:cd.sensor_fit='VERTICAL';cd.angle_y=math.radians(lens or 45)
    return c
z0=gz(LX,LY)
VIEWS=[('01_lineup_front_ortho',cam('Cam_LineupOrtho',(LX+6.,LY-30.,z0+1.),(LX+6.,LY,z0+1.),ortho=17.5),(1800,700)),
       ('02_lineup_perspective',cam('Cam_LineupPersp',(LX+2.,LY-9.,z0+3.6),(LX+6.,LY+.5,z0+.3),lens=40),(1600,900)),
       ('03_meadow_third_person',cam('Cam_Meadow',(a01.x-8.,a01.y-10.,gz(a01.x-8,a01.y-10)+3.6),(a01.x-1.,a01.y-1.,gz(a01.x,a01.y)+.4),lens=50),(1600,900)),
       ('04_trail_clue_T01',cam('Cam_Clue',(t1.x+5.,t1.y-4.,gz(t1.x,t1.y)+2.6),(t1.x+.6,t1.y,gz(t1.x,t1.y)+.2),lens=45),(1600,900)),
       ('05_bank_side_profile',cam('Cam_BankSide',(146.,62.,.9),(155.,62.,.35),lens=30),(1600,900)),
       ('06_bank_route_entry',cam('Cam_BankEntry',(150.,70.,4.),(155.,59.,.2),lens=50),(1600,900)),
       ('07_meadow_overview',cam('Cam_MeadowHigh',(125.,72.,32.),(145.,108.,1.),lens=45),(1600,900))]
for eng in ('BLENDER_EEVEE_NEXT','BLENDER_EEVEE'):
    try:S.render.engine=eng;break
    except TypeError:pass
try:S.eevee.taa_render_samples=48
except AttributeError:pass
S.render.image_settings.file_format='PNG'
for name,c,(w,h) in VIEWS:
    S.camera=c;S.render.resolution_x,S.render.resolution_y=w,h;S.render.filepath=str(RENDERS/f'{name}.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
(HERE/'placement.json').write_text(json.dumps({'note':'Visual scale trial only; layout.json is unchanged and remains the coordinate source.',
    'art_batch':'art/authored/qingxi-hunt/v001','instances':PLACED,'renders':[v[0]+'.png' for v in VIEWS]},ensure_ascii=False,indent=1),encoding='utf-8')
print('PLACED',len(PLACED),'renders',len(VIEWS))
