"""Normalise -> join per group -> UV atlas -> bake -> LOD1/LOD2 -> baked materials -> FBX -> renders."""
import bpy, bmesh, math, json, hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
from wr_core import S, write_grain_attributes
from wr_mats import MAT_INFO, set_emission

VIEWS = [('01_front', (0, -1, 0)), ('02_right', (1, 0, 0)), ('03_rear', (0, 1, 0)), ('04_left', (-1, 0, 0)),
         ('05_front_right', (1, -1, .45)), ('06_rear_right', (1, 1, .45)), ('07_rear_left', (-1, 1, .45)),
         ('08_front_left', (-1, -1, .45)), ('09_top', (0, 0, 1)), ('10_high_front', (0, -1, 1))]
EXPOSURE = -1.3   # same light rig as SectFacilities05, exposure lowered so material detail is not clipped
LOD_RULES = {0: (99, 1.0), 1: (2, .45), 2: (1, .2)}     # (drop parts with detail >= n, decimate ratio)

def eval_bounds(objs):
    dg = bpy.context.evaluated_depsgraph_get(); pts = []
    for o in objs:
        e = o.evaluated_get(dg)
        if o.type != 'MESH': continue
        me = e.to_mesh(); mw = o.matrix_world
        pts += [mw @ v.co for v in me.vertices]; e.to_mesh_clear()
    lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
    return lo, hi

def normalise():
    """Move parts and sockets so the model sits on its bottom-centre origin."""
    bpy.context.view_layer.update()
    lo, hi = eval_bounds(S['parts'])
    shift = Matrix.Translation(-Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z)))
    for o in S['parts'] + list(S['sockets'].values()) + list(S['cut'].objects):
        if o.parent is None: o.matrix_world = shift @ o.matrix_world
    bpy.context.view_layer.update()
    write_grain_attributes()

def join_groups():
    """Evaluate every part (modifiers applied) and join per export group, at identity transform."""
    scene = bpy.context.scene
    S['lodcol'] = bpy.data.collections.new('02_Export_LODs'); scene.collection.children.link(S['lodcol'])
    dg = bpy.context.evaluated_depsgraph_get()
    groups = {}
    for o in S['parts']:
        if o.type != 'MESH': continue
        groups.setdefault(o['group'], []).append(o)
    out = {}
    for gname, parts in groups.items():
        temps = []
        for o in parts:
            e = o.evaluated_get(dg)
            me = bpy.data.meshes.new_from_object(e, preserve_all_data_layers=True, depsgraph=dg)
            if not me.uv_layers: me.uv_layers.new(name='UVMap')
            while len(me.uv_layers) > 1: me.uv_layers.remove(me.uv_layers[-1])
            me.uv_layers[0].name = 'UVMap'
            at = me.attributes.new('part_detail', 'INT', 'FACE'); at.data.foreach_set('value', [int(o['detail'])] * len(me.polygons))
            t = bpy.data.objects.new(o.name + '_eval', me); S['lodcol'].objects.link(t); t.matrix_world = o.matrix_world.copy()
            temps.append(t)
        bpy.ops.object.select_all(action='DESELECT')
        for t in temps: t.select_set(True)
        bpy.context.view_layer.objects.active = temps[0]
        bpy.ops.object.join()
        j = bpy.context.view_layer.objects.active
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        base = S['asset'] if gname == 'Main' else f"{S['asset']}_{gname}"
        j.name = base + '_LOD0'; j.data.name = j.name
        # merge duplicate material slots
        _dedupe_slots(j.data)
        out[gname] = j
    S['lod0'] = out
    return out

def _dedupe_slots(me):
    mats = list(me.materials); uniq = []
    for m in mats:
        if m not in uniq: uniq.append(m)
    remap = [uniq.index(m) for m in mats]
    idx = np.zeros(len(me.polygons), dtype=np.int32); me.polygons.foreach_get('material_index', idx)
    idx = np.array([remap[i] if i < len(remap) else 0 for i in idx], dtype=np.int32)
    me.materials.clear()
    for m in uniq: me.materials.append(m)
    me.polygons.foreach_set('material_index', idx); me.update()

def uv_atlas():
    objs = list(S['lod0'].values())
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.context.scene.tool_settings.use_uv_select_sync = True
    keep = {}
    for o in objs:
        me = o.data
        own = [(MAT_INFO.get(m.name) or MAT_INFO.get(m.name.rsplit('.', 1)[0]) or {}).get('own_uv', False) for m in me.materials]
        for p in me.polygons: p.select = not own[p.material_index]
        # own-UV faces (painting, journal page) keep their authored UVs: pack/average can still move them
        uvl = me.uv_layers.active
        keep[o.name] = {li: uvl.data[li].uv.copy() for p in me.polygons if own[p.material_index] for li in p.loop_indices}
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(58), island_margin=.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(rotate=True, margin=.0025)
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in objs:
        uvl = o.data.uv_layers.active
        for li, uv in keep[o.name].items(): uvl.data[li].uv = uv

def _img(name, size, color=True, alpha=False):
    im = bpy.data.images.new(name, size, size, alpha=alpha, float_buffer=not color)
    im.colorspace_settings.name = 'sRGB' if color else 'Non-Color'
    return im

def bake(tex_dir, size):
    """Bake colour/roughness/metal/emission through an Emission shader, then a tangent normal map."""
    scene = bpy.context.scene; scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'
    scene.render.bake.margin = 12; scene.render.bake.use_clear = True
    objs = list(S['lod0'].values())
    mats = {m for o in objs for m in o.data.materials if not MAT_INFO[m.name]['own_uv']}
    own = {m for o in objs for m in o.data.materials if MAT_INFO[m.name]['own_uv']}
    a = S['asset']; imgs = {}
    passes = [('BaseColor', 'OUT_COLOR', True, 16), ('Roughness', 'OUT_ROUGH', False, 4),
              ('Metallic', 'OUT_METAL', False, 4), ('Emission', 'OUT_EMIT', True, 4)]
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    dummy = _img('Bake_Dummy', 16)
    for label, node_name, color, samples in passes + [('Normal', None, False, 4)]:
        img = _img(f'{a}_{label}', size, color); imgs[label] = img
        scene.cycles.samples = samples
        for m in mats | own:
            nt = m.node_tree; tn = nt.nodes.new('ShaderNodeTexImage'); tn.name = 'BAKE_TARGET'
            tn.image = img if m in mats else dummy
            nt.nodes.active = tn
            if node_name:
                em = nt.nodes.new('ShaderNodeEmission'); em.name = 'BAKE_EMIT'; em.inputs['Strength'].default_value = 1
                src = nt.nodes[node_name].outputs[0]
                if src.type == 'VALUE':
                    cmb = nt.nodes.new('ShaderNodeCombineColor'); cmb.name = 'BAKE_CMB'
                    for i in range(3): nt.links.new(src, cmb.inputs[i])
                    src = cmb.outputs[0]
                nt.links.new(src, em.inputs['Color']); nt.links.new(em.outputs[0], nt.nodes['OUTPUT'].inputs['Surface'])
        if node_name: bpy.ops.object.bake(type='EMIT')
        else: bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT')
        for m in mats | own:
            nt = m.node_tree
            for nm in ('BAKE_TARGET', 'BAKE_EMIT', 'BAKE_CMB'):
                if nm in nt.nodes: nt.nodes.remove(nt.nodes[nm])
            bs = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]
            nt.links.new(bs.outputs[0], nt.nodes['OUTPUT'].inputs['Surface'])
        print('BAKED', a, label, flush=True)
    tex_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    for label in ('BaseColor', 'Normal', 'Roughness', 'Metallic', 'Emission'):
        im = imgs[label]; im.filepath_raw = str(tex_dir / f'{a}_{label}.png'); im.file_format = 'PNG'
        im.save(); files[label] = im.filepath_raw
    # Unity URP packed map: R metallic, A smoothness
    px = lambda im: np.array(im.pixels[:], dtype=np.float32).reshape(size, size, 4)
    met = px(imgs['Metallic'])[..., 0]; rough = px(imgs['Roughness'])[..., 0]
    ms = np.zeros((size, size, 4), np.float32); ms[..., 0] = met; ms[..., 1] = met; ms[..., 2] = met; ms[..., 3] = 1 - rough
    msi = _img(f'{a}_MetallicSmoothness', size, False, True); msi.pixels.foreach_set(ms.ravel())
    msi.filepath_raw = str(tex_dir / f'{a}_MetallicSmoothness.png'); msi.file_format = 'PNG'; msi.save()
    files['MetallicSmoothness'] = msi.filepath_raw
    emit_used = float(px(imgs['Emission'])[..., :3].max()) > .01
    if not emit_used:
        Path(files['Emission']).unlink(); del files['Emission']
    S['tex'] = {k: Path(v) for k, v in files.items()}
    return S['tex']

def make_lods():
    lods = {0: dict(S['lod0'])}
    for lv in (1, 2):
        lods[lv] = {}
        drop, ratio = LOD_RULES[lv]
        for gname, src in S['lod0'].items():
            o = src.copy(); o.data = src.data.copy(); S['lodcol'].objects.link(o)
            o.name = src.name.replace('_LOD0', f'_LOD{lv}'); o.data.name = o.name
            bm = bmesh.new(); bm.from_mesh(o.data)
            lay = bm.faces.layers.int.get('part_detail')
            kill = [f for f in bm.faces if f[lay] >= drop]
            bmesh.ops.delete(bm, geom=kill, context='FACES')
            bm.to_mesh(o.data); bm.free()
            if len(o.data.polygons) == 0:
                bpy.data.objects.remove(o); continue
            m = o.modifiers.new('LOD_decimate', 'DECIMATE'); m.ratio = ratio; m.use_collapse_triangulate = True
            bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
            bpy.ops.object.modifier_apply(modifier=m.name)
            with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o], selected_editable_objects=[o]):
                try: bpy.ops.mesh.customdata_custom_splitnormals_clear()
                except Exception: pass
                bpy.ops.object.shade_smooth_by_angle(angle=math.radians(38))
            lods[lv][gname] = o
    S['lods'] = lods
    return lods

def export_materials():
    """Swap procedural materials on the LOD meshes for baked texture materials (what ships)."""
    a = S['asset']; tex = S['tex']
    def load(p, color):
        im = bpy.data.images.load(str(p), check_existing=True); im.colorspace_settings.name = 'sRGB' if color else 'Non-Color'; return im
    base = load(tex['BaseColor'], True); nrm = load(tex['Normal'], False); rgh = load(tex['Roughness'], False)
    met = load(tex['Metallic'], False); emi = load(tex['Emission'], True) if 'Emission' in tex else None
    cache = {}
    def baked(slot, emissive):
        key = slot
        if key in cache: return cache[key]
        m = bpy.data.materials.new(f'M_{a}_{slot}'); m.use_nodes = True; nt = m.node_tree
        bs = nt.nodes['Principled BSDF']
        def t(im, sock, nonc=False):
            n = nt.nodes.new('ShaderNodeTexImage'); n.image = im; nt.links.new(n.outputs['Color'], sock); return n
        t(base, bs.inputs['Base Color']); t(rgh, bs.inputs['Roughness']); t(met, bs.inputs['Metallic'])
        nm = nt.nodes.new('ShaderNodeNormalMap'); t(nrm, nm.inputs['Color']); nt.links.new(nm.outputs[0], bs.inputs['Normal'])
        bs.inputs['Specular IOR Level'].default_value = .35
        if emissive and emi is not None:
            t(emi, bs.inputs['Emission Color'])
            v = nt.nodes.new('ShaderNodeValue'); v.name = 'EMIT_STRENGTH'; v.outputs[0].default_value = 0
            nt.links.new(v.outputs[0], bs.inputs['Emission Strength'])
        m['unity'] = {'shader': 'Universal Render Pipeline/Lit', 'emissive_slot': bool(emissive)}
        cache[key] = m; return m
    for lv, groups in S['lods'].items():
        for o in groups.values():
            me = o.data; newmats = []
            for m in me.materials:
                info = MAT_INFO.get(m.name) or dict(m['_ti_info'])
                if info['own_uv']:
                    newmats.append(m)            # keeps its own image texture; renamed once, shared by all LODs
                    if not m.name.startswith('M_'):
                        m['_ti_info'] = info; m.name = f"M_{a}_{info['slot']}"
                else:
                    newmats.append(baked(info['slot'], info['slot'] != 'Main'))
            idx = np.zeros(len(me.polygons), dtype=np.int32); me.polygons.foreach_get('material_index', idx)
            me.materials.clear()                 # clear() resets polygon material indices
            for m in newmats: me.materials.append(m)
            me.polygons.foreach_set('material_index', idx); me.update()
            _dedupe_slots(me)
    return cache

def tri_count(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)

def export_fbx(path):
    a = S['asset']
    root = bpy.data.objects.new(a, None); S['lodcol'].objects.link(root); S['root'] = root
    for groups in S['lods'].values():
        for o in groups.values(): o.parent = root
    for e in S['sockets'].values():
        mw = e.matrix_world.copy()
        for c in list(e.users_collection): c.objects.unlink(e)
        S['lodcol'].objects.link(e); e.parent = root; e.matrix_world = mw
    bpy.ops.object.select_all(action='DESELECT')
    root.select_set(True)
    for groups in S['lods'].values():
        for o in groups.values(): o.select_set(True)
    for e in S['sockets'].values(): e.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={'MESH', 'EMPTY'},
                             apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL', bake_space_transform=True,
                             axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE', use_mesh_modifiers=True,
                             add_leaf_bones=False, bake_anim=False, path_mode='STRIP', embed_textures=False)

def fbx_roundtrip(path):
    """Re-import the FBX into an empty scene and report object names and LOD0 dimensions."""
    before = set(bpy.data.objects)
    tmp = bpy.data.collections.new('99_FBX_Check'); bpy.context.scene.collection.children.link(tmp)
    lc = bpy.context.view_layer.layer_collection.children[tmp.name]; bpy.context.view_layer.active_layer_collection = lc
    bpy.ops.import_scene.fbx(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH' and o.name.split('.')[0].endswith('_LOD0')]
    bpy.context.view_layer.update()
    lo, hi = eval_bounds(meshes)
    rep = {'objects': sorted(o.name for o in new), 'lod0_dimensions_m': [round(v, 4) for v in hi - lo],
           'sockets': {o.name: [round(v, 4) for v in o.matrix_world.translation] for o in new if o.name.startswith('SOCKET_')}}
    for o in new: bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(tmp)
    bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    return rep

# ---------------------------------------------------------------- studio renders
def studio(extent_objs, samples=48):
    scene = bpy.context.scene
    st = bpy.data.collections.get('90_Studio_Not_Exported')
    if st is None:
        st = bpy.data.collections.new('90_Studio_Not_Exported'); scene.collection.children.link(st)
    for o in list(st.objects): bpy.data.objects.remove(o, do_unlink=True)
    lo, hi = eval_bounds(extent_objs); centre = (lo + hi) / 2; ext = hi - lo
    cam = bpy.data.objects.new('Reference_Camera', bpy.data.cameras.new('Reference_Camera')); st.objects.link(cam)
    scene.camera = cam; cam.data.type = 'ORTHO'; cam.data.clip_start = .01; cam.data.clip_end = 100
    cam.data.ortho_scale = max(ext.length * 1.08, .3)
    ls = max(max(ext) * .65, .25)
    for name, d, p in [('Key', (-.8, -1.1, 1.5), 1100), ('Fill', (1.2, -.4, .9), 650), ('Rim', (.2, 1.1, 1.3), 950)]:
        L = bpy.data.lights.new(name, 'AREA'); L.energy = p * ls * ls / 7; L.shape = 'DISK'; L.size = ls
        o = bpy.data.objects.new(name, L); st.objects.link(o); o.location = centre + Vector(d) * ls
        o.rotation_euler = (centre - o.location).to_track_quat('-Z', 'Y').to_euler()
    scene.world = bpy.data.worlds.get('Neutral_Studio') or bpy.data.worlds.new('Neutral_Studio'); scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes['Background']; bg.inputs[0].default_value = (.19, .21, .22, 1); bg.inputs[1].default_value = .65
    scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'; scene.cycles.samples = samples; scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 1024; scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'; scene.view_settings.view_transform = 'AgX'
    scene.view_settings.exposure = EXPOSURE
    scene.render.film_transparent = False
    return cam, centre, ext

def show_only(objs):
    keep = set(objs)
    for o in bpy.context.scene.objects:
        if o.type == 'MESH': o.hide_render = o not in keep

def ten_views(objs, out_dir, source_rel):
    from bpy_extras.object_utils import world_to_camera_view
    scene = bpy.context.scene; show_only(objs)
    cam, centre, ext = studio(objs)
    out_dir.mkdir(parents=True, exist_ok=True); records = []
    for name, d in VIEWS:
        cam.location = centre + Vector(d).normalized() * cam.data.ortho_scale * 2.3
        cam.rotation_euler = (centre - cam.location).to_track_quat('-Z', 'Y').to_euler(); bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        proj = [world_to_camera_view(scene, cam, o.matrix_world @ Vector(p)) for o in objs for p in o.evaluated_get(dg).bound_box]
        ok = all(.005 < p.x < .995 and .005 < p.y < .995 and p.z > 0 for p in proj)
        assert ok, (S['asset'], name, 'cropped')
        scene.render.filepath = str(out_dir / f'{name}.png'); bpy.ops.render.render(write_still=True)
        records.append({'file': f'{name}.png', 'direction': list(d), 'camera_location': [round(v, 4) for v in cam.location],
                        'projection': 'orthographic', 'framing_checked': True})
        print('VIEW_COMPLETE', S['asset'], name, flush=True)
    (out_dir / 'views.json').write_text(json.dumps({'asset': S['asset'], 'source': source_rel, 'same_geometry': True,
                                                     'render_of': 'exported LOD0 with baked textures', 'views': records}, indent=2))
    return records

def persp_shot(objs, path, direction=(1, -1.25, .55), samples=64, lens=55, margin=1.12):
    scene = bpy.context.scene; show_only(objs)
    cam, centre, ext = studio(objs, samples)
    cam.data.type = 'PERSP'; cam.data.lens = lens
    dist = ext.length * margin / (2 * math.tan(cam.data.angle / 2))
    cam.location = centre + Vector(direction).normalized() * dist
    cam.rotation_euler = (centre - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(path); bpy.ops.render.render(write_still=True)

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
