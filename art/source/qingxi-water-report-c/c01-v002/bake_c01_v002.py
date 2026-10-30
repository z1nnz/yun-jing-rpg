"""C01 v002 bake + export — Eli-0731, Blender 4.5.3 LTS.
Runs after build_c01_v002.py. Gives LOD0 a unique UV, bakes the tiled source materials into one 1024² set
(albedo with AO + edge wear, tangent normal, URP mask, glTF ORM), transfers that UV to LOD1/LOD2 and exports
one-material FBX (Unity) and GLB (PWA).
blender -b --factory-startup -P bake_c01_v002.py
"""
import bpy,bmesh,json,math
from pathlib import Path
import numpy as np
SRC=Path(__file__).resolve().parent;ROOT=SRC.parents[3]
TEX=ROOT/'art/textures/qingxi-water-report-c/c01-v002';OUT=ROOT/'art/exports/qingxi-water-report-c/c01-v002'
bpy.ops.wm.open_mainfile(filepath=str(SRC/'C01_CouncilTable_v002.blend'))
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=16
bk=sc.render.bake;bk.margin=12;bk.use_clear=True
RES=1024
lod=[bpy.data.objects[f'C01_CouncilTable_LOD{i}'] for i in range(3)];L0=lod[0]
mats=list(L0.data.materials)
METAL={'C01_AgedBronze':.30}
for o in sc.objects:o.hide_render=o is not L0  # only LOD0 may occlude itself while baking
def sel(o):
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
# ---------- unique UV on LOD0 ----------
sel(L0);L0.data.uv_layers['UVMap'].active_render=True
bake_uv=L0.data.uv_layers.new(name='Bake');L0.data.uv_layers.active=bake_uv
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(60),island_margin=.004,area_weight=0,correct_aspect=True,scale_to_bounds=False)
bpy.ops.uv.pack_islands(margin=.004,rotate=True)
bpy.ops.object.mode_set(mode='OBJECT')
# triangulate before baking so the baked tangent basis matches what the engines compute
bm=bmesh.new();bm.from_mesh(L0.data);bmesh.ops.triangulate(bm,faces=bm.faces);bm.to_mesh(L0.data);bm.free()
# source textures keep reading the tiled UVMap; the bake target is the active 'Bake' layer
for m in mats:
    nt=m.node_tree;uvn=nt.nodes.new('ShaderNodeUVMap');uvn.uv_map='UVMap'
    for n in [n for n in nt.nodes if n.type=='TEX_IMAGE']:nt.links.new(uvn.outputs['UV'],n.inputs['Vector'])
def target(name,noncolor=False):
    im=bpy.data.images.new(name,RES,RES,alpha=False,float_buffer=noncolor)  # float buffers are linear: data maps bake without sRGB encoding
    for m in mats:
        nt=m.node_tree;t=nt.nodes.get('BAKE_TARGET') or nt.nodes.new('ShaderNodeTexImage');t.name='BAKE_TARGET';t.image=im;nt.nodes.active=t
    return im
def arr(im):return np.array(im.pixels[:],dtype=np.float32).reshape(RES,RES,4)
def bake(name,type,noncolor=False,**kw):
    im=target(name,noncolor);sel(L0);bpy.ops.object.bake(type=type,**kw);return arr(im)
def emission_override(fn):
    """temporarily drive each material's output from an emission computed by fn(nodetree, material)"""
    saved=[]
    for m in mats:
        nt=m.node_tree;out=next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL');old=out.inputs['Surface'].links[0].from_socket
        em=nt.nodes.new('ShaderNodeEmission');fn(nt,m,em);nt.links.new(em.outputs[0],out.inputs['Surface']);saved.append((nt,out,old,em))
    return saved
def restore(saved):
    for nt,out,old,em in saved:nt.links.new(old,out.inputs['Surface']);nt.nodes.remove(em)
albedo=bake('C01_bake_albedo','DIFFUSE',pass_filter={'COLOR'})
sc.cycles.samples=64;ao=bake('C01_bake_ao','AO',True)[...,0];sc.cycles.samples=16
rough=bake('C01_bake_rough','ROUGHNESS',True)[...,0]
nrm=bake('C01_bake_normal','NORMAL',True,normal_space='TANGENT')
s=emission_override(lambda nt,m,em:em.inputs['Color'].__setattr__('default_value',(METAL.get(m.name,0),)*3+(1,)))
metal=bake('C01_bake_metal','EMIT',True)[...,0];restore(s)
def edges(nt,m,em):
    g=nt.nodes.new('ShaderNodeNewGeometry');r=nt.nodes.new('ShaderNodeValToRGB');r.color_ramp.elements[0].position=.53;r.color_ramp.elements[1].position=.62
    nt.links.new(g.outputs['Pointiness'],r.inputs['Fac']);nt.links.new(r.outputs['Color'],em.inputs['Color'])
s=emission_override(edges);edge=bake('C01_bake_edge','EMIT',True)[...,0];restore(s)
def position(nt,m,em):
    g=nt.nodes.new('ShaderNodeNewGeometry');nt.links.new(g.outputs['Position'],em.inputs['Color'])
s=emission_override(position);pos=bake('C01_bake_pos','EMIT',True)[...,:3];restore(s)
filled=np.abs(pos).sum(2)>1e-6
px,py,pz=pos[...,0],pos[...,1],pos[...,2];rad=np.hypot(px,py)
rng=np.random.default_rng(31)
def smooth(a,lo,hi):return np.clip((a-lo)/(hi-lo),0,1)
# ---------- compose (stylised: AO kept soft, worn edges lifted and warmed) ----------
col=albedo[...,:3]*(.62+.38*ao[...,None])
wear=np.clip(edge,0,1)[...,None]*(1-.6*metal[...,None])
col=np.clip(col*(1+.45*wear)+wear*np.array([.05,.035,.015]),0,1)
top=(pz>.612)&filled&(metal<.01)
# hands and cups polish the middle ring of the top: lighter, smoother
polish=top*smooth(.40-rad,0,.18)*(rad>.12)
col=col*(1+.22*polish[...,None]);rough=rough-.18*polish
# knife marks and cup rings on the top (sub-2 cm detail lives in the texture, per spec)
scr=np.zeros_like(px)
for _ in range(46):
    a=rng.uniform(0,np.pi);r0=rng.uniform(.14,.50);t0=rng.uniform(0,2*np.pi);c=np.array([r0*np.cos(t0),r0*np.sin(t0)]);L=rng.uniform(.03,.11);d=np.array([np.cos(a),np.sin(a)])
    rx,ry=px-c[0],py-c[1];along=np.clip(rx*d[0]+ry*d[1],-L/2,L/2);dist=np.hypot(rx-along*d[0],ry-along*d[1]);scr=np.maximum(scr,np.clip(1-dist/.0011,0,1))
for _ in range(3):
    t0=rng.uniform(0,2*np.pi);r0=rng.uniform(.2,.42);cx,cy=r0*np.cos(t0),r0*np.sin(t0);rr=rng.uniform(.032,.042)
    scr=np.maximum(scr,.55*np.clip(1-np.abs(np.hypot(px-cx,py-cy)-rr)/.0018,0,1))
scr*=top;col=col*(1-.28*scr[...,None])
# dried mud splashed up the feet and the lowest part of the legs
mudn=np.clip(np.sin(px*90)*np.sin(py*83)*.5+.5+.3*np.sin((px+py)*240),0,1)
mud=filled*smooth(.16-pz,0,.10)*np.clip(.55+.6*mudn,0,1)*(metal<.01)
col=col*(1-mud[...,None])+np.array([.25,.20,.14])*mud[...,None]*(.85+.2*mudn[...,None]);rough=rough+.08*mud
def save(name,rgba,noncolor=False):
    im=bpy.data.images.new(name,RES,RES,alpha=True)
    if noncolor:im.colorspace_settings.name='Non-Color'  # set before writing pixels: changing it afterwards regenerates a blank buffer
    im.pixels.foreach_set(np.ascontiguousarray(rgba,dtype=np.float32).ravel())
    im.filepath_raw=str(TEX/f'{name}.png');im.file_format='PNG';im.save();return im
one=np.ones((RES,RES),np.float32)
ALB=save('C01_CouncilTable_v002_Albedo',np.dstack([col,one]))
NRM=save('C01_CouncilTable_v002_Normal',nrm,True)
MASK=save('C01_CouncilTable_v002_MaskURP',np.dstack([metal,ao,0*one,1-rough]),True)  # URP Lit: R metal, A smoothness (G=AO for the Occlusion slot)
ORM=save('C01_CouncilTable_v002_ORM',np.dstack([ao,rough,metal,one]),True)          # glTF: R occlusion, G roughness, B metallic
# ---------- final single material ----------
fm=bpy.data.materials.new('C01_CouncilTable');fm.use_nodes=True;nt=fm.node_tree;bs=nt.nodes['Principled BSDF']
def tex(im):t=nt.nodes.new('ShaderNodeTexImage');t.image=im;return t
nt.links.new(tex(ALB).outputs['Color'],bs.inputs['Base Color'])
nm=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(tex(NRM).outputs['Color'],nm.inputs['Color']);nt.links.new(nm.outputs['Normal'],bs.inputs['Normal'])
sp=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(tex(ORM).outputs['Color'],sp.inputs['Color'])
nt.links.new(sp.outputs['Green'],bs.inputs['Roughness']);nt.links.new(sp.outputs['Blue'],bs.inputs['Metallic'])
# ---------- export copies: LOD0 bake UV, transferred to LOD1/LOD2 ----------
exp=[]
for i,o in enumerate(lod):
    d=o.copy();d.data=o.data.copy();sc.collection.objects.link(d);d.name=o.name.replace('LOD','Export_LOD')
    if i:
        bm=bmesh.new();bm.from_mesh(d.data);bmesh.ops.triangulate(bm,faces=bm.faces);bm.to_mesh(d.data);bm.free()
        d.data.uv_layers.new(name='Bake');sel(d);m=d.modifiers.new('uv','DATA_TRANSFER');m.object=L0;m.use_loop_data=True;m.data_types_loops={'UV'}
        m.layers_uv_select_src='Bake';m.layers_uv_select_dst='Bake';m.loop_mapping='POLYINTERP_NEAREST';bpy.ops.object.modifier_apply(modifier=m.name)
    uvs=d.data.uv_layers;uvs.remove(uvs['UVMap']);uvs['Bake'].name='UVMap'
    d.data.materials.clear();d.data.materials.append(fm);exp.append(d)
colo=bpy.data.objects['C01_CouncilTable_Collider']
bpy.ops.wm.save_as_mainfile(filepath=str(SRC/'C01_CouncilTable_v002.blend'))
for d,o in zip(exp,lod):o.name=o.name+'_src';d.name=d.name.replace('Export_LOD','LOD')  # export names stay C01_CouncilTable_LODn
sel(exp[0]);bpy.ops.export_scene.gltf(filepath=str(OUT/'C01_CouncilTable_v002.glb'),use_selection=True,export_format='GLB',export_apply=True)
for o in exp+[colo]:o.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(OUT/'C01_CouncilTable_v002.fbx'),use_selection=True,object_types={'MESH'},global_scale=1.0,apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_ALL',bake_space_transform=True,axis_forward='-Z',axis_up='Y',use_mesh_modifiers=True,mesh_smooth_type='FACE',
    use_tspace=True,add_leaf_bones=False,bake_anim=False,path_mode='RELATIVE',embed_textures=False)
def tris(o):return sum(len(p.vertices)-2 for p in o.data.polygons)
pts=[v.co for v in exp[0].data.vertices];dims=[max(p[i] for p in pts)-min(p[i] for p in pts) for i in range(3)]
# UV sanity: islands inside 0-1
uv=np.array([l.uv[:] for l in exp[0].data.uv_layers['UVMap'].data]);uvok=bool((uv>=-1e-4).all() and (uv<=1+1e-4).all())
report={'asset':'C01_CouncilTable_v002','authors':'Eli-0731','reference':'art/references/qingxi-water-report-c/C01-three-view.png',
 'dimensions_xyz_m':[round(x,4) for x in dims],'uv0_in_unit_square':uvok,
 'stats':{o.name:{'triangles':tris(o),'vertices':len(o.data.vertices),'materials':len(o.data.materials)} for o in exp+[colo]},
 'textures':{p.name:f'{RES}x{RES}' for p in sorted(TEX.glob('C01_CouncilTable_v002_*.png'))},
 'lods':'hand-authored per-LOD geometry (build_c01_v002.py LODS); LOD1/LOD2 reuse the LOD0 bake through UV data transfer',
 'unity':'not imported on this machine (no Unity Editor installed)'}
(OUT/'C01_CouncilTable_v002-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=1),encoding='utf-8')
print('C01V2_BAKED',json.dumps(report,ensure_ascii=False))
