"""Reopen all six .blend files and round-trip FBX bounds; writes validation.json."""
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
for path in sorted(p for p in (ROOT/'Models').glob('*/v001/*.blend') if p.parent.parent.name != 'MountainSanctuary'):
    bpy.ops.wm.open_mainfile(filepath=str(path));aid=path.parent.parent.name
    meshes=[o for o in bpy.data.collections['01_Editable_Asset'].objects if o.type=='MESH']
    assert meshes and bpy.data.objects.get(aid+'_ROOT')
    assert all(o.data.vertices and o.data.polygons for o in meshes)
    lo,hi=bounds(meshes);size=hi-lo
    assert abs(lo.z)<.001 and abs(lo.x+hi.x)<.001 and abs(lo.y+hi.y)<.001
    motion={}
    if aid in ('WindPine','WindGrass'):
        def sample(frame):
            bpy.context.scene.frame_set(frame);dg=bpy.context.evaluated_depsgraph_get()
            return [e.matrix_world@v.co for o in meshes for e in [o.evaluated_get(dg)] for v in e.data.vertices]
        neutral=sample(1);bent=sample(25);end=sample(97)
        displacement=max((p-q).length for p,q in zip(neutral,bent))
        seam=max((p-q).length for p,q in zip(neutral,end))
        root_motion=max((p-q).length for p,q in zip(neutral,bent) if p.z<.001)
        assert displacement>.05 and seam<.00001 and root_motion<.0001,(aid,displacement,seam,root_motion)
        motion={'maximum_wind_displacement_m':displacement,'loop_seam_error_m':seam,'root_motion_m':root_motion}
        bpy.context.scene.frame_set(1)
    if aid=='SectSummitPlateau':
        dg=bpy.context.evaluated_depsgraph_get()
        for x,y in [(-22,-31),(22,-31),(-22,31),(22,31),(0,0)]:
            hit,p,*_=bpy.context.scene.ray_cast(dg,Vector((x,y,100)),Vector((0,0,-1)))
            assert hit and abs(p.z-48)<.001,('Plateau usable rectangle',x,y,list(p))
        motion['flat_44x62m_summit_checked']=True
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
    row.update(motion)
    results.append(row);print('VERIFIED',aid,flush=True)
(ROOT/'validation.json').write_text(json.dumps(results,indent=2))
assert len(results)==6
print('ALL_SIX_VERIFIED',flush=True)
