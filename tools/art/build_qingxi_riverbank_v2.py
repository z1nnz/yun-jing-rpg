"""Build a textured 12 m Qingxi riverbank module after its AI three-view was saved.

Local Y follows the river. Positive X faces the water. Ground heights are metres.
"""
import json
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
REF=ROOT/'art/references/qingxi-riverbank-v1/three-view.png'
if not REF.is_file(): raise FileNotFoundError('Save and inspect the AI three-view first')
TEX=ROOT/'art/textures/qingxi-riverbank-v2'
for texture in ('stone-albedo.png','path-albedo.png','grass-albedo.png','water-albedo.png'):
    if not (TEX/texture).is_file(): raise FileNotFoundError(TEX/texture)
OUT=ROOT/'art/exports/qingxi-riverbank-v2'
SOURCE=ROOT/'art/source'
PREVIEW=ROOT/'art/previews/qingxi-riverbank-v2'
for d in (OUT,SOURCE,PREVIEW):d.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1

colors={'earth':(.27,.22,.15),'grass':(.24,.36,.19),'path':(.49,.37,.23),
        'stone':(.40,.42,.39),'stone_light':(.57,.56,.49),'moss':(.21,.32,.16),
        'pebble':(.51,.49,.42),'shallow':(.18,.42,.43),'water':(.07,.29,.34),
        'foam':(.54,.72,.66),'reeds':(.31,.43,.19)}
mats={}
for key,rgb in colors.items():
    m=bpy.data.materials.new('M_QXBank_'+key)
    m.diffuse_color=(*rgb,1)
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*rgb,1)
    p.inputs['Roughness'].default_value=.19 if key in ('water','shallow') else .87
    texture={'stone':'stone-albedo.png','stone_light':'stone-albedo.png',
             'path':'path-albedo.png','grass':'grass-albedo.png',
             'water':'water-albedo.png','shallow':'water-albedo.png'}.get(key)
    if texture:
        img=bpy.data.images.load(str(TEX/texture),check_existing=True)
        img.pack()
        node=m.node_tree.nodes.new('ShaderNodeTexImage')
        node.name='Albedo_'+key;node.image=img;node.extension='REPEAT'
        m.node_tree.links.new(node.outputs['Color'],p.inputs['Base Color'])
    mats[key]=m

groups={}
for name in ('Ground','StoneFace','Path','Water','Details'):
    c=bpy.data.collections.new('ASSET_Riverbank_'+name);scene.collection.children.link(c)
    groups[name]=c

def assign_uv(me,scale):
    uv=me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        normal=poly.normal
        axis=max(range(3),key=lambda j:abs(normal[j]))
        for loop in poly.loop_indices:
            p=me.vertices[me.loops[loop].vertex_index].co
            coords=((p.y,p.z),(p.x,p.z),(p.x,p.y))[axis]
            uv.data[loop].uv=(coords[0]*scale,coords[1]*scale)

def create(name,group,vertices,faces,material):
    me=bpy.data.meshes.new(name);me.from_pydata(vertices,[],faces);me.update()
    assign_uv(me,.42 if material in ('grass','path') else .32 if material in ('stone','stone_light') else .22 if material in ('water','shallow') else 1)
    ob=bpy.data.objects.new('SM_QXBank_'+name,me);groups[group].objects.link(ob)
    me.materials.append(mats[material]);return ob

def grid(name,group,x_values,y_values,height,material):
    verts=[(x,y,height(x,y)) for y in y_values for x in x_values]
    faces=[]; nx=len(x_values)
    for j in range(len(y_values)-1):
        for i in range(nx-1):
            a=j*nx+i;faces.append((a,a+1,a+nx+1,a+nx))
    return create(name,group,verts,faces,material)

def bank_x(y):return -.12+.25*math.sin(math.pi*y/6)+.13*math.sin(3*math.pi*y/6)
def upper_z(x,y):
    ramp=max(0,min(1,(x+5)/4.8))
    return .13+.41*ramp+.025*math.sin(y*.64)*math.sin(math.pi*max(0,x+5)/5)
ys=[-6+i*.5 for i in range(25)]
xs=[-5.0+i*.25 for i in range(22)]
grid('Raised grass bank','Ground',xs,ys,upper_z,'grass')

# An irregular stepped stone-and-earth cross-section. The exposed upper edge
# follows a single mathematical curve, so adjacent copies connect at Y=+-6.
verts=[];faces=[]
cross=[(-.15,.56),(.05,.49),(.27,.36),(.53,.28),(.82,.14),(1.22,.07)]
for y in ys:
    bend=bank_x(y)
    for xx,zz in cross:
        verts.append((xx+bend,y,zz+.018*math.sin(y*1.4+xx*5)))
for j in range(len(ys)-1):
    for i in range(len(cross)-1):
        a=j*len(cross)+i;faces.append((a,a+1,a+1+len(cross),a+len(cross)))
create('Layered stone slope','StoneFace',verts,faces,'stone')

# The compacted path remains broad enough for an approximate 2 m character
# controller and sits back from the unstable outer edge.
def path_h(x,y):return upper_z(x,y)+.012
path_verts=[];path_faces=[];path_steps=13
for y in ys:
    # All terms meet at equal endpoint values so copies tile without a jump.
    center=-3.02+.41*math.sin(math.pi*y/6)+.16*math.sin(3*math.pi*y/6)
    width=2.34+.20*math.cos(2*math.pi*y/6)+.10*math.sin(4*math.pi*y/6)
    for i in range(path_steps):
        t=i/(path_steps-1)
        edge_wobble=(1-t)*.13*math.sin(5*math.pi*y/6)+t*.11*math.sin(7*math.pi*y/6)
        x=center+width*(t-.5)+edge_wobble
        path_verts.append((x,y,path_h(x,y)))
for j in range(len(ys)-1):
    for i in range(path_steps-1):
        a=j*path_steps+i
        path_faces.append((a,a+1,a+1+path_steps,a+path_steps))
create('Compacted footpath','Path',path_verts,path_faces,'path')

# Pebble shelf and two water color bands. These are opaque preview materials;
# a real URP water shader and collision are separate later tasks.
grid('Shallow pebble shelf','Ground',[1.16+i*.19 for i in range(12)],ys,
     lambda x,y:.055-.018*(x-1.16),'pebble')
def shallow_water_z(x,y):return .085+.008*math.sin(y*2.1+x*2)
grid('Shallow water color','Water',[1.12+i*.21 for i in range(13)],ys,
     shallow_water_z,'shallow')
def deep_water_z(x,y):
    t=max(0,min(1,(x-3.64)/.3))
    return (1-t)*shallow_water_z(3.64,y)+t*(.075+.012*math.sin(y*2+x*2.3))
grid('Deep water color','Water',[3.64+i*.26 for i in range(13)],ys,
     deep_water_z,'water')
foam_verts=[];foam_faces=[]
for y in ys:
    edge=1.31+bank_x(y)
    foam_verts.extend([(edge,y,.101),(edge+.055,y,.101)])
for j in range(len(ys)-1):
    a=j*2;foam_faces.append((a,a+1,a+3,a+2))
create('Shoreline foam trace','Water',foam_verts,foam_faces,'foam')

def ico(name,center,scale,mat):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=1,location=center)
    ob=bpy.context.object;ob.name='SM_QXBank_'+name
    for c in list(ob.users_collection):c.objects.unlink(ob)
    groups['Details'].objects.link(ob)
    ob.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    ob.data.materials.append(mats[mat])
    return ob

rng=random.Random(251025)
for i,(y,x,s) in enumerate(((-4.8,.18,.55),(-3.1,.65,.41),(-1.2,.28,.68),
                             (.9,.62,.44),(2.6,.24,.58),(4.7,.72,.62))):
    ico('Shore boulder %02d'%i,(x,y,.25),(.65*s/.55,.50*s/.55,.45*s/.55),
        'stone_light' if i%3==0 else 'stone')
for row in range(2):
    for i in range(17):
        y=-5.62+i*.69+(row%2)*.30
        if y>5.85:continue
        x=bank_x(y)+(.34 if row==0 else .80)
        z=.35 if row==0 else .19
        ico('Stone course %d %02d'%(row,i),(x,y,z),
            (.23,.25,.12) if row==0 else (.20,.24,.10),
            'stone_light' if (i+row)%5==0 else 'stone')
for i in range(11):
    y=-5.3+i*1.04
    x=bank_x(y)+(.12 if i%2 else .57)
    z=.52 if i%2 else .28
    ico('Moss in joints %02d'%i,(x,y,z),(.15,.19,.07),'moss')
placed_pebbles=[]
for i in range(50):
    for attempt in range(40):
        y=rng.uniform(-5.8,5.8);x=rng.uniform(1.26,2.35);radius=rng.uniform(.035,.12)
        if all((x-px)**2+(y-py)**2>(radius+pr+.025)**2
               for px,py,pr in placed_pebbles):
            break
    else:
        continue
    placed_pebbles.append((x,y,radius))
    ico('Pebble %02d'%i,(x,y,.095),(radius,radius*.8,radius*.5),
        'stone_light' if i%6==0 else 'pebble')

# Small foliage rosettes near stone seams. These are simple shapes and remain
# in the model rather than referencing external live assets.
for i in range(18):
    y=-5.5+i*.64+rng.uniform(-.19,.19)
    x=rng.choice([-.48,.34,.92])+rng.uniform(-.15,.15)
    z=max(.10,.52-.34*max(0,x))
    for k in range(3):
        theta=(k*2*math.pi/3)+rng.uniform(-.2,.2)
        tip=(x+.12*math.cos(theta),y+.12*math.sin(theta),z+.23)
        base=(x+.045*math.cos(theta),y+.045*math.sin(theta),z)
        verts=[base,(x,y,z),tip,(x+.05*math.sin(theta),y-.05*math.cos(theta),z+.025)]
        create(f'Reed {i} {k}','Details',verts,[(0,1,2),(1,3,2)],'reeds')

# Narrow stone treads are visible from the walking path and interrupt the
# retaining wall in two places, as in the saved three-view reference.
def tread(name,x,y,z,width=.32,length=1.05,thick=.105):
    a=x-width/2;b=x+width/2;c=y-length/2;d=y+length/2
    bot=z-thick;top=z
    verts=[(a,c,bot),(b,c,bot),(b,d,bot),(a,d,bot),
           (a,c,top),(b,c,top),(b,d,top),(a,d,top)]
    faces=[(4,5,6,7),(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    create(name,'Details',verts,faces,'stone_light')
for run_y in (-1.9,3.4):
    for step in range(4):
        tread(f'Water access {run_y} step {step}',.03+step*.31,run_y,
              .60-step*.135)

# A single joined leaf mesh keeps hundreds of grass blades inexpensive in the
# GLB while adding a 3D silhouette that a flat ground texture cannot supply.
leaf_verts=[];leaf_faces=[]
for row_x in (-4.82,-4.51,-1.62,-.95,-.43,.22,.76):
    for index in range(28):
        y=-5.82+index*.43+rng.uniform(-.12,.12)
        x=row_x+rng.uniform(-.15,.15)
        if row_x>-.4:
            x+=bank_x(y)
            z=max(.12,.52-.35*max(0,x))
        else:
            z=upper_z(x,y)+.014
        for blade in range(5):
            angle=blade*2*math.pi/5+rng.uniform(-.35,.35)
            height=rng.uniform(.09,.29) if row_x<-.4 else rng.uniform(.16,.41)
            radius=rng.uniform(.055,.12)
            dx=math.cos(angle);dy=math.sin(angle)
            bend=rng.uniform(.03,.10)
            base=len(leaf_verts)
            leaf_verts.extend([
                (x-radius*dy*.5,y+radius*dx*.5,z),
                (x+radius*dy*.5,y-radius*dx*.5,z),
                (x+bend*dx-radius*dy*.32,y+bend*dy+radius*dx*.32,z+height*.65),
                (x+bend*dx+radius*dy*.32,y+bend*dy-radius*dx*.32,z+height*.65),
                (x+2*bend*dx,y+2*bend*dy,z+height),
            ])
            leaf_faces.extend([(base,base+1,base+3,base+2),
                               (base+2,base+3,base+4)])
create('Dense grass and reed blades','Details',leaf_verts,leaf_faces,'reeds')

asset=[o for col in groups.values() for o in col.objects if o.type=='MESH']
tris=sum(len(p.vertices)-2 for o in asset for p in o.data.polygons)
report={'asset':'Qingxi riverbank 12m module v2','reference':str(REF.relative_to(ROOT)),
        'length_m':12,'mesh_objects_source':len(asset),'triangles_source':tris,
        'height_land_m':.54,'water_level_m':.08,
        'textures':['stone-albedo.png','path-albedo.png','grass-albedo.png','water-albedo.png'],
        'limits':'visual module; AI texture tiling, normal maps, shader/collision/LOD/Unity/mobile unverified'}
(OUT/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/'qingxi-riverbank-v2.blend'))

# Merge by material only for export; retain unmerged Blender source for editing.
mapping={key:[o.name for o in asset if o.data.materials and o.data.materials[0]==mats[key]]
         for key in mats}
batched=[]
for key,names in mapping.items():
    if not names:continue
    group=[bpy.data.objects[n] for n in names]
    bpy.ops.object.select_all(action='DESELECT')
    for o in group:o.select_set(True)
    bpy.context.view_layer.objects.active=group[0]
    bpy.ops.object.join();ob=bpy.context.view_layer.objects.active
    ob.name='SM_QXBank_Batched_'+key;batched.append(ob)
report['mesh_objects_export']=len(batched)
(OUT/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
bpy.ops.object.select_all(action='DESELECT')
for ob in batched:ob.select_set(True)
bpy.context.view_layer.objects.active=batched[0]
bpy.ops.export_scene.fbx(filepath=str(OUT/'qingxi-riverbank-v2.fbx'),use_selection=True,
    axis_forward='-Z',axis_up='Y',add_leaf_bones=False,bake_anim=False,
    use_mesh_modifiers=True,mesh_smooth_type='FACE')
bpy.ops.export_scene.gltf(filepath=str(OUT/'qingxi-riverbank-v2.glb'),
    export_format='GLB',use_selection=True,export_apply=True)

sun_data=bpy.data.lights.new('Bank afternoon','SUN');sun_data.energy=1.7
sun=bpy.data.objects.new('Bank afternoon',sun_data);scene.collection.objects.link(sun)
sun.rotation_euler=Vector((-.5,.6,-1)).to_track_quat('-Z','Y').to_euler()
scene.world.use_nodes=True
background=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND')
background.inputs['Color'].default_value=(.64,.76,.86,1)
background.inputs['Strength'].default_value=.8
scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=1500;scene.render.resolution_y=900
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX'
scene.view_settings.look='AgX - Medium High Contrast'
def cam(name,loc,target):
    data=bpy.data.cameras.new(name);ob=bpy.data.objects.new(name,data)
    scene.collection.objects.link(ob);ob.location=loc
    ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
    data.lens=37;return ob
for name,loc in [('river-oblique',(13,-15,11)),('path-to-water',(-10,-13,6))]:
    scene.camera=cam(name,loc,(0,0,.1));scene.render.filepath=str(PREVIEW/(name+'.png'))
    bpy.ops.render.render(write_still=True)
print('@@BANK@@'+json.dumps(report,ensure_ascii=False))
