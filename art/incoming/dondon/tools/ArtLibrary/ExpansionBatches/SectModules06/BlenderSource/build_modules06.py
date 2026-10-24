"""Build eight sect boundary, stair, training and herb modules and render ten views per asset.
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

# 4 m wall module with end-to-end connectors; the short terminal pillar is not duplicated.
def wall_part(length=4):
    box('Wall_Footing',(0,0,.16),(length,.60,.32),stone,.025)
    box('Wall_Plaster_Core',(0,0,1.27),(length,.32,1.58),plaster,.025)
    box('Wall_Lower_Course',(0,0,.40),(length,.46,.16),stone,.018)
    box('Wall_Top_Beam',(0,0,2.125),(length,.43,.13),wood,.015)
    # Continuous pitch cap, ending exactly at the modular connection planes.
    for side in (-1,1):
        verts=[(-length/2,0,2.37),(length/2,0,2.37),(length/2,side*.37,2.17),(-length/2,side*.37,2.17)]
        faces=[(0,1,2,3)] if side>0 else [(3,2,1,0)]
        o=mesh('Wall_Pitched_Cap',verts,faces,tile);mod=o.modifiers.new('Cap_Thickness','SOLIDIFY');mod.thickness=.045
        for i in range(1,int(length/.22)):
            x=-length/2+i*length/int(length/.22)
            beam('Wall_Tile_Roll',(x,0,2.39),(x,side*.36,2.19),.025,tilelight)
    # Restrained inset panels retain solid masonry, rather than claiming cut-out openings.
    for x in (-length/4,length/4):
        for side in (-1,1):
            box('Wall_Recess_Border',(x,side*.176,1.28),(.85,.025,.64),wood,.018)
            box('Wall_Jade_Inset',(x,side*.197,1.28),(.74,.018,.53),jade,.015)
            for xx in (-.23,0,.23):box('Panel_Lattice',(x+xx,side*.215,1.28),(.028,.02,.50),gold,.004)

def straight():wall_part(4)

def corner():
    # A solid elbow pier with two short returns, on a 1.0 m square footprint.
    box('Corner_Stone_Base',(0,0,.18),(.92,.92,.36),stone,.035)
    box('Corner_Pier',(0,0,1.26),(.62,.62,1.80),plaster,.03)
    box('Corner_Collar',(0,0,2.16),(.78,.78,.15),wood,.02)
    bpy.ops.mesh.primitive_cone_add(vertices=4,radius1=.70,radius2=.08,depth=.42,location=(0,0,2.43),rotation=(0,0,math.pi/4))
    finish(bpy.context.object,'Corner_Tiled_Pyramid',tile,.025)
    cyl('Corner_Finial',(0,0,2.69),.065,.13,gold)
    for x in (-.34,.34):
        for y in (-.34,.34):box('Corner_Trim',(x,y,1.25),(.055,.055,1.7),wood,.01)

def courtyard_gate():
    # Ground-level threshold; side posts leave a clear 2.0 m entrance.
    for x in (-1.18,1.18):
        box('Gate_Stone_Pedestal',(x,0,.15),(.46,.55,.30),stone,.035)
        post(x,0,.30,2.26)
    box('Gate_Lintel',(0,0,2.77),(2.8,.27,.22),wood,.03)
    roof('Courtyard_Gate_Roof',3.4,1.55,2.94,.66)
    plaque('Courtyard_Crest',0,-.20,2.54,1.3,.34)
    for side in (-1,1):
        # Two separate closed leaves, with geometry-backed frame and lattice.
        cx=side*.50
        box('Gate_Leaf_Panel',(cx,0,1.18),(.965,.10,2.10),board,.018)
        for z in (.32,1.05,2.14):box('Gate_Leaf_Rail',(cx,-.075,z),(.82,.06,.09),wood,.01)
        for x in (-.44,.44):box('Gate_Leaf_Stile',(cx+x,-.075,1.18),(.06,.06,2.03),wood,.01)
        for y in (-.09,.09):torus('Gate_Ring_Handle',(side*.16,y,1.2),.075,.014,gold,(math.pi/2,0,0))
        for z in (.45,1.95):cyl('Gate_Hinge_Barrel',(side*.99,0,z),.04,.20,bronze)


def stairs():
    # 18 risers of 0.1667 m and 0.28 m treads: rise 3 m, run 5.04 m.
    n=18;rise=3.0;run=5.04;width=1.5
    for i in range(n):
        z=(i+1)*rise/n;y=-run/2+(i+.5)*run/n
        box('Stair_Tread_%02d'%i,(0,y,z-.045),(width,.29,.09),board,.015)
        box('Stair_Riser_%02d'%i,(0,y-.135,z-rise/n/2),(width,.035,rise/n-.025),wood,.008)
    for x in (-.64,.64):
        vertices=[(x+dx,y,z) for dx in (-.07,.07) for y,z in [(-2.35,0),(-2.35,.04),(2.52,2.938),(2.52,2.718)]]
        mesh('Stair_Solid_Stringer',vertices,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],wood)
        for i in (0,4,8,12,17):
            y=-run/2+(i+.5)*run/n;z=(i+1)*rise/n
            box('Stair_Baluster',(x,y,z+.43),(.07,.07,.86),wood,.012)
        beam('Stair_Handrail',(x,-run/2+.14,1.02),(x,run/2-.14,3.86),.055,board)
    box('Stair_Top_Landing',(0,run/2+.40,2.95),(1.5,.8,.10),board,.018)
    for x in (-.64,.64):box('Landing_Support',(x,run/2+.68,1.45),(.12,.12,2.9),wood,.02)

def dummy():
    cyl('Dummy_Stone_Socket',(0,0,.13),.35,.26,stone)
    cyl('Training_Dummy_Trunk',(0,0,.92),.16,1.50,board)
    cyl('Training_Dummy_Head',(0,0,1.81),.22,.27,rope)
    for z in (.65,1.0,1.30):torus('Dummy_Rope_Wrap',(0,0,z),.17,.025,rope)
    beam('Dummy_Arms',(-.53,0,1.25),(.53,0,1.25),.085,wood)
    beam('Dummy_Angled_Leg',(0,0,.65),(.35,-.35,.30),.075,wood)

def spirit_herb(stage):
    scale=(.38,.68,1.0)[stage];count=(2,3,5)[stage]
    lathe('Herb_Root_Crown',[(0,0),(.027*scale,0),(.035*scale,.04*scale),(0,.06*scale)],(0,0,0),board,24)
    for j in range(count):
        a=j*math.tau/count;start=Vector((0,0,.035*scale));tip=start+Vector((.12*math.cos(a),.12*math.sin(a),.36+.025*(j%2)))*scale
        beam('Herb_Stem',start,tip,.007*scale,green)
        for t in ((.45,.8) if stage==0 else (.30,.58,.86)):
            origin=start+(tip-start)*t
            for sign in (-1,1):
                end=origin+Vector((.15*math.cos(a+sign*1.0),.15*math.sin(a+sign*1.0),.06))*scale
                leaf('Herb_Leaf',origin,end,.045*scale,sage if stage<2 else green)
        if stage==2:
            cyl('Flower_Centre',tip,.018,.02,gold)
            for k in range(5):
                angle=k*math.tau/5;end=tip+Vector((.055*math.cos(angle),.055*math.sin(angle),.018))
                leaf('Spirit_Flower_Petal',tip,end,.021,jade)

def seedling():spirit_herb(0)
def young():spirit_herb(1)
def mature():spirit_herb(2)

BUILDERS={'SectWallStraight':straight,'SectWallCorner':corner,'CourtyardGate':courtyard_gate,'TimberStairFlight':stairs,'TrainingDummy':dummy,'SpiritHerbSeedling':seedling,'SpiritHerbYoung':young,'SpiritHerbMature':mature}
NAMES={'SectWallStraight':'宗門直牆模組','SectWallCorner':'宗門轉角柱','CourtyardGate':'宗門院門','TimberStairFlight':'木構樓梯','TrainingDummy':'演武木樁','SpiritHerbSeedling':'靈草幼苗','SpiritHerbYoung':'靈草成長株','SpiritHerbMature':'靈草成熟株'}
DETAILS={'SectWallStraight':'4 m long wall module; connectors at local X +/-2 m. Static plaster, stone, timber and tile geometry.','SectWallCorner':'Corner pier for wall joints. Place wall ends against the 0.62 m central pier; does not auto-snap.','CourtyardGate':'Separate closed door leaves and hinge barrels; no rig, door animation or navigation.','TimberStairFlight':'3 m total rise, 18 steps, 0.28 m tread, 1.5 m width with landing and handrails. Not yet fitted into the scripture library.','TrainingDummy':'Independently built training dummy matching the existing training-ground style; no animation or interaction.','SpiritHerbSeedling':'Two-stem seedling growth appearance; not a harvest interaction.','SpiritHerbYoung':'Three-stem intermediate growth appearance; no growth animation.','SpiritHerbMature':'Five-stem flowering mature plant; no harvested-state model or wind rig.'}
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
        d=bpy.data.lights.new(name,'AREA');d.energy=power*ls*ls/7;d.shape='DISK';d.size=ls
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
