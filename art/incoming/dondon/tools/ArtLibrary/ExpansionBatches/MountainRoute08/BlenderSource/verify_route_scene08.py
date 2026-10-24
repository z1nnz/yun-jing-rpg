import bpy,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Models/MountainSanctuary/v002'
info=json.loads((OUT/'route_info.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(OUT/'MountainSanctuary_v002.blend'));s=bpy.context.scene;s.frame_set(1)
assert bpy.data.collections.get('60_Mountain_Ascent') and len(info['placements'])==33
assert info['stairs_flights']==20 and info['risers']==240
for o in s.objects:
 if o.get('effect_type'):o.hide_set(True)
bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
samples=0;max_error=0;headroom=0
for seg in info['walking_segments']:
 a,b=Vector(seg['start']),Vector(seg['end']);delta=b-a;side=Vector((-delta.y,delta.x,0)).normalized()
 n=seg.get('steps',0) or max(1,round(Vector((delta.x,delta.y,0)).length/.25))
 for i in range(n):
  t=(i+.5)/n;p=a.lerp(b,t)
  if seg['type']=='stairs':p.z=a.z+delta.z*(i+1)/n
  for offset in (-1.1,0,1.1):
   q=p+side*offset;hit,pt,normal,index,obj,matrix=s.ray_cast(dg,q+Vector((0,0,.30)),Vector((0,0,-1)),distance=.55)
   assert hit,('No walking surface',seg,list(q))
   err=abs(pt.z-q.z);assert err<.15,('Unexpected surface height',obj.name,list(q),list(pt));max_error=max(max_error,err)
   hit2,pt2,normal2,index2,obj2,matrix2=s.ray_cast(dg,pt+Vector((0,0,.03)),Vector((0,0,1)),distance=2.0)
   assert not hit2,('Blocked headroom',obj2.name,list(pt2))
   samples+=1;headroom+=1
for a,b in zip(info['walking_segments'],info['walking_segments'][1:]):assert (Vector(a['end'])-Vector(b['start'])).length<.001
# Check the remaining existing entrance steps rather than claiming the new path alone reaches the courtyard.
heights=[]
for i in range(33):
 y=-30+i*.1;hit,p,*rest=s.ray_cast(dg,Vector((0,y,48.8)),Vector((0,0,-1)),distance=1)
 assert hit;heights.append(p.z)
assert max(abs(a-b) for a,b in zip(heights,heights[1:]))<.22,heights

def bounds(objects):
 dg=bpy.context.evaluated_depsgraph_get();lo=Vector((1e10,1e10,1e10));hi=-lo
 for o in objects:
  e=o.evaluated_get(dg)
  for v in e.data.vertices:
   p=e.matrix_world@v.co
   for i in range(3):assert math.isfinite(p[i]);lo[i]=min(lo[i],p[i]);hi[i]=max(hi[i],p[i])
 return lo,hi
meshes=[o for o in s.objects if o.type=='MESH' and not o.get('effect_type')];count=len(meshes);lo,hi=bounds(meshes)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(OUT/'MountainSanctuary_v002.fbx'))
imported=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert len(imported)==count
a,b=bounds(imported);error=max([abs(a[i]-lo[i]) for i in range(3)]+[abs(b[i]-hi[i]) for i in range(3)]);assert error<.001,error
assert not any(o.type in ('CAMERA','LIGHT') for o in bpy.context.scene.objects)
for f in ['01_ascent_overview.png','02_bridge_and_gate.png','03_route_top.png']:assert (OUT/f).stat().st_size>10000
(OUT/'validation.json').write_text(json.dumps({'blend_reopened':True,'route_placements':len(info['placements']),'rise_m':48,'walk_surface_samples':samples,'sampled_clear_width_m':2.2,'sampled_headroom_m':2.0,'max_walk_height_error_m':max_error,'connector_gaps_checked':True,'existing_gate_step_height_checked':True,'fbx_reimported':True,'mesh_count':count,'fbx_bounds_error_m':error,'unreal_collision_or_navigation_verified':False,'structural_engineering_verified':False},indent=2))
print('ROUTE_SCENE_VERIFIED',samples,flush=True)
