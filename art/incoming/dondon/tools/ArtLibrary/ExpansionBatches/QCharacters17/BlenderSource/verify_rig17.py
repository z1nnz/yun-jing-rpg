"""Verify the rigged QCharacters17 v005/v006 files (rig_qchar17.py; QRIG_VERSION) and write ../validation_<version>.json.
  blender --background --python-exit-code 1 --python verify_rig17.py
Checks: 17-bone armature; every part skinned to it with weights summing to 1; Idle/Walk present and looping; rest pose
unchanged from v004 (size, bottom-centre pivot); hands, feet and head stay attached through both actions; the walking
feet reach the ground without sinking; FBX round trip keeps the armature, parts, size and both actions; ten 1024 views
and the animation frames exist.
"""
import bpy,json,math,struct,hashlib,importlib.util,os
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
SRC=Path(__file__).resolve().parent;BATCH=SRC.parent;VER=os.environ.get('QRIG_VERSION','v005')
os.environ['QCHAR_VERSION']='v004'
spec=importlib.util.spec_from_file_location('rig',SRC/'rig_qchar17.py');R=importlib.util.module_from_spec(spec);spec.loader.exec_module(R);Q=R.Q
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
BONES={'root','pelvis','spine','neck','head'}|{f'{b}_{s}' for b in ('upperarm','lowerarm','hand','thigh','calf','foot') for s in 'lr'}

def world_verts(o,dg):
    e=o.evaluated_get(dg);m=e.to_mesh();v=[e.matrix_world@x.co for x in m.vertices];e.to_mesh_clear();return v
def bounds(objs,dg):
    pts=[p for o in objs for p in world_verts(o,dg)];return Vector([min(p[i] for p in pts) for i in range(3)]),Vector([max(p[i] for p in pts) for i in range(3)])
def gap(A,Bs,dg):
    """Smallest distance from part group A to part group B (evaluated, world space)."""
    pb=[p for o in Bs for p in world_verts(o,dg)];kd=KDTree(len(pb))
    for i,p in enumerate(pb):kd.insert(p,i)
    kd.balance();pa=[p for o in A for p in world_verts(o,dg)];step=max(1,len(pa)//400)
    return min(kd.find(p)[2] for p in pa[::step])

import sys
ONLY=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else None   # spot-check a few; the report is written only for all 12
results=[]
for aid,sp in Q.CHARACTERS.items():
    if ONLY and aid not in ONLY:continue
    p=BATCH/'Models'/aid/VER/f'{aid}_{VER}.blend';bpy.ops.wm.open_mainfile(filepath=str(p));s=bpy.context.scene
    arm=bpy.data.objects['Armature'];objs=[o for o in bpy.data.collections['01_Editable_Asset'].objects if o.type=='MESH']
    assert {b.name for b in arm.data.bones}==BONES,(aid,'bones')
    clash=[o.name for o in objs if o.name.split('.')[0].lower() in BONES]
    assert VER<'v006' or not clash,(aid,'part names clash with bones',clash)   # Unreal renames such bones
    for o in objs:
        md=[m for m in o.modifiers if m.type=='ARMATURE'];assert o.parent==arm and md and md[0].object==arm,(aid,o.name)
        gi={g.index for g in o.vertex_groups if g.name in BONES}
        for v in o.data.vertices:
            w=sum(g.weight for g in v.groups if g.group in gi);assert abs(w-1)<1e-3,(aid,o.name,v.index,w)
    acts={a.name:a for a in bpy.data.actions};assert {'Idle','Walk'}<=set(acts),(aid,'actions')
    assert tuple(acts['Idle'].frame_range)==(1,R.IDLE+1) and tuple(acts['Walk'].frame_range)==(1,R.WALK+1)
    # rest pose = v004 shape
    arm.data.pose_position='REST';bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
    lo,hi=bounds(objs,dg);size=hi-lo;v4=json.loads((BATCH/'Models'/aid/'v004'/'model_info.json').read_text(encoding='utf-8'))
    assert abs(lo.z)<.001 and max(abs(size[i]-v4['dimensions_m'][i]) for i in range(3))<.002,(aid,'rest',size)
    rx=arm.data.bones['root'].head_local.x;side=lambda o:'l' if sum(v.co.x for v in o.data.vertices)/len(o.data.vertices)>rx else 'r'
    nm=lambda o:o.name.split('.')[0].removesuffix('_Mesh')   # v006 renames Head/Neck for Unreal
    pairs={'head-neck':([o for o in objs if nm(o)=='Head'],[o for o in objs if nm(o)=='Neck'])}
    for sd in 'lr':
        pairs['hand-sleeve_'+sd]=([o for o in objs if nm(o).startswith(('Hand','Thumb')) and side(o)==sd],[o for o in objs if nm(o).startswith(('Sleeve','Forearm')) and side(o)==sd])
        pairs['shoe-leg_'+sd]=([o for o in objs if nm(o)=='Shoe' and side(o)==sd],[o for o in objs if nm(o)=='Leg' and side(o)==sd])
    assert all(a and b for a,b in pairs.values()),(aid,'pairs')
    rest={k:gap(a,b,dg) for k,(a,b) in pairs.items()}
    arm.data.pose_position='POSE';worst={k:0. for k in pairs};loop={}
    soles=[o for o in objs if nm(o)=='Shoe_Sole'];lowest=[];sink=0.;ly=[]
    for act,n,frames in (('Idle',R.IDLE,range(1,R.IDLE+2,6)),('Walk',R.WALK,range(1,R.WALK+2))):
        arm.animation_data.action=acts[act]
        s.frame_set(1);m0=[b.matrix.copy() for b in arm.pose.bones];s.frame_set(n+1)
        loop[act]=max(abs(a[i][j]-b.matrix[i][j]) for a,b in zip(m0,arm.pose.bones) for i in range(4) for j in range(4))
        assert loop[act]<1e-4,(aid,act,'loop')
        for f in frames:
            s.frame_set(f);dg=bpy.context.evaluated_depsgraph_get()
            for k,(a,b) in pairs.items():worst[k]=max(worst[k],gap(a,b,dg)-rest[k])
            if act=='Walk':
                zs=[min(p.z for p in world_verts(o,dg)) for o in soles];lowest.append(min(zs));sink=min(sink,min(zs))
                l=next(o for o in objs if nm(o)=='Shoe' and side(o)=='l');ly.append(sum(p.y for p in world_verts(l,dg))/len(l.data.vertices))
    stride=max(ly)-min(ly)
    checks={'bones':len(BONES),'weights_sum_to_one':True,'loop_error':loop,'attachment_growth_m':worst,'walk_planted_foot_max_height_m':max(lowest),
            'walk_sole_min_z_m':sink,'walk_foot_travel_m':stride}
    assert max(worst.values())<.01,(aid,worst)
    assert max(lowest)<.03 and sink>-.02 and stride>.08,(aid,checks)
    count=len(objs)
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(p.with_suffix('.fbx')))
    arms=[o for o in bpy.context.scene.objects if o.type=='ARMATURE'];imp=[o for o in bpy.context.scene.objects if o.type=='MESH']
    assert len(arms)==1 and {b.name for b in arms[0].data.bones}==BONES,(aid,'fbx armature')
    arm_scale=list(arms[0].matrix_world.to_scale())
    names=[a.name for a in bpy.data.actions];assert any(n.endswith('Walk') for n in names) and any(n.endswith('Idle') for n in names),(aid,names)
    arms[0].data.pose_position='REST';bpy.context.view_layer.update();a,b=bounds(imp,bpy.context.evaluated_depsgraph_get());err=max(abs(size[i]-(b-a)[i]) for i in range(3))
    assert len(imp)==count and err<.002,(aid,len(imp),count,err)
    folder=BATCH/'ArtLibrary/Turnarounds'/f'{aid}_{VER}';man=json.loads((folder/'views.json').read_text())
    assert len(man['views'])==10 and len({tuple(v['direction']) for v in man['views']})==10;hs=set()
    for v in man['views']:
        d=(folder/v['file']).read_bytes();assert d[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',d[16:24])==(1024,1024);hs.add(hashlib.sha256(d).hexdigest())
    assert len(hs)==10
    frames=[f for a in man['animation_frames'].values() for f in a['files']];assert len(frames)==12 and all((BATCH/f).exists() for f in frames)
    results.append({'asset':aid,'name_zh':sp['zh'],'blend_reopened':True,'bottom_center_pivot':True,'height_m':size.z,'mesh_objects':count,'checks':checks,
                    'fbx_reimported':True,'fbx_actions':sorted(names),'fbx_armature_scale_in_blender':arm_scale,'part_bone_name_clashes':clash,'fbx_dimension_error_m':err,'distinct_1024_views':10,'animation_frames':12,
                    'blend_sha256':sha(p),'fbx_sha256':sha(p.with_suffix('.fbx'))})
    print('VERIFIED',aid,{k:round(v,4) for k,v in worst.items()},round(max(lowest),4),round(sink,4),round(stride,3),flush=True)
if ONLY:raise SystemExit(0)
ds=BATCH/f"DesignSheets_{VER}";sheets=[f.name for f in ds.glob('lineup_*.png')];assert len(sheets)==3
(BATCH/f'validation_{VER}.json').write_text(json.dumps({'batch':'QCharacters17','version':VER,'blender':bpy.app.version_string,'assets':results,'design_sheets':sheets,
    'not_verified':['Unreal import, retargeting and in-game playback','cloth / hair secondary motion (robe and hair are skinned, not simulated)',
                    'arm-robe and hair-shoulder intersections in every frame (only hand, foot and head attachment is measured)','UV and texture bake','LOD',
                    'in-game scale against doors and furniture']},ensure_ascii=False,indent=2),encoding='utf-8')
print('ALL_VERIFIED',len(results),flush=True)
