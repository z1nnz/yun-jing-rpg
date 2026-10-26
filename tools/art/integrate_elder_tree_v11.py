"""Replace the altered Qingxi tree with the intact Tree Companion source tree.

Run against qingxi-world-detailed-v9.blend. No new geometry is authored here:
all branches, all 16 foliage meshes and all roots are appended unchanged.
Only the parent assembly is translated so the trunk enters the world ground.
"""

import json
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
HERO = ROOT / 'art/source/elder-world-tree-faithful-v11.blend'
OUT = ROOT / 'art/previews/qingxi-world-v11'
OUT.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene

old = [o for o in bpy.data.objects if o.name.startswith('ELDER_WORLD_TREE_HERO_')]
if len(old) != 3:
    raise RuntimeError(f'Expected three altered old tree meshes; got {len(old)}')
for ob in old:
    bpy.data.objects.remove(ob, do_unlink=True)

names = (
    '生命樹_主枝', '生命樹_主體', '生命樹_前景葉冠',
    '生命樹_後景葉冠', '生命樹_盤根與樹皮',
)
with bpy.data.libraries.load(str(HERO), link=False) as (src, dst):
    dst.collections = [n for n in names if n in src.collections]
if len(dst.collections) != len(names):
    raise RuntimeError('The Tree Companion source is missing a tree collection')

assembly = bpy.data.collections.new('WORLD_V11_OriginalTreeCompanion')
scene.collection.children.link(assembly)
loaded = set()
for collection in dst.collections:
    assembly.children.link(collection)
    loaded.update(collection.all_objects)

# All source objects share one parent empty. Move this one node, retaining
# every original child transform, original branch direction, and leaf layout.
top = [o for o in loaded if o.parent is None]
if len(top) != 1:
    raise RuntimeError(f'Expected one original tree root empty; got {[o.name for o in top]}')
top[0].location += Vector((12, 5, 1.03))
bpy.context.view_layer.update()

leaf = [o for o in loaded if o.type == 'MESH' and '立體葉冠' in o.name]
if len(leaf) != 16:
    raise RuntimeError(f'Original tree requires all 16 leaf meshes; got {len(leaf)}')
if any(not o.data.materials or not o.data.materials[0].name.startswith('立體葉片_柔霧玉綠') for o in leaf):
    raise RuntimeError('Original foliage material not retained')

cam_data = bpy.data.cameras.new('CAM_V11_OriginalTree')
cam = bpy.data.objects.new('CAM_V11_OriginalTree', cam_data)
scene.collection.objects.link(cam)
cam.location = (20, -9, 8.5)
cam.rotation_euler = (Vector((12, 5, 4.5)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
cam_data.lens = 36
scene.camera = cam
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1600
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'Standard'
scene.frame_set(36)

blend = ROOT / 'art/source/qingxi-world-original-tree-v11.blend'
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
scene.render.filepath = str(OUT / 'original-tree-in-world.png')
bpy.ops.render.render(write_still=True)

report = {
    'source': 'art/source/elder-world-tree-faithful-v11.blend',
    'removed_altered_meshes': len(old),
    'source_objects': len(loaded),
    'source_leaf_meshes': len(leaf),
    'tree_rotation_degrees': 0,
    'extra_or_duplicated_leaves': 0,
    'translation': [12, 5, 1.03],
    'limits': 'Blender review; Unity runtime and mobile performance unverified',
}
(OUT / 'build-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('@@V11_WORLD@@' + json.dumps(report, ensure_ascii=False))
