"""Staged walk-through of the Qingxi hunt graybox: two player stand-ins and six rabbit stand-ins.

  blender --background --factory-startup --python-exit-code 1 --python docs/graybox/qingxi-hunt/blender/demo/build_hunt_demo.py -- [--render follow,map] [--fps 24] [--speedup 2] [--frames N]

Reads ../../layout.json, packages/content/hunting.json and ../QingxiHuntGraybox_blockout.blend (none are modified) and writes
beside this file: QingxiHuntDemo.blend, demo_report.json and, with --render, demo_follow.mp4 / demo_map.mp4.
Stand-ins are appended copies of art/incoming/dondon QPlayerMale/QPlayerFemale v006 (Idle/Walk) and the static
QMountainRabbit v002; the source files are untouched. Players walk the layout routes; chases, flights and returns use a
0.5 m grid A* around the layout's boxes. It is a scripted rehearsal: no Unity NavMesh, CharacterController, rabbit AI,
combat, drops or merchant API is simulated.
"""
import bpy,bmesh,json,math,heapq,sys,time,random
from pathlib import Path
from mathutils import Vector,Euler
from mathutils.bvhtree import BVHTree
import numpy as np

HERE=Path(__file__).resolve().parent;GRAYBOX=HERE.parent/'QingxiHuntGraybox_blockout.blend';LAYOUT=HERE.parents[1]/'layout.json'
REPO=HERE.parents[4];DONDON=REPO/'art/incoming/dondon';HUNT=REPO/'packages/content/hunting.json'
argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
def arg(name,default):
    return argv[argv.index(name)+1] if name in argv else default
FPS=int(arg('--fps',24));SPEEDUP=float(arg('--speedup',2));RENDER=[r for r in arg('--render','').split(',') if r];MAXFRAMES=int(arg('--frames',0))

D=json.loads(LAYOUT.read_text(encoding='utf-8'));HUNTING=json.loads(HUNT.read_text(encoding='utf-8'))
RABBIT_DEF=next(e for e in HUNTING['enemies'] if e['id']=='qingxi-mountain-rabbit')
NOTICE=RABBIT_DEF['noticeRadiusM'];LEASH=RABBIT_DEF['leashRadiusM']
PLAYER_SPEED=D['player']['speed']
RABBIT_SPEED=5.0     # assumption: no rabbit speed in content yet; faster than a 4 m/s player
DT=.1                # simulation step, game seconds
M={m['name']:m for m in D['markers']}
def P(name):p=M[name]['position'];return Vector((p['x'],p['z']))
def route(name):return [Vector((p['x'],p['z'])) for p in next(r for r in D['routes'] if r['name']==name)['points']]

bpy.ops.wm.open_mainfile(filepath=str(GRAYBOX));S=bpy.context.scene;O=bpy.data.objects
bpy.context.preferences.edit.keyframe_new_interpolation_type='LINEAR'   # factory-startup session only; not saved
OUT_BLEND=HERE/'QingxiHuntDemo.blend';HERE.mkdir(exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))   # work on a copy; the graybox file stays as built

# ------------------------------------------------------------------ ground + collider BVHs
G=next(o for o in O if o.name.startswith('Ground_'))
def bvh_of(objs):
    V=[];F=[]
    for o in objs:
        mw=o.matrix_world;b=len(V);V+=[mw@v.co for v in o.data.vertices];F+=[[b+i for i in p.vertices] for p in o.data.polygons]
    return BVHTree.FromPolygons(V,F)
GROUND=bvh_of([G]);WORLD=bvh_of([o for o in O if o.type=='MESH' and o.get('collider')=='Box']+[G])
def gz(p):
    h=GROUND.ray_cast(Vector((p.x,p.y,60)),Vector((0,0,-1)),120);return h[0].z if h[0] else 0.
def blocked(a,b):
    d=b-a;L=d.length;h=WORLD.ray_cast(a,d.normalized(),L);return h[0] is not None and h[3]<L-1e-3

# ------------------------------------------------------------------ 0.5 m grid A* around the layout boxes (x, z plane)
CELL=.5;W,H=D['bounds']['width'],D['bounds']['depth'];NX,NZ=int(W/CELL)+1,int(H/CELL)+1
def free_grid(radius):
    g=np.ones((NX,NZ),bool);xs=np.arange(NX)*CELL;zs=np.arange(NZ)*CELL
    g[xs<radius,:]=False;g[xs>W-radius,:]=False;g[:,zs<radius]=False;g[:,zs>H-radius]=False
    for o in D['obstacles']:
        p,s=o['position'],o['size'];x0,x1=p['x']-s['x']/2-radius,p['x']+s['x']/2+radius;z0,z1=p['z']-s['z']/2-radius,p['z']+s['z']/2+radius
        g[np.ix_((xs>=x0)&(xs<=x1),(zs>=z0)&(zs<=z1))]=False
    return g
GRID={'player':free_grid(D['player']['radius']),'rabbit':free_grid(D['rabbit']['radius'])}
def cell(p):return (min(NX-1,max(0,round(p.x/CELL))),min(NZ-1,max(0,round(p.y/CELL))))
def seg_free(g,a,b):
    n=max(1,int((b-a).length/(CELL*.5)))
    return all(g[cell(a.lerp(b,i/n))] for i in range(n+1))
def astar(kind,a,b):
    g=GRID[kind];s,t=cell(a),cell(b)
    if not g[s] or not g[t]:raise RuntimeError(f'{kind} A* endpoint blocked {a} {b}')
    q=[(0.,0.,s)];cost={s:0.};prev={}
    while q:
        _,c,n=heapq.heappop(q)
        if n==t:break
        if c>cost[n]:continue
        for dx in (-1,0,1):
            for dz in (-1,0,1):
                if dx==dz==0:continue
                m=(n[0]+dx,n[1]+dz)
                if not(0<=m[0]<NX and 0<=m[1]<NZ) or not g[m] or (dx and dz and not(g[n[0]+dx,n[1]] and g[n[0],n[1]+dz])):continue
                nc=c+math.hypot(dx,dz)
                if nc<cost.get(m,1e18):cost[m]=nc;prev[m]=n;heapq.heappush(q,(nc+math.dist(m,t),nc,m))
    else:raise RuntimeError(f'{kind} A* found no path {a} -> {b}')
    pts=[t]
    while pts[-1]!=s:pts.append(prev[pts[-1]])
    pts=[a]+[Vector((i*CELL,j*CELL)) for i,j in reversed(pts[1:-1])]+[b]
    out=[pts[0]];i=0   # string pulling: keep the farthest point still in straight sight
    while i<len(pts)-1:
        j=len(pts)-1
        while j>i+1 and not seg_free(g,pts[i],pts[j]):j-=1
        out.append(pts[j]);i=j
    return out
def plen(pts):return sum((b-a).length for a,b in zip(pts,pts[1:]))

# ------------------------------------------------------------------ tracks: position samples every DT game seconds
class Track:
    def __init__(s,start,t0=0.):s.t=[t0];s.p=[start.copy()];s.moving=[False]
    @property
    def now(s):return s.t[-1]
    @property
    def pos(s):return s.p[-1]
    def wait_until(s,t):
        while s.now+DT<=t+1e-9:s.t.append(s.now+DT);s.p.append(s.pos.copy());s.moving.append(False)
    def walk(s,pts,speed,stop_short=0.):
        pts=[s.pos]+[q for q in pts[1:]] if (pts[0]-s.pos).length<.6 else [s.pos]+list(pts)
        if stop_short:
            L=plen(pts);keep=L-stop_short;acc=0.;cut=[pts[0]]
            for a,b in zip(pts,pts[1:]):
                l=(b-a).length
                if acc+l>=keep:cut.append(a.lerp(b,(keep-acc)/max(l,1e-9)));break
                cut.append(b);acc+=l
            pts=cut
        for a,b in zip(pts,pts[1:]):
            d=b-a;L=d.length;n=max(1,math.ceil(L/(speed*DT)))
            for i in range(1,n+1):s.t.append(s.now+L/speed/n);s.p.append(a.lerp(b,i/n));s.moving.append(True)
    def at(s,t):
        if t<=s.t[0]:return s.p[0]
        if t>=s.t[-1]:return s.p[-1]
        i=int(np.searchsorted(s.t,t));a,b=s.t[i-1],s.t[i];return s.p[i-1].lerp(s.p[i],(t-a)/max(b-a,1e-9))
    def first(s,pred):
        for t,p in zip(s.t,s.p):
            if pred(t,p):return t
        return None

def offset_path(pts,side,step=.5):
    """Sample a polyline every 0.5 m and shift it sideways by `side` metres (same idea as validate_layout.py's two traces)."""
    out=[]
    for a,b in zip(pts,pts[1:]):
        n=max(1,math.ceil((b-a).length/step));out+=[a.lerp(b,i/n) for i in range(n)]
    out.append(pts[-1]);res=[]
    for i,p in enumerate(out):
        t=(out[min(i+1,len(out)-1)]-out[max(i-1,0)]).normalized();res.append(p+Vector((t.y,-t.x))*side)
    return res

EVENTS=[]   # (time, text) captions, also written to the report
def event(t,text):EVENTS.append((round(t,2),text))

# ---- phase 1: both players walk the main discovery route side by side
main=route('MainDiscovery');L1=offset_path(main,-.8);L2=offset_path(main,.8)
P1=Track(P('PlayerSpawn_01'));P2=Track(P('PlayerSpawn_02'))
start2=min(range(len(L2)),key=lambda i:(L2[i]-P('PlayerSpawn_02')).length)
P1.walk(L1,PLAYER_SPEED)
t_meet=P1.first(lambda t,p:(p-L1[start2]).length<.3) or 0.
P2.wait_until(t_meet);P2.walk(L2[start2:],PLAYER_SPEED)
event(0,'兩名玩家從聚落出口出發（走路 4 m/s）')
for i in range(1,7):
    n=f'TrailClue_{i:02}';tc=P1.first(lambda t,p:(p-P(n)).length<3)
    if tc is not None:event(tc,f'經過腳印線索 T{i:02}（{tc:.1f} 秒）')
th=P1.first(lambda t,p:(p-P('HerbNode_01')).length<6)
if th is not None:event(th,'進入採藥林：沿路有 6 個採藥點')

RABBITS={n:{'home':P(n),'group':M[n]['group'],'track':None} for n in M if M[n]['kind']=='rabbit'}
def sight_time(track,t_end):
    for t,p in zip(track.t,track.p):
        if t>t_end:break
        eye=Vector((p.x,p.y,gz(p)+1.4))
        for n,r in RABBITS.items():
            h=r['home'];tgt=Vector((h.x,h.y,gz(h)+.4))
            if (tgt-eye).length<60 and not blocked(eye,tgt):return t,n
    return None,None
t_main_end=P1.now
t_sight,first_seen=sight_time(P1,t_main_end)
if t_sight is not None:event(t_sight,f'第一次看見山兔 {first_seen[-3:]}（{t_sight:.1f} 秒，60 m 內無遮擋）')

# ---- phase 2: group A notices the players and flees to its flee points
def player_pos(t):return [P1.at(t),P2.at(t)]
flee_report={};taken=set();prey='RabbitSpawn_A01'
group_a=[prey]+sorted(n for n in RABBITS if RABBITS[n]['group']=='A' and n!=prey)
def flee(n):
    home=RABBITS[n]['home'];tn=None
    for t in P1.t:
        if min((q-home).length for q in player_pos(t))<NOTICE:tn=t;break
    if tn is None:flee_report[n]={'notice_s':None,'note':f'no player came within {NOTICE} m; stayed home'};return
    ps=player_pos(tn);flees=[f for f in M if M[f]['kind']=='flee' and M[f]['group']=='A' and f not in taken]
    target=max(flees,key=lambda f:min((P(f)-q).length for q in ps));taken.add(target)
    path=astar('rabbit',home,P(target));tr=Track(home);tr.wait_until(tn);tr.walk(path,RABBIT_SPEED)
    RABBITS[n].update(track=tr,flee=target,notice=tn,flee_path=path)
    flee_report[n]={'notice_s':round(tn,2),'flee_point':target,'path_m':round(plen(path),2),'arrive_s':round(tr.now,2),
                    'flee_point_from_home_m':round((P(target)-home).length,2),'within_leash':(P(target)-home).length<=LEASH}
flee(prey);event(RABBITS[prey]['notice'],f'A01 察覺玩家（{NOTICE} m 內）並逃向逃跑點')

# ---- phase 3: players chase rabbit A01 to its flee point; staged catch
prey_pt=P(RABBITS[prey]['flee'])
chase1=astar('player',P1.pos,prey_pt);P1.walk(chase1,PLAYER_SPEED,stop_short=1.)
chase2=astar('player',P2.pos,prey_pt);P2.walk(chase2,PLAYER_SPEED*.9,stop_short=2.2)
t_catch=max(P1.now,RABBITS[prey]['track'].now)
event(t_catch,f'追上 A01 並捕獲（{t_catch:.1f} 秒；示意，未模擬戰鬥與掉落）')
RABBITS[prey]['track'].wait_until(t_catch);RABBITS[prey]['dead']=t_catch
for n in group_a[1:]:   # the other A rabbit flees if the players came close, waits, then hops home (leash)
    flee(n)
    if RABBITS[n]['track'] is None:continue
    event(RABBITS[n]['notice'],f'{n[-3:]} 也受驚逃開')
    tr=RABBITS[n]['track'];tr.wait_until(max(tr.now,t_catch+4));back=astar('rabbit',tr.pos,RABBITS[n]['home']);tr.walk(back,RABBIT_SPEED*.5)
    flee_report[n]['returned_home_s']=round(tr.now,2)

# ---- phase 4: alternative return to the merchant
alt=route('AlternativeReturn');A1=offset_path(alt,-.8);A2=offset_path(alt,.8)
j1=min(range(len(A1)),key=lambda i:(A1[i]-alt[1]).length);j2=min(range(len(A2)),key=lambda i:(A2[i]-alt[1]).length)
P1.wait_until(t_catch+2.5);P2.wait_until(t_catch+2.5)
P1.walk(astar('player',P1.pos,A1[j1]),PLAYER_SPEED);P2.walk(astar('player',P2.pos,A2[j2]),PLAYER_SPEED)
t_sync=max(P1.now,P2.now);P1.wait_until(t_sync);P2.wait_until(t_sync)
event(t_sync,'沿替代回程經淺灘與捷徑回村')
t_ret0=t_sync;P1.walk(A1[j1:],PLAYER_SPEED);P2.walk(A2[j2:],PLAYER_SPEED)
t_home=max(P1.now,P2.now)
event(t_home,f'回到材料商販（全程 {t_home:.0f} 秒；回程 {t_home-t_catch:.0f} 秒；出售未接 API）')
T_END=t_home+5
for tr in [P1,P2]+[r['track'] for r in RABBITS.values() if r['track']]:tr.wait_until(T_END)
for n,r in RABBITS.items():
    if r['track'] is None:r['track']=Track(r['home']);r['track'].wait_until(T_END)
sep=min((P1.at(t)-P2.at(t)).length for t in np.arange(0,T_END,DT))

# ------------------------------------------------------------------ actors: append stand-ins
def fr(t):return 1+t*FPS/SPEEDUP
S.render.fps=FPS;S.frame_start=1;S.frame_end=int(math.ceil(fr(T_END)))
if MAXFRAMES:S.frame_end=min(S.frame_end,MAXFRAMES)
DEMO=bpy.data.collections.new('Demo_Actors');S.collection.children.link(DEMO)
MAPONLY=bpy.data.collections.new('Demo_MapOnly');S.collection.children.link(MAPONLY)
for o in O:   # hide the static spawn capsules that the stand-ins replace
    if o.name.endswith('_proxy') and o.parent and o.parent.get('kind') in ('player','rabbit'):o.hide_render=o.hide_viewport=True
ACTIONS={}
def append_player(asset,ver):
    path=DONDON/asset/ver/f'{asset}_{ver}.blend'
    with bpy.data.libraries.load(str(path),link=False) as (src,dst):dst.collections=['01_Editable_Asset'];dst.actions=['Idle','Walk']
    ACTIONS[asset]=dict(zip(('Idle','Walk'),dst.actions));col=dst.collections[0];col.name=f'Demo_{asset}';DEMO.children.link(col)
    arm=next(o for o in col.all_objects if o.type=='ARMATURE');arm.name=f'Demo_{asset}_Armature';return arm
ARM1=append_player('QPlayerMale','v006');ARM2=append_player('QPlayerFemale','v006')
def mover(arm,name):   # the empty carries the route motion; the armature keeps its own NLA Idle/Walk
    e=bpy.data.objects.new(name,None);DEMO.objects.link(e);arm.parent=e;arm.location=(0,0,0);arm.rotation_euler=(0,0,0);return e
ROOT1=mover(ARM1,'Demo_P1_Male');ROOT2=mover(ARM2,'Demo_P2_Female')
def append_rabbit():
    path=DONDON/'QMountainRabbit/v002/QMountainRabbit_v002.blend'
    with bpy.data.libraries.load(str(path),link=False) as (src,dst):dst.objects=list(src.objects)
    objs=[o for o in dst.objects if o and o.type not in ('CAMERA','LIGHT')]
    for o in objs:DEMO.objects.link(o)
    for o in [o for o in dst.objects if o and o.type in ('CAMERA','LIGHT')]:bpy.data.objects.remove(o)
    return next(o for o in objs if o.name.startswith('QMountainRabbit_ROOT'))
def clone(root):
    m={}
    def rec(o,parent):
        c=o.copy();DEMO.objects.link(c);c.parent=parent;m[o]=c
        for ch in o.children:rec(ch,c)
        return c
    return rec(root,None)
base=append_rabbit();RROOT={}
for i,n in enumerate(sorted(RABBITS)):RROOT[n]=base if i==0 else clone(base);RROOT[n].name=f'Demo_Rabbit_{n[-3:]}'

def ring(parent,radius,rgb,name):
    bm=bmesh.new();bmesh.ops.create_circle(bm,segments=32,radius=radius,cap_ends=True)
    me=bpy.data.meshes.new(name);bm.to_mesh(me);bm.free();o=bpy.data.objects.new(name,me);MAPONLY.objects.link(o)
    m=bpy.data.materials.new(name);m.use_nodes=True;b=next(x for x in m.node_tree.nodes if x.type=='BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value=(*rgb,1);b.inputs['Emission Color'].default_value=(*rgb,1);b.inputs['Emission Strength'].default_value=2.
    me.materials.append(m);o.parent=parent;o.location=(0,0,.3);return o
ring(ROOT1,2.2,(.1,.35,1.),'MapRing_P1');ring(ROOT2,2.2,(1.,.25,.6),'MapRing_P2')
for n,r in RROOT.items():ring(r,1.6,(1.,.45,.05),'MapRing_'+n[-3:])

def yaw_of(d,prev):
    if d.length<1e-4:return prev
    y=math.atan2(d.x,-d.y)   # stand-ins face -Y
    while y-prev>math.pi:y-=2*math.pi
    while y-prev<-math.pi:y+=2*math.pi
    return y
def key_track(obj,tr,step=.25,zoff=.05,hop=None):
    yaw=0.;ts=list(np.arange(0,T_END+1e-9,step))
    for t in ts:
        p=tr.at(t);d=tr.at(t+step)-tr.at(max(0,t-step));yaw=yaw_of(d,yaw)
        z=gz(p)+zoff+(hop(t,tr) if hop else 0.)
        obj.location=(p.x,p.y,z);obj.rotation_euler=(0,obj.rotation_euler.y,yaw)
        obj.keyframe_insert('location',frame=fr(t));obj.keyframe_insert('rotation_euler',index=2,frame=fr(t))
key_track(ROOT1,P1);key_track(ROOT2,P2)

# walk / idle as NLA strips, play rate like the UE driver: speed / 0.6 m/s, capped at 3.4
def nla(arm,tr,acts):
    ad=arm.animation_data or arm.animation_data_create();ad.action=None
    walk,idle=acts['Walk'],acts['Idle'];rate=min(PLAYER_SPEED/.6,3.4)
    track=ad.nla_tracks.new();track.name='WalkIdle';spans=[];cur=tr.moving[0];t0=0.
    for t,m in zip(tr.t,tr.moving):
        if m!=cur:spans.append((t0,t,cur));t0,cur=t,m
    spans.append((t0,T_END,cur));last=1
    for a,b,mv in spans:
        fa=max(last,int(round(fr(a))));fb=int(round(fr(b)))
        if fb-fa<2:continue
        act=walk if mv else idle;L=act.frame_range[1]-act.frame_range[0]
        sc=FPS/(24*SPEEDUP*(rate if mv else 1.))
        st=track.strips.new(('Walk' if mv else 'Idle')+f'_{fa}',fa,act);st.scale=sc;st.repeat=max(.05,(fb-fa-.02)/(L*sc))
        last=int(math.ceil(st.frame_end))
    return rate
RATE=nla(ARM1,P1,ACTIONS['QPlayerMale']);nla(ARM2,P2,ACTIONS['QPlayerFemale'])

rng=random.Random(9)
def rabbit_keys(n):
    root=RROOT[n];r=RABBITS[n];tr=r['track'];dead=r.get('dead');phase=rng.uniform(0,1.6);yaw=rng.uniform(-math.pi,math.pi)
    t=0.
    while t<=T_END:   # idle hops every 1.6 s, flight hops every 0.18 s
        moving=any(tr.moving[i] for i in range(int(np.searchsorted(tr.t,t)),min(len(tr.t),int(np.searchsorted(tr.t,t+.2))+1)))
        if dead is not None and t>=dead:break
        p=tr.at(t);d=tr.at(t+.2)-tr.at(max(0,t-.2))
        if moving:
            yaw=yaw_of(d,yaw);seq=[(0.,0.),(.09,.28),(.18,0.)];dt_=.18
        else:
            if (t+phase)%1.6>.1:t+=.1;continue
            yaw+=rng.uniform(-.5,.5);seq=[(0.,0.),(.17,.12),(.35,0.)];dt_=.35
        for off,hz in seq:
            q=tr.at(t+off);root.location=(q.x,q.y,gz(q)+.03+hz);root.rotation_euler=(0,0,yaw)
            root.keyframe_insert('location',frame=fr(t+off));root.keyframe_insert('rotation_euler',frame=fr(t+off))
        t+=dt_
    if dead is not None:   # staged catch: tip onto its side, then vanish
        q=tr.at(dead);base_z=gz(q)+.03
        for off,roll,sc in [(0,0,1),(.3,math.pi/2,1),(2.,math.pi/2,1),(2.4,math.pi/2,.01)]:
            root.location=(q.x,q.y,base_z+(.18 if roll else 0));root.rotation_euler=(0,roll,yaw);root.scale=(sc,sc,sc)
            for k in ('location','rotation_euler','scale'):root.keyframe_insert(k,frame=fr(dead+off))
for n in RABBITS:rabbit_keys(n)

# ------------------------------------------------------------------ cameras
def cam(name,ortho=None,fov=60):
    cd=bpy.data.cameras.new(name);c=bpy.data.objects.new(name,cd);S.collection.objects.link(c);cd.clip_start=.1;cd.clip_end=500
    if ortho:cd.type='ORTHO';cd.ortho_scale=ortho
    else:cd.sensor_fit='VERTICAL';cd.angle_y=math.radians(fov)
    return c
FOLLOW=cam('Demo_FollowCam');DIST=6.;ELEV=math.radians(D['camera']['elevationDegrees']);TH=D['camera']['targetHeight']
fdir=Vector((0,1));occl=[];prev_e=None
for t in np.arange(0,T_END+1e-9,.2):
    p=P1.at(t);d=P1.at(t+.6)-P1.at(t)
    if d.length>.2:fdir=(fdir*.75+d.normalized()*.25).normalized()
    tgt=Vector((p.x,p.y,gz(p)+TH));c=tgt-Vector((fdir.x,fdir.y,0))*DIST*math.cos(ELEV)+Vector((0,0,DIST*math.sin(ELEV)))
    e=(tgt-c).to_track_quat('-Z','Y').to_euler()
    if prev_e:e.make_compatible(prev_e)
    prev_e=e;FOLLOW.location=c;FOLLOW.rotation_euler=e
    FOLLOW.keyframe_insert('location',frame=fr(t));FOLLOW.keyframe_insert('rotation_euler',frame=fr(t))
    occl.append((round(float(t),1),blocked(tgt,c)))
longest=cur=0.
for t,b in occl:
    cur=cur+.2 if b else 0.;longest=max(longest,cur)
MAPCAM=O['Preview_Birdseye'];MAP_RES=(1280,round(1280*(H+10)/(W+12)))   # same framing as renders/birdseye.png

# ------------------------------------------------------------------ captions (camera children) and clock
FONT=bpy.data.fonts.load('C:/Windows/Fonts/msjh.ttc') if Path('C:/Windows/Fonts/msjh.ttc').is_file() else None
def text_mat(name,rgb,alpha=1.):
    m=bpy.data.materials.new(name);m.use_nodes=True;b=next(x for x in m.node_tree.nodes if x.type=='BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value=(*rgb,1);b.inputs['Emission Color'].default_value=(*rgb,1);b.inputs['Emission Strength'].default_value=1.
    if alpha<1:
        b.inputs['Alpha'].default_value=alpha
        if hasattr(m,'surface_render_method'):m.surface_render_method='BLENDED'
    return m
MW=text_mat('CaptionWhite',(1,1,.96));MB=text_mat('CaptionBack',(0,0,0),.55)
CAPCOL={}
def label(camobj,body,x,y,size,depth,align='LEFT',back=True):
    cu=bpy.data.curves.new('cap','FONT');cu.body=body;cu.size=size;cu.align_x=align;cu.align_y='CENTER'
    if FONT:cu.font=FONT
    col=CAPCOL.get(camobj.name)
    if col is None:col=CAPCOL[camobj.name]=bpy.data.collections.new('Captions_'+camobj.name);S.collection.children.link(col)
    t=bpy.data.objects.new('Caption',cu);col.objects.link(t);cu.materials.append(MW)
    t.parent=camobj;t.location=(x,y,-depth);t.visible_shadow=False
    if back:
        bm=bmesh.new();bmesh.ops.create_grid(bm,x_segments=1,y_segments=1,size=.5);me=bpy.data.meshes.new('capback');bm.to_mesh(me);bm.free()
        me.materials.append(MB);bg=bpy.data.objects.new('CaptionBack',me);col.objects.link(bg);bg.parent=t;bg.visible_shadow=False
        bg.location=(size*len(body)*.48 if align=='LEFT' else 0,0,-.001);bg.scale=(size*len(body)*1.0+size,size*1.6,1)
    return t
def show(obj,t0,t1):
    for o in [obj]+list(obj.children):
        for f,v in [(1,True),(fr(t0),False),(fr(t1),True)]:
            o.hide_render=v;o.hide_viewport=v;o.keyframe_insert('hide_render',frame=f);o.keyframe_insert('hide_viewport',frame=f)
def caption_set(camobj,ortho):
    if ortho:hw=ortho/2;hh=hw*MAP_RES[1]/MAP_RES[0];depth=10;sz=hh*.045
    else:hh=math.tan(math.radians(30));hw=hh*16/9;depth=1.;sz=hh*.055
    head=label(camobj,'灰盒演示：替身模型與方塊，不是遊戲實機或 Unity 畫面',-hw*.95,hh*.88,sz*.8,depth)
    clock=label(camobj,'遊戲時間 00:00.0',hw*.95,hh*.88,sz*.8,depth,align='RIGHT',back=False)
    times=[e[0] for e in EVENTS]+[T_END]
    for i,(t,txt) in enumerate(sorted(EVENTS)):
        c=label(camobj,txt,-hw*.95,-hh*.84,sz,depth);show(c,t,min(t+6,sorted(times)[i+1] if i+1<len(times) else T_END))
    return clock
CLOCKS=[caption_set(FOLLOW,None),caption_set(MAPCAM,MAPCAM.data.ortho_scale)]
def tick(scene,*_):
    t=(scene.frame_current-1)*SPEEDUP/FPS
    for c in CLOCKS:c.data.body=f'遊戲時間 {int(t//60):02d}:{t%60:04.1f}  ×{SPEEDUP:g}'
bpy.app.handlers.frame_change_pre.append(tick)
S.camera=FOLLOW;bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))

# ------------------------------------------------------------------ report
report={'scope':'Scripted Blender rehearsal on the graybox layout. Not Unity, not NavMesh/CharacterController, no rabbit AI, combat, drops or sales API.',
        'layoutSha256':S.get('layout_sha256'),'fps':FPS,'speedup':SPEEDUP,'frames':S.frame_end,
        'assumptions':{'player_speed_mps':PLAYER_SPEED,'rabbit_flee_speed_mps':RABBIT_SPEED,'notice_radius_m':NOTICE,'leash_radius_m':LEASH,
                       'walk_play_rate':RATE,'grid_cell_m':CELL,'side_by_side_offset_m':.8,'follow_camera_distance_m':DIST},
        'timeline_s':{'main_route_end':round(t_main_end,2),'first_rabbit_seen':t_sight,'first_seen':first_seen,'catch':round(t_catch,2),
                      'return_start':round(t_ret0,2),'home':round(t_home,2),'return_duration_after_catch':round(t_home-t_catch,2)},
        'events':sorted(EVENTS),'rabbit_flights':flee_report,'min_player_separation_m':round(sep,3),
        'follow_camera':{'samples':len(occl),'blocked_samples':sum(b for _,b in occl),'longest_blocked_s':round(longest,1),
                         'blocked_times_s':[t for t,b in occl if b][:60],'note':'No camera collision or pull-in simulated; a blocked sample means the 6 m camera would be behind geometry.'}}
(HERE/'demo_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=float),encoding='utf-8')
print('DEMO built frames',S.frame_end,'T_END',round(T_END,1),'catch',round(t_catch,1),'home',round(t_home,1))

# ------------------------------------------------------------------ renders
def set_video(path,w,h):
    r=S.render;r.resolution_x,r.resolution_y=w,h;r.resolution_percentage=100;r.filepath=str(path)
    try:r.image_settings.media_type='VIDEO'
    except (AttributeError,TypeError):pass
    r.image_settings.file_format='FFMPEG';r.ffmpeg.format='MPEG4';r.ffmpeg.codec='H264';r.ffmpeg.constant_rate_factor='MEDIUM'
for eng in ('BLENDER_EEVEE_NEXT','BLENDER_EEVEE'):
    try:S.render.engine=eng;break
    except TypeError:pass
try:S.eevee.taa_render_samples=16
except AttributeError:pass
PREV=bpy.data.collections['95_Preview_Only']
def vis(col,on):
    for o in col.all_objects:
        if o is not None and o.type!='CAMERA':o.hide_render=not on
for kind in RENDER:
    t0=time.time()
    follow=kind=='follow';vis(PREV,not follow);MAPONLY.hide_render=follow
    CAPCOL[FOLLOW.name].hide_render=not follow;CAPCOL[MAPCAM.name].hide_render=follow
    S.camera=FOLLOW if follow else MAPCAM;set_video(HERE/f'demo_{kind}.mp4',*((1280,720) if follow else MAP_RES))
    bpy.ops.render.render(animation=True);print('RENDERED',kind,round(time.time()-t0,1),'s')
