"""Restore Tree Companion's existing hero scene for visual comparison.

This reads the user's original Blender garden and Unity textures. It does not
generate, rotate, duplicate, or remodel any part of the tree. The source file
is never saved over; a review copy is written into this repository.
"""

import json
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[2]
SOURCE_NAME = 'elder-world-tree-garden-original.blend'
if Path(bpy.data.filepath).name != SOURCE_NAME:
    raise RuntimeError(f'Open the preserved Tree Companion source {SOURCE_NAME} before running this script')

TEXTURES = ROOT / 'art/textures/elder-world-tree-faithful-v11'
OUT = ROOT / 'art/previews/elder-world-tree-faithful-v11'
OUT.mkdir(parents=True, exist_ok=True)


def color_texture(material_name, image_name, scale=(1, 1), projection='FLAT'):
    material = bpy.data.materials[material_name]
    nodes = material.node_tree.nodes
    nodes.clear()
    output = nodes.new('ShaderNodeOutputMaterial')
    pbr = nodes.new('ShaderNodeBsdfPrincipled')
    pbr.inputs['Roughness'].default_value = .83
    coordinates = nodes.new('ShaderNodeTexCoord')
    vector = nodes.new('ShaderNodeVectorMath')
    vector.operation = 'MULTIPLY'
    vector.inputs[1].default_value = (scale[0], scale[1], 1)
    image = nodes.new('ShaderNodeTexImage')
    image.image = bpy.data.images.load(str(TEXTURES/image_name), check_existing=True)
    image.projection = projection
    image.projection_blend = .30
    links = material.node_tree.links
    links.new(coordinates.outputs['UV' if projection == 'FLAT' else 'Generated'], vector.inputs[0])
    links.new(vector.outputs[0], image.inputs['Vector'])
    links.new(image.outputs['Color'], pbr.inputs['Base Color'])
    links.new(pbr.outputs['BSDF'], output.inputs['Surface'])


for name in ('樹皮深棕', '樹皮暖棕'):
    color_texture(name, 'bark-original-unity.png', (1.35, 2.8))

# The Unity tree renders the source's individual vertex-colored leaf meshes
# with a broad sunward tint. Recreate that color rule in Blender for review.
leaves = bpy.data.materials['立體葉片_柔霧玉綠']
nodes = leaves.node_tree.nodes
nodes.clear()
output = nodes.new('ShaderNodeOutputMaterial')
pbr = nodes.new('ShaderNodeBsdfPrincipled')
pbr.inputs['Roughness'].default_value = .88
pbr.inputs['Metallic'].default_value = 0
vertex = nodes.new('ShaderNodeVertexColor')
vertex.layer_name = '葉色'
geometry = nodes.new('ShaderNodeNewGeometry')
separate = nodes.new('ShaderNodeSeparateXYZ')
range_node = nodes.new('ShaderNodeMapRange')
range_node.inputs['From Min'].default_value = -3.6
range_node.inputs['From Max'].default_value = 3.2
range_node.inputs['To Min'].default_value = 0
range_node.inputs['To Max'].default_value = 1
range_node.clamp = True
tint = nodes.new('ShaderNodeMixRGB')
tint.blend_type = 'MIX'
tint.inputs[1].default_value = (.17, .39, .32, 1)
tint.inputs[2].default_value = (.55, .78, .38, 1)
multiply = nodes.new('ShaderNodeMixRGB')
multiply.blend_type = 'MULTIPLY'
multiply.inputs[0].default_value = 1
links = leaves.node_tree.links
links.new(geometry.outputs['Position'], separate.inputs[0])
links.new(separate.outputs['X'], range_node.inputs['Value'])
links.new(range_node.outputs['Result'], tint.inputs[0])
links.new(vertex.outputs['Color'], multiply.inputs[1])
links.new(tint.outputs[0], multiply.inputs[2])
links.new(multiply.outputs[0], pbr.inputs['Base Color'])
links.new(pbr.outputs['BSDF'], output.inputs['Surface'])
leaves.use_backface_culling = False

# Existing island surfaces use the original Tree Companion color maps. The
# Blender source's flat preview colors are kept if a material has no UVs.
for material_name, image_name in (
    ('浮島新芽草', 'island-grass-original-unity.png'),
    ('浮島暖灰岩', 'island-rock-original-unity.png'),
):
    color_texture(material_name, image_name, (.85, .85), projection='BOX')

scene = bpy.context.scene
scene.camera = bpy.data.objects['預覽_相機']
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 900
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'Standard'
scene.render.filepath = str(OUT / 'original-tree-and-island.png')

blend = ROOT / 'art/source/elder-world-tree-faithful-v11.blend'
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
bpy.ops.render.render(write_still=True)

report = {
    'source': SOURCE_NAME,
    'mesh_or_curve_count': sum(o.type in {'MESH', 'CURVE'} for o in bpy.data.objects),
    'tree_shape_changes': 0,
    'tree_rotation_changes': 0,
    'source_textures': ['bark', 'island grass', 'island rock'],
    'foliage': 'Original 16 leaf clusters and source vertex color with a Blender approximation of Unity sunward tint',
    'limits': 'Blender material comparison; not a Unity or phone render. Sky, water, and cloud rendering differ from Tree Companion.',
}
(OUT / 'build-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('@@ELDER_V11@@' + json.dumps(report, ensure_ascii=False))
