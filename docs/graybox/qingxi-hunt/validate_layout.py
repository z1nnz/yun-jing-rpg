"""Offline geometric preflight only; never claims Unity, NavMesh, gameplay or device validation.
Python 3 standard library. Run from any directory; emits validation.json beside this file.
"""
import hashlib, heapq, itertools, json, math
from pathlib import Path

HERE = Path(__file__).resolve().parent

def xyz(p): return (p['x'], p['y'], p['z'])
def xz(p): return (p['x'], p['z'])
def ground(d,x,z):
    h=d['hill']; return h['height']*max(0,1-abs(x-h['centerX'])/h['halfWidth'])*max(0,1-abs(z-h['centerZ'])/h['halfDepth'])
def sampled(points,step=.5):
    yield points[0],0.
    total=0.
    for a,b in zip(points,points[1:]):
        length=math.dist(xyz(a),xyz(b));n=max(1,math.ceil(length/step))
        for i in range(1,n+1):yield {k:a[k]+(b[k]-a[k])*i/n for k in 'xyz'},total+length*i/n
        total+=length
def rect(o):
    p,s=o['position'],o['size'];return p['x']-s['x']/2,p['z']-s['z']/2,p['x']+s['x']/2,p['z']+s['z']/2
def clearance(p,obstacles):
    x,z=xz(p);return min(math.hypot(max(a-x,0,x-c),max(b-z,0,z-e)) for a,b,c,e in map(rect,obstacles))
def free(d,p,r):return r<=p['x']<=d['bounds']['width']-r and r<=p['z']<=d['bounds']['depth']-r and clearance(p,d['obstacles'])>r
def segment_box(a,b,o,pad=0):
    lo,hi=0.,1.
    for k in 'xyz':
        low=o['position'][k]-o['size'][k]/2-pad;high=o['position'][k]+o['size'][k]/2+pad
        delta=b[k]-a[k]
        if abs(delta)<1e-9:
            if not low<=a[k]<=high:return False
        else:
            v,w=(low-a[k])/delta,(high-a[k])/delta
            lo=max(lo,min(v,w));hi=min(hi,max(v,w))
            if lo>hi:return False
    return True
def visible(d,p,target):
    a=dict(p,y=p['y']+1.4);b=dict(target,y=target['y']+.4)
    return not any(segment_box(a,b,o) for o in d['obstacles'])
def astar(d,a,b,r):
    # 2 m lattice with diagonal corner-cutting disallowed. Ground is a continuous shallow hill.
    start=tuple(round(v/2) for v in xz(a));goal=tuple(round(v/2) for v in xz(b))
    def node(n):return {'x':n[0]*2,'y':ground(d,n[0]*2,n[1]*2),'z':n[1]*2}
    def edge(p,q):return all(free(d,v,r) for v,_ in sampled([p,q],.5))
    if not edge(a,node(start)) or not edge(node(goal),b):return None
    queue=[(math.dist(start,goal),0.,start)];cost={start:0.}
    while queue:
        _,g,n=heapq.heappop(queue)
        if g>cost[n]:continue
        if n==goal:return round(g*2+math.dist(xz(a),xz(node(start)))+math.dist(xz(b),xz(node(goal))),2)
        for dx,dz in itertools.product((-1,0,1),repeat=2):
            if dx==dz==0:continue
            nxt=n[0]+dx,n[1]+dz;ng=g+math.hypot(dx,dz)
            if ng>=cost.get(nxt,math.inf) or not edge(node(n),node(nxt)):continue
            cost[nxt]=ng;heapq.heappush(queue,(ng+math.dist(nxt,goal),ng,nxt))
    return None

def validate(d):
    checks={};details={}
    def check(name,value):checks[name]=bool(value)
    markers={m['name']:m for m in d['markers']}
    expected=['PlayerSpawn_01','PlayerSpawn_02','Merchant_Material','SafeReturn_01','AreaBoundary_Hunt']
    expected += [f'TrailClue_{i:02}' for i in range(1,7)]+[f'HerbNode_{i:02}' for i in range(1,7)]
    expected += [f'RabbitSpawn_{g}{i:02}' for g in 'ABC' for i in (1,2)]
    expected += [f'RabbitFlee_{g}{i:02}' for g in 'ABC' for i in (1,2,3)]
    check('all_required_markers',set(expected)<=markers.keys())
    check('unique_marker_and_blocker_names',len(markers)==len(d['markers']) and len({o['name'] for o in d['obstacles']})==len(d['obstacles']))
    check('six_zones_220x160',len(d['zones'])==6 and d['bounds']['width']==220 and d['bounds']['depth']==160)
    check('camera_blocker_pairs',all('CameraBlocker_'+o['name'].removeprefix('NavBlocker_') in markers for o in d['obstacles']))
    check('source_metres_version',d['unit']=='metre' and d['unityVersion']=='6000.0.85f1')
    positions=[m for m in markers.values() if m['kind'] not in ('cameraBlocker','boundary')]
    check('markers_clear_of_blockers',all(free(d,m['position'],d['rabbit' if m['kind'] in ('rabbit','flee') else 'player']['radius']) for m in positions))
    check('marker_height_matches_ground',all(abs(m['position']['y']-ground(d,*xz(m['position'])))<.001 for m in positions))
    rabbits=[m for m in markers.values() if m['kind']=='rabbit']
    spacing=min(math.dist(xz(a['position']),xz(b['position'])) for a,b in itertools.combinations(rabbits,2))
    details['minimum_rabbit_spawn_spacing_m']=round(spacing,3);check('all_six_rabbit_spawns_at_least_8m',spacing>=8)
    playergap=math.dist(xz(markers['PlayerSpawn_01']['position']),xz(markers['PlayerSpawn_02']['position']))
    details['player_spawn_spacing_m']=playergap;check('two_spawns_at_least_8m',playergap>=8)
    route_results={}
    for route in d['routes']:
        samples=list(sampled(route['points']));length=samples[-1][1];margin=min(clearance(p,d['obstacles']) for p,_ in samples)
        check('route_clear_'+route['name'],all(free(d,p,d['player']['radius']) for p,_ in samples))
        check('route_declared_width_'+route['name'],margin>=route['width']/2+.05 and route['width']>=2.5)
        route_results[route['name']]={'length_m':round(length,3),'at_4mps_seconds':round(length/d['player']['speed'],3),'minimum_centerline_obstacle_clearance_m':round(margin,3),'declared_width_m':route['width']}
    details['routes']=route_results
    main=next(r for r in d['routes'] if r['name']=='MainDiscovery')
    ms=list(sampled(main['points']))
    firstclue=next(distance for p,distance in ms if math.dist(xz(p),xz(markers['TrailClue_01']['position']))<.001)
    firstvisible=next(((p,distance) for p,distance in ms if any(visible(d,p,r['position']) for r in rabbits)),None)
    details['first_clue_arrival_seconds']=round(firstclue/4,3)
    details['first_rabbit_geometric_line_of_sight_seconds']=None if firstvisible is None else round(firstvisible[1]/4,3)
    details['first_rabbit_visible_from']=None if firstvisible is None else firstvisible[0]
    check('first_clue_20_to_30_seconds',20<=firstclue/4<=30)
    check('first_rabbit_geometric_sight_60_to_90_seconds',firstvisible is not None and 60<=firstvisible[1]/4<=90)
    check('village_cannot_see_all_rabbits',not all(visible(d,markers['PlayerSpawn_01']['position'],r['position']) for r in rabbits))
    check('return_around_60_seconds',50<=route_results['AlternativeReturn']['at_4mps_seconds']<=70)
    check('mountain_path_about_60m',55<=route_results['MountainTrailSegment']['length_m']<=65)
    check('shortcut_about_70m',65<=route_results['ShortcutSegment']['length_m']<=80)
    # Exact triangle slopes for the same 5 m mesh construction as the Builder.
    grid=d['bounds']['grid'];slopes=[]
    for z in range(0,d['bounds']['depth'],grid):
        for x in range(0,d['bounds']['width'],grid):
            a,b,c,e=[ground(d,px,pz) for px,pz in [(x,z),(x+grid,z),(x,z+grid),(x+grid,z+grid)]]
            slopes.extend([math.degrees(math.atan(math.hypot((b-a)/grid,(c-a)/grid))),math.degrees(math.atan(math.hypot((e-c)/grid,(e-b)/grid)))])
    details['max_ground_triangle_slope_degrees']=round(max(slopes),3);check('ground_slope_under_35_degrees',max(slopes)<35)
    check('no_ground_discontinuities',d['hill']['height']>0 and d['hill']['halfWidth']%grid==0 and d['hill']['halfDepth']%grid==0)
    paths=[]
    for group in 'ABC':
        nodes=[m for m in markers.values() if m['group']==group]
        for a,b in itertools.combinations(nodes,2):
            length=astar(d,a['position'],b['position'],d['rabbit']['radius'])
            paths.append({'from':a['name'],'to':b['name'],'lattice_path_m':length})
        check('herd_'+group+'_all_spawn_flee_pairs_connected',all(p['lattice_path_m'] is not None for p in paths if p['from'].startswith(('RabbitSpawn_'+group,'RabbitFlee_'+group))))
    details['rabbit_lattice_paths']=paths
    # Two capsule-centre traces on the main/return route; not a live multiplayer rehearsal.
    two=[]
    for route in [r for r in d['routes'] if r['name'] in ('MainDiscovery','AlternativeReturn')]:
        samples=list(sampled(route['points']));conflicts=[]
        for i,(p,distance) in enumerate(samples):
            a=samples[max(0,i-1)][0];b=samples[min(len(samples)-1,i+1)][0]
            dx,dz=b['x']-a['x'],b['z']-a['z'];norm=math.hypot(dx,dz)
            for sign in (-1,1):
                q=dict(p,x=p['x']+sign*.8*dz/norm,z=p['z']-sign*.8*dx/norm)
                if not free(d,q,d['player']['radius']):conflicts.append(round(distance,2))
        two.append({'route':route['name'],'centre_separation_m':1.6,'blocked_samples':conflicts})
        check('two_capsule_offsets_clear_'+route['name'],not conflicts)
    details['two_capsule_geometric_traces']=two
    camera=[]
    for v in d['views']:
        for distance in (3.5,6):
            for yaw in range(0,360,45):
                a=dict(v['target'],y=v['target']['y']+d['camera']['targetHeight']);r=math.radians(yaw);e=math.radians(d['camera']['elevationDegrees'])
                b=dict(a,x=a['x']-math.sin(r)*distance*math.cos(e),z=a['z']-math.cos(r)*distance*math.cos(e),y=a['y']+distance*math.sin(e))
                hits=[o['name'] for o in d['obstacles'] if segment_box(a,b,o,d['camera']['probeRadius'])]
                if hits:camera.append({'view':v['name'],'distance_m':distance,'yaw':yaw,'hits':hits})
    details['camera_box_probe_conflicts']=camera
    check('six_viewpoints_96_box_probes_clear',not camera)
    # Sanity checks on the validator itself: an obstructed point/path must fail.
    wall=d['obstacles'][0];check('validator_rejects_blocker_interior',not free(d,wall['position'],.35))
    check('validator_detects_wall_ray',segment_box(dict(wall['position'],x=wall['position']['x']-20),dict(wall['position'],x=wall['position']['x']+20),wall))
    return checks,details

def main():
    source=HERE/'layout.json';d=json.loads(source.read_text(encoding='utf-8'));checks,details=validate(d)
    report={'status':'passed' if all(checks.values()) else 'failed','scope':'Offline coordinate/AABB/lattice preflight only',
            'unityCompiled':False,'navMeshMeasured':False,'twoPlayerPlaytest':False,'phoneCameraTest':False,
            'layoutSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'checks':checks,'checkCount':len(checks),'measurements':details}
    (HERE/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'checks':len(checks),'failed':[k for k,v in checks.items() if not v],'routes':details['routes'],'firstSightSeconds':details['first_rabbit_geometric_line_of_sight_seconds'],'cameraConflicts':details['camera_box_probe_conflicts']},ensure_ascii=False,indent=2))
    raise SystemExit(0 if report['status']=='passed' else 1)
if __name__=='__main__':main()
