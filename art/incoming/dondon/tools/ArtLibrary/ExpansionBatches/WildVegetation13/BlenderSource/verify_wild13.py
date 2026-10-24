"""Reopen models, round-trip FBX and verify ten distinct uncropped reference files.
Blender CLI: blender --background --python-exit-code 1 --python verify_wild13.py
Writes only ../validation.json.
"""
import bpy, bmesh, json, math, struct, hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
ASSETS=['CommonPine','BambooClump','WildShrub','MossBoulderSet','ScreePile']
def bounds(objects):
    dg=bpy.context.evaluated_depsgraph_get()
    pts=[o.evaluated_get(dg).matrix_world@v.co for o in objects for v in o.evaluated_get(dg).data.vertices]
    return Vector([min(p[i] for p in pts) for i in range(3)]),Vector([max(p[i] for p in pts) for i in range(3)])
def named(meshes,prefix):return [o for o in meshes if o.name.startswith(prefix)]
def closed(o):
    bm=bmesh.new();bm.from_mesh(o.data);ok=all(e.is_manifold for e in bm.edges);bm.free();return ok
results=[]
for aid in ASSETS:
    path=ROOT/'Models'/aid/'v001'/f'{aid}_v001.blend'
    bpy.ops.wm.open_mainfile(filepath=str(path))
    meshes=[o for o in bpy.data.collections['01_Editable_Asset'].objects if o.type=='MESH']
    assert meshes and bpy.data.objects.get(aid+'_ROOT')
    assert all(o.data.vertices and o.data.polygons for o in meshes)
    assert all(math.isfinite(c) for o in meshes for v in o.data.vertices for c in v.co)
    lo,hi=bounds(meshes);size=hi-lo;count=len(meshes)
    assert abs(lo.z)<.001 and abs(lo.x+hi.x)<.001 and abs(lo.y+hi.y)<.001,(aid,lo,hi)
    info=json.loads((path.parent/'model_info.json').read_text(encoding='utf-8'))
    assert max(abs(size[i]-info['dimensions_m'][i]) for i in range(3))<.001
    tris=sum(len(p.vertices)-2 for o in meshes for p in o.data.polygons);assert tris==info['triangles']
    if aid=='CommonPine':
        assert len(named(meshes,'Pine_Trunk'))==1 and len(named(meshes,'Pine_Pad'))==info['foliage_pads']>=10
        trunk=named(meshes,'Pine_Trunk')[0];t_lo,t_hi=bounds([trunk])
        pads=named(meshes,'Pine_Pad');p_lo,p_hi=bounds(pads)
        assert abs(t_lo.z)<.001 and p_lo.z>1.5,('canopy should clear a walking character',p_lo.z)
        checks={'trunk_on_ground':True,'foliage_pads':len(pads),'lowest_foliage_m':p_lo.z,'height_m':size.z}
    elif aid=='BambooClump':
        culms=named(meshes,'Bamboo_Culm');leaves=named(meshes,'Bamboo_Leaves');nodes=named(meshes,'Bamboo_Nodes')
        assert len(culms)==len(leaves)==len(nodes)==11 and len(named(meshes,'Bamboo_Shoot'))==3
        quads=sum(1 for o in leaves for p in o.data.polygons if len(p.vertices)==4)
        assert quads>=info['leaf_cards']>800,(quads,info['leaf_cards'])
        assert all(bounds([c])[0].z<.001 for c in culms),'every culm reaches the ground'
        checks={'culms':11,'node_ring_sets':11,'leaf_cards':info['leaf_cards'],'shoots':3,'culms_grounded':True}
    elif aid=='WildShrub':
        masses=named(meshes,'Shrub_Leaf_Mass');assert len(masses)==9 and len(named(meshes,'Shrub_Woody_Stems'))==1
        assert all(closed(o) for o in masses)
        checks={'leaf_masses':9,'closed_leaf_masses':True,'blossoms':info['blossoms']}
    elif aid=='MossBoulderSet':
        stones=named(meshes,'Boulder');assert len(stones)==7
        soles=0
        for o in stones:
            assert closed(o),(o.name,'boulder not closed')
            b=bmesh.new();b.from_mesh(o.data);assert b.calc_volume(signed=True)>0;b.free()
            area=sum(p.area for p in o.data.polygons if p.normal.z<-.999 and abs((o.matrix_world@p.center).z)<.001)
            assert area>.01,(o.name,'no flat sole',area);soles+=1
        checks={'boulders':7,'closed_positive_volume':True,'flat_soles_on_ground':soles}
    else:
        stones=named(meshes,'Scree_Stone');assert len(stones)==info['stones']>=70 and len(named(meshes,'Scree_Gravel_Core'))==1
        assert all(bounds([o])[0].z>-.001 for o in stones)
        checks={'stones':len(stones),'gravel_core':True,'no_stone_below_ground':True}
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
    results.append({'asset':aid,'blend_reopened':True,'mesh_objects':count,'triangles':tris,'finite_vertices':True,'bottom_center_pivot':True,'asset_checks':checks,'fbx_reimported':True,'fbx_no_studio_objects':True,'fbx_dimension_error_m':delta,'distinct_1024_views':10,'framing_checked':True,'blend_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'fbx_sha256':hashlib.sha256(path.with_suffix('.fbx').read_bytes()).hexdigest()})
    print('VERIFIED',aid,flush=True)
(ROOT/'validation.json').write_text(json.dumps({'batch':'WildVegetation13','blender':bpy.app.version_string,'assets':results,'not_verified':['UV/texture bake','collision','LOD','Unreal import','wind animation','two-sided foliage material in engine']},indent=2))
print('ALL_FIVE_VERIFIED',flush=True)
