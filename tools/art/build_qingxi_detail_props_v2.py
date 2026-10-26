"""Build four original modular props after saving their AI three-view sheet."""
import json
import math
import random
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / 'art/references/qingxi-detail-props-v2/three-view.png'
if not REFERENCE.is_file():
    raise FileNotFoundError(REFERENCE)
OUT = ROOT / 'art/exports/qingxi-detail-props-v2'
PREVIEW = ROOT / 'art/previews/qingxi-detail-props-v2'
OUT.mkdir(parents=True, exist_ok=True)
PREVIEW.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1


def material(name, color, roughness=.88, emission=0):
    mat = bpy.data.materials.new('M_QXDetail_' + name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = roughness
    if emission:
        bsdf.inputs['Emission Color'].default_value = (*color, 1)
        bsdf.inputs['Emission Strength'].default_value = emission
    return mat


M = {
    'reed': material('ReedLeaf', (.18, .28, .09)),
    'reed_light': material('ReedLeafSun', (.33, .44, .14)),
    'head': material('ReedSeed', (.53, .40, .21)),
    'fern': material('Fern', (.12, .28, .12)),
    'fern_light': material('FernLight', (.28, .44, .20)),
    'stem': material('FlowerStem', (.22, .34, .10)),
    'cream': material('CreamFlower', (.88, .84, .60)),
    'yellow': material('YellowFlower', (.90, .65, .17)),
    'stone': material('WarmLimestone', (.48, .47, .41)),
    'stone_light': material('LimestoneLight', (.63, .60, .51)),
    'stone_dark': material('LimestoneCrevice', (.29, .30, .26)),
    'moss': material('Moss', (.26, .36, .11)),
    'wood': material('AgedWood', (.24, .15, .09)),
    'wood_light': material('WoodEdge', (.37, .23, .13)),
    'paper': material('LanternPaper', (.97, .70, .38), emission=.45),
    'soil': material('RootSoil', (.31, .28, .19)),
}
stone_image = bpy.data.images.load(str(ROOT/'art/textures/qingxi-riverbank-v2/stone-albedo.png'),check_existing=True)
stone_image.pack()
for stone_key in ('stone','stone_light','stone_dark'):
    mat=M[stone_key]
    bsdf=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    image_node=mat.node_tree.nodes.new('ShaderNodeTexImage')
    image_node.image=stone_image
    image_node.extension='REPEAT'
    mat.node_tree.links.new(image_node.outputs['Color'],bsdf.inputs['Base Color'])


def collection(name):
    col = bpy.data.collections.new('ASSET_QX_' + name)
    scene.collection.children.link(col)
    return col


def mesh(col, name, verts, faces, mat):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    ob = bpy.data.objects.new('SM_QX_' + name, data)
    col.objects.link(ob)
    data.materials.append(M[mat])
    return ob


def block(col, name, location, size, mat, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    ob = bpy.context.object
    ob.name = 'SM_QX_' + name
    ob.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for old in list(ob.users_collection):
        old.objects.unlink(ob)
    col.objects.link(ob)
    ob.data.materials.append(M[mat])
    if bevel:
        mod = ob.modifiers.new('softened cut edge', 'BEVEL')
        mod.width = bevel
        mod.segments = 1
        ob.modifiers.new('weighted normals', 'WEIGHTED_NORMAL')
    return ob


def curved_blade(col, name, base, angle, height, width, bend, mat):
    dx, dy = math.cos(angle), math.sin(angle)
    sx, sy = -dy, dx
    verts = []
    for t, w in ((0, .65), (.28, 1), (.67, .72), (1, .03)):
        x = base[0] + bend * t * t * dx
        y = base[1] + bend * t * t * dy
        z = base[2] + height * t
        verts.extend([(x + sx*width*w/2, y + sy*width*w/2, z),
                      (x - sx*width*w/2, y - sy*width*w/2, z)])
    return mesh(col, name, verts,
                [(0, 1, 3, 2), (2, 3, 5, 4), (4, 5, 7, 6)], mat)


def stem(col, name, start, end, radius, mat, vertices=6):
    direction = Vector(end) - Vector(start)
    mid = (Vector(start) + Vector(end)) / 2
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius,
                                        depth=direction.length, location=mid)
    ob = bpy.context.object
    ob.rotation_euler = direction.to_track_quat('Z', 'Y').to_euler()
    ob.name = 'SM_QX_' + name
    for old in list(ob.users_collection): old.objects.unlink(ob)
    col.objects.link(ob)
    ob.data.materials.append(M[mat])
    return ob


def root_pad(col, name, radius):
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=radius, depth=.04,
                                        location=(0,0,0))
    ob=bpy.context.object
    ob.name='SM_QX_'+name
    for old in list(ob.users_collection):old.objects.unlink(ob)
    col.objects.link(ob)
    ob.data.materials.append(M['soil'])
    return ob


def flower(col, name, pos, mat):
    x, y, z = pos
    verts = [(x, y, z + .008)]
    faces = []
    for i in range(5):
        a = math.tau * i / 5
        start = len(verts)
        verts.extend([(x + .005*math.cos(a-.42), y + .005*math.sin(a-.42), z-.004),
                      (x + .048*math.cos(a), y + .048*math.sin(a), z+.012),
                      (x + .005*math.cos(a+.42), y + .005*math.sin(a+.42), z-.004)])
        faces.append((0, start, start+1, start+2))
    mesh(col, name, verts, faces, mat)


rng = random.Random(20261026)
reed = collection('RiverReed_v2')
root_pad(reed,'ReedRootSoil',.68)
for i in range(46):
    x, y = rng.uniform(-.40, .40), rng.uniform(-.29, .29)
    a = rng.uniform(0, math.tau)
    curved_blade(reed, f'ReedBlade_{i:02}', (x, y, 0), a,
                 rng.uniform(.38, 1.15), rng.uniform(.018, .047),
                 rng.uniform(.18, .55), 'reed_light' if i % 5 == 0 else 'reed')
for i in range(5):
    x, y = rng.uniform(-.22, .22), rng.uniform(-.2, .2)
    tip = (x+rng.uniform(-.12,.12), y+rng.uniform(-.12,.12), rng.uniform(.98, 1.35))
    stem(reed, f'ReedHeadStem_{i}', (x,y,0), tip, .008, 'reed')
    stem(reed, f'ReedSeedHead_{i}', tip, (tip[0],tip[1],tip[2]+.17), .025, 'head', 8)

fern = collection('FernFlower_v2')
root_pad(fern,'FernRootSoil',.60)
for i in range(12):
    a = math.tau*i/12+rng.uniform(-.2,.2)
    length = rng.uniform(.27,.58)
    x,y = .08*math.cos(a), .08*math.sin(a)
    mid_height=rng.uniform(.23,.52)
    curved_blade(fern, f'FernMidrib_{i}', (x,y,0), a,
                 mid_height, .025, length,
                 'fern_light' if i%3==0 else 'fern')
    for j in range(5):
        t = .25+j*.14
        sx = x+math.cos(a)*length*t*t
        sy = y+math.sin(a)*length*t*t
        z = mid_height*t
        for side in (-1,1):
            curved_blade(fern, f'FernPinna_{i}_{j}_{side}', (sx,sy,z),
                         a+side*.95, .07*(1-t/1.4), .028,
                         .13*(1-t/1.5), 'fern_light' if i%3==0 else 'fern')
for i in range(23):
    a = rng.uniform(0, math.tau)
    r = rng.uniform(.1,.47)
    x,y = math.cos(a)*r,math.sin(a)*r
    h = rng.uniform(.18,.48)
    stem(fern, f'FlowerStalk_{i}', (x,y,0), (x,y,h), .005, 'stem', 5)
    flower(fern, f'Wildflower_{i}', (x,y,h), 'cream' if i%3 else 'yellow')


def rough_rock(col, name, center, radius, height, mat, seed):
    rr = random.Random(seed)
    rings = []
    count = 11
    for z, spread in ((0,.70), (.13,.98), (.75,1), (1,.65)):
        rings.append([(center[0] + radius*spread*(1+rr.uniform(-.16,.16))*math.cos(math.tau*i/count),
                       center[1] + radius*spread*(1+rr.uniform(-.16,.16))*math.sin(math.tau*i/count),
                       center[2] + height*z+rr.uniform(-.035,.035)) for i in range(count)])
    verts=[p for ring in rings for p in ring]
    faces=[]
    for j in range(3):
        for i in range(count):
            n=(i+1)%count
            faces.append((j*count+i,j*count+n,(j+1)*count+n,(j+1)*count+i))
    faces.append(tuple(range(3*count,4*count)))
    ob=mesh(col,name,verts,faces,mat)
    uv=ob.data.uv_layers.new(name='UVMap')
    for polygon in ob.data.polygons:
        for loop_index in polygon.loop_indices:
            p=ob.data.vertices[ob.data.loops[loop_index].vertex_index].co
            uv.data[loop_index].uv=(p.x*1.7+p.z*.3,p.y*1.7+p.z*.5)
    return ob


rock = collection('MossBoulder_v2')
main_rock=rough_rock(rock, 'LayeredMainBoulder', (0,0,0), .72, .58, 'stone', 11)
for i,(x,y,r,h) in enumerate(((-.6,-.22,.27,.24),(.60,.14,.36,.31),(.10,.45,.30,.17))):
    rough_rock(rock, f'RockShoulder_{i}', (x,y,0), r,h,
               'stone_light' if i%2 else 'stone_dark', 90+i)
for i in range(18):
    a = rng.uniform(0, math.tau)
    r = rng.uniform(.08,.56)
    x,y = r*math.cos(a),r*math.sin(a)
    hit,point,normal,face_index=main_rock.ray_cast(Vector((x,y,2)),Vector((0,0,-1)))
    if not hit:continue
    curved_blade(rock, f'MossBlade_{i}', (x,y,point.z-.025), a,
                 rng.uniform(.10,.15), .035, .04, 'moss')

lantern = collection('TrailLantern_v2')
block(lantern,'LanternStonePlinth',(0,0,.16),(.58,.58,.32),'stone',.025)
block(lantern,'LanternStoneCap',(0,0,.34),(.64,.64,.05),'stone_light',.014)
block(lantern,'LanternPost',(0,0,1.03),(.13,.13,1.35),'wood',.018)
block(lantern,'LanternCrossbeam',(0,0,1.76),(1.07,.15,.13),'wood',.02)
for side in (-1,1):
    stem(lantern,f'CurvedRoofRafter_{side}',(0,side*.08,1.76),
         (side*.57,side*.08,1.86),.045,'wood',8)
    block(lantern,f'RoofTip_{side}',(side*.54,0,1.88),(.10,.2,.12),'wood_light',.02)
block(lantern,'PaperLantern',(0,-.19,1.38),(.27,.26,.41),'paper',.09)
block(lantern,'LanternTopBand',(0,-.19,1.60),(.30,.29,.045),'wood',.005)
block(lantern,'LanternBottomBand',(0,-.19,1.16),(.30,.29,.045),'wood',.005)
stem(lantern,'LanternTassel',(0,-.19,1.17),(0,-.19,.94),.01,'wood',5)

# Give every procedural piece exportable UVs and triangle-only caps. The
# solid-color props deliberately share UV space; these are not bake atlases.
for asset_col in (reed,fern,rock,lantern):
    for asset_ob in asset_col.objects:
        if asset_ob.type!='MESH':continue
        mesh=asset_ob.data
        if any(len(poly.vertices)>4 for poly in mesh.polygons):
            editable=bmesh.new()
            editable.from_mesh(mesh)
            bmesh.ops.triangulate(editable,faces=[f for f in editable.faces if len(f.verts)>4])
            editable.to_mesh(mesh)
            editable.free()
        if not mesh.uv_layers:
            uv=mesh.uv_layers.new(name='UVMap')
            columns=math.ceil(math.sqrt(len(mesh.polygons)))
            cell=1.0/columns
            for face_index,poly in enumerate(mesh.polygons):
                points=[mesh.vertices[mesh.loops[i].vertex_index].co for i in poly.loop_indices]
                origin=points[0]
                edge=(points[1]-origin).normalized()
                across=poly.normal.cross(edge).normalized()
                coordinates=[((p-origin).dot(edge),(p-origin).dot(across)) for p in points]
                low_u=min(pair[0] for pair in coordinates)
                low_v=min(pair[1] for pair in coordinates)
                len_u=max(max(pair[0] for pair in coordinates)-low_u,1e-6)
                len_v=max(max(pair[1] for pair in coordinates)-low_v,1e-6)
                cell_x=face_index%columns
                cell_y=face_index//columns
                for loop_index in poly.loop_indices:
                    co=mesh.vertices[mesh.loops[loop_index].vertex_index].co
                    local_u=(co-origin).dot(edge)
                    local_v=(co-origin).dot(across)
                    uv.data[loop_index].uv=(cell*(cell_x+.1+.8*(local_u-low_u)/len_u),
                                            cell*(cell_y+.1+.8*(local_v-low_v)/len_v))

world = bpy.data.worlds.new('Qingxi daylight')
scene.world=world
world.use_nodes=True
world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.64,.76,.85,1)
world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.8
light=bpy.data.lights.new('soft sun','SUN')
light.energy=1.8
sun=bpy.data.objects.new('soft sun',light)
scene.collection.objects.link(sun)
sun.rotation_euler=(.32,-.5,-.6)

report={'reference':'art/references/qingxi-detail-props-v2/three-view.png',
        'owner':'z1nnz / Codex-assisted original modeling',
        'status':'Blender source and GLB preview; Unity import and mobile performance unverified',
        'assets':{}}
for key,col in [('river-reed',reed),('fern-flower',fern),('moss-boulder',rock),('trail-lantern',lantern)]:
    objects=[o for o in col.objects if o.type=='MESH']
    report['assets'][key]={'source_meshes':len(objects),
                           'triangles':sum(len(p.vertices)-2 for o in objects for p in o.data.polygons)}

bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/source/qingxi-detail-props-v2.blend'))
for key,col in [('river-reed',reed),('fern-flower',fern),('moss-boulder',rock),('trail-lantern',lantern)]:
    for other in (reed,fern,rock,lantern):
        for ob in other.objects: ob.hide_render = other != col
    bpy.ops.object.select_all(action='DESELECT')
    selected=list(col.objects)
    for ob in selected: ob.select_set(True)
    bpy.context.view_layer.objects.active=selected[0]
    bpy.ops.export_scene.gltf(filepath=str(OUT/f'qingxi-{key}-v2.glb'),
                              export_format='GLB',use_selection=True,export_apply=True)
    camdata=bpy.data.cameras.new('preview camera')
    camera=bpy.data.objects.new('preview camera',camdata)
    scene.collection.objects.link(camera)
    camera.location=(2.8,-3.7,2.55) if key!='trail-lantern' else (3,-4,3)
    target=Vector((0,0,.45 if key!='trail-lantern' else 1.05))
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    camdata.type='ORTHO';camdata.ortho_scale=3.0 if key!='trail-lantern' else 3.3
    scene.camera=camera
    scene.render.engine='BLENDER_EEVEE'
    scene.render.resolution_x=900;scene.render.resolution_y=900
    scene.render.resolution_percentage=100
    scene.view_settings.view_transform='AgX'
    scene.render.image_settings.file_format='PNG'
    scene.render.filepath=str(PREVIEW/f'{key}-preview.png')
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera,do_unlink=True)

(OUT/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('@@QX_DETAIL@@'+json.dumps(report,ensure_ascii=False))
