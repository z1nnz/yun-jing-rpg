"""Verify the combined layout and round-trip the exported FBX in Blender."""
import bpy
import json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
blend=sorted((ROOT/'Models/TownLayout').glob('v*/*.blend'))[-1]
OUT=blend.parent
bpy.ops.wm.open_mainfile(filepath=str(blend))
scene=bpy.context.scene
assert scene.name=='Qingxi_First_Street'
house=next(o for o in scene.objects if o.name.startswith('StarterHouse_ROOT'))
assert (house.location-Vector((12,-2,.24))).length<.001
assert len([o for o in scene.objects if o.name.startswith('Door_Left_Hinge')])==1
source=[o for o in scene.objects if o.type=='MESH' and not any(c.name.startswith('90_') for c in o.users_collection)]
info=json.loads((OUT/'layout_info.json').read_text())
assert len(source)==info['mesh_objects']
assert len(info['east_passage_samples'])==18
if 'blacksmith' in info:
    smith=next(o for o in scene.objects if o.name.startswith('Blacksmith_ROOT'))
    assert (smith.location-Vector(info['blacksmith']['location'])).length<.001
    assert len(info['shop_lane_ray_samples'])==18
    assert len(info['return_stair_heights_m'])==6
    for actual,expected in zip(info['return_stair_heights_m'],[1.14,.96,.78,.60,.42,.24]):
        assert abs(actual-expected)<.015
def bounds(objects):
    deps=bpy.context.evaluated_depsgraph_get()
    pts=[o.matrix_world@Vector(p) for src in objects for o in [src.evaluated_get(deps)] for p in o.bound_box]
    return [[min(p[i] for p in pts) for i in range(3)],[max(p[i] for p in pts) for i in range(3)]]
before=bounds(source)
test=bpy.data.scenes.new('FBX_Check'); bpy.context.window.scene=test
bpy.ops.import_scene.fbx(filepath=str(next(OUT.glob('*.fbx'))))
imported=[o for o in test.objects if o.type=='MESH']
assert len(imported)==len(source)
after=bounds(imported)
error=max(abs(a-b) for aa,bb in zip(before,after) for a,b in zip(aa,bb))
assert error<.01
assert not any(o.type in ('CAMERA','LIGHT') for o in test.objects)
for name in ('Door_Left_Hinge','Door_Right_Hinge'):
    hinge=next(o for o in test.objects if o.name.startswith(name))
    assert len(hinge.children)==18
report={'blend_reopened':True,'house_location_verified':True,'door_hierarchy_preserved':True,
        'source_mesh_objects':len(source),'fbx_mesh_objects':len(imported),'fbx_bounds_error_m':error,
        'studio_excluded':True,'passage_ray_samples':18,'unity_verified':False}
if 'blacksmith' in info:
    assert any(o.name.startswith('Blacksmith_ROOT') for o in test.objects)
    report.update({'smithy_location_verified':True,'shop_lane_samples':18,'return_stair_risers':6})
(OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('VALIDATED',json.dumps(report),flush=True)
