"""Build the first editable Heroine-01 face study from Blender's CC0 human base.

Usage: blender -b --factory-startup -P this_file.py -- <human_base_meshes_bundle.blend>
The downloaded study archives are deliberately never opened or referenced here.
"""

import math
import pathlib
import sys

import bpy
from mathutils import Vector


ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE = pathlib.Path(sys.argv[sys.argv.index("--") + 1])
OUT_BLEND = ROOT / "art/source/heroine-01-face-module-v2.blend"
OUT_GLB = ROOT / "art/exports/heroine-01-face-module-v2-preview.glb"
OUT_PREVIEW = ROOT / "art/previews/heroine-01-face-module-v2"
OUT_PREVIEW.mkdir(parents=True, exist_ok=True)
OUT_BLEND.parent.mkdir(parents=True, exist_ok=True)
OUT_GLB.parent.mkdir(parents=True, exist_ok=True)

# This is a fresh background scene, never the user's open Blender project.
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)

names = ["GEO-head_stylized", "GEO-head_stylized.eye.L", "GEO-head_stylized.eye.R"]
with bpy.data.libraries.load(str(SOURCE), link=False) as (source, target):
    missing = set(names) - set(source.objects)
    if missing:
        raise RuntimeError(f"Official base mesh is missing: {sorted(missing)}")
    target.objects = names

parts = {}
for obj in target.objects:
    bpy.context.collection.objects.link(obj)
    obj.data = obj.data.copy()
    obj.hide_set(False)
    obj.hide_render = False
    obj.animation_data_clear()
    obj.parent = None
    obj.matrix_parent_inverse.identity()
    for modifier in list(obj.modifiers):
        obj.modifiers.remove(modifier)
    obj.location.x -= 2.083
    obj.location.z -= .5556
    parts[obj.name] = obj

head = parts["GEO-head_stylized"]
head.name = "SK_Heroine01_FaceStudy"
head.data.name = "Heroine01_EditableFaceQuads"
head.shape_key_add(name="CC0_Base", from_mix=False)
shape = head.shape_key_add(name="Heroine01_JawAndEyeStudy", from_mix=False)
shape.value = 1

# Primary sculpt only: a narrower jaw and softer chin. Keep the existing
# continuous eye, cheek and mouth loops instead of kitbashing face primitives.
for vertex in shape.data:
    x, y, z = vertex.co
    jaw = max(0, min(1, (.15 - z) / .17))
    vertex.co.x = x * (1 - .13 * jaw)
    if z < .06 and y < -.05:
        vertex.co.y += .003 * jaw
    if y < -.065:
        for eye_x in (-.044, .044):
            dx = x - eye_x
            weight = math.exp(-((dx / .043) ** 2 + ((z - .1726) / .037) ** 2))
            if weight < .02:
                continue
            vertex.co.z += (-(z - .1726) * .22 +
                            .003 * dx / .04 * (1 if eye_x > 0 else -1)) * weight


def material(name, color, roughness=.6):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


skin = material("M_Heroine01_SkinStudy", (.78, .58, .51), .55)
sclera = material("M_Heroine01_ScleraStudy", (.91, .88, .83), .28)
iris = material("M_Heroine01_IrisStudy", (.23, .105, .055), .26)
pupil = material("M_Heroine01_PupilStudy", (.012, .007, .007), .17)
head.data.materials.clear()
head.data.materials.append(skin)

for source_name, short in [("GEO-head_stylized.eye.L", "L"),
                           ("GEO-head_stylized.eye.R", "R")]:
    eye = parts[source_name]
    eye.name = f"SK_Heroine01_Eyeball_{short}"
    eye.data.name = f"Heroine01_EyeQuads_{short}"
    eye.location.y += .020
    eye.data.materials.clear()
    for mat in (sclera, iris, pupil):
        eye.data.materials.append(mat)
    for poly in eye.data.polygons:
        center = poly.center
        radius = math.hypot(center.x, center.z)
        poly.material_index = (2 if radius < .006 else 1 if radius < .015 else 0) if center.y < -.015 else 0
    for poly in eye.data.polygons:
        poly.use_smooth = True

for poly in head.data.polygons:
    poly.use_smooth = True

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 900
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.world.color = (.35, .35, .35)


def area(name, position, energy, size):
    light_data = bpy.data.lights.new(name, "AREA")
    light_data.energy = energy
    light_data.shape = "DISK"
    light_data.size = size
    light = bpy.data.objects.new(name, light_data)
    bpy.context.collection.objects.link(light)
    light.location = position
    light.rotation_euler = (Vector((0, 0, .16)) - light.location).to_track_quat("-Z", "Y").to_euler()


area("Key", (-.55, -.55, .55), 18, .8)
area("Fill", (.42, -.26, .28), 10, .65)
area("Rim", (0, .35, .5), 24, .5)

camera_data = bpy.data.cameras.new("ReviewCamera")
camera = bpy.data.objects.new("ReviewCamera", camera_data)
bpy.context.collection.objects.link(camera)
scene.camera = camera
camera_data.type = "ORTHO"
camera_data.ortho_scale = .43

for label, position in [("front", (0, -.8, .16)), ("three-quarter", (.48, -.65, .18)),
                        ("profile", (.8, -.05, .18))]:
    camera.location = position
    camera.rotation_euler = (Vector((0, -.005, .15)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(OUT_PREVIEW / f"{label}.png")
    bpy.ops.render.render(write_still=True)

camera_data.ortho_scale = .145
for label, position in [("eye-front", (.044, -.38, .173)),
                        ("eye-three-quarter", (.22, -.31, .19))]:
    camera.location = position
    camera.rotation_euler = (Vector((.044, -.08, .174)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(OUT_PREVIEW / f"{label}.png")
    bpy.ops.render.render(write_still=True)

scene.render.filepath = "//"
bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))
for obj in bpy.context.selected_objects:
    obj.select_set(False)
for obj in (head, parts["GEO-head_stylized.eye.L"], parts["GEO-head_stylized.eye.R"]):
    obj.select_set(True)
bpy.context.view_layer.objects.active = head
bpy.ops.export_scene.gltf(filepath=str(OUT_GLB), export_format="GLB", use_selection=True)
print("FACE_STUDY", OUT_BLEND, "head quads", len(head.data.polygons))
