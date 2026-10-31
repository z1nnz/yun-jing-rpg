"""承天 · 第 1、2 天的模型（C 包）— Eli-0731, Blender 4.5.3 LTS.
RK03 官道茶亭、G01 村口石燈、TY04 院角舊石燈（守燈）、TY08 晾藥架、TY09 生活雜物組。
Each item is modelled only after its AI three-view candidates are saved and one is picked in
art/references/qingxi-day12-c/<ID>/prompt.txt (AGENTS.md order).
Pipeline: named parts with painterly tiled source materials, tagged into bake groups → each group joined, unique UV,
Cycles bake (diffuse colour, AO with the whole asset visible, roughness, tangent normal, object normal, metal, glow mask,
edge pointiness, position) → numpy finish (cool AO shade, warm worn edges, moss on up-facing joints, soil at the feet,
per-item paint) → one material per group with Albedo / Normal / MaskURP / ORM (+ Emission for lamp groups)
→ LOD1 ≈ 50 %, LOD2 ≈ 15 % per group → simple _Collision mesh → .blend, FBX (all LODs + collision), GLB (LOD0).
Origin: footprint centre, bottom at z = 0, Blender -Y is the front. No ground plate.
blender -b --factory-startup -P build_day12.py -- G01 [TY04 ...]
"""
import bpy,bmesh,json,math,sys,random
from pathlib import Path
from mathutils import Vector,Matrix
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];PKG='qingxi-day12-c'
REF=ROOT/'art/references'/PKG;TEX=ROOT/'art/textures'/PKG;OUT=ROOT/'art/exports'/PKG
for p in (TEX,OUT):p.mkdir(parents=True,exist_ok=True)
LIMITS={'RK03':(6,5,4.5),'G01':(.6,.6,2.2),'TY04':(.9,.9,2.0),'TY08':(2.0,.8,1.8),'TY09':(1.6,1.6,2.0)}

# ---------------- painterly tiled source textures (512², tileable) ----------------
R=512;rng=np.random.default_rng(1101)
def tile_noise(cx,cy):
    g=rng.random((cy,cx));x=np.linspace(0,cx,R,endpoint=False);y=np.linspace(0,cy,R,endpoint=False)
    xi=x.astype(int);yi=y.astype(int);fx=x-xi;fy=y-yi;fx=fx*fx*(3-2*fx);fy=fy*fy*(3-2*fy)
    a=g[np.ix_(yi%cy,xi%cx)];b=g[np.ix_(yi%cy,(xi+1)%cx)];c=g[np.ix_((yi+1)%cy,xi%cx)];d=g[np.ix_((yi+1)%cy,(xi+1)%cx)]
    fx=fx[None,:];fy=fy[:,None];return (a*(1-fx)+b*fx)*(1-fy)+(c*(1-fx)+d*fx)*fy
def fbm(c0,oct=4,aniso=1):
    v=0;amp=.5;tot=0
    for o in range(oct):v=v+amp*tile_noise(c0*2**o,max(1,int(c0*2**o/aniso)));tot+=amp;amp*=.5
    return v/tot
def lerp(a,b,t):return np.asarray(a)[None,None,:]*(1-t[...,None])+np.asarray(b)[None,None,:]*t[...,None]
def img(name,rgb,data=False):
    im=bpy.data.images.new(name,R,R)
    if data:im.colorspace_settings.name='Non-Color'
    a=np.ones((R,R,4),np.float32);a[...,:3]=np.clip(rgb,0,1);im.pixels.foreach_set(a.ravel());im.pack();return im
def nmap(name,h,s):
    dx=(np.roll(h,-1,1)-np.roll(h,1,1))*s;dy=(np.roll(h,-1,0)-np.roll(h,1,0))*s
    n=np.dstack([-dx,-dy,np.ones_like(h)]);n/=np.linalg.norm(n,axis=2,keepdims=True);return img(name,n*.5+.5,True)
X=np.arange(R)[None,:]/R;Y=np.arange(R)[:,None]/R
def strokes(c,aniso,lo=.62):  # a few visible brush strokes, not a field of noise
    return np.clip((fbm(c,2,aniso)-lo)*4,0,1)
GLOW={}
def make_sources():
    S={}
    soft=fbm(2,3);warp=fbm(2,2)
    # timber: palette #6a4630 → #a87a50, sun-faded grey, long soft grain, few cracks
    grain=(.5+.5*np.sin(math.tau*(X*7+warp*.6)))**2;cr=np.clip((fbm(30,2,aniso=14)-.70)*6,0,1);st=strokes(6,6)
    t=np.clip(.50+.30*(soft-.5)*2-.12*grain+.12*st-.30*cr,0,1)
    S['wood']=(lerp((.33,.25,.19),(.58,.46,.35),t)*(1-.10*(fbm(3,2)>.6)[...,None])+.05*np.array([.4,.4,.42])*fbm(4,2)[...,None],.5*grain+1.2*cr+.3*st,2.4,.78,0,0)
    S['oldwood']=(lerp((.25,.21,.17),(.50,.43,.35),np.clip(t*1.1-.05,0,1))*(1-.25*cr[...,None]),.8*grain+1.6*cr,2.8,.86,0,0)
    S['planks']=(lerp((.33,.23,.16),(.56,.41,.28),np.clip(t*.9+.1*((X*5)%1<.04),0,1))*(1-.35*((X*5)%1<.03))[...,None],.5*grain+1.5*((X*5)%1<.03)+cr,2.6,.8,0,0)
    # stone: warm granite (#8a8478 → #b8b0a0) with lichen dots; blue-grey garden stone
    big=fbm(3,4);lich=np.clip((fbm(40,2)-.72)*5,0,1);st=strokes(5,3,.6)
    blot=np.clip((fbm(2,3)-.45)*2.2,0,1);S['granite']=(lerp((.36,.34,.31),(.64,.61,.55),np.clip(big*.8+.25*blot+.15*st-.05,0,1))*(1-.10*lich[...,None])+lich[...,None]*np.array([.06,.08,.02]),big+.5*fbm(24,2)+.6*lich,3.2,.88,0,0)
    S['bluestone']=(lerp((.26,.30,.33),(.52,.56,.58),np.clip(big*.8+.25*blot+.15*st-.05,0,1))*(1-.08*lich[...,None])+lich[...,None]*np.array([.10,.12,.10]),big+.5*fbm(24,2)+.6*lich,3.2,.88,0,0)
    S['plinth']=(lerp((.42,.40,.36),(.64,.61,.55),np.clip(big+.12*st,0,1)),big+.4*fbm(16,2),3.0,.9,0,0)
    # roof tile: blue-grey #3e4e58 / #2c3640, soft tonal patches
    S['tile']=(lerp((.18,.22,.26),(.34,.40,.45),np.clip(soft*.8+.2*strokes(8,2),0,1)),fbm(20,2),1.4,.72,0,0)
    S['tile_new']=(lerp((.24,.29,.34),(.38,.45,.51),soft),fbm(20,2),1.2,.6,0,0)
    nodes=np.clip(1-np.abs(((Y*3)%1)-.5)*30,0,1);S['bamboo']=(lerp((.46,.42,.24),(.70,.63,.38),.6*soft+.4*fbm(4,2,aniso=6))*(1-.28*nodes[...,None]),.3*fbm(12,2,aniso=8)+nodes,1.8,.6,0,0)
    S['bamboo_old']=(lerp((.33,.29,.20),(.54,.48,.34),.6*soft+.4*fbm(4,2,aniso=6))*(1-.28*nodes[...,None]),.3*fbm(12,2,aniso=8)+nodes,1.8,.7,0,0)
    tw=.5+.5*np.sin(math.tau*((X+Y)*12));S['hemp']=(lerp((.38,.30,.20),(.60,.50,.34),np.clip(tw*.6+.4*soft,0,1)),tw,1.2,.92,0,0)
    S['rope_new']=(lerp((.62,.55,.38),(.80,.74,.56),np.clip(tw*.6+.4*soft,0,1)),tw,1.2,.9,0,0)
    S['paper']=(lerp((.78,.72,.58),(.90,.85,.72),fbm(4,3))*(1-.18*np.clip((fbm(10,2)-.62)*4,0,1))[...,None],fbm(30,2),.6,.9,0,1)
    S['lantern']=(lerp((.78,.60,.40),(.90,.74,.52),fbm(4,3)),.5+.5*np.sin(Y*math.tau*14),.8,.85,0,1)
    S['lacquer_red']=(lerp((.42,.10,.07),(.58,.18,.10),soft),fbm(10,2),.6,.55,0,0)
    S['clay']=(lerp((.40,.22,.14),(.62,.38,.25),np.clip(soft+.1*strokes(6,2),0,1)),fbm(14,3),1.6,.88,0,0)
    S['glaze']=(lerp((.12,.24,.23),(.27,.42,.38),np.clip(soft*.9+.2*fbm(5,3),0,1))*(1-.18*np.clip((fbm(3,2)-.55)*3,0,1))[...,None],.3*fbm(10,2),.5,.32,0,0)
    S['iron']=(lerp((.17,.15,.14),(.40,.24,.14),np.clip((fbm(6,4)-.35)*1.8,0,1)),fbm(18,3),2.4,.8,.3,0)
    S['linen']=(lerp((.70,.66,.56),(.84,.80,.70),soft)*(1-.06*(np.sin(X*900)>.6))[...,None],.5*np.sin(X*700)+.5*np.sin(Y*700),.7,.95,0,0)
    wx=((X*10)%1<.5);wy=((Y*10)%1<.5);ov=np.where(wx^wy,.5+.5*np.sin(X*10*math.tau)**2,.5+.5*np.sin(Y*10*math.tau)**2)
    S['weave']=(lerp((.26,.20,.12),(.54,.44,.27),ov*.75+.25*soft)*(1-.15*np.clip((fbm(3,2)-.5)*3,0,1))[...,None],ov,3.2,.85,0,0)
    S['moss']=(lerp((.22,.30,.12),(.42,.50,.20),fbm(8,3)),fbm(16,3),3.0,.95,0,0)
    S['soil']=(lerp((.28,.21,.14),(.45,.35,.24),fbm(8,3)),fbm(24,3),2.4,.95,0,0)
    S['water']=(lerp((.06,.16,.16),(.12,.26,.25),soft),fbm(6,2)*.2,.3,.05,0,0)
    S['charcoal']=(lerp((.05,.05,.05),(.20,.13,.10),fbm(20,2)),fbm(20,2),2,.9,0,0)
    S['ember']=(lerp((.55,.18,.06),(.85,.40,.12),fbm(20,2)),fbm(20,2),1,.9,0,1)
    for k,(c0,c1) in {'herb_green':((.20,.32,.12),(.38,.52,.22)),'herb_sage':((.36,.42,.30),(.56,.62,.46)),'herb_dry':((.40,.34,.18),(.62,.54,.30)),
                      'herb_olive':((.30,.32,.14),(.48,.50,.24)),'flower_violet':((.36,.30,.48),(.54,.46,.66)),'flower_gold':((.62,.46,.14),(.82,.66,.26)),
                      'leaf_fallen':((.42,.28,.14),(.66,.46,.22))}.items():
        S[k]=(lerp(c0,c1,np.clip(.6*fbm(6,2)+.4*(.5+.5*np.sin(X*math.tau*3)),0,1)),fbm(20,2),1,.85,0,0)
    out={}
    for k,(alb,h,s,r,m,glow) in S.items():
        mat=bpy.data.materials.new('src_'+k);mat.use_nodes=True;nt=mat.node_tree;bs=nt.nodes['Principled BSDF']
        bs.inputs['Roughness'].default_value=r;bs.inputs['Metallic'].default_value=m
        uvn=nt.nodes.new('ShaderNodeUVMap');uvn.uv_map='Tiled'
        ta=nt.nodes.new('ShaderNodeTexImage');ta.image=img('alb_'+k,alb);nt.links.new(uvn.outputs['UV'],ta.inputs['Vector']);nt.links.new(ta.outputs['Color'],bs.inputs['Base Color'])
        tn=nt.nodes.new('ShaderNodeTexImage');tn.image=nmap('nrm_'+k,h,s);nt.links.new(uvn.outputs['UV'],tn.inputs['Vector'])
        nm=nt.nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.8;nt.links.new(tn.outputs['Color'],nm.inputs['Color']);nt.links.new(nm.outputs['Normal'],bs.inputs['Normal'])
        out[k]=mat;GLOW[mat.name]=(m,glow)
    return out

# ---------------- geometry helpers ----------------
parts=[]
def link(o,grp):bpy.context.scene.collection.objects.link(o);o['grp']=grp;parts.append(o);return o
def finish(name,bm,mat,grp,scale=.4,uv=None):
    """tiled UV: box projection on principal axes, or uv=(u,v) callables of a world point for cylinders"""
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces);lay=bm.loops.layers.uv.get('Tiled') or bm.loops.layers.uv.new('Tiled')
    if uv:
        for f in bm.faces:
            us=[uv[0](l.vert.co) for l in f.loops];m=max(us)-min(us)
            for l,u in zip(f.loops,us):l[lay].uv=(u/scale,uv[1](l.vert.co)/scale)
    else:
        pts=np.array([v.co[:] for v in bm.verts]);c=pts.mean(0)
        try:_,_,vt=np.linalg.svd(pts-c,full_matrices=False);A,S1,S2=[Vector(v) for v in vt]
        except Exception:A,S1,S2=Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1))
        for f in bm.faces:
            n=f.normal;k=int(np.argmax([abs(n.dot(A)),abs(n.dot(S1)),abs(n.dot(S2))]))
            for l in f.loops:
                p=l.vert.co-Vector(c);u,v={0:(p.dot(S1),p.dot(S2)),1:(p.dot(S2),p.dot(A)),2:(p.dot(S1),p.dot(A))}[k];l[lay].uv=(u/scale,v/scale)
    me=bpy.data.meshes.new(name);bm.to_mesh(me);bm.free();o=bpy.data.objects.new(name,me);me.materials.append(mat)
    return link(o,grp)
def cyl_uv(r):return (lambda p:math.atan2(p.y,p.x)*r,lambda p:p.z)
def lathe(name,profile,mat,grp,seg=48,scale=.4,smooth=True,cyl=None,center=(0,0,0)):
    """profile: [(r,z)...] bottom→top; revolved around Z, then moved to center"""
    bm=bmesh.new();rings=[]
    for r,z in profile:
        rings.append([bm.verts.new((r*math.cos(math.tau*i/seg),r*math.sin(math.tau*i/seg),z)) if r>1e-6 else None for i in range(seg)])
    for a,b in zip(rings,rings[1:]):
        if a[0] is not None and b[0] is not None:
            for i in range(seg):j=(i+1)%seg;bm.faces.new((a[i],a[j],b[j],b[i]))
    for idx,(r,z) in [(0,profile[0]),(len(profile)-1,profile[-1])]:
        if r<=1e-6:
            nb=rings[1] if idx==0 else rings[-2];c=bm.verts.new((0,0,z))
            for i in range(seg):j=(i+1)%seg;bm.faces.new((nb[j],nb[i],c) if idx==0 else (nb[i],nb[j],c))
    bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=1e-7)
    for f in bm.faces:f.smooth=smooth
    o=finish(name,bm,mat,grp,scale,uv=cyl_uv(max(r for r,z in profile)) if cyl else None)
    o.data.transform(Matrix.Translation(center));return o
def tube(name,pts,r,mat,grp,sides=8,scale=.3,caps=True,radii=None):
    pts=[Vector(p) for p in pts];bm=bmesh.new();rings=[];prev=None
    for i,p in enumerate(pts):
        t=(pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)]).normalized()
        u=(prev-t*prev.dot(t)).normalized() if prev is not None else t.orthogonal().normalized();prev=u;v=t.cross(u);rr=radii[i] if radii else r
        rings.append([bm.verts.new(p+(u*math.cos(math.tau*k/sides)+v*math.sin(math.tau*k/sides))*rr) for k in range(sides)])
    for a,b in zip(rings,rings[1:]):
        for k in range(sides):bm.faces.new((a[k],a[(k+1)%sides],b[(k+1)%sides],b[k]))
    if caps:bm.faces.new(list(reversed(rings[0])));bm.faces.new(rings[-1])
    for f in bm.faces:f.smooth=True
    return finish(name,bm,mat,grp,scale)
def rope(name,pts,r,mat,grp,plies=3,twist=None,sides=5):
    P=[Vector(p) for p in pts];L=sum((b-a).length for a,b in zip(P,P[1:]));twist=twist or L/(r*14);dense=[]
    for a,b in zip(P,P[1:]):
        n=max(2,int((b-a).length/(r*1.0)))
        for i in range(n):dense.append(a+(b-a)*(i/n))
    dense.append(P[-1]);res=[]
    for k in range(plies):
        path=[];s=0
        for i,p in enumerate(dense):
            if i:s+=(p-dense[i-1]).length
            t=(dense[min(i+1,len(dense)-1)]-dense[max(i-1,0)]).normalized();u=t.orthogonal().normalized();v=t.cross(u)
            ang=math.tau*k/plies+s/L*twist*math.tau;path.append(p+(u*math.cos(ang)+v*math.sin(ang))*r*.55)
        res.append(tube(f'{name}_ply{k+1}',path,r*.52,mat,grp,sides,.1))
    return res
def lashing(name,center,axis,r,turns,mat,grp,width=None,cord=.006):
    """rope wrapped around a pole: helix of `turns` around `axis` through `center`"""
    axis=Vector(axis).normalized();u=axis.orthogonal().normalized();v=axis.cross(u);width=width or turns*cord*2.4;pts=[]
    n=turns*16
    for i in range(n+1):
        a=math.tau*i/16;pts.append(Vector(center)+axis*(-width/2+width*i/n)+(u*math.cos(a)+v*math.sin(a))*(r+cord))
    return tube(name,pts,cord,mat,grp,6,.1)
def box_bm(size,center=(0,0,0)):
    bm=bmesh.new();bmesh.ops.create_cube(bm,size=1)
    for v in bm.verts:v.co=Vector([center[i]+v.co[i]*size[i] for i in range(3)])
    return bm
def bevel(o,w,segs=2,angle=35):
    m=o.modifiers.new('wear','BEVEL');m.width=w;m.segments=segs;m.limit_method='ANGLE';m.angle_limit=math.radians(angle);m.use_clamp_overlap=True
    apply(o,m)
def apply(o,m):
    bpy.context.view_layer.objects.active=o;o.select_set(True);bpy.ops.object.modifier_apply(modifier=m.name);o.select_set(False)
def subdiv(o,cuts):
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.subdivide_edges(bm,edges=bm.edges,cuts=cuts,use_grid_fill=True);bm.to_mesh(o.data);bm.free()
def jitter(o,amt,seed=1,freq=6):
    r=random.Random(seed);ph=[r.uniform(0,9) for _ in range(6)];o.data.update()
    for v in o.data.vertices:
        p=v.co;n=v.normal;d=amt*(math.sin(p.x*freq+ph[0])*math.sin(p.y*freq*1.3+ph[1])+.6*math.sin(p.z*freq*.8+ph[2])*math.sin((p.x+p.y)*freq*2.1+ph[3]))
        v.co=p+n*d
def box(name,size,center,mat,grp,bev=.01,segs=2,scale=.4,cuts=0,jit=0,seed=1,rot=None):
    o=finish(name,box_bm(size),mat,grp,scale)
    if cuts:subdiv(o,cuts)
    if bev:bevel(o,bev,segs)
    if jit:jitter(o,jit,seed,freq=4/max(size))
    if rot:o.data.transform(rot)
    o.data.transform(Matrix.Translation(center));return o
def beam(name,a,b,w,h,mat,grp,bev=.008,up=(0,0,1),scale=.5):
    """rectangular member from a to b (w across, h along `up`)"""
    a,b=Vector(a),Vector(b);t=(b-a);L=t.length;t.normalize();up=Vector(up);s=t.cross(up).normalized();u=s.cross(t)
    o=finish(name,box_bm((L,w,h)),mat,grp,scale);bevel(o,bev,2)
    o.data.transform(Matrix(((t.x,s.x,u.x,0),(t.y,s.y,u.y,0),(t.z,s.z,u.z,0),(0,0,0,1))));o.data.transform(Matrix.Translation((a+b)/2));return o
def prism(name,poly,depth,mat,grp,bev=.004,scale=.4):
    """2D polygon in XZ (front view) extruded along Y (depth, centred on y=0)"""
    bm=bmesh.new();f=bm.faces.new([bm.verts.new((x,-depth/2,z)) for x,z in poly])
    r=bmesh.ops.extrude_face_region(bm,geom=[f]);vs=[e for e in r['geom'] if isinstance(e,bmesh.types.BMVert)]
    bmesh.ops.translate(bm,verts=vs,vec=(0,depth,0));o=finish(name,bm,mat,grp,scale)
    if bev:bevel(o,bev,1,30)
    return o
def carve(o,cutters):
    for c in cutters:
        m=o.modifiers.new('carve','BOOLEAN');m.operation='DIFFERENCE';m.object=c;m.solver='EXACT';apply(o,m);bpy.data.objects.remove(c)
    assert len(o.data.polygons)>0,f'{o.name}: boolean emptied the mesh'
def cutter(bm,name='cut'):
    me=bpy.data.meshes.new(name);bm.to_mesh(me);bm.free();o=bpy.data.objects.new(name,me);bpy.context.scene.collection.objects.link(o);o.hide_render=True;return o
def leaf(name,base,direction,normal,L,W,mat,grp,curl=.25,seg=5):
    """lens-shaped leaf with a slight fold along the midrib"""
    d=Vector(direction).normalized();n=Vector(normal);s=d.cross(n).normalized();n=s.cross(d);bm=bmesh.new();mid=[];left=[];right=[]
    for i in range(seg+1):
        t=i/seg;w=W*math.sin(math.pi*t)**.8/2;c=Vector(base)+d*L*t-n*curl*L*t*t
        mid.append(bm.verts.new(c+n*w*.25))
        if 0<i<seg:left.append(bm.verts.new(c-s*w));right.append(bm.verts.new(c+s*w))
    for i in range(seg):
        if i==0:bm.faces.new((mid[0],left[0],mid[1]));bm.faces.new((mid[0],mid[1],right[0]))
        elif i==seg-1:bm.faces.new((mid[i],left[i-1],mid[i+1]));bm.faces.new((mid[i],mid[i+1],right[i-1]))
        else:bm.faces.new((mid[i],left[i-1],left[i],mid[i+1]));bm.faces.new((mid[i],mid[i+1],right[i],right[i-1]))
    for f in bm.faces:f.smooth=True
    return finish(name,bm,mat,grp,.05)
def join(objs,name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:o.select_set(True)
    bpy.context.view_layer.objects.active=objs[0];bpy.ops.object.join();o=bpy.context.object;o.name=name;return o

def hip_surface(name,hw,hd,ze,zr,p,U,mat,grp,step=.03,thick=.06,bump=None,xs=None,region=None):
    """concave hip roof z = ze + (zr-ze)·(d/dmax)^p with upturned corners.
    region=(x0,x1,y0,y1) limits the grid; gable=True variant handled by caller through `zf`."""
    dmax=min(hw,hd)
    def lift(x,y):
        sx=max(0,(abs(x)/hw-.58)/.42);sy=max(0,(abs(y)/hd-.58)/.42);return U*(sx*sy)**1.1
    def zf(x,y,d):return ze+(zr-ze)*(max(0,d)/dmax)**p+lift(x,y)
    x0,x1,y0,y1=region or (-hw,hw,-hd,hd);nx=max(2,int((x1-x0)/step));ny=max(2,int((y1-y0)/step))
    bm=bmesh.new();V=[]
    for j in range(ny+1):
        row=[]
        for i in range(nx+1):
            x=x0+(x1-x0)*i/nx;y=y0+(y1-y0)*j/ny;dx=hw-abs(x);dy=hd-abs(y);d=min(dx,dy);z=zf(x,y,xs(x,y) if xs else d)
            if bump:z+=bump(x,y,dx,dy)
            row.append(bm.verts.new((x,y,z)))
        V.append(row)
    for j in range(ny):
        for i in range(nx):bm.faces.new((V[j][i],V[j][i+1],V[j+1][i+1],V[j+1][i]))
    for f in bm.faces:f.smooth=True
    o=finish(name,bm,mat,grp,.5)
    m=o.modifiers.new('s','SOLIDIFY');m.thickness=thick;m.offset=-1;m.use_even_offset=True;apply(o,m)
    return o,zf

# ---------------- items ----------------
def stone_lantern(M,pid,stone,dims):
    """shared build for G01 and TY04; dims drives the silhouette difference"""
    G='Stone';L='Lamp';parts_z=0;D=dims;meta={'soot':[],'moss_low':.35,'lamp':True}
    z=0
    for k,(w,h,j,cut) in enumerate(D['base']):
        if D.get('fieldstone') and k==0:   # two rough fieldstones side by side for the bottom course
            for sx,ww,sd in ((-w/4,w/2-.012,3),(w/4,w/2-.012,7)):
                box(f'{pid}_Base{k}_{sd}',(ww,w*.98,h),(sx,0,z+h/2),M[stone],G,bev=.03,cuts=5,jit=j*1.8,seed=sd,scale=.5)
        else:
            box(f'{pid}_Base{k}',(w,w,h),(0,0,z+h/2),M[stone],G,bev=.018 if k else .025,cuts=3,jit=j,seed=11+k,scale=.5)
            if cut:  # split line: the course is two dressed stones
                o=parts[-1];bm=box_bm((.008,w+.02,h+.02),(w*.12,0,z+h/2));carve(o,[cutter(bm)])
        z+=h
    zs=z;sh=D['shaft'];h=sh['h']
    bm=box_bm((1,1,1));
    for v in bm.verts:
        t=v.co.z+.5;w=sh['w0']+(sh['w1']-sh['w0'])*t;v.co=Vector((v.co.x*w,v.co.y*w,zs+t*h))
    o=finish(f'{pid}_Shaft',bm,M[stone],G,.5);subdiv(o,3);bevel(o,.012,2);jitter(o,.002,5,8)
    if sh.get('panel'):   # recessed carved frame on front and back
        cs=[]
        for sy in (-1,1):
            w_mid=(sh['w0']+sh['w1'])/2;b=box_bm((w_mid*.62,.03,h*.62),(0,sy*(w_mid/2),zs+h*.5));cs.append(cutter(b))
            b=box_bm((w_mid*.50,.05,h*.52),(0,sy*(w_mid/2),zs+h*.5));inner=cutter(b,'inner')
            m=cs[-1].modifiers.new('ring','BOOLEAN');m.operation='DIFFERENCE';m.object=inner;m.solver='EXACT';apply(cs[-1],m);bpy.data.objects.remove(inner)
        carve(o,cs)
    z=zs+h
    for k,(kind,w,hh) in enumerate(D['upper']):
        if kind=='box':box(f'{pid}_Up{k}',(w,w,hh),(0,0,z+hh/2),M[stone],G,bev=.012,cuts=2,jit=.002,seed=20+k)
        elif kind=='cushion':lathe(f'{pid}_Up{k}',[(w*.40,0),(w*.50,hh*.25),(w*.52,hh*.5),(w*.50,hh*.75),(w*.40,hh)],M[stone],G,seg=36,center=(0,0,z))
        elif kind=='brackets':
            box(f'{pid}_Up{k}',(w,w,hh),(0,0,z+hh/2),M[stone],G,bev=.01)
            for sx in (-1,1):
                for sy in (-1,1):box(f'{pid}_Br{k}{sx}{sy}',(.05,.05,hh*1.6),(sx*w*.48,sy*w*.48,z-hh*.3),M[stone],G,bev=.008)
        z+=hh
    # light chamber: four stone corner posts, a stone floor, window frames and paper (Lamp group), soot inside
    c=D['chamber'];cw,ch=c['w'],c['h'];zc=z
    for sx in (-1,1):
        for sy in (-1,1):box(f'{pid}_Post{sx}{sy}',(c['post'],c['post'],ch),(sx*(cw/2-c['post']/2),sy*(cw/2-c['post']/2),zc+ch/2),M[stone],G,bev=.008,cuts=2,jit=.0015,seed=30)
    box(f'{pid}_ChFloor',(cw-.02,cw-.02,.03),(0,0,zc+.015),M[stone],G,bev=.004)
    inner=cw-2*c['post'];fz=zc+.03;fh=ch-.06
    for side in range(4):
        rot=Matrix.Rotation(side*math.pi/2,4,'Z');yy=-(cw/2-c['post']*.55)
        frame=[]
        frame.append(box(f'{pid}_FrT{side}',(inner,.025,.025),(0,yy,fz+fh-.0125),M['oldwood'],L,bev=.003))
        frame.append(box(f'{pid}_FrB{side}',(inner,.025,.025),(0,yy,fz+.0125),M['oldwood'],L,bev=.003))
        nv=c['bars'];nh=c['rails']
        for i in range(1,nv):frame.append(box(f'{pid}_FrV{side}{i}',(.012,.02,fh-.04),(-inner/2+inner*i/nv,yy-.002,fz+fh/2),M['oldwood'],L,bev=.002))
        for i in range(1,nh):frame.append(box(f'{pid}_FrH{side}{i}',(inner-.01,.02,.012),(0,yy-.002,fz+fh*i/nh),M['oldwood'],L,bev=.002))
        frame.append(box(f'{pid}_Paper{side}',(inner,.004,fh-.04),(0,yy+.012,fz+fh/2),M['paper'],L,bev=0,cuts=3))
        for o in frame:o.data.transform(Matrix.Translation((0,0,0)));o.data.transform(rot)
    meta['soot'].append((0,0,zc+ch*.55,cw/2,ch*.6));meta['light']=(0,0,zc+ch*.45)
    box(f'{pid}_Wick',(.05,.05,.06),(0,0,zc+.06),M['clay'],G,bev=.006)
    z=zc+ch
    r=D['roof'];box(f'{pid}_RoofBase',(cw+.04,cw+.04,.035),(0,0,z+.0175),M[stone],G,bev=.006);z+=.035
    box(f'{pid}_RoofSlab',(cw+.12,cw+.12,.04),(0,0,z+.02),M[stone],G,bev=.012);z+=.03
    o,_=hip_surface(f'{pid}_Roof',r['hw'],r['hw'],z+r['ze'],z+r['zr'],r['p'],r['U'],M[stone],G,step=.012,thick=r['t'],
                    bump=lambda x,y,dx,dy:.004*math.sin((x if dy<dx else y)*math.tau/.07)**2*min(1,min(dx,dy)/.04))
    jitter(o,.0025,9,12);z+=r['zr']+.0
    zt=z-.01
    for k,(rr,hh) in enumerate(D['finial']):
        prof=[(0,0)]+[(rr*math.sin(math.pi*min(1,t/0.999))**.7*(1-.15*t),hh*t) for t in np.linspace(.08,1,9)]+[(0,hh*1.0001)]
        prof=[(.0,0),(rr*.55,0),(rr*.85,hh*.15),(rr,hh*.38),(rr*.9,hh*.58),(rr*.55,hh*.78),(rr*.22,hh*.92),(rr*.06,hh*.985),(0,hh)] if k==len(D['finial'])-1 else [(0,0),(rr,0),(rr*1.05,hh*.5),(rr*.8,hh),(0,hh)]
        lathe(f'{pid}_Finial{k}',prof,M[stone],G,seg=32,center=(0,0,zt));zt+=hh*.94
    meta['top']=zt;meta['moss_up']=.5;meta['stone']=stone
    return meta

def G01(M):
    """村口石燈 · warm granite, slender, small roof cap; soot in the chamber, carved panel on the shaft"""
    return stone_lantern(M,'G01','granite',{
        'base':[(.58,.17,.005,True),(.50,.13,.004,False),(.42,.10,.003,False)],
        'shaft':{'w0':.30,'w1':.24,'h':.80,'panel':True},
        'upper':[('box',.36,.06),('brackets',.44,.07),('box',.48,.07)],
        'chamber':{'w':.34,'h':.34,'post':.055,'bars':2,'rails':2},
        'roof':{'hw':.275,'ze':-.01,'zr':.17,'p':1.5,'U':.045,'t':.065},
        'finial':[(.045,.05),(.06,.12)]})

def TY04(M):
    """院角舊石燈・守燈 · blue-grey stone, stocky, wide roof; tiny crescent carved low on the base"""
    meta=stone_lantern(M,'TY04','bluestone',{
        'fieldstone':True,
        'base':[(.80,.22,.010,True),(.62,.16,.006,False),(.50,.08,.003,False)],
        'shaft':{'w0':.38,'w1':.28,'h':.49},
        'upper':[('cushion',.40,.10),('box',.56,.10)],
        'chamber':{'w':.40,'h':.38,'post':.06,'bars':3,'rails':3},
        'roof':{'hw':.405,'ze':-.02,'zr':.22,'p':1.6,'U':.08,'t':.075},
        'finial':[(.07,.07),(.055,.10)]})
    # 缺月: a small worn crescent (about 4 cm) on the lowest course, left of centre, low — not enlarged, not explained
    o=next(p for p in parts if p.name=='TY04_Base0_3');cx,cz=-.12,.075
    vs=[v.co for v in o.data.vertices if abs(v.co.x-cx)<.05 and abs(v.co.z-cz)<.05 and v.co.y<0];fy=min(v.y for v in vs) if vs else -.39
    bm=bmesh.new();N=24;outer=[(.020*math.cos(a),.020*math.sin(a)) for a in np.linspace(math.radians(60),math.radians(300),N)]
    inner=[(.007+.016*math.cos(a),.016*math.sin(a)) for a in np.linspace(math.radians(280),math.radians(80),N)]
    poly=outer+inner;f=bm.faces.new([bm.verts.new((cx+x,fy-.02,cz+y)) for x,y in poly])
    r=bmesh.ops.extrude_face_region(bm,geom=[f]);bmesh.ops.translate(bm,verts=[e for e in r['geom'] if isinstance(e,bmesh.types.BMVert)],vec=(0,.026,0))
    carve(o,[cutter(bm,'crescent')]);meta['crescent']={'centre':[cx,round(fy,3),cz],'size_m':.04,'depth_m':.006}
    return meta

def TY08(M):
    """晾藥架 · weathered cedar A-frames, three bamboo rails, rope lashings, a splinted leg with fresh rope, sieve shelf; Herbs = full state"""
    F='Frame';H='Herbs';meta={'moss_low':.5,'soil':.12}
    W=1.84;fx=W/2-.02;feet=.32;top=1.70;rr=.034
    legs=[]
    for sx in (-1,1):
        x=sx*fx
        for sy in (-1,1):
            a=(x,sy*feet,0.0);b=(x,-sy*.05,top+.06)
            legs.append(tube(f'TY08_Leg{sx}{sy}',[a,((a[0]+b[0])/2+.004*sy,(a[1]+b[1])/2,(a[2]+b[2])/2),b],rr,M['oldwood'],F,10,.3,radii=[rr*1.08,rr,rr*.9]))
        lashing(f'TY08_TopLash{sx}',(x,0,top-.02),(0,1,0),.05,5,M['hemp'],F)
        for k,(zz,half) in enumerate(((1.28,feet*(1-1.28/top)+.03),(.88,feet*(1-.88/top)+.03),(.34,feet*(1-.34/top)+.03))):
            tube(f'TY08_Cross{sx}{k}',[(x,-half,zz),(x,half,zz)],.022,M['oldwood'],F,8,.3)
            for sy in (-1,1):lashing(f'TY08_CrLash{sx}{k}{sy}',(x,sy*(half-.03),zz),(0,1,0),.03,3,M['hemp'],F)
        for sy in (-1,1):box(f'TY08_FootStone{sx}{sy}',(.14,.12,.07),(x+.01*sy,sy*feet,.03),M['granite'],F,bev=.02,cuts=2,jit=.006,seed=40+sx*3+sy)
    # rails: top rail rests in the A-frame crotch, two lower rails sit on the cross bars
    rails=[(top-.005,0),(1.28+.045,0),(.88+.045,0)]
    for k,(zz,yy) in enumerate(rails):
        tube(f'TY08_Rail{k}',[(-W/2-.05,yy,zz),(W/2+.05,yy,zz)],.021,M['bamboo_old'],F,10,.3)
        for sx in (-1,1):lashing(f'TY08_RLash{k}{sx}',(sx*fx,yy,zz),(1,0,0),.021,4,M['hemp'],F)
    # low shelf: two slats between the frames, round sieve on it with fallen leaves
    for yy in (-.07,.07):box(f'TY08_Slat{yy}',(W-.02,.10,.025),(0,yy,.375),M['oldwood'],F,bev=.006,scale=.5)
    lathe('TY08_Sieve',[(0,0),(.22,0),(.235,.005),(.24,.045),(.225,.05),(.215,.012),(0,.012)],M['weave'],F,seg=40,cyl=True,center=(-.42,0,.39))
    rnd=random.Random(8)
    for i in range(9):
        a=rnd.uniform(0,math.tau);r=rnd.uniform(0,.17);base=Vector((-.42+r*math.cos(a),r*math.sin(a),.405))
        leaf(f'TY08_Fallen{i}',base,(math.cos(a*3),math.sin(a*3),.0),(0,0,1),rnd.uniform(.05,.08),.025,M['leaf_fallen'],F,curl=-.2)
    for i in range(6):
        a=rnd.uniform(0,math.tau);x=rnd.choice((-1,1))*fx+rnd.uniform(-.1,.1);y=rnd.choice((-1,1))*.34+rnd.uniform(-.08,.08)
        leaf(f'TY08_FootLeaf{i}',(x,y,.072),(math.cos(a),math.sin(a),0),(0,0,1),rnd.uniform(.05,.07),.022,M['leaf_fallen'],F,curl=-.15)
    # repaired leg: split-bamboo splint on the left-front leg, tied with fresh rope
    p0=Vector((-fx,-feet,0));p1=Vector((-fx,.05,top+.06));t=(p1-p0).normalized()
    for k,off in enumerate((-.032,.032)):
        a=p0+t*.40;b=p0+t*.72;n=Vector((off,0,0))
        tube(f'TY08_Splint{k}',[a+n,b+n],.012,M['bamboo'],F,6,.2)
    for k,s in enumerate((.45,.56,.67)):lashing(f'TY08_Repair{k}',p0+t*s,t,.046,4,M['rope_new'],F)
    # linen cloth draped over the right end of the top rail
    bm=bmesh.new();cols=8;rows=10;V=[]
    for j in range(rows+1):
        V.append([])
        for i in range(cols+1):
            u=i/cols;v=j/rows;x=.62+u*.32;side=1 if v<.5 else -1;vv=abs(v-.5)*2
            V[-1].append(bm.verts.new((x,side*(.025+.02*vv)+.012*math.sin(u*7+v*3),top+.02-vv*.42*(1+.15*math.sin(u*5)))))
    for j in range(rows):
        for i in range(cols):bm.faces.new((V[j][i],V[j][i+1],V[j+1][i+1],V[j+1][i]))
    for f in bm.faces:f.smooth=True
    o=finish('TY08_Linen',bm,M['linen'],F,.4);m=o.modifiers.new('s','SOLIDIFY');m.thickness=.004;apply(o,m)
    # herbs (full state): bundles tied with twine on each rail
    kinds=[('herb_green',None),('herb_sage',None),('herb_dry',None),('herb_olive','flower_gold'),('herb_sage','flower_violet'),('herb_green',None),('herb_dry',None)]
    for k,(zz,yy) in enumerate(rails):
        n=7 if k==0 else 6
        for i in range(n):
            x=-W/2+.16+(W-.32)*(i+.5)/n+rnd.uniform(-.03,.03);kind,fl=kinds[(i*3+k*2)%len(kinds)];L=rnd.uniform(.24,.36)
            top_pt=Vector((x,yy,zz-.024));tie=top_pt-Vector((0,0,.05))
            tube(f'TY08_Twine{k}{i}',[top_pt+Vector((-.012,0,.025)),top_pt+Vector((0,0,-.02)),tie],.004,M['hemp'],H,5,.1)
            lathe(f'TY08_Tie{k}{i}',[(.0,0),(.016,0),(.017,.012),(.016,.024),(0,.024)],M['hemp'],H,seg=10,center=tie-Vector((0,0,.012)))
            for s in range(8):
                ang=rnd.uniform(0,math.tau);spread=rnd.uniform(.025,.07);end=tie+Vector((spread*math.cos(ang),spread*math.sin(ang),-L*rnd.uniform(.75,1)))
                tube(f'TY08_Stem{k}{i}{s}',[tie,tie+(end-tie)*.5+Vector((0,0,0)),end],.0025,M[kind],H,4,.1)
                for q in range(8):
                    tt=.15+.85*q/8;at=tie+(end-tie)*tt;dirv=Vector((math.cos(ang+q*2.1),math.sin(ang+q*2.1),-.9-.2*rnd.random()))
                    leaf(f'TY08_L{k}{i}{s}{q}',at,dirv,(math.cos(ang+q*2.1+1.6),math.sin(ang+q*2.1+1.6),0),rnd.uniform(.05,.08),rnd.uniform(.014,.024),M[kind],H,curl=.3,seg=4)
                if fl:
                    lathe(f'TY08_Fl{k}{i}{s}',[(0,0),(.009,.004),(.011,.012),(.007,.02),(0,.022)],M[fl],H,seg=8,center=end-Vector((0,0,.012)))
    meta['states']={'empty':'hide the TY08_Herbs_* nodes','full':'show TY08_Herbs_* (default)'}
    return meta

def TY09(M):
    """生活雜物組 · glazed water vat (with gourd ladle), woven basket with a mended rim, old hoe leaning on the vat, coopered bucket with ear handles"""
    meta={'moss_low':.25,'soil':.10,'pieces':{}}
    V,Bk,Ho,Bu='Vat','Basket','Hoe','Bucket'
    vx,vy=.12,.30
    prof=[(.25,0),(.28,.02),(.33,.12),(.365,.30),(.36,.45),(.335,.58),(.30,.66),(.285,.70),(.30,.72),(.315,.745),(.30,.765),(.27,.758),(.262,.72),(.27,.66),(.30,.56),(.315,.45),(.30,.30),(.26,.14),(.22,.08),(0,.08)]
    lathe('TY09_Vat',prof,M['glaze'],V,seg=64,cyl=True,center=(vx,vy,0))
    lathe('TY09_Water',[(0,.62),(.292,.62),(.292,.60),(0,.60)],M['water'],V,seg=64,center=(vx,vy,0))
    # gourd ladle on the rim
    g=lathe('TY09_Ladle',[(0,0),(.05,.004),(.075,.03),(.08,.05),(.072,.07),(.0,.072)],M['wood'],V,seg=24)
    g.data.transform(Matrix.Rotation(math.radians(180),4,'X'));g.data.transform(Matrix.Translation((vx+.10,vy-.08,.792)))
    tube('TY09_LadleHandle',[(vx+.10,vy-.08,.76),(vx+.20,vy-.17,.77),(vx+.33,vy-.28,.79)],.014,M['wood'],V,8)
    meta['pieces']['Vat']={'centre':[vx,vy],'collision':{'type':'cylinder','radius':.365,'height':.765}}
    # basket
    bx,by=-.42,-.32
    lathe('TY09_Basket',[(.20,.0),(.215,.01),(.25,.20),(.268,.40),(.255,.40),(.237,.20),(.205,.025),(0,.025)],M['weave'],Bk,seg=48,cyl=True,center=(bx,by,0))
    ring=[(bx+.268*math.cos(a),by+.268*math.sin(a),.405) for a in np.linspace(0,math.tau,49)]
    tube('TY09_BasketRim',ring,.016,M['bamboo_old'],Bk,8,.2,caps=False)
    for k,a in enumerate(np.linspace(math.radians(200),math.radians(250),7)):   # mended section: fresh strip wrapped over a broken rim
        lashing(f'TY09_Mend{k}',(bx+.268*math.cos(a),by+.268*math.sin(a),.405),(-math.sin(a),math.cos(a),0),.013,2,M['bamboo'],Bk,cord=.0035)
    meta['pieces']['Basket']={'centre':[bx,by],'collision':{'type':'cylinder','radius':.27,'height':.42}}
    # bucket: coopered staves, two taller ear staves with a cross handle, two iron hoops
    ux,uy=.64,-.30;n=18;r0,r1,h=.165,.185,.40
    for i in range(n):
        a0=math.tau*i/n+.004;a1=math.tau*(i+1)/n-.004;ear=i in (0,9);hh=h+(.12 if ear else 0);bm=bmesh.new();vs=[]
        for z,r in ((0,r0),(hh,r1+(r1-r0)*(hh-h)/h if ear else r1)):
            for rr in (r,r-.016):
                for a in (a0,a1):vs.append(bm.verts.new((rr*math.cos(a),rr*math.sin(a),z)))
        q=lambda *ix:bm.faces.new([vs[k] for k in ix])
        q(0,1,5,4);q(3,2,6,7);q(2,0,4,6);q(1,3,7,5);q(4,5,7,6);q(1,0,2,3)
        o=finish(f'TY09_Stave{i}',bm,M['wood'],Bu,.3);bevel(o,.003,1);o.data.transform(Matrix.Translation((ux,uy,0)))
    lathe('TY09_BucketBottom',[(0,.03),(.17,.03),(.17,.05),(0,.05)],M['wood'],Bu,seg=36,center=(ux,uy,0))
    for k,z in enumerate((.07,.33)):
        rz=r0+(r1-r0)*z/h+.004;lathe(f'TY09_Hoop{k}',[(rz,z-.016),(rz+.005,z-.012),(rz+.005,z+.012),(rz,z+.016),(rz-.002,z)],M['iron'],Bu,seg=48,center=(ux,uy,0))
    hy=h+.09;tube('TY09_BucketHandle',[(ux+r1-.005,uy,hy),(ux-r1+.005,uy,hy)],.017,M['wood'],Bu,8)
    meta['pieces']['Bucket']={'centre':[ux,uy],'collision':{'type':'cylinder','radius':.19,'height':.52}}
    # hoe: iron blade resting on the ground at the vat's left front, handle leaning on the vat rim
    B=Vector((vx+.20,vy-.66,.045));C=Vector((vx+.21,vy-.21,.765));t=(C-B).normalized()
    tube('TY09_HoeHandle',[B,C+t*.40],.019,M['wood'],Ho,10,.3,radii=[.021,.018])
    lathe('TY09_HoeSocket',[(.026,0),(.027,.07),(.024,.075),(0,.075)],M['iron'],Ho,seg=16)
    sk=parts[-1];sk.data.transform(t.to_track_quat('Z','Y').to_matrix().to_4x4());sk.data.transform(Matrix.Translation(B-t*.01))
    fwd=Vector((t.x,t.y,0)).normalized();side=Vector((-fwd.y,fwd.x,0))
    top_=B-fwd*.02+Vector((0,0,-.01));tube('TY09_HoeNeck',[B+t*.02,B-fwd*.03+Vector((0,0,-.005)),top_],.011,M['iron'],Ho,8,.2)
    w0,w1,L=.10,.15,.19;bm=bmesh.new()
    pl=[(-w0/2,0),(w0/2,0),(w1/2,L),(-w1/2,L)]
    vs=[bm.verts.new(top_+side*x+(-fwd*.9+Vector((0,0,-.12)))*y) for x,y in pl]
    f=bm.faces.new(vs);r=bmesh.ops.extrude_face_region(bm,geom=[f]);bmesh.ops.translate(bm,verts=[e for e in r['geom'] if isinstance(e,bmesh.types.BMVert)],vec=Vector((0,0,.006)))
    o=finish('TY09_HoeBlade',bm,M['iron'],Ho,.2);bevel(o,.0015,1)
    bc=top_-fwd*.12+Vector((0,0,-.02))
    meta['pieces']['Hoe']={'collision':None,'note':'leans on the vat rim; place after the vat'}
    meta['vat']=(vx,vy);meta['hoe_blade']=list(bc)
    return meta

def RK03(M):
    """官道茶亭 · stone plinth with two steps, four posts, railings on the sides, plank back wall with a tea shelf,
    hipped-gable roof (歇山) of blue-grey roll tiles with upturned corners, moss on the ridges, a repaired corner with newer tiles;
    under the eaves a square tea table, two benches, a charcoal stove with a clay kettle, paper lanterns, rolled bamboo blinds, a signboard without text."""
    T,S,Rf,Fu,L='Timber','Stone','Roof','Furniture','Lamp';meta={'moss_low':.4,'soil':.06,'roof':True}
    rnd=random.Random(3)
    PX,PY=2.3,1.9;FZ=.45      # plinth half extents and floor height
    # plinth: two courses of dressed stones around the edge, flagstone floor on top
    for side in range(4):
        horiz=side%2==0;half=PX if horiz else PY;sgn=-1 if side<2 else 1
        for course,(z0,hh) in enumerate(((0,.22),(.22,.18))):
            x=-half+(rnd.uniform(0,.3) if course else 0)
            while x<half-.02:
                ln=min(rnd.uniform(.55,.85),half-x);c=x+ln/2
                cen=(c,sgn*(PY-.15),z0+hh/2) if horiz else (sgn*(PX-.15),c,z0+hh/2);sz=(ln-.012,.30,hh-.01) if horiz else (.30,ln-.012,hh-.01)
                box(f'RK03_Plinth{side}{course}{x:.2f}',sz,cen,M['plinth'],S,bev=.02,cuts=2,jit=.004,seed=int(x*100)+side*7+course,scale=.8)
                x+=ln
    box('RK03_PlinthCore',(2*PX-.5,2*PY-.5,.38),(0,0,.19),M['plinth'],S,bev=0)
    nx,ny=8,6
    for i in range(nx):
        for j in range(ny):
            w=2*PX/nx;d=2*PY/ny;box(f'RK03_Flag{i}{j}',(w-.012,d-.012,.06),(-PX+w*(i+.5),-PY+d*(j+.5),FZ-.03+rnd.uniform(-.004,.004)),M['plinth'],S,bev=.012,cuts=1,jit=.002,seed=i*9+j,scale=.8)
    for k,(z1,ycut) in enumerate(((.30,PY+.30),(.15,PY+.60))):
        sx=-.85
        for s,w in enumerate((.6,.55,.55)):
            box(f'RK03_Step{k}{s}',(w-.012,.31,z1-.004),(sx+w/2,-(ycut-.155),z1/2),M['plinth'],S,bev=.018,cuts=2,jit=.003,seed=60+k*3+s,scale=.8);sx+=w
    # posts on drum bases
    PX0,PY0=1.9,1.5;ptop=2.80
    for sx in (-1,1):
        for sy in (-1,1):
            lathe(f'RK03_Base{sx}{sy}',[(.17,0),(.19,.03),(.19,.09),(.16,.13),(0,.13)],M['granite'],S,seg=32,center=(sx*PX0,sy*PY0,FZ))
            tube(f'RK03_Post{sx}{sy}',[(sx*PX0,sy*PY0,FZ+.12),(sx*PX0,sy*PY0,ptop)],.11,M['wood'],T,16,.6,radii=[.115,.105])
    # tie beams, plate, bracket blocks, crossbeams, struts, purlins
    for sy in (-1,1):
        beam(f'RK03_TieX{sy}',(-PX0-.2,sy*PY0,2.69),(PX0+.2,sy*PY0,2.69),.14,.22,M['wood'],T)
        beam(f'RK03_PlateX{sy}',(-PX0-.25,sy*PY0,2.83),(PX0+.25,sy*PY0,2.83),.22,.06,M['wood'],T)
    for sx in (-1,1):
        beam(f'RK03_TieY{sx}',(sx*PX0,-PY0-.2,2.69),(sx*PX0,PY0+.2,2.69),.14,.22,M['wood'],T)
        beam(f'RK03_PlateY{sx}',(sx*PX0,-PY0-.25,2.83),(sx*PX0,PY0+.25,2.83),.22,.06,M['wood'],T)
        beam(f'RK03_Cross{sx}',(sx*PX0,-PY0-.05,2.94),(sx*PX0,PY0+.05,2.94),.16,.18,M['wood'],T)
        for yy in (-.75,.75):beam(f'RK03_Strut{sx}{yy}',(sx*PX0,yy,3.03),(sx*PX0,yy,3.24),.10,.10,M['wood'],T,up=(1,0,0))
        beam(f'RK03_KingPost{sx}',(sx*PX0,0,3.03),(sx*PX0,0,3.78),.12,.12,M['wood'],T,up=(1,0,0))
    for yy in (-.75,.75):tube(f'RK03_Purlin{yy}',[(-2.05,yy,3.30),(2.05,yy,3.30)],.075,M['wood'],T,12,.6)
    tube('RK03_RidgePurlin',[(-2.05,0,3.84),(2.05,0,3.84)],.085,M['wood'],T,12,.6)
    for x in (-PX0,-.95,0,.95,PX0):
        for sy in (-1,1):box(f'RK03_Dou{x}{sy}',(.16,.16,.10),(x,sy*PY0,2.91),M['wood'],T,bev=.012)
    for y in (-PY0,0,PY0):
        for sx in (-1,1):box(f'RK03_DouY{y}{sx}',(.16,.16,.10),(sx*PX0,y,2.91),M['wood'],T,bev=.012)
    # carved brackets (雀替) under the front and side tie beams at the posts
    br=[(0,0),(.42,0),(.40,.03),(.30,.05),(.22,.10),(.14,.11),(.08,.16),(.03,.20),(0,.22)]
    for sx in (-1,1):
        for sy in (-1,1):
            o=prism(f'RK03_Que{sx}{sy}x',[(sx*(PX0-.10)-sx*u,2.58-z) for u,z in br],.06,M['wood'],T,.004);o.data.transform(Matrix.Translation((0,sy*PY0,0)))
            o=prism(f'RK03_Que{sx}{sy}y',[(sy*(PY0-.10)-sy*u,2.58-z) for u,z in br],.06,M['wood'],T,.004)
            o.data.transform(Matrix.Rotation(math.pi/2,4,'Z'));o.data.transform(Matrix.Scale(-1,4,(1,0,0)));o.data.transform(Matrix.Translation((sx*PX0,0,0)))
    # railings: sides full, front with the opening at the steps
    def railing(a,b,tag):
        a,b=Vector(a),Vector(b);d=(b-a);L=d.length;t=d.normalized()
        beam(f'RK03_RTop{tag}',a+Vector((0,0,FZ+.55)),b+Vector((0,0,FZ+.55)),.08,.06,M['wood'],T,.01)
        beam(f'RK03_RBot{tag}',a+Vector((0,0,FZ+.10)),b+Vector((0,0,FZ+.10)),.06,.06,M['wood'],T)
        beam(f'RK03_RMid{tag}',a+Vector((0,0,FZ+.42)),b+Vector((0,0,FZ+.42)),.04,.035,M['wood'],T,.004)
        n=max(2,int(L/.16))
        for i in range(1,n):
            p=a+d*(i/n);beam(f'RK03_RBal{tag}{i}',p+Vector((0,0,FZ+.13)),p+Vector((0,0,FZ+.40)),.035,.022,M['wood'],T,.004,up=(t.y,-t.x,0) if abs(t.x)+abs(t.y)>0 else (1,0,0))
    railing((-PX0+.11,-PY0,0),(-.80,-PY0,0),'F1');railing((.80,-PY0,0),(PX0-.11,-PY0,0),'F2')
    for sx in (-1,1):railing((sx*PX0,-PY0+.11,0),(sx*PX0,PY0-.11,0),f'S{sx}')
    for x in (-.80,.80):tube(f'RK03_EndPost{x}',[(x,-PY0,FZ),(x,-PY0,FZ+.62)],.045,M['wood'],T,8,.3)
    # back wall of vertical planks with a tea shelf, jars and cups
    n=22
    for i in range(n):
        x=-PX0+.11+(2*PX0-.22)*(i+.5)/n;box(f'RK03_Plank{i}',((2*PX0-.22)/n-.006,.035,2.58-FZ-.02),(x,PY0+.02,(FZ+2.58)/2),M['planks'],T,bev=.004,scale=.8)
    beam('RK03_WallRailLo',(-PX0,PY0-.02,FZ+.06),(PX0,PY0-.02,FZ+.06),.05,.09,M['wood'],T)
    box('RK03_Shelf',(1.6,.24,.035),(-.7,PY0-.13,1.35),M['wood'],T,bev=.006)
    for sx in (-1.4,-.1):box(f'RK03_ShelfBr{sx}',(.04,.2,.12),(sx,PY0-.11,1.28),M['wood'],T,bev=.004)
    for k,(x,rr,hh,mat) in enumerate(((-1.35,.07,.18,'clay'),(-1.12,.06,.15,'glaze'),(-.92,.075,.20,'clay'),(-.66,.05,.12,'glaze'),(-.45,.065,.16,'clay'),(-.22,.045,.10,'clay'))):
        lathe(f'RK03_Jar{k}',[(rr*.7,0),(rr,hh*.35),(rr*.92,hh*.75),(rr*.55,hh*.88),(rr*.6,hh),(0,hh)],M[mat],Fu,seg=24,center=(x,PY0-.13,1.3675))
    # tea table and two benches
    tx,ty=0,.05
    box('RK03_TableTop',(.92,.92,.055),(tx,ty,FZ+.75-.0275),M['wood'],Fu,bev=.012,scale=.5)
    for sx in (-1,1):
        for sy in (-1,1):box(f'RK03_TLeg{sx}{sy}',(.065,.065,.70),(tx+sx*.39,ty+sy*.39,FZ+.35),M['wood'],Fu,bev=.006)
        beam(f'RK03_TApronX{sx}',(tx-.36,ty+sx*.39,FZ+.65),(tx+.36,ty+sx*.39,FZ+.65),.03,.08,M['wood'],Fu,.004)
        beam(f'RK03_TApronY{sx}',(tx+sx*.39,ty-.36,FZ+.65),(tx+sx*.39,ty+.36,FZ+.65),.03,.08,M['wood'],Fu,.004)
        beam(f'RK03_TStretch{sx}',(tx+sx*.39,ty-.36,FZ+.12),(tx+sx*.39,ty+.36,FZ+.12),.03,.03,M['wood'],Fu,.004)
    for sy in (-1,1):
        by=ty+sy*.74
        box(f'RK03_BenchTop{sy}',(1.30,.30,.05),(tx,by,FZ+.45-.025),M['wood'],Fu,bev=.01,scale=.5)
        for sx in (-1,1):
            box(f'RK03_BLeg{sy}{sx}',(.06,.24,.40),(tx+sx*.52,by,FZ+.20),M['wood'],Fu,bev=.006)
        beam(f'RK03_BStretch{sy}',(tx-.52,by,FZ+.12),(tx+.52,by,FZ+.12),.03,.03,M['wood'],Fu,.004)
    # things on the table: tray, teapot, cups
    box('RK03_Tray',(.36,.24,.02),(tx-.12,ty-.05,FZ+.76),M['bamboo_old'],Fu,bev=.004)
    lathe('RK03_Teapot',[(.0,0),(.045,0),(.065,.03),(.068,.06),(.05,.09),(.03,.095),(.03,.105),(0,.105)],M['clay'],Fu,seg=28,center=(tx-.20,ty-.05,FZ+.77))
    tube('RK03_Spout',[(tx-.14,ty-.05,FZ+.81),(tx-.11,ty-.05,FZ+.85),(tx-.095,ty-.05,FZ+.875)],.008,M['clay'],Fu,6,.1,radii=[.012,.009,.007])
    tube('RK03_PotHandle',[(tx-.255,ty-.05,FZ+.85),(tx-.29,ty-.05,FZ+.82),(tx-.255,ty-.05,FZ+.79)],.008,M['clay'],Fu,6,.1)
    for k,(x,y) in enumerate(((tx-.02,ty-.10),(tx+.05,ty-.01),(tx+.22,ty+.20))):
        lathe(f'RK03_Cup{k}',[(0,0),(.022,0),(.03,.01),(.034,.04),(.03,.04),(.026,.012),(0,.012)],M['glaze'],Fu,seg=20,center=(x,y,FZ+.77 if k<2 else FZ+.75))
    # charcoal stove with a clay kettle beside the table
    sx_,sy_=1.30,.85
    lathe('RK03_Stove',[(.15,0),(.17,.02),(.16,.25),(.14,.33),(.15,.35),(.12,.36),(.11,.30),(0,.30)],M['clay'],Fu,seg=32,center=(sx_,sy_,FZ))
    o=box('RK03_StoveMouth',(.09,.08,.07),(sx_,sy_-.15,FZ+.09),M['charcoal'],Fu,bev=.01)
    lathe('RK03_Ember',[(0,.0),(.07,0),(.06,.03),(0,.035)],M['ember'],L,seg=12,center=(sx_,sy_,FZ+.29))
    lathe('RK03_Kettle',[(0,0),(.07,0),(.10,.04),(.105,.08),(.08,.13),(.04,.15),(.045,.17),(0,.17)],M['clay'],Fu,seg=28,center=(sx_,sy_,FZ+.35))
    tube('RK03_KettleSpout',[(sx_+.09,sy_,FZ+.43),(sx_+.15,sy_,FZ+.48),(sx_+.17,sy_,FZ+.52)],.012,M['clay'],Fu,6,.1,radii=[.016,.012,.009])
    tube('RK03_KettleBail',[(sx_-.07,sy_,FZ+.47),(sx_-.04,sy_,FZ+.58),(sx_+.04,sy_,FZ+.58),(sx_+.07,sy_,FZ+.47)],.006,M['bamboo_old'],Fu,6,.1)
    tube('RK03_Fan',[(sx_-.20,sy_-.02,FZ+.02),(sx_-.17,sy_-.05,FZ+.30)],.006,M['bamboo'],Fu,5,.1)
    # rolled bamboo blinds under the side tie beams, hanging cords
    for sx in (-1,1):
        tube(f'RK03_Blind{sx}',[(sx*(PX0+.02),-PY0+.25,2.50),(sx*(PX0+.02),PY0-.25,2.50)],.065,M['bamboo'],Fu,14,.15)
        for yy in (-.9,.9):tube(f'RK03_BlindCord{sx}{yy}',[(sx*(PX0+.02),yy,2.58),(sx*(PX0+.1),yy,2.50),(sx*(PX0+.02),yy,2.42),(sx*(PX0-.06),yy,2.50),(sx*(PX0+.02),yy,2.58)],.007,M['hemp'],Fu,5,.1)
    # signboard without text under the front tie beam
    box('RK03_Sign',(1.10,.05,.36),(0,-PY0-.10,2.32),M['planks'],T,bev=.012,scale=.6)
    box('RK03_SignFrame',(1.18,.035,.44),(0,-PY0-.075,2.32),M['wood'],T,bev=.01)
    for x in (-.45,.45):tube(f'RK03_SignCord{x}',[(x,-PY0-.08,2.58),(x,-PY0-.10,2.50)],.008,M['hemp'],T,5,.1)
    # paper lanterns at the four corners under the eaves
    for k,(x,y) in enumerate(((-2.18,-1.78),(2.18,-1.78),(-2.18,1.78),(2.18,1.78))):
        zc=2.30
        tube(f'RK03_LCord{k}',[(x,y,2.95),(x,y,zc+.22)],.006,M['hemp'],L,5,.1)
        lathe(f'RK03_LCap{k}',[(0,0),(.08,0),(.08,.035),(0,.035)],M['lacquer_red'],L,seg=20,center=(x,y,zc+.18))
        lathe(f'RK03_LCapB{k}',[(0,0),(.08,0),(.08,.035),(0,.035)],M['lacquer_red'],L,seg=20,center=(x,y,zc-.215))
        prof=[(.075,-.18)]+[(.075+.085*math.sin(math.pi*t)**.8,-.18+.36*t) for t in np.linspace(.05,.95,10)]+[(.075,.18)]
        lathe(f'RK03_Lantern{k}',prof,M['lantern'],L,seg=24,cyl=True,center=(x,y,zc))
        tube(f'RK03_Tassel{k}',[(x,y,zc-.215),(x,y,zc-.40)],.012,M['lacquer_red'],L,6,.1,radii=[.006,.016])
    # ---- roof: hipped gable. front/back gable slopes over |x|<=XG, hip skirts beyond, gable walls at x=±XG
    HW,HD,ZE,ZR,P_,U=2.90,2.40,2.80,3.94,1.55,.30;XG=1.98;DXG=HW-XG;PIT=.22
    def roll(c):   # roll-tile rows: rounded rolls over a shallow pan channel
        t=(c/PIT)%1;return .055*math.sqrt(max(0,1-((t-.5)/.2)**2))+.012*math.cos(math.tau*t)
    def bump(x,y,dx,dy):
        e=min(dx,dy);fade=min(1,e/.04)
        return roll(x if dy<=dx else y)*fade
    def bump_fb(x,y,dx,dy):return roll(x)*min(1,dy/.04)
    o,zf=hip_surface('RK03_RoofFront',HW,HD,ZE,ZR,P_,U,M['tile'],Rf,step=.025,thick=.12,bump=bump_fb,region=(-XG,XG,-HD,0),xs=lambda x,y:HD-abs(y))
    o,_=hip_surface('RK03_RoofBack',HW,HD,ZE,ZR,P_,U,M['tile'],Rf,step=.025,thick=.12,bump=bump_fb,region=(-XG,XG,0,HD),xs=lambda x,y:HD-abs(y))
    for sx in (-1,1):
        reg=(XG,HW,-HD,HD) if sx>0 else (-HW,-XG,-HD,HD)
        hip_surface(f'RK03_Skirt{sx}',HW,HD,ZE,ZR,P_,U,M['tile'],Rf,step=.025,thick=.12,bump=bump,region=reg)
    F=lambda x,y,d:zf(x,y,d)
    # main ridge with curled ends
    zr=F(0,0,HD)
    box('RK03_Ridge',(2*XG+.30,.20,.24),(0,0,zr+.10),M['tile'],Rf,bev=.02,cuts=3,scale=.5)
    box('RK03_RidgeCap',(2*XG+.36,.24,.05),(0,0,zr+.235),M['tile'],Rf,bev=.015,scale=.5)
    for sx in (-1,1):
        x0=sx*(XG+.15);curl=[(x0,0,zr+.05),(x0+sx*.06,0,zr+.25),(x0+sx*.02,0,zr+.36),(x0-sx*.09,0,zr+.38),(x0-sx*.13,0,zr+.31)]
        tube(f'RK03_RidgeEnd{sx}',curl,.075,M['tile'],Rf,10,.3,radii=[.11,.10,.08,.06,.04])
    # gable rake ridges, gable walls (vertical planks) and a hanging-fish board under each apex
    for sx in (-1,1):
        xr=sx*(XG+.04);pts=[(xr,y,F(xr,y,HD-abs(y))+.07) for y in np.linspace(-(HD-DXG),HD-DXG,25)]
        tube(f'RK03_Rake{sx}',pts,.065,M['tile'],Rf,10,.4)
        poly=[(y,F(XG,y,HD-abs(y))-.10) for y in np.linspace(-(HD-DXG)+.05,(HD-DXG)-.05,21)]
        zbase=F(XG,0,DXG)-.02;poly=[(poly[0][0],zbase)]+poly+[(poly[-1][0],zbase)]
        o=prism(f'RK03_Gable{sx}',[(y,z) for y,z in poly],.05,M['planks'],T,.004);o.data.transform(Matrix.Rotation(-math.pi/2,4,'Z'));o.data.transform(Matrix.Translation((sx*XG,0,0)))
        fish=[(-.10,0),(.10,0),(.08,-.18),(.03,-.30),(0,-.36),(-.03,-.30),(-.08,-.18)]
        o=prism(f'RK03_Fish{sx}',fish,.04,M['wood'],T,.004);o.data.transform(Matrix.Rotation(-math.pi/2,4,'Z'));o.data.transform(Matrix.Translation((sx*(XG+.04),0,zr-.12)))
    # hip ridges on the skirts with upturned ends
    for sx in (-1,1):
        for sy in (-1,1):
            pts=[]
            for t in np.linspace(-.07,DXG-.02,22):
                x=sx*(HW-max(t,0));y=sy*(HD-max(t,0));z=F(x,y,max(t,0))+.075+(.13*(-t/.07)**1.5 if t<0 else 0)
                if t<0:x=sx*(HW-t*.5);y=sy*(HD-t*.5)
                pts.append((x,y,z))
            tube(f'RK03_Hip{sx}{sy}',pts,.06,M['tile'],Rf,10,.4,radii=[.035+.025*min(1,i/4) for i in range(len(pts))])
    # eave tile ends (瓦當) and round rafter ends under the eaves
    for x in np.arange(-HW+PIT/2,HW,PIT):
        if abs(x)>HW-.12:continue
        for sy in (-1,1):
            z=F(x,sy*HD,0)+.03;c=lathe(f'RK03_Wd{x:.2f}{sy}',[(0,0),(.042,0),(.046,.006),(.046,.022),(.04,.026),(0,.026)],M['tile'],Rf,seg=14,smooth=False)
            c.data.transform(Matrix.Rotation(-sy*math.pi/2,4,'X'));c.data.transform(Matrix.Translation((x,sy*(HD+.0),z)))
    for y in np.arange(-HD+PIT/2,HD,PIT):
        if abs(y)>HD-.12:continue
        for sx in (-1,1):
            z=F(sx*HW,y,0)+.03;c=lathe(f'RK03_Wds{y:.2f}{sx}',[(0,0),(.042,0),(.046,.006),(.046,.022),(.04,.026),(0,.026)],M['tile'],Rf,seg=14,smooth=False)
            c.data.transform(Matrix.Rotation(sx*math.pi/2,4,'Y'));c.data.transform(Matrix.Translation((sx*HW,y,z)))
    for x in np.arange(-PX0,PX0+.01,.30):
        for sy in (-1,1):
            a=(x,sy*(PY0+.05),2.90);b=(x,sy*(HD-.12),F(x,sy*(HD-.12),.12)-.14)
            tube(f'RK03_Rafter{x:.2f}{sy}',[a,b],.035,M['wood'],T,8,.3)
    for y in np.arange(-PY0,PY0+.01,.30):
        for sx in (-1,1):
            a=(sx*(PX0+.05),y,2.90);b=(sx*(HW-.12),y,F(sx*(HW-.12),y,.12)-.14)
            tube(f'RK03_RafterS{y:.2f}{sx}',[a,b],.035,M['wood'],T,8,.3)
    meta['newtiles']=(1.9,-1.6)   # repaired corner (front right, seen from the road)
    meta['zf']=None
    return meta

PROPS={'RK03':RK03,'G01':G01,'TY04':TY04,'TY08':TY08,'TY09':TY09}
GROUP_RES={'RK03':{'Roof':2048,'Timber':2048,'Stone':2048,'Furniture':1024,'Lamp':512},
           'G01':{'Stone':2048,'Lamp':1024},'TY04':{'Stone':2048,'Lamp':1024},
           'TY08':{'Frame':2048,'Herbs':1024},'TY09':{'Vat':1024,'Basket':1024,'Hoe':512,'Bucket':1024}}
MOSS={'Stone':.55,'Roof':.45,'Frame':.15,'Vat':.12,'Bucket':.08,'Basket':.05,'Timber':.04}

# ---------------- collision ----------------
def collision(pid,meta,dims):
    """simple static collider meshes joined into <ID>_Collision; primitive list for model_info"""
    prims=[]
    def add(kind,size,center):prims.append({'type':kind,'size':[round(v,3) for v in size],'center':[round(v,3) for v in center]})
    if pid=='RK03':
        add('box',(4.6,3.8,.45),(0,0,.225))
        add('box',(1.7,.30,.30),(0,-2.05,.15));add('box',(1.7,.30,.15),(0,-2.35,.075))
        for sx in (-1,1):
            for sy in (-1,1):add('box',(.24,.24,2.35),(sx*1.9,sy*1.5,.45+1.175))
            add('box',(.1,3.0,.60),(sx*1.9,0,.75))
        for x0,x1 in ((-1.79,-.80),(.80,1.79)):add('box',(x1-x0,.1,.60),((x0+x1)/2,-1.5,.75))
        add('box',(3.8,.12,2.13),(0,1.52,.45+1.065))
        add('box',(.92,.92,.75),(0,.05,.45+.375))
        for sy in (-1,1):add('box',(1.3,.30,.45),(0,.05+sy*.74,.45+.225))
        add('box',(.36,.36,.36),(1.30,.85,.45+.18))
    elif pid in ('G01','TY04'):
        w=.6 if pid=='G01' else .8;add('box',(w,w,dims[2]),(0,0,dims[2]/2))
    elif pid=='TY08':
        for sx in (-1,1):add('box',(.12,.80,1.78),(sx*.91,0,.89))
        add('box',(1.9,.14,.10),(0,0,1.10))
    elif pid=='TY09':
        for k,v in meta['pieces'].items():
            c=v.get('collision')
            if c:prims.append({'type':'cylinder','piece':k,'radius':c['radius'],'height':c['height'],'center':[v['centre'][0],v['centre'][1],c['height']/2]})
    objs=[]
    for p in prims:
        if p['type']=='box':bm=box_bm(p['size'],p['center'])
        else:
            bm=bmesh.new();bmesh.ops.create_cone(bm,cap_ends=True,segments=12,radius1=p['radius'],radius2=p['radius'],depth=p['height'])
            bmesh.ops.translate(bm,verts=bm.verts,vec=Vector(p['center']))
        me=bpy.data.meshes.new('col');bm.to_mesh(me);bm.free();o=bpy.data.objects.new('col',me);bpy.context.scene.collection.objects.link(o);objs.append(o)
    c=join(objs,f'{pid}_Collision');c.data.name=c.name;c.hide_render=True;c.display_type='WIRE'
    return c,prims

# ---------------- bake / LOD / export ----------------
def gpu(sc):
    try:
        pr=bpy.context.preferences.addons['cycles'].preferences
        for t in ('OPTIX','CUDA'):
            try:pr.compute_device_type=t
            except TypeError:continue
            pr.get_devices();ds=[d for d in pr.devices if d.type==t]
            if ds:
                for d in pr.devices:d.use=d.type==t
                sc.cycles.device='GPU';return t
    except Exception as e:print('GPU unavailable',e)
    sc.cycles.device='CPU';return 'CPU'
def run(pid):
    sel_txt=(REF/pid/'prompt.txt').read_text(encoding='utf-8')
    assert '選用：' in sel_txt and (REF/pid/f'{pid}-cand-1.png').stat().st_size>10000,f'{pid}: pick a saved AI three-view before modelling'
    bpy.ops.wm.read_factory_settings(use_empty=True);parts.clear();GLOW.clear()
    sc=bpy.context.scene;sc.unit_settings.system='METRIC';sc.render.engine='CYCLES';dev=gpu(sc);sc.cycles.samples=16;sc.render.bake.margin=12
    M=make_sources();meta=PROPS[pid](M)
    def sel(*obs):
        bpy.ops.object.select_all(action='DESELECT')
        for o in obs:o.select_set(True)
        bpy.context.view_layer.objects.active=obs[0]
    pts=np.array([(o.matrix_world@v.co)[:] for o in parts for v in o.data.vertices]);lo,hi=pts.min(0),pts.max(0)
    off=Vector((-(lo[0]+hi[0])/2,-(lo[1]+hi[1])/2,-lo[2]))
    for o in parts:o.data.transform(Matrix.Translation(off))
    meta['offset']=np.array(off[:])
    srcparts=list(parts);groups={}
    for o in srcparts:groups.setdefault(o['grp'],[]).append(o)
    G={}
    for g,objs in groups.items():
        cp=[]
        for o in objs:d=o.copy();d.data=o.data.copy();sc.collection.objects.link(d);cp.append(d)
        sel(*cp);bpy.ops.object.join();o=bpy.context.object;o.name=o.data.name=f'{pid}_{g}_LOD0'
        bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.triangulate(bm,faces=bm.faces);bm.to_mesh(o.data);bm.free()
        for u in [u for u in o.data.uv_layers if u.name!='Tiled']:o.data.uv_layers.remove(u)
        bu=o.data.uv_layers.new(name='Bake');o.data.uv_layers.active=bu;sel(o)
        res=GROUP_RES[pid][g];mg=6/res
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(55),island_margin=mg,area_weight=0,scale_to_bounds=False);bpy.ops.uv.pack_islands(margin=mg,rotate=True)
        bpy.ops.object.mode_set(mode='OBJECT');G[g]=o
    for o in sc.objects:o.hide_render=o not in G.values()
    tex={}
    for g,o in G.items():
        RES=GROUP_RES[pid][g];mats=list(o.data.materials)
        def target(name,data=False):
            im=bpy.data.images.new(name,RES,RES,alpha=False,float_buffer=data)
            for m in mats:
                nt=m.node_tree;t=nt.nodes.get('BAKE_TARGET') or nt.nodes.new('ShaderNodeTexImage');t.name='BAKE_TARGET';t.image=im;nt.nodes.active=t
            return im
        def bake(name,type,data=False,**kw):
            im=target(name,data);sel(o);bpy.ops.object.bake(type=type,**kw);a=np.array(im.pixels[:],dtype=np.float32).reshape(RES,RES,4);bpy.data.images.remove(im);return a
        def emit(fn):
            saved=[]
            for m in mats:
                nt=m.node_tree;out=next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL');old=out.inputs['Surface'].links[0].from_socket
                em=nt.nodes.new('ShaderNodeEmission');fn(nt,m,em);nt.links.new(em.outputs[0],out.inputs['Surface']);saved.append((nt,out,old,em))
            return saved
        def restore(s):
            for nt,out,old,em in s:nt.links.new(old,out.inputs['Surface']);nt.nodes.remove(em)
        alb=bake('alb','DIFFUSE',pass_filter={'COLOR'});sc.cycles.samples=96;ao=bake('ao','AO',True)[...,0];sc.cycles.samples=16
        rough=bake('rough','ROUGHNESS',True)[...,0];nrm=bake('nrm','NORMAL',True,normal_space='TANGENT');onrm=bake('onrm','NORMAL',True,normal_space='OBJECT')[...,:3]*2-1
        s=emit(lambda nt,m,em:em.inputs['Color'].__setattr__('default_value',(GLOW.get(m.name,(0,0))[0],)*3+(1,)));met=bake('met','EMIT',True)[...,0];restore(s)
        s=emit(lambda nt,m,em:em.inputs['Color'].__setattr__('default_value',(GLOW.get(m.name,(0,0))[1],)*3+(1,)));glow=bake('glow','EMIT',True)[...,0];restore(s)
        def edges(nt,m,em):
            gg=nt.nodes.new('ShaderNodeNewGeometry');nt.links.new(gg.outputs['Pointiness'],em.inputs['Color'])
        s=emit(edges);pt=bake('edge','EMIT',True)[...,0];restore(s);edge=np.clip((pt-.52)/.07,0,1);cav=np.clip((.485-pt)/.05,0,1)
        s=emit(lambda nt,m,em:nt.links.new(nt.nodes.new('ShaderNodeNewGeometry').outputs['Position'],em.inputs['Color']));pos=bake('pos','EMIT',True)[...,:3];restore(s)
        filled=np.abs(pos).sum(2)>1e-7;px,py,pz=pos[...,0],pos[...,1],pos[...,2];H=hi[2]-lo[2]
        # painterly finish: cool blue-violet shade in occlusion, warm light on top, worn warm edges
        cool=np.array([.30,.32,.46]);col=alb[...,:3]*(.42+.58*ao[...,None])+(1-ao[...,None])*cool*.12
        col=col*(1-.45*cav[...,None])+cav[...,None]*np.array([.10,.09,.07])*.45
        col=col*(1+.08*np.clip(pz/H,0,1)[...,None]*np.array([1.0,.85,.6]))
        wear=np.clip(edge,0,1)[...,None]*(met[...,None]<.1)*(glow[...,None]<.5);col=np.clip(col*(1+.35*wear)+wear*np.array([.06,.05,.03]),0,1)
        # soot inside lamp chambers
        for (cx,cy,cz,hw_,hh_) in meta.get('soot',[]):
            q=pos-meta['offset'];inside=filled&(np.abs(q[...,0]-cx)<hw_)&(np.abs(q[...,1]-cy)<hw_)&(np.abs(q[...,2]-cz)<hh_)
            k=np.clip((q[...,2]-cz+hh_*.2)/(hh_*1.2),0,1)*inside*(1-.6*(glow>.5))*(1-np.clip(np.abs(q[...,0])+np.abs(q[...,1])-hw_*1.6,0,1))
            col=col*(1-.75*k[...,None])+np.array([.05,.045,.04])*.75*k[...,None]
        # moss on up-facing joints near the ground (and on roof ridges / tile channels)
        mn=np.clip((onrm[...,2]-.35)/.5,0,1)
        n1=np.sin(px*7.3+np.sin(py*5.1+pz*2.3)*1.7)*np.sin(py*6.7+np.sin(pz*4.3+px*2.1)*1.9);n2=np.sin(px*23.1+np.sin(py*19.7)*1.3)*np.sin(pz*21.3+py*13.9)
        noise=np.clip(.5+.42*n1+.18*n2,0,1)
        amt=MOSS.get(g,0)
        if amt:
            low=np.clip(1-pz/.5,0,1)*meta.get('moss_low',0)
            highm=np.clip((pz-(meta.get('top',H)*.80))/(H*.25),0,1)*.6 if g in ('Stone','Roof') else 0
            ridge=(np.clip((pz-3.7)/.4,0,1)+np.clip((1-ao)*2-.6,0,1)*.5) if g=='Roof' else 0
            creep=np.clip(1-pz/.30,0,1)*meta.get('moss_low',0)*.9+cav*.5
            m=np.clip((mn*(low+highm+ridge+.15)+creep)*amt*2*np.clip((noise-.38)*3.5,0,1),0,1)*filled*(glow<.5)
            mcol=np.array([.27,.36,.13])*(1-m[...,None]*.0)+np.array([.10,.10,.04])*noise[...,None]
            col=col*(1-m[...,None])+mcol*m[...,None];rough=np.clip(rough+.15*m,0,1)
        # roof: a repaired corner with newer, cleaner tiles
        if g=='Roof' and meta.get('newtiles'):
            q=pos-meta['offset'];k=filled&(q[...,0]>1.98)&(q[...,0]<2.75)&(q[...,1]<-1.75)&(onrm[...,2]>.15)
            col=np.where(k[...,None],alb[...,:3]*.25*(.55+.45*ao[...,None])+np.array([.33,.42,.50])*(.45+.55*ao[...,None])*.75,col);rough=np.where(k,.55,rough)
        # soil and water stains low on everything that stands on the ground
        if meta.get('soil'):
            s_=np.clip((meta['soil']-pz)/meta['soil'],0,1)*filled*(met<.5);col=col*(1-.45*s_[...,None])+np.array([.26,.20,.14])*.45*s_[...,None]
        if g=='Vat':   # unglazed clay foot below a dripping glaze line, water stains under the rim
            q=pos-meta['offset'];vx,vy=meta['vat'];ang=np.arctan2(q[...,1]-vy,q[...,0]-vx);line=.24+.035*np.sin(ang*7)+.05*np.clip(np.sin(ang*13),0,1)**6
            outer=filled&(np.hypot(q[...,0]-vx,q[...,1]-vy)>.27)&(glow<.5)
            raw=outer&(q[...,2]<line);col=np.where(raw[...,None],np.array([.46,.30,.20])*(.75+.25*ao[...,None]),col);rough=np.where(raw,.92,rough)
            ln=.72-.22*np.clip(np.sin(ang*3.3+1)*np.sin(ang*1.7),0,1);st=outer&(q[...,2]>ln)&(q[...,2]<.735)&(np.sin(ang*9+np.sin(ang*4)*2.5)>.55);col=np.where(st[...,None],col*.86+np.array([.42,.40,.34])*.06,col)
        if g=='Hoe':
            q=pos-meta['offset'];b=np.array(meta['hoe_blade']);d=np.linalg.norm(q-b,axis=2);k=filled&(met>.1)&(d<.20)&(q[...,2]<.12)
            col=np.where(k[...,None],col*.4+np.array([.32,.25,.17])*.6,col);rough=np.where(k,.95,rough)
        def save(name,rgba,data=False):
            im=bpy.data.images.new(name,RES,RES,alpha=True)
            if data:im.colorspace_settings.name='Non-Color'
            im.pixels.foreach_set(np.ascontiguousarray(rgba,dtype=np.float32).ravel());im.filepath_raw=str(TEX/f'{name}.png');im.file_format='PNG';im.save();return im
        one=np.ones((RES,RES),np.float32);key=f'{pid}_{g}'
        T={'alb':save(f'{key}_Albedo',np.dstack([np.clip(col,0,1),one])),'nrm':save(f'{key}_Normal',nrm,True),
           'orm':save(f'{key}_ORM',np.dstack([ao,rough,met,one]),True)}
        save(f'{key}_MaskURP',np.dstack([met,ao,0*one,1-rough]),True)
        if glow.max()>.5:   # lamp paper / embers: emission colour = warm light through the paper albedo
            em=np.clip(alb[...,:3]*np.array([1.25,.95,.62])*(glow[...,None]>.5),0,1);T['emi']=save(f'{key}_Emission',np.dstack([em,one]))
        tex[g]=T
    # final materials, LODs, root, lamp driver
    root=bpy.data.objects.new(f'{pid}_GroundOrigin',None);sc.collection.objects.link(root)
    if meta.get('lamp'):root['glow_level']=0 if pid=='TY04' else 1
    lods=[]
    for g,o in G.items():
        T=tex[g];fm=bpy.data.materials.new(f'{pid}_{g}');fm.use_nodes=True;nt=fm.node_tree;bs=nt.nodes['Principled BSDF']
        def tn(im):t=nt.nodes.new('ShaderNodeTexImage');t.image=im;return t
        nt.links.new(tn(T['alb']).outputs['Color'],bs.inputs['Base Color'])
        nmn=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(tn(T['nrm']).outputs['Color'],nmn.inputs['Color']);nt.links.new(nmn.outputs['Normal'],bs.inputs['Normal'])
        sp=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(tn(T['orm']).outputs['Color'],sp.inputs['Color']);nt.links.new(sp.outputs['Green'],bs.inputs['Roughness']);nt.links.new(sp.outputs['Blue'],bs.inputs['Metallic'])
        if 'emi' in T:
            nt.links.new(tn(T['emi']).outputs['Color'],bs.inputs['Emission Color'])
            if pid in ('G01','TY04'):   # lamp state on the root: G01 0 = unlit / 1 = lit; TY04 glow_level 0..4
                fc=bs.inputs['Emission Strength'].driver_add('default_value');dr=fc.driver;dr.type='SCRIPTED';v=dr.variables.new();v.name='lv'
                v.targets[0].id=root;v.targets[0].data_path='["glow_level"]'
                dr.expression='1.2*lv' if pid=='G01' else '0.2333*lv+0.1167*lv*lv'
            else:bs.inputs['Emission Strength'].default_value=1.0
        group=[o]
        for L,ratio in ((1,.5),(2,.15)):
            d=o.copy();d.data=o.data.copy();sc.collection.objects.link(d);d.name=d.data.name=f'{pid}_{g}_LOD{L}'
            m=d.modifiers.new('d','DECIMATE');m.ratio=ratio;m.use_collapse_triangulate=True;sel(d);bpy.ops.object.modifier_apply(modifier='d');group.append(d)
        for d in group:
            uvs=d.data.uv_layers;uvs.remove(uvs['Tiled']);uvs['Bake'].name='UVMap';d.data.materials.clear();d.data.materials.append(fm);d.hide_render=not d.name.endswith('LOD0');d.parent=root
        lods.append(group)
    pts=np.array([v.co[:] for gr in lods for v in gr[0].data.vertices]);lo,hi=pts.min(0),pts.max(0);dims=hi-lo
    col,prims=collision(pid,meta,dims);col.parent=root
    if meta.get('light'):
        ls=bpy.data.objects.new(f'{pid}_LightSocket',None);sc.collection.objects.link(ls);ls.location=Vector(meta['light'])+Vector(meta['offset']);ls.parent=root
    lim=LIMITS[pid];fits=bool(all(dims[i]<=lim[i]+1e-6 for i in range(3)))
    src=bpy.data.collections.new(f'{pid}_SourceParts');sc.collection.children.link(src)
    for o in srcparts:
        for c in list(o.users_collection):c.objects.unlink(o)
        src.objects.link(o);o.hide_render=True;o.hide_set(True)
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/f'{pid}.blend'),compress=True)
    if 'glow_level' in root:root['glow_level']=4 if pid=='TY04' else 1;bpy.context.view_layer.update()   # export carries the emissive texture at full strength
    extra=[o for o in sc.objects if o.name.endswith('LightSocket')]
    sel(root,*[gr[0] for gr in lods],*extra);bpy.ops.export_scene.gltf(filepath=str(OUT/f'{pid}.glb'),use_selection=True,export_format='GLB',export_apply=True)
    sel(root,*[d for gr in lods for d in gr],col,*extra);bpy.ops.export_scene.fbx(filepath=str(OUT/f'{pid}.fbx'),use_selection=True,object_types={'MESH','EMPTY'},global_scale=1.0,apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_ALL',bake_space_transform=True,axis_forward='-Z',axis_up='Y',use_mesh_modifiers=True,mesh_smooth_type='FACE',
        use_tspace=True,add_leaf_bones=False,bake_anim=False,path_mode='RELATIVE',embed_textures=False)
    tri=lambda o:sum(len(p.vertices)-2 for p in o.data.polygons)
    info={'id':pid,'device':dev,'dimensions_xyz_m':[round(float(x),3) for x in dims],'size_limit_m':lim,'fits_limit':fits,
          'groups':{g:{'material':f'{pid}_{g}','texture_px':GROUP_RES[pid][g],'triangles':[tri(d) for d in gr],'emission':'emi' in tex[g]} for g,gr in zip(G,lods)},
          'triangles_total':[sum(tri(gr[i]) for gr in lods) for i in range(3)],'source_parts':len(srcparts),
          'reference':f'art/references/{PKG}/{pid}/prompt.txt','origin':'footprint centre, bottom z = 0, front = -Y (Blender) / +Z glTF',
          'textures':'per group: Albedo / Normal / MaskURP (R metal, G AO, A smoothness) / ORM (glTF) [+ Emission]','collision':{'mesh':f'{pid}_Collision','primitives':prims}}
    for k in ('crescent','states','pieces'):
        if k in meta:info[k]=meta[k]
    if meta.get('light'):info['light_socket']=[round(float(v),3) for v in Vector(meta['light'])+Vector(meta['offset'])]
    print('DAY12_DONE',json.dumps(info,ensure_ascii=False));return info
ids=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else list(PROPS)
infos=[run(i) for i in ids]
mf=OUT/'model_info.json';old=json.loads(mf.read_text(encoding='utf-8')) if mf.exists() else {}
old.update({i['id']:i for i in infos});mf.write_text(json.dumps(old,ensure_ascii=False,indent=1),encoding='utf-8')
