"""Trace z1nnz's black-on-white tree skeleton sheets (art/references/tree-species-v1/skeleton-<species>.png) into
branch frames for build_authored_trees_v1.py.

The left part of each sheet is the front view. Its silhouette is thinned to a centre line (skimage), the radius at
every centre-line pixel comes from the distance to the background, and the centre-line graph is walked from the
trunk foot: at each fork the thicker side carries on as the same branch and the others start new branches, short
spurs are dropped. The front view gives x (across) and z (up); depth comes from turning each first-order limb
round the trunk by its own angle, its children following it, so the tree reads as the drawing from the front and
fills out in the round. Output: art/references/tree-species-v1/skeleton-<species>.json, metres, z up, foot at 0.

Run: python tools/art/trace_tree_skeleton.py camphor juniper ginkgo plum willow
"""
import json
import math
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage
from skimage.morphology import skeletonize

ROOT = Path(__file__).resolve().parents[2]
REFS = ROOT / 'art/references/tree-species-v1'
HEIGHT = {'camphor': 12.0, 'juniper': 8.0, 'ginkgo': 14.0, 'plum': 6.0, 'willow': 10.0}


def front_view(img):
    """The left drawing: columns up to the widest white gap between the two drawings."""
    a = np.asarray(img.convert('L'), dtype=np.float32) / 255
    ink = (a < .5)
    cols = ink.sum(axis=0)
    w = ink.shape[1]
    best, start, run = (0, w), None, 0
    for x in range(int(w * .3), int(w * .85)):
        if cols[x] == 0:
            if start is None:
                start = x
            if x - start > best[1] - best[0] or best == (0, w):
                best = (start, x)
        else:
            start = None
    cut = (best[0] + best[1]) // 2 if best != (0, w) else w
    return ink[:, :cut]


def trace(name):
    img = Image.open(REFS / f'skeleton-{name}.png')
    scale = 1000 / max(img.size)
    img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
    ink = front_view(img)
    ink = ndimage.binary_closing(ink, iterations=1)
    dist = ndimage.distance_transform_edt(ink)
    sk = skeletonize(ink)
    ys, xs = np.nonzero(sk)
    pix = set(zip(ys.tolist(), xs.tolist()))
    # Trunk foot: the lowest centre-line pixel among the thickest near the bottom.
    bottom = max(ys)
    near = [(y, x) for y, x in pix if y > bottom - 40]
    root = max(near, key=lambda p: dist[p] * 3 + p[0])
    parent, order = {root: None}, [root]
    q = deque([root])
    while q:
        p = q.popleft()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                n = (p[0] + dy, p[1] + dx)
                if n in pix and n not in parent:
                    parent[n] = p
                    order.append(n)
                    q.append(n)
    children = {p: [] for p in order}
    for p in order[1:]:
        children[parent[p]].append(p)
    # Weight of each subtree (ink it carries): the thicker side continues the branch at a fork.
    weight = {}
    for p in reversed(order):
        weight[p] = dist[p] ** 2 + sum(weight[c] for c in children[p])
    ground = root[0]
    top = min(y for y, x in order)
    m_per_px = HEIGHT[name] / max(ground - top, 1)
    branches = []

    def walk(start, parent_idx, depth, first_dir):
        pts = [start]
        p = start
        while True:
            kids = sorted(children[p], key=lambda c: -weight[c])
            if not kids:
                break
            for k in kids[1:]:
                pending.append((k, len(branches), depth + 1, None))
            p = kids[0]
            pts.append(p)
        length = len(pts)
        r0 = dist[pts[0]]
        if length < max(6, r0 * 2.5) and depth > 0:   # a spur, not a branch
            return
        branches.append(dict(px=pts, parent=parent_idx, depth=depth))

    pending = deque([(root, -1, 0, None)])
    while pending:
        s, pi, d, fd = pending.popleft()
        walk(s, pi, d, fd)
    # Depth: each first-order limb turns round the trunk by its own angle; children follow their limb.
    rng = np.random.default_rng(len(name) * 97)
    turn = {}
    out = []
    rx = root[1]
    for i, b in enumerate(branches):
        if b['parent'] < 0:
            a = 0.0
        elif branches[b['parent']]['parent'] < 0:
            a = float(rng.uniform(-1.1, 1.1))
        else:
            a = turn.get(b['parent'], 0.0) + float(rng.uniform(-.35, .35))
        turn[i] = a
        pts = b['px'][::4] + ([b['px'][-1]] if len(b['px']) % 4 != 1 else [])
        if len(pts) < 2:
            pts = [b['px'][0], b['px'][-1]]
        xyz, radii = [], []
        for y, x in pts:
            u = (x - rx) * m_per_px
            z = (ground - y) * m_per_px
            xyz.append([round(u * math.cos(a), 3), round(u * math.sin(a), 3), round(z, 3)])
            radii.append(round(max(dist[(y, x)] * m_per_px, .012), 3))
        out.append(dict(parent=b['parent'], depth=b['depth'], points=xyz, radii=radii))
    data = dict(species=name, height=HEIGHT[name], branches=out)
    (REFS / f'skeleton-{name}.json').write_text(json.dumps(data), encoding='utf-8')
    tips = sum(1 for i, b in enumerate(out) if not any(c['parent'] == i for c in out))
    print(f'{name}: {len(out)} branches, {tips} tips, trunk radius {out[0]["radii"][0]:.2f} m, {m_per_px * 1000:.1f} mm/px')


if __name__ == '__main__':
    for n in sys.argv[1:] or list(HEIGHT):
        trace(n)
