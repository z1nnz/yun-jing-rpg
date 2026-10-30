"""Fast look-dev render of an asset with its live procedural materials (no bake, nothing exported).

blender -b --factory-startup --python quicklook.py -- <ASSET_ID> <out_dir> [chain]
`chain` also renders the piece repeated along its interfaces (start-to-end) to check that joints are seamless.
"""
import bpy, sys, math
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from mathutils import Vector, Matrix
import wr_core as C
import assets as A

argv = sys.argv[sys.argv.index('--') + 1:]
AID, OUT = argv[0], Path(argv[1]); CHAIN = 'chain' in argv
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
C.reset_state(AID)
spec = A.ASSETS[AID]
spec['build']()
bpy.context.view_layer.update()
C.write_grain_attributes()
parts = [o for o in C.S['parts'] if o.type == 'MESH']


def setup_render(samples=64):
    scene.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for kind in ('OPTIX', 'CUDA'):
        try:
            prefs.compute_device_type = kind; prefs.get_devices()
            if any(d.type == kind for d in prefs.devices):
                for d in prefs.devices: d.use = d.type == kind
                scene.cycles.device = 'GPU'; break
        except Exception: pass
    scene.cycles.samples = samples; scene.cycles.use_denoising = True
    scene.view_settings.view_transform = 'AgX'; scene.view_settings.look = 'AgX - Medium High Contrast'; scene.view_settings.exposure = -.6
    w = bpy.data.worlds.new('Sky'); w.use_nodes = True; nt = w.node_tree
    sky = nt.nodes.new('ShaderNodeTexSky')
    for t in ('NISHITA', 'SINGLE_SCATTERING', 'MULTIPLE_SCATTERING'):
        try: sky.sky_type = t; break
        except Exception: pass
    try: sky.sun_elevation = math.radians(38); sky.sun_rotation = math.radians(210); sky.sun_disc = False
    except Exception: pass
    nt.links.new(sky.outputs[0], nt.nodes['Background'].inputs[0]); nt.nodes['Background'].inputs[1].default_value = .22
    scene.world = w
    sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); scene.collection.objects.link(sun)
    sun.data.energy = 3.2; sun.data.angle = math.radians(2); sun.rotation_euler = (math.radians(52), 0, math.radians(-35))
    g = bpy.data.meshes.new('Ground'); g.from_pydata([(-40, -40, 0), (40, -40, 0), (40, 40, 0), (-40, 40, 0)], [], [(0, 1, 2, 3)])
    go = bpy.data.objects.new('Ground', g); scene.collection.objects.link(go)
    gm = bpy.data.materials.new('G'); gm.use_nodes = True
    gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.09, .1, .065, 1)
    gm.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .95
    g.materials.append(gm)


def bounds(objs):
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return lo, hi


def shoot(name, objs, d, lens=50, margin=1.15, res=(1600, 1000)):
    lo, hi = bounds(objs); c = (lo + hi) / 2; ext = (hi - lo).length
    cam = scene.camera
    if cam is None:
        cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); scene.collection.objects.link(cam); scene.camera = cam
    cam.data.lens = lens
    dist = ext * margin / (2 * math.tan(cam.data.angle / 2) * res[1] / res[0])   # fit the shorter (vertical) side
    cam.location = c + Vector(d).normalized() * dist
    cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.filepath = str(OUT / f'{AID}_{name}.png'); bpy.ops.render.render(write_still=True)


setup_render()
shoot('front34', parts, (.55, -1, .38))
shoot('rear34', parts, (-.5, 1, .45))
shoot('close', parts, (.25, -1, .2), lens=50, margin=.55)
if CHAIN and 'end' in spec.get('interfaces', {}):
    itf = spec['interfaces']; s, e = Vector(itf['start']['centre']), Vector(itf['end']['centre'])
    ds, de = Vector(itf['start']['direction']), Vector(itf['end']['direction'])
    # place copy k so that its start interface sits on the end interface of copy k-1
    M = Matrix.Identity(4); copies = list(parts)
    rot = (Vector(ds).to_track_quat('X', 'Z').inverted() @ Vector(de).to_track_quat('X', 'Z')).to_matrix().to_4x4()
    step = Matrix.Translation(e) @ rot @ Matrix.Translation(-s)
    for k in range(2):
        M = M @ step
        for o in parts:
            d = o.copy(); d.data = o.data; scene.collection.objects.link(d); d.matrix_world = M @ o.matrix_world; copies.append(d)
    shoot('chain', copies, (.35, -1, .42), margin=1.0)
    shoot('chain_joint', copies, (.12, -1, .1), margin=.42)
if CHAIN and 'StraightOf' in spec:
    pass
print('QUICKLOOK_DONE', AID, len(parts), sum(len(p.data.polygons) for p in parts))
