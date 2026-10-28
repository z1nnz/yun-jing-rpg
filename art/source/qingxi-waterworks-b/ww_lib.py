"""Waterworks-specific helpers on top of qa_lib (copied from qingxi-alchemy-b).

Kit conventions (metres, Blender Z-up, front = -Y, origin = base centre unless noted):
  channel port: outer 0.60 x 0.40, clear 0.40, floor 0.10, walls 0.10, water surface z = 0.28.
  joint: every port face is flat with a 10 mm deep x 21 mm wide U groove (bore offset 40 mm);
         one JointGasket (20 mm thick installed, 23 mm free, 20 mm wide) per joint spans both grooves.
Stone parts get two vertex attributes the materials read after the parts are joined:
  ww_wet    1 inside the water bore (wet line + algae below the water surface), 0 outside
  ww_nomoss 1 near mating faces (moss suppressed so it never sits on a joint), 0 elsewhere
"""
import bpy, bmesh, math, random
from pathlib import Path
import numpy as np
from mathutils import Vector, Matrix, Euler
import qa_lib as Q

TAU = math.tau
PORT = dict(outer=0.60, height=0.40, clear=0.40, floor=0.10, wall=0.10, water_z=0.28, groove_depth=0.010, groove_w=0.021,
            groove_offset=0.040, gasket_w=0.020, gasket_t=0.020, gasket_free_t=0.023)
WATER_Z = 0.28
STATE = {'ports': [], 'bores': [], 'mats': {}}


def begin():
    STATE['ports'] = []; STATE['bores'] = []; STATE['mats'] = {}; STATE.pop('water_tex', None)


# ----------------------------------------------------------------------------- materials
def m_waterstone(name='WW_Stone', light=(0.240, 0.230, 0.210), dark=(0.112, 0.106, 0.095), scale=1.0, moss=0.75, chisel=1.0):
    """Dressed warm-grey stone (after qa_lib.m_stone) + per-block tint, point-chisel striations and pits, and the
    water history: dark wet band and algae below the water line inside the bore (ww_wet), a pale mineral tide line,
    damp foot at the ground, restrained moss in cavities and on the ground course, none near mating faces (ww_nomoss)."""
    m, nt, b = Q.new_mat(name); co = Q.coords(nt, (scale, scale, scale))
    n1 = Q.noise(nt, co, 3.2, 6, 0.62, 0.4); n2 = Q.noise(nt, co, 16.0, 4, 0.55)
    col = Q.mix(nt, Q.smooth(nt, n1, 0.40, 0.62), dark, light)
    # sandstone bedding: wavy layers along local Z of each block
    bd = Q.N(nt, 'ShaderNodeTexWave', wave_type='BANDS', bands_direction='Z'); Q.L(nt, co, bd.inputs['Vector'])
    bd.inputs['Scale'].default_value = 5.5; bd.inputs['Distortion'].default_value = 7.0
    bd.inputs['Detail'].default_value = 3.0; bd.inputs['Detail Scale'].default_value = 1.5
    bed = Q.smooth(nt, bd.outputs['Fac'], 0.30, 0.75)
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', bed, 0.38), col, (light[0] * 1.18, light[1] * 1.10, light[2] * 0.98))
    n3 = Q.noise(nt, co, 7.5, 5, 0.65)
    # mineral grain: dark and pale specks about 1 cm, visible at game texel density
    g1 = Q.smooth(nt, Q.noise(nt, co, 85.0, 2, 0.5), 0.56, 0.66)
    g2 = Q.smooth(nt, Q.noise(nt, co, 120.0, 2, 0.5, 0.3), 0.44, 0.34)
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', g1, 0.45), col, (dark[0] * 0.62, dark[1] * 0.62, dark[2] * 0.60))
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', g2, 0.35), col, tuple(min(1.0, c * 1.45) for c in light))
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', Q.smooth(nt, n3, 0.50, 0.64), 0.55), col, (dark[0] * 0.75, dark[1] * 0.75, dark[2] * 0.72))
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', Q.smooth(nt, n3, 0.42, 0.30), 0.35), col, (light[0] * 1.25, light[1] * 1.22, light[2] * 1.18))
    sd = Q.attr(nt, 'qa_seed', 'fac')
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', Q.smooth(nt, sd, 0.2, 0.9), 0.60), col, (light[0] * 0.68, light[1] * 0.72, light[2] * 0.76))
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', Q.smooth(nt, sd, 0.6, 0.0), 0.50), col, (light[0] * 1.22, light[1] * 1.10, light[2] * 0.96))
    # point-chisel striations: distorted bands across each block face
    wv = Q.N(nt, 'ShaderNodeTexWave', wave_type='BANDS', bands_direction='DIAGONAL'); Q.L(nt, co, wv.inputs['Vector'])
    wv.inputs['Scale'].default_value = 11.0 * chisel; wv.inputs['Distortion'].default_value = 3.5
    wv.inputs['Detail'].default_value = 2.0; wv.inputs['Detail Scale'].default_value = 2.5
    stri = Q.smooth(nt, wv.outputs['Fac'], 0.25, 0.85)
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', stri, 0.16), col, (dark[0] * 0.8, dark[1] * 0.8, dark[2] * 0.8))
    pits = Q.smooth(nt, Q.voronoi(nt, co, 38.0, rand=1.0), 0.13, 0.03)
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', pits, 0.55), col, (0.13, 0.125, 0.115))
    sp = Q.smooth(nt, Q.voronoi(nt, co, 140.0), 0.0, 0.25)
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', Q.math_(nt, 'SUBTRACT', 1.0, sp), 0.40), col, (0.15, 0.14, 0.13))
    sp2 = Q.smooth(nt, Q.voronoi(nt, co, 95.0, rand=0.9), 0.0, 0.12)
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', Q.math_(nt, 'SUBTRACT', 1.0, sp2), 0.30), col, tuple(min(1.0, c * 1.6) for c in light))
    warm = Q.smooth(nt, Q.noise(nt, co, 1.3, 2), 0.55, 0.8)
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', warm, 0.30), col, (0.34, 0.285, 0.22))
    cav, edge = Q.edge_cavity(nt, 0.04, 0.006)
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', Q.smooth(nt, cav, 0.1, 0.6), 0.65), col, (0.075, 0.07, 0.062))
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', Q.smooth(nt, edge, 0.3, 0.8), 0.45), col, tuple(min(1.0, c * 1.5) for c in light))
    p = Q.sep(nt, Q.world_pos(nt)); z = p[2]
    # weathering in world space: rain streaks down the faces, soil splash at the foot, sun-bleached tops
    gn = Q.sep(nt, Q.N(nt, 'ShaderNodeNewGeometry').outputs['Normal'])
    wp = Q.N(nt, 'ShaderNodeMapping'); Q.L(nt, Q.world_pos(nt), wp.inputs['Vector']); wp.inputs['Scale'].default_value = (9.0, 9.0, 0.7)
    streak = Q.math_(nt, 'MULTIPLY', Q.smooth(nt, Q.noise(nt, wp.outputs['Vector'], 2.2, 3, 0.5), 0.52, 0.70),
                     Q.math_(nt, 'SUBTRACT', 1.0, Q.smooth(nt, Q.math_(nt, 'ABSOLUTE', gn[2]), 0.5, 0.8)))
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', streak, 0.42), col, (0.10, 0.095, 0.085))
    splash = Q.math_(nt, 'SUBTRACT', 1.0, Q.smooth(nt, Q.math_(nt, 'ADD', z, Q.math_(nt, 'MULTIPLY', n3, 0.05)), 0.02, 0.16))
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', splash, 0.40), col, (0.13, 0.105, 0.075))
    tops = Q.math_(nt, 'MULTIPLY', Q.smooth(nt, gn[2], 0.6, 0.95), 0.30)
    col = Q.mix(nt, tops, col, tuple(min(1.0, c * 1.35) for c in light))
    wob = Q.math_(nt, 'MULTIPLY', Q.math_(nt, 'SUBTRACT', Q.noise(nt, co, 6.0, 3), 0.5), 0.016)
    zw = Q.math_(nt, 'ADD', z, wob)
    wet_in = Q.attr(nt, 'ww_wet', 'fac')
    below = Q.math_(nt, 'SUBTRACT', 1.0, Q.smooth(nt, zw, WATER_Z + 0.004, WATER_Z + 0.016))
    wet = Q.math_(nt, 'MULTIPLY', wet_in, below)
    algae = Q.math_(nt, 'MULTIPLY', wet, Q.smooth(nt, Q.noise(nt, co, 5.0, 4), 0.42, 0.62))
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', wet, 0.75), col, (0.070, 0.080, 0.064))
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', algae, 0.55), col, (0.10, 0.15, 0.085))
    tide = Q.math_(nt, 'MULTIPLY', wet_in, Q.math_(nt, 'SUBTRACT', 1.0, Q.smooth(nt, Q.math_(nt, 'ABSOLUTE', Q.math_(nt, 'SUBTRACT', zw, WATER_Z + 0.022)), 0.003, 0.011)))
    col = Q.mix(nt, Q.math_(nt, 'MULTIPLY', tide, 0.30), col, (0.40, 0.385, 0.35))
    damp = Q.math_(nt, 'MULTIPLY', Q.math_(nt, 'SUBTRACT', 1.0, Q.smooth(nt, Q.math_(nt, 'ADD', z, Q.math_(nt, 'MULTIPLY', n1, 0.03)), 0.01, 0.075)), 0.45)
    col = Q.mix(nt, damp, col, (0.20, 0.19, 0.17))
    nomoss = Q.math_(nt, 'SUBTRACT', 1.0, Q.attr(nt, 'ww_nomoss', 'fac'))
    site = Q.math_(nt, 'MAXIMUM', Q.smooth(nt, cav, 0.25, 0.7), Q.math_(nt, 'MULTIPLY', Q.math_(nt, 'SUBTRACT', 1.0, Q.smooth(nt, z, 0.03, 0.11)), 0.9))
    mm = Q.math_(nt, 'MULTIPLY', Q.math_(nt, 'MULTIPLY', site, Q.smooth(nt, Q.noise(nt, co, 3.2, 5, 0.6), 0.52, 0.66)), nomoss)
    mm = Q.math_(nt, 'MULTIPLY', Q.math_(nt, 'MULTIPLY', mm, Q.math_(nt, 'SUBTRACT', 1.0, wet)), moss)
    mcol = Q.mix(nt, Q.noise(nt, co, 22.0, 3), (0.11, 0.15, 0.045), (0.24, 0.29, 0.10))
    col = Q.mix(nt, mm, col, mcol)
    rough = Q.mixf(nt, Q.math_(nt, 'MULTIPLY', wet, 0.8), Q.mixf(nt, n2, 0.80, 0.92), 0.62)
    rough = Q.mixf(nt, mm, rough, 0.95)
    hgt = Q.math_(nt, 'ADD', Q.math_(nt, 'MULTIPLY', n2, 0.5), Q.math_(nt, 'MULTIPLY', Q.voronoi(nt, co, 9.0 * chisel, 'F2'), 0.5))
    hgt = Q.math_(nt, 'ADD', hgt, Q.math_(nt, 'MULTIPLY', stri, 0.18))
    hgt = Q.math_(nt, 'ADD', hgt, Q.math_(nt, 'MULTIPLY', bed, 0.22))
    hgt = Q.math_(nt, 'SUBTRACT', Q.math_(nt, 'ADD', hgt, Q.math_(nt, 'MULTIPLY', g2, 0.12)), Q.math_(nt, 'MULTIPLY', g1, 0.15))
    hgt = Q.math_(nt, 'SUBTRACT', hgt, Q.math_(nt, 'MULTIPLY', pits, 0.8))
    hgt = Q.math_(nt, 'ADD', hgt, Q.math_(nt, 'MULTIPLY', mm, 0.5))
    return Q.finish(m, nt, b, col, rough, 0.0, hgt, 0.003, 0.80)


def roughen(objs, step=0.045, amp=0.0035):
    """Grid-cut and roughen stones that are not boxes (prisms): inward-only noise along vertex normals, skipping
    vertices on the ground, on port planes, on bore walls and on the bore floor so joints and the bore stay true."""
    from mathutils import noise as mn
    for o in objs:
        if not o.get('ww_prism'): continue
        bm = bmesh.new(); bm.from_mesh(o.data); mw = o.matrix_world; iw = mw.inverted()
        mn_, mx_ = [min(v.co[i] for v in bm.verts) for i in range(3)], [max(v.co[i] for v in bm.verts) for i in range(3)]
        for i in range(3):
            n = int((mx_[i] - mn_[i]) / step)
            for k in range(1, n):
                no = Vector((0, 0, 0)); no[i] = 1.0
                bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=no * (mn_[i] + k * (mx_[i] - mn_[i]) / n), plane_no=no)
        bm.normal_update(); seed = Vector((hash(o.name) % 97, hash(o.name) % 89, 3.3))
        for v in bm.verts:
            w = mw @ v.co
            if w.z < 1e-4: continue
            if any(abs((w - Vector(p['position'])).dot(Vector(p['normal']))) < 2e-4 for p in STATE['ports']): continue
            onb = False
            for poly in STATE['bores']:
                d = min(_dist_seg((w.x, w.y), poly[j], poly[(j + 1) % len(poly)]) for j in range(len(poly)))
                if d < 0.0025 or (_inside((w.x, w.y), poly) and abs(w.z - PORT['floor']) < 2e-3): onb = True
            if onb: continue
            v.co -= v.normal * amp * (0.5 + 0.5 * mn.noise(w * 5.0 + seed))
        bm.to_mesh(o.data); bm.free()
        o.data.set_sharp_from_angle(angle=math.radians(42))


WATER_TILE = 0.5          # metres per water-normal tile; surface UV = local XY / WATER_TILE, continuous across ports
FOAM_W = 0.035            # foam band width along the walls
SHARED_TEX = Q.EXPORTS / '_shared' / 'textures'


def _periodic_field(shape, seed, filt):
    """Tileable random field: white noise shaped in the Fourier domain (wraps exactly at the image edges)."""
    rng = np.random.default_rng(seed); F = np.fft.fft2(rng.standard_normal(shape))
    ky = np.fft.fftfreq(shape[0]) * shape[0]; kx = np.fft.fftfreq(shape[1]) * shape[1]
    KY, KX = np.meshgrid(ky, kx, indexing='ij'); F = F * filt(KX, KY, np.sqrt(KX ** 2 + KY ** 2) + 1e-6)
    return F, KX, KY


def _save_png(name, rgba, non_color):
    SHARED_TEX.mkdir(parents=True, exist_ok=True); path = SHARED_TEX / f'{name}.png'
    h, w = rgba.shape[:2]; img = bpy.data.images.get(name) or bpy.data.images.new(name, w, h, alpha=True)
    img.pixels.foreach_set(np.ascontiguousarray(rgba, np.float32).ravel())
    img.filepath_raw = str(path); img.file_format = 'PNG'; img.save()
    img.colorspace_settings.name = 'Non-Color' if non_color else 'sRGB'
    return img


def water_textures():
    """Generated once per build: a tileable flow-ripple normal map (streaks run along local Y, the flow axis of a
    straight module) and a foam band (U = 0 at the wall to 1 in the stream, V tiles every metre)."""
    if 'water_tex' in STATE: return STATE['water_tex']
    n = 1024
    def wfilt(KX, KY, K):
        streak = np.exp(-(KY / (0.30 * np.abs(KX) + 2.0)) ** 2)          # long crests along the flow
        return np.where(K < 2, 0, K ** -1.45 * np.exp(-(K / 70.0) ** 2) * (0.35 + 1.0 * streak))
    F, KX, KY = _periodic_field((n, n), 11, wfilt)
    gx = np.fft.ifft2(F * 1j * KX).real; gy = np.fft.ifft2(F * 1j * KY).real
    s = 0.22 / np.sqrt((gx ** 2 + gy ** 2).mean())
    nx, ny = -gx * s, -gy * s; nz = np.ones_like(nx); ln = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    nrm = np.stack([nx / ln * 0.5 + 0.5, ny / ln * 0.5 + 0.5, nz / ln * 0.5 + 0.5, np.ones_like(nx)], -1)
    normal = _save_png('T_WW_Water_Normal', nrm, True)
    hv, wu = 512, 128
    F2, _, _ = _periodic_field((hv, wu), 23, lambda KX, KY, K: np.where(K < 1, 0, K ** -1.1 * np.exp(-(K / 26.0) ** 2)))
    nz2 = np.fft.ifft2(F2).real; nz2 = (nz2 - nz2.min()) / (np.ptp(nz2) + 1e-9)
    u = np.broadcast_to(np.linspace(0, 1, wu)[None, :], (hv, wu))
    ss = lambda x, a, b: np.clip((x - a) / (b - a), 0, 1) ** 2 * (3 - 2 * np.clip((x - a) / (b - a), 0, 1))
    edge = (1 - u) ** 2.2 * (0.45 + 0.75 * ss(nz2, 0.30, 0.75))                       # meniscus scum hugging the stone
    lace = np.exp(-((u - 0.42 - 0.12 * (nz2 - 0.5)) / 0.10) ** 2) * ss(nz2, 0.52, 0.72) * 0.55   # broken lace further out
    a = np.clip(edge + lace, 0, 0.70) * ss(1 - u, 0.0, 0.12)
    tint = ss(u, 0.0, 0.35)[..., None]
    col = (1 - tint) * np.array([0.42, 0.41, 0.35]) + tint * np.array([0.66, 0.69, 0.66])
    foam = _save_png('T_WW_WaterFoam_BaseColor', np.concatenate([col, a[..., None]], -1), False)
    STATE['water_tex'] = (normal, foam)
    return STATE['water_tex']


def m_water(name='WW_Water', color=(0.022, 0.045, 0.034), alpha=0.80):
    """Not baked: kept as its own node. Portable glTF: base colour + alpha BLEND + a tiling ripple normal map
    (exports as normalTexture with scale); the engine may scroll its UV along the flow."""
    normal, _ = water_textures()
    m, nt, b = Q.new_mat(name)
    b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = 0.035
    b.inputs['Alpha'].default_value = alpha; b.inputs['IOR'].default_value = 1.33
    tx = Q.N(nt, 'ShaderNodeTexImage', image=normal); nm = Q.N(nt, 'ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 0.6
    Q.L(nt, tx.outputs['Color'], nm.inputs['Color']); Q.L(nt, nm.outputs['Normal'], b.inputs['Normal'])
    m.surface_render_method = 'BLENDED'; m.use_backface_culling = False; m['qa_nobake'] = True
    return m


def m_foam(name='WW_Foam'):
    _, foam = water_textures()
    m, nt, b = Q.new_mat(name)
    tx = Q.N(nt, 'ShaderNodeTexImage', image=foam)
    Q.L(nt, tx.outputs['Color'], b.inputs['Base Color']); Q.L(nt, tx.outputs['Alpha'], b.inputs['Alpha'])
    b.inputs['Roughness'].default_value = 0.6
    m.surface_render_method = 'BLENDED'; m.use_backface_culling = False; m['qa_nobake'] = True
    return m


def mats():
    """One shared material set per build (names are per asset so bakes never collide)."""
    if STATE['mats']: return STATE['mats']
    M = STATE['mats']
    M['stone'] = m_waterstone('WW_Stone')
    M['stone_dark'] = m_waterstone('WW_StoneDark', light=(0.185, 0.178, 0.165), dark=(0.088, 0.084, 0.077), moss=0.5)
    cedar_a, cedar_b = (0.056, 0.042, 0.031), (0.118, 0.086, 0.060)
    for ax in 'XYZ':
        M['wood' + ax] = Q.m_wood('WW_Cedar' + ax, a=cedar_a, b_=cedar_b, axis=ax, ring=3.2, wear=0.32, rough=0.78, seed_tint=0.12)
    M['endgrain'] = Q.m_endgrain('WW_CedarEnd', a=(0.20, 0.135, 0.08), b_=(0.33, 0.235, 0.14))
    M['bronze'] = Q.m_bronze('WW_Bronze', patina=0.62, polish=0.55)
    M['bronze_dark'] = Q.m_bronze('WW_BronzeOld', patina=0.8, polish=0.3)
    M['gasket'] = Q.m_simple('WW_Gasket', (0.30, 0.15, 0.085), (0.40, 0.21, 0.12), rough=0.92, nscale=40.0, bump=0.0008, cav_col=(0.16, 0.08, 0.05))
    M['rope'] = Q.m_cord('WW_Rope', c1=(0.36, 0.29, 0.18), c2=(0.50, 0.42, 0.28))
    M['cloth'] = Q.m_cloth('WW_Pennant', base=(0.55, 0.10, 0.06), stain=(0.35, 0.10, 0.06), stain_axis_z=None)
    M['iron'] = Q.m_iron('WW_Iron', rust=0.45)
    M['water'] = m_water(); M['foam'] = m_foam()
    return M


# ----------------------------------------------------------------------------- geometry
def _cuts(h, free_lo, free_hi, step, r):
    """Cut positions along one axis: regular grid plus a fan near free faces so edge rounding has vertices."""
    n = max(1, int(round(2 * h / step))); cs = {round(-h + 2 * h * i / n, 6) for i in range(1, n)}
    for f, s in ((free_lo, -1), (free_hi, 1)):
        if f:
            for k in (1.0, 0.62, 0.30, 0.10): cs.add(round(s * (h - r * k), 6))
    return sorted(c for c in cs if -h + 1e-4 < c < h - 1e-4)


def stone(name, size, loc, mat=None, seed=1, keep=('z-',), chips=2, bevel=0.0, chip_r=(0.03, 0.06), rot=(0, 0, 0), bseg=2,
          wear=(0.006, 0.022), step=0.045, flat=()):
    """Dressed stone block. keep lists faces that must stay perfectly flat and unchipped (mating faces, bedding,
    bore faces): any of 'x-','x+','y-','y+','z-','z+'. Edges between two free faces are worn round with a radius
    that wanders along the edge (wear); chips are real boolean bites on those edges. Mating-face edges stay crisp."""
    mat = mat or mats()['stone']
    rnd = random.Random(seed); hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2; H = (hx, hy, hz)
    free = {a + s: (a + s) not in keep for a in 'xyz' for s in '-+'}
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    for i, a in enumerate('xyz'):
        for c in _cuts(H[i], free[a + '-'], free[a + '+'], step, wear[1]):
            no = Vector((0, 0, 0)); no[i] = 1.0
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=no * c, plane_no=no)
    from mathutils import noise as mn
    off = Vector((seed * 7.31, seed * 3.17, seed * 1.91))
    for v in bm.verts:
        p = v.co.copy(); W_ = wear[1]
        q = p.copy()
        for i, a in enumerate('xyz'):
            lo = -H[i] + W_ if free[a + '-'] else -1e9; hi = H[i] - W_ if free[a + '+'] else 1e9
            q[i] = min(max(p[i], lo), hi)
        d = p - q
        if d.length > 1e-9:
            # radial map of the wear zone towards a round (factor depends only on the angle, so it cannot fold);
            # the wear amount varies along the edge only (noise sampled with the zone axes masked out)
            m_ = p.copy()
            for i in range(3):
                if abs(d[i]) > 1e-9: m_[i] = 0.0
            t = (wear[0] + (W_ - wear[0]) * (0.5 + 0.5 * mn.noise(m_ * 9.0 + off))) / W_
            dinf = max(abs(c) for c in d)
            v.co = q + d * (1.0 - t + t * dinf / d.length)
        # gentle face undulation, inward only, fading to zero 1 wear-width under the face (measured on the
        # pre-rounding position) so the fan of edge cuts is compressed, never pushed past its neighbours
        for i, a in enumerate('xyz'):
            for s, f in ((-1, a + '-'), (1, a + '+')):
                dist = abs(p[i] - s * H[i])
                if free[f] and f not in flat and dist < W_:
                    v.co[i] -= s * 0.0035 * (0.5 + 0.5 * mn.noise(p * 5.0 + off * 1.7)) * (1.0 - dist / W_)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=2e-4)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=2e-4)
    o = Q._obj(name, bm, mat, smooth=True, sharp=42); o.location = loc; o.rotation_euler = rot; o['ww_stone'] = True
    free = [f for f in ('x-', 'x+', 'y-', 'y+', 'z-', 'z+') if f not in keep]
    edges = []
    axes = {'x': 0, 'y': 1, 'z': 2}
    for i, a in enumerate(free):
        for b_ in free[i + 1:]:
            if a[0] == b_[0]: continue
            edges.append((a, b_))
    rnd.shuffle(edges)
    cutters = []
    for k, (a, b_) in enumerate(edges[:chips]):
        c = [0.0, 0.0, 0.0]; half = [hx, hy, hz]
        for f in (a, b_): c[axes[f[0]]] = half[axes[f[0]]] * (1 if f[1] == '+' else -1)
        run = 3 - axes[a[0]] - axes[b_[0]]
        lim = half[run] - 0.06
        if lim <= 0.01: continue
        c[run] = rnd.uniform(-lim, lim)
        # never bite into a keep plane
        r = rnd.uniform(*chip_r)
        for f in keep:
            ax = axes[f[0]]; plane = half[ax] * (1 if f[1] == '+' else -1)
            if ax == run and abs(c[run] - plane) < r * 1.6: c[run] = plane - math.copysign(r * 1.7, plane)
        w = Matrix.Translation(loc) @ Euler(rot).to_matrix().to_4x4() @ Vector(c)
        cut = Q.rock(f'Cut_{name}_{k}', (r, r * rnd.uniform(0.7, 1.1), r * rnd.uniform(0.6, 0.9)), w, mat, seed=seed * 31 + k, subd=2, rough=0.35)
        cutters.append(cut); Q.boolean(o, cut)
    Q.apply_mods(o)
    if bevel: Q.add_bevel(o, bevel, bseg, angle=35)
    return o


def lathe_axis(name, prof, mat, axis='Y', segs=32, sharp=38, loc=(0, 0, 0)):
    o = Q.lathe(name, prof, mat, segs=segs, sharp=sharp)
    o.rotation_euler = {'Z': (0, 0, 0), 'Y': (-math.pi / 2, 0, 0), 'X': (0, math.pi / 2, 0)}[axis]
    o.location = loc
    return o


def outline_prism(name, outline, z0, z1, mat, sharp=30):
    """Closed (x, y) outline extruded from z0 to z1."""
    o = Q.prism(name, outline, z1 - z0, mat, axis='Z', center=(z0 + z1) / 2, sharp=sharp)
    return o


def arc(cx, cy, r, a0, a1, n=8):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def groove_outline():
    """U band (x, z) of the joint groove at a port face, port centred on x = 0."""
    hc = PORT['clear'] / 2; off = PORT['groove_offset']; w = PORT['groove_w']; fl = PORT['floor']; top = PORT['height'] + 0.01
    a, b = hc + off - w / 2, hc + off + w / 2
    za, zb = fl - off + w / 2, fl - off - w / 2
    return [(-b, top), (-b, zb), (b, zb), (b, top), (a, top), (a, za), (-a, za), (-a, top)]


def gasket_outline():
    hc = PORT['clear'] / 2; off = PORT['groove_offset']; w = PORT['gasket_w']; fl = PORT['floor']; top = PORT['height'] - 0.004
    a, b = hc + off - w / 2, hc + off + w / 2
    za, zb = fl - off + w / 2, fl - off - w / 2
    return [(-b, top), (-b, zb), (b, zb), (b, top), (a, top), (a, za), (-a, za), (-a, top)]


def port_frame(center, yaw):
    """World matrix of a port: local x across the bore, local -y = outward normal, z up."""
    return Matrix.Translation(Vector(center)) @ Matrix.Rotation(yaw, 4, 'Z')


def add_port(name, center, yaw, targets):
    """Register a port at `center` (bore centre on the face, z = 0 floor bottom) whose outward normal is
    (-sin(yaw)... ) i.e. the -Y axis rotated by yaw; cut the joint groove into `targets` and add the socket."""
    M = port_frame(center, yaw)
    cut = Q.prism(f'Cut_groove_{name}', groove_outline(), PORT['groove_depth'] * 2, mats()['stone'], axis='Y', center=0.0)
    cut.matrix_world = M
    bpy.context.view_layer.update(); cmn, cmx = _wbox(cut)
    for t in targets:
        if t.type != "MESH" or t.get("qa_node") == "Water": continue
        tmn, tmx = _wbox(t)
        if all(tmn[k] < cmx[k] + 1e-3 and cmn[k] < tmx[k] + 1e-3 for k in range(3)): Q.boolean(t, cut)
    n = (M.to_3x3() @ Vector((0, -1, 0))).normalized()
    STATE['ports'].append(dict(name=name, position=[round(c, 5) for c in center], normal=[round(c, 5) for c in n], up=[0, 0, 1],
                               yaw_deg=round(math.degrees(yaw), 3), clear_width=PORT['clear'], floor_z=round(center[2] + PORT['floor'], 5),
                               water_z=round(center[2] + PORT['water_z'], 5), outer=[PORT['outer'], PORT['height']], type='channel_std',
                               compatible=['channel_std'], gasket='shared JointGasket, one per joint'))
    return cut


def apply_all(objs):
    """Bake modifier stacks (bevel first, then groove / mortise booleans) so later tests see the real mesh."""
    for o in objs:
        if o.type == 'MESH' and not o.get('qa_cutter') and o.modifiers: Q.apply_mods(o)


def gasket(name='JointGasket', loc=(0, 0, 0), yaw=0.0):
    g = Q.prism(name, gasket_outline(), PORT['gasket_t'], mats()['gasket'], axis='Y', center=0.0)
    g.matrix_world = port_frame(loc, yaw); return g


def bore(poly):
    """Register an (x, y) bore polygon: stone vertices inside it (grown by 25 mm) are tagged wet."""
    STATE['bores'].append(poly)


def _inside(pt, poly):
    x, y = pt; c = False; n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1: c = not c
    return c


def _dist_seg(p, a, b):
    ax, ay = a; bx, by = b; px, py = p; dx, dy = bx - ax, by - ay
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy + 1e-12)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def tag_water_attrs(objs):
    """Write ww_wet / ww_nomoss point attributes on every mesh (world-space test, before joining)."""
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        if o.type != 'MESH' or o.get('qa_cutter'): continue
        if o.modifiers: Q.apply_mods(o)
        me = o.data; mw = o.matrix_world; n = len(me.vertices)
        wet = np.zeros(n, np.float32); nom = np.zeros(n, np.float32)
        for i, v in enumerate(me.vertices):
            w = mw @ v.co; p = (w.x, w.y)
            if STATE['bores']:
                ins = any(_inside(p, poly) or min(_dist_seg(p, poly[j], poly[(j + 1) % len(poly)]) for j in range(len(poly))) < 0.025 for poly in STATE['bores'])
                wet[i] = 1.0 if ins else 0.0
            d = 9.0
            for pt in STATE['ports']:
                c = Vector(pt['position']); nn = Vector(pt['normal'])
                d = min(d, abs((w - c).dot(nn)) + max(0.0, (w - c - nn * (w - c).dot(nn)).length - 0.45) * 2)
            nom[i] = 1.0 - min(1.0, max(0.0, (d - 0.04) / 0.20))
        for nm, arr in (('ww_wet', wet), ('ww_nomoss', nom)):
            a = me.attributes.get(nm) or me.attributes.new(nm, 'FLOAT', 'POINT'); a.data.foreach_set('value', arr)


def water_plane(name, poly, z=WATER_Z, mat=None, subdiv=0.10):
    """Flat water surface (x, y) polygon at height z, gridded so morph targets can ripple it."""
    bm = bmesh.new(); vs = [bm.verts.new((x, y, z)) for x, y in poly]; f = bm.faces.new(vs)
    bmesh.ops.triangulate(bm, faces=[f])
    for _ in range(3):
        long = [e for e in bm.edges if e.calc_length() > subdiv]
        if not long: break
        bmesh.ops.subdivide_edges(bm, edges=long, cuts=1, use_grid_fill=False)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    for f in bm.faces: f.normal_update()
    if any(f.normal.z < 0 for f in bm.faces): bmesh.ops.reverse_faces(bm, faces=[f for f in bm.faces if f.normal.z < 0])
    uv = bm.loops.layers.uv.new('UVMap')
    for f in bm.faces:
        for lp in f.loops: lp[uv].uv = (lp.vert.co.x / WATER_TILE, lp.vert.co.y / WATER_TILE)
    _foam_strips(bm, uv, poly, z)
    o = Q._obj(name, bm, mat or mats()['water'], smooth=True, sharp=80); o['qa_node'] = 'Water'
    o.data.materials.append(mats()['foam'])
    return o


def _foam_strips(bm, uv, poly, z):
    """Foam band (material slot 1) along every wall edge of the water polygon, none across a port: inner edge
    mitred at wall-wall corners, square to the port plane where a wall meets a port. Sits 1.5 mm above the water."""
    P = [Vector((x, y, 0)) for x, y in poly]; k = len(P)
    area = sum(P[i].x * P[(i + 1) % k].y - P[(i + 1) % k].x * P[i].y for i in range(k))
    def inward(i):
        d = (P[(i + 1) % k] - P[i]).normalized(); return Vector((-d.y, d.x, 0)) if area > 0 else Vector((d.y, -d.x, 0))
    def on_port(i):
        m = (P[i] + P[(i + 1) % k]) / 2
        for pt in STATE['ports']:
            c = Vector((pt['position'][0], pt['position'][1], 0)); nn = Vector((pt['normal'][0], pt['normal'][1], 0))
            if abs((m - c).dot(nn)) < 0.005 and (m - c - nn * (m - c).dot(nn)).length < 0.25: return True
        return False
    wall = [not on_port(i) for i in range(k)]
    if not any(wall): return
    off = []
    for i in range(k):
        a, b_ = (i - 1) % k, i          # edges meeting at vertex i
        if wall[a] and wall[b_]:
            m = (inward(a) + inward(b_)).normalized(); off.append(m * (FOAM_W / max(0.35, m.dot(inward(b_)))))
        elif wall[b_]: off.append(inward(b_) * FOAM_W)
        elif wall[a]: off.append(inward(a) * FOAM_W)
        else: off.append(Vector((0, 0, 0)))
    zf = z + 0.0015; vlen = 0.0
    for i in range(k):
        j = (i + 1) % k; ln = (P[j] - P[i]).length
        if wall[i]:
            ns = max(1, math.ceil(ln / 0.05))      # short segments so the strip follows the ripple morphs
            outer = [bm.verts.new((*(P[i].lerp(P[j], t / ns)).xy, zf)) for t in range(ns + 1)]
            inner = [bm.verts.new((*(P[i].lerp(P[j], t / ns) + off[i].lerp(off[j], t / ns)).xy, zf)) for t in range(ns + 1)]
            for t in range(ns):
                f = bm.faces.new((outer[t], outer[t + 1], inner[t + 1], inner[t])); f.material_index = 1; f.normal_update()
                if f.normal.z < 0: f.normal_flip()
                for lp in f.loops:
                    s = (outer + inner).index(lp.vert) % (ns + 1)
                    lp[uv].uv = (0.0 if lp.vert in outer else 1.0, vlen + ln * s / ns)
        vlen += ln


def ripple_keys(o, amp=0.004, k=18.0, frames=48, phases=2):
    """Portable water motion: two shape keys with travelling ripples, looped by keyframes (exports as morph targets)."""
    o.shape_key_add(name='Basis')
    for i in range(phases):
        sk = o.shape_key_add(name=f'Ripple{i}')
        for v, d in zip(o.data.vertices, sk.data):
            x, y = v.co.x, v.co.y; ph = i * math.pi / phases
            d.co = v.co + Vector((0, 0, amp * (math.sin(k * (x * 0.7 + y) + ph * 2) * 0.6 + math.sin(k * 1.7 * (y - x * 0.4) + ph * 3) * 0.4)))
    return o


def rivet(name, loc, normal, r=0.008, h=0.005, mat=None):
    o = Q.cyl(name, r, h, (0, 0, 0), mat or mats()['bronze'], segs=10, r2=r * 0.55)
    n = Vector(normal).normalized(); o.rotation_euler = n.to_track_quat('Z', 'Y').to_euler()
    o.location = Vector(loc) + n * (h / 2 - 0.001)
    return o


def strap(name, a, b, normal, w=0.040, t=0.006, mat=None, rivets=2):
    """Flat bronze strap from a to b lying on a face with outward `normal`; rivets spaced along it."""
    a, b, n = Vector(a), Vector(b), Vector(normal).normalized()
    d = (b - a); L = d.length
    o = Q.box(name, (w, L, t), (0, 0, 0), mat or mats()['bronze'], bevel=0.0015, bseg=1)
    yv = d.normalized(); zv = n; xv = yv.cross(zv).normalized()
    o.matrix_world = Matrix((xv, yv, zv)).transposed().to_4x4()
    o.location = (a + b) / 2 + n * (t / 2 - 0.0008)
    parts = [o]
    for i in range(rivets):
        f = (i + 1) / (rivets + 1)
        parts.append(rivet(f'{name}_rv{i}', a + d * f + n * (t - 0.0012), n, r=w * 0.18, mat=mat))
    return parts


def wood_box(name, size, loc, axis, rot=(0, 0, 0), bevel=0.006, endgrain=True):
    """Cedar member with grain along `axis` (local) and end-grain material on the two end faces."""
    M = mats(); o = Q.box(name, size, loc, M['wood' + axis], bevel=0.0, rot=rot)
    if endgrain: _endgrain(o, axis)
    if bevel: Q.add_bevel(o, bevel, 2, angle=40)
    return o


def _endgrain(o, axis):
    M = mats(); me = o.data; me.materials.append(M['endgrain'])
    ax = {'X': 0, 'Y': 1, 'Z': 2}[axis]
    for p in me.polygons:
        if abs(p.normal[ax]) > 0.9: p.material_index = len(me.materials) - 1


def peg(name, loc, normal, r=0.009, L=0.03):
    n = Vector(normal).normalized(); o = Q.cyl(name, r, L, (0, 0, 0), mats()['endgrain'], segs=10)
    o.rotation_euler = n.to_track_quat('Z', 'Y').to_euler(); o.location = Vector(loc) - n * (L / 2 - 0.003)
    return o


def scale_rod(name='ScaleRod_1p75', loc=(0, 0, 0)):
    """Neutral 1.75 m graduated rod (10 cm bands) with an eye-height ring at 1.62 m; not a character."""
    objs = []; dark = Q.m_simple('ScaleDark', (0.06, 0.06, 0.06), rough=0.6); light = Q.m_simple('ScaleLight', (0.85, 0.83, 0.78), rough=0.6)
    eye = Q.m_simple('ScaleEye', (0.85, 0.35, 0.10), rough=0.5)
    for i in range(18):
        h = min(0.10, 1.75 - i * 0.10)
        if h <= 0: break
        objs.append(Q.cyl(f'{name}_{i}', 0.018, h, (loc[0], loc[1], loc[2] + i * 0.10 + h / 2), dark if i % 2 == 0 else light, segs=12))
    objs.append(Q.torus(f'{name}_eye', 0.045, 0.008, (loc[0], loc[1], loc[2] + 1.62), eye, 24, 8))
    objs.append(Q.cyl(f'{name}_base', 0.10, 0.012, (loc[0], loc[1], loc[2] + 0.006), dark, segs=24))
    return objs


EYE_HEIGHT = 1.62    # adopted player eye height for a 1.75 m character


def localize_images(objs, tdir):
    """Copy every non-baked image used by these objects (shared water normal / foam) next to the asset's own
    textures and point the image at the copy, so the FBX folder is self-contained."""
    import shutil
    tdir.mkdir(parents=True, exist_ok=True)
    for o in objs:
        for m in (o.data.materials if o.type == 'MESH' else []):
            for n in (m.node_tree.nodes if m and m.use_nodes else []):
                img = getattr(n, 'image', None)
                if n.type == 'TEX_IMAGE' and img and img.filepath_raw:
                    src = Path(bpy.path.abspath(img.filepath_raw)); dst = tdir / src.name
                    if src.exists() and src.resolve() != dst.resolve(): shutil.copyfile(src, dst)
                    img.filepath_raw = str(dst); img.filepath = str(dst)


COURSES = ((0.0, 0.22), (0.22, 0.40))     # shared bed joint height, so joints line up from module to module


def course_wall(prefix, axis, a0, a1, c0, c1, inner, seed, ends=(0.0, 0.0), end_keep=((), ()), joints=(),
                lens=(0.24, 0.42), courses=COURSES, chips=1, mat=None, open_ends=(False, False)):
    """Dry-laid wall from a0..a1 along `axis` ('X' or 'Y'), thickness c0..c1 on the other axis, `inner` ('-' or '+')
    is the bore side. Courses of blocks with staggered head joints; `ends` gives full-height end stones (pilasters)
    at a0 / a1; `joints` forces a head joint through every course (where a clamp crosses it). Bore face, bed and
    the wall ends stay flat; head joints and the top are worn round so the joints read, without gaps between stones.
    end_keep adds faces to keep on an end stone: 'outer' (a mating face continues across it) or 'top'.
    open_ends: True where the wall end is free (worn), not butting a port plane or another stone."""
    rnd = random.Random(seed * 101 + 7)
    A, T = ('x', 'y') if axis == 'X' else ('y', 'x')
    out_face = T + ('+' if inner == '-' else '-'); in_face = T + inner
    stones = []
    def block(nm, b0, b1, z0, z1, keep, flat):
        size = [0, 0, z1 - z0]; loc = [0, 0, (z0 + z1) / 2]
        ia, it = (0, 1) if axis == 'X' else (1, 0)
        size[ia] = b1 - b0; size[it] = c1 - c0; loc[ia] = (b0 + b1) / 2; loc[it] = (c0 + c1) / 2
        stones.append(stone(nm, tuple(size), tuple(loc), mat=mat, seed=rnd.randint(1, 9999), keep=keep, flat=flat,
                            chips=chips if b1 - b0 > 0.2 else 0, chip_r=(0.02, 0.04), step=0.08, wear=(0.004, 0.013)))
    lo, hi = a0 + ends[0], a1 - ends[1]
    for e, (b0, b1) in enumerate(((a0, lo), (hi, a1))):
        if b1 - b0 < 1e-6: continue
        end_face = A + ('-' if e == 0 else '+')
        keep = ['z-', in_face] + ([] if open_ends[e] else [end_face])
        keep += [out_face] if 'outer' in end_keep[e] else []
        keep += ['z+'] if 'top' in end_keep[e] else []
        inside = A + ('+' if e == 0 else '-')
        block(f'{prefix}_End{e}', b0, b1, courses[0][0], courses[-1][1], tuple(keep), (inside,))
    for k, (z0, z1) in enumerate(courses):
        cuts = [lo]; x = lo + (rnd.uniform(*lens) * (0.5 if k % 2 else 1.0))
        while x < hi - 0.12:
            cuts.append(x); x += rnd.uniform(*lens)
        cuts.append(hi)
        for j in joints:
            if lo < j < hi:
                cuts = [c for c in cuts if abs(c - j) > 0.08 or c in (lo, hi)] + [j]
        cuts = sorted(set(round(c, 4) for c in cuts))
        for i in range(len(cuts) - 1):
            b0, b1 = cuts[i], cuts[i + 1]
            keep = ['z-', in_face]
            if i == 0 and ends[0] < 1e-6 and not open_ends[0]: keep.append(A + '-')
            if i == len(cuts) - 2 and ends[1] < 1e-6 and not open_ends[1]: keep.append(A + '+')
            flat = tuple(f for f in (A + '-', A + '+') if f not in keep)
            if k < len(courses) - 1: flat += ('z+',)
            block(f'{prefix}_C{k}_{i}', b0, b1, z0, z1, tuple(keep), flat)
    return stones


def coursed_prism(name, outline, mat, courses=COURSES, bevel=0.010):
    """A carved one-piece stone outline (fillet corners, splitter) laid in the same courses as the walls."""
    out = []
    for k, (z0, z1) in enumerate(courses):
        p = outline_prism(f'{name}_C{k}', outline, z0, z1, mat); p['ww_prism'] = True
        Q.add_bevel(p, bevel, 2, 35); out.append(p)
    return out


def _wbox(o):
    cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return [min(c[k] for c in cs) for k in range(3)], [max(c[k] for c in cs) for k in range(3)]
