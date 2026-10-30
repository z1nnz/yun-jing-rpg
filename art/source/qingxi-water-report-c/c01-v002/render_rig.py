"""Fixed preview rig for C01 versions. Eli-0731, Blender 4.5.3 LTS.
blender -b -P render_rig.py -- --glb <path> --out <dir> [--wire]
Imports the exported asset (what the engine receives), never the working scene.
"""
import bpy,math,sys,argparse
from pathlib import Path
from mathutils import Vector
a=argparse.ArgumentParser();a.add_argument('--glb',required=True);a.add_argument('--out',required=True);a.add_argument('--wire',action='store_true');a.add_argument('--samples',type=int,default=48);a.add_argument('--tag',default='c01');a.add_argument('--ruler',action='store_true')
args=a.parse_args(sys.argv[sys.argv.index('--')+1:])
out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=args.samples;sc.cycles.use_denoising=True
sc.render.resolution_x=960;sc.render.resolution_y=720;sc.view_settings.view_transform='AgX';sc.view_settings.look='None'
bpy.ops.import_scene.gltf(filepath=args.glb)
obs=[o for o in sc.objects if o.type=='MESH']
pts=[o.matrix_world@Vector(c) for o in obs for c in o.bound_box]
lo=Vector([min(p[i] for p in pts) for i in range(3)]);hi=Vector([max(p[i] for p in pts) for i in range(3)])
if args.ruler:  # 1.75 m figure beside the prop (review spec: every view shows a human-scale ruler)
    fm=bpy.data.materials.new('ruler');fm.use_nodes=True;fm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.30,.42,.55,1)
    x0=hi.x+.45
    for loc,size in [((x0,0,.45),(.30,.18,.90)),((x0,0,1.18),(.40,.22,.58)),((x0,0,1.62),(.22,.22,.26))]:
        bpy.ops.mesh.primitive_cube_add(size=1,location=loc);c=bpy.context.object;c.dimensions=size;c.data.materials.append(fm)
    for z in (0.5,1.0,1.5,1.75):
        bpy.ops.mesh.primitive_cube_add(size=1,location=(x0+.24,0,z));t_=bpy.context.object;t_.dimensions=(.10,.01,.006);t_.data.materials.append(fm)
    lo.x=min(lo.x,x0-.2);hi.x=x0+.3;hi.z=max(hi.z,1.75)
ctr=(lo+hi)/2;rad=(hi-lo).length/2
# ground
bpy.ops.mesh.primitive_plane_add(size=12,location=(0,0,lo.z));g=sc.objects[-1] if False else bpy.context.object
gm=bpy.data.materials.new('ground');gm.use_nodes=True;gb=gm.node_tree.nodes['Principled BSDF'];gb.inputs['Base Color'].default_value=(.52,.52,.50,1);gb.inputs['Roughness'].default_value=.9;g.data.materials.append(gm)
world=bpy.data.worlds.new('w');sc.world=world;world.use_nodes=True;bg=world.node_tree.nodes['Background']
cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam'));sc.collection.objects.link(cam);sc.camera=cam;cam.data.lens=70
def aim(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def sun(name,rot,energy,color,angle=.05):
    l=bpy.data.objects.new(name,bpy.data.lights.new(name,'SUN'));l.data.energy=energy;l.data.color=color;l.data.angle=angle;l.rotation_euler=rot;sc.collection.objects.link(l);return l
lights=[]
def rig(mode):
    for l in lights:bpy.data.objects.remove(l)
    lights.clear()
    if mode=='neutral':
        bg.inputs['Color'].default_value=(.62,.62,.62,1);bg.inputs['Strength'].default_value=.9
        lights.append(sun('key',(math.radians(50),0,math.radians(-35)),2.2,(1,1,1),.3))
    else: # project style: warm afternoon key, cool sky fill, rim from behind
        bg.inputs['Color'].default_value=(.42,.55,.66,1);bg.inputs['Strength'].default_value=.55
        lights.append(sun('key',(math.radians(55),0,math.radians(-40)),3.6,(1,.86,.68),.08))
        lights.append(sun('rim',(math.radians(-60),0,math.radians(160)),2.4,(.80,.90,1),.1))
views={'front':(0,-1,.18),'side':(1,0,.18),'back':(0,1,.18),'threequarter':(-.72,-.72,.55)}
def shoot(tag,mode):
    rig(mode)
    for v,d in views.items():
        dist=max(rad*4.3,(hi.z-lo.z)*3.4,(hi.x-lo.x)*2.6);cam.location=ctr+Vector(d).normalized()*dist;aim(cam,ctr)
        sc.render.filepath=str(out/f'{args.tag}-{mode}-{v}.png');bpy.ops.render.render(write_still=True)
shoot(args.tag,'neutral');shoot(args.tag,'style')
if args.wire:
    wm=bpy.data.materials.new('wire');wm.use_nodes=True;n=wm.node_tree.nodes;n.clear();e=n.new('ShaderNodeEmission');e.inputs['Color'].default_value=(.02,.05,.09,1);o2=n.new('ShaderNodeOutputMaterial');wm.node_tree.links.new(e.outputs[0],o2.inputs[0])
    flat=bpy.data.materials.new('flat');flat.use_nodes=True;flat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.8,.8,.78,1)
    for o in obs:
        d=o.copy();d.data=o.data.copy();sc.collection.objects.link(d);d.data.materials.clear();d.data.materials.append(wm)
        m=d.modifiers.new('w','WIREFRAME');m.thickness=.0012;m.use_replace=True
        o.data.materials.clear() if False else None
        for i in range(len(o.material_slots)):o.material_slots[i].material=flat
    rig('neutral');cam.location=ctr+Vector(views['threequarter']).normalized()*rad*4.3;aim(cam,ctr)
    sc.render.filepath=str(out/f'{args.tag}-wire-threequarter.png');bpy.ops.render.render(write_still=True)
print('RIG_DONE',len(obs),'meshes')
