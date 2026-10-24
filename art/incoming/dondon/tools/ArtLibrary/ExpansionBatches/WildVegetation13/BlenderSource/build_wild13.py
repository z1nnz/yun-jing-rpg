"""Wild vegetation and rocks: procedural editable meshes, metres, ten same-geometry views.
Blender CLI: blender --background --python-exit-code 1 --python build_wild13.py [-- AssetId ...]
Skips an asset whose views.json already exists; writes only inside this batch folder.
Palette follows SectCore04 / MountainWind07: jade-gray stone, deep greens, warm timber.
"""
import bpy,bmesh,math,json,sys,random
from pathlib import Path
from mathutils import Vector,Matrix,noise
ROOT=Path(__file__).resolve().parents[1]
VIEWS=[('01_front',(0,-1,0)),('02_right',(1,0,0)),('03_rear',(0,1,0)),('04_left',(-1,0,0)),('05_front_right',(1,-1,.6)),('06_rear_right',(1,1,.6)),('07_rear_left',(-1,1,.6)),('08_front_left',(-1,-1,.6)),('09_top',(0,0,1)),('10_high_front',(0,-1,1))]
NAMES={'CommonPine':'普通松','BambooClump':'竹叢','WildShrub':'野灌木','MossBoulderSet':'苔石組','ScreePile':'碎石堆'}
DETAILS={'CommonPine':'Upright mountain pine with layered cloud-pad foliage; plain counterpart to WelcomingPine.',
 'BambooClump':'Eleven jointed culms with leaf sprays, soil mound and three shoots.',
 'WildShrub':'Rounded broadleaf shrub with woody stems and small pale-rose blossoms.',
 'MossBoulderSet':'One large and six smaller flat-based boulders with moss on upward faces.',
 'ScreePile':'Loose heap of angular stones for path edges and slope feet.'}
CATEGORY={'CommonPine':'野外植被','BambooClump':'野外植被','WildShrub':'野外植被','MossBoulderSet':'山石','ScreePile':'山石'}
EXTRA={}

def mat(name,c,rough=.9,spec=.15):
    # Low specular: under the large studio area lights the default sheen washed dark greens out to mint.
    m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);m.use_nodes=True
    bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(*c,1);bs.inputs['Roughness'].default_value=rough
    bs.inputs['Specular IOR Level'].default_value=spec
    return m

def varied(name,dark,light,scale=6,bump=.12,rough=.9,spec=.15):
    """Object-space noise blends two tones; viewport and FBX keep the mid colour."""
    m=mat(name,tuple((a+b)/2 for a,b in zip(dark,light)),rough,spec);n=m.node_tree.nodes;l=m.node_tree.links
    bs=next(x for x in n if x.type=='BSDF_PRINCIPLED');coord=n.new('ShaderNodeTexCoord')
    tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=scale;tex.inputs['Detail'].default_value=4;l.new(coord.outputs['Object'],tex.inputs['Vector'])
    ramp=n.new('ShaderNodeValToRGB');e=ramp.color_ramp.elements;e[0].position=.3;e[0].color=(*dark,1);e[1].position=.72;e[1].color=(*light,1)
    l.new(tex.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs['Color'],bs.inputs['Base Color'])
    b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=bump;b.inputs['Distance'].default_value=.03
    l.new(tex.outputs['Fac'],b.inputs['Height']);l.new(b.outputs['Normal'],bs.inputs['Normal'])
    return m

def mossy(name,dark,light,moss_dark,moss_light):
    """Rock tones with a smooth moss cap on upward normals, broken up by noise."""
    m=varied(name,dark,light,1.6,.4);n=m.node_tree.nodes;l=m.node_tree.links
    bs=next(x for x in n if x.type=='BSDF_PRINCIPLED');ramp=next(x for x in n if x.type=='VALTORGB')
    geo=n.new('ShaderNodeNewGeometry');sep=n.new('ShaderNodeSeparateXYZ');l.new(geo.outputs['Normal'],sep.inputs[0])
    coord=next(x for x in n if x.type=='TEX_COORD');tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=3.5;tex.inputs['Detail'].default_value=5
    l.new(coord.outputs['Object'],tex.inputs['Vector'])
    add=n.new('ShaderNodeMath');add.operation='ADD';l.new(sep.outputs['Z'],add.inputs[0]);sub=n.new('ShaderNodeMath');sub.operation='SUBTRACT'
    l.new(tex.outputs['Fac'],sub.inputs[0]);sub.inputs[1].default_value=.5;l.new(sub.outputs[0],add.inputs[1])
    mask=n.new('ShaderNodeMapRange');mask.inputs['From Min'].default_value=.55;mask.inputs['From Max'].default_value=.8;l.new(add.outputs[0],mask.inputs['Value'])
    mr=n.new('ShaderNodeValToRGB');e=mr.color_ramp.elements;e[0].color=(*moss_dark,1);e[1].color=(*moss_light,1);l.new(tex.outputs['Fac'],mr.inputs[0])
    mix=n.new('ShaderNodeMix');mix.data_type='RGBA';l.new(mask.outputs['Result'],mix.inputs['Factor'])
    l.new(ramp.outputs['Color'],mix.inputs['A']);l.new(mr.outputs['Color'],mix.inputs['B']);l.new(mix.outputs['Result'],bs.inputs['Base Color'])
    return m

def make_materials():
    global M
    M={'bark':varied('Pine_Bark',(.05,.028,.016),(.15,.09,.05),14,.35),
       'needle':varied('Pine_Needle_Pads',(.012,.045,.025),(.05,.12,.04),3,.25),
       'needle_dark':mat('Pine_Pad_Underside',(.008,.025,.016)),
       'culm':varied('Bamboo_Culm',(.09,.20,.06),(.20,.28,.09),2,.04,.55,.35),
       'culm_old':varied('Bamboo_Culm_Aged',(.30,.30,.13),(.42,.39,.19),2,.04,.6,.35),
       'node':mat('Bamboo_Node_Ring',(.30,.31,.15),.6,.35),
       'bamboo_leaf':varied('Bamboo_Leaf',(.02,.07,.025),(.07,.16,.045),9,.02,.7),
       'sheath':mat('Bamboo_Shoot_Sheath',(.29,.16,.07)),
       'soil':varied('Forest_Soil',(.04,.025,.012),(.09,.06,.03),5,.3),
       'shrub_leaf':varied('Shrub_Leaves',(.025,.09,.035),(.08,.18,.06),9,.45),
       'shrub_dark':mat('Shrub_Leaf_Underside',(.012,.04,.02)),
       'twig':mat('Shrub_Twig',(.10,.06,.035)),
       'blossom':mat('Pale_Rose_Blossom',(.50,.24,.27),.6),
       # Upward faces take the full key light, so stone albedo sits well below the MountainWind07 values.
       'rock':varied('Jade_Gray_Weathered_Rock',(.022,.034,.036),(.07,.09,.085),1.6,.4),
       'rock_pale':varied('Pale_Scree_Stone',(.04,.05,.047),(.10,.11,.10),3,.35),
       'soil_gravel':varied('Gravel_And_Soil',(.035,.033,.028),(.09,.085,.07),14,.5),
       'mossy_rock':mossy('Jade_Gray_Rock_Moss_Cap',(.022,.034,.036),(.07,.09,.085),(.015,.035,.012),(.06,.095,.028))}

def link(name,bm,mats,smooth=True):
    """smooth=None keeps the per-face flags already set in bm."""
    d=bpy.data.meshes.new(name+'_Mesh');bm.to_mesh(d);bm.free()
    for m in mats:d.materials.append(m)
    if smooth is not None:
        for p in d.polygons:p.use_smooth=smooth
    o=bpy.data.objects.new(name,d);assets.objects.link(o);o.parent=root;return o

def tube_into(bm,points,radii,sides=10,cap=True):
    """Swept ring tube along points; returns created faces."""
    rings=[];faces=[]
    for j,p in enumerate(points):
        p=Vector(p);t=(Vector(points[min(j+1,len(points)-1)])-Vector(points[max(j-1,0)])).normalized()
        u=t.cross(Vector((0,0,1)))
        if u.length<.01:u=t.cross(Vector((0,1,0)))
        u.normalize();w=t.cross(u)
        rings.append([bm.verts.new(p+radii[j]*(u*math.cos(i*math.tau/sides)+w*math.sin(i*math.tau/sides))) for i in range(sides)])
    for a,b in zip(rings,rings[1:]):
        for i in range(sides):faces.append(bm.faces.new((a[i],a[(i+1)%sides],b[(i+1)%sides],b[i])))
    if cap:faces.append(bm.faces.new(list(reversed(rings[0]))));faces.append(bm.faces.new(rings[-1]))
    return faces

def lumpy_into(bm,center,radii,seed,subdiv=3,rough=.22,freq=1.5,rot=0):
    """Noise-displaced icosphere added to bm; returns its verts."""
    r=bmesh.ops.create_icosphere(bm,subdivisions=subdiv,radius=1);vs=r['verts'];off=Vector((seed*1.37,seed*2.11,seed*.73))
    rm=Matrix.Rotation(rot,3,'Z')
    for v in vs:
        d=v.co.normalized();k=1+rough*noise.fractal(d*freq+off,.6,2.0,4)
        v.co=Vector(center)+rm@Vector((d.x*radii[0]*k,d.y*radii[1]*k,d.z*radii[2]*k))
    return vs

def flat_base(bm,z=0.0):
    """Cut everything below z and close the opening with a flat sole."""
    geom=bm.verts[:]+bm.edges[:]+bm.faces[:]
    bmesh.ops.bisect_plane(bm,geom=geom,plane_co=(0,0,z),plane_no=(0,0,1),clear_inner=True)
    edges=[e for e in bm.edges if e.is_boundary]
    if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)

def chisel(bm,center,radii,cuts,rng):
    """Planar cuts give rocks broken flat faces; cut faces stay flat-shaded."""
    for k in range(cuts):
        a=rng.uniform(0,math.tau);el=rng.uniform(-.1,.9);d=Vector((math.cos(a)*math.cos(el),math.sin(a)*math.cos(el),math.sin(el)))
        reach=Vector((d.x*radii[0],d.y*radii[1],d.z*radii[2])).length*rng.uniform(.72,.86)
        geom=bm.verts[:]+bm.edges[:]+bm.faces[:]
        bmesh.ops.bisect_plane(bm,geom=geom,plane_co=Vector(center)+d*reach,plane_no=d,clear_outer=True)
        edges=[e for e in bm.edges if e.is_boundary]
        if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)
    for f in bm.faces:f.smooth=len(f.verts)<=4

def by_normal(o,up_index,down_index,up=.55,down=-.15):
    for p in o.data.polygons:
        if p.normal.z>up:p.material_index=up_index
        elif p.normal.z<down:p.material_index=down_index

# ---------------------------------------------------------------- assets
def pine():
    rng=random.Random(1301);H=6.6
    trunk=[(0.32*math.sin(t*2.2)*t,0.10*math.sin(t*3.1)*t,H*t) for t in [i/16 for i in range(17)]]
    bm=bmesh.new();tube_into(bm,trunk,[.30*(1-t)**.85+.05 for t in [i/16 for i in range(17)]],14)
    # Root flare: five short buttress roots spreading onto the ground plane.
    for i in range(5):
        a=i*math.tau/5+.3;pts=[(0,0,.55),(.30*math.cos(a),.30*math.sin(a),.18),(.62*math.cos(a),.62*math.sin(a),.06)]
        tube_into(bm,pts,[.16,.10,.05],8)
    branches=[];golden=2.39996
    for i in range(7):
        t=.36+i*.085;h=H*t;a=i*golden+.6;L=2.3-1.25*(i/6);base=Vector(trunk[round(t*16)])
        tip=base+Vector((L*math.cos(a),L*math.sin(a),.35+.25*rng.random()))
        mid=base.lerp(tip,.5)+Vector((0,0,.32))
        pts=[base,base.lerp(mid,.6),mid,mid.lerp(tip,.5),tip]
        tube_into(bm,[tuple(p) for p in pts],[.11-.008*i,.085,.065,.05,.035],8)
        branches.append((tip,a,L))
    for v in bm.verts:v.co.z=max(v.co.z,0.0)
    link('Pine_Trunk_And_Branches',bm,[M['bark']])
    # Cloud-pad foliage: each pad is several flattened lumps merged into one mesh.
    def pad(name,c,r,seed):
        bm=bmesh.new();rr=random.Random(seed)
        for k in range(4):
            dx,dy=rr.uniform(-.45,.45)*r,rr.uniform(-.45,.45)*r
            lumpy_into(bm,(c.x+dx,c.y+dy,c.z+rr.uniform(-.05,.1)),(r*rr.uniform(.6,.85),r*rr.uniform(.5,.75),r*.3),seed*10+k,3,.28,1.8,rr.uniform(0,6))
        o=link(name,bm,[M['needle'],M['needle_dark']]);by_normal(o,0,1,.4,-.35);return o
    for i,(tip,a,L) in enumerate(branches):
        pad('Pine_Pad_Branch_%02d'%i,tip+Vector((0,0,.12)),.75+.18*L,40+i)
        inner=tip.lerp(Vector((0,0,tip.z)),.45)+Vector((0,0,.32))
        if i%2==0:pad('Pine_Pad_Inner_%02d'%i,inner,.62,70+i)
    top=Vector(trunk[-1])
    pad('Pine_Pad_Crown',top+Vector((0,0,.05)),1.0,99);pad('Pine_Pad_Crown_Upper',top+Vector((.05,0,.42)),.62,98)
    EXTRA['CommonPine']={'branch_tiers':7,'foliage_pads':len([o for o in assets.objects if o.name.startswith('Pine_Pad')]),'wind':'static; no shape keys'}

def bamboo():
    rng=random.Random(1302);culms=[]
    bm=bmesh.new();lumpy_into(bm,(0,0,0),(.78,.66,.16),5,3,.18,2.2);flat_base(bm)
    link('Bamboo_Soil_Mound',bm,[M['soil']])
    for i in range(11):
        a=i*2.39996;r=.12+.36*math.sqrt(i/10);base=Vector((r*math.cos(a),r*math.sin(a),0))
        H=rng.uniform(4.3,6.4);R=rng.uniform(.032,.052);lean=rng.uniform(.10,.26)
        out=Vector((math.cos(a),math.sin(a),0)) if r>.15 else Vector((.6,-.8,0))
        def at(t):return base+out*(lean*H*t**1.8)+Vector((0,0,H*t*(1-.06*t**3)))  # tips arch outward and nod
        n=26;pts=[at(j/n) for j in range(n+1)];old=i in (3,8)
        bm=bmesh.new();tube_into(bm,[tuple(p) for p in pts],[R*(1-.45*(j/n)) for j in range(n+1)],10)
        link('Bamboo_Culm_%02d'%i,bm,[M['culm_old' if old else 'culm']])
        # Node rings every ~0.3 m; leaves sprout from nodes above 45 % height.
        bm=bmesh.new();leaves=bmesh.new();k=0;z=.22
        while z<H*.97:
            t=z/H;c=at(t);rad=R*(1-.45*t)*1.18;nxt=at(min(1,t+.01))
            tube_into(bm,[tuple(c-(nxt-c).normalized()*.012),tuple(c+(nxt-c).normalized()*.012)],[rad,rad],10)
            if t>.36:
                for s in range(3):
                    ang=rng.uniform(0,math.tau);twig=c+Vector((math.cos(ang),math.sin(ang),.3)).normalized()*rng.uniform(.22,.38)
                    tube_into(leaves,[tuple(c),tuple(twig)],[.008,.005],5,False)
                    for q in range(rng.randint(6,9)):
                        la=ang+rng.uniform(-1.3,1.3);ln=rng.uniform(.22,.34);droop=rng.uniform(-.55,-.1)
                        d=Vector((math.cos(la),math.sin(la),droop)).normalized();side=d.cross(Vector((0,0,1))).normalized()*rng.uniform(.03,.042)
                        p0=twig;p1=twig+d*ln*.35+side;p2=twig+d*ln+Vector((0,0,-.03));p3=twig+d*ln*.35-side
                        vs=[leaves.verts.new(p) for p in (p0,p1,p2,p3)];leaves.faces.new(vs);k+=1
            z+=rng.uniform(.27,.34)
        link('Bamboo_Nodes_%02d'%i,bm,[M['node']])
        link('Bamboo_Leaves_%02d'%i,leaves,[M['bamboo_leaf']],False)
        culms.append({'height_m':round(H,3),'radius_m':round(R,3),'leaves':k,'aged':old})
    for j in range(3):
        a=j*2.1+.9;c=Vector((.52*math.cos(a),.52*math.sin(a),0));h=rng.uniform(.28,.45)
        bm=bmesh.new();bmesh.ops.create_cone(bm,cap_ends=True,segments=10,radius1=.06,radius2=.0,depth=h,matrix=Matrix.Translation(c+Vector((0,0,h/2))))
        link('Bamboo_Shoot_%02d'%j,bm,[M['sheath']])
    EXTRA['BambooClump']={'culms':culms,'shoots':3,'leaf_cards':sum(c['leaves'] for c in culms),'two_sided_leaves_required':True,'wind':'static; no shape keys'}

def shrub():
    rng=random.Random(1303);bm=bmesh.new()
    for i in range(7):
        a=i*math.tau/7+rng.uniform(-.2,.2);L=rng.uniform(.45,.75)
        pts=[(0,0,0),(.12*math.cos(a),.12*math.sin(a),.2),(L*.6*math.cos(a),L*.6*math.sin(a),.55),(L*math.cos(a),L*math.sin(a),.75+rng.uniform(0,.2))]
        tube_into(bm,pts,[.045,.035,.022,.012],7)
    for v in bm.verts:v.co.z=max(v.co.z,0.0)
    link('Shrub_Woody_Stems',bm,[M['twig']])
    blobs=[((0,0,.78),(.55,.5,.45)),((.48,-.15,.55),(.42,.38,.36)),((-.5,.1,.56),(.44,.40,.37)),((.1,.45,.6),(.42,.4,.38)),
           ((-.15,-.42,.52),(.40,.36,.34)),((.32,.32,.95),(.35,.33,.3)),((-.3,-.2,1.0),(.34,.32,.3)),((.42,-.4,.38),(.28,.26,.25)),((-.46,.42,.36),(.28,.27,.25))]
    surface=[]
    for i,(c,r) in enumerate(blobs):
        bm=bmesh.new();vs=lumpy_into(bm,c,r,300+i,3,.17,1.7,rng.uniform(0,6))
        surface+= [v.co.copy() for v in vs if v.co.z>.5 and v.normal.z>-.1]
        o=link('Shrub_Leaf_Mass_%02d'%i,bm,[M['shrub_leaf'],M['shrub_dark']]);by_normal(o,0,1,.45,-.7)
    bm=bmesh.new();picks=rng.sample(surface,36)
    for p in picks:
        d=(p-Vector((0,0,.6))).normalized();q=d.to_track_quat('Z','Y').to_matrix().to_4x4()
        bmesh.ops.create_icosphere(bm,subdivisions=2,radius=.05,matrix=Matrix.Translation(p+d*.02)@q@Matrix.Diagonal((1,1,.45,1)))
    link('Shrub_Blossoms',bm,[M['blossom']])
    EXTRA['WildShrub']={'leaf_masses':len(blobs),'stems':7,'blossoms':36,'wind':'static; no shape keys'}

def boulders():
    specs=[((0,0),(1.05,.85,.95),0),((1.05,.35),(.55,.48,.45),1),((-.95,-.25),(.6,.5,.5),2),((.55,-.75),(.32,.3,.26),3),((-.45,.75),(.36,.3,.3),4),((1.45,-.35),(.22,.2,.17),5),((-1.4,.45),(.24,.22,.18),6)]
    rng=random.Random(1304)
    for i,((x,y),r,s) in enumerate(specs):
        c=(x,y,r[2]*.55);bm=bmesh.new();lumpy_into(bm,c,r,500+s,3,.18,1.1,s*1.7)
        chisel(bm,c,r,7 if i<3 else 4,rng);flat_base(bm)
        for f in bm.faces:
            if abs(f.normal.z+1)<1e-3:f.smooth=False
        link('Boulder_%02d'%i,bm,[M['mossy_rock']],None)
    EXTRA['MossBoulderSet']={'boulders':len(specs),'flat_soles':True,'planar_chisel_cuts':True,'moss':'shader mask on upward normals; FBX carries base rock colour only'}

def scree():
    rng=random.Random(1305);R=.85;n=0
    # Low gravel core closes the gaps between stones so the pile reads as one heap.
    bm=bmesh.new();lumpy_into(bm,(0,0,-.02),(R*1.2,R*.95,.36),705,3,.15,2.0);flat_base(bm)
    link('Scree_Gravel_Core',bm,[M['soil_gravel']])
    for ring,count in [(0,1),(.15,5),(.3,9),(.45,12),(.6,15),(.75,18),(.92,16)]:
        for k in range(count):
            a=k*math.tau/count+rng.uniform(-.2,.2)+ring*3;rr=ring*R*rng.uniform(.9,1.1)
            x,y=rr*math.cos(a)*1.25,rr*math.sin(a);s=rng.uniform(.09,.17)*(1.25-ring*.5)
            heap=.42*(1-(rr/R)**2)**1.2 if rr<R else 0
            bm=bmesh.new();vs=lumpy_into(bm,(0,0,0),(s*rng.uniform(1,1.5),s*rng.uniform(.8,1.2),s*rng.uniform(.55,.8)),700+n,1,.35,2.5,rng.uniform(0,6))
            bmesh.ops.rotate(bm,verts=vs,cent=(0,0,0),matrix=Matrix.Rotation(rng.uniform(-.5,.5),3,'X')@Matrix.Rotation(rng.uniform(-.5,.5),3,'Y'))
            low=min(v.co.z for v in vs);z=max(heap-s*.35,-low)  # half-buried in the heap, never below ground
            bmesh.ops.translate(bm,verts=vs,vec=(x,y,z))
            o=link('Scree_Stone_%02d'%n,bm,[M['rock_pale'] if n%3 else M['rock']],False);n+=1
    EXTRA['ScreePile']={'stones':n,'gravel_core':True,'heap_radius_m':R,'loose_pieces':'each stone is a separate mesh for scatter reuse'}

BUILDERS={'CommonPine':pine,'BambooClump':bamboo,'WildShrub':shrub,'MossBoulderSet':boulders,'ScreePile':scree}

def bounds(objects):
    dg=bpy.context.evaluated_depsgraph_get();pts=[o.evaluated_get(dg).matrix_world@v.co for o in objects for v in o.evaluated_get(dg).data.vertices]
    return Vector([min(p[i] for p in pts) for i in range(3)]),Vector([max(p[i] for p in pts) for i in range(3)])

def assemble(aid):
    """Build one asset into the current scene, centred on its bottom; returns mesh objects."""
    global assets,root
    s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
    assets=bpy.data.collections.new('01_Editable_Asset');s.collection.children.link(assets)
    root=bpy.data.objects.new(aid+'_ROOT',None);assets.objects.link(root)
    make_materials();BUILDERS[aid]();bpy.context.view_layer.update()
    objects=[o for o in assets.objects if o.type=='MESH'];lo,hi=bounds(objects)
    shift=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
    for o in objects:o.location-=shift
    bpy.context.view_layer.update();return objects

def build(aid):
    out=ROOT/'Models'/aid/'v001';refs=ROOT/'ArtLibrary/Turnarounds'/f'{aid}_v001'
    if (refs/'views.json').exists():print('ALREADY_COMPLETE',aid,flush=True);return
    out.mkdir(parents=True,exist_ok=True);refs.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;bpy.context.preferences.filepaths.save_version=0
    objects=assemble(aid);lo,hi=bounds(objects);extent=hi-lo;centre=(lo+hi)/2
    studio=bpy.data.collections.new('90_Studio_Not_Exported');s.collection.children.link(studio)
    def add(name,data):
        ob=bpy.data.objects.new(name,data);studio.objects.link(ob);return ob
    cam=add('Reference_Camera',bpy.data.cameras.new('Reference_Camera'));s.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=extent.length*1.08;cam.data.clip_end=1000
    ls=max(extent)*.65
    for name,dr,power in [('Key',(-.8,-1.1,1.5),1100),('Fill',(1.2,-.4,.9),650),('Rim',(.2,1.1,1.3),950)]:
        d=bpy.data.lights.new(name,'AREA');d.energy=power*ls*ls/7;d.shape='DISK';d.size=ls;o=add(name,d);o.location=centre+Vector(dr)*ls;o.rotation_euler=(centre-o.location).to_track_quat('-Z','Y').to_euler()
    s.world=bpy.data.worlds.new('Neutral_Studio');s.world.use_nodes=True;bg=next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND')
    bg.inputs[0].default_value=(.19,.21,.22,1);bg.inputs[1].default_value=.65
    try:s.render.engine='CYCLES'
    except TypeError as e:raise SystemExit('Cycles unavailable: %s'%e)
    s.cycles.device='CPU';s.cycles.samples=24;s.cycles.use_denoising=True
    s.render.resolution_x=1024;s.render.resolution_y=1024;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX';s.view_settings.exposure=-.7
    def position(dr):
        cam.location=centre+Vector(dr).normalized()*cam.data.ortho_scale*2.3;cam.rotation_euler=(centre-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
    position((1,-1,.6));bpy.ops.object.select_all(action='DESELECT')
    for o in [root]+objects:o.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.export_scene.fbx(filepath=str(out/(aid+'_v001.fbx')),use_selection=True,object_types={'MESH','EMPTY'},add_leaf_bones=False,axis_forward='-Z',axis_up='Y',apply_unit_scale=True,bake_anim=False)
    root['stage']='Editable procedural prototype; UV bake, collision, LOD and engine tests pending'
    bpy.ops.wm.save_as_mainfile(filepath=str(out/(aid+'_v001.blend')))
    tris=sum(len(p.vertices)-2 for o in objects for p in o.data.polygons)
    info={'asset':aid,'name_zh':NAMES[aid],'category':CATEGORY[aid],'description':DETAILS[aid],'units':'meters','front':'-Y','pivot':'bottom centre','dimensions_m':list(extent),'mesh_objects':len(objects),'triangles':tris,
          'modeling_method':'procedural Python (build_wild13.py), seeded and reproducible; editable meshes, no generative AI','same_geometry_ten_views':True,'stage':'editable vegetation/rock prototype','uv_baked':False,'collision':False,'lod':False,'unreal_import_verified':False}
    info.update(EXTRA.get(aid,{}))
    (out/'model_info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    from bpy_extras.object_utils import world_to_camera_view
    records=[]
    for name,dr in VIEWS:
        position(dr);dg=bpy.context.evaluated_depsgraph_get()
        projected=[world_to_camera_view(s,cam,e.matrix_world@Vector(p)) for o in objects for e in [o.evaluated_get(dg)] for p in e.bound_box]
        assert all(.005<p.x<.995 and .005<p.y<.995 and p.z>0 for p in projected),(aid,name,'cropped')
        s.render.filepath=str(refs/(name+'.png'));bpy.ops.render.render(write_still=True)
        records.append({'file':name+'.png','direction':dr,'camera_location':list(cam.location),'projection':'orthographic','framing_checked':True});print('VIEW_COMPLETE',aid,name,flush=True)
    (refs/'views.json').write_text(json.dumps({'asset':aid,'source':(out/(aid+'_v001.blend')).relative_to(ROOT).as_posix(),'same_geometry':True,'views':records},indent=2))
    print('ASSET_COMPLETE',aid,flush=True)

if __name__=='__main__':
    for aid in (sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else BUILDERS):build(aid)
