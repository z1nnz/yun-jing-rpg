"""Reopen all eight .blend files and round-trip FBX bounds; writes validation.json."""
import bpy,json,math,hashlib,struct
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
results=[]
def bounds(objects):
    dg=bpy.context.evaluated_depsgraph_get()
    pts=[e.matrix_world@v.co for o in objects for e in [o.evaluated_get(dg)] for v in e.data.vertices]
    lo=Vector([min(p[i] for p in pts) for i in range(3)]);hi=Vector([max(p[i] for p in pts) for i in range(3)])
    return lo,hi
for path in sorted(p for p in (ROOT/'Models').glob('*/v001/*.blend') if p.parent.parent.name != 'SectLayout'):
    bpy.ops.wm.open_mainfile(filepath=str(path));aid=path.parent.parent.name
    meshes=[o for o in bpy.data.collections['01_Editable_Asset'].objects if o.type=='MESH']
    assert meshes and bpy.data.objects.get(aid+'_ROOT')
    assert all(o.data.vertices and o.data.polygons for o in meshes)
    lo,hi=bounds(meshes);size=hi-lo
    assert abs(lo.z)<.001 and abs(lo.x+hi.x)<.001 and abs(lo.y+hi.y)<.001
    if aid=='TimberStairFlight':
        treads=[o for o in meshes if o.name.startswith('Stair_Tread_')]
        assert len(treads)==18
        assert abs(bounds(treads)[1].z-3.0)<.001
    if aid=='SectWallStraight':assert abs(size.x-4.0)<.001
    expected_stems={'SpiritHerbSeedling':2,'SpiritHerbYoung':3,'SpiritHerbMature':5}
    if aid in expected_stems:assert sum(o.name.startswith('Herb_Stem') for o in meshes)==expected_stems[aid]
    count=len(meshes)
    assert all(math.isfinite(c) for o in meshes for v in o.data.vertices for c in v.co)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path.with_suffix('.fbx')))
    imported=[o for o in bpy.context.scene.objects if o.type=='MESH']
    a,b=bounds(imported);imp_size=b-a
    delta=max(abs(size[i]-imp_size[i]) for i in range(3))
    assert len(imported)==count,(aid,'mesh count mismatch')
    assert delta<.001,(aid,'FBX bounds mismatch',list(size),list(imp_size))
    assert not any(o.type in ('LIGHT','CAMERA') for o in bpy.context.scene.objects)
    manifest=json.loads((ROOT/'ArtLibrary/Turnarounds'/f'{aid}_v001'/'views.json').read_text())
    assert len(manifest['views'])==10
    assert len({tuple(r['direction']) for r in manifest['views']})==10
    digests=set()
    for record in manifest['views']:
        img=ROOT/'ArtLibrary/Turnarounds'/f'{aid}_v001'/record['file']
        data=img.read_bytes();assert len(data)>1000
        assert data[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',data[16:24])==(1024,1024)
        assert record['framing_checked'];digests.add(hashlib.sha256(data).hexdigest())
    assert len(digests)==10
    row={'asset':aid,'blend_reopened':True,'meshes':count,'vertices_finite':True,'bottom_center_pivot_checked':True,'fbx_reimported':True,'fbx_no_studio_objects':True,'fbx_dimension_error_m':delta,'ten_view_files_present':True}
    results.append(row);print('VERIFIED',aid,flush=True)
(ROOT/'validation.json').write_text(json.dumps(results,indent=2))
assert len(results)==8
print('ALL_EIGHT_VERIFIED',flush=True)
