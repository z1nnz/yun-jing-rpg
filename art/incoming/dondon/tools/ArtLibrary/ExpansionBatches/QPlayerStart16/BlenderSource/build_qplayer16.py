"""First-batch editable Q-style blockouts. No overwrite of completed asset versions.
Blender --background --python-exit-code 1 --python this_file.py -- [asset IDs|preview]
Only writes within QPlayerStart16. Installation into main Models is a separate step.
"""
import bpy, bmesh, math, json, sys, hashlib
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

BATCH=Path(__file__).resolve().parents[1]
VIEWS=[('01_front',(0,-1,0)),('02_right',(1,0,0)),('03_rear',(0,1,0)),('04_left',(-1,0,0)),
       ('05_front_right',(1,-1,.45)),('06_rear_right',(1,1,.45)),('07_rear_left',(-1,1,.45)),
       ('08_front_left',(-1,-1,.45)),('09_top',(0,0,1)),('10_high_front',(0,-1,1))]
ASSETS={
 'QMaleBase':('BODY01','男修基底'), 'QFemaleBase':('BODY02','女修基底'),
 'QTopknotHair':('HAIR01','束髮髻'), 'QDoubleBunHair':('HAIR02','雙低髻'),
 'QMaleNoviceOutfit':('CLOTH01','男新手服'), 'QFemaleNoviceOutfit':('CLOTH02','女新手服'),
 'QMountainRabbit':('CREATURE01','山兔'), 'QMountainBoar':('CREATURE02','山豬'),
 'QSpiritStone':('ITEM01','靈石'), 'QPillBottle':('ITEM02','丹瓶'), 'QQiManual':('ITEM04','煉氣訣書冊'),
 'QAptitudeCrystal':('ASSESS01','測靈晶石'), 'QCaveEntrance':('HOME01','洞府入口'),
 'QCaveFloor':('HOME02','洞府地板'), 'QCaveWall':('HOME03','洞府直牆'), 'QCaveDoor':('HOME06','洞府門')}
M={}; objects=[]

def material(name,color,rough=.65,metal=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    return m

def reset():
    global objects,M
    bpy.ops.wm.read_factory_settings(use_empty=True);objects=[]
    bpy.context.preferences.filepaths.save_version=0
    bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
    colors={'skin':(.73,.43,.29),'innerEar':(.61,.27,.21),'ivory':(.77,.70,.54),
      'jade':(.20,.36,.32),'jadeLight':(.35,.53,.44),'jadeDark':(.09,.20,.18),
      'cloth':(.15,.18,.18),'hair':(.047,.034,.025),'hairLight':(.085,.059,.039),
      'brown':(.21,.115,.055),'brownLight':(.34,.21,.11),'sole':(.09,.065,.04),
      'white':(.94,.91,.80),'iris':(.20,.085,.027),'black':(.014,.009,.006),
      'pink':(.60,.30,.29),'fur':(.66,.59,.45),'furLight':(.88,.81,.65),
      'boar':(.24,.17,.12),'boarLight':(.38,.27,.18),'stone':(.36,.42,.40),
      'stoneDark':(.23,.29,.28),'stoneLight':(.50,.55,.50),'gold':(.57,.37,.13),
      'crystal':(.10,.55,.45),'crystalLight':(.35,.79,.65),'paper':(.80,.72,.51)}
    M={k:material(k,v,.38 if 'crystal' in k else .72,.3 if k=='gold' else 0) for k,v in colors.items()}

def finish(o,name,mat,smooth=True):
    o.name=name;o.data.materials.append(M[mat]);objects.append(o)
    if o.type=='MESH':
        for p in o.data.polygons:p.use_smooth=smooth
    return o

def mesh(name,verts,faces,mat,smooth=True):
    d=bpy.data.meshes.new(name+'_mesh');d.from_pydata(verts,[],faces);d.update()
    bm=bmesh.new();bm.from_mesh(d);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(d);bm.free()
    o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);return finish(o,name,mat,smooth)

def ell(name,pos,scale,mat,rot=(0,0,0),segments=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=20,location=pos)
    o=bpy.context.object;o.scale=scale;o.rotation_euler=rot
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return finish(o,name,mat)

def box(name,pos,size,mat,bevel=.015,rot=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(size=1,location=pos);o=bpy.context.object;o.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.rotation_euler=rot
    if bevel:
        mod=o.modifiers.new('Soft_edges','BEVEL');mod.width=bevel;mod.segments=3
        bpy.ops.object.modifier_apply(modifier=mod.name)
        n=o.modifiers.new('Weighted_normals','WEIGHTED_NORMAL');n.keep_sharp=True
    return finish(o,name,mat,True)

def tube(name,points,radii,mat,sides=16):
    verts=[];faces=[]
    for j,p in enumerate(points):
        p=Vector(p);t=(Vector(points[min(j+1,len(points)-1)])-Vector(points[max(0,j-1)])).normalized()
        u=t.cross(Vector((0,1,0)))
        if u.length<.01:u=t.cross(Vector((1,0,0)))
        u.normalize();v=t.cross(u)
        for i in range(sides):verts.append(p+(u*math.cos(i*math.tau/sides)+v*math.sin(i*math.tau/sides))*radii[j])
    for j in range(len(points)-1):
        for i in range(sides):faces.append((j*sides+i,j*sides+(i+1)%sides,(j+1)*sides+(i+1)%sides,(j+1)*sides+i))
    faces.extend([tuple(reversed(range(sides))),tuple((len(points)-1)*sides+i for i in range(sides))])
    return mesh(name,verts,faces,mat)

def rings(name,rows,mat,n=40,start=0,end=math.tau,cap=True):
    # rows: z, x radius, y radius. Seam duplicates intentionally allow open robe panels.
    verts=[];faces=[]
    for z,rx,ry in rows:
        for i in range(n+1):
            a=start+(end-start)*i/n;verts.append((rx*math.sin(a),-ry*math.cos(a),z))
    for j in range(len(rows)-1):
        for i in range(n):
            a=j*(n+1)+i;faces.append((a,a+1,a+n+2,a+n+1))
    if cap:
        faces.append(tuple(reversed(range(n+1))));faces.append(tuple((len(rows)-1)*(n+1)+i for i in range(n+1)))
    o=mesh(name,verts,faces,mat)
    if not cap:
        m=o.modifiers.new('Fabric_thickness','SOLIDIFY');m.thickness=.005
    return o

def ribbon(name,points,width,mat):
    verts=[]
    for x,y,z in points:verts.extend([(x-width/2,y,z),(x+width/2,y,z)])
    o=mesh(name,verts,[(i*2,i*2+1,i*2+3,i*2+2) for i in range(len(points)-1)],mat)
    m=o.modifiers.new('Fabric_thickness','SOLIDIFY');m.thickness=.004
    return o

def base(female=False):
    k=.96 if female else 1.0
    ell('Head',(0,0,.975),(.193*k,.161,.205),'skin')
    # Closed mannequin underlayer; no anatomical details.
    rings('Underlayer_Torso',[(.38,.115*k,.073),(.47,.125*k,.083),(.62,.112*k,.076),(.74,.142*k,.071),(.79,.062,.055)],'cloth')
    tube('Neck',[(0,0,.74),(0,0,.83)],[.055,.054],'skin')
    for side in (-1,1):
        s='L' if side<0 else 'R'
        ell('Ear_'+s,(side*.19*k,0,.96),(.038,.028,.052),'skin')
        ell('Ear_inner_'+s,(side*.213*k,-.018,.96),(.019,.008,.031),'innerEar')
        tube('Arm_'+s,[(side*.12*k,0,.74),(side*.207*k,0,.615),(side*.28*k,-.006,.48)],[.046,.038,.029],'skin')
        ell('Palm_'+s,(side*.29*k,-.006,.452),(.035,.022,.041),'skin',rot=(0,side*-.22,0))
        for i in range(4):
            x=side*(.268*k+i*.014);z=.426+abs(i-1.3)*.004
            tube('Finger_'+s+str(i),[(x,-.009,z+.016),(x+side*.009,-.014,z-.022)],[.008,.006],'skin',10)
        tube('Thumb_'+s,[(side*.266*k,-.008,.458),(side*.246*k,-.028,.43)],[.011,.007],'skin',12)
        tube('Leg_'+s,[(side*.067*k,0,.43),(side*.075*k,0,.24),(side*.076*k,0,.073)],[.063,.051,.039],'cloth')
        box('Foot_'+s,(side*.076*k,-.022,.042),(.09,.16,.084),'cloth',.035)
        ex=side*.074*k
        ell('Eye_white_'+s,(ex,-.145,.986),(.052,.025,.059),'white')
        ell('Iris_'+s,(ex,-.166,.985),(.030,.012,.041),'iris')
        ell('Pupil_'+s,(ex,-.176,.986),(.017,.005,.028),'black')
        ell('Eye_glint_'+s,(ex-.009,-.181,1.002),(.009,.003,.012),'white',segments=20)
        tube('Upper_lid_'+s,[(ex-.045,-.158,1.013),(ex-.022,-.173,1.042),(ex+.017,-.171,1.044),(ex+.045,-.156,1.016)],[.006]*4,'hair',10)
        tube('Brow_'+s,[(ex-.038,-.145,1.07),(ex,-.157,1.081),(ex+.034,-.143,1.067)],[.006,.010,.004],'hair',10)
    ell('Nose',(0,-.163,.932),(.025,.021,.022),'skin')
    tube('Smile',[(-.029,-.147,.892),(0,-.158,.885),(.029,-.147,.892)],[.0035,.004,.0035],'pink',10)

def hair(female=False):
    k=.96 if female else 1.;n=48;steps=14;verts=[];faces=[]
    for j in range(steps+1):
        for i in range(n):
            a=i*math.tau/n
            # front hairline at forehead; back cap extends toward nape.
            limit=1.32+.76*(1-math.cos(a))/2
            t=.025+(limit-.025)*j/steps
            verts.append((.202*k*math.sin(t)*math.sin(a),-.174*math.sin(t)*math.cos(a),.977+.215*math.cos(t)))
    for j in range(steps):
        for i in range(n):
            ni=(i+1)%n;faces.append((j*n+i,j*n+ni,(j+1)*n+ni,(j+1)*n+i))
    mesh('Hair_cap',verts,faces,'hair')
    for j in range(7):
        x=(j-3)*.044*k
        rows=[(x*.45,-.058,1.182-abs(x)*.16,.012,.008),
              (x*.8,-.112,1.164-abs(x)*.17,.032,.013),
              (x,-.151+abs(x)*.16,1.111-abs(x)*.12,.031,.015),
              (x-.018,-.166+abs(x)*.22,1.046+abs(x)*.05,.016,.010),
              (x-.029,-.162+abs(x)*.23,1.025+abs(x)*.07,.001,.001)]
        verts=[];faces=[];sides=16
        for xx,y,z,w,d in rows:
            for i in range(sides):
                a=i*math.tau/sides;verts.append((xx+w*math.cos(a),y+d*math.sin(a),z))
        for row in range(4):
            for i in range(sides):faces.append((row*sides+i,row*sides+(i+1)%sides,(row+1)*sides+(i+1)%sides,(row+1)*sides+i))
        mesh('Swept_fringe_%02d'%j,verts,faces,'hairLight' if j%3==0 else 'hair')
    for side in (-1,1):
        ell('Side_lock_'+str(side),(side*.176*k,-.048,1.014),(.027,.087,.112),'hair',rot=(0,side*.1,0))
    if female:
        for side in (-1,1):
            ell('Low_bun_'+str(side),(side*.20,.063,.96),(.071,.067,.075),'hair')
            tube('Bun_tie_'+str(side),[(side*.205,-.002,.97),(side*.24,.026,.97),(side*.218,.083,.97)],[.012]*3,'jadeLight')
            ribbon('Bun_ribbon_'+str(side),[(side*.214,.015,.935),(side*.22,.007,.88),(side*.239,.01,.845)],.024,'jade')
    else:
        ell('Topknot',(0,.025,1.215),(.085,.067,.073),'hair')
        rings('Topknot_band',[(1.174,.068,.059),(1.195,.073,.063)],'jadeLight')
        for i in (-1,0,1):ell('Topknot_lock'+str(i),(i*.026,.011,1.247),(.028,.053,.044),'hairLight' if i==0 else 'hair',rot=(0,i*.12,0))

def outfit(female=False):
    k=.96 if female else 1.0
    rings('Ivory_tunic',[(.36,.16*k,.096),(.42,.15*k,.094),(.59,.12*k,.086),(.72,.147*k,.083),(.79,.061,.058)],'ivory')
    rings('Open_jade_robe',[(.355,.184*k,.112),(.46,.15*k,.106),(.60,.131*k,.094),(.72,.155*k,.092),(.78,.075,.067)],'jade',start=.49,end=math.tau-.49,cap=False)
    ribbon('Cross_collar_A',[(-.051,-.047,.795),(-.022,-.080,.762),(.012,-.096,.727)],.029,'white')
    ribbon('Cross_collar_B',[(.052,-.052,.795),(.015,-.092,.744),(-.033,-.103,.684),(-.085,-.102,.62)],.029,'white')
    rings('Waist_sash',[(.575,.139*k,.107),(.615,.138*k,.105)],'brown')
    ribbon('Sash_tail_A',[(.025,-.113,.60),(.027,-.123,.52),(.015,-.126,.44)],.029,'brownLight')
    ribbon('Sash_tail_B',[(.055,-.112,.60),(.064,-.119,.53),(.087,-.116,.48)],.025,'brown')
    box('Sash_knot',(.037,-.119,.592),(.062,.026,.040),'brownLight',.01)
    for side in (-1,1):
        s=str(side)
        ell('Shoulder_cap_'+s,(side*.133*k,0,.735),(.065,.064,.070),'jade',rot=(0,side*-.35,0))
        tube('Sleeve_ivory_'+s,[(side*.13*k,0,.744),(side*.20*k,0,.641),(side*.24*k,0,.554)],[.055,.052,.041],'ivory')
        tube('Sleeve_jade_'+s,[(side*.14*k,0,.735),(side*.18*k,0,.675),(side*.22*k,0,.604)],[.061,.058,.056],'jade')
        tube('Cuff_'+s,[(side*.237*k,0,.565),(side*.25*k,0,.54)],[.044,.041],'brownLight')
        tube('Trouser_'+s,[(side*.076*k,0,.414),(side*.08*k,0,.28),(side*.078*k,0,.153)],[.072,.075,.050],'cloth')
        box('Boot_sole_'+s,(side*.078*k,-.033,.023),(.112,.183,.046),'sole',.018)
        box('Boot_toe_'+s,(side*.078*k,-.038,.069),(.106,.174,.091),'brown',.035)
        tube('Boot_ankle_'+s,[(side*.078*k,.009,.065),(side*.078*k,.009,.155)],[.054,.055],'brown')
        for j in range(3):
            z=.089+j*.021
            tube('Boot_lace_'+s+str(j),[(side*.078*k-.034,-.045,z),(side*.078*k+.034,-.045,z+.014)],[.004]*2,'brownLight',8)
    # Cloth seam piping marks panels and does not create separate asset counts.
    for side in (-1,1):
        tube('Robe_edge_'+str(side),[(side*.085,-.097,.365),(side*.070,-.099,.46),(side*.063,-.090,.565)],[.004]*3,'jadeLight',8)

def rabbit():
    ell('Rabbit_body',(0,.055,.20),(.17,.24,.20),'furLight')
    ell('Rabbit_head',(0,-.16,.37),(.16,.14,.145),'furLight')
    ell('Rabbit_muzzle',(0,-.275,.325),(.09,.049,.052),'white')
    ell('Rabbit_nose',(0,-.317,.343),(.025,.012,.018),'pink')
    for side in (-1,1):
        ell('Rabbit_ear_'+str(side),(side*.075,-.13,.57),(.048,.032,.19),'furLight',rot=(0,side*.16,0))
        ell('Rabbit_ear_inner_'+str(side),(side*.083,-.157,.58),(.025,.009,.14),'pink',rot=(0,side*.16,0))
        ell('Rabbit_eye_'+str(side),(side*.104,-.257,.393),(.030,.016,.037),'black')
        ell('Rabbit_glint_'+str(side),(side*.10,-.271,.405),(.009,.004,.011),'white',segments=20)
        ell('Rabbit_haunch_'+str(side),(side*.14,.12,.145),(.095,.13,.14),'fur')
        ell('Rabbit_back_paw_'+str(side),(side*.13,.036,.046),(.078,.12,.046),'furLight')
        ell('Rabbit_front_paw_'+str(side),(side*.08,-.142,.040),(.046,.075,.040),'white')
    ell('Rabbit_tail',(0,.29,.20),(.073,.07,.073),'white')

def boar():
    ell('Boar_body',(0,.07,.34),(.24,.37,.25),'boar')
    ell('Boar_head',(0,-.29,.35),(.235,.235,.20),'boarLight')
    ell('Boar_muzzle',(0,-.493,.285),(.145,.09,.095),'brownLight')
    ell('Boar_nose_pad',(0,-.562,.292),(.116,.025,.070),'boar')
    for side in (-1,1):
        ell('Boar_nostril_'+str(side),(side*.046,-.584,.302),(.018,.008,.023),'black')
        ell('Boar_eye_'+str(side),(side*.165,-.443,.405),(.035,.019,.041),'black')
        ell('Boar_glint_'+str(side),(side*.16,-.46,.418),(.009,.004,.012),'white',segments=20)
        ell('Boar_ear_'+str(side),(side*.19,-.22,.53),(.091,.034,.103),'boar',rot=(.2,side*.60,0))
        ell('Boar_ear_inner_'+str(side),(side*.196,-.248,.539),(.052,.010,.067),'pink',rot=(.2,side*.60,0))
        for y in (-.17,.28):
            tube('Boar_leg_'+str(side)+str(y),[(side*.16,y,.30),(side*.16,y,.055)],[.072,.054],'boarLight')
            for dx in (-.026,.026):box('Cloven_hoof',(side*.16+dx,y-.012,.037),(.047,.10,.074),'sole',.014)
        tube('Boar_tusk_'+str(side),[(side*.12,-.473,.25),(side*.17,-.51,.28),(side*.181,-.50,.35)],[.026,.019,.002],'ivory')
    for j in range(7):
        y=-.08+j*.061
        tube('Bristle_'+str(j),[(0,y,.55),(.003,y+.012,.64)],[.035,.005],'hair',8)
    pts=[(.035*math.sin(i*.45),.40+i*.008,.32+.035*math.cos(i*.45)) for i in range(16)]
    tube('Curled_tail',pts,[.014]*len(pts),'boarLight',10)

def crystal(name,pos,height,radius,mat='crystal',sides=6):
    x,y,z=pos;verts=[]
    for h,r in [(0,.65),(height*.18,1),(height*.75,.90),(height,0)]:
        for i in range(sides):
            a=i*math.tau/sides;verts.append((x+radius*r*math.cos(a),y+radius*r*math.sin(a),z+h))
    faces=[]
    for j in range(3):
        for i in range(sides):faces.append((j*sides+i,j*sides+(i+1)%sides,(j+1)*sides+(i+1)%sides,(j+1)*sides+i))
    faces.append(tuple(reversed(range(sides))))
    return mesh(name,verts,faces,mat,False)

def stone():
    crystal('Spirit_stone',(0,0,0),.19,.065)
    tube('Jade_inclusion',[(-.04,-.042,.045),(0,-.057,.085),(.024,-.045,.122)],[.002]*3,'crystalLight',8)

def bottle():
    rings('Bottle_body',[(0,.045,.045),(.012,.058,.058),(.10,.062,.062),(.145,.037,.037),(.172,.025,.025),(.182,.027,.027)],'jade')
    rings('Ivory_neck',[(.168,.028,.028),(.181,.028,.028)],'ivory')
    rings('Cork',[(.18,.024,.024),(.202,.030,.030)],'brown')
    box('Paper_label',(0,-.063,.082),(.052,.004,.065),'paper',.003)
    ell('Label_seal',(0,-.067,.082),(.015,.003,.015),'jadeDark',segments=24)
    tube('Neck_string',[(-.025,-.018,.172),(-.015,-.029,.17),(.026,-.023,.17),(.033,-.02,.12)],[.003]*4,'brownLight',10)

def book():
    box('Book_pages',(0,0,.022),(.18,.25,.035),'paper',.004)
    for z in (.003,.043):box('Book_cover',(0,0,z),(.195,.265,.006),'jade',.002)
    box('Book_spine',(-.092,0,.023),(.012,.265,.04),'jadeDark',.003)
    box('Cover_title_plate',(.038,.02,.048),(.049,.15,.004),'ivory',.002)
    for y in (-.09,-.03,.03,.09):
        tube('Book_binding', [(-.075,y,.048),(-.102,y,.043),(-.103,y,.009),(-.077,y,.001)],[.0025]*4,'ivory',8)
    fontpath=Path('C:/Windows/Fonts/msjh.ttc')
    if fontpath.exists():
        font=bpy.data.fonts.load(str(fontpath))
        for i,char in enumerate('煉氣訣'):
            c=bpy.data.curves.new('Title_'+char,'FONT');c.body=char;c.font=font;c.size=.028;c.align_x='CENTER';c.align_y='CENTER';c.extrude=.0004
            o=bpy.data.objects.new('Title_'+char,c);bpy.context.collection.objects.link(o);o.location=(.038,.065-i*.044,.051)
            bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.ops.object.convert(target='MESH')
            finish(bpy.context.object,'Title_'+char,'jadeDark',False)

def aptitude():
    crystal('Main_assessment_crystal',(0,0,.10),.92,.20)
    for i in range(5):
        a=i*math.tau/5;crystal('Satellite_'+str(i),(.21*math.cos(a),.21*math.sin(a),.035),.23+i*.018,.06,'crystalLight')
    rings('Crystal_socket',[(0,.25,.25),(.035,.28,.28),(.09,.23,.23)],'stoneDark',n=8)
    rings('Socket_trim',[(.03,.285,.285),(.053,.285,.285)],'gold',n=8)

def entrance():
    for side in (-1,1):
        for j in range(5):box('Arch_jamb_'+str(side)+str(j),(side*1.13,0,.23+j*.43),(.36,.65,.42),'stone' if j%2 else 'stoneLight',.07)
        box('Jamb_foot_'+str(side),(side*1.13,0,.13),(.55,.81,.26),'stoneDark',.04)
    for j in range(9):
        a=j*math.pi/8;box('Arch_voussoir_'+str(j),(1.13*math.cos(a),0,1.94+1.13*math.sin(a)),(.40,.68,.44),'stone' if j%2 else 'stoneLight',.055,rot=(0,-a,0))
    box('Threshold',(0,-.03,.055),(2.05,.74,.11),'stoneLight',.025)
    for side in (-1,1):
        box('Jade_inlay_'+str(side),(side*1.13,-.34,1.12),(.12,.016,.38),'jade',.025)

def floor():
    for x in range(4):
        for y in range(4):box('Floor_tile_%d_%d'%(x,y),((x-1.5)*.99,(y-1.5)*.99,.10),(.975,.975,.20),'stone' if (x+y)%3 else 'stoneLight',.018)

def wall():
    box('Wall_core',(0,.04,1.45),(4,.36,2.9),'stoneDark',.04)
    for row in range(6):
        for col in range(4):box('Wall_stone_%d_%d'%(row,col),((col-1.5)*.99,-.16,.24+row*.475),(.975,.15,.455),'stone' if (row+col)%3 else 'stoneLight',.035)
    box('Wall_plinth',(0,-.025,.14),(4.05,.5,.28),'stoneDark',.025)
    box('Wall_top',(0,.0,2.96),(4.05,.47,.14),'stoneLight',.025)

def door():
    # Two independently editable leaves. Hinge attachment coordinates in model_info.
    for side in (-1,1):
        for j in range(4):
            x=side*(.12+j*.225)
            box('Door_plank_'+str(side)+str(j),(x,0,1.05),(.216,.105,2.10),'brown' if j%2 else 'brownLight',.012)
        for z in (.22,1.80):box('Door_brace_'+str(side)+str(z),(side*.45,-.067,z),(.86,.058,.10),'jadeDark',.012)
        box('Door_edge_'+str(side),(side*.895,-.01,1.05),(.045,.13,2.1),'brown',.008)
        for z in (.28,1.77):
            tube('Hinge_'+str(side)+str(z),[(side*.93,0,z-.09),(side*.93,0,z+.09)],[.032,.032],'gold',12)
        ell('Handle_plate_'+str(side),(side*.13,-.079,1.0),(.062,.018,.081),'gold')
        pts=[(side*.13+.042*math.cos(i*math.tau/24),-.105,.948+.047*math.sin(i*math.tau/24)) for i in range(25)]
        tube('Handle_ring_'+str(side),pts,[.007]*len(pts),'gold',8)

BUILD={'QMaleBase':lambda:base(False),'QFemaleBase':lambda:base(True),
       'QTopknotHair':lambda:hair(False),'QDoubleBunHair':lambda:hair(True),
       'QMaleNoviceOutfit':lambda:outfit(False),'QFemaleNoviceOutfit':lambda:outfit(True),
       'QMountainRabbit':rabbit,'QMountainBoar':boar,'QSpiritStone':stone,'QPillBottle':bottle,
       'QQiManual':book,'QAptitudeCrystal':aptitude,'QCaveEntrance':entrance,'QCaveFloor':floor,'QCaveWall':wall,'QCaveDoor':door}

def bounds(obs):
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();pts=[]
    for o in obs:
        e=o.evaluated_get(dg);pts.extend(e.matrix_world@v.co for v in e.data.vertices)
    return Vector([min(p[i] for p in pts) for i in range(3)]),Vector([max(p[i] for p in pts) for i in range(3)])

def studio(obs):
    s=bpy.context.scene;lo,hi=bounds(obs);center=(lo+hi)/2;extent=hi-lo
    c=bpy.data.cameras.new('Reference_camera');cam=bpy.data.objects.new('Reference_camera',c);s.collection.objects.link(cam);s.camera=cam
    c.type='ORTHO';c.ortho_scale=extent.length*1.16;c.clip_start=.001;c.clip_end=1000
    s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=1024;s.render.resolution_y=1024;s.render.resolution_percentage=100
    s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA'
    sh=s.display.shading;sh.light='STUDIO';sh.studiolight_rotate_z=.35;sh.color_type='MATERIAL'
    sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH';sh.curvature_ridge_factor=1.15;sh.curvature_valley_factor=.75
    sh.show_specular_highlight=True;sh.background_type='WORLD';s.world=bpy.data.worlds.new('Warm_neutral');s.world.color=(.19,.205,.20)
    s.display.render_aa='32';s.view_settings.view_transform='Standard'
    return cam,center,c.ortho_scale

def position(cam,center,scale,dr):
    cam.location=center+Vector(dr).normalized()*scale*2.5
    cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()

def save_asset(aid):
    out=BATCH/'Models'/aid/'v001';ref=BATCH/'ArtLibrary/Turnarounds'/f'{aid}_v001'
    if (out/'model_info.json').exists() or (out/(aid+'_v001.blend')).exists():
        raise RuntimeError('Refusing overwrite: '+str(out))
    out.mkdir(parents=True,exist_ok=True);ref.mkdir(parents=True,exist_ok=True)
    reset();BUILD[aid]();lo,hi=bounds(objects);offset=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
    for o in objects:o.location-=offset
    root=bpy.data.objects.new(aid+'_ROOT',None);bpy.context.collection.objects.link(root)
    root['stage']='Q-style editable blockout; NOT rigged or game-ready'
    root['assembly_offset_m']=list(offset)
    for o in objects:o.parent=root
    lo,hi=bounds(objects);cam,center,scale=studio(objects);position(cam,center,scale,(1,-1,.45))
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects+[root]:o.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.export_scene.fbx(filepath=str(out/(aid+'_v001.fbx')),use_selection=True,object_types={'MESH','EMPTY'},add_leaf_bones=False,axis_forward='-Z',axis_up='Y',apply_unit_scale=True,bake_anim=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/(aid+'_v001.blend')))
    info={'asset':aid,'plan_id':ASSETS[aid][0],'name_zh':ASSETS[aid][1],
          'stage':'editable_blockout','units':'meters','front':'-Y','pivot':'bottom_center',
          'assembly_offset_m':list(offset),'dimensions_m':list(hi-lo),'bounds_m':[list(lo),list(hi)],
          'mesh_objects':len(objects),'triangles':sum(len(p.vertices)-2 for o in objects for p in o.data.polygons),
          'modeling_method':'procedural editable geometry guided by approved Q-style concept; not image generation',
          'render_engine':'Blender Workbench studio','uv_baked':False,'rigged':False,'animation_ready':False,
          'collision_ready':False,'lod_ready':False,'unreal_import_verified':False,
          'limits':'Separate overlapping construction meshes; retopology, unified skin, UV and rigging remain.'}
    if aid=='QCaveDoor':info['hinge_axes_before_centering']=[[-.93,0,0],[.93,0,0]]
    records=[]
    for name,dr in VIEWS:
        position(cam,center,scale,dr)
        dg=bpy.context.evaluated_depsgraph_get()
        pts=[world_to_camera_view(bpy.context.scene,cam,e.matrix_world@Vector(v)) for o in objects for e in [o.evaluated_get(dg)] for v in e.bound_box]
        assert all(.008<p.x<.992 and .008<p.y<.992 and p.z>0 for p in pts),(aid,name,'cropped')
        bpy.context.scene.render.filepath=str(ref/(name+'.png'));bpy.ops.render.render(write_still=True)
        records.append({'file':name+'.png','direction':dr,'camera_location':list(cam.location),'framing_pass':True})
        print('VIEW_COMPLETE',aid,name,flush=True)
    (ref/'views.json').write_text(json.dumps({'asset':aid,'same_geometry':True,'projection':'orthographic','resolution':[1024,1024],'source':str((out/(aid+'_v001.blend')).relative_to(BATCH)), 'views':records},ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'model_info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    print('ASSET_COMPLETE',aid,flush=True)

def preview():
    out=BATCH/'Previews';out.mkdir(parents=True,exist_ok=True)
    for female in (False,True):
        aid='QFemaleAssembled' if female else 'QMaleAssembled';reset();base(female);hair(female);outfit(female)
        cam,center,scale=studio(objects)
        for suffix,dr in [('front',(0,-1,.07)),('threequarter',(1,-2,.35)),('rear',(0,1,.05))]:
            position(cam,center,scale,dr);bpy.context.scene.render.filepath=str(out/(aid+'_'+suffix+'.png'));bpy.ops.render.render(write_still=True)
        position(cam,center,scale,(1,-2,.35));bpy.ops.wm.save_as_mainfile(filepath=str(out/(aid+'_v001.blend')))
        print('PREVIEW_COMPLETE',aid,flush=True)

if __name__=='__main__':
    paused={'QMaleBase','QFemaleBase','QTopknotHair','QDoubleBunHair','QMaleNoviceOutfit','QFemaleNoviceOutfit'}
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [a for a in ASSETS if a not in paused]
    if 'preview' in args or set(args)&paused:
        raise RuntimeError('Character, hair and clothing work paused by user on 2026-10-24. Existing files are reference only.')
    for aid in args:save_asset(aid)
