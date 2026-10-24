"""Verify only the ten active non-character v002 assets and their layout."""
import bpy,json,math,hashlib,struct,importlib.util,sys
from pathlib import Path
BATCH=Path(__file__).resolve().parents[1];ROOT=BATCH.parents[2]
spec=importlib.util.spec_from_file_location('nc',Path(__file__).with_name('continue_noncharacter.py'));nc=importlib.util.module_from_spec(spec);spec.loader.exec_module(nc)
scene_only='--scene-only' in sys.argv
rows=json.loads((BATCH/'noncharacter_validation.json').read_text(encoding='utf-8'))['assets'] if scene_only else []
for aid in ([] if scene_only else nc.ALLOWED):
    version=nc.VERSIONS[aid];out=BATCH/'Models'/aid/version;blend=out/(aid+'_'+version+'.blend');fbx=out/(aid+'_'+version+'.fbx')
    info=json.loads((out/'model_info.json').read_text(encoding='utf-8'))
    bpy.ops.wm.open_mainfile(filepath=str(blend));s=bpy.context.scene;s.frame_set(1);obs=[o for o in s.objects if o.type=='MESH']
    lo,hi=nc.bounds(obs);dim=hi-lo
    assert all(math.isfinite(v) for o in obs for vert in o.data.vertices for v in vert.co),aid
    assert max(abs(dim[i]-info['dimensions_m'][i]) for i in range(3))<1e-5
    assert abs(lo.z)<1e-5
    count=len(obs);door_test=None
    if aid=='QCaveDoor':
        assert dim.x<1.71,(aid,'door wider than entrance footstone opening')
        h=[bpy.data.objects.get('Door_Leaf_Left'),bpy.data.objects.get('Door_Leaf_Right')]
        assert all(h) and all(x.animation_data for x in h)
        assert all(sum(o.parent==x for o in obs)>0 for x in h)
        s.frame_set(35);assert all(abs(abs(x.rotation_euler.z)-math.pi/2)<1e-5 for x in h)
        s.frame_set(120);assert all(abs(x.rotation_euler.z)<1e-5 for x in h)
        s.frame_set(1)
        door_test={'hinges':2,'open_frame':35,'open_angle_deg':90,'closed_frame':120,'static_width_m':dim.x,'entry_footstone_clear_width_m':1.71,'total_width_clearance_m':1.71-dim.x,'full_sweep_collision_test':False}
    ref=BATCH/'ArtLibrary/Turnarounds'/f'{aid}_{version}';manifest=json.loads((ref/'views.json').read_text());hashes=[]
    assert len(manifest['views'])==10 and len({tuple(v['direction']) for v in manifest['views']})==10
    for v in manifest['views']:
        p=ref/v['file'];head=p.read_bytes()[:24];assert head[:8]==b'\x89PNG\r\n\x1a\n'
        assert struct.unpack('>II',head[16:24])==(1024,1024);assert v['framing_pass'];hashes.append(nc.sha(p))
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(fbx),use_anim=False)
    imported=[o for o in bpy.context.scene.objects if o.type=='MESH'];lo2,hi2=nc.bounds(imported)
    err=max(abs((hi2-lo2)[i]-dim[i]) for i in range(3));assert err<.001,(aid,err);assert len(imported)==count
    if aid=='QCaveDoor':
        bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(out/(aid+'_open_close_v002.fbx')),use_anim=True)
        s=bpy.context.scene;h=[bpy.data.objects.get('Door_Leaf_Left'),bpy.data.objects.get('Door_Leaf_Right')];assert all(h)
        s.frame_set(1);rest=[x.rotation_euler.z for x in h]
        s.frame_set(35);motion=[abs(x.rotation_euler.z-a) for x,a in zip(h,rest)];assert min(motion)>1.4,motion
        door_test['animated_fbx_roundtrip']=True
    row={'asset':aid,'name_zh':info['name_zh'],'version':version,'blend_reopened':True,'fbx_roundtrip':True,
         'fbx_dimension_error_m':err,'dimensions_m':list(dim),'mesh_objects':count,'finite_geometry':True,
         'png_views_1024':10,'unique_camera_angles':10,'unique_png_hashes':len(set(hashes)),
         'framing_checks':True,'blend_sha256':nc.sha(blend),'fbx_sha256':nc.sha(fbx),'door_test':door_test,'unreal_verified':False}
    (out/'validation.json').write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8');rows.append(row)
    print('ACTIVE_VERIFIED',aid,flush=True)

V=nc.SCENE_VERSION
scene_dir=BATCH/'Scenes/QCaveResidence'/V;scene_info=json.loads((scene_dir/'model_info.json').read_text(encoding='utf-8'))
assert not scene_info['character_assets_used']
for item in scene_info['instances']:assert nc.sha(ROOT/item['source'])==item['source_sha256'],item['source']
bpy.ops.wm.open_mainfile(filepath=str(scene_dir/('QCaveResidence_'+V+'.blend')));meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];lo,hi=nc.bounds(meshes);dims=hi-lo
garden=[o for o in meshes if o.name.startswith('SpiritHerbGarden_')];ground=[o for o in meshes if o.name=='Scene_support_not_independent_asset']
gl,gh=nc.bounds(garden);sl,sh=nc.bounds(ground)
assert all(sl[i]<gl[i] and gh[i]<sh[i] for i in (0,1)),'Garden overhangs support'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(scene_dir/('QCaveResidence_'+V+'.fbx')),use_anim=False)
lo2,hi2=nc.bounds([o for o in bpy.context.scene.objects if o.type=='MESH']);scene_error=max(abs((hi2-lo2)[i]-dims[i]) for i in range(3));assert scene_error<.001
scene_views=json.loads((BATCH/'Previews'/('CaveResidence_'+V)/'views.json').read_text())
assert len(scene_views['views'])==10
for row in scene_views['views']:
    h=(BATCH/'Previews'/('CaveResidence_'+V)/row['file']).read_bytes()[:24];assert struct.unpack('>II',h[16:24])==(1024,1024)
report={'batch':'QPlayerStart16','scope':'non-character only','active_asset_count':10,'model_view_images':100,'extra_door_pose_images':1,
        'scene_preview_images':10,'scene_count':1,'assets':rows,
        'scene_checks':{'version':V,'blend_reopened':True,'fbx_dimension_error_m':scene_error,'sources_unchanged':True,'character_assets_used':False,'garden_within_support':True},
        'status':'Blender file, size and render checks passed; editable appearance prototypes, not UE-ready',
        'limits':['Creatures have no rig or animation','No authored UV bake, LOD, collision or UE test','Door width and animation tested; full sweep collision and gameplay not tested','Cutaway scene has low side walls and no ceiling']}
(BATCH/'noncharacter_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('NONCHARACTER_VALIDATION_PASSED',flush=True)
