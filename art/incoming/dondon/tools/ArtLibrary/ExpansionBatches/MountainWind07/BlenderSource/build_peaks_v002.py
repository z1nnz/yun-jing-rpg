"""CloudpiercerPeak / MountainRidge v002: karst stone-pillar peaks (Zhangjiajie / Huangshan style).
v001 lathed sine-wave cones read as striped onions. v002 pillars have near-vertical cliffs, stepped
strata ledges, vertical fissures, blocky cell-noise faces and mossy caps; moss/strata come from the
shader (normal + height), so any edit to the mesh keeps reading correctly. v001 files stay untouched.
Blender CLI: blender -b -P this.py [-- CloudpiercerPeak MountainRidge] [-- preview]
"""
import bpy,math,json,sys,random
from pathlib import Path
from mathutils import Vector,noise
from bpy_extras.object_utils import world_to_camera_view
ROOT=Path(__file__).resolve().parents[1]
VIEWS=[('01_front',(0,-1,0)),('02_right',(1,0,0)),('03_rear',(0,1,0)),('04_left',(-1,0,0)),('05_front_right',(1,-1,.45)),('06_rear_right',(1,1,.45)),('07_rear_left',(-1,1,.45)),('08_front_left',(-1,-1,.45)),('09_top',(0,0,1)),('10_high_front',(0,-1,1))]
NAMES={'CloudpiercerPeak':'凌雲孤峰','MountainRidge':'連綿山脊'}
DETAILS={'CloudpiercerPeak':'Karst stone-pillar peak: 68 m main pillar with four fused satellite pillars and a mossy talus foot; strata ledges and vertical fissures. Scenery mesh, no trail.',
         'MountainRidge':'Ridge of nine karst pillars (20-49 m) rising from a 22 m spine on a shared talus foot; strata ledges and vertical fissures. Overlapping editable meshes.'}

def smooth(e0,e1,x):
    t=max(0,min(1,(x-e0)/(e1-e0)));return t*t*(3-2*t)

def rock_material():
    m=bpy.data.materials.new('Karst_Rock_Moss');m.use_nodes=True;m.diffuse_color=(.22,.26,.24,1)
    nt=m.node_tree;n=nt.nodes;l=nt.links;n.clear()
    def node(t,**kw):
        x=n.new(t)
        for k,v in kw.items():x.inputs[k].default_value=v
        return x
    out=node('ShaderNodeOutputMaterial');bs=node('ShaderNodeBsdfPrincipled',Roughness=.92);l.new(bs.outputs[0],out.inputs['Surface'])
    tc=n.new('ShaderNodeTexCoord');geo=n.new('ShaderNodeNewGeometry')
    # Strata: distorted horizontal bands in object space (meters).
    wave=node('ShaderNodeTexWave',Scale=.09,Distortion=3.5,**{'Detail':3,'Detail Scale':1.5});wave.wave_type='BANDS';wave.bands_direction='Z'
    l.new(tc.outputs['Object'],wave.inputs['Vector'])
    tone=node('ShaderNodeTexNoise',Scale=.12,Detail=6,Roughness=.6);l.new(tc.outputs['Object'],tone.inputs['Vector'])
    strata=n.new('ShaderNodeValToRGB');e=strata.color_ramp.elements
    e[0].position=.25;e[0].color=(.07,.10,.10,1);e[1].position=.75;e[1].color=(.26,.27,.23,1)
    e2=e.new(.5);e2.color=(.14,.17,.16,1)
    mixv=node('ShaderNodeMath',Value=0);mixv.operation='MULTIPLY_ADD'
    mixv.inputs[1].default_value=.55;l.new(wave.outputs['Fac'],mixv.inputs[0]);l.new(tone.outputs['Fac'],mixv.inputs[2])
    l.new(mixv.outputs[0],strata.inputs['Fac'])
    # Moss where the surface faces up (ledges, caps), broken up by noise.
    sep=n.new('ShaderNodeSeparateXYZ');l.new(geo.outputs['Normal'],sep.inputs[0])
    mossn=node('ShaderNodeTexNoise',Scale=.35,Detail=4);l.new(tc.outputs['Object'],mossn.inputs['Vector'])
    up=n.new('ShaderNodeMath');up.operation='MULTIPLY_ADD';up.inputs[1].default_value=.35;l.new(mossn.outputs['Fac'],up.inputs[0]);l.new(sep.outputs['Z'],up.inputs[2])
    mfac=node('ShaderNodeMapRange',**{'From Min':.78,'From Max':.92});mfac.clamp=True;l.new(up.outputs[0],mfac.inputs['Value'])
    mossc=n.new('ShaderNodeValToRGB');me=mossc.color_ramp.elements;me[0].color=(.05,.10,.035,1);me[1].color=(.16,.25,.07,1);l.new(mossn.outputs['Fac'],mossc.inputs['Fac'])
    mix=n.new('ShaderNodeMix');mix.data_type='RGBA';l.new(mfac.outputs['Result'],mix.inputs['Factor']);l.new(strata.outputs['Color'],mix.inputs[6]);l.new(mossc.outputs['Color'],mix.inputs[7])
    # Crevice darkening.
    ao=node('ShaderNodeAmbientOcclusion',Distance=2.5);ao.samples=8;l.new(mix.outputs[2],ao.inputs['Color'])
    aomix=n.new('ShaderNodeMix');aomix.data_type='RGBA';aomix.blend_type='MULTIPLY';aomix.inputs['Factor'].default_value=.6
    l.new(mix.outputs[2],aomix.inputs[6]);l.new(ao.outputs['AO'],aomix.inputs[7]);l.new(aomix.outputs[2],bs.inputs['Base Color'])
    # Cracks + grain bump.
    stretch=node('ShaderNodeVectorMath');stretch.operation='MULTIPLY';stretch.inputs[1].default_value=(1,1,.3);l.new(tc.outputs['Object'],stretch.inputs[0])
    vor=node('ShaderNodeTexVoronoi',Scale=.32,Randomness=.9);vor.feature='DISTANCE_TO_EDGE';l.new(stretch.outputs[0],vor.inputs['Vector'])
    crack=node('ShaderNodeMapRange',**{'From Min':0,'From Max':.025,'To Min':.55,'To Max':1});crack.clamp=True;l.new(vor.outputs['Distance'],crack.inputs['Value'])
    grain=node('ShaderNodeTexNoise',Scale=2.2,Detail=8);l.new(tc.outputs['Object'],grain.inputs['Vector'])
    h=n.new('ShaderNodeMath');h.operation='MULTIPLY_ADD';h.inputs[1].default_value=.5;l.new(grain.outputs['Fac'],h.inputs[0]);l.new(crack.outputs['Result'],h.inputs[2])
    bump=node('ShaderNodeBump',Strength=.45,Distance=.25);l.new(h.outputs[0],bump.inputs['Height']);l.new(bump.outputs[0],bs.inputs['Normal'])
    return m

def pillar(name,cx,cy,rx,ry,h,seed,lean=(0,0),taper=.30,cap=.18,flare=.35,talus=False):
    """Closed karst pillar: footprint radii rx/ry at the base, height h (m)."""
    rng=random.Random(seed);n=150 if not talus else 120
    rings=max(18,int(h/(.55 if not talus else .8)))
    bands=[0.0]
    while bands[-1]<h:bands.append(bands[-1]+rng.uniform(2.2,6.5))
    offs=[rng.uniform(-.10,.06) for _ in bands]
    shifts=[(rng.uniform(-.05,.05)*rx,rng.uniform(-.05,.05)*ry) for _ in bands]
    fiss=[(rng.uniform(0,math.tau),rng.uniform(.03,.08),rng.uniform(.07,.18),rng.uniform(0,h*.4),rng.uniform(h*.6,h*1.1)) for _ in range(rng.randint(5,9))]
    off=Vector((rng.uniform(-50,50),rng.uniform(-50,50),rng.uniform(-50,50)))
    def strata(z):
        for b in range(len(bands)-1):
            if z<bands[b+1]:
                k=smooth(bands[b+1]-.45,bands[b+1],z);return offs[b]*(1-k)+offs[b+1]*k
        return offs[-1]
    def radius(a,z,t):
        if talus:
            base=(1-t)**.8+.02
        else:
            base=(1-taper*t**1.4)+flare*math.exp(-t*h/max(2.5,h*.07))
        f=base+strata(z)*(0 if talus else 1)
        for fa,w,depth,z0,z1 in fiss:
            d=(a-fa+math.pi)%math.tau-math.pi
            f-=depth*math.exp(-(d/w)**2)*smooth(z0,z0+3,z)*(1-smooth(z1-3,z1,z))
        p=Vector((math.cos(a)*rx,math.sin(a)*ry,z))
        f+=(.16 if talus else .07)*noise.fractal(p*(.09 if talus else .06)+off,1,2,4)+.045*(noise.cell(p*.28+off)-.5)
        return max(f,.08)
    def band_shift(z):
        for b in range(len(bands)-1):
            if z<bands[b+1]:
                k=smooth(bands[b+1]-.6,bands[b+1],z);return [shifts[b][i]*(1-k)+shifts[b+1][i]*k for i in (0,1)]
        return shifts[-1]
    def centre(t):
        sh=(0,0) if talus else band_shift(h*t)
        return (cx+lean[0]*t*t+sh[0],cy+lean[1]*t*t+sh[1])
    verts=[]
    body=rings if talus else int(rings*(1-cap*min(rx,ry)/h))
    for j in range(body+1):
        t=j/rings;z=h*t;c=centre(t)
        for i in range(n):
            a=i*math.tau/n;f=radius(a,z,t);verts.append((c[0]+rx*f*math.cos(a),c[1]+ry*f*math.sin(a),z))
    if not talus:  # rounded, lumpy cap: rings shrink toward the summit
        zt=h*body/rings;capn=8;lump=min(.6,(h-zt)*.25);prev=[zt]*n;gap=(h-zt)/(capn*20)
        for k in range(1,capn+1):
            u=k/(capn+1);t=zt/h;c=centre(t)
            for i in range(n):
                a=i*math.tau/n;f=radius(a,zt,t)*math.cos(u*math.pi/2)**.7
                z=zt+(h-zt)*math.sin(u*math.pi/2)+lump*noise.noise(Vector((math.cos(a),math.sin(a),u))*2+off)
                # Each column must keep rising and stay under the summit vertex, or the cap folds inward.
                z=min(max(z,prev[i]+gap),h-(capn-k)*gap);prev[i]=z
                verts.append((c[0]+rx*f*math.cos(a),c[1]+ry*f*math.sin(a),z))
    rows=len(verts)//n
    faces=[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(rows-1) for i in range(n)]
    faces.append(tuple(reversed(range(n))))
    c=centre(1);top=len(verts);verts.append((c[0],c[1],h+(0 if talus else .3)))
    faces+=[((rows-1)*n+i,(rows-1)*n+(i+1)%n,top) for i in range(n)]
    d=bpy.data.meshes.new(name+'_Mesh');d.from_pydata(verts,[],faces);d.update();d.shade_smooth()
    o=bpy.data.objects.new(name,d);assets.objects.link(o);o.parent=root;d.materials.append(MAT)
    o.modifiers.new('Weld_Seams','WELD').merge_threshold=.01
    return o

def peak():
    pillar('Main_Stone_Pillar',0,0,11,9.5,68,17,lean=(1.5,-.8))
    pillar('Satellite_West',-12,3,6,5.5,44,39,lean=(-1.2,.4))
    pillar('Satellite_East',10.5,6,5.5,5,34,24,lean=(.8,.6))
    pillar('Satellite_Front',4,-9.5,4.2,4,22,51)
    pillar('Satellite_Rear_Small',-5,10,3.6,3.4,15,63)
    pillar('Talus_Foot',0,0,23,19,10,73,talus=True)

def ridge():
    # A low connecting massif with pillars rising out of it reads as one ridge, not a row of jars.
    pillar('Ridge_Spine',0,1,34,10,22,54,taper=.4,cap=.35)
    for idx,(x,y,rx,ry,h) in enumerate([(-24,1,8,7,33),(-12,3,7,6.5,40),(-1,2,9.5,8.5,49),(10,-1,7,6.5,42),(21,0,8,7,37),(31,3,5.5,5,28),(-33,-2,5,4.5,22),(5,-7,4.5,4,26),(-17,-6,4,4,20)]):
        r=random.Random(idx)
        pillar('Ridge_Pillar_%02d'%idx,x,y,rx,ry,h,62+idx*11,lean=(r.uniform(-1.2,1.2),r.uniform(-.6,.6)))
    pillar('Ridge_Talus_Foot',0,0,44,17,12,55,talus=True)

BUILDERS={'CloudpiercerPeak':peak,'MountainRidge':ridge}

def bounds(objects):
    dg=bpy.context.evaluated_depsgraph_get()
    pts=[e.matrix_world@v.co for o in objects for e in [o.evaluated_get(dg)] for v in e.data.vertices]
    return Vector([min(p[i] for p in pts) for i in range(3)]),Vector([max(p[i] for p in pts) for i in range(3)])

args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
PREVIEW='preview' in args
ids=[a for a in args if a in BUILDERS] or list(BUILDERS)
for aid in ids:
    out=ROOT/'Models'/aid/'v002';refs=ROOT/'ArtLibrary/Turnarounds'/f'{aid}_v002'
    out.mkdir(parents=True,exist_ok=True);refs.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;bpy.context.preferences.filepaths.save_version=0
    scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    assets=bpy.data.collections.new('01_Editable_Asset');scene.collection.children.link(assets)
    root=bpy.data.objects.new(aid+'_ROOT',None);assets.objects.link(root);root['stage']=DETAILS[aid]
    MAT=rock_material()
    BUILDERS[aid]();bpy.context.view_layer.update()
    objects=[o for o in assets.objects if o.type=='MESH'];lo,hi=bounds(objects)
    shift=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
    for o in objects:o.location-=shift
    bpy.context.view_layer.update();lo,hi=bounds(objects);centre=(lo+hi)/2;extent=hi-lo
    studio=bpy.data.collections.new('90_Studio_Not_Exported');scene.collection.children.link(studio)
    def studio_obj(name,data):
        o=bpy.data.objects.new(name,data);studio.objects.link(o);return o
    cam=studio_obj('Reference_Camera',bpy.data.cameras.new('Reference_Camera'));scene.camera=cam;cam.data.type='ORTHO'
    cam.data.clip_start=.01;cam.data.clip_end=1000;cam.data.ortho_scale=max(extent.length*1.08,.5)
    ls=max(extent)*.65
    for name,direction,power in [('Key',(-.8,-1.1,1.5),1100),('Fill',(1.2,-.4,.9),500),('Rim',(.2,1.1,1.3),900)]:
        d=bpy.data.lights.new(name,'AREA');d.energy=power*ls*ls/7;d.shape='DISK';d.size=ls
        o=studio_obj(name,d);o.location=centre+Vector(direction)*ls;o.rotation_euler=(centre-o.location).to_track_quat('-Z','Y').to_euler()
    scene.world=bpy.data.worlds.new('Neutral_Studio');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.19,.21,.22,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.65
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16;scene.cycles.use_denoising=True
    scene.render.resolution_x=1024;scene.render.resolution_y=1024;scene.render.image_settings.file_format='PNG'
    scene.view_settings.view_transform='AgX';scene.view_settings.exposure=-1.1;scene.frame_set(1)
    def position(direction):
        cam.location=centre+Vector(direction).normalized()*cam.data.ortho_scale*2.3
        cam.rotation_euler=(centre-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
    views=VIEWS[4:5] if PREVIEW else VIEWS
    if not PREVIEW:
        position((1,-1,.65));bpy.ops.object.select_all(action='DESELECT')
        for o in [root]+objects:o.select_set(True)
        bpy.context.view_layer.objects.active=root
        bpy.ops.export_scene.fbx(filepath=str(out/(aid+'_v002.fbx')),use_selection=True,object_types={'MESH','EMPTY'},use_mesh_modifiers=True,add_leaf_bones=False,axis_forward='-Z',axis_up='Y',apply_unit_scale=True,bake_anim=False)
        bpy.ops.wm.save_as_mainfile(filepath=str(out/(aid+'_v002.blend')))
        tris=sum(len(p.vertices)-2 for o in objects for p in o.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.polygons)
        info={'asset':aid,'version':'v002','replaces':'v001 lathed sine-wave massif','name_zh':NAMES[aid],'stage':'editable_landscape_prototype','description':DETAILS[aid],'units':'meters','front':'-Y','dimensions_m':list(extent),'mesh_objects':len(objects),'triangles':tris,'bounds_method':'evaluated mesh vertices','modeling_method':'procedural karst pillars: strata ledges, fissures, cell-noise faces, rounded caps; moss/strata from shader (normal + object Z)','animation':'static','uv_baked':False,'collision':False,'lod':False,'unreal_import_verified':False}
        (out/'model_info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2))
    records=[]
    for name,direction in views:
        position(direction);dg=bpy.context.evaluated_depsgraph_get()
        projected=[world_to_camera_view(scene,cam,e.matrix_world@Vector(p)) for o in objects for e in [o.evaluated_get(dg)] for p in e.bound_box]
        assert all(.005<p.x<.995 and .005<p.y<.995 and p.z>0 for p in projected),(aid,name,'cropped')
        scene.render.filepath=str(refs/(name+'.png'));bpy.ops.render.render(write_still=True)
        records.append({'file':name+'.png','direction':direction,'camera_location':list(cam.location),'projection':'orthographic','framing_checked':True})
        print('VIEW_COMPLETE',aid,name,flush=True)
    if not PREVIEW:
        (refs/'views.json').write_text(json.dumps({'asset':aid,'source':str((out/(aid+'_v002.blend')).relative_to(ROOT)),'same_geometry':True,'views':records},indent=2))
    print('ASSET_COMPLETE',aid,list(extent),flush=True)
