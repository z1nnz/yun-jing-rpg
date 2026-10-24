"""Extract eight existing components non-destructively, normalize, export and render.
Blender -b -t 4 --python extract_props.py [-- --project /path/to/強悍修仙2.0]
"""
import bpy,json,math,sys,argparse,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
from bpy_extras.object_utils import world_to_camera_view
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--project',default='/Users/joshmac/強悍修仙2.0');parser.add_argument('--only',nargs='*')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
PROJECT=Path(args.project)
SOURCES={'town':'Models/SpawnTown/v001/SpawnTown_v001.blend','smith':'Models/Blacksmith/v001/Blacksmith_v001.blend'}
SPECS={
 'StoneLantern':('石燈','town',lambda o:o.name.startswith('Lower_Left_'),Matrix.Identity(4)),
 'TownWaymarker':('指路碑','town',lambda o:o.name.startswith('Waymarker_'),Matrix.Identity(4)),
 'TownBench':('長凳','town',lambda o:o.name.startswith(('Bench_Seat_-3.65','Bench_Support_-3.65_')),Matrix.Rotation(math.pi/2,4,'Z')),
 'SmithAnvil':('鐵砧與底座','smith',lambda o:o.parent and o.parent.name=='Anvil_Station_ROOT',Matrix.Identity(4)),
 'SmithWorkbench':('工作台','smith',lambda o:o.name.startswith('Workbench_') and o.type=='MESH',Matrix.Identity(4)),
 'QuenchBarrel':('淬火桶','smith',lambda o:o.parent and o.parent.name=='Quench_Barrel_ROOT',Matrix.Identity(4)),
 'WeaponDisplayRack':('武器架','smith',lambda o:o.name.startswith('Rack_'),Matrix.Identity(4)),
 'SmithHammer':('鐵鎚','smith',lambda o:o.name.startswith('Hammer_'),Matrix.Rotation(-math.pi/2,4,'Y')@Matrix.Rotation(-math.atan2(.18,.70),4,'Z'))}
VIEWS=[('01_front',(0,-1,0)),('02_right',(1,0,0)),('03_rear',(0,1,0)),('04_left',(-1,0,0)),('05_front_right',(1,-1,.45)),('06_rear_right',(1,1,.45)),('07_rear_left',(-1,1,.45)),('08_front_left',(-1,-1,.45)),('09_top',(0,0,1)),('10_high_front',(0,-1,1))]
before={str(PROJECT/p):hashlib.sha256((PROJECT/p).read_bytes()).hexdigest() for p in SOURCES.values()}
for aid,(name,src,select,rotation) in SPECS.items():
 if args.only and aid not in args.only:continue
 out=ROOT/'Models'/aid/'v001';refs=ROOT/'ArtLibrary/Turnarounds'/f'{aid}_v001'
 if (refs/'views.json').exists():print('SKIP_COMPLETE',aid,flush=True);continue
 out.mkdir(parents=True,exist_ok=True);refs.mkdir(parents=True,exist_ok=True)
 source=PROJECT/SOURCES[src];bpy.ops.wm.open_mainfile(filepath=str(source));scene=bpy.context.scene
 objects=[o for o in scene.objects if o.type=='MESH' and select(o)]
 assert objects,(aid,'no components selected')
 source_names=[o.name for o in objects]
 # Keep mesh data, materials and modifiers; remove only other objects in this in-memory copy.
 for o in objects:
  mw=o.matrix_world.copy();o.parent=None;o.matrix_world=rotation@mw
 for o in list(bpy.data.objects):
  if o not in objects:bpy.data.objects.remove(o,do_unlink=True)
 assets=bpy.data.collections.new('01_Editable_Asset');scene.collection.children.link(assets)
 for o in objects:
  for c in list(o.users_collection):c.objects.unlink(o)
  assets.objects.link(o)
 for c in list(bpy.data.collections):
  if c!=assets:bpy.data.collections.remove(c)
 root=bpy.data.objects.new(aid+'_ROOT',None);assets.objects.link(root)
 root['stage']='Extracted appearance prototype; no UV bake, collision, LOD or Unreal validation'
 for o in objects:o.parent=root
 bpy.context.view_layer.update()
 def points():
  dg=bpy.context.evaluated_depsgraph_get()
  return [e.matrix_world@Vector(p) for o in objects for e in [o.evaluated_get(dg)] for p in e.bound_box]
 def bounds():
  pts=points();return Vector([min(p[i] for p in pts) for i in range(3)]),Vector([max(p[i] for p in pts) for i in range(3)])
 lo,hi=bounds();shift=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
 for o in objects:o.location-=shift
 bpy.context.view_layer.update();lo,hi=bounds();extent=hi-lo;centre=(lo+hi)/2
 scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
 studio=bpy.data.collections.new('90_Studio_Not_Exported');scene.collection.children.link(studio)
 def studio_obj(name,data):
  o=bpy.data.objects.new(name,data);studio.objects.link(o);return o
 camera=studio_obj('Reference_Camera',bpy.data.cameras.new('Reference_Camera'));scene.camera=camera
 camera.data.type='ORTHO';camera.data.ortho_scale=extent.length*1.16;camera.data.clip_start=.001;camera.data.clip_end=1000
 for n,pos,power,size in [('Key',(-3,-4,6),750,4),('Fill',(4,-1,3),450,4),('Rim',(0,4,5),650,3)]:
  d=bpy.data.lights.new(n,'AREA');d.energy=power;d.shape='DISK';d.size=size
  o=studio_obj(n,d);o.location=centre+Vector(pos);o.rotation_euler=(centre-o.location).to_track_quat('-Z','Y').to_euler()
 scene.world=bpy.data.worlds.new('Neutral_Studio');scene.world.use_nodes=True
 bg=scene.world.node_tree.nodes['Background'];bg.inputs[0].default_value=(.19,.21,.20,1);bg.inputs[1].default_value=.7
 scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16;scene.cycles.use_denoising=True
 scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
 scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False;scene.view_settings.view_transform='AgX'
 # Clear original scene compositing and output overrides.
 scene.use_nodes=False;scene.render.use_border=False;scene.render.use_crop_to_border=False
 def camera_pose(direction):
  camera.location=centre+Vector(direction).normalized()*camera.data.ortho_scale*2.5
  camera.rotation_euler=(centre-camera.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
 camera_pose((1,-1,.45));bpy.ops.object.select_all(action='DESELECT')
 for o in [root]+objects:o.select_set(True)
 bpy.context.view_layer.objects.active=root
 bpy.ops.export_scene.fbx(filepath=str(out/f'{aid}_v001.fbx'),use_selection=True,object_types={'MESH','EMPTY'},add_leaf_bones=False,axis_forward='-Z',axis_up='Y',apply_unit_scale=True,bake_anim=False)
 bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(out/f'{aid}_v001.blend'))
 info={'asset':aid,'name_zh':name,'stage':'extracted_appearance_prototype','source_blend':SOURCES[src],'source_sha256':before[str(source)],'source_objects':source_names,'rotation_matrix_from_source':[list(r) for r in rotation],'units':'meters','front':'-Y','dimensions_m':list(extent),'mesh_objects':len(objects),'uv_baked':False,'collision_ready':False,'lod_ready':False,'unreal_import_verified':False}
 (out/'model_info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2))
 records=[]
 for view,direction in VIEWS:
  camera_pose(direction);projections=[world_to_camera_view(scene,camera,p) for p in points()]
  assert all(.005<p.x<.995 and .005<p.y<.995 and p.z>0 for p in projections),(aid,view,'cropped')
  scene.render.filepath=str(refs/(view+'.png'));bpy.ops.render.render(write_still=True)
  records.append({'file':view+'.png','direction':direction,'camera_location':list(camera.location),'projection':'orthographic','framing_checked':True})
  print('VIEW_COMPLETE',aid,view,flush=True)
 (refs/'views.json').write_text(json.dumps({'asset':aid,'source':str((out/f'{aid}_v001.blend').relative_to(ROOT)),'same_geometry':True,'views':records},indent=2))
 print('ASSET_COMPLETE',aid,flush=True)
for source,digest in before.items():assert hashlib.sha256(Path(source).read_bytes()).hexdigest()==digest
(ROOT/'source_integrity.json').write_text(json.dumps({'source_blend_files_unchanged':True,'sha256':before},indent=2))
