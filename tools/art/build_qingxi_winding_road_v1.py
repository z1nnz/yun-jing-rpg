"""Build a 12 m winding village road from the saved AI three-view reference."""
import json
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
REF=ROOT/'art/references/qingxi-winding-road-v1/three-view.png'
if not REF.is_file():raise FileNotFoundError(REF)
TEX=ROOT/'art/textures/qingxi-riverbank-v2'
OUT=ROOT/'art/exports/qingxi-winding-road-v1'
PREVIEW=ROOT/'art/previews/qingxi-winding-road-v1'
for p in (OUT,PREVIEW):p.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1

def material(key,color,texture=None):
    m=bpy.data.materials.new('M_QXRoad_'+key)
    m.diffuse_color=(*color,1)
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=.88
    if texture:
        img=bpy.data.images.load(str(TEX/texture),check_existing=True)
        img.pack()
        node=m.node_tree.nodes.new('ShaderNodeTexImage');node.image=img
        node.extension='REPEAT'
        m.node_tree.links.new(node.outputs['Color'],p.inputs['Base Color'])
    return m
mats={
    'grass':material('Meadow',(.24,.4,.17),'grass-albedo.png'),
    'path':material('PackedEarth',(.5,.35,.2),'path-albedo.png'),
    'stone':material('Limestone',(.5,.48,.4),'stone-albedo.png'),
    'leaf':material('GrassBlade',(.28,.47,.2)),
}
group=bpy.data.collections.new('ASSET_WindingRoad_12m')
scene.collection.children.link(group)
def mesh(name,verts,faces,mat,uv_scale=.4):
    me=bpy.data.meshes.new(name)
    me.from_pydata(verts,[],faces);me.update()
    uv=me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        for li in poly.loop_indices:
            p=me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv=(p.x*uv_scale,p.y*uv_scale)
    ob=bpy.data.objects.new('SM_QXRoad_'+name,me)
    group.objects.link(ob);me.materials.append(mats[mat])
    return ob

def height(x,y):
    return .0275+.08*(1-math.cos(math.pi*y/6))+.025*math.sin(math.pi*x/3.5)*math.sin(math.pi*y/6)
ys=[-6+i*.25 for i in range(49)]
xs=[-3.5+i*.25 for i in range(29)]
verts=[(x,y,height(x,y)) for y in ys for x in xs]
faces=[]
for j in range(len(ys)-1):
    for i in range(len(xs)-1):
        a=j*len(xs)+i;faces.append((a,a+1,a+len(xs)+1,a+len(xs)))
mesh('MeadowSubstrate',verts,faces,'grass')

def path_bounds(y):
    # Periodic terms force identical cross sections at y = -6 and +6.
    center=.77*math.sin(math.pi*y/6)+.22*math.sin(3*math.pi*y/6)
    width=2.65+.22*math.cos(2*math.pi*y/6)+.12*math.sin(4*math.pi*y/6)
    left=center-width/2+.11*math.sin(5*math.pi*y/6)
    right=center+width/2+.09*math.sin(7*math.pi*y/6)
    return left,right
verts=[];faces=[]
for y in ys:
    left,right=path_bounds(y)
    for i in range(15):
        x=left+(right-left)*i/14
        verts.append((x,y,height(x,y)+.009))
for j in range(len(ys)-1):
    for i in range(14):
        a=j*15+i;faces.append((a,a+1,a+16,a+15))
mesh('IrregularPackedEarthPath',verts,faces,'path')

rng=random.Random(25102529)
placed=[]
for i in range(34):
    for attempt in range(80):
        y=rng.uniform(-5.7,5.7)
        left,right=path_bounds(y)
        edge=rng.choice((left,right))
        x=edge+rng.uniform(-.48,.48)
        size=rng.uniform(.08,.30)
        if all((x-px)**2+(y-py)**2>(size+ps+.035)**2 for px,py,ps in placed):
            placed.append((x,y,size))
            break
    else:
        continue
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=1,
        location=(x,y,height(x,y)+size*.26))
    ob=bpy.context.object;ob.name=f'SM_QXRoad_EdgeStone_{i:02d}'
    for c in list(ob.users_collection):c.objects.unlink(ob)
    group.objects.link(ob)
    ob.scale=(size*1.3,size*.85,size*.35)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    ob.data.materials.append(mats['stone'])

blade_vertices=[];blade_faces=[]
for i in range(124):
    y=rng.uniform(-5.9,5.9)
    left,right=path_bounds(y)
    x=rng.choice((left-rng.uniform(.12,1.1),right+rng.uniform(.12,1.1)))
    if abs(x)>3.35:continue
    z=height(x,y)
    for blade in range(5):
        angle=2*math.pi*blade/5+rng.uniform(-.2,.2)
        h=rng.uniform(.09,.29);r=.045
        dx=math.cos(angle);dy=math.sin(angle)
        b=len(blade_vertices)
        blade_vertices.extend([(x-r*dy,y+r*dx,z),(x+r*dy,y-r*dx,z),
                               (x+.07*dx,y+.07*dy,z+h)])
        blade_faces.append((b,b+1,b+2))
mesh('EdgeGrass',blade_vertices,blade_faces,'leaf')

source_objects=[o for o in group.objects if o.type=='MESH']
report={
    'asset':'Qingxi winding road 12m v1',
    'reference':str(REF.relative_to(ROOT)),
    'length_m':12,
    'minimum_path_width_m':2.3,
    'source_meshes':len(source_objects),
    'source_triangles':sum(len(p.vertices)-2 for o in source_objects for p in o.data.polygons),
    'limits':'Visual mesh only; collision, Unity import, LOD, and mobile performance unverified',
}
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/source/qingxi-winding-road-v1.blend'))

for key,mat in mats.items():
    items=[o for o in group.objects if o.type=='MESH' and o.data.materials and o.data.materials[0]==mat]
    if len(items)<2:continue
    bpy.ops.object.select_all(action='DESELECT')
    for o in items:o.select_set(True)
    bpy.context.view_layer.objects.active=items[0]
    bpy.ops.object.join()
    bpy.context.view_layer.objects.active.name='SM_QXRoad_Batch_'+key
export_objects=[o for o in group.objects if o.type=='MESH']
report['export_meshes']=len(export_objects)
(OUT/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
bpy.ops.object.select_all(action='DESELECT')
for o in export_objects:o.select_set(True)
bpy.context.view_layer.objects.active=export_objects[0]
bpy.ops.export_scene.gltf(filepath=str(OUT/'qingxi-winding-road-v1.glb'),
    export_format='GLB',use_selection=True,export_apply=True)

world=bpy.data.worlds.new('Preview daylight')
scene.world=world;world.use_nodes=True
bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND')
bg.inputs['Color'].default_value=(.65,.76,.85,1);bg.inputs['Strength'].default_value=.8
light=bpy.data.lights.new('Late morning','SUN');light.energy=1.6
sun=bpy.data.objects.new('Late morning',light);scene.collection.objects.link(sun)
sun.rotation_euler=Vector((-.5,.7,-1)).to_track_quat('-Z','Y').to_euler()
camera_data=bpy.data.cameras.new('Road preview')
camera=bpy.data.objects.new('Road preview',camera_data)
scene.collection.objects.link(camera);camera.location=(10,-14,9)
camera.rotation_euler=(Vector((0,0,.1))-camera.location).to_track_quat('-Z','Y').to_euler()
scene.camera=camera
scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=1600;scene.render.resolution_y=900
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX'
scene.render.filepath=str(PREVIEW/'winding-road-oblique-v1.png')
bpy.ops.render.render(write_still=True)
print('@@ROAD@@'+json.dumps(report,ensure_ascii=False))
