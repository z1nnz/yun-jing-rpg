"""A2 overturned cart for qingxi-world-ruins-b: a small two-wheeled plank cargo cart, built upright and then
tipped over as one rigid body onto its stable side; the down-side wheel has come off and leans against the
tail, the other stays on the axle; two grain sacks tumbled out of the open bed, one torn and spilling.

Blender Z-up, 1 unit = 1 m, origin at the footprint centre, z = 0 at ground level.
The AI reference (v002, reviewed at 81) is not geometrically consistent between its views; this model
follows its parts list but takes its pose from the rigid-body tip computed below.
"""
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix, noise
import wr_core as C
from wr_core import S
import wr_materials as WM
import wr_props as P

LIMIT = (3.6, 2.2, 1.6)
EMBED = 0.0
WHEEL_R = .5
BED_L, BED_W, FLOOR_Z, SIDE_H = 1.9, 1.1, .64, .42
RAIL_Y = .36
AXLE_Z, AXLE_X, AXLE_HALF = WHEEL_R, -.05, .76


def _felloe_seg(name, am, half, ri, ro, w, mat, n=8):
    """One felloe arc centred on angle am (in the wheel's xz plane), grain along its chord, small joint gap."""
    bm = bmesh.new(); rings = []
    for i in range(n + 1):
        f = -half + 2 * half * i / n
        d = Vector((math.sin(f), 0, math.cos(f)))
        rings.append([bm.verts.new(d * r + Vector((0, y, 0))) for r, y in ((ri, -w), (ro, -w), (ro, w), (ri, w))])
    for a, b in zip(rings, rings[1:]):
        for j in range(4):
            bm.faces.new((a[j], a[(j + 1) % 4], b[(j + 1) % 4], b[j]))
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); C._uv_box(me)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    o.rotation_euler = (0, math.pi / 2 - am, 0)
    o = C.finish(o, name, mat, grain='x', bevel=.005, seg=2)
    return o


def _wheel(tag, wood, iron, M):
    """Spoked wheel, axis along local Y, centre at the origin of frame M: hub, 10 spokes, felloe, iron tyre."""
    parts = []
    with C.xf(M):
        parts.append(C.cyl(f'{tag}_Hub', (0, 0, 0), .09, .24, wood, axis='y', verts=16, grain='y'))
        parts.append(C.cyl(f'{tag}_Hub_Band', (0, 0, 0), .095, .05, iron, axis='y', verts=16, grain='y'))
        for k in range(10):
            a = k * math.tau / 10
            d = Vector((math.cos(a), 0, math.sin(a)))
            c = d * (.09 + (WHEEL_R - .08 - .09) / 2)
            parts.append(C.box(f'{tag}_Spoke_{k}', tuple(c), (WHEEL_R - .17 + .02, .045, .035), wood, bevel=.006,
                               rot=(0, -a, 0), grain='x'))
        for k in range(5):                          # five felloes, each carrying two spokes, butted with a hairline gap
            parts.append(_felloe_seg(f'{tag}_Felloe_{k}', (k + .5) * math.tau / 5 + math.tau / 20, math.tau / 10 - .006,
                                     WHEEL_R - .085, WHEEL_R - .012, .035, wood))
        with C.xf(C.RX(math.pi / 2)):
            parts.append(C.lathe(f'{tag}_Tyre', [(WHEEL_R - .013, -.03), (WHEEL_R, -.03), (WHEEL_R, .03), (WHEEL_R - .013, .03),
                                                 (WHEEL_R - .013, -.03)], (0, 0, 0), iron, seg=40, grain='z'))
    return parts


def _cart(wood, plank, iron, rr):
    """The cart upright, in its own frame: x along the shafts (forward +x), y across, z up."""
    parts = []
    x0, x1 = -BED_L / 2, BED_L / 2
    # chassis rails running on into the draw shafts, and three cross bearers
    for k, s in enumerate((-1, 1)):
        parts.append(C.box(f'Rail_{k}', ((x0 + x1) / 2 - .02, s * RAIL_Y, FLOOR_Z - .07), (BED_L + .04, .09, .1), wood, bevel=.01, grain='x'))
        sh = [(x1 - .05 + t * 1.25, s * (RAIL_Y - t * .08), FLOOR_Z - .07 + .05 * t) for t in (0, .35, .7, 1.0)]
        parts.append(C.tube(f'Shaft_{k}', sh, .042, wood, radii=[1.0, .92, .84, .78], res=8, grain='x'))
        parts.append(C.cyl(f'Shaft_Ferrule_{k}', sh[-1], .036, .05, iron, axis='x', verts=12, grain='x'))
    for k, x in enumerate((x0 + .08, AXLE_X, x1 - .08)):
        parts.append(C.box(f'Bearer_{k}', (x, 0, FLOOR_Z - .135), (.09, 2 * RAIL_Y + .12, .07), wood, bevel=.008, grain='y'))
    # axle block and axle
    parts.append(C.box('Axle_Block', (AXLE_X, 0, AXLE_Z + .08), (.14, 2 * RAIL_Y + .1, .1), wood, bevel=.01, grain='y'))
    parts.append(C.cyl('Axle', (AXLE_X, 0, AXLE_Z), .045, 2 * AXLE_HALF, wood, axis='y', verts=12, grain='y'))
    # floor planks
    n = 6; pw = BED_W / n
    for k in range(n):
        parts.append(C.box(f'Floor_{k}', (0, -BED_W / 2 + pw * (k + .5), FLOOR_Z), (BED_L, pw - .006, .035), plank, bevel=.004,
                           rot=(0, 0, rr.uniform(-.003, .003)), grain='x'))
    # sides: three planks per side, stakes and iron straps; ends: two planks
    for k, s in enumerate((-1, 1)):
        for j in range(3):
            z = FLOOR_Z + .03 + .07 + j * .135
            parts.append(C.box(f'Side_{k}_{j}', (0, s * (BED_W / 2 + .015), z), (BED_L, .03, .125), plank, bevel=.004,
                               rot=(rr.uniform(-.004, .004), 0, 0), grain='x'))
        for j, x in enumerate((x0 + .03, -.32, .32, x1 - .03)):
            parts.append(C.box(f'Stake_{k}_{j}', (x, s * (BED_W / 2 + .05), FLOOR_Z + SIDE_H / 2 - .02), (.06, .05, SIDE_H + .12), wood, bevel=.008,
                               grain='z'))
            if j in (1, 2):
                parts.append(C.box(f'Strap_{k}_{j}', (x, s * (BED_W / 2 + .077), FLOOR_Z + SIDE_H / 2 - .02), (.045, .006, SIDE_H + .04), iron,
                                   bevel=.002, grain='z'))
    for k, x in enumerate((x0 - .015, x1 + .015)):
        for j in range(2):
            parts.append(C.box(f'End_{k}_{j}', (x, 0, FLOOR_Z + .1 + j * .17), (.03, BED_W, .16), plank, bevel=.004, grain='y'))
    # an old repair: a cracked side plank held by a nailed iron strap
    parts.append(C.box('Repair_Strap', (-.62, -(BED_W / 2 + .032), FLOOR_Z + .24), (.05, .005, .28), iron, bevel=.002, rot=(0, .2, 0), grain='z'))
    # wheels: the +y wheel stays on the axle, the -y one is built separately and leans on the tail
    parts += _wheel('Wheel_On', wood, iron, C.T(AXLE_X, AXLE_HALF - .08, AXLE_Z))
    parts.append(C.cyl('Linch_Pin', (AXLE_X, AXLE_HALF + .02, AXLE_Z), .012, .06, iron, axis='z', verts=8, grain='z'))
    return parts


def _tip(parts):
    """Rigid-body rest pose for a tip about the long axis: the convex hull of the cart in the (y, z) plane;
    of the hull edges that carry the centre of mass, take the one reached by rolling the cart over towards -y.
    Returns the rotation angle about +x and the vertical offset that puts that edge on the ground."""
    pts = [p for o in parts for p in C.world_points(o)]
    com = sum(pts, Vector()) / len(pts)
    yz = sorted({(round(p.y, 4), round(p.z, 4)) for p in pts})
    def cross(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for q in yz:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], q) <= 0: lo.pop()
        lo.append(q)
    for q in reversed(yz):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], q) <= 0: hi.pop()
        hi.append(q)
    hullp = lo[:-1] + hi[:-1]
    best = None
    for i in range(len(hullp)):
        a, b = Vector(hullp[i]), Vector(hullp[(i + 1) % len(hullp)])
        e = b - a
        if e.length < .05: continue
        nrm = Vector((e.y, -e.x)).normalized()                       # outward normal of a counter-clockwise hull
        ang = -math.pi / 2 - math.atan2(nrm.y, nrm.x)                # rotation about x that turns nrm to (0, -1)
        ang = (ang + math.pi) % math.tau - math.pi
        c = Vector((com.y, com.z))
        t = (c - a).dot(e) / e.length_squared
        if not (.08 < t < .92) or ang < .3: continue                 # unstable edge, or not a roll towards -y
        # overturned, not just leaning: of the stable edges, the one that lays the cart nearest on its side
        if best is None or abs(ang - math.pi / 2) < abs(best[0] - math.pi / 2): best = (ang, a)
    ang, a = best
    R = Matrix.Rotation(ang, 4, 'X')
    zmin = min((R @ p).z for p in pts)
    return R, zmin


def _sack(name, p, size, rot, mat, seed, open_end=False):
    bm = C.rock_mesh(size, seed, sub=10, round_=.62, chips=0, wobble=.12, flat_bottom=.55)
    rr = random.Random(seed)
    for v in bm.verts:                              # slumped: the top sags, the cloth creases a little
        v.co.z -= .25 * size[2] * max(0, v.co.z / (size[2] / 2)) ** 2 * (.6 + .4 * abs(v.co.x) / (size[0] / 2))
    if open_end:                                    # the torn end gapes: pull the -x end open and down
        for v in bm.verts:
            if v.co.x < -size[0] * .3:
                v.co.z *= .7; v.co.y *= 1.12
    else:                                           # the tied end is gathered into a neck
        h = size[0] / 2
        for v in bm.verts:
            if v.co.x > h * .45:
                f = min(1.0, (v.co.x - h * .45) / (h * .55))
                v.co.y *= 1 - .62 * f ** 1.4; v.co.z = v.co.z * (1 - .55 * f ** 1.4) + .25 * size[2] * f * .3
                v.co.x += .04 * f
    # the sewn bottom end keeps two corner ears where the seam meets the fold
    hx0 = size[0] / 2; bot = 1 if open_end else -1
    for v in bm.verts:
        f = max(0.0, bot * v.co.x / hx0 - .55) / .45
        if f > 0:
            e = abs(v.co.y) / (size[1] / 2)
            v.co.x += bot * .05 * f * e ** 3; v.co.y *= 1 + .12 * f * e ** 2; v.co.z *= 1 - .35 * f
    # cloth over loose grain: lumpy fill, long slump creases down the sides, pleats gathered towards the neck
    off = Vector((rr.uniform(-50, 50), rr.uniform(-50, 50), rr.uniform(-50, 50)))
    hx = size[0] / 2
    for v in bm.verts:
        co = v.co.copy()
        rad = Vector((0, co.y, co.z)); rl = rad.length
        if rl < 1e-5: continue
        rad /= rl
        th = math.atan2(co.z, co.y)
        u = co.x / hx                                   # -1 .. 1 along the sack
        lump = noise.noise(co * 7.0 + off) * .022
        crease = noise.noise(Vector((u * 1.6, th * 1.3, 0)) + off)
        crease = -.024 * max(0.0, 1 - abs(crease) * 5) ** 2  # thin sunken folds where the field crosses zero
        g = max(0.0, u - .1) / .9 if not open_end else max(0.0, -u - .3) / .7
        pleat = .018 * g * math.sin(th * 11 + noise.noise(co * 4 + off) * 2)
        top = max(0.0, co.z) / (size[2] / 2)
        v.co += rad * (lump + crease * (.4 + .6 * top) + pleat)
    o = P._bm_part(name, bm, mat, sharp=89, grain='x')
    o.location = p; o.rotation_euler = rot
    o.matrix_world = S['M'][-1] @ o.matrix_basis
    return o


def a2_cart():
    wood = WM.aged_wood('M_A2_OldTimber', grey=.5, rough=.8, ring=2.6)
    plank = WM.aged_wood('M_A2_Plank', grey=.62, rough=.82, ring=2.2)
    iron = WM.iron('M_A2_Iron')
    sack = WM.cloth('M_A2_Burlap', WM.hexl('#7A6848'), 'Sack', weave=110.0, rough=.95, sheen=.2, dirt=.9, coarse=.4)
    grain = WM.grain('M_A2_Grain', slot='Sack')
    rope = WM.rope('M_A2_Cord', slot='Sack', base='#7A6544')
    rr = random.Random(6100)

    parts = _cart(wood, plank, iron, rr)
    R, zmin = _tip(parts)
    M = C.T(.12, .05, -zmin + .004) @ R
    for o in parts: o.matrix_world = M @ o.matrix_world
    bpy.context.view_layer.update()
    # where the tipped bed's open mouth and tail ended up
    mouth = M @ Vector((0, 0, FLOOR_Z + SIDE_H))
    tail_x = min(p.x for o in parts for p in C.world_points(o) if not o.name.startswith('Wheel'))

    # the detached wheel stands on its rim behind the tail, its hub resting against the end planks
    t = .2
    xb = tail_x - .12 * math.cos(t) - .012
    loose = _wheel('Wheel_Off', wood, iron, C.T(xb, -.2, WHEEL_R * math.cos(t) + .035 * math.sin(t) + .002) @ C.RZ(math.pi / 2) @ C.RX(t))

    # sacks tumbled out of the bed's mouth onto the ground; the torn one spills its grain
    side = 1 if mouth.y > 0 else -1
    sk = [((-.35, side * .8, .17), (.72, .44, .34), (0, 0, .4), False),
          ((.38, side * .84, .15), (.7, .42, .3), (0, 0, -.25), True)]
    sacks = []
    for k, (p, sz, rot, torn) in enumerate(sk):
        p = (p[0], p[1] + side * .12, p[2] + .05)      # dropped just clear of the bed, then let fall against it
        sacks.append(_sack(f'Sack_{k}', p, sz, rot, sack, 6200 + k, open_end=torn))
    bpy.context.view_layer.update()
    P._rigid_settle(sacks, frames=60, friction=.9, passive=[o for o in parts + loose if o.type == 'MESH'])
    # neck ties
    for k, o in enumerate(sacks):
        if k == 1: continue
        # round the gathered neck: a loop traced over the sack's own cross-section there, so it hugs the cloth
        xs = .29
        ring = [v.co for v in o.data.vertices if abs(v.co.x - xs) < .025]
        cy = sum(q.y for q in ring) / len(ring); cz = sum(q.z for q in ring) / len(ring)
        loop = []
        for i in range(17):
            th = i / 16 * math.tau
            d = Vector((0, math.cos(th), math.sin(th)))
            r = max(((q - Vector((q.x, cy, cz))).dot(d) for q in ring), default=.08)
            loop.append(tuple(o.matrix_world @ Vector((xs, cy + d.y * (r * .97 + .006), cz + d.z * (r * .97 + .006)))))
        C.tube(f'Sack_Tie_{k}', loop, .009, rope, res=4, caps=False, grain='x')
        top = Vector((xs, cy, cz + max((q.z - cz) for q in ring)))
        tail = [o.matrix_world @ (top + Vector(q)) for q in ((0, .02, .0), (.04, .06, -.01), (.08, .09, -.05), (.1, .1, -.12))]
        C.tube(f'Sack_Tie_End_{k}', [tuple(q) for q in tail], .008, rope, res=4, grain='x', detail=1)
    # grain: a low spill from the torn end, then loose kernels scattered round it
    torn = sacks[1]
    end = torn.matrix_world @ Vector((-.34, 0, -.06))
    gm = C.rock_mesh((.56, .44, .16), 6300, sub=9, round_=.8, chips=0, wobble=.18, flat_bottom=.05)
    for v in gm.verts:                              # a poured cone: highest at the tear, running out thin
        v.co.z = max(v.co.z, 0.0) * (1.0 - .45 * max(0.0, -v.co.x / .28)) - .005
        if v.co.z > 0: v.co.z += noise.noise(v.co * 30.0) * .012 * min(1.0, v.co.z / .03)   # kernels slide in small lumps
    g = P._bm_part('Grain_Spill', gm, grain, sharp=80, grain='z')
    g.location = (end.x - .14, end.y + side * .02, 0); g.matrix_world = S['M'][-1] @ g.matrix_basis
    bm = bmesh.new()
    for k in range(320):
        a = rr.uniform(0, math.tau); r = abs(rr.gauss(0, .26)) + .05
        x, y = end.x - .18 + r * math.cos(a) * 1.2, end.y + r * math.sin(a)
        res = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=.0045)
        M_k = Matrix.Translation((x, y, .0025)) @ Matrix.Rotation(rr.uniform(0, 3), 4, 'Z') @ Matrix.Diagonal((1.6, 1.0, .75, 1))
        bmesh.ops.transform(bm, matrix=M_k, verts=res['verts'])
    me = bpy.data.meshes.new('Grain_Scatter'); bm.to_mesh(me); bm.free(); C._uv_box(me)
    gs = bpy.data.objects.new('Grain_Scatter', me); bpy.context.scene.collection.objects.link(gs)
    C.finish(gs, 'Grain_Scatter', grain, grain='z', detail=2)
    # frayed threads at the torn seam
    for k in range(8):
        a = rr.uniform(-1, 1)
        c = torn.matrix_world @ Vector((-.3, .12 * a, .05 + .04 * rr.random()))
        C.tube(f'Seam_Thread_{k}', [tuple(c), (c.x - .03, c.y + .02 * a, c.z - .015), (c.x - .05, c.y + .035 * a, c.z - .045)], .0013, sack,
               res=4, grain='x', detail=2)

    # collision: hull of the tipped cart body (without shafts), the shafts, the loose wheel and the sacks
    body = [o for o in parts if not o.name.startswith(('Shaft', 'Wheel_On'))]
    C.hull('Collision_Cart', [p for o in body for p in C.world_points(o)])
    for k in range(2):
        C.hull(f'Collision_Shaft_{k}', [p for o in parts if o.name.startswith(f'Shaft_{k}') or o.name == f'Shaft_Ferrule_{k}' for p in C.world_points(o)])
    C.hull('Collision_WheelOn', [p for o in parts if o.name.startswith('Wheel_On') for p in C.world_points(o)])
    C.hull('Collision_WheelOff', [p for o in loose for p in C.world_points(o)])
    C.hull('Collision_Sacks', [p for o in sacks for p in C.world_points(o)])
    # centre the vignette's footprint on the origin
    bpy.context.view_layer.update()
    pts = [p for o in S['parts'] for p in C.world_points(o)]
    cx = (min(p.x for p in pts) + max(p.x for p in pts)) / 2; cy = (min(p.y for p in pts) + max(p.y for p in pts)) / 2
    for o in S['parts'] + S['coll']: o.matrix_world = Matrix.Translation((-cx, -cy, 0)) @ o.matrix_world
