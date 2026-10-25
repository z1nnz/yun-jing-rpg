"""Check the giant tree v1 outputs of build-giant-tree.py and write art/exports/giant-tree-v1/validation.json.
  blender --background --factory-startup --python-exit-code 1 --python tools/validate-giant-tree.py
Reopens the .blend (finite vertices, noted dimensions within tolerance, origin at the trunk base), re-imports the GLB and
FBX (same size), and checks the ten 1024 px views. Only what is listed under "checks" was verified.
"""
import bpy,json,math,struct,hashlib
from pathlib import Path
from mathutils import Vector
REPO=Path(__file__).resolve().parents[1];EXP=REPO/'art/exports/giant-tree-v1';PREV=REPO/'art/previews/giant-tree-v1'
def bounds(objs):
    dg=bpy.context.evaluated_depsgraph_get();pts=[o.evaluated_get(dg).matrix_world@v.co for o in objs for v in o.evaluated_get(dg).data.vertices]
    return Vector([min(p[i] for p in pts) for i in range(3)]),Vector([max(p[i] for p in pts) for i in range(3)])
checks={}
bpy.ops.wm.open_mainfile(filepath=str(REPO/'art/source/giant-tree-v1.blend'))
objs=[o for o in bpy.data.collections['01_Giant_Tree'].objects if o.type=='MESH'];assert objs
checks['finite_vertices']=all(math.isfinite(c) for o in objs for v in o.data.vertices for c in v.co)
lo,hi=bounds(objs);size=hi-lo;fol=[o for o in objs if o.name.startswith('Tree_Leaf_Clump')];flo,fhi=bounds(fol)
trunk=bpy.data.objects['Tree_Trunk_Limbs'];tv=[v.co for v in trunk.data.vertices if 2.6<v.co.z<3.4 and abs(v.co.x)<9 and abs(v.co.y)<9]
roots=bpy.data.objects['Tree_Roots'];rv=[v.co for v in roots.data.vertices if v.co.z<.6]
m={'height_m':size.z,'crown_width_m':fhi.x-flo.x,'crown_depth_m':fhi.y-flo.y,'trunk_diameter_at_3m_m':max(v.x for v in tv)-min(v.x for v in tv),
   'root_flare_m':max(v.x for v in rv)-min(v.x for v in rv),'crown_underside_m':flo.z,'leaf_clumps':len(fol),'min_z_m':lo.z}
T={'height_m':(62,1.),'crown_width_m':(90,2.),'crown_depth_m':(70,2.5),'trunk_diameter_at_3m_m':(10,1.),'root_flare_m':(22,1.5),'crown_underside_m':(26,1.5),'leaf_clumps':(15,0)}
checks['noted_dimensions']={k:{'target':t,'measured':round(m[k],2),'ok':abs(m[k]-t)<=tol} for k,(t,tol) in T.items()}
checks['origin_on_ground']=abs(lo.z)<.01
checks['triangles']=sum(len(p.vertices)-2 for o in objs for p in o.data.polygons)
size0=size
for fmt in ('glb','fbx'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    (bpy.ops.import_scene.gltf if fmt=='glb' else bpy.ops.import_scene.fbx)(filepath=str(EXP/f'giant-tree.{fmt}'))
    imp=[o for o in bpy.context.scene.objects if o.type=='MESH'];a,b=bounds(imp);err=max(abs((b-a)[i]-size0[i]) for i in range(3))
    checks[f'{fmt}_reimport']={'objects':len(imp),'size_error_m':round(err,4),'ok':len(imp)==len(objs) and err<.05}
hs=set();ok=True
for p in sorted(PREV.glob('[01]*_*.png')):
    d=p.read_bytes();ok&=d[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',d[16:24])==(1024,1024);hs.add(hashlib.sha256(d).hexdigest())
checks['ten_distinct_1024_views']=ok and len(hs)==10
passed=all(v if isinstance(v,bool) else v.get('ok',True) if isinstance(v,dict) and 'ok' in v else True for v in checks.values()) and all(x['ok'] for x in checks['noted_dimensions'].values())
(EXP/'validation.json').write_text(json.dumps({'asset':'giant-tree','version':'v1','blender':bpy.app.version_string,'status':'passed' if passed else 'failed','checks':checks,
    'not_verified':['LOD1','UV / texture bake','collision','Unity import / URP / mobile performance','visual match beyond the ten views reviewed by a person']},ensure_ascii=False,indent=2),encoding='utf-8')
print('VALIDATION','passed' if passed else 'failed',json.dumps(checks['noted_dimensions'],ensure_ascii=False),flush=True)
