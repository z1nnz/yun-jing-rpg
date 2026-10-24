"""Reopen, measure and FBX round-trip each new blockout; audit fourteen reuse sources."""
import bpy,json,math,hashlib,struct,sys
from pathlib import Path
from mathutils import Vector
BATCH=Path(__file__).resolve().parents[1];ROOT=BATCH.parents[2]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bounds(obs):
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();pts=[]
    for o in obs:
        e=o.evaluated_get(dg);pts.extend(e.matrix_world@v.co for v in e.data.vertices)
    assert pts and all(math.isfinite(x) for p in pts for x in p)
    lo=Vector([min(p[i] for p in pts) for i in range(3)]);hi=Vector([max(p[i] for p in pts) for i in range(3)])
    return lo,hi
def source_meshes():
    return [o for o in bpy.context.scene.objects if o.type=='MESH' and not o.hide_render
            and not any(c.name.startswith(('80_','90_','91_','92_')) for c in o.users_collection)
            and not any(x in o.name.lower() for x in ('studio_ground','studio_floor','backdrop'))]

results=[]
for path in sorted((BATCH/'Models').glob('*/v001/model_info.json')):
    info=json.loads(path.read_text(encoding='utf-8'));aid=info['asset'];blend=path.parent/(aid+'_v001.blend');fbx=path.parent/(aid+'_v001.fbx')
    bpy.ops.wm.open_mainfile(filepath=str(blend));obs=[o for o in bpy.context.scene.objects if o.type=='MESH'];lo,hi=bounds(obs);dim=hi-lo
    assert max(abs(dim[i]-info['dimensions_m'][i]) for i in range(3))<1e-5,aid
    assert abs(lo.z)<1e-5,(aid,'bottom not zero')
    assert max(abs(lo[i]+hi[i]) for i in (0,1))<1e-5,(aid,'center')
    assert len(obs)==info['mesh_objects'],aid
    roots=[o for o in bpy.context.scene.objects if o.type=='EMPTY' and o.name==aid+'_ROOT'];assert len(roots)==1
    assert all(o.parent==roots[0] for o in obs)
    ref=BATCH/'ArtLibrary/Turnarounds'/f'{aid}_v001';views=json.loads((ref/'views.json').read_text())
    assert len(views['views'])==10 and len({tuple(x['direction']) for x in views['views']})==10
    hashes=[]
    for row in views['views']:
        p=ref/row['file'];h=p.read_bytes()[:24];assert h[:8]==b'\x89PNG\r\n\x1a\n'
        assert struct.unpack('>II',h[16:24])==(1024,1024);hashes.append(sha(p));assert row['framing_pass']
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(fbx),use_anim=False)
    imported=[o for o in bpy.context.scene.objects if o.type=='MESH'];lo2,hi2=bounds(imported)
    error=max(abs((hi2-lo2)[i]-dim[i]) for i in range(3));assert error<.001,(aid,error)
    assert len(imported)==len(obs),(aid,'FBX meshes')
    row={'asset':aid,'blend_reopened':True,'finite_vertices':True,'bottom_center_root':True,
         'mesh_count':len(imported),'dimensions_m':list(dim),'fbx_dimension_error_m':error,
         'ten_camera_angles':True,'ten_png_1024':True,'framing_checked':True,'unique_png_hashes':len(set(hashes)),
         'blend_sha256':sha(blend),'fbx_sha256':sha(fbx),'unreal_verified':False}
    results.append(row);(path.parent/'validation.json').write_text(json.dumps(row,indent=2),encoding='utf-8')
    print('VERIFIED',aid,flush=True)
assert len(results)==16

plan=json.loads((ROOT/'ArtLibrary/Planning/PlayerJourney_QStyle_v001/asset_plan.json').read_text(encoding='utf-8'))
reuse=[]
scale={'DiscipleBed':.65,'StorageChest':.75,'MeditationCushion':.72,'BasicSword01':.62,'SmithWorkbench':.70,'AlchemyFurnace':.8}
for item in plan['reuse_assets']:
    if not item['first_batch']:continue
    p=ROOT/item['blend']['path'];before=sha(p);bpy.ops.wm.open_mainfile(filepath=str(p));obs=source_meshes();lo,hi=bounds(obs)
    assert sha(p)==before
    reuse.append({'asset':item['id'],'name_zh':item['name'],'source':str(p.relative_to(ROOT)),
                  'source_sha256':before,'source_unchanged':True,'blend_reopened':True,
                  'mesh_objects':len(obs),'measured_dimensions_m':list(hi-lo),
                  'proposed_instance_scale':scale.get(item['id'],1.0),
                  'status':'read_only_size_audit; scale proposal not applied to original; no UE interaction acceptance'})
    print('REUSE_CHECKED',item['id'],len(obs),list(hi-lo),flush=True)
assert len(reuse)==14
(BATCH/'reuse14_audit.json').write_text(json.dumps(reuse,ensure_ascii=False,indent=2),encoding='utf-8')
report={'batch':'QPlayerStart16','stage':'editable_blockouts','new_asset_count':len(results),'same_model_images':160,
        'new_asset_checks_passed':True,'reuse_sources_read_only_checked':len(reuse),'assets':results,
        'limits':['No retopology or unified deformation mesh','No UV bake, rig, animation, collision or LOD','No UE import test','Reuse source audit is not gameplay readiness']}
(BATCH/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('BATCH_VERIFIED',flush=True)
