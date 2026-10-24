"""Build the Yun Jing aptitude-test plaza after its AI three-view was saved and reviewed."""

import bpy
import hashlib
import json
import math
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
REFERENCE = ROOT / "art/references/world-master-v1/aptitude-plaza-three-view.png"
SOURCE = ROOT / "art/source/aptitude-plaza-v1.blend"
EXPORT = ROOT / "art/exports/aptitude-plaza-v1"
UNITY = ROOT / "apps/game/Assets/YunJing/Models/AptitudePlazaV1"
PREVIEW = ROOT / "art/previews/aptitude-plaza-v1.png"

assert REFERENCE.is_file(), "AI three-view reference must exist before modeling"
for directory in (SOURCE.parent, EXPORT, UNITY, PREVIEW.parent):
    directory.mkdir(parents=True, exist_ok=True)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.materials, bpy.data.curves, bpy.data.cameras, bpy.data.lights):
    pass

scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1600
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.world.color = (0.035, 0.05, 0.065)


def material(name, color, metallic=0.0, roughness=0.7, transmission=0.0, emission=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    if transmission:
        shader.inputs["Transmission Weight"].default_value = transmission
        shader.inputs["IOR"].default_value = 1.46
    if emission:
        shader.inputs["Emission Color"].default_value = (*emission, 1)
        shader.inputs["Emission Strength"].default_value = 0.45
    mat.diffuse_color = (*color, 1)
    return mat


STONE = material("Stone warm gray", (0.38, 0.40, 0.38), roughness=0.88)
STONE_DARK = material("Stone edge", (0.20, 0.23, 0.22), roughness=0.9)
BRONZE = material("Aged bronze", (0.20, 0.12, 0.055), metallic=0.72, roughness=0.42)
JADE = material("Cloudy jade", (0.18, 0.75, 0.53), roughness=0.18, transmission=0.28,
                emission=(0.08, 0.32, 0.21))
MOSS = material("Sparse moss", (0.13, 0.25, 0.09), roughness=0.95)

render_objects = []


def finish(obj, name, mat, bevel=0.0):
    obj.name = name
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new("Soft stone edges", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    obj["ai_reference"] = str(REFERENCE.relative_to(ROOT)).replace("\\", "/")
    obj["asset_version"] = "1"
    render_objects.append(obj)
    return obj


def cube(name, location, scale, mat=STONE, bevel=0.06):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(obj, name, mat, bevel)


def cylinder(name, radius, depth, z, mat=STONE, vertices=64, bevel=0.05):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=(0, 0, z))
    return finish(bpy.context.object, name, mat, bevel)


def torus(name, radius, minor, z, mat=BRONZE):
    bpy.ops.mesh.primitive_torus_add(major_radius=radius, minor_radius=minor,
                                    major_segments=64, minor_segments=8,
                                    location=(0, 0, z))
    return finish(bpy.context.object, name, mat, 0.0)


# Three low concentric tiers: 18 m diameter and 0.75 m total height.
cylinder("Plaza_Base_Lower", 9.0, 0.24, 0.12, STONE_DARK, 96, 0.06)
cylinder("Plaza_Base_Middle", 8.7, 0.24, 0.36, STONE, 96, 0.05)
cylinder("Plaza_Base_Upper", 8.4, 0.24, 0.60, STONE, 96, 0.05)
cylinder("Plaza_Floor", 8.15, 0.16, 0.77, STONE, 96, 0.035)

# Opposing entrance stairs. They overlap the circular tiers intentionally so the silhouette remains clean.
for side in (-1, 1):
    for index in range(4):
        y = side * (8.15 + index * 0.52)
        step_height = 0.66 - index * 0.16
        cube(f"Stair_{'North' if side > 0 else 'South'}_{index + 1}",
             (0, y, step_height / 2), (2.35, 0.34, step_height / 2), STONE, 0.045)
    for x in (-2.65, 2.65):
        cube(f"Stair_Cap_{side}_{x}", (x, side * 8.72, 0.44), (0.22, 0.62, 0.44), STONE_DARK, 0.05)

# Floor rings and four radial inlays make the test ritual readable from above.
for radius, width in ((2.25, 0.045), (3.15, 0.07), (6.15, 0.055), (7.45, 0.04)):
    torus(f"Floor_Inlay_Ring_{radius}", radius, width, 0.875, BRONZE)
for angle in (0, math.pi / 2, math.pi, math.pi * 1.5):
    x = math.sin(angle) * 4.65
    y = math.cos(angle) * 4.65
    bar = cube(f"Floor_Inlay_Radial_{round(angle, 2)}", (x, y, 0.875),
               (0.045, 2.25, 0.025), BRONZE, 0.015)
    bar.rotation_euler[2] = -angle

# Central pedestal, bronze focusing bands and the aptitude crystal.
cylinder("Pedestal_Base", 1.55, 0.32, 0.99, STONE_DARK, 64, 0.05)
cylinder("Pedestal_Step", 1.28, 0.28, 1.28, STONE, 64, 0.045)
cylinder("Pedestal_Core", 0.86, 0.52, 1.65, STONE, 48, 0.04)
torus("Pedestal_Bronze_Band", 0.91, 0.09, 1.72, BRONZE)
for angle in (0, math.pi / 2, math.pi, math.pi * 1.5):
    cube(f"Pedestal_Brace_{round(angle, 2)}",
         (math.sin(angle) * 0.88, math.cos(angle) * 0.88, 1.63),
         (0.11, 0.30, 0.38), BRONZE, 0.035).rotation_euler[2] = -angle

bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=0.53, radius2=0.16, depth=2.05,
                                location=(0, 0, 2.72))
crystal = finish(bpy.context.object, "Aptitude_Crystal", JADE, 0.045)
crystal.rotation_euler[2] = math.radians(22.5)

# Four modest marker pillars at cardinal points.
for label, x, y, rotation in (("East", 6.25, 0, 0), ("West", -6.25, 0, 0),
                              ("North", 0, 6.25, math.pi / 2), ("South", 0, -6.25, math.pi / 2)):
    cube(f"Marker_{label}_Foot", (x, y, 1.02), (0.55, 0.55, 0.18), STONE_DARK, 0.045)
    cube(f"Marker_{label}_Shaft", (x, y, 1.88), (0.38, 0.38, 0.72), STONE, 0.055)
    cap = cube(f"Marker_{label}_Cap", (x, y, 2.64), (0.54, 0.54, 0.14), BRONZE, 0.04)
    cap.rotation_euler[2] = rotation
    # A restrained jade inset that can receive emissive animation in Unity later.
    inset = cube(f"Marker_{label}_Jade", (x, y - 0.391 if y <= 0 else y - 0.391, 2.0),
                 (0.13, 0.035, 0.27), JADE, 0.025)
    if label in ("East", "West"):
        inset.location = (x - (0.391 if x > 0 else -0.391), y, 2.0)
        inset.rotation_euler[2] = math.pi / 2

# Small moss patches kept as separate togglable detail geometry.
for index, (x, y, sx, sy) in enumerate(((-5.4, -4.1, .8, .22), (4.8, 4.7, .65, .18),
                                        (-2.8, 6.9, .55, .16), (6.4, -2.5, .48, .15))):
    patch = cube(f"Moss_Patch_{index+1}", (x, y, 0.89), (sx, sy, 0.015), MOSS, 0.02)
    patch.rotation_euler[2] = math.atan2(y, x)

# Mark all render geometry for import tooling.
for obj in render_objects:
    obj["game_layer"] = "crystal" if obj is crystal else "detail" if "Inlay" in obj.name or "Moss" in obj.name else "body"


def select(objects):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]


select(render_objects)
bpy.ops.export_scene.gltf(filepath=str(EXPORT / "aptitude-plaza-v1.glb"), export_format="GLB",
                          use_selection=True, export_apply=True)
bpy.ops.export_scene.fbx(filepath=str(UNITY / "aptitude-plaza-v1.fbx"), use_selection=True,
                         object_types={"MESH"}, apply_unit_scale=True, axis_forward="-Z", axis_up="Y",
                         bake_anim=False, mesh_smooth_type="FACE", path_mode="RELATIVE")

# Save editable source before adding preview-only objects.
for image in bpy.data.images:
    if image.source == "FILE" and image.filepath:
        image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))

# Preview stage.
bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, -0.025))
preview_ground = bpy.context.object
preview_ground.name = "Preview-only ground"
preview_ground.data.materials.append(material("Preview ground", (0.055, 0.07, 0.075), roughness=1.0))
for name, location, power, size in (("Key", (-9, -10, 14), 1850, 8),
                                    ("Fill", (9, 2, 8), 900, 6),
                                    ("Rim", (1, 10, 12), 1250, 5)):
    bpy.ops.object.light_add(type="AREA", location=location)
    lamp = bpy.context.object
    lamp.name = name
    lamp.data.energy = power
    lamp.data.shape = "DISK"
    lamp.data.size = size
    lamp.rotation_euler = (Vector((0, 0, 1.0)) - lamp.location).to_track_quat("-Z", "Y").to_euler()
bpy.ops.object.camera_add(location=(15, -20, 16))
camera = bpy.context.object
camera.rotation_euler = (Vector((0, 0, 1.0)) - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.type = "ORTHO"
camera.data.ortho_scale = 23
scene.camera = camera
scene.view_settings.look = "AgX - Medium High Contrast"
scene.render.filepath = str(PREVIEW)
bpy.ops.render.render(write_still=True)

triangles = 0
for obj in render_objects:
    obj.data.calc_loop_triangles()
    triangles += len(obj.data.loop_triangles)

report = {
    "asset": "AptitudePlaza",
    "version": "v1",
    "blender": bpy.app.version_string,
    "units": "meters",
    "diameter_m": 18.0,
    "height_to_crystal_m": 3.745,
    "objects": len(render_objects),
    "triangles": triangles,
    "reference": {
        "file": str(REFERENCE.relative_to(ROOT)).replace("\\", "/"),
        "sha256": hashlib.sha256(REFERENCE.read_bytes()).hexdigest(),
        "reviewed_before_modeling": True,
    },
    "exports": {
        "blend": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
        "fbx": str((UNITY / "aptitude-plaza-v1.fbx").relative_to(ROOT)).replace("\\", "/"),
        "glb": str((EXPORT / "aptitude-plaza-v1.glb").relative_to(ROOT)).replace("\\", "/"),
        "preview": str(PREVIEW.relative_to(ROOT)).replace("\\", "/"),
    },
    "limits": [
        "Concept materials only; texture baking and final UV polish are pending.",
        "Unity import, prefab generation, collision and mobile performance are not yet verified.",
        "Marker jade orientation will be finalized after in-engine camera review.",
    ],
}
(EXPORT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("APTITUDE_PLAZA_COMPLETE " + json.dumps(report, ensure_ascii=False))
