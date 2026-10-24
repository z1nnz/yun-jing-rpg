"""Build six editable sect architecture modules and render ten views per asset.
Run: Blender --background --factory-startup -t 4 --python this_file.py
Optional IDs after -- select assets. Existing completed assets are not overwritten.
"""
import bpy, math, json, sys, random
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
VIEWS=[('01_front',(0,-1,0)),('02_right',(1,0,0)),('03_rear',(0,1,0)),('04_left',(-1,0,0)),
       ('05_front_right',(1,-1,.45)),('06_rear_right',(1,1,.45)),('07_rear_left',(-1,1,.45)),
       ('08_front_left',(-1,-1,.45)),('09_top',(0,0,1)),('10_high_front',(0,-1,1))]

def mat(name,c,metal=0,rough=.6):
    m=bpy.data.materials.new(name); m.diffuse_color=(*c,1); m.use_nodes=True
    n=m.node_tree.nodes; bs=n.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(*c,1)
    bs.inputs['Metallic'].default_value=metal; bs.inputs['Roughness'].default_value=rough
    noise=n.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value=45
    bump=n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.14; bump.inputs['Distance'].default_value=.015
    m.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height']); m.node_tree.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
    return m

def finish(o,name,m,bevel=0):
    o.name=name
    for c in list(o.users_collection): c.objects.unlink(o)
    assets.objects.link(o); o.parent=root; o.data.materials.append(m)
    if bevel:
        mod=o.modifiers.new('Soft_edges','BEVEL'); mod.width=bevel; mod.segments=3
        mod=o.modifiers.new('Weighted_normals','WEIGHTED_NORMAL')
    return o

def box(name,p,s,m,bevel=.012):
    bpy.ops.mesh.primitive_cube_add(size=1,location=p); o=bpy.context.object; o.dimensions=s
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return finish(o,name,m,bevel)

def cyl(name,p,r,d,m):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=r,depth=d,location=p)
    return finish(bpy.context.object,name,m,min(r*.08,.008))

def mesh(name,v,f,m):
    d=bpy.data.meshes.new(name+'_Mesh'); d.from_pydata(v,[],f); d.update()
    o=bpy.data.objects.new(name,d); assets.objects.link(o); o.parent=root; d.materials.append(m); return o

def beam(name,a,b,r,m):
    a,b=Vector(a),Vector(b); o=cyl(name,(a+b)/2,r,(b-a).length,m)
    o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler(); return o

def torus(name,p,major,minor,m,rot=(0,0,0)):
    bpy.ops.mesh.primitive_torus_add(major_segments=64,minor_segments=12,location=p,major_radius=major,minor_radius=minor,rotation=rot)
    o=finish(bpy.context.object,name,m)
    for f in o.data.polygons:f.use_smooth=True
    return o

def lathe(name,profile,p,m,segments=64):
    v=[(p[0]+r*math.cos(i*math.tau/segments),p[1]+r*math.sin(i*math.tau/segments),p[2]+z) for r,z in profile for i in range(segments)]
    f=[(j*segments+i,j*segments+(i+1)%segments,(j+1)*segments+(i+1)%segments,(j+1)*segments+i) for j in range(len(profile)-1) for i in range(segments)]
    o=mesh(name,v,f,m)
    for f in o.data.polygons:f.use_smooth=True
    return o

def leaf(name,a,b,width,m):
    a,b=Vector(a),Vector(b); d=b-a; side=d.cross(Vector((0,0,1)))
    if side.length<.001:side=Vector((1,0,0))
    side.normalize(); mid=a+d*.5; ridge=mid+Vector((0,0,width*.17))
    v=[tuple(a),tuple(mid+side*width),tuple(b),tuple(mid-side*width),tuple(ridge)]
    o=mesh(name,v,[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],m)
    mod=o.modifiers.new('Leaf_thickness','SOLIDIFY');mod.thickness=.002
    return o

def herb(p,scale=1):
    p=Vector(p)
    for j in range(5):
        a=j*math.tau/5; tip=p+Vector((.13*math.cos(a),.13*math.sin(a),.34+.04*(j%2)))*scale
        beam('Herb_Stem',p,tip,.008*scale,green)
        for t in (.35,.65,.9):
            origin=p+(tip-p)*t
            for sign in (-1,1):
                angle=a+sign*1.1
                end=origin+Vector((.14*math.cos(angle),.14*math.sin(angle),.07))*scale
                leaf('Herb_Leaf',origin,end,.047*scale,green if j%2 else sage)

def ribbon(name,points,r,material):
    # A continuous round timber/tile profile, with editable bevel depth.
    bpy.ops.object.select_all(action='DESELECT')
    d=bpy.data.curves.new(name,'CURVE');d.dimensions='3D';d.resolution_u=1
    d.bevel_depth=r;d.bevel_resolution=2
    s=d.splines.new('POLY');s.points.add(len(points)-1)
    for v,p in zip(s.points,points):v.co=(*p,1)
    o=bpy.data.objects.new(name,d);assets.objects.link(o);o.parent=root;d.materials.append(material)
    bpy.context.view_layer.objects.active=o;o.select_set(True)
    bpy.ops.object.convert(target='MESH');o.select_set(False)
    return o

def roof(name,w,d,eave,rise,cx=0,cy=0):
    # Two curved tiled slopes. Ends rise modestly, all tile ribs follow the same surface.
    nx=max(12,int(w/.30));ny=12
    def pt(x,t,sign):
        return (cx+x,cy+sign*d*.5*t,eave+rise*(1-t)**1.5+.20*t**8+.15*(abs(x)/(w*.5))**8*t**3)
    for sign in (-1,1):
        v=[pt(-w/2+w*i/nx,j/ny,sign) for j in range(ny+1) for i in range(nx+1)]
        f=[(j*(nx+1)+i,j*(nx+1)+i+1,(j+1)*(nx+1)+i+1,(j+1)*(nx+1)+i) for j in range(ny) for i in range(nx)]
        if sign<0:f=[tuple(reversed(face)) for face in f]
        o=mesh(name+'_Tile_Bed',v,f,tile);m=o.modifiers.new('Roof_Thickness','SOLIDIFY');m.thickness=.10
        for i in range(nx+1):
            x=-w/2+w*i/nx
            ribbon(name+'_Tile_Roll',[pt(x,j/ny,sign) for j in range(ny+1)],.045,tilelight if i%3==0 else tile)
        for j in range(2,ny+1,2):
            ribbon(name+'_Tile_Overlap',[pt(-w/2+w*i/nx,j/ny,sign) for i in range(nx+1)],.018,tilelight)
        for x in (-w/2,w/2):ribbon(name+'_Gable_Bargeboard',[tuple(Vector(pt(x,j/ny,sign))+Vector((0,0,-.09))) for j in range(ny+1)],.105,wood)
        ribbon(name+'_Eave_Fascia',[tuple(Vector(pt(-w/2+w*i/nx,1,sign))+Vector((0,0,-.10))) for i in range(nx+1)],.10,wood)
    ribbon(name+'_Ridge',[(cx-w/2-.14,cy,eave+rise+.22),(cx-w/2+.18,cy,eave+rise+.07),(cx+w/2-.18,cy,eave+rise+.07),(cx+w/2+.14,cy,eave+rise+.22)],.12,tilelight)
    for x in (-w/2+.15,w/2-.15):
        beam(name+'_Ridge_End',(cx+x,cy,eave+rise+.12),(cx+x*1.035,cy,eave+rise+.48),.085,gold)

def steps(width,yfront,floor,n=5):
    for i in range(n):
        h=floor*(i+1)/n;y=yfront-(n-i-.5)*.32
        box('Stair_Tread_%02d'%i,(0,y,h/2),(width,.34,h),stone,.025)

def terrace(w,d,h=.6,stairs=4):
    box('Stone_Foundation',(0,0,h/2),(w,d,h),stone,.065)
    box('Terrace_Coping',(0,0,h-.035),(w+.14,d+.14,.11),pale,.025)
    for x in range(int(w)):
        box('Terrace_Front_Joint',(-w/2+x+.5,-d/2-.006,h*.47),(.015,.016,h*.65),dark,.001)
    steps(min(3.2,w*.5),-d/2,h,stairs)

def post(x,y,z0,h):
    box('Column_Stone_Base',(x,y,z0+.12),(.46,.46,.24),pale,.04)
    cyl('Timber_Column',(x,y,z0+.24+h/2),.15,h,wood)
    for z in (z0+.34,z0+h+.13):cyl('Column_Collar',(x,y,z),.19,.11,board)
    for axis in (0,1):
        dim=(.83,.18,.14) if axis==0 else (.18,.83,.14)
        box('Bracket_Crossarm',(x,y,z0+h+.23),dim,board,.025)
    for s in (-1,1):
        beam('Column_Knee_Brace',(x,y,z0+h-.48),(x+s*.55,y,z0+h+.12),.065,wood)

def window(x,y,z,w=1.2,h=1.3):
    box('Window_Paper',(x,y+.035,z),(w,.045,h),paper,.005)
    for xx in (-w/2,w/2):box('Window_Frame',(x+xx,y,z),(.075,.12,h+.12),wood)
    for zz in (-h/2,h/2):box('Window_Frame',(x,y,z+zz),(w+.12,.12,.075),wood)
    for i in range(1,6):box('Window_Lattice_V',(x-w/2+i*w/6,y-.035,z),(.025,.055,h),wood,.002)
    for i in range(1,5):box('Window_Lattice_H',(x,y-.04,z-h/2+i*h/5),(w,.055,.025),wood,.002)

def plaque(name,x,y,z,w=2,h=.65):
    box(name+'_Blank_Nameboard',(x,y,z),(w,.15,h),jade,.045)
    for zz in (-h/2,h/2):box(name+'_Border',(x,y-.087,z+zz),(w+.04,.035,.035),gold,.008)
    for xx in (-w/2,w/2):box(name+'_Border',(x+xx,y-.087,z),(.035,.035,h),gold,.008)
    # Unnamed sect: crest in the centre, blank space on both sides for future lettering.
    torus(name+'_Sun_Crest',(x,y-.10,z),h*.24,.018,gold,(math.pi/2,0,0))
    o=box(name+'_Jade_Crest',(x,y-.11,z),(h*.18,.025,h*.18),gold,.003);o.rotation_euler.y=math.pi/4

def railing(a,b,z):
    a,b=Vector(a),Vector(b);n=max(1,round((b-a).length/.9))
    for i in range(n+1):
        p=a+(b-a)*i/n
        key=(round(p.x,4),round(p.y,4),round(z,4))
        if key in rail_posts:continue
        rail_posts.add(key)
        box('Rail_Post',(p.x,p.y,z+.42),(.13,.13,.84),wood,.02)
        cyl('Rail_Cap',(p.x,p.y,z+.87),.10,.09,gold)
    for zz in (.28,.74):beam('Rail_Crossbar',(a.x,a.y,z+zz),(b.x,b.y,z+zz),.045,board)

def gate():
    terrace(9,3.5,.48,3)
    for x in (-3.5,-1.65,1.65,3.5):post(x,0,.48,3.5 if abs(x)<2 else 2.6)
    box('Main_Arch_Lintel',(0,0,3.91),(4.1,.36,.32),wood,.04)
    roof('Central_Gateway_Roof',4.9,2.7,4.22,1.0)
    for x in (-2.7,2.7):
        box('Side_Arch_Lintel',(x,0,3.02),(2.35,.3,.26),wood,.04)
        roof('Side_Gateway_Roof',2.6,2.15,3.29,.66,x)
    plaque('Sect_Gate',0,-.23,3.60,2.5,.57)
    for x in (-3.5,3.5):
        box('Gate_Foot_Plinth',(x,-.12,.83),(.7,.75,.7),stone,.06)
        box('Gate_Jade_Inlay',(x,-.51,.87),(.34,.035,.38),jade,.03)
    for x in (-2.6,2.6):
        for xx in (-.38,0,.38):box('Side_Screen_Slat',(x+xx,0,1.55),(.065,.14,1.4),wood,.012)
        box('Side_Screen_Base',(x,0,.9),(1.5,.19,.18),wood)

def hall():
    terrace(12.5,8.4,.9,6)
    # Enclosed inner hall with an open 2.4 m entrance; porch remains walkable.
    box('Hall_Back_Wall',(0,2.62,2.6),(9.6,.18,3.4),plaster,.025)
    for x in (-4.7,4.7):box('Hall_Side_Wall',(x,.3,2.6),(.18,4.8,3.4),plaster,.025)
    for x in (-3.0,3.0):
        box('Hall_Front_Wall',(x,-2.1,2.6),(3.6,.18,3.4),plaster,.025)
        window(x,-2.22,2.55,2,1.65)
    box('Door_Header',(0,-2.1,4.05),(2.4,.20,.5),wood,.025)
    for x in (-1.2,1.2):box('Door_Jamb',(x,-2.14,2.35),(.16,.25,2.9),wood)
    for x in (-5.2,-2.6,0,2.6,5.2):
        for y in (-3.25,3.25):
            if x==0 and y<0:continue
            post(x,y,.9,3.2)
    for y in (-3.25,3.25):box('Grand_Crossbeam',(0,y,4.28),(11.3,.27,.28),wood,.035)
    for x in (-5.2,5.2):box('Side_Crossbeam',(x,0,4.28),(.27,6.7,.28),wood,.035)
    # A full main roof, plus a separate entrance canopy beneath its front slope.
    roof('Grand_Hall_Roof',12.1,8.0,4.55,2.1)
    roof('Entry_Canopy',4.8,2.0,3.9,.58,0,-3.7)
    plaque('Grand_Hall',0,-2.29,3.68,2.1,.48)
    for x in (-5.6,5.6):railing((x,-2.6,0),(x,3.5,0),.9)
    for a,b in [((-5.6,-3.7,0),(-2,-3.7,0)),((2,-3.7,0),(5.6,-3.7,0))]:railing(a,b,.9)
    # A simple stone dais visible through the entrance; not a furnished interior.
    box('Inner_Ritual_Dais',(0,1.5,1.08),(3.2,1.5,.36),stone,.055)
    box('Altar_Top',(0,1.6,1.95),(2.4,.7,.14),board,.035)
    for x in (-1,1):box('Altar_Leg',(x,1.6,1.58),(.14,.55,.65),wood,.02)

def dormitory():
    terrace(8.8,6.3,.54,3)
    box('Dorm_Back_Wall',(0,2.1,2.05),(7.7,.16,3.02),plaster,.025)
    for x in (-3.8,3.8):box('Dorm_End_Wall',(x,.1,2.05),(.16,4.1,3.02),plaster,.025)
    box('Room_Partition',(0,.1,2.05),(.14,4.1,3.02),plaster,.02)
    # Two independent room entrances, solid timber doors and lattice windows.
    for side in (-1,1):
        cx=side*1.9
        dx=cx-side*.65
        left=cx-1.85;right=cx+1.85
        for a,b in ((left,dx-.57),(dx+.57,right)):
            box('Room_Front_Wall',((a+b)/2,-1.95,2.05),(b-a,.15,3.02),plaster,.02)
        box('Room_Door_Header',(dx,-1.95,3.15),(1.14,.15,.82),plaster,.02)
        box('Room_Door',(dx,-2.06,1.64),(1.1,.12,2.2),board,.025)
        for i in range(6):box('Door_Plank_Joint',(dx-.48+i*.19,-2.13,1.64),(.012,.01,2.1),wood,.001)
        cyl('Door_Latch_Base',(dx+side*.33,-2.15,1.6),.05,.03,gold).rotation_euler.x=math.pi/2
        torus('Door_Ring_Handle',(dx+side*.33,-2.18,1.57),.07,.012,gold,(math.pi/2,0,0))
        window(cx+side*.70,-2.06,2.05,.9,1.1)
    for x in (-3.85,0,3.85):
        for y in (-2.65,2.3):post(x,y,.54,2.75)
    for y in (-2.65,2.3):box('Dorm_Crossbeam',(0,y,3.45),(8.2,.23,.25),wood,.035)
    roof('Dormitory_Roof',9.2,6.5,3.58,1.45)
    for x in (-3.9,3.9):railing((x,-2.8,0),(x,-1.8,0),.54)

def training():
    terrace(8,7,.30,2)
    # Repeated stone pavers leave visible seams.
    for i in range(10):
        for j in range(8):box('Training_Paver',(-3.6+i*.8,-3.05+j*.85,.325),(.77,.82,.06),pale if (i+j)%3 else stone,.014)
    for x,y in [(-2.5,1.6),(0,1.6),(2.5,1.6)]:
        cyl('Dummy_Stone_Socket',(x,y,.48),.35,.26,stone)
        cyl('Training_Dummy_Trunk',(x,y,1.27),.16,1.5,board)
        cyl('Training_Dummy_Head',(x,y,2.16),.22,.27,rope)
        for z in (1.0,1.35,1.65):torus('Dummy_Rope_Wrap',(x,y,z),.17,.025,rope)
        beam('Dummy_Arms',(x-.53,y,1.6),(x+.53,y,1.6),.085,wood)
        beam('Dummy_Angled_Leg',(x,y,1.0),(x+.35,y-.35,.65),.075,wood)
    railing((-3.65,2.9,0),(3.65,2.9,0),.36)
    for x in (-3.65,3.65):railing((x,.4,0),(x,2.9,0),.36)
    # Footwork marks are shallow jade stone inlays, not magical effects.
    for x in (-1.6,0,1.6):
        for y in (-1.7,-.75):box('Footwork_Marker',(x,y,.362),(.2,.38,.012),jade,.04)

def garden():
    box('Garden_Ground',(0,0,.08),(6.3,4.9,.16),soil,.07)
    box('Garden_Main_Path',(0,-1.75,.16),(6.1,1.1,.16),pale,.025)
    for x in (-2,0,2):
        box('Raised_Bed_Soil',(x,.45,.30),(1.6,2.5,.4),soil,.035)
        for dx in (-.85,.85):box('Bed_Stone_Edge',(x+dx,.45,.29),(.15,2.7,.42),stone,.035)
        for y in (-.9,1.8):box('Bed_Stone_End',(x,y,.29),(1.85,.15,.42),stone,.035)
        stage=int(x/2)+1;scale=(.38,.68,1.0)[stage]
        for dx in (-.37,.37):
            for y in (-.4,.4,1.2):herb((x+dx,y,.51),scale)
        box('Bed_Stage_Plaque',(x,-1.02,.53),(.38,.065,.26),wood,.02)
        for i in range(stage+1):box('Growth_Stage_Mark',(x+(i-stage/2)*.08,-1.058,.54),(.028,.01,.14),gold,.003)
    # Open stone irrigation channel and quiet water surface along the rear.
    box('Channel_Base',(0,2.15,.16),(6.2,.48,.12),stone,.015)
    for y in (1.91,2.39):box('Channel_Wall',(0,y,.25),(6.2,.09,.25),stone,.015)
    box('Channel_Water',(0,2.15,.23),(6.05,.35,.015),water,.003)
    for x in (-3.025,3.025):box('Channel_End',(x,2.15,.25),(.08,.48,.25),stone,.012)

def platform():
    bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=2.8,depth=.32,location=(0,0,.16))
    finish(bpy.context.object,'Octagonal_Foundation',stone,.035)
    cyl('Raised_Cultivation_Dais',(0,0,.39),2.5,.18,pale)
    for r in (1.0,1.6,2.18):torus('Concentric_Jade_Inlay',(0,0,.487),r,.025,jade)
    for i in range(8):
        a=i*math.tau/8
        beam('Radial_Brass_Inlay',(1.0*math.cos(a),1.0*math.sin(a),.49),(2.18*math.cos(a),2.18*math.sin(a),.49),.012,gold)
        x,y=2.24*math.cos(a),2.24*math.sin(a)
        cyl('Spirit_Stone_Socket',(x,y,.54),.17,.10,bronze)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=.16,location=(x,y,.68))
        o=finish(bpy.context.object,'Spirit_Stone_Insert',jade);o.scale.z=1.65
    cyl('Meditation_Seat_Base',(0,0,.57),.64,.18,wood)
    lathe('Woven_Meditation_Seat',[(0,.65),(.48,.65),(.55,.71),(.50,.80),(0,.82)],(0,0,0),rope)
    for r in (.12,.22,.32,.42):torus('Seat_Weave',(0,0,.817-r*.03),r,.009,straw)
    steps(1.8,-2.4,.30,2)
    for x in (-1.65,1.65):
        box('Array_Stele_Base',(x,1.6,.60),(.55,.55,.24),stone,.04)
        box('Array_Stele',(x,1.6,1.1),(.34,.28,.9),jade,.06)
        torus('Stele_Crest',(x,1.45,1.17),.10,.018,gold,(math.pi/2,0,0))

BUILDERS={'SectGate':gate,'SectGrandHall':hall,'DiscipleResidence':dormitory,'TrainingGround':training,'SpiritHerbGarden':garden,'CultivationPlatform':platform}
NAMES={'SectGate':'宗門山門','SectGrandHall':'宗門大殿','DiscipleResidence':'弟子居所','TrainingGround':'演武場','SpiritHerbGarden':'靈藥圃','CultivationPlatform':'修煉台／聚靈陣'}
DETAILS={'SectGate':'Three-bay mountain gate; blank crest plaque for future sect name.', 'SectGrandHall':'Main hall, open central entrance, porch and basic inner altar; not a furnished interior.', 'DiscipleResidence':'Two-room prototype with independent closed doors and wall openings; no hinges, animation or furnishings yet.', 'TrainingGround':'Paved training court with three static dummies; no animation.', 'SpiritHerbGarden':'Three adjacent planted beds showing small, medium and large growth appearances; no growth animation or harvesting states.', 'CultivationPlatform':'Static cultivation dais with jade inlay, stone sockets and woven seat; no gameplay or VFX.'}

def actual_bounds(objects):
    dg=bpy.context.evaluated_depsgraph_get()
    pts=[e.matrix_world@v.co for o in objects for e in [o.evaluated_get(dg)] for v in e.data.vertices]
    return Vector([min(p[i] for p in pts) for i in range(3)]),Vector([max(p[i] for p in pts) for i in range(3)])

ids=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else list(BUILDERS)
for aid in ids:
    out=ROOT/'Models'/aid/'v001';refs=ROOT/'ArtLibrary/Turnarounds'/f'{aid}_v001'
    if (refs/'views.json').exists():print('ALREADY_COMPLETE',aid,flush=True);continue
    out.mkdir(parents=True,exist_ok=True);refs.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;bpy.context.preferences.filepaths.save_version=0
    scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    assets=bpy.data.collections.new('01_Editable_Asset');scene.collection.children.link(assets)
    root=bpy.data.objects.new(aid+'_ROOT',None);assets.objects.link(root);root['stage']=DETAILS[aid]
    wood=mat('Dark_Chestnut',(.16,.065,.028));board=mat('Warm_Timber',(.29,.14,.055))
    stone=mat('Blue_Gray_Stone',(.24,.30,.31));pale=mat('Pale_Stone',(.45,.49,.46));dark=mat('Recess_Shadow',(.065,.085,.08))
    jade=mat('Celadon_Jade',(.08,.29,.24),.18,.32);gold=mat('Aged_Brass',(.51,.31,.075),.6,.34)
    bronze=mat('Socket_Bronze',(.22,.14,.06),.6,.4);plaster=mat('Warm_Lime_Plaster',(.67,.62,.50))
    tile=mat('Blue_Green_Tiles',(.065,.15,.155));tilelight=mat('Tile_Roll_Highlight',(.11,.22,.22))
    paper=mat('Warm_Window_Paper',(.61,.49,.29));soil=mat('Dark_Loam',(.085,.053,.025))
    green=mat('Mature_Herb',(.10,.25,.055));sage=mat('Young_Leaf',(.28,.40,.12))
    rope=mat('Natural_Hemp',(.48,.35,.17));straw=mat('Woven_Straw',(.62,.45,.21));water=mat('Channel_Water',(.055,.20,.20),.2,.18)
    rail_posts=set()
    BUILDERS[aid]();bpy.context.view_layer.update()
    objects=[o for o in assets.objects if o.type=='MESH'];lo,hi=actual_bounds(objects)
    shift=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
    for o in objects:o.location-=shift
    bpy.context.view_layer.update();lo,hi=actual_bounds(objects);centre=(lo+hi)/2;extent=hi-lo
    studio=bpy.data.collections.new('90_Studio_Not_Exported');scene.collection.children.link(studio)
    def studio_obj(name,data):
        o=bpy.data.objects.new(name,data);studio.objects.link(o);return o
    cam=studio_obj('Reference_Camera',bpy.data.cameras.new('Reference_Camera'));scene.camera=cam;cam.data.type='ORTHO'
    cam.data.clip_start=.01;cam.data.clip_end=1000;cam.data.ortho_scale=max(extent.length*1.08,.5)
    # Scale light positions and power with architecture dimensions for consistent exposures.
    ls=max(extent)*.65
    for name,direction,power in [('Key',(-.8,-1.1,1.5),1100),('Fill',(1.2,-.4,.9),650),('Rim',(.2,1.1,1.3),950)]:
        d=bpy.data.lights.new(name,'AREA');d.energy=power*ls*ls/4;d.shape='DISK';d.size=ls
        o=studio_obj(name,d);o.location=centre+Vector(direction)*ls;o.rotation_euler=(centre-o.location).to_track_quat('-Z','Y').to_euler()
    scene.world=bpy.data.worlds.new('Neutral_Studio');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.19,.21,.22,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.65
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=12;scene.cycles.use_denoising=True
    scene.render.resolution_x=1024;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
    def position(direction):
        cam.location=centre+Vector(direction).normalized()*cam.data.ortho_scale*2.3
        cam.rotation_euler=(centre-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
    position((1,-1,.65));bpy.ops.object.select_all(action='DESELECT')
    for o in [root]+objects:o.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.export_scene.fbx(filepath=str(out/(aid+'_v001.fbx')),use_selection=True,object_types={'MESH','EMPTY'},add_leaf_bones=False,axis_forward='-Z',axis_up='Y',apply_unit_scale=True,bake_anim=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/(aid+'_v001.blend')))
    info={'asset':aid,'name_zh':NAMES[aid],'stage':'editable_architecture_prototype','description':DETAILS[aid],'units':'meters','front':'-Y','dimensions_m':list(extent),'mesh_objects':len(objects),'bounds_method':'evaluated mesh vertices','modeling_method':'procedural mesh construction; ten views rendered from the same model','uv_baked':False,'collision':False,'lod':False,'unreal_import_verified':False}
    (out/'model_info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2))
    from bpy_extras.object_utils import world_to_camera_view
    records=[]
    for name,direction in VIEWS:
        position(direction);dg=bpy.context.evaluated_depsgraph_get()
        projected=[world_to_camera_view(scene,cam,e.matrix_world@Vector(p)) for o in objects for e in [o.evaluated_get(dg)] for p in e.bound_box]
        assert all(.005<p.x<.995 and .005<p.y<.995 and p.z>0 for p in projected),(aid,name,'cropped')
        scene.render.filepath=str(refs/(name+'.png'));bpy.ops.render.render(write_still=True)
        records.append({'file':name+'.png','direction':direction,'camera_location':list(cam.location),'projection':'orthographic','framing_checked':True})
        print('VIEW_COMPLETE',aid,name,flush=True)
    (refs/'views.json').write_text(json.dumps({'asset':aid,'source':str((out/(aid+'_v001.blend')).relative_to(ROOT)),'same_geometry':True,'views':records},indent=2))
    print('ASSET_COMPLETE',aid,flush=True)

