"""TerritoryInterior18 v002: LOD1 / LOD2 rebuilt from the v001 LOD0 to about 50% / 15% (00-overview §4.2).

LOD0, materials, textures and sockets are the v001 ones, unchanged. Per mesh group, LOD1/LOD2 first drop small parts
(the `part_detail` face layer, same rule as v001) only while that still leaves enough triangles, then a collapse
decimate is tuned until the count lands on the target. v001 files are not touched; writes:
  art/source/territory-interior-b/blend/<ID>_v002.blend
  art/exports/territory-interior-b/<ID>/<ID>_v002.fbx, model_info_v002.json, validation_v002.json
  art/previews/territory-interior-b/<ID>/<ID>_lod_v001_v002.png   (v001 row above, v002 row below)

blender --background --factory-startup art/source/territory-interior-b/blend/<ID>_v001.blend --python lod_v002.py -- <ID> <repo>/art
"""
import bpy, bmesh, json, math, sys, hashlib
from pathlib import Path
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
AID, ART = argv[0], Path(argv[1])
KIT = 'territory-interior-b'
TARGET = {1: .50, 2: .15}
DROPS = {1: (2, 3, 99), 2: (1, 2, 3, 99)}          # most aggressive first; 99 keeps every part
BLEND = ART / 'source' / KIT / 'blend' / f'{AID}_v002.blend'
EXP = ART / 'exports' / KIT / AID
FBX = EXP / f'{AID}_v002.fbx'
PNG = ART / 'previews' / KIT / AID / f'{AID}_lod_v001_v002.png'


def tris(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def eval_tris(o):
    dg = bpy.context.evaluated_depsgraph_get(); e = o.evaluated_get(dg)
    m = e.to_mesh(); n = tris(m); e.to_mesh_clear(); return n


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# the v001 blend points at the build-time texture folder; use the delivered copies next to the FBX
for img in bpy.data.images:
    if img.source == 'FILE' and img.filepath:
        p = EXP / 'Textures' / Path(bpy.path.abspath(img.filepath)).name
        if p.exists(): img.filepath = str(p); img.reload()

root = bpy.data.objects[AID]
kids = [o for o in root.children if o.type == 'MESH']
lod0 = sorted([o for o in kids if o.name.endswith('_LOD0')], key=lambda o: o.name)
old = {o.name: o for o in kids if o.name.endswith(('_LOD1', '_LOD2'))}
for o in old.values():
    o.name = o.name + '_v001'; o.parent = None   # kept only for the comparison render
col = lod0[0].users_collection[0]

groups = {}
for src in lod0:
    n0 = tris(src.data); g = {'LOD0': n0}
    for lv in (1, 2):
        want = n0 * TARGET[lv]
        for drop in DROPS[lv]:
            me = src.data.copy()
            bm = bmesh.new(); bm.from_mesh(me)
            lay = bm.faces.layers.int.get('part_detail')
            if lay is not None and drop < 99:
                bmesh.ops.delete(bm, geom=[f for f in bm.faces if f[lay] >= drop], context='FACES')
            bm.to_mesh(me); bm.free()
            if tris(me) >= want * .98 or drop == 99:
                break
            bpy.data.meshes.remove(me)
        o = src.copy(); o.data = me; col.objects.link(o)
        o.name = src.name.replace('_LOD0', f'_LOD{lv}'); me.name = o.name
        start = tris(me); r = min(1., want / max(start, 1))
        if r < .999:
            m = o.modifiers.new('LOD_decimate', 'DECIMATE'); m.use_collapse_triangulate = True; m.ratio = r
            for _ in range(6):                               # collapse lands a little off the asked ratio; walk it in
                n = eval_tris(o)
                if abs(n - want) <= max(2, want * .01): break
                m.ratio = min(1., m.ratio * want / max(n, 1))
        bpy.ops.object.select_all(action='DESELECT'); o.hide_set(False); o.select_set(True); bpy.context.view_layer.objects.active = o
        if r < .999: bpy.ops.object.modifier_apply(modifier=m.name)
        try: bpy.ops.mesh.customdata_custom_splitnormals_clear()
        except Exception: pass
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(38))
        g[f'LOD{lv}'] = tris(o.data); g[f'LOD{lv}_drop_part_detail_ge'] = drop
    groups[src.name.replace('_LOD0', '')] = g

new = [o for o in root.children if o.type == 'MESH']
sockets = [o for o in root.children if o.type == 'EMPTY']
total = {k: sum(g[k] for g in groups.values()) for k in ('LOD0', 'LOD1', 'LOD2')}
old_total = {f'LOD{lv}': sum(tris(o.data) for n, o in old.items() if n.endswith(f'_LOD{lv}')) for lv in (1, 2)}

# ---------------------------------------------------------------- FBX (same settings as v001)
EXP.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='DESELECT')
for o in [root] + new + sockets: o.hide_set(False); o.select_set(True)
bpy.context.view_layer.objects.active = root
bpy.ops.export_scene.fbx(filepath=str(FBX), use_selection=True, object_types={'MESH', 'EMPTY'},
                         apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL', bake_space_transform=True,
                         axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE', use_mesh_modifiers=True,
                         add_leaf_bones=False, bake_anim=False, path_mode='STRIP', embed_textures=False)

# ---------------------------------------------------------------- re-import check
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(FBX))
imp = [o for o in bpy.data.objects if o not in before]
imp_mesh = {o.name.split('.')[0]: o for o in imp if o.type == 'MESH'}
imp_tris = {k: tris(o.data) for k, o in imp_mesh.items()}
lo = [Vector((1e9,) * 3), Vector((-1e9,) * 3)]
for k, o in imp_mesh.items():
    if k.endswith('_LOD0'):
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c); lo[0] = Vector(map(min, lo[0], w)); lo[1] = Vector(map(max, lo[1], w))
dims = [round(v, 4) for v in (lo[1] - lo[0])]
imp_sockets = sorted(o.name.split('.')[0] for o in imp if o.type == 'EMPTY' and o.name.startswith('SOCKET_'))
for o in imp: bpy.data.objects.remove(o, do_unlink=True)

checks = {}
names_ok = all(f'{g}_LOD{lv}' in imp_mesh for g in groups for lv in (0, 1, 2))
checks['fbx_reimport_has_every_group_LOD0_LOD1_LOD2'] = names_ok
checks['fbx_reimport_triangles_match'] = all(imp_tris.get(f'{g}_LOD{lv}') == groups[g][f'LOD{lv}'] for g in groups for lv in (0, 1, 2))
checks['fbx_reimport_sockets'] = imp_sockets == sorted(o.name for o in sockets)
r1, r2 = total['LOD1'] / total['LOD0'], total['LOD2'] / total['LOD0']
checks['LOD1_ratio_45_55_percent'] = .45 <= r1 <= .55
checks['LOD2_ratio_12_18_percent'] = .12 <= r2 <= .18

# ---------------------------------------------------------------- comparison render: v001 row above, v002 row below
scene = bpy.context.scene
for o in scene.objects: o.hide_render = True
def level(objs, lv): return [o for o in objs if o.name.endswith(f'_LOD{lv}') or o.name.endswith(f'_LOD{lv}_v001')]
bb = [Vector((1e9,) * 3), Vector((-1e9,) * 3)]
for o in lod0:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c); bb[0] = Vector(map(min, bb[0], w)); bb[1] = Vector(map(max, bb[1], w))
size = bb[1] - bb[0]; sx = max(size.x, size.y) * 1.35 + .05; sz = size.z * 1.45 + .05
rows = [(level(lod0, 0), level(old.values(), 1), level(old.values(), 2)), (level(lod0, 0), level(new, 1), level(new, 2))]
labels = [('v001', total['LOD0'], old_total['LOD1'], old_total['LOD2']), ('v002', total['LOD0'], total['LOD1'], total['LOD2'])]
shown = []
font = None
for fp in ('C:/Windows/Fonts/msjh.ttc', 'C:/Windows/Fonts/msyh.ttc'):
    try: font = bpy.data.fonts.load(fp); break
    except Exception: pass
for ri, row in enumerate(rows):
    for ci, objs in enumerate(row):
        off = Vector((ci * sx, 0, (1 - ri) * sz)) - Vector((bb[0].x + size.x / 2, 0, 0))
        for o in objs:
            d = o.copy(); scene.collection.objects.link(d); d.parent = None
            d.matrix_world = o.matrix_world.copy(); d.location = d.location + off; d.hide_render = False; shown.append(d)
        ver, n0, n1, n2 = labels[ri]; n = (n0, n1, n2)[ci]
        txt = f'{ver}  LOD{ci}\n{n:,} tris  {n / n0 * 100:.0f}%'
        cu = bpy.data.curves.new(f'lbl{ri}{ci}', 'FONT'); cu.body = txt; cu.size = sz * .07; cu.align_x = 'CENTER'
        if font: cu.font = font
        t = bpy.data.objects.new(cu.name, cu); scene.collection.objects.link(t)
        t.location = Vector((ci * sx, bb[0].y - .02, (1 - ri) * sz - sz * .1)); t.rotation_euler = (math.radians(90), 0, 0)
        mat = bpy.data.materials.new('Label'); mat.use_nodes = True
        mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.92, .9, .84, 1)
        mat.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value = (.92, .9, .84, 1)
        mat.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 1.0
        cu.materials.append(mat); shown.append(t)

top = sz + size.z; bottom = -sz * .22
centre = Vector((sx, bb[0].y, (top + bottom) / 2))
cam_d = bpy.data.cameras.new('CompareCam'); cam_d.type = 'ORTHO'
cam = bpy.data.objects.new('CompareCam', cam_d); scene.collection.objects.link(cam)
direction = Vector((.3, -1., .18)).normalized()
cam.location = centre + direction * (max(sx, sz) * 6)
cam.rotation_euler = (-direction).to_track_quat('-Z', 'Y').to_euler()
cam_d.ortho_scale = max(3 * sx, (top - bottom) * 1.8) * 1.1
scene.camera = cam
sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); scene.collection.objects.link(sun)
sun.data.energy = 3.2; sun.rotation_euler = (math.radians(55), 0, math.radians(30))
fill = bpy.data.objects.new('Fill', bpy.data.lights.new('Fill', 'SUN')); scene.collection.objects.link(fill)
fill.data.energy = 1.0; fill.rotation_euler = (math.radians(70), 0, math.radians(-140))
w = bpy.data.worlds.new('Grey'); w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (.16, .17, .18, 1)
w.node_tree.nodes['Background'].inputs[1].default_value = .9; scene.world = w
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x, scene.render.resolution_y = 1800, 1000
scene.render.film_transparent = False
scene.view_settings.view_transform = 'Standard'
PNG.parent.mkdir(parents=True, exist_ok=True)
scene.render.filepath = str(PNG)
bpy.ops.render.render(write_still=True)

# ---------------------------------------------------------------- clean up, save the v002 working file
for o in shown + [cam, sun, fill] + list(old.values()):
    bpy.data.objects.remove(o, do_unlink=True)
BLEND.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), copy=True)

info_v1 = json.loads((EXP / 'model_info.json').read_text(encoding='utf-8'))
info = dict(info_v1)
info.update({
    'version': 'v002',
    'supersedes': 'v001 (LOD0, materials, textures and sockets unchanged; LOD1/LOD2 rebuilt)',
    'files': {'fbx': FBX.name, 'blend': f'art/source/{KIT}/blend/{BLEND.name}', 'textures': 'Textures/ (same as v001)'},
    'lod_rule': 'LOD1 ~50%, LOD2 ~15% of LOD0 triangles (00-overview 4.2); small parts dropped only while enough triangles remain, then collapse decimate',
    'lod_triangles_total': total,
    'lod_ratio': {'LOD1': round(r1, 3), 'LOD2': round(r2, 3)},
    'lod_groups': groups,
    'v001_lod_triangles_total': {'LOD0': total['LOD0'], **old_total},
})
(EXP / 'model_info_v002.json').write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')
val = {'asset': AID, 'version': 'v002', 'checks': checks, 'passed': all(checks.values()),
       'fbx_reimport_LOD0_dimensions_m': dims, 'fbx_sha256': sha(FBX),
       'comparison_render': f'art/previews/{KIT}/{AID}/{PNG.name}',
       'not_checked': ['Unity import of v002 (the Unity demo still loads v001; LOD0 is identical)', 'LODGroup switch distances']}
(EXP / 'validation_v002.json').write_text(json.dumps(val, ensure_ascii=False, indent=2), encoding='utf-8')
print('LODV002', AID, json.dumps({'total': total, 'ratio': [round(r1, 3), round(r2, 3)], 'checks': checks}))
