"""QX_GatheringLandmark v002: herb-gatherers' two-post timber paifang under a tiled roof. Semi-real.
v002 follows the reviewed AI three-view R04 (art/references/.../ai_threeview_v002): heavier near-round posts on
square clamp stones carved with cloud scrolls and bound in iron, one raking strut per post set outward, a
through-tenoned tie beam with wedges and two drying-herb bundles, a wide framed jade plaque between studs, a
lintel with carved que-ti brackets, a row of dou-gong bracket sets, and a concave grey-teal tiled roof with
flying corners, barrel tiles and end discs, a ridge with curling end scrolls and a jade pearl on a lotus base.
Jade banners hang from poles that run out past the lintel ends; a paper lantern hangs from the left lintel end;
a herb basket stands outside the left post. The back of the plaque is plain.
Origin: bottom centre on the path axis; the path runs along Y through the opening; front -Y.
"""
import bpy,bmesh,math,random
from mathutils import Vector,Matrix,noise
import qx_kit as K
import qx_ore as O
import qx_chilu as C

TAU=math.tau
PX=1.40                     # post centre |x|: 0.58 m clamp stones leave a 2.22 m clear opening at the ground
PR=.32                      # post section (octagonal, nearly round)
ST=.58                      # clamp stone width
Z_TIE,Z_LINTEL=2.45,3.20
Z_PLAQUE=(Z_TIE+.12+Z_LINTEL-.13)/2
Z_EAVE,ROOF_H=3.70,.34      # top surface at the straight eave edge / rise to the ridge
XE,YE,RX=2.45,.92,1.62      # roof half-length, half-depth at the eave, ridge half-length

# ---------------------------------------------------------------- geometry
def gbm():
    bm=bmesh.new();return bm,bm.verts.layers.float_color.new('G')

def member(bm,gl,p0,p1,w,h,up=(0,0,1),ch=.22,taper=0.0,warp=0.0,seed=0,step=.2,pith=(.0,.0)):
    """Hewn timber swept p0->p1: chamfered rectangle, slight taper / bow / hand-hewn wobble.
    G = (across, across, along) in member space, metres, so the shader grows rings round the pith
    and lays the grain along the member whatever its direction."""
    p0,p1=Vector(p0),Vector(p1);d=p1-p0;L=d.length;dz=d/L;side=dz.cross(Vector(up)).normalized();upv=side.cross(dz).normalized()
    c=min(w,h)*ch*.5;prof=[(w/2-c,h/2),(-w/2+c,h/2),(-w/2,h/2-c),(-w/2,-h/2+c),(-w/2+c,-h/2),(w/2-c,-h/2),(w/2,-h/2+c),(w/2,h/2-c)]
    n=max(2,int(L/step)+1);rows=[]
    for i in range(n+1):
        t=i/n;s=1-taper*t;bow=math.sin(t*math.pi)*warp
        row=[]
        for k,(a,b) in enumerate(prof):
            j=.004*noise.noise(Vector((seed+k*.7,t*L*3,0)))
            v=bm.verts.new(p0+dz*L*t+side*(a*s+j)+upv*(b*s+j)+side*bow);v[gl]=(a+pith[0],b+pith[1],t*L+seed*3.1,1);row.append(v)
        rows.append(row)
    for a,b in zip(rows,rows[1:]):
        for k in range(8):bm.faces.new((a[k],a[(k+1)%8],b[(k+1)%8],b[k]))
    bm.faces.new(list(reversed(rows[0])));bm.faces.new(rows[-1])

def to_obj(name,bm,mat,smooth=True):
    K.ctx.vdata.clear()
    if smooth:
        for f in bm.faces:f.smooth=True
    me=bpy.data.meshes.new(name+'_Mesh');bm.to_mesh(me);bm.free();o=bpy.data.objects.new(name,me);K.ctx.coll.objects.link(o)
    o.parent=K.ctx.root;K.ctx.objs.append(o);me.materials.append(mat)
    if smooth:
        for p in me.polygons:p.use_smooth=True
    return o

def stone_lp(name,bm):
    me=bpy.data.meshes.new(name+'_Mesh');bm.to_mesh(me);bm.free();o=bpy.data.objects.new(name,me);K.ctx.coll.objects.link(o);return o

def dressed(name,bm,mat,moss_mat,seed,voxel=.009,amp=.38,scale=.55,moss=True):
    """Game low poly (hidden in review) + remeshed, weathered high poly + optional moss cushions."""
    K.ctx.vdata.clear()
    lp=stone_lp(name,bm);lp.parent=K.ctx.root;lp.data.materials.append(mat);lp.hide_render=True;lp['qx_role']='game_low_poly';K.ctx.objs.append(lp)
    hp=O.remeshed(lp,name+'_HP',K.ctx.coll,voxel,2);hp.parent=K.ctx.root;hb,l2=O.sculpt(hp,scale,amp,seed,False,moss)
    hp.data.materials.append(mat);hp['qx_role']='bake_source_high_poly';K.ctx.objs.append(hp)
    if moss:
        ms=O.moss_shell(hb,l2,name+'_Moss',K.ctx.coll,.016);ms.parent=K.ctx.root;ms.data.materials.append(moss_mat);K.ctx.objs.append(ms)
    hb.free();return hp

def loft(bm,sections):
    """sections: list of rings (same vertex count), closed ends."""
    rows=[[bm.verts.new(p) for p in ring] for ring in sections];n=len(rows[0])
    for a,b in zip(rows,rows[1:]):
        for k in range(n):bm.faces.new((a[k],a[(k+1)%n],b[(k+1)%n],b[k]))
    bm.faces.new(list(reversed(rows[0])));bm.faces.new(rows[-1])

# ---------------------------------------------------------------- materials
def emblem(nt,du,dv,sc=1.0):
    """Gatherers' mark in metres around (0,0): five lanceolate leaves fanning up from a stem point,
    inside a thin ring. Returns a 0..1 mask socket."""
    mr,ad,mrng,m_=K.mul,K.add,K.mrange,K.math_
    out=None
    for k in range(5):
        a=math.pi/2+(k-2)*.55;L=(.15,.12,.09)[abs(k-2)]*sc;W=.024*sc;c,s_=math.cos(a),math.sin(a)
        x=ad(nt,du,0.0);y=ad(nt,dv,.085*sc)
        qx=ad(nt,mr(nt,x,c),mr(nt,y,s_));qy=ad(nt,mr(nt,x,-s_),mr(nt,y,c))
        t=m_(nt,'MINIMUM',m_(nt,'MAXIMUM',m_(nt,'DIVIDE',qx,L),0.0),1.0)
        hw=ad(nt,mr(nt,m_(nt,'POWER',m_(nt,'SINE',mr(nt,t,math.pi)),.8),W),.0005)
        leaf=mr(nt,mr(nt,mrng(nt,qx,0,.004),mrng(nt,qx,L,L-.004)),mrng(nt,m_(nt,'SUBTRACT',m_(nt,'ABSOLUTE',qy),hw),.002,-.002))
        out=leaf if out is None else m_(nt,'MAXIMUM',out,leaf)
    rad=K.node(nt,'ShaderNodeVectorMath',{0:K.comb(nt,du,dv,0)},operation='LENGTH').outputs['Value']
    ring=mr(nt,mrng(nt,rad,.155*sc,.160*sc),mrng(nt,rad,.176*sc,.171*sc))
    return m_(nt,'MAXIMUM',out,ring)

def mat_timber(name,weather=.55,dark=False,tread=False):
    """Semi-real weathered hewn timber: growth rings round the pith (flame grain on the faces), long
    drying checks along the grain, silver-grey weathering on exposed faces, dark runoff streaks under
    the coping, mud splash at the foot, worn lighter arrises, grime in the joints."""
    m,nt,bs=K.pbr(name,True,.8,.35);g=K.node(nt,'ShaderNodeAttribute',attribute_name='G').outputs['Vector'];a,b,L=K.sep(nt,g)
    ob=K.coord(nt);x,y,z=K.sep(nt,ob);geo=K.node(nt,'ShaderNodeNewGeometry');nz=K.sep(nt,geo.outputs['Normal'])[2];pt=geo.outputs['Pointiness']
    mr,mx,ad,mrng=K.mul,K.mix,K.add,K.mrange
    ring=K.node(nt,'ShaderNodeTexWave',{'Vector':K.comb(nt,a,b,K.mul(nt,L,.35)),'Scale':34,'Distortion':5,'Detail':3,'Detail Scale':1.2},wave_type='RINGS',rings_direction='Z',wave_profile='SAW').outputs['Fac']
    late=mrng(nt,ring,.72,.95);fib=K.noise_t(nt,K.comb(nt,K.mul(nt,a,90),K.mul(nt,b,90),K.mul(nt,L,2.5)),1,4)
    base=[(0,(.115,.083,.055)),(1,(.205,.155,.105))] if not dark else [(0,(.06,.042,.03)),(1,(.12,.085,.058))]
    col=K.ramp(nt,ad(nt,mr(nt,fib,.55),mr(nt,K.noise_t(nt,g,1.2,3),.45)),base)
    col=mx(nt,mr(nt,late,.55),col,(.065,.046,.032))
    wt=mr(nt,mrng(nt,ad(nt,K.noise_t(nt,K.comb(nt,K.mul(nt,a,6),K.mul(nt,b,6),K.mul(nt,L,.8)),3,4),mr(nt,nz,.25)),.35,.62),weather)
    col=mx(nt,wt,col,K.ramp(nt,fib,[(0,(.17,.165,.15)),(1,(.27,.26,.24))]))                       # silvered weathering
    chk=K.voronoi_t(nt,K.comb(nt,K.mul(nt,a,26),K.mul(nt,b,26),K.mul(nt,L,1.1)),1,'DISTANCE_TO_EDGE')
    check=mr(nt,mrng(nt,chk,.035,.008),mrng(nt,K.noise_t(nt,g,2.2,2),.45,.55))
    col=mx(nt,mr(nt,check,.9),col,(.018,.013,.009))
    streak=K.noise_t(nt,K.scaled(nt,ob,(26,26,.9)),3,3)
    col=mx(nt,mr(nt,mr(nt,mrng(nt,streak,.55,.72),mrng(nt,z,2.0,3.2)),.5),col,(.05,.045,.04))
    mud=mr(nt,mrng(nt,ad(nt,z,mr(nt,K.noise_t(nt,ob,9,4),.18)),.42,.12),.85);col=mx(nt,mud,col,(.045,.036,.026))
    col=mx(nt,mr(nt,mrng(nt,pt,.505,.56),.5),col,(.30,.27,.22))
    cav=mrng(nt,O.ao(nt,.06),.95,.5);col=mx(nt,mr(nt,cav,.7),col,(.025,.02,.016))
    moss=mr(nt,mr(nt,mrng(nt,z,.55,.15),mrng(nt,nz,-.2,.5)),mrng(nt,K.noise_t(nt,ob,3,4),.5,.62))
    col=mx(nt,moss,col,K.ramp(nt,K.noise_t(nt,ob,60,3),[(0,(.03,.045,.014)),(1,(.07,.09,.026))]))
    hgt=ad(nt,ad(nt,mr(nt,late,.35),mr(nt,fib,.4)),mr(nt,check,-1.5));rough=ad(nt,.74,mr(nt,wt,.16))
    if tread:                                                                                     # worn walking line: lighter, smoother, checks filled with grit
        wear=mr(nt,mr(nt,mrng(nt,nz,.85,.97),mrng(nt,K.math_(nt,'ABSOLUTE',x),.36,.10)),mrng(nt,ad(nt,K.noise_t(nt,ob,5,4),mr(nt,K.math_(nt,'ABSOLUTE',y),-.4)),.25,.55))
        col=mx(nt,mr(nt,wear,.7),col,K.ramp(nt,fib,[(0,(.20,.18,.15)),(1,(.30,.28,.24))]));rough=mx(nt,wear,rough,(.55,.55,.55))
        hgt=mx(nt,wear,hgt,mr(nt,hgt,.4))
    K.finish(nt,bs,col,rough,hgt,.4,.004);return m

def mat_plaque(name,zc):
    """Lacquered plaque: dark lacquer with crazing, faded jade field, raised pale-jade emblem, paint
    worn through to grey wood on the arrises and the lower edge."""
    m,nt,bs=K.pbr(name,True,.45,.45);ob=K.coord(nt);r,g,b=K.attr(nt);geo=K.node(nt,'ShaderNodeNewGeometry');pt=geo.outputs['Pointiness']
    craze=K.mrange(nt,K.voronoi_t(nt,ob,38,'DISTANCE_TO_EDGE'),.02,.004)
    col=K.ramp(nt,r,[(0,(.025,.022,.02)),(.45,(.03,.075,.06)),(.55,(.05,.11,.09)),(1,(.40,.58,.48))])   # r: 0 frame, .5 field, 1 emblem
    col=K.mix(nt,K.mul(nt,K.mrange(nt,K.noise_t(nt,ob,4,4),.45,.7),.18),col,(.08,.09,.075))
    x,y,z=K.sep(nt,ob);em=K.mul(nt,emblem(nt,x,K.math_(nt,'SUBTRACT',z,zc),.85),K.mrange(nt,r,.3,.45))
    col=K.mix(nt,K.mul(nt,em,K.mrange(nt,K.noise_t(nt,ob,40,3),.2,.4)),col,(.40,.58,.48))
    wear=K.mul(nt,K.mrange(nt,K.noise_t(nt,ob,14,4),.6,.7),.7)
    col=K.mix(nt,wear,col,(.20,.18,.15));col=K.mix(nt,K.mul(nt,craze,.6),col,(.01,.01,.01))
    K.finish(nt,bs,col,K.mix(nt,wear,(.42,.42,.42),(.8,.8,.8)),K.add(nt,K.add(nt,craze,K.noise_t(nt,ob,60,3)),K.mul(nt,em,2.5)),.15,.002);return m

def mat_iron(name):
    m,nt,bs=K.pbr(name,True,.6,.5,.85);ob=K.coord(nt);n=K.noise_t(nt,ob,18,5)
    rust=K.mrange(nt,K.add(nt,K.noise_t(nt,ob,5,4),K.mul(nt,n,.3)),.5,.75)
    col=K.mix(nt,rust,K.ramp(nt,n,[(0,(.035,.035,.038)),(1,(.08,.08,.085))]),K.ramp(nt,n,[(0,(.10,.04,.015)),(1,(.22,.10,.04))]))
    bs.inputs['Metallic'].default_value=.0;nt.links.new(K.mix(nt,rust,(.85,.85,.85),(.1,.1,.1)),bs.inputs['Metallic'])
    K.finish(nt,bs,col,K.mix(nt,rust,(.5,.5,.5),(.9,.9,.9)),n,.3,.002);return m

def mat_banner(name):
    """Faded jade linen: weave, sun-bleached upper part, dirt toward the frayed hem, pale emblem (Var.r=1)."""
    m,nt,bs=K.pbr(name,False,.9,.25);ob=K.coord(nt);r,g,b=K.attr(nt);u,v=K.uv(nt)
    weave=K.mul(nt,K.wave_t(nt,K.scaled(nt,ob,(1,1,1)),260,'X',0,0),K.wave_t(nt,ob,260,'Z',0,0))
    col=K.ramp(nt,K.add(nt,K.mul(nt,K.noise_t(nt,ob,3,4),.6),K.mul(nt,v,.4)),[(0,(.022,.07,.06)),(.6,(.05,.13,.105)),(1,(.10,.20,.16))])
    col=K.mix(nt,K.mul(nt,K.mrange(nt,v,.3,.0),.55),col,(.07,.075,.055))                      # dirt toward the hem
    du=K.mul(nt,K.math_(nt,'SUBTRACT',u,.5),.26);dv=K.mul(nt,K.math_(nt,'SUBTRACT',v,.78),1.78)
    rad=K.node(nt,'ShaderNodeVectorMath',{0:K.comb(nt,du,dv,0)},operation='LENGTH').outputs['Value']
    emb=emblem(nt,du,dv,.62)
    band=K.add(nt,K.mul(nt,K.mrange(nt,v,.915,.92),K.mrange(nt,v,.94,.935)),K.mul(nt,K.mrange(nt,v,.60,.605),K.mrange(nt,v,.615,.61)))
    paint=K.mul(nt,K.math_(nt,'MINIMUM',K.add(nt,emb,band),1.0),K.mrange(nt,K.noise_t(nt,ob,30,3),.25,.45))
    col=K.mix(nt,paint,col,(.40,.52,.43));col=K.mix(nt,K.mul(nt,weave,.15),col,(0,0,0))
    sub=bs.inputs.get('Subsurface Weight')
    if sub:sub.default_value=.15
    K.finish(nt,bs,col,None,K.add(nt,weave,K.mul(nt,paint,.8)),.12,.002);return m

def mat_paper(name):
    m,nt,bs=K.pbr(name,True,.8,.3,0,(1,.55,.22),2.2);ob=K.coord(nt);f=K.noise_t(nt,ob,40,4)
    col=K.ramp(nt,f,[(0,(.55,.36,.18)),(1,(.78,.56,.30))]);nt.links.new(K.ramp(nt,K.noise_t(nt,ob,6,3),[(0,(.8,.38,.12)),(1,(1,.6,.25))]),bs.inputs['Emission Color'])
    K.finish(nt,bs,col,None,f,.2,.002);return m

def mat_pearl(name):
    m,nt,bs=K.pbr(name,True,.18,.5);ob=K.coord(nt);bs.inputs['IOR'].default_value=1.6
    K._set(nt,bs.inputs['Transmission Weight'],.55);n=K.noise_t(nt,ob,9,4)
    col=K.ramp(nt,n,[(0,(.22,.48,.42)),(1,(.55,.82,.72))]);nt.links.new(K.ramp(nt,n,[(0,(.02,.18,.14)),(1,(.15,.7,.55))]),bs.inputs['Emission Color'])
    bs.inputs['Emission Strength'].default_value=.6;K.finish(nt,bs,col,None,n,.05,.002);return m

def mat_roof_tile(name):
    """Fired grey-teal barrel tiles: per-tile tone shifts, rain streaks down the slope, moss settled on the
    upward faces and in the channels, lichen dots; darker soffit under the eaves."""
    m,nt,bs=K.pbr(name,True,.62,.4);ob=K.coord(nt);nz=K.normal_z(nt)
    mr,mx,ad,mrng=K.mul,K.mix,K.add,K.mrange
    n=K.noise_t(nt,ob,5,4);cell=K.sep(nt,K.voronoi_t(nt,K.scaled(nt,ob,(7,2.5,7)),1,'F1','Color'))[0]
    col=K.ramp(nt,ad(nt,mr(nt,cell,.5),mr(nt,n,.5)),[(0,(.040,.052,.054)),(.5,(.064,.082,.084)),(1,(.094,.112,.110))])
    col=mx(nt,mr(nt,mrng(nt,K.noise_t(nt,K.scaled(nt,ob,(30,4,1)),3,3),.55,.75),.45),col,(.026,.030,.032))
    col=mx(nt,mrng(nt,nz,.1,-.4),col,(.03,.024,.02))
    moss=mr(nt,mrng(nt,nz,.25,.75),mrng(nt,ad(nt,K.noise_t(nt,ob,2.2,5),mr(nt,K.noise_t(nt,ob,14,3),.25)),.58,.70))
    mc=K.ramp(nt,K.noise_t(nt,ob,90,3),[(0,(.032,.050,.014)),(.6,(.075,.100,.028)),(1,(.13,.14,.045))])
    col=mx(nt,moss,col,mc)
    dots=mr(nt,mrng(nt,K.voronoi_t(nt,ob,60),.10,.05),mrng(nt,K.noise_t(nt,ob,4),.55,.62));col=mx(nt,mr(nt,dots,.7),col,(.20,.21,.16))
    K.finish(nt,bs,col,mx(nt,moss,(.55,.55,.55),(.95,.95,.95)),ad(nt,mr(nt,moss,1.2),mr(nt,K.noise_t(nt,ob,60,3),.5)),.3,.004);return m

def mat_wicker(name):
    """Split-cane wicker: golden straw with darker weathered strands and dirt toward the foot."""
    m,nt,bs=K.pbr(name,True,.75,.35);ob=K.coord(nt);x,y,z=K.sep(nt,ob);n=K.noise_t(nt,K.scaled(nt,ob,(1,1,6)),40,3)
    col=K.ramp(nt,K.add(nt,K.mul(nt,n,.7),K.mul(nt,K.noise_t(nt,ob,4,3),.3)),[(0,(.10,.065,.03)),(.5,(.21,.14,.065)),(1,(.32,.23,.11))])
    col=K.mix(nt,K.mrange(nt,z,.12,.0),col,(.07,.055,.035))
    K.finish(nt,bs,col,None,n,.25,.002);return m

PALE_STONE=[(0,(.15,.148,.14)),(.45,(.21,.205,.195)),(.75,(.19,.18,.165)),(1,(.25,.245,.235))]

# ---------------------------------------------------------------- build
def roof_up(x):e=max(0.0,(abs(x)-1.15)/(XE-1.15));return .46*e**2.3
def roof_ye(x):e=max(0.0,(abs(x)-1.15)/(XE-1.15));return YE+.14*e**2
def roof_ridge(x):e=max(0.0,(abs(x)-RX)/(XE-RX));return Z_EAVE+ROOF_H*(1-e**1.4)
def roof_z(x,t):
    """Top surface at x, t in -1..1 across (0 = ridge): concave slope, eaves curling up toward the corners."""
    eave=Z_EAVE+roof_up(x);ridge=max(roof_ridge(x),eave+.03);return eave+(ridge-eave)*(1-abs(t))**1.7

def cloud_into(bm,c,u,n,s):
    """Carved cloud scroll in relief on a face: two curling volutes, a crest arc and a wavy tail, as
    half-sunk round mouldings. c centre, u face-right, n face-out (unit), s size (m)."""
    up=n.cross(u);c=Vector(c)
    for cx,dirn in ((-.34,1),(.34,-1)):
        pts=[];rad=[]
        for k in range(22):
            t=k/21;a=math.pi*.15+t*1.35*TAU;r=(.30-.24*t)*s
            pts.append(c+u*(cx*s+dirn*r*math.cos(a))+up*(r*math.sin(a))+n*.002);rad.append(.032*s*(1-.5*t)+.003)
        K.tube_into(bm,pts,rad,7)
    K.tube_into(bm,[c+u*(math.cos(a)*.62*s)+up*(.18*s+math.sin(a)*.32*s)+n*.002 for a in [math.pi*(.12+.76*k/14) for k in range(15)]],[.030*s]*15,7)
    K.tube_into(bm,[c+u*((-.75+1.5*k/12)*s)+up*(-.42*s+.05*s*math.sin(k/12*TAU))+n*.002 for k in range(13)],[.022*s]*13,7)

def build(post):
    rng=random.Random(5102);ctx=K.ctx
    M={'stone':O.mat_rock_real('QX_Src_Gate_Dressed_Stone',False,False,PALE_STONE),'moss':O.mat_moss_real('QX_Src_Gate_Moss'),
       'post':mat_timber('QX_Src_Gate_Timber_Post',.6),'beam':mat_timber('QX_Src_Gate_Timber_Beam',.45),'dark':mat_timber('QX_Src_Gate_Timber_Dark',.25,True),
       'plaque':mat_plaque('QX_Src_Gate_Plaque',Z_PLAQUE),'iron':mat_iron('QX_Src_Gate_Iron'),'tile':mat_roof_tile('QX_Src_Gate_Roof_Tile'),
       'banner':mat_banner('QX_Src_Gate_Jade_Banner'),'paper':mat_paper('QX_Src_Gate_Lantern_Paper'),'pearl':mat_pearl('QX_Src_Gate_Jade_Pearl'),
       'skirt':O.mat_skirt('QX_Src_Gate_Ground'),'herb':C.mat_leaf_real('QX_Src_Gate_Dried_Herb'),'seed':C.mat_berry_real('QX_Src_Gate_Dried_Seed',True),
       'flower':C.mat_berry_real('QX_Src_Gate_Dried_Flower'),'wicker':mat_wicker('QX_Src_Gate_Wicker')}
    PAD=(2.75,1.45)
    # --- ground pad with loose stones round the plinths (the path itself is not part of the landmark)
    sk=K.new_bm();O.skirt_into(sk,PAD,.03,18,96,9);K.link('Gate_Ground_Blend',sk,[M['skirt']])
    fl=bmesh.new();n=0
    for k in range(300):
        if n>=16:break
        sx=rng.choice((-1,1));a=rng.uniform(0,TAU);r=rng.uniform(.48,.90);x,y=sx*PX+r*math.cos(a),r*.8*math.sin(a)
        if abs(x)<PX-.45 or abs(x)>PX+.75 and abs(y)<.35:continue
        sz=rng.uniform(.05,.12);z=O.skirt_height(x,y,PAD,.03)
        b=O.hull_block((x,y,z+sz*.1),(sz*1.3,sz,sz*.6),700+k,30,.6,(0,0,rng.uniform(0,TAU)),rmin=.7);O.finish_block(b,sz*.1,max(z-.002,0));K.merge_into(fl,b);n+=1
    dressed('Gate_Foot_Stones',fl,M['stone'],M['moss'],21,.008,.25,.45,True)
    # --- clamp stones: plinth slab + square block round each post, carved cloud scrolls on all four faces
    for sx in (-1,1):
        bm=bmesh.new();cx=sx*PX
        bmesh.ops.create_cube(bm,size=1,matrix=Matrix.Translation((cx,0,.05))@Matrix.Diagonal((ST+.20,ST+.20,.10,1)))
        bmesh.ops.bevel(bm,geom=bm.edges[:],offset=.02,segments=2,affect='EDGES')
        b2=bmesh.new();bmesh.ops.create_cube(b2,size=1,matrix=Matrix.Translation((cx,0,.10+.36))@Matrix.Diagonal((ST,ST,.72,1)))
        for v in b2.verts:
            if v.co.z>.7:v.co.x=cx+(v.co.x-cx)*.92;v.co.y*=.92                                        # slight batter to the top
        bmesh.ops.bevel(b2,geom=b2.edges[:],offset=.03,segments=2,affect='EDGES');K.merge_into(bm,b2)
        b3=bmesh.new()
        for n_,u_ in (((0,-1,0),(1,0,0)),((0,1,0),(-1,0,0)),((1,0,0),(0,1,0)),((-1,0,0),(0,-1,0))):
            n_,u_=Vector(n_),Vector(u_);cloud_into(b3,Vector((cx,0,.36))+n_*(ST/2-.012),u_,n_,.16)
        K.merge_into(bm,b3)
        dressed('Gate_Clamp_Stone_'+('L' if sx<0 else 'R'),bm,M['stone'],M['moss'],30+sx,.006,.18,.45,True)
    # --- posts and raking struts (outward and a little back)
    pb,pg=gbm()
    for i,sx in enumerate((-1,1)):member(pb,pg,(sx*PX,0,.10),(sx*PX,0,Z_LINTEL+.12),PR,PR,(0,1,0),1.0,.04,.006,11+i,pith=(.02,-.02))
    to_obj('Gate_Posts',pb,M['post'])
    sb,sg=gbm();struts=[]
    for i,sx in enumerate((-1,1)):
        top=Vector((sx*(PX+PR*.42),.05,1.62));foot=Vector((sx*(PX+.86),.30,.03));struts.append((top,foot))
        member(sb,sg,foot,top,.16,.16,(0,1,0),1.0,.05,.008,21+i)
    to_obj('Gate_Raking_Struts',sb,M['dark'])
    # --- tie beam with through-tenons, studs, lintel, bracket-set layer, eave plate
    bb,bg=gbm()
    member(bb,bg,(-PX-.38,0,Z_TIE),(PX+.38,0,Z_TIE),.20,.24,(0,0,1),.2,0,.01,31)
    member(bb,bg,(-PX-.62,0,Z_LINTEL),(PX+.62,0,Z_LINTEL),.22,.26,(0,0,1),.2,0,.012,33,step=.12)
    for sx in (-1,1):member(bb,bg,(sx*.80,0,Z_TIE+.12),(sx*.80,0,Z_LINTEL-.13),.12,.11,(0,1,0),.25,0,0,40+sx)
    zp=Z_LINTEL+.13
    for k in range(9):                                                                               # dou-gong sets: block, crossed arms, three top blocks
        x=-2.0+k*.5;s=80+k*7
        member(bb,bg,(x,0,zp),(x,0,zp+.08),.15,.15,(0,1,0),.3,0,0,s,step=.5)
        member(bb,bg,(x,-.26,zp+.12),(x,.26,zp+.12),.08,.08,(0,0,1),.3,0,0,s+1,step=.5)
        member(bb,bg,(x-.17,0,zp+.12),(x+.17,0,zp+.12),.08,.08,(0,0,1),.3,0,0,s+2,step=.5)
        for j,dy in enumerate((-.21,0,.21)):member(bb,bg,(x,dy,zp+.16),(x,dy,zp+.23),.10,.10,(0,1,0),.3,0,0,s+3+j,step=.5)
    member(bb,bg,(-XE+.30,0,zp+.27),(XE-.30,0,zp+.27),.66,.08,(0,0,1),.2,0,0,90,step=.3)
    to_obj('Gate_Beams_And_Brackets',bb,M['beam'])
    qb,qg=gbm()
    def slab(outline,place,y0,y1,key):
        f=[qb.verts.new(place(a,b,y0)) for a,b in outline];bk=[qb.verts.new(place(a,b,y1)) for a,b in outline];m=len(outline)
        for v,(a,b) in zip(f+bk,outline+outline):v[qg]=(b,v.co.y,a+key,1)
        qb.faces.new(f);qb.faces.new(list(reversed(bk)))
        for k in range(m):qb.faces.new((f[k],bk[k],bk[(k+1)%m],f[(k+1)%m]))
    for sx in (-1,1):
        for side in (-1,1):
            dirx=side*sx;x0=sx*PX+dirx*PR/2;L,H=.48,.26;pts=[(0,0),(L,0)]
            for k in range(1,14):t=k/13;pts.append((L*(1-t)+.03*math.sin(t*math.pi*2),-H*t**1.7-.035*math.sin(t*math.pi)))
            pts.append((0,-H));place=lambda a,b,y,x0=x0,dirx=dirx:Vector((x0+dirx*a,y,Z_LINTEL-.13+b))
            slab(pts,place,-.05,.05,sx*7)
            inner=[(a*.78+.02,b*.78-.02) for a,b in pts[1:-1]]+[(.02,-.02)]
            for y0,y1 in ((-.05,-.066),(.05,.066)):slab(inner,place,y0,y1,sx*7+1)
    bmesh.ops.recalc_face_normals(qb,faces=qb.faces[:])
    to_obj('Gate_QueTi_Brackets',qb,M['beam'])
    wb,wg=gbm()                                                                                      # tenon wedges and through-pegs
    for sx in (-1,1):
        member(wb,wg,(sx*(PX+.27),0,Z_TIE-.19),(sx*(PX+.27),0,Z_TIE+.17),.05,.20,(0,1,0),.2,.45,0,70+sx,step=.36)
        for z in (Z_TIE,Z_LINTEL):member(wb,wg,(sx*PX,-PR/2-.035,z),(sx*PX,PR/2+.035,z),.05,.05,(0,0,1),.3,0,0,72+sx,step=.5)
    to_obj('Gate_Tenon_Wedges',wb,M['dark'])
    # --- iron: bands round each clamp stone, post collar above it, strut collars, beam straps
    ir=bmesh.new()
    for sx in (-1,1):
        for z,w in ((.58,ST+.004),(.17,ST+.025)):bmesh.ops.create_cube(ir,size=1,matrix=Matrix.Translation((sx*PX,0,z))@Matrix.Diagonal((w,w,.05,1)))
        K.lathe_into(ir,[(0,.88),(PR/2+.018,.88),(PR/2+.018,.94),(0,.94)],10,(sx*PX,0,0))
        top,foot=struts[(sx+1)//2];d=(top-foot).normalized();q=d.to_track_quat('Z','Y').to_matrix().to_4x4()
        for t in (.84,.20):bmesh.ops.create_cube(ir,size=1,matrix=Matrix.Translation(foot+(top-foot)*t)@q@Matrix.Diagonal((.185,.185,.05,1)))
        for z,h in ((Z_TIE,.24),(Z_LINTEL,.26)):
            bmesh.ops.create_cube(ir,size=1,matrix=Matrix.Translation((sx*(PX+PR/2+.07),0,z))@Matrix.Diagonal((.035,.23,h+.02,1)))
    for f in ir.faces:f.smooth=False
    io=stone_lp('Gate_Iron_Fittings',ir);io.parent=ctx.root;io.data.materials.append(M['iron']);ctx.objs.append(io)
    # --- plaque: frame + jade field + raised emblem and carved clouds (Var.r 0 / .5 / 1); plain back
    W,Hh=1.42,.46
    pq=K.new_bm();K.box_into(pq,(0,0,Z_PLAQUE),(W,.08,Hh),.014);K.link('Gate_Plaque_Frame',pq,[M['plaque']],None,(0,0,0))
    fld=K.new_bm();K.box_into(fld,(0,-.042,Z_PLAQUE),(W-.14,.012,Hh-.12),.004);K.link('Gate_Plaque_Field',fld,[M['plaque']],None,(.5,0,0))
    cl=K.new_bm()
    for sx in (-1,1):cloud_into(cl,Vector((sx*.46,-.048,Z_PLAQUE-.02)),Vector((1,0,0)),Vector((0,-1,0)),.18)
    K.link('Gate_Plaque_Clouds',cl,[M['plaque']],True,(1,0,0))
    # --- tiled roof: concave slopes with flying corners, eave boards, barrel tiles with end discs, hip ridges,
    #     rafters, main ridge with end scrolls, lotus base and jade pearl
    rf=bmesh.new();secs=[];eb,eg=gbm();es=[[],[]]
    for i in range(61):
        x=-XE+2*XE*i/60;ye=roof_ye(x);ts=[-1+2*k/16 for k in range(17)]
        secs.append([(x,t*ye,roof_z(x,t)) for t in ts]+[(x,t*ye,min(roof_z(x,t)-.10,Z_EAVE+roof_up(x)*abs(t)**2-.10)) for t in reversed(ts)])   # solid body: flat soffit, no hollow under the slopes
        for j,sy in enumerate((-1,1)):
            z=roof_z(x,sy);es[j].append([(x,sy*(ye+a),z+b) for a,b in ((-.08,-.04),(.0,-.04),(.0,-.13),(-.08,-.12))])
    loft(rf,secs)
    for j in range(2):
        rows=[[eb.verts.new(p) for p in ring] for ring in es[j]]
        for r_ in rows:
            for v in r_:v[eg]=(v.co.z*4,v.co.y*4,v.co.x,1)
        for a,b in zip(rows,rows[1:]):
            for k in range(4):eb.faces.new((a[k],a[(k+1)%4],b[(k+1)%4],b[k]))
        eb.faces.new(list(reversed(rows[0])));eb.faces.new(rows[-1])
    bmesh.ops.recalc_face_normals(eb,faces=eb.faces[:])
    to_obj('Gate_Eave_Boards',eb,M['dark'],False)
    raf=bmesh.new();k=0
    while -XE+.14+k*.16<XE-.14:
        x=-XE+.14+k*.16;k+=1;ye=roof_ye(x)
        for sy in (-1,1):K.tube_into(raf,[(x,sy*(ye-.40),roof_z(x,sy*(1-.40/ye))-.13),(x,sy*(ye-.02),roof_z(x,sy)-.12)],[.03,.03],6)
    tl=bmesh.new();k=0
    while -XE+.10+k*.19<XE-.06:
        x=-XE+.10+k*.19;k+=1;ye=roof_ye(x)
        for sy in (-1,1):
            pts=[(x,sy*(.03+.97*j/12)*ye,roof_z(x,sy*(.03+.97*j/12))+.036) for j in range(13)]
            K.tube_into(tl,pts,[.048+.008*(j%3==0) for j in range(13)],10)                          # overlapping courses
            e=Vector(pts[-1]);d=(e-Vector(pts[-2])).normalized();q=d.to_track_quat('Z','Y').to_matrix().to_4x4()
            bmesh.ops.create_cone(tl,cap_ends=True,segments=14,radius1=.066,radius2=.066,depth=.03,matrix=Matrix.Translation(e+d*.012)@q)
    zr=Z_EAVE+ROOF_H;rd=bmesh.new()
    bmesh.ops.create_cube(rd,size=1,matrix=Matrix.Translation((0,0,zr+.06))@Matrix.Diagonal((2*RX+.10,.26,.18,1)))
    bmesh.ops.bevel(rd,geom=rd.edges[:],offset=.025,segments=2,affect='EDGES')
    for sx in (-1,1):                                                                                # ridge-end blocks with curling scrolls
        bmesh.ops.create_cube(rd,size=1,matrix=Matrix.Translation((sx*RX,0,zr+.11))@Matrix.Diagonal((.24,.30,.26,1)))
        pts=[];rad=[]
        for k in range(16):
            t=k/15;a=math.pi*(1.0-1.7*t);r=.14-.07*t
            pts.append((sx*(RX-.04-r*math.cos(a)),0,zr+.30+r*math.sin(a)+.10*t));rad.append(.065-.03*t)
        K.tube_into(rd,pts,rad,8)
    for sx in (-1,1):                                                                                # hip ridges down to the flying corners, curled tips
        for sy in (-1,1):
            pts=[];rad=[]
            for k in range(14):
                t=k/13;x=sx*(RX+(XE-.04-RX)*t);pts.append((x,sy*t*.97*roof_ye(x),roof_z(x,sy*t*.97)+.06));rad.append(.075-.02*t)
            K.tube_into(rd,pts,rad,8)
            x=sx*(XE-.04);b0=Vector(pts[-1]);pts=[];rad=[]
            for k in range(12):
                t=k/11;a=math.pi*.8*t
                pts.append(b0+Vector((sx*.12*math.sin(a),sy*.07*math.sin(a),.26*t+.05*(1-math.cos(a)))));rad.append(.055-.03*t)
            K.tube_into(rd,pts,rad,8)
    K.lathe_into(rd,[(0,zr+.14),(.18,zr+.14),(.20,zr+.18),(.14,zr+.22),(.17,zr+.25),(.10,zr+.28),(0,zr+.28)],16,(0,0,0),.04)   # lotus base
    for bm_,name,mat in ((rf,'Gate_Roof_Slab',M['tile']),(tl,'Gate_Roof_Barrel_Tiles',M['tile']),(rd,'Gate_Roof_Ridge',M['tile'])):
        o=stone_lp(name,bm_);o.parent=ctx.root;o.data.materials.append(mat);ctx.objs.append(o)
        for p in o.data.polygons:p.use_smooth=True
    ro=stone_lp('Gate_Eave_Rafters',raf);ro.parent=ctx.root;ro.data.materials.append(M['dark']);ctx.objs.append(ro)
    g=ro.data.color_attributes.new('G','FLOAT_COLOR','POINT')
    for k,v in enumerate(ro.data.vertices):g.data[k].color=(v.co.x*3,v.co.z*3,v.co.y,1)
    pr=K.new_bm();z2=zr+.27;K.lathe_into(pr,[(0,z2),(.06,z2+.015),(.095,z2+.07),(.09,z2+.13),(.06,z2+.18),(.025,z2+.21),(0,z2+.22)],18)
    K.link('Gate_Jade_Pearl',pr,[M['pearl']])
    # --- drying herb bundles: two pairs hanging from the tie beam just inside the posts; dried leafy stems,
    #     orange flower heads on the right pair, a string of brown seed pods on the left
    hb=K.new_bm();fw=K.new_bm();sd=bmesh.new();tb=bmesh.new()
    for bi,x in enumerate((-(PX-.30),-(PX-.48),PX-.30,PX-.48)):
        ztop=Z_TIE-.12;tie=ztop-.10;K.tube_into(tb,[(x,0,ztop+.12),(x,0,tie)],[.006,.006],6)
        K.tube_into(tb,[(x,0,tie+.025),(x,0,tie-.035)],[.024,.022],8)
        for s in range(24):
            az=s*K.GOLDEN;sp=rng.uniform(.6,1.0);c=Vector((x+.012*math.cos(az),.012*math.sin(az),tie+.04));L=rng.uniform(.52,.76)
            pts=[c+Vector((math.cos(az)*.15*sp*(j/8)**1.2,math.sin(az)*.10*sp*(j/8)**1.2,-L*j/8)) for j in range(9)]
            wilt=rng.uniform(.55,1.0);side=Vector((-math.sin(az),math.cos(az),0))
            K.ribbon_into(hb,pts,[.004]*9,side,0.0,0,2,(rng.random(),wilt,0))
            for li in range(5):
                p=pts[2+li];a2=az+rng.uniform(-1.2,1.2);ll=rng.uniform(.07,.11)
                lp=[p+Vector((math.cos(a2)*.035*q,math.sin(a2)*.035*q,-ll*q)) for q in (0,.25,.5,.75,1)]
                K.ribbon_into(hb,lp,[.002,.012,.016,.011,.001],Vector((-math.sin(a2),math.cos(a2),0)),.35,rng.uniform(-.6,.6),3,(rng.random(),min(1,wilt+rng.uniform(-.1,.2)),0))
            if bi>=2 and s%3==0:
                for k in range(4):K.ico_into(fw,1,rng.uniform(.010,.015),Matrix.Translation(pts[-1]+Vector((rng.uniform(-.025,.025),rng.uniform(-.025,.025),rng.uniform(-.03,.02)))))
        if bi==0:
            K.tube_into(tb,[(x+.08,-.03,tie),(x+.08,-.03,tie-.44)],[.003,.003],5)
            for k in range(7):K.ico_into(sd,2,.026-.001*k,Matrix.Translation((x+.08+.018*math.sin(k*1.7),-.03,tie-.07-k*.055)))
    to_obj('Gate_Herb_Bundle_Cords',tb,M['dark'],False)
    K.link('Gate_Drying_Herb_Bundles',hb,[M['herb']],False)
    K.link('Gate_Dried_Flower_Heads',fw,[M['flower']],True,(.5,.5,0))
    so=stone_lp('Gate_Dried_Seed_Pods',sd);so.parent=ctx.root;so.data.materials.append(M['seed']);ctx.objs.append(so)
    for p in so.data.polygons:p.use_smooth=True
    # --- jade banners hung from poles that run out past the lintel ends, tied up to the flying corners
    bn=K.new_bm();rods=K.new_bm();tas=K.new_bm()
    for sx in (-1,1):
        xc=sx*2.30;zt=Z_LINTEL-.02;zb=1.46;w=.31;nx,nz=8,44;grid=[];x0=xc-w/2
        for j in range(nz+1):
            v=j/nz;row=[]
            for i in range(nx+1):
                u=i/nx;rag=.10*abs(math.sin(u*17+sx*3))*v**18+.05*(1-abs(2*u-1))*v**22
                z=zt-(zt-zb)*v+rag;y=-.03+.035*math.sin(v*4.0+u*1.1+sx)*v+.006*math.sin(u*11)*v;xx=x0+w*u+.025*math.sin(v*3+sx)*v
                p=bn.verts.new((xx,y,z));K.tag_uv(p,u,1-v,(0,0,0));row.append(p)
            grid.append(row)
        for j in range(nz):
            for i in range(nx):bn.faces.new((grid[j][i],grid[j][i+1],grid[j+1][i+1],grid[j+1][i]))
        K.tube_into(rods,[(sx*(PX+.50),-.03,Z_LINTEL+.10),(sx*2.62,-.03,Z_LINTEL+.10)],[.022,.018],8)           # pole out past the lintel
        K.tube_into(rods,[(xc-.19,-.03,zt+.02),(xc+.19,-.03,zt+.02)],[.012,.012],8)                       # banner head rod
        for dx in (-.15,.15):K.tube_into(rods,[(xc+dx,-.03,zt+.02),(xc+dx,-.03,Z_LINTEL+.10)],[.004,.004],5)
        tip=Vector((sx*(XE-.06),-roof_ye(sx*(XE-.06))*.6,roof_z(sx*(XE-.06),-1)-.08))
        K.tube_into(rods,[(sx*2.58,-.03,Z_LINTEL+.10),tip],[.004,.004],5)
        for dx in (-.19,.19):K.tube_into(tas,[(xc+dx,-.03,zt+.01),(xc+dx,-.03,zt-.14),(xc+dx,-.03,zt-.28)],[.006,.016,.004],6)
        K.tube_into(tas,[(xc,-.03,zb+.06),(xc,-.03,zb-.08),(xc,-.03,zb-.24)],[.005,.018,.004],6)
    K.link('Gate_Jade_Banners',bn,[M['banner']])
    K.link('Gate_Banner_Rods',rods,[M['dark']])
    K.link('Gate_Tassels',tas,[M['banner']],True,(.2,0,0))
    # --- paper lantern from the left lintel end
    LX=-(PX+.50);LY=0.0;lz=Z_LINTEL-.13
    ln=K.new_bm();K.lathe_into(ln,[(0,lz-.70),(.10,lz-.695),(.14,lz-.64),(.15,lz-.50),(.15,lz-.34),(.14,lz-.26),(.10,lz-.22),(0,lz-.215)],18,(LX,LY,0))
    K.link('Gate_Lantern_Paper',ln,[M['paper']])
    lf=bmesh.new()
    K.lathe_into(lf,[(0,lz-.22),(.11,lz-.22),(.11,lz-.19),(0,lz-.18)],16,(LX,LY,0));K.lathe_into(lf,[(0,lz-.73),(.11,lz-.73),(.11,lz-.695),(0,lz-.695)],16,(LX,LY,0))
    for k in range(8):
        a=k*TAU/8;K.tube_into(lf,[(LX+r*math.cos(a),LY+r*math.sin(a),zz) for r,zz in ((.10,lz-.695),(.142,lz-.64),(.152,lz-.50),(.152,lz-.34),(.142,lz-.26),(.10,lz-.22))],[.004]*6,5)
    K.tube_into(lf,[(LX,LY,lz-.18),(LX,LY,lz)],[.005,.005],5)
    K.tube_into(lf,[(LX,LY,lz-.73),(LX,LY,lz-.82),(LX,LY,lz-.96)],[.006,.016,.004],6)
    to_obj('Gate_Lantern_Frame',lf,M['dark'],False)
    # --- tall woven herb basket outside the left post: hoop courses over vertical stakes, rim, straps
    bk=bmesh.new();bx,by=-(PX+.46),-.50;R0,R1,BH=.15,.185,.50
    K.lathe_into(bk,[(0,.02),(R0-.012,.02),(R1-.014,BH),(0,BH-.03)],20,(bx,by,0))
    for k in range(int(BH/.028)):
        z=.03+k*.028;r=R0+(R1-R0)*z/BH;ph=(k%2)*math.pi
        K.tube_into(bk,[(bx+(r+.004*math.sin(a*16+ph))*math.cos(a),by+(r+.004*math.sin(a*16+ph))*math.sin(a),z) for a in [j*TAU/64 for j in range(65)]],[.011]*65,5,False)
    for j in range(16):
        a=j*TAU/16;K.tube_into(bk,[(bx+(R0+(R1-R0)*z/BH+.009)*math.cos(a),by+(R0+(R1-R0)*z/BH+.009)*math.sin(a),z) for z in (.01,BH*.5,BH+.01)],[.006]*3,5)
    K.tube_into(bk,[(bx+(R1+.01)*math.cos(a),by+(R1+.01)*math.sin(a),BH+.01) for a in [j*TAU/32 for j in range(33)]],[.017]*33,6,False)
    for s2 in (-1,1):K.tube_into(bk,[(bx+s2*.05,by+R1+.012,BH-.24),(bx+s2*.07,by+R1+.03,BH-.08),(bx+s2*.05,by+R1+.012,BH+.02)],[.007]*3,5)
    to_obj('Gate_Herb_Basket',bk,M['wicker'])
    hs=K.new_bm()
    for k in range(18):
        az=k*K.GOLDEN;pts,h=K.arch((bx+.08*math.cos(az),by+.08*math.sin(az),BH-.06),az,rng.uniform(.24,.38),.12,1.2,8)
        K.ribbon_into(hs,pts,[.014*min(1,j/8*5)*(1-j/8)**.5+.0008 for j in range(9)],Vector((-h.y,h.x,0)),.35,0,5,(rng.random(),rng.uniform(0,.3),0))
    K.link('Gate_Basket_Herbs',hs,[M['herb']],False)
    # --- grass round the plinths and the pad edge, path kept clear
    gr=K.new_bm();placed=0
    for k in range(900):
        if placed>=70:break
        x=rng.uniform(-2.6,2.6);y=rng.uniform(-1.3,1.3)
        if (x/PAD[0])**2+(y/PAD[1])**2>.92 or abs(x)<PX-.40 and abs(y)<1.05:continue
        dp=min(math.hypot(x-sx*PX,y) for sx in (-1,1))
        if dp<.45 or (dp>.90 and rng.random()<.7):continue
        O.tuft_into(gr,rng,Vector((x,y,O.skirt_height(x,y,PAD,.03)-.006)),.05,.16);placed+=1
    K.link('Gate_Grass_Tufts',gr,[K.M['blade']],False)
    ctx.extra.update({'reference':'ai_threeview_v002/R04_QX_GatheringLandmark.png','post_centres_x_m':[-PX,PX],
                      'clear_opening_at_ground_m':round(2*PX-ST,3),'clear_opening_between_posts_m':round(2*PX-PR,3),
                      'tie_beam_z_m':Z_TIE,'lintel_z_m':Z_LINTEL,'eave_z_m':Z_EAVE,'ridge_z_m':round(Z_EAVE+ROOF_H,3),
                      'state_change':'none (landmark has one state)'})
