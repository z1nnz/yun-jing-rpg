"""QX_GatheringLandmark rebuild: herb-gatherers' timber paifang (Chinese two-post gate) under a carved stone roof. Semi-real.
Rhythm, bottom to top: clamp stones (jia gan shi) with iron hoops | hewn posts braced by raking struts |
through-tenoned tie beam with wedges and hanging herb bundles | framed plaque with the herb emblem between
the beams | lintel with carved que-ti brackets at the posts | bracket blocks | carved stone hip roof with tile
rolls, upturned eave corners, ridge-end scrolls and a jade pearl on a lotus base (the gatherers' mark).
Jade banners hang from the overhangs; a warm lantern on the left overhang; a herb basket at the right post.
Origin: bottom centre on the path axis; the path runs along Y through the opening; front -Y.
"""
import bpy,bmesh,math,random
from mathutils import Vector,Matrix,noise
import qx_kit as K
import qx_ore as O

TAU=math.tau
PX=1.22                     # post centre |x|
POST=(.26,.26)              # post section (m)
Z_TIE,Z_LINTEL,Z_COP=2.62,3.30,3.79

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

PALE_STONE=[(0,(.15,.148,.14)),(.45,(.21,.205,.195)),(.75,(.19,.18,.165)),(1,(.25,.245,.235))]

# ---------------------------------------------------------------- build
def build(post):
    rng=random.Random(5101);ctx=K.ctx
    M={'stone':O.mat_rock_real('QX_Src_Gate_Dressed_Stone',False,False,PALE_STONE),'moss':O.mat_moss_real('QX_Src_Gate_Moss'),
       'post':mat_timber('QX_Src_Gate_Timber_Post',.6),'beam':mat_timber('QX_Src_Gate_Timber_Beam',.45),'dark':mat_timber('QX_Src_Gate_Timber_Dark',.25,True),
       'plaque':mat_plaque('QX_Src_Gate_Plaque',(Z_TIE+Z_LINTEL)/2),'iron':mat_iron('QX_Src_Gate_Iron'),
       'banner':mat_banner('QX_Src_Gate_Jade_Banner'),'paper':mat_paper('QX_Src_Gate_Lantern_Paper'),'pearl':mat_pearl('QX_Src_Gate_Jade_Pearl'),
       'skirt':O.mat_skirt('QX_Src_Gate_Ground')}
    # --- ground pad + threshold flagstones
    sk=K.new_bm();O.skirt_into(sk,(2.15,1.45),.03,18,96,9);K.link('Gate_Ground_Blend',sk,[M['skirt']])
    fl=bmesh.new()
    for k,(x,y,sx,sy) in enumerate([(-.05,-.62,.62,.34),(.08,.02,.70,.40),(-.10,.66,.58,.33)]):
        b=O.hull_block((x,y,.035),(sx,sy,.07),700+k,40,.35,(0,0,rng.uniform(-.2,.2)),rmin=.92);O.finish_block(b,.012,0.0);K.merge_into(fl,b)
    dressed('Gate_Threshold_Flagstones',fl,M['stone'],M['moss'],21,.008,.25,.45,False)
    # --- clamp stones (jia gan shi): footing slab + two tall blocks gripping each post front and back
    for sx in (-1,1):
        bm=bmesh.new()
        bmesh.ops.create_cube(bm,size=1,matrix=Matrix.Translation((sx*PX,0,.06))@Matrix.Diagonal((.78,.86,.12,1)))
        bmesh.ops.bevel(bm,geom=bm.edges[:],offset=.02,segments=2,affect='EDGES')
        for sy in (-1,1):
            b2=bmesh.new();bmesh.ops.create_cube(b2,size=1,matrix=Matrix.Translation((sx*PX,sy*(POST[1]/2+.115),.12+.40))@Matrix.Diagonal((.50,.23,.80,1)))
            for v in b2.verts:
                if v.co.z>.8 and v.co.y*sy>POST[1]/2+.115:v.co.z-=.07                       # sloped weather top
            bmesh.ops.bevel(b2,geom=b2.edges[:],offset=.025,segments=2,affect='EDGES');K.merge_into(bm,b2)
        dressed('Gate_Clamp_Stones_'+('L' if sx<0 else 'R'),bm,M['stone'],M['moss'],30+sx,.008,.3,.5,True)
    # --- posts, struts, beams, brackets (timber)
    pb,pg=gbm()
    for i,sx in enumerate((-1,1)):
        member(pb,pg,(sx*PX,0,.12),(sx*PX,0,Z_COP-.16),POST[0],POST[1],(0,1,0),.24,.06,.008,11+i,pith=(.03,-.02))
    to_obj('Gate_Posts',pb,M['post'])
    sb,sg=gbm()
    for i,sx in enumerate((-1,1)):
        for sy in (-1,1):
            foot=Vector((sx*(PX+.08),sy*.78,.05));top=Vector((sx*PX,sy*.12,1.62))
            member(sb,sg,foot,top,.11,.13,(0,0,1),.25,0,.006,21+i*2+sy)
    to_obj('Gate_Raking_Struts',sb,M['dark'])
    bb,bg=gbm()
    member(bb,bg,(-PX-.29,0,Z_TIE),(PX+.29,0,Z_TIE),.16,.22,(0,0,1),.2,0,.01,31)                     # tie beam, through-tenons
    member(bb,bg,(-PX-.62,0,Z_LINTEL),(PX+.62,0,Z_LINTEL),.20,.26,(0,0,1),.2,0,.012,33,step=.12)
    for sx in (-1,1):                                                                            # studs between the beams
        member(bb,bg,(sx*.56,0,Z_TIE+.11),(sx*.56,0,Z_LINTEL-.13),.12,.10,(0,1,0),.25,0,0,40+sx)
    for sx in (-1,1):                                                                            # bracket blocks under the coping
        for dx in (-.16,.16):
            x=sx*PX+dx;member(bb,bg,(x,0,Z_LINTEL+.13),(x,0,Z_COP-.17),.17,.24,(0,1,0),.3,0,0,50+int(x*10),step=.5)
        member(bb,bg,(sx*PX-.30,0,Z_COP-.145),(sx*PX+.30,0,Z_COP-.145+.0001),.26,.05,(0,0,1),.3,0,0,60+sx,step=.3)
    to_obj('Gate_Beams_And_Brackets',bb,M['beam'])
    # que-ti: carved brackets under the lintel on both sides of each post
    qb,qg=gbm()
    def slab(outline,place,y0,y1,key):
        f=[qb.verts.new(place(a,b,y0)) for a,b in outline];bk=[qb.verts.new(place(a,b,y1)) for a,b in outline];n=len(outline)
        for v,(a,b) in zip(f+bk,outline+outline):v[qg]=(b,v.co.y,a+key,1)
        qb.faces.new(f);qb.faces.new(list(reversed(bk)))
        for k in range(n):qb.faces.new((f[k],bk[k],bk[(k+1)%n],f[(k+1)%n]))
    for sx in (-1,1):
        for side in (-1,1):
            dirx=side*sx;x0=sx*PX+dirx*POST[0]/2;L,H=.50,.30;pts=[(0,0),(L,0)]
            for k in range(1,14):
                t=k/13;pts.append((L*(1-t)+.03*math.sin(t*math.pi*2),-H*t**1.7-.035*math.sin(t*math.pi)))
            pts.append((0,-H))
            place=lambda a,b,y,x0=x0,dirx=dirx:Vector((x0+dirx*a,y,Z_LINTEL-.13+b))
            slab(pts,place,-.045,.045,sx*7)
            inner=[(a*.78+.02,b*.78-.02) for a,b in pts[1:-1]]+[(.02,-.02)]                       # carved scroll relief
            for y0,y1 in ((-.045,-.062),(.045,.062)):slab(inner,place,y0,y1,sx*7+1)
    bmesh.ops.recalc_face_normals(qb,faces=qb.faces[:])
    to_obj('Gate_QueTi_Brackets',qb,M['beam'])
    # wedges through the tie-beam tenons
    wb,wg=gbm()
    for sx in (-1,1):member(wb,wg,(sx*(PX+.21),0,Z_TIE-.17),(sx*(PX+.21),0,Z_TIE+.15),.045,.19,(0,1,0),.2,.45,0,70+sx,step=.32)
    to_obj('Gate_Tenon_Wedges',wb,M['dark'])
    # --- iron: post collars, beam straps, nails, lantern hook
    ir=bmesh.new()
    for sx in (-1,1):
        for z in (.36,.74):bmesh.ops.create_cube(ir,size=1,matrix=Matrix.Translation((sx*PX,0,z))@Matrix.Diagonal((.52,POST[1]+.48,.05,1)))   # hoops round the clamp stones
        bmesh.ops.create_cube(ir,size=1,matrix=Matrix.Translation((sx*PX,0,Z_TIE-.16))@Matrix.Diagonal((POST[0]+.016,POST[1]+.016,.035,1)))
        for z in (Z_TIE,Z_LINTEL):
            for dy in (-1,1):
                for dz in (-.06,.06):K.tube_into(ir,[(sx*PX,dy*(POST[1]/2+.004),z+dz),(sx*PX,dy*(POST[1]/2+.016),z+dz)],[.014,.012],8)
    K.tube_into(ir,[(-PX+.02,-POST[1]/2,2.32),(-PX+.02,-.44,2.32),(-PX+.02,-.46,2.26)],[.011,.011,.009],6)   # lantern arm
    for f in ir.faces:f.smooth=False
    io=stone_lp('Gate_Iron_Fittings',ir);io.parent=ctx.root;io.data.materials.append(M['iron']);ctx.objs.append(io)
    # --- plaque between the beams: frame + jade field + raised emblem (Var.r 0 / .5 / 1)
    pq=K.new_bm();zc=(Z_TIE+Z_LINTEL)/2;W,Hh=.86,.40
    K.box_into(pq,(0,-.02,zc),(W,.06,Hh),.012);K.link('Gate_Plaque_Frame',pq,[M['plaque']],None,(0,0,0))
    fld=K.new_bm();K.box_into(fld,(0,-.052,zc),(W-.12,.012,Hh-.10),.004);K.link('Gate_Plaque_Field',fld,[M['plaque']],None,(.5,0,0))
    # --- carved stone hip roof: eave slab, two slopes with carved tile rolls, hipped ends, upturned
    #     eave corners, ridge cap with end scrolls; lotus base + jade pearl at the ridge centre
    cp=bmesh.new();XE=PX+.70;ye=.36;z0=Z_COP-.12;slope=.21/(ye-.05);secs=[]
    for i in range(41):
        x=-XE+2*XE*i/40;d=XE-abs(x);e=max(0,1-d/.55);up=.07*e**2;rise=min(.21,slope*d);yr=max(.05,ye-d);cap=.06 if d>=ye-.05 else 0.0
        yw=ye+.03*e
        prof=[(-yw,z0+up),(yw,z0+up),(yw,z0+.06+up),(yr,z0+.06+rise+up*.3),(yr,z0+.06+rise+cap),(-yr,z0+.06+rise+cap),(-yr,z0+.06+rise+up*.3),(-yw,z0+.06+up)]
        secs.append([(x,yy,zz) for yy,zz in prof])
    loft(cp,secs);xr=XE-(ye-.05)
    for k in range(int(2*xr/.11)+1):
        x=-xr+.055+k*.11
        if abs(x)>xr-.02:continue
        for sy in (-1,1):K.tube_into(cp,[(x,sy*.06,z0+.06+.21+.004),(x,sy*(ye+.015),z0+.06+.006)],[.02,.02],8)
    for sx in (-1,1):
        K.lathe_into(cp,[(0,z0+.30),(.07,z0+.30),(.08,z0+.36),(.06,z0+.42),(.03,z0+.45),(0,z0+.45)],10,(sx*(xr-.02),0,0))   # ridge-end scrolls
    K.lathe_into(cp,[(0,z0+.32),(.16,z0+.32),(.18,z0+.36),(.13,z0+.40),(.15,z0+.43),(.09,z0+.47),(0,z0+.47)],16,(0,0,0),.04)
    dressed('Gate_Stone_Roof',cp,M['stone'],M['moss'],44,.009,.28,.5,True)
    pr=K.new_bm();zp=z0+.46;K.lathe_into(pr,[(0,zp),(.07,zp+.02),(.11,zp+.09),(.105,zp+.16),(.07,zp+.22),(.03,zp+.27),(0,zp+.32)],18)
    K.link('Gate_Jade_Pearl',pr,[M['pearl']])
    # --- drying herb bundles on iron hooks under the tie beam
    hb=K.new_bm();tb=bmesh.new()
    for k,x in enumerate((-.62,0.0,.58)):
        ztop=Z_TIE-.11;K.tube_into(tb,[(x,0,ztop),(x,0,ztop-.06),(x,-.01,ztop-.10)],[.005,.005,.004],5)
        for s in range(9):                                                                        # bundle of drying herb stems, heads down
            az=s*K.GOLDEN;c=Vector((x+.012*math.cos(az),.012*math.sin(az),ztop-.10));L=rng.uniform(.22,.32)
            pts=[c+Vector((math.cos(az)*.05*(j/6)**1.4,math.sin(az)*.05*(j/6)**1.4,-L*j/6)) for j in range(7)]
            K.ribbon_into(hb,pts,[.006+.012*math.sin(math.pi*min(1,j/6+.2))*(j>1) for j in range(7)],Vector((-math.sin(az),math.cos(az),0)),.3,0,3,(rng.random(),.6,0))
    to_obj('Gate_Herb_Bundle_Hooks',tb,M['iron'])
    K.link('Gate_Drying_Herb_Bundles',hb,[K.M['leaf_q']],False)
    # --- jade banners from the lintel overhangs
    bn=K.new_bm()
    for sx in (-1,1):
        x0=sx*(PX+.45)-.13;zt=Z_LINTEL-.14;zb=1.38;nx,nz=8,40;grid=[]
        for j in range(nz+1):
            v=j/nz;row=[]
            for i in range(nx+1):
                u=i/nx;z=zt-(zt-zb)*v+.18*(1-abs(2*u-1))*v**24+.02*abs(math.sin(u*37+sx))*v**30
                y=-.03+.03*math.sin(v*4.4+u*1.3+sx)*v+.008*math.sin(u*13)*v;xx=x0+.26*u+.02*math.sin(v*3+sx)*v
                p=bn.verts.new((xx,y,z));rr=(xx-(x0+.13))**2+(z-(zt-.42))**2
                K.tag_uv(p,u,1-v,(0,0,0));row.append(p)
            grid.append(row)
        for j in range(nz):
            for i in range(nx):bn.faces.new((grid[j][i],grid[j][i+1],grid[j+1][i+1],grid[j+1][i]))
    K.link('Gate_Jade_Banners',bn,[M['banner']])
    rods=K.new_bm()
    for sx in (-1,1):K.tube_into(rods,[(sx*(PX+.45)-.16,-.03,Z_LINTEL-.14),(sx*(PX+.45)+.16,-.03,Z_LINTEL-.14)],[.01,.01],8)
    K.link('Gate_Banner_Rods',rods,[M['dark']])
    # --- lantern on the left overhang
    LX=-PX+.02;LY=-.46;lz=2.26
    ln=K.new_bm();K.lathe_into(ln,[(0,lz-.36),(.10,lz-.355),(.15,lz-.30),(.165,lz-.21),(.15,lz-.10),(.10,lz-.05),(0,lz-.045)],16,(LX,LY,0))
    K.link('Gate_Lantern_Paper',ln,[M['paper']])
    lf=bmesh.new()
    K.lathe_into(lf,[(0,lz-.05),(.11,lz-.05),(.11,lz-.03),(0,lz-.02)],16,(LX,LY,0));K.lathe_into(lf,[(0,lz-.38),(.105,lz-.38),(.105,lz-.355),(0,lz-.355)],16,(LX,LY,0))
    for k in range(8):
        a=k*TAU/8;K.tube_into(lf,[(LX+r*math.cos(a),LY+r*math.sin(a),zz) for r,zz in ((.10,lz-.355),(.152,lz-.30),(.167,lz-.21),(.152,lz-.10),(.10,lz-.05))],[.004]*5,5)
    K.tube_into(lf,[(LX,LY,lz-.02),(LX,LY,lz)],[.004,.004],5)
    to_obj('Gate_Lantern_Frame',lf,M['dark'],False)
    # --- herb basket at the right post
    bk=bmesh.new();bx,by=PX+.42,-.40
    K.lathe_into(bk,[(0,.02),(.15,.02),(.19,.12),(.205,.24),(.215,.27),(.195,.275),(.18,.08),(0,.08)],24,(bx,by,0))
    K.tube_into(bk,[(bx+.21*math.cos(a),by+.21*math.sin(a),.27) for a in [k*TAU/24 for k in range(25)]],[.012]*25,6,False)
    bo=to_obj('Gate_Herb_Basket',bk,M['dark'])
    hs=K.new_bm()
    for k in range(11):
        az=k*K.GOLDEN;pts,h=K.arch((bx+.07*math.cos(az),by+.07*math.sin(az),.10),az,rng.uniform(.22,.32),.15,1.1,8)
        K.ribbon_into(hs,pts,[.012*min(1,j/8*5)*(1-j/8)**.5+.0008 for j in range(9)],Vector((-h.y,h.x,0)),.35,0,5,(rng.random(),0,0))
    K.link('Gate_Basket_Herbs',hs,[K.M['leaf_q']],False)
    # --- grass at the plinths and pad edge
    gr=K.new_bm();placed=0
    for k in range(900):
        if placed>=70:break
        x=rng.uniform(-2.0,2.0);y=rng.uniform(-1.3,1.3)
        if (x/2.1)**2+(y/1.4)**2>.92 or abs(x)<.55 and abs(y)<1.05:continue                         # keep the path clear
        dp=min(math.hypot(x-sx*PX,y) for sx in (-1,1))
        if dp<.36 or (dp>.75 and rng.random()<.7):continue
        O.tuft_into(gr,rng,Vector((x,y,O.skirt_height(x,y,(2.15,1.45),.03)-.006)),.05,.16);placed+=1
    K.link('Gate_Grass_Tufts',gr,[K.M['blade']],False)
    ctx.extra.update({'post_centres_x_m':[-PX,PX],'clear_opening_m':round(2*PX-POST[0],3),'tie_beam_z_m':Z_TIE,'lintel_z_m':Z_LINTEL,'coping_z_m':Z_COP,
                      'state_change':'none (landmark has one state)'})
