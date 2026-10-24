"""Editable mountain-water prototypes. References use one fixed mesh per asset.
Run with Blender --background --python this_file.py -- [asset IDs].
Water is styled static mesh geometry, not a fluid simulation.
"""
import bpy, math, random, json, sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
NAMES={'WaterfallCliff':'山崖瀑布','MountainStreamBend':'彎曲山溪','SpiritSpringPool':'靈泉水潭'}
VIEWS=[('01_front',(0,-1,0)),('02_right',(1,0,0)),('03_rear',(0,1,0)),('04_left',(-1,0,0)),('05_front_right',(1,-1,.6)),('06_rear_right',(1,1,.6)),('07_rear_left',(-1,1,.6)),('08_front_left',(-1,-1,.6)),('09_top',(0,0,1)),('10_high_front',(0,-1,1))]

def material(name,color,rough=.8,noise_scale=6):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough
    tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=noise_scale;tex.inputs['Detail'].default_value=3
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.22;bump.inputs['Distance'].default_value=.065 if rough>.5 else .018
    l.new(tex.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],bs.inputs['Normal'])
    return m

def mesh(name,verts,faces,mat,smooth=False):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    ob=bpy.data.objects.new(name,data);assets.objects.link(ob);ob.parent=root;data.materials.append(mat)
    for f in data.polygons:f.use_smooth=smooth
    return ob

def rock(name,pos,scale,seed,mat=None):
    rng=random.Random(seed);n=12;verts=[]
    rings=[(0,.7),(.15,1),(.48,1.02),(.78,.80),(1,.48)]
    radial=[rng.uniform(.80,1.14) for i in range(n)]
    for j,(z,f) in enumerate(rings):
        for i in range(n):
            a=math.tau*i/n;rr=radial[i]*f*rng.uniform(.94,1.06)
            zz=z+(rng.uniform(-.05,.05) if j not in (0,4) else 0)
            verts.append((pos[0]+scale[0]*rr*math.cos(a),pos[1]+scale[1]*rr*math.sin(a),pos[2]+scale[2]*zz))
    faces=[tuple(reversed(range(n))),tuple(range(4*n,5*n))]
    faces += [(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(4) for i in range(n)]
    ob=mesh(name,verts,faces,mat or stone)
    ob.data.materials.append(pale);ob.data.materials.append(moss)
    for p in ob.data.polygons if mat is not foam else []:
        if p.center.z>pos[2]+scale[2]*.76 and rng.random()<.7:p.material_index=2
        elif rng.random()<.16:p.material_index=1
    return ob

def ellipse(name,c,rx,ry,depth,mat,n=80):
    verts=[(c[0]+rx*math.cos(i*math.tau/n),c[1]+ry*math.sin(i*math.tau/n),c[2]+dz) for dz in (-depth,0) for i in range(n)]
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,n+(i+1)%n,n+i) for i in range(n)]
    return mesh(name,verts,faces,mat)

def line(name,points,radius,mat,sides=6):
    verts=[]
    for j,p in enumerate(points):
        p=Vector(p);delta=Vector(points[min(j+1,len(points)-1)])-Vector(points[max(j-1,0)])
        tangent=delta.normalized();normal=tangent.cross(Vector((0,0,1)))
        if normal.length<.01:normal=tangent.cross(Vector((0,1,0)))
        normal.normalize();other=tangent.cross(normal).normalized()
        verts.extend([tuple(p+radius*(normal*math.cos(i*math.tau/sides)+other*math.sin(i*math.tau/sides))) for i in range(sides)])
    faces=[tuple(reversed(range(sides))),tuple(range((len(points)-1)*sides,len(points)*sides))]
    faces += [(j*sides+i,j*sides+(i+1)%sides,(j+1)*sides+(i+1)%sides,(j+1)*sides+i) for j in range(len(points)-1) for i in range(sides)]
    return mesh(name,verts,faces,mat,True)

def reeds(x,y,z,seed):
    rng=random.Random(seed)
    for k in range(6):
        a=rng.uniform(0,math.tau);h=rng.uniform(.35,.8);dx=math.cos(a);dy=math.sin(a)
        verts=[(x-.035*dy,y+.035*dx,z),(x+.035*dy,y-.035*dx,z),
               (x+dx*.20+.025*dy,y+dy*.20-.025*dx,z+h*.65),(x+dx*.20-.025*dy,y+dy*.20+.025*dx,z+h*.65),
               (x+dx*.45,y+dy*.45,z+h)]
        mesh('Reed_Leaf',verts,[(0,1,2,3),(3,2,4)],leaf)

def ripples(c,rx,ry,count=3):
    for k in range(count):
        points=[(c[0]+rx*(1+k*.30)*math.cos(a),c[1]+ry*(1+k*.30)*math.sin(a),c[2]) for a in [math.tau*i/52 for i in range(43)]]
        line('Broken_Water_Ripple',points,.012,foam)

def waterfall():
    ellipse('Pool_Rock_Foundation',(0,-1,.35),5.2,4.8,.35,stone)
    ellipse('Water_Lower_Pool',(0,-1,.52),4.65,4.1,.13,water)
    for j in range(24):
        a=math.tau*j/24;x=4.9*math.cos(a);y=-1+4.45*math.sin(a)
        rock('Pool_Shore_Rock',(x,y,.22),(.62,.66,.55+(j%3)*.1),100+j)
        if j%4==0:reeds(x,y,.72,700+j)
    # Irregular overlapping rock columns form a readable, full-depth cliff mass.
    for i in range(7):
        x=-4.8+i*1.6;h=[5.4,7.8,9.8,9.3,10.6,8.5,6.0][i]
        rock('Cliff_Main_Pillar',(x,2.8,.25),(1.6,2.0,h),20+i)
    rock('Waterfall_Lip',(.1,1.0,8.8),(1.85,1.75,.65),45)
    upstream=mesh('Water_Upper_Source',[(-1.05,-.85,9.58),(1.05,-.85,9.58),(1.05,2,9.58),(-1.05,2,9.58)],[(0,1,2,3)],water)
    upstream.modifiers.new('Water_Source_Thickness','SOLIDIFY').thickness=.05
    verts=[];rows=48;cols=18
    for j in range(rows+1):
        t=j/rows;z=9.58-9.03*t;y=-.85-.5*t*t
        for i in range(cols+1):
            u=i/cols;w=1.05+.28*t;verts.append(((u*2-1)*w,y+.065*math.sin(u*math.tau*4+t*8),z+.035*math.sin(u*15+t*9)))
    ob=mesh('Water_Falling_Curtain',verts,[(j*(cols+1)+i,j*(cols+1)+i+1,(j+1)*(cols+1)+i+1,(j+1)*(cols+1)+i) for j in range(rows) for i in range(cols)],water,True)
    thick=ob.modifiers.new('Thin_Water_Sheet','SOLIDIFY');thick.thickness=.045
    for i in range(11):
        x=-.95+i*.19
        line('Waterfall_White_Streak',[(x*(1+.25*t),-.98-.5*t*t+.025*math.sin(t*25+i),9.55-9*t) for t in [j/40 for j in range(41)]],.014+(i%3)*.008,foam)
    for i in range(18):
        a=i*2.4;r=.2+.11*(i%6)
        rock('Impact_Foam',(r*math.cos(a),-1.5+r*.6*math.sin(a),.53),(.24,.17,.08+(i%4)*.02),800+i,foam)
    ripples((0,-1.5,.56),1.1,.68,4)

def stream():
    rows=60;cols=8
    def center(y):return .85*math.sin(y*.55)
    for name,width,z,depth,mat in [('Streambed',2.55,.22,.22,stone),('Water_Stream',1.32,.36,.10,water)]:
        verts=[]
        for j in range(rows+1):
            y=-5+j/rows*10
            for i in range(cols+1):verts.append((center(y)+(i/cols*2-1)*width,y,z))
        ob=mesh(name,verts,[(j*(cols+1)+i,j*(cols+1)+i+1,(j+1)*(cols+1)+i+1,(j+1)*(cols+1)+i) for j in range(rows) for i in range(cols)],mat)
        mod=ob.modifiers.new('Closed_Thickness','SOLIDIFY');mod.thickness=depth
    rng=random.Random(912)
    for side in (-1,1):
        for j in range(21):
            y=-4.7+j*.47;x=center(y)+side*rng.uniform(1.65,2.1)
            rock('Streambank_Rock',(x,y,.18),(rng.uniform(.45,.70),rng.uniform(.4,.65),rng.uniform(.28,.65)),900+j+(side+1)*40)
            if j%3==1:reeds(x,y,.65,1200+j+(side+1)*30)
    for j in range(4):
        y=-3.5+j*2.3;x=center(y)+(-1 if j%2 else 1)*.6
        rock('Exposed_Stream_Stone',(x,y,.2),(.42,.60,.3),330+j,pale)
        line('Flow_Highlight',[(center(yy)+(-.5+j*.3),yy,.38) for yy in [y+i*.09 for i in range(16)]],.012,foam)

def spring():
    ellipse('Spring_Limestone_Base',(0,0,.3),3.9,3.2,.3,stone)
    ellipse('Water_Spring_Surface',(0,0,.53),3.15,2.55,.12,water)
    rng=random.Random(126)
    for j in range(25):
        a=j*math.tau/25;x=3.45*math.cos(a);y=2.8*math.sin(a)
        rock('Spring_Rim_Stone',(x,y,.2),(.52,.58,rng.uniform(.45,.86)),j+440,pale)
        if j%4==0:reeds(x,y,.8,j+544)
    rock('Spring_Source_Outcrop',(0,2.3,.3),(1.45,1.1,2),120)
    for i in range(5):
        x=-.7+i*.33;h=[.7,1.25,1.6,.95,.55][i];z=1.8
        verts=[(x+.14*math.cos(a),2.25+.14*math.sin(a),z) for a in [j*math.tau/6 for j in range(6)]]
        verts += [(x+.12*math.cos(a),2.25+.12*math.sin(a),z+h*.7) for a in [j*math.tau/6 for j in range(6)]]+[(x+.12,2.2,z+h)]
        mesh('Jade_Crystal',verts,[tuple(reversed(range(6)))]+[(j,(j+1)%6,6+(j+1)%6,6+j) for j in range(6)]+[(6+j,6+(j+1)%6,12) for j in range(6)],jade)
    line('Spring_Source_Trickle',[(0,1.35,1.65),(0,1.15,1.3),(.06,.98,.9),(.1,.8,.56)],.075,water,10)
    ripples((.1,.45,.56),.55,.38,3)
    for x,y,rx in [(-1.4,-.5,.35),(-1.9,.2,.26),(1.4,-.9,.30)]:
        n=36;verts=[(x,y,.56)]+[(x+rx*math.cos(a),y+rx*math.sin(a),.56) for a in [math.tau*.93*j/n for j in range(n+1)]]
        mesh('Lotus_Leaf',verts,[(0,i,i+1) for i in range(1,n+1)],leaf)

BUILDERS={'WaterfallCliff':waterfall,'MountainStreamBend':stream,'SpiritSpringPool':spring}
def bounds(objects):
    dg=bpy.context.evaluated_depsgraph_get();pts=[o.evaluated_get(dg).matrix_world@v.co for o in objects for v in o.evaluated_get(dg).data.vertices]
    return Vector([min(p[i] for p in pts) for i in range(3)]),Vector([max(p[i] for p in pts) for i in range(3)])

def build(aid):
    global assets,root,stone,pale,moss,water,foam,leaf,jade
    out=ROOT/'Models'/aid/'v001';refs=ROOT/'ArtLibrary/Turnarounds'/f'{aid}_v001'
    if (refs/'views.json').exists():print('ALREADY_COMPLETE',aid,flush=True);return
    out.mkdir(parents=True,exist_ok=True);refs.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;bpy.context.preferences.filepaths.save_version=0
    s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
    assets=bpy.data.collections.new('01_Editable_Asset');s.collection.children.link(assets)
    root=bpy.data.objects.new(aid+'_ROOT',None);assets.objects.link(root)
    stone=material('Blue_Grey_Limestone',(.22,.27,.25));pale=material('Pale_Limestone',(.38,.40,.32));moss=material('Moss',(.11,.20,.07))
    water=material('Jade_Water',(.035,.30,.29),.22,12);foam=material('Water_Foam',(.70,.84,.78),.4,25)
    leaf=material('Reed_And_Lotus',(.14,.27,.075));jade=material('Spirit_Jade',(.14,.57,.43),.24)
    BUILDERS[aid]();bpy.context.view_layer.update();objects=[o for o in assets.objects if o.type=='MESH']
    lo,hi=bounds(objects);shift=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
    for o in objects:o.location-=shift
    bpy.context.view_layer.update();lo,hi=bounds(objects);extent=hi-lo;centre=(lo+hi)/2
    studio=bpy.data.collections.new('90_Studio_Not_Exported');s.collection.children.link(studio)
    def add(name,data):
        ob=bpy.data.objects.new(name,data);studio.objects.link(ob);return ob
    cam=add('Reference_Camera',bpy.data.cameras.new('Reference_Camera'));s.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=extent.length*1.08;cam.data.clip_end=1000
    ls=max(extent)*.65
    for name,dr,power in [('Key',(-.8,-1.1,1.5),1100),('Fill',(1.2,-.4,.9),650),('Rim',(.2,1.1,1.3),950)]:
        d=bpy.data.lights.new(name,'AREA');d.energy=power*ls*ls/7;d.shape='DISK';d.size=ls;o=add(name,d);o.location=centre+Vector(dr)*ls;o.rotation_euler=(centre-o.location).to_track_quat('-Z','Y').to_euler()
    s.world=bpy.data.worlds.new('Neutral_Studio');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.19,.21,.22,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.65
    s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=16;s.cycles.use_denoising=True
    s.render.resolution_x=1024;s.render.resolution_y=1024;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
    def position(dr):
        cam.location=centre+Vector(dr).normalized()*cam.data.ortho_scale*2.3;cam.rotation_euler=(centre-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
    position((1,-1,.6));bpy.ops.object.select_all(action='DESELECT')
    for o in [root]+objects:o.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.export_scene.fbx(filepath=str(out/(aid+'_v001.fbx')),use_selection=True,object_types={'MESH','EMPTY'},add_leaf_bones=False,axis_forward='-Z',axis_up='Y',apply_unit_scale=True,bake_anim=False)
    root['water_type']='Static styled mesh water; not fluid simulation';bpy.ops.wm.save_as_mainfile(filepath=str(out/(aid+'_v001.blend')))
    info={'asset':aid,'name_zh':NAMES[aid],'units':'meters','front':'-Y','dimensions_m':list(extent),'mesh_objects':len(objects),'same_geometry_ten_views':True,'water':'static mesh','uv_baked':False,'collision':False,'lod':False,'unreal_import_verified':False}
    if aid=='MountainStreamBend':info['water_endpoints_m']=[list(Vector((.85*math.sin(y*.55),y,.36))-shift) for y in [-5,5]]
    (out/'model_info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2))
    from bpy_extras.object_utils import world_to_camera_view
    records=[]
    for name,dr in VIEWS:
        position(dr);dg=bpy.context.evaluated_depsgraph_get()
        projected=[world_to_camera_view(s,cam,e.matrix_world@Vector(p)) for o in objects for e in [o.evaluated_get(dg)] for p in e.bound_box]
        assert all(.005<p.x<.995 and .005<p.y<.995 and p.z>0 for p in projected),(aid,name,'cropped')
        s.render.filepath=str(refs/(name+'.png'));bpy.ops.render.render(write_still=True)
        records.append({'file':name+'.png','direction':dr,'camera_location':list(cam.location),'projection':'orthographic','framing_checked':True});print('VIEW_COMPLETE',aid,name,flush=True)
    (refs/'views.json').write_text(json.dumps({'asset':aid,'source':str((out/(aid+'_v001.blend')).relative_to(ROOT)),'same_geometry':True,'views':records},indent=2))
    print('ASSET_COMPLETE',aid,flush=True)

if __name__=='__main__':
    for aid in (sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else BUILDERS):build(aid)
