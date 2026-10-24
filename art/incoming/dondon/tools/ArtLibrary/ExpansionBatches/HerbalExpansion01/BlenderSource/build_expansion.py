"""Build six editable Qingxi village prototypes and render ten views per asset.
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

def tray(p,s=(.62,.40)):
    x,y,z=p; w,d=s
    box('Removable_Tray_Base',(x,y,z),(w,d,.035),board)
    for xx in (-w/2,w/2):box('Tray_Side',(x+xx,y,z+.055),(.025,d,.11),wood,.004)
    for yy in (-d/2,d/2):box('Tray_End',(x,y+yy,z+.055),(w,.025,.11),wood,.004)

def jar(p,r=.12,h=.27):
    lathe('Glazed_Medicine_Jar',[(0,0),(r*.7,0),(r,.06),(r,h*.65),(r*.6,h*.90),(r*.6,h),(r*.46,h),(r*.46,h*.8),(r*.8,h*.6),(r*.7,.04),(0,.04)],p,jade)
    cyl('Jar_Wood_Lid',(p[0],p[1],p[2]+h+.018),r*.64,.036,board)

def stall():
    for x in (-1.3,1.3):
        for y in (-.65,.65):
            h=2.18 if y<0 else 2.60
            box('Timber_Post',(x,y,h/2),(.15,.15,h),wood,.025)
            box('Stone_Foot',(x,y,.11),(.24,.24,.22),stone,.025)
            beam('Diagonal_Brace',(x,y,1.72),(x*.69,y,2.12 if y<0 else 2.49),.048,wood)
    for y,z in ((-.65,2.12),(.65,2.54)):box('Canopy_Crossbeam',(0,y,z),(2.95,.14,.14),wood,.025)
    for x in (-1.3,1.3):beam('Roof_Side_Beam',(x,-.76,2.16),(x,.8,2.60),.065,wood)
    # Continuous fabric with gentle sag between front and rear crossbeams.
    nx,ny=24,20; v=[]
    for j in range(ny+1):
        t=j/ny
        for i in range(nx+1):
            x=-1.48+2.96*i/nx
            z=2.19+.44*t-.16*math.sin(math.pi*t)-.035*math.cos(x/1.48*math.pi/2)
            v.append((x,-.86+1.72*t,z))
    f=[(j*(nx+1)+i,j*(nx+1)+i+1,(j+1)*(nx+1)+i+1,(j+1)*(nx+1)+i) for j in range(ny) for i in range(nx)]
    o=mesh('Removable_Sage_Canopy',v,f,cloth);o.modifiers.new('Fabric_thickness','SOLIDIFY').thickness=.012
    for k in range(10):
        x=-1.48+k*.296
        vs=[(x+i*.296/12,-.865,2.19-.035*math.cos((x+i*.296/12)/1.48*math.pi/2)) for i in range(13)]
        vs += [(x+i*.296/12,-.867,2.04-.10*math.sin(i*math.pi/12)) for i in range(13)]
        mesh('Scalloped_Canopy_Hem',vs,[(i,i+1,14+i,13+i) for i in range(12)],cloth)
    for i in range(14):box('Counter_Front_Plank',(-1.2+i*.185,-.57,.53),(.177,.065,.87),board,.006)
    for y in (-.54,.54):
        box('Counter_Lower_Rail',(0,y,.13),(2.58,.1,.14),wood)
        box('Counter_Upper_Rail',(0,y,.94),(2.58,.10,.13),wood)
    for x in (-1.24,1.24):box('Counter_Side',(x,0,.52),(.06,1.05,.82),board)
    for i in range(6):box('Counter_Top_Plank',(0,-.50+i*.20,1.03),(2.72,.19,.095),board,.008)
    for z in (1.45,1.94):box('Rear_Shelf',(0,.52,z),(2.45,.38,.055),wood)
    for x in (-.84,0,.84):
        tray((x,-.22,1.10))
        for k in range(5):
            leaf('Dried_Tray_Leaf',(x-.23+k*.10,-.30,1.13),(x-.16+k*.10,-.13,1.15),.035,green)
    for x in (-.90,-.55,.65,.98):jar((x,.51,1.48),.105,.25)
    for x in (-.65,0,.65):jar((x,.51,1.97),.11,.27)
    box('Sign_Bracket',(1.49,-.65,1.97),(.48,.07,.07),wood)
    beam('Sign_Rope',(1.69,-.65,1.97),(1.69,-.65,1.78),.015,rope)
    o=cyl('Round_Herbalist_Sign',(1.69,-.65,1.54),.24,.055,board);o.rotation_euler[0]=math.pi/2
    torus('Sign_Rim',(1.69,-.69,1.54),.225,.018,wood,(math.pi/2,0,0))
    beam('Sign_Leaf_Stem',(1.69,-.69,1.39),(1.69,-.69,1.65),.009,green)
    # Raised leaves face the front of the sign.
    for sign in (-1,1):
        o=mesh('Sign_Leaf_Emblem',[(0,0,0),(sign*.075,0,.045),(sign*.13,0,.17),(sign*.025,0,.12),(sign*.065,-.008,.085)],[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],green)
        o.modifiers.new('Emblem_thickness','SOLIDIFY').thickness=.003
        o.location=(1.69,-.70,1.49)

def rack():
    for x in (-.54,.54):
        for y in (-.28,.28):box('Rack_Post',(x,y,.84),(.065,.065,1.68),wood)
        box('Rack_Foot',(x,0,.055),(.13,.84,.11),wood)
    for z in (.34,.77,1.20):
        tray((0,0,z),(1.08,.64))
        for i in range(16):box('Bamboo_Tray_Slat',(-.49+i*.065,0,z+.022),(.027,.58,.02),rope,.003)
        for k in range(5):
            for q in range(2):leaf('Drying_Leaf',(-.43+k*.19,-.20+q*.24,z+.06),(-.32+k*.19,-.05+q*.24,z+.075),.04,green if k%2 else gold)
    beam('Hanging_Rail',(-.64,0,1.65),(.64,0,1.65),.032,wood)
    for x in (-.37,0,.37):
        beam('Bundle_Tie',(x,0,1.65),(x,0,1.50),.014,rope)
        for k in range(5):
            ang=k*math.tau/5; end=(x+.1*math.cos(ang),.1*math.sin(ang),1.29)
            beam('Dried_Stem',(x,0,1.53),end,.006,rope)
            leaf('Hanging_Herb',(x,0,1.48),end,.04,green)
    beam('Rear_Brace',(-.53,.30,.20),(.53,.30,1.54),.025,wood)

def mortar():
    lathe('Hollow_Stone_Mortar',[(0,0),(.16,0),(.20,.035),(.245,.15),(.25,.25),(.24,.29),(.205,.29),(.19,.25),(.165,.12),(.10,.065),(0,.065)],(0,0,0),stone)
    torus('Mortar_Rim',(0,0,.275),.226,.018,jade)
    beam('Removable_Wood_Pestle',(.045,.02,.12),(.21,.10,.49),.042,wood)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=.065,location=(.045,.02,.12));finish(bpy.context.object,'Pestle_Grinding_Head',stone)
    for i in range(5):leaf('Crushed_Herb',(-.09+i*.034,-.055,.082),(-.065+i*.034,.03,.09),.015,green)

def planter():
    lathe('Hollow_Glazed_Pot',[(0,0),(.14,0),(.20,.03),(.24,.18),(.21,.33),(.225,.35),(.225,.39),(.185,.39),(.18,.34),(.19,.18),(.16,.05),(0,.05)],(0,0,0),jade)
    cyl('Pot_Soil',(0,0,.32),.18,.04,soil)
    torus('Glazed_Pot_Rim',(0,0,.375),.205,.018,gold)
    herb((0,0,.33),1.45)
    for j in range(3):
        a=j*math.tau/3; p=(.08*math.cos(a),.08*math.sin(a),.91+j*.035)
        beam('Flower_Stem',(0,0,.38),p,.008,green)
        for k in range(5):
            t=k*math.tau/5
            leaf('Spirit_Flower_Petal',p,(p[0]+.075*math.cos(t),p[1]+.075*math.sin(t),p[2]+.02),.035,petal)
        cyl('Flower_Core',p,.019,.025,gold)

def furnace():
    for j in range(3):
        a=j*math.tau/3+math.pi/6
        p=(.34*math.cos(a),.34*math.sin(a),.04); q=(.28*math.cos(a),.28*math.sin(a),.38)
        beam('Bronze_Tripod_Leg',p,q,.058,bronze)
        box('Furnace_Foot',(p[0],p[1],.04),(.17,.15,.08),bronze,.025)
    lathe('Hollow_Furnace_Body',[(0,.28),(.20,.28),(.37,.38),(.43,.60),(.40,.79),(.30,.90),(.30,.95),(.25,.95),(.25,.88),(.35,.76),(.37,.60),(.31,.42),(.18,.34),(0,.34)],(0,0,0),jade)
    for z,r in ((.39,.36),(.81,.38),(.94,.29)):torus('Bronze_Furnace_Band',(0,0,z),r,.026,bronze)
    for x in (-.49,.49):torus('Side_Ring_Handle',(x,0,.77),.13,.029,bronze,(math.pi/2,0,0))
    lathe('Removable_Furnace_Lid',[(0,.94),(.31,.94),(.32,.97),(.28,1.00),(.23,1.09),(.10,1.16),(0,1.16)],(0,0,0),bronze)
    torus('Lid_Finial_Ring',(0,0,1.22),.068,.022,gold,(math.pi/2,0,0))
    for j in range(12):
        a=j*math.tau/12
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=.024,location=(.414*math.cos(a),.414*math.sin(a),.66))
        finish(bpy.context.object,'Bronze_Rivet',gold)
    for a in (-.30,0,.30):
        beam('Front_Bronze_Inlay',(a,-math.sqrt(.42**2-a*a)-.008,.51),(a,-math.sqrt(.42**2-a*a)-.008,.70),.012,bronze)

def cushion():
    lathe('Woven_Cushion',[(0,0),(.35,0),(.44,.035),(.46,.085),(.44,.14),(.37,.17),(0,.18)],(0,0,0),rope)
    for r in [i*.017 for i in range(3,26)]:torus('Woven_Concentric_Braid',(0,0,.18-.10*(r/.46)**4),r,.0055,board if round(r*1000)%2 else straw)
    for j in range(32):
        a=j*math.tau/32
        beam('Radial_Weave',(.08*math.cos(a),.08*math.sin(a),.181),(.41*math.cos(a),.41*math.sin(a),.14),.003,straw)
    for z,r in ((.055,.451),(.115,.451)):torus('Sage_Edge_Binding',(0,0,z),r,.014,cloth)
    box('Front_Cloth_Tag',(0,-.455,.085),(.09,.012,.085),cloth,.007)

BUILDERS={'HerbalStall':stall,'DryingRack':rack,'MortarPestle':mortar,'HerbPlanter':planter,'AlchemyFurnace':furnace,'MeditationCushion':cushion}
NAMES={'HerbalStall':'藥草攤','DryingRack':'晾藥架','MortarPestle':'研缽與杵','HerbPlanter':'靈草盆','AlchemyFurnace':'丹爐','MeditationCushion':'打坐蒲團'}
ids=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else list(BUILDERS)
for aid in ids:
    out=ROOT/'Models'/aid/'v001'; refs=ROOT/'ArtLibrary/Turnarounds'/f'{aid}_v001'
    if (refs/'views.json').exists():print('ALREADY_COMPLETE',aid,flush=True);continue
    out.mkdir(parents=True,exist_ok=True);refs.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True); scene=bpy.context.scene
    scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.0
    assets=bpy.data.collections.new('01_Editable_Asset');scene.collection.children.link(assets)
    root=bpy.data.objects.new(aid+'_ROOT',None);assets.objects.link(root)
    root['stage']='Editable appearance prototype; not game-ready; no gameplay, baked textures, LOD or collision validation.'
    wood=mat('Dark_Chestnut',(.20,.09,.045));board=mat('Warm_Timber',(.34,.19,.085))
    stone=mat('Blue_Gray_Stone',(.29,.36,.36));cloth=mat('Sage_Canvas',(.32,.41,.29))
    jade=mat('Celadon_Glaze',(.10,.26,.22),.12,.3);green=mat('Herb_Green',(.15,.28,.065))
    sage=mat('Young_Leaf',(.29,.40,.13));rope=mat('Natural_Hemp',(.48,.36,.19))
    gold=mat('Warm_Brass',(.57,.36,.10),.55,.32);bronze=mat('Aged_Bronze',(.29,.18,.07),.65,.35)
    soil=mat('Dark_Soil',(.07,.045,.02));petal=mat('Spirit_Flower',(.34,.35,.63));straw=mat('Golden_Straw',(.64,.48,.24))
    BUILDERS[aid]();bpy.context.view_layer.update()
    objects=[o for o in assets.objects if o.type=='MESH']
    def bounds():
        deps=bpy.context.evaluated_depsgraph_get()
        pts=[e.matrix_world@Vector(p) for o in objects for e in [o.evaluated_get(deps)] for p in e.bound_box]
        return Vector([min(p[i] for p in pts) for i in range(3)]),Vector([max(p[i] for p in pts) for i in range(3)])
    lo,hi=bounds();shift=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
    for o in objects:o.location-=shift
    bpy.context.view_layer.update();lo,hi=bounds();centre=(lo+hi)/2;extent=hi-lo
    studio=bpy.data.collections.new('90_Studio_Not_Exported');scene.collection.children.link(studio)
    def studio_obj(name,data):
        o=bpy.data.objects.new(name,data);studio.objects.link(o);return o
    cam=studio_obj('Reference_Camera',bpy.data.cameras.new('Reference_Camera'));scene.camera=cam;cam.data.type='ORTHO'
    cam.data.clip_start=.01;cam.data.clip_end=1000
    cam.data.ortho_scale=max(extent.length*1.18,.5)
    for name,direction,power,size in [('Key',(-3,-4,6),750,4),('Fill',(4,-1,3),450,4),('Rim',(0,4,5),650,3)]:
        d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size
        o=studio_obj(name,d);o.location=centre+Vector(direction);o.rotation_euler=(centre-o.location).to_track_quat('-Z','Y').to_euler()
    scene.world=bpy.data.worlds.new('Warm_Gray_Studio');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.19,.21,.20,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.7
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16;scene.cycles.use_denoising=True
    scene.render.resolution_x=1024;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
    scene.view_settings.view_transform='AgX'
    def position(direction):
        cam.location=centre+Vector(direction).normalized()*cam.data.ortho_scale*2.5
        cam.rotation_euler=(centre-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
    position((1,-1,.65))
    bpy.ops.object.select_all(action='DESELECT')
    for o in [root]+objects:o.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.export_scene.fbx(filepath=str(out/(aid+'_v001.fbx')),use_selection=True,object_types={'MESH','EMPTY'},add_leaf_bones=False,axis_forward='-Z',axis_up='Y',apply_unit_scale=True,bake_anim=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/(aid+'_v001.blend')))
    model_info={'asset':aid,'name_zh':NAMES[aid],'stage':'appearance_prototype','units':'meters','front':'-Y','dimensions_m':list(extent),'mesh_objects':len(objects),'source_concept':'ArtReferences/HerbalStall/concept.png' if aid=='HerbalStall' else None,'modeling_method':'procedural editable mesh; artist interpretation, not automatic image reconstruction','uv_baked':False,'collision':False,'lod':False,'unreal_import_verified':False}
    (out/'model_info.json').write_text(json.dumps(model_info,ensure_ascii=False,indent=2))
    records=[]
    from bpy_extras.object_utils import world_to_camera_view
    for name,direction in VIEWS:
        position(direction)
        deps=bpy.context.evaluated_depsgraph_get()
        projected=[world_to_camera_view(scene,cam,e.matrix_world@Vector(p)) for obj in objects for e in [obj.evaluated_get(deps)] for p in e.bound_box]
        assert all(.005<p.x<.995 and .005<p.y<.995 and p.z>0 for p in projected),(aid,name,'cropped')
        scene.render.filepath=str(refs/(name+'.png'));bpy.ops.render.render(write_still=True)
        records.append({'file':name+'.png','camera_location':list(cam.location),'direction':direction,'projection':'orthographic','framing_checked':True})
        print('VIEW_COMPLETE',aid,name,flush=True)
    (refs/'views.json').write_text(json.dumps({'asset':aid,'source':str((out/(aid+'_v001.blend')).relative_to(ROOT)),'same_geometry':True,'views':records},indent=2))
    print('ASSET_COMPLETE',aid,flush=True)
