"""Q-version character kit v004 for QCharacters17 (user revision of v003, 2026-10-24): darker black hair, a larger mouth
painted onto the face like the eyes (mouth_decals), curved side locks for the women (side_locks curve=True). Else as v003.
v003: v002 eyes rebuilt as flat surface decals; see eye_decals. v002 notes follow.
Q-version character kit v002 for QCharacters17 (v001 kit: qchar17.py, kept for rebuilding v001).
User revisions (2026-10-24, reference: an anime chibi figure): anime eyes with whites, coloured two-tone irises and a heavy
upper lash line, open smiling mouth; fuller layered hair with shoulder-length side locks and an ahoge; about 2.5 heads with
slimmer limbs and visible legs (shorter robes, leg wraps); props gripped by a closed hand with the handle through the palm.
Units metres, front -Y, origin bottom centre, A-pose (not T-pose: the user kept A). Palette follows SectCore04.
"""
import bpy,bmesh,math
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree

# ------------------------------------------------------------------ materials
def mat(name,c,rough=.75,spec=.25,sss=0.):
    m=bpy.data.materials.get(name)
    if m:return m
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*c,1)
    b=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value=(*c,1);b.inputs['Roughness'].default_value=rough;b.inputs['Specular IOR Level'].default_value=spec
    if sss:
        b.inputs['Subsurface Weight'].default_value=sss;b.inputs['Subsurface Radius'].default_value=(.6,.25,.15)
    return m

COLORS={'skin':(.86,.60,.47),'skin_tan':(.74,.47,.33),'blush':(.93,.42,.42),'sclera':(.92,.92,.93),'pupil':(.025,.015,.015),
        'eye_hi':(1.,1.,1.),'mouth':(.42,.12,.10),'mouth_in':(.30,.05,.05),'tongue':(.85,.35,.35),'lash':(.03,.02,.02),
        'iris_amber':(.32,.14,.03),'iris_amber_l':(.80,.48,.12),'iris_blue':(.07,.16,.38),'iris_blue_l':(.32,.55,.85),
        'iris_jade':(.03,.20,.14),'iris_jade_l':(.22,.62,.45),'iris_brown':(.14,.06,.03),'iris_brown_l':(.45,.25,.10),
        'iris_grey':(.12,.14,.18),'iris_grey_l':(.45,.52,.62),'iris_plum':(.22,.06,.14),'iris_plum_l':(.62,.30,.48),
        'iris_green':(.06,.18,.05),'iris_green_l':(.35,.58,.20),'pupil_shade':(.03,.025,.035),
        'hair_black':(.014,.011,.014),'hair_brown':(.12,.06,.03),'hair_white':(.80,.80,.76),'hair_grey':(.45,.44,.42),
        'teal':(.06,.24,.22),'teal_light':(.18,.42,.38),'white_robe':(.78,.78,.72),'cream':(.70,.64,.50),'jade':(.10,.36,.28),
        'timber':(.16,.065,.028),'leather':(.20,.09,.035),'ochre':(.45,.26,.07),'plum':(.30,.12,.18),'sage':(.30,.40,.24),
        'stone':(.36,.37,.33),'charcoal':(.08,.08,.08),'iron':(.10,.11,.11),'brass':(.40,.28,.08),'straw':(.55,.40,.18),
        'rust':(.40,.12,.06),'indigo':(.06,.09,.20),'pants_dark':(.07,.08,.08),'shoe':(.06,.04,.03),'red':(.55,.08,.06),
        'herb':(.10,.30,.08),'wood':(.30,.16,.07),'wrap':(.74,.70,.60)}
def M(key):
    c=COLORS[key] if not key.endswith('_d') else tuple(x*.45 for x in COLORS[key[:-2]]);eye=key.startswith(('iris','eye','pupil','sclera'))
    rough=.15 if eye else {'hair_black':.6,'hair_brown':.6,'hair_white':.6,'hair_grey':.6,'jade':.35,'iron':.4,'brass':.35,'tongue':.4,'mouth_in':.5}.get(key,.75)
    spec=.35 if eye else (.12 if key.startswith('hair') else .2)   # low hair sheen: 0.35 turned black hair grey under the studio lights
    if key=='hair_black':rough,spec=.42,.05   # v004: still grey in v003; a tighter, fainter highlight leaves the rest of the hair dark
    m=mat('Q17v4_'+key,c,rough,spec,.12 if key.startswith('skin') else 0.)
    if eye or key=='lash':   # painted look: matte with a little self-light so the decals do not shade like solids
        bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Roughness'].default_value=.9;bs.inputs['Specular IOR Level'].default_value=.05
        bs.inputs['Emission Color'].default_value=(*c,1);bs.inputs['Emission Strength'].default_value=.6 if key=='eye_hi' else .25
    metal={'iron':.6,'brass':.7}.get(key,0.)
    if metal:next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Metallic'].default_value=metal
    return m

# ------------------------------------------------------------------ geometry kit
class Kit:
    def __init__(s,coll,root):s.coll,s.root,s.count=coll,root,0
    def obj(s,name,bm,key,smooth=True,group=None):
        me=bpy.data.meshes.new(name);bm.to_mesh(me);bm.free();me.materials.append(M(key))
        for p in me.polygons:p.use_smooth=smooth
        o=bpy.data.objects.new(name,me);s.coll.objects.link(o);o.parent=s.root;s.count+=1
        if group:o['part']=group
        return o
    def ellipsoid(s,name,c,r,key,rot=None,segs=32,rings=16,group=None):
        bm=bmesh.new();m=Matrix.Translation(Vector(c))@(rot or Matrix.Identity(3)).to_4x4()@Matrix.Diagonal((*r,1))
        bmesh.ops.create_uvsphere(bm,u_segments=segs,v_segments=rings,radius=1,matrix=m)
        return s.obj(name,bm,key,group=group)
    def lathe(s,name,prof,key,segs=36,c=(0,0),group=None):
        """prof: list of (z, rx, ry) bottom->top; closed with centre caps."""
        bm=bmesh.new();rings=[]
        for z,rx,ry in prof:rings.append([bm.verts.new((c[0]+rx*math.cos(a),c[1]+ry*math.sin(a),z)) for a in (i*2*math.pi/segs for i in range(segs))])
        for a,b in zip(rings,rings[1:]):
            for i in range(segs):bm.faces.new((a[i],a[(i+1)%segs],b[(i+1)%segs],b[i]))
        for ring,z,flip in ((rings[0],prof[0][0],True),(rings[-1],prof[-1][0],False)):
            ctr=bm.verts.new((c[0],c[1],z))
            for i in range(segs):bm.faces.new((ring[(i+1)%segs],ring[i],ctr) if flip else (ring[i],ring[(i+1)%segs],ctr))
        bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
        return s.obj(name,bm,key,group=group)
    def sweep(s,name,pts,rx,ry,key,segs=12,ups=None,cap=True,group=None,closed=False):
        """Elliptic section swept along pts; rx/ry scalar or per point; ups gives the ry (thickness) direction."""
        n=len(pts);pts=[Vector(p) for p in pts];rx=rx if isinstance(rx,(list,tuple)) else [rx]*n;ry=ry if isinstance(ry,(list,tuple)) else [ry]*n
        bm=bmesh.new();rings=[]
        for j,p in enumerate(pts):
            t=((pts[(j+1)%n]-pts[j-1]) if closed else (pts[min(j+1,n-1)]-pts[max(j-1,0)])).normalized()
            up=Vector(ups[j]) if ups else (Vector((0,-1,0)) if abs(t.z)>.7 else Vector((0,0,1)))
            u=(up-t*up.dot(t));u=u.normalized() if u.length>1e-6 else t.orthogonal().normalized();w=t.cross(u).normalized()
            rings.append([bm.verts.new(p+w*rx[j]*math.cos(a)+u*ry[j]*math.sin(a)) for a in (i*2*math.pi/segs for i in range(segs))])
        for j in range(n if closed else n-1):
            a,b=rings[j],rings[(j+1)%n]
            for i in range(segs):bm.faces.new((a[i],a[(i+1)%segs],b[(i+1)%segs],b[i]))
        if cap and not closed:bm.faces.new(list(reversed(rings[0])));bm.faces.new(rings[-1])
        bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
        return s.obj(name,bm,key,group=group)
    def plate(s,name,outline,F,origin,key,thick=.004):
        """Flat filled shape (2-D outline in frame F) with a little thickness, for decal-like face parts."""
        bm=bmesh.new();vs=[bm.verts.new(origin+F@Vector((x,y,0))) for x,y in outline];bm.faces.new(vs)
        bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
        o=s.obj(name,bm,key);md=o.modifiers.new('Thickness','SOLIDIFY');md.thickness=thick;md.offset=1;return o

def frame(n,ref=Vector((1,0,0)),roll=0.):
    """Rotation whose Z = n (outward), X ~ ref, rolled by roll radians about n."""
    n=n.normalized();x=(ref-n*ref.dot(n)).normalized();y=n.cross(x);F=Matrix((x,y,n)).transposed()
    return F@Matrix.Rotation(roll,3,'Z') if roll else F

def taper(a,b,n):return [a+(b-a)*(i/(n-1)) for i in range(n)]

# ------------------------------------------------------------------ body (about 2.5 heads)
class Body:
    def __init__(s,girth=1.):
        s.g=girth
        s.C=Vector((0,0,1.03));s.hr=Vector((.27,.25,.255))      # head centre and radii; head ~0.51 of ~1.30 m
        s.neck=.745;s.waist=.52;s.hip=.43
        s.shoulder=lambda sx:Vector((sx*.108*girth,0,.705))
        s.hand=lambda sx:Vector((sx*(.25+.03*(girth-1)),-.02,.47))

def build_head(k,b,skin='skin'):
    bm=bmesh.new();C=b.C;R=b.hr
    bmesh.ops.create_uvsphere(bm,u_segments=48,v_segments=24,radius=1,matrix=Matrix.Translation(C)@Matrix.Diagonal((*R,1)))
    for v in bm.verts:      # round cheeks, small pointed chin
        t=max(0.,(C.z-v.co.z)/R.z)
        v.co.x=C.x+(v.co.x-C.x)*(1-.18*t**1.8)
        if v.co.y<C.y:v.co.y=C.y+(v.co.y-C.y)*(1+.05*math.sin(min(1.,t*1.6)*math.pi))
    b.head_tree=BVHTree.FromBMesh(bm);k.obj('Head',bm,skin)
    for sx in (-1,1):k.ellipsoid('Ear',(sx*R.x*.96,C.y+.01,C.z-.03),(.03,.045,.052),skin,segs=16,rings=8)
    k.lathe('Neck',[(b.neck-.04,.045,.042),(C.z-R.z*.7,.045,.042)],skin,segs=16)

def on_head(b,x,z,outset=0.):
    hit,n,_,_=b.head_tree.ray_cast(Vector((x,-2,z)),Vector((0,1,0)))
    return hit+n*outset,n

def _semi(a,b,n=16,top=0.):
    """Outline of a D shape: flat top edge, rounded bottom (open mouth)."""
    return [(a*math.cos(t),top-b*math.sin(t)) for t in taper(0,math.pi,n)]

def build_face(k,b,iris='iris_brown',brow='hair_black',eyes='anime',mouth='open',blush=True,brows=True):
    C=b.C
    for sx in (-1,1):
        p,n=on_head(b,sx*.092,C.z-.045)
        F=frame(n,roll=sx*.10)              # outer corner slightly raised
        if eyes=='sleepy':                  # smiling closed eyes (^^)
            arc=[p+F@Vector((.046*math.cos(a),.024*math.sin(a)-.008,.006)) for a in taper(math.radians(170),math.radians(10),9)]
            k.sweep('Eye_Closed',arc,[.005,.007,.008,.009,.009,.009,.008,.007,.005],.004,'lash',segs=8,ups=[n]*9)
        else:
            eye_decals(k,b,p,n,F,sx,iris)
        if brows:
          bp,bn=on_head(b,sx*.095,C.z+.045);BF=frame(bn)
          k.sweep('Eyebrow',[bp+BF@Vector((dx,dz,.004)) for dx,dz in ((-.026,-.003),(0,.005),(.026,-.001))],.006,.003,brow,segs=8,ups=[bn]*3)
        if blush:
            cp,cn=on_head(b,sx*.150,C.z-.105);k.ellipsoid('Blush',cp-cn*.003,(.030,.015,.006),'blush',rot=frame(cn),segs=16,rings=8)
    mp,mn=on_head(b,0,C.z-.140);MF=frame(mn)
    # v004: about 25 % larger (v003 read small in the lineup) and projected onto the skin like the eyes; a larger
    # flat plate would have sunk into the curved face at its corners.
    if mouth=='open':
        mouth_decal(k,'Mouth_Open',b,mp,mn,MF,_semi(.043,.038),.0012,'mouth_in')
        mouth_decal(k,'Mouth_Tongue',b,mp,mn,MF,[(x*.6,y*.45-.019) for x,y in _semi(.043,.038)],.0024,'tongue')
    elif mouth=='small_open':
        mouth_decal(k,'Mouth_Open',b,mp,mn,MF,_semi(.025,.021),.0012,'mouth_in')
    else:
        k.sweep('Mouth',[mp+MF@Vector((dx,-.006*(1-(dx/.018)**2),.003)) for dx in taper(-.018,.018,7)],.004,.003,'mouth',segs=8,ups=[mn]*7)


# ------------------------------------------------------------------ flat eye decals (v003)
# v002 eyes were raised domes (sclera, iris, highlights) and a floating 3-D lash arch, which read as plastic
# buttons. v003 paints them as thin layers that follow the head surface: every vertex is projected onto the skin.
def _project(b,q,n,off):
    hit,hn,_,_=b.head_tree.ray_cast(q+n*.2,-n)
    return (hit+hn*off) if hit else q+n*off

def decal_ellipse(k,name,b,p,n,F,cx,cy,rx,ry,off,key,rings=4,segs=32):
    """Filled ellipse (centre cx,cy in frame F) projected onto the head, offset off above the skin."""
    bm=bmesh.new();ctr=bm.verts.new(_project(b,p+F@Vector((cx,cy,0)),n,off));prev=None;rows=[]
    for r in range(1,rings+1):
        f=r/rings;rows.append([bm.verts.new(_project(b,p+F@Vector((cx+rx*f*math.cos(a),cy+ry*f*math.sin(a),0)),n,off)) for a in taper(0,2*math.pi,segs+1)[:-1]])
    for i in range(segs):bm.faces.new((ctr,rows[0][i],rows[0][(i+1)%segs]))
    for a,c in zip(rows,rows[1:]):
        for i in range(segs):bm.faces.new((a[i],c[i],c[(i+1)%segs],a[(i+1)%segs]))
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
    for f in bm.faces:   # outward (towards the camera side of the face)
        if f.normal.dot(n)<0:f.normal_flip()
    o=k.obj(name,bm,key);md=o.modifiers.new('Thickness','SOLIDIFY');md.thickness=.0006;md.offset=-1;return o

def mouth_decal(k,name,b,p,n,F,outline,off,key,rings=4):
    """Filled closed outline (frame F) projected onto the head: rings shrunk toward its centroid, centre fan."""
    cx=sum(x for x,_ in outline)/len(outline);cy=sum(y for _,y in outline)/len(outline);N=len(outline)
    bm=bmesh.new();ctr=bm.verts.new(_project(b,p+F@Vector((cx,cy,0)),n,off))
    rows=[[bm.verts.new(_project(b,p+F@Vector((cx+(x-cx)*r/rings,cy+(y-cy)*r/rings,0)),n,off)) for x,y in outline] for r in range(1,rings+1)]
    for i in range(N):bm.faces.new((ctr,rows[0][i],rows[0][(i+1)%N]))
    for a,c in zip(rows,rows[1:]):
        for i in range(N):bm.faces.new((a[i],c[i],c[(i+1)%N],a[(i+1)%N]))
    for f in bm.faces:
        if f.normal.dot(n)<0:f.normal_flip()
    o=k.obj(name,bm,key);md=o.modifiers.new('Thickness','SOLIDIFY');md.thickness=.0006;md.offset=-1;return o

def decal_strip(k,name,b,p,n,F,inner,outer,off,key):
    """Filled band between two 2-D polylines (frame F), projected onto the head."""
    bm=bmesh.new();A=[bm.verts.new(_project(b,p+F@Vector((x,y,0)),n,off)) for x,y in inner];B=[bm.verts.new(_project(b,p+F@Vector((x,y,0)),n,off)) for x,y in outer]
    for i in range(len(A)-1):bm.faces.new((A[i],A[i+1],B[i+1],B[i]))
    for f in bm.faces:
        if f.normal.dot(n)<0:f.normal_flip()
    o=k.obj(name,bm,key);md=o.modifiers.new('Thickness','SOLIDIFY');md.thickness=.0006;md.offset=-1;return o

def eye_decals(k,b,p,n,F,sx,iris):
    RX,RY=.050,.062                     # eye opening
    L=.0012                             # layer step above the skin (0.4 mm z-fought: specks on the white)
    decal_ellipse(k,'Eye_Sclera',b,p,n,F,0,-.004,RX,RY,L*1,'sclera')
    # Iris tucked up under the lash line: only the sides and bottom of the white show.
    decal_ellipse(k,'Eye_Iris',b,p,n,F,0,-.004,.039,.056,L*2,iris)
    decal_ellipse(k,'Eye_Iris_Shadow',b,p,n,F,0,.036,.036,.014,L*3,iris+'_d')            # thin darker band under the lash
    decal_ellipse(k,'Eye_Iris_Light',b,p,n,F,0,-.034,.027,.016,L*3,iris+'_l')                # lighter lower crescent
    decal_ellipse(k,'Eye_Pupil',b,p,n,F,0,-.006,.015,.022,L*4,'pupil')
    decal_ellipse(k,'Eye_Highlight',b,p,n,F,-.014,.016,.014,.017,L*5,'eye_hi',rings=3,segs=24)  # same side on both eyes
    decal_ellipse(k,'Eye_Highlight_Small',b,p,n,F,.014,-.030,.0065,.0065,L*5,'eye_hi',rings=2,segs=16)
    # Upper lash: a solid stroke on the top edge of the white, thin at the inner corner, thick outside, flicked up.
    a0,a1=(math.radians(165),math.radians(8)) if sx>0 else (math.radians(15),math.radians(172))
    inn=[];out=[]
    for t in taper(0,1,14):
        a=a0+(a1-a0)*t;ex,ey=RX*math.cos(a),RY*math.sin(a)-.004
        nx,ny=math.cos(a)/RX,math.sin(a)/RY;l=math.hypot(nx,ny);nx,ny=nx/l,ny/l
        th=.003+.011*t**.7
        inn.append((ex-nx*th*.35,ey-ny*th*.35));out.append((ex+nx*th*.65,ey+ny*th*.65))
    ex,ey=out[-1];inn.append((inn[-1][0]+sx*.010,inn[-1][1]+.004));out.append((ex+sx*.016,ey+.011))   # wing
    decal_strip(k,'Eye_Lash_Upper',b,p,n,F,inn,out,L*6,'lash')
    b0,b1=(math.radians(-12),math.radians(-48)) if sx>0 else (math.radians(192),math.radians(228))
    li=[];lo=[]
    for t in taper(0,1,5):
        a=b0+(b1-b0)*t;ex,ey=RX*math.cos(a),RY*math.sin(a)-.004;th=.0022*(1-t)+.0006
        li.append((ex*.93,ey*.93));lo.append((ex*.93+math.cos(a)*th,ey*.93+math.sin(a)*th))   # on the white's rim, no gap
    decal_strip(k,'Eye_Lash_Lower',b,p,n,F,li,lo,L*6,'lash')

# ------------------------------------------------------------------ hands
def relaxed_hand(k,b,sx,skin):
    hc=b.hand(sx)+Vector((sx*.004,-.004,0))
    k.ellipsoid('Hand',hc,(.034*b.g,.030*b.g,.040*b.g),skin,segs=20,rings=10)
    k.ellipsoid('Thumb',hc+Vector((-sx*.008,-.027,.010)),(.012,.014,.017),skin,segs=12,rings=8)

def grip_hand(k,b,sx,axis,rh,skin):
    """Closed hand round a handle of radius rh along axis through the palm centre: back of hand, four curled fingers
    wrapping the handle, thumb closing the gap."""
    H=b.hand(sx);A=Vector(axis).normalized()
    o=Vector((sx,0,0))-A*A.x*sx;o=o.normalized() if o.length>1e-4 else Vector((0,-1,0))   # outward (back of hand)
    f=A.cross(o).normalized()
    k.ellipsoid('Hand_Back',H+o*(rh+.010),(.016,.030,.034),skin,rot=frame(o,ref=f),segs=20,rings=10)   # close to the handle
    R=rh+.010
    for i,off in enumerate((-.021,-.007,.007,.021)):
        c=H+A*off;pts=[c+(o*math.cos(t)+f*math.sin(t))*R for t in taper(math.radians(-40),math.radians(240),9)]
        k.sweep('Hand_Finger',pts,.0105,.0105,skin,segs=10)
    tb=H+f*(R+.004)-o*.004
    k.sweep('Hand_Thumb',[tb-A*.03+o*.01,tb-A*.012,tb+A*.008],[.012,.011,.009],[.011,.010,.009],skin,segs=10)

# ------------------------------------------------------------------ limbs
def build_limbs(k,b,sleeve,cuff,skin,sleeve_style,grips,pants='pants_dark',shoes='shoe',wraps=True):
    g=b.g
    for sx in (-1,1):
        sh=b.shoulder(sx);hd=b.hand(sx);el=sh.lerp(hd,.5)+Vector((sx*.01,0,0))
        path=[sh+Vector((-sx*.018,0,.008)),sh.lerp(el,.5),el,el.lerp(hd,.55),hd+Vector((0,0,.042))]
        if sleeve_style=='wide':
            k.sweep('Sleeve',path,[.046*g,.048*g,.054*g,.064*g,.072*g],[.044*g,.045*g,.051*g,.061*g,.069*g],sleeve,segs=20)
            d=(path[-1]-path[-2]).normalized()
            k.sweep('Sleeve_Cuff',[path[-1]-d*.01,path[-1]+d*.007],.076*g,.073*g,cuff,segs=20)
        else:   # rolled sleeve to the elbow, bare forearm
            k.sweep('Sleeve',path[:3],[.048*g,.050*g,.048*g],[.045*g,.046*g,.045*g],sleeve,segs=18)
            d=(el-sh).normalized();k.sweep('Sleeve_Roll',[el-d*.016,el+d*.010],.055*g,.052*g,cuff,segs=18)
            k.sweep('Forearm',[el,el.lerp(hd,.5),hd+Vector((0,0,.03))],[.034*g,.032*g,.029*g],[.032*g,.030*g,.027*g],skin,segs=16)
        if sx in grips:grip_hand(k,b,sx,*grips[sx],skin)
        else:relaxed_hand(k,b,sx,skin)
    for sx in (-1,1):
        x=sx*.058*g
        k.lathe('Leg',[(.05,.034*g,.034),(.20,.038*g,.038),(.33,.046*g,.046),(b.hip,.052*g,.050)],pants,c=(x,0),segs=20)
        if wraps:   # cloth leg wraps (bang tui) over the shin
            k.lathe('Leg_Wrap',[(.06,.038*g,.038),(.21,.042*g,.042)],'wrap',c=(x,0),segs=20)
            for z in (.09,.15):k.lathe('Leg_Wrap_Tie',[(z,.0435*g,.0435),(z+.012,.0435*g,.0435)],'leather',c=(x,0),segs=20)
        k.ellipsoid('Shoe',(x,-.016,.04),(.050*g,.078,.042),shoes,segs=24,rings=12)
        k.ellipsoid('Shoe_Sole',(x,-.016,.016),(.053*g,.080,.016),'shoe',segs=24,rings=8)

# ------------------------------------------------------------------ outfit
def robe_profile(b,hem,flare=1.,belly=0.):
    g=b.g;n=b.neck;w=b.waist;h=b.hip
    p=[(hem,.150*g*flare,.128*flare),(hem+.05,.145*g*flare,.124*flare)]
    if hem<h-.04:p.append(((hem+h)/2,.140*g*(1+.5*(flare-1)),.118))
    p+=[(h,.136*g,.115+belly*.5),(w,.124*g,.106+belly),(w+.08,.130*g,.109+belly*.7),(n-.10,.128*g,.106),(n-.05,.114*g,.096),(n,.080*g,.068),(n+.025,.056*g,.048)]
    return p

def build_robe(k,b,outer,inner,trim,belt,hem,flare=1.,belly=0.,belt_out=0.):
    """belt_out pushes the belt, knot and tails outwards so they sit over an apron (apron itself sits over the lapel)."""
    prof=robe_profile(b,hem,flare,belly);robe=k.lathe('Robe',prof,outer,segs=48)
    bm=bmesh.new();bm.from_mesh(robe.data);tree=BVHTree.FromBMesh(bm);bm.free()
    def surf(x,z,out=.006):
        hit,n,_,_=tree.ray_cast(Vector((x,-1,z)),Vector((0,1,0)));return (hit+n*out,n) if hit else (Vector((x,-.11,z)),Vector((0,-1,0)))
    g=b.g;n=b.neck;w=b.waist
    vpts=[surf(x,z,.004) for x,z in ((-.045*g,n+.01),(0,w+.08),(.045*g,n+.01))]
    k.sweep('Collar_Inner',[p for p,_ in vpts],.019,.006,inner,segs=10,ups=[nn for _,nn in vpts])
    lap=[surf(x,z,.008) for x,z in ((.062*g,n+.02),(.036*g,n-.08),(0,n-.14),(-.045*g,w+.04),(-.068*g,w+.005))]
    k.sweep('Collar_Lapel',[p for p,_ in lap],.021,.007,trim,segs=10,ups=[nn for _,nn in lap])
    band=[Vector((.078*g*math.cos(a),.066*math.sin(a)+.004,n+.025+.010*math.sin(a))) for a in taper(math.radians(-60),math.radians(240),15)]
    band+=[surf(-.052*g,n-.06,.008)[0],surf(-.03*g,n-.11,.008)[0]]
    k.sweep('Collar_Neckband',band,.019,.008,trim,segs=10,ups=[Vector((math.cos(math.atan2(p.y,p.x)),math.sin(math.atan2(p.y,p.x)),0)) for p in band])
    ring=lambda r,z,c=48:[Vector((r[0]*math.cos(a),r[1]*math.sin(a),z)) for a in taper(0,2*math.pi,c+1)[:-1]]
    outw=lambda c=48:[Vector((math.cos(a),math.sin(a),0)) for a in taper(0,2*math.pi,c+1)[:-1]]
    k.sweep('Hem_Trim',ring((prof[0][1]+.004,prof[0][2]+.004),hem+.022),.019,.007,trim,segs=8,ups=outw(),closed=True)
    wr=next((r[1],r[2]) for r in prof if abs(r[0]-w)<1e-6);bz=w+.01
    k.sweep('Belt',ring((wr[0]+.011+belt_out,wr[1]+.011+belt_out),bz),.028,.009,belt,segs=8,ups=outw(),closed=True)
    kp,kn=surf(.027*g,bz,.015+belt_out);k.ellipsoid('Belt_Knot',kp,(.023,.018,.021),belt,rot=frame(kn),segs=16,rings=8)
    for dx,L in ((.018,.12),(.04,.09)):
        pts=[surf(dx*g+.009*i,bz-.01-L*i/4,.013+belt_out)[0] for i in range(5)]
        k.sweep('Belt_Tail',pts,[.014,.015,.016,.016,.014],.005,belt,segs=8,ups=[Vector((0,-1,0))]*5)
    return robe,surf

def front_panel(k,name,surf,x0,x1,z0,z1,key,out=.017,nx=8,nz=10,thick=.008):
    bm=bmesh.new();grid=[[bm.verts.new(surf(x0+(x1-x0)*i/nx,z1+(z0-z1)*j/nz,out)[0]) for i in range(nx+1)] for j in range(nz+1)]
    for j in range(nz):
        for i in range(nx):bm.faces.new((grid[j][i],grid[j][i+1],grid[j+1][i+1],grid[j+1][i]))
    o=k.obj(name,bm,key);md=o.modifiers.new('Thickness','SOLIDIFY');md.thickness=thick;md.offset=1;return o

def capelet(k,b,key,trim=None,flare=1.18):
    g=b.g;n=b.neck;z0=b.waist+.10
    k.lathe('Capelet',[(z0,.158*g*flare,.134*flare),(z0+.045,.153*g*flare,.130*flare),(n-.06,.148*g,.125),(n-.015,.135*g,.114),(n+.015,.098*g,.082),(n+.033,.072*g,.06)],key,segs=48)
    if trim:
        r=(.158*g*flare+.004,.134*flare+.004)
        k.sweep('Capelet_Trim',[Vector((r[0]*math.cos(a),r[1]*math.sin(a),z0+.011)) for a in taper(0,2*math.pi,49)[:-1]],.013,.006,trim,segs=8,
                ups=[Vector((math.cos(a),math.sin(a),0)) for a in taper(0,2*math.pi,49)[:-1]],closed=True)

# ------------------------------------------------------------------ hair (fuller than v001)
CAP=1.10
def _hair_dir(b,d,out=CAP+.005):
    d=Vector(d).normalized();return b.C+Vector((0,.012,.012))+Vector((d.x*b.hr.x,d.y*b.hr.y,d.z*b.hr.z))*out

def _sstep(x):x=max(0.,min(1.,x));return x*x*(3-2*x)

def hair_cap(k,b,key,hairline=.30,side_low=-.40,back_low=-.55,scale=CAP,volume=True):
    """volume=False under caps and headscarves, where the crown locks would poke through."""
    C2=b.C+Vector((0,.012,.012));R=b.hr*scale;bm=bmesh.new()
    bmesh.ops.create_uvsphere(bm,u_segments=64,v_segments=32,radius=1,matrix=Matrix.Translation(C2)@Matrix.Diagonal((*R,1)))
    for v in bm.verts:   # smooth face opening: sink it inside the head (no stair-stepped deleted faces)
        d=v.co-C2;d=Vector((d.x/R.x,d.y/R.y,d.z/R.z))
        front=min((-.12-d.y)/.10,(.76-abs(d.x))/.16,(hairline+.25*d.x*d.x-d.z)/.08)   # wider temple falloff: no stepped edge
        low=side_low+(back_low-side_low)*max(0.,min(1.,(d.y+.12)/.6))
        f=_sstep(max(front,(low-d.z)/.08)+.5)
        if f>0:v.co=C2+(v.co-C2)*(1-f*.33)
    o=k.obj('Hair_Cap',bm,key);md=o.modifiers.new('Thickness','SOLIDIFY');md.thickness=.02;md.offset=1
    nape_strands(k,b,key,side_low,back_low)
    if volume:volume_locks(k,b,key,side_low,back_low)
    return o

def volume_locks(k,b,key,side_low,back_low,n=12):
    """Broad locks radiating from the crown over the sides and back, bulging off the cap: breaks the smooth dome
    into layered, fuller hair (the reference figure's volume). The front is left to the fringe."""
    crown=Vector((0,.12,1.))
    for i in range(n):
        a=math.radians(-20+220*i/(n-1));dx,dy=math.cos(a),math.sin(a)
        if dy<-.2:continue
        low=side_low+(back_low-side_low)*max(0.,min(1.,(dy+.12)/.6))
        end=Vector((dx,dy,low+.10));pts=[]
        for t in taper(0,1,7):
            d=crown.lerp(end,t);pts.append(_hair_dir(b,d,CAP+.004+.04*math.sin(t*math.pi*.9)))
        pts.append(pts[-1]+Vector((dx*.02,dy*.02,-.05)))
        w=[.05,.075,.085,.085,.08,.07,.05,.012];k.sweep('Hair_Volume',pts,w,[.02,.026,.03,.03,.028,.026,.022,.01],key,segs=12,
                                                        ups=[(p-b.C).normalized() for p in pts])

def nape_strands(k,b,key,side_low,back_low,n=9):
    """Broad rounded locks round the lower rim, alternating length (not a bowl cut, not icicles)."""
    for i in range(n):
        a=math.radians(-25+230*i/(n-1));dx,dy=math.cos(a),math.sin(a)
        if dy<-.15:continue
        low=side_low+(back_low-side_low)*max(0.,min(1.,(dy+.12)/.6))
        top=_hair_dir(b,(dx*.95,dy*.95,low+.30));rim=_hair_dir(b,(dx,dy,low+.02),CAP+.015)
        tip=rim+Vector((dx*.015,dy*.022,-.045-.025*(i%2)))
        k.sweep('Hair_Nape',[top,rim,rim.lerp(tip,.6),tip],[.068,.064,.048,.02],[.024,.024,.021,.014],key,segs=12,ups=[Vector((dx,dy,0))]*4)

def bangs(k,b,key,n=9,span=.66,tip=.08,length=1.,part=None):
    """Thick anime fringe: chunky pointed locks from the crown over the forehead, standing off the cap."""
    for i in range(n):
        u=-1+2*i/(n-1);x=u*span
        if part is not None and abs(u-part)<.1:continue
        d0=Vector((x*.35,-.15,1.));d1=Vector((x*1.06,-1.,tip+.13*abs(u)**2-.06*length*(1-abs(u))))
        pts=[_hair_dir(b,d0.lerp(d1,t),CAP+.01+.045*t) for t in taper(0,1,8)]
        k.sweep('Hair_Bang',pts,[.060,.062,.060,.056,.049,.039,.024,.006],[.03]*7+[.01],key,segs=10,ups=[(p-b.C).normalized() for p in pts])

def side_locks(k,b,key,length=.26,width=.05,curve=False):
    """Two locks per side framing the face, reaching the shoulders. curve=True (v004, the women): the front lock bows
    out over the cheek and sweeps in under the jaw like a bracket, the rear lock flicks outward at the tip."""
    for sx in (-1,1):
        for j,(dy,L,w) in enumerate(((-.45,length,width),(-.05,length*1.12,width*.9))):
            top=_hair_dir(b,(sx*.85,dy,.25),CAP);mid=_hair_dir(b,(sx*.98,dy+.08,-.35),CAP+.03)
            if curve:
                ts=taper(0,1,9)[1:];pts=[top,mid]
                for t in ts:
                    if j==0:x,y=.032*math.sin(math.pi*t)-.034*t**3,-.012-.048*t*t
                    else:x,y=.020*math.sin(math.pi*t*.8)+.030*t**3,-.010-.020*t
                    pts.append(mid+Vector((sx*x,y,-L*t+(.012*t**4 if j==0 else 0))))
                ws=[w,w*1.08]+[w*(1.05-.35*t-.62*t**4)+.004 for t in ts]
                k.sweep('Hair_SideLock',pts,ws,[.024,.026]+[.025-.017*t*t for t in ts],key,segs=10,ups=[Vector((sx,0,0))]*len(pts))
                continue
            # flare out over the cheek, then the tip turns forward toward the chin
            pts=[top,mid,mid+Vector((sx*.018,-.012,-L*.45)),mid+Vector((sx*.012,-.03,-L*.8)),mid+Vector((-sx*.004,-.045,-L))]
            k.sweep('Hair_SideLock',pts,[w,w*1.08,w*.95,w*.55,.007],[.024,.026,.024,.018,.006],key,segs=10,ups=[Vector((sx,0,0))]*5)

def ahoge(k,b,key):
    base=_hair_dir(b,(.05,-.05,1.),CAP)
    k.sweep('Hair_Ahoge',[base,base+Vector((.0,-.02,.07)),base+Vector((.01,-.06,.11)),base+Vector((.015,-.10,.09))],[.02,.017,.011,.003],[.008,.007,.006,.002],key,segs=10,ups=[Vector((1,0,0))]*4)

def bun(k,b,key,d,size=.10,band=None,pin=None):
    p=_hair_dir(b,d,CAP+.04);n=(p-b.C).normalized()
    k.ellipsoid('Hair_Bun',p+n*size*.55,(size,size,size*.9),key,rot=frame(n),segs=28,rings=14)
    if band:
        F=frame(n);rr=[p+n*size*.05+F@Vector((size*.75*math.cos(a),size*.75*math.sin(a),0)) for a in taper(0,2*math.pi,25)[:-1]]
        k.sweep('Hair_Band',rr,.016,.011,band,segs=8,ups=[n]*24,closed=True)
    if pin:
        a=p+n*size*.55+Vector((-size*1.5,0,.02));c=p+n*size*.55+Vector((size*1.5,0,-.03))
        k.sweep('Hairpin',[a,c],.007,.007,pin[0],segs=8);k.ellipsoid('Hairpin_Bead',a,(.016,.016,.016),pin[1],segs=12,rings=8)
    return p+n*size*.55

def ponytail(k,b,key,band=None,length=.46):
    tie=_hair_dir(b,(0,.75,.55),CAP)
    pts=[tie,tie+Vector((0,.08,0)),tie+Vector((0,.13,-.10)),tie+Vector((0,.14,-length*.6)),tie+Vector((0,.11,-length))]
    k.sweep('Hair_Ponytail',pts,[.058,.074,.072,.055,.012],[.05,.06,.058,.045,.01],key,segs=16)
    if band:k.sweep('Hair_Tie',[tie+Vector((0,.015,0)),tie+Vector((0,.05,0))],.052,.048,band,segs=16)

def long_back(k,b,key,bottom=.52,n=5):
    """Long back hair as a fan of separate locks (a single swept slab read as a plank)."""
    for i in range(n):
        u=-1+2*i/(n-1);top=_hair_dir(b,(u*.55,.85,.25),CAP-.01)
        mid=Vector((u*.13,top.y+.05,(top.z+bottom)/2+.02));tip=Vector((u*.16,top.y+.01,bottom-.03*abs(u)))
        k.sweep('Hair_Back',[top,top+Vector((u*.02,.05,-.14)),mid,tip],[.06,.065,.055,.008],[.03,.032,.026,.008],key,segs=12,ups=[Vector((u*.3,1,0))]*4)

def beard(k,b,key,length=.22,width=.10):
    p,n=on_head(b,0,b.C.z-.17,.004)
    k.sweep('Beard',[p+Vector((0,.02,.03)),p+Vector((0,-.02,-.04)),p+Vector((0,-.03,-length*.6)),p+Vector((0,-.01,-length))],[width*.9,width,width*.55,.008],[.05,.06,.04,.006],key,segs=16)
    mp,mn=on_head(b,0,b.C.z-.11,.008)
    for sx in (-1,1):k.sweep('Mustache',[mp,mp+Vector((sx*.035,-.01,-.005)),mp+Vector((sx*.065,-.005,-.035))],[.014,.012,.004],[.009,.008,.003],key,segs=8)

def straw_hat(k,b):
    top=b.C.z+b.hr.z*1.08
    k.lathe('Straw_Hat',[(top-.10,.40,.38),(top-.085,.40,.38),(top-.02,.21,.20),(top+.10,.03,.03),(top+.11,.0,.0)],'straw',segs=48)
    k.sweep('Straw_Hat_Band',[Vector((.205*math.cos(a),.195*math.sin(a),top-.005)) for a in taper(0,2*math.pi,41)[:-1]],.017,.006,'rust',segs=8,
            ups=[Vector((math.cos(a),math.sin(a),0)) for a in taper(0,2*math.pi,41)[:-1]],closed=True)

def skull_cap(k,b,key,knob='red'):
    C=b.C;R=b.hr;bm=bmesh.new()
    bmesh.ops.create_uvsphere(bm,u_segments=48,v_segments=24,radius=1,matrix=Matrix.Translation(C+Vector((0,.01,.03)))@Matrix.Diagonal((R.x*1.13,R.y*1.14,R.z*1.10,1)))
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.calc_center_median().z<C.z+R.z*.30],context='FACES')
    o=k.obj('Skull_Cap',bm,key);md=o.modifiers.new('Thickness','SOLIDIFY');md.thickness=.012;md.offset=1
    k.ellipsoid('Skull_Cap_Knob',(0,.01,C.z+R.z*1.13),(.023,.023,.02),knob,segs=12,rings=8)

def headscarf(k,b,key):
    C=b.C;R=b.hr;C2=C+Vector((0,.02,.02));RR=Vector((R.x*1.16,R.y*1.18,R.z*1.15));bm=bmesh.new()
    bmesh.ops.create_uvsphere(bm,u_segments=64,v_segments=32,radius=1,matrix=Matrix.Translation(C2)@Matrix.Diagonal((*RR,1)))
    for v in bm.verts:
        d=v.co-C2;d=Vector((d.x/RR.x,d.y/RR.y,d.z/RR.z));f=_sstep(max(min((-.25-d.y)/.10,(.55-d.z)/.08),(-.15-d.z)/.08)+.5)
        if f>0:v.co=C2+(v.co-C2)*(1-f*.36)
    o=k.obj('Headscarf',bm,key);md=o.modifiers.new('Thickness','SOLIDIFY');md.thickness=.015;md.offset=1
    knot=Vector((0,C.y+R.y*1.12,C.z+.02));k.ellipsoid('Headscarf_Knot',knot,(.045,.032,.036),key,segs=16,rings=8)
    for sx in (-1,1):k.sweep('Headscarf_Tail',[knot,knot+Vector((sx*.04,.03,-.08)),knot+Vector((sx*.06,.04,-.14))],[.028,.026,.01],[.008]*3,key,segs=8)

# ------------------------------------------------------------------ props: (grip hand side, axis, handle radius) + geometry
def prop_hammer(k,b):
    H=b.hand(1);A=Vector((.05,-.08,1.)).normalized();top=H+A*.25
    k.sweep('Hammer_Handle',[H-A*.09,top],.017,.017,'wood',segs=10)
    k.sweep('Hammer_Head',[top+Vector((-.075,0,0)),top+Vector((.085,0,0))],.044,.040,'iron',segs=14)
    k.sweep('Hammer_Band',[top+Vector((-.018,0,0)),top+Vector((.018,0,0))],.048,.044,'brass',segs=14)
    return {1:(A,.017)}
def prop_staff(k,b):
    H=b.hand(1)
    k.sweep('Staff',[Vector((H.x,H.y,.01)),Vector((H.x,H.y,1.22)),Vector((H.x+.03,H.y,1.30))],[.016,.014,.011],[.016,.014,.011],'wood',segs=10)
    k.ellipsoid('Staff_Gourd',(H.x+.034,H.y,1.27),(.033,.033,.042),'ochre',segs=16,rings=8)
    k.ellipsoid('Staff_Jade',(H.x+.03,H.y,1.33),(.028,.028,.028),'jade',segs=16,rings=8)
    return {1:((0,0,1),.016)}
def prop_cane(k,b):
    H=b.hand(1)
    k.sweep('Cane',[Vector((H.x,H.y,.01)),Vector((H.x,H.y,H.z+.05)),Vector((H.x-.02,H.y,H.z+.09)),Vector((H.x-.06,H.y,H.z+.07))],.013,.013,'wood',segs=10)
    return {1:((0,0,1),.013)}
def prop_abacus(k,b):
    """Carried at the side by its back bar, like a ledger: frame in the Y-Z plane in front of the hand."""
    H=b.hand(1);c=H+Vector((0,-.125,0));fx=lambda dy,dz:c+Vector((0,dy,dz))
    k.sweep('Abacus_Frame',[fx(-.12,.06),fx(.12,.06),fx(.12,-.06),fx(-.12,-.06)],.011,.011,'timber',segs=6,closed=True)
    for i in range(7):
        y=-.09+i*.03;k.sweep('Abacus_Rod',[fx(y,-.06),fx(y,.06)],.003,.003,'brass',segs=6)
        for z in (.035,-.01,-.03):k.ellipsoid('Abacus_Bead',fx(y,z),(.008,.012,.008),'red' if z>0 else 'timber',segs=10,rings=6)
    k.sweep('Abacus_Bar',[fx(-.12,.015),fx(.12,.015)],.007,.007,'timber',segs=6)
    return {1:((0,0,1),.011)}
def prop_teapot(k,b):
    H=b.hand(1);T=H+Vector((0,-.10,-.01))
    k.ellipsoid('Teapot',T,(.068,.068,.055),'jade',segs=24,rings=12);k.ellipsoid('Teapot_Lid',T+Vector((0,0,.05)),(.032,.032,.014),'jade',segs=16,rings=6)
    k.sweep('Teapot_Spout',[T+Vector((0,-.055,0)),T+Vector((0,-.09,.035)),T+Vector((0,-.105,.055))],[.015,.011,.008],[.015,.011,.008],'jade',segs=10)
    k.sweep('Teapot_Handle',[T+Vector((0,.06,.03)),H+Vector((0,0,.035)),H+Vector((0,0,-.035)),T+Vector((0,.06,-.025))],.008,.008,'timber',segs=8)
    return {1:((0,0,1),.008)}
def prop_axe(k,b):
    H=b.hand(1);A=Vector((.10,0,-1.)).normalized();low=H+A*.32
    k.sweep('Axe_Handle',[H-A*.06,low],.017,.017,'wood',segs=10)
    k.sweep('Axe_Blade',[low+Vector((0,0,.06)),low+Vector((.11,0,.03))],[.011,.011],[.042,.07],'iron',segs=12,ups=[Vector((0,0,1))]*2)
    k.sweep('Axe_Edge',[low+Vector((.105,0,.03)),low+Vector((.12,0,.03))],.009,.075,'stone',segs=10,ups=[Vector((0,0,1))]*2)
    return {1:(A,.017)}
def prop_pill_bottle(k,b):
    H=b.hand(-1)
    k.lathe('Pill_Bottle',[(H.z-.055,.024,.024),(H.z-.01,.03,.03),(H.z+.035,.026,.026),(H.z+.05,.012,.012),(H.z+.065,.012,.012)],'white_robe',c=(H.x,H.y),segs=20)
    k.ellipsoid('Pill_Bottle_Stopper',(H.x,H.y,H.z+.075),(.013,.013,.012),'red',segs=12,rings=6)
    return {-1:((0,0,1),.028)}
def prop_basket_back(k,b):
    c=Vector((0,.20,.62))
    k.lathe('Back_Basket',[(c.z-.15,.09,.07),(c.z-.13,.11,.09),(c.z+.09,.145,.12),(c.z+.11,.15,.125)],'straw',c=(0,c.y),segs=28)
    for x in (-.05,0,.05):k.sweep('Basket_Herb',[Vector((x,c.y,c.z+.09)),Vector((x*1.6,c.y+.03,c.z+.22))],[.018,.032],[.018,.032],'herb',segs=10)
    for sx in (-1,1):k.sweep('Basket_Strap',[Vector((sx*.09,c.y-.04,c.z+.09)),Vector((sx*.09,.02,b.neck-.01)),Vector((sx*.08,-.10,b.neck-.07)),Vector((sx*.09,-.115,b.waist+.06))],.013,.005,'leather',segs=8)
    return {}
def prop_sword_back(k,b):
    a=Vector((-.15,.13,.30));c=Vector((.15,.13,.88))
    k.sweep('Sword_Scabbard',[a,a.lerp(c,.75)],[.02,.023],[.011,.011],'timber',segs=10)
    k.sweep('Sword_Guard',[a.lerp(c,.75)+Vector((-.028,0,.028)),a.lerp(c,.75)+Vector((.028,0,-.028))],.011,.016,'brass',segs=8)
    k.sweep('Sword_Hilt',[a.lerp(c,.77),c],.013,.013,'jade',segs=10);k.ellipsoid('Sword_Pommel',c,(.018,.018,.018),'brass',segs=12,rings=6)
    k.sweep('Sword_Strap',[Vector((.11,-.10,b.neck-.06)),Vector((0,-.12,b.waist+.08)),Vector((-.10,-.10,b.waist+.01))],.011,.005,'leather',segs=8)
    return {}
def prop_gourd_belt(k,b):
    c=Vector((-.135*b.g,-.07,b.hip-.01))
    k.ellipsoid('Belt_Gourd_Low',c,(.036,.036,.04),'ochre',segs=16,rings=8);k.ellipsoid('Belt_Gourd_High',c+Vector((0,0,.055)),(.025,.025,.027),'ochre',segs=16,rings=8)
    k.sweep('Belt_Gourd_Cord',[c+Vector((0,0,.08)),Vector((-.11*b.g,-.09,b.waist))],.005,.005,'rust',segs=6)
    return {}
PROPS={'hammer':prop_hammer,'staff':prop_staff,'cane':prop_cane,'abacus':prop_abacus,'teapot':prop_teapot,'axe':prop_axe,
       'basket':prop_basket_back,'sword':prop_sword_back,'gourd':prop_gourd_belt,'pill':prop_pill_bottle}

# ------------------------------------------------------------------ characters
CHARACTERS={
 'QPlayerMale':dict(zh='玩家（男）',hair='topknot',hair_key='hair_black',iris='iris_amber',outer='teal',inner='white_robe',trim='white_robe',belt='leather',hem=.27,ahoge=True),
 'QPlayerFemale':dict(zh='玩家（女）',hair='double_buns',hair_key='hair_black',iris='iris_blue',outer='teal',inner='white_robe',trim='white_robe',belt='leather',hem=.25,flare=1.1,band='jade',ahoge=True,lock_curve=True),
 'QDiscipleSword':dict(zh='劍修弟子',hair='ponytail',hair_key='hair_black',iris='iris_grey',outer='white_robe',inner='teal_light',trim='teal',belt='teal',hem=.26,props=['sword'],band='teal',ahoge=True),
 'QDiscipleAlchemy':dict(zh='丹修弟子',hair='long_pin',hair_key='hair_brown',iris='iris_jade',outer='cream',inner='white_robe',trim='jade',belt='jade',hem=.20,flare=1.12,props=['pill','gourd'],lock_curve=True),
 'QDiscipleFarmer':dict(zh='體修弟子',hair='short_band',hair_key='hair_brown',iris='iris_brown',outer='ochre',inner='cream',trim='timber',belt='timber',hem=.28,sleeves='short',skin='skin_tan',girth=1.08,ahoge=True),
 'QSectElder':dict(zh='宗門長老',hair='elder',hair_key='hair_white',outer='white_robe',inner='teal',trim='jade',belt='jade',hem=.05,flare=1.18,props=['staff'],capelet=('teal','jade'),eyes='sleepy',mouth='smile',scale=1.04,wraps=False),
 'QBlacksmith':dict(zh='鐵匠',hair='spiky',hair_key='hair_black',iris='iris_brown',outer='charcoal',inner='charcoal',trim='leather',belt='leather',hem=.28,sleeves='short',skin='skin_tan',girth=1.18,apron='leather',props=['hammer']),
 'QShopkeeper':dict(zh='雜貨店主',hair='cap',hair_key='hair_black',outer='ochre',inner='cream',trim='timber',belt='timber',hem=.16,girth=1.14,belly=.03,props=['abacus'],mustache=True,eyes='sleepy',mouth='small_open',wraps=False),
 'QInnkeeper':dict(zh='客棧老闆娘',hair='low_bun',hair_key='hair_black',iris='iris_plum',outer='plum',inner='cream',trim='cream',belt='cream',hem=.10,flare=1.1,apron='white_robe',props=['teapot'],wraps=False,lock_curve=True),
 'QHerbalist':dict(zh='藥師',hair='braid',hair_key='hair_brown',iris='iris_green',outer='sage',inner='cream',trim='timber',belt='timber',hem=.22,flare=1.08,props=['basket'],lock_curve=True),
 'QGranny':dict(zh='村中婆婆',hair='scarf',hair_key='hair_grey',outer='rust',inner='cream',trim='cream',belt='timber',hem=.08,flare=1.1,props=['cane'],eyes='sleepy',mouth='small_open',scale=.92,capelet=('indigo',None),wraps=False),
 'QWoodcutter':dict(zh='樵夫',hair='straw_hat',hair_key='hair_black',iris='iris_amber',outer='indigo',inner='cream',trim='cream',belt='straw',hem=.28,sleeves='short',skin='skin_tan',props=['axe'],girth=1.06),
}

def build_hair(k,b,spec):
    h=spec['hair'];key=spec['hair_key'];band=spec.get('band','red');cv=spec.get('lock_curve',False)   # v004: curved side locks (the women)
    if h=='topknot':
        hair_cap(k,b,key,hairline=.36,side_low=-.32);bangs(k,b,key,n=7,span=.6,tip=.16,length=.7,part=0.);side_locks(k,b,key,length=.14,width=.04)
        bun(k,b,key,(0,.15,1.),.08,band='timber',pin=('wood','jade'))
    elif h=='double_buns':
        hair_cap(k,b,key,hairline=.30,side_low=-.45);bangs(k,b,key);side_locks(k,b,key,length=.30,curve=cv)
        for sx in (-1,1):
            c=bun(k,b,key,(sx*.75,.25,.65),.08,band=band)
            k.sweep('Bun_Ribbon',[c+Vector((sx*.02,.06,-.02)),c+Vector((sx*.05,.10,-.12)),c+Vector((sx*.06,.11,-.20))],[.02,.022,.012],.005,band,segs=8,ups=[Vector((0,1,0))]*3)
    elif h=='ponytail':
        hair_cap(k,b,key,hairline=.32,side_low=-.35);bangs(k,b,key,n=8,tip=.1,length=.9);ponytail(k,b,key,band=band);side_locks(k,b,key,length=.22,width=.042)
    elif h=='long_pin':
        hair_cap(k,b,key,hairline=.30,side_low=-.55,back_low=-.75);bangs(k,b,key,n=9,tip=.05,length=1.1,part=-.33);side_locks(k,b,key,length=.32,curve=cv)
        long_back(k,b,key);bun(k,b,key,(0,.7,.6),.065,band='jade',pin=('brass','jade'))
    elif h=='short_band':
        hair_cap(k,b,key,hairline=.42,side_low=-.25);bangs(k,b,key,n=7,span=.62,tip=.22,length=.5)
        rr=[_hair_dir(b,(math.cos(a),math.sin(a),.42),CAP+.03) for a in taper(0,2*math.pi,33)[:-1]]
        k.sweep('Headband',rr,.023,.01,'red',segs=8,ups=[(p-b.C).normalized() for p in rr],closed=True)
    elif h=='elder':
        hair_cap(k,b,key,hairline=.50,side_low=-.30,back_low=-.40);bun(k,b,key,(0,.1,1.),.075,band='jade',pin=('jade','jade'))
        k.ellipsoid('Elder_Crown',_hair_dir(b,(0,.1,1.),CAP+.04)+Vector((0,0,.07)),(.055,.032,.028),'jade',segs=16,rings=8)
        beard(k,b,key,length=.24,width=.10)
    elif h=='spiky':
        hair_cap(k,b,key,hairline=.42,side_low=-.25);bangs(k,b,key,n=7,span=.62,tip=.26,length=.4)
        for i in range(7):
            a=-1.1+i*.37;base=_hair_dir(b,(math.sin(a)*.6,.2+.1*math.cos(a),.95),CAP-.02);n=(base-b.C).normalized()
            k.sweep('Hair_Spike',[base,base+n*.06+Vector((0,.04,0)),base+n*.10+Vector((0,.08,0))],[.042,.028,.004],[.028,.019,.003],key,segs=10)
    elif h=='cap':
        hair_cap(k,b,key,hairline=.35,side_low=-.30,volume=False);skull_cap(k,b,'indigo')
    elif h=='low_bun':
        hair_cap(k,b,key,hairline=.32,side_low=-.40);bangs(k,b,key,n=8,tip=.08,length=.9,part=.2);side_locks(k,b,key,length=.22,width=.042,curve=cv)
        bun(k,b,key,(0,.9,-.05),.09,band='cream',pin=('brass','red'))
    elif h=='braid':
        hair_cap(k,b,key,hairline=.30,side_low=-.40);bangs(k,b,key);side_locks(k,b,key,length=.18,width=.04,curve=cv)
        start=_hair_dir(b,(.6,.5,-.35),CAP)
        for i in range(6):k.ellipsoid('Hair_Braid',start+Vector((.03+.01*i,-.04-.012*i,-.065*i)),(.038-.003*i,.038-.003*i,.046),key,segs=16,rings=8)
        k.sweep('Hair_Braid_Tie',[start+Vector((.09,-.11,-.38)),start+Vector((.09,-.11,-.41))],.026,.026,'jade',segs=12)
    elif h=='scarf':
        hair_cap(k,b,key,hairline=.32,side_low=-.30,volume=False);headscarf(k,b,'indigo')
    elif h=='straw_hat':
        hair_cap(k,b,key,hairline=.38,side_low=-.30);bangs(k,b,key,n=7,span=.58,tip=.18,length=.6);straw_hat(k,b)
    if spec.get('ahoge'):ahoge(k,b,key)

def build_character(coll,aid):
    spec=CHARACTERS[aid];root=bpy.data.objects.new(aid+'_ROOT',None);coll.objects.link(root);k=Kit(coll,root)
    b=Body(spec.get('girth',1.));skin=spec.get('skin','skin')
    build_head(k,b,skin)
    build_face(k,b,spec.get('iris','iris_brown'),spec['hair_key'],spec.get('eyes','anime'),spec.get('mouth','open'),
               brows=spec['hair'] in ('elder','cap','scarf'))   # fringe covers the brows on everyone else
    grips={}
    for p in spec.get('props',[]):grips.update(PROPS[p](k,b))
    build_limbs(k,b,spec['outer'],spec['trim'],skin,'short' if spec.get('sleeves')=='short' else 'wide',grips,wraps=spec.get('wraps',True))
    robe,surf=build_robe(k,b,spec['outer'],spec['inner'],spec['trim'],spec['belt'],spec['hem'],spec.get('flare',1.),spec.get('belly',0.),
                         belt_out=.022 if spec.get('apron') else 0.)
    if spec.get('apron'):front_panel(k,'Apron',surf,-.11*b.g,.11*b.g,max(.10,spec['hem']+.02),b.waist+.16,spec['apron'])
    if spec.get('capelet'):capelet(k,b,*spec['capelet'])
    build_hair(k,b,spec)
    if spec.get('mustache'):
        mp,mn=on_head(b,0,b.C.z-.11,.008)   # ends curl upward so the face reads cheerful
        for sx in (-1,1):k.sweep('Mustache',[mp,mp+Vector((sx*.035,-.008,-.01)),mp+Vector((sx*.062,-.004,.004))],[.013,.011,.004],[.009,.008,.003],spec['hair_key'],segs=8)
    s=spec.get('scale',1.)
    if s!=1.:
        for o in coll.objects:
            if o.type=='MESH' and o.parent==root:o.data.transform(Matrix.Scale(s,4))
    root['grips']=str({k_:(list(v[0]),v[1]) for k_,v in grips.items()})
    return root
