"""Batch-1 variants of B02 (straight) and B03 (bend): independent forms built from the user's variant sheets, not
rotations, mirrors, scales or recolours of the base pieces. They register into ww_assets.ASSETS like the base kit.
Every variant keeps the kit port (0.60 x 0.40, clear 0.40, floor 0.10, water 0.28, 10 mm seat per face)."""
import math, random
import bmesh
from mathutils import Vector
import qa_lib as Q
import ww_lib as W
from ww_assets import asset, cbox, channel_collision, bpy_join

PI = math.pi
USER_REF = 'user-supplied variant sheet (chat, 2026-10-29)'
RIPPLE = dict(name='Water_Ripple', frames=48, loop=True, morphs=[('Water', 'Ripple0', [0, 1, 0]), ('Water', 'Ripple1', [1, 0, 1])])


# ----------------------------------------------------------------------------- shared helpers
def arc_wall(prefix, C, r0, r1, a0, a1, seed, ends=(0.0, 0.0), courses=W.COURSES, lens=(0.26, 0.42), mat=None, bevel=0.008, rough=True):
    """Curved dry-laid wall: annular-sector stones between radii r0..r1 and angles a0 < a1 about C, laid in the kit
    courses with staggered head joints. `ends` (metres of arc at mid radius) are full-height end stones at the ports."""
    mat = mat or W.mats()['stone']; rnd = random.Random(seed * 131 + 5); rm = (r0 + r1) / 2; out = []
    def sector(nm, b0, b1, z0, z1):
        n = max(2, int(math.ceil((b1 - b0) * r1 / 0.05)))      # ~5 cm facets on the outer face
        pts = W.arc(C[0], C[1], r1, b0, b1, n) + W.arc(C[0], C[1], r0, b1, b0, n)
        p = W.outline_prism(nm, pts, z0, z1, mat); p['ww_prism'] = rough; Q.add_bevel(p, bevel, 2, 35); out.append(p)
    lo, hi = a0 + ends[0] / rm, a1 - ends[1] / rm
    if ends[0] > 0: sector(f'{prefix}_End0', a0, lo, courses[0][0], courses[-1][1])
    if ends[1] > 0: sector(f'{prefix}_End1', hi, a1, courses[0][0], courses[-1][1])
    for k, (z0, z1) in enumerate(courses):
        cuts = [lo]; t = lo + rnd.uniform(*lens) / rm * (0.5 if k % 2 else 1.0)
        while t < hi - 0.12 / rm:
            cuts.append(t); t += rnd.uniform(*lens) / rm
        cuts.append(hi)
        for i in range(len(cuts) - 1): sector(f'{prefix}_C{k}_{i}', cuts[i], cuts[i + 1], z0, z1)
    return out


def hull_stone(name, pts, mat=None, bevel=0.010):
    """Carved one-piece stone from the convex hull of `pts` (buttresses, sloping wing walls)."""
    bm = bmesh.new()
    for p in pts: bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=bm.verts[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    o = Q._obj(name, bm, mat or W.mats()['stone'], sharp=30); o['ww_prism'] = True
    if bevel: Q.add_bevel(o, bevel, 2, 35)
    return o


def prism_stone(name, outline, z0, z1, mat=None, bevel=0.008):
    o = W.outline_prism(name, outline, z0, z1, mat or W.mats()['stone']); o['ww_prism'] = True
    if bevel: Q.add_bevel(o, bevel, 2, 35)
    return o


def rbox(center, size, yaw, note=''):
    b = cbox(center, size, note); b['yaw_deg'] = round(math.degrees(yaw), 2); return b


def arc_collision(C, r_in, r_out, a0, a1, n=4):
    """Floor + two walls of a curved channel as n yawed box triples (tangent boxes on the mid radius)."""
    out = []
    for i in range(n):
        a = a0 + (a1 - a0) * (i + 0.5) / n; L = (a1 - a0) / n * r_out * 1.02
        for r, w, z, h, note in (((r_in + r_out) / 2, r_out - r_in, 0.05, 0.10, 'floor'), (r_in - 0.05, 0.10, 0.20, 0.40, 'wall'),
                                 (r_out + 0.05, 0.10, 0.20, 0.40, 'wall')):
            out.append(rbox((C[0] + r * math.cos(a), C[1] + r * math.sin(a), z), (w, L, h), a, note))
    return out


def cramp(name, a, b, z=0.40):
    return W.strap(name, (a[0], a[1], z), (b[0], b[1], z), (0, 0, 1), w=0.035, rivets=2)


# ============================================================================ B02-V02 worn stepped-wall straight
@asset('B02-V02', 'WornStraight', res=2048, budget=13000, size=(0.60, 1.00, 0.40), ref='B02_V02_three_view.png',
       variant_of='B02', ref_author=USER_REF)
def b02_v02():
    M = W.mats(); P = []; S = W.stone; CW = W.course_wall
    for sy in (-1, 1):
        P.append(S(f'B02V02_Floor{sy:+d}', (0.40, 0.50, 0.10), (0, sy * 0.25, 0.05), seed=17 + sy,
                   keep=('z-', 'x-', 'x+', 'y+' if sy > 0 else 'y-'), flat=('z+', 'y-' if sy > 0 else 'y+'), chips=1, step=0.10))
    # wall tops between the pilasters weathered down in steps, never below 0.34 (6 cm freeboard over the water line)
    steps = {'L': ((-0.40, -0.14, 0.370), (-0.14, 0.12, 0.340), (0.12, 0.40, 0.385)),
             'R': ((-0.40, -0.22, 0.345), (-0.22, 0.18, 0.390), (0.18, 0.40, 0.350))}
    for sx, tag in ((-1, 'L'), (1, 'R')):
        c0, c1, inner = (-0.30, -0.20, '+') if sx < 0 else (0.20, 0.30, '-')
        P += CW(f'B02V02_Wall{tag}F', 'Y', -0.50, -0.40, c0, c1, inner, 21 + sx, ends=(0.10, 0.0))
        P += CW(f'B02V02_Wall{tag}B', 'Y', 0.40, 0.50, c0, c1, inner, 23 + sx, ends=(0.0, 0.10))
        P += CW(f'B02V02_Wall{tag}Base', 'Y', -0.40, 0.40, c0, c1, inner, 25 + sx, courses=(W.COURSES[0],), chips=2)
        segs = steps[tag]
        for i, (y0, y1, top) in enumerate(segs):
            P += CW(f'B02V02_Wall{tag}Top{i}', 'Y', y0, y1, c0, c1, inner, 27 + 3 * i + sx, courses=((0.22, top),), chips=3,
                    open_ends=(i > 0 and segs[i - 1][2] < top, i < len(segs) - 1 and segs[i + 1][2] < top))
        # one bronze strap over the pilaster joint, stopping under the lowest worn top
        y = -0.40 if sx < 0 else 0.40
        P += W.strap(f'B02V02_Strap{tag}', (sx * 0.30, y, 0.05), (sx * 0.30, y, min(t for _, _, t in segs) - 0.04), (sx, 0, 0), rivets=2)
    W.bore([(-0.20, -0.50), (0.20, -0.50), (0.20, 0.50), (-0.20, 0.50)])
    W.add_port('End_Front', (0, -0.50, 0), 0.0, P)
    W.add_port('End_Back', (0, 0.50, 0), PI, P)
    wat = W.water_plane('B02V02_Water', [(-0.20, -0.50), (0.20, -0.50), (0.20, 0.50), (-0.20, 0.50)]); W.ripple_keys(wat); P.append(wat)
    return P, dict(collision=channel_collision(0, 0, 1.00), anim=RIPPLE,
                   decisions=['Ports identical to the kit standard at both ends (full-height 10 cm pilasters).',
                              'Upper course broken into stepped worn runs; lowest wall top 0.34 keeps 6 cm freeboard over the 0.28 water line.',
                              'Exposed tops of the lower course and the step ends are weathered; a single strap per side as drawn.'])


# ============================================================================ B02-V03 half-buried footing straight
@asset('B02-V03', 'FootingStraight', res=2048, budget=14000, size=(0.84, 1.00, 0.60), ref='B02_V03_three_view.png',
       variant_of='B02', ref_author=USER_REF)
def b02_v03():
    M = W.mats(); P = []; S = W.stone
    for i, (y0, y1) in enumerate(((-0.50, -0.18), (-0.18, 0.20), (0.20, 0.50))):   # three floor flags
        keep = ['z-', 'x-', 'x+'] + (['y-'] if i == 0 else []) + (['y+'] if i == 2 else [])
        flat = ['z+'] + (['y-'] if i > 0 else []) + (['y+'] if i < 2 else [])
        P.append(S(f'B02V03_Floor{i}', (0.40, y1 - y0, 0.10), (0, (y0 + y1) / 2, 0.05), seed=31 + i, keep=tuple(keep), flat=tuple(flat), chips=0, step=0.10))
    for sx, tag in ((-1, 'L'), (1, 'R')):
        c0, c1, inner = (-0.30, -0.20, '+') if sx < 0 else (0.20, 0.30, '-')
        P += W.course_wall(f'B02V03_Wall{tag}', 'Y', -0.50, 0.50, c0, c1, inner, 33 + sx, ends=(0.10, 0.10))
        # stepped footing courses against the outer face: widest 0.84 over the middle, 20 cm transitions to the ports
        for k, (z0, z1, xo, ya, yb) in enumerate(((0.00, 0.10, 0.42, 0.30, 0.47), (0.10, 0.20, 0.38, 0.22, 0.36), (0.20, 0.28, 0.345, 0.14, 0.24))):
            out = [(0.30, -yb), (xo, -ya), (xo, ya), (0.30, yb)]
            P.append(prism_stone(f'B02V03_Step{tag}{k}', [(sx * x, y) for x, y in out], z0, z1, bevel=0.010))
        for y in (-0.42, -0.14, 0.14, 0.42):   # bronze caps across the wall top, turned down the outer face
            P += cramp(f'B02V03_Cap{tag}{y:+.2f}', (sx * 0.20, y), (sx * 0.30, y))
            P += W.strap(f'B02V03_CapDrop{tag}{y:+.2f}', (sx * 0.30, y, 0.33), (sx * 0.30, y, 0.395), (sx, 0, 0), w=0.035, rivets=1)
    # buried footing slab, two courses down to z -0.20, octagonal in plan (0.60 at the ports, 0.84 in the middle)
    foot = [(-0.30, -0.50), (0.30, -0.50), (0.42, -0.30), (0.42, 0.30), (0.30, 0.50), (-0.30, 0.50), (-0.42, 0.30), (-0.42, -0.30)]
    footing = W.coursed_prism('B02V03_Footing', foot, M['stone_dark'], courses=((-0.20, -0.09), (-0.09, 0.0)))
    for o in footing: o['ww_prism'] = False   # buried: no surface roughening (saves the grid cuts)
    P += footing
    W.bore([(-0.20, -0.50), (0.20, -0.50), (0.20, 0.50), (-0.20, 0.50)])
    ported = [o for o in P if 'Footing' not in o.name]
    W.add_port('End_Front', (0, -0.50, 0), 0.0, ported)
    W.add_port('End_Back', (0, 0.50, 0), PI, ported)
    wat = W.water_plane('B02V03_Water', [(-0.20, -0.50), (0.20, -0.50), (0.20, 0.50), (-0.20, 0.50)]); W.ripple_keys(wat); P.append(wat)
    col = channel_collision(0, 0, 1.00) + [cbox((s * 0.36, 0, 0.10), (0.12, 0.60, 0.20), 'footing step') for s in (-1, 1)]
    return P, dict(collision=col, anim=RIPPLE, below=-0.20, origin_note='base centre at grade; footing buried to z -0.20',
                   decisions=['Floor and water at the kit levels (0.10 / 0.28); ports identical to B02.',
                              'Footing steps out to 0.84 over the middle 0.60 with 0.20 transitions and continues to z -0.20 (buried).',
                              'Validation allows z down to -0.20 for the buried footing only.'])


# ============================================================================ B02-V04 keyed short coupler (40 cm)
@asset('B02-V04', 'ShortCoupler', res=1024, budget=7000, size=(0.72, 0.40, 0.40), ref='B02_V04_three_view.png',
       variant_of='B02', ref_author=USER_REF)
def b02_v04():
    M = W.mats(); P = []
    r = 0.025   # small fillet in the bore's bottom corners, as drawn
    sec = ([(-0.30, 0.0), (0.30, 0.0), (0.30, 0.40), (0.20, 0.40)] + W.arc(0.20 - r, 0.10 + r, r, 0, -PI / 2, 4) +
           W.arc(-0.20 + r, 0.10 + r, r, -PI / 2, -PI, 4) + [(-0.20, 0.40), (-0.30, 0.40)])
    u = Q.prism('B02V04_Body', sec, 0.40, M['stone'], axis='Y', center=0.0, sharp=30); u['ww_prism'] = True
    Q.add_bevel(u, 0.010, 2, 35); P.append(u)
    for sx, tag in ((-1, 'L'), (1, 'R')):
        for sy in (-1, 1):   # cedar keys 10 cm in from each end, two bronze bands each
            y = sy * 0.10
            P.append(W.wood_box(f'B02V04_Key{tag}{sy:+d}', (0.024, 0.05, 0.34), (sx * 0.312, y, 0.20), 'Z'))
            for z in (0.10, 0.30):
                P += W.strap(f'B02V04_Band{tag}{sy:+d}{z:.2f}', (sx * 0.324, y - 0.028, z), (sx * 0.324, y + 0.028, z), (sx, 0, 0), w=0.030, rivets=1)
                for t in (-1, 1):
                    P += W.strap(f'B02V04_BandTab{tag}{sy:+d}{z:.2f}{t}', (sx * 0.30, y + t * 0.026, z), (sx * 0.30, y + t * 0.052, z), (sx, 0, 0), w=0.030, rivets=1)
        # raking cedar wedges driven under the foot of each wall face
        for sy in (-1, 1):
            w = Q.prism(f'B02V04_Wedge{tag}{sy:+d}', [(sx * 0.30, 0.0), (sx * 0.36, 0.0), (sx * 0.30, 0.07)], 0.06, M['woodY'], axis='Y', center=sy * 0.035)
            Q.add_bevel(w, 0.003, 1, 40); P.append(w)
    W.bore([(-0.20, -0.20), (0.20, -0.20), (0.20, 0.20), (-0.20, 0.20)])
    W.add_port('End_Front', (0, -0.20, 0), 0.0, P)
    W.add_port('End_Back', (0, 0.20, 0), PI, P)
    wat = W.water_plane('B02V04_Water', [(-0.20, -0.20), (0.20, -0.20), (0.20, 0.20), (-0.20, 0.20)]); W.ripple_keys(wat); P.append(wat)
    return P, dict(collision=channel_collision(0, 0, 0.40), anim=RIPPLE,
                   decisions=['40 cm one-piece U (10 + 20 + 10 key spacing) used to close odd gaps in a route.',
                              'Bore bottom corners filleted 25 mm as drawn; the kit gasket covers the step against a square-cornered neighbour.'])


# ============================================================================ B02-V05 terminal spill apron
def _flare(y):   # inner face of the apron wing walls: 0.20 at the port block, 0.35 at the open end
    return 0.20 + 0.15 * (0.20 - y) / 0.60


@asset('B02-V05', 'SpillApron', res=2048, budget=15000, size=(0.90, 0.80, 0.46), ref='B02_V05_three_view.png',
       variant_of='B02', ref_author=USER_REF)
def b02_v05():
    M = W.mats(); P = []; S = W.stone
    # standard input port block: 20 cm pilasters, floor flag, weir sill holding the 0.28 water line
    for sx, tag in ((-1, 'L'), (1, 'R')):
        inner = 'x+' if sx < 0 else 'x-'
        P.append(S(f'B02V05_Pilaster{tag}', (0.10, 0.20, 0.40), (sx * 0.25, 0.30, 0.20), seed=41 + sx, keep=('z-', inner, 'y+', 'z+'), chips=1))
        P.append(S(f'B02V05_Cap{tag}', (0.13, 0.21, 0.06), (sx * 0.25, 0.295, 0.43), seed=43 + sx, keep=('z-',), chips=0, step=0.06))
        for z in (0.07, 0.32):
            P += W.strap(f'B02V05_Band{tag}{z:.2f}', (sx * 0.30, 0.22, z), (sx * 0.30, 0.38, z), (sx, 0, 0), w=0.036, rivets=2)
    P.append(S('B02V05_PortFloor', (0.40, 0.20, 0.10), (0, 0.30, 0.05), seed=45, keep=('z-', 'x-', 'x+', 'y+', 'y-'), flat=('z+',), chips=0))
    P.append(S('B02V05_Weir', (0.40, 0.06, 0.15), (0, 0.23, 0.175), seed=47, keep=('z-', 'x-', 'x+', 'y+'), chips=0, step=0.06))
    # flared wing walls stepping down in three runs; apron tiers drop twice to an open discharge edge at grade
    runs = ((0.20, 0.00, ((0.0, 0.22), (0.22, 0.34))), (0.00, -0.20, ((0.0, 0.25),)), (-0.20, -0.40, ((0.0, 0.16),)))
    for sx, tag in ((-1, 'L'), (1, 'R')):
        for i, (ya, yb, crs) in enumerate(runs):
            for k, (z0, z1) in enumerate(crs):
                q = [(_flare(ya), ya), (_flare(ya) + 0.10, ya), (_flare(yb) + 0.10, yb), (_flare(yb), yb)]
                P.append(prism_stone(f'B02V05_Wing{tag}{i}_C{k}', [(sx * x, y) for x, y in q], z0, z1, bevel=0.010))
    tiers = ((0.20, -0.10, -0.05, 0.05), (-0.10, -0.40, -0.05, 0.00))
    for i, (ya, yb, z0, z1) in enumerate(tiers):
        for sx in (-1, 1):   # each tier two flags with a joint on the axis
            q = [(0.0, ya), (_flare(ya), ya), (_flare(yb), yb), (0.0, yb)]
            P.append(prism_stone(f'B02V05_Tier{i}{"LR"[sx > 0]}', [(sx * x, y) for x, y in q], z0, z1, mat=M['stone_dark'] if i else None, bevel=0.008))
    W.bore([(-0.20, 0.20), (0.20, 0.20), (0.20, 0.40), (-0.20, 0.40)])
    W.add_port('In_Back', (0, 0.40, 0), PI, P)
    # water: pool at 0.28 over the weir, a falling sheet, a film on each tier and a short drop between them
    pool = W.water_plane('B02V05_Pool', [(-0.20, 0.26), (0.20, 0.26), (0.20, 0.40), (-0.20, 0.40)])
    film1 = W.water_plane('B02V05_Film1', [(-_flare(0.20), 0.20), (_flare(0.20), 0.20), (_flare(-0.10), -0.10), (-_flare(-0.10), -0.10)], z=0.062)
    film2 = W.water_plane('B02V05_Film2', [(-_flare(-0.10), -0.10), (_flare(-0.10), -0.10), (_flare(-0.40), -0.40), (-_flare(-0.40), -0.40)], z=0.012)
    fall = [(0.26, W.WATER_Z), (0.20, 0.270)] + [(0.20 - 0.09 * s, 0.270 - 0.208 * s * s) for s in (i / 6 for i in range(1, 7))]
    drop = [(-0.10 - 0.03 * s, 0.062 - 0.050 * s * s) for s in (i / 4 for i in range(5))]
    falls = [_sheet('B02V05_Fall', 0.195, fall), _sheet('B02V05_Drop', _flare(-0.10) - 0.005, drop)]
    Q.select_only([pool, film1, film2] + falls, pool); bpy_join()
    wat = Q.bpy.context.view_layer.objects.active; wat.name = 'B02V05_Water'; wat['qa_node'] = 'Water'
    W.ripple_keys(wat); P.append(wat)
    col = [cbox((0, 0.30, 0.05), (0.40, 0.20, 0.10), 'port floor'), cbox((0, 0.23, 0.175), (0.40, 0.06, 0.15), 'weir')]
    col += [cbox((s * 0.25, 0.30, 0.23), (0.10, 0.20, 0.46), 'pilaster') for s in (-1, 1)]
    col += [cbox((0, -0.10, 0.0), (0.60, 0.60, 0.10), 'apron')]
    col += [rbox((s * (_flare(-0.10) + 0.05), -0.10, 0.12), (0.10, 0.62, 0.24), -s * math.atan2(0.15, 0.60), 'wing wall') for s in (-1, 1)]
    return P, dict(collision=col, anim=RIPPLE, below=-0.05, origin_note='port-block floor centre at grade; apron tiers set 5 cm into the soil',
                   decisions=['One standard port (In_Back); the open discharge edge is a route terminator, no second port.',
                              'A 15 cm weir sill holds the kit 0.28 water line at the port; water spills 3 cm over it onto the apron.',
                              'Sheet side labels 10 / 5 cm read as the two apron tier thicknesses: tiers top at 0.05 and 0.00, set 5 cm into the soil.',
                              'Wing walls flare from 0.60 to 0.90 and step down 0.34 / 0.25 / 0.16 toward the open end.'])


def _sheet(name, half_w, path):
    """Falling water sheet across x = +-half_w along a (y, z) path (crest, then a ballistic fall: y linear, z quadratic)."""
    bm = bmesh.new(); rows = []
    for y, z in path:
        rows.append([bm.verts.new((x, y, z)) for x in (-half_w, 0.0, half_w)])
    for a, b in zip(rows, rows[1:]):
        for j in range(2): bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))
    bm.normal_update()
    if sum(f.normal.y for f in bm.faces) > 0: bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    uv = bm.loops.layers.uv.new('UVMap')
    for f in bm.faces:
        for lp in f.loops: lp[uv].uv = (lp.vert.co.x / W.WATER_TILE, (lp.vert.co.y - lp.vert.co.z) / W.WATER_TILE)
    o = Q._obj(name, bm, W.mats()['water'], smooth=True, sharp=80); o.data.materials.append(W.mats()['foam'])
    return o


# ============================================================================ B03-V02 right broad-radius bend
V02_C = (0.60, -0.60)


@asset('B03-V02', 'BroadBendRight', res=2048, budget=18000, size=(1.20, 1.20, 0.40), ref='B03_V02_three_view.png',
       variant_of='B03', ref_author=USER_REF)
def b03_v02():
    M = W.mats(); P = []; C = V02_C; a0, a1 = PI / 2, PI
    P += arc_wall('B03V02_Inner', C, 0.60, 0.70, a0, a1, 51, ends=(0.10, 0.10))
    P += arc_wall('B03V02_Outer', C, 1.10, 1.20, a0, a1, 53, ends=(0.10, 0.10), lens=(0.30, 0.46))
    P += arc_wall('B03V02_Floor', C, 0.70, 1.10, a0, a1, 55, courses=((0.0, 0.10),), lens=(0.38, 0.52), bevel=0.006, rough=False)
    # cedar posts against the outer wall, a bronze band running between them
    posts = [a0 + (a1 - a0) * t for t in (0.22, 0.5, 0.78)]; pw = 0.082 / 1.20
    for i, a in enumerate(posts):
        P.append(W.wood_box(f'B03V02_Post{i}', (0.05, 0.08, 0.36), (C[0] + 1.225 * math.cos(a), C[1] + 1.225 * math.sin(a), 0.19), 'Z', rot=(0, 0, a)))
    edges = [a0 + 0.10 / 1.15] + [b for a in posts for b in (a - pw / 2, a + pw / 2)] + [a1 - 0.10 / 1.15]
    for i in range(0, len(edges), 2):
        P += arc_wall(f'B03V02_Band{i // 2}', C, 1.200, 1.207, edges[i], edges[i + 1], 1, courses=((0.290, 0.325),), lens=(9, 9), mat=M['bronze'], bevel=0.0015, rough=False)
    for r0, r1, tag in ((0.60, 0.70, 'I'), (1.10, 1.20, 'O')):   # cramps over the pilaster joints on both walls
        for a in (a0 + 0.10 / ((r0 + r1) / 2), a1 - 0.10 / ((r0 + r1) / 2)):
            P += cramp(f'B03V02_Cramp{tag}{a:.2f}', (C[0] + (r0 + 0.01) * math.cos(a), C[1] + (r0 + 0.01) * math.sin(a)),
                       (C[0] + (r1 - 0.01) * math.cos(a), C[1] + (r1 - 0.01) * math.sin(a)))
    bore = W.arc(*C, 1.10, a0, a1, 16) + W.arc(*C, 0.70, a1, a0, 12)
    W.bore(bore)
    W.add_port('In_Front', (C[0] - 0.90, C[1], 0), 0.0, P)
    W.add_port('Out_Right', (C[0], C[1] + 0.90, 0), PI / 2, P)
    wat = W.water_plane('B03V02_Water', bore); W.ripple_keys(wat); P.append(wat)
    return P, dict(collision=arc_collision(C, 0.70, 1.10, a0, a1), anim=RIPPLE,
                   decisions=['Right-hand 90 degree arc, inner wall radius 0.60, outer 1.20, bore between 0.70 and 1.10; ports on the radial end faces.',
                              'Curved blocks laid in the kit courses with staggered joints; floor in three curved flags.',
                              'Its own form: a different radius and outer edge from B03, not a scaled copy.'])


# ============================================================================ B03-V03 left chamfer-buttress bend
V03_BORE = ([(-0.20, -0.50), (0.20, -0.50), (0.20, 0.25), (0.05, 0.40), (-0.50, 0.40), (-0.50, 0.0)] +
            W.arc(-0.26, -0.06, 0.06, PI / 2, 0, 4))


@asset('B03-V03', 'ChamferBendLeft', res=2048, budget=16000, size=(1.00, 1.00, 0.40), ref='B03_V03_three_view.png',
       variant_of='B03', ref_author=USER_REF)
def b03_v03():
    M = W.mats(); P = []; CW = W.course_wall
    P += CW('B03V03_InStem', 'Y', -0.50, -0.10, -0.30, -0.20, '+', 61, ends=(0.10, 0.0))
    P += CW('B03V03_InCross', 'X', -0.50, -0.30, -0.10, 0.0, '+', 63, ends=(0.10, 0.0))
    P += W.coursed_prism('B03V03_InFillet', [(-0.30, -0.10), (-0.20, -0.10), (-0.20, -0.06)] + W.arc(-0.26, -0.06, 0.06, 0, PI / 2, 4)[1:-1] +
                         [(-0.26, 0.0), (-0.30, 0.0)], M['stone'])
    P += CW('B03V03_Right', 'Y', -0.50, 0.15, 0.20, 0.30, '-', 65, ends=(0.10, 0.0))
    P += CW('B03V03_Top', 'X', -0.50, -0.05, 0.40, 0.50, '-', 67, ends=(0.10, 0.0))
    # outer corner cut off at 45 degrees (bore face x + y = 0.45), carved one piece per course
    P += W.coursed_prism('B03V03_Chamfer', [(0.20, 0.15), (0.30, 0.15), (0.30, 0.291), (0.091, 0.50), (-0.05, 0.50), (-0.05, 0.40),
                                            (0.05, 0.40), (0.20, 0.25)], M['stone'])
    # sloping solid buttress on the right face behind the chamfer
    foot = [(0.30, -0.02), (0.50, 0.08), (0.50, 0.20), (0.30, 0.28)]
    P.append(hull_stone('B03V03_Buttress', [(x, y, 0.0) for x, y in foot] + [(x, y, 0.38 if x < 0.4 else 0.06) for x, y in foot], M['stone_dark']))
    f = W.outline_prism('B03V03_Floor', V03_BORE, 0.0, 0.10, M['stone']); Q.add_bevel(f, 0.006, 2, 35); P.append(f)
    # cedar battens with bronze bands either side of both ports, cramps over the pilaster joints
    for nm, loc, nrm in (('InL', (-0.315, -0.42), (-1, 0, 0)), ('InR', (0.315, -0.42), (1, 0, 0)),
                         ('OutS', (-0.42, -0.115), (0, -1, 0)), ('OutN', (-0.42, 0.515), (0, 1, 0))):
        along_x = nrm[0] == 0
        size = (0.06, 0.03, 0.38) if along_x else (0.03, 0.06, 0.38)
        P.append(W.wood_box(f'B03V03_Batten{nm}', size, (loc[0], loc[1], 0.19), 'Z'))
        t = Vector((1, 0)) if along_x else Vector((0, 1)); face = Vector(loc) - Vector(nrm[:2]) * 0.015; top = face + Vector(nrm[:2]) * 0.030
        for z in (0.10, 0.30):   # band over the batten face, tabs riveted to the wall either side (as B02)
            P += W.strap(f'B03V03_BattenBand{nm}{z:.2f}', (*(top - t * 0.03), z), (*(top + t * 0.03), z), nrm, w=0.030, rivets=1)
            for s in (-1, 1):
                P += W.strap(f'B03V03_BattenTab{nm}{z:.2f}{s}', (*(face + t * s * 0.031), z), (*(face + t * s * 0.058), z), nrm, w=0.030, rivets=1)
    P += cramp('B03V03_CrampStem', (-0.29, -0.40), (-0.21, -0.40)) + cramp('B03V03_CrampRight', (0.21, -0.40), (0.29, -0.40))
    P += cramp('B03V03_CrampCross', (-0.40, -0.09), (-0.40, -0.01)) + cramp('B03V03_CrampTop', (-0.40, 0.41), (-0.40, 0.49))
    W.bore(V03_BORE)
    W.add_port('In_Front', (0, -0.50, 0), 0.0, P)
    W.add_port('Out_Left', (-0.50, 0.20, 0), -PI / 2, P)
    wat = W.water_plane('B03V03_Water', V03_BORE); W.ripple_keys(wat); P.append(wat)
    col = channel_collision(0, -0.25, 0.50) + channel_collision(-0.15, 0.20, 0.70, along='X')
    col += [cbox((0.40, 0.13, 0.11), (0.20, 0.30, 0.22), 'buttress')]
    return P, dict(collision=col, anim=RIPPLE,
                   decisions=['Left-hand form built as its own mesh (front inlet, left outlet), not a mirror of B03.',
                              'Outer bore corner chamfered at 45 degrees; a sloping solid buttress backs the right face.',
                              'Inner corner on a 6 cm fillet stone; cedar battens and bronze bands either side of each port.'])


# ============================================================================ B03-V04 left swept terrace bend
V04_C = (-0.27, -0.37)


@asset('B03-V04', 'TerraceBendLeft', res=2048, budget=18000, size=(1.30, 1.10, 0.40), ref='B03_V04_three_view.png',
       variant_of='B03', ref_author=USER_REF)
def b03_v04():
    M = W.mats(); P = []; S = W.stone; CW = W.course_wall; C = V04_C
    # straight stubs at the ports (inlet x 0.03..0.43, outlet y -0.07..0.33), swept arc between them
    P += CW('B03V04_InInner', 'Y', -0.55, -0.37, -0.07, 0.03, '+', 71, ends=(0.10, 0.0))
    P += CW('B03V04_InOuter', 'Y', -0.55, -0.37, 0.43, 0.53, '-', 73, ends=(0.10, 0.0))
    P += CW('B03V04_OutInner', 'X', -0.65, -0.27, -0.17, -0.07, '+', 75, ends=(0.10, 0.0))
    P += CW('B03V04_OutOuter', 'X', -0.65, -0.27, 0.33, 0.43, '-', 77, ends=(0.10, 0.0))
    P += arc_wall('B03V04_ArcInner', C, 0.20, 0.30, 0, PI / 2, 79, lens=(0.20, 0.30))
    P += arc_wall('B03V04_ArcOuter', C, 0.70, 0.80, 0, PI / 2, 81, lens=(0.30, 0.44))
    P += arc_wall('B03V04_ArcFloor', C, 0.30, 0.70, 0, PI / 2, 83, courses=((0.0, 0.10),), lens=(0.30, 0.40), bevel=0.006, rough=False)
    P.append(S('B03V04_InFloor', (0.40, 0.18, 0.10), (0.23, -0.46, 0.05), seed=85, keep=('z-', 'x-', 'x+', 'y-', 'y+'), flat=('z+',), chips=0))
    P.append(S('B03V04_OutFloor', (0.38, 0.40, 0.10), (-0.46, 0.13, 0.05), seed=87, keep=('z-', 'x-', 'x+', 'y-', 'y+'), flat=('z+',), chips=0))
    # terrace shelf 12 cm proud of the outer wall at mid height, on stone brackets
    P += arc_wall('B03V04_Shelf', C, 0.80, 0.92, 0, PI / 2, 89, courses=((0.22, 0.28),), lens=(0.40, 0.55), mat=M['stone_dark'], bevel=0.008)
    P.append(prism_stone('B03V04_ShelfIn', [(0.53, -0.45), (0.65, -0.45), (0.65, -0.37), (0.53, -0.37)], 0.22, 0.28, M['stone_dark']))
    P.append(prism_stone('B03V04_ShelfOut', [(-0.55, 0.43), (-0.27, 0.43), (-0.27, 0.55), (-0.55, 0.55)], 0.22, 0.28, M['stone_dark']))
    for i, a in enumerate((PI / 8, PI / 4, 3 * PI / 8)):
        P.append(S(f'B03V04_Bracket{i}', (0.12, 0.06, 0.14), (C[0] + 0.86 * math.cos(a), C[1] + 0.86 * math.sin(a), 0.15), seed=91 + i,
                   keep=('x-', 'z+'), chips=0, rot=(0, 0, a), step=0.05))
    P.append(S('B03V04_BracketIn', (0.12, 0.06, 0.14), (0.59, -0.41, 0.15), seed=95, keep=('x-', 'z+'), chips=0, step=0.05))
    P.append(S('B03V04_BracketOut', (0.06, 0.12, 0.14), (-0.41, 0.49, 0.15), seed=97, keep=('y-', 'z+'), chips=0, step=0.05))
    P += cramp('B03V04_CrampInI', (-0.06, -0.45), (0.02, -0.45)) + cramp('B03V04_CrampInO', (0.44, -0.45), (0.52, -0.45))
    P += cramp('B03V04_CrampOutI', (-0.55, -0.16), (-0.55, -0.08)) + cramp('B03V04_CrampOutO', (-0.55, 0.34), (-0.55, 0.42))
    P += W.strap('B03V04_StrapInInner', (-0.07, -0.45, 0.05), (-0.07, -0.45, 0.36), (-1, 0, 0), rivets=2)
    P += W.strap('B03V04_StrapOutInner', (-0.55, -0.17, 0.05), (-0.55, -0.17, 0.36), (0, -1, 0), rivets=2)
    bore = ([(0.03, -0.55), (0.43, -0.55), (0.43, -0.37)] + W.arc(*C, 0.70, 0, PI / 2, 14)[1:] + [(-0.65, 0.33), (-0.65, -0.07), (-0.27, -0.07)] +
            W.arc(*C, 0.30, PI / 2, 0, 8)[1:])
    W.bore(bore)
    W.add_port('In_Front', (0.23, -0.55, 0), 0.0, P)
    W.add_port('Out_Left', (-0.65, 0.13, 0), -PI / 2, P)
    wat = W.water_plane('B03V04_Water', bore); W.ripple_keys(wat); P.append(wat)
    col = channel_collision(0.23, -0.46, 0.18) + channel_collision(-0.46, 0.13, 0.38, along='X') + arc_collision(C, 0.30, 0.70, 0, PI / 2, 3)
    return P, dict(collision=col, anim=RIPPLE,
                   decisions=['Left swept arc about (-0.27, -0.37): inner wall radius 0.20, bore 0.30-0.70, outer wall to 0.80.',
                              'Ports on the kit grid: inlet centre (0.23, -0.55), outlet centre (-0.65, 0.13); offsets go to interfaces.json.',
                              'Terrace shelf 12 cm proud of the outer wall at 0.22-0.28 on three stone brackets, continued over both stubs.'])
