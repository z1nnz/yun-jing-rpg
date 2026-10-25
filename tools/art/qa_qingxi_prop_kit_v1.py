"""Run Blender asset QA on each independent Qingxi prop, source or GLB."""
import json
import sys
from pathlib import Path

import bpy

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'))
import qa_check

mode=sys.argv[-1]
if mode not in ('source','glb'):raise ValueError('Expected source or glb')
folder=ROOT/'art/exports/qingxi-prop-kit-v1'
summary={}
for key in ('grass','wildflower','cobble'):
    if mode=='glb':
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        bpy.ops.import_scene.gltf(filepath=str(folder/f'qingxi-{key}-v1.glb'))
        objects=[o.name for o in bpy.data.objects if o.type=='MESH']
    else:
        objects=[o.name for o in bpy.data.objects if o.type=='MESH' and
                 o.name.startswith('SM_QX_'+key+'_')]
    if not objects:raise RuntimeError('No mesh for '+key)
    report=qa_check.run(objects=objects,profile='game',tol=.025)
    summary[key]={
        'pass':report['pass'],
        'meshes':len(objects),
        'triangles':sum(len(poly.vertices)-2 for name in objects for poly in bpy.data.objects[name].data.polygons),
        'errors_count':len(report['errors']),
        'errors_sample':report['errors'][:12],
        'warnings_count':len(report['warnings']),
        'warnings_sample':report['warnings'][:12],
    }
(folder/f'{mode}-qa-report.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print('@@PROP_QA@@'+json.dumps(summary,ensure_ascii=False))
