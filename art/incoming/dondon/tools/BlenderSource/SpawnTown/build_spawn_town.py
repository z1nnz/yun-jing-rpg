"""Editable xianxia spawn plaza. Run with Blender --background --factory-startup --python.
One unit is one metre. New runs create new versions; no existing asset is overwritten.
"""
import bpy
import math
import random
import json
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'Models' / 'SpawnTown'
version = 1
while (BASE / f'v{version:03d}').exists():
    version += 1
OUT = BASE / f'v{version:03d}'
OUT.mkdir(parents=True)
rng = random.Random(1015)
scene = bpy.data.scenes.new('Qingxi_Spawn_Plaza')
bpy.context.window.scene = scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1

def coll(name):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c

ground = coll('01_Flagstone_Plaza_Road')
stairs = coll('02_Six_Steps_Upper_Landing')
spawn = coll('03_Spawn_Stone_Dais')
lanterns = coll('04_Stone_Lanterns')
gate = coll('05_Timber_Town_Gateway')
props = coll('06_Waymarker_Benches')
pine = coll('07_Welcoming_Pine')
markers = coll('80_Gameplay_Markers_Not_Exported')
studio = coll('90_Studio_Not_Exported')

def material(name, color, noise=False, stretch=(1,1,1), emission=0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color,1)
    m.use_nodes = True
    n,l = m.node_tree.nodes,m.node_tree.links
    p = n.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color,1)
    p.inputs['Roughness'].default_value = .82
    if emission:
        p.inputs['Emission Color'].default_value = (*color,1)
        p.inputs['Emission Strength'].default_value = emission
    if noise:
        co=n.new('ShaderNodeTexCoord')
        scale=n.new('ShaderNodeVectorMath'); scale.operation='MULTIPLY'
        scale.inputs[1].default_value=stretch
        tex=n.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value=5
        tex.inputs['Detail'].default_value=4
        ramp=n.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].color=(*(v*.55 for v in color),1)
        ramp.color_ramp.elements[1].color=(*(min(v*1.4,1) for v in color),1)
        bump=n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.32
        bump.inputs['Distance'].default_value=.035
        l.new(co.outputs['Object'],scale.inputs[0]); l.new(scale.outputs[0],tex.inputs['Vector'])
        l.new(tex.outputs['Fac'],ramp.inputs[0]); l.new(ramp.outputs[0],p.inputs['Base Color'])
        l.new(tex.outputs['Fac'],bump.inputs['Height']); l.new(bump.outputs[0],p.inputs['Normal'])
    return m

stone=[material(f'Bluestone_{i}',(.20+i*.018,.245+i*.018,.255+i*.018),True) for i in range(5)]
dark=material('Deep_Stone_Joints',(.065,.085,.078),True)
moss=material('Sparse_Moss',(.095,.145,.045),True)
wood=material('Aged_Red_Brown_Timber',(.19,.075,.035),True,(3,3,.3))
roofmat=material('Jade_Grey_Roof_Tiles',(.07,.16,.17),True)
gold=material('Oxidised_Brass_Inlay',(.42,.30,.095))
lightmat=material('Warm_Lantern_Core',(.95,.55,.18),emission=.7)
earth=material('Earth_Base',(.16,.19,.115),True)

def move(obj,c):
    for old in list(obj.users_collection): old.objects.unlink(obj)
    c.objects.link(obj)

def finish(obj,name,mat,c,bevel=0):
    obj.name=name; move(obj,c)
    if mat: obj.data.materials.append(mat)
    if bevel:
        mod=obj.modifiers.new('Soft_Worn_Edges','BEVEL'); mod.width=bevel; mod.segments=2
    return obj

def box(name,loc,size,mat,c,bevel=.025):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    o=bpy.context.object; o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return finish(o,name,mat,c,bevel)

def cylinder(name,loc,radius,depth,mat,c,vertices=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=loc)
    return finish(bpy.context.object,name,mat,c,.018)

def mesh(name,verts,faces,mat,c,bevel=0):
    data=bpy.data.meshes.new(name+'_Mesh'); data.from_pydata(verts,[],faces); data.update()
    obj=bpy.data.objects.new(name,data); c.objects.link(obj)
    if mat: data.materials.append(mat)
    if bevel:
        mod=obj.modifiers.new('Worn_Edges','BEVEL'); mod.width=bevel; mod.segments=2
    return obj

def prism(name,polygon,z0,z1,mat,c,bevel=.02):
    n=len(polygon)
    return mesh(name,[(x,y,z) for z in (z0,z1) for x,y in polygon],
                [tuple(reversed(range(n))),tuple(range(n,2*n))]+
                [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],mat,c,bevel)

def paving(name,x0,x1,y0,y1,top,c):
    box(name+'_Joint_Base',((x0+x1)/2,(y0+y1)/2,top/2-.025),(x1-x0,y1-y0,top-.05),dark,c)
    nx=max(1,round((x1-x0)/.85)); ny=max(1,round((y1-y0)/.85))
    dx=(x1-x0)/nx; dy=(y1-y0)/ny
    points={}
    for j in range(ny+1):
        for i in range(nx+1):
            points[i,j]=(x0+i*dx+(rng.uniform(-.16,.16) if 0<i<nx else 0),
                         y0+j*dy+(rng.uniform(-.14,.14) if 0<j<ny else 0))
    for j in range(ny):
        for i in range(nx):
            poly=[points[i,j],points[i+1,j],points[i+1,j+1],points[i,j+1]]
            cx=sum(p[0] for p in poly)/4; cy=sum(p[1] for p in poly)/4
            poly=[(cx+(x-cx)*.955,cy+(y-cy)*.955) for x,y in poly]
            prism(f'{name}_Slab_{i:02}_{j:02}',poly,top-.12,top+rng.uniform(-.008,.008),rng.choice(stone),c,.015)

# Ground level is zero. Walkable lower plaza is +0.24 m.
box('Terrain_Display_Island',(0,-.9,-.25),(16,19,.5),earth,ground,.35)
paving('Lower_Plaza',-4.6,4.6,-6,.4,.24,ground)
paving('South_Approach',-1.8,1.8,-10,-6,.24,ground)
paving('Upper_Landing',-3.6,3.6,2.8,6.7,1.32,stairs)
for i in range(6):
    top=.24+(i+1)*.18
    for j in range(5):
        box(f'Stair_{i+1}_Block_{j+1}',(-1.6+j*.8,.4+(i+.5)*.4,top/2),(.79,.398,top),stone[(i+j)%5],stairs,.015)
for side in (-1,1):
    for j in range(5):
        box(f'Landing_Retaining_{side}_{j}',(side*3.52,3.18+j*.77,.62),(.22,.74,1.15),stone[j],stairs)
    for j in range(8):
        box(f'Plaza_Edge_{side}_{j}',(side*4.7,-5.6+j*.8,.19),(.22,.77,.38),stone[j%5],ground)

# Octagonal birth / meditation stone: shallow, approachable, no tall obstacles.
cylinder('Spawn_Dais_Lower',(0,-3.3,.31),1.65,.14,stone[0],spawn,8)
cylinder('Spawn_Dais_Upper',(0,-3.3,.43),1.45,.10,stone[3],spawn,8)
for radius in (1.10,1.22):
    bpy.ops.mesh.primitive_torus_add(major_segments=64,minor_segments=6,location=(0,-3.3,.486),major_radius=radius,minor_radius=.012)
    finish(bpy.context.object,'Dais_Brass_Ring',gold,spawn)
for i in range(8):
    a=i*math.tau/8
    o=box(f'Dais_Radial_Inlay_{i}',(math.cos(a)*.78,-3.3+math.sin(a)*.78,.486),(.26,.028,.009),gold,spawn,.002)
    o.rotation_euler.z=a

def roof(name,x,y,z,width,depth,c,mat):
    # Curved gable roof, upturned corners; separate solid strips remain editable.
    count=max(8,int(width/.22))
    for i in range(count):
        xa=-width/2+i*width/count; xb=xa+width/count-.012
        verts=[]
        for xlocal in (xa,xb):
            for j in range(9):
                t=-1+j/4
                zz=z+.60*(1-abs(t))**1.7+.24*abs(t)**5+.27*(abs(xlocal)/(width/2))**7
                verts.append((x+xlocal,y+t*depth/2,zz))
        faces=[(j,j+1,10+j,9+j) for j in range(8)]
        obj=mesh(f'{name}_Tile_Rib_{i:02}',verts,faces,mat,c)
        sol=obj.modifiers.new('Tile_Thickness','SOLIDIFY'); sol.thickness=.075
    box(name+'_Ridge',(x,y,z+.65),(width+.08,.16,.17),mat,c,.06)

def lantern(name,x,y,base):
    box(name+'_Foot',(x,y,base+.10),(.86,.86,.2),stone[1],lanterns,.06)
    cylinder(name+'_Pedestal',(x,y,base+.48),.24,.58,stone[0],lanterns,8)
    box(name+'_Chamber_Base',(x,y,base+.84),(.72,.72,.14),stone[3],lanterns)
    for sx in (-1,1):
        for sy in (-1,1):
            box(name+f'_Post_{sx}_{sy}',(x+sx*.255,y+sy*.255,base+1.12),(.1,.1,.48),stone[0],lanterns,.01)
    cylinder(name+'_Amber_Core',(x,y,base+1.10),.13,.32,lightmat,lanterns,8)
    roof(name+'_Cap',x,y,base+1.36,.98,.98,lanterns,stone[0])

for name,x,y,z in [('Lower_Left',-3.5,-4.9,.24),('Lower_Right',3.5,-4.9,.24),
                    ('Upper_Left',-2.8,3.5,1.32),('Upper_Right',2.8,3.5,1.32)]:
    lantern(name,x,y,z)

# Town threshold: intentionally modest timber gateway, not a grand sect palace.
for side in (-1,1):
    x=side*2.45
    box(f'Gate_Stone_Socket_{side}',(x,5.5,1.61),(.80,.80,.58),stone[2],gate,.05)
    cylinder(f'Gate_Timber_Post_{side}',(x,5.5,3.29),.21,3.62,wood,gate,16)
    box(f'Gate_Capital_{side}',(x,5.5,4.88),(.70,.75,.24),wood,gate)
    for offset in (-.38,.38):
        box(f'Gate_Bracket_{side}_{offset}',(x+offset,5.5,4.72),(.18,.7,.3),wood,gate)
box('Gate_Main_Crossbeam',(0,5.5,4.99),(5.9,.38,.35),wood,gate)
box('Gate_Lower_Crossbeam',(0,5.5,4.42),(5.2,.24,.18),wood,gate)
box('Gate_Nameboard_Blank',(0,5.23,4.66),(1.65,.12,.48),wood,gate)
box('Gate_Nameboard_Inset',(0,5.159,4.66),(1.48,.018,.32),gold,gate,.01)
roof('Town_Gateway',0,5.5,5.15,6.8,2.2,gate,roofmat)

# Standing waymarker and two simple benches are separate prop assemblies.
prism('Waymarker_Stone',[(2.95,-1.8),(3.65,-1.8),(3.72,-1.36),(3.02,-1.32)],.24,1.85,stone[1],props,.12)
box('Waymarker_Dark_Inset',(3.33,-1.816,1.17),(.40,.025,.87),dark,props,.035)
for z in (.91,1.15,1.39):
    box('Waymarker_Abstract_Carving',(3.33,-1.835,z),(.24,.018,.026),gold,props,.006)
for x in (-3.65,3.65):
    box(f'Bench_Seat_{x}',(x,-3.1,.77),(.62,1.8,.16),wood,props)
    for y in (-3.72,-2.48):
        box(f'Bench_Support_{x}_{y}',(x,y,.47),(.46,.22,.46),stone[0],props)

# Append only actual pine geometry. Retain editable source materials except bark.
source=ROOT/'Models/WelcomingPine/v002/WelcomingPine_v002.blend'
if source.exists():
    with bpy.data.libraries.load(str(source),link=False) as (src,dst):
        dst.collections=[n for n in src.collections if n.startswith(('01_Trunk','02_Pine','03_Root'))]
    tree_root=bpy.data.objects.new('Welcoming_Pine_Placement',None); pine.objects.link(tree_root)
    natural_bark=material('Pine_Bark_Soft_Longitudinal',(.13,.085,.044),True,(3,3,.35))
    for c in dst.collections:
        for obj in list(c.all_objects):
            if obj.type!='MESH': continue
            world=obj.matrix_world.copy()
            pine.objects.link(obj)
            obj.parent=tree_root; obj.matrix_world=world
            for slot in obj.material_slots:
                if slot.material and 'Bark' in slot.material.name: slot.material=natural_bark
    tree_root.location=(-4.0,-.8,0)
    tree_root.scale=(.76,.76,.76)

for name,loc in [('Spawn_Player_Feet',(0,-3.3,.49)),('Town_Exit_North',(0,6.7,1.33)),
                 ('Future_Smith_East',(7,0,0)),('Future_Inn_West',(-7,5,0))]:
    obj=bpy.data.objects.new(name,None); markers.objects.link(obj); obj.location=loc
    obj.empty_display_type='ARROWS'; obj.empty_display_size=.7
    obj['purpose']='Layout marker only; does not implement gameplay.'

# Studio is deliberately excluded from FBX.
studio_mat=material('Studio_Sand',(.26,.29,.28))
box('Studio_Floor',(0,0,-.58),(200,200,.10),studio_mat,studio,0)
world=bpy.data.worlds.new('Overcast_Daylight'); world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.49,.62,.73,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.45
scene.world=world

def aim(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

for name,loc,power,size in [('Key',(-8,-9,16),2500,9),('Fill',(10,-2,10),1600,8),('Rim',(0,10,12),2200,7)]:
    data=bpy.data.lights.new(name,'AREA'); data.energy=power; data.shape='DISK'; data.size=size
    obj=bpy.data.objects.new(name,data); studio.objects.link(obj); obj.location=loc; aim(obj,(0,0,1))
data=bpy.data.cameras.new('Overview'); camera=bpy.data.objects.new('Overview',data)
studio.objects.link(camera); camera.location=(18,-25,20); aim(camera,(-.7,-1.0,1.7))
data.type='ORTHO'; data.ortho_scale=25
scene.camera=camera
scene.render.engine='CYCLES'; scene.cycles.device='CPU'; scene.cycles.samples=32
scene.cycles.use_denoising=True
scene.render.resolution_x=1400; scene.render.resolution_y=1100; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.view_settings.view_transform='AgX'
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            s=area.spaces.active; s.shading.type='MATERIAL'
            s.region_3d.view_distance=26; s.region_3d.view_location=Vector((0,-1,1))
            s.region_3d.view_rotation=camera.rotation_euler.to_quaternion()

assets=[o for c in (ground,stairs,spawn,lanterns,gate,props,pine) for o in c.objects if o.type=='MESH']
for obj in scene.objects: obj.select_set(False)
for obj in assets: obj.select_set(True)
bpy.context.view_layer.objects.active=assets[0]
fbx=OUT/f'SpawnTown_v{version:03d}.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},
                        apply_unit_scale=True,bake_anim=False,axis_forward='-Z',axis_up='Y',mesh_smooth_type='FACE')
for obj in scene.objects: obj.select_set(False)
point=bpy.data.objects['Spawn_Player_Feet']; point.select_set(True)
bpy.context.view_layer.objects.active=point
blend=OUT/f'SpawnTown_v{version:03d}.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
stats={'stage':'Editable first-pass spawn plaza, not a full town', 'seed':1015,
       'blender':bpy.app.version_string,'mesh_objects':len(assets),
       'base_triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in assets),
       'spawn_feet_blender_m':[0,-3.3,.49], 'stairs':{'risers':6,'riser_m':.18,'tread_m':.4},
       'limitations':['No gameplay/colliders/navmesh implemented','No UV unwrap or texture bake',
                      'FBX contains base colors; procedural materials require baking for Unity',
                      'No Unity import verification, LOD or production optimisation',
                      'Town shops and houses are planned, not built; signboard text is unassigned']}
(OUT/'model_info.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
print('SAVED',blend,flush=True)
views=[('01_overview',(18,-25,20),(-.7,-1,1.7),25),
       ('02_top',(0,-1,35),(0,-1,0),24),
       ('03_spawn_eye_level',(8,-14,6),(0,-.4,2),17)]
for name,loc,target,scale in views:
    camera.location=loc; aim(camera,target); data.ortho_scale=scale
    scene.render.filepath=str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True)
    print('RENDERED',name,flush=True)
print('COMPLETE',json.dumps(stats),flush=True)
