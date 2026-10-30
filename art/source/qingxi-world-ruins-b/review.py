"""Review renders for qingxi-world-ruins-b (modeling-style-spec-v1 section 8): EEVEE, AgX Medium High Contrast,
front / side / rear orthographic and a 50 mm 3/4 view, each beside a 1.75 m stand-in figure and a ruler ticked
every 0.25 m; plus a LOD strip and optional close-ups. Renders the exported LOD meshes with baked textures.

Sky: the spec names the Poly Haven HDRI kloofendal_48d_partly_cloudy_puresky (CC0); it is not in the repo or on
this machine, so a physical sky (Nishita / multiple scattering) plus a sun stands in, identical for every asset.
"""
import bpy, bmesh, json, math
from mathutils import Vector, Matrix

HUMAN = 1.75
VIEWS = [('01_front', '正面', Vector((0, -1, 0)), 'ORTHO'), ('02_side', '側面', Vector((1, 0, 0)), 'ORTHO'),
         ('03_rear', '背面', Vector((0, 1, 0)), 'ORTHO'), ('04_three_quarter', '3/4', Vector((1, -1, 0)).normalized(), 'PERSP')]


def _font():
    for fp in ('C:/Windows/Fonts/msjh.ttc', 'C:/Windows/Fonts/msyh.ttc'):
        try: return bpy.data.fonts.load(fp, check_existing=True)
        except Exception: pass


def _mat(name, rgb, rough=.8, emit=0.):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*rgb, 1); b.inputs['Roughness'].default_value = rough
    if emit: b.inputs['Emission Color'].default_value = (*rgb, 1); b.inputs['Emission Strength'].default_value = emit
    return m


def _solid(col, name, build, m):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); build(bm); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new(name, me); col.objects.link(o); me.materials.append(m); return o


def setup(scene):
    col = bpy.data.collections.new('90_Review_Not_Exported'); scene.collection.children.link(col)
    scene.render.engine = 'BLENDER_EEVEE'
    try:
        scene.eevee.use_shadows = True; scene.eevee.use_raytracing = True
        scene.eevee.ray_tracing_options.resolution_scale = '1'
    except Exception: pass
    try: scene.eevee.taa_render_samples = 64
    except Exception: pass
    scene.view_settings.view_transform = 'AgX'; scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = -.5
    w = bpy.data.worlds.new('Review_Sky'); w.use_nodes = True; nt = w.node_tree
    sky = nt.nodes.new('ShaderNodeTexSky')
    for t in ('NISHITA', 'MULTIPLE_SCATTERING', 'SINGLE_SCATTERING'):
        try: sky.sky_type = t; break
        except Exception: pass
    for k, v in (('sun_elevation', math.radians(40)), ('sun_rotation', math.radians(215)), ('sun_disc', False)):
        try: setattr(sky, k, v)
        except Exception: pass
    nt.links.new(sky.outputs[0], nt.nodes['Background'].inputs[0]); nt.nodes['Background'].inputs[1].default_value = .09
    scene.world = w
    sun = bpy.data.objects.new('Review_Sun', bpy.data.lights.new('Review_Sun', 'SUN')); col.objects.link(sun)
    sun.data.energy = 5.0; sun.data.color = (1.0, .95, .88); sun.data.angle = math.radians(1.5); sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
    g = bpy.data.meshes.new('Review_Ground')
    g.from_pydata([(-60, -60, 0), (60, -60, 0), (60, 60, 0), (-60, 60, 0)], [], [(0, 1, 2, 3)])
    go = bpy.data.objects.new('Review_Ground', g); col.objects.link(go); g.materials.append(_mat('Review_Ground', (.16, .12, .08), .95))
    return col, sun


def aim_sun(sun, d):
    """Keep the key light in the same place relative to the camera for every view (front-left, 40 deg up), so the
    side and rear views are lit like the front one instead of standing in the house's own shadow."""
    yaw = math.atan2(d.y, d.x) - math.atan2(-1, 0)
    sun.rotation_euler = (math.radians(50), 0, math.radians(-35) + yaw)


def figure(col):
    grey, ink = _mat('Figure', (.3, .3, .3)), _mat('Ruler', (.85, .7, .38), .5)
    fig, rul = [], []
    def cyl(name, r1, r2, z0, z1, x=0.):
        def b(bm): bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=r1, radius2=r2, depth=z1 - z0,
                                         matrix=Matrix.Translation((x, 0, (z0 + z1) / 2)))
        fig.append(_solid(col, name, b, grey))
    for s in (-1, 1):
        cyl('Leg', .075, .065, 0, .86, s * .095); cyl('Arm', .05, .042, .80, 1.42, s * .25)
    cyl('Body', .19, .17, .82, 1.46); cyl('Neck', .05, .05, 1.44, 1.53)
    fig.append(_solid(col, 'Head', lambda bm: bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=.11,
                                                                       matrix=Matrix.Translation((0, 0, HUMAN - .11))), grey))
    def box(name, sx, sz, z, x=0.):
        rul.append(_solid(col, name, lambda bm: bmesh.ops.create_cube(bm, size=1, matrix=Matrix.Translation((x, 0, z)) @ Matrix.Diagonal((sx, .02, sz, 1))), ink))
    box('RulerBar', .025, HUMAN, HUMAN / 2)
    for i in range(8):
        z = i * .25 if i < 7 else HUMAN
        box('Tick', .09 if i % 2 == 0 or i == 7 else .055, .012, z, .03)
    return fig, rul


def bounds(objs):
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return lo, hi


def _text(col, body, size, M, font):
    cu = bpy.data.curves.new('Label', 'FONT'); cu.body = body; cu.size = size
    if font: cu.font = font
    t = bpy.data.objects.new('Label', cu); col.objects.link(t); cu.materials.append(_mat('LabelInk', (.95, .92, .84), emit=1.))
    t.matrix_world = M; return t


def render_all(AID, SPEC, lods, colls, out, fast=False):
    scene = bpy.context.scene
    out.mkdir(parents=True, exist_ok=True)
    col, sun = setup(scene)
    font = _font()
    model = [lods[0]]
    for o in scene.objects:
        if o.type in ('MESH', 'FONT') and o not in model and o.name not in ('Review_Ground',): o.hide_render = True
    fig, rul = figure(col)
    lo, hi = bounds(model); size = hi - lo; centre = (lo + hi) / 2
    cam = bpy.data.objects.new('Review_Cam', bpy.data.cameras.new('Review_Cam')); col.objects.link(cam); scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = (1600, 1000) if not fast else (800, 500)
    aspect = 1.6; written = []
    for key, zh, d, proj in VIEWS:
        aim_sun(sun, d)
        right = (-d).cross(Vector((0, 0, 1))).normalized()
        half = max(abs((Vector((x, y, 0)) - Vector((centre.x, centre.y, 0))).dot(right)) for x in (lo.x, hi.x) for y in (lo.y, hi.y))
        gap = max(.3, .15 * max(size.x, size.y))
        fpos = Vector((centre.x, centre.y, 0)) - right * (half + gap + .3)
        face = Matrix.Rotation(math.atan2(right.y, right.x), 4, 'Z')
        for o in fig: o.matrix_world = Matrix.Translation(fpos) @ face
        rpos = fpos - right * .42
        for o in rul: o.matrix_world = Matrix.Translation(rpos) @ face
        for o in [o for o in col.objects if o.name.startswith('Label')]: bpy.data.objects.remove(o, do_unlink=True)
        left = (rpos - centre).dot(right) - .25; rgt = half + .2
        top = max(HUMAN + .55, hi.z + .45); bottom = min(0, lo.z) - .1
        width = rgt - left; height = top - bottom
        mid = Vector((centre.x, centre.y, 0)) + right * ((left + rgt) / 2) + Vector((0, 0, (top + bottom) / 2))
        _text(col, '1.75 m', .1, Matrix.Translation(rpos + Vector((0, 0, HUMAN + .06))) @ face @ Matrix.Rotation(math.radians(90), 4, 'X'), font)
        _text(col, f"{AID}  {SPEC['zh']}  {zh}", min(.14, width * .025), Matrix.Translation(mid + right * (-width / 2 + .05) + Vector((0, 0, height / 2 - .16)))
              @ face @ Matrix.Rotation(math.radians(90), 4, 'X'), font)
        if proj == 'ORTHO':
            cam.data.type = 'ORTHO'
            vd = (d * math.cos(math.radians(6)) + Vector((0, 0, math.sin(math.radians(6))))).normalized()
            cam.location = mid + vd * 40; cam.data.ortho_scale = max(width, height * aspect) * 1.08
            cam.data.clip_end = 200
        else:
            cam.data.type = 'PERSP'; cam.data.lens = 50
            vd = (d * math.cos(math.radians(18)) + Vector((0, 0, math.sin(math.radians(18))))).normalized()
            fov = 2 * math.atan(36 / 2 / 50)
            dist = max(width, height * aspect) * 1.12 / (2 * math.tan(fov / 2))
            cam.location = mid + vd * dist
        cam.rotation_euler = (-vd).to_track_quat('-Z', 'Y').to_euler()
        p = out / f'review_{key}.png'; scene.render.filepath = str(p); bpy.ops.render.render(write_still=True); written.append(p.name)
    for o in fig + rul + [o for o in col.objects if o.name.startswith('Label')]: o.hide_render = True
    # hero 3/4 and close-ups
    cam.data.type = 'PERSP'; cam.data.lens = 50
    for name, d, margin, aim in [('hero', SPEC.get('hero', (.75, -1, .45)), 1.05, None)] + list(SPEC.get('closeups', [])):
        if aim is None: c, ext = centre, size.length
        else: c, ext = Vector(aim[0]), aim[1]
        vd = Vector(d).normalized(); fov = 2 * math.atan(24 / 2 / 50)
        aim_sun(sun, Vector((vd.x, vd.y, 0)))
        cam.location = c + vd * ext * margin / (2 * math.tan(fov / 2)); cam.rotation_euler = (-vd).to_track_quat('-Z', 'Y').to_euler()
        p = out / f'{name}.png'; scene.render.filepath = str(p); bpy.ops.render.render(write_still=True); written.append(p.name)
    # LOD strip: LOD0 / LOD1 / LOD2 side by side, same scale
    shown = []
    step = size.x * 1.15 + .3
    for k in (0, 1, 2):
        o = lods[k]; d = o.copy(); col.objects.link(d); d.parent = None; d.matrix_world = Matrix.Translation(((k - 1) * step, 0, 0)) @ o.matrix_world
        d.hide_render = False; shown.append(d)
        n = sum(len(p.vertices) - 2 for p in o.data.polygons)
        _text(col, f'LOD{k}  {n:,} tris', max(.1, size.x * .07), Matrix.Translation(((k - 1) * step - size.x * .35, lo.y - .2, hi.z + .15)) @ Matrix.Rotation(math.radians(90), 4, 'X'), font)
    lods[0].hide_render = True
    sl, sh = bounds(shown); sc = (sl + sh) / 2
    cam.data.type = 'ORTHO'; vd = Vector((.25, -1, .3)).normalized(); cam.location = sc + vd * 60
    aim_sun(sun, Vector((0, -1, 0)))
    cam.rotation_euler = (-vd).to_track_quat('-Z', 'Y').to_euler(); cam.data.ortho_scale = (sh.x - sl.x) * 1.05 + .3
    p = out / 'lod_strip.png'; scene.render.filepath = str(p); bpy.ops.render.render(write_still=True); written.append(p.name)
    for d in shown: bpy.data.objects.remove(d, do_unlink=True)
    lods[0].hide_render = False
    (out / 'review.json').write_text(json.dumps({
        'asset': AID, 'renders': written, 'engine': 'EEVEE', 'colour': 'AgX Medium High Contrast, exposure -0.5',
        'sky': 'Nishita physical sky + sun 5.0 (sun turned with each camera: front-left key in every view), sky strength 0.09, earth-brown ground (HDRI from spec not available locally)', 'figure_height_m': HUMAN,
        'ruler_ticks_m': .25, 'model': 'exported LOD0 with baked textures', 'model_size_m': [round(v, 3) for v in size]},
        ensure_ascii=False, indent=2), encoding='utf-8')
    return written
