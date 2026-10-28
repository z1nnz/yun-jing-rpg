"""Build, bake, export, render and validate the Qingxi waterworks B kit.

  blender -b --python-exit-code 1 --python art/source/qingxi-waterworks-b/build.py -- B01 B02     (listed assets)
  blender -b --python-exit-code 1 --python art/source/qingxi-waterworks-b/build.py -- --no-render (all, no previews)

Per asset <key> = <ID>_<Name>:
  art/source/qingxi-waterworks-b/blend/<key>_v001.blend   10_Procedural_Source (hidden, editable parts) + 00_Game_Export
  art/exports/qingxi-waterworks-b/<key>/<key>.glb           LOD0 nodes, water, sockets, baked animation, embedded textures
  .../<key>.fbx + textures/ (LOD0-2 for a Unity LOD Group), <key>_model_info.json
  art/previews/qingxi-waterworks-b/<ID>/                    ortho front/side/back, 3/4 neutral + stylized, close-up,
                                                            wireframe, 1.75 m scale/eye height, GLB re-import render
"""
import bpy, bmesh, sys, json, math, time, struct
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_lib as Q
import ww_lib as W
import ww_assets as A
import ww_variants  # noqa: F401,E402  (batch-1 B02 / B03 variants register themselves into A.ASSETS)
try:
    import ww_assets2   # noqa: F401  (B07-B12 register themselves into A.ASSETS)
except ImportError as e:
    print('B07-B12 builders not loaded:', e)

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
RENDER = '--no-render' not in argv
ids = [a for a in argv if not a.startswith('--')] or sorted(A.ASSETS)
REF = Q.REPO / 'art/references' / Q.KIT
AUTHOR = 'Claude Code (Claude Opus 5.5) for joshsu54'

# designed joints: part-name fragments whose interpenetration is intended (tenon in mortise, inlay, gear mesh ...)
JOINT_WHITELIST = [('Tenon', 'Post', 'through tenon in mortise'), ('TopTenon', 'TopBeam', 'rack-guide tenon through the top beam'),
                   ('BrgRv', 'Bearing', 'rivet through bearing plate'), ('GripStub', 'Spoke', 'grip stub tenoned into the spoke'), ('Tooth', 'ToothStrip', 'teeth brazed to strip'),
                   ('Tooth', 'Rack', 'teeth seated on rack'), ('Spoke', 'Felloe', 'spoke tenon in felloe'), ('Spoke', 'Hub', 'spoke socket'),
                   ('Spoke', 'Rim', 'spoke end under tyre'), ('Grip', 'GripStub', 'grip on stub'), ('Pinion', 'Shaft', 'keyed hub'),
                   ('PinionBoss', 'Shaft', 'boss on shaft'), ('Coupling', 'Shaft', 'shaft end in coupling sleeve'), ('Pinion', 'Tooth', 'gear mesh at rest'), ('Collar', 'Shaft', 'collar on shaft'), ('Hub', 'Shaft', 'shaft through hub'),
                   ('SquareTip', 'Shaft', 'coupling'), ('_rv', '', 'rivet head seated in plate'), ('Peg', '', 'peg in bore'),
                   ('Wedge', '', 'wedge in tenon'), ('Lug', '', 'lug fixed to face'), ('Strap', '', 'strap bedded on face'),
                   ('Band', '', 'band bedded on face'), ('Cramp', '', 'cramp bedded on face'), ('Shoe', '', 'shoe on member'),
                   ('Wire', 'Wire', 'woven wire crossing'), ('Wire', 'Frame', 'wire ends in frame'), ('Brace', '', 'housed brace end'),
                   ('Hoop', '', 'hoop bedded on member'), ('Inlay', '', 'inlay set into board'), ('Rope', '', 'rope wraps member'),
                   ('Cord', '', 'cord wraps member'), ('Keel', 'Hull', 'keel fixed to hull'), ('Mast', '', 'mast stepped in hull'),
                   ('Ring', '', 'ring through eye'), ('Gasket', '', 'gasket seated in groove'), ('Load', '', 'load resting / lashed'),
                   ('Axle', '', 'axle through hub/hanger'), ('Felloe', 'Rim', 'tyre shrunk on felloe'), ('Ear', '', 'ring ear'),
                   ('Batten', '', 'batten fixed to face'), ('Key', '', 'timber key in clamp'), ('Pin', '', 'pin through member'),
                   ('Handle', '', 'handle socket'), ('Collar', '', 'collar on member'), ('Cap', '', 'cap on member'), ('Bar', '', 'bar on face'),
                   ('Frame', 'Frame', 'corner joint'), ('Tablet', '', 'tablet in frame rebate'), ('Plank', 'Plank', 'plank edge joint'),
                   ('Leg', '', 'leg mortised into frame'), ('Rail', '', 'rail mortised into member'), ('Slat', '', 'slat in rail'),
                   ('Stake', '', 'stake'), ('Pad', '', 'pad stone under post'), ('Spade', '', 'tool'), ('Mallet', '', 'tool')]


def whitelist(a, b):
    for x, y, why in JOINT_WHITELIST:
        if (x in a and y in b) or (x in b and y in a): return why
    return None


# ----------------------------------------------------------------------------- game mesh (qa_lib.game_mesh + depth allowance + kept nodes)
def game_mesh(name, objs, gcoll, below=-0.003):
    dg = bpy.context.evaluated_depsgraph_get(); bake = []; ids = {'Body': 0}
    for o in objs:
        if o.type != 'MESH' or o.get('qa_cutter') or o.hide_render or o.get('ww_keep') or o.get('qa_node') == 'Water': continue
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        me.transform(o.matrix_world)
        if not len(me.polygons): bpy.data.meshes.remove(me); continue
        nid = ids.setdefault(o.get('qa_node', 'Body'), len(ids))
        at = me.attributes.new('qa_node', 'INT', 'FACE'); at.data.foreach_set('value', [nid] * len(me.polygons))
        c = bpy.data.objects.new(o.name + '_G', me); gcoll.objects.link(c); bake.append(c)
    Q.select_only(bake, bake[0]); bpy.ops.object.join(); G = bpy.context.view_layer.objects.active
    G.name = name; G.data.name = name + '_Mesh'
    for uv in list(G.data.uv_layers): G.data.uv_layers.remove(uv)
    G.data.uv_layers.new(name='UVMap'); Q.dissolve_degenerate(G)
    bm = bmesh.new(); bm.from_mesh(G.data); bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4]); bm.to_mesh(G.data); bm.free()
    lo = min(v.co.z for v in G.data.vertices)
    assert lo > below - 0.004, f'{name}: lowest vertex z={lo:.4f} below allowed {below}'
    for v in G.data.vertices:
        if below >= -0.003 and -0.003 < v.co.z < 0: v.co.z = 0.0
    Q.select_only([G], G); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(62), island_margin=0.003, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(rotate=True, margin=0.003)
    bpy.ops.object.mode_set(mode='OBJECT')
    G['qa_nodes'] = json.dumps(sorted(ids, key=ids.get))
    return G


def fix_normals(parts):
    for o in parts:
        if o.type != 'MESH' or o.get('qa_cutter') or o.get('qa_node') == 'Water' or o.get('ww_open'): continue
        if o.data.shape_keys: continue
        bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()


# ----------------------------------------------------------------------------- QA helpers
def coplanar_report(o, tol=2.5e-4):
    """Faces that coincide with another face: same direction = z-fighting (error); opposite = hidden contact."""
    me = o.data; mw = o.matrix_world
    verts = [mw @ v.co for v in me.vertices]; polys = [tuple(p.vertices) for p in me.polygons]
    bvh = BVHTree.FromPolygons(verts, polys, all_triangles=False)
    nrm = [(mw.to_3x3() @ p.normal).normalized() for p in me.polygons]
    same, contact = set(), set()
    for p in me.polygons:
        c = mw @ p.center
        for loc, n, j, d in bvh.find_nearest_range(c, tol):
            if j == p.index or d > 2e-5: continue      # the face centre must lie ON face j, not just near its plane
            dt = nrm[p.index].dot(nrm[j])
            if dt > 0.999: same.add(p.index)
            elif dt < -0.999: contact.add(p.index)
    return {'sameDirectionCoplanarFaces': len(same), 'oppositeContactFaces': len(contact)}


def part_overlaps(parts):
    dg = bpy.context.evaluated_depsgraph_get(); trees = []
    for o in parts:
        if o.type != 'MESH' or o.get('qa_cutter') or o.get('qa_node') == 'Water' or o.hide_render: continue
        # shrink 0.6 mm along vertex normals: blocks that merely touch (bedding, butt joints) no longer count,
        # anything that really penetrates does
        e = o.evaluated_get(dg); me = e.to_mesh(); mw = o.matrix_world; nm = mw.to_3x3()
        vs = [mw @ v.co - (nm @ v.normal).normalized() * 0.0006 for v in me.vertices]; ps = [tuple(p.vertices) for p in me.polygons]
        # plane of each face (unshrunk) so face-to-face contact can be told from real penetration
        fp = [((nm @ p.normal).normalized(), mw @ p.center) for p in me.polygons]
        if ps:
            mn = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs))); mx = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
            trees.append((o.name, BVHTree.FromPolygons(vs, ps, all_triangles=False), mn, mx, fp))
        e.to_mesh_clear()
    def contact(fa, fb):     # opposite faces lying in one plane: a butt joint, not an interpenetration
        (na, ca), (nb, cb) = fa, fb
        return na.dot(nb) < -0.985 and abs((cb - ca).dot(na)) < 2e-4
    ok, bad = [], []
    for i in range(len(trees)):
        a, ta, amn, amx, fa = trees[i]
        for b, tb, bmn, bmx, fb in trees[i + 1:]:
            if any(amx[k] < bmn[k] - 1e-4 or bmx[k] < amn[k] - 1e-4 for k in range(3)): continue
            hits = ta.overlap(tb)
            if not hits or all(contact(fa[x], fb[y]) for x, y in hits): continue
            why = whitelist(a, b)
            (ok if why else bad).append([a, b] + ([why] if why else []))
    return ok, bad


def uv_report(o, res):
    me = o.data; uv = me.uv_layers.active
    import numpy as np
    a = np.zeros(len(uv.data) * 2, np.float32); uv.data.foreach_get('uv', a); a = a.reshape(-1, 2)
    nan = int(np.isnan(a).sum()); area3 = 0.0; area2 = 0.0; zero = 0
    for p in me.polygons:
        li = list(p.loop_indices); pts = a[li]
        s = 0.0
        for k in range(1, len(pts) - 1):
            u1 = pts[k] - pts[0]; u2 = pts[k + 1] - pts[0]; s += abs(u1[0] * u2[1] - u1[1] * u2[0]) / 2
        if s < 1e-10: zero += 1
        area2 += s; area3 += p.area
    texel = math.sqrt(area2 / max(area3, 1e-9)) * res
    return {'nanUV': nan, 'zeroAreaUVFaces': zero, 'texelDensityPxPerM': round(texel, 1), 'uvCoverage': round(area2, 3)}


# ----------------------------------------------------------------------------- export / roundtrip
def tree(o):
    out = [o]
    for c in o.children: out += tree(c)
    return out


def export_glb(root, path, anim):
    sel = [o for o in tree(root) if not o.name.endswith(('_LOD1', '_LOD2'))]
    Q.select_only(sel, root)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
                              export_image_format='AUTO', export_materials='EXPORT', export_extras=True,
                              export_animations=bool(anim), export_animation_mode='SCENE', export_force_sampling=True,
                              export_morph=True, export_morph_animation=True, export_def_bones=False)


def export_fbx(root, path):
    Q.select_only(tree(root), root)
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y',
                             bake_space_transform=False, mesh_smooth_type='FACE', use_tspace=True, path_mode='RELATIVE', embed_textures=False,
                             add_leaf_bones=False, object_types={'EMPTY', 'MESH'}, bake_anim=True, bake_anim_use_all_actions=False,
                             bake_anim_use_nla_strips=False, use_custom_props=True)


def glb_json(path):
    b = path.read_bytes(); n = struct.unpack_from('<I', b, 12)[0]; return json.loads(b[20:20 + n])


def roundtrip(path, kind):
    Q.reset()
    if kind == 'glb': bpy.ops.import_scene.gltf(filepath=str(path))
    else: bpy.ops.import_scene.fbx(filepath=str(path))
    ms = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.endswith(('_LOD1', '_LOD2'))]
    tris = sum(Q.tri_count(o) for o in ms)
    pts = [o.matrix_world @ Vector(c) for o in ms for c in o.bound_box]
    mn = [min(p[i] for p in pts) for i in range(3)]; mx = [max(p[i] for p in pts) for i in range(3)]
    imgs = [i for i in bpy.data.images if i.type == 'IMAGE']
    return dict(objects=sorted(o.name for o in bpy.data.objects), meshes=len(ms), triangles=tris, bbox_min=mn, bbox_max=mx,
                materials=sorted({m.name for o in ms for m in o.data.materials if m}),
                images=len(imgs), imagesLoaded=sum(1 for i in imgs if i.has_data or (i.size[0] > 0)),
                empties=sum(1 for o in bpy.data.objects if o.type == 'EMPTY'), actions=sorted(a.name for a in bpy.data.actions),
                shapeKeys=sorted({k.name for o in ms if o.data.shape_keys for k in o.data.shape_keys.key_blocks}),
                lods=sorted(o.name for o in bpy.data.objects if o.name.endswith(('_LOD1', '_LOD2'))))


# ----------------------------------------------------------------------------- previews
def ortho_cam(objs, yaw, name):
    s = bpy.context.scene; mn, mx = Q.bbox(objs)
    c = Vector(((mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, (mn[2] + mx[2]) / 2)); size = max(mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2]) * 1.18
    cam = s.camera; cam.data.type = 'ORTHO'; cam.data.ortho_scale = max(size, 0.2)
    y = math.radians(yaw); d = Vector((math.sin(y), -math.cos(y), 0.0)); cam.location = c + d * 20; cam.data.clip_end = 60
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()


def previews(a, key, nodes, info, root):
    out = Q.PREVIEWS / a['id']; s = bpy.context.scene
    Q.gpu(s, 48); Q.studio('neutral')
    vis = [o for o in nodes if o.type == 'MESH']
    Q.camera_fit(vis, 35, 18)
    for nm, yaw in (('ortho_front', 0), ('ortho_right', 90), ('ortho_back', 180)):
        ortho_cam(vis, yaw, nm); Q.render(out / f'{nm}.png', 1024, 40)
    s.camera.data.type = 'PERSP'
    for nm, yaw, pitch, mg in (('neutral_threequarter', 35, 22, 1.15), ('neutral_back_threequarter', 215, 20, 1.15), ('neutral_top', 0, 80, 1.1)):
        Q.camera_fit(vis, yaw, pitch, margin=mg); Q.render(out / f'{nm}.png', 1024, 48)
    # close-up: a port face or the busiest node
    if W.STATE['ports']:
        p = W.STATE['ports'][0]; c = Vector(p['position']) + Vector((0, 0, 0.22)); n = Vector(p['normal'])
        cam = s.camera; cam.data.lens = 50; cam.location = c + n * 0.75 + Vector((0.32, 0, 0.30)) if abs(n.y) > 0.5 else c + n * 0.75 + Vector((0, -0.32, 0.30))
        cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler(); Q.render(out / 'close_joint.png', 1024, 64)
    else:
        Q.camera_fit(vis, 20, 14, margin=0.55); Q.render(out / 'close_detail.png', 1024, 64)
    # 1.75 m scale rod + adopted eye height camera
    rod = W.scale_rod(loc=(Q.bbox(vis)[1][0] + 0.35, 0, 0))
    for o in rod: bpy.context.scene.collection.objects.link(o) if not o.users_collection else None
    Q.camera_fit(vis + rod, 25, 10, margin=1.12); Q.render(out / 'scale_1p75m.png', 1024, 40)
    cam = s.camera; mn, mx = Q.bbox(vis); ctr = Vector(((mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, (mn[2] + mx[2]) / 2))
    cam.data.lens = 28; cam.location = Vector((ctr.x + 0.9, ctr.y - 2.2, W.EYE_HEIGHT)); cam.rotation_euler = (ctr - cam.location).to_track_quat('-Z', 'Y').to_euler()
    Q.render(out / 'eye_height_1p62m.png', 1024, 40)
    for o in rod: bpy.data.objects.remove(o)
    # states
    if info.get('anim') and info['anim'].get('tracks'):
        s.frame_set(info['anim']['frames']); Q.camera_fit(vis, 35, 22, margin=1.15); Q.render(out / 'state_end.png', 1024, 48)
        Q.camera_fit(vis, 90, 10, margin=1.15); Q.render(out / 'state_end_side.png', 1024, 40)
        s.frame_set(1); Q.render(out / 'state_start_side.png', 1024, 40)
    # wireframe
    wm, nt, b = Q.new_mat('QA_Wire'); w = Q.N(nt, 'ShaderNodeWireframe', use_pixel_size=True); w.inputs['Size'].default_value = 1.0
    col = Q.mix(nt, w.outputs['Fac'], (0.72, 0.72, 0.70), (0.05, 0.05, 0.06)); Q.L(nt, col, b.inputs['Base Color'])
    keep = [list(o.data.materials) for o in vis]
    for o in vis:
        for i in range(len(o.data.materials)): o.data.materials[i] = wm
    Q.camera_fit(vis, 35, 22); Q.render(out / 'wireframe.png', 1024, 16)
    for o, ms in zip(vis, keep):
        for i, m in enumerate(ms): o.data.materials[i] = m
    for o in list(bpy.data.objects):
        if o.name.startswith('QA_') and o.type in ('LIGHT', 'MESH'): bpy.data.objects.remove(o)
    Q.studio('stylized')
    for nm, yaw, pitch in (('stylized_threequarter', 35, 20), ('stylized_front', 0, 12)):
        Q.camera_fit(vis, yaw, pitch); Q.render(out / f'{nm}.png', 1024, 64)


def roundtrip_render(path, out):
    s = bpy.context.scene; Q.gpu(s, 32); Q.studio('neutral')
    ms = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith('QA_')]
    Q.camera_fit(ms, 35, 22); Q.render(out, 768, 32)


# ----------------------------------------------------------------------------- one asset
def build(a):
    t0 = time.time(); Q.reset(); W.begin(); key = f"{a['id']}_{a['name']}"
    ref = REF / a['ref']
    assert ref.exists(), f'{key}: three-view {ref} missing - refuse to model'
    src = Q.coll('10_Procedural_Source'); Q.ACTIVE['coll'] = src
    parts, info = a['build']()
    bpy.context.view_layer.update()
    W.apply_all(parts); W.roughen(parts); fix_normals(parts); W.tag_water_attrs(parts); Q.finalize_parts(parts)
    empty = [o.name for o in parts if o.type == 'MESH' and not o.get('qa_cutter') and not o.data.polygons]
    assert not empty, f'{key}: parts lost all faces (boolean failure): {empty}'
    ok_pairs, bad_pairs = part_overlaps(parts)
    game = Q.coll('00_Game_Export'); Q.ACTIVE['coll'] = game
    G = game_mesh(key, parts, game, below=info.get('below', -0.003))
    cop = coplanar_report(G)
    adir = Q.EXPORTS / key; tdir = adir / 'textures'
    imgs, alpha = Q.bake_asset(G, key, tdir, a['res'])
    gm = Q.game_material(key, imgs, alpha); G.data.materials.clear(); G.data.materials.append(gm)
    uvr = uv_report(G, a['res'])
    G.name = f'{key}_LOD0'
    nodes = Q.split_nodes(G, key)
    for o in nodes:
        if o is not G and o.name.endswith('_LOD0'): pass
    kept = []
    for o in parts:
        if o.type == 'MESH' and (o.get('ww_keep') or o.get('qa_node') == 'Water'):
            for c in o.users_collection: c.objects.unlink(o)
            game.objects.link(o); nm = o.get('qa_node', 'Part') if o.get('qa_node') else o.name.split('_', 1)[-1]
            o.name = f"{key}_{o['ww_name'] if o.get('ww_name') else nm}"; kept.append(o)
    root = bpy.data.objects.new(key, None); game.objects.link(root); root.empty_display_size = 0.2
    root['ww_asset'] = a['id']; root['ww_units'] = 'metre'; root['ww_origin'] = info.get('origin_note', 'base centre')
    node_of = {'Body': G}
    for o in nodes[1:]:
        node_of[o.name[len(key) + 1:-5]] = o
    for o in kept: node_of[o.name[len(key) + 1:]] = o
    for nm, p in info.get('pivots', {}).items():
        o = node_of[nm]; o.data.transform(Matrix.Translation(-Vector(p))); o.location = Vector(p)
    lods = []
    for o in nodes:
        base = o.name[:-5]
        for i, r in enumerate((0.5, 0.22), 1):
            c = o.copy(); c.data = o.data.copy(); c.name = f'{base}_LOD{i}'; game.objects.link(c)
            d = c.modifiers.new('Decimate', 'DECIMATE'); d.ratio = r; d.use_collapse_triangulate = True
            Q.apply_mods(c); Q.clean_uvs(c); c.parent = o; c.matrix_parent_inverse = o.matrix_world.inverted(); lods.append(c)
    for o in nodes + kept:
        mw = o.matrix_world.copy(); o.parent = root; o.matrix_world = mw
    socks = []
    for p in W.STATE['ports'] + info.get('sockets', []):
        e = bpy.data.objects.new(f"SOCKET_{p['name']}", None); game.objects.link(e); e.empty_display_type = 'SINGLE_ARROW'
        e.empty_display_size = 0.12; e.location = p['position']
        n = Vector(p['normal']); e.rotation_euler = (-n).to_track_quat('Y', 'Z').to_euler() if abs(n.z) < 0.9 else e.rotation_euler
        for k, v in p.items():
            if k != 'name': e[k] = json.dumps(v) if isinstance(v, (list, dict)) else v
        e.parent = root; socks.append(e)
    anim = info.get('anim'); s = bpy.context.scene
    if anim:
        s.name = anim['name']; s.frame_start = 1; s.frame_end = anim['frames']; s.render.fps = 24
        for nm, prop, ax, vals in anim.get('tracks', []):
            o = node_of[nm]; base = getattr(o, 'location' if prop == 'location' else 'rotation_euler')[ax]
            for i, v in enumerate(vals):
                f = 1 + round(i * (anim['frames'] - 1) / (len(vals) - 1))
                if prop == 'location': o.location[ax] = base + v; o.keyframe_insert('location', index=ax, frame=f)
                else: o.rotation_euler[ax] = base + v; o.keyframe_insert('rotation_euler', index=ax, frame=f)
            o.animation_data.action.name = f"{anim['name']}_{nm}"
        for nm, kb, vals in anim.get('morphs', []):
            o = node_of[nm]; blk = o.data.shape_keys.key_blocks[kb]
            for i, v in enumerate(vals):
                f = 1 + round(i * (anim['frames'] - 1) / (len(vals) - 1)); blk.value = v; blk.keyframe_insert('value', frame=f)
        for o in bpy.data.objects:
            ad = o.animation_data
            for owner in (o, getattr(o.data, 'shape_keys', None)):
                if owner and owner.animation_data and owner.animation_data.action:
                    for fc in _fcurves(owner.animation_data.action):
                        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR' if not anim.get('loop') else 'BEZIER'
        s.frame_set(1)
    src.hide_render = True; src.hide_viewport = True
    for o in src.objects: o.hide_render = True
    for l in lods: l.hide_render = True
    glb = adir / f'{key}.glb'; fbx = adir / f'{key}.fbx'; adir.mkdir(parents=True, exist_ok=True)
    W.localize_images(kept, tdir)
    export_glb(root, glb, anim); export_fbx(root, fbx)
    blend = Q.HERE / 'blend' / f'{key}_{Q.VER}.blend'; blend.parent.mkdir(parents=True, exist_ok=True)
    for img in bpy.data.images:
        if img.filepath_raw and img.filepath_raw.startswith(str(tdir)): img.filepath = img.filepath_raw
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True, relative_remap=True)
    bpy.ops.file.make_paths_relative(); bpy.ops.wm.save_mainfile(compress=True)
    # validation (rest pose)
    s.frame_set(1)
    vis = nodes + kept; mn, mx = Q.bbox(vis); dims = [round(mx[i] - mn[i], 4) for i in range(3)]
    tris = [sum(Q.tri_count(o) for o in nodes)] + [sum(Q.tri_count(l) for l in lods if l.name.endswith(f'_LOD{i}')) for i in (1, 2)]
    water_tris = sum(Q.tri_count(o) for o in kept)
    hs = [Q.mesh_health(o) for o in nodes]; health = {k: sum(h[k] for h in hs) for k in hs[0]}
    finite = all(all(math.isfinite(c) for c in v.co) for o in vis for v in o.data.vertices)
    body_mn, body_mx = Q.bbox([G])
    pivots = {nm: [round(c, 4) for c in node_of[nm].location] for nm in info.get('pivots', {})}
    anim_range = None
    if anim and anim.get('tracks'):
        rng = {}
        for nm, prop, ax, vals in anim['tracks']:
            o = node_of[nm]; s.frame_set(anim['frames']); end = (o.location if prop == 'location' else o.rotation_euler)[ax]
            s.frame_set(1); st = (o.location if prop == 'location' else o.rotation_euler)[ax]
            rng[f'{nm}.{prop}[{ax}]'] = [round(st, 4), round(end, 4)]
        anim_range = rng
    gj = glb_json(glb)
    v = {'asset': a['id'], 'key': key, 'version': Q.VER, 'reference': {'file': a['ref'], 'sha256': Q.sha(ref)},
         'dimensions_m': dims, 'target_size_m': a['size'], 'bbox_min': [round(x, 4) for x in mn], 'bbox_max': [round(x, 4) for x in mx],
         'body_min_z': round(body_mn[2], 4), 'groundContact': abs(body_mn[2]) < 0.002 or info.get('below', 0) < -0.003,
         'finiteCoordinates': finite, 'trianglesLOD': tris, 'waterTriangles': water_tris, 'budgetLOD0': a['budget'], 'withinBudget': tris[0] <= a['budget'],
         'vertices': sum(len(o.data.vertices) for o in nodes), 'nodes': [o.name for o in nodes + kept], 'meshHealth': health,
         'coplanar': cop, 'uv': uvr, 'designedJointOverlaps': len(ok_pairs), 'unlistedOverlaps': bad_pairs,
         'materials': sorted({m.name for o in vis for m in o.data.materials if m}), 'textureResolution': a['res'],
         'textures': sorted(p.name for p in tdir.glob(f'T_{key}_*.png')), 'pivots': pivots, 'animationRange': anim_range,
         'sockets': [e.name for e in socks], 'glbAnimations': [x.get('name') for x in gj.get('animations', [])],
         'glbAlphaModes': {m.get('name', ''): m.get('alphaMode', 'OPAQUE') for m in gj.get('materials', [])},
         'buildSecondsBeforeRender': round(time.time() - t0, 1)}
    lift = info.get("preview_lift", 0.0)   # axle-rooted parts are shown at their mounted height, not half in the ground
    if RENDER:
        root.location.z += lift; bpy.context.view_layer.update()
        previews(a, key, vis, info, root)
        root.location.z -= lift; bpy.context.view_layer.update()
    rg = roundtrip(glb, 'glb')
    if RENDER: roundtrip_render(glb, Q.PREVIEWS / a['id'] / 'reimport_glb.png')
    rf = roundtrip(fbx, 'fbx')
    v['glbRoundTrip'] = dict(rg, trianglesMatch=rg['triangles'] == tris[0] + water_tris,
                             bboxMatch=all(abs(p - q) < 0.003 for p, q in zip(rg['bbox_min'] + rg['bbox_max'], mn + mx)),
                             socketsMatch=rg['empties'] >= len(socks) + 1, animationOk=(not anim) or bool(rg['actions']))
    v['fbxRoundTrip'] = dict(rf, trianglesMatch=rf['triangles'] == tris[0] + water_tris,
                             bboxMatch=all(abs(p - q) < 0.003 for p, q in zip(rf['bbox_min'] + rf['bbox_max'], mn + mx)),
                             lodsPresent=len(rf['lods']) == len(lods))
    v['files'] = {p.name: {'bytes': p.stat().st_size, 'sha256': Q.sha(p)} for p in (glb, fbx, blend)}
    v['buildSeconds'] = round(time.time() - t0, 1)
    v['notChecked'] = ['Unity import / LOD Group setup', 'in-game lighting and water shader', 'mobile performance']
    mi = dict(id=a['id'], name=a['name'], key=key, author=AUTHOR, reference_author=a.get('ref_author', 'Codex / OpenAI image_gen'), variant_of=a.get('variant_of'), units='metre',
              axes='Blender Z-up, front -Y; glTF Y-up, front +Z', origin=info.get('origin_note', 'base centre'),
              dimensions_m=dims, triangles=tris[0], lod_triangles=tris, collision=info.get('collision', []), ports=W.STATE['ports'],
              sockets=info.get('sockets', []), animation=anim, mechanism=info.get('mechanism'), decisions=info.get('decisions', []),
              validation=v)
    (adir / f'{key}_model_info.json').write_text(json.dumps(mi, indent=1, ensure_ascii=False, default=float), encoding='utf-8')
    print(f"[{key}] tris {tris} dims {dims} health {health} coplanar {cop} overlapsBad {len(bad_pairs)} "
          f"glb {v['glbRoundTrip']['trianglesMatch']}/{v['glbRoundTrip']['bboxMatch']} fbx {v['fbxRoundTrip']['trianglesMatch']} {v['buildSeconds']}s", flush=True)
    return v


def _fcurves(action):
    if hasattr(action, 'fcurves') and len(action.fcurves): return list(action.fcurves)
    out = []
    for layer in getattr(action, 'layers', []):
        for strip in layer.strips:
            for bag in strip.channelbags: out += list(bag.fcurves)
    return out


if __name__ == '__main__':
    report = {}
    for aid in ids:
        report[aid] = build(A.ASSETS[aid])
    print('DONE', ', '.join(report))
