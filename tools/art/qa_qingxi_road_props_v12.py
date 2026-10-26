"""Run Blender asset QA on each Qingxi v12 collection; record every finding."""
import json
import sys
from pathlib import Path

import bpy

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'))
import qa_check

report={}
for key,name in {
    'road':'ASSET_QingxiWindingRoad_v2',
    'bridge-rail':'ASSET_QingxiBridgeRail_v1',
    'herb-rack':'ASSET_QingxiHerbRack_v1',
    'waymarker':'ASSET_QingxiWaymarker_v1',
}.items():
    names=[ob.name for ob in bpy.data.collections[name].objects if ob.type=='MESH']
    result=qa_check.run(objects=names,profile='game',max_tris=300000)
    report[key]={
        'pass':result['pass'],
        'errors':result['errors'],
        'warnings':result['warnings'],
        'ground_z':result['ground_z'],
        'mesh_count':len(result['objects']),
        'triangles':sum(o['tris'] for o in result['objects'].values()),
    }
out=ROOT/'art/exports/qingxi-road-props-v12/qa-report.json'
out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('@@QINGXI_QA@@'+json.dumps({k:{'pass':v['pass'],'errors':len(v['errors']),'warnings':len(v['warnings'])} for k,v in report.items()}))
