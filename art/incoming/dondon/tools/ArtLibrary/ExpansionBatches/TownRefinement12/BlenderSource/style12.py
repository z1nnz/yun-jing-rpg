"""Palette and studio derived from SectCore04; semantic material mapping only."""
import bpy
from mathutils import Vector
PALETTE={
 'stone':(.24,.30,.31),'pale':(.45,.49,.46),'plaster':(.67,.62,.50),
 'timber':(.16,.065,.028),'board':(.29,.14,.055),'lacquer':(.16,.065,.028),
 'tile':(.065,.15,.155),'bamboo':(.38,.37,.17),'straw':(.62,.45,.21),
 'clay':(.32,.14,.065),'glaze':(.08,.29,.24),'paper':(.61,.49,.29),
 'rope':(.48,.35,.17),'iron':(.065,.085,.08),'brass':(.25,.17,.065),
 'gold':(.25,.17,.065),'cloth':(.16,.27,.20),'lantern':(.61,.49,.29),
 'water':(.055,.20,.20),'paving':(.24,.30,.31),'kerb':(.45,.49,.46),
 'jade':(.08,.29,.24),'pad':(.10,.25,.055),'soil':(.085,.053,.025),
 'lotus':(.56,.30,.33),'burlap':(.40,.31,.18),'greens':(.10,.25,.055),
 'cabbage':(.28,.40,.12)}

def apply():
    changed=[]
    for m in bpy.data.materials:
        if not m.name.startswith('TL09_'):continue
        key=m.name[5:].split('.')[0].lower()
        if key not in PALETTE:continue
        color=PALETTE[key];m.diffuse_color=(*color,1);bs=m.node_tree.nodes.get('Principled BSDF')
        bs.inputs['Base Color'].default_value=(*color,1)
        bs.inputs['Roughness'].default_value=.6
        bs.inputs['Metallic'].default_value=.6 if key in ('gold','brass','iron') else (.18 if key in ('jade','glaze') else 0)
        if key in ('jade','glaze','water'):bs.inputs['Roughness'].default_value=.32
        if key=='lantern':bs.inputs['Emission Strength'].default_value=.25;bs.inputs['Emission Color'].default_value=(1,.6,.25,1)
        for n in m.node_tree.nodes:
            if n.type=='TEX_NOISE':n.inputs['Scale'].default_value=45
            if n.type=='BUMP':n.inputs['Strength'].default_value=.14;n.inputs['Distance'].default_value=.015
        changed.append(key)
    return sorted(set(changed))

def studio(meshes, bounds):
    sc=bpy.context.scene
    for o in list(sc.objects):
        if o.type=='LIGHT':bpy.data.objects.remove(o,do_unlink=True)
    coll=bpy.data.collections.get('90_Studio_Not_Exported')
    if coll is None:coll=bpy.data.collections.new('90_Studio_Not_Exported');sc.collection.children.link(coll)
    lo,hi=bounds(meshes);centre=(lo+hi)/2;ls=max(hi-lo)*.65
    for name,direction,power in [('Key',(-.8,-1.1,1.5),1100),('Fill',(1.2,-.4,.9),650),('Rim',(.2,1.1,1.3),950)]:
        d=bpy.data.lights.new('TR12_'+name,'AREA');d.energy=power*ls*ls/4;d.shape='DISK';d.size=ls
        o=bpy.data.objects.new('TR12_'+name,d);coll.objects.link(o);o.location=centre+Vector(direction)*ls
        o.rotation_euler=(centre-o.location).to_track_quat('-Z','Y').to_euler()
    sc.world.use_nodes=True;bg=sc.world.node_tree.nodes['Background']
    bg.inputs[0].default_value=(.19,.21,.22,1);bg.inputs[1].default_value=.65
    sc.view_settings.view_transform='AgX';sc.view_settings.look='None';sc.view_settings.exposure=0
    sc.render.film_transparent=False
