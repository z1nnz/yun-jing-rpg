"""QX_CreekSteppingPlank rebuild: creek stepping module, semi-real. One repeatable bay of a low plank walk.
Structure, bottom to top: river cobbles packed round the pile feet (algae, wet) | four barked round piles,
axe-trimmed flat on top, a green algae band and dark wet wood below the waterline | two hewn cross beams sat
in saddle notches, held by forged iron cramps | three hewn deck boards, slightly cupped, with drying checks
and a lighter, smoother worn tread down the middle, forged square-head spikes.
The board tops are the only light, flat, continuous surface (the foot surface), 0.62 m above the base.
Origin: bottom centre (creek bed); front -Y; the walking direction is along Y.
"""
import bpy,bmesh,math,random
from mathutils import Vector,Matrix,noise
import qx_kit as K
import qx_ore as O
import qx_gate as G

TAU=math.tau
PILES=[(-.30,-.22),(.30,-.22),(-.30,.22),(.30,.22)]
Z_BEAM,Z_TOP=.53,.62
WATER=.16

def pile_into(bm,gl,x,y,r,H,seed):
    """Barked round log: irregular section, bark furrows along the length, slight lean, axe-cut top facets."""
    rng=random.Random(seed);n=20;rows=[];lean=Vector((rng.uniform(-.015,.015),rng.uniform(-.015,.015),0))
    for j in range(15):
        t=j/14;z=H*t;c=Vector((x,y,z))+lean*t;row=[]
        for i in range(n):
            a=i*TAU/n;d=Vector((math.cos(a),math.sin(a),0))
            fur=.16*max(0,noise.noise(Vector((a*2.6,z*1.4,seed))))+.06*noise.noise(Vector((a*7,z*6,seed)))
            rr=r*(1+.06*noise.noise(Vector((math.cos(a)*1.5,math.sin(a)*1.5,z*2+seed)))-.04*t)*(1-fur*.35)
            if t==1:rr*=.86
            v=bm.verts.new(c+d*rr);v[gl]=(d.x*rr,d.y*rr,z+seed*3.1,1);row.append(v)
        rows.append(row)
    for a,b in zip(rows,rows[1:]):
        for i in range(n):bm.faces.new((a[i],a[(i+1)%n],b[(i+1)%n],b[i]))
    top=bm.verts.new(Vector((x,y,H))+lean+Vector((0,0,.004)));top[gl]=(0,0,H+seed*3.1,1)
    for i in range(n):bm.faces.new((rows[-1][i],rows[-1][(i+1)%n],top))
    bm.faces.new(list(reversed(rows[0])))

def mat_bark(name):
    """Barked pile: dark grey-brown furrowed bark with lighter ridges, a few peeled patches showing grey
    weathered wood; dark wet wood below the waterline, green algae band at it, pale silt line above."""
    m,nt,bs=K.pbr(name,True,.85,.3);g=K.node(nt,'ShaderNodeAttribute',attribute_name='G').outputs['Vector'];a,b,L=K.sep(nt,g)
    ob=K.coord(nt);x,y,z=K.sep(nt,ob);mr,mx,ad,mrng=K.mul,K.mix,K.add,K.mrange
    fur=K.noise_t(nt,K.comb(nt,K.mul(nt,a,60),K.mul(nt,b,60),K.mul(nt,z,4)),2,5,.6)
    col=K.ramp(nt,fur,[(0,(.025,.020,.016)),(.5,(.065,.052,.040)),(1,(.13,.11,.085))])
    peel=mrng(nt,K.noise_t(nt,K.comb(nt,K.mul(nt,a,9),K.mul(nt,b,9),K.mul(nt,z,1.4)),2,4),.62,.66)
    col=mx(nt,peel,col,K.ramp(nt,K.noise_t(nt,K.comb(nt,K.mul(nt,a,80),K.mul(nt,b,80),K.mul(nt,z,2)),1,3),[(0,(.12,.11,.095)),(1,(.22,.20,.17))]))
    wet=mrng(nt,ad(nt,z,mr(nt,K.noise_t(nt,ob,8,3),.04)),WATER+.02,WATER-.02)
    col=mx(nt,mr(nt,wet,.75),col,(.018,.02,.014))
    alg=mr(nt,mr(nt,mrng(nt,z,WATER-.08,WATER-.02),mrng(nt,z,WATER+.07,WATER+.01)),mrng(nt,K.noise_t(nt,ob,14,4),.35,.55))
    col=mx(nt,alg,col,K.ramp(nt,K.noise_t(nt,ob,90,3),[(0,(.03,.055,.018)),(1,(.07,.10,.03))]))
    silt=mr(nt,mrng(nt,z,WATER+.03,WATER+.05),mrng(nt,z,WATER+.09,WATER+.06));col=mx(nt,mr(nt,silt,.45),col,(.15,.14,.11))
    K.finish(nt,bs,col,mx(nt,wet,(.86,.86,.86),(.35,.35,.35)),ad(nt,mr(nt,fur,1.0),mr(nt,peel,-.3)),.6,.006);return m

def build(post):
    rng=random.Random(3501);ctx=K.ctx
    M={'pile':mat_bark('QX_Src_Plank_Pile_Bark'),'beam':G.mat_timber('QX_Src_Plank_Beam',.6,True),'board':G.mat_timber('QX_Src_Plank_Board',.85,tread=True),
       'iron':G.mat_iron('QX_Src_Plank_Iron'),'stone':O.mat_rock_real('QX_Src_Plank_Cobble',False,False,[(0,(.055,.06,.062)),(.5,(.095,.10,.104)),(1,(.135,.135,.13))]),'moss':O.mat_moss_real('QX_Src_Plank_Algae_Moss')}
    # --- river cobbles packed round the pile feet
    cb=bmesh.new()
    for k,(x,y) in enumerate(PILES):
        for j in range(5):
            a=j*TAU/5+k+rng.uniform(-.3,.3);d=rng.uniform(.09,.13);s=rng.uniform(.045,.075)
            b=O.hull_block((x+d*math.cos(a),y+d*math.sin(a),s*.35),(s*1.4,s*1.1,s*.8),600+k*10+j,40,.5,(0,0,a),rmin=.75);O.finish_block(b,s*.15,0.0);K.merge_into(cb,b)
    G.dressed('Plank_Cobbles',cb,M['stone'],M['moss'],41,.005,.22,.25,True)
    # --- barked piles
    pb,pg=G.gbm()
    for k,(x,y) in enumerate(PILES):pile_into(pb,pg,x,y,rng.uniform(.058,.066),Z_BEAM-.035,k+1)
    G.to_obj('Plank_Barked_Piles',pb,M['pile'])
    # --- hewn cross beams in saddle notches
    bb,bg=G.gbm()
    for k,y in enumerate((-.22,.22)):G.member(bb,bg,(-.41,y,Z_BEAM),(.41,y,Z_BEAM),.10,.08,(0,0,1),.25,0,.006,20+k,.1,(.03,.05))
    G.to_obj('Plank_Hewn_Beams',bb,M['beam'])
    # --- three deck boards, the foot surface
    db,dg=G.gbm();zc=Z_TOP-.025
    for k,x in enumerate((-.25,0,.25)):
        w=.232+rng.uniform(-.006,.004);G.member(db,dg,(x,-.36+rng.uniform(-.01,.01),zc),(x+rng.uniform(-.006,.006),.36+rng.uniform(-.01,.01),zc),w,.05,(0,0,1),.18,0,.003,30+k,.06,(.0,-.09))
    for v in db.verts:                                                                              # cupping: board edges lift a few mm
        cx=min((-.25,0,.25),key=lambda q:abs(q-v.co.x));u=(v.co.x-cx)/.116
        if v.co.z>zc:v.co.z+=.003*u*u
    G.to_obj('Plank_Foot_Surface_Boards',db,M['board'])
    # --- forged iron: square-head spikes through the boards, cramps over the beam-pile joints
    ib=bmesh.new()
    for x in (-.25,0,.25):
        for y in (-.22,.22):
            for dx in (-.06,.06):
                c=(x+dx+rng.uniform(-.006,.006),y+rng.uniform(-.006,.006),Z_TOP+.003);sz=.016
                bmesh.ops.create_cube(ib,size=1,matrix=Matrix.Translation(c)@Matrix.Rotation(rng.uniform(-.4,.4),4,'Z')@Matrix.Diagonal((sz,sz,.006,1)))
    for x,y in PILES:                                                                              # flat strap dogs: beam face down onto the pile, spiked at both ends
        for sy in (-1,1):
            sb,sg=G.gbm();ys=y+sy*.053
            G.member(sb,sg,(x,ys,Z_BEAM+.025),(x,ys+sy*.014,Z_BEAM-.105),.026,.006,(0,sy,0),.3,0,0,0,.05);K.merge_into(ib,sb)
            for z,dy in ((Z_BEAM+.012,0),(Z_BEAM-.09,.012)):
                bmesh.ops.create_cube(ib,size=1,matrix=Matrix.Translation((x,ys+sy*(dy+.006),z))@Matrix.Diagonal((.013,.006,.013,1)))
    bmesh.ops.bevel(ib,geom=ib.edges[:],offset=.0012,segments=1,affect='EDGES',clamp_overlap=True)
    G.to_obj('Plank_Forged_Iron',ib,M['iron'])
    ctx.extra.update({'foot_surface_top_m':Z_TOP,'foot_surface_size_m':[.732,.72],'waterline_m':WATER})
