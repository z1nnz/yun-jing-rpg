"""Five route modules. All reference views are rendered from the same mesh geometry."""
import bpy,math,json,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
VIEWS=[('01_front',(0,-1,0)),('02_right',(1,0,0)),('03_rear',(0,1,0)),('04_left',(-1,0,0)),('05_front_right',(1,-1,.45)),('06_rear_right',(1,1,.45)),('07_rear_left',(-1,1,.45)),('08_front_left',(-1,-1,.45)),('09_top',(0,0,1)),('10_high_front',(0,-1,1))]
NAMES={'MountainStoneStairs':'青石登山階梯','MountainTurnLanding':'山路轉折平台','CliffBoardwalk':'峭壁木棧道','TimberSpanBridge':'山谷木橋','MountainStonePath':'青石古道路段'}
DETAILS={'MountainStoneStairs':'12 risers of 0.2 m; 0.4 m tread; 4.8 m run, 2.4 m rise, 3 m width.','MountainTurnLanding':'4 x 4 m landing. South and east entrances; north and west rails are removable mesh parts.','CliffBoardwalk':'6 x 3 m boardwalk with exposed-edge rail and triangular wall brackets. Add inner rail when freestanding.','TimberSpanBridge':'12 x 3 m timber footbridge with dual guard rails, trusses and cross beams. No structural engineering certification.','MountainStonePath':'6 x 3 m paved path with stone edging; may be shortened along the travel axis.'}
CONNECTORS={'MountainStoneStairs':{'entry':(0,-2.4,0),'exit':(0,2.4,2.4)},'MountainTurnLanding':{'entry':(0,-2,.3),'exit':(2,0,.3)},'CliffBoardwalk':{'entry':(0,-3,1.2),'exit':(0,3,1.2)},'TimberSpanBridge':{'entry':(0,-6,.6),'exit':(0,6,.6)},'MountainStonePath':{'entry':(0,-3,.2),'exit':(0,3,.2)}}
def mat(name,c):
 m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*c,1);bs.inputs['Roughness'].default_value=.8
 tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=22;tex.inputs['Detail'].default_value=3
 bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.18;bump.inputs['Distance'].default_value=.025;l.new(tex.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],bs.inputs['Normal']);return m
def make_materials():
 global stone,pale,wood,board,metal,jade
 stone=mat('Weathered_Blue_Stone',(.20,.27,.27));pale=mat('Pale_Edge_Stone',(.37,.42,.37));wood=mat('Deep_Cedar',(.12,.055,.025));board=mat('Cedar_Planks',(.28,.14,.065));metal=mat('Dark_Bronze',(.12,.11,.075));jade=mat('Mossy_Jade',(.10,.21,.12))
def box(name,p,s,m,bevel=.01):
 bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=bpy.context.object;o.dimensions=s;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 o.name=name
 for c in list(o.users_collection):c.objects.unlink(o)
 assets.objects.link(o);o.parent=root;o.data.materials.append(m)
 if bevel:
  mod=o.modifiers.new('Edge_Soften','BEVEL');mod.width=bevel;mod.segments=2;o.modifiers.new('Weighted_Normals','WEIGHTED_NORMAL')
 return o
def beam(name,a,b,width,depth,m):
 a,b=Vector(a),Vector(b);o=box(name,(a+b)/2,(width,depth,(b-a).length),m,.012);o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o
def rail(name,a,b,z0,z1=None,stone_style=False,endpoint_posts=True):
 a,b=Vector(a),Vector(b);z1=z0 if z1 is None else z1;n=max(1,round((b-a).length/1.2));m=pale if stone_style else wood
 for i in range(n+1):
  if not endpoint_posts and i in (0,n):continue
  t=i/n;p=a.lerp(b,t);z=z0+(z1-z0)*t
  box(name+'_Post',(p.x,p.y,z+.54),(.16,.16,1.08),m,.018)
  box(name+'_Cap',(p.x,p.y,z+1.10),(.23,.23,.10),jade if stone_style else board,.025)
 for zz in (.40,.96):beam(name+'_Rail',(a.x,a.y,z0+zz),(b.x,b.y,z1+zz),.09,.09,m)
def stairs():
 for i in range(12):
  h=(i+1)*.2;y=-2.4+(i+.5)*.4
  box('Walk_Tread_%02d'%i,(0,y,h/2),(3,.4,h),stone,.006)
 for x in (-1.48,1.48):rail('Stair_Guard',(x,-2.4,0),(x,2.4,0),0,2.4,True)
def landing():
 box('Walk_Landing',(0,0,.15),(4,4,.3),stone,.008)
 for x in (-1,0,1):box('Paving_Joint',(x,0,.301),(.015,3.8,.002),jade,.0005)
 rail('Rail_North',(-1.9,1.9,0),(1.9,1.9,0),.3,stone_style=True,endpoint_posts=False)
 rail('Rail_West',(-1.9,-1.9,0),(-1.9,1.9,0),.3,stone_style=True,endpoint_posts=False)
 for x in (-1.9,1.9):
  for y in (-1.9,1.9):
   box('Landing_Corner_Post',(x,y,.84),(.16,.16,1.08),pale,.018)
   box('Landing_Corner_Cap',(x,y,1.40),(.23,.23,.10),jade,.025)
def plankdeck(length,z):
 box('Continuous_Deck_Subfloor',(0,0,z-.16),(2.96,length,.08),wood,.004)
 n=round(length/.25)
 for i in range(n):box('Walk_Plank_%02d'%i,(0,-length/2+(i+.5)*length/n,z-.075),(3,length/n-.008,.15),board,.008)
 for x in (-1.1,1.1):box('Longitudinal_Beam',(x,0,z-.3),(.24,length,.45),wood,.015)
def boardwalk():
 plankdeck(6,1.2)
 rail('Outer_Guard',(-1.55,-3,0),(-1.55,3,0),1.2)
 for y in (-2.4,0,2.4):
  box('Wall_Anchor',(1.35,y,.54),(.22,.22,1.08),wood,.015)
  beam('Wall_Diagonal_Bracket',(1.35,y,.12),(-1.1,y,.96),.17,.17,wood)
  box('Crossbeam',(0,y,.91),(3.1,.20,.24),wood,.01)
def bridge():
 plankdeck(12,.6)
 for x in (-1.55,1.55):
  rail('Bridge_Guard',(x,-6,0),(x,6,0),.6)
  for i in range(6):
   y=-6+i*2;beam('Side_Truss',(x,y,.76),(x,y+2,1.46),.075,.075,board)
 for y in (-5.8,-3.9,-2,0,2,3.9,5.8):box('Bridge_Crossbeam',(0,y,.13),(3.2,.20,.26),wood,.015)
def path():
 box('Path_Subbase',(0,0,.06),(3,6,.12),stone,.005)
 for j in range(12):
  for i in range(3):box('Walk_Paver',(i-1,-2.75+j*.5,.16),(.99,.49,.08),pale if (i+j)%4==0 else stone,.004)
 for x in (-1.55,1.55):
  for j in range(6):box('Path_Kerb',(x,-2.5+j,.16),(.15,.99,.32),pale,.008)
BUILDERS={'MountainStoneStairs':stairs,'MountainTurnLanding':landing,'CliffBoardwalk':boardwalk,'TimberSpanBridge':bridge,'MountainStonePath':path}
def actual_bounds(objects):
    dg=bpy.context.evaluated_depsgraph_get()
    pts=[e.matrix_world@v.co for o in objects for e in [o.evaluated_get(dg)] for v in e.data.vertices]
    return Vector([min(p[i] for p in pts) for i in range(3)]),Vector([max(p[i] for p in pts) for i in range(3)])

ids=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else list(BUILDERS)
for aid in ids:
    out=ROOT/'Models'/aid/'v001';refs=ROOT/'ArtLibrary/Turnarounds'/f'{aid}_v001'
    if (refs/'views.json').exists():print('ALREADY_COMPLETE',aid,flush=True);continue
    out.mkdir(parents=True,exist_ok=True);refs.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;bpy.context.preferences.filepaths.save_version=0
    scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    assets=bpy.data.collections.new('01_Editable_Asset');scene.collection.children.link(assets)
    root=bpy.data.objects.new(aid+'_ROOT',None);assets.objects.link(root);root['stage']=DETAILS[aid]
    make_materials()
    BUILDERS[aid]();bpy.context.view_layer.update()
    objects=[o for o in assets.objects if o.type=='MESH'];lo,hi=actual_bounds(objects)
    shift=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
    for o in objects:o.location-=shift
    bpy.context.view_layer.update();lo,hi=actual_bounds(objects);centre=(lo+hi)/2;extent=hi-lo
    studio=bpy.data.collections.new('90_Studio_Not_Exported');scene.collection.children.link(studio)
    def studio_obj(name,data):
        o=bpy.data.objects.new(name,data);studio.objects.link(o);return o
    cam=studio_obj('Reference_Camera',bpy.data.cameras.new('Reference_Camera'));scene.camera=cam;cam.data.type='ORTHO'
    cam.data.clip_start=.01;cam.data.clip_end=1000;cam.data.ortho_scale=max(extent.length*1.08,.5)
    # Scale light positions and power with architecture dimensions for consistent exposures.
    ls=max(extent)*.65
    for name,direction,power in [('Key',(-.8,-1.1,1.5),1100),('Fill',(1.2,-.4,.9),650),('Rim',(.2,1.1,1.3),950)]:
        d=bpy.data.lights.new(name,'AREA');d.energy=power*ls*ls/7;d.shape='DISK';d.size=ls
        o=studio_obj(name,d);o.location=centre+Vector(direction)*ls;o.rotation_euler=(centre-o.location).to_track_quat('-Z','Y').to_euler()
    scene.world=bpy.data.worlds.new('Neutral_Studio');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.19,.21,.22,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.65
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=12;scene.cycles.use_denoising=True
    scene.render.resolution_x=1024;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
    def position(direction):
        cam.location=centre+Vector(direction).normalized()*cam.data.ortho_scale*2.3
        cam.rotation_euler=(centre-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
    position((1,-1,.65));bpy.ops.object.select_all(action='DESELECT')
    for o in [root]+objects:o.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.export_scene.fbx(filepath=str(out/(aid+'_v001.fbx')),use_selection=True,object_types={'MESH','EMPTY'},add_leaf_bones=False,axis_forward='-Z',axis_up='Y',apply_unit_scale=True,bake_anim=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/(aid+'_v001.blend')))
    info={'asset':aid,'name_zh':NAMES[aid],'stage':'editable_path_prototype','description':DETAILS[aid],'units':'meters','front':'-Y','dimensions_m':list(extent),'mesh_objects':len(objects),'bounds_method':'evaluated mesh vertices','modeling_method':'procedural mesh construction; ten views rendered from the same model','uv_baked':False,'collision':False,'lod':False,'unreal_import_verified':False}
    info['connectors']={k:list(Vector(v)-shift) for k,v in CONNECTORS[aid].items()}
    info['clear_walk_width_m']=2.6
    (out/'model_info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2))
    from bpy_extras.object_utils import world_to_camera_view
    records=[]
    for name,direction in VIEWS:
        position(direction);dg=bpy.context.evaluated_depsgraph_get()
        projected=[world_to_camera_view(scene,cam,e.matrix_world@Vector(p)) for o in objects for e in [o.evaluated_get(dg)] for p in e.bound_box]
        assert all(.005<p.x<.995 and .005<p.y<.995 and p.z>0 for p in projected),(aid,name,'cropped')
        scene.render.filepath=str(refs/(name+'.png'));bpy.ops.render.render(write_still=True)
        records.append({'file':name+'.png','direction':direction,'camera_location':list(cam.location),'projection':'orthographic','framing_checked':True})
        print('VIEW_COMPLETE',aid,name,flush=True)
    (refs/'views.json').write_text(json.dumps({'asset':aid,'source':str((out/(aid+'_v001.blend')).relative_to(ROOT)),'same_geometry':True,'views':records},indent=2))
    print('ASSET_COMPLETE',aid,flush=True)
