"""Build mountain sanctuary and a close-up wind/fog demonstration without changing source files."""
import bpy,math,json,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[2]

def fresh(name):
    bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.name=name
    bpy.context.preferences.filepaths.save_version=0;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
    s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=16;s.cycles.use_denoising=True
    s.cycles.max_bounces=5;s.cycles.volume_bounces=1
    s.render.image_settings.file_format='PNG';s.render.resolution_percentage=100;s.view_settings.view_transform='AgX'
    s.frame_start=1;s.frame_end=96;s.render.fps=24;s.frame_set(1)
    s.world=bpy.data.worlds.new('Mountain_Daylight');s.world.use_nodes=True
    s.world.node_tree.nodes['Background'].inputs[0].default_value=(.34,.45,.51,1)
    s.world.node_tree.nodes['Background'].inputs[1].default_value=.65
    d=bpy.data.lights.new('Soft_Morning_Sun','SUN');d.energy=2.2;d.angle=math.radians(18)
    o=bpy.data.objects.new(d.name,d);s.collection.objects.link(o);o.rotation_euler=(.45,-.50,-.4)
    return s

def load_asset(aid,location=(0,0,0),scale=(1,1,1),angle=0):
    path=ROOT/'Models'/aid/'v001'/f'{aid}_v001.blend'
    with bpy.data.libraries.load(str(path),link=False) as (src,dst):dst.collections=['01_Editable_Asset']
    coll=dst.collections[0];bpy.context.scene.collection.children.link(coll);coll.name=aid+'_Placed'
    top=[o for o in coll.all_objects if o.parent is None]
    assert len(top)==1
    top[0].location=location;top[0].scale=scale;top[0].rotation_euler.z=angle
    return coll,top[0]

def load_sect():
    p=PROJECT/'Models/SectLayout/v003/SectLayout_v003.blend'
    with bpy.data.libraries.load(str(p),link=False) as (src,dst):dst.collections=[n for n in src.collections if not n.startswith('90_')]
    group=bpy.data.objects.new('Sect_v003_Placed_On_Summit',None);bpy.context.scene.collection.objects.link(group)
    for c in dst.collections:
        bpy.context.scene.collection.children.link(c)
        for o in c.all_objects:
            if o.parent is None:o.parent=group
    group.location=(0,-9.5,48.35)
    return group

def camera(name,location,target,lens=50,ortho=None):
    d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);bpy.context.scene.collection.objects.link(o)
    o.location=location;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.lens=lens;d.clip_end=2000;d.clip_start=.05
    if ortho:d.type='ORTHO';d.ortho_scale=ortho
    return o

def fog(name,location,size,density=.18,phase=0):
    # A bounded, smoothly faded volume. Texture coordinates drift; no surface geometry pretends to be cloud.
    bpy.ops.mesh.primitive_cube_add(size=1,location=location);o=bpy.context.object;o.name=name;o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.display_type='WIRE';o['effect_type']='animated procedural volume; Blender only'
    m=bpy.data.materials.new(name+'_Volume');m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;n.clear()
    out=n.new('ShaderNodeOutputMaterial');vol=n.new('ShaderNodeVolumePrincipled');vol.inputs['Color'].default_value=(.78,.88,.90,1);vol.inputs['Anisotropy'].default_value=.15
    l.new(vol.outputs['Volume'],out.inputs['Volume'])
    tc=n.new('ShaderNodeTexCoord');distance=n.new('ShaderNodeVectorMath');distance.operation='DISTANCE';distance.inputs[1].default_value=(.5,.5,.5);l.new(tc.outputs['Generated'],distance.inputs[0])
    fade=n.new('ShaderNodeMapRange');fade.inputs['From Min'].default_value=.12;fade.inputs['From Max'].default_value=.50;fade.inputs['To Min'].default_value=1;fade.inputs['To Max'].default_value=0;fade.clamp=True;l.new(distance.outputs['Value'],fade.inputs['Value'])
    drift=n.new('ShaderNodeVectorMath');drift.name='Cloud_Drift';drift.operation='ADD';l.new(tc.outputs['Generated'],drift.inputs[0])
    for f in range(1,98,8):
        a=(f-1)/96*math.tau+phase;drift.inputs[1].default_value=(.27*math.sin(a),.27*math.cos(a),0);drift.inputs[1].keyframe_insert(data_path='default_value',frame=f)
    tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=5.5;tex.inputs['Detail'].default_value=2;l.new(drift.outputs['Vector'],tex.inputs['Vector'])
    remap=n.new('ShaderNodeMapRange');remap.inputs['From Min'].default_value=.33;remap.inputs['From Max'].default_value=.72;remap.inputs['To Min'].default_value=0;remap.inputs['To Max'].default_value=density;remap.clamp=True;l.new(tex.outputs['Fac'],remap.inputs['Value'])
    mul=n.new('ShaderNodeMath');mul.operation='MULTIPLY';l.new(remap.outputs['Result'],mul.inputs[0]);l.new(fade.outputs['Result'],mul.inputs[1]);l.new(mul.outputs[0],vol.inputs['Density'])
    o.data.materials.append(m);return o

def surface(name,size,z,color):
    bpy.ops.mesh.primitive_plane_add(size=size,location=(0,0,z));o=bpy.context.object;o.name=name
    m=bpy.data.materials.new(name+'_Material');m.use_nodes=True;m.diffuse_color=(*color,1)
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=.95;o.data.materials.append(m)
    return o

def render(s,cam,path,w,h):
    s.camera=cam;s.render.resolution_x=w;s.render.resolution_y=h;s.render.filepath=str(path);s.frame_set(1);bpy.ops.render.render(write_still=True)

def mountain():
    out=ROOT/'Models/MountainSanctuary/v001';out.mkdir(parents=True,exist_ok=True);s=fresh('Mountain_Sanctuary');s.view_settings.exposure=.5
    load_asset('SectSummitPlateau');load_sect()
    load_asset('CloudpiercerPeak',(-68,56,0),(1.1,1.1,1.5),-.4)
    load_asset('CloudpiercerPeak',(62,66,0),(.85,1,1.25),.8)
    load_asset('MountainRidge',(0,114,0),(2,1.5,1.45),.1)
    load_asset('LayeredCliff',(-46,-2,0),(1,1.6,1.4),.3)
    for x,y,a in [(-27,-23,.1),(27,-22,2.0),(-27,20,-.6),(27,20,1.7)]:load_asset('WindPine',(x,y,48),(.65,.65,.65),a)
    surface('Valley_Ground',6000,-.15,(.10,.16,.11))
    fog('Cloud_Valley_West',(-38,10,20),(160,120,38),.06)
    fog('Cloud_Valley_East',(58,48,31),(120,110,34),.045,2)
    fog('Cloud_Distant_Saddle',(0,105,60),(210,65,36),.035,4)
    overview=camera('01_Mountain_Overview',(194,-249,182),(0,24,47),45)
    approach=camera('02_Summit_Approach',(76,-117,88),(0,0,51),49)
    top=camera('03_Summit_Top',(0,0,245),(0,0,0),ortho=155)
    s.camera=overview;s.render.resolution_x=1440;s.render.resolution_y=1080
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'MountainSanctuary_v001.blend'))
    render(s,overview,out/'01_mountain_overview.png',1440,1080)
    render(s,approach,out/'02_summit_approach.png',1440,1080)
    render(s,top,out/'03_summit_top.png',1200,1200)
    # FBX is geometry only: deliberately exclude fog containers and studios.
    bpy.ops.object.select_all(action='DESELECT');selected=[]
    for o in s.objects:
        if o.type=='MESH' and not o.get('effect_type'):o.select_set(True);selected.append(o)
    bpy.context.view_layer.objects.active=selected[0]
    bpy.ops.export_scene.fbx(filepath=str(out/'MountainSanctuary_v001.fbx'),use_selection=True,object_types={'MESH'},bake_anim=False,add_leaf_bones=False,axis_forward='-Z',axis_up='Y')
    (out/'scene_info.json').write_text(json.dumps({'scene':'MountainSanctuary','sect_source':'SectLayout/v003','assets':['SectSummitPlateau','CloudpiercerPeak','MountainRidge','LayeredCliff','WindPine'],'summit_z_m':48,'previews':3,'fog_volumes':3,'fbx':'static geometry only; no fog or wind animation','limitations':['No playable ascent route','No terrain collision, LOD, UV baking or engine verification','Overlapping terrain masses are editable scenery prototypes']},indent=2))
    print('MOUNTAIN_SCENE_COMPLETE',flush=True)

def wind():
    out=ROOT/'Effects/WindFog/v001';out.mkdir(parents=True,exist_ok=True);frames=out/'frames';frames.mkdir(exist_ok=True)
    s=fresh('Wind_And_Cloud_Study');s.cycles.samples=12
    load_asset('WindPine')
    for i,(x,y,scale) in enumerate([(-4,-1.8,1.5),(-2,-2.4,1.8),(.4,-1.7,1.6),(2.3,-1.5,1.5),(4,-1,1.4),(-3,1,1.3)]):load_asset('WindGrass',(x,y,.01),(scale,scale,scale),i*.7)
    load_asset('CloudpiercerPeak',(-15,38,-1),(.5,.5,.5),.5)
    load_asset('MountainRidge',(18,65,-2),(.7,.7,.7),.3)
    surface('Mossy_Ground',500,-.02,(.10,.15,.075))
    fog('Low_Drifting_Mist',(0,2,1.5),(25,14,3.6),.32)
    fog('Rear_Cloud_Ribbon',(1,15,4),(52,17,8),.15,2)
    cam=camera('Wind_Closeup',(15,-24,10.5),(0,1,3.5),48)
    s.camera=cam;s.render.resolution_x=960;s.render.resolution_y=640
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'WindFog_v001.blend'))
    render(s,cam,out/'01_wind_fog_preview.png',1200,800)
    s.render.resolution_x=720;s.render.resolution_y=480;s.cycles.samples=8;s.render.fps=24
    for f in range(1,97,2):
        s.frame_set(f);s.render.filepath=str(frames/f'{f:04d}.png');bpy.ops.render.render(write_still=True)
        print('WIND_FRAME',f,flush=True)
    (out/'effect_info.json').write_text(json.dumps({'effect':'WindFog','blender_fps':24,'frame_range':[1,96],'loop_seconds':4,'preview_fps':12,'preview_frames':48,'wind_method':'height-weighted shape keys; roots fixed','cloud_method':'bounded procedural volumes, circular texture-coordinate drift','rigid_body_or_fluid_simulation':False,'engine_effect_exported':False,'editable_parameters':['Wind_Main and Wind_Gust shape-key amplitudes','Cloud_Drift keyframes','Volume density remap','Fog object dimensions']},indent=2))
    print('WIND_EFFECT_COMPLETE',flush=True)

mode=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'all'
if mode in ('mountain','all'):mountain()
if mode in ('wind','all'):wind()
