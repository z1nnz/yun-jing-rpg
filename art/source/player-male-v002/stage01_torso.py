"""Torso-first construction study. Run in a new headless Blender process.

This stage has no head, hands, legs, rig or final game export. Measurements are
working dimensions inferred from the approved reference, not measured anatomy.
"""
import bpy
import bmesh
import math
import json
import hashlib
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
OUT = PROJECT / 'art/previews/player-male-v002/stage01'
REF = PROJECT / 'art/references/player-character-redesign-review'
OUT.mkdir(parents=True, exist_ok=True)
for name in ['male-three-view.png', 'male-five-view-provisional.png',
             'male-a-pose-provisional.png', 'male-garment-provisional.png']:
    assert (REF / name).is_file(), name

# This is a separate CLI process; never run the cleanup in the user's live scene.
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
scene.render.engine = 'CYCLES'
scene.cycles.samples = 40
scene.cycles.use_denoising = True
scene.render.resolution_x = 1000
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = 'AgX'
scene.render.image_settings.file_format = 'PNG'
scene.world.use_nodes = True
scene.world.node_tree.nodes.get('Background').inputs[0].default_value = (0.16, 0.18, 0.20, 1)
scene.world.node_tree.nodes.get('Background').inputs[1].default_value = 0.3
scene.render.film_transparent = False
scene['stage'] = '01 torso; approved reference 2026-10-26; not game ready'

def collection(name):
    col = bpy.data.collections.new(name)
    scene.collection.children.link(col)
    return col

BODY = collection('01_Anatomy_Torso')
CLOTH = collection('02_Upper_Garment_Study')
STUDIO = collection('90_Review_Studio')
REFERENCES = collection('99_Approved_References')

def linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def material(name, rgb, cloth=False):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    nt = m.node_tree
    bs = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    bs.inputs['Base Color'].default_value = (*[linear(c) for c in rgb], 1)
    bs.inputs['Roughness'].default_value = .72 if cloth else .62
    if cloth:
        bs.inputs['Sheen Weight'].default_value = .18
        tc = nt.nodes.new('ShaderNodeTexCoord')
        noise = nt.nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 550
        noise.inputs['Detail'].default_value = 2
        nt.links.new(tc.outputs['Generated'], noise.inputs['Vector'])
        bump = nt.nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .15
        bump.inputs['Distance'].default_value = .00025
        nt.links.new(noise.outputs['Fac'], bump.inputs['Height'])
        nt.links.new(bump.outputs['Normal'], bs.inputs['Normal'])
    return m

skin = material('M_TorsoClay', (.57, .55, .51))
teal = material('M_JadeLinen_Study', (.48, .64, .61), True)
ivory = material('M_IvoryBinding_Study', (.88, .85, .79), True)
charcoal = material('M_InnerCharcoal_Study', (.29, .32, .31), True)
tan = material('M_TanSash_Study', (.54, .38, .25), True)
seam_mat = material('M_TealSeams', (.40, .53, .50), True)
clay = material('M_TopologyClay', (.68, .72, .72))

def make_mesh(name, verts, faces, uv, mat, col, subdiv=0, thickness=0):
    me = bpy.data.meshes.new(name + '_ControlCage')
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    ob.data.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    if uv:
        layer = me.uv_layers.new(name='ConstructionUV')
        for poly, coords in zip(me.polygons, uv):
            for li, co in zip(poly.loop_indices, coords):
                layer.data[li].uv = co
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    if subdiv:
        mod = ob.modifiers.new('EditableSurface', 'SUBSURF')
        mod.levels = subdiv
        mod.render_levels = subdiv
    if thickness:
        mod = ob.modifiers.new('FabricThickness', 'SOLIDIFY')
        mod.thickness = thickness
        mod.offset = -1
        mod.use_even_offset = True
    return ob

# Shape-preserving interpolation avoids cylinder-like transitions between anatomy
# stations. Width, front depth and back depth are authored separately.
STATIONS = [
    (.900, .159, .094, .106), (.955, .170, .100, .113),
    (1.020, .162, .097, .108), (1.080, .148, .087, .096),
    (1.150, .155, .094, .100), (1.220, .172, .108, .103),
    (1.300, .188, .120, .108), (1.360, .202, .111, .103),
    (1.405, .220, .084, .092), (1.435, .211, .066, .074),
    (1.460, .147, .059, .066), (1.485, .069, .050, .053),
    (1.525, .056, .048, .050), (1.550, .054, .046, .048),
]

def interpolate(z, column):
    for i in range(len(STATIONS)-1):
        a,b=STATIONS[i],STATIONS[i+1]
        if z <= b[0]:
            t=max(0,min(1,(z-a[0])/(b[0]-a[0])))
            t=t*t*(3-2*t)
            return a[column]*(1-t)+b[column]*t
    return STATIONS[-1][column]

def gauss(x, center, width):
    return math.exp(-((x-center)/width)**2)

def anatomy_point(theta,z):
    st,ct=math.sin(theta), math.cos(theta)
    width=interpolate(z,1)
    x=width*st
    depth=interpolate(z,2 if ct>=0 else 3)
    y=-ct*depth
    # Broad pectoral mass, sternum, upper abdomen and scapular plane.
    if ct>0:
        pec=.009*gauss(abs(x),.091,.055)*gauss(z,1.315,.047)
        sternum=-.004*gauss(x,0,.023)*gauss(z,1.32,.085)
        abdomen=.0035*gauss(x,0,.080)*gauss(z,1.115,.10)
        clavicle=.003*gauss(z,1.410-.15*abs(x),.009)
        y-=ct*(pec+sternum+abdomen+clavicle)
    else:
        scap=.006*gauss(abs(x),.09,.045)*gauss(z,1.35,.065)
        groove=-.004*gauss(x,0,.018)*gauss(z,1.28,.16)
        y+=(-ct)*(scap+groove)
    return x,y,z

def rings_surface(name, point_fn, rows, cols, mat, col, omit=None, subdiv=1, thickness=0):
    verts=[point_fn(i/cols*math.tau,j/rows) for j in range(rows+1) for i in range(cols)]
    faces=[];uv=[]
    for j in range(rows):
        for i in range(cols):
            if omit and omit(i/cols*math.tau,(j+.5)/rows):
                continue
            faces.append((j*cols+i,j*cols+(i+1)%cols,(j+1)*cols+(i+1)%cols,(j+1)*cols+i))
            uv.append(((i/cols,j/rows),((i+1)/cols,j/rows),((i+1)/cols,(j+1)/rows),(i/cols,(j+1)/rows)))
    used=sorted({v for face in faces for v in face})
    mapping={v:i for i,v in enumerate(used)}
    return make_mesh(name,[verts[v] for v in used],
                     [tuple(mapping[v] for v in f) for f in faces],uv,mat,col,subdiv,thickness)

torso=rings_surface('Torso_ContinuousCage',lambda t,v: anatomy_point(t,.90+.65*v),
                    52,64,skin,BODY,
                    subdiv=2)
torso['open_boundaries']='Neck and pelvis; shoulder patches remain closed until arm attachment.'
torso['dimensions_are']='Working proportions inferred from the approved clothed image.'

# Preserve the anatomy checkpoint before any garment is created.
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Male_Stage01_Anatomy.blend'))

# Clothing dimensions follow the same chest/waist stations, with visible drape
# clearance rather than intersections between geometric primitives.
def cloth_shape(z):
    zs=[(.98,.164,.110), (1.06,.162,.109),(1.11,.178,.124),
        (1.22,.194,.134),(1.32,.210,.143),(1.40,.231,.125),
        (1.46,.190,.100),(1.50,.073,.067),(1.53,.060,.056)]
    for a,b in zip(zs,zs[1:]):
        if z<=b[0]:
            t=max(0,min(1,(z-a[0])/(b[0]-a[0])))
            return a[1]*(1-t)+b[1]*t,a[2]*(1-t)+b[2]*t
    return zs[-1][1:]

def cloth_top(theta):
    a=abs((theta+math.pi)%math.tau-math.pi)
    if a<.32:
        return 1.305+.195*(a/.32)
    if a<1.3:
        return 1.50-.055*((a-.32)/.98)
    return 1.445+.053*((a-1.3)/(math.pi-1.3))

def fabric_point(theta,v):
    z=.98+v*(cloth_top(theta)-.98)
    rx,depth=cloth_shape(z)
    # Folds converge into the cinched waist; broader and quieter at the chest.
    gather=.004*gauss(z,1.125,.035)*math.sin(12*theta+9*z)
    drape=.0024*math.sin(9*theta+2.1*z)*gauss(z,1.26,.14)
    shoulder=.002*math.sin(15*theta-8*z)*gauss(z,1.39,.06)
    angle=(theta+math.pi)%math.tau-math.pi
    tension=0
    for sign in (-1,1):
        for shift,amp in [(0,.004),(.22,.0024)]:
            center=sign*(.30+2.5*(z-1.1)+shift)
            tension+=amp*gauss(angle,center,.065)*gauss(z,1.22,.10)
    fold=(gather+drape+shoulder+tension)*min(1,max(0,(z-1.08)/.04))
    x=(rx+fold)*math.sin(theta)
    y=-(depth+fold)*math.cos(theta)
    return x,y,z

def shell_with_shoulder(theta,v):
    if v<=.82:return fabric_point(theta,v/.82)
    outer=Vector(fabric_point(theta,1))
    angle=abs((theta+math.pi)%math.tau-math.pi)
    topz=1.275+.210*min(1,angle/1.0)
    neck=Vector((.077*math.sin(theta),-.073*math.cos(theta),topz))
    if angle<1.0:
        neck.y=outer.y
    t=(v-.82)/.18
    return outer.lerp(neck,t)

jacket=rings_surface('OuterRobe_UpperShell',shell_with_shoulder,64,96,teal,CLOTH,
                      subdiv=2,thickness=.0022)
jacket['construction']='Continuous quad cloth shell and shoulder yoke; sleeve attachment topology deferred.'

def front_y(x,z):
    rx,depth=cloth_shape(z)
    return -depth*math.sqrt(max(.06,1-(x/rx)**2))

def sample_path(points,t):
    i=min(len(points)-2,int(t*(len(points)-1)))
    a=(t*(len(points)-1))-i
    p0=Vector(points[max(0,i-1)]);p1=Vector(points[i])
    p2=Vector(points[i+1]);p3=Vector(points[min(len(points)-1,i+2)])
    return .5*((2*p1)+(-p0+p2)*a+(2*p0-5*p1+4*p2-p3)*a*a+(-p0+3*p1-3*p2+p3)*a*a*a)

def ribbon(name,path,width,mat,offset=.005,segments=80):
    # Broad cloth strips lie tangent to the torso, never circular tubes.
    verts=[];faces=[];uv=[];across=8
    for i in range(segments+1):
        t=i/segments
        p=sample_path(path,t)
        d=sample_path(path,min(1,t+.001))-sample_path(path,max(0,t-.001))
        d.normalize()
        side=Vector((d.z,0,-d.x)).normalized()
        for j in range(across+1):
            u=j/across
            q=p+side*(u-.5)*width
            q.y=front_y(q.x,q.z)-offset-.0008*math.sin(math.pi*u)
            verts.append(q)
    for i in range(segments):
        for j in range(across):
            a=i*(across+1)+j
            faces.append((a,a+1,a+across+2,a+across+1))
            uv.append(((j/across,i/segments),((j+1)/across,i/segments),
                       ((j+1)/across,(i+1)/segments),(j/across,(i+1)/segments)))
    return make_mesh(name,verts,faces,uv,mat,CLOTH,1,.002)

def continuous_collar(name, width, neck_width, neck_depth, neck_z, end_z, mat, outer=False):
    under_x=.012
    points=[(under_x,-.137,end_z),(-.028,-.143,min(neck_z-.055,end_z+.07)),
            (-neck_width,-.090,neck_z-.025),(-neck_width,-.035,neck_z)]
    for i in range(1,17):
        a=math.pi-math.pi*i/16
        points.append((neck_width*math.cos(a),neck_depth*math.sin(a),neck_z))
    points += [(neck_width,-.035,neck_z),(neck_width,-.090,neck_z-.025),
               (.035,-.151,min(neck_z-.055,end_z+.09)),(.014,-.146,end_z-.015)]
    if outer:
        points[-2:]=[(.049,-.148,1.365),(.012,-.152,1.268),
                     (-.045,-.137,1.155),(-.080,-.095,1.035)]
    verts=[];faces=[];uv=[]
    n=160;across=8
    for i in range(n+1):
        t=i/n;p=sample_path(points,t)
        tangent=(sample_path(points,min(1,t+.0001))-sample_path(points,max(0,t-.0001))).normalized()
        normal=Vector((p.x/(neck_width*neck_width),p.y/(neck_depth*neck_depth),0)).normalized()
        # On the broad chest the strip lies flat; around the neck it turns upward.
        if p.y<-.035:
            blend=min(1,max(0,(-p.y-.035)/.065))
            normal=normal.lerp(Vector((0,-1,0)),blend).normalized()
        side=tangent.cross(normal).normalized()
        if side.z<0: side=-side
        for j in range(across+1):
            u=j/across;q=p+side*(u-.5)*width
            q+=normal*(.001*math.sin(math.pi*u))
            if p.y < -.065:
                clearance=.009 if outer else (.005 if mat==charcoal else .0025)
                if outer:clearance*=max(.1,min(1,(q.z-1.075)/.05))
                target_y=front_y(q.x,q.z)-clearance-(.003 if t>.5 and q.z>1.10 else 0)
                blend=min(1,max(0,(-p.y-.065)/.035))
                q.y=q.y*(1-blend)+target_y*blend
            verts.append(q)
    for i in range(n):
        for j in range(across):
            a=i*(across+1)+j
            faces.append((a,a+1,a+across+2,a+across+1))
            uv.append(((j/across,i/n),((j+1)/across,i/n),((j+1)/across,(i+1)/n),(j/across,(i+1)/n)))
    return make_mesh(name,verts,faces,uv,mat,CLOTH,1,.002)

continuous_collar('Undershirt_ContinuousCollar',.020,.052,.058,1.515,1.38,ivory)
continuous_collar('InnerRobe_ContinuousCollar',.034,.067,.068,1.505,1.29,charcoal)
continuous_collar('OuterRobe_ContinuousBinding',.043,.078,.079,1.488,1.245,ivory,True)

# Inner garment chest panel closes the space below the white V neckline.
verts=[];faces=[];uv=[]
for j in range(33):
    v=j/32
    for i in range(25):
        u=i/24;x=(u-.5)*(.006+.109*v)
        top=1.357+.072*abs(2*u-1)
        z=1.295+(top-1.295)*v
        verts.append((x,front_y(x,z)-.003,z))
for j in range(32):
    for i in range(24):
        a=j*25+i
        faces.append((a,a+1,a+26,a+25))
        uv.append(((i/24,j/32),((i+1)/24,j/32),((i+1)/24,(j+1)/32),(i/24,(j+1)/32)))
make_mesh('InnerRobe_ChestPanel',verts,faces,uv,charcoal,CLOTH,1,.001)

# Cloth waist wrap, not a round rope. Folds have shallow broad ridges.
def sash_point(theta,v):
    z=1.026+.064*v
    fold=.0016*math.sin(v*math.pi*3+theta*.8)+.0006*math.sin(v*math.pi*7-theta)
    rx,depth=cloth_shape(z)
    clearance=.0018+.0007*math.sin(v*math.pi*3+theta*.8)
    return ((rx+clearance)*math.sin(theta),-(depth+clearance)*math.cos(theta),z)
sash=rings_surface('WaistSash_WovenBand',sash_point,16,128,tan,CLOTH,subdiv=1,thickness=.0015)
sash['pending']='Knot and hanging tails belong to the later accessory stage.'

# Back centre seam: a narrow flat inset strip, editable separately.
verts=[];faces=[];uv=[]
for i in range(81):
    z=1.095+(1.485-1.095)*i/80
    depth=cloth_shape(z)[1]
    for x in (-.0008,.0008):
        verts.append((x,depth+.001,z))
for i in range(80):
    a=2*i;faces.append((a,a+1,a+3,a+2));uv.append(((0,i/80),(1,i/80),(1,(i+1)/80),(0,(i+1)/80)))
make_mesh('BackCentreSeam',verts,faces,uv,seam_mat,CLOTH,0,.0005)

# Embed approved references as editable image empties, disabled in renders.
for i,name in enumerate(['male-three-view.png','male-five-view-provisional.png','male-garment-provisional.png']):
    img=bpy.data.images.load(str(REF/name),check_existing=True)
    img.pack()
    ob=bpy.data.objects.new('REF_'+name[:-4],None)
    REFERENCES.objects.link(ob)
    ob.empty_display_type='IMAGE';ob.data=img
    ob.empty_display_size=1.8
    ob.location=(2+i*2,0,1)
    ob.rotation_euler=(math.pi/2,0,0)
    ob.hide_render=True
REFERENCES.hide_viewport=True

# Review lighting and cameras. No full-body placeholder is made.
def area(name,loc,energy,size):
    d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);STUDIO.objects.link(o);o.location=loc
    o.rotation_euler=(Vector((0,0,1.25))-o.location).to_track_quat('-Z','Y').to_euler()
area('Key',(-1.4,-2.2,2.6),120,2)
area('Fill',(1.5,-.8,1.6),55,2)
area('Rim',(.7,1.1,2.0),95,1.6)

cams={}
for name,loc in [('front',(0,-3,1.24)),('side',(3,0,1.24)),
                 ('rear',(0,3,1.24)),('three-quarter',(2.3,-3,1.50))]:
    d=bpy.data.cameras.new(name);o=bpy.data.objects.new('Camera_'+name,d)
    STUDIO.objects.link(o);o.location=loc
    o.rotation_euler=(Vector((0,0,1.235))-o.location).to_track_quat('-Z','Y').to_euler()
    d.type='ORTHO';d.ortho_scale=.83;cams[name]=o

def render(name,cam):
    scene.camera=cam
    scene.render.filepath=str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True)

scene.camera=cams['three-quarter']
scene['next_stage']='Torso review before limbs, lower robe, hair, face, rig and export.'
scene['reference_approval']='User approved five-view and detail sheets on 2026-10-26.'
bpy.context.view_layer.update()
for ob in bpy.context.selected_objects: ob.select_set(False)
jacket.select_set(True);bpy.context.view_layer.objects.active=jacket
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Male_Stage01_TorsoAndCollar.blend'))

for name,cam in cams.items():
    render('torso-'+name,cam)
CLOTH.hide_render=True
render('anatomy-front',cams['front'])
render('anatomy-side',cams['side'])
render('anatomy-rear',cams['rear'])
CLOTH.hide_render=False

# Wire overlay depicts the control cage, not a dense final triangulated export.
wiremat=material('M_Wire',(.08,.12,.13))
wire_objs=[]
for original in [torso,jacket]:
    ob=original.copy();ob.data=original.data.copy();STUDIO.objects.link(ob)
    ob.name='WIRE_'+original.name
    ob.modifiers.clear()
    ob.data.materials.clear();ob.data.materials.append(wiremat)
    mod=ob.modifiers.new('ControlCageWire','WIREFRAME');mod.thickness=.0005
    mod.use_replace=True
    wire_objs.append(ob)
render('torso-wire',cams['three-quarter'])
for ob in wire_objs:bpy.data.objects.remove(ob,do_unlink=True)

report={
    'stage':'01 torso, not final character',
    'blender':bpy.app.version_string,
    'working_scale':{'reference_total_height_m':1.78,'shoulder_width_m':.462,
                     'waist_band_width_m':.34,'shoulder_z_m':1.425,'waist_z_m':1.058},
    'references':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in REF.glob('male-*.png')},
    'objects':[],
    'unfinished':['sleeves','limbs','lower robe','hair','face','rig','textures','animation','Unity'],
}
for ob in list(BODY.objects)+list(CLOTH.objects):
    report['objects'].append({'name':ob.name,'vertices':len(ob.data.vertices),
        'control_tris':sum(len(p.vertices)-2 for p in ob.data.polygons),
        'dimensions_m':list(ob.dimensions),'modifiers':[m.type for m in ob.modifiers]})
(OUT/'build-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('@@DONE@@',str(ROOT/'Male_Stage01_TorsoAndCollar.blend'))
