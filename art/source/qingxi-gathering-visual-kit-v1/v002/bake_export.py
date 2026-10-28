"""Bake + export the Qingxi gathering kit game assets (v002).
blender -b --python-exit-code 1 --python bake_export.py -- [key ...]        (no keys = all nine states)
blender -b --python-exit-code 1 --python bake_export.py -- --master         (master .blend from the exports)
Per asset state:
  1. build the procedural source (qx_kit.build_state);
  2. join the game parts into one mesh: every part except the high-poly bake sources (their hidden low polys
     are game parts), modifiers applied; one fresh 'UVMap' atlas (smart project);
  3. bake base colour / roughness / tangent normal / emission selected-to-active from the render sources:
     group A = low polys <- high-poly sources (deep cage), group B = every other part <- itself (thin cage);
     both groups are baked without margin, composited by coverage and dilated;
  4. one PBR game material (double-sided, opaque, metallic 0);
  5. write exports/<Asset>/v002/<key>.glb (embedded textures), <key>.fbx (textures/ beside it),
     <key>.blend (procedural source + game mesh), textures/*.png and <key>_model_info.json.
Translucency, subsurface, transmission and metallic are switched off on the sources while baking so the
colour pass carries the full albedo; the game material does not reproduce them (noted in model_info).
Env: QX_SAMPLES (default 8), QX_RES (override the texture size).
"""
import bpy,bmesh,sys,os,json,math,time,hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import qx_kit as K
REPO=Path(__file__).resolve().parents[4];OUT=REPO/'art/exports/qingxi-gathering-visual-kit-v1';VER='v002'
PASSES=[('BaseColor','DIFFUSE',{'COLOR'},'sRGB'),('Roughness','ROUGHNESS',set(),'Non-Color'),('Normal','NORMAL',set(),'Non-Color'),('Emission','EMIT',set(),'sRGB')]
EMPTY={'BaseColor':None,'Roughness':(.8,.8,.8,1),'Normal':(.5,.5,1,1),'Emission':(0,0,0,1)}
CAGE={'A':(.06,.12),'B':(.003,.008)}          # (cage extrusion, max ray distance) in metres

def parse(key):
    for a,s in K.STATES:
        if K.state_key(a,s)==key:return a,s
    raise SystemExit('unknown key '+key)

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def select_only(objs,active=None):
    for o in bpy.context.view_layer.objects:o.select_set(False)
    for o in objs:o.select_set(True)
    if active:bpy.context.view_layer.objects.active=active

def game_mesh(key,objs,coll):
    """Evaluated copies of the game parts joined into one object; face int 'qx_grp' = 1 for low polys."""
    dg=bpy.context.evaluated_depsgraph_get();copies=[]
    for o in objs:
        if o.get('qx_role')=='bake_source_high_poly':continue
        me=bpy.data.meshes.new_from_object(o.evaluated_get(dg),preserve_all_data_layers=True,depsgraph=dg);me.transform(o.matrix_world)
        if not len(me.polygons):bpy.data.meshes.remove(me);continue
        a=me.attributes.new('qx_grp','INT','FACE');g=1 if o.get('qx_role')=='game_low_poly' else 0
        a.data.foreach_set('value',[g]*len(me.polygons))
        c=bpy.data.objects.new(o.name+'_G',me);coll.objects.link(c);copies.append(c)
    select_only(copies,copies[0]);bpy.ops.object.join();G=bpy.context.view_layer.objects.active;G.name=key;G.data.name=key+'_Mesh'
    for uv in list(G.data.uv_layers):G.data.uv_layers.remove(uv)
    for a in [a for a in G.data.attributes if a.name in ('Var','Rk','Rk2','Ms','G')]:G.data.attributes.remove(a)
    G.data.uv_layers.new(name='UVMap');G.data.materials.clear()
    select_only([G],G);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60),island_margin=.0015,area_weight=0.0,correct_aspect=True,scale_to_bounds=False)
    bpy.ops.uv.pack_islands(rotate=True,margin=.002)
    bpy.ops.object.mode_set(mode='OBJECT');return G

def split_group(G,grp,mat,coll):
    me=G.data.copy();bm=bmesh.new();bm.from_mesh(me);lay=bm.faces.layers.int['qx_grp']
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if f[lay]!=grp],context='FACES');n=len(bm.faces);bm.to_mesh(me);bm.free()
    if not n:bpy.data.meshes.remove(me);return None
    me.materials.clear();me.materials.append(mat);o=bpy.data.objects.new(f'{G.name}_Bake{grp}',me);coll.objects.link(o);return o

def prepare_sources(objs):
    """Full albedo into the colour pass: no translucent mix, subsurface, transmission or metal while baking."""
    for m in {m for o in objs for m in o.data.materials if m and m.use_nodes}:
        nt=m.node_tree
        for n in nt.nodes:
            if n.type=='MIX_SHADER' and n.inputs[2].is_linked and n.inputs[2].links[0].from_node.type=='BSDF_TRANSLUCENT':
                for l in list(n.inputs[0].links):nt.links.remove(l)
                n.inputs[0].default_value=0.0
            if n.type=='BSDF_PRINCIPLED':
                met=n.inputs['Metallic']
                if met.is_linked or met.default_value>.01:                          # metal reads as dark iron, not its rust-tinted base colour
                    mx=nt.nodes.new('ShaderNodeMix');mx.data_type='RGBA';bc=n.inputs['Base Color']
                    if met.is_linked:nt.links.new(met.links[0].from_socket,mx.inputs[0])
                    else:mx.inputs[0].default_value=met.default_value
                    if bc.is_linked:nt.links.new(bc.links[0].from_socket,mx.inputs[6])
                    else:mx.inputs[6].default_value=bc.default_value
                    mx.inputs[7].default_value=(.055,.055,.058,1);nt.links.new(mx.outputs[2],bc)
                for name in ('Subsurface Weight','Transmission Weight','Metallic'):
                    s=n.inputs.get(name)
                    if s:
                        for l in list(s.links):nt.links.remove(l)
                        s.default_value=0.0

def dilate(arr,filled,steps=24):
    a=arr.copy();f=filled.copy()
    for _ in range(steps):
        acc=np.zeros_like(a);cnt=np.zeros(f.shape,np.float32)
        for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
            sf=np.roll(f,(dy,dx),(0,1));sa=np.roll(a,(dy,dx),(0,1))
            acc+=sa*sf[...,None];cnt+=sf
        new=(~f)&(cnt>0);a[new]=acc[new]/cnt[new][:,None];f=f|new
        if f.all():break
    return a,f

def bake_state(key,res,samples):
    aid,st=parse(key);bpy.ops.wm.read_factory_settings(use_empty=True);K.M.clear();s=bpy.context.scene
    src=bpy.data.collections.new('10_Procedural_Source');s.collection.children.link(src)
    root,objs=K.build_state(aid,st,src);bpy.context.view_layer.update()
    s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=samples;s.cycles.use_denoising=False
    game=bpy.data.collections.new('00_Game_Export');s.collection.children.link(game)
    t0=time.time();G=game_mesh(key,objs,game);tris=len(G.data.loop_triangles) if G.data.loop_triangles else sum(len(p.vertices)-2 for p in G.data.polygons)
    prepare_sources(objs)
    tm=bpy.data.materials.new('QX_BakeTarget');tm.use_nodes=True;tex=tm.node_tree.nodes.new('ShaderNodeTexImage');tm.node_tree.nodes.active=tex
    tgt={'A':split_group(G,1,tm,game),'B':split_group(G,0,tm,game)}
    srcs={'A':[o for o in objs if o.get('qx_role')=='bake_source_high_poly'],
          'B':[o for o in objs if not o.hide_render and o.get('qx_role')!='bake_source_high_poly']}
    G.hide_render=True;tdir=OUT/aid/VER/'textures';tdir.mkdir(parents=True,exist_ok=True);maps={}
    for pname,ptype,pfilter,cs in PASSES:
        layers={}
        for gk in ('A','B'):
            if tgt[gk] is None or not srcs[gk]:continue
            img=bpy.data.images.new(f'{key}_{pname}_{gk}',res,res,alpha=True);img.generated_color=(0,0,0,0);img.colorspace_settings.name=cs;tex.image=img
            for o in tgt.values():
                if o:o.hide_render=o is not tgt[gk]
            select_only(srcs[gk]+[tgt[gk]],tgt[gk]);ext,dist=CAGE[gk]
            bpy.ops.object.bake(type=ptype,pass_filter=pfilter,use_selected_to_active=True,cage_extrusion=ext,max_ray_distance=dist,margin=0,use_clear=False,target='IMAGE_TEXTURES')
            px=np.empty(res*res*4,np.float32);img.pixels.foreach_get(px);layers[gk]=px.reshape(res,res,4)
        out=np.zeros((res,res,4),np.float32);filled=np.zeros((res,res),bool)
        for gk in ('B','A'):                                                                       # A (stone) over B where both landed
            if gk in layers:m=layers[gk][...,3]>.5;out[m]=layers[gk][m];filled|=m
        cover=float(filled.mean());rgb,f2=dilate(out[...,:3],filled)
        fill=EMPTY[pname] or (*(rgb[filled].mean(0) if filled.any() else (.2,.2,.2)),1)
        rgb[~f2]=fill[:3];fin=np.concatenate([rgb,np.ones((res,res,1),np.float32)],2)
        img=bpy.data.images.new(f'{key}_{pname}',res,res,alpha=False);img.colorspace_settings.name=cs;img.pixels.foreach_set(fin.ravel())
        p=tdir/f'{key}_{pname}.png';img.filepath_raw=str(p);img.file_format='PNG';img.save();maps[pname]=(img,p,cover)
        print('BAKED',key,pname,f'coverage={cover:.3f}',flush=True)
    for o in tgt.values():
        if o:bpy.data.meshes.remove(o.data)
    bpy.data.materials.remove(tm);G.hide_render=False
    # --- game material
    gm=bpy.data.materials.new(key+'_Mat');gm.use_nodes=True;gm.use_backface_culling=False;nt=gm.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
    def tnode(name,x):n=nt.nodes.new('ShaderNodeTexImage');n.image=maps[name][0];n.location=(x,0);return n
    nt.links.new(tnode('BaseColor',-600).outputs['Color'],bs.inputs['Base Color'])
    nt.links.new(tnode('Roughness',-600).outputs['Color'],bs.inputs['Roughness'])
    nm=nt.nodes.new('ShaderNodeNormalMap');nm.uv_map='UVMap';nt.links.new(tnode('Normal',-900).outputs['Color'],nm.inputs['Color']);nt.links.new(nm.outputs['Normal'],bs.inputs['Normal'])
    nt.links.new(tnode('Emission',-600).outputs['Color'],bs.inputs['Emission Color']);bs.inputs['Emission Strength'].default_value=1.0;bs.inputs['Metallic'].default_value=0.0
    G.data.materials.append(gm)
    if 'qx_grp' in G.data.attributes:G.data.attributes.remove(G.data.attributes['qx_grp'])
    G['asset']=aid;G['state']=st;G['qx_role']='game_export'
    # --- export
    d=OUT/aid/VER;glb=d/f'{key}.glb';fbx=d/f'{key}.fbx';blend=d/f'{key}.blend'
    select_only([G],G)
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_apply=True,export_materials='EXPORT',export_yup=True)
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',
                             path_mode='RELATIVE',mesh_smooth_type='FACE',add_leaf_bones=False,axis_forward='-Z',axis_up='Y')
    for img,p,_ in maps.values():img.filepath=str(p)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True,relative_remap=True)
    lo=Vector([min((G.matrix_world@v.co)[i] for v in G.data.vertices) for i in range(3)]);hi=Vector([max((G.matrix_world@v.co)[i] for v in G.data.vertices) for i in range(3)])
    G.data.calc_loop_triangles();hp=sum(len(o.data.polygons) for o in srcs['A'])
    info={'key':key,'asset':aid,'state':st,'name_zh':K.NAMES[aid],'state_zh':K.STATE_ZH[st],'version':VER,
          'design':K.DESIGN[aid],'material_direction':K.MATERIAL_DIRECTION[aid],
          'units':'1 Blender unit = 1 m','front_axis':'-Y (Blender); GLB exported +Y up, so the front faces +Z in glTF space',
          'origin':'bottom centre at ground level' if aid in K.GROUND_ORIGIN or not K.CENTRE_XY.get(aid,True) else 'bottom centre of the bounds',
          'dimensions_m':[round(x,4) for x in hi-lo],'bounds_min_m':[round(x,4) for x in lo],'bounds_max_m':[round(x,4) for x in hi],
          'game_triangles':len(G.data.loop_triangles),'game_vertices':len(G.data.vertices),'high_poly_bake_source_faces':hp,
          'texture_size_px':res,'texture_maps':{k:{'file':str(v[1].relative_to(d)).replace('\\','/'),'uv_coverage_before_dilation':round(v[2],4)} for k,v in maps.items()},
          'bake':{'engine':'Cycles CPU','samples':samples,'groups':{'A_low_poly_from_high_poly':{'cage_extrusion_m':CAGE['A'][0],'max_ray_m':CAGE['A'][1],'sources':[o.name for o in srcs['A']]},
                                                                   'B_self':{'cage_extrusion_m':CAGE['B'][0],'max_ray_m':CAGE['B'][1],'sources':len(srcs['B'])}}},
          'not_reproduced_in_game_material':['leaf / petal back-light translucency','berry / blossom subsurface','crystal transmission (crystals are opaque with baked colour and emission)','iron metallic (baked as dark iron-grey dielectric: base colour mixed toward 0.055 grey by the metallic amount)'],
          'files':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in (glb,fbx,blend)},
          'build_seconds':round(time.time()-t0,1)}
    if K.ctx.extra:info['build_notes']={k:(v if isinstance(v,(int,float,str,list)) else str(v)) for k,v in K.ctx.extra.items()}
    (d/f'{key}_model_info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    print('EXPORTED',key,info['dimensions_m'],info['game_triangles'],f"{info['build_seconds']}s",flush=True)

def master():
    """One editable master file: every state's procedural source in a row (x spacing by footprint) plus the
    re-imported game GLB of each state one row behind it."""
    bpy.ops.wm.read_factory_settings(use_empty=True);K.M.clear();s=bpy.context.scene;x=0.0;rows={}
    srcc=bpy.data.collections.new('10_Procedural_Sources');s.collection.children.link(srcc)
    gamec=bpy.data.collections.new('00_Game_GLB_v002');s.collection.children.link(gamec)
    for aid,st in K.STATES:
        key=K.state_key(aid,st);info=json.loads((OUT/aid/VER/f'{key}_model_info.json').read_text('utf-8'));w=info['dimensions_m'][0]
        x+=w/2;root,objs=K.build_state(aid,st,srcc,(x,0,0))
        before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(OUT/aid/VER/f'{key}.glb'))
        for o in set(bpy.data.objects)-before:
            for c in list(o.users_collection):c.objects.unlink(o)
            gamec.objects.link(o)
            if o.parent is None:o.location=(x,6.0,0)
        rows[key]=x;x+=w/2+1.0
    s['qx_layout']=json.dumps(rows);p=OUT/f'QX_QingxiGatheringKit_master_{VER}.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(p),compress=True,relative_remap=True);print('MASTER',p,flush=True)

if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    if '--master' in args:master()
    else:
        samples=int(os.environ.get('QX_SAMPLES','8'))
        for key in (args or [K.state_key(a,s) for a,s in K.STATES]):
            aid,_=parse(key);res=int(os.environ.get('QX_RES',K.TEX_RES.get(aid,1024)))
            bake_state(key,res,samples)
