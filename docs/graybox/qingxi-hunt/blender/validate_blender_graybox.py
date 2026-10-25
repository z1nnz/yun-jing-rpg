"""Check QingxiHuntGraybox_blockout.blend against ../layout.json. Blender geometry only: no Unity, NavMesh or devices.

  blender --background --factory-startup --python-exit-code 1 --python docs/graybox/qingxi-hunt/blender/validate_blender_graybox.py

Writes blender-validation.json beside this file and exits non-zero when a check fails.
"""
import bpy,json,math,hashlib,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE=Path(__file__).resolve().parent;LAYOUT=HERE.parent/'layout.json';BLEND=HERE/'QingxiHuntGraybox_blockout.blend'
D=json.loads(LAYOUT.read_text(encoding='utf-8'));SHA=hashlib.sha256(LAYOUT.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(BLEND));S=bpy.context.scene;O=bpy.data.objects
checks={};details={}
def check(name,ok,detail=None):
    checks[name]=bool(ok)
    if detail is not None:details[name]=detail
def U(p):return Vector((p['x'],p['z'],p['y']))
def ground(x,z):
    h=D['hill'];return h['height']*max(0,1-abs(x-h['centerX'])/h['halfWidth'])*max(0,1-abs(z-h['centerZ'])/h['halfDepth'])

check('blend_built_from_current_layout',S.get('layout_sha256')==SHA,{'layoutSha256':SHA})

# ---- names and positions
miss=[m['name'] for m in D['markers'] if m['name'] not in O]
off=[m['name'] for m in D['markers'] if m['name'] in O and (O[m['name']].matrix_world.translation-U(m['position'])).length>1e-4]
check('all_layout_markers_present',not miss,miss);check('marker_positions_match_layout',not off,off)
bad=[]
for o in D['obstacles']:
    ob=O.get(o['name']);s=o['size']
    if ob is None or ob.get('collider')!='Box':bad.append(o['name']);continue
    lo=Vector(min(v.co[i] for v in ob.data.vertices) for i in range(3));hi=Vector(max(v.co[i] for v in ob.data.vertices) for i in range(3))
    if ((hi+lo)/2-U(o['position'])).length>1e-4 or (hi-lo-Vector((s['x'],s['z'],s['y']))).length>1e-4:bad.append(o['name'])
check('obstacles_present_as_matching_boxes',not bad,bad)

# ---- ground mesh
G=next(o for o in O if o.name.startswith('Ground_'));me=G.data
tris=sum(len(p.vertices)-2 for p in me.polygons);zs=[v.co.z for v in me.vertices]
xs=[v.co.x for v in me.vertices];ys=[v.co.y for v in me.vertices]
gd={'vertices':len(me.vertices),'triangles':tris,'size_m':[max(xs)-min(xs),max(ys)-min(ys)],'max_height_m':round(max(zs),4)}
check('ground_matches_builder_grid',len(me.vertices)==1485 and tris==2816 and gd['size_m']==[220,160] and abs(max(zs)-D['hill']['height'])<1e-6,gd)
meshcol=[o.name for o in O if o.get('collider','').startswith('MeshCollider')]
check('only_ground_uses_mesh_collider',meshcol==[G.name],meshcol)
dz=[]
for v in me.vertices:
    if abs(v.co.z-ground(v.co.x,v.co.y))>1e-5:dz.append(v.index)
check('ground_vertices_follow_layout_hill',not dz,len(dz))
slopes=[]
for p in me.polygons:
    n=p.normal;slopes.append(math.degrees(math.acos(max(-1,min(1,abs(n.z))))))
check('ground_slope_under_35_degrees',max(slopes)<35,{'max_degrees':round(max(slopes),3)})

# ---- collision world: ground + box colliders (boundaries included), built in world space
def bvh_of(objs):
    V=[];F=[]
    for o in objs:
        mw=o.matrix_world;base=len(V);V+=[mw@v.co for v in o.data.vertices];F+=[[base+i for i in p.vertices] for p in o.data.polygons]
    return BVHTree.FromPolygons(V,F)
SOLID=[o for o in O if o.type=='MESH' and o.get('collider') in ('Box',) ]
WORLD=bvh_of(SOLID+[G]);BOXES=bvh_of(SOLID)
def blocked(a,b,tree=WORLD):
    d=b-a;L=d.length;hit=tree.ray_cast(a,d.normalized(),L)
    return hit[0] is not None and hit[3]<L-1e-3

# ---- marker heights on the actual ground mesh
# layout.json heights come from the exact hill formula; the 5 m triangles are planar, so inside a cell they differ slightly.
# Tolerance 5 cm (rabbit step 0.15 m); every offset over 1 cm is listed for the Builder owner.
GT=bvh_of([G]);hd=[];worst=0.
for m in D['markers']:
    if m['kind'] in ('cameraBlocker','boundary'):continue
    p=U(m['position']);hit=GT.ray_cast(Vector((p.x,p.y,50)),Vector((0,0,-1)),100)
    if hit[0] is None:hd.append([m['name'],None]);continue
    dz=p.z-hit[0].z;worst=max(worst,abs(dz))
    if abs(dz)>.01:hd.append([m['name'],round(dz,4)])
check('markers_within_5cm_of_ground_mesh',worst<=.05 and all(h[1] is not None for h in hd),{'max_abs_offset_m':round(worst,4),'offsets_over_1cm_marker_minus_mesh_m':hd})

# ---- agent capsules vs box colliders (same rule as the Builder's CheckGeometry: OverlapCapsule)
def capsule_hits(p,r,h):
    hits=[]
    for o in D['obstacles']:
        c=U(o['position']);s=o['size'];half=Vector((s['x'],s['z'],s['y']))/2
        # distance from the capsule segment to the box, sampled along the segment
        for t in [i/10 for i in range(11)]:
            q=p+Vector((0,0,r+.05+(h-2*r-.05)*t))
            dx=max(abs(q.x-c.x)-half.x,0);dy=max(abs(q.y-c.y)-half.y,0);dz=max(abs(q.z-c.z)-half.z,0)
            if math.sqrt(dx*dx+dy*dy+dz*dz)<r:hits.append(o['name']);break
    return hits
cap=[]
for m in D['markers']:
    if m['kind'] not in ('player','rabbit','flee','herb','merchant'):continue
    a=D['rabbit' if m['kind'] in ('rabbit','flee') else 'player'];h=capsule_hits(U(m['position']),a['radius'],a['height'])
    if h:cap.append([m['name'],h])
check('agent_capsules_clear_of_colliders',not cap,cap)
names=[m['name'] for m in D['markers'] if m['kind']=='player'];pp=[U(m['position']) for m in D['markers'] if m['kind']=='player']
check('two_player_spawns_do_not_overlap',(pp[0]-pp[1]).length>=2*D['player']['radius']+.1,{'distance_m':round((pp[0]-pp[1]).length,3)})
rb=[(m['name'],U(m['position'])) for m in D['markers'] if m['kind']=='rabbit']
gap=min((a[1]-b[1]).length for i,a in enumerate(rb) for b in rb[i+1:]);check('rabbit_spawns_at_least_8m_apart',gap>=8,{'minimum_m':round(gap,3)})

# ---- camera bookmarks: 0.2 m sphere probe approximated by 9 rays, against boxes and ground
cc=D['camera'];cam=[]
def cam_pos(v,dist):
    pitch=math.radians(cc['elevationDegrees']);yaw=math.radians(v['yaw']);fwd=Vector((math.sin(yaw),math.cos(yaw),0))
    tgt=U(v['target'])+Vector((0,0,cc['targetHeight']));return tgt-fwd*(dist*math.cos(pitch))+Vector((0,0,dist*math.sin(pitch))),tgt
probe=[Vector((0,0,0))]+[Vector((math.cos(k*math.pi/4),0,math.sin(k*math.pi/4)))*cc['probeRadius'] for k in range(8)]
for v in D['views']:
    for dist in (cc['minDistance'],v['distance'],cc['maxDistance']):
        c,t=cam_pos(v,dist);side=(c-t).cross(Vector((0,0,1))).normalized();up=side.cross((c-t).normalized())
        offs=[side*o.x+up*o.z for o in probe]
        if any(blocked(t+o,c+o) for o in offs):cam.append(f"{v['name']}@{dist}m")
    bm=O['View_'+v['name']]
    if (bm.location-cam_pos(v,v['distance'])[0]).length>1e-4:cam.append('bookmark_position_'+v['name'])
check('six_camera_bookmarks_clear_at_3.5_5_6m',not cam,cam)

# ---- settlement cannot see every rabbit (eye 1.4 m -> rabbit +0.4 m), as in validate_layout.py
eye=U(next(m for m in D['markers'] if m['name']=='PlayerSpawn_01')['position'])+Vector((0,0,1.4))
seen=[n for n,p in rb if not blocked(eye,p+Vector((0,0,.4)))]
check('settlement_spawn_cannot_see_all_rabbits',len(seen)<len(rb),{'visible_from_PlayerSpawn_01':seen})

# ---- information only: route strips are flat boxes, so on the hill their ends sink into the ground
sink={}
for r in D['routes']:
    if r['name'] not in ('MainDiscovery','AlternativeReturn','HerdConnector'):continue
    ob=O[r['name']];worst=0.
    for poly in ob.data.polygons:
        if poly.normal.z<.9:continue
        for i in poly.vertices:
            q=ob.data.vertices[i].co;worst=max(worst,ground(q.x,q.y)-q.z)
    sink[r['name']]=round(worst,3)
details['info_route_strip_max_sink_below_ground_m']=sink

# ---- renders
need=['birdseye.png','overview.png']+[f"view_{v['name']}.png" for v in D['views']]
rend={}
for n in need:
    p=HERE/'renders'/n
    if p.is_file():img=bpy.data.images.load(str(p));rend[n]=list(img.size);bpy.data.images.remove(img)
check('eight_preview_renders_present',len(rend)==8 and all(rend[f"view_{v['name']}.png"]==[cc['width'],cc['height']] for v in D['views']),rend)

report={'status':'passed' if all(checks.values()) else 'failed',
        'scope':'Blender geometry of the graybox copy only. Not compiled or run in Unity; NavMesh, CharacterController, two-player play and phone camera are NOT measured.',
        'blender':bpy.app.version_string,'layoutSha256':SHA,'checkCount':len(checks),'checks':checks,'details':details}
(HERE/'blender-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('VALIDATION',report['status'],sum(checks.values()),'/',len(checks))
for k,v in checks.items():
    if not v:print('  FAIL',k,details.get(k))
sys.exit(0 if report['status']=='passed' else 1)
