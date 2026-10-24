"""Reopen styled assets, validate ten views and FBX; test revised town connections."""
import bpy,json,math,hashlib,struct,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from refine_town12 import ROOT,BATCH,SRC,bounds
from style12 import PALETTE

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def view_check(aid,ver):
    folder=ROOT/'ArtLibrary/Turnarounds'/f'{aid}_{ver}';data=json.loads((folder/'views.json').read_text())
    assert data['same_geometry'] and len(data['views'])==10
    assert len({tuple(v['direction']) for v in data['views']})==10
    hashes=[]
    for v in data['views']:
        p=folder/v['file'];blob=p.read_bytes()
        assert blob[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',blob[16:24])==(1024,1024)
        assert v['framing_checked'];hashes.append(sha(p))
    assert len(set(hashes))==10
    return 10

def roundtrip(path,meshes):
    lo,hi=bounds(meshes);expected=len(meshes)
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(path.with_suffix('.fbx')))
    imp=[o for o in bpy.context.scene.objects if o.type=='MESH'];a,b=bounds(imp)
    error=max(abs((hi-lo)[i]-(b-a)[i]) for i in range(3))
    assert len(imp)==expected and error<.001,(path.name,expected,len(imp),error)
    assert not any(o.type in ('CAMERA','LIGHT') for o in bpy.context.scene.objects)
    return {'mesh_objects':expected,'fbx_reimported':True,'fbx_dimension_error_m':error}

def tree(objects):
    vs=[];fs=[];dg=bpy.context.evaluated_depsgraph_get()
    for o in objects:
        if o.type!='MESH':continue
        e=o.evaluated_get(dg);off=len(vs);vs.extend(e.matrix_world@v.co for v in e.data.vertices)
        fs.extend(tuple(off+i for i in p.vertices) for p in e.data.polygons)
    return BVHTree.FromPolygons(vs,fs)

def geometry_signature(meshes):
    h=hashlib.sha256()
    for o in sorted(meshes,key=lambda q:q.name):
        h.update(o.name.encode())
        for row in o.matrix_world:
            for v in row:h.update(struct.pack('<d',round(v,7)))
        for p in o.data.vertices:
            for v in p.co:h.update(struct.pack('<d',round(v,7)))
        for p in o.data.polygons:h.update(struct.pack('<'+'I'*len(p.vertices),*p.vertices))
    return h.hexdigest()

layout=json.loads((SRC/'Models/TownLayout/v003/layout_info.json').read_text())
ids=sorted(set(p['asset'] for p in layout['placements'])-{'MountainStonePath'})
results=[]
for aid in ids:
    path=ROOT/'Models'/aid/'v002'/f'{aid}_v002.blend'
    original_signature=None
    if aid not in ('TownPaifang','TownRoadCrossroad','TownRoadTJunction','PondEdge','NoticeBoard','BambooBasket','WoodenCrate'):
        bpy.ops.wm.open_mainfile(filepath=str(SRC/'Models'/aid/'v001'/f'{aid}_v001.blend'))
        original_signature=geometry_signature([o for o in bpy.data.collections['01_Editable_Asset'].objects if o.type=='MESH'])
    bpy.ops.wm.open_mainfile(filepath=str(path))
    meshes=[o for o in bpy.data.collections['01_Editable_Asset'].objects if o.type=='MESH']
    if original_signature:assert geometry_signature(meshes)==original_signature,(aid,'unintended geometry change')
    assert meshes and all(o.data.vertices and o.data.polygons for o in meshes)
    assert all(math.isfinite(v) for o in meshes for p in o.data.vertices for v in p.co)
    lo,hi=bounds(meshes)
    assert abs(lo.z)<.001 and abs(lo.x+hi.x)<.001 and abs(lo.y+hi.y)<.001,(aid,lo,hi)
    info=json.loads((path.parent/'model_info.json').read_text())
    assert max(abs((hi-lo)[i]-info['dimensions_m'][i]) for i in range(3))<.001
    images=[i for i in bpy.data.images if i.source=='FILE'];assert len(images)>=10 and all(i.packed_file for i in images),(aid,'missing packed refs')
    materials=0
    for m in bpy.data.materials:
        if m.name.startswith('TL09_'):
            key=m.name[5:].split('.')[0].lower()
            if key in PALETTE:
                c=m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value
                assert max(abs(c[i]-PALETTE[key][i]) for i in range(3))<1e-6
                materials+=1
    extra={}
    if aid=='TownPaifang':
        bases=sorted([bounds([o]) for o in meshes if o.name.startswith('Paifang_Drum_Base')],key=lambda bb:bb[0].x)
        clear=bases[2][0].x-bases[1][1].x;assert clear>=3.59
        extra['clear_width_at_bases_m']=clear
        t=tree(meshes)
        # Central road corridor remains clear at ankle, chest and head heights.
        samples=0
        for x in [-1.5,-.75,0,.75,1.5]:
            for z in [.25,1,1.8,2.2]:
                hit=t.ray_cast(Vector((x,-1.5,z)),Vector((0,1,0)),3)[0]
                assert hit is None,(x,z,hit);samples+=1
        extra['central_corridor_rays_clear']=samples
    if aid in ('TownRoadCrossroad','TownRoadTJunction'):
        import bmesh
        kerbs=[o for o in meshes if o.name.startswith('Continuous_')]
        assert len(kerbs)==(4 if aid=='TownRoadCrossroad' else 3)
        for o in kerbs:
            bm=bmesh.new();bm.from_mesh(o.data)
            assert all(e.is_manifold for e in bm.edges) and bm.calc_volume(signed=True)>0
            bm.free();assert abs(bounds([o])[1].z-.32)<.001
        extra['closed_continuous_kerbs']=len(kerbs)
        extra['kerb_height_m']=.32
    if aid=='PondEdge':
        pads=[o for o in meshes if o.name.startswith('Lotus_Pad')];assert len(pads)==5
        centres=[(bounds([o])[0]+bounds([o])[1])/2 for o in pads]
        spacing=min((Vector((a.x,a.y))-Vector((b.x,b.y))).length for i,a in enumerate(centres) for b in centres[i+1:])
        assert spacing>.46
        extra['minimum_lotus_pad_centre_spacing_m']=spacing
    if aid=='BambooBasket':
        bundles=[o for o in meshes if o.name.startswith('Basket_Herb_Bundle')]
        centres=[(bounds([o])[0]+bounds([o])[1])/2 for o in bundles]
        spacing=min((Vector((a.x,a.y))-Vector((b.x,b.y))).length for i,a in enumerate(centres) for b in centres[i+1:])
        assert spacing>.18;extra['herb_bundle_spacing_m']=spacing
    if aid=='NoticeBoard':
        planes=[round(bounds([o])[0].y,5) for o in meshes if o.name.startswith('Notice_Paper_')]
        assert len(planes)==len(set(planes))==6;extra['six_separate_paper_planes']=True
    result={'asset':aid,'version':'v002','source_geometry_preserved':aid not in ('TownPaifang','TownRoadCrossroad','TownRoadTJunction','PondEdge','NoticeBoard','BambooBasket','WoodenCrate'),'blend_reopened':True,'packed_reference_images':len(images),'matched_palette_materials':materials,'distinct_1024_views':view_check(aid,'v002'),'blend_sha256':sha(path),'fbx_sha256':sha(path.with_suffix('.fbx')),**extra}
    result.update(roundtrip(path,meshes));results.append(result)
    print('VERIFIED',aid,flush=True)
# The town is checked separately; it is not counted as an independent asset.
path=ROOT/'Models/TownLayout/v004/TownLayout_v004.blend';bpy.ops.wm.open_mainfile(filepath=str(path))
scene=bpy.context.scene
meshes=[o for o in scene.objects if o.type=='MESH' and not any(c.name.startswith(('80_','90_')) for c in o.users_collection)]
scenery=tree(meshes)
# Gate is open; check at low and waist height across its actual clear opening.
rays=0
for y in [28.5,28.75,29,29.25,29.5]:
    for z in [1.55,2.1,2.7]:
        hit=scenery.ray_cast(Vector((9.4,y,z)),Vector((1,0,0)),1.6)[0]
        assert hit is None,('garden blocked',y,z,hit);rays+=1
# Curb opening and approach are supported, with no >2.5 cm step along samples.
walk=bpy.data.collections['13_Connected_Forecourts_v004'];walktree=tree(walk.objects)
heights=[]
for i in range(96):
    x=1.51+(10.98-1.51)*i/95
    hit=walktree.ray_cast(Vector((x,29,3)),Vector((0,0,-1)),3)[0]
    assert hit is not None,('missing approach',x)
    heights.append(hit.z)
assert max(abs(a-b) for a,b in zip(heights,heights[1:]))<.025
# Garden no longer intrudes into the existing east lane.
road=bounds(bpy.data.collections['MountainStonePath_04'].all_objects)
fences=[o for c in bpy.data.collections if c.name.startswith(('BambooFence_','BambooFenceCorner_','FenceGate_')) for o in c.objects if o.type=='MESH']
flo,fhi=bounds(fences);assert flo.x-road[1].x>.4
# Corrected fence corners really land at (10,25), (18,25), (10,33), (18,33).
posts=[o.matrix_world.translation for o in fences if o.name.startswith(('Fence_Post','Corner_Post')) and 'Cap' not in o.name]
for x,y in [(10,25),(18,25),(10,33),(18,33)]:assert any((Vector((p.x,p.y))-Vector((x,y))).length<.01 for p in posts),(x,y)
# Stone rail joints have no exact duplicate posts or finials.
keys=[]
for o in meshes:
    if o.name.startswith(('Stone_Rail_Post','Stone_Rail_Lotus_Cap')):keys.append((o.name.split('.')[0],tuple(round(v,4) for v in o.matrix_world.translation)))
assert len(keys)==len(set(keys))
town={'asset':'TownLayout','version':'v004','blend_reopened':True,'distinct_1024_views':view_check('TownLayout','v004'),'garden_clearance_rays':rays,'garden_path_height_samples':len(heights),'garden_road_gap_m':flo.x-road[1].x,'aligned_fence_corners':4,'duplicate_stone_posts':0,'blend_sha256':sha(path),'fbx_sha256':sha(path.with_suffix('.fbx'))}
town.update(roundtrip(path,meshes))
report={'assets':results,'scene':town,'scope':'Blender geometry, materials, packed references, render manifest and FBX roundtrip only. No Unreal, collision, UV baking, LOD or navigation validation.'}
(BATCH/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('ALL_VERIFIED',len(results),'assets + 1 scene',flush=True)
