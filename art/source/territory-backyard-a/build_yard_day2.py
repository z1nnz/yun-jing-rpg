"""第 2 天的院子 (A, work package 2026-11-01/03-half-load-revision.md). Run in a background Blender 5.2:

  blender -b --python-exit-code 1 --python build_yard_day2.py [-- TY01 TY02 TY07]
  blender -b --python-exit-code 1 --python build_yard_day2.py -- --sheets

Each asset: procedural parts modelled from its selected AI sheet (art/references/territory-backyard-a/<id>/selected.png, made with
the art style guide's prompt), baked to one atlas, LOD0 / LOD1 (~50 %) / LOD2 (~15 %) in the same GLB and FBX, simple _Collision
meshes for what blocks the player, <file>_model_info.json. Original procedural modelling only; no third-party meshes.

Materials follow docs/execution/art-style-guide-v1.md: large soft gradients and a few strokes (no fine noise), warm where light
lands and blue-violet in the cavities, warm grey stone, aged brown timber, jade greens.
"""
import sys
import json
import math
import os
import random
import time
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector, noise

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import kitlib as Q  # noqa: E402

REF = ROOT.parents[2] / 'art/references/territory-backyard-a'
EXPORT, PREV = Q.EXPORTS, Q.PREVIEWS
ARGV = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
TAU = math.tau

# TY01 field bed (TY_Field slot 2.6 x 3.4 x 0.5)
HX, HY = 1.25, 1.65          # outer half-size of the ridge at the base (the foot stones bulge ~4 cm past it)
RIDGE = 0.27                 # earth ridge top; stones sit on it
SOIL = 0.14                  # furrow bottom
ROW_X = (-0.66, 0.0, 0.66)
PLANT_Y = (-1.02, -0.34, 0.34, 1.02)
INLET_Y = 0.6
STAGE_T = (0.0, 0.25, 0.6, 1.0)


def lin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


COOL = (0.040, 0.044, 0.085)      # shadows lean blue-violet, never black


def painted(name, shade, mid, light, scale=2.0, rough=0.85, strokes=(1, 1, 5), bump=0.0015, cool=0.65, warm=0.45, grain=0.0):
    """Hand-painted look: a large soft gradient, a few long strokes, light baked warm on what faces up and on worn edges, cool in the cavities."""
    m, nt, b = Q.new_mat(name)
    co = Q.coords(nt, (1, 1, 1))
    big = Q.noise(nt, co, scale, 2, 0.45)
    stroke = Q.noise(nt, Q.coords(nt, strokes), scale * 2.4, 2, 0.4)
    col = Q.mix(nt, Q.smooth(nt, big, 0.32, 0.5), shade, mid)
    col = Q.mix(nt, Q.smooth(nt, big, 0.5, 0.7), col, light)
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', Q.smooth(nt, stroke, 0.56, 0.66), 0.28), col, light)
    height = Q.math_(nt, 'ADD', stroke, big)
    if grain:                                            # long cracks and grain along the length (local Z)
        lines = Q.smooth(nt, Q.noise(nt, Q.coords(nt, (16, 16, 0.7)), 1.6, 3, 0.55), 0.56, 0.42)
        col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', lines, grain), col, COOL)
        height = Q.math_(nt, 'SUBTRACT', height, Q.math_(nt, 'MULTIPLY', lines, 1.2))
    nz = Q.sep(nt, Q.N(nt, 'ShaderNodeNewGeometry').outputs['Normal'])[2]
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', Q.smooth(nt, nz, 0.1, 0.9), 0.22), col, tuple(min(1.0, c * 1.25 + 0.012) for c in light))
    cav, edge = Q.edge_cavity(nt, 0.05, 0.006)
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', Q.smooth(nt, cav, 0.08, 0.55), cool), col, COOL)
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', Q.smooth(nt, edge, 0.3, 0.8), warm), col, tuple(min(1.0, c * 1.5 + 0.02) for c in light))
    return Q.finish(m, nt, b, col, rough, 0.0, height, bump, 0.7)


def moss(m, amount=0.8, up=(0.3, 0.8), cover=(0.46, 0.6)):
    """Soft yellow-green moss on what faces up, in large patches (kept in the bake channels)."""
    nt = m.node_tree
    alb = next(n for n in nt.nodes if n.type == 'REROUTE' and n.name == 'CH_albedo')
    src = alb.inputs[0].links[0].from_socket
    nz = Q.sep(nt, Q.N(nt, 'ShaderNodeNewGeometry').outputs['Normal'])[2]
    co = Q.coords(nt, (1, 1, 1))
    mask = Q.math_(nt, 'MULTIPLY', Q.smooth(nt, nz, *up), Q.smooth(nt, Q.noise(nt, co, 3.4, 3, 0.5), *cover))
    tint = Q.mix(nt, Q.noise(nt, co, 7.0, 2), lin('#3e6a2a'), lin('#8fae48'))
    Q.L(nt, Q.mix(nt, Q.math_(nt, 'MULTIPLY', mask, amount), src, tint), alb.inputs[0])
    rr = next(n for n in nt.nodes if n.type == 'REROUTE' and n.name == 'CH_rough')
    Q.L(nt, Q.mixf(nt, mask, rr.inputs[0].links[0].from_socket, 0.95), rr.inputs[0])
    return m


def m_soil(name='TilledSoil'):
    """Dark tilled soil, warm where it dries. A WETNESS value node (0 dry, 1 wet) darkens it: the bed is baked once per state."""
    m, nt, b = Q.new_mat(name)
    wet = Q.N(nt, 'ShaderNodeValue')
    wet.name = wet.label = 'WETNESS'
    wet.outputs[0].default_value = 0.0
    co = Q.coords(nt, (1, 1, 1), offset_by_seed=False)
    big = Q.noise(nt, co, 2.4, 2, 0.45)
    clod = Q.smooth(nt, Q.voronoi(nt, co, 16.0, 'F1'), 0.45, 0.05)
    rake = Q.math_(nt, 'SINE', Q.math_(nt, 'MULTIPLY', Q.sep(nt, co)[0], 70.0))
    wz = Q.attr(nt, 'qa_ridge', 'fac')       # 0 in a furrow, 1 on a row crest
    dry = Q.mix(nt, Q.smooth(nt, big, 0.32, 0.68), tuple(c * 0.2 for c in lin('#8a6a44')), tuple(c * 0.36 for c in lin('#8a6a44')))
    dry = Q.mix(nt, Q.math_(nt, 'MULTIPLY', wz, 0.45), dry, tuple(c * 0.5 for c in lin('#8a6a44')))
    dry = Q.mix(nt, Q.math_(nt, 'MULTIPLY', clod, 0.3), dry, tuple(c * 0.72 for c in lin('#8a6a44')))
    wetc = Q.mix(nt, Q.smooth(nt, big, 0.32, 0.68), (0.016, 0.012, 0.014), (0.032, 0.022, 0.018))
    wetc = Q.mix(nt, Q.math_(nt, 'MULTIPLY', clod, 0.25), wetc, (0.055, 0.038, 0.028))
    col = Q.mix(nt, wet.outputs[0], dry, wetc)
    cav, _ = Q.edge_cavity(nt, 0.06, 0.006)
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', Q.smooth(nt, cav, 0.08, 0.5), 0.55), col, COOL)
    rough = Q.mixf(nt, wet.outputs[0], 0.95, 0.62)
    hgt = Q.math_(nt, 'ADD', Q.math_(nt, 'MULTIPLY', clod, 0.9), Q.math_(nt, 'MULTIPLY', rake, 0.1))
    return Q.finish(m, nt, b, col, rough, 0.0, hgt, 0.009, 1.0)


def m_leaf(name='QinglingLeaf'):
    """Jade blade from blade(): qa_t root..tip, qa_x edge..midrib..edge, qa_glow on mature tips. Teal shade at the root, fresh
    jade body, warm yellow-green toward the tip and along the toothed edge, a pale midrib; cyan emission only where qa_glow is set."""
    m, nt, b = Q.new_mat(name)
    t = Q.attr(nt, 'qa_t', 'fac')
    x = Q.attr(nt, 'qa_x', 'fac')
    glow = Q.attr(nt, 'qa_glow', 'fac')
    sd = Q.attr(nt, 'qa_seed', 'fac')
    col = Q.mix(nt, Q.smooth(nt, t, 0.0, 0.4), lin('#1d4a46'), lin('#4a8650'))
    col = Q.mix(nt, Q.smooth(nt, t, 0.45, 1.0), col, lin('#8fb868'))
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', sd, 0.3), col, lin('#6fa443'))
    edge = Q.smooth(nt, Q.math_(nt, 'ABSOLUTE', x), 0.62, 1.0)
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', edge, 0.6), col, lin('#b8d468'))
    rib = Q.math_(nt, 'SUBTRACT', 1.0, Q.smooth(nt, Q.math_(nt, 'ABSOLUTE', x), 0.0, 0.14))
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', rib, 0.55), col, lin('#b8d468'))
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', glow, 0.5), col, (0.10, 0.48, 0.42))
    emit = Q.mix(nt, Q.math_(nt, 'MULTIPLY', glow, 0.7), (0, 0, 0), (0.08, 0.62, 0.52))
    m = Q.finish(m, nt, b, col, 0.7, 0.0, rib, 0.0004, 0.5, emit=emit)
    m['qa_texel'] = 1.6
    return m


def make_materials():
    g = {}
    g['SOILM'] = m_soil()
    g['RIDGEM'] = moss(painted('EarthRidge', lin('#54402c'), lin('#6e5438'), lin('#8a6a44'), scale=2.6, rough=0.95, strokes=(1, 1, 7)), 0.75, (0.45, 0.9), cover=(0.42, 0.58))
    g['STONE'] = moss(painted('FittedStone', lin('#524f49'), lin('#6e6a60'), lin('#8a8478'), scale=3.0, rough=0.88, strokes=(1, 3, 1), bump=0.002, warm=0.28), 0.8, (0.4, 0.85), cover=(0.42, 0.58))
    g['POST'] = moss(painted('OldTimber', lin('#3a2c22'), lin('#54402f'), lin('#7c6248'), scale=3.0, rough=0.85, strokes=(9, 9, 1), bump=0.006, warm=0.3, grain=0.32, cool=0.45), 0.45, (0.55, 0.95), cover=(0.5, 0.64))
    g['BAMBOO'] = painted('OldBamboo', lin('#6e6638'), lin('#8e8548'), lin('#b8ab68'), scale=2.2, rough=0.62, strokes=(6, 6, 1), bump=0.0006)
    g['WICKER'] = painted('Wicker', lin('#5e4a2c'), lin('#7a6238'), lin('#a88e58'), scale=3.0, rough=0.8, strokes=(1, 1, 1), bump=0.001)
    g['ROPE'] = Q.m_cord('OldHemp', lin('#8a7448'), lin('#a88e58'))
    g['NEWROPE'] = Q.m_cord('NewHemp', lin('#b8a468'), lin('#d8c890'))
    g['HANDLE'] = painted('TrowelHandle', lin('#5a3a24'), lin('#6a4630'), lin('#a87a50'), scale=4.0, rough=0.6, strokes=(1, 1, 8))
    g['IRON'] = painted('TrowelBlade', lin('#44464a'), lin('#5e5e5e'), lin('#8a8478'), scale=5.0, rough=0.55)
    g['LEAF'] = m_leaf()
    g['COLLAR'] = painted('RootSoil', lin('#4e3a28'), lin('#6e5236'), lin('#8a6a44'), scale=8.0, rough=0.95)
    globals().update(g)


# ====================================================================== helpers
def smoothstep(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def boulder(name, radii, loc, mat, seed=1, subd=2, rough=0.2, rot=0.0, squash_top=0.0, ground=0.0, tilt=(0.0, 0.0)):
    """Rounded stone with a few soft cuts; anything below `ground` is flattened onto it."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subd, radius=1.0)
    off = Vector((seed * 1.37, seed * 2.11, seed * 0.73))
    rmat = Matrix.Rotation(tilt[0], 3, 'X') @ Matrix.Rotation(tilt[1], 3, 'Y')
    for v in bm.verts:
        d = v.co.normalized()
        k = 1 + rough * noise.fractal(d * 1.3 + off, 0.5, 2.0, 3)
        p = Vector((d.x * radii[0] * k, d.y * radii[1] * k, d.z * radii[2] * k))
        if squash_top and p.z > 0:
            p.z *= 1 - squash_top
        for ci in range(2):
            nrm = Vector((math.sin(seed * 3.1 + ci * 2.4), math.cos(seed * 1.7 + ci * 1.3), 0.6 * math.sin(seed + ci))).normalized()
            lim = 0.82 * (radii[0] * abs(nrm.x) + radii[1] * abs(nrm.y) + radii[2] * abs(nrm.z))
            dd = p.dot(nrm)
            if dd > lim:
                p -= nrm * (dd - lim) * 0.75
        p = rmat @ p
        c, s = math.cos(rot), math.sin(rot)
        p = Vector((p.x * c - p.y * s, p.x * s + p.y * c, p.z))
        p.z = max(p.z, ground - loc[2])
        v.co = p
    o = Q._obj(name, bm, mat, sharp=70)
    o.location = loc
    return o


def ring_point(th, hx, hy, n=7.0):
    c, s = math.cos(th), math.sin(th)
    x = hx * math.copysign(abs(c) ** (2 / n), c)
    y = hy * math.copysign(abs(s) ** (2 / n), s)
    nx = abs(x / hx) ** (n - 1) * math.copysign(1, x) / hx
    ny = abs(y / hy) ** (n - 1) * math.copysign(1, y) / hy
    nl = math.hypot(nx, ny) or 1.0
    return x, y, nx / nl, ny / nl


def even_angles(hx, hy, count, n=7.0):
    fine = [TAU * i / 2400 for i in range(2401)]
    pts = [ring_point(a, hx, hy, n)[:2] for a in fine]
    acc = [0.0]
    for p0, p1 in zip(pts, pts[1:]):
        acc.append(acc[-1] + math.dist(p0, p1))
    out, j = [], 0
    for k in range(count):
        target = acc[-1] * k / count
        while acc[j + 1] < target:
            j += 1
        out.append(fine[j])
    return out


def set_vattr(o, name, fn):
    me = o.data
    at = me.attributes.get(name) or me.attributes.new(name, 'FLOAT', 'POINT')
    at.data.foreach_set('value', [fn(v.co) for v in me.vertices])


FOOT = [(-0.33, -0.95, 0.5), (-0.33, -0.32, -0.4), (0.33, 0.28, 0.3), (0.33, 0.95, -0.3)]    # footprints in the furrows


def soil_h(x, y):
    """Bed soil height (field-local): furrows, three flat-topped rows tapering at their ends, rising to meet the ridge, two footsteps."""
    h = SOIL
    taper = 1.0 - smoothstep(1.2, 1.42, abs(y))
    h += 0.085 * max(math.exp(-((x - c) / 0.21) ** 4) for c in ROW_X) * taper
    h += 0.05 * smoothstep(HX - 0.42, HX - 0.27, abs(x)) + 0.05 * smoothstep(HY - 0.42, HY - 0.27, abs(y))
    h += 0.012 * noise.fractal(Vector((x * 7.0, y * 7.0, 0.3)), 0.5, 2.0, 2)
    for fx, fy, a in FOOT:
        dx, dy = (x - fx) * math.cos(a) + (y - fy) * math.sin(a), -(x - fx) * math.sin(a) + (y - fy) * math.cos(a)
        h -= 0.022 * (1 - smoothstep(0.75, 1.0, math.hypot(dx / 0.055, dy / 0.13)))
    return h


# ====================================================================== TY01 field bed
def build_TY01():
    rnd = random.Random(101)
    prof = [(0.0, 0.0), (0.05, 0.1), (0.1, 0.21), (0.15, RIDGE - 0.01), (0.2, RIDGE), (0.25, RIDGE - 0.02), (0.28, 0.17), (0.3, 0.09)]
    ns = 200
    bm = bmesh.new()
    rings = []
    for i in range(ns):
        th = TAU * i / ns
        row = []
        for k, (d, z) in enumerate(prof):
            x, y, nx, ny = ring_point(th, HX - d, HY - d)
            wob = 0.018 * noise.noise(Vector((x * 3.1, y * 3.1, k * 0.7))) if 0 < k < len(prof) - 1 else 0.0
            dip = 0.1 if x > HX - 0.5 and abs(y - INLET_Y) < 0.14 and 2 <= k <= 5 else 0.0     # the notch of the inlet
            row.append(bm.verts.new((x + nx * wob, y + ny * wob, z - dip)))
        rings.append(row)
    for i in range(ns):
        A, B = rings[i], rings[(i + 1) % ns]
        for k in range(len(prof) - 1):
            bm.faces.new((A[k], B[k], B[k + 1], A[k + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    Q._obj('TY01_Ridge', bm, RIDGEM, sharp=55)

    nx_, ny_ = 76, 104
    hx, hy = HX - 0.27, HY - 0.27
    bm = bmesh.new()
    grid = [[bm.verts.new((-hx + 2 * hx * i / nx_, -hy + 2 * hy * j / ny_, 0.0)) for i in range(nx_ + 1)] for j in range(ny_ + 1)]
    for row in grid:
        for v in row:
            v.co.z = soil_h(v.co.x, v.co.y)
    for j in range(ny_):
        for i in range(nx_):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    soil = Q._obj('TY01_Soil', bm, SOILM, sharp=80)
    set_vattr(soil, 'qa_ridge', lambda co: smoothstep(SOIL + 0.02, SOIL + 0.08, co.z))

    # fitted stones: close-set rounded cap stones on the crown, big half-buried ones along the foot
    for course, (inset, z, count, rad) in enumerate(((0.2, RIDGE - 0.012, 62, (0.105, 0.08, 0.05)), (0.05, 0.075, 46, (0.135, 0.075, 0.095)))):
        for k, th in enumerate(even_angles(HX - inset, HY - inset, count)):
            x, y, nx, ny = ring_point(th, HX - inset, HY - inset)
            if x > 0.8 and abs(y - INLET_Y) < 0.17:
                continue
            s = rnd.choice((0.78, 0.9, 1.0, 1.0, 1.12, 1.25))
            r = (rad[0] * s, rad[1] * rnd.uniform(0.9, 1.15), rad[2] * rnd.uniform(0.85, 1.1))
            boulder(f'TY01_Stone_{course}_{k}', r, (x, y, z), STONE, seed=course * 100 + k + 3, subd=2, rough=0.22,
                    rot=math.atan2(ny, nx) + math.pi / 2 + rnd.uniform(-0.2, 0.2), squash_top=0.3 if course == 0 else 0.0,
                    tilt=(0.0, 0.0) if course == 0 else (0.3 * ny, -0.3 * nx))

    # the inlet: two squared stones flanking the notch, a flat sill stone
    for s in (-1, 1):
        Q.box(f'TY01_InletJamb_{s}', (0.3, 0.1, 0.24), (HX - 0.14, INLET_Y + s * 0.18, 0.12), STONE, bevel=0.022, bseg=3)
    Q.box('TY01_InletSill', (0.34, 0.26, 0.06), (HX - 0.14, INLET_Y, 0.1), STONE, bevel=0.012, bseg=2)
    SOCKETS.append(dict(name='SOCKET_inlet', loc=[round(HX - 0.02, 4), INLET_Y, 0.14], forward=[-1.0, 0.0, 0.0]))

    # corner stakes with a hemp lashing
    for k, (sx, sy) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        x, y = sx * (HX - 0.1), sy * (HY - 0.1)
        h = rnd.uniform(0.44, 0.49)
        prof_ = [(0, 0), (0.05, 0.0), (0.048, h * 0.5), (0.045, h - 0.02), (0.03, h), (0, h - 0.006)]
        st = Q.lathe(f'TY01_Stake_{k}', prof_, POST, segs=10, sharp=50)
        st.location = (x, y, 0)
        st.rotation_euler = (rnd.uniform(-0.05, 0.05), rnd.uniform(-0.05, 0.05), rnd.uniform(0, 3))
        for w in range(3):
            Q.torus(f'TY01_Lash_{k}_{w}', 0.055, 0.011, (x, y, 0.25 + w * 0.024), ROPE, major=18, minor=6, rot=(rnd.uniform(-0.1, 0.1), rnd.uniform(-0.1, 0.1), 0))

    # a dropped hand trowel on the near furrow
    tx, ty = 0.33, -0.72
    z0 = soil_h(tx, ty) + 0.012
    Q.rod('TY01_TrowelHandle', (tx - 0.04, ty - 0.13, z0 + 0.03), (tx + 0.01, ty, z0 + 0.012), 0.012, HANDLE, segs=8, bevel=0.004)
    Q.box('TY01_TrowelBlade', (0.06, 0.13, 0.006), (tx + 0.035, ty + 0.07, z0 + 0.006), IRON, bevel=0.002, bseg=1, rot=(0, 0, -0.38))


# ====================================================================== TY02 qingling grass, four stages
def blade(bm, lay, base, yaw, length, width, lean, arch, twist, segs, glow_from=None, teeth=0.0):
    """One slender leaf with a toothed edge: a folded strip (edge, midrib, edge) bending outward and down."""
    d = Vector((math.cos(yaw), math.sin(yaw), 0.0))
    side = Vector((-d.y, d.x, 0.0))
    pts, p = [], Vector(base)
    step = length / segs
    for i in range(segs + 1):
        t = i / segs
        ang = lean + arch * t ** 1.6
        if i:
            p = p + (Vector((0, 0, math.cos(ang))) + d * math.sin(ang)) * step
        pts.append((t, p.copy(), ang))
    rows = []
    for i, (t, p, ang) in enumerate(pts):
        w = width * min(1.0, 0.35 + t * 3.0) * (1.0 - t ** 2.0) + 0.0008
        if teeth and 0 < i < segs:
            w *= 1 + (teeth if i % 2 else -teeth * 0.6)
        tw = twist * t
        sv = side * math.cos(tw) + Vector((0, 0, 1)) * math.sin(tw) * 0.3
        up = (Vector((0, 0, math.cos(ang))) + d * math.sin(ang)).cross(sv).normalized()
        fold = up * (w * 0.4)
        row = []
        for xs, off in ((-1.0, -sv * w + fold), (0.0, Vector()), (1.0, sv * w + fold)):
            v = bm.verts.new(p + off)
            v[lay['t']] = t
            v[lay['x']] = xs
            v[lay['g']] = smoothstep(glow_from, 1.0, t) if glow_from is not None else 0.0
            row.append(v)
        rows.append(row)
    for a, b in zip(rows, rows[1:]):
        bm.faces.new((a[0], b[0], b[1], a[1]))
        bm.faces.new((a[1], b[1], b[2], a[2]))


STAGES = {
    1: dict(n=4, L=(0.15, 0.22), w=0.022, lean=(0.12, 0.45), arch=(0.25, 0.6), H=0.2, segs=6, teeth=0.0),
    2: dict(n=9, L=(0.26, 0.38), w=0.027, lean=(0.15, 0.62), arch=(0.3, 0.85), H=0.35, segs=14, teeth=0.3),
    3: dict(n=16, L=(0.38, 0.56), w=0.033, lean=(0.08, 0.72), arch=(0.45, 1.25), H=0.5, segs=20, teeth=0.34),
    4: dict(n=20, L=(0.46, 0.68), w=0.036, lean=(0.06, 0.72), arch=(0.45, 1.3), H=0.6, segs=20, teeth=0.34),
}
FORMS = ('upright', 'leaning', 'spreading')


def clump(name, stage, form, base, seed):
    rnd = random.Random(seed)
    S = STAGES[stage]
    bm = bmesh.new()
    lay = {'t': bm.verts.layers.float.new('qa_t'), 'x': bm.verts.layers.float.new('qa_x'), 'g': bm.verts.layers.float.new('qa_glow')}
    drift = rnd.uniform(0, TAU)
    for i in range(S['n']):
        yaw = TAU * i * 0.382 + rnd.uniform(-0.3, 0.3)
        k = i / max(1, S['n'] - 1)                           # the inner leaves stand tall, the outer ones arch away
        lean = S['lean'][0] + (S['lean'][1] - S['lean'][0]) * k + rnd.uniform(-0.05, 0.05)
        arch = S['arch'][0] + (S['arch'][1] - S['arch'][0]) * k + rnd.uniform(-0.1, 0.1)
        if form == 'upright':
            lean *= 0.65
            arch *= 0.75
        elif form == 'leaning':
            yaw = drift + (yaw - drift) * 0.6
            lean += 0.12
        else:
            lean = lean * 1.2 + 0.08
            arch *= 1.15
        L = (S['L'][1] - (S['L'][1] - S['L'][0]) * k) * rnd.uniform(0.92, 1.06)
        off = Vector((math.cos(yaw), math.sin(yaw), 0)) * rnd.uniform(0.0, 0.012 + 0.006 * stage)
        blade(bm, lay, Vector(base) + off, yaw, L, S['w'] * rnd.uniform(0.85, 1.12), lean, arch, rnd.uniform(-0.5, 0.5), S['segs'],
              glow_from=0.78 if stage == 4 else None, teeth=S['teeth'])
    o = Q._obj(name, bm, LEAF, sharp=89)
    zmax = max(v.co.z for v in o.data.vertices) - base[2]
    if zmax > S['H']:
        k = S['H'] / zmax
        for v in o.data.vertices:
            v.co.z = base[2] + (v.co.z - base[2]) * k
    o['qa_node'] = f'S{stage}'
    col = Q.cyl(f'{name}_Collar', 0.05 + 0.014 * stage, 0.025, (base[0], base[1], base[2] + 0.006), COLLAR, segs=12, r2=0.015 + 0.006 * stage)
    Q.jitter(col, 0.004, seed=seed)
    col['qa_node'] = f'S{stage}'
    for p in range(1 + stage // 2):
        a = rnd.uniform(0, TAU)
        ps = boulder(f'{name}_Pebble_{p}', (0.018, 0.014, 0.012), (base[0] + 0.05 * (1 + stage * 0.2) * math.cos(a), base[1] + 0.05 * (1 + stage * 0.2) * math.sin(a), base[2] + 0.008),
                     STONE, seed=seed + p, subd=1, rough=0.2, ground=base[2])
        ps['qa_node'] = f'S{stage}'
    return o


def build_TY02():
    rnd = random.Random(202)
    spots = [(x + rnd.uniform(-0.04, 0.04), y + rnd.uniform(-0.05, 0.05)) for x in ROW_X for y in PLANT_Y]
    forms = [FORMS[(i * 7 + 1) % 3] for i in range(len(spots))]
    for stage in (1, 2, 3, 4):
        for i, ((x, y), form) in enumerate(zip(spots, forms)):
            clump(f'TY02_S{stage}_{i:02d}', stage, form, (x, y, soil_h(x, y) - 0.012), seed=stage * 100 + i)
        shift_module(f'S{stage}', 2.8 * (stage - 1))


# ====================================================================== TY07 gate (between two posts; two leaves)
POST_X = 1.37
OPENING = 1.25                      # half the clear opening: leaves hinge at +-OPENING
LEAF_W = OPENING - 0.015            # a hair of gap at the middle
LEAF_BOTTOM, LEAF_TOP = 0.1, 2.08


def log_post(name, x, seed, height=2.4):
    rnd = random.Random(seed)
    prof = [(0, 0), (0.135, 0.0), (0.128, 0.5), (0.122, 1.4), (0.116, height - 0.12), (0.095, height - 0.03), (0.05, height), (0, height - 0.012)]
    o = Q.lathe(name, prof, POST, segs=18, sharp=60)
    for v in o.data.vertices:                                # bark bulges and a broken, uneven top
        a = math.atan2(v.co.y, v.co.x)
        k = 1 + 0.07 * noise.noise(Vector((math.cos(a) * 2, math.sin(a) * 2, v.co.z * 2.5 + seed)))
        v.co.x *= k
        v.co.y *= k
        if v.co.z > height - 0.15:
            v.co.z += 0.05 * noise.noise(Vector((math.cos(a) * 3, math.sin(a) * 3, seed)))
    o.location = (x, rnd.uniform(-0.005, 0.005), 0)
    for k_, z in enumerate((0.62, 1.86)):
        for w in range(4):
            Q.torus(f'{name}_Wrap_{k_}_{w}', 0.135, 0.016, (x, 0, z + w * 0.03), ROPE, major=20, minor=6, rot=(rnd.uniform(-0.05, 0.05), rnd.uniform(-0.05, 0.05), 0))
    return o


def build_leaf(tag, sign, sag):
    """A leaf hinged at x = sign * OPENING, closing toward the middle. sag: how far the free end has dropped."""
    def P(u, z, y=0.0):                                      # u: distance from the hinge; the free end droops
        return Vector((sign * (OPENING - u), y, z - sag * (u / LEAF_W)))

    def top(u):                                              # the top rail dips toward the middle
        return LEAF_TOP - 0.16 * smoothstep(0.0, 1.0, u / LEAF_W)

    n = f'TY07{tag}_'
    Q.pole(n + 'HingeStile', P(0.03, LEAF_BOTTOM), P(0.03, top(0.03) + 0.02), 0.032, BAMBOO, segs=10, node_every=0.42)
    Q.pole(n + 'FreeStile', P(LEAF_W - 0.03, LEAF_BOTTOM), P(LEAF_W - 0.03, top(LEAF_W) + 0.03), 0.032, BAMBOO, segs=10, node_every=0.42)
    Q.pole(n + 'BottomRail', P(0.0, LEAF_BOTTOM + 0.04, 0.02), P(LEAF_W, LEAF_BOTTOM + 0.04, 0.02), 0.026, BAMBOO, segs=8, node_every=0.5)
    Q.pole(n + 'MidRail', P(0.0, 0.98, 0.02), P(LEAF_W, 0.98, 0.02), 0.026, BAMBOO, segs=8, node_every=0.5)
    Q.tube(n + 'TopRail', [P(u, top(u), 0.02) for u in (0.0, LEAF_W * 0.33, LEAF_W * 0.66, LEAF_W)], 0.024, BAMBOO, segs=8, res=4)
    Q.rod(n + 'Brace', P(0.06, LEAF_BOTTOM + 0.08, 0.05), P(LEAF_W - 0.08, 0.95, 0.05), 0.024, POST, segs=8, bevel=0.004)
    rnd = random.Random(70 + sign)
    # upper: vertical split-bamboo slats, uneven tops
    u = 0.1
    k = 0
    while u < LEAF_W - 0.07:
        Q.pole(f'{n}Slat_{k}', P(u, 0.98, -0.012), P(u + rnd.uniform(-0.008, 0.008), top(u) + rnd.uniform(-0.04, 0.05), -0.012), rnd.uniform(0.018, 0.023), BAMBOO, segs=7, node_every=0.4)
        u += rnd.uniform(0.04, 0.05)
        k += 1
    # lower: horizontal wicker woven over and under thin uprights
    stakes = [0.08 + i * (LEAF_W - 0.16) / 8 for i in range(9)]
    for i, us in enumerate(stakes):
        Q.rod(f'{n}Stake_{i}', P(us, LEAF_BOTTOM + 0.03), P(us, 0.98), 0.009, WICKER, segs=6)
    for row in range(29):
        z = LEAF_BOTTOM + 0.07 + row * 0.0275
        pts = [P(0.05, z, 0.0)] + [P(us, z + rnd.uniform(-0.003, 0.003), 0.017 * (1 if (i + row) % 2 else -1)) for i, us in enumerate(stakes)] + [P(LEAF_W - 0.05, z, 0.0)]
        Q.tube(f'{n}Withy_{row}', pts, 0.0105, WICKER, segs=6, res=3)
    # rope ties where rails cross the stiles
    for z in (LEAF_BOTTOM + 0.04, 0.98):
        for us in (0.03, LEAF_W - 0.03):
            Q.torus(f'{n}Tie_{z:.2f}_{us:.2f}', 0.036, 0.0065, P(us, z, 0.01), ROPE, major=12, minor=5, rot=(math.pi / 2 * 0.9, 0, 0))
    Q.tag_node([o for o in Q.ACTIVE['coll'].objects if o.name.startswith(n)], tag)


def build_TY07():
    rnd = random.Random(77)
    log_post('TY07F_PostL', -POST_X, 3)
    log_post('TY07F_PostR', POST_X, 8)
    for s in (-1, 1):                                       # stones stacked at the post feet: a ring on the ground, a smaller one above
        for k, (z, d, r_) in enumerate([(0.06, 0.2, 0.12)] * 6 + [(0.2, 0.17, 0.09)] * 4 + [(0.31, 0.16, 0.065)] * 2):
            a = TAU * k / (6 if k < 6 else 4 if k < 10 else 2) + rnd.uniform(-0.3, 0.3) + s
            x = max(-1.5 + r_, min(1.5 - r_, s * POST_X + d * math.cos(a)))
            boulder(f'TY07F_Stone_{s}_{k}', (r_ * rnd.uniform(0.9, 1.2), r_ * rnd.uniform(0.8, 1.05), r_ * rnd.uniform(0.65, 0.85)), (x, d * math.sin(a) * 1.05, z),
                    STONE, seed=k * 7 + (s > 0), subd=2, rough=0.22)
    Q.tag_node([o for o in Q.ACTIVE['coll'].objects if o.name.startswith('TY07F_')], 'Frame')
    build_leaf('LeafL', -1, 0.0)
    build_leaf('LeafR', 1, 0.045)                           # this leaf has sagged on its hinges
    # the latch bar on the left leaf, with the newer rope tie that holds the gate shut
    bar = Q.rod('TY07LeafL_Latch', (-0.42, -0.05, 1.12), (0.1, -0.05, 1.11), 0.028, POST, segs=8, bevel=0.005)
    bar['qa_node'] = 'LeafL'
    for k in range(4):
        t = Q.torus(f'TY07LeafL_NewTie_{k}', 0.05, 0.0085, (-0.05, -0.02, 1.09 + k * 0.016), NEWROPE, major=12, minor=5, rot=(0.25, 0.1, 0))
        t['qa_node'] = 'LeafL'
    for tag, x in (('LeafL', -OPENING), ('LeafR', OPENING)):
        # hinges: three rope loops from the stile to the post
        for k, z in enumerate((0.35, 1.15, 1.9)):
            h = Q.torus(f'TY07{tag}_Hinge_{k}', 0.05, 0.009, (x + (-0.03 if x > 0 else 0.03), 0, z), ROPE, major=14, minor=5)
            h['qa_node'] = tag
    HINGES.update({'LeafL': -OPENING, 'LeafR': OPENING})


HINGES = {}


def gate_pivots(nodes, obj):
    """Each leaf node's origin is its hinge axis, so an engine opens it by rotating the node about the vertical."""
    for n in nodes:
        for tag, x in HINGES.items():
            if n.name == f'{obj}_{tag}_LOD0':
                n.data.transform(Matrix.Translation((-x, 0, 0)))
                n.location.x = x


def collision(name, boxes, coll, loc=(0, 0, 0)):
    """A simple box mesh that blocks the player: never rendered, not part of the visual triangle count."""
    bm = bmesh.new()
    for size, c in boxes:
        ret = bmesh.ops.create_cube(bm, size=1.0)
        for v in ret['verts']:
            v.co = Vector((v.co.x * size[0] + c[0], v.co.y * size[1] + c[1], v.co.z * size[2] + c[2]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    o.location = loc
    o.display_type = 'WIRE'
    o.hide_render = True
    return o


# ====================================================================== asset table + build
SOCKETS = []
OFFSETS = {}


def shift_module(nm, dx):
    for o in Q.ACTIVE['coll'].objects:
        if o.get('qa_node') == nm:
            o.location.x += dx
    OFFSETS[nm] = dx


ASSETS = {
    'TY01': dict(build=build_TY01, name='SpiritField', ver='v002', res=2048, states=True, slot=['TY_Field_1 (-2.8, 6.7)', 'TY_Field_2 (2.8, 6.7)'],
                 category='structure (embedded bed; ground from terrain)',
                 collide=lambda obj, game: [collision(f'{obj}_Collision', [((2.5, 3.3, RIDGE), (0, 0, RIDGE / 2))], game)],
                 note='rim 0.27 m blocks the player; plant and harvest from the side. Inlet on +X: rotate 180 deg for TY_Field_2 so both inlets face the x = 0 path'),
    'TY02': dict(build=build_TY02, name='QinglingGrass', ver='v002', res=2048, modules=True, double=True, emit=1.4, slot=['inside TY01, same origin'],
                 category='crop stages', collide=None, note='non-blocking plants; swap S1..S4 by growth t: <0.25 S1, <0.6 S2, <1 S3, >=1 S4',
                 stage_names=('sprout', 'young', 'grown', 'mature'), stage_h=[STAGES[i]['H'] for i in (1, 2, 3, 4)]),
    'TY07': dict(build=build_TY07, name='Gate', ver='v001', res=2048, modules=True, double=True, post_split=gate_pivots, slot=['the yard gate (position decided by the core team; fence postponed)'],
                 category='structure with two moving leaves',
                 collide=lambda obj, game: [
                     collision(f'{obj}_Frame_Collision', [((0.27, 0.27, 2.4), (-POST_X, 0, 1.2)), ((0.27, 0.27, 2.4), (POST_X, 0, 1.2))], game),
                     collision(f'{obj}_LeafL_Collision', [((LEAF_W, 0.08, 1.98), (LEAF_W / 2, 0, 1.09))], game, loc=(-OPENING, 0, 0)),
                     collision(f'{obj}_LeafR_Collision', [((LEAF_W, 0.08, 1.98), (-LEAF_W / 2, 0, 1.09))], game, loc=(OPENING, 0, 0))],
                 note='closed: leaves at rotation 0; open: rotate LeafL by -100 deg and LeafR by +100 deg about the vertical (their origin is the hinge), with their _Collision nodes'),
}


def glb_roundtrip(path, skip):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in before]
    mesh = [o for o in new if o.type == 'MESH' and o.name.split('.')[0] not in skip]
    tris = sum(Q.tri_count(o) for o in mesh)
    mn, mx = Q.bbox(mesh)
    mats = sorted({m.name for o in mesh for m in o.data.materials if m})
    for o in new:
        bpy.data.objects.remove(o)
    return tris, mn, mx, mats


def build_asset(aid):
    t0 = time.time()
    a = ASSETS[aid]
    stem = f"{aid}_{a['name']}_{a['ver']}"
    obj = f"SM_TY_{a['name']}"
    assert (REF / aid / 'selected.png').is_file(), f'{aid}: save and review the AI reference sheet before modelling'
    Q.reset()
    random.seed(31)
    src = Q.coll('10_Procedural_Source')
    Q.ACTIVE['coll'] = src
    make_materials()
    SOCKETS.clear()
    OFFSETS.clear()
    a['build']()
    parts = [o for o in src.objects if o.type == 'MESH' and not o.get('qa_cutter')]
    bpy.context.view_layer.update()
    Q.finalize_parts(parts, seed=sum(map(ord, aid)))
    game = Q.coll('00_Game_Export')
    Q.ACTIVE['coll'] = game
    G, _ = Q.game_mesh(obj, parts, game)
    tdir = EXPORT / 'textures'
    soil = SOILM.node_tree.nodes.get('WETNESS')
    base = f"{aid}_{a['name']}_{a['ver']}"
    imgs, alpha = Q.bake_asset(G, base + ('_Dry' if a.get('states') else ''), tdir, a['res'])
    wet = None
    if a.get('states'):                                  # the wet state: same mesh and UVs, only the bed soil changes
        soil.outputs[0].default_value = 1.0
        wet, _ = Q.bake_asset(G, base + '_Wet', tdir, a['res'])
        (tdir / f'T_{base}_Wet_Normal.png').unlink()     # identical to the dry normal map
        soil.outputs[0].default_value = 0.0
    glow_faces = None
    if 'Emissive' in imgs:                               # glowing tips get their own material slot
        at = G.data.attributes.get('qa_glow')
        vals = np.zeros(len(G.data.vertices), np.float32)
        at.data.foreach_get('value', vals)
        glow_faces = [p.index for p in G.data.polygons if max(vals[i] for i in p.vertices) > 0.05]
    base_imgs = {k: v for k, v in imgs.items() if k != 'Emissive'}
    gm = Q.game_material(f"TY_{a['name']}", base_imgs, alpha)
    gm.use_backface_culling = not a.get('double')
    G.data.materials.clear()
    G.data.materials.append(gm)
    if glow_faces:
        gg = Q.game_material(f"TY_{a['name']}_Glow", imgs, alpha, emit_strength=a.get('emit', 2.0))
        gg.use_backface_culling = False
        G.data.materials.append(gg)
        for i in glow_faces:
            G.data.polygons[i].material_index = 1
    if wet:
        Q.game_material(f"TY_{a['name']}_Wet", {**base_imgs, 'BaseColor': wet['BaseColor'], 'ORM': wet['ORM']}, alpha).use_fake_user = True
    G.name = f'{obj}_LOD0'
    nodes = Q.split_nodes(G, obj)
    if a.get('modules'):
        nodes = [n for n in nodes if len(n.data.polygons)]
        for n in nodes:
            nm = n.name[len(obj) + 1:-5]
            if OFFSETS.get(nm):
                n.data.transform(Matrix.Translation((-OFFSETS[nm], 0, 0)))
    if a.get('post_split'):
        a['post_split'](nodes, obj)
    lods = []
    for n in nodes:
        ls = Q.make_lods(n, ratios=(0.5, 0.15), gcoll=game)
        for l in ls:
            for vv in l.data.vertices:
                vv.co.z = max(vv.co.z, 0.0)
        for l, nm in zip(ls, ('LOD1', 'LOD2')):
            l.name = f"{n.name[:-5]}_{nm}"
        lods += ls
    hulls = a['collide'](obj, game) if a.get('collide') else []
    src.hide_render = True
    src.hide_viewport = True
    for l in lods:
        l.hide_render = True
    empties = []
    for sk in SOCKETS:
        e = bpy.data.objects.new(sk['name'], None)
        e.empty_display_type = 'SINGLE_ARROW'
        e.empty_display_size = 0.2
        e.location = sk['loc']
        e.rotation_euler = Vector(sk['forward']).to_track_quat('Y', 'Z').to_euler()
        game.objects.link(e)
        empties.append(e)
    bpy.context.view_layer.update()
    glb, fbx = EXPORT / f'{stem}.glb', EXPORT / f'{stem}.fbx'
    shipped = nodes + empties + hulls
    Q.export(shipped, glb, fbx, shipped + lods)
    Q.select_only(shipped + lods, nodes[0])
    bpy.ops.export_scene.gltf(filepath=str(glb), export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
                              export_image_format='WEBP', export_image_quality=88, export_materials='EXPORT', export_extras=False)
    for l in lods:
        l.hide_set(True)
    blend = ROOT / 'blend' / f'{stem}.blend'
    blend.parent.mkdir(exist_ok=True)
    for img in bpy.data.images:
        if img.filepath_raw and img.filepath_raw.startswith(str(tdir)):
            img.filepath = img.filepath_raw
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True, relative_remap=True)
    bpy.ops.file.make_paths_relative()
    bpy.ops.wm.save_mainfile(compress=True)
    mn, mx = Q.bbox(nodes)
    dims = [round(mx[i] - mn[i], 4) for i in range(3)]
    per_node = {n.name: [Q.tri_count(n)] + [Q.tri_count(l) for l in lods if l.name.rsplit('_', 1)[0] == n.name.rsplit('_', 1)[0]] for n in nodes}
    lod0 = sum(Q.tri_count(o) for o in nodes)
    hs = [Q.mesh_health(o) for o in nodes]
    health = {k: sum(h[k] for h in hs) for k in hs[0]}
    rt_tris, rmn, rmx, rmats = glb_roundtrip(glb, {o.name for o in lods} | {o.name for o in hulls})
    v = {'asset': aid, 'dimensions_m': dims, 'bbox_min': [round(x, 4) for x in mn], 'bbox_max': [round(x, 4) for x in mx], 'trianglesLOD0': lod0,
         'materials': sorted({m.name for o in nodes for m in o.data.materials if m}), 'textureResolution': a['res'], 'nodes': [o.name for o in nodes],
         'originAtBase': abs(mn[2]) < 0.003, 'meshHealth': health,
         'glbRoundTrip': {'triangles': rt_tris, 'trianglesMatch': rt_tris == lod0, 'bboxMatch': all(abs(p - q) < 0.002 for p, q in zip(rmn + rmx, mn + mx)), 'materials': rmats},
         'files': {p.name: {'bytes': p.stat().st_size, 'sha256': Q.sha(p)} for p in (glb, fbx)}, 'reference': f'art/references/territory-backyard-a/{aid}/selected.png',
         'notChecked': ['mobile performance', 'LOD screen-size thresholds']}
    info = dict(id=aid, name=a['name'], file=stem, units='metre', forward='-Y (Blender) / +Z (glTF)', origin='footprint centre, base z = 0', category=a['category'], slots=a['slot'],
                dimensions_m=dims, triangles_lod0=lod0, triangles_per_node=per_node, collision=[o.name for o in hulls], note=a['note'], sockets=list(SOCKETS),
                author='Johnnnny0823', validation=v)
    if aid == 'TY01':
        info['states'] = {'dry': f'material M_TY_{a["name"]} (T_{base}_Dry_*)', 'wet': f'BaseColor and ORM from T_{base}_Wet_*, normal shared with dry'}
        info['planting'] = dict(rows_x=list(ROW_X), plants_y=list(PLANT_Y), note='3 x 4 clumps, field-local; crop meshes share this origin')
    if a.get('stage_names'):
        info['stages'] = {f'{obj}_S{i}_LOD0': dict(stage=a['stage_names'][i - 1], t_from=STAGE_T[i - 1], t_to=(STAGE_T[i] if i < 4 else None), height_m=a['stage_h'][i - 1]) for i in (1, 2, 3, 4)}
        info['glow'] = f'mature leaf tips use M_TY_{a["name"]}_Glow (Emissive map, strength {a.get("emit", 2.0)}); every other face uses M_TY_{a["name"]}'
    if aid == 'TY07':
        info['gate'] = dict(leaves=[f'{obj}_LeafL_LOD0', f'{obj}_LeafR_LOD0'], open_degrees={'LeafL': -100, 'LeafR': 100}, note='rotate about the vertical at the node origin (the hinge)')
    (EXPORT / f'{stem}_model_info.json').write_text(json.dumps(info, indent=1, ensure_ascii=False), encoding='utf-8')
    print(f'[{stem}] lod0 {lod0} per-node {per_node} dims {dims} health {health} roundtrip {rt_tris} {time.time() - t0:.0f}s', flush=True)
    return v


# ====================================================================== review sheets (from the exported GLBs)
HDRI = Path(os.environ.get('YJ_HDRI', Path.home() / '.cache/yunjing/hdri/kloofendal_48d_partly_cloudy_puresky_2k.hdr'))
OLD_KIT = Path(os.environ.get('YJ_OLD_KIT', ROOT.parents[2].parent / 'backyard-a1/art/exports/territory-backyard-a'))     # v001 for the old vs new sheet
F1, F2, F7 = 'TY01_SpiritField_v002', 'TY02_QinglingGrass_v002', 'TY07_Gate_v001'


def scene():
    """Modelling spec section 8: EEVEE, the spec HDRI at strength 1.0, AgX Medium High Contrast."""
    Q.reset()
    s = bpy.context.scene
    assert HDRI.is_file(), f'review HDRI missing: {HDRI}'
    for eng in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
        try:
            s.render.engine = eng
            break
        except TypeError:
            continue
    w = bpy.data.worlds.new('QA_HDRI')
    s.world = w
    w.use_nodes = True
    nt = w.node_tree
    env = nt.nodes.new('ShaderNodeTexEnvironment')
    env.image = bpy.data.images.load(str(HDRI), check_existing=True)
    nt.links.new(env.outputs['Color'], nt.nodes['Background'].inputs['Color'])
    nt.nodes['Background'].inputs['Strength'].default_value = 1.0
    for attr, val in (('sun_threshold', 2.0), ('use_sun_shadow', True), ('sun_angle', math.radians(1.5))):
        if hasattr(w, attr):
            setattr(w, attr, val)
    for attr, val in (('use_shadows', True), ('use_raytracing', True), ('use_gtao', True)):
        if hasattr(s.eevee, attr):
            setattr(s.eevee, attr, val)
    s.view_settings.view_transform = 'AgX'
    s.view_settings.look = 'AgX - Medium High Contrast'
    gm = bpy.data.materials.new('QA_Ground')
    gm.use_nodes = True
    gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.20, 0.17, 0.12, 1)
    bpy.ops.mesh.primitive_plane_add(size=60)
    bpy.context.active_object.data.materials.append(gm)


def figure(loc):
    m = bpy.data.materials.get('QA_Figure') or Q.m_simple('QA_Figure', (0.30, 0.31, 0.31), (0.33, 0.34, 0.34), rough=0.8)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=0.17, radius2=0.2, depth=0.85, matrix=Matrix.Translation((0, 0, 0.425)))
    bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=0.2, radius2=0.12, depth=0.7, matrix=Matrix.Translation((0, 0, 1.2)))
    bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=0.11, matrix=Matrix.Translation((0, 0, 1.64)))
    Q.ACTIVE['coll'] = None
    o = Q._obj('QA_Figure', bm, m)
    o.location = loc
    bpy.context.view_layer.update()
    return o


def load(path, at=(0, 0, 0), keep=lambda n: True):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path if isinstance(path, Path) else EXPORT / f'{path}.glb'))
    out = []
    for o in [o for o in bpy.data.objects if o not in before]:
        if o.type != 'MESH' or '_LOD1' in o.name or '_LOD2' in o.name or 'Collision' in o.name or not keep(o.name):
            bpy.data.objects.remove(o)
            continue
        o.rotation_mode = 'XYZ'
        o.location += Vector(at)
        out.append(o)
    bpy.context.view_layer.update()
    return out


def wet(objs):
    for o in objs:
        for i, m in enumerate(o.data.materials):
            if not m:
                continue
            w = m.copy()
            for n in w.node_tree.nodes:
                if n.type == 'TEX_IMAGE' and n.image and ('BaseColor' in n.image.name or 'ORM' in n.image.name):
                    kind = 'BaseColor' if 'BaseColor' in n.image.name else 'ORM'
                    img = bpy.data.images.load(str(EXPORT / 'textures' / f'T_{F1}_Wet_{kind}.png'), check_existing=True)
                    img.colorspace_settings.name = 'sRGB' if kind == 'BaseColor' else 'Non-Color'
                    n.image = img
            o.data.materials[i] = w


def shot(path, cam_loc, target, lens=50, res=(1600, 1000), ortho=None, samples=64):
    s = bpy.context.scene
    cam = s.camera or bpy.data.objects.new('QA_Cam', bpy.data.cameras.new('QA_Cam'))
    if not s.camera:
        s.collection.objects.link(cam)
        s.camera = cam
    cam.data.type = 'ORTHO' if ortho else 'PERSP'
    if ortho:
        cam.data.ortho_scale = ortho
    cam.data.lens = lens
    cam.data.sensor_width = 36
    cam.data.clip_start = 0.01
    cam.data.clip_end = 300
    cam.location = cam_loc
    cam.rotation_euler = (Vector(target) - Vector(cam_loc)).to_track_quat('-Z', 'Y').to_euler()
    s.render.resolution_x, s.render.resolution_y = res
    s.render.resolution_percentage = 100
    s.eevee.taa_render_samples = samples
    s.render.filepath = str(path)
    s.render.image_settings.file_format = 'PNG'
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)
    print('SHOT', Path(path).parent.name, Path(path).name, flush=True)


def four_views(out, objs):
    mn, mx = Q.bbox(objs)
    fig = figure((mn[0] - 0.7, (mn[1] + mx[1]) / 2, 0))
    a, b = Q.bbox(objs + [fig])
    c = Vector([(a[i] + b[i]) / 2 for i in range(3)])
    span = max(b[0] - a[0], b[2] - a[2], b[1] - a[1]) * 1.12
    shot(out / 'ortho_front.png', (c.x, c.y - 40, c.z), c, ortho=span)
    fig.location = (fig.location.x, mn[1] - 0.6, 0)
    bpy.context.view_layer.update()
    shot(out / 'ortho_side.png', (c.x + 40, c.y, c.z), c, ortho=max(b[1] - a[1] + 1.4, b[2] - a[2]) * 1.15, res=(1200, 1000))
    fig.location = (mx[0] + 0.5, (mn[1] + mx[1]) / 2, 0)
    bpy.context.view_layer.update()
    shot(out / 'ortho_back.png', (c.x, c.y + 40, c.z), c, ortho=span)
    fig.location = (mn[0] - 0.7, (mn[1] + mx[1]) / 2, 0)
    bpy.context.view_layer.update()
    d = max(b[0] - a[0], b[1] - a[1], b[2] - a[2])
    shot(out / 'three_quarter.png', c + Vector((0.75, -1.25, 0.7)) * d * 1.05, c, lens=50)
    bpy.data.objects.remove(fig)


def arrange(groups, gap):
    x = 0.0
    for g in groups:
        mn, mx = Q.bbox(g)
        for o in g:
            o.location.x += x - mn[0]
        x += mx[0] - mn[0] + gap
        bpy.context.view_layer.update()
    mn, mx = Q.bbox([o for g in groups for o in g])
    for g in groups:
        for o in g:
            o.location.x -= (mn[0] + mx[0]) / 2
    bpy.context.view_layer.update()


def side_by_side(a, b, out):
    ia, ib = bpy.data.images.load(str(a)), bpy.data.images.load(str(b))
    pa, pb = Q._img_np(ia), Q._img_np(ib)
    h = min(pa.shape[0], pb.shape[0])
    Q._np_img(Path(out).stem, np.concatenate([pa[:h], np.ones((h, 24, 4), np.float32), pb[:h]], axis=1), 'sRGB', out)


def sheets():
    # TY01: dry state four views, wet beside dry, the inlet, old vs new
    out = PREV / 'TY01_SpiritField'
    scene()
    four_views(out, load(F1))
    shot(out / 'close_inlet_trowel.png', (2.2, -1.6, 1.1), (0.7, 0.1, 0.2), lens=50)
    scene()
    load(F1, (-1.6, 0, 0))
    wet(load(F1, (1.6, 0, 0)))
    shot(out / 'states_dry_wet.png', (0, -7.0, 4.8), (0, 0, 0.1), lens=40, res=(1800, 1000))
    # TY02: four views of the four stage meshes, stages side by side in beds, top layout, 1.7 m eye, close
    out = PREV / 'TY02_QinglingGrass'
    scene()
    stages = [load(F2, keep=lambda n, i=i: f'_S{i + 1}_' in n) for i in range(4)]
    arrange(stages, 0.5)
    four_views(out, [o for g in stages for o in g])
    scene()
    for i in range(4):
        x = (i - 1.5) * 2.85
        load(F1, (x, 0, 0))
        load(F2, (x, 0, 0), keep=lambda n, i=i: f'_S{i + 1}_' in n)
    shot(out / 'stages_side_by_side.png', (0, -12.5, 4.4), (0, 0, 0.3), lens=38, res=(2000, 900))
    scene()
    load(F1)
    load(F2, keep=lambda n: '_S4_' in n)
    shot(out / 'mature_close.png', (0.4, -2.7, 1.1), (0.2, -0.9, 0.42), lens=50)
    shot(out / 'top_layout.png', (0, 0, 20), (0, 0.0001, 0), ortho=3.8, res=(1200, 1400))
    shot(out / 'eye_1p7m_mature.png', (2.2, -2.5, 1.7), (0.0, 0.1, 0.3), lens=28, res=(1600, 900))
    # TY07: closed four views, leaves open, close-up of the tie, beside the author's #39 broken fence
    out = PREV / 'TY07_Gate'
    scene()
    four_views(out, load(F7))
    shot(out / 'close_tie_sag.png', (0.5, -2.2, 1.4), (0.0, 0, 1.05), lens=50)
    scene()
    for o in load(F7):
        if 'LeafL' in o.name:
            o.rotation_euler.z += math.radians(-100)
        elif 'LeafR' in o.name:
            o.rotation_euler.z += math.radians(100)
    figure((0.0, 0.0, 0))
    shot(out / 'open.png', (3.2, -5.2, 2.2), (0, 0, 1.1), lens=50)
    scene()
    load(F7, (-1.9, 0, 0))
    fence = ROOT.parents[2] / 'art/exports/qingxi-encounter-a/A08_BrokenBambooFence.glb'
    other = load(fence)
    mn, mx = Q.bbox(other)
    for o in other:
        o.location += Vector((2.2 - (mn[0] + mx[0]) / 2, -(mn[1] + mx[1]) / 2, -mn[2]))
    figure((0.0, -0.9, 0))
    shot(out / 'compare_39_broken_fence.png', (0.1, -7.5, 1.7), (0.1, 0, 1.0), lens=40, res=(1800, 1000))
    # old vs new (common rules 4.2): v001 from PR #56 and v002, same camera
    if OLD_KIT.is_dir():
        scene()
        load(OLD_KIT / 'TY01_SpiritField_v001.glb', keep=lambda n: not n.endswith('_Water'))
        load(OLD_KIT / 'TY02_QinglingGrass_v001.glb', keep=lambda n: '_S4_' in n)
        shot(PREV / 'TY01_SpiritField' / '_old.png', (3.4, -4.6, 2.8), (0, 0, 0.2), lens=45)
        scene()
        load(F1)
        load(F2, keep=lambda n: '_S4_' in n)
        shot(PREV / 'TY01_SpiritField' / '_new.png', (3.4, -4.6, 2.8), (0, 0, 0.2), lens=45)
        side_by_side(PREV / 'TY01_SpiritField' / '_old.png', PREV / 'TY01_SpiritField' / '_new.png', PREV / 'TY01_SpiritField' / 'compare_v001_vs_v002.png')
        for f in ('_old.png', '_new.png'):
            (PREV / 'TY01_SpiritField' / f).unlink()


if __name__ == '__main__' and '--sheets' in ARGV:
    sheets()
elif __name__ == '__main__':
    todo = [x for x in ARGV if not x.startswith('--')] or list(ASSETS)
    report = {aid: build_asset(aid) for aid in todo}
    print('DONE', json.dumps({k: [v['trianglesLOD0'], v['glbRoundTrip']['trianglesMatch'], v['glbRoundTrip']['bboxMatch']] for k, v in report.items()}), flush=True)
