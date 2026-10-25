"""Export the Qingxi town blockout (yun-jing art/source/qingxi-town-blockout-v1.blend) for the integrated Unity world.

  blender -b art/source/qingxi-town-blockout-v1.blend --python-exit-code 1 --python tools/export-qingxi-town-for-unity.py

Does not save the source .blend. Writes into apps/game/Assets/QingxiWorld/:
  Models/Town/Town_Terrain.fbx, Town_LakeBed.fbx, Town_Water.fbx, Town_Placeholders.fbx, Town_Background.fbx
  Data/town_world.json   asset placements read from the .blend itself, placeholder list, water level, sample heights
The hunt area (220 x 160 m, rotated 180 degrees) sits south-west of the town; terrain and water inside its footprint are
removed, leaving a 2 m overlap at the edge so the two grounds touch. Coordinates stay Blender metres (X east, Y north, Z up).
"""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'apps/game/Assets/QingxiWorld'
(OUT/'Models/Town').mkdir(parents=True,exist_ok=True);(OUT/'Data').mkdir(parents=True,exist_ok=True)
# Hunt area: local (x, z) -> world (HX - x, HY - z), i.e. rotated 180 degrees so its settlement exit faces the town.
HX,HY,HW,HD=-98.,-108.,220.,160.
CUT=(HX-HW,HY-HD,HX-2.,HY-2.)   # x0, y0, x1, y1 of terrain removed (2 m overlap left at the town side)
def in_cut(x,y):return CUT[0]<=x<=CUT[2] and CUT[1]<=y<=CUT[3]

S=bpy.context.scene;O=bpy.data.objects
def col(name):return next(c for c in S.collection.children if c.name==name)
terrain=next(o for o in col('10_Terrain').objects if o.type=='MESH');water=next(o for o in col('20_Water').objects if o.type=='MESH')
wz=[(water.matrix_world@v.co).z for v in water.data.vertices];WATER=sum(wz)/len(wz)

def world_bm(o):
    bm=bmesh.new();bm.from_mesh(o.data);bm.transform(o.matrix_world);return bm
def new_obj(name,bm,mats):
    me=bpy.data.meshes.new(name);bm.to_mesh(me);bm.free()
    for m in mats:me.materials.append(m)
    o=bpy.data.objects.new(name,me);S.collection.objects.link(o);return o

# terrain: drop faces in the hunt footprint, then split the lake bed (all corners under water) from dry ground
bm=world_bm(terrain);bmesh.ops.delete(bm,geom=[f for f in bm.faces if in_cut(*f.calc_center_median().xy)],context='FACES')
bed=bm.copy()
bmesh.ops.delete(bm,geom=[f for f in bm.faces if all(v.co.z<WATER-.25 for v in f.verts)],context='FACES')
bmesh.ops.delete(bed,geom=[f for f in bed.faces if not all(v.co.z<WATER-.25 for v in f.verts)],context='FACES')
T_DRY=new_obj('Town_Terrain',bm,terrain.data.materials);T_BED=new_obj('Town_LakeBed',bed,terrain.data.materials)
# water: original rectangle minus the hunt footprint, as two quads
xs=[(water.matrix_world@v.co).x for v in water.data.vertices];ys=[(water.matrix_world@v.co).y for v in water.data.vertices]
wx0,wx1,wy0,wy1=min(xs),max(xs),min(ys),max(ys);bm=bmesh.new()
def quad(x0,y0,x1,y1):
    if x1<=x0 or y1<=y0:return
    vs=[bm.verts.new((x,y,WATER)) for x,y in ((x0,y0),(x1,y0),(x1,y1),(x0,y1))];bm.faces.new(vs)
quad(wx0,HY,wx1,wy1);quad(HX,wy0,wx1,HY)
T_WATER=new_obj('Town_Water',bm,water.data.materials)

def copies(cname,skip=lambda o:False):
    res=[]
    for o in col(cname).all_objects:
        if o.type!='MESH' or skip(o):continue
        c=o.copy();c.data=o.data.copy();S.collection.objects.link(c);c.matrix_world=o.matrix_world.copy();c.name=o.name.replace('TODO_','');res.append(c)
    return res
PH=copies('40_ToDo_Placeholders',lambda o:in_cut(*o.matrix_world.translation.xy))
BG=copies('50_Background')

def export(objs,name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:o.select_set(True)
    bpy.context.view_layer.objects.active=objs[0]
    bpy.ops.export_scene.fbx(filepath=str(OUT/'Models/Town'/f'{name}.fbx'),use_selection=True,object_types={'MESH'},
        apply_scale_options='FBX_SCALE_ALL',mesh_smooth_type='FACE',use_mesh_modifiers=True,add_leaf_bones=False,bake_anim=False)
export([T_DRY],'Town_Terrain');export([T_BED],'Town_LakeBed');export([T_WATER],'Town_Water');export(PH,'Town_Placeholders');export(BG,'Town_Background')

# placements straight from the .blend instances (not the older layout.json)
GT=BVHTree.FromObject(T_DRY,bpy.context.evaluated_depsgraph_get())
def ground(x,y):
    h=GT.ray_cast(Vector((x,y,500)),Vector((0,0,-1)),1000);return None if h[0] is None else round(h[0].z,3)
placements=[]
for e in col('30_Existing_Assets_Linked').all_objects:
    if e.instance_type!='COLLECTION' or not e.instance_collection:continue
    aid=e.get('asset_id') or e.instance_collection.name.split('_')[1];p=e.matrix_world.translation
    if in_cut(p.x,p.y):continue
    placements.append({'asset':aid,'collection':e.instance_collection.name,'x':round(p.x,3),'y':round(p.y,3),'z':round(p.z,3),
                       'yaw_deg':round(math.degrees(e.matrix_world.to_euler().z),2),'scale':round(e.matrix_world.to_scale().x,4),'role':e.get('role','')})
under=[p for p in placements if p['z']<WATER-.2 and not p['asset'].startswith('Q')]
report={'source':'art/source/qingxi-town-blockout-v1.blend','axes':'Blender metres: X east, Y north, Z up; Unity X = X, Unity Z = Y, Unity Y = Z',
        'water_level':round(WATER,3),'hunt':{'origin_xy':[HX,HY],'rotation_deg':180,'size':[HW,HD],'terrain_cut_xyxy':CUT,
        'note':'hunt local (x, z) maps to world (HX - x, HY - z)'},
        'junction':{'boardwalk_end_xy':[-118.,-112.],'ground_at':{f'{x},{y}':ground(x,y) for x,y in [(-118,-106),(-118,-104),(-110,-100),(-100,-104),(0,25),(0,17),(-3,17)]}},
        'placements':placements,'placeholders':[{'name':o.name,'x':round(o.matrix_world.translation.x,2),'y':round(o.matrix_world.translation.y,2),
        'z':round(o.matrix_world.translation.z,2),'dims':[round(v,2) for v in o.dimensions]} for o in PH],
        'assets_below_water':[(p['asset'],p['x'],p['y'],p['z']) for p in under],
        'tris':{o.name:sum(len(f.vertices)-2 for f in o.data.polygons) for o in (T_DRY,T_BED,T_WATER)}}
(OUT/'Data/town_world.json').write_text(json.dumps(report,ensure_ascii=False,indent=1),encoding='utf-8')
print('TOWN EXPORT water',round(WATER,3),'placements',len(placements),'placeholders',len(PH),'below water',len(under),'ground',report['junction']['ground_at'])
