import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];V=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'v003';OUT=ROOT/'Models/MountainSanctuary'/V
info=json.loads((OUT/'scene_info.json').read_text())
def bounds(objects):
    dg=bpy.context.evaluated_depsgraph_get();lo=Vector((1e10,1e10,1e10));hi=-lo
    for o in objects:
        e=o.evaluated_get(dg)
        for v in e.data.vertices:
            p=e.matrix_world@v.co
            for i in range(3):assert math.isfinite(p[i]);lo[i]=min(lo[i],p[i]);hi[i]=max(hi[i],p[i])
    return lo,hi
bpy.ops.wm.open_mainfile(filepath=str(OUT/f'MountainSanctuary_{V}.blend'));s=bpy.context.scene;s.frame_set(1)
assert not [o for o in s.objects if o.get('effect_type')],'volume fog left in scene'
assert not [m for m in bpy.data.materials if m.users and m.node_tree and any(n.type=='PRINCIPLED_VOLUME' for n in m.node_tree.nodes)]
clouds=[o for o in s.objects if o.get('cloud_type')];assert len(clouds)==len(info['solid_clouds'])
locs=[]
for f in (1,49,97):s.frame_set(f);locs.append([tuple(o.location) for o in clouds])
assert locs[0]!=locs[1] and max(abs(a-b) for p,q in zip(locs[0],locs[2]) for a,b in zip(p,q))<1e-4,'cloud drift must loop'
s.frame_set(1)
meshes=[o for o in s.objects if o.type=='MESH'];count=len(meshes);lo,hi=bounds(meshes);clo,chi=bounds(clouds)
for p in ['01_ascent_overview.png','02_bridge_and_gate.png','03_mountain_overview.png','04_summit_approach.png']:assert (OUT/p).stat().st_size>10000,p
def reimport(path):
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(path))
    return [o for o in bpy.context.scene.objects if o.type=='MESH']
def err(a,b):return max(max(abs(a[0][i]-b[0][i]),abs(a[1][i]-b[1][i])) for i in range(3))
imp=reimport(OUT/f'MountainSanctuary_{V}.fbx');assert len(imp)==count;e1=err((lo,hi),bounds(imp));assert e1<.001,e1
imp=reimport(OUT/f'SolidClouds_{V}.fbx');assert len(imp)==len(clouds);e2=err((clo,chi),bounds(imp));assert e2<.001,e2
(OUT/'validation.json').write_text(json.dumps({'blend_reopened':True,'volume_fog_removed':True,'solid_clouds':len(clouds),'cloud_drift_loops':True,'mesh_count':count,'fbx_reimported':True,'fbx_bounds_error_m':e1,'clouds_fbx_bounds_error_m':e2,'previews':4,'unreal_import_verified':False},indent=2))
print('SANCTUARY_VERIFIED',V,count,len(clouds),flush=True)
