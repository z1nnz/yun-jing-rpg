"""Run on art/source/qingxi-riverside-house-v1.blend with Blender 5.2."""
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'))
import qa_check

export_mode=sys.argv[-1]=='glb'
if export_mode:
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'art/exports/qingxi-riverside-house-v1/qingxi-riverside-house-v1.glb'))
names=[o.name for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('SM_QX_')]
report=qa_check.run(objects=names,profile='game',tol=.025)
out=ROOT/'art/exports/qingxi-riverside-house-v1'/('export-qa-report.json' if export_mode else 'qa-report.json')
summary={'pass':report['pass'],'objects_checked':len(names),
         'errors':report['errors'],'warnings':report['warnings'],
         'ground_z':report['ground_z']}
out.write_text(json.dumps(summary,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
print('@@QA_SUMMARY@@'+json.dumps({'pass':summary['pass'],'objects':len(names),
      'errors':len(summary['errors']),'warnings':len(summary['warnings']),
      'error_sample':summary['errors'][:8],
      'warning_sample':summary['warnings'][:8]},ensure_ascii=False,default=str))
