"""Ruin-kit materials for qingxi-world-ruins-b, built on the node helpers in wr_mats.py.

Colours follow docs/art/modeling-style-spec-v1.md section 2 (sRGB swatches, converted with hexl).
Roughness ranges follow section 3: old wood .65-.85, stone .7-.9, tile .5-.7, cloth .8-.95.
"""
import math
from wr_mats import _new, _finish, _grain_coords, cloth, wood, metal, plain, MAT_INFO


def hexl(h, k=1.0):
    """sRGB hex -> linear rgb tuple (optionally scaled)."""
    h = h.lstrip('#'); out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append((c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4) * k)
    return tuple(out)


def _lerp(a, b, t): return tuple(x + (y - x) * t for x, y in zip(a, b))


def _sepz(g, vec, comp='Z'):
    s = g.node('ShaderNodeSeparateXYZ'); g.link(vec, s.inputs[0]); return s.outputs[comp]


def stone(name, tones=('#6A706A', '#474D49', '#8E918A'), warm='#7A7262', slot='Main', moss=.55, lichen=.5,
          soot=0.0, ground_dirt=.6, rough=.86, moss_top=1.2, relief=1.0, scale=1.0, rosettes=0.0, small_rosettes=0.0, lichen_cover=0.0, moss_low=0.0, rosette_scale=11.0):
    """Weathered grey-green field stone: per-stone tone, granular surface with hairline fractures and pits,
    pale lichen crusts on exposed faces, moss in crevices and on upward faces, dirt splash at the foot,
    worn lighter edges. scale < 1 enlarges every feature (a single big stone rather than wall stones).
    rosettes > 0 adds round pale crustose lichen colonies, clustered, mostly on faces turned up or outwards."""
    m, g = _new(name, slot)
    Pw = g.geo('Position'); N = g.geo('Normal'); r = g.attr('part_rand', 'Fac')
    # texture in part-local space offset by the part's random value: chain-joint halves of a stone match
    rr3 = g.node('ShaderNodeCombineXYZ')
    for i in range(3): g.link(r, rr3.inputs[i])
    P = g.vmath('ADD', g.attr('lp'), g.vmath('MULTIPLY', rr3.outputs[0], (7.3, 3.1, 5.9)))
    if scale != 1.0: P = g.vmath('MULTIPLY', P, (scale, scale, scale))
    Z = _sepz(g, Pw); up = g.maprange(_sepz(g, N), .15, .85)
    t0, t1, t2 = (hexl(c) for c in tones); tw = hexl(warm)
    base = g.ramp(r, [(0, t1), (.2, _lerp(t1, tw, .5)), (.4, t0), (.62, t2), (.8, _lerp(t0, tw, .8)), (1, _lerp(t2, tw, .4))])
    big = g.noise(P, 2.2, 4, .55); mid = g.noise(P, 9.0, 5, .6); fine = g.noise(P, 48.0, 4, .65)
    grit = g.noise(P, 160.0, 3, .7)
    mott = g.math('ADD', g.math('MULTIPLY', big, .5), g.math('MULTIPLY', mid, .5))
    base = g.mul(1.0, base, g.ramp(mott, [(.3, (.66, .66, .66)), (.55, (1, 1, 1)), (.75, (1.2, 1.18, 1.14))]))
    base = g.mul(1.0, base, g.ramp(grit, [(.35, (.8, .8, .8)), (.65, (1.12, 1.12, 1.1))]))
    # dark mineral streaks running across the stone
    rust = g.math('MULTIPLY', g.maprange(g.noise(P, 1.6, 4, .6), .58, .72), g.maprange(r, .5, .9))
    base = g.mix(g.math('MULTIPLY', rust, .45), base, hexl('#7A6248'))
    spk = g.maprange(fine, .62, .72)
    base = g.mix(g.math('MULTIPLY', spk, .25), base, _lerp(t2, (1, 1, 1), .25))
    pits = g.maprange(g.voronoi(P, 26.0, 'F1', 'Distance'), .0, .12, 1, 0)
    base = g.mix(g.math('MULTIPLY', pits, .45), base, tuple(c * .4 for c in t1))
    fn = g.noise(g.vmath('MULTIPLY', P, (1, 1, 1.6)), 4.0, 3, .5, out='Color')
    frac = g.math('MULTIPLY', g.maprange(g.voronoi(g.vmath('ADD', g.vmath('MULTIPLY', P, (1, 1, 1.6)), g.vmath('MULTIPLY', fn, (.12, .12, .12))),
                                                    4.0, 'DISTANCE_TO_EDGE'), .0, .006, 1, 0),
                  g.maprange(g.noise(P, 2.5, 3, .5), .56, .66))
    base = g.mix(g.math('MULTIPLY', frac, .45), base, tuple(c * .45 for c in t1))
    ao = g.ao(.06)
    cav = g.math('SUBTRACT', 1.0, ao)
    base = g.mul(1.0, base, g.ramp(ao, [(0, (.22, .22, .2)), (.6, (.75, .75, .72)), (1, (1, 1, 1))]))
    e = g.math('MULTIPLY', g.edge(.006), g.attr('iface', 'Fac'))
    base = g.mix(g.math('MULTIPLY', e, .45), base, _lerp(t2, (.85, .84, .8), .35))
    if lichen:
        crust = g.maprange(g.noise(P, 70.0, 3, .6), .3, .6)
        patch = g.maprange(g.noise(P, 6.0, 6, .7), .55 - .12 * lichen_cover, .62 - .08 * lichen_cover)
        lm = g.math('MULTIPLY', g.math('MULTIPLY', patch, crust), g.math('ADD', .4, g.math('MULTIPLY', up, .6)))
        base = g.mix(g.math('MULTIPLY', lm, lichen), base, hexl('#ADB09E'))
        ochre = g.math('MULTIPLY', g.maprange(g.noise(g.vmath('ADD', P, (9, 4, 2)), 7.0, 6, .7), .62, .67), crust)
        base = g.mix(g.math('MULTIPLY', ochre, lichen * .6), base, hexl('#9E8A55'))
    if rosettes:
        wp = g.vmath('ADD', P, g.vmath('MULTIPLY', g.noise(P, 9.0, 4, .6, out='Color'), (.09, .09, .09)))
        vd = g.voronoi(wp, rosette_scale, 'F1', 'Distance')
        clus = g.math('MULTIPLY', g.maprange(g.noise(g.vmath('ADD', P, (3, 8, 1)), 2.0, 4, .6), .4, .56),
                      g.math('ADD', .55, g.math('MULTIPLY', up, .45)))      # crustose lichen grows on upright faces too
        size = g.math('MULTIPLY', clus, .62)                                         # colonies grow where the cluster is strong
        vdl = g.math('ADD', vd, g.math('MULTIPLY', g.noise(P, 35.0, 3, .65), .1))
        spot = g.maprange(g.math('SUBTRACT', vdl, size), .04, -.06)
        ring = g.math('MULTIPLY', spot, g.maprange(g.math('SUBTRACT', vd, size), -.05, -.01))   # paler growing rim
        rm = g.math('MULTIPLY', spot, g.maprange(g.noise(P, 110.0, 2, .6), .25, .55))
        base = g.mix(g.math('MULTIPLY', rm, rosettes * .8), base, hexl('#A5AA9A'))
        base = g.mix(g.math('MULTIPLY', ring, rosettes * .45), base, hexl('#BEC0B0'))
    if small_rosettes:
        # a dense crust of small young colonies between the big ones: the whole stone reads speckled pale
        wp2 = g.vmath('ADD', P, g.vmath('MULTIPLY', g.noise(P, 21.0, 3, .6, out='Color'), (.04, .04, .04)))
        vd2 = g.voronoi(wp2, 30.0, 'F1', 'Distance')
        clus2 = g.math('MULTIPLY', g.maprange(g.noise(g.vmath('ADD', P, (5, 2, 7)), 3.0, 4, .6), .3, .55),
                       g.math('ADD', .5, g.math('MULTIPLY', up, .5)))
        lobe = g.noise(P, 60.0, 3, .65)                                             # ragged, lobed colony margins
        spot2 = g.maprange(g.math('SUBTRACT', g.math('ADD', vd2, g.math('MULTIPLY', lobe, .12)), g.math('MULTIPLY', clus2, .5)), .07, -.04)
        spot2 = g.math('MULTIPLY', spot2, g.maprange(g.noise(P, 140.0, 2, .6), .15, .55))
        base = g.mix(g.math('MULTIPLY', spot2, small_rosettes * .5), base, hexl('#A3A898'))
    if moss:
        mn = g.noise(P, 6.0, 5, .6)
        mm = g.math('ADD', g.math('MULTIPLY', cav, 2.4), g.math('MULTIPLY', g.maprange(up, .55, .95), g.maprange(Z, moss_top, .0)))
        if moss_low:                                # damp lower flanks: moss creeps up the sides too, not only on ledges
            mm = g.math('ADD', mm, g.math('MULTIPLY', g.maprange(Z, moss_top, .0), moss_low))
        mm = g.math('MULTIPLY', mm, g.maprange(mn, .34, .6))
        mm = g.maprange(mm, .3, .7)
        mcol = g.ramp(g.noise(P, 14.0, 4, .6), [(.3, hexl('#2F4A2A')), (.6, hexl('#4E6B3A')), (.85, hexl('#6F8A4A'))])
        base = g.mix(g.math('MULTIPLY', mm, moss), base, mcol)
    if ground_dirt:
        dm = g.math('MULTIPLY', g.maprange(Z, .22, 0.0), g.maprange(g.noise(P, 8.0, 3, .5), .3, .6))
        base = g.mix(g.math('MULTIPLY', dm, ground_dirt), base, hexl('#5A4632'))
    if soot:
        sm = g.math('MULTIPLY', g.maprange(g.noise(P, 4.0, 4, .55), .35, .7), soot)
        base = g.mul(sm, base, (.25, .23, .21))
    rgh = g.math('ADD', rough, g.math('MULTIPLY', g.math('SUBTRACT', fine, .5), .16))
    rgh = g.math('SUBTRACT', rgh, g.math('MULTIPLY', e, .12))
    h = g.math('ADD', g.math('ADD', g.math('MULTIPLY', mid, .5), g.math('MULTIPLY', fine, .35)), g.math('MULTIPLY', grit, .25))
    h = g.math('SUBTRACT', h, g.math('ADD', g.math('MULTIPLY', pits, .4), g.math('MULTIPLY', frac, .8)))
    _finish(g, base, rgh, 0.0, g.bump(h, min(1.0, .75 * relief), .006 * relief), spec=.22)
    return m


def bamboo(name, slot='Main', fresh=.2, grey=.7, rough=.55, straw='#A8976A', olive='#857F52'):
    """Dried bamboo culm: straw yellow-green with long fibre streaks, greyed and darker towards the ground,
    mould specks; nodes are geometry, the AO term darkens the pinches."""
    m, g = _new(name, slot)
    co, r = _grain_coords(g, (1, 1, 1))
    P = g.geo('Position'); Z = _sepz(g, P)
    streak = g.maprange(g.noise(g.vmath('MULTIPLY', co, (.6, 120, 120)), 1.0, 4, .6), .3, .7)
    fine = g.maprange(g.noise(g.vmath('MULTIPLY', co, (2, 600, 600)), 1.0, 3, .6), .35, .65)
    straw = hexl(straw); olive = hexl(olive); greyc = hexl('#857F72'); dark = hexl('#4E4430')
    base = g.ramp(g.math('ADD', g.math('MULTIPLY', r, .6), g.math('MULTIPLY', streak, .4)),
                  [(0, _lerp(straw, olive, fresh + .3)), (.5, straw), (1, _lerp(straw, (.62, .55, .38), .3))])
    base = g.mix(g.math('MULTIPLY', g.maprange(g.noise(P, 3.0, 4, .5), .3, .7), grey), base, greyc)
    base = g.mix(g.math('MULTIPLY', g.maprange(r, .7, 1.0), .5), base, hexl('#6E5E40'))
    stain = g.math('MULTIPLY', g.maprange(g.noise(g.vmath('MULTIPLY', co, (1.5, 8, 8)), 2.0, 4, .6), .6, .72), .55)
    base = g.mix(stain, base, hexl('#5A4A34'))
    base = g.mul(.6, base, g.ramp(fine, [(0, (.82, .8, .76)), (1, (1.05, 1.04, 1.0))]))
    ao = g.ao(.03)
    base = g.mul(1.0, base, g.ramp(ao, [(0, (.35, .32, .28)), (1, (1, 1, 1))]))
    low = g.math('MULTIPLY', g.maprange(Z, .35, 0.0), g.maprange(g.noise(P, 6.0, 3, .5), .3, .6))
    base = g.mix(g.math('MULTIPLY', low, .75), base, dark)
    mould = g.math('MULTIPLY', g.maprange(g.noise(P, 18.0, 4, .6), .62, .75), .5)
    base = g.mix(mould, base, (.05, .045, .035))
    e = g.edge(.002)
    base = g.mix(g.math('MULTIPLY', e, .3), base, _lerp(straw, (1, 1, 1), .2))
    rgh = g.math('ADD', rough, g.math('ADD', g.math('MULTIPLY', low, .25), g.math('MULTIPLY', fine, .1)))
    _finish(g, base, rgh, 0.0, g.bump(g.math('ADD', g.math('MULTIPLY', streak, .5), fine), .12, .0008), spec=.45)
    return m


def rope(name, slot='Main', base='#A88E62'):
    """Hemp cord: twisted strands as diagonal bands, fuzzy fibres, dirt in the wraps."""
    m, g = _new(name, slot)
    P = g.geo('Position')
    tw = g.wave(P, 140.0, 2.0, 'BANDS', 'DIAGONAL', 2)
    fuzz = g.noise(P, 300.0, 4, .7)
    c = hexl(base)
    col = g.ramp(g.math('ADD', g.math('MULTIPLY', tw, .6), g.math('MULTIPLY', fuzz, .4)),
                 [(.15, tuple(x * .45 for x in c)), (.55, c), (.9, _lerp(c, (1, .95, .85), .25))])
    ao = g.ao(.02)
    col = g.mul(1.0, col, g.ramp(ao, [(0, (.35, .32, .28)), (1, (1, 1, 1))]))
    col = g.mix(g.math('MULTIPLY', g.maprange(g.noise(P, 5.0, 3, .5), .4, .7), .5), col, hexl('#6E6458'))
    _finish(g, col, g.math('ADD', .86, g.math('MULTIPLY', fuzz, .08)), 0.0,
            g.bump(g.math('ADD', tw, g.math('MULTIPLY', fuzz, .5)), .5, .0015), sheen=.3, spec=.25)
    return m


def bark(name, slot='Main', dark='#3B2617', light='#6E6458', rough=.88, lichen=.6):
    """Rough bark: furrows along the grain axis, greyed ridges, lichen dots."""
    m, g = _new(name, slot)
    co, r = _grain_coords(g, (1, 1, 1))
    fur = g.wave(g.vmath('MULTIPLY', co, (.15, 1, 1)), 18.0, 6.0, 'BANDS', 'Y', 4)
    plate = g.voronoi(g.vmath('MULTIPLY', co, (.4, 3.5, 3.5)), 6.0, 'DISTANCE_TO_EDGE')
    h = g.math('MULTIPLY', g.maprange(fur, .1, .9), g.maprange(plate, .0, .08))
    col = g.ramp(h, [(.1, hexl(dark, .6)), (.45, hexl(dark)), (.85, hexl(light))])
    P = g.geo('Position')
    lich = g.math('MULTIPLY', g.maprange(g.voronoi(P, 30.0, 'F1', 'Distance'), .3, .15), g.maprange(g.noise(P, 4, 3, .5), .5, .65))
    col = g.mix(g.math('MULTIPLY', lich, lichen), col, hexl('#8E9A7E'))
    ao = g.ao(.03)
    col = g.mul(1.0, col, g.ramp(ao, [(0, (.4, .37, .34)), (1, (1, 1, 1))]))
    _finish(g, col, g.math('SUBTRACT', rough, g.math('MULTIPLY', h, .1)), 0.0, g.bump(h, .7, .006), spec=.3)
    return m


def shingle(name, slot='Main', tones=('#7A4A30', '#5A3422', '#8E6046'), grey=.35, moss=.45, rough=.86):
    """Split wooden shingles: a tone per shingle, long riven fibre streaks along the grain (no sawn growth rings),
    silvered by weather, dark rain runs, moss and grime in the laps, pale lichen specks, worn light edges."""
    m, g = _new(name, slot)
    co, r = _grain_coords(g, (1, 1, 1))
    P = g.geo('Position')
    t0, t1, t2 = (hexl(c) for c in tones)
    base = g.ramp(r, [(0, t1), (.5, t0), (1, t2)])
    # streaks sized to read at the 256 px/m atlas (a 1 cm streak bakes to mush): 2-4 cm riven ridges, finer split lines
    fib = g.maprange(g.noise(g.vmath('MULTIPLY', co, (1.5, 34, 34)), 1.0, 4, .6), .28, .72)
    fine = g.maprange(g.noise(g.vmath('MULTIPLY', co, (5, 110, 110)), 1.0, 3, .55), .3, .7)
    base = g.mul(1.0, base, g.ramp(g.math('ADD', g.math('MULTIPLY', fib, .7), g.math('MULTIPLY', fine, .3)),
                                   [(0, (.62, .6, .58)), (.5, (.95, .94, .92)), (1, (1.12, 1.1, 1.06))]))
    # weathering runs down the slope with the grain, and differs shingle to shingle
    silver = g.math('MULTIPLY', g.maprange(g.math('ADD', g.math('MULTIPLY', g.noise(g.vmath('MULTIPLY', co, (2, 9, 9)), 1.0, 3, .5), .7),
                                                     g.math('MULTIPLY', r, .5)), .35, .9), grey)
    base = g.mix(silver, base, hexl('#857C70'))
    rain = g.maprange(g.noise(g.vmath('MULTIPLY', P, (16, 16, 1.4)), 2.0, 3, .5), .5, .74)
    base = g.mix(g.math('MULTIPLY', rain, .4), base, tuple(c * .45 for c in t1))
    ao = g.ao(.05)
    base = g.mul(1.0, base, g.ramp(ao, [(0, (.55, .52, .48)), (1, (1, 1, 1))]))
    # moss only in the shaded laps, broken up by noise; lichen as small dim rosettes, sparse
    mm = g.math('MULTIPLY', g.maprange(g.math('SUBTRACT', 1.0, ao), .25, .6), g.maprange(g.noise(P, 4.0, 4, .6), .5, .66))
    base = g.mix(g.math('MULTIPLY', mm, moss), base, hexl('#4E5A34'))
    lich = g.math('MULTIPLY', g.maprange(g.voronoi(g.vmath('MULTIPLY', P, (1, 1, 1)), 22.0, 'F1', 'Distance'), .12, .06),
                  g.maprange(g.noise(P, 3.0, 3, .5), .58, .7))
    base = g.mix(g.math('MULTIPLY', lich, .35), base, hexl('#8E8A78'))
    e = g.edge(.003)
    base = g.mix(g.math('MULTIPLY', e, .2), base, _lerp(t2, (.8, .78, .72), .25))
    _finish(g, base, g.math('ADD', rough, g.math('MULTIPLY', fine, .08)), 0.0, g.bump(g.math('ADD', fib, g.math('MULTIPLY', fine, .5)), .35, .0012), spec=.3)
    return m


def tile(name, slot='Main', tones=('#5E6B6A', '#46524F', '#7C8784'), moss=.5, rough=.6):
    """Fired grey-teal roof tile: per-tile tone, ceramic mottling, dark rain streaks, moss in the laps."""
    m, g = _new(name, slot)
    P = g.geo('Position'); r = g.attr('part_rand', 'Fac')
    t0, t1, t2 = (hexl(c) for c in tones)
    base = g.ramp(r, [(0, t1), (.5, t0), (1, t2)])
    n = g.noise(P, 12.0, 5, .6)
    base = g.mul(1.0, base, g.ramp(n, [(.3, (.9, .9, .9)), (.7, (1.05, 1.05, 1.04))]))
    streak = g.maprange(g.noise(g.vmath('MULTIPLY', P, (14, 14, 1.5)), 2.0, 3, .5), .45, .7)
    base = g.mix(g.math('MULTIPLY', streak, .35), base, tuple(c * .4 for c in t1))
    ao = g.ao(.05)
    base = g.mul(1.0, base, g.ramp(ao, [(0, (.3, .3, .3)), (1, (1, 1, 1))]))
    mm = g.math('MULTIPLY', g.maprange(g.math('SUBTRACT', 1.0, ao), .1, .5), g.maprange(g.noise(P, 5.0, 4, .6), .4, .62))
    base = g.mix(g.math('MULTIPLY', mm, moss), base, hexl('#4E6B3A'))
    e = g.edge(.004)
    base = g.mix(g.math('MULTIPLY', e, .4), base, _lerp(t2, (1, 1, 1), .2))
    _finish(g, base, g.math('ADD', rough, g.math('MULTIPLY', n, .12)), 0.0, g.bump(g.noise(P, 60.0, 3, .6), .2, .001), spec=.35)
    return m


def plaster(name, slot='Main', mud='#8C6A48', lime='#C8BCA6', lime_amt=.55, rough=.9, age_grey=1.0, cracks=.55, under=None):
    """Mud-and-straw daub under an old lime wash. lime_amt = how much of the wash survives (0 = bare earth):
    the wash has worn through at the foot of the wall and flaked off in small ragged patches with a darker
    rim; straw flecks in the exposed mud, hairline cracks, rain streaks, damp at the foot.
    age_grey < 1 keeps a coloured skim (a clay coat, not a lime wash) from greying; cracks = crack strength.
    under = (stone, mortar) hex pair: the coat sits on a rubble-stone wall, so the losses show rounded fieldstones
    bedded in sandy mortar instead of daub."""
    m, g = _new(name, slot)
    P = g.geo('Position'); Z = _sepz(g, P)
    n = g.noise(P, 4.0, 5, .6); f = g.noise(P, 40.0, 4, .6)
    md = hexl(mud); lm = hexl(lime)
    mudc = g.ramp(f, [(.3, tuple(c * .78 for c in md)), (.7, _lerp(md, hexl('#A88560'), .45))])
    straw = g.maprange(g.noise(g.vmath('MULTIPLY', P, (60, 60, 8)), 3.0, 2, .5), .7, .78)
    mudc = g.mix(g.math('MULTIPLY', straw, .55), mudc, hexl('#B49A68'))
    col = mudc
    if lime_amt > 0:
        # wash colour: off-white greyed by age, never paper white
        limec = g.ramp(n, [(.3, _lerp(lm, hexl('#8E8676'), .55 * age_grey) if age_grey else tuple(c * .8 for c in lm)),
                           (.7, _lerp(lm, hexl('#C8BCA6'), .4 * age_grey))])
        # where the wash has gone: large coherent losses (low-frequency field) with a ragged border (the finer
        # octaves only move the edge), more of it near the foot and less high up under the eaves
        Pz = g.vmath('MULTIPLY', P, (1, 1, 1.35))
        big = g.noise(Pz, 1.6, 3, .45); mid = g.noise(Pz, 4.2, 6, .62); fine = g.noise(Pz, 24.0, 4, .6)
        frac = g.math('ADD', g.math('MULTIPLY', big, 1.15), g.math('ADD', g.math('MULTIPLY', mid, .36), g.math('MULTIPLY', fine, .24)))
        frac = g.math('SUBTRACT', frac, .57 * 1.75 - .57)
        foot = g.maprange(Z, 1.15, .62) if not under else g.maprange(Z, 1.75, 1.05)   # wash worn off towards the foot
        high = g.maprange(Z, 1.9, 2.4)                                # sheltered by the eaves
        mask = g.math('ADD', frac, g.math('ADD', g.math('SUBTRACT', g.math('MULTIPLY', foot, .3), g.math('MULTIPLY', high, .12)),
                                          -(lime_amt - .55) * .5))
        peel = g.maprange(mask, .6, .612)
        rim = g.math('SUBTRACT', g.maprange(mask, .575, .6), peel)
        # exposed daub keeps a film of old wash, so it reads as worn plaster rather than a separate colour
        bare = g.mix(.22, mudc, limec)
        if under:
            sp = g.vmath('MULTIPLY', P, (1, 1, 1.45))
            cellc = g.voronoi(sp, 3.6, 'F1', 'Color')
            jd = g.voronoi(sp, 3.6, 'DISTANCE_TO_EDGE')
            joint = g.maprange(jd, .03, .08)
            st = hexl(under[0])
            stc = g.ramp(cellc, [(.2, tuple(c * .8 for c in st)), (.55, st), (.9, _lerp(st, (.72, .7, .66), .3))])
            stc = g.mul(1.0, stc, g.ramp(g.maprange(jd, .05, .22), [(0, (.5, .48, .46)), (.6, (.92, .92, .92)), (1, (1.06, 1.06, 1.06))]))   # rounded stones
            stc = g.mul(1.0, stc, g.ramp(g.noise(P, 30.0, 3, .6), [(.3, (.82, .82, .82)), (.7, (1.08, 1.08, 1.08))]))
            bare = g.mix(joint, tuple(c * .62 for c in hexl(under[1])), stc)     # mortar sits back in shadow
        col = g.mix(g.math('SUBTRACT', 1.0, peel), bare, limec)
        col = g.mul(g.math('MULTIPLY', rim, .6), col, (.72, .68, .62))
    damp = g.math('MULTIPLY', g.maprange(Z, .95, .45), g.maprange(g.noise(P, 6.0, 4, .5), .3, .65))
    col = g.mul(g.math('MULTIPLY', damp, .75), col, (.58, .53, .47))
    streak = g.maprange(g.noise(g.vmath('MULTIPLY', P, (4.5, 4.5, .9)), 2.0, 2, .45), .55, .75)
    col = g.mul(g.math('MULTIPLY', streak, .3), col, (.7, .66, .6))
    grime = g.maprange(g.noise(P, 1.6, 4, .55), .35, .7)
    col = g.mul(g.math('MULTIPLY', grime, .35), col, (.78, .75, .7))
    # hairline shrinkage cracks: cell edges pushed around by noise so they wander instead of running straight
    wob = g.vmath('MULTIPLY', g.noise(P, 2.2, 4, .6, out='Color'), (.35, .35, .35))
    crk = g.maprange(g.voronoi(g.vmath('ADD', g.vmath('MULTIPLY', P, (1, 1, .7)), wob), 3.0, 'DISTANCE_TO_EDGE'), .0, .008 + .006 * cracks, 1, 0)
    crk = g.math('MULTIPLY', crk, g.maprange(g.noise(P, 2.6, 4, .6), .64 - .2 * cracks, .7 - .12 * cracks))
    col = g.mix(g.math('MULTIPLY', crk, cracks), col, tuple(c * .35 for c in md))
    ao = g.ao(.06)
    col = g.mul(1.0, col, g.ramp(ao, [(0, (.4, .38, .35)), (1, (1, 1, 1))]))
    h = g.math('SUBTRACT', g.math('ADD', g.math('MULTIPLY', n, .5), g.math('MULTIPLY', f, .35)), g.math('MULTIPLY', crk, .6))
    if lime_amt > 0: h = g.math('ADD', h, g.math('MULTIPLY', g.math('SUBTRACT', 1.0, peel), .3))
    if lime_amt > 0 and under: h = g.math('ADD', h, g.math('MULTIPLY', g.math('MULTIPLY', g.maprange(jd, .02, .2), peel), .6))
    _finish(g, col, g.math('ADD', rough, g.math('MULTIPLY', f, .06)), 0.0, g.bump(h, .55, .005), spec=.25)
    return m


def burlap(name, slot='Main', base='#9C8A64'):
    return cloth(name, hexl(base), slot, weave=420.0, rough=.92, sheen=.35, dirt=.45)


def grain(name, slot='Main'):
    """Husked grain: warm gold, per-kernel tone from a fine Voronoi, dark kernel boundaries."""
    m, g = _new(name, slot)
    P = g.geo('Position')
    cell = g.node('ShaderNodeTexVoronoi', feature='F1'); g.link(P, cell.inputs['Vector']); cell.inputs['Scale'].default_value = 160.0
    kern = g.maprange(cell.outputs['Distance'], .45, .1)
    sc = g.node('ShaderNodeSeparateColor'); g.link(cell.outputs['Color'], sc.inputs[0])
    col = g.ramp(sc.outputs[0], [(0, hexl('#9A8150')), (.5, hexl('#B39A66')), (1, hexl('#80683E'))])
    col = g.mul(1.0, col, g.ramp(kern, [(0, (.45, .4, .32)), (1, (1.05, 1.03, 1.0))]))
    ao = g.ao(.03)
    col = g.mul(1.0, col, g.ramp(ao, [(0, (.4, .36, .3)), (1, (1, 1, 1))]))
    _finish(g, col, g.math('SUBTRACT', .55, g.math('MULTIPLY', kern, .15)), 0.0, g.bump(kern, .6, .002), spec=.45)
    return m


def aged_wood(name, slot='Main', grey=.0, rough=.74, ring=6.0, mid=0.0):
    """Old softwood from the style swatches; grey > 0 pulls the light tone towards weathered grey #6E6458."""
    dark = _lerp(hexl('#3B2617'), hexl('#4A433A'), grey)
    light = _lerp(hexl('#7A5234'), hexl('#6E6458'), grey)
    return wood(name, dark, light, slot, ring=ring, rough=rough, wear=.4, grime=.5, mid=mid)


def wood_tint(name, dark, light, slot='Main', ring=6.0, rough=.78, mid=0.0):
    """Aged wood in an explicit dark / light pair (sRGB hex): dark-stained frames, rust-brown shingles."""
    return wood(name, hexl(dark), hexl(light), slot, ring=ring, rough=rough, wear=.4, grime=.5, mid=mid)


def iron(name, slot='Main'):
    return metal(name, hexl('#3A3632'), hexl('#6A4A30'), slot, rough=.55, patina_amt=.7, patina_scale=10.0, crevice=2.0)


def thatch(name, slot='Main', light='#B89A5C', dark='#6E5A36', grey=.35, moss=.35, rough=.9):
    """Old straw thatch, combed down the slope (grain axis = down-slope): dense stalk streaks, butt ends showing as
    a fine dark stipple, weathered grey on top, darker and mossy towards the eave where it stays wet."""
    m, g = _new(name, slot)
    co, r = _grain_coords(g, (1, 1, 1))
    P = g.geo('Position'); Z = _sepz(g, P)
    # sized for the 256 px/m atlas: 2-3 cm stalk bundles with dark gaps, broad combed clumps, finer stalks between
    stalk = g.maprange(g.noise(g.vmath('MULTIPLY', co, (.8, 40, 40)), 1.0, 4, .6), .26, .74)
    clump = g.maprange(g.noise(g.vmath('MULTIPLY', co, (.6, 8, 8)), 1.0, 3, .5), .3, .7)
    stalk = g.math('ADD', g.math('MULTIPLY', stalk, .75), g.math('MULTIPLY', clump, .25))
    fine = g.maprange(g.noise(g.vmath('MULTIPLY', co, (3, 130, 130)), 1.0, 3, .6), .3, .7)
    butts = g.maprange(g.voronoi(g.vmath('MULTIPLY', co, (3.5, 1, 1)), 70.0, 'F1', 'Distance'), .25, .05)
    lt, dk = hexl(light), hexl(dark)
    t = g.math('ADD', g.math('MULTIPLY', stalk, .7), g.math('MULTIPLY', fine, .3))
    col = g.ramp(t, [(.1, tuple(c * .55 for c in dk)), (.4, dk), (.75, lt), (1, _lerp(lt, (1, .95, .8), .2))])
    col = g.mix(g.math('MULTIPLY', butts, .35), col, tuple(c * .45 for c in dk))
    wthr = g.math('MULTIPLY', g.maprange(g.noise(P, 1.4, 4, .5), .35, .7), grey)
    col = g.mix(wthr, col, hexl('#7E786A'))
    wet = g.math('MULTIPLY', g.maprange(Z, 2.9, 2.2), g.maprange(g.noise(P, 3.0, 4, .55), .3, .65))
    col = g.mix(g.math('MULTIPLY', wet, .6), col, hexl('#4A3E2A'))
    mm = g.math('MULTIPLY', g.maprange(g.noise(P, 4.0, 5, .6), .55, .7), g.math('MULTIPLY', wet, moss * 2))
    col = g.mix(g.math('MINIMUM', mm, 1.0), col, hexl('#55603A'))
    ao = g.ao(.08)
    col = g.mul(1.0, col, g.ramp(ao, [(0, (.3, .27, .22)), (1, (1, 1, 1))]))
    h = g.math('ADD', g.math('MULTIPLY', stalk, .7), g.math('MULTIPLY', fine, .3))
    _finish(g, col, g.math('ADD', rough, g.math('MULTIPLY', fine, .06)), 0.0, g.bump(h, .6, .004), sheen=.2, spec=.25)
    return m


def weave(name, slot='Main', light='#A8955E', dark='#5E5236', strip=.035, block=.21, grey=.4):
    """Woven split-bamboo wall mat (in the plane of the panel's grain axis gA and gC): broad flat strips in a
    twill of blocks, alternating direction, dark gaps, per-strip tone, greyed and stained from the foot."""
    m, g = _new(name, slot)
    co, r = _grain_coords(g, (1, 1, 1))
    sep = g.node('ShaderNodeSeparateXYZ'); g.link(co, sep.inputs[0])
    X, Y = sep.outputs['X'], sep.outputs['Z']
    P = g.geo('Position'); Z = _sepz(g, P)
    bx = g.math('FLOOR', g.math('DIVIDE', X, block)); by = g.math('FLOOR', g.math('DIVIDE', Y, block))
    par = g.math('MULTIPLY', g.math('FRACT', g.math('MULTIPLY', g.math('ADD', bx, by), .5)), 2.0)
    across = g.math('ADD', Y, g.math('MULTIPLY', g.math('SUBTRACT', X, Y), par))
    along = g.math('ADD', X, g.math('MULTIPLY', g.math('SUBTRACT', Y, X), par))
    s = g.math('FRACT', g.math('DIVIDE', across, strip))
    prof = g.math('POWER', g.math('SINE', g.math('MULTIPLY', s, math.pi)), .3)
    rid = g.math('ADD', g.math('FLOOR', g.math('DIVIDE', across, strip)), g.math('MULTIPLY', par, 517.0))
    wn = g.node('ShaderNodeTexWhiteNoise', noise_dimensions='1D'); g.link(rid, wn.inputs['W']); rv = wn.outputs['Value']
    fa = g.math('FRACT', g.math('DIVIDE', along, block))
    dip = g.maprange(g.math('MINIMUM', fa, g.math('SUBTRACT', 1.0, fa)), 0.0, .12)
    h = g.math('MULTIPLY', prof, g.math('ADD', .4, g.math('MULTIPLY', dip, .6)))
    fib = g.maprange(g.noise(g.vmath('MULTIPLY', g.vmath('ADD', co, (0, 0, 0)), (40, 40, 40)), 3.0, 3, .6), .3, .7)
    t = g.math('ADD', g.math('ADD', g.math('MULTIPLY', h, .5), g.math('MULTIPLY', rv, .32)), g.math('MULTIPLY', fib, .18))
    lt, dk = hexl(light), hexl(dark)
    col = g.ramp(t, [(.12, tuple(c * .4 for c in dk)), (.4, dk), (.85, lt)])
    col = g.mix(g.math('MULTIPLY', g.maprange(g.noise(P, 2.0, 4, .5), .3, .7), grey), col, hexl('#857F72'))
    low = g.math('MULTIPLY', g.maprange(Z, 1.1, .5), g.maprange(g.noise(P, 5.0, 4, .5), .25, .65))
    col = g.mix(g.math('MULTIPLY', low, .7), col, hexl('#4A3F2E'))
    ao = g.ao(.03)
    col = g.mul(1.0, col, g.ramp(ao, [(0, (.4, .36, .3)), (1, (1, 1, 1))]))
    _finish(g, col, g.math('ADD', .78, g.math('MULTIPLY', fib, .1)), 0.0, g.bump(h, .5, .003), sheen=.1, spec=.3)
    return m


def rammed_earth(name, slot='Main', earth='#9A6E48', band='#7E5A3C', rough=.92):
    """Rammed earth: horizontal lifts about 12 cm high with darker compaction lines, embedded gravel, rain
    erosion streaks and pitting, darker damp foot."""
    m, g = _new(name, slot)
    P = g.geo('Position'); Z = _sepz(g, P)
    wob = g.math('MULTIPLY', g.noise(P, 1.5, 3, .5), .05)
    lift = g.math('FRACT', g.math('DIVIDE', g.math('ADD', Z, wob), .125))
    line = g.maprange(lift, .0, .08, 1, 0)
    lt, bd = hexl(earth), hexl(band)
    li = g.node('ShaderNodeTexWhiteNoise', noise_dimensions='1D')
    g.link(g.math('FLOOR', g.math('DIVIDE', g.math('ADD', Z, wob), .125)), li.inputs['W'])
    n = g.noise(P, 6.0, 5, .6); f = g.noise(P, 50.0, 4, .6)
    col = g.ramp(g.math('ADD', g.math('MULTIPLY', li.outputs['Value'], .45), g.math('MULTIPLY', n, .55)),
                 [(.2, _lerp(bd, lt, .3)), (.55, lt), (.85, _lerp(lt, hexl('#B8936A'), .5))])
    col = g.mix(g.math('MULTIPLY', line, .5), col, tuple(c * .6 for c in bd))
    grav = g.maprange(g.voronoi(P, 38.0, 'F1', 'Distance'), .2, .08)
    col = g.mix(g.math('MULTIPLY', grav, .5), col, hexl('#8E8676'))
    streak = g.maprange(g.noise(g.vmath('MULTIPLY', P, (16, 16, 1.1)), 2.0, 4, .5), .5, .72)
    col = g.mul(g.math('MULTIPLY', streak, .5), col, (.68, .62, .56))
    pits = g.maprange(g.voronoi(P, 22.0, 'F1', 'Distance'), .07, .0)
    col = g.mul(g.math('MULTIPLY', pits, .6), col, (.5, .45, .4))
    damp = g.math('MULTIPLY', g.maprange(Z, 1.0, .5), g.maprange(g.noise(P, 5.0, 4, .5), .3, .65))
    col = g.mul(g.math('MULTIPLY', damp, .7), col, (.6, .55, .5))
    ao = g.ao(.06)
    col = g.mul(1.0, col, g.ramp(ao, [(0, (.4, .37, .33)), (1, (1, 1, 1))]))
    h = g.math('SUBTRACT', g.math('ADD', g.math('MULTIPLY', n, .4), g.math('MULTIPLY', f, .3)),
               g.math('ADD', g.math('MULTIPLY', line, .3), g.math('MULTIPLY', pits, .5)))
    _finish(g, col, g.math('ADD', rough, g.math('MULTIPLY', f, .05)), 0.0, g.bump(h, .6, .006), spec=.25)
    return m


def split_wood(name, slot='Main', dark='#6A4A2E', light='#B38C5E', grey=.25, rings_per_m=75.0):
    """Split and sawn firewood. Rings and radial checks are centred on the part origin (lp), which the
    billet builder puts on the pith, so the cut ends show concentric growth rings and drying cracks while
    the split faces show torn fibres along the grain."""
    m, g = _new(name, slot)
    lp = g.attr('lp'); A = g.attr('gA'); B = g.attr('gB'); Cc = g.attr('gC')
    u = g.vmath('DOT_PRODUCT', lp, A); v = g.vmath('DOT_PRODUCT', lp, B); w = g.vmath('DOT_PRODUCT', lp, Cc)
    rad = g.math('SQRT', g.math('ADD', g.math('MULTIPLY', v, v), g.math('MULTIPLY', w, w)))
    theta = g.math('ARCTAN2', w, v)
    r = g.attr('part_rand', 'Fac')
    seedv = g.node('ShaderNodeCombineXYZ'); g.link(g.math('MULTIPLY', r, 17.0), seedv.inputs[2])
    # growth rings, wobbling slightly around the circumference
    wob = g.noise(g.vmath('ADD', g.vmath('MULTIPLY', lp, (6, 6, 6)), seedv.outputs[0]), 1.0, 2, .5)
    rpm = g.math('MULTIPLY', g.math('ADD', .65, g.math('MULTIPLY', r, .8)), rings_per_m)      # 0.65x .. 1.45x per billet
    ring = g.math('SINE', g.math('MULTIPLY', g.math('ADD', rad, g.math('MULTIPLY', wob, .008)), g.math('MULTIPLY', rpm, math.tau)))
    ring = g.maprange(ring, -.2, 1.0)
    late = g.math('POWER', g.maprange(ring, .55, 1.0), 2.5)                                  # narrow latewood band
    # torn fibres along the grain on the split faces
    fv = g.node('ShaderNodeCombineXYZ')
    g.link(g.math('MULTIPLY', u, 1.4), fv.inputs[0]); g.link(g.math('MULTIPLY', v, 110.0), fv.inputs[1]); g.link(g.math('MULTIPLY', w, 110.0), fv.inputs[2])
    fib = g.maprange(g.noise(g.vmath('ADD', fv.outputs[0], seedv.outputs[0]), 1.0, 4, .6), .3, .7)
    N = g.geo('Normal')
    endf = g.maprange(g.math('ABSOLUTE', g.vmath('DOT_PRODUCT', N, A)), .6, .85)
    # on the sawn ends the fibre noise would read as blotches: use fine end-grain speckle there instead
    speck = g.maprange(g.noise(g.vmath('ADD', g.vmath('MULTIPLY', lp, (240, 240, 240)), seedv.outputs[0]), 1.0, 2, .5), .3, .7)
    side_t = g.math('ADD', g.math('MULTIPLY', ring, .22), g.math('MULTIPLY', fib, .78))
    end_t = g.math('SUBTRACT', g.math('ADD', .52, g.math('MULTIPLY', speck, .22)), g.math('MULTIPLY', late, .2))
    t = g.math('ADD', side_t, g.math('MULTIPLY', g.math('SUBTRACT', end_t, side_t), endf))
    d, l = hexl(dark), hexl(light)
    base = g.ramp(t, [(.15, tuple(c * .78 for c in d)), (.45, d), (.7, _lerp(d, l, .6)), (.95, l)])
    base = g.mul(1.0, base, g.ramp(r, [(0, (.72, .7, .68)), (.5, (.92, .9, .87)), (1, (1.08, 1.05, 1.0))]))
    # long drying checks and torn fibre shadows on the split faces
    kv = g.node('ShaderNodeCombineXYZ')
    g.link(g.math('MULTIPLY', u, .8), kv.inputs[0]); g.link(g.math('MULTIPLY', v, 26.0), kv.inputs[1]); g.link(g.math('MULTIPLY', w, 26.0), kv.inputs[2])
    sck = g.math('MULTIPLY', g.maprange(g.math('ABSOLUTE', g.math('SUBTRACT', g.noise(g.vmath('ADD', kv.outputs[0], seedv.outputs[0]), 1.0, 2, .5), .5)), .02, .0),
                 g.math('SUBTRACT', 1.0, endf))
    base = g.mix(g.math('MULTIPLY', sck, .8), base, tuple(c * .35 for c in hexl(dark)))
    # cut ends weather to a dull grey-brown within a season
    base = g.mix(g.math('MULTIPLY', endf, .5), base, hexl('#8C7A62'))
    # end faces: several radial drying checks round each end and a dark pith
    cv = g.node('ShaderNodeCombineXYZ'); g.link(g.math('MULTIPLY', theta, 4.5), cv.inputs[0]); g.link(g.math('MULTIPLY', r, 31.0), cv.inputs[1])
    chk = g.math('MULTIPLY', g.maprange(g.noise(cv.outputs[0], 1.0, 2, .4), .62, .7), g.maprange(rad, .008, .02))
    chk = g.math('MULTIPLY', chk, endf)
    base = g.mix(g.math('MULTIPLY', chk, .85), base, tuple(c * .3 for c in d))
    base = g.mix(g.math('MULTIPLY', g.maprange(rad, .009, .004), endf), base, tuple(c * .55 for c in d))
    # weathering: exposed old wood greys, the underside stays damp and dark
    P = g.geo('Position')
    gr = g.math('MULTIPLY', g.maprange(g.noise(P, 3.0, 3, .5), .35, .7), grey)
    base = g.mix(gr, base, hexl('#8A8070'))
    damp = g.math('MULTIPLY', g.maprange(_sepz(g, P), .12, .0), .6)
    base = g.mul(damp, base, (.55, .5, .45))
    ao = g.ao(.03)
    base = g.mul(1.0, base, g.ramp(ao, [(0, (.38, .34, .3)), (1, (1, 1, 1))]))
    h = g.math('SUBTRACT', g.math('ADD', g.math('MULTIPLY', ring, .3), g.math('MULTIPLY', fib, .5)), g.math('MULTIPLY', chk, 1.2))
    _finish(g, base, g.math('ADD', .8, g.math('MULTIPLY', fib, .1)), 0.0, g.bump(h, .5, .002), spec=.3)
    return m


def plate_bark(name, slot='Main', rough=.92, lichen=.5, moss=.3):
    """Thick old bark for firewood: plates stretched along the grain, split by deep dark fissures; each plate
    its own grey-brown, pale lichen rosettes on the plate tops, green moss down in the fissures."""
    m, g = _new(name, slot)
    co, r = _grain_coords(g, (1, 1, 1))
    # furrows between long bark plates: a strongly warped Voronoi (no honeycomb), big plates split again by a
    # finer, shallower crack network; furrow width varies along its length; each plate gets its own tone
    warp = g.vmath('MULTIPLY', g.vmath('SUBTRACT', g.noise(g.vmath('MULTIPLY', co, (2.5, 9, 9)), 1.0, 3, .55, out='Color'), (.5, .5, .5)), (.02, .11, .11))
    cs = g.vmath('ADD', g.vmath('MULTIPLY', co, (.22, 1, 1)), warp)
    e1 = g.voronoi(cs, 26.0, 'DISTANCE_TO_EDGE')
    e2 = g.voronoi(g.vmath('MULTIPLY', cs, (1.3, 1, 1)), 60.0, 'DISTANCE_TO_EDGE')
    wid = g.maprange(g.noise(g.vmath('MULTIPLY', co, (1.2, 4, 4)), 9.0, 2, .5), .3, .7, .1, .26)
    nd = g.node('ShaderNodeMapRange', clamp=True); g.link(e1, nd.inputs[0]); nd.inputs[1].default_value = .0; g.link(wid, nd.inputs[2])
    f1 = g.math('POWER', nd.outputs[0], .8)
    f2 = g.math('ADD', .55, g.math('MULTIPLY', g.maprange(e2, .0, .08), .45))
    flake = g.maprange(g.noise(g.vmath('MULTIPLY', co, (2, 9, 9)), 30.0, 3, .6), .35, .65)
    fis = g.math('MULTIPLY', g.math('MULTIPLY', f1, f2), g.math('ADD', .75, g.math('MULTIPLY', flake, .25)))
    cellc = g.voronoi(cs, 26.0, 'F1', 'Color')
    sc = g.node('ShaderNodeSeparateColor'); g.link(cellc, sc.inputs[0]); tone = sc.outputs[0]
    grain = g.maprange(g.noise(g.vmath('MULTIPLY', co, (3, 60, 60)), 1.0, 4, .6), .3, .7)
    top = g.math('MULTIPLY', fis, g.math('ADD', .75, g.math('MULTIPLY', grain, .25)))
    base = g.ramp(tone, [(.3, hexl('#4E4033')), (.5, hexl('#62543F')), (.7, hexl('#716552'))])
    base = g.mul(1.0, base, g.ramp(grain, [(0, (.8, .78, .76)), (1, (1.1, 1.08, 1.04))]))
    col = g.mix(g.maprange(fis, .6, .0), base, hexl('#2A2018'))  # dark furrows
    # weathered grey on the proud plate faces
    P = g.geo('Position'); N = g.geo('Normal')
    col = g.mix(g.math('MULTIPLY', g.maprange(top, .8, 1.0), .35), col, hexl('#8C8576'))
    # lichen rosettes, clustered
    li = g.math('MULTIPLY', g.maprange(g.noise(g.vmath('MULTIPLY', P, (1, 1, 1)), 22.0, 4, .7), .55, .68), g.maprange(g.noise(P, 4.0, 3, .5), .5, .64))
    col = g.mix(g.math('MULTIPLY', g.math('MULTIPLY', li, fis), lichen), col, hexl('#A3A893'))
    # moss in the fissures on the upper side
    up = g.maprange(_sepz(g, N), .1, .7)
    mo = g.math('MULTIPLY', g.math('MULTIPLY', g.maprange(fis, .5, .1), up), g.maprange(g.noise(P, 3.0, 3, .5), .45, .6))
    col = g.mix(g.math('MULTIPLY', mo, moss), col, hexl('#4C5A2A'))
    ao = g.ao(.03)
    col = g.mul(1.0, col, g.ramp(ao, [(0, (.38, .35, .32)), (1, (1, 1, 1))]))
    h = g.math('ADD', g.math('MULTIPLY', fis, .8), g.math('MULTIPLY', grain, .2))
    _finish(g, col, g.math('SUBTRACT', rough, g.math('MULTIPLY', top, .08)), 0.0, g.bump(h, 1.0, .012), spec=.3)
    return m
