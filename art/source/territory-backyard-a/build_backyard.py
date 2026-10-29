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
    g['LOTUSLEAF'] = m_lotus_leaf()
    g['PETAL'] = m_petal()
    g['POD'] = m_pod()
    g['STALK'] = Q.m_simple('LotusStalk', (0.06, 0.10, 0.04), (0.10, 0.15, 0.06), rough=0.5, nscale=60.0, bump=0.0006)
    g['LSTONE'] = m_lantern_stone()
    g['LWOOD'] = Q.m_wood('LanternFrame', (0.05, 0.03, 0.018), (0.11, 0.07, 0.04), axis='Z', ring=3.0, wear=0.5, rough=0.7)
    g['PAPER'] = m_paper()
    g['PSTONE'] = m_worn_stone()
    g['JOINT'] = Q.m_simple('JointEarth', (0.035, 0.026, 0.018), (0.06, 0.045, 0.03), rough=0.95, nscale=20.0, bump=0.002)
    g['GRASS'] = Q.m_simple('JointGrass', (0.035, 0.065, 0.02), (0.09, 0.13, 0.04), rough=0.8, nscale=30.0, bump=0.0004)
    g['TSTONE'] = add_moss(Q.m_stone('TrainingGranite', light=(0.20, 0.20, 0.19), dark=(0.07, 0.072, 0.07), scale=2.2, speck=1.2, chisel=1.0), 0.25, (0.7, 0.98))
    g['BRONZE'] = Q.m_simple('OxidisedCopper', lin('#3E5C52'), lin('#6B8F7E'), rough=0.45, metal=0.7, nscale=14.0, bump=0.001, edge_col=(0.25, 0.17, 0.09))
    g['TWOOD'] = Q.m_wood('HandledElm', (0.06, 0.036, 0.02), (0.15, 0.095, 0.055), axis='Z', ring=3.2, wear=0.7, rough=0.65)
    g['IRON'] = Q.m_iron('OldIron', rust=0.45)
    g['TASSEL'] = Q.m_simple('FadedTassel', (0.22, 0.05, 0.03), (0.32, 0.09, 0.05), rough=0.9, nscale=60.0)
    g['FWOOD'] = add_moss(Q.m_wood('FencePost', tuple(c * 0.8 for c in lin('#3B2617')), lin('#6E6458'), axis='Z', ring=2.4, wear=0.6, rough=0.82), 0.3, (0.6, 0.95))
    g['FBAMBOO'] = Q.m_bamboo('FenceBamboo', (0.25, 0.20, 0.09), (0.38, 0.31, 0.15), axis='Z', aged=0.5)
    g['RBAMBOO'] = Q.m_bamboo('RackBamboo', (0.30, 0.25, 0.11), (0.45, 0.37, 0.18), axis='Z', aged=0.35)
    g['WEAVE'] = Q.m_weave('GateWicker', pitch=0.03, a=(0.22, 0.17, 0.08), b_=(0.36, 0.28, 0.14))
    g['SIEVE'] = Q.m_weave('SieveWeave', pitch=0.012, a=(0.30, 0.22, 0.10), b_=(0.46, 0.35, 0.18))
    g['BASKETW'] = Q.m_weave('BasketWeave', pitch=0.02, a=(0.28, 0.21, 0.09), b_=(0.44, 0.34, 0.16), mode='wall', radius=0.17)
    g['BUCKETW'] = Q.m_wood('BucketStaves', (0.08, 0.05, 0.028), (0.17, 0.11, 0.06), axis='Z', ring=4.0, wear=0.5, rough=0.7)
    g['JAR'] = Q.m_celadon('JarGlaze', glaze_z=0.1, clay=(0.30, 0.22, 0.15), g1=(0.06, 0.10, 0.075), g2=(0.13, 0.17, 0.12), crackle=0.9, glaze_rough=0.3)
    g['GOURD'] = Q.m_simple('DryGourd', (0.36, 0.24, 0.10), (0.50, 0.36, 0.16), rough=0.5, nscale=10.0, bump=0.0006)
    g['FIREWOOD'] = Q.m_wood('SplitFirewood', (0.17, 0.11, 0.06), (0.33, 0.23, 0.13), axis='Z', ring=5.0, wear=0.3, rough=0.85)
    g['GRAVEL'] = m_gravel()
    g['HERB'] = Q.m_simple('DryingHerb', (0.05, 0.075, 0.025), (0.15, 0.15, 0.06), rough=0.8, nscale=40.0, bump=0.0004, cav_col=(0.03, 0.04, 0.015))
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
        shift_module(f'S{stage}', 2.6 * (stage - 1))


# ====================================================================== TY03 clearwater lotus, four stages
def m_lotus_leaf(name='LotusLeaf'):
    """Round leaf: qa_t = radius 0 (centre) .. 1 (rim), qa_x = angle / tau. Blue-green, paler centre spot, radial veins,
    a faint yellow rim and a few weathered spots."""
    m, nt, b = Q.new_mat(name)
    r = Q.attr(nt, 'qa_t', 'fac')
    ang = Q.attr(nt, 'qa_x', 'fac')
    co = Q.coords(nt, (1, 1, 1))
    col = Q.mix(nt, Q.smooth(nt, Q.noise(nt, co, 9.0, 4), 0.3, 0.7), (0.040, 0.085, 0.042), (0.075, 0.13, 0.055))
    col = Q.mix(nt, Q.math_(nt, 'SUBTRACT', 1.0, Q.smooth(nt, r, 0.02, 0.12)), col, (0.17, 0.22, 0.10))
    veins = Q.math_(nt, 'MULTIPLY', Q.smooth(nt, Q.math_(nt, 'SINE', Q.math_(nt, 'MULTIPLY', ang, math.tau * 21)), 0.82, 1.0), Q.smooth(nt, r, 0.08, 0.3))
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', veins, 0.5), col, (0.13, 0.19, 0.09))
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', Q.smooth(nt, r, 0.9, 1.0), 0.5), col, (0.18, 0.17, 0.06))
    spot = Q.math_(nt, 'MULTIPLY', Q.smooth(nt, Q.noise(nt, co, 35.0, 2), 0.7, 0.76), 0.6)
    col = Q.mix(nt, spot, col, (0.12, 0.10, 0.05))
    m = Q.finish(m, nt, b, col, 0.42, 0.0, Q.math_(nt, 'ADD', veins, Q.math_(nt, 'MULTIPLY', Q.noise(nt, co, 60.0, 3), 0.2)), 0.0006, 0.6)
    m['qa_texel'] = 1.3
    return m


def m_petal(name='LotusPetal'):
    """qa_t = 0 at the petal base .. 1 at its tip; white with a faint pink tip and fine longitudinal veins."""
    m, nt, b = Q.new_mat(name)
    t = Q.attr(nt, 'qa_t', 'fac')
    x = Q.attr(nt, 'qa_x', 'fac')
    col = Q.mix(nt, Q.smooth(nt, t, 0.0, 0.3), (0.62, 0.62, 0.40), (0.86, 0.82, 0.74))
    col = Q.mix(nt, Q.smooth(nt, t, 0.65, 1.0), col, (0.86, 0.56, 0.56))
    veins = Q.math_(nt, 'MULTIPLY', Q.smooth(nt, Q.math_(nt, 'SINE', Q.math_(nt, 'MULTIPLY', x, 40.0)), 0.7, 1.0), 0.18)
    col = Q.mix(nt, veins, col, (0.62, 0.55, 0.55))
    m = Q.finish(m, nt, b, col, 0.55, 0.0, veins, 0.0004, 0.4)
    m['qa_texel'] = 1.5
    return m


def m_pod(name='LotusPod'):
    """Seed pod and stamens: yellow-green with seed pits; qa_glow marks the faint moon-white centre glow."""
    m, nt, b = Q.new_mat(name)
    co = Q.coords(nt, (1, 1, 1))
    pits = Q.smooth(nt, Q.voronoi(nt, co, 220.0, 'F1'), 0.12, 0.05)
    col = Q.mix(nt, pits, (0.52, 0.48, 0.14), (0.16, 0.18, 0.06))
    glow = Q.attr(nt, 'qa_glow', 'fac')
    emit = Q.mix(nt, Q.math_(nt, 'MULTIPLY', glow, 0.7), (0, 0, 0), lin('#EEF2F2'))
    return Q.finish(m, nt, b, col, 0.6, 0.0, pits, 0.0008, 0.6, emit=emit)


def set_vattr(o, name, fn):
    """Per-vertex float attribute from fn(local co)."""
    me = o.data
    at = me.attributes.get(name) or me.attributes.new(name, 'FLOAT', 'POINT')
    at.data.foreach_set('value', [fn(v.co) for v in me.vertices])


def lotus_leaf(name, centre, r, tilt=(0.0, 0.0), cup=0.0, seed=0):
    """Round leaf of radius r: rim waves, cupped edges (cup in m), a small central dip where the stalk joins."""
    rnd = random.Random(seed)
    nr, ns = 6, 28
    bm = bmesh.new()
    lt, lx = bm.verts.layers.float.new('qa_t'), bm.verts.layers.float.new('qa_x')
    rot = Matrix.Rotation(tilt[0], 3, 'X') @ Matrix.Rotation(tilt[1], 3, 'Y') @ Matrix.Rotation(rnd.uniform(0, TAUi), 3, 'Z')
    ph = rnd.uniform(0, TAUi)
    c = bm.verts.new(Vector(centre) + rot @ Vector((0, 0, -0.004)))
    c[lt], c[lx] = 0.0, 0.0
    rings = []
    for k in range(1, nr + 1):
        f = k / nr
        row = []
        for i in range(ns):
            a = TAUi * i / ns
            rr = r * f * (1 + 0.04 * math.sin(5 * a + ph))
            z = cup * f ** 2 + 0.012 * r * 4 * f ** 3 * math.sin(7 * a + ph)
            v = bm.verts.new(Vector(centre) + rot @ Vector((rr * math.cos(a), rr * math.sin(a), z)))
            v[lt], v[lx] = f, i / ns
            row.append(v)
        rings.append(row)
    for i in range(ns):
        bm.faces.new((c, rings[0][i], rings[0][(i + 1) % ns]))
    for A, B in zip(rings, rings[1:]):
        for i in range(ns):
            j = (i + 1) % ns
            bm.faces.new((A[i], B[i], B[j], A[j]))
    return Q._obj(name, bm, LOTUSLEAF, sharp=89)


def stalk(name, top, base_z, r=0.007, bend=0.03, seed=0):
    rnd = random.Random(seed)
    top = Vector(top)
    a = rnd.uniform(0, TAUi)
    off = Vector((math.cos(a), math.sin(a), 0)) * bend
    pts = [Vector((top.x, top.y, base_z)) + off * 0.6, Vector((top.x, top.y, (base_z + top.z) / 2)) + off, top]
    return Q.tube(name, pts, r, STALK, segs=8, res=4)


def bud(name, base, h=0.11, r=0.034):
    prof = [(0.0, 0.0)] + [(r * math.sin(math.pi * min(1.0, (z / h) ** 0.75)) * (1 - 0.25 * (z / h) ** 3), z) for z in [h * i / 12 for i in range(1, 12)]] + [(0.0, h)]
    o = Q.lathe(name, prof, PETAL, segs=16, sharp=70)
    o.location = base
    set_vattr(o, 'qa_t', lambda co: min(1.0, co.z / h))
    set_vattr(o, 'qa_x', lambda co: math.atan2(co.y, co.x) / TAUi)
    return o


def petal(bm, lay, base, yaw, open_deg, length, width, cup):
    """One petal: a cupped spoon shape rising from the receptacle at open_deg from vertical."""
    d = Vector((math.cos(yaw), math.sin(yaw), 0))
    side = Vector((-d.y, d.x, 0))
    nu, nv = 6, 4
    rows = []
    for i in range(nu + 1):
        t = i / nu
        ang = math.radians(open_deg) * (0.55 + 0.6 * t)
        p = Vector(base) + (Vector((0, 0, 1)) * math.cos(ang) + d * math.sin(ang)) * length * t
        w = width * math.sin(math.pi * min(0.92, 0.12 + t * 0.8)) ** 0.6                  # broad, rounded tip (lotus, not a star)
        row = []
        for j in range(nv + 1):
            s = j / nv * 2 - 1
            q = p + side * s * w + (Vector((0, 0, 1)) * math.cos(ang) + d * math.sin(ang)).cross(side) * (-cup * (1 - s * s) * w)
            v = bm.verts.new(q)
            v[lay['t']], v[lay['x']] = t, s
            row.append(v)
        rows.append(row)
    for A, B in zip(rows, rows[1:]):
        for j in range(nv):
            bm.faces.new((A[j], B[j], B[j + 1], A[j + 1]))


def bloom(name, base, seed=0):
    rnd = random.Random(seed)
    bm = bmesh.new()
    lay = {'t': bm.verts.layers.float.new('qa_t'), 'x': bm.verts.layers.float.new('qa_x')}
    for ring, (n, ang, L, W) in enumerate(((7, 70, 0.085, 0.042), (8, 46, 0.095, 0.046), (6, 22, 0.08, 0.04))):
        for i in range(n):
            yaw = TAUi * (i + 0.5 * ring) / n + rnd.uniform(-0.12, 0.12)
            petal(bm, lay, Vector(base) + Vector((0, 0, 0.006 * ring)), yaw, ang + rnd.uniform(-6, 6), L * rnd.uniform(0.92, 1.06), W * 1.15, 0.55)
    o = Q._obj(name, bm, PETAL, sharp=89)
    pod = Q.lathe(f'{name}_Pod', [(0.0, 0.0), (0.012, 0.004), (0.022, 0.022), (0.024, 0.03), (0.0, 0.032)], POD, segs=16)
    pod.location = Vector(base) + Vector((0, 0, 0.01))
    set_vattr(pod, 'qa_glow', lambda co: 1.0 if co.z > 0.025 else 0.4)
    for i in range(18):                                   # stamens around the pod
        a = TAUi * i / 18
        s = Q.rod(f'{name}_Stamen_{i}', Vector(base) + Vector((0.024 * math.cos(a), 0.024 * math.sin(a), 0.012)),
                  Vector(base) + Vector((0.04 * math.cos(a), 0.04 * math.sin(a), 0.035)), 0.0015, POD, segs=4)
        set_vattr(s, 'qa_glow', lambda co: 0.3)
    return o


LOTUS_SPOTS = [(-0.5, -0.9), (0.5, -0.9), (-0.5, 0.0), (0.5, 0.0), (-0.5, 0.9), (0.5, 0.9)]


def build_TY03():
    """Four stage meshes for one flooded TY01 field (six plant groups), sharing TY01's origin and one atlas."""
    wz = WATER_Z + 0.003
    for stage in (1, 2, 3, 4):
        for g, (gx, gy) in enumerate(LOTUS_SPOTS):
            rnd = random.Random(300 + g)                  # same group layout at every stage: the plant grows in place
            gx += rnd.uniform(-0.08, 0.08)
            gy += rnd.uniform(-0.08, 0.08)
            parts = []
            nfloat = 3 + (g % 2)
            for k in range(nfloat):
                a = TAUi * k / nfloat + rnd.uniform(-0.3, 0.3)
                d = rnd.uniform(0.08, 0.16) * (1 + 0.5 * (stage > 1))
                r = rnd.uniform(0.05, 0.075) * (1.0 if stage == 1 else rnd.uniform(1.4, 1.75))
                parts.append(lotus_leaf(f'TY03_S{stage}_{g}_F{k}', (gx + d * math.cos(a), gy + d * math.sin(a), wz), r, seed=g * 10 + k))
            if stage >= 2:
                nstand = 2 + (stage >= 3)
                for k in range(nstand):
                    a = rnd.uniform(0, TAUi)
                    top = Vector((gx + 0.12 * math.cos(a), gy + 0.12 * math.sin(a), WATER_Z + rnd.uniform(0.22, 0.32)))
                    parts.append(lotus_leaf(f'TY03_S{stage}_{g}_U{k}', top, rnd.uniform(0.12, 0.175),
                                            tilt=(rnd.uniform(-0.35, 0.35), rnd.uniform(-0.35, 0.35)), cup=0.035, seed=g * 10 + 5 + k))
                    parts.append(stalk(f'TY03_S{stage}_{g}_US{k}', top - Vector((0, 0, 0.003)), SOIL_BASE, seed=g * 7 + k))
            if stage >= 3:
                top = Vector((gx + 0.04, gy - 0.03, WATER_Z + 0.5))
                parts.append(stalk(f'TY03_S{stage}_{g}_FS', top, SOIL_BASE, r=0.006, bend=0.02, seed=g))
                parts.append(bud(f'TY03_S{stage}_{g}_Bud', top) if stage == 3 else bloom(f'TY03_S{stage}_{g}_Bloom', top, seed=g))
        for o in list(Q.ACTIVE['coll'].objects):
            if o.name.startswith(f'TY03_S{stage}_'):
                o['qa_node'] = f'S{stage}'
        shift_module(f'S{stage}', 2.6 * (stage - 1))


# ====================================================================== TY04 old stone lantern (shoudeng)
def m_lantern_stone(name='LanternStone'):
    """Grey-blue weathered stone; on the base block's -Y face a small, shallow crescent with a chipped corner
    (the 'broken moon'): a few cm, only in the normal map and a slight darkening, never highlighted."""
    m = Q.m_stone(name, light=(0.16, 0.175, 0.17), dark=(0.055, 0.062, 0.06), scale=1.8, speck=0.9, chisel=1.3)
    nt = m.node_tree
    lc = Q.sep(nt, Q.attr(nt, 'qa_lc'))
    face = Q.math_(nt, 'MULTIPLY', Q.attr(nt, 'qa_mark', 'fac'), Q.math_(nt, 'LESS_THAN', lc[1], -0.2))
    dx = Q.math_(nt, 'SUBTRACT', lc[0], 0.1)
    dz = Q.math_(nt, 'SUBTRACT', lc[2], -0.06)
    d1 = Q.math_(nt, 'SQRT', Q.math_(nt, 'ADD', Q.math_(nt, 'POWER', dx, 2.0), Q.math_(nt, 'POWER', dz, 2.0)))
    d2 = Q.math_(nt, 'SQRT', Q.math_(nt, 'ADD', Q.math_(nt, 'POWER', Q.math_(nt, 'SUBTRACT', dx, 0.009), 2.0),
                                     Q.math_(nt, 'POWER', Q.math_(nt, 'SUBTRACT', dz, 0.007), 2.0)))
    crescent = Q.math_(nt, 'MULTIPLY', Q.math_(nt, 'LESS_THAN', d1, 0.022), Q.math_(nt, 'GREATER_THAN', d2, 0.019))
    chip = Q.math_(nt, 'LESS_THAN', Q.math_(nt, 'ADD', dx, dz), 0.022)          # one horn broken off
    mark = Q.math_(nt, 'MULTIPLY', Q.math_(nt, 'MULTIPLY', crescent, chip), face)
    alb = next(n for n in nt.nodes if n.type == 'REROUTE' and n.name == 'CH_albedo')
    Q.L(nt, Q.mix(nt, Q.math_(nt, 'MULTIPLY', mark, 0.35), alb.inputs[0].links[0].from_socket, (0.04, 0.045, 0.043)), alb.inputs[0])
    bump = next(n for n in nt.nodes if n.type == 'BUMP')
    h = bump.inputs['Height'].links[0].from_socket
    Q.L(nt, Q.math_(nt, 'SUBTRACT', h, Q.math_(nt, 'MULTIPLY', mark, 1.5)), bump.inputs['Height'])
    return add_moss(m, 0.7, (0.5, 0.9), cover=(0.38, 0.58))


def m_paper(name='LanternPaper'):
    """Aged paper screen: fibres, water stains, darker toward the frame; emission (warm gold, spec accent) is baked into
    the Emissive map and scaled at run time for the five brightness levels."""
    m, nt, b = Q.new_mat(name)
    co = Q.coords(nt, (1, 1, 1))
    fib = Q.noise(nt, Q.coords(nt, (1, 1, 8)), 90.0, 3)
    stain = Q.smooth(nt, Q.noise(nt, co, 5.0, 4), 0.55, 0.7)
    col = Q.mix(nt, Q.smooth(nt, fib, 0.3, 0.8), (0.50, 0.45, 0.34), (0.62, 0.57, 0.45))
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', stain, 0.35), col, (0.36, 0.30, 0.20))
    emit = Q.mix(nt, Q.math_(nt, 'MULTIPLY', stain, 0.35), lin('#E8C877'), (0.55, 0.38, 0.16))
    return Q.finish(m, nt, b, col, 0.85, 0.0, fib, 0.0004, 0.4, emit=emit)


def roof(name, half, z0, rise, lift, thick, mat):
    """Small pyramidal stone cap with up-turned corners (curved like a tiny roof)."""
    n = 20
    bm = bmesh.new()
    vs = [[None] * (n + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        for j in range(n + 1):
            x, y = -half + 2 * half * i / n, -half + 2 * half * j / n
            m_ = max(abs(x), abs(y)) / half
            corner = (min(abs(x), abs(y)) / half) ** 2
            z = z0 + rise * (1 - m_) ** 1.3 + lift * corner * m_ ** 3
            vs[i][j] = bm.verts.new((x, y, z))
    for i in range(n):
        for j in range(n):
            bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]))
    o = Q._obj(name, bm, mat, sharp=50)
    s = o.modifiers.new('Solid', 'SOLIDIFY')
    s.thickness = thick
    s.offset = -1
    Q.apply_mods(o)
    Q.add_bevel(o, 0.008, 2, angle=50)
    return o


def build_TY04():
    st, wood = LSTONE, LWOOD
    plinth = Q.box('TY04_Plinth', (0.6, 0.6, 0.08), (0, 0, 0.04), st, bevel=0.012, bseg=2)
    base = Q.box('TY04_Base', (0.48, 0.48, 0.36), (0, 0, 0.26), st, bevel=0.02, bseg=3)
    set_vattr(base, 'qa_mark', lambda co: 1.0)
    chip = Q.box('TY04_Chip', (0.12, 0.12, 0.12), (0.25, -0.25, 0.43), None, bevel=0.0, rot=(0.4, 0.3, 0.7))
    Q.boolean(base, chip)                                  # the chipped corner
    Q.box('TY04_BaseCap', (0.42, 0.42, 0.06), (0, 0, 0.47), st, bevel=0.012)
    Q.cyl('TY04_Post', 0.115, 0.5, (0, 0, 0.75), st, segs=8, bevel=0.01)
    Q.box('TY04_Collar', (0.3, 0.3, 0.05), (0, 0, 1.025), st, bevel=0.01)
    Q.box('TY04_Shelf', (0.46, 0.46, 0.07), (0, 0, 1.085), st, bevel=0.014)
    z0, z1, hw = 1.12, 1.42, 0.17                           # lantern chamber
    for sx in (-1, 1):
        for sy in (-1, 1):
            Q.box(f'TY04_FramePost_{sx}_{sy}', (0.04, 0.04, z1 - z0), (sx * hw, sy * hw, (z0 + z1) / 2), wood, bevel=0.004)
    for z in (z0 + 0.02, z1 - 0.02):
        for k, (sx, sy, sz) in enumerate(((2 * hw, 0.035, 0.035), (0.035, 2 * hw, 0.035))):
            for s in (-1, 1):
                loc = (0, s * hw, z) if k == 0 else (s * hw, 0, z)
                Q.box(f'TY04_Rail_{z:.2f}_{k}_{s}', (sx, sy, sz), loc, wood, bevel=0.003)
    for face in range(4):                                   # paper screens and their lattice, one per side
        a = face * math.pi / 2
        n = Vector((math.cos(a - math.pi / 2), math.sin(a - math.pi / 2), 0))
        t = Vector((-n.y, n.x, 0))
        pc = n * (hw - 0.006) + Vector((0, 0, (z0 + z1) / 2))
        pp = Q.box(f'TY04_Paper_{face}', (2 * hw - 0.04, 0.004, z1 - z0 - 0.07), pc, PAPER, bevel=0.0, rot=(0, 0, a))
        set_vattr(pp, 'qa_glow', lambda co: 1.0)
        for u in (-1, 1):                                    # two vertical and two horizontal lattice bars
            Q.box(f'TY04_LatV_{face}_{u}', (0.012, 0.014, z1 - z0 - 0.07), pc + n * 0.008 + t * u * hw / 3, wood, bevel=0.002, rot=(0, 0, a))
            Q.box(f'TY04_LatH_{face}_{u}', (2 * hw - 0.04, 0.014, 0.012), pc + n * 0.008 + Vector((0, 0, u * (z1 - z0) / 6)), wood, bevel=0.002, rot=(0, 0, a))
    Q.box('TY04_Lid', (0.4, 0.4, 0.04), (0, 0, z1 + 0.02), st, bevel=0.01)
    roof('TY04_Roof', 0.31, z1 + 0.04, 0.12, 0.07, 0.045, st)
    Q.lathe('TY04_Finial', [(0, 0), (0.05, 0.0), (0.035, 0.03), (0.05, 0.05), (0.055, 0.08), (0.04, 0.11), (0.012, 0.135), (0, 0.14)], st, segs=16)
    bpy.data.objects['TY04_Finial'].location = (0, 0, z1 + 0.15)


# ====================================================================== shared helpers for TY05-TY10
def clip_poly(poly, a, b):
    """Keep the part of a convex polygon closer to point a than to point b (Voronoi half-plane)."""
    a, b = Vector(a), Vector(b)
    n, m = b - a, (a + b) / 2
    out = []
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        dp, dq = (p - m).dot(n), (q - m).dot(n)
        if dp <= 0:
            out.append(p)
        if dp * dq < 0:
            out.append(p + (q - p) * (dp / (dp - dq)))
    return out


def slab(name, outline, z0, z1, mat, inset=0.0, bev=0.012, tilt=(0.0, 0.0), seed=0):
    """Stone slab from a convex 2-D outline (x, y), shrunk by `inset` toward its centroid for the joint, top bevelled."""
    c = sum(outline, Vector((0, 0))) / len(outline)
    pts = [c + (p - c) * max(0.0, 1 - inset / max(1e-6, (p - c).length)) for p in outline]
    bm = bmesh.new()
    lo = [bm.verts.new((p.x, p.y, z0)) for p in pts]
    hi = [bm.verts.new((p.x, p.y, z1)) for p in pts]
    bm.faces.new(lo[::-1])
    bm.faces.new(hi)
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = Q._obj(name, bm, mat, smooth=False)
    Q.add_bevel(o, bev, 2, angle=50)
    Q.apply_mods(o)
    sub = o.modifiers.new('Sub', 'SUBSURF')                 # a few more vertices so the top can wear unevenly
    sub.subdivision_type = 'SIMPLE'
    sub.levels = 1
    Q.apply_mods(o)
    rnd = random.Random(seed)
    off = Vector((rnd.uniform(0, 50), rnd.uniform(0, 50), 0))
    for v in o.data.vertices:                               # worn, slightly domed top
        if v.co.z > z1 - 0.002:
            v.co.z += 0.004 * noise.noise(v.co * 6 + off) - 0.003
    if tilt != (0.0, 0.0):
        o.data.transform(Matrix.Translation((c.x, c.y, z1)) @ Matrix.Rotation(tilt[0], 4, 'X') @ Matrix.Rotation(tilt[1], 4, 'Y')
                         @ Matrix.Translation((-c.x, -c.y, -z1)))
    for v in o.data.vertices:
        v.co.z = max(v.co.z, 0.0)
    o.data.update()
    return o


def tufts(prefix, spots, h=(0.05, 0.12), seed=0, mat=None):
    """Small grass tufts (joint grass, path edges), baked like the crops."""
    rnd = random.Random(seed)
    out = []
    for k, (x, y, z) in enumerate(spots):
        bm = bmesh.new()
        lay = {'t': bm.verts.layers.float.new('qa_t'), 'x': bm.verts.layers.float.new('qa_x'), 'g': bm.verts.layers.float.new('qa_glow')}
        n = rnd.randint(5, 9)
        H = rnd.uniform(*h)
        for i in range(n):
            blade(bm, lay, Vector((x, y, z)), TAUi * i / n + rnd.uniform(-0.5, 0.5), H * rnd.uniform(0.7, 1.15), 0.006,
                  rnd.uniform(0.15, 0.6), rnd.uniform(0.3, 1.2), rnd.uniform(-0.5, 0.5), 3)
        out.append(Q._obj(f'{prefix}_{k}', bm, mat or GRASS, sharp=89))
    return out


def tag(prefix, node):
    for o in Q.ACTIVE['coll'].objects:
        if o.name.startswith(prefix):
            o['qa_node'] = node


def m_worn_stone(name='PracticeStone'):
    """Practice slabs: grey-blue stone, polished paler and smoother toward the centre (qa_r = distance from the post)."""
    m = Q.m_stone(name, light=(0.15, 0.165, 0.16), dark=(0.05, 0.057, 0.055), scale=1.4, speck=0.8, chisel=1.2)
    nt = m.node_tree
    r = Q.attr(nt, 'qa_r', 'fac')
    worn = Q.math_(nt, 'SUBTRACT', 1.0, Q.smooth(nt, r, 0.35, 1.05))
    scuff = Q.math_(nt, 'MULTIPLY', Q.smooth(nt, Q.noise(nt, Q.coords(nt, (1, 1, 1)), 30.0, 3), 0.5, 0.7), Q.smooth(nt, r, 0.2, 0.5))
    alb = next(n for n in nt.nodes if n.type == 'REROUTE' and n.name == 'CH_albedo')
    src = alb.inputs[0].links[0].from_socket
    Q.L(nt, Q.mix(nt, Q.math_(nt, 'MULTIPLY', Q.math_(nt, 'MAXIMUM', worn, Q.math_(nt, 'MULTIPLY', scuff, worn)), 0.55), src, (0.27, 0.28, 0.265)), alb.inputs[0])
    rr = next(n for n in nt.nodes if n.type == 'REROUTE' and n.name == 'CH_rough')
    Q.L(nt, Q.mixf(nt, worn, rr.inputs[0].links[0].from_socket, 0.45), rr.inputs[0])
    return add_moss(m, 0.5, (0.6, 0.95), cover=(0.5, 0.66))


# ====================================================================== TY05 practice floor, two layouts
PRACTICE_HALF = 1.5


def practice_layout_A():
    rnd = random.Random(51)
    seeds = [Vector((0, 0))]
    for k in range(8):
        a = TAUi * k / 8 + rnd.uniform(-0.1, 0.1)
        seeds.append(Vector((0.55 * math.cos(a), 0.55 * math.sin(a))))
    for k in range(13):
        a = TAUi * k / 13 + rnd.uniform(-0.15, 0.15)
        seeds.append(Vector((1.15 * math.cos(a), 1.15 * math.sin(a))))
    for sx in (-1, 1):
        for sy in (-1, 1):
            seeds.append(Vector((sx * 1.32, sy * 1.32)))
    sq = [Vector((-PRACTICE_HALF, -PRACTICE_HALF)), Vector((PRACTICE_HALF, -PRACTICE_HALF)), Vector((PRACTICE_HALF, PRACTICE_HALF)), Vector((-PRACTICE_HALF, PRACTICE_HALF))]
    cells = []
    for i, s in enumerate(seeds):
        poly = list(sq)
        for j, t in enumerate(seeds):
            if i != j:
                poly = clip_poly(poly, s, t)
        cells.append(poly)
    return cells


def practice_layout_B():
    rnd = random.Random(52)
    cells = []
    rows = [(-1.5, -0.95), (-0.95, -0.45), (0.45, 0.95), (0.95, 1.5)]
    for r, (y0, y1) in enumerate(rows):
        x = -1.5 + (0.0 if r % 2 else -0.35)
        while x < 1.5:
            w = rnd.uniform(0.6, 0.9)
            x0, x1 = max(-1.5, x), min(1.5, x + w)
            if x1 - x0 > 0.15:
                cells.append([Vector((x0, y0)), Vector((x1, y0)), Vector((x1, y1)), Vector((x0, y1))])
            x += w
    for x0, x1 in ((-1.5, -0.45), (0.45, 1.5)):          # the middle band beside the cobble square
        mid = (x0 + x1) / 2 + rnd.uniform(-0.1, 0.1)
        for a, b in ((x0, mid), (mid, x1)):
            cells.append([Vector((a, -0.45)), Vector((b, -0.45)), Vector((b, 0.45)), Vector((a, 0.45))])
    cob = []
    n = 8
    for i in range(n):
        for j in range(n):
            x0, y0 = -0.45 + 0.9 * i / n, -0.45 + 0.9 * j / n
            if abs(x0 + 0.05625) < 0.17 and abs(y0 + 0.05625) < 0.17:
                continue                                        # the post stands here
            cob.append([Vector((x0, y0)), Vector((x0 + 0.1125, y0)), Vector((x0 + 0.1125, y0 + 0.1125)), Vector((x0, y0 + 0.1125))])
    return cells, cob


def build_TY05():
    rnd = random.Random(55)
    for layout in ('A', 'B'):
        if layout == 'A':
            cells, cob = practice_layout_A(), []
        else:
            cells, cob = practice_layout_B()
        crack = 3 if layout == 'A' else 5
        sunk = 7 if layout == 'A' else 2
        for k, poly in enumerate(cells):
            tilt = (rnd.uniform(-0.012, 0.012), rnd.uniform(-0.012, 0.012))
            z1 = 0.05 - (0.015 if k == sunk else 0.0)
            if k == crack:                                        # one slab split in two along a crooked line
                c = sum(poly, Vector((0, 0))) / len(poly)
                a, b = c + Vector((0.3, 0.2)), c - Vector((0.3, 0.05))
                for h, (p, q) in enumerate(((a, b), (b, a))):
                    slab(f'TY05{layout}_Slab_{k}_{h}', clip_poly(poly, p, q), 0.0, z1, PSTONE, inset=0.014, tilt=tilt, seed=k * 3 + h)
            else:
                slab(f'TY05{layout}_Slab_{k}', poly, 0.0, z1, PSTONE, inset=0.012, tilt=tilt, seed=k)
        for k, poly in enumerate(cob):
            slab(f'TY05{layout}_Cobble_{k}', poly, 0.0, 0.045, PSTONE, inset=0.009, bev=0.01, tilt=(rnd.uniform(-0.03, 0.03), rnd.uniform(-0.03, 0.03)), seed=200 + k)
        Q.box(f'TY05{layout}_Bedding', (2.98, 2.98, 0.02), (0, 0, 0.01), JOINT, bevel=0.004)     # dark joint earth under the slabs
        spots = []
        for k in range(40):                                       # joint grass, mostly toward the edges
            a = rnd.uniform(0, TAUi)
            r = rnd.uniform(0.95, 1.45)
            x, y = max(-1.45, min(1.45, r * math.cos(a))), max(-1.45, min(1.45, r * math.sin(a)))
            spots.append((x, y, 0.02))
        tufts(f'TY05{layout}_Grass', spots, (0.03, 0.08), seed=5 + len(layout))
        for o in Q.ACTIVE['coll'].objects:
            if o.name.startswith(f'TY05{layout}_'):
                set_vattr(o, 'qa_r', lambda co, o=o: (o.matrix_world @ co).to_2d().length)
        tag(f'TY05{layout}_', f'Layout{layout}')
        shift_module(f'Layout{layout}', 0.0 if layout == 'A' else 3.4)
    SOCKETS.append(dict(name='SOCKET_post', loc=[0.0, 0.0, 0.05], forward=[0.0, -1.0, 0.0]))


# ====================================================================== TY06 training equipment
def build_TY06():
    # stone lock: a padlock-shaped granite weight with a worn handle
    body = Q.box('TY06L_Body', (0.35, 0.17, 0.2), (0, 0, 0.1), TSTONE, bevel=0.035, bseg=4)
    Q.jitter(body, 0.003, seed=61)
    hd = Q.box('TY06L_Handle', (0.26, 0.09, 0.15), (0, 0, 0.255), TSTONE, bevel=0.03, bseg=3)
    hole = Q.box('TY06L_Hole', (0.15, 0.3, 0.075), (0, 0, 0.255), None, bevel=0.0)
    Q.boolean(hd, hole)
    tag('TY06L_', 'StoneLock')
    shift_module('StoneLock', 0.0)
    # stone barbell: two stone wheels on a wooden pole, rope wraps at the wheels
    for s in (-1, 1):
        w = Q.cyl(f'TY06B_Wheel_{s}', 0.225, 0.12, (s * 0.62, 0, 0.225), TSTONE, segs=32, bevel=0.025, rot=(0, math.pi / 2, 0))
        Q.jitter(w, 0.004, seed=62 + s)
        Q.cyl(f'TY06B_Hub_{s}', 0.05, 0.13, (s * 0.62, 0, 0.225), BRONZE, segs=16, bevel=0.006, rot=(0, math.pi / 2, 0))
        for k in range(3):
            Q.torus(f'TY06B_Rope_{s}_{k}', 0.04, 0.009, (s * (0.5 - k * 0.018), 0, 0.225), ROPE, major=16, minor=6, rot=(0, math.pi / 2, 0))
    Q.rod('TY06B_Pole', (-0.75, 0, 0.225), (0.75, 0, 0.225), 0.032, TWOOD, segs=14, bevel=0.006)
    tag('TY06B_', 'StoneBarbell')
    shift_module('StoneBarbell', 1.3)
    # weapon rack: two A-frames on skids, two rails, a staff, a practice sword and a spear standing in it
    for s in (-1, 1):
        x = s * 0.55
        Q.rod(f'TY06R_LegF_{s}', (x, -0.3, 0), (x, -0.02, 1.4), 0.03, TWOOD, segs=10, bevel=0.005)
        Q.rod(f'TY06R_LegB_{s}', (x, 0.3, 0), (x, 0.02, 1.4), 0.03, TWOOD, segs=10, bevel=0.005)
        Q.box(f'TY06R_Skid_{s}', (0.07, 0.75, 0.06), (x, 0, 0.03), TWOOD, bevel=0.008)
        for z in (0.55, 1.15):
            Q.torus(f'TY06R_Lash_{s}_{z}', 0.045, 0.008, (x, -0.3 + 0.28 * z / 1.4, z), ROPE, major=14, minor=5, rot=(math.pi / 2 - 0.2, 0, 0))
    for z, y in ((1.22, -0.05), (0.55, -0.18), (0.12, -0.05)):
        Q.rod(f'TY06R_Rail_{z}', (-0.62, y, z), (0.62, y, z), 0.025, TWOOD, segs=10, bevel=0.004)
    Q.rod('TY06R_Staff', (-0.3, -0.07, 0.06), (-0.33, -0.1, 1.75), 0.018, TWOOD, segs=10, bevel=0.004)
    Q.box('TY06R_SwordBlade', (0.045, 0.012, 0.75), (0.0, -0.08, 0.5), TWOOD, bevel=0.004)
    Q.box('TY06R_SwordGuard', (0.13, 0.03, 0.025), (0.0, -0.08, 0.89), TWOOD, bevel=0.004)
    Q.cyl('TY06R_SwordHilt', 0.016, 0.2, (0.0, -0.08, 1.0), ROPE, segs=10)
    Q.rod('TY06R_SpearShaft', (0.3, -0.07, 0.06), (0.32, -0.1, 1.68), 0.016, TWOOD, segs=10, bevel=0.004)
    Q.lathe('TY06R_SpearHead', [(0, 0), (0.014, 0.0), (0.022, 0.04), (0.012, 0.13), (0, 0.16)], IRON, segs=4)
    bpy.data.objects['TY06R_SpearHead'].location = (0.32, -0.1, 1.67)
    Q.cyl('TY06R_SpearTassel', 0.03, 0.06, (0.32, -0.1, 1.64), TASSEL, segs=10, r2=0.012)
    tag('TY06R_', 'WeaponRack')
    shift_module('WeaponRack', 3.2)


# ====================================================================== TY07 fence modules
POST, POST_H, RAILS = 0.12, 1.16, (0.32, 0.88)


def fence_post(name, x, y=0.0, h=POST_H):
    p = Q.box(name, (POST, POST, h), (x, y, h / 2), FWOOD, bevel=0.012)
    Q.jitter(p, 0.003, seed=hash(name) % 97)
    Q.box(f'{name}_Cap', (POST + 0.02, POST + 0.02, 0.03), (x, y, h + 0.012), FWOOD, bevel=0.008)
    return p


def base_stones(prefix, x0, x1, seed, every=0.32):
    rnd = random.Random(seed)
    x = x0 + 0.1
    k = 0
    while x < x1 - 0.1:
        if rnd.random() < 0.75:
            boulder(f'{prefix}_{k}', (rnd.uniform(0.07, 0.11), rnd.uniform(0.06, 0.08), rnd.uniform(0.05, 0.08)),
                    (x, rnd.uniform(-0.04, 0.04), 0.03), FSTONE, seed=seed + k, subd=2, rough=0.25, ground=0.0)
        x += every * rnd.uniform(0.7, 1.2)
        k += 1


def slats(prefix, x0, x1, seed):
    """Split-bamboo slats lashed to the two rails, tops uneven."""
    rnd = random.Random(seed)
    x = x0 + 0.08
    k = 0
    while x < x1 - 0.05:
        top = 1.0 + rnd.uniform(-0.05, 0.08)
        Q.pole(f'{prefix}_{k}', (x, -0.035, 0.05), (x + rnd.uniform(-0.01, 0.01), -0.035, top), rnd.uniform(0.018, 0.024), FBAMBOO, segs=8, node_every=0.32)
        x += rnd.uniform(0.055, 0.07)
        k += 1
    for z in RAILS:
        Q.rod(f'{prefix}_Rail_{z}', (x0, 0.02, z), (x1, 0.02, z), 0.028, FWOOD, segs=8, bevel=0.004)


def wattle(prefix, x0, x1, seed):
    """Woven bamboo wattle: upright stakes with thin withies weaving over and under them."""
    rnd = random.Random(seed)
    stakes = [x0 + 0.1 + i * (x1 - x0 - 0.2) / 7 for i in range(8)]
    for k, x in enumerate(stakes):
        Q.pole(f'{prefix}_Stake_{k}', (x, 0, 0.0), (x, 0, 1.02 + rnd.uniform(-0.03, 0.03)), 0.017, FBAMBOO, segs=8, node_every=0.35)
    for row in range(16):
        z = 0.16 + row * 0.054
        ph = row % 2
        pts = [Vector((x0 + 0.06, 0.0, z))]
        for k, x in enumerate(stakes):
            pts.append(Vector((x, 0.022 * (1 if (k + ph) % 2 else -1), z + rnd.uniform(-0.004, 0.004))))
        pts.append(Vector((x1 - 0.06, 0.0, z)))
        Q.tube(f'{prefix}_Withy_{row}', pts, 0.009, FBAMBOO, segs=6, res=3)
    for z in RAILS:
        Q.rod(f'{prefix}_Rail_{z}', (x0, 0.04, z), (x1, 0.04, z), 0.025, FWOOD, segs=8, bevel=0.004)


def build_TY07():
    # every straight carries the post at its start (-L/2); END closes a run with the last post; CORNER is a post with two half-spans
    mods = [('StraightA', 2.0), ('StraightB', 2.0), ('Straight1m', 1.0)]
    x = 0.0
    for nm, L in mods:
        fence_post(f'TY07{nm}_Post', -L / 2)
        if nm == 'StraightB':
            wattle(f'TY07{nm}_W', -L / 2 + POST / 2, L / 2, 71)
        else:
            slats(f'TY07{nm}_S', -L / 2 + POST / 2, L / 2, 70 + int(L))
        base_stones(f'TY07{nm}_Stone', -L / 2, L / 2, 75 + int(L * 10))
        tag(f'TY07{nm}_', nm)
        shift_module(nm, x)
        x += L + 0.8
    fence_post('TY07Corner_Post', 0.0)
    tag('TY07Corner_', 'Corner')
    shift_module('Corner', x)
    x += 1.0
    fence_post('TY07End_Post', 0.0)
    Q.rod('TY07End_Brace', (0.06, 0.0, 0.95), (0.42, 0.0, 0.04), 0.03, FWOOD, segs=8, bevel=0.004)
    base_stones('TY07End_Stone', 0.0, 0.5, 79)
    tag('TY07End_', 'End')
    shift_module('End', x)
    x += 1.5
    # gate: posts 1.0 m apart (frame) + a separate leaf hinged on the -X post
    fence_post('TY07GateFrame_PostL', -0.5)
    fence_post('TY07GateFrame_PostR', 0.5)
    tag('TY07GateFrame_', 'GateFrame')
    shift_module('GateFrame', x)
    lw, lh = 0.86, 1.0
    for k, sx in enumerate((-1, 1)):
        Q.box(f'TY07GateLeaf_Stile_{k}', (0.05, 0.05, lh), (sx * (lw / 2 - 0.025), 0, 0.08 + lh / 2), FWOOD, bevel=0.006)
    for z in (0.1, 0.06 + lh):
        Q.box(f'TY07GateLeaf_Rail_{z:.2f}', (lw, 0.05, 0.05), (0, 0, z), FWOOD, bevel=0.006)
    Q.rod('TY07GateLeaf_Brace', (-lw / 2 + 0.05, 0.03, 0.13), (lw / 2 - 0.05, 0.03, lh + 0.03), 0.022, FWOOD, segs=8, bevel=0.004)
    Q.box('TY07GateLeaf_Wicker', (lw - 0.1, 0.02, lh - 0.06), (0, -0.005, 0.08 + lh / 2), WEAVE, bevel=0.0)
    for z in (0.25, 0.9):
        Q.cyl(f'TY07GateLeaf_Hinge_{z}', 0.02, 0.07, (-0.5 + 0.06, 0, z), IRON, segs=10)
    tag('TY07GateLeaf_', 'GateLeaf')
    shift_module('GateLeaf', x)
    SOCKETS.append(dict(name='SOCKET_gate_hinge', loc=[-0.44, 0.0, 0.0], forward=[0.0, -1.0, 0.0]))


def fence_corner_fixup(nodes, obj):
    """Corner: two half-length straight-A spans at 90 deg are left to placement; the leaf pivots on its hinge."""
    for n in nodes:
        if n.name == f'{obj}_GateLeaf_LOD0':
            n.data.transform(Matrix.Translation((0.44, 0, 0)))  # hinge axis at the node origin
            n.location.x = -0.44


# ====================================================================== TY08 herb drying rack
def herb_bundle(name, top, length, seed):
    rnd = random.Random(seed)
    bm = bmesh.new()
    lay = {'t': bm.verts.layers.float.new('qa_t'), 'x': bm.verts.layers.float.new('qa_x'), 'g': bm.verts.layers.float.new('qa_glow')}
    for i in range(14):                                    # stems hang down from the tie and splay a little
        yaw = TAUi * i / 14 + rnd.uniform(-0.3, 0.3)
        blade(bm, lay, Vector(top), yaw, length * rnd.uniform(0.7, 1.0), 0.016, math.pi - rnd.uniform(0.1, 0.35), -rnd.uniform(0.0, 0.3),
              rnd.uniform(-0.6, 0.6), 4)
    o = Q._obj(name, bm, HERB, sharp=89)
    Q.torus(f'{name}_Tie', 0.018, 0.006, (top[0], top[1], top[2] - 0.03), ROPE, major=12, minor=5)
    Q.rod(f'{name}_String', (top[0], top[1], top[2] + 0.05), (top[0], top[1], top[2] - 0.03), 0.003, ROPE, segs=4)
    return o


def build_TY08():
    L, D, H = 1.9, 0.7, 1.7
    for s in (-1, 1):
        x = s * (L / 2 - 0.05)
        Q.pole(f'TY08R_LegF_{s}', (x, -D / 2, 0), (x, 0.0, H), 0.026, RBAMBOO, segs=10, node_every=0.35)
        Q.pole(f'TY08R_LegB_{s}', (x, D / 2, 0), (x, 0.0, H), 0.026, RBAMBOO, segs=10, node_every=0.35)
        Q.pole(f'TY08R_Cross_{s}', (x, -0.22, 0.45), (x, 0.22, 0.45), 0.02, RBAMBOO, segs=8, node_every=0.4)
        for z in (0.45, 1.05, 1.62):
            Q.torus(f'TY08R_Lash_{s}_{z}', 0.04, 0.008, (x, 0, z), ROPE, major=14, minor=5, rot=(0, math.pi / 2, 0))
    for z, y in ((1.62, 0.0), (1.33, 0.0), (1.05, 0.0)):
        Q.pole(f'TY08R_Bar_{z}', (-L / 2, y, z), (L / 2, y, z), 0.021, RBAMBOO, segs=10, node_every=0.45)
    for y in (-0.2, 0.2):
        Q.pole(f'TY08R_Shelf_{y}', (-L / 2 + 0.05, y, 0.45), (L / 2 - 0.05, y, 0.45), 0.02, RBAMBOO, segs=8, node_every=0.45)
    for k, x in enumerate((-0.42, 0.42)):
        sv = Q.lathe(f'TY08R_Sieve_{k}', [(0, 0), (0.36, 0.0), (0.38, 0.05), (0.36, 0.05), (0.34, 0.012), (0, 0.012)], SIEVE, segs=36)
        sv.location = (x, 0, 0.47)
    tag('TY08R_', 'Rack')
    rnd = random.Random(81)
    for bar_z in (1.62, 1.33):
        for k in range(6):
            x = -0.75 + k * 0.3 + rnd.uniform(-0.04, 0.04)
            herb_bundle(f'TY08H_Bundle_{bar_z}_{k}', (x, 0.0, bar_z - 0.04), rnd.uniform(0.25, 0.4), seed=int(bar_z * 100) + k)
    for k, x in enumerate((-0.42, 0.42)):                       # loose leaves drying on the sieves
        for i in range(10):
            a, r = rnd.uniform(0, TAUi), rnd.uniform(0, 0.3)
            lf = Q.box(f'TY08H_Leaf_{k}_{i}', (0.06, 0.025, 0.004), (x + r * math.cos(a), r * math.sin(a), 0.488), HERB, bevel=0.0,
                       rot=(0, 0, rnd.uniform(0, math.pi)))
            set_vattr(lf, 'qa_t', lambda co: 0.6)
    tag('TY08H_', 'Herbs')


# ====================================================================== TY09 household clutter
def build_TY09():
    x = 0.0
    # water jar with a wooden lid and a gourd ladle
    Q.lathe('TY09J_Jar', [(0, 0), (0.16, 0.0), (0.24, 0.12), (0.28, 0.3), (0.25, 0.48), (0.19, 0.56), (0.2, 0.58), (0.17, 0.58), (0.16, 0.54), (0, 0.54)], JAR, segs=40)
    Q.cyl('TY09J_Lid', 0.215, 0.03, (0, 0, 0.6), TWOOD, segs=32, bevel=0.006)
    for k in (-1, 1):
        Q.box(f'TY09J_LidBatten_{k}', (0.36, 0.04, 0.02), (0, k * 0.08, 0.625), TWOOD, bevel=0.004)
    g = Q.lathe('TY09J_Gourd', [(0, 0), (0.045, 0.02), (0.05, 0.05), (0.03, 0.085), (0.032, 0.11), (0.012, 0.14), (0, 0.14)], GOURD, segs=16)
    g.location, g.rotation_euler = (0.05, 0.02, 0.665), (math.radians(80), 0, 0.6)
    tag('TY09J_', 'WaterJar')
    shift_module('WaterJar', x)
    x += 1.0
    Q.lathe('TY09K_Basket', [(0, 0), (0.12, 0.0), (0.16, 0.06), (0.18, 0.3), (0.185, 0.33), (0.17, 0.33), (0.165, 0.3), (0.145, 0.06), (0, 0.012)], BASKETW, segs=32)
    Q.torus('TY09K_Rim', 0.18, 0.012, (0, 0, 0.33), RBAMBOO, major=32, minor=6)
    tag('TY09K_', 'Basket')
    shift_module('Basket', x)
    x += 0.8
    Q.rod('TY09H_Handle', (0, 0, 0.0), (0, 0.42, 1.33), 0.019, TWOOD, segs=10, bevel=0.004)          # leans on a fence behind it
    Q.box('TY09H_Blade', (0.15, 0.17, 0.008), (0, 0.33, 1.3), IRON, bevel=0.003, rot=(math.radians(52), 0, 0))     # flat blade hanging forward of the socket
    Q.cyl('TY09H_Socket', 0.026, 0.06, (0, 0.42, 1.36), IRON, segs=10, rot=(math.radians(-18), 0, 0))
    tag('TY09H_', 'Hoe')
    shift_module('Hoe', x)
    x += 0.8
    prof = [(0, 0), (0.15, 0.0), (0.17, 0.02), (0.19, 0.44), (0.175, 0.45), (0.165, 0.03), (0, 0.025)]
    Q.lathe('TY09B_Bucket', prof, BUCKETW, segs=24)
    for z in (0.08, 0.36):
        Q.torus(f'TY09B_Hoop_{z}', 0.155 + z * 0.08, 0.008, (0, 0, z), IRON, major=32, minor=6)
    for s in (-1, 1):
        Q.box(f'TY09B_Ear_{s}', (0.04, 0.03, 0.12), (s * 0.19, 0, 0.47), BUCKETW, bevel=0.006)
    Q.tube('TY09B_Rope', [Vector((-0.19, 0, 0.5)), Vector((-0.12, 0, 0.66)), Vector((0.12, 0, 0.66)), Vector((0.19, 0, 0.5))], 0.009, ROPE, segs=6)
    tag('TY09B_', 'Bucket')
    shift_module('Bucket', x)
    x += 1.2
    rnd = random.Random(91)
    for s in (-1, 1):
        Q.box(f'TY09W_Post_{s}', (0.06, 0.06, 0.74), (s * 0.48, 0, 0.37), TWOOD, bevel=0.006)
    Q.box('TY09W_Sill', (1.0, 0.38, 0.05), (0, 0, 0.025), TWOOD, bevel=0.006)
    Q.box('TY09W_Roof', (1.08, 0.5, 0.03), (0, -0.02, 0.75), TWOOD, bevel=0.006, rot=(math.radians(-6), 0, 0))
    for row in range(5):
        for k in range(8):
            r = rnd.uniform(0.045, 0.06)
            y = rnd.uniform(-0.01, 0.01)
            z = 0.05 + r + row * 0.125
            xx = -0.4 + k * 0.115 + (0.05 if row % 2 else 0)
            if xx > 0.43:
                continue
            log = Q.cyl(f'TY09W_Log_{row}_{k}', r, 0.34, (xx, y, z), FIREWOOD, segs=7, rot=(math.pi / 2, 0, rnd.uniform(0, 1)))
            Q.jitter(log, 0.004, seed=row * 10 + k)
    tag('TY09W_', 'Woodpile')
    shift_module('Woodpile', x)
    x += 1.0
    Q.box('TY09S_Top', (0.34, 0.24, 0.035), (0, 0, 0.29), TWOOD, bevel=0.008)
    for sx in (-1, 1):
        for sy in (-1, 1):
            Q.rod(f'TY09S_Leg_{sx}_{sy}', (sx * 0.15, sy * 0.1, 0.0), (sx * 0.12, sy * 0.08, 0.28), 0.018, TWOOD, segs=8, bevel=0.003)
        Q.rod(f'TY09S_Stretcher_{sx}', (sx * 0.135, -0.09, 0.1), (sx * 0.135, 0.09, 0.1), 0.012, TWOOD, segs=6)
    tag('TY09S_', 'Stool')
    shift_module('Stool', x)


# ====================================================================== TY10 gravel path modules
PATH_W = 1.1


def m_gravel(name='Gravel'):
    """Small grey gravel in dark earth: pebble cells for colour and relief, a little soil showing between them."""
    m, nt, b = Q.new_mat(name)
    co = Q.coords(nt, (1, 1, 1), offset_by_seed=False)
    cell = Q.voronoi(nt, co, 55.0, 'F1')
    edge = Q.voronoi(nt, co, 55.0, 'DISTANCE_TO_EDGE')
    tone = Q.voronoi(nt, co, 55.0, 'F1', out='Color')
    stone = Q.mix(nt, Q.sep(nt, tone)[0], (0.07, 0.075, 0.072), (0.20, 0.20, 0.19))
    col = Q.mix(nt, Q.smooth(nt, edge, 0.0, 0.08), (0.04, 0.03, 0.02), stone)
    big = Q.smooth(nt, Q.noise(nt, co, 4.0, 3), 0.4, 0.7)
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', big, 0.3), col, (0.10, 0.08, 0.055))
    hgt = Q.math_(nt, 'ADD', Q.smooth(nt, edge, 0.0, 0.12), Q.math_(nt, 'MULTIPLY', cell, 0.2))
    return Q.finish(m, nt, b, col, 0.85, 0.0, hgt, 0.006, 1.0)


def path_piece(prefix, L, seed, steps=(), groove=False, end=False):
    rnd = random.Random(seed)
    nx_, ny_ = 22, int(L * 20)
    bm = bmesh.new()
    vs = []
    for j in range(ny_ + 1):
        row = []
        for i in range(nx_ + 1):
            x = -PATH_W / 2 + PATH_W * i / nx_
            y = -L / 2 + L * j / ny_
            if end and y > L / 2 - PATH_W / 2:                 # rounded far end
                dy = y - (L / 2 - PATH_W / 2)
                x *= math.sqrt(max(0.0, 1 - (dy / (PATH_W / 2)) ** 2))
            z = 0.012 + 0.004 * noise.noise(Vector((x * 9, y * 9, seed)))
            if groove:
                z -= 0.006 * math.exp(-(x / 0.18) ** 2)
            z *= smoothstep(PATH_W / 2, PATH_W / 2 - 0.08, abs(x)) * 0.8 + 0.2
            row.append(bm.verts.new((x, y, z)))
        vs.append(row)
    for j in range(ny_):
        for i in range(nx_):
            bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    Q._obj(f'{prefix}_Gravel', bm, GRAVEL, sharp=80)
    k = 0
    for s in (-1, 1):                                          # half-buried edge pebbles
        y = -L / 2 + 0.08
        while y < L / 2 - 0.08 - (PATH_W / 2 if end else 0):
            e = boulder(f'{prefix}_Edge_{k}', (rnd.uniform(0.05, 0.08), rnd.uniform(0.035, 0.05), 0.025), (s * (PATH_W / 2 - 0.04), y, -0.008),
                        FSTONE, seed=seed + k, subd=2, rough=0.15, rot=rnd.uniform(-0.3, 0.3) + math.pi / 2, ground=0.0)
            top = max(v.co.z for v in e.data.vertices)
            if e.location.z + top > 0.019:                       # path rule: nothing above 2 cm; the noise can push a crown higher
                k_ = (0.019 - e.location.z) / top
                for v in e.data.vertices:
                    if v.co.z > 0:
                        v.co.z *= k_
            y += rnd.uniform(0.13, 0.2)
            k += 1
    for i, (sx, sy, rx, ry) in enumerate(steps):              # flat stepping stones, top 2 cm above ground
        pts = [Vector((sx + rx * math.cos(a) * (1 + 0.1 * math.sin(3 * a + i)), sy + ry * math.sin(a) * (1 + 0.1 * math.cos(2 * a + i)))) for a in [TAUi * t / 14 for t in range(14)]]
        slab(f'{prefix}_Step_{i}', pts, 0.0, 0.02, PSTONE, bev=0.008, seed=seed + 50 + i)
    spots = [(s * (PATH_W / 2 + rnd.uniform(-0.03, 0.04)), rnd.uniform(-L / 2 + 0.1, L / 2 - 0.1), 0.0) for s in (-1, 1) for _ in range(int(L * 4))]
    tufts(f'{prefix}_Grass', spots, (0.04, 0.09), seed=seed)


def build_TY10():
    path_piece('TY10A', 2.0, 101, steps=((0.05, -0.45, 0.24, 0.2), (-0.05, 0.45, 0.25, 0.21)))
    tag('TY10A_', 'StraightA')
    shift_module('StraightA', 0.0)
    path_piece('TY10B', 2.0, 102, groove=True)
    tag('TY10B_', 'StraightB')
    shift_module('StraightB', 1.6)
    path_piece('TY10E', 1.1, 103, steps=((0.0, -0.3, 0.32, 0.12),), end=True)
    tag('TY10E_', 'End')
    shift_module('End', 3.2)


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
OFFSETS = {}


def shift_module(nm, dx):
    """Move every source part tagged qa_node == nm by dx along X for the bake; build_asset moves the node back."""
    for o in Q.ACTIVE['coll'].objects:
        if o.get('qa_node') == nm:
            o.location.x += dx
    OFFSETS[nm] = dx


ASSETS = {
    'TY01': dict(build=build_TY01, ref='TY01_three_view.png', name='SpiritField', res=2048, states=('Dry', 'Wet'),
                 category='structure (embedded bed; ground from terrain)', slot=['TY_Field_1 (-2.8, 6.7)', 'TY_Field_2 (2.8, 6.7)'],
                 collision=dict(type='box', size=[2.4, 3.2, 0.3], center=[0, 0, 0.15],
                                note='rim 0.3 m: not meant to be walked through; plant / harvest from the side. Inlet on +X: '
                                     'rotate 180 deg about the vertical for TY_Field_2 so both inlets face the x = 0 path')),
    'TY02': dict(build=build_TY02, ref='TY02_three_view.png', name='QinglingGrass', res=2048, states=None, modules=True, double=True,
                 category='crop stages (placed with TY01, same origin)', slot=['inside TY01'],
                 collision=dict(type='none', note='non-blocking plants; swap S1..S4 by growth t: <0.25 S1, <0.6 S2, <1 S3, >=1 S4'),
                 stage_names=('sprout', 'young', 'grown', 'mature'), stage_h=[STAGES[i]['H'] for i in (1, 2, 3, 4)]),
    'TY03': dict(build=build_TY03, ref='TY03_three_view.png', name='ClearwaterLotus', res=2048, states=None, modules=True, double=True, emit=1.5,
                 category='crop stages (placed with TY01 in its flooded state, same origin)', slot=['inside TY01 (flooded)'],
                 collision=dict(type='none', note='non-blocking plants; same t thresholds as TY02; show TY01 flooded'),
                 stage_names=('floating', 'standing', 'bud', 'bloom'), stage_h=[0.01, 0.35, 0.61, 0.6]),
    'TY04': dict(build=build_TY04, ref='TY04_three_view.png', name='Shoudeng', res=2048, states=None, glow_name='Paper', emit=1.0,
                 category='placed prop', slot=['TY_Lantern (-5.2, 12.0)'],
                 collision=dict(type='box', size=[0.6, 0.6, 1.75], center=[0, 0, 0.875], note='blocks; lantern corner, not climbable')),
    'TY05': dict(build=build_TY05, ref='TY05_three_view.png', name='PracticeFloor', res=2048, states=None, modules=True,
                 category='structure (flush floor; terrain meets its edge)', slot=['TY_Practice (0, 10.8)'],
                 collision=dict(type='box', size=[3.0, 3.0, 0.05], center=[0, 0, 0.025], note='walkable; agility-post (existing model) stands at SOCKET_post')),
    'TY06': dict(build=build_TY06, ref='TY06_three_view.png', name='TrainingGear', res=2048, states=None, modules=True,
                 category='placed props', slot=['beside TY_Practice'],
                 collision=dict(type='per module', note='StoneLock box 0.35 x 0.17 x 0.33; StoneBarbell capsule along X r 0.225; WeaponRack box 1.2 x 0.75 x 1.4')),
    'TY07': dict(build=build_TY07, ref='TY07_three_view.png', name='Fence', res=2048, states=None, modules=True, post_split=fence_corner_fixup,
                 category='structure (modular fence; origin at each module centre, posts at -X end)', slot=['TY_Fence (four sides)'],
                 collision=dict(type='box per module', note='0.12 m thick, 1.1 m high; GateLeaf rotates about its origin (the hinge), open = -100 deg')),
    'TY08': dict(build=build_TY08, ref='TY08_three_view.png', name='HerbRack', res=2048, states=None, modules=True,
                 category='placed prop', slot=['TY_Rack (5.4, 4.0), long side along the fence'],
                 collision=dict(type='box', size=[1.9, 0.7, 1.7], center=[0, 0, 0.85], note='Herbs node: show after a harvest (full), hide when empty')),
    'TY09': dict(build=build_TY09, ref='TY09_three_view.png', name='YardClutter', res=2048, states=None, modules=True,
                 category='placed props', slot=['TY_Corner_R (5.0, 11.5)'],
                 collision=dict(type='per module', note='jar cylinder r 0.28; woodpile box 1.0 x 0.4 x 0.75; basket, bucket, stool, hoe non-blocking')),
    'TY10': dict(build=build_TY10, ref='TY10_three_view.png', name='GravelPath', res=2048, states=None, modules=True,
                 category='structure (path; top <= 2 cm above ground)', slot=['along x = 0 from the back door'],
                 collision=dict(type='none', note='walkable; terrain provides the ground')),
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
    OFFSETS.clear()
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
    gm.use_backface_culling = not a.get('double')
    G.data.materials.clear()
    G.data.materials.append(gm)
    if glow_faces:
        gg = Q.game_material(f"TY_{a['name']}_{a.get('glow_name', 'Glow')}", imgs, alpha, emit_strength=a.get('emit', 2.0))
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
    if a.get('modules'):                             # node 0 ('Body') is empty: every part is tagged with its module / stage
        nodes = [n for n in nodes if len(n.data.polygons)]
        for n in nodes:                              # modules were laid out apart for the bake (no shared AO); bring each to its origin
            nm = n.name[len(obj) + 1:-5]
            if OFFSETS.get(nm):
                n.data.transform(Matrix.Translation((-OFFSETS[nm], 0, 0)))
    if a.get('post_split'):
        a['post_split'](nodes, obj)
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
    if a.get('stage_names'):
        info['stages'] = {f'{obj}_S{i}_LOD0': dict(stage=a['stage_names'][i - 1], t_from=STAGE_T[i - 1], t_to=(STAGE_T[i] if i < 4 else None),
                                                   approx_height_above_bed_m=a['stage_h'][i - 1]) for i in (1, 2, 3, 4)}
        info['glow'] = (f'glowing faces (mature tips / bloom centre) use M_TY_{a["name"]}_Glow (Emissive map, strength {a.get("emit", 2.0)}); '
                        f'every other face uses M_TY_{a["name"]}')
    if aid == 'TY04':
        info['brightness'] = dict(material=f'M_TY_{a["name"]}_Paper', emissive_map=f'T_{aid}_{a["name"]}_Emissive',
                                  levels={'0': 0.0, '1': 0.2, '2': 0.5, '3': 0.9, '4': 1.5},
                                  note='set the material emission strength from the level (0 = unlit .. 4 = warm light); optionally a warm point light '
                                       'at (0, 0, 1.27) m with 0 / 0.3 / 0.8 / 1.6 / 3 W-equivalent. One model, never five.')
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
        o.rotation_mode = 'XYZ'                      # glTF import uses quaternions; the sheets rotate by Euler Z
        o.location = Matrix.Rotation(rot, 3, 'Z') @ o.location + Vector(at)
        o.rotation_euler.z += rot
        out.append(o)
    bpy.context.view_layer.update()
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


def nodes_of(objs, sub):
    return [o for o in objs if sub in o.name]


def arrange(groups, gap=0.5):
    """Lay groups of objects side by side along X (left to right), each group's bbox starting where the last ended."""
    x = 0.0
    for g in groups:
        mn, mx = Q.bbox(g)
        dx = x - mn[0]
        for o in g:
            o.location.x += dx
        x += (mx[0] - mn[0]) + gap
    bpy.context.view_layer.update()
    mn, mx = Q.bbox([o for g in groups for o in g])
    shift = -(mn[0] + mx[0]) / 2
    for g in groups:
        for o in g:
            o.location.x += shift
    bpy.context.view_layer.update()
    return Q.bbox([o for g in groups for o in g])


def four_views(out, objs, fig_gap=0.6):
    """Spec section 8: front / side / back orthographic and a 3/4 perspective (50 mm), each with the 1.75 m figure."""
    mn, mx = Q.bbox(objs)
    fig = scale_figure((mn[0] - fig_gap, (mn[1] + mx[1]) / 2, 0))
    bpy.context.view_layer.update()
    mn, mx = Q.bbox(objs + [fig])
    c = Vector([(mn[i] + mx[i]) / 2 for i in range(3)])
    span = max(mx[0] - mn[0], mx[2] - mn[2], mx[1] - mn[1]) * 1.12
    shot(out / 'ortho_front.png', (c.x, c.y - 40, c.z), c, ortho=span, res=(1600, 1000))
    fig.location = ((mn[0] + mx[0]) / 2, mn[1] - fig_gap, 0)
    bpy.context.view_layer.update()
    side_span = max(mx[1] - mn[1] + 2 * fig_gap, mx[2] - mn[2]) * 1.15
    shot(out / 'ortho_side.png', (c.x + 40, c.y, c.z), (c.x, c.y, c.z), ortho=side_span, res=(1200, 1000))
    fig.location = (mx[0] + fig_gap * 0.5, (mn[1] + mx[1]) / 2, 0)
    shot(out / 'ortho_back.png', (c.x, c.y + 40, c.z), c, ortho=span, res=(1600, 1000))
    fig.location = (mn[0] - fig_gap, (mn[1] + mx[1]) / 2, 0)
    d = max(mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2])
    shot(out / 'three_quarter.png', c + Vector((0.75, -1.25, 0.7)) * d * 1.05, c, lens=50, res=(1600, 1000))
    bpy.data.objects.remove(fig)


def scene():
    Q.reset()
    Q.gpu(bpy.context.scene, 64)
    outdoor_light()


def lantern_levels(objs, level):
    strength = {0: 0.0, 1: 0.2, 2: 0.5, 3: 0.9, 4: 1.5}[level]
    for o in objs:
        for i, m in enumerate(o.data.materials):
            if m and 'Paper' in m.name:
                c = m.copy()
                b = next(n for n in c.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
                b.inputs['Emission Strength'].default_value = strength
                o.data.materials[i] = c


def night():
    s = bpy.context.scene
    bg = next(n for n in s.world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Strength'].default_value = 0.025
    if hasattr(s.world, 'sun_threshold'):
        s.world.sun_threshold = 1000.0


def label(text, loc, size=0.28):
    cu = bpy.data.curves.new(text, 'FONT')
    cu.body = text
    cu.size = size
    cu.align_x = 'CENTER'
    o = bpy.data.objects.new(f'QA_Label_{text}', cu)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    m = bpy.data.materials.new('QA_LabelMat')
    m.use_nodes = True
    e = m.node_tree.nodes.new('ShaderNodeEmission')
    e.inputs['Color'].default_value = (1.0, 0.95, 0.5, 1)
    e.inputs['Strength'].default_value = 3.0
    m.node_tree.links.new(e.outputs[0], m.node_tree.nodes['Material Output'].inputs['Surface'])
    cu.materials.append(m)
    return o


def place(objs, x, y, rot=0.0):
    for o in objs:
        o.rotation_mode = 'XYZ'
        o.location = Matrix.Rotation(rot, 3, 'Z') @ o.location + Vector((x, y, 0))
        o.rotation_euler.z += rot
    bpy.context.view_layer.update()
    return objs


def sheets2():
    V = Q.VER
    f1 = f'TY01_SpiritField_{V}'
    no_water = lambda n: not n.endswith('_Water')
    # TY03: four stages side by side, each in a flooded field; bloom close-up
    scene()
    for i in range(4):
        x = (i - 1.5) * 2.9
        wet(load(f1, (x, 0, 0)))
        load(f'TY03_ClearwaterLotus_{V}', (x, 0, 0), keep=lambda n, i=i: f'_S{i + 1}_' in n)
    out = PREV / 'TY03_ClearwaterLotus'
    shot(out / 'stages_side_by_side.png', (0, -9.5, 3.6), (0, 0, 0.3), lens=40, res=(2000, 900))
    scene()
    wet(load(f1))
    load(f'TY03_ClearwaterLotus_{V}', keep=lambda n: '_S4_' in n)
    scale_figure((-1.9, -0.6, 0))
    shot(out / 'bloom_close.png', (-0.3, -2.4, 1.2), (-0.4, -0.85, 0.6), lens=50)
    shot(out / 'top_layout.png', (0, 0, 20), (0, 0.0001, 0), ortho=3.6, res=(1200, 1400))
    shot(out / 'eye_1p7m_bloom.png', (2.1, -2.3, 1.7), (0.0, 0.1, 0.4), lens=28, res=(1600, 900))
    # TY04: four views, five brightness levels by day and by night, comparison with the existing trail lantern
    out = PREV / 'TY04_Shoudeng'
    scene()
    four_views(out, load(f'TY04_Shoudeng_{V}'))
    shot(out / 'base_mark_close.png', (0.25, -0.75, 0.32), (0.08, -0.24, 0.2), lens=60, res=(1200, 900))
    for tod in ('day', 'night'):
        scene()
        for lv in range(5):
            lantern_levels(load(f'TY04_Shoudeng_{V}', ((lv - 2) * 1.0, 0, 0)), lv)
            label(str(lv), ((lv - 2) * 1.0, -0.6, 0.0), 0.2)
        if tod == 'night':
            night()
        shot(out / f'levels_0to4_{tod}.png', (0, -6.0, 1.6), (0, 0, 1.0), lens=45, res=(1800, 900))
    scene()
    load(f'TY04_Shoudeng_{V}', (-0.7, 0, 0))
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(ROOT.parents[2] / 'art/exports/qingxi-detail-props-v2/qingxi-trail-lantern-v2.glb'))
    other = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    mn, mx = Q.bbox(other)
    for o in [o for o in bpy.data.objects if o not in before and not o.parent]:
        o.location += Vector((0.7 - (mn[0] + mx[0]) / 2, -(mn[1] + mx[1]) / 2, -mn[2]))
    scale_figure((-1.6, 0.2, 0))
    shot(out / 'compare_trail_lantern.png', (0.0, -4.6, 1.5), (0.0, 0, 0.9), lens=45, res=(1600, 1000))
    # TY05-TY10 four views (modules side by side)
    for aid, nm in (('TY05', 'PracticeFloor'), ('TY06', 'TrainingGear'), ('TY07', 'Fence'), ('TY09', 'YardClutter'), ('TY10', 'GravelPath')):
        scene()
        objs = load(f'{aid}_{nm}_{V}')
        mods = {}
        for o in objs:
            mods.setdefault(o.name.split('_LOD0')[0], []).append(o)
        arrange(list(mods.values()), gap=0.4)
        four_views(PREV / f'{aid}_{nm}', objs)
    scene()
    rack = load(f'TY08_HerbRack_{V}', keep=lambda n: '_Rack_' in n)
    full = load(f'TY08_HerbRack_{V}')
    arrange([rack, full], gap=0.6)
    four_views(PREV / 'TY08_HerbRack', rack + full)
    # TY05 with the existing agility post, close
    scene()
    load(f'TY05_PracticeFloor_{V}', keep=lambda n: 'LayoutA' in n)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(ROOT.parents[2] / 'art/exports/qingxi-training-yard-v1/agility-post.glb'))
    for o in [o for o in bpy.data.objects if o not in before and not o.parent]:
        o.location.z += 0.05
    scale_figure((1.0, -0.9, 0.05))
    shot(PREV / 'TY05_PracticeFloor' / 'eye_1p7m_with_post.png', (1.6, -3.4, 1.7), (0, 0, 0.3), lens=30, res=(1600, 900))
    # TY07 beside the #39 broken bamboo fence (A08)
    scene()
    load(f'TY07_Fence_{V}', (-1.4, 0, 0), keep=lambda n: 'StraightA' in n)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(ROOT.parents[2] / 'art/exports/qingxi-encounter-a/A08_BrokenBambooFence.glb'))
    other = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    mn, mx = Q.bbox(other)
    for o in [o for o in bpy.data.objects if o not in before and not o.parent]:
        o.location += Vector((1.6 - (mn[0] + mx[0]) / 2, -(mn[1] + mx[1]) / 2, -mn[2]))
    scale_figure((0.1, -0.8, 0))
    shot(PREV / 'TY07_Fence' / 'compare_39_broken_fence.png', (0.1, -5.5, 1.6), (0.1, 0, 0.7), lens=40, res=(1800, 1000))
    backyard_layout()


SLOTS = {'TY_Field_1': (-2.8, 6.7), 'TY_Field_2': (2.8, 6.7), 'TY_Practice': (0.0, 10.8), 'TY_Lantern': (-5.2, 12.0),
         'TY_Corner_R': (5.0, 11.5), 'TY_Rack': (5.4, 4.0)}


def backyard_layout():
    """Whole yard at the work-package slots (scene x, z mapped to Blender x, y). The house wall is a grey placeholder
    (the house is B's work); ground, lighting and the exact scene are the core team's."""
    V = Q.VER
    scene()
    wall = Q.box('QA_HouseWall_Placeholder', (12.4, 0.3, 3.2), (0, 2.35, 1.6), None, bevel=0.0)
    gm = bpy.data.materials.new('QA_Wall')
    gm.use_nodes = True
    gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.5, 0.5, 0.5, 1)
    wall.data.materials.append(gm)
    door = Q.box('QA_Door', (1.2, 0.5, 2.2), (0, 2.35, 1.1), None, bevel=0.0)
    Q.boolean(wall, door)
    Q.apply_mods(wall)
    f = load(f'TY01_SpiritField_{V}', keep=lambda n: not n.endswith('_Water'))
    place(f, *SLOTS['TY_Field_1'])
    place(load(f'TY02_QinglingGrass_{V}', keep=lambda n: '_S4_' in n), *SLOTS['TY_Field_1'])
    f2 = load(f'TY01_SpiritField_{V}')
    wet(f2)
    place(f2, *SLOTS['TY_Field_2'], rot=math.pi)
    place(load(f'TY03_ClearwaterLotus_{V}', keep=lambda n: '_S4_' in n), *SLOTS['TY_Field_2'], rot=math.pi)
    place(load(f'TY05_PracticeFloor_{V}', keep=lambda n: 'LayoutA' in n), *SLOTS['TY_Practice'])
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(ROOT.parents[2] / 'art/exports/qingxi-training-yard-v1/agility-post.glb'))
    for o in [o for o in bpy.data.objects if o not in before and not o.parent]:
        o.location += Vector((SLOTS['TY_Practice'][0], SLOTS['TY_Practice'][1], 0.05))
    lantern = load(f'TY04_Shoudeng_{V}')
    lantern_levels(lantern, 2)
    place(lantern, *SLOTS['TY_Lantern'])
    gear = load(f'TY06_TrainingGear_{V}')
    for o, (x, y, r) in zip(sorted(gear, key=lambda o: o.name), ((-3.1, 12.0, 0.15), (1.95, 10.1, 0.0), (-2.4, 10.4, math.pi / 2))):
        place([o], x, y, r)
    cx, cy = SLOTS['TY_Corner_R']
    clutter = {o.name.split('_LOD0')[0].rsplit('_', 1)[-1]: o for o in load(f'TY09_YardClutter_{V}')}
    for nm, (dx, dy, r) in {'WaterJar': (-0.45, 0.35, 0), 'Basket': (0.15, 0.45, 0), 'Hoe': (0.62, 0.15, math.pi / 2), 'Bucket': (-0.5, -0.35, 0),
                            'Woodpile': (0.15, -0.2, math.pi / 2), 'Stool': (-0.05, -0.6, 0.3)}.items():
        if nm in clutter:
            place([clutter[nm]], cx + dx, cy + dy, r)
    place(load(f'TY08_HerbRack_{V}'), *SLOTS['TY_Rack'], rot=math.pi / 2)
    path = {o.name.split('_LOD0')[0].rsplit('_', 1)[-1]: o for o in load(f'TY10_GravelPath_{V}')}
    place([path['End']], 0, 2.5 + 0.55, math.pi)
    for k, (nm, y) in enumerate((('StraightA', 4.1), ('StraightB', 6.1), ('StraightA', 8.1))):
        o = path[nm] if k < 2 else load(f'TY10_GravelPath_{V}', keep=lambda n: 'StraightA' in n)[0]
        place([o], 0, y)
    # fence: back side (x -6..6 at y 12.5) and the two sides (y 2.5..12.5); gate in the back near the right corner
    def run(p0, p1, kinds):
        d = (Vector(p1) - Vector(p0)).normalized()
        rot = math.atan2(d.y, d.x)
        pos = Vector(p0)
        for kind in kinds:
            L = {'StraightA': 2.0, 'StraightB': 2.0, 'Straight1m': 1.0, 'Gate': 1.0}[kind]
            ctr = pos + d * (L / 2)
            if kind == 'Gate':
                for part in ('GateFrame', 'GateLeaf'):
                    place(load(f'TY07_Fence_{V}', keep=lambda n, part=part: f'_{part}_' in n), ctr.x, ctr.y, rot)
            else:
                place(load(f'TY07_Fence_{V}', keep=lambda n, kind=kind: f'_{kind}_' in n), ctr.x, ctr.y, rot)
            pos += d * L
    run((-6, 12.5), (6, 12.5), ['StraightA', 'StraightB', 'StraightA', 'StraightB', 'Straight1m', 'Gate', 'Straight1m', 'Straight1m'])
    run((-6, 2.5), (-6, 12.5), ['StraightB', 'StraightA', 'StraightB', 'StraightA', 'StraightB'])
    run((6, 12.5), (6, 2.5), ['StraightA', 'StraightB', 'StraightA', 'StraightB', 'StraightA'])
    for x, y in ((-6, 12.5), (6, 12.5)):
        place(load(f'TY07_Fence_{V}', keep=lambda n: '_Corner_' in n), x, y)
    for x, y in ((-6, 2.5), (6, 2.5)):
        place(load(f'TY07_Fence_{V}', keep=lambda n: '_End_' in n), x, y, math.pi / 2)
    out = PREV / 'backyard'
    shot(out / 'eye_1p7m_from_back_door.png', (0.0, 2.9, 1.7), (0.0, 9.0, 0.6), lens=24, res=(1800, 1000))
    shot(out / 'eye_1p7m_from_yard_end.png', (1.9, 12.1, 1.7), (-0.6, 4.0, 0.8), lens=24, res=(1800, 1000))
    for slot, (x, y) in SLOTS.items():
        label(slot, (x, y, 2.4), 0.3)
    label('TY_Fence', (-6.3, 7.5, 2.4), 0.3)
    label('TY10 path (x = 0)', (0.9, 5.2, 2.4), 0.25)
    shot(out / 'top_slots.png', (0, 7.5, 40), (0, 7.5001, 0), ortho=14.0, res=(1400, 1400))


if __name__ == '__main__' and '--sheets2' in ARGV:
    sheets2()
elif __name__ == '__main__' and '--layout' in ARGV:
    backyard_layout()
elif __name__ == '__main__' and '--sheets' in ARGV:
    sheets()
elif __name__ == '__main__':
    todo = [x for x in ARGV if not x.startswith('--')] or list(ASSETS)
    report = {aid: build_asset(aid) for aid in todo}
    print('DONE', json.dumps({k: [v['trianglesLOD0'], v['glbRoundTrip']['trianglesMatch'], v['glbRoundTrip']['bboxMatch']] for k, v in report.items()}), flush=True)
