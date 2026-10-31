"""Bake/export/render toolkit for the newcomer territory backyard kit (A, 2026-10-31).

Copied from art/source/qingxi-waterhead-a/kitlib.py (PR #45) with only KIT changed; that file is not modified.

Adapted from art/source/qingxi-alchemy-b/qa_lib.py (joshsu54 + Claude Code, main ebe57d4) so the
training yard ships at the same level as the alchemy workshop: procedural materials with AO-driven
edge/cavity weathering baked into one atlas per asset (BaseColor, ORM, Normal), LOD0-2, GLB + FBX.
Differences from the original: the kit paths below, UV islands scaled by surface area before packing (large terrain
tiles), and unbaked parts keep their own UVs (water flow direction). The source file is not modified.

Geometry helpers build real-scale parts (1 unit = 1 m, front -Y, origin at the base centre).
Procedural Cycles materials expose channel reroutes (CH_albedo, CH_rough, CH_metal, CH_emit, CH_alpha) so
bake_asset() can bake every part into one atlas material per asset: base colour x AO, ORM (R=AO G=rough
B=metal), tangent normal, optional emission. Parts tagged qa_nobake keep their own material (glass, liquid).
Weathering masks come from Cycles AO (cavity) and inverted AO (edges), so they follow the real geometry.
"""
import bpy, bmesh, math, json, hashlib, random
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
KIT = 'territory-backyard-a'
EXPORTS = REPO / 'art/exports' / KIT
PREVIEWS = REPO / 'art/previews' / KIT
VER = 'v001'
TAU = math.tau


# ----------------------------------------------------------------------------- scene
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.unit_settings.system = 'METRIC'; s.unit_settings.scale_length = 1.0
    return s


def gpu(scene, samples=64):
    scene.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for kind in ('OPTIX', 'CUDA'):
        try:
            prefs.compute_device_type = kind; prefs.get_devices()
            if any(d.type == kind for d in prefs.devices): break
        except TypeError:
            continue
    for d in prefs.devices: d.use = d.type != 'CPU'
    scene.cycles.device = 'GPU'; scene.cycles.samples = samples
    return scene


def coll(name, parent=None):
    c = bpy.data.collections.new(name); (parent or bpy.context.scene.collection).children.link(c); return c


ACTIVE = {'coll': None}


def link(o):
    (ACTIVE['coll'] or bpy.context.scene.collection).objects.link(o); return o


def select_only(objs, active=None):
    for o in bpy.context.view_layer.objects: o.select_set(False)
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = active or (objs[0] if objs else None)


# ----------------------------------------------------------------------------- geometry
def _obj(name, bm, mat, smooth=True, sharp=38):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth:
        for p in me.polygons: p.use_smooth = True
        me.set_sharp_from_angle(angle=math.radians(sharp))
    o = bpy.data.objects.new(name, me); link(o)
    if mat: me.materials.append(mat)
    return o


def lathe(name, prof, mat, segs=48, sharp=38, a0=0.0):
    """Revolve a (r, z) profile. Trace it counter-clockwise in the r-z plane (out along the base, up the
    outside, back in over the top or down an inner wall) and the faces point outward."""
    bm = bmesh.new(); rings = []
    for r, z in prof:
        if r < 1e-6: rings.append([bm.verts.new((0, 0, z))])
        else: rings.append([bm.verts.new((r * math.cos(a0 + TAU * i / segs), r * math.sin(a0 + TAU * i / segs), z)) for i in range(segs)])
    for A, B in zip(rings, rings[1:]):
        for i in range(segs):
            j = (i + 1) % segs
            if len(A) == 1 and len(B) == 1: break
            if len(A) == 1: bm.faces.new((A[0], B[j], B[i]))
            elif len(B) == 1: bm.faces.new((A[i], A[j], B[0]))
            else: bm.faces.new((A[i], A[j], B[j], B[i]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    return _obj(name, bm, mat, sharp=sharp)


def prism(name, outline, depth, mat, axis='Y', center=0.0, sharp=30):
    """Extrude a closed 2-D outline. axis='Y': outline is (x, z), extruded along Y; 'X': (y, z); 'Z': (x, y)."""
    bm = bmesh.new()
    def P(u, v, w):
        return {'Y': (u, w, v), 'X': (w, u, v), 'Z': (u, v, w)}[axis]
    lo = [bm.verts.new(P(u, v, center - depth / 2)) for u, v in outline]
    hi = [bm.verts.new(P(u, v, center + depth / 2)) for u, v in outline]
    n = len(outline)
    bm.faces.new(lo); bm.faces.new(hi[::-1])
    for i in range(n):
        j = (i + 1) % n; bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj(name, bm, mat, sharp=sharp)


def box(name, size, loc=(0, 0, 0), mat=None, bevel=0.004, bseg=2, rot=(0, 0, 0)):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    o = _obj(name, bm, mat, smooth=False); o.location = loc; o.rotation_euler = rot
    if bevel: add_bevel(o, bevel, bseg)
    return o


def cyl(name, r, h, loc=(0, 0, 0), mat=None, segs=24, bevel=0.0, bseg=2, rot=(0, 0, 0), r2=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r, radius2=r if r2 is None else r2, depth=h)
    o = _obj(name, bm, mat); o.location = loc; o.rotation_euler = rot
    if bevel: add_bevel(o, bevel, bseg)
    return o


def torus(name, R, r, loc=(0, 0, 0), mat=None, major=32, minor=10, rot=(0, 0, 0)):
    bm = bmesh.new(); rings = []
    for i in range(major):
        a = TAU * i / major; c = Vector((math.cos(a), math.sin(a), 0))
        rings.append([bm.verts.new(c * (R + r * math.cos(TAU * k / minor)) + Vector((0, 0, r * math.sin(TAU * k / minor)))) for k in range(minor)])
    for i in range(major):
        A, B = rings[i], rings[(i + 1) % major]
        for k in range(minor):
            m = (k + 1) % minor; bm.faces.new((A[k], B[k], B[m], A[m]))
    o = _obj(name, bm, mat, sharp=80); o.location = loc; o.rotation_euler = rot
    return o


def tube(name, pts, radius, mat, segs=10, closed=False, res=6, taper=None, cap=True):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    cu.bevel_depth = radius; cu.bevel_resolution = max(1, segs // 4 - 1); cu.resolution_u = res; cu.use_fill_caps = cap
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1); sp.use_cyclic_u = closed
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
    if taper:
        for bp, t in zip(sp.bezier_points, taper): bp.radius = t
    tmp = bpy.data.objects.new(name + '_c', cu); link(tmp)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp); bpy.data.curves.remove(cu)
    for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new(name, me); link(o)
    me.materials.clear(); me.materials.append(mat)
    return o


def add_bevel(o, width, segs=2, angle=40, harden=True):
    m = o.modifiers.new('Bevel', 'BEVEL'); m.width = width; m.segments = segs
    m.limit_method = 'ANGLE'; m.angle_limit = math.radians(angle); m.harden_normals = harden; m.miter_outer = 'MITER_ARC'
    return m


def boolean(o, cutter, op='DIFFERENCE'):
    m = o.modifiers.new('Bool_' + cutter.name, 'BOOLEAN'); m.operation = op; m.object = cutter; m.solver = 'EXACT'
    try: m.material_mode = 'TRANSFER'
    except AttributeError: pass
    cutter.hide_render = True; cutter.hide_set(True); cutter['qa_cutter'] = True
    return m


def apply_mods(o):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    o.modifiers.clear(); old = o.data; o.data = me; bpy.data.meshes.remove(old)
    return o


def jitter(o, amp, seed=1, axis_scale=(1, 1, 1)):
    rnd = random.Random(seed)
    for v in o.data.vertices:
        v.co += Vector((rnd.uniform(-amp, amp) * axis_scale[0], rnd.uniform(-amp, amp) * axis_scale[1], rnd.uniform(-amp, amp) * axis_scale[2]))
    return o


def rock(name, size, loc, mat, seed=1, subd=2, rough=0.25, flat=0.0):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=subd, radius=1.0)
    rnd = random.Random(seed); n = [Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))).normalized() for _ in range(5)]
    for v in bm.verts:
        d = v.co.normalized(); k = 1 + sum(rough * 0.5 * max(0, d.dot(a)) ** 3 for a in n) - rough * 0.35 * abs(d.dot(n[0]))
        v.co = Vector((d.x * size[0] * k, d.y * size[1] * k, d.z * size[2] * k * (1 - flat * (d.z < 0))))
    o = _obj(name, bm, mat, sharp=55); o.location = loc
    o.rotation_euler = (rnd.uniform(0, 6), rnd.uniform(0, 6), rnd.uniform(0, 6))
    return o


def arch_outline(w, z0, zs, n=12, inset=0.0):
    """Arched opening outline (x, z): straight jambs from z0 to zs, semicircular head of radius w/2."""
    r = w / 2 - inset; pts = [(-r, z0 + inset), (r, z0 + inset)]
    for i in range(n + 1):
        a = math.pi * i / n; pts.append((r * math.cos(a), zs + r * math.sin(a)))
    return pts[:2] + pts[2:]


def finalize_parts(objs, seed=0):
    """Store part-local coordinates (qa_lc) and a per-part random value (qa_seed) as point attributes so
    textures keep following each part after the parts are joined into one game mesh."""
    rnd = random.Random(seed)
    for o in objs:
        if o.type != 'MESH' or o.get('qa_cutter'): continue
        me = o.data; n = len(me.vertices); s = rnd.random()
        lc = me.attributes.get('qa_lc') or me.attributes.new('qa_lc', 'FLOAT_VECTOR', 'POINT')
        co = np.zeros(n * 3, np.float32); me.vertices.foreach_get('co', co); lc.data.foreach_set('vector', co)
        sd = me.attributes.get('qa_seed') or me.attributes.new('qa_seed', 'FLOAT', 'POINT')
        sd.data.foreach_set('value', [s] * n)


# ----------------------------------------------------------------------------- material node helpers
def N(nt, kind, x=0, y=0, **kw):
    n = nt.nodes.new(kind); n.location = (x, y)
    for k, v in kw.items():
        if k.startswith('i_'):
            key = k[2:].replace('_', ' ')
            sock = n.inputs[int(key)] if key.isdigit() else n.inputs[key]
            sock.default_value = v
        else:
            setattr(n, k, v)
    return n


def L(nt, a, b): nt.links.new(a, b); return b


def math_(nt, op, a, b=None, clamp=False):
    n = N(nt, 'ShaderNodeMath', operation=op, use_clamp=clamp)
    for i, v in enumerate((a, b)):
        if v is None: continue
        if isinstance(v, (int, float)): n.inputs[i].default_value = v
        else: L(nt, v, n.inputs[i])
    return n.outputs[0]


def mix(nt, fac, a, b):
    n = N(nt, 'ShaderNodeMix', data_type='RGBA', clamp_factor=True)
    for sock, v in ((n.inputs[0], fac), (n.inputs[6], a), (n.inputs[7], b)):
        if isinstance(v, (int, float)): sock.default_value = v
        elif isinstance(v, tuple): sock.default_value = v if len(v) == 4 else (*v, 1)
        else: L(nt, v, sock)
    return n.outputs[2]


def mixf(nt, fac, a, b):
    n = N(nt, 'ShaderNodeMix', data_type='FLOAT', clamp_factor=True)
    for sock, v in ((n.inputs[0], fac), (n.inputs[2], a), (n.inputs[3], b)):
        if isinstance(v, (int, float)): sock.default_value = v
        else: L(nt, v, sock)
    return n.outputs[0]


def smooth(nt, v, lo, hi):
    n = N(nt, 'ShaderNodeMapRange', interpolation_type='SMOOTHSTEP', clamp=True)
    L(nt, v, n.inputs['Value'])
    for key, val in (('From Min', lo), ('From Max', hi)):
        if isinstance(val, (int, float)): n.inputs[key].default_value = val
        else: L(nt, val, n.inputs[key])
    return n.outputs['Result']


def attr(nt, name, kind='vec'):
    a = N(nt, 'ShaderNodeAttribute', attribute_name=name, attribute_type='GEOMETRY')
    return a.outputs['Vector'] if kind == 'vec' else a.outputs['Fac']


def coords(nt, scale=(1, 1, 1), offset_by_seed=True):
    lc = attr(nt, 'qa_lc')
    mp = N(nt, 'ShaderNodeMapping'); L(nt, lc, mp.inputs['Vector']); mp.inputs['Scale'].default_value = scale
    if offset_by_seed:
        sd = attr(nt, 'qa_seed', 'fac'); off = math_(nt, 'MULTIPLY', sd, 37.0)
        cv = N(nt, 'ShaderNodeCombineXYZ'); [L(nt, off, cv.inputs[i]) for i in range(3)]
        L(nt, cv.outputs[0], mp.inputs['Location'])
    return mp.outputs['Vector']


def noise(nt, vec, scale=4.0, detail=4.0, rough=0.55, dist=0.0, dims='3D'):
    n = N(nt, 'ShaderNodeTexNoise', noise_dimensions=dims)
    L(nt, vec, n.inputs['Vector']); n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = detail
    n.inputs['Roughness'].default_value = rough; n.inputs['Distortion'].default_value = dist
    return n.outputs['Fac']


def voronoi(nt, vec, scale=10.0, feature='F1', out='Distance', rand=1.0):
    n = N(nt, 'ShaderNodeTexVoronoi', feature=feature)
    L(nt, vec, n.inputs['Vector']); n.inputs['Scale'].default_value = scale; n.inputs['Randomness'].default_value = rand
    return n.outputs[out]


def ao(nt, dist, inside=False, samples=16):
    n = N(nt, 'ShaderNodeAmbientOcclusion', inside=inside, only_local=True, samples=samples)
    n.inputs['Distance'].default_value = dist
    return n.outputs['AO']


def sep(nt, vec):
    s = N(nt, 'ShaderNodeSeparateXYZ'); L(nt, vec, s.inputs[0]); return s.outputs


def world_pos(nt):
    return N(nt, 'ShaderNodeNewGeometry').outputs['Position']


def new_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = N(nt, 'ShaderNodeOutputMaterial', 900, 0); bsdf = N(nt, 'ShaderNodeBsdfPrincipled', 600, 0)
    L(nt, bsdf.outputs['BSDF'], out.inputs['Surface'])
    return m, nt, bsdf


def finish(m, nt, bsdf, albedo, rough, metal=0.0, height=None, bump=0.002, bump_strength=1.0, emit=None, alpha=None):
    def chan(name, v, default):
        r = N(nt, 'NodeReroute'); r.name = r.label = name
        if v is None: v = default
        if isinstance(v, (int, float)):
            val = N(nt, 'ShaderNodeValue'); val.outputs[0].default_value = v; v = val.outputs[0]
        elif isinstance(v, tuple):
            rgb = N(nt, 'ShaderNodeRGB'); rgb.outputs[0].default_value = v if len(v) == 4 else (*v, 1); v = rgb.outputs[0]
        L(nt, v, r.inputs[0]); return r.outputs[0]
    a = chan('CH_albedo', albedo, (0.5, 0.5, 0.5)); L(nt, a, bsdf.inputs['Base Color'])
    r = chan('CH_rough', rough, 0.6); L(nt, r, bsdf.inputs['Roughness'])
    mt = chan('CH_metal', metal, 0.0); L(nt, mt, bsdf.inputs['Metallic'])
    e = chan('CH_emit', emit, (0, 0, 0))
    if emit is not None:
        L(nt, e, bsdf.inputs['Emission Color']); bsdf.inputs['Emission Strength'].default_value = 1.0
    al = chan('CH_alpha', alpha, 1.0)
    if alpha is not None: L(nt, al, bsdf.inputs['Alpha']); m['qa_alpha'] = True
    if emit is not None: m['qa_emit'] = True
    if height is not None:
        b = N(nt, 'ShaderNodeBump'); b.inputs['Distance'].default_value = bump; b.inputs['Strength'].default_value = bump_strength
        L(nt, height, b.inputs['Height']); L(nt, b.outputs['Normal'], bsdf.inputs['Normal'])
    return m


def edge_cavity(nt, cav_dist=0.035, edge_dist=0.006):
    cav = math_(nt, 'SUBTRACT', 1.0, ao(nt, cav_dist))
    edge = math_(nt, 'SUBTRACT', 1.0, ao(nt, edge_dist, inside=True))
    return cav, edge


# ----------------------------------------------------------------------------- material library
def m_bronze(name='Bronze', patina=0.55, polish=0.6, scale=1.0, band=None, seams=False, soot=0.0, heat=0.0, smudge=None,
             heat_zone=((0, 0, 0.15), (0.2, 0.2, 0.2))):
    """heat > 0: heat-oxidised zone around heat_zone (centre, radii): dark red-brown core with the patina burnt off,
    ringed by a purple-to-straw temper band."""
    m, nt, b = new_mat(name); co = coords(nt, (scale, scale, scale))
    n1 = noise(nt, co, 3.0, 6, 0.6); n2 = noise(nt, co, 18.0, 3, 0.5)
    base = mix(nt, n1, (0.105, 0.064, 0.032), (0.19, 0.12, 0.058))
    ox = smooth(nt, noise(nt, co, 3.5, 6, 0.62), 0.44, 0.64)
    base = mix(nt, math_(nt, 'MULTIPLY', ox, 0.75), base, (0.032, 0.024, 0.018))
    cav, edge = edge_cavity(nt, 0.05, 0.008)
    pm = smooth(nt, math_(nt, 'ADD', math_(nt, 'MULTIPLY', cav, 2.2), math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', n2, 0.5), 0.9)), 0.55 - patina * 0.4, 0.95 - patina * 0.4)
    streak = smooth(nt, noise(nt, co, 1.6, 4, 0.6), 0.58 - patina * 0.12, 0.74)
    pm = math_(nt, 'MAXIMUM', pm, math_(nt, 'MULTIPLY', streak, 0.85 * patina))
    spots = smooth(nt, voronoi(nt, co, 9.0, 'F1'), 0.12, 0.05)
    pm = math_(nt, 'MAXIMUM', pm, math_(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', spots, smooth(nt, n2, 0.4, 0.65)), 0.7 * patina))
    pat = mix(nt, n2, (0.11, 0.22, 0.17), (0.22, 0.35, 0.28))
    col = mix(nt, pm, base, pat)
    em = smooth(nt, math_(nt, 'ADD', edge, math_(nt, 'MULTIPLY', n2, 0.25)), 0.35, 0.75)
    col = mix(nt, math_(nt, 'MULTIPLY', em, polish), col, (0.40, 0.27, 0.13))
    hgt = voronoi(nt, co, 55.0, 'SMOOTH_F1')                                    # hammered surface
    if band or seams:
        p = sep(nt, world_pos(nt)); th = N(nt, 'ShaderNodeMath', operation='ARCTAN2'); L(nt, p[1], th.inputs[0]); L(nt, p[0], th.inputs[1])
        th = th.outputs[0]
    if band:
        zc, half, amp, k = band
        wav = math_(nt, 'ADD', zc, math_(nt, 'MULTIPLY', math_(nt, 'SINE', math_(nt, 'MULTIPLY', th, k)), amp))
        d = math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', p[2], wav))
        line = math_(nt, 'SUBTRACT', 1.0, smooth(nt, d, 0.003, 0.0065))
        curl = math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', math_(nt, 'FRACT', math_(nt, 'DIVIDE', math_(nt, 'ADD', th, math.pi), TAU / k)), 0.5))
        dot = math_(nt, 'SUBTRACT', 1.0, smooth(nt, math_(nt, 'ADD', math_(nt, 'MULTIPLY', curl, 0.12),
                    math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', p[2], math_(nt, 'SUBTRACT', zc, math_(nt, 'MULTIPLY', math_(nt, 'SINE', math_(nt, 'MULTIPLY', th, k)), -amp * 0.2))))), 0.004, 0.008))
        inband = math_(nt, 'MULTIPLY', smooth(nt, p[2], zc - half, zc - half + 0.003), math_(nt, 'SUBTRACT', 1.0, smooth(nt, p[2], zc + half - 0.003, zc + half)))
        orn = math_(nt, 'MULTIPLY', math_(nt, 'MAXIMUM', line, math_(nt, 'MULTIPLY', dot, 0.8)), inband)
        hgt = math_(nt, 'ADD', math_(nt, 'MULTIPLY', hgt, 0.35), math_(nt, 'MULTIPLY', orn, 1.6))
        col = mix(nt, math_(nt, 'MULTIPLY', orn, 0.55), col, (0.50, 0.35, 0.17))
        col = mix(nt, math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', inband, orn), 0.6), col, mix(nt, n2, (0.17, 0.28, 0.22), (0.12, 0.10, 0.06)))
    if seams:
        s = math_(nt, 'ABSOLUTE', math_(nt, 'SINE', math_(nt, 'MULTIPLY', th, 2.0)))
        ln = math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', 1.0, smooth(nt, s, 0.006, 0.014)), smooth(nt, p[1], -0.15, 0.0) if False else 1.0)
        zon = math_(nt, 'MULTIPLY', smooth(nt, p[2], 0.2, 0.24), math_(nt, 'SUBTRACT', 1.0, smooth(nt, p[2], 0.54, 0.56)))
        front = smooth(nt, p[1], -0.2, -0.1)
        ln = math_(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', ln, zon), front)
        hgt = math_(nt, 'ADD', hgt, math_(nt, 'MULTIPLY', ln, 1.0))
        col = mix(nt, math_(nt, 'MULTIPLY', ln, 0.5), col, (0.45, 0.32, 0.16))
    if smudge:
        c, rr = smudge; wp = world_pos(nt)
        d = N(nt, 'ShaderNodeVectorMath', operation='DIVIDE'); L(nt, wp, d.inputs[0])
        sub = N(nt, 'ShaderNodeVectorMath', operation='SUBTRACT'); L(nt, wp, sub.inputs[0]); sub.inputs[1].default_value = c
        dv = N(nt, 'ShaderNodeVectorMath', operation='DIVIDE'); L(nt, sub.outputs[0], dv.inputs[0]); dv.inputs[1].default_value = rr
        ln = N(nt, 'ShaderNodeVectorMath', operation='LENGTH'); L(nt, dv.outputs[0], ln.inputs[0])
        sm = math_(nt, 'SUBTRACT', 1.0, smooth(nt, math_(nt, 'ADD', ln.outputs['Value'], math_(nt, 'MULTIPLY', n2, 0.5)), 0.5, 1.2))
        col = mix(nt, math_(nt, 'MULTIPLY', sm, 0.85), col, (0.03, 0.026, 0.024)); pm = math_(nt, 'MULTIPLY', pm, math_(nt, 'SUBTRACT', 1.0, sm))
    if heat:
        c, rr = heat_zone; wp = world_pos(nt)
        sub = N(nt, 'ShaderNodeVectorMath', operation='SUBTRACT'); L(nt, wp, sub.inputs[0]); sub.inputs[1].default_value = c
        dv = N(nt, 'ShaderNodeVectorMath', operation='DIVIDE'); L(nt, sub.outputs[0], dv.inputs[0]); dv.inputs[1].default_value = rr
        ln = N(nt, 'ShaderNodeVectorMath', operation='LENGTH'); L(nt, dv.outputs[0], ln.inputs[0])
        d = math_(nt, 'ADD', ln.outputs['Value'], math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', n1, 0.5), 0.45))
        core = math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', 1.0, smooth(nt, d, 0.45, 0.72)), heat)
        ring = math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', 1.0, smooth(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', d, 0.84)), 0.04, 0.14)), heat * 0.9)
        pm = math_(nt, 'MULTIPLY', pm, math_(nt, 'SUBTRACT', 1.0, core))
        col = mix(nt, core, col, mix(nt, n2, (0.045, 0.024, 0.019), (0.085, 0.042, 0.028)))
        col = mix(nt, ring, col, mix(nt, smooth(nt, d, 0.78, 0.92), (0.13, 0.065, 0.16), (0.36, 0.23, 0.09)))
    if soot:
        pz = sep(nt, world_pos(nt))[2]
        sm = math_(nt, 'MULTIPLY', soot, smooth(nt, noise(nt, co, 5.0, 3), 0.35, 0.7))
        col = mix(nt, sm, col, (0.035, 0.03, 0.028))
    rough = mixf(nt, pm, mixf(nt, em, mixf(nt, ox, 0.46, 0.62), 0.30), 0.78)
    metal = mixf(nt, pm, mixf(nt, ox, 0.7, 0.35), 0.05)
    if heat:   # oxide scale is matte: the hot core stops reading as polished bronze
        rough = mixf(nt, core, rough, 0.68); metal = mixf(nt, core, metal, 0.12)
    return finish(m, nt, b, col, rough, metal, hgt, 0.0016, 0.6)


def m_iron(name='Iron', rust=0.5):
    m, nt, b = new_mat(name); co = coords(nt, (1, 1, 1))
    n = noise(nt, co, 14.0, 5, 0.6); cav, edge = edge_cavity(nt, 0.03, 0.005)
    col = mix(nt, n, (0.045, 0.043, 0.045), (0.085, 0.08, 0.078))
    rm = smooth(nt, math_(nt, 'ADD', math_(nt, 'MULTIPLY', cav, 1.8), math_(nt, 'MULTIPLY', n, 0.6)), 0.75 - rust * 0.3, 1.1 - rust * 0.3)
    col = mix(nt, rm, col, mix(nt, n, (0.16, 0.07, 0.03), (0.24, 0.12, 0.05)))
    col = mix(nt, math_(nt, 'MULTIPLY', smooth(nt, edge, 0.4, 0.8), 0.7), col, (0.20, 0.19, 0.18))
    return finish(m, nt, b, col, mixf(nt, rm, 0.55, 0.85), mixf(nt, rm, 0.75, 0.0), voronoi(nt, co, 90, 'SMOOTH_F1'), 0.001, 0.4)


def m_stone(name='Stone', light=(0.50, 0.48, 0.44), dark=(0.33, 0.31, 0.29), scale=1.0, speck=1.0, soot=0.0, soot_z=None, chisel=1.0):
    m, nt, b = new_mat(name); co = coords(nt, (scale, scale, scale))
    n1 = noise(nt, co, 2.5, 6, 0.62, 0.3); n2 = noise(nt, co, 14.0, 4, 0.55)
    col = mix(nt, smooth(nt, n1, 0.3, 0.75), dark, light)
    sp = smooth(nt, voronoi(nt, co, 140.0), 0.0, 0.25)
    col = mix(nt, math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', 1.0, sp), 0.45 * speck), col, (0.16, 0.15, 0.14))
    sp2 = smooth(nt, voronoi(nt, co, 95.0, rand=0.9), 0.0, 0.12)
    col = mix(nt, math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', 1.0, sp2), 0.35 * speck), col, tuple(min(1.0, c * 1.7) for c in light))
    warm = smooth(nt, noise(nt, co, 1.3, 2), 0.55, 0.8)
    col = mix(nt, math_(nt, 'MULTIPLY', warm, 0.35), col, (0.52, 0.42, 0.32))
    cav, edge = edge_cavity(nt, 0.04, 0.006)
    col = mix(nt, math_(nt, 'MULTIPLY', smooth(nt, cav, 0.1, 0.6), 0.55), col, (0.14, 0.13, 0.12))
    col = mix(nt, math_(nt, 'MULTIPLY', smooth(nt, edge, 0.3, 0.8), 0.35), col, tuple(min(1.0, c * 1.45) for c in light))   # worn edges: a step lighter than the stone, not white
    if soot:
        z = sep(nt, world_pos(nt))[2]
        sm = smooth(nt, math_(nt, 'ADD', z, math_(nt, 'MULTIPLY', n1, 0.25)), soot_z[0], soot_z[1]) if soot_z else 1.0
        col = mix(nt, math_(nt, 'MULTIPLY', sm, soot), col, (0.06, 0.055, 0.05))
    hgt = math_(nt, 'ADD', math_(nt, 'MULTIPLY', n2, 0.6), math_(nt, 'MULTIPLY', voronoi(nt, co, 9.0 * chisel, 'F2'), 0.6))
    return finish(m, nt, b, col, mixf(nt, n2, 0.78, 0.9), 0.0, hgt, 0.0025, 0.7)


def m_wood(name='Walnut', a=(0.060, 0.030, 0.016), b_=(0.125, 0.064, 0.034), axis='X', ring=3.0, wear=0.55, rough=0.6, seed_tint=0.18):
    m, nt, b = new_mat(name)
    sc = {'X': (1.0, 9.0, 9.0), 'Y': (9.0, 1.0, 9.0), 'Z': (9.0, 9.0, 1.0)}[axis]
    co = coords(nt, sc)
    wv = N(nt, 'ShaderNodeTexWave', wave_type='BANDS', bands_direction='X' if axis != 'X' else 'Y')
    L(nt, co, wv.inputs['Vector']); wv.inputs['Scale'].default_value = ring; wv.inputs['Distortion'].default_value = 3.5
    wv.inputs['Detail'].default_value = 3.0; wv.inputs['Detail Scale'].default_value = 1.5
    ax = {'X': 0, 'Y': 1, 'Z': 2}[axis]
    fib = noise(nt, co, 40.0, 3, 0.6)
    g = math_(nt, 'ADD', math_(nt, 'MULTIPLY', wv.outputs['Fac'], 0.8), math_(nt, 'MULTIPLY', fib, 0.2))
    col = mix(nt, smooth(nt, g, 0.15, 0.95), a, b_)
    col = mix(nt, math_(nt, 'MULTIPLY', smooth(nt, noise(nt, co, 2.0, 2), 0.4, 0.7), 0.5), col, (a[0] * 0.7, a[1] * 0.7, a[2] * 0.7))
    sd = attr(nt, 'qa_seed', 'fac')
    col = mix(nt, math_(nt, 'MULTIPLY', sd, seed_tint), col, (0.16, 0.09, 0.045))
    cav, edge = edge_cavity(nt, 0.03, 0.005)
    col = mix(nt, math_(nt, 'MULTIPLY', smooth(nt, cav, 0.1, 0.7), 0.6), col, (0.04, 0.025, 0.015))
    col = mix(nt, math_(nt, 'MULTIPLY', smooth(nt, math_(nt, 'ADD', edge, math_(nt, 'MULTIPLY', fib, 0.3)), 0.45, 0.85), wear), col, (0.22, 0.14, 0.075))
    hgt = math_(nt, 'ADD', math_(nt, 'MULTIPLY', wv.outputs['Fac'], 0.5), math_(nt, 'MULTIPLY', fib, 0.5))
    return finish(m, nt, b, col, mixf(nt, edge, rough, rough - 0.12), 0.0, hgt, 0.0012, 0.8)


def m_bamboo(name='Bamboo', a=(0.42, 0.29, 0.12), b_=(0.58, 0.43, 0.20), axis='Z', aged=0.3):
    m, nt, b = new_mat(name)
    sc = {'X': (2.0, 60.0, 60.0), 'Y': (60.0, 2.0, 60.0), 'Z': (60.0, 60.0, 2.0)}[axis]
    co = coords(nt, sc)
    fib = noise(nt, co, 1.0, 4, 0.6); n2 = noise(nt, coords(nt, (3, 3, 3)), 2.0, 3)
    col = mix(nt, smooth(nt, fib, 0.3, 0.75), a, b_)
    col = mix(nt, math_(nt, 'MULTIPLY', smooth(nt, n2, 0.45, 0.75), aged), col, (0.30, 0.22, 0.12))
    cav, edge = edge_cavity(nt, 0.02, 0.004)
    col = mix(nt, math_(nt, 'MULTIPLY', smooth(nt, cav, 0.1, 0.6), 0.6), col, (0.13, 0.08, 0.035))
    col = mix(nt, math_(nt, 'MULTIPLY', smooth(nt, edge, 0.4, 0.8), 0.3), col, (0.70, 0.56, 0.32))
    return finish(m, nt, b, col, mixf(nt, fib, 0.38, 0.5), 0.0, fib, 0.0006, 0.6)


def m_weave(name='Weave', pitch=0.016, open_=0.0, a=(0.40, 0.28, 0.12), b_=(0.60, 0.45, 0.22), mode='flat', radius=0.3):
    """Plain over-under weave. mode='flat' uses local x/y, mode='wall' unrolls a cylinder (u = angle*radius, v = z).
    open_ > 0 punches square holes through alpha (alpha-clip)."""
    m, nt, b = new_mat(name); lc = attr(nt, 'qa_lc'); p = sep(nt, lc)
    if mode == 'wall':
        th = N(nt, 'ShaderNodeMath', operation='ARCTAN2'); L(nt, p[1], th.inputs[0]); L(nt, p[0], th.inputs[1])
        u = math_(nt, 'MULTIPLY', th.outputs[0], radius); v = p[2]
    else:
        u, v = p[0], p[1]
    U = math_(nt, 'DIVIDE', u, pitch); V = math_(nt, 'DIVIDE', v, pitch)
    fu = math_(nt, 'FRACT', U); fv = math_(nt, 'FRACT', V)
    cu = math_(nt, 'FLOOR', U); cv = math_(nt, 'FLOOR', V)
    par = math_(nt, 'MODULO', math_(nt, 'ABSOLUTE', math_(nt, 'ADD', cu, cv)), 2.0)
    w = 1.0 - open_
    su = math_(nt, 'LESS_THAN', math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', fv, 0.5)), w * 0.5)   # strand running along u
    sv = math_(nt, 'LESS_THAN', math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', fu, 0.5)), w * 0.5)
    top_u = math_(nt, 'MULTIPLY', su, math_(nt, 'MAXIMUM', par, math_(nt, 'SUBTRACT', 1.0, sv)))
    hu = math_(nt, 'MULTIPLY', math_(nt, 'SINE', math_(nt, 'MULTIPLY', fv, math.pi)), math_(nt, 'MULTIPLY', math_(nt, 'SINE', math_(nt, 'MULTIPLY', fu, math.pi)), 0.6))
    hv = math_(nt, 'MULTIPLY', math_(nt, 'SINE', math_(nt, 'MULTIPLY', fu, math.pi)), math_(nt, 'MULTIPLY', math_(nt, 'SINE', math_(nt, 'MULTIPLY', fv, math.pi)), 0.6))
    hgt = mixf(nt, top_u, math_(nt, 'MULTIPLY', hv, sv), math_(nt, 'ADD', hu, 0.4))
    fib = noise(nt, coords(nt, (4, 4, 4)), 30.0, 3)
    col = mix(nt, math_(nt, 'ADD', math_(nt, 'MULTIPLY', fib, 0.6), math_(nt, 'MULTIPLY', top_u, 0.3)), a, b_)
    shade = smooth(nt, hgt, 0.0, 0.5)
    col = mix(nt, math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', 1.0, shade), 0.55), col, (0.10, 0.06, 0.025))
    alpha = math_(nt, 'MAXIMUM', su, sv) if open_ > 0 else None
    return finish(m, nt, b, col, 0.55, 0.0, hgt, 0.0015, 0.8, alpha=alpha)


def m_celadon(name='Celadon', glaze_z=None, drip=0.05, clay=(0.46, 0.41, 0.35), g1=(0.30, 0.44, 0.37), g2=(0.44, 0.57, 0.49), crackle=1.0, incise=None, glaze_rough=0.16):
    m, nt, b = new_mat(name); co = coords(nt, (1, 1, 1), False)
    n = noise(nt, co, 6.0, 4); cav, edge = edge_cavity(nt, 0.02, 0.004)
    flow = noise(nt, N(nt, 'ShaderNodeMapping', vector_type='POINT').outputs[0] if False else co, 6.0, 4)
    gl = mix(nt, smooth(nt, n, 0.3, 0.8), g1, g2)
    gl = mix(nt, math_(nt, 'MULTIPLY', smooth(nt, cav, 0.05, 0.4), 0.8), gl, (0.17, 0.30, 0.24))          # glaze pools greener in recesses
    gl = mix(nt, math_(nt, 'MULTIPLY', smooth(nt, edge, 0.4, 0.8), 0.6), gl, (0.66, 0.70, 0.60))          # thin glaze on edges
    ck = math_(nt, 'SUBTRACT', 1.0, smooth(nt, voronoi(nt, co, 26.0, 'DISTANCE_TO_EDGE'), 0.0, 0.025))
    gl = mix(nt, math_(nt, 'MULTIPLY', ck, 0.25 * crackle), gl, (0.20, 0.26, 0.21))
    if glaze_z is not None:
        z = sep(nt, world_pos(nt))[2]; th = N(nt, 'ShaderNodeMath', operation='ARCTAN2'); pp = sep(nt, world_pos(nt))
        L(nt, pp[1], th.inputs[0]); L(nt, pp[0], th.inputs[1])
        dr = N(nt, 'ShaderNodeTexNoise', noise_dimensions='1D'); L(nt, math_(nt, 'MULTIPLY', th.outputs[0], 3.0), dr.inputs['W'])
        dr.inputs['Scale'].default_value = 2.4; dr.inputs['Detail'].default_value = 2
        drips = math_(nt, 'MULTIPLY', math_(nt, 'POWER', smooth(nt, dr.outputs['Fac'], 0.45, 0.85), 3.0), drip)
        gm = smooth(nt, math_(nt, 'ADD', z, drips), glaze_z - 0.004, glaze_z + 0.004)
        cl = mix(nt, noise(nt, coords(nt, (1, 1, 1), False), 25.0, 3), clay, (clay[0] * 0.8, clay[1] * 0.8, clay[2] * 0.8))
        cl = mix(nt, math_(nt, 'MULTIPLY', smooth(nt, cav, 0.1, 0.6), 0.5), cl, (0.18, 0.16, 0.13))
        rim = math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', 1.0, smooth(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', gm, 0.5)), 0.0, 0.5)), 0.6)
        col = mix(nt, gm, cl, mix(nt, rim, gl, (0.24, 0.36, 0.30)))
        rough = mixf(nt, gm, 0.86, glaze_rough)
        hgt = mixf(nt, gm, noise(nt, co, 60.0, 3), math_(nt, 'MULTIPLY', n, 0.2))
    else:
        col, rough, hgt = gl, glaze_rough, math_(nt, 'MULTIPLY', n, 0.2)
    if incise:
        zc, amp, k, wdt = incise
        p = sep(nt, world_pos(nt)); th = N(nt, 'ShaderNodeMath', operation='ARCTAN2'); L(nt, p[1], th.inputs[0]); L(nt, p[0], th.inputs[1])
        th = th.outputs[0]
        wv = math_(nt, 'ADD', zc, math_(nt, 'MULTIPLY', math_(nt, 'SINE', math_(nt, 'MULTIPLY', th, k)), amp))
        ln = math_(nt, 'SUBTRACT', 1.0, smooth(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', p[2], wv)), wdt * 0.4, wdt))
        cur = math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', math_(nt, 'FRACT', math_(nt, 'DIVIDE', math_(nt, 'ADD', th, math.pi), TAU / k)), 0.5))
        sp = math_(nt, 'SUBTRACT', 1.0, smooth(nt, math_(nt, 'ADD', math_(nt, 'MULTIPLY', cur, 0.05),
             math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', p[2], math_(nt, 'ADD', zc, math_(nt, 'MULTIPLY', math_(nt, 'COSINE', math_(nt, 'MULTIPLY', th, k)), amp * 0.6))))), wdt * 0.4, wdt))
        for zz in (zc - amp * 2.4, zc + amp * 2.4):
            ln = math_(nt, 'MAXIMUM', ln, math_(nt, 'SUBTRACT', 1.0, smooth(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', p[2], zz)), wdt * 0.3, wdt * 0.8)))
        ln = math_(nt, 'MAXIMUM', ln, math_(nt, 'MULTIPLY', sp, 0.8))
        hgt = math_(nt, 'SUBTRACT', hgt, math_(nt, 'MULTIPLY', ln, 1.2))
        col = mix(nt, math_(nt, 'MULTIPLY', ln, 0.6), col, (0.15, 0.27, 0.21))
    return finish(m, nt, b, col, rough, 0.0, hgt, 0.0012, 0.6)


def m_cloth(name='Linen', base=(0.74, 0.70, 0.60), stain=(0.52, 0.42, 0.28), stain_axis_z=None, pitch=0.0018):
    m, nt, b = new_mat(name); co = coords(nt, (1, 1, 1))
    p = sep(nt, co); wx = math_(nt, 'SINE', math_(nt, 'DIVIDE', p[0], pitch)); wz = math_(nt, 'SINE', math_(nt, 'DIVIDE', math_(nt, 'ADD', p[2], p[1]), pitch))
    weave = math_(nt, 'MULTIPLY', math_(nt, 'ADD', wx, wz), 0.5)
    n = noise(nt, co, 9.0, 4); cav, edge = edge_cavity(nt, 0.03, 0.004)
    col = mix(nt, math_(nt, 'MULTIPLY', n, 0.4), base, (base[0] * 0.86, base[1] * 0.86, base[2] * 0.84))
    if stain_axis_z:
        z = sep(nt, world_pos(nt))[2]
        sm = math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', 1.0, smooth(nt, math_(nt, 'ADD', z, math_(nt, 'MULTIPLY', n, 0.06)), stain_axis_z[0], stain_axis_z[1])), 0.85)
        col = mix(nt, sm, col, stain)
    col = mix(nt, math_(nt, 'MULTIPLY', smooth(nt, cav, 0.1, 0.6), 0.45), col, (0.30, 0.27, 0.22))
    return finish(m, nt, b, col, 0.9, 0.0, math_(nt, 'ADD', math_(nt, 'MULTIPLY', weave, 0.4), math_(nt, 'MULTIPLY', n, 0.6)), 0.0008, 0.5)


def m_simple(name, c1, c2=None, rough=0.6, metal=0.0, nscale=8.0, bump=0.0006, cav_col=None, edge_col=None, emit=None, alpha=None):
    m, nt, b = new_mat(name); co = coords(nt, (1, 1, 1))
    n = noise(nt, co, nscale, 4)
    col = mix(nt, smooth(nt, n, 0.3, 0.8), c1, c2 or c1)
    cav, edge = edge_cavity(nt, 0.02, 0.004)
    if cav_col: col = mix(nt, math_(nt, 'MULTIPLY', smooth(nt, cav, 0.1, 0.6), 0.6), col, cav_col)
    if edge_col: col = mix(nt, math_(nt, 'MULTIPLY', smooth(nt, edge, 0.4, 0.8), 0.5), col, edge_col)
    return finish(m, nt, b, col, rough, metal, n, bump, 0.5, emit=emit, alpha=alpha)


def m_refractory(name='Refractory', heat=0.0, floor_z=0.19):
    """Firebox lining: dark sooty brick, glowing near the coal bed when heat > 0."""
    m, nt, b = new_mat(name); wp = world_pos(nt)
    br = N(nt, 'ShaderNodeTexBrick'); L(nt, wp, br.inputs['Vector']); br.inputs['Scale'].default_value = 14.0
    br.inputs['Mortar Size'].default_value = 0.025; br.inputs['Color1'].default_value = (0.11, 0.10, 0.095, 1)
    br.inputs['Color2'].default_value = (0.07, 0.065, 0.06, 1); br.inputs['Mortar'].default_value = (0.03, 0.028, 0.026, 1)
    n = noise(nt, wp, 20.0, 4)
    col = mix(nt, math_(nt, 'MULTIPLY', n, 0.4), br.outputs['Color'], (0.04, 0.035, 0.03))
    emit = None
    if heat:
        z = sep(nt, wp)[2]; g = math_(nt, 'SUBTRACT', 1.0, smooth(nt, z, floor_z, floor_z + 0.16))
        emit = mix(nt, math_(nt, 'MULTIPLY', math_(nt, 'POWER', g, 2.0), heat), (0, 0, 0), (0.75, 0.13, 0.02))
    return finish(m, nt, b, col, 0.92, 0.0, math_(nt, 'ADD', math_(nt, 'MULTIPLY', br.outputs['Fac'], 1.0), math_(nt, 'MULTIPLY', n, 0.4)), 0.002, 0.8, emit=emit)


def m_coal(name='Coal', heat=0.0):
    m, nt, b = new_mat(name); co = coords(nt, (1, 1, 1)); n = noise(nt, co, 30.0, 4)
    cav, _ = edge_cavity(nt, 0.02, 0.004)
    col = mix(nt, n, (0.035, 0.032, 0.03), (0.12, 0.115, 0.11))
    emit = None
    if heat:
        crust = smooth(nt, voronoi(nt, co, 45.0, 'F1'), 0.10, 0.28)                  # dark ash crust islands
        glow = math_(nt, 'MULTIPLY', smooth(nt, noise(nt, co, 22.0, 3), 0.35, 0.6), crust)
        glow = math_(nt, 'MAXIMUM', glow, math_(nt, 'MULTIPLY', smooth(nt, cav, 0.15, 0.6), 0.9))
        emit = mix(nt, math_(nt, 'MULTIPLY', glow, heat), (0.0, 0.0, 0.0), mix(nt, n, (0.85, 0.12, 0.015), (1.0, 0.36, 0.05)))
        col = mix(nt, glow, col, (0.25, 0.05, 0.01))
    return finish(m, nt, b, col, 0.9, 0.0, n, 0.002, 0.6, emit=emit)


def m_glass(name='Glass', color=(0.80, 0.90, 0.86), alpha=0.14, rough=0.05):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = rough
    b.inputs['Alpha'].default_value = alpha; b.inputs['IOR'].default_value = 1.45
    m.surface_render_method = 'BLENDED'; m.use_backface_culling = False; m['qa_nobake'] = True
    return m


# ----------------------------------------------------------------------------- game mesh + bake
def game_mesh(name, objs, gcoll):
    """Join evaluated copies of every renderable part (cutters excluded) into one mesh with one UV atlas."""
    dg = bpy.context.evaluated_depsgraph_get(); bake, keep = [], []; ids = {'Body': 0}
    for o in objs:
        if o.type != 'MESH' or o.get('qa_cutter') or o.hide_render: continue
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        me.transform(o.matrix_world)
        if not len(me.polygons): bpy.data.meshes.remove(me); continue
        nid = ids.setdefault(o.get('qa_node', 'Body'), len(ids))
        at = me.attributes.new('qa_node', 'INT', 'FACE'); at.data.foreach_set('value', [nid] * len(me.polygons))
        c = bpy.data.objects.new(o.name + '_G', me); gcoll.objects.link(c)
        nob = any(m and m.get('qa_nobake') for m in me.materials)
        (keep if nob else bake).append(c)
    def join(lst, nm, reset_uv=True):
        if not lst: return None
        select_only(lst, lst[0]); bpy.ops.object.join(); g = bpy.context.view_layer.objects.active; g.name = nm; g.data.name = nm + '_Mesh'
        if reset_uv:   # the baked group gets a fresh atlas; unbaked parts (water flow UVs, foliage) keep their own UVs
            for uv in list(g.data.uv_layers): g.data.uv_layers.remove(uv)
            g.data.uv_layers.new(name='UVMap')
        return g
    G = join(bake, name); dissolve_degenerate(G)
    for v in G.data.vertices:   # props rest on z = 0: jitter + bevel can push a sole a few mm below; flatten it, refuse anything larger
        if v.co.z < 0:
            assert v.co.z > -0.01, f'{name}: vertex {v.index} at z={v.co.z:.4f} is below the ground'
            v.co.z = 0.0
    sq = bpy.data.images.get('QA_square') or bpy.data.images.new('QA_square', 8, 8)
    for m in G.data.materials:   # UV unwrap/pack correct islands for the aspect of the active image node: make it a square one
        if m and m.use_nodes:      # (the bake reuses this QA_BAKE node for its targets)
            t = m.node_tree.nodes.get('QA_BAKE') or N(m.node_tree, 'ShaderNodeTexImage', 1100, 300)
            t.name = 'QA_BAKE'; t.image = sq; m.node_tree.nodes.active = t
    select_only([G], G); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(62), island_margin=0.004, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    uvkeep = G.data.attributes.get('qa_uv_keep')   # FLOAT_VECTOR, not FLOAT2: a FLOAT2 corner attribute is a UV map and would be dropped above
    if uvkeep:   # parts that bring their own unwrap (corner attribute qa_uv_keep, face flag qa_uv_keep_f) keep it instead of smart-project strips
        bpy.ops.object.mode_set(mode='OBJECT')
        uvkeep = G.data.attributes['qa_uv_keep']   # re-fetch: leaving edit mode rebuilt the mesh data
        flag = G.data.attributes['qa_uv_keep_f'].data; uv = G.data.uv_layers.active.data
        for poly in G.data.polygons:
            if flag[poly.index].value:
                for li in poly.loop_indices: uv[li].uv = uvkeep.data[li].vector[:2]
        kept = {G.data.loops[li].edge_index for poly in G.data.polygons if flag[poly.index].value for li in poly.loop_indices}
        for e in G.data.edges:   # smart-project's seams would cut the kept sheet into slivers when packing
            if e.index in kept: e.use_seam = False
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.context.scene.tool_settings.use_uv_select_sync = True   # UVs written from Python carry no UV selection: let the ops follow the mesh selection
    bpy.ops.uv.average_islands_scale()   # texel density follows real surface area: terrain gets the atlas, not grass blades
    boost = {i: m['qa_texel'] for i, m in enumerate(G.data.materials) if m and m.get('qa_texel')}
    if boost:   # hero surfaces (material['qa_texel'] = linear factor) get more of the atlas than their area alone gives them
        bpy.ops.object.mode_set(mode='OBJECT')
        uv = G.data.uv_layers.active.data
        for poly in G.data.polygons:
            f = boost.get(poly.material_index)
            if f:
                for li in poly.loop_indices: uv[li].uv = uv[li].uv * f
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(rotate=True, margin=0.004)
    bpy.ops.object.mode_set(mode='OBJECT')
    K = join(keep, name + '_Clear', reset_uv=False)
    G['qa_nodes'] = json.dumps(sorted(ids, key=ids.get))
    return G, K


def split_nodes(G, key):
    names = json.loads(G['qa_nodes']); out = [G]
    if len(names) == 1: return out
    def keep_only(o, test):
        bm = bmesh.new(); bm.from_mesh(o.data); lay = bm.faces.layers.int['qa_node']
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if not test(f[lay])], context='FACES'); bm.to_mesh(o.data); bm.free()
    for nid, nm in enumerate(names[1:], 1):
        c = G.copy(); c.data = G.data.copy(); c.name = f'{key}_{nm}_LOD0'; G.users_collection[0].objects.link(c)
        keep_only(c, lambda v, nid=nid: v == nid); out.append(c)
    keep_only(G, lambda v: v == 0)
    return out


def _img_np(img):
    a = np.empty(img.size[0] * img.size[1] * 4, np.float32); img.pixels.foreach_get(a); return a.reshape(img.size[1], img.size[0], 4)


def _np_img(name, arr, colorspace, path):
    h, w = arr.shape[:2]; img = bpy.data.images.new(name, w, h, alpha=True, float_buffer=False)
    img.colorspace_settings.name = colorspace; img.pixels.foreach_set(arr.astype(np.float32).ravel())
    img.filepath_raw = str(path); img.file_format = 'PNG'; img.save(); return img


def bake_asset(G, key, tdir, res=1024, ao_samples=96):
    """Bake every material on G into image maps; returns dict of saved images."""
    s = bpy.context.scene; gpu(s, 1); s.render.bake.margin = 6; s.render.bake.margin_type = 'EXTEND'
    s.render.bake.use_clear = True; s.render.bake.target = 'IMAGE_TEXTURES'
    mats = [m for m in G.data.materials if m]
    has_emit = any(m.get('qa_emit') for m in mats); has_alpha = any(m.get('qa_alpha') for m in mats)
    tdir.mkdir(parents=True, exist_ok=True); select_only([G], G)
    # Only G may be hit by bake rays: the procedural source parts sit exactly on G and would occlude everything
    # (AO pass and the shader AO used for cavity/edge weathering).
    hidden = [o for o in s.objects if o is not G and o.type == 'MESH' and not o.hide_render]
    for o in hidden: o.hide_render = True
    if s.world is None: s.world = bpy.data.worlds.new('QA_BakeWorld')
    mn, mx = bbox([G]); s.world.light_settings.distance = min(0.35, max(0.03, (Vector(mx) - Vector(mn)).length * 0.25))
    def target(nm, cs):
        img = bpy.data.images.new(f'{key}_{nm}', res, res, alpha=False, float_buffer=True); img.colorspace_settings.name = cs
        for m in mats:
            t = m.node_tree.nodes.get('QA_BAKE') or N(m.node_tree, 'ShaderNodeTexImage', 1100, 300)
            t.name = 'QA_BAKE'; t.image = img; m.node_tree.nodes.active = t
        return img
    def rewire(ch):
        for m in mats:
            nt = m.node_tree; out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
            if ch is None:
                L(nt, next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED').outputs['BSDF'], out.inputs['Surface']); continue
            e = nt.nodes.get('QA_EMIT') or N(nt, 'ShaderNodeEmission', 800, 300); e.name = 'QA_EMIT'
            r = next(n for n in nt.nodes if n.type == 'REROUTE' and n.name == ch)
            L(nt, r.outputs[0], e.inputs['Color']); e.inputs['Strength'].default_value = 1.0
            L(nt, e.outputs['Emission'], out.inputs['Surface'])
    maps = {}
    chans = [('albedo', 'CH_albedo', 'sRGB'), ('rough', 'CH_rough', 'Non-Color'), ('metal', 'CH_metal', 'Non-Color')]
    if has_emit: chans.append(('emit', 'CH_emit', 'sRGB'))
    if has_alpha: chans.append(('alpha', 'CH_alpha', 'Non-Color'))
    s.cycles.samples = 4
    for nm, ch, cs in chans:
        img = target(nm, 'Linear Rec.709' if cs == 'sRGB' else 'Non-Color'); rewire(ch)
        bpy.ops.object.bake(type='EMIT'); maps[nm] = _img_np(img)
    rewire(None)
    img = target('ao', 'Non-Color'); s.cycles.samples = ao_samples; bpy.ops.object.bake(type='AO'); maps['ao'] = _img_np(img)
    img = target('normal', 'Non-Color'); s.cycles.samples = 4; s.render.bake.normal_space = 'TANGENT'
    bpy.ops.object.bake(type='NORMAL'); maps['normal'] = _img_np(img)
    for m in mats:
        t = m.node_tree.nodes.get('QA_BAKE'); t and m.node_tree.nodes.remove(t)
    # compose
    aov = np.clip(maps['ao'][..., 0], 0, 1); aof = 0.35 + 0.65 * aov
    lin = np.clip(maps['albedo'][..., :3], 0, 1) * aof[..., None]
    srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(lin, 1 / 2.4) - 0.055)
    a = np.ones_like(aov) if not has_alpha else (maps['alpha'][..., 0] > 0.5).astype(np.float32)
    out = {}
    out['BaseColor'] = _np_img(f'T_{key}_BaseColor', np.dstack([srgb, a]), 'sRGB', tdir / f'T_{key}_BaseColor.png')
    orm = np.dstack([aov, np.clip(maps['rough'][..., 0], 0.04, 1), np.clip(maps['metal'][..., 0], 0, 1), np.ones_like(aov)])
    out['ORM'] = _np_img(f'T_{key}_ORM', orm, 'Non-Color', tdir / f'T_{key}_ORM.png')
    out['Normal'] = _np_img(f'T_{key}_Normal', np.dstack([maps['normal'][..., :3], np.ones_like(aov)]), 'Non-Color', tdir / f'T_{key}_Normal.png')
    if has_emit:
        e = np.clip(maps['emit'][..., :3], 0, 1); e = np.where(e <= 0.0031308, e * 12.92, 1.055 * np.power(e, 1 / 2.4) - 0.055)
        out['Emissive'] = _np_img(f'T_{key}_Emissive', np.dstack([e, np.ones_like(aov)]), 'sRGB', tdir / f'T_{key}_Emissive.png')
    for o in hidden: o.hide_render = False
    return out, has_alpha


def game_material(key, imgs, alpha=False, emit_strength=3.0):
    m, nt, b = new_mat(f'M_{key}')
    bc = N(nt, 'ShaderNodeTexImage', -600, 300, image=imgs['BaseColor']); L(nt, bc.outputs['Color'], b.inputs['Base Color'])
    orm = N(nt, 'ShaderNodeTexImage', -600, 0, image=imgs['ORM']); sp = N(nt, 'ShaderNodeSeparateColor', -300, 0)
    L(nt, orm.outputs['Color'], sp.inputs['Color']); L(nt, sp.outputs['Green'], b.inputs['Roughness']); L(nt, sp.outputs['Blue'], b.inputs['Metallic'])
    nm = N(nt, 'ShaderNodeTexImage', -600, -300, image=imgs['Normal']); nmap = N(nt, 'ShaderNodeNormalMap', -300, -300)
    L(nt, nm.outputs['Color'], nmap.inputs['Color']); L(nt, nmap.outputs['Normal'], b.inputs['Normal'])
    for i in (orm, nm): i.image.colorspace_settings.name = 'Non-Color'
    if 'Emissive' in imgs:
        em = N(nt, 'ShaderNodeTexImage', -600, -600, image=imgs['Emissive']); L(nt, em.outputs['Color'], b.inputs['Emission Color'])
        b.inputs['Emission Strength'].default_value = emit_strength
    if alpha:
        # Math:Round on the alpha path is what the glTF exporter reads as alphaMode MASK (cutoff 0.5); a direct link
        # exports as BLEND and engines sort the weave as transparent
        L(nt, math_(nt, 'ROUND', bc.outputs['Alpha']), b.inputs['Alpha'])
        m.surface_render_method = 'DITHERED'; m.use_backface_culling = False
        try: m.blend_method = 'CLIP'
        except Exception: pass
    return m


def clean_uvs(o):
    for uv in o.data.uv_layers:
        a = np.zeros(len(uv.data) * 2, np.float32); uv.data.foreach_get('uv', a)
        if np.isnan(a).any(): uv.data.foreach_set('uv', np.nan_to_num(a, nan=0.0))


def dissolve_degenerate(o):
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-5); bm.to_mesh(o.data); bm.free()


def make_lods(obj, ratios=(0.5, 0.22), gcoll=None):
    lods = []
    for i, r in enumerate(ratios, 1):
        c = obj.copy(); c.data = obj.data.copy(); c.name = f'{obj.name}_LOD{i}'; (gcoll or obj.users_collection[0]).objects.link(c)
        d = c.modifiers.new('Decimate', 'DECIMATE'); d.ratio = r; d.use_collapse_triangulate = True
        apply_mods(c); clean_uvs(c); lods.append(c)
    return lods


def tri_count(o):
    o.data.calc_loop_triangles(); return len(o.data.loop_triangles)


def export(objs, path_glb, path_fbx=None, fbx_objs=None):
    path_glb.parent.mkdir(parents=True, exist_ok=True)
    select_only(objs, objs[0])
    bpy.ops.export_scene.gltf(filepath=str(path_glb), export_format='GLB', use_selection=True, export_apply=True,
                              export_yup=True, export_image_format='AUTO', export_materials='EXPORT', export_extras=False)
    if path_fbx:
        select_only(fbx_objs or objs, (fbx_objs or objs)[0])
        bpy.ops.export_scene.fbx(filepath=str(path_fbx), use_selection=True, apply_scale_options='FBX_SCALE_ALL',
                                 axis_forward='-Z', axis_up='Y', bake_space_transform=True, mesh_smooth_type='FACE',
                                 use_tspace=True, path_mode='RELATIVE', embed_textures=False, add_leaf_bones=False)


def glb_roundtrip(path):
    """Re-import a GLB into an empty scene and return (tris, bbox min, bbox max, materials, images)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    tris = sum(tri_count(o) for o in new); pts = [o.matrix_world @ Vector(c) for o in new for c in o.bound_box]
    mn = [min(p[i] for p in pts) for i in range(3)]; mx = [max(p[i] for p in pts) for i in range(3)]
    mats = sorted({m.name for o in new for m in o.data.materials if m})
    for o in new: bpy.data.objects.remove(o)
    return tris, mn, mx, mats


def bbox(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


def bvh_of(o, mat=None):
    me = o.data; mw = mat or o.matrix_world
    verts = [mw @ v.co for v in me.vertices]; polys = [tuple(p.vertices) for p in me.polygons]
    return BVHTree.FromPolygons(verts, polys, all_triangles=False)


def mesh_health(o):
    bm = bmesh.new(); bm.from_mesh(o.data)
    nm = sum(1 for e in bm.edges if not e.is_manifold); loose = sum(1 for v in bm.verts if not v.link_edges)
    zero = sum(1 for f in bm.faces if f.calc_area() < 1e-9); bm.free()
    return {'nonManifoldEdges': nm, 'looseVerts': loose, 'zeroAreaFaces': zero}


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ----------------------------------------------------------------------------- preview rendering
VIEWS = [('01_front', 0, 8), ('02_front_right', 45, 14), ('03_right', 90, 8), ('04_back_right', 135, 14), ('05_back', 180, 8),
         ('06_back_left', 225, 14), ('07_left', 270, 8), ('08_front_left', 315, 14), ('09_top', 0, 89), ('10_high_front', 0, 38)]


def studio(style='neutral', ground=True):
    s = bpy.context.scene; w = bpy.data.worlds.new('QA_World'); s.world = w; w.use_nodes = True; nt = w.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = N(nt, 'ShaderNodeOutputWorld', 600, 0); lp = N(nt, 'ShaderNodeLightPath', -400, 200)
    env = N(nt, 'ShaderNodeBackground', 0, 0); cam = N(nt, 'ShaderNodeBackground', 0, -200); mx = N(nt, 'ShaderNodeMixShader', 300, 0)
    L(nt, lp.outputs['Is Camera Ray'], mx.inputs[0]); L(nt, env.outputs[0], mx.inputs[1]); L(nt, cam.outputs[0], mx.inputs[2]); L(nt, mx.outputs[0], out.inputs[0])
    sky = N(nt, 'ShaderNodeTexGradient', -600, 0); tc = N(nt, 'ShaderNodeTexCoord', -900, 0); L(nt, tc.outputs['Generated'], sky.inputs[0])
    if style == 'neutral':
        env.inputs['Color'].default_value = (0.55, 0.55, 0.55, 1); env.inputs['Strength'].default_value = 0.55
        cam.inputs['Color'].default_value = (0.78, 0.77, 0.75, 1); cam.inputs['Strength'].default_value = 1.0
        lights = [((-3, -4, 5), 480, (1, 1, 1), 2.5), ((4, -2, 2.5), 180, (1, 1, 1), 3.0), ((1, 4, 4), 260, (1, 1, 1), 2.0)]
    else:
        env.inputs['Color'].default_value = (0.42, 0.52, 0.56, 1); env.inputs['Strength'].default_value = 0.45
        cam.inputs['Color'].default_value = (0.60, 0.66, 0.64, 1); cam.inputs['Strength'].default_value = 1.0
        lights = [((-3.5, -3, 4.5), 900, (1.0, 0.82, 0.62), 1.6), ((4, -3, 2), 160, (0.62, 0.78, 1.0), 3.5), ((1.5, 4.5, 3.2), 700, (1.0, 0.86, 0.70), 1.2)]
    for i, (loc, pw, col, size) in enumerate(lights):
        ld = bpy.data.lights.new(f'QA_L{i}', 'AREA'); ld.energy = pw; ld.color = col; ld.size = size
        lo = bpy.data.objects.new(f'QA_L{i}', ld); s.collection.objects.link(lo); lo.location = loc
        lo.rotation_euler = (Vector((0, 0, 0.4)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    if ground:
        gm = bpy.data.materials.new('QA_Ground'); gm.use_nodes = True; gb = gm.node_tree.nodes.get('Principled BSDF')
        gb.inputs['Base Color'].default_value = (0.62, 0.61, 0.58, 1) if style == 'neutral' else (0.34, 0.37, 0.34, 1); gb.inputs['Roughness'].default_value = 0.9
        bpy.ops.mesh.primitive_plane_add(size=40); g = bpy.context.active_object; g.name = 'QA_Ground'; g.data.materials.append(gm)
        g.is_shadow_catcher = False
    s.view_settings.view_transform = 'AgX'; s.view_settings.look = 'AgX - Base Contrast' if style == 'stylized' else 'None'
    s.cycles.use_denoising = True
    return s


def camera_fit(objs, yaw_deg, pitch_deg, lens=85, margin=1.18, target=None):
    s = bpy.context.scene; mn, mx = bbox(objs)
    c = Vector(((mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, (mn[2] + mx[2]) / 2)) if target is None else Vector(target)
    rad = max(0.05, (Vector(mx) - Vector(mn)).length / 2)
    cam = s.camera or bpy.data.objects.new('QA_Cam', bpy.data.cameras.new('QA_Cam'))
    if not s.camera: s.collection.objects.link(cam); s.camera = cam
    cam.data.lens = lens; cam.data.sensor_width = 36; cam.data.clip_start = 0.005; cam.data.clip_end = 200
    fov = 2 * math.atan(18 / lens); d = rad * margin / math.sin(fov / 2)
    y, p = math.radians(yaw_deg), math.radians(pitch_deg)
    dirv = Vector((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p)))
    cam.location = c + dirv * d; cam.rotation_euler = (-dirv).to_track_quat('-Z', 'Y').to_euler()
    return cam


def render(path, res=1024, samples=48):
    s = bpy.context.scene; s.render.resolution_x = s.render.resolution_y = res; s.render.resolution_percentage = 100
    s.cycles.samples = samples; s.render.filepath = str(path); s.render.image_settings.file_format = 'PNG'
    Path(path).parent.mkdir(parents=True, exist_ok=True); bpy.ops.render.render(write_still=True)


def weld(o, dist=2e-5):
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
    o.data.set_sharp_from_angle(angle=math.radians(30)); return o


# ----------------------------------------------------------------------------- extra helpers (B03-B12)
def orient(o, a, b):
    a, b = Vector(a), Vector(b); o.location = a; o.rotation_euler = (b - a).to_track_quat('Z', 'Y').to_euler(); return o


def pole(name, a, b, r, mat, segs=12, node_every=0.17, ridge=0.12, cap=True):
    """Bamboo pole from a to b with node ridges."""
    L_ = (Vector(b) - Vector(a)).length; n = max(1, int(L_ / node_every)); prof = [(0, 0), (r * 0.96, 0)] if cap else [(r * 0.96, 0)]
    for i in range(1, n + 1):
        z = min(L_ - 0.004, i * L_ / (n + 0.5))
        prof += [(r, z - 0.012), (r * (1 + ridge), z - 0.003), (r * (1 + ridge * 0.6), z + 0.003), (r * 0.99, z + 0.01)]
    prof += [(r, L_ - 0.002), (r * 0.94, L_)] + ([(0, L_)] if cap else [])
    o = lathe(name, prof, mat, segs=segs, sharp=50); return orient(o, a, b)


def rod(name, a, b, r, mat, segs=12, bevel=0.0):
    L_ = (Vector(b) - Vector(a)).length
    o = lathe(name, [(0, 0), (r * 0.9, 0), (r, max(0.001, min(bevel, L_ / 3))), (r, L_ - max(0.001, min(bevel, L_ / 3))), (r * 0.9, L_), (0, L_)], mat, segs=segs, sharp=50)
    return orient(o, a, b)


def superlathe(name, prof, mat, segs=48, n_of_r=None, sharp=40):
    """Lathe whose cross-section is a superellipse (rounded square). n_of_r(r) -> exponent (2 = circle)."""
    o = lathe(name, prof, mat, segs=segs, sharp=sharp)
    for v in o.data.vertices:
        x, y = v.co.x, v.co.y; r = math.hypot(x, y)
        if r < 1e-6: continue
        n = n_of_r(r) if n_of_r else 4.0; c, s_ = abs(x) / r, abs(y) / r
        k = (c ** n + s_ ** n) ** (-1.0 / n)
        v.co.x, v.co.y = x * k, y * k
    return o


def tag_node(objs, node):
    for o in objs: o['qa_node'] = node
    return objs


def m_endgrain(name='EndGrain', a=(0.30, 0.20, 0.11), b_=(0.48, 0.34, 0.19)):
    m, nt, b = new_mat(name); p = sep(nt, attr(nt, 'qa_lc'))
    r = N(nt, 'ShaderNodeVectorMath', operation='LENGTH'); cx = N(nt, 'ShaderNodeCombineXYZ'); L(nt, p[0], cx.inputs[0]); L(nt, p[1], cx.inputs[1])
    L(nt, cx.outputs[0], r.inputs[0]); rr = r.outputs['Value']
    n = noise(nt, coords(nt, (1, 1, 1)), 30.0, 3)
    ring = math_(nt, 'SINE', math_(nt, 'MULTIPLY', math_(nt, 'ADD', rr, math_(nt, 'MULTIPLY', n, 0.004)), 420.0))
    col = mix(nt, smooth(nt, ring, -0.6, 0.9), a, b_)
    crack = math_(nt, 'SUBTRACT', 1.0, smooth(nt, voronoi(nt, coords(nt, (1, 1, 1)), 18.0, 'DISTANCE_TO_EDGE'), 0.0, 0.02))
    col = mix(nt, math_(nt, 'MULTIPLY', crack, 0.5), col, (0.12, 0.07, 0.04))
    return finish(m, nt, b, col, 0.8, 0.0, ring, 0.0006, 0.5)


def m_bark(name='Bark'):
    m, nt, b = new_mat(name); co = coords(nt, (42, 42, 9))
    n = noise(nt, co, 3.0, 6, 0.65, 1.5); v = voronoi(nt, co, 3.0, 'DISTANCE_TO_EDGE')
    col = mix(nt, smooth(nt, n, 0.3, 0.7), (0.05, 0.04, 0.03), (0.16, 0.13, 0.10))
    col = mix(nt, math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', 1.0, smooth(nt, v, 0.0, 0.08)), 0.7), col, (0.025, 0.02, 0.015))
    return finish(m, nt, b, col, 0.9, 0.0, math_(nt, 'ADD', n, smooth(nt, v, 0.0, 0.1)), 0.003, 0.9)


def m_slips(name='Slips'):
    """Bamboo slips with brushed botanical sprigs (no readable text)."""
    m, nt, b = new_mat(name); lc = attr(nt, 'qa_lc'); p = sep(nt, lc); sd = attr(nt, 'qa_seed', 'fac')
    co = coords(nt, (60, 60, 2))
    fib = noise(nt, co, 1.0, 4, 0.6)
    col = mix(nt, smooth(nt, fib, 0.3, 0.75), (0.25, 0.17, 0.075), (0.36, 0.26, 0.12))
    wob = math_(nt, 'MULTIPLY', math_(nt, 'SINE', math_(nt, 'ADD', math_(nt, 'MULTIPLY', p[2], 21.0), math_(nt, 'MULTIPLY', sd, 40.0))), 0.0025)
    stem = math_(nt, 'SUBTRACT', 1.0, smooth(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', p[0], wob)), 0.0008, 0.0017))
    top = math_(nt, 'ADD', 0.06, math_(nt, 'MULTIPLY', sd, 0.07))
    band = math_(nt, 'MULTIPLY', smooth(nt, p[2], -0.135, -0.115), math_(nt, 'SUBTRACT', 1.0, smooth(nt, p[2], top, math_(nt, 'ADD', top, 0.012))))
    vv = N(nt, 'ShaderNodeCombineXYZ'); L(nt, math_(nt, 'MULTIPLY', p[0], 1.6), vv.inputs[0]); L(nt, math_(nt, 'MULTIPLY', p[2], 0.55), vv.inputs[1])
    L(nt, math_(nt, 'MULTIPLY', sd, 3.0), vv.inputs[2])
    leaf = smooth(nt, voronoi(nt, vv.outputs[0], 80.0, 'F1', rand=0.85), 0.30, 0.17)
    leaf = math_(nt, 'MULTIPLY', leaf, smooth(nt, math_(nt, 'ABSOLUTE', p[0]), 0.0105, 0.006))
    ink = math_(nt, 'MULTIPLY', math_(nt, 'MAXIMUM', stem, math_(nt, 'MULTIPLY', leaf, 0.9)), math_(nt, 'MULTIPLY', band, math_(nt, 'GREATER_THAN', sd, 0.25)))
    col = mix(nt, math_(nt, 'MULTIPLY', ink, 0.85), col, (0.05, 0.045, 0.04))
    cav, edge = edge_cavity(nt, 0.015, 0.003)
    col = mix(nt, math_(nt, 'MULTIPLY', smooth(nt, cav, 0.1, 0.6), 0.6), col, (0.14, 0.09, 0.04))
    return finish(m, nt, b, col, 0.5, 0.0, fib, 0.0005, 0.5)


def m_cord(name='Cord', c1=(0.30, 0.36, 0.26), c2=(0.42, 0.47, 0.34)):
    m, nt, b = new_mat(name); co = coords(nt, (1, 1, 1)); p = sep(nt, co)
    tw = math_(nt, 'SINE', math_(nt, 'MULTIPLY', math_(nt, 'ADD', math_(nt, 'ADD', p[0], p[1]), p[2]), 700.0))
    col = mix(nt, smooth(nt, tw, -0.5, 0.8), c1, c2)
    return finish(m, nt, b, col, 0.85, 0.0, tw, 0.0004, 0.6)
