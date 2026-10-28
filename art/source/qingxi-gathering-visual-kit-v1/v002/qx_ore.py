"""QX_EmbeddedOre_Yumai v002: split jade-vein boulder (pre / post harvest).
v002 follows the reviewed AI three-view R03 / R03b (art/references/.../ai_threeview_v002): the whole piece is
turned so the cleft opens to the front (two blocks side by side, crystals fanning out of the cleft toward the
viewer), the right block is raised to about 0.8 of the left one, the stone is a paler granite with glowing jade
veins running along the beds across both blocks, and the crystals are taller (main about 1.3 x the block) and a
paler, milkier jade. Post: crystals snapped to stumps and the veins unlit.
v001 notes:
Primary: two faceted blocks split by a V cleft that widens upward; the back-left block is two
stacked strata tiers (ledge), the front-right block is a lower dipping slab, plus one fallen chunk.
Secondary: boolean chips on silhouette edges, thin crack grooves, shallow weathering pockets.
Crystals: one main, three secondaries fanned along the cleft, small crystals on the cleft lips.
Ground: height-to-zero blend skirt, graded talus fan at the front-right foot, moss clumps.
Origin: skirt centre at z=0 (bounds centre within a few mm); front -Y.
"""
import bpy,bmesh,math,random
from mathutils import Vector,Matrix,Euler,noise
from mathutils.bvhtree import BVHTree
import qx_kit as K

TAU=math.tau
A_CLEFT=-.6                                     # cleft plane normal heading (rad)
NC=Vector((math.cos(A_CLEFT),math.sin(A_CLEFT),0))
TC=Vector((-NC.y,NC.x,0))                       # direction along the cleft (towards back-right)
def half_gap(z):return .022+.085*K.c01(z/.85)

# ---------------------------------------------------------------- geometry helpers
def hull_block(center,size,seed,n=70,exp=.38,rot=(0,0,0),side=0,jag=.018,taper=0.0,lean=(0,0),rmin=.86):
    """Faceted block: convex hull of superellipsoid samples, near-coplanar facets merged.
    side=-1/+1 clamps samples to that side of the cleft plane (flat, slightly broken wall)."""
    rng=random.Random(seed);bm=bmesh.new();R=Euler(rot).to_matrix();c=Vector(center)
    for k in range(n):
        d=Vector((rng.gauss(0,1),rng.gauss(0,1),rng.gauss(0,1))).normalized()
        p=Vector([math.copysign(abs(x)**exp,x)*s for x,s in zip(d,size)])*rng.uniform(rmin,1.0)
        zn=K.c01(.5+.5*p.z/size[2]);p.x*=1-taper*zn;p.y*=1-taper*zn;p.x+=lean[0]*zn;p.y+=lean[1]*zn
        p=c+R@p
        if side:
            lim=half_gap(max(p.z,0))+jag*noise.noise(p*6+Vector((seed,0,0)))
            dd=p.dot(NC)
            if side<0 and dd>-lim:p-=NC*(dd+lim)
            if side>0 and dd<lim:p+=NC*(lim-dd)
        bm.verts.new(p)
    res=bmesh.ops.convex_hull(bm,input=bm.verts[:])
    bmesh.ops.delete(bm,geom=list({g for g in res['geom_interior']+res['geom_unused'] if isinstance(g,bmesh.types.BMVert)}),context='VERTS')
    bmesh.ops.dissolve_limit(bm,angle_limit=math.radians(9),verts=bm.verts[:],edges=bm.edges[:])
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces[:])        # outward normals: an inside-out cutter would union instead of cut
    return bm

def finish_block(bm,bevel=.022,base=0.0,min_angle=24):
    edges=[e for e in bm.edges if e.is_manifold and e.calc_face_angle(0)>math.radians(min_angle)]
    big=[e for e in edges if e.calc_face_angle(0)>math.radians(55)]
    if big:bmesh.ops.bevel(bm,geom=big,offset=bevel,segments=2,profile=.62,affect='EDGES',clamp_overlap=True)
    rest=[e for e in bm.edges if e.is_valid and e.is_manifold and math.radians(min_angle)<e.calc_face_angle(0)<=math.radians(55)]
    if rest:bmesh.ops.bevel(bm,geom=rest,offset=bevel*.4,segments=1,affect='EDGES',clamp_overlap=True)
    K.plane_cut(bm,(0,0,base),(0,0,1),True)
    bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>4])
    return bm

def to_object(name,bm,coll):
    me=bpy.data.meshes.new(name+'_Mesh');bm.to_mesh(me);bm.free();o=bpy.data.objects.new(name,me);coll.objects.link(o);return o

LOG=[]
def boolean(target,cutters,op='DIFFERENCE'):
    """Apply cutters one by one; a result that loses over 40 % of the volume-proxy (vertex bounds) or
    goes non-manifold is rejected and logged, so a degenerate cutter can never delete a block."""
    for c in cutters:
        before=len(target.data.vertices);lo=[min(v.co[i] for v in target.data.vertices) for i in range(3)];hi=[max(v.co[i] for v in target.data.vertices) for i in range(3)]
        md=target.modifiers.new('B','BOOLEAN');md.operation=op;md.solver='EXACT';md.object=c
        bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();me=bpy.data.meshes.new_from_object(target.evaluated_get(dg));target.modifiers.clear()
        ok=len(me.vertices)>=before*.6
        if ok:
            lo2=[min(v.co[i] for v in me.vertices) for i in range(3)];hi2=[max(v.co[i] for v in me.vertices) for i in range(3)]
            ok=all((hi2[i]-lo2[i])>(hi[i]-lo[i])*.8 for i in range(3))
            if ok and op=='DIFFERENCE':ok=all(lo2[i]>=lo[i]-.002 and hi2[i]<=hi[i]+.002 for i in range(3))   # a cut can never grow the block
        if ok:old=target.data;target.data=me;bpy.data.meshes.remove(old)
        else:bpy.data.meshes.remove(me);LOG.append((target.name,c.name,'rejected'))
        bpy.data.objects.remove(c)

def crystal_into(bm,base,d,r,L,rng,var_r,broken=False,tipf=.3):
    """Hexagonal prism with an off-centre six-facet termination; UV v runs base->tip.
    broken: tilted fracture cap with its own verts (Var.b=1 marks the fresh fracture)."""
    d=d.normalized();q=d.to_track_quat('Z','Y').to_matrix();ro=rng.uniform(0,TAU);rr=[r*(1+.16*rng.uniform(-1,1)) for _ in range(6)]
    def P(x,y,z):return base+q@Vector((x,y,z))
    def ring(z,k,vv):
        out=[]
        for i in range(6):
            a=ro+i*TAU/6;v=bm.verts.new(P(rr[i]*k*math.cos(a),rr[i]*k*math.sin(a),z));K.tag_uv(v,i/6,vv,(var_r,0,0));out.append(v)
        return out
    r0=ring(-.04,.88,0.0)
    if broken:
        h=min(L*rng.uniform(.14,.26),rng.uniform(.13,.19));sx,sy=rng.uniform(-.6,.6),rng.uniform(-.6,.6)
        top=[];cap=[]
        for i in range(6):
            a=ro+i*TAU/6;x,y=rr[i]*math.cos(a),rr[i]*math.sin(a);z=h+sx*x+sy*y+r*.35*rng.uniform(-1,1)
            v=bm.verts.new(P(x,y,z));K.tag_uv(v,i/6,z/L,(var_r,0,0));top.append(v)
            c=bm.verts.new(P(x,y,z));K.tag_uv(c,i/6,z/L,(var_r,0,1));cap.append(c)
        for i in range(6):bm.faces.new((r0[i],r0[(i+1)%6],top[(i+1)%6],top[i]))
        c0=bm.verts.new(P(r*rng.uniform(-.3,.3),r*rng.uniform(-.3,.3),h+r*rng.uniform(-.5,.4)));K.tag_uv(c0,.5,h/L,(var_r,0,1))
        for i in range(6):bm.faces.new((cap[i],cap[(i+1)%6],c0))
        bm.faces.new(list(reversed(r0)));return
    body=L*(1-tipf);r1=ring(body*.55,.97,body*.55/L);r2=ring(body,1.0,body/L)
    tip=bm.verts.new(P(r*rng.uniform(-.3,.3),r*rng.uniform(-.3,.3),L));K.tag_uv(tip,.5,1.0,(var_r,0,0))
    for a,b in ((r0,r1),(r1,r2)):
        for i in range(6):bm.faces.new((a[i],a[(i+1)%6],b[(i+1)%6],b[i]))
    for i in range(6):bm.faces.new((r2[i],r2[(i+1)%6],tip))
    bm.faces.new(list(reversed(r0)))

def skirt_into(bm,R=(1.18,1.0),h0=.07,rings=16,segs=72,seed=5):
    """Ground blend: height falls to exactly 0 at the rim. Var.r = normalised radius."""
    centre=bm.verts.new((0,0,h0));K.tag_uv(centre,.5,.5,(0,0,0));rows=[]
    for j in range(1,rings+1):
        s=j/rings;row=[]
        for i in range(segs):
            a=i*TAU/segs;w=1+.07*noise.noise(Vector((math.cos(a)*1.6,math.sin(a)*1.6,seed)))
            x,y=R[0]*s*w*math.cos(a),R[1]*s*w*math.sin(a);z=-.012 if j==rings else h0*(1-s)**1.6-.012*s**6*(1+.35*noise.noise(Vector((x*3,y*3,seed))))
            v=bm.verts.new((x,y,z));K.tag_uv(v,.5+.5*s*math.cos(a),.5+.5*s*math.sin(a),(s,0,0));row.append(v)
        rows.append(row)
    for i in range(segs):bm.faces.new((centre,rows[0][i],rows[0][(i+1)%segs]))
    for a,b in zip(rows,rows[1:]):
        for i in range(segs):bm.faces.new((a[i],b[i],b[(i+1)%segs],a[(i+1)%segs]))

def skirt_height(x,y,R=(1.18,1.0),h0=.07):
    s=min(1,math.hypot(x/R[0],y/R[1]));return h0*(1-s)**1.6

# ---------------------------------------------------------------- materials
def ao(nt,dist,inside=False):
    return K.node(nt,'ShaderNodeAmbientOcclusion',{'Distance':dist},inside=inside,only_local=True,samples=16).outputs['AO']

def mat_rock(name,post):
    """Clean layered rock: facet tint, height gradient, crisp edge wear, cavity, broken strata lines,
    sparse painted cracks, weathered brown foot, inset moss caps, cleft mineral coat + veins, scar."""
    m,nt,bs=K.pbr(name,True,.8,.42);ob=K.coord(nt);x,y,z=K.sep(nt,ob);geo=K.node(nt,'ShaderNodeNewGeometry');N=geo.outputs['Normal'];nz=K.sep(nt,N)[2]
    mr,mx,ad,mrng,sub=K.mul,K.mix,K.add,K.mrange,lambda a,b:K.math_(nt,'SUBTRACT',a,b)
    edge=mrng(nt,ao(nt,.06,True),.80,.52);cav=mrng(nt,ao(nt,.25),.9,.45)
    facet=K.node(nt,'ShaderNodeVectorMath',{0:N,1:(.55,-.65,.5)},operation='DOT_PRODUCT').outputs['Value']
    mid=K.noise_t(nt,ob,3.2,3,.45);fine=K.noise_t(nt,ob,34,4)
    col=K.ramp(nt,mrng(nt,ad(nt,z,mr(nt,mid,.12)),.0,1.05),[(0,(.070,.078,.088)),(.5,(.150,.165,.180)),(1,(.225,.240,.252))])
    col=mx(nt,mr(nt,mrng(nt,facet,-.4,.6),.28),col,(.20,.205,.20))        # light-facing facets warmer and lighter
    col=mx(nt,mr(nt,mrng(nt,K.noise_t(nt,ob,.8,2),.5,.75),.3),col,(.13,.13,.125))
    col=mx(nt,mr(nt,fine,.07),col,(.04,.045,.05))
    # strata: thin dark lines with a light lip, broken up so they never read as stripes
    tilt=ad(nt,z,ad(nt,mr(nt,x,.42),mr(nt,y,-.22)))
    saw=K.wave_t(nt,K.comb(nt,0,0,tilt),1.7,'Z',1.4,1,'SAW');brk=mrng(nt,K.noise_t(nt,ob,1.3,2),.5,.6)
    sline=mr(nt,mrng(nt,saw,.93,.985),brk);slip=mr(nt,mr(nt,mrng(nt,saw,.0,.04),mrng(nt,saw,.09,.04)),brk)
    col=mx(nt,mr(nt,slip,.45),col,(.26,.27,.275));col=mx(nt,mr(nt,sline,.8),col,(.035,.04,.045))
    # painted cracks: sparse, warped, tapering
    warp=K.node(nt,'ShaderNodeVectorMath',{0:ob,1:K.scaled(nt,K.node(nt,'ShaderNodeTexNoise',{'Vector':ob,'Scale':2.5,'Detail':3}).outputs['Color'],(.35,.35,.35))},operation='ADD').outputs[0]
    crack=mr(nt,mrng(nt,K.voronoi_t(nt,warp,1.5,'DISTANCE_TO_EDGE'),.009,.002),mrng(nt,K.noise_t(nt,ob,1.4,2),.58,.64))
    col=mx(nt,mr(nt,crack,.85),col,(.02,.022,.026))
    # weathered foot: brown dirt rising from the ground with vertical rain streaks
    wz=mrng(nt,ad(nt,z,mr(nt,K.noise_t(nt,ob,2.5),.14)),.30,.06)
    streak=K.noise_t(nt,K.scaled(nt,ob,(20,20,1.1)),3,3)
    col=mx(nt,mr(nt,wz,.75),col,K.ramp(nt,streak,[(0,(.055,.048,.038)),(1,(.10,.088,.07))]))
    rain=mr(nt,mrng(nt,streak,.62,.75),mrng(nt,z,.2,.6));col=mx(nt,mr(nt,rain,.25),col,(.06,.065,.07))
    col=mx(nt,mr(nt,edge,.9),col,(.42,.44,.45))
    col=mx(nt,mr(nt,cav,.9),col,(.022,.026,.03))
    lich=mr(nt,mr(nt,mrng(nt,K.voronoi_t(nt,ob,16),.10,.07),mrng(nt,K.noise_t(nt,ob,2.3),.58,.64)),mrng(nt,wz,.5,0))
    col=mx(nt,mr(nt,lich,.7),col,(.33,.35,.30))
    # moss caps: upward faces only, inset from edges, light fringe = soft thickness
    mv=ad(nt,nz,mr(nt,sub(K.noise_t(nt,ob,1.7,4),.5),1.0))
    inset=mrng(nt,edge,.3,.05)
    moss=mr(nt,mr(nt,mrng(nt,mv,.64,.70),inset),mrng(nt,z,.22,.38))
    fringe=mr(nt,mr(nt,mrng(nt,mv,.58,.64),mrng(nt,mv,.71,.65)),mrng(nt,z,.22,.38))
    mcol=K.ramp(nt,ad(nt,mr(nt,K.noise_t(nt,ob,28,4),.55),mr(nt,K.noise_t(nt,ob,4,2),.45)),[(0,(.050,.075,.030)),(.55,(.092,.122,.050)),(1,(.14,.168,.072))])
    col=mx(nt,mr(nt,fringe,.7),col,(.14,.16,.08));col=mx(nt,moss,col,mcol)
    # cleft
    dist=K.math_(nt,'ABSOLUTE',K.node(nt,'ShaderNodeVectorMath',{0:ob,1:tuple(NC)},operation='DOT_PRODUCT').outputs['Value'])
    facing=mrng(nt,K.math_(nt,'ABSOLUTE',K.node(nt,'ShaderNodeVectorMath',{0:N,1:tuple(NC)},operation='DOT_PRODUCT').outputs['Value']),.55,.8)
    cl=mr(nt,mrng(nt,dist,.15,.07),facing)
    col=mx(nt,mr(nt,cl,.85),col,(.02,.05,.058))
    warp2=K.node(nt,'ShaderNodeVectorMath',{0:K.scaled(nt,ob,(1,1,.7)),1:K.scaled(nt,K.node(nt,'ShaderNodeTexNoise',{'Vector':ob,'Scale':3,'Detail':2}).outputs['Color'],(.25,.25,.25))},operation='ADD').outputs[0]
    vein=mr(nt,mr(nt,mrng(nt,K.voronoi_t(nt,warp2,4.2,'DISTANCE_TO_EDGE'),.012,.003),cl),mrng(nt,K.noise_t(nt,ob,2.2,2),.42,.55))
    col=mx(nt,vein,col,(.16,.50,.48) if not post else (.08,.13,.13))
    hgt=ad(nt,ad(nt,mr(nt,sline,-.8),mr(nt,crack,-1.2)),ad(nt,mr(nt,mid,.35),mr(nt,fine,.3)))
    if post:
        d=K.node(nt,'ShaderNodeVectorMath',{0:ob,1:(0,0,.36)},operation='DISTANCE').outputs['Value']
        sc=mr(nt,mrng(nt,ad(nt,d,mr(nt,K.noise_t(nt,ob,8),.12)),.44,.34),mrng(nt,dist,.28,.14))
        col=mx(nt,sc,col,K.ramp(nt,K.noise_t(nt,ob,40),[(0,(.27,.27,.26)),(1,(.40,.40,.385))]))
        hgt=ad(nt,hgt,mr(nt,sc,mr(nt,mrng(nt,K.voronoi_t(nt,ob,30),.12,.03),-1)))
    else:
        nt.links.new(K.ramp(nt,vein,[(0,(0,0,0)),(1,(.16,.85,.74))]),bs.inputs['Emission Color']);bs.inputs['Emission Strength'].default_value=1.6
    rough=mx(nt,moss,mx(nt,edge,(.84,.84,.84),(.66,.66,.66)),(.97,.97,.97))
    K.finish(nt,bs,col,rough,hgt,.45,.01);return m

# ---------------------------------------------------------------- semi-real high-poly pass
def sm01(a,b,x):
    t=K.c01((x-a)/(b-a));return t*t*(3-2*t)
def cell01(p):return noise.cell(p)*.5+.5

def rock_relief(p,n,scale=1.0,amp=1.0,seed=0):
    """Displacement along the normal (m) and masks for a fractured, bedded stone surface.
    flakes: each voronoi cell is a slightly tilted plane sunk by its own depth (stepped conchoidal breaks);
    beds: tilted layers weather back by different amounts, with grooves at the bed joints (walls only);
    cracks: sparse warped cell edges cut 2 cm deep; grain: fine fractal."""
    o=Vector((seed*7.31,seed*3.17,seed*1.93));q=p/scale+o;qw=q+noise.noise_vector(q*2.0)*.07
    wall=1-abs(n.z)
    fs=qw*3.4;ds,ps=noise.voronoi(fs,distance_metric='DISTANCE',exponent=2.5);c=ps[0]
    r1=cell01(c);tilt=Vector((cell01(c+Vector((3.1,0,0)))-.5,cell01(c+Vector((0,5.7,0)))-.5,cell01(c+Vector((0,0,2.3)))-.5))
    flake=-(.018*r1+.022*(fs-c).dot(tilt))*sm01(.30,.55,noise.noise(q*1.3)*.5+.5)
    fresh=1-sm01(0,.06,ds[1]-ds[0])
    t=(p.z+p.x*.42-p.y*.22)/scale*6.5+noise.noise(q*1.6)*.35;bed=math.floor(t);f=t-bed;br0=cell01(Vector(((bed-1)*1.37,seed,.5)));br1=cell01(Vector((bed*1.37,seed,.5)));br=br0+(br1-br0)*sm01(0,.22,f)
    groove=1-sm01(0,.15,min(f,1-f));bmask=sm01(.25,.6,wall)*sm01(.32,.55,noise.noise(q*.9+Vector((0,0,9)))*.5+.5)
    strata=(-.013*br-.011*groove)*bmask
    ds2,_=noise.voronoi(q*1.45+noise.noise_vector(q*3.1)*.12,distance_metric='DISTANCE',exponent=2.5)
    crack=(1-sm01(0,.05,ds2[1]-ds2[0]))*sm01(.47,.58,noise.noise(q*1.1+Vector((4,0,0)))*.5+.5)
    grain=noise.fractal(q*16,1.0,2.0,4)*.0018+noise.noise(q*55)*.0006
    dp,_=noise.voronoi(q*7.5,distance_metric='DISTANCE',exponent=2.5)
    pits=(1-sm01(.0,.28,dp[0]))*sm01(.5,.62,noise.noise(q*2.2+Vector((1,7,3)))*.5+.5)*sm01(.4,.8,n.z)
    grain-=.007*pits
    db,pb=noise.voronoi(q*1.8+noise.noise_vector(q*1.2)*.15,distance_metric='DISTANCE',exponent=2.5);cb=pb[0]
    grain-=(.022*cell01(cb+Vector((9,1,4)))+.03*(q*1.8-cb).dot(Vector((cell01(cb)-.5,cell01(cb+Vector((2,8,0)))-.5,0))))*sm01(.45,.75,n.z)
    grain+=.032*noise.noise(q*1.4+Vector((5,5,5)))+.008*noise.noise(q*4.2+Vector((1,2,9)))   # broad undulation
    return (flake+strata-.022*crack+grain)*amp,crack,groove*bmask,r1,br,fresh

def remeshed(src,name,coll,voxel,smooth=2):
    o=bpy.data.objects.new(name,src.data.copy());coll.objects.link(o)
    md=o.modifiers.new('R','REMESH');md.mode='VOXEL';md.voxel_size=voxel;md.adaptivity=0.0
    if smooth:sm=o.modifiers.new('S','SMOOTH');sm.factor=.5;sm.iterations=smooth
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();me=bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    o.modifiers.clear();old=o.data;o.data=me;bpy.data.meshes.remove(old);return o

def sculpt(o,scale=1.0,amp=1.0,seed=0,cleft=False,moss=True):
    """Displace a remeshed object in place; writes point colours Rk (crack, groove, flake id) and
    Rk2 (bed id, moss mask, fresh flake edge). Returns the bmesh (caller frees) for the moss shell."""
    bm=bmesh.new();bm.from_mesh(o.data);bm.normal_update()
    rk=bm.verts.layers.float_color.new('Rk');rk2=bm.verts.layers.float_color.new('Rk2')
    new=[]
    for v in bm.verts:
        p=v.co.copy();n=v.normal.copy();d,cr,gr,fl,br,fe=rock_relief(p,n,scale,amp,seed)
        if cleft:d*=.35+.65*sm01(.05,.16,abs(p.dot(NC)))           # cleft walls stay a cleaner mineral face
        new.append(p+n*d*sm01(.0,.05,p.z));v[rk]=(cr,gr,fl,1);v[rk2]=(br,0,fe,1)
    for v,p in zip(bm.verts,new):v.co=p
    soft=[v for v in bm.verts if v[rk][0]>.08 or v[rk][1]>.5]          # relax crack / joint walls (no voxel teeth)
    for _ in range(2):bmesh.ops.smooth_vert(bm,verts=soft,factor=.5,use_axis_x=True,use_axis_y=True,use_axis_z=True)
    bm.normal_update()
    if moss:
        for v in bm.verts:
            p=v.co;m=sm01(.46,.80,v.normal.z+noise.noise(p*1.7+Vector((2,2,2)))*.22)*sm01(.22,.36,p.z)
            m*=sm01(.26,.50,noise.noise(p*1.9)*.5+.5+.30*(p.y-p.x*.5))
            c0=v[rk];m*=.75+.25*sm01(.0,.35,c0[0]+c0[1]+noise.noise(p*2.6)*.25)
            m=sm01(.22,.62,m+.22*noise.noise(p*11)+.08*noise.noise(p*29))
            if cleft:m*=sm01(.10,.20,abs(p.dot(NC)))
            c=v[rk2];v[rk2]=(c[0],m,c[2],1)
    for f in bm.faces:f.smooth=True
    bm.to_mesh(o.data);return bm,rk2

def moss_shell(bm_src,layer,name,coll,thick=.024):
    """Moss as real thickness: faces under the moss mask lifted along the normal into soft cushions that
    thin to the rock surface at their edges. Point colour Ms = mask (for edge fade and tip colour)."""
    bm=bmesh.new();ms=bm.verts.layers.float_color.new('Ms');vmap={}
    for f in bm_src.faces:
        if min(v[layer][1] for v in f.verts)<=.30:continue
        vs=[]
        for v in f.verts:
            nv=vmap.get(v)
            if nv is None:
                m=v[layer][1];h=thick*sm01(.30,1,m)**1.3*(.35+1.3*(noise.noise(v.co*24)*.5+.5)*(.7+.3*noise.noise(v.co*70)))+.0012
                nv=bm.verts.new(v.co+v.normal*h);nv[ms]=(m,noise.noise(v.co*9)*.5+.5,0,1);vmap[v]=nv
            vs.append(nv)
        try:bm.faces.new(vs)
        except ValueError:pass
    for f in bm.faces:f.smooth=True
    me=bpy.data.meshes.new(name+'_Mesh');bm.to_mesh(me);bm.free();o=bpy.data.objects.new(name,me);coll.objects.link(o);return o

def mat_rock_real(name,post,seam=True,tone=None):
    """Semi-real stone driven by the sculpt masks: cool grey beds with per-bed / per-flake tone shifts,
    mineral grains, worn convex edges and fresh flake edges, dusty cavities and joints, dark cracks,
    rain streaks, damp foot, crustose lichen, dark under-moss, jade mineral coat in the cleft."""
    m,nt,bs=K.pbr(name,True,.86,.45);ob=K.coord(nt);x,y,z=K.sep(nt,ob);geo=K.node(nt,'ShaderNodeNewGeometry');N=geo.outputs['Normal'];nz=K.sep(nt,N)[2]
    mr,mx,ad,mrng=K.mul,K.mix,K.add,K.mrange
    cr,gr,fl=K.attr(nt,'Rk');br,mo,fe=K.attr(nt,'Rk2');pt=geo.outputs['Pointiness']
    convex=mrng(nt,pt,.505,.56);concave=mrng(nt,pt,.495,.44);cav=mrng(nt,ao(nt,.10),.95,.55)
    col=K.ramp(nt,br,tone or [(0,(.125,.131,.137)),(.45,(.172,.178,.184)),(.75,(.168,.162,.150)),(1,(.212,.215,.217))])
    col=mx(nt,mr(nt,fl,.22),col,(.205,.21,.21));col=mx(nt,mr(nt,K.math_(nt,'SUBTRACT',1,fl),.18),col,(.10,.105,.11))
    col=mx(nt,mr(nt,mrng(nt,K.noise_t(nt,ob,.7,2),.45,.75),.35),col,(.17,.158,.140))     # warm iron-stained patches
    grains=K.voronoi_t(nt,ob,240,'F1','Color');gsel=K.sep(nt,grains)[0];gd=mrng(nt,K.voronoi_t(nt,ob,240),.42,.22)
    col=mx(nt,mr(nt,mr(nt,gd,.6),mrng(nt,gsel,.72,.76)),col,(.07,.074,.078))                        # dark mafic grains
    col=mx(nt,mr(nt,mr(nt,gd,.5),mrng(nt,gsel,.975,.985)),col,(.28,.28,.27))                         # sparse quartz flecks
    col=mx(nt,mr(nt,K.noise_t(nt,ob,30,5),.12),col,(.07,.075,.08))
    col=mx(nt,mr(nt,convex,.45),col,(.27,.275,.27));col=mx(nt,mr(nt,fe,.08),col,(.25,.255,.255))
    col=mx(nt,mr(nt,mrng(nt,K.noise_t(nt,ob,1.6,4),.52,.8),.45),col,(.085,.087,.084))     # grime mottling
    col=mx(nt,mr(nt,mrng(nt,K.noise_t(nt,ob,2.4,3),.6,.72),.35),col,(.17,.138,.10))      # ochre stains
    streak=K.noise_t(nt,K.scaled(nt,ob,(22,22,1.2)),3,3)
    col=mx(nt,mr(nt,mr(nt,mrng(nt,streak,.55,.72),mrng(nt,nz,.6,.2)),.45),col,(.055,.058,.06))
    col=mx(nt,mr(nt,concave,.6),col,(.075,.066,.052));col=mx(nt,mr(nt,cav,.75),col,(.035,.034,.032))
    col=mx(nt,mr(nt,gr,.55),col,(.072,.068,.060));col=mx(nt,mr(nt,cr,.92),col,(.016,.016,.018))
    wz=mrng(nt,ad(nt,z,mr(nt,K.noise_t(nt,ob,3),.06)),.17,.03)
    col=mx(nt,mr(nt,wz,.72),col,(.045,.040,.032))
    lich=mr(nt,mrng(nt,K.noise_t(nt,ob,3.5,6,.62),.58,.64),mr(nt,mrng(nt,z,.12,.3),mrng(nt,mo,.1,0)))
    lc=K.ramp(nt,K.noise_t(nt,ob,40,4),[(0,(.19,.21,.16)),(1,(.30,.32,.25))])
    col=mx(nt,mr(nt,lich,.8),col,lc)
    ylich=mr(nt,mrng(nt,K.noise_t(nt,K.coord(nt),5.1,6,.6),.67,.71),mrng(nt,nz,.2,.6))
    col=mx(nt,mr(nt,ylich,.75),col,(.26,.23,.09))
    dots=mr(nt,mrng(nt,K.voronoi_t(nt,ob,45),.12,.06),mr(nt,mrng(nt,nz,.4,.8),mrng(nt,K.noise_t(nt,ob,3.3),.55,.6)))
    col=mx(nt,mr(nt,dots,.8),col,(.03,.032,.028))
    mf=K.add(nt,mo,mr(nt,K.math_(nt,'SUBTRACT',K.noise_t(nt,ob,55,4),.5),.30))
    col=mx(nt,mrng(nt,mf,.0,.08),col,(.034,.038,.02))                                    # damp rim
    mcol=K.ramp(nt,K.add(nt,mr(nt,K.noise_t(nt,ob,22,4),.6),mr(nt,K.noise_t(nt,ob,420,3),.4)),[(0,(.030,.048,.014)),(.5,(.062,.090,.026)),(.8,(.105,.128,.036)),(1,(.15,.15,.05))])
    mshade=mrng(nt,mf,.08,.30);col=mx(nt,mshade,col,mcol)
    dist=K.math_(nt,'ABSOLUTE',K.node(nt,'ShaderNodeVectorMath',{0:ob,1:tuple(NC)},operation='DOT_PRODUCT').outputs['Value'])
    facing=mrng(nt,K.math_(nt,'ABSOLUTE',K.node(nt,'ShaderNodeVectorMath',{0:N,1:tuple(NC)},operation='DOT_PRODUCT').outputs['Value']),.5,.8)
    cl=mr(nt,mr(nt,mr(nt,mrng(nt,dist,.16,.07),facing),mrng(nt,z,.08,.2)),1.0 if seam else 0.0)   # seam=False: plain stone, no jade cleft
    ccol=K.ramp(nt,K.noise_t(nt,ob,9,4),[(0,(.018,.050,.046)),(1,(.045,.105,.092))])
    col=mx(nt,mr(nt,cl,.9),col,ccol)
    warp2=K.node(nt,'ShaderNodeVectorMath',{0:K.scaled(nt,ob,(1,1,.7)),1:K.scaled(nt,K.node(nt,'ShaderNodeTexNoise',{'Vector':ob,'Scale':3,'Detail':2}).outputs['Color'],(.25,.25,.25))},operation='ADD').outputs[0]
    vein=mr(nt,mr(nt,mrng(nt,K.voronoi_t(nt,warp2,4.2,'DISTANCE_TO_EDGE'),.008,.002),cl),mrng(nt,K.noise_t(nt,ob,2.2,2),.42,.55))
    bedv=K.comb(nt,x,y,ad(nt,ad(nt,z,mr(nt,x,.16)),mr(nt,y,-.10)))                                # gently dipping bed planes
    bands=K.wave_t(nt,bedv,1.15,'Z',3.0,2)
    sv=mr(nt,mr(nt,mr(nt,mrng(nt,bands,.990,.9985),mrng(nt,nz,.78,.45)),mr(nt,mrng(nt,K.noise_t(nt,ob,1.6,3),.44,.52),mrng(nt,z,.10,.18))),1.0 if seam else 0.0)
    vein=K.math_(nt,'MAXIMUM',vein,sv)
    col=mx(nt,vein,col,(.26,.62,.52) if not post else (.10,.15,.14))
    sparkle=mr(nt,mrng(nt,K.voronoi_t(nt,ob,420),.12,.04),cl)
    hgt=ad(nt,ad(nt,mr(nt,K.noise_t(nt,ob,90,5),.6),mr(nt,gd,.25)),ad(nt,mr(nt,lich,.5),mr(nt,cr,-.6)))
    rough=mx(nt,wz,mx(nt,cl,ad(nt,.80,mr(nt,K.noise_t(nt,ob,14,3),.14)),mx(nt,sparkle,(.42,.42,.42),(.18,.18,.18))),(.62,.62,.62))
    if post:
        d=K.node(nt,'ShaderNodeVectorMath',{0:ob,1:(0,0,.36)},operation='DISTANCE').outputs['Value']
        sc=mr(nt,mrng(nt,ad(nt,d,mr(nt,K.noise_t(nt,ob,8),.10)),.40,.30),mrng(nt,dist,.28,.12))
        col=mx(nt,sc,col,K.ramp(nt,K.noise_t(nt,ob,45,4),[(0,(.25,.255,.25)),(1,(.36,.365,.355))]))
        hgt=ad(nt,hgt,mr(nt,sc,mr(nt,mrng(nt,K.voronoi_t(nt,ob,28),.14,.03),-1.2)))
    else:
        nt.links.new(K.ramp(nt,vein,[(0,(0,0,0)),(1,(.14,.80,.62))]),bs.inputs['Emission Color']);bs.inputs['Emission Strength'].default_value=1.1
    rough=mx(nt,mshade,rough,(.95,.95,.95));hgt=ad(nt,hgt,mr(nt,mshade,mr(nt,K.noise_t(nt,ob,420,3),.8)))
    K.finish(nt,bs,col,rough,hgt,.32,.003);return m

def mat_moss_real(name):
    """Cushion moss: olive-to-yellow-green tips, darker in the folds, fibrous micro bump, soft sheen."""
    m,nt,bs=K.pbr(name,True,.92,.25);ob=K.coord(nt);ms,mv,_=K.attr(nt,'Ms');cav=K.mrange(nt,ao(nt,.03),.95,.5)
    fib=K.noise_t(nt,ob,420,3);clump=K.noise_t(nt,ob,22,4)
    col=K.ramp(nt,K.add(nt,K.mul(nt,clump,.6),K.mul(nt,mv,.4)),[(0,(.030,.048,.014)),(.5,(.062,.090,.026)),(.8,(.105,.128,.036)),(1,(.15,.15,.05))])
    col=K.mix(nt,K.mul(nt,K.mrange(nt,fib,.55,.75),.35),col,(.17,.19,.07))                       # sunlit tips
    col=K.mix(nt,K.mul(nt,K.mrange(nt,ms,.25,.0),.55),col,(.07,.066,.04))                          # thin, browner edges
    col=K.mix(nt,K.mul(nt,cav,.7),col,(.010,.016,.006))
    b=bs.inputs.get('Sheen Weight')
    if b:b.default_value=.35;bs.inputs['Sheen Tint'].default_value=(.75,.85,.55,1)
    K.finish(nt,bs,col,None,K.add(nt,K.mul(nt,fib,.6),K.mul(nt,clump,.4)),.55,.004);return m

def mat_crystal_real(name,glow):
    """Translucent jade quartz: milky frosted root, clearer body, horizontal growth striations,
    inner cloudy glow (pre only); fracture caps frosted. v (UV) runs base->tip."""
    m,nt,bs=K.pbr(name,True,.05,.5);u,v=K.uv(nt);r,g,b=K.attr(nt);ob=K.coord(nt)
    bs.inputs['IOR'].default_value=1.6
    frac=K.mrange(nt,b,.4,.6);cloud=K.noise_t(nt,ob,7,4)
    t=K.add(nt,v,K.mul(nt,K.math_(nt,'SUBTRACT',r,.5),.15))
    stops=[(0,(.20,.36,.30)),(.35,(.44,.70,.58)),(1,(.74,.92,.82))] if glow else [(0,(.09,.14,.13)),(.5,(.17,.25,.23)),(1,(.28,.36,.34))]
    col=K.mix(nt,frac,K.ramp(nt,t,stops),(.62,.78,.75) if glow else (.26,.34,.33))
    trans=K.mix(nt,frac,K.mrange(nt,t,.0,.55,.35,.92) if glow else K.mrange(nt,K.add(nt,t,K.mul(nt,cloud,.3)),0,1.2,.55,.78),(.25,.25,.25) if not glow else (.40,.40,.40))
    K._set(nt,bs.inputs['Transmission Weight'],trans)
    stri=K.wave_t(nt,K.comb(nt,0,0,K.mul(nt,v,1.0)),38,'Z',3,2)
    rough=K.mix(nt,frac,K.add(nt,K.mrange(nt,t,0,.6,.18,.02) if glow else K.mrange(nt,t,0,1,.16,.10),K.mul(nt,K.mrange(nt,stri,.7,1),.06)),(.15,.15,.15) if glow else (.06,.06,.06))
    if glow:
        nt.links.new(K.ramp(nt,K.mul(nt,K.mul(nt,t,K.mrange(nt,cloud,.35,.7,.4,1)),K.math_(nt,'SUBTRACT',1,frac)),[(0,(0,0,0)),(.4,(.03,.12,.08)),(1,(.30,.85,.62))]),bs.inputs['Emission Color'])
        bs.inputs['Emission Strength'].default_value=.45
    ripple=K.wave_t(nt,K.add(nt,ob,K.mul(nt,cloud,.02)),55,'Z',6,3)                           # conchoidal ripples on breaks
    K.finish(nt,bs,col,rough,K.add(nt,K.add(nt,K.mul(nt,stri,.3),K.mul(nt,K.noise_t(nt,ob,60,2),.7)),K.mul(nt,frac,K.mul(nt,ripple,2.0))),.02,.002);return m

def tuft_into(bm,rng,c,hmin=.04,hmax=.12):
    for s in range(rng.randint(7,13)):
        az=rng.uniform(0,TAU);pts,h=K.arch(c,az,rng.uniform(hmin,hmax),rng.uniform(.10,.40),rng.uniform(.6,1.4),5,1.8)
        K.ribbon_into(bm,pts,[.0026*(1-j/5)**.6+.0004 for j in range(6)],Vector((-h.y,h.x,0)),.25,0,3,(rng.random(),rng.choice((0,0,.3,1)),0))

def mat_gravel(name):
    m,nt,bs=K.pbr(name,True,.85,.4);ob=K.coord(nt);nz=K.normal_z(nt);r,g,b=K.attr(nt)
    edge=K.mrange(nt,ao(nt,.025,True),.9,.55);cav=K.mrange(nt,ao(nt,.12),.92,.5)
    col=K.ramp(nt,K.noise_t(nt,ob,4,3),[(0,(.06,.064,.07)),(1,(.12,.125,.13))])
    col=K.mix(nt,K.mul(nt,K.mrange(nt,K.noise_t(nt,ob,1.5),.45,.7),.4),col,(.15,.14,.12))
    col=K.mix(nt,K.mul(nt,edge,.6),col,(.24,.25,.26));col=K.mix(nt,K.mul(nt,cav,.8),col,(.03,.03,.032))
    moss=K.mul(nt,K.mrange(nt,nz,.7,.85),K.mrange(nt,K.noise_t(nt,ob,3),.55,.6));col=K.mix(nt,moss,col,(.05,.08,.03))
    K.finish(nt,bs,col,None,K.noise_t(nt,ob,25,4),.3,.004);return m

def mat_skirt(name):
    """Zones by normalised radius (Var.r): damp dark soil at the rock foot, gravelly soil, moss patches, neutral rim."""
    m,nt,bs=K.pbr(name,True,.9,.3);ob=K.coord(nt);s,g,b=K.attr(nt)
    peb=K.mrange(nt,K.voronoi_t(nt,ob,38),.17,.09)
    soil=K.ramp(nt,K.noise_t(nt,ob,7,4),[(0,(.045,.035,.025)),(1,(.085,.068,.048))])
    soil=K.mix(nt,K.mul(nt,peb,.7),soil,(.15,.145,.135))
    damp=K.mrange(nt,s,.62,.42);col=K.mix(nt,K.mul(nt,damp,.85),soil,(.022,.018,.014))
    mp=K.mul(nt,K.mrange(nt,K.add(nt,K.noise_t(nt,ob,1.6,3),K.mul(nt,s,.15)),.56,.6),K.mrange(nt,s,.45,.6))
    col=K.mix(nt,mp,col,K.ramp(nt,K.noise_t(nt,ob,24,4),[(0,(.035,.058,.024)),(1,(.07,.098,.042))]))
    col=K.mix(nt,K.mrange(nt,s,.74,.97),col,(.058,.066,.04))
    K.finish(nt,bs,col,None,K.add(nt,K.mul(nt,peb,.8),K.noise_t(nt,ob,20)),.35,.006);return m

def mat_moss(name):
    m,nt,bs=K.pbr(name,True,.97,.2);ob=K.coord(nt);n=K.noise_t(nt,ob,60,5);cav=K.mrange(nt,ao(nt,.08),.92,.5)
    col=K.ramp(nt,K.add(nt,K.mul(nt,n,.5),K.mul(nt,K.noise_t(nt,ob,6),.5)),[(0,(.03,.05,.02)),(1,(.085,.115,.048))])
    K.finish(nt,bs,K.mix(nt,K.mul(nt,cav,.7),col,(.012,.02,.01)),None,n,.5,.004);return m

def mat_crystal(name,glow):
    m,nt,bs=K.pbr(name,True,.10,.7,0,(.2,.9,.8),1.0 if glow else 0.0);u,v=K.uv(nt);r,g,b=K.attr(nt)
    edge=K.mrange(nt,ao(nt,.015,True),.9,.5)
    facet=K.node(nt,'ShaderNodeLayerWeight',{'Blend':.35}).outputs['Facing']   # per-facet value change
    t=K.add(nt,v,K.mul(nt,K.math_(nt,'SUBTRACT',r,.5),.2))
    stops=[(0,(.006,.045,.05)),(.35,(.025,.20,.22)),(.75,(.10,.52,.50)),(1,(.40,.88,.82))] if glow else [(0,(.015,.04,.045)),(.6,(.05,.11,.115)),(1,(.13,.20,.20))]
    col=K.ramp(nt,t,stops);col=K.mix(nt,K.mul(nt,facet,.45),col,(.004,.03,.04) if glow else (.01,.02,.02))
    col=K.mix(nt,K.mul(nt,edge,.55),col,(.55,.95,.90) if glow else (.25,.32,.31))
    frac=K.mrange(nt,b,.4,.6);col=K.mix(nt,frac,col,(.30,.45,.43) if glow else (.30,.36,.35))
    if glow:nt.links.new(K.ramp(nt,K.mul(nt,t,K.math_(nt,'SUBTRACT',1,frac)),[(0,(0,0,0)),(.45,(.01,.12,.12)),(1,(.22,.85,.75))]),bs.inputs['Emission Color'])
    K.finish(nt,bs,col,K.mix(nt,frac,(.10,.10,.10),(.6,.6,.6)),K.noise_t(nt,K.coord(nt),40,2),.04,.002);return m

# ---------------------------------------------------------------- build
def build(post):
    rng=random.Random(4301 if not post else 4301);ctx=K.ctx;coll=ctx.coll
    M={'rock':mat_rock_real('QX_Src_Ore_Rock_'+('post' if post else 'pre'),post),'gravel':mat_gravel('QX_Src_Ore_Gravel'),
       'skirt':mat_skirt('QX_Src_Ore_Ground_Blend'),'moss':mat_moss_real('QX_Src_Ore_Moss'),
       'crystal':mat_crystal_real('QX_Src_Ore_Crystal_Glow',True),'dull':mat_crystal_real('QX_Src_Ore_Crystal_Spent',False)}
    # --- primary blocks
    A1=hull_block((-.34,.14,.20),(.60,.52,.78),11,32,.75,(0,math.radians(-7),math.radians(8)),-1,.02,.34,(-.10,.06),.78)
    A2=hull_block((-.52,.30,.86),(.40,.34,.17),12,60,.5,(math.radians(9),math.radians(-21),math.radians(-10)),-1,.012,.1,(0,0),.85)
    B=hull_block((.38,-.26,.06),(.62,.48,.64),13,30,.75,(math.radians(-10),math.radians(-17),math.radians(-4)),1,.02,.22,(.05,-.05),.78)
    C=hull_block((.82,.46,-.04),(.24,.19,.22),14,40,.6,(.3,.5,.2),0,0,.2,(0,0),.75)
    # primary design facets: A's top rises toward the cleft, a broad flat outer face; B's top dips away
    K.plane_cut(A1,(-.34,.14,.86),(Vector((0,0,1))-NC*.42+TC*.12).normalized())
    K.plane_cut(A1,Vector((-.34,.14,.2))-NC*.50,(-NC+TC*.25+Vector((0,0,.18))).normalized())
    K.plane_cut(B,(.38,-.26,.56),(Vector((0,0,1))+NC*.38-TC*.14).normalized())
    K.plane_cut(B,Vector((.38,-.26,.2))+NC*.52-TC*.2,(NC-TC*.35+Vector((0,0,.25))).normalized())
    K.plane_cut(B,Vector((.38,-.26,.42))-TC*.52,(-TC+NC*.3+Vector((0,0,.55))).normalized())        # front chamfer
    K.plane_cut(B,Vector((.38,-.26,.42))+TC*.50,(TC+NC*.5+Vector((0,0,.35))).normalized())
    K.plane_cut(A1,Vector((-.34,.14,.60))-TC*.48,(-TC-NC*.4+Vector((0,0,.45))).normalized())
    K.plane_cut(A1,Vector((-.34,.14,.55))+TC*.50,(TC-NC*.6+Vector((0,0,.3))).normalized())
    K.plane_cut(A1,Vector((-.34,.14,.80))-NC*.36,(-NC*.8+Vector((0,0,1))).normalized())          # weathered-back outer top edge (no boolean: deterministic)
    A2.free()
    objs={}
    for name,bm,bv in (('A1',A1,.038),('B',B,.036),('C',C,.024)):objs[name]=to_object('_blk_'+name,finish_block(bm,bv),coll)
    # --- secondary: chips on silhouette edges, crack grooves, weathering pockets
    def cutter(center,size,seed,rot=(0,0,0),exp=.45,n=24,bevel=True):
        bm=hull_block(center,size,seed,n,exp,rot)
        if bevel:bmesh.ops.bevel(bm,geom=bm.edges[:],offset=.006,segments=1,affect='EDGES',clamp_overlap=True)
        return to_object('_cut%d'%seed,bm,coll)
    def chip_at(o,p,seed,size):
        cen=sum((v.co for v in o.data.vertices),Vector())/len(o.data.vertices);out=(p-cen);out.z=0;out=out.normalized()
        return cutter(p+out*size[0]*.55+Vector((0,0,size[2]*.35)),size,seed,(rng.uniform(0,3),rng.uniform(0,3),rng.uniform(0,3)))
    def top_points(o,k,minz,side):
        cen=sum((v.co for v in o.data.vertices),Vector())/len(o.data.vertices)
        vs=sorted((v.co.copy() for v in o.data.vertices if v.co.z>minz and (v.co-cen).dot(NC)*side>.12),key=lambda p:-(p.z*.6+(p-cen).xy.length))
        out=[]
        for p in vs:
            if all((p-q).length>.22 for q in out):out.append(p)
            if len(out)==k:break
        return out
    cuts=[]
    for i,p in enumerate(top_points(objs['A1'],4,.45,-1)):
        cuts.append(chip_at(objs['A1'],p,100+i,(rng.uniform(.09,.14),rng.uniform(.08,.12),rng.uniform(.08,.12))))
    boolean(objs['A1'],cuts)
    cuts=[]
    for i,p in enumerate(top_points(objs['B'],3,.38,1)):
        cuts.append(chip_at(objs['B'],p,160+i,(rng.uniform(.08,.12),rng.uniform(.07,.1),rng.uniform(.06,.09))))
    if post:  # pick-mark notches on both cleft lips
        for i,(t,z) in enumerate([(-.12,.36),(.10,.42),(.0,.30)]):
            p=TC*t+Vector((0,0,z));cuts.append(cutter(p+NC*(.07 if i%2 else -.07),(.06,.04,.05),180+i,(.4,.2,i)))
    boolean(objs['B'],cuts)
    rock=bmesh.new()
    for n in ('A1','B','C'):
        rock.from_mesh(objs[n].data);bpy.data.objects.remove(objs[n])
    K.flat_base(rock);bmesh.ops.remove_doubles(rock,verts=rock.verts[:],dist=.0005)
    # drop loose slivers a cutter may have left floating (keep the real blocks: > 30 cm)
    seen=set();dropped=0
    for v in list(rock.verts):
        if v in seen or not v.is_valid:continue
        isl=[];stack=[v];seen.add(v)
        while stack:
            a=stack.pop();isl.append(a)
            for e in a.link_edges:
                b=e.other_vert(a)
                if b not in seen:seen.add(b);stack.append(b)
        lo=Vector([min(q.co[i] for q in isl) for i in range(3)]);hi=Vector([max(q.co[i] for q in isl) for i in range(3)])
        if (hi-lo).length<.30:bmesh.ops.delete(rock,geom=isl,context='VERTS');dropped+=1
    LOG.append(('Ore_Boulder','loose islands removed',str(dropped)))
    for f in rock.faces:f.smooth=True
    for e in rock.edges:
        if not e.is_manifold or e.calc_face_angle(0)>math.radians(16):e.smooth=False   # facets stay crisp, bevel rows soften
    ul=rock.loops.layers.uv.verify();cl=rock.loops.layers.float_color.new('Var')
    for f in rock.faces:
        for lp in f.loops:lp[cl]=(.5,0,0,1)
    me=bpy.data.meshes.new('Ore_Boulder_Mesh');rock.to_mesh(me);rock.free();me.uv_layers[0].name='UVMap'
    o=bpy.data.objects.new('Ore_Boulder',me);coll.objects.link(o);o.parent=ctx.root;ctx.objs.append(o);me.materials.append(M['rock'])
    # edge-normal smoothing: keep facets, soften bevel rows
    md=o.modifiers.new('WN','WEIGHTED_NORMAL');md.keep_sharp=True
    # semi-real: 8 mm voxel remesh of the game mesh, sculpted relief, moss cushions with thickness.
    # The high poly is the review / bake source; the low poly above is the game mesh (hidden in renders).
    o.hide_render=True;o['qx_role']='game_low_poly'
    hp=remeshed(o,'Ore_Boulder_HP',coll,.008);hp.parent=ctx.root;hbm,l2=sculpt(hp,1.0,1.0,0,True)
    hp.data.materials.append(M['rock']);hp['qx_role']='bake_source_high_poly';ctx.objs.append(hp)
    ms=moss_shell(hbm,l2,'Ore_Moss_Shell',coll);ms.parent=ctx.root;ms.data.materials.append(M['moss']);ctx.objs.append(ms)
    rock_bvh=BVHTree.FromBMesh(hbm);hbm.free()
    # --- crystals in the cleft
    cr=K.new_bm();base0=Vector((0,0,.16))
    def cdir(along,up,out=0.0):return (TC*along+Vector((0,0,up))+NC*out).normalized()
    main=[(base0+TC*-.06,cdir(-.16,1,.04),.115,1.32),
          (base0+TC*.12+Vector((0,0,.03)),cdir(.30,1,-.10),.078,.80),
          (base0+TC*-.20+Vector((0,0,.02)),cdir(-.70,1,.20),.070,.70),
          (base0+TC*-.30+Vector((0,0,.0)),cdir(-1.1,1,-.15),.056,.50),
          (base0+TC*.02+Vector((0,0,.05)),cdir(.05,1,.50),.055,.46),
          (base0+TC*-.12+Vector((0,0,.04)),cdir(-.40,1,-.45),.048,.38)]
    small=[]
    for k in range(14):  # small crystals on the cleft lips, grouped in clumps of 3-5
        clump=k//4;t=[-.30,-.05,.22,.38][clump]+rng.uniform(-.05,.05);sidev=1 if clump%2 else -1
        z=.24+.15*K.c01(1-abs(t)/.45)+rng.uniform(-.03,.03)
        p=TC*t+NC*sidev*(half_gap(z)+.005)+Vector((0,0,z))
        small.append((p,(NC*sidev*.8+Vector((0,0,1))+TC*rng.uniform(-.5,.5)).normalized(),rng.uniform(.016,.032),rng.uniform(.07,.19)))
    for i,(p,d,r,L) in enumerate(main):
        if post:crystal_into(cr,p,d,r,L,rng,rng.random(),True)
        else:crystal_into(cr,p,d,r,L,rng,rng.random())
    for i,(p,d,r,L) in enumerate(small):
        if post and i%3:continue                      # most small crystals were taken too
        crystal_into(cr,p,d,r,L,rng,rng.random(),post)
    oc=K.link('Ore_Crystals_Spent' if post else 'Ore_Crystals',cr,[M['dull' if post else 'crystal']],False)
    bv=oc.modifiers.new('EdgeCatch','BEVEL');bv.width=.0025;bv.segments=1;bv.limit_method='ANGLE';bv.angle_limit=math.radians(25)
    # --- ground blend skirt, talus fan, moss clumps, shards
    sk=K.new_bm();skirt_into(sk);K.link('Ore_Ground_Blend',sk,[M['skirt']])
    ta=bmesh.new();fan=[]
    # fine pebbles half-sunk along the rock foot (weathered off the blocks), thinning outward
    prng=random.Random(77);npeb=0
    for k in range(400):
        if npeb>=56:break
        a=prng.uniform(0,TAU);s_=prng.uniform(.25,.95);x,y=1.12*s_*math.cos(a),.95*s_*math.sin(a)
        if rock_bvh.ray_cast(Vector((x,y,3)),Vector((0,0,-1)))[0] is not None:continue
        nr=rock_bvh.find_nearest(Vector((x,y,.02)))[3]
        if nr is None or nr<.01 or prng.random()>math.exp(-nr/.12):continue
        sz=prng.uniform(.010,.032);z=skirt_height(x,y)
        b2=hull_block((x,y,z+sz*.05),(sz*1.3,sz,sz*.55),600+k,24,.6,(prng.uniform(0,.4),prng.uniform(0,.4),prng.uniform(0,TAU)),rmin=.7)
        finish_block(b2,sz*.12,max(z-.002,0));K.merge_into(ta,b2);npeb+=1
    # graded scree: medium pieces at the foot of B, smaller ones trailing out, all inside the skirt
    for k,(sz,cnt,r0,r1) in enumerate([(.10,2,.0,.06),(.06,4,.05,.16),(.035,7,.12,.30),(.02,12,.22,.42)]):
        for i in range(cnt):
            t=rng.uniform(r0,r1);a=rng.uniform(-.9,.9);base=Vector((.70,-.62,0))+Vector((math.cos(a-.6)*.8,math.sin(a-.6),0)).normalized()*t
            if math.hypot(base.x/1.12,base.y/.95)>.9:continue
            s_=sz*rng.uniform(.75,1.2);z=skirt_height(base.x,base.y)
            b2=hull_block((base.x,base.y,z+s_*.1),(s_*1.3,s_,s_*.6),300+len(fan),30,.62,(rng.uniform(0,.5),rng.uniform(0,.5),rng.uniform(0,TAU)),rmin=.7)
            finish_block(b2,s_*.1,max(z-.002,0));K.merge_into(ta,b2);fan.append(base)
    for k,(x,y,s_) in enumerate([(-.92,.0,.075),(-.55,-.60,.05),(.18,.72,.06),(-.30,-.70,.035),(-.70,.55,.04),(.55,.62,.035)]):
        z=skirt_height(x,y);b2=hull_block((x,y,z+s_*.08),(s_*1.4,s_,s_*.65),400+k,30,.6,(0,0,k),rmin=.7);finish_block(b2,s_*.1,max(z-.002,0));K.merge_into(ta,b2)
    tb=K.new_bm();K.merge_into(tb,ta);o2=K.link('Ore_Talus_And_Gravel',tb,[M['rock']],False)
    o2.hide_render=True;o2['qx_role']='game_low_poly'
    th=remeshed(o2,'Ore_Talus_HP',coll,.004,1);th.parent=ctx.root;tbm,_=sculpt(th,.3,.35,3,False,False);tbm.free()
    th.data.materials.append(M['rock']);th['qx_role']='bake_source_high_poly';ctx.objs.append(th)
    mo=K.new_bm()
    for k,(x,y,rx,ry) in enumerate([(-.82,.42,.20,.13),(-.15,.74,.16,.10),(-.92,-.30,.13,.09),(.42,.55,.12,.08)]):
        z=skirt_height(x,y);K.lumpy_into(mo,(x,y,z-.01),(rx,ry,.035),500+k,3,.25,2.5,k)
    K.flat_base(mo,0.0);mc=K.link('Ore_Moss_Clumps',mo,[M['moss']])
    ca=mc.data.color_attributes.new('Ms','FLOAT_COLOR','POINT')
    for i,v in enumerate(mc.data.vertices):ca.data[i].color=(K.c01(v.co.z/.02),noise.noise(v.co*9)*.5+.5,0,1)
    # grass tufts where water and soil collect: at the rock foot and around the skirt, never on the rock
    gr=K.new_bm();placed=tries=0
    centres=[]
    while len(centres)<24 and tries<4000:
        tries+=1;a=rng.uniform(0,TAU);s_=rng.uniform(.3,1.0)**.5;c_=(1.12*s_*math.cos(a),.95*s_*math.sin(a))
        nr=rock_bvh.find_nearest(Vector((c_[0],c_[1],.03)))[3]
        if nr is not None and .03<nr<(.18 if len(centres)<16 else .5) and all(math.dist(c_,q)>.14 for q in centres):centres.append(c_)
    tries=0
    while placed<110 and tries<5000:
        tries+=1;c_=rng.choice(centres);r_=abs(rng.gauss(0,.045));a=rng.uniform(0,TAU);x,y=c_[0]+r_*math.cos(a),c_[1]+r_*math.sin(a)
        hit=rock_bvh.ray_cast(Vector((x,y,3)),Vector((0,0,-1)))
        if hit[0] is not None and hit[0].z>.012:continue
        near=rock_bvh.find_nearest(Vector((x,y,.03)))[3]
        if near is None or near<.02:continue
        tuft_into(gr,rng,Vector((x,y,skirt_height(x,y)-.006)),.05,.17 if near<.15 else .11);placed+=1
    K.link('Ore_Grass_Tufts',gr,[K.M['blade']],False)
    sh=K.new_bm()
    for k in range(7 if post else 3):
        a=-1.2+k*.35+rng.uniform(-.1,.1);t=rng.uniform(.2,.45) if post else rng.uniform(.15,.3);p=Vector((.2,-.48,0))+Vector((math.cos(a),math.sin(a),0))*t
        p.z=skirt_height(p.x,p.y)+.008;d=Vector((math.cos(a+1.4),math.sin(a+1.4),.18))
        crystal_into(sh,p,d,rng.uniform(.012,.022)*(1.4 if post else 1),rng.uniform(.06,.11),rng,rng.random(),True)
    K.link('Ore_Crystal_Shards',sh,[M['dull' if post else 'crystal']],False)
    ctx.root.rotation_euler=(0,0,math.pi/2-math.atan2(TC.y,TC.x))                               # cleft opens to the front (-Y)
    ctx.extra['boolean_rejections']=[list(x) for x in LOG];LOG.clear()
    ctx.extra.update({'cleft_normal':list(NC),'cleft_direction':list(TC),'crystal_base_m':list(base0),'main_crystals':len(main),'small_crystals':len(small),
                      'talus_pieces':len(fan),'state_change':'post: crystals snapped to fracture stumps, veins unlit, pick notches on cleft lips, more spent shards' if post else 'pre'})
