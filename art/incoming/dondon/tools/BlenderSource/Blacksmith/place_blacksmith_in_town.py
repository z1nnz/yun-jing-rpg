"""Add the latest completed smithy to the first street, with a walkable-layout loop."""
import bpy
import math
import json
import random
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'Models/TownLayout/v001/TownLayout_v001.blend'
SMITHY=sorted((ROOT/'Models/Blacksmith').glob('v*/*.blend'))[-1]
BASE=ROOT/'Models/TownLayout'
version=1
while (BASE/f'v{version:03d}').exists(): version+=1
OUT=BASE/f'v{version:03d}'; OUT.mkdir(parents=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene
def collection(name):
    c=bpy.data.collections.new(name); scene.collection.children.link(c); return c
plot=collection('10_Blacksmith_NorthEast_Plot')
paths=collection('11_Smithy_Street_And_Return_Steps')
with bpy.data.libraries.load(str(SMITHY),link=False) as (src,dst):
    dst.collections=[n for n in src.collections if n[:2] in ('01','02','03','04','05','06','07','08')]
for c in dst.collections: plot.children.link(c)
smith=next(o for o in plot.all_objects if o.name.startswith('Blacksmith_ROOT'))
smith.location=(12,8,.24); smith.rotation_euler.z=-math.pi/2
stone=[bpy.data.materials[f'Bluestone_{i}'] for i in range(5)]
dark=bpy.data.materials['Deep_Stone_Joints']; rng=random.Random(1021)
def block(name,x0,x1,y0,y1,z0,z1,material):
    verts=[(x,y,z) for z in (z0,z1) for x,y in [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]]
    faces=[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    mesh=bpy.data.meshes.new(name+'_Mesh'); mesh.from_pydata(verts,[],faces); mesh.update()
    obj=bpy.data.objects.new(name,mesh); paths.objects.link(obj); mesh.materials.append(material)
    mod=obj.modifiers.new('Worn_Stone_Edges','BEVEL'); mod.width=.012; mod.segments=2
    return obj
def paving(name,x0,x1,y0,y1):
    block(name+'_Mortar',x0,x1,y0,y1,0,.19,dark)
    nx=max(1,round((x1-x0)/.8)); ny=max(1,round((y1-y0)/.8))
    dx=(x1-x0)/nx; dy=(y1-y0)/ny
    for i in range(nx):
        for j in range(ny):
            block(f'{name}_{i}_{j}',x0+i*dx+.012,x0+(i+1)*dx-.012,
                  y0+j*dy+.012,y0+(j+1)*dy-.012,.15,.24,stone[rng.randrange(5)])
paving('Northbound_Shop_Lane',6.65,9,2.05,11.8)
paving('Smithy_Stone_Apron',9,15.1,4.2,11.8)
paving('Return_Steps_Landing',4.4,6.65,8,10.4)
for i in range(6):
    top=1.32-(i+1)*.18
    for j in range(3):
        block(f'Return_Stair_{i+1}_{j+1}',2+i*.4,2+(i+1)*.4,8+j*.8+.01,8+(j+1)*.8-.01,
              0,top,stone[(i+j)%5])

markers=next(c for c in scene.collection.children if c.name.startswith('80_'))
old=scene.objects.get('Future_Smith_East')
if old:
    old.name='Smithy_Entry_Feet'; old.location=(9.45,8,.42)
    old['purpose']='Smithy entry layout reference only, not a gameplay component.'
for name,loc in [('Smithy_NPC_Work_Position',(12.8,7.4,.42)),('Return_Stair_Low',(4.6,9.2,.24))]:
    o=bpy.data.objects.new(name,None); markers.objects.link(o); o.location=loc
    o.empty_display_type='ARROWS'; o.empty_display_size=.5
studio=next(c for c in scene.collection.children if c.name.startswith('90_'))
def aim(o,target): o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.lights.new('Smithy_Plot_Fill','AREA'); d.energy=2400; d.size=8
o=bpy.data.objects.new('Smithy_Plot_Fill',d); studio.objects.link(o); o.location=(12,2,13); aim(o,(12,8,2))
d=bpy.data.lights.new('Smithy_Forge_Preview_Glow','POINT'); d.energy=25; d.color=(1,.22,.04); d.shadow_soft_size=.25
o=bpy.data.objects.new('Smithy_Forge_Preview_Glow',d); studio.objects.link(o)
o.parent=smith; o.location=(-1.8,.73,1.02)
bpy.context.view_layer.update()
deps=bpy.context.evaluated_depsgraph_get()
checks=[]
for y in (2.5,4,6,8,10,11):
    for x in (7.1,7.8,8.5):
        hit,pos,normal,index,obj,matrix=scene.ray_cast(deps,Vector((x,y,2.0)),Vector((0,0,-1)),distance=3)
        assert hit and .12<pos.z<.27,(x,y,tuple(pos),obj.name if obj else None)
        checks.append([x,y,round(pos.z,4)])
steps=[]
for i in range(6):
    x=2.2+i*.4
    hit,pos,normal,index,obj,matrix=scene.ray_cast(deps,Vector((x,9.2,2.4)),Vector((0,0,-1)),distance=3)
    expected=1.32-(i+1)*.18
    assert hit and abs(pos.z-expected)<.015,(i,pos.z,expected)
    steps.append(round(pos.z,4))

camera=scene.camera; camera.location=(-25,-36,32); aim(camera,(4,1.7,1.6)); camera.data.type='ORTHO'; camera.data.ortho_scale=40
scene.render.resolution_x=1600; scene.render.resolution_y=1100; scene.cycles.samples=32
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            s=area.spaces.active; s.region_3d.view_location=Vector((4,2,2)); s.region_3d.view_distance=40
            s.region_3d.view_rotation=camera.rotation_euler.to_quaternion()
exports=[]
for c in scene.collection.children:
    if c.name.startswith(('80_','90_')): continue
    exports.extend(o for o in c.all_objects if o.type in ('MESH','EMPTY'))
exports=list(dict.fromkeys(exports))
for o in scene.objects: o.select_set(False)
for o in exports: o.select_set(True)
bpy.context.view_layer.objects.active=smith
bpy.ops.export_scene.fbx(filepath=str(OUT/f'TownLayout_v{version:03d}.fbx'),use_selection=True,object_types={'MESH','EMPTY'},
    apply_unit_scale=True,bake_anim=False,axis_forward='-Z',axis_up='Y',mesh_smooth_type='FACE')
for o in scene.objects: o.select_set(False)
smith.select_set(True); bpy.context.view_layer.objects.active=smith
blend=OUT/f'TownLayout_v{version:03d}.blend'; bpy.ops.wm.save_as_mainfile(filepath=str(blend))
info=json.loads((SOURCE.parent/'layout_info.json').read_text())
info.update({'stage':'Plaza, house and smithy linked by a street loop',
             'blacksmith':{'source':str(SMITHY.relative_to(ROOT)),'location':[12,8,.24],'rotation_z_degrees':-90},
             'mesh_objects':sum(o.type=='MESH' for o in exports),'shop_lane_ray_samples':checks,
             'return_stair_heights_m':steps,'unity_verified':False})
(OUT/'layout_info.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
print('SAVED',blend,flush=True)
for name,loc,target,scale in [('01_town_with_smithy',(-25,-36,32),(4,1.7,1.6),40),
                              ('02_town_top_plan',(3.5,.5,45),(3.5,.5,0),42),
                              ('03_shop_street',(-6,-7,13),(10,3.5,2),25)]:
    camera.location=loc; aim(camera,target); camera.data.ortho_scale=scale
    scene.render.filepath=str(OUT/(name+'.png')); bpy.ops.render.render(write_still=True)
    print('RENDERED',name,flush=True)
print('COMPLETE',flush=True)
