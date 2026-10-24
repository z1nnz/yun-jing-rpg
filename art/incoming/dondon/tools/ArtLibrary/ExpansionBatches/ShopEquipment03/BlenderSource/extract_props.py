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
SOURCES={'shop':'Models/MaterialShop/v001/MaterialShop_v001.blend','smith':'Models/Blacksmith/v001/Blacksmith_v001.blend'}
SPECS={
 'BasicSword01':('基礎法劍','smith',lambda o:o.parent and o.parent.name=='Display_Sword_1_ROOT',Matrix.Identity(4)),
 'SmithTongs':('火鉗','smith',lambda o:o.name in ('Tongs_Left','Tongs_Right'),Matrix.Identity(4)),
 'MedicineJar01':('藥罐','shop',lambda o:o.name in ('Counter_Medicine_Jar_0','Jar_Cork'),Matrix.Identity(4)),
 'MaterialSack01':('材料袋','shop',lambda o:o.name in ('Material_Sack_0','Sack_Tie'),Matrix.Identity(4)),
 'GoodsShelf':('貨架','shop',lambda o:o.parent and o.parent.name=='Goods_Shelf_ROOT',Matrix.Identity(4)),
 'SalesCounter':('售貨櫃台','shop',lambda o:o.parent and o.parent.name=='Sales_Counter_ROOT',Matrix.Identity(4)),
 'JadeOre01':('靈礦原石','shop',lambda o:o.name=='Raw_Jade_Ore_0',Matrix.Identity(4)),
 'IronIngot01':('鐵錠','smith',lambda o:o.name=='Stored_Ingot_0',Matrix.Identity(4))}

def rebuild_tongs(objects,assets,root):
 iron=objects[0].data.materials[0]
 for o in objects:bpy.data.objects.remove(o,do_unlink=True)
 parts=[]
 def finish(o,name):
  o.name=name
  for c in list(o.users_collection):c.objects.unlink(o)
  assets.objects.link(o);o.parent=root;o.data.materials.append(iron);parts.append(o)
  return o
 for side in (-1,1):
  y=side*.017
  coords=[(side*x,y,z) for x,z in [(-.085,.015),(-.090,.10),(-.055,.22),(0,.34),(.085,.43),(.095,.52),(.035,.565)]]
  curve=bpy.data.curves.new('Forged_Arm','CURVE');curve.dimensions='3D';curve.bevel_depth=.015;curve.bevel_resolution=3;curve.use_fill_caps=True
  spline=curve.splines.new('BEZIER');spline.bezier_points.add(len(coords)-1)
  for p,co in zip(spline.bezier_points,coords):p.co=co;p.handle_left_type='AUTO';p.handle_right_type='AUTO'
  obj=bpy.data.objects.new('Arm',curve);assets.objects.link(obj)
  bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
  bpy.ops.object.convert(target='MESH');finish(bpy.context.object,'Tongs_Left_Arm' if side<0 else 'Tongs_Right_Arm')
  bpy.ops.mesh.primitive_cube_add(size=1,location=(side*.035,y,.562));obj=bpy.context.object;obj.dimensions=(.04,.065,.045)
  bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);finish(obj,'Forged_Gripping_Jaw')
  mod=obj.modifiers.new('Jaw_Soft_Edge','BEVEL');mod.width=.005;mod.segments=3
  # Two raised ridges on each inner jaw make the gripping surfaces readable.
  for z in (.552,.572):
   bpy.ops.mesh.primitive_cube_add(size=1,location=(side*.0135,y,z));obj=bpy.context.object;obj.dimensions=(.009,.055,.006)
   bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);finish(obj,'Jaw_Grip_Ridge')
 bpy.ops.mesh.primitive_cylinder_add(vertices=40,radius=.037,depth=.088,location=(0,0,.34),rotation=(math.pi/2,0,0))
 obj=finish(bpy.context.object,'Tongs_Pivot_Pin');mod=obj.modifiers.new('Pivot_Bevel','BEVEL');mod.width=.005;mod.segments=3
 for y in (-.047,.047):
  bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=.031,location=(0,y,.34))
  obj=finish(bpy.context.object,'Pivot_Rivet_Cap');obj.scale=(1,.3,1)
 return parts


def rebuild_sack(objects,assets,root):
 cloth=objects[0].data.materials[0]
 for o in objects:bpy.data.objects.remove(o,do_unlink=True)
 cloth.use_nodes=True
 nodes=cloth.node_tree.nodes;links=cloth.node_tree.links;shader=nodes.get('Principled BSDF');shader.inputs['Roughness'].default_value=.88
 noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=100
 bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.3;bump.inputs['Distance'].default_value=.004
 links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],shader.inputs['Normal'])
 rope=bpy.data.materials.new('Sack_Hemp_Cord');rope.diffuse_color=(.25,.16,.065,1);rope.use_nodes=True
 bs=rope.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.25,.16,.065,1);bs.inputs['Roughness'].default_value=.9
 parts=[]
 def finish(o,name,mat):
  o.name=name
  for c in list(o.users_collection):c.objects.unlink(o)
  assets.objects.link(o);o.parent=root;o.data.materials.append(mat);parts.append(o)
  return o
 profile=[(.11,0),(.16,.015),(.18,.055),(.195,.11),(.20,.18),(.195,.25),(.17,.31),(.13,.355),(.085,.38),(.052,.40),(.065,.425),(.085,.45),(.09,.46),(.069,.46),(.045,.405),(.06,.36),(.11,.20),(.10,.04),(.001,.035)]
 n=64;verts=[]
 for j,(r,z) in enumerate(profile):
  for i in range(n):
   a=i*math.tau/n;fold=(.004+.009*(z/.46)**2)*math.sin(9*a+.4*z)+.003*math.sin(5*a-14*z)
   radius=max(.001,r+fold*(1 if r>.04 else 0))
   verts.append((radius*math.cos(a),radius*.84*math.sin(a),z+.003*math.sin(7*a)*(z/.46)**4))
 faces=[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(len(profile)-1) for i in range(n)]
 faces += [tuple(reversed(range(n))),tuple(range((len(profile)-1)*n,len(profile)*n))]
 data=bpy.data.meshes.new('Gathered_Cloth_Mesh');data.from_pydata(verts,[],faces);data.update()
 obj=bpy.data.objects.new('Gathered_Material_Sack',data);assets.objects.link(obj);finish(obj,'Gathered_Material_Sack',cloth)
 for p in obj.data.polygons:p.use_smooth=True
 mod=obj.modifiers.new('Cloth_Surface','SUBSURF');mod.levels=1;mod.render_levels=1
 def cord(name,coords,r=.004):
  data=bpy.data.curves.new(name,'CURVE');data.dimensions='3D';data.bevel_depth=r;data.bevel_resolution=3;data.use_fill_caps=True
  spline=data.splines.new('BEZIER');spline.bezier_points.add(len(coords)-1)
  for p,co in zip(spline.bezier_points,coords):p.co=co;p.handle_left_type='AUTO';p.handle_right_type='AUTO'
  obj=bpy.data.objects.new(name,data);assets.objects.link(obj);bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
  bpy.ops.object.convert(target='MESH');return finish(bpy.context.object,name,rope)
 for z in (.399,.409):
  coords=[(.058*math.cos(i*math.tau/16),.049*math.sin(i*math.tau/16),z) for i in range(17)]
  cord('Neck_Hemp_Wrap',coords)
 for sign in (-1,1):
  cord('Tie_Bow_Loop',[(0,-.055,.405),(sign*.035,-.061,.421),(sign*.043,-.063,.400),(sign*.020,-.061,.391),(0,-.055,.405)],.0038)
  cord('Loose_Cord_End',[(0,-.055,.403),(sign*.020,-.100,.37),(sign*.035,-.143,.335),(sign*.020,-.158,.30)],.0035)
 return parts

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
 if aid=='SmithTongs':objects=rebuild_tongs(objects,assets,root)
 if aid=='MaterialSack01':objects=rebuild_sack(objects,assets,root)
 bpy.context.view_layer.update()
 def points():
  dg=bpy.context.evaluated_depsgraph_get()
  return [e.matrix_world@v.co for o in objects for e in [o.evaluated_get(dg)] for v in e.data.vertices]
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
 info={'asset':aid,'name_zh':name,'stage':'refined_appearance_prototype' if aid in ('SmithTongs','MaterialSack01') else 'extracted_appearance_prototype','source_blend':SOURCES[src],'source_sha256':before[str(source)],'source_objects':source_names,'geometry_changes':'rebuilt forged arms, pivot and gripping jaws' if aid=='SmithTongs' else 'rebuilt folded cloth, gathered neck and hemp ties' if aid=='MaterialSack01' else 'none; isolated and recentered','rotation_matrix_from_source':[list(r) for r in rotation],'units':'meters','front':'-Y','dimensions_m':list(extent),'mesh_objects':len(objects),'uv_baked':False,'collision_ready':False,'lod_ready':False,'unreal_import_verified':False}
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
