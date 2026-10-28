"""Qingxi creek-side gathering kit v002 (semi-realistic): shared procedural builders.
Six reusable assets; the two spirit herbs and the embedded ore also have a post-harvest state.
1 Blender unit = 1 m, front -Y, origin at the bottom centre (landmark: under the pole).
Source materials are procedural PBR node trees (grain, strata, veins, weave); bake_export.py bakes
them into one texture set per asset state for GLB/FBX. Leaves, petals and blades carry a 'UVMap'
laid out along their length (u across, v base->tip) and a per-corner 'Var' attribute
(r = per-part random, g = dryness / wilt, b = special mask: cut end, lip spots) read by the shaders.
SectCore04 hues (teal tile, warm timber, pale stone, pale jade) remain as accents.
"""
import bpy,bmesh,math,random
from mathutils import Vector,Matrix,noise

TAU=math.tau
GOLDEN=2.39996

STATES=[('QX_SpiritHerb_Qinglan','pre'),('QX_SpiritHerb_Qinglan','post'),
        ('QX_SpiritHerb_Chilu','pre'),('QX_SpiritHerb_Chilu','post'),
        ('QX_EmbeddedOre_Yumai','pre'),('QX_EmbeddedOre_Yumai','post'),
        ('QX_GatheringLandmark','base'),('QX_CreekSteppingPlank','base'),('QX_WaterReeds','base')]
NAMES={'QX_SpiritHerb_Qinglan':'青溪蘭（靈草一）','QX_SpiritHerb_Chilu':'赤露參（靈草二）','QX_EmbeddedOre_Yumai':'嵌地玉脈石（石礦）',
       'QX_GatheringLandmark':'採藥旗（採集地標）','QX_CreekSteppingPlank':'渡溪踏板','QX_WaterReeds':'水邊蘆草'}
STATE_ZH={'pre':'採前','post':'採後','base':'單一狀態'}
TEX_RES={'QX_GatheringLandmark':2048,'QX_EmbeddedOre_Yumai':2048}
DESIGN={
 'QX_SpiritHerb_Qinglan':'Cymbidium-like clump: 16 channelled strap leaves with parallel veins and a few dry tips, pseudobulbs, three arching spikes of pale-jade orchid blossoms that glow faintly. Post: leaves sickle-cut to 6-14 cm with fresh cut ends, spikes cut, cut leaves left on the soil, three new shoots.',
 'QX_SpiritHerb_Chilu':'Ginseng-like spirit herb: one stem, a whorl of four palmate leaves (five serrated leaflets each) and an umbel of 22 glowing vermilion berries. Post: berries stripped (bare pedicels), one leaf snapped and wilting, two dull fallen berries.',
 'QX_EmbeddedOre_Yumai':'Stratified jade-grey boulder sunk in gravelly soil with grass and pebbles, a pale jade quartz seam and a cluster of ten terminated jade crystals. Post: crystals broken to fractured stumps, fresh pale scar with pick marks, shards and chips on the soil.',
 'QX_GatheringLandmark':'5.6 m herb-gathering banner pole: weathered stone plinth ringed by field stones, timber pole with iron bands, barrel-tile teal cap with gourd finial, long jade banner with embroidered herb emblem, ribbed paper lantern, woven basket of cut herbs.',
 'QX_CreekSteppingPlank':'Stepping module: three weathered boards nailed onto two hewn beams over four barked piles with rope lashings; the board tops are the only light, flat surface, 0.62 m above the base; algae band at the waterline.',
 'QX_WaterReeds':'Water-edge clump: 56 reed blades green-to-straw, seven cattails and four feathery reed plumes on a wet mud tuft with pebbles.'}
MATERIAL_DIRECTION={
 'QX_SpiritHerb_Qinglan':'Glossy deep jade-green leaves (rough 0.42) with fine parallel veins, yellow-green bases, a few dry straw tips; petals pale jade-white with red-violet lip spots and low emission.',
 'QX_SpiritHerb_Chilu':'Matte dark green leaflets with herringbone veins; reddish stem; berries glossy vermilion (rough 0.2) with faint inner glow = the kit hot accent.',
 'QX_EmbeddedOre_Yumai':'Jade-grey stone with strata bands, cracks, lichen spots and moss on upward faces; pale jade seam; crystals jade with inner emission (pre) / dull fractured (post); fresh scar warm pale grey with pick marks.',
 'QX_GatheringLandmark':'Pale weathered stone, warm timber with vertical grain, dark iron bands, glazed teal barrel tiles, deep jade woven banner with pale embroidery, warm amber lantern paper.',
 'QX_CreekSteppingPlank':'Board tops grey-brown weathered timber, lighter and smoother in the walking centre, darker sides and cracks; piles dark barked wood with green algae band; iron nail heads; hemp rope.',
 'QX_WaterReeds':'Blades green at the base fading to straw, some fully dry; dark velvety cattails; pale straw plumes; wet dark mud.'}

def lerp(a,b,t):return tuple(x+(y-x)*t for x,y in zip(a,b))
def c01(x):return max(0.0,min(1.0,x))

# ---------------------------------------------------------------- material node helpers
def _set(nt,sock,v):
    if isinstance(v,bpy.types.NodeSocket):nt.links.new(v,sock)
    elif isinstance(v,(tuple,list)) and len(v)==3 and len(sock.default_value)==4:sock.default_value=(*v,1)
    else:sock.default_value=v

def node(nt,typ,ins=None,**attrs):
    n=nt.nodes.new(typ)
    for k,v in attrs.items():setattr(n,k,v)
    for k,v in (ins or {}).items():_set(nt,n.inputs[k],v)
    return n

def coord(nt,kind='Object'):
    tc=next((x for x in nt.nodes if x.type=='TEX_COORD'),None) or nt.nodes.new('ShaderNodeTexCoord');return tc.outputs[kind]
def scaled(nt,v,s):return node(nt,'ShaderNodeVectorMath',{0:v,1:s},operation='MULTIPLY').outputs[0]
def noise_t(nt,v,scale,detail=4,rough=.55,dist=0):return node(nt,'ShaderNodeTexNoise',{'Vector':v,'Scale':scale,'Detail':detail,'Roughness':rough,'Distortion':dist}).outputs['Fac']
def wave_t(nt,v,scale,axis='Z',dist=4,detail=3,profile='SIN'):
    w=node(nt,'ShaderNodeTexWave',{'Vector':v,'Scale':scale,'Distortion':dist,'Detail':detail},wave_type='BANDS',wave_profile=profile);w.bands_direction=axis;return w.outputs['Fac']
def voronoi_t(nt,v,scale,feature='F1',out='Distance'):return node(nt,'ShaderNodeTexVoronoi',{'Vector':v,'Scale':scale},feature=feature).outputs[out]
def ramp(nt,fac,stops):
    r=node(nt,'ShaderNodeValToRGB',{'Fac':fac});e=r.color_ramp.elements
    while len(e)<len(stops):e.new(0)
    for el,(p,c) in zip(e,stops):el.position=p;el.color=(*c,1)
    return r.outputs['Color']
def mix(nt,fac,a,b):
    m=nt.nodes.new('ShaderNodeMix');m.data_type='RGBA';_set(nt,m.inputs[0],fac);_set(nt,m.inputs[6],a);_set(nt,m.inputs[7],b);return m.outputs[2]
def math_(nt,op,a,b=0.0):return node(nt,'ShaderNodeMath',{0:a,1:b},operation=op).outputs[0]
def mul(nt,a,b):return math_(nt,'MULTIPLY',a,b)
def add(nt,a,b):return math_(nt,'ADD',a,b)
def mrange(nt,v,a,b,c=0.0,d=1.0):return node(nt,'ShaderNodeMapRange',{'Value':v,'From Min':a,'From Max':b,'To Min':c,'To Max':d}).outputs['Result']
def sep(nt,v):s=node(nt,'ShaderNodeSeparateXYZ',{0:v});return s.outputs[0],s.outputs[1],s.outputs[2]
def comb(nt,x,y,z=0.0):return node(nt,'ShaderNodeCombineXYZ',{0:x,1:y,2:z}).outputs[0]
def attr(nt,name='Var'):a=node(nt,'ShaderNodeAttribute',attribute_name=name);s=node(nt,'ShaderNodeSeparateColor',{0:a.outputs['Color']});return s.outputs[0],s.outputs[1],s.outputs[2]
def normal_z(nt):return sep(nt,node(nt,'ShaderNodeNewGeometry').outputs['Normal'])[2]
def uv(nt):u=node(nt,'ShaderNodeUVMap',uv_map='UVMap');return sep(nt,u.outputs['UV'])[:2]

def pbr(name,cull=True,rough=.8,spec=.3,metal=0.0,emit=None,estrength=0.0):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.use_backface_culling=cull;nt=m.node_tree;bs=next(x for x in nt.nodes if x.type=='BSDF_PRINCIPLED')
    _set(nt,bs.inputs['Roughness'],rough);_set(nt,bs.inputs['Specular IOR Level'],spec);_set(nt,bs.inputs['Metallic'],metal)
    if emit is not None:_set(nt,bs.inputs['Emission Color'],emit);_set(nt,bs.inputs['Emission Strength'],estrength)
    m['qx_cull']=cull;m['qx_emit_strength']=estrength;return m,nt,bs

def finish(nt,bs,color,rough=None,height=None,strength=.3,dist=.01):
    _set(nt,bs.inputs['Base Color'],color)
    if rough is not None:_set(nt,bs.inputs['Roughness'],rough)
    if height is not None:b=node(nt,'ShaderNodeBump',{'Strength':strength,'Distance':dist,'Height':height});_set(nt,bs.inputs['Normal'],b.outputs['Normal'])

# ---------------------------------------------------------------- materials
M={}
def mat_leaf_monocot(name,dark,mid,base):
    m,nt,bs=pbr(name,False,.42,.45);u,v=uv(nt);r,g,b=attr(nt);ob=coord(nt)
    col=ramp(nt,v,[(0,base),(.16,mid),(.75,dark),(1,lerp(dark,(.12,.12,.05),.4))])
    veins=wave_t(nt,comb(nt,u,mul(nt,v,.05)),6,'X',.3,1)
    col=mix(nt,mul(nt,veins,.18),col,lerp(mid,(.2,.25,.1),.3))
    rib=mrange(nt,math_(nt,'ABSOLUTE',math_(nt,'SUBTRACT',u,.5)),0,.07,1,0)
    col=mix(nt,mul(nt,rib,.35),col,lerp(mid,(.25,.3,.12),.5))
    col=mix(nt,mul(nt,noise_t(nt,ob,22,4),.25),col,lerp(dark,(0,0,0),.4))
    col=mix(nt,mul(nt,r,.25),col,lerp(dark,(.05,.10,.02),.6))
    dry=mrange(nt,add(nt,mul(nt,v,g),mul(nt,noise_t(nt,ob,30),.12)),.62,.72)
    col=mix(nt,dry,col,ramp(nt,noise_t(nt,ob,40),[(0,(.16,.11,.05)),(1,(.34,.26,.12))]))
    col=mix(nt,mrange(nt,b,.4,.6),col,(.42,.40,.24))                          # fresh cut ends
    finish(nt,bs,col,mix(nt,dry,(.42,.42,.42),(.8,.8,.8)),add(nt,mul(nt,veins,.5),rib),.15,.002);return m

def mat_leaf_dicot(name):
    m,nt,bs=pbr(name,False,.55,.35);u,v=uv(nt);r,g,b=attr(nt);ob=coord(nt)
    ax=math_(nt,'ABSOLUTE',math_(nt,'SUBTRACT',u,.5))
    lat=wave_t(nt,comb(nt,0,add(nt,v,mul(nt,ax,.9))),9,'Y',.4,1)
    vein=math_(nt,'MAXIMUM',mrange(nt,lat,.82,.98),mrange(nt,ax,.025,0))
    col=ramp(nt,ax,[(0,(.035,.085,.022)),(.38,(.028,.07,.018)),(.5,(.08,.14,.03))])
    col=mix(nt,mul(nt,noise_t(nt,ob,25,5),.3),col,(.012,.03,.01))
    col=mix(nt,mul(nt,vein,.55),col,(.11,.17,.05))
    wilt=mul(nt,g,mrange(nt,noise_t(nt,ob,12),.3,.6,.55,1));col=mix(nt,wilt,col,(.10,.09,.03))
    finish(nt,bs,col,mix(nt,wilt,(.55,.55,.55),(.75,.75,.75)),mul(nt,vein,-1),.25,.002);return m

def mat_stem(name,base=(.06,.10,.03),top=(.18,.06,.03)):
    m,nt,bs=pbr(name,True,.6,.3);ob=coord(nt);z=sep(nt,ob)[2];r,g,b=attr(nt)
    col=ramp(nt,mrange(nt,z,0,.35),[(0,lerp(base,(.03,.02,.01),.3)),(.3,base),(1,top)])
    col=mix(nt,mrange(nt,b,.4,.6),col,(.40,.40,.26))
    finish(nt,bs,col,None,noise_t(nt,scaled(nt,ob,(1,1,8)),60),.15,.002);return m

def mat_soil(name,wet=False):
    m,nt,bs=pbr(name,True,.55 if wet else .95,.3);ob=coord(nt);nzv=normal_z(nt)
    n1=noise_t(nt,ob,6,6,.6);peb=voronoi_t(nt,ob,55)
    col=ramp(nt,n1,[(0,(.018,.014,.01)),(1,(.05,.04,.028))] if wet else [(0,(.035,.025,.016)),(.55,(.075,.055,.034)),(1,(.12,.095,.06))])
    pm=mrange(nt,peb,.16,.08);col=mix(nt,mul(nt,pm,.8),col,(.07,.068,.06) if wet else (.16,.15,.13))
    if not wet:
        moss=mul(nt,mrange(nt,nzv,.6,.9),mrange(nt,noise_t(nt,ob,4,3),.5,.62))
        col=mix(nt,moss,col,ramp(nt,noise_t(nt,ob,30),[(0,(.02,.04,.012)),(1,(.06,.09,.025))]))
    finish(nt,bs,col,None,add(nt,mul(nt,pm,.6),n1),.4,.01);return m

def mat_stone(name,pale=False,seam=None,scar=None):
    """seam: (point, normal, half-width) plane band in object space; scar: (centre, radius)."""
    m,nt,bs=pbr(name,True,.85,.35);ob=coord(nt);nzv=normal_z(nt)
    n1=noise_t(nt,ob,3,6,.6);n2=noise_t(nt,ob,14,4);cr=voronoi_t(nt,add(nt,ob,mul(nt,noise_t(nt,ob,4),.25)),2.2,'DISTANCE_TO_EDGE');strata=wave_t(nt,ob,3.5,'Z',5,4)
    lo,hi=((.17,.17,.155),(.36,.35,.32)) if pale else ((.06,.075,.075),(.21,.23,.215))
    col=ramp(nt,add(nt,mul(nt,n1,.7),mul(nt,strata,.3)),[(0,lo),(.5,lerp(lo,hi,.55)),(1,hi)])
    col=mix(nt,mul(nt,n2,.3),col,lerp(lo,(0,0,0),.4))
    crack=mul(nt,mrange(nt,cr,.018,0),mrange(nt,noise_t(nt,ob,2.2,3),.52,.62));col=mix(nt,mul(nt,crack,.7),col,(.02,.022,.02))
    lich=mul(nt,mrange(nt,voronoi_t(nt,ob,22),.12,.07),mrange(nt,noise_t(nt,ob,5),.45,.6));col=mix(nt,mul(nt,lich,.7),col,(.34,.36,.28))
    hgt=add(nt,mul(nt,crack,-.8),add(nt,n2,mul(nt,strata,.4)))
    if seam:
        p,nrm,w=seam;dot=node(nt,'ShaderNodeVectorMath',{0:ob,1:nrm},operation='DOT_PRODUCT').outputs['Value']
        d=math_(nt,'ABSOLUTE',math_(nt,'SUBTRACT',dot,Vector(p).dot(Vector(nrm))))
        band=mrange(nt,add(nt,d,mul(nt,noise_t(nt,ob,9),.05)),w,w*.6)
        col=mix(nt,band,col,ramp(nt,noise_t(nt,ob,30),[(0,(.16,.42,.34)),(1,(.42,.62,.52))]));hgt=add(nt,hgt,mul(nt,band,.6))
    if scar:
        c,rad=scar;dist=node(nt,'ShaderNodeVectorMath',{0:ob,1:c},operation='DISTANCE').outputs['Value']
        sm=mrange(nt,add(nt,dist,mul(nt,noise_t(nt,ob,10),.08)),rad,rad*.75)
        col=mix(nt,sm,col,ramp(nt,noise_t(nt,ob,40),[(0,(.30,.29,.25)),(1,(.44,.42,.37))]))
        pick=mul(nt,sm,mrange(nt,voronoi_t(nt,ob,26),.1,.04));col=mix(nt,pick,col,(.08,.08,.075));hgt=add(nt,hgt,mul(nt,pick,-1.5))
    moss=mul(nt,mrange(nt,nzv,.55,.85),mrange(nt,noise_t(nt,ob,3.5,4),.48,.6))
    col=mix(nt,moss,col,ramp(nt,noise_t(nt,ob,35,5),[(0,(.02,.045,.012)),(1,(.07,.11,.025))]))
    finish(nt,bs,col,mix(nt,moss,(.85,.85,.85),(.95,.95,.95)),hgt,.45,.02);return m

def mat_wood(name,axis='Z',weathered=False,bark=False,dark=False):
    m,nt,bs=pbr(name,True,.78,.3);ob=coord(nt)
    st={'X':(1,8,8),'Y':(8,1,8),'Z':(8,8,1)}[axis];p=scaled(nt,ob,st);g=wave_t(nt,p,2.2,axis,9,4);n=noise_t(nt,p,5,5)
    if weathered:stops=[(0,(.10,.085,.065)),(.5,(.20,.17,.13)),(1,(.32,.28,.22))]
    elif dark:stops=[(0,(.035,.022,.012)),(.5,(.08,.05,.03)),(1,(.14,.09,.05))]
    else:stops=[(0,(.10,.05,.022)),(.5,(.20,.11,.05)),(1,(.34,.20,.09))]
    col=ramp(nt,add(nt,mul(nt,g,.6),mul(nt,n,.4)),stops)
    crack=mrange(nt,voronoi_t(nt,p,9,'DISTANCE_TO_EDGE'),.03,0);col=mix(nt,mul(nt,crack,.7),col,(.02,.015,.01))
    hgt=add(nt,g,mul(nt,crack,-1.2))
    if bark:
        bm_=mrange(nt,voronoi_t(nt,scaled(nt,ob,(1,1,.35)),14,'DISTANCE_TO_EDGE'),0,.12)
        col=mix(nt,mul(nt,mrange(nt,noise_t(nt,ob,3),.4,.55),.9),col,mix(nt,bm_,(.02,.018,.014),(.09,.08,.065)));hgt=add(nt,hgt,mul(nt,bm_,1.5))
    finish(nt,bs,col,.8 if weathered else .72,hgt,.35,.006);return m

def mat_plank_top(name):
    """Walking boards: grain along Y, grey weathering, worn smooth lighter centre (object-space radial)."""
    m,nt,bs=pbr(name,True,.8,.3);ob=coord(nt);x,y,z=sep(nt,ob);nzv=normal_z(nt);p=scaled(nt,ob,(9,1,9))
    g=wave_t(nt,p,2.4,'Y',10,4);n=noise_t(nt,p,6,5)
    col=ramp(nt,add(nt,mul(nt,g,.6),mul(nt,n,.4)),[(0,(.11,.09,.07)),(.5,(.22,.19,.15)),(1,(.34,.30,.24))])
    r=math_(nt,'SQRT',add(nt,math_(nt,'POWER',math_(nt,'DIVIDE',x,.34),2),math_(nt,'POWER',math_(nt,'DIVIDE',y,.32),2)))
    wear=mul(nt,mrange(nt,r,1.0,.25),mrange(nt,nzv,.8,.95));col=mix(nt,mul(nt,wear,.7),col,(.44,.38,.29))
    col=mix(nt,mrange(nt,nzv,.7,.3),col,(.07,.05,.035))
    crack=mrange(nt,voronoi_t(nt,scaled(nt,ob,(12,1,12)),7,'DISTANCE_TO_EDGE'),.035,0);col=mix(nt,mul(nt,crack,.8),col,(.03,.025,.02))
    finish(nt,bs,col,mix(nt,wear,(.82,.82,.82),(.58,.58,.58)),add(nt,mul(nt,g,.6),mul(nt,crack,-1.4)),.35,.006);return m

def mat_pile(name):
    m=mat_wood(name,'Z',bark=True,dark=True);nt=m.node_tree;bs=next(x for x in nt.nodes if x.type=='BSDF_PRINCIPLED')
    base=bs.inputs['Base Color'].links[0].from_socket;ob=coord(nt);z=sep(nt,ob)[2]
    band=mul(nt,mul(nt,mrange(nt,z,.08,.16),mrange(nt,z,.32,.24)),mrange(nt,noise_t(nt,ob,9),.3,.5))
    nt.links.new(mix(nt,band,base,ramp(nt,noise_t(nt,ob,40),[(0,(.02,.05,.015)),(1,(.06,.10,.03))])),bs.inputs['Base Color']);return m

def mat_cloth(name,bands):
    m,nt,bs=pbr(name,False,.92,.25);ob=coord(nt);x,y,z=sep(nt,ob)
    weave=mul(nt,wave_t(nt,ob,260,'X',0,0),wave_t(nt,ob,260,'Z',0,0))
    col=ramp(nt,noise_t(nt,ob,3,4),[(0,(.012,.06,.045)),(.6,(.025,.12,.09)),(1,(.05,.16,.12))])
    col=mix(nt,mul(nt,mrange(nt,z,2.2,1.6),.5),col,(.08,.13,.10))
    for z0,z1 in bands:col=mix(nt,mul(nt,mrange(nt,z,z0-.004,z0),mrange(nt,z,z1+.004,z1)),col,(.42,.44,.30))
    col=mix(nt,mul(nt,weave,.12),col,(0,0,0));finish(nt,bs,col,None,weave,.12,.002);return m

def mat_embroidery(name):
    m,nt,bs=pbr(name,False,.6,.4);ob=coord(nt);st=wave_t(nt,ob,180,'X',2,2,'SAW')
    finish(nt,bs,ramp(nt,st,[(0,(.30,.30,.17)),(1,(.55,.55,.34))]),None,st,.2,.002);return m

def mat_tile(name):
    m,nt,bs=pbr(name,True,.32,.5);ob=coord(nt);n=noise_t(nt,ob,6,5);nzv=normal_z(nt)
    col=ramp(nt,n,[(0,(.012,.07,.06)),(.5,(.03,.13,.11)),(1,(.07,.20,.17))])
    col=mix(nt,mrange(nt,nzv,0,-.4),col,(.10,.06,.035))
    dirt=mul(nt,mrange(nt,noise_t(nt,ob,20,3),.55,.75),.6);col=mix(nt,dirt,col,(.05,.06,.045))
    finish(nt,bs,col,mix(nt,dirt,(.3,.3,.3),(.7,.7,.7)),n,.2,.004);return m

def mat_iron(name):
    m,nt,bs=pbr(name,True,.55,.5,.85);ob=coord(nt);rust=mrange(nt,noise_t(nt,ob,14,6),.45,.7)
    finish(nt,bs,mix(nt,rust,(.05,.05,.05),(.16,.06,.02)),mix(nt,rust,(.45,.45,.45),(.9,.9,.9)),noise_t(nt,ob,60),.2,.002)
    nt.links.new(math_(nt,'SUBTRACT',.85,mul(nt,rust,.75)),bs.inputs['Metallic']);return m

def mat_glow(name,base,emit,strength,rough=.3,cull=True,spots=False,scale=12):
    m,nt,bs=pbr(name,cull,rough,.5,0,emit,strength);ob=coord(nt);n=noise_t(nt,ob,scale,4)
    col=ramp(nt,n,[(0,lerp(base,(0,0,0),.25)),(1,lerp(base,(1,1,1),.15))])
    if spots:
        r,g,b=attr(nt);u,v=uv(nt);sp=mul(nt,mrange(nt,b,.4,.6),mrange(nt,voronoi_t(nt,comb(nt,u,v),14),.22,.12));col=mix(nt,sp,col,(.30,.03,.10))
    nt.links.new(ramp(nt,n,[(0,lerp(emit,(0,0,0),.45)),(1,emit)]),bs.inputs['Emission Color'])
    finish(nt,bs,col,None,n,.08,.002);return m

def mat_simple(name,lo,hi,rough=.85,scale=30,cull=True,spec=.3,stretch=(1,1,1)):
    m,nt,bs=pbr(name,cull,rough,spec);ob=coord(nt);n=noise_t(nt,scaled(nt,ob,stretch),scale,5)
    finish(nt,bs,ramp(nt,n,[(0,lo),(1,hi)]),None,n,.25,.003);return m

def mat_blade(name):
    m,nt,bs=pbr(name,False,.6,.35);u,v=uv(nt);r,g,b=attr(nt);ob=coord(nt)
    veins=wave_t(nt,comb(nt,u,0),5,'X',0,0)
    t=add(nt,mul(nt,v,mrange(nt,g,0,1,.9,3.2)),mul(nt,noise_t(nt,ob,8),.25))
    col=ramp(nt,t,[(0,(.03,.06,.015)),(.35,(.05,.11,.025)),(.8,(.08,.13,.03)),(1,(.28,.25,.12))])
    col=mix(nt,mul(nt,r,.3),col,(.18,.17,.07));col=mix(nt,mul(nt,veins,.15),col,(0,0,0))
    finish(nt,bs,col,mix(nt,mrange(nt,t,.8,1),(.55,.55,.55),(.85,.85,.85)),veins,.1,.001);return m

def make_materials():
    if M:return
    M.update({
     'soil':mat_soil('QX_Src_Forest_Soil'),'mud':mat_soil('QX_Src_Wet_Mud',True),
     'leaf_q':mat_leaf_monocot('QX_Src_Qinglan_Leaf',(.016,.06,.045),(.04,.12,.07),(.16,.20,.07)),
     'leaf_c':mat_leaf_dicot('QX_Src_Chilu_Leaflet'),
     'stem_q':mat_stem('QX_Src_Qinglan_Stem',(.06,.11,.05),(.10,.16,.09)),'stem_c':mat_stem('QX_Src_Chilu_Stem'),
     'petal':mat_glow('QX_Src_Glow_Orchid_Petal',(.62,.74,.64),(.45,.95,.72),.6,.5,False,True),
     'mote':mat_glow('QX_Src_Glow_Spirit_Mote',(.75,.95,.85),(.55,1,.8),3.0,.5),
     'berry':mat_glow('QX_Src_Glow_Vermilion_Berry',(.42,.018,.008),(1,.12,.02),.35,.2,True,False,40),
     'berry_dull':mat_simple('QX_Src_Fallen_Berry',(.10,.012,.008),(.22,.03,.012),.5,30),
     'stone':mat_stone('QX_Src_JadeGrey_Stone'),'plinth':mat_stone('QX_Src_Pale_Plinth_Stone',True),
     'crystal':mat_glow('QX_Src_Glow_Jade_Crystal',(.10,.42,.32),(.20,.85,.60),.9,.12,True,False,7),
     'crystal_dull':mat_simple('QX_Src_Dull_Crystal_Fracture',(.10,.20,.17),(.26,.36,.31),.45,18),
     'timber':mat_wood('QX_Src_Timber_Vertical','Z'),'timber_x':mat_wood('QX_Src_Timber_Horizontal','X'),
     'iron':mat_iron('QX_Src_Wrought_Iron'),'tile':mat_tile('QX_Src_Glazed_Teal_Tile'),
     'cloth':mat_cloth('QX_Src_Jade_Banner_Cloth',[(4.25,4.22),(4.17,4.155),(1.99,1.96)]),'embroidery':mat_embroidery('QX_Src_Banner_Embroidery'),
     'paper':mat_glow('QX_Src_Glow_Lantern_Paper',(.75,.52,.30),(1,.55,.22),2.4,.8,True,False,25),
     'lacquer':mat_simple('QX_Src_Red_Lacquer_Tassel',(.18,.02,.012),(.32,.04,.02),.5,40),
     'gourd':mat_simple('QX_Src_PaleJade_Finial',(.32,.42,.34),(.50,.60,.50),.35,12),
     'basket':mat_wood('QX_Src_Woven_Bamboo','Z',weathered=True),
     'plank':mat_plank_top('QX_Src_Plank_Foot_Surface'),'beam':mat_wood('QX_Src_Hewn_Beam','X',dark=True),'pile':mat_pile('QX_Src_Barked_Pile'),
     'rope':mat_simple('QX_Src_Hemp_Rope',(.09,.065,.04),(.20,.15,.09),.95,90,True,.2,(1,1,3)),
     'blade':mat_blade('QX_Src_Reed_Blade'),'cattail':mat_simple('QX_Src_Cattail_Head',(.05,.025,.012),(.12,.065,.03),.95,90),
     'plume':mat_simple('QX_Src_Reed_Plume',(.28,.24,.17),(.50,.44,.32),.9,50,False),
     'reedstem':mat_stem('QX_Src_Reed_Stem',(.05,.09,.025),(.16,.15,.06))})

# ---------------------------------------------------------------- mesh helpers
class Ctx:pass
ctx=Ctx()

def new_bm():
    bm=bmesh.new();bm.loops.layers.uv.new('UVMap');bm.loops.layers.float_color.new('Var');return bm

def tag_uv(vert,u,v,var=(.5,0,0)):ctx.vdata[vert]=((u,v),var)

def ico_into(bm,subdiv,radius,matrix):
    """Icosphere appended to bm via a scratch bmesh; returns its new verts. Creating it with bmesh.ops directly
    on bm reallocates bm's verts, which orphans every UV / Var tag already set on that bmesh."""
    tmp=bmesh.new();bmesh.ops.create_icosphere(tmp,subdivisions=subdiv,radius=radius,matrix=matrix);vm={}
    for tv in tmp.verts:vm[tv]=bm.verts.new(tv.co)
    for tf in tmp.faces:bm.faces.new([vm[x] for x in tf.verts])
    tmp.free();return list(vm.values())

def merge_into(bm,sub):
    """Append a temporary bmesh (no UV/Var data needed) into bm."""
    me=bpy.data.meshes.new('_tmp');sub.to_mesh(me);sub.free();bm.from_mesh(me);bpy.data.meshes.remove(me)

def link(name,bm,mats,smooth=True,var=None):
    ul=bm.loops.layers.uv['UVMap'];cl=bm.loops.layers.float_color['Var'];dv=(*(var or (.5,0,0)),1)
    for f in bm.faces:
        for lp in f.loops:
            d=ctx.vdata.get(lp.vert)
            if d:lp[ul].uv=d[0];lp[cl]=(*d[1],1)
            else:lp[cl]=dv
    ctx.vdata.clear()
    d=bpy.data.meshes.new(name+'_Mesh');bm.to_mesh(d);bm.free()
    for m in mats:d.materials.append(m)
    if smooth is not None:
        for p in d.polygons:p.use_smooth=smooth
    o=bpy.data.objects.new(name,d);ctx.coll.objects.link(o);o.parent=ctx.root;ctx.objs.append(o);return o

def tube_into(bm,points,radii,sides=8,cap=True,jitter=0.0,seed=0):
    rings=[]
    for j,p in enumerate(points):
        p=Vector(p);t=(Vector(points[min(j+1,len(points)-1)])-Vector(points[max(j-1,0)])).normalized()
        u=t.cross(Vector((0,0,1)))
        if u.length<.01:u=t.cross(Vector((0,1,0)))
        u.normalize();w=t.cross(u);ring=[]
        for i in range(sides):
            d=u*math.cos(i*TAU/sides)+w*math.sin(i*TAU/sides);k=1+jitter*noise.noise(p*7+d*1.3+Vector((seed,0,0)))
            ring.append(bm.verts.new(p+radii[j]*k*d))
        rings.append(ring)
    for a,b in zip(rings,rings[1:]):
        for i in range(sides):bm.faces.new((a[i],a[(i+1)%sides],b[(i+1)%sides],b[i]))
    if cap:bm.faces.new(list(reversed(rings[0])));bm.faces.new(rings[-1])
    return rings

def lumpy_into(bm,center,radii,seed,subdiv=3,rough=.2,freq=1.5,rot=0):
    r=bmesh.ops.create_icosphere(bm,subdivisions=subdiv,radius=1);vs=r['verts'];off=Vector((seed*1.37,seed*2.11,seed*.73));rm=Matrix.Rotation(rot,3,'Z')
    for v in vs:
        d=v.co.normalized();k=1+rough*noise.fractal(d*freq+off,.6,2.0,4)
        v.co=Vector(center)+rm@Vector((d.x*radii[0]*k,d.y*radii[1]*k,d.z*radii[2]*k))
    return vs

def plane_cut(bm,co,no,inner=False):
    geom=bm.verts[:]+bm.edges[:]+bm.faces[:]
    bmesh.ops.bisect_plane(bm,geom=geom,plane_co=co,plane_no=no,clear_outer=not inner,clear_inner=inner)
    edges=[e for e in bm.edges if e.is_boundary]
    if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)

def flat_base(bm,z=0.0):plane_cut(bm,(0,0,z),(0,0,1),True)

def chisel(bm,center,radii,cuts,rng,el=(-.1,.9)):
    for k in range(cuts):
        a=rng.uniform(0,TAU);e=rng.uniform(*el);d=Vector((math.cos(a)*math.cos(e),math.sin(a)*math.cos(e),math.sin(e)))
        reach=Vector((d.x*radii[0],d.y*radii[1],d.z*radii[2])).length*rng.uniform(.78,.9);plane_cut(bm,Vector(center)+d*reach,d)

def lathe_into(bm,profile,segs=12,center=(0,0,0),rot=0.0,jitter=0.0):
    c=Vector(center);rings=[];new=[]
    for r,z in profile:
        if r<1e-5:v=bm.verts.new(c+Vector((0,0,z)));rings.append([v]);new.append(v)
        else:
            ring=[]
            for i in range(segs):
                a=rot+i*TAU/segs;k=1+jitter*noise.noise(Vector((math.cos(a)*2,math.sin(a)*2,z*5)));ring.append(bm.verts.new(c+Vector((r*k*math.cos(a),r*k*math.sin(a),z))))
            rings.append(ring);new+=ring
    for a,b in zip(rings,rings[1:]):
        if len(a)==1 and len(b)==1:continue
        if len(a)==1:
            for i in range(segs):bm.faces.new((a[0],b[i],b[(i+1)%segs]))
        elif len(b)==1:
            for i in range(segs):bm.faces.new((a[i],b[0],a[(i+1)%segs]))
        else:
            for i in range(segs):bm.faces.new((a[i],a[(i+1)%segs],b[(i+1)%segs],b[i]))
    return new

def box_into(bm,center,size,bevel=0.0,warp=0.0,seed=0):
    sub=bmesh.new();bmesh.ops.create_cube(sub,size=1,matrix=Matrix.Translation(center)@Matrix.Diagonal((*size,1)))
    if bevel>0:bmesh.ops.bevel(sub,geom=sub.edges[:],offset=bevel,segments=2,affect='EDGES',profile=.5)
    if warp:
        for v in sub.verts:v.co.z+=warp*noise.noise(v.co*3+Vector((seed,seed,0)))
    merge_into(bm,sub)

def arch(base,az,L,tilt0,tilt1,n=10,power=1.6):
    h=Vector((math.cos(az),math.sin(az),0));p=Vector(base);pts=[p.copy()];d=L/n
    for j in range(n):
        t=(j+.5)/n;tl=tilt0+(tilt1-tilt0)*t**power;p=p+(h*math.sin(tl)+Vector((0,0,math.cos(tl))))*d;pts.append(p.copy())
    return pts,h

def ribbon_into(bm,pts,widths,side_dir,fold=.25,twist=0.0,cols=5,var=(.5,0,0),prof=lambda u:abs(u)**1.5,v0=0.0,v1=1.0,var_fn=None):
    """Blade/leaf/petal strip; UV u across 0..1, v along v0..v1; var_fn(j,n) overrides Var per row."""
    n=len(pts);rows=[]
    for j,p in enumerate(pts):
        t=(pts[min(j+1,n-1)]-pts[max(j-1,0)]).normalized()
        s=Vector(side_dir);s=s-t*s.dot(t);s=s.normalized() if s.length>1e-6 else t.orthogonal().normalized()
        s=Matrix.Rotation(twist*j/max(n-1,1),3,t)@s;up=s.cross(t).normalized();w=max(widths[j],.0006);row=[]
        for i in range(cols):
            uu=-1+2*i/(cols-1);vert=bm.verts.new(p+s*w*uu+up*w*fold*prof(uu))
            tag_uv(vert,i/(cols-1),v0+(v1-v0)*j/max(n-1,1),var_fn(j,n) if var_fn else var);row.append(vert)
        rows.append(row)
    for a,b in zip(rows,rows[1:]):
        for i in range(cols-1):bm.faces.new((a[i],a[i+1],b[i+1],b[i]))
    return rows

def ground_height(bm):
    """Height lookup over the top of a mound (nearest upper vertex within 5 cm)."""
    top=[v.co.copy() for v in bm.verts if v.co.z>.004]
    def f(p):
        if not top:return 0.0
        best=min(top,key=lambda q:(q.x-p.x)**2+(q.y-p.y)**2);return best.z if (best.x-p.x)**2+(best.y-p.y)**2<.0025 else 0.0
    return f

def grass_into(bm,rng,rin,rout,count,ground,hmin=.035,hmax=.10,sx=1.0,sy=1.0):
    for k in range(count):
        a=rng.uniform(0,TAU);r=rng.uniform(rin,rout);c=Vector((r*math.cos(a)*sx,r*math.sin(a)*sy,0));c.z=ground(c)-.008
        for s in range(rng.randint(3,6)):
            az=rng.uniform(0,TAU);pts,h=arch(c,az,rng.uniform(hmin,hmax),rng.uniform(.15,.45),rng.uniform(.7,1.5),5,1.8)
            ribbon_into(bm,pts,[.0022*(1-j/5)**.6+.0004 for j in range(6)],Vector((-h.y,h.x,0)),.25,0,3,(rng.random(),rng.choice((0,0,.3,1)),0))

def surface_anchor(bm,xy,minz=.25):
    bm.normal_update();best=min((v for v in bm.verts if v.normal.z>minz),key=lambda v:(v.co.x-xy[0])**2+(v.co.y-xy[1])**2)
    return best.co.copy(),best.normal.copy()

def soil_bed(radii,seed,rng,grass=24,mat='soil',name='Soil_Bed'):
    bm=new_bm();lumpy_into(bm,(0,0,0),radii,seed,4,.2,2.4);flat_base(bm);gh=ground_height(bm);link(name,bm,[M[mat]])
    if grass:
        g=new_bm();R=max(radii[0],radii[1]);grass_into(g,rng,.35,.9,grass,gh,sx=radii[0],sy=radii[1]);link(name+'_Grass',g,[M['blade']])
    return gh

# ---------------------------------------------------------------- assets
def qinglan(post):
    rng=random.Random(3101);gh=soil_bed((.26,.24,.05),31,rng,16)
    bulbs=new_bm()
    for k in range(4):
        a=k*TAU/4+.4;lathe_into(bulbs,[(0,0),(.016,.008),(.021,.025),(.017,.042),(.008,.055),(0,.058)],8,(.03*math.cos(a),.03*math.sin(a),.012),a,.08)
    link('Qinglan_Pseudobulbs',bulbs,[M['stem_q']])
    bm=new_bm();cut=[]
    for i in range(16):
        az=i*GOLDEN+rng.uniform(-.25,.25);L=rng.uniform(.40,.70);W=rng.uniform(.011,.016);dry=1.0 if i in (3,9,13) else 0.0
        n=18;pts,h=arch((.032*math.cos(az),.032*math.sin(az),.03),az,L,rng.uniform(.10,.32),rng.uniform(1.0,1.75),n,1.7)
        ws=[W*min(1,j/n*6)*(1-j/n)**.5+.0008 for j in range(n+1)];side=Vector((-h.y,h.x,0))
        if post:
            keep=max(3,round(n*rng.uniform(.10,.20)));pts=pts[:keep+1];ws=ws[:keep+1];ws[-1]=ws[-2]
            pts[-1]=pts[-1]+side*.0+Vector((0,0,.012*rng.uniform(-1,1)))      # angled sickle cut
            r0=rng.random();ribbon_into(bm,pts,ws,side,.35,rng.uniform(-.5,.5),5,v1=keep/n,var_fn=lambda j,nn,r=r0:(r,0,.5 if j==nn-1 else 0))
            cut.append((L,W,az))
        else:ribbon_into(bm,pts,ws,side,.35,rng.uniform(-.7,.7),5,(rng.random(),dry,0))
    if post:
        for j in range(3):  # new shoots
            az=j*2.2+.7;pts,h=arch((.01*math.cos(az),.01*math.sin(az),.03),az,.13,.05,.3,8)
            ribbon_into(bm,pts,[.009*min(1,k/8*5)*(1-k/8)**.5+.0008 for k in range(9)],Vector((-h.y,h.x,0)),.35,0,5,(.2,0,0),v1=.5)
    link('Qinglan_Leaves',bm,[M['leaf_q']])
    if post:
        ly=new_bm()   # cut leaf pieces dropped on the soil
        for k,(L,W,az) in enumerate(cut[:3]):
            a=k*2.3+rng.uniform(-.5,.5);rr=rng.uniform(.09,.17);c=Vector((rr*math.cos(a),rr*math.sin(a),0));d=Vector((math.cos(a+rng.uniform(.6,2.4)),math.sin(a+rng.uniform(.6,2.4)),0)).normalized();L2=L*rng.uniform(.35,.5)
            pts=[]
            for s in range(11):
                t=s/10;q=c+d*L2*(t-.5);q=q+d.cross(Vector((0,0,1)))*.03*math.sin(t*2.5);pts.append(q+Vector((0,0,gh(q)+.004+.018*t*t)))
            ribbon_into(ly,pts,[W*(1-t/10)**.4+.001 for t in range(11)],Vector((0,0,1)).cross(d),.45,rng.uniform(-.8,.8),5,(rng.random(),.0,0),v0=.3)
        link('Qinglan_Cut_Leaves_On_Soil',ly,[M['leaf_q']])
        st=new_bm()
        for j in range(3):
            az=j*2.1+.5;b=Vector((.02*math.cos(az),.02*math.sin(az),.02));rings=tube_into(st,[b,b+Vector((.012*math.cos(az),.012*math.sin(az),.07))],[.0042,.004],8)
            for v in rings[-1]:tag_uv(v,0,0,(.5,0,1))
        link('Qinglan_Cut_Spikes',st,[M['stem_q']])
        return
    stems=new_bm();petals=new_bm();motes=new_bm()
    for j in range(3):
        az=j*2.3+.5;n=16;pts,h=arch((.02*math.cos(az),.02*math.sin(az),.03),az,.55+.06*j,.06,.85,n,1.3)
        tube_into(stems,pts,[.0042-.0018*k/n for k in range(n+1)],6)
        for b in range(6):
            k=7.5+b*1.3;i0=int(k);c=pts[i0].lerp(pts[min(i0+1,n)],k-i0)
            side=Vector((-h.y,h.x,0))*(1 if b%2 else -1);face=(side*.8+h*.4+Vector((0,0,-.15))).normalized()
            centre=c+side*.018+Vector((0,0,-.008));tube_into(stems,[c,c+side*.01+Vector((0,0,.004)),centre],[.0018,.0016,.0015],5,False)
            q=face.to_track_quat('Z','Y').to_matrix();sz=.85+.15*rng.random()
            for ang,L,W,lift in [(math.pi/2,.032,.0065,.55),(math.pi/2+2.2,.030,.006,.35),(math.pi/2-2.2,.030,.006,.35),(math.pi/2+.9,.024,.0075,.75),(math.pi/2-.9,.024,.0075,.75)]:
                dirp=(q@Vector((math.cos(ang),math.sin(ang),lift))).normalized();sd=q@Vector((-math.sin(ang),math.cos(ang),0))
                pp=[centre+dirp*L*sz*u+face*.008*u*u for u in (0,.25,.5,.75,1)]
                ribbon_into(petals,pp,[W*.35,W*.9,W,W*.8,W*.25],sd,.5,0,5,(rng.random(),0,0),lambda u:u*u)
            lipd=(q@Vector((0,-1,.25))).normalized();sd=q@Vector((1,0,0));dn=q@Vector((0,0,-.012))
            pp=[centre+lipd*.022*u*sz+face*(.006*u)+dn*u*u for u in (0,.25,.5,.75,1)]
            ribbon_into(petals,pp,[.003,.008,.011,.011,.006],sd,.7,0,5,(0,0,1),lambda u:u*u)
            tube_into(petals,[centre,centre+face*.012],[.003,.0022],5)
    for j in range(5):
        a=j*GOLDEN;r=rng.uniform(.10,.24);bmesh.ops.create_icosphere(motes,subdivisions=2,radius=rng.uniform(.004,.007),matrix=Matrix.Translation((r*math.cos(a),r*math.sin(a),rng.uniform(.32,.58))))
    link('Qinglan_Flower_Spikes',stems,[M['stem_q']])
    link('Qinglan_Glow_Blossoms',petals,[M['petal']])
    link('Qinglan_Spirit_Motes',motes,[M['mote']])

def leaflet_into(bm,base,direction,L,W,droop,var):
    """Serrated obovate leaflet; alternating row widths cut the teeth."""
    d=Vector(direction).normalized();side=d.cross(Vector((0,0,1)));side=side.normalized() if side.length>1e-4 else Vector((1,0,0));n=16;pts=[];ws=[]
    for j in range(n+1):
        t=j/n;pts.append(base+d*L*t+Vector((0,0,-droop*t*t)))
        w=W*(math.sin(math.pi*min(.999,t*1.08))**.65)*(1-.35*(1-t)**3);ws.append(w*(1-.13*(j%2)*(t>.2))+.0006)
    ribbon_into(bm,pts,ws,side,.18,0,5,var,lambda u:u*u)

def chilu(post):
    rng=random.Random(3201);gh=soil_bed((.28,.26,.045),41,rng,18)
    st=new_bm();top=Vector((.008,-.004,.27))
    tube_into(st,[Vector((0,0,.02)),Vector((.003,-.001,.1)),Vector((.006,-.003,.19)),top],[.0055,.005,.0047,.0045],8)
    lv=new_bm()
    for k in range(4):
        az=k*TAU/4+.35;h=Vector((math.cos(az),math.sin(az),0))
        if post and k==2:  # snapped petiole hanging, leaflets wilting
            kink=top+h*.04+Vector((0,0,.01));end=kink+h*.03+Vector((0,0,-.07));tube_into(st,[top,kink,end],[.003,.0028,.0025],6)
            for f in range(5):
                a=(f-2)*.5;dd=Vector((h.x*math.cos(a)-h.y*math.sin(a),h.x*math.sin(a)+h.y*math.cos(a),-1.6)).normalized()
                leaflet_into(lv,end,dd,(.10 if f==2 else .075),(.03 if f==2 else .024),.01,(rng.random(),1,0))
            continue
        tip=top+h*.085+Vector((0,0,.03));tube_into(st,[top,top+h*.04+Vector((0,0,.022)),tip],[.003,.0028,.0026],6)
        for f in range(5):
            a=(f-2)*.62;dd=Vector((h.x*math.cos(a)-h.y*math.sin(a),h.x*math.sin(a)+h.y*math.cos(a),.12)).normalized()
            L=[.07,.095,.12,.095,.07][f];leaflet_into(lv,tip,dd,L,L*.36,.035,(rng.random(),.15 if post else 0,0))
    link('Chilu_Leaves',lv,[M['leaf_c']])
    pk=top+Vector((0,0,.13));tube_into(st,[top,top+Vector((.002,0,.07)),pk],[.0035,.0032,.003],6)
    berries=new_bm()
    for b in range(22):
        phi=math.acos(1-1.35*(b+.5)/22);th=b*GOLDEN;d=Vector((math.sin(phi)*math.cos(th),math.sin(phi)*math.sin(th),math.cos(phi)))
        if post:tube_into(st,[pk,pk+d*.022],[.0012,.0009],4);continue
        tip=pk+d*.038;tube_into(st,[pk,tip],[.0012,.001],4,False);r=rng.uniform(.0095,.0115)
        bmesh.ops.create_icosphere(berries,subdivisions=2,radius=r,matrix=Matrix.Translation(tip+d*r*.85)@d.to_track_quat('Z','Y').to_matrix().to_4x4()@Matrix.Diagonal((1,1,.88,1)))
    link('Chilu_Stem_Petioles',st,[M['stem_c']])
    if post:
        fb=new_bm()
        for x,y in [(.09,-.11),(-.12,-.05)]:
            bmesh.ops.create_icosphere(fb,subdivisions=2,radius=.0105,matrix=Matrix.Translation((x,y,gh(Vector((x,y,0)))+.008))@Matrix.Diagonal((1,1,.75,1)))
        link('Chilu_Fallen_Berries',fb,[M['berry_dull']])
    else:link('Chilu_Glow_Berries',berries,[M['berry']])

def crystal_into(bm,base,d,r,L,rng,broken=False):
    """Hexagonal prism with a six-face termination; broken = fractured by a tilted plane."""
    q=d.to_track_quat('Z','Y').to_matrix().to_4x4();ro=rng.uniform(0,1);rr=[r*(1+.12*rng.uniform(-1,1)) for _ in range(6)]
    tmp=bmesh.new();rings=[[tmp.verts.new((rr[i]*k*math.cos(ro+i*TAU/6),rr[i]*k*math.sin(ro+i*TAU/6),z)) for i in range(6)] for z,k in [(0,.92),(L*.7,1.0)]]
    tip=tmp.verts.new((r*.1,0,L))
    for i in range(6):tmp.faces.new((rings[0][i],rings[0][(i+1)%6],rings[1][(i+1)%6],rings[1][i]))
    for i in range(6):tmp.faces.new((rings[1][i],rings[1][(i+1)%6],tip))
    tmp.faces.new(list(reversed(rings[0])))
    if broken:
        h=L*rng.uniform(.18,.32);plane_cut(tmp,Vector((0,0,h)),Vector((rng.uniform(-.5,.5),rng.uniform(-.5,.5),1)).normalized())
        for v in tmp.verts:
            if v.co.z>h*.7:v.co.z+=.006*noise.noise(v.co*90)
    tmp.transform(Matrix.Translation(base)@q);merge_into(bm,tmp)

def yumai(post):
    rng=random.Random(3301);gh=soil_bed((.98,.80,.07),61,rng,40)
    peb=new_bm()
    for k in range(26):
        a=rng.uniform(0,TAU);r=rng.uniform(.58,.92);x,y=r*math.cos(a)*1.05,r*math.sin(a)*.85;s=rng.uniform(.018,.05)
        lumpy_into(peb,(x,y,gh(Vector((x,y,0)))+s*.2),(s*1.3,s,s*.6),400+k,2,.3,2.2,a)
    link('Ore_Pebbles',peb,[M['stone']])
    c=(0,0,.02);R=(.66,.50,.58);bm=new_bm();lumpy_into(bm,c,R,62,5,.17,1.3,.3);chisel(bm,c,R,10,rng,(-.05,.85));flat_base(bm)
    anchor,nrm=surface_anchor(bm,(.06,-.18),.35);link('Ore_Boulder',bm,[M['stone_s']])
    for k,(x,y,s) in enumerate([(.62,.22,.22),(-.58,.18,.18)]):
        b2=new_bm();cc=(x,y,0);rr=(s*1.3,s,s);lumpy_into(b2,cc,rr,70+k,3,.18,1.3);chisel(b2,cc,rr,4,rng);flat_base(b2);link(f'Ore_Side_Stone_{k}',b2,[M['stone']])
    cr=new_bm();frame=nrm.to_track_quat('Z','Y').to_matrix()
    specs=[(0,.05,.075,.50),(.8,.42,.06,.40),(1.9,.38,.055,.34),(3.0,.5,.05,.30),(4.1,.40,.046,.27),(5.2,.55,.04,.22),(1.4,.9,.034,.17),(3.6,.85,.03,.15),(2.5,.7,.026,.12),(5.8,.95,.024,.1)]
    for k,(a,lean,r,L) in enumerate(specs):
        d=(frame@Vector((math.sin(lean)*math.cos(a),math.sin(lean)*math.sin(a),math.cos(lean)))).normalized()
        base=anchor+(frame@Vector((math.cos(a),math.sin(a),0)))*(.012+.11*lean)-d*.06;crystal_into(cr,base,d,r,L,rng,post)
    if post:
        link('Ore_Broken_Crystal_Stumps',cr,[M['crystal_dull']],False)
        sh=new_bm()
        for k in range(9):
            a=-2.2+k*.5+rng.uniform(-.2,.2);r=rng.uniform(.6,.85);x,y=r*math.cos(a)*1.05,r*math.sin(a)*.85;z=gh(Vector((x,y,0)))
            if k<5:crystal_into(sh,Vector((x,y,z+.012)),Vector((math.cos(a+1.6),math.sin(a+1.6),.12)).normalized(),rng.uniform(.018,.03),rng.uniform(.07,.13),rng,True)
            else:lumpy_into(sh,(x,y,z+.01),(.03,.022,.014),930+k,1,.35,2.5,a)
        link('Ore_Shards_And_Chips',sh,[M['crystal_dull']],False)
    else:link('Ore_Glow_Crystals',cr,[M['crystal']],False)
    ctx.extra['crystal_anchor_m']=[round(x,3) for x in anchor]

def landmark(post):
    rng=random.Random(3401);H=5.0
    bm=new_bm();lathe_into(bm,[(0,0),(.70,0),(.70,.05),(.68,.17),(.64,.19),(.53,.205),(.52,.215),(.50,.36),(.47,.385),(.44,.40),(0,.40)],8,rot=TAU/16,jitter=.012)
    link('Landmark_Stone_Plinth',bm,[M['plinth']],False)
    fs=new_bm()
    for k in range(11):
        a=k*TAU/11+rng.uniform(-.12,.12);r=rng.uniform(.78,.9);s=rng.uniform(.10,.17);c=(r*math.cos(a),r*math.sin(a),0);rr=(s*1.4,s,s*.8)
        sub=bmesh.new();lumpy_into(sub,c,rr,500+k,3,.2,1.4,a);chisel(sub,c,rr,3,rng);flat_base(sub);merge_into(fs,sub)
    link('Landmark_Field_Stones',fs,[M['stone']])
    wood=new_bm();tube_into(wood,[(0,0,.3),(0,0,1.5),(0,0,3.0),(0,0,4.2),(0,0,H-.1)],[.082,.077,.071,.066,.062],14,jitter=.04)
    for x in (-.40,.46):tube_into(wood,[(0,0,3.92),(x*.5,0,4.17),(x*.8,0,4.37)],[.03,.028,.026],8)
    for k in range(4):
        a=k*TAU/4+TAU/8;tube_into(wood,[(0,0,1.15),(.22*math.cos(a),.22*math.sin(a),.75),(.40*math.cos(a),.40*math.sin(a),.385)],[.036,.038,.04],8,jitter=.05)
    link('Landmark_Timber_Pole',wood,[M['timber']])
    bar=new_bm();box_into(bar,(.16,0,4.42),(1.86,.10,.12),.014,.006);link('Landmark_Crossbar',bar,[M['timber_x']])
    ir=new_bm()
    for z in (.48,1.18,4.28):tube_into(ir,[(0,0,z-.03),(0,0,z+.03)],[.088 if z<2 else .073]*2,16)
    for x in (-.77,1.09):box_into(ir,(x,0,4.42),(.05,.112,.132),.004)
    for x in (.18,.48,.78):tube_into(ir,[(x,-.004,4.30),(x,-.004,4.37)],[.010,.010],8)
    link('Landmark_Iron_Fittings',ir,[M['iron']])
    R=.72;N=44;bm=new_bm();g=[]    # barrel-tile hip roof: corrugated surface + hip ridges
    for j in range(N+1):
        row=[]
        for i in range(N+1):
            x=-R+2*R*i/N;y=-R+2*R*j/N;m=max(abs(x),abs(y))/R;z=.42*(1-m)**1.3+.16*((abs(x)*abs(y))/R**2)**2.4
            along=y if abs(x)>abs(y) else x;z+=.022*abs(math.sin(along*math.pi/.075))*min(1,(1-m)*12+.3)
            row.append(bm.verts.new((x,y,4.80+z)))
        g.append(row)
    for j in range(N):
        for i in range(N):bm.faces.new((g[j][i],g[j][i+1],g[j+1][i+1],g[j+1][i]))
    bmesh.ops.solidify(bm,geom=bm.faces[:],thickness=.05)
    for s in (1,-1):
        for t in (1,-1):tube_into(bm,[(s*R*u,t*R*u,4.80+.42*(1-u)**1.3+.16*(u*u)**2.4+.05) for u in [k/8 for k in range(9)]],[.03]*9,8)
    bmesh.ops.rotate(bm,verts=bm.verts[:],cent=(0,0,0),matrix=Matrix.Rotation(TAU/8,3,'Z'))
    link('Landmark_Teal_Tile_Cap',bm,[M['tile']])
    fin=new_bm();lathe_into(fin,[(0,5.20),(.07,5.21),(.10,5.27),(.10,5.31),(.06,5.36),(.035,5.39),(.04,5.42),(.085,5.47),(.09,5.52),(.06,5.58),(.02,5.62),(0,5.63)],14)
    link('Landmark_Gourd_Finial',fin,[M['gourd']])
    rod=new_bm();tube_into(rod,[(.08,0,4.29),(.92,0,4.29)],[.012,.012],8);link('Landmark_Banner_Rod',rod,[M['timber_x']])
    cloth=new_bm();x0,x1,zt,zb=.10,.90,4.27,1.62;nx,nzr=16,64;gg=[]
    def wob(u,v):return .055*math.sin(v*5.2+u*1.4)*v+.018*math.sin(u*11+v*3)*v+.01*math.sin(u*25)
    def sway(v):return .035*math.sin(v*3)*v
    for j in range(nzr+1):
        v=j/nzr;row=[]
        for i in range(nx+1):
            u=i/nx;z=zt-(zt-zb)*v+.40*(1-abs(2*u-1))*v**30+.03*abs(math.sin(u*41))*v**40   # swallowtail notch + frayed hem
            row.append(cloth.verts.new((x0+(x1-x0)*u+sway(v),wob(u,v),z)))
        gg.append(row)
    for j in range(nzr):
        for i in range(nx):cloth.faces.new((gg[j][i],gg[j][i+1],gg[j+1][i+1],gg[j+1][i]))
    bmesh.ops.solidify(cloth,geom=cloth.faces[:],thickness=.006)
    link('Landmark_Jade_Banner',cloth,[M['cloth']])
    em=new_bm();cx,cz=(x0+x1)/2,3.45
    def on_cloth(x,z,off):v=(zt-z)/(zt-zb);u=(x-x0)/(x1-x0);return em.verts.new((x+sway(v),wob(u,v)+off,z))
    for side in (-1,1):
        off=side*.011;ring=[]
        for k in range(40):
            a=k*TAU/40
            for r in (.27,.235):ring.append(on_cloth(cx+r*math.cos(a),cz+r*math.sin(a),off))
        for k in range(40):
            a,b=ring[2*k],ring[2*k+1];c,d=ring[(2*k+2)%80],ring[(2*k+3)%80];em.faces.new((a,c,d,b) if side<0 else (a,b,d,c))
        for ang,ln in [(math.pi/2,.21),(math.pi/2+.7,.16),(math.pi/2-.7,.16),(math.pi/2+1.25,.11),(math.pi/2-1.25,.11)]:
            rows=[]
            for s in range(12):
                t=s/11;w=.042*math.sin(math.pi*t)**.75*(ln/.21)+.0015;px=cx+math.cos(ang)*ln*1.45*t;pz=cz-.17+math.sin(ang)*ln*1.45*t
                nx_,nz_=-math.sin(ang)*w,math.cos(ang)*w;rows.append([on_cloth(px-nx_,pz-nz_,off*1.25),on_cloth(px+nx_,pz+nz_,off*1.25)])
            for a,b in zip(rows,rows[1:]):em.faces.new((a[0],b[0],b[1],a[1]) if side<0 else (a[0],a[1],b[1],b[0]))
    link('Landmark_Banner_Emblem',em,[M['embroidery']],False)
    LX=-.62;lan=new_bm();lathe_into(lan,[(0,3.74),(.15,3.75),(.21,3.81),(.235,3.89),(.235,3.95),(.21,4.03),(.15,4.08),(0,4.09)],16,(LX,0,0))
    link('Landmark_Glow_Lantern_Paper',lan,[M['paper']])
    fr=new_bm();lathe_into(fr,[(0,4.07),(.155,4.07),(.16,4.11),(.04,4.125),(0,4.125)],16,(LX,0,0));lathe_into(fr,[(0,3.715),(.04,3.715),(.16,3.73),(.155,3.765),(0,3.765)],16,(LX,0,0))
    for k in range(8):
        a=k*TAU/8;tube_into(fr,[(LX+r*math.cos(a),r*math.sin(a),z) for r,z in [(.15,3.75),(.21,3.81),(.238,3.89),(.238,3.95),(.21,4.03),(.15,4.08)]],[.0045]*6,5)
    tube_into(fr,[(LX,0,4.125),(LX,0,4.37)],[.005,.005],6)
    link('Landmark_Lantern_Frame',fr,[M['timber_x']])
    ts=new_bm();tube_into(ts,[(LX,0,3.715),(LX,0,3.62)],[.004,.004],5);lathe_into(ts,[(0,3.42),(.035,3.44),(.03,3.60),(.012,3.625),(0,3.63)],10,(LX,0,0),jitter=.1)
    link('Landmark_Lantern_Tassel',ts,[M['lacquer']])
    bk=new_bm();lathe_into(bk,[(0,0),(.15,0),(.19,.10),(.205,.22),(.215,.25),(.195,.255),(.18,.06),(0,.06)],20,(.78,-.42,0))
    tube_into(bk,[(.78+.21*math.cos(a),-.42+.21*math.sin(a),.25) for a in [k*TAU/24 for k in range(25)]],[.012]*25,6,False)
    link('Landmark_Herb_Basket',bk,[M['basket']])
    hb=new_bm()
    for k in range(9):
        az=k*GOLDEN;pts,h=arch((.78+.07*math.cos(az),-.42+.07*math.sin(az),.06),az,rng.uniform(.25,.36),.12,1.1,10)
        ribbon_into(hb,pts,[.012*min(1,j/10*6)*(1-j/10)**.5+.0008 for j in range(11)],Vector((-h.y,h.x,0)),.35,0,5,(rng.random(),0,0))
    link('Landmark_Basket_Herbs',hb,[M['leaf_q']])

def plank(post):
    rng=random.Random(3501);pl=new_bm()
    for k,(x,y) in enumerate([(-.3,-.22),(.3,-.22),(-.3,.22),(.3,.22)]):
        tube_into(pl,[(x,y,0),(x+rng.uniform(-.012,.012),y+rng.uniform(-.01,.01),.25),(x,y,.47)],[.062,.058,.055],12,jitter=.022,seed=k)
    link('Plank_Barked_Piles',pl,[M['pile']])
    bmb=new_bm()
    for k,y in enumerate((-.22,.22)):box_into(bmb,(0,y,.505),(.82,.085,.075),.012,.004,k)
    link('Plank_Hewn_Beams',bmb,[M['beam']])
    top=new_bm()
    for k,x in enumerate((-.248,0,.248)):
        box_into(top,(x,rng.uniform(-.008,.008),.569),(.232+rng.uniform(-.006,.004),.70+rng.uniform(-.015,.01),.052+rng.uniform(-.004,.003)),.009,.005,10+k)
    link('Plank_Foot_Surface_Boards',top,[M['plank']])
    nl=new_bm()
    for x in (-.248,0,.248):
        for y in (-.22,.22):
            for dx in (-.06,.06):lathe_into(nl,[(0,.5925),(.009,.593),(.0085,.597),(0,.5985)],8,(x+dx+rng.uniform(-.008,.008),y+rng.uniform(-.008,.008),0))
    link('Plank_Iron_Nails',nl,[M['iron']])
    rope=new_bm()
    for x in (-.3,.3):
        for y in (-.22,.22):tube_into(rope,[(x+.07*math.cos(t*TAU),y+.063*math.sin(t*TAU),.43+.0125*t) for t in [s/12 for s in range(49)]],[.009]*49,6)
    link('Plank_Rope_Lashing',rope,[M['rope']])

def reeds(post):
    rng=random.Random(3601);bm=new_bm();lumpy_into(bm,(0,0,0),(.36,.32,.07),71,4,.22,2.2);flat_base(bm);gh=ground_height(bm);link('Reed_Wet_Mud_Tuft',bm,[M['mud']])
    pb=new_bm()
    for k in range(10):
        a=rng.uniform(0,TAU);r=rng.uniform(.18,.33);x,y=r*math.cos(a),r*math.sin(a);s=rng.uniform(.015,.035)
        lumpy_into(pb,(x,y,gh(Vector((x,y,0)))+s*.1),(s*1.3,s,s*.6),800+k,2,.3,2.2,a)
    link('Reed_Pebbles',pb,[M['stone']])
    bl=new_bm()
    for i in range(56):
        a=i*GOLDEN;r=.2*math.sqrt(rng.random());base=Vector((r*math.cos(a),r*math.sin(a),0));base.z=gh(base)-.01;L=rng.uniform(.7,1.5);W=rng.uniform(.006,.010)
        n=16;pts,h=arch(base,a+rng.uniform(-.5,.5),L,rng.uniform(.02,.2),rng.uniform(.3,1.25),n,2.2)
        if rng.random()<.2:
            k=rng.randint(9,12);dn=Vector((h.x*.35,h.y*.35,-1)).normalized();pts=pts[:k+1]+[pts[k]+dn*(L/n)*s for s in range(1,n-k+1)]
        ws=[W*(1-j/(len(pts)-1))**.7+.0006 for j in range(len(pts))]
        ribbon_into(bl,pts,ws,Vector((-h.y,h.x,0)),.3,rng.uniform(-1,1),3,(rng.random(),1.0 if rng.random()<.22 else rng.random()*.4,0))
    link('Reed_Blades',bl,[M['blade']])
    st=new_bm();heads=new_bm()
    for k in range(7):
        a=k*TAU/7+.4;r=.04+.09*((k*3)%7)/7;H=rng.uniform(1.15,1.6);lean=Vector((math.cos(a),math.sin(a),0))*rng.uniform(.04,.14)
        b=Vector((r*math.cos(a),r*math.sin(a),0));b.z=gh(b)-.01
        pts=[b+lean*(t*t)+Vector((0,0,H*t)) for t in [s/12 for s in range(13)]];tube_into(st,pts,[.0055-.0015*s/12 for s in range(13)],6)
        d=(pts[-1]-pts[-2]).normalized();q=d.to_track_quat('Z','Y').to_matrix().to_4x4()
        vs=lathe_into(heads,[(0,0),(.012,.004),(.019,.02),(.021,.06),(.021,.13),(.019,.16),(.011,.175),(0,.18)],12,jitter=.05)
        bmesh.ops.transform(heads,matrix=Matrix.Translation(pts[-1]-d*.19)@q,verts=vs)
        tube_into(st,[pts[-1]-d*.01,pts[-1]+d*.08],[.0025,.0008],4)
    link('Reed_Stems',st,[M['reedstem']])
    link('Reed_Cattail_Heads',heads,[M['cattail']])
    pl=new_bm()
    for k in range(4):
        a=k*1.7+1.2;b=Vector((.13*math.cos(a),.13*math.sin(a),0));b.z=gh(b)-.01;pts,h=arch(b,a,1.35+.1*k,.04,.36,12,1.8);tube_into(pl,pts,[.0035]*13,4,False)
        for s in range(26):
            sa=s*GOLDEN;along=pts[-1-int(s/26*4)];d=(h*.5+Vector((math.cos(sa)*.5,math.sin(sa)*.5,-.55-.4*rng.random()))).normalized();sd=d.cross(Vector((0,0,1))).normalized()
            ribbon_into(pl,[along+d*.15*u+Vector((0,0,-.03*u*u)) for u in (0,.3,.6,.85,1)],[.0015,.006,.007,.005,.0015],sd,.2,0,3,(rng.random(),0,0))
    link('Reed_Plumes',pl,[M['plume']])

BUILDERS={'QX_SpiritHerb_Qinglan':qinglan,'QX_SpiritHerb_Chilu':chilu,'QX_EmbeddedOre_Yumai':yumai,'QX_GatheringLandmark':landmark,'QX_CreekSteppingPlank':plank,'QX_WaterReeds':reeds}
CENTRE_XY={'QX_GatheringLandmark':False}
GROUND_ORIGIN={'QX_EmbeddedOre_Yumai'}

def state_key(aid,st):return aid if st=='base' else f'{aid}_{st}'

def build_state(aid,st,parent_coll,location=(0,0,0)):
    """Build one asset state into its own collection; returns (root, mesh objects)."""
    make_materials()
    # the ore seam / scar masks live in the boulder material, so it is made per state
    key=state_key(aid,st);ctx.coll=bpy.data.collections.new(key);parent_coll.children.link(ctx.coll)
    ctx.root=bpy.data.objects.new(key+'_ROOT',None);ctx.coll.objects.link(ctx.root);ctx.objs=[];ctx.vdata={};ctx.extra={}
    BUILDERS[aid](st=='post')
    pts=[v.co for o in ctx.objs for v in o.data.vertices];lo=Vector([min(p[i] for p in pts) for i in range(3)]);hi=Vector([max(p[i] for p in pts) for i in range(3)])
    shift=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z)) if CENTRE_XY.get(aid,True) else Vector((0,0,lo.z))
    if aid in GROUND_ORIGIN:shift.z=0.0   # origin at ground level; a terrain-blend rim dips just below it
    for o in ctx.objs:o.data.transform(Matrix.Translation(-shift))
    ctx.root.location=location;ctx.root['asset']=aid;ctx.root['state']=st;ctx.root['origin_shift_applied_m']=list(shift)
    for k,v in ctx.extra.items():ctx.root[k]=v
    return ctx.root,list(ctx.objs)

def stats(objs):
    pts=[o.matrix_world@v.co for o in objs for v in o.data.vertices]
    lo=Vector([min(p[i] for p in pts) for i in range(3)]);hi=Vector([max(p[i] for p in pts) for i in range(3)])
    return {'dimensions_m':[round(x,4) for x in hi-lo],'bounds_min_m':[round(x,4) for x in lo],'bounds_max_m':[round(x,4) for x in hi],
            'triangles':sum(len(p.vertices)-2 for o in objs for p in o.data.polygons),'vertices':sum(len(o.data.vertices) for o in objs),
            'mesh_objects':len(objs),'source_materials':sorted({m.name for o in objs for m in o.data.materials})}

# the ore was rebuilt from scratch in its own module (split boulder, boolean secondary forms)
import qx_ore
BUILDERS['QX_EmbeddedOre_Yumai']=qx_ore.build
CENTRE_XY['QX_EmbeddedOre_Yumai']=False

# the landmark was rebuilt as a semi-real timber gate with a stone coping in its own module
import qx_gate
BUILDERS['QX_GatheringLandmark']=qx_gate.build
NAMES['QX_GatheringLandmark']='採藥山門（採集地標）'
GROUND_ORIGIN.add('QX_GatheringLandmark')

# the red-berry herb was rebuilt semi-real in its own module
import qx_chilu
BUILDERS['QX_SpiritHerb_Chilu']=qx_chilu.build
CENTRE_XY['QX_SpiritHerb_Chilu']=False
GROUND_ORIGIN.add('QX_SpiritHerb_Chilu')

# the orchid, the stepping plank and the reeds were rebuilt semi-real in their own modules
import qx_qinglan,qx_plank,qx_reeds
BUILDERS['QX_SpiritHerb_Qinglan']=qx_qinglan.build
BUILDERS['QX_CreekSteppingPlank']=qx_plank.build
BUILDERS['QX_WaterReeds']=qx_reeds.build
for _aid in ('QX_SpiritHerb_Qinglan','QX_WaterReeds'):
    CENTRE_XY[_aid]=False;GROUND_ORIGIN.add(_aid)

DESIGN.update({
 'QX_SpiritHerb_Qinglan':'Creek orchid (Cymbidium-like): fan clump of 18 keeled strap leaves arching in crossing S curves, papery sheaths and pseudobulbs, three scapes with bracts and 5-7 nodding jade blossoms (cupped sepals, hooded petals, spotted recurved lip, the top ones buds) in the lee of a mossy stone. Post: scapes cut to stubs, outer leaves sickle-cut, young leaves kept, two new shoots, cut leaves / scape / blossoms on the soil.',
 'QX_SpiritHerb_Chilu':'Ginseng-like spirit herb patch: dense meadow grass feathering out at the rim, three fruiting plants of graded size and three young plants growing through it, so the compact crimson umbels sit among the blades. Each plant: S-curved stem, whorl of palmate leaves (five finely serrated leaflets). Post: every umbel stripped to short broken pedicels, one missed green berry, one leaf snapped and wilting, grass trampled flat round the main plant, crushed berries.',
 'QX_EmbeddedOre_Yumai':'Split granite boulder pair sunk in a soil skirt: bedded, flaked and cracked surfaces (remeshed high poly), moss cushions on the upper and back faces, a pale jade cleft between the blocks with a cluster of glowing terminated crystals. Post: crystals broken to glassy fractured stumps, fresh scar and chips, shards on the soil.',
 'QX_GatheringLandmark':'Herb-gatherers\u2019 timber paifang: clamp stones with iron hoops, hewn posts with raking struts, through-tenoned tie beam with wedges and drying herb bundles, framed emblem plaque, que-ti brackets, carved stone hip roof with tile rolls and a jade pearl; jade banners, a lantern and a herb basket.',
 'QX_CreekSteppingPlank':'Stepping bay: river cobbles round the pile feet, four barked round piles with a waterline algae band, two hewn beams in saddle notches with forged cramps, three cupped hewn deck boards with square-head spikes; the board tops (0.62 m) are the only light, flat surface and carry a worn tread.',
 'QX_WaterReeds':'Water-edge clump: nine Typha shoots in flat leaf fans (some kinked), five cattails (one bursting into fluff), three jointed Phragmites culms with drooping leaves and nodding purple-brown plumes, dead leaves folded onto a wet mud tuft with pebbles.'})
MATERIAL_DIRECTION.update({
 'QX_SpiritHerb_Qinglan':'Glossy deep jade-green leaves (rough 0.32) with fine parallel veins, pale keel, yellow-green sheath base and a few straw-dry tips; blossoms pale jade with darker veins, ivory lip with red-violet spots, soft inner glow; papery straw sheaths.',
 'QX_SpiritHerb_Chilu':'Dark green leaflets with pinnate veins, yellowing margins and back-light; stem green flushing purple-red at the whorl; berries deep crimson, waxy (rough 0.30) with a dark stylar point, faint inner glow = the kit hot accent.',
 'QX_EmbeddedOre_Yumai':'Cool grey granite with bed tone shifts, mineral grains, worn edges, rain streaks, lichen and moss; pale jade cleft coat and veins; crystals translucent jade with inner emission (pre) / darker drained glassy stumps with rippled fractures (post).',
 'QX_GatheringLandmark':'Silver-weathered hewn timber with growth rings and checks, pale moss-spotted stone, dark forged iron, deep jade cloth with painted emblem, warm lantern paper, pale jade pearl.',
 'QX_CreekSteppingPlank':'Board tops silver-grey weathered timber with a lighter, smoother worn tread; darker beams; dark furrowed bark with peeled patches, a green algae band and dark wet wood below the waterline; wet dark cobbles; black forged iron.',
 'QX_WaterReeds':'Leaves green with pale bases yellowing to straw tips, dead ones grey-brown; dark cinnamon velvet cattails, pale fluff; purple-brown plumes with silvery hairs; near-black wet mud with mirror puddles and a pale silt rim.'})
# v002: descriptions follow the reviewed AI three-views R01-R06 (art/references/.../ai_threeview_v002)
DESIGN.update({
 'QX_SpiritHerb_Qinglan':'v002 to R01/R01b. Creek orchid clump: 26 broad keeled strap leaves with yellowed tips, three large sheathed pseudobulbs with brown bracts, four upright scapes with open white star blossoms (cyan glow at the heart) and a bud cluster at the top, a moss stone behind on the left. Post: leaves kept, scapes cut to tall stubs with pale cut faces, cut scape pieces on the soil.',
 'QX_SpiritHerb_Chilu':'v002 to R02/R02b. Low wide patch: one main ginseng-like plant and two smaller fruiting plants plus a young one, each a short thick stem, a flat whorl of palmate leaves (five serrated leaflets) and a straight peduncle to a dense globe of glossy crimson berries; soil, moss cushions and pebbles visible between sparse grass. Post: the main plant dug out (pit, clods, torn root), side umbels stripped to broken pedicels, torn leaflets.',
 'QX_EmbeddedOre_Yumai':'v002 to R03/R03b. Split pale granite boulder with the cleft facing front, right block lower, glowing jade veins along the beds, a fan of tall milky jade crystals (main about 1.3 x the block) out of the cleft. Post: crystals snapped to dull stumps, veins unlit.',
 'QX_GatheringLandmark':'v002 to R04. Two-post timber paifang: cloud-carved clamp stones bound in iron, near-round posts with one outward raking strut each, through-tenoned tie beam with wedges and two pairs of drying herb bundles, wide jade plaque with emblem and cloud reliefs between studs, que-ti brackets, dou-gong row, concave grey-teal tiled roof with flying corners, barrel tiles, hip ridges, ridge scrolls and a jade pearl on a lotus base; jade banners from poles past the lintel ends, paper lantern, wicker herb basket. Clear opening 2.22 m at the ground.',
 'QX_CreekSteppingPlank':'v002 to R05. Stepping bay on two T supports: one central round pile per support in a heap of wet river cobbles with an algae band, a round cross log across the full width (growth rings at both ends) lashed with hemp rope coils and iron I-cramps, three cupped deck boards with square-head spikes; the board tops (0.62 m) are the only light, flat surface.',
 'QX_WaterReeds':'v002 to R06. About 1.9 m water-edge clump: twelve Typha shoots of broad strap leaves, many arching outward and down, green mixed with dry straw; three cattails (one bursting into fluff); two Phragmites culms with broad leaves and big pale silvery plumes; broken dead stems and dead leaves at the base of a wet mud tuft with pebbles and grass.'})
MATERIAL_DIRECTION.update({
 'QX_GatheringLandmark':'Weathered hewn timber with growth rings and checks, pale cloud-carved stone with moss, dark forged iron, grey-teal fired tiles with moss and rain streaks, jade lacquer plaque, deep jade cloth with painted emblem, warm lantern paper, golden wicker, pale jade pearl.',
 'QX_CreekSteppingPlank':'Warm brown weathered boards with a lighter worn tread; round logs with ring ends; hewn pile dark and wet low down under a ragged green algae band; wet grey cobbles; hemp rope; dark rusty forged iron.',
 'QX_EmbeddedOre_Yumai':'Pale cool granite with bed tone shifts, grains, rain streaks, lichen and moss; glowing jade bed veins and cleft coat (pre); milky translucent jade crystals with inner emission (pre) / dull drained stumps (post).',
 'QX_WaterReeds':'Leaves green with pale bases yellowing to straw tips, many fully dry, dead ones grey-brown; dark cinnamon velvet cattails, white fluff; pale buff-silver plumes; dead stems grey-straw; near-black wet mud with puddles and a pale silt rim.'})
