"""Reopen models, round-trip FBX and verify ten distinct uncropped reference files."""
import bpy, json, math, struct, hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
def bounds(objects):
    dg=bpy.context.evaluated_depsgraph_get()
    pts=[o.evaluated_get(dg).matrix_world@v.co for o in objects for v in o.evaluated_get(dg).data.vertices]
    return Vector([min(p[i] for p in pts) for i in range(3)]),Vector([max(p[i] for p in pts) for i in range(3)])
results=[]
for aid in ['WaterfallCliff','MountainStreamBend','SpiritSpringPool']:
    path=ROOT/'Models'/aid/'v001'/f'{aid}_v001.blend'
    bpy.ops.wm.open_mainfile(filepath=str(path))
    meshes=[o for o in bpy.data.collections['01_Editable_Asset'].objects if o.type=='MESH']
    assert meshes and bpy.data.objects.get(aid+'_ROOT')
    assert all(o.data.vertices and o.data.polygons for o in meshes)
    assert all(math.isfinite(c) for o in meshes for v in o.data.vertices for c in v.co)
    assert any(o.name.startswith('Water_') for o in meshes)
    lo,hi=bounds(meshes);size=hi-lo;count=len(meshes)
    assert abs(lo.z)<.001 and abs(lo.x+hi.x)<.001 and abs(lo.y+hi.y)<.001
    info=json.loads((path.parent/'model_info.json').read_text())
    assert max(abs(size[i]-info['dimensions_m'][i]) for i in range(3))<.001
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(path.with_suffix('.fbx')))
    imported=[o for o in bpy.context.scene.objects if o.type=='MESH'];a,b=bounds(imported)
    delta=max(abs(size[i]-(b-a)[i]) for i in range(3))
    assert len(imported)==count and delta<.001,(aid,count,len(imported),delta)
    assert not any(o.type in ('LIGHT','CAMERA') for o in bpy.context.scene.objects)
    folder=ROOT/'ArtLibrary/Turnarounds'/f'{aid}_v001';manifest=json.loads((folder/'views.json').read_text())
    assert manifest['same_geometry'] and len(manifest['views'])==10
    assert len({tuple(v['direction']) for v in manifest['views']})==10
    hashes=set()
    for view in manifest['views']:
        data=(folder/view['file']).read_bytes()
        assert len(data)>1000 and data[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',data[16:24])==(1024,1024)
        assert view['framing_checked'];hashes.add(hashlib.sha256(data).hexdigest())
    assert len(hashes)==10
    results.append({'asset':aid,'blend_reopened':True,'mesh_objects':count,'finite_vertices':True,'bottom_center_pivot':True,'editable_water_mesh':True,'fbx_reimported':True,'fbx_no_studio_objects':True,'fbx_dimension_error_m':delta,'distinct_1024_views':10,'framing_checked':True,'blend_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'fbx_sha256':hashlib.sha256(path.with_suffix('.fbx').read_bytes()).hexdigest()})
    print('VERIFIED',aid,flush=True)
(ROOT/'validation.json').write_text(json.dumps(results,indent=2))
print('ALL_THREE_VERIFIED',flush=True)
