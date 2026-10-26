import bpy, sys, json
from pathlib import Path
import os
qa_scripts = Path(os.environ.get('BLENDER_ASSET_QA_SCRIPTS', str(Path.home() / '.codex/skills/blender-asset-qa/scripts')))
if not (qa_scripts / 'qa_check.py').is_file():
    raise RuntimeError('Set BLENDER_ASSET_QA_SCRIPTS to the installed blender-asset-qa scripts directory')
sys.path.insert(0, str(qa_scripts))
import qa_check
root=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(root/'Male_Stage01_TorsoAndCollar.blend'))
objects=[o.name for o in bpy.data.objects if o.type=='MESH']
report=qa_check.run(objects=objects,profile='render',no_modifiers=True,uv=True,eps=.0001)
report['scope']='Stage 01 editable control cage; intended neck/pelvis/sleeve boundaries; no rig, final UV or game certification.'
(root.parents[1]/'previews/player-male-v002/stage01/qa-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ['pass','errors','warnings']},indent=2))

if not report['pass']:
    raise RuntimeError('Static control-cage QA failed; inspect qa-report.json')
