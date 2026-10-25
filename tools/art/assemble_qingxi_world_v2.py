"""Assemble a Qingxi visual slice from existing collaborator assets.

The terrain slabs and distant silhouettes are composition blockout, not new
finished props. Re-run with Blender 5.2 in background mode.
"""
import json
import math
import random
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "art" / "incoming" / "dondon"
OUT = ROOT / "art" / "previews" / "qingxi-world-v2"
OUT.mkdir(parents=True, exist_ok=True)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.view_settings.view_transform = "AgX"
scene.world.color = (.68, .76, .75)
scene.world.use_nodes = True
scene.world.node_tree.nodes.get("Background").inputs["Color"].default_value = (.78, .82, .78, 1)
scene.world.node_tree.nodes.get("Background").inputs["Strength"].default_value = 1.2
scene.render.image_settings.color_mode = "RGBA"

def mat(name, rgb, roughness=.87):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    return m

soil = mat("Terrain mossy ochre", (.39, .45, .29))
grass = mat("Terrace grass", (.27, .40, .26))
water = mat("Qingxi turquoise water", (.13, .42, .48), .34)
stone = mat("Warm pale stone", (.53, .54, .46))
trail = mat("Footpath sandstone", (.58, .50, .35))
farm = mat("Cultivated soil", (.34, .29, .20))
mist = mat("Far ridge blue", (.48, .59, .59))

def block(name, center, size, material):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    o = bpy.context.object
    o.name = name
    o.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    return o

def disk(name, center, radius, depth, material, vertices=64):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=center)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(material)
    return o

sources = {}
placements = []

def import_asset(name, version="v001"):
    key = (name, version)
    if key in sources:
        return sources[key]
    path = SOURCE / name / version / f"{name}_{version}.fbx"
    if not path.exists():
        raise FileNotFoundError(path)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(path), use_anim=False)
    imported = set(bpy.data.objects) - before
    meshes = [o for o in imported if o.type == "MESH"]
    if not meshes:
        raise RuntimeError(f"No meshes: {path}")
    mins = [min((o.matrix_world @ Vector(c)).to_tuple()[axis] for o in meshes for c in o.bound_box)
            for axis in range(3)]
    maxs = [max((o.matrix_world @ Vector(c)).to_tuple()[axis] for o in meshes for c in o.bound_box)
            for axis in range(3)]
    origin = Vector(((mins[0]+maxs[0])/2, (mins[1]+maxs[1])/2, mins[2]))
    # Collection instances preserve the source's mesh data and avoid repeating
    # thousands of Blender objects for each placed tree or house.
    collection = bpy.data.collections.new(f"SOURCE {name} {version}")
    for obj in imported:
        world = obj.matrix_world.copy()
        for old in list(obj.users_collection):
            old.objects.unlink(obj)
        collection.objects.link(obj)
        obj.matrix_world = world
    for obj in imported:
        if obj.parent is None:
            obj.matrix_world = Matrix.Translation(-origin) @ obj.matrix_world
    tris = sum(sum(max(0, len(poly.vertices)-2) for poly in o.data.polygons) for o in meshes)
    sources[key] = (collection, tris, str(path.relative_to(ROOT)).replace("\\", "/"))
    return sources[key]

def place(name, label, xy, z=0, rotation=0, scale=1, version="v001"):
    collection, tris, path = import_asset(name, version)
    obj = bpy.data.objects.new(label, None)
    scene.collection.objects.link(obj)
    obj.instance_type = "COLLECTION"
    obj.instance_collection = collection
    obj.location = (xy[0], xy[1], z)
    obj.rotation_euler.z = math.radians(rotation)
    obj.scale = (scale, scale, scale)
    placements.append({"asset": name, "version": version, "name": label,
        "x": xy[0], "y": xy[1], "z": z, "yaw_deg": rotation,
        "scale": scale, "source_triangles": tris, "source": path})
    return obj

def local_asset(filename, label, xy, z=0, rotation=0, scale=1):
    path = ROOT / "apps" / "game" / "Assets" / "YunJing" / "Models" / "QingxiWorldV1" / filename
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(path), use_anim=False)
    imported = set(bpy.data.objects)-before
    meshes = [o for o in imported if o.type == "MESH"]
    mins = [min((o.matrix_world @ Vector(c)).to_tuple()[a] for o in meshes for c in o.bound_box) for a in range(3)]
    maxs = [max((o.matrix_world @ Vector(c)).to_tuple()[a] for o in meshes for c in o.bound_box) for a in range(3)]
    offset = Vector((xy[0]-(mins[0]+maxs[0])/2, xy[1]-(mins[1]+maxs[1])/2, z-mins[2]))
    for o in imported:
        if o.parent is None:
            o.matrix_world = Matrix.Translation(Vector((xy[0],xy[1],z))) @ Matrix.Scale(scale,4) @ Matrix.Translation(-Vector(((mins[0]+maxs[0])/2,(mins[1]+maxs[1])/2,mins[2]))) @ o.matrix_world
    placements.append({"asset": filename, "name": label, "x": xy[0], "y": xy[1], "z": z,
                       "scale": scale, "source": str(path.relative_to(ROOT)).replace("\\", "/")})

# First playable slice. The river and terraces are temporary terrain masses;
# the architectural, vegetation, and cliff shapes below use existing models.
block("BLOCKOUT valley terrain", (0, 0, -.55), (180, 146, 1.1), soil)
block("BLOCKOUT village turf", (-40, 3, .04), (94, 106, .09), grass)
block("BLOCKOUT east forest turf", (58, -2, .04), (63, 115, .09), grass)
block("BLOCKOUT Qingxi river surface", (25, 0, .04), (13, 145, .08), water)
block("BLOCKOUT western river bank", (16, 0, .2), (4, 137, .38), stone)
block("BLOCKOUT eastern river bank", (34, 0, .2), (4, 137, .38), stone)
block("BLOCKOUT village path", (-20, 5, .14), (49, 3.4, .05), trail)
block("BLOCKOUT forest path", (56, 5, .14), (44, 3.4, .05), trail)
block("BLOCKOUT plaza approach", (-10, 18, .13), (3.6, 35, .05), trail)
disk("BLOCKOUT plaza stone floor", (-20, 29, .18), 10, .32, stone)
disk("BLOCKOUT ancient tree mound", (-27, 32, .48), 6.4, .75, grass)

# The collaborator's full village is used for this visual composition only.
# Its ~0.9M triangles / thousands of objects require a mobile LOD pass first.
place("TownLayout", "Collaborator town west of Qingxi", (-43, -1), .15, rotation=-6, version="v004")
place("StarterHouse", "Riverside blue-roof house", (-1, -16), .18, rotation=22, version="v004")
place("StarterHouse", "Plaza east-side blue-roof house", (1, 32), .18, rotation=-45, version="v004")
place("StarterHouse", "South market blue-roof house", (-14, -29), .18, rotation=125, version="v004")
place("HerbalStall", "Village herbal stall", (-17, 8), .20, rotation=90)
place("TrainingGround", "East training yard", (54, 21), .20)
place("HerbPlanter", "Herb planter by road A", (-4, 12), .22)
place("HerbPlanter", "Herb planter by road B", (-4, 14), .22)
for i in range(5):
    x = -70 + i*9
    block(f"BLOCKOUT farm soil {i}", (x, -47, .19), (6.5, 11, .24), farm)
    place("SpiritHerbGarden", f"Collaborator herb garden {i}", (x, -47), .31, scale=.72)

local_asset("qingxi-sacred-tree-v1.fbx", "Ancient tree at plaza", (-27, 32), .8, scale=2.15)
local_asset("qingxi-timber-bridge-v1.fbx", "Main Qingxi timber bridge", (25, 5), .23)
place("StoneArchBridge", "Southern stone arch crossing", (25, -36), .13, rotation=-90)
place("MountainStreamBend", "Eastern stream bend", (52, -26), .12)
place("MountainStreamBend", "Northern stream bend", (50, 40), .12, rotation=172)
for i, (x, y, rot) in enumerate([(3, 49, 82), (70, 47, -12), (78, 57, 25), (-71, 52, 52)]):
    block(f"BLOCKOUT cliff foot {i}", (x, y, 2.0), (15, 13, 4), stone)
    place("LayeredCliff", f"Collaborator layered cliff {i}", (x, y), 2.0, rotation=rot, scale=.60)
place("QCaveEntrance", "East cliff cave entrance", (71, 45), 1.1, rotation=180, version="v003")
place("SectGate", "Distant sect gate", (8, 60), 6.5, rotation=180)
place("MountainStoneStairs", "Northern stone ascent", (8, 50), .5)
place("MountainStonePath", "East cave path", (69, 35), .2)
place("CliffBoardwalk", "Northern overlook boardwalk", (39, 50), 2.2)

rng = random.Random(241025)
for i in range(19):
    x = rng.uniform(41, 85)
    y = rng.uniform(-57, 44)
    if abs(y-5) < 6 or (x > 68 and y > 31):
        continue
    place("CommonPine", f"Collaborator east pine {i:02d}", (x,y), .10,
          rotation=rng.randrange(360), scale=rng.uniform(.75, 1.15))
for i, (x,y) in enumerate([(-80,12),(-79,40),(-12,48),(6,44),(47,-41),(77,-42)]):
    place("CommonPine", f"Collaborator framing pine {i}", (x,y), .12, rotation=i*41)
for i, (x,y) in enumerate([(-17,45),(-37,49),(-6,43),(-3,25),(-8,-30),(-23,-39),
                           (9,-23),(50,-14),(59,-19),(70,-12),(78,9),(72,21)]):
    place("CommonPine", f"Collaborator intermediate pine {i}", (x,y), .12,
          rotation=i*27, scale=.85 if i%3 else 1.15)
for i in range(8):
    x = rng.uniform(46, 84); y = rng.uniform(-54, 39)
    if abs(y-5)<6: y += 9
    place("BambooClump", f"Collaborator bamboo {i:02d}", (x,y), .12, rotation=i*43,
          scale=rng.uniform(.65,.95))
for i in range(18):
    x = rng.uniform(-83,85); y = rng.uniform(-61,57)
    if abs(x-25)<9 or abs(y-5)<3: continue
    place("MossBoulderSet", f"Collaborator moss boulder {i:02d}", (x,y), .12,
          rotation=rng.randrange(360), scale=rng.uniform(.6,1.1))
for i in range(16):
    x = rng.uniform(-80,85); y = rng.uniform(-62,57)
    if abs(x-25)<8 or abs(y-5)<3: continue
    place("WildShrub", f"Collaborator wild shrub {i:02d}", (x,y), .12,
          rotation=rng.randrange(360), scale=rng.uniform(.6,1.0))

# Far silhouettes are deliberately simple graybox, inspired by the five
# references; future regions will replace these with measured modular sets.
# Distant mountains are outside this small slice; the five source images remain
# the art direction for later connected regions instead of crude cube towers.

bpy.ops.object.light_add(type="SUN", location=(0,0,90))
sun = bpy.context.object
sun.name = "Warm afternoon sun"
sun.data.energy = 3.4
sun.rotation_euler = (math.radians(28), math.radians(20), math.radians(-34))

def camera(name, at, location, ortho, file):
    bpy.ops.object.camera_add(location=location)
    c = bpy.context.object; c.name=name
    c.rotation_euler = (Vector(at)-c.location).to_track_quat("-Z","Y").to_euler()
    c.data.type = "ORTHO"
    c.data.ortho_scale = ortho
    scene.camera = c
    scene.render.filepath = str(OUT/file)
    bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/"art"/"source"/"qingxi-world-assembled-v2.blend"))
camera("Overview from southwest", (0,11,0), (123,-145,100), 185, "qingxi-assembled-overview-v2.png")
camera("Ancient tree and town", (-18,16,3), (49,-76,49), 100, "qingxi-assembled-village-v2.png")
camera("Forest and cliff", (45,18,3), (105,-55,52), 95, "qingxi-assembled-forest-v2.png")
(OUT/"placements.json").write_text(json.dumps(placements, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"@@QINGXI_V2@@ {len(placements)} model placements; {len(sources)} collaborator source assets")
