"""Build the two Qingxi landmarks after their AI three-view references were saved.

Run: blender -b --factory-startup --python-exit-code 1 -P tools/art/build_qingxi_landmarks.py
Coordinates are metres; bridge length is X, walkway width is Y, up is Z.
"""
import json
import math
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "art" / "exports" / "qingxi-world-v1"
SOURCE = ROOT / "art" / "source"
UNITY = ROOT / "apps" / "game" / "Assets" / "YunJing" / "Models" / "QingxiWorldV1"
for directory in (OUT, SOURCE, UNITY):
    directory.mkdir(parents=True, exist_ok=True)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.context.scene.unit_settings.system = "METRIC"
bpy.context.scene.unit_settings.scale_length = 1.0

def mat(name, color, roughness=0.9):
    m = bpy.data.materials.new("M_" + name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = roughness
    return m

wood = mat("AgedTimber", (0.18, 0.23, 0.21))
trim = mat("TimberEdge", (0.33, 0.28, 0.19))
stone = mat("PaleBridgeStone", (0.54, 0.53, 0.43))
bark = mat("SacredBark", (0.27, 0.24, 0.17))
leaves = [mat("Canopy" + str(i), c) for i,c in enumerate(((0.31,0.43,0.26),(0.40,0.51,0.30),(0.25,0.38,0.27)))]
ribbon = mat("CeremonyRibbon", (0.51, 0.28, 0.19))

def collection(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c

def move_to_collection(obj, c):
    for old in list(obj.users_collection): old.objects.unlink(obj)
    c.objects.link(obj)
    return obj

def cube(c, name, center, size, material):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    o = move_to_collection(bpy.context.object, c)
    o.name = "SM_" + name
    o.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    return o

def tapered(c, name, a, b, r0, r1, material, vertices=8):
    direction = Vector(b)-Vector(a)
    mid = (Vector(a)+Vector(b))*0.5
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=r0, radius2=r1,
        depth=direction.length, location=mid)
    o = move_to_collection(bpy.context.object, c)
    o.name = "SM_"+name
    o.rotation_euler = direction.to_track_quat('Z','Y').to_euler()
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    o.data.materials.append(material)
    bm=bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    bm.to_mesh(o.data); bm.free()
    return o

def canopy(c, name, xyz, radius, material):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1, location=xyz)
    o = move_to_collection(bpy.context.object,c)
    o.name = "SM_"+name
    o.scale = (radius[0],radius[1],radius[2])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    return o

bridge = collection("ASSET_TimberBridge_low")
def deck_height(x): return 1.15 + 0.50 * (1.0 - (x/5.5)**2)

# 26 individually replaceable deck planks; small gaps are deliberate.
for i in range(26):
    x = -5.25 + i*0.42
    cube(bridge, f"BridgeDeck_{i:02d}", (x,0,deck_height(x)), (.39,3.5,.16), trim if i%5==0 else wood)
# Continuous-looking structural stringers touch each deck plank and one another.
for side in (-1,1):
    for i in range(26):
        x=-5.25+i*.42
        cube(bridge,f"Stringer_{side}_{i:02d}",(x,side*1.18,deck_height(x)-.18),(.47,.24,.25),wood)
for side in (-1,1):
    y = side*1.77
    for i in range(9):
        x = -5.2+i*1.3
        h = deck_height(x)
        cube(bridge, f"Post_{side}_{i}", (x,y,h+.56), (.17,.18,1.20),wood)
        cube(bridge, f"PostCap_{side}_{i}", (x,y,h+1.19), (.26,.27,.12),trim)
    for i in range(8):
        x = -5.2+i*1.3
        x2=x+1.3
        a=Vector((x,y,deck_height(x)+1.06))
        b=Vector((x2,y,deck_height(x2)+1.06))
        o=cube(bridge,f"Rail_{side}_{i}",(a+b)*.5,(1.33,.13,.15),wood)
        o.rotation_euler[1] = -math.atan2(b.z-a.z,1.3)
        bpy.context.view_layer.objects.active=o
        bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
for side in (-1,1):
    cube(bridge,f"Abutment_{side}",(side*5.63,0,.38),(.85,4.15,.76),stone)
    cube(bridge,f"AbutmentLip_{side}",(side*5.63,0,.79),(.96,4.25,.12),stone)

tree = collection("ASSET_SacredTree_low")
tapered(tree,"TrunkLower",(0,0,0),(0.05,0.05,4.0),.82,.58,bark,12)
tapered(tree,"TrunkUpper",(.05,.05,3.75),(.10,.15,8.0),.62,.27,bark,10)
for i in range(7):
    a=2*math.pi*i/7
    tapered(tree,f"Root_{i}",(0,0,.85),(math.cos(a)*1.9,math.sin(a)*1.65,.15),.36,.08,bark,6)
branch_ends=[]
for i in range(8):
    a=2*math.pi*i/8
    x,y=math.cos(a),math.sin(a)
    start=(.08,.10,5.3+(i%3)*.7)
    end=(x*(3.5+(i%2)),y*(3.0+((i+1)%2)),9.0+(i%3)*.7)
    tapered(tree,f"Branch_{i}",start,end,.31,.10,bark,7)
    branch_ends.append(end)
    canopy(tree,f"LeafCluster_{i}",(end[0]*1.05,end[1]*1.05,end[2]+.2),
        (2.5,2.25,1.65),leaves[i%3])
canopy(tree,"LeafCrown",(0,0,11.0),(3.65,3.5,2.7),leaves[1])
canopy(tree,"LeafCrownTop",(.2,-.1,12.55),(2.7,2.55,1.35),leaves[0])
for i in (1,4,6):
    x,y,z=branch_ends[i]
    cube(tree,f"Ribbon_{i}",(x,y,z-1.1),(.08,.055,1.8),ribbon)

def only(c):
    bpy.ops.object.select_all(action="DESELECT")
    for o in c.objects: o.select_set(True)
    bpy.context.view_layer.objects.active=next(iter(c.objects))

def export_asset(c, stem):
    for col in (bridge,tree):
        for o in col.objects: o.hide_render = col != c
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/(stem+".blend")))
    # Keep the editable source modular; merge same-material copies for the game export.
    export_collection=collection("EXPORT_"+stem)
    groups={}
    for original in list(c.objects):
        clone=original.copy(); clone.data=original.data.copy()
        export_collection.objects.link(clone)
        key=original.data.materials[0].name
        groups.setdefault(key,[]).append(clone)
    joined=[]
    for key,parts in groups.items():
        bpy.ops.object.select_all(action="DESELECT")
        for part in parts: part.select_set(True)
        bpy.context.view_layer.objects.active=parts[0]
        bpy.ops.object.join()
        result=bpy.context.view_layer.objects.active
        result.name="SM_"+stem.replace('-','_')+"_"+key
        joined.append(result)
    bpy.ops.object.select_all(action="DESELECT")
    for item in joined: item.select_set(True)
    bpy.context.view_layer.objects.active=joined[0]
    fbx = OUT/(stem+".fbx")
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},
        apply_unit_scale=True,axis_forward='-Z',axis_up='Y',add_leaf_bones=False,
        use_mesh_modifiers=True,mesh_smooth_type='FACE')
    glb=OUT/(stem+".glb")
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,
        export_apply=True,export_materials='EXPORT')
    (UNITY/(stem+".fbx")).write_bytes(fbx.read_bytes())
    tris=sum(len(p.vertices)-2 for o in c.objects if o.type=='MESH' for p in o.data.polygons)
    for item in joined: bpy.data.objects.remove(item,do_unlink=True)
    bpy.data.collections.remove(export_collection)
    return {"name":stem,"objects":len(c.objects),"triangles":tris,
            "export_meshes":len(groups),
            "fbx_bytes":fbx.stat().st_size,"glb_bytes":glb.stat().st_size}

report=[export_asset(bridge,"qingxi-timber-bridge-v1"),export_asset(tree,"qingxi-sacred-tree-v1")]
(OUT/"build-report.json").write_text(json.dumps(report,indent=2),encoding='utf-8')
print("@@JSON@@"+json.dumps(report))
