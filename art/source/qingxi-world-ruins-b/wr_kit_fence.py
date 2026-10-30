"""R02 bamboo fence: straight 2 m, corner, leaning (broken) section, end post.

Chaining as for R01 (see wr_kit_walls.py): each piece owns the post at its START interface; the next piece's
start post stands at this piece's END interface, so a run is closed with R02_BambooFence_EndPost.
Rails pass on the front (-Y, right of travel) side of the posts; pickets stand behind the rails and are tied to
each rail with an X lashing of hemp cord; rails are bound to the posts with tight coils.
"""
import math, random
from mathutils import Vector, Matrix
import wr_core as C
from wr_core import S
import wr_materials as WM

FENCE_L = 2.0
POST_R, POST_H, POST_EMBED = .052, 1.16, .2
RAIL_R, RAIL_Z = .03, (.24, .9)
PICK_R = (.019, .024)
PICK_EMBED = .08
FENCE_EMBED = POST_EMBED


def _lash_x(name, centre, along, across, r1, r2, mat, detail=1, cord=.006, passes=1, span_k=1.45):
    """X lashing where a picket (axis `along`) crosses a rail (axis `across`): two diagonal loops of cord."""
    a = Vector(along).normalized(); b = Vector(across).normalized(); n = a.cross(b).normalized()
    depth = r1 + r2 + .006                     # half-depth of the rail + picket stack along n
    span = max(r1, r2) * span_k + .004         # half-length of each diagonal pass
    out = []
    for k, sgn in enumerate([1, -1] * passes):
        grow = 1 + .9 * cord * (k // 2) / max(r1, r2)      # later passes lie over the earlier ones
        d1 = (a + sgn * b).normalized()
        pts = []
        for i in range(25):
            t = i / 24 * math.tau
            c, s_ = math.cos(t), math.sin(t)
            # superellipse: the cord hugs the stack, flat across the front and back faces
            cn = math.copysign(abs(c) ** .45, c); sd = math.copysign(abs(s_) ** .45, s_)
            pts.append(tuple(Vector(centre) + n * cn * depth * grow + d1 * sd * span))
        out.append(C.tube(f'{name}_{k}', pts, cord, mat, res=4, detail=detail))
    return out


def _coil(name, base, axis, radius, z0, z1, turns, mat, cord=.0085, detail=0):
    """Tight helical binding around a post (axis), from z0 to z1 along it."""
    ax = Vector(axis).normalized(); h = Vector((1, 0, 0)) if abs(ax.x) < .9 else Vector((0, 1, 0))
    u = ax.cross(h).normalized(); v = ax.cross(u)
    n = int(turns * 14); pts = []
    for i in range(n + 1):
        t = i / n; ang = t * turns * math.tau
        pts.append(tuple(Vector(base) + ax * (z0 + (z1 - z0) * t) + (u * math.cos(ang) + v * math.sin(ang)) * (radius + cord)))
    return C.tube(name, pts, cord, mat, res=4, detail=detail)


def _post_bind(name, base, axis, tangent, rmat, z_half=.045, turns=5):
    """Rail-to-post binding: a tight coil round the post and a doubled X of cord over the rail."""
    out = []
    ax = Vector(axis).normalized()
    for zr in RAIL_Z:
        out.append(_coil(f'{name}_{int(zr * 100)}', base, ax, POST_R, zr - z_half, zr + z_half, turns, rmat))
        front = Vector((tangent[1], -tangent[0], 0))
        c = Vector(base) + ax * zr + front * (POST_R + RAIL_R - .004) * .5
        out += _lash_x(f'{name}_X_{int(zr * 100)}', c, ax, Vector(tangent), RAIL_R, POST_R, rmat, cord=.0075, passes=2, span_k=.95)
    return out


def _post(name, x, y, bmat, seed, lean=(0, 0)):
    base = Vector((x, y, -POST_EMBED))
    d = Vector((math.sin(lean[0]), math.sin(lean[1]), 1)).normalized()
    p = C.culm(name, base, d, POST_H + POST_EMBED, POST_R, bmat, seed, seg=16, node_gap=(.26, .34))
    p['rand_seed'] = seed
    return p, d


def _run(prefix, frame, u0, u1, bmat, rmat, rr, panel=None, missing=(), broken=(), rail_ext=(.07, .07)):
    """Rails and pickets along path coordinate u0..u1; frame(u) -> (origin, tangent). panel: extra transform (leaning)."""
    parts = []
    def P(u, v, z):
        o, t = frame(u); front = Vector((t.y, -t.x, 0))       # right of travel = front
        return o + front * v + Vector((0, 0, z))
    rail_v = POST_R + RAIL_R - .004
    pick_v = rail_v - RAIL_R - PICK_R[1] + .003
    M = panel or Matrix.Identity(4); M3 = M.to_3x3()
    for k, zr in enumerate(RAIL_Z):
        a = M @ P(u0 - rail_ext[0], rail_v, zr + rr.uniform(-.01, .01)); b = M @ P(u1 + rail_ext[1], rail_v, zr + rr.uniform(-.01, .01))
        parts.append(C.culm(f'{prefix}Rail_{k}', a, b - a, (b - a).length, RAIL_R, bmat, rr.randrange(1 << 30), seg=12, taper=.9))
    n = int(round((u1 - u0 - .14) / .112))
    for i in range(n):
        if i in missing: continue
        u = u0 + .07 + (i + .5) * (u1 - u0 - .14) / n + rr.uniform(-.008, .008)
        r = rr.uniform(*PICK_R)
        top = rr.uniform(.45, .62) if i in broken else rr.uniform(.97, 1.04)
        lean = Vector((rr.uniform(-.025, .025), rr.uniform(-.015, .015), 0))
        base = M @ P(u, pick_v, -PICK_EMBED)
        d = (M3 @ (Vector((0, 0, 1)) + lean)).normalized()
        parts.append(C.culm(f'{prefix}Picket_{i:02d}', base, d, top + PICK_EMBED, r, bmat, rr.randrange(1 << 30), seg=10,
                            node_gap=(.22, .32), open_top=i not in broken))
        if i in broken:                                        # snapped top: a few splinters standing off the break
            tip = base + d * (top + PICK_EMBED)
            for s in range(4):
                ang = s * 1.6 + rr.uniform(0, .6)
                off = Vector((math.cos(ang), math.sin(ang), 0)) * r * .75
                parts.append(C.box(f'{prefix}Splinter_{i}_{s}', tip + off + d * .035, (.007, .004, .06 + rr.uniform(0, .06)), bmat,
                                   bevel=0, rot=(rr.uniform(-.2, .2), rr.uniform(-.2, .2), ang), grain='z', detail=1))
        _, t = frame(u)
        for zr in RAIL_Z:
            if zr > top - .03: continue
            c = M @ P(u, (rail_v + pick_v) / 2, zr)
            parts += _lash_x(f'{prefix}Lash_{i:02d}_{int(zr * 100)}', c, M3 @ Vector((0, 0, 1)), M3 @ t, RAIL_R, r, rmat)
    return parts


def straight_frame(x0):
    return lambda u: (Vector((x0 + u, 0, 0)), Vector((1, 0, 0)))


def r02_fence(variant):
    bmat = WM.bamboo('M_R02_DriedBamboo', fresh=.55, grey=.55, rough=.72, straw='#9C9566', olive='#7A7A4C'); rmat = WM.rope('M_R02_HempCord', base='#B39A6C')
    rr = random.Random(2002 + len(variant))
    S['iface_planes'] = []
    zc, hc = (POST_H - POST_EMBED) / 2, POST_H + POST_EMBED
    if variant == 'Straight':
        _post('Post_Start', -FENCE_L / 2, 0, bmat, 5101)
        _post_bind('Bind', (-FENCE_L / 2, 0, 0), (0, 0, 1), (1, 0, 0), rmat)
        _run('', straight_frame(-FENCE_L / 2), 0, FENCE_L, bmat, rmat, rr)
        C.hull_box('Collision', (0, -.02, zc), (FENCE_L + .1, .16, hc))
    elif variant == 'EndPost':
        _post('Post', 0, 0, bmat, 5101)
        _post_bind('Bind', (0, 0, 0), (0, 0, 1), (1, 0, 0), rmat)
        C.hull_box('Collision', (0, 0, zc), (.14, .14, hc))
    elif variant == 'Corner':
        _post('Post_Start', -1.0, 0, bmat, 5101)
        _post('Post_Corner', 0, 0, bmat, 5133)
        _post_bind('BindS', (-1.0, 0, 0), (0, 0, 1), (1, 0, 0), rmat)
        _post_bind('BindC', (0, 0, 0), (0, 0, 1), (1, 0, 0), rmat, z_half=.07, turns=7)
        # the incoming rails run on past the corner post; the outgoing rails butt against their side (no pipe-elbow join)
        rv = POST_R + RAIL_R - .004
        _run('In', straight_frame(-1.0), 0, 1.0, bmat, rmat, rr, rail_ext=(.07, rv + RAIL_R + .08))
        _run('Out', lambda u: (Vector((0, u, 0)), Vector((0, 1, 0))), 0, 1.0, bmat, rmat, rr, rail_ext=(rv - RAIL_R - .002, .07))
        C.hull_box('Collision_In', (-.5, -.02, zc), (1.1, .16, hc))
        C.hull_box('Collision_Out', (.02, .5, zc), (.16, 1.1, hc))
    elif variant == 'Leaning':
        # the panel came loose from the next post and leans forward, hinged on its start post, which is pushed over too
        _post('Post_Start', -FENCE_L / 2, 0, bmat, 5101, lean=(0, -.12))
        hinge = Vector((-FENCE_L / 2, 0, 0))
        M = Matrix.Translation(hinge) @ Matrix.Rotation(math.radians(9), 4, 'Z') @ Matrix.Rotation(math.radians(-24), 4, 'X') @ Matrix.Translation(-hinge)
        _post_bind('Bind', (-FENCE_L / 2, 0, 0), Vector((0, -.12, 1)).normalized(), (1, 0, 0), rmat)
        _run('', straight_frame(-FENCE_L / 2), 0, FENCE_L, bmat, rmat, rr, panel=M, missing=(11,), broken=(4, 13))
        # the missing picket lies in the grass in front; frayed cord ends hang from the loose rail ends
        C.culm('Fallen_Picket', (.1, -.95, PICK_R[1] * .8), (1, -.22, 0), 1.0, PICK_R[1], bmat, 6611, seg=10)
        for k, zr in enumerate(RAIL_Z):
            e = M @ Vector((FENCE_L / 2 + .05, -(POST_R + RAIL_R), zr))
            pts = [tuple(e), tuple(e + Vector((.02, -.01, -.06))), tuple(e + Vector((.015, -.02, -.13 - k * .04))),
                   tuple(e + Vector((.03, -.015, -.2 - k * .05)))]
            C.tube(f'Frayed_Cord_{k}', pts, .005, rmat, res=4, detail=1)
        pts = [M @ Vector((x, y, z)) for x in (-FENCE_L / 2, FENCE_L / 2 + .07) for y in (-.12, .04) for z in (0, 1.05)]
        C.hull('Collision', [tuple(p) for p in pts])


FENCE_INTERFACES = {
    'Straight': {'start': {'centre': [-1.0, 0, 0], 'direction': [1, 0, 0]}, 'end': {'centre': [1.0, 0, 0], 'direction': [1, 0, 0]}},
    'Leaning': {'start': {'centre': [-1.0, 0, 0], 'direction': [1, 0, 0]}, 'end': {'centre': [1.0, 0, 0], 'direction': [1, 0, 0]}},
    'Corner': {'start': {'centre': [-1.0, 0, 0], 'direction': [1, 0, 0]}, 'end': {'centre': [0, 1.0, 0], 'direction': [0, 1, 0]}},
    'EndPost': {'start': {'centre': [0, 0, 0], 'direction': [1, 0, 0]}},
}
