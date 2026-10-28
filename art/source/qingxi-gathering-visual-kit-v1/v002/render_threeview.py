"""Stage 1 check: front / side / top orthographic views of every asset state + dimension and material notes.
blender --background --python-exit-code 1 --python render_threeview.py [-- AssetKey ...]
Writes only to art/references/qingxi-gathering-visual-kit-v1/threeview (overwrites; these are review renders).
"""
import bpy,sys,json
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import qx_kit as K
REPO=Path(__file__).resolve().parents[4];OUT=REPO/'art/references/qingxi-gathering-visual-kit-v1/threeview'
VIEWS=[('front',(0,-1,0)),('side',(1,0,0)),('top',(0,0,1))]

def studio(s,centre,ext):
    coll=bpy.data.collections.new('90_Studio_Not_Exported');s.collection.children.link(coll)
    cam=bpy.data.objects.new('Cam',bpy.data.cameras.new('Cam'));coll.objects.link(cam);s.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=max(ext)*1.25;cam.data.clip_end=500
    ls=max(ext)*.8
    for name,dr,p in [('Key',(-.8,-1.1,1.5),1100),('Fill',(1.2,-.4,.9),600),('Rim',(.2,1.1,1.3),900)]:
        d=bpy.data.lights.new(name,'AREA');d.energy=p*ls*ls/7;d.shape='DISK';d.size=ls;o=bpy.data.objects.new(name,d);coll.objects.link(o)
        o.location=centre+Vector(dr)*ls*1.6;o.rotation_euler=(centre-o.location).to_track_quat('-Z','Y').to_euler()
    s.world=bpy.data.worlds.new('Neutral');s.world.use_nodes=True;bg=s.world.node_tree.nodes['Background'];bg.inputs[0].default_value=(.19,.21,.22,1);bg.inputs[1].default_value=.65
    s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=32;s.cycles.use_denoising=True
    s.render.resolution_x=s.render.resolution_y=800;s.view_settings.view_transform='AgX';s.view_settings.exposure=-.6;s.render.image_settings.file_format='PNG'
    return cam

def main(keys):
    OUT.mkdir(parents=True,exist_ok=True);report={}
    for aid,st in K.STATES:
        key=K.state_key(aid,st)
        if keys and key not in keys:continue
        bpy.ops.wm.read_factory_settings(use_empty=True);K.M.clear();s=bpy.context.scene
        root,objs=K.build_state(aid,st,s.collection);bpy.context.view_layer.update();info=K.stats(objs)
        lo,hi=Vector(info['bounds_min_m']),Vector(info['bounds_max_m']);c=(lo+hi)/2;cam=studio(s,c,hi-lo)
        for name,dr in VIEWS:
            cam.location=c+Vector(dr)*max(hi-lo)*4;cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler()
            s.render.filepath=str(OUT/f'{key}_{name}.png');bpy.ops.render.render(write_still=True)
        info.update(name_zh=K.NAMES[aid],state=st,state_zh=K.STATE_ZH[st],design=K.DESIGN[aid],material_direction=K.MATERIAL_DIRECTION[aid]);report[key]=info
        print('THREEVIEW',key,info['dimensions_m'],info['triangles'],flush=True)
    p=OUT/'threeview_stats.json';old=json.loads(p.read_text('utf-8')) if p.exists() else {}
    old.update(report);p.write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
