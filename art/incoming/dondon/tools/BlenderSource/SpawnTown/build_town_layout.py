"""Place the existing house east of the spawn plaza, retaining original asset files.
Run in Blender background mode. Every run creates a new TownLayout version.
"""
import bpy
import math
import json
import random
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
PLAZA=ROOT/'Models/SpawnTown/v001/SpawnTown_v001.blend'
HOUSE=ROOT/'Models/StarterHouse/v004/StarterHouse_v004.blend'
BASE=ROOT/'Models/TownLayout'
version=1
while (BASE/f'v{version:03d}').exists(): version+=1
OUT=BASE/f'v{version:03d}'; OUT.mkdir(parents=True)
rng=random.Random(1017)
bpy.ops.wm.open_mainfile(filepath=str(PLAZA))
scene=bpy.context.scene; scene.name='Qingxi_First_Street'
scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1

def collection(name):
    c=bpy.data.collections.new(name); scene.collection.children.link(c); return c
housecoll=collection('08_StarterHouse_East_Plot')
paths=collection('09_Connecting_Paths')
with bpy.data.libraries.load(str(HOUSE),link=False) as (src,dst):
    dst.collections=[n for n in src.collections if n[:2] in ('01','02','03','04','05','06','07')]
for c in dst.collections: housecoll.children.link(c)
house=next(o for o in housecoll.all_objects if o.name.startswith('StarterHouse_ROOT'))
house.location=(12,-2,.24); house.rotation_euler.z=-math.pi/2
house['layout_note']='Front faces west toward spawn plaza. Base rests on the +0.24 m stone apron.'
terrain=scene.objects['Terrain_Display_Island']
terrain.location=(3.5,.5,-.25); terrain.dimensions=(29,27,.5)
for o in scene.objects: o.select_set(False)
terrain.select_set(True); bpy.context.view_layer.objects.active=terrain
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)

# Open a genuine gap through the east curb, then move props clear of the walking route.
removed=[]
for i in (3,4,5,6):
    o=scene.objects.get(f'Plaza_Edge_1_{i}')
    if o:
        removed.append(o.name)
        for c in list(o.users_collection): c.objects.unlink(o)
for o in scene.objects:
    if o.name.startswith(('Bench_Seat_3.65','Bench_Support_3.65')):
        o.location+=Vector((3.45,3.8,0))
    if o.name.startswith('Waymarker_'):
        o.location.y+=1.2

stone=[bpy.data.materials[f'Bluestone_{i}'] for i in range(5)]
dark=bpy.data.materials['Deep_Stone_Joints']
def mesh(name,verts,faces,material):
    data=bpy.data.meshes.new(name+'_Mesh'); data.from_pydata(verts,[],faces); data.update()
    o=bpy.data.objects.new(name,data); paths.objects.link(o); data.materials.append(material)
    mod=o.modifiers.new('Worn_Edges','BEVEL'); mod.width=.012; mod.segments=2
    return o
def prism(name,poly,z0,z1,material):
    n=len(poly)
    return mesh(name,[(x,y,z) for z in (z0,z1) for x,y in poly],
                [tuple(reversed(range(n))),tuple(range(n,2*n))]+
                [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],material)
def paving(name,x0,x1,y0,y1,top):
    prism(name+'_Base',[(x0,y0),(x1,y0),(x1,y1),(x0,y1)],0,top-.05,dark)
    nx=max(1,round((x1-x0)/.85)); ny=max(1,round((y1-y0)/.85))
    points={}
    for j in range(ny+1):
        for i in range(nx+1):
            points[i,j]=(x0+(x1-x0)*i/nx+(rng.uniform(-.10,.10) if 0<i<nx else 0),
                         y0+(y1-y0)*j/ny+(rng.uniform(-.10,.10) if 0<j<ny else 0))
    for j in range(ny):
        for i in range(nx):
            p=[points[i,j],points[i+1,j],points[i+1,j+1],points[i,j+1]]
            cx=sum(v[0] for v in p)/4; cy=sum(v[1] for v in p)/4
            p=[(cx+(x-cx)*.965,cy+(y-cy)*.965) for x,y in p]
            prism(f'{name}_Slab_{i}_{j}',p,top-.1,top,stone[rng.randrange(5)])

# 2.6 m side street meets the porch steps. The full apron supports the house base.
paving('East_Lane',4.60,6.65,-3.30,-.70,.24)
paving('House_Apron',6.65,15.10,-6.0,2.05,.24)
# Extend the elevated main route through the gateway for later town expansion.
paving('North_Street',-2,2,6.7,11.7,1.32)

markers=next(c for c in scene.collection.children if c.name.startswith('80_'))
for name,loc in [('House_Entry_Feet',(9.12,-2,.78)),('East_Lane_Centre',(5.5,-2,.24)),
                 ('Next_Town_Block_North',(0,11.7,1.32))]:
    o=bpy.data.objects.new(name,None); markers.objects.link(o); o.location=loc
    o.empty_display_type='ARROWS'; o.empty_display_size=.5
    o['purpose']='Layout reference only; no gameplay or navigation implementation.'
# Update obsolete planning markers to match the new layout.
if 'Future_Smith_East' in scene.objects:
    scene.objects['Future_Smith_East'].location=(11,8,0)
    scene.objects['Future_Smith_East']['purpose']='Reserved smithy area north of starter house; unbuilt.'

studio=next(c for c in scene.collection.children if c.name.startswith('90_'))
def aim(o,target): o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.lights.new('House_Plot_Fill','AREA'); d.energy=2500; d.shape='DISK'; d.size=9
light=bpy.data.objects.new('House_Plot_Fill',d); studio.objects.link(light)
light.location=(12,-7,12); aim(light,(11,-2,2))
camera=scene.camera; camera.location=(-25,-36,30); aim(camera,(3.8,.3,1.5))
camera.data.type='ORTHO'; camera.data.ortho_scale=39
scene.render.resolution_x=1600; scene.render.resolution_y=1100; scene.render.resolution_percentage=100
scene.cycles.samples=32; scene.cycles.use_denoising=True
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            s=area.spaces.active; s.shading.type='MATERIAL'
            s.region_3d.view_distance=39; s.region_3d.view_location=Vector((4,0,2))
            s.region_3d.view_rotation=camera.rotation_euler.to_quaternion()
bpy.context.view_layer.update()

# Check the opened east passage: downward rays start below the roof height.
# This only checks static geometry clearance; character collisions remain a Unity task.
deps=bpy.context.evaluated_depsgraph_get()
samples=[]
for x in (2.5,3.5,4.65,5.4,6.5,7.1):
    for y in (-2.6,-2,-1.4):
        hit,pos,normal,index,obj,matrix=scene.ray_cast(deps,Vector((x,y,2)),Vector((0,0,-1)),distance=3)
        assert hit and .08<pos.z<.28,(x,y,hit,tuple(pos),obj.name if obj else None)
        samples.append({'x':x,'y':y,'surface_z':round(pos.z,4),'surface':obj.name})

exports=[]
for c in scene.collection.children:
    if c.name.startswith(('80_','90_')): continue
    exports.extend(o for o in c.all_objects if o.type in ('MESH','EMPTY'))
exports=list(dict.fromkeys(exports))
for o in scene.objects: o.select_set(False)
for o in exports: o.select_set(True)
bpy.context.view_layer.objects.active=house
fbx=OUT/f'TownLayout_v{version:03d}.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','EMPTY'},
                        apply_unit_scale=True,bake_anim=False,axis_forward='-Z',axis_up='Y',mesh_smooth_type='FACE')
for o in scene.objects: o.select_set(False)
house.select_set(True); bpy.context.view_layer.objects.active=house
blend=OUT/f'TownLayout_v{version:03d}.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
info={'stage':'Spawn plaza plus one house and connecting first street',
      'sources':[str(PLAZA.relative_to(ROOT)),str(HOUSE.relative_to(ROOT))],
      'house_location_blender_m':[12,-2,.24],'house_rotation_z_degrees':-90,
      'side_lane_width_m':2.6,'house_step_height_m':.18,
      'mesh_objects':sum(o.type=='MESH' for o in exports),'removed_curb_sections':removed,
      'east_passage_samples':samples,'unity_verified':False,
      'limitations':['Exterior layout only; no collision meshes, navmesh or gameplay',
                     'North elevated street end is a placeholder boundary, not a finished exit',
                     'FBX procedural materials need baking/rebuilding; no LOD optimisation']}
(OUT/'layout_info.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
print('SAVED',blend,flush=True)
views=[('01_town_overview',(-25,-36,30),(3.8,.3,1.5),'ORTHO',39),
       ('02_top_plan',(3.5,.5,45),(3.5,.5,0),'ORTHO',42),
       ('03_house_from_plaza',(2,-8,3.7),(11,-2,2.4),'PERSP',28)]
for name,loc,target,kind,value in views:
    camera.location=loc; aim(camera,target); camera.data.type=kind
    if kind=='ORTHO': camera.data.ortho_scale=value
    else: camera.data.lens=value
    scene.render.filepath=str(OUT/(name+'.png')); bpy.ops.render.render(write_still=True)
    print('RENDERED',name,flush=True)
print('COMPLETE',flush=True)
