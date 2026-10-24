"""Furnished non-character cutaway assembly. Originals are read only; no player model."""
import bpy,json,math,hashlib,importlib.util
from pathlib import Path
from mathutils import Vector,Matrix
BATCH=Path(__file__).resolve().parents[1];ROOT=BATCH.parents[2]
spec=importlib.util.spec_from_file_location('nonchar',Path(__file__).with_name('continue_noncharacter.py'));nc=importlib.util.module_from_spec(spec);spec.loader.exec_module(nc)
V=nc.SCENE_VERSION
OUT=BATCH/'Scenes/QCaveResidence'/V;REF=BATCH/'Previews'/('CaveResidence_'+V)
if (OUT/('QCaveResidence_'+V+'.blend')).exists():raise RuntimeError('Scene exists; use a new version.')
OUT.mkdir(parents=True,exist_ok=True);REF.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
placed=[];all_meshes=[]
catalog=json.loads((ROOT/'ArtLibrary/asset_catalog.json').read_text(encoding='utf-8'));byid={e['id']:e for e in catalog['entries']}

def source(aid):
    if aid in nc.ALLOWED:
        v=nc.VERSIONS[aid];return BATCH/'Models'/aid/v/(aid+'_'+v+'.blend')
    return (ROOT/'ArtLibrary'/byid[aid]['blend']).resolve()

def append(aid,pos=(0,0,0),scale=(1,1,1),yaw=0,open_door=False):
    p=source(aid);before=nc.sha(p)
    with bpy.data.libraries.load(str(p),link=False) as (a,b):b.objects=list(a.objects)
    loaded=[o for o in b.objects if o]
    collection=bpy.data.collections.new('Instance_'+aid+'_'+str(len(placed)));s.collection.children.link(collection)
    for o in loaded:collection.objects.link(o)
    s.frame_set(60 if open_door else 1);bpy.context.view_layer.update()
    obs=[o for o in loaded if o.type=='MESH' and not o.hide_render and not any(c.name.startswith(('80_','90_','91_','92_')) for c in o.users_collection)]
    assert obs,aid
    lo,hi=nc.bounds(obs);offset=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
    # Door open placement must retain the CLOSED rest-pose origin.
    if open_door:offset=Vector((0,0,0))
    transform=Matrix.Translation(Vector(pos))@Matrix.Rotation(yaw,4,'Z')@Matrix.Diagonal((*scale,1))@Matrix.Translation(-offset)
    dg=bpy.context.evaluated_depsgraph_get();copies=[]
    for o in obs:
        e=o.evaluated_get(dg);d=bpy.data.meshes.new_from_object(e,depsgraph=dg)
        ob=bpy.data.objects.new(aid+'_'+o.name,d);collection.objects.link(ob);ob.matrix_world=transform@e.matrix_world;copies.append(ob)
    for o in loaded:bpy.data.objects.remove(o,do_unlink=True)
    s.frame_set(1);bpy.context.view_layer.update();all_meshes.extend(copies)
    assert nc.sha(p)==before
    placed.append({'asset':aid,'source':str(p.relative_to(ROOT)),'source_sha256':before,'position_m':list(pos),'scale':list(scale),'yaw_rad':yaw,'open_door':open_door,'mesh_objects':len(copies)})
    return copies

# Eight-metre square floor, full back wall, low side walls for a clear cutaway.
for x in (-1.98,1.98):
    for y in (-1.98,1.98):append('QCaveFloor',(x,y,0))
for x in (-2,2):append('QCaveWall',(x,4,.20))
for y in (-2,2):
    append('QCaveWall',(-4,y,.20),scale=(1,1,.38),yaw=math.pi/2)
    append('QCaveWall',(4,y,.20),scale=(1,1,.38),yaw=math.pi/2)
append('QCaveEntrance',(0,-4,.20));append('QCaveDoor',(0,-4.03,.31),open_door=True)
append('DiscipleBed',(-2.65,2.2,.20))
append('StorageChest',(-2.65,-.35,.20))
append('SmithWorkbench',(2.5,2.3,.20))
append('AlchemyFurnace',(2.65,-.3,.20))
append('MeditationCushion',(0,1.4,.20))
append('SpiritHerbGarden',(6.3,.2,0),scale=(.60,.60,.60))
append('QQiManual',(2.1,2.25,1.18))
append('QPillBottle',(2.68,2.22,1.18))
append('QSpiritStone',(2.9,2.25,1.18))
append('QAptitudeCrystal',(2.0,-4.8,0))
append('QMountainRabbit',(-3.0,-4.7,0))
append('QMountainBoar',(-1.8,-5.0,0),yaw=-.3)

# Context ground is a scene-only support, not an independently counted asset.
bpy.ops.mesh.primitive_cube_add(size=1,location=(1.0,-.4,-.14));ground=bpy.context.object;ground.name='Scene_support_not_independent_asset';ground.scale=(15,12,.28)
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
m=bpy.data.materials.new('Garden_ground');m.diffuse_color=(.16,.23,.13,1);m.use_nodes=True
m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.16,.23,.13,1);m.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.95;ground.data.materials.append(m)
mod=ground.modifiers.new('Soft_support_edges','BEVEL');mod.width=.15;mod.segments=3
all_meshes.append(ground)
cam,center,size=nc.lighting(all_meshes);s.cycles.samples=16
nc.position(cam,center,size,(1,-1.5,1.3))
bpy.ops.object.select_all(action='DESELECT')
for o in all_meshes:o.select_set(True)
bpy.context.view_layer.objects.active=ground
bpy.ops.export_scene.fbx(filepath=str(OUT/('QCaveResidence_'+V+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',bake_anim=False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/('QCaveResidence_'+V+'.blend')))
records=[]
directions=[('01_front',(0,-1,.6)),('02_right',(1,0,.7)),('03_rear',(0,1,.7)),('04_left',(-1,0,.7)),('05_front_right',(1,-1.5,1.3)),('06_rear_right',(1,1,1)),('07_rear_left',(-1,1,1)),('08_front_left',(-1,-1.5,1.3)),('09_top',(0,0,1)),('10_high_front',(0,-1,1.5))]
for name,dr in directions:
    nc.position(cam,center,size,dr);s.render.filepath=str(REF/(name+'.png'));bpy.ops.render.render(write_still=True)
    records.append({'file':name+'.png','direction':dr});print('CAVE_VIEW',name,flush=True)
(REF/'views.json').write_text(json.dumps({'scene':'QCaveResidence','source':str((OUT/('QCaveResidence_'+V+'.blend')).relative_to(ROOT)),'views':records,'not_independent_asset_views':True},indent=2),encoding='utf-8')
info={'scene':'QCaveResidence','stage':'furnished_cutaway_layout_prototype','instances':placed,'independent_new_assets_added':0,
      'character_assets_used':False,'door_pose':'open; baked static for layout','cutaway':'No ceiling; side walls at 38% height; open front sides',
      'original_furniture_scale':1.0,'garden_instance_scale':.6,'source_files_unchanged':True,
      'limits':['Layout only, not enclosed playable cave','No collision/navigation or UE acceptance','No character scale or interaction tests'],
      'version':V,'blend_sha256':nc.sha(OUT/('QCaveResidence_'+V+'.blend')),'fbx_sha256':nc.sha(OUT/('QCaveResidence_'+V+'.fbx'))}
(OUT/'model_info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
print('CAVE_PREVIEW_COMPLETE',flush=True)
