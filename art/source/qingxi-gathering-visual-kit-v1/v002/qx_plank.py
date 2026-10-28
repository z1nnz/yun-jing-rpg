"""QX_CreekSteppingPlank v002: creek stepping module, semi-real. One repeatable bay of a low plank walk.
v002 follows the reviewed AI three-view R05 (art/references/.../ai_threeview_v002): two T supports instead of
v001's four piles. Bottom to top: a heap of wet river cobbles round each pile foot (one big boulder in front) |
one central round pile per support, hewn smooth with drying checks, dark and wet low down under a ragged
green algae band | a round cross log across the full width on each pile, growth rings showing at both ends,
lashed with hemp rope coils and forged iron I-cramps | three hewn deck boards along the walk, slightly cupped,
with a worn tread and square-head spikes.
The board tops are the only light, flat, continuous surface (the foot surface), 0.62 m above the base.
Where R05's side view contradicts its front view (it draws the cross log along the walk), the front view is
followed, as recorded in ai_threeview_v002/REVIEW.md.
Origin: bottom centre (creek bed); front -Y; the walking direction is along Y.
"""
import bpy,bmesh,math,random
from mathutils import Vector,Matrix,noise
import qx_kit as K
import qx_ore as O
import qx_gate as G

TAU=math.tau
SUP_Y=(-.26,.26)            # the two T supports along the walk
PILE_R,LOG_R=.10,.068
Z_TOP,BOARD_T=.62,.055
Z_LOG=Z_TOP-BOARD_T-LOG_R   # log centre: the boards sit on top of the logs
WATER=.20

def log_into(bm,gl,p0,p1,r,seed,n=20,rows=14,taper=.03,ends=True):
    """Round hewn log p0->p1: slightly irregular section, faint adze flats, G = (across, across, along)
    in metres so the timber shader grows rings round the pith and lays the grain along the log."""
    p0,p1=Vector(p0),Vector(p1);d=p1-p0;L=d.length;ax=d/L
    u=ax.cross(Vector((0,0,1)))
    if u.length<.01:u=ax.cross(Vector((0,1,0)))
    u.normalize();w=ax.cross(u);rr=[]
    for j in range(rows+1):
        t=j/rows;row=[]
        for i in range(n):
            a=i*TAU/n;ca,sa=math.cos(a),math.sin(a)
            k=r*(1-taper*t)*(1+.045*noise.noise(Vector((ca*1.3,sa*1.3,t*L*2+seed)))+.012*noise.noise(Vector((a*5,t*L*9,seed))))
            k*=1-.035*max(0,math.cos(a*5+seed))                                                    # adze flats
            v=bm.verts.new(p0+ax*L*t+u*ca*k+w*sa*k);v[gl]=(ca*k+.012,sa*k-.008,t*L+seed*3.1,1);row.append(v)
        rr.append(row)
    for a_,b_ in zip(rr,rr[1:]):
        for i in range(n):bm.faces.new((a_[i],a_[(i+1)%n],b_[(i+1)%n],b_[i]))
    for row,c,flip in ((rr[0],p0,True),(rr[-1],p1,False)):                                           # end grain: fan to the pith
        cv=bm.verts.new(c+(ax*(-.003 if flip else .003)));cv[gl]=(.012,-.008,(0 if flip else L)+seed*3.1,1)
        for i in range(n):
            f=(row[(i+1)%n],row[i],cv) if flip else (row[i],row[(i+1)%n],cv);bm.faces.new(f)

def coil_into(bm,x0,x1,y,z,R,turns,r,sides=7):
    """Rope coil wound round an X-axis log: rings framed on the radial direction, so the tube never flips
    where the helix runs vertical; a slight ply bulge every few rings."""
    N=int(turns*16);rows=[]
    for j in range(N+1):
        t=j/N;a=t*turns*TAU;c=Vector((x0+(x1-x0)*t,y+R*math.cos(a),z+R*math.sin(a)))
        rad=Vector((0,math.cos(a),math.sin(a)));tan=Vector(((x1-x0)/(turns*TAU),-R*math.sin(a),R*math.cos(a))).normalized()
        w=tan.cross(rad).normalized();rr=r*(1+.12*math.sin(j*2.1));row=[]
        for i in range(sides):
            b=i*TAU/sides;row.append(bm.verts.new(c+rad*math.cos(b)*rr+w*math.sin(b)*rr))
        rows.append(row)
    for p,q in zip(rows,rows[1:]):
        for i in range(sides):bm.faces.new((p[i],p[(i+1)%sides],q[(i+1)%sides],q[i]))
    bm.faces.new(list(reversed(rows[0])));bm.faces.new(rows[-1])

def mat_pile(name):
    """Hewn round pile: warm brown wood with flame grain and drying checks along the length; dark wet wood
    below the waterline, a ragged green algae band climbing above it, pale silt line on top."""
    m,nt,bs=K.pbr(name,True,.8,.3);g=K.node(nt,'ShaderNodeAttribute',attribute_name='G').outputs['Vector'];a,b,L=K.sep(nt,g)
    ob=K.coord(nt);x,y,z=K.sep(nt,ob);mr,mx,ad,mrng=K.mul,K.mix,K.add,K.mrange
    fib=K.noise_t(nt,K.comb(nt,mr(nt,a,90),mr(nt,b,90),mr(nt,L,2.5)),1,4)
    col=K.ramp(nt,ad(nt,mr(nt,fib,.6),mr(nt,K.noise_t(nt,g,1.5,3),.4)),[(0,(.085,.058,.036)),(.5,(.15,.105,.065)),(1,(.23,.17,.11))])
    chk=K.voronoi_t(nt,K.comb(nt,mr(nt,a,26),mr(nt,b,26),mr(nt,L,.9)),1,'DISTANCE_TO_EDGE')
    check=mr(nt,mrng(nt,chk,.03,.006),mrng(nt,K.noise_t(nt,g,2.2,2),.42,.55));col=mx(nt,mr(nt,check,.9),col,(.018,.012,.008))
    col=mx(nt,mr(nt,mrng(nt,K.noise_t(nt,ob,3,3),.5,.7),.4),col,(.20,.19,.17))                      # silvered patches
    edge=ad(nt,WATER+.10,mr(nt,ad(nt,K.noise_t(nt,ob,9,4),-.5),.22))                                 # ragged top of the algae band
    alg=mr(nt,mrng(nt,z,edge,ad(nt,edge,-.03)),mrng(nt,K.noise_t(nt,ob,30,4),.30,.45))
    wet=mrng(nt,ad(nt,z,mr(nt,K.noise_t(nt,ob,8,3),.05)),WATER+.04,WATER-.04)
    col=mx(nt,mr(nt,wet,.8),col,(.022,.02,.014))
    col=mx(nt,alg,col,K.ramp(nt,K.noise_t(nt,ob,120,3),[(0,(.022,.045,.012)),(.5,(.05,.085,.02)),(1,(.11,.13,.035))]))
    silt=mr(nt,mrng(nt,z,ad(nt,edge,.0),ad(nt,edge,.02)),mrng(nt,z,ad(nt,edge,.07),ad(nt,edge,.04)));col=mx(nt,mr(nt,silt,.35),col,(.16,.15,.12))
    hgt=ad(nt,ad(nt,mr(nt,fib,.4),mr(nt,check,-1.5)),mr(nt,alg,.8))
    K.finish(nt,bs,col,mx(nt,K.math_(nt,'MAXIMUM',wet,mr(nt,alg,.6)),(.82,.82,.82),(.38,.38,.38)),hgt,.5,.004);return m

def build(post):
    rng=random.Random(3502);ctx=K.ctx
    M={'pile':mat_pile('QX_Src_Plank_Pile'),'log':G.mat_timber('QX_Src_Plank_Cross_Log',.08),'board':G.mat_timber('QX_Src_Plank_Board',.15,tread=True),
       'iron':G.mat_iron('QX_Src_Plank_Iron'),'rope':K.M['rope'],
       'stone':O.mat_rock_real('QX_Src_Plank_Cobble',False,False,[(0,(.075,.08,.08)),(.5,(.13,.135,.135)),(1,(.19,.19,.185))]),'moss':O.mat_moss_real('QX_Src_Plank_Algae_Moss')}
    # --- heap of river cobbles round each pile foot: one big boulder in front, a ring of mid stones, pebbles
    cb=bmesh.new();k=0
    for si,y in enumerate(SUP_Y):
        stones=[(0,y-.17,.13,0)]+[(.17*math.cos(a)+rng.uniform(-.03,.03),y+.15*math.sin(a)+rng.uniform(-.03,.03),rng.uniform(.065,.10),a) for a in [j*TAU/9+si for j in range(9)]]
        stones+=[(rng.uniform(.18,.30)*math.cos(a),y+rng.uniform(.16,.26)*math.sin(a),rng.uniform(.03,.05),a) for a in [rng.uniform(0,TAU) for _ in range(12)]]
        stones+=[(.115*math.cos(a),y+.115*math.sin(a),rng.uniform(.06,.08),a) for a in [j*TAU/7+.4 for j in range(7)]]
        for x,yy,s,a in stones:
            if math.hypot(x,yy-y)<PILE_R+s*.35 and s<.12:continue
            b=O.hull_block((x,yy,s*.50),(s*1.25,s*1.05,s*.95),620+k,90,.85,(0,0,a+rng.uniform(-.5,.5)),rmin=.96);O.finish_block(b,s*.30,0.0,10);K.merge_into(cb,b);k+=1
    G.dressed('Plank_Cobble_Heaps',cb,M['stone'],M['moss'],42,.005,.06,.20,True)
    # --- central round piles
    pb,pg=G.gbm()
    for k,y in enumerate(SUP_Y):log_into(pb,pg,(rng.uniform(-.006,.006),y,0),(0,y+rng.uniform(-.006,.006),Z_LOG-LOG_R*.55),PILE_R,k+1,22,12,.04)
    G.to_obj('Plank_Piles',pb,M['pile'])
    # --- round cross logs across the full width, ring ends showing
    lb,lg=G.gbm()
    for k,y in enumerate(SUP_Y):log_into(lb,lg,(-.445,y,Z_LOG),(.445,y+rng.uniform(-.01,.01),Z_LOG+rng.uniform(-.004,.004)),LOG_R,10+k,20,16,.05)
    G.to_obj('Plank_Cross_Logs',lb,M['log'])
    # --- three deck boards, the foot surface
    db,dg=G.gbm();zc=Z_TOP-BOARD_T/2;XB=(-.25,0,.25)
    for k,x in enumerate(XB):
        w=.232+rng.uniform(-.006,.004)
        G.member(db,dg,(x,-.39+rng.uniform(-.01,.01),zc),(x+rng.uniform(-.006,.006),.39+rng.uniform(-.01,.01),zc),w,BOARD_T,(0,0,1),.18,0,.003,30+k,.06,(.0,-.09))
    for v in db.verts:                                                                              # cupping: board edges lift a few mm
        cx=min(XB,key=lambda q:abs(q-v.co.x));u=(v.co.x-cx)/.116
        if v.co.z>zc:v.co.z+=.003*u*u
    G.to_obj('Plank_Foot_Surface_Boards',db,M['board'])
    # --- hemp lashing: a coil round each log near both ends
    rp=K.new_bm()
    for y in SUP_Y:
        for sx in (-1,1):
            coil_into(rp,sx*.30-.045,sx*.30+.045,y,Z_LOG,LOG_R+.012,4.2,.011)
    K.link('Plank_Rope_Lashing',rp,[M['rope']])
    # --- forged iron: I-cramps over each rope coil (front and back), square-head spikes through the boards
    ib=bmesh.new()
    for y in SUP_Y:
        for sx in (-1,1):
            for sy in (-1,1):
                yf=y+sy*(LOG_R+.024);h=2*LOG_R+.012
                bmesh.ops.create_cube(ib,size=1,matrix=Matrix.Translation((sx*.30,yf,Z_LOG))@Matrix.Diagonal((.020,.010,h,1)))
                for dz in (-1,1):bmesh.ops.create_cube(ib,size=1,matrix=Matrix.Translation((sx*.30,yf-sy*.008,Z_LOG+dz*h/2))@Matrix.Diagonal((.052,.026,.014,1)))
    for x in XB:
        for y in SUP_Y:
            for dx in (-.07,.07):
                c=(x+dx+rng.uniform(-.006,.006),y+rng.uniform(-.006,.006),Z_TOP+.003);sz=.018
                bmesh.ops.create_cube(ib,size=1,matrix=Matrix.Translation(c)@Matrix.Rotation(rng.uniform(-.4,.4),4,'Z')@Matrix.Diagonal((sz,sz,.007,1)))
    bmesh.ops.bevel(ib,geom=ib.edges[:],offset=.0015,segments=1,affect='EDGES',clamp_overlap=True)
    G.to_obj('Plank_Forged_Iron',ib,M['iron'])
    ctx.extra.update({'reference':'ai_threeview_v002/R05_QX_CreekSteppingPlank.png','foot_surface_top_m':Z_TOP,'foot_surface_size_m':[.732,.78],
                      'supports':'2 T supports (one central pile + one round cross log each)','support_spacing_m':SUP_Y[1]-SUP_Y[0],'waterline_m':WATER})
