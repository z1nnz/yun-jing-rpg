"""Refresh the description fields of exported v002 model_info files from qx_kit (no rebuild, no re-export).
blender -b --python-exit-code 1 --python refresh_model_info.py
Rewrites only 'design' and 'material_direction'; every other field (sizes, counts, file hashes) is left as the
bake wrote it.
"""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import qx_kit as K
OUT=Path(__file__).resolve().parents[4]/'art/exports/qingxi-gathering-visual-kit-v1'
for a,s in K.STATES:
    key=K.state_key(a,s);p=OUT/a/'v002'/f'{key}_model_info.json';info=json.loads(p.read_text('utf-8'))
    info['design']=K.DESIGN[a];info['material_direction']=K.MATERIAL_DIRECTION[a]
    p.write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8');print('REFRESHED',key,flush=True)
