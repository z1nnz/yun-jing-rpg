"""Run the local Blender asset QA gate on each separate prop collection."""
import json
import sys
from pathlib import Path

import bpy

skill_scripts=Path.home()/'.codex/skills/blender-asset-qa/scripts'
if not skill_scripts.is_dir():raise RuntimeError(f'Missing QA skill: {skill_scripts}')
sys.path.insert(0,str(skill_scripts))
import qa_check

root=Path(__file__).resolve().parents[2]
results={}
for collection in sorted(bpy.data.collections,key=lambda item:item.name):
    if not collection.name.startswith('ASSET_QX_'):continue
    names=[obj.name for obj in collection.objects if obj.type=='MESH']
    results[collection.name]=qa_check.run(objects=names,profile='game')
path=root/'art/exports/qingxi-detail-props-v2/qa-report.json'
path.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print('@@QX_DETAIL_QA@@'+json.dumps({key:{'pass':value.get('pass'),'errors':len(value.get('errors',[])),'warnings':len(value.get('warnings',[])),'objects':len(value.get('objects',{}))} for key,value in results.items()}))
