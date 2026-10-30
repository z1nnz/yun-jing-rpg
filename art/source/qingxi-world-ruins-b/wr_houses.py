"""H01-H08: eight abandoned houses from one parametric generator (plan: HOUSES_PLAN.md, design references:
art/references/qingxi-world-ruins-b/house-variants/H0x_*-v001.png).

Every house shares the D3 conventions: Blender Z-up, front faces -Y, origin at the footprint centre (re-centred after
the build), ground z = 0, footing stones embedded 5 cm. A house is a config dict (see HOUSES at the bottom); the
generator builds footing, timber (or bamboo) frame, wall infill of the chosen type, a roof made of slopes (gable
along x or y, hip, lean-to annex, door canopy) carrying one of four coverings (clay tiles, wooden shingles, split
bamboo, thatch), and the damage the config asks for:
  roof holes      per slope, a function hole(x, s) of the position along the slope's ridge axis and down-slope
                  distance; tiles, boards, rafters, fascia, ridge and verge all break around it
  wall collapse   per wall, keep(u) = height the wall still stands to at distance u along it; posts, rails, panels,
                  collision follow, and the lost material lies in rubble piles
  purlin / truss  breaks named explicitly (a snapped purlin hangs or lies on the floor)
Each house is still walk-in: door clear >= 0.9 x 1.9 m and a 2 x 2 m interior area free of geometry and collision.
"""
import math, random, zlib
from types import SimpleNamespace
import bpy, bmesh
from mathutils import Vector, Matrix
import wr_core as C
from wr_core import S, RZ, RX, RY
import wr_materials as WM
from wr_mats import plain
from wr_scene_hut import (V, frame_rot, beam, pole, splinters, shell, merged, pan_template, cover_template, size_key,
                          PAN_L, PAN_DEP, PAN_T, COV_R, COV_L, RAFTER_R, BOARD_T, OFF_BOARD, BOARD_L, _verts_in, _hull_hits)

EMBED = .05
LIMIT = (5.5, 4.5, 3.8)
FOOT_T = .36
FLOOR = .12
THRESH = .14
Z_UP = Vector((0, 0, 1))
K = SimpleNamespace()          # the house being built


# ---------------------------------------------------------------- small helpers
def jag(seed, amp=1.0):
    """Deterministic 1-D wobble for ragged break lines."""
    return lambda t: amp * (.55 * math.sin(7.3 * t + seed) + .3 * math.sin(17.1 * t + 2.3 * seed) + .15 * math.sin(41 * t + 5.1 * seed))


def blob(cx, cs, rx, rs, seed=0.0, rough=.2):
    """Ragged elliptical hole in slope coordinates."""
    def f(x, s):
        a = math.atan2((s - cs) / rs, (x - cx) / rx)
        return ((x - cx) / rx) ** 2 + ((s - cs) / rs) ** 2 < 1 + rough * (math.sin(5 * a + seed) + .6 * math.sin(11 * a + 2 * seed) + .3 * math.sin(23 * a + 3 * seed))
    return f


def runs(pred, lo, hi, step=.04):
    """Contiguous [a, b] intervals of t in [lo, hi] where pred(t) holds."""
    out, start, t = [], None, lo
    n = int(round((hi - lo) / step))
    for i in range(n + 1):
        t = lo + (hi - lo) * i / max(n, 1)
        if pred(t):
            if start is None: start = t
        elif start is not None:
            out.append((start, lo + (hi - lo) * (i - 1) / max(n, 1))); start = None
    if start is not None: out.append((start, hi))
    return out


def drop_about(a, b, piv, axis, deg):
    """Rotate segment a-b about `piv` around `axis` (a vector) by deg, with the sign that brings it lower; the angle is
    reduced until the piece stays above the floor."""
    best = None
    for sign in (1, -1):
        for k in range(7):
            M = Matrix.Translation(piv) @ Matrix.Rotation(sign * math.radians(deg * (1 - k * .13)), 4, Vector(axis)) @ Matrix.Translation(-piv)
            pa, pb = M @ a, M @ b
            if min(pa.z, pb.z) > FLOOR + .06: break
        if best is None or pa.z + pb.z < best[0].z + best[1].z: best = (pa, pb)
    return best


# ---------------------------------------------------------------- configuration
def configure(cfg):
    K.__dict__.clear()
    K.__dict__.update(dict(
        PX=2.37, PY=1.87, FOOT_TOP=.5, SILL=(.5, .64), MID=(1.44, 1.56), PLATE=(2.3, 2.44), TAN=.417,
        front_posts=(0, 1.22, 2.42, 3.57, 4.74), back_posts=(0, 1.57, 3.17, 4.74), side_posts=None,
        door_u=(1.22, 2.42), lintel=None, roof='gable_x', eave_out=.23, gable_out=.32, cover='tile',
        holes={}, sags={}, leaners=[], purlin_breaks=[], truss_broken=(), keep={}, gable_keep={}, gables=('L', 'R'), wall='daub',
        frame='timber', footing='rubble', windows=[], patches=[], rubble=[], annex=None, canopy=None,
        door_leaf=('lean', 'L'), bed='left_back', quiver=(-.8,), room=((-1.3, -1.6), (.7, .4)), seed=1, rafter_gap=.42,
        truss=None, sill=True, debris_extra=[], lashings=[], braces=[], foot_course=.25, foot_lens=(.3, .42, .54),
    ))
    K.__dict__.update(cfg)
    if K.side_posts is None: K.side_posts = (0, K.PY, 2 * K.PY)
    if K.lintel is None: K.lintel = K.PLATE[0] - .13
    if K.wall == 'stone_daub': K.SILL = (K.FOOT_TOP, K.FOOT_TOP + .14)
    K.rows = [(K.SILL[1], K.MID[0]), (K.MID[1], K.PLATE[0])] if K.MID else [(K.SILL[1], K.PLATE[0])]
    if not K.sill: K.rows = [(K.FOOT_TOP, K.PLATE[0])] if not K.MID else [(K.FOOT_TOP, K.MID[0]), (K.MID[1], K.PLATE[0])]
    K.PH = .1 if K.wall == 'earth' else .08               # half the post width
    K.JAMB = (-K.PX + K.door_u[0] + K.PH, -K.PX + K.door_u[1] - K.PH)
    K.HS = K.PX if K.roof == 'gable_y' else K.PY                  # half span measured to the wall line
    K.ANG = math.atan(K.TAN); K.CA, K.SA = math.cos(K.ANG), math.sin(K.ANG)
    K.RZ = K.PLATE[1] + .185 + K.TAN * K.HS
    K.WALLS = {
        'Front': (V(-K.PX, -K.PY, 0), V(1, 0, 0), V(0, -1, 0), tuple(K.front_posts)),
        'Back': (V(-K.PX, K.PY, 0), V(1, 0, 0), V(0, 1, 0), tuple(K.back_posts)),
        'Left': (V(-K.PX, -K.PY, 0), V(0, 1, 0), V(-1, 0, 0), tuple(K.side_posts)),
        'Right': (V(K.PX, -K.PY, 0), V(0, 1, 0), V(1, 0, 0), tuple(K.side_posts)),
    }
    K.rr = random.Random(K.seed)
    K.offset = Vector((0, 0, 0))
    K.debris_pts = []                       # (x, y, kind) spots where fallen material lies


def kh(w, u):
    f = K.keep.get(w)
    return 99.0 if f is None else f(u)


def wall_point(w, u, z, v=0.0):
    o, d, out, _ = K.WALLS[w]
    return o + d * u + out * v + V(0, 0, z)


def wall_len(w):
    return K.WALLS[w][3][-1]


# ---------------------------------------------------------------- materials
def materials():
    P = K.palette; M = {}
    # the roof timbers get the same wood under a second name, so the frame can be split over two atlases
    for k, nm in (('wood', 'Timber'), ('wood_roof', 'RoofTimber')):
        if 'wood_dark' in P: M[k] = WM.wood_tint(f'M_{K.id}_{nm}', P['wood_dark'], P['wood_light'], ring=4.5, mid=1.0)
        else: M[k] = WM.aged_wood(f'M_{K.id}_{nm}', grey=P.get('wood_grey', .4), rough=.8, ring=4.5, mid=1.0)
    M['wood_new'] = WM.aged_wood(f'M_{K.id}_RepairTimber', grey=.12, rough=.74)
    M['plank'] = WM.aged_wood(f'M_{K.id}_Plank', grey=P.get('plank_grey', .7), rough=.82, mid=.8)
    M['poles'] = WM.bark(f'M_{K.id}_RafterPole', slot=P.get('pole_slot', 'Wall'), dark='#3B2617', light='#6E6458', lichen=.15)
    M['board'] = WM.aged_wood(f'M_{K.id}_RoofBoard', slot='Roof', grey=.55, rough=.82, mid=.8)
    cov = K.cover
    if cov == 'tile': M['cover'] = WM.tile(f'M_{K.id}_RoofTile', slot='Roof', tones=P['tile'], moss=P.get('moss', .5), rough=.62)
    elif cov == 'shingle': M['cover'] = WM.shingle(f'M_{K.id}_Shingle', slot='Roof', tones=P['shingle'], grey=P.get('shingle_grey', .35))
    elif cov == 'bamboo': M['cover'] = WM.bamboo(f'M_{K.id}_SplitBamboo', slot='Roof', fresh=.75, grey=.6, straw=P['bamboo'][0], olive=P['bamboo'][1])
    elif cov == 'thatch': M['cover'] = WM.thatch(f'M_{K.id}_Thatch', slot='Roof', light=P['thatch'][0], dark=P['thatch'][1])
    w = K.wall
    if w in ('daub', 'stone_daub'):
        M['infill'] = WM.plaster(f'M_{K.id}_Plaster', slot='Wall', mud=P['mud'], lime=P['lime'], lime_amt=P['lime_amt'],
                                  under=P.get('under'), age_grey=P.get('age_grey', 1.0), cracks=P.get('cracks', .55))
    elif w == 'earth' and 'clay' in P:      # earth wall under a clay skim coat that has flaked off in places
        M['infill'] = WM.plaster(f'M_{K.id}_ClayPlaster', slot='Wall', mud=P['clay'][1], lime=P['clay'][0], lime_amt=P['clay'][2],
                                  age_grey=.15, cracks=.9)
    elif w == 'earth':
        M['infill'] = WM.rammed_earth(f'M_{K.id}_RammedEarth', slot='Wall', earth=P['earth'][0], band=P['earth'][1])
    elif w == 'weave':
        M['infill'] = WM.weave(f'M_{K.id}_WovenMat', slot='Wall', light=P['weave'][0], dark=P['weave'][1])
    elif w == 'plank':
        M['infill'] = WM.wood_tint(f'M_{K.id}_WallBoard', P['wallboard'][0], P['wallboard'][1], slot='Wall', ring=1.1, rough=.8)
    M['gable'] = M['infill'] if w != 'stone_daub' else M['infill']
    M['earth_floor'] = WM.plaster(f'M_{K.id}_EarthFloor', slot=P.get('floor_slot', 'Main'), mud=P.get('floor', '#6E5238'), lime_amt=0.0)
    M['stone'] = WM.stone(f'M_{K.id}_FootingStone', slot='Stone', tones=P['stone'], moss=P.get('stone_moss', .45), lichen=.4, relief=1.8)
    M['wattle'] = WM.aged_wood(f'M_{K.id}_Wattle', slot='Wall', grey=.6, rough=.85)
    fr = P.get('frame', ('#B89A5E', '#8E7C4C'))
    M['bamboo'] = WM.bamboo(f'M_{K.id}_BambooFrame', slot='Main', fresh=.15, grey=.25, straw=fr[0], olive=fr[1]) if K.frame == 'bamboo' else None
    if K.frame == 'bamboo': M['poles'] = M['bamboo']
    M['rope'] = WM.rope(f'M_{K.id}_HempLashing')
    M['iron'] = WM.iron(f'M_{K.id}_Iron')
    M['leather'] = plain(f'M_{K.id}_Leather', WM.hexl('#4A3020'), 'Main', rough=.7, noise=.3, scale=60.0, bump=.2)
    K.M = M
    return M


# ---------------------------------------------------------------- footing (instanced rubble courses)
_PROTO = {}


def _rock_copy(name, key, size, seed, p, yaw, mat):
    """A footing stone from a small library of prototypes: copies share one baked texture (UV instancing)."""
    if key not in _PROTO:
        bm = C.rock_mesh(size, seed, sub=2, round_=.24, chips=9, chip_depth=(.06, .22), wobble=.07, flat_bottom=.8, bulge=.06,
                         taper=random.Random(seed).uniform(-.2, .2), skew=random.Random(seed + 1).uniform(-.12, .12))
        me = bpy.data.meshes.new(f'Proto_{key}'); bm.to_mesh(me); bm.free()
        _PROTO[key] = (me, min(v.co.z for v in me.vertices), len(_PROTO) + 1)
    me, zmin, idx = _PROTO[key]
    o = bpy.data.objects.new(name, me.copy()); bpy.context.scene.collection.objects.link(o)
    o.location = (p[0], p[1], p[2] - zmin); o.rotation_euler = (0, 0, yaw)
    if not o.data.uv_layers: o.data.uv_layers.new(name='UVMap')
    o = C.finish(o, name, mat, grain='x')
    for f in o.data.polygons: f.use_smooth = True
    o.data.set_sharp_from_angle(angle=math.radians(34))
    # the chipped faces are flat already: collapse the subdivision on them (about 190 -> 105 triangles a stone)
    dm = o.modifiers.new('Footing_decimate', 'DECIMATE'); dm.ratio = .55; dm.use_collapse_triangulate = False
    m = o.modifiers.new('Facet_normals', 'WEIGHTED_NORMAL'); m.keep_sharp = True; m.weight = 50
    o['inst_key'] = 1000000 + zlib.crc32(f'{K.id}{key}'.encode()) % 100000
    return o


def footing(stone, rr):
    if K.footing == 'piers':
        return piers(stone, rr)
    H = K.FOOT_TOP + EMBED; nc = max(2, round(H / K.foot_course)); ch = H / nc
    X0, Y0 = K.PX + FOOT_T / 2, K.PY - FOOT_T / 2
    runs_ = [('Front_L', V(-X0, -K.PY, 0), V(1, 0, 0), K.JAMB[0] + X0), ('Front_R', V(K.JAMB[1], -K.PY, 0), V(1, 0, 0), X0 - K.JAMB[1]),
             ('Back', V(-X0, K.PY, 0), V(1, 0, 0), 2 * X0),
             ('Left', V(-K.PX, -Y0, 0), V(0, 1, 0), 2 * Y0), ('Right', V(K.PX, -Y0, 0), V(0, 1, 0), 2 * Y0)]
    lens = K.foot_lens
    k = 0
    for nm, o, d, L in runs_:
        yaw = math.atan2(d.y, d.x)
        for ci in range(nc):
            z0 = -EMBED + ci * ch - (.0 if ci == 0 else .015)
            u = 0.0 if ci % 2 == 0 else -lens[0] / 2
            while u < L - .04:
                rem = L - u
                if rem < lens[-1] + .12 or u < .01:    # a cut stone at either end of the run
                    ln = min(rem, lens[1]) if u >= 0 else lens[1]
                    a, b = max(u, 0), min(u + ln, L)
                    c = o + d * ((a + b) / 2); c.z = z0 + ch / 2
                    s = C.rock(f'Footing_{nm}_{k:03d}', c, ((b - a) * 1.06 + .03, FOOT_T + .03, ch * 1.08), stone, rr.randrange(1 << 30),
                               rot=(0, 0, yaw), sub=2, round_=.24, chips=8, chip_depth=(.06, .2), wobble=.07, flat_bottom=.8, bulge=.06)
                    C.clip_axis(s, 'z', -EMBED, None)
                    lo_, hi_ = o + d * 0, o + d * L
                    ax = 'x' if abs(d.x) > .5 else 'y'
                    C.clip_axis(s, ax, min(getattr(lo_, ax), getattr(hi_, ax)), max(getattr(lo_, ax), getattr(hi_, ax)))
                    s['rand_seed'] = rr.randrange(1 << 30)
                    u = b
                    k += 1; continue
                li = rr.randrange(3); ln = lens[li]; var = rr.randrange(4)
                c = o + d * (u + ln / 2); c.z = z0
                _rock_copy(f'Footing_{nm}_{k:03d}', (ci == 0, li, var), (ln * 1.05, FOOT_T + .03, ch * 1.12), 7000 + li * 31 + var * 7 + (ci == 0) * 3,
                           c, yaw + (math.pi if rr.random() < .5 else 0) + rr.uniform(-.03, .03), stone)
                u += ln * .97; k += 1
    C.rock('Threshold_Stone', ((K.JAMB[0] + K.JAMB[1]) / 2, -K.PY - .02, (THRESH - EMBED) / 2), (K.JAMB[1] - K.JAMB[0] + .1, FOOT_T + .08, THRESH + EMBED),
           stone, 5521 + K.seed, sub=3, round_=.25, chips=3, chip_depth=(.03, .08), wobble=.03, flat_bottom=.9)
    C.clip_axis(S['parts'][-1], 'z', -EMBED, None)


def piers(stone, rr):
    """Squared stone pads under every post, a low rubble kerb between them."""
    seen = set()
    for w, (o, d, out, posts) in K.WALLS.items():
        for u in posts:
            p = wall_point(w, u, 0)
            if w == 'Front' and u in K.door_u: p += d * (.13 if u == K.door_u[1] else -.13)
            key = (round(p.x, 2), round(p.y, 2))
            if key in seen: continue
            seen.add(key)
            s = C.rock(f'Pier_{len(seen):02d}', (p.x, p.y, (K.FOOT_TOP - EMBED) / 2), (.42, .42, K.FOOT_TOP + EMBED + .02), stone, rr.randrange(1 << 30),
                       rot=(0, 0, rr.uniform(-.1, .1)), sub=2, round_=.2, chips=7, chip_depth=(.05, .15), wobble=.04, flat_bottom=.9)
            C.clip_axis(s, 'z', -EMBED, K.FOOT_TOP)
    C.rock('Threshold_Stone', ((K.JAMB[0] + K.JAMB[1]) / 2, -K.PY - .02, (THRESH - EMBED) / 2), (K.JAMB[1] - K.JAMB[0] + .1, FOOT_T + .08, THRESH + EMBED),
           stone, 5521 + K.seed, sub=3, round_=.25, chips=3, chip_depth=(.03, .08), wobble=.03, flat_bottom=.9)
    C.clip_axis(S['parts'][-1], 'z', -EMBED, None)


def floor(earth):
    w, d = (2 * K.PX - .17) / 2, (2 * K.PY - .17) / 2
    for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        o = C.box(f'Floor_Earth_{i}', (sx * w / 2, sy * d / 2, (FLOOR - EMBED) / 2), (w + .002, d + .002, FLOOR + EMBED), earth, bevel=.004,
                  rot=(0, 0, math.pi if sx * sy < 0 else 0), grain='x')
        o['inst_key'] = size_key('floor', earth, w, d)


# ---------------------------------------------------------------- frame and walls
def member(name, a, b, w, h, mat, up=(0, 0, 1), inst=True):
    """A frame member: hewn timber, or a bamboo culm for bamboo-framed houses."""
    if K.frame == 'bamboo':
        return culm(name, a, b, min(w, h) * .45, K.M['bamboo'])
    return beam(name, a, b, w, h, mat, up=up, inst=inst)


def culm(name, a, b, r, mat, gap=.42):
    """Round bamboo culm with a node ring every ~42 cm."""
    a, b = Vector(a), Vector(b); d = b - a
    o = pole(name, a, b, r, mat, verts=12)
    q = Z_UP.rotation_difference(d.normalized()).to_euler()
    n = int(d.length / gap)
    for k in range(1, n + 1):
        t = (k - .5 + .3 * math.sin(k * 2.7 + len(name))) / n
        C.torus(f'{name}_Node_{k}', tuple(a.lerp(b, t)), r * 1.02, r * .11, mat, rot=tuple(q), major=10, minor=3, detail=1)
    return o


def broken_member(name, a, b, w, h, mat, keep_to, up=(0, 0, 1), fall=True):
    """Member from a to b of which only the length up to parameter keep_to (0..1) stands; the snapped rest lies at
    the foot (recorded as debris)."""
    rr = K.rr; a, b = Vector(a), Vector(b)
    if keep_to >= .999: return member(name, a, b, w, h, mat, up)
    if keep_to > .08:
        tip = a.lerp(b, keep_to)
        member(name + '_Stub', a, tip, w, h, mat, up)
        splinters(name + '_Break', tip, b - a, min(w, h) * .5, mat, rr)
    if fall and (1 - keep_to) * (b - a).length > .4:
        K.debris_pts.append(('member', a.lerp(b, keep_to), b, w, h, mat))


def wall_panel(name, w, a, b, z0, z1, mat, kind, seamless=False):
    """Infill between posts u a..b, rows z0..z1, cut down to the wall's keep line. seamless: no bevel and no shared
    texture, for pieces that butt against each other in one bay (round a window) so the joint does not show."""
    rr = K.rr; t = {'daub': .12, 'stone_daub': .12, 'earth': .3, 'weave': .045, 'plank': .03}[kind]
    tops = [(u, min(z1, kh(w, u))) for u in [a + (b - a) * i / max(2, int((b - a) / .05)) for i in range(max(2, int((b - a) / .05)) + 1)]]
    if all(z >= z1 for _, z in tops):
        if kind == 'plank': return plank_bay(name, w, a, b, z0, z1, mat, None)
        o_, d, out, _ = K.WALLS[w]
        c = wall_point(w, (a + b) / 2, (z0 + z1) / 2)
        o = C.box(name, c, (b - a, t, z1 - z0), mat, bevel=0 if seamless else .008, rot=(0, 0, math.atan2(d.y, d.x)), grain='x')
        # woven and boarded panels share a texture by size. Plaster and earth carry wear patterns that would show if
        # they repeated, so only the panel at the same place on the opposite wall shares: that copy's outside face
        # carries the master's inside face, and no viewpoint shows the same face pattern twice
        if not seamless and kind in ('weave', 'plank'): o['inst_key'] = size_key('panel', mat, b - a, t, round(z1 - z0, 2))
        elif not seamless: o['inst_key'] = size_key('panel', mat, b - a, t, round(z1 - z0, 2), round(z0, 2), round(a, 2), w in ('Front', 'Back'))
        return o
    if max(z for _, z in tops) < z0 + .16:          # a sliver on the rail would read as a plank: count it as fallen
        K.debris_pts.append(('lump', wall_point(w, (a + b) / 2, 0), mat, (b - a) * (z1 - z0)))
        return None
    if kind == 'plank': return plank_bay(name, w, a, b, z0, z1, mat, tops)
    j = jag(zlib.crc32(name.encode()) % 100, .06)
    top = [(u, max(z0 + .04, z + (j(u * 4.5) + rr.uniform(-.018, .018) if z < z1 else 0))) for u, z in tops]
    if kind in ('daub', 'stone_daub'):
        # the wattle core stands out of the broken top edge
        for k, u in enumerate([a + (b - a) * (i + .5) / max(2, int((b - a) / .16)) for i in range(max(2, int((b - a) / .16)))]):
            zt = min(z1, kh(w, u))
            if z0 + .1 < zt < z1 - .05:
                zz = max(z0 + .04, zt + j(u * 4.5))
                pole(f'{name}_Stave_{k}', wall_point(w, u, zz - .1), wall_point(w, u + rr.uniform(-.03, .03), min(z1, zz + rr.uniform(.08, .26))), .012, K.M['wattle'], verts=8, detail=1)
    o_, d, out, _ = K.WALLS[w]
    lost = sum((z1 - z) for _, z in tops) / len(tops) * (b - a)
    if lost > .05: K.debris_pts.append(('lump', wall_point(w, (a + b) / 2, 0), mat, lost))
    # only the stretches still standing at least 10 cm keep a piece; a lower remnant would be a loose sliver
    stand = [i for i, (u, z) in enumerate(top) if z > z0 + .1]
    groups, cur = [], []
    for i in stand:
        if cur and i != cur[-1] + 1: groups.append(cur); cur = []
        cur.append(i)
    if cur: groups.append(cur)
    o = None
    for gi, idx in enumerate(groups):
        seg = [top[i] for i in idx]
        if seg[-1][0] - seg[0][0] < .08: continue
        pts = [(seg[0][0], z0), (seg[-1][0], z0)] + [(u, z) for u, z in reversed(seg)]
        nm = name if gi == 0 else f'{name}_{gi}'
        if abs(d.x) > .5: o = C.extrude_profile(nm, [(o_.x + u, z) for u, z in pts], t, mat, plane='xz', p=(0, o_.y, 0), bevel=.008)
        else: o = C.extrude_profile(nm, [(o_.y + u, z) for u, z in pts], t, mat, plane='yz', p=(o_.x, 0, 0), bevel=.008)
    return o


def plank_bay(name, w, a, b, z0, z1, mat, tops):
    """Horizontal wall boards between two posts, slightly overlapping like a lapped board wall."""
    rr = K.rr; z = z0; k = 0
    hs = random.Random(K.seed * 31 + int(z0 * 100))
    while z < z1 - .02:
        hb = hs.choice((.17, .2, .23, .26))
        top = min(z + hb, z1)
        if z1 - top < .09: top = z1
        if tops is None:
            segs = [(a, b)]
        else:
            segs = runs(lambda u: kh(w, u) > top - .02, a, b, .03)
        for j, (u0, u1) in enumerate(segs):
            if u1 - u0 < .12: continue
            full = tops is None or (u0 <= a + .01 and u1 >= b - .01)
            p0 = wall_point(w, u0 - (0 if u0 > a + .01 else .03), (z + top) / 2, .0 + .012 * (k % 2))
            p1 = wall_point(w, u1 + (0 if u1 < b - .01 else .03), (z + top) / 2, .0 + .012 * (k % 2))
            o = beam(f'{name}_B{k:02d}_{j}', p0, p1, top - z + .012, .028, mat, up=tuple(K.WALLS[w][2]), bevel=.005, inst=full)
            if not full: splinters(f'{name}_B{k:02d}_{j}_Brk', p1, p1 - p0, .03, mat, rr, n=2)
        z = top; k += 1
    return None


def walls():
    M = K.M; rr = K.rr; wood = M['wood']
    cw = {}
    for w in ('Front', 'Back', 'Left', 'Right'):
        o, d, out, posts = K.WALLS[w]
        L = posts[-1]
        for i, u in enumerate(posts):
            if w in ('Left', 'Right') and i in (0, len(posts) - 1): continue
            top_k = kh(w, u)
            if w in ('Front', 'Back') and i in (0, len(posts) - 1):
                side = 'Left' if i == 0 else 'Right'
                top_k = min(top_k, kh(side, 0 if w == 'Front' else 2 * K.PY))
            z0 = K.SILL[0] if K.sill else K.FOOT_TOP
            if w == 'Front' and u in K.door_u and K.wall == 'stone_daub': z0 = THRESH + .02
            frac = 1.0 if top_k >= K.PLATE[0] else max(0.0, (top_k + K.rr.uniform(-.15, .2) - z0) / (K.PLATE[0] - z0))
            sz = (.2, .2) if K.wall == 'earth' else (.16, .16)
            broken_member(f'Post_{w}_{i}', wall_point(w, u, z0), wall_point(w, u, K.PLATE[0]), sz[0], sz[1], wood, min(1.0, frac), up=(out.x, out.y, 0))
        ext = .1 if w in ('Front', 'Back') else -.08
        rails = [('Plate', K.PLATE)]
        if K.sill: rails.append(('Sill', K.SILL))
        if K.MID: rails.append(('MidRail', K.MID))
        for nm, (z0, z1) in rails:
            zc = (z0 + z1) / 2
            spans = [(0, L)] if (w != 'Front' or nm == 'Plate') else [(0, K.door_u[0]), (K.door_u[1], L)]
            for j, (a, b) in enumerate(spans):
                a2 = a - (ext if a == 0 else -.08); b2 = b + (ext if b == L else -.08)
                for jj, (ra, rb) in enumerate(runs(lambda u: kh(w, u) > z1 - .02, a2, b2, .03)):
                    if rb - ra < .25: continue
                    # long rails are never UV-instanced: a twin baked beside a leaning door would carry its shadow over
                    member(f'{nm}_{w}_{j}_{jj}', wall_point(w, ra, zc), wall_point(w, rb, zc), .14 if nm != 'Plate' else .16, z1 - z0, wood, inst=False)
                    for end, cut in ((ra, ra > a2 + .01), (rb, rb < b2 - .01)):
                        if cut: splinters(f'{nm}_{w}_{j}_{jj}_Brk{int(end * 100)}', wall_point(w, end, zc), d * (1 if end == rb else -1), .06, wood, rr)
        if w == 'Front':
            member('Door_Lintel', wall_point(w, K.door_u[0] - .08, (K.lintel + K.PLATE[0]) / 2), wall_point(w, K.door_u[1] + .08, (K.lintel + K.PLATE[0]) / 2),
                   .14, K.PLATE[0] - K.lintel, wood)
            for j, z in enumerate((.5, 1.7)):
                C.box(f'Hinge_Pin_{j}', (K.JAMB[0] + .02, -K.PY - .05, z), (.06, .016, .016), M['iron'], bevel=.003, detail=1)
        # infill
        for i in range(len(posts) - 1):
            a, b = posts[i] + .08, posts[i + 1] - .08
            if w in ('Left', 'Right'): a = max(a, .08); b = min(b, posts[-1] - .08)
            if w == 'Front' and (posts[i], posts[i + 1]) == tuple(K.door_u): continue
            for zi, (z0, z1) in enumerate(K.rows):
                key = (w, i, zi)
                win = next((x for x in K.windows if (x['wall'], x['bay'], x['row']) == key), None)
                if win: window(win, a, b, z0, z1)
                else: wall_panel(f'Infill_{w}_{i}_{zi}', w, a, b, z0, z1, M['infill'], K.wall)
                if any((p['wall'], p['bay'], p['row']) == key for p in K.patches): plank_patch(w, a, b, z0, z1)
                if K.wall == 'weave' and kh(w, (a + b) / 2) > z1: weave_battens(f'Batten_{w}_{i}_{zi}', w, a, b, z0, z1)
    gables()


def weave_battens(name, w, a, b, z0, z1):
    """Split-bamboo battens pinning a woven mat to the frame, outside face."""
    for k, z in enumerate((z0 + .05, (z0 + z1) / 2, z1 - .05)):
        pole(f'{name}_{k}', wall_point(w, a - .02, z, .04), wall_point(w, b + .02, z, .04), .014, K.M['bamboo'] or K.M['wattle'], verts=8, detail=1)


def window(win, a, b, z0, z1):
    """Opening in a bay: bars, shutters, or boarded over."""
    M = K.M; w = win['wall']; rr = K.rr
    h0, h1 = win.get('u', (a + .2, b - .2)); v0, v1 = win.get('z', (z0 + .1, z1 - .1))
    t = {'daub': .12, 'stone_daub': .12, 'earth': .3, 'weave': .045, 'plank': .03}[K.wall]
    kind = K.wall
    for nm, (p0, p1, q0, q1) in {'L': (a, h0, z0, z1), 'R': (h1, b, z0, z1), 'B': (h0, h1, z0, v0), 'T': (h0, h1, v1, z1)}.items():
        if win['kind'] == 'torn': break
        if p1 - p0 > .02 and q1 - q0 > .02: wall_panel(f'Infill_{w}_Win{win["bay"]}_{nm}', w, p0, p1, q0, q1, M['infill'], kind, seamless=True)
    up_w = tuple(K.WALLS[w][1])
    if win['kind'] == 'torn': return torn_mat(win, a, b, z0, z1, h0, h1, v0, v1)
    for nm, (p0, p1) in {'Sill': ((h0 - .05, v0), (h1 + .05, v0)), 'Head': ((h0 - .05, v1), (h1 + .05, v1)),
                         'JambA': ((h0, v0), (h0, v1)), 'JambB': ((h1, v0), (h1, v1))}.items():
        member(f'Win_{w}_{win["bay"]}_{nm}', wall_point(w, p0[0], p0[1]), wall_point(w, p1[0], p1[1]), max(t, .12) + .02, .05, M['wood'],
               up=(0, 0, 1) if 'Jamb' not in nm else up_w)
    style = win['kind']
    if style == 'torn':
        return torn_mat(win, a, b, z0, z1, h0, h1, v0, v1)
    if style == 'bars':
        n = max(3, int((h1 - h0) / .1))
        for k in range(n):
            u = h0 + (k + 1) * (h1 - h0) / (n + 1)
            if k in win.get('missing', ()): continue
            top = v1 if k not in win.get('snapped', ()) else v0 + (v1 - v0) * .55
            beam(f'Win_{w}_{win["bay"]}_Bar_{k}', wall_point(w, u, v0), wall_point(w, u, top), .03, .03, M['wood'], up=up_w, bevel=.004)
            if top < v1: splinters(f'Win_{w}_{win["bay"]}_Bar_{k}_Brk', wall_point(w, u, top), (0, 0, 1), .02, M['wood'], rr, n=3)
    elif style == 'shutter':
        # one leaf of vertical boards on two battens, hung on the left jamb and swung a little open
        hinge = wall_point(w, h0 - .02, v0, .09); ang = win.get('open', 12)
        o_, d, out, _ = K.WALLS[w]
        R = Matrix.Rotation(math.radians(ang if d.cross(out).z > 0 else -ang), 4, 'Z')
        n = 4; bw = (h1 - h0 + .06) / n
        for k in range(n):
            u0 = k * bw
            p0 = hinge + (R @ (d * (u0 + bw / 2)).to_4d()).to_3d() + V(0, 0, -.02); p1 = p0 + V(0, 0, v1 - v0 + .04)
            beam(f'Shutter_{w}_{win["bay"]}_{k}', p0, p1, bw - .006, .026, M['plank'], up=tuple((R @ out.to_4d()).to_3d()), bevel=.004)
        for j, zz in enumerate((.12, v1 - v0 - .12)):
            a_ = hinge + (R @ (d * .04).to_4d()).to_3d() + (R @ (out * .022).to_4d()).to_3d() + V(0, 0, zz)
            b_ = hinge + (R @ (d * (h1 - h0)).to_4d()).to_3d() + (R @ (out * .022).to_4d()).to_3d() + V(0, 0, zz)
            beam(f'Shutter_{w}_{win["bay"]}_Batten_{j}', a_, b_, .07, .022, M['plank'], up=(0, 0, 1), bevel=.004)
    elif style == 'boarded':
        for k in range(3):
            zz = v0 + (k + .5) * (v1 - v0) / 3 + rr.uniform(-.03, .03)
            p0 = wall_point(w, h0 - .12 + rr.uniform(-.04, .02), zz + rr.uniform(-.04, .04), .1)
            p1 = wall_point(w, h1 + .12 + rr.uniform(-.02, .04), zz + rr.uniform(-.04, .04), .1)
            beam(f'Boarded_{w}_{win["bay"]}_{k}', p0, p1, .15 + rr.uniform(-.02, .02), .025, M['plank'], up=tuple(K.WALLS[w][2]), bevel=.005)
            for j, p in enumerate((p0.lerp(p1, .06), p0.lerp(p1, .94))):
                C.cyl(f'Boarded_Nail_{w}_{k}_{j}', p + K.WALLS[w][2] * .014, .006, .008, M['iron'],
                      axis='y' if abs(K.WALLS[w][1].x) > .5 else 'x', verts=8, detail=2)


def torn_mat(win, a, b, z0, z1, h0, h1, v0, v1):
    """A woven mat torn open: ragged hole, broken strips across it, the torn flap hanging out askew."""
    M = K.M; w = win['wall']; rr = K.rr; o_, d, out, _ = K.WALLS[w]
    n = 28; cx, cz, rx, rz = (h0 + h1) / 2, (v0 + v1) / 2, (h1 - h0) / 2, (v1 - v0) / 2
    j = jag(7, .12)
    hole = [(cx + rx * (1 + j(t)) * math.cos(t), cz + rz * (1 + j(t + 1)) * math.sin(t)) for t in [math.tau * i / n for i in range(n)]]
    top_i = max(range(n), key=lambda i: hole[i][1]); bot_i = min(range(n), key=lambda i: hole[i][1])
    ccw = lambda i0, i1: [hole[(i0 + k) % n] for k in range(((i1 - i0) % n) + 1)]
    right = ccw(bot_i, top_i)            # bottom -> right side -> top
    left = ccw(top_i, bot_i)             # top -> left side -> bottom
    (xb, zb), (xt, zt) = hole[bot_i], hole[top_i]
    polys = [[(a, z0), (xb, z0)] + list(reversed(left)) + [(xt, z1), (a, z1)],
             [(xb, z0), (b, z0), (b, z1), (xt, z1)] + list(reversed(right))]
    for k, pts in enumerate(polys):
        if abs(d.x) > .5: C.extrude_profile(f'Torn_{w}_{k}', [(o_.x + u, z) for u, z in pts], .045, M['infill'], plane='xz', p=(0, o_.y, 0), bevel=.003)
        else: C.extrude_profile(f'Torn_{w}_{k}', [(o_.y + u, z) for u, z in pts], .045, M['infill'], plane='yz', p=(o_.x, 0, 0), bevel=.003)
    for k in range(4):                          # broken strips still bridging the hole
        z = cz - rz * .6 + k * rz * .4
        u0 = cx - rx * 1.05; L = rx * rr.uniform(.5, 1.1)
        beam(f'Torn_Strip_{w}_{k}', wall_point(w, u0, z), wall_point(w, u0 + L, z + rr.uniform(-.06, .06), rr.uniform(.0, .05)), .03, .006,
             M['infill'], up=tuple(out), bevel=0, detail=1, inst=False)
    # flap: hinged at the top of the hole, swung out and twisted
    hinge = wall_point(w, cx + rx * .2, cz + rz * .85, .03)
    R = Matrix.Rotation(math.radians(-38 if d.cross(out).z > 0 else 38), 4, Vector(d)) @ Matrix.Rotation(math.radians(14), 4, Vector(out))
    fw, fh = rx * 1.3, rz * 1.4
    c = hinge + (R @ (-Z_UP * fh / 2).to_4d()).to_3d()
    rot = (R @ Matrix.Rotation(math.atan2(d.y, d.x), 4, 'Z')).to_euler()
    C.box(f'Torn_Flap_{w}', c, (fw, .02, fh), M['infill'], bevel=.003, rot=rot, grain='x')


def plank_patch(w, a, b, z0, z1):
    rr = K.rr; M = K.M
    z = z0 - .02; k = 0
    while z < z1 - .05:
        wdt = rr.uniform(.16, .21)
        u0, u1 = a - .1 + rr.uniform(-.04, .05), b + .1 - rr.uniform(0, .25)
        tilt = rr.uniform(-.035, .035)
        p0 = wall_point(w, u0, z + wdt / 2, .095 + k * .002); p1 = wall_point(w, u1, z + wdt / 2 + (u1 - u0) * tilt, .095 + k * .002)
        beam(f'Patch_{w}_Plank_{k}', p0, p1, wdt - .01, .026, M['plank'], up=tuple(K.WALLS[w][2]), bevel=.006)
        z += wdt + rr.uniform(-.01, .02); k += 1


def gables():
    """Infill triangles over the plates at the gable ends, under the roof line, cut to their keep line."""
    if K.roof not in ('gable_x', 'gable_y'): return
    zt = K.PLATE[1] + .16
    ridge = K.RZ - RAFTER_R - .17
    for g in K.gables:
        f = K.gable_keep.get(g, lambda u: 99.0)
        pts = []
        n = 24
        for i in range(n + 1):
            u = -K.HS + 2 * K.HS * i / n
            z = min(ridge - (ridge - zt) * abs(u) / K.HS, f(u))
            pts.append((u, max(zt, z)))
        if max(z for _, z in pts) < zt + .1: continue
        mat = K.M['infill']
        if K.wall == 'plank':
            gable_boards(g, zt, ridge, f); continue
        # standing stretches only (the low slivers of a broken gable fall away)
        groups, cur = [], []
        for i, (u, z) in enumerate(pts):
            if z > zt + .08: cur.append(i)
            elif cur: groups.append(cur); cur = []
        if cur: groups.append(cur)
        for gi, idx in enumerate(groups):
            i0, i1 = max(0, idx[0] - 1), min(len(pts) - 1, idx[-1] + 1)
            seg = pts[i0:i1 + 1]
            prof = [(seg[0][0], zt), (seg[-1][0], zt)] + list(reversed(seg))
            nm = f'Gable_{g}' if gi == 0 else f'Gable_{g}_{gi}'
            if K.roof == 'gable_x':
                x = -K.PX if g == 'L' else K.PX
                C.extrude_profile(nm, prof, .1 if K.wall != 'earth' else .26, mat, plane='yz', p=(x, 0, 0), bevel=.01)
            else:
                y = -K.PY if g == 'F' else K.PY
                C.extrude_profile(nm, prof, .1, mat, plane='xz', p=(0, y, 0), bevel=.01)


def gable_boards(g, zt, ridge, keep):
    """Board-walled gable: horizontal boards cut to the roof line."""
    rr = K.rr; mat = K.M['infill']; z = zt; k = 0
    if K.roof == 'gable_x': base, along = V(-K.PX if g == 'L' else K.PX, 0, 0), V(0, 1, 0)
    else: base, along = V(0, -K.PY if g == 'F' else K.PY, 0), V(1, 0, 0)
    while z < ridge - .12:
        top = z + .19
        half = K.HS * (ridge - top) / (ridge - zt)
        for j, (a, b) in enumerate(runs(lambda u: keep(u) > top, -half, half, .04)):
            if b - a < .15: continue
            full = a <= -half + .01 and b >= half - .01
            beam(f'Gable_{g}_Board_{k:02d}_{j}', base + along * a + V(0, 0, (z + top) / 2), base + along * b + V(0, 0, (z + top) / 2), .2, .03, mat,
                 up=tuple(along.cross(Z_UP)), bevel=.005, inst=False)
            if not full: splinters(f'Gable_{g}_Board_{k:02d}_{j}_Brk', base + along * b + V(0, 0, (z + top) / 2), along, .03, mat, rr, n=2)
        z = top - .006; k += 1


# ---------------------------------------------------------------- roof: slopes
class Slope:
    """One roof plane. Parameters: x along the ridge axis `a`, s down-slope distance from the ridge line `o`."""
    def __init__(self, key, o, h, a, tan, s_end, xlim, s_wall, hole=None, ridge=True, sag=None):
        self.key = key; self.o = Vector(o); self.h = Vector(h); self.a = Vector(a); self.tan = tan
        ang = math.atan(tan); self.ca, self.sa = math.cos(ang), math.sin(ang)
        self.d = self.h * self.ca - Z_UP * self.sa; self.n = self.h * self.sa + Z_UP * self.ca; self.X = self.h.cross(Z_UP)
        self.s_end, self.xlim, self.s_wall, self.ridge = s_end, xlim, s_wall, ridge
        self.hole = hole or (lambda x, s: False)
        self.sag = sag

    def at(self, x, s, off=0.0):
        p = self.o + self.a * x + self.d * s + self.n * off
        return p - Z_UP * self.sag(x, s) if self.sag else p

    def R(self, x=None, s=None):
        """Frame of the plane; on a sagging slope, the local frame at (x, s)."""
        if not self.sag or x is None: return Matrix((self.X, self.d, self.n)).transposed()
        e = .05
        dx = (self.at(x + e, s) - self.at(x - e, s)).normalized(); ds = (self.at(x, s + e) - self.at(x, s - e)).normalized()
        if self.X.dot(self.a) < 0: dx = -dx
        nn = dx.cross(ds).normalized()
        if nn.dot(self.n) < 0: nn = -nn
        ds = nn.cross(dx).normalized()
        return Matrix((dx, ds, nn)).transposed()

    def inside(self, x, s, m=0.0):
        lo, hi = self.xlim(s); return lo + m <= x <= hi - m


def slopes():
    hz = K.holes
    E = K.HS + K.eave_out
    out = []
    if K.roof == 'gable_x':
        GX = K.PX + K.gable_out
        for key, h in (('F', (0, -1, 0)), ('B', (0, 1, 0))):
            out.append(Slope(key, (0, 0, K.RZ), h, (1, 0, 0), K.TAN, E / K.CA, (lambda s, GX=GX: (-GX, GX)), K.HS / K.CA, hz.get(key)))
    elif K.roof == 'gable_y':
        GY = K.PY + K.gable_out
        for key, h in (('L', (-1, 0, 0)), ('R', (1, 0, 0))):
            out.append(Slope(key, (0, 0, K.RZ), h, (0, 1, 0), K.TAN, E / K.CA, (lambda s, GY=GY: (-GY, GY)), K.HS / K.CA, hz.get(key)))
    elif K.roof == 'hip':
        RL = K.PX - K.PY
        for key, h in (('F', (0, -1, 0)), ('B', (0, 1, 0))):
            out.append(Slope(key, (0, 0, K.RZ), h, (1, 0, 0), K.TAN, E / K.CA, (lambda s, RL=RL: (-RL - s * K.CA, RL + s * K.CA)), K.HS / K.CA, hz.get(key),
                             sag=K.sags.get(key)))
        for key, h, sx in (('L', (-1, 0, 0), -1), ('R', (1, 0, 0), 1)):
            out.append(Slope(key, (sx * RL, 0, K.RZ), h, (0, 1, 0), K.TAN, E / K.CA, (lambda s: (-s * K.CA, s * K.CA)), K.HS / K.CA, hz.get(key), ridge=False))
    return out


def spole(sl, nm, x, s0, s1, r, mat, verts=10):
    """Pole down the slope at x from s0 to s1; on a sagging slope, in short pieces that follow the dip."""
    n = 1 if not sl.sag else max(1, math.ceil((s1 - s0) / .4))
    for k in range(n):
        pole(nm if k == 0 else f'{nm}_{k}', sl.at(x, s0 + (s1 - s0) * k / n), sl.at(x, s0 + (s1 - s0) * (k + 1) / n), r, mat, verts=verts)


def xpole(sl, nm, p, a, b, r, mat, verts=12):
    """Pole along the slope's ridge axis through points p(x), x in a..b (pieces on a sagging slope)."""
    n = 1 if not sl.sag else max(1, math.ceil((b - a) / .45))
    for k in range(n):
        pole(nm if k == 0 else f'{nm}_{k}', p(a + (b - a) * k / n), p(a + (b - a) * (k + 1) / n), r, mat, verts=verts)


def purlin_z(sl, s, r):
    return sl.at(0, s).z - RAFTER_R - r


def purlins_and_trusses(sls):
    M = K.M; rr = K.rr; poles = M['poles']; wood = M['wood_roof']
    breaks = {(b['slope'], b['level']): b for b in K.purlin_breaks}
    main = sls[0]
    # ridge purlin
    lo, hi = main.xlim(0)
    lines = [('ridge', main, 0.0, .08, lo, hi)]
    for sl in sls:
        for lvl, s in (('mid', sl.s_wall * .5), ('wall', sl.s_wall)):
            a, b = sl.xlim(s)
            lines.append((lvl, sl, s, .07, a, b))
    for lvl, sl, s, r, a, b in lines:
        if b - a < .3: continue
        p = lambda x, sl=sl, s=s, r=r: V(*(sl.at(x, s) - Z_UP * (RAFTER_R + r)))
        br = breaks.get((sl.key, lvl))
        nm = f'Purlin_{sl.key}_{lvl}'
        if not br:
            xpole(sl, nm, p, a, b, r, poles, verts=14 if lvl == 'ridge' else 12); continue
        xb = br['x']; keep_left = br.get('keep', 'left') == 'left'
        k0, k1 = (a, xb) if keep_left else (xb, b)
        xpole(sl, nm, p, k0, k1, r, poles, verts=12)
        tip = p(k1 if keep_left else k0)
        splinters(nm + '_Break', tip, sl.a * (1 if keep_left else -1), r, poles, rr)
        f0, f1 = (xb + .07, b) if keep_left else (a, xb - .07)
        if br.get('fallen', 'hang') == 'hang':
            piv = p(f1 if keep_left else f0)
            ax = sl.a.cross(Z_UP)
            pa, pb = drop_about(p(f0), p(f1), piv, ax, br.get('deg', 26))
            pole(nm + '_Fallen', pa, pb, r, poles, verts=12)
        elif br.get('fallen') == 'floor':
            K.debris_pts.append(('pole', p(f0), p(f1), r, poles))
    # trusses across the span at positions along the main ridge axis
    pos = K.truss if K.truss is not None else ((-K.PX, -.75, .75, K.PX) if K.roof == 'gable_x' else
                                             (-K.PY, 0, K.PY) if K.roof == 'gable_y' else (-(K.PX - K.PY), (K.PX - K.PY)))
    across = main.h * -1          # from the front wall to the back
    zmid = purlin_z(main, main.s_wall * .5, .07) - .07
    for i, t in enumerate(pos):
        base = main.a * t
        if i in K.truss_broken:
            a_ = base - across * (K.HS + .12) + V(0, 0, K.PLATE[1] + .08)
            beam(f'Truss_{i}_Tie_Stub', a_, a_ + across * .9, .14, .16, wood)
            splinters(f'Truss_{i}_Tie_Break', a_ + across * .9, across, .08, wood, rr)
            K.debris_pts.append(('member', base + V(0, 0, K.PLATE[1] + .16), base + V(0, 0, K.RZ - RAFTER_R - .16), .12, .12, wood))
            continue
        member(f'Truss_{i}_Tie', base - across * (K.HS + .12) + V(0, 0, K.PLATE[1] + .08), base + across * (K.HS + .12) + V(0, 0, K.PLATE[1] + .08), .14, .16, wood)
        member(f'Truss_{i}_King', base + V(0, 0, K.PLATE[1] + .16), base + V(0, 0, K.RZ - RAFTER_R - .16), .12, .12, wood, up=tuple(main.a))
        for sg in (-1, 1):
            q = base + across * sg * main.s_wall * .5 * main.ca
            member(f'Truss_{i}_Post_{sg}', q + V(0, 0, K.PLATE[1] + .16), q + V(0, 0, zmid), .1, .1, wood, up=tuple(main.a))


def rafter_positions(sl):
    lo, hi = sl.xlim(sl.s_end)
    if K.roof == 'hip':
        n = int((hi - lo) / K.rafter_gap); xs = [lo + (hi - lo) * (i + .5) / n for i in range(n)]
        if sl.key in ('L', 'R'): return [(x, abs(x) / sl.ca) for x in xs]
        RL = K.PX - K.PY
        return [(x, max(0.0, (abs(x) - RL) / sl.ca)) for x in xs]
    lo, hi = lo + .15, hi - .15
    n = int(round((hi - lo) / K.rafter_gap))
    return [(lo + (hi - lo) * i / n, 0.0) for i in range(n + 1)]


def rafters(sl, bare):
    rr = K.rr; poles = K.M['poles']
    for i, (x, s0) in enumerate(rafter_positions(sl)):
        if s0 > sl.s_end - .3: continue
        nm = f'Rafter_{sl.key}_{i:02d}'
        sa0 = s0 - (.06 if s0 == 0 else 0)
        L1 = sl.s_end + .06
        ints = runs(lambda s: sl.hole(x, s), s0, sl.s_end, .05)
        o0 = sl.at(x, 0)
        if not ints:
            spole(sl, nm, x, sa0, L1, RAFTER_R, poles); continue
        state = rr.random()
        if state < .28:
            spole(sl, nm, x, sa0, L1, RAFTER_R, poles); bare.append((x, ints[0])); continue
        if state > .88: K.debris_pts.append(('pole', sl.at(x, sa0), sl.at(x, L1), RAFTER_R, poles)); continue
        a, b = ints[0][0], ints[-1][1]
        if a > s0 + .05: sa = min(a + rr.uniform(.1, .4), b - .1)
        else: sa = s0 + rr.uniform(.4, 1.1) if rr.random() < .7 else s0
        sa = min(sa, sl.s_end - .2)
        if sa > s0 + .1:
            spole(sl, nm + '_Stub', x, sa0, sa, RAFTER_R, poles)
            splinters(nm + '_StubBreak', sl.at(x, sa), sl.d, RAFTER_R, poles, rr)
        s_plate = sl.s_wall + .06
        if b < sl.s_end - .05:                               # lower length still on the wall plate
            sb = max(b - rr.uniform(.1, .35), sa + .15)
            spole(sl, nm + '_Low', x, sb, L1, RAFTER_R, poles)
            splinters(nm + '_LowBreak', sl.at(x, sb), -sl.d, RAFTER_R, poles, rr)
            f0, f1 = sa + .08, sb - .08
            if f1 - f0 > .35:
                pa, pb = drop_about(sl.at(x, f0), sl.at(x, f1), sl.at(x, f1), sl.X, rr.uniform(40, 65))
                pole(nm + '_Fallen', pa, pb, RAFTER_R, poles, verts=10)
        elif sa + .1 < s_plate:                              # the hole runs out over the eave: lower length tipped in
            pa, pb = drop_about(sl.at(x, sa + .1), sl.at(x, L1), sl.at(x, s_plate), sl.X, rr.uniform(26, 44))
            pole(nm + '_Fallen', pa, pb, RAFTER_R, poles, verts=10)
            splinters(nm + '_FallenBreak', pa, pa - pb, RAFTER_R, poles, rr)


def boards(sl):
    rr = K.rr; mat = K.M['board']
    lo_ref = sl.xlim(sl.s_end)[0]
    k = 0; s = 0.0
    while s < sl.s_end - .01:
        w = min(.2, sl.s_end - s); sm = s + w / 2
        lo, hi = sl.xlim(sm)
        if K.roof == 'hip': lo, hi = lo + .03, hi - .03
        for j, (a, b) in enumerate(runs(lambda x: not sl.hole(x, sm), lo, hi, .04)):
            a2 = a if a <= lo + .01 else max(lo, a - rr.uniform(.04, .3))
            b2 = b if b >= hi - .01 else min(hi, b + rr.uniform(.04, .3))
            if b2 - a2 < .2: continue
            j0 = lo_ref + (BOARD_L / 2 if k % 2 else 0)
            cuts = [a2] + [j0 + i * BOARD_L for i in range(-1, 12) if a2 + .05 < j0 + i * BOARD_L < b2 - .05] + [b2]
            if sl.sag:                                   # short lengths where the slope has sunk
                cuts = sorted(set(cuts + [c for c in [a2 + .3 * i for i in range(1, 40)] if c < b2 - .05 and sl.sag(c, sm) > .01]))
            for q, (c0, c1) in enumerate(zip(cuts, cuts[1:])):
                if c1 - c0 < .06: continue
                beam(f'Board_{sl.key}_{k:02d}_{j}_{q}', sl.at(c0 + .002, sm, RAFTER_R + BOARD_T / 2), sl.at(c1 - .002, sm, RAFTER_R + BOARD_T / 2),
                     w - .006, BOARD_T, mat, up=tuple(sl.n), bevel=.003, seg=1, inst=abs((c1 - c0) - BOARD_L) < .01)   # one-step bevel: seen only from below
        k += 1; s += w


def fascia_and_verge(sl):
    wood = K.M['wood_roof']; rr = K.rr
    lo, hi = sl.xlim(sl.s_end)
    for j, (a, b) in enumerate(runs(lambda x: not sl.hole(x, sl.s_end - .05), lo, hi, .04)):
        if b - a > .3: beam(f'Fascia_{sl.key}_{j}', sl.at(a, sl.s_end, RAFTER_R), sl.at(b, sl.s_end, RAFTER_R), .03, .1, wood, up=tuple(sl.n))
    if K.roof in ('gable_x', 'gable_y') or getattr(sl, 'verge', False):
        for end, xg in (('L', lo - .02), ('R', hi + .02)):
            if K.cover == 'thatch': continue
            for j, (a, b) in enumerate(runs(lambda s: not sl.hole(xg * .97 if abs(xg) > 1 else xg, s), 0, sl.s_end, .05)):
                if b - a < .3: continue
                beam(f'Barge_{sl.key}_{end}_{j}', sl.at(xg, max(a, .02), OFF_BOARD + .05), sl.at(xg, b + .03, OFF_BOARD + .05), .035, .17, wood, up=tuple(sl.n))


# ---------------------------------------------------------------- coverings
def cover_tiles(sl, bare, kind):
    rr = K.rr; mat = K.M['cover']
    pans, covers, caps, loose, pan_u, cov_u = [], [], [], [], [], []
    lo, hi = sl.xlim(sl.s_end)
    n = int((hi - lo - .12) / .26); x0 = (lo + hi) / 2 - n * .26 / 2
    xs = [x0 + i * .26 for i in range(n + 1)]
    m = -.02 if K.roof == 'hip' else -1
    near = lambda x, s, r=.42: any(sl.hole(x + dx, s + ds) for dx in (-r, 0, r) for ds in (-r * .6, 0, r * .6))
    for ci, x in enumerate(xs):
        kk = 0; sc = sl.s_end + .05 - PAN_L / 2
        while sc - PAN_L / 2 > .1:
            jit = rr.uniform(-.06, .06)
            if sl.inside(x, sc, m + .1) and not sl.hole(x + jit, sc) and rr.random() > .012:
                o = sl.at(x + rr.uniform(-.006, .006), sc, OFF_BOARD + PAN_DEP + PAN_T + .002 + kk * .0004)
                Mx = Matrix.Translation(o) @ sl.R().to_4x4() @ Matrix.Rotation(math.radians(2.6 + rr.uniform(-.8, .8)), 4, 'X') @ Matrix.Rotation(rr.uniform(-.03, .03), 4, 'Z')
                pans.append((Mx, rr.random()))
                pan_u.append(kk == 0 or ci in (0, n) or near(x, sc) or not sl.inside(x, sc, m + .2))
            kk += 1; sc -= .165
    for ci, x in enumerate(xs[:-1]):
        xc = x + .13; kk = 0; sc = sl.s_end + .04 - COV_L / 2
        while sc - COV_L / 2 > .12:
            jit = rr.uniform(-.05, .05)
            if sl.inside(xc, sc, m + .12) and not near(xc + jit, sc, .08):
                slip = .06 if kk > 0 and rr.random() < .03 else 0.0
                o = sl.at(xc + rr.uniform(-.005, .005), sc + slip, OFF_BOARD + PAN_T + .004)
                Mx = Matrix.Translation(o) @ sl.R().to_4x4() @ Matrix.Rotation(math.radians(1.6), 4, 'X') @ Matrix.Rotation(rr.uniform(-.025, .025), 4, 'Z')
                covers.append((Mx, rr.random()))
                cov_u.append(kk == 0 or ci in (0, n - 1) or near(xc, sc) or slip > 0 or not sl.inside(xc, sc, m + .2))
                if kk == 0: caps.append(o + sl.d * (COV_L / 2) + sl.n * .02)
            kk += 1; sc -= .2
    merged(f'Tiles_Pan_{sl.key}', pan_template(), pans, mat, kind=kind, variants=16, unique=pan_u)
    merged(f'Tiles_Cover_{sl.key}', cover_template(), covers, mat, kind=kind + 1, variants=12, unique=cov_u)
    for j, c in enumerate(caps):
        pole(f'Tile_EaveDisc_{sl.key}_{j:02d}', c - sl.d * .008, c + sl.d * .012, COV_R + .004, mat, verts=14, detail=1)
    for j, (x0_, (a, b)) in enumerate(bare[:2]):
        o = sl.at(x0_, rr.uniform(a, b), RAFTER_R * 2 + PAN_DEP + PAN_T)
        loose.append((Matrix.Translation(o) @ sl.R().to_4x4() @ Matrix.Rotation(rr.uniform(-.25, .25), 4, 'Z') @ Matrix.Rotation(rr.uniform(-.15, .15), 4, 'Y'), rr.random()))
    merged(f'Tiles_Loose_{sl.key}', pan_template(), loose, mat, detail=1)


SH_W, SH_L, SH_T, SH_STEP = .15, .44, .016, .14


def shingle_template():
    xs = [-SH_W / 2, -SH_W / 4, 0, SH_W / 4, SH_W / 2]
    top = [(x, .003 * (1 - (2 * x / SH_W) ** 2)) for x in xs]
    bot = [(x, z - SH_T) for x, z in top]
    return shell(top, bot, SH_L)


def cover_shingles(sl, bare, kind):
    """Split wooden shingles, three deep: rows every 14 cm, joints offset by half a shingle row to row."""
    rr = K.rr; mat = K.M['cover']; items, uniq = [], []
    near = lambda x, s, r=.3: any(sl.hole(x + dx, s + ds) for dx in (-r, 0, r) for ds in (-r * .6, 0, r * .6))
    sc = sl.s_end + .04 - SH_L / 2; row = 0
    lo_e, hi_e = sl.xlim(sl.s_end)
    while sc - SH_L / 2 > -.02:
        lo, hi = sl.xlim(max(sc, 0))
        x = lo_e - .04 + (SH_W / 2 if row % 2 else 0) + rr.uniform(0, .03)
        while x < hi_e + .04:
            w_ = SH_W
            if sl.inside(x, sc, -.04 if K.roof == 'hip' else -.06) and not sl.hole(x + rr.uniform(-.04, .04), sc) and rr.random() > .01:
                o = sl.at(x, sc, OFF_BOARD + SH_T + .003 + (row % 3) * .006)
                Mx = Matrix.Translation(o) @ sl.R(x, sc).to_4x4() @ Matrix.Rotation(math.radians(3.5 + rr.uniform(-1, 1)), 4, 'X') @ Matrix.Rotation(rr.uniform(-.03, .03), 4, 'Z')
                items.append((Mx, rr.random()))
                uniq.append(row == 0 or near(x, sc) or not sl.inside(x, sc, .12))
            x += w_ + rr.uniform(.004, .012)
        sc -= SH_STEP; row += 1
    merged(f'Shingles_{sl.key}', shingle_template(), items, mat, kind=kind, variants=14, unique=uniq, grain=tuple(sl.d))
    loose = []
    for j, (x0_, (a, b)) in enumerate(bare[:3]):
        o = sl.at(x0_, rr.uniform(a, b), RAFTER_R * 2 + SH_T)
        loose.append((Matrix.Translation(o) @ sl.R().to_4x4() @ Matrix.Rotation(rr.uniform(-.6, .6), 4, 'Z'), rr.random()))
    merged(f'Shingles_Loose_{sl.key}', shingle_template(), loose, mat, detail=1)


BB_R, BB_T, BB_L = .052, .009, 1.3


def half_culm(L, up=True, r=BB_R, node=.45):
    """Half a bamboo culm, length along y, with a raised node ring every `node` metres (the split culm keeps its
    nodes: a low bulge outside, the diaphragm stub inside)."""
    th = [math.pi * i / 6 for i in range(7)]; n = len(th)
    sg = 1 if up else -1
    st = [(-L / 2, 1.0)]
    y = -L / 2 + (node or 0) * .55
    while node and y < L / 2 - .06:
        st += [(y - .016, 1.0), (y, 1.075), (y + .016, 1.0)]; y += node
    st.append((L / 2, 1.0))
    verts = []
    for y, k in st:
        ri = (r - BB_T) * (2 - k)                      # inside the node closes in a little
        verts += [(r * k * math.cos(t), y, sg * r * k * math.sin(t)) for t in th]
        verts += [(ri * math.cos(t), y, sg * ri * math.sin(t)) for t in th]
    f = []
    for s in range(len(st) - 1):
        T0, B0, T1, B1 = 2 * n * s, 2 * n * s + n, 2 * n * (s + 1), 2 * n * (s + 1) + n
        for i in range(n - 1):
            f.append((T0 + i, T0 + i + 1, T1 + i + 1, T1 + i))
            f.append((B0 + i, B1 + i, B1 + i + 1, B0 + i + 1))
        f.append((T0, T1, B1, B0)); f.append((T0 + n - 1, B0 + n - 1, B1 + n - 1, T1 + n - 1))
    T0, B0 = 0, n; T1, B1 = 2 * n * (len(st) - 1), 2 * n * (len(st) - 1) + n
    for i in range(n - 1):
        f.append((T0 + i, B0 + i, B0 + i + 1, T0 + i + 1))
        f.append((T1 + i, T1 + i + 1, B1 + i + 1, B1 + i))
    return verts, f


def cover_bamboo(sl, bare, kind):
    """Split-bamboo roof: half culms laid as channels (concave up) side by side, capped by half culms (convex up)
    over the joints; two lengths per run, the upper one overlapping the lower by 10 cm."""
    rr = K.rr; mat = K.M['cover']
    lo, hi = sl.xlim(sl.s_end); pitch = 2 * BB_R * .98
    n = int((hi - lo) / pitch)
    segs = [(sl.s_end + .05 - BB_L, sl.s_end + .05), (-.02, sl.s_end + .05 - BB_L + .1)]
    full, fu, broken = [], [], []
    for layer, up in (('Ch', False), ('Cap', True)):
        for ci in range(n + (0 if up else 1)):
            x = lo + ci * pitch + (pitch / 2 if up else 0) + (.0 if up else BB_R * .2)
            for si, (s0, s1) in enumerate(segs):
                Lseg = s1 - s0
                ok = runs(lambda s: not sl.hole(x, s), max(s0, 0), min(s1, sl.s_end + .05), .04)
                off = OFF_BOARD + (BB_R + .004 if not up else BB_R * .9 + BB_T)
                if len(ok) == 1 and ok[0][1] - ok[0][0] > Lseg - .06:
                    sm = (s0 + s1) / 2
                    o = sl.at(x, sm, off - (.0 if not up else 0) + si * .008)
                    Mx = Matrix.Translation(o) @ sl.R().to_4x4() @ Matrix.Rotation(rr.uniform(-.008, .008), 4, 'Z')
                    full.append((layer, Mx, rr.random(), ci in (0, n)))
                    continue
                for a, b in ok:
                    if b - a < .15: continue
                    a2 = a + (rr.uniform(.0, .12) if a > s0 + .01 else 0); b2 = b - (rr.uniform(0, .12) if b < s1 - .01 else 0)
                    band = max(1, int((b2 - a2) / .1))              # snapped to 10 cm so equal lengths share a texture
                    if a2 > s0 + .01: a2 = b2 - band * .1
                    else: b2 = a2 + band * .1
                    o = sl.at(x, (a2 + b2) / 2, off + si * .008)
                    Mx = Matrix.Translation(o) @ sl.R().to_4x4() @ Matrix.Rotation(rr.uniform(-.02, .02), 4, 'Z')
                    broken.append((layer, band, Mx, rr.random()))
    for layer, up in (('Ch', False), ('Cap', True)):
        items = [(Mx, r) for l, Mx, r, u in full if l == layer]
        uniq = [u for l, Mx, r, u in full if l == layer]
        tpl = half_culm(BB_L, up, node=.45 if up else None)
        merged(f'Bamboo_{layer}_{sl.key}', tpl, items, mat, kind=kind + (0 if up else 1), variants=10, unique=uniq, grain=tuple(sl.d))
        for band in sorted({bd for l, bd, Mx, r in broken if l == layer}):
            its = [(Mx, r) for l, bd, Mx, r in broken if l == layer and bd == band]
            merged(f'Bamboo_{layer}_Broken_{sl.key}_{band:02d}', half_culm(band * .1, up, node=.45 if up else None), its, mat,
                   kind=2000 + kind * 40 + (20 if up else 0) + band, variants=2, grain=tuple(sl.d))


def cover_thatch(sl, bare, kind):
    """Thick straw thatch as one solid sheet over the boards: stepped courses (each course thicker at its butt),
    a thick cut eave and verge, thinned and torn round any hole."""
    rr = K.rr; mat = K.M['cover']
    lo, hi = sl.xlim(sl.s_end)
    lo, hi = lo - .05, hi + .05
    s_lo, s_hi = -.05, sl.s_end + .1
    nx, ns = int((hi - lo) / .09), int((s_hi - s_lo) / .07)
    X = [lo + (hi - lo) * i / nx for i in range(nx + 1)]
    Sv = [s_lo + (s_hi - s_lo) * j / ns for j in range(ns + 1)]
    cell = {}
    for i in range(nx):
        for j in range(ns):
            xc, sc = (X[i] + X[i + 1]) / 2, (Sv[j] + Sv[j + 1]) / 2
            cell[i, j] = not sl.hole(xc, sc)
    def edge_dist(i, j, r=3):
        for k in range(1, r + 1):
            for di in range(-k, k + 1):
                for dj in (-k, k):
                    if not cell.get((i + di, j + dj), True): return k
            for dj in range(-k, k + 1):
                for di in (-k, k):
                    if not cell.get((i + di, j + dj), True): return k
        return r + 1
    T0 = .2
    def thick(i, j):
        s = Sv[j]; course = ((s_hi - s) / .38) % 1.0
        t = T0 + .07 * course + .02 * math.sin(X[i] * 9 + s * 4) + .012 * math.sin(X[i] * 31 + s * 17)
        if s > sl.s_end - .05: t *= .85
        de = min([edge_dist(ii, jj) for ii in (i - 1, i) for jj in (j - 1, j) if (ii, jj) in cell] or [9])
        if de <= 3: t *= .45 + .18 * de
        return t
    verts, faces, idx = [], [], {}
    def vid(i, j, top):
        k = (i, j, top)
        if k not in idx:
            x, s = X[i], Sv[j]
            ins = [(ii, jj) for ii in (i - 1, i) for jj in (j - 1, j) if (ii, jj) in cell]
            if any(not cell[c] for c in ins):
                jr = random.Random(K.seed * 100003 + i * 7919 + j * 104729 + kind)
                x += jr.uniform(-.035, .035); s += jr.uniform(-.03, .03)
            off = OFF_BOARD + (thick(i, j) if top else .0)
            p = sl.at(x, s, off)
            if Sv[j] > sl.s_end - .3:                              # the last courses bend down over the eave
                p -= sl.n * ((Sv[j] - sl.s_end + .3) * .45)
            if j == ns:                                            # eave butts: ragged length, cut back and down
                jr = random.Random(K.seed * 7 + i * 131 + kind)
                p += sl.d * (jr.uniform(-.05, .06) + .03 * math.sin(i * .9)) - sl.n * ((.06 + jr.uniform(0, .05)) if top else 0)
            idx[k] = len(verts); verts.append(tuple(p))
        return idx[k]
    buf = {}
    nch = max(1, round((hi - lo) / 1.3)); per = -(-nx // nch)
    for ch in range(nch):
        verts, faces, idx = [], [], {}
        for (i, j), on in cell.items():
            if not on or i // per != ch: continue
            faces.append((vid(i, j, 1), vid(i + 1, j, 1), vid(i + 1, j + 1, 1), vid(i, j + 1, 1)))
            if j >= ns - 2 or i <= 1 or i >= nx - 2 or edge_dist(i, j, 1) <= 1:      # underside only where it can be seen
                faces.append((vid(i, j, 0), vid(i, j + 1, 0), vid(i + 1, j + 1, 0), vid(i + 1, j, 0)))
            for (di, dj), (a, b) in (((0, -1), ((i, j), (i + 1, j))), ((1, 0), ((i + 1, j), (i + 1, j + 1))),
                                     ((0, 1), ((i + 1, j + 1), (i, j + 1))), ((-1, 0), ((i, j + 1), (i, j)))):
                if not cell.get((i + di, j + dj), False):
                    faces.append((vid(*a, 1), vid(*a, 0), vid(*b, 0), vid(*b, 1)))
        if not faces: continue
        o = C.mesh(f'Thatch_{sl.key}_{ch}', verts, faces, mat, smooth=True, grain=tuple(sl.d))
        bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
        for p in o.data.polygons: p.use_smooth = True
    # hazel sways: rods pegged across the thatch near the eave and the ridge
    for k, s in enumerate((sl.s_end - .55, .55)):
        ok = runs(lambda x: not sl.hole(x, s), lo + .2, hi - .2, .05)
        for j, (a, b) in enumerate(ok):
            if b - a > .5: pole(f'Thatch_Sway_{sl.key}_{k}_{j}', sl.at(a, s, OFF_BOARD + T0 + .07), sl.at(b, s, OFF_BOARD + T0 + .07), .014, K.M['wattle'], verts=8, detail=1)


COVERS = {'tile': cover_tiles, 'shingle': cover_shingles, 'bamboo': cover_bamboo, 'thatch': cover_thatch}


# ---------------------------------------------------------------- ridges
def ridge_line(sls):
    """Main ridge, split where either slope is holed at the top."""
    rr = K.rr; mat = K.M['cover']; main = sls[0]
    lo, hi = main.xlim(0)
    lo2, hi2 = (lo + .1, hi - .1) if K.roof != 'hip' else (lo, hi)
    tops = [sl for sl in sls if sl.ridge]
    for j, (a, b) in enumerate(runs(lambda x: not any(sl.hole(x, .12) for sl in tops), lo2, hi2, .04)):
        if b - a < .35: continue
        A, B = main.o + main.a * a, main.o + main.a * b
        if K.cover == 'tile':
            # a lime-mortar core with three courses of flat tiles laid on edge-to-edge, stepping in as they rise,
            # capped by a row of cover tiles: the layered ridge of the reference rather than one smooth block
            beam(f'Ridge_Body_{j}', A + V(0, 0, .07), B + V(0, 0, .07), .2, .13, K.M['infill'], bevel=.015, inst=False)
            yaw = math.atan2(main.a.y, main.a.x)
            for k in range(3):
                zc = .145 + k * .04; wd = .32 - k * .035; x = a + .02 + (k % 2) * .12; n = 0
                while x < b - .05:
                    ln = min(rr.uniform(.22, .27), b - x)
                    if ln < .08: break
                    c = main.o + main.a * (x + ln / 2) + main.h * rr.uniform(-.008, .008) + V(0, 0, zc + rr.uniform(-.004, .004))
                    if rr.random() > .04 or k == 2:          # now and then a course tile has dropped out
                        C.box(f'Ridge_Course_{j}_{k}_{n:02d}', tuple(c), (ln - .012, wd + rr.uniform(-.01, .01), .034), mat, bevel=.004,
                              rot=(rr.uniform(-.02, .02), rr.uniform(-.02, .02), yaw + rr.uniform(-.015, .015)), detail=1, seg=1)
                    x += ln; n += 1
            items = []; x = a + .06
            while x < b - .1:
                c = main.o + main.a * (x + COV_L / 2) + V(0, 0, .24)
                Mx = Matrix.Translation(c) @ Matrix((tuple(-main.h), tuple(main.a), (0, 0, 1))).transposed().to_4x4() @ Matrix.Rotation(rr.uniform(-.02, .02), 4, 'Z')
                items.append((Mx, rr.random())); x += COV_L - .03
            merged(f'Ridge_Covers_{j}', cover_template(), items, mat)
            for end, xe, sx in (('L', a, -1), ('R', b, 1)):
                E = main.o + main.a * xe
                if K.roof != 'hip' and abs(xe) > main.xlim(0)[1] - .2:
                    pts = [E - main.a * sx * .16 + V(0, 0, .26), E - main.a * sx * .04 + V(0, 0, .28), E + main.a * sx * .03 + V(0, 0, .315), E + main.a * sx * .06 + V(0, 0, .35)]
                    C.tube(f'Ridge_End_Curl_{j}_{end}', [tuple(p) for p in pts], .055, mat, radii=[1, .95, .85, .7], res=8)
                elif K.roof != 'hip':
                    for k in range(2):
                        Mx = Matrix.Translation(E + main.a * sx * (.15 + k * .28) + main.h * rr.uniform(-.25, .25) + V(0, 0, .03 - k * .03)) \
                            @ Matrix.Rotation(rr.uniform(0, 3), 4, 'Z') @ Matrix.Rotation(rr.uniform(-.5, .5), 4, 'X')
                        merged(f'Ridge_Loose_{j}_{end}_{k}', cover_template(), [(Mx, rr.random())], mat, detail=1)
        elif K.cover == 'shingle':
            for sg in (-1, 1):
                off = main.h * sg * .09 + V(0, 0, .07)
                beam(f'Ridge_Board_{j}_{sg}', A + off, B + off, .2, .025, mat, up=tuple(main.h * sg * math.sin(.6) + Z_UP * math.cos(.6)), bevel=.004, inst=False)
        elif K.cover == 'bamboo':
            o = (A + B) / 2 + V(0, 0, .08)
            Mx = Matrix.Translation(o) @ Matrix((tuple(-main.h), tuple(main.a), (0, 0, 1))).transposed().to_4x4() @ Matrix.Diagonal((1, (b - a) / BB_L, 1, 1))
            merged(f'Ridge_Bamboo_{j}', half_culm(BB_L, True, .14), [(Mx, rr.random())], mat)
            culm(f'Ridge_Culm_{j}', A + V(0, 0, .26), B + V(0, 0, .26), .045, K.M['bamboo'] or K.M['poles'])
            for k in range(int((b - a) / .6)):
                x = a + .3 + k * .6
                C.torus(f'Ridge_Lash_{j}_{k}', tuple(main.o + main.a * x + V(0, 0, .2)), .075, .008, K.M['rope'],
                        rot=tuple(frame_rot(main.a).to_euler()) if abs(main.a.x) < .5 else (0, math.pi / 2, 0), major=16, minor=5, detail=1)
        elif K.cover == 'thatch':
            p0, p1 = A + V(0, 0, .28), B + V(0, 0, .28)
            pole(f'Ridge_Thatch_{j}', p0, p1, .18, mat, verts=16, inst=False)
            S['parts'][-1]['grain'] = 'v'; S['parts'][-1]['grain_vec'] = (1, 0, 0) if abs(main.a.x) > .5 else (0, 1, 0)
            for k in range(3):
                q = main.h * ((k - 1) * .12) + V(0, 0, .18 * math.cos((k - 1) * .6) + .01)
                pole(f'Ridge_Liggers_{j}_{k}', p0 + q, p1 + q, .012, K.M['wattle'], verts=8, detail=1)
            pole(f'Ridge_Log_{j}', A + V(0, 0, .48), B + V(0, 0, .48), .04, K.M['poles'], verts=10)
            nx = max(1, int((b - a) / .9))
            for k in range(nx):                     # crossed pegs pinning the ridge log
                c = main.o + main.a * (a + (b - a) * (k + .5) / nx)
                for sg in (-1, 1):
                    pole(f'Ridge_Cross_{j}_{k}_{sg}', c + main.h * sg * .26 + V(0, 0, .3), c - main.h * sg * .07 + V(0, 0, .56), .022, K.M['poles'], verts=8)
    if K.roof == 'hip':
        hips(sls)
        RL = K.PX - K.PY
        for sx in (-1, 1):
            c = V(sx * RL, 0, K.RZ + .17)
            for sg in (-1, 1):
                pole(f'Hip_Finial_{sx}_{sg}', c + V(sx * .04, sg * .2, -.12), c + V(-sx * .02, -sg * .07, .14), .035, K.M['poles'], verts=10)
            C.torus(f'Hip_Finial_Lash_{sx}', tuple(c + V(0, 0, -.01)), .05, .008, K.M['rope'], rot=(math.pi / 2, 0, 0), major=12, minor=4, detail=1)


def hips(sls):
    """Four hip lines from the ridge ends to the eave corners: a heavy hip rafter under, ridge covering over."""
    rr = K.rr; mat = K.M['cover']; RL = K.PX - K.PY; E = K.HS + K.eave_out
    for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        top = V(sx * RL, 0, K.RZ); bot = V(sx * (RL + E), sy * E, K.RZ - K.TAN * E)
        d = (bot - top).normalized()
        keyx = 'L' if sx < 0 else 'R'; keyy = 'F' if sy < 0 else 'B'
        sl_y = next(s for s in sls if s.key == keyy)
        broken = [t for t in [k / 20 for k in range(21)] if sl_y.hole(sx * (RL + t * E), t * E / K.CA)]
        cut = min(broken) if broken else 1.0
        pole(f'Hip_Rafter_{i}', top, top.lerp(bot, cut) + d * .08, .06, K.M['poles'], verts=12)
        if cut < 1: splinters(f'Hip_Rafter_{i}_Brk', top.lerp(bot, cut) + d * .08, d, .06, K.M['poles'], rr)
        n_up = (sl_y.n + next(s for s in sls if s.key == keyx).n).normalized()
        up = (n_up - d * n_up.dot(d)).normalized()
        a_, b_ = top + up * .2, top.lerp(bot, cut) + up * .2
        if K.cover == 'tile':
            beam(f'Hip_Body_{i}', a_ - up * .08, b_ - up * .08, .24, .14, mat, up=tuple(up), bevel=.02, inst=False)
            items = []; L = (b_ - a_).length; t = .04
            while t < L - .15:
                c = a_ + d * (t + COV_L / 2) + up * .02
                Mx = Matrix.Translation(c) @ Matrix((tuple(d.cross(up)), tuple(d), tuple(up))).transposed().to_4x4()
                items.append((Mx, rr.random())); t += COV_L - .03
            merged(f'Hip_Covers_{i}', cover_template(), items, mat)
        elif K.cover == 'shingle':
            side = d.cross(up)
            for sg in (-1, 1):
                beam(f'Hip_Board_{i}_{sg}', a_ - up * .1 + side * sg * .08, b_ - up * .1 + side * sg * .08, .18, .025, mat,
                     up=tuple((up + side * sg * .7).normalized()), bevel=.004, inst=False)


# ---------------------------------------------------------------- roof assembly
def roof():
    sls = slopes()
    purlins_and_trusses(sls)
    for i, sl in enumerate(sls):
        bare = []
        rafters(sl, bare)
        boards(sl)
        fascia_and_verge(sl)
        COVERS[K.cover](sl, bare, 10 + i * 4)
    ridge_line(sls)
    K.slopes = sls


def lean_roof(cfg, idx):
    """A one-slope roof hung off a wall (annex or door canopy). cfg: o (top edge centre on the wall), h (outward),
    a (along the wall), tan, run (horizontal run to the eave beam), out (overhang past it), half (half length along a),
    posts (bool: posts under the eave beam), back (plank wall on the closed end: 'B' / 'F' / None)."""
    M = K.M; rr = K.rr
    tan = cfg['tan']; ang = math.atan(tan); ca = math.cos(ang)
    o = Vector(cfg['o']); h = Vector(cfg['h']); a = Vector(cfg['a'])
    s_end = (cfg['run'] + cfg['out']) / ca
    sl = Slope(f'Lean{idx}', o, h, a, tan, s_end, (lambda s, H=cfg['half']: (-H, H)), cfg['run'] / ca, cfg.get('hole'))
    sl.verge = True
    # ledger on the wall, eave beam on posts or brackets
    led = o - Z_UP * (RAFTER_R + .07)
    member(f'Lean{idx}_Ledger', led - a * cfg['half'], led + a * cfg['half'], .1, .14, M['wood'], up=tuple(h))
    eb = sl.at(0, cfg['run'] / ca) - Z_UP * (RAFTER_R + .07)
    member(f'Lean{idx}_EaveBeam', eb - a * (cfg['half'] - .05), eb + a * (cfg['half'] - .05), .14, .14, M['wood'])
    if cfg.get('posts'):
        for j, sg in enumerate((-1, 1)):
            p = eb + a * sg * (cfg['half'] - .2)
            member(f'Lean{idx}_Post_{j}', V(p.x, p.y, .1), V(p.x, p.y, p.z - .07), .14, .14, M['wood'], up=tuple(h))
            s_ = C.rock(f'Lean{idx}_Pad_{j}', (p.x, p.y, .02), (.3, .3, .16), M['stone'], rr.randrange(1 << 30), sub=2, round_=.3, chips=5, flat_bottom=.9)
            C.clip_axis(s_, 'z', -EMBED, None)
            K.lean_posts.append((p.x, p.y))
    else:
        for j, sg in enumerate((-1, 1)):
            p = eb + a * sg * (cfg['half'] - .1)
            q = V(*(o + a * sg * (cfg['half'] - .1) - h * .02 - Z_UP * .55))
            member(f'Lean{idx}_Bracket_{j}', q, p - Z_UP * .05, .1, .1, M['wood'], up=tuple(a))
    bare = []
    n = max(2, int(2 * cfg['half'] / .45))
    for i in range(n + 1):
        x = -cfg['half'] + .1 + (2 * cfg['half'] - .2) * i / n
        pole(f'Lean{idx}_Rafter_{i:02d}', sl.at(x, 0), sl.at(x, s_end + .05), RAFTER_R, M['poles'], verts=10)
    boards(sl)
    fascia_and_verge(sl)
    COVERS[K.cover](sl, bare, 40 + idx * 4)
    if cfg.get('back'):
        # closed end: horizontal boards from the ground up to the underside of the lean-to roof
        sy = 1 if cfg['back'] == 'B' else -1; yb = sy * (cfg['half'] - .06)
        x_wall, x_eave = (o - h * .06).x, eb.x
        z = .1; k = 0
        while True:
            zt = z + .19
            reach = (o.z - RAFTER_R - .08 - zt) / tan            # horizontal distance from the wall still under the roof
            if reach < .25: break
            xe = x_eave if reach >= abs(x_eave - x_wall) else x_wall + h.x * reach
            beam(f'Lean{idx}_BackBoard_{k}', V(x_wall, yb, z + .095), V(xe, yb, z + .095), .19, .026, M['plank'], up=(0, sy, 0), bevel=.005,
                 inst=reach >= abs(x_eave - x_wall))
            z = zt - .005; k += 1
    K.lean_slopes.append(sl)


# ---------------------------------------------------------------- interior and outside
def bed():
    wood = K.M['wood']; rr = K.rr
    side = K.bed
    if side == 'left_back': x0, x1, y0, y1 = -K.PX + .13, -K.PX + .95, K.PY - .15 - 1.84, K.PY - .15
    elif side == 'right_back': x0, x1, y0, y1 = K.PX - .95, K.PX - .13, K.PY - .15 - 1.84, K.PY - .15
    elif side == 'back_left': x0, x1, y0, y1 = -K.PX + .2, -K.PX + .2 + 1.84, K.PY - .95, K.PY - .13
    elif side == 'back_right': x0, x1, y0, y1 = K.PX - .2 - 1.84, K.PX - .2, K.PY - .95, K.PY - .13
    else: return
    h = .44; along_y = (y1 - y0) > (x1 - x0)
    for j, (x, y) in enumerate(((x0 + .04, y0 + .04), (x1 - .04, y0 + .04), (x0 + .04, y1 - .04), (x1 - .04, y1 - .04))):
        head = (y > (y0 + y1) / 2) if along_y else (x < (x0 + x1) / 2)
        beam(f'Bed_Leg_{j}', (x, y, FLOOR), (x, y, FLOOR + h + (.2 if head else .06)), .07, .07, wood, up=(1, 0, 0), bevel=.008)
    if along_y:
        for sd, x in (('L', x0 + .04), ('R', x1 - .04)): beam(f'Bed_Rail_{sd}', (x, y0, FLOOR + h - .05), (x, y1, FLOOR + h - .05), .06, .1, wood)
        for e, y in (('Foot', y0 + .04), ('Head', y1 - .04)): beam(f'Bed_End_{e}', (x0, y, FLOOR + h - .05), (x1, y, FLOOR + h - .05), .06, .1, wood)
        beam('Bed_HeadRail', (x0, y1 - .04, FLOOR + h + .17), (x1, y1 - .04, FLOOR + h + .17), .06, .07, wood)
        y = y0 + .12; k = 0
        while y < y1 - .1:
            if k not in (3, 9): beam(f'Bed_Slat_{k:02d}', (x0 + .02, y, FLOOR + h + .012), (x1 - .02, y, FLOOR + h + .012), .085, .022, wood, bevel=.004)
            y += .125; k += 1
    else:
        for sd, y in (('F', y0 + .04), ('B', y1 - .04)): beam(f'Bed_Rail_{sd}', (x0, y, FLOOR + h - .05), (x1, y, FLOOR + h - .05), .06, .1, wood)
        for e, x in (('Head', x0 + .04), ('Foot', x1 - .04)): beam(f'Bed_End_{e}', (x, y0, FLOOR + h - .05), (x, y1, FLOOR + h - .05), .06, .1, wood)
        beam('Bed_HeadRail', (x0 + .04, y0, FLOOR + h + .17), (x0 + .04, y1, FLOOR + h + .17), .06, .07, wood)
        x = x0 + .12; k = 0
        while x < x1 - .1:
            if k not in (4, 8): beam(f'Bed_Slat_{k:02d}', (x, y0 + .02, FLOOR + h + .012), (x, y1 - .02, FLOOR + h + .012), .085, .022, wood, bevel=.004)
            x += .125; k += 1
    C.hull_box('Collision_Bed', ((x0 + x1) / 2, (y0 + y1) / 2, (FLOOR + h + .2) / 2), (x1 - x0, y1 - y0, FLOOR + h + .2))
    K.bed_box = (x0, y0, x1, y1)


def quiver():
    if not K.quiver: return
    M = K.M; x = K.quiver[0]
    peg = V(x, K.PY - .08, 1.78)
    pole('Quiver_Peg', peg, peg + V(0, -.13, .02), .016, M['wood'], verts=8)
    prof = [(0, 0), (.046, 0), (.052, .015), (.052, .48), (.06, .5), (.06, .52), (.052, .52), (.045, .5), (.045, .025), (0, .025)]
    Mx = Matrix.Translation(V(x + .14, K.PY - .135, 1.16)) @ Matrix.Rotation(math.radians(-7), 4, 'Y') @ Matrix.Rotation(math.radians(4), 4, 'X')
    with C.xf(Mx):
        C.lathe('Quiver_Body', prof, (0, 0, 0), M['leather'], seg=20)
        for j, z in enumerate((.1, .4)): C.torus(f'Quiver_Band_{j}', (0, 0, z), .054, .007, M['leather'], major=24, minor=6, detail=1)
    top = Mx @ V(-.05, 0, .5); bot = Mx @ V(-.05, 0, .1)
    C.tube('Quiver_Strap', [tuple(bot), tuple(bot + V(-.03, .01, .2)), tuple(top + V(-.05, .015, .05)), tuple(peg + V(0, -.1, .03)), tuple(top + V(.06, 0, .02))],
           .008, M['leather'], res=4)


def door_leaf():
    M = K.M; rr = K.rr; mode, side = K.door_leaf
    wd = K.JAMB[1] - K.JAMB[0] + .04
    if mode == 'lean':
        lean = math.atan(.2 / 1.93)
        x = K.JAMB[0] - .2 - wd / 2 if side == 'L' else K.JAMB[1] + .2 + wd / 2
        Mx = Matrix.Translation(V(x, -K.PY - .35, 0)) @ RZ(math.radians(-5 if side == 'L' else 5)) @ RY(math.radians(2.5)) @ RX(-lean)
    elif mode == 'side':       # carried round and leant against a side wall, outside
        lean = math.atan(.11 / 1.93); sx = -1 if side == 'L' else 1
        Mx = Matrix.Translation(V(sx * (K.PX + FOOT_T / 2 + .14), -K.PY + .9, 0)) @ RZ(math.radians(90 * sx + 4)) @ RY(math.radians(2)) @ RX(-lean)
    elif mode == 'flat':       # fell flat outside the door
        Mx = Matrix.Translation(V((K.JAMB[0] + K.JAMB[1]) / 2 + .25, -K.PY - .35, .045)) @ RZ(math.radians(70)) @ RX(math.radians(-90 + 1.5))
    else:
        return
    if K.frame == 'bamboo':    # a leaf of culms side by side on three split-culm battens, lashed with cord
        with C.xf(Mx):
            n = int(wd / .062); x = -wd / 2 + wd / n / 2
            for k in range(n):
                top = 1.93 - rr.uniform(0, .05) - (.25 if k in (n // 2, n // 2 + 1) else 0)
                culm(f'Door_Culm_{k:02d}', (x, 0, .02), (x, 0, top), .028, M['bamboo'], gap=.5)
                x += wd / n
            for j, z in enumerate((.25, 1.0, 1.7)):
                pole(f'Door_Batten_{j}', (-wd / 2 + .02, .045, z), (wd / 2 - .02, .045, z), .02, M['bamboo'], verts=8)
                for e in (-1, 1):
                    C.torus(f'Door_Lash_{j}_{e}', (e * (wd / 2 - .1), .03, z), .035, .006, M['rope'], rot=(0, math.pi / 2, 0), major=10, minor=3, detail=1)
        pts = [Mx @ V(x, y, z) for x in (-wd / 2, wd / 2) for y in (-.03, .07) for z in (0, 1.95)]
        C.hull('Collision_DoorLeaf', [tuple(p) for p in pts])
        return
    with C.xf(Mx):
        n = 4; bw = wd / n; x = -wd / 2
        for k in range(n):
            z0 = .3 if (k == 2 and mode == 'lean') else 0.0
            beam(f'Door_Plank_{k}', (x + bw / 2, 0, z0), (x + bw / 2, 0, 1.93 - rr.uniform(0, .03)), bw - .006, .035, M['plank'], up=(0, -1, 0), bevel=.006)
            if z0: splinters('Door_Plank_Break', V(x + bw / 2, 0, z0), (0, 0, -1), .03, M['plank'], rr)
            x += bw
        for j, z in enumerate((.25, 1.0, 1.7)):
            beam(f'Door_Batten_{j}', (-wd / 2 + .04, .033, z), (wd / 2 - .04, .033, z), .1, .03, M['plank'], bevel=.006)
        beam('Door_Brace', (-wd / 2 + .1, .033, .3), (wd / 2 - .1, .033, .95), .09, .028, M['plank'], up=(0, 1, 0), bevel=.006)
        for j, z in enumerate((.25, 1.7)):
            C.box(f'Door_Strap_{j}', (-wd / 2 + .3, -.02, z), (.56, .006, .045), M['iron'], bevel=.002, detail=1)
    pts = [Mx @ V(x, y, z) for x in (-wd / 2, wd / 2) for y in (-.03, .07) for z in (0, 1.95)]
    C.hull('Collision_DoorLeaf', [tuple(p) for p in pts])


def rubble():
    """Lost wall and roof material on the ground: piles named in the config plus whatever the build dropped."""
    M = K.M; rr = K.rr
    pile = []
    for pc in K.rubble:
        cx, cy = pc['c']; R = pc['r']
        if pc.get('core'):      # a tall heap needs a body under the loose lumps, or they float
            core = C.rock(f'Rubble_Core_{len(pile):03d}', (cx, cy, pc['h'] * .28), (R * 1.6, R * 1.4, pc['h'] * .72), M['infill'], rr.randrange(1 << 30),
                          rot=(0, 0, rr.uniform(0, 3)), sub=2, round_=.55, chips=5, wobble=.14)
            C.clip_axis(core, 'z', -EMBED, None)
        for j in range(pc.get('n', 24)):
            ang = rr.uniform(0, math.tau); rad = R * math.sqrt(rr.random())
            x, y = cx + math.cos(ang) * rad, cy + math.sin(ang) * rad
            if _blocked(x, y): continue
            z0 = FLOOR if abs(x) < K.PX - .1 and abs(y) < K.PY - .1 else 0.0
            hgt = (1 - rad / R) * pc.get('h', .35)
            kind = rr.choice(pc.get('kinds', ('lump', 'lump', 'stone')))
            sz = rr.uniform(.1, .26)
            mat = M['infill'] if kind == 'lump' else M['stone']
            s = C.rock(f'Rubble_{len(pile):03d}', (x, y, z0 + hgt * rr.uniform(.3, 1) + sz * .25), (sz * rr.uniform(.9, 1.5), sz, sz * rr.uniform(.45, .8)), mat,
                       rr.randrange(1 << 30), rot=(rr.uniform(-.4, .4), rr.uniform(-.4, .4), rr.uniform(0, 3)), sub=1, round_=.4 if kind == 'lump' else .3,
                       chips=4, wobble=.1, detail=1 if sz < .16 else 0)
            pile.append(s)
        C.hull_box(f'Collision_Rubble_{len(pile)}', (cx, cy, pc.get('h', .35) / 2 - EMBED / 2), (R * 1.3, R * 1.3, pc.get('h', .35) + EMBED))
    # crumbs sitting on the broken top of a plastered / earth wall, so the break reads as crumbled, not sawn
    if K.wall in ('earth', 'daub', 'stone_daub'):
        t = .3 if K.wall == 'earth' else .12
        for w, f in K.keep.items():
            L = wall_len(w); u = .1; k = 0
            while u < L - .1:
                z = kh(w, u)
                if K.FOOT_TOP + .12 < z < K.PLATE[0] - .12:
                    sz = rr.uniform(.06, .11) * (1.4 if K.wall == 'earth' else 1.0)
                    C.rock(f'Crumb_{w}_{k:02d}', tuple(wall_point(w, u, z - sz * .25, rr.uniform(-t, t) * .25)), (sz * 1.4, min(t, sz * 1.1), sz * .75),
                           M['infill'], rr.randrange(1 << 30), rot=(rr.uniform(-.3, .3), rr.uniform(-.3, .3), rr.uniform(0, 3)), sub=1, round_=.45,
                           chips=3, wobble=.15, detail=1)
                    k += 1
                u += rr.uniform(.2, .34)
    # timbers that came down with the wall and lean where they landed: (foot, head, width, depth)
    for k, (a, b, w_, h_) in enumerate(K.leaners):
        member(f'Fallen_Timber_{k}', V(*a), V(*b), w_, h_, M['wood'])
        splinters(f'Fallen_Timber_{k}_Brk', V(*b), V(*b) - V(*a), .05, M['wood'], rr)
    # members and poles that fell
    for k, item in enumerate(K.debris_pts):
        if item[0] in ('member', 'pole'):
            a, b = item[1], item[2]
            L = (b - a).length
            mid0 = Vector(((a.x + b.x) / 2, (a.y + b.y) / 2, 0))
            mid0.x = max(-K.PX - .25, min(K.PX + .25, mid0.x)); mid0.y = max(-K.PY - .2, min(K.PY + .2, mid0.y))
            yaw0 = math.atan2(b.y - a.y, b.x - a.x) + rr.uniform(-.6, .6)
            # the whole length must lie clear of the room, door and bed: try nearby spots, turns and shorter pieces
            placed = None
            for half in (min(L, 1.6) / 2, min(L, 1.1) / 2, .4):
                for r in (0, .3, .6, 1.0, 1.4):
                    for kk in range(12 if r else 1):
                        mid = mid0 + V(math.cos(kk * .52) * r, math.sin(kk * .52) * r, 0)
                        for dy in (0, .5, -.5, 1.0, -1.0, 1.57):
                            dv = V(math.cos(yaw0 + dy), math.sin(yaw0 + dy), 0) * half
                            if not any(_blocked(*(mid + dv * t).xy) for t in (-1, -.5, 0, .5, 1)):
                                placed = (mid, dv); break
                        if placed: break
                    if placed: break
                if placed: break
            if not placed: continue
            mid, dv = placed
            z0 = FLOOR if abs(mid.x) < K.PX - .1 and abs(mid.y) < K.PY - .1 else 0.0
            r_ = item[3] if item[0] == 'pole' else min(item[3], item[4]) / 2
            lift = rr.uniform(.0, .35)
            p0, p1 = mid - dv + V(0, 0, z0 + r_), mid + dv + V(0, 0, z0 + r_ + lift)
            for ax, lim in (('x', 2.6), ('y', 2.1)):          # slide back inside the slot
                over = max(abs(getattr(p0, ax)), abs(getattr(p1, ax))) - lim
                if over > 0:
                    sgn = 1 if max(getattr(p0, ax), getattr(p1, ax)) > lim else -1
                    setattr(p0, ax, getattr(p0, ax) - sgn * over); setattr(p1, ax, getattr(p1, ax) - sgn * over)
            if item[0] == 'pole': pole(f'Debris_Pole_{k}', p0, p1, r_, item[4], verts=10, detail=0)
            else: beam(f'Debris_Member_{k}', p0, p1, item[3], item[4], item[5], up=(0, 0, 1), inst=False)
        elif item[0] == 'lump':
            p = item[1]; mat = item[2]; amount = item[3]
            out = V(p.x, p.y, 0) * (1 + .12 / max(.5, V(p.x, p.y, 0).length))
            for j in range(min(6, 2 + int(amount * 6))):
                q = out + V(rr.uniform(-.35, .35), rr.uniform(-.35, .35), 0)
                if _blocked(q.x, q.y): continue
                sz = rr.uniform(.06, .14)
                C.rock(f'Debris_Lump_{k}_{j}', (q.x, q.y, sz * .3), (sz * 1.3, sz, sz * .6), mat, rr.randrange(1 << 30), rot=(0, 0, rr.uniform(0, 3)),
                       sub=1, round_=.5, chips=3, wobble=.1, detail=1)


def _blocked(x, y):
    if abs(x) > 2.5 or abs(y) > 2.0: return True          # loose pieces stay well inside the 5.5 x 4.5 m slot
    (rx0, ry0), (rx1, ry1) = K.room
    if rx0 - .22 < x < rx1 + .22 and ry0 - .22 < y < ry1 + .22: return True
    if K.JAMB[0] - .15 < x < K.JAMB[1] + .15 and -K.PY - .9 < y < -K.PY + .9: return True
    bb = getattr(K, 'bed_box', None)
    if bb and bb[0] - .05 < x < bb[2] + .05 and bb[1] - .05 < y < bb[3] + .05: return True
    return False


def _nudge(p):
    for r in (.5, 1.0, 1.5, 2.0):
        for k in range(12):
            q = p + V(math.cos(k * .52) * r, math.sin(k * .52) * r, 0)
            if not _blocked(q.x, q.y): return q
    return p


def roof_shards():
    """Tile / shingle / straw remains on the floor under each hole."""
    rr = K.rr; mat = K.M['cover']; items = []
    for sl in K.slopes + getattr(K, 'lean_slopes', []):
        for k in range(160):
            x = rr.uniform(*sl.xlim(sl.s_end)); s = rr.uniform(0, sl.s_end)
            if not sl.hole(x, s): continue
            p = sl.at(x, s) + V(rr.uniform(-.2, .2), rr.uniform(-.2, .2), 0)
            p.x = max(-2.6, min(2.6, p.x)); p.y = max(-2.1, min(2.1, p.y))
            if _blocked(p.x, p.y) or len(items) > 26: continue
            inside = abs(p.x) < K.PX - .12 and abs(p.y) < K.PY - .12
            Lr = rr.uniform(.08, .16)
            z = (FLOOR if inside else 0) + .016
            Mx = Matrix.Translation(V(p.x, p.y, z)) @ RZ(rr.uniform(0, math.tau)) @ RY(rr.uniform(-.25, .25)) @ RX(rr.choice((0, math.pi)))
            items.append((Mx @ Matrix.Diagonal((rr.uniform(.4, .8), Lr / PAN_L, 1, 1)), rr.random()))
    if K.cover == 'tile': merged('Roof_Shards', pan_template(), items, mat, detail=1)
    elif K.cover == 'shingle': merged('Roof_Shards', shingle_template(), items, mat, detail=1)
    elif K.cover == 'bamboo': merged('Roof_Shards', half_culm(.5, True), items, mat, detail=1)


def collision():
    zc = lambda h: (h - EMBED) / 2
    C.hull_box('Collision_Floor', (0, 0, (FLOOR - EMBED) / 2), (2 * K.PX - .2, 2 * K.PY - .2, FLOOR + EMBED))
    X0 = K.PX + FOOT_T / 2
    for w in ('Front', 'Back', 'Left', 'Right'):
        o, d, out, posts = K.WALLS[w]
        L = posts[-1]
        lo, hi = (-FOOT_T / 2, L + FOOT_T / 2) if w in ('Front', 'Back') else (FOOT_T / 2, L - FOOT_T / 2)
        gaps = [(K.door_u[0] + .08, K.door_u[1] - .08)] if w == 'Front' else []
        step = .2; u = lo; segs = []
        edges = sorted([e for g in gaps for e in g if lo < e < hi])
        while u < hi - 1e-6:
            u1 = min([hi, u + step] + [e for e in edges if e > u + 1e-6]); um = (u + u1) / 2
            if not any(g0 < um < g1 for g0, g1 in gaps):
                h = min(kh(w, um), K.PLATE[1]); hq = round(h / .25) * .25 if h < K.PLATE[1] else K.PLATE[1]
                if hq >= .4:
                    if segs and abs(segs[-1][1] - u) < 1e-6 and segs[-1][2] == hq: segs[-1][1] = u1
                    else: segs.append([u, u1, hq])
            u = u1
        for j, (a, b, h) in enumerate(segs):
            c = wall_point(w, (a + b) / 2, zc(h))
            C.hull_box(f'Collision_Wall_{w}_{j}', c, (b - a, FOOT_T, h + EMBED), rot_z=math.atan2(d.y, d.x))
    C.hull_box('Collision_Lintel', ((K.JAMB[0] + K.JAMB[1]) / 2, -K.PY, (K.lintel + K.PLATE[1]) / 2), (K.JAMB[1] - K.JAMB[0], FOOT_T, K.PLATE[1] - K.lintel))
    C.hull_box('Collision_Threshold', ((K.JAMB[0] + K.JAMB[1]) / 2, -K.PY - .02, (THRESH - EMBED) / 2), (K.JAMB[1] - K.JAMB[0], FOOT_T + .08, THRESH + EMBED))
    for j, (x, y) in enumerate(K.lean_posts):
        C.hull_box(f'Collision_LeanPost_{j}', (x, y, 1.0), (.2, .2, 2.0))


def balance_slots():
    """Spread the materials over the four atlas slots (Main / Roof / Wall / Stone) so each slot gets a similar
    surface area to texture. Area is counted once per UV-instanced key; footing and rubble stones are discounted for
    their hidden beds and backs. Longest-processing-time greedy: biggest material first into the emptiest slot."""
    from wr_mats import MAT_INFO
    seen, area = set(), {}
    for o in S['parts']:
        if o.type != 'MESH' or not o.data.materials: continue
        m = o.data.materials[0].name
        k = o.get('inst_key')
        if k:
            if k in seen: continue
            seen.add(k)
        sc = o.matrix_world.to_scale(); f = abs(sc.x * sc.y * sc.z) ** (2 / 3)
        me = o.data; a = 0.0
        ik = me.attributes.get('inst_key'); it = me.attributes.get('inst_tile')
        if ik is not None and ik.domain == 'FACE':
            kv = [0] * len(me.polygons); tv = [0] * len(me.polygons)
            ik.data.foreach_get('value', kv); it.data.foreach_get('value', tv)
            first = {}
            for kk, tt in zip(kv, tv):
                if kk and (kk not in first or tt < first[kk]): first[kk] = tt
            for p, kk, tt in zip(me.polygons, kv, tv):
                if not kk or first[kk] == tt: a += p.area
        else:
            a = sum(p.area for p in me.polygons)
        a *= f * (.55 if 'Stone' in m or 'Rubble' in o.name else .8 if 'Floor' in o.name else 1.0)
        area[m] = area.get(m, 0.0) + a
    load = {s: 0.0 for s in ('Main', 'Roof', 'Wall', 'Stone')}
    for m, a in sorted(area.items(), key=lambda t: -t[1]):
        s = min(load, key=load.get); MAT_INFO[m]['slot'] = s; load[s] += a
    print(f'[houses] {K.id} slot areas m2:', {s: round(v, 1) for s, v in load.items()},
          {m: (MAT_INFO[m]['slot'], round(a, 1)) for m, a in sorted(area.items(), key=lambda t: -t[1])}, flush=True)


def _report_intrusions():
    """Log parts whose bounds reach into the door passage or the 2 x 2 m room (the export check counts vertices)."""
    bpy.context.view_layer.update()
    for nm, (lo, hi) in (('door', door_box()), ('room', room_box())):
        hits = []
        for o in S['parts']:
            ws = [o.matrix_world @ Vector(c) for c in o.bound_box]
            lo_w = [min(getattr(w, a) for w in ws) for a in 'xyz']; hi_w = [max(getattr(w, a) for w in ws) for a in 'xyz']
            if all(lo_w[k] < hi[k] and hi_w[k] > lo[k] for k in range(3)):
                hits.append(o.name)
        print(f'[houses] {K.id} parts with bounds in the {nm} box:', hits[:40], flush=True)
    far = []
    for o in S['parts']:
        ws = [o.matrix_world @ Vector(c) for c in o.bound_box]
        ext = (min(w.x for w in ws), max(w.x for w in ws), min(w.y for w in ws), max(w.y for w in ws), max(w.z for w in ws))
        if ext[0] < -2.72 or ext[1] > 2.72 or ext[2] < -2.22 or ext[3] > 2.22 or ext[4] > 3.75:
            far.append((o.name, tuple(round(e, 2) for e in ext)))
    print(f'[houses] {K.id} parts near the slot limit:', sorted(far, key=lambda t: min(t[1][0], -t[1][1]))[:14], flush=True)


def recenter():
    """Move everything so the footprint (bounding box in plan) is centred on the origin."""
    bpy.context.view_layer.update()
    xs, ys = [], []
    for o in S['parts']:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c); xs.append(w.x); ys.append(w.y)
    off = Vector((-(min(xs) + max(xs)) / 2, -(min(ys) + max(ys)) / 2, 0))
    if off.length < 1e-4: return
    T = Matrix.Translation(off)
    for o in S['parts'] + S['coll']: o.matrix_world = T @ o.matrix_world
    K.offset = off


# ---------------------------------------------------------------- entry
def lashings_and_braces():
    """Hemp lashings wound tight round square posts (a repair binding a split post, or a cleat tied on), and
    knee braces from post to wall plate in the end bays."""
    M = K.M; rr = K.rr
    for k, (w, i, zc) in enumerate(K.lashings):
        o, d, out, posts = K.WALLS[w]
        if kh(w, posts[i]) < zc + .1: continue
        c = wall_point(w, posts[i], 0)
        h = K.PH + .008; turns = rr.randint(4, 6); pitch = .024
        pts = []
        for t in range(turns * 8 + 1):
            a = t / 8 * math.tau + math.pi / 8
            # rounded square: clamp a circle onto the post faces, keeping the corners eased
            cx, cy = math.cos(a), math.sin(a)
            m = max(abs(cx), abs(cy)); sx, sy = cx / m, cy / m
            sx, sy = sx * .9 + cx * .1, sy * .9 + cy * .1
            q = c + d * (sx * h) + out * (sy * h) + V(0, 0, zc - turns * pitch / 2 + t / 8 * pitch)
            pts.append(tuple(q))
        # the loose end hangs down a little
        last = Vector(pts[-1]); pts += [tuple(last + out * .01 + V(0, 0, -.05)), tuple(last + out * .014 + V(.01, 0, -.13))]
        C.tube(f'Post_Lash_{k}', pts, .0085, M['rope'], res=4, caps=True)
    for k, (w, i, side) in enumerate(K.braces):
        o, d, out, posts = K.WALLS[w]
        u = posts[i] + side * K.PH
        if kh(w, u) < K.PLATE[0]: continue
        a = wall_point(w, u + side * .03, K.PLATE[0] - .62, .04)
        b = wall_point(w, u + side * .62, K.PLATE[0] - .02, .04)
        member(f'Brace_{w}_{k}', a, b, .1, .11, M['wood'], up=(out.x, out.y, 0))


def build_house(cfg):
    _PROTO.clear()
    configure(cfg)
    S['iface_planes'] = []
    K.lean_posts = []
    materials()
    rr = K.rr
    footing(K.M['stone'], rr)
    floor(K.M['earth_floor'])
    walls()
    lashings_and_braces()
    roof()
    K.lean_slopes = []
    for i, lc in enumerate([c for c in (K.annex, K.canopy) if c]):
        lean_roof(lc, i)
    bed(); quiver(); door_leaf()
    rubble(); roof_shards()
    collision()
    balance_slots()
    _report_intrusions()
    recenter()
    for me, _, _ in _PROTO.values(): bpy.data.meshes.remove(me)
    _PROTO.clear()


def door_box():
    return ((K.JAMB[0] + .06 + K.offset.x, -K.PY - .53 + K.offset.y, THRESH + .05), (K.JAMB[1] - .012 + K.offset.x, -K.PY + .37 + K.offset.y, K.lintel - .02))


def room_box():
    (x0, y0), (x1, y1) = K.room
    return ((x0 + K.offset.x, y0 + K.offset.y, FLOOR + .05), (x1 + K.offset.x, y1 + K.offset.y, 1.95))


def house_checks(lods, colls, S):
    db, rb = door_box(), room_box()
    return {
        'door_clear_at_least_0p9_x_1p9': K.JAMB[1] - K.JAMB[0] >= .9 and K.lintel - THRESH >= 1.9,
        'door_passage_free_of_geometry': _verts_in(lods[0], db) == 0,
        'door_passage_free_of_collision': not [h for h in _hull_hits(colls, db) if 'Floor' not in h and 'Threshold' not in h],
        'interior_2x2_free_of_geometry': _verts_in(lods[0], rb) == 0,
        'interior_2x2_free_of_collision': not [h for h in _hull_hits(colls, rb) if 'Floor' not in h],
        'interior_box_is_2x2': rb[1][0] - rb[0][0] >= 2.0 - 1e-6 and rb[1][1] - rb[0][1] >= 2.0 - 1e-6,
    }


# ---------------------------------------------------------------- the eight houses
def _h01_front_left(x, s):      # front-left corner of the roof and its eave
    return x < -1.35 + .35 * math.sin(2.1 * s + .4) + .18 * math.sin(6.3 * s) - .5 * max(0, 1.2 - s) * 1.6 and s > .55 + .2 * math.sin(3 * x)


HOUSES = {
    'H01_StoneTimberHouse': dict(
        id='H01', seed=101, PY=1.8, TAN=.44, FOOT_TOP=.92, wall='stone_daub', MID=None,
        front_posts=(0, 1.05, 1.83, 2.91, 3.69, 4.74), door_u=(1.83, 2.91), back_posts=(0, 1.58, 3.16, 4.74),
        windows=[dict(wall='Front', bay=0, row=0, kind='shutter', z=(1.3, 1.95), open=3),
                 dict(wall='Front', bay=3, row=0, kind='shutter', z=(1.3, 1.95), open=16),
                 dict(wall='Right', bay=1, row=0, kind='bars', z=(1.45, 1.95), missing=(2,)),
                 dict(wall='Back', bay=1, row=0, kind='bars', z=(1.45, 1.95), snapped=(1,))],
        holes={'F': _h01_front_left},
        purlin_breaks=[dict(slope='F', level='wall', x=-1.6, keep='right', fallen='hang', deg=22)],
        keep={'Left': lambda u: 99 if u > 1.0 else 1.6 + u * .9 + .08 * math.sin(u * 19)},
        gable_keep={'L': lambda u: 99 if u > -.55 else 3.0 + (u + .55) * 1.8},
        rubble=[dict(c=(-2.35, -1.9), r=.32, n=12, h=.22, kinds=('stone', 'lump', 'lump'))],
        door_leaf=('lean', 'L'), bed='right_back', quiver=(-1.2,), room=((-1.15, -1.55), (.85, .45)),
        lashings=[('Front', 1, 1.25), ('Front', 4, 1.3), ('Back', 0, 1.55), ('Back', 3, 1.55), ('Right', 1, 1.1)],
        braces=[('Back', 0, 1), ('Back', 3, -1), ('Right', 0, 1), ('Right', 2, -1)], foot_course=.2, foot_lens=(.24, .33, .43),
        palette=dict(tile=('#3E4448', '#2E3336', '#565C60'), moss=.45, wood_dark='#4E453B', wood_light='#A09078', mud='#8C7458', lime='#CDBFA2', lime_amt=.5, age_grey=.6, cracks=.8,
                     stone=('#686C70', '#4C5054', '#84888C'), stone_moss=.3)),
    'H07_DarkFrameHouse': dict(
        id='H07', seed=707, PY=1.72, TAN=.4, PLATE=(2.4, 2.54), MID=(1.42, 1.54), SILL=(.5, .64), lintel=2.08,
        front_posts=(0, .98, 2.06, 3.3, 4.74), door_u=(.98, 2.06), back_posts=(0, .98, 2.06, 3.3, 4.74), side_posts=(0, 1.72, 3.44),
        windows=[dict(wall='Front', bay=0, row=1, kind='boarded'),
                 dict(wall='Right', bay=1, row=1, kind='bars', missing=(1,)),
                 dict(wall='Back', bay=0, row=1, kind='bars', snapped=(2,))],
        patches=[dict(wall='Back', bay=3, row=0), dict(wall='Back', bay=3, row=1)],
        keep={'Front': lambda u: 99 if u < 3.45 else 2.5 - (u - 3.45) * 1.55 + .1 * math.sin(u * 13),
              'Right': lambda u: 99 if u > 1.5 else .55 + u * 1.25 + .08 * math.sin(u * 17)},
        holes={'F': blob(2.35, 1.5, 1.25, 1.25, 1.3, .18)},
        purlin_breaks=[dict(slope='F', level='wall', x=1.0, keep='left', fallen='floor'),
                       dict(slope='F', level='mid', x=1.45, keep='left', fallen='hang', deg=30)],
        canopy=dict(o=(-.6, -1.84, 2.45), h=(0, -1, 0), a=(1, 0, 0), tan=.5, run=.3, out=.07, half=1.0, posts=False),
        rubble=[dict(c=(2.45, -1.95), r=.7, n=13, h=.4, kinds=('lump', 'lump', 'stone'))],
        leaners=[((2.3, -2.15, .06), (1.25, -1.62, 1.95), .14, .12), ((1.7, -1.15, .07), (2.28, -.3, 1.85), .12, .1),
                 ((1.65, -2.15, .05), (2.2, -1.45, .55), .2, .035)],
        door_leaf=('lean', 'L'), bed='back_left', quiver=(1.0,), room=((-1.1, -1.45), (.9, .55)),
        gable_keep={'R': lambda u: 99 if u > -.15 else -1},
        palette=dict(tile=('#4C4452', '#352F3B', '#625A68'), moss=.35, wood_dark='#22170F', wood_light='#4E3B2A', mud='#8E765C',
                     lime='#CBBFA4', lime_amt=.62, age_grey=.5, cracks=.8, stone=('#5F6466', '#474C4E', '#7A7F80'), stone_moss=.5)),
    'H05_LimewashAnnexHouse': dict(
        id='H05', seed=505, PX=1.85, PY=1.78, TAN=.44,
        front_posts=(0, 1.7, 2.8, 3.7), door_u=(1.7, 2.8), back_posts=(0, 1.85, 3.7), side_posts=(0, 1.78, 3.56),
        windows=[dict(wall='Front', bay=0, row=1, kind='bars', u=(.45, 1.15)),
                 dict(wall='Right', bay=0, row=1, kind='bars', missing=(2,))],
        holes={'F': blob(.45, 1.55, .72, .62, .7, .2)},
        annex=dict(o=(-1.97, 0, 2.18), h=(-1, 0, 0), a=(0, 1, 0), tan=.45, run=1.0, out=.17, half=1.98, posts=True, back='B'),
        door_leaf=('lean', 'R'), bed='left_back', quiver=(.9,), room=((-.72, -1.5), (1.28, .5)),
        palette=dict(tile=('#3E4C60', '#2E3A4C', '#56647A'), moss=.3, wood_dark='#4C4238', wood_light='#90806A', mud='#9A7A5A', lime='#D2CAB6', lime_amt=.66,
                     age_grey=.6, cracks=.75,
                     stone=('#6A7070', '#51585A', '#858A8A'), stone_moss=.4)),
    'H04_StrawThatchHouse': dict(
        id='H04', seed=404, PX=2.3, PY=1.5, PLATE=(2.2, 2.34), TAN=.44, cover='thatch', eave_out=.45, gable_out=.28,
        front_posts=(0, .95, 1.65, 2.73, 3.6, 4.6), door_u=(1.65, 2.73), back_posts=(0, 1.53, 3.07, 4.6), side_posts=(0, 1.5, 3.0),
        windows=[dict(wall='Front', bay=4, row=1, kind='bars', missing=(1,)),
                 dict(wall='Right', bay=0, row=1, kind='bars')],
        keep={'Front': lambda u: 99 if u > 1.0 else 1.05 + u * .9 + .08 * math.sin(u * 17),
              'Left': lambda u: 99 if u > 1.7 else 1.0 + u * .55 + .08 * math.sin(u * 13)},
        gable_keep={'L': lambda u: 99 if u > .25 else 2.45 + .1 * math.sin(u * 9)},
        holes={'F': lambda x, s: x < -1.3 + .2 * math.sin(3.3 * s + .5) + .1 * math.sin(9 * s),
               'B': lambda x, s: x < -2.0 + .14 * math.sin(4 * s + 1) and s < 1.4},
        purlin_breaks=[dict(slope='F', level='mid', x=-1.3, keep='right', fallen='hang', deg=28),
                       dict(slope='F', level='wall', x=-1.1, keep='right', fallen='floor')],
        truss_broken=(0,),
        rubble=[dict(c=(-2.3, -.9), r=.5, n=22, h=.32), dict(c=(-2.1, -1.75), r=.3, n=10, h=.2)],
        door_leaf=('lean', 'R'), bed='right_back', quiver=(.6,), room=((-1.1, -1.27), (.9, .73)),
        palette=dict(thatch=('#C9A458', '#7E6234'), wood_grey=.45, mud='#8A6C4C', lime='#C4A472', lime_amt=.62, age_grey=.3, cracks=.8,
                     stone=('#78746A', '#5C5850', '#948E84'), stone_moss=.5)),
    'H03_BambooWeaveHouse': dict(
        id='H03', seed=303, PX=2.3, PY=1.5, FOOT_TOP=.3, SILL=(.3, .42), PLATE=(2.45, 2.59), TAN=.4, cover='bamboo',
        frame='bamboo', wall='weave', footing='piers',
        front_posts=(0, .9, 1.6, 2.7, 3.6, 4.6), door_u=(1.6, 2.7), back_posts=(0, 1.53, 3.07, 4.6), side_posts=(0, 1.5, 3.0),
        windows=[dict(wall='Right', bay=1, row=0, kind='torn'),
                 dict(wall='Front', bay=0, row=1, kind='bars')],
        holes={'F': blob(.05, .45, 1.05, .72, 2.1, .22), 'B': blob(.25, .42, .9, .6, .9, .22)},
        purlin_breaks=[dict(slope='F', level='mid', x=.2, keep='left', fallen='floor')],
        canopy=dict(o=(-.15, -1.56, 2.54), h=(0, -1, 0), a=(1, 0, 0), tan=.25, run=.6, out=.08, half=1.25, posts=True),
        door_leaf=('lean', 'R'), bed='left_back', quiver=(.9,), room=((-1.2, -1.27), (.8, .73)),
        palette=dict(bamboo=('#6C7446', '#444E2A'), weave=('#C8AE76', '#8A7046'), frame=('#BC9E62', '#8E7A48'), wood_grey=.5,
                     stone=('#6E6C66', '#55534E', '#8A8780'), stone_moss=.55)),
    'H06_RustShingleHouse': dict(
        id='H06', seed=606, PX=1.9, PY=1.85, TAN=.45, roof='gable_y', gables=('F', 'B'), gable_out=.26, cover='shingle', wall='plank',
        front_posts=(0, 1.36, 2.44, 3.8), door_u=(1.36, 2.44), back_posts=(0, 1.9, 3.8), side_posts=(0, 1.23, 2.47, 3.7),
        windows=[dict(wall='Left', bay=1, row=1, kind='bars', snapped=(1,))],
        patches=[dict(wall='Back', bay=1, row=1)],
        holes={'R': blob(1.0, 1.05, 1.0, .8, 1.7, .2)},
        purlin_breaks=[dict(slope='R', level='mid', x=.9, keep='left', fallen='hang', deg=24)],
        door_leaf=('lean', 'L'), bed='left_back', quiver=(.5,), room=((-.8, -1.25), (1.2, .75)),
        palette=dict(shingle=('#6C3828', '#46241A', '#84503C'), shingle_grey=.28, wallboard=('#56483A', '#A08E74'), wood_dark='#3A2C1E', wood_light='#6E5840',
                     stone=('#646A70', '#4C5258', '#7E848A'), stone_moss=.4)),
    'H02_RammedEarthHouse': dict(
        id='H02', seed=202, PX=2.2, PY=1.85, TAN=.4, roof='hip', wall='earth', sill=False, MID=None, FOOT_TOP=.55,
        front_posts=(0, 1.5, 2.7, 4.4), door_u=(1.5, 2.7), back_posts=(0, 1.5, 2.7, 4.4), side_posts=(0, 1.85, 3.7), truss=(0,),
        windows=[dict(wall='Back', bay=1, row=0, kind='bars', z=(1.4, 1.85)),
                 dict(wall='Front', bay=2, row=0, kind='bars', u=(3.2, 3.75), z=(1.4, 1.85))],
        keep={'Back': lambda u: 99 if u < 2.8 else 2.3 - (u - 2.8) * 1.15 + .12 * math.sin(u * 11),
              'Right': lambda u: 99 if u < 1.9 else 2.3 - (u - 1.9) * 1.1 + .12 * math.sin(u * 13)},
        holes={'B': blob(1.75, 1.3, 1.2, 1.05, .4, .2), 'R': blob(1.45, 1.25, 1.1, 1.0, 1.1, .2)},
        rubble=[dict(c=(2.0, 1.62), r=.55, n=30, h=.95, core=True, kinds=('lump', 'lump', 'lump', 'stone')),
                dict(c=(2.42, 1.2), r=.32, n=10, h=.28, kinds=('lump', 'lump', 'stone'))],
        door_leaf=('lean', 'L'), bed='left_back', quiver=(-.3,), room=((-1.1, -1.45), (.9, .55)),
        palette=dict(tile=('#7C4030', '#5A2C1F', '#94563F'), moss=.5, wood_dark='#44382C', wood_light='#86725A', clay=('#B9844E', '#7A5232', .6),
                     stone=('#7A6E62', '#5E554C', '#958A7E'), stone_moss=.35)),
    'H08_SandStonePlasterHouse': dict(
        id='H08', seed=808, PX=2.2, PY=1.85, TAN=.42, roof='hip', wall='stone_daub', FOOT_TOP=1.0, MID=None, cover='shingle',
        front_posts=(0, 1.55, 2.65, 4.4), door_u=(1.55, 2.65), back_posts=(0, 1.47, 2.93, 4.4), side_posts=(0, 1.85, 3.7), truss=(0,),
        windows=[dict(wall='Front', bay=2, row=0, kind='bars', z=(1.45, 1.95)),
                 dict(wall='Left', bay=1, row=0, kind='boarded', z=(1.4, 1.95))],
        holes={'B': lambda x, s: .35 < s < 1.45 - 1.1 * abs(x - .1) + .08 * math.sin(x * 13 + s * 5)},
        sags={'B': lambda x, s: .42 * max(0.0, 1 - abs(x - .1) / 1.5) ** 1.3 * (math.sin(math.pi * min(1.0, s / 2.05)) if s > 0 else 0)},
        purlin_breaks=[dict(slope='B', level='mid', x=.15, keep='left', fallen='hang', deg=30)],
        door_leaf=('lean', 'L'), bed='right_back', quiver=(-1.0,), room=((-1.2, -1.45), (.8, .55)),
        palette=dict(shingle=('#8A7858', '#5E5240', '#A08C6C'), shingle_grey=.5, wood_grey=.5, mud='#857158', lime='#D2C6AA', lime_amt=.36,
                     under=('#7A7872', '#A8987A'), stone=('#6E737A', '#50555C', '#8A8E94'), stone_moss=.3)),
}
