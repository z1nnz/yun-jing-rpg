"""Mobile LOD1 for the foliage states of the Qingxi gathering kit (v002).
blender -b --python-exit-code 1 --python lod_export.py -- [key ...]     (no keys = the five foliage states)
Per state: import the exported LOD0 <key>.glb, collapse-decimate the single game mesh to the mobile triangle
target (UVs kept, same baked texture set), export exports/<Asset>/v002/<key>_LOD1_mobile.glb (textures
embedded), re-import it and record triangles / bounds / material and texture counts against LOD0, and render
a front comparison (LOD0 left, LOD1 right) to art/references/qingxi-gathering-visual-kit-v1/lod_v002/.
Results go to exports/<Asset>/v002/<key>_LOD1_mobile.json. This is a decimated copy of the baked LOD0, not a
separately authored mesh; billboards / impostors for far distance are not made here.
"""
import bpy,sys,json,math,hashlib
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import qx_kit as K
REPO=Path(__file__).resolve().parents[4];OUT=REPO/'art/exports/qingxi-gathering-visual-kit-v1';VER='v002'
REV=REPO/'art/references/qingxi-gathering-visual-kit-v1/lod_v002'
TARGET={'QX_SpiritHerb_Qinglan':9000,'QX_SpiritHerb_Chilu':12000,'QX_WaterReeds':12000}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load(p):
    before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(p))
    ms=[o for o in set(bpy.data.objects)-before if o.type=='MESH'];return ms

def stats(ms):
    bpy.context.view_layer.update();pts=[o.matrix_world@v.co for o in ms for v in o.data.vertices]
    lo=Vector([min(p[i] for p in pts) for i in range(3)]);hi=Vector([max(p[i] for p in pts) for i in range(3)])
    tris=0
    for o in ms:o.data.calc_loop_triangles();tris+=len(o.data.loop_triangles)
    mats={m.name for o in ms for m in o.data.materials if m};imgs={n.image.name for m in bpy.data.materials if m.node_tree for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image}
    return {'meshes':len(ms),'triangles':tris,'materials':len(mats),'images':len(imgs),'bounds_min_m':[round(x,4) for x in lo],'bounds_max_m':[round(x,4) for x in hi]}

def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def render_pair(key,lod0,lod1,dims,out):
    """Front orthographic comparison, LOD0 at x<0 and LOD1 at x>0, Cycles GPU if present."""
    clear();s=bpy.context.scene;w=max(dims[0],.3);h=max(dims[2],.3)
    a=load(lod0);b=load(lod1)
    for o in a:
        if o.parent is None:o.location.x-=w*.6
    for o in b:
        if o.parent is None:o.location.x+=w*.6
    cam=bpy.data.cameras.new('C');cam.type='ORTHO';cam.ortho_scale=max(w*2.5,h*1.15);co=bpy.data.objects.new('C',cam);s.collection.objects.link(co)
    co.location=(0,-10,h/2);co.rotation_euler=(math.pi/2,0,0);s.camera=co
    for e,(rx,rz) in {'K':(.9,-.6),'F':(1.2,.9)}.items():
        l=bpy.data.lights.new(e,'SUN');l.energy=3.2 if e=='K' else 1.0;lo=bpy.data.objects.new(e,l);lo.rotation_euler=(rx,0,rz);s.collection.objects.link(lo)
    wd=bpy.data.worlds.new('W');s.world=wd;wd.use_nodes=True;wd.node_tree.nodes['Background'].inputs[0].default_value=(.34,.36,.38,1)
    s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True;s.render.resolution_x=1600;s.render.resolution_y=int(1600*min(1.0,max(.35,h*1.15/(max(w*2.5,h*1.15)))))
    s.render.film_transparent=False;s.view_settings.view_transform='AgX'
    try:
        pr=bpy.context.preferences.addons['cycles'].preferences
        for t in ('OPTIX','CUDA'):
            try:pr.compute_device_type=t;pr.get_devices();break
            except Exception:pass
        for d in pr.devices:d.use=True
        s.cycles.device='GPU'
    except Exception:pass
    s.render.filepath=str(out);bpy.ops.render.render(write_still=True)

def run(key):
    aid=next(a for a,st in K.STATES if K.state_key(a,st)==key);d=OUT/aid/VER;src=d/f'{key}.glb';dst=d/f'{key}_LOD1_mobile.glb'
    clear();ms=load(src);s0=stats(ms);g=max(ms,key=lambda o:len(o.data.polygons))
    ratio=min(1.0,TARGET[aid]/max(s0['triangles'],1))
    m=g.modifiers.new('LOD1','DECIMATE');m.decimate_type='COLLAPSE';m.ratio=ratio;m.use_collapse_triangulate=True
    bpy.context.view_layer.objects.active=g;bpy.ops.object.modifier_apply(modifier=m.name)
    for o in bpy.context.view_layer.objects:o.select_set(False)
    for o in ms:o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(dst),export_format='GLB',use_selection=True,export_yup=True,export_apply=True,export_image_format='AUTO')
    clear();s1=stats(load(dst))
    err=max(abs(a-b) for a,b in zip(s0['bounds_min_m']+s0['bounds_max_m'],s1['bounds_min_m']+s1['bounds_max_m']))
    REV.mkdir(parents=True,exist_ok=True);dims=[s0['bounds_max_m'][i]-s0['bounds_min_m'][i] for i in range(3)]
    # glTF import is +Z up in Blender, so dims are x, y, z as authored
    png=REV/f'{key}_LOD0_vs_LOD1_front.png';render_pair(key,src,dst,dims,png)
    rec={'key':key,'asset':aid,'version':VER,'method':'Blender Decimate (collapse, triangulate) on the exported LOD0 game mesh; UVs and baked textures reused',
         'target_triangles':TARGET[aid],'ratio':round(ratio,4),'lod0':s0,'lod1':s1,'bounds_max_abs_diff_m':round(err,4),
         'comparison_render':str(png.relative_to(REPO)).replace('\\','/'),
         'file':{'name':dst.name,'bytes':dst.stat().st_size,'sha256':sha(dst)},
         'not_checked':['switch distance in an engine','visual pop at the switch','mobile device performance']}
    (d/f'{key}_LOD1_mobile.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf-8')
    print('LOD1',key,s0['triangles'],'->',s1['triangles'],'bounds diff',round(err,4),flush=True)

if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    for key in (args or [K.state_key(a,s) for a,s in K.STATES if a in TARGET]):run(key)
