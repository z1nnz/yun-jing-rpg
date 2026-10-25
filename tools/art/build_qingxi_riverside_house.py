"""Build the Qingxi riverside guesthouse after its AI three-view was saved.

Run with Blender 5.2 in background. Units are metres; front faces -Y.
This is a modular visual asset, not yet a Unity prefab or collider setup.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / 'art/references/qingxi-riverside-house-v1/three-view.png'
if not REF.is_file():
    raise FileNotFoundError('AI three-view must be saved and inspected before modeling')
OUT = ROOT / 'art/exports/qingxi-riverside-house-v1'
PREVIEW = ROOT / 'art/previews/qingxi-riverside-house-v1'
SOURCE = ROOT / 'art/source'
for p in (OUT, PREVIEW, SOURCE):
    p.mkdir(parents=True, exist_ok=True)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1

palette = {
    'stone': (.39,.43,.40), 'stone_light': (.57,.57,.49),
    'moss': (.26,.36,.22), 'wood': (.31,.19,.105),
    'wood_light': (.49,.32,.17), 'wood_dark': (.16,.115,.075),
    'plaster': (.68,.64,.52), 'tile': (.065,.105,.13),
    'tile_edge': (.14,.19,.21), 'bronze': (.37,.285,.13),
    'glass': (.39,.51,.50), 'lantern': (.88,.58,.26),
}
materials = {}
for name, color in palette.items():
    m = bpy.data.materials.new('M_QX_'+name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    shader = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    shader.inputs['Base Color'].default_value = (*color,1)
    shader.inputs['Roughness'].default_value = .83 if name != 'glass' else .29
    if name == 'lantern':
        shader.inputs['Emission Color'].default_value = (*color,1)
        shader.inputs['Emission Strength'].default_value = .8
    materials[name] = m

parts = {}
for name in ('Foundation','Frame','Walls','Openings','Roof','Details'):
    c = bpy.data.collections.new('ASSET_House_'+name)
    scene.collection.children.link(c)
    parts[name] = c

def link(obj, part, material):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    parts[part].objects.link(obj)
    obj.data.materials.append(materials[material])
    return obj

def box(part, name, loc, dims, material, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = link(bpy.context.object,part,material)
    o.name='SM_QX_'+name
    o.dimensions=dims
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        mod=o.modifiers.new('Softened edges','BEVEL')
        mod.width=bevel; mod.segments=1
        bpy.context.view_layer.objects.active=o
        bpy.ops.object.modifier_apply(modifier=mod.name)
        o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
    return o

def beam(part,name,a,b,r,material,sides=6):
    a,b=Vector(a),Vector(b)
    d=b-a
    bpy.ops.mesh.primitive_cylinder_add(vertices=sides,radius=r,depth=d.length,
                                        end_fill_type='TRIFAN',location=(a+b)/2)
    o=link(bpy.context.object,part,material)
    o.name='SM_QX_'+name
    o.rotation_euler=d.to_track_quat('Z','Y').to_euler()
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    return o

def mesh(part,name,verts,faces,material):
    me=bpy.data.meshes.new(name)
    me.from_pydata(verts,[],faces); me.update()
    uv=me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        normal=poly.normal
        axis=max(range(3),key=lambda i:abs(normal[i]))
        for loop_index in poly.loop_indices:
            xyz=me.vertices[me.loops[loop_index].vertex_index].co
            uv.data[loop_index].uv=([(xyz.y,xyz.z),(xyz.x,xyz.z),(xyz.x,xyz.y)][axis])
    o=bpy.data.objects.new('SM_QX_'+name,me)
    parts[part].objects.link(o)
    me.materials.append(materials[material])
    return o

def roof_z(x,y):
    # x is along the ridge. Eaves curve gently upward at both ends.
    t=min(1,abs(y)/4.08)
    return 6.42-2.08*t + .34*t**4 + .18*(abs(x)/5.02)**6*t**3

# Stone plinth, pier caps, irregular exposed blocks and entrance stairs.
box('Foundation','Plinth',(0,0,.54),(9.35,7.35,1.08),'stone',.035)
box('Foundation','Upper course',(0,0,1.10),(9.44,7.42,.17),'stone_light',.025)
for side,y in enumerate((-3.7,3.7)):
    for row in range(2):
        for i in range(15):
            x=-4.51+i*.645+(row%2)*.13
            if x>4.53: continue
            w=.57+((i*7+row*3)%4)*.015
            box('Foundation',f'Stone {side} {row} {i}',(x,y+(.025 if side else -.025),.23+row*.47),(w,.13,.40),'stone_light' if (i+row)%5==0 else 'stone')
for j in range(3):
    box('Foundation',f'Front stair {j}',(0,-4.30-j*.28,.60-j*.19),(2.5+j*.25,.58,.19),'stone_light',.02)

# Floor, warm timber frame and pale wall panels.
box('Frame','Porch deck',(0,-3.05,1.24),(9.05,1.52,.16),'wood_light')
box('Walls','Central wall',(0,.12,2.83),(8.45,5.45,3.25),'plaster')
for x in (-4.16,-2.75,-1.38,0,1.38,2.75,4.16):
    for y in (-3.72,3.15):
        box('Frame',f'Column {x} {y}',(x,y,2.75),(.22,.22,3.22),'wood',.025)
        box('Foundation',f'Column shoe {x} {y}',(x,y,1.28),(.31,.31,.36),'stone_light')
for y in (-3.73,3.16):
    for z in (1.55,4.24):
        box('Frame',f'Long beam {y} {z}',(0,y+(.035 if y<0 else -.035),z),(8.85,.18,.23),'wood_dark',.015)
for x in (-4.17,4.17):
    for z in (1.58,4.22):
        box('Frame',f'Side beam {x} {z}',(x+(.06 if x<0 else -.06),-.24,z),(.18,6.95,.20),'wood_dark')
for x in (-4.15,-2.75,-1.38,0,1.38,2.75,4.15):
    # bracket layers visibly support the broad eave
    for y in (-3.72,3.16):
        box('Details',f'Bracket lower {x} {y}',(x,y,4.42),(.48,.39,.18),'wood_light')
        box('Details',f'Bracket upper {x} {y}',(x,y,4.72 if y>0 else 4.59),(.32,.62,.18),'wood_dark')

# Windows: dark recess, framing, copper-blue panes and lattice bars.
def window(label,x,y,z,width=1.03,height=1.28,side=False):
    if side:
        box('Openings',label+' glass',(x,y,z),(.065,width,height),'glass')
        for yy in (y-width/2,y+width/2):
            box('Openings',label+' upright',(x,yy,z),(.12,.085,height-.10),'wood_dark')
        for zz in (z-height/2,z+height/2):
            box('Openings',label+' sill',(x,y,zz),(.12,width+.15,.09),'wood_light')
        for k in (-1,0,1):
            box('Openings',label+' lattice v',(x-.085,y+k*width/4,z),(.036,.035,height),'wood_dark')
        for k in (-1,0,1):
            box('Openings',label+' lattice h',(x-.11,y,z+k*height/4),(.036,width,.035),'wood_dark')
    else:
        box('Openings',label+' glass',(x,y,z),(width,.065,height),'glass')
        for xx in (x-width/2,x+width/2):
            box('Openings',label+' upright',(xx,y,z),(.085,.12,height-.10),'wood_dark')
        for zz in (z-height/2,z+height/2):
            box('Openings',label+' sill',(x,y,zz),(width+.15,.12,.09),'wood_light')
        for k in (-1,0,1):
            box('Openings',label+' lattice v',(x+k*width/4,y-.085,z),(.035,.036,height),'wood_dark')
            box('Openings',label+' lattice h',(x,y-.11,z+k*height/4),(width,.036,.035),'wood_dark')
for i,x in enumerate((-3.36,-1.90,1.90,3.36)):
    window(f'Front window {i}',x,-2.65,2.71)
    window(f'Rear window {i}',x,2.91,2.70)
for i,y in enumerate((-1.45,.35,2.0)):
    window(f'Right window {i}',4.29,y,2.75,side=True)
    window(f'Left window {i}',-4.29,y,2.75,side=True)

# Double front doors with vertical panels, hardware and a shallow lintel.
for sign in (-1,1):
    box('Openings',f'Door leaf {sign}',(sign*.37,-2.77,2.47),(.69,.10,2.08),'wood')
    for i in range(3):
        box('Details',f'Door panel {sign} {i}',(sign*.37,-2.835,1.82+i*.58),(.55,.034,.45),'wood_light')
    beam('Details',f'Door pull {sign}',(sign*.15,-2.88,2.32),(sign*.15,-2.88,2.55),.034,'bronze')
box('Openings','Door lintel',(0,-2.83,3.57),(1.71,.19,.24),'wood_dark')

# Veranda rails with an open middle entrance and repeated balusters.
for x0,x1 in ((-4.36,-1.02),(1.02,4.36)):
    box('Details',f'Rail top {x0}',((x0+x1)/2,-3.80,2.04),(x1-x0,.10,.11),'wood_light')
    box('Details',f'Rail bottom {x0}',((x0+x1)/2,-3.80,1.54),(x1-x0,.08,.09),'wood_dark')
    n=round((x1-x0)/.37)
    for i in range(n+1):
        xx=x0+(x1-x0)*i/n
        box('Details',f'Rail spindle {x0} {i}',(xx,-3.80,1.79),(.055,.065,.43),'wood')
for x in (-4.33,4.33):
    box('Details',f'Side veranda rail {x}',(x,-3.23,1.80),(.075,1.06,.55),'wood')

# Roof decks are a continuous mesh. Individual curved tiles are batched into
# one mesh per side instead of hundreds of draw calls.
for sgn in (-1,1):
    verts=[]; faces=[]
    nx,ny=28,12
    for j in range(ny+1):
        for i in range(nx+1):
            x=-5.03+10.06*i/nx; y=sgn*4.10*j/ny
            verts.append((x,y,roof_z(x,y)-.105))
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i; faces.append((a,a+1,a+nx+2,a+nx+1))
    mesh('Roof',f'Roof deck {sgn}',verts,faces,'tile')
    # Each tile is a small four-sided convex segment lifted from the deck.
    verts=[]; faces=[]
    for row in range(12):
        for col in range(45):
            x=-4.95+col*.22+(row%2)*.105
            y0=sgn*(.03+row*.335); y1=sgn*(.03+(row+1)*.335)
            if x>4.95: continue
            center=(x+.105,(y0+y1)/2)
            z0=roof_z(x,y0)+.011; z1=roof_z(x,y1)+.011
            crown=.055+.008*(col%3)
            base=len(verts)
            verts.extend([(x,y0,z0),(x+.21,y0,z0),(x+.21,y1,z1),(x,y1,z1),
                          (x+.105,y0,roof_z(x+.105,y0)+crown),
                          (x+.105,y1,roof_z(x+.105,y1)+crown)])
            if row==0: faces.append((base,base+1,base+4))
            if row==11: faces.append((base+3,base+5,base+2))
            faces.extend([(base,base+4,base+5,base+3),
                          (base+4,base+1,base+2,base+5)])
    mesh('Roof',f'Curved tile array {sgn}',verts,faces,'tile_edge')

# Ridge and turned corner finials. Ridge segments share the same roof curve.
beam('Roof','Main roof ridge',(-5.0,0,6.49),(5.0,0,6.49),.10,'tile_edge',10)
for sgn in (-1,1):
    for xsgn in (-1,1):
        y=sgn*4.08; x=xsgn*5.03
        beam('Roof',f'Corner finial foot {sgn} {xsgn}',(x,y,roof_z(x,y)),
             (xsgn*5.24,sgn*4.27,roof_z(x,y)+.27),.080,'bronze',8)
        beam('Roof',f'Corner finial horn {sgn} {xsgn}',(xsgn*5.24,sgn*4.27,roof_z(x,y)+.27),
             (xsgn*5.36,sgn*4.29,roof_z(x,y)+.50),.045,'bronze',8)
    # dark fascia under the roof eave
    box('Roof',f'Eave fascia {sgn}',(0,sgn*4.10,4.61),(10.17,.13,.17),'wood_dark')

# Front central gable / dormer: smaller layered roof and framed window.
mesh('Walls','Front triangular gable',
     [(-1.56,-3.48,5.47),(1.56,-3.48,5.47),(0,-3.48,6.44),
      (-1.56,-3.30,5.47),(1.56,-3.30,5.47),(0,-3.30,6.44)],
     [(0,1,2),(3,5,4),(0,3,4,1),(1,4,5,2),(2,5,3,0)],'plaster')
for sg in (-1,1):
    verts=[]; faces=[]
    for ix in range(9):
        x=sg*(.06+1.60*ix/8)
        z=6.51-1.01*(ix/8)+.19*(ix/8)**4
        verts.extend([(x,-4.57,z),(x,-2.68,z+.03)])
    for ix in range(8):
        a=2*ix; faces.append((a,a+1,a+3,a+2))
    mesh('Roof',f'Gable roof {sg}',verts,faces,'tile')
    beam('Roof',f'Gable verge {sg}',(sg*.06,-4.60,6.54),(sg*1.68,-4.60,5.66),.06,'tile_edge')
window('Gable window',0,-3.59,5.78,.68,.55)
beam('Roof','Gable ridge',(0,-4.59,6.55),(0,-2.64,6.55),.09,'tile_edge')

for x in (-3.9,3.9):
    box('Details',f'Lantern arm {x}',(x,-4.01,4.07),(.09,.69,.09),'wood_dark')
    box('Details',f'Lantern housing {x}',(x,-4.42,3.76),(.31,.31,.42),'bronze')
    box('Details',f'Lantern glow {x}',(x,-4.43,3.76),(.245,.245,.33),'lantern')
    beam('Details',f'Lantern tassel {x}',(x,-4.43,3.54),(x,-4.43,3.28),.018,'bronze')

# In-place QA-friendly bookkeeping. Preview ground and lights are omitted from export.
asset_objects=[o for c in parts.values() for o in c.objects if o.type=='MESH']
triangles=sum(len(p.vertices)-2 for o in asset_objects for p in o.data.polygons)
lower=[min((o.matrix_world @ v.co)[axis] for o in asset_objects for v in o.data.vertices)
       for axis in range(3)]
upper=[max((o.matrix_world @ v.co)[axis] for o in asset_objects for v in o.data.vertices)
       for axis in range(3)]
dimensions=[round(upper[i]-lower[i],3) for i in range(3)]
manifest={'asset':'Qingxi Riverside Guesthouse v1','source_three_view':str(REF.relative_to(ROOT)),
          'mesh_objects':len(asset_objects),'triangles_source':triangles,'materials':len(materials),
          'overall_dimensions_m':dimensions,'plinth_footprint_m':[9.35,7.35],'front':'-Y',
          'notes':'visual asset; no Unity compile, collision or mobile benchmark'}
(OUT/'build-report.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/'qingxi-riverside-house-v1.blend'))

# Batch by material for runtime export. The saved .blend remains modular.
batched=[]
groups={mat_name:[o.name for o in asset_objects if o.data.materials and
                  o.data.materials[0] == materials[mat_name]] for mat_name in materials}
for mat_name in materials:
    group=[bpy.data.objects[name] for name in groups[mat_name]]
    if not group: continue
    bpy.ops.object.select_all(action='DESELECT')
    for ob in group: ob.select_set(True)
    bpy.context.view_layer.objects.active=group[0]
    bpy.ops.object.join()
    joined=bpy.context.view_layer.objects.active
    joined.name='SM_QX_Batched_'+mat_name
    batched.append(joined)
# Framed carpentry intersects by design. Keep its three finishes as material
# slots in one draw mesh, avoiding duplicate coplanar object boundaries.
joinery=[o for o in batched if o.name in
         ('SM_QX_Batched_wood','SM_QX_Batched_wood_light','SM_QX_Batched_wood_dark')]
remaining=[o for o in batched if o.name not in
           ('SM_QX_Batched_wood','SM_QX_Batched_wood_light','SM_QX_Batched_wood_dark')]
bpy.ops.object.select_all(action='DESELECT')
for ob in joinery: ob.select_set(True)
bpy.context.view_layer.objects.active=joinery[0]
bpy.ops.object.join()
carpentry=bpy.context.view_layer.objects.active
carpentry.name='SM_QX_Batched_carpentry'
batched=remaining+[carpentry]
manifest['meshes_exported']=len(batched)
(OUT/'build-report.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')

# Export one static asset at its world origin. The illustration stage is not exported.
bpy.ops.object.select_all(action='DESELECT')
for o in batched: o.select_set(True)
bpy.context.view_layer.objects.active=batched[0]
bpy.ops.export_scene.fbx(filepath=str(OUT/'qingxi-riverside-house-v1.fbx'),use_selection=True,
                         apply_unit_scale=True,axis_forward='-Z',axis_up='Y',
                         add_leaf_bones=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',
                         bake_anim=False)
bpy.ops.export_scene.gltf(filepath=str(OUT/'qingxi-riverside-house-v1.glb'),
                          export_format='GLB',use_selection=True,export_apply=True)

box('Details','Preview earth',(0,0,-.16),(16,14,.31),'moss')
box('Details','Preview path',(0,-6.0,-.007),(2.7,5,.07),'stone_light')

def camera(name,loc,target,lens):
    data=bpy.data.cameras.new(name)
    ob=bpy.data.objects.new(name,data); scene.collection.objects.link(ob)
    ob.location=loc; ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
    data.lens=lens
    return ob

sun_data=bpy.data.lights.new('Warm afternoon','SUN'); sun_data.energy=1.8
sun=bpy.data.objects.new('Warm afternoon',sun_data); scene.collection.objects.link(sun)
sun.rotation_euler=Vector((-4,7,-10)).to_track_quat('-Z','Y').to_euler()
fill_data=bpy.data.lights.new('Front sky fill','AREA'); fill_data.energy=450; fill_data.shape='DISK'; fill_data.size=11
fill=bpy.data.objects.new('Front sky fill',fill_data); scene.collection.objects.link(fill)
fill.location=(1,-8,10); fill.rotation_euler=(Vector((0,-1,3))-fill.location).to_track_quat('-Z','Y').to_euler()
scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND')
bg.inputs['Color'].default_value=(.52,.59,.66,1)
bg.inputs['Strength'].default_value=.36
scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=1600; scene.render.resolution_y=1000
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.image_settings.color_mode='RGB'
scene.view_settings.view_transform='AgX'
scene.view_settings.look='AgX - Medium High Contrast'
for name,loc,target,lens in (
    ('front-three-quarter',(11,-15,9),(0,-.1,3.2),37),
    ('front-elevation',(0,-23,5.1),(0,0,3.4),50),
    ('roof-and-veranda',(-11,-12,13),(0,0,3.1),35),
):
    scene.camera=camera(name,loc,target,lens)
    scene.render.filepath=str(PREVIEW/(name+'.png'))
    bpy.ops.render.render(write_still=True)
print('@@HOUSE@@'+json.dumps(manifest,ensure_ascii=False))
