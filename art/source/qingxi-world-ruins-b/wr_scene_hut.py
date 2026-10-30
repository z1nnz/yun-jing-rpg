"""D3_AbandonedHut: a poor timber-and-daub hut on a rubble footing whose right half of the roof has fallen in.

Layout (Blender, front faces -Y, origin at the footprint centre, ground z = 0, footing stones embedded 5 cm):
  footing 5.1 x 4.1 m (outer faces), 0.36 m thick, top at z 0.5; earthen floor top at z 0.12
  frame post centres at x = +-2.37, y = +-1.87; sill 0.50-0.64, mid rail 1.44-1.56, top plate 2.30-2.44
  door in the front wall between jamb faces x -1.07 and -0.03 (1.04 m), stone threshold top 0.14, lintel 2.17
  gable roof, ridge along x, rafter centre line z = 3.40 - 0.417 |y| (22.6 deg), eaves at y = +-2.1,
  gable overhang to x = +-2.72; tiles intact on the left, the right ~45 % has fallen in.
Interior: a bed frame against the left wall, an empty quiver hanging on the back wall, tally marks cut into
the right door jamb that stop part-way through a group. Wear and repair: a plank patch on the back wall, a
spliced (scarfed) top plate with a pegged splint and lashing, daub fallen off one panel showing the wattle.
"""
import math, random, zlib
import bmesh
from mathutils import Vector, Matrix
import wr_core as C
from wr_core import S, RZ, RX, RY
import wr_materials as WM
from wr_mats import plain

# ---------------------------------------------------------------- dimensions
EMBED = .05
PX, PY = 2.37, 1.87                 # post centre lines
FOOT_T, FOOT_TOP = .36, .50
FLOOR = .12
SILL, MID, PLATE = (.50, .64), (1.44, 1.56), (2.30, 2.44)
DOOR_X = (-1.15, .05)               # door post centres
JAMB = (-1.07, -.03)                # clear opening
THRESH = .14
LINTEL = 2.17
TAN = .417; ANG = math.atan(TAN); CA, SA = math.cos(ANG), math.sin(ANG)
RIDGE_Z = 3.40                      # rafter centre line at y = 0
EAVE_Y = 2.10; S_EAVE = EAVE_Y / CA
GABLE_X = 2.72
RAFTER_R = .045; BOARD_T = .02; OFF_BOARD = RAFTER_R + BOARD_T
TRUSS_X = (-2.37, -.75, .75, 2.37)
LIMIT = (5.5, 4.5, 3.8)


def V(*a): return Vector(a)


# ---------------------------------------------------------------- generic members
def frame_rot(x, up=(0, 0, 1)):
    x = Vector(x).normalized(); u = Vector(up)
    if abs(x.dot(u.normalized())) > .95: u = Vector((0, 1, 0)) if abs(x.y) < .9 else Vector((1, 0, 0))
    y = u.cross(x).normalized(); z = x.cross(y)
    return Matrix((x, y, z)).transposed()


def size_key(tag, mat, L, *dims):
    """UV-instancing key for a straight member: same material and cross-section, length within a 6 % band. Copies
    get the master's baked texels (stretched by at most ~6 % along the grain), so repeated timbers cost atlas once."""
    band = round(math.log(max(L, .01)) / math.log(1.06))
    return 100000 + zlib.crc32(f'{tag}|{mat.name if mat else ""}|{band}|' .encode() + '|'.join(f'{d:.3f}' for d in dims).encode()) % 800000


def beam(name, a, b, w, h, mat, up=(0, 0, 1), bevel=.012, inst=True, **kw):
    """Hewn timber between two points: w across, h along `up`."""
    a, b = Vector(a), Vector(b); d = b - a
    o = C.box(name, (a + b) / 2, (d.length, w, h), mat, bevel=bevel, rot=frame_rot(d, up).to_euler(), grain='x', **kw)
    if inst: o['inst_key'] = size_key('beam', mat, d.length, w, h, bevel)
    return o


def pole(name, a, b, r, mat, verts=10, inst=True, **kw):
    a, b = Vector(a), Vector(b); d = b - a
    q = Vector((0, 0, 1)).rotation_difference(d.normalized())
    o = C.cyl(name, (a + b) / 2, r, d.length, mat, verts=verts, rot=q.to_euler(), **kw)
    if inst: o['inst_key'] = size_key('pole', mat, d.length, r, verts)
    return o


def splinters(name, tip, d, r, mat, rr, n=4):
    """A few sharp slivers standing off a snapped end (tip, pointing along d)."""
    d = Vector(d).normalized(); R = frame_rot(d)
    for k in range(n):
        ang = k * 2.1 + rr.uniform(0, .8)
        off = R @ Vector((0, math.cos(ang) * r * .6, math.sin(ang) * r * .6))
        L = rr.uniform(.04, .11)
        beam(f'{name}_{k}', tip + off - d * .01, tip + off + d * L + R @ Vector((0, rr.uniform(-.01, .01), rr.uniform(-.01, .01))),
             r * .35, r * .22, mat, bevel=0, detail=1)


# ---------------------------------------------------------------- merged shells (roof tiles, shards)
def shell(top, bot, L):
    """Profile (x, z) lists extruded along y over [-L/2, L/2]; returns verts, faces of a closed shell."""
    n = len(top); verts = []
    for y in (-L / 2, L / 2):
        verts += [(x, y, z) for x, z in top] + [(x, y, z) for x, z in bot]
    T0, B0, T1, B1 = 0, n, 2 * n, 3 * n
    f = []
    for i in range(n - 1):
        f.append((T0 + i, T0 + i + 1, T1 + i + 1, T1 + i))
        f.append((B0 + i, B1 + i, B1 + i + 1, B0 + i + 1))
        f.append((T0 + i, B0 + i, B0 + i + 1, T0 + i + 1))
        f.append((T1 + i, T1 + i + 1, B1 + i + 1, B1 + i))
    f.append((T0, T1, B1, B0)); f.append((T0 + n - 1, B0 + n - 1, B1 + n - 1, T1 + n - 1))
    return verts, f


PAN_W, PAN_L, PAN_DEP, PAN_T = .22, .27, .03, .013
COV_R, COV_L, COV_T = .056, .25, .011


def pan_template(w=PAN_W, L=PAN_L):
    xs = [-w / 2 + w * i / 4 for i in range(5)]        # shallow curve: four facets read smooth once shaded
    top = [(x, PAN_DEP * ((2 * x / w) ** 2) - PAN_DEP) for x in xs]
    bot = [(x, z - PAN_T) for x, z in top]
    return shell(top, bot, L)


def cover_template(L=COV_L):
    th = [math.pi * i / 6 for i in range(7)]
    top = [(COV_R * math.cos(t), COV_R * math.sin(t)) for t in th]
    bot = [((COV_R - COV_T) * math.cos(t), (COV_R - COV_T) * math.sin(t) + .002) for t in th]
    return shell(top, bot, L)


def merged(name, template, items, mat, detail=0, kind=0, variants=0, unique=None, grain=None):
    """One mesh object from many transformed copies of a template; per-copy random tone in part_rand.

    With variants > 0 the copies are UV-instanced: each copy not flagged in `unique` gets one of `variants` keys;
    build.py bakes only the first copy of each key ("master") at full density and gives the other copies the
    master's UVs after the bake (face attributes inst_key / inst_tile / inst_f). Unique copies (eave row, verge,
    tiles at a broken edge) keep their own texels."""
    tv, tf = template
    verts, faces, rand, fkey, ftile, ff = [], [], [], [], [], []
    rr = random.Random(zlib.crc32(name.encode()))
    for t, (M, rv) in enumerate(items):
        base = len(verts)
        verts += [tuple(M @ Vector(v)) for v in tv]
        faces += [tuple(base + i for i in f) for f in tf]
        S['inst_counter'] = S.get('inst_counter', 0) + 1
        key = 0 if not variants or (unique and unique[t]) else kind * 1000 + rr.randrange(variants) + 1
        rand += [rv if not key else (key % 1000) / variants] * len(tv)
        fkey += [key] * len(tf); ftile += [S['inst_counter']] * len(tf); ff += list(range(len(tf)))
    if not verts: return None
    o = C.mesh(name, verts, faces, mat, smooth=False, detail=detail, **({'grain': grain} if grain else {}))
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
    at = o.data.attributes.new('part_rand', 'FLOAT', 'POINT'); at.data.foreach_set('value', rand)
    for nm, vals in (('inst_key', fkey), ('inst_tile', ftile), ('inst_f', ff)):
        o.data.attributes.new(nm, 'INT', 'FACE').data.foreach_set('value', vals)
    o['own_rand'] = True
    o.data.set_sharp_from_angle(angle=math.radians(40))
    for p in o.data.polygons: p.use_smooth = True
    return o


# ---------------------------------------------------------------- roof geometry
def slope_frame(sg, x, s, off):
    """sg = -1 front slope, +1 rear slope. Returns origin and the tile frame (X across, Y down-slope, Z out)."""
    d = V(0, sg * CA, -SA); n = V(0, sg * SA, CA); X = V(sg, 0, 0)
    o = V(x, 0, RIDGE_Z) + d * s + n * off
    return o, Matrix((X, d, n)).transposed(), d, n


def edge_front(s):   # x beyond which the front slope has fallen in
    return .45 + .32 * math.sin(2.3 * s + .5) + .14 * math.sin(7.1 * s)


def edge_rear(s):
    return .85 + .3 * math.sin(2.0 * s + 1.7) + .15 * math.sin(6.3 * s + 2.0)


BOARD_L = 1.26      # roof boards are sawn to one length and butt-jointed over a rafter, joints staggered by row


def board_row(name, x0, x1, o0, n, w, mat, k):
    """Boards along x from x0 to x1 at the row centre o0: full-length boards share one baked texture, the cut
    pieces at the ends keep their own."""
    j0 = -GABLE_X + (BOARD_L / 2 if k % 2 else 0)
    cuts = [x0] + [j0 + i * BOARD_L for i in range(-1, 8) if x0 + .05 < j0 + i * BOARD_L < x1 - .05] + [x1]
    for j, (a, b) in enumerate(zip(cuts, cuts[1:])):
        if b - a < .06: continue
        full = abs((b - a) - BOARD_L) < .01
        o = beam(f'{name}_{j}', V(a + .002, o0.y, o0.z), V(b - .002, o0.y, o0.z), w, BOARD_T, mat, up=n, bevel=.003, inst=full)


def roof(wood, poles, tile, board_mat, rope, rr):
    # purlins (round logs) and trusses
    pole('Purlin_Ridge', V(-GABLE_X, 0, RIDGE_Z - RAFTER_R - .08), V(GABLE_X, 0, RIDGE_Z - RAFTER_R - .08), .08, poles, verts=14)
    zmid = RIDGE_Z - TAN * .95 - RAFTER_R - .07
    zw = RIDGE_Z - TAN * PY - RAFTER_R - .07
    for sg, nm in ((-1, 'Front'), (1, 'Rear')):
        pole(f'Purlin_Wall_{nm}', V(-GABLE_X, sg * PY, zw), V(GABLE_X, sg * PY, zw), .07, poles, verts=12)
        if sg == -1:
            # the front middle purlin snapped at x 1.55; its right length dropped and hangs from the gable truss
            pole('Purlin_Mid_Front', V(-GABLE_X, -.95, zmid), V(1.55, -.95, zmid), .07, poles, verts=12)
            splinters('Purlin_Mid_Front_Break', V(1.55, -.95, zmid), (1, 0, 0), .07, poles, rr)
            piv = V(2.37, -.95, zmid); M = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(-24), 4, 'Y') @ Matrix.Translation(-piv)
            a, b = M @ V(1.62, -.95, zmid), M @ V(GABLE_X, -.95, zmid)
            pole('Purlin_Mid_Front_Fallen', a, b, .07, poles, verts=12)
            splinters('Purlin_Mid_Front_Fallen_Break', a, a - b, .07, poles, rr)
        else:
            pole(f'Purlin_Mid_{nm}', V(-GABLE_X, sg * .95, zmid), V(GABLE_X, sg * .95, zmid), .07, poles, verts=12)
    for i, x in enumerate(TRUSS_X):
        beam(f'Truss_{i}_Tie', V(x, -PY - .12, PLATE[1] + .08), V(x, PY + .12, PLATE[1] + .08), .14, .16, wood)
        top = RIDGE_Z - RAFTER_R - .16
        beam(f'Truss_{i}_King', V(x, 0, PLATE[1] + .16), V(x, 0, top), .12, .12, wood, up=(1, 0, 0))
        for sg in (-1, 1):
            if i == 3 and sg == -1:   # the right gable's front strut broke when the purlin dropped
                beam(f'Truss_{i}_Strut_Stub', V(x, -.95, PLATE[1] + .16), V(x, -.95, PLATE[1] + .3), .1, .1, wood, up=(1, 0, 0))
                splinters(f'Truss_{i}_Strut_Break', V(x, -.95, PLATE[1] + .3), (0, 0, 1), .05, wood, rr)
                continue
            beam(f'Truss_{i}_Post_{sg}', V(x, sg * .95, PLATE[1] + .16), V(x, sg * .95, zmid - .07), .1, .1, wood, up=(1, 0, 0))
    # left gable: daub triangle under the rafters, with barge boards on the verge
    zt = PLATE[1] + .16
    gab = [(-PY, zt), (PY, zt), (0, RIDGE_Z - RAFTER_R - .17)]
    C.extrude_profile('Gable_Left_Daub', gab, .1, S['plaster'], plane='yz', p=(-PX, 0, 0), bevel=.01)
    for sg in (-1, 1):
        o0, _, d, n = slope_frame(sg, -GABLE_X - .02, 0, OFF_BOARD + .05)
        beam(f'Barge_{sg}', o0 + d * .02, o0 + d * (S_EAVE + .03), .035, .17, wood, up=n)

    rafters_x = [-2.52 + i * .42 for i in range(13)]
    for sg, nm, edge in ((-1, 'Front', edge_front), (1, 'Rear', edge_rear)):
        emin = min(edge(s / 10) for s in range(0, 25)); emax = max(edge(s / 10) for s in range(0, 25))
        # rafters
        for i, x in enumerate(rafters_x):
            o0, _, d, n = slope_frame(sg, x, -.06, 0)
            if x < emax + .05:            # under tiles somewhere along its length: kept whole
                r_ = pole(f'Rafter_{nm}_{i:02d}', o0, o0 + d * (S_EAVE + .06), RAFTER_R, poles, verts=10)
                r_['inst_key'] = 9000 + (i % 3) + (0 if sg < 0 else 3)     # identical poles share 6 baked variants
                continue
            state = rr.random()
            if state < .38:             # bare but whole
                pole(f'Rafter_{nm}_{i:02d}', o0, o0 + d * (S_EAVE + .06), RAFTER_R, poles, verts=10)
            elif state < .85:           # snapped: a stub at the ridge, the lower length fell inwards off the wall plate
                sb = rr.uniform(.7, 1.4)
                stub_end = o0 + d * sb
                pole(f'Rafter_{nm}_{i:02d}_Stub', o0, stub_end, RAFTER_R, poles, verts=10)
                splinters(f'Rafter_{nm}_{i:02d}_StubBreak', stub_end, d, RAFTER_R, poles, rr)
                piv = o0 + d * (PY / CA + .06)
                best = None
                for sign in (1, -1):
                    M = Matrix.Translation(piv) @ Matrix.Rotation(sign * math.radians(rr.uniform(28, 46)), 4, 'X') @ Matrix.Translation(-piv)
                    a = M @ (o0 + d * (sb + .1))
                    if best is None or a.z < best[0].z: best = (a, M)
                a, M = best
                b = M @ (o0 + d * (S_EAVE + .06))
                pole(f'Rafter_{nm}_{i:02d}_Fallen', a, b, RAFTER_R, poles, verts=10)
                splinters(f'Rafter_{nm}_{i:02d}_FallenBreak', a, a - b, RAFTER_R, poles, rr)
            # else: gone entirely
        # roof boards under the tiles, broken off a little past the tile edge
        k = 0; s = 0.0
        while s < S_EAVE - .01:
            w = min(.2, S_EAVE - s)
            xe = min(GABLE_X, edge(s + w / 2) + rr.uniform(.04, .3))
            o0, R, d, n = slope_frame(sg, 0, s + w / 2, RAFTER_R + BOARD_T / 2)
            board_row(f'Board_{nm}_{k:02d}', -GABLE_X, xe, o0, n, w - .006, board_mat, k)
            k += 1; s += w
        # eave fascia on the intact length
        o0, _, d, n = slope_frame(sg, 0, S_EAVE, RAFTER_R)
        beam(f'Fascia_{nm}', V(-GABLE_X, o0.y, o0.z), V(edge(S_EAVE) + .15, o0.y, o0.z), .03, .1, wood, up=n)
        # tiles: pan columns every 0.26 m, cover tiles over the seams
        pans, covers, caps, loose, pan_u, cov_u = [], [], [], [], [], []
        xs = [-2.6 + i * .26 for i in range(21)]
        for ci, x in enumerate(xs):
            kk = 0; sc = S_EAVE + .05 - PAN_L / 2
            while sc - PAN_L / 2 > .1:
                jitter = rr.uniform(-.06, .06)
                if x + jitter < edge(sc) and rr.random() > .015:
                    o, R, d, n = slope_frame(sg, x + rr.uniform(-.006, .006), sc, OFF_BOARD + PAN_DEP + PAN_T + .002 + kk * .0004)
                    M = Matrix.Translation(o) @ R.to_4x4() @ Matrix.Rotation(math.radians(2.6 + rr.uniform(-.8, .8)), 4, 'X') \
                        @ Matrix.Rotation(rr.uniform(-.03, .03), 4, 'Z')
                    pans.append((M, rr.random()))
                    pan_u.append(kk == 0 or ci in (0, 20) or sc - PAN_L / 2 - .165 < .1 or x + .45 > edge(sc))
                kk += 1; sc -= .165
        for ci, x in enumerate(xs[:-1]):
            xc = x + .13; kk = 0; sc = S_EAVE + .04 - COV_L / 2
            while sc - COV_L / 2 > .12:
                jitter = rr.uniform(-.05, .05)
                if xc + jitter < edge(sc) - .05:
                    slip = .06 if kk > 0 and rr.random() < .03 else 0.0   # a few cover tiles have crept down
                    o, R, d, n = slope_frame(sg, xc + rr.uniform(-.005, .005), sc + slip, OFF_BOARD + PAN_T + .004)
                    M = Matrix.Translation(o) @ R.to_4x4() @ Matrix.Rotation(math.radians(1.6), 4, 'X') @ Matrix.Rotation(rr.uniform(-.025, .025), 4, 'Z')
                    covers.append((M, rr.random()))
                    cov_u.append(kk == 0 or ci in (0, 19) or xc + .4 > edge(sc) - .05 or slip > 0)
                    if kk == 0:
                        caps.append(o + d * (COV_L / 2) + n * .02)
                kk += 1; sc -= .2
        merged(f'Tiles_Pan_{nm}', pan_template(), pans, tile, kind=1 if sg < 0 else 2, variants=16, unique=pan_u)
        merged(f'Tiles_Cover_{nm}', cover_template(), covers, tile, kind=3 if sg < 0 else 4, variants=12, unique=cov_u)
        for j, c in enumerate(caps):     # round eave-end discs (wadang) on the cover tiles
            o, R, d, n = slope_frame(sg, 0, S_EAVE, 0)
            pole(f'Tile_EaveDisc_{nm}_{j:02d}', c - d * .008, c + d * .012, COV_R + .004, tile, verts=14, detail=1)
        # loose tiles that slid onto the bare rafters
        for j in range(2):
            x0 = rafters_x[-1 - 2 * j - (0 if sg < 0 else 1)]; s0 = rr.uniform(.5, 1.0)
            o, R, d, n = slope_frame(sg, x0, s0, RAFTER_R * 2 + PAN_DEP + PAN_T)
            M = Matrix.Translation(o) @ R.to_4x4() @ Matrix.Rotation(rr.uniform(-.25, .25), 4, 'Z') @ Matrix.Rotation(rr.uniform(-.15, .15), 4, 'Y')
            loose.append((M, rr.random()))
        merged(f'Tiles_Loose_{nm}', pan_template(), loose, tile, detail=1)
    # ridge: a mortar-bedded tile ridge on the intact length, broken off above the collapse
    xr = .62
    C.box('Ridge_Body', ((-2.66 + xr) / 2, 0, RIDGE_Z + .11), (xr + 2.66, .3, .16), tile, bevel=.02, grain='x')
    items = []
    x = -2.6
    while x < xr - .1:
        M = Matrix.Translation(V(x + COV_L / 2, 0, RIDGE_Z + .19)) @ Matrix(((0, 1, 0, 0), (-1, 0, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))).transposed() \
            @ Matrix.Rotation(rr.uniform(-.02, .02), 4, 'Z')
        items.append((M, rr.random())); x += COV_L - .03
    merged('Ridge_Covers', cover_template(), items, tile)
    C.tube('Ridge_End_Curl', [(-2.5, 0, RIDGE_Z + .22), (-2.62, 0, RIDGE_Z + .25), (-2.69, 0, RIDGE_Z + .3), (-2.72, 0, RIDGE_Z + .35)],
           .055, tile, radii=[1, .95, .85, .7], res=8)
    for j in range(3):   # ridge tiles that came loose at the break
        x0 = xr + .1 + j * .3
        M = Matrix.Translation(V(x0, rr.uniform(-.25, .25), RIDGE_Z + .05 - j * .03)) @ Matrix.Rotation(rr.uniform(0, 3), 4, 'Z') \
            @ Matrix.Rotation(rr.uniform(-.5, .5), 4, 'X')
        merged(f'Ridge_Loose_{j}', cover_template(), [(M, rr.random())], tile, detail=1)


# ---------------------------------------------------------------- footing, floor, walls
WALLS = {   # origin, along, out, post positions u
    'Front': (V(-PX, -PY, 0), V(1, 0, 0), V(0, -1, 0), (0, 1.22, 2.42, 3.57, 4.74)),
    'Back': (V(-PX, PY, 0), V(1, 0, 0), V(0, 1, 0), (0, 1.57, 3.17, 4.74)),
    'Left': (V(-PX, -PY, 0), V(0, 1, 0), V(-1, 0, 0), (0, 1.87, 3.74)),
    'Right': (V(PX, -PY, 0), V(0, 1, 0), V(1, 0, 0), (0, 1.87, 3.74)),
}
DOOR_U = (1.22, 2.42)


def footing(stone, rr):
    runs = [('Front_L', V(-2.55, -PY, 0), V(1, 0, 0), JAMB[0] + 2.55), ('Front_R', V(JAMB[1], -PY, 0), V(1, 0, 0), 2.55 - JAMB[1]),
            ('Back', V(-2.55, PY, 0), V(1, 0, 0), 5.1),
            ('Left', V(-PX, -PY + FOOT_T / 2, 0), V(0, 1, 0), 2 * PY - FOOT_T), ('Right', V(PX, -PY + FOOT_T / 2, 0), V(0, 1, 0), 2 * PY - FOOT_T)]
    courses = ((-EMBED, .24), (.24, FOOT_TOP))
    k = 0
    for nm, o, d, L in runs:
        yaw = math.atan2(d.y, d.x)
        for ci, (z0, z1) in enumerate(courses):
            u = -rr.uniform(0, .12) if ci else 0.0
            while u < L - .05:
                ln = min(rr.choice((rr.uniform(.18, .3), rr.uniform(.3, .58), rr.uniform(.3, .5))), L - u + .04) if L - u > .2 else L - u + .04
                h = (z1 - z0) * rr.uniform(.82, 1.12)
                c = o + d * (u + ln / 2)
                c.z = (z0 + z1) / 2 + rr.uniform(-.025, .02)
                s = C.rock(f'Footing_{nm}_{k:03d}', c, (ln * 1.04, FOOT_T + rr.uniform(-.01, .04), h), stone, rr.randrange(1 << 30),
                           rot=(rr.uniform(-.03, .03), rr.uniform(-.04, .04), yaw + rr.uniform(-.04, .04)), sub=2,
                           round_=rr.uniform(.18, .32), chips=9, chip_depth=(.06, .22), wobble=.07, flat_bottom=.8,
                           taper=rr.uniform(-.2, .2), skew=rr.uniform(-.12, .12), bulge=.06)
                s['rand_seed'] = rr.randrange(1 << 30)
                if ci == 0: C.clip_axis(s, 'z', -EMBED, None)
                if nm.startswith('Front'):
                    C.clip_axis(s, 'x', -2.55 if nm == 'Front_L' else JAMB[1], JAMB[0] if nm == 'Front_L' else 2.55)
                elif nm == 'Back':
                    C.clip_axis(s, 'x', -2.55, 2.55)
                else:
                    C.clip_axis(s, 'y', -PY + FOOT_T / 2 - .02, PY - FOOT_T / 2 + .02)
                k += 1; u += ln * .94
    # worn threshold slab in the doorway
    C.rock('Threshold_Stone', ((JAMB[0] + JAMB[1]) / 2, -PY - .02, (THRESH - EMBED) / 2), (JAMB[1] - JAMB[0] + .1, FOOT_T + .08, THRESH + EMBED),
           stone, 5521, sub=3, round_=.25, chips=3, chip_depth=(.03, .08), wobble=.03, flat_bottom=.9)
    C.clip_axis(S['parts'][-1], 'z', -EMBED, None)


def wall_point(w, u, z, v=0.0):
    o, d, out, _ = WALLS[w]
    return o + d * u + out * v + V(0, 0, z)


def panel(name, w, u0, u1, z0, z1, mat, t=.12, inset=0.0):
    o, d, out, _ = WALLS[w]
    c = wall_point(w, (u0 + u1) / 2, (z0 + z1) / 2, -inset)
    yaw = math.atan2(d.y, d.x)
    o = C.box(name, c, (u1 - u0, t, z1 - z0), mat, bevel=.008, rot=(0, 0, yaw), grain='x')
    o['inst_key'] = size_key('panel', mat, u1 - u0, t, round(z1 - z0, 2))
    return o


def walls(wood, plaster, wattle, iron, rope, carved, rr):
    for w, (o, d, out, posts) in WALLS.items():
        for i, u in enumerate(posts):
            if w in ('Left', 'Right') and i in (0, len(posts) - 1): continue   # corner posts belong to front / back
            beam(f'Post_{w}_{i}', wall_point(w, u, SILL[0]), wall_point(w, u, PLATE[0]), .16, .16, wood, up=(out.x, out.y, 0))
        L = posts[-1]
        ext = .1 if w in ('Front', 'Back') else -.08
        for nm, (z0, z1) in (('Sill', SILL), ('MidRail', MID)):
            spans = [(0, L)] if w != 'Front' else [(0, DOOR_U[0]), (DOOR_U[1], L)]
            for j, (a, b) in enumerate(spans):
                a2 = a - (ext if a == 0 else -.08); b2 = b + (ext if b == L else -.08)
                beam(f'{nm}_{w}_{j}', wall_point(w, a2, (z0 + z1) / 2), wall_point(w, b2, (z0 + z1) / 2), .14, z1 - z0, wood)
        zc = sum(PLATE) / 2
        if w == 'Front':
            # spliced top plate: the right length was renewed and joined with a long scarf, a pegged splint and lashings
            beam('Plate_Front_A', wall_point(w, -.12, zc), wall_point(w, 3.69, zc), .16, PLATE[1] - PLATE[0], wood)
            beam('Plate_Front_B', wall_point(w, 3.45, zc + .002), wall_point(w, L + .12, zc + .002), .158, PLATE[1] - PLATE[0] - .004,
                 S['wood_new'])
            sp_y = -PY - .08 - .025
            C.box('Plate_Front_Splint', (1.2, sp_y, zc), (.62, .05, .13), S['wood_new'], bevel=.008, grain='x')
            for j, x in enumerate((.98, 1.2, 1.42)):
                pole(f'Plate_Front_Peg_{j}', V(x, sp_y - .04, zc + rr.uniform(-.02, .02)), V(x, -PY + .06, zc), .014, wood, verts=8, detail=1)
            for j, x in enumerate((.93, 1.47)):
                for t in range(4):
                    xx = x + t * .014
                    pts = [(xx, -PY + .085, PLATE[1] + .008), (xx, sp_y - .03, PLATE[1] + .008), (xx + .003, sp_y - .03, PLATE[0] - .008),
                           (xx + .006, -PY + .085, PLATE[0] - .008), (xx + .007, -PY + .085, PLATE[1] + .008)]
                    C.tube(f'Plate_Front_Lash_{j}_{t}', pts, .006, rope, res=4, detail=1)
            # lintel and threshold-side hinge pins on the left jamb
            beam('Door_Lintel', wall_point(w, DOOR_U[0] - .08, (LINTEL + PLATE[0]) / 2), wall_point(w, DOOR_U[1] + .08, (LINTEL + PLATE[0]) / 2),
                 .14, PLATE[0] - LINTEL, wood)
            for j, z in enumerate((.5, 1.7)):
                C.box(f'Hinge_Pin_{j}', (JAMB[0] + .02, -PY - .05, z), (.06, .016, .016), iron, bevel=.003, detail=1)
                pole(f'Hinge_Pintle_{j}', V(JAMB[0] + .045, -PY - .05, z - .05), V(JAMB[0] + .045, -PY - .05, z + .03), .009, iron, verts=8, detail=1)
        else:
            beam(f'Plate_{w}', wall_point(w, -ext if w in ('Front', 'Back') else .08, zc), wall_point(w, L + (ext if w in ('Front', 'Back') else -.08), zc),
                 .16, PLATE[1] - PLATE[0], wood)
        # daub infill
        for i in range(len(posts) - 1):
            a, b = posts[i] + .08, posts[i + 1] - .08
            if w in ('Left', 'Right'):
                a = max(a, .08); b = min(b, posts[-1] - .08)
            if w == 'Front' and (posts[i], posts[i + 1]) == DOOR_U: continue
            for zi, (z0, z1) in enumerate(((SILL[1], MID[0]), (MID[1], PLATE[0]))):
                key = (w, i, zi)
                if key == ('Front', 3, 0):
                    daub_breach(a, b, z0, z1, plaster, wattle, rr)
                elif key == ('Right', 1, 1):
                    window('Right', a, b, z0, z1, (a + .2, b - .2, z0 + .1, z1 - .1), plaster, wood, rr)
                elif key == ('Back', 2, 1):
                    window('Back', a, b, z0, z1, (a + .2, b - .35, z0 + .14, z1 - .12), plaster, wood, rr)
                else:
                    panel(f'Daub_{w}_{i}_{zi}', w, a, b, z0, z1, plaster)
                if key == ('Back', 0, 0):
                    plank_patch(a, b, z0, z1, S['wood_grey'], iron, rr)
    tally(carved)


def daub_breach(a, b, z0, z1, plaster, wattle, rr):
    """Front wall, right bay, lower panel: a bite of daub has fallen out and shows the woven wattle core."""
    x0, x1 = -PX + a, -PX + b
    # ragged bite: an ellipse-ish edge with many small jags so the break reads as crumbled, not cut
    notch = []
    for k in range(19):
        t = k / 18
        ang = math.pi * (-.5 + t)                              # from bottom to top along the left side of the bite
        r = .3 + .05 * math.sin(7 * t) + rr.uniform(-.035, .035)
        notch.append((x1 - .02 - r * math.cos(ang) * 1.0, (z0 + z1) / 2 + .02 + r * 1.25 * math.sin(ang)))
    notch = [(x, min(max(z, z0 + .015), z1 - .03)) for x, z in notch]
    pts = [(x0, z0), (x1, z0), (x1, notch[0][1])] + notch + [(x1, notch[-1][1]), (x1, z1), (x0, z1)]
    C.extrude_profile('Daub_Front_3_0_Broken', pts, .12, plaster, plane='xz', p=(0, -PY, 0), bevel=.008)
    # wattle: upright staves and horizontal withies woven in and out, inside the breach
    staves = [x1 - .08 - k * .14 for k in range(4)]
    for k, x in enumerate(staves):
        pole(f'Wattle_Stave_{k}', V(x, -PY, z0 + .005), V(x, -PY, z1 - .005), .013, wattle, verts=8)
    z = z0 + .05; k = 0
    while z < z1 - .03:
        xs = [x1 - .02] + staves + [x1 - .5]
        pts = [(x, -PY + (.017 if (j + k) % 2 else -.017), z + rr.uniform(-.004, .004)) for j, x in enumerate(xs)]
        C.tube(f'Wattle_Withy_{k:02d}', pts, .009, wattle, res=4)
        z += .055; k += 1
    # fallen lumps of daub at the foot of the wall
    for j in range(5):
        C.rock(f'Daub_Lump_{j}', (x1 - rr.uniform(.05, .45), -PY - rr.uniform(.22, .32), FOOT_TOP * 0 + .03), (rr.uniform(.06, .12), rr.uniform(.05, .09), .045),
               plaster, rr.randrange(1 << 30), rot=(0, 0, rr.uniform(0, 3)), sub=1, round_=.5, chips=3, wobble=.1, detail=1)


def window(w, a, b, z0, z1, hole, plaster, wood, rr):
    h0, h1, v0, v1 = hole
    panel(f'Daub_{w}_Win_L', w, a, h0, z0, z1, plaster); panel(f'Daub_{w}_Win_R', w, h1, b, z0, z1, plaster)
    panel(f'Daub_{w}_Win_B', w, h0, h1, z0, v0, plaster); panel(f'Daub_{w}_Win_T', w, h0, h1, v1, z1, plaster)
    for nm, (p0, p1) in {'Sill': ((h0 - .04, v0), (h1 + .04, v0)), 'Head': ((h0 - .04, v1), (h1 + .04, v1)),
                         'JambA': ((h0, v0), (h0, v1)), 'JambB': ((h1, v0), (h1, v1))}.items():
        beam(f'Win_{w}_{nm}', wall_point(w, p0[0], p0[1]), wall_point(w, p1[0], p1[1]), .14, .05, wood, up=(0, 0, 1) if 'Jamb' not in nm else tuple(WALLS[w][1]))
    n = 5
    for k in range(n):
        u = h0 + (k + 1) * (h1 - h0) / (n + 1)
        if k == 3: continue                                  # one bar is gone
        top = v1 if k != 1 else v0 + (v1 - v0) * .55         # one snapped
        beam(f'Win_{w}_Bar_{k}', wall_point(w, u, v0), wall_point(w, u, top), .03, .03, wood, up=tuple(WALLS[w][1]), bevel=.004)
        if k == 1: splinters(f'Win_{w}_Bar_{k}_Break', wall_point(w, u, top), (0, 0, 1), .02, wood, rr, n=3)


def plank_patch(a, b, z0, z1, wood, iron, rr):
    """Back wall, left bay, lower panel: a hole patched from outside with odd planks nailed to the posts."""
    z = z0 - .02; k = 0
    while z < z1 - .05:
        wdt = rr.uniform(.16, .21)
        u0, u1 = a - .1 + rr.uniform(-.04, .05), b + .1 - rr.uniform(0, .25)
        y = PY + .07 + .014 + k * .002
        tilt = rr.uniform(-.035, .035)
        beam(f'Patch_Plank_{k}', (-PX + u0, y, z + wdt / 2), (-PX + u1, y, z + wdt / 2 + (u1 - u0) * tilt), wdt - .01, .026, wood,
             up=(0, 1, 0), bevel=.006)
        for j, uu in enumerate((u0 + .06, u1 - .06)):
            C.cyl(f'Patch_Nail_{k}_{j}', (-PX + uu, y + .014, z + wdt / 2 + (uu - u0) * tilt), .006, .006, iron, axis='y', verts=8, detail=2)
        z += wdt + rr.uniform(-.01, .02); k += 1


def tally(carved):
    """Tally marks cut into the right door jamb face (x = -0.03, facing the opening): three full gates of five,
    then two strokes, and no more."""
    x = JAMB[1] + .0016          # cut in: only a hair of the pale groove floor stands proud of the face
    rows = [(1.56, 5), (1.44, 5), (1.32, 5), (1.20, 2)]
    for r, (zt, n) in enumerate(rows):
        for k in range(min(n, 4)):
            C.box(f'Tally_{r}_{k}', (x, -PY - .045 + k * .024, zt - .045), (.005, .009, .085), carved, bevel=.001, grain='z', detail=2)
        if n == 5:
            C.box(f'Tally_{r}_Slash', (x, -PY - .009, zt - .045), (.005, .009, .12), carved, bevel=.001, rot=(math.radians(56), 0, 0),
                  grain='z', detail=2)


# ---------------------------------------------------------------- interior and outside
def bed(wood, rr):
    x0, x1, y0, y1, h = -2.24, -1.42, -.12, 1.72, .44
    for j, (x, y) in enumerate(((x0 + .04, y0 + .04), (x1 - .04, y0 + .04), (x0 + .04, y1 - .04), (x1 - .04, y1 - .04))):
        top = h + (.2 if y > 1 else .06)
        beam(f'Bed_Leg_{j}', (x, y, FLOOR), (x, y, FLOOR + top), .07, .07, wood, up=(1, 0, 0), bevel=.008)
    for side, x in (('L', x0 + .04), ('R', x1 - .04)):
        beam(f'Bed_Rail_{side}', (x, y0, FLOOR + h - .05), (x, y1, FLOOR + h - .05), .06, .1, wood)
    for end, y in (('Foot', y0 + .04), ('Head', y1 - .04)):
        beam(f'Bed_End_{end}', (x0, y, FLOOR + h - .05), (x1, y, FLOOR + h - .05), .06, .1, wood)
    beam('Bed_HeadRail', (x0, y1 - .04, FLOOR + h + .17), (x1, y1 - .04, FLOOR + h + .17), .06, .07, wood)
    y = y0 + .12; k = 0
    while y < y1 - .1:
        if k not in (3, 4, 9):                               # three slats missing
            beam(f'Bed_Slat_{k:02d}', (x0 + .02, y, FLOOR + h + .012), (x1 - .02, y + rr.uniform(-.02, .02), FLOOR + h + .012), .085, .022, wood,
                 up=(0, 0, 1), bevel=.004)
        y += .125; k += 1
    # a broken slat lying on the floor beneath
    beam('Bed_Slat_Fallen', (x0 + .1, .5, FLOOR + .012), (x1 - .25, .85, FLOOR + .03), .085, .022, wood, bevel=.004, detail=1)
    C.hull_box('Collision_Bed', ((x0 + x1) / 2, (y0 + y1) / 2, (FLOOR + h + .2) / 2), (x1 - x0, y1 - y0, FLOOR + h + .2))


def quiver(leather, wood, rope):
    """An empty arrow quiver hanging on a peg on the back wall."""
    peg = V(-.8, PY - .08, 1.78)
    pole('Quiver_Peg', peg, peg + V(0, -.13, .02), .016, wood, verts=8)
    prof = [(0, 0), (.046, 0), (.052, .015), (.052, .48), (.06, .5), (.06, .52), (.052, .52), (.045, .5), (.045, .025), (0, .025)]
    base = V(-.66, PY - .135, 1.16)
    M = Matrix.Translation(base) @ Matrix.Rotation(math.radians(-7), 4, 'Y') @ Matrix.Rotation(math.radians(4), 4, 'X')
    with C.xf(M):
        C.lathe('Quiver_Body', prof, (0, 0, 0), leather, seg=20)
        for j, z in enumerate((.1, .4)):
            C.torus(f'Quiver_Band_{j}', (0, 0, z), .054, .007, leather, major=24, minor=6, detail=1)
    top = M @ V(-.05, 0, .5); bot = M @ V(-.05, 0, .1)
    C.tube('Quiver_Strap', [tuple(bot), tuple(bot + V(-.03, .01, .2)), tuple(top + V(-.05, .015, .05)), tuple(peg + V(0, -.1, .03)), tuple(top + V(.06, .0, .02))],
           .008, leather, res=4)


def door_leaf(wood, iron, rr):
    """The door leaf has come off its pins and leans against the wall to the left of the opening."""
    lean = math.atan(.2 / 1.93)
    M = Matrix.Translation(V(-1.76, -2.22, 0)) @ RZ(math.radians(-5)) @ RY(math.radians(2.5)) @ RX(-lean)
    with C.xf(M):
        widths = (.25, .25, .25, .24)
        x = -.495
        for k, w in enumerate(widths):
            z0 = .32 if k == 2 else .0                        # one plank broken off at the foot
            h = 1.93 - rr.uniform(0, .03)
            beam(f'Door_Plank_{k}', (x + w / 2, 0, z0), (x + w / 2, 0, h), w - .006, .035, wood, up=(0, -1, 0), bevel=.006)
            if k == 2: splinters('Door_Plank_Break', V(x + w / 2, 0, z0), (0, 0, -1), .03, wood, rr)
            x += w
        for j, z in enumerate((.25, 1.0, 1.7)):
            beam(f'Door_Batten_{j}', (-.46, .033, z), (.46, .033, z), .1, .03, wood, up=(0, 0, 1), bevel=.006)
        beam('Door_Brace', (-.4, .033, .3), (.4, .033, .95), .09, .028, wood, up=(0, 1, 0), bevel=.006)
        for j, z in enumerate((.25, 1.7)):
            C.box(f'Door_Strap_{j}', (-.2, -.02, z), (.56, .006, .045), iron, bevel=.002, detail=1)
            C.cyl(f'Door_Strap_Eye_{j}', (-.48, -.02, z), .016, .05, iron, axis='z', verts=10, detail=1)
    pts = [M @ V(x, y, z) for x in (-.5, .5) for y in (-.03, .07) for z in (0, 1.95)]
    C.hull('Collision_DoorLeaf', [tuple(p) for p in pts])
    S['door_matrix'] = M


def debris(stone, wood, poles, tile, rr):
    """Under the fallen-in roof: a rafter end on the floor, tile shards, a board."""
    shards = []
    for j in range(16):
        L = rr.uniform(.08, .16)
        M = Matrix.Translation(V(rr.uniform(.95, 2.1), rr.uniform(-1.5, 1.45), FLOOR + .016)) @ RZ(rr.uniform(0, math.tau)) @ RY(rr.uniform(-.25, .25)) \
            @ RX(rr.choice((0, math.pi)) + rr.uniform(-.15, .15))
        shards.append((M @ Matrix.Diagonal((rr.uniform(.4, .8), L / PAN_L, 1, 1)), rr.random()))
    merged('Tile_Shards', pan_template(), shards, tile, detail=1)
    pole('Debris_Rafter', V(1.15, -.2, FLOOR + .045), V(2.15, .55, FLOOR + .3), RAFTER_R, poles, verts=10)
    beam('Debris_Board', V(1.6, -1.2, FLOOR + .01), V(2.18, -.35, FLOOR + .32), .19, BOARD_T, S['board'], up=(0, 0, 1), bevel=.003, detail=1)


def floor(earth):
    """Beaten-earth floor laid as four equal slabs (seams sit under the dust); alternate slabs are turned 180 degrees
    and all four share one baked texture."""
    w, d = (2 * PX - .17) / 2, (2 * PY - .17) / 2
    for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        o = C.box(f'Floor_Earth_{i}', (sx * w / 2, sy * d / 2, (FLOOR - EMBED) / 2), (w + .002, d + .002, FLOOR + EMBED), earth, bevel=.004,
                  rot=(0, 0, math.pi if sx * sy < 0 else 0), grain='x')
        o['inst_key'] = size_key('floor', earth, w, d)


def collision():
    zc, h = (PLATE[1] - EMBED) / 2, PLATE[1] + EMBED
    C.hull_box('Collision_Floor', (0, 0, (FLOOR - EMBED) / 2), (2 * PX - .2, 2 * PY - .2, FLOOR + EMBED))
    C.hull_box('Collision_Wall_FrontL', ((-2.55 + JAMB[0]) / 2, -PY, zc), (JAMB[0] + 2.55, FOOT_T, h))
    C.hull_box('Collision_Wall_FrontR', ((JAMB[1] + 2.55) / 2, -PY, zc), (2.55 - JAMB[1], FOOT_T, h))
    C.hull_box('Collision_Lintel', ((JAMB[0] + JAMB[1]) / 2, -PY, (LINTEL + PLATE[1]) / 2), (JAMB[1] - JAMB[0], FOOT_T, PLATE[1] - LINTEL))
    C.hull_box('Collision_Threshold', ((JAMB[0] + JAMB[1]) / 2, -PY - .02, (THRESH - EMBED) / 2), (JAMB[1] - JAMB[0], FOOT_T + .08, THRESH + EMBED))
    C.hull_box('Collision_Wall_Back', (0, PY, zc), (5.1, FOOT_T, h))
    C.hull_box('Collision_Wall_Left', (-PX, 0, zc), (FOOT_T, 2 * PY - FOOT_T, h))
    C.hull_box('Collision_Wall_Right', (PX, 0, zc), (FOOT_T, 2 * PY - FOOT_T, h))


# ---------------------------------------------------------------- entry
def d3_hut():
    rr = random.Random(3301)
    S['iface_planes'] = []
    wood = WM.aged_wood('M_D3_OldTimber', grey=.45, rough=.8, ring=2.6)
    S['wood_new'] = WM.aged_wood('M_D3_RepairTimber', grey=.12, rough=.74)
    S['wood_grey'] = WM.aged_wood('M_D3_PatchPlank', grey=.75, rough=.82)
    poles = WM.bark('M_D3_RafterPole', slot='Wall', dark='#3B2617', light='#6E6458')
    S['board'] = WM.aged_wood('M_D3_RoofBoard', slot='Roof', grey=.55, rough=.82)
    tile = WM.tile('M_D3_RoofTile', slot='Roof', tones=('#56605E', '#3F4947', '#6B7573'), moss=.7, rough=.62)
    S['plaster'] = plaster = WM.plaster('M_D3_Daub', slot='Wall', mud='#7E6A54', lime='#B8AD98', lime_amt=.42)
    earth = WM.plaster('M_D3_EarthFloor', slot='Roof', mud='#6E5238', lime_amt=0.0)
    stone = WM.stone('M_D3_FootingStone', slot='Stone', moss=.5, lichen=.4, relief=1.8)
    wattle = WM.aged_wood('M_D3_Wattle', slot='Wall', grey=.6, rough=.85)
    rope = WM.rope('M_D3_HempLashing')
    iron = WM.iron('M_D3_Iron')
    carved = plain('M_D3_TallyCut', WM.hexl('#94795A'), 'Main', rough=.85, noise=.25)
    leather = plain('M_D3_Leather', WM.hexl('#4A3020'), 'Main', rough=.7, noise=.3, scale=60.0, bump=.2)
    footing(stone, rr)
    floor(earth)
    walls(wood, plaster, wattle, iron, rope, carved, rr)
    roof(wood, poles, tile, S['board'], rope, rr)
    bed(wood, rr)
    quiver(leather, wood, rope)
    door_leaf(S['wood_grey'], iron, rr)
    debris(stone, wood, poles, tile, rr)
    collision()


# ---------------------------------------------------------------- walk-in checks (run by build.py on the export)
DOOR_BOX = ((JAMB[0] + .06, -2.4, THRESH + .05), (JAMB[1] - .012, -1.5, LINTEL - .02))
ROOM_BOX = ((-1.3, -1.6, FLOOR + .05), (.7, .4, 1.95))


def _verts_in(o, box):
    (x0, y0, z0), (x1, y1, z1) = box
    M = o.matrix_world
    return sum(1 for v in o.data.vertices if x0 < (M @ v.co).x < x1 and y0 < (M @ v.co).y < y1 and z0 < (M @ v.co).z < z1)


def _hull_hits(colls, box):
    (x0, y0, z0), (x1, y1, z1) = box; hits = []
    for c in colls:
        ws = [c.matrix_world @ v.co for v in c.data.vertices]
        lo = Vector((min(w.x for w in ws), min(w.y for w in ws), min(w.z for w in ws)))
        hi = Vector((max(w.x for w in ws), max(w.y for w in ws), max(w.z for w in ws)))
        if lo.x < x1 and hi.x > x0 and lo.y < y1 and hi.y > y0 and lo.z < z1 and hi.z > z0: hits.append(c.name)
    return hits


def hut_checks(lods, colls, S):
    door_w = JAMB[1] - JAMB[0]; door_h = LINTEL - THRESH
    return {
        'door_clear_at_least_0p9_x_1p9': door_w >= .9 and door_h >= 1.9,
        'door_passage_free_of_geometry': _verts_in(lods[0], DOOR_BOX) == 0,
        'door_passage_free_of_collision': not [h for h in _hull_hits(colls, DOOR_BOX) if 'Floor' not in h and 'Threshold' not in h],
        'interior_2x2_free_of_geometry': _verts_in(lods[0], ROOM_BOX) == 0,
        'interior_2x2_free_of_collision': not [h for h in _hull_hits(colls, ROOM_BOX) if 'Floor' not in h],
    }
