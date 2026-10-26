"""Build the Qingxi road close-up and three independent modular props.

Every new prop has a saved, inspected AI three-view before this script runs.
This is Blender/PWA art validation, not a Unity gameplay build.
"""
import json
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
REFS = {
    "road": ROOT / "art/references/qingxi-winding-road-v1/three-view.png",
    "rail": ROOT / "art/references/qingxi-bridge-rail-v1/three-view.png",
    "rack": ROOT / "art/references/qingxi-herb-rack-v1/three-view.png",
    "marker": ROOT / "art/references/qingxi-waymarker-v1/three-view.png",
}
for ref in REFS.values():
    if not ref.is_file():
        raise FileNotFoundError(f"Three-view must be saved before modeling: {ref}")

SRC = ROOT / "art/source"
EXP = ROOT / "art/exports/qingxi-road-props-v12"
PRE = ROOT / "art/previews/qingxi-road-props-v12"
for folder in (SRC, EXP, PRE):
    folder.mkdir(parents=True, exist_ok=True)

random.seed(261026)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1


def mat(name, rgb, texture=None, roughness=0.9):
    material = bpy.data.materials.new("M_QX12_" + name)
    material.use_nodes = True
    material.diffuse_color = (*rgb, 1)
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    if texture:
        img = bpy.data.images.load(str(ROOT / "art/textures/qingxi-riverbank-v2" / texture), check_existing=True)
        img.pack()
        node = material.node_tree.nodes.new("ShaderNodeTexImage")
        node.image = img
        material.node_tree.links.new(node.outputs["Color"], bsdf.inputs["Base Color"])
    return material


M = {
    "earth": mat("Earth", (.55, .39, .25), "path-albedo.png"),
    "meadow": mat("Meadow", (.3, .43, .19), "grass-albedo.png"),
    "stone": mat("Stone", (.38, .38, .34)),
    "stone_dark": mat("StoneDark", (.29, .3, .28)),
    "stone_warm": mat("StoneWarm", (.46, .42, .34)),
    "moss": mat("Moss", (.27, .38, .15)),
    "grass_a": mat("GrassA", (.11, .3, .055)),
    "grass_b": mat("GrassB", (.19, .37, .075)),
    "grass_c": mat("GrassC", (.16, .27, .08)),
    "flower_white": mat("FlowerWhite", (.93, .88, .64)),
    "flower_gold": mat("FlowerGold", (.92, .67, .19)),
    "flower_pink": mat("FlowerPink", (.7, .4, .43)),
    "wood": mat("Wood", (.34, .23, .14)),
    "wood_light": mat("WoodLight", (.52, .35, .2)),
    "bamboo": mat("Bamboo", (.56, .48, .29)),
    "herb": mat("Herb", (.3, .38, .17)),
    "rope": mat("Rope", (.68, .57, .34)),
}


def collection(name):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c


ROAD = collection("ASSET_QingxiWindingRoad_v2")
RAIL = collection("ASSET_QingxiBridgeRail_v1")
RACK = collection("ASSET_QingxiHerbRack_v1")
MARKER = collection("ASSET_QingxiWaymarker_v1")


def put(obj, target, name, material):
    obj.name = name
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    target.objects.link(obj)
    obj.data.materials.clear()
    obj.data.materials.append(M[material])
    return obj


def box(target, name, loc, scale, material, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = put(bpy.context.object, target, name, material)
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        modifier = obj.modifiers.new("SoftEdge", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
        obj.modifiers.new("WeightedNormals", "WEIGHTED_NORMAL")
    return obj


def ico(target, name, loc, scale, material, subdiv=1, seed=0):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv, radius=1, location=loc)
    obj = put(bpy.context.object, target, name, material)
    rnd = random.Random(seed)
    for vertex in obj.data.vertices:
        vertex.co *= rnd.uniform(.83, 1.14)
    obj.scale = scale
    return obj


def cylinder_between(target, name, p1, p2, radius, material, vertices=8):
    a, b = Vector(p1), Vector(p2)
    vec = b-a
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=vec.length, location=(a+b)/2)
    ob = put(bpy.context.object, target, name, material)
    ob.rotation_euler = vec.to_track_quat("Z", "Y").to_euler()
    return ob


def mesh(target, name, vertices, faces, material, uv_scale=.5):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    uv = data.uv_layers.new(name="UVMap")
    for polygon in data.polygons:
        for index in polygon.loop_indices:
            v = data.vertices[data.loops[index].vertex_index].co
            uv.data[index].uv = (v.x*uv_scale, v.y*uv_scale)
    ob = bpy.data.objects.new(name, data)
    target.objects.link(ob)
    data.materials.append(M[material])
    return ob


# Road: 12 m module, S curve, roughly 2.4 m clear central tread. The edge is
# intentionally irregular but joins at y = +/-6 with the same section.
def road_height(x, y):
    return .05 + .045*(1-math.cos(math.pi*y/6)) + .018*math.sin(1.8*x)*math.sin(math.pi*y/6)


def bounds(y):
    center = .72*math.sin(math.pi*y/6) + .2*math.sin(math.pi*y/2)
    width = 2.65 + .14*math.cos(math.pi*y/3)
    left = center-width/2 + .11*math.sin(math.pi*y*5/6)
    right = center+width/2 + .09*math.sin(math.pi*y*7/6)
    return left, right


ys = [-6 + i*.2 for i in range(61)]
xs = [-3.9 + i*.2 for i in range(40)]
ground_verts = []
for y in ys:
    edge_shift = .11*math.sin(math.pi*y/3)*math.sin(math.pi*y/6)
    for x in xs:
        shape_x = x + edge_shift*(abs(x)/3.9)**4
        ground_verts.append((shape_x, y, road_height(shape_x, y)))
ground_faces = []
for j in range(len(ys)-1):
    for i in range(len(xs)-1):
        a = j*len(xs)+i
        ground_faces.append((a, a+1, a+len(xs)+1, a+len(xs)))
mesh(ROAD, "SM_QX12_MeadowBase", ground_verts, ground_faces, "meadow")
path_vertices, path_faces = [], []
for y in ys:
    l, r = bounds(y)
    for i in range(19):
        x = l+(r-l)*i/18
        path_vertices.append((x, y, road_height(x, y)+.012))
for j in range(len(ys)-1):
    for i in range(18):
        a = j*19+i
        path_faces.append((a, a+1, a+20, a+19))
mesh(ROAD, "SM_QX12_IrregularPackedTread", path_vertices, path_faces, "earth")

rng = random.Random(2601026)
occupied = []
for i in range(84):
    y = rng.uniform(-5.85, 5.85)
    left, right = bounds(y)
    edge = left if rng.random() < .5 else right
    x = edge + rng.uniform(-.67, .67)
    size = rng.uniform(.055, .16) if i < 66 else rng.uniform(.17, .38)
    if abs(x)>3.73 or any((x-px)**2+(y-py)**2 < (size+ps+.035)**2 for px,py,ps in occupied):
        continue
    occupied.append((x,y,size))
    key = ("stone","stone_dark","stone_warm")[i%3]
    ico(ROAD, f"SM_QX12_ShoreStone_{i:03}", (x,y,road_height(x,y)+size*.19),
        (size*1.3,size*.9,size*.35), key, 1 if size<.2 else 2, i+981)

# Batched individual clusters: crossed tapered grass blades, small blossoms,
# and flat rosettes. These are deliberately concentrated at the road edge.
plant_vertices = {k:[] for k in ("grass_a","grass_b","grass_c","flower_white","flower_gold","flower_pink")}
plant_faces = {k:[] for k in plant_vertices}


def tri(key, points):
    v = plant_vertices[key]
    n = len(v)
    v.extend(points)
    plant_faces[key].append((n,n+1,n+2))


for i in range(520):
    y = rng.uniform(-5.9,5.9)
    left,right = bounds(y)
    side = rng.choice((-1,1))
    edge = left if side<0 else right
    gap = rng.betavariate(1.35,2.2)*2.05 + .025
    x = edge+side*gap
    if abs(x)>3.75: continue
    z = road_height(x,y)+.02
    key = ["grass_a","grass_b","grass_c"][i%3]
    count = 3 + i%5
    for b in range(count):
        angle = 2*math.pi*b/count+rng.uniform(-.22,.22)
        length = rng.uniform(.07,.24) * (.7 if gap<.2 else 1)
        width = rng.uniform(.027,.047)
        u,v = math.cos(angle),math.sin(angle)
        tri(key,[(x-v*width,y+u*width,z),(x+v*width,y-u*width,z),
                 (x+u*length*.3,y+v*length*.3,z+length)])
    if i%9 == 0:
        flower = ["flower_white","flower_gold","flower_pink"][i%3]
        h = rng.uniform(.12,.22)
        for petal in range(4):
            theta = petal*math.pi/2
            u,v = math.cos(theta),math.sin(theta)
            tri(flower,[(x,y,z+h),(x+.026*u-.012*v,y+.026*v+.012*u,z+h+.01),
                        (x+.026*u+.012*v,y+.026*v-.012*u,z+h+.01)])
for key, verts in plant_vertices.items():
    if verts:
        mesh(ROAD, "SM_QX12_"+key, verts, plant_faces[key], key)
for i in range(45):
    y = rng.uniform(-5.7,5.7)
    left,right = bounds(y)
    x = (left-rng.uniform(.18,1.4)) if i%2 else (right+rng.uniform(.18,1.4))
    if abs(x)>3.7: continue
    radius=rng.uniform(.065,.16)
    ico(ROAD,f"SM_QX12_LowLeafMound_{i:03}",(x,y,road_height(x,y)+.045),
        (radius,radius*.68,.07),("grass_a","grass_b","grass_c")[i%3],1,i+743)

# Modular bridge guardrail: 2.4 m span; no whole bridge, so it can be reused.
for x in (-1.1, 0, 1.1):
    box(RAIL, f"SM_QX12_RailPost_{x}", (x,0,.61), (.13,.13,.9), "wood", .018)
    box(RAIL, f"SM_QX12_RailStoneFoot_{x}", (x,0,.08), (.24,.23,.16), "stone", .012)
for z in (.44,.88):
    cylinder_between(RAIL, f"SM_QX12_RailBeam_{z}", (-1.2,0,z), (1.2,0,z), .047, "wood_light", 8)
for x in (-.55,.55):
    cylinder_between(RAIL, f"SM_QX12_RailBrace_{x}", (x-.25,0,.41), (x+.25,0,.86), .027, "wood", 6)

# Herb rack, 1.3 m wide: floor tray and suspended bundles, all parts grounded.
for x in (-.57,.57):
    for y in (-.2,.2):
        cylinder_between(RACK, f"SM_QX12_RackLeg_{x}_{y}", (x,y,0), (x,y,1.55), .042, "bamboo", 8)
for z in (.58,1.5):
    for y in (-.2,.2):
        cylinder_between(RACK, f"SM_QX12_RackCross_{z}_{y}", (-.63,y,z), (.63,y,z), .032, "wood_light", 8)
box(RACK,"SM_QX12_RackWovenTray",(0,0,.62),(1.23,.48,.035),"rope",.012)
for k in range(7):
    x = -.48+k*.16
    cylinder_between(RACK, f"SM_QX12_HerbTie_{k}", (x,0,1.46), (x,0,1.08), .009, "rope", 5)
    for blade in range(5):
        a = blade*2*math.pi/5
        cylinder_between(RACK,f"SM_QX12_Herb_{k}_{blade}",(x+.018*math.cos(a),.018*math.sin(a),1.15),
                         (x+.055*math.cos(a),.045*math.sin(a),.89),.013,"herb",5)

# Moss-stained waymarker with recessed-looking plaque and simple geometric
# cloud carving. No baked text makes it usable for multiple locations.
box(MARKER,"SM_QX12_MarkerBase",(0,0,.105),(.72,.43,.21),"stone_dark",.034)
body = box(MARKER,"SM_QX12_MarkerBody",(0,0,.56),(.47,.3,.79),"stone",.07)
box(MARKER,"SM_QX12_MarkerPlaque",(0,-.158,.58),(.32,.025,.24),"stone_dark",.003)
for i in range(3):
    ico(MARKER,f"SM_QX12_MarkerMoss_{i}",(-.19+i*.17,-.09,.956-i*.055),
        (.085,.07,.035),"moss",1,20+i)

# Export-ready transforms and basic per-face UVs for the independently
# placeable props. The large textured road meshes already have world UVs.
for group in (ROAD, RAIL, RACK, MARKER):
    for ob in group.objects:
        if ob.type != "MESH": continue
        if any(abs(s-1)>1e-5 for s in ob.scale):
            bpy.ops.object.select_all(action="DESELECT")
            ob.select_set(True)
            bpy.context.view_layer.objects.active=ob
            bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        if not ob.data.uv_layers:
            uv=ob.data.uv_layers.new(name="UVMap")
            for polygon in ob.data.polygons:
                n=polygon.normal
                axes=(1,2) if abs(n.x)>max(abs(n.y),abs(n.z)) else ((0,2) if abs(n.y)>abs(n.z) else (0,1))
                for loop_index in polygon.loop_indices:
                    v=ob.data.vertices[ob.data.loops[loop_index].vertex_index].co
                    uv.data[loop_index].uv=(v[axes[0]]+.5,v[axes[1]]+.5)


def select_collection(target):
    bpy.ops.object.select_all(action="DESELECT")
    objects = [o for o in target.objects if o.type=="MESH"]
    for ob in objects: ob.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    return objects


reports = {}
for key, group in (("road",ROAD),("bridge-rail",RAIL),("herb-rack",RACK),("waymarker",MARKER)):
    objects = select_collection(group)
    tris = sum(len(face.vertices)-2 for ob in objects for face in ob.data.polygons)
    reports[key] = {"reference":str(REFS["road" if key=="road" else {"bridge-rail":"rail","herb-rack":"rack","waymarker":"marker"}[key]].relative_to(ROOT)),
                    "mesh_count":len(objects),"triangles":tris}
    bpy.ops.export_scene.gltf(filepath=str(EXP/f"qingxi-{key}-v12.glb"),
        export_format="GLB",use_selection=True,export_apply=True)

scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1600
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "AgX"
world = bpy.data.worlds.new("Qingxi daylight")
world.use_nodes = True
world.node_tree.nodes.get("Background").inputs["Color"].default_value = (.73,.79,.83,1)
scene.world = world
sun_data = bpy.data.lights.new("Warm sun","SUN")
sun_data.energy = 1.35
sun = bpy.data.objects.new("Warm sun",sun_data)
scene.collection.objects.link(sun)
sun.rotation_euler = Vector((-.7,.5,-1)).to_track_quat("-Z","Y").to_euler()
camera_data = bpy.data.cameras.new("Art QA camera")
camera = bpy.data.objects.new("Art QA camera",camera_data)
scene.collection.objects.link(camera)
scene.camera = camera


def preview(key, group, location, target, lens, top=False):
    for g in (ROAD,RAIL,RACK,MARKER):
        for ob in g.objects: ob.hide_render = (g != group)
    camera.location = location
    camera.rotation_euler = (Vector(target)-camera.location).to_track_quat("-Z","Y").to_euler()
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = lens
    scene.render.filepath = str(PRE/f"{key}.png")
    bpy.ops.render.render(write_still=True)


preview("road-oblique",ROAD,(10,-13,10),(0,0,.1),14)
preview("road-top",ROAD,(0,0,18),(0,0,0),14)
preview("bridge-rail",RAIL,(3,-5,2.5),(0,0,.5),3.4)
preview("herb-rack",RACK,(2.5,-3.4,2.2),(0,0,.8),2.8)
preview("waymarker",MARKER,(1.8,-2.8,1.7),(0,0,.52),1.7)
for g in (ROAD,RAIL,RACK,MARKER):
    for ob in g.objects: ob.hide_render = False
bpy.ops.wm.save_as_mainfile(filepath=str(SRC/"qingxi-road-props-v12.blend"))
(EXP/"build-report.json").write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding="utf8")
print("@@QINGXI_V12@@"+json.dumps(reports,ensure_ascii=False))
