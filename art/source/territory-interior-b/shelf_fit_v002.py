"""TI01 v002: the v001 shelf slot test (BVH overlap of a test block resting 2 mm above each SOCKET_slot_N)
run again on the v002 LODs; the result is added to validation_v002.json.

blender --background --factory-startup art/source/territory-interior-b/blend/TI01_BoguShelf_v002.blend --python shelf_fit_v002.py -- <repo>/art
"""
import bpy, json, sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ART = Path(sys.argv[sys.argv.index('--') + 1])
VAL = ART / 'exports' / 'territory-interior-b' / 'TI01_BoguShelf' / 'validation_v002.json'
root = bpy.data.objects['TI01_BoguShelf']
meshes = {lv: [o for o in root.children if o.type == 'MESH' and o.name.endswith(f'_LOD{lv}')] for lv in (0, 1, 2)}


def bvh_of(o):
    mw = o.matrix_world
    return BVHTree.FromPolygons([mw @ v.co for v in o.data.vertices], [tuple(p.vertices) for p in o.data.polygons])


def box_bvh(c, s):
    h = [x / 2 for x in s]
    v = [Vector((c[0] + x * h[0], c[1] + y * h[1], c[2] + z * h[2])) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    return BVHTree.FromPolygons(v, [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])


trees = {lv: [bvh_of(o) for o in objs] for lv, objs in meshes.items()}
res = {'method': 'same as v001: BVH triangle overlap between each LOD mesh and an axis-aligned block resting 2 mm above the socket', 'blocks': {}}
ok = True
for label, size in (('collectible_0.35x0.30x0.35', (.35, .30, .35)), ('clearance_0.36x0.31x0.36', (.36, .31, .36))):
    rows = []
    for k in range(1, 9):
        s = bpy.data.objects[f'SOCKET_slot_{k}'].matrix_world.translation
        tb = box_bvh((s.x, s.y, s.z + .002 + size[2] / 2), size)
        hits = {f'LOD{lv}': sum(len(t.overlap(tb)) for t in ts) for lv, ts in trees.items()}
        rows.append({'slot': k, 'overlapping_triangles': hits, 'pass': all(v == 0 for v in hits.values())})
        ok &= rows[-1]['pass']
    res['blocks'][label] = rows
val = json.loads(VAL.read_text(encoding='utf-8'))
val['shelf_slot_fit_v002'] = res
val['checks']['shelf_8_slots_fit_test_blocks_LOD0_LOD1_LOD2'] = ok
val['passed'] = all(val['checks'].values())
val['not_checked'] = [n for n in val['not_checked'] if 'shelf' not in n]
VAL.write_text(json.dumps(val, ensure_ascii=False, indent=2), encoding='utf-8')
print('SHELFFIT', ok, [[r['slot'], r['overlapping_triangles']] for r in res['blocks']['clearance_0.36x0.31x0.36']])
