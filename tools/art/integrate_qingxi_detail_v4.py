"""Place the new house and an existing Tree Companion adult tree in Qingxi v3.

Run: blender -b art/source/qingxi-world-art-directed-v3.blend -P this_script
Only the local copied art asset is read; no Tree Companion live data is used.
"""
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'art/previews/qingxi-world-v4'
OUT.mkdir(parents=True,exist_ok=True)
scene=bpy.context.scene

detail=bpy.data.collections.new('WORLD_V4_DetailedGuesthouseAndTree')
scene.collection.children.link(detail)

# Replace exactly one old low-detail house, retaining all other collaborator art.
for old_name in ('Additional village house 02','Riverside blue-roof house',
                 'Collaborator intermediate pine 6','Riverbank moss rock 00'):
    old=bpy.data.objects.get(old_name)
    if old: old.hide_render=True; old.hide_set(True)

before=set(bpy.data.objects.keys())
bpy.ops.import_scene.gltf(filepath=str(ROOT/'art/exports/qingxi-riverside-house-v1/qingxi-riverside-house-v1.glb'))
new=[o for o in bpy.data.objects if o.name not in before and o.type=='MESH']
transform=Matrix.Translation(Vector((9,-18,.16))) @ Matrix.Rotation(math.radians(36),4,'Z') @ Matrix.Scale(1.08,4)
for ob in new:
    world=ob.matrix_world.copy()
    for c in list(ob.users_collection): c.objects.unlink(ob)
    detail.objects.link(ob)
    ob.matrix_world=transform @ world
    ob.name='GUESTHOUSE_'+ob.name

before=set(bpy.data.objects.keys())
bpy.ops.import_scene.gltf(filepath=str(ROOT/'art/incoming/elder-tree-esg/life-tree-growth-stages.glb'))
imported=[o for o in bpy.data.objects if o.name not in before]
adult=[o for o in imported if o.type=='MESH' and ('_4_' in o.name or '_04' in o.name)]
tree_transform=Matrix.Translation(Vector((19,-7,.16))) @ Matrix.Rotation(math.radians(-23),4,'Z') @ Matrix.Scale(1.65,4)
for ob in adult:
    world=ob.matrix_world.copy()
    ob.parent=None
    for c in list(ob.users_collection): c.objects.unlink(ob)
    detail.objects.link(ob)
    ob.matrix_world=tree_transform @ world
    ob.name='ELDER_TREE_REUSE_'+ob.name
for ob in imported:
    if ob not in adult:
        bpy.data.objects.remove(ob,do_unlink=True)

def camera(name,position,target,lens):
    data=bpy.data.cameras.new(name)
    ob=bpy.data.objects.new(name,data); scene.collection.objects.link(ob)
    ob.location=position
    ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
    data.lens=lens
    return ob

scene.camera=camera('CAM_V4_GuesthouseNearTree',(30,-45,16),(9,-15,3.5),37)
scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=1920;scene.render.resolution_y=1080
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.filepath=str(OUT/'qingxi-detailed-house-and-reused-tree-v4.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/source/qingxi-world-detail-v4.blend'))
bpy.ops.render.render(write_still=True)
print('@@V4@@house_meshes=%s elder_tree_meshes=%s'%(len(new),len(adult)))
