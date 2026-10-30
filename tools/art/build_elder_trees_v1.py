"""Game trees built on z1nnz's Elder World Tree (elder-tree-esg, 生命樹庭園_母稿.blend).

Input: art/exports/elder-world-tree-hero-v1/elder-world-tree-hero-v1.glb (the extracted hero: trunk, branches
and roots, about 61 000 leaf cards coloured by vertex colour). Output: art/exports/elder-trees-v1/ with one FBX
per tree (three LODs named <Tree>_LOD0..2 for Unity's LOD group), the bark texture, one leaf palette per tree,
review renders and a report.

The trees:
  ElderGuardian  建木, the hero itself: every leaf, roots and all (the old forest's 守脈古樹)
  JianmuSapling  a young 建木, the same tree a third the size, hanging roots and all (the player's own plot)
The other species (camphor, maple, ginkgo, willow, plum, cypress, withered) are grown branch by branch, each with
its own trunk and leaf, in build_species_trees_v1.py.
Leaf colour: Unity's lit shader ignores vertex colour, so each leaf's colour is quantised into a 64-swatch
palette texture and the leaf's UVs point at its swatch. Recolouring a variant maps the palette by brightness.
LODs keep a random share of the leaf cards and grow each kept card about its own centre, so the canopy keeps
its coverage; the wood is decimated for LOD1 and LOD2.

Run: blender -b --factory-startup -P tools/art/build_elder_trees_v1.py
"""
import colorsys
import json
import math
import random
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'art/exports/elder-world-tree-hero-v1/elder-world-tree-hero-v1.glb'
OUT = ROOT / 'art/exports/elder-trees-v1'
PREVIEW = ROOT / 'art/previews/elder-trees-v1'
SWATCHES = 64
FOOT = 3.15   # source height of the trunk's foot, where the hanging roots begin

# keep: share of leaf cards per LOD; grow: card scale per LOD; wood: decimate ratio per LOD.
LODS = [dict(keep=1.0, grow=1.0, wood=1.0), dict(keep=.07, grow=2.6, wood=.3), dict(keep=.02, grow=4.2, wood=.08)]

# Each species reshapes the same trunk, branches and leaves (see shape()):
#   girth     trunk thickness about its own centre line (the crown keeps its size)
#   stretch   trunk length between the foot and the crown base (1 = as modelled)
#   straight  1 pulls the trunk onto a straight axis, 0 keeps the modelled S-curve, negative exaggerates it
#   twist     degrees of twist from the foot to the crown top; lean: metres of lean per metre of height
#   crown     crown scale (x, y, z) about the axis; cone: 0 round … 1 a pointed crown
#   droop     metres the outer crown hangs down (willow); leafz: leaf cards stretched vertically
#   scale     the whole tree; colours: palette stops dark → light (None keeps the source colours)
BASE = dict(roots=False, girth=1, stretch=1, straight=0, twist=0, lean=0, crown=(1, 1, 1), cone=0, droop=0, leafz=1,
            scale=(1, 1, 1), mirror=False, colours=None, sparse=1)
TREES = {
    # 建木: the hero itself, roots and all (the 守脈古樹 in the old forest).
    'ElderGuardian': dict(BASE, roots=True, seed=1),
    # A young 建木: the same tree, hanging roots and all, a third the size (the one in the player's own plot).
    'JianmuSapling': dict(BASE, roots=True, scale=(.3, .3, .3), seed=9, sparse=.5),
}
# The other species are grown branch by branch in build_species_trees_v1.py.
CROWN = 6.0      # source height of the crown base
CROWN_TOP = 9.8  # source height of the crown top
AXIS = []        # trunk centre line: (z, x, y) every 0.25 m, from the source trunk

def hex_rgb(h):
    """sRGB hex to linear (vertex colours and the palette maths are linear)."""
    def lin(c):
        return c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4
    return tuple(lin(int(h[i:i + 2], 16) / 255) for i in (1, 3, 5))


def lum(c):
    return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]


def gradient(stops, t):
    t = min(max(t, 0), 1) * (len(stops) - 1)
    i = min(int(t), len(stops) - 2)
    f = t - i
    a, b = hex_rgb(stops[i]), hex_rgb(stops[i + 1])
    return tuple(a[k] + (b[k] - a[k]) * f for k in range(3))


def load_source():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    objs = {o.name: o for o in bpy.data.objects if o.type == 'MESH'}
    for o in objs.values():
        o.data.transform(o.matrix_world)
        o.matrix_world = Matrix.Identity(4)
        o.parent = None
    return objs['主幹'], objs['SM_ElderWorldTree_Batch_01'], objs['SM_ElderWorldTree_Batch_02']


def islands(bm):
    seen, out = set(), []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack, group = [f], []
        seen.add(f.index)
        while stack:
            x = stack.pop()
            group.append(x)
            for e in x.edges:
                for o in e.link_faces:
                    if o.index not in seen:
                        seen.add(o.index)
                        stack.append(o)
        out.append(group)
    return out


def leaf_cards(leaves):
    """Each leaf card: its faces' vertex positions, loop normals, colour and centre."""
    me = leaves.data
    me.calc_loop_triangles() if hasattr(me, 'calc_loop_triangles') else None
    colour = me.color_attributes['Color']
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    cards = []
    normals = [Vector(l.vector) for l in me.corner_normals] if hasattr(me, "corner_normals") else None
    for group in islands(bm):
        polys = []
        rgb = Vector((0, 0, 0))
        n = 0
        for f in group:
            loops = []
            for l in f.loops:
                c = colour.data[l.index].color
                rgb += Vector(c[:3])
                n += 1
                loops.append((l.vert.co.copy(), normals[l.index] if normals else f.normal.copy()))
            polys.append(loops)
        centre = sum((p for poly in polys for p, _ in poly), Vector()) / sum(len(p) for p in polys)
        cards.append(dict(polys=polys, colour=tuple(rgb / max(n, 1)), centre=centre))
    bm.free()
    return cards


def palette(cards, stops):
    """64 swatches sorted by brightness; each card gets its nearest swatch."""
    ranked = sorted(range(len(cards)), key=lambda i: lum(cards[i]['colour']))
    swatches = []
    for s in range(SWATCHES):
        members = ranked[s * len(ranked) // SWATCHES:(s + 1) * len(ranked) // SWATCHES]
        avg = [sum(cards[i]['colour'][k] for i in members) / max(len(members), 1) for k in range(3)]
        for i in members:
            cards[i]['swatch'] = s
        swatches.append(tuple(avg) if stops is None else gradient(stops, (s + .5) / SWATCHES))
    return swatches


def save_palette(name, swatches):
    img = bpy.data.images.new(name, SWATCHES, 4, alpha=False)
    px = []
    for _ in range(4):
        for c in swatches:
            # Vertex colours are linear; the PNG is sRGB.
            px += [((x * 12.92) if x <= .0031308 else (1.055 * x ** (1 / 2.4) - .055)) for x in c] + [1]
    img.pixels = px
    img.filepath_raw = str(OUT / f'{name}.png')
    img.file_format = 'PNG'
    img.save()
    return img


def centre(z):
    """The source trunk's centre (x, y) at height z, clamped to the trunk."""
    z = min(max(z, AXIS[0][0]), AXIS[-1][0])
    for (z0, x0, y0), (z1, x1, y1) in zip(AXIS, AXIS[1:]):
        if z <= z1:
            t = (z - z0) / max(z1 - z0, 1e-6)
            return Vector((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    return Vector(AXIS[-1][1:])


def trunk_axis(trunk):
    zs = [v.co.z for v in trunk.data.vertices]
    lo, hi = max(min(zs), FOOT), min(max(zs), CROWN + 1)
    z = lo
    while z <= hi:
        ring = [v.co for v in trunk.data.vertices if abs(v.co.z - z) < .18]
        if ring:
            AXIS.append((z, sum(c.x for c in ring) / len(ring), sum(c.y for c in ring) / len(ring)))
        z += .25


def shape(p, spec):
    """Reshape one source point into the species (trunk curve, length, crown form, droop, twist, lean).
    Returns the new point and the twist angle there (for the leaf normals)."""
    z0 = p.z
    # Trunk girth about the trunk's own centre at this height, fading out into the crown.
    if spec['girth'] != 1:
        k = 1 + (spec['girth'] - 1) * (1 - min(max((z0 - (CROWN - 1)) / 1.5, 0), 1))
        c0 = centre(z0)
        p = Vector((c0.x + (p.x - c0.x) * k, c0.y + (p.y - c0.y) * k, z0))
    foot = centre(FOOT)
    # Trunk curve: move every point with the trunk's offset from a straight axis, scaled by (1 - straight).
    bend = centre(min(z0, CROWN)) - foot
    x, y = p.x - spec['straight'] * bend.x, p.y - spec['straight'] * bend.y
    # Trunk length.
    z = z0 if z0 <= FOOT else FOOT + min(z0 - FOOT, CROWN - FOOT) * spec['stretch'] + max(z0 - CROWN, 0)
    base = FOOT + (CROWN - FOOT) * spec['stretch']
    # Crown form about the axis at the crown base, blending in over the lower 1.5 m of the crown.
    axis = foot + (centre(CROWN) - foot) * (1 - spec['straight'])
    w = min(max((z0 - (CROWN - .5)) / 1.5, 0), 1)
    t = min(max((z0 - CROWN) / (CROWN_TOP - CROWN), 0), 1)
    sx, sy, sz = (1 + (c - 1) * w for c in spec['crown'])
    taper = 1 - spec['cone'] * t * .9 * w
    dx, dy = (x - axis.x) * sx * taper, (y - axis.y) * sy * taper
    x, y = axis.x + dx, axis.y + dy
    if z0 > CROWN:
        z = base + (z0 - CROWN) * sz
    r = math.hypot(dx, dy)
    z -= spec['droop'] * w * min(r / 4.5, 1.3) ** 1.6
    # Twist about the foot and lean, growing with height.
    h = max(z - FOOT, 0)
    top = base - FOOT + (CROWN_TOP - CROWN) * spec['crown'][2]
    a = math.radians(spec['twist']) * min(h / max(top, 1e-6), 1)
    rx, ry = x - foot.x, y - foot.y
    x, y = foot.x + rx * math.cos(a) - ry * math.sin(a), foot.y + rx * math.sin(a) + ry * math.cos(a)
    x += spec['lean'] * h
    return Vector((x, y, z)), a

def build_wood(name, trunk, branches, spec, ratio, drop):
    me = bpy.data.meshes.new(name + '_wood')
    bm = bmesh.new()
    for src in (trunk, branches):
        tmp = bmesh.new()
        tmp.from_mesh(src.data)
        if not spec['roots']:
            # Hanging roots: cut everything below the trunk's foot; the spreading buttress roots above it stay.
            geom = tmp.verts[:] + tmp.edges[:] + tmp.faces[:]
            bmesh.ops.bisect_plane(tmp, geom=geom, plane_co=(0, 0, FOOT), plane_no=(0, 0, 1), clear_inner=True)
        tmp.to_mesh(me)
        bm.from_mesh(me)
        tmp.free()
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name + '_wood', me)
    bpy.context.collection.objects.link(ob)
    ob.data.materials.append(bpy.data.materials['ElderBark'])
    for v in me.vertices:
        v.co = shape(v.co, spec)[0]
        v.co.z -= drop
    if ratio < 1:
        mod = ob.modifiers.new('decimate', 'DECIMATE')
        mod.ratio = ratio
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return ob


def build_leaves(name, cards, lod, material, rng, drop, spec):
    me = bpy.data.meshes.new(name + '_leaves')
    verts, faces, uvs, norms = [], [], [], []
    sparse = spec['sparse']
    grow = lod['grow'] / math.sqrt(sparse)
    for card in cards:
        if rng.random() > lod['keep'] * sparse:
            continue
        c, a = shape(card['centre'], spec)
        u = (card['swatch'] + .5) / SWATCHES
        for poly in card['polys']:
            idx = []
            for p, n in poly:
                # Each card keeps its own form: offsets from the source centre, grown, stretched for long leaves.
                d = (p - card['centre']) * grow
                d.z *= spec['leafz']
                q = c + Vector((d.x * math.cos(a) - d.y * math.sin(a), d.x * math.sin(a) + d.y * math.cos(a), d.z))
                q.z -= drop
                idx.append(len(verts))
                verts.append(q)
                uvs.append((u, .5))
                norms.append(Vector((n.x * math.cos(a) - n.y * math.sin(a), n.x * math.sin(a) + n.y * math.cos(a), n.z)))
            faces.append(idx)
    me.from_pydata(verts, [], faces)
    uv = me.uv_layers.new(name='UVMap')
    for loop in me.loops:
        uv.data[loop.index].uv = uvs[loop.vertex_index]
    me.normals_split_custom_set([norms[l.vertex_index] for l in me.loops])
    ob = bpy.data.objects.new(name + '_leaves', me)
    bpy.context.collection.objects.link(ob)
    me.materials.append(material)
    return ob


def leaf_material(name, image):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = image
    tex.interpolation = 'Closest'
    mat.node_tree.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = .8
    return mat


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    PREVIEW.mkdir(parents=True, exist_ok=True)
    trunk, branches, leaves = load_source()
    bark = bpy.data.materials['樹皮深棕']
    bark_img = next(n.image for n in bark.node_tree.nodes if n.type == 'TEX_IMAGE')
    bark_img.filepath_raw = str(OUT / 'ElderBark.png')
    bark_img.file_format = 'PNG'
    bark_img.save()
    bark.name = 'ElderBark'
    cards = leaf_cards(leaves)
    trunk_axis(trunk)
    report = {'source': str(SOURCE.relative_to(ROOT)), 'leaf_cards': len(cards), 'trees': {}}
    for o in (trunk, branches, leaves):
        o.hide_set(True)
        o.hide_render = True
    built = []
    for name, spec in TREES.items():
        swatches = palette(cards, spec['colours'])
        img = save_palette(name + '_Leaves', swatches)
        mat = leaf_material(name + '_Leaves', img)
        drop = 0 if spec['roots'] else FOOT - .12   # without the hanging roots the trunk's foot comes down to the ground
        root = bpy.data.objects.new(name, None)
        bpy.context.collection.objects.link(root)
        tris = []
        for i, lod in enumerate(LODS):
            rng = random.Random(spec['seed'] * 100 + i)
            wood = build_wood(f'{name}_LOD{i}', trunk, branches, spec, lod['wood'], drop)
            leaf = build_leaves(f'{name}_LOD{i}', cards, lod, mat, rng, drop, spec)
            bpy.ops.object.select_all(action='DESELECT')
            for o in (wood, leaf):
                o.hide_set(False)
                o.select_set(True)
            bpy.context.view_layer.objects.active = wood
            bpy.ops.object.join()
            wood.name = wood.data.name = f'{name}_LOD{i}'
            sx, sy, sz = spec['scale']
            wood.data.transform(Matrix.Diagonal((-sx if spec['mirror'] else sx, sy, sz, 1)))
            if spec['mirror']:
                wood.data.flip_normals()
            wood.parent = root
            tris.append(sum(len(p.vertices) - 2 for p in wood.data.polygons))
        lod0 = bpy.data.objects[f'{name}_LOD0']
        pts = [lod0.matrix_world @ v.co for v in lod0.data.vertices]
        dims = [round(max(p[k] for p in pts) - min(p[k] for p in pts), 2) for k in range(3)]
        report['trees'][name] = {'triangles_per_lod': tris, 'size_m': dims, 'min_z': round(min(p.z for p in pts), 2)}
        built.append(root)
        bpy.ops.object.select_all(action='DESELECT')
        root.select_set(True)
        for c in root.children:
            c.select_set(True)
        bpy.ops.export_scene.fbx(filepath=str(OUT / f'{name}.fbx'), use_selection=True, object_types={'MESH', 'EMPTY'},
                                 axis_forward='-Z', axis_up='Y', apply_scale_options='FBX_SCALE_ALL',
                                 bake_space_transform=True, mesh_smooth_type='OFF', path_mode='RELATIVE',
                                 add_leaf_bones=False, bake_anim=False)
    render_lineup(built)
    (OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('ELDER_TREES ' + json.dumps(report, ensure_ascii=False))


def render_lineup(roots):
    scene = bpy.context.scene
    for e in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
        try:
            scene.render.engine = e
            break
        except TypeError:
            pass
    scene.render.resolution_x, scene.render.resolution_y = 2800, 900
    world = bpy.data.worlds.new('w')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.78, .84, .88, 1)
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(50), 0, math.radians(35))
    sun.data.energy = 3.5
    x = 0
    for r in roots:
        for c in r.children:
            c.hide_render = not c.name.endswith('LOD0')
        xs = [v.co.x for c in r.children if c.name.endswith('LOD0') for v in c.data.vertices]
        r.location.x = x - min(xs)
        x += max(xs) - min(xs) + 1.5
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.location = (x / 2, -x * 1.3, 3.2)
    cam.rotation_euler = (math.radians(89), 0, 0)
    cam.data.lens = 50
    scene.render.filepath = str(PREVIEW / 'lineup.png')
    bpy.ops.render.render(write_still=True)
    for i, lod in enumerate(LODS):
        for r in roots:
            for c in r.children:
                c.hide_render = not c.name.endswith(f'LOD{i}')
        scene.render.filepath = str(PREVIEW / f'lineup-lod{i}.png')
        bpy.ops.render.render(write_still=True)


main()
