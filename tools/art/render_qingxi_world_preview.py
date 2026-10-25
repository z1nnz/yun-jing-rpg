"""Render the same first-pass world layout as QingxiWorldBuilder (visual blockout)."""
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"art"/"previews"/"qingxi-world-v1"
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
scene.unit_settings.scale_length=1
scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=1600
scene.render.resolution_y=1000
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.film_transparent=False
scene.world.color=(.72,.80,.79)
scene.view_settings.view_transform='AgX'

def material(name,color):
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*color,1)
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=.9
    return m

grass=material('BlockoutValleyGrass',(.35,.47,.30))
forest=material('BlockoutForest',(.19,.34,.25))
water=material('BlockoutQingxiWater',(.20,.48,.54))
path=material('BlockoutSandstonePath',(.67,.60,.45))
field=material('BlockoutField',(.41,.32,.20))
roof=material('BlockoutTealRoof',(.17,.27,.27))
wall=material('BlockoutHouseWall',(.65,.57,.42))
rock=material('BlockoutRidge',(.43,.48,.44))
bark=material('BlockoutBark',(.28,.25,.18))

def block(name,location,size,mat):
    bpy.ops.mesh.primitive_cube_add(size=1,location=location)
    o=bpy.context.object;o.name=name;o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(mat)
    return o

def sphere(name,location,size,mat):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=1,location=location)
    o=bpy.context.object;o.name=name;o.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(mat)
    return o

def asset(blend,collection,name,position):
    with bpy.data.libraries.load(str(ROOT/'art'/'source'/blend),link=False) as (source,target):
        target.collections=[collection]
    col=target.collections[0]
    if col is None: raise RuntimeError('Missing asset collection '+collection)
    scene.collection.children.link(col)
    for obj in col.objects:
        obj.location += Vector(position)
    return col

block('Valley walkable footprint',(0,0,-.38),(180,140,.7),grass)
block('Qingxi river',(25,0,.02),(10,139,.05),water)
for name,xyz,scale in [
    ('Village-plaza road',(0,14,.02),(3.2,48,.04)),
    ('Village-bridge road',(15,5,.02),(31,2.6,.04)),
    ('Eastern forest road',(50,5,.02),(42,2.6,.04)),
    ('Cave trail',(70,27,.02),(2.5,48,.04))]: block(name,xyz,scale,path)

asset('qingxi-timber-bridge-v1.blend','ASSET_TimberBridge_low','Qingxi timber bridge',(25,5,0))
asset('qingxi-sacred-tree-v1.blend','ASSET_SacredTree_low','Village sacred tree',(-13,27,0))

# The plaza is an earlier source asset with its own three-view; the ring also reads at distance.
bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=8,depth=.25,location=(0,29,.13))
plaza=bpy.context.object;plaza.name='Aptitude plaza footprint';plaza.data.materials.append(path)
bpy.ops.mesh.primitive_torus_add(major_segments=32,minor_segments=4,location=(0,29,.32),major_radius=6.2,minor_radius=.13)
bpy.context.object.name='Aptitude ring';bpy.context.object.data.materials.append(rock)

for i in range(7):
    x=-34+i*6
    block('Medicinal field blockout %02d'%i,(x,-28,.08),(4,12,.16),field)
    for row in range(3):
        for col in range(3): sphere('Field foliage marker',(x-1.1+col*1.1,-32+row*3,.38),(.35,.5,.38),forest)
for i in range(10):
    x=-54+(i%5)*9;y=-4+(i//5)*12
    block('Village house blockout %02d'%i,(x,y,1.65),(5,4,3.3),wall)
    block('Village roof blockout %02d'%i,(x,y,3.55),(6,5,.55),roof)
    block('Door marker %02d'%i,(x,y-2.04,1.05),(1.1,.08,2),bark)

random.seed(241025)
for i in range(54):
    x=38+random.random()*48;y=-47+random.random()*92
    if abs(y-5)<5 or (x>68 and y>34):continue
    block('Forest trunk blockout %02d'%i,(x,y,2.4),(.7,.7,4.8),bark)
    sphere('Forest crown blockout %02d'%i,(x,y,5.9),(2.1,2.1,1.6),forest)
block('Cave rock blockout',(73,48,3.2),(10,4,6.4),rock)
block('Cave opening marker',(73,45.95,2.1),(3.4,.1,4.2),roof)
for i in range(8):
    x=-80+i*21
    sphere('Distant sect ridge blockout %02d'%i,(x,67,9),(13,8,12),rock)
block('Distant mountain path blockout',(0,52,.05),(3,24,.1),path)

bpy.ops.object.light_add(type='SUN',location=(0,0,80))
sun=bpy.context.object;sun.name='Morning sun';sun.data.energy=2.4
sun.rotation_euler=(math.radians(30),math.radians(-35),math.radians(-25))
bpy.ops.object.camera_add(location=(95,-135,150))
camera=bpy.context.object;camera.name='World overview camera'
direction=Vector((4,5,0))-camera.location
camera.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO';camera.data.ortho_scale=215
scene.camera=camera
scene.render.filepath=str(OUT/'qingxi-world-blockout-v1.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art'/'source'/'qingxi-world-blockout-v1.blend'))
bpy.ops.render.render(write_still=True)
camera.location=(57,-62,64)
camera.rotation_euler=(Vector((9,12,0))-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.ortho_scale=100
scene.render.filepath=str(OUT/'qingxi-village-crossing-v1.png')
bpy.ops.render.render(write_still=True)
print('@@PREVIEW@@'+str(OUT/'qingxi-world-blockout-v1.png'))
