"""TI01-TI08 builders. Dimensions follow art/references/territory-interior-b/v001/README.md.

Front = -Y. Each builder places parts around the origin; the pipeline re-centres afterwards.
"""
import bpy, math
import numpy as np
from mathutils import Vector, Matrix
from ti_core import (S, box, cyl, sphere, torus, lathe, mesh, surface, extrude_profile, tube, ribbon,
                     leaf_petal, boolean, socket, xf, T, RZ, RX, RY, rng)
import ti_mats as tm

# ---------------------------------------------------------------- palette (linear albedo)
def palette():
    P = {}
    P['wood'] = tm.wood('Aged_Elm', (.07, .033, .015), (.17, .09, .04))            # main frame
    P['wood_board'] = tm.wood('Weathered_Board', (.09, .045, .021), (.20, .11, .052), ring=5.0)
    P['wood_old'] = tm.wood('Polished_Old_Elm', (.06, .028, .013), (.17, .085, .036), rough=.42, wear=.8)
    P['wood_end'] = tm.wood('Raw_Endgrain', (.11, .06, .03), (.22, .13, .07), rough=.8, wear=.2)
    P['brass'] = tm.metal('Aged_Brass', (.34, .22, .085), (.10, .17, .13), rough=.42, patina_amt=.65, hammered=.25)
    P['iron'] = tm.metal('Blackened_Iron', (.07, .065, .06), (.11, .08, .05), rough=.55, patina_amt=.3)
    P['bronze'] = tm.metal('Verdigris_Bronze', (.115, .07, .034), (.09, .17, .14), rough=.55, patina_amt=.55, hammered=.9, patina_scale=48.0, crevice=2.6)
    P['linen'] = tm.cloth('Undyed_Linen', (.30, .27, .21), weave=300)
    P['sage'] = tm.cloth('Sage_Binding', (.08, .12, .09), weave=260)
    P['jade'] = tm.glaze('Pale_Jade', (.20, .32, .27), (.13, .21, .17), rough=.2, crackle=25, mottle=.25)
    P['celadon'] = tm.glaze('Celadon_Glaze', (.16, .29, .23), (.06, .11, .085), rough=.22, crackle=70, mottle=.4)
    P['redglaze'] = tm.glaze('Persimmon_Glaze', (.072, .026, .011), (.03, .011, .005), rough=.34, crackle=60, mottle=.7)
    P['clay'] = tm.plain('Unglazed_Foot', (.30, .18, .10), rough=.85, noise=.25)
    P['rope'] = tm.cloth('Hemp_Cord', (.20, .13, .06), weave=380, rough=.82, sheen=.2)
    P['ink'] = tm.plain('Inkstone_Slate', (.016, .017, .019), rough=.45, noise=.45, bump=.35, scale=35.0)
    P['inkwet'] = tm.plain('Wet_Ink', (.01, .01, .012), rough=.08)
    P['bamboo'] = tm.wood('Brush_Bamboo', (.26, .17, .07), (.42, .30, .13), ring=2.0, rough=.4, wear=.3)
    P['hair'] = tm.plain('Brush_Hair', (.03, .025, .02), rough=.7, noise=.4)
    P['ring_stain'] = tm.plain('Old_Ring_Stain', (.035, .017, .008), rough=.35, noise=.3)
    P['coal'] = tm.plain('Ash_Bed', (.05, .045, .04), rough=.95, noise=.5, scale=60)
    return P

# ---------------------------------------------------------------- shared shapes
def cloud_bracket(name, w, h, t, mat, p, rot, **kw):
    """Corner spandrel: right angle with a concave cloud curve, outline in its local x/z."""
    pts = [(0, 0), (w, 0)]
    for i in range(1, 12):
        a = i / 12
        x = w * (1 - a); z = h * a
        bulge = .22 * math.sin(math.pi * a) * min(w, h) + .05 * math.sin(3 * math.pi * a) * min(w, h)
        pts.append((x * (1 - .0) - bulge * .7, z - bulge * .7))
    pts.append((0, h))
    pts = [(-x, -z) for x, z in pts]       # hangs down-left from the corner
    return extrude_profile(name, pts[::-1], t, mat, 'xz', p, rot, bevel=.0015, **kw)

def rivet(name, p, r, mat, axis='y', **kw):
    kw.setdefault('detail', 2)
    return sphere(name, p, r, mat, scale=(1, .45, 1) if axis == 'y' else ((.45, 1, 1) if axis == 'x' else (1, 1, .45)), seg=10, ring=6, **kw)

def corner_plate(p, w, h, mat, P, face='-y', rivets=2, **kw):
    t = .004
    if face == '-y':
        box('Brass_Corner_Plate', (p[0], p[1] - t / 2, p[2]), (w, t, h), mat, bevel=.0012, detail=1, **kw)
        for i in range(rivets):
            z = p[2] + (i - (rivets - 1) / 2) * h * .55
            rivet('Plate_Rivet', (p[0], p[1] - t, z), .0045, mat)

# ================================================================ TI01 博古架
SHELF = dict(W=1.66, D=.38, stile=.055, board=.03, rows=[(.40, .80), (.38, .66), (.42, .86), (.39, .70)])

def ti01_bogu_shelf(P, with_sockets=True):
    W, D, st, bt = SHELF['W'], SHELF['D'], SHELF['stile'], SHELF['board']
    y0, y1 = -D / 2, D / 2
    xi = W / 2 - st                             # interior half width .775
    wood, board, old = P['wood'], P['wood_board'], P['wood_old']
    # corner stiles run to the floor as legs
    for sx in (-1, 1):
        for sy in (-1, 1):
            box('Corner_Stile', (sx * (W / 2 - st / 2), sy * (D / 2 - st / 2), .925), (st, st, 1.85), wood, .004, grain='z')
            # brass shoe on each foot
            box('Brass_Foot_Shoe', (sx * (W / 2 - st / 2), sy * (D / 2 - st / 2), .021), (st + .008, st + .008, .042), P['brass'], .0015, detail=1)
    # bottom board, apron and cloud-cut skirt brackets
    z = .11
    box('Bottom_Board', (0, (y0 + y1) / 2 - .005, z + bt / 2), (2 * xi + .01, D - .02, bt), board, .003)
    ap = [(-xi, z), (xi, z), (xi, z - .05)]
    for k in range(1, 48):
        x = xi - 2 * xi * k / 48; u = abs(x) / xi
        ap.append((x, z - .05 + (.022 * abs(math.sin(math.pi * 3 * x / xi)) ** 1.6 if u < .82 else 0)))
    ap.append((-xi, z - .05))
    extrude_profile('Front_Apron_Cloud', ap[::-1], .022, wood, 'xz', (0, y0 + .012, 0), bevel=.002)
    box('Rear_Apron', (0, y1 - .012, z - .025), (2 * xi, .022, .05), wood, .003)
    for sx in (-1, 1):
        box('Side_Apron', (sx * xi, 0, z - .025), (.022, D - 2 * st, .05), wood, .003, grain='y')
        cloud_bracket('Skirt_Bracket', .075, .045, .018, wood, (sx * xi, y0 + .012, z - .05), (0, 0, 0 if sx > 0 else math.pi), detail=1)
    # rows, from the bottom row 4 up to row 1; rows list is bottom->top: (height, left width)
    rows = SHELF['rows']; S['shelf_cells'] = []
    zf = z + bt                                 # floor of the current row
    row_floors = []
    for ri, (hgt, lw) in enumerate(rows):
        row_floors.append((zf, hgt, lw))
        ztop = zf + hgt
        # board above this row (top board for row 1 is the cap board)
        box('Shelf_Board', (0, (y0 + y1) / 2 - .005, ztop + bt / 2), (2 * xi + .01, D - .02, bt), board, .003)
        box('Shelf_Front_Lip', (0, y0 + .006, ztop + bt / 2), (2 * xi, .014, bt + .006), wood, .0025)
        # divider in this row
        dx = -xi + lw + .02
        box('Cell_Divider', (dx, (y0 + y1) / 2 - .005, zf + hgt / 2), (.04, D - .03, hgt), wood, .003, grain='z')
        # brass corner plates on the front stiles at each shelf level
        for sx in (-1, 1):
            corner_plate((sx * (W / 2 - st / 2), y0, ztop + bt / 2), .036, .06, P['brass'], P)
        corner_plate((dx, y0 + .008, ztop - .03), .03, .05, P['brass'], P, rivets=1)
        # cloud spandrels in the top corners of both cells, flush with the front plane
        for cx0, cx1 in ((-xi, dx - .02), (dx + .02, xi)):
            cloud_bracket('Cell_Spandrel', .055, .04, .014, wood, (cx1, y0 + .016, ztop), (0, 0, 0), detail=1)
            cloud_bracket('Cell_Spandrel', .055, .04, .014, wood, (cx0, y0 + .016, ztop), (0, 0, math.pi), detail=1)
        zf = ztop + bt
    S['shelf_row_floors'] = row_floors
    # frieze and stepped cornice up to 1.96
    zc = zf                                    # 1.85
    box('Cornice_Frieze', (0, y0 - .002, zc + .03), (W, .03, .06), wood, .004)
    box('Cornice_Frieze_Side', (0, .005, zc + .03), (W - .002, D - .02, .06), wood, .003)
    box('Cornice_Bed_Mould', (0, .005, zc + .07), (1.72, .40, .02), board, .006)
    box('Cornice_Cap', (0, .005, zc + .095), (1.76, .42, .03), wood, .008)
    for sx in (-1, 1):
        corner_plate((sx * (W / 2 - .02), y0 - .017, zc + .03), .03, .05, P['brass'], P, rivets=1)
    # side frame-and-panel
    for sx in (-1, 1):
        x = sx * (W / 2 - .012)
        for zz in [r[0] - bt / 2 for r in row_floors[1:]] + [zc - .015]:
            box('Side_Rail', (x, 0, zz), (.024, D - 2 * st + .004, .045), wood, .003, grain='y')
        box('Side_Panel', (sx * (W / 2 - .02), 0, (z + zc) / 2), (.012, D - 2 * st, zc - z), board, .002, grain='z')
    # back: vertical tongue-and-groove planks with rear frame
    n = 12; pw = (2 * xi) / n
    for i in range(n):
        x = -xi + pw * (i + .5)
        box('Back_Plank', (x, y1 - .018, (z + zc) / 2), (pw - .003, .016, zc - z), old if (i < 3) else board, .0015, grain='z')
    for zz in [r[0] - bt / 2 for r in row_floors[1:]]:
        box('Rear_Rail', (0, y1 - .004, zz), (2 * xi, .02, .05), wood, .003)
    box('Rear_Mullion', (0, y1 - .004, (z + zc) / 2), (.05, .02, zc - z), wood, .003, grain='z')
    # slot 1 (top-left) shows long use: polished floor, faint ring stain, worn lip
    zf1, h1, lw1 = row_floors[-1]
    cx = -xi + lw1 / 2
    box('Slot1_Worn_Floor', (cx, (y0 + y1) / 2 - .005, zf1 - .0006), (lw1 - .004, D - .03, .0016), old, .0005)
    lathe('Slot1_Ring_Stain', [(.078, 0), (.092, 0)], (cx - .03, -.01, zf1 + .0012), P['ring_stain'], seg=48, detail=1)
    # sockets: one per cell, numbered top->bottom, left->right
    k = 0
    for zf_, hgt, lw in reversed(row_floors):
        dx = -xi + lw + .02
        for cx0, cx1 in ((-xi, dx - .02), (dx + .02, xi)):
            k += 1
            c = ((cx0 + cx1) / 2, (y0 + (y1 - .026)) / 2, zf_)
            S['shelf_cells'].append({'slot': k, 'x0': cx0, 'x1': cx1, 'y0': y0, 'y1': y1 - .026, 'z0': zf_, 'z1': zf_ + hgt})
            if with_sockets: socket(f'SOCKET_slot_{k}', c)

# ================================================================ TI02 守溫小丹爐
def ti02_home_furnace(P):
    br, wood = P['bronze'], P['wood']
    cx, cy = -.11, .08
    with xf(T(cx, cy, 0)):
        # four scroll legs
        for i in range(4):
            a = math.radians(45 + 90 * i); ca, sa = math.cos(a), math.sin(a)
            pts = [(.17 * ca, .17 * sa, .20), (.23 * ca, .23 * sa, .17), (.245 * ca, .245 * sa, .11), (.22 * ca, .22 * sa, .05),
                   (.235 * ca, .235 * sa, .02)]
            tube('Scroll_Leg', pts, .036, br, radii=[1.25, 1.15, .85, .7, .8], grain='z')
            torus('Leg_Scroll_Foot', (.255 * ca, .255 * sa, .026), .026, .013, br, rot=(math.pi / 2, 0, a + math.pi / 2), detail=1)
            torus('Leg_Knee_Curl', (.25 * ca, .25 * sa, .16), .026, .012, br, rot=(math.pi / 2, 0, a + math.pi / 2), detail=1)
            box('Leg_Mount_Plate', (.2 * ca, .2 * sa, .19), (.07, .02, .05), br, .006, rot=(0, 0, a + math.pi / 2))
        # firebox drum with an arched opening at the front
        drum = lathe('Firebox_Drum', [(0, .16), (.215, .16), (.235, .17), (.235, .19), (.212, .205), (.205, .33), (.215, .355), (.205, .38), (0, .38)], (0, 0, 0), br, seg=64)
        arch = [(-.085, .175), (.085, .175)] + [(.085 * math.cos(t), .27 + .085 * math.sin(t)) for t in [math.pi * k / 16 for k in range(17)]]
        cut = extrude_profile('Arch_Cutter', arch, .40, None, 'xz', (0, -.2, 0), bevel=0)
        boolean(drum, cut)
        hollow = lathe('Firebox_Hollow', [(0, .175), (.17, .175), (.17, .345), (0, .345)], (0, 0, 0), br, seg=48)
        boolean(drum, hollow)
        # soot-dark inner wall, open where the arch is (sweep skips the front)
        a0 = -math.pi / 2 + math.asin(.088 / .172)
        surface('Firebox_Inner_Wall', 40, 3, lambda u, v: (.172 * math.cos(a0 + u * (math.tau - 2 * (a0 + math.pi / 2))),
                                                            .172 * math.sin(a0 + u * (math.tau - 2 * (a0 + math.pi / 2))), .176 + .168 * v),
                P['coal'], grain='z')
        # flat-bottomed arch frame hugging the curved drum wall
        def on_drum(x, z, out=.006): return (x, -math.sqrt(max(.207 ** 2 - x * x, 0)) - out, z)
        ap = [on_drum(-.096, .178)] + [on_drum(-.096 * math.cos(t), .27 + .096 * math.sin(t)) for t in [math.pi * k / 20 for k in range(21)]] + [on_drum(.096, .178)]
        tube('Arch_Frame', ap, .012, br, grain='z')
        box('Arch_Sill', (0, -.21, .174), (.23, .05, .02), br, .005)
        for t in range(7):
            ang = math.pi * (t + .5) / 7
            rivet('Arch_Rivet', on_drum(.113 * math.cos(ang), .27 + .113 * math.sin(ang), .011), .0065, br)
        for sx in (-1, 1):
            rivet('Arch_Rivet', on_drum(sx * .113, .2, .011), .0065, br)
        # ember bed: ash, grate and coals (cold); fire insert is its own group
        lathe('Ash_Bed', [(0, .176), (.16, .176), (.15, .19), (0, .195)], (0, 0, 0), P['coal'], seg=32)
        for i in range(-3, 4):
            box('Grate_Bar', (i * .035, -.04, .2), (.012, .22, .01), P['iron'], .002, grain='y', detail=1)
        r_ = rng()
        for i in range(9):
            sphere('Cold_Coal', (r_.uniform(-.09, .09), r_.uniform(-.12, .05), .21), r_.uniform(.018, .03), P['coal'],
                   scale=(1.2, 1, .7), seg=10, ring=6, detail=1)
        fire_m = tm.emissive('Ember_Glow', (.04, .025, .015), (1.0, .42, .10), 'FireInsert')
        flame_m = tm.flame('Flame_Tongue', 'FireInsert')
        for i in range(7):
            sphere('Ember_Coal', (r_.uniform(-.08, .08), r_.uniform(-.11, .03), .222), r_.uniform(.018, .026), fire_m,
                   scale=(1.25, 1, .7), seg=10, ring=6, group='Fire')
        for i, (fx, fh) in enumerate([(-.04, .09), (.0, .12), (.045, .08), (.02, .065), (-.065, .06)]):
            prof = [(0, 0), (.024, .008), (.026, .025), (.018, fh * .55), (.008, fh * .85), (0, fh)]
            o = lathe('Flame', prof, (fx, -.05 + .02 * (i % 2), .215), flame_m, seg=12, group='Fire', scale=(1, .55, 1))
            o.rotation_euler = (0, .12 * (i - 2), 0)
        socket('SOCKET_fire_light', (0, -.05, .27))
        # perforated vent collar
        collar = lathe('Vent_Collar', [(0, .38), (.20, .38), (.205, .39), (.20, .44), (.215, .445), (0, .445)], (0, 0, 0), br, seg=64)
        for i in range(14):
            a = math.tau * (i + .5) / 14
            boolean(collar, cyl('Vent_Hole_Cut', (.2 * math.cos(a), .2 * math.sin(a), .413), .011, .03, P['coal'],
                                rot=(math.pi / 2, 0, a + math.pi / 2), bevel=0))
        # globular body
        prof = [(0, .44), (.19, .44), (.22, .46)]
        for k in range(1, 12):
            t = k / 12; z = .46 + t * .34
            prof.append((.22 + .055 * math.sin(math.pi * t) ** .8 - .03 * t, z))
        prof += [(.195, .815), (.205, .83), (.205, .85), (0, .85)]
        body = lathe('Globular_Body', prof, (0, 0, 0), br, seg=72)
        for z, r in ((.47, .232), (.79, .207)):
            torus('Body_Band', (0, 0, z), r, .011, br)
            for i in range(16):
                a = math.tau * i / 16
                rivet('Band_Rivet', ((r + .01) * math.cos(a), (r + .01) * math.sin(a), z), .006, br, axis='z')
        # front lotus relief and trefoil vent
        for k in range(-2, 3):
            ang = k * .42
            base = (0, -.276, .55); tip = (.15 * math.sin(ang), -.274 + .03 * abs(k), .55 + .14 * math.cos(ang))
            leaf_petal('Lotus_Petal', base, tip, .045 - .005 * abs(k), br, lift=.18)
        # rear ventilation plate with slots
        box('Rear_Vent_Plate', (0, .268, .60), (.16, .012, .11), br, .006)
        for zz in (.575, .60, .625):
            box('Rear_Vent_Slot', (0, .273, zz), (.11, .008, .012), P['coal'], .002)
        # ring handles on both sides
        for sx in (-1, 1):
            box('Handle_Lug', (sx * .262, 0, .74), (.035, .04, .05), br, .006)
            torus('Handle_Ring', (sx * .29, 0, .69), .055, .011, br, rot=(0, math.pi / 2, 0))
        # removable lid + lotus-bud finial (own group so it can be lifted)
        lid = [(0, .85), (.215, .85), (.225, .862), (.215, .875), (.18, .88), (.16, .91), (.12, .935), (.075, .95), (.06, .955), (0, .955)]
        lathe('Lid_Dome', lid, (0, 0, 0), br, seg=64, group='Lid')
        torus('Lid_Rim_Band', (0, 0, .87), .205, .008, br, group='Lid')
        lathe('Lid_Tier', [(0, .955), (.075, .955), (.07, .975), (.045, .98), (0, .98)], (0, 0, 0), br, seg=48, group='Lid')
        bud = [(0, .98), (.022, .985), (.032, 1.0), (.034, 1.02), (.026, 1.04), (.012, 1.055), (0, 1.062)]
        lathe('Lotus_Bud_Finial', bud, (0, 0, 0), br, seg=24, group='Lid')
        for k in range(5):
            a = math.tau * k / 5
            leaf_petal('Finial_Petal', (.02 * math.cos(a), .02 * math.sin(a), .99), (.04 * math.cos(a), .04 * math.sin(a), 1.035), .016, br, lift=.0, group='Lid', detail=1)
    # medicine bottle tray (front right)
    with xf(T(.215, -.32, 0)):
        tw, td = .24, .17
        box('Tray_Base', (0, 0, .03), (tw, td, .02), wood, .003)
        for sx in (-1, 1):
            for sy in (-1, 1):
                box('Tray_Foot', (sx * (tw / 2 - .015), sy * (td / 2 - .015), .01), (.025, .025, .02), wood, .003, grain='z')
        for sy in (-1, 1):
            box('Tray_Rail', (0, sy * (td / 2 - .006), .075), (tw, .012, .012), wood, .002)
            box('Tray_Lattice_Low', (0, sy * (td / 2 - .006), .045), (tw - .01, .008, .008), wood, .0015)
            for i in range(-2, 3):
                box('Tray_Lattice_Post', (i * .045, sy * (td / 2 - .006), .06), (.008, .008, .03), wood, .0015, grain='z', detail=1)
        for sx in (-1, 1):
            box('Tray_End', (sx * (tw / 2 - .006), 0, .06), (.012, td, .05), wood, .002, grain='y')
            box('Tray_Handle_Post', (sx * (tw / 2 - .006), 0, .14), (.016, .016, .17), wood, .003, grain='z')
        box('Tray_Handle_Bar', (0, 0, .222), (tw + .01, .02, .02), wood, .004)
        for i, (bx, by, s) in enumerate([(-.07, -.02, 1.0), (.0, .03, .9), (.07, -.025, .8)]):
            prof = [(0, 0), (.032 * s, 0), (.036 * s, .03 * s), (.034 * s, .065 * s), (.016 * s, .085 * s), (.014 * s, .095 * s), (0, .095 * s)]
            lathe('Medicine_Bottle', prof, (bx, by, .04), P['celadon'], seg=28)
            lathe('Bottle_Stopper', [(0, .093 * s), (.017 * s, .093 * s), (.018 * s, .11 * s), (0, .113 * s)], (bx, by, .04), wood, seg=16)

# ================================================================ TI03 行記書案與椅凳
def ti03_journal_desk(P, page_img):
    wood, board, brass = P['wood'], P['wood_board'], P['brass']
    L, Dp, top_z = 1.20, .56, .72
    # top panel with breadboard ends and everted (upturned) flanges
    top = box('Desk_Top_Panel', (0, 0, top_z - .0175), (L - .08, Dp, .035), board, .004)
    for sx in (-1, 1):
        box('Breadboard_End', (sx * (L / 2 - .02), 0, top_z - .0175), (.04, Dp, .035), wood, .004, grain='y')
        prof = [(0, 0), (.04, 0), (.05, .02), (.07, .035), (.075, .05), (.062, .058), (.045, .045), (.03, .03), (0, .03)]
        pts = [(sx * (L / 2 - .04 + x), z) for x, z in prof]
        if sx < 0: pts = pts[::-1]
        extrude_profile('Everted_Flange', pts, Dp, wood, 'xz', (0, 0, top_z), bevel=.003, grain='y')
    # old knife scratch across the top (geometry groove + raw wood inside)
    sc_m = P['wood_end']
    pts = [(.03 + .36 * t, .14 - .09 * t - .03 * math.sin(t * math.pi), top_z) for t in [i / 14 for i in range(15)]]
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        mid = Vector(a).lerp(Vector(b), .5); d = Vector(b) - Vector(a)
        c = box('Scratch_Cutter', (mid.x, mid.y, top_z), (d.length + .004, .0028 * (1 - abs(i - 7) / 9), .004), sc_m, 0, rot=(0, 0, math.atan2(d.y, d.x)))
        boolean(top, c)
    # legs (slight splay), aprons, spandrels, stretchers
    lx, ly = L / 2 - .09, Dp / 2 - .045
    for sx in (-1, 1):
        for sy in (-1, 1):
            box('Desk_Leg', (sx * (lx + .006), sy * ly, (top_z - .035) / 2), (.045, .045, top_z - .035), wood, .005,
                rot=(sy * .018, -sx * .03, 0), grain='z')
        for zz in (.11, .30):
            box('Side_Stretcher', (sx * (lx + (.002 if zz > .2 else .008)), 0, zz), (.03, 2 * ly, .035), wood, .004, grain='y')
        box('Side_Apron', (sx * lx, 0, top_z - .075), (.022, 2 * ly - .04, .08), wood, .003, grain='y')
    for sy in (-1, 1):
        box('Long_Apron', (0, sy * (ly + .002), top_z - .075), (2 * lx - .04, .022, .08), wood, .003)
        for sx in (-1, 1):
            cloud_bracket('Leg_Spandrel', .09, .07, .018, wood, (sx * (lx - .025), sy * (ly + .002), top_z - .115),
                          (0, 0, 0 if sx > 0 else math.pi), detail=1)
    box('Rear_Stretcher', (0, ly, .11), (2 * lx, .03, .035), wood, .004)
    # two front drawers with ring pulls
    for sx in (-1, 1):
        x = sx * .26
        box('Drawer_Front', (x, -ly - .014, top_z - .072), (.40, .016, .07), board, .003)
        box('Drawer_Box', (x, -ly + .14, top_z - .072), (.39, .28, .065), board, .002, detail=1)
        cyl('Pull_Backplate', (x, -ly - .024, top_z - .072), .02, .004, brass, axis='y', verts=6, detail=1)
        torus('Drawer_Ring_Pull', (x, -ly - .03, top_z - .09), .016, .0035, brass, rot=(math.pi / 2, 0, 0))
    # desk objects ---------------------------------------------------------
    # inkstone with well
    stone = lathe('Inkstone', [(0, 0), (.098, 0), (.103, .006), (.104, .024), (.098, .031), (.092, .032), (0, .032)], (-.17, .06, top_z), P['ink'], seg=40, scale=(1, .7, 1))
    well = cyl('Ink_Well_Cut', (-.22, .06, top_z + .03), .035, .03, P['inkwet'], verts=32)
    boolean(stone, well)
    pool = box('Ink_Grind_Cut', (-.13, .06, top_z + .031), (.09, .095, .012), P['inkwet'], .01)
    boolean(stone, pool)
    cyl('Ink_Pool', (-.22, .06, top_z + .018), .033, .002, P['inkwet'], verts=32, detail=1)
    # brush rack with two brushes, top at 0.84
    rx, ry = -.43, .11
    box('Brush_Rack_Base', (rx, ry, top_z + .008), (.17, .055, .016), P['wood'], .003)
    for sx in (-1, 1):
        box('Brush_Rack_Post', (rx + sx * .07, ry, top_z + .06), (.014, .02, .09), P['wood'], .002, grain='z')
        box('Brush_Rack_Cap', (rx + sx * .07, ry, top_z + .108), (.02, .03, .01), P['wood'], .002)
        for k, zz in enumerate((.085, .104)):
            box('Brush_Rest_Notch', (rx + sx * .07, ry + (-.006 if k else .006), top_z + zz - .002), (.016, .006, .006), P['wood_end'], .001, detail=2)
    for k, (zz, dy) in enumerate(((.093, .006), (.112, -.006))):
        cyl('Brush_Handle', (rx + .02 * k, ry + dy, top_z + zz), .0055, .21, P['bamboo'], axis='x', verts=12)
        cyl('Brush_Ferrule', (rx + .02 * k + .11, ry + dy, top_z + zz), .0068, .02, P['bamboo'], axis='x', verts=12)
        o = cyl('Brush_Tip', (rx + .02 * k + .14, ry + dy, top_z + zz), .0068, .04, P['hair'], axis='x', verts=12, r2=.0005)
    # open journal (page faces use their own UV and material so text can be swapped later)
    page_m = tm.image_mat('Journal_Page_Blank', page_img, 'JournalPage', rough=.86)
    jx, jy = .22, -.03
    with xf(T(jx, jy, top_z) @ RZ(.06)):
        for sx in (-1, 1):
            box('Journal_Cover', (sx * .1, 0, .003), (.2, .27, .006), P['sage'], .0015, rot=(0, sx * -.025, 0))
            box('Page_Block', (sx * .093, 0, .012), (.18, .255, .012), P['linen'], .0015, rot=(0, sx * -.03, 0))
        def page(u, v):
            x = (u - .5) * .37; z = .02 + .012 * math.sin(math.pi * min(1, abs(x) / .185)) ** .6 - .02 * (1 - min(1, abs(x) / .01)) * .0
            z += .004 * math.sin(math.pi * u) - .006 * math.exp(-(x / .012) ** 2)
            return (x, (v - .5) * .25, z)
        surface('Journal_Pages', 24, 4, page, page_m, uvfn=lambda u, v: (u, v), grain='y')
        box('Journal_Spine', (0, 0, .004), (.012, .27, .008), P['sage'], .002)
        socket('SOCKET_journal', (0, 0, .03))
    # bookmark ribbon draped over the front edge, jade bead and tassel
    rb = [(.30, -.03, top_z + .028), (.31, -.17, top_z + .02), (.30, -.28, top_z + .004), (.30, -.285, top_z - .04), (.30, -.29, top_z - .09)]
    ribbon('Bookmark_Ribbon', rb, .006, P['sage'], .0012)
    sphere('Jade_Bead', (.30, -.292, top_z - .1), .009, P['jade'], seg=16, ring=10)
    for k in range(7):
        a = math.tau * k / 7
        tube('Tassel_Thread', [(.30, -.292, top_z - .108), (.30 + .006 * math.cos(a), -.292 + .006 * math.sin(a), top_z - .15)], .0018, P['sage'], detail=2)
    # stool tucked under the front
    with xf(T(0, -.21, 0)):
        sw, sd, sh = .46, .34, .42
        box('Stool_Seat_Frame', (0, 0, sh - .02), (sw, sd, .04), wood, .006)
        box('Stool_Seat_Cushion', (0, 0, sh + .004), (sw - .06, sd - .06, .022), P['linen'], .008)
        for sx in (-1, 1):
            for sy in (-1, 1):
                box('Stool_Leg', (sx * (sw / 2 - .03), sy * (sd / 2 - .03), (sh - .04) / 2), (.035, .035, sh - .04), wood, .004, grain='z')
            box('Stool_Side_Stretcher', (sx * (sw / 2 - .03), 0, .09), (.022, sd - .06, .025), wood, .003, grain='y')
        for sy in (-1, 1):
            box('Stool_Apron', (0, sy * (sd / 2 - .03), sh - .07), (sw - .08, .018, .05), wood, .003)
            for sx in (-1, 1):
                cloud_bracket('Stool_Spandrel', .05, .04, .014, wood, (sx * (sw / 2 - .05), sy * (sd / 2 - .03), sh - .095), (0, 0, 0 if sx > 0 else math.pi), detail=1)
        box('Stool_Long_Stretcher', (0, 0, .09), (sw - .06, .022, .025), wood, .003)
        socket('SOCKET_seat', (0, 0, sh + .015))

# ================================================================ TI04 歸明燈架
def ti04_paper_lamp(P):
    wood, brass, jade = P['wood'], P['brass'], P['jade']
    paper_m = tm.paper('Lamp_Shade_Paper', (.47, .39, .25), 'ShadePaper')
    # base: feet, plinth, two steps
    for sx in (-1, 1):
        for sy in (-1, 1):
            box('Cloud_Foot', (sx * .17, sy * .17, .012), (.07, .07, .024), wood, .004, grain='z')
    box('Base_Plinth', (0, 0, .05), (.42, .42, .052), wood, .006)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box('Base_Corner_Cap_X', (sx * .2085, sy * .19, .05), (.005, .04, .054), brass, .0015, detail=1)
            box('Base_Corner_Cap_Y', (sx * .19, sy * .2085, .05), (.04, .005, .054), brass, .0015, detail=1)
            rivet('Base_Rivet', (sx * .195, sy * .211, .05), .004, brass)
    box('Base_Step_2', (0, 0, .097), (.30, .30, .042), P['wood_board'], .005)
    box('Base_Step_3', (0, 0, .133), (.18, .18, .03), wood, .004)
    for sx in (-1, 1):
        box('Shaft_Brace', (sx * .05, 0, .18), (.03, .09, .06), wood, .004, grain='z')
    # twin shaft posts with connectors and a jade band
    for sx in (-1, 1):
        box('Shaft_Post', (sx * .022, 0, .6), (.032, .04, .9), wood, .003, grain='z')
    for zz in (.30, .46, .80, .95):
        box('Shaft_Connector', (0, 0, zz), (.024, .03, .03), P['wood_board'], .002, detail=1)
    box('Jade_Band', (0, 0, .64), (.094, .056, .06), jade, .006)
    # key-fret brackets under the shade
    for sx in (-1, 1):
        box('Fret_Arm', (sx * .07, 0, 1.03), (.10, .022, .018), wood, .002)
        box('Fret_Drop', (sx * .115, 0, 1.005), (.018, .022, .05), wood, .002, grain='z', detail=1)
    for sy in (-1, 1):
        box('Fret_Arm_Y', (0, sy * .07, 1.03), (.022, .10, .018), wood, .002, grain='y')
        box('Fret_Drop_Y', (0, sy * .115, 1.005), (.022, .018, .05), wood, .002, grain='z', detail=1)
    # tapered shade frame: bottom 0.40 square at 1.06, top 0.27 square at 1.47
    zb, zt, hb, ht = 1.06, 1.47, .195, .13
    for sx in (-1, 1):
        box('Shade_Bottom_Rail', (0, sx * hb, zb), (2 * hb + .02, .02, .022), wood, .003)
        box('Shade_Bottom_Rail', (sx * hb, 0, zb), (.02, 2 * hb + .02, .022), wood, .003, grain='y')
        box('Shade_Top_Rail', (0, sx * ht, zt), (2 * ht + .02, .018, .02), wood, .003)
        box('Shade_Top_Rail', (sx * ht, 0, zt), (.018, 2 * ht + .02, .02), wood, .003, grain='y')
    for sx in (-1, 1):
        for sy in (-1, 1):
            tube('Shade_Corner_Post', [(sx * hb, sy * hb, zb), (sx * ht, sy * ht, zt)], .011, wood, res=2, grain='z')
            box('Shade_Corner_Cap', (sx * hb, sy * hb, zb - .004), (.034, .034, .03), brass, .003)
            rivet('Shade_Cap_Rivet', (sx * (hb + .0175), sy * hb, zb - .004), .004, brass, axis='x')
    # paper panels and two thin slats per face
    for face in range(4):
        with xf(RZ(face * math.pi / 2)):
            inset = .006
            v = [(-hb + .012, -hb + inset, zb + .011), (hb - .012, -hb + inset, zb + .011), (ht - .011, -ht + inset, zt - .01), (-ht + .011, -ht + inset, zt - .01)]
            mesh('Shade_Paper_Panel', v, [(0, 1, 2, 3)], paper_m, solid=.002, grain='z')
            for f in (-1 / 3, 1 / 3):
                tube('Shade_Slat', [(f * 2 * hb, -hb - .001, zb + .01), (f * 2 * ht, -ht - .001, zt - .01)], .0055, wood, res=2, grain='z', detail=1)
    # top cap: crossed bars with upturned ends, collar, finial block (top = 1.64)
    for ang in (0, math.pi / 2):
        with xf(RZ(ang)):
            box('Cap_Cross_Bar', (0, 0, 1.495), (.36, .03, .03), wood, .004)
            for sx in (-1, 1):
                tube('Cap_Upturned_End', [(sx * (.16 + .03 * math.sin(t)), 0, 1.495 + .028 * (1 - math.cos(t))) for t in [k * math.pi / 2 / 6 for k in range(7)]],
                     .014, wood, radii=[1, 1, .95, .9, .82, .74, .66], grain='x')
    box('Cap_Hub', (0, 0, 1.53), (.06, .06, .05), wood, .005, grain='z')
    box('Cap_Jade_Collar', (0, 0, 1.567), (.05, .05, .024), jade, .004)
    box('Cap_Finial_Block', (0, 0, 1.6), (.04, .04, .045), brass, .005)
    box('Cap_Finial_Top', (0, 0, 1.6315), (.026, .026, .017), brass, .004)
    socket('SOCKET_lamp_light', (0, 0, 1.26))

# ================================================================ TI05 遠岫屏風
def ti05_landscape_screen(P, paint_img):
    wood, brass = P['wood'], P['wood']
    paint_m = tm.image_mat('Painted_Linen_Front', paint_img, 'PaintedLinen', rough=.9)
    w, gap, theta = .582, .006, math.radians(16)
    H = 1.70
    def panel(idx, outer_left, outer_right):
        st, rt = .036, .03     # stile width (x) / depth (y)
        for x, outer in ((st / 2, outer_left), (w - st / 2, outer_right)):
            box('Screen_Stile', (x, 0, H / 2 + .01), (st, rt, H - .02), wood, .004, grain='z')
            lathe('Stile_Cap', [(0, H - .005), (.014, H - .005), (.016, H + .005), (.009, H + .016), (0, H + .02)], (x, 0, 0), wood, seg=16, detail=1)
            if outer:
                prof = [(-.11, 0), (.11, 0), (.11, .018), (.08, .03), (.05, .03), (.02, .075), (-.02, .075), (-.05, .03), (-.08, .03), (-.11, .018)]
                extrude_profile('Shoe_Foot', [(y, z) for y, z in prof], .05, wood, 'yz', (x, 0, 0), bevel=.003, grain='y')
            else:
                box('Inner_Foot', (x, 0, .015), (st + .004, .1, .03), wood, .004, grain='y')
        box('Top_Rail', (w / 2, 0, H - .03), (w - 2 * st, rt - .004, .036), wood, .004)
        box('Mid_Rail', (w / 2, 0, .33), (w - 2 * st, rt - .004, .036), wood, .004)
        bottom = box('Bottom_Rail', (w / 2, 0, .14), (w - 2 * st, rt - .006, .028), wood, .003)
        # cloud-cut apron between bottom and mid rails, with two short struts
        prof = [(0, 0)]
        n = 20
        for i in range(n + 1):
            x = (w - 2 * st) * i / n
            prof.append((x, .045 + .03 * abs(math.sin(math.pi * i / n * 3)) ** 1.5))
        prof.append(((w - 2 * st), 0))
        pts = [(st + x, .312 - z) for x, z in prof]
        extrude_profile('Cloud_Apron', pts[::-1], .016, wood, 'xz', (0, 0, 0), bevel=.002, detail=0)
        for f in (.33, .67):
            box('Apron_Strut', (w * f, 0, .21), (.02, .016, .12), wood, .002, grain='z', detail=1)
        # painted front face and plain linen back, set into the frame
        x0, x1, z0, z1 = st - .004, w - st + .004, .348, H - .048
        u0, u1 = idx / 3, (idx + 1) / 3
        mesh('Painted_Front', [(x0, -.003, z0), (x1, -.003, z0), (x1, -.003, z1), (x0, -.003, z1)], [(0, 1, 2, 3)], paint_m,
             uvs=[(u0, 0), (u1, 0), (u1, 1), (u0, 1)])
        mesh('Linen_Back', [(x1, .003, z0), (x0, .003, z0), (x0, .003, z1), (x1, .003, z1)], [(0, 1, 2, 3)], P['linen'], grain='z')
        box('Panel_Core', ((x0 + x1) / 2, 0, (z0 + z1) / 2), (x1 - x0, .004, z1 - z0), P['linen'], 0, detail=1)
        return bottom
    # middle panel flat, wings angled forward (toward -Y) by theta
    with xf(T(-w / 2, 0, 0)):
        panel(1, False, False)
    with xf(T(w / 2 + gap, 0, 0) @ RZ(-theta)):
        panel(2, False, True)
    # left wing built from its outer end toward the hinge so its front still faces -Y
    ox = -w / 2 - gap - w * math.cos(theta); oy = -w * math.sin(theta)
    with xf(T(ox, oy, 0) @ RZ(theta)):
        b = panel(0, True, False)
        # tiny carved crescent with a nicked tip, rear face of the lower rail by the outer stile
        crescent_mark(P, b, (.085, .0125, .14))
    # brass hinges across both joints
    for sx, ang in ((1, -theta), (-1, theta)):
        for zz in (.42, 1.48):
            with xf(T(sx * (w / 2 + gap / 2), -.016, zz)):
                box('Hinge_Leaf', (0, 0, 0), (.05, .003, .06), P['brass'], .001)
                cyl('Hinge_Barrel', (0, -.003, 0), .004, .06, P['brass'], verts=10)
                for k in (-1, 1):
                    rivet('Hinge_Pin', (k * .016, -.002, .018), .0028, P['brass'])
                    rivet('Hinge_Pin', (k * .016, -.002, -.018), .0028, P['brass'])
    # crescent mark: tiny carved missing-corner moon on the rear of the left wing's lower rail
    S['crescent'] = True
    return paint_m

def crescent_mark(P, target, centre, normal_axis='y'):
    """Carve a 26 mm crescent with a nicked tip into target at centre (on its rear face)."""
    cut = cyl('Crescent_Outer_Cut', centre, .013, .006, P['wood_end'], axis='y', verts=40, bevel=0)
    keep = cyl('Crescent_Inner_Keep', (centre[0] + .006, centre[1], centre[2] + .003), .0115, .012, P['wood_end'], axis='y', verts=40, bevel=0)
    nick = box('Crescent_Nick', (centre[0] - .002, centre[1], centre[2] + .0125), (.006, .012, .006), P['wood_end'], 0)
    m = cut.modifiers.new('Moon_Shape', 'BOOLEAN'); m.object = keep; m.operation = 'DIFFERENCE'; m.solver = 'EXACT'
    m2 = cut.modifiers.new('Moon_Nick', 'BOOLEAN'); m2.object = nick; m2.operation = 'DIFFERENCE'; m2.solver = 'EXACT'
    for o in (keep, nick):
        for c in list(o.users_collection): c.objects.unlink(o)
        S['cut'].objects.link(o); S['parts'].remove(o)
    boolean(target, cut)

# ================================================================ TI06 安坐地蓆
def ti06_woven_mat(P):
    reed = tm.straw('Reed_Weave', (.25, .17, .07), (.075, .048, .02))
    sage = tm.cloth('Jade_Cloth_Binding', (.045, .075, .058), weave=240, dirt=.5)
    W, D, H = 1.96, 1.36, .025
    b = .05
    box('Reed_Mat_Body', (0, 0, .009), (W - .05, D - .05, .016), reed, .004)
    # rolled cloth binding along all four edges
    for sy in (-1, 1):
        box('Edge_Binding_Long', (0, sy * (D / 2 - b / 2), .011), (W - 2 * b + .004, b, .022), sage, .009)
    for sx in (-1, 1):
        box('Edge_Binding_Short', (sx * (W / 2 - b / 2), 0, .011), (b, D - 2 * b + .004, .022), sage, .009, grain='y')
    # folded corner patches
    for sx in (-1, 1):
        for sy in (-1, 1):
            box('Corner_Patch', (sx * (W / 2 - b / 2), sy * (D / 2 - b / 2), .0115), (b + .004, b + .004, .023), sage, .01)
            box('Corner_Fold', (sx * (W / 2 - b / 2 - .004), sy * (D / 2 - b / 2 - .004), .0228), (.046, .046, .0025), sage, .001,
                rot=(0, 0, math.pi / 4), detail=1)
    # running stitches along the inner edge of the binding
    r_ = rng()
    for sy in (-1, 1):
        for i in range(44):
            x = -W / 2 + .07 + i * (W - .14) / 43
            box('Stitch', (x, sy * (D / 2 - b + .004), .0225), (.016, .0018, .0012), P['rope'], 0, detail=2)
    for sx in (-1, 1):
        for i in range(30):
            y = -D / 2 + .07 + i * (D - .14) / 29
            box('Stitch', (sx * (W / 2 - b + .004), y, .0225), (.0018, .016, .0012), P['rope'], 0, detail=2)
    # binding wear: two frayed spots with loose reed fibres lying flat
    for (fx, fy, ang) in ((-.62, -D / 2 + .03, .2), (.71, D / 2 - .035, -.4), (W / 2 - .03, -.31, 1.5)):
        for k in range(7):
            a = ang + r_.uniform(-.5, .5); l = r_.uniform(.02, .05)
            p0 = (fx + r_.uniform(-.03, .03), fy + r_.uniform(-.01, .01), .0215)
            tube('Loose_Reed_Fibre', [p0, (p0[0] + l * math.cos(a), p0[1] + l * math.sin(a), .0205)], .0011, reed, detail=2)
    socket('SOCKET_cushion', (0, 0, .018))

# ================================================================ TI07 歸居門簾
def ti07_linen_curtain(P):
    lin = tm.cloth('Undyed_Linen_Curtain', (.33, .30, .24), weave=320)
    sage = tm.cloth('Sage_Hem_Band', (.08, .12, .095), weave=260)
    rodz = 2.128
    cyl('Curtain_Rod', (0, 0, rodz), .016, 1.18, P['wood'], axis='x', verts=24)
    for sx in (-1, 1):
        lathe('Rod_End_Knob', [(0, 0), (.02, 0), (.024, .008), (.024, .022), (.02, .03), (.012, .04), (0, .041)],
              (0, 0, 0), P['brass'], seg=24, grain='z').matrix_world = (T(sx * .59, 0, rodz) @ RY(sx * math.pi / 2))
        torus('Rod_Collar', (sx * .585, 0, rodz), .018, .004, P['brass'], rot=(0, math.pi / 2, 0), detail=1)
    r_ = rng()
    for side in (-1, 1):
        x0 = .012 if side > 0 else -.6
        x1 = .6 if side > 0 else -.012
        ph = r_.uniform(0, 6)
        def fold(x, z, extra=0.0):
            t = 1 - (z - .03) / 2.05                   # 0 top -> 1 hem
            a = .009 + .012 * t
            y = a * math.sin((x - x0) / .115 * math.tau + ph) + .004 * math.sin((x - x0) / .043 * math.tau + ph * 2)
            if z < .32:   # crumpled hem
                k = (.32 - z) / .32
                y += k * (.008 * math.sin(x * 61 + ph) + .006 * math.sin(x * 23 + z * 40))
            return y + extra
        def hem_z(x):
            return .03 + .012 * math.sin(x * 9 + ph) + .006 * math.sin(x * 31)
        def body(u, v):
            x = x0 + (x1 - x0) * u; zb = hem_z(x); z = zb + (2.08 - zb) * v
            return (x, fold(x, z), z)
        # body above the hem band, band below (separate materials)
        def band(u, v):
            x = x0 + (x1 - x0) * u; zb = hem_z(x); z = zb + .14 * v
            return (x, fold(x, z), z)
        def upper(u, v):
            x = x0 + (x1 - x0) * u; zb = hem_z(x) + .13; z = zb + (2.08 - zb) * v
            return (x, fold(x, z), z)
        surface('Curtain_Hem_Band', 96, 10, band, sage, solid=.004, grain='z')
        surface('Curtain_Panel', 96, 40, upper, lin, solid=.003, grain='z')
        # top tabs over the rod
        for i in range(5):
            x = x0 + .03 + i * (x1 - x0 - .06) / 4
            pts = [(x, fold(x, 2.06) - .002, 2.06), (x, -.022, rodz - .005), (x, -.018, rodz + .02), (x, 0, rodz + .026),
                   (x, .018, rodz + .02), (x, .022, rodz - .005), (x, .01, 2.07)]
            ribbon('Curtain_Tab_Loop', pts, .019, lin, .003, grain='z')
            box('Tab_Stitch', (x, fold(x, 2.07) - .006, 2.07), (.03, .002, .0018), P['rope'], 0, detail=2)
        if side < 0:
            # mended patch with cross stitches, low on the left panel
            px, pz = -.48, .42
            def patch(u, v):
                x = px + .13 * u; z = pz + .15 * v
                return (x, fold(x, z) - .0028, z)
            surface('Mended_Patch', 10, 10, patch, tm.cloth('Mend_Linen_Patch', (.22, .19, .14), weave=380, dirt=.5), solid=.0012, grain='z', detail=1)
            for k in range(7):
                for (dx, dz) in ((0, 0), (.13, 0)):
                    z = pz + .02 + k * .02; x = px + dx
                    box('Patch_Cross_Stitch', (x, fold(x, z) - .0045, z), (.012, .0015, .0015), P['rope'], 0, rot=(0, .7, 0), detail=2)
                    box('Patch_Cross_Stitch', (x, fold(x, z) - .0045, z), (.012, .0015, .0015), P['rope'], 0, rot=(0, -.7, 0), detail=2)

# ================================================================ TI08 收藏示意道具
def keepsake_box(P):
    wood, brass = P['wood'], P['brass']
    W, D = .22, .17
    box('Box_Body', (0, 0, .055), (W - .008, D - .008, .08), P['wood'], .004)
    skirt = box('Box_Skirt', (0, 0, .012), (W, D, .024), wood, .003)
    boolean(skirt, box('Skirt_Cut_Front', (0, 0, .004), (.14, D + .02, .016), wood, 0))
    boolean(skirt, box('Skirt_Cut_Side', (0, 0, .004), (W + .02, .09, .016), wood, 0))
    box('Box_Lid', (0, 0, .118), (W, D, .044), P['wood_board'], .006)
    for sx in (-1, 1):   # end boards with grain running front-to-back, so the ends don't show cut rings
        box('Box_End_Board', (sx * (W / 2 - .0055), 0, .055), (.008, D - .006, .079), P['wood'], .002, grain='y')
        box('Lid_End_Board', (sx * (W / 2 - .0015), 0, .118), (.006, D - .004, .042), P['wood_board'], .003, grain='y')
    box('Lid_Seam_Shadow', (0, 0, .096), (W - .006, D - .006, .003), P['coal'], .0005)
    for sx in (-1, 1):
        for sy in (-1, 1):
            for zz in (.008, .126):
                box('Corner_Bracket_X', (sx * (W / 2 - .014), sy * (D / 2 + .001), zz), (.028, .003, .026), brass, .001, detail=1)
                box('Corner_Bracket_Y', (sx * (W / 2 + .001), sy * (D / 2 - .014), zz), (.003, .028, .026), brass, .001, detail=1)
    # cloud latch plate and hasp
    cloud = [(.022 * (1 + .22 * math.cos(4 * t)) * math.cos(t), .09 + .022 * (1 + .22 * math.cos(4 * t)) * math.sin(t)) for t in [math.tau * k / 48 for k in range(48)]]
    extrude_profile('Latch_Plate', cloud, .004, brass, 'xz', (0, -D / 2 - .002, 0), bevel=.0012)
    box('Latch_Hasp', (0, -D / 2 - .005, .075), (.018, .004, .04), brass, .0015)
    torus('Latch_Ring', (0, -D / 2 - .008, .06), .007, .002, brass, rot=(math.pi / 2, 0, 0), detail=1)
    for sx in (-1, 1):
        box('Rear_Hinge', (sx * .055, D / 2 + .002, .098), (.032, .004, .028), brass, .001)
        torus('Side_Bail', (sx * (W / 2 + .004), 0, .07), .013, .002, brass, rot=(0, math.pi / 2, 0), detail=1)

def paper_scroll(P):
    L = .21; r = .032
    cyl('Scroll_Paper_Roll', (0, 0, .04), r, L, P['linen'], axis='x', verts=32)
    for sx in (-1, 1):
        cyl('Roller_Rod', (sx * (L / 2 + .012), 0, .04), .011, .024, P['wood'], axis='x', verts=16)
        lathe('Roller_Knob', [(0, 0), (.02, 0), (.022, .008), (.02, .016), (0, .018)], (0, 0, 0), P['wood'], seg=20).matrix_world = T(sx * (L / 2 + .022), 0, .04) @ RY(sx * math.pi / 2)
        torus('Roller_Collar', (sx * (L / 2 + .002), 0, .04), r * .98, .0025, P['brass'], rot=(0, math.pi / 2, 0), detail=1)
    cyl('Cloth_Wrap_Band', (.0, 0, .04), r + .0015, .055, P['sage'], axis='x', verts=32)
    for dx in (-.012, .012):
        torus('Cord_Turn', (dx, 0, .04), r + .003, .0022, P['rope'], rot=(0, math.pi / 2, 0))
    sphere('Cord_Knot', (0, -.006, .04 + r + .004), .007, P['rope'], scale=(1.4, 1, .8))
    for k, dx in enumerate((-.01, .012)):
        tube('Cord_End', [(dx * .4, -.01, .04 + r + .004), (dx, -.03, .06), (dx * 1.4, -.04, .03), (dx * 1.6, -.042, .006)], .0022, P['rope'])

def celadon_jar(P):
    prof = [(0, 0), (.045, 0), (.05, .006), (.048, .012)]
    for k in range(1, 13):
        t = k / 12
        prof.append((.05 + .03 * math.sin(math.pi * (t * .9 + .05)) ** .9 - .02 * t, .012 + t * .16))
    prof += [(.042, .176), (.044, .184), (0, .184)]
    lathe('Jar_Body', prof, (0, 0, 0), P['celadon'], seg=48)
    lathe('Jar_Foot', [(0, -.0005), (.046, -.0005), (.051, .006), (.049, .014), (0, .014)], (0, 0, 0), P['clay'], seg=48, detail=1)
    lid = [(0, .182), (.05, .182), (.0525, .1845), (.0535, .188), (.0525, .192), (.049, .197), (.043, .202), (.034, .206), (.024, .209), (.018, .2115),
           (.0155, .215), (.016, .2185), (.0185, .2215), (.0195, .2245), (.018, .2275), (.0135, .2298), (.007, .231), (0, .2312)]
    lathe('Jar_Lid', lid, (0, 0, 0), P['celadon'], seg=40)
    torus('Jar_Rim_Line', (0, 0, .183), .045, .0018, P['clay'], detail=1)

def cover_radius_at(z):
    """Outer radius of the draped cloth at height z (same formula as the cover surface)."""
    best = .044
    for k in range(200):
        rr = .044 + .03 * k / 199; drop = (rr - .044) * 1.25
        zz = .162 - drop * .9; rr2 = .044 + (rr - .044) * .45
        if zz >= z: best = rr2
    return best

def medicine_pot(P):
    prof = [(0, 0), (.04, 0), (.046, .006), (.056, .02), (.065, .045), (.069, .07), (.067, .095), (.058, .118),
            (.045, .132), (.036, .14), (.04, .148), (.038, .155), (0, .155)]
    lathe('Pot_Body', prof, (0, 0, 0), P['redglaze'], seg=48)
    lathe('Pot_Foot', [(0, -.0005), (.041, -.0005), (.046, .006), (.044, .012), (0, .012)], (0, 0, 0), P['clay'], seg=48, detail=1)
    cloth_m = tm.cloth('Cover_Cloth', (.28, .25, .19), weave=300, dirt=.4)
    def cover(u, v):
        a = u * math.tau; rr = .002 + .072 * v
        drop = 0 if rr < .044 else (rr - .044) * 1.25
        wav = .006 * math.sin(a * 9) * max(0, (rr - .045) / .03)
        z = .162 + .012 * (1 - (rr / .044) ** 2 if rr < .044 else 0) - drop * .9 + wav
        rr2 = rr if rr < .044 else .044 + (rr - .044) * .45
        return (rr2 * math.cos(a), rr2 * math.sin(a), z)
    surface('Pot_Cloth_Cover', 48, 10, cover, cloth_m, solid=.0015, closed_u=True)
    zc = .142; rc = cover_radius_at(zc) + .0035
    torus('Cover_Tie_Cord', (0, 0, zc), rc, .0028, P['rope'])
    sphere('Cord_Bow', (.0, -rc - .002, zc), .0065, P['rope'], scale=(1.6, 1, 1))
    for dx in (-.008, .008):
        tube('Cord_Tail', [(dx, -rc - .003, zc - .002), (dx * 1.5, -rc - .006, zc - .025), (dx * 1.8, -rc - .006, zc - .05)], .0024, P['rope'])
        sphere('Tail_Knot', (dx * 1.8, -rc - .006, zc - .053), .0045, P['rope'], detail=1)

PROPS = [('KeepsakeBox', '木匣', keepsake_box), ('PaperScroll', '紙卷', paper_scroll),
         ('CeladonJar', '青瓷罐', celadon_jar), ('MedicinePot', '陶藥罐', medicine_pot)]

def ti08_display_props(P, only=None):
    """Props laid out in a row; each one is its own export group so Unity gets one object per prop."""
    xs = {'KeepsakeBox': -.36, 'PaperScroll': -.06, 'CeladonJar': .17, 'MedicinePot': .36}
    for key, _, fn in PROPS:
        if only and key != only: continue
        start = len(S['parts'])
        with xf(T(0 if only else xs[key], 0, 0)):
            fn(P)
        for o in S['parts'][start:]: o['group'] = 'Main' if only else key

# ================================================================ textures
def fbm(shape, octaves, seed, base=4):
    r = np.random.default_rng(seed); h, w = shape; acc = np.zeros(shape, np.float32); amp = 1.0; tot = 0
    for o in range(octaves):
        n = base * 2 ** o
        g = r.random((n + 1, int(n * w / h) + 2)).astype(np.float32)
        ys = np.linspace(0, n, h); xs = np.linspace(0, int(n * w / h) + 1 - 1e-3, w)
        y0 = ys.astype(int); x0 = xs.astype(int); fy = (ys - y0)[:, None]; fx = (xs - x0)[None, :]
        fy = fy * fy * (3 - 2 * fy); fx = fx * fx * (3 - 2 * fx)
        y1 = np.minimum(y0 + 1, n); x1 = np.minimum(x0 + 1, g.shape[1] - 1)
        v = (g[y0][:, x0] * (1 - fx) + g[y0][:, x1] * fx) * (1 - fy) + (g[y1][:, x0] * (1 - fx) + g[y1][:, x1] * fx) * fy
        acc += v * amp; tot += amp; amp *= .5
    return acc / tot

def blur(a, k):
    """Separable box blur of radius k (2-D array)."""
    for axis in (0, 1):
        pad = [(k + 1, k) if i == axis else (0, 0) for i in range(2)]
        c = np.cumsum(np.pad(a, pad, mode='edge'), axis=axis)
        n = a.shape[axis]
        a = (np.take(c, range(2 * k + 1, 2 * k + 1 + n), axis=axis) - np.take(c, range(0, n), axis=axis)) / (2 * k + 1)
    return a

def landscape_texture(path, W=3072, H=2560, seed=18):
    """Faint ink-wash landscape continuous across three panels, on undyed linen (sRGB)."""
    r = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); X = xx / W; Y = 1 - yy / H     # Y up
    linen = np.array([.70, .64, .52], np.float32)
    weave = (np.sin(xx * 1.9) * np.sin(yy * 1.9)) * .012 + (fbm((H, W), 5, seed + 1, 8) - .5) * .06
    img = np.ones((H, W, 3), np.float32) * linen + weave[..., None]
    ink_far = np.array([.62, .68, .66], np.float32); ink_mid = np.array([.42, .50, .46], np.float32); ink_near = np.array([.22, .27, .25], np.float32)
    def ridge(seed2, base, amp, peaks, sharp=1.6):
        n1 = fbm((1, W), 6, seed2, 3)[0]
        pk = np.zeros(W, np.float32)
        for c, h, wd in peaks:
            pk += h * np.exp(-((X[0] - c) / wd) ** 2) ** (1 / sharp)
        return base + amp * (n1 - .5) + pk
    tex = fbm((H, W), 6, seed + 2, 6)
    layers = [
        (ink_far, ridge(seed + 3, .50, .06, [(.18, .16, .07), (.30, .10, .05), (.72, .20, .08), (.86, .12, .06)]), .30, .10),
        (ink_mid, ridge(seed + 4, .38, .07, [(.08, .22, .05), (.40, .28, .06), (.47, .18, .04), (.95, .14, .05)]), .44, .14),
        (ink_near, ridge(seed + 5, .20, .06, [(.05, .20, .07), (.62, .10, .06), (.80, .06, .08)]), .56, .12),
    ]
    for col, rid, alpha, fade in layers:
        d = rid[None, :] - Y                                      # >0 below ridge line
        body = np.clip(d / .01, 0, 1) * np.exp(-np.clip(d, 0, None) / fade)
        streak = blur(tex, 3) * .6 + .4
        a = body * alpha * streak
        img = img * (1 - a[..., None]) + col * a[..., None]
        # dry-brush ridge contour
        edge = np.exp(-(d / .004) ** 2) * alpha * 1.2 * (fbm((H, W), 4, seed + 7, 30) > .45)
        img = img * (1 - edge[..., None]) + col * .7 * edge[..., None]
    # water band and mist
    water = np.exp(-((Y - .17) / .05) ** 2)
    img = img * (1 - .25 * water[..., None]) + linen * .25 * water[..., None]
    for k in range(18):
        y0 = r.uniform(.08, .24); x0 = r.uniform(.05, .9); ln = r.uniform(.03, .12)
        m = (np.abs(Y - y0) < .0012) & (X > x0) & (X < x0 + ln)
        img[m] = img[m] * .85 + ink_mid * .15
    # tree clusters along mid and near ridges
    for col, rid, cnt in ((ink_mid, layers[1][1], 120), (ink_near, layers[2][1], 160)):
        for k in range(cnt):
            cx = r.uniform(0, 1); ix = int(cx * (W - 1)); cy = rid[ix] - r.uniform(.0, .05)
            for d in range(r.integers(4, 9)):
                px = cx + r.normal(0, .004); py = cy + r.normal(0, .006); rad = r.uniform(.002, .005)
                x0 = int((px - rad) * W); x1 = int((px + rad) * W) + 1; y0 = int((1 - py - rad) * H); y1 = int((1 - py + rad) * H) + 1
                x0, y0 = max(x0, 0), max(y0, 0)
                if x1 <= x0 or y1 <= y0: continue
                sub = img[y0:y1, x0:x1]
                dd = ((xx[y0:y1, x0:x1] / W - px) ** 2 + ((1 - yy[y0:y1, x0:x1] / H) - py) ** 2) < rad ** 2
                sub[dd] = sub[dd] * .55 + col * .45
    # mist band across the middle
    mist = np.exp(-((Y - .32) / .04) ** 2) * (fbm((H, W), 4, seed + 9, 3) * .8 + .2)
    img = img * (1 - .35 * mist[..., None]) + linen * .35 * mist[..., None]
    # age: overall faded, slight foxing
    fox = (fbm((H, W), 5, seed + 11, 5) > .72) * .05
    img = img * (1 - fox[..., None]) + np.array([.62, .52, .36]) * fox[..., None]
    _save(img, path)

def journal_page_texture(path, W=2048, H=1384, seed=19):
    """Blank two-page spread: warm handmade paper, faint fibres, darker gutter and edges."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); X = xx / W; Y = yy / H
    base = np.array([.82, .77, .66], np.float32)
    f = fbm((H, W), 6, seed, 10) - .5
    img = base + f[..., None] * .07
    gutter = np.exp(-((X - .5) / .025) ** 2) * .22
    edge = (np.exp(-(np.minimum(X, 1 - X) / .02)) + np.exp(-(np.minimum(Y, 1 - Y) / .02))) * .1
    img = img * (1 - (gutter + edge)[..., None]) + np.array([.55, .45, .30]) * (gutter + edge)[..., None]
    _save(img, path)

def _save(img, path):
    img = np.clip(img, 0, 1); H, W = img.shape[:2]
    rgba = np.ones((H, W, 4), np.float32); rgba[..., :3] = img[::-1]   # Blender rows start at the bottom
    im = bpy.data.images.new(path.stem, W, H, alpha=False)
    im.colorspace_settings.name = 'sRGB'
    im.pixels.foreach_set(rgba.ravel()); im.filepath_raw = str(path); im.file_format = 'PNG'; im.save()
    return im
