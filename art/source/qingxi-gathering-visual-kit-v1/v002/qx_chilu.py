"""QX_SpiritHerb_Chilu v002 (red-berry spirit herb, ginseng-like). Semi-real.
v002 follows the reviewed AI three-view R02 / R02b (art/references/.../ai_threeview_v002): a low, wide patch
(about 1.0 x 0.3 m in front view) instead of v001's dense meadow that hid the plants.
Layout: one main plant in the centre and a smaller fruiting plant on each side, plus one young plant; the soil,
moss cushions and pebbles stay visible between sparse grass tufts.
Each plant: short thick stem, a low whorl of palmate leaves spread almost flat (five broad serrated leaflets
each) | a straight peduncle rising from the whorl to a dense globe of glossy crimson berries just above the
leaves (main ~0.27 m high), a few under-ripe orange ones.
Post (R02b): the main plant is dug out - a pit of loosened dark soil with clods thrown round it and a torn root;
the side plants keep their leaves but their umbels are stripped to broken pedicels; torn leaflets on the soil.
Origin: centre of the bed at (0,0,0) = ground level; front -Y.
"""
import bpy,bmesh,math,random
from mathutils import Vector,Matrix,noise
import qx_kit as K
import qx_ore as O

TAU=math.tau
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
PLANTS=[(0,0,1.0,0.25,5,64),(-.34,.03,.62,2.1,4,40),(.35,-.02,.58,4.4,4,36),(.15,.25,.36,1.2,2,0)]
BED=(.54,.40)
PIT=(.0,.0,.095)                                                                              # dug pit (x, y, radius) after harvest

def bed_h(x,y):return O.skirt_height(x,y,BED,.03)

def pit_h(x,y):
    """Ground height after the main plant is dug out: a bowl 2.4 cm deep with a thrown-up rim."""
    r=math.hypot(x-PIT[0],y-PIT[1])/PIT[2];w=1+.12*noise.noise(Vector((x*14,y*14,7)))
    return bed_h(x,y)-.024*(1-O.sm01(.0,1.0,r*w))+.007*math.exp(-((r*w-1.15)/.28)**2)

def plant_into(st,lv,br,cfg,post,rng):
    """One plant built at the origin, then scaled / turned / moved onto its base. Returns placed berry count."""
    bx,by,s,rot,nl,tries=cfg;marks=[len(st.verts),len(lv.verts),len(br.verts)]
    node_=Vector((.004,-.002,.045))
    K.tube_into(st,curve([(0,0,-.012),(.003,.001,.02),node_],6),[.0085,.008,.0075,.0072,.007,.007,.0072,.0078,.0082,.0085,.0085,.0085,.0085],10)
    for k in range(nl):
        az=k*TAU/nl+rng.uniform(-.15,.15);h=Vector((math.cos(az),math.sin(az),0));pl=rng.uniform(.085,.105)*(1 if k else .9)
        tip=node_+h*pl*.8+Vector((0,0,.062))
        K.tube_into(st,curve([node_,node_+h*pl*.25+Vector((0,0,.040)),tip],6),[.0036-.00008*i for i in range(13)],7)
        for f in range(5):
            a=(f-2)*.56+rng.uniform(-.06,.06);dd=Vector((h.x*math.cos(a)-h.y*math.sin(a),h.x*math.sin(a)+h.y*math.cos(a),.30+.10*(2-abs(f-2))))
            Ls=[.092,.132,.170,.132,.092][f]*rng.uniform(.92,1.06)
            leaflet(lv,tip,dd,Ls,Ls*.37,.062,.006*(f-2)*rng.uniform(.6,1.2),.16*(f-2),(rng.random(),.08 if post else 0,0),rng)
    placed=[]
    if tries:
        pk=node_+Vector((.004,-.003,.170))
        K.tube_into(st,curve([node_,node_+Vector((-.004,.003,.085)),pk],6),[.0046-.00012*i for i in range(13)],8)
        rng2=random.Random(77+int(bx*1000))
        for bi in range(tries):
            phi=math.acos(1-1.45*(bi+.5)/tries);th=bi*K.GOLDEN+rng2.uniform(-.25,.25)
            d=Vector((math.sin(phi)*math.cos(th),math.sin(phi)*math.sin(th),math.cos(phi)+.15)).normalized()
            L=(.012 if bi<tries*.3 else .018)*rng2.uniform(.9,1.1);r=rng2.uniform(.0086,.0102)
            ripe=0.0 if rng2.random()>.07 else .5
            tipp=pk+d*L;bc=tipp+d*r*.85
            if any((bc-q).length<r*1.78 for q in placed):continue                                  # berry centres, not pedicel tips
            placed.append(bc)
            if post:                                                                                # stripped: broken pedicels
                e=pk+d*L*rng2.uniform(.45,1.0);rg=K.tube_into(st,[pk,e],[.0012,.001],5)
                for v in rg[-1]:K.tag_uv(v,.5,.5,(0,0,1))
                continue
            K.tube_into(st,[pk,pk+d*L*.5+Vector((0,0,.002)),tipp],[.0012,.0011,.001],5,False)
            berry_into(br,tipp+d*r*.85,d,r,(rng2.random(),ripe,0))
    T=Matrix.Translation((bx,by,bed_h(bx,by)))@Matrix.Rotation(rot,4,'Z')@Matrix.Scale(s,4)
    for bm,m0 in zip((st,lv,br),marks):
        bm.verts.ensure_lookup_table();bmesh.ops.transform(bm,matrix=T,verts=bm.verts[m0:])
    return len(placed)

def build(post):
    rng=random.Random(3202);ctx=K.ctx;hf=pit_h if post else bed_h
    M={'leaf':mat_leaf_real('QX_Src_Chilu_Leaf'),'berry':mat_berry_real('QX_Src_Chilu_Berry'),
       'stem':mat_stem_real('QX_Src_Chilu_Stem'),'litter':mat_litter('QX_Src_Chilu_Leaf_Litter'),'skirt':O.mat_skirt('QX_Src_Chilu_Soil_Bed'),
       'moss':O.mat_moss_real('QX_Src_Chilu_Moss'),'rock':O.mat_rock_real('QX_Src_Chilu_Pebble',False,False),'grass':mat_grass_real('QX_Src_Chilu_Grass')}
    # --- soil bed in the shared ground language; after harvest the centre is dug into a pit
    sk=K.new_bm();O.skirt_into(sk,BED,.03,28,72,23)
    if post:
        for v in sk.verts:
            if math.hypot(v.co.x-PIT[0],v.co.y-PIT[1])<PIT[2]*1.7:v.co.z+=pit_h(v.co.x,v.co.y)-bed_h(v.co.x,v.co.y)
    K.link('Chilu_Soil_Bed',sk,[M['skirt']])
    pb=bmesh.new();n=0
    for k in range(300):
        if n>=16:break
        a=rng.uniform(0,TAU);s_=rng.uniform(.3,.94);x,y=BED[0]*s_*math.cos(a),BED[1]*s_*math.sin(a);sz=rng.uniform(.010,.026)*(1.7 if k<3 else 1)
        if any(math.hypot(x-px,y-py)<.10*ps+.03 for px,py,ps,*_ in PLANTS):continue
        b=O.hull_block((x,y,bed_h(x,y)+sz*.05),(sz*1.3,sz,sz*.6),800+k,24,.6,(0,0,rng.uniform(0,TAU)),rmin=.7);O.finish_block(b,sz*.12,max(bed_h(x,y)-.002,0));K.merge_into(pb,b);n+=1
    me=bpy.data.meshes.new('Chilu_Pebbles_Mesh');pb.to_mesh(me);pb.free();po=bpy.data.objects.new('Chilu_Pebbles',me);ctx.coll.objects.link(po);po.parent=ctx.root
    po.hide_render=True;po['qx_role']='game_low_poly';me.materials.append(M['rock']);ctx.objs.append(po)
    ph=O.remeshed(po,'Chilu_Pebbles_HP',ctx.coll,.003,1);ph.parent=ctx.root;hb,_=O.sculpt(ph,.15,.25,7,False,False);hb.free()
    ph.data.materials.append(M['rock']);ph['qx_role']='bake_source_high_poly';ctx.objs.append(ph)
    mo=K.new_bm();cush=[(-.20,-.20,.07,.05),(.14,-.24,.06,.04),(-.42,-.12,.06,.04),(.44,.12,.05,.04),(-.10,.27,.07,.04),(.27,.20,.05,.035)]
    for k,(x,y,rx,ry) in enumerate(cush):K.lumpy_into(mo,(x,y,bed_h(x,y)-.006),(rx,ry,.016),900+k,3,.25,2.5,k)
    K.flat_base(mo,0.0);mc=K.link('Chilu_Moss_Cushions',mo,[M['moss']])
    ca=mc.data.color_attributes.new('Ms','FLOAT_COLOR','POINT')
    for i,v in enumerate(mc.data.vertices):ca.data[i].color=(K.c01(v.co.z/.015),noise.noise(v.co*9)*.5+.5,0,1)
    lt=K.new_bm()                                                                                  # leaf litter
    for k in range(14):
        a=rng.uniform(0,TAU);s_=rng.uniform(.3,.9);x,y=BED[0]*s_*math.cos(a),BED[1]*s_*math.sin(a);az=rng.uniform(0,TAU);L=rng.uniform(.03,.055)
        p0=Vector((x,y,hf(x,y)+.002));d=Vector((math.cos(az),math.sin(az),0));pts=[p0+d*L*t/6+Vector((0,0,.004*math.sin(t/6*math.pi)+.003*(t/6)**2)) for t in range(7)]
        K.ribbon_into(lt,pts,[L*.20*math.sin(math.pi*min(.99,t/6*1.05))**.8+.0005 for t in range(7)],Vector((-d.y,d.x,0)),.45,rng.uniform(-.5,.5),5,(rng.random(),0,0))
    K.link('Chilu_Leaf_Litter',lt,[M['litter']],False)
    gr=K.new_bm();tufts=0                                                                          # sparse grass tufts, clear of the plants
    for k in range(80):
        if tufts>=17:break
        a=rng.uniform(0,TAU);s_=rng.uniform(.25,.92);x,y=BED[0]*s_*math.cos(a),BED[1]*s_*math.sin(a)
        if any(math.hypot(x-px,y-py)<.17*ps+.03 for px,py,ps,*_ in PLANTS):continue
        O.tuft_into(gr,rng,Vector((x,y,hf(x,y)-.004)),.04,.12+.03*(s_>.6));tufts+=1
    K.link('Chilu_Grass',gr,[M['grass']],False)
    # --- the plants (the main one is gone after harvest)
    st=K.new_bm();lv=K.new_bm();br=K.new_bm();berries=[]
    for k,cfg in enumerate(PLANTS):
        if post and k==0:continue
        berries.append(plant_into(st,lv,br,cfg,post,rng))
    if post:                                                                                        # torn leaflets dropped on the soil
        for x,y,a,L in [(.10,-.15,.4,.10),(-.13,-.11,2.2,.085),(.18,.09,4.0,.09),(-.06,.15,5.4,.07)]:
            d=Vector((math.cos(a),math.sin(a),0));b0=Vector((x,y,hf(x,y)+.003))-d*L*.5
            n0=len(lv.verts);leaflet(lv,b0,d,L,L*.38,.0,.004,.1,(rng.random(),.35,0),rng)
            for v in list(lv.verts)[n0:]:v.co.z=max(v.co.z,hf(v.co.x,v.co.y)+.0015)
    keep_st={v:ctx.vdata.pop(v) for v in st.verts if v in ctx.vdata};keep_br={v:ctx.vdata.pop(v) for v in br.verts if v in ctx.vdata}
    K.link('Chilu_Leaves',lv,[M['leaf']],True)
    ctx.vdata.update(keep_st)
    if post:                                                                                        # torn tap root left at the pit edge
        rt=[Vector((.07,.03,pit_h(.07,.03)+.004)),Vector((.045,.02,pit_h(.045,.02)+.008)),Vector((.02,.012,pit_h(.02,.012)+.003))]
        rg=K.tube_into(st,curve(rt,5),[.004,.0045,.0048,.0046,.0042,.004,.0036,.0032,.003,.0028,.0026],8)
        for v in rg[0]:K.tag_uv(v,.5,.5,(0,0,1))
    K.link('Chilu_Stem_Petioles',st,[M['stem']])
    ctx.vdata.update(keep_br)
    if len(br.verts):K.link('Chilu_Berries',br,[M['berry']])
    else:br.free()
    if post:                                                                                        # loosened soil clods thrown round the pit
        cl=bmesh.new()
        for k in range(26):
            a=rng.uniform(0,TAU);r=PIT[2]*rng.uniform(.95,1.6);x,y=PIT[0]+r*math.cos(a),PIT[1]+r*math.sin(a);sz=rng.uniform(.007,.018)
            b=O.hull_block((x,y,pit_h(x,y)+sz*.25),(sz*1.2,sz,sz*.7),1300+k,18,.5,(0,0,rng.uniform(0,TAU)),rmin=.6);K.merge_into(cl,b)
        me=bpy.data.meshes.new('Chilu_Soil_Clods_Mesh');cl.to_mesh(me);cl.free();co=bpy.data.objects.new('Chilu_Soil_Clods',me);ctx.coll.objects.link(co);co.parent=ctx.root
        me.materials.append(M['skirt']);ctx.objs.append(co)
        va=me.color_attributes.new('Var','FLOAT_COLOR','CORNER')
        for i in range(len(va.data)):va.data[i].color=(.3,0,0,1)                                    # damp dark soil zone of the skirt material
    ctx.extra.update({'reference':'ai_threeview_v002/R02b_QX_SpiritHerb_Chilu_post.png' if post else 'ai_threeview_v002/R02_QX_SpiritHerb_Chilu.png',
                      'berries_per_plant':str(berries),'grass_tufts':tufts,
                      'state_change':'post: main plant dug out (pit, thrown clods, torn root), side umbels stripped to broken pedicels, torn leaflets on the soil' if post else 'pre'})
