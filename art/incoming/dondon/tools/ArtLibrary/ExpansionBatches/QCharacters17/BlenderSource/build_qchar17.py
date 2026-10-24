"""QCharacters17 builder (Blender 5.2 CLI). Writes only inside this batch folder; skips characters whose views.json exists.
  blender --background --python-exit-code 1 --python build_qchar17.py [-- QPlayerMale ...]    # characters
  blender --background --python-exit-code 1 --python build_qchar17.py -- lineup                # design-sheet lineups
"""
import bpy,sys,json,math,importlib.util
from pathlib import Path
from mathutils import Vector
SRC=Path(__file__).resolve().parent;BATCH=SRC.parent
import os
VER=os.environ.get('QCHAR_VERSION','v001')   # v002 = user revision: anime eyes, fuller hair, 2.5 heads, gripping hands
spec=importlib.util.spec_from_file_location('qchar17',SRC/('qchar17.py' if VER=='v001' else f'qchar17_{VER}.py'));Q=importlib.util.module_from_spec(spec);spec.loader.exec_module(Q)
VIEWS=[('01_front',(0,-1,.12)),('02_right',(1,0,.12)),('03_rear',(0,1,.12)),('04_left',(-1,0,.12)),('05_front_right',(1,-1,.45)),
       ('06_rear_right',(1,1,.45)),('07_rear_left',(-1,1,.45)),('08_front_left',(-1,-1,.45)),('09_top',(0,0,1)),('10_high_front',(0,-1,1))]

def bounds(objs):
    dg=bpy.context.evaluated_depsgraph_get();pts=[o.evaluated_get(dg).matrix_world@v.co for o in objs for v in o.evaluated_get(dg).data.vertices]
    return Vector([min(p[i] for p in pts) for i in range(3)]),Vector([max(p[i] for p in pts) for i in range(3)])

def studio(s,coll,centre,size,res=(1024,1024)):
    w=bpy.data.worlds.new('Q17_Studio');w.use_nodes=True;s.world=w;bg=next(n for n in w.node_tree.nodes if n.type=='BACKGROUND')
    bg.inputs[0].default_value=(.42,.45,.46,1);bg.inputs[1].default_value=.7
    for name,d,p in (('Key',(-.8,-1.2,1.3),900),('Fill',(1.2,-.6,.7),450),('Rim',(.3,1.2,1.1),700)):
        l=bpy.data.lights.new('Q17_'+name,'AREA');l.energy=p*size*size/2.2;l.shape='DISK';l.size=size*.9
        o=bpy.data.objects.new('Q17_'+name,l);coll.objects.link(o);o.location=centre+Vector(d)*size*1.6;o.rotation_euler=(centre-o.location).to_track_quat('-Z','Y').to_euler()
    try:s.render.engine='CYCLES'
    except TypeError as e:raise SystemExit('Cycles unavailable: %s'%e)
    s.cycles.device='CPU';s.cycles.samples=48;s.cycles.use_denoising=True
    s.render.resolution_x,s.render.resolution_y=res;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
    s.view_settings.view_transform='AgX';s.view_settings.exposure=-.2   # +0.15 washed black hair out to grey-brown in the first lineup
    cam=bpy.data.objects.new('Q17_Camera',bpy.data.cameras.new('Q17_Camera'));coll.objects.link(cam);s.camera=cam;cam.data.type='ORTHO';cam.data.clip_end=200.
    return cam

def aim(cam,centre,d,dist=30.):
    cam.location=centre+Vector(d).normalized()*dist;cam.rotation_euler=(centre-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()

def fit(s,cam,pts,margin=.06):
    from bpy_extras.object_utils import world_to_camera_view
    cam.data.ortho_scale=.2
    while True:
        pr=[world_to_camera_view(s,cam,p) for p in pts]
        if all(margin<p.x<1-margin and margin<p.y<1-margin for p in pr) or cam.data.ortho_scale>50:return cam.data.ortho_scale
        cam.data.ortho_scale*=1.03

def build(aid):
    out=BATCH/'Models'/aid/VER;views=BATCH/'ArtLibrary/Turnarounds'/f'{aid}_{VER}'
    if (views/'views.json').exists():print('ALREADY_COMPLETE',aid,flush=True);return
    out.mkdir(parents=True,exist_ok=True);views.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;bpy.context.preferences.filepaths.save_version=0
    s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
    coll=bpy.data.collections.new('01_Editable_Asset');s.collection.children.link(coll)
    st=bpy.data.collections.new('90_Studio_Not_Exported');s.collection.children.link(st)
    root=Q.build_character(coll,aid);bpy.context.view_layer.update()
    objs=[o for o in coll.objects if o.type=='MESH'];lo,hi=bounds(objs)
    shift=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
    for o in objs:o.location-=shift          # bottom-centre origin, root stays at 0
    bpy.context.view_layer.update();lo,hi=bounds(objs);ext=hi-lo;centre=(lo+hi)/2
    bpy.ops.object.select_all(action='DESELECT')
    for o in [root]+objs:o.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.export_scene.fbx(filepath=str(out/f'{aid}_{VER}.fbx'),use_selection=True,object_types={'MESH','EMPTY'},add_leaf_bones=False,axis_forward='-Z',axis_up='Y',
                             apply_unit_scale=True,use_mesh_modifiers=True,bake_anim=False)
    dg=bpy.context.evaluated_depsgraph_get();tris=sum(len(p.vertices)-2 for o in objs for p in o.evaluated_get(dg).data.polygons)
    spec=Q.CHARACTERS[aid]
    info={'asset':aid,'version':VER,'name_zh':spec['zh'],'style':'Q-version chibi, ~2 heads tall' if VER=='v001' else 'Q-version chibi, ~2.5 heads, anime eyes, gripping hands',
          'grips':Q.CHARACTERS[aid].get('props',[]) and root.get('grips'),'units':'meters','front':'-Y','pivot':'bottom centre',
          'dimensions_m':list(ext),'height_m':ext.z,'mesh_objects':len(objs),'triangles':tris,'pose':'A-pose (arms ~35 deg), static',
          'hair':spec['hair'],'props':spec.get('props',[]),'kit':'qchar17.py shared body/face/hair/outfit/prop parts',
          'modeling_method':'procedural Python, editable separate parts; no generative AI','rigged':False,'uv_baked':False,'collision':False,'lod':False,'unreal_import_verified':False}
    (out/'model_info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    cam=studio(s,st,centre,max(ext))
    bpy.ops.wm.save_as_mainfile(filepath=str(out/f'{aid}_{VER}.blend'))
    pts=[Vector((x,y,z)) for x in (lo.x,hi.x) for y in (lo.y,hi.y) for z in (lo.z,hi.z)];recs=[]
    for name,d in VIEWS:
        aim(cam,centre,d);sc=fit(s,cam,pts);s.render.filepath=str(views/(name+'.png'));bpy.ops.render.render(write_still=True)
        recs.append({'file':name+'.png','direction':list(d),'camera_location':list(cam.location),'ortho_scale':sc,'projection':'orthographic','framing_checked':True})
        print('VIEW_COMPLETE',aid,name,flush=True)
    (views/'views.json').write_text(json.dumps({'asset':aid,'source':f'Models/{aid}/{VER}/{aid}_{VER}.blend','same_geometry':True,'views':recs},indent=2))
    print('ASSET_COMPLETE',aid,flush=True)

def lineup():
    out=BATCH/('DesignSheets' if VER=='v001' else f'DesignSheets_{VER}');out.mkdir(exist_ok=True)
    if (out/'lineup.json').exists():print('ALREADY_COMPLETE lineup');return
    bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene
    st=bpy.data.collections.new('90_Studio');s.collection.children.link(st);ids=list(Q.CHARACTERS);gap=.82;order=[]
    for i,aid in enumerate(ids):
        c=bpy.data.collections.new(aid);s.collection.children.link(c);r=Q.build_character(c,aid);r.location=((i-(len(ids)-1)/2)*gap,0,0);order.append([aid,Q.CHARACTERS[aid]['zh'],r.location.x])
    bpy.context.view_layer.update();objs=[o for o in bpy.data.objects if o.type=='MESH'];lo,hi=bounds(objs);centre=(lo+hi)/2
    cam=studio(s,st,centre,4.,(3200,800));pts=[Vector((x,y,z)) for x in (lo.x,hi.x) for y in (lo.y,hi.y) for z in (lo.z,hi.z)]
    shots={}
    for name,d in (('lineup_front',(0,-1,.08)),('lineup_three_quarter',(.35,-1,.2)),('lineup_back',(0,1,.08))):
        aim(cam,centre,d);fit(s,cam,pts,.03);s.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
        from bpy_extras.object_utils import world_to_camera_view
        shots[name]=[[aid,zh,world_to_camera_view(s,cam,Vector((x,0,0))).x] for aid,zh,x in order];print('LINEUP',name,flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/f'QCharacters17_lineup_{VER}.blend' if VER!='v001' else 'QCharacters17_lineup.blend'))
    (out/'lineup.json').write_text(json.dumps({'characters':order,'label_x_fraction':shots,'note':'Rendered from the same kit geometry as the per-character models'},ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else list(Q.CHARACTERS)
    if args==['lineup']:lineup()
    else:
        for aid in args:build(aid)
