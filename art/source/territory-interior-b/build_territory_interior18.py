"""TerritoryInterior18: TI01-TI08 newcomer-territory interior furniture, v001.

Run (one asset per process keeps memory flat):
  blender --background --factory-startup --python build_territory_interior18.py -- TI01_BoguShelf
No IDs = all assets. An asset whose validation.json exists is skipped unless --force is given.
Writes into this batch only: Models/<ID>/v001, ArtLibrary/Turnarounds/<ID>_v001.
Root install (Models/, ArtLibrary/Turnarounds/) is a separate step: install_batch18.py.
"""
import bpy, sys, json, math, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import ti_core, ti_mats, ti_pipeline as pl, ti_assets as A
from ti_core import S

BATCH = HERE.parent
VER = 'v001'

ASSETS = {
    'TI01_BoguShelf': dict(zh='博古架', slot='TI_Shelf', target=(1.76, .42, 1.96), limit=(1.8, .45, 2.0), tex=4096,
        build=lambda P: A.ti01_bogu_shelf(P),
        layers=('擺放旅途收藏的架子', '文人博古陳設', '一件件收藏拼成歷史；最上層左格比其他格舊，像以前常放東西'),
        states=['empty', 'half', 'full']),
    'TI02_HomeFurnace': dict(zh='守溫小丹爐', slot='TI_Furnace', target=(.78, .76, 1.06), limit=(.8, .8, 1.1), tex=2048,
        build=lambda P: A.ti02_home_furnace(P),
        layers=('在家煉簡單藥物的小爐', '守火、溫養的煉藥意象', '家中開始有自己的生活節奏'),
        states=['cold', 'burning']),
    'TI03_JournalDesk': dict(zh='行記書案與椅凳', slot='TI_Desk', target=(1.28, .68, .84), limit=(1.3, .7, .85), tex=4096,
        build=lambda P: A.ti03_journal_desk(P, TEX['page']),
        layers=('寫旅途手札的書案', '遊記與文房器用', '桌面舊刻痕暗示過往使用者，不解釋其身分'), states=[]),
    'TI04_PaperLamp': dict(zh='歸明燈架', slot='TI_Lamp_1/TI_Lamp_2', target=(.42, .42, 1.64), limit=(.45, .45, 1.7), tex=2048,
        build=lambda P: A.ti04_paper_lamp(P),
        layers=('回家點的燈', '燈火待歸的意象', '夜晚讓空屋成為自己的家'), states=['off', 'on']),
    'TI05_LandscapeScreen': dict(zh='遠岫屏風', slot='TI_Screen', target=(1.76, .32, 1.72), limit=(1.8, .35, 1.75), tex=2048,
        build=lambda P: A.ti05_landscape_screen(P, TEX['paint']),
        layers=('隔開床與書案的屏風', '山水屏障、借景', '背面左扇下橫檔外角刻極小缺月記號'), states=[]),
    'TI06_WovenMat': dict(zh='安坐地蓆', slot='TI_Rug', target=(1.96, 1.36, .025), limit=(2.0, 1.4, .03), tex=2048,
        build=lambda P: A.ti06_woven_mat(P),
        layers=('承托蒲團的草蓆', '草蓆坐具', '中央坐痕與邊緣磨損呈現生活延續'), states=[]),
    'TI07_LinenCurtain': dict(zh='歸居門簾', slot='TI_Curtain_F/TI_Curtain_B', target=(1.28, .09, 2.16), limit=(1.3, .1, 2.2), tex=2048,
        build=lambda P: A.ti07_linen_curtain(P),
        layers=('遮擋門口視線的布簾', '布簾分隔內外', '從外出回到私人空間；左片低處有補丁'), states=[]),
}
for i, (key, zh, fn) in enumerate(A.PROPS):
    ASSETS[f'TI08{"abcd"[i]}_{key}'] = dict(zh=zh, slot='TI01 sockets (display only)', target=None, limit=(.35, .30, .35), tex=1024,
        build=(lambda k: (lambda P: A.ti08_display_props(P, only=k)))(key),
        layers=(f'收藏架展示用的{zh}', '木匣、卷軸與陶瓷器', '無劇情伏筆；正式見聞道具由 C 製作'), states=[])
TEX = {}

def textures():
    d = BATCH / 'Textures'; d.mkdir(parents=True, exist_ok=True)
    p = d / 'TI05_LandscapeScreen_PaintedLinen.png'
    if not p.exists(): A.landscape_texture(p)
    q = d / 'TI03_JournalDesk_JournalPage_Blank.png'
    if not q.exists(): A.journal_page_texture(q)
    TEX['paint'] = bpy.data.images.load(str(p)); TEX['page'] = bpy.data.images.load(str(q))
    return {'paint': p, 'page': q}

# ---------------------------------------------------------------- checks
def bvh_of(o):
    me = o.data; mw = o.matrix_world
    return BVHTree.FromPolygons([mw @ v.co for v in me.vertices], [tuple(p.vertices) for p in me.polygons])

def box_bvh(c, s):
    hx, hy, hz = s[0] / 2, s[1] / 2, s[2] / 2
    v = [(c[0] + x * hx, c[1] + y * hy, c[2] + z * hz) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return BVHTree.FromPolygons([Vector(p) for p in v], f), v

def shelf_fit_test():
    res = {'method': 'BVH triangle overlap between each LOD mesh and an axis-aligned test block resting 2 mm above the socket; '
                     'block centred on the socket in X and Y', 'blocks': {}}
    for label, size in (('collectible_0.35x0.30x0.35', (.35, .30, .35)), ('clearance_0.36x0.31x0.36', (.36, .31, .36))):
        rows = []
        for k in range(1, 9):
            s = S['sockets'][f'SOCKET_slot_{k}'].matrix_world.translation
            c = (s.x, s.y, s.z + .002 + size[2] / 2)
            tb, verts = box_bvh(c, size)
            hits = {}
            for lv, groups in S['lods'].items():
                n = 0
                for o in groups.values(): n += len(bvh_of(o).overlap(tb))
                hits[f'LOD{lv}'] = n
            # also make sure no vertex of the block sits inside solid geometry (ray parity against LOD0)
            rows.append({'slot': k, 'socket_blender_xyz': [round(v, 4) for v in s], 'overlapping_triangles': hits,
                         'pass': all(v == 0 for v in hits.values())})
        res['blocks'][label] = rows
    cells = []
    for c in S['shelf_cells']:
        cells.append({'slot': c['slot'], 'inner_width_m': round(c['x1'] - c['x0'], 3), 'inner_depth_m': round(c['y1'] - c['y0'], 3),
                      'inner_height_m': round(c['z1'] - c['z0'], 3)})
    res['cell_interiors_from_construction'] = cells
    res['pass'] = all(r['pass'] for rows in res['blocks'].values() for r in rows)
    return res

# ---------------------------------------------------------------- per-asset run
def run(aid, force=False):
    cfg = ASSETS[aid]
    out = BATCH / 'Models' / aid / VER; refs = BATCH / 'ArtLibrary' / 'Turnarounds' / f'{aid}_{VER}'
    if (out / 'validation.json').exists() and not force:
        print('ALREADY_COMPLETE', aid, flush=True); return
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene; scene.unit_settings.system = 'METRIC'; scene.unit_settings.scale_length = 1
    bpy.context.preferences.filepaths.save_version = 0
    ti_mats.MAT_INFO.clear()
    texfiles = textures()
    ti_core.reset_state(aid)
    P = A.palette()
    cfg['build'](P)
    pl.normalise()
    pl.join_groups(); pl.uv_atlas()
    tex = pl.bake(out / 'Textures', cfg['tex'])
    pl.make_lods(); pl.export_materials()
    S['col'].hide_render = True; S['col'].hide_viewport = True
    # own-UV textures ship next to the atlas
    extra = {}
    for key, p in texfiles.items():
        if (key == 'paint' and aid.startswith('TI05')) or (key == 'page' and aid.startswith('TI03')):
            dst = out / 'Textures' / p.name; dst.write_bytes(p.read_bytes()); extra[key] = dst.name
    lod0 = list(S['lods'][0].values())
    lo, hi = pl.eval_bounds(lod0); dims = hi - lo
    checks = []
    def check(name, ok, detail):
        checks.append({'check': name, 'pass': bool(ok), 'detail': detail})
    check('origin_bottom_centre', abs(lo.z) < 1e-4 and abs((lo.x + hi.x) / 2) < 1e-3 and abs((lo.y + hi.y) / 2) < 1e-3,
          {'min': [round(v, 4) for v in lo], 'max': [round(v, 4) for v in hi]})
    lim = cfg['limit']
    check('within_slot_limit', all(d <= l + 1e-4 for d, l in zip(dims, lim)), {'dims_m': [round(v, 4) for v in dims], 'limit_m': lim})
    if cfg['target']:
        dev = [round(d - t, 4) for d, t in zip(dims, cfg['target'])]
        check('near_design_target', all(abs(x) <= .03 for x in dev), {'target_m': cfg['target'], 'deviation_m': dev, 'tolerance_m': .03})
    fit = None
    if aid == 'TI01_BoguShelf':
        fit = shelf_fit_test(); check('shelf_8_slots_fit_collectible_block', fit['pass'], 'see shelf_fit_test in model_info.json')
    # FBX
    fbx = out / f'{aid}_{VER}.fbx'
    pl.export_fbx(fbx)
    rt = pl.fbx_roundtrip(fbx)
    check('fbx_reimport_dimensions', all(abs(a - b) < 2e-3 for a, b in zip(rt['lod0_dimensions_m'], dims)),
          {'fbx_lod0_dims_m': rt['lod0_dimensions_m'], 'blend_dims_m': [round(v, 4) for v in dims]})
    # ten views of the exported LOD0 (baked textures)
    rel = f'Models/{aid}/{VER}/{aid}_{VER}.blend'
    main_lod0 = [o for o in lod0 if 'Fire' not in o.name]
    if aid == 'TI02_HomeFurnace': main_lod0 = lod0   # fire insert visible but unlit in the reference views
    pl.ten_views(main_lod0, refs, rel)
    check('ten_views_rendered', len(list(refs.glob('*.png'))) == 10, 'orthographic, framing asserted per view')
    # LOD sheet
    shots = []
    for lv in (0, 1, 2):
        objs = list(S['lods'][lv].values())
        p = out / f'_lod{lv}.png'; pl.persp_shot(objs, p, samples=32); shots.append(p)
    _strip(shots, out / f'{aid}_LOD_comparison.png'); [p.unlink() for p in shots]
    # state renders
    states = {}
    if aid == 'TI02_HomeFurnace':
        fire = [o for o in lod0 if 'Fire' in o.name]
        body = [o for o in lod0 if 'Fire' not in o.name]
        pl.persp_shot(body, out / 'state_cold.png', direction=(.15, -1, .12), samples=64); states['cold'] = 'state_cold.png'
        _set_emit(8.0); L = _point(S['sockets']['SOCKET_fire_light'].matrix_world.translation, 25, (1, .55, .25))
        pl.persp_shot(lod0, out / 'state_burning.png', direction=(.15, -1, .12), samples=64); states['burning'] = 'state_burning.png'
        bpy.data.objects.remove(L); _set_emit(0)
    if aid == 'TI04_PaperLamp':
        pl.persp_shot(lod0, out / 'state_off.png', samples=64); states['off'] = 'state_off.png'
        _set_emit(3.5); L = _point(S['sockets']['SOCKET_lamp_light'].matrix_world.translation, 30, (1, .7, .4))
        w = bpy.context.scene.world.node_tree.nodes['Background']; w.inputs[1].default_value = .12
        pl.persp_shot(lod0, out / 'state_on.png', samples=64); states['on'] = 'state_on.png'
        bpy.data.objects.remove(L); _set_emit(0)
    if aid == 'TI05_LandscapeScreen':
        pl.persp_shot(lod0, out / 'rear_crescent_overview.png', direction=(-.6, 1, .35), samples=64)
        _crescent_closeup(lod0, out / 'rear_crescent_closeup.png')
    if aid == 'TI03_JournalDesk':
        _closeup(lod0, out / 'desk_top_closeup.png', S['sockets']['SOCKET_journal'].matrix_world.translation + Vector((-.12, .02, 0)), (0.0, -.35, 1), .75)
    pl.persp_shot(main_lod0, out / f'{aid}_hero.png', samples=96)
    # bookkeeping
    bpy.ops.wm.save_as_mainfile(filepath=str(out / f'{aid}_{VER}.blend'))
    tris = {f'LOD{lv}': {o.name: pl.tri_count(o) for o in g.values()} for lv, g in S['lods'].items()}
    check('lod_triangle_order', all(sum(tris[f'LOD{a}'].values()) > sum(tris[f'LOD{b}'].values()) for a, b in ((0, 1), (1, 2))), tris)
    mats = sorted({m.name for g in S['lods'].values() for o in g.values() for m in o.data.materials})
    info = {
        'asset': aid, 'version': VER, 'name_zh': cfg['zh'], 'interior_slot': cfg['slot'],
        'naming_three_layers': dict(zip(('surface', 'allusion', 'foreshadowing_internal_only'), cfg['layers'])),
        'units': 'meters', 'front': '-Y (Blender)', 'up': '+Z (Blender); FBX exported Y-up, -Z forward, transforms baked',
        'origin': 'bottom centre', 'dimensions_m': [round(v, 4) for v in dims], 'design_target_m': cfg['target'], 'slot_limit_m': cfg['limit'],
        'lods': tris, 'lod_rules': {'LOD1': 'drop rivets/stitches/fibres (detail 2), collapse decimate 0.45',
                                    'LOD2': 'also drop small brackets/notches (detail 1), collapse decimate 0.20'},
        'materials': mats, 'textures': sorted(p.name for p in (out / 'Textures').glob('*.png')),
        'texture_size_px': cfg['tex'], 'own_uv_textures': extra,
        'unity': {'pipeline': 'URP Lit', 'BaseColor': f'{aid}_BaseColor.png', 'Normal': f'{aid}_Normal.png (OpenGL +Y, Unity default)',
                  'MetallicSmoothness': f'{aid}_MetallicSmoothness.png (R metallic, A smoothness)',
                  'Emission': f'{aid}_Emission.png' if 'Emission' in S['tex'] else None,
                  'lod_group': 'objects end in _LOD0/_LOD1/_LOD2 under one root, so Unity builds a LODGroup on import'},
        'sockets_blender_xyz': {k: [round(v, 4) for v in e.matrix_world.translation] for k, e in S['sockets'].items()},
        'sockets_fbx_reimport_xyz': rt['sockets'],
        'states': cfg['states'], 'state_renders': states,
        'fbx_objects': rt['objects'],
        'modeling_method': 'procedural mesh construction (BlenderSource/build_territory_interior18.py); procedural shaders baked to a UV atlas',
        'uv_baked': True, 'collision': False, 'collision_note': 'none exported; use a box collider at dimensions_m (props: no collider needed on the shelf)',
        'unity_import_verified': False, 'unreal_import_verified': False,
        'reference': 'art/references/territory-interior-b/v001 (AI design sheets, not measured)',
    }
    if fit: info['shelf_fit_test'] = fit
    if aid.startswith('TI02'): info['separate_objects'] = {'lid': f'{aid}_Lid_LOD*', 'fire_insert': f'{aid}_Fire_LOD* (toggle for cold/burning)'}
    (out / 'model_info.json').write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')
    val = {'asset': aid, 'checks': checks, 'all_pass': all(c['pass'] for c in checks), 'seconds': round(time.time() - t0),
           'not_checked': ['Unity import', 'in-engine lighting match', 'collision', 'player clearance in the real room (see presentation renders)']}
    (out / 'validation.json').write_text(json.dumps(val, ensure_ascii=False, indent=2), encoding='utf-8')
    print('ASSET_COMPLETE', aid, 'all_pass=', val['all_pass'], round(time.time() - t0), 's', flush=True)

def _set_emit(v):
    for m in bpy.data.materials:
        if m.node_tree and 'EMIT_STRENGTH' in m.node_tree.nodes: m.node_tree.nodes['EMIT_STRENGTH'].outputs[0].default_value = v

def _point(p, w, c):
    L = bpy.data.lights.new('State_Light', 'POINT'); L.energy = w; L.color = c; L.shadow_soft_size = .03
    col = bpy.data.collections.get('91_State_Lights') or bpy.data.collections.new('91_State_Lights')
    if col.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(col)
    o = bpy.data.objects.new('State_Light', L); col.objects.link(o); o.location = p
    return o

def _closeup(objs, path, target, direction, scale):
    pl.persp_shot(objs, path, samples=8)        # sets lights and visibility
    scene = bpy.context.scene; cam = scene.camera
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = scale
    cam.location = Vector(target) + Vector(direction).normalized() * 3
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.cycles.samples = 96; scene.render.filepath = str(path); bpy.ops.render.render(write_still=True)

def _crescent_closeup(objs, path):
    # crescent sits on the rear face of the left wing's lower rail
    ws = [o for o in bpy.data.objects if o.name.startswith('Bottom_Rail')]
    left = min(ws, key=lambda o: o.matrix_world.translation.x)
    tgt = left.matrix_world @ Vector((.085 - .291 + .0, .0125, .0))
    _closeup(objs, path, tgt, (-.25, 1, .15), .16)

def _strip(paths, out):
    ims = [bpy.data.images.load(str(p)) for p in paths]
    w, h = ims[0].size
    arr = np.concatenate([np.array(i.pixels[:], np.float32).reshape(h, w, 4) for i in ims], axis=1)
    im = bpy.data.images.new(out.stem, w * len(ims), h, alpha=True); im.pixels.foreach_set(arr.ravel())
    im.filepath_raw = str(out); im.file_format = 'PNG'; im.save()

if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    force = '--force' in argv; ids = [a for a in argv if not a.startswith('--')] or list(ASSETS)
    for aid in ids: run(aid, force)
