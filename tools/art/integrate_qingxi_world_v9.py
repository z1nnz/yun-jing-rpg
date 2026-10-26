"""Ground the existing Tree Companion tree and dress Qingxi's river road.

Source: v8 Blender art scene. This is look development, not Unity validation.
"""
import json
import math
import random
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT/'art/source/qingxi-world-flora-water-v8.blend'
REF = ROOT/'art/references/qingxi-detail-props-v2/three-view.png'
PROP = ROOT/'art/exports/qingxi-detail-props-v2'
OUT = ROOT/'art/previews/qingxi-world-v9'
OUT.mkdir(parents=True, exist_ok=True)
if not SOURCE.exists() or not REF.exists():
    raise FileNotFoundError('v8 source and saved three-view are required')
scene=bpy.context.scene
col=bpy.data.collections.new('WORLD_V9_GroundedTree_RoadDetails')
scene.collection.children.link(col)

# v8 copied tree geometry kept its source offset: lowest visible trunk was
# 3.28 m above world zero. Lower all three source meshes as one intact tree.
tree=[o for o in bpy.data.objects if o.name.startswith('ELDER_WORLD_TREE_HERO_') and o.type=='MESH']
assert len(tree)==3, f'Expected existing three-mesh Tree Companion hero, got {len(tree)}'
root_before=min((o.matrix_world@Vector(c)).z for o in tree for c in o.bound_box)
ground_shift=root_before-.59
for ob in tree:
    ob.location.z-=ground_shift
bpy.context.view_layer.update()
root_after=min((o.matrix_world@Vector(c)).z for o in tree for c in o.bound_box)
assert .55<root_after<.63


def imported_template(key):
    previous=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(PROP/f'qingxi-{key}-v2.glb'))
    source=[o for o in bpy.data.objects if o not in previous and o.type=='MESH']
    if not source: raise RuntimeError('Missing '+key)
    # Merge one asset's many authoring pieces into a few instanced material
    # batches. Source .blend retains the individual editable meshes.
    result=[]
    by_material={}
    for ob in source:
        if ob.data.materials:
            by_material.setdefault(ob.data.materials[0].name,[]).append(ob)
    for mat_name,group in sorted(by_material.items()):
        if 'RootSoil' in mat_name:
            # Authoring pads keep each isolated foliage asset QA-connected.
            # In the assembled world the terrain supplies that soil instead.
            for ob in group:ob.hide_render=True
            continue
        bpy.ops.object.select_all(action='DESELECT')
        for ob in group: ob.select_set(True)
        bpy.context.view_layer.objects.active=group[0]
        bpy.ops.object.join()
        joined=group[0]
        joined.name='TEMPLATE_V9_'+key+'_'+mat_name
        for old in list(joined.users_collection): old.objects.unlink(joined)
        col.objects.link(joined)
        joined.hide_render=True
        result.append(joined)
    return result


templates={key:imported_template(key) for key in
           ('river-reed','fern-flower','moss-boulder','trail-lantern')}
rng=random.Random(20261026)
counts={key:0 for key in templates}
def place(key, x,y,z, scale, angle=0):
    transform=Matrix.Translation(Vector((x,y,z))) @ Matrix.Rotation(angle,4,'Z') @ Matrix.Scale(scale,4)
    for part in templates[key]:
        ob=part.copy()
        ob.data=part.data
        col.objects.link(ob)
        ob.name=f'V9_{key}_{counts[key]:03d}_{part.name}'
        ob.hide_render=False
        ob.matrix_world=transform @ part.matrix_world
    counts[key]+=1


# Bank slope coordinates are inherited from the v8 strip source: bank x=19,
# path roughly x=15..18; river starts around x=20. Plant in alternating,
# irregular patches rather than evenly repeated rows.
for cy in (-54,-42,-30,-18,-6,6,18):
    patches=[(cy+rng.uniform(-4.7,4.7),rng.uniform(1.8,3.6)) for _ in range(5)]
    for patch_y,span in patches:
        for j in range(rng.randint(5,9)):
            y=max(cy-5.75,min(cy+5.75,patch_y+rng.gauss(0,span*.35)))
            side=rng.choice((-1,1))
            x=19+((-4.65 if side<0 else -.47)+rng.uniform(-.36,.36))
            local=x-19
            z=.15+.41*max(0,min(1,(local+5)/4.8))+.05
            if local>.2:z=max(.23,.53-.34*local)+.05
            key='river-reed' if side>0 and j%5==0 else 'fern-flower'
            place(key,x,y,z,rng.uniform(.64,1.15),rng.uniform(0,math.tau))
    for j in range(5):
        y=cy+rng.uniform(-5.4,5.4)
        x=19+rng.choice((-.42,.15,.7,1.15))+rng.uniform(-.18,.18)
        z=.25 if x>20 else .40
        place('moss-boulder',x,y,z-.08,rng.uniform(.35,.9),rng.uniform(0,math.tau))

# Distinct landmarks, well clear of tree roots and bridge clearance.
for x,y,z in ((14.2,-41.5,.66),(14.1,-17.0,.66),(14.25,10.0,.66)):
    place('trail-lantern',x,y,z,1.0,math.pi/2)

# Dress the root/soil contact with dense vegetation and embedded stones.
for i in range(32):
    a=rng.uniform(0,math.tau);r=rng.uniform(.7,3.45)
    x,y=12+r*math.cos(a),5+r*math.sin(a)
    t=r/3.9
    z=.10+.86*(1-t*t)**2
    if i%7==0:
        place('moss-boulder',x,y,z-.16,rng.uniform(.22,.46),a)
    else:
        place('fern-flower',x,y,z-.025,
              rng.uniform(.35,.72),a)

scene.frame_set(36)
output=ROOT/'art/source/qingxi-world-detailed-v9.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output))

def camera(name,position,target,lens=44):
    data=bpy.data.cameras.new(name)
    data.lens=lens
    ob=bpy.data.objects.new(name,data)
    scene.collection.objects.link(ob)
    ob.location=position
    ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
    return ob

scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=1600;scene.render.resolution_y=900
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX'
views=(('tree-root-canopy', (20,-9,7.5), (12,5,4.25),36),
       ('river-road-details',(32,-31,10),(17,-21,.35),48))
for name,pos,target,lens in views:
    cam=camera('CAM_V9_'+name,pos,target,lens)
    scene.camera=cam
    scene.render.filepath=str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam,do_unlink=True)

report={'source_scene':str(SOURCE.relative_to(ROOT)),
        'tree_source':'latest Tree Companion authoring file; same SHA256 as copied local source',
        'tree_root_before_m':round(root_before,3),'tree_root_after_m':round(root_after,3),
        'tree_vertical_correction_m':round(ground_shift,3),
        'reference_props':str(REF.relative_to(ROOT)),'instances':counts,
        'owner':'z1nnz / Codex-assisted integration',
        'limits':'Blender visual preview; Unity compilation, collider, runtime LOD and mobile tests pending'}
(OUT/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('@@V9@@'+json.dumps(report,ensure_ascii=False))
