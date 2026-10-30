"""Meadow ground cover for the novice world, after the Mondstadt-style meadows z1nnz pointed to: knee-high lush grass
that ripples, sun-dried grass in patches, and little white, yellow and blue flowers scattered through it.

Each clump is a terrain detail (instanced, YunJing/QingxiGrass shader): blades are curved tapered strips with
vertex colours from a dark root to a bright tip, so the meadow reads as grass up close and as soft colour from
afar. Origins at the root; Y is the blade height the shader's wind and backlight use.

Output: art/exports/qingxi-ground-v1/*.fbx, review render art/previews/qingxi-ground-v1/kit.png
Run: blender -b --factory-startup -P tools/art/build_ground_kit_v1.py
"""
import math
import random
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'art/exports/qingxi-ground-v1'
PREVIEW = ROOT / 'art/previews/qingxi-ground-v1'


def lin(h):
    def c(x):
        return x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4
    return [c(int(h[i:i + 2], 16) / 255) for i in (1, 3, 5)]


def mix(a, b, t):
    return [a[k] + (b[k] - a[k]) * t for k in range(3)]


def blade(bm, col, rng, base, height, width, lean, yaw, colours, segs=4):
    """A curved, tapered blade: pairs of vertices up the blade, a point at the tip."""
    root, mid, tip = (lin(c) for c in colours)
    jitter = rng.uniform(-.06, .06)
    d = Vector((math.cos(yaw), math.sin(yaw), 0))
    side = Vector((-d.y, d.x, 0))
    rows = []
    for i in range(segs + 1):
        t = i / segs
        p = base + d * lean * height * t ** 1.8 + Vector((0, 0, height * t * (1 - .12 * t)))
        w = width * (1 - t) ** .8 if i < segs else 0
        tone = mix(root, mid, t / .6) if t < .6 else mix(mid, tip, (t - .6) / .4)
        tone = [min(max(x * (1 + jitter), 0), 1) for x in tone]
        if i < segs:
            rows.append(((bm.verts.new(p - side * w), bm.verts.new(p + side * w)), tone))
        else:
            rows.append(((bm.verts.new(p),), tone))
    for i in range(segs):
        (a, ta), (b, tb) = rows[i], rows[i + 1]
        verts = (a[0], a[1], b[0]) if len(b) == 1 else (a[0], a[1], b[1], b[0])
        f = bm.faces.new(verts)
        for loop in f.loops:
            loop[col] = (*(tb if loop.vert in b else ta), 1)


def flower(bm, col, rng, base, height, petal_hex, centre_hex, colours):
    """A thin stem and a small five-petal flower facing up and a little outward."""
    stem_yaw = rng.uniform(0, math.tau)
    blade(bm, col, rng, base, height, .006, .15, stem_yaw, colours, segs=3)
    top = base + Vector((math.cos(stem_yaw), math.sin(stem_yaw), 0)) * .15 * height + Vector((0, 0, height * .88))
    r = rng.uniform(.028, .04)
    petal = lin(petal_hex)
    centre = lin(centre_hex)
    for k in range(5):
        a = math.tau * k / 5 + rng.random() * .3
        dvec = Vector((math.cos(a), math.sin(a), .18))
        side = Vector((-math.sin(a), math.cos(a), 0)) * r * .45
        v = [bm.verts.new(top), bm.verts.new(top + dvec * r * .55 - side), bm.verts.new(top + dvec * r * 1.15), bm.verts.new(top + dvec * r * .55 + side)]
        f = bm.faces.new(v)
        for loop in f.loops:
            loop[col] = (*(centre if loop.vert is v[0] else petal), 1)


KITS = {
    # Lush meadow grass, knee high: the main cover.
    'GrassLush': dict(blades=34, height=(.16, .3), width=(.03, .045), lean=(.15, .45), spread=.22,
                      colours=('#2a4a22', '#4f7a34', '#a3b85e')),
    # Taller grass for meadow edges and slopes.
    'GrassTall': dict(blades=24, height=(.3, .48), width=(.03, .045), lean=(.2, .5), spread=.2,
                      colours=('#2e5026', '#5a8238', '#b0c06a')),
    # Sun-dried grass in patches.
    'GrassDry': dict(blades=28, height=(.14, .26), width=(.03, .042), lean=(.2, .5), spread=.22,
                     colours=('#5a5430', '#8e8644', '#c8bc78')),
    'FlowerWhite': dict(blades=8, height=(.12, .2), width=(.025, .035), lean=(.2, .4), spread=.16,
                        colours=('#2f5a24', '#5f9a3a', '#a8cc60'), flowers=(5, '#f6f6ee', '#e8c440')),
    'FlowerYellow': dict(blades=8, height=(.2, .34), width=(.025, .035), lean=(.2, .4), spread=.16,
                         colours=('#2f5a24', '#5f9a3a', '#a8cc60'), flowers=(5, '#f4d23c', '#c87a1e')),
    'FlowerBlue': dict(blades=8, height=(.2, .34), width=(.025, .035), lean=(.2, .4), spread=.16,
                       colours=('#2f5a24', '#5f9a3a', '#a8cc60'), flowers=(5, '#7cb4ec', '#f0f0e0')),
}


def stone(bm, col, rng, centre, size, colours):
    """A rounded, slightly flattened stone, sunk about a third into the ground: warm grey, moss on top."""
    dark, mid = lin(colours[0]), lin(colours[1])
    moss = lin(colours[2]) if colours[2] else mid
    res = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1)
    verts = res['verts']
    sx, sy, sz = size * rng.uniform(.8, 1.2), size * rng.uniform(.7, 1.0), size * rng.uniform(.6, .85)
    seed = rng.random() * 100
    for v in verts:
        n = v.co.normalized()
        bump = 1 + .14 * math.sin(n.x * 5 + seed) * math.cos(n.y * 4 + seed) + .06 * math.sin(n.z * 9 + seed * 2)
        v.co = centre + Vector((n.x * sx, n.y * sy, n.z * sz)) * bump - Vector((0, 0, sz * .3))
    for f in {f for v in verts for f in v.link_faces}:
        for loop in f.loops:
            n = (loop.vert.co - centre).normalized()
            t = min(max(n.z * 1.4 + rng.uniform(-.1, .1), 0), 1)
            c = mix(dark, mid, min(max(n.z + .6, 0), 1))
            if n.z > .55 and colours[2]:
                c = mix(c, moss, min((n.z - .55) * 2.5, .8))
            loop[col] = (*c, 1)


STONES = {
    # Pebbles along paths and creeks: 5-9 small stones, 5-18 cm.
    'Pebbles': dict(count=(5, 9), size=(.05, .18), spread=.5, colours=('#6e6a62', '#b0a898', '')),
    # A few bigger half-buried stones in the meadow, mossy on top.
    'StonesMossy': dict(count=(1, 3), size=(.2, .42), spread=.4, colours=('#6a665c', '#a8a090', '#6a8a3a')),
}


def build_stones(name, k, rng):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    col = bm.loops.layers.color.new('Col')
    for _ in range(rng.randint(*k['count'])):
        a, r = rng.uniform(0, math.tau), k['spread'] * math.sqrt(rng.random())
        stone(bm, col, rng, Vector((math.cos(a) * r, math.sin(a) * r, 0)), rng.uniform(*k['size']), k['colours'])
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    mat = bpy.data.materials.get('QingxiStone') or bpy.data.materials.new('QingxiStone')
    me.materials.append(mat)
    return ob


def build(name, k, rng):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    col = bm.loops.layers.color.new('Col')
    for _ in range(k['blades']):
        a, r = rng.uniform(0, math.tau), k['spread'] * math.sqrt(rng.random())
        base = Vector((math.cos(a) * r, math.sin(a) * r, 0))
        yaw = a + rng.uniform(-.8, .8)   # blades lean outward from the clump's heart
        blade(bm, col, rng, base, rng.uniform(*k['height']), rng.uniform(*k['width']), rng.uniform(*k['lean']), yaw, k['colours'])
    if k.get('flowers'):
        n, petal, centre = k['flowers']
        for _ in range(n):
            a, r = rng.uniform(0, math.tau), k['spread'] * .8 * math.sqrt(rng.random())
            flower(bm, col, rng, Vector((math.cos(a) * r, math.sin(a) * r, 0)), rng.uniform(.18, .3), petal, centre, k['colours'])
    bm.to_mesh(me)
    bm.free()
    # Normals point up and a little out: the clump shades as one soft tuft.
    me.normals_split_custom_set([(Vector(me.vertices[l.vertex_index].co) * Vector((1, 1, 0)) * 1.5 + Vector((0, 0, 1))).normalized() for l in me.loops])
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    mat = bpy.data.materials.get('QingxiGrass') or bpy.data.materials.new('QingxiGrass')
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    if not any(n.type == 'VERTEX_COLOR' for n in nodes):
        vc = nodes.new('ShaderNodeVertexColor')
        vc.layer_name = 'Col'
        mat.node_tree.links.new(vc.outputs['Color'], next(n for n in nodes if n.type == 'BSDF_PRINCIPLED').inputs['Base Color'])
    me.materials.append(mat)
    return ob


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    PREVIEW.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = []
    for i, (name, k) in enumerate(list(KITS.items()) + list(STONES.items())):
        ob = (build_stones if name in STONES else build)(name, k, random.Random(i + 7))
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.ops.export_scene.fbx(filepath=str(OUT / f'{name}.fbx'), use_selection=True, object_types={'MESH'},
                                 axis_forward='-Z', axis_up='Y', apply_scale_options='FBX_SCALE_ALL',
                                 bake_space_transform=True, mesh_smooth_type='OFF', colors_type='SRGB')
        objs.append(ob)
        print('GROUND_KIT', name, sum(len(p.vertices) - 2 for p in ob.data.polygons), 'tris')
    # Review: a small meadow of each clump.
    scene = bpy.context.scene
    for e in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
        try:
            scene.render.engine = e
            break
        except TypeError:
            pass
    scene.render.resolution_x, scene.render.resolution_y = 1600, 700
    rng = random.Random(3)
    for i, ob in enumerate(objs):
        for _ in range(40):
            c = ob.copy()
            scene.collection.objects.link(c)
            c.location = (i * 1.6 + rng.uniform(-.6, .6), rng.uniform(-.6, .6), 0)
            c.rotation_euler.z = rng.uniform(0, math.tau)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(4, 0, 0))
    g = bpy.context.active_object
    g.scale = (14, 5, 1)
    gm = bpy.data.materials.new('soil')
    gm.use_nodes = True
    next(n for n in gm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = (.12, .2, .06, 1)
    g.data.materials.append(gm)
    w = bpy.data.worlds.new('w')
    scene.world = w
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (.55, .7, .9, 1)
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(45), 0, math.radians(30))
    sun.data.energy = 4
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.location = (4, -4.2, 1.4)
    cam.rotation_euler = (math.radians(78), 0, 0)
    scene.render.filepath = str(PREVIEW / 'kit.png')
    bpy.ops.render.render(write_still=True)


main()
