"""Procedural builders for Qingxi waterworks B01-B12. Each builder() creates parts in the active collection and
returns (parts, info). info: ports come from W.STATE; 'pivots' {node: xyz}; 'anim' {name, frames, tracks, morphs};
'collision' list of boxes; 'below' lowest allowed z (buried piles, axle-rooted parts)."""
import math, random
from mathutils import Vector, Matrix, Euler
import qa_lib as Q
import ww_lib as W

TAU = math.tau
PI = math.pi
ASSETS = {}


def asset(aid, name, res=1024, budget=8000, size=None, ref=None, tri_note='', variant_of=None, ref_author=None):
    def deco(fn):
        ASSETS[aid] = dict(id=aid, name=name, res=res, budget=budget, size=size, build=fn, ref=ref or f'{aid}_three_view.png',
                           variant_of=variant_of, ref_author=ref_author or 'Codex / OpenAI image_gen')
        return fn
    return deco


def cbox(center, size, note=''):
    return dict(type='box', center=[round(c, 4) for c in center], size=[round(s, 4) for s in size], note=note)


def channel_collision(cx, cy, L, along='Y'):
    """U-section collision: floor slab + two walls (water bore stays open)."""
    if along == 'Y':
        return [cbox((cx, cy, 0.05), (0.40, L, 0.10), 'floor'), cbox((cx - 0.25, cy, 0.20), (0.10, L, 0.40), 'wall'),
                cbox((cx + 0.25, cy, 0.20), (0.10, L, 0.40), 'wall')]
    return [cbox((cx, cy, 0.05), (L, 0.40, 0.10), 'floor'), cbox((cx, cy - 0.25, 0.20), (L, 0.10, 0.40), 'wall'),
            cbox((cx, cy + 0.25, 0.20), (L, 0.10, 0.40), 'wall')]


# ============================================================================ B01 square public source plinth
@asset('B01', 'SourcePlinth', res=2048, budget=26000, size=(1.40, 1.40, 0.46))
def b01():
    M = W.mats(); P = []; S = W.stone; CW = W.course_wall
    for sy, tag in ((-1, 'F'), (1, 'B')):
        c0, c1, inner = (-0.70, -0.60, '+') if sy < 0 else (0.60, 0.70, '-')
        # each half: worn corner stone outside, port cheek stone (mating face kept flat) at the 40 cm opening
        P += CW(f'B01_Wall{tag}L', 'X', -0.70, -0.20, c0, c1, inner, 11 + sy, ends=(0.14, 0.10), end_keep=((), ('outer',)),
                joints=(-0.42,), open_ends=(True, False))
        P += CW(f'B01_Wall{tag}R', 'X', 0.20, 0.70, c0, c1, inner, 13 + sy, ends=(0.10, 0.14), end_keep=(('outer',), ()),
                joints=(0.42,), open_ends=(False, True))
        P.append(S(f'B01_PortFloor{tag}', (0.40, 0.10, 0.10), (0, sy * 0.65, 0.05), seed=23 + sy,
                   keep=('z-', 'z+', 'y-', 'y+', 'x-', 'x+'), chips=0, bevel=0.006))
    for sx, tag in ((-1, 'L'), (1, 'R')):
        c0, c1, inner = (-0.70, -0.60, '+') if sx < 0 else (0.60, 0.70, '-')
        P += CW(f'B01_Side{tag}', 'Y', -0.60, 0.60, c0, c1, inner, 31 + sx, joints=(-0.20, 0.20))
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.append(S(f'B01_Floor{sx:+d}{sy:+d}', (0.60, 0.60, 0.10), (sx * 0.30, sy * 0.30, 0.05), seed=41 + sx + 3 * sy,
                       keep=('z-', 'x+' if sx > 0 else 'x-', 'y+' if sy > 0 else 'y-'),
                       flat=('z+', 'x-' if sx > 0 else 'x+', 'y-' if sy > 0 else 'y+'), chips=0, step=0.10))
    # raised cap stones on the four corners and over the port cheeks (sheet: caps proud of the 40 cm rim)
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.append(S(f'B01_CapCorner{sx:+d}{sy:+d}', (0.17, 0.17, 0.06), (sx * 0.615, sy * 0.615, 0.43), seed=51 + sx + 2 * sy,
                       keep=('z-',), chips=1, chip_r=(0.015, 0.03), step=0.06))
            P.append(S(f'B01_CapCheek{sx:+d}{sy:+d}', (0.13, 0.10, 0.05), (sx * 0.285, sy * 0.65, 0.425), seed=61 + sx + 2 * sy,
                       keep=('z-',), chips=0, step=0.06))
    # bronze: vertical straps over the forced head joints, cramps across them on the rim, corner wraps
    for sy in (-1, 1):
        for x in (-0.42, 0.42):
            P += W.strap(f'B01_StrapFB{sy}{x:+.2f}', (x, sy * 0.70, 0.05), (x, sy * 0.70, 0.36), (0, sy, 0), rivets=2)
            P += W.strap(f'B01_Cramp{sy}{x:+.2f}', (x - 0.05, sy * 0.65, 0.40), (x + 0.05, sy * 0.65, 0.40), (0, 0, 1), w=0.035, rivets=2)
    for sx in (-1, 1):
        for y in (-0.20, 0.20):
            P += W.strap(f'B01_StrapS{sx}{y:+.2f}', (sx * 0.70, y, 0.05), (sx * 0.70, y, 0.36), (sx, 0, 0), rivets=2)
            P += W.strap(f'B01_CrampS{sx}{y:+.2f}', (sx * 0.65, y - 0.05, 0.40), (sx * 0.65, y + 0.05, 0.40), (0, 0, 1), w=0.035, rivets=2)
        for sy in (-1, 1):
            P += W.strap(f'B01_CornerX{sx}{sy}', (sx * 0.70, sy * 0.635, 0.08), (sx * 0.70, sy * 0.635, 0.32), (sx, 0, 0), w=0.034, rivets=1)
            P += W.strap(f'B01_CornerY{sx}{sy}', (sx * 0.635, sy * 0.70, 0.08), (sx * 0.635, sy * 0.70, 0.32), (0, sy, 0), w=0.034, rivets=1)
    bore = [(-0.60, -0.60), (-0.20, -0.60), (-0.20, -0.70), (0.20, -0.70), (0.20, -0.60), (0.60, -0.60), (0.60, 0.60),
            (0.20, 0.60), (0.20, 0.70), (-0.20, 0.70), (-0.20, 0.60), (-0.60, 0.60)]
    W.bore(bore)
    W.add_port('Out_Front', (0, -0.70, 0), 0.0, P)
    W.add_port('In_Back', (0, 0.70, 0), PI, P)
    wat = W.water_plane('B01_Water', bore); W.ripple_keys(wat, 0.003); P.append(wat)
    col = [cbox((0, 0, 0.05), (1.40, 1.40, 0.10), 'floor')] + [cbox((s * 0.65, 0, 0.20), (0.10, 1.40, 0.40), 'side wall') for s in (-1, 1)]
    col += [cbox((s * 0.45, sy * 0.65, 0.20), (0.50, 0.10, 0.40), 'front/back wall') for s in (-1, 1) for sy in (-1, 1)]
    return P, dict(collision=col, anim=dict(name='Water_Ripple', frames=48, loop=True, morphs=[('Water', 'Ripple0', [0, 1, 0]), ('Water', 'Ripple1', [1, 0, 1])]),
                   decisions=['Ports cut through front/back walls, floor continuous at z=0.10, no spill lip.',
                              'Walls dry-laid in two courses (bed joint 0.22) with staggered head joints, as drawn.',
                              'Cap stones sit proud of the 0.40 rim (top 0.46) as on the sheet; they stay off the port faces.'])


# ============================================================================ B02 straight trough
@asset('B02', 'StraightTrough', res=2048, budget=12000, size=(0.60, 1.00, 0.40))
def b02():
    M = W.mats(); P = []; S = W.stone
    for sy in (-1, 1):   # two floor flags, worn joint between them, port ends and wall sides flat
        P.append(S(f'B02_Floor{sy:+d}', (0.40, 0.50, 0.10), (0, sy * 0.25, 0.05), seed=3 + sy,
                   keep=('z-', 'x-', 'x+', 'y+' if sy > 0 else 'y-'), flat=('z+', 'y-' if sy > 0 else 'y+'), chips=0, step=0.10))
    for sx, tag in ((-1, 'L'), (1, 'R')):
        c0, c1, inner = (-0.30, -0.20, '+') if sx < 0 else (0.20, 0.30, '-')
        P += W.course_wall(f'B02_Wall{tag}', 'Y', -0.50, 0.50, c0, c1, inner, 5 + sx, ends=(0.10, 0.10))
        xo = sx * 0.30
        for sy in (-1, 1):   # timber key batten across the pilaster joint, held by two bronze bands
            y = sy * 0.40
            P.append(W.wood_box(f'B02_Key{tag}{sy:+d}', (0.016, 0.036, 0.30), (xo + sx * 0.008, y, 0.20), 'Z'))
            for z in (0.11, 0.30):
                P += W.strap(f'B02_Band{tag}{sy:+d}{z:.2f}', (xo + sx * 0.016, y - 0.021, z), (xo + sx * 0.016, y + 0.021, z), (sx, 0, 0), w=0.030, rivets=1)
                for t in (-1, 1):
                    P += W.strap(f'B02_BandTab{tag}{sy:+d}{z:.2f}{t}', (xo, y + t * 0.019, z), (xo, y + t * 0.046, z), (sx, 0, 0), w=0.030, rivets=1)
    W.bore([(-0.20, -0.50), (0.20, -0.50), (0.20, 0.50), (-0.20, 0.50)])
    W.add_port('End_Front', (0, -0.50, 0), 0.0, P)
    W.add_port('End_Back', (0, 0.50, 0), PI, P)
    wat = W.water_plane('B02_Water', [(-0.20, -0.50), (0.20, -0.50), (0.20, 0.50), (-0.20, 0.50)]); W.ripple_keys(wat); P.append(wat)
    return P, dict(collision=channel_collision(0, 0, 1.00), anim=dict(name='Water_Ripple', frames=48, loop=True, morphs=[('Water', 'Ripple0', [0, 1, 0]), ('Water', 'Ripple1', [1, 0, 1])]),
                   decisions=['End pilaster stones 10 cm, walls between them in two courses; clamps only on outer faces.'])


# ============================================================================ B03 90 degree corner
B03_BORE = ([(-0.40, -0.50), (0.0, -0.50), (0.0, -0.10)] + W.arc(0.10, -0.10, 0.10, PI, PI / 2)[1:] +
            [(0.50, 0.0), (0.50, 0.40), (-0.28, 0.40)] + W.arc(-0.28, 0.28, 0.12, PI / 2, PI)[1:])


@asset('B03', 'CornerTrough', res=2048, budget=14000, size=(1.00, 1.00, 0.40))
def b03():
    M = W.mats(); P = []; S = W.stone
    P += W.course_wall('B03_WallOutL', 'Y', -0.50, 0.0, -0.50, -0.40, '+', 3, ends=(0.10, 0.0))
    P += W.course_wall('B03_WallOutT', 'X', 0.0, 0.50, 0.40, 0.50, '-', 5, ends=(0.0, 0.10))
    corner = [(-0.50, 0.0), (-0.40, 0.0), (-0.40, 0.28)] + W.arc(-0.28, 0.28, 0.12, PI, PI / 2)[1:] + [(0.0, 0.40), (0.0, 0.50), (-0.50, 0.50)]
    P += W.coursed_prism('B03_WallCorner', corner, M['stone'])
    # inner corner: coursed stem and cross walls meeting a small carved fillet stone
    P += W.course_wall('B03_InStem', 'Y', -0.50, -0.10, 0.0, 0.10, '-', 7, ends=(0.10, 0.0))
    P += W.course_wall('B03_InCross', 'X', 0.10, 0.50, -0.10, 0.0, '+', 9, ends=(0.0, 0.10))
    P += W.coursed_prism('B03_InFillet', [(0.0, -0.10), (0.10, -0.10)] + W.arc(0.10, -0.10, 0.10, PI / 2, PI)[:-1], M['stone'])
    f = W.outline_prism('B03_Floor', B03_BORE, 0.0, 0.10, M['stone']); Q.add_bevel(f, 0.006, 2, 35); P.append(f)
    # clamps over the outer joints + ring ears
    P += W.strap('B03_StrapL', (-0.50, 0.0, 0.05), (-0.50, 0.0, 0.36), (-1, 0, 0), rivets=2)
    P += W.strap('B03_StrapT', (0.0, 0.50, 0.05), (0.0, 0.50, 0.36), (0, 1, 0), rivets=2)
    P += W.strap('B03_CrampL', (-0.45, -0.05, 0.40), (-0.45, 0.05, 0.40), (0, 0, 1), w=0.035)
    P += W.strap('B03_CrampT', (-0.05, 0.45, 0.40), (0.05, 0.45, 0.40), (0, 0, 1), w=0.035)
    P += W.strap('B03_StrapIn', (0.10, -0.30, 0.05), (0.10, -0.30, 0.36), (1, 0, 0), rivets=2)
    for nm, loc, n in (('B03_EarL', (-0.50, -0.30, 0.26), (-1, 0, 0)), ('B03_EarT', (0.30, 0.50, 0.26), (0, 1, 0))):
        nv = Vector(n); lug = Q.box(nm + '_lug', (0.05, 0.05, 0.018), Vector(loc) + nv * 0.012, M['bronze'], bevel=0.003)
        lug.rotation_euler = nv.to_track_quat('Z', 'Y').to_euler(); P.append(lug)
        ring = Q.torus(nm + '_ring', 0.030, 0.0055, Vector(loc) + nv * 0.026 - Vector((0, 0, 0.032)), M['bronze'], 24, 8)
        ring.rotation_euler = (Vector((0, 0, 1)).cross(nv) if abs(nv.z) < 0.9 else Vector((1, 0, 0))).to_track_quat('Z', 'Y').to_euler()
        P.append(ring)
    W.bore(B03_BORE)
    W.add_port('In_Front', (-0.20, -0.50, 0), 0.0, P)
    W.add_port('Out_Right', (0.50, 0.20, 0), PI / 2, P)
    wat = W.water_plane('B03_Water', B03_BORE); W.ripple_keys(wat); P.append(wat)
    col = channel_collision(-0.20, -0.25, 0.50) + channel_collision(0.0, 0.20, 1.00, along='X')
    return P, dict(collision=col, anim=dict(name='Water_Ripple', frames=48, loop=True, morphs=[('Water', 'Ripple0', [0, 1, 0]), ('Water', 'Ripple1', [1, 0, 1])]),
                   decisions=['Ports are direction-neutral: a left turn is this mesh placed reversed (rotation only).',
                              'Bore turns on a 0.10 m convex fillet (inner wall) and 0.12 m concave fillet (outer corner).',
                              'Fillet corners are carved one-piece stones per course; straight runs are coursed blocks.'])


# ============================================================================ B04 T junction
B04_BORE = ([(-0.20, -0.50), (0.20, -0.50), (0.20, -0.06)] + W.arc(0.26, -0.06, 0.06, PI, PI / 2)[1:] +
            [(0.60, 0.0), (0.60, 0.40), (-0.60, 0.40), (-0.60, 0.0)] + W.arc(-0.26, -0.06, 0.06, PI / 2, 0)[1:])


@asset('B04', 'TeeTrough', res=2048, budget=16000, size=(1.20, 1.00, 0.40))
def b04():
    M = W.mats(); P = []; S = W.stone
    P += W.course_wall('B04_Back', 'X', -0.60, 0.60, 0.40, 0.50, '-', 3, ends=(0.10, 0.10), joints=(-0.30, 0.30))
    # front walls either side of the stem: coursed stem + cross walls and a small carved fillet stone at each turn
    P += W.course_wall('B04_StemL', 'Y', -0.50, -0.10, -0.30, -0.20, '+', 5, ends=(0.10, 0.0))
    P += W.course_wall('B04_CrossL', 'X', -0.60, -0.30, -0.10, 0.0, '+', 7, ends=(0.10, 0.0))
    P += W.coursed_prism('B04_FilletL', [(-0.30, -0.10), (-0.20, -0.10), (-0.20, -0.06)] + W.arc(-0.26, -0.06, 0.06, 0, PI / 2)[1:-1] + [(-0.26, 0.0), (-0.30, 0.0)], M['stone'])
    P += W.course_wall('B04_StemR', 'Y', -0.50, -0.10, 0.20, 0.30, '-', 9, ends=(0.10, 0.0))
    P += W.course_wall('B04_CrossR', 'X', 0.30, 0.60, -0.10, 0.0, '+', 11, ends=(0.0, 0.10))
    P += W.coursed_prism('B04_FilletR', [(0.20, -0.10), (0.30, -0.10), (0.30, 0.0), (0.26, 0.0)] + W.arc(0.26, -0.06, 0.06, PI / 2, PI)[1:-1] + [(0.20, -0.06)], M['stone'])
    f = W.outline_prism('B04_Floor', B04_BORE, 0.0, 0.10, M['stone']); Q.add_bevel(f, 0.006, 2, 35); P.append(f)
    nose = W.outline_prism('B04_SplitNose', [(-0.11, 0.40), (0.11, 0.40), (0.0, 0.25)], 0.10, 0.185, M['stone_dark'])
    Q.add_bevel(nose, 0.012, 2, 30); P.append(nose)
    # cedar battens and bronze bands on the closed back and on the two front faces
    for x in (-0.30, 0.30):
        P.append(W.wood_box(f'B04_BackBatten{x:+.1f}', (0.06, 0.03, 0.38), (x, 0.515, 0.19), 'Z'))
        P += W.strap(f'B04_BackBattenBand{x:+.1f}', (x - 0.05, 0.53, 0.30), (x + 0.05, 0.53, 0.30), (0, 1, 0), w=0.032, rivets=2)
    P += W.strap('B04_BackBand', (-0.56, 0.50, 0.12), (0.56, 0.50, 0.12), (0, 1, 0), w=0.036, rivets=6)
    for sx in (-1, 1):
        x = sx * 0.45
        P.append(W.wood_box(f'B04_FrontBatten{sx:+d}', (0.06, 0.03, 0.38), (x, -0.115, 0.19), 'Z'))
        P += W.strap(f'B04_FrontBattenBand{sx:+d}', (x - 0.05, -0.13, 0.28), (x + 0.05, -0.13, 0.28), (0, -1, 0), w=0.032, rivets=2)
        P += W.strap(f'B04_StemStrap{sx:+d}', (sx * 0.30, -0.36, 0.05), (sx * 0.30, -0.36, 0.36), (sx, 0, 0), rivets=2)
    W.bore(B04_BORE)
    W.add_port('In_Front', (0, -0.50, 0), 0.0, P)
    W.add_port('Out_Left', (-0.60, 0.20, 0), -PI / 2, P)
    W.add_port('Out_Right', (0.60, 0.20, 0), PI / 2, P)
    wat = W.water_plane('B04_Water', B04_BORE); W.ripple_keys(wat); P.append(wat)
    col = channel_collision(0, -0.30, 0.40) + channel_collision(0, 0.20, 1.20, along='X')
    return P, dict(collision=col, anim=dict(name='Water_Ripple', frames=48, loop=True, morphs=[('Water', 'Ripple0', [0, 1, 0]), ('Water', 'Ripple1', [1, 0, 1])]),
                   decisions=['Exactly three ports; back wall closed and coursed; splitter nose 8.5 cm high below the water surface.'])


# ============================================================================ B05 manual sluice gate (channel insert)
RACK_PITCH = math.pi * 0.004            # module 4 mm
PINION_R = 0.032                        # 16 teeth x 4 mm / 2
RACK_Y = 0.020                          # rack bar centre, set back so the cross shaft runs inside the right post
RACK_FRONT = RACK_Y - 0.020             # tooth face; teeth point downstream (-Y)
AXLE = (0.0, RACK_FRONT - 0.0045 - PINION_R, 0.90)    # pinion centre; the cross shaft runs along +X to the right bank
COUPLING_X = 0.43                       # B06's square tip seats in the coupling sleeve from here outward
GATE_RISE = 0.32
WHEEL_TURN = GATE_RISE / PINION_R      # 10 rad


@asset('B05', 'SluiceGate', res=2048, budget=16000, size=(0.90, 0.30, 1.50))
def b05():
    M = W.mats(); P = []; S = W.stone; G = []
    P.append(S('B05_Floor', (0.40, 0.30, 0.10), (0, 0, 0.05), seed=3, keep=('z-', 'z+', 'x-', 'x+', 'y-', 'y+'), chips=0, bevel=0.006))
    walls = []
    for sx, tag in ((-1, 'L'), (1, 'R')):
        inner = 'x+' if sx < 0 else 'x-'; outer = 'x-' if sx < 0 else 'x+'
        for k, (z0, z1) in enumerate(W.COURSES):   # cheek and abutment laid in the channel courses (22 / 18 cm)
            top = k == len(W.COURSES) - 1
            w = S(f'B05_Wall{tag}_C{k}', (0.10, 0.30, z1 - z0), (sx * 0.25, 0, (z0 + z1) / 2), seed=5 + sx + 7 * k,
                  keep=('z-', inner, 'y-', 'y+', outer) + (('z+',) if top else ()), flat=() if top else ('z+',), chips=0, wear=(0.004, 0.013))
            slot = Q.box(f'Cut_Slot{tag}{k}', (0.034, 0.060, 0.40), (sx * 0.205, 0, 0.30), M['stone'], bevel=0.0); Q.boolean(w, slot)
            walls.append(w); P.append(w)
            P.append(S(f'B05_Abut{tag}_C{k}', (0.15, 0.26, z1 - z0), (sx * 0.375, 0, (z0 + z1) / 2), seed=9 + sx + 7 * k,
                       keep=('z-', inner) + (('z+',) if top else ()), flat=() if top else ('z+',), chips=2 if top else 1, chip_r=(0.02, 0.04), wear=(0.004, 0.013)))
    # timber frame
    tenon = Q.box('Cut_Tenon', (0.86, 0.070, 0.080), (0, 0, 1.34), M['woodX'], bevel=0.0)
    for sx, tag in ((-1, 'L'), (1, 'R')):
        post = W.wood_box(f'B05_Post{tag}', (0.12, 0.12, 1.10), (sx * 0.34, 0, 0.95), 'Z', bevel=0.0)
        Q.boolean(post, tenon); Q.add_bevel(post, 0.007, 2, 40); P.append(post)
        stile = W.wood_box(f'B05_Stile{tag}', (0.08, 0.12, 0.88), (sx * 0.24, 0, 0.84), 'Z', bevel=0.0)
        g = Q.box(f'Cut_Groove{tag}', (0.052, 0.060, 0.90), (sx * 0.20, 0, 0.84), M['woodZ'], bevel=0.0); Q.boolean(stile, g)
        Q.add_bevel(stile, 0.005, 2, 40); P.append(stile)
        # side operating grip at 1.05 m: cedar bar on two bronze lugs
        xo = sx * 0.40
        for z in (0.96, 1.14):
            lug = Q.box(f'B05_GripLug{tag}{z:.2f}', (0.06, 0.03, 0.022), (xo + sx * 0.03, 0, z), M['bronze'], bevel=0.003); P.append(lug)
        P.append(Q.rod(f'B05_Grip{tag}', (xo + sx * 0.055, 0, 0.94), (xo + sx * 0.055, 0, 1.16), 0.016, M['woodZ'], segs=12, bevel=0.006))
        P += W.strap(f'B05_PostShoe{tag}', (sx * 0.40, -0.04, 0.42), (sx * 0.40, -0.04, 0.60), (sx, 0, 0), w=0.05, rivets=2)
        P += W.strap(f'B05_PostShoeB{tag}', (sx * 0.40, 0.04, 0.42), (sx * 0.40, 0.04, 0.60), (sx, 0, 0), w=0.05, rivets=2)
    beam = W.wood_box('B05_TopBeam', (0.56, 0.14, 0.12), (0, 0, 1.34), 'X', bevel=0.0)
    ten = W.wood_box('B05_TopTenon', (0.86, 0.070, 0.080), (0, 0, 1.34), 'X', bevel=0.004)
    slot = Q.box('Cut_RackSlot', (0.056, 0.070, 0.30), (0, RACK_Y - 0.006, 1.34), M['woodX'], bevel=0.0)
    Q.boolean(beam, slot); Q.boolean(ten, slot); Q.add_bevel(beam, 0.007, 2, 40); P += [beam, ten]
    for sx in (-1, 1):
        P.append(W.peg(f'B05_Wedge{sx:+d}', (sx * 0.415, 0, 1.40), (0, 0, 1), r=0.010, L=0.10))
    # cross braces front (below the pinion) and back
    for sy, tag, z in ((-1, 'F', 0.74), (1, 'B', 0.90)):
        P.append(W.wood_box(f'B05_Rail{tag}', (0.80, 0.05, 0.08), (0, sy * 0.085, z), 'X'))
        for sx in (-1, 1):
            P.append(W.peg(f'B05_RailPeg{tag}{sx:+d}', (sx * 0.34, sy * 0.11, z), (0, sy, 0), r=0.008, L=0.06))
    # drive (node Drive): pinion in front of the rack on a cross shaft that runs through the right stile and post to a
    # coupling sleeve over the right bank, where B06 seats, so the wheel is turned from the bank, not from the water
    bore = Q.cyl('Cut_ShaftBore', 0.0135, 0.30, (0.31, AXLE[1], AXLE[2]), M['bronze'], segs=20, rot=(0, PI / 2, 0))
    for o in P:
        if o.name in ('B05_StileR', 'B05_PostR'): Q.boolean(o, bore)
    D = []
    D.append(Q.rod('B05_DriveShaft', (-0.030, AXLE[1], AXLE[2]), (COUPLING_X, AXLE[1], AXLE[2]), 0.012, M['bronze'], segs=16, bevel=0.002))
    pin = Q.prism('B05_Pinion', gear_outline(PINION_R, 16), 0.030, M['bronze'], axis='X', center=0.0, sharp=25)
    pin.location = AXLE; Q.add_bevel(pin, 0.0006, 1, 30); D.append(pin)
    D.append(W.lathe_axis('B05_PinionBoss', [(0.012, -0.022), (0.020, -0.022), (0.020, -0.015), (0.012, -0.015), (0.012, -0.022)], M['bronze'], 'X', segs=20, loc=AXLE))
    D.append(W.lathe_axis('B05_ShaftCollar', [(0.012, -0.006), (0.020, -0.006), (0.020, 0.006), (0.012, 0.006), (0.012, -0.006)], M['bronze'], 'X', segs=20,
                          loc=(0.192, AXLE[1], AXLE[2])))
    sleeve = W.lathe_axis('B05_Coupling', [(0.0, 0.0), (0.024, 0.0), (0.024, 0.040), (0.0, 0.040)], M['bronze'], 'X', segs=24, loc=(COUPLING_X, AXLE[1], AXLE[2]))
    Q.boolean(sleeve, Q.box('Cut_SquareSocket', (0.050, 0.0205, 0.0205), (COUPLING_X + 0.023, AXLE[1], AXLE[2]), M['bronze'], bevel=0.0)); D.append(sleeve)
    Q.tag_node(D, 'Drive'); P += D
    plate = Q.box('B05_BearingR', (0.008, 0.07, 0.08), (0.404, -0.020, AXLE[2]), M['bronze'], bevel=0.002)   # on the post's outer face
    Q.boolean(plate, bore); P.append(plate)
    for dy in (-0.025, 0.025):
        for dz in (-0.028, 0.028):
            P.append(W.rivet(f'B05_BrgRv{dy:+.2f}{dz:+.2f}', (0.408, -0.020 + dy, AXLE[2] + dz), (1, 0, 0), r=0.006))
    # gate panel (node Gate): three cedar planks, bronze edge straps and corner plates, rack on top
    for k in range(3):
        G.append(W.wood_box(f'B05_Plank{k}', (0.44, 0.05, 0.1333), (0, 0, 0.10 + 0.0667 + k * 0.1333), 'X', bevel=0.004))
    for sy in (-1, 1):
        for sx in (-1, 1):
            G += W.strap(f'B05_PanelEdge{sy}{sx}', (sx * 0.185, sy * 0.025, 0.115), (sx * 0.185, sy * 0.025, 0.485), (0, sy, 0), w=0.034, rivets=3)
        G += W.strap(f'B05_PanelBand{sy}', (-0.16, sy * 0.025, 0.30), (0.16, sy * 0.025, 0.30), (0, sy, 0), w=0.030, rivets=2)
    rack = W.wood_box('B05_Rack', (0.040, 0.040, 0.85), (0, RACK_Y, 0.50 + 0.425), 'Z', bevel=0.003); G.append(rack)
    shoe = Q.box('B05_RackShoe', (0.11, 0.062, 0.05), (0, RACK_Y, 0.525), M['bronze'], bevel=0.003); G.append(shoe)
    G.append(Q.box('B05_RackCap', (0.05, 0.05, 0.02), (0, RACK_Y, 1.36), M['bronze'], bevel=0.003))
    tooth = [(RACK_FRONT + 0.0015, -0.0034), (RACK_FRONT - 0.009, -0.0013), (RACK_FRONT - 0.009, 0.0013), (RACK_FRONT + 0.0015, 0.0034)]
    k = 0; z = 0.04 + ((0.40 - 0.04) % RACK_PITCH) + RACK_PITCH / 2
    while z < 0.82:   # teeth on the downstream face, meshing with the pinion in front of the rack
        t = Q.prism(f'B05_Tooth{k}', [(y, zz + 0.50 + z) for y, zz in tooth], 0.03, M['bronze'], axis='X', center=0.0, sharp=20); G.append(t)
        z += RACK_PITCH; k += 1
    G.append(Q.box('B05_ToothStrip', (0.032, 0.004, 0.80), (0, RACK_FRONT - 0.0005, 0.50 + 0.43), M['bronze'], bevel=0.0))
    Q.tag_node(G, 'Gate'); P += G
    W.bore([(-0.20, -0.15), (0.20, -0.15), (0.20, 0.15), (-0.20, 0.15)])
    tg = [P[0]] + walls
    W.add_port('Out_Front', (0, -0.15, 0), 0.0, tg)
    W.add_port('In_Back', (0, 0.15, 0), PI, tg)
    up = W.water_plane('B05_WaterUp', [(-0.20, 0.028), (0.20, 0.028), (0.20, 0.15), (-0.20, 0.15)], subdiv=0.05)
    dn = W.water_plane('B05_WaterDown', [(-0.20, -0.15), (0.20, -0.15), (0.20, -0.028), (-0.20, -0.028)], z=0.13, subdiv=0.05)
    Q.select_only([up, dn], up); bpy_join(); wat = Q.bpy.context.view_layer.objects.active; wat.name = 'B05_Water'; wat['qa_node'] = 'Water'
    wat.shape_key_add(name='Basis'); sk = wat.shape_key_add(name='Open')
    for v, d in zip(wat.data.vertices, sk.data):
        if v.co.y < 0: d.co.z = W.WATER_Z
    P.append(wat)
    col = channel_collision(0, 0, 0.30) + [cbox((s * 0.375, 0, 0.20), (0.15, 0.26, 0.40), 'abutment') for s in (-1, 1)]
    col += [cbox((s * 0.34, 0, 0.95), (0.12, 0.12, 1.10), 'post') for s in (-1, 1)] + [cbox((0, 0, 1.34), (0.86, 0.14, 0.12), 'top beam')]
    col += [cbox((0, 0, 0.30), (0.44, 0.05, 0.40), 'gate panel (moves with node Gate)')]
    return P, dict(collision=col, pivots={'Gate': (0, 0, 0.10), 'Drive': AXLE},
                   anim=dict(name='Gate_Open', frames=48, tracks=[('Gate', 'location', 2, [0.0, GATE_RISE]), ('Drive', 'rotation', 0, [0.0, WHEEL_TURN])],
                             morphs=[('Water', 'Open', [0, 1])]),
                   sockets=[dict(name='WheelMount', position=[COUPLING_X, round(AXLE[1], 5), AXLE[2]], normal=[1, 0, 0], up=[0, 0, 1], type='b06_axle',
                                 note='B06 root (square-tip end) goes here, wheel out over the right bank; the operator stands on the bank at +X. '
                                      'Positive rotation about +X raises the gate.')],
                   mechanism=dict(module_mm=4, pinion_teeth=16, pinion_pitch_radius_m=PINION_R, rack_pitch_m=round(RACK_PITCH, 6),
                                  rise_m=GATE_RISE, wheel_turn_rad=round(WHEEL_TURN, 4), wheel_turns=round(WHEEL_TURN / TAU, 3),
                                  closed_panel_bottom_z=0.10, open_panel_bottom_z=0.42, operating_grip_z=1.05, axle_z=0.90),
                   decisions=['Closed panel bears on the floor (z=0.10) in 22 mm wall slots: no leak gap.',
                              'Wheel moved to the side (user review 2026-10-29): the sheets put the B06 wheel over the water, where nobody can '
                              'stand to turn it. Rack teeth now face downstream; the pinion sits in front of the rack on a cross shaft through '
                              'the right stile and post to a coupling over the right bank. The pinion moved from B06 into B05.'])


def bpy_join():
    Q.bpy.ops.object.join()


# ============================================================================ B06 bronze gate wheel
def gear_outline(r_pitch, teeth, add=0.004, ded=0.005, phase=PI):
    pts = []; rt, rr = r_pitch + add, r_pitch - ded; step = TAU / teeth
    for i in range(teeth):
        c = phase + i * step
        for a, r in ((-0.30, rr), (-0.17, rt), (0.17, rt), (0.30, rr)):
            ang = c + a * step * 1.0
            pts.append((r * math.cos(ang), r * math.sin(ang)))
    return pts


@asset('B06', 'GateWheel', res=1024, budget=9000, size=(0.50, 0.48, 0.50))
def b06():
    """Root = square-tip end of the shaft (seats in B05 socket WheelMount). Axle along +X, wheel out over the right bank,
    operator on the bank at +X. Built along -Y as drawn on the sheet, then turned onto +X at the end."""
    M = W.mats(); P = []
    yw = -0.175      # wheel centre plane
    rim = [(0.214, -0.017), (0.232, -0.023), (0.247, -0.018), (0.251, 0.0), (0.247, 0.018), (0.232, 0.023), (0.214, 0.017), (0.211, 0.0), (0.214, -0.017)]
    P.append(W.lathe_axis('B06_Rim', [(r, z) for r, z in rim], M['bronze'], 'Y', segs=64, loc=(0, yw, 0)))
    fel = [(0.192, -0.013), (0.213, -0.013), (0.213, 0.013), (0.192, 0.013), (0.192, -0.013)]
    P.append(W.lathe_axis('B06_Felloe', fel, M['woodZ'], 'Y', segs=48, loc=(0, yw, 0)))
    for k in range(4):
        a = k * PI / 2; d = Vector((math.cos(a), 0, math.sin(a)))
        sp = Q.lathe(f'B06_Spoke{k}', [(0, 0.045), (0.018, 0.045), (0.016, 0.12), (0.012, 0.20), (0, 0.20)], M['woodZ'], segs=8, sharp=50)
        for v in sp.data.vertices: v.co.y *= 0.65
        sp.rotation_euler = d.to_track_quat('Z', 'Y').to_euler(); sp.location = (0, yw, 0); P.append(sp)
    hub = [(0, -0.032), (0.040, -0.032), (0.050, -0.026), (0.052, -0.012), (0.056, -0.008), (0.056, 0.008), (0.052, 0.012), (0.050, 0.026), (0.030, 0.034), (0, 0.036)]
    P.append(W.lathe_axis('B06_Hub', [(r, -z) for r, z in hub][::-1], M['bronze'], 'Y', segs=40, loc=(0, yw, 0)))
    for k in range(8):
        a = k * TAU / 8
        P.append(W.rivet(f'B06_HubBolt{k}', (0.042 * math.cos(a), yw - 0.022, 0.042 * math.sin(a)), (0, -1, 0), r=0.0065, h=0.006))
    # shaft: hub front (y -0.20) to the 20 mm square coupling (y +0.15) = 0.35 m
    P.append(Q.rod('B06_Shaft', (0, -0.20, 0), (0, 0.11, 0), 0.012, M['bronze'], segs=16, bevel=0.002))
    P.append(Q.box('B06_SquareTip', (0.020, 0.040, 0.020), (0, 0.13, 0), M['bronze'], bevel=0.0015))
    P.append(W.lathe_axis('B06_ThrustCollar', [(0.012, -0.0075), (0.030, -0.0075), (0.032, -0.004), (0.032, 0.004), (0.030, 0.0075), (0.012, 0.0075), (0.012, -0.0075)], M['bronze'], 'Y', segs=28, loc=(0, -0.1325, 0)))
    # rear collar stops the shaft against the B05 coupling sleeve face; the pinion is part of B05 now
    P.append(W.lathe_axis('B06_RearCollar', [(0.012, -0.004), (0.022, -0.004), (0.022, 0.004), (0.012, 0.004), (0.012, -0.004)], M['bronze'], 'Y', segs=20, loc=(0, 0.104, 0)))
    # axial turning grip on the +X spoke at r = 0.18
    P.append(Q.rod('B06_GripStub', (0.18, yw - 0.010, 0), (0.18, yw - 0.032, 0), 0.010, M['bronze'], segs=12))
    grip = [(0, 0), (0.014, 0), (0.019, 0.02), (0.022, 0.06), (0.020, 0.10), (0.016, 0.115), (0, 0.12)]
    g = Q.lathe('B06_Grip', grip, M['woodZ'], segs=16); g.rotation_euler = (PI / 2, 0, 0); g.location = (0.18, yw - 0.032, 0); P.append(g)
    turn = Matrix.Translation((0.15, 0, 0)) @ Matrix.Rotation(PI / 2, 4, 'Z')   # -Y -> +X, square-tip end -> origin
    Q.bpy.context.view_layer.update()
    for o in P: o.matrix_world = turn @ o.matrix_world
    xw = 0.15 - yw
    col = [dict(type='cylinder', axis='X', center=[xw, 0, 0], radius=0.25, height=0.05, note='wheel'),
           dict(type='cylinder', axis='X', center=[0.175, 0, 0], radius=0.015, height=0.35, note='shaft')]
    return P, dict(collision=col, pivots={'Body': (0, 0, 0)}, below=-0.26, preview_lift=0.90,
                   origin_note='root at the square-tip end of the shaft (seats in the B05 coupling), not the base',
                   anim=dict(name='Wheel_RaiseGate', frames=48, tracks=[('Body', 'rotation', 0, [0.0, WHEEL_TURN])]),
                   mechanism=dict(drives='B05 pinion (16 teeth, module 4 mm) through the 20 mm square coupling', wheel_diameter_m=0.50,
                                  shaft_length_m=0.35, square_coupling_mm=20, grip_radius_m=0.18, grip_axis='axial (+X, toward the operator)',
                                  wheel_centre_from_root_m=round(xw, 3), turn_to_raise_rad=round(WHEEL_TURN, 4)),
                   decisions=['Axial grip at r=0.18 (side view), not the radial grip of the front view.',
                              'Side-mounted (user review 2026-10-29): axle across the channel, wheel over the right bank so it is turned from the '
                              'bank. The sheet\'s pinion now lives in B05; B06 is wheel + shaft + 20 mm square tip.'])


# ============================================================================ joint gasket (interface accessory, not one of the 12)
@asset('JG', 'JointGasket', res=512, budget=400, size=(0.522, 0.020, 0.36), ref='B02_three_view.png')
def joint_gasket():
    g = W.gasket('JG_Gasket'); return [g], dict(collision=[], below=0.0, origin_note='port centre on the joint plane, floor bottom z=0',
                                                 decisions=['20 mm installed (23 mm free) clay-fibre U strip; half sits in each module groove.'])
