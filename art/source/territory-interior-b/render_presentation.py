"""Presentation renders and layout checks for TerritoryInterior18 (run after all assets are built).

  blender --background --factory-startup --python render_presentation.py

Outputs to Presentation/:
  shelf_empty.png / shelf_half.png / shelf_full.png   TI01 with TI08 props placed on its sockets
  lineup_with_dondon_furniture.png                     TI01-TI07 beside DiscipleBed / StorageChest / MeditationCushion
  room_front_door_day.png / room_front_door_night.png  1.7 m eye height from the front door
  room_top_slots.png                                    orthographic top view with slot IDs
  layout_check.json                                     footprints, door clearance, approach zones
The bed/chest/cushion are rebuilt here from their original build scripts (SectFacilities05 / HerbalExpansion01)
because their .blend files are Git LFS pointers in this checkout. Walls/floor are a grey placeholder shell
(C2's interior kit is not available here) and are not part of this delivery.
"""
import bpy, sys, json, math, re
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
from mathutils import Vector, Matrix
import ti_pipeline as pl

BATCH = HERE.parent; ART = BATCH.parents[2]; OUT = BATCH / 'Presentation'; OUT.mkdir(exist_ok=True)
VER = 'v001'
ROOM = dict(x0=-3.5, x1=3.5, y0=-2.5, y1=2.5, h=3.2, door_w=1.2, door_h=2.2)
# slot table from the task brief: scene (x, z) -> Blender (X, Y); facing -> rotation of a -Y-front model
FACE = {'-x': -math.pi / 2, '+x': math.pi / 2, '-z': 0.0, '+z': math.pi}
LAYOUT = [
    ('TI_Shelf', 'TI01_BoguShelf', (3.25, -0.6), '-x'),
    ('TI_Desk', 'TI03_JournalDesk', (-2.6, -1.6), '+x'),
    ('TI_Furnace', 'TI02_HomeFurnace', (2.7, -1.9), '-x'),
    ('TI_Lamp_1', 'TI04_PaperLamp', (-1.6, 2.1), '-z'),
    ('TI_Lamp_2', 'TI04_PaperLamp', (1.45, -2.1), '+z'),          # brief 1.9: moved so the furnace keeps a 0.6 m standing zone
    ('TI_Screen', 'TI05_LandscapeScreen', (-1.2, 0.4), '-z'),     # brief -1.4: moved so it clears the bed
    ('TI_Rug', 'TI06_WovenMat', (0.6, 0.0), '-z'),
    ('TI_Curtain_F', 'TI07_LinenCurtain', (0.0, -2.5), '-z'),
    ('TI_Curtain_B', 'TI07_LinenCurtain', (0.0, 2.5), '+z'),
]
EXISTING = [('Bed', 'DiscipleBed', (-2.75, 1.0), '-z'), ('StorageChest', 'StorageChest', (2.6, 1.9), '-z'),
            ('Cushion', 'MeditationCushion', (1.2, -0.2), '-z')]

def append_lod0(aid, groups=None):
    path = BATCH / 'Models' / aid / VER / f'{aid}_{VER}.blend'
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n.endswith('_LOD0') and (groups is None or any(g in n for g in groups))]
    objs = [o for o in dst.objects if o is not None]
    return objs

def instance(objs, name, loc, rot, col):
    out = []
    for o in objs:
        c = o.copy(); c.data = o.data; col.objects.link(c); c.name = f'{name}__{o.name}'
        c.matrix_world = Matrix.Translation(Vector(loc)) @ Matrix.Rotation(rot, 4, 'Z') @ o.matrix_world
        out.append(c)
    return out

def set_emit(v, prefix=None):
    for m in bpy.data.materials:
        if m.node_tree and 'EMIT_STRENGTH' in m.node_tree.nodes and (prefix is None or prefix in m.name):
            m.node_tree.nodes['EMIT_STRENGTH'].outputs[0].default_value = v

# ---------------------------------------------------------------- dondon furniture rebuilt from source
def build_existing(col):
    src5 = (ART / 'ArtLibrary/ExpansionBatches/SectFacilities05/BlenderSource/build_facilities05.py').read_text(encoding='utf-8')
    src1 = (ART / 'ArtLibrary/ExpansionBatches/HerbalExpansion01/BlenderSource/build_expansion.py').read_text(encoding='utf-8')
    def block(src, start, end):
        a = src.index(start); b = src.index(end, a); return src[a:b]
    helpers5 = block(src5, 'def mat(', 'def leaf(')
    made = {}
    for key, src, helpers, fn, cols in (
        ('DiscipleBed', src5, helpers5, block(src5, 'def bed():', 'def room_shell('), 'sect'),
        ('StorageChest', src5, helpers5, block(src5, 'def chest():', 'def bed():'), 'sect'),
        ('MeditationCushion', src1, block(src1, 'def mat(', 'def leaf(') if 'def leaf(' in src1 else block(src1, 'def mat(', 'def herb('),
         block(src1, 'def cushion():', 'BUILDERS='), 'herbal')):
        sub = bpy.data.collections.new('Existing_' + key); col.children.link(sub)
        root = bpy.data.objects.new(key + '_ROOT', None); sub.objects.link(root)
        ns = {'bpy': bpy, 'math': math, 'Vector': Vector, 'assets': sub, 'root': root}
        exec('import bpy, math\nfrom mathutils import Vector\n' + helpers, ns)
        m = ns['mat']
        if cols == 'sect':   # palette exactly as in build_facilities05.py
            ns.update(wood=m('Dark_Chestnut', (.16, .065, .028)), board=m('Warm_Timber', (.29, .14, .055)), jade=m('Celadon_Jade', (.08, .29, .24), .18, .32),
                      gold=m('Aged_Brass', (.51, .31, .075), .6, .34), bronze=m('Socket_Bronze', (.22, .14, .06), .6, .4),
                      paper=m('Warm_Window_Paper', (.61, .49, .29)), rope=m('Natural_Hemp', (.48, .35, .17)))
        else:                # palette as in build_expansion.py
            ns.update(board=m('Warm_Timber', (.34, .19, .085)), rope=m('Natural_Hemp', (.48, .36, .19)), straw=m('Golden_Straw', (.64, .48, .24)),
                      cloth=m('Sage_Canvas', (.32, .41, .29)))
        exec(fn, ns); ns[fn.split('(')[0].replace('def ', '')]()
        bpy.context.view_layer.update()
        objs = [o for o in sub.objects if o.type == 'MESH']
        lo, hi = pl.eval_bounds(objs)
        shift = Matrix.Translation(-Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z)))
        for o in objs:
            if o.parent == root: pass
        root.matrix_world = shift
        bpy.context.view_layer.update()
        made[key] = (root, objs, [round(v, 3) for v in hi - lo])
    return made

# ---------------------------------------------------------------- scene setup
def fresh():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene; s.unit_settings.system = 'METRIC'
    s.render.engine = 'CYCLES'; s.cycles.device = 'CPU'; s.cycles.use_denoising = True
    s.render.image_settings.file_format = 'PNG'; s.view_settings.view_transform = 'AgX'
    return s

def footprint(objs):
    lo, hi = pl.eval_bounds(objs); return [round(lo.x, 3), round(lo.y, 3), round(hi.x, 3), round(hi.y, 3), round(hi.z, 3)]

def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]

def shelf_states():
    s = fresh(); col = bpy.data.collections.new('Shelf'); s.collection.children.link(col)
    shelf = instance(append_lod0('TI01_BoguShelf'), 'Shelf', (0, 0, 0), 0, col)
    info = json.loads((BATCH / 'Models/TI01_BoguShelf' / VER / 'model_info.json').read_text(encoding='utf-8'))
    sockets = info['sockets_blender_xyz']
    props = {k: append_lod0(k) for k in ('TI08a_KeepsakeBox', 'TI08b_PaperScroll', 'TI08c_CeladonJar', 'TI08d_MedicinePot')}
    for objs in props.values():
        for o in objs: o.hide_render = True
    half = {1: 'TI08c_CeladonJar', 4: 'TI08a_KeepsakeBox', 6: 'TI08b_PaperScroll', 7: 'TI08d_MedicinePot'}
    full = {1: 'TI08c_CeladonJar', 2: 'TI08a_KeepsakeBox', 3: 'TI08b_PaperScroll', 4: 'TI08d_MedicinePot',
            5: 'TI08a_KeepsakeBox', 6: 'TI08c_CeladonJar', 7: 'TI08d_MedicinePot', 8: 'TI08b_PaperScroll'}
    report = {}
    for state, table in (('empty', {}), ('half', half), ('full', full)):
        placed = []
        for slot, key in table.items():
            p = sockets[f'SOCKET_slot_{slot}']; rot = .25 * ((slot % 3) - 1)
            placed += instance(props[key], f'{state}_{slot}', p, rot, col)
        pl.persp_shot(shelf + placed, OUT / f'shelf_{state}.png', direction=(.5, -1.4, .35), samples=96, lens=50, margin=1.05)
        report[state] = {str(k): v for k, v in table.items()}
        for o in placed: bpy.data.objects.remove(o)
    return report

def room(eye_day=True):
    s = fresh(); col = bpy.data.collections.new('Room'); s.collection.children.link(col)
    shell = bpy.data.collections.new('Placeholder_Shell_Not_Delivered'); s.collection.children.link(shell)
    pm = bpy.data.materials.new('Placeholder_Plaster'); pm.use_nodes = True
    pm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.42, .39, .34, 1)
    fm = bpy.data.materials.new('Placeholder_Floor'); fm.use_nodes = True
    fm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.16, .10, .06, 1)
    def slab(name, c, sz, m):
        bpy.ops.mesh.primitive_cube_add(size=1, location=c); o = bpy.context.object; o.scale = sz; o.name = name
        for cc in list(o.users_collection): cc.objects.unlink(o)
        shell.objects.link(o); o.data.materials.append(m); return o
    R = ROOM; t = .15
    slab('Floor', (0, 0, -.05), (7.6, 5.6, .1), fm)
    for sx in (-1, 1): slab('Wall_Side', (sx * (3.5 + t / 2), 0, R['h'] / 2), (t, 5.3, R['h']), pm)
    for sy in (-1, 1):
        side = (7 - R['door_w']) / 2
        for sx in (-1, 1): slab('Wall_End', (sx * (R['door_w'] / 2 + side / 2), sy * (2.5 + t / 2), R['h'] / 2), (side, t, R['h']), pm)
        slab('Door_Header', (0, sy * (2.5 + t / 2), (R['h'] + R['door_h']) / 2), (R['door_w'], t, R['h'] - R['door_h']), pm)
    ceil = slab('Ceiling', (0, 0, R['h'] + .05), (7.6, 5.6, .1), pm)
    items = {}; fps = {}
    cache = {}
    for slot, aid, (x, z), face in LAYOUT:
        if aid not in cache: cache[aid] = append_lod0(aid)
        objs = instance(cache[aid], slot, (x, z, 0), FACE[face], col)
        items[slot] = objs
    made = build_existing(col)
    for name, key, (x, z), face in EXISTING:
        root, objs, dims = made[key]
        root.matrix_world = Matrix.Translation((x, z, 0)) @ Matrix.Rotation(FACE[face], 4, 'Z') @ root.matrix_world
        items[name] = objs
    for cache_objs in cache.values():
        for o in cache_objs: o.hide_render = True; o.hide_viewport = True
    bpy.context.view_layer.update()
    for k, objs in items.items(): fps[k] = footprint(objs)
    return s, col, shell, ceil, items, fps

def layout_checks(fps):
    rep = {'footprints_xy_min_max_and_height': fps, 'room': ROOM, 'conflicts': [], 'door_clearance': {}, 'approach': {}}
    keys = list(fps)
    walk = {'TI_Rug', 'Cushion', 'TI_Curtain_F', 'TI_Curtain_B'}           # walkable / in the doorway by design
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if {a, b} <= walk or (a == 'TI_Rug' or b == 'TI_Rug'): continue
            if overlap(fps[a], fps[b]): rep['conflicts'].append([a, b])
    for name, y0, y1 in (('front', -2.5, -1.3), ('back', 1.3, 2.5)):
        zone = [-.6, y0, .6, y1]
        hits = [k for k, f in fps.items() if k not in walk and overlap(zone, f)]
        rep['door_clearance'][name] = {'zone_xy': zone, 'blocking': hits, 'pass': not hits}
    for k, f in fps.items():
        if k in walk or k.startswith('TI_Curtain'): continue
        # 0.6 m deep standing zone in front of the item's room-facing side
        cx, cy = (f[0] + f[2]) / 2, (f[1] + f[3]) / 2
        face = dict([(s, fc) for s, _, _, fc in LAYOUT] + [(n, fc) for n, _, _, fc in EXISTING]).get(k, '-z')
        if face == '-x': z = [f[0] - .6, cy - .3, f[0], cy + .3]
        elif face == '+x': z = [f[2], cy - .3, f[2] + .6, cy + .3]
        elif face == '+z': z = [cx - .3, f[3], cx + .3, f[3] + .6]
        else: z = [cx - .3, f[1] - .6, cx + .3, f[1]]
        inside = z[0] >= -3.5 and z[2] <= 3.5 and z[1] >= -2.5 and z[3] <= 2.5
        hits = [o for o, g in fps.items() if o != k and o not in walk and overlap(z, g)]
        rep['approach'][k] = {'zone_xy': [round(v, 3) for v in z], 'inside_room': inside, 'blocking': hits, 'pass': inside and not hits}
    rep['pass'] = not rep['conflicts'] and all(v['pass'] for v in rep['door_clearance'].values()) and all(v['pass'] for v in rep['approach'].values())
    return rep

def light_room(s, night):
    s.world = bpy.data.worlds.new('Room_World'); s.world.use_nodes = True
    bg = s.world.node_tree.nodes['Background']
    lights = []
    def add(kind, name, loc, energy, color, size=.5, rot=None):
        L = bpy.data.lights.new(name, kind); L.energy = energy; L.color = color
        if kind == 'AREA': L.size = size
        else: L.shadow_soft_size = size
        o = bpy.data.objects.new(name, L); s.collection.objects.link(o); o.location = loc
        if rot: o.rotation_euler = rot
        lights.append(o); return o
    if not night:
        bg.inputs[0].default_value = (.55, .62, .70, 1); bg.inputs[1].default_value = .6
        add('AREA', 'Daylight_Ceiling_Bounce', (0, 0, 3.0), 420, (1, .96, .9), 5.0)
        for sy in (-1, 1): add('AREA', 'Doorway_Daylight', (0, sy * 2.7, 1.2), 260, (.92, .96, 1.0), 1.2, (math.pi / 2 * (1 if sy < 0 else -1), 0, 0))
        set_emit(0)
    else:
        bg.inputs[0].default_value = (.02, .03, .06, 1); bg.inputs[1].default_value = .3
        set_emit(6.0, 'TI04'); set_emit(8.0, 'TI02')
        for slot, _, (x, z), _ in LAYOUT:
            if slot.startswith('TI_Lamp'): add('POINT', 'Lamp_' + slot, (x, z, 1.26), 140, (1, .66, .35), .12)
        add('POINT', 'Furnace_Fire', (2.62, -1.9, .27), 30, (1, .5, .2), .06)
        add('AREA', 'Moonlight_Doorway', (0, 2.7, 1.4), 40, (.6, .7, 1.0), 1.2, (-math.pi / 2, 0, 0))
    return lights

def render_room():
    s, col, shell, ceil, items, fps = room()
    rep = layout_checks(fps)
    s.render.resolution_x = 2048; s.render.resolution_y = 1000
    cam = bpy.data.objects.new('Eye_Camera', bpy.data.cameras.new('Eye_Camera')); s.collection.objects.link(cam); s.camera = cam
    # equirectangular eye-height panorama (+-86 deg) so the furniture on both side walls is in frame
    cam.data.type = 'PANO'; cam.data.panorama_type = 'EQUIRECTANGULAR'
    cam.data.longitude_min, cam.data.longitude_max = math.radians(-86), math.radians(86)
    cam.data.latitude_min, cam.data.latitude_max = math.radians(-52), math.radians(32)
    cam.location = (0, -2.3, 1.7)   # just inside the door curtain
    cam.rotation_euler = (Vector((0, 1.0, 1.7)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    for night in (False, True):
        lights = light_room(s, night)
        s.cycles.samples = 160; s.view_settings.exposure = .4 if night else -.4
        s.render.filepath = str(OUT / f'room_front_door_{"night" if night else "day"}.png'); bpy.ops.render.render(write_still=True)
        for o in lights: bpy.data.objects.remove(o)
    # top view with labels, ceiling hidden
    ceil.hide_render = True
    set_emit(0); light_room(s, False)
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 7.9; cam.location = (0, 0, 10); cam.rotation_euler = (0, 0, 0)
    s.render.resolution_x = 1600; s.render.resolution_y = 1160
    lab = bpy.data.materials.new('Label'); lab.use_nodes = True
    nt = lab.node_tree; nt.nodes.clear(); em = nt.nodes.new('ShaderNodeEmission'); em.inputs[0].default_value = (1, .92, .55, 1); em.inputs[1].default_value = 4
    out = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(em.outputs[0], out.inputs[0])
    s.view_settings.exposure = -.4
    labels = {k: v for k, v in [(s_, (x, z)) for s_, _, (x, z), _ in LAYOUT] + [(n, (x, z)) for n, _, (x, z), _ in EXISTING]}
    for k, (x, z) in labels.items():
        cu = bpy.data.curves.new(k, 'FONT'); cu.body = k; cu.size = .16; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.extrude = .002
        o = bpy.data.objects.new('Label_' + k, cu); s.collection.objects.link(o); o.location = (x, z + (.32 if k.startswith('TI_Lamp') else 0), 3.4)
        o.data.materials.append(lab)
    # door clearance zones as translucent red boxes
    zm = bpy.data.materials.new('Clearance'); zm.use_nodes = True; zn = zm.node_tree; zn.nodes.clear()
    e2 = zn.nodes.new('ShaderNodeEmission'); e2.inputs[0].default_value = (.2, .9, .5, 1); e2.inputs[1].default_value = .6
    tr = zn.nodes.new('ShaderNodeBsdfTransparent'); mx = zn.nodes.new('ShaderNodeMixShader'); mx.inputs[0].default_value = .35
    o2 = zn.nodes.new('ShaderNodeOutputMaterial'); zn.links.new(tr.outputs[0], mx.inputs[1]); zn.links.new(e2.outputs[0], mx.inputs[2]); zn.links.new(mx.outputs[0], o2.inputs[0])
    for y0, y1 in ((-2.5, -1.3), (1.3, 2.5)):
        bpy.ops.mesh.primitive_plane_add(size=1, location=(0, (y0 + y1) / 2, .02)); p = bpy.context.object; p.scale = (1.2, y1 - y0, 1); p.data.materials.append(zm)
    s.cycles.samples = 64
    s.render.filepath = str(OUT / 'room_top_slots.png'); bpy.ops.render.render(write_still=True)
    return rep

def lineup():
    s = fresh(); col = bpy.data.collections.new('Lineup'); s.collection.children.link(col)
    made = build_existing(col)
    order = [('DiscipleBed', None), ('TI01_BoguShelf', 1), ('TI03_JournalDesk', 1), ('StorageChest', None), ('TI02_HomeFurnace', 1),
             ('TI04_PaperLamp', 1), ('TI05_LandscapeScreen', 1), ('MeditationCushion', None), ('TI07_LinenCurtain', 1)]
    x = 0; objs_all = []
    for key, mine in order:
        if mine:
            objs = instance(append_lod0(key), 'L_' + key, (0, 0, 0), 0, col)
        else:
            root, objs, dims = made[key]
        lo, hi = pl.eval_bounds(objs); w = hi.x - lo.x
        M = Matrix.Translation((x + w / 2 - (lo.x + hi.x) / 2, 0, 0))
        if mine:
            for o in objs: o.matrix_world = M @ o.matrix_world
        else:
            root.matrix_world = M @ root.matrix_world
        bpy.context.view_layer.update(); x += w + .35; objs_all += objs
    mat = instance(append_lod0('TI06_WovenMat'), 'L_mat', (0, 0, 0), 0, col)
    lo, hi = pl.eval_bounds(objs_all)
    for o in mat: o.matrix_world = Matrix.Translation(((lo.x + hi.x) / 2, -1.3, 0)) @ o.matrix_world
    objs = objs_all + mat; pl.show_only(objs)
    cam, centre, ext = pl.studio(objs, 128)
    s.render.resolution_x = 2400; s.render.resolution_y = 1000
    cam.data.type = 'PERSP'; cam.data.lens = 40; cam.data.sensor_fit = 'HORIZONTAL'
    dist = (ext.x * .52) / math.tan(cam.data.angle / 2) + ext.y / 2
    cam.location = centre + Vector((.15, -1, .32)).normalized() * dist
    cam.rotation_euler = (centre - cam.location).to_track_quat('-Z', 'Y').to_euler()
    s.render.filepath = str(OUT / 'lineup_with_dondon_furniture.png'); bpy.ops.render.render(write_still=True)

if __name__ == '__main__':
    shelf = shelf_states()
    lineup()
    rep = render_room()
    rep['shelf_states'] = shelf
    rep['notes'] = ['Footprints are axis-aligned bounds of LOD0 meshes placed per the brief; walls/floor are a placeholder shell.',
                    'Rug, cushion and curtains are excluded from blocking tests (walkable or in the doorway by design).',
                    'Bed/chest/cushion orientation from the brief (90 / 180 / 0 deg) was interpreted so each fits inside the room; see README.']
    (OUT / 'layout_check.json').write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding='utf-8')
    print('PRESENTATION_COMPLETE pass=', rep['pass'])
