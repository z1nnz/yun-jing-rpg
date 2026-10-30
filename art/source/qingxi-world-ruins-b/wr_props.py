"""Batch 2 props for qingxi-world-ruins-b: R05 milestone (more to follow in this module).

Blender Z-up, 1 unit = 1 m, front faces -Y, origin at the footprint centre, z = 0 at ground level.
"""
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix, noise
import wr_core as C
from wr_core import S
import wr_materials as WM


def _keep_slots(o, name, mat, **kw):
    """C.finish clears the material list, which in Blender 5 also resets every face's slot index:
    keep the indices set while building and restore them."""
    idx = [0] * len(o.data.polygons); o.data.polygons.foreach_get('material_index', idx)
    o = C.finish(o, name, mat, **kw)
    o.data.polygons.foreach_set('material_index', idx)
    return o


def _bm_part(name, bm, mat, sharp=34, **kw):
    """Object from a finished bmesh, shaded like wr_core.rock (smooth with faceted chips)."""
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); C._uv_box(me)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    kw.setdefault('grain', 'x')
    o = _keep_slots(o, name, mat, **kw)
    for f in o.data.polygons: f.use_smooth = True
    o.data.set_sharp_from_angle(angle=math.radians(sharp))
    m = o.modifiers.new('Facet_normals', 'WEIGHTED_NORMAL'); m.keep_sharp = True; m.weight = 50
    return o


# ---------------------------------------------------------------- R05 milestone
MS_W, MS_D, MS_H, MS_EMBED = .58, .34, 1.35, .25
PANEL = (.34, .65, .33)          # blank inscription face: width, height, bottom edge above ground


def r05_milestone():
    """Rough-quarried upright stone, rounded shoulders, a sunk and dressed blank panel on the road face (-Y).
    The panel is left blank on purpose: the game writes the place names, not the model."""
    stone = WM.stone('M_R05_Stone', tones=('#5A6264', '#3F4648', '#7A8282'), warm='#76705F', moss=1.0, moss_top=.7, lichen=1.0,
                     relief=2.4, scale=.8, rosettes=1.3, small_rosettes=1.0, lichen_cover=.6, moss_low=.8, rosette_scale=7.0, ground_dirt=.4)
    # the dressed panel is the same stone, tooled smoother and a little paler, with only young lichen on it
    dressed = WM.stone('M_R05_Panel', tones=('#7C7F79', '#6A6D68', '#8A8C86'), warm='#7E786C', moss=.1, lichen=.4,
                       small_rosettes=.35, ground_dirt=0, relief=.45, rough=.84)
    full = MS_H + MS_EMBED
    bm = C.rock_mesh((MS_W, MS_D, full), 5011, sub=30, round_=.3, chips=24, chip_depth=(.05, .24), wobble=.08,
                     flat_bottom=.95, taper=-.03)
    pw, ph, pz = PANEL
    zs = [v.co.z for v in bm.verts]; z0, z1 = min(zs), max(zs)
    ylim = -MS_D / 2 * .78
    for v in bm.verts:
        if v.co.y < ylim: v.co.y = ylim + (v.co.y - ylim) * .18      # road face roughly dressed flat
        v.co.z = -MS_EMBED + (v.co.z - z0) * full / (z1 - z0)        # bottom exactly at the embed depth, top at 1.35
        # rounded shoulders: the top narrows towards a blunt, knocked crown
        t = max(0.0, (v.co.z - 1.1) / (MS_H - 1.1))
        v.co.x *= 1 - .2 * t ** 1.5
        v.co.y *= 1 - .12 * t ** 1.5
        # quarry-face roughness finer than the chips: shallow lumps every few centimetres
        n = noise.noise(v.co * 7.0 + Vector((11.0, 3.0, 5.0))) + .5 * noise.noise(v.co * 17.0 + Vector((2.0, 9.0, 4.0)))
        n += .35 * noise.noise(v.co * 31.0 + Vector((5.0, 1.0, 8.0)))
        v.co += v.co.normalized() * (.012 if v.co.y > ylim + .01 else .005) * n
    # split faces: planes slice shallow caps off the block, each leaving one flat, crisp-edged facet, the
    # angular faces of a quarried, frost-split stone. The road face is left for the dressed panel.
    rf = random.Random(5012)
    for k in range(46):
        a = rf.uniform(0, 2 * math.pi); el = rf.uniform(-.25, .75)
        nrm = Vector((math.cos(a) * math.cos(el), math.sin(a) * math.cos(el) * 1.5, math.sin(el))).normalized()
        if nrm.y < -.55: continue
        far = max(v.co.dot(nrm) for v in bm.verts)
        cut = far - rf.uniform(.012, .045)
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=nrm * cut, plane_no=nrm, clear_outer=True)
        edges = [e for e in bm.edges if e.is_boundary]
        if edges:
            bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], quad_method='BEAUTY', ngon_method='BEAUTY')
    bm.normal_update()
    # cut the panel outline into the mesh, then press the face inside it back onto one plane
    for co, no in (((pw / 2, 0, 0), (1, 0, 0)), ((-pw / 2, 0, 0), (1, 0, 0)), ((0, 0, pz), (0, 0, 1)), ((0, 0, pz + ph), (0, 0, 1)),
                   ((pw / 2 + .008, 0, 0), (1, 0, 0)), ((-pw / 2 - .008, 0, 0), (1, 0, 0)),
                   ((0, 0, pz - .008), (0, 0, 1)), ((0, 0, pz + ph + .008), (0, 0, 1)),
                   ((pw / 2 + .04, 0, 0), (1, 0, 0)), ((-pw / 2 - .04, 0, 0), (1, 0, 0)),
                   ((0, 0, pz - .04), (0, 0, 1)), ((0, 0, pz + ph + .04), (0, 0, 1))):
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no)
    inside = lambda c, m=0.0: abs(c.x) < pw / 2 + m and pz - m < c.z < pz + ph + m and c.y < -.05
    ys = sorted(v.co.y for v in bm.verts if inside(v.co, .04))
    y_face = ys[len(ys) // 2]                  # the dressed margin around the panel lies on one plane
    off = Vector((3.1, 7.7, 1.3))
    for v in bm.verts:
        c = v.co
        if c.y > -.05: continue
        d = max(abs(c.x) - pw / 2, pz - c.z, c.z - pz - ph, 0.0)      # distance outside the panel rectangle
        if d <= 1e-4:
            # sunk 12 mm; dressed, not polished: a faint tooled waviness
            c.y = y_face + .012 + .002 * noise.noise(Vector((c.x * 9, 0, c.z * 9)) + off)
        elif d < .07:
            w = 1.0 if d <= .02 else 1 - ((d - .02) / .05) ** 2 * (3 - 2 * (d - .02) / .05)   # a narrow dressed margin, then rough stone
            c.y += (y_face + .0015 * noise.noise(c * 12 + off) - c.y) * w
    bm.normal_update()
    o = _bm_part('Milestone_Body', bm, stone, grain='z')
    o.data.materials.append(dressed)
    for f in o.data.polygons:
        c = f.center
        if abs(c.x) < pw / 2 and pz < c.z < pz + ph and c.y < -.05 and f.normal.y < -.85: f.material_index = 1
        elif abs(c.x) < pw / 2 + .01 and pz - .01 < c.z < pz + ph + .01 and y_face - .002 < c.y < y_face + .014: f.material_index = 1
    # a few frost spalls at the foot, half buried
    rr = random.Random(55)
    for k, (x, y) in enumerate(((.36, -.12), (-.33, .1), (.12, .25))):
        s = rr.uniform(.07, .11)
        C.rock(f'Spall_{k}', (x, y, s * .15), (s * 1.4, s, s * .55), stone, 600 + k, rot=(rr.uniform(-.3, .3), rr.uniform(-.3, .3), rr.uniform(0, 3)),
               sub=1, round_=.35, chips=4, wobble=.08, flat_bottom=.7, detail=1)
    hw, hd = MS_W / 2 + .01, MS_D / 2 + .01
    pts = [(x * hw, y * hd, -MS_EMBED) for x in (-1, 1) for y in (-1, 1)]
    pts += [(x * hw * .98, y * hd, 1.02) for x in (-1, 1) for y in (-1, 1)]
    pts += [(x * hw * .62, y * hd * .9, MS_H) for x in (-1, 1) for y in (-1, 1)]
    C.hull('Collision', pts)


# ---------------------------------------------------------------- R04 stone lanterns
def _block(name, c, size, mat, seed, top=1.0, chips=6, depth=(.04, .12), round_=.12, wob=.012, rough=.003, cuts=(), extra=()):
    """A dressed but weathered stone block: boxy, edges knocked, top and bed worked flat, optional taper
    (top = top width / bottom width). c = (x, y, z of the bed). cuts = fracture planes (point, normal):
    the stone beyond each plane is broken away and the fresh break gets material slot 1."""
    sx, sy, sz = size
    n = min(14, max(3, int(max(size) / .035)))
    bm = C.rock_mesh(size, seed, sub=n, round_=round_, chips=chips, chip_depth=depth, wobble=wob)
    for v in bm.verts:
        h = sz / 2 * .9
        if v.co.z > h: v.co.z = h + (v.co.z - h) * .15
        if v.co.z < -h: v.co.z = -h + (v.co.z + h) * .15
    bm.normal_update()
    zs = [v.co.z for v in bm.verts]; z0, z1 = min(zs), max(zs)
    off = Vector((seed * .37, seed * .11, 3.0))
    for v in bm.verts:
        t = (v.co.z - z0) / (z1 - z0)
        v.co.z = c[2] + t * sz
        s = 1 + (top - 1) * t
        v.co.x *= s; v.co.y *= s
        v.co += v.normal * rough * noise.noise(v.co * 23 + off)
        v.co.x += c[0]; v.co.y += c[1]
    for co, no in cuts:
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no, clear_outer=True)
        edges = [e for e in bm.edges if e.is_boundary]
        if edges:
            for f in bmesh.ops.holes_fill(bm, edges=edges, sides=0)['faces']: f.material_index = 1
    if len(bm.faces) < 4:
        bm.free(); return None
    if cuts:
        # a break is never a clean plane: ring the fresh faces inwards a few times, then lift and sink the
        # inner points with a coarse noise so the break surface reads as conchoidal, granular stone
        bm.normal_update()
        for th in (.008, .012, .014):
            fresh_f = [f for f in bm.faces if f.material_index == 1]
            if not fresh_f: break
            bmesh.ops.inset_individual(bm, faces=fresh_f, thickness=th, depth=0, use_even_offset=True)
        fresh_f = [f for f in bm.faces if f.material_index == 1]
        bmesh.ops.triangulate(bm, faces=[f for f in fresh_f if len(f.verts) > 4])
        bm.normal_update()
        offb = Vector((seed * .7, 1.0, seed * .3))
        for v in bm.verts:
            fs = v.link_faces
            if fs and all(f.material_index == 1 for f in fs):
                n_ = sum((f.normal for f in fs), Vector()).normalized()
                v.co += n_ * (.012 * noise.noise(v.co * 18 + offb) + .005 * noise.noise(v.co * 55 + offb))
    bm.normal_update()
    o = _bm_part(name, bm, mat, grain='z')
    for m in extra: o.data.materials.append(m)
    return o


def _bite(o, cutters):
    """Break chunks out of a part: boolean difference with irregular rock-shaped cutters whose material
    (the fresh-break stone) carries over onto the new surfaces. Returns None if nothing is left."""
    for cut in cutters:
        # a bite only takes a notch: if a solver collapses the part (it can, on the mesh a previous bite left),
        # put the part back and try the other solver, else leave this notch out
        keep = o.data.copy(); n0 = len(o.data.polygons)
        box = lambda me: [f(v.co[i] for v in me.vertices) for f in (min, max) for i in range(3)]
        b0 = box(keep)
        for solver in ('EXACT', 'FLOAT', None):
            if solver is None:                     # neither solver gave a clean notch: leave this one out
                bad = o.data; o.data = keep.copy(); bpy.data.meshes.remove(bad); break
            m = o.modifiers.new('Break', 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.solver = solver
            m.object = cut; m.material_mode = 'TRANSFER'
            o.modifiers.move(len(o.modifiers) - 1, 0)
            C._active(o); bpy.ops.object.modifier_apply(modifier=m.name)
            # a difference can only take stone away: it must keep most of the part and never grow past it
            if len(o.data.polygons) > n0 * .5 and all(
                    (b1 >= a - 1e-3) if k < 3 else (b1 <= a + 1e-3) for k, (a, b1) in enumerate(zip(b0, box(o.data)))):
                break
            bad = o.data; o.data = keep.copy(); bpy.data.meshes.remove(bad)
        bpy.data.meshes.remove(keep)
    if len(o.data.polygons) < 4:
        C.drop_part(o); return None
    return o


def _rim_cutters(fresh, w, seed, top=1.25):
    """Rock-shaped cutters strung round the top of the open chamber: each bites a jagged notch to its own
    depth, so the surviving rim is uneven, deepest at the front middle, near full height at the back-right."""
    rr = random.Random(seed); cutters = []
    spots = [(-.3, -1, .05), (.2, -1, .1), (1, -.3, .04), (.25, 1, .025), (-.4, 1, .05), (-1, .35, .09),
             (.75, -1, .03), (-1, -.6, .035), (1, .6, .07), (-.8, 1, .03)]
    for k, (u, v, depth) in enumerate(spots):
        if depth <= 0: continue
        sz = (rr.uniform(.13, .2), rr.uniform(.13, .2), rr.uniform(.16, .22))
        rm = C.rock_mesh(sz, seed + k, sub=2, round_=.35, chips=7, chip_depth=(.08, .25), wobble=.12)
        # the cutter must be a clean closed solid for the exact boolean: take the convex hull of the rock,
        # which also gives the bite the flat conchoidal facets of split stone
        bm = bmesh.new()
        for rv in rm.verts: bm.verts.new(rv.co)
        rm.free()
        res = bmesh.ops.convex_hull(bm, input=bm.verts[:])
        bmesh.ops.delete(bm, geom=list({g for g in res['geom_interior'] + res['geom_unused'] if isinstance(g, bmesh.types.BMVert) and g.is_valid}), context='VERTS')
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        c = Vector((u * w / 2, v * w / 2, top + sz[2] / 2 - depth))
        bm.transform(Matrix.Translation(c) @ Matrix.Rotation(rr.uniform(0, 3), 4, 'Z') @ Matrix.Rotation(rr.uniform(-.25, .25), 4, 'X'))
        me = bpy.data.meshes.new(f'Cutter_{k}'); bm.to_mesh(me); bm.free()
        me.materials.append(fresh)
        co = bpy.data.objects.new(f'Cutter_{k}', me); bpy.context.scene.collection.objects.link(co)
        co.hide_render = True; cutters.append(co)
    return cutters


def _roof_cap(name, mat, seed, prof, n=10):
    """Four-slope stone cap from square rings (half-width, z), bottom to top, capped at both ends."""
    bm = bmesh.new(); rings = []
    for hw, z in prof:
        ring = []
        for side in range(4):
            for i in range(n):
                t = -1 + 2 * i / n
                x, y = ((t, -1), (1, t), (-t, 1), (-1, -t))[side]
                ring.append(bm.verts.new((x * hw, y * hw, z)))
        rings.append(ring)
    m = 4 * n
    for A, B in zip(rings, rings[1:]):
        for i in range(m):
            bm.faces.new((A[i], A[(i + 1) % m], B[(i + 1) % m], B[i]))
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > .02], cuts=2)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    rr = random.Random(seed); off = Vector((rr.random() * 9, rr.random() * 9, 1.0))
    # knocked eave corners and a few edge chips, then a hand-worked unevenness
    pts = [v.co for v in bm.verts]
    for k in range(9):
        a = math.pi / 4 + math.pi / 2 * rr.randrange(4) + rr.uniform(-.5, .5)
        nrm = Vector((math.cos(a), math.sin(a), rr.uniform(-.4, .5))).normalized()
        cut = max(p.dot(nrm) for p in pts) - rr.uniform(.012, .035)
        for p in pts:
            d = p.dot(nrm) - cut
            if d > 0: p -= nrm * d
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * .004 * noise.noise(v.co * 19 + off)
    return _bm_part(name, bm, mat, grain='z')


def _soot_inside(o, centre, idx, top=None):
    """Faces turned into the lamp chamber (and its floor) take the soot slot."""
    cx, cy = centre
    for f in o.data.polygons:
        c = f.center; nrm = f.normal
        inward = Vector((cx - c.x, cy - c.y, 0))
        if inward.length > 1e-4 and nrm.dot(inward.normalized()) > .6: f.material_index = idx
        elif top is not None and nrm.z > .8 and abs(c.x - cx) < top and abs(c.y - cy) < top: f.material_index = idx


LT_EMBED = .05


def _lantern_mats(tag):
    stone = WM.stone(f'M_{tag}_Stone', tones=('#686C66', '#4C514C', '#878A82'), warm='#7A7462', moss=1.0, moss_top=1.8,
                     lichen=1.0, relief=1.8, scale=.8, rosettes=.8, small_rosettes=1.0, lichen_cover=1.0)
    fresh = WM.stone(f'M_{tag}_Break', tones=('#8E887C', '#7A746A', '#A09A8C'), warm='#9C8C70', moss=0, lichen=0,
                     ground_dirt=0, relief=1.3, scale=.8)
    soot = WM.stone(f'M_{tag}_Soot', tones=('#4A4C4B', '#353737', '#5A5B58'), warm='#4E453A', moss=0, lichen=.1,
                    ground_dirt=0, soot=.7, relief=.9, scale=.8)
    return stone, fresh, soot


def _lantern_base(stone, d, seed):
    """Foot, step, shaft with an old repaired seam, collar(s) and the flared fire-box table. Returns the parts."""
    parts = []
    parts.append(_block('Foot', (0, 0, -LT_EMBED), (d['foot'], d['foot'], d['foot_h'] + LT_EMBED), stone, seed, chips=9, depth=(.05, .14)))
    z = d['foot_h']
    parts.append(_block('Foot_Step', (0, 0, z), (d['step'], d['step'], .04), stone, seed + 1, chips=5, depth=(.05, .2)))
    z += .04
    sb, st = d['shaft']; zs = d['seam']; zt = d['shaft_top']
    tw = sb + (st - sb) * (zs - z) / (zt - z)
    parts.append(_block('Shaft_Lower', (0, 0, z), (sb, sb, zs - z), stone, seed + 2, top=tw / sb, chips=7, depth=(.04, .12)))
    # the repair: the upper drum was reset 6 mm off true on a lime bed
    mortar = WM.stone(f'M_{stone.name[2:6]}_Mortar', tones=('#9C9482', '#8A8270', '#ABA493'), warm='#A0927A', moss=0, lichen=.2,
                      ground_dirt=0, relief=.6)
    parts.append(_block('Shaft_Repair_Bed', (0, 0, zs), (tw * .985, tw * .985, .008), mortar, seed + 3, chips=0, wob=.003))
    parts.append(_block('Shaft_Upper', (.006, -.004, zs + .008), (tw, tw, zt - zs - .008), stone, seed + 4, top=st / tw, chips=7, depth=(.04, .12)))
    z = zt
    for k, (w, h) in enumerate(d['collars']):
        parts.append(_block(f'Collar_{k}', (0, 0, z), (w, w, h), stone, seed + 5 + k, chips=4, depth=(.05, .2)))
        z += h
    tb, tt, th = d['table']
    parts.append(_block('Firebox_Table', (0, 0, z), (tb, tb, th), stone, seed + 8, top=tt / tb, chips=8, depth=(.04, .12)))
    return parts, z + th


def _lantern_chamber(stone, fresh, soot, d, z, seed, cutters=()):
    """Sill with a sooted lamp socket, four corner posts, a set-back wall panel in every face pierced by a
    square window, and a lintel ring on top. cutters = rock solids that break the upper ring and whatever
    else they reach away to a jagged rim, as when the cap was thrown down."""
    parts = []
    w, pw, sh, ph, lh = d['sill'], d['post'], d['sill_h'], d['post_h'], d['lintel_h']
    sill = _block('Chamber_Sill', (0, 0, z), (w, w, sh), stone, seed, chips=7, depth=(.05, .14), extra=(fresh, soot))
    _soot_inside(sill, (0, 0), 2, top=w / 2 - pw)
    parts.append(sill); z += sh
    sock = C.lathe('Lamp_Socket', [(.0, -.004), (.05, -.004), (.052, .012), (.04, .016), (.03, .006), (.0, .004)], (0, 0, z), soot, seg=12)
    parts.append(sock)
    # wall panels: set back from the post faces, each with a square window; the strips butt into the posts
    ow, oh = d['window']; tp = .032; span = w - 2 * pw + .02
    pc = w / 2 - pw * .6
    bh = (ph - oh) / 2; sw = (span - ow) / 2
    for k, (ax, s_) in enumerate((('y', -1), ('x', 1), ('y', 1), ('x', -1))):
        strips = [(0, bh / 2, span, bh), (0, ph - bh / 2, span, bh),
                  (-(ow + sw) / 2, ph / 2, sw, oh + .004), ((ow + sw) / 2, ph / 2, sw, oh + .004)]
        for j, (u, zc, lu, lz) in enumerate(strips):
            if ax == 'y': c, size = (u, s_ * pc, z + zc - lz / 2), (lu, tp, lz)
            else: c, size = (s_ * pc, u, z + zc - lz / 2), (tp, lu, lz)
            st = _block(f'Panel_{k}_{j}', c, size, stone, seed + 40 + 4 * k + j, chips=3, depth=(.03, .1), round_=.08,
                        rough=.004, extra=(fresh, soot))
            _soot_inside(st, (0, 0), 2)
            if cutters:
                st = _bite(st, cutters)
                if st is None: continue
            parts.append(st)
    o = w / 2 - pw / 2
    for k, (sx, sy) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        post = _block(f'Post_{k}', (sx * o, sy * o, z), (pw, pw, ph), stone, seed + 10 + k, top=.97,
                      chips=6, depth=(.06, .18), rough=.005, extra=(fresh, soot))
        _soot_inside(post, (0, 0), 2)
        if cutters:
            post = _bite(post, cutters)
            if post is None: continue
        parts.append(post)
    z += ph - .008                                # lintels bed slightly into the post heads
    lw = pw * 1.05
    for k, (axis, s_) in enumerate((('x', -1), ('y', 1), ('x', 1), ('y', -1))):
        if axis == 'x':
            c, size = (0, s_ * (w / 2 - lw / 2), z), (w, lw, lh)
        else:
            c, size = (s_ * (w / 2 - lw / 2), 0, z), (lw, w - 2 * lw + .006, lh)
        lin = _block(f'Lintel_{k}', c, size, stone, seed + 20 + k, chips=6, depth=(.05, .2), rough=.005, extra=(fresh, soot))
        _soot_inside(lin, (0, 0), 2)
        if cutters:
            lin = _bite(lin, cutters)
            if lin is None: continue             # broken away entirely
        parts.append(lin)
    return parts, z + .008 + lh


R04_DIMS = dict(
    intact=dict(foot=.56, foot_h=.15, step=.42, shaft=(.33, .235), seam=.49, shaft_top=.80, collars=((.30, .05),),
                table=(.48, .52, .12), sill=.40, sill_h=.05, post=.09, post_h=.19, lintel_h=.06, window=(.13, .12)),
    broken=dict(foot=.58, foot_h=.14, step=.45, shaft=(.34, .265), seam=.45, shaft_top=.66, collars=((.33, .04), (.31, .035)),
                table=(.52, .56, .13), sill=.44, sill_h=.05, post=.10, post_h=.19, lintel_h=.145, window=(.16, .13)),
)


def r04_lantern_intact():
    """Roadside stone lantern, whole: foot, tapered shaft with an old reset seam, fire-box table, open lamp
    chamber sooted inside, four-slope stone cap and a blunt finial. 1.65 m, 0.68 m at the eaves."""
    stone, fresh, soot = _lantern_mats('R04I')
    d = R04_DIMS['intact']
    base, z = _lantern_base(stone, d, 4100)
    ch, z = _lantern_chamber(stone, fresh, soot, d, z, 4130)
    zr = z
    # thick eave, then concave slopes rising to a small square crown block
    roof = _roof_cap('Roof_Cap', stone, 4150, [(.185, zr), (.31, zr + .01), (.34, zr + .025), (.34, zr + .06), (.315, zr + .075),
                                               (.25, zr + .1), (.18, zr + .13), (.125, zr + .165), (.1, zr + .2)])
    z = zr + .2
    fb = _block('Finial_Seat', (0, 0, z), (.14, .14, .04), stone, 4160, chips=4, depth=(.05, .2))
    z += .04
    hb = 1.65 - z
    bud = [(0, 0), (.042, 0), (.055, hb * .1), (.062, hb * .34), (.056, hb * .6), (.036, hb * .82), (.012, hb * .96), (0, hb)]
    fin = C.lathe('Finial_Bud', bud, (0, 0, z), stone, seg=8)
    fin.data.set_sharp_from_angle(angle=math.radians(30))
    C.hull('Collision_Foot', C.world_points(base[0]) + C.world_points(base[1]))
    C.hull('Collision_Shaft', [p for o in base[2:] for p in C.world_points(o)])
    C.hull('Collision_Head', [p for o in ch + [roof, fb, fin] for p in C.world_points(o)])


def r04_lantern_broken():
    """The same lantern family with its cap long gone: the windowed chamber still stands, but its tall upper
    ring is broken to a jagged rim at uneven heights; the lamp basin is sooted. 1.25 m, 0.58 m footprint."""
    stone, fresh, soot = _lantern_mats('R04B')
    d = R04_DIMS['broken']
    base, z = _lantern_base(stone, d, 4200)
    cutters = _rim_cutters(fresh, d['sill'], 4240)
    ch, z = _lantern_chamber(stone, fresh, soot, d, z, 4230, cutters=cutters)
    for co in cutters: bpy.data.objects.remove(co, do_unlink=True)
    C.hull('Collision_Foot', C.world_points(base[0]) + C.world_points(base[1]))
    C.hull('Collision_Shaft', [p for o in base[2:] for p in C.world_points(o)])
    C.hull('Collision_Head', [p for o in ch for p in C.world_points(o)])


# ---------------------------------------------------------------- R03 firewood
def _section(R, kind, ang):
    """Billet cross-section in its own (y, z) plane, pith at the origin: [(y, z, edge kind)], edge kind
    0 = bark, 1 = split face. A sector starts at angle 0; the roll given to the billet orients it."""
    prof = []
    if kind == 'round':
        n = 26
        for i in range(n):
            a = i * math.tau / n
            prof.append((R * math.cos(a), R * math.sin(a), 0))
        return prof
    if kind == 'half': ang = math.pi
    n = max(5, int(ang / .13)); nsplit = 4
    for i in range(nsplit):                             # pith -> bark along the first split face
        t = i / nsplit
        prof.append((R * t, 0.0, 1))
    for i in range(n + 1):                              # the bark arc
        a = ang * i / n
        prof.append((R * math.cos(a), R * math.sin(a), 0 if i < n else 1))
    for i in range(1, nsplit):                          # bark -> pith along the second split face
        t = 1 - i / nsplit
        prof.append((R * t * math.cos(ang), R * t * math.sin(ang), 1))
    return prof


def _section_world(prof, roll, step=.005):
    """Outline of a billet laid along +Y (Euler (roll, 0, pi/2)) as (X, Z) points, densely resampled,
    relative to the cross-section centroid."""
    cy = sum(p[0] for p in prof) / len(prof); cz = sum(p[1] for p in prof) / len(prof)
    c, s_ = math.cos(roll), math.sin(roll)
    pts = []
    for i in range(len(prof)):
        y0, z0 = prof[i][0] - cy, prof[i][1] - cz
        y1, z1 = prof[(i + 1) % len(prof)][0] - cy, prof[(i + 1) % len(prof)][1] - cz
        k = max(1, int(math.hypot(y1 - y0, z1 - z0) / step))
        for j in range(k):
            y = y0 + (y1 - y0) * j / k; z = z0 + (z1 - z0) * j / k
            yr, zr = y * c - z * s_, y * s_ + z * c
            pts.append((-yr, zr))                       # local y maps to world -x after the 90 degree yaw
    return pts


def _billet_mesh(L, R, kind, ang, seed, tilt=(0.0, 0.0)):
    """Split firewood billet along local X, origin on the pith so the shader's growth rings centre there.
    kind: 'round' (whole small log), 'half' or 'split' (a sector of ang radians). Bark faces get slot 0,
    split faces and the sawn ends slot 1. Returns (bmesh, cross-section centroid (y, z))."""
    rr = random.Random(seed)
    off = Vector((rr.random() * 30, rr.random() * 30, rr.random() * 30))
    prof = _section(R, kind, ang)
    taper = rr.uniform(-.12, .12)
    bow = (rr.uniform(-.1, .1) * R * L / .5, rr.uniform(-.1, .1) * R * L / .5)
    m = max(4, int(L / .045))
    bm = bmesh.new(); rings = []
    np_ = len(prof)
    for j in range(m + 1):
        s = j / m
        ring = []
        for i, (y, z, k) in enumerate(prof):
            x = -L / 2 + L * s
            if j in (0, m):                             # sawn or snapped ends, never quite square
                x += (tilt[0] * y + tilt[1] * z) * (1 if j == m else -1) * .8
            p = Vector((x, y * (1 + taper * (s - .5)), z * (1 + taper * (s - .5))))
            p.y += bow[0] * (4 * s * (1 - s) - .5); p.z += bow[1] * (4 * s * (1 - s) - .5)
            rad = math.hypot(y, z)
            if rad > 1e-4:
                if k == 0 or (kind == 'round'):
                    # bark: lumpy, with long shallow furrows
                    th = math.atan2(z, y)
                    fis = abs(noise.noise(Vector((x * 2.2, math.cos(th) * 2.4, math.sin(th) * 2.4)) + off))
                    d = .06 * R * noise.noise(Vector((x * 3, y / R * 2, z / R * 2)) + off) \
                        + .045 * R * min(1.0, fis * 5) - .03 * R
                    p.y += y / rad * d; p.z += z / rad * d
                else:
                    # split face: torn fibres, ridges running with the grain
                    nx, ny = -z / rad, y / rad
                    d = .011 * noise.noise(Vector((x * 5, rad * 55, 0)) + off) + .007 * noise.noise(Vector((x * 1.5, rad * 9, 3)) + off)
                    d += .008 * max(0.0, noise.noise(Vector((x * 9, rad * 20, 7)) + off) - .25)   # a raised splinter here and there
                    p.y += nx * d; p.z += ny * d
            ring.append(bm.verts.new(p))
        rings.append(ring)
    for j in range(m):
        A, B = rings[j], rings[j + 1]
        for i in range(np_):
            f = bm.faces.new((A[i], A[(i + 1) % np_], B[(i + 1) % np_], B[i]))
            f.material_index = 0 if (kind == 'round' or prof[i][2] == 0) else 1
    # end caps: a rim of bark round the sawn face (inner ring at 0.88 R), the face itself never quite flat
    for ring, rev in ((rings[0], True), (rings[-1], False)):
        cen = sum((v.co for v in ring), Vector()) / np_
        sgn = -1 if rev else 1
        inner = []
        for i, v in enumerate(ring):
            bark_v = kind == 'round' or prof[i][2] == 0
            q = cen + (v.co - cen) * (.88 if bark_v else .97)
            q.x += sgn * (-.003 + .004 * noise.noise(q * 30 + off))
            inner.append(bm.verts.new(q))
        for i in range(np_):
            j = (i + 1) % np_
            f = bm.faces.new((ring[i], inner[i], inner[j], ring[j]) if rev else (ring[i], ring[j], inner[j], inner[i]))
            f.material_index = 0 if (kind == 'round' or (prof[i][2] == 0 and prof[j][2] == 0)) else 1
        c = bm.verts.new(cen + Vector((sgn * -.004, 0, 0)))
        for i in range(np_):
            a, b = inner[i], inner[(i + 1) % np_]
            f = bm.faces.new((c, b, a) if rev else (c, a, b))
            f.material_index = 1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    cy = sum(p[0] for p in prof) / np_; cz = sum(p[1] for p in prof) / np_
    return bm, (cy, cz)


def _billet(name, centre, rot, L, R, kind, seed, bark, wood, ang=1.8, tilt=None):
    """Place a billet so its cross-section centroid sits at centre; rot = Euler XYZ (roll about the grain first)."""
    from mathutils import Euler
    rr = random.Random(seed + 7)
    tilt = tilt if tilt is not None else (rr.uniform(-.25, .25), rr.uniform(-.25, .25))
    bm, (cy, cz) = _billet_mesh(L, R, kind, ang, seed, tilt)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); C._uv_box(me)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    Rm = Euler(rot).to_matrix()
    o.location = Vector(centre) - Rm @ Vector((0, cy, cz)); o.rotation_euler = rot
    o = _keep_slots(o, name, bark, grain='x')
    o.data.materials.append(wood)
    for f in o.data.polygons: f.use_smooth = True
    o.data.set_sharp_from_angle(angle=math.radians(40))
    o['rand_seed'] = seed
    return o


def _section_extent(R, kind, ang):
    """Half height of a billet's cross-section, used for stacking (sector pieces sit lower than round ones)."""
    return R if kind == 'round' else R * (.5 if kind == 'half' else .45 + .1 * min(1, ang / 2))


def _firewood_mats(tag):
    bark = WM.plate_bark(f'M_{tag}_Bark')
    wood = WM.split_wood(f'M_{tag}_SplitWood', dark='#6E5238', light='#B0946C', grey=.55)      # seasoned, greyed ends
    return bark, wood


def r03_firewood_neat():
    """Neat woodpile: split billets laid front to back in rows on two timber sleepers, small round billets
    cribbed at both ends behind stakes, a few long logs on top tied with hemp. 1.7 x 0.72 x 0.9 m."""
    bark, wood = _firewood_mats('R03N')
    sleeper = WM.aged_wood('M_R03N_Sleeper', grey=.45, rough=.86)
    rope = WM.rope('M_R03N_Rope')
    rr = random.Random(3101)
    for k, x in enumerate((-.7, .7)):
        C.box(f'Sleeper_{k}', (x, 0, .045), (.15, .74, .1), sleeper, bevel=.012, grain='y')
    seed = 3200; n = 0
    # main stack: billets laid along Y; each is tried at many positions and rolls on the stack's top
    # profile and goes where its centre ends lowest, so the wedges nest into one another without overlap
    cell = .01; X0 = -.645; NB = 129
    top = [.095] * NB
    pool = []
    for k in range(160):
        kind = rr.choices(('split', 'half', 'round'), (.6, .24, .16))[0]
        R = rr.uniform(.052, .062) if kind == 'round' else rr.uniform(.085, .125)
        pool.append((kind, rr.uniform(1.35, 2.0), R))
    zcap = .66
    for kind, ang, R in pool:
        prof = _section(R, kind, ang)
        best = None
        for roll in [rr.uniform(0, math.tau) for _ in range(8)]:
            pts = _section_world(prof, roll)
            lo_, hi_ = {}, {}
            for X, Z in pts:
                b = int(round(X / cell))
                lo_[b] = min(lo_.get(b, 9), Z); hi_[b] = max(hi_.get(b, -9), Z)
            bmin, bmax = min(lo_), max(lo_)
            for xb in range(-bmin, NB - bmax, 2):
                zc = max(top[xb + b] - lo_[b] for b in lo_) + .004
                if best is None or zc < best[0]: best = (zc, xb, roll, lo_, hi_)
        zc, xb, roll, lo_, hi_ = best
        if zc + max(hi_.values()) > zcap + .06 or zc > zcap: continue
        for b in hi_: top[xb + b] = max(top[xb + b], zc + hi_[b])
        _billet(f'Billet_{n:02d}', (X0 + xb * cell, rr.uniform(-.025, .025), zc), (roll, 0, math.pi / 2), rr.uniform(.6, .7), R, kind,
                seed + n, bark, wood, ang=ang)
        n += 1
    z = sum(top) / NB
    ztop = z
    # end cribs: small whole billets stacked at both ends, held by two stakes each
    for side, xc in ((-1, -.725), (1, .725)):
        zc = .095
        k = 0
        while zc < ztop + .02:
            r = rr.uniform(.036, .046)
            _billet(f'Crib_{side + 1}_{k}', (xc + rr.uniform(-.006, .006), 0, zc + r), (rr.uniform(0, 3), 0, math.pi / 2), rr.uniform(.64, .7), r,
                    'round', seed + 500 + k + (side + 1) * 40, bark, wood)
            zc += 2 * r * .97; k += 1
        for j, y in enumerate((-.31, .31)):
            C.cyl(f'Stake_{side + 1}_{j}', (xc + side * .055, y, .47), .024, .97, bark, verts=10, rot=(rr.uniform(-.03, .03), side * .04, 0),
                  grain='z')
    # on top: a long split log on the left, a tied bundle of three round logs on the right
    _billet('Top_Log_L', (-.34, -.04, ztop + .06), (1.2, 0, rr.uniform(-.05, .05)), .78, .1, 'half', seed + 900, bark, wood)
    bx = .3
    for j, (y, dz, r) in enumerate(((-.075, .062, .062), (.06, .058, .058), (-.01, .17, .056))):
        _billet(f'Bundle_{j}', (bx + rr.uniform(-.03, .03), y, ztop + dz), (rr.uniform(0, 3), 0, rr.uniform(-.03, .03)), rr.uniform(.66, .74), r,
                'round', seed + 950 + j, bark, wood)
    for j, xr in enumerate((bx - .08, bx + .07)):
        pts = []
        for i in range(26):
            a = i / 24 * math.tau * 1.08
            pts.append((xr + .006 * i / 24, .002 + .14 * math.cos(a), ztop + .105 + .125 * math.sin(a)))
        C.tube(f'Rope_{j}', pts, .0075, rope, res=6, grain='x')
    C.hull_box('Collision_Stack', (0, 0, (ztop + .25) / 2), (1.66, .74, ztop + .25))


def _rigid_settle(objs, frames=240, friction=.85, passive=()):
    """Drop objects onto the ground plane with Blender's rigid body solver (convex hulls, no bounce) and
    keep where they come to rest, so every piece is physically supported. The solver state is removed."""
    scene = bpy.context.scene
    me = bpy.data.meshes.new('Settle_Ground')
    # a thick slab rather than a plane, so a fast-falling piece cannot tunnel through it
    me.from_pydata([(x, y, z) for z in (-1, 0) for x, y in ((-20, -20), (20, -20), (20, 20), (-20, 20))], [],
                   [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
    ground = bpy.data.objects.new('Settle_Ground', me); scene.collection.objects.link(ground)
    if scene.rigidbody_world is None: bpy.ops.rigidbody.world_add()
    rw = scene.rigidbody_world
    rw.substeps_per_frame = 20; rw.solver_iterations = 30
    rw.point_cache.frame_start = 1; rw.point_cache.frame_end = frames
    scene.frame_start, scene.frame_end = 1, frames
    def add(o, kind):
        bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = o; o.select_set(True)
        bpy.ops.rigidbody.object_add(type=kind)
        rb = o.rigid_body; rb.collision_shape = 'CONVEX_HULL'
        rb.friction = friction; rb.restitution = 0.0; rb.use_margin = True; rb.collision_margin = .001
        if kind == 'ACTIVE':
            rb.linear_damping = .6; rb.angular_damping = .95
            rb.mass = max(.2, o.dimensions.x * o.dimensions.y * o.dimensions.z * 500)
    add(ground, 'PASSIVE')
    for o in passive: add(o, 'PASSIVE')
    for o in objs: add(o, 'ACTIVE')
    for f in range(1, frames + 1): scene.frame_set(f)
    rest = {o.name: o.matrix_world.copy() for o in objs}
    for o in list(objs) + list(passive) + [ground]:
        bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = o; o.select_set(True)
        bpy.ops.rigidbody.object_remove()
    bpy.ops.rigidbody.world_remove()
    scene.frame_set(1)
    for o in objs: o.matrix_world = rest[o.name]
    bpy.data.objects.remove(ground, do_unlink=True)


def r03_firewood_scattered():
    """Loose heap of split firewood, built the way a real one is: billets are tossed onto the heap a few at a
    time and the rigid body solver lets each batch slide, roll and lock against what is already there, so the
    mound takes its own angle of repose and every piece is supported. Three pieces have rolled away from the
    foot. The heap itself is about 1.9 x 1.3 m and 0.7 m high; the rolled pieces widen the footprint to about 2.8 x 2.1 m."""
    bark, wood = _firewood_mats('R03S')
    rr = random.Random(3301)
    pieces = []
    for k in range(48):
        kind = rr.choices(('split', 'half', 'round'), (.55, .25, .2))[0]
        ang = rr.uniform(1.3, 2.2)
        R = rr.uniform(.07, .115) if kind != 'round' else rr.uniform(.05, .075)
        L = rr.uniform(.34, .64)
        pieces.append((R * R * L, kind, ang, R, L))
    rr.shuffle(pieces)
    loose = pieces[-3:]; pieces = pieces[:-3]
    objs = []; settled = []
    def top_at(x, y):
        h = 0.0
        for o in settled:
            ws = [o.matrix_world @ Vector(c) for c in o.bound_box]
            if min(w.x for w in ws) - .15 <= x <= max(w.x for w in ws) + .15 and min(w.y for w in ws) - .15 <= y <= max(w.y for w in ws) + .15:
                h = max(h, max(w.z for w in ws))
        return h
    for bi in range(0, len(pieces), 5):
        batch = []
        z0 = 0.0
        for j, (_, kind, ang, R, L) in enumerate(pieces[bi:bi + 5]):
            n = bi + j
            cx, cy = rr.gauss(0, .28), rr.gauss(0, .12)
            yaw = rr.gauss(0, .35) + (math.pi / 2 if rr.random() < .1 else 0) + rr.choice((0, math.pi))
            dx, dy = math.cos(yaw) * L / 2, math.sin(yaw) * L / 2
            z0 = max([z0] + [top_at(cx + dx * u, cy + dy * u) for u in (-1, -.5, 0, .5, 1)]) + R + .05
            o = _billet(f'Billet_{n:02d}', (cx, cy, z0), (rr.uniform(0, math.tau), rr.uniform(-.15, .15), yaw), L, R, kind, 3400 + n, bark, wood, ang=ang)
            z0 += R
            batch.append(o)
        bpy.context.view_layer.update()
        _rigid_settle(batch, frames=70, friction=.9, passive=settled)
        settled += batch; objs += batch
    for k, (_, kind, ang, R, L) in enumerate(loose):
        cx, cy, yaw = ((-.62, .26, .3), (.64, -.2, 2.9), (.1, -.4, 1.62))[k]
        while top_at(cx, cy) > 0: cx, cy = cx * 1.08, cy * 1.08     # clear of the heap foot
        objs.append(_billet(f'Loose_{k}', (cx, cy, R + .02), (rr.uniform(0, math.tau), 0, yaw), L, R, kind, 3480 + k, bark, wood, ang=ang))
    bpy.context.view_layer.update()
    _rigid_settle(objs[-3:], frames=40, friction=1.0, passive=settled)
    bpy.context.view_layer.update()
    parts = [o for o in S['parts'] if o.name.startswith(('Billet', 'Loose'))]
    for name, lo, hi in (('Collision_W', -2, -.3), ('Collision_M', -.3, .3), ('Collision_E', .3, 2)):
        pts = [p for o in parts for p in C.world_points(o) if lo <= p.x <= hi]
        if len(pts) > 8: C.hull(name, pts)
