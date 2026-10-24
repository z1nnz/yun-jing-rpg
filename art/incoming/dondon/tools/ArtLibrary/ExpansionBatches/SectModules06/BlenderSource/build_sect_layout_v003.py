"""Add perimeter modules to a copy of SectLayout v002; all earlier sources remain unchanged."""
import bpy,json,math,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
R=Path(__file__).resolve().parents[1];PROJECT=R.parents[2];OUT=R/'Models/SectLayout/v003';OUT.mkdir(parents=True,exist_ok=True)
assert not (OUT/'SectLayout_v003.blend').exists()
source=PROJECT/'Models/SectLayout/v002/SectLayout_v002.blend'
bpy.ops.wm.open_mainfile(filepath=str(source));bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;boundary=bpy.data.collections.new('70_Sect_Perimeter');scene.collection.children.link(boundary)
templates={};sourcehash={str(source):hashlib.sha256(source.read_bytes()).hexdigest()}
for aid in ['SectWallStraight','SectWallCorner','CourtyardGate']:
 p=R/'Models'/aid/'v001'/f'{aid}_v001.blend';sourcehash[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
 with bpy.data.libraries.load(str(p),link=False) as (a,b):b.collections=['01_Editable_Asset']
 templates[aid]=b.collections[0]
placements=[]
def instance(aid,pos,angle=0,stretch=1):
 src=templates[aid];root=bpy.data.objects.new(aid+'_Placement',None);boundary.objects.link(root);root.location=pos;root.rotation_euler.z=angle;root.scale.x=stretch
 bpy.context.view_layer.update()
 for old in src.objects:
  if old.type=='MESH':
   new=old.copy();new.data=old.data;boundary.objects.link(new);new.parent=root;new.matrix_parent_inverse=Matrix.Identity(4);new.matrix_basis=old.matrix_basis.copy()
 placements.append({'asset':aid,'location_m':list(pos),'rotation_z_radians':angle,'length_scale':stretch})
def span(a,b):
 a,b=Vector(a),Vector(b);length=(b-a).length;n=max(1,round(length/4));step=length/n;angle=math.atan2(b.y-a.y,b.x-a.x)
 for i in range(n):instance('SectWallStraight',a+(b-a)*(i+.5)/n,angle,step/4)
 # Exact designed end points; bases are wider than the masonry pier for foot support.
 return {'start':list(a),'end':list(b),'segments':n,'module_length_m':step}
spans=[]
for x in (-20,20):
 for y in (-19,38):instance('SectWallCorner',(x,y,0))
spans.append(span((-19.69,38,0),(19.69,38,0)))
spans.append(span((-20,-18.69,0),(-20,37.69,0)))
spans.append(span((20,-18.69,0),(20,4.3,0)))
spans.append(span((20,7.7,0),(20,37.69,0)))
spans.append(span((-19.69,-19,0),(-2.3,-19,0)))
spans.append(span((2.3,-19,0),(19.69,-19,0)))
instance('CourtyardGate',(20,6,0),math.pi/2)
# Remove unlinked source collections after creating the independent object copies.
for col in templates.values():
 for o in list(col.objects):bpy.data.objects.remove(o,do_unlink=True)
 bpy.data.collections.remove(col)
# Short paver approach joins the open southern gap; side gate is a closed static prototype.
mat=next(m for m in bpy.data.materials if m.name.startswith('Path_Stone'))
for y in (-19.2,-18.4):
 for x in (-.8,0,.8):
  bpy.ops.mesh.primitive_cube_add(size=1,location=(x,y,.035));o=bpy.context.object;o.name='South_Entrance_Paver';o.dimensions=(.775,.775,.07);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat)
  for col in list(o.users_collection):col.objects.unlink(o)
  boundary.objects.link(o)
bpy.context.view_layer.update();cam=scene.camera;target=Vector((0,9,1.7))
bpy.ops.object.select_all(action='DESELECT');objects=[o for o in scene.objects if o.type in ('MESH','EMPTY')]
for o in objects:o.select_set(True)
bpy.context.view_layer.objects.active=objects[0]
bpy.ops.export_scene.fbx(filepath=str(OUT/'SectLayout_v003.fbx'),use_selection=True,object_types={'MESH','EMPTY'},add_leaf_bones=False,axis_forward='-Z',axis_up='Y',apply_unit_scale=True,bake_anim=False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'SectLayout_v003.blend'))
for name,pos,scale in [('01_campus_overview',(42,-50,52),73),('02_campus_top',(0,9,85),63),('03_campus_front',(30,-48,30),70)]:
 cam.location=pos;cam.data.ortho_scale=scale;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True);print('LAYOUT_VIEW',name,flush=True)
info=json.loads((PROJECT/'Models/SectLayout/v002/layout_info.json').read_text());info.update({'name_zh':'宗門圍合配置','source_scene':'Models/SectLayout/v002/SectLayout_v002.blend','perimeter_placements':placements,'wall_spans':spans,'front_opening_width_m':4.6,'side_gate_opening_width_m':3.4,'side_gate_door_state':'closed; no animation','library_stair_installed':False,'stage':'Static perimeter layout; no navmesh or collision verified.'})
(OUT/'layout_info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2));(R/'source_integrity.json').write_text(json.dumps(sourcehash,indent=2));print('LAYOUT_COMPLETE',len(placements),flush=True)
