"""Extract the user's gnarled world tree from the Tree Companion garden source.

Run with 生命樹庭園_母稿.blend open in background Blender. Source is read only.
The island, waterfalls, cameras, and other props are intentionally excluded.
"""
import json
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(bpy.data.filepath)
if SOURCE.name != '生命樹庭園_母稿.blend':
    raise RuntimeError('Open 生命樹庭園_母稿.blend first')
collection_names = (
    '生命樹_主枝', '生命樹_主體', '生命樹_前景葉冠',
    '生命樹_後景葉冠', '生命樹_盤根與樹皮',
)
keep = set()
for name in collection_names:
    collection = bpy.data.collections.get(name)
    if collection is None:
        raise RuntimeError(f'Missing tree collection: {name}')
    keep.update(collection.objects)
for ob in list(keep):
    parent = ob.parent
    while parent:
        keep.add(parent)
        parent = parent.parent
for ob in list(bpy.data.objects):
    if ob not in keep:
        bpy.data.objects.remove(ob, do_unlink=True)
for ob in list(bpy.data.objects):
    if ob.type == 'CURVE':
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.convert(target='MESH')

meshes = [o for o in bpy.data.objects if o.type == 'MESH']
if not meshes:
    raise RuntimeError('No hero tree geometry found')
mesh_count = len(meshes)
face_count = sum(len(o.data.polygons) for o in meshes)
coords = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
lo = Vector(tuple(min(p[i] for p in coords) for i in range(3)))
hi = Vector(tuple(max(p[i] for p in coords) for i in range(3)))
dimensions = [round(hi[i]-lo[i],3) for i in range(3)]
offset = Matrix.Translation(Vector((-(lo.x+hi.x)/2,-(lo.y+hi.y)/2,-lo.z)))
for ob in bpy.data.objects:
    if ob.parent is None:
        ob.matrix_world = offset @ ob.matrix_world

out = ROOT/'art/exports/elder-world-tree-hero-v1'
out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/source/elder-world-tree-hero-v1.blend'))

# The original bark uses procedural nodes that glTF cannot represent. Keep
# those nodes in the editable .blend, then substitute an export-safe albedo.
bark_path=ROOT/'art/textures/elder-world-tree-hero-v1/bark-albedo.png'
if not bark_path.is_file():
    raise FileNotFoundError(bark_path)
bark_image=bpy.data.images.load(str(bark_path),check_existing=True)
for name in ('樹皮深棕','樹皮暖棕'):
    material=bpy.data.materials.get(name)
    if material is None:
        raise RuntimeError(f'Missing bark material {name}')
    pbr=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    albedo=material.node_tree.nodes.new('ShaderNodeTexImage')
    albedo.name='Export safe bark albedo'
    albedo.image=bark_image
    albedo.extension='REPEAT'
    material.node_tree.links.new(albedo.outputs['Color'],pbr.inputs['Base Color'])

# Batch meshes sharing a material. The editable source remains separate.
groups = {}
for ob in meshes:
    key = tuple(slot.material.name if slot.material else '<none>' for slot in ob.material_slots)
    groups.setdefault(key,[]).append(ob)
for index,items in enumerate(groups.values()):
    if len(items)<2:
        continue
    bpy.ops.object.select_all(action='DESELECT')
    for ob in items:
        ob.select_set(True)
    bpy.context.view_layer.objects.active=items[0]
    bpy.ops.object.join()
    bpy.context.view_layer.objects.active.name=f'SM_ElderWorldTree_Batch_{index:02d}'
export_meshes=[o for o in bpy.data.objects if o.type=='MESH']
for ob in export_meshes:
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active=ob
    if ob.parent is not None:
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    me=ob.data
    for old_uv in list(me.uv_layers):
        me.uv_layers.remove(old_uv)
    uv=me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        normal=poly.normal
        axis=max(range(3),key=lambda i:abs(normal[i]))
        for li in poly.loop_indices:
            p=me.vertices[me.loops[li].vertex_index].co
            coords=((p.y,p.z),(p.x,p.z),(p.x,p.y))[axis]
            uv.data[li].uv=(coords[0]*.4,coords[1]*.4)
bpy.ops.object.select_all(action='DESELECT')
for ob in export_meshes:
    ob.select_set(True)
bpy.context.view_layer.objects.active=export_meshes[0]
bpy.ops.export_scene.gltf(filepath=str(out/'elder-world-tree-hero-v1.glb'),
    export_format='GLB',use_selection=True,export_apply=True)
report={
    'source_repo':'elder-tree-esg',
    'source_file':str(SOURCE),
    'source_collections':collection_names,
    'mesh_count_source':mesh_count,
    'mesh_count_export':len(export_meshes),
    'faces_source':face_count,
    'dimensions_m':dimensions,
    'excluded':'floating island, waterfalls, lights, cameras, memorial markers',
    'limits':'Hero visual asset only; mobile LOD, wind, collision and Unity import unverified',
}
(out/'provenance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('@@HERO_TREE@@'+json.dumps(report,ensure_ascii=False))
