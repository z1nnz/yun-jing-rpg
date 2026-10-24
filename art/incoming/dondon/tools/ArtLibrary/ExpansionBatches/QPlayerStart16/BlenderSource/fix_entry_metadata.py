"""Repair triangle metadata after removal of the two overlapping entry blocks; geometry unchanged."""
import bpy,json
from pathlib import Path
BATCH=Path(__file__).resolve().parents[1];ROOT=BATCH.parents[2]
p=BATCH/'Models/QCaveEntrance/v003/model_info.json'
bpy.ops.wm.open_mainfile(filepath=str(p.parent/'QCaveEntrance_v003.blend'))
data=json.loads(p.read_text(encoding='utf-8'))
data['triangles']=sum(len(poly.vertices)-2 for o in bpy.context.scene.objects if o.type=='MESH' for poly in o.data.polygons)
content=json.dumps(data,ensure_ascii=False,indent=2)
p.write_text(content,encoding='utf-8')
(ROOT/'Models/QCaveEntrance/v003/model_info.json').write_text(content,encoding='utf-8')
print('ENTRY_METADATA_UPDATED',data['triangles'])
