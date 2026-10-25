"""Round-trip both Unity FBX exports in a clean Blender scene."""
import json
from pathlib import Path

import bpy
from mathutils import Vector

root=Path(__file__).resolve().parents[2]
folder=root/'art'/'exports'/'qingxi-world-v1'
report=[]
for stem in ('qingxi-timber-bridge-v1','qingxi-sacred-tree-v1'):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.fbx(filepath=str(folder/(stem+'.fbx')))
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    points=[o.matrix_world@Vector(corner) for o in meshes for corner in o.bound_box]
    mins=[min(point[i] for point in points) for i in range(3)]
    maxs=[max(point[i] for point in points) for i in range(3)]
    dimensions=[round(maxs[i]-mins[i],3) for i in range(3)]
    tris=sum(len(poly.vertices)-2 for o in meshes for poly in o.data.polygons)
    assert meshes and tris>0
    report.append({'asset':stem,'meshes':len(meshes),'triangles':tris,'fbx_dimensions_m':dimensions})
(folder/'roundtrip-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('@@ROUNDTRIP@@'+json.dumps(report))
