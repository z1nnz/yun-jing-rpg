"""Newcomer territory backyard kit (A, 2026-10-31). Run in a background Blender 5.2:

  blender -b --python-exit-code 1 --python build_backyard.py [-- TY01 TY02 ...] [--no-render]
  blender -b --python-exit-code 1 --python build_backyard.py -- --sheets      (review sheets from the exported GLBs)

Each asset: editable procedural parts modelled from its saved AI reference sheet in art/references/territory-backyard-a/,
baked to one atlas (BaseColor, ORM, Normal, Emissive where something glows), LOD0/LOD1 (~50 %)/LOD2 (~15 %) in the same
GLB and FBX, <file>_model_info.json and review renders. Original procedural modelling only; no third-party meshes.

Coordinates: Blender metres, Z up, front -Y, origin at the footprint centre with the base at z = 0 (grounding spec).
In the scene (QingxiLodgingInterior, Unity Y up) a field's long side runs along world z.
"""
import sys
import json
import math
import random
import os
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
RENDER = '--no-render' not in ARGV

# TY01 field bed (fits the TY_Field slot 2.6 x 3.4 x 0.5)
FIELD_HX, FIELD_HY = 1.2, 1.6          # outer half-size of the bund at the base (2.4 x 3.2 m)
BUND_TOP = 0.30                        # rammed-earth bund top; fieldstones sit on it
SOIL_BASE = 0.17                       # furrow bottom inside the bed
ROW_X = (-0.62, 0.0, 0.62)             # three raised rows along the long side
PLANT_Y = (-0.96, -0.32, 0.32, 0.96)   # four clumps per row: 3 x 4 = 12 per field
WATER_Z = 0.29                         # flooded state (water lotus): ~2 cm over the row crests, ~12 cm in the furrows
STAGE_T = (0.0, 0.25, 0.6, 1.0)        # growth progress t at which each stage starts (work package section 6)


# ====================================================================== materials
def lin(hexs):
    """sRGB hex (spec palette) -> linear RGB."""
    c = [int(hexs[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def add_moss(m, amount=0.7, up=(0.35, 0.8), color=(0.035, 0.065, 0.012), cover=(0.32, 0.55)):
    """Moss on upward-facing surfaces, broken up by noise (kept in the bake channels)."""
    nt = m.node_tree
    alb = next(n for n in nt.nodes if n.type == 'REROUTE' and n.name == 'CH_albedo')
    src = alb.inputs[0].links[0].from_socket
    nz = Q.sep(nt, Q.N(nt, 'ShaderNodeNewGeometry').outputs['Normal'])[2]
    co = Q.coords(nt, (1, 1, 1))
    mask = Q.math_(nt, 'MULTIPLY', Q.smooth(nt, nz, *up), Q.smooth(nt, Q.noise(nt, co, 2.2, 6, 0.6), *cover))
    tint = Q.mix(nt, Q.noise(nt, co, 9.0, 3), color, (color[0] * 1.6, color[1] * 1.45, color[2] * 1.3))
    Q.L(nt, Q.mix(nt, Q.math_(nt, 'MULTIPLY', mask, amount), src, tint), alb.inputs[0])
    rr = next(n for n in nt.nodes if n.type == 'REROUTE' and n.name == 'CH_rough')
    Q.L(nt, Q.mixf(nt, mask, rr.inputs[0].links[0].from_socket, 0.95), rr.inputs[0])
    return m


def m_tilled(name='TilledSoil'):
    """Raked bed soil with crumbs and clods. A 'WETNESS' value node (0 dry, 1 wet) darkens it and makes it glossier:
    the field is baked once per state (dry / wet), and the flooded state is the wet bake plus the water node."""
    m, nt, b = Q.new_mat(name)
    wet = Q.N(nt, 'ShaderNodeValue')
    wet.name = wet.label = 'WETNESS'
    wet.outputs[0].default_value = 0.0
    co = Q.coords(nt, (1, 1, 1), offset_by_seed=False)
    n1, n2 = Q.noise(nt, co, 3.0, 6, 0.6), Q.noise(nt, co, 40.0, 3)
    clod = Q.smooth(nt, Q.voronoi(nt, co, 38.0, 'F1'), 0.3, 0.0)
    rake = Q.math_(nt, 'SINE', Q.math_(nt, 'MULTIPLY', Q.sep(nt, co)[0], 160.0))    # fine rake lines along the rows
    dry = Q.mix(nt, Q.smooth(nt, n1, 0.3, 0.75), (0.085, 0.055, 0.034), (0.15, 0.10, 0.062))
    dry = Q.mix(nt, Q.math_(nt, 'MULTIPLY', clod, 0.5), dry, (0.20, 0.14, 0.09))         # dry crumbs catch the light
    wetc = Q.mix(nt, Q.smooth(nt, n1, 0.3, 0.75), (0.032, 0.021, 0.014), (0.058, 0.039, 0.025))
    col = Q.mix(nt, wet.outputs[0], dry, wetc)
    peb = Q.smooth(nt, Q.voronoi(nt, Q.coords(nt, (1, 1, 1), offset_by_seed=False), 18.0, 'F1', rand=1.0), 0.09, 0.05)
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', peb, 0.7), col, (0.16, 0.16, 0.15))           # a few small stones in the soil
    rough = Q.mixf(nt, wet.outputs[0], Q.mixf(nt, n2, 0.88, 0.97), Q.mixf(nt, n2, 0.42, 0.6))
    hgt = Q.math_(nt, 'ADD', Q.math_(nt, 'MULTIPLY', clod, 0.8), Q.math_(nt, 'ADD', Q.math_(nt, 'MULTIPLY', rake, 0.12), Q.math_(nt, 'MULTIPLY', n2, 0.3)))
    return Q.finish(m, nt, b, col, rough, 0.0, hgt, 0.008, 1.0)


def m_rammed(name='RammedEarth'):
    """Bund: packed earth in thin horizontal lifts, lighter and drier than the bed soil, dark at the foot."""
    m, nt, b = Q.new_mat(name)
    co = Q.coords(nt, (1, 1, 1))
    z = Q.sep(nt, Q.world_pos(nt))[2]
    n1 = Q.noise(nt, co, 4.0, 6, 0.6)
    lifts = Q.math_(nt, 'SINE', Q.math_(nt, 'MULTIPLY', Q.math_(nt, 'ADD', z, Q.math_(nt, 'MULTIPLY', n1, 0.02)), 110.0))
    base_c = lin('#8C6A48')
    grey = (0.11, 0.095, 0.08)
    col = Q.mix(nt, Q.smooth(nt, n1, 0.3, 0.75), tuple(0.5 * c * 0.42 + 0.5 * g for c, g in zip(base_c, grey)), tuple(0.5 * c * 0.6 + 0.5 * g * 1.4 for c, g in zip(base_c, grey)))
    grit = Q.smooth(nt, Q.voronoi(nt, Q.coords(nt, (1, 1, 1)), 70.0, 'F1'), 0.12, 0.04)
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', grit, 0.5), col, (0.17, 0.16, 0.14))           # grit and small pebbles in the earth
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', Q.smooth(nt, lifts, 0.4, 0.9), 0.25), col, tuple(c * 0.75 for c in base_c))
    col = Q.mix(nt, Q.math_(nt, 'SUBTRACT', 1.0, Q.smooth(nt, z, 0.0, 0.12)), col, (0.05, 0.035, 0.024))
    cav, edge = Q.edge_cavity(nt, 0.03, 0.005)
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', Q.smooth(nt, cav, 0.1, 0.6), 0.6), col, (0.04, 0.03, 0.02))
    hgt = Q.math_(nt, 'ADD', Q.math_(nt, 'MULTIPLY', lifts, 0.25), Q.math_(nt, 'ADD', Q.math_(nt, 'MULTIPLY', Q.noise(nt, co, 30.0, 4), 0.6), Q.math_(nt, 'MULTIPLY', grit, 0.5)))
    return add_moss(Q.finish(m, nt, b, col, 0.93, 0.0, hgt, 0.005, 1.0), 0.35, (0.5, 0.9), cover=(0.45, 0.62))


def m_leaf(name='QinglingLeaf'):
    """Qingling grass blade. Vertex attributes from blade(): qa_t (0 root .. 1 tip), qa_x (-1 edge .. 0 midrib .. 1 edge),
    qa_glow (1 on mature leaf tips). Dark sheath at the root, muted green blade with a paler midrib, a faint blue-green
    cast toward the tip, a few dry flecks; emission (cyan, spec 'spirit' accent) only where qa_glow is set."""
    m, nt, b = Q.new_mat(name)
    t = Q.attr(nt, 'qa_t', 'fac')
    x = Q.attr(nt, 'qa_x', 'fac')
    glow = Q.attr(nt, 'qa_glow', 'fac')
    sd = Q.attr(nt, 'qa_seed', 'fac')
    co = Q.coords(nt, (1, 1, 1))
    col = Q.mix(nt, Q.smooth(nt, t, 0.0, 0.35), lin('#2F4A2A'), lin('#4E6B3A'))
    col = Q.mix(nt, Q.smooth(nt, t, 0.45, 1.0), col, tuple(0.9 * c for c in (0.10, 0.20, 0.16)))
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', sd, 0.35), col, lin('#6F8A4A'))                 # clump-to-clump tint
    rib = Q.math_(nt, 'SUBTRACT', 1.0, Q.smooth(nt, Q.math_(nt, 'ABSOLUTE', x), 0.0, 0.18))
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', rib, 0.45), col, (0.20, 0.26, 0.13))
    veins = Q.math_(nt, 'MULTIPLY', Q.smooth(nt, Q.math_(nt, 'SINE', Q.math_(nt, 'MULTIPLY', x, 26.0)), 0.6, 1.0), 0.12)
    col = Q.mix(nt, veins, col, (0.03, 0.05, 0.02))
    fleck = Q.math_(nt, 'MULTIPLY', Q.smooth(nt, Q.noise(nt, co, 60.0, 2), 0.68, 0.74), Q.smooth(nt, t, 0.55, 0.9))
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', fleck, 0.7), col, (0.22, 0.17, 0.08))
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', glow, 0.25), col, (0.30, 0.55, 0.50))          # glowing tips a touch paler
    emit = Q.mix(nt, Q.math_(nt, 'MULTIPLY', glow, 0.6), (0, 0, 0), lin('#7FE0D4'))
    hgt = Q.math_(nt, 'ADD', Q.math_(nt, 'MULTIPLY', rib, 0.4), veins)
    m = Q.finish(m, nt, b, col, Q.mixf(nt, rib, 0.55, 0.42), 0.0, hgt, 0.0004, 0.5, emit=emit)
    m['qa_texel'] = 1.6     # thin blades still get a readable midrib in the atlas
    return m


def water_normal_image():
    """Tileable ripple normal map: same algorithm, size and seed as group B's ww_lib.water_textures() and the
    #45 river kit, so the PNG is identical to their T_WW_Water_Normal and every kit can share one water shader."""
    img = bpy.data.images.get('T_WW_Water_Normal')
    if img:
        return img
    n = 1024
    rng = np.random.default_rng(11)
    F = np.fft.fft2(rng.standard_normal((n, n)))
    ky = np.fft.fftfreq(n) * n
    kx = np.fft.fftfreq(n) * n
    KY, KX = np.meshgrid(ky, kx, indexing='ij')
    K = np.sqrt(KX ** 2 + KY ** 2) + 1e-6
    streak = np.exp(-(KY / (0.30 * np.abs(KX) + 2.0)) ** 2)
    F = F * np.where(K < 2, 0, K ** -1.45 * np.exp(-(K / 70.0) ** 2) * (0.35 + 1.0 * streak))
    gx = np.fft.ifft2(F * 1j * KX).real
    gy = np.fft.ifft2(F * 1j * KY).real
    s = 0.22 / np.sqrt((gx ** 2 + gy ** 2).mean())
    nx, ny = -gx * s, -gy * s
    ln = np.sqrt(nx ** 2 + ny ** 2 + 1.0)
    rgba = np.stack([nx / ln * 0.5 + 0.5, ny / ln * 0.5 + 0.5, 1.0 / ln * 0.5 + 0.5, np.ones_like(nx)], -1)
    tdir = EXPORT / 'textures'
    tdir.mkdir(parents=True, exist_ok=True)
    img = bpy.data.images.new('T_WW_Water_Normal', n, n, alpha=True)
    img.pixels.foreach_set(np.ascontiguousarray(rgba, np.float32).ravel())
    img.filepath_raw = str(tdir / 'T_WW_Water_Normal.png')
    img.file_format = 'PNG'
    img.save()
    img.colorspace_settings.name = 'Non-Color'
    return img


def m_water(name='FieldWater'):
    """Unbaked, its own node: spec water hue #1A5659, darkened and at 50 % opacity because the sheet is only a few cm deep
    over dark soil (at the spec's 70 % it read as an opaque teal tarp); roughness 0.05, shared ripple normal."""
    m, nt, b = Q.new_mat(name)
    b.inputs['Base Color'].default_value = (*(0.45 * c for c in lin('#1A5659')), 1)
    b.inputs['Roughness'].default_value = 0.05
    b.inputs['Alpha'].default_value = 0.5
    b.inputs['IOR'].default_value = 1.33
    tx = Q.N(nt, 'ShaderNodeTexImage', image=water_normal_image())
    nm = Q.N(nt, 'ShaderNodeNormalMap')
    nm.inputs['Strength'].default_value = 0.4
    Q.L(nt, tx.outputs['Color'], nm.inputs['Color'])
    Q.L(nt, nm.outputs['Normal'], b.inputs['Normal'])
    m.surface_render_method = 'BLENDED'
    m.use_backface_culling = False
    m['qa_nobake'] = True
    return m


def make_materials():
    g = {}
    g['SOIL'] = m_tilled()
    g['BUND'] = m_rammed()
    g['FSTONE'] = add_moss(Q.m_stone('FieldStone', light=(0.15, 0.16, 0.155), dark=(0.05, 0.056, 0.054), scale=1.6, speck=0.8, chisel=1.6),
                           0.6, (0.45, 0.9), cover=(0.4, 0.6))
    g['STAKE'] = add_moss(Q.m_wood('OldStake', tuple(c * 0.8 for c in lin('#3B2617')), lin('#6E6458'), axis='Z', ring=2.6, wear=0.6, rough=0.8),
                          0.3, (0.6, 0.95))
    g['ENDG'] = Q.m_endgrain('StakeTop', (0.16, 0.12, 0.08), (0.27, 0.21, 0.14))
    g['ROPE'] = Q.m_cord('Hemp', (0.22, 0.16, 0.08), (0.36, 0.27, 0.14))
    g['BAMBOO'] = Q.m_bamboo('SpoutBamboo', (0.26, 0.21, 0.09), (0.40, 0.33, 0.15), axis='Z', aged=0.5)
    g['WATERM'] = m_water()
    g['LEAF'] = m_leaf()
    g['COLLAR'] = Q.m_simple('RootCollar', (0.05, 0.034, 0.022), (0.09, 0.062, 0.04), rough=0.95, nscale=30.0, bump=0.002)
    globals().update(g)


# ====================================================================== shape helpers
def smoothstep(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def boulder(name, radii, loc, mat, seed=1, subd=2, rough=0.16, rot=0.0, squash_top=0.0, cleave=3, ground=0.0, tilt=(0.0, 0.0)):
    """Noise-displaced stone (same generator as the #45 river kit); anything below `ground` (world z) is flattened."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subd, radius=1.0)
    off = Vector((seed * 1.37, seed * 2.11, seed * 0.73))
    rmat = Matrix.Rotation(tilt[0], 3, 'X') @ Matrix.Rotation(tilt[1], 3, 'Y')
    for v in bm.verts:
        d = v.co.normalized()
        k = 1 + rough * noise.fractal(d * 1.4 + off, 0.55, 2.0, 5) + 0.05 * noise.noise(d * 6 + off)
        p = Vector((d.x * radii[0] * k, d.y * radii[1] * k, d.z * radii[2] * k))
        if squash_top and p.z > 0:
            p.z *= 1 - squash_top
        for ci in range(cleave):
            nrm = Vector((math.sin(seed * 3.1 + ci * 2.4), math.cos(seed * 1.7 + ci * 1.3), 0.6 * math.sin(seed + ci))).normalized()
            lim = 0.78 * (radii[0] * abs(nrm.x) + radii[1] * abs(nrm.y) + radii[2] * abs(nrm.z))
            dd = p.dot(nrm)
            if dd > lim:
                p -= nrm * (dd - lim) * 0.85
        p = rmat @ p
        c, s = math.cos(rot), math.sin(rot)
        p = Vector((p.x * c - p.y * s, p.x * s + p.y * c, p.z))
        p.z = max(p.z, ground - loc[2])
        v.co = p
    o = Q._obj(name, bm, mat, sharp=60)
    o.location = loc
    return o


def rect_ring(th, hx, hy, n=6.0):
    """Point and outward normal on a superellipse rounded rectangle at angle th (0 = +X, counter-clockwise)."""
    c, s = math.cos(th), math.sin(th)
    x = hx * math.copysign(abs(c) ** (2 / n), c)
    y = hy * math.copysign(abs(s) ** (2 / n), s)
    nx = abs(x / hx) ** (n - 1) * math.copysign(1, x) / hx
    ny = abs(y / hy) ** (n - 1) * math.copysign(1, y) / hy
    nl = math.hypot(nx, ny) or 1.0
    return x, y, nx / nl, ny / nl


def perimeter_angles(hx, hy, count, n=6.0):
    """Angles that space `count` points evenly by arc length around rect_ring."""
    fine = [TAUi * i / 2000 for i in range(2001)]
    pts = [rect_ring(a, hx, hy, n)[:2] for a in fine]
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


TAUi = math.tau


def soil_h(x, y):
    """Bed soil height (field-local): furrow bottom, three raised rows tapering at the row ends, rising to meet the bund."""
    h = SOIL_BASE
    taper = 1.0 - smoothstep(1.12, 1.34, abs(y))
    for c in ROW_X:
        h += 0.10 * math.exp(-((x - c) / 0.2) ** 4) * taper              # flat-topped raked rows, clear furrows between
    h += 0.045 * smoothstep(0.84, 0.99, abs(x)) + 0.045 * smoothstep(1.24, 1.39, abs(y))
    clods = 0.011 * noise.fractal(Vector((x * 22.0, y * 22.0, 0.3)), 0.6, 2.0, 3)        # loose clods and crumbs
    return h + 0.006 * noise.noise(Vector((x * 9.0, y * 9.0, 0.3))) + clods


# ====================================================================== TY01 field bed
def build_TY01():
    rnd = random.Random(101)
    # rammed-earth bund: a ring lofted around the bed (outside -> top -> inner wall that dips under the soil)
    prof = [(0.00, 0.00), (0.03, 0.10), (0.07, 0.23), (0.11, 0.285), (0.17, BUND_TOP), (0.21, 0.29), (0.235, 0.20), (0.25, 0.12)]
    ns = 192
    bm = bmesh.new()
    rings = []
    for i in range(ns):
        th = TAUi * i / ns
        row = []
        for k, (d, z) in enumerate(prof):
            x, y, nx, ny = rect_ring(th, FIELD_HX - d, FIELD_HY - d)
            wob = (0.022 * noise.noise(Vector((x * 3.1, y * 3.1, k * 0.7))) + 0.008 * noise.noise(Vector((x * 14.0, y * 14.0, k)))) if 0 < k < len(prof) - 1 else 0.0
            row.append(bm.verts.new((x + nx * wob, y + ny * wob, z + (0.012 * noise.noise(Vector((x * 2.3, y * 2.3, 5.0))) if 2 <= k <= 5 else 0.0))))
        rings.append(row)
    for i in range(ns):
        A, B = rings[i], rings[(i + 1) % ns]
        for k in range(len(prof) - 1):
            bm.faces.new((A[k], B[k], B[k + 1], A[k + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    Q._obj('TY01_Bund', bm, BUND, sharp=50)

    # bed soil: a height field tucked under the bund's inner wall
    nx_, ny_ = 72, 100
    hx, hy = FIELD_HX - 0.225, FIELD_HY - 0.225
    bm = bmesh.new()
    grid = [[bm.verts.new((-hx + 2 * hx * i / nx_, -hy + 2 * hy * j / ny_, 0.0)) for i in range(nx_ + 1)] for j in range(ny_ + 1)]
    for row in grid:
        for v in row:
            v.co.z = soil_h(v.co.x, v.co.y)
    for j in range(ny_):
        for i in range(nx_):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    Q._obj('TY01_Soil', bm, SOIL, sharp=80)

    # fieldstones: a top course set into the bund crown and a lower course leaning on the outer face
    inlet_y = 0.55
    for course, (inset, z, count, rad) in enumerate(((0.15, BUND_TOP - 0.025, 58, (0.11, 0.075, 0.048)), (0.045, 0.08, 50, (0.12, 0.06, 0.09)))):
        for k, th in enumerate(perimeter_angles(FIELD_HX - inset, FIELD_HY - inset, count)):
            x, y, nx, ny = rect_ring(th, FIELD_HX - inset, FIELD_HY - inset)
            if x > 0.9 and abs(y - inlet_y) < 0.2:      # leave the gap for the inlet stone
                continue
            s = rnd.choice((0.7, 0.85, 1.0, 1.0, 1.15, 1.3))
            r = (rad[0] * s, rad[1] * rnd.uniform(0.85, 1.2), rad[2] * rnd.uniform(0.8, 1.15))
            tilt = (0.0, 0.0) if course == 0 else (0.35 * ny, -0.35 * nx)
            boulder(f'TY01_Stone_{course}_{k}', r, (x, y, z + (0.0 if course == 0 else rnd.uniform(-0.01, 0.03))), FSTONE,
                    seed=course * 100 + k + 3, subd=2, rough=0.3, rot=math.atan2(ny, nx) + math.pi / 2 + rnd.uniform(-0.25, 0.25),
                    squash_top=0.35 if course == 0 else 0.0, tilt=tilt, ground=0.0)

    # inlet: a notched stone in the +X long side with a split-bamboo spout over it (faces the path when the field sits at x = -2.8)
    blk = Q.box('TY01_InletStone', (0.24, 0.3, 0.24), (FIELD_HX - 0.12, inlet_y, 0.17), FSTONE, bevel=0.018, bseg=3)
    cut = Q.box('TY01_InletCut', (0.5, 0.09, 0.12), (FIELD_HX - 0.12, inlet_y, 0.29), None, bevel=0.0)
    Q.boolean(blk, cut)
    Q.jitter(blk, 0.004, seed=7)
    spout = Q.pole('TY01_Spout', (FIELD_HX + 0.16, inlet_y, 0.355), (FIELD_HX - 0.16, inlet_y, 0.3), 0.032, BAMBOO, segs=12, node_every=0.3)
    half = Q.box('TY01_SpoutCut', (0.5, 0.12, 0.06), (FIELD_HX, inlet_y, 0.358), None, bevel=0.0, rot=(0, math.radians(-9.75), 0))
    Q.boolean(spout, half)                       # split along its length: an open channel, not a pipe
    Q.box('TY01_SpoutProp', (0.05, 0.05, 0.315), (FIELD_HX + 0.1, inlet_y, 0.1575), STAKE, bevel=0.006)
    SOCKETS.append(dict(name='SOCKET_inlet', loc=[round(FIELD_HX + 0.16, 4), inlet_y, 0.355], forward=[-1.0, 0.0, 0.0]))

    # corner stakes with a hemp lashing
    for k, (sx, sy) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        x, y = sx * (FIELD_HX - 0.07), sy * (FIELD_HY - 0.07)
        h = rnd.uniform(0.42, 0.47)
        st = Q.box(f'TY01_Stake_{k}', (0.085, 0.085, h), (x, y, h / 2), STAKE, bevel=0.01, bseg=2,
                   rot=(rnd.uniform(-0.04, 0.04), rnd.uniform(-0.04, 0.04), rnd.uniform(-0.2, 0.2)))
        Q.jitter(st, 0.003, seed=20 + k)
        cap = Q.cyl(f'TY01_StakeTop_{k}', 0.036, 0.012, (x, y, h + 0.002), ENDG, segs=10)
        cap.rotation_euler = st.rotation_euler
        for w in range(3):
            Q.torus(f'TY01_Lash_{k}_{w}', 0.062, 0.011, (x, y, 0.27 + w * 0.024), ROPE, major=20, minor=6,
                    rot=(rnd.uniform(-0.12, 0.12), rnd.uniform(-0.12, 0.12), 0))

    # flooded-state water (its own node, hidden in the dry and wet states)
    bm = bmesh.new()
    wx, wy = FIELD_HX - 0.235, FIELD_HY - 0.235
    nwx, nwy = 8, 11
    vg = [[bm.verts.new((-wx + 2 * wx * i / nwx, -wy + 2 * wy * j / nwy, WATER_Z)) for i in range(nwx + 1)] for j in range(nwy + 1)]
    for j in range(nwy):
        for i in range(nwx):
            bm.faces.new((vg[j][i], vg[j][i + 1], vg[j + 1][i + 1], vg[j + 1][i]))
    uv = bm.loops.layers.uv.new('UVMap')
    for f in bm.faces:
        for lp in f.loops:
            lp[uv].uv = (lp.vert.co.x / 0.5, lp.vert.co.y / 0.5)
    Q._obj('TY01_Water', bm, WATERM, sharp=80)


# ====================================================================== TY02 qingling grass, four stages
def blade(bm, lay, base, yaw, length, width, lean, arch, twist, segs, glow_from=None, curl=0.0):
    """One leaf: a folded strip (edge, midrib, edge) bending outward and down along its length."""
    d = Vector((math.cos(yaw), math.sin(yaw), 0.0))
    side = Vector((-d.y, d.x, 0.0))
    pts, p = [], Vector(base)
    step = length / segs
    for i in range(segs + 1):
        t = i / segs
        ang = lean + arch * t ** 1.6                       # angle from vertical grows toward the tip
        if i:
            p = p + (Vector((0, 0, math.cos(ang))) + d * math.sin(ang)) * step
        pts.append((t, p.copy(), ang))
    rows = []
    for t, p, ang in pts:
        w = width * min(1.0, 0.45 + t * 4.0) * (1.0 - t ** 1.8) + 0.0008
        tw = twist * t
        sv = side * math.cos(tw) + Vector((0, 0, 1)) * math.sin(tw) * 0.3
        up = (Vector((0, 0, math.cos(ang))) + d * math.sin(ang)).cross(sv).normalized()
        fold = up * (w * (0.35 + curl))
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


STAGES = {   # blades, length range, width, lean (rad), arch, target height
    1: dict(n=3, L=(0.055, 0.085), w=0.012, lean=(0.15, 0.45), arch=(0.2, 0.5), H=0.08, segs=3),
    2: dict(n=8, L=(0.15, 0.24), w=0.015, lean=(0.25, 0.7), arch=(0.3, 0.9), H=0.22, segs=5),
    3: dict(n=22, L=(0.30, 0.47), w=0.021, lean=(0.15, 0.85), arch=(0.5, 1.5), H=0.40, segs=7),
    4: dict(n=28, L=(0.34, 0.54), w=0.023, lean=(0.12, 0.85), arch=(0.5, 1.5), H=0.48, segs=7),
}
FORMS = ('upright', 'leaning', 'spreading')


def clump(name, stage, form, base, seed):
    """One clump at `base`. Forms: upright (narrow fan), leaning (all blades drift one way), spreading (wide, drooping)."""
    rnd = random.Random(seed)
    S = STAGES[stage]
    bm = bmesh.new()
    lay = {'t': bm.verts.layers.float.new('qa_t'), 'x': bm.verts.layers.float.new('qa_x'), 'g': bm.verts.layers.float.new('qa_glow')}
    drift = rnd.uniform(0, TAUi)
    for i in range(S['n']):
        yaw = TAUi * i / S['n'] + rnd.uniform(-0.4, 0.4)
        lean = rnd.uniform(*S['lean'])
        arch = rnd.uniform(*S['arch'])
        if form == 'upright':
            lean *= 0.6
            arch *= 0.7
        elif form == 'leaning':
            yaw = drift + (yaw - drift) * 0.55
            lean += 0.15
        else:
            lean = lean * 1.25 + 0.1
            arch *= 1.2
        L = rnd.uniform(*S['L']) * (1.0 - 0.35 * (lean / 1.2))   # outer leaves a little shorter
        off = Vector((math.cos(yaw), math.sin(yaw), 0)) * rnd.uniform(0.0, 0.012 + 0.006 * stage)
        blade(bm, lay, Vector(base) + off, yaw, L, S['w'] * rnd.uniform(0.8, 1.15), lean, arch, rnd.uniform(-0.6, 0.6), S['segs'],
              glow_from=0.9 if stage == 4 else None, curl=rnd.uniform(0.0, 0.25))
    o = Q._obj(name, bm, LEAF, sharp=89)
    zmax = max(v.co.z for v in o.data.vertices) - base[2]
    if zmax > S['H']:                                       # keep each stage at its sheet height
        k = S['H'] / zmax
        for v in o.data.vertices:
            v.co = Vector(base) + (v.co - Vector(base)) * Vector((1.0, 1.0, k))
    o['qa_node'] = f'S{stage}'
    if stage >= 2:                                           # a dark collar of disturbed soil hides the blade roots
        col = Q.cyl(f'{name}_Collar', 0.03 + 0.012 * stage, 0.018, (base[0], base[1], base[2] + 0.004), COLLAR, segs=12, r2=0.012 + 0.006 * stage)
        Q.jitter(col, 0.003, seed=seed)
        col['qa_node'] = f'S{stage}'
    return o


def build_TY02():
    """Four stage meshes for one field (12 clumps on TY01's three rows), sharing TY01's origin and one atlas."""
    rnd = random.Random(202)
    spots = [(x + rnd.uniform(-0.04, 0.04), y + rnd.uniform(-0.05, 0.05)) for x in ROW_X for y in PLANT_Y]
    forms = [FORMS[(i * 7 + 1) % 3] for i in range(len(spots))]
    for stage in (1, 2, 3, 4):
        for i, ((x, y), form) in enumerate(zip(spots, forms)):
            clump(f'TY02_S{stage}_{i:02d}', stage, form, (x, y, soil_h(x, y) - 0.012), seed=stage * 100 + i)


# ====================================================================== asset table + build
def glb_roundtrip(path, skip):
    """Re-import a GLB; triangles and bbox of every mesh except the LOD1 / LOD2 copies (LOD0 + water is what is compared)."""
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


SOCKETS = []

ASSETS = {
    'TY01': dict(build=build_TY01, ref='TY01_three_view.png', name='SpiritField', res=2048, states=('Dry', 'Wet'),
                 category='structure (embedded bed; ground from terrain)', slot=['TY_Field_1 (-2.8, 6.7)', 'TY_Field_2 (2.8, 6.7)'],
                 collision=dict(type='box', size=[2.4, 3.2, 0.3], center=[0, 0, 0.15],
                                note='rim 0.3 m: not meant to be walked through; plant / harvest from the side. Inlet on +X: '
                                     'rotate 180 deg about the vertical for TY_Field_2 so both inlets face the x = 0 path')),
    'TY02': dict(build=build_TY02, ref='TY02_three_view.png', name='QinglingGrass', res=2048, states=None,
                 category='crop stages (placed with TY01, same origin)', slot=['inside TY01'],
                 collision=dict(type='none', note='non-blocking plants; swap S1..S4 by growth t: <0.25 S1, <0.6 S2, <1 S3, >=1 S4')),
}


def build_asset(aid):
    t0 = time.time()
    a = ASSETS[aid]
    stem = f"{aid}_{a['name']}_{Q.VER}"           # file name (versioned, never overwritten by a later version)
    obj = f"SM_TY_{a['name']}"                      # object name prefix (spec section 7)
    assert (REF / a['ref']).is_file(), f'{aid}: save and review the AI reference sheet before modelling'
    Q.reset()
    random.seed(31)
    src = Q.coll('10_Procedural_Source')
    Q.ACTIVE['coll'] = src
    make_materials()
    SOCKETS.clear()
    a['build']()
    parts = [o for o in src.objects if o.type == 'MESH' and not o.get('qa_cutter')]
    bpy.context.view_layer.update()
    Q.finalize_parts(parts, seed=sum(map(ord, aid)))
    game = Q.coll('00_Game_Export')
    Q.ACTIVE['coll'] = game
    G, K = Q.game_mesh(obj, parts, game)
    tdir = EXPORT / 'textures'
    soil = SOIL.node_tree.nodes.get('WETNESS')
    imgs, alpha = Q.bake_asset(G, f"{aid}_{a['name']}" + ('_Dry' if a['states'] else ''), tdir, a['res'])
    extra = {}
    if a['states']:                                  # the wet state: same mesh and UVs, only the bed soil changes
        soil.outputs[0].default_value = 1.0
        wet, _ = Q.bake_asset(G, f"{aid}_{a['name']}_Wet", tdir, a['res'])
        (tdir / f"T_{aid}_{a['name']}_Wet_Normal.png").unlink()      # identical to the dry normal map
        extra = {'Wet': {k: wet[k] for k in ('BaseColor', 'ORM')}}
        soil.outputs[0].default_value = 0.0
    glow_faces = None
    if 'Emissive' in imgs:                           # glowing tips get their own material slot (engines can drive it)
        at = G.data.attributes.get('qa_glow')
        vals = np.zeros(len(G.data.vertices), np.float32)
        at.data.foreach_get('value', vals)
        glow_faces = [p.index for p in G.data.polygons if max(vals[i] for i in p.vertices) > 0.05]
    base_imgs = {k: v for k, v in imgs.items() if k != 'Emissive'}
    gm = Q.game_material(f"TY_{a['name']}", base_imgs, alpha)
    gm.use_backface_culling = aid != 'TY02'
    G.data.materials.clear()
    G.data.materials.append(gm)
    if glow_faces:
        gg = Q.game_material(f"TY_{a['name']}_Glow", imgs, alpha, emit_strength=2.0)
        gg.use_backface_culling = False
        G.data.materials.append(gg)
        for i in glow_faces:
            G.data.polygons[i].material_index = 1
    for nm, d in extra.items():                      # second material for the wet state (kept in the .blend; engines build it from the Wet textures)
        wm = Q.game_material(f"TY_{a['name']}_{nm}", {**base_imgs, **d}, alpha)
        wm.use_fake_user = True
    G.name = f'{obj}_LOD0'
    clear = []
    if K:
        K.name = f'{obj}_Water'
        K.data.name = f'{obj}_Water_Mesh'
        clear = [K]
    nodes = Q.split_nodes(G, obj)
    if aid == 'TY02':                                # node 0 ('Body') is empty: every clump is tagged with its stage
        nodes = [n for n in nodes if len(n.data.polygons)]
    lods = []
    for n in nodes:
        base = n.name[:-5] if n.name.endswith('_LOD0') else n.name
        tri = Q.tri_count(n)
        ls = Q.make_lods(n, ratios=(0.5, 0.15), gcoll=game)
        for l in ls:                                 # collapse can push a base vertex a few mm under the ground
            for vv in l.data.vertices:
                vv.co.z = max(vv.co.z, 0.0)
        for l, nm in zip(ls, ('LOD1', 'LOD2')):
            l.name = f'{base}_{nm}'
        lods += ls
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
    glb, fbx = EXPORT / f'{stem}.glb', EXPORT / f'{stem}.fbx'
    shipped = nodes + clear + empties
    Q.export(shipped, glb, fbx, shipped + lods)
    Q.select_only(shipped + lods, nodes[0])          # the GLB carries the LOD1 / LOD2 meshes too
    bpy.ops.export_scene.gltf(filepath=str(glb), export_format='GLB', use_selection=True, export_apply=True,
                              export_yup=True, export_image_format='WEBP', export_image_quality=88,
                              export_materials='EXPORT', export_extras=False)
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
    mn, mx = Q.bbox(nodes + clear)
    dims = [round(mx[i] - mn[i], 4) for i in range(3)]
    per_node = {n.name: [Q.tri_count(n)] + [Q.tri_count(l) for l in lods if l.name.rsplit('_', 1)[0] == n.name.rsplit('_', 1)[0]] for n in nodes}
    lod0 = sum(Q.tri_count(o) for o in nodes + clear)
    hs = [Q.mesh_health(o) for o in nodes]
    health = {k: sum(h[k] for h in hs) for k in hs[0]}
    rt_tris, rmn, rmx, rmats = glb_roundtrip(glb, {o.name for o in lods})
    v = {
        'asset': aid, 'dimensions_m': dims, 'bbox_min': [round(x, 4) for x in mn], 'bbox_max': [round(x, 4) for x in mx],
        'trianglesLOD0': lod0, 'trianglesPerNode': per_node,
        'materials': sorted({m.name for o in nodes + clear for m in o.data.materials if m}), 'textureResolution': a['res'],
        'nodes': [o.name for o in nodes + clear], 'originAtBase': abs(mn[2]) < 0.003, 'meshHealth': health,
        'glbRoundTrip': {'triangles': rt_tris, 'trianglesMatch': rt_tris == lod0,
                         'bboxMatch': all(abs(p - q) < 0.002 for p, q in zip(rmn + rmx, mn + mx)),
                         'bbox': [[round(x, 4) for x in rmn], [round(x, 4) for x in rmx]], 'materials': rmats},
        'files': {p.name: {'bytes': p.stat().st_size, 'sha256': Q.sha(p)} for p in (glb, fbx)},
        'reference': f"art/references/territory-backyard-a/{a['ref']}",
        'notChecked': ['Unity import', 'in-game lighting', 'mobile performance', 'LOD screen-size thresholds'],
    }
    info = dict(id=aid, name=a['name'], file=stem, units='metre', forward='-Y (Blender) / +Z (glTF)', origin='footprint centre, base z = 0',
                category=a['category'], slots=a['slot'], dimensions_m=dims, triangles_lod0=lod0, triangles_per_node=per_node,
                collision=a['collision'], sockets=list(SOCKETS), author='Johnnnny0823', validation=v)
    if aid == 'TY01':
        info['states'] = {
            'dry': f'material M_TY_{a["name"]} (T_{aid}_{a["name"]}_Dry_*); hide {obj}_Water',
            'wet': f'material M_TY_{a["name"]}_Wet (T_{aid}_{a["name"]}_Wet_BaseColor / _ORM, normal shared); hide {obj}_Water',
            'flooded': f'wet material and show {obj}_Water (surface z = {WATER_Z} m, for clearwater lotus)',
        }
        info['planting'] = dict(rows_x=list(ROW_X), plants_y=list(PLANT_Y), note='3 x 4 clumps, field-local; crop meshes share this origin')
    if aid == 'TY02':
        info['stages'] = {f'{obj}_S{i}_LOD0': dict(t_from=STAGE_T[i - 1], t_to=(STAGE_T[i] if i < 4 else None), height_m=STAGES[i]['H'])
                          for i in (1, 2, 3, 4)}
        info['glow'] = f'mature leaf tips use material M_TY_{a["name"]}_Glow (Emissive map, strength 2); every other face uses M_TY_{a["name"]}'
    (EXPORT / f'{stem}_model_info.json').write_text(json.dumps(info, indent=1, ensure_ascii=False), encoding='utf-8')
    print(f'[{stem}] lod0 {lod0} per-node {per_node} dims {dims} health {health} roundtrip {rt_tris} {time.time() - t0:.0f}s', flush=True)
    return v


# ====================================================================== review sheets (from the exported GLBs)
HDRI = Path(os.environ.get('YJ_HDRI', Path.home() / '.cache/yunjing/hdri/kloofendal_48d_partly_cloudy_puresky_2k.hdr'))


def outdoor_light():
    """Review lighting of modelling spec section 8: EEVEE, Poly Haven kloofendal_48d_partly_cloudy_puresky (CC0) at
    strength 1.0, AgX Medium High Contrast. The HDRI is not in the repo (set YJ_HDRI or put it in ~/.cache/yunjing/hdri)."""
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
    bg = nt.nodes.get('Background')
    env = nt.nodes.new('ShaderNodeTexEnvironment')
    env.image = bpy.data.images.load(str(HDRI), check_existing=True)
    nt.links.new(env.outputs['Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 1.0
    for attr, val in (('sun_threshold', 2.0), ('use_sun_shadow', True), ('sun_angle', math.radians(1.5))):
        if hasattr(w, attr):          # EEVEE extracts the HDRI sun into a shadow-casting light
            setattr(w, attr, val)
    for attr, val in (('use_shadows', True), ('use_raytracing', True), ('use_gtao', True)):
        if hasattr(s.eevee, attr):
            setattr(s.eevee, attr, val)
    s.view_settings.view_transform = 'AgX'
    s.view_settings.look = 'AgX - Medium High Contrast'
    gm = bpy.data.materials.new('QA_Ground')
    gm.use_nodes = True
    gb = gm.node_tree.nodes.get('Principled BSDF')
    gb.inputs['Base Color'].default_value = (0.20, 0.17, 0.12, 1)
    gb.inputs['Roughness'].default_value = 0.95
    bpy.ops.mesh.primitive_plane_add(size=60)
    g = bpy.context.active_object
    g.name = 'QA_Ground'
    g.data.materials.append(gm)


def scale_figure(loc):
    """Plain grey 1.75 m figure (head top at 1.75 m)."""
    m = bpy.data.materials.get('QA_Figure') or Q.m_simple('QA_Figure', (0.30, 0.31, 0.31), (0.33, 0.34, 0.34), rough=0.8)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=0.17, radius2=0.2, depth=0.85, matrix=Matrix.Translation((0, 0, 0.425)))
    bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=0.2, radius2=0.12, depth=0.7, matrix=Matrix.Translation((0, 0, 1.2)))
    bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=0.11, matrix=Matrix.Translation((0, 0, 1.64)))
    Q.ACTIVE['coll'] = None
    o = Q._obj('QA_Figure', bm, m)
    o.location = loc
    return o


def load(stem, at=(0, 0, 0), rot=0.0, keep=lambda n: True):
    """Import an exported GLB, drop its LOD1/LOD2 copies and sockets, move it to `at`."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(EXPORT / f'{stem}.glb'))
    new = [o for o in bpy.data.objects if o not in before]
    out = []
    for o in new:
        if o.type != 'MESH' or '_LOD1' in o.name or '_LOD2' in o.name or not keep(o.name):
            bpy.data.objects.remove(o)
            continue
        o.location = Matrix.Rotation(rot, 3, 'Z') @ o.location + Vector(at)
        o.rotation_euler.z += rot
        out.append(o)
    return out


def wet(objs):
    """Swap the field's dry textures for the wet set (what an engine does for the wet / flooded states)."""
    tdir = EXPORT / 'textures'
    for o in objs:
        for i, m in enumerate(o.data.materials):
            if not m or 'SpiritField' not in m.name:
                continue
            w = m.copy()
            for n in w.node_tree.nodes:
                if n.type == 'TEX_IMAGE' and n.image and ('BaseColor' in n.image.name or 'ORM' in n.image.name):
                    kind = 'BaseColor' if 'BaseColor' in n.image.name else 'ORM'
                    img = bpy.data.images.load(str(tdir / f'T_TY01_SpiritField_Wet_{kind}.png'), check_existing=True)
                    img.colorspace_settings.name = 'sRGB' if kind == 'BaseColor' else 'Non-Color'
                    n.image = img
            o.data.materials[i] = w


def shot(path, cam_loc, target, lens=50, res=(1600, 1000), ortho=None, samples=96):
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
    s.cycles.samples = samples
    s.eevee.taa_render_samples = samples
    s.render.filepath = str(path)
    s.render.image_settings.file_format = 'PNG'
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)
    print('SHOT', Path(path).name, flush=True)


def sheets():
    f1, f2 = 'TY01_SpiritField_v001', 'TY02_QinglingGrass_v001'
    no_water = lambda n: not n.endswith('_Water')
    # TY01: four review views with the 1.75 m figure (spec section 8)
    Q.reset(); Q.gpu(bpy.context.scene, 96); outdoor_light()
    load(f1, keep=no_water)
    scale_figure((-2.0, 0.0, 0))
    out = PREV / 'TY01_SpiritField'
    shot(out / 'ortho_front.png', (-0.4, -30, 0.45), (-0.4, 0, 0.45), ortho=4.6)
    shot(out / 'ortho_side.png', (30, 0, 0.6), (0, 0, 0.6), ortho=5.0)
    shot(out / 'ortho_back.png', (-0.4, 30, 0.45), (-0.4, 0, 0.45), ortho=4.6)
    shot(out / 'three_quarter.png', (3.4, -4.4, 2.6), (0, 0, 0.15), lens=50)
    shot(out / 'close_inlet.png', (2.3, -0.6, 0.9), (1.2, 0.55, 0.28), lens=50)
    # TY01 states: dry / wet / flooded
    Q.reset(); Q.gpu(bpy.context.scene, 96); outdoor_light()
    load(f1, (-3.0, 0, 0), keep=no_water)
    wet(load(f1, (0, 0, 0), keep=no_water))
    wet(load(f1, (3.0, 0, 0)))
    shot(out / 'states_dry_wet_flooded.png', (0, -7.6, 5.2), (0, 0, 0.1), lens=40, res=(1800, 1000))
    # TY02: the four stages side by side, each in a dry field
    Q.reset(); Q.gpu(bpy.context.scene, 96); outdoor_light()
    out2 = PREV / 'TY02_QinglingGrass'
    for i in range(4):
        x = (i - 1.5) * 2.9
        load(f1, (x, 0, 0), keep=no_water)
        load(f2, (x, 0, 0), keep=lambda n, i=i: f'_S{i + 1}_' in n)
    shot(out2 / 'stages_side_by_side.png', (0, -9.5, 3.4), (0, 0, 0.25), lens=40, res=(2000, 900))
    # TY02: one mature field, close and from above
    Q.reset(); Q.gpu(bpy.context.scene, 128); outdoor_light()
    load(f1, keep=no_water)
    load(f2, keep=lambda n: '_S4_' in n)
    scale_figure((-1.9, -0.6, 0))
    shot(out2 / 'mature_close.png', (-0.15, -2.6, 0.95), (-0.15, -0.7, 0.35), lens=50)
    # TY02: top-down layout of one mature field
    shot(out2 / 'top_layout.png', (0, 0, 20), (0, 0.0001, 0), ortho=3.6, res=(1200, 1400))
    # TY02: 1.7 m eye height, standing at the field's long side and looking down at the mature crop
    shot(out2 / 'eye_1p7m_mature.png', (2.1, -2.3, 1.7), (0.0, 0.1, 0.25), lens=28, res=(1600, 900))
    # comparison with the village communal spirit bed (irrigation-v2, already in the game)
    Q.reset(); Q.gpu(bpy.context.scene, 96); outdoor_light()
    load(f1, (-1.8, 0, 0), keep=no_water)
    load(f2, (-1.8, 0, 0), keep=lambda n: '_S3_' in n)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(ROOT.parents[2] / 'art/exports/irrigation-v2/spirit-bed.glb'))
    other = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    mn, mx = Q.bbox(other)
    for o in [o for o in bpy.data.objects if o not in before and not o.parent]:
        o.location += Vector((2.2 - (mn[0] + mx[0]) / 2, -(mn[1] + mx[1]) / 2, -mn[2]))
    scale_figure((0.3, -2.2, 0))
    shot(PREV / 'TY01_SpiritField' / 'compare_village_spirit_bed.png', (0.2, -8.0, 4.4), (0.2, 0, 0.3), lens=40, res=(1800, 1000))


if __name__ == '__main__' and '--sheets' in ARGV:
    sheets()
elif __name__ == '__main__':
    todo = [x for x in ARGV if not x.startswith('--')] or list(ASSETS)
    report = {aid: build_asset(aid) for aid in todo}
    print('DONE', json.dumps({k: [v['trianglesLOD0'], v['glbRoundTrip']['trianglesMatch'], v['glbRoundTrip']['bboxMatch']] for k, v in report.items()}), flush=True)
