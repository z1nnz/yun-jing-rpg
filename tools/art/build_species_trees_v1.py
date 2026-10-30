"""Tree species for the novice world, grown branch by branch, at the Elder World Tree's level of finish.

The Elder World Tree (z1nnz, elder-tree-esg; tools/art/build_elder_trees_v1.py) sets the bar: curved bark-textured
limbs with flared roots, and a canopy of thousands of real leaf cards with soft volume normals. Each species here
grows its own skeleton and its own leaf, so the trunks and crowns differ, not just the colours:

  Camphor   樟   a short trunk that splits into four or five big limbs; a full round crown of oval leaves
  Maple     楓   a short leaning trunk, limbs spreading flat; palmate five-lobed leaves, red to orange
  Ginkgo    銀杏 one straight leader to the top, short level branches; fan leaves, gold
  Willow    柳   a thick short trunk, limbs arching up, then curtains of hanging strands with narrow leaves
  Plum      梅   a zigzag gnarled trunk and angular limbs, straight thin shoots; five-petal blossom, no leaves
  Cypress   柏   one straight leader, dense rising branches in a narrow cone; flat scale-leaf sprays
  Withered  枯樹 a twisted dead trunk with broken limbs; a few curled brown leaves (the sick tree; 九夜's tree)

Bark: the Elder World Tree's bark albedo, retinted and re-contrasted per species. Leaf colour: a 64-swatch
palette per species (the leaves' UVs point at their swatch), unfiltered in Unity. Three LODs per tree
(<Tree>_LOD0..2): fewer branch levels, fewer ring sides and fewer, larger leaf cards.

Output: art/exports/elder-trees-v1/ (with the Guardian built by build_elder_trees_v1.py), review renders in
art/previews/elder-trees-v1/. Run: blender -b --factory-startup -P tools/art/build_species_trees_v1.py
"""
import json
import math
import random
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parents[2]
HERO = ROOT / 'art/exports/elder-world-tree-hero-v1/elder-world-tree-hero-v1.glb'
OUT = ROOT / 'art/exports/elder-trees-v1'
PREVIEW = ROOT / 'art/previews/elder-trees-v1'
SWATCHES = 64
UP = Vector((0, 0, 1))


# ---------------------------------------------------------------- leaf shapes (outline in metres; y along the leaf)
def outline_oval(n=8):
    return [(math.sin(a) * .5 * (1 - .35 * math.cos(a)), .5 - .5 * math.cos(a)) for a in (math.pi * 2 * i / n for i in range(n))]


def outline_palmate():
    pts = []
    for i in range(15):   # five lobes: tip, notch, tip ... around the base
        a = -math.pi * .95 + math.pi * 1.9 * i / 14
        r = .62 if i % 3 == 0 else .3 if i % 3 == 2 else .48
        pts.append((math.sin(a) * r, .3 + math.cos(a) * r))
    return [(0, 0)] + pts


def outline_fan():
    pts = [(0, 0), (-.06, .18)]
    for i in range(9):
        a = -1.05 + 2.1 * i / 8
        r = .5 if i != 4 else .42   # the notch in the middle of the fan
        pts.append((math.sin(a) * r, .18 + math.cos(a) * r * .8))
    return pts + [(.06, .18)]


def outline_lance():
    return [(0, 0), (-.07, .3), (0, 1), (.07, .3)]


def outline_spray():
    return [(0, 0), (-.18, .25), (-.28, .55), (-.12, .7), (0, 1), (.12, .7), (.28, .55), (.18, .25)]


def outline_curl():
    return [(0, 0), (-.25, .35), (-.1, .8), (.15, .6), (.2, .25)]


def petal(angle, r=.5):
    c, s = math.cos(angle), math.sin(angle)
    shape = [(0, .05), (-.24, .42), (0, .75), (.24, .42)]
    return [(x * c * r * 1.3 - y * s * r * 1.3 + 0, x * s * r * 1.3 + y * c * r * 1.3) for x, y in shape]


SHAPES = {'oval': [(0, 0), (-.4, .45), (0, 1), (.4, .45)],   # four corners, like the Elder World Tree's cards
          'palmate': [(0, 0)] + [(math.sin(math.radians(a)) * r, .42 + math.cos(math.radians(a)) * r)
                                 for a, r in ((-128, .26), (-100, .58), (-74, .3), (-48, .6), (-22, .32), (0, .58),
                                              (22, .32), (48, .6), (74, .3), (100, .58), (128, .26))],
          'fan': [(0, 0), (-.52, .72), (-.2, 1), (0, .86), (.2, 1), (.52, .72)],
          'lance': outline_lance(),
          'spray': [(0, 0), (-.36, .34), (-.14, .44), (-.3, .74), (0, 1), (.3, .74), (.14, .44), (.36, .34)],
          'curl': outline_curl(),
          'needle': [(0, 0), (-.08, .5), (0, 1), (.08, .5)]}

# ---------------------------------------------------------------- species
# Per level (0 = trunk): count of children, spread angle (deg), length ratio, radius ratio, gnarl, tropism.
SPECIES = {
    # Shapes follow the reference sheets in art/references/tree-species-v1/ (z1nnz, 2026-10-30): S-curved leaning
    # trunks, winding limbs, and foliage in many small clumps at the twig ends (bright tops, teal undersides) with
    # sky between them. trunk = (length, radius); lean/bend shape the trunk's S; cluster = clump radius (m); flat
    # squashes the clump vertically (pine pads).
    # 樟 (camphor.png): a massive twisting trunk leaning, splitting into four great winding limbs; a broad crown of
    # many leafy clumps.
    'Camphor': dict(barkref='camphor', height=12, trunk=(4.2, 1.0), lean=.3, bend=.95, gnarl=.12, zig=0, split=True,
                    levels=[dict(n=6, angle=(42, 68), length=1.6, radius=.7, start=.62, gnarl=.14, up=.2),
                            dict(n=5, angle=(30, 55), length=.55, radius=.6, start=.2, gnarl=.22, up=.12),
                            dict(n=4, angle=(30, 60), length=.48, radius=.55, start=.25, gnarl=.25, up=.1),
                            dict(n=3, angle=(25, 50), length=.45, radius=.5, start=.3, gnarl=.25, up=.15)],
                    leaf='oval', size=(.12, .19), cards=130000, cluster=.85, flat=.75, roots=4, flare=1.18,
                    bark=dict(tint='#8a6a4a', contrast=1.0, scale=(1.6, 1.0)),
                    colours=['#163f3c', '#1f5e48', '#3f8a3a', '#8cbc2c', '#d4e64a']),
    # 楓 (maple.png): a pale S-curved trunk, limbs reaching out in long curves; red to orange clumps.
    'Maple': dict(barkref='maple', height=8, trunk=(3.4, .52), lean=.3, bend=.75, gnarl=.12, zig=0, split=True,
                  levels=[dict(n=5, angle=(40, 70), length=1.15, radius=.6, start=.65, gnarl=.32, up=.05),
                          dict(n=4, angle=(30, 55), length=.55, radius=.55, start=.25, gnarl=.3, up=.08),
                          dict(n=4, angle=(30, 55), length=.45, radius=.5, start=.25, gnarl=.3, up=.1),
                          dict(n=3, angle=(25, 50), length=.4, radius=.5, start=.3, gnarl=.3, up=.12)],
                  leaf='palmate', size=(.13, .2), cards=60000, cluster=.85, flat=.7, roots=4, flare=1.18,
                  bark=dict(tint='#a49c8e', contrast=.5, scale=(1.4, .7)),
                  colours=['#6a1420', '#b0201e', '#e0381c', '#f07428', '#f8b040']),
    # 銀杏 (ginkgo.png): a leaning twisting trunk that carries on to the top, branches all the way up; airy gold.
    'Ginkgo': dict(barkref='ginkgo', floor=.25, height=12, trunk=(9.0, .7), lean=.7, bend=1.0, gnarl=.1, zig=0, split=False,
                   levels=[dict(n=11, angle=(40, 70), length=(.5, .18), radius=.45, start=.25, gnarl=.26, up=.08),
                           dict(n=4, angle=(30, 55), length=.45, radius=.55, start=.25, gnarl=.28, up=.12),
                           dict(n=3, angle=(25, 50), length=.42, radius=.5, start=.3, gnarl=.28, up=.15)],
                   leaf='fan', size=(.11, .16), cards=90000, cluster=.75, flat=.7, roots=4, flare=1.2,
                   bark=dict(tint='#8c8070', contrast=1.15, scale=(1.2, 1.6)),
                   colours=['#8a5a06', '#cc8a0c', '#eeb014', '#f8d22c', '#fcea7a']),
    # 柳 (willow.png): a gnarled trunk leaning hard over the water, long arching limbs, curtains hanging.
    'Willow': dict(barkref='willow', height=8, trunk=(3.0, .74), lean=.6, bend=.45, gnarl=.12, zig=0, split=True,
                   levels=[dict(n=5, angle=(35, 65), length=1.5, radius=.6, start=.7, gnarl=.3, up=.12),
                           dict(n=5, angle=(30, 55), length=.5, radius=.5, start=.3, gnarl=.28, up=.15),
                           dict(n=4, angle=(25, 50), length=.45, radius=.5, start=.3, gnarl=.25, up=.2),
                           dict(n=3, angle=(25, 50), length=.4, radius=.5, start=.3, gnarl=.25, up=.15)],
                   leaf='lance', size=(.13, .22), weep=(1.0, 3.4), strand=.075, spread=.0, cards=200000, strands=9, roots=4, flare=1.18,
                   bark=dict(tint='#7a7062', contrast=1.3, scale=(1.3, 1.3)),
                   colours=['#4a7448', '#76a444', '#b0d044', '#dcea58', '#f6f8a0']),
    # 梅: a zigzag gnarled dark trunk, angular limbs, blossom along the shoots (no reference sheet yet).
    'Plum': dict(barkref='plum', height=5, trunk=(2.0, .3), lean=.25, bend=.6, gnarl=.12, zig=.55, split=True,
                 levels=[dict(n=5, angle=(40, 75), length=1.4, radius=.62, start=.75, gnarl=.12, up=.1, zig=.5),
                         dict(n=5, angle=(30, 60), length=.55, radius=.5, start=.2, gnarl=.1, up=.18, zig=.3),
                         dict(n=5, angle=(25, 50), length=.45, radius=.45, start=.15, gnarl=.03, up=.35, zig=0)],
                 leaf='blossom', size=(.18, .26), cards=8000, along=1, spread=.08, roots=4, flare=1.18,
                 bark=dict(tint='#3e2f2a', contrast=1.25, scale=(1.0, .8)),
                 colours=['#5e1a2c', '#d47c96', '#eca8ba', '#f8d2dc', '#fff4f6']),
    # 松 (pine.png): a twisting S trunk, long near-level limbs that zigzag out, flat pads of needles at their ends.
    'Pine': dict(barkref='pine', floor=.3, height=10, trunk=(8.5, .58), lean=.3, bend=.8, gnarl=.1, zig=0, split=False,
                 levels=[dict(n=7, angle=(70, 88), length=(.8, .3), radius=.5, start=.42, gnarl=.3, up=-.02, zig=.35),
                         dict(n=4, angle=(30, 60), length=.4, radius=.5, start=.35, gnarl=.3, up=.05),
                         dict(n=3, angle=(25, 55), length=.4, radius=.5, start=.3, gnarl=.3, up=.1)],
                 leaf='needle', size=(.12, .18), cards=130000, cluster=.8, flat=.25, roots=4, flare=1.2,
                 bark=dict(tint='#8a6248', contrast=1.4, scale=(1.0, 1.0)),
                 colours=['#16301f', '#22482a', '#3a6a34', '#6a9440', '#a8c058']),
    # 圓柏 / 真柏 (Chinese juniper, the bonsai z1nnz pointed to): a low trunk of silver-white deadwood twisting with a
    # brown live vein, leaning hard to one side; limbs swing out level and one cascades down; the foliage is dense
    # flat pads of fine scale leaves, layered and uneven, bright on top.
    'Cypress': dict(barkref='juniper', floor=.4, height=7, trunk=(4.4, .7), lean=.55, bend=1.1, gnarl=.18, zig=0, split=True,
                    levels=[dict(n=6, angle=(55, 95), length=1.15, radius=.62, start=.3, gnarl=.3, up=.02, zig=.2),
                            dict(n=5, angle=(35, 70), length=.5, radius=.55, start=.2, gnarl=.3, up=.08),
                            dict(n=4, angle=(30, 65), length=.42, radius=.5, start=.2, gnarl=.3, up=.1)],
                    leaf='spray', size=(.1, .16), cards=120000, cluster=.85, flat=.4, roots=4, flare=1.25,
                    bark=dict(tint='#b8b4ac', contrast=1.6, scale=(.7, 3.2)),
                    colours=['#1a3a1e', '#2a5428', '#467a30', '#76a23a', '#b0c856']),
    # 枯樹: an old dead giant, a twisted forked trunk, snapped limbs, a fine net of bare twigs, a few curled leaves.
    'Withered': dict(barkref='juniper', height=10, trunk=(4.0, .85), lean=.15, bend=.35, gnarl=.1, zig=.08, split=True,
                     levels=[dict(n=4, angle=(22, 48), length=.85, radius=.62, start=.72, gnarl=.25, up=.15, broken=.3),
                             dict(n=5, angle=(30, 58), length=.55, radius=.5, start=.25, gnarl=.28, up=.08, broken=.25),
                             dict(n=5, angle=(30, 60), length=.48, radius=.45, start=.25, gnarl=.32, up=.05, broken=.15),
                             dict(n=4, angle=(30, 65), length=.45, radius=.45, start=.3, gnarl=.35, up=.02)],
                     leaf='curl', size=(.14, .2), per_twig=0, sparse_leaves=34, spread=.2, roots=4, flare=1.2,
                     bark=dict(tint='#5e5650', contrast=1.4, scale=(1.2, 1.4)),
                     colours=['#3a2a1c', '#5a4026', '#7a5a34', '#9a7a4a', '#b89a6a']),
}

LODS = [dict(levels=99, sides=1.0, leaves=1.0, grow=1.0), dict(levels=-1, sides=.55, leaves=.15, grow=2.1),
        dict(levels=-2, sides=.35, leaves=.04, grow=3.8)]


def hex_lin(h):
    def lin(c):
        return c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4
    return tuple(lin(int(h[i:i + 2], 16) / 255) for i in (1, 3, 5))


def gradient(stops, t):
    t = min(max(t, 0), 1) * (len(stops) - 1)
    i = min(int(t), len(stops) - 2)
    f = t - i
    a, b = hex_lin(stops[i]), hex_lin(stops[i + 1])
    return tuple(a[k] + (b[k] - a[k]) * f for k in range(3))


# ---------------------------------------------------------------- skeleton
class Limb:
    def __init__(self, pts, radii, level):
        self.pts, self.radii, self.level = pts, radii, level
        self.children, self.twig, self.strands = [], False, []


def rotate_towards(d, axis, angle):
    return (Quaternion(axis, angle) @ d).normalized()


def perpendicular(d):
    p = d.cross(Vector((1, 0, 0)) if abs(d.x) < .9 else Vector((0, 1, 0)))
    return p.normalized()


def walk(start, direction, length, r0, r1, gnarl, up, zig, rng, twist=0, floor=-1e9, ceiling=1e9):
    """A branch as real ones grow: it bends smoothly along one curve whose plane turns slowly (no step-by-step
    wobble), reaches toward the light, and the longer and thinner it is the more its outer part sags under its own
    weight. `gnarl` is how much it curves overall; `up` how strongly it seeks the light; plum's `zig` adds the
    angular turns of an old flowering branch at a few nodes."""
    n = max(6, int(length / .22))
    pts, radii = [start.copy()], [r0]
    d = direction.normalized()
    plane = (Quaternion(d, rng.uniform(0, math.tau)) @ perpendicular(d)).normalized()
    curve = rng.gauss(0, 1) * gnarl * 2.2                    # total bend over the branch, radians
    wave, phase = rng.uniform(.6, 1.4), rng.uniform(0, math.tau)
    turn = rng.gauss(0, 1) * gnarl * 1.5                     # how far the bending plane rotates along the branch
    sag = max(0.0, length * .045 - r0 * 1.5) * (1 if up < .3 else .4)
    nodes = {int(n * f) for f in (rng.uniform(.25, .4), rng.uniform(.55, .7), rng.uniform(.8, .9))} if zig else set()
    for i in range(1, n + 1):
        t = i / n
        k = curve * (1 + .6 * math.sin(math.tau * wave * t + phase)) / n
        plane = (Quaternion(d, turn / n) @ plane).normalized()
        d = (Quaternion(plane.cross(d).normalized() if plane.cross(d).length > 1e-6 else perpendicular(d), k) @ d).normalized()
        if i in nodes:
            d = (Quaternion(perpendicular(d), rng.choice((-1, 1)) * zig * rng.uniform(.5, .9)) @ d).normalized()
        d = (d + UP * up * 3.0 / n - UP * sag * t * 2.2 / n).normalized()
        z = pts[-1].z
        if z < floor and d.z < .15:
            d = (d + UP * .5).normalized()
        if z > ceiling and d.z > -.05:
            d = Vector((d.x, d.y, d.z * .3 - .05)).normalized()
        if twist:
            plane = Quaternion(d, twist / n) @ plane
        pts.append(pts[-1] + d * length / n)
        radii.append(r0 + (r1 - r0) * t ** .8)
    return pts, radii


def point_at(limb, t):
    f = t * (len(limb.pts) - 1)
    i = min(int(f), len(limb.pts) - 2)
    k = f - i
    p = limb.pts[i].lerp(limb.pts[i + 1], k)
    r = limb.radii[i] + (limb.radii[i + 1] - limb.radii[i]) * k
    d = (limb.pts[i + 1] - limb.pts[i]).normalized()
    return p, r, d


def grow(spec, rng):
    h, r = spec['trunk']
    # The trunk's S: it leans one way, bends back over its length and drifts a little sideways, plus a little
    # gnarl. Radius tapers to the fork (split) or toward the top (a leader that carries on).
    az = rng.uniform(0, math.tau)
    d, side = Vector((math.cos(az), math.sin(az), 0)), Vector((-math.sin(az), math.cos(az), 0))
    n = max(8, int(h / .3))
    bend, lean = spec.get('bend', 0), spec['lean']
    pts, radii = [], []
    wob = Vector()
    for i in range(n + 1):
        t = i / n
        if i:
            wob += Vector((rng.gauss(0, 1), rng.gauss(0, 1), 0)) * spec['gnarl'] * .08
        off = d * (lean * h * t ** 1.8 + bend * h * .32 * math.sin(math.pi * t * 1.6) * t) + side * (bend * h * .14 * math.sin(math.tau * t * .8) * t)
        pts.append(off + wob * t + Vector((0, 0, h * t)))
        radii.append(r * (1 - (1 - (.58 if spec['split'] else .12)) * t ** .9))
    trunk = Limb(pts, radii, 0)
    levels = spec['levels']

    def branch(parent, depth):
        if depth >= len(levels):
            parent.twig = True
            return
        lv = levels[depth]
        az = rng.random() * math.tau
        for k in range(lv['n']):
            t = lv['start'] + (1 - lv['start']) * (k + rng.random() * .6) / lv['n']
            t = min(t, .995)
            p, pr, pd = point_at(parent, t)
            az += math.radians(137.5) + (rng.random() - .5) * .5
            out = (Quaternion(pd, az) @ perpendicular(pd)).normalized()
            ang = math.radians(rng.uniform(*lv['angle']))
            d = (pd * math.cos(ang) + out * math.sin(ang)).normalized()
            plen = sum((parent.pts[i + 1] - parent.pts[i]).length for i in range(len(parent.pts) - 1))
            ratio = lv['length']
            if isinstance(ratio, tuple):   # excurrent crowns: long low branches, short high ones
                ratio = ratio[0] + (ratio[1] - ratio[0]) * (t - lv['start']) / max(1 - lv['start'], 1e-6)
                length = spec['height'] * ratio * rng.uniform(.8, 1.15)
            else:
                length = plen * ratio * rng.uniform(.75, 1.15)
            if lv.get('broken') and rng.random() < lv['broken']:
                length *= rng.uniform(.25, .5)   # a snapped limb: short and blunt
            cr = max(pr * lv['radius'], .012)
            start = p - d * pr * .6   # start inside the parent so the joint has no seam
            cpts, cradii = walk(start, d, length, cr, max(cr * .32, .006), lv['gnarl'], lv['up'], lv.get('zig', 0), rng,
                               floor=h * spec.get('floor', .55), ceiling=spec['height'] * spec.get('dome', 1.0))
            child = Limb(cpts, cradii, depth + 1)
            child.broken = lv.get('broken') and length < plen * ratio * .55 if not isinstance(lv['length'], tuple) else False
            parent.children.append(child)
            branch(child, depth + 1)

    branch(trunk, 0)
    # Willow: curtains of hanging strands from the outer twigs.
    if spec.get('weep'):
        for limb in all_limbs(trunk):
            if limb.twig:
                for _ in range(spec.get('strands', 3)):
                    p, _, d = point_at(limb, rng.uniform(.4, 1))
                    length = rng.uniform(*spec['weep'])
                    out = Vector((d.x, d.y, 0)).normalized() * .25
                    strand = [p]
                    for i in range(1, 12):
                        t = i / 11
                        strand.append(p + out * math.sin(t * 1.4) + Vector((0, 0, -length * t)) + Vector((rng.random() - .5, rng.random() - .5, 0)) * .04)
                    limb.strands.append(strand)
    return trunk


def all_limbs(root):
    out, stack = [], [root]
    while stack:
        l = stack.pop()
        out.append(l)
        stack.extend(l.children)
    return out


# ---------------------------------------------------------------- meshes
def smooth(pts, radii, k=2):
    for _ in range(k):
        np_, nr = [pts[0]], [radii[0]]
        for i in range(len(pts) - 1):
            np_ += [pts[i].lerp(pts[i + 1], .25), pts[i].lerp(pts[i + 1], .75)]
            nr += [radii[i] * .75 + radii[i + 1] * .25, radii[i] * .25 + radii[i + 1] * .75]
        np_.append(pts[-1])
        nr.append(radii[-1])
        pts, radii = np_, nr
    return pts, radii


def tube(bm, uv, pts, radii, sides_scale, bark_scale, rng, flare=0, cap=True):
    pts, radii = smooth(pts, radii, 2 if len(pts) < 30 else 1)
    sides = max(4, min(16, int(max(radii) * 46 * sides_scale) + 3))
    tangent = [(pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized() for i in range(len(pts))]
    normal = perpendicular(tangent[0])
    rings, v = [], 0.0
    bump = [rng.random() for _ in range(sides)]
    for i, p in enumerate(pts):
        if i:
            normal = (tangent[i - 1].rotation_difference(tangent[i]) @ normal).normalized()
            v += (pts[i] - pts[i - 1]).length
        binormal = tangent[i].cross(normal)
        r = radii[i]
        if flare and i < len(pts) * .06:   # a slight widening where the trunk meets the ground
            r *= 1 + (flare - 1) * (1 - i / (len(pts) * .06)) ** 2
        ring = []
        for s in range(sides + 1):
            a = math.tau * s / sides
            ridge = 1 + .08 * (bump[s % sides] - .5) * (1 if r > .05 else 0)
            ring.append(bm.verts.new(p + (normal * math.cos(a) + binormal * math.sin(a)) * r * ridge))
        rings.append((ring, v))
    for i in range(len(rings) - 1):
        (a, va), (b, vb) = rings[i], rings[i + 1]
        for s in range(sides):
            f = bm.faces.new((a[s], a[s + 1], b[s + 1], b[s]))
            us = (s / sides * bark_scale[0], (s + 1) / sides * bark_scale[0])
            for loop, (uu, vv) in zip(f.loops, ((us[0], va), (us[1], va), (us[1], vb), (us[0], vb))):
                loop[uv].uv = (uu, vv * bark_scale[1] / max(.6, radii[0] * 6))
    if cap:
        last, vl = rings[-1]
        tip = bm.verts.new(pts[-1] + tangent[-1] * radii[-1] * 1.5)
        for s in range(sides):
            f = bm.faces.new((last[s], last[s + 1], tip))
            for loop in f.loops:
                loop[uv].uv = (s / sides * bark_scale[0], vl * bark_scale[1])


def roots(spec, trunk, rng):
    out = []
    r0 = trunk.radii[0]
    for k in range(spec['roots']):
        a = math.tau * (k + rng.random() * .5) / spec['roots']
        d = Vector((math.cos(a), math.sin(a), 0))
        # A short root swelling out of the trunk foot and diving into the soil (no root legs, no swollen skirt).
        reach, rise, depth = r0 * rng.uniform(1.3, 2.0), r0 * rng.uniform(.45, .8), r0 * rng.uniform(.8, 1.2)
        pts = [d * (r0 * .2 + reach * (i / 8) ** .75) + Vector((0, 0, rise * (1 - i / 8) ** 1.8 - depth * (i / 8) ** 2.2)) for i in range(9)]
        out.append((pts, [r0 * .3 * (1 - .5 * i / 8) for i in range(9)]))
    return out


def leaf_cards(spec, trunk, rng, lod, crown_centre):
    """Leaf (or blossom) cards: (vertices, faces, colour t per face, normals) for the species."""
    cards = []
    lo, hi = spec['size']
    limbs = all_limbs(trunk)
    twigs = [l for l in limbs if l.twig]
    shape = spec['leaf']
    keep = lod['leaves']

    def card(origin, axis, facing, length, t):
        side = axis.cross(facing).normalized()
        face_n = side.cross(axis).normalized()
        if shape == 'blossom':
            polys = [petal(math.tau * k / 5 + rng.random() * .3) for k in range(5)]
            verts = []
            faces = []
            for poly in polys:
                idx = []
                for x, y in poly:
                    idx.append(len(verts))
                    verts.append(origin + side * x * length + axis * y * length * .35 + face_n * y * length * .1)
                faces.append((idx, t))
            # The dark heart of the flower.
            idx = []
            for k in range(5):
                a = math.tau * k / 5
                idx.append(len(verts))
                verts.append(origin + (side * math.cos(a) + axis * math.sin(a) * .35) * length * .14 + face_n * .01)
            faces.append((idx, 0.0))
            return verts, faces
        wide = rng.uniform(.75, 1.2)
        pts = [(x * wide * (1 + rng.uniform(-.2, .2)), y * (1 + rng.uniform(-.15, .15)) if y else 0) for x, y in SHAPES[shape]]
        verts = [origin + side * x * length + axis * y * length for x, y in pts]
        # A slight fold down the midrib so the card is not flat.
        verts = [v + face_n * (abs(x) * -.05 * length) for v, (x, y) in zip(verts, pts)]
        return verts, [(list(range(len(verts))), t)]

    def tone(p, extra=0):
        height = (p.z - crown_centre.z) / max(spec['height'] * .5, 1)
        inner = (p - crown_centre).length / max(spec['height'] * .5, 1)
        return min(max(.45 + height * .22 + inner * .15 + (rng.random() - .5) * .8 + extra, .02), .99)

    if spec.get('weep'):
        total = sum((s[i] - s[i - 1]).length for l in twigs for s in l.strands for i in range(1, len(s)))
        per_m = spec['cards'] / max(total, 1e-3)
        for l in twigs:
            for strand in l.strands:
                for i in range(1, len(strand)):
                    a, b = strand[i - 1], strand[i]
                    steps = max(1, int((b - a).length * per_m))
                    for k in range(steps):
                        if rng.random() > keep:
                            continue
                        p = a.lerp(b, k / steps) + Vector((rng.random() - .5, rng.random() - .5, rng.random() - .5)) * .06
                        out = Vector((p.x, p.y, 0)).normalized() if p.xy.length > .01 else Vector((1, 0, 0))
                        axis = (Vector((0, 0, -1)) + out * .5 + Vector((rng.random() - .5, rng.random() - .5, 0)) * .8).normalized()
                        cards.append(card(p, axis, rotate_towards(out, UP, rng.random() * 2 - 1), rng.uniform(lo, hi) * lod['grow'], tone(p)))
        return cards
    if spec.get('along'):   # plum: blossom along the thin shoots, not only at the tips
        shoots = [x for x in limbs if x.level >= len(spec['levels']) - 1]
        for l in shoots:
            n = spec['cards'] // max(len(shoots), 1)
            for k in range(n):
                if rng.random() > keep:
                    continue
                p, r, d = point_at(l, rng.random())
                out = perpendicular(d)
                out = Quaternion(d, rng.random() * math.tau) @ out
                cards.append(card(p + out * r, out, d, rng.uniform(lo, hi) * lod['grow'], rng.uniform(.25, .98)))
        return cards
    if spec.get('sparse_leaves'):   # withered: a handful of curled leaves hanging on
        for _ in range(int(spec['sparse_leaves'] * max(keep, .3))):
            l = rng.choice(twigs)
            p, _, d = point_at(l, rng.uniform(.5, 1))
            cards.append(card(p, (d + Vector((0, 0, -1.5))).normalized(), perpendicular(d), rng.uniform(lo, hi) * lod['grow'], rng.random()))
        return cards
    # Clumps at the twig ends (the reference sheets): each twig carries a clump of leaves around its tip and a few
    # along its last third. Each clump has its own shade; within it, leaves on top catch the sun and leaves
    # underneath fall into cool shade, so the crown reads as many small lit clumps with sky between them.
    per = spec['cards'] // max(len(twigs), 1)
    for l in twigs:
        tip = l.pts[-1]
        cl = spec['cluster'] * rng.uniform(.75, 1.25)
        centre = tip + UP * cl * .35
        shade = rng.uniform(-.14, .14) + .1 * ((tip.z - crown_centre.z) / max(spec['height'] * .5, 1))
        for k in range(per):
            if rng.random() > keep:
                continue
            u = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1))).normalized()
            if u.z < -.3:
                u.z = -.3 - (u.z + .3) * .3   # a flatter underside
            depth = rng.random() ** .3
            if rng.random() < .1:   # a few leaves along the twig itself
                p, _, d = point_at(l, rng.uniform(.45, .95))
                pos = p + u * cl * .35 * depth
            else:
                pos = centre + Vector((u.x * cl, u.y * cl, u.z * cl * spec['flat'])) * depth
            axis = (u + Vector((rng.random() - .5, rng.random() - .5, rng.random() - .5)) * .8).normalized()
            t = .48 + .5 * u.z + shade - (1 - depth) * .38 + (rng.random() - .5) * .12
            cards.append(card(pos, axis, u, rng.uniform(lo, hi) * lod['grow'], min(max(t, .02), .99)))
    return cards


# ---------------------------------------------------------------- materials and textures
# ---------------------------------------------------------------- painted foliage clusters
REFS = ROOT / 'art/references/tree-species-v1'


def foliage_atlas(name, species):
    """z1nnz's hand-painted leaf-cluster sheet (leaves-<species>.png: nine clusters in a 3 x 3 grid on white) made
    into a game texture: white keyed out to alpha, the colour under transparent pixels filled with the cluster's
    own leaf colour so mipmaps don't fringe white. None when there is no sheet for this species yet."""
    src = REFS / f'leaves-{species}.png'
    if not src.exists():
        return None
    img = bpy.data.images.load(str(src))
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    rgb = px[..., :3]
    # Distance from white: the strongest channel's shortfall (yellow highlights keep their alpha: blue is low).
    d = (1 - rgb).max(axis=2)
    a = np.clip((d - .12) / .14, 0, 1)
    a = a * a * (3 - 2 * a)
    leaf = a > .9
    fill = rgb[leaf].mean(axis=0) if leaf.any() else np.array([.3, .5, .2], dtype=np.float32)
    # Edge pixels are blended with the white paper: pull them toward the leaf colour so no pale fringe shows.
    rgb = np.where(a[..., None] < .9, rgb * a[..., None] + fill * (1 - a[..., None]), rgb)
    rgb = np.clip(rgb, 0, 1)
    out = np.concatenate([rgb, a[..., None]], axis=2).astype(np.float32)
    atlas = bpy.data.images.new(f'Elder{name}_Foliage', w, h, alpha=True)
    atlas.pixels = out.ravel().tolist()
    atlas.scale(1024, 1024)
    atlas.filepath_raw = str(OUT / f'Elder{name}_Foliage.png')
    atlas.file_format = 'PNG'
    atlas.save()
    bpy.data.images.remove(img)
    return atlas


def foliage_cards(spec, skeleton, rng, lod_index, crown_centre):
    """Painted clusters on cards at the twig ends: each card faces out from the crown, stays upright (the sheet is
    lit from above) and shows one of the nine clusters. Willow cards hang from their top edge. Fewer, larger cards
    for the far LODs. Returns (four corners, four uvs) per card."""
    twigs = [l for l in all_limbs(skeleton) if l.twig]
    # The bar is z1nnz's Elder World Tree (art/references/tree-species-v1/benchmark-elder-tree.jpg): a thin, airy
    # layer of foliage on the branch ends with sky and limbs showing through, not a stuffed crown.
    per, grow_, keep = [(spec.get('cards_per_twig', 2), 1.0, .95), (1, 1.5, .8), (1, 2.0, .55)][lod_index]
    weep = bool(spec.get('weep'))
    out = []
    for l in twigs:
        if rng.random() > keep:
            continue
        tip = l.pts[-1]
        cl = spec.get('cluster', .7) * rng.uniform(.8, 1.2)
        for _ in range(per):
            pos = tip + Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, .5))) * cl * .2
            n = (pos - crown_centre)
            n = n.normalized() if n.length > .01 else Vector((0, -1, 0))
            n = (n + Vector((rng.gauss(0, .25), rng.gauss(0, .25), 0))).normalized()
            n.z = max(min(n.z, .35), -.15)
            n.normalize()
            up = (UP - n * n.dot(UP)).normalized()
            up = Quaternion(n, rng.uniform(-.3, .3)) @ up
            side = up.cross(n).normalized()
            size = cl * rng.uniform(1.3, 1.9) * grow_
            hw, hh = size * .5, size * (.75 if weep else .5)
            centre = pos - up * hh * .9 if weep else pos
            cell = rng.randrange(9)
            cu, cv = cell % 3, 2 - cell // 3
            m = .012
            u0, u1, v0, v1 = cu / 3 + m, (cu + 1) / 3 - m, cv / 3 + m, (cv + 1) / 3 - m
            corners = [centre - side * hw - up * hh, centre + side * hw - up * hh, centre + side * hw + up * hh, centre - side * hw + up * hh]
            out.append((corners, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]))
    return out


def bark_image(name, src, spec):
    painted = REFS / f"bark-{spec.get('barkref', name.lower())}.png"
    if painted.exists():
        img = bpy.data.images.load(str(painted))
        img.scale(1024, 1024)
        img.filepath_raw = str(OUT / f'{name}.png')
        img.file_format = 'PNG'
        img.save()
        return img
    return bark_image_from_elder(name, src, spec)


def bark_image_from_elder(name, src, spec):
    w, h = src.size
    px = np.array(src.pixels[:], dtype=np.float32).reshape(h, w, 4)
    grey = px[..., :3] @ np.array([.2126, .7152, .0722], dtype=np.float32)
    mean = grey.mean()
    c = spec['bark']['contrast']
    g = np.clip(mean + (grey - mean) * c, 0, 1) / max(mean, 1e-3)
    tint = np.array(hex_lin(spec['bark']['tint']), dtype=np.float32)
    rgb = np.clip(g[..., None] * tint[None, None, :] * 1.0, 0, 1)
    # Keep a little of the source's own hue (the moss and warm cracks).
    rgb = rgb * .8 + px[..., :3] * (tint.mean() / max(px[..., :3].mean(), 1e-3)) * .2
    out = np.concatenate([np.clip(rgb, 0, 1), np.ones((h, w, 1), dtype=np.float32)], axis=2)
    img = bpy.data.images.new(name, w, h, alpha=False)
    img.pixels = out.ravel().tolist()
    img.scale(1024, 1024)
    img.filepath_raw = str(OUT / f'{name}.png')
    img.file_format = 'PNG'
    img.save()
    return img


def palette_image(name, stops):
    img = bpy.data.images.new(name, SWATCHES, 4, alpha=False)
    px = []
    for _ in range(4):
        for s in range(SWATCHES):
            c = gradient(stops, (s + .5) / SWATCHES)
            px += [((x * 12.92) if x <= .0031308 else (1.055 * x ** (1 / 2.4) - .055)) for x in c] + [1]
    img.pixels = px
    img.filepath_raw = str(OUT / f'{name}.png')
    img.file_format = 'PNG'
    img.save()
    return img


def material(name, img, rough):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = img
    if name.endswith('_Leaves'):
        tex.interpolation = 'Closest'
    mat.node_tree.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = rough
    return mat


# ---------------------------------------------------------------- build
def build(name, spec, src_bark):
    seed = sum(map(ord, name))
    bark_mat = material(f'Elder{name}_Bark', bark_image(f'Elder{name}_Bark', src_bark, spec), .9)
    atlas = foliage_atlas(name, spec.get('atlas', name.lower()))
    leaf_mat = material(f'Elder{name}_Leaves', atlas if atlas is not None else palette_image(f'Elder{name}_Leaves', spec['colours']), .75)
    if atlas is not None:
        tex = next(n for n in leaf_mat.node_tree.nodes if n.type == 'TEX_IMAGE')
        tex.interpolation = 'Linear'
        leaf_mat.node_tree.links.new(tex.outputs['Alpha'], next(n for n in leaf_mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Alpha'])
        try:
            leaf_mat.blend_method = 'CLIP'
        except Exception:
            pass
    root = bpy.data.objects.new(f'Elder{name}', None)
    bpy.context.collection.objects.link(root)
    rng = random.Random(seed)
    skeleton = grow(spec, rng)
    limbs = all_limbs(skeleton)
    tips = [l.pts[-1] for l in limbs if l.twig] or [skeleton.pts[-1]]
    crown_centre = sum(tips, Vector()) / len(tips)
    rootlist = roots(spec, skeleton, random.Random(seed + 7))
    tris = []
    for i, lod in enumerate(LODS):
        bm = bmesh.new()
        uv = bm.loops.layers.uv.new('UVMap')
        rng_l = random.Random(seed * 10 + i)
        max_level = len(spec['levels']) + (lod['levels'] if lod['levels'] < 0 else 0)
        for limb in limbs:
            if limb.level > max_level:
                continue
            tube(bm, uv, limb.pts, limb.radii, lod['sides'], spec['bark']['scale'], rng_l, flare=spec['flare'] if limb.level == 0 else 0,
                 cap=not (limb.level == 0 and spec['split']))
        for pts, radii in rootlist:
            tube(bm, uv, pts, radii, lod['sides'], spec['bark']['scale'], rng_l)
        wood_faces = len(bm.faces)
        # Willow strands: very thin hanging tubes the leaves hang on (LOD0 and LOD1).
        if spec.get('weep') and i < 2 and atlas is None:
            for limb in limbs:
                for strand in limb.strands:
                    tube(bm, uv, strand, [spec['strand'] * .2] * len(strand), .3, spec['bark']['scale'], rng_l, cap=False)
        me = bpy.data.meshes.new(f'Elder{name}_LOD{i}')
        bm.to_mesh(me)
        bm.free()
        me.materials.append(bark_mat)
        me.materials.append(leaf_mat)
        # Leaves.
        verts, faces, uvs, norms = [], [], [], []
        if atlas is not None:
            for corners, cuv in foliage_cards(spec, skeleton, random.Random(seed * 100 + i), i, crown_centre):
                base = len(verts)
                verts += corners
                faces.append([base, base + 1, base + 2, base + 3])
                uvs.append(cuv)
        else:
            for cv, cf in leaf_cards(spec, skeleton, random.Random(seed * 100 + i), lod, crown_centre):
                base = len(verts)
                verts += cv
                for idx, t in cf:
                    faces.append([base + j for j in idx])
                    u = (min(int(t * SWATCHES), SWATCHES - 1) + .5) / SWATCHES
                    uvs.append([(u, .5)] * len(idx))
        if verts:
            lm = bpy.data.meshes.new('leaves')
            lm.from_pydata(verts, [], faces)
            luv = lm.uv_layers.new(name='UVMap')
            for poly, u in zip(lm.polygons, uvs):
                poly.material_index = 1
                for k, li in enumerate(poly.loop_indices):
                    luv.data[li].uv = u[k]
            # Soft canopy shading: leaf normals lean out from the crown centre.
            lm.normals_split_custom_set([((Vector(lm.vertices[lm.loops[li].vertex_index].co) - crown_centre).normalized() * .75
                                          + lm.polygons[p.index].normal * .25).normalized()
                                         for p in lm.polygons for li in p.loop_indices])
            tmp = bpy.data.objects.new('tmp_leaves', lm)
            wood = bpy.data.objects.new(f'Elder{name}_LOD{i}', me)
            for o in (tmp, wood):
                bpy.context.collection.objects.link(o)
            lm.materials.append(bark_mat)
            lm.materials.append(leaf_mat)
            bpy.ops.object.select_all(action='DESELECT')
            tmp.select_set(True)
            wood.select_set(True)
            bpy.context.view_layer.objects.active = wood
            bpy.ops.object.join()
        else:
            wood = bpy.data.objects.new(f'Elder{name}_LOD{i}', me)
            bpy.context.collection.objects.link(wood)
        wood.parent = root
        tris.append(sum(len(p.vertices) - 2 for p in wood.data.polygons))
    bpy.ops.object.select_all(action='DESELECT')
    root.select_set(True)
    for c in root.children:
        c.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT / f'Elder{name}.fbx'), use_selection=True, object_types={'MESH', 'EMPTY'},
                             axis_forward='-Z', axis_up='Y', apply_scale_options='FBX_SCALE_ALL',
                             bake_space_transform=True, mesh_smooth_type='OFF', path_mode='RELATIVE',
                             add_leaf_bones=False, bake_anim=False)
    lod0 = bpy.data.objects[f'Elder{name}_LOD0']
    pts = [v.co for v in lod0.data.vertices]
    size = [round(max(p[k] for p in pts) - min(p[k] for p in pts), 2) for k in range(3)]
    return root, {'triangles_per_lod': tris, 'size_m': size, 'leaf': spec['leaf']}


def render(roots_):
    scene = bpy.context.scene
    for e in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
        try:
            scene.render.engine = e
            break
        except TypeError:
            pass
    scene.render.resolution_x, scene.render.resolution_y = 2800, 1000
    world = bpy.data.worlds.new('w')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.78, .84, .88, 1)
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(50), 0, math.radians(35))
    sun.data.energy = 3.5
    x = 0
    for r in roots_:
        for c in r.children:
            c.hide_render = not c.name.endswith('LOD0')
        xs = [v.co.x for c in r.children if c.name.endswith('LOD0') for v in c.data.vertices]
        r.location.x = x - min(xs)
        x += max(xs) - min(xs) + 1.5
    # Ground, so the review shows the trees as planted: buried roots hidden, only the part above the soil.
    bpy.ops.mesh.primitive_plane_add(size=1, location=(x / 2, 0, 0))
    ground = bpy.context.active_object
    ground.scale = (x + 40, 60, 1)
    soil = bpy.data.materials.new('ReviewSoil')
    soil.use_nodes = True
    next(n for n in soil.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = (.24, .3, .14, 1)
    ground.data.materials.append(soil)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.lens = 30
    cam.location = (x / 2, -x * .8, 5)
    cam.rotation_euler = (math.radians(88), 0, 0)
    scene.render.filepath = str(PREVIEW / 'species-lineup.png')
    bpy.ops.render.render(write_still=True)
    # Each tree whole, three-quarter view from a little above eye height, as on the reference sheets, so they can be
    # compared side by side with art/references/tree-species-v1/<species>.png.
    scene.render.resolution_x, scene.render.resolution_y = 1200, 1000
    cam.data.lens = 35
    for r in roots_:
        lod0 = next(c for c in r.children if c.name.endswith('LOD0'))
        vs = [r.matrix_world @ v.co for v in lod0.data.vertices]
        lo = Vector((min(v.x for v in vs), min(v.y for v in vs), 0)); hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
        c = (lo + hi) / 2
        size = max(hi.x - lo.x, hi.y - lo.y, hi.z)
        cam.location = c + Vector((size * .55, -size * 1.25, -hi.z * .5 + 1.7 + size * .08))
        cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str(PREVIEW / f'{r.name}-full.png')
        bpy.ops.render.render(write_still=True)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    PREVIEW.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(HERO))
    src_bark = next(i for i in bpy.data.images if 'bark' in i.name.lower())
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    report, roots_ = {}, []
    for name, spec in SPECIES.items():
        root, info = build(name, spec, src_bark)
        roots_.append(root)
        report[f'Elder{name}'] = info
    render(roots_)
    (OUT / 'species-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('SPECIES_TREES ' + json.dumps(report, ensure_ascii=False))


main()
