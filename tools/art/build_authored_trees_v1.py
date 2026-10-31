"""Trees authored the way Codex built z1nnz's Elder World Tree (elder-tree-esg tools/blender/build_life_tree.py):
the trunk centre line and the main limbs are written by hand to a reference sheet, so the first few limbs own the
silhouette; each limb grows two secondary branches and each of those two twigs on a fixed rule; the trunk and the
root collar are one fluted surface; the crown is many clusters of small cupped leaves (five vertices, a raised
midrib) laid along curling sprays, coloured by height from deep teal to sunlit yellow-green. No alpha cards.

Unity's lit shader ignores vertex colour, so each leaf's colour is a swatch in a 64 x 4 palette texture the leaf's
UVs point at (as the other Elder trees). Bark: z1nnz's painted sheet (art/references/tree-species-v1/bark-*.png),
box-projected at about 1.2 m per tile. Three LODs (fewer, larger leaves; decimated wood).

Species so far: Camphor (樟, art/references/tree-species-v1/camphor.png).
Output: art/exports/elder-trees-v1/Elder<Species>.fbx (+ _Bark.png, _Leaves.png), review render in
art/previews/authored-trees-v1/. Run: blender -b --factory-startup -P tools/art/build_authored_trees_v1.py
"""
import json
import math
import random
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
REFS = ROOT / 'art/references/tree-species-v1'
OUT = ROOT / 'art/exports/elder-trees-v1'
PREVIEW = ROOT / 'art/previews/authored-trees-v1'
SWATCHES = 64
UP = Vector((0, 0, 1))


def lin(h):
    def c(x):
        return x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4
    return tuple(c(int(h[i:i + 2], 16) / 255) for i in (1, 3, 5))


# ------------------------------------------------------------------ the species, written by hand
# 樟 after camphor.png: a massive trunk leaning right and twisting, splitting at about a third of its height into
# a long low limb sweeping left, a limb reaching right, and a leader carrying on up; five more limbs fill the
# broad dome behind and in front. Metres; z up; the trunk foot at the origin.
CAMPHOR = dict(
    name='Camphor',
    # The trunk only to the fork; the two leaders carry on from there (no fan of limbs from one point).
    trunk=[(0, 0, 0), (.45, .05, 1.2), (1.0, .1, 2.4), (1.25, 0, 3.5), (1.2, 0, 4.0)],
    trunk_radii=[1.05, .86, .76, .68, .62],
    limbs=[  # (points along the limb, radius at its base); bends written in, thickness very unequal
        # a low limb leaving the trunk at 2.2 m, dipping then rising as it sweeps left
        ([(.75, 0, 2.2), (-.8, .2, 2.85), (-2.6, .35, 3.1), (-4.2, .55, 3.85), (-5.6, .4, 4.75)], .42),
        # leader 1: up and to the left in an S
        ([(1.15, .05, 3.7), (.65, .25, 5.0), (-.55, .55, 6.15), (-1.35, .9, 7.6), (-1.55, 1.25, 9.1)], .56),
        # leader 2: out to the right, kinking up
        ([(1.3, -.05, 3.7), (2.35, -.25, 4.5), (3.05, -.1, 5.75), (4.3, -.35, 6.55), (5.5, -.45, 7.05)], .5),
        # two thin ones behind and in front
        ([(1.1, .3, 4.1), (1.0, 1.6, 4.95), (.6, 3.0, 6.2), (.2, 4.2, 6.6)], .22),
        ([(1.0, -.3, 4.4), (1.6, -1.6, 5.35), (1.4, -3.2, 6.3), (1.9, -4.1, 6.95)], .19),
        # from the leaders' middles
        ([(-.55, .55, 6.15), (-2.2, .4, 7.0), (-3.6, .8, 7.45)], .2),
        ([(3.05, -.1, 5.75), (3.25, .6, 7.2), (2.8, 1.1, 8.6)], .19),
    ],
    front=[(1.2, -2.6, 5.4), (-1.6, -1.6, 5.6), (3.0, -1.8, 6.4), (-3.2, -.8, 4.6)],   # foliage in front of the trunk
    roots=[  # (middle, buried end, radius at the collar)
        ((-1.5, -.4, .08), (-2.9, -.8, -.4), .55), ((1.4, -.7, .06), (2.6, -1.2, -.4), .5),
        ((1.1, 1.0, .05), (2.0, 1.9, -.4), .45), ((-1.1, .9, .07), (-2.2, 1.6, -.4), .45),
        ((.2, -1.4, .05), (.4, -2.5, -.35), .38), ((-.6, -1.1, .04), (-1.1, -1.9, -.3), .3),
        ((.9, .2, .05), (1.8, .4, -.3), .3),
    ],
    cluster_scale=(2.6, 2.6, 1.8), leaves_per_cluster=1700, leaf_size=(.032, .056),
    palette=['#163f3c', '#1f5e48', '#3f8a3a', '#8cbc2c', '#d6e650'],
    bark='camphor', height_hint=13.5,
)
# The Elder World Tree's structure from build_life_tree.py, number for number (its 4.3 m trunk; S scales it up):
# the 7-point S trunk, the eight limbs ("the first three own the silhouette"), the ten roots and the sixteen leaf
# clusters with their scales. Its bevel x radius products are written here as plain radii in metres.
ELDER = dict(
    trunk=[(0, 0, .05), (.42, -.04, .78), (.72, .04, 1.45), (.54, .10, 2.10), (-.06, .02, 2.75), (-.45, 0, 3.35), (-.12, .02, 4.30)],
    trunk_radii=[r * .58 for r in (1.45, 1.15, .99, .85, .62, .36, .08)],
    limbs=[((.62, .01, 1.75), (-.45, -.10, 2.80), (-3.75, -.05, 3.30)), ((.42, .02, 2.25), (1.95, -.10, 3.15), (3.80, -.25, 3.35)),
           ((.08, .08, 2.60), (-1.10, .65, 3.32), (-2.85, 1.10, 4.05)), ((.10, .06, 2.72), (1.25, .75, 3.55), (2.60, 1.20, 4.20)),
           ((-.30, -.02, 3.10), (-1.25, -.70, 3.82), (-2.05, -1.10, 4.70)), ((-.25, .04, 3.30), (.72, -.65, 3.98), (1.75, -1.05, 4.65)),
           ((-.32, .08, 3.48), (-.80, .34, 4.35), (-.95, .42, 5.20)), ((-.25, .03, 3.65), (.40, .17, 4.42), (.75, .22, 5.08))],
    roots=[((-1.82, -.54), (-.92, -.22, .04), .58, 1.35 * .23), ((1.48, -.68), (.72, -.32, .03), .58, 1.35 * .23),
           ((.98, .82), (.34, .46, .02), .34, .8 * .18), ((-1.28, .52), (-.58, .34, .04), .34, .8 * .18),
           ((.30, -.92), (-.08, -.46, .03), .34, .8 * .18), ((-.58, -.74), (-.34, -.31, .04), .11, .54 * .14),
           ((1.05, .18), (.48, .08, .05), .11, .54 * .14), ((-.72, .32), (-.32, .16, .05), .11, .54 * .14),
           ((.58, -.52), (.20, -.26, .05), .11, .54 * .14), ((.12, .64), (0, .30, .05), .11, .54 * .14)],
    back=[((-2.95, .75, 3.90), (1.82, 1.50, 1.55)), ((-1.90, 1.35, 4.55), (1.72, 1.48, 1.65)), ((2.90, .70, 3.85), (1.90, 1.35, 1.45)),
          ((1.85, 1.42, 4.65), (1.62, 1.55, 1.50)), ((-.85, 1.30, 5.28), (1.60, 1.50, 1.55)), ((.35, .90, 5.16), (1.68, 1.55, 1.80)),
          ((1.10, .50, 4.85), (1.50, 1.55, 1.45)), ((-.12, 1.80, 4.60), (1.52, 1.70, 1.45))],
    front=[((-3.10, -.58, 3.52), (1.70, 1.25, 1.40)), ((-1.80, -1.28, 3.92), (1.95, 1.50, 1.55)), ((3.15, -.62, 3.55), (1.70, 1.32, 1.35)),
           ((1.82, -1.34, 4.05), (1.85, 1.5, 1.60)), ((-1.30, -.98, 4.75), (1.75, 1.45, 1.70)), ((-.40, -.80, 5.15), (1.72, 1.50, 1.70)),
           ((.90, -.96, 4.76), (1.55, 1.5, 1.40)), ((.12, -1.54, 3.90), (1.65, 1.5, 1.40))],
)


def elder_hierarchy(i, pts, S, branches, g=1.0):
    """build_life_tree.py add_branch_hierarchy, unchanged except for the scale."""
    _, middle, original_end = (Vector(p) * S for p in pts)
    end = middle.lerp(original_end, .67)
    axis = (end - middle).normalized()
    lateral = Vector((-axis.y, axis.x, 0))
    lateral = lateral.normalized() if lateral.length > .01 else Vector((1, 0, 0))
    for k, sign in enumerate((-1.0, 1.0), start=1):
        st = middle.lerp(end, .28 + k * .18)
        mid = st + (axis * (.20 + k * .04) + lateral * sign * (.20 + i % 3 * .035) + UP * (.08 + k * .03)) * S
        en = st + (axis * (.40 + k * .05) + lateral * sign * (.42 + i % 2 * .06) + UP * (.18 + k * .04)) * S
        branches.append(curve(f'sec_{i}_{k}', [st, mid, en], [r * .115 * S * g for r in (.58, .30, .04)]))
        for j, ts_ in enumerate((-1.0, 1.0), start=1):
            ts = mid.lerp(en, .42 + j * .14)
            ta = (en - mid).normalized()
            tl = Vector((-ta.y, ta.x, 0))
            tl = tl.normalized() if tl.length > .01 else lateral
            tm = ts + (ta * .12 + tl * ts_ * (.09 + k * .02) + UP * .06) * S
            te = ts + (ta * .24 + tl * ts_ * (.20 + k * .025) + UP * .035) * S
            branches.append(curve(f'twig_{i}_{k}_{j}', [ts, tm, te], [r * .07 * S * g for r in (.42, .20, .025)]))


def lean_form(variant, spec):
    """How one variant's trunk stands: it leans its own way by its own amount, sways sideways through its height,
    and may be mirrored. Applied to the skeleton in the Elder tree's own units (trunk 4.3 m), the foot unmoved."""
    rng = random.Random(hash((spec['name'], variant)) & 0xffff)
    a = rng.uniform(0, math.tau)
    lean = spec.get('lean', 1.0) * (.35, .9, 1.5)[variant] * rng.uniform(.85, 1.15)   # upright-ish, leaning, leaning hard
    sway = rng.choice((-1, 1)) * rng.uniform(.5, 1.0)
    stretch = (1.0, rng.uniform(.85, .95), rng.uniform(1.05, 1.15))[variant]
    mirror = rng.choice((1, -1)) if variant else 1
    d, side = Vector((math.cos(a), math.sin(a), 0)), Vector((-math.sin(a), math.cos(a), 0))

    def T(p):
        p = Vector(p)
        p.x *= mirror
        t = max(0.0, min(p.z / 4.3, 1.5))
        p.z *= stretch
        return p + d * lean * t ** 1.5 + side * sway * math.sin(math.pi * min(t, 1))
    return T


def build_traced_form(spec, variant=0):
    """A species on its own traced skeleton (tools/art/trace_tree_skeleton.py, from z1nnz's skeleton sheet): every
    branch a smooth curve at its traced thickness, the trunk fluted like the Elder World Tree's, a few roots diving
    into the soil, and the crown as clusters of cupped leaves gathered over the branch tips. Variants: as drawn,
    mirrored, mirrored and a little shorter."""
    # Variants: the sheet's left tree, its right tree (a different tree), and the left one mirrored and shorter.
    second = REFS / f"skeleton-{spec['skeleton']}-b.json"
    src = second if variant == 1 and second.exists() else REFS / f"skeleton-{spec['skeleton']}.json"
    data = json.loads(src.read_text(encoding='utf-8'))
    name = 'Elder' + spec['name']
    mx = -1 if variant == 2 else 1
    sz = (.9 if variant == 2 else 1.0) * spec.get('tall', 1.3)
    bark_src = bpy.data.images.load(str(OUT / 'ElderBark.png'))
    tint = spec.get('bark_tint')
    if tint:
        import numpy as np
        px = np.array(bark_src.pixels[:], dtype=np.float32).reshape(-1, 4)
        grey = px[:, :3] @ np.array([.2126, .7152, .0722], dtype=np.float32)
        t = np.array(lin(tint), dtype=np.float32)
        px[:, :3] = np.clip(px[:, :3] * .35 + (grey[:, None] / max(grey.mean(), 1e-3)) * t[None, :] * .65, 0, 1)
        bark_src.pixels = px.ravel().tolist()
    bark_src.filepath_raw = str(OUT / f'{name}_Bark.png')
    bark_src.file_format = 'PNG'
    bark_src.save()
    bark_mat = material(f'{name}_Bark', bark_src)
    leaf_mat = material(f'{name}_Leaves', palette_image(f'{name}_Leaves', spec['palette']), closest=True)
    girth = spec.get('girth', .7)   # the drawings' trunks are heavy for a game tree
    pieces, tips = [], []
    branches = data['branches']
    has_child = {b['parent'] for b in branches}
    for i, b in enumerate(branches):
        pts = [Vector((x * mx, y, z * sz)) for x, y, z in b['points']]
        if len(pts) < 2:
            continue
        if b['depth'] > 0 and min(p.z for p in pts) < 1.2:   # limbs drooping to the ground in the drawing: left out
            continue
        # Traced thickness wobbles pixel to pixel: smooth it along the branch and never let it grow outward.
        raw = b['radii']
        sm = [sum(raw[max(0, k - 3):k + 4]) / len(raw[max(0, k - 3):k + 4]) for k in range(len(raw))]
        for k in range(1, len(sm)):
            sm[k] = min(sm[k], sm[k - 1])
        radii = [max(r * girth, .012) for r in sm]
        if b['parent'] >= 0:   # start inside the parent so the joint has no seam
            pts[0] = pts[0] - (pts[1] - pts[0]).normalized() * radii[0] * .5
        if i not in has_child:
            tips.append(pts[-1])
        pieces.append(to_mesh(curve(f'b{i}', pts, radii)))
    trunk = pieces[0]
    # Flutes on the trunk (as build_life_tree.py), fading out above the first fork.
    cl = [Vector((x * mx, y, z * sz)) for x, y, z in branches[0]['points']]
    top = cl[-1].z
    for v in trunk.data.vertices:
        w = v.co
        seg = next((k for k in range(len(cl) - 1) if w.z <= cl[k + 1].z), len(cl) - 2)
        a, b = cl[seg], cl[seg + 1]
        t = max(0, min(1, (w.z - a.z) / max(b.z - a.z, 1e-6)))
        c = a.lerp(b, t)
        radial = Vector((w.x - c.x, w.y - c.y, 0))
        ang = math.atan2(radial.y, radial.x)
        fade = max(0, 1 - w.z / max(top, .1))
        v.co += radial * (math.sin(ang * 5 + w.z * .6) * .1 + .035 * math.sin(ang * 9 - w.z * .4)) * fade
    r0 = branches[0]['radii'][0] * girth
    for k in range(6):   # roots diving into the soil
        a = k * 1.05 + .3
        d = Vector((math.cos(a), math.sin(a), 0))
        pieces.append(to_mesh(curve(f'root{k}', [d * r0 * .2 + Vector((0, 0, r0 * .9)), d * r0 * 1.4 + Vector((0, 0, r0 * .15)),
                                                  d * r0 * 2.2 + Vector((0, 0, -r0 * .9))], [r0 * .45, r0 * .28, r0 * .1])))
    bpy.ops.object.select_all(action='DESELECT')
    for o in pieces:
        o.select_set(True)
    bpy.context.view_layer.objects.active = trunk
    bpy.ops.object.join()
    for poly in trunk.data.polygons:
        poly.use_smooth = True
    box_uv(trunk.data, tile=1.6)
    trunk.data.materials.clear()
    trunk.data.materials.append(bark_mat)
    trunk.data.materials.append(leaf_mat)
    # Crown: tips gathered into clusters about `cluster` metres across, one leaf cluster over each.
    cell = spec.get('cluster', 1.6)
    groups = {}
    for tp in tips:
        groups.setdefault((round(tp.x / cell), round(tp.y / cell), round(tp.z / cell)), []).append(tp)
    clusters = []
    for g in groups.values():
        c = sum(g, Vector()) / len(g)
        if c.z < max(2.6, data['height'] * .3) and not spec.get('hang'):   # no foliage lying on the ground under drooping limbs
            continue
        r = cell * (.55 + .12 * min(len(g), 6))
        clusters.append((c, Vector((r, r, r * spec.get('crown_z', .75)))))
    return name, trunk, bark_mat, leaf_mat, clusters


def build_elder_form(spec, variant=0):
    """A species on the Elder World Tree's own skeleton, scaled by spec['scale'], with the species' bark and leaf
    colours: the trunk fluted as build_life_tree.py flutes it and fused with its roots, the eight limbs with their
    secondaries and twigs, and sixteen clusters of 1875 cupped leaves."""
    S = spec['scale']
    name = 'Elder' + spec['name']
    wide, tall = spec.get('wide', 1.0), spec.get('tall', 1.0)
    # Every species stands on the Elder skeleton, stretched across and up in its own proportions (a ginkgo narrow
    # and tall, a maple wide and low); the stretch is applied to the finished wood below.
    bark_src = bpy.data.images.load(str(OUT / 'ElderBark.png'))   # the Elder World Tree's own bark
    tint = spec.get('bark_tint')
    if tint:
        import numpy as np
        w_, h_ = bark_src.size
        px = np.array(bark_src.pixels[:], dtype=np.float32).reshape(-1, 4)
        grey = px[:, :3] @ np.array([.2126, .7152, .0722], dtype=np.float32)
        t = np.array(lin(tint), dtype=np.float32)
        px[:, :3] = np.clip(px[:, :3] * .35 + (grey[:, None] / max(grey.mean(), 1e-3)) * t[None, :] * .65, 0, 1)
        bark_src.pixels = px.ravel().tolist()
    bark_src.filepath_raw = str(OUT / f'{name}_Bark.png')
    bark_src.file_format = 'PNG'
    bark_src.save()
    bark_mat = material(f'{name}_Bark', bark_src)
    leaf_mat = material(f'{name}_Leaves', palette_image(f'{name}_Leaves', spec['palette']), closest=True)
    T = lean_form(variant, spec)
    # Girth: the Elder World Tree is a fantasy giant with a trunk as thick as it is tall to the fork; an ordinary
    # tree of the same height has a far slimmer one. g brings the trunk foot to the species' real radius
    # (spec['trunk_r'], metres); limbs thin a little less, twigs least, so the crown keeps its reach.
    g = spec.get('trunk_r', .84 * S) / (.84 * S)
    g_limb, g_twig = g ** .6, g ** .4
    E = dict(ELDER)
    E['trunk'] = [T(p) for p in ELDER['trunk']]
    E['limbs'] = [tuple(T(p) for p in limb) for limb in ELDER['limbs']]
    E['back'] = [(T(c), sc) for c, sc in ELDER['back']]
    E['front'] = [(T(c), sc) for c, sc in ELDER['front']]
    if spec.get('tiers'):
        # Pine and juniper (pine.png, juniper.png): the limbs leave the trunk in tiers all the way up, lower ones
        # longer, each reaching out, sagging a little and turning up at its end under a flat pad of needles.
        trunk_pts = [Vector(p) for p in E['trunk']]

        def on_trunk(z):
            for a_, b_ in zip(trunk_pts, trunk_pts[1:]):
                if z <= b_.z:
                    return a_.lerp(b_, (z - a_.z) / max(b_.z - a_.z, 1e-6))
            return trunk_pts[-1].copy()
        top = trunk_pts[-1].z
        limbs, pads = [], []
        for i, (a0, m0, e0) in enumerate(E['limbs']):
            k = i / (len(E['limbs']) - 1)
            st = on_trunk(top * (.38 + .55 * k))
            out = Vector((e0[0] - a0[0], e0[1] - a0[1], 0))
            out = out.normalized() if out.length > .01 else Vector((1, 0, 0))
            reach = top * (.85 - .45 * k) * random.Random(i * 7 + variant).uniform(.8, 1.15)
            mid = st + out * reach * .5 + Vector((0, 0, -reach * .12))
            end = st + out * reach + Vector((0, 0, -reach * .02))
            limbs.append((tuple(st), tuple(mid), tuple(end)))
            pads.append((tuple(end + Vector((0, 0, .3))), (2.3 - .6 * k, 2.3 - .6 * k, .75)))
            pads.append((tuple(st.lerp(end, .58) + Vector((0, 0, .2))), (1.6 - .4 * k, 1.6 - .4 * k, .6)))
        pads.append((tuple(trunk_pts[-1] + Vector((0, 0, .3))), (1.8, 1.8, .8)))
        E['limbs'], E['back'], E['front'] = limbs, pads, []
    trunk = to_mesh(curve('trunk', [Vector(p) * S for p in E['trunk']], [r * S * g for r in E['trunk_radii']]))
    cl = [Vector(p) * S for p in E['trunk']]
    for v in trunk.data.vertices:   # build_life_tree.py's flutes, in its own (unscaled) units
        w = v.co / S
        seg = next((k for k in range(6) if w.z <= cl[k + 1].z / S), 5)
        a, b = cl[seg] / S, cl[seg + 1] / S
        t = max(0, min(1, (w.z - a.z) / max(b.z - a.z, 1e-6)))
        c = a.lerp(b, t)
        radial = Vector((w.x - c.x, w.y - c.y, 0))
        ang = math.atan2(radial.y, radial.x)
        amp = .09 + .12 * max(0, 1 - w.z / 1.6)
        f = math.sin(ang * 5 + w.z * 1.15) * amp + .035 * math.sin(ang * 9 - w.z * .72)
        v.co += radial * f * S * g
    roots = []
    for k, (end, mid, z0, r) in enumerate(E['roots']):
        # The root's reach shrinks with the girth (a slim trunk has short roots), so none sticks out like a leg.
        reach = max(g, .3) * 1.1
        roots.append(to_mesh(curve('root', [Vector((-.16 if k < 5 else -.06, 0, z0 * max(g, .4))) * S,
                                            Vector((mid[0] * reach, mid[1] * reach, mid[2])) * S,
                                            Vector((end[0] * reach, end[1] * reach, -.18)) * S],
                                   [r * S * g, r * .35 * S * g, r * .1 * S * g])))
    bpy.ops.object.select_all(action='DESELECT')
    for o in [trunk, *roots]:
        o.select_set(True)
    bpy.context.view_layer.objects.active = trunk
    bpy.ops.object.join()
    for mod, kw in (('REMESH', dict(mode='VOXEL', voxel_size=.045 * S * max(g, .35))), ('SMOOTH', dict(factor=.75, iterations=4))):
        m = trunk.modifiers.new(mod, mod)
        for k_, v_ in kw.items():
            setattr(m, k_, v_)
        bpy.ops.object.modifier_apply(modifier=m.name)
    d = trunk.modifiers.new('budget', 'DECIMATE')
    d.ratio = min(1.0, 11000 / max(1, len(trunk.data.polygons) * 2))
    bpy.ops.object.modifier_apply(modifier=d.name)
    branches = []
    for i, pts in enumerate(E['limbs'], start=1):
        bevel = max(.14, .32 - i * .018)
        branches.append(curve(f'limb_{i}', [Vector(p) * S for p in pts], [r * bevel * S * g_limb * (.55 if spec.get('tiers') else 1) for r in (1.12 if i < 4 else .88, .48, .08)]))
        if not spec.get('hang'):   # a weeping tree has no upward twigs: its curtains hang from the limbs
            elder_hierarchy(i, pts, S, branches, g_twig)
    for o in branches:
        to_mesh(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in [trunk, *branches]:
        o.select_set(True)
    bpy.context.view_layer.objects.active = trunk
    bpy.ops.object.join()
    if wide != 1 or tall != 1:
        for v in trunk.data.vertices:
            # Proportions: limbs stretched across and the height stretched up, the trunk foot left as it is.
            k = min(1, v.co.z / (1.5 * S))
            v.co.x *= 1 + (wide - 1) * k
            v.co.y *= 1 + (wide - 1) * k
            v.co.z *= tall
    for poly in trunk.data.polygons:
        poly.use_smooth = True
    box_uv(trunk.data, tile=1.6)
    trunk.data.materials.clear()
    trunk.data.materials.append(bark_mat)
    trunk.data.materials.append(leaf_mat)
    cz = spec.get('crown_z', 1.0)
    clusters = [(Vector((c[0] * S * wide, c[1] * S * wide, c[2] * S * tall)),
                 Vector((sc[0] * S * spec.get('crown_xy', 1.0), sc[1] * S * spec.get('crown_xy', 1.0), sc[2] * S * cz)))
                for c, sc in E['back'] + E['front']]
    if spec.get('hang'):
        # Weeping trees: curtains also hang from every limb end, so no bare tip sticks up out of the crown.
        clusters += [(Vector((c[0] * S * wide, c[1] * S * wide, c[2] * S * tall)), Vector((.9, .9, .6)) * S)
                     for c in (limb[2] for limb in E['limbs'])]
    return name, trunk, bark_mat, leaf_mat, clusters


CAMPHOR_ELDER = dict(trunk_r=1.05, name='Camphor', scale=1.9, leaves_per_cluster=1875, leaf_size=(.025, .048),
                     palette=['#163f3c', '#1f5e48', '#3f8a3a', '#8cbc2c', '#d6e650'])
MAPLE_ELDER = dict(trunk_r=0.35, name='Maple', scale=1.35, wide=1.25, tall=1.06, crown_xy=1.1, crown_z=.8, leaves_per_cluster=1700,
                   leaf_size=(.028, .05), leaf_width=1.6, bark_tint='#8a8278',
                   palette=['#5e1420', '#9c2420', '#cf4522', '#e8802c', '#f6c454'])
GINKGO_ELDER = dict(trunk_r=0.62, name='Ginkgo', scale=1.6, wide=.7, tall=1.45, crown_xy=.8, crown_z=1.15, leaves_per_cluster=1700,
                    leaf_size=(.028, .05), leaf_width=1.5, bark_tint='#8c7f6c',
                    palette=['#7f6a14', '#b88a18', '#e0b028', '#f2d048', '#faea96'])
WILLOW_ELDER = dict(trunk_r=0.58, name='Willow', scale=1.35, wide=1.05, tall=1.15, crown_xy=.62, crown_z=.6, leaves_per_cluster=2300,
                    leaf_size=(.05, .085), leaf_width=.32, hang=2.3, bark_tint='#6e6a5e',
                    palette=['#3a6444', '#5c8a3e', '#8cb24a', '#bcd468', '#e4ee9e'])
PLUM_ELDER = dict(trunk_r=0.28, name='Plum', scale=.85, wide=1.1, tall=.95, crown_xy=.85, crown_z=.85, leaves_per_cluster=1500, sparse=.55,
                  leaf_size=(.03, .05), leaf_width=1.4, bark_tint='#3e2f2a',
                  palette=['#8a2a44', '#d47c96', '#eca8ba', '#f8d2dc', '#fff4f6'])
PINE_ELDER = dict(trunk_r=0.43, name='Pine', scale=1.45, wide=1.0, tall=1.94, crown_xy=1.0, crown_z=.8, tiers=True, lean=1.3, leaves_per_cluster=1900,
                  leaf_size=(.03, .055), leaf_width=.25, bark_tint='#8a5a40',
                  palette=['#14301e', '#1f4a28', '#356a32', '#5e8c3c', '#9ab456'])
JUNIPER_ELDER = dict(trunk_r=0.66, name='Cypress', scale=1.15, wide=1.0, tall=1.69, crown_xy=1.0, crown_z=.8, tiers=True, lean=1.8, leaves_per_cluster=1800,
                     leaf_size=(.026, .046), leaf_width=.6, bark_tint='#b8b0a4',
                     palette=['#14301a', '#204a22', '#356a2a', '#5c8e30', '#98b444'])
# Species traced from z1nnz's skeleton sheets (skeleton-<species>.png -> .json); maple and pine keep the Elder form.
CAMPHOR_TRACED = dict(name='Camphor', skeleton='camphor', cluster=1.7, leaves_total=24000, leaf_size=(0.050, 0.090), crown_z=.7,
                      palette=['#163f3c', '#1f5e48', '#3f8a3a', '#8cbc2c', '#d6e650'])
GINKGO_TRACED = dict(name='Ginkgo', skeleton='ginkgo', cluster=1.6, leaves_total=21600, leaf_size=(0.050, 0.090), leaf_width=1.5,
                     crown_z=.8, bark_tint='#8c7f6c', palette=['#7f6a14', '#b88a18', '#e0b028', '#f2d048', '#faea96'])
WILLOW_TRACED = dict(name='Willow', skeleton='willow', cluster=1.2, leaves_total=18000, leaf_size=(0.080, 0.140), leaf_width=.32,
                     hang=1.6, crown_z=.6, bark_tint='#6e6a5e', palette=['#3a6444', '#5c8a3e', '#8cb24a', '#bcd468', '#e4ee9e'])
PLUM_TRACED = dict(name='Plum', skeleton='plum', cluster=1.0, leaves_total=7200, sparse=.6, leaf_size=(0.060, 0.100), leaf_width=1.4,
                   crown_z=.7, bark_tint='#3e2f2a', palette=['#8a2a44', '#d47c96', '#eca8ba', '#f8d2dc', '#fff4f6'])
JUNIPER_TRACED = dict(name='Cypress', skeleton='juniper', cluster=1.3, leaves_total=19200, leaf_size=(0.044, 0.080), leaf_width=.6,
                      crown_z=.45, girth=1.25, bark_tint='#b8b0a4', palette=['#14301a', '#204a22', '#356a2a', '#5c8e30', '#98b444'])
SPECIES = [CAMPHOR_TRACED, MAPLE_ELDER, GINKGO_TRACED, WILLOW_TRACED, PLUM_TRACED, PINE_ELDER, JUNIPER_ELDER]   # juniper: its sheet has two intertwined trunks the tracer merges
SPREAD = 2.0   # the Elder tree's branch-hierarchy offsets were written for a 4 m trunk; these trees are about twice that

LODS = [dict(keep=1.0, grow=1.0, wood=1.0), dict(keep=.3, grow=1.8, wood=.4), dict(keep=.08, grow=3.2, wood=.15)]


# ------------------------------------------------------------------ geometry (after build_life_tree.py)
def curve(name, points, radii):
    data = bpy.data.curves.new(name, type='CURVE')
    data.dimensions = '3D'
    data.bevel_depth = 1.0
    data.bevel_resolution = 3
    data.resolution_u = 5
    data.use_fill_caps = True
    sp = data.splines.new('BEZIER')
    sp.bezier_points.add(len(points) - 1)
    for p, (co, r) in zip(sp.bezier_points, zip(points, radii)):
        p.co = Vector(co)
        p.radius = r
        p.handle_left_type = p.handle_right_type = 'AUTO'
    ob = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(ob)
    return ob


def to_mesh(ob):
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.convert(target='MESH')
    return ob


def branch_hierarchy(limb_index, points, radius, branches, ends, rng):
    """Secondaries along the outer part of a limb, as build_life_tree.py grows them, but uneven: one to three of
    them, at different places, sides, angles and lengths, each bending through its middle; each carries one or two
    short twigs."""
    pts = [Vector(p) for p in points]
    s = SPREAD
    for k in range(rng.choice((1, 2, 2, 3))):
        t = rng.uniform(.45, .9)
        seg = min(int(t * (len(pts) - 1)), len(pts) - 2)
        f = t * (len(pts) - 1) - seg
        st = pts[seg].lerp(pts[seg + 1], f)
        axis = (pts[seg + 1] - pts[seg]).normalized()
        lateral = Vector((-axis.y, axis.x, 0))
        lateral = lateral.normalized() if lateral.length > .01 else Vector((1, 0, 0))
        side = rng.choice((-1, 1))
        L = rng.uniform(.5, 1.25) * s
        mid = st + axis * .35 * L + lateral * side * rng.uniform(.25, .5) * L + UP * rng.uniform(.05, .3) * L
        en = mid + axis * .45 * L + lateral * side * rng.uniform(.1, .4) * L + UP * rng.uniform(-.05, .25) * L
        r = radius * rng.uniform(.3, .5)
        branches.append(curve(f'sec_{limb_index}_{k}', [st, mid, en], [r, r * .55, .02]))
        ends.append(en)
        for j in range(rng.choice((1, 2))):
            ts = mid.lerp(en, rng.uniform(.3, .8))
            ta = (en - mid).normalized()
            tl = Vector((-ta.y, ta.x, 0))
            tl = tl.normalized() if tl.length > .01 else lateral
            ts2 = rng.choice((-1, 1))
            l2 = rng.uniform(.25, .55) * s
            tm = ts + ta * .4 * l2 + tl * ts2 * .3 * l2 + UP * .15 * l2
            te = tm + ta * .5 * l2 + tl * ts2 * .2 * l2 + UP * rng.uniform(-.05, .2) * l2
            branches.append(curve(f'twig_{limb_index}_{k}_{j}', [ts, tm, te], [r * .45, r * .22, .01]))
            ends.append(te)


def flute(mesh, centreline):
    """Broad twisting lobes on the trunk (build_life_tree.py): change the silhouette and the grazing light."""
    cl = [Vector(p) for p in centreline]
    for v in mesh.vertices:
        w = v.co
        seg = next((i for i in range(len(cl) - 1) if w.z <= cl[i + 1].z), len(cl) - 2)
        a, b = cl[seg], cl[seg + 1]
        t = max(0, min(1, (w.z - a.z) / max(b.z - a.z, 1e-6)))
        c = a.lerp(b, t)
        radial = Vector((w.x - c.x, w.y - c.y, 0))
        ang = math.atan2(radial.y, radial.x)
        amp = .09 + .12 * max(0, 1 - w.z / 3.2)
        f = math.sin(ang * 5 + w.z * .58) * amp + .035 * math.sin(ang * 9 - w.z * .36)
        v.co += radial * f


def box_uv(mesh, tile=1.2):
    while mesh.uv_layers:   # curves bring their own UV layers; keep exactly one, shared with the leaves
        mesh.uv_layers.remove(mesh.uv_layers[0])
    uv = mesh.uv_layers.new(name='UVMap')
    for p in mesh.polygons:
        n = p.normal
        ax = max(range(3), key=lambda k: abs(n[k]))
        for li in p.loop_indices:
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            u, v = ((co.y, co.z), (co.x, co.z), (co.x, co.y))[ax]
            uv.data[li].uv = (u / tile, v / tile)


def canopy(cluster_loc, scale, index, rng, spec, lod):
    """One cluster of cupped leaves along curling sprays (build_life_tree.py add_solid_canopy_geometry)."""
    verts, faces, tones, norms = [], [], [], []
    count = int(spec['leaves_per_cluster'] * lod['keep'])
    twist = index * .83
    sx, sy, sz = scale
    mean = (sx + sy + sz) / 3
    for i in range(count):
        z = 1 - 2 * (i + .5) / count
        az = i * 2.3999632297 + index * .73
        rad = math.sqrt(max(0, 1 - z * z))
        direction = Vector((rad * math.cos(az), rad * math.sin(az), z))
        spray = i % 11
        t = rng.random()
        heading = spray * 2.399963 + .55 * math.sin(index)
        curl = heading + t * (1.15 + .35 * math.sin(spray))
        reach = .16 + .80 * t
        scatter = .075 + .08 * math.sin(math.pi * t)
        local = Vector((math.cos(curl) * reach + direction.x * scatter, math.sin(curl) * reach + direction.y * scatter,
                        .34 * math.sin(t * math.pi + spray * .65) + .20 * math.cos(heading) + direction.z * scatter))
        local = Vector((local.x * math.cos(twist) - local.y * math.sin(twist), local.x * math.sin(twist) + local.y * math.cos(twist), local.z))
        centre = cluster_loc + Vector((local.x * sx, local.y * sy, local.z * sz))
        normal = (direction * .5 + Vector((0, 0, .68))).normalized()
        q = normal.to_track_quat('Z', 'Y')
        spin = rng.uniform(-math.pi, math.pi)
        length = rng.uniform(*spec['leaf_size']) * mean * lod['grow']
        width = length * rng.uniform(.43, .64) * spec.get('leaf_width', 1.0)
        hang = spec.get('hang', 0)
        if hang:   # willow: leaves trail down from the spray in long curtains, the outer ones furthest
            q = Vector((rng.uniform(-.3, .3), rng.uniform(-.3, .3), -1)).normalized().to_track_quat('Y', 'Z')
            centre = centre - Vector((0, 0, hang * mean * rng.random() ** .6 * (.4 + .6 * min(1, (centre - cluster_loc).xy.length / max(sx, 1e-3)))))
        if spec.get('sparse'):
            if rng.random() > spec['sparse']:
                continue
        shape = ((0, -length, 0), (width, 0, -.005 * mean), (0, length, .008 * mean), (-width, 0, -.005 * mean), (0, 0, .011 * mean))
        base = len(verts)
        for x, y, h in shape:
            sp = Vector((x * math.cos(spin) - y * math.sin(spin), x * math.sin(spin) + y * math.cos(spin), h))
            verts.append(centre + q @ sp)
            norms.append(normal)
        for k in range(4):
            faces.append((base + 4, base + k, base + (k + 1) % 4))
        exposure = max(0, min(1, (local.z + .54) / 1.08))
        tones.append(max(0, min(.999, exposure + rng.uniform(-.03, .03))))
    return verts, faces, tones, norms


# ------------------------------------------------------------------ materials
def palette_image(name, stops):
    img = bpy.data.images.new(name, SWATCHES, 4, alpha=False)
    px = []
    cols = [lin(c) for c in stops]
    for _ in range(4):
        for sidx in range(SWATCHES):
            t = (sidx + .5) / SWATCHES * (len(cols) - 1)
            lo = min(int(t), len(cols) - 2)
            f = t - lo
            c = [cols[lo][k] * (1 - f) + cols[lo + 1][k] * f for k in range(3)]
            px += [(x * 12.92) if x <= .0031308 else (1.055 * x ** (1 / 2.4) - .055) for x in c] + [1]
    img.pixels = px
    img.filepath_raw = str(OUT / f'{name}.png')
    img.file_format = 'PNG'
    img.save()
    return img


def material(name, img, closest=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    tex = m.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = img
    if closest:
        tex.interpolation = 'Closest'
    m.node_tree.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = .85
    return m


# ------------------------------------------------------------------ build
def build(spec, variant=0):
    if 'skeleton' in spec:
        name, wood, bark_mat, leaf_mat, clusters = build_traced_form(spec, variant)
        n = max(len(clusters), 1)
        spec = dict(spec, leaves_per_cluster=max(150, spec.get('leaves_total', 30000) // n))
        return finish(spec, name + ('', '_B', '_C')[variant], wood, bark_mat, leaf_mat, clusters)
    if 'scale' in spec:
        name, wood, bark_mat, leaf_mat, clusters = build_elder_form(spec, variant)
        return finish(spec, name + ('', '_B', '_C')[variant], wood, bark_mat, leaf_mat, clusters)
    name = 'Elder' + spec['name']
    rng = random.Random(20261031)
    bark_src = bpy.data.images.load(str(REFS / f"bark-{spec['bark']}.png"))
    bark_src.scale(1024, 1024)
    bark_src.filepath_raw = str(OUT / f'{name}_Bark.png')
    bark_src.file_format = 'PNG'
    bark_src.save()
    bark_mat = material(f'{name}_Bark', bark_src)
    leaf_mat = material(f'{name}_Leaves', palette_image(f'{name}_Leaves', spec['palette']), closest=True)

    # Trunk with the root collar fused into one fluted surface.
    trunk = to_mesh(curve('trunk', spec['trunk'], spec['trunk_radii']))
    flute(trunk.data, spec['trunk'])
    roots = []
    for mid, end, r in spec['roots']:
        roots.append(to_mesh(curve('root', [(0, 0, .55), mid, end], [r, r * .55, r * .2])))
    bpy.ops.object.select_all(action='DESELECT')
    for o in [trunk, *roots]:
        o.select_set(True)
    bpy.context.view_layer.objects.active = trunk
    bpy.ops.object.join()
    rem = trunk.modifiers.new('fuse', 'REMESH')
    rem.mode = 'VOXEL'
    rem.voxel_size = .07
    bpy.ops.object.modifier_apply(modifier=rem.name)
    sm = trunk.modifiers.new('soften', 'SMOOTH')
    sm.factor, sm.iterations = .75, 4
    bpy.ops.object.modifier_apply(modifier=sm.name)
    dec = trunk.modifiers.new('budget', 'DECIMATE')
    dec.ratio = min(1.0, 14000 / max(1, len(trunk.data.polygons)))
    bpy.ops.object.modifier_apply(modifier=dec.name)

    # Limbs, secondaries and twigs.
    branches, ends = [], []
    brng = random.Random(311)
    for i, (pts, r) in enumerate(spec['limbs'], start=1):
        # Taper from the base to a thin tip, swelling a little where the limb bends.
        radii = [max(.04, r * (1 - k / (len(pts) - 1)) ** .8 * brng.uniform(.9, 1.12)) for k in range(len(pts))]
        branches.append(curve(f'limb_{i}', pts, radii))
        if r > .3:   # the thick limbs carry foliage along their outer part too, so the dome has no hole
            ends.append(Vector(pts[-2]).lerp(Vector(pts[-1]), .4) + UP * .5)
        branch_hierarchy(i, pts, r, branches, ends, brng)
        ends.append(Vector(pts[-1]))
    ends += [Vector(p) for p in spec.get('front', [])]
    for o in branches:
        to_mesh(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in [trunk, *branches]:
        o.select_set(True)
    bpy.context.view_layer.objects.active = trunk
    bpy.ops.object.join()
    wood = trunk
    for poly in wood.data.polygons:
        poly.use_smooth = True
    box_uv(wood.data)
    wood.data.materials.clear()
    wood.data.materials.append(bark_mat)
    wood.data.materials.append(leaf_mat)

    clusters = [(e + UP * .3, Vector(spec['cluster_scale'])) for e in ends]
    return finish(spec, name, wood, bark_mat, leaf_mat, clusters)


def finish(spec, name, wood, bark_mat, leaf_mat, clusters):
    root = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(root)
    tris = []
    for li, lod in enumerate(LODS):
        w = wood.copy()
        w.data = wood.data.copy()
        bpy.context.collection.objects.link(w)
        if lod['wood'] < 1:
            d = w.modifiers.new('lod', 'DECIMATE')
            d.ratio = lod['wood']
            bpy.ops.object.select_all(action='DESELECT')
            w.select_set(True)
            bpy.context.view_layer.objects.active = w
            bpy.ops.object.modifier_apply(modifier=d.name)
        # Crown: a cluster at every limb and secondary end, so the crown follows the authored branches.
        verts, faces, tones, norms = [], [], [], []
        crng = random.Random(77 + li)
        for idx, (c, sc) in enumerate(clusters):
            v, f, t, n = canopy(c, tuple(sc), idx, crng, spec, lod)
            base = len(verts)
            verts += v
            faces += [tuple(base + k for k in face) for face in f]
            tones += t
            norms += n
        lm = bpy.data.meshes.new('leaves')
        lm.from_pydata(verts, [], faces)
        uv = lm.uv_layers.new(name='UVMap')
        for p in lm.polygons:
            p.material_index = 1
            u = (min(int(tones[p.index // 4] * SWATCHES), SWATCHES - 1) + .5) / SWATCHES
            for idx in p.loop_indices:
                uv.data[idx].uv = (u, .5)
        lm.normals_split_custom_set([norms[lm.loops[i].vertex_index] for i in range(len(lm.loops))])
        lo = bpy.data.objects.new('leaves', lm)
        bpy.context.collection.objects.link(lo)
        lm.materials.append(bark_mat)
        lm.materials.append(leaf_mat)
        bpy.ops.object.select_all(action='DESELECT')
        lo.select_set(True)
        w.select_set(True)
        bpy.context.view_layer.objects.active = w
        bpy.ops.object.join()
        w.name = w.data.name = f'{name}_LOD{li}'
        w.parent = root
        tris.append(sum(len(p.vertices) - 2 for p in w.data.polygons))
    bpy.data.objects.remove(wood, do_unlink=True)
    bpy.ops.object.select_all(action='DESELECT')
    root.select_set(True)
    for c in root.children:
        c.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT / f'{name}.fbx'), use_selection=True, object_types={'MESH', 'EMPTY'},
                             axis_forward='-Z', axis_up='Y', apply_scale_options='FBX_SCALE_ALL', bake_space_transform=True,
                             mesh_smooth_type='OFF', path_mode='RELATIVE', add_leaf_bones=False, bake_anim=False)
    lod0 = next(c for c in root.children if c.name.endswith('LOD0'))
    zs = [v.co.z for v in lod0.data.vertices]
    xs = [v.co.x for v in lod0.data.vertices]
    stale = OUT / f'{name}_Foliage.png'   # the card version's atlas would override the palette in Unity
    if stale.exists():
        stale.unlink()
    return root, {'triangles_per_lod': tris, 'size_m': [round(max(xs) - min(xs), 2), 0, round(max(zs), 2)], 'leaf': 'authored'}


def render(roots_):
    scene = bpy.context.scene
    for e in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
        try:
            scene.render.engine = e
            break
        except TypeError:
            pass
    scene.render.resolution_x, scene.render.resolution_y = 1400, 1050
    world = bpy.data.worlds.new('w')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.78, .8, .82, 1)
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(50), 0, math.radians(-25))
    sun.data.energy = 3.8
    bpy.ops.mesh.primitive_plane_add(size=60)
    g = bpy.context.active_object
    gm = bpy.data.materials.new('soil')
    gm.use_nodes = True
    next(n for n in gm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = (.22, .3, .12, 1)
    g.data.materials.append(gm)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.lens = 35
    for r in roots_:
        for c in r.children:
            c.hide_render = True
    for r in roots_:
        for c in r.children:
            c.hide_render = not c.name.endswith('LOD0')
        for k, (az, tag) in enumerate(((-.35, 'front'), (1.2, 'side'))):
            cam.location = Vector((math.sin(az) * 22, -math.cos(az) * 22, 5.2))
            cam.rotation_euler = (Vector((0, 0, 6.2)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
            scene.render.filepath = str(PREVIEW / f'{r.name}-{tag}.png')
            bpy.ops.render.render(write_still=True)
        for c in r.children:
            c.hide_render = True


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    PREVIEW.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    report_path = OUT / 'species-report.json'
    report = json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else {}
    roots_ = []
    for spec in SPECIES:
        for variant in range(3 if ('scale' in spec or 'skeleton' in spec) else 1):
            r, info = build(spec, variant)
            roots_.append(r)
            report[r.name] = info
    render(roots_)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('AUTHORED_TREES ' + json.dumps({r.name: report[r.name]['size_m'] for r in roots_}))


main()
