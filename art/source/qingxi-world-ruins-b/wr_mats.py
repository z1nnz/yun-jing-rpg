"""Procedural material node helpers for qingxi-world-ruins-b (forked unchanged from territory-interior-b ti_mats.py; Cycles, baked for export).

Each material exposes identity nodes OUT_COLOR / OUT_ROUGH / OUT_METAL / OUT_EMIT that the
bake step routes into an Emission shader. MAT_INFO records which exported material slot a
procedural material lands in, and whether its faces keep their own 0-1 UVs.
"""
import bpy, math

MAT_INFO = {}

class G:
    """Tiny node-graph builder."""
    def __init__(self, mat):
        self.t = mat.node_tree; self.n = self.t.nodes; self.l = self.t.links
    def node(self, kind, **props):
        nd = self.n.new(kind)
        for k, v in props.items(): setattr(nd, k, v)
        return nd
    def link(self, a, b): self.l.new(a, b)
    def val(self, v):
        nd = self.node('ShaderNodeValue'); nd.outputs[0].default_value = v; return nd.outputs[0]
    def rgb(self, c):
        nd = self.node('ShaderNodeRGB'); nd.outputs[0].default_value = (*c, 1); return nd.outputs[0]
    def math(self, op, a, b=None, clamp=False):
        nd = self.node('ShaderNodeMath', operation=op, use_clamp=clamp)
        self._in(nd.inputs[0], a)
        if b is not None: self._in(nd.inputs[1], b)
        return nd.outputs[0]
    def vmath(self, op, a, b=None):
        nd = self.node('ShaderNodeVectorMath', operation=op)
        self._in(nd.inputs[0], a)
        if b is not None: self._in(nd.inputs[1], b)
        return nd.outputs['Value'] if op in ('DOT_PRODUCT', 'LENGTH', 'DISTANCE') else nd.outputs['Vector']
    def _in(self, sock, v):
        if isinstance(v, bpy.types.NodeSocket): self.link(v, sock)
        elif isinstance(v, (tuple, list)): sock.default_value = tuple(v) + ((1,) if len(v) == 3 and len(sock.default_value) == 4 else ())
        else: sock.default_value = v
    def mix(self, fac, a, b):
        nd = self.node('ShaderNodeMix', data_type='RGBA', blend_type='MIX', clamp_factor=True)
        self._in(nd.inputs['Factor'], fac)
        self._in(_ident(nd.inputs, 'A_Color'), a); self._in(_ident(nd.inputs, 'B_Color'), b)
        return _ident(nd.outputs, 'Result_Color')
    def mul(self, fac, a, b):
        nd = self.node('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY', clamp_factor=True)
        self._in(nd.inputs['Factor'], fac)
        self._in(_ident(nd.inputs, 'A_Color'), a); self._in(_ident(nd.inputs, 'B_Color'), b)
        return _ident(nd.outputs, 'Result_Color')
    def ramp(self, fac, stops):
        nd = self.node('ShaderNodeValToRGB'); self._in(nd.inputs[0], fac)
        el = nd.color_ramp.elements
        el[0].position, el[0].color = stops[0][0], (*stops[0][1], 1)
        el[1].position, el[1].color = stops[-1][0], (*stops[-1][1], 1)
        for p, c in stops[1:-1]:
            e = el.new(p); e.color = (*c, 1)
        return nd.outputs[0]
    def maprange(self, v, a, b, c=0.0, d=1.0):
        nd = self.node('ShaderNodeMapRange', clamp=True); self._in(nd.inputs[0], v)
        nd.inputs[1].default_value = a; nd.inputs[2].default_value = b
        nd.inputs[3].default_value = c; nd.inputs[4].default_value = d
        return nd.outputs[0]
    def attr(self, name, out='Vector'):
        nd = self.node('ShaderNodeAttribute', attribute_type='GEOMETRY', attribute_name=name); return nd.outputs[out]
    def geo(self, out): return self.node('ShaderNodeNewGeometry').outputs[out]
    def noise(self, vec, scale, detail=4, rough=.55, dims='3D', out='Fac'):
        nd = self.node('ShaderNodeTexNoise', noise_dimensions=dims); self._in(nd.inputs['Vector'], vec)
        nd.inputs['Scale'].default_value = scale; nd.inputs['Detail'].default_value = detail
        nd.inputs['Roughness'].default_value = rough
        return nd.outputs[out]
    def wave(self, vec, scale, distort, kind='RINGS', direction='X', detail=3):
        nd = self.node('ShaderNodeTexWave', wave_type=kind)
        if kind == 'RINGS': nd.rings_direction = direction
        else: nd.bands_direction = direction
        self._in(nd.inputs['Vector'], vec)
        nd.inputs['Scale'].default_value = scale; nd.inputs['Distortion'].default_value = distort
        nd.inputs['Detail'].default_value = detail; nd.inputs['Detail Scale'].default_value = 1.5
        return nd.outputs['Fac']
    def voronoi(self, vec, scale, feature='DISTANCE_TO_EDGE', out='Distance'):
        nd = self.node('ShaderNodeTexVoronoi', feature=feature); self._in(nd.inputs['Vector'], vec)
        nd.inputs['Scale'].default_value = scale; return nd.outputs[out]
    def ao(self, dist=.04):
        nd = self.node('ShaderNodeAmbientOcclusion', only_local=True, samples=12)
        nd.inputs['Distance'].default_value = dist; return nd.outputs['AO']
    def edge(self, radius=.003):
        bev = self.node('ShaderNodeBevel', samples=8); bev.inputs['Radius'].default_value = radius
        d = self.vmath('DOT_PRODUCT', bev.outputs['Normal'], self.geo('Normal'))
        return self.maprange(d, .995, .90)          # 0 on flats, 1 on worn edges
    def bump(self, height, strength, dist=.002, normal=None):
        nd = self.node('ShaderNodeBump'); nd.inputs['Strength'].default_value = strength
        nd.inputs['Distance'].default_value = dist; self._in(nd.inputs['Height'], height)
        if normal is not None: self.link(normal, nd.inputs['Normal'])
        return nd.outputs['Normal']

def _ident(socks, ident):
    for s in socks:
        if s.identifier == ident: return s
    raise KeyError(ident)

def _new(name, slot, own_uv=False):
    m = bpy.data.materials.new(name); m.use_nodes = True
    m.node_tree.nodes.clear()
    MAT_INFO[name] = {'slot': slot, 'own_uv': own_uv}
    return m, G(m)

def _finish(g, color, rough, metal, normal=None, emit=None, sheen=0.0, coat=0.0, spec=.4):
    bs = g.node('ShaderNodeBsdfPrincipled'); out = g.node('ShaderNodeOutputMaterial'); out.name = 'OUTPUT'
    oc = g.node('ShaderNodeGamma', name='OUT_COLOR'); g._in(oc.inputs['Color'], color); oc.inputs['Gamma'].default_value = 1
    orr = g.node('ShaderNodeMath', name='OUT_ROUGH', operation='ADD', use_clamp=True); g._in(orr.inputs[0], rough); orr.inputs[1].default_value = 0
    om = g.node('ShaderNodeMath', name='OUT_METAL', operation='ADD', use_clamp=True); g._in(om.inputs[0], metal); om.inputs[1].default_value = 0
    oe = g.node('ShaderNodeGamma', name='OUT_EMIT'); g._in(oe.inputs['Color'], emit if emit is not None else (0, 0, 0)); oe.inputs['Gamma'].default_value = 1
    es = g.node('ShaderNodeValue', name='EMIT_STRENGTH'); es.outputs[0].default_value = 0.0
    g.link(oc.outputs[0], bs.inputs['Base Color']); g.link(orr.outputs[0], bs.inputs['Roughness'])
    g.link(om.outputs[0], bs.inputs['Metallic']); g.link(oe.outputs[0], bs.inputs['Emission Color'])
    g.link(es.outputs[0], bs.inputs['Emission Strength'])
    bs.inputs['Sheen Weight'].default_value = sheen; bs.inputs['Coat Weight'].default_value = coat
    bs.inputs['Specular IOR Level'].default_value = spec
    if normal is not None: g.link(normal, bs.inputs['Normal'])
    g.link(bs.outputs[0], out.inputs['Surface'])

def _grain_coords(g, stretch=(1, 1, 1)):
    P = g.geo('Position'); r = g.attr('part_rand', 'Fac')
    u = g.vmath('DOT_PRODUCT', P, g.attr('gA')); v = g.vmath('DOT_PRODUCT', P, g.attr('gB')); w = g.vmath('DOT_PRODUCT', P, g.attr('gC'))
    cx = g.node('ShaderNodeCombineXYZ')
    g.link(g.math('MULTIPLY', u, stretch[0]), cx.inputs[0])
    g.link(g.math('ADD', g.math('MULTIPLY', v, stretch[1]), g.math('MULTIPLY', r, 3.7)), cx.inputs[1])
    g.link(g.math('ADD', g.math('MULTIPLY', w, stretch[2]), g.math('MULTIPLY', r, 5.3)), cx.inputs[2])
    return cx.outputs[0], r

def wood(name, dark, light, slot='Main', ring=7.0, rough=.62, wear=.55, grime=.35, edge_tint=None, mid=0.0):
    """Aged hardwood: rings around the grain axis, fibre streaks, cavity dirt, worn bright edges.
    mid > 0 adds grain streaks and weather checks coarse enough to survive a ~130 px/m bake (house atlases)."""
    m, g = _new(name, slot)
    co, r = _grain_coords(g, (1.0, 1.0, 1.0))
    # gentle low-frequency waviness across the grain only, then tight rings around the grain axis
    warp = g.vmath('MULTIPLY', g.vmath('SUBTRACT', g.noise(g.vmath('MULTIPLY', co, (.7, 5, 5)), 1.0, 2, .5, out='Color'), (.5, .5, .5)), (0, .02, .02))
    cw = g.vmath('ADD', co, warp)
    rings = g.wave(cw, ring * 2.6, 1.1, 'RINGS', 'X', 2)
    # long fibre streaks: stretched hard along the grain axis
    fibre = g.noise(g.vmath('MULTIPLY', cw, (.9, 160, 160)), 1.0, 5, .6)
    fine = g.noise(g.vmath('MULTIPLY', cw, (3, 900, 900)), 1.0, 3, .6)
    fibre = g.maprange(fibre, .3, .7); fine = g.maprange(fine, .35, .65)
    pores = g.maprange(fine, .7, .95)
    blot = g.noise(co, 3.0, 3, .5)
    # wide rings on a narrow face fold into flat blocks of one tone: coarse (house) wood keeps them faint
    t = g.math('ADD', g.math('ADD', g.math('MULTIPLY', rings, .35 * (1 - .75 * mid)), g.math('MULTIPLY', fibre, .42)), g.math('MULTIPLY', fine, .23))
    t = g.math('SUBTRACT', t, g.math('MULTIPLY', pores, .3))
    if mid:
        streak = g.maprange(g.noise(g.vmath('MULTIPLY', cw, (.5, 34, 34)), 1.0, 3, .55), .3, .7)
        t = g.math('ADD', g.math('MULTIPLY', t, 1 - .45 * mid), g.math('MULTIPLY', streak, .45 * mid))
        # weather checks: thin dark splits running along the grain
        chk = g.maprange(g.math('ABSOLUTE', g.math('SUBTRACT', g.noise(g.vmath('MULTIPLY', cw, (.25, 24, 24)), 1.0, 2, .5), .5)), .0, .012, 1, 0)
        chk = g.math('MULTIPLY', chk, g.maprange(g.noise(g.vmath('MULTIPLY', co, (2, 4, 4)), 1.0, 2, .5), .52, .62))
        t = g.math('SUBTRACT', t, g.math('MULTIPLY', chk, .5 * mid))
    base = g.ramp(t, [(0.22, tuple(c * .8 for c in dark)), (0.42, dark), (0.58, tuple((a + b) / 2 for a, b in zip(dark, light))), (0.78, light)])
    # per-part tone variation so neighbouring boards don't read as one slab
    tint = g.ramp(r, [(0, (.86, .84, .82)), (1, (1.08, 1.04, 1.0))])
    base = g.mul(1.0, base, tint)
    base = g.mul(grime * .6, base, g.ramp(blot, [(.35, (.55, .5, .45)), (.7, (1, 1, 1))]))
    ao = g.ao(.05)
    base = g.mul(1.0, base, g.ramp(ao, [(0, (.42, .38, .34)), (1, (1, 1, 1))]))
    e = g.edge(.0035)
    et = edge_tint or tuple(min(1, c * 1.55 + .03) for c in light)
    base = g.mix(g.math('MULTIPLY', e, wear), base, et)
    rgh = g.math('SUBTRACT', g.math('ADD', rough, g.math('MULTIPLY', fibre, .12)), g.math('MULTIPLY', e, .22))
    hgt = g.math('ADD', g.math('MULTIPLY', rings, .6), g.math('MULTIPLY', fibre, .4))
    if mid: hgt = g.math('SUBTRACT', g.math('ADD', g.math('MULTIPLY', hgt, 1 - .6 * mid), g.math('MULTIPLY', streak, .5 * mid)), g.math('MULTIPLY', chk, 1.2 * mid))
    nrm = g.bump(hgt, .22 + .2 * mid, .0015)
    _finish(g, base, rgh, 0.0, nrm, spec=.35)
    return m

def metal(name, base, patina, slot='Main', rough=.34, patina_amt=.45, hammered=0.0, patina_scale=18.0, crevice=1.6):
    m, g = _new(name, slot)
    P = g.geo('Position')
    n = g.noise(P, patina_scale, 5, .6); n2 = g.noise(P, 60.0, 3, .5)
    ao = g.ao(.03)
    mask = g.math('ADD', g.math('MULTIPLY', g.math('SUBTRACT', 1.0, ao), crevice), g.math('MULTIPLY', n, patina_amt))
    mask = g.maprange(mask, .55, .85)
    e = g.edge(.0025)
    col = g.mix(mask, base, patina)
    col = g.mix(g.math('MULTIPLY', e, .7), col, tuple(min(1, c * 1.6 + .05) for c in base))
    met = g.math('SUBTRACT', .92, g.math('MULTIPLY', mask, .85))
    rgh = g.math('ADD', g.math('ADD', rough, g.math('MULTIPLY', mask, .4)), g.math('MULTIPLY', n2, .08))
    rgh = g.math('SUBTRACT', rgh, g.math('MULTIPLY', e, .12))
    h = n2
    if hammered:
        h = g.math('ADD', g.math('MULTIPLY', g.voronoi(P, 55.0, 'F1', 'Distance'), hammered), g.math('MULTIPLY', n2, .3))
    _finish(g, col, rgh, met, g.bump(h, .25, .001))
    return m

def cloth(name, base, slot='Main', weave=900.0, rough=.88, sheen=.4, dirt=.25, own_uv=False, coarse=0.0):
    """coarse > 0: an open, hairy weave (burlap) whose threads and gaps read in colour as well as in relief."""
    m, g = _new(name, slot, own_uv)
    P = g.geo('Position')
    w1 = g.wave(P, weave, 1.0, 'BANDS', 'X', 1); w2 = g.wave(P, weave, 1.0, 'BANDS', 'Z', 1)
    if coarse:                                      # a third band set so the weave also shows on up-facing cloth
        w3 = g.wave(P, weave, 1.0, 'BANDS', 'Y', 1)
        w2 = g.math('MULTIPLY', g.math('ADD', w2, w3), .5)
    slub = g.noise(g.vmath('MULTIPLY', P, (2, 2, 40)), 6.0, 4, .6)
    n = g.noise(P, 7.0, 4, .55)
    ao = g.ao(.04)
    col = g.ramp(g.math('ADD', g.math('MULTIPLY', slub, .5), g.math('MULTIPLY', n, .5)),
                 [(.3, tuple(c * .82 for c in base)), (.7, tuple(min(1, c * 1.08) for c in base))])
    col = g.mul(1.0, col, g.ramp(ao, [(0, (.5, .48, .45)), (1, (1, 1, 1))]))
    col = g.mul(dirt, col, g.ramp(g.noise(P, 2.2, 3, .5), [(.4, (.7, .66, .6)), (.7, (1, 1, 1))]))
    h = g.math('ADD', g.math('MULTIPLY', g.math('ADD', w1, w2), .5), g.math('MULTIPLY', slub, .4))
    if coarse:
        wv = g.math('MULTIPLY', g.math('ADD', w1, w2), .5)
        col = g.mul(coarse, col, g.ramp(wv, [(.25, (.55, .5, .44)), (.6, (1, 1, 1)), (.9, (1.12, 1.1, 1.05))]))
    _finish(g, col, g.math('ADD', rough, g.math('MULTIPLY', n, .06)), 0.0, g.bump(h, .12 + .3 * coarse, .0008 + .001 * coarse), sheen=sheen, spec=.25)
    return m

def paper(name, base, slot, emit=(1.0, .58, .26), own_uv=False):
    m, g = _new(name, slot, own_uv)
    P = g.geo('Position')
    fib = g.noise(g.vmath('MULTIPLY', P, (1, 1, 1)), 90.0, 6, .7)
    blot = g.noise(P, 6.0, 3, .5)
    ao = g.ao(.03)
    col = g.ramp(g.math('ADD', g.math('MULTIPLY', fib, .4), g.math('MULTIPLY', blot, .6)),
                 [(.3, tuple(c * .9 for c in base)), (.7, base)])
    col = g.mul(1.0, col, g.ramp(ao, [(0, (.62, .58, .52)), (1, (1, 1, 1))]))
    em = g.mul(1.0, g.rgb(emit), g.ramp(fib, [(.3, (.8, .8, .8)), (.7, (1, 1, 1))]))
    _finish(g, col, .82, 0.0, g.bump(fib, .06, .0006), emit=em, spec=.3)
    return m

def straw(name, light, dark, slot='Main', reed=.0065, block=.026, wear=True):
    """Basket weave: blocks of flat reeds alternating direction, dark gaps, per-reed tone, reeds dip at block edges."""
    m, g = _new(name, slot)
    P = g.geo('Position')
    sep = g.node('ShaderNodeSeparateXYZ'); g.link(P, sep.inputs[0])
    X, Y = sep.outputs['X'], sep.outputs['Y']
    bx = g.math('FLOOR', g.math('DIVIDE', X, block)); by = g.math('FLOOR', g.math('DIVIDE', Y, block))
    par = g.math('MULTIPLY', g.math('FRACT', g.math('MULTIPLY', g.math('ADD', bx, by), .5)), 2.0)   # 0 / 1 checker
    across = g.math('ADD', Y, g.math('MULTIPLY', g.math('SUBTRACT', X, Y), par))
    along = g.math('ADD', X, g.math('MULTIPLY', g.math('SUBTRACT', Y, X), par))
    s = g.math('FRACT', g.math('DIVIDE', across, reed))
    prof = g.math('POWER', g.math('SINE', g.math('MULTIPLY', s, math.pi)), .45)
    rid = g.math('ADD', g.math('ADD', g.math('FLOOR', g.math('DIVIDE', across, reed)), g.math('MULTIPLY', par, 517.0)),
                 g.math('MULTIPLY', g.math('FLOOR', g.math('DIVIDE', along, block)), 37.0))
    wn = g.node('ShaderNodeTexWhiteNoise', noise_dimensions='1D'); g.link(rid, wn.inputs['W']); rv = wn.outputs['Value']
    fa = g.math('FRACT', g.math('DIVIDE', along, block))
    dip = g.maprange(g.math('MINIMUM', fa, g.math('SUBTRACT', 1.0, fa)), 0.0, .16)          # reeds dive under at block edges
    h = g.math('MULTIPLY', prof, g.math('ADD', .45, g.math('MULTIPLY', dip, .55)))
    n = g.noise(P, 4.0, 4, .55); fine = g.noise(g.vmath('MULTIPLY', P, (1, 1, 1)), 260.0, 3, .6)
    t = g.math('ADD', g.math('ADD', g.math('MULTIPLY', h, .55), g.math('MULTIPLY', rv, .3)), g.math('MULTIPLY', n, .25))
    col = g.ramp(t, [(.15, tuple(c * .55 for c in dark)), (.45, dark), (.8, light)])
    col = g.mix(g.math('MULTIPLY', fine, .18), col, tuple(c * .8 for c in dark))
    if wear:
        # elliptical seat wear around the centre: lighter and smoother
        ell = g.vmath('LENGTH', g.vmath('MULTIPLY', P, (1 / .62, 1 / .44, 0)))
        wm = g.math('MULTIPLY', g.maprange(ell, 1.0, .35), g.maprange(n, .35, .6))
        col = g.mix(g.math('MULTIPLY', wm, .55), col, tuple(min(1, c * 1.18) for c in light))
        h = g.math('MULTIPLY', h, g.math('SUBTRACT', 1.0, g.math('MULTIPLY', wm, .5)))
    ao = g.ao(.02)
    col = g.mul(1.0, col, g.ramp(ao, [(0, (.45, .42, .38)), (1, (1, 1, 1))]))
    _finish(g, col, g.math('ADD', .72, g.math('MULTIPLY', fine, .1)), 0.0, g.bump(h, .45, .0012), sheen=.15, spec=.3)
    return m

def glaze(name, base, line, slot='Main', rough=.16, crackle=40.0, mottle=.3):
    m, g = _new(name, slot)
    P = g.geo('Position')
    cr = g.voronoi(P, crackle); crk = g.maprange(cr, .0, .02, 1, 0)
    n = g.noise(P, 9.0, 4, .55); ao = g.ao(.03)
    col = g.ramp(n, [(.3, tuple(c * (1 - mottle * .5) for c in base)), (.7, tuple(min(1, c * (1 + mottle * .3)) for c in base))])
    col = g.mix(g.math('MULTIPLY', crk, .3), col, line)
    col = g.mul(1.0, col, g.ramp(ao, [(0, (.55, .55, .55)), (1, (1, 1, 1))]))
    _finish(g, col, g.math('ADD', rough, g.math('MULTIPLY', n, .08)), 0.0, g.bump(crk, .05, .0004), coat=.4, spec=.5)
    return m

def plain(name, base, slot='Main', rough=.6, metal_v=0.0, noise=.2, emit=None, scale=20.0, own_uv=False, bump=.1):
    m, g = _new(name, slot, own_uv)
    P = g.geo('Position'); n = g.noise(P, scale, 4, .55); ao = g.ao(.03)
    col = g.ramp(n, [(.3, tuple(c * (1 - noise) for c in base)), (.7, tuple(min(1, c * (1 + noise * .5)) for c in base))])
    col = g.mul(1.0, col, g.ramp(ao, [(0, (.5, .5, .5)), (1, (1, 1, 1))]))
    em = g.rgb(emit) if emit else None
    _finish(g, col, g.math('ADD', rough, g.math('MULTIPLY', n, .1)), metal_v, g.bump(n, bump, .001), emit=em)
    return m

def image_mat(name, img, slot, rough=.85, own_uv=True, sheen=.3):
    """Face material reading its own texture (painting, journal page)."""
    m, g = _new(name, slot, own_uv)
    tex = g.node('ShaderNodeTexImage'); tex.image = img; tex.interpolation = 'Cubic'
    ao = g.ao(.03)
    col = g.mul(1.0, tex.outputs['Color'], g.ramp(ao, [(0, (.6, .58, .55)), (1, (1, 1, 1))]))
    P = g.geo('Position'); n = g.noise(P, 300.0, 3, .6)
    _finish(g, col, rough, 0.0, g.bump(n, .05, .0004), sheen=sheen, spec=.25)
    return m

def emissive(name, base, emit, slot):
    """Fire insert: dark ember body, bright glowing cracks."""
    m, g = _new(name, slot)
    P = g.geo('Position')
    cr = g.voronoi(P, 38.0); glow = g.maprange(cr, .0, .06, 1, 0)
    n = g.noise(P, 25.0, 4, .55)
    gm = g.math('ADD', glow, g.math('MULTIPLY', n, .5))
    col = g.mix(gm, base, tuple(c * .4 for c in emit))
    em = g.ramp(gm, [(.2, tuple(c * .25 for c in emit)), (.75, emit), (1, (1.0, .9, .55))])
    _finish(g, col, .85, 0.0, g.bump(n, .2, .001), emit=em)
    return m

def flame(name, slot, inner=(1.0, .86, .45), outer=(1.0, .38, .08)):
    m, g = _new(name, slot)
    P = g.geo('Position'); sep = g.node('ShaderNodeSeparateXYZ'); g.link(P, sep.inputs[0])
    n = g.noise(P, 30.0, 3, .5)
    hgt = g.maprange(sep.outputs['Z'], 0.0, 1.0)   # remapped later by object height via attribute-free gradient
    em = g.ramp(n, [(.25, outer), (.75, inner)])
    _finish(g, em, .9, 0.0, None, emit=em)
    return m

def set_emission(mat, strength):
    nd = mat.node_tree.nodes.get('EMIT_STRENGTH')
    if nd: nd.outputs[0].default_value = strength
