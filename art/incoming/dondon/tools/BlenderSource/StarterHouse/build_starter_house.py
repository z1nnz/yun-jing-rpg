"""Generate a modular Qingxi starter house in metres, with versioned deliveries.
Run: Blender --background --factory-startup --python this_file.py
"""
import bpy
import math
import json
import random
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'Models/StarterHouse'
version=1
while (BASE/f'v{version:03d}').exists(): version+=1
OUT=BASE/f'v{version:03d}'; OUT.mkdir(parents=True)
rng=random.Random(1016)
scene=bpy.data.scenes.new('Qingxi_Starter_House'); bpy.context.window.scene=scene
scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1

def collection(name):
    c=bpy.data.collections.new(name); scene.collection.children.link(c); return c
foundation=collection('01_Foundation_Porch_Steps')
walls=collection('02_Plaster_Wall_Modules')
frame=collection('03_Timber_Frame')
roof=collection('04_Curved_Tile_Roof')
doors=collection('05_Hinged_Double_Door')
windows=collection('06_Lattice_Window_Modules')
props=collection('07_Porch_Props')
studio=collection('90_Studio_Not_Exported')
assetcols=[foundation,walls,frame,roof,doors,windows,props]

def empty(name,c,parent=None,loc=(0,0,0)):
    o=bpy.data.objects.new(name,None); c.objects.link(o); o.parent=parent; o.location=loc
    o.empty_display_size=.25; return o
asset=empty('StarterHouse_ROOT',foundation)
asset['stage']='Exterior first pass; no furnished interior, UV bake or gameplay.'
asset['units']='metres'; asset['front']='Blender -Y'; asset['ground_origin']='bottom centre of building'

def mat(name,color,texture=False,stretch=(1,1,1)):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    n,l=m.node_tree.nodes,m.node_tree.links; bs=n.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1); bs.inputs['Roughness'].default_value=.83
    if texture:
        co=n.new('ShaderNodeTexCoord'); mult=n.new('ShaderNodeVectorMath'); mult.operation='MULTIPLY'
        mult.inputs[1].default_value=stretch
        noise=n.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value=4.5; noise.inputs['Detail'].default_value=3
        ramp=n.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].position=.15; ramp.color_ramp.elements[1].position=.85
        ramp.color_ramp.elements[0].color=(*(v*.65 for v in color),1)
        ramp.color_ramp.elements[1].color=(*(min(v*1.2,1) for v in color),1)
        bump=n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.25; bump.inputs['Distance'].default_value=.026
        l.new(co.outputs['Object'],mult.inputs[0]); l.new(mult.outputs[0],noise.inputs['Vector'])
        l.new(noise.outputs['Fac'],ramp.inputs[0]); l.new(ramp.outputs[0],bs.inputs['Base Color'])
        l.new(noise.outputs['Fac'],bump.inputs['Height']); l.new(bump.outputs[0],bs.inputs['Normal'])
    return m
plaster=mat('Warm_Lime_Plaster',(.68,.63,.50),True)
timber=mat('Aged_Chestnut_Timber',(.18,.075,.035),True,(3,3,.25))
lightwood=mat('Worn_Porch_Boards',(.25,.14,.065),True,(.3,5,3))
stone=[mat(f'Blue_Stone_{i}',(.22+i*.02,.26+i*.02,.27+i*.02),True) for i in range(4)]
tiles=[mat(f'Celadon_Grey_Tile_{i}',(.065+i*.01,.13+i*.012,.14+i*.012),True) for i in range(5)]
shadow=mat('Dark_Joint',(.045,.05,.041))
paper=mat('Warm_Window_Paper',(.66,.54,.34),True)
metal=mat('Dark_Brass',(.26,.18,.065)); metal.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value=.65
potmat=mat('Clay_Jar',(.23,.14,.09),True)

def mesh(name,verts,faces,material,c,parent=asset,bevel=0):
    d=bpy.data.meshes.new(name+'_Mesh'); d.from_pydata(verts,[],faces); d.update()
    o=bpy.data.objects.new(name,d); c.objects.link(o); o.parent=parent
    if material: d.materials.append(material)
    if bevel:
        b=o.modifiers.new('Soft_Edges','BEVEL'); b.width=bevel; b.segments=2
    return o

def finish(o,name,material,c,parent,bevel):
    o.name=name
    for old in list(o.users_collection): old.objects.unlink(o)
    c.objects.link(o); o.parent=parent; o.data.materials.append(material)
    if bevel:
        m=o.modifiers.new('Soft_Edges','BEVEL'); m.width=bevel; m.segments=2
    return o

def box(name,loc,size,material,c,parent=asset,bevel=.015):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o=bpy.context.object; o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    finish(o,name,material,c,parent,bevel); o.location=loc; return o

def cyl(name,loc,radius,depth,material,c,parent=asset,vertices=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth)
    o=finish(bpy.context.object,name,material,c,parent,.012); o.location=loc; return o

def rod(name,a,b,radius,material,c,parent=asset):
    a,b=Vector(a),Vector(b); o=cyl(name,(a+b)/2,radius,(b-a).length,material,c,parent)
    o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler(); return o

# Three stone risers reach a 0.54 m floor. Porch is part of the editable building.
box('Foundation_Mortar',(0,-.45,.24),(7.55,6.5,.48),shadow,foundation)
for y in (-3.65,2.75):
    for i in range(10):
        box(f'Foundation_Block_{y}_{i}',(-3.42+i*.76,y,.24),(.745,.30,.47),stone[i%4],foundation,bevel=.03)
for x in (-3.65,3.65):
    for i in range(8):
        box(f'Side_Foundation_{x}_{i}',(x,-3.25+i*.78,.24),(.30,.765,.47),stone[i%4],foundation,bevel=.03)
box('Interior_Floor',(0,.05,.50),(7.15,5.1,.08),lightwood,foundation)
for i in range(22):
    box(f'Porch_Plank_{i:02}',(-3.52+i*.335,-3.12,.50),(.325,1.08,.08),lightwood,foundation,bevel=.008)
for i in range(3):
    top=(i+1)*.18
    for j in range(3):
        box(f'Entry_Step_{i+1}_{j}',(-.78+j*.78,-4.55+i*.34,top/2),(.77,.34,top),stone[(i+j)%4],foundation,bevel=.015)

# Local wall coordinates: exterior faces -Y; all wall modules preserve door/window holes.
def window(name,cx,sill,width,height,parent):
    root=empty(name+'_ROOT',windows,parent,(cx,0,0))
    box(name+'_Paper',(0,.025,sill+height/2),(width-.10,.035,height-.10),paper,windows,root,.002)
    for x in (-width/2,width/2): box(name+'_Jamb',(x,-.06,sill+height/2),(.11,.17,height+.15),timber,windows,root)
    for z in (sill,sill+height): box(name+'_Rail',(0,-.06,z),(width+.12,.18,.11),timber,windows,root)
    box(name+'_Stone_Sill',(0,-.09,sill-.075),(width+.26,.30,.10),stone[2],windows,root)
    for j in range(1,6):
        x=-width/2+j*width/6
        box(name+f'_Lattice_V{j}',(x,-.07,sill+height/2),(.025,.05,height-.08),timber,windows,root,.003)
    for j in range(1,5):
        z=sill+j*height/5
        box(name+f'_Lattice_H{j}',(0,-.075,z),(width-.08,.05,.025),timber,windows,root,.003)
    return root

def wall_module(name,loc,angle,length,openings):
    root=empty(name+'_ROOT',walls,asset,loc); root.rotation_euler.z=angle
    cursor=-length/2
    for idx,(cx,width,sill,head,kind) in enumerate(sorted(openings)):
        left,right=cx-width/2,cx+width/2
        if left>cursor:
            box(name+f'_Pier_{idx}',((cursor+left)/2,.10,1.945),(left-cursor,.22,2.81),plaster,walls,root)
        if sill>.54:
            box(name+f'_Below_{idx}',(cx,.10,(sill+.54)/2),(width,.22,sill-.54),plaster,walls,root)
        box(name+f'_Above_{idx}',(cx,.10,(3.35+head)/2),(width,.22,3.35-head),plaster,walls,root)
        if kind=='window': window(name+f'_Window_{idx}',cx,sill,width,head-sill,root)
        cursor=right
    if cursor<length/2:
        box(name+'_Last_Pier',((cursor+length/2)/2,.10,1.945),(length/2-cursor,.22,2.81),plaster,walls,root)
    for z in (.65,3.23): box(name+'_Horizontal_Beam',(0,-.035,z),(length+.10,.18,.15),timber,frame,root)
    return root

front=wall_module('Front',(0,-2.6,0),0,7.2,[(-2.35,1.35,1.35,2.65,'window'),(0,1.7,.54,2.95,'door'),(2.35,1.35,1.35,2.65,'window')])
wall_module('Rear',(0,2.6,0),math.pi,7.2,[(0,1.4,1.35,2.65,'window')])
wall_module('Right',(3.6,0,0),math.pi/2,5.2,[(0,1.4,1.35,2.65,'window')])
wall_module('Left',(-3.6,0,0),-math.pi/2,5.2,[(0,1.4,1.35,2.65,'window')])
for x in (-3.6,-1.08,1.08,3.6):
    for y in (-2.6,2.6):
        box(f'Timber_Column_{x}_{y}',(x,y,1.99),(.19,.24,2.90),timber,frame)
for x in (-3.5,3.5):
    cyl(f'Porch_Stone_Socket_{x}',(x,-3.46,.67),.23,.26,stone[1],foundation,vertices=8)
    cyl(f'Porch_Post_{x}',(x,-3.46,2.03),.105,2.55,timber,frame)
    rod(f'Porch_Diagonal_{x}',(x,-3.46,2.85),(x-math.copysign(.55,x),-3.46,3.30),.065,timber,frame)
box('Porch_Header',(0,-3.46,3.32),(7.35,.20,.22),timber,frame)
def roof_z(x,t): return 3.40+1.60*(1-t)**1.35+.18*t**8+.25*(abs(x)/4.3)**8
for x in (-3.65,3.65):
    # Gable infill follows the asymmetric curved roof underside without open gaps.
    profile=[]
    for j in range(25):
        y=2.62-j*5.24/24
        profile.append((y,roof_z(x,abs(y)/(3.95 if y<0 else 3.45))-.17))
    poly=[(-2.62,3.35),(2.62,3.35)]+profile
    n=len(poly)
    v=[(x+d,y,z) for d in (-.08,.08) for y,z in poly]
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    mesh(f'Gable_Plaster_{x}',v,faces,plaster,walls)
    for j in range(len(profile)-1):
        a,b=profile[j],profile[j+1]
        rod(f'Gable_Curved_Rake_{x}_{j}',(x,a[0],a[1]-.025),(x,b[0],b[1]-.025),.065,timber,frame)
    rod(f'Gable_Centre_{x}',(x,0,3.35),(x,0,roof_z(x,0)-.17),.07,timber,frame)

# Each door has a hinge empty on its outer edge, ready for later animation.
for x in (-.90,.90): box('Door_Outer_Jamb',(x,-2.69,1.77),(.14,.25,2.50),timber,doors)
box('Door_Lintel',(0,-2.69,3.00),(1.94,.26,.17),timber,doors)
for side in (-1,1):
    hinge=empty('Door_Left_Hinge' if side<0 else 'Door_Right_Hinge',doors,asset,(side*.84,-2.69,.55))
    hinge['rotation_axis']='local Z'; hinge['closed_angle_degrees']=0
    center=-side*.415
    box(f'Door_{side}_Backing',(center,.015,1.17),(.82,.09,2.30),timber,doors,hinge)
    for j in range(4):
        box(f'Door_{side}_Lower_Plank_{j}',(-side*(.105+j*.20),-.045,.61),(.19,.04,1.02),lightwood,doors,hinge,.005)
    box(f'Door_{side}_Upper_Paper',(center,-.045,1.76),(.65,.02,.87),paper,doors,hinge,.003)
    for j in range(5):
        box(f'Door_{side}_Lattice_{j}',(center-.28+j*.14,-.075,1.76),(.025,.035,.90),timber,doors,hinge,.003)
    for z in (1.30,1.53,1.76,1.99,2.22):
        box(f'Door_{side}_Rail_{z}',(center,-.075,z),(.69,.04,.035),timber,doors,hinge,.004)
    hx=-side*.70
    box(f'Door_{side}_Handle_Plate',(hx,-.088,1.10),(.12,.024,.19),metal,doors,hinge,.012)
    bpy.ops.mesh.primitive_torus_add(major_radius=.065,minor_radius=.012,major_segments=20,minor_segments=6)
    o=finish(bpy.context.object,f'Door_{side}_Ring_Handle',metal,doors,hinge,0)
    o.location=(hx,-.12,1.08); o.rotation_euler.x=math.pi/2

# Curved tile roof: solid underlay plus individual overlapping half-round tiles.
# Ridge runs along X; front slope reaches farther over the porch.
for side,depth in [(-1,3.95),(1,3.45)]:
    verts=[]
    for ix in range(37):
        x=-4.3+ix*8.6/36
        for j in range(17):
            t=j/16; verts.append((x,side*t*depth,roof_z(x,t)-.07))
    faces=[(i*17+j,i*17+j+1,(i+1)*17+j+1,(i+1)*17+j) for i in range(36) for j in range(16)]
    if side>0: faces=[tuple(reversed(f)) for f in faces]
    o=mesh(f'Roof_{side}_Solid_Underlay',verts,faces,timber,roof)
    m=o.modifiers.new('Underlay_Thickness','SOLIDIFY'); m.thickness=.12
    # Each column is one editable tile strip, with overlapping rows of tiles in its mesh.
    for i in range(36):
        xc=-4.18+i*(8.36/35); verts=[]; faces=[]
        for row in range(11):
            t0=row/11; t1=min(1,(row+1.10)/11); start=len(verts)
            for t in (t0,t1):
                for j in range(7):
                    a=math.pi*j/6; x=xc+.115*math.cos(a)
                    verts.append((x,side*t*depth,roof_z(x,t)+.055*math.sin(a)+.018*(1-t)))
            for j in range(6): faces.append((start+j,start+j+1,start+j+8,start+j+7))
        if side>0: faces=[tuple(reversed(f)) for f in faces]
        o=mesh(f'Roof_{side}_Tile_Strip_{i:02}',verts,faces,tiles[rng.randrange(5)],roof)
        m=o.modifiers.new('Ceramic_Thickness','SOLIDIFY'); m.thickness=.025
    # Exposed timber fascia follows the curved roof edges.
    for x in (-4.33,4.33):
        for j in range(16):
            t0=j/16; t1=(j+1)/16
            rod(f'Fascia_{side}_{x}_{j}',(x,side*t0*depth,roof_z(x,t0)-.12),(x,side*t1*depth,roof_z(x,t1)-.12),.065,timber,roof)
    for i in range(17):
        x=-4.05+i*.506
        rod(f'Eave_Rafter_{side}_{i}',(x,side*(depth-.70),roof_z(x,(depth-.70)/depth)-.18),
            (x,side*depth,roof_z(x,1)-.16),.055,timber,roof)
for i in range(24):
    x=-4.24+i*.368
    rod(f'Ridge_Cap_{i}',(x,0,5.08+.25*(abs(x)/4.3)**8),
        (x+.37,0,5.08+.25*(abs(x+.37)/4.3)**8),.13,tiles[2],roof)

# Sparse porch dressing: wood bench and two hollow clay jars.
box('Porch_Bench_Seat',(2.5,-3.15,1.03),(1.35,.43,.12),lightwood,props)
for x in (2.02,2.98): box('Porch_Bench_Leg',(x,-3.15,.76),(.16,.30,.44),timber,props)
def jar(name,loc,scale):
    profile=[(.21,0),(.31,.10),(.36,.36),(.30,.58),(.18,.68),(.19,.74),(.145,.74),(.14,.66),(.25,.56),(.30,.35),(.25,.13),(.14,.07)]
    verts=[(loc[0]+scale*r*math.cos(i*math.tau/32),loc[1]+scale*r*math.sin(i*math.tau/32),loc[2]+scale*z) for r,z in profile for i in range(32)]
    faces=[]
    for j in range(len(profile)-1):
        for i in range(32): faces.append((j*32+i,j*32+(i+1)%32,(j+1)*32+(i+1)%32,(j+1)*32+i))
    faces.extend([tuple(reversed(range(32))),tuple(range((len(profile)-1)*32,len(profile)*32))])
    o=mesh(name,verts,faces,potmat,props)
    for p in o.data.polygons: p.use_smooth=True
jar('Clay_Jar_Large',(-2.6,-3.13,.54),1)
jar('Clay_Jar_Small',(-1.90,-3.18,.54),.65)

# Neutral studio and cameras are never exported.
bg=mat('Studio_Warm_Grey',(.25,.28,.27))
box('Studio_Ground',(0,0,-.12),(200,200,.20),bg,studio,None,0)
world=bpy.data.worlds.new('House_Daylight'); world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.55,.65,.74,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.5; scene.world=world
def aim(o,target): o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
for name,loc,energy,size in [('Key',(-5,-8,12),1800,7),('Fill',(7,-1,8),1000,6),('Rim',(0,7,11),1800,6)]:
    d=bpy.data.lights.new(name,'AREA'); d.energy=energy; d.shape='DISK'; d.size=size
    o=bpy.data.objects.new(name,d); studio.objects.link(o); o.location=loc; aim(o,(0,0,2))
camdata=bpy.data.cameras.new('House_Overview'); camera=bpy.data.objects.new('House_Overview',camdata)
studio.objects.link(camera); camera.location=(11,-16,10); aim(camera,(0,-.3,2.25))
camdata.type='ORTHO'; camdata.ortho_scale=14.4; scene.camera=camera
scene.render.engine='CYCLES'; scene.cycles.device='CPU'; scene.cycles.samples=40; scene.cycles.use_denoising=True
scene.render.resolution_x=1440; scene.render.resolution_y=1100; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.view_settings.view_transform='AgX'
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            s=area.spaces.active; s.shading.type='MATERIAL'; s.region_3d.view_distance=16
            s.region_3d.view_location=Vector((0,-.3,2.2)); s.region_3d.view_rotation=camera.rotation_euler.to_quaternion()
assets=[o for c in assetcols for o in c.objects]
for o in scene.objects: o.select_set(False)
for o in assets: o.select_set(True)
bpy.context.view_layer.objects.active=asset
fbx=OUT/f'StarterHouse_v{version:03d}.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','EMPTY'},apply_unit_scale=True,
    bake_anim=False,axis_forward='-Z',axis_up='Y',mesh_smooth_type='FACE')
for o in scene.objects: o.select_set(False)
asset.select_set(True); bpy.context.view_layer.objects.active=asset
blend=OUT/f'StarterHouse_v{version:03d}.blend'; bpy.ops.wm.save_as_mainfile(filepath=str(blend))
meshes=[o for o in assets if o.type=='MESH']
info={'stage':'Editable exterior first pass','blender':bpy.app.version_string,'mesh_objects':len(meshes),
      'base_triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes),
      'wall_footprint_m':[7.2,5.2],'floor_height_m':.54,'door_opening_m':[1.7,2.41],
      'window_modules':5,'door_hinges':['Door_Left_Hinge','Door_Right_Hinge'],
      'limits':['No furnished interior, door animation or gameplay','No UV bake, collision meshes or LOD',
                'Procedural materials export only base colors to FBX','Unity import not yet verified']}
(OUT/'model_info.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
print('SAVED',blend,flush=True)
for name,loc,target,scale in [('01_front_right',(11,-16,10),(0,-.3,2.25),14.4),
                              ('02_front',(0,-20,6),(0,-.5,2.2),12.4),
                              ('03_rear_left',(-12,16,9),(0,0,2.3),14.2)]:
    camera.location=loc; aim(camera,target); camdata.ortho_scale=scale
    scene.render.filepath=str(OUT/(name+'.png')); bpy.ops.render.render(write_still=True)
    print('RENDERED',name,flush=True)
print('COMPLETE',json.dumps(info),flush=True)
