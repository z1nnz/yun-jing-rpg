"""Editable Qingxi smithy with masonry forge, tools and display weapons.
Run with Blender --background --factory-startup --python this_file.py.
"""
import bpy
import json
import math
import random
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'Models/Blacksmith'
version=1
while (BASE/f'v{version:03d}').exists(): version+=1
OUT=BASE/f'v{version:03d}'; OUT.mkdir(parents=True)
rng=random.Random(1020)
scene=bpy.data.scenes.new('Qingxi_Blacksmith'); bpy.context.window.scene=scene
scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1
def collection(name):
    c=bpy.data.collections.new(name); scene.collection.children.link(c); return c
floor=collection('01_Smithy_Foundation')
frame=collection('02_Open_Timber_Shelter')
roof=collection('03_Smithy_Tile_Roof')
forge=collection('04_Masonry_Forge_Chimney')
anvil=collection('05_Anvil_Hammer_Tongs')
bench=collection('06_Workbench_Ingots')
rack=collection('07_Weapon_Rack')
barrel=collection('08_Quench_Barrel_Coal')
studio=collection('90_Smithy_Studio_Not_Exported')
assetcols=[floor,frame,roof,forge,anvil,bench,rack,barrel]
def empty(name,c,parent=None,loc=(0,0,0)):
    o=bpy.data.objects.new(name,None); c.objects.link(o); o.parent=parent; o.location=loc
    o.empty_display_size=.25; return o
root=empty('Blacksmith_ROOT',floor)
root['stage']='Editable first-pass exterior and workshop props; no smithing gameplay.'
root['units']='metres'; root['front']='-Y'; root['floor_height_m']=.18
def mat(name,color,texture=False,metallic=0,emission=0):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    n,l=m.node_tree.nodes,m.node_tree.links; bs=n.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1); bs.inputs['Roughness'].default_value=.76 if not metallic else .4
    bs.inputs['Metallic'].default_value=metallic
    if emission:
        bs.inputs['Emission Color'].default_value=(*color,1); bs.inputs['Emission Strength'].default_value=emission
    if texture:
        co=n.new('ShaderNodeTexCoord'); noise=n.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value=6; noise.inputs['Detail'].default_value=3
        ramp=n.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].color=(*(v*.55 for v in color),1)
        ramp.color_ramp.elements[1].color=(*(min(v*1.3,1) for v in color),1)
        bump=n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.25; bump.inputs['Distance'].default_value=.025
        l.new(co.outputs['Object'],noise.inputs['Vector']); l.new(noise.outputs['Fac'],ramp.inputs[0])
        l.new(ramp.outputs[0],bs.inputs['Base Color']); l.new(noise.outputs['Fac'],bump.inputs['Height'])
        l.new(bump.outputs[0],bs.inputs['Normal'])
    return m
stone=[mat(f'Smithy_Bluestone_{i}',(.20+i*.025,.24+i*.025,.25+i*.025),True) for i in range(4)]
brick=[mat(f'Forge_Firebrick_{i}',(.22+i*.025,.17+i*.018,.12+i*.012),True) for i in range(4)]
wood=mat('Smithy_Aged_Timber',(.18,.078,.035),True)
board=mat('Smithy_Workbench_Wood',(.25,.135,.06),True)
tile=[mat(f'Smithy_Jade_Tile_{i}',(.07+i*.015,.14+i*.015,.15+i*.015),True) for i in range(4)]
iron=mat('Forged_Dark_Iron',(.095,.115,.12),True,.72)
steel=mat('Brushed_Sword_Steel',(.35,.42,.44),False,.8)
brass=mat('Smithy_Old_Brass',(.34,.23,.075),False,.65)
coal=mat('Charcoal',(.018,.015,.012),True)
glow=mat('Hot_Ember',(.8,.075,.009),False,0,2.2)
water=mat('Quench_Water',(.022,.06,.067)); water.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.18
dark=mat('Smithy_Joints',(.045,.05,.04))

def finish(o,name,material,c,parent=root,bevel=0):
    o.name=name
    for old in list(o.users_collection): old.objects.unlink(o)
    c.objects.link(o); o.parent=parent; o.data.materials.append(material)
    if bevel:
        b=o.modifiers.new('Soft_Worked_Edges','BEVEL'); b.width=bevel; b.segments=2
    return o
def box(name,loc,size,material,c,parent=root,bevel=.015):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o=bpy.context.object; o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    finish(o,name,material,c,parent,bevel); o.location=loc; return o
def mesh(name,verts,faces,material,c,parent=root,bevel=0):
    d=bpy.data.meshes.new(name+'_Mesh'); d.from_pydata(verts,[],faces); d.update()
    o=bpy.data.objects.new(name,d); c.objects.link(o); o.parent=parent; d.materials.append(material)
    if bevel:
        b=o.modifiers.new('Soft_Edges','BEVEL'); b.width=bevel; b.segments=2
    return o
def cyl(name,loc,radius,depth,material,c,parent=root,vertices=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth)
    o=finish(bpy.context.object,name,material,c,parent,.01); o.location=loc; return o
def rod(name,a,b,r,material,c,parent=root):
    a,b=Vector(a),Vector(b); o=cyl(name,(a+b)/2,r,(b-a).length,material,c,parent)
    o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler(); return o
def torus(name,loc,radius,minor,material,c,parent=root):
    bpy.ops.mesh.primitive_torus_add(major_radius=radius,minor_radius=minor,major_segments=32,minor_segments=6)
    o=finish(bpy.context.object,name,material,c,parent); o.location=loc; return o

# Low stone foundation keeps the open working floor accessible from a single step.
box('Smithy_Joint_Base',(0,-.1,.07),(6.8,5.6,.14),dark,floor)
for i in range(8):
    for j in range(7):
        box(f'Smithy_Floor_{i}_{j}',(-2.975+i*.85,-2.50+j*.8,.145),(.825,.777,.07),stone[(i+j)%4],floor,bevel=.012)
for x in (-3.05,3.05):
    for y in (-2.35,2.15):
        cyl(f'Column_Socket_{x}_{y}',(x,y,.31),.25,.26,stone[1],frame,vertices=8)
        cyl(f'Open_Post_{x}_{y}',(x,y,1.83),.13,2.95,wood,frame)
        rod(f'Column_Brace_{x}_{y}',(x,y,2.68),(x-math.copysign(.6,x),y,3.22),.065,wood,frame)
for y in (-2.35,2.15): box(f'Smithy_Header_{y}',(0,y,3.25),(6.45,.23,.24),wood,frame)
for x in (-3.05,3.05): box(f'Smithy_Side_Beam_{x}',(x,-.1,3.28),(.23,4.8,.22),wood,frame)
for row in range(4):
    for i in range(9):
        box(f'Rear_Masonry_{row}_{i}',(-2.85+i*.71,2.3,.30+row*.25),(.69,.22,.24),stone[(i+row)%4],frame)
for row in range(3):
    for j in range(6):
        box(f'Left_Low_Wall_{row}_{j}',(-3.18,-1.95+j*.78,.30+row*.25),(.20,.76,.24),stone[(j+row)%4],frame)

# Brick forge: a real arched opening, recessed coal bed, tapered hood and open chimney.
fx,fy=-1.8,1.05
box('Forge_Platform',(fx,fy,.405),(1.85,1.6,.45),stone[0],forge,bevel=.035)
box('Forge_Coal_Bed',(fx,fy,.665),(1.34,1.12,.08),coal,forge)
for side in (-1,1):
    for row in range(3):
        box(f'Forge_Side_{side}_{row}',(fx+side*.76,fy,.76+row*.23),(.29,1.5,.22),brick[row],forge)
box('Forge_Back_Wall',(fx,fy+.66,1.36),(1.8,.27,1.47),brick[1],forge)
for i in range(9):
    a0=i*math.pi/9+.012; a1=(i+1)*math.pi/9-.012
    poly=[(fx+r*math.cos(a),1.30+r*math.sin(a)) for r,a in [(.48,a0),(.72,a0),(.72,a1),(.48,a1)]]
    verts=[(x,y,z) for y in (fy-.77,fy-.40) for x,z in poly]
    mesh(f'Forge_Arch_Voussoir_{i}',verts,[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],brick[i%4],forge,bevel=.012)
for side in (-1,1):
    for row in range(3):
        box(f'Forge_Arch_Pier_{side}_{row}',(fx+side*.60,fy-.60,.75+row*.22),(.24,.36,.21),brick[row],forge)
# Hood overlaps the crown of the masonry arch; front opening remains unobstructed.
v=[(fx+x,fy+y,z) for z,hx,hy in [(1.98,.92,.78),(2.78,.43,.43)] for x,y in [(-hx,-hy),(hx,-hy),(hx,hy),(-hx,hy)]]
mesh('Forge_Tapered_Hood',v,[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],brick[0],forge,bevel=.02)
for row in range(11):
    z=2.90+row*.22
    for side in (-1,1):
        box(f'Chimney_Front_Back_{row}_{side}',(fx,fy+side*.35,z),(.86,.16,.215),brick[row%4],forge)
        box(f'Chimney_Left_Right_{row}_{side}',(fx+side*.35,fy,z),(.16,.54,.215),brick[(row+1)%4],forge)
for side in (-1,1):
    box(f'Chimney_Cap_FB_{side}',(fx,fy+side*.38,5.28),(1.03,.22,.16),stone[0],forge)
    box(f'Chimney_Cap_LR_{side}',(fx+side*.405,fy,5.28),(.22,.55,.16),stone[0],forge)
box('Chimney_Dark_Interior',(fx,fy,3.05),(.53,.53,.08),coal,forge)
for i in range(23):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=rng.uniform(.05,.105))
    o=finish(bpy.context.object,f'Ember_Coal_{i}',glow if i%3==0 else coal,forge)
    o.location=(fx+rng.uniform(-.47,.47),fy+rng.uniform(-.43,.36),.74)
heat=bpy.data.lights.new('Forge_Preview_Glow','POINT'); heat.energy=25; heat.color=(1,.22,.04); heat.shadow_soft_size=.25
o=bpy.data.objects.new('Forge_Preview_Glow',heat); studio.objects.link(o); o.location=(fx,fy-.32,1.02)

# Forging station and anvil, with a tapered horn instead of a rectangular placeholder.
aroot=empty('Anvil_Station_ROOT',anvil,root,(.15,-.75,.18))
cyl('Anvil_Stump',(0,0,.25),.42,.50,board,anvil,aroot,12)
for z in (.12,.40): torus('Stump_Iron_Band',(0,0,z),.425,.022,iron,anvil,aroot)
levels=[(.50,.34,.23),(.57,.30,.20),(.71,.19,.14),(.87,.25,.18),(.92,.45,.20)]
verts=[(x,y,z) for z,hx,hy in levels for x,y in [(-hx,-hy),(hx,-hy),(hx,hy),(-hx,hy)]]
faces=[(3,2,1,0),tuple(range(16,20))]+[(k*4+i,k*4+(i+1)%4,(k+1)*4+(i+1)%4,(k+1)*4+i) for k in range(4) for i in range(4)]
mesh('Anvil_Tapered_Body',verts,faces,iron,anvil,aroot,.015)
box('Anvil_Polished_Face',(0,0,.935),(.95,.42,.05),steel,anvil,aroot,.01)
bpy.ops.mesh.primitive_cone_add(vertices=16,radius1=.15,radius2=.015,depth=.46)
o=finish(bpy.context.object,'Anvil_Horn',iron,anvil,aroot,.008); o.location=(.66,0,.85); o.rotation_euler.y=math.pi/2
box('Anvil_Square_Tail',(-.56,0,.90),(.22,.28,.09),iron,anvil,aroot)

# Carpenter-like heavy bench plus recognizable hand tools and ingot stock.
broot=empty('Workbench_ROOT',bench,root,(1.65,1.25,.18))
for x in (-.84,.84):
    for y in (-.30,.30): box('Workbench_Leg',(x,y,.43),(.14,.14,.86),wood,bench,broot)
for j in range(4): box('Workbench_Plank',(0,-.31+j*.21,.91),(2.05,.20,.12),board,bench,broot)
box('Workbench_Lower_Shelf',(0,0,.24),(1.8,.64,.10),board,bench,broot)
for i in range(5): box(f'Stored_Ingot_{i}',(-.62+i*.30,0,.34),(.25,.36,.12),iron,bench,broot,.025)
rod('Hammer_Handle',(1.15,1.12,1.20),(1.85,1.30,1.20),.034,board,anvil)
box('Hammer_Steel_Head',(1.88,1.30,1.22),(.20,.36,.17),iron,anvil,bevel=.025)
rod('Tongs_Left',(2.24,1.02,1.18),(2.48,1.53,1.18),.018,iron,anvil)
rod('Tongs_Right',(2.40,1.02,1.18),(2.31,1.53,1.18),.018,iron,anvil)

# Upright display rack: blades, guards, wrapped grips and pommels are editable parts.
rroot=empty('Weapon_Rack_ROOT',rack,root,(2.1,-.85,.18))
for x in (-.72,.72):
    box('Rack_Foot',(x,0,.07),(.18,.78,.14),wood,rack,rroot)
    box('Rack_Upright',(x,.15,.86),(.12,.15,1.66),wood,rack,rroot)
for z in (.42,1.27): box('Rack_Crossbar',(0,.15,z),(1.6,.16,.14),board,rack,rroot)
for i in range(3):
    sroot=empty(f'Display_Sword_{i+1}_ROOT',rack,rroot,(-.45+i*.45,-.025,.34))
    rod('Sword_Grip',(0,0,0),(0,0,.23),.028,wood,rack,sroot)
    cyl('Sword_Pommel',(0,0,-.015),.05,.05,brass,rack,sroot)
    box('Sword_Guard',(0,0,.26),(.29,.09,.055),brass,rack,sroot)
    h=.98+i*.09; w=.055+i*.006
    verts=[(-w,0,.29),(0,-.025,.29),(w,0,.29),(0,.025,.29),(-w,0,h),(0,-.020,h),(w,0,h),(0,.020,h),(0,0,h+.20)]
    faces=[(3,2,1,0)]+[(j,(j+1)%4,(j+1)%4+4,j+4) for j in range(4)]+[(4+j,4+(j+1)%4,8) for j in range(4)]
    mesh('Sword_Blade',verts,faces,steel,rack,sroot)

# Open quench barrel with a visible water surface and separate iron bands.
qroot=empty('Quench_Barrel_ROOT',barrel,root,(-2.23,-1.5,.18))
profile=[(.31,0),(.36,.10),(.40,.37),(.36,.74),(.325,.74),(.36,.37),(.32,.10),(.28,.055)]
verts=[(r*math.cos(i*math.tau/20),r*math.sin(i*math.tau/20),z) for r,z in profile for i in range(20)]
faces=[(j*20+i,j*20+(i+1)%20,(j+1)*20+(i+1)%20,(j+1)*20+i) for j in range(len(profile)-1) for i in range(20)]
faces+=[tuple(reversed(range(20))),tuple(range((len(profile)-1)*20,len(profile)*20))]
mesh('Wooden_Quench_Barrel',verts,faces,board,barrel,qroot)
for z,r in ((.13,.37),(.61,.38)): torus('Barrel_Iron_Hoop',(0,0,z),r,.025,iron,barrel,qroot)
cyl('Barrel_Water',(0,0,.65),.333,.01,water,barrel,qroot,32)
box('Coal_Box_Base',(-2.50,-.15,.28),(.75,.65,.20),wood,barrel)
for i in range(16):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=rng.uniform(.055,.11))
    o=finish(bpy.context.object,f'Fuel_Coal_{i}',coal,barrel)
    o.location=(-2.50+rng.uniform(-.25,.25),-.15+rng.uniform(-.21,.21),.42)

# Curved ceramic canopy. Chimney opening is cut in both underlay and tile strips.
def roof_z(x,t): return 3.35+1.10*(1-t)**1.4+.16*t**8+.18*(abs(x)/3.65)**8
def chimney_hole(x,y): return abs(x-fx)<.53 and abs(y-fy)<.54
for side,depth in [(-1,3.0),(1,2.65)]:
    verts=[]; faces=[]
    for i in range(31):
        x=-3.65+i*7.3/30
        for j in range(25):
            t=j/24; verts.append((x,side*t*depth,roof_z(x,t)-.055))
    for i in range(30):
        for j in range(24):
            x=-3.65+(i+.5)*7.3/30; y=side*(j+.5)*depth/24
            if chimney_hole(x,y): continue
            face=(i*25+j,i*25+j+1,(i+1)*25+j+1,(i+1)*25+j)
            faces.append(tuple(reversed(face)) if side>0 else face)
    o=mesh(f'Canopy_Underlay_{side}',verts,faces,wood,roof)
    sol=o.modifiers.new('Roof_Underlay_Thickness','SOLIDIFY'); sol.thickness=.09
    for i in range(30):
        xc=-3.51+i*7.02/29; verts=[]; faces=[]
        for row in range(12):
            t0=row/12; t1=min(1,(row+1.08)/12)
            if chimney_hole(xc,side*(t0+t1)/2*depth): continue
            start=len(verts)
            for t in (t0,t1):
                for j in range(7):
                    a=math.pi*j/6; x=xc+.118*math.cos(a)
                    verts.append((x,side*t*depth,roof_z(x,t)+.055*math.sin(a)))
            for j in range(6):
                f=(start+j,start+j+1,start+j+8,start+j+7)
                faces.append(tuple(reversed(f)) if side>0 else f)
        o=mesh(f'Canopy_Tiles_{side}_{i}',verts,faces,tile[i%4],roof)
        sol=o.modifiers.new('Ceramic_Thickness','SOLIDIFY'); sol.thickness=.025
    for x in (-3.65,3.65):
        for j in range(12):
            t0=j/12; t1=(j+1)/12
            rod('Canopy_Fascia',(x,side*t0*depth,roof_z(x,t0)-.12),(x,side*t1*depth,roof_z(x,t1)-.12),.065,wood,roof)
for i in range(22):
    x=-3.65+i*7.3/22; xx=x+7.3/22
    rod('Canopy_Ridge',(x,0,roof_z(x,0)+.05),(xx,0,roof_z(xx,0)+.05),.11,tile[1],roof)
# Chimney flashing covers the small grid tolerance around the roof penetration.
for side in (-1,1):
    x=fx+side*.49
    rod('Chimney_Flashing_Side',(x,fy-.55,roof_z(x,(fy-.55)/2.65)+.015),
        (x,fy+.55,roof_z(x,(fy+.55)/2.65)+.015),.07,iron,roof)

# Studio lights and floor are excluded from the exported asset.
bg=mat('Smithy_Studio_Ground',(.25,.28,.27))
box('Smithy_Studio_Floor',(0,0,-.12),(200,200,.2),bg,studio,None,0)
world=bpy.data.worlds.new('Smithy_Daylight'); world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.55,.65,.74,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.5; scene.world=world
def aim(o,target): o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
for name,loc,power,size in [('Key',(-4,-8,10),1700,7),('Fill',(6,-5,6),1400,6),('Rim',(1,6,10),1700,6)]:
    d=bpy.data.lights.new('Smithy_'+name,'AREA'); d.energy=power; d.shape='DISK'; d.size=size
    o=bpy.data.objects.new('Smithy_'+name,d); studio.objects.link(o); o.location=loc; aim(o,(0,0,1.8))
data=bpy.data.cameras.new('Smithy_Overview'); camera=bpy.data.objects.new('Smithy_Overview',data)
studio.objects.link(camera); camera.location=(9,-16,8); aim(camera,(0,0,2.2)); data.type='ORTHO'; data.ortho_scale=12.5
scene.camera=camera; scene.render.engine='CYCLES'; scene.cycles.device='CPU'; scene.cycles.samples=40; scene.cycles.use_denoising=True
scene.render.resolution_x=1440; scene.render.resolution_y=1100; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.view_settings.view_transform='AgX'
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            s=area.spaces.active; s.shading.type='MATERIAL'; s.region_3d.view_distance=14
            s.region_3d.view_location=Vector((0,0,2)); s.region_3d.view_rotation=camera.rotation_euler.to_quaternion()
assets=list(dict.fromkeys(o for c in assetcols for o in c.all_objects))
for o in scene.objects: o.select_set(False)
for o in assets: o.select_set(True)
bpy.context.view_layer.objects.active=root
fbx=OUT/f'Blacksmith_v{version:03d}.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','EMPTY'},
    apply_unit_scale=True,bake_anim=False,axis_forward='-Z',axis_up='Y',mesh_smooth_type='FACE')
for o in scene.objects: o.select_set(False)
root.select_set(True); bpy.context.view_layer.objects.active=root
blend=OUT/f'Blacksmith_v{version:03d}.blend'; bpy.ops.wm.save_as_mainfile(filepath=str(blend))
meshes=[o for o in assets if o.type=='MESH']
info={'stage':'Editable smithy exterior and prop kit','mesh_objects':len(meshes),
      'base_triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes),
      'floor_footprint_m':[6.8,5.6],'floor_height_m':.18,'display_swords':3,
      'limits':['No crafting interaction, animation, colliders or LOD','No UV bake; FBX base colors only',
                'Ember material and preview light are not a fire simulation','Unity import not verified']}
(OUT/'model_info.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
print('SAVED',blend,flush=True)
for name,loc,target,scale,cut in [('01_smithy_overview',(9,-16,8),(0,0,2.2),12.5,False),
                                 ('02_workshop_roof_hidden',(8,-12,10),(0,0,1.4),10.6,True),
                                 ('03_smithy_rear',(-10,14,9),(0,0,2.3),12.5,False)]:
    roof.hide_render=cut
    camera.location=loc; aim(camera,target); data.ortho_scale=scale
    scene.render.filepath=str(OUT/(name+'.png')); bpy.ops.render.render(write_still=True)
    print('RENDERED',name,flush=True)
roof.hide_render=False
print('COMPLETE',json.dumps(info),flush=True)
