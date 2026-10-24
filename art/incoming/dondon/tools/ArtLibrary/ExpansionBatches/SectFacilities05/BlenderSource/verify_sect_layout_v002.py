import bpy,json,math
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[1];D=R/'Models/SectLayout/v002';P=D/'SectLayout_v002.blend'
bpy.ops.wm.open_mainfile(filepath=str(P))
expected={'SectGate','SectGrandHall','DiscipleResidence','TrainingGround','SpiritHerbGarden','CultivationPlatform','AlchemyHall','ScriptureLibrary','SectStorehouse'}
assert all(bpy.data.collections.get(a) for a in expected)
roots=[o for o in bpy.context.scene.objects if o.type=='EMPTY' and o.name.endswith('_ROOT')]
assert len(roots)==9
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
def bounds(meshes):
 dg=bpy.context.evaluated_depsgraph_get();pts=[e.matrix_world@v.co for o in meshes for e in [o.evaluated_get(dg)] for v in e.data.vertices]
 assert all(math.isfinite(c) for p in pts for c in p)
 return [min(p[i] for p in pts) for i in range(3)]+[max(p[i] for p in pts) for i in range(3)]
a=bounds(meshes);count=len(meshes)
# Check separate architecture modules do not overlap each other's bounding boxes.
footprints={}
for aid in expected:
 b=bounds([o for o in bpy.data.collections[aid].objects if o.type=='MESH']);footprints[aid]=b
for i,aid in enumerate(sorted(expected)):
 for bid in sorted(expected)[i+1:]:
  aa=footprints[aid];bb=footprints[bid]
  assert not (min(aa[3],bb[3])-max(aa[0],bb[0])>.001 and min(aa[4],bb[4])-max(aa[1],bb[1])>.001),(aid,bid,'overlapping module footprints')
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(P.with_suffix('.fbx')))
imp=[o for o in bpy.context.scene.objects if o.type=='MESH'];b=bounds(imp)
assert len(imp)==count
err=max(abs(x-y) for x,y in zip(a,b));assert err<.001
assert not any(o.type in ('LIGHT','CAMERA') for o in bpy.context.scene.objects)
assert len(list(D.glob('*.png')))==3
result={'blend_reopened':True,'module_roots':9,'module_footprints_nonoverlapping':True,'meshes':count,'fbx_reimported':True,'max_bounds_error_m':err,'studio_excluded_from_fbx':True,'preview_files':3,'navigation_and_collision_verified':False,'unreal_import_verified':False}
(D/'layout_validation.json').write_text(json.dumps(result,indent=2));print('LAYOUT_VERIFIED',json.dumps(result),flush=True)
