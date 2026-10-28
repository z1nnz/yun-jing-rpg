"""QX_SpiritHerb_Chilu rebuild (red-berry spirit herb, ginseng-like). Semi-real.
Layout: a dense grassy patch; three fruiting plants of graded size and three young one- or two-leaf plants grow
through it, so the crimson umbels sit among the grass blades rather than on bare soil.
Each plant: one S-curved stem with a swollen node at the whorl, purple-red toward the top | four palmate leaves
of graded size (main, two secondary, one young) on petioles of different length and droop, five serrated
leaflets each, overlapping in depth | a peduncle leaning out of the whorl carrying a dense umbel of berries:
varied size, a tight core with looser outliers, a few under-ripe orange / green ones.
Ground: the shared soil / pebble / moss skirt, covered by jittered tufts of green meadow grass (a few dry blades).
Post: every umbel stripped (bare and broken pedicels, one missed green berry), one leaf snapped and wilting,
grass trampled flat round the main plant, crushed berries on the soil.
Origin: stem base at (0,0,0) = ground level; front -Y.
"""
import bpy,bmesh,math,random
from mathutils import Vector,Matrix,noise
import qx_kit as K
import qx_ore as O

TAU=math.tau
BED=(.50,.45)

def bed_h(x,y):return O.skirt_height(x,y,BED,.035)

def curve(pts,n=24):
    """Catmull-Rom through pts."""
    P=[Vector(p) for p in pts];P=[P[0]*2-P[1]]+P+[P[-1]*2-P[-2]];out=[]
    for i in range(1,len(P)-2):
        a,b,c,d=P[i-1],P[i],P[i+1],P[i+2]
        for k in range(n):
            t=k/n;t2,t3=t*t,t*t*t;out.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t2+(-a+3*b-3*c+d)*t3))
    out.append(P[-2]);return out

def leaflet(bm,base,d,L,W,droop,curl,twist,var,rng):
    """Serrated elliptic-acuminate leaflet: V-folded midrib, blistered surface between the veins,
    wavy margin, tip drooping, slight lateral curl. UV u across, v base->tip."""
    d=d.normalized();side=d.cross(Vector((0,0,1)));side=side.normalized() if side.length>1e-4 else Vector((1,0,0))
    n=30;pts=[];ws=[]
    for j in range(n+1):
        t=j/n;p=base+d*L*t+Vector((0,0,-droop*t**2))+side*curl*t*t+Vector((0,0,.0010*math.sin(t*math.pi*5)*t))
        pts.append(p)
        w=W*math.sin(math.pi*min(.999,t*1.04))**.72*(1-.45*(1-t)**3)*(1-.55*max(0,t-.8)/.2)
        ws.append(w*(1-(.06 if j%2 else .02*(j%4==0))*(t>.12))+.0005)
    K.ribbon_into(bm,pts,ws,side,.16,twist,7,var,lambda u:abs(u)**1.25)

def berry_into(bm,c,d,r,var):
    for v in K.ico_into(bm,3,r,Matrix.Translation(c)@d.to_track_quat('Z','Y').to_matrix().to_4x4()@Matrix.Diagonal((1.16,.84,.90,1))):
        lo=v.co-c;k=lo.normalized().dot(d)
        if k<-.86:v.co+=d*r*.16*(-k-.86)/.14                                                 # dimple where the pedicel joins
        if k>.9:v.co-=d*r*.10*(k-.9)/.1                                                     # shallow seam at the stylar end
        K.tag_uv(v,.5,.5,(var[0],var[1],K.c01((k-.93)/.07)))

# ---------------------------------------------------------------- materials
def mat_leaf_real(name):
    """Thin leaf: deep green upper face, paler midrib and pinnate secondaries, faint tertiary net,
    yellowing serrated margin, blistered relief, back-light translucency; Var.g = wilt."""
    m,nt,bs=K.pbr(name,False,.42,.4);u,v=K.uv(nt);r,g,b=K.attr(nt);ob=K.coord(nt)
    mr,mx,ad,mrng,m_=K.mul,K.mix,K.add,K.mrange,K.math_
    ax=m_(nt,'ABSOLUTE',m_(nt,'SUBTRACT',u,.5))
    sec=K.wave_t(nt,K.comb(nt,0,ad(nt,mr(nt,v,1.0),mr(nt,ax,.75))),8.5,'Y',.6,1)
    vein=m_(nt,'MAXIMUM',mr(nt,mrng(nt,sec,.86,.98),mrng(nt,ax,.46,.30)),mrng(nt,ax,.03,.008))
    tert=mrng(nt,K.voronoi_t(nt,K.comb(nt,mr(nt,u,2.0),mr(nt,v,6.0)),6,'DISTANCE_TO_EDGE'),.03,.0)
    col=K.ramp(nt,ad(nt,mr(nt,K.noise_t(nt,ob,9,4),.5),mr(nt,r,.5)),[(0,(.018,.05,.012)),(.5,(.03,.075,.018)),(1,(.05,.10,.024))])
    col=mx(nt,mr(nt,mrng(nt,ax,.36,.5),.6),col,(.075,.10,.025))                                  # margin yellowing
    col=mx(nt,mr(nt,tert,.22),col,(.06,.11,.03));col=mx(nt,mr(nt,vein,.6),col,(.10,.16,.05))
    spots=mr(nt,mrng(nt,K.voronoi_t(nt,ob,140),.10,.05),mrng(nt,K.noise_t(nt,ob,7),.62,.68))
    col=mx(nt,mr(nt,spots,.7),col,(.08,.06,.02))
    wilt=mr(nt,g,mrng(nt,K.noise_t(nt,ob,14),.3,.6,.55,1));col=mx(nt,wilt,col,(.11,.085,.03))
    blister=K.noise_t(nt,K.comb(nt,mr(nt,u,8),mr(nt,v,24)),1,3)
    K.finish(nt,bs,col,mx(nt,wilt,(.42,.42,.42),(.75,.75,.75)),ad(nt,mr(nt,vein,-1.2),mr(nt,blister,.5)),.3,.002)
    out=next(x for x in nt.nodes if x.type=='OUTPUT_MATERIAL');tr=K.node(nt,'ShaderNodeBsdfTranslucent')
    K._set(nt,tr.inputs['Color'],mx(nt,wilt,K.ramp(nt,mr(nt,vein,1),[(0,(.10,.24,.03)),(1,(.18,.30,.06))]),(.25,.18,.05)))
    mixs=K.node(nt,'ShaderNodeMixShader',{0:.28});nt.links.new(bs.outputs[0],mixs.inputs[1]);nt.links.new(tr.outputs[0],mixs.inputs[2]);nt.links.new(mixs.outputs[0],out.inputs['Surface'])
    return m

def mat_berry_real(name,dull=False):
    """Glossy ripe berry: deep red with subsurface glow, faint lenticels, darker round the calyx dimple;
    Var.g = ripeness (0 ripe red .. .5 orange .. 1 green). Faint inner emission = the spirit-herb accent."""
    m,nt,bs=K.pbr(name,True,.30 if not dull else .55,.5);ob=K.coord(nt);r,g,b=K.attr(nt)
    col=K.ramp(nt,K.add(nt,g,K.mul(nt,K.noise_t(nt,ob,60,2),.10)),[(0,(.30,.010,.010)),(.12,(.40,.022,.014)),(.5,(.52,.15,.02)),(1,(.16,.27,.05))] if not dull else [(0,(.07,.010,.008)),(1,(.13,.04,.02))])
    col=K.mix(nt,K.mul(nt,K.mrange(nt,K.voronoi_t(nt,ob,900),.10,.05),.25),col,(.50,.22,.16))
    col=K.mix(nt,K.mrange(nt,b,.2,.6),col,(.035,.02,.012))                                   # dark stylar point
    sub=bs.inputs.get('Subsurface Weight')
    if sub and not dull:sub.default_value=.45;bs.inputs['Subsurface Radius'].default_value=(1,.25,.12);bs.inputs['Subsurface Scale'].default_value=.006
    coat=bs.inputs.get('Coat Weight')
    if coat and not dull:coat.default_value=.25
    if not dull:
        nt.links.new(K.ramp(nt,g,[(0,(1,.10,.03)),(.6,(.6,.15,.0)),(1,(0,0,0))]),bs.inputs['Emission Color']);bs.inputs['Emission Strength'].default_value=.12
    K.finish(nt,bs,col,None,K.noise_t(nt,ob,300,3),.04,.001);return m

def mat_stem_real(name):
    """Green stem flushing purple-red above the node; fine longitudinal striations; Var.b = broken end."""
    m,nt,bs=K.pbr(name,True,.5,.35);ob=K.coord(nt);z=K.sep(nt,ob)[2];r,g,b=K.attr(nt)
    col=K.ramp(nt,K.mrange(nt,z,.02,.42),[(0,(.045,.06,.02)),(.25,(.05,.10,.03)),(.62,(.10,.06,.035)),(1,(.20,.04,.035))])
    col=K.mix(nt,K.mrange(nt,b,.86,.98),col,(.17,.13,.06));col=K.mix(nt,K.mul(nt,g,.8),col,(.10,.08,.03))
    K.finish(nt,bs,col,None,K.noise_t(nt,K.scaled(nt,ob,(1,1,10)),90,2),.15,.001);return m

def mat_grass_real(name):
    """Meadow grass blade: dark green at the base to fresh green, slightly paler tips, parallel veins,
    a few blades straw-dry (Var.g), back-light translucency."""
    m,nt,bs=K.pbr(name,False,.5,.4);u,v=K.uv(nt);r,g,b=K.attr(nt);ob=K.coord(nt)
    mr,mx,ad,mrng=K.mul,K.mix,K.add,K.mrange
    veins=K.wave_t(nt,K.comb(nt,u,0),4,'X',.2,1)
    col=K.ramp(nt,ad(nt,v,mr(nt,K.noise_t(nt,ob,4,3),.25)),[(0,(.018,.035,.010)),(.35,(.040,.075,.018)),(.85,(.070,.110,.026)),(1,(.11,.13,.04))])
    col=mx(nt,mr(nt,r,.35),col,(.05,.09,.022))
    dry=mr(nt,mrng(nt,g,.2,.9),mrng(nt,ad(nt,v,mr(nt,g,.6)),.5,.9));col=mx(nt,dry,col,K.ramp(nt,r,[(0,(.15,.12,.06)),(1,(.24,.20,.10))]))
    col=mx(nt,mr(nt,mrng(nt,veins,.8,1),.2),col,(0,0,0))
    K.finish(nt,bs,col,mx(nt,dry,(.45,.45,.45),(.8,.8,.8)),veins,.1,.0008)
    out=next(x for x in nt.nodes if x.type=='OUTPUT_MATERIAL');tr=K.node(nt,'ShaderNodeBsdfTranslucent')
    K._set(nt,tr.inputs['Color'],mx(nt,dry,(.08,.20,.03),(.26,.20,.08)))
    mixs=K.node(nt,'ShaderNodeMixShader',{0:.3});nt.links.new(bs.outputs[0],mixs.inputs[1]);nt.links.new(tr.outputs[0],mixs.inputs[2]);nt.links.new(mixs.outputs[0],out.inputs['Surface'])
    return m

def mat_litter(name):
    m,nt,bs=K.pbr(name,False,.7,.3);u,v=K.uv(nt);r,g,b=K.attr(nt);ob=K.coord(nt)
    col=K.ramp(nt,K.add(nt,K.mul(nt,r,.6),K.mul(nt,K.noise_t(nt,ob,30,4),.4)),[(0,(.03,.02,.012)),(.5,(.07,.045,.022)),(1,(.13,.085,.035))])
    col=K.mix(nt,K.mrange(nt,K.math_(nt,'ABSOLUTE',K.math_(nt,'SUBTRACT',u,.5)),.03,.0),col,(.10,.07,.035))   # midrib
    K.finish(nt,bs,col,None,K.noise_t(nt,ob,80,3),.2,.001);return m

# ---------------------------------------------------------------- build
# (base x, base y, scale, rotation, leaves, umbel tries; 0 tries = young plant without fruit)
PLANTS=[(0,0,1.0,0.0,4,34),(.19,-.12,.74,.9,3,24),(-.17,.09,.64,2.3,3,18),(-.06,-.23,.50,4.0,2,0),(.10,.21,.44,1.4,1,0),(-.30,-.10,.40,5.2,1,0)]

def plant_into(st,lv,br,cfg,post,rng,main):
    """One plant built at the origin, then scaled / turned / moved onto its base. Returns placed umbel count."""
    bx,by,s,rot,nl,tries=cfg;marks=[len(st.verts),len(lv.verts),len(br.verts)]
    node_=Vector((.012,-.006,.16 if tries else .11))
    path=curve([(0,0,-.01),(.006,.004,node_.z*.35),(-.004,.002,node_.z*.68),node_],8)
    rad=[.0062-.0016*i/(len(path)-1) for i in range(len(path))];rad[-1]=.0065;rad[-2]=.0055
    K.tube_into(st,path,rad,10)
    leaves=[(0.35,1.00,.105,.010),(1.95,.82,.085,.020),(3.55,.78,.090,.0),(5.0,.58,.060,.028)][:nl]
    for k,(az,sc,pl,dz) in enumerate(leaves):
        az+=rng.uniform(-.12,.12);h=Vector((math.cos(az),math.sin(az),0))
        if post and main and k==1:                                                               # snapped petiole, wilting leaf hanging
            kink=node_+h*.035+Vector((0,0,.012));end=kink+h*.02+Vector((0,0,-.085))
            K.tube_into(st,[node_,kink,end],[.0032,.003,.0026],7)
            for f in range(5):
                a=(f-2)*.42;dd=Vector((h.x*math.cos(a)-h.y*math.sin(a),h.x*math.sin(a)+h.y*math.cos(a),-1.7))
                Ls=[.06,.08,.10,.08,.06][f]*sc;leaflet(lv,end,dd,Ls,Ls*.36,.012,.004*(f-2),.4*(f-2),(rng.random(),1,0),rng)
            continue
        tip=node_+h*pl+Vector((0,0,.022+dz))
        K.tube_into(st,curve([node_,node_+h*pl*.5+Vector((0,0,.020+dz*.8)),tip],6),[.0034,.0031,.003,.0028,.0027,.0026,.0026,.0025,.0025,.0024,.0024,.0024,.0024],7)
        for f in range(5):
            a=(f-2)*.60+rng.uniform(-.06,.06);dd=Vector((h.x*math.cos(a)-h.y*math.sin(a),h.x*math.sin(a)+h.y*math.cos(a),.18+.06*(2-abs(f-2))))
            Ls=[.065,.095,.125,.095,.065][f]*sc*rng.uniform(.92,1.06)
            leaflet(lv,tip,dd,Ls,Ls*.37,.032*sc,.006*(f-2)*rng.uniform(.6,1.2),.18*(f-2),(rng.random(),.12 if post else 0,0),rng)
    placed=[]
    if tries:
        pk=node_+Vector((-.012,.010,.09))
        K.tube_into(st,curve([node_,node_+Vector((.0,.006,.045)),pk],6),[.0038,.0036,.0034,.0032,.003,.003,.0029,.0028,.0028,.0028,.0028,.0028,.0028],7)
        rng2=random.Random(77+int(bx*1000))
        for bi in range(tries):
            phi=math.acos(1-1.3*(bi+.5)/tries)*(1 if bi<tries*.7 else 1.10);th=bi*K.GOLDEN+rng2.uniform(-.2,.2)
            d=Vector((math.sin(phi)*math.cos(th),math.sin(phi)*math.sin(th),math.cos(phi)+.15)).normalized()
            outlier=bi>=tries*.76;L=(.017 if not outlier else .026)*rng2.uniform(.88,1.12);r=rng2.uniform(.0058,.0078)*(.85 if outlier else 1)/max(s,.7)**.5
            ripe=0.0 if rng2.random()>.18 else rng2.choice((.5,.5,1.0))
            tipp=pk+d*L
            if any((tipp-q).length<r*1.45 for q in placed):continue
            placed.append(tipp)
            if post:
                if main and bi==7:                                                                  # one missed green berry
                    K.tube_into(st,[pk,tipp],[.0011,.0009],5);berry_into(br,tipp+d*.005,d,.0058,(rng2.random(),1.0,0))
                else:
                    e=pk+d*L*rng2.uniform(.45,1.0);rg=K.tube_into(st,[pk,e],[.0011,.0009],5)
                    for v in rg[-1]:K.tag_uv(v,.5,.5,(0,0,1))
                continue
            K.tube_into(st,[pk,pk+d*L*.5+Vector((0,0,.002)),tipp],[.0011,.001,.0009],5,False)
            berry_into(br,tipp+d*r*.85,d,r,(rng2.random(),ripe,0))
    T=Matrix.Translation((bx,by,bed_h(bx,by)))@Matrix.Rotation(rot,4,'Z')@Matrix.Scale(s,4)
    for bm,m0 in zip((st,lv,br),marks):
        bm.verts.ensure_lookup_table();bmesh.ops.transform(bm,matrix=T,verts=bm.verts[m0:])
    return len(placed)

def meadow_into(gr,rng,post):
    """Jittered tufts of meadow grass over the whole bed, kept off the plant stems; after harvest the tufts
    round the main plant are trampled flat, leaning away from it."""
    step=.052;n=0
    for ix in range(-12,13):
        for iy in range(-12,13):
            x=ix*step+rng.uniform(-.02,.02);y=iy*step+rng.uniform(-.02,.02)
            ell=(x/BED[0])**2+(y/BED[1])**2;edge=O.sm01(.40,.95,ell)
            if ell>.95 or rng.random()<edge*.55:continue                                        # thinner toward the rim
            if any(math.hypot(x-px,y-py)<.03+.03*ps for px,py,ps,*_ in PLANTS):continue
            rr=math.hypot(x,y);trample=post and rr<.22;away=math.atan2(y,x)
            hb=(.10+.20*(noise.noise(Vector((x*4,y*4,3)))*.5+.5))*(1-.72*edge)                     # and shorter, so the patch feathers out
            c=Vector((x,y,bed_h(x,y)-.004))
            for b in range(rng.randint(5,9)):
                az=away+rng.uniform(-.6,.6) if trample or rng.random()<edge*.8 else rng.uniform(0,TAU)
                H=hb*rng.uniform(.6,1.1)*(.85 if trample else 1)
                t0,t1=(rng.uniform(.9,1.2),rng.uniform(1.45,1.62)) if trample else (rng.uniform(.04,.30)+.25*edge,rng.uniform(.45,1.35)+.35*edge)
                pts,h=K.arch(c+Vector((rng.uniform(-.008,.008),rng.uniform(-.008,.008),0)),az,H,t0,t1,6,1.6)
                dry=rng.choices((0,.35,1.0),(85,10,5))[0]
                K.ribbon_into(gr,pts,[rng.uniform(.0028,.0042)*(1-j/6)**.65+.0003 for j in range(7)],Vector((-h.y,h.x,0)),.3,rng.uniform(-.6,.6),3,(rng.random(),dry,0))
            n+=1
    return n

def build(post):
    rng=random.Random(3201);ctx=K.ctx
    M={'leaf':mat_leaf_real('QX_Src_Chilu_Leaf'),'berry':mat_berry_real('QX_Src_Chilu_Berry'),'crushed':mat_berry_real('QX_Src_Chilu_Berry_Crushed',True),
       'stem':mat_stem_real('QX_Src_Chilu_Stem'),'litter':mat_litter('QX_Src_Chilu_Leaf_Litter'),'skirt':O.mat_skirt('QX_Src_Chilu_Soil_Bed'),
       'moss':O.mat_moss_real('QX_Src_Chilu_Moss'),'rock':O.mat_rock_real('QX_Src_Chilu_Pebble',False,False),'grass':mat_grass_real('QX_Src_Chilu_Meadow_Grass')}
    # --- soil bed in the shared ground language (mostly hidden by the grass)
    sk=K.new_bm();O.skirt_into(sk,BED,.035,14,72,23);K.link('Chilu_Soil_Bed',sk,[M['skirt']])
    pb=bmesh.new();n=0
    for k in range(200):
        if n>=12:break
        a=rng.uniform(0,TAU);s_=rng.uniform(.3,.92);x,y=BED[0]*s_*math.cos(a),BED[1]*s_*math.sin(a);sz=rng.uniform(.010,.028)*(1.8 if k<2 else 1)
        b=O.hull_block((x,y,bed_h(x,y)+sz*.05),(sz*1.3,sz,sz*.6),800+k,24,.6,(0,0,rng.uniform(0,TAU)),rmin=.7);O.finish_block(b,sz*.12,max(bed_h(x,y)-.002,0));K.merge_into(pb,b);n+=1
    me=bpy.data.meshes.new('Chilu_Pebbles_Mesh');pb.to_mesh(me);pb.free();po=bpy.data.objects.new('Chilu_Pebbles',me);ctx.coll.objects.link(po);po.parent=ctx.root
    po.hide_render=True;po['qx_role']='game_low_poly';me.materials.append(M['rock']);ctx.objs.append(po)
    ph=O.remeshed(po,'Chilu_Pebbles_HP',ctx.coll,.003,1);ph.parent=ctx.root;hb,_=O.sculpt(ph,.15,.25,7,False,False);hb.free()
    ph.data.materials.append(M['rock']);ph['qx_role']='bake_source_high_poly';ctx.objs.append(ph)
    mo=K.new_bm()
    for k,(x,y,rx,ry) in enumerate([(-.30,.20,.09,.06),(.26,.22,.07,.05),(.30,-.25,.06,.04)]):
        K.lumpy_into(mo,(x,y,bed_h(x,y)-.006),(rx,ry,.018),900+k,3,.25,2.5,k)
    K.flat_base(mo,0.0);mc=K.link('Chilu_Moss_Cushions',mo,[M['moss']])
    ca=mc.data.color_attributes.new('Ms','FLOAT_COLOR','POINT')
    for i,v in enumerate(mc.data.vertices):ca.data[i].color=(K.c01(v.co.z/.015),noise.noise(v.co*9)*.5+.5,0,1)
    lt=K.new_bm()                                                                                  # leaf litter between the tufts
    for k in range(16):
        a=rng.uniform(0,TAU);s_=rng.uniform(.25,.9);x,y=BED[0]*s_*math.cos(a),BED[1]*s_*math.sin(a);az=rng.uniform(0,TAU);L=rng.uniform(.03,.06)
        p0=Vector((x,y,bed_h(x,y)+.002));d=Vector((math.cos(az),math.sin(az),0));pts=[p0+d*L*t/6+Vector((0,0,.004*math.sin(t/6*math.pi)+.003*(t/6)**2)) for t in range(7)]
        K.ribbon_into(lt,pts,[L*.20*math.sin(math.pi*min(.99,t/6*1.05))**.8+.0005 for t in range(7)],Vector((-d.y,d.x,0)),.45,rng.uniform(-.5,.5),5,(rng.random(),0,0))
    K.link('Chilu_Leaf_Litter',lt,[M['litter']],False)
    gr=K.new_bm();tufts=meadow_into(gr,rng,post);K.link('Chilu_Meadow_Grass',gr,[M['grass']],False)
    # --- the plants growing through the grass
    st=K.new_bm();lv=K.new_bm();br=K.new_bm();umbel=[]
    for k,cfg in enumerate(PLANTS):umbel.append(plant_into(st,lv,br,cfg,post,rng,k==0))
    keep_st={v:ctx.vdata.pop(v) for v in st.verts if v in ctx.vdata};keep_br={v:ctx.vdata.pop(v) for v in br.verts if v in ctx.vdata}
    K.link('Chilu_Leaves',lv,[M['leaf']],True)
    ctx.vdata.update(keep_st)
    K.link('Chilu_Stem_Petioles',st,[M['stem']])
    ctx.vdata.update(keep_br)
    if len(br.verts):K.link('Chilu_Berries' if not post else 'Chilu_Missed_Berry',br,[M['berry']])
    else:br.free()
    if post:
        fb=K.new_bm()
        for x,y in [(.10,-.12),(-.13,-.06),(.24,-.03)]:
            n0=len(fb.verts);berry_into(fb,Vector((x,y,bed_h(x,y)+.004)),Vector((0,0,1)),.0075,(0,0,0))
            for v in list(fb.verts)[n0:]:v.co.z=max(bed_h(x,y)+.001,bed_h(x,y)+(v.co.z-bed_h(x,y))*.45)   # crushed
        K.link('Chilu_Crushed_Berries',fb,[M['crushed']])
    ctx.extra.update({'umbel_positions':str(umbel),'grass_tufts':tufts,'state_change':'post: all umbels stripped, bare and broken pedicels, one missed green berry, leaf snapped and wilting, grass trampled round the main plant, crushed berries' if post else 'pre'})
