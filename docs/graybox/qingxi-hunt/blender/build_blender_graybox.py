"""Blender copy of the Qingxi hunt graybox, built only from ../layout.json.

  blender --background --factory-startup --python-exit-code 1 --python docs/graybox/qingxi-hunt/blender/build_blender_graybox.py

Follows the same rules as apps/game/Assets/YunJing/Editor/QingxiHuntGrayboxBuilder.cs: a 5 m ground grid with the tent
hill, one box per obstacle, the shallow-water slab, 2 m route strips, marker discs and proxies, and the six camera
bookmarks. It is for looking at the layout and checking it in Blender; it is NOT the Unity scene and proves nothing about
NavMesh, CharacterController or phone cameras. Objects in 95_Preview_Only (zone outlines, big marker rings, flat labels)
exist only here, so the renders read at map scale.

Unity (x, y up, z north) -> Blender (X = x, Y = z, Z = y). Writes beside this file:
QingxiHuntGraybox_blockout.blend and renders/{birdseye,overview,view_01_exit..view_06_shortcut}.png.
"""
import bpy,bmesh,json,math,hashlib
from pathlib import Path
from mathutils import Vector,Matrix

HERE=Path(__file__).resolve().parent;LAYOUT=HERE.parent/'layout.json'
OUT_BLEND=HERE/'QingxiHuntGraybox_blockout.blend';RENDERS=HERE/'renders'
D=json.loads(LAYOUT.read_text(encoding='utf-8'));SHA=hashlib.sha256(LAYOUT.read_bytes()).hexdigest()

def U(p):return Vector((p['x'],p['z'],p['y']))   # Unity point -> Blender
def ground(x,z):
    h=D['hill'];return h['height']*max(0,1-abs(x-h['centerX'])/h['halfWidth'])*max(0,1-abs(z-h['centerZ'])/h['halfDepth'])

bpy.ops.wm.read_factory_settings(use_empty=True);S=bpy.context.scene;S.unit_settings.system='METRIC'
S['layout_sha256']=SHA;S['source']='docs/graybox/qingxi-hunt/layout.json';S['unity_validated']=False
def coll(name,parent=None):
    c=bpy.data.collections.new(name);(parent or S.collection).children.link(c);return c
ROOT=coll('QingxiHuntGraybox_ROOT')
C_GROUND,C_AREAS,C_COLL,C_WATER,C_ROUTES,C_MARK,C_CAMS=(coll(n,ROOT) for n in
    ('10_Ground','20_Areas','30_SimplifiedColliders','40_Water','50_RouteReferences_no_countdown_no_arrows','60_Markers','90_CameraBookmarks_3.5_to_6m'))
C_PREV=coll('95_Preview_Only')   # outside the ROOT: not part of the Unity scene

def srgb(c):return tuple(((v/12.92) if v<=.04045 else ((v+.055)/1.055)**2.4) for v in c)
MATS={}
def mat(name,rgb,alpha=1.,emit=0.):
    if name in MATS:return MATS[name]
    m=bpy.data.materials.new(name);m.use_nodes=True;b=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value=(*srgb(rgb),1);b.inputs['Roughness'].default_value=.85
    if alpha<1:
        b.inputs['Alpha'].default_value=alpha
        if hasattr(m,'surface_render_method'):m.surface_render_method='BLENDED'
    if emit:b.inputs['Emission Color'].default_value=(*srgb(rgb),1);b.inputs['Emission Strength'].default_value=emit
    m.diffuse_color=(*srgb(rgb),alpha);MATS[name]=m;return m
# Same colours as the Unity builder (sRGB values there).
M_GROUND=mat('Ground',(.35,.43,.36));M_CLIFF=mat('Cliff',(.42,.45,.46));M_TREE=mat('TreeProxy',(.21,.36,.29))
M_WATER=mat('WaterProxy',(.23,.54,.65));M_ROAD=mat('MainRoute',(.72,.61,.41));M_SHORT=mat('ReturnRoute',(.41,.66,.64))
MARKER_RGB={'player':(.4,.7,1),'rabbit':(1,.72,.3),'flee':(1,.4,.3),'herb':(.3,.9,.45),'merchant':(1,.85,.35)}
def marker_mat(kind):return mat('Marker_'+kind,MARKER_RGB.get(kind,(.65,.7,.7)))

def mesh_obj(name,bm,material,col):
    me=bpy.data.meshes.new(name);bm.to_mesh(me);bm.free();o=bpy.data.objects.new(name,me);col.objects.link(o)
    if material:me.materials.append(material)
    return o
def box_bm(bm,center,size,yaw=0.):
    """Axis box like a scaled Unity cube; yaw in radians about Blender Z."""
    r=bmesh.ops.create_cube(bm,size=1.)['verts']
    for v in r:
        v.co=Vector((v.co.x*size[0],v.co.y*size[1],v.co.z*size[2]))
        if yaw:v.co.rotate(Matrix.Rotation(yaw,3,'Z'))
        v.co+=center
def cyl_bm(bm,center,radius,depth,seg=16):
    bmesh.ops.create_cone(bm,cap_ends=True,segments=seg,radius1=radius,radius2=radius,depth=depth,
                          matrix=Matrix.Translation(center))
def capsule_bm(bm,base,radius,height,seg=16):
    """Unity capsule: total height includes both caps; base is the bottom point."""
    body=max(0.,height-2*radius);ring=6;verts=[]
    rows=[]
    for i in range(ring+1):   # bottom hemisphere
        a=-math.pi/2+math.pi/2*i/ring;rows.append((radius*math.cos(a),radius+radius*math.sin(a)))
    for i in range(ring+1):   # top hemisphere
        a=math.pi/2*i/ring;rows.append((radius*math.cos(a),radius+body+radius*math.sin(a)))
    for r_,z_ in rows:
        verts.append([bm.verts.new(base+Vector((max(r_,1e-4)*math.cos(2*math.pi*k/seg),max(r_,1e-4)*math.sin(2*math.pi*k/seg),z_))) for k in range(seg)])
    for a,b in zip(verts,verts[1:]):
        for k in range(seg):bm.faces.new((a[k],a[(k+1)%seg],b[(k+1)%seg],b[k]))
    bmesh.ops.remove_doubles(bm,verts=bm.verts[:],dist=1e-5)

# ------------------------------------------------------------------ ground: same 5 m grid and triangle order as the Builder
g=D['bounds']['grid'];nx=round(D['bounds']['width']/g);nz=round(D['bounds']['depth']/g)
verts=[(x*g,z*g,ground(x*g,z*g)) for z in range(nz+1) for x in range(nx+1)];tris=[]
for z in range(nz):
    for x in range(nx):
        a=z*(nx+1)+x;b=a+nx+1;tris+=[(a,a+1,b),(a+1,b+1,b)]   # Unity (a,b,a+1),(a+1,b,b+1) mirrored to Blender's winding
me=bpy.data.meshes.new('Ground_5m_grid');me.from_pydata(verts,[],tris);me.materials.append(M_GROUND)
GROUND=bpy.data.objects.new(f'Ground_{len(verts)}_vertices_{len(tris)}_triangles',me);C_GROUND.objects.link(GROUND)
GROUND['collider']='MeshCollider (only one in the scene)'

# ------------------------------------------------------------------ areas (empties sized like the zone, as the Builder's Area_* objects)
for z in D['zones']:
    e=bpy.data.objects.new(f"Area_{z['name']}_{z['width']}x{z['depth']}m",None);e.empty_display_type='CUBE'
    e.location=U(z['center']);e.scale=(z['width']/2,z['depth']/2,.5);e['label']=z['label'];C_AREAS.objects.link(e)

# ------------------------------------------------------------------ simplified colliders
KIND_MAT={'tree':M_TREE,'deepWater':M_WATER}
for o in D['obstacles']:
    bm=bmesh.new();s=o['size'];box_bm(bm,U(o['position']),(s['x'],s['z'],s['y']))
    ob=mesh_obj(o['name'],bm,KIND_MAT.get(o['kind'],M_CLIFF),C_COLL);ob['collider']='Box';ob['kind']=o['kind']
    if o['kind']=='boundary':ob.hide_render=True;ob.display_type='WIRE'
bm=bmesh.new();box_bm(bm,Vector((140,45,.06)),(40,30,.12))
w=mesh_obj('ShallowWater_depth_0.12m',bm,mat('ShallowWaterPreview',(.23,.54,.65),alpha=.55),C_WATER);w['collider']='none (walkable)'

# ------------------------------------------------------------------ route strips: ceil(length/2) boxes per segment, like the Builder
ROUTE_MAT={'AlternativeReturn':M_SHORT}
for r in D['routes']:
    if r['name'] not in ('MainDiscovery','AlternativeReturn','HerdConnector'):continue
    bm=bmesh.new()
    for a,b in zip(r['points'],r['points'][1:]):
        A,B=U(a),U(b);L=(B-A).length;steps=max(1,math.ceil(L/2));yaw=math.atan2(B.y-A.y,B.x-A.x)-math.pi/2
        for j in range(steps):
            p=A.lerp(B,(j+.5)/steps);p.z=ground(p.x,p.y)+.025
            box_bm(bm,p,(r['width'],L/steps+.05,.04),yaw)
    ob=mesh_obj(r['name'],bm,ROUTE_MAT.get(r['name'],M_ROAD),C_ROUTES);ob['collider']='none'

# ------------------------------------------------------------------ markers: empty with the exact name + Builder proxies
for m in D['markers']:
    P=U(m['position']);e=bpy.data.objects.new(m['name'],None);e.location=P;e.empty_display_size=.6;e['kind']=m['kind']
    e['group']=m['group'];e['note']=m['note'];C_MARK.objects.link(e)
    if m['kind'] in ('boundary','cameraBlocker'):
        if m['kind']=='boundary':e.empty_display_type='CUBE';e.scale=(D['bounds']['width']/2,D['bounds']['depth']/2,5)
        continue
    M=marker_mat(m['kind']);bm=bmesh.new();cyl_bm(bm,P+Vector((0,0,.04)),.3,.08)
    if m['kind']=='rabbit':capsule_bm(bm,P,.25,.8)
    if m['kind']=='player':capsule_bm(bm,P,.35,2.)
    if m['kind']=='clue':
        for j in range(4):box_bm(bm,P+Vector((-.15 if j%2==0 else .15,j*.3,.035)),(.12,.2,.035))
    proxy=mesh_obj(m['name']+'_proxy',bm,M,C_MARK);proxy.parent=e;proxy.matrix_parent_inverse=Matrix.Translation(-P)   # proxy verts are already in world space;proxy['collider']='none'

# ------------------------------------------------------------------ camera bookmarks: Builder CameraPosition()
cam_cfg=D['camera']
def cam_pos(v,dist):
    pitch=math.radians(cam_cfg['elevationDegrees']);yaw=math.radians(v['yaw'])
    fwd=Vector((math.sin(yaw),math.cos(yaw),0))   # Unity Quaternion.Euler(0,yaw,0)*forward in Blender axes
    tgt=U(v['target'])+Vector((0,0,cam_cfg['targetHeight']))
    return tgt-fwd*(dist*math.cos(pitch))+Vector((0,0,dist*math.sin(pitch))),tgt
def make_cam(name,loc,look,col,fov_v=60.,ortho=None):
    cd=bpy.data.cameras.new(name);cam=bpy.data.objects.new(name,cd);col.objects.link(cam);cam.location=loc
    cam.rotation_euler=(look-loc).to_track_quat('-Z','Y').to_euler();cd.clip_start=.1;cd.clip_end=400
    if ortho:cd.type='ORTHO';cd.ortho_scale=ortho
    else:cd.sensor_fit='VERTICAL';cd.angle_y=math.radians(fov_v)
    return cam
for v in D['views']:
    loc,tgt=cam_pos(v,v['distance']);c=make_cam('View_'+v['name'],loc,tgt,C_CAMS);c['distance_m']=v['distance']

# ------------------------------------------------------------------ lighting like the Builder: one sun Euler(50,-30,0) and grey ambient
sd=bpy.data.lights.new('GrayboxSun','SUN');sd.energy=3.2;sun=bpy.data.objects.new('GrayboxSun',sd);C_CAMS.objects.link(sun)
x50,y30=math.radians(50),math.radians(-30)
du=Vector((math.cos(x50)*math.sin(y30),-math.sin(x50),math.cos(x50)*math.cos(y30)))   # Unity light forward
sun.rotation_euler=Vector((du.x,du.z,du.y)).to_track_quat('-Z','Y').to_euler()
world=bpy.data.worlds.new('Ambient');S.world=world;world.use_nodes=True
bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(*srgb((.65,.65,.65)),1);bg.inputs['Strength'].default_value=.9

# ------------------------------------------------------------------ preview-only helpers (not in the Unity scene)
ZONE_RGB=['#d9d9c3','#e9e0cc','#d2dfcb','#dfe7b9','#cce3df','#d4e4da']
def hexrgb(h):return tuple(int(h[i:i+2],16)/255 for i in (1,3,5))
for z,hx in zip(D['zones'],ZONE_RGB):   # draped zone outline, 0.5 m wide, sampled every metre
    c=z['center'];x0,x1=c['x']-z['width']/2,c['x']+z['width']/2;z0,z1=c['z']-z['depth']/2,c['z']+z['depth']/2
    bm=bmesh.new();corners=[(x0,z0),(x1,z0),(x1,z1),(x0,z1),(x0,z0)]
    for (ax,az),(bx,bz) in zip(corners,corners[1:]):
        n=max(1,round(math.hypot(bx-ax,bz-az)))
        for i in range(n):
            px,pz=ax+(bx-ax)*(i+.5)/n,az+(bz-az)*(i+.5)/n
            box_bm(bm,Vector((px,pz,ground(px,pz)+.12)),(.5 if ax==bx else math.hypot(bx-ax,bz-az)/n+.02,.5 if az==bz else math.hypot(bx-ax,bz-az)/n+.02,.2))
    mesh_obj('ZoneOutline_'+z['name'],bm,mat('ZoneOutline_'+z['name'],tuple(v*.82 for v in hexrgb(hx)),emit=.4),C_PREV)
LABEL_MAT=mat('PreviewLabel',(.1,.14,.13));LABEL_W=mat('PreviewLabelLight',(.97,.96,.9))
def flat_text(name,body,x,z,size,material,align='CENTER'):
    cu=bpy.data.curves.new(name,'FONT');cu.body=body;cu.size=size;cu.align_x=align;cu.align_y='CENTER';cu.extrude=.02
    t=bpy.data.objects.new(name,cu);t.location=(x,z,ground(x,z)+6.);t.visible_shadow=False;cu.materials.append(material);C_PREV.objects.link(t);return t
ZONE_TAG={'SettlementExit':'01 SettlementExit','MountainTrail':'02 MountainTrail','HerbForest':'03 HerbForest',
          'RabbitSlope':'04 RabbitSlope','ShallowStream':'05 ShallowStream','ReturnShortcut':'06 ReturnShortcut'}
ZONE_POS={'SettlementExit':(24,36),'MountainTrail':(73,46),'HerbForest':(44,120),'RabbitSlope':(150,146),'ShallowStream':(132,22),'ReturnShortcut':(60,4)}
for z in D['zones']:flat_text('ZoneLabel_'+z['name'],f"{ZONE_TAG[z['name']]}  {z['width']}x{z['depth']} m",*ZONE_POS[z['name']],3.2,LABEL_MAT)
SHORT={'player':lambda n:'P'+n[-1],'merchant':lambda n:'M','return':lambda n:'S','herb':lambda n:'H'+n[-2:],'clue':lambda n:'T'+n[-2:],
       'rabbit':lambda n:n[-3]+n[-1],'flee':lambda n:'F'+n[-3]+n[-1]}
for m in D['markers']:
    k=m['kind']
    if k not in SHORT:continue
    P=U(m['position']);bm=bmesh.new();cyl_bm(bm,P+Vector((0,0,.1)),1.3 if k!='flee' else 1.0,.2,24)
    mesh_obj('Ring_'+m['name'],bm,mat('Ring_'+k,MARKER_RGB.get(k,(.65,.7,.7)),emit=.8),C_PREV).visible_shadow=False
    dx,dz={'merchant':(0,-3.2),'player':(0,3.2) if m['name'].endswith('01') else (0,-3.2),'return':(0,3.2)}.get(k,(2.6,2.2))
    flat_text('Label_'+m['name'],SHORT[k](m['name']),P.x+dx,P.y+dz,2.3,LABEL_MAT)
for o in D['obstacles']:
    if o['kind'] in ('cliff','deepWater'):
        p=o['position'];s=o['size'];t=flat_text('Label_'+o['name'],o['name'].removeprefix('NavBlocker_'),p['x'],p['z'],2.0,LABEL_W)
        t.location.z=p['y']+s['y']/2+.3
        if s['z']>s['x']*1.6:t.rotation_euler.z=math.pi/2

# ------------------------------------------------------------------ preview cameras
W,H=D['bounds']['width'],D['bounds']['depth']
make_cam('Preview_Birdseye',Vector((W/2,H/2,150)),Vector((W/2,H/2,0)),C_PREV,ortho=W+12)
make_cam('Preview_Overview',Vector((W/2-35,-105,150)),Vector((W/2+2,H/2+4,0)),C_PREV,fov_v=40)

RENDERS.mkdir(parents=True,exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))

# ------------------------------------------------------------------ renders (Blender previews, not Unity screenshots)
r=S.render
for eng in ('BLENDER_EEVEE_NEXT','BLENDER_EEVEE','BLENDER_WORKBENCH'):
    try:r.engine=eng;break
    except TypeError:continue
S.view_settings.view_transform='Standard';r.image_settings.file_format='PNG'
try:S.eevee.taa_render_samples=32
except AttributeError:pass
def render(cam,path,w,h,preview):
    S.camera=bpy.data.objects[cam];r.resolution_x,r.resolution_y=w,h;r.resolution_percentage=100
    C_PREV_layer=bpy.context.view_layer.layer_collection.children['95_Preview_Only'];C_PREV_layer.exclude=False
    for o in C_PREV.objects:
        if o.type!='CAMERA':o.hide_render=not preview
    r.filepath=str(path);bpy.ops.render.render(write_still=True)
render('Preview_Birdseye',RENDERS/'birdseye.png',2400,round(2400*(H+10)/(W+12)),True)
render('Preview_Overview',RENDERS/'overview.png',2000,1150,True)
for v in D['views']:
    render('View_'+v['name'],RENDERS/f"view_{v['name']}.png",cam_cfg['width'],cam_cfg['height'],False)
for o in C_PREV.objects:o.hide_render=False
bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))
print('BUILT',OUT_BLEND,'sha',SHA[:12],'objects',len(bpy.data.objects))
