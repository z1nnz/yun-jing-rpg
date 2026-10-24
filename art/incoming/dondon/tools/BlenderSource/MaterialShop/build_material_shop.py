"""Create a shop variant from the house, without modifying the house source."""
import bpy
import math
import json
import random
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'Models/StarterHouse/v004/StarterHouse_v004.blend'
BASE=ROOT/'Models/MaterialShop'; version=1
while (BASE/f'v{version:03d}').exists(): version+=1
OUT=BASE/f'v{version:03d}'; OUT.mkdir(parents=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene; scene.name='Qingxi_Material_Shop'
root=scene.objects['StarterHouse_ROOT']; root.name='MaterialShop_ROOT'
root['stage']='Editable general goods and materials shop exterior; no trading gameplay.'
rng=random.Random(1022)
goods=bpy.data.collections.new('08_Shop_Counter_Shelves_Goods'); scene.collection.children.link(goods)
awning=bpy.data.collections.new('09_Shop_Cloth_Awning_Sign'); scene.collection.children.link(awning)
for o in list(scene.objects):
    if o.name.startswith(('Porch_Bench_','Clay_Jar_','Front_Window_0','Front_Below_0')):
        bpy.data.objects.remove(o,do_unlink=True)
wood=bpy.data.materials['Aged_Chestnut_Timber']; board=bpy.data.materials['Worn_Porch_Boards']
plaster=bpy.data.materials['Warm_Lime_Plaster']; stone=bpy.data.materials['Blue_Stone_1']; brass=bpy.data.materials['Dark_Brass']
def material(name,color,roughness=.8):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    bs=m.node_tree.nodes['Principled BSDF']; bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Roughness'].default_value=roughness; return m
cloth=material('Shop_Ochre_Canvas',(.46,.29,.10)); sack=material('Shop_Linen_Sacks',(.46,.37,.22))
jars=[material('Shop_Glazed_Jar_'+str(i),c,.3) for i,c in enumerate([(.13,.24,.20),(.20,.14,.08),(.32,.29,.19)])]
herb=material('Shop_Dried_Herbs',(.12,.21,.065)); ore=material('Shop_Jade_Ore',(.08,.32,.28),.4)
grain=material('Shop_Grain',(.56,.40,.15)); dark=material('Shop_Dark_Coin_Centre',(.07,.055,.035))
def finish(o,name,mat,c,parent=root,bevel=0):
    o.name=name
    for old in list(o.users_collection): old.objects.unlink(o)
    c.objects.link(o); o.parent=parent; o.data.materials.append(mat)
    if bevel:
        m=o.modifiers.new('Soft_Edges','BEVEL'); m.width=bevel; m.segments=2
    return o
def box(name,loc,size,mat,c=goods,parent=root,bevel=.012):
    bpy.ops.mesh.primitive_cube_add(size=1); o=bpy.context.object; o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    finish(o,name,mat,c,parent,bevel); o.location=loc; return o
def cyl(name,loc,r,depth,mat,c=goods,parent=root):
    bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=r,depth=depth)
    o=finish(bpy.context.object,name,mat,c,parent,.006); o.location=loc; return o
def mesh(name,verts,faces,mat,c=goods,parent=root):
    data=bpy.data.meshes.new(name+'_Mesh'); data.from_pydata(verts,[],faces); data.update()
    o=bpy.data.objects.new(name,data); c.objects.link(o); o.parent=parent; data.materials.append(mat); return o
def empty(name,loc):
    o=bpy.data.objects.new(name,None); goods.objects.link(o); o.parent=root; o.location=loc
    o.empty_display_size=.2; return o
def lathe(name,profile,loc,scale,mat,parent=root):
    v=[(loc[0]+r*scale*math.cos(i*math.tau/24),loc[1]+r*scale*math.sin(i*math.tau/24),loc[2]+z*scale) for r,z in profile for i in range(24)]
    f=[(j*24+i,j*24+(i+1)%24,(j+1)*24+(i+1)%24,(j+1)*24+i) for j in range(len(profile)-1) for i in range(24)]
    f.extend([tuple(reversed(range(24))),tuple(range((len(profile)-1)*24,len(profile)*24))])
    o=mesh(name,v,f,mat,parent=parent)
    for p in o.data.polygons: p.use_smooth=True
    return o

# Sales hatch replaces the left paper window; retain a real clear opening.
box('Sales_Hatch_Lower_Wall',(-2.35,-2.5,.82),(1.35,.22,.56),plaster)
for x in (-3.08,-1.62): box('Sales_Hatch_Jamb',(x,-2.66,1.89),(.12,.18,1.65),wood)
box('Sales_Hatch_Header',(-2.35,-2.66,2.70),(1.62,.20,.13),wood)
box('Sales_Hatch_Sill',(-2.35,-2.66,1.10),(1.62,.28,.12),stone)
counter=empty('Sales_Counter_ROOT',(-2.35,-3.15,.54))
box('Counter_Cabinet',(0,0,.34),(1.82,.70,.68),wood,parent=counter)
box('Counter_Top',(0,0,.73),(1.94,.82,.10),board,parent=counter)
for i in range(8): box('Counter_Front_Plank',(-.79+i*.225,-.36,.34),(.212,.035,.58),board,parent=counter,bevel=.004)
box('Sales_Interior_Shelf',(-2.35,-2.18,1.75),(1.34,.40,.07),board)
jarprofile=[(.10,0),(.145,.05),(.15,.22),(.10,.32),(.08,.34),(.08,.38),(.055,.38),(.055,.33)]
for i in range(6):
    loc=(-3.0+(i%3)*.32,-3.25+(i//3)*.28,1.32)
    lathe(f'Counter_Medicine_Jar_{i}',jarprofile,loc,.85+jars.index(jars[i%3])*.1,jars[i%3])
    cyl('Jar_Cork',(loc[0],loc[1],loc[2]+.36*(.85+(i%3)*.1)),.065,.05,board)
for i in range(4): lathe('Interior_Jar_'+str(i),jarprofile,(-2.85+i*.33,-2.18,1.79),1.05,jars[(i+1)%3])

# Right-hand materials shelf, distinct from the residential bench.
shelf=empty('Goods_Shelf_ROOT',(2.35,-3.12,.54))
for x in (-.68,.68):
    for y in (-.23,.23): box('Shelf_Post',(x,y,.89),(.08,.08,1.78),wood,parent=shelf)
for z in (.12,.70,1.30,1.76): box('Goods_Shelf_Board',(0,0,z),(1.48,.55,.075),board,parent=shelf)
for i in range(4): lathe('Shelf_Jar_'+str(i),jarprofile,(1.84+i*.33,-3.12,1.30),1.0,jars[i%3])
sackprofile=[(.14,0),(.22,.06),(.24,.22),(.20,.42),(.10,.50),(.11,.54),(.08,.54),(.08,.49)]
for i in range(3):
    lathe('Material_Sack_'+str(i),sackprofile,(1.87+i*.47,-3.12,.71),.85,sack)
    cyl('Sack_Tie',(1.87+i*.47,-3.12,1.15),.09,.035,wood)
for i in range(7):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=.13)
    o=finish(bpy.context.object,'Raw_Jade_Ore_'+str(i),ore,goods)
    o.location=(1.86+(i%4)*.31,-3.15+(i//4)*.12,1.98); o.scale=(.8,.7,1.1+rng.random()*.6)
for i in range(2):
    box('Herb_Tray',(-1.83,-3.18+i*.28,1.34),(.36,.24,.05),board)
    for j in range(6):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=.08)
        o=finish(bpy.context.object,'Dried_Herb_Bundle',herb,goods)
        o.location=(-1.96+j*.045,-3.18+i*.28,1.42); o.scale=(.6,1.3,.5)

# Small canvas canopy and a coin emblem distinguish the shop at a distance.
verts=[]
for i in range(17):
    x=-3.65+i*3.0/16
    for j in range(7):
        t=j/6; y=-2.65-t*1.55
        z=2.88-t*.34-.11*math.sin(t*math.pi)+.025*math.sin(i*math.pi/2)
        verts.append((x,y,z))
faces=[(i*7+j,i*7+j+1,(i+1)*7+j+1,(i+1)*7+j) for i in range(16) for j in range(6)]
o=mesh('Canvas_Awning',verts,faces,cloth,awning)
solid=o.modifiers.new('Canvas_Thickness','SOLIDIFY'); solid.thickness=.015
for i in range(12):
    x=-3.525+i*.25
    box('Canvas_Valance',(x,-4.19,2.44+(.025 if i%2 else 0)),(.245,.025,.20),cloth,awning,bevel=.008)
for x in (-3.55,-.76):
    cyl('Awning_Support_Pole',(x,-4.05,1.27),.045,2.54,wood,awning)
    cyl('Awning_Stone_Foot',(x,-4.05,.07),.11,.14,stone,awning)
box('Shop_Sign_Bracket',(3.48,-3.25,2.63),(.10,.70,.10),wood,awning)
box('Shop_Hanging_Sign',(3.48,-3.61,2.25),(.51,.09,.65),wood,awning)
o=cyl('Shop_Coin_Emblem',(3.48,-3.67,2.25),.19,.025,brass,awning); o.rotation_euler.x=math.pi/2
box('Coin_Square_Centre',(3.48,-3.687,2.25),(.11,.012,.11),dark,awning,bevel=.004)

camera=scene.camera; camera.location=(11,-17,9); target=Vector((0,-.55,2.2))
camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler(); camera.data.ortho_scale=14.7
scene.cycles.samples=32
assets=[o for o in scene.objects if o.type in ('MESH','EMPTY') and not any(c.name.startswith('90_') for c in o.users_collection)]
for o in scene.objects: o.select_set(False)
for o in assets: o.select_set(True)
bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.fbx(filepath=str(OUT/f'MaterialShop_v{version:03d}.fbx'),use_selection=True,object_types={'MESH','EMPTY'},
                        apply_unit_scale=True,bake_anim=False,axis_forward='-Z',axis_up='Y',mesh_smooth_type='FACE')
for o in scene.objects: o.select_set(False)
root.select_set(True); bpy.context.view_layer.objects.active=root
blend=OUT/f'MaterialShop_v{version:03d}.blend'; bpy.ops.wm.save_as_mainfile(filepath=str(blend))
info={'stage':'Editable materials shop exterior prototype','derived_from':str(SOURCE.relative_to(ROOT)),
      'mesh_objects':sum(o.type=='MESH' for o in assets),'engine_target':'Unreal Engine; import not verified',
      'limitations':['No shop interactions, colliders, LOD or UV texture baking','FBX includes base colors only',
                     'Goods are illustrative prop examples, not a complete item catalogue']}
(OUT/'model_info.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
print('SAVED',blend,flush=True)
scene.render.filepath=str(OUT/'01_material_shop_overview.png'); bpy.ops.render.render(write_still=True)
print('COMPLETE',flush=True)
