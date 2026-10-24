"""MountainSanctuary v003: v002 (ascent route) with solid mesh clouds instead of volume fog.
Source v002 is read-only. Clouds sit at valley/mountain-waist height and avoid the route and sect.
Blender CLI: blender -b -P this.py [-- preview]   (preview: overview render only, no FBX)
"""
import bpy,json,sys,os
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
PREVIEW='--' in sys.argv and 'preview' in sys.argv[sys.argv.index('--'):]
from build_solid_clouds_v002 import solid_cloud
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[2]
OUT=ROOT/'Models/MountainSanctuary/v003';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(PROJECT/'Models/MountainSanctuary/v002/MountainSanctuary_v002.blend'))
s=bpy.context.scene;s.frame_set(1);bpy.context.preferences.filepaths.save_version=0

removed=[o.name for o in s.objects if o.get('effect_type')]
for name in removed:
    o=bpy.data.objects[name];m=o.data;bpy.data.objects.remove(o);bpy.data.meshes.remove(m)
s.cycles.volume_bounces=0

clouds=bpy.data.collections.new('50_Solid_Clouds');s.collection.children.link(clouds)
# name, center, size (x,y,z m), seed, phase
LAYOUT=[
    ('Cloud_West_Peak_Collar',(-68,56,56),(84,72,11),11,0),
    ('Cloud_East_Peak_Collar',(62,66,40),(74,68,10),12,1),
    ('Cloud_Ridge_Band',(0,132,50),(180,34,12),13,2),
    ('Cloud_North_Saddle',(0,82,30),(90,26,13),19,2.5),
    ('Cloud_West_Valley',(-84,-2,22),(50,40,15),14,3),
    ('Cloud_East_Flank',(72,-18,20),(48,64,15),15,4),
    ('Cloud_East_Front_Low',(48,-98,14),(60,40,14),16,5),
    ('Cloud_Southwest_Low',(-112,-92,14),(50,40,13),17,1.5),
    ('Cloud_Far_Front_Sea',(10,-178,8),(130,40,11),18,3.5),
]
for name,loc,size,seed,phase in LAYOUT:
    solid_cloud(name,loc,size,seed=seed,phase=phase,puffs=26,drift=2,collection=clouds)
bpy.context.view_layer.update()

def box(objs,pad=0):
    lo=Vector((1e9,)*3);hi=-lo
    for o in objs:
        if o.type!='MESH':continue
        for c in o.bound_box:
            p=o.matrix_world@Vector(c);lo=Vector(map(min,lo,p));hi=Vector(map(max,hi,p))
    return lo-Vector((pad,)*3),hi+Vector((pad,)*3)
def overlap(a,b):return all(a[0][i]<b[1][i] and b[0][i]<a[1][i] for i in range(3))
keep_clear={'60_Mountain_Ascent':box(bpy.data.collections['60_Mountain_Ascent'].all_objects,4),
            'Sect_v003':(Vector((-22,-31,47)),Vector((22,31,60)))}
for o in clouds.objects:
    for k,b in keep_clear.items():assert not overlap(box([o]),b),(o.name,'blocks',k)

overview=s.objects['04_Ascent_Overview']
s.camera=overview;s.render.resolution_x=1440;s.render.resolution_y=1080;s.cycles.samples=16
if PREVIEW:
    s.render.filepath=str(OUT/'01_ascent_overview.png');bpy.ops.render.render(write_still=True);print('PREVIEW_DONE',flush=True);sys.exit()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'MountainSanctuary_v003.blend'))
views=[('01_ascent_overview','04_Ascent_Overview',1440,1080),('02_bridge_and_gate','05_Bridge_And_Gate',1440,1080),('03_mountain_overview','01_Mountain_Overview',1440,1080),('04_summit_approach','02_Summit_Approach',1440,1080)]
for fname,cname,w,h in views:
    s.camera=s.objects[cname];s.render.resolution_x=w;s.render.resolution_y=h;s.render.filepath=str(OUT/(fname+'.png'));bpy.ops.render.render(write_still=True);print('SCENE_VIEW',fname,flush=True)
s.frame_set(1)
def export(path,objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:o.select_set(True)
    bpy.context.view_layer.objects.active=objs[0]
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},bake_anim=False,add_leaf_bones=False,axis_forward='-Z',axis_up='Y')
meshes=[o for o in s.objects if o.type=='MESH']
export(OUT/'MountainSanctuary_v003.fbx',meshes)
export(OUT/'SolidClouds_v003.fbx',list(clouds.objects))
(OUT/'scene_info.json').write_text(json.dumps({'scene':'MountainSanctuary','version':'v003','source_scene':'MountainSanctuary/v002','removed_volume_fog':removed,'solid_clouds':[n for n,*_ in LAYOUT],
  'cloud_method':'metaball-derived solid meshes; 96-frame looping object drift in .blend','fbx':'static geometry including solid clouds; SolidClouds_v003.fbx holds clouds alone',
  'clouds_clear_of':['60_Mountain_Ascent (4 m margin, bounding boxes)','sect area above 47 m'],'previews':len(views),
  'limitations':['Mist/haze should come from the engine (e.g. Unreal Exponential Height Fog)','Cloud drift animation is not exported to FBX','No collision, LOD or UV baking']},indent=2,ensure_ascii=False))
print('SANCTUARY_V003_COMPLETE',flush=True)
