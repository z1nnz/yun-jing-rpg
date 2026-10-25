"""Qingxi giant tree v1 (LOD0) from the AI three-view art/references/qingxi-town-v1/giant-tree/three-view.png.

  blender --background --factory-startup --python-exit-code 1 --python tools/build-giant-tree.py
  blender --background --factory-startup --python-exit-code 1 --python tools/validate-giant-tree.py

The three-view's drawn proportions disagree with its own dimension notes; the user chose the notes: 62 m tall, crown
90 m wide (X) by 70 m deep (Y), trunk 10 m across at 3 m, root flare 22 m, trunk split at about 18 m, crown underside about
26 m. Shapes (V split, long level side limbs, forward-leaning upper tree, 15 leaf clumps, hanging moss, boulders gripped by
buttress roots) follow the drawing. Procedural and seeded; metres, Z up, front -Y, origin at the base centre.
Writes art/source/giant-tree-v1.blend, art/exports/giant-tree-v1/{giant-tree.glb,giant-tree.fbx,report.json} and ten
1024 px views in art/previews/giant-tree-v1/. Rebuilding overwrites these generated files; keep hand edits in a new version.
"""
import bpy,bmesh,json,math,random,os
from pathlib import Path
from mathutils import Vector,Matrix
REPO=Path(__file__).resolve().parents[1];NAME='giant-tree'
BLEND=REPO/'art/source/giant-tree-v1.blend';EXP=REPO/'art/exports/giant-tree-v1';PREV=REPO/'art/previews/giant-tree-v1'
REF=REPO/'art/references/qingxi-town-v1/giant-tree/three-view.png'
assert REF.exists(),'the three-view must be saved before modelling (AGENTS.md)'
rng=random.Random(62)

bpy.ops.wm.read_factory_settings(use_empty=True);S=bpy.context.scene;S.unit_settings.system='METRIC'
ASSET=bpy.data.collections.new('01_Giant_Tree');S.collection.children.link(ASSET)
STUDIO=bpy.data.collections.new('90_Studio_Not_Exported');S.collection.children.link(STUDIO)
ROOT=bpy.data.objects.new('GiantTree_ROOT',None);ASSET.objects.link(ROOT)

MATS={}
def mat(name,c,rough=.85):
    if name not in MATS:
        m=bpy.data.materials.new(name);m.use_nodes=True;b=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        b.inputs['Base Color'].default_value=(*c,1);b.inputs['Roughness'].default_value=rough;b.inputs['Specular IOR Level'].default_value=.15
        m.diffuse_color=(*c,1);m.use_backface_culling=False;MATS[name]=m
    return MATS[name]
BARK=mat('Tree_Bark',(.24,.16,.10));MOSS=mat('Tree_Moss',(.20,.33,.07));LEAF_L=mat('Tree_Leaf_Light',(.34,.55,.10))
LEAF_D=mat('Tree_Leaf_Dark',(.08,.22,.06));LEAF_M=mat('Tree_Leaf_Mid',(.18,.38,.08));HANG=mat('Tree_HangingMoss',(.36,.48,.10));ROCK=mat('Tree_Rock',(.30,.30,.27))

def obj(name,bm,mats,smooth=True):
    me=bpy.data.meshes.new(name);bm.to_mesh(me);bm.free()
    for m in mats:me.materials.append(m)
    for p in me.polygons:p.use_smooth=smooth
    o=bpy.data.objects.new(name,me);ASSET.objects.link(o);o.parent=ROOT;return o

# ------------------------------------------------------------------ swept tubes
def spline(pts,n):
    """Uniform Catmull-Rom through control points, n samples."""
    P=[Vector(p) for p in pts];P=[P[0]+(P[0]-P[1])]+P+[P[-1]+(P[-1]-P[-2])];out=[]
    for i in range(n):
        t=i/(n-1)*(len(P)-3);k=min(int(t),len(P)-4);u=t-k;p0,p1,p2,p3=P[k:k+4]
        out.append(.5*((2*p1)+(-p0+p2)*u+(2*p0-5*p1+4*p2-p3)*u*u+(-p0+3*p1-3*p2+p3)*u**3))
    return out
def lerp_list(vals,n):
    return [vals[min(int(t),len(vals)-2)]+(vals[min(int(t),len(vals)-2)+1]-vals[min(int(t),len(vals)-2)])*(t-min(int(t),len(vals)-2)) for t in [i/(n-1)*(len(vals)-1) for i in range(n)]]
def tube(bm,pts,radii,n,segs,flutes=0,famp=0.,twist=0.,flat=1.,cap=True,start_cap=False,up=Vector((0,0,1))):
    """Tube along a spline with parallel-transport frames. flutes/famp: bark ridges, twisting by `twist` rad per metre.
    flat < 1 squashes the section across the path's side axis (buttress roots: tall and thin)."""
    path=spline(pts,n);R=lerp_list(radii,n);rings=[];s=0.
    t0=(path[1]-path[0]).normalized();N=(up-t0*up.dot(t0));N=N.normalized() if N.length>1e-4 else t0.orthogonal().normalized()
    for i,p in enumerate(path):
        t=((path[min(i+1,n-1)]-path[max(i-1,0)])).normalized()
        if i:N=(N-t*N.dot(t)).normalized();s+=(p-path[i-1]).length
        B=t.cross(N);ring=[]
        for j in range(segs):
            a=2*math.pi*j/segs;r=R[i]*(1+famp*math.sin(flutes*a+twist*s)+.035*math.sin(3*a+.7*s))
            ring.append(bm.verts.new(p+N*(math.cos(a)*r)+B*(math.sin(a)*r*flat)))
        rings.append(ring)
    for a,b in zip(rings,rings[1:]):
        for j in range(segs):bm.faces.new((a[j],a[(j+1)%segs],b[(j+1)%segs],b[j]))
    if cap:bm.faces.new(list(reversed(rings[-1])))
    if start_cap:bm.faces.new(rings[0])
    return path,R

# ------------------------------------------------------------------ trunk: three intertwined stems that become the main limbs
LEAN=lambda z:Vector((0,-4.5*(min(z,19)/19)**1.4,0))      # upper trunk leans forward (-Y), RIGHT SIDE view
def helix(k,z):
    a=2*math.pi*k/3+math.radians(200)*z/18;rh=2.2-.4*z/18
    return Vector((math.cos(a)*rh,math.sin(a)*rh,z))+LEAN(z)
LIMBS={   # control points after the split (m) and radii; these three continue the trunk stems
 'up_left':  ([(-6,-6,26),(-12,-5,36),(-17,-4,46),(-19,-3,53)],[3.6,2.7,1.6,.6]),
 'up_right': ([(6,-8,27),(10,-10,38),(13,-12,48),(14,-12,55)],[3.6,2.7,1.6,.6]),
 'front':    ([(-3,-14,24),(-5,-24,27),(-6,-33,30)],[2.5,1.4,.5])}
BRANCH={  # limbs leaving the stems near the split
 'side_left': ([(-2,-3,16),(-12,-2,23),(-24,-1,27),(-35,0,29),(-42,-1,28)],[3.3,2.3,1.5,.8,.35]),
 'side_right':([(2,-3.5,16),(13,-4,23),(25,-4,27),(36,-3,29),(43,-2,28)],[3.3,2.3,1.5,.8,.35]),
 'back':     ([(0,-2,17),(2,6,27),(3,15,33),(4,22,37)],[2.2,1.4,.8,.35])}
bm=bmesh.new();paths={}
tube(bm,[Vector((0,0,z))+LEAN(z) for z in (0,4,10,16)],[4.2,3.8,3.7,3.5],20,24,flutes=11,famp=.12,twist=.1,start_cap=True)   # core
for k,name in enumerate(('up_left','up_right','front')):
    pts,rad=LIMBS[name];stem=[helix(k,z) for z in (0,4.5,9,13.5,18)]
    paths[name]=tube(bm,stem+[Vector(p) for p in pts],[3.0,3.1,3.2,3.4,3.6]+rad,44,18,flutes=7,famp=.10,twist=.14)
for name,(pts,rad) in BRANCH.items():paths[name]=tube(bm,pts,rad,26,16,flutes=6,famp=.08,twist=.12)
trunk_bm=bm

# ------------------------------------------------------------------ crown: 15 clumps filling the noted 90 x 70 m envelope
CLUMPS=[(-36.3,-2,32,10,6),(36.3,-4,32,10,6),(-22,-17,40,12,7),(22,-18,40,12,7),(-22,13,39,12,7),(22,11,39,12,7),
        (0,-27,35,11,6.5),(0,22,37,11,6.5),(-10,-5,49,13,8),(11,-6,49,13,8),(0,5,54,12,8),
        (-32,-20,33,8,5),(32,-21,33,8,5),(-31,15,31,8,5),(31,14,31,8,5)]   # (x, y, z centre, horizontal radius, vertical half-height)
def nearest_on_limbs(p):
    best=None
    for k,(path,R) in paths.items():
        for q,r in zip(path,R):
            d=(q-p).length
            if best is None or d<best[0]:best=(d,q,r)
    return best
for x,y,z,R,h in CLUMPS:    # secondary branch from the nearest limb into the clump's underside
    c=Vector((x,y,z-h*.5));d,q,r=nearest_on_limbs(c);mid=q.lerp(c,.5)+Vector((0,0,1.5))
    tube(trunk_bm,[q,mid,c],[min(r,1.1)*.9,.6,.28],10,8,flutes=0)
bmesh.ops.recalc_face_normals(trunk_bm,faces=trunk_bm.faces)
for f in trunk_bm.faces:   # moss on the lower trunk and on upward-facing limb tops
    c=f.calc_center_median();n=f.normal
    f.material_index=1 if (c.z<14 and math.sin(c.x*.9)*math.cos(c.y*.8+c.z*.35)>.3) or (n.z>.6 and c.z>8) else 0
trunk=obj('Tree_Trunk_Limbs',trunk_bm,[BARK,MOSS])

def lumpy_blob(bm,c,rx,ry,rz,sub=2,amp=.10):
    g=bmesh.ops.create_icosphere(bm,subdivisions=sub,radius=1,matrix=Matrix.Translation(c)@Matrix.Diagonal((rx,ry,rz,1)))
    ph=rng.uniform(0,6.28)
    for v in g['verts']:
        d=(v.co-c);u=Vector((d.x/rx,d.y/ry,d.z/rz))
        v.co=c+d*(1+amp*math.sin(5*u.x+ph)*math.sin(5*u.y+ph*.7)+amp*.6*math.sin(9*u.z+ph))
    return g['verts']
for i,(x,y,z,R,h) in enumerate(CLUMPS,1):   # a tiered cluster of small leaf puffs: wide lower shelf, smaller top
    bm=bmesh.new();C=Vector((x,y,z));placed=[];tone=bm.verts.layers.int.new('tone')   # one tone per puff: 0 light, 1 mid, 2 dark
    for tier,(zf,rf,cnt) in enumerate(((-.25,1.,int(R*1.1)),(.25,.7,int(R*.7)),(.6,.35,3))):
        for j in range(cnt):
            for _ in range(30):
                a=rng.uniform(0,6.28);d=math.sqrt(rng.uniform(0,1))*R*rf*.82
                p=C+Vector((math.cos(a)*d,math.sin(a)*d,zf*h+rng.uniform(-.15,.15)*h));pr=rng.uniform(.24,.34)*R
                if all((p-q).length>(pr+qr)*.55 for q,qr in placed):break
            placed.append((p,pr));t=[2,1,0][tier] if rng.random()<.75 else rng.choice((0,1,2))
            for v in lumpy_blob(bm,p,pr,pr,pr*.72,sub=1 if pr<2.4 else 2,amp=.12):v[tone]=t
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
    for f in bm.faces:f.material_index=f.verts[0][tone]   # per puff, not per face: per-face switching read as facets
    obj(f'Tree_Leaf_Clump_{i:02d}',bm,[LEAF_L,LEAF_M,LEAF_D])

# ------------------------------------------------------------------ hanging moss curtains from the level limbs and clump undersides
bm=bmesh.new()
def strand(p,L,w):
    yaw=rng.uniform(0,math.pi);side=Vector((math.cos(yaw),math.sin(yaw),0));sway=Vector((-side.y,side.x,0))*rng.uniform(-.8,.8);prev=None
    for t in range(8):
        f=t/7;c=p+Vector((0,0,-L*f))+sway*f*f;wv=side*(w*(1-.75*f)/2)
        cur=(bm.verts.new(c-wv),bm.verts.new(c+wv))
        if prev:bm.faces.new((prev[0],prev[1],cur[1],cur[0]))
        prev=cur
for k in ('side_left','side_right','front','back'):
    path,R=paths[k]
    for q,r in list(zip(path,R))[5:]:
        for _ in range(3):strand(q+Vector((rng.uniform(-1.2,1.2),rng.uniform(-1.2,1.2),-r*.8)),rng.uniform(5,10),rng.uniform(.5,.9))
for x,y,z,R,h in CLUMPS:
    if z<42:
        for _ in range(5):
            a=rng.uniform(0,6.28);d=rng.uniform(.3,.85)*R;strand(Vector((x+math.cos(a)*d,y+math.sin(a)*d,z-h*.45)),rng.uniform(4,9),rng.uniform(.45,.75))
obj('Tree_HangingMoss',bm,[HANG],smooth=False)

# ------------------------------------------------------------------ buttress roots gripping large mossy boulders, ivy
bm=bmesh.new()
for a,r,s_ in ((.55,11.6,3.0),(1.6,12.2,3.6),(2.6,11.4,2.6),(3.7,12.4,3.4),(4.7,11.8,2.8),(5.7,12.0,3.2)):   # between the root ends, roots stay visible
    lumpy_blob(bm,Vector((math.cos(a)*r,math.sin(a)*r,s_*.62)),s_*1.05,s_*.95,s_*.95,sub=3,amp=.12)
bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
for f in bm.faces:f.material_index=1 if f.normal.z>.45 else 0
obj('Tree_Boulders',bm,[ROCK,MOSS])
bm=bmesh.new()
for i in range(12):
    a=2*math.pi*i/12+rng.uniform(-.12,.12);reach=rng.uniform(10.2,11.4)
    P=lambda r,z,a=a:(math.cos(a)*r,math.sin(a)*r,z)
    tube(bm,[P(3.2,8.),P(5.8,4.2),P(8.4,2.2),P(reach,.3)],[2.7,1.9,1.0,.3],14,10,flutes=3,famp=.08,flat=.5,up=Vector((0,0,1)))
bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
for f in bm.faces:f.material_index=1 if f.normal.z>.7 else 0
obj('Tree_Roots',bm,[BARK,MOSS])
bm=bmesh.new()
for i in range(44):
    z=rng.uniform(2,17);a=rng.uniform(0,6.28);r=5.0-z*.08;c=Vector((math.cos(a)*r,math.sin(a)*r,z))+LEAN(z)
    lumpy_blob(bm,c,rng.uniform(.6,1.3),rng.uniform(.6,1.3),rng.uniform(.5,.9),sub=1)
obj('Tree_Ivy',bm,[MOSS])
for o in ASSET.objects:   # nothing below the ground plane
    if o.type=='MESH':
        for v in o.data.vertices:v.co.z=max(v.co.z,0.)

# ------------------------------------------------------------------ measure, studio, ten views, exports
objs=[o for o in ASSET.objects if o.type=='MESH']
def bounds(objs):
    pts=[o.matrix_world@v.co for o in objs for v in o.data.vertices]
    return Vector([min(p[i] for p in pts) for i in range(3)]),Vector([max(p[i] for p in pts) for i in range(3)])
lo,hi=bounds(objs);size=hi-lo
tris=sum(len(p.vertices)-2 for o in objs for p in o.data.polygons)
foliage=[o for o in objs if o.name.startswith('Tree_Leaf_Clump')];flo,fhi=bounds(foliage)
tv=[v.co for v in trunk.data.vertices if 2.6<v.co.z<3.4 and abs(v.co.x)<9 and abs(v.co.y)<9]
trunk_d=max(v.x for v in tv)-min(v.x for v in tv)
measure={'size_m':list(size),'bounds_min_m':list(lo),'bounds_max_m':list(hi),'triangles':tris,'objects':[o.name for o in objs],
         'trunk_width_at_3m':trunk_d,'crown_underside_m':flo.z,'crown_width_x_m':fhi.x-flo.x,'crown_depth_y_m':fhi.y-flo.y,
         'materials':sorted(MATS)}
print('MEASURE',json.dumps({k:v for k,v in measure.items() if k!='objects'}),flush=True)

w=bpy.data.worlds.new('Studio');w.use_nodes=True;S.world=w;bg=next(n for n in w.node_tree.nodes if n.type=='BACKGROUND')
bg.inputs[0].default_value=(.72,.74,.72,1);bg.inputs[1].default_value=.35
centre=(lo+hi)/2;ext=max(size)
for nm,d,p in (('Key',(-.8,-1.2,1.1),900),('Fill',(1.2,-.6,.6),420),('Rim',(.3,1.2,1.),650)):
    l=bpy.data.lights.new(nm,'AREA');l.energy=p*ext*ext/2.2*.3;l.size=ext*.9;l.shape='DISK'
    o=bpy.data.objects.new(nm,l);STUDIO.objects.link(o);o.location=centre+Vector(d)*ext*1.6;o.rotation_euler=(centre-o.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.objects.new('Cam',bpy.data.cameras.new('Cam'));STUDIO.objects.link(cam);S.camera=cam;cam.data.type='ORTHO';cam.data.clip_end=2000
for eng in ('CYCLES',):
    S.render.engine=eng
S.cycles.device='CPU';S.cycles.samples=48;S.cycles.use_denoising=True;S.view_settings.view_transform='AgX';S.view_settings.exposure=-.9
PREVIEW=os.environ.get('TREE_PREVIEW')   # quick look: front / right / top only, nothing saved or exported
if PREVIEW:VIEWS_ONLY={'01_front','02_right','09_top'};S.cycles.samples=16;PREV=Path(PREVIEW)
S.render.resolution_x=S.render.resolution_y=1024;S.render.image_settings.file_format='PNG'
VIEWS=[('01_front',(0,-1,0)),('02_right',(1,0,0)),('03_rear',(0,1,0)),('04_left',(-1,0,0)),('05_front_right',(1,-1,.45)),
       ('06_rear_right',(1,1,.45)),('07_rear_left',(-1,1,.45)),('08_front_left',(-1,-1,.45)),('09_top',(0,0,1)),('10_high_front',(0,-1,1))]
from bpy_extras.object_utils import world_to_camera_view
corners=[Vector((x,y,z)) for x in (lo.x,hi.x) for y in (lo.y,hi.y) for z in (lo.z,hi.z)]
PREV.mkdir(parents=True,exist_ok=True);views=[]
for name,d in VIEWS:
    if PREVIEW and name not in VIEWS_ONLY:continue
    D=Vector(d).normalized();cam.location=centre+D*400;cam.rotation_euler=(-D).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
    sc=.5
    while True:
        cam.data.ortho_scale=sc;bpy.context.view_layer.update();pr=[world_to_camera_view(S,cam,p) for p in corners]
        if all(.04<p.x<.96 and .04<p.y<.96 for p in pr):break
        sc*=1.03
    S.render.filepath=str(PREV/f'{name}.png');bpy.ops.render.render(write_still=True)
    views.append({'file':f'{name}.png','direction':list(d),'ortho_scale':sc});print('VIEW',name,flush=True)

if PREVIEW:raise SystemExit(0)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
EXP.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='DESELECT')
for o in objs:o.select_set(True)
bpy.context.view_layer.objects.active=objs[0]
bpy.ops.export_scene.gltf(filepath=str(EXP/f'{NAME}.glb'),export_format='GLB',use_selection=True,export_apply=True)
bpy.ops.export_scene.fbx(filepath=str(EXP/f'{NAME}.fbx'),use_selection=True,object_types={'MESH'},apply_unit_scale=True,axis_forward='-Z',axis_up='Y',
                         bake_anim=False,mesh_smooth_type='FACE',path_mode='RELATIVE')
(EXP/'report.json').write_text(json.dumps({'asset':NAME,'version':'v1','lod':0,'reference':str(REF.relative_to(REPO)).replace('\\','/'),
    'dimension_basis':'three-view dimension notes (user choice), not the drawn proportions','target':{'height_m':62,'crown_width_m':90,'crown_depth_m':70,
    'trunk_diameter_at_3m_m':10,'root_flare_m':22,'split_height_m':18,'crown_underside_m':26},'measured':measure,'views':views,
    'blender':bpy.app.version_string,'units':'metres, Z up, front -Y, origin base centre',
    'not_done':['LOD1','UV unwrap and texture bake (procedural colours only)','collision','wind animation','Unity import']},ensure_ascii=False,indent=2),encoding='utf-8')
print('DONE',tris,'tris',flush=True)
