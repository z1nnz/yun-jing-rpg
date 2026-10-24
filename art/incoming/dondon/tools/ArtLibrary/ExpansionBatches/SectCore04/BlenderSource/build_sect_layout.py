"""Assemble copies of the six sect modules; never modify their sources."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Models/SectLayout/v001'
assert not (OUT/'SectLayout_v001.blend').exists(),'Existing layout retained; use a new version.'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
placement={'SectGate':(0,-15,0),'SectGrandHall':(0,13,0),'DiscipleResidence':(-11,0,0),'TrainingGround':(11,-3,0),'SpiritHerbGarden':(-11,12,0),'CultivationPlatform':(10,12,0)}
records=[];asset_objects=[]
for aid,pos in placement.items():
    source=ROOT/'Models'/aid/'v001'/f'{aid}_v001.blend'
    with bpy.data.libraries.load(str(source),link=False) as (a,b):b.collections=['01_Editable_Asset']
    col=b.collections[0];col.name=aid;scene.collection.children.link(col)
    root=next(o for o in col.objects if o.type=='EMPTY' and o.name.startswith(aid+'_ROOT'))
    root.location=pos;asset_objects.extend(list(col.objects))
    records.append({'asset':aid,'source':str(source.relative_to(ROOT)),'position_m':pos})
dressing=bpy.data.collections.new('80_Layout_Terrain_and_Paths');scene.collection.children.link(dressing)
def mat(name,c):
    m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);m.use_nodes=True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*c,1)
    m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.85
    return m
ground=mat('Sage_Ground',(.19,.235,.155));stone=mat('Path_Stone',(.40,.44,.42));edge=mat('Border_Stone',(.25,.30,.29))
def box(name,p,s,m):
    bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=bpy.context.object;o.name=name;o.dimensions=s
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for c in list(o.users_collection):c.objects.unlink(o)
    dressing.objects.link(o);o.data.materials.append(m)
    mod=o.modifiers.new('Edge_Soften','BEVEL');mod.width=.025;mod.segments=2
    asset_objects.append(o);return o
box('Campus_Terrain',(0,1,-.18),(37,42,.36),ground)
def path(a,b,w=2.4):
    return {'from':list(a),'to':list(b),'width_m':w}
routes=[path((0,-12,0),(0,7,0),3.2),path((0,-6,0),(-11,-6,0)),path((-11,-6,0),(-11,-4,0)),path((0,-9,0),(11,-9,0)),path((11,-9,0),(11,-7,0)),path((0,6,0),(-11,6,0)),path((-11,6,0),(-11,9.6,0)),path((0,6,0),(10,6,0)),path((10,6,0),(10,9,0))]
# One shared paving grid, so intersections never stack coincident surfaces.
for ix in range(-20,21):
    for iy in range(-20,21):
        x,y=ix*.8,iy*.8
        def inside(r):
            a,b=r['from'],r['to'];half=r['width_m']/2
            if abs(a[0]-b[0])<.001:return abs(x-a[0])<half and min(a[1],b[1])-.4<=y<=max(a[1],b[1])+.4
            return abs(y-a[1])<half and min(a[0],b[0])-.4<=x<=max(a[0],b[0])+.4
        if any(inside(r) for r in routes):box('Walkway_Paver',(x,y,.035),(.775,.775,.07),stone)
bpy.context.view_layer.update()
studio=bpy.data.collections.new('90_Studio_Not_Exported');scene.collection.children.link(studio)
def obj(name,data):
    o=bpy.data.objects.new(name,data);studio.objects.link(o);return o
cam=obj('Campus_Camera',bpy.data.cameras.new('Campus_Camera'));scene.camera=cam;cam.data.type='ORTHO';cam.data.clip_end=500;cam.data.ortho_scale=53
target=Vector((0,1,1.7))
for name,p,power,size in [('Key',(-18,-22,32),110000,22),('Fill',(22,-6,24),70000,20),('Rim',(0,24,30),90000,18)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power*.35;d.size=size;o=obj(name,d);o.location=p;o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
scene.world=bpy.data.worlds.new('Campus_World');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.19,.21,.22,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.65
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.resolution_x=1400;scene.render.resolution_y=1400;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
def pose(p,scale):
    cam.location=p;cam.data.ortho_scale=scale;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
pose((35,-44,42),58)
bpy.ops.object.select_all(action='DESELECT')
for o in asset_objects:o.select_set(True)
bpy.context.view_layer.objects.active=asset_objects[0]
bpy.ops.export_scene.fbx(filepath=str(OUT/'SectLayout_v001.fbx'),use_selection=True,object_types={'MESH','EMPTY'},add_leaf_bones=False,axis_forward='-Z',axis_up='Y',apply_unit_scale=True,bake_anim=False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'SectLayout_v001.blend'))
for name,p,scale in [('01_campus_overview',(35,-44,42),58),('02_campus_top',(0,1,70),46),('03_campus_front',(26,-42,24),55)]:
    pose(p,scale);scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True);print('LAYOUT_VIEW',name,flush=True)
(OUT/'layout_info.json').write_text(json.dumps({'asset':'SectLayout','name_zh':'宗門核心配置','units':'meters','placements':records,'routes':routes,'stage':'Static editable campus layout; paths are visual guides, not validated navigation or collision.','unreal_import_verified':False,'preview_count':3},ensure_ascii=False,indent=2))
print('LAYOUT_COMPLETE',flush=True)
