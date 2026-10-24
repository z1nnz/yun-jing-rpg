"""Build eight editable sect facilities and furniture assets and render ten views per asset.
Run: Blender --background --factory-startup -t 4 --python this_file.py
Optional IDs after -- select assets. Existing completed assets are not overwritten.
"""
import bpy, math, json, sys, random, os
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
VIEWS=[('01_front',(0,-1,0)),('02_right',(1,0,0)),('03_rear',(0,1,0)),('04_left',(-1,0,0)),
       ('05_front_right',(1,-1,.45)),('06_rear_right',(1,1,.45)),('07_rear_left',(-1,1,.45)),
       ('08_front_left',(-1,-1,.45)),('09_top',(0,0,1)),('10_high_front',(0,-1,1))]

def mat(name,c,metal=0,rough=.6):
    m=bpy.data.materials.new(name); m.diffuse_color=(*c,1); m.use_nodes=True
    n=m.node_tree.nodes; bs=n.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(*c,1)
    bs.inputs['Metallic'].default_value=metal; bs.inputs['Roughness'].default_value=rough
    noise=n.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value=45
    bump=n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.14; bump.inputs['Distance'].default_value=.015
    m.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height']); m.node_tree.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
    return m

def finish(o,name,m,bevel=0):
    o.name=name
    for c in list(o.users_collection): c.objects.unlink(o)
    assets.objects.link(o); o.parent=root; o.data.materials.append(m)
    if bevel:
        mod=o.modifiers.new('Soft_edges','BEVEL'); mod.width=bevel; mod.segments=3
        mod=o.modifiers.new('Weighted_normals','WEIGHTED_NORMAL')
    return o

def box(name,p,s,m,bevel=.012):
    bpy.ops.mesh.primitive_cube_add(size=1,location=p); o=bpy.context.object; o.dimensions=s
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return finish(o,name,m,bevel)

def cyl(name,p,r,d,m):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=r,depth=d,location=p)
    return finish(bpy.context.object,name,m,min(r*.08,.008))

def mesh(name,v,f,m):
    d=bpy.data.meshes.new(name+'_Mesh'); d.from_pydata(v,[],f); d.update()
    o=bpy.data.objects.new(name,d); assets.objects.link(o); o.parent=root; d.materials.append(m); return o

def beam(name,a,b,r,m):
    a,b=Vector(a),Vector(b); o=cyl(name,(a+b)/2,r,(b-a).length,m)
    o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler(); return o

def torus(name,p,major,minor,m,rot=(0,0,0)):
    bpy.ops.mesh.primitive_torus_add(major_segments=64,minor_segments=12,location=p,major_radius=major,minor_radius=minor,rotation=rot)
    o=finish(bpy.context.object,name,m)
    for f in o.data.polygons:f.use_smooth=True
    return o

def lathe(name,profile,p,m,segments=64):
    v=[(p[0]+r*math.cos(i*math.tau/segments),p[1]+r*math.sin(i*math.tau/segments),p[2]+z) for r,z in profile for i in range(segments)]
    f=[(j*segments+i,j*segments+(i+1)%segments,(j+1)*segments+(i+1)%segments,(j+1)*segments+i) for j in range(len(profile)-1) for i in range(segments)]
    o=mesh(name,v,f,m)
    for f in o.data.polygons:f.use_smooth=True
    return o

def leaf(name,a,b,width,m):
    a,b=Vector(a),Vector(b); d=b-a; side=d.cross(Vector((0,0,1)))
    if side.length<.001:side=Vector((1,0,0))
    side.normalize(); mid=a+d*.5; ridge=mid+Vector((0,0,width*.17))
    v=[tuple(a),tuple(mid+side*width),tuple(b),tuple(mid-side*width),tuple(ridge)]
    o=mesh(name,v,[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],m)
    mod=o.modifiers.new('Leaf_thickness','SOLIDIFY');mod.thickness=.002
    return o

def herb(p,scale=1):
    p=Vector(p)
    for j in range(5):
        a=j*math.tau/5; tip=p+Vector((.13*math.cos(a),.13*math.sin(a),.34+.04*(j%2)))*scale
        beam('Herb_Stem',p,tip,.008*scale,green)
        for t in (.35,.65,.9):
            origin=p+(tip-p)*t
            for sign in (-1,1):
                angle=a+sign*1.1
                end=origin+Vector((.14*math.cos(angle),.14*math.sin(angle),.07))*scale
                leaf('Herb_Leaf',origin,end,.047*scale,green if j%2 else sage)

def ribbon(name,points,r,material):
    # A continuous round timber/tile profile, with editable bevel depth.
    bpy.ops.object.select_all(action='DESELECT')
    d=bpy.data.curves.new(name,'CURVE');d.dimensions='3D';d.resolution_u=1
    d.bevel_depth=r;d.bevel_resolution=2
    s=d.splines.new('POLY');s.points.add(len(points)-1)
    for v,p in zip(s.points,points):v.co=(*p,1)
    o=bpy.data.objects.new(name,d);assets.objects.link(o);o.parent=root;d.materials.append(material)
    bpy.context.view_layer.objects.active=o;o.select_set(True)
    bpy.ops.object.convert(target='MESH');o.select_set(False)
    return o

def roof(name,w,d,eave,rise,cx=0,cy=0):
    # Two curved tiled slopes. Ends rise modestly, all tile ribs follow the same surface.
    nx=max(12,int(w/.30));ny=12
    def pt(x,t,sign):
        return (cx+x,cy+sign*d*.5*t,eave+rise*(1-t)**1.5+.20*t**8+.15*(abs(x)/(w*.5))**8*t**3)
    for sign in (-1,1):
        v=[pt(-w/2+w*i/nx,j/ny,sign) for j in range(ny+1) for i in range(nx+1)]
        f=[(j*(nx+1)+i,j*(nx+1)+i+1,(j+1)*(nx+1)+i+1,(j+1)*(nx+1)+i) for j in range(ny) for i in range(nx)]
        if sign<0:f=[tuple(reversed(face)) for face in f]
        o=mesh(name+'_Tile_Bed',v,f,tile);m=o.modifiers.new('Roof_Thickness','SOLIDIFY');m.thickness=.10
        for i in range(nx+1):
            x=-w/2+w*i/nx
            ribbon(name+'_Tile_Roll',[pt(x,j/ny,sign) for j in range(ny+1)],.045,tilelight if i%3==0 else tile)
        for j in range(2,ny+1,2):
            ribbon(name+'_Tile_Overlap',[pt(-w/2+w*i/nx,j/ny,sign) for i in range(nx+1)],.018,tilelight)
        for x in (-w/2,w/2):ribbon(name+'_Gable_Bargeboard',[tuple(Vector(pt(x,j/ny,sign))+Vector((0,0,-.09))) for j in range(ny+1)],.105,wood)
        ribbon(name+'_Eave_Fascia',[tuple(Vector(pt(-w/2+w*i/nx,1,sign))+Vector((0,0,-.10))) for i in range(nx+1)],.10,wood)
    ribbon(name+'_Ridge',[(cx-w/2-.14,cy,eave+rise+.22),(cx-w/2+.18,cy,eave+rise+.07),(cx+w/2-.18,cy,eave+rise+.07),(cx+w/2+.14,cy,eave+rise+.22)],.12,tilelight)
    for x in (-w/2+.15,w/2-.15):
        beam(name+'_Ridge_End',(cx+x,cy,eave+rise+.12),(cx+x*1.035,cy,eave+rise+.48),.085,gold)

def steps(width,yfront,floor,n=5):
    for i in range(n):
        h=floor*(i+1)/n;y=yfront-(n-i-.5)*.32
        box('Stair_Tread_%02d'%i,(0,y,h/2),(width,.34,h),stone,.025)

def terrace(w,d,h=.6,stairs=4):
    box('Stone_Foundation',(0,0,h/2),(w,d,h),stone,.065)
    box('Terrace_Coping',(0,0,h-.035),(w+.14,d+.14,.11),pale,.025)
    for x in range(int(w)):
        box('Terrace_Front_Joint',(-w/2+x+.5,-d/2-.006,h*.47),(.015,.016,h*.65),dark,.001)
    steps(min(3.2,w*.5),-d/2,h,stairs)

def post(x,y,z0,h):
    box('Column_Stone_Base',(x,y,z0+.12),(.46,.46,.24),pale,.04)
    cyl('Timber_Column',(x,y,z0+.24+h/2),.15,h,wood)
    for z in (z0+.34,z0+h+.13):cyl('Column_Collar',(x,y,z),.19,.11,board)
    for axis in (0,1):
        dim=(.83,.18,.14) if axis==0 else (.18,.83,.14)
        box('Bracket_Crossarm',(x,y,z0+h+.23),dim,board,.025)
    for s in (-1,1):
        beam('Column_Knee_Brace',(x,y,z0+h-.48),(x+s*.55,y,z0+h+.12),.065,wood)

def window(x,y,z,w=1.2,h=1.3):
    box('Window_Paper',(x,y+.035,z),(w,.045,h),paper,.005)
    for xx in (-w/2,w/2):box('Window_Frame',(x+xx,y,z),(.075,.12,h+.12),wood)
    for zz in (-h/2,h/2):box('Window_Frame',(x,y,z+zz),(w+.12,.12,.075),wood)
    for i in range(1,6):box('Window_Lattice_V',(x-w/2+i*w/6,y-.035,z),(.025,.055,h),wood,.002)
    for i in range(1,5):box('Window_Lattice_H',(x,y-.04,z-h/2+i*h/5),(w,.055,.025),wood,.002)

def plaque(name,x,y,z,w=2,h=.65):
    box(name+'_Blank_Nameboard',(x,y,z),(w,.15,h),jade,.045)
    for zz in (-h/2,h/2):box(name+'_Border',(x,y-.087,z+zz),(w+.04,.035,.035),gold,.008)
    for xx in (-w/2,w/2):box(name+'_Border',(x+xx,y-.087,z),(.035,.035,h),gold,.008)
    # Unnamed sect: crest in the centre, blank space on both sides for future lettering.
    torus(name+'_Sun_Crest',(x,y-.10,z),h*.24,.018,gold,(math.pi/2,0,0))
    o=box(name+'_Jade_Crest',(x,y-.11,z),(h*.18,.025,h*.18),gold,.003);o.rotation_euler.y=math.pi/4

def railing(a,b,z):
    a,b=Vector(a),Vector(b);n=max(1,round((b-a).length/.9))
    for i in range(n+1):
        p=a+(b-a)*i/n
        key=(round(p.x,4),round(p.y,4),round(z,4))
        if key in rail_posts:continue
        rail_posts.add(key)
        box('Rail_Post',(p.x,p.y,z+.42),(.13,.13,.84),wood,.02)
        cyl('Rail_Cap',(p.x,p.y,z+.87),.10,.09,gold)
    for zz in (.28,.74):beam('Rail_Crossbar',(a.x,a.y,z+zz),(b.x,b.y,z+zz),.045,board)

# New facilities and their independently delivered furnishings.
def placed(builder,offset=(0,0,0),angle=0):
    from mathutils import Matrix
    before=set(assets.objects);builder();bpy.context.view_layer.update();new=set(assets.objects)-before
    M=Matrix.Translation(Vector(offset))@Matrix.Rotation(angle,4,'Z')
    for o in new:o.matrix_world=M@o.matrix_world

def tagged_roof(*args,**kwargs):
    before=set(assets.objects);roof(*args,**kwargs)
    for o in set(assets.objects)-before:o['roof_reveal']=True

def cabinet():
    for x in (-.89,.89):
        box('Cabinet_Side',(x,0,1.05),(.12,.58,1.95),wood,.018)
        for y in (-.22,.22):box('Cabinet_Foot',(x,y,.10),(.15,.15,.20),wood,.018)
    box('Cabinet_Back',(0,.27,1.10),(1.7,.07,1.85),board,.01)
    for z in (.18,2.05):box('Cabinet_Cornice',(0,0,z),(2,.68,.12),board,.025)
    for i in range(4):
        for j in range(5):
            x=-.69+i*.46;z=.40+j*.33
            box('Independent_Drawer',(x,-.03,z),(.425,.48,.29),board,.012)
            box('Drawer_Front',(x,-.295,z),(.43,.065,.295),wood,.014)
            box('Blank_Label_Plate',(x,-.334,z+.065),(.15,.012,.055),gold,.004)
            torus('Drawer_Pull',(x,-.35,z-.035),.045,.009,gold,(math.pi/2,0,0))

def shelf():
    for x in (-.92,.92):box('Shelf_Side',(x,0,1.0),(.13,.48,2.0),wood,.018)
    box('Shelf_Back',(0,.23,1.0),(1.8,.06,1.95),board,.012)
    for z in (.13,.66,1.19,1.72,2.04):box('Shelf_Plank',(0,0,z),(2,.55,.10),wood,.02)
    for k,z in enumerate((.23,.76,1.29)):
        for i in range(5):
            x=-.70+i*.34
            # Horizontal rolled bamboo texts, with bindings and round ends.
            o=cyl('Bamboo_Scroll',(x,-.015,z+.11),.09,.37,rope);o.rotation_euler.x=math.pi/2
            for y in (-.15,.13):torus('Scroll_Binding',(x,y,z+.11),.095,.014,jade,(math.pi/2,0,0))
        for x in (-.35,.35):box('Shelf_Divider',(x,.02,z+.20),(.055,.39,.4),wood,.008)
    for i in range(7):
        x=-.72+i*.24
        o=box('Jade_Slip',(x,0,1.89),(.16,.30,.17),jade,.018);o.rotation_euler.z=.03*(i%3-1)

def desk():
    box('Reading_Tabletop',(0,0,.78),(1.7,.85,.10),board,.025)
    for x in (-.68,.68):
        for y in (-.29,.29):box('Desk_Leg',(x,y,.375),(.10,.10,.75),wood,.015)
        box('Desk_Lower_Brace',(x,0,.20),(.08,.64,.10),wood,.012)
    box('Desk_Long_Brace',(0,.24,.28),(1.4,.08,.10),wood,.012)
    # A bamboo tablet mat and inkstone make the reading desk distinct from a workbench.
    for i in range(10):box('Bamboo_Writing_Slip',(-.5+i*.07,-.06,.851),(.055,.40,.025),rope,.005)
    for y in (-.19,.07):box('Tablet_Tie',(-.185,y,.867),(.70,.018,.012),jade,.003)
    box('Inkstone',(0.54,.12,.87),(.22,.18,.07),dark,.028)
    beam('Brush_Handle',(.28,-.22,.86),(.63,-.13,.86),.012,wood)

def chest():
    # Actual open box cavity; lid stays separately editable with a hinge marker.
    box('Chest_Bottom',(0,0,.15),(1.44,.81,.13),wood,.025)
    for x in (-.65,.65):box('Chest_Side',(x,0,.40),(.10,.76,.48),board,.015)
    for y in (-.34,.34):box('Chest_Front_Back',(0,y,.40),(1.22,.09,.48),board,.015)
    box('Chest_Separate_Lid',(0,0,.70),(1.45,.82,.14),wood,.03)
    for x in (-.47,.47):
        for y in (-.396,.396):box('Chest_Metal_Strap',(x,y,.41),(.065,.025,.47),bronze,.007)
        box('Lid_Metal_Strap',(x,0,.782),(.065,.79,.025),bronze,.007)
        o=cyl('Lid_Hinge_Barrel',(x,.417,.68),.035,.18,gold);o.rotation_euler.y=math.pi/2
    box('Chest_Latch',(0,-.408,.58),(.15,.035,.22),gold,.014)
    torus('Chest_Latch_Ring',(0,-.44,.52),.06,.014,bronze,(math.pi/2,0,0))
    for x in (-.55,.55):
        for y in (-.27,.27):box('Chest_Foot',(x,y,.06),(.17,.17,.12),wood,.015)

def bed():
    for x in (-.54,.54):
        for y in (-.98,.98):box('Bed_Post',(x,y,.36),(.12,.12,.72),wood,.025)
    box('Bed_Frame',(0,0,.38),(1.18,2.12,.18),wood,.025)
    for y,h in ((.98,.85),(-.98,.55)):
        box('Bed_End_Board',(0,y,h),(1.18,.12,.25),board,.025)
    box('Woven_Mattress',(0,0,.53),(1.06,1.94,.16),rope,.07)
    box('Folded_Quilt',(0,-.24,.67),(1.04,1.26,.12),jade,.055)
    for x in (-.40,.40):box('Quilt_Binding',(x,-.24,.737),(.025,1.16,.012),gold,.004)
    box('Pillow',(0,.64,.67),(.72,.36,.18),paper,.085)

def room_shell(w,d,floor,h,front_opening):
    terrace(w+1.4,d+1.4,floor,3)
    box('Room_Back_Wall',(0,d/2,floor+h/2),(w,.18,h),plaster,.02)
    for x in (-w/2,w/2):box('Room_End_Wall',(x,0,floor+h/2),(.18,d,h),plaster,.02)
    for side in (-1,1):
        span=(w-front_opening)/2;cx=side*(front_opening/2+span/2)
        box('Room_Front_Wall',(cx,-d/2,floor+h/2),(span,.18,h),plaster,.02)
        if span>1.2:window(cx,-d/2-.12,floor+1.65,min(span-.35,1.4),1.25)
    box('Entry_Header',(0,-d/2,floor+h-.2),(front_opening,.23,.4),wood,.025)
    for x in (-front_opening/2,front_opening/2):box('Entry_Jamb',(x,-d/2-.07,floor+(h-.4)/2),(.14,.25,h-.4),wood,.018)
    for x in (-w/2, w/2):
        for y in (-d/2-.35,d/2):post(x,y,floor,h-.25)
    for y in (-d/2-.35,d/2):box('Room_Crossbeam',(0,y,floor+h+.04),(w+.5,.25,.26),wood,.025)

def furnace_copy():
    project=Path(os.environ.get('XIUXIAN_PROJECT','/Users/joshmac/強悍修仙2.0'))
    path=project/'Models/AlchemyFurnace/v001/AlchemyFurnace_v001.blend'
    with bpy.data.libraries.load(str(path),link=False) as (a,b):b.collections=['01_Editable_Asset']
    col=b.collections[0]
    for o in list(col.objects):
        if o.type=='MESH':
            mw=o.matrix_world.copy();o.parent=root;o.matrix_world=mw
            for old in list(o.users_collection):old.objects.unlink(o)
            assets.objects.link(o);o.name='Reused_Furnace_'+o.name
    for o in list(col.objects):bpy.data.objects.remove(o,do_unlink=True)
    bpy.data.collections.remove(col)

def alchemy():
    room_shell(6.8,4.8,.54,3.0,3.4)
    tagged_roof('Alchemy_Roof',8.4,6.7,3.72,1.35)
    plaque('Alchemy_Crest',0,-2.57,3.22,1.9,.45)
    placed(cabinet,(-2.15,1.92,.56))
    placed(furnace_copy,(.1,.0,.56))
    placed(desk,(2.1,1.45,.56))
    # Rear brick exhaust shaft and high open cowl; no smoke particle effect.
    box('Kiln_Flue_Stack',(-2.4,2.8,2.93),(.65,.65,4.74),stone,.035)
    box('Chimney_Collar',(-2.4,2.8,5.25),(.83,.83,.16),pale,.025)
    for x in (-2.68,-2.12):
        for y in (2.52,3.08):box('Chimney_Cowl_Post',(x,y,5.51),(.10,.10,.45),stone,.015)
    box('Chimney_Cap',(-2.4,2.8,5.78),(1.03,1.03,.16),tile,.035)

def scripture():
    room_shell(8.0,5.4,.6,3.0,2.6)
    # Annular lower eaves leave an actual opening for the central upper chamber.
    inner=[(-2.85,-1.85), (2.85,-1.85),(2.85,1.85),(-2.85,1.85)]
    outer=[(-4.9,-3.6),(4.9,-3.6),(4.9,3.6),(-4.9,3.6)]
    for i in range(4):
        j=(i+1)%4;v=[(*inner[i],4.02),(*outer[i],3.38),(*outer[j],3.38),(*inner[j],4.02)]
        o=mesh('Lower_Eave_Panel',v,[(0,1,2,3)],tile);o['roof_reveal']=True;m=o.modifiers.new('Eave_Thickness','SOLIDIFY');m.thickness=.10
        a,b=Vector(v[0]),Vector(v[3]);c,d=Vector(v[1]),Vector(v[2]);n=max(6,int((d-c).length/.3))
        for k in range(n+1):
            p=a+(b-a)*k/n;q=c+(d-c)*k/n
            o=beam('Lower_Eave_Tile_Roll',p,q,.045,tilelight);o['roof_reveal']=True
        o=beam('Lower_Eave_Fascia',c+Vector((0,0,-.07)),d+Vector((0,0,-.07)),.09,wood);o['roof_reveal']=True
    for x in (-2.7,2.7):
        o=box('Upper_Loft_End',(x,0,4.75),(.15,3.15,2.25),plaster,.02);o['roof_reveal']=True
    for y in (-1.65,1.65):
        o=box('Upper_Loft_Wall',(0,y,4.75),(5.5,.15,2.25),plaster,.02);o['roof_reveal']=True
        before=set(assets.objects)
        for x in (-1.7,0,1.7):window(x,y-.1 if y<0 else y+.1,4.8,1.1,1.2)
        for o in set(assets.objects)-before:o['roof_reveal']=True
    tagged_roof('Scripture_Upper_Roof',6.65,4.65,6.0,1.2)
    plaque('Scripture_Crest',0,-2.87,3.25,2,.45)
    for x in (-2.7,0,2.7):placed(shelf,(x,2.25,.62))
    for x in (-2.3,2.3):placed(desk,(x,-.35,.62))

def storehouse():
    room_shell(7.8,5.6,.48,2.8,3.2)
    tagged_roof('Storehouse_Roof',9.2,7.1,3.45,1.35)
    # Wide doors held open as individual editable leaves, with hinge barrels.
    for side in (-1,1):
        leaf=box('Open_Storehouse_Door',(side*1.58,-3.5,1.7),(.13,1.35,2.38),wood,.025)
        for z in (.8,2.5):cyl('Storehouse_Hinge',(side*1.6,-2.82,z),.045,.24,bronze)
        for z in (1.0,2.4):box('Door_Iron_Brace',(side*1.66,-3.5,z),(.035,1.25,.09),bronze,.01)
    plaque('Storehouse_Crest',0,-2.96,3.0,2,.4)
    for x in (-2.6,0,2.6):
        for y in (.7,2.1):placed(chest,(x,y,.5))
    # External buttresses differentiate the utilitarian storage building.
    for x in (-4,4):
        for y in (-1.8,.2,2.2):box('Storage_Buttress',(x,y,1.32),(.32,.34,1.7),stone,.035)

BUILDERS={'AlchemyHall':alchemy,'ScriptureLibrary':scripture,'SectStorehouse':storehouse,'MedicineCabinet':cabinet,'ScrollShelf':shelf,'ReadingDesk':desk,'StorageChest':chest,'DiscipleBed':bed}
NAMES={'AlchemyHall':'煉丹房','ScriptureLibrary':'藏經閣','SectStorehouse':'宗門倉庫','MedicineCabinet':'百子藥櫃','ScrollShelf':'經卷玉簡架','ReadingDesk':'閱讀書案','StorageChest':'宗門儲物箱','DiscipleBed':'弟子床鋪'}
DETAILS={'AlchemyHall':'Open-entry alchemy building, medicine cabinet and reused AlchemyFurnace; static flue, no smoke or alchemy gameplay.','ScriptureLibrary':'Two-tier scripture building with reading area; upper loft exterior only, no stair or accessible upper floor.','SectStorehouse':'Storage building with static open doors, buttresses and separate storage boxes; no interaction.','MedicineCabinet':'Twenty individually editable drawer assemblies; no animation or functional drawer cavities.','ScrollShelf':'Shelving with bamboo scrolls and jade slips; contents are editable but not separately delivered assets.','ReadingDesk':'Reading desk with bamboo tablet, inkstone and brush; static props.','StorageChest':'Hollow box body and separately editable lid; hinge barrels mark the hinge axis; no rig or animation.','DiscipleBed':'Timber bed, woven mattress, pillow and folded quilt; no cloth simulation.'}
def actual_bounds(objects):
    dg=bpy.context.evaluated_depsgraph_get()
    pts=[e.matrix_world@v.co for o in objects for e in [o.evaluated_get(dg)] for v in e.data.vertices]
    return Vector([min(p[i] for p in pts) for i in range(3)]),Vector([max(p[i] for p in pts) for i in range(3)])

ids=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else list(BUILDERS)
for aid in ids:
    out=ROOT/'Models'/aid/'v001';refs=ROOT/'ArtLibrary/Turnarounds'/f'{aid}_v001'
    if (refs/'views.json').exists():print('ALREADY_COMPLETE',aid,flush=True);continue
    out.mkdir(parents=True,exist_ok=True);refs.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;bpy.context.preferences.filepaths.save_version=0
    scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    assets=bpy.data.collections.new('01_Editable_Asset');scene.collection.children.link(assets)
    root=bpy.data.objects.new(aid+'_ROOT',None);assets.objects.link(root);root['stage']=DETAILS[aid]
    wood=mat('Dark_Chestnut',(.16,.065,.028));board=mat('Warm_Timber',(.29,.14,.055))
    stone=mat('Blue_Gray_Stone',(.24,.30,.31));pale=mat('Pale_Stone',(.45,.49,.46));dark=mat('Recess_Shadow',(.065,.085,.08))
    jade=mat('Celadon_Jade',(.08,.29,.24),.18,.32);gold=mat('Aged_Brass',(.51,.31,.075),.6,.34)
    bronze=mat('Socket_Bronze',(.22,.14,.06),.6,.4);plaster=mat('Warm_Lime_Plaster',(.67,.62,.50))
    tile=mat('Blue_Green_Tiles',(.065,.15,.155));tilelight=mat('Tile_Roll_Highlight',(.11,.22,.22))
    paper=mat('Warm_Window_Paper',(.61,.49,.29));soil=mat('Dark_Loam',(.085,.053,.025))
    green=mat('Mature_Herb',(.10,.25,.055));sage=mat('Young_Leaf',(.28,.40,.12))
    rope=mat('Natural_Hemp',(.48,.35,.17));straw=mat('Woven_Straw',(.62,.45,.21));water=mat('Channel_Water',(.055,.20,.20),.2,.18)
    rail_posts=set()
    BUILDERS[aid]();bpy.context.view_layer.update()
    objects=[o for o in assets.objects if o.type=='MESH'];lo,hi=actual_bounds(objects)
    shift=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
    for o in objects:o.location-=shift
    bpy.context.view_layer.update();lo,hi=actual_bounds(objects);centre=(lo+hi)/2;extent=hi-lo
    studio=bpy.data.collections.new('90_Studio_Not_Exported');scene.collection.children.link(studio)
    def studio_obj(name,data):
        o=bpy.data.objects.new(name,data);studio.objects.link(o);return o
    cam=studio_obj('Reference_Camera',bpy.data.cameras.new('Reference_Camera'));scene.camera=cam;cam.data.type='ORTHO'
    cam.data.clip_start=.01;cam.data.clip_end=1000;cam.data.ortho_scale=max(extent.length*1.08,.5)
    # Scale light positions and power with architecture dimensions for consistent exposures.
    ls=max(extent)*.65
    for name,direction,power in [('Key',(-.8,-1.1,1.5),1100),('Fill',(1.2,-.4,.9),650),('Rim',(.2,1.1,1.3),950)]:
        d=bpy.data.lights.new(name,'AREA');d.energy=power*ls*ls/7;d.shape='DISK';d.size=ls
        o=studio_obj(name,d);o.location=centre+Vector(direction)*ls;o.rotation_euler=(centre-o.location).to_track_quat('-Z','Y').to_euler()
    scene.world=bpy.data.worlds.new('Neutral_Studio');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.19,.21,.22,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.65
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=12;scene.cycles.use_denoising=True
    scene.render.resolution_x=1024;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
    def position(direction):
        cam.location=centre+Vector(direction).normalized()*cam.data.ortho_scale*2.3
        cam.rotation_euler=(centre-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
    position((1,-1,.65));bpy.ops.object.select_all(action='DESELECT')
    for o in [root]+objects:o.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.export_scene.fbx(filepath=str(out/(aid+'_v001.fbx')),use_selection=True,object_types={'MESH','EMPTY'},add_leaf_bones=False,axis_forward='-Z',axis_up='Y',apply_unit_scale=True,bake_anim=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/(aid+'_v001.blend')))
    info={'asset':aid,'name_zh':NAMES[aid],'stage':'editable_architecture_prototype','description':DETAILS[aid],'units':'meters','front':'-Y','dimensions_m':list(extent),'mesh_objects':len(objects),'bounds_method':'evaluated mesh vertices','modeling_method':'procedural mesh construction; ten views rendered from the same model','uv_baked':False,'collision':False,'lod':False,'unreal_import_verified':False}
    (out/'model_info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2))
    from bpy_extras.object_utils import world_to_camera_view
    records=[]
    for name,direction in VIEWS:
        position(direction);dg=bpy.context.evaluated_depsgraph_get()
        projected=[world_to_camera_view(scene,cam,e.matrix_world@Vector(p)) for o in objects for e in [o.evaluated_get(dg)] for p in e.bound_box]
        assert all(.005<p.x<.995 and .005<p.y<.995 and p.z>0 for p in projected),(aid,name,'cropped')
        scene.render.filepath=str(refs/(name+'.png'));bpy.ops.render.render(write_still=True)
        records.append({'file':name+'.png','direction':direction,'camera_location':list(cam.location),'projection':'orthographic','framing_checked':True})
        print('VIEW_COMPLETE',aid,name,flush=True)
    (refs/'views.json').write_text(json.dumps({'asset':aid,'source':str((out/(aid+'_v001.blend')).relative_to(ROOT)),'same_geometry':True,'views':records},indent=2))
    if aid in ('AlchemyHall','ScriptureLibrary','SectStorehouse'):
        for o in objects:
            if o.get('roof_reveal'):o.hide_render=True
        position((1,-1,1.15));scene.render.filepath=str(out/'interior_roof_hidden.png');bpy.ops.render.render(write_still=True)
        for o in objects:o.hide_render=False
    print('ASSET_COMPLETE',aid,flush=True)

