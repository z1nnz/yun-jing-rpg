"""D3 dry well for qingxi-world-ruins-b: a dry-stone ring over a stone-lined shaft, two timber uprights
carrying a beam and a wooden rope drum, the rope snapped part way down.

Blender Z-up, 1 unit = 1 m, front faces -Y, origin at the ring centre, z = 0 at ground level.
The shaft is modelled down to SHAFT_Z: the terrain must be cut (a 0.88 m hole) where the well is placed.
"""
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix
import wr_core as C
from wr_core import S
import wr_materials as WM
import wr_props as P

LIMIT = (1.8, 1.8, 2.2)
SHAFT_Z = -1.6
EMBED = -SHAFT_Z
R_IN, R_OUT, RING_H = .44, .71, .68
POST_X, POST_W, POST_D, POST_H = .76, .15, .17, 2.1
BEAM_Z = 1.93


def _course(tag, z0, h, r_in, r_out, n, mat, seed, detail=0, phase=0.0, round_=.26, chips=5, lip=False):
    """One course of dry-laid stones round the ring: each stone runs through the wall, lengths vary,
    joints break over the course below via the phase offset. Returns the stones."""
    rr = random.Random(seed)
    w = [rr.uniform(.8, 1.2) for _ in range(n)]; tot = sum(w)
    a = phase; out = []
    rm = (r_in + r_out) / 2
    for k in range(n):
        da = math.tau * w[k] / tot
        ac = a + da / 2
        L = rm * da * .99
        sz = (L, (r_out - r_in) * rr.uniform(.95, 1.05), h * rr.uniform(.93, 1.07))
        dr = rr.uniform(-.015, .015)                # stones sit a little proud or shy of the face
        p = ((rm + dr) * math.cos(ac), (rm + dr) * math.sin(ac), z0 + sz[2] / 2)
        o = C.rock(f'{tag}_{k:02d}', p, sz, mat, seed * 7 + k, rot=(rr.uniform(-.03, .03), rr.uniform(-.03, .03), ac + math.pi / 2),
                   sub=2 if detail else 3, round_=round_, chips=chips, chip_depth=(.05, .18), wobble=.07, flat_bottom=.8, detail=detail)
        o['ring_angle'] = ac
        out.append(o); a += da
    return out


def d3_well():
    stone = WM.stone('M_DW_FieldStone', slot='Stone', tones=('#666C66', '#535953', '#7C807A'), warm='#7A7262', moss=.8, moss_low=.35,
                     moss_top=.5, lichen=1.0, lichen_cover=.4, rosettes=.7, rosette_scale=9.0, small_rosettes=.8, relief=1.8)
    lip = WM.stone('M_DW_LipStone', slot='Stone', tones=('#6A706A', '#575D57', '#80847E'), warm='#7A7262', moss=.4, lichen=.8,
                   rosettes=.6, rosette_scale=9.0, small_rosettes=.6, relief=1.2, rough=.76)
    shaft = WM.stone('M_DW_ShaftStone', slot='Stone', tones=('#545A56', '#3E4440', '#666C67'), moss=.8, moss_top=-1.0, lichen=.1, ground_dirt=0)
    core = WM.stone('M_DW_Hearting', slot='Stone', tones=('#3A403C', '#2E3330', '#454B46'), warm='#3E3A33', moss=.2, lichen=0, ground_dirt=0)
    fresh = WM.stone('M_DW_FreshBreak', slot='Stone', tones=('#8E887C', '#7A746A', '#A09A8C'), warm='#9C8C70', moss=0, lichen=0, ground_dirt=0)
    silt = WM.stone('M_DW_DrySilt', slot='Stone', tones=('#6E5E4A', '#5A4C3C', '#7E6E58'), warm='#7A6A52', moss=0, lichen=0, ground_dirt=0, relief=.6)
    wood = WM.aged_wood('M_DW_OldTimber', grey=.88, rough=.88, ring=4.5, mid=1.0)
    patch = WM.aged_wood('M_DW_PatchPlank', grey=.75, rough=.82)
    rope = WM.rope('M_DW_HempRope')
    rr = random.Random(5100)

    # hearting behind the faces: closes every gap between dry-laid stones
    C.lathe('Hearting', [(R_IN + .03, SHAFT_Z), (R_OUT - .09, SHAFT_Z), (R_OUT - .09, RING_H - .1), (R_IN + .03, RING_H - .1), (R_IN + .03, SHAFT_Z)],
            (0, 0, 0), core, seg=40)
    # shaft lining below ground: smaller stones, only their inner faces are ever seen
    z = SHAFT_Z; k = 0
    while z < -.02:
        h = rr.uniform(.12, .15)
        _course(f'Shaft_{k:02d}', z, h, R_IN, R_IN + .2, 15, shaft, 5200 + k, detail=1, phase=rr.uniform(0, 1), round_=.3, chips=3)
        z += h; k += 1
    # the ring above ground: three walling courses and a coping of larger, use-worn lip stones
    z = -.04
    for k, h in enumerate((.14, .135, .13, .125)):
        _course(f'Ring_{k}', z, h, R_IN, R_OUT, 19 - k % 2, stone, 5300 + k, phase=k * .23, round_=.24, chips=7)
        z += h
        # pinnings: thin slivers driven into the bed joint from outside, as a waller tightens a course
        for j in range(9):
            a = rr.uniform(0, math.tau); s_ = rr.uniform(.05, .09)
            C.rock(f'Pinning_{k}_{j}', ((R_OUT - .05) * math.cos(a), (R_OUT - .05) * math.sin(a), z - .002), (s_, .1, s_ * .4), stone,
                   5700 + 10 * k + j, rot=(0, 0, a + math.pi / 2), sub=1, round_=.3, chips=3, flat_bottom=.6, detail=1)
    coping = _course('Coping', z, RING_H - z, R_IN - .02, R_OUT + .02, 13, lip, 5400, phase=.4, round_=.22, chips=6)
    # one lip stone has lost its outer top corner
    victim = min(coping, key=lambda o: abs(math.atan2(math.sin(o['ring_angle'] + 1.15), math.cos(o['ring_angle'] + 1.15))))
    ac = victim['ring_angle']
    rm =C.rock_mesh((.2, .2, .2), 5451, sub=2, round_=.35, chips=7, chip_depth=(.08, .25), wobble=.12)
    bm = bmesh.new()
    for v in rm.verts: bm.verts.new(v.co)
    rm.free()
    res = bmesh.ops.convex_hull(bm, input=bm.verts[:])
    bmesh.ops.delete(bm, geom=list({g for g in res['geom_interior'] + res['geom_unused'] if isinstance(g, bmesh.types.BMVert) and g.is_valid}), context='VERTS')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.transform(Matrix.Translation((math.cos(ac) * (R_OUT + .03), math.sin(ac) * (R_OUT + .03), RING_H + .03)))
    me = bpy.data.meshes.new('Cutter_Corner'); bm.to_mesh(me); bm.free(); me.materials.append(fresh)
    cutter = bpy.data.objects.new('Cutter_Corner', me); bpy.context.scene.collection.objects.link(cutter)
    victim.data.materials.append(fresh)
    P._bite(victim, [cutter])
    bpy.data.objects.remove(cutter, do_unlink=True)
    # a dry floor at the bottom: silt and a few fallen stones
    C.cyl('Shaft_Floor', (0, 0, SHAFT_Z + .02), R_IN + .02, .05, silt, verts=24)
    for k in range(5):
        a = rr.uniform(0, math.tau); r = rr.uniform(0, .25); s = rr.uniform(.08, .14)
        C.rock(f'Fallen_{k}', (r * math.cos(a), r * math.sin(a), SHAFT_Z + .05 + s * .2), (s * 1.3, s, s * .6), stone, 5500 + k,
               rot=(0, 0, rr.uniform(0, 3)), sub=1, round_=.3, chips=4, flat_bottom=.7, detail=1)

    # timber frame: two uprights outside the ring, a squared beam through mortises near their tops
    for k, sx in enumerate((-1, 1)):
        # adze-hewn post: slightly irregular faces, knocked arrises, a few checks; not a sawn box
        bm = C.rock_mesh((POST_W, POST_D, POST_H + .05), 5600 + k, sub=6, round_=.1, chips=4, chip_depth=(.04, .1), wobble=.025, taper=-.06)
        for v in bm.verts:
            v.co.x += .006 * math.sin(v.co.z * 2.3 + k)             # a gentle bow along its length
            if abs(v.co.y) > POST_D * .45 and abs(v.co.x) < POST_W * .12 and .2 < v.co.z + POST_H / 2 < 1.6:
                v.co.y *= .97                                       # shallow drying check down the face
        o = P._bm_part(f'Upright_{k}', bm, wood, sharp=40, grain='z')
        o.location = (sx * POST_X, 0, (POST_H - .05) / 2); o.rotation_euler = (rr.uniform(-.012, .012), sx * .01, 0)
        o.matrix_world = S['M'][-1] @ o.matrix_basis
        C.box(f'Peg_{k}', (sx * POST_X, -POST_D / 2 - .012, BEAM_Z + .11), (.03, .04, .03), wood, bevel=.004, grain='y')
    bm = C.rock_mesh((2 * POST_X + .22, .13, .15), 5650, sub=8, round_=.1, chips=5, chip_depth=(.03, .09), wobble=.02)
    for v in bm.verts:
        v.co.z += .008 * math.sin(v.co.x * 1.9 + .4)                # a slight sag and twist along the old beam
    o = P._bm_part('Beam', bm, wood, sharp=40, grain='x')
    o.location = (0, 0, BEAM_Z); o.matrix_world = S['M'][-1] @ o.matrix_basis
    # rope drum on the beam, the rope coiled on it and snapped part way down
    for k, x in enumerate((-.09, .09)):
        C.cyl(f'Drum_Flange_{k}', (x, 0, BEAM_Z), .1, .025, wood, axis='x', verts=16, grain='x')
    C.cyl('Drum', (0, 0, BEAM_Z), .082, .16, wood, axis='x', verts=16, grain='x')
    pts = []
    for i in range(5 * 14 + 1):
        a = i / 14 * math.tau
        pts.append((-.065 + .13 * i / 70, .092 * math.cos(a), BEAM_Z + .092 * math.sin(a)))
    C.tube('Rope_Coil', pts, .009, rope, res=6, grain='x')
    end_z = 1.22
    hang =[(.065, -.093, BEAM_Z)] + [(.065 + .01 * math.sin(i * 1.3), -.095 - .006 * i, BEAM_Z - (BEAM_Z - end_z) * i / 6) for i in range(1, 7)]
    C.tube('Rope_Hanging', hang, .011, rope, res=6, grain='z')
    ex, ey, ez = hang[-1]
    for k in range(11):
        a = k / 11 * math.tau + rr.uniform(-.2, .2); L = rr.uniform(.08, .17); sp = rr.uniform(.02, .055)
        cu = rr.uniform(.6, 1.4) * (1 if k % 2 else -1)          # each strand untwists and curls its own way
        pts = []
        for j in range(6):
            t = j / 5
            aa = a + cu * t * 1.6
            rad = sp * (.15 + .85 * t ** .7)
            pts.append((ex + math.cos(aa) * rad, ey + math.sin(aa) * rad, ez + .01 - L * t + .25 * L * t * t * (sp / .055)))
        C.tube(f'Rope_Fray_{k}', pts, .0022, rope, radii=[1.0, .95, .85, .75, .6, .45], res=4, caps=True, grain='z', detail=2)
    # old repair on the left upright: a grey plank lashed against its outer face
    px = -POST_X - POST_W / 2 - .022
    C.box('Repair_Plank', (px, .005, 1.02), (.04, .13, .6), patch, bevel=.006, rot=(0, .02, 0), grain='z')
    for j, zl in enumerate((.82, 1.2)):
        pts = []
        for t in range(3 * 8 + 1):
            ang = t / 8 * math.tau
            cxs, cys = (-POST_X - .022), 0.0
            hx, hy = POST_W / 2 + .035, POST_D / 2 + .01
            pts.append((cxs + hx * max(-1, min(1, 1.4 * math.cos(ang))), cys + hy * max(-1, min(1, 1.4 * math.sin(ang))), zl + .022 * t / 8))
        C.tube(f'Lashing_{j}', pts, .007, rope, res=6, grain='z')

    # collision: the ring as twelve convex blocks round the open shaft, and the two uprights
    for k in range(12):
        a = k / 12 * math.tau
        C.hull_box(f'Collision_Ring_{k:02d}', ((R_IN + R_OUT) / 2 * math.cos(a), (R_IN + R_OUT) / 2 * math.sin(a), RING_H / 2),
                   ((R_IN + R_OUT) * math.pi / 12 + .02, R_OUT - R_IN + .04, RING_H), rot_z=a + math.pi / 2)
    for k, sx in enumerate((-1, 1)):
        C.hull_box(f'Collision_Upright_{k}', (sx * POST_X, 0, POST_H / 2), (POST_W, POST_D, POST_H))
