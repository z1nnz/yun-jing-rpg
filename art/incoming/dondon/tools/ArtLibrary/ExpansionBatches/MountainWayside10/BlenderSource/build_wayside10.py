"""Wayside architecture: editable meshes, metres, fixed geometry for ten views."""
import bpy,math,json,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
NAMES={'MountainRestPavilion':'六角休憩亭','StoneArchBridge':'拱形石橋','TrailStoneRailing':'獨立石欄杆'}
VIEWS=[('01_front',(0,-1,0)),('02_right',(1,0,0)),('03_rear',(0,1,0)),('04_left',(-1,0,0)),('05_front_right',(1,-1,.6)),('06_rear_right',(1,1,.6)),('07_rear_left',(-1,1,.6)),('08_front_left',(-1,-1,.6)),('09_top',(0,0,1)),('10_high_front',(0,-1,1))]
CONNECTORS={}
def material(name,color,rough=.8):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough
    tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=18;tex.inputs['Detail'].default_value=3
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.16;bump.inputs['Distance'].default_value=.02;l.new(tex.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],p.inputs['Normal'])
    return m
def mesh(name,v,f,m,smooth=False):
    d=bpy.data.meshes.new(name);d.from_pydata(v,[],f);d.update();o=bpy.data.objects.new(name,d);assets.objects.link(o);o.parent=root;d.materials.append(m)
    for p in d.polygons:p.use_smooth=smooth
    return o
CUBE_FACES=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
def box(name,p,size,m,bevel=0):
    x,y,z=p;a,b,c=[v/2 for v in size]
    o=mesh(name,[(x-a,y-b,z-c),(x+a,y-b,z-c),(x+a,y+b,z-c),(x-a,y+b,z-c),(x-a,y-b,z+c),(x+a,y-b,z+c),(x+a,y+b,z+c),(x-a,y+b,z+c)],CUBE_FACES,m)
    if bevel:
        mod=o.modifiers.new('Soft_Stone_Edges','BEVEL');mod.width=bevel;mod.segments=2;o.modifiers.new('Weighted_Normals','WEIGHTED_NORMAL')
    return o
def cylinder(name,loc,r,h,m,n=16):
    x,y,z=loc;v=[(x+r*math.cos(i*math.tau/n),y+r*math.sin(i*math.tau/n),z+dz) for dz in (0,h) for i in range(n)]
    f=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,n+(i+1)%n,n+i) for i in range(n)]
    return mesh(name,v,f,m)
def hbar(name,a,b,w,h,m):
    a,b=Vector(a),Vector(b);d=b-a;side=Vector((-d.y,d.x,0)).normalized()*w/2;z=Vector((0,0,h/2))
    return mesh(name,[tuple(a-side-z),tuple(b-side-z),tuple(b+side-z),tuple(a+side-z),tuple(a-side+z),tuple(b-side+z),tuple(b+side+z),tuple(a+side+z)],CUBE_FACES,m)
def tube(name,points,r,m,sides=8):
    v=[]
    for j,p in enumerate(points):
        tangent=(Vector(points[min(j+1,len(points)-1)])-Vector(points[max(j-1,0)])).normalized();u=tangent.cross(Vector((0,0,1)))
        if u.length<.01:u=tangent.cross(Vector((0,1,0)))
        u.normalize();w=tangent.cross(u)
        v.extend([tuple(Vector(p)+r*(u*math.cos(i*math.tau/sides)+w*math.sin(i*math.tau/sides))) for i in range(sides)])
    f=[tuple(reversed(range(sides))),tuple(range((len(points)-1)*sides,len(points)*sides))]+[(j*sides+i,j*sides+(i+1)%sides,(j+1)*sides+(i+1)%sides,(j+1)*sides+i) for j in range(len(points)-1) for i in range(sides)]
    return mesh(name,v,f,m,True)
def stonepost(name,x,y,z,h=1.1,base_curve=None):
    if base_curve:
        corners=[(x-.17,y-.17),(x+.17,y-.17),(x+.17,y+.17),(x-.17,y+.17)]
        mesh(name+'_Foot',[(xx,yy,base_curve(yy)-.01) for xx,yy in corners]+[(xx,yy,z+.14) for xx,yy in corners],CUBE_FACES,pale)
    else:box(name+'_Foot',(x,y,z+.07),(.34,.34,.14),pale,.018)
    box(name+'_Shaft',(x,y,z+h*.47),(.22,.22,h*.82),stone,.012)
    box(name+'_Cap',(x,y,z+h-.055),(.34,.34,.11),pale,.02)
    cylinder(name+'_Finial',(x,y,z+h),.10,.10,jade,8)

def pavilion():
    for i,(r,z,h) in enumerate([(3.35,0,.18),(3.14,.18,.18),(2.93,.36,.18)]):cylinder('Pavilion_Tier_'+str(i),(0,0,z),r,h,pale if i==2 else stone,6)
    radius=2.4;points=[Vector((radius*math.cos(i*math.tau/6),radius*math.sin(i*math.tau/6),.54)) for i in range(6)]
    for i,p in enumerate(points):
        cylinder('Pillar_Stone_Base',p,.28,.24,pale,12);cylinder('Cedar_Pillar',(p.x,p.y,.78),.145,2.84,wood,16)
        cylinder('Pillar_Bronze_Band',(p.x,p.y,.9),.16,.08,bronze,16)
        box('Capital_Block',(p.x,p.y,3.56),(.44,.44,.24),wood,.01)
        radial=Vector((p.x,p.y,0)).normalized();tangent=Vector((-radial.y,radial.x,0))
        box('Capital_Neck',(p.x,p.y,3.87),(.22,.22,.5),wood,.01)
        for zz,axis,length in [(3.65,tangent,.72),(3.8,radial,.83),(3.94,tangent,1.0)]:
            aa=Vector((p.x,p.y,zz))-axis*length/2;bb=Vector((p.x,p.y,zz))+axis*length/2
            hbar('Stacked_Dougong_Bracket',aa,bb,.14,.16,wood)
        q=points[(i+1)%6];a=Vector((p.x,p.y,3.53));b=Vector((q.x,q.y,3.53));hbar('Upper_Hex_Beam',a,b,.18,.24,wood)
        for p0,p1 in [(p,q),(q,p)]:
            end=p0.lerp(p1,.22);tube('Diagonal_Timber_Bracket',[(p0.x,p0.y,3.05),(end.x,end.y,3.48)],.075,wood,8)
        if i in (1,4):continue  # Opposite entrances remain clear.
        a=p.lerp(q,.14);b=p.lerp(q,.86)
        hbar('Bench_Seat',(a.x,a.y,.99),(b.x,b.y,.99),.44,.12,board)
        for t in (.22,.78):
            pos=p.lerp(q,t);box('Bench_Leg',(pos.x,pos.y,.74),(.14,.23,.40),wood,.008)
        hbar('Bench_Back',(a.x,a.y,1.35),(b.x,b.y,1.35),.085,.14,wood)
        for t in (.18,.82):
            pos=p.lerp(q,t);box('Bench_Back_Post',(pos.x,pos.y,1.2),(.09,.09,.55),wood,.005)
    # Six curved roof sectors. Ribs and eaves follow identical roof profiles.
    radii=[.12,.4,1,1.8,2.6,3.25,3.7];heights=[5.77,5.5,4.9,4.45,4.08,3.98,4.12]
    def roofpoint(side,j,u):
        a=side*math.tau/6;b=(side+1)*math.tau/6;r=radii[j]
        return (r*((1-u)*math.cos(a)+u*math.cos(b)),r*((1-u)*math.sin(a)+u*math.sin(b)),heights[j]+.22*(2*u-1)**4*(r/3.7)**3)
    for side in range(6):
        cols=16;v=[roofpoint(side,j,i/cols) for j in range(len(radii)) for i in range(cols+1)]
        f=[(j*(cols+1)+i,(j+1)*(cols+1)+i,(j+1)*(cols+1)+i+1,j*(cols+1)+i+1) for j in range(len(radii)-1) for i in range(cols)]
        roof=mesh('Roof_Sector',v,f,tile,True);roof['part']='removable_roof';roof.modifiers.new('Roof_Thickness','SOLIDIFY').thickness=.09
        for i in range(17):
            points2=[tuple(Vector(roofpoint(side,j,i/16))+Vector((0,0,.035))) for j in range(1,len(radii))]
            rib=tube('Roof_Tile_Rib',points2,.025,tilelight);rib['part']='removable_roof'
        for j in range(2,len(radii)):
            line=tube('Roof_Tile_Row',[tuple(Vector(roofpoint(side,j,i/16))+Vector((0,0,.025))) for i in range(17)],.018,tilelight);line['part']='removable_roof'
        ridge=tube('Roof_Corner_Ridge',[tuple(Vector(roofpoint(side,j,0))+Vector((0,0,.06))) for j in range(len(radii))],.055,jade);ridge['part']='removable_roof'
        fascia=tube('Roof_Eave',[roofpoint(side,len(radii)-1,i/16) for i in range(17)],.075,wood);fascia['part']='removable_roof'
        # Exposed rafters carry the eaves back to the timber frame.
        for i in (2,5,8,11,14):
            support=[tuple(Vector(roofpoint(side,j,i/16))-Vector((0,0,.2))) for j in range(3,7)]
            raf=tube('Roof_Rafter',support,.055,wood);raf['part']='removable_roof'
    for j,(r,z,h) in enumerate([(.24,5.69,.12),(.16,5.81,.17),(.08,5.98,.20)]):
        ob=cylinder('Roof_Finial',(0,0,z),r,h,bronze,12);ob['part']='removable_roof'
    # Small rear plaque makes orientation clear without fabricated inscriptions.
    box('Rear_Empty_Plaque',(0,2.08,3.18),(.85,.08,.32),board,.015)
    CONNECTORS['MountainRestPavilion']={'front_floor_entry':(0,-2.93*math.sqrt(3)/2,.54),'rear_floor_exit':(0,2.93*math.sqrt(3)/2,.54)}

def deck_z(y):return .5+1.6*(1-(y/4.5)**2)
def bridge():
    n=40;v=[]
    for j in range(n+1):
        y=-4.5+9*j/n;z=deck_z(y)
        v.extend([(-1.7,y,z-.5),(1.7,y,z-.5),(1.7,y,z),(-1.7,y,z)])
    f=[(3,2,1,0),(4*n,4*n+1,4*n+2,4*n+3)]
    for j in range(n):
        for k in range(4):f.append((4*j+k,4*j+(k+1)%4,4*(j+1)+(k+1)%4,4*(j+1)+k))
    ob=mesh('Continuous_Stone_Arch',v,[tuple(reversed(face)) for face in f],stone);ob.data.materials.append(pale)
    for face in ob.data.polygons:
        if face.index>=2 and ((face.index-2)//4)%4==0:face.material_index=1
    # Flush contrasting strips mark joints on the curve; no gaps in the walking surface.
    for j in range(1,30):
        y=-4.5+j*.3;hbar('Deck_Masonry_Joint',(-1.52,y,deck_z(y)+.004),(1.52,y,deck_z(y)+.004),.012,.005,jade)
    for side in (-1,1):
        x=side*1.66
        for j in range(11):
            y=-4.5+j*.9;stonepost('Bridge_Baluster',x,y,deck_z(y),1.08,deck_z)
        for j in range(40):
            a=-4.5+j*9/40;b=-4.5+(j+1)*9/40
            for dz,w,h in [(.11,.22,.2),(.46,.09,.13),(.96,.16,.14)]:hbar('Bridge_Curved_Rail',(x,a,deck_z(a)+dz),(x,b,deck_z(b)+dz),w,h,pale)
        for y in (-4.5,4.5):box('Abutment_Foot',(x,y,.25),(.62,.75,.5),stone,.025)
    # Distinct removable approach marker on the entry end.
    mesh('Entry_Centre_Stone',[(x,y,deck_z(y)+.006) for x,y in [(-.25,-4.4),(.25,-4.4),(.25,-4.2),(-.25,-4.2)]],[(0,1,2,3)],pale)
    CONNECTORS['StoneArchBridge']={'entry':(0,-4.5,.5),'exit':(0,4.5,.5)}

def railing():
    box('Railing_Foundation',(0,0,.09),(3.4,.48,.18),stone,.015)
    for x in (-1.5,0,1.5):stonepost('Railing_Post',x,0,.18,1.1)
    for a,b in [(-1.5,0),(0,1.5)]:
        for z,w,h in [(.38,.15,.12),(.85,.13,.13),(1.20,.2,.12)]:hbar('Railing_Beam',(a,0,z),(b,0,z),w,h,pale)
        for x in [a+.3,a+.6,a+.9,a+1.2]:box('Railing_Spindle',(x,0,.62),(.065,.075,.42),stone,.004)
        x=(a+b)/2
        for z1,z2,xx1,xx2 in [(1.02,1.15,x-.1,x),(1.15,1.02,x,x+.1),(1.02,.89,x+.1,x),(.89,1.02,x,x-.1)]:tube('Jade_Diamond',[(xx1,-.085,z1),(xx2,-.085,z2)],.02,jade,6)
    CONNECTORS['TrailStoneRailing']={'left_end':(-1.7,0,0),'right_end':(1.7,0,0)}
BUILDERS={'MountainRestPavilion':pavilion,'StoneArchBridge':bridge,'TrailStoneRailing':railing}

def bounds(objects):
    dg=bpy.context.evaluated_depsgraph_get();pts=[o.evaluated_get(dg).matrix_world@v.co for o in objects for v in o.evaluated_get(dg).data.vertices]
    return Vector([min(p[i] for p in pts) for i in range(3)]),Vector([max(p[i] for p in pts) for i in range(3)])

def build(aid):
    global assets,root,stone,pale,wood,board,tile,tilelight,bronze,jade
    out=ROOT/'Models'/aid/'v001';refs=ROOT/'ArtLibrary/Turnarounds'/f'{aid}_v001'
    if (refs/'views.json').exists():print('ALREADY_COMPLETE',aid,flush=True);return
    out.mkdir(parents=True,exist_ok=True);refs.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;bpy.context.preferences.filepaths.save_version=0
    s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
    assets=bpy.data.collections.new('01_Editable_Asset');s.collection.children.link(assets)
    root=bpy.data.objects.new(aid+'_ROOT',None);assets.objects.link(root)
    stone=material('Weathered_Blue_Stone',(.19,.25,.24));pale=material('Pale_Edge_Stone',(.34,.38,.33))
    wood=material('Deep_Cedar',(.085,.035,.018));board=material('Cedar_Seat',(.22,.11,.045))
    tile=material('Blue_Green_Roof',(.045,.12,.12));tilelight=material('Roof_Tile_Ridges',(.075,.17,.16))
    bronze=material('Aged_Bronze',(.25,.17,.065),.45);jade=material('Jade_Trim',(.065,.21,.14),.6)
    BUILDERS[aid]();bpy.context.view_layer.update();objects=[o for o in assets.objects if o.type=='MESH']
    lo,hi=bounds(objects);shift=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
    for o in objects:o.location-=shift
    bpy.context.view_layer.update();lo,hi=bounds(objects);extent=hi-lo;centre=(lo+hi)/2
    studio=bpy.data.collections.new('90_Studio_Not_Exported');s.collection.children.link(studio)
    def add(name,data):
        ob=bpy.data.objects.new(name,data);studio.objects.link(ob);return ob
    cam=add('Reference_Camera',bpy.data.cameras.new('Reference_Camera'));s.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=extent.length*1.08;cam.data.clip_end=1000
    ls=max(extent)*.65
    for name,dr,power in [('Key',(-.8,-1.1,1.5),1100),('Fill',(1.2,-.4,.9),650),('Rim',(.2,1.1,1.3),950)]:
        d=bpy.data.lights.new(name,'AREA');d.energy=power*ls*ls/7;d.shape='DISK';d.size=ls;o=add(name,d);o.location=centre+Vector(dr)*ls;o.rotation_euler=(centre-o.location).to_track_quat('-Z','Y').to_euler()
    s.world=bpy.data.worlds.new('Neutral_Studio');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.19,.21,.22,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.65
    s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=16;s.cycles.use_denoising=True
    s.render.resolution_x=1024;s.render.resolution_y=1024;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX';s.view_settings.exposure=-.65
    def position(dr):
        cam.location=centre+Vector(dr).normalized()*cam.data.ortho_scale*2.3;cam.rotation_euler=(centre-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
    position((1,-1,.6));bpy.ops.object.select_all(action='DESELECT')
    for o in [root]+objects:o.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.export_scene.fbx(filepath=str(out/(aid+'_v001.fbx')),use_selection=True,object_types={'MESH','EMPTY'},add_leaf_bones=False,axis_forward='-Z',axis_up='Y',apply_unit_scale=True,bake_anim=False)
    root['stage']='Editable architecture prototype; collision and engine tests pending';bpy.ops.wm.save_as_mainfile(filepath=str(out/(aid+'_v001.blend')))
    info={'asset':aid,'name_zh':NAMES[aid],'units':'meters','front':'-Y','dimensions_m':list(extent),'mesh_objects':len(objects),'same_geometry_ten_views':True,'stage':'editable architecture prototype','uv_baked':False,'collision':False,'lod':False,'unreal_import_verified':False}
    info['connectors']={k:list(Vector(v)-shift) for k,v in CONNECTORS[aid].items()}
    if aid=='MountainRestPavilion':info.update({'pillars':6,'entry_width_between_pillars_m':2.11,'entry_clear_width_at_bases_m':1.84,'floor_height_m':.54,'step_risers_m':[.18,.18,.18],'roof_removable':True})
    if aid=='StoneArchBridge':info.update({'deck_length_m':9,'clear_width_m':2.98,'arch_thickness_vertical_m':.5,'deck_max_slope':1.6*2/4.5,'center_under_arch_clearance_m':1.6})
    if aid=='TrailStoneRailing':info.update({'foundation_length_m':3.4,'post_centres_m':[-1.5,0,1.5],'use':'Standalone visual module; adjust end posts when joining repeats.'})
    (out/'model_info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2))
    from bpy_extras.object_utils import world_to_camera_view
    records=[]
    for name,dr in VIEWS:
        position(dr);dg=bpy.context.evaluated_depsgraph_get()
        projected=[world_to_camera_view(s,cam,e.matrix_world@Vector(p)) for o in objects for e in [o.evaluated_get(dg)] for p in e.bound_box]
        assert all(.005<p.x<.995 and .005<p.y<.995 and p.z>0 for p in projected),(aid,name,'cropped')
        s.render.filepath=str(refs/(name+'.png'));bpy.ops.render.render(write_still=True)
        records.append({'file':name+'.png','direction':dr,'camera_location':list(cam.location),'projection':'orthographic','framing_checked':True});print('VIEW_COMPLETE',aid,name,flush=True)
    (refs/'views.json').write_text(json.dumps({'asset':aid,'source':str((out/(aid+'_v001.blend')).relative_to(ROOT)),'same_geometry':True,'views':records},indent=2))
    if aid=='MountainRestPavilion':
        roof_objects=[o for o in objects if o.get('part')=='removable_roof']
        for o in roof_objects:o.hide_render=True
        position((1,-1,1));s.render.filepath=str(out/'11_interior_roof_hidden.png');bpy.ops.render.render(write_still=True)
        for o in roof_objects:o.hide_render=False
    print('ASSET_COMPLETE',aid,flush=True)

if __name__=='__main__':
    for aid in (sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else BUILDERS):build(aid)
