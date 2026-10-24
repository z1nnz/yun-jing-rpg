"""QCharacters17 v005/v006: the v004 characters with a skeleton, skin weights and two looping in-place actions (Idle, Walk).
Geometry is v004 unchanged, read from Models/<ID>/v004/<ID>_v004.blend; the look is still rebuilt from qchar17_v004.py.
  blender --background --python-exit-code 1 --python rig_qchar17.py             # all 12; finished ones are skipped
  blender --background --python-exit-code 1 --python rig_qchar17.py -- lineup   # design sheets from the 12 v005 files
Skeleton, 17 bones with Unreal-style names; the armature object is named Armature so Unreal does not add an extra root:
root > pelvis > spine > neck > head; spine > upperarm > lowerarm > hand; pelvis > thigh > calf > foot (_l/_r).
_l is the character's left (+X; the character faces -Y). Weights: head, hands, held props and shoes are rigid; sleeves blend
upper/lower arm, legs blend thigh/calf/foot, the robe blends spine/pelvis and, below the hip, the thighs.
v006 (QRIG_VERSION=v006) is the same rig with an FBX for Unreal. v005's FBX kept metres plus a x100 scale on the Armature
node; Unreal skips that node (it is the armature) and its scale with it, so the skeleton came in 100x too small while the
skin did not. FBX_SCALE_ALL did not help (it writes metres with UnitScaleFactor 100, and Unreal converted only the skin).
v006 writes the FBX in centimetres: bones, vertices, Solidify thickness and pelvis location keys are scaled x100 in memory
just before export (the saved .blend stays 1 unit = 1 m), so the file has UnitScaleFactor 1 and no node scale. Parts named
like a bone (Head, Neck) become Head_Mesh / Neck_Mesh (Unreal had renamed the bones to head2 / neck1).
"""
import bpy,json,math,os,sys,importlib.util
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
SRC=Path(__file__).resolve().parent;BATCH=SRC.parent;BASE,VER='v004',os.environ.get('QRIG_VERSION','v005')
UNREAL_FBX=VER>='v006'
os.environ['QCHAR_VERSION']=BASE   # build_qchar17 helpers (studio, aim, fit, VIEWS) and the v004 kit
spec=importlib.util.spec_from_file_location('build_qchar17',SRC/'build_qchar17.py');B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B);Q=B.Q
FPS=24;WALK=24;IDLE=48          # frames per loop; one extra key repeats the first so the clip closes
KNEE,ANKLE=.24,.07
X,Y,Z=(1,0,0),(0,1,0),(0,0,1)

def sstep(a,b,x):t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3-2*t)   # a>b gives the falling ramp

# ------------------------------------------------------------------ skeleton
def skeleton(aid,off):
    """Joint positions from the kit's Body, scaled like the mesh and shifted like build_qchar17 shifted it (off)."""
    sp=Q.CHARACTERS[aid];b=Q.Body(sp.get('girth',1.));s=sp.get('scale',1.)
    P=lambda v:Vector(v)*s+off
    neck_top=b.C.z-b.hr.z;top=b.C.z+b.hr.z+.05
    J={'root':(None,P((0,0,0)),P((0,0,.12))),'pelvis':('root',P((0,0,b.hip)),P((0,0,b.waist))),
       'spine':('pelvis',P((0,0,b.waist)),P((0,0,b.neck-.04))),'neck':('spine',P((0,0,b.neck-.04)),P((0,0,neck_top))),
       'head':('neck',P((0,0,neck_top)),P((0,0,top)))}
    for sx,sd in ((1,'l'),(-1,'r')):
        sh=b.shoulder(sx);hd=b.hand(sx);el=sh.lerp(hd,.5)+Vector((sx*.01,0,0))   # elbow as in build_limbs
        J['upperarm_'+sd]=('spine',P(sh),P(el));J['lowerarm_'+sd]=('upperarm_'+sd,P(el),P(hd))
        J['hand_'+sd]=('lowerarm_'+sd,P(hd),P(hd+(hd-el).normalized()*.06))
        x=sx*.058*b.g
        J['thigh_'+sd]=('pelvis',P((x,0,b.hip)),P((x,0,KNEE)));J['calf_'+sd]=('thigh_'+sd,P((x,0,KNEE)),P((x,0,ANKLE)))
        J['foot_'+sd]=('calf_'+sd,P((x,0,ANKLE)),P((x,-.08,.02)))
    return J,s

def make_armature(coll,J):
    ob=bpy.data.objects.new('Armature',bpy.data.armatures.new('Armature'));coll.objects.link(ob)
    bpy.context.view_layer.objects.active=ob;ob.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    for n,(par,h,t) in J.items():
        e=ob.data.edit_bones.new(n);e.head,e.tail=h,t;e.roll=0.
        if par:e.parent=ob.data.edit_bones[par]
    bpy.ops.object.mode_set(mode='OBJECT');return ob

# ------------------------------------------------------------------ weights
HEAD=('Head','Ear','Blush','Eye','Mouth','Mustache','Beard','Hair','Skull_Cap','Straw_Hat','Elder_Crown','Bun_Ribbon')   # Head* covers Headband, Headscarf
HAND=('Hand','Thumb','Hammer','Staff','Cane','Abacus','Teapot','Axe','Pill_Bottle')   # held props ride on the gripping hand
SPINE=('Sword','Back_Basket','Basket','Capelet','Collar')
CLOTH=('Robe','Hem_Trim','Apron')

def weights(o,J,s,aid):
    n=o.name.split('.')[0];V=[o.matrix_world@v.co for v in o.data.vertices];sd='l' if sum(v.x for v in V)/len(V)>J['root'][1].x else 'r'
    one=lambda bone:[{bone:1.}]*len(V)
    if n.startswith(HEAD):return one('head')
    if n=='Neck':return one('neck')
    if n.startswith(HAND):return one('hand_'+sd)
    if n.startswith(SPINE):return one('spine')
    if n.startswith('Belt'):return one('pelvis')   # belt, knot, tail and the belt gourd
    if n.startswith('Shoe'):return one('foot_'+sd)
    if n.startswith(('Sleeve','Forearm')):
        sh=J['upperarm_'+sd][1];ax=J['lowerarm_'+sd][2]-sh;out=[]
        for v in V:
            t=(v-sh).dot(ax)/ax.length_squared;lw=sstep(.35,.65,t);sp=.5*sstep(.15,0,t)   # elbow blend; shoulder cap half on the spine
            out.append({'spine':sp,'upperarm_'+sd:(1-lw)*(1-sp),'lowerarm_'+sd:lw*(1-sp)})
        return out
    if n.startswith('Leg'):
        k=J['calf_'+sd][1].z;a=J['foot_'+sd][1].z;out=[]
        for v in V:
            c=sstep(k+.035,k-.035,v.z);f=sstep(a+.03,a,v.z)
            out.append({'thigh_'+sd:1-c,'calf_'+sd:c*(1-f),'foot_'+sd:c*f})
        return out
    if n.startswith(CLOTH):
        hip=J['pelvis'][1].z;waist=J['pelvis'][2].z;hem=max(Q.CHARACTERS[aid]['hem']*s+J['root'][1].z,.06);xc=J['root'][1].x;out=[]
        for v in V:
            up=sstep(hip,waist+.04*s,v.z);d=.8*sstep(hip,hem,v.z);L=sstep(-.06,.06,v.x-xc)   # skirt follows the thighs, 80 % at the hem
            out.append({'spine':up,'pelvis':(1-up)*(1-d),'thigh_l':(1-up)*d*L,'thigh_r':(1-up)*d*(1-L)})
        return out
    raise SystemExit(f'{aid}: no bone rule for part {o.name}')

def skin(o,arm,ws):
    for vi,w in enumerate(ws):
        tot=sum(w.values())
        for bn,x in w.items():
            if x>1e-4:(o.vertex_groups.get(bn) or o.vertex_groups.new(name=bn)).add([vi],x/tot,'REPLACE')
    o.parent=arm;o.matrix_parent_inverse=Matrix.Identity(4)   # armature sits at the origin: world transform unchanged
    m=o.modifiers.new('Armature','ARMATURE');m.object=arm

# ------------------------------------------------------------------ actions
def turn(pb,axis,deg):
    """Rotation about a world axis expressed in the bone's rest frame (children turn with their parents)."""
    return Quaternion((pb.bone.matrix_local.to_3x3().inverted()@Vector(axis)).normalized(),math.radians(deg))

def pose_walk(P,ph,grips,leg):
    s,c=math.sin(ph),math.cos(ph);TH=22
    for sd,sg in (('l',1),('r',-1)):
        th=-TH*s*sg                          # thigh: negative = forward; left leg leads while sin>0
        knee=6+34*max(0.,c*sg)**1.5          # bend while the leg swings forward
        P['thigh_'+sd].rotation_quaternion=turn(P['thigh_'+sd],X,th)
        P['calf_'+sd].rotation_quaternion=turn(P['calf_'+sd],X,knee)
        P['foot_'+sd].rotation_quaternion=turn(P['foot_'+sd],X,-.7*(th+knee))
        arm=(9 if sd in grips else 26)*s*sg    # arms swing against the legs; a hand holding a prop swings less
        P['upperarm_'+sd].rotation_quaternion=turn(P['upperarm_'+sd],X,arm)
        P['lowerarm_'+sd].rotation_quaternion=turn(P['lowerarm_'+sd],X,-10)
    # straight legs at full stride raise the hips: drop the pelvis so the planted foot stays on the ground
    P['pelvis'].location=P['pelvis'].bone.matrix_local.to_3x3().inverted()@Vector((0,0,-leg*(1-math.cos(math.radians(TH*abs(s))))))
    P['pelvis'].rotation_quaternion=turn(P['pelvis'],Z,-5*s)
    P['spine'].rotation_quaternion=turn(P['spine'],Z,7*s)@turn(P['spine'],X,3)
    P['head'].rotation_quaternion=turn(P['head'],Z,-2*s)@turn(P['head'],X,-1.5*math.cos(2*ph))

def pose_idle(P,ph,grips,leg):
    P['spine'].rotation_quaternion=turn(P['spine'],X,1.2*math.sin(ph))
    P['head'].rotation_quaternion=turn(P['head'],Y,2.5*math.sin(ph+.8))@turn(P['head'],X,1.*math.sin(2*ph))
    for sd,sg in (('l',1),('r',-1)):
        if sd not in grips:P['upperarm_'+sd].rotation_quaternion=turn(P['upperarm_'+sd],Y,-sg*2.*math.sin(ph))   # arms breathe outward

def bake(ob,name,n,fn,grips,leg):
    act=bpy.data.actions.new(name);act.use_fake_user=True;ob.animation_data.action=act
    for f in range(n+1):
        for pb in ob.pose.bones:pb.rotation_mode='QUATERNION';pb.rotation_quaternion=(1,0,0,0);pb.location=(0,0,0)
        fn(ob.pose.bones,2*math.pi*f/n,grips,leg)
        for pb in ob.pose.bones:
            pb.keyframe_insert('rotation_quaternion',frame=f+1)
            if pb.name=='pelvis':pb.keyframe_insert('location',frame=f+1)
    act.use_frame_range=True;act.frame_start,act.frame_end=1,n+1;act.use_cyclic=True
    return act

# ------------------------------------------------------------------ FBX
def export_fbx(path,arm,objs):
    bpy.context.scene.frame_set(1);bpy.ops.object.select_all(action='DESELECT')
    for o in [arm]+objs:o.select_set(True)
    bpy.context.view_layer.objects.active=arm
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE','MESH'},add_leaf_bones=False,
                             axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',use_mesh_modifiers=True,use_armature_deform_only=True,
                             bake_anim=True,bake_anim_use_all_actions=True,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True)

def fcurves(act):
    for layer in act.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:yield from bag.fcurves

def to_centimetres(arm,objs,k=100.):
    """Rescale the rigged scene in place so 1 Blender unit = 1 cm (Unreal's unit); never saved."""
    s=bpy.context.scene;s.frame_set(1);arm.data.pose_position='REST';s.unit_settings.scale_length=1/k
    bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);bpy.context.view_layer.objects.active=arm;bpy.ops.object.mode_set(mode='EDIT')
    for e in arm.data.edit_bones:e.head*=k;e.tail*=k
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in objs:
        o.data.transform(Matrix.Scale(k,4));o.location*=k
        for m in o.modifiers:
            if m.type=='SOLIDIFY':m.thickness*=k
    for act in bpy.data.actions:
        for fc in fcurves(act):
            if fc.data_path.endswith('.location'):
                for kp in fc.keyframe_points:kp.co.y*=k;kp.handle_left.y*=k;kp.handle_right.y*=k
    arm.data.pose_position='POSE';bpy.context.view_layer.update()

# ------------------------------------------------------------------ per character
ANIM=[('walk_side',(1,0,.12),'Walk',[1,4,7,10,13,16,19,22]),('idle_front',(0,-1,.12),'Idle',[1,13,25,37])]

def rig(aid):
    out=BATCH/'Models'/aid/VER;views=BATCH/'ArtLibrary/Turnarounds'/f'{aid}_{VER}'
    if (views/'views.json').exists():print('ALREADY_COMPLETE',aid,flush=True);return
    out.mkdir(parents=True,exist_ok=True);views.mkdir(parents=True,exist_ok=True);(out/'anim').mkdir(exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(BATCH/'Models'/aid/BASE/f'{aid}_{BASE}.blend'));s=bpy.context.scene
    bpy.context.preferences.filepaths.save_version=0;bpy.context.preferences.edit.keyframe_new_interpolation_type='LINEAR'
    coll=bpy.data.collections['01_Editable_Asset'];root=next(o for o in coll.objects if o.type=='EMPTY')
    objs=[o for o in coll.objects if o.type=='MESH'];off=bpy.data.objects['Head'].location.copy()   # build shifted every part by -off
    J,sc=skeleton(aid,off);arm=make_armature(coll,J)
    grips_txt=root.get('grips','{}');grips={('l' if int(k)>0 else 'r') for k in eval(grips_txt or '{}')}
    arm['grips']=grips_txt;bpy.data.objects.remove(root)
    for o in objs:skin(o,arm,weights(o,J,sc,aid))
    if UNREAL_FBX:
        for o in objs:
            if o.name.split('.')[0].lower() in J:o.name=o.name.split('.')[0]+'_Mesh'+o.name[len(o.name.split('.')[0]):]
    leg=J['thigh_l'][1].z-J['foot_l'][1].z
    arm.animation_data_create();walk=bake(arm,'Walk',WALK,pose_walk,grips,leg);idle=bake(arm,'Idle',IDLE,pose_idle,grips,leg)
    arm.animation_data.action=idle;s.render.fps=FPS;s.frame_start,s.frame_end=1,IDLE+1;s.frame_set(1)
    if not UNREAL_FBX:export_fbx(out/f'{aid}_{VER}.fbx',arm,objs)   # v006 exports after the renders, once the scene is in cm
    v4=json.loads((BATCH/'Models'/aid/BASE/'model_info.json').read_text(encoding='utf-8'))
    info=dict(v4,version=VER,base_geometry=f'Models/{aid}/{BASE}',pose='A-pose rest; Idle and Walk actions',rigged=True,
              skeleton={'armature_object':'Armature','bones':{n:(p or '') for n,(p,_,_) in J.items()},'left_is':'+X (character faces -Y)'},
              actions={'Idle':{'frames':[1,IDLE+1],'fps':FPS,'loop':True,'in_place':True},'Walk':{'frames':[1,WALK+1],'fps':FPS,'loop':True,'in_place':True,'stride_deg':22}},
              skinning='rigid head, hands, held props and shoes; blended sleeves (elbow), legs (knee, ankle) and robe (waist, thighs below the hip)',
              kit='qchar17_v004.py geometry + rig_qchar17.py skeleton/weights/actions',root_motion=False,
              fbx_export={'apply_scale_options':'FBX_SCALE_ALL' if UNREAL_FBX else 'FBX_SCALE_NONE','parts_renamed':{'Head':'Head_Mesh','Neck':'Neck_Mesh'} if UNREAL_FBX else {}})
    (out/'model_info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    bpy.ops.wm.save_as_mainfile(filepath=str(out/f'{aid}_{VER}.blend'))
    # ten views in the rest pose, then fixed-camera animation frames
    cam=s.camera;arm.data.pose_position='REST';bpy.context.view_layer.update()
    lo,hi=B.bounds(objs);centre=(lo+hi)/2;pts=[Vector((x,y,z)) for x in (lo.x,hi.x) for y in (lo.y-.12,hi.y+.12) for z in (lo.z,hi.z)];recs=[]
    for name,d in B.VIEWS:
        B.aim(cam,centre,d);sc_=B.fit(s,cam,pts);s.render.filepath=str(views/(name+'.png'));bpy.ops.render.render(write_still=True)
        recs.append({'file':name+'.png','direction':list(d),'camera_location':list(cam.location),'ortho_scale':sc_,'projection':'orthographic','framing_checked':True,'pose':'rest'})
    arm.data.pose_position='POSE';s.render.resolution_x=s.render.resolution_y=512;s.cycles.samples=24
    for name,d,act,frames in ANIM:
        arm.animation_data.action=bpy.data.actions[act];B.aim(cam,centre,d);B.fit(s,cam,pts)
        for i,f in enumerate(frames):
            s.frame_set(f);s.render.filepath=str(out/'anim'/f'{name}_{i+1:02d}.png');bpy.ops.render.render(write_still=True)
    if UNREAL_FBX:to_centimetres(arm,objs);export_fbx(out/f'{aid}_{VER}.fbx',arm,objs)   # the .blend was saved in metres above
    (views/'views.json').write_text(json.dumps({'asset':aid,'source':f'Models/{aid}/{VER}/{aid}_{VER}.blend','same_geometry':True,'views':recs,
        'animation_frames':{n:{'action':a,'frames':f,'files':[f'Models/{aid}/{VER}/anim/{n}_{i+1:02d}.png' for i in range(len(f))]} for n,_,a,f in ANIM}},indent=2))
    print('ASSET_COMPLETE',aid,flush=True)

# ------------------------------------------------------------------ design sheets: all twelve mid-stride
def lineup():
    out=BATCH/f'DesignSheets_{VER}';out.mkdir(exist_ok=True)
    if (out/'lineup.json').exists():print('ALREADY_COMPLETE lineup');return
    bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene
    st=bpy.data.collections.new('90_Studio');s.collection.children.link(st);ids=list(Q.CHARACTERS);gap=.82;order=[];FR=7
    for i,aid in enumerate(ids):
        p=BATCH/'Models'/aid/VER/f'{aid}_{VER}.blend'
        with bpy.data.libraries.load(str(p)) as (src,dst):dst.collections=['01_Editable_Asset'];dst.actions=['Walk']
        c=dst.collections[0];c.name=aid;s.collection.children.link(c)
        arm=next(o for o in c.objects if o.type=='ARMATURE');x=(i-(len(ids)-1)/2)*gap;arm.location.x=x
        arm.animation_data.action=dst.actions[0];arm.animation_data.action_slot=dst.actions[0].slots[0]
        order.append([aid,Q.CHARACTERS[aid]['zh'],x])
    s.frame_set(FR);bpy.context.view_layer.update()
    objs=[o for o in bpy.data.objects if o.type=='MESH'];lo,hi=B.bounds(objs);centre=(lo+hi)/2
    cam=B.studio(s,st,centre,4.,(3200,800));pts=[Vector((x,y,z)) for x in (lo.x,hi.x) for y in (lo.y,hi.y) for z in (lo.z,hi.z)];shots={}
    from bpy_extras.object_utils import world_to_camera_view
    for name,d in (('lineup_front',(0,-1,.08)),('lineup_three_quarter',(.35,-1,.2)),('lineup_back',(0,1,.08))):
        B.aim(cam,centre,d);B.fit(s,cam,pts,.03);s.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
        shots[name]=[[aid,zh,world_to_camera_view(s,cam,Vector((x,0,0))).x] for aid,zh,x in order];print('LINEUP',name,flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/f'QCharacters17_lineup_{VER}.blend'))
    (out/'lineup.json').write_text(json.dumps({'characters':order,'label_x_fraction':shots,'pose':f'Walk frame {FR}',
        'note':f'Linked from the per-character {VER} files'},ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else list(Q.CHARACTERS)
    if args==['lineup']:lineup()
    else:
        for aid in args:rig(aid)
