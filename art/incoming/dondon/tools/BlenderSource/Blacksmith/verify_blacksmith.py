"""Reopen the smithy and verify its exported FBX meshes and prop hierarchy."""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
blend=sorted((ROOT/'Models/Blacksmith').glob('v*/*.blend'))[-1]; OUT=blend.parent
bpy.ops.wm.open_mainfile(filepath=str(blend))
scene=bpy.context.scene
assert scene.name=='Qingxi_Blacksmith'
source=[o for o in scene.objects if o.type=='MESH' and not any(c.name.startswith('90_') for c in o.users_collection)]
assert all(math.isfinite(v) for o in source for vert in o.data.vertices for v in vert.co)
assert len([o for o in scene.objects if o.name.startswith('Display_Sword_') and o.type=='EMPTY'])==3
assert all(sum(p.normal.z for p in o.data.polygons)>0 for o in source if o.name.startswith('Canopy_Tiles_'))
assert not bpy.data.collections['03_Smithy_Tile_Roof'].hide_render
names=['Blacksmith_ROOT','Anvil_Station_ROOT','Workbench_ROOT','Weapon_Rack_ROOT','Quench_Barrel_ROOT']
assert all(name in scene.objects for name in names)
def bounds(objects):
    deps=bpy.context.evaluated_depsgraph_get()
    pts=[o.matrix_world@Vector(p) for src in objects for o in [src.evaluated_get(deps)] for p in o.bound_box]
    return [[min(p[i] for p in pts) for i in range(3)],[max(p[i] for p in pts) for i in range(3)]]
before=bounds(source)
test=bpy.data.scenes.new('Smithy_FBX_Check'); bpy.context.window.scene=test
bpy.ops.import_scene.fbx(filepath=str(next(OUT.glob('*.fbx'))))
imported=[o for o in test.objects if o.type=='MESH']
assert len(imported)==len(source)
after=bounds(imported); error=max(abs(a-b) for aa,bb in zip(before,after) for a,b in zip(aa,bb))
assert error<.01
assert not any(o.type in ('CAMERA','LIGHT') for o in test.objects)
assert all(any(o.name.startswith(name) for o in test.objects) for name in names)
report={'blend_reopened':True,'finite_vertices':True,'roof_tile_normals_outward':True,
        'source_meshes':len(source),'fbx_meshes':len(imported),'fbx_bounds_error_m':error,
        'prop_roots_preserved':True,'display_swords':3,'studio_excluded':True,'unity_verified':False}
(OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('VALIDATED',json.dumps(report),flush=True)
