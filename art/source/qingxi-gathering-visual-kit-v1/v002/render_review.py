"""Art review renders for one or more asset states (source procedural materials, Cycles).
blender --background --python-exit-code 1 --python render_review.py -- AssetKey [AssetKey ...]
Per state: neutral front / right / top orthographic, game-light 3/4 perspective on a ground plane,
close-up of the focal area, and a 12 m eye-height distance shot. Writes to
art/references/qingxi-gathering-visual-kit-v1/review/<pass>/ (pass name via QX_PASS env, default 'current').
QX_QUICK=1: GPU, front + 3/4 + close-up only, fewer samples (iteration renders, not for delivery).
"""
import bpy,sys,json,os,math
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import qx_kit as K
REPO=Path(__file__).resolve().parents[4];OUT=REPO/'art/references/qingxi-gathering-visual-kit-v1/review'/os.environ.get('QX_PASS','current')
FOCUS={'QX_EmbeddedOre_Yumai':(Vector((0,0,.45)),1.25),'QX_GatheringLandmark':(Vector((1.22,-.1,2.75)),1.7),'QX_SpiritHerb_Chilu':(Vector((0,-.02,.27)),.6),'QX_SpiritHerb_Qinglan':(Vector((0,-.05,.36)),.45),'QX_CreekSteppingPlank':(Vector((.30,-.22,.45)),.55),'QX_WaterReeds':(Vector((0,0,1.35)),.6)}
FAR={'QX_GatheringLandmark':('far40m',Vector((6,-40,1.6)))}

QUICK=os.environ.get('QX_QUICK')=='1'

def use_gpu(s):
    prefs=bpy.context.preferences.addons['cycles'].preferences
    for kind in ('OPTIX','CUDA'):
        try:
            prefs.compute_device_type=kind;prefs.get_devices()
            if any(d.type==kind for d in prefs.devices):break
        except TypeError:continue
    for d in prefs.devices:d.use=d.type!='CPU'
    s.cycles.device='GPU'

def look(cam,target,loc):cam.location=loc;cam.rotation_euler=(Vector(target)-Vector(loc)).to_track_quat('-Z','Y').to_euler()

def neutral(s,centre,ext):
    coll=bpy.data.collections.new('90_Studio_Not_Exported');s.collection.children.link(coll);ls=max(ext)*.8;lights=[]
    for name,dr,p in [('Key',(-.8,-1.1,1.5),1100),('Fill',(1.2,-.4,.9),600),('Rim',(.2,1.1,1.3),900)]:
        d=bpy.data.lights.new(name,'AREA');d.energy=p*ls*ls/7;d.shape='DISK';d.size=ls;o=bpy.data.objects.new(name,d);coll.objects.link(o)
        o.location=centre+Vector(dr)*ls*1.6;o.rotation_euler=(centre-o.location).to_track_quat('-Z','Y').to_euler();lights.append(o)
    return coll

def world(s,col,strength):
    w=bpy.data.worlds.get('QX_World') or bpy.data.worlds.new('QX_World');w.use_nodes=True;bg=w.node_tree.nodes['Background'];bg.inputs[0].default_value=(*col,1);bg.inputs[1].default_value=strength;s.world=w

def game_light(s):
    coll=bpy.data.collections.new('91_GameLight_Not_Exported');s.collection.children.link(coll)
    sun=bpy.data.lights.new('Sun','SUN');sun.energy=3.6;sun.angle=math.radians(3);sun.color=(1,.93,.84);o=bpy.data.objects.new('Sun',sun);coll.objects.link(o);o.rotation_euler=(math.radians(52),0,math.radians(-38))
    me=bpy.data.meshes.new('Ground');me.from_pydata([(-60,-60,0),(60,-60,0),(60,60,0),(-60,60,0)],[],[(0,1,2,3)])
    g=bpy.data.objects.new('Ground_Plane',me);coll.objects.link(g);m=bpy.data.materials.new('Review_Ground');m.use_nodes=True;bs=m.node_tree.nodes['Principled BSDF']
    nt=m.node_tree;n=nt.nodes.new('ShaderNodeTexNoise');n.inputs['Scale'].default_value=1.5;r=nt.nodes.new('ShaderNodeValToRGB');r.color_ramp.elements[0].color=(.045,.055,.03,1);r.color_ramp.elements[1].color=(.075,.08,.045,1)
    nt.links.new(n.outputs['Fac'],r.inputs[0]);nt.links.new(r.outputs['Color'],bs.inputs['Base Color']);bs.inputs['Roughness'].default_value=.95;me.materials.append(m)
    return coll

def main(keys):
    OUT.mkdir(parents=True,exist_ok=True);report={}
    for aid,st in K.STATES:
        key=K.state_key(aid,st)
        if keys and key not in keys:continue
        bpy.ops.wm.read_factory_settings(use_empty=True);K.M.clear();s=bpy.context.scene
        root,objs=K.build_state(aid,st,s.collection);bpy.context.view_layer.update()
        dg=bpy.context.evaluated_depsgraph_get();info=K.stats(objs)
        tri=lambda o:len(o.evaluated_get(dg).data.loop_triangles)
        info['triangles_evaluated']=sum(tri(o) for o in objs if o.get('qx_role')!='bake_source_high_poly')
        info['triangles_high_poly_bake_source']=sum(tri(o) for o in objs if o.get('qx_role')=='bake_source_high_poly')
        lo,hi=Vector(info['bounds_min_m']),Vector(info['bounds_max_m']);c=(lo+hi)/2;ext=hi-lo
        cam=bpy.data.objects.new('Cam',bpy.data.cameras.new('Cam'));s.collection.objects.link(cam);s.camera=cam;cam.data.clip_end=500
        s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.use_denoising=True;s.view_settings.view_transform='AgX';s.render.image_settings.file_format='PNG'
        if QUICK:use_gpu(s)
        # neutral orthographic three-view
        studio=neutral(s,c,ext);world(s,(.19,.21,.22),.65);s.view_settings.exposure=-.6;s.cycles.samples=40;s.render.resolution_x=s.render.resolution_y=900
        cam.data.type='ORTHO';cam.data.ortho_scale=max(ext)*1.15
        for name,dr in [('front',(0,-1,0))] if QUICK else [('front',(0,-1,0)),('right',(1,0,0)),('top',(0,0,1))]:
            look(cam,c,c+Vector(dr)*max(ext)*4);s.render.filepath=str(OUT/f'{key}_{name}.png');bpy.ops.render.render(write_still=True)
        studio.hide_render=True
        # game light: sun + sky fill on a ground plane
        game_light(s);world(s,(.30,.40,.50),.85);s.view_settings.exposure=-.35;s.cycles.samples=32 if QUICK else 96
        s.render.resolution_x,s.render.resolution_y=1600,1000;cam.data.type='PERSP';cam.data.lens=50
        f,fr=FOCUS.get(aid,(c,max(ext)*.35))
        if os.environ.get('QX_FOCUS'):*fv,fr=map(float,os.environ['QX_FOCUS'].split(','));f=Vector(fv)   # x,y,z,distance
        shots=[('beauty34',c,c+Vector((1.0,-1.35,.62)).normalized()*max(ext)*2.0),
               ('beauty_back',c,c+Vector((-1.1,1.2,.7)).normalized()*max(ext)*2.0),
               ('closeup',f,f+Vector((.75,-1.2,.55)).normalized()*fr),
               ('far12m',Vector((0,0,c.z*.8)),Vector((2.0,-12,1.6)))]+([(FAR[aid][0],Vector((0,0,c.z*.8)),FAR[aid][1])] if aid in FAR else [])
        if QUICK:shots=shots[:1]+shots[2:3]
        for name,t,loc in shots:
            look(cam,t,loc);cam.data.lens=50 if name!='closeup' else 60;s.render.filepath=str(OUT/f'{key}_{name}.png');bpy.ops.render.render(write_still=True)
        report[key]=info;print('REVIEW',key,info['dimensions_m'],info['triangles_evaluated'],info['triangles_high_poly_bake_source'],flush=True)
    p=OUT/'review_stats.json';old=json.loads(p.read_text('utf-8')) if p.exists() else {};old.update(report);p.write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
