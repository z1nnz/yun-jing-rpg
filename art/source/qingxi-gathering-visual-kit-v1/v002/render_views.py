"""Delivery views of the exported game models (GLB re-import), v002.
blender -b --python-exit-code 1 --python render_views.py -- [key ...]        (no keys = all nine states)
Per state, from exports/<Asset>/v002/<key>.glb re-imported into an empty scene:
  * re-import check: mesh / material / texture count, dimensions against <key>_model_info.json, origin;
  * ten 1024 x 1024 views of the same model (front, four diagonals, right, back, left, top, high front);
  * orthographic front / right / top at a shared scale for the three-view sheet (make_sheets.py adds sizes);
  * eye-height (1.6 m) shots on a ground plane at near and far distances.
Writes art/references/qingxi-gathering-visual-kit-v1/views_v002/<key>/ with views.json and validation.json.
Camera directions use Blender axes: the model front faces -Y; 'right' looks from +X.
"""
import bpy,sys,json,math,os,hashlib
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import qx_kit as K
from render_review import look,neutral,world,game_light
REPO=Path(__file__).resolve().parents[4];EXP=REPO/'art/exports/qingxi-gathering-visual-kit-v1';OUT=REPO/'art/references/qingxi-gathering-visual-kit-v1/views_v002';VER='v002'
TEN=[('01_front',0,12),('02_front_right',45,12),('03_right',90,12),('04_back_right',135,12),('05_back',180,12),
     ('06_back_left',225,12),('07_left',270,12),('08_front_left',315,12),('09_top',0,90),('10_high_front',0,48)]
EYE={'QX_GatheringLandmark':[('eye_40m',(6,-40)),('eye_15m',(2.5,-15)),('eye_6m',(1.2,-6))]}
EYE_DEFAULT=[('eye_8m',(2.0,-8)),('eye_3m',(.9,-3)),('eye_1m2',(.35,-1.2))]
SAMPLES=int(os.environ.get('QX_SAMPLES','32'))

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def adir(az,el):
    a,e=math.radians(az),math.radians(el)
    return Vector((math.sin(a)*math.cos(e),-math.cos(a)*math.cos(e),math.sin(e))) if el<89.9 else Vector((0,-1e-4,1)).normalized()

def render(s,path,w,h):
    s.render.resolution_x,s.render.resolution_y=w,h;s.render.filepath=str(path);bpy.ops.render.render(write_still=True)

def main(keys):
    for aid,st in K.STATES:
        key=K.state_key(aid,st)
        if keys and key not in keys:continue
        d=EXP/aid/VER;info=json.loads((d/f'{key}_model_info.json').read_text('utf-8'));out=OUT/key;out.mkdir(parents=True,exist_ok=True)
        bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene
        bpy.ops.import_scene.gltf(filepath=str(d/f'{key}.glb'))
        meshes=[o for o in s.objects if o.type=='MESH'];bpy.context.view_layer.update()
        pts=[o.matrix_world@v.co for o in meshes for v in o.data.vertices]
        lo=Vector([min(p[i] for p in pts) for i in range(3)]);hi=Vector([max(p[i] for p in pts) for i in range(3)]);ext=hi-lo;c=(lo+hi)/2
        mats={m for o in meshes for m in o.data.materials if m};imgs={n.image.name for m in mats if m.use_nodes for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image}
        for o in meshes:o.data.calc_loop_triangles()
        tris=sum(len(o.data.loop_triangles) for o in meshes)
        dim_err=max(abs(a-b) for a,b in zip(ext,info['dimensions_m']))
        checks={'glb_imports':bool(meshes),'one_mesh_one_material':len(meshes)==1 and len(mats)==1,'four_textures_embedded':len(imgs)==4,
                'dimensions_match_model_info_1mm':dim_err<.001,'triangles_match_model_info':tris==info['game_triangles'],
                'origin_bottom_centre':abs(lo.z-info['bounds_min_m'][2])<.001 and abs(c.x-(info['bounds_min_m'][0]+info['bounds_max_m'][0])/2)<.001}
        cam=bpy.data.objects.new('Cam',bpy.data.cameras.new('Cam'));s.collection.objects.link(cam);s.camera=cam;cam.data.clip_end=800;cam.data.sensor_fit='VERTICAL'
        s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=SAMPLES;s.cycles.use_denoising=True;s.view_settings.view_transform='AgX';s.render.image_settings.file_format='PNG'
        studio=neutral(s,c,ext);world(s,(.19,.21,.22),.65);s.view_settings.exposure=-.6
        r=ext.length/2;cam.data.type='PERSP';cam.data.lens=50;fov=2*math.atan(cam.data.sensor_height/2/cam.data.lens);dist=r/math.sin(fov/2)*1.04
        views=[]
        for name,az,el in TEN:
            loc=c+adir(az,el)*dist;look(cam,c,loc);p=out/f'{name}.png';render(s,p,1024,1024)
            views.append({'file':p.name,'azimuth_deg':az,'elevation_deg':el,'camera_m':[round(x,3) for x in loc],'target_m':[round(x,3) for x in c],'lens_mm':50,'projection':'perspective'})
        # orthographic three-view at one shared scale (sheet adds the sizes)
        cam.data.type='ORTHO';cam.data.ortho_scale=max(ext)*1.12;ortho=[]
        for name,dr in [('ortho_front',(0,-1,0)),('ortho_right',(1,0,0)),('ortho_top',(0,-1e-4,1))]:
            look(cam,c,c+Vector(dr).normalized()*max(ext)*4);p=out/f'{name}.png';render(s,p,1024,1024)
            ortho.append({'file':p.name,'direction':list(dr),'ortho_scale_m':round(cam.data.ortho_scale,4)})
        studio.hide_render=True;game_light(s);world(s,(.30,.40,.50),.85);s.view_settings.exposure=-.35
        cam.data.type='PERSP';cam.data.lens=35;eye=[]
        for name,(x,y) in EYE.get(aid,EYE_DEFAULT):
            loc=Vector((x,y,1.6));t=Vector((0,0,min(c.z,1.2)));look(cam,t,loc);p=out/f'{name}.png';render(s,p,1600,1000)
            eye.append({'file':p.name,'camera_m':list(loc),'target_m':[round(v,3) for v in t],'lens_mm':35,'note':'eye height 1.6 m'})
        files=[out/v['file'] for v in views]
        checks['ten_views_1024']=all(f.exists() for f in files) and len(files)==10
        valid={'key':key,'source_glb':str((d/f'{key}.glb').relative_to(REPO)).replace('\\','/'),'glb_sha256':sha(d/f'{key}.glb'),
               'checks':checks,'all_passed':all(checks.values()),
               'measured':{'dimensions_m':[round(x,4) for x in ext],'bounds_min_m':[round(x,4) for x in lo],'triangles':tris,'materials':len(mats),'textures':sorted(imgs)},
               'model_info':{'dimensions_m':info['dimensions_m'],'game_triangles':info['game_triangles']},
               'not_checked':['Unreal / Godot import','collision','LOD','navigation','in-engine lighting']}
        (out/'validation.json').write_text(json.dumps(valid,ensure_ascii=False,indent=2),encoding='utf-8')
        (out/'views.json').write_text(json.dumps({'key':key,'name_zh':K.NAMES[aid],'state_zh':K.STATE_ZH[st],'front_axis':'-Y','right_view_from':'+X',
            'ten_views':views,'orthographic':ortho,'eye_height':eye,'render':{'engine':'Cycles CPU','samples':SAMPLES,'denoise':True}},ensure_ascii=False,indent=2),encoding='utf-8')
        print('VIEWS',key,'passed' if valid['all_passed'] else 'FAILED',{k:v for k,v in checks.items() if not v},flush=True)

if __name__=='__main__':main(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
