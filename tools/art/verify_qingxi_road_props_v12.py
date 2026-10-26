"""Reimport each exported GLB independently and check basic asset integrity."""
import json
from pathlib import Path

import bpy

root=Path(__file__).resolve().parents[2]
folder=root/'art/exports/qingxi-road-props-v12'
result={}
for name in ('road','bridge-rail','herb-rack','waymarker'):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    path=folder/f'qingxi-{name}-v12.glb'
    bpy.ops.import_scene.gltf(filepath=str(path))
    objs=[o for o in bpy.context.scene.objects if o.type=='MESH']
    result[name]={
        'file_bytes':path.stat().st_size,
        'mesh_count':len(objs),
        'triangles':sum(len(face.vertices)-2 for o in objs for face in o.data.polygons),
        'materials':len({m.name for o in objs for m in o.data.materials if m}),
    }
    if not objs or not result[name]['triangles'] or not result[name]['materials']:
        raise RuntimeError(f'Invalid GLB: {name}: {result[name]}')
(folder/'roundtrip-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print('@@QINGXI_ROUNDTRIP@@'+json.dumps(result,ensure_ascii=False))
