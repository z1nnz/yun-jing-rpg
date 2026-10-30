"""Shared geometry helpers for qingxi-world-ruins-b (forked from territory-interior-b ti_core.py).

Blender Z-up, 1 unit = 1 m, model front faces -Y, origin at the footprint centre, bottom at z = 0.
Every visible part carries world-space grain axes (gA/gB/gC) and a random value (part_rand) as point
attributes, so the procedural shaders still read correctly after all parts are joined into one export
mesh and baked into an atlas. Collision hulls are kept apart in S["coll"] and never baked.
"""
import bpy, bmesh, math, random
from contextlib import contextmanager
from mathutils import Vector, Matrix

# ---------------------------------------------------------------- state
S = {}   # per-asset state: parts, cutters, collections, sockets, transform stack

def reset_state(asset_id):
    S.clear()
    S.update(asset=asset_id, parts=[], sockets={}, coll=[], M=[Matrix.Identity(4)], rng=random.Random(asset_id))
    scene = bpy.context.scene
    S['col'] = bpy.data.collections.new('01_Editable_Parts'); scene.collection.children.link(S['col'])
    S['cut'] = bpy.data.collections.new('80_Boolean_Cutters'); scene.collection.children.link(S['cut'])
    S['cut'].hide_render = True; S['cut'].hide_viewport = True

def rng():
    return S['rng']

@contextmanager
def xf(M):
    S['M'].append(S['M'][-1] @ M)
    try: yield
    finally: S['M'].pop()

def T(x=0, y=0, z=0): return Matrix.Translation(Vector((x, y, z)))
def RZ(a): return Matrix.Rotation(a, 4, 'Z')
def RX(a): return Matrix.Rotation(a, 4, 'X')
def RY(a): return Matrix.Rotation(a, 4, 'Y')

AXES = {'x': Vector((1, 0, 0)), 'y': Vector((0, 1, 0)), 'z': Vector((0, 0, 1))}

def finish(o, name, mat, grain='x', detail=0, group='Main', bevel=0.0, seg=3, smooth=False):
    """detail 0 = always kept, 1 = dropped at LOD2, 2 = dropped at LOD1 and LOD2."""
    o.name = name
    for c in list(o.users_collection): c.objects.unlink(o)
    S['col'].objects.link(o)
    o.matrix_world = S['M'][-1] @ o.matrix_basis      # matrix_world is stale until a depsgraph update
    if mat is not None:
        o.data.materials.clear(); o.data.materials.append(mat)
    if smooth:
        for f in o.data.polygons: f.use_smooth = True
    if bevel:
        m = o.modifiers.new('Soft_edges', 'BEVEL'); m.width = bevel; m.segments = seg
        m.limit_method = 'ANGLE'; m.angle_limit = math.radians(35)
        o.modifiers.new('Weighted_normals', 'WEIGHTED_NORMAL').keep_sharp = True
        for f in o.data.polygons: f.use_smooth = True
    o['grain'] = grain if isinstance(grain, str) else 'v'
    if not isinstance(grain, str): o['grain_vec'] = list(grain)
    o['detail'] = detail; o['group'] = group
    S['parts'].append(o)
    return o

def _active(o):
    bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = o; o.select_set(True)

def box(name, p, s, mat, bevel=.004, rot=(0, 0, 0), **kw):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * s[0], v.co.y * s[1], v.co.z * s[2]))
    bm.to_mesh(me); bm.free(); _uv_box(me)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    o.location = p; o.rotation_euler = rot
    return finish(o, name, mat, bevel=bevel, **kw)

def _uv_box(me):
    if not me.uv_layers: me.uv_layers.new(name='UVMap')

def cyl(name, p, r, d, mat, axis='z', verts=32, bevel=None, rot=None, r2=None, **kw):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=verts, radius1=r, radius2=r if r2 is None else r2, depth=d)
    bm.to_mesh(me); bm.free(); _uv_box(me)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    o.location = p
    if rot is not None: o.rotation_euler = rot
    elif axis == 'x': o.rotation_euler = (0, math.pi / 2, 0)
    elif axis == 'y': o.rotation_euler = (math.pi / 2, 0, 0)
    for f in me.polygons: f.use_smooth = True
    kw.setdefault('grain', axis if axis in 'xyz' else 'z')
    b = min(r * .12, .004) if bevel is None else bevel
    o = finish(o, name, mat, bevel=b, seg=2, **kw)
    return o

def sphere(name, p, r, mat, scale=(1, 1, 1), seg=24, ring=12, **kw):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=ring, radius=r)
    for v in bm.verts: v.co = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2]))
    bm.to_mesh(me); bm.free(); _uv_box(me)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); o.location = p
    kw.setdefault('grain', 'z')
    return finish(o, name, mat, smooth=True, **kw)

def torus(name, p, R, r, mat, rot=(0, 0, 0), major=48, minor=10, **kw):
    me = bpy.data.meshes.new(name)
    verts, faces = [], []
    for i in range(major):
        a = i * math.tau / major
        for j in range(minor):
            b = j * math.tau / minor
            verts.append(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b)))
    for i in range(major):
        for j in range(minor):
            faces.append((i * minor + j, ((i + 1) % major) * minor + j, ((i + 1) % major) * minor + (j + 1) % minor, i * minor + (j + 1) % minor))
    me.from_pydata(verts, [], faces); me.update(); _uv_box(me)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    o.location = p; o.rotation_euler = rot
    kw.setdefault('grain', 'z')
    return finish(o, name, mat, smooth=True, **kw)

def lathe(name, profile, p, mat, seg=48, scale=(1, 1, 1), **kw):
    """profile: (radius, z) bottom to top. Radius 0 at an end closes the shape with a pole."""
    verts, faces, rings = [], [], []
    for r, z in profile:
        if r < 1e-6:
            rings.append([len(verts)]); verts.append((0, 0, z))
        else:
            ring = []
            for i in range(seg):
                a = i * math.tau / seg
                ring.append(len(verts)); verts.append((r * math.cos(a) * scale[0], r * math.sin(a) * scale[1], z * scale[2]))
            rings.append(ring)
    for A, B in zip(rings, rings[1:]):
        if len(A) == 1 and len(B) > 1:
            faces += [(A[0], B[(i + 1) % seg], B[i]) for i in range(seg)]
        elif len(B) == 1 and len(A) > 1:
            faces += [(A[i], A[(i + 1) % seg], B[0]) for i in range(seg)]
        elif len(A) > 1:
            faces += [(A[i], A[(i + 1) % seg], B[(i + 1) % seg], B[i]) for i in range(seg)]
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update(); _uv_box(me)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); o.location = p
    kw.setdefault('grain', 'z')
    return finish(o, name, mat, smooth=True, **kw)

def mesh(name, verts, faces, mat, uvs=None, smooth=False, solid=None, **kw):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    uv = me.uv_layers.new(name='UVMap')
    if uvs is not None:
        for poly in me.polygons:
            for li in poly.loop_indices:
                uv.data[li].uv = uvs[me.loops[li].vertex_index]
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    o = finish(o, name, mat, smooth=smooth, **kw)
    if solid:
        m = o.modifiers.new('Thickness', 'SOLIDIFY'); m.thickness = solid; m.offset = 0
    return o

def surface(name, nu, nv, fn, mat, uvfn=None, solid=None, closed_u=False, **kw):
    """Grid surface fn(u,v)->xyz with u,v in [0,1]."""
    cu = nu if closed_u else nu + 1
    verts = [fn(i / nu, j / nv) for j in range(nv + 1) for i in range(cu)]
    faces = []
    for j in range(nv):
        for i in range(nu):
            a = j * cu + i; b = j * cu + (i + 1) % cu
            faces.append((a, b, b + cu, a + cu))
    uvs = None
    if uvfn: uvs = [uvfn(i / nu, j / nv) for j in range(nv + 1) for i in range(cu)]
    return mesh(name, verts, faces, mat, uvs=uvs, smooth=True, solid=solid, **kw)

def extrude_profile(name, pts2d, thickness, mat, plane='xz', p=(0, 0, 0), rot=(0, 0, 0), bevel=.002, **kw):
    """Closed 2D outline (counter-clockwise) extruded along the plane normal; centred on thickness."""
    n = len(pts2d); verts = []
    for side in (-.5, .5):
        for a, b in pts2d:
            if plane == 'xz': verts.append((a, side * thickness, b))
            elif plane == 'yz': verts.append((side * thickness, a, b))
            else: verts.append((a, b, side * thickness))
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    vs = [bm.verts.new(v) for v in verts]
    bm.faces.new(vs[:n][::-1]); bm.faces.new(vs[n:])
    for i in range(n):
        j = (i + 1) % n; bm.faces.new((vs[i], vs[j], vs[n + j], vs[n + i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free(); _uv_box(me)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    o.location = p; o.rotation_euler = rot
    return finish(o, name, mat, bevel=bevel, seg=2, **kw)

def tube(name, pts, r, mat, radii=None, caps=True, res=6, **kw):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.resolution_u = 2
    cu.bevel_depth = r; cu.bevel_resolution = res // 2; cu.use_fill_caps = caps
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for i, (pt, q) in enumerate(zip(sp.points, pts)):
        pt.co = (*q, 1); pt.radius = radii[i] if radii else 1.0
    o = bpy.data.objects.new(name, cu); bpy.context.scene.collection.objects.link(o)
    _active(o); bpy.ops.object.convert(target='MESH')
    o = bpy.context.view_layer.objects.active
    _uv_box(o.data)
    kw.setdefault('grain', 'z')
    return finish(o, name, mat, smooth=True, **kw)

def _catmull(pts, n):
    P = [Vector(p) for p in pts]; P = [P[0]] + P + [P[-1]]; out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            out.append(.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2]); return out

def ribbon(name, pts, half_width, mat, thickness=.003, **kw):
    """Flat band whose width runs along X, following a smoothed path (tabs, bookmark)."""
    path = _catmull(pts, 6); nv = len(path) - 1
    def fn(u, v):
        p = path[min(int(round(v * nv)), nv)]
        return (p.x + (u - .5) * 2 * half_width, p.y, p.z)
    o = surface(name, 1, nv, fn, mat, solid=thickness, **kw)
    return o

def leaf_petal(name, base, tip, width, mat, lift=.2, **kw):
    a, b = Vector(base), Vector(tip); d = b - a
    side = d.cross(Vector((0, -1, 0)))
    if side.length < 1e-4: side = Vector((1, 0, 0))
    side.normalize(); out = side.cross(d).normalized()
    pts = []
    for t in (0, .35, .7, 1):
        w = width * math.sin(math.pi * min(t, .97)) ** .7
        c = a + d * t + out * (lift * width * math.sin(math.pi * t))
        pts.append((c - side * w, c, c + side * w))
    verts = [tuple(v) for row in pts for v in row]
    faces = [(i * 3 + k, i * 3 + k + 1, (i + 1) * 3 + k + 1, (i + 1) * 3 + k) for i in range(3) for k in range(2)]
    o = mesh(name, verts, faces, mat, smooth=True, solid=.004, **kw)
    return o

def boolean(target, cutter, mode='DIFFERENCE'):
    for c in list(cutter.users_collection): c.objects.unlink(cutter)
    S['cut'].objects.link(cutter)
    if cutter in S['parts']: S['parts'].remove(cutter)
    cutter.matrix_world = cutter.matrix_world  # already transformed by finish
    m = target.modifiers.new('Cut_' + cutter.name, 'BOOLEAN'); m.object = cutter; m.operation = mode
    m.solver = 'EXACT'; m.material_mode = 'TRANSFER'
    # keep the boolean before the normal-weighting step
    if 'Weighted_normals' in target.modifiers:
        idx = list(target.modifiers).index(target.modifiers['Weighted_normals'])
        bpy.context.view_layer.objects.active = target
        with bpy.context.temp_override(object=target):
            bpy.ops.object.modifier_move_to_index(modifier=m.name, index=idx)
    return m

def socket(name, p, rot=(0, 0, 0)):
    e = bpy.data.objects.new(name, None); e.empty_display_type = 'ARROWS'; e.empty_display_size = .08
    S['col'].objects.link(e)
    e.matrix_world = S["M"][-1] @ (Matrix.Translation(Vector(p)) @ Matrix(Euler_from(rot)).to_4x4())
    S['sockets'][name] = e
    return e

def Euler_from(rot):
    from mathutils import Euler
    return Euler(rot).to_matrix()

# ---------------------------------------------------------------- attributes
def write_grain_attributes():
    for o in S['parts']:
        if o.type != 'MESH': continue
        R = o.matrix_world.to_3x3().normalized()
        if o['grain'] == 'v': a = R @ Vector(o['grain_vec'])
        else: a = R @ AXES[o['grain']]
        a.normalize()
        helper = Vector((0, 0, 1)) if abs(a.z) < .9 else Vector((1, 0, 0))
        b = a.cross(helper).normalized(); c = a.cross(b).normalized()
        me = o.data; n = len(me.vertices)
        for nm, vec in (('gA', a), ('gB', b), ('gC', c)):
            at = me.attributes.get(nm) or me.attributes.new(nm, 'FLOAT_VECTOR', 'POINT')
            at.data.foreach_set('vector', list(vec) * n)
        if not o.get('own_rand'):       # merged multi-piece meshes (roof tiles) carry their own per-piece values
            at = me.attributes.get('part_rand') or me.attributes.new('part_rand', 'FLOAT', 'POINT')
            pr = random.Random(o['rand_seed']).random() if 'rand_seed' in o else rng().random()
            at.data.foreach_set('value', [pr] * n)
        # lp: part-local position (rotation and scale applied, translation removed). Periodic copies of one stone
        # get identical lp, so their two halves texture as one stone across a chain joint.
        M3 = o.matrix_world.to_3x3()
        lp = [M3 @ v.co for v in me.vertices]
        at = me.attributes.get('lp') or me.attributes.new('lp', 'FLOAT_VECTOR', 'POINT')
        at.data.foreach_set('vector', [c for q in lp for c in q])
        # iface: 0 on a chain interface plane, 1 from 5 cm away (fades edge wear on cut faces)
        planes = S.get('iface_planes', [])
        vals = []
        for q in lp:
            w = o.matrix_world.translation + q
            d = min([abs((w - Vector(pc)).dot(Vector(pn))) for pc, pn in planes] or [1.0])
            vals.append(min(1.0, d / .05))
        at = me.attributes.get('iface') or me.attributes.new('iface', 'FLOAT', 'POINT')
        at.data.foreach_set('value', vals)

# ---------------------------------------------------------------- stones
def rock_mesh(size, seed, sub=3, round_=.42, chips=7, chip_depth=(.06, .2), wobble=.05, flat_bottom=None, face=None, taper=0.0, skew=0.0, bulge=0.0):
    """Field stone: a subdivided cube pushed towards a rounded box (round_ = superellipsoid exponent, small = boxy),
    with corners and edges knocked off by flat facets cut in metric space (so long stones keep blunt ends),
    then a gentle lumpiness. size = full extents (x, y, z) in m.
    chip_depth is a fraction of the stone's smallest extent. flat_bottom / face flatten the bed (-z) and the
    outward face (face = -1 for -y, +1 for +y), as a waller lays a stone with its flattest sides out and down."""
    from mathutils import noise
    r = random.Random(seed)
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=max(1, sub + 1), use_grid_fill=True)
    e = max(.08, round_)
    h = Vector(size) / 2; mn = min(size)
    off = Vector((r.random() * 50, r.random() * 50, r.random() * 50))
    pts = []
    for v in bm.verts:
        d = v.co.normalized()
        p = Vector([math.copysign(abs(c) ** e, c) for c in d])
        q = Vector((p.x * h.x, p.y * h.y, p.z * h.z))
        zr = q.z / h.z
        q.x = q.x * (1 + taper * zr) + skew * q.z          # trapezoid / leaning outline seen from the face
        if bulge: q.y += math.copysign(bulge * mn * (1 - min(1, abs(p.x)) ** 2) * (1 - min(1, abs(p.z)) ** 2), q.y)
        pts.append(q)
    for _ in range(chips):
        # knock a corner or an edge: direction towards a box corner, with one axis sometimes dropped (edge chip)
        sgn = [r.choice((-1, 1)) for _ in range(3)]
        w = [r.uniform(.35, 1.0) for _ in range(3)]
        if r.random() < .45: w[r.randrange(3)] = r.uniform(0, .15)
        n = Vector((sgn[0] * w[0] / h.x, sgn[1] * w[1] / h.y, sgn[2] * w[2] / h.z)).normalized()
        top = max(q.dot(n) for q in pts)
        cut = top - r.uniform(*chip_depth) * mn
        for q in pts:
            k = q.dot(n)
            if k > cut: q -= n * (k - cut)
    for q in pts:
        q += Vector(noise.noise_vector(Vector((q.x / mn, q.y / mn, q.z / mn)) * .9 + off)) * wobble * mn
    if flat_bottom is not None:
        lim = -h.z * flat_bottom
        for q in pts:
            if q.z < lim: q.z = lim + (q.z - lim) * .12
    if face is not None:
        lim = h.y * .85
        for q in pts:
            if q.y * face > lim: q.y = face * (lim + (q.y * face - lim) * .45)
    for v, q in zip(bm.verts, pts): v.co = q
    return bm

def rock(name, p, size, mat, seed, rot=(0, 0, 0), sub=3, **kw):
    geo = {k: kw.pop(k) for k in ('round_', 'chips', 'chip_depth', 'wobble', 'flat_bottom', 'face', 'taper', 'skew', 'bulge') if k in kw}
    bm = rock_mesh(size, seed, sub=sub, **geo)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); _uv_box(me)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    o.location = p; o.rotation_euler = rot
    kw.setdefault('grain', 'x')
    o = finish(o, name, mat, **kw)
    for f in o.data.polygons: f.use_smooth = True
    o.data.set_sharp_from_angle(angle=math.radians(34))
    m = o.modifiers.new('Facet_normals', 'WEIGHTED_NORMAL'); m.keep_sharp = True; m.weight = 50
    return o

# ---------------------------------------------------------------- bamboo
def culm_profile(length, r, seed, node_gap=(.24, .34), open_top=True, taper=.9, wall=.18):
    """(radius, z) lathe profile for a bamboo culm: slight taper, a raised ring and pinch at every node,
    cut open at the top (wall thickness = wall * r) so the hollow shows."""
    rr = random.Random(seed)
    nodes = []; z = rr.uniform(.06, .16)
    while z < length - .05:
        nodes.append(z); z += rr.uniform(*node_gap)
    prof = [(0.0, 0.0), (r, 0.0)]
    rad = lambda z: r * (1 - (1 - taper) * z / length)
    for zn in nodes:
        R = rad(zn)
        prof += [(R, zn - .028), (R * .97, zn - .008), (R * 1.055, zn - .002), (R * 1.055, zn + .004), (R * .985, zn + .012), (R, zn + .03)]
    top = rad(length)
    prof.append((top, length))
    if open_top:
        prof += [(top * (1 - wall), length), (top * (1 - wall), length - .015), (0.0, length - .02)]
    else:
        prof.append((0.0, length))
    prof = [prof[0]] + sorted(prof[1:-3 if open_top else -1], key=lambda q: q[1]) + prof[(-3 if open_top else -1):]
    return prof, nodes

def culm(name, base, direction, length, r, mat, seed, seg=14, **kw):
    """Bamboo culm from base point along direction."""
    prof, nodes = culm_profile(length, r, seed, **{k: kw.pop(k) for k in ('node_gap', 'open_top', 'taper') if k in kw})
    d = Vector(direction).normalized()
    q = Vector((0, 0, 1)).rotation_difference(d)
    roll = random.Random(seed).uniform(0, math.tau)
    with xf(Matrix.Translation(Vector(base)) @ q.to_matrix().to_4x4() @ RZ(roll)):
        o = lathe(name, prof, (0, 0, 0), mat, seg=seg, grain='z', **kw)
    return o

# ---------------------------------------------------------------- clipping and collision
def clip_axis(o, axis, lo=None, hi=None):
    """Cut a part flat at axis = lo and/or axis = hi (object space == world space for parts built at identity)
    and fill the cut so the end face is closed. Used to make wall and fence ends periodic."""
    bpy.context.view_layer.update()
    me = o.data; bm = bmesh.new(); bm.from_mesh(me)
    mw = o.matrix_world; inv = mw.inverted()
    ax = AXES[axis]
    for val, keep_pos in ((lo, True), (hi, False)):
        if val is None: continue
        co = inv @ (ax * val)
        no = (inv.to_3x3() @ ax).normalized()
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_inner=keep_pos, clear_outer=not keep_pos)
        edges = [e for e in res['geom_cut'] if isinstance(e, bmesh.types.BMEdge)]
        if edges:
            bmesh.ops.remove_doubles(bm, verts=list({v for e in edges if e.is_valid for v in e.verts}), dist=1e-5)
            edges = [e for e in bm.edges if e.is_boundary]
            if edges:
                new = bmesh.ops.holes_fill(bm, edges=edges, sides=0)['faces']
                if new: bmesh.ops.triangulate(bm, faces=new)
    bm.to_mesh(me); bm.free()
    return len(me.polygons)

def world_points(o):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get(); e = o.evaluated_get(dg); me = e.to_mesh()
    pts = [o.matrix_world @ v.co for v in me.vertices]; e.to_mesh_clear(); return pts

def hull(name, pts):
    """Convex hull collision mesh from world-space points. Kept apart from render parts."""
    bm = bmesh.new()
    for p in pts: bm.verts.new(S['M'][-1] @ Vector(p))
    res = bmesh.ops.convex_hull(bm, input=bm.verts[:])
    for g in res.get('geom_interior', []) + res.get('geom_unused', []):
        if isinstance(g, bmesh.types.BMVert) and g.is_valid: bm.verts.remove(g)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    S.setdefault('collcol', None)
    if S['collcol'] is None:
        S['collcol'] = bpy.data.collections.new('03_Collision'); bpy.context.scene.collection.children.link(S['collcol'])
    S['collcol'].objects.link(o); o.display_type = 'WIRE'; o.hide_render = True
    S['coll'].append(o)
    return o

def hull_box(name, centre, size, rot_z=0.0):
    c = Vector(centre); h = Vector(size) / 2; R = Matrix.Rotation(rot_z, 3, 'Z')
    pts = [c + R @ Vector((x * h.x, y * h.y, z * h.z)) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    return hull(name, pts)

def drop_part(o):
    if o in S['parts']: S['parts'].remove(o)
    bpy.data.objects.remove(o, do_unlink=True)
