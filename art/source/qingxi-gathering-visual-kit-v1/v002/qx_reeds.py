"""QX_WaterReeds rebuild: water-edge reed clump, semi-real. Two species read at once:
Typha (cattail): nine shoots, each a flat fan of thick strap leaves, spiralling slowly, tips yellowing, a few
kinked and broken; five flower stems with velvety brown female spikes, the thin male spike above, one spike
bursting into pale fluff | Phragmites (common reed): three jointed culms with node sheaths, lanceolate leaves
drooping from the nodes and nodding purple-brown plumes with silvery hairs | last year's dead leaves folded
down onto the mud.
Ground: a low wet mud tuft (sheen, puddles, silt rim) with pebbles and grass on the rim in the shared language.
Origin: bottom centre; front -Y.
"""
import bpy,bmesh,math,random
from mathutils import Vector,Matrix,noise
import qx_kit as K
import qx_ore as O
import qx_chilu as C
import qx_ground as GR

TAU=math.tau
BED=(.55,.48)

def strap(bm,base,az,L,W,t0,t1,twist,var,rng,kink=False,flat_dir=None,n=22):
    pts,h=K.arch(base,az,L,t0,t1,n,2.0);side=flat_dir if flat_dir is not None else Vector((-h.y,h.x,0))
    if kink:
        k=rng.randint(int(n*.45),int(n*.7));dn=(h*.5+Vector((0,0,-1))).normalized();seg=L/n
        pts=pts[:k+1]+[pts[k]+dn*seg*s for s in range(1,n-k+1)]
    ws=[W*(.75+.25*min(1,j/(n*.15)))*(1-j/n)**.55+.0005 for j in range(n+1)]
    K.ribbon_into(bm,pts,ws,side,.30,twist,5,var,lambda u:abs(u)**1.4)

# ---------------------------------------------------------------- materials
def mat_reed_leaf(name):
    """Green strap / blade: fine parallel veins, pale sheath base, yellowing to straw toward dry tips
    (Var.g), dead grey-brown leaves (Var.b), back-light translucency."""
    m,nt,bs=K.pbr(name,False,.48,.4);u,v=K.uv(nt);r,g,b=K.attr(nt);ob=K.coord(nt)
    mr,mx,ad,mrng,m_=K.mul,K.mix,K.add,K.mrange,K.math_
    veins=K.wave_t(nt,K.comb(nt,u,0),9,'X',.2,1)
    col=K.ramp(nt,ad(nt,mr(nt,K.noise_t(nt,ob,5,4),.6),mr(nt,r,.4)),[(0,(.028,.055,.016)),(.5,(.045,.080,.022)),(1,(.075,.105,.030))])
    col=mx(nt,mr(nt,mrng(nt,v,.12,.0),.8),col,(.13,.15,.07))
    dz=m_(nt,'SUBTRACT',1.0,mr(nt,g,.65));dry=mrng(nt,ad(nt,v,mr(nt,K.noise_t(nt,ob,9,3),.08)),m_(nt,'SUBTRACT',dz,.10),dz)
    dry=mr(nt,dry,mrng(nt,g,.02,.1))
    col=mx(nt,dry,col,K.ramp(nt,ad(nt,mr(nt,r,.5),mr(nt,K.noise_t(nt,ob,40,3),.5)),[(0,(.17,.14,.07)),(1,(.30,.25,.13))]))
    col=mx(nt,mrng(nt,b,.4,.8),col,K.ramp(nt,K.noise_t(nt,ob,25,3),[(0,(.07,.06,.045)),(1,(.15,.13,.10))]))
    col=mx(nt,mr(nt,mrng(nt,veins,.78,1),.22),col,(0,0,0))
    K.finish(nt,bs,col,mx(nt,ad(nt,dry,b),(.42,.42,.42),(.80,.80,.80)),mr(nt,veins,.35),.15,.001)
    out=next(x for x in nt.nodes if x.type=='OUTPUT_MATERIAL');tr=K.node(nt,'ShaderNodeBsdfTranslucent')
    K._set(nt,tr.inputs['Color'],mx(nt,ad(nt,dry,b),(.10,.22,.04),(.30,.24,.10)))
    mixs=K.node(nt,'ShaderNodeMixShader',{0:.25});nt.links.new(bs.outputs[0],mixs.inputs[1]);nt.links.new(tr.outputs[0],mixs.inputs[2]);nt.links.new(mixs.outputs[0],out.inputs['Surface'])
    return m

def mat_culm(name):
    """Stems / culms: green at the foot, straw above, darker node bands (Var.b), fine striation."""
    m,nt,bs=K.pbr(name,True,.5,.4);ob=K.coord(nt);z=K.sep(nt,ob)[2];r,g,b=K.attr(nt)
    col=K.ramp(nt,K.add(nt,K.mrange(nt,z,.1,1.4),K.mul(nt,K.noise_t(nt,ob,6,3),.15)),[(0,(.05,.08,.025)),(.5,(.10,.12,.045)),(1,(.22,.19,.10))])
    col=K.mix(nt,K.mrange(nt,b,.4,.9),col,(.06,.05,.03))
    K.finish(nt,bs,col,None,K.noise_t(nt,K.scaled(nt,ob,(1,1,14)),90,2),.12,.001);return m

def mat_cattail(name):
    """Female spike: dense dark cinnamon velvet, slightly lighter at the shoulders, soft sheen; male spike
    above thin and straw (Var.b)."""
    m,nt,bs=K.pbr(name,True,.9,.3);ob=K.coord(nt);r,g,b=K.attr(nt)
    fz=K.noise_t(nt,ob,700,2);col=K.ramp(nt,K.add(nt,K.mul(nt,K.noise_t(nt,ob,30,3),.6),K.mul(nt,fz,.4)),[(0,(.035,.020,.012)),(.6,(.075,.045,.025)),(1,(.11,.07,.04))])
    col=K.mix(nt,K.mrange(nt,b,.4,.8),col,(.20,.17,.10))
    sh=bs.inputs.get('Sheen Weight')
    if sh:sh.default_value=.6;bs.inputs['Sheen Tint'].default_value=(.8,.6,.45,1)
    K.finish(nt,bs,col,None,fz,.35,.002);return m

def mat_fluff(name):
    m,nt,bs=K.pbr(name,False,.95,.2);ob=K.coord(nt)
    col=K.ramp(nt,K.noise_t(nt,ob,60,4),[(0,(.36,.32,.26)),(1,(.62,.58,.50))])
    sh=bs.inputs.get('Sheen Weight')
    if sh:sh.default_value=1.0;bs.inputs['Sheen Tint'].default_value=(1,1,1,1)
    sub=bs.inputs.get('Subsurface Weight')
    if sub:sub.default_value=.4;bs.inputs['Subsurface Scale'].default_value=.004
    K.finish(nt,bs,col,None,K.noise_t(nt,ob,300,3),.5,.002);return m

def mat_plume(name):
    """Reed plume spikelets: purple-brown at the base, silvery hairs toward the tips."""
    m,nt,bs=K.pbr(name,False,.75,.3);u,v=K.uv(nt);r,g,b=K.attr(nt);ob=K.coord(nt)
    col=K.ramp(nt,K.add(nt,v,K.mul(nt,r,.3)),[(0,(.10,.05,.05)),(.5,(.20,.13,.11)),(1,(.46,.43,.38))])
    sh=bs.inputs.get('Sheen Weight')
    if sh:sh.default_value=.8;bs.inputs['Sheen Tint'].default_value=(1,1,1,1)
    K.finish(nt,bs,col,None,K.noise_t(nt,ob,200,2),.2,.0005)
    out=next(x for x in nt.nodes if x.type=='OUTPUT_MATERIAL');tr=K.node(nt,'ShaderNodeBsdfTranslucent');K._set(nt,tr.inputs['Color'],(.40,.32,.26))
    mixs=K.node(nt,'ShaderNodeMixShader',{0:.3});nt.links.new(bs.outputs[0],mixs.inputs[1]);nt.links.new(tr.outputs[0],mixs.inputs[2]);nt.links.new(mixs.outputs[0],out.inputs['Surface'])
    return m

def mat_mud(name):
    """Wet mud tuft: near-black brown, wet sheen with mirror-smooth puddles in the hollows, paler dried silt
    toward the rim (Var.r = normalised radius), plant debris flecks."""
    m,nt,bs=K.pbr(name,True,.35,.5);ob=K.coord(nt);s,g,b=K.attr(nt);mr,mx,ad,mrng=K.mul,K.mix,K.add,K.mrange
    col=K.ramp(nt,K.noise_t(nt,ob,6,4),[(0,(.022,.018,.013)),(1,(.050,.040,.028))])
    silt=mrng(nt,ad(nt,s,mr(nt,K.noise_t(nt,ob,3,3),.25)),.75,.95);col=mx(nt,mr(nt,silt,.8),col,K.ramp(nt,K.noise_t(nt,ob,20,3),[(0,(.075,.068,.052)),(1,(.11,.10,.075))]))
    deb=mr(nt,mrng(nt,K.voronoi_t(nt,K.scaled(nt,ob,(1,3,1)),45),.08,.03),.6);col=mx(nt,deb,col,(.12,.09,.05))
    pud=mr(nt,mrng(nt,K.noise_t(nt,ob,4,2),.40,.34),mrng(nt,s,.7,.5))
    col=mx(nt,mr(nt,pud,.6),col,(.012,.012,.010))
    rough=mx(nt,pud,mx(nt,silt,(.30,.30,.30),(.85,.85,.85)),(.03,.03,.03))
    K.finish(nt,bs,col,rough,mr(nt,ad(nt,K.noise_t(nt,ob,40,4),mr(nt,pud,-1)),1),.3,.004);return m

# ---------------------------------------------------------------- build
def build(post):
    rng=random.Random(3601);ctx=K.ctx
    M={'leaf':mat_reed_leaf('QX_Src_Reed_Leaf'),'culm':mat_culm('QX_Src_Reed_Culm'),'cattail':mat_cattail('QX_Src_Reed_Cattail'),
       'fluff':mat_fluff('QX_Src_Reed_Cattail_Fluff'),'plume':mat_plume('QX_Src_Reed_Plume'),
       'skirt':mat_mud('QX_Src_Reed_Wet_Mud'),'rock':O.mat_rock_real('QX_Src_Reed_Pebble',False,False),'moss':O.mat_moss_real('QX_Src_Reed_Moss'),
       'litter':C.mat_litter('QX_Src_Reed_Litter')}
    hf=GR.bed('Reed',BED,.05,rng,M,16,0,(),6,.26,(.01,.035),seed=61)
    lv=K.new_bm();st=K.new_bm();heads=K.new_bm();male=K.new_bm()
    shoots=[]
    for k in range(9):
        a=k*K.GOLDEN+rng.uniform(-.3,.3);r=.04+.17*math.sqrt((k+.5)/9);shoots.append(Vector((r*math.cos(a),r*math.sin(a),0)))
    # --- Typha: flat fans of thick strap leaves
    for k,b in enumerate(shoots):
        b.z=hf(b.x,b.y)-.01;fan=rng.uniform(0,math.pi);fd=Vector((math.cos(fan),math.sin(fan),0));nl=rng.randint(5,7)
        out=Vector((b.x,b.y,0)).normalized() if b.length>.01 else Vector((1,0,0))
        for i in range(nl):
            sg=1 if i%2 else -1;az=math.atan2(fd.y,fd.x)+(0 if sg>0 else math.pi)+rng.uniform(-.25,.25)
            if fd.dot(out)*sg<0 and rng.random()<.5:az+=math.pi*.15
            L=rng.uniform(.75,1.45)*(1-.35*(i>=nl-2));W=rng.uniform(.010,.015);dry=rng.choice((0,.15,.3,.3,.6,1.0))
            strap(lv,b+Vector((0,0,.004*i)),az,L,W,rng.uniform(.01,.08)+.03*i,rng.uniform(.25,.95)+.1*(i<2),rng.uniform(-1.6,1.6),(rng.random(),dry,0),rng,rng.random()<.18,Vector((-math.sin(az),math.cos(az),0)))
    for k in range(9):                                                                              # last year's dead leaves folded onto the mud
        a=k*TAU/9+rng.uniform(-.3,.3);b=shoots[k%9];az=a
        strap(lv,Vector((b.x,b.y,hf(b.x,b.y)-.01)),az,rng.uniform(.5,.9),rng.uniform(.010,.014),rng.uniform(.3,.6),rng.uniform(1.9,2.4),rng.uniform(-1,1),(rng.random(),1,1),rng,rng.random()<.5)
    # --- Typha flower stems: velvety female spike, thin male spike above, one bursting
    for k in range(5):
        b=shoots[(k*2)%9].copy();b.z=hf(b.x,b.y)-.01;H=rng.uniform(1.25,1.65);lean=Vector((b.x,b.y,0)).normalized()*rng.uniform(.04,.12)
        pts=[b+lean*(t*t)+Vector((0,0,H*t)) for t in [s/16 for s in range(17)]];K.tube_into(st,pts,[.0058-.0018*s/16 for s in range(17)],7)
        d=(pts[-1]-pts[-2]).normalized();q=d.to_track_quat('Z','Y').to_matrix().to_4x4();Lf=rng.uniform(.13,.17);rf=rng.uniform(.0125,.016)
        prof=[(0,0),(rf*.6,.003),(rf*.95,.015)]+[(rf*(1+.04*math.sin(i*1.7)),.015+(Lf-.03)*i/6) for i in range(7)]+[(rf*.85,Lf-.004),(rf*.4,Lf),(0,Lf+.002)]
        vs=K.lathe_into(heads,prof,14,jitter=.03);bmesh.ops.transform(heads,matrix=Matrix.Translation(pts[-1]-d*(Lf+.02))@q,verts=vs)
        m0=len(male.verts);rings=K.tube_into(male,[pts[-1]-d*.018,pts[-1]+d*.02,pts[-1]+d*.10],[.0042,.0032,.0012],6)
        for ring in rings:
            for v in ring:K.tag_uv(v,.5,.5,(0,0,1))
        if k==3:                                                                                    # bursting spike: pale fluff cloud on one side
            side=d.orthogonal().normalized();c=pts[-1]-d*(Lf*.55+.02)+side*rf*.9
            fl=bmesh.new();K.lumpy_into(fl,c,(rf*1.5,rf*1.3,Lf*.36),777,4,.20,3.0)
            bmesh.ops.transform(fl,matrix=Matrix.Translation(c)@q@Matrix.Translation(-c),verts=fl.verts[:])
            fluff=fl
    # --- Phragmites: jointed culms, node sheaths, drooping leaves, nodding plumes
    pl=K.new_bm()
    for k in range(3):
        a=k*2.1+.6;b=Vector((.10*math.cos(a),.10*math.sin(a),0));b.z=hf(b.x,b.y)-.01;H=rng.uniform(1.6,1.85);lean=Vector((math.cos(a),math.sin(a),0))*rng.uniform(.08,.16)
        n=24;pts=[b+lean*(t**1.8)+Vector((0,0,H*t)) for t in [s/n for s in range(n+1)]]
        K.tube_into(st,pts,[.0048-.0018*s/n for s in range(n+1)],7)
        for j,zf in enumerate((.12,.24,.36,.48,.60,.71)):
            i0=int(zf*n);p=pts[i0];rings=K.tube_into(st,[p-Vector((0,0,.004)),p+Vector((0,0,.05))],[.0058,.0052],7)
            for v in rings[0]:K.tag_uv(v,.5,.5,(0,0,1))
            az=a+j*math.pi+rng.uniform(-.4,.4);h=Vector((math.cos(az),math.sin(az),0));n2=14;L=rng.uniform(.22,.34);W=rng.uniform(.014,.020)
            lp,hh=K.arch(p+Vector((0,0,.05)),az,L,rng.uniform(.4,.7),rng.uniform(1.7,2.2),n2,1.4)
            K.ribbon_into(lv,lp,[W*math.sin(math.pi*min(.999,.12+t/n2*.95))**.7*(1-t/n2)**.3+.0005 for t in range(n2+1)],Vector((-hh.y,hh.x,0)),.25,rng.uniform(-1.2,1.2),5,(rng.random(),rng.choice((0,.2,.4)),0),lambda u:abs(u)**1.4)
        top=pts[-1];d=(pts[-1]-pts[-2]).normalized();h=Vector((math.cos(a),math.sin(a),0))
        ax=[top+d*.018*s+h*(.0016*s*s)+Vector((0,0,-.0012*s*s)) for s in range(14)]                    # nodding panicle axis
        K.tube_into(st,ax,[.0022-.0012*s/13 for s in range(14)],5)
        for bi in range(20):
            s=1+bi*12/20;i0=int(s);p=ax[i0].lerp(ax[min(i0+1,13)],s-i0);sa=bi*K.GOLDEN
            bd=(h*.6+Vector((math.cos(sa)*.6,math.sin(sa)*.6,-.6-.3*rng.random()))).normalized();Lb=rng.uniform(.06,.13)*(1-.4*bi/20)
            bp=[p+bd*Lb*t+Vector((0,0,-.02*t*t)) for t in (0,.33,.66,1)];K.tube_into(st,bp,[.0009,.0008,.0007,.0005],4,False)
            for si in range(6):
                t=.2+.8*si/5;q=bp[0].lerp(bp[3],t);sd=(bd+Vector((rng.uniform(-.5,.5),rng.uniform(-.5,.5),-.3))).normalized();side=sd.cross(Vector((0,0,1))).normalized()
                K.ribbon_into(pl,[q+sd*.013*u for u in (0,.35,.7,1)],[.0006,.0018,.0016,.0004],side,.2,0,3,(rng.random(),0,0))
    parts=[('Reed_Leaves',lv,M['leaf']),('Reed_Culms_And_Stems',st,M['culm']),('Reed_Cattail_Male_Spikes',male,M['cattail']),
           ('Reed_Cattail_Heads',heads,M['cattail']),('Reed_Plumes',pl,M['plume'])]
    saved=[{v:ctx.vdata.pop(v) for v in bm.verts if v in ctx.vdata} for _,bm,_ in parts]                # K.link clears vdata: link each with its own
    for (name,bm,mat),vd in zip(parts,saved):ctx.vdata.update(vd);K.link(name,bm,[mat])
    fb=K.new_bm();K.merge_into(fb,fluff);K.link('Reed_Cattail_Fluff',fb,[M['fluff']])
