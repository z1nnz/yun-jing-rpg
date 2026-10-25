"""Add terrain material and sky to the detailed road, river and world-tree slice.

Run: blender -b art/source/qingxi-world-detail-v4.blend -P this_script
No Unity runtime or gameplay collision is implied by these renders.
"""
import math
import json
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'art/previews/qingxi-world-v7';OUT.mkdir(parents=True,exist_ok=True)
scene=bpy.context.scene
group=bpy.data.collections.new('WORLD_V7_GuesthouseRiverbankSlice')
scene.collection.children.link(group)

# Replace the wrongly chosen growth-stage tree with the actual gnarled hero
# tree extracted from the Tree Companion garden source.
for ob in list(bpy.data.objects):
    if ob.name.startswith('ELDER_TREE_REUSE_'):
        bpy.data.objects.remove(ob,do_unlink=True)
before=set(bpy.data.objects.keys())
bpy.ops.import_scene.gltf(filepath=str(ROOT/'art/exports/elder-world-tree-hero-v1/elder-world-tree-hero-v1.glb'))
tree=[o for o in bpy.data.objects if o.name not in before and o.type=='MESH']
if len(tree)!=3:raise RuntimeError(f'Expected three batched hero-tree meshes, got {len(tree)}')
tree_transform=Matrix.Translation(Vector((19,-7,.16))) @ Matrix.Rotation(math.radians(-23),4,'Z') @ Matrix.Scale(1.0,4)
for ob in tree:
    world=ob.matrix_world.copy()
    ob.parent=None
    for c in list(ob.users_collection):c.objects.unlink(ob)
    group.objects.link(ob)
    ob.matrix_world=tree_transform @ world
    ob.name='ELDER_WORLD_TREE_HERO_'+ob.name

before=set(bpy.data.objects.keys())
bpy.ops.import_scene.gltf(filepath=str(ROOT/'art/exports/qingxi-riverbank-v2/qingxi-riverbank-v2.glb'))
module=[o for o in bpy.data.objects if o.name not in before and o.type=='MESH']
expected=json.loads((ROOT/'art/exports/qingxi-riverbank-v2/build-report.json').read_text(encoding='utf-8'))['mesh_objects_export']
if len(module)!=expected:raise RuntimeError(f'Expected {expected} exported riverbank meshes, got {len(module)}')
for ob in module:
    for c in list(ob.users_collection):c.objects.unlink(ob)
    group.objects.link(ob)

bank_centers=(-54,-42,-30,-18,-6,6,18)
for index,cy in enumerate(bank_centers):
    transform=Matrix.Translation(Vector((19,cy,.047)))
    for original in module:
        ob=original if index==0 else original.copy()
        if index:group.objects.link(ob)
        ob.matrix_world=transform @ original.matrix_world.copy() if index==0 else Matrix.Translation(Vector((0,cy-bank_centers[0],0))) @ original.matrix_world
        ob.name=f'RIVERBANK_{index}_{original.name}'

# Early ground-look pass. Only the visible top of the existing blockout terrain
# receives the meadow texture; side faces retain their current placeholder.
meadow=bpy.data.materials.get('M_QXBank_grass')
if meadow is None:raise RuntimeError('Imported meadow material missing')
for name in ('BLOCKOUT valley terrain','North_Terrace_Ground'):
    terrain=bpy.data.objects.get(name)
    if terrain is None or terrain.type!='MESH':
        raise RuntimeError(f'Missing existing terrain {name}')
    slot=len(terrain.data.materials)
    terrain.data.materials.append(meadow)
    uv=terrain.data.uv_layers.get('UVMap') or terrain.data.uv_layers.new(name='UVMap')
    for poly in terrain.data.polygons:
        if poly.normal.z>.75:
            poly.material_index=slot
        for li in poly.loop_indices:
            p=terrain.data.vertices[terrain.data.loops[li].vertex_index].co
            uv.data[li].uv=(p.x*.20,p.y*.20)

def simple_mat(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1)
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=.9
    return m
trail=bpy.data.materials.get('M_QXBank_path') or simple_mat('M_QX_SpurTrail',(.47,.36,.22))

# Curving spur connects the guesthouse entrance to the path on the west bank.
centers=[(11.1,-21.0,.20),(12.0,-20.7,.24),(13.1,-20.0,.29),
         (14.2,-19.3,.34),(15.1,-18.7,.39)]
verts=[]
for i,(x,y,z) in enumerate(centers):
    forward=Vector((centers[min(i+1,len(centers)-1)][0]-centers[max(i-1,0)][0],
                    centers[min(i+1,len(centers)-1)][1]-centers[max(i-1,0)][1]))
    forward.normalize()
    normal=Vector((-forward.y,forward.x))
    for s in (-1,1):verts.append((x+s*normal.x*.9,y+s*normal.y*.9,z))
faces=[(2*i,2*i+1,2*i+3,2*i+2) for i in range(len(centers)-1)]
me=bpy.data.meshes.new('Guesthouse path mesh');me.from_pydata(verts,[],faces);me.update()
uv=me.uv_layers.new(name='UVMap')
for poly in me.polygons:
    for loop_index in poly.loop_indices:
        p=me.vertices[me.loops[loop_index].vertex_index].co
        uv.data[loop_index].uv=(p.x*.42,p.y*.42)
ob=bpy.data.objects.new('SM_QX_GuesthouseToBankPath',me);group.objects.link(ob)
me.materials.append(trail)

def camera(name,location,target,lens):
    data=bpy.data.cameras.new(name)
    ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob)
    ob.location=location
    ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
    data.lens=lens;return ob

scene.render.engine='BLENDER_EEVEE'
# The sky panorama is shown to camera rays while a subdued color lights the
# scene, so the preview can keep the original material contrast.
sky_world=bpy.data.worlds.new('Qingxi daylight sky v1')
sky_world.use_nodes=True
scene.world=sky_world
nodes=sky_world.node_tree.nodes
nodes.clear()
env=nodes.new('ShaderNodeTexEnvironment')
env.image=bpy.data.images.load(str(ROOT/'art/textures/qingxi-sky-v1/daylight-panorama.png'),check_existing=True)
env.image.pack()
camera_bg=nodes.new('ShaderNodeBackground')
camera_bg.inputs['Strength'].default_value=.85
ambient_bg=nodes.new('ShaderNodeBackground')
ambient_bg.inputs['Color'].default_value=(.5,.63,.73,1)
ambient_bg.inputs['Strength'].default_value=.22
light_path=nodes.new('ShaderNodeLightPath')
mix=nodes.new('ShaderNodeMixShader')
output=nodes.new('ShaderNodeOutputWorld')
links=sky_world.node_tree.links
links.new(env.outputs['Color'],camera_bg.inputs['Color'])
links.new(light_path.outputs['Is Camera Ray'],mix.inputs[0])
links.new(ambient_bg.outputs[0],mix.inputs[1])
links.new(camera_bg.outputs[0],mix.inputs[2])
links.new(mix.outputs[0],output.inputs['Surface'])
sun=bpy.data.objects.get('ENV_Mood_Sun')
if sun and sun.type=='LIGHT':sun.data.energy=2.0
scene.render.resolution_x=1920;scene.render.resolution_y=1080
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX'
scene.view_settings.look='AgX - Medium High Contrast'
cameras=[
    camera('CAM_V7_BankOverview',(34,-49,19),(13,-18,2.9),38),
    camera('CAM_V7_BankWalkingView',(30,-32,5.8),(14,-18,2.2),39),
    camera('CAM_V7_ValleySky',(73,-94,47),(0,1,5),39),
]
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/source/qingxi-world-lookdev-v7.blend'))
for cam,file in zip(cameras,('riverbank-overview-v7.png','riverbank-walking-view-v7.png','valley-sky-v7.png')):
    scene.camera=cam;scene.render.filepath=str(OUT/file)
    bpy.ops.render.render(write_still=True)
print('@@V7@@seven winding shoreline modules, textured terrain, correct world tree, sky preview, existing bridge')
