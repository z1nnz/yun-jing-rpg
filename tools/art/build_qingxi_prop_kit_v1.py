"""Build three reusable Qingxi props from the saved AI orthographic reference.

Run with Blender 5.2: blender -b -P tools/art/build_qingxi_prop_kit_v1.py
The source keeps individual parts; each GLB is an independent placeable prop.
"""
import json
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / 'art/references/qingxi-prop-kit-v1/three-view.png'
if not REFERENCE.is_file():
    raise FileNotFoundError('Inspect and save the AI three-view before modeling')
SOURCE = ROOT / 'art/source/qingxi-prop-kit-v1.blend'
OUT = ROOT / 'art/exports/qingxi-prop-kit-v1'
PREVIEW = ROOT / 'art/previews/qingxi-prop-kit-v1'
OUT.mkdir(parents=True, exist_ok=True)
PREVIEW.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
rng = random.Random(251025)


def material(name, color, roughness=0.9):
    mat = bpy.data.materials.new('M_QX_' + name)
    mat.diffuse_color = (*color, 1)
    pbr = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    pbr.inputs['Base Color'].default_value = (*color, 1)
    pbr.inputs['Roughness'].default_value = roughness
    return mat


def add_albedo(mat, path):
    image=bpy.data.images.load(str(path),check_existing=True)
    image.pack()
    tex=mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image=image
    pbr=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    mat.node_tree.links.new(tex.outputs['Color'],pbr.inputs['Base Color'])


mats = {
    'leaf': material('LeafGreen', (.21, .35, .12)),
    'leaf_light': material('LeafLight', (.35, .49, .18)),
    'stem': material('Stem', (.20, .31, .11)),
    'petal': material('PetalCream', (.86, .82, .56)),
    'petal_yellow': material('PetalYellow', (.91, .67, .16)),
    'stone': material('RiverStone', (.42, .43, .37)),
    'moss': material('StoneMoss', (.23, .32, .13)),
    'soil': material('Soil', (.28, .23, .16)),
}
add_albedo(mats['stone'],ROOT/'art/textures/qingxi-riverbank-v2/stone-albedo.png')
add_albedo(mats['soil'],ROOT/'art/textures/qingxi-riverbank-v2/path-albedo.png')
collections = {}
for key in ('grass', 'wildflower', 'cobble'):
    col = bpy.data.collections.new('ASSET_QX_' + key)
    scene.collection.children.link(col)
    collections[key] = col


def mesh(key, name, verts, faces, mat):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    ob = bpy.data.objects.new('SM_QX_' + key + '_' + name, data)
    collections[key].objects.link(ob)
    data.materials.append(mats[mat])
    uv = data.uv_layers.new(name='UVMap')
    for poly in data.polygons:
        axis=max(range(3),key=lambda i:abs(poly.normal[i]))
        for loop in poly.loop_indices:
            p = data.vertices[data.loops[loop].vertex_index].co
            coords=((p.y,p.z),(p.x,p.z),(p.x,p.y))[axis]
            uv.data[loop].uv = (coords[0] * 1.4 + .5, coords[1] * 1.4 + .5)
    return ob


def flat_seed(key, width, length, height):
    return mesh(key, 'root_soil', [(-width,-length,0),(width,-length,0),
        (width,length,0),(-width,length,0),(0,0,height)],
        [(0,1,4),(1,2,4),(2,3,4),(3,0,4)], 'soil')


flat_seed('grass', .18, .16, .025)
verts, faces = [], []
for index in range(26):
    angle = index * 2.39996 + rng.uniform(-.18, .18)
    radius = .025 + .14 * math.sqrt((index+.3)/26)
    x, y = radius*math.cos(angle), radius*math.sin(angle)
    height = rng.uniform(.18,.42) * (1-.22*radius/.17)
    side = Vector((-math.sin(angle), math.cos(angle), 0))
    bend = rng.uniform(.02,.13)
    width = rng.uniform(.009,.021)
    base = len(verts)
    verts += [(x-side.x*width,y-side.y*width,.015),
              (x+side.x*width,y+side.y*width,.015),
              (x+math.cos(angle)*bend-side.x*width*.55,
               y+math.sin(angle)*bend-side.y*width*.55,height*.66),
              (x+math.cos(angle)*bend+side.x*width*.55,
               y+math.sin(angle)*bend+side.y*width*.55,height*.66),
              (x+math.cos(angle)*bend*1.65,y+math.sin(angle)*bend*1.65,height)]
    faces += [(base,base+1,base+3,base+2),(base+2,base+3,base+4)]
mesh('grass','blades',verts,faces,'leaf')

flat_seed('wildflower', .20, .18, .025)
verts, faces = [], []
leaves, leaf_faces=[],[]
petals, petal_faces = [], []
for index in range(12):
    angle = index * 2.39996
    radius = .035 + .13*math.sqrt((index+.3)/12)
    x, y = radius*math.cos(angle),radius*math.sin(angle)
    h = rng.uniform(.13,.36)
    head = (x + .035*math.cos(angle),y+.035*math.sin(angle),h)
    base = len(verts)
    verts += [(x-.012,y,.015),(x+.012,y,.015),
              (head[0]+.008,head[1],h*.87),head]
    faces += [(base,base+1,base+2),(base,base+2,base+3)]
    for side in (-1,1):
        b=len(leaves)
        stem_z=h*(.34 if side<0 else .55)
        dx=.045*side
        leaves += [(x,y,stem_z),(x+dx,y-.018,stem_z+.015),
                   (x+dx*1.4,y+.015,stem_z+.03)]
        leaf_faces.append((b,b+1,b+2))
    for k in range(5):
        a = 2*math.pi*k/5
        b = len(petals)
        petals += [head,(head[0]+.045*math.cos(a-.32),head[1]+.045*math.sin(a-.32),h+.006),
                    (head[0]+.055*math.cos(a+.32),head[1]+.055*math.sin(a+.32),h+.006)]
        petal_faces.append((b,b+1,b+2))
mesh('wildflower','leaves_and_stems',verts,faces,'stem')
mesh('wildflower','small_leaves',leaves,leaf_faces,'leaf_light')
mesh('wildflower','small_cream_petals',petals,petal_faces,'petal')

bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1)
rock = bpy.context.object
rock.name='SM_QX_cobble_weathered_rock'
for col in list(rock.users_collection):col.objects.unlink(rock)
collections['cobble'].objects.link(rock)
rock.scale=(.45,.33,.24)
for vertex in rock.data.vertices:
    noise = 1 + .09*math.sin(vertex.co.x*11+vertex.co.y*7) + .06*math.sin(vertex.co.z*17)
    vertex.co *= noise
    if vertex.co.z < -.48: vertex.co.z = -.48
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
rock.data.materials.append(mats['stone'])
uv=rock.data.uv_layers.new(name='UVMap')
for poly in rock.data.polygons:
    for li in poly.loop_indices:
        p=rock.data.vertices[rock.data.loops[li].vertex_index].co
        uv.data[li].uv=(p.x+.5,p.y+.5)
rock.location.z=.12

scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND')
bg.inputs['Color'].default_value=(.72,.78,.78,1)
bg.inputs['Strength'].default_value=.7
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
report={'reference':str(REFERENCE.relative_to(ROOT)),'source':str(SOURCE.relative_to(ROOT)),
        'assets':{},'status':'geometry preview; leaf alpha, LOD and Unity import not verified'}
for key,col in collections.items():
    objects=[ob for ob in col.objects if ob.type=='MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:ob.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    filepath=OUT/('qingxi-'+key+'-v1.glb')
    bpy.ops.export_scene.gltf(filepath=str(filepath),export_format='GLB',
        use_selection=True,export_apply=True)
    report['assets'][key]={'meshes':len(objects),
        'triangles':sum(len(poly.vertices)-2 for ob in objects for poly in ob.data.polygons),
        'file':str(filepath.relative_to(ROOT))}

# Render the three actual meshes together as a small contact sheet.
for key,col in collections.items():
    offset={'grass':(-1.25,0,0),'wildflower':(0,0,0),'cobble':(1.25,0,0)}[key]
    for ob in col.objects:ob.location+=Vector(offset)
sun_data=bpy.data.lights.new('Preview sunlight','SUN');sun_data.energy=2
sun=bpy.data.objects.new('Preview sunlight',sun_data);scene.collection.objects.link(sun)
sun.rotation_euler=(math.radians(25),math.radians(-25),math.radians(-35))
camera_data=bpy.data.cameras.new('Preview camera')
camera=bpy.data.objects.new('Preview camera',camera_data);scene.collection.objects.link(camera)
camera.location=(3,-5,3.1)
camera.rotation_euler=(Vector((0,0,.1))-camera.location).to_track_quat('-Z','Y').to_euler()
camera_data.type='ORTHO';camera_data.ortho_scale=4.5
scene.camera=camera
scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=1400;scene.render.resolution_y=800
scene.render.filepath=str(PREVIEW/'prop-kit-oblique-v1.png')
bpy.ops.render.render(write_still=True)
(OUT/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('@@PROP_KIT@@'+json.dumps(report,ensure_ascii=False))
