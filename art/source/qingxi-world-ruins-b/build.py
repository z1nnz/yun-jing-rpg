"""qingxi-world-ruins-b build: model -> atlas per material slot -> bake (BaseColor / Normal / ORM) -> LOD1 50% /
LOD2 15% -> collision -> FBX + GLB -> re-import check -> review renders -> model_info.json / validation.json.

One asset per process keeps memory flat:
  blender -b --factory-startup --python art/source/qingxi-world-ruins-b/build.py -- <ASSET_ID> [--fast]
--fast bakes at 1/4 resolution with few samples (look-dev only; never delivered).

Writes (version v001, never overwrites another version):
  art/source/qingxi-world-ruins-b/blend/<ID>_v001.blend
  art/exports/qingxi-world-ruins-b/<ID>/<ID>_v001.fbx, <ID>_v001.glb, Textures/, model_info.json, validation.json
  art/previews/qingxi-world-ruins-b/<ID>/ (four 1.75 m review views, 3/4 hero, LOD strip)
Specs: docs/art/modeling-style-spec-v1.md (sections 3, 6-8), docs/execution/2026-10-29/14-grounding-spec.md.
"""
import bpy, bmesh, sys, json, math, time, hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np
from mathutils import Vector, Matrix
import wr_core as C
from wr_core import S
from wr_mats import MAT_INFO
import assets as A

KIT = 'qingxi-world-ruins-b'
VER = 'v001'
ART = HERE.parent.parent
REPO = ART.parent
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
AID = argv[0]; FAST = '--fast' in argv
SPEC = A.ASSETS[AID]
EXP = ART / 'exports' / KIT / AID
PRE = ART / 'previews' / KIT / AID
BLEND = HERE / 'blend' / f'{AID}_{VER}.blend'
LOD_TARGET = {1: .50, 2: .15}
DROPS = {1: (2, 99), 2: (1, 2, 99)}
T0 = time.time()


def log(*a): print(f'[{time.time() - T0:7.1f}s]', AID, *a, flush=True)


def tris(me): return sum(len(p.vertices) - 2 for p in me.polygons)


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def gpu():
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for kind in ('OPTIX', 'CUDA'):
        try:
            prefs.compute_device_type = kind; prefs.get_devices()
            if any(d.type == kind for d in prefs.devices):
                for d in prefs.devices: d.use = d.type == kind
                bpy.context.scene.cycles.device = 'GPU'; return kind
        except Exception: pass
    bpy.context.scene.cycles.device = 'CPU'; return 'CPU'


# ---------------------------------------------------------------- 1. model
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
C.reset_state(AID)
SPEC['build']()
bpy.context.view_layer.update()
C.write_grain_attributes()
parts = [o for o in S['parts'] if o.type == 'MESH']
log('parts', len(parts))

# ---------------------------------------------------------------- 2. join per material slot group (all 'Main' unless a material says otherwise)
dg = bpy.context.evaluated_depsgraph_get()
lodcol = bpy.data.collections.new('02_Export_LODs'); scene.collection.children.link(lodcol)
temps = []
for o in parts:
    e = o.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(e, preserve_all_data_layers=True, depsgraph=dg)
    if not me.uv_layers: me.uv_layers.new(name='UVMap')
    while len(me.uv_layers) > 1: me.uv_layers.remove(me.uv_layers[-1])
    at = me.attributes.new('part_detail', 'INT', 'FACE'); at.data.foreach_set('value', [int(o['detail'])] * len(me.polygons))
    if o.get('inst_key'):        # whole-object UV instancing (identical parts share one baked master)
        S['inst_counter'] = S.get('inst_counter', 0) + 1; nf = len(me.polygons)
        for nm, vals in (('inst_key', [int(o['inst_key'])] * nf), ('inst_tile', [S['inst_counter']] * nf), ('inst_f', list(range(nf)))):
            (me.attributes.get(nm) or me.attributes.new(nm, 'INT', 'FACE')).data.foreach_set('value', vals)
    t = bpy.data.objects.new(o.name + '_eval', me); lodcol.objects.link(t); t.matrix_world = o.matrix_world.copy(); temps.append(t)
bpy.ops.object.select_all(action='DESELECT')
for t in temps: t.select_set(True)
bpy.context.view_layer.objects.active = temps[0]
bpy.ops.object.join()
lod0 = bpy.context.view_layer.objects.active
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
lod0.name = f'{AID}_LOD0'; lod0.data.name = lod0.name
for o in parts: o.hide_render = True; o.hide_set(True)
# merge duplicate material slots
mats = list(lod0.data.materials); uniq = []
for m in mats:
    if m not in uniq: uniq.append(m)
idx = np.zeros(len(lod0.data.polygons), np.int32); lod0.data.polygons.foreach_get('material_index', idx)
remap = np.array([uniq.index(m) for m in mats], np.int32)
lod0.data.materials.clear()
for m in uniq: lod0.data.materials.append(m)
lod0.data.polygons.foreach_set('material_index', remap[idx]); lod0.data.update()
slot_of = [MAT_INFO[m.name]['slot'] for m in lod0.data.materials]
SLOTS = sorted(set(slot_of), key=lambda s: (s != 'Main', s))
log('LOD0 tris', tris(lod0.data), 'slots', SLOTS)

# ---------------------------------------------------------------- 3. UV atlas, one 0-1 atlas per slot
bpy.ops.object.select_all(action='DESELECT'); lod0.select_set(True); bpy.context.view_layer.objects.active = lod0
scene.tool_settings.use_uv_select_sync = True
# hidden faces (buried, or enclosed by neighbouring parts: the backs and beds of stacked stones) get their own
# islands at 12 % texel density, so the atlas is spent on what can be seen
from mathutils.bvhtree import BVHTree
me0 = lod0.data
bvh = BVHTree.FromPolygons([v.co for v in me0.vertices], [p.vertices for p in me0.polygons], epsilon=0.0)
DIRS = []
for i in range(16):                                   # fixed cosine-ish hemisphere sample set around +Z
    a = i * 2.39996; zc = 1 - (i + .5) / 16 * .92
    DIRS.append(Vector((math.cos(a) * math.sqrt(1 - zc * zc), math.sin(a) * math.sqrt(1 - zc * zc), zc)))
hidden = np.zeros(len(me0.polygons), bool)
for p in me0.polygons:
    c = p.center; n = p.normal
    if c.z < -.01 and n.z < .5: hidden[p.index] = True; continue
    R = Vector((0, 0, 1)).rotation_difference(n).to_matrix()
    # sample the centre and points 85 % of the way to each corner: a big face half hidden behind a neighbour
    # still counts as visible
    samples = [c] + [c.lerp(me0.vertices[vi].co, .85) for vi in p.vertices]
    seen = False
    for s0 in samples:
        for d in DIRS:
            w = R @ d
            if bvh.ray_cast(s0 + n * .002, w, 1.5)[0] is None and (s0 + w * 1.5).z > -.01: seen = True; break
        if seen: break
    hidden[p.index] = not seen
def fattr(nm):
    at = me0.attributes.get(nm)
    if at is None or at.domain != 'FACE': return None
    arr = np.zeros(len(me0.polygons), np.int64); at.data.foreach_get('value', arr); return arr


IK, IT, IF = fattr('inst_key'), fattr('inst_tile'), fattr('inst_f')
inst_slave = np.zeros(len(me0.polygons), bool)
if IK is not None and IK.any():
    master = {}
    for k, t in zip(IK, IT):
        if k and (k not in master or t < master[k]): master[k] = t
    inst_slave = (IK > 0) & (IT != np.array([master.get(k, -1) for k in IK]))
    # a master face is baked at full density when it can be seen on any of its copies
    seen_any = {(int(k), int(f)) for k, f, h in zip(IK, IF, hidden) if k and not h}
    for i in np.nonzero((IK > 0) & ~inst_slave)[0]: hidden[i] = (int(IK[i]), int(IF[i])) not in seen_any
    hidden |= inst_slave
log('hidden faces', int(hidden.sum()), 'of', len(hidden), '(UV-instanced copies', int(inst_slave.sum()), ')')
scene.tool_settings.mesh_select_mode = (False, False, True)
UV_ANGLE = float(next((a.split('=')[1] for a in argv if a.startswith('--uvangle=')), 66))


def select_faces(pred):
    """Select exactly the faces for which pred(p) is true, with their vertices and edges (a stale vertex selection
    would flush into neighbouring faces of another material slot in edit mode)."""
    me0.vertices.foreach_set('select', [False] * len(me0.vertices)); me0.edges.foreach_set('select', [False] * len(me0.edges))
    vsel = np.zeros(len(me0.vertices), bool)
    for p in me0.polygons:
        p.select = bool(pred(p))
        if p.select: vsel[list(p.vertices)] = True
    me0.vertices.foreach_set('select', vsel.tolist())
    me0.edges.foreach_set('select', [bool(vsel[e.vertices[0]] and vsel[e.vertices[1]]) for e in me0.edges])


def texel_density(slot_name):
    uvd = me0.uv_layers[0].data; A = U = 0.0
    for p in me0.polygons:
        if hidden[p.index] or slot_of[p.material_index] != slot_name: continue
        A += p.area; l = [uvd[i].uv for i in p.loop_indices]
        U += sum(abs((l[k] - l[0]).cross(l[k + 1] - l[0])) / 2 for k in range(1, len(l) - 1))
    return round(SPEC.get('tex', 2048) * math.sqrt(U / max(A, 1e-9)), 1)


def uv_cover(slot_name):
    uvd = me0.uv_layers[0].data; U = 0.0
    for p in me0.polygons:
        if slot_of[p.material_index] != slot_name or inst_slave[p.index]: continue
        l = [uvd[i].uv for i in p.loop_indices]
        U += sum(abs((l[k] - l[0]).cross(l[k + 1] - l[0])) / 2 for k in range(1, len(l) - 1))
    return round(U, 3)


HIDDEN_UV = .12          # hidden faces keep this fraction of their UV size: they bake, but nobody sees them


def unwrap_all():
    for slot in SLOTS:
        for want_hidden in (False, True):
            select_faces(lambda p: slot_of[p.material_index] == slot and bool(hidden[p.index]) == want_hidden)
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.uv.smart_project(angle_limit=math.radians(UV_ANGLE), island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
            bpy.ops.object.mode_set(mode='OBJECT')
        select_faces(lambda p: slot_of[p.material_index] == slot)
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.uv.average_islands_scale(); bpy.ops.object.mode_set(mode='OBJECT')
        uvd = me0.uv_layers[0].data
        for p in me0.polygons:
            if hidden[p.index] and slot_of[p.material_index] == slot:
                for li in p.loop_indices: uvd[li].uv = uvd[li].uv * (.02 if inst_slave[p.index] else HIDDEN_UV)
        select_faces(lambda p: slot_of[p.material_index] == slot)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.uv.pack_islands(rotate=True, rotate_method='ANY', margin_method='FRACTION', margin=.001, shape_method='AABB')  # 2 px gaps at 2048
        bpy.ops.object.mode_set(mode='OBJECT')
    return {s: texel_density(s) for s in SLOTS}


# minimum visible texel density: 256 px/m by default; houses trade it down to keep texture memory in budget
MIN_TEXEL = SPEC.get('min_texel', 256)
TEXEL = unwrap_all()
log('uv done, visible texel density px/m', TEXEL)
log('uv coverage of the 0-1 square', {s: uv_cover(s) for s in SLOTS})
best = (min(TEXEL.values()), list(slot_of))
for attempt in range(5):
    if not SPEC.get('rebalance') or min(TEXEL.values()) >= MIN_TEXEL or len(SLOTS) < 2: break
    # move whole materials between the slots so every atlas carries a similar load, then unwrap again. A
    # material's load is its visible area divided by the packing efficiency its slot reached last time
    # (eff = density^2 * area / size^2), so thin-shelled tiles and blocky timbers are weighed fairly.
    vis = {}
    for p in me0.polygons:
        if not hidden[p.index]: vis[p.material_index] = vis.get(p.material_index, 0.0) + p.area
    A_s = {sl: sum(a for mi, a in vis.items() if slot_of[mi] == sl) for sl in SLOTS}
    eff = {sl: max(.2, TEXEL[sl] ** 2 * A_s[sl] / SPEC.get('tex', 2048) ** 2) for sl in SLOTS}
    cost = {mi: a / eff[slot_of[mi]] for mi, a in vis.items()}
    load = {sl: 0.0 for sl in SLOTS}
    if attempt < 2:
        for mi, c in sorted(cost.items(), key=lambda t: -t[1]):
            sl = min(load, key=load.get); slot_of[mi] = sl; load[sl] += c
    else:
        # greedy reassignment oscillates near the limit: instead move one material from the densest-packed slot
        # to the emptiest, the one whose cost best halves the gap
        for mi, c in cost.items(): load[slot_of[mi]] += c
        lo_s = min(TEXEL, key=TEXEL.get); hi_s = max(TEXEL, key=TEXEL.get)
        gap = (load[lo_s] - load[hi_s]) / 2
        cand = [mi for mi in cost if slot_of[mi] == lo_s and cost[mi] < 2 * max(gap, 1e-6)]
        if cand:
            mi = min(cand, key=lambda m: abs(cost[m] - gap)); slot_of[mi] = hi_s; load[lo_s] -= cost[mi]; load[hi_s] += cost[mi]
    for mi in range(len(slot_of)):
        if mi not in vis: slot_of[mi] = min(load, key=load.get)
    for mi, m in enumerate(lod0.data.materials): MAT_INFO[m.name]['slot'] = slot_of[mi]
    log('rebalanced slots, load', {k: round(v, 1) for k, v in load.items()},
        {lod0.data.materials[mi].name: slot_of[mi] for mi in sorted(vis, key=lambda m: -vis[m])})
    TEXEL = unwrap_all()
    log('uv done, visible texel density px/m', TEXEL)
    if min(TEXEL.values()) > best[0]: best = (min(TEXEL.values()), list(slot_of))
if SPEC.get('rebalance') and min(TEXEL.values()) < best[0]:
    # the assignments can oscillate: go back to the best one seen
    slot_of[:] = best[1]
    for mi, m in enumerate(lod0.data.materials): MAT_INFO[m.name]['slot'] = slot_of[mi]
    TEXEL = unwrap_all()
    log('restored the best slot assignment, texel density px/m', TEXEL)
if min(TEXEL.values()) < MIN_TEXEL:
    # still a little short: give the visible faces the room the hidden ones were holding
    HIDDEN_UV = .04
    TEXEL = unwrap_all()
    log('hidden faces shrunk to', HIDDEN_UV, 'texel density px/m', TEXEL)

if SPEC.get('rebalance'):
    # with rebalancing the slot names (Main / Roof / Wall / Stone) no longer describe their contents:
    # name each atlas after the material with the most visible area in it
    vis = {}
    for p in me0.polygons:
        if not hidden[p.index]: vis[p.material_index] = vis.get(p.material_index, 0.0) + p.area
    rename = {}
    for sl in SLOTS:
        mis = [mi for mi in range(len(slot_of)) if slot_of[mi] == sl]
        top = max(mis, key=lambda mi: vis.get(mi, 0.0))
        rename[sl] = lod0.data.materials[top].name.split('_', 2)[-1]
    slot_of[:] = [rename[sl] for sl in slot_of]
    for mi, m in enumerate(lod0.data.materials): MAT_INFO[m.name]['slot'] = slot_of[mi]
    TEXEL = {rename[sl]: v for sl, v in TEXEL.items()}
    SLOTS = [rename[sl] for sl in SLOTS]
    log('atlas slots named after their main material', rename)

# ---------------------------------------------------------------- 4. bake
# texture size: largest power of two <= 2048 keeping the visible texel density near the spec's 256-512 px/m
FULL = SPEC.get('tex', 2048)
dens = lambda f, agg=max: agg(TEXEL.values()) * f / SPEC.get('tex', 2048)
# halve only while every slot keeps at least MIN_TEXEL px/m (the sparsest slot decides, not the densest)
while FULL > 512 and dens(FULL) > 512 and dens(FULL / 2, min) >= MIN_TEXEL: FULL //= 2
TEXEL = {s: round(v * FULL / SPEC.get('tex', 2048), 1) for s, v in TEXEL.items()}
log('texture size', FULL, 'texel density', TEXEL)
SIZE = FULL // (4 if FAST else 1)
device = gpu()
scene.render.engine = 'CYCLES'; scene.render.bake.margin = 8; scene.render.bake.use_clear = True
TEX = EXP / 'Textures'; TEX.mkdir(parents=True, exist_ok=True)
for old in TEX.glob(f'T_{AID}_*.png'): old.unlink()          # atlas names can change between builds


def img(name, color):
    im = bpy.data.images.new(name, SIZE, SIZE, alpha=False, float_buffer=not color)
    im.colorspace_settings.name = 'sRGB' if color else 'Non-Color'; return im


passes = [('BaseColor', 'OUT_COLOR', True, 4 if FAST else 16), ('Roughness', 'OUT_ROUGH', False, 2 if FAST else 4),
          ('Metallic', 'OUT_METAL', False, 1), ('AO', None, False, 8 if FAST else 64), ('Normal', None, False, 2 if FAST else 8)]
baked = {s: {} for s in SLOTS}
for slot in SLOTS:
    smats = [m for m in lod0.data.materials if MAT_INFO[m.name]['slot'] == slot]
    others = [m for m in lod0.data.materials if m not in smats]
    dummy = bpy.data.images.new('dummy', 8, 8)
    for label, node_name, color, samples in passes:
        im = img(f'T_{AID}_{slot}_{label}', color); baked[slot][label] = im
        scene.cycles.samples = samples
        for m in smats + others:
            nt = m.node_tree; tn = nt.nodes.new('ShaderNodeTexImage'); tn.name = 'BAKE_TARGET'
            tn.image = im if m in smats else dummy; nt.nodes.active = tn
            if node_name:
                em = nt.nodes.new('ShaderNodeEmission'); em.name = 'BAKE_EMIT'
                src = nt.nodes[node_name].outputs[0]
                if src.type == 'VALUE':
                    cmb = nt.nodes.new('ShaderNodeCombineColor'); cmb.name = 'BAKE_CMB'
                    for i in range(3): nt.links.new(src, cmb.inputs[i])
                    src = cmb.outputs[0]
                nt.links.new(src, em.inputs['Color']); nt.links.new(em.outputs[0], nt.nodes['OUTPUT'].inputs['Surface'])
        if label == 'AO':
            scene.world = scene.world or bpy.data.worlds.new('W')
            bpy.ops.object.bake(type='AO')
        elif label == 'Normal':
            bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT')
        else:
            bpy.ops.object.bake(type='EMIT')
        for m in smats + others:
            nt = m.node_tree
            for nm in ('BAKE_TARGET', 'BAKE_EMIT', 'BAKE_CMB'):
                if nm in nt.nodes: nt.nodes.remove(nt.nodes[nm])
            bs = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]
            nt.links.new(bs.outputs[0], nt.nodes['OUTPUT'].inputs['Surface'])
        log('baked', slot, label, device)

files = {}
for slot in SLOTS:
    b = baked[slot]
    px = lambda im: np.array(im.pixels[:], np.float32).reshape(SIZE, SIZE, 4)
    orm = np.ones((SIZE, SIZE, 4), np.float32)
    ao = px(b['AO'])[..., 0]; orm[..., 0] = .35 + .65 * ao          # AO kept soft: the base colour already carries cavity darkening
    orm[..., 1] = px(b['Roughness'])[..., 0]; orm[..., 2] = px(b['Metallic'])[..., 0]
    o_im = img(f'T_{AID}_{slot}_ORM', False); o_im.pixels.foreach_set(orm.ravel())
    out = {}
    for label, im in (('BaseColor', b['BaseColor']), ('Normal', b['Normal']), ('ORM', o_im)):
        p = TEX / f'T_{AID}_{slot}_{label}.png'
        if im.is_float:                             # data maps baked in float: write them as 8-bit PNG (16-bit tripled the size)
            b8 = bpy.data.images.new(im.name + '_8', SIZE, SIZE, alpha=False, float_buffer=False)
            b8.colorspace_settings.name = 'Non-Color'
            b8.pixels.foreach_set(np.clip(np.array(im.pixels[:], np.float32), 0, 1)); im = b8
        im.filepath_raw = str(p); im.file_format = 'PNG'; im.save(); out[label] = p
    files[slot] = out
log('textures saved')
if inst_slave.any():
    where = {(int(k), int(f)): i for i, (k, t, f) in enumerate(zip(IK, IT, IF)) if k and t == master[k]}
    uvd = me0.uv_layers[0].data; n = 0
    for p in me0.polygons:
        if not inst_slave[p.index]: continue
        m = me0.polygons[where[(int(IK[p.index]), int(IF[p.index]))]]
        for a_, b_ in zip(p.loop_indices, m.loop_indices): uvd[a_].uv = uvd[b_].uv
        n += 1
    log('instanced UVs copied to', n, 'faces')

# ---------------------------------------------------------------- 5. LODs (drop small parts only while enough triangles remain, then tuned collapse)
def eval_tris(o):
    e = o.evaluated_get(bpy.context.evaluated_depsgraph_get()); m = e.to_mesh(); n = tris(m); e.to_mesh_clear(); return n


lods = {0: lod0}
n0 = tris(lod0.data)
for lv in (1, 2):
    want = n0 * LOD_TARGET[lv]
    for drop in DROPS[lv]:
        me = lod0.data.copy(); bm = bmesh.new(); bm.from_mesh(me)
        lay = bm.faces.layers.int.get('part_detail')
        if lay is not None and drop < 99:
            bmesh.ops.delete(bm, geom=[f for f in bm.faces if f[lay] >= drop], context='FACES')
        bm.to_mesh(me); bm.free()
        if tris(me) >= want * .98 or drop == 99: break
        bpy.data.meshes.remove(me)
    o = lod0.copy(); o.data = me; lodcol.objects.link(o); o.name = f'{AID}_LOD{lv}'; me.name = o.name
    r = min(1., want / max(tris(me), 1))
    if r < .999:
        m = o.modifiers.new('LOD', 'DECIMATE'); m.use_collapse_triangulate = True; m.ratio = r
        for _ in range(8):
            n = eval_tris(o)
            if abs(n - want) <= max(2, want * .01): break
            m.ratio = min(1., m.ratio * want / max(n, 1))
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier=m.name)
    with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o], selected_editable_objects=[o]):
        try: bpy.ops.mesh.customdata_custom_splitnormals_clear()
        except Exception: pass
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(36))
    lods[lv] = o
log('LOD tris', {k: tris(v.data) for k, v in lods.items()})

# ---------------------------------------------------------------- 6. shipped materials (baked textures, one per slot)
def load(p, color):
    im = bpy.data.images.load(str(p), check_existing=True); im.colorspace_settings.name = 'sRGB' if color else 'Non-Color'; return im


def gltf_group():
    g = bpy.data.node_groups.get('glTF Material Output')
    if g is None:
        g = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
        g.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
    return g


ship = {}
for slot in SLOTS:
    f = files[slot]
    m = bpy.data.materials.new(f'M_WRB_{AID}_{slot}' if len(SLOTS) > 1 else f'M_WRB_{AID}'); m.use_nodes = True; nt = m.node_tree
    bs = nt.nodes['Principled BSDF']
    tb = nt.nodes.new('ShaderNodeTexImage'); tb.image = load(f['BaseColor'], True); nt.links.new(tb.outputs[0], bs.inputs['Base Color'])
    to = nt.nodes.new('ShaderNodeTexImage'); to.image = load(f['ORM'], False)
    sp = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(to.outputs[0], sp.inputs[0])
    nt.links.new(sp.outputs[1], bs.inputs['Roughness']); nt.links.new(sp.outputs[2], bs.inputs['Metallic'])
    tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = load(f['Normal'], False)
    nm = nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(tn.outputs[0], nm.inputs['Color']); nt.links.new(nm.outputs[0], bs.inputs['Normal'])
    gg = nt.nodes.new('ShaderNodeGroup'); gg.node_tree = gltf_group(); nt.links.new(sp.outputs[0], gg.inputs['Occlusion'])
    bs.inputs['Specular IOR Level'].default_value = .3
    ship[slot] = m
for o in lods.values():
    me = o.data
    idx = np.zeros(len(me.polygons), np.int32); me.polygons.foreach_get('material_index', idx)
    order = [slot_of[i] for i in range(len(me.materials))]
    me.materials.clear()
    for s in SLOTS: me.materials.append(ship[s])
    me.polygons.foreach_set('material_index', np.array([SLOTS.index(order[i]) for i in idx], np.int32)); me.update()

# ---------------------------------------------------------------- 7. collision
colls = []
for i, c in enumerate(S['coll']):
    c.name = f'{AID}_Collision' if len(S['coll']) == 1 else f'{AID}_Collision_{i:02d}'; c.data.name = c.name
    for col in list(c.users_collection): col.objects.unlink(c)
    lodcol.objects.link(c); colls.append(c)

# ---------------------------------------------------------------- 8. export
EXP.mkdir(parents=True, exist_ok=True)
root = bpy.data.objects.new(AID, None); lodcol.objects.link(root)
for o in list(lods.values()) + colls: o.parent = root
FBX = EXP / f'{AID}_{VER}.fbx'; GLB = EXP / f'{AID}_{VER}.glb'
bpy.ops.object.select_all(action='DESELECT')
for o in [root] + list(lods.values()) + colls: o.hide_set(False); o.select_set(True)
bpy.context.view_layer.objects.active = root
bpy.ops.export_scene.fbx(filepath=str(FBX), use_selection=True, object_types={'MESH', 'EMPTY'}, apply_unit_scale=True,
                         apply_scale_options='FBX_SCALE_ALL', bake_space_transform=True, axis_forward='-Z', axis_up='Y',
                         mesh_smooth_type='FACE', use_mesh_modifiers=True, add_leaf_bones=False, bake_anim=False,
                         path_mode='STRIP', embed_textures=False)
bpy.ops.object.select_all(action='DESELECT')
for o in [root, lods[0]] + colls: o.select_set(True)
# textures go into the GLB as WebP (EXT_texture_webp) to keep the browser download small; Textures/ keeps the PNGs
bpy.ops.export_scene.gltf(filepath=str(GLB), use_selection=True, export_format='GLB', export_apply=True, export_yup=True,
                          export_image_format=SPEC.get('glb_image', 'WEBP'), export_image_quality=SPEC.get('glb_quality', 90))
log('exported', FBX.name, GLB.name)

# re-import checks
before = set(bpy.data.objects)
tmp = bpy.data.collections.new('99_Check'); scene.collection.children.link(tmp)
bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children[tmp.name]
bpy.ops.import_scene.fbx(filepath=str(FBX))
imp = [o for o in bpy.data.objects if o not in before]
imp_m = {o.name.split('.')[0]: o for o in imp if o.type == 'MESH'}
bpy.context.view_layer.update()


def bbox(objs):
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return lo, hi


rl, rh = bbox([o for k, o in imp_m.items() if k.endswith('_LOD0')])
fbx_check = {'objects': sorted(imp_m), 'lod0_size_m': [round(v, 4) for v in rh - rl], 'lod0_min_m': [round(v, 4) for v in rl],
             'tris': {k: tris(o.data) for k, o in imp_m.items()}}
for o in imp: bpy.data.objects.remove(o, do_unlink=True)
bpy.data.collections.remove(tmp)
# GLB: read the JSON chunk directly (Blender 5.2's glTF importer fails on its own Principled mapping)
import struct
raw = GLB.read_bytes(); jl = struct.unpack('<I', raw[12:16])[0]; gj = json.loads(raw[20:20 + jl])
glb_check = {'meshes': sorted(n.get('name', '') for n in gj.get('nodes', []) if 'mesh' in n),
             'images': len(gj.get('images', [])), 'materials': [m.get('name') for m in gj.get('materials', [])],
             'occlusion_texture': any('occlusionTexture' in m for m in gj.get('materials', [])), 'bytes': len(raw)}
bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection

# ---------------------------------------------------------------- 9. review renders (exported LOD0, baked textures)
import review
review.render_all(AID, SPEC, lods, colls, PRE, FAST)
log('renders done')

# ---------------------------------------------------------------- 10. info + validation
lo, hi = bbox([lods[0]])
size = hi - lo
tri = {f'LOD{k}': tris(v.data) for k, v in lods.items()}
coll_info = [{'name': c.name, 'type': 'convex hull', 'vertices': len(c.data.vertices), 'faces': len(c.data.polygons)} for c in colls]
info = {
    'asset': AID, 'name_zh': SPEC['zh'], 'version': VER, 'kit': KIT, 'batch': SPEC['batch'],
    'units': '1 unit = 1 m; Blender Z-up, FBX/GLB exported Y-up; front faces -Y in Blender (-Z forward in FBX)',
    'origin': 'footprint centre, z = 0 at ground level', 'design_embed_depth_m': SPEC.get('embed', 0.0),
    'size_m': {'x': round(size.x, 3), 'y': round(size.y, 3), 'z_above_ground': round(hi.z, 3), 'z_below_ground': round(-min(lo.z, 0), 3)},
    'bounds_m': {'min': [round(v, 3) for v in lo], 'max': [round(v, 3) for v in hi]},
    'slot_limit_m': SPEC.get('limit'), 'triangles': tri,
    'lod_ratio': {'LOD1': round(tri['LOD1'] / tri['LOD0'], 3), 'LOD2': round(tri['LOD2'] / tri['LOD0'], 3)},
    'materials': [{'name': ship[s].name, 'slot': s, 'textures': {k: f'Textures/{v.name}' for k, v in files[s].items()},
                   'texture_size': SIZE, 'visible_texel_density_px_per_m': TEXEL[s], 'orm': 'R = ambient occlusion, G = roughness, B = metallic (linear)',
                   'normal': 'OpenGL tangent space'} for s in SLOTS],
    'collision': coll_info, 'has_collision': bool(colls),
    'interfaces': SPEC.get('interfaces'), 'scene_slot': SPEC.get('slot'),
    'files': {'fbx': FBX.name, 'glb': GLB.name, 'blend': f'art/source/{KIT}/blend/{BLEND.name}'},
    'reference': SPEC.get('reference'), 'notes': SPEC.get('notes', []),
    'bake': {'device': device, 'fast_lookdev': FAST},
}
(EXP / 'model_info.json').write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')
checks = {
    'origin_footprint_centre_xy': abs((lo.x + hi.x) / 2) < .06 and abs((lo.y + hi.y) / 2) < .06 if SPEC['kind'] == 'scene' else True,
    'bottom_at_design_embed': abs(lo.z + SPEC.get('embed', 0.0)) < .03,
    'fbx_has_LOD0_LOD1_LOD2': all(f'{AID}_LOD{k}' in fbx_check['objects'] for k in (0, 1, 2)),
    'fbx_has_collision': (not S['coll']) or any('_Collision' in n for n in fbx_check['objects']),
    'fbx_lod0_size_matches_blender': all(abs(a - b) < .005 for a, b in zip(sorted(fbx_check['lod0_size_m']), sorted(size))),
    'lod1_45_55_percent': .45 <= info['lod_ratio']['LOD1'] <= .55,
    'lod2_12_18_percent': .12 <= info['lod_ratio']['LOD2'] <= .18,
    'texel_density_at_least_min_px_m': min(TEXEL.values()) >= MIN_TEXEL or FAST,
    'glb_reimports': any(n.startswith(f'{AID}_LOD0') for n in glb_check['meshes']),
}
if SPEC.get('limit'):
    L = SPEC['limit']; checks['within_slot_limit_w_d_h'] = size.x <= L[0] + 1e-3 and size.y <= L[1] + 1e-3 and hi.z <= L[2] + 1e-3
checks.update(SPEC.get('extra_checks', lambda **k: {})(lods=lods, colls=colls, S=S) or {})
val = {'asset': AID, 'version': VER, 'checks': checks, 'passed': all(checks.values()), 'fbx_reimport': fbx_check,
       'glb_reimport': glb_check, 'sha256': {FBX.name: sha(FBX), GLB.name: sha(GLB)},
       'not_checked': ['Unity import and LODGroup distances', 'in-game lighting', 'mobile performance']}
(EXP / 'validation.json').write_text(json.dumps(val, ensure_ascii=False, indent=2), encoding='utf-8')
BLEND.parent.mkdir(parents=True, exist_ok=True)
for o in parts: o.hide_set(False)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True)
log('DONE', json.dumps({'tris': tri, 'size': [round(v, 3) for v in size], 'passed': val['passed'],
                        'failed': [k for k, v in checks.items() if not v]}))
