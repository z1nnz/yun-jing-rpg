"""Scale and style comparison renders: this kit's exported LOD0 meshes lined up beside the project's existing
assets (StarterHouse_v004, StoneArchBridge_v001, CommonPine, BambooClump, MossBoulderSet) and the 1.75 m figure.
Same EEVEE look as review.py. Nothing here is exported.

blender -b --factory-startup --python compare.py
Writes art/previews/qingxi-world-ruins-b/_compare/*.png.
"""
import bpy, sys, math
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from mathutils import Vector, Matrix
import review as R

ROOT = HERE.parents[2]
EXP = ROOT / 'art/exports/qingxi-world-ruins-b'
INC = ROOT / 'art/incoming/dondon'
OUT = ROOT / 'art/previews/qingxi-world-ruins-b/_compare'
OURS = {k: EXP / k / f'{k}_v001.glb' for k in (
    'H01_StoneTimberHouse', 'H02_RammedEarthHouse', 'H03_BambooWeaveHouse', 'H04_StrawThatchHouse', 'H05_LimewashAnnexHouse',
    'H06_RustShingleHouse', 'H07_DarkFrameHouse', 'H08_SandStonePlasterHouse', 'D3_AbandonedHut', 'D3_DryWell',
    'A2_OverturnedCart', 'R01_DryStoneWall_Straight', 'R01_DryStoneWall_Collapsed', 'R02_BambooFence_Straight',
    'R02_BambooFence_Leaning', 'R03_FirewoodNeat', 'R03_FirewoodScattered', 'R04_StoneLanternIntact',
    'R04_StoneLanternBroken', 'R05_Milestone')}
THEIRS = {k: INC / k / v / f'{k}_{v}.fbx' for k, v in (
    ('StarterHouse', 'v004'), ('StoneArchBridge', 'v001'), ('CommonPine', 'v001'), ('BambooClump', 'v001'), ('MossBoulderSet', 'v001'))}
LABEL = {'StarterHouse': 'StarterHouse_v004（既有）', 'StoneArchBridge': 'StoneArchBridge_v001（既有）',
         'CommonPine': 'CommonPine（既有）', 'BambooClump': 'BambooClump（既有）', 'MossBoulderSet': 'MossBoulderSet（既有）'}


def load(key):
    before = set(bpy.data.objects)
    if key in OURS: bpy.ops.import_scene.gltf(filepath=str(OURS[key]))
    else: bpy.ops.import_scene.fbx(filepath=str(THEIRS[key]))
    new = [o for o in bpy.data.objects if o not in before]
    keep = []
    for o in new:
        n = o.name.lower()
        drop = o.type != 'MESH' or 'collision' in n or 'lod1' in n or 'lod2' in n or n.startswith(('ucx_', 'ubx_'))
        if drop: o.hide_render = True; o.hide_viewport = True
        else: keep.append(o)
    bpy.context.view_layer.update()
    lo, hi = R.bounds(keep)
    if (hi - lo).length > 200:                      # centimetre FBX
        for o in new:
            if o.parent is None: o.matrix_world = Matrix.Scale(.01, 4) @ o.matrix_world
        bpy.context.view_layer.update(); lo, hi = R.bounds(keep)
    roots = [o for o in new if o.parent is None]
    return keep, roots, lo, hi


def row(name, keys, gap=.6, view=(.3, -1, .26), label=.3):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.resolution_x, scene.render.resolution_y = 2400, 1100
    col, sun = R.setup(scene)
    g = bpy.data.objects['Review_Ground']; g.scale = (8, 8, 1)     # no ground edge in long rows
    font = R._font()
    fig, rul = R.figure(col)
    x = 0.0
    fl, fh = R.bounds(fig + rul)
    for o in fig + rul: o.matrix_world = Matrix.Translation((-fl.x, 0, 0)) @ o.matrix_world
    x = fh.x - fl.x + gap
    allk = list(fig + rul); n_done = 0; stagger = True
    for key in keys:
        keep, roots, lo, hi = load(key)
        # well: its shaft is modelled below ground; show it standing on the ground plane as placed in the game
        dx = x - lo.x; dy = -(lo.y + hi.y) / 2
        for o in roots: o.matrix_world = Matrix.Translation((dx, dy, 0)) @ o.matrix_world
        bpy.context.view_layer.update()
        lo, hi = R.bounds(keep)
        R._text(col, LABEL.get(key, key), label, Matrix.Translation((lo.x, lo.y - .25 - label * 1.6 * (n_done % 2 if stagger else 0) - label, .01)), font)
        allk += keep; x = hi.x + gap; n_done += 1
    lo, hi = R.bounds(allk)
    lo.z = 0
    vd = Vector(view).normalized()
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); col.objects.link(cam); scene.camera = cam
    cam.data.type = 'ORTHO'
    mid = (lo + hi) / 2
    cam.location = mid + vd * 80; cam.rotation_euler = (-vd).to_track_quat('-Z', 'Y').to_euler()
    cam.data.clip_end = 300
    aspect = scene.render.resolution_x / scene.render.resolution_y
    cam.data.ortho_scale = max(hi.x - lo.x + 1.2, (hi.z - lo.z + 2.2) * aspect)
    R.aim_sun(sun, Vector((vd.x, vd.y, 0)))
    OUT.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(OUT / f'{name}.png'); bpy.ops.render.render(write_still=True)
    print('WROTE', name)


row('compare_houses_a', ['StarterHouse', 'H01_StoneTimberHouse', 'H02_RammedEarthHouse', 'H03_BambooWeaveHouse',
                         'H04_StrawThatchHouse'], gap=1.0, label=.32)
row('compare_houses_b', ['StarterHouse', 'H05_LimewashAnnexHouse', 'H06_RustShingleHouse', 'H07_DarkFrameHouse',
                         'H08_SandStonePlasterHouse', 'D3_AbandonedHut'], gap=1.0, label=.32)
row('compare_scenes', ['StoneArchBridge', 'D3_AbandonedHut', 'D3_DryWell', 'A2_OverturnedCart', 'CommonPine'], gap=.9, label=.26)
row('compare_boundaries', ['MossBoulderSet', 'R01_DryStoneWall_Straight', 'R01_DryStoneWall_Collapsed', 'R02_BambooFence_Straight',
                           'R02_BambooFence_Leaning', 'BambooClump'], gap=.6, label=.17)
row('compare_props', ['MossBoulderSet', 'R03_FirewoodNeat', 'R03_FirewoodScattered', 'R04_StoneLanternIntact',
                      'R04_StoneLanternBroken', 'R05_Milestone'], gap=.6, label=.11)
