"""Non-character v002 only: material render, door hinges, and immutable v001 sources.
Usage: blender --background --python-exit-code 1 --python this.py -- [asset IDs]
"""
import bpy,json,math,hashlib,sys,importlib.util
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
BATCH=Path(__file__).resolve().parents[1]
ALLOWED=['QMountainRabbit','QMountainBoar','QSpiritStone','QPillBottle','QQiManual','QAptitudeCrystal','QCaveEntrance','QCaveFloor','QCaveWall','QCaveDoor']
VERSIONS={a:('v003' if a=='QCaveEntrance' else 'v002') for a in ALLOWED}
SCENE_VERSION='v002'
VIEWS=[('01_front',(0,-1,0)),('02_right',(1,0,0)),('03_rear',(0,1,0)),('04_left',(-1,0,0)),('05_front_right',(1,-1,.45)),('06_rear_right',(1,1,.45)),('07_rear_left',(-1,1,.45)),('08_front_left',(-1,-1,.45)),('09_top',(0,0,1)),('10_high_front',(0,-1,1))]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bounds(obs):
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();pts=[]
    for o in obs:
        e=o.evaluated_get(dg);pts.extend(e.matrix_world@v.co for v in e.data.vertices)
    return Vector([min(p[i] for p in pts) for i in range(3)]),Vector([max(p[i] for p in pts) for i in range(3)])
def position(cam,center,scale,dr):
    cam.location=center+Vector(dr).normalized()*scale*2.5;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
def lighting(obs):
    s=bpy.context.scene
    for o in list(s.objects):
        if o.type in ('LIGHT','CAMERA'):bpy.data.objects.remove(o,do_unlink=True)
    lo,hi=bounds(obs);center=(lo+hi)/2;extent=hi-lo;scale=extent.length*1.18
    d=bpy.data.cameras.new('PreviewCamera');cam=bpy.data.objects.new('PreviewCamera',d);s.collection.objects.link(cam);s.camera=cam;d.type='ORTHO';d.ortho_scale=scale;d.clip_start=.001;d.clip_end=1000
    ls=max(extent)*.85
    for name,dr,power in [('Key',(-1.0,-1.5,1.8),1100),('Fill',(1.3,-.6,.8),650),('Rim',(.5,1.2,1.4),900)]:
        ld=bpy.data.lights.new(name,'AREA');ld.energy=power*ls*ls/7;ld.shape='DISK';ld.size=ls
        ob=bpy.data.objects.new(name,ld);s.collection.objects.link(ob);ob.location=center+Vector(dr)*ls;ob.rotation_euler=(center-ob.location).to_track_quat('-Z','Y').to_euler()
    s.world=bpy.data.worlds.new('Neutral_world');s.world.use_nodes=True
    bg=s.world.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(.24,.27,.26,1);bg.inputs['Strength'].default_value=.7
    s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=16;s.cycles.use_denoising=True
    s.render.resolution_x=1024;s.render.resolution_y=1024;s.render.resolution_percentage=100
    s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.view_settings.view_transform='AgX';s.view_settings.exposure=.35
    return cam,center,scale
def run(aid):
    assert aid in ALLOWED,'Character work is paused; this tool permits non-character assets only.'
    source=BATCH/'Models'/aid/'v001'/(aid+'_v001.blend');before=sha(source)
    version=VERSIONS[aid]
    out=BATCH/'Models'/aid/version;ref=BATCH/'ArtLibrary/Turnarounds'/f'{aid}_{version}'
    if (out/'model_info.json').exists():print('ALREADY_COMPLETE',aid,flush=True);return
    if (out/(aid+'_'+version+'.blend')).exists():raise RuntimeError('Incomplete version exists; inspect it before resuming: '+aid)
    out.mkdir(parents=True,exist_ok=True);ref.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(source));bpy.context.preferences.filepaths.save_version=0
    s=bpy.context.scene;obs=[o for o in s.objects if o.type=='MESH'];root=bpy.data.objects.get(aid+'_ROOT')
    if aid=='QCaveEntrance':
        # Top jamb blocks coincided with arch endpoints, causing black coplanar seams.
        for name in ('Arch_jamb_-14','Arch_jamb_14'):
            ob=bpy.data.objects.get(name)
            assert ob is not None,name
            obs.remove(ob);bpy.data.objects.remove(ob,do_unlink=True)
    for m in bpy.data.materials:
        if not m.use_nodes:continue
        p=m.node_tree.nodes.get('Principled BSDF')
        if p:
            p.inputs['Roughness'].default_value=.78 if m.name not in ('crystal','crystalLight','gold') else .35
            p.inputs['Specular IOR Level'].default_value=.2
    hinges=[]
    if aid=='QCaveDoor':
        # Door narrowed to fit the opening between the entry's footstones (1.71m).
        for o in obs:
            o.location.x*=.86
            for v in o.data.vertices:v.co.x*=.86
        for side in (-1,1):
            h=bpy.data.objects.new('Door_Leaf_Left' if side<0 else 'Door_Leaf_Right',None);s.collection.objects.link(h)
            h.location=(side*.93*.86,.028499998,0);h.parent=root;hinges.append(h)
            for o in obs:
                if o.name.startswith('Hinge_'):continue
                lo,hi=bounds([o])
                if ((lo.x+hi.x)<0)==(side<0):
                    mw=o.matrix_world.copy();o.parent=h;o.matrix_world=mw
            for frame,angle in [(1,0),(35,side*math.pi/2),(85,side*math.pi/2),(120,0)]:
                h.rotation_euler.z=angle;h.keyframe_insert(data_path='rotation_euler',frame=frame)
        s.frame_start=1;s.frame_end=120;s.render.fps=30;s.frame_set(1)
    lo,hi=bounds(obs);cam,center,scale=lighting(obs);position(cam,center,scale,(1,-1,.45))
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs+[root]+hinges:o.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.export_scene.fbx(filepath=str(out/(aid+'_'+version+'.fbx')),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,bake_anim=False,add_leaf_bones=False)
    if hinges:
        bpy.ops.export_scene.fbx(filepath=str(out/(aid+'_open_close_v002.fbx')),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,add_leaf_bones=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/(aid+'_'+version+'.blend')))
    records=[]
    for name,dr in VIEWS:
        position(cam,center,scale,dr);dg=bpy.context.evaluated_depsgraph_get()
        projected=[world_to_camera_view(s,cam,e.matrix_world@Vector(v)) for o in obs for e in [o.evaluated_get(dg)] for v in e.bound_box]
        assert all(.005<p.x<.995 and .005<p.y<.995 and p.z>0 for p in projected),(aid,name,'cropped')
        s.render.filepath=str(ref/(name+'.png'));bpy.ops.render.render(write_still=True)
        records.append({'file':name+'.png','direction':dr,'framing_pass':True});print('VIEW_COMPLETE',aid,name,flush=True)
    if hinges:
        s.frame_set(60);lo2,hi2=bounds(obs);c=(lo2+hi2)/2;cam.data.ortho_scale=(hi2-lo2).length*1.18
        position(cam,c,cam.data.ortho_scale,(1,-1,.65));s.render.filepath=str(ref/'11_open_preview.png');bpy.ops.render.render(write_still=True);s.frame_set(1)
    info=json.loads((source.parent/'model_info.json').read_text(encoding='utf-8'))
    info.update({'version':version,'stage':'editable_noncharacter_prototype','source_version':'v001','source_sha256':before,'mesh_objects':len(obs),'triangles':sum(len(p.vertices)-2 for o in obs for p in o.data.polygons),
      'dimensions_m':list(hi-lo),'bounds_m':[list(lo),list(hi)],'render_engine':'Cycles CPU, 16 samples, denoised',
      'door_hinge_animation':bool(hinges),'animation_ready':False,'limits':'Appearance prototype; UV/LOD/collision and UE validation pending. Creatures not rigged.'})
    if hinges:info.update({'door_opening_frames':[1,35,85,120],'door_open_angle_deg':90,'door_width_adjustment':.86,'animated_fbx':aid+'_open_close_v002.fbx','hinge_axes_m':[list(h.location) for h in hinges]})
    (out/'model_info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    (ref/'views.json').write_text(json.dumps({'asset':aid,'version':version,'same_geometry':True,'resolution':[1024,1024],'views':records,'extra_images':['11_open_preview.png'] if hinges else []},indent=2),encoding='utf-8')
    assert sha(source)==before
    print('NONCHARACTER_COMPLETE',aid,flush=True)
if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ALLOWED
    assert set(args)<=set(ALLOWED)
    for aid in args:run(aid)
