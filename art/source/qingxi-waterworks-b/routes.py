"""Route renders for the Qingxi waterworks B kit. Imports the exported GLBs, snaps each piece port-to-port from its
model_info.json (no hand placement), and renders labelled route images: segment IDs, joint labels in mm / cm,
flow arrows and a 1.75 m figure. A route can be rendered with one joint broken to show the break hint.

    blender -b --python routes.py -- R1 [R2 ...] [--no-render]
"""
import bpy, bmesh, sys, json, math
from pathlib import Path
from mathutils import Vector, Matrix
sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_lib as Q
import ww_lib as W

OUT = Q.PREVIEWS / 'routes'
FONTS = [Path('C:/Windows/Fonts/msjhbd.ttc'), Path('C:/Windows/Fonts/NotoSansTC-VF.ttf')]
GASKET_MM = 20

# chain entries: (segment id, asset key, port joined to the previous piece, port leading on); the first piece takes a yaw
ROUTES = {
    'R1': dict(title='路線一  直通村田', file='R1_direct_fields', yaw=math.pi / 2, chain=[
        ('S01', 'B01_SourcePlinth', None, 'Out_Front'),
        ('S02', 'B02_StraightTrough', 'End_Back', 'End_Front'),
        ('S03', 'B05_SluiceGate', 'In_Back', 'Out_Front'),
        ('S04', 'B02-V02_WornStraight', 'End_Back', 'End_Front'),
        ('S05', 'B03_CornerTrough', 'In_Front', 'Out_Right'),
        ('S06', 'B02-V04_ShortCoupler', 'End_Front', 'End_Back'),
        ('S07', 'B02_StraightTrough', 'End_Front', 'End_Back'),
        ('S08', 'B02-V05_SpillApron', 'In_Back', None)],
        mounts=[('S03', 'WheelMount', 'B06_GateWheel', 'S03W')], gate_open=True, figure=('S03', (1.15, -0.04)), operator=('S03', (2.2, -1.9, 1.70), (0.55, 0.0, 0.85)),
        breaks=[dict(after='S04', gap=0.15, fix='把 S05 拖回 S04 End_Front，接口自動吸附')]),
}


def ang(v):
    return math.atan2(v.y, v.x)


def info(key):
    return json.loads((Q.EXPORTS / key / f'{key}_model_info.json').read_text(encoding='utf-8'))


def import_piece(seg, key):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(Q.EXPORTS / key / f'{key}.glb'))
    new = [o for o in bpy.data.objects if o not in before]
    root = bpy.data.objects.new(f'SEG_{seg}', None); bpy.context.scene.collection.objects.link(root)
    for o in new:
        if o.parent is None or o.parent not in new:
            o.parent = root; o.matrix_parent_inverse = Matrix.Identity(4)
    return root, new


def port(mi, name):
    p = next(p for p in mi['ports'] if p['name'] == name)
    return Vector(p['position']), Vector(p['normal'])


def snap(T_prev, mi_prev, out_name, mi, in_name):
    """World matrix that puts `in_name` of this piece face to face on `out_name` of the previous piece."""
    pa, na = port(mi_prev, out_name); pa = T_prev @ pa; na = (T_prev.to_3x3() @ na).normalized()
    pb, nb = port(mi, in_name)
    R = Matrix.Rotation(ang(-na) - ang(nb), 4, 'Z')
    return Matrix.Translation(pa - R @ pb) @ R, pa, na


# ----------------------------------------------------------------------------- annotation
def mat_emit(name, col, strength=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    e = nt.nodes.new('ShaderNodeEmission'); e.inputs['Color'].default_value = (*col, 1); e.inputs['Strength'].default_value = strength
    o = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(e.outputs[0], o.inputs[0]); return m


def font():
    for f in FONTS:
        if f.exists():
            try: return bpy.data.fonts.load(str(f))
            except RuntimeError: pass
    return None


class Notes:
    def __init__(self):
        self.font = font(); self.objs = []; self.billboards = []
        self.ink = mat_emit('N_Ink', (0.02, 0.02, 0.02)); self.paper = mat_emit('N_Paper', (0.95, 0.93, 0.88), 1.0)
        self.red = mat_emit('N_Red', (0.85, 0.06, 0.04), 1.6); self.green = mat_emit('N_Green', (0.10, 0.55, 0.20), 1.4)
        self.blue = mat_emit('N_Blue', (0.15, 0.55, 0.95), 2.2); self.redink = mat_emit('N_RedInk', (0.70, 0.02, 0.02))

    def _link(self, o):
        bpy.context.scene.collection.objects.link(o); o.visible_shadow = False; self.objs.append(o); return o

    def text(self, body, loc, size=0.07, ink=None, align='CENTER', board=True, plate=True):
        cu = bpy.data.curves.new('N_txt', 'FONT'); cu.body = body; cu.size = size; cu.align_x = align; cu.align_y = 'CENTER'
        if self.font: cu.font = self.font
        o = self._link(bpy.data.objects.new('N_Text', cu)); o.location = loc; cu.materials.append(ink or self.ink)
        if plate:
            bpy.context.view_layer.update(); w, h = o.dimensions.x + size * 0.8, o.dimensions.y + size * 0.6
            x0 = {'CENTER': -w / 2, 'LEFT': -size * 0.4, 'RIGHT': -w + size * 0.4}[align]
            me = bpy.data.meshes.new('N_plate'); me.from_pydata([(x0, -h / 2, -0.002), (x0 + w, -h / 2, -0.002), (x0 + w, h / 2, -0.002), (x0, h / 2, -0.002)], [], [(0, 1, 2, 3)])
            p = self._link(bpy.data.objects.new('N_Plate', me)); p.data.materials.append(self.paper); p.parent = o
        if board: self.billboards.append(o)
        return o

    def stick(self, a, b, mat=None, r=0.006):
        o = Q.rod('N_Stick', a, b, r, mat or self.ink, segs=8); o.visible_shadow = False; self.objs.append(o); return o

    def ring(self, loc, n, mat, R=0.40):
        """Ring standing in the joint plane (axis along the flow), framing the trough section."""
        o = Q.torus('N_Ring', R, 0.012, loc, mat, 48, 8); o.rotation_euler = Vector(n).to_track_quat('Z', 'Y').to_euler()
        o.visible_shadow = False; self.objs.append(o); return o

    def arrow(self, loc, d, mat=None, L=0.20):
        """Flat chevron lying on the water surface, pointing along d."""
        d = Vector((d.x, d.y, 0)).normalized(); s = Vector((-d.y, d.x, 0)); w = 0.07
        pts = [-d * L / 2 + s * w, d * L / 2, -d * L / 2 - s * w, -d * L / 4]
        me = bpy.data.meshes.new('N_arrow'); me.from_pydata([tuple(Vector(loc) + p) for p in pts], [], [(0, 1, 3), (1, 2, 3)])
        o = self._link(bpy.data.objects.new('N_Arrow', me)); o.data.materials.append(mat or self.blue); return o

    def face(self, cam):
        for o in self.billboards: o.rotation_euler = cam.matrix_world.to_euler()


def figure(loc):
    """Plain 1.75 m figure for scale (feet at loc): legs, torso, arms, head."""
    m = Q.m_simple('N_Figure', (0.33, 0.35, 0.38), rough=0.7); x, y, z = loc; out = []
    for s in (-1, 1):
        out.append(Q.rod('N_FigLeg', (x + s * 0.09, y, z), (x + s * 0.09, y, z + 0.88), 0.065, m, segs=12, bevel=0.02))
        out.append(Q.rod('N_FigArm', (x + s * 0.23, y, z + 1.44), (x + s * 0.25, y, z + 0.82), 0.045, m, segs=12, bevel=0.015))
    out.append(Q.rod('N_FigBody', (x, y, z + 0.86), (x, y, z + 1.48), 0.17, m, segs=16, bevel=0.06))
    out.append(Q.rod('N_FigNeck', (x, y, z + 1.46), (x, y, z + 1.53), 0.05, m, segs=12))
    hd = Q.lathe('N_FigHead', [(0, 0)] + [(0.11 * math.sin(math.pi * i / 10), 0.22 * (1 - math.cos(math.pi * i / 10)) / 2) for i in range(1, 10)] + [(0, 0.22)], m, segs=20)
    hd.location = (x, y, z + 1.53); out.append(hd)
    return out


def spill(p, n, mats):
    """Leak at an open joint: a sheet falling from the port lip to the ground and a puddle."""
    t = Vector((-n.y, n.x, 0)); bm = bmesh.new(); rows = []
    for i in range(7):
        s = i / 6; c = p + n * (0.13 * s) + Vector((0, 0, W.WATER_Z - (W.WATER_Z - 0.004) * s * s))
        rows.append([bm.verts.new(c + t * k) for k in (-0.19, 0.0, 0.19)])
    for a, b in zip(rows, rows[1:]):
        for j in range(2): bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))
    sheet = Q._obj('N_Spill', bm, mats['water'], smooth=True, sharp=80)
    c = p + n * 0.20
    pud = W.water_plane('N_Puddle', [(c.x + 0.42 * math.cos(a) * (1 + 0.15 * math.sin(3 * a)), c.y + 0.32 * math.sin(a)) for a in (i * math.tau / 20 for i in range(20))], z=0.004)
    return [sheet, pud]


# ----------------------------------------------------------------------------- build + render
def build(rid, broken=None):
    R = ROUTES[rid]; Q.reset(); W.begin(); mats = W.mats(); notes = Notes()
    T = Matrix.Rotation(R.get('yaw', 0.0), 4, 'Z'); segs = {}; mis = {}; joints = []; prev = None; downstream = False
    for seg, key, pin, pout in R['chain']:
        mi = info(key); root, objs = import_piece(seg, key)
        if prev:
            T, pa, na = snap(segs[prev[0]]['T'], mis[prev[0]], prev[1], mi, pin)
            brk = broken and broken['after'] == prev[0]
            if brk:
                T = Matrix.Translation(na * broken['gap']) @ T; downstream = True
            joints.append(dict(id=f'J{len(joints) + 1}', a=prev[0], a_port=prev[1], b=seg, b_port=pin, pos=pa, n=na, broken=bool(brk)))
        root.matrix_world = T; segs[seg] = dict(T=T.copy(), key=key, root=root, objs=objs, dry=downstream); mis[seg] = mi
        prev = (seg, pout)
    for seg, sock, key, mid in R.get('mounts', []):
        s = next(s for s in mis[seg].get('sockets', []) if s['name'] == sock)
        root, objs = import_piece(mid, key); T = segs[seg]['T'] @ Matrix.Translation(Vector(s['position']))
        root.matrix_world = T; segs[mid] = dict(T=T, key=key, root=root, objs=objs, dry=False, mount_of=seg); mis[mid] = info(key)
    bpy.context.view_layer.update()
    sc = bpy.context.scene; sc.frame_set(mis['S03']['animation']['frames'] if R.get('gate_open') and 'S03' in mis else 1)
    for seg, d in segs.items():
        if d['dry']:
            for o in d['objs']:
                if 'Water' in o.name: o.hide_render = True
    # notes: segment tags, joints, arrows, figure, leak
    for seg, d in segs.items():
        if d.get('mount_of'): continue
        mesh = [o for o in d['objs'] if o.type == 'MESH' and 'Water' not in o.name]
        mn, mx = Q.bbox(mesh); top = Vector(((mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, mx[2]))
        tag = notes.text(f"{seg}  {d['key'].split('_')[0]}", top + Vector((0, 0, 0.55)), 0.075)
        notes.stick(top + Vector((0, 0, 0.02)), top + Vector((0, 0, 0.50)))
        if not d['dry']:
            mi = mis[seg]
            for p in mi['ports']:
                c = d['T'] @ Vector(p['position']); n = (d['T'].to_3x3() @ Vector(p['normal'])).normalized()
                flow_in = any(j['b'] == seg and j['b_port'] == p['name'] for j in joints) or (seg == R['chain'][0][0])
                at = c - n * 0.16 + Vector((0, 0, W.WATER_Z + 0.006))
                notes.arrow(at, -n if flow_in else n)
    for i, j in enumerate(joints):   # joint labels alternate sides so neighbours do not collide
        p = j['pos']; side = Vector((-j['n'].y, j['n'].x, 0)) * (0.75 if i % 2 == 0 else -0.75)
        notes.ring(p + Vector((0, 0, 0.20)), j['n'], notes.red if j['broken'] else notes.green)
        if j['broken']:
            body = (f"{j['id']}  斷開 {round(broken['gap'] * 1000)} mm\n{j['a']} {j['a_port']} 未接上 {j['b']} {j['b_port']}\n修正：{broken['fix']}")
            notes.text(body, p + side + Vector((0, 0, 0.95)), 0.07, ink=notes.redink)
            notes.stick(p + Vector((0, 0, 0.42)), p + side + Vector((0, 0, 0.80)), notes.red)
            for o in spill(p, j['n'], mats): sc.collection.objects.link(o) if not o.users_collection else None
        else:
            notes.text(f"{j['id']}  間隙 0 mm · 墊片 {GASKET_MM} mm\n水面 28 cm · 槽寬 40 cm", p + side * 0.9 + Vector((0, 0, 0.72)), 0.062)
            notes.stick(p + Vector((0, 0, 0.42)), p + side * 0.9 + Vector((0, 0, 0.62)), r=0.004)
    allm = [o for d in segs.values() for o in d['objs'] if o.type == 'MESH']
    seg, off = R.get('figure', (None, None))   # stand the figure on the bank by the operating point
    at = segs[seg]['T'] @ Vector((off[0], off[1], 0)) if seg else Vector((Q.bbox(allm)[1][0] + 0.6, 0, 0))
    fig = figure((at.x, at.y, 0)); notes.text('1.75 m', Vector((at.x, at.y, 1.95)), 0.08)
    return R, segs, joints, notes, allm + fig


def frame(notes, objs, yaw, pitch, lens, title, legend, res=(1920, 1080), margin=1.05):
    sc = bpy.context.scene; sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    cam = Q.camera_fit(objs, yaw, pitch, lens=lens, margin=margin); notes.face(cam)
    old = [o for o in notes.objs if o.name.startswith('N_Cam')]   # drop the previous frame's title before it dangles
    notes.objs[:] = [o for o in notes.objs if o not in old]; notes.billboards[:] = [o for o in notes.billboards if o not in old]
    for o in old: bpy.data.objects.remove(o)
    hw = 18 / lens; hh = hw * res[1] / res[0]
    for body, y, size in ((title, hh * 0.86, hw * 0.055), (legend, -hh * 0.88, hw * 0.028)):
        t = notes.text(body, (0, 0, 0), size, align='LEFT', board=False); t.name = 'N_CamText'
        t.parent = cam; t.matrix_parent_inverse = Matrix.Identity(4); t.location = (-hw * 0.95, y, -1.0); t.rotation_euler = (0, 0, 0)
    return cam


def render(path, samples=96):
    sc = bpy.context.scene; sc.cycles.samples = samples; sc.render.filepath = str(path); sc.render.image_settings.file_format = 'PNG'
    Path(path).parent.mkdir(parents=True, exist_ok=True); bpy.ops.render.render(write_still=True); print('wrote', path)


LEGEND = '藍箭頭＝水流方向　綠環＝接口正常　紅環＝斷接　間隙 / 墊片單位 mm，水面 / 槽寬單位 cm　接口詳見 interfaces.json'

if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    for rid in [a for a in argv if not a.startswith('--')] or sorted(ROUTES):
        R = ROUTES[rid]
        for brk in [None] + R.get('breaks', []):
            R_, segs, joints, notes, objs = build(rid, brk)
            Q.gpu(bpy.context.scene, 96); Q.studio('stylized')
            tag = 'break' if brk else 'flow'
            sub = '（斷接提示）' if brk else '（閘門開，水流通）'
            frame(notes, objs, 14, 42, 35, R['title'] + sub, LEGEND, margin=0.98)
            if '--no-render' not in argv: render(OUT / f"{R['file']}_{tag}.png")
            if not brk and '--no-render' not in argv:
                frame(notes, objs, 0, 89, 35, R['title'] + '（俯視）', LEGEND)
                render(OUT / f"{R['file']}_top.png", 64)
                if R.get('operator'):   # 1.70 m eye height from the bank, behind the figure at the gate wheel
                    seg, eye, look = R['operator']; T = segs[seg]['T']; cam = frame(notes, objs, 14, 42, 30, R['title'] + '（岸上操作者視角，眼高 1.70 m）', LEGEND)
                    cam.location = T @ Vector(eye); cam.rotation_euler = (T @ Vector(look) - cam.location).to_track_quat('-Z', 'Y').to_euler()
                    notes.face(cam); render(OUT / f"{R['file']}_operator.png", 96)
            print(rid, tag, 'joints', [(j['id'], j['a'], j['b'], j['broken']) for j in joints])
