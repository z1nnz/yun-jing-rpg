"""Scatter modular flora, ground the elder tree, and animate preview river water.

Run against qingxi-world-lookdev-v7.blend with Blender 5.2. This is a Blender
look-development animation, not a compiled Unity water implementation.
"""
import json
import math
import random
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT=Path(__file__).resolve().parents[2]
for reference in ('art/references/qingxi-prop-kit-v1/three-view.png',
                  'art/references/qingxi-root-transition-v1/three-view.png'):
    if not (ROOT/reference).is_file():raise FileNotFoundError(reference)
OUT=ROOT/'art/previews/qingxi-world-v8';OUT.mkdir(parents=True,exist_ok=True)
scene=bpy.context.scene
col=bpy.data.collections.new('WORLD_V8_GroundedTree_Flora_Water')
scene.collection.children.link(col)

# Existing reed rows are part of the imported bank modules. Replace those
# entirely with independently authored, size-varied tufts and flowers.
removed=[]
for ob in list(bpy.data.objects):
    if ob.name.startswith('RIVERBANK_') and 'Batched_reeds' in ob.name:
        removed.append(ob.name)
        bpy.data.objects.remove(ob,do_unlink=True)

def import_prop(key):
    before=set(bpy.data.objects.keys())
    bpy.ops.import_scene.gltf(filepath=str(ROOT/f'art/exports/qingxi-prop-kit-v1/qingxi-{key}-v1.glb'))
    group=[o for o in bpy.data.objects if o.name not in before and o.type=='MESH']
    if not group:raise RuntimeError('Missing prop '+key)
    for ob in group:
        for old in list(ob.users_collection):old.objects.unlink(ob)
        col.objects.link(ob)
    return group

templates={key:import_prop(key) for key in ('grass','wildflower','cobble')}
for group in templates.values():
    for ob in group:ob.hide_render=True

rng=random.Random(20261025)
counts={'grass':0,'wildflower':0,'cobble':0}
def plant(key,pos,scale,turn):
    transform=Matrix.Translation(Vector(pos)) @ Matrix.Rotation(turn,4,'Z') @ Matrix.Scale(scale,4)
    for prototype in templates[key]:
        ob=prototype.copy();ob.data=prototype.data
        col.objects.link(ob)
        ob.hide_render=False
        ob.matrix_world=transform @ prototype.matrix_world
        ob.name=f'V8_{key}_{counts[key]:03d}_{prototype.name}'
    counts[key]+=1

# Seven 12 m riverbank sections. Random positions use the same fixed seed on
# every build, so art revisions can be compared frame by frame.
bank_centers=(-54,-42,-30,-18,-6,6,18)
for cy in bank_centers:
    for i in range(48):
        y=cy+rng.uniform(-5.8,5.8)
        x=19+rng.choice((-4.70,-4.18,-1.48,-.80,-.18,.40)) + rng.uniform(-.28,.28)
        # Keep the character path clear and concentrate plants along edges.
        if -4.0<x-19<-1.9:continue
        local_x=x-19
        z=.15+.41*max(0,min(1,(local_x+5)/4.8))+.047
        if local_x>.2:z=max(.23,.53-.34*local_x)+.047
        kind='wildflower' if i%7==0 else 'grass'
        plant(kind,(x,y,z),rng.uniform(.6,1.55),rng.uniform(0,math.tau))
    for i in range(6):
        y=cy+rng.uniform(-5.6,5.6)
        x=19+rng.choice((-.45,.30,.75,1.26))+rng.uniform(-.18,.18)
        z=.23 if x>20 else .40
        plant('cobble',(x,y,z),rng.uniform(.45,1.25),rng.uniform(0,math.tau))

# The previous tree sat partly over the river. Pull the copied geometry toward
# the trunk below 2.6 m, then plant it on an irregular bank-side earth mound.
tree=[o for o in bpy.data.objects if o.name.startswith('ELDER_WORLD_TREE_HERO_') and o.type=='MESH']
if len(tree)!=3:raise RuntimeError(f'Expected three hero tree meshes, got {len(tree)}')
old_x,old_y=19,-7
new_x,new_y=12,5
for ob in tree:
    ob.data=ob.data.copy()
    for vert in ob.data.vertices:
        p=vert.co
        h=max(0,min(1,p.z/2.7))
        rad=math.hypot(p.x,p.y)
        if rad>1.0 and h<1:
            factor=.43+.57*h
            p.x*=factor;p.y*=factor
            p.z=max(0,p.z-.15*(1-h))
    ob.matrix_world.translation+=Vector((new_x-old_x,new_y-old_y,.20))

grass=bpy.data.materials.get('M_QXBank_grass')
if grass is None:raise RuntimeError('Missing meadow material')
verts=[];faces=[]
rings=7;steps=48
for ring in range(rings):
    t=ring/(rings-1)
    radius=.22+3.65*t
    for i in range(steps):
        angle=math.tau*i/steps
        edge=1+.07*math.sin(5*angle)+.045*math.sin(11*angle+1.3)
        r=radius*edge
        z=.08+.86*(1-t*t)**2+.025*math.sin(7*angle+2*t)
        verts.append((new_x+r*math.cos(angle),new_y+r*math.sin(angle),z))
for ring in range(rings-1):
    for i in range(steps):
        j=(i+1)%steps
        a=ring*steps+i;b=ring*steps+j
        faces.append((a,b,b+steps,a+steps))
mesh=bpy.data.meshes.new('V8 tree root soil mound');mesh.from_pydata(verts,[],faces);mesh.update()
uv=mesh.uv_layers.new(name='UVMap')
for poly in mesh.polygons:
    for li in poly.loop_indices:
        p=mesh.vertices[mesh.loops[li].vertex_index].co
        uv.data[li].uv=(p.x*.23,p.y*.23)
mound=bpy.data.objects.new('SM_QX_V8_TreeRootMound',mesh);col.objects.link(mound)
mesh.materials.append(grass)
for i in range(42):
    theta=rng.uniform(0,math.tau);rad=rng.uniform(1.55,3.75)
    x=new_x+rad*math.cos(theta);y=new_y+rad*math.sin(theta)
    t=rad/3.9;z=.10+.86*(1-t*t)**2
    plant('grass' if i%5 else 'wildflower',(x,y,z),rng.uniform(.65,1.4),theta)
for i in range(11):
    theta=rng.uniform(0,math.tau);rad=rng.uniform(2.1,3.6)
    t=rad/3.9
    plant('cobble',(new_x+rad*math.cos(theta),new_y+rad*math.sin(theta),
                    .10+.86*(1-t*t)**2),rng.uniform(.55,1.35),theta)

# The river runs north-to-south in this sample. Animate both UV drift and
# irregular surface height, plus a few centimetres of shoreline breathing.
water=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('RIVERBANK_')
       and ('Batched_water' in o.name or 'Batched_shallow' in o.name)]
foam=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('RIVERBANK_')
      and 'Batched_foam' in o.name]
if len(water)<7:raise RuntimeError('Water meshes missing from v7 scene')
for ob in water:
    ob.data=ob.data.copy()
    base_z=ob.location.z
    basis=ob.shape_key_add(name='Still baseline')
    rise=ob.shape_key_add(name='Flow ripple A')
    fall=ob.shape_key_add(name='Flow ripple B')
    for idx,vertex in enumerate(ob.data.vertices):
        world=ob.matrix_world @ vertex.co
        rise.data[idx].co.z+=.014*math.sin(world.y*1.8+world.x*2.6)+.008*math.sin(world.y*4.1)
        fall.data[idx].co.z+=.013*math.sin(world.y*1.8+world.x*2.6+2.1)+.006*math.sin(world.y*3.4+1.2)
    for frame,ra,fa,level in ((1,0,0,0),(36,1,0,.032),(78,0,1,-.018),(121,0,0,0)):
        rise.value=ra;fall.value=fa
        rise.keyframe_insert(data_path='value',frame=frame)
        fall.keyframe_insert(data_path='value',frame=frame)
        ob.location.z=base_z+level
        ob.keyframe_insert(data_path='location',frame=frame)
for ob in foam:
    start=ob.location.x
    for frame,offset in ((1,0),(36,.07),(78,-.045),(121,0)):
        ob.location.x=start+offset
        ob.keyframe_insert(data_path='location',frame=frame)

animated_materials=[]
for mat in bpy.data.materials:
    if not mat.use_nodes or 'QXBank_water' not in mat.name and 'QXBank_shallow' not in mat.name:
        continue
    image=next((node for node in mat.node_tree.nodes if node.type=='TEX_IMAGE'),None)
    if image is None:continue
    image.extension='REPEAT'
    uvnode=mat.node_tree.nodes.new('ShaderNodeUVMap');uvnode.uv_map='UVMap'
    flow=mat.node_tree.nodes.new('ShaderNodeVectorMath');flow.operation='ADD'
    mat.node_tree.links.new(uvnode.outputs['UV'],flow.inputs[0])
    mat.node_tree.links.new(flow.outputs[0],image.inputs['Vector'])
    for frame,scroll in ((1,0),(121,1.6)):
        flow.inputs[1].default_value=(0,scroll,0)
        flow.inputs[1].keyframe_insert(data_path='default_value',frame=frame)
    animated_materials.append(mat.name)

scene.frame_start=1;scene.frame_end=121;scene.render.fps=30
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/source/qingxi-world-flora-water-v8.blend'))
camera=bpy.data.objects.get('CAM_V7_BankOverview')
if camera is None:raise RuntimeError('Missing overview camera')
scene.camera=camera
scene.render.resolution_x=1600;scene.render.resolution_y=900
for frame in (1,36,78):
    scene.frame_set(frame)
    scene.render.filepath=str(OUT/f'riverbank-flow-frame-{frame:03d}.png')
    bpy.ops.render.render(write_still=True)
report={'reference_props':'art/references/qingxi-prop-kit-v1/three-view.png',
        'reference_roots':'art/references/qingxi-root-transition-v1/three-view.png',
        'removed_uniform_grass_meshes':len(removed),'prop_instances':counts,
        'tree_new_position_m':[new_x,new_y],'tree_root_contraction_below_m':2.7,
        'water_meshes_animated':len(water),'foam_meshes_animated':len(foam),
        'flow_materials':animated_materials,'water_vertical_amplitude_m':.032,
        'limits':'Blender animation preview only; no Unity shader, current collision, buoyancy or gameplay tests'}
(OUT/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('@@V8@@'+json.dumps(report,ensure_ascii=False))
