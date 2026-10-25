"""Compose Qingxi world presentation views from the v2 scene and existing models.

All additional architecture, vegetation and rocks are instances of collaborator
models. Existing terrain slabs remain visible blockout, not finished terrain art.
Run with Blender 5.2: blender -b art/source/qingxi-world-assembled-v2.blend -P this_file
"""
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "art" / "previews" / "qingxi-world-v3"
OUT.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.render.film_transparent = False
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"

base = bpy.data.collections.new("WORLD_V2_Base")
scene.collection.children.link(base)
for obj in list(scene.collection.objects):
    base.objects.link(obj)
    scene.collection.objects.unlink(obj)

added = bpy.data.collections.new("WORLD_V3_ExistingAssetInstances")
scene.collection.children.link(added)
refs = {c.name.split(" ", 1)[1]: c for c in bpy.data.collections
        if c.name.startswith("SOURCE ")}
placements = []

def instance(asset, name, xyz, size=1.0, angle=0.0, version="v001"):
    key = f"{asset} {version}"
    source = refs.get(key)
    if source is None:
        raise KeyError(f"Missing source collection: {key}")
    ob = bpy.data.objects.new(name, None)
    added.objects.link(ob)
    ob.instance_type = "COLLECTION"
    ob.instance_collection = source
    ob.location = xyz
    ob.rotation_euler.z = math.radians(angle)
    ob.scale = (size, size, size)
    placements.append({"asset": asset, "version": version, "name": name,
                       "position_m": list(xyz), "scale": size, "yaw_deg": angle})
    return ob

def node_color(mat, rgb, roughness=None):
    mat.diffuse_color = (*rgb, 1)
    bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*rgb, 1)
        if roughness is not None:
            bsdf.inputs["Roughness"].default_value = roughness

# The FBX has correct diffuse swatches but its shader nodes render ivory. Keep
# the original geometry; fix the material presentation of the existing tree.
for token, rgb in {
    "M_Canopy0": (.20, .40, .22),
    "M_Canopy1": (.29, .50, .23),
    "M_Canopy2": (.16, .34, .20),
    "M_SacredBark": (.29, .23, .15),
    "M_CeremonyRibbon": (.70, .29, .15),
}.items():
    material = bpy.data.materials.get(token)
    if material:
        node_color(material, rgb)
for obj in list(scene.objects):
    if obj.name.startswith("SM_qingxi_sacred_tree_v1_") and obj.type == "MESH":
        with bpy.context.temp_override(object=obj, active_object=obj,
                                       selected_objects=[obj],
                                       selected_editable_objects=[obj]):
            result = bpy.ops.object.transform_apply(location=False,
                                                    rotation=False, scale=True)
        if result != {'FINISHED'}:
            raise RuntimeError(f"Failed to apply tree scale: {obj.name}")
for name, rgb in {
    "Terrain mossy ochre": (.25, .36, .22),
    "Terrace grass": (.19, .34, .18),
    "Qingxi turquoise water": (.07, .29, .34),
    "Warm pale stone": (.45, .44, .35),
    "Footpath sandstone": (.48, .38, .24),
}.items():
    material = bpy.data.materials.get(name)
    if material:
        node_color(material, rgb, .25 if "water" in name.lower() else .82)

# Reuse architectural modules to form an arrival road and a wider river edge.
for i, (x, y, yaw) in enumerate([(32,-23,0),(32,-14,0),(32,19,0),
                                 (32,31,0),(55,51,76)]):
    instance("CliffBoardwalk", f"Waterfront boardwalk {i:02d}", (x,y,.18),
             .92 if i < 4 else 1.08, yaw)
instance("StoneArchBridge", "Northern stone crossing", (25,43,.15), 1.0, -90)
for i, (x, y, yaw) in enumerate([(49,-37,35),(61,-25,-55),
                                 (59,38,160),(71,32,20)]):
    instance("MountainStreamBend", f"Garden stream {i:02d}", (x,y,.11),
             .85, yaw)
for i, (x, y, yaw) in enumerate([(-7,-32,130),(-8,43,-20),
                                 (9,-18,55),(6,26,-120)]):
    instance("StarterHouse", f"Additional village house {i:02d}",
             (x,y,.16), .78 if i % 2 else .9, yaw, "v004")

# Repeated cliff faces, with an existing sect gate high at the northern end.
# This is only a distant silhouette; walkable grades still need terrain work.
for i, (x, y, z, scale, yaw) in enumerate([
    (-77,59,.4,.62,35),(-49,62,1.0,.57,-20),(-17,68,.4,.70,10),
    (9,71,1.6,.83,90),(35,69,.4,.72,-35),(63,67,.3,.62,30),
    (-60,83,4.0,.88,20),(25,83,4.0,.90,-25)
]):
    instance("LayeredCliff", f"Northern cliff layer {i:02d}",
             (x,y,z), scale, yaw)
instance("SectGate", "High northern gate", (9,77,19.6), 1.15, 180)
for i, (x,y,z) in enumerate([(-72,63,16),(-55,65,15),(-18,73,18),
                            (23,76,22),(38,72,18),(63,70,16)]):
    instance("CommonPine", f"Clifftop pine silhouette {i:02d}",
             (x,y,z), .75+(i%3)*.17, i*37)

# More vegetation belongs where terrain, water and habitation meet. Reuse the
# same mesh data through collection instances so this is easy to art direct.
rng = random.Random(251026)
pine_positions = [(-85,-33),(-81,-5),(-80,29),(-73,47),(-61,47),(-42,49),
                  (-16,53),(4,52),(23,51),(42,53),(67,51),(84,37),
                  (83,15),(83,-8),(79,-35),(71,-55),(51,-57),(37,-54),
                  (-72,-55),(-52,-54),(-35,-53),(-18,-51),(1,-51),
                  (44,-44),(58,-42),(77,-42),(56,-6),(70,-1),(48,25)]
for i, (x,y) in enumerate(pine_positions):
    size = [1.05,1.3,.86,1.55][i % 4]
    instance("CommonPine", f"Woodland pine extension {i:02d}",
             (x,y,.13), size, rng.randrange(360))
for i in range(20):
    x,y = rng.uniform(40,85),rng.uniform(-55,48)
    if abs(y-5)<7 or (x>68 and y>31):
        continue
    instance("CommonPine", f"Forest infill pine {i:02d}",
             (x,y,.13),rng.uniform(.75,1.1),rng.randrange(360))
for i, (x,y) in enumerate([(45,-45),(56,-50),(77,-51),(73,-24),(49,-14),
                           (67,13),(78,28),(44,43),(-78,46),(-53,44)]):
    instance("BambooClump", f"Bamboo bank extension {i:02d}",
             (x,y,.13),.75+rng.random()*.3,rng.randrange(360))
for i in range(22):
    x = rng.choice([rng.uniform(9,17),rng.uniform(34,39),rng.uniform(65,88)])
    y = rng.uniform(-58,54)
    instance("MossBoulderSet", f"Riverbank moss rock {i:02d}",
             (x,y,.13),rng.uniform(.6,1.2),rng.randrange(360))
for i in range(26):
    x,y = rng.uniform(-84,84),rng.uniform(-62,52)
    if abs(x-25)<9 or abs(y-5)<4:
        continue
    instance("WildShrub", f"Shrub infill {i:02d}",
             (x,y,.13),rng.uniform(.8,1.35),rng.randrange(360))

# Hide only the flat placeholder bank strips in this picture composition. The
# water, road and buildings remain; a future terrain pass will replace them.
for name in ("BLOCKOUT western river bank", "BLOCKOUT eastern river bank",
             "BLOCKOUT cliff foot 0", "BLOCKOUT cliff foot 1",
             "BLOCKOUT cliff foot 2", "BLOCKOUT cliff foot 3"):
    ob = bpy.data.objects.get(name)
    if ob:
        ob.hide_render = True
for ob in scene.objects:
    if ob.name.startswith("Collaborator layered cliff "):
        ob.location.z = 0

def make_camera(name, location, target, lens):
    cam_data = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam)
    cam.location = location
    cam.rotation_euler = (Vector(target)-cam.location).to_track_quat("-Z","Y").to_euler()
    cam_data.type = "PERSP"
    cam_data.lens = lens
    cam_data.clip_end = 1000
    return cam

hero = make_camera("CAM_AncientTreeVillage", (62,-100,51), (-24,20,7), 38)
river = make_camera("CAM_QingxiCrossing", (68,-105,34), (20,12,5), 44)
ridge = make_camera("CAM_NorthernSectVista", (-77,-69,34), (8,62,16), 43)
scene.camera = hero

old_sun = bpy.data.objects.get("Warm afternoon sun")
if old_sun:
    bpy.data.objects.remove(old_sun, do_unlink=True)
sys.path.insert(0, str(Path("C:/Users/User/.codex/skills/blender-time-of-day/scripts")))
import scene_mood
print("@@MOOD@@", json.dumps(scene_mood.run(time="afternoon", elevation=30,
                                           heading=95, fog_visibility=1500,
                                           fog_height=1.5,
                                           fog_color=(.68,.78,.85), grade=False)))
scene.view_settings.exposure = .45
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080

save_path = ROOT / "art" / "source" / "qingxi-world-art-directed-v3.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(save_path))
for cam, filename in [
    (hero,"qingxi-ancient-tree-village-v3.png"),
    (river,"qingxi-river-crossing-v3.png"),
    (ridge,"qingxi-northern-sect-v3.png"),
]:
    scene.camera = cam
    scene.render.filepath = str(OUT/filename)
    bpy.ops.render.render(write_still=True)

(OUT/"added-placements.json").write_text(json.dumps(placements, ensure_ascii=False, indent=2), encoding="utf-8")
print("@@WORLD_V3@@", json.dumps({"added_instances":len(placements),
                                  "blend":str(save_path),
                                  "images":[x.name for x in OUT.glob("*.png")]},ensure_ascii=False))
