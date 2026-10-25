"""Run Blender mesh QA for one environment asset, source or GLB roundtrip.

Examples:
  blender -b art/source/qingxi-riverbank-v2.blend -P this.py -- bank source
  blender -b -P this.py -- bank glb
"""
import json
import sys
from collections import Counter
from pathlib import Path

import bpy

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'))
import qa_check

asset,mode=sys.argv[-2:]
assets={
    'bank':('qingxi-riverbank-v2','qingxi-riverbank-v2.glb','SM_QXBank_'),
    'road':('qingxi-winding-road-v1','qingxi-winding-road-v1.glb','SM_QXRoad_'),
    'tree':('elder-world-tree-hero-v1','elder-world-tree-hero-v1.glb',None),
}
if asset not in assets or mode not in ('source','glb'):
    raise ValueError('Usage: bank|road|tree source|glb')
folder,filename,prefix=assets[asset]
out=ROOT/'art/exports'/folder
if mode=='glb':
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(out/filename))
meshes=[o for o in bpy.data.objects if o.type=='MESH']
names=[o.name for o in meshes if prefix is None or o.name.startswith(prefix)]
if not names:raise RuntimeError('No matching mesh objects')
report=qa_check.run(objects=names,profile='game',tol=.025)
summary={
    'asset':asset,'mode':mode,'pass':report['pass'],
    'objects_checked':len(names),
    'triangles':sum(len(p.vertices)-2 for o in meshes if o.name in names for p in o.data.polygons),
    'errors':report['errors'],'warnings':report['warnings'],
    'ground_z':report['ground_z'],
}
if asset=='tree':
    def error_kind(message):
        if message.startswith('floating/detached'):return 'detached foliage or branch island'
        if message.startswith('z-fighting'):return 'coplanar foliage overlap'
        if 'zero-area UV' in message:return 'zero-area UV'
        if 'no UV map' in message:return 'missing UV'
        if 'unapplied scale' in message:return 'unapplied scale'
        return message.split(':',1)[0]
    summary['error_kinds']=dict(Counter(error_kind(m) for m in report['errors']))
    summary['error_examples']=report['errors'][:20]
    summary['errors_omitted']=max(0,len(report['errors'])-20)
    summary['error_count']=len(report['errors'])
    summary['errors']=[]
    summary['warnings']=report['warnings'][:20]
    summary['warnings_omitted']=max(0,len(report['warnings'])-20)
(out/(mode+'-qa-report.json')).write_text(json.dumps(summary,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
print('@@ENV_QA@@'+json.dumps({'asset':asset,'mode':mode,'pass':summary['pass'],
    'objects':len(names),'triangles':summary['triangles'],
    'errors':len(report['errors']),'warnings':len(report['warnings'])},ensure_ascii=False))
