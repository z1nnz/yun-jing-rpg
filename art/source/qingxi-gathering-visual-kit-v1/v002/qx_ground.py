"""Shared semi-real ground dressing for the small kit pieces (same language as the ore and red-berry beds):
blended soil skirt, remeshed pebbles (game low poly + high-poly bake source), moss cushions, curled leaf
litter and grass clumped round the rim and the cushions instead of an even scatter."""
import bpy,bmesh,math,random
from mathutils import Vector,noise
import qx_kit as K
import qx_ore as O

TAU=math.tau

def bed(prefix,R,h0,rng,mats,pebbles=14,litter=24,cushions=(),rim_clumps=7,keep_out=.10,peb_size=(.008,.026),seed=23):
    """mats: skirt, rock, moss, litter. Returns the height function h(x,y)."""
    hf=lambda x,y:O.skirt_height(x,y,R,h0)
    sk=K.new_bm();O.skirt_into(sk,R,h0,14,72,seed);K.link(prefix+'_Soil_Bed',sk,[mats['skirt']])
    pb=bmesh.new();n=0
    for k in range(400):
        if n>=pebbles:break
        a=rng.uniform(0,TAU);s_=rng.uniform(.25,.92);x,y=R[0]*s_*math.cos(a),R[1]*s_*math.sin(a)
        if math.hypot(x,y)<keep_out:continue
        sz=rng.uniform(*peb_size)*(1.8 if k<2 else 1)
        b=O.hull_block((x,y,hf(x,y)+sz*.05),(sz*1.3,sz,sz*.6),800+k,24,.6,(0,0,rng.uniform(0,TAU)),rmin=.7);O.finish_block(b,sz*.12,max(hf(x,y)-.002,0));K.merge_into(pb,b);n+=1
    if n:
        me=bpy.data.meshes.new(prefix+'_Pebbles_Mesh');pb.to_mesh(me);pb.free();po=bpy.data.objects.new(prefix+'_Pebbles',me);K.ctx.coll.objects.link(po);po.parent=K.ctx.root
        po.hide_render=True;po['qx_role']='game_low_poly';me.materials.append(mats['rock']);K.ctx.objs.append(po)
        ph=O.remeshed(po,prefix+'_Pebbles_HP',K.ctx.coll,.003,1);ph.parent=K.ctx.root;hb,_=O.sculpt(ph,.15,.25,7,False,False);hb.free()
        ph.data.materials.append(mats['rock']);ph['qx_role']='bake_source_high_poly';K.ctx.objs.append(ph)
    else:pb.free()
    if cushions:
        mo=K.new_bm()
        for k,(x,y,rx,ry) in enumerate(cushions):K.lumpy_into(mo,(x,y,hf(x,y)-.006),(rx,ry,.018),900+k,3,.25,2.5,k)
        K.flat_base(mo,0.0);mc=K.link(prefix+'_Moss_Cushions',mo,[mats['moss']])
        ca=mc.data.color_attributes.new('Ms','FLOAT_COLOR','POINT')
        for i,v in enumerate(mc.data.vertices):ca.data[i].color=(K.c01(v.co.z/.015),noise.noise(v.co*9)*.5+.5,0,1)
    if litter:
        lt=K.new_bm()
        for k in range(litter):
            a=rng.uniform(0,TAU);s_=rng.uniform(.2,.9);x,y=R[0]*s_*math.cos(a),R[1]*s_*math.sin(a);az=rng.uniform(0,TAU);L=rng.uniform(.03,.06)
            p0=Vector((x,y,hf(x,y)+.002));d=Vector((math.cos(az),math.sin(az),0))
            pts=[p0+d*L*t/6+Vector((0,0,.004*math.sin(t/6*math.pi)+.003*(t/6)**2)) for t in range(7)]
            K.ribbon_into(lt,pts,[L*.20*math.sin(math.pi*min(.99,t/6*1.05))**.8+.0005 for t in range(7)],Vector((-d.y,d.x,0)),.45,rng.uniform(-.5,.5),5,(rng.random(),0,0))
        K.link(prefix+'_Leaf_Litter',lt,[mats['litter']],False)
    gr=K.new_bm()
    cl=[(x,y) for x,y,_,_ in cushions]+[(R[0]*.82*math.cos(a),R[1]*.82*math.sin(a)) for a in [k*TAU/rim_clumps+.4 for k in range(rim_clumps)]]
    for cx,cy in cl:
        for k in range(rng.randint(3,6)):
            x,y=cx+rng.gauss(0,.035),cy+rng.gauss(0,.03)
            if (x/R[0])**2+(y/R[1])**2>.95 or math.hypot(x,y)<keep_out+.02:continue
            O.tuft_into(gr,rng,Vector((x,y,hf(x,y)-.004)),.03,.10)
    if len(gr.verts):K.link(prefix+'_Grass',gr,[K.M['blade']],False)
    else:gr.free()
    return hf
