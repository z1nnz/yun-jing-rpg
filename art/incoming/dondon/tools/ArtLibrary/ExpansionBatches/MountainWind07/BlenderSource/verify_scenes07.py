import bpy,json,math,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
def bounds(objects):
    dg=bpy.context.evaluated_depsgraph_get();lo=Vector((1e10,1e10,1e10));hi=-lo
    for o in objects:
        e=o.evaluated_get(dg)
        for v in e.data.vertices:
            p=e.matrix_world@v.co
            for i in range(3):assert math.isfinite(p[i]);lo[i]=min(lo[i],p[i]);hi[i]=max(hi[i],p[i])
    return lo,hi

out=ROOT/'Models/MountainSanctuary/v001';bpy.ops.wm.open_mainfile(filepath=str(out/'MountainSanctuary_v001.blend'));s=bpy.context.scene;s.frame_set(1)
assert s.objects.get('Sect_v003_Placed_On_Summit')
assert abs(s.objects['Sect_v003_Placed_On_Summit'].location.z-48.35)<.001
fog=[o for o in s.objects if o.get('effect_type')];assert len(fog)==3
meshes=[o for o in s.objects if o.type=='MESH' and not o.get('effect_type')];count=len(meshes);lo,hi=bounds(meshes)
for p in ['01_mountain_overview.png','02_summit_approach.png','03_summit_top.png']:assert (out/p).stat().st_size>10000
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(out/'MountainSanctuary_v001.fbx'))
imported=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert len(imported)==count
a,b=bounds(imported);delta=max(abs(lo[i]-a[i]) for i in range(3));delta=max(delta,max(abs(hi[i]-b[i]) for i in range(3)));assert delta<.001,delta
assert not any(o.type in ('CAMERA','LIGHT') for o in bpy.context.scene.objects)
(out/'validation.json').write_text(json.dumps({'blend_reopened':True,'mesh_count':count,'fbx_reimported':True,'bounds_error_m':delta,'fog_excluded_from_fbx':True,'source_sect_placement_checked':True,'previews':3,'collision_or_navigation_verified':False},indent=2))
print('MOUNTAIN_SCENE_VERIFIED',flush=True)

out=ROOT/'Effects/WindFog/v001';bpy.ops.wm.open_mainfile(filepath=str(out/'WindFog_v001.blend'));s=bpy.context.scene
fog=[o for o in s.objects if o.get('effect_type')];assert len(fog)==2
drifts=[]
for f in [1,25,97]:
 s.frame_set(f);drifts.append([tuple(o.data.materials[0].node_tree.nodes['Cloud_Drift'].inputs[1].default_value) for o in fog])
assert drifts[0]!=drifts[1]
assert max(abs(a-b) for p,q in zip(drifts[0],drifts[2]) for a,b in zip(p,q))<.00001
animated=[o for o in s.objects if o.type=='MESH' and o.data.shape_keys and o.data.shape_keys.animation_data];assert len(animated)>6
frames=sorted((out/'frames').glob('*.png'));assert len(frames)==48
assert len({hashlib.sha256(p.read_bytes()).hexdigest() for p in frames})==48
(out/'validation.json').write_text(json.dumps({'blend_reopened':True,'animated_meshes':len(animated),'animated_volume_materials':len(fog),'cloud_drift_changes':True,'cloud_loop_endpoint_matches':True,'distinct_rendered_frames':48,'engine_effect_verified':False},indent=2))
print('WIND_EFFECT_VERIFIED',flush=True)
