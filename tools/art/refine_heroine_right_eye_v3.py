"""Study the Heroine-01 right upper/lower eyelid on our CC0-based face.

The original AI eye three-view was saved before this edit. This script edits
only the local eye shape; it does not use any downloaded character mesh.
"""

import math
import pathlib

import bpy
from mathutils import Vector


ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE = ROOT / "art/source/heroine-01-face-module-v2.blend"
OUTPUT = ROOT / "art/source/heroine-01-right-eye-v3.blend"
PREVIEW = ROOT / "art/previews/heroine-01-right-eye-v3"
PREVIEW.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))

head = bpy.data.objects["SK_Heroine01_FaceStudy"]
old = head.data.shape_keys.key_blocks["Heroine01_JawAndEyeStudy"]
study = head.shape_key_add(name="RightEye_UpperLidStudy", from_mix=True)
old.value = 0
study.value = 1
changed = 0
for vertex in study.data:
    x, y, z = vertex.co
    dx = x - .044
    dz = z - .173
    if y > -.105 or abs(dx) > .055 or abs(dz) > .042:
        continue
    weight = math.exp(-((dx / .035) ** 2 + (dz / .020) ** 2))
    if weight < .04:
        continue
    # Bring the upper lid onto the iris; slightly raise the lower edge. Both
    # edits fade into the surrounding continuous CC0 face loops.
    if dz > 0:
        vertex.co.z -= .0048 * weight
    else:
        vertex.co.z += .0018 * weight
    # A restrained outer-corner rise keeps the eye from reading as a circle.
    vertex.co.z += .0015 * (dx / .04) * weight
    changed += 1

scene = bpy.context.scene
scene.render.resolution_x = 900
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
camera = scene.camera
camera_data = camera.data
for label, location, target, scale in (
    ("eye-front", (.044, -.38, .173), (.044, -.08, .174), .145),
    ("eye-three-quarter", (.22, -.31, .19), (.044, -.08, .174), .145),
    ("face-front", (0, -.8, .16), (0, -.005, .15), .43),
):
    camera.location = location
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.ortho_scale = scale
    scene.render.filepath = str(PREVIEW / f"{label}.png")
    bpy.ops.render.render(write_still=True)

scene.render.filepath = "//"
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT))
print("HEROINE_EYE_V3", changed, OUTPUT)
