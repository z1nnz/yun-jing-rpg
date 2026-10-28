"""QX_SpiritHerb_Qinglan v002 (creek orchid, Cymbidium-like spirit herb). Semi-real.
v002 follows the reviewed AI three-view R01 / R01b (art/references/.../ai_threeview_v002): broader strap
leaves with yellowed tips, four upright scapes with open white star blossoms (cyan glow at the heart) and a
bud cluster at the top, three large sheathed pseudobulbs, the stone moved behind on the left; post keeps the
leaves and cuts the scapes to tall stubs with pale cut faces, cut scape pieces lying on the soil.
v001 description (base this module was edited from):
Form: a fan clump of keeled strap leaves, narrow at the base, widest at a third, long acute tips, arching in
brush-stroke S curves that cross each other; papery sheaths and pseudobulbs at the base | three upright
scapes with papery bracts carrying 5-7 nodding blossoms each (three cupped sepals, two hooded petals, a
recurved spotted lip, a pale column), the top ones still buds | a moss-covered stone behind the clump.
Ground: the shared soil / pebble / moss / litter / grass bed.
Post: scapes cut to stubs with fresh cut faces, most leaves sickle-cut at 8-18 cm, the young inner leaves
left, two new shoots; cut leaves, a cut scape and two fallen blossoms on the soil.
Origin: clump base at (0,0,0) = ground level; front -Y.
"""
import bpy,bmesh,math,random
from mathutils import Vector,Matrix,noise
import qx_kit as K
import qx_ore as O
import qx_gate as G
import qx_chilu as C
import qx_ground as GR

TAU=math.tau
BED=(.40,.36)

# ---------------------------------------------------------------- geometry
def leaf_path(base,az,L,t0,t1,sway,n=24):
    pts,h=K.arch(base,az,L,t0,t1,n,1.5);side=Vector((-h.y,h.x,0))
    return [p+side*sway*math.sin(math.pi*j/n)*(j/n) for j,p in enumerate(pts)],h

def leaf_widths(W,n,cut=None):
    ws=[]
    for j in range(n+1):
        t=j/n;w=W*(.38+.62*math.sin(min(1,t/.33)*math.pi/2))*(1-t)**.62
        ws.append(w+.0005)
    return ws

def petal_into(bm,c,d,f,L,W,curl,cup,rows,var,shape=.75,taper=.2):
    """Cupped lanceolate perianth part from c along d (unit), facing f; curl bends the tip toward +f."""
    side=f.cross(d).normalized();pts=[];ws=[]
    for j in range(rows+1):
        t=j/rows;pts.append(c+d*L*t+f*curl*L*t*t);ws.append(W*math.sin(math.pi*min(t*1.08,.999))**shape*(1-taper*t)+.0003)
    K.ribbon_into(bm,pts,ws,side,cup,0,7,var,lambda u:u*u)

def flower_into(bm,col_bm,c,f,u,sc,rng,bud=False):
    """v002 open star blossom: five pointed tepals spread wide round f, a small pale lip and a glowing column."""
    f=f.normalized();u=(u-f*u.dot(f)).normalized();s=f.cross(u)
    vr=rng.random()
    if bud:
        for v in K.ico_into(bm,2,.0036*sc,Matrix.Translation(c+f*.008*sc)@f.to_track_quat('Z','Y').to_matrix().to_4x4()@Matrix.Diagonal((1,1,2.4,1))):
            K.tag_uv(v,.5,.3+.6*K.c01((v.co-c).dot(f)/(.02*sc)),(vr,.35,0))
        return
    def dirn(a,fw):return (u*math.cos(a)+s*math.sin(a)+f*fw).normalized()
    for k in range(5):
        a=k*TAU/5+rng.uniform(-.12,.12)
        petal_into(bm,c,dirn(a,.22),f,(.030 if k%2==0 else .027)*sc,.0068*sc,.10,.22,10,(vr,0,0),.85,.35)
    lip=(-u*.6+f).normalized();side=f.cross(lip).normalized();pts=[];ws=[]
    for j in range(7):
        t=j/6;pts.append(c+f*.003+lip*.012*sc*t-u*.006*sc*t**2.0);ws.append(.0055*sc*math.sin(math.pi*min(t*.9+.1,.999))**.6+.0003)
    K.ribbon_into(bm,pts,ws,side,.30,0,5,(vr,0,1),lambda q:q*q)
    K.tube_into(col_bm,[c,c+f*.006*sc,c+f*.010*sc],[.0024*sc,.0022*sc,.0017*sc],6)                 # glowing column
    for v in col_bm.verts[-12:]:K.tag_uv(v,.5,.5,(0,0,.6))

BULB=[(0,0),(.022,.006),(.030,.024),(.026,.046),(.015,.064),(.005,.076),(0,.079)]

def bulb_r(z):
    for (r0,z0),(r1,z1) in zip(BULB,BULB[1:]):
        if z<=z1:return r0+(r1-r0)*(z-z0)/max(z1-z0,1e-6)
    return 0.0

def bract_into(bm,bc,a,z0,z1,W,rng,lift=.0028):
    """Pointed bract hugging the pseudobulb surface (bulb_r) from z0 to z1 above the bulb base bc, tip flared out."""
    h=Vector((math.cos(a),math.sin(a),0));side=Vector((-h.y,h.x,0));n=7
    pts=[]
    for j in range(n+1):
        t=j/n;z=z0+(z1-z0)*t;pts.append(Vector(bc)+h*(bulb_r(z)+lift+.008*t**2.5)+Vector((0,0,z)))
    K.ribbon_into(bm,pts,[W*(1-t**1.7)*(.75+.25*math.sin(min(1,t*3)*math.pi/2))+.0005 for t in [j/n for j in range(n+1)]],side,-.30,rng.uniform(-.1,.1),5,(rng.random(),rng.uniform(.55,1.0),0),lambda q:q*q)

def sheath_into(bm,base,az,L,W,rng):
    h=Vector((math.cos(az),math.sin(az),0));side=Vector((-h.y,h.x,0))
    pts=[base+Vector((0,0,L*t))+h*.004*t*t for t in [j/6 for j in range(7)]]
    K.ribbon_into(bm,pts,[W*(1-.55*t)**.8+.0006 for t in [j/6 for j in range(7)]],side,1.1,rng.uniform(-.3,.3),7,(rng.random(),0,0),lambda u:u*u)

# ---------------------------------------------------------------- materials
def mat_orchid_leaf(name):
    """Glossy deep jade-green strap leaf: fine parallel veins, pale keel, yellow-green sheath base, thin
    yellow margin, dry straw tips (Var.g = dry tip length), fresh pale cut face (Var.b), back-light."""
    m,nt,bs=K.pbr(name,False,.32,.45);u,v=K.uv(nt);r,g,b=K.attr(nt);ob=K.coord(nt)
    mr,mx,ad,mrng,m_=K.mul,K.mix,K.add,K.mrange,K.math_
    ax=m_(nt,'ABSOLUTE',m_(nt,'SUBTRACT',u,.5))
    veins=K.wave_t(nt,K.comb(nt,u,0),11,'X',.2,1)
    col=K.ramp(nt,ad(nt,mr(nt,K.noise_t(nt,ob,6,4),.6),mr(nt,r,.4)),[(0,(.022,.064,.022)),(.5,(.036,.095,.030)),(1,(.058,.140,.042))])
    col=mx(nt,mr(nt,mrng(nt,v,.10,.0),.85),col,(.09,.12,.035))                                     # sheath base
    col=mx(nt,mr(nt,mrng(nt,ax,.04,.0),.45),col,(.06,.12,.05))                                     # keel
    col=mx(nt,mr(nt,mrng(nt,ax,.44,.5),.6),col,(.10,.12,.03))                                      # margin
    col=mx(nt,mr(nt,mrng(nt,veins,.75,1),.25),col,(.006,.02,.008))
    dry=mr(nt,mrng(nt,ad(nt,v,mr(nt,K.noise_t(nt,ob,20,3),.06)),m_(nt,'SUBTRACT',1.0,mr(nt,g,.30)),ad(nt,m_(nt,'SUBTRACT',1.0,mr(nt,g,.30)),.04)),mrng(nt,g,.01,.05))
    col=mx(nt,dry,col,K.ramp(nt,K.noise_t(nt,ob,30,3),[(0,(.16,.12,.06)),(1,(.26,.21,.11))]))
    col=mx(nt,mr(nt,mrng(nt,v,.7,1),mrng(nt,dry,.0,.3,.25,0)),col,(.07,.06,.02))                   # browning ahead of the dry zone
    cut=mrng(nt,b,.4,.9);col=mx(nt,cut,col,(.30,.34,.16))
    K.finish(nt,bs,col,mx(nt,dry,(.30,.30,.30),(.75,.75,.75)),ad(nt,mr(nt,veins,.25),mr(nt,mrng(nt,ax,.05,.0),-.4)),.25,.001)
    out=next(x for x in nt.nodes if x.type=='OUTPUT_MATERIAL');tr=K.node(nt,'ShaderNodeBsdfTranslucent')
    K._set(nt,tr.inputs['Color'],mx(nt,dry,(.06,.20,.05),(.30,.22,.08)))
    mixs=K.node(nt,'ShaderNodeMixShader',{0:.22});nt.links.new(bs.outputs[0],mixs.inputs[1]);nt.links.new(tr.outputs[0],mixs.inputs[2]);nt.links.new(mixs.outputs[0],out.inputs['Surface'])
    return m

def mat_blossom(name):
    """Pale jade sepals and petals with darker parallel veins and a greener base; ivory lip with red-violet
    spots (Var.b = 1); ivory column (Var.b = .6); buds greener (Var.g); soft inner light = spirit accent."""
    m,nt,bs=K.pbr(name,False,.42,.4);u,v=K.uv(nt);r,g,b=K.attr(nt);ob=K.coord(nt)
    mr,mx,ad,mrng,m_=K.mul,K.mix,K.add,K.mrange,K.math_
    ax=m_(nt,'ABSOLUTE',m_(nt,'SUBTRACT',u,.5))
    vein=mr(nt,mrng(nt,K.wave_t(nt,K.comb(nt,u,0),3.5,'X',.3,1),.80,.98),mrng(nt,v,.05,.25))
    col=K.ramp(nt,ad(nt,v,mr(nt,r,.10)),[(0,(.42,.62,.52)),(.25,(.74,.82,.74)),(1,(.86,.88,.82))])
    col=mx(nt,mr(nt,vein,.25),col,(.50,.58,.48))
    col=mx(nt,mr(nt,mrng(nt,ax,.40,.5),.3),col,(.62,.70,.56))
    lip=mrng(nt,b,.8,.95);spots=mr(nt,mr(nt,mrng(nt,K.voronoi_t(nt,K.comb(nt,mr(nt,u,9),mr(nt,v,13)),1),.26,.14),mrng(nt,v,.10,.25)),mrng(nt,v,.85,.65))
    lipc=mx(nt,mr(nt,spots,.0),(.80,.84,.74),(.80,.84,.74))
    col=mx(nt,lip,col,lipc);col=mx(nt,mr(nt,mrng(nt,b,.5,.6),mrng(nt,b,.7,.62)),col,(.66,.68,.55))
    col=mx(nt,mr(nt,g,.8),col,(.12,.22,.08))
    sub=bs.inputs.get('Subsurface Weight')
    if sub:sub.default_value=.35;bs.inputs['Subsurface Radius'].default_value=(.5,.8,.4);bs.inputs['Subsurface Scale'].default_value=.002
    heart=mx(nt,mrng(nt,b,.5,.6),K.ramp(nt,m_(nt,'SUBTRACT',1.0,v),[(0,(0,0,0)),(.7,(.01,.06,.055)),(1,(.10,.55,.50))]),(.25,.95,.85))
    heart=mx(nt,mr(nt,g,1.0),heart,(0,0,0))                                                         # buds do not glow
    nt.links.new(heart,bs.inputs['Emission Color']);bs.inputs['Emission Strength'].default_value=1.0
    K.finish(nt,bs,col,None,ad(nt,mr(nt,vein,.4),mr(nt,K.noise_t(nt,ob,150,2),.3)),.12,.0005)
    out=next(x for x in nt.nodes if x.type=='OUTPUT_MATERIAL');tr=K.node(nt,'ShaderNodeBsdfTranslucent');K._set(nt,tr.inputs['Color'],(.72,.76,.55))
    mixs=K.node(nt,'ShaderNodeMixShader',{0:.25});nt.links.new(bs.outputs[0],mixs.inputs[1]);nt.links.new(tr.outputs[0],mixs.inputs[2]);nt.links.new(mixs.outputs[0],out.inputs['Surface'])
    return m

def mat_scape(name):
    """Scape: jade green with a purple flush toward the top and on the bracts; fine striations; Var.b = fresh cut."""
    m,nt,bs=K.pbr(name,True,.45,.35);ob=K.coord(nt);z=K.sep(nt,ob)[2];r,g,b=K.attr(nt)
    col=K.ramp(nt,K.add(nt,K.mrange(nt,z,.05,.45),K.mul(nt,K.noise_t(nt,ob,12,3),.2)),[(0,(.08,.13,.045)),(.6,(.12,.16,.06)),(1,(.16,.13,.09))])
    col=K.mix(nt,K.mrange(nt,b,.4,.9),col,(.42,.48,.26))
    K.finish(nt,bs,col,None,K.noise_t(nt,K.scaled(nt,ob,(1,1,12)),80,2),.12,.001);return m

def mat_sheath(name):
    """Papery dry sheath: straw to mid brown, fine longitudinal fibres, darker frayed tips."""
    m,nt,bs=K.pbr(name,False,.8,.3);u,v=K.uv(nt);r,g,b=K.attr(nt);ob=K.coord(nt)
    fib=K.wave_t(nt,K.comb(nt,K.mul(nt,u,1.0),0),24,'X',2,2)
    col=K.ramp(nt,K.add(nt,K.mul(nt,fib,.35),K.add(nt,K.mul(nt,r,.35),K.mul(nt,v,.3))),[(0,(.07,.05,.025)),(.5,(.15,.11,.06)),(1,(.24,.19,.11))])
    col=K.mix(nt,K.mrange(nt,v,.0,.25,.6,0),col,(.10,.13,.05))
    K.finish(nt,bs,col,None,fib,.15,.0008)
    out=next(x for x in nt.nodes if x.type=='OUTPUT_MATERIAL');tr=K.node(nt,'ShaderNodeBsdfTranslucent');K._set(nt,tr.inputs['Color'],(.30,.20,.08))
    mixs=K.node(nt,'ShaderNodeMixShader',{0:.18});nt.links.new(bs.outputs[0],mixs.inputs[1]);nt.links.new(tr.outputs[0],mixs.inputs[2]);nt.links.new(mixs.outputs[0],out.inputs['Surface'])
    return m

# ---------------------------------------------------------------- build
def build(post):
    rng=random.Random(3101);ctx=K.ctx
    M={'leaf':mat_orchid_leaf('QX_Src_Qinglan_Leaf'),'blossom':mat_blossom('QX_Src_Qinglan_Blossom'),'scape':mat_scape('QX_Src_Qinglan_Scape'),
       'sheath':mat_sheath('QX_Src_Qinglan_Sheath'),'bulb':C.mat_stem_real('QX_Src_Qinglan_Pseudobulb'),
       'skirt':O.mat_skirt('QX_Src_Qinglan_Soil_Bed'),'moss':O.mat_moss_real('QX_Src_Qinglan_Moss'),
       'rock':O.mat_rock_real('QX_Src_Qinglan_Stone',False,False),'litter':C.mat_litter('QX_Src_Qinglan_Leaf_Litter')}
    hf=GR.bed('Qinglan',BED,.035,rng,M,14,22,[(-.22,.10,.08,.05),(.18,-.16,.06,.04)],7,.12,seed=31)
    # --- moss-covered stone behind the clump (the orchid grows in its lee)
    rb=O.hull_block((-.17,.20,.045),(.15,.10,.09),4711,70,.42,(0,0,-.5),rmin=.82);O.finish_block(rb,.02,0.0)
    G.dressed('Qinglan_Stone',rb,M['rock'],M['moss'],17,.006,.28,.38,True)
    # --- pseudobulbs and papery sheaths
    bu=K.new_bm();zb=hf(0,0)-.012;bcs=[]
    for k in range(3):                                                                              # three big sheathed pseudobulbs (R01)
        a=k*TAU/3-1.2;bc=Vector((.042*math.cos(a),.042*math.sin(a),zb));bcs.append((a,bc))
        K.lathe_into(bu,BULB,12,tuple(bc),a,0.0)
    K.link('Qinglan_Pseudobulbs',bu,[M['bulb']])
    br=K.new_bm()                                                                                   # overlapping pointed bracts, green with browned tips
    for a,bc in bcs:
        for row,(z0,z1,nb,W,lift) in enumerate(((.002,.050,7,.016,.0026),(.020,.068,6,.013,.0040),(.040,.084,5,.009,.0052))):
            for j in range(nb):bract_into(br,bc,a+j*TAU/nb+row*.5,z0,z1,W,rng,lift)
    K.link('Qinglan_Bracts',br,[M['leaf']])
    sh=K.new_bm()
    for k in range(5):sheath_into(sh,Vector((.012*math.cos(k*GOLDEN_A),.012*math.sin(k*GOLDEN_A),hf(0,0)-.01)),k*GOLDEN_A,rng.uniform(.05,.08),rng.uniform(.012,.016),rng)
    K.link('Qinglan_Sheaths',sh,[M['sheath']])
    # --- leaves: outer long arching ones first, inner young ones shorter and more upright
    lv=K.new_bm();z0=hf(0,0)-.005
    for i in range(26):
        inner=i>=20;az=i*K.GOLDEN+rng.uniform(-.2,.2)
        L=rng.uniform(.26,.36) if inner else rng.uniform(.40,.58);W=rng.uniform(.017,.021) if inner else rng.uniform(.023,.031)
        t0=rng.uniform(.03,.14) if inner else rng.uniform(.14,.42);t1=rng.uniform(.55,1.0) if inner else rng.uniform(1.45,2.25)
        n=24;pts,h=leaf_path(Vector((.016*math.cos(az),.016*math.sin(az),z0)),az,L,t0,t1,rng.uniform(-.05,.05),n)
        ws=leaf_widths(W,n);side=Vector((-h.y,h.x,0));dry=0.15 if inner else rng.choice((.25,.35,.35,.45,.6,1.0));tw=rng.uniform(-.9,.9)
        K.ribbon_into(lv,pts,ws,side,.5,tw,5,(rng.random(),dry,0),lambda u:abs(u))
    K.link('Qinglan_Leaves',lv,[M['leaf']])
    sc_bm=K.new_bm();bl=K.new_bm()
    scapes=[(.35,.56),(1.9,.50),(3.4,.53),(5.0,.47)]
    if post:
        for j,(az,H) in enumerate(scapes):                                                          # tall stubs with pale cut faces (R01b)
            b0=Vector((.010*math.cos(az),.010*math.sin(az),z0));h=Vector((math.cos(az),math.sin(az),0));top=H*rng.uniform(.52,.64);n=8
            pts=[b0+h*.03*(k/n)**1.4+Vector((0,0,top*k/n)) for k in range(n+1)]
            rings=K.tube_into(sc_bm,pts,[.0040-.0006*k/n for k in range(n+1)],8)
            for v in rings[-1]:K.tag_uv(v,.5,.5,(0,0,1))
            for t0,Lb in ((.15,.035),(.40,.03)):sheath_into(sc_bm,pts[int(t0*n)],az+t0*9,Lb,.007,rng)
        for k,(x,y,a,L) in enumerate([(-.20,-.16,.6,.16),(.06,-.24,2.6,.13),(.24,-.04,1.4,.11)]):    # cut scape pieces on the soil
            d=Vector((math.cos(a),math.sin(a),0));c=Vector((x,y,0));pts=[]
            for t in [q/6 for q in range(7)]:p=c+d*L*(t-.5);pts.append(p+Vector((0,0,hf(p.x,p.y)+.0045)))
            rings=K.tube_into(sc_bm,pts,[.0036]*7,8)
            for v in rings[0]+rings[-1]:K.tag_uv(v,.5,.5,(0,0,1))
        for x,y in [(.15,-.19),(-.07,-.22)]:                                                        # two fallen blossoms
            flower_into(bl,sc_bm,Vector((x,y,hf(x,y)+.006)),Vector((rng.uniform(-.4,.4),rng.uniform(-.4,.4),1)),Vector((1,0,0)),.95,rng)
    else:
        for j,(az,H) in enumerate(scapes):
            b0=Vector((.010*math.cos(az),.010*math.sin(az),z0));h=Vector((math.cos(az),math.sin(az),0));n=18
            pts=[b0+h*(.07*(t**1.3)+.010*math.sin(t*math.pi))+Vector((0,0,H*t)) for t in [k/n for k in range(n+1)]]
            K.tube_into(sc_bm,pts,[.0038-.0018*k/n for k in range(n+1)],8)
            for t0,Lb in ((.12,.035),(.26,.03),(.40,.022)):sheath_into(sc_bm,pts[int(t0*n)],az+t0*9,Lb,.006,rng)
            nf=5;nb=4
            for k in range(nf+nb):
                bud=k>=nf;t=(.44+.36*k/(nf-1)) if not bud else (.84+.16*(k-nf)/(nb-1));p=pts[min(int(t*n),n)];sd=(1 if k%2 else -1)
                out=Matrix.Rotation(.6*sd*k/(nf+nb),3,'Z')@(h.cross(Vector((0,0,1)))*sd*.9+h*.45).normalized()
                if bud:
                    c=p+out*.007+Vector((0,0,.004));K.tube_into(sc_bm,[p,c],[.0013,.0011],5,False)
                    flower_into(bl,sc_bm,c,(out*.5+Vector((0,0,1))).normalized(),out,1.1,rng,bud=True);continue
                c=p+out*.020+Vector((0,0,.002))
                K.tube_into(sc_bm,[p,p+out*.010+Vector((0,0,.003)),c],[.0016,.0014,.0013],5,False)            # pedicel + ovary
                sheath_into(sc_bm,p,az+sd*1.2,.012,.003,rng)                                                # floral bract
                flower_into(bl,sc_bm,c,(out+Vector((0,0,.15))).normalized(),Vector((0,0,1)),rng.uniform(1.25,1.4),rng)
    bl_v={v:K.ctx.vdata.pop(v) for v in bl.verts if v in K.ctx.vdata}                              # K.link clears vdata: keep the blossoms' UV / Var
    K.link('Qinglan_Scapes',sc_bm,[M['scape']])
    K.ctx.vdata.update(bl_v)
    if len(bl.verts):K.link('Qinglan_Blossoms',bl,[M['blossom']],True)
    else:bl.free()
    ctx.extra.update({'reference':'ai_threeview_v002/R01b_QX_SpiritHerb_Qinglan_post.png' if post else 'ai_threeview_v002/R01_QX_SpiritHerb_Qinglan.png',
                      'state_change':'post: all four scapes cut to tall stubs with pale cut faces, leaves kept, three cut scape pieces and two blossoms on the soil' if post else 'pre'})

GOLDEN_A=2.39996
