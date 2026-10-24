"""Six editable landscape assets. Blender CLI; optional asset IDs after --.
Ten reference cameras use the exact same geometry at frame 1.
Wind animation is delivered in .blend; FBX exports the neutral static pose.
"""
import bpy,math,json,sys,random
from pathlib import Path
from mathutils import Vector,noise
ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[2]
VIEWS=[('01_front',(0,-1,0)),('02_right',(1,0,0)),('03_rear',(0,1,0)),('04_left',(-1,0,0)),('05_front_right',(1,-1,.45)),('06_rear_right',(1,1,.45)),('07_rear_left',(-1,1,.45)),('08_front_left',(-1,-1,.45)),('09_top',(0,0,1)),('10_high_front',(0,-1,1))]
NAMES={'CloudpiercerPeak':'凌雲孤峰','MountainRidge':'連綿山脊','LayeredCliff':'層岩峭壁','SectSummitPlateau':'宗門山頂平台','WindPine':'迎風松','WindGrass':'風動草叢'}
DETAILS={'CloudpiercerPeak':'Asymmetric tall rock peak and attached foothills; independent scenery mesh, no traversable trail.', 'MountainRidge':'Three connected-looking peak masses with a shared broad rocky base; overlapping editable meshes.', 'LayeredCliff':'Stratified vertical cliff segment, approximately 28 m wide; no automatic terrain seam.', 'SectSummitPlateau':'Flat summit at 48 m, central 44 x 62 m reserved for the sect; terrain perimeter is irregular. No navigable ascent yet.', 'WindPine':'Variant of existing WelcomingPine. Height-weighted looping shape-key sway with a fixed rocky base; Blender preview only.', 'WindGrass':'Independent 42-blade grass tuft with height-weighted looping shape-key sway; Blender preview only.'}

def mat(name,c):
    m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*c,1);bs.inputs['Roughness'].default_value=.88
    return m

def rockmat(name,dark,light,green=False):
    m=mat(name,tuple((x+y)/2 for x,y in zip(dark,light)));n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF')
    coord=n.new('ShaderNodeTexCoord');scale=n.new('ShaderNodeVectorMath');scale.operation='MULTIPLY';scale.inputs[1].default_value=(.18,.18,.9)
    l.new(coord.outputs['Object'],scale.inputs[0]);tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=1;tex.inputs['Detail'].default_value=4;l.new(scale.outputs[0],tex.inputs['Vector'])
    ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.22;ramp.color_ramp.elements[0].color=(*dark,1);ramp.color_ramp.elements[1].position=.8;ramp.color_ramp.elements[1].color=(*light,1)
    l.new(tex.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs['Color'],bs.inputs['Base Color'])
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.28;bump.inputs['Distance'].default_value=.12 if not green else .035
    l.new(tex.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],bs.inputs['Normal']);return m

def make_materials():
    global rock,moss,shale,earth,grassmats
    rock=rockmat('Jade_Gray_Weathered_Rock',(.075,.12,.13),(.29,.35,.32))
    shale=rockmat('Exposed_Pale_Strata',(.16,.20,.19),(.41,.42,.34))
    moss=rockmat('Moss_And_Summit_Turf',(.045,.09,.035),(.17,.24,.075),True)
    earth=mat('Dark_Grass_Roots',(.09,.075,.035))
    grassmats=[mat('Grass_Jade',(.065,.20,.10)),mat('Grass_Sage',(.18,.32,.12)),mat('Grass_Tips',(.32,.42,.15))]

def mesh(name,verts,faces,materials):
    d=bpy.data.meshes.new(name+'_Mesh');d.from_pydata(verts,[],faces);d.update();o=bpy.data.objects.new(name,d);assets.objects.link(o);o.parent=root
    for m in materials:d.materials.append(m)
    return o

def massif(name,center,rx,ry,height,seed,plateau=False):
    rng=random.Random(seed);n=64;rings=42 if height>20 else 16;verts=[]
    radial=[rng.uniform(-1,1) for _ in range(n)]
    phase=seed*.67
    for j in range(rings+1):
        t=j/rings
        if plateau:
            profile=1.10-.14*t+.08*math.sin(t*9)-.045*math.sin(t*33)
        else:
            profile=(1-t)**.62*(1-.16*math.sin(t*8))+.008
        for i in range(n):
            a=i*math.tau/n
            crag=.10*math.sin(7*a+phase)+.06*math.sin(13*a+phase*.2)+.027*radial[i]
            noiseval=noise.noise_vector(Vector((math.cos(a)*2+seed,math.sin(a)*2,t*3)))[0]
            p=profile+crag*(.9 if plateau else (1-t)**.62)+.045*noiseval*(1 if plateau else (1-t))
            leanx=0 if plateau else height*.065*t*math.sin(t*2+phase)
            leany=0 if plateau else height*.04*t*math.cos(t*3+phase)
            x=center[0]+rx*p*math.cos(a)+leanx;y=center[1]+ry*p*math.sin(a)+leany
            z=center[2]+height*t
            if j not in (0,rings):z+=height*.005*math.sin(5*a+phase)+height*.003*noiseval
            verts.append((x,y,z))
    faces=[]
    for j in range(rings):
        for i in range(n):
            a=j*n+i;b=j*n+(i+1)%n;c=(j+1)*n+(i+1)%n;d=(j+1)*n+i
            faces.extend([(a,b,d),(b,c,d)] if (i+j)%2 else [(a,b,c),(a,c,d)])
    faces.append(tuple(reversed(range(n))))
    # A coplanar triangle fan leaves the plateau central surface completely level.
    top=len(verts);verts.append((center[0]+(0 if plateau else height*.065*math.sin(2+phase)),center[1]+(0 if plateau else height*.04*math.cos(3+phase)),center[2]+height))
    for i in range(n):faces.append((rings*n+i,rings*n+(i+1)%n,top))
    o=mesh(name,verts,faces,[rock,shale,moss])
    for p in o.data.polygons:
        z=p.center.z-center[2]
        if p.normal.z>.52 and z>height*.12:p.material_index=2
        elif (int(z/(height*.14))%3)==1:p.material_index=1
        else:p.material_index=0
    return o

def peak():
    massif('Main_Rock_Spire',(0,0,0),17,14,68,17)
    massif('Attached_Spur_West',(-13,2,0),8,9,37,39)
    massif('Attached_Spur_East',(10,5,0),8,7,30,24)
    massif('Eroded_Foot',(-1,-2,0),22,18,9,73)

def ridge():
    massif('Ridge_Foot',(0,0,0),40,15,10,55)
    for idx,(x,y,rx,ry,h) in enumerate([(-23,1,14,12,31),(-2,2,16,13,49),(21,0,14,11,38)]):
        massif('Ridge_Peak_%02d'%idx,(x,y,0),rx,ry,h,62+idx*11)

def cliff():
    # Broad central buttress and unequal side blocks create a layered wall silhouette.
    massif('Cliff_Central',(0,0,0),14,6,25,91,True)
    massif('Cliff_Left',(-10,1,0),5,6,22,92,True)
    massif('Cliff_Right',(11,1,0),5,5,19,96,True)

def plateau():
    massif('Summit_Main',(0,0,0),42,52,48,121,True)
    massif('Summit_Buttress_West',(-28,6,0),15,20,34,122,True)
    massif('Summit_Buttress_East',(29,15,0),14,18,30,126,True)
    root['summit_surface_z']=48.0;root['reserved_rectangle_m']=[44.0,62.0]

def pine():
    path=PROJECT/'Models/WelcomingPine/v001/WelcomingPine_v001.blend'
    with bpy.data.libraries.load(str(path),link=False) as (src,dst):dst.collections=[n for n in src.collections if n.startswith(('01_','02_','03_'))]
    for c in dst.collections:bpy.context.scene.collection.children.link(c)
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
    for c in dst.collections:
        for src in list(c.all_objects):
            if src.type!='MESH':continue
            ev=src.evaluated_get(dg);d=bpy.data.meshes.new_from_object(ev,depsgraph=dg)
            o=bpy.data.objects.new(src.name+'_WindReady',d);assets.objects.link(o);o.matrix_world=src.matrix_world.copy();o.parent=root
    for c in dst.collections:
        for o in list(c.all_objects):bpy.data.objects.remove(o,do_unlink=True)
        bpy.data.collections.remove(c)

def grass():
    rng=random.Random(713);vs=[];fs=[]
    for i in range(42):
        a=rng.uniform(0,math.tau);r=rng.uniform(.02,.32);x=r*math.cos(a);y=r*math.sin(a);h=rng.uniform(.38,.92);w=rng.uniform(.022,.052);bend=rng.uniform(.12,.36)
        offset=len(vs)
        for j in range(7):
            t=j/6;cx=x+math.cos(a)*bend*t*t;cy=y+math.sin(a)*bend*t*t
            for side in (-1,1):vs.append((cx-side*math.sin(a)*w*(1-t),cy+side*math.cos(a)*w*(1-t),h*t))
        for j in range(6):k=offset+j*2;fs.append((k,k+1,k+3,k+2))
    o=mesh('Grass_Blades',vs,fs,grassmats)
    for i,p in enumerate(o.data.polygons):p.material_index=(i//6)%3
    # Deliberately no ground disk: this tuft sits directly on terrain at its roots.

def add_wind(objects,aid):
    lo,hi=actual_bounds(objects);H=hi.z;amplitude=.32 if aid=='WindPine' else .16
    animated=0
    for o in objects:
        if aid=='WindPine' and any(s in o.name.lower() for s in ('rock','moss')):continue
        inv=o.matrix_world.inverted();basis=o.shape_key_add(name='Basis');a=o.shape_key_add(name='Wind_Main');b=o.shape_key_add(name='Wind_Gust')
        for idx,v in enumerate(basis.data):
            p=o.matrix_world@v.co;weight=max(0,min(1,p.z/H))**1.7
            a.data[idx].co=inv@(p+Vector((amplitude*weight,amplitude*.23*weight,0)))
            b.data[idx].co=inv@(p+Vector((amplitude*.14*weight,amplitude*.37*weight,0)))
        for key,mul in ((a,1),(b,2)):
            key.slider_min=-1
            for f in range(1,98,8):key.value=math.sin((f-1)/96*math.tau*mul);key.keyframe_insert(data_path='value',frame=f)
        animated+=1
    root['wind_loop_frames']=96;root['wind_preview_only']=True;root['animated_mesh_count']=animated
    bpy.context.scene.frame_set(1)

BUILDERS={'CloudpiercerPeak':peak,'MountainRidge':ridge,'LayeredCliff':cliff,'SectSummitPlateau':plateau,'WindPine':pine,'WindGrass':grass}
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
    make_materials()
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
    if aid not in ('WindPine','WindGrass'):scene.view_settings.exposure=-.55
    def position(direction):
        cam.location=centre+Vector(direction).normalized()*cam.data.ortho_scale*2.3
        cam.rotation_euler=(centre-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
    scene.frame_start=1;scene.frame_end=97;scene.render.fps=24;scene.frame_set(1)
    position((1,-1,.65));bpy.ops.object.select_all(action='DESELECT')
    for o in [root]+objects:o.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.export_scene.fbx(filepath=str(out/(aid+'_v001.fbx')),use_selection=True,object_types={'MESH','EMPTY'},add_leaf_bones=False,axis_forward='-Z',axis_up='Y',apply_unit_scale=True,bake_anim=False)
    if aid in ('WindPine','WindGrass'): add_wind(objects,aid)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/(aid+'_v001.blend')))
    info={'asset':aid,'name_zh':NAMES[aid],'stage':'editable_landscape_prototype','description':DETAILS[aid],'units':'meters','front':'-Y','dimensions_m':list(extent),'mesh_objects':len(objects),'bounds_method':'evaluated mesh vertices','modeling_method':'editable geometry; all ten views rendered at frame 1 from the same model','animation':('Blender shape keys, 96-frame wind loop; FBX is static' if aid in ('WindPine','WindGrass') else 'static'),'uv_baked':False,'collision':False,'lod':False,'unreal_import_verified':False}
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
