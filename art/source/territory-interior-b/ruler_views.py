"""TerritoryInterior18 review sheets (00-overview 4.4): front, side, rear and 3/4, each with a 1.75 m figure and ruler.

Renders the v002 LOD0 (same mesh as v001) beside a plain 1.75 m stand-in figure and a ruler marked every 0.25 m.
Writes art/previews/territory-interior-b/<ID>/ruler_0N_<view>.png; the model files are not touched.

blender --background --factory-startup art/source/territory-interior-b/blend/<ID>_v002.blend --python ruler_views.py -- <ID> <repo>/art
"""
import bpy, bmesh, json, math, sys
from pathlib import Path
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index('--') + 1:]
AID, ART = argv[0], Path(argv[1])
KIT = 'territory-interior-b'
OUT = ART / 'previews' / KIT / AID
info = json.loads((ART / 'exports' / KIT / AID / 'model_info_v002.json').read_text(encoding='utf-8'))
HUMAN = 1.75
VIEWS = [('01_front', '正面', Vector((0, -1, 0))), ('02_side', '側面', Vector((1, 0, 0))),
         ('03_rear', '背面', Vector((0, 1, 0))), ('04_three_quarter', '3/4', Vector((1, -1, 0)).normalized())]

scene = bpy.context.scene
for img in bpy.data.images:                      # textures live next to the FBX
    if img.source == 'FILE' and img.filepath:
        p = ART / 'exports' / KIT / AID / 'Textures' / Path(bpy.path.abspath(img.filepath)).name
        if p.exists(): img.filepath = str(p); img.reload()
asset = [o for o in bpy.data.objects[AID].children if o.type == 'MESH' and o.name.endswith('_LOD0')]
for o in scene.objects: o.hide_render = o not in asset
lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
for o in asset:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
size = hi - lo; centre = (lo + hi) / 2


def mat(name, rgb, rough=.8, emit=0.):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*rgb, 1); b.inputs['Roughness'].default_value = rough
    if emit: b.inputs['Emission Color'].default_value = (*rgb, 1); b.inputs['Emission Strength'].default_value = emit
    return m


def solid(name, build, m):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); build(bm); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new(name, me); scene.collection.objects.link(o); me.materials.append(m); return o


grey, ink = mat('Figure', (.46, .48, .50)), mat('Ruler', (.85, .70, .38), .5)


def figure():
    """Plain 1.75 m stand-in: legs, body, arms, head (no face), feet on z = 0."""
    parts = []
    def cyl(name, r1, r2, z0, z1, x=0.):
        def b(bm):
            bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=r1, radius2=r2, depth=z1 - z0,
                                  matrix=Matrix.Translation((x, 0, (z0 + z1) / 2)))
        parts.append(solid(name, b, grey))
    for s in (-1, 1):
        cyl('Leg', .075, .065, 0, .86, s * .095)
        cyl('Arm', .05, .042, .80, 1.42, s * .25)
    cyl('Body', .19, .17, .82, 1.46)
    cyl('Neck', .05, .05, 1.44, 1.53)
    def head(bm): bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=.11, matrix=Matrix.Translation((0, 0, HUMAN - .11)))
    parts.append(solid('Head', head, grey))
    return parts


def ruler():
    parts = []
    def box(name, sx, sz, z, x=0.):
        def b(bm): bmesh.ops.create_cube(bm, size=1, matrix=Matrix.Translation((x, 0, z)) @ Matrix.Diagonal((sx, .02, sz, 1)))
        parts.append(solid(name, b, ink))
    box('RulerBar', .025, HUMAN, HUMAN / 2)
    for i in range(8):
        z = i * .25 if i < 7 else HUMAN
        box('Tick', .09 if i % 2 == 0 or i == 7 else .055, .012, z, .03)
    return parts


fig, rul = figure(), ruler()
font = None
for fp in ('C:/Windows/Fonts/msjh.ttc', 'C:/Windows/Fonts/msyh.ttc'):
    try: font = bpy.data.fonts.load(fp); break
    except Exception: pass
floor = solid('Floor', lambda bm: bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=30), mat('Floor', (.22, .22, .23), .95))

sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); scene.collection.objects.link(sun); sun.data.energy = 3.0
fill = bpy.data.objects.new('Fill', bpy.data.lights.new('Fill', 'SUN')); scene.collection.objects.link(fill); fill.data.energy = .9
w = bpy.data.worlds.new('Grey'); w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (.16, .17, .18, 1)
scene.world = w
cam_d = bpy.data.cameras.new('Cam'); cam_d.type = 'ORTHO'
cam = bpy.data.objects.new('Cam', cam_d); scene.collection.objects.link(cam); scene.camera = cam
scene.render.engine = 'BLENDER_EEVEE'; scene.render.resolution_x, scene.render.resolution_y = 1600, 1000
scene.view_settings.view_transform = 'Standard'
aspect = 1.6
OUT.mkdir(parents=True, exist_ok=True)
written = []

for key, zh, d in VIEWS:
    look = -d                                     # camera looks back at the model from direction d
    right = look.cross(Vector((0, 0, 1))).normalized()
    # half the model's width across this view, then the figure on the left with a gap
    half = max(abs((Vector((x, y, 0)) - Vector((centre.x, centre.y, 0))).dot(right))
               for x in (lo.x, hi.x) for y in (lo.y, hi.y))
    gap = max(.3, .25 * max(size.x, size.y))
    fpos = Vector((centre.x, centre.y, 0)) - right * (half + gap + .3)
    face = Matrix.Rotation(math.atan2(right.y, right.x), 4, 'Z')   # local x along the view's right: arms side by side, text facing the camera
    for o in fig: o.matrix_world = Matrix.Translation(fpos) @ face
    rpos = fpos - right * .42
    for o in rul: o.matrix_world = Matrix.Translation(rpos) @ face
    # label above the ruler
    for o in [o for o in scene.objects if o.name.startswith('Label')]: bpy.data.objects.remove(o, do_unlink=True)
    cu = bpy.data.curves.new('Label', 'FONT'); cu.body = '1.75 m'; cu.size = .1; cu.align_x = 'CENTER'
    if font: cu.font = font
    lab = bpy.data.objects.new('Label', cu); scene.collection.objects.link(lab); cu.materials.append(mat('LabelInk', (.95, .9, .8), emit=1.))
    lab.matrix_world = Matrix.Translation(rpos + Vector((0, 0, HUMAN + .06))) @ face @ Matrix.Rotation(math.radians(90), 4, 'X')
    cu2 = bpy.data.curves.new('LabelTitle', 'FONT'); cu2.body = f"{AID}  {info.get('name_zh', '')}  {zh}"; cu2.size = .12
    if font: cu2.font = font
    # frame: everything between the ruler and the model, floor to the taller of figure / model
    left = (rpos - centre).dot(right) - .25
    rgt = half + .15
    top = max(HUMAN + .2, size.z + .1)
    width = rgt - left; height = top + .25
    mid = Vector((centre.x, centre.y, 0)) + right * ((left + rgt) / 2) + Vector((0, 0, top / 2 - .05))
    elev = math.radians(8)
    view_dir = (d * math.cos(elev) + Vector((0, 0, math.sin(elev)))).normalized()
    cam.location = mid + view_dir * 20
    cam.rotation_euler = (-view_dir).to_track_quat('-Z', 'Y').to_euler()
    cam_d.ortho_scale = max(width, height * aspect) * 1.1
    title = bpy.data.objects.new('LabelTitle', cu2); scene.collection.objects.link(title); cu2.materials.append(mat('TitleInk', (.95, .9, .8), emit=1.))
    title.matrix_world = Matrix.Translation(mid + right * (-width / 2 + .05) + Vector((0, 0, top / 2 + .02))) @ face @ Matrix.Rotation(math.radians(90), 4, 'X')
    sun.rotation_euler = (-view_dir + Vector((0, 0, -1.2)) + right * .6).to_track_quat('-Z', 'Y').to_euler()   # from above, front-left
    fill.rotation_euler = (-view_dir + Vector((0, 0, -.5)) - right * .9).to_track_quat('-Z', 'Y').to_euler()   # front-right
    p = OUT / f'ruler_{key}.png'
    scene.render.filepath = str(p)
    bpy.ops.render.render(write_still=True)
    written.append(p.name)

(OUT / 'ruler_views.json').write_text(json.dumps({
    'asset': AID, 'model': f"{AID}_v002.fbx LOD0 (same mesh as v001)", 'figure_height_m': HUMAN,
    'ruler_ticks_m': .25, 'camera': 'orthographic, 8 deg above horizontal', 'views': written,
    'model_dimensions_m': [round(v, 3) for v in size]}, ensure_ascii=False, indent=2), encoding='utf-8')
print('RULER', AID, written, [round(v, 3) for v in size])
