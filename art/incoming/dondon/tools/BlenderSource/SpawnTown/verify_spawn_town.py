"""Reopen the delivered blend and round-trip its FBX in Blender (not Unity)."""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=sorted((ROOT/'Models/SpawnTown').glob('v[0-9][0-9][0-9]'))[-1]
blend=next(OUT.glob('*.blend'))
fbx=next(OUT.glob('*.fbx'))
bpy.ops.wm.open_mainfile(filepath=str(blend))
scene=bpy.context.scene
assets=[o for o in scene.objects if o.type=='MESH' and not any(c.name.startswith('90_') for c in o.users_collection)]
assert scene.name=='Qingxi_Spawn_Plaza'
assert 'Spawn_Player_Feet' in scene.objects
assert len([o for o in assets if o.name.startswith('Stair_')])==30
assert all(math.isfinite(v) for o in assets for vert in o.data.vertices for v in vert.co)
deps=bpy.context.evaluated_depsgraph_get()
def bounds(objects):
    coords=[o.matrix_world @ Vector(p) for source in objects for o in [source.evaluated_get(deps)] for p in o.bound_box]
    return [[min(p[i] for p in coords) for i in range(3)], [max(p[i] for p in coords) for i in range(3)]]
before=bounds(assets)
expected=len(assets)
testscene=bpy.data.scenes.new('FBX_Roundtrip_Check')
bpy.context.window.scene=testscene
bpy.ops.import_scene.fbx(filepath=str(fbx))
imported=[o for o in testscene.objects if o.type=='MESH']
deps=bpy.context.evaluated_depsgraph_get()
after=bounds(imported)
error=max(abs(a-b) for aa,bb in zip(before,after) for a,b in zip(aa,bb))
assert len(imported)==expected,(len(imported),expected)
assert error<.01,error
assert not any(o.type in {'CAMERA','LIGHT'} for o in testscene.objects)
report={'blend_reopened':True,'finite_vertex_coordinates':True,'fbx_reimported_in_blender':True,
        'source_meshes':expected,'imported_meshes':len(imported),'world_bounds_m':before,
        'fbx_bounds_max_error_m':error,'studio_camera_lights_excluded':True,
        'unity_verified':False}
(OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('VALIDATED',json.dumps(report),flush=True)
