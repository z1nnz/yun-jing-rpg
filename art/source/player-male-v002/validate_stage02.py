import bpy,sys,json,hashlib
from pathlib import Path
import os
qa_scripts = Path(os.environ.get('BLENDER_ASSET_QA_SCRIPTS', str(Path.home() / '.codex/skills/blender-asset-qa/scripts')))
if not (qa_scripts / 'qa_check.py').is_file():
    raise RuntimeError('Set BLENDER_ASSET_QA_SCRIPTS to the installed blender-asset-qa scripts directory')
sys.path.insert(0, str(qa_scripts))
import qa_check
root=Path(__file__).resolve().parent
p=root/'Male_Stage02_ArmsAndSleeves.blend'
bpy.ops.wm.open_mainfile(filepath=str(p))
obs=[o.name for o in bpy.data.objects if o.type=='MESH']
r=qa_check.run(objects=obs,profile='render',no_modifiers=True,uv=False,eps=.0001)
r['blend_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
r['scope']='Control cage only, render profile, UV not final and not checked; no rig/Unity checks'
(root.parents[1]/'previews/player-male-v002/stage02/qa-report.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print(json.dumps({k:r[k] for k in ['pass','errors','warnings']},indent=2))

# Visual control-cage evidence; no changes are saved into the editable master.
mat=bpy.data.materials.new('ReviewWire');mat.diffuse_color=(.03,.06,.06,1)
node=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
node.inputs['Base Color'].default_value=(.02,.04,.04,1)
for name in ['OuterRobe_ConnectedSleeves','Torso_ConnectedArms_Cage']:
    src=bpy.data.objects[name];o=src.copy();o.data=src.data.copy();bpy.context.scene.collection.objects.link(o)
    o.modifiers.clear();o.data.materials.clear();o.data.materials.append(mat)
    mod=o.modifiers.new('Cage','WIREFRAME');mod.thickness=.00035;mod.use_replace=True
scene=bpy.context.scene;scene.camera=bpy.data.objects['Camera_three-quarter'];scene.cycles.samples=24
scene.render.filepath=str(root.parents[1]/'previews/player-male-v002/stage02/upperbody-wire.png')
bpy.ops.render.render(write_still=True)

if not r['pass']:
    raise RuntimeError('Static control-cage QA failed; inspect qa-report.json')
