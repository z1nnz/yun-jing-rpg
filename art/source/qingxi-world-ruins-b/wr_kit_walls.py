"""R01 dry-stone wall and R02 bamboo fence (straight, corner, broken / leaning, fence end post).

Chaining rule (both kits): a piece runs along its path coordinate u from its START interface (u = 0) to its
END interface (u = period). Stone and picket layouts are periodic in u, so the end face of one piece and the
start face of the next carry the same stones / rails: chain pieces start-to-end without rotating any by 180°.
Front (-Y) is on the right-hand side of the direction of travel.
"""
import math, random
from mathutils import Vector, Matrix
import wr_core as C
from wr_core import S, T, RZ, RX, RY, xf
import wr_materials as WM

# ---------------------------------------------------------------- R01 dry-stone wall
WALL_L = 3.0
WALL_H = .95
WALL_EMBED = .05            # bottom course sits 5 cm into the terrain
COURSES = [(-WALL_EMBED, .36, (.42, .82)), (.31, .27, (.30, .62)), (.58, .22, (.24, .50))]
COPE_Z = .80                # coping course from here to WALL_H


def thick(z):
    """Battered wall: 0.56 m at the foot, 0.44 m under the coping."""
    return .56 - .12 * max(0., min(1., z / COPE_Z))


def _rows(rr, z0, z1):
    """Course heights from the foot up: big stones low, smaller towards the coping, summing to z1 - z0."""
    hs = []; k = 0
    while True:
        lo, hi = (.24, .34) if k == 0 else ((.17, .26) if k < 2 else (.11, .2))
        hs.append(rr.uniform(lo, hi)); k += 1
        if sum(hs) >= (z1 - z0) - .08: break
    s = (z1 - z0) / sum(hs)
    out = []; z = z0
    for h in hs: out.append((z, h * s)); z += h * s
    return out


def _skin(rr, period, rows, side, recs):
    """One face skin (side -1 front, +1 back): a periodic bond of stones per row. Some stones are two rows tall;
    the row above skips their span. Each stone overlaps its neighbours slightly so no daylight shows."""
    taken = {}                                    # row index -> list of (u0, u1) already covered from below
    for ri, (z0, h) in enumerate(rows):
        u = rr.uniform(0, .5); start = u
        while u < start + period - .05:
            busy = [iv for iv in taken.get(ri, []) if iv[0] - .01 <= (u % period) < iv[1] - .01]
            if busy:
                u += busy[0][1] - (u % period); continue
            L = rr.uniform(1.1, 3.2) * h if ri else rr.uniform(1.4, 2.8) * h
            L = min(L, .85)
            if u + L > start + period - .12: L = start + period - u
            tall = ri + 1 < len(rows) and rr.random() < .14 and L < .55
            hh = h + (rows[ri + 1][1] if tall else 0)
            if tall: taken.setdefault(ri + 1, []).append(((u % period), (u % period) + L))
            zc = z0 + hh / 2
            t = thick(zc)
            sh = rr.uniform(.8, 1.12)
            recs.append(dict(kind='face', u0=u % period - .03, u1=u % period + L + .03, z=zc + (sh - 1) * hh * .3 + rr.uniform(-.015, .015),
                             h=hh * 1.12 * sh, d=t * rr.uniform(.55, .68), v=side * (t / 2 - t * .3) + rr.uniform(-.015, .04) * side,
                             seed=rr.randrange(1 << 30), tilt=rr.uniform(-.1, .1), yaw=rr.uniform(-.07, .07),
                             roll=rr.uniform(-.06, .06), face=side, taper=rr.uniform(-.3, .3), skew=rr.uniform(-.35, .35)))
            # pinning stones wedged in the joint after this stone
            for _ in range(2 if rr.random() < .45 else 1):
                if rr.random() > .92 or h < .1: continue
                s = rr.uniform(.045, .085); cz = z0 + rr.uniform(.2, .8) * h
                recs.append(dict(kind='chink', u0=(u + L) % period - s * .5, u1=(u + L) % period + s * .5, z=cz, h=s * rr.uniform(.6, .85),
                                 d=.1, v=side * (thick(cz) / 2 - .055), seed=rr.randrange(1 << 30),   # flush with the face, seen in the joint
                                 tilt=rr.uniform(-.3, .3), yaw=rr.uniform(-.3, .3), roll=rr.uniform(-.2, .2)))
            u += L


def wall_layout(seed, period=WALL_L):
    """Stone records in path coordinates (u along the wall, v across, z up), periodic in u: two face skins with
    their own bonds, a hearting core between them, and a coping course."""
    rr = random.Random(seed); recs = []
    rows = _rows(rr, -WALL_EMBED, COPE_Z)
    for side in (-1, 1):
        _skin(rr, period, rows, side, recs)
    for a in range(12):                           # hearting: dark rubble core, only seen through deep joints
        for zi, zc in enumerate((.12, .36, .6)):
            uu = a * .25 + (zi % 2) * .12
            recs.append(dict(kind='core', u0=uu - .16, u1=uu + .16, z=zc, h=.28, d=thick(zc) * .62, v=rr.uniform(-.03, .03),
                             seed=rr.randrange(1 << 30), tilt=rr.uniform(-.3, .3), yaw=rr.uniform(-.3, .3), roll=rr.uniform(-.3, .3)))
    u = rr.uniform(0, .3); start = u
    while u < start + period - .05:
        L = rr.uniform(.3, .6)
        if u + L > start + period - .2: L = start + period - u
        hh = rr.uniform(.13, .18)
        recs.append(dict(kind='cope', u0=u % period - .01, u1=u % period + L + .01, z=COPE_Z + hh / 2 - .015, h=hh,
                         d=thick(COPE_Z) * rr.uniform(1.02, 1.14), v=rr.uniform(-.025, .025), seed=rr.randrange(1 << 30),
                         tilt=rr.uniform(-.07, .07), yaw=rr.uniform(-.07, .07), roll=rr.uniform(-.06, .06)))
        u += L
    # periodic copies of stones that run past either end of the period
    for r in list(recs):
        if r['u1'] > period:
            q = dict(r); q['u0'] -= period; q['u1'] -= period; recs.append(q)
        if r['u0'] < 0:
            q = dict(r); q['u0'] += period; q['u1'] += period; recs.append(q)
    return recs


def _stone_params(r):
    if r['kind'] == 'chink': return dict(round_=.62, chips=3, chip_depth=(.05, .15), wobble=.1, sub=2)      # water-worn pebble
    if r['kind'] == 'core': return dict(round_=.4, chips=4, chip_depth=(.05, .15), wobble=.1, sub=1)
    if r['kind'] == 'cope': return dict(round_=.4, chips=7, chip_depth=(.04, .18), wobble=.1, flat_bottom=.85, sub=3, bulge=.1)
    # field stones: weathered round at the arrises, lumpy, a few old frost chips; still laid with a flattish face out
    return dict(round_=.48, chips=6, chip_depth=(.04, .16), wobble=.11, flat_bottom=.8, face=r.get('face'), sub=3,
                taper=r.get('taper', 0) * .6, skew=r.get('skew', 0) * .6, bulge=.12)


def place_stone(name, r, frame, mat, drop=None, detail=0):
    """frame(u) -> (origin, tangent); stone centred at mid-u in that frame. drop: optional extra transform."""
    u = (r['u0'] + r['u1']) / 2; L = r['u1'] - r['u0']
    o, tng = frame(u)
    yaw = math.atan2(tng.y, tng.x)
    M = Matrix.Translation(o) @ RZ(yaw) @ T(0, r['v'], r['z']) @ RZ(r['yaw']) @ RY(r['tilt']) @ RX(r.get('roll', 0))
    if drop is not None: M = drop @ M
    p = dict(_stone_params(r))
    sub = p.pop('sub')
    if r['kind'] == 'core': mat = S.get('core_mat', mat)
    with xf(M):
        o = C.rock(name, (0, 0, 0), (L, r['d'], r['h']), mat, r['seed'], sub=sub, detail=detail, **p)
    o['rand_seed'] = r['seed']
    return o


def straight_frame(x0):
    return lambda u: (Vector((x0 + u, 0, 0)), Vector((1, 0, 0)))


def r01_wall(variant):
    # one grey-green field stone, stone-to-stone variation kept narrow; lichen crusts and moss in the joints
    mat = WM.stone('M_R01_FieldStone', tones=('#666C66', '#535953', '#7C807A'), warm='#7A7262', moss=.8, moss_low=.3, moss_top=.8,
                   lichen=1.0, lichen_cover=.4, rosettes=.6, rosette_scale=9.0, small_rosettes=.7, relief=1.8)
    core = WM.stone('M_R01_Hearting', tones=('#3A403C', '#2E3330', '#454B46'), warm='#3E3A33', moss=.2, lichen=0, ground_dirt=.3)
    S['core_mat'] = core
    S['iface_planes'] = [(i['centre'], i['direction']) for i in WALL_INTERFACES[variant].values()]
    recs = wall_layout(1031)
    parts = []
    if variant == 'Straight':
        for i, r in enumerate(recs):
            s = place_stone(f"Stone_{r['kind']}_{i:03d}", r, straight_frame(-WALL_L / 2), mat, detail=1 if r['kind'] == 'chink' else 0)
            if C.clip_axis(s, 'x', -WALL_L / 2, WALL_L / 2): parts.append(s)
            else: C.drop_part(s)
        C.hull_box('Collision', (0, 0, (WALL_H - WALL_EMBED) / 2), (WALL_L, .58, WALL_H + WALL_EMBED))
    elif variant == 'Collapsed':
        rr = random.Random(77)
        # breach in the middle: upper courses fall out between u 1.05 and 2.1, tumble to the front
        for i, r in enumerate(recs):
            u = (r['u0'] + r['u1']) / 2
            breach = 1.05 < u < 2.15
            if breach and r['kind'] == 'core': r = dict(r, z=.17, h=.42)
            gone = breach and r['kind'] != 'core' and (r['kind'] == 'cope' or r['z'] > .3)
            if not gone:
                s = place_stone(f"Stone_{r['kind']}_{i:03d}", r, straight_frame(-WALL_L / 2), mat, detail=1 if r['kind'] == 'chink' else 0)
                if C.clip_axis(s, 'x', -WALL_L / 2, WALL_L / 2): parts.append(s)
                else: C.drop_part(s)
            elif r['kind'] != 'chink' and rr.random() < .82:
                # fallen stone: same stone, rolled out in front of the breach and resting on the ground
                x = -WALL_L / 2 + u + rr.uniform(-.25, .25)
                y = -rr.uniform(.35, 1.05) * (1.3 if r['kind'] == 'cope' else 1.0)
                rx, ry = rr.uniform(-.5, .5), rr.uniform(-.6, .6)
                lift = min(r['h'], r['d'], r['u1'] - r['u0']) * .38
                q = dict(r); q['v'] = 0; q['z'] = 0; q['tilt'] = 0; q['yaw'] = 0
                drop = Matrix.Translation((x, y, lift - .03)) @ RZ(rr.uniform(0, math.tau)) @ RX(rx) @ RY(ry) @ Matrix.Translation((-(-WALL_L / 2 + u), 0, 0))
                s = place_stone(f"Fallen_{r['kind']}_{i:03d}", q, straight_frame(-WALL_L / 2), mat, drop=drop)
                # settle on the measured underside: 4 cm into the soil, never below the wall's design embed
                s.matrix_world = Matrix.Translation((0, 0, -.04 - min(p.z for p in C.world_points(s)))) @ s.matrix_world
                parts.append(s)
        # loose rubble in the breach
        for k in range(14):
            x = rr.uniform(-.35, .55); y = rr.uniform(-.2, .15); s = rr.uniform(.07, .16)
            parts.append(C.rock(f'Rubble_{k:02d}', (x, y, .3 + rr.uniform(0, .05)), (s * 1.3, s, s * .7), mat, rr.randrange(1 << 30),
                                rot=(rr.uniform(-.5, .5), rr.uniform(-.5, .5), rr.uniform(0, 3)), sub=2, round_=.65, chips=5, wobble=.06, detail=1))
        C.hull_box('Collision_End_A', (-1.05, 0, (WALL_H - WALL_EMBED) / 2), (.9, .58, WALL_H + WALL_EMBED))
        C.hull_box('Collision_End_B', (1.12, 0, (WALL_H - WALL_EMBED) / 2), (.76, .58, WALL_H + WALL_EMBED))
        C.hull_box('Collision_Breach', (.04, 0, .17), (1.24, .58, .44))
    elif variant == 'Corner':
        # unfolded 3 m path: incoming arm along +x (u 0..1.5 - t/2), quoin block, outgoing arm along +y
        half = .29
        def frame(u):
            if u <= WALL_L / 2: return Vector((-WALL_L / 2 + u, 0, 0)), Vector((1, 0, 0))
            return Vector((0, u - WALL_L / 2, 0)), Vector((0, 1, 0))
        for i, r in enumerate(recs):
            det = 1 if r['kind'] == 'chink' else 0
            if r['u0'] < WALL_L / 2 - half and r['u1'] > 0:
                s = place_stone(f"StoneIn_{r['kind']}_{i:03d}", r, straight_frame(-WALL_L / 2), mat, detail=det)
                if C.clip_axis(s, 'x', -WALL_L / 2, -half): parts.append(s)
                else: C.drop_part(s)
            if r['u1'] > WALL_L / 2 + half and r['u0'] < WALL_L:
                s = place_stone(f"StoneOut_{r['kind']}_{i:03d}", r, lambda uu: (Vector((0, uu - WALL_L / 2, 0)), Vector((0, 1, 0))), mat, detail=det)
                if C.clip_axis(s, 'y', half, WALL_L / 2): parts.append(s)
                else: C.drop_part(s)
        # quoins: big squared corner stones, long side alternating between the two arms each course
        rr = random.Random(5)
        zs = [(-WALL_EMBED, .36), (.31, .27), (.58, .22)]
        for k, (z0, h) in enumerate(zs):
            t = thick(z0 + h / 2)
            if k % 2 == 0: c, s = (-.05, 0, z0 + h / 2), (t + .1, t, h * .97)
            else: c, s = (0, .05, z0 + h / 2), (t, t + .1, h * .97)
            parts.append(C.rock(f'Quoin_{k}', c, s, mat, 900 + k, rot=(0, 0, rr.uniform(-.03, .03)), sub=3, round_=.36, chips=6,
                                chip_depth=(.03, .12), wobble=.03, flat_bottom=.75))
        hc = .15
        parts.append(C.rock('Quoin_Cap', (0, 0, COPE_Z + hc / 2 + .005), (thick(COPE_Z) + .08, thick(COPE_Z) + .08, hc), mat, 977,
                            sub=3, round_=.4, chips=7, chip_depth=(.03, .14), wobble=.03, flat_bottom=.75))
        zc, hc_ = (WALL_H - WALL_EMBED) / 2, WALL_H + WALL_EMBED
        C.hull_box('Collision_In', ((-WALL_L / 2 + half) / 2, 0, zc), (WALL_L / 2 + half, .58, hc_))          # x -1.5 .. +0.29
        C.hull_box('Collision_Out', (0, (half + WALL_L / 2) / 2, zc), (.58, WALL_L / 2 - half, hc_))            # y +0.29 .. +1.5
    elif variant == 'EndCap':
        # cheek end: the first 0.22 m of the periodic bond (joins a chain end), then a column of squared
        # quoin stones laid long-and-short across the wall's full thickness, finished on the outer face
        x0, xq = -.25, -.03
        for i, r in enumerate(recs):
            if r['u0'] < xq - x0 and r['u1'] > 0:
                s = place_stone(f"Stone_{r['kind']}_{i:03d}", r, straight_frame(x0), mat, detail=1 if r['kind'] == 'chink' else 0)
                if C.clip_axis(s, 'x', x0, xq + .02): parts.append(s)
                else: C.drop_part(s)
        rows = _rows(random.Random(1031), -WALL_EMBED, COPE_Z)
        rr = random.Random(41)
        for k, (z0, h) in enumerate(rows):
            t = thick(z0 + h / 2)
            ln = .3 if k % 2 == 0 else .2
            s = C.rock(f'Cheek_{k}', (xq + ln / 2 - .01, 0, z0 + h / 2), (ln, t * 1.02, h * 1.06), mat, 700 + k,
                       rot=(rr.uniform(-.03, .03), rr.uniform(-.04, .04), rr.uniform(-.03, .03)), sub=2, round_=.22, chips=7,
                       chip_depth=(.04, .18), wobble=.07, flat_bottom=.85)
            s['rand_seed'] = 700 + k; parts.append(s)
        hc = .16
        s = C.rock('Cheek_Cap', (.05, 0, COPE_Z + hc / 2 - .015), (.42, thick(COPE_Z) * 1.1, hc), mat, 790, sub=2, round_=.24,
                   chips=8, chip_depth=(.04, .2), wobble=.08, flat_bottom=.85)
        s['rand_seed'] = 790; parts.append(s)
        C.hull_box('Collision', (0, 0, (WALL_H - WALL_EMBED) / 2), (.5, .58, WALL_H + WALL_EMBED))
    return parts


WALL_INTERFACES = {
    'EndCap': {'start': {'centre': [-.25, 0, 0], 'direction': [1, 0, 0]}},
    'Straight': {'start': {'centre': [-1.5, 0, 0], 'direction': [1, 0, 0]}, 'end': {'centre': [1.5, 0, 0], 'direction': [1, 0, 0]}},
    'Collapsed': {'start': {'centre': [-1.5, 0, 0], 'direction': [1, 0, 0]}, 'end': {'centre': [1.5, 0, 0], 'direction': [1, 0, 0]}},
    'Corner': {'start': {'centre': [-1.5, 0, 0], 'direction': [1, 0, 0]}, 'end': {'centre': [0, 1.5, 0], 'direction': [0, 1, 0]}},
}
