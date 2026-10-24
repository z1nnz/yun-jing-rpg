"""Add a two-leg ascent, bridge and summit approach to a new scene version.
Source v001 is read-only. Route contacts use explicit walk-surface connectors.
"""
import bpy,math,json
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[2]
OUT=ROOT/'Models/MountainSanctuary/v002';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(PROJECT/'Models/MountainSanctuary/v001/MountainSanctuary_v001.blend'))
s=bpy.context.scene;s.frame_set(1);bpy.context.preferences.filepaths.save_version=0
route=bpy.data.collections.new('60_Mountain_Ascent');s.collection.children.link(route)
cache={};placements=[];segments=[];count=0

def source(aid):
 if aid not in cache:
  with bpy.data.libraries.load(str(ROOT/'Models'/aid/'v001'/f'{aid}_v001.blend'),link=False) as (src,dst):dst.collections=['01_Editable_Asset']
  coll=dst.collections[0];info=json.loads((ROOT/'Models'/aid/'v001/model_info.json').read_text());cache[aid]=(coll,info)
 return cache[aid]

def module(aid,start,yaw=0,scale=(1,1,1),mode='default'):
 global count
 proto,info=source(aid);copy={}
 for old in proto.objects:
  o=old.copy();route.objects.link(o);copy[old]=o
 for old,o in copy.items():o.parent=copy.get(old.parent)
 root=next(o for o in copy.values() if o.type=='EMPTY');count+=1;root.name=f'Route_{count:03d}_{aid}'
 entry=Vector(info['connectors']['entry']);exit=Vector(info['connectors']['exit'])
 if aid=='MountainTurnLanding':
  centre=entry+Vector((0,2,0))
  if mode=='straight':
   exit=centre+Vector((0,2,0))
   for o in list(copy.values()):
    if o.name.startswith('Rail_North'):bpy.data.objects.remove(o,do_unlink=True)
    elif o.name.startswith('Rail_West'):
     extra=o.copy();route.objects.link(extra);extra.parent=root;extra.location.x=2*centre.x-o.location.x;extra.name='Rail_East_Straight'
  elif mode=='west_to_north':
   entry=centre+Vector((-2,0,0));exit=centre+Vector((0,2,0))
   for o in list(copy.values()):
    if o.name.startswith('Rail_North'):o.location.y=2*centre.y-o.location.y;o.name='Rail_South_Top_Turn'
    elif o.name.startswith('Rail_West'):o.location.x=2*centre.x-o.location.x;o.name='Rail_East_Top_Turn'
 if aid=='CliffBoardwalk':
  for o in list(copy.values()):
   if o.name.startswith('Outer_Guard'):
    extra=o.copy();route.objects.link(extra);extra.parent=root;extra.location.x=-o.location.x;extra.name='Inner_Guard_Added'
 rotation=Matrix.Rotation(yaw,3,'Z');scaled=lambda v:Vector(tuple(v[i]*scale[i] for i in range(3)))
 root.location=Vector(start)-rotation@scaled(entry);root.rotation_euler.z=yaw;root.scale=scale
 end=Vector(start)+rotation@scaled(exit-entry)
 placements.append({'root':root.name,'asset':aid,'start':list(start),'end':list(end),'scale':list(scale),'mode':mode})
 print('PLACED',count,aid,flush=True)
 if aid=='MountainTurnLanding':
  c=root.location+rotation@scaled(centre);segments.append({'start':list(start),'end':list(c),'type':'level'});segments.append({'start':list(c),'end':list(end),'type':'level'})
 else:segments.append({'start':list(start),'end':list(end),'type':'stairs' if aid=='MountainStoneStairs' else 'level','steps':12 if aid=='MountainStoneStairs' else 0})
 return end,root

stone=bpy.data.materials.new('Ascent_Pier_Blue_Stone');stone.diffuse_color=(.20,.26,.25,1);stone.use_nodes=True
stone.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.20,.26,.25,1);stone.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.85
def box(name,p,sz,mat=stone):
 vertices=[(sx*sz[0]/2,sy*sz[1]/2,szn*sz[2]/2) for szn in (-1,1) for sy in (-1,1) for sx in (-1,1)]
 data=bpy.data.meshes.new(name+'_Mesh');data.from_pydata(vertices,[],[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]);data.update()
 o=bpy.data.objects.new(name,data);o.location=p;route.objects.link(o);data.materials.append(mat);return o

# Terrain height comes from the original scene before the route is placed.
terrain=[];bpy.context.view_layer.update();terrain_dg=bpy.context.evaluated_depsgraph_get()
for o in s.objects:
 if o.type=='MESH' and (o.name.startswith(('Summit_','Valley_Ground','Cliff_','Main_Rock','Attached_','Eroded_','Ridge_'))):terrain.append((o.matrix_world.copy(),o.matrix_world.inverted(),BVHTree.FromObject(o,terrain_dg)))
def ground(x,y):
 best=-.15
 for world,inv,bvh in terrain:
  p=inv@Vector((x,y,200));d=(inv.to_3x3()@Vector((0,0,-1))).normalized()
  pt,normal,index,distance=bvh.ray_cast(p,d)
  if pt is not None:best=max(best,(world@pt).z)
 return best

def pier(start,end,aid):
 p=(Vector(start)+Vector(end))/2;low=min(start[2],end[2])
 thickness={'MountainStoneStairs':.08,'MountainTurnLanding':.30,'TimberSpanBridge':.60}.get(aid,.3)
 top=low-thickness;bottom=ground(p.x,p.y)-.08
 if top-bottom<.3:return
 size=(2.5,1.4,top-bottom) if abs(end[1]-start[1])>abs(end[0]-start[0]) else (1.4,2.5,top-bottom)
 box('Ascent_Masonry_Pier',(p.x,p.y,(top+bottom)/2),size)
 box('Pier_Capital',(p.x,p.y,top-.12),(size[0]+.4,size[1]+.4,.24))
 for z in range(math.ceil(bottom/3)*3,math.floor(top),3):box('Pier_Stone_Course',(p.x,p.y,z),(size[0]+.06,size[1]+.06,.08))

# Entry connects the valley floor (-0.15 m) to the path (+0.15 m) via two 0.15 m risers.
box('Entry_First_Step',(-60,-136.2,-.075),(3.0,.4,.15))
entry=Vector((-60,-136,.15));p,_=module('MountainStonePath',entry)
for leg in range(2):
 yaw=0 if leg==0 else -math.pi/2
 for i in range(10):
  before=p.copy();p,_=module('MountainStoneStairs',p,yaw);pier(before,p,'MountainStoneStairs')
  if i in (3,7):
   before=p.copy();p,_=module('MountainTurnLanding',p,yaw,mode='straight');pier(before,p,'MountainTurnLanding')
 if leg==0:
  before=p.copy();p,_=module('MountainTurnLanding',p,mode='default');pier(before,p,'MountainTurnLanding')
before=p.copy();p,_=module('MountainTurnLanding',p,mode='west_to_north');pier(before,p,'MountainTurnLanding')
before=p.copy();p,_=module('TimberSpanBridge',p);pier(before,p,'TimberSpanBridge')
p,_=module('CliffBoardwalk',p)
for _ in range(3):p,_=module('MountainStonePath',p)
p,_=module('MountainStonePath',p,scale=(1,2/3,1))
assert (p-Vector((0,-30,48.15))).length<.001,list(p)
bpy.context.view_layer.update()

def cam(name,loc,target,ortho=None):
 d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);s.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.lens=43;d.clip_end=5000
 if ortho:d.type='ORTHO';d.ortho_scale=ortho
 return o
overview=cam('04_Ascent_Overview',(185,-310,195),(-12,-31,39))
detail=cam('05_Bridge_And_Gate',(55,-110,84),(-7,-52,44))
plan=cam('06_Route_Top',(-24,-15,310),(-24,-15,0),275)
s.camera=overview;s.render.resolution_x=1440;s.render.resolution_y=1080;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.cycles.samples=16
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'MountainSanctuary_v002.blend'))
for name,c,w,h in [('01_ascent_overview',overview,1440,1080),('02_bridge_and_gate',detail,1440,1080),('03_route_top',plan,1200,1200)]:
 s.camera=c;s.render.resolution_x=w;s.render.resolution_y=h;s.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True);print('SCENE_VIEW',name,flush=True)
bpy.ops.object.select_all(action='DESELECT');meshes=[]
for o in s.objects:
 if o.type=='MESH' and not o.get('effect_type'):o.select_set(True);meshes.append(o)
bpy.context.view_layer.objects.active=meshes[0]
bpy.ops.export_scene.fbx(filepath=str(OUT/'MountainSanctuary_v002.fbx'),use_selection=True,object_types={'MESH'},bake_anim=False,axis_forward='-Z',axis_up='Y')
(OUT/'route_info.json').write_text(json.dumps({'source_scene':'MountainSanctuary/v001','entry':list(entry),'summit_entry':list(p),'rise_m':48,'stairs_flights':20,'risers':240,'nominal_riser_m':.2,'placements':placements,'walking_segments':segments,'preview_files':3,'terrain_surface_edited':False,'physics_collision_verified':False,'structural_engineering_verified':False,'notes':['Masonry piers support an elevated approach outside the mountain.','Bridge and boardwalk brackets intersect terrain below the walk surface by design.','No Unreal navigation mesh or character traversal test.']},indent=2))
print('ROUTE_SCENE_COMPLETE',flush=True)
