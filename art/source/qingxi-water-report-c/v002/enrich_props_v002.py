"""Detail pass v002 for the delivered water-report props — Eli-0731, Blender 4.5.3 LTS.
Source geometry: ../WaterReportC_variants.blend (v001, already modelled from saved AI three-views; untouched).
For each prop: worn/rounded edges, tiled wood/stone/bronze/hemp materials (shared with C01 v002),
unique-UV bake (albedo with AO + edge wear + ground mud, tangent normal, URP mask, glTF ORM),
LOD0 = detailed, LOD1 = clean v001 geometry, LOD2 ≈ 15 % of LOD0. State parts (water, soil, cloth) stay
separate objects with their own simple materials so the existing state switching keeps working.
blender -b --factory-startup -P enrich_props_v002.py -- [ids...]
"""
import bpy,bmesh,json,math,sys
from pathlib import Path
from mathutils import Vector,Matrix
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
SRCBLEND=HERE.parent/'WaterReportC_variants.blend'
TEX0=ROOT/'art/textures/qingxi-water-report-c/c01-v002'          # shared tiled source textures
TEX=ROOT/'art/textures/qingxi-water-report-c/v002';OUT=ROOT/'art/exports/qingxi-water-report-c/v002'
for p in (TEX,OUT):p.mkdir(parents=True,exist_ok=True)
IDS=['C02','C04','C07','C08','C03_tall_01','C03_low_02','C03_bail_03','C05_notch_01','C05_fork_02','C06_fork_01','C06_slant_02']
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
IDS=[i for i in IDS if not args or i in args]
# material families: tint multiplies the shared tiled albedo
FAM={'warm_weathered_wood':('wood',(.92,.86,.80),.72,0),'old_joinery':('wood',(.52,.43,.38),.70,0),'aged_bamboo':('wood',(1.08,1.04,.66),.60,0),
     'natural_hemp':('hemp',(1,1,1),.92,0),'warm_gray_stone':('stone',(.74,.77,.73),.86,0),'stone_recess':('stone',(.24,.31,.27),.88,0),
     'aged_bronze':('bronze',(1,1,1),.50,.30),'dry_ochre':('paint',(.61,.37,.13),.80,0),'restored_teal':('paint',(.12,.39,.37),.80,0),
     'record_choice':('bronze',(1.15,1.05,.7),.55,.25)}   # tints matched against the v001 palette so the detail pass does not wash colours out
STATE={'opaque_water_sample','soil_dry','soil_partly_moist','soil_moist','work_in_progress_hemp','complete_sage_hemp'}
def base(n):return n.split('.')[0]
def is_state(o,pid):
    ms={base(m.name) for m in o.data.materials}
    return bool(ms&STATE) or (pid.startswith('C06') and bool(ms&{'restored_teal','dry_ochre'}))
RES=1024
def run(pid):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=16;bk=sc.render.bake;bk.margin=12
    with bpy.data.libraries.load(str(SRCBLEND),link=False) as (src,dst):dst.collections=[pid]
    col=dst.collections[0];sc.collection.children.link(col)
    meshes=[o for o in col.all_objects if o.type=='MESH']
    def sel(*obs):
        bpy.ops.object.select_all(action='DESELECT')
        for o in obs:o.select_set(True)
        bpy.context.view_layer.objects.active=obs[0]
    # bake world transforms into mesh data, unparent
    bpy.context.view_layer.update();root=bpy.data.objects[f'{pid}_GroundOrigin'];Minv=root.matrix_world.inverted()
    mws={o.name:Minv@o.matrix_world for o in col.all_objects}   # every world matrix, relative to the prop's ground origin, before touching parents
    def pivot_of(o):
        q=o.parent
        while q:
            if 'Pivot' in q.name:return q.name
            q=q.parent
    pivots={o.name:pivot_of(o) for o in meshes}
    for o in col.all_objects:o.parent=None
    for o in col.all_objects:o.matrix_world=mws[o.name]
    sel(*meshes);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    empties=[o for o in col.all_objects if o.type=='EMPTY']   # sockets, pivots and the ground origin are interfaces: kept
    pivot_names=sorted({v for v in pivots.values() if v})
    for o in meshes:  # face attribute: 0 = fixed body, n = n-th pivot group
        a=o.data.attributes.new('grp','INT','FACE');g=pivot_names.index(pivots[o.name])+1 if pivots[o.name] else 0
        a.data.foreach_set('value',[g]*len(o.data.polygons))
    static=[o for o in meshes if not is_state(o,pid)];state=[o for o in meshes if is_state(o,pid)]
    # ---------- tiled source materials ----------
    imgs={k:bpy.data.images.load(str(TEX0/f'C01_{k}_albedo.png')) for k in ('wood','bronze','stone','hemp')}
    nrms={k:bpy.data.images.load(str(TEX0/f'C01_{k}_normal.png')) for k in ('wood','bronze','stone','hemp')}
    for im in nrms.values():im.colorspace_settings.name='Non-Color'
    srcmat={}
    def tiled(name):
        if name in srcmat:return srcmat[name]
        fam,tint,rough,metal=FAM.get(name,('wood',(1,1,1),.75,0))
        m=bpy.data.materials.new('src_'+name);m.use_nodes=True;nt=m.node_tree;bs=nt.nodes['Principled BSDF']
        bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
        uvn=nt.nodes.new('ShaderNodeUVMap');uvn.uv_map='Tiled'
        if fam=='paint':
            bs.inputs['Base Color'].default_value=(*tint,1);nk='wood'
        else:
            t=nt.nodes.new('ShaderNodeTexImage');t.image=imgs[fam];nt.links.new(uvn.outputs['UV'],t.inputs['Vector'])
            mx=nt.nodes.new('ShaderNodeMix');mx.data_type='RGBA';mx.blend_type='MULTIPLY';mx.inputs['Factor'].default_value=1
            nt.links.new(t.outputs['Color'],mx.inputs[6]);mx.inputs[7].default_value=(*tint,1);nt.links.new(mx.outputs[2],bs.inputs['Base Color']);nk=fam
        tn=nt.nodes.new('ShaderNodeTexImage');tn.image=nrms[nk];nt.links.new(uvn.outputs['UV'],tn.inputs['Vector'])
        nm=nt.nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.8;nt.links.new(tn.outputs['Color'],nm.inputs['Color']);nt.links.new(nm.outputs['Normal'],bs.inputs['Normal'])
        srcmat[name]=(m,metal);return srcmat[name]
    def project(o):
        """world-scale box projection; grain (V) follows the part's longest axis"""
        bm=bmesh.new();bm.from_mesh(o.data);uv=bm.loops.layers.uv.get('Tiled') or bm.loops.layers.uv.new('Tiled')
        pts=np.array([v.co[:] for v in bm.verts]);c=pts.mean(0);u,s,vt=np.linalg.svd(pts-c,full_matrices=False) if len(pts)>2 else (0,0,np.eye(3))
        A,S1,S2=[Vector(v) for v in vt]
        for f in bm.faces:
            n=f.normal;k=int(np.argmax([abs(n.dot(A)),abs(n.dot(S1)),abs(n.dot(S2))]))
            for l in f.loops:
                p=l.vert.co-Vector(c);l[uv].uv={0:(p.dot(S1),p.dot(S2)),1:(p.dot(S2),p.dot(A)),2:(p.dot(S1),p.dot(A))}[k]
                l[uv].uv=(l[uv].uv[0]/.5,l[uv].uv[1]/.5)
        bm.to_mesh(o.data);bm.free();o.data.uv_layers['Tiled'].active_render=True
    lod1_src=[]
    for o in static:
        for i,m in enumerate(o.data.materials):o.data.materials[i]=tiled(base(m.name))[0]
        for u in [u for u in o.data.uv_layers if u.name!='Tiled']:o.data.uv_layers.remove(u)
        project(o)
        d=o.copy();d.data=o.data.copy();sc.collection.objects.link(d);lod1_src.append(d)   # clean v001 geometry for LOD1
        dims=sorted(o.dimensions);w=min(.006,dims[0]*.18,dims[1]*.18)
        if w>.0008 and len(o.data.polygons)<4000:
            bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=1e-6);bm.to_mesh(o.data);bm.free()
            md=o.modifiers.new('worn','BEVEL');md.width=w;md.segments=2;md.limit_method='ANGLE';md.angle_limit=math.radians(40);md.use_clamp_overlap=True;md.harden_normals=False
            sel(o);bpy.ops.object.modifier_apply(modifier=md.name)
    def join(obs,name):
        cp=[]
        for o in obs:d=o.copy();d.data=o.data.copy();sc.collection.objects.link(d);cp.append(d)
        sel(*cp);bpy.ops.object.join();j=bpy.context.object;j.name=name;j.data.name=name
        bm=bmesh.new();bm.from_mesh(j.data);bmesh.ops.triangulate(bm,faces=bm.faces);bm.to_mesh(j.data);bm.free();return j
    L0=join(static,f'{pid}_LOD0');L1=join(lod1_src,f'{pid}_LOD1')
    for o in static+lod1_src:bpy.data.objects.remove(o)
    # ---------- unique UV + bake (only LOD0 visible) ----------
    for o in sc.objects:o.hide_render=o is not L0
    sel(L0);bu=L0.data.uv_layers.new(name='Bake');L0.data.uv_layers.active=bu
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60),island_margin=.004,area_weight=0,scale_to_bounds=False);bpy.ops.uv.pack_islands(margin=.004,rotate=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    mats=list(L0.data.materials)
    def target(name,data=False):
        im=bpy.data.images.new(name,RES,RES,alpha=False,float_buffer=data)
        for m in mats:
            nt=m.node_tree;t=nt.nodes.get('BAKE_TARGET') or nt.nodes.new('ShaderNodeTexImage');t.name='BAKE_TARGET';t.image=im;nt.nodes.active=t
        return im
    def bake(name,type,data=False,**kw):
        im=target(name,data);sel(L0);bpy.ops.object.bake(type=type,**kw);return np.array(im.pixels[:],dtype=np.float32).reshape(RES,RES,4)
    def emit(fn):
        saved=[]
        for m in mats:
            nt=m.node_tree;out=next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL');old=out.inputs['Surface'].links[0].from_socket
            em=nt.nodes.new('ShaderNodeEmission');fn(nt,m,em);nt.links.new(em.outputs[0],out.inputs['Surface']);saved.append((nt,out,old,em))
        return saved
    def restore(s):
        for nt,out,old,em in s:nt.links.new(old,out.inputs['Surface']);nt.nodes.remove(em)
    albedo=bake('alb','DIFFUSE',pass_filter={'COLOR'})
    sc.cycles.samples=64;ao=bake('ao','AO',True)[...,0];sc.cycles.samples=16
    rough=bake('rough','ROUGHNESS',True)[...,0];nrm=bake('nrm','NORMAL',True,normal_space='TANGENT')
    metalv={m.name:v for m,v in srcmat.values()}
    s=emit(lambda nt,m,em:em.inputs['Color'].__setattr__('default_value',(metalv.get(m.name,0),)*3+(1,)));metal=bake('metal','EMIT',True)[...,0];restore(s)
    def edges(nt,m,em):
        g=nt.nodes.new('ShaderNodeNewGeometry');r=nt.nodes.new('ShaderNodeValToRGB');r.color_ramp.elements[0].position=.53;r.color_ramp.elements[1].position=.62
        nt.links.new(g.outputs['Pointiness'],r.inputs['Fac']);nt.links.new(r.outputs['Color'],em.inputs['Color'])
    s=emit(edges);edge=bake('edge','EMIT',True)[...,0];restore(s)
    s=emit(lambda nt,m,em:nt.links.new(nt.nodes.new('ShaderNodeNewGeometry').outputs['Position'],em.inputs['Color']));pos=bake('pos','EMIT',True)[...,:3];restore(s)
    filled=np.abs(pos).sum(2)>1e-6;px,py,pz=pos[...,0],pos[...,1],pos[...,2]
    def smooth(a,lo,hi):return np.clip((a-lo)/(hi-lo),0,1)
    col=albedo[...,:3]*(.62+.38*ao[...,None])
    wear=np.clip(edge,0,1)[...,None]*(1-.6*metal[...,None]);col=np.clip(col*(1+.45*wear)+wear*np.array([.05,.035,.015]),0,1)
    zmin=pz[filled].min() if filled.any() else 0
    mudn=np.clip(np.sin(px*90)*np.sin(py*83)*.5+.5+.3*np.sin((px+py)*240),0,1)
    mud=filled*smooth(zmin+.12-pz,0,.09)*np.clip(.5+.6*mudn,0,1)*(metal<.01)
    col=col*(1-mud[...,None])+np.array([.25,.20,.14])*mud[...,None]*(.85+.2*mudn[...,None]);rough=np.clip(rough+.08*mud,0,1)
    def save(name,rgba,data=False):
        im=bpy.data.images.new(name,RES,RES,alpha=True)
        if data:im.colorspace_settings.name='Non-Color'   # before writing: changing it later blanks the buffer
        im.pixels.foreach_set(np.ascontiguousarray(rgba,dtype=np.float32).ravel());im.filepath_raw=str(TEX/f'{name}.png');im.file_format='PNG';im.save();return im
    one=np.ones((RES,RES),np.float32)
    ALB=save(f'{pid}_v002_Albedo',np.dstack([col,one]));NRM=save(f'{pid}_v002_Normal',nrm,True)
    save(f'{pid}_v002_MaskURP',np.dstack([metal,ao,0*one,1-rough]),True);ORM=save(f'{pid}_v002_ORM',np.dstack([ao,rough,metal,one]),True)
    fm=bpy.data.materials.new(f'{pid}_Baked');fm.use_nodes=True;nt=fm.node_tree;bs=nt.nodes['Principled BSDF']
    def tex(im):t=nt.nodes.new('ShaderNodeTexImage');t.image=im;return t
    nt.links.new(tex(ALB).outputs['Color'],bs.inputs['Base Color'])
    nm=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(tex(NRM).outputs['Color'],nm.inputs['Color']);nt.links.new(nm.outputs['Normal'],bs.inputs['Normal'])
    sp=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(tex(ORM).outputs['Color'],sp.inputs['Color']);nt.links.new(sp.outputs['Green'],bs.inputs['Roughness']);nt.links.new(sp.outputs['Blue'],bs.inputs['Metallic'])
    # ---------- LODs: LOD1 = clean v001, LOD2 ≈ 15 % of LOD0 ----------
    t0=len(L0.data.polygons)
    L2=L1.copy();L2.data=L1.data.copy();sc.collection.objects.link(L2);L2.name=L2.data.name=f'{pid}_LOD2'
    r=min(1,.15*t0/max(1,len(L2.data.polygons)));md=L2.modifiers.new('d','DECIMATE');md.ratio=r;md.use_collapse_triangulate=True;sel(L2);bpy.ops.object.modifier_apply(modifier='d')
    for d in (L1,L2):
        d.data.uv_layers.new(name='Bake');sel(d);md=d.modifiers.new('uv','DATA_TRANSFER');md.object=L0;md.use_loop_data=True;md.data_types_loops={'UV'}
        md.layers_uv_select_src='Bake';md.layers_uv_select_dst='Bake';md.loop_mapping='POLYINTERP_NEAREST';bpy.ops.object.modifier_apply(modifier=md.name)
    for d in (L0,L1,L2):
        uvs=d.data.uv_layers;uvs.remove(uvs['Tiled']);uvs['Bake'].name='UVMap';d.data.materials.clear();d.data.materials.append(fm);d.hide_render=False
    root.matrix_world=Matrix();emp={o.name:o for o in empties}
    def split(o,L):
        """separate pivot groups so the panel can still turn; returns the new objects"""
        g=np.zeros(len(o.data.polygons),np.int32);o.data.attributes['grp'].data.foreach_get('value',g);res=[]
        for gi in sorted(set(g.tolist())):
            if gi==0 and len(set(g.tolist()))==1:o.name=o.data.name=f'{pid}_LOD{L}';res.append(o);break
            bm=bmesh.new();bm.from_mesh(o.data);lay=bm.faces.layers.int['grp']
            bmesh.ops.delete(bm,geom=[f for f in bm.faces if f[lay]!=gi],context='FACES')
            nm=f'{pid}_LOD{L}' if gi==0 else f'{pid}_{pivot_names[gi-1]}_LOD{L}'
            me=bpy.data.meshes.new(nm);bm.to_mesh(me);bm.free();me.materials.append(fm);n=bpy.data.objects.new(nm,me);sc.collection.objects.link(n)
            if gi:pv=emp[pivot_names[gi-1]];n.parent=pv;n.matrix_parent_inverse=pv.matrix_world.inverted()
            res.append(n)
        else:bpy.data.objects.remove(o)
        return res
    lodparts={L:split(o,L) for L,o in enumerate((L0,L1,L2))}
    # state parts keep their v001 names (the PWA looks them up); LOD1/LOD2 copies get a suffix
    stobs={0:list(state),1:[],2:[]}
    for L in (1,2):
        for o in state:
            d=o.copy();d.data=o.data.copy();sc.collection.objects.link(d);d.name=o.name+f'_LOD{L}';stobs[L].append(d)
    for o in empties:
        if o is not root and o.parent is None:o.parent=root
    for L in (0,1,2):
        for o in lodparts[L]+stobs[L]:
            if o.parent is None:o.parent=root
            o.hide_render=L>0
    # collider proxy: box around LOD0
    pts=np.array([(o.matrix_world@v.co)[:] for o in lodparts[0] for v in o.data.vertices]);lo,hi=pts.min(0),pts.max(0)
    bm=bmesh.new();bmesh.ops.create_cube(bm,size=1)
    for v in bm.verts:v.co=Vector([(lo[i]+hi[i])/2+v.co[i]*(hi[i]-lo[i]) for i in range(3)])
    cm=bpy.data.meshes.new(f'{pid}_Collider');bm.to_mesh(cm);bm.free();colo=bpy.data.objects.new(f'{pid}_Collider',cm);sc.collection.objects.link(colo);colo.parent=root;colo.hide_render=True
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/f'{pid}_v002.blend'))
    sel(root,*empties,*lodparts[0],*stobs[0]);bpy.ops.export_scene.gltf(filepath=str(OUT/f'{pid}_v002.glb'),use_selection=True,export_format='GLB',export_apply=True)
    sel(root,*empties,*[o for L in (0,1,2) for o in lodparts[L]+stobs[L]],colo)
    bpy.ops.export_scene.fbx(filepath=str(OUT/f'{pid}_v002.fbx'),use_selection=True,object_types={'MESH','EMPTY'},global_scale=1.0,apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_ALL',bake_space_transform=True,axis_forward='-Z',axis_up='Y',use_mesh_modifiers=True,mesh_smooth_type='FACE',
        use_tspace=True,add_leaf_bones=False,bake_anim=False,path_mode='RELATIVE',embed_textures=False)
    def tris(o):return sum(len(p.vertices)-2 for p in o.data.polygons)
    T={L:sum(tris(o) for o in lodparts[L]+stobs[L]) for L in (0,1,2)}
    info={'id':pid,'source':'WaterReportC_variants.blend (v001, from saved AI three-views)','dimensions_xyz_m':[round(float(x),4) for x in hi-lo],
          'origin':'ground centre (v001 GroundOrigin)','triangles':{f'LOD{L}':T[L] for L in T},'lod_ratio':[1,round(T[1]/T[0],2),round(T[2]/T[0],2)],
          'materials':1+len({m.name for o in state for m in o.data.materials}),'state_parts':sorted(o.name for o in state),
          'interfaces':sorted(o.name for o in empties),'pivot_groups':pivot_names,
          'collision':{'shape':'box','size_m':[round(float(x),3) for x in hi-lo]},'textures':f'{RES}² Albedo/Normal/MaskURP/ORM'}
    print('PROP_DONE',json.dumps(info,ensure_ascii=False));return info
infos=[run(i) for i in IDS]
mf=OUT/'v002-manifest.json';old=json.loads(mf.read_text(encoding='utf-8')) if mf.exists() else {}
old.update({i['id']:i for i in infos});mf.write_text(json.dumps(old,ensure_ascii=False,indent=1),encoding='utf-8')
