"""Verify saved model, roof face direction, movable doors and FBX roundtrip."""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
blend=sorted((ROOT/'Models/StarterHouse').glob('v*/*.blend'))[-1]
OUT=blend.parent
bpy.ops.wm.open_mainfile(filepath=str(blend))
scene=bpy.context.scene
assert scene.name=='Qingxi_Starter_House'
source=[o for o in scene.objects if o.type=='MESH' and not any(c.name.startswith('90_') for c in o.users_collection)]
assert all(math.isfinite(v) for o in source for p in o.data.vertices for v in p.co)
roof=[o for o in source if '_Tile_Strip_' in o.name]
assert len(roof)==72
assert all(sum(p.normal.z for p in o.data.polygons)>0 for o in roof),'Roof tile normals must face upward'
door_results={}
for name in ('Door_Left_Hinge','Door_Right_Hinge'):
    hinge=scene.objects[name]
    assert len(hinge.children)>10
    child=next(o for o in hinge.children if '_Backing' in o.name)
    before=child.matrix_world.translation.copy()
    hinge.rotation_euler.z=math.radians(30); bpy.context.view_layer.update()
    moved=(child.matrix_world.translation-before).length
    assert moved>.1
    hinge.rotation_euler.z=0; bpy.context.view_layer.update()
    door_results[name]={'child_parts':len(hinge.children),'rotation_test_displacement_m':moved}

def bounds(objects):
    deps=bpy.context.evaluated_depsgraph_get()
    pts=[o.matrix_world@Vector(p) for src in objects for o in [src.evaluated_get(deps)] for p in o.bound_box]
    return [[min(p[i] for p in pts) for i in range(3)],[max(p[i] for p in pts) for i in range(3)]]
original=bounds(source)
test=bpy.data.scenes.new('FBX_Verification_Only'); bpy.context.window.scene=test
bpy.ops.import_scene.fbx(filepath=str(next(OUT.glob('*.fbx'))))
imported=[o for o in test.objects if o.type=='MESH']
assert len(imported)==len(source)
result=bounds(imported)
error=max(abs(a-b) for aa,bb in zip(original,result) for a,b in zip(aa,bb))
assert error<.01
for name in door_results:
    h=next(o for o in test.objects if o.name.startswith(name))
    assert len(h.children)==door_results[name]['child_parts']
assert not any(o.type in {'CAMERA','LIGHT'} for o in test.objects)
report={'blend_reopened':True,'mesh_objects':len(source),'finite_vertices':True,'roof_tiles_outward':True,
        'door_hinge_rotation':door_results,'fbx_imported_in_blender':True,'fbx_mesh_objects':len(imported),
        'fbx_bounds_error_m':error,'door_hierarchy_preserved':True,'studio_excluded':True,'unity_verified':False}
(OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('VALIDATED',json.dumps(report),flush=True)
