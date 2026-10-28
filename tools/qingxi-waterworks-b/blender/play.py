"""Qingxi waterworks repair, playable inside Blender (local demo).

    blender --python tools/qingxi-waterworks-b/blender/play.py [-- --fixture all|two|one|none] [--demo OUT_DIR]

What the player gets (all inside the 3D viewport, no README needed):
  * a planning board drawn over the viewport (bottom left): click a cell to lay the selected trough, click again to
    rotate, right click to take it out; arrows + Enter / R / X / G / 1-7 / Z / Y do the same from the keyboard;
  * the 3D view rebuilds the real kit GLBs port to port along whatever the board connects, with water running
    through, leaks spraying where a port is open or the old channel cracks, and the gate wheel turning;
  * a sidebar panel 「青溪古水路修復」 (top of the Tool tab) with the clues, treatment direction, meters, issues, local display stock and the receipt.

Rules are not re-implemented here: every edit goes through ../src/cli.mjs (node), which wraps waterworks-core.mjs —
the same code the tests and the proposed server contract use. Materials are local display stock, never the real
inventory. Blender has no touch input; touch play is not covered by this scene.

--demo OUT_DIR plays a scripted session (mis-connection, fix, gate, three plans, finish twice, undo/redo, retry),
saves window frames to OUT_DIR/frames, the receipts to OUT_DIR/receipts.json, then quits.
"""
import bpy, blf, gpu, json, math, shutil, subprocess, sys, time
from pathlib import Path
from mathutils import Vector, Matrix
from gpu_extras.batch import batch_for_shader
from bpy_extras import view3d_utils

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CLI = HERE.parent / 'src' / 'cli.mjs'
EXPORTS = REPO / 'art' / 'exports' / 'qingxi-waterworks-b'
FONT_FILES = ['C:/Windows/Fonts/msjh.ttc', 'C:/Windows/Fonts/msjhbd.ttc', 'C:/Windows/Fonts/NotoSansTC-VF.ttf']
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
CELL = 1.0                      # metres per board cell when a piece is not connected yet (connected pieces snap by port)
WATER_Z = 0.30
STEP = {'N': (0, 1), 'E': (1, 0), 'S': (0, -1), 'W': (-1, 0)}
OPP = {'N': 'S', 'E': 'W', 'S': 'N', 'W': 'E'}
SIDES = ['N', 'E', 'S', 'W']
KEYS_PIECES = ['straight', 'worn', 'bendR', 'bendL', 'tee', 'gate', 'apron']


def arg(name, default=None):
    return ARGS[ARGS.index(name) + 1] if name in ARGS and ARGS.index(name) + 1 < len(ARGS) else default


# ============================================================================ rules bridge
class Game:
    """Holds the rule state; every change is a round trip through cli.mjs."""

    def __init__(self):
        self.node = shutil.which('node')
        self.state = None; self.view = None; self.site = None; self.receipt = None; self.replayed = False
        self.sel = 'worn'; self.rot = 0; self.cursor = [3, 1]; self.hover = None
        self.toast = ('', 0.0, False); self.gate_t = {}; self.receipts = []

    def call(self, action):
        if not self.node:
            self.say('找不到 node，規則核心跑不起來。請先安裝 Node.js 22。', bad=True); return {'ok': False}
        out = subprocess.run([self.node, str(CLI)], input=json.dumps({'state': self.state, 'action': action}).encode('utf-8'),
                             capture_output=True, timeout=20)
        if out.returncode:
            self.say('規則核心錯誤：' + out.stderr.decode('utf-8', 'replace')[-300:], bad=True); return {'ok': False}
        r = json.loads(out.stdout.decode('utf-8'))
        self.state, self.view = r['state'], r['view']
        if action['op'] == 'site': self.site = r['res']['site']
        return r['res']

    def start(self, fixture):
        self.call({'op': 'site'}); self.call({'op': 'new', 'fixture': fixture, 'sessionId': 'blender'})
        self.receipt = None; self.gate_t = {}
        self.say(f"線索：{self.site['FIXTURES'][fixture]['label']}。先在右側選處理方向，再從水源（南邊 B01）往北鋪槽。")

    def say(self, text, bad=False):
        self.toast = (text, time.monotonic(), bad)

    # ------------------------------------------------------------------ helpers over the state
    def piece(self, x, y):
        return self.state['pieces'].get(f'{x},{y}') if self.state else None

    def sides(self, p):
        return [SIDES[(SIDES.index(s) + p['rot']) % 4] for s in self.site['PIECES'][p['type']]['sides']]

    def known(self, what):
        return self.state['known'].get(what, False)

    def act(self, action, ok_text=None):
        res = self.call(action)
        if not res.get('ok'):
            self.say(res.get('message') or '；'.join(i['message'] for i in res.get('issues', [])) or '做不到', bad=True)
        elif ok_text:
            self.say(ok_text)
        else:
            self.explain()
        rebuild(); return res

    def explain(self):
        """After an edit, surface the most useful rule message so the player knows what to do next."""
        sim = self.view['sim']; iss = sim['issues']
        if iss: self.say(iss[0]['message'], bad=iss[0]['code'] in ('PORT_MISMATCH', 'APRON_MISPLACED', 'LOOP'))
        elif not self.state['direction']: self.say(f"水已經到村田 {sim['fields']} L/s。到右側選一個處理方向，再按「完成方案」。")
        else: self.say(f"水路接通：村田 {sim['fields']} L/s（{sim['supply']}%），育幼區{sim['nursery']['text']}。可以按「完成方案」。")

    # ------------------------------------------------------------------ player actions
    def click(self, x, y):
        p = self.piece(x, y)
        if p: return self.act({'op': 'rotate', 'x': x, 'y': y})
        return self.act({'op': 'place', 'x': x, 'y': y, 'type': self.sel, 'rot': self.rot})

    def gate(self, x=None, y=None):
        if x is None:
            x, y = self.cursor
            if not (self.piece(x, y) and self.site['PIECES'][self.piece(x, y)['type']].get('gate')):
                gates = [k for k, p in self.state['pieces'].items() if self.site['PIECES'][p['type']].get('gate')]
                if not gates: self.say('還沒有閘板。按 6 選閘板，放在水路上。', bad=True); return
                x, y = map(int, gates[0].split(','))
        res = self.act({'op': 'gate', 'x': x, 'y': y})
        if res.get('ok'): self.say('閘板升起，水放行。' if res['open'] else '閘板放下，水被擋住。')

    def finish(self):
        res = self.call({'op': 'finish'})
        if res.get('ok'):
            self.receipt = res['receipt']; self.replayed = res['replay']
            if not res['replay']: self.receipts.append(res['receipt'])
            self.say('同一個請求重送：回傳原收據，展示材料沒有重複扣。' if res['replay'] else f"方案完成：{res['receipt']['outcomeId']}")
        else:
            self.say(res.get('message') or '；'.join(i['message'] for i in res.get('issues', [])[:2]), bad=True)
        rebuild(); return res


G = Game()


# ============================================================================ kit library + snapping
def info(key):
    return json.loads((EXPORTS / key / f'{key}_model_info.json').read_text(encoding='utf-8'))


LIB = {}       # model key -> {'info', 'objs' (hidden originals), 'root'}


def lib(key):
    if key in LIB: return LIB[key]
    col = coll('WW_LIB')
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(EXPORTS / key / f'{key}.glb'))
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        for c in list(o.users_collection): c.objects.unlink(o)
        col.objects.link(o)
        if o.animation_data: o.animation_data_clear()
    root = next(o for o in new if o.parent is None)
    LIB[key] = {'info': info(key), 'objs': [o for o in new if not o.name.startswith('SOCKET_')], 'root': root}
    return LIB[key]


def instance(key, T, col, tag):
    """Copy a library model (sharing meshes) into col with world matrix T. Returns {role: obj}."""
    L = lib(key); m = {}
    for o in L['objs']:
        c = o.copy(); col.objects.link(c); m[o] = c
    for o, c in m.items():
        c.parent = m.get(o.parent)
    root = m[L['root']]; root.matrix_world = T; root.name = f'WW_{tag}_{key}'
    roles = {'root': root}
    for o, c in m.items():
        base = o.name.split('.')[0]
        for role in ('Gate', 'Drive', 'Water'):
            if base.endswith('_' + role + '_LOD0') or base.endswith('_' + role): roles[role] = c
        if key == 'B06_GateWheel' and base.endswith('_LOD0'): roles['Wheel'] = c
        if c.type == 'MESH': c.hide_select = True
    for r in ('Gate', 'Drive', 'Wheel'):
        if r in roles:
            o = roles[r]; o.rotation_mode = 'XYZ'; o['base_loc'] = list(o.location); o['base_rot'] = list(o.rotation_euler)
    return roles


def port(mi, name):
    p = next(p for p in mi['ports'] if p['name'] == name)
    return Vector(p['position']), Vector(p['normal'])


def ang(v):
    return math.atan2(v.y, v.x)


def snap(T_prev, mi_prev, out_name, mi, in_name):
    pa, na = port(mi_prev, out_name); pa = T_prev @ pa; na = (T_prev.to_3x3() @ na).normalized()
    pb, nb = port(mi, in_name)
    R = Matrix.Rotation(ang(-na) - ang(nb), 4, 'Z')
    return Matrix.Translation(pa - R @ pb) @ R


def cell_world(x, y):
    return Vector(((x - 3) * CELL, 0.7 + (y - 0.5) * CELL, 0))


SOURCE_T = Matrix.Rotation(math.pi, 4, 'Z')      # B01 Out_Front (local -Y) faces north (+Y)


def loose_T(p, x, y):
    """Where an unconnected piece sits: its cell, turned so its first port faces the board side it names."""
    spec = G.site['PIECES'][p['type']]; mi = lib(spec['model'])['info']
    side = SIDES[(SIDES.index(spec['sides'][0]) + p['rot']) % 4]
    want = Vector((*STEP[side], 0)); _, n = port(mi, spec['ports'][0])
    R = Matrix.Rotation(ang(want) - ang(n), 4, 'Z')
    centre = sum((Vector(q['position']) for q in mi['ports']), Vector()) / len(mi['ports'])
    if len(mi['ports']) == 1: centre = Vector(mi['ports'][0]['position']) * 0.0
    return Matrix.Translation(cell_world(x, y) - R @ Vector((centre.x, centre.y, 0))) @ R


# ============================================================================ scene
def coll(name, hidden=False):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c)
        if hidden or name == 'WW_LIB':
            c.hide_viewport = True; c.hide_render = True
    return c


def clear(col):
    for o in list(col.objects): bpy.data.objects.remove(o)


def mat(name, rgb, rough=0.8, emit=0.0, alpha=1.0):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name)
    if not m.node_tree: m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*rgb, 1); b.inputs['Roughness'].default_value = rough
    if emit: b.inputs['Emission Color'].default_value = (*rgb, 1); b.inputs['Emission Strength'].default_value = emit
    if alpha < 1: b.inputs['Alpha'].default_value = alpha; m.surface_render_method = 'BLENDED'
    m.diffuse_color = (*rgb, alpha); return m


def box(name, col, c, s, m, rot=0.0):
    me = bpy.data.meshes.new(name); import bmesh
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); col.objects.link(o); o.location = c; o.scale = s; o.rotation_euler = (0, 0, rot)
    me.materials.append(m); o.hide_select = True; return o


def blob(name, col, c, r, m, seg=8, squash=1.0):
    import bmesh
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); col.objects.link(o); o.location = c; o.scale = (1, 1, squash); me.materials.append(m)
    o.hide_select = True; return o


def build_env():
    """Ground, creek, village field beds, boulders, the den's grass and the sandy slope, laid on the board grid."""
    col = coll('WW_ENV'); clear(col); S = G.site; T = S['TERRAIN']
    ground = mat('ww_ground', (0.30, 0.34, 0.20)); sand = mat('ww_sand', (0.62, 0.52, 0.33)); rock = mat('ww_rock', (0.36, 0.36, 0.34), 0.9)
    creek = mat('ww_creek', (0.10, 0.32, 0.42), 0.08, alpha=0.85); soil = mat('ww_soil', (0.30, 0.20, 0.12)); crop = mat('ww_crop', (0.33, 0.55, 0.20))
    grass = mat('ww_grass', (0.20, 0.38, 0.14)); bed = mat('ww_oldbed', (0.25, 0.24, 0.22), 0.95)
    box('WW_Ground', col, (0, 3.0, -0.06), (16, 16, 0.10), ground)
    box('WW_CreekS', col, (-1.0, -1.25, 0.0), (9.5, 0.9, 0.04), creek)          # creek feeding the source plinth
    box('WW_CreekW', col, (-4.05, 2.4, 0.0), (0.9, 8.2, 0.04), creek)           # and running back up the west side
    for x, y in T['seep']: box(f'WW_Seep_{x}_{y}', col, cell_world(x, y) + Vector((0, 0, -0.005)), (CELL * 0.98, CELL * 0.98, 0.02), sand)
    for x, y in T['oldChannel']: box(f'WW_OldBed_{x}_{y}', col, cell_world(x, y) + Vector((0, 0, -0.005)), (0.9, CELL * 0.98, 0.02), bed)
    for x, y in T['rock']:
        c = cell_world(x, y); blob(f'WW_Rock_{x}_{y}', col, c + Vector((0, 0, 0.25)), 0.55, rock, squash=0.65)
        blob(f'WW_Rock2_{x}_{y}', col, c + Vector((0.32, -0.25, 0.12)), 0.28, rock, squash=0.7)
    for i, (x, y) in enumerate(T['nursery']):                                     # tall grass + burrow mouth
        c = cell_world(x, y)
        for j in range(5):
            a = (i * 5 + j) * 2.39996; r = 0.18 + 0.07 * (j % 3)
            blob(f'WW_Tuft_{x}_{y}_{j}', col, c + Vector((math.cos(a) * r * 1.6, math.sin(a) * r * 1.6, 0.18)), 0.22, grass, squash=1.6)
    burrow = cell_world(4.5, 3.5); blob('WW_Burrow', col, burrow + Vector((0, 0, 0.02)), 0.30, soil, squash=0.35)
    top = cell_world(2, 5).y + CELL * 0.5                                           # village field beds north of row 5
    for i in range(3):
        y0 = top + 0.9 + i * 1.3
        box(f'WW_Bund_{i}', col, (-1.0, y0, 0.06), (3.6, 1.15, 0.12), soil)
        for r in range(5): box(f'WW_Crop_{i}_{r}', col, (-2.5 + r * 0.75, y0, 0.16), (0.14, 0.95, 0.10), crop)
    box('WW_FieldInlet', col, (-1.0, top + 0.3, 0.01), (3.0, 0.30, 0.03), creek)


def rebuild():
    """Re-snap every connected piece from the source along the rule core's reach tree; loose pieces sit on their cell."""
    if not G.state: return
    col = coll('WW_BUILD'); clear(col); fx = coll('WW_FX'); clear(fx)
    S = G.site; sim = G.view['sim']; reach = sim['reach']; wet = sim['wet']
    SCENE['pieces'] = {}; SCENE['paths'] = []; SCENE['sprays'] = []
    src = instance('B01_SourcePlinth', SOURCE_T, col, 'S00')
    SCENE['source'] = {'T': SOURCE_T, 'mi': lib('B01_SourcePlinth')['info'], 'roles': src}
    src_out, src_n = port(SCENE['source']['mi'], 'Out_Front')
    order = sorted(reach.items(), key=lambda kv: kv[1]['order'])
    for k, r in order:
        x, y = map(int, k.split(',')); p = G.state['pieces'][k]; spec = S['PIECES'][p['type']]; mi = lib(spec['model'])['info']
        sides = G.sides(p); in_port = spec['ports'][sides.index(r['inSide'])]
        if r['from'] == 'source':
            T = snap(SOURCE_T, SCENE['source']['mi'], 'Out_Front', mi, in_port)
        else:
            px, py = map(int, r['from'].split(',')); parent = SCENE['pieces'][r['from']]
            side = next(s for s in SIDES if (px + STEP[s][0], py + STEP[s][1]) == (x, y))
            pp = G.state['pieces'][r['from']]; out_port = S['PIECES'][pp['type']]['ports'][G.sides(pp).index(side)]
            T = snap(parent['T'], parent['mi'], out_port, mi, in_port)
        SCENE['pieces'][k] = place_piece(k, p, spec, mi, T, col, in_port, wet.get(k, 0))
    for k, p in G.state['pieces'].items():
        if k in reach: continue
        x, y = map(int, k.split(',')); spec = S['PIECES'][p['type']]
        SCENE['pieces'][k] = place_piece(k, p, spec, lib(spec['model'])['info'], loose_T(p, x, y), col, None, 0, loose=True)
    build_fx(fx)
    for o in bpy.data.objects:                     # imports leave the copies selected; keep the view clean
        try: o.select_set(False)
        except RuntimeError: pass
    bpy.context.view_layer.objects.active = None


def place_piece(k, p, spec, mi, T, col, in_port, q, loose=False):
    roles = instance(spec['model'], T, col, p['seg'])
    if 'Water' in roles: roles['Water'].hide_viewport = q <= 0
    d = {'T': T, 'mi': mi, 'roles': roles, 'in': in_port, 'q': q, 'loose': loose, 'seg': p['seg'], 'type': p['type']}
    if spec.get('gate'):
        sk = next(s for s in mi['sockets'] if s['name'] == 'WheelMount')
        d['wheel'] = instance('B06_GateWheel', T @ Matrix.Translation(Vector(sk['position'])), col, p['seg'] + 'W')
        G.gate_t.setdefault(k, 1.0 if p.get('open', True) else 0.0)
    return d


# ---------------------------------------------------------------------------- water flecks and leak sprays
SCENE = {'pieces': {}, 'paths': [], 'sprays': [], 'flecks': [], 'drops': []}


def world_port(d, name):
    pos, n = port(d['mi'], name); R = d['T'].to_3x3()
    return (d['T'] @ pos), (R @ n).normalized()


def meet(a, da, b, db):
    """Intersection of two horizontal rays (a + s*da, b + t*db), or None when parallel."""
    cr = da.x * db.y - da.y * db.x
    if abs(cr) < 1e-4: return None
    s = ((b.x - a.x) * db.y - (b.y - a.y) * db.x) / cr
    return a + da * s


def build_fx(col):
    blue = mat('ww_fleck', (0.30, 0.65, 1.0), 0.2, emit=1.2); spray = mat('ww_spray', (0.85, 0.95, 1.0), 0.2, emit=2.0)
    S = G.site; sim = G.view['sim']
    for k, d in SCENE['pieces'].items():
        if d['loose'] or d['q'] <= 0: continue
        spec = S['PIECES'][d['type']]
        if spec.get('gate') and G.gate_t.get(k, 1) < 0.5: continue
        a, na = world_port(d, d['in']); a.z = WATER_Z
        outs = [n for n in spec['ports'] if n != d['in']]
        if spec.get('outlet'):                                                  # apron: in -> pool -> over the lip
            T = d['T']; pts = [a, T @ Vector((0, 0.0, WATER_Z)), T @ Vector((0, -0.42, 0.20)), T @ Vector((0, -0.62, 0.02))]
            SCENE['paths'].append((pts, d['q']))
        for o in outs:
            b, nb = world_port(d, o); b.z = WATER_Z
            m = meet(a, -na, b, -nb); mid = Vector((m.x, m.y, WATER_Z)) if m else (a + b) / 2
            share = d['q'] / max(1, len(outs)); SCENE['paths'].append(([a, mid, b], share))
    for lk in sim['leaks']:
        k = f"{lk['at'][0]},{lk['at'][1]}"; d = SCENE['pieces'].get(k)
        if not d: continue
        if lk['why'] == 'open' and lk.get('side'):
            p = G.state['pieces'][k]; name = S['PIECES'][p['type']]['ports'][G.sides(p).index(lk['side'])]
            pos, n = world_port(d, name); pos.z = WATER_Z
        else:                                                                    # crack / seep: out through the side wall
            pos = d['T'] @ Vector((0.0, 0.0, 0.12)); n = (d['T'].to_3x3() @ Vector((1, 0, 0))).normalized()
        SCENE['sprays'].append((pos, n, lk['q'], lk['why']))
    me = bpy.data.meshes.get('ww_fleck_mesh')
    if not me:
        import bmesh
        me = bpy.data.meshes.new('ww_fleck_mesh'); bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.035); bm.to_mesh(me); bm.free()
        me.materials.append(blue)
    sme = bpy.data.meshes.get('ww_drop_mesh')
    if not sme:
        sme = me.copy(); sme.name = 'ww_drop_mesh'; sme.materials[0] = spray
    SCENE['flecks'] = []
    for i, (pts, q) in enumerate(SCENE['paths']):
        n = max(2, min(14, round(q / 6)))
        for j in range(n):
            o = bpy.data.objects.new('WW_Fleck', me); col.objects.link(o); o.hide_select = True
            SCENE['flecks'].append((o, i, j / n))
    SCENE['drops'] = []
    for i, (pos, n, q, why) in enumerate(SCENE['sprays']):
        for j in range(max(3, min(10, round(q / 3)))):
            o = bpy.data.objects.new('WW_Drop', sme); col.objects.link(o); o.hide_select = True
            SCENE['drops'].append((o, i, j))


def along(pts, t):
    L = [(b - a).length for a, b in zip(pts, pts[1:])]; tot = sum(L) or 1; s = t * tot
    for (a, b), l in zip(zip(pts, pts[1:]), L):
        if s <= l: return a.lerp(b, s / l if l else 0)
        s -= l
    return pts[-1]


def tick():
    """Animation pump (~30 fps): flecks, sprays, gate travel, wheel turn, water ripple."""
    now = time.monotonic()
    try:
        for o, i, ph in SCENE['flecks']:
            pts, q = SCENE['paths'][i]; L = sum((b - a).length for a, b in zip(pts, pts[1:])) or 1
            o.location = along(pts, (ph + now * 0.55 / L) % 1.0)
        for o, i, j in SCENE['drops']:
            pos, n, q, why = SCENE['sprays'][i]; t = (now * 1.3 + j * 0.37) % 1.0
            side = Vector((-n.y, n.x, 0)) * (((j * 7) % 5 - 2) * 0.03)
            o.location = pos + n * (0.55 * t) + side + Vector((0, 0, 0.25 * t - 0.9 * t * t))
        for k, d in SCENE['pieces'].items():
            if 'wheel' not in d: continue
            p = G.state['pieces'].get(k)
            if not p: continue
            want = 1.0 if p.get('open', True) else 0.0; t = G.gate_t.get(k, want)
            t = min(want, t + 0.03) if want > t else max(want, t - 0.03); G.gate_t[k] = t
            g = d['roles'].get('Gate')
            if g: g.location.z = g['base_loc'][2] + 0.32 * t
            for o in (d['roles'].get('Drive'), d['wheel'].get('Wheel')):
                if o: o.rotation_euler.x = o['base_rot'][0] + 10.0 * t
        for d in SCENE['pieces'].values():
            w = d['roles'].get('Water')
            if w and w.data.shape_keys:
                kb = w.data.shape_keys.key_blocks
                for name, ph in (('Ripple0', 0.0), ('Ripple1', 1.6)):
                    if name in kb: kb[name].value = 0.5 + 0.5 * math.sin(now * 2.2 + ph)
                if 'Open' in kb and d['type'] == 'gate': kb['Open'].value = G.gate_t.get(next((k for k, v in SCENE['pieces'].items() if v is d), ''), 1)
    except ReferenceError:
        pass                                     # objects were rebuilt between ticks
    for win in bpy.context.window_manager.windows:
        for a in win.screen.areas:
            if a.type == 'VIEW_3D': a.tag_redraw()
    return 1 / 30


# ============================================================================ overlay: board, labels, toast
FONT = {'id': 0}
LAYOUT = {}
COL = {'ground': (0.36, 0.40, 0.27, 0.92), 'old': (0.44, 0.40, 0.32, 0.95), 'seep': (0.74, 0.63, 0.40, 0.95), 'rock': (0.30, 0.30, 0.30, 0.95),
       'grass': (0.22, 0.40, 0.18, 0.95), 'den': (0.66, 0.36, 0.30, 0.95), 'fields': (0.38, 0.62, 0.25, 0.95), 'creek': (0.18, 0.45, 0.66, 0.95),
       'wet': (0.25, 0.60, 0.95, 1.0), 'dry': (0.80, 0.77, 0.70, 1.0), 'bad': (0.92, 0.25, 0.18, 1.0), 'line': (0.1, 0.1, 0.08, 0.55),
       'cursor': (1.0, 0.85, 0.2, 1.0), 'paper': (0.96, 0.94, 0.88, 0.94), 'ink': (0.12, 0.11, 0.10, 1.0), 'amber': (0.80, 0.50, 0.18, 1.0),
       'jade': (0.25, 0.44, 0.38, 1.0)}
SH = None


def rect(x, y, w, h, c):
    global SH
    SH = SH or gpu.shader.from_builtin('UNIFORM_COLOR')
    b = batch_for_shader(SH, 'TRIS', {'pos': [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]}, indices=[(0, 1, 2), (0, 2, 3)])
    SH.uniform_float('color', c); b.draw(SH)


def poly(pts, c):
    global SH
    SH = SH or gpu.shader.from_builtin('UNIFORM_COLOR')
    b = batch_for_shader(SH, 'TRIS', {'pos': pts}, indices=[(0, i, i + 1) for i in range(1, len(pts) - 1)]); SH.uniform_float('color', c); b.draw(SH)


def frame_rect(x, y, w, h, c, t=2):
    rect(x, y, w, t, c); rect(x, y + h - t, w, t, c); rect(x, y, t, h, c); rect(x + w - t, y, t, h, c)


def text(s, x, y, size, c=COL['ink'], center=False, shadow=False):
    f = FONT['id']; blf.size(f, size); blf.color(f, *c)
    if shadow: blf.enable(f, blf.SHADOW); blf.shadow(f, 3, 0, 0, 0, 0.85); blf.shadow_offset(f, 1, -1)
    if center: w, h = blf.dimensions(f, s); x -= w / 2; y -= h / 2
    blf.position(f, x, y, 0); blf.draw(f, s)
    if shadow: blf.disable(f, blf.SHADOW)


def wrap(s, n):
    out = []
    for para in s.split('\n'):
        while len(para) > n: out.append(para[:n]); para = para[n:]
        out.append(para)
    return out


def draw():
    if not G.state or not G.site: return
    reg = bpy.context.region; rv3d = bpy.context.region_data; ui = bpy.context.preferences.system.ui_scale
    gpu.state.blend_set('ALPHA'); BUTTONS.clear()
    draw_labels(reg, rv3d, ui)
    draw_board(reg, ui)
    draw_status(reg, ui)
    # banner + toast
    text('本機演示 · 展示材料，不入正式背包', reg.width / 2, reg.height - 70 * ui, 15 * ui, (1, 0.86, 0.75, 1), center=True, shadow=True)
    msg, t0, bad = G.toast
    if msg and time.monotonic() - t0 < 9:
        lines = wrap(msg, 34); lh = 22 * ui; w = min(reg.width - 40, 640 * ui); h = lh * len(lines) + 14 * ui
        x = (reg.width - w) / 2; y = reg.height - 84 * ui - h
        rect(x, y, w, h, (0.97, 0.87, 0.84, 0.95) if bad else COL['paper'])
        for i, l in enumerate(lines): text(l, x + 12 * ui, y + h - (i + 1) * lh, 15 * ui, COL['bad'] if bad else COL['ink'])
    gpu.state.blend_set('NONE')


def draw_labels(reg, rv3d, ui):
    S = G.site; T = S['TERRAIN']; sim = G.view['sim']
    def at(co): return view3d_utils.location_3d_to_region_2d(reg, rv3d, co)
    issues = {}
    for i in sim['issues']:
        if i.get('at'): issues.setdefault(f"{i['at'][0]},{i['at'][1]}", i)
    for k, d in SCENE['pieces'].items():
        p2 = at(d['T'] @ Vector((0, 0, 1.15)))
        if not p2: continue
        bad = k in issues; name = f"{d['seg']} {S['PIECES'][d['type']]['label']}"
        if d['loose']: name += '（未接水）'
        text(name, p2.x, p2.y, 13 * ui, COL['bad'] if bad or d['loose'] else (1, 1, 1, 1), center=True, shadow=True)
        if d['q'] > 0 and not d['loose']: text(f"{d['q']:.0f} L/s", p2.x, p2.y - 16 * ui, 11 * ui, (0.75, 0.9, 1, 1), center=True, shadow=True)
    hz = [('crack', '破槽', T['crack']), ('silt', '泥沙', T['silt'])]
    for what, label, cells in hz:
        for x, y in cells:
            p2 = at(cell_world(x, y) + Vector((0.55, 0, 0.5)))
            if p2: text(label if G.known(what) else '？未確認', p2.x, p2.y, 12 * ui, (1, 0.7, 0.5, 1) if G.known(what) else (0.85, 0.85, 0.8, 1), shadow=True)
    p2 = at(cell_world(4.5, 3.5) + Vector((0, 0, 0.9)))
    if p2: text('育幼區（幼獸足跡）' if G.known('nursery') else '？草叢', p2.x, p2.y, 13 * ui, (1, 0.75, 0.65, 1) if G.known('nursery') else (0.9, 0.9, 0.85, 1), center=True, shadow=True)
    for label, co in (('村田進水口', Vector((-1.0, cell_world(2, 5).y + 1.2, 0.4))), ('溪道回流口', Vector((-4.0, 1.7, 0.3))), ('水源 B01', Vector((0, 0, 1.0)))):
        p2 = at(co)
        if p2: text(label, p2.x, p2.y, 13 * ui, (0.85, 0.95, 1, 1), center=True, shadow=True)


def draw_board(reg, ui):
    S = G.site; T = S['TERRAIN']; W, H = S['W'], S['H']; sim = G.view['sim']
    c = round(46 * ui); band = round(14 * ui); x0 = round(70 * ui) + band; y0 = round(46 * ui)
    ph = round(34 * ui); pal_h = 4 * ph + 8 * ui; top = y0 + H * c + band
    LAYOUT.update(region=(reg.x, reg.y), x0=x0, y0=y0, c=c, W=W, H=H, pal=(x0, top + 6 * ui, W * c / 4, ph))
    rect(x0 - band - 8 * ui, y0 - 34 * ui, W * c + band + 16 * ui, H * c + band + pal_h + 50 * ui, (0.12, 0.13, 0.11, 0.80))
    # controls: treatment direction, then gate / undo / redo / finish / retry
    st = G.state; bw = W * c / 3; by = top + 6 * ui + 2 * ph + 8 * ui
    for i, (d, spec) in enumerate(S['DIRECTIONS'].items()):
        button(x0 + i * bw, by + ph, bw, ph, spec['label'], lambda d=d: G.act({'op': 'direction', 'dir': d},
               ok_text=f"處理方向：{S['DIRECTIONS'][d]['label']}。{S['DIRECTIONS'][d]['text']}"), ui, on=st['direction'] == d,
               sub=' '.join(f"{S['STOCK_ZH'][m]}{n}" for m, n in spec['cost'].items()))
    bw = W * c / 5
    for i, (label, fn, accent) in enumerate((('閘板 G', lambda: G.gate(), False), ('撤回 Z', lambda: G.act({'op': 'undo'}), False),
                                              ('重做 Y', lambda: G.act({'op': 'redo'}), False), ('完成方案', G.finish, True), ('重試', retry, False))):
        button(x0 + i * bw, by, bw, ph, label, fn, ui, accent=accent)
    # palette
    px, py, pw, ph = LAYOUT['pal']
    for i, t in enumerate(KEYS_PIECES):
        on = t == G.sel; x = px + (i % 4) * pw; py_i = py + (1 - i // 4) * ph
        rect(x + 2, py_i + 2, pw - 4, ph - 4, COL['jade'] if on else COL['paper'])
        text(f"{i + 1} {S['PIECES'][t]['label']}", x + pw / 2, py_i + ph * 0.64, 12 * ui, (1, 1, 1, 1) if on else COL['ink'], center=True)
        cost = ' '.join(f"{S['STOCK_ZH'][m][:1]}{n}" for m, n in S['PIECES'][t]['cost'].items())
        text(cost, x + pw / 2, py_i + ph * 0.27, 10 * ui, (0.9, 0.95, 0.9, 1) if on else (0.4, 0.38, 0.34, 1), center=True)
    # targets
    for tg in S['TARGETS']:
        for x, y in tg['cells']:
            if tg['side'] == 'N': rect(x0 + x * c, y0 + H * c, c, band, COL['fields'])
            else: rect(x0 - band, y0 + y * c, band, c, COL['creek'])
    text('村田進水口', x0 + 2 * c + c / 2, y0 + H * c + band + 1, 10 * ui, (0.9, 1, 0.85, 1), center=True)
    # cells
    for y in range(H):
        for x in range(W):
            cx, cy = x0 + x * c, y0 + y * c; col = COL['ground']; tag = ''
            if [x, y] in T['oldChannel']: col = COL['old']
            if [x, y] in T['seep']: col, tag = COL['seep'], '沙坡'
            if [x, y] in T['rock']: col, tag = COL['rock'], '大石'
            if [x, y] in T['nursery']: col, tag = (COL['den'], '育幼') if G.known('nursery') else (COL['grass'], '草叢')
            if [x, y] in T['crack'] and G.known('crack'): tag = '裂'
            if [x, y] in T['silt'] and G.known('silt'): tag = '淤'
            rect(cx + 1, cy + 1, c - 2, c - 2, col)
            if tag: text(tag, cx + 4 * ui, cy + 4 * ui, 10 * ui, (1, 1, 1, 0.85))
    sx, sy = S['SOURCE']['x'], S['SOURCE']['y']
    rect(x0 + sx * c + c * 0.15, y0 + sy * c + c * 0.15, c * 0.7, c * 0.7, COL['creek']); text('B01', x0 + sx * c + c / 2, y0 + sy * c + c / 2, 11 * ui, (1, 1, 1, 1), center=True)
    rect(x0 + sx * c + c * 0.36, y0 + sy * c + c * 0.85, c * 0.28, c * 0.15, COL['wet'])
    # pieces
    bad_cells = {f"{i['at'][0]},{i['at'][1]}" for i in sim['issues'] if i.get('at')}
    for k, p in G.state['pieces'].items():
        x, y = map(int, k.split(',')); glyph(x0 + x * c, y0 + y * c, c, p, sim['wet'].get(k, 0) > 0, ui)
        if k in bad_cells: frame_rect(x0 + x * c + 1, y0 + y * c + 1, c - 2, c - 2, COL['bad'], max(2, round(2 * ui)))
    hx = G.hover
    if hx and not G.piece(*hx) and not G.state['finished']:
        glyph(x0 + hx[0] * c, y0 + hx[1] * c, c, {'type': G.sel, 'rot': G.rot, 'seg': '', 'open': True}, False, ui, ghost=True)
    frame_rect(x0 + G.cursor[0] * c, y0 + G.cursor[1] * c, c, c, COL['cursor'], max(2, round(2 * ui)))
    text(f"旋轉 {G.rot * 90}°（R）  ·  左鍵放／轉  右鍵拆  方向鍵+Enter  G 閘板  Z 撤回  Y 重做", x0 - band, y0 - 24 * ui, 11 * ui, (0.92, 0.9, 0.85, 1))


BUTTONS = []


def button(x, y, w, h, label, fn, ui, on=False, accent=False, sub=None):
    bg = COL['jade'] if on else COL['amber'] if accent else COL['paper']; fg = (1, 1, 1, 1) if on or accent else COL['ink']
    rect(x + 2, y + 2, w - 4, h - 4, bg)
    text(label, x + w / 2, y + h * (0.64 if sub else 0.5), 12 * ui, fg, center=True)
    if sub: text(sub, x + w / 2, y + h * 0.27, 10 * ui, (0.9, 0.95, 0.9, 1) if on else (0.4, 0.38, 0.34, 1), center=True)
    BUTTONS.append((x, y, w, h, fn))


def retry():
    G.act({'op': 'retry'}, ok_text='新方案：展示材料重置，請求編號換新。現有槽件保留，可以拆掉重鋪。'); G.receipt = None


def next_fixture():
    keys = list(G.site['FIXTURES']); sc = bpy.context.scene
    sc.ww_fixture = keys[(keys.index(sc.ww_fixture) + 1) % len(keys)]


def draw_status(reg, ui):
    """Right-hand card: steps, clues and unknown risks, water meters, what is still wrong, stock, receipt."""
    S = G.site; st = G.state; sim = G.view['sim']; chk = G.view['check']; q = G.view['quote']
    w = round(330 * ui); lh = round(19 * ui); x = reg.width - w - 16 * ui; n = 20
    rows = []                                                  # (text, colour, size) or ('bar', frac, colour) or ('btn', label, fn)
    ink, red, amber, jade, dim = COL['ink'], COL['bad'], (0.62, 0.40, 0.08, 1), COL['jade'], (0.45, 0.43, 0.40, 1)
    steps = [('看線索', True), ('選處理方向', bool(st['direction'])), ('從水源鋪到村田', sim['fields'] > 0 and not sim['issues']),
             ('開閘看水', sim['fields'] > 0), ('完成方案', bool(st['finished']))]
    now = next((i for i, (_, d) in enumerate(steps) if not d), None)
    mark = lambda i, d: '■' if d else '▶' if i == now else '□'
    rows.append(('  '.join(f"{mark(i, d)}{i + 1}{t}" for i, (t, d) in enumerate(steps[:3])), ink, 12))
    rows.append(('  '.join(f"{mark(i + 3, d)}{i + 4}{t}" for i, (t, d) in enumerate(steps[3:])), ink, 12))
    rows.append(('btn', f"線索：{S['FIXTURES'][bpy.context.scene.ww_fixture]['label']}（點我換）", next_fixture))
    rows.append(('  '.join(f"{o['label']}{'：看到' if oid in st['observationIds'] else '：沒看到'}" for oid, o in S['OBSERVATIONS'].items()), dim, 12))
    for r in sim['risks']:
        for l in wrap('未知風險：' + r, n): rows.append((l, amber, 12))
    rows.append((f"處理方向：{S['DIRECTIONS'][st['direction']]['label'] if st['direction'] else '還沒選'}", ink, 13))
    rows.append((f"到村田 {sim['fields']} L/s（{sim['supply']}%，需求 {S['FIELD_DEMAND']}）", ink, 13)); rows.append(('bar', sim['supply'] / 100, COL['wet']))
    rows.append((f"回溪道 {sim['creek']} L/s   漏失 {sum(l['q'] for l in sim['leaks']):.1f} L/s", ink, 12))
    rows.append((f"育幼區：{sim['nursery']['text']}" + ('' if G.known('nursery') else '（線索沒看到，只是預估）'), red if sim['nursery']['level'] == 2 else ink, 12))
    if chk['issues'] and not st['finished']:
        rows.append((f"還要處理 {len(chk['issues'])} 件：", red, 13))
        for iss in chk['issues'][:3]:
            for l in wrap(iss['message'], n): rows.append((l, red, 12))
    else:
        rows.append(('沒有問題，可以按「完成方案」。' if not st['finished'] else '已完成；再按一次只會拿回同一張收據。', jade, 12))
    rows.append(('展示材料（不是正式背包）需要/現有：', dim, 12))
    rows.append(('  '.join(f"{S['STOCK_ZH'][m]}{q['need'].get(m, 0)}/{have}" for m, have in st['stock'].items()), ink, 12))
    rows.append((f"請求編號 {G.view['requestId']}", dim, 11))
    if G.receipt:
        rc = G.receipt; res = rc['result']
        rows.append(('重送：同一張收據，沒有重複扣料' if G.replayed else '收據', jade, 13))
        for l in [f"outcomeId：{rc['outcomeId']}", f"村田 {res['fieldsFlow']} L/s（{res['fieldsSupplyPct']}%） 溪道 {res['creekFlow']} L/s",
                  f"育幼區：{res['nursery']}", '扣料：' + ' '.join(f"{S['STOCK_ZH'][m]}{v}" for m, v in rc['materials']['spent'].items())] + rc['surprises']:
            for ll in wrap(l, n): rows.append((ll, ink, 12))
    h = sum(lh * (1.5 if r[0] == 'btn' else 0.6 if r[0] == 'bar' else 1) for r in rows) + 44 * ui
    y = reg.height - 110 * ui; rect(x, y - h, w, h, COL['paper'])
    text('青溪古水路修復', x + 12 * ui, y - 24 * ui, 15 * ui, ink); y -= 34 * ui
    for r in rows:
        if r[0] == 'bar':
            rect(x + 12 * ui, y - lh * 0.45, w - 24 * ui, lh * 0.35, (0.85, 0.82, 0.74, 1)); rect(x + 12 * ui, y - lh * 0.45, (w - 24 * ui) * min(1, r[1]), lh * 0.35, r[2]); y -= lh * 0.6
        elif r[0] == 'btn':
            button(x + 8 * ui, y - lh * 1.35, w - 16 * ui, lh * 1.3, r[1], r[2], ui); y -= lh * 1.5
        else:
            text(r[0], x + 12 * ui, y - lh * 0.8, r[2] * ui, r[1]); y -= lh


def glyph(x, y, c, p, wet, ui, ghost=False):
    spec = G.site['PIECES'][p['type']]; a = 0.45 if ghost else 1.0
    col = COL['wet'] if wet else COL['dry']; col = (*col[:3], a); w = c * 0.30; m = x + c / 2, y + c / 2
    sides = G.sides(p)
    for s in sides:
        dx, dy = STEP[s]
        if dx: rect(min(m[0], m[0] + dx * c / 2), m[1] - w / 2, c / 2, w, col)
        else: rect(m[0] - w / 2, min(m[1], m[1] + dy * c / 2), w, c / 2, col)
    rect(m[0] - w / 2, m[1] - w / 2, w, w, col)
    if spec.get('outlet'):
        o = SIDES[(SIDES.index(spec['outlet']) + p['rot']) % 4]; dx, dy = STEP[o]; ex, ey = m[0] + dx * c * 0.45, m[1] + dy * c * 0.45
        sx, sy = -dy * c * 0.28, dx * c * 0.28
        poly([(m[0] + sx, m[1] + sy), (ex + sx * 0.5, ey + sy * 0.5), (ex - sx * 0.5, ey - sy * 0.5), (m[0] - sx, m[1] - sy)], (*COL['wet'][:3], 0.6 * a) if wet else col)
    if spec.get('gate'):
        s0 = sides[0]; dx, dy = STEP[s0]; bar = (0.85, 0.2, 0.15, a) if not p.get('open', True) else (*COL['amber'][:3], a)
        if dx: rect(m[0] - c * 0.06, m[1] - c * 0.32, c * 0.12, c * 0.64, bar)
        else: rect(m[0] - c * 0.32, m[1] - c * 0.06, c * 0.64, c * 0.12, bar)
    if p.get('seg'): text(p['seg'], x + c - 22 * ui, y + c - 13 * ui, 9 * ui, (1, 1, 1, 0.9))


def board_cell(mx, my):
    """Window mouse coords -> board cell, palette index, or None."""
    if not LAYOUT: return None
    rx, ry = LAYOUT['region']; x, y = mx - rx, my - ry; c = LAYOUT['c']
    for i, (bx, by, bw, bh, _) in enumerate(BUTTONS):
        if bx <= x < bx + bw and by <= y < by + bh: return ('btn', i)
    px, py, pw, ph = LAYOUT['pal']
    if py <= y < py + 2 * ph and px <= x < px + pw * 4:
        i = int(1 - (y - py) // ph) * 4 + int((x - px) // pw)
        return ('pal', i) if i < len(KEYS_PIECES) else None
    gx, gy = (x - LAYOUT['x0']) // c, (y - LAYOUT['y0']) // c
    if 0 <= gx < LAYOUT['W'] and 0 <= gy < LAYOUT['H']: return ('cell', int(gx), int(gy))
    return None


# ============================================================================ operators + panel
class WW_OT_play(bpy.types.Operator):
    """Board input: mouse over the board and keyboard while the cursor is in the 3D view"""
    bl_idname = 'ww.play'; bl_label = '開始操作'

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self); WW_OT_play.running = True; return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if not G.state: return {'PASS_THROUGH'}
        area = next((a for a in context.window.screen.areas if a.type == 'VIEW_3D'), None)
        if not area: return {'PASS_THROUGH'}
        reg = next(r for r in area.regions if r.type == 'WINDOW')
        inside = reg.x <= event.mouse_x < reg.x + reg.width and reg.y <= event.mouse_y < reg.y + reg.height
        ui_reg = next((r for r in area.regions if r.type == 'UI'), None)
        if ui_reg and ui_reg.width > 1 and ui_reg.x <= event.mouse_x < ui_reg.x + ui_reg.width and reg.y <= event.mouse_y < reg.y + reg.height:
            inside = False                                         # the sidebar sits over the region; leave its clicks alone
        if not inside: return {'PASS_THROUGH'}
        hit = board_cell(event.mouse_x, event.mouse_y)
        if event.type == 'MOUSEMOVE':
            G.hover = hit[1:] if hit and hit[0] == 'cell' else None; return {'PASS_THROUGH'}
        if event.value != 'PRESS': return {'PASS_THROUGH'}
        if event.type in ('LEFTMOUSE', 'RIGHTMOUSE') and hit:
            if hit[0] == 'btn':
                if event.type == 'LEFTMOUSE': BUTTONS[hit[1]][4]()
                return {'RUNNING_MODAL'}
            if hit[0] == 'pal':
                if event.type == 'LEFTMOUSE': G.sel = KEYS_PIECES[hit[1]]; G.say(f"選了「{G.site['PIECES'][G.sel]['label']}」。點格子放下。")
                return {'RUNNING_MODAL'}
            G.cursor = list(hit[1:])
            if event.type == 'LEFTMOUSE': G.click(*hit[1:])
            else: G.act({'op': 'remove', 'x': hit[1], 'y': hit[2]})
            return {'RUNNING_MODAL'}
        if event.ctrl or event.alt: return {'PASS_THROUGH'}
        k = event.type; cx, cy = G.cursor
        moves = {'UP_ARROW': (0, 1), 'DOWN_ARROW': (0, -1), 'LEFT_ARROW': (-1, 0), 'RIGHT_ARROW': (1, 0)}
        if k in moves:
            G.cursor = [min(G.site['W'] - 1, max(0, cx + moves[k][0])), min(G.site['H'] - 1, max(0, cy + moves[k][1]))]; G.hover = G.cursor
        elif k in ('RET', 'NUMPAD_ENTER', 'SPACE'): G.click(cx, cy)
        elif k == 'R':
            if G.piece(cx, cy): G.act({'op': 'rotate', 'x': cx, 'y': cy})
            else: G.rot = (G.rot + 1) % 4; G.say(f'下一件旋轉 {G.rot * 90}°')
        elif k in ('X', 'DEL', 'BACK_SPACE'): G.act({'op': 'remove', 'x': cx, 'y': cy})
        elif k == 'G': G.gate()
        elif k == 'Z': G.act({'op': 'undo'})
        elif k == 'Y': G.act({'op': 'redo'})
        elif k in ('ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN'):
            G.sel = KEYS_PIECES[['ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN'].index(k)]; G.say(f"選了「{G.site['PIECES'][G.sel]['label']}」")
        else: return {'PASS_THROUGH'}
        return {'RUNNING_MODAL'}


WW_OT_play.running = False


class WW_OT_do(bpy.types.Operator):
    bl_idname = 'ww.do'; bl_label = '水路操作'
    op: bpy.props.StringProperty(); arg: bpy.props.StringProperty()

    @classmethod
    def description(cls, context, props):
        return {'direction': '選這個處理方向', 'piece': '選這種槽件（之後點規劃板格子放下）', 'gate': '轉動閘輪：升起／放下閘板 (G)',
                'undo': '撤回上一步 (Z)', 'redo': '重做 (Y)', 'finish': '完成方案：結算一次，重按只會拿回同一張收據',
                'retry': '開新方案（新的請求編號，展示材料重置）', 'view': '把視角拉回整條水路', 'fixture': '換一組觀察線索（重新開始）'}.get(props.op, '')

    def execute(self, context):
        o, a = self.op, self.arg
        if o == 'direction': G.act({'op': 'direction', 'dir': a}, ok_text=f"處理方向：{G.site['DIRECTIONS'][a]['label']}。{G.site['DIRECTIONS'][a]['text']}")
        elif o == 'piece': G.sel = a; G.say(f"選了「{G.site['PIECES'][a]['label']}」。點規劃板格子放下。")
        elif o == 'gate': G.gate()
        elif o in ('undo', 'redo'): G.act({'op': o})
        elif o == 'finish': G.finish()
        elif o == 'retry': retry()
        elif o == 'view': frame_view()
        elif o == 'fixture': context.scene.ww_fixture = a
        return {'FINISHED'}


def on_fixture(self, context):
    G.start(self.ww_fixture); build_env(); rebuild()


class WW_PT_panel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'; bl_region_type = 'UI'; bl_category = 'Tool'; bl_label = '青溪古水路修復'
    bl_order = -1000                                 # top of the default Tool tab (Region.active_panel_category is read-only)

    def draw(self, context):
        L = self.layout; S = G.site
        if not G.state: L.label(text='載入中…'); return
        st = G.state; sim = G.view['sim']; chk = G.view['check']; n = max(14, int(context.region.width / (14 * context.preferences.system.ui_scale)))
        box = L.box(); box.alert = True; box.label(text='本機演示 · 展示材料，不入正式背包', icon='INFO')
        if not WW_OT_play.running: L.operator('ww.play', text='開始操作（規劃板接收滑鼠／鍵盤）', icon='PLAY')
        # steps
        steps = [('看線索', True), ('選處理方向', bool(st['direction'])), ('從水源鋪到村田', sim['fields'] > 0 and not sim['issues']),
                 ('開閘看水', sim['fields'] > 0), ('完成方案', bool(st['finished']))]
        col = L.column(align=True); now = next((i for i, (_, d) in enumerate(steps) if not d), None)
        for i, (t, d) in enumerate(steps):
            col.label(text=f"{i + 1}. {t}", icon='CHECKMARK' if d else ('RIGHTARROW' if i == now else 'DOT'))
        # clues
        b = L.box(); b.label(text='觀察線索（來自觀察者 A，本機 fixture）', icon='VIEWZOOM'); b.prop(context.scene, 'ww_fixture', text='')
        for oid, o in S['OBSERVATIONS'].items():
            seen = oid in st['observationIds']; r = b.row(); r.active = seen
            r.label(text=f"{o['label']}：{'看到' if seen else '沒看到'}", icon='HIDE_OFF' if seen else 'HIDE_ON')
        for r in sim['risks']:
            for i, l in enumerate(wrap('未知風險：' + r, n)): row = b.row(); row.alert = True; row.label(text=l, icon='ERROR' if i == 0 else 'BLANK1')
        # direction
        b = L.box(); b.label(text='處理方向', icon='ORIENTATION_GIMBAL')
        for d, spec in S['DIRECTIONS'].items():
            cost = ' '.join(f"{S['STOCK_ZH'][m]}{v}" for m, v in spec['cost'].items())
            op = b.operator('ww.do', text=f"{spec['label']}（{cost}）", depress=st['direction'] == d); op.op = 'direction'; op.arg = d
        if st['direction']:
            for l in wrap(S['DIRECTIONS'][st['direction']]['text'], n): b.label(text=l)
        # pieces + edit tools
        b = L.box(); b.label(text=f"槽件（下一件旋轉 {G.rot * 90}°）", icon='MOD_ARRAY'); g = b.grid_flow(columns=2, align=True)
        for i, t in enumerate(KEYS_PIECES):
            op = g.operator('ww.do', text=f"{i + 1} {S['PIECES'][t]['label']}", depress=G.sel == t); op.op = 'piece'; op.arg = t
        r = b.row(align=True)
        for o, t, ic in (('gate', '閘板 G', 'MODIFIER'), ('undo', '撤回 Z', 'LOOP_BACK'), ('redo', '重做 Y', 'LOOP_FORWARDS'), ('view', '看全線', 'VIEW_CAMERA')):
            op = r.operator('ww.do', text=t, icon=ic); op.op = o
        # meters
        b = L.box(); b.label(text='水量（依已知線索預估）', icon='MOD_FLUIDSIM')
        b.label(text=f"到村田：{sim['fields']} L/s（需求 {S['FIELD_DEMAND']}，{sim['supply']}%）"); b.progress(factor=sim['supply'] / 100, text=f"{sim['supply']}%")
        b.label(text=f"回溪道：{sim['creek']} L/s"); b.label(text=f"漏失：{sum(l['q'] for l in sim['leaks']):.1f} L/s")
        r = b.row(); r.alert = sim['nursery']['level'] == 2; r.label(text=f"育幼區：{sim['nursery']['text']}" + ('' if G.known('nursery') else '（線索未看到）'))
        # issues
        if chk['issues']:
            b = L.box(); b.label(text=f"還要處理（{len(chk['issues'])}）", icon='ERROR')
            for iss in chk['issues'][:6]:
                for i, l in enumerate(wrap(iss['message'], n)): row = b.row(); row.alert = True; row.label(text=l, icon='DOT' if i == 0 else 'BLANK1')
        # stock
        q = G.view['quote']; b = L.box(); b.label(text='展示材料（不是正式背包）', icon='PACKAGE'); g = b.grid_flow(columns=3, align=True)
        for m, have in st['stock'].items():
            need = q['need'].get(m, 0); cell = g.row(); cell.alert = need > have; cell.label(text=f"{S['STOCK_ZH'][m]} {need}/{have}")
        # finish
        b = L.box(); r = b.row(align=True); r.scale_y = 1.5
        op = r.operator('ww.do', text='完成方案', icon='CHECKMARK'); op.op = 'finish'
        op = r.operator('ww.do', text='重試（新方案）', icon='FILE_REFRESH'); op.op = 'retry'
        b.label(text=f"請求編號：{G.view['requestId']}")
        if G.receipt:
            rc = G.receipt; res = rc['result']
            b.label(text=('重送：同一張收據，沒有重複扣料' if G.replayed else '收據'), icon='FILE_TEXT')
            for l in [f"結果：{rc['outcomeId']}", f"村田 {res['fieldsFlow']} L/s（{res['fieldsSupplyPct']}%） 溪道 {res['creekFlow']} L/s",
                      f"育幼區：{res['nursery']}", '扣料：' + ' '.join(f"{S['STOCK_ZH'][m]}{v}" for m, v in rc['materials']['spent'].items())] + rc['surprises']:
                for w in wrap(l, n): b.label(text=w)


def frame_view():
    for win in bpy.context.window_manager.windows:
        for a in win.screen.areas:
            if a.type != 'VIEW_3D': continue
            r3 = a.spaces.active.region_3d
            r3.view_location = Vector((-0.6, 2.9, 0.3)); r3.view_distance = 10.0; r3.view_perspective = 'PERSP'
            r3.view_rotation = (Matrix.Rotation(math.radians(-18), 3, 'Z') @ Matrix.Rotation(math.radians(52), 3, 'X')).to_quaternion()


# ============================================================================ startup
def setup_view():
    win = bpy.context.window_manager.windows[0]
    area = next(a for a in win.screen.areas if a.type == 'VIEW_3D')
    with bpy.context.temp_override(window=win, area=area, region=next(r for r in area.regions if r.type == 'WINDOW')):
        try: bpy.ops.screen.screen_full_area()
        except RuntimeError: pass
    for a in bpy.context.window_manager.windows[0].screen.areas:
        if a.type != 'VIEW_3D': continue
        sp = a.spaces.active; sp.show_region_ui = False; sp.show_region_toolbar = False; sp.overlay.show_floor = False
        sp.overlay.show_axis_x = sp.overlay.show_axis_y = False; sp.overlay.show_relationship_lines = False; sp.overlay.show_extras = False
        sp.overlay.show_outline_selected = False; sp.overlay.show_object_origins = False; sp.shading.type = 'MATERIAL'; sp.clip_end = 300
    frame_view()


def start():
    win = bpy.context.window_manager.windows[0]
    setup_view()
    area = next(a for a in win.screen.areas if a.type == 'VIEW_3D'); reg = next(r for r in area.regions if r.type == 'WINDOW')
    with bpy.context.temp_override(window=win, area=area, region=reg):
        bpy.ops.ww.play('INVOKE_DEFAULT')
    if '--demo' in ARGS: Demo(Path(arg('--demo'))).begin()
    return None


CLASSES = (WW_OT_play, WW_OT_do, WW_PT_panel)


def main():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    sc = bpy.context.scene
    for f in FONT_FILES:
        if Path(f).exists():
            fid = blf.load(f)
            if fid != -1: FONT['id'] = fid; break
    G.call({'op': 'site'})
    items = [(k, v['label'], ', '.join(v['observationIds']) or '沒有線索') for k, v in G.site['FIXTURES'].items()]
    bpy.types.Scene.ww_fixture = bpy.props.EnumProperty(name='線索', items=items, default='all', update=on_fixture)
    for c in CLASSES: bpy.utils.register_class(c)
    bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_PIXEL')
    fixture = arg('--fixture', 'all'); G.start(fixture); build_env(); rebuild()
    if fixture != 'all': sc['ww_fixture'] = list(G.site['FIXTURES']).index(fixture)
    bpy.app.timers.register(tick, first_interval=0.2, persistent=True)
    if bpy.app.background:
        return
    bpy.app.timers.register(start, first_interval=0.5)


# ============================================================================ scripted demo (operation recording)
class Demo:
    """Plays a fixed session through the same Game methods the mouse and keys use, saving window frames as it goes."""

    def __init__(self, out):
        self.out = out; self.frames = out / 'frames'; self.frames.mkdir(parents=True, exist_ok=True)
        for f in self.frames.glob('*.png'): f.unlink()
        self.n = 0; self.queue = []; self.shot_every = 0.25; self.until = 0; self.marks = []

    def add(self, secs, fn=None, mark=None):
        self.queue.append((secs, fn, mark))

    def begin(self):
        P = lambda x, y, t, r=0: (lambda: (setattr(G, 'sel', t), setattr(G, 'rot', r), setattr(G, 'cursor', [x, y]), G.click(x, y)))
        A = lambda a: (lambda: G.act(a))
        sc = bpy.context.scene
        self.add(2.0, lambda: setattr(sc, 'ww_fixture', 'two'), 'start_missed_nursery_clue')
        self.add(1.5, A({'op': 'direction', 'dir': 'restore_channel'}), 'direction_restore')
        self.add(1.2, P(3, 1, 'gate'), None)
        self.add(1.0, P(3, 2, 'worn'), None)
        self.add(2.5, P(3, 3, 'worn', 1), 'misconnection_port_named')
        self.add(2.0, lambda: (setattr(G, 'cursor', [3, 3]), G.click(3, 3)), 'rotated_fixed')
        self.add(1.0, P(3, 4, 'worn'), None)
        self.add(3.0, P(3, 5, 'apron'), 'water_reaches_fields')
        self.add(3.0, lambda: G.gate(3, 1), 'gate_closed')
        self.add(3.0, lambda: G.gate(3, 1), 'gate_open')
        self.add(3.0, G.finish, 'finish_direct')
        self.add(2.5, G.finish, 'finish_again_same_receipt')
        self.add(1.5, retry, 'retry')
        for y in (5, 4, 3, 2, 1): self.add(0.4, A({'op': 'remove', 'x': 3, 'y': y}))
        self.add(1.5, A({'op': 'undo'}), 'undo')
        self.add(1.5, A({'op': 'redo'}), 'redo')
        self.add(1.2, A({'op': 'direction', 'dir': 'protect_nursery'}), None)
        for x, y, t, r in [(3, 1, 'bendL', 0), (2, 1, 'straight', 1), (1, 1, 'bendR', 3), (1, 2, 'straight', 0), (1, 3, 'straight', 0), (1, 4, 'straight', 0)]:
            self.add(0.6, P(x, y, t, r))
        self.add(3.0, P(1, 5, 'apron'), 'detour_flowing')
        self.add(3.0, G.finish, 'finish_detour')
        self.add(1.0, retry)
        for y in (5, 4, 3, 2, 1): self.add(0.3, A({'op': 'remove', 'x': 1, 'y': y}))
        for x in (2, 3): self.add(0.3, A({'op': 'remove', 'x': x, 'y': 1}))
        self.add(1.2, A({'op': 'direction', 'dir': 'clear_silt'}), None)
        for x, y, t, r in [(3, 1, 'tee', 1), (2, 1, 'straight', 1), (1, 1, 'straight', 1), (0, 1, 'apron', 3), (3, 2, 'worn', 0), (3, 3, 'worn', 0), (3, 4, 'worn', 0)]:
            self.add(0.6, P(x, y, t, r))
        self.add(3.0, P(3, 5, 'apron'), 'divert_split_flowing')
        self.add(3.5, G.finish, 'finish_divert')
        self.next_at = time.monotonic() + 1.5; self.shot_at = time.monotonic() + 0.5
        bpy.app.timers.register(self.step, first_interval=0.1)

    def shot(self, name=None):
        win = bpy.context.window_manager.windows[0]
        path = self.frames / f'f{self.n:05d}.png'
        with bpy.context.temp_override(window=win):
            bpy.ops.screen.screenshot(filepath=str(path))
        if name: self.marks.append({'frame': self.n, 'mark': name, 'toast': G.toast[0]})
        self.n += 1

    def step(self):
        now = time.monotonic()
        if now >= self.shot_at: self.shot(); self.shot_at = now + self.shot_every
        if now < self.next_at: return 0.05
        if self.pending_mark: self.shot(self.pending_mark); self.pending_mark = None
        if not self.queue:
            (self.out / 'receipts.json').write_text(json.dumps(G.receipts, ensure_ascii=False, indent=2), encoding='utf-8')
            (self.out / 'marks.json').write_text(json.dumps(self.marks, ensure_ascii=False, indent=2), encoding='utf-8')
            bpy.ops.wm.quit_blender(); return None
        secs, fn, mark = self.queue.pop(0)
        if fn: fn()
        self.pending_mark = mark; self.next_at = now + secs
        return 0.05

    pending_mark = None


if __name__ == '__main__':
    main()
