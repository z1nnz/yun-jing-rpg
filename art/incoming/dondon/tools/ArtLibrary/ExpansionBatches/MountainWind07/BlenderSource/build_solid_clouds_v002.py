"""WindFog v002: solid mesh clouds replace v001 volumes (volume noise flickered between frames).
Clouds are metaball puffs converted to editable meshes; they drift by looping object keyframes, so
the shape never resamples per frame. v001 stays untouched. Blender CLI: blender -b -P this.py
"""
import bpy,math,json,sys,random,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
_argv=sys.argv;sys.argv=[a for a in sys.argv if a!='--']+['--','none']  # import helpers without running v001 builds
try:import build_scenes07 as base
finally:sys.argv=_argv  # callers that import solid_cloud keep their own arguments
ROOT=base.ROOT

def cloud_material():
    m=bpy.data.materials.get('Solid_Cloud')
    if m:return m
    m=bpy.data.materials.new('Solid_Cloud');m.use_nodes=True;m.diffuse_color=(.93,.96,.97,1)
    nodes=m.node_tree.nodes;bs=next((n for n in nodes if n.type=='BSDF_PRINCIPLED'),None)
    if bs is None:  # files opened with non-factory settings may start materials without the default BSDF
        nodes.clear();out=nodes.new('ShaderNodeOutputMaterial');bs=nodes.new('ShaderNodeBsdfPrincipled');m.node_tree.links.new(bs.outputs[0],out.inputs['Surface'])
    bs.inputs['Base Color'].default_value=(.90,.94,.96,1);bs.inputs['Roughness'].default_value=1
    bs.inputs['Subsurface Weight'].default_value=.25;bs.inputs['Subsurface Radius'].default_value=(1,1,1);bs.inputs['Subsurface Scale'].default_value=.6
    # Soft self-light keeps the underside pale instead of turning into a gray rock.
    bs.inputs['Emission Color'].default_value=(.80,.88,.92,1);bs.inputs['Emission Strength'].default_value=.18
    return m

def solid_cloud(name,location,size,seed=0,phase=0,puffs=14,drift=.6,collection=None):
    """Flat-bottomed cumulus of overlapping puffs, sized (x,y,z) in meters."""
    rnd=random.Random(seed);sx,sy,sz=size
    mb=bpy.data.metaballs.new(name+'_Puffs');mb.resolution=max(.12,min(sx,sy)/28);mb.render_resolution=mb.resolution;mb.threshold=.6
    for i in range(puffs):  # base layer: puffs scattered in an ellipse, larger toward the center
        a=rnd.uniform(0,math.tau);d=math.sqrt(rnd.random())
        x=math.cos(a)*d*sx*.38;y=math.sin(a)*d*sy*.30
        r=min(sx,sy)*(.20+.16*(1-d))*rnd.uniform(.8,1.2)
        e=mb.elements.new();e.co=(x,y,r*.3);e.radius=r;e.stiffness=2
    for i in range(max(3,puffs//2)):  # billowing top lumps, kept inward so edges taper
        x=rnd.uniform(-.26,.26)*sx;y=rnd.uniform(-.14,.14)*sy;k=1-abs(x)/(sx*.3)
        e=mb.elements.new();e.co=(x,y,sz*(.30+.30*k));e.radius=min(sx,sy)*rnd.uniform(.16,.26)*(.7+.5*k);e.stiffness=2
    tmp=bpy.data.objects.new(name+'_Meta',mb);bpy.context.scene.collection.objects.link(tmp);bpy.context.view_layer.update()
    me=bpy.data.meshes.new_from_object(tmp.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(tmp);bpy.data.metaballs.remove(mb)
    zmin=min(v.co.z for v in me.vertices);flat=zmin+sz*.12
    for v in me.vertices:  # squash the base so clouds read as sitting on air, not floating balls
        if v.co.z<flat:v.co.z=flat-(flat-v.co.z)*.25
    zmin=min(v.co.z for v in me.vertices);zmax=max(v.co.z for v in me.vertices)
    for v in me.vertices:v.co.z=(v.co.z-zmin)/(zmax-zmin)*sz-sz/2
    me.name=name+'_Mesh';me.shade_smooth();me.materials.append(cloud_material())
    o=bpy.data.objects.new(name,me);(collection or bpy.context.scene.collection).objects.link(o);o.location=location
    o['cloud_type']='solid cloud mesh; looping object drift'
    base_loc=tuple(location)
    for f in range(1,98,8):  # same 96-frame loop as v001, frame 97 == frame 1
        a=(f-1)/96*math.tau+phase
        o.location=(base_loc[0]+drift*math.sin(a),base_loc[1]+drift*.5*math.cos(a),base_loc[2]+drift*.15*math.sin(2*a))
        o.keyframe_insert('location',frame=f)
    o.location=base_loc;bpy.context.scene.frame_set(1)
    return o

def wind():
    out=ROOT/'Effects/WindFog/v002';out.mkdir(parents=True,exist_ok=True);frames=out/'frames';frames.mkdir(exist_ok=True)
    s=base.fresh('Wind_And_Solid_Cloud_Study');s.cycles.samples=24;s.cycles.volume_bounces=0
    base.load_asset('WindPine')
    for i,(x,y,scale) in enumerate([(-4,-1.8,1.5),(-2,-2.4,1.8),(.4,-1.7,1.6),(2.3,-1.5,1.5),(4,-1,1.4),(-3,1,1.3)]):base.load_asset('WindGrass',(x,y,.01),(scale,scale,scale),i*.7)
    base.load_asset('CloudpiercerPeak',(-15,38,-1),(.5,.5,.5),.5)
    base.load_asset('MountainRidge',(18,65,-2),(.7,.7,.7),.3)
    base.surface('Mossy_Ground',500,-.02,(.10,.15,.075))
    solid_cloud('Cloud_Low_Left',(-9,6,2.2),(9,4,2.4),seed=1,drift=.5)
    solid_cloud('Cloud_Low_Right',(6,4,2.6),(8,3.5,2.2),seed=2,phase=2,drift=.5)
    solid_cloud('Cloud_Rear_Ribbon',(10,22,9),(26,8,4.5),seed=3,phase=4,puffs=24,drift=1.2)
    solid_cloud('Cloud_Peak_Collar',(-14,34,16),(16,9,3.5),seed=4,phase=1,drift=.8)
    cam=base.camera('Wind_Closeup',(15,-24,10.5),(0,1,3.5),48)
    s.camera=cam
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'WindFog_v002.blend'))
    base.render(s,cam,out/'01_wind_fog_preview.png',1200,800)
    if os.environ.get('PREVIEW_ONLY'):return
    s.render.resolution_x=720;s.render.resolution_y=480;s.cycles.samples=16
    for f in range(1,97,2):
        s.frame_set(f);s.render.filepath=str(frames/f'{f:04d}.png');bpy.ops.render.render(write_still=True)
        print('WIND_FRAME',f,flush=True)
    clouds=[o.name for o in s.objects if o.get('cloud_type')]
    (out/'effect_info.json').write_text(json.dumps({'effect':'WindFog','version':'v002','replaces':'v001 volumetric fog (per-frame volume noise flicker)','blender_fps':24,'frame_range':[1,96],'loop_seconds':4,'preview_fps':12,'preview_frames':48,'wind_method':'height-weighted shape keys; roots fixed','cloud_method':'solid metaball-derived meshes, looping object-location drift','solid_clouds':clouds,'rigid_body_or_fluid_simulation':False,'engine_effect_exported':False,'editable_parameters':['Wind_Main and Wind_Gust shape-key amplitudes','Cloud object location keyframes','Solid_Cloud material','Cloud mesh vertices (editable)']},indent=2))
    print('SOLID_CLOUD_EFFECT_COMPLETE',flush=True)

if __name__=='__main__':wind()
