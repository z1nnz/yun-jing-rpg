"""MountainSanctuary v004: v003 (route + solid clouds) with CloudpiercerPeak / MountainRidge swapped to v002
karst pillars. Placements (location/rotation/scale) are kept exactly; source v003 is read-only.
Blender CLI: blender -b -P this.py [-- preview]
"""
import bpy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PREVIEW='--' in sys.argv and 'preview' in sys.argv[sys.argv.index('--'):]
SRC=ROOT/'Models/MountainSanctuary/v003';OUT=ROOT/'Models/MountainSanctuary/v004';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SRC/'MountainSanctuary_v003.blend'))
s=bpy.context.scene;s.frame_set(1);bpy.context.preferences.filepaths.save_version=0

swapped=[]
for coll in [c for c in s.collection.children if c.name.startswith(('CloudpiercerPeak_Placed','MountainRidge_Placed'))]:
    aid=coll.name.split('_Placed')[0];name=coll.name
    top=[o for o in coll.all_objects if o.parent is None];assert len(top)==1
    matrix=top[0].matrix_world.copy()
    meshes={o.data for o in coll.all_objects if o.type=='MESH'}
    for o in list(coll.all_objects):bpy.data.objects.remove(o,do_unlink=True)
    for m in meshes:
        if not m.users:bpy.data.meshes.remove(m)
    bpy.data.collections.remove(coll)
    with bpy.data.libraries.load(str(ROOT/'Models'/aid/'v002'/f'{aid}_v002.blend'),link=False) as (src,dst):dst.collections=['01_Editable_Asset']
    new=dst.collections[0];s.collection.children.link(new);new.name=name
    roots=[o for o in new.all_objects if o.parent is None];assert len(roots)==1
    roots[0].matrix_world=matrix;swapped.append({'collection':name,'asset':aid,'version':'v002','location':list(matrix.translation)})
assert len(swapped)==3,swapped
bpy.context.view_layer.update()

s.camera=s.objects['04_Ascent_Overview'];s.render.resolution_x=1440;s.render.resolution_y=1080;s.cycles.samples=16
if PREVIEW:
    s.render.filepath=str(OUT/'03_mountain_overview.png');s.camera=s.objects['01_Mountain_Overview'];bpy.ops.render.render(write_still=True);print('PREVIEW_DONE',flush=True);sys.exit()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'MountainSanctuary_v004.blend'))
views=[('01_ascent_overview','04_Ascent_Overview'),('02_bridge_and_gate','05_Bridge_And_Gate'),('03_mountain_overview','01_Mountain_Overview'),('04_summit_approach','02_Summit_Approach')]
for fname,cname in views:
    s.camera=s.objects[cname];s.render.filepath=str(OUT/(fname+'.png'));bpy.ops.render.render(write_still=True);print('SCENE_VIEW',fname,flush=True)
s.frame_set(1)
def export(path,objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:o.select_set(True)
    bpy.context.view_layer.objects.active=objs[0]
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},use_mesh_modifiers=True,bake_anim=False,add_leaf_bones=False,axis_forward='-Z',axis_up='Y')
export(OUT/'MountainSanctuary_v004.fbx',[o for o in s.objects if o.type=='MESH'])
export(OUT/'SolidClouds_v004.fbx',[o for o in s.objects if o.get('cloud_type')])
info=json.loads((SRC/'scene_info.json').read_text())
info.update({'version':'v004','source_scene':'MountainSanctuary/v003','swapped_assets':swapped,'previews':len(views),
  'fbx':'static geometry including solid clouds; SolidClouds_v004.fbx holds clouds alone'})
info.pop('removed_volume_fog',None)
(OUT/'scene_info.json').write_text(json.dumps(info,indent=2,ensure_ascii=False))
print('SANCTUARY_V004_COMPLETE',flush=True)
