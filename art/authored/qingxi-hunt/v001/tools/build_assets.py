"""Build reviewed Qingxi environment assets. Run only in a NEW headless Blender.
References must exist before modeling. Rebuild writes only this version's outputs.
Requires installed blender-* skill helpers; override QINGXI_SKILLS if needed.
"""
import bpy, bmesh, math, random, json, sys, os, hashlib
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
SKILLS = Path(os.environ.get('QINGXI_SKILLS', str(Path.home()/'.codex/skills')))
for sub in ['blender-asset-qa', 'blender-export-pipelines']:
    sys.path.insert(0, str(SKILLS/sub/'scripts'))
import qa_check, export_asset, review_shots
assert bpy.app.background, 'Use a fresh background process; never reset a live scene.'
for ref in ['V01_low-grass.png','V02_trampled-grass.png','V03_stream-bank.png']:
    assert (ROOT/'references'/ref).is_file(), ref
for d in ['models','previews','reports','textures']:
    (ROOT/d).mkdir(exist_ok=True)

PALETTE = [(0.08,.19,.085),(.16,.31,.095),(.29,.43,.12),(.45,.56,.19),
           (.53,.36,.20),(.66,.49,.29),(.76,.61,.40),(.36,.40,.34)]

def palette_material():
    # Authored swatch texture, not a modification of any AI image.
    im=bpy.data.images.new('T_QingxiPalette',128,128,alpha=True)
    pix=[]
    for y in range(128):
        shade=.85+.15*y/127
        for x in range(128):
            c=PALETTE[x//16]
            pix.extend([v*shade for v in c]+[1])
    im.pixels.foreach_set(pix)
    im.filepath_raw=str(ROOT/'textures/T04_model-palette.png')
    im.file_format='PNG'; im.save()
    mat=bpy.data.materials.new('M_QingxiPalette')
    mat.diffuse_color=(.23,.38,.12,1)
    bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    bs.inputs['Roughness'].default_value=.88
    bs.inputs['Metallic'].default_value=0
    tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=im
    tex.interpolation='Closest'
    mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    return mat

class Mesh:
    def __init__(self): self.v=[]; self.f=[]; self.c=[]
    def add(self, verts, faces, color):
        n=len(self.v);self.v.extend(verts)
        self.f.extend([tuple(n+i for i in f) for f in faces])
        self.c.extend(color if isinstance(color,list) else [color]*len(faces))
    def ellipsoid(self, center, scale, color, segments=12, rings=4):
        vs=[(center[0],center[1],center[2]-scale[2])]
        for j in range(1,rings):
            t=-math.pi/2+math.pi*j/rings
            for i in range(segments):
                a=i*2*math.pi/segments
                vs.append((center[0]+scale[0]*math.cos(t)*math.cos(a),center[1]+scale[1]*math.cos(t)*math.sin(a),center[2]+scale[2]*math.sin(t)))
        top=len(vs);vs.append((center[0],center[1],center[2]+scale[2]))
        fs=[]
        for i in range(segments):
            a=1+i;b=1+(i+1)%segments;fs.append((0,b,a))
            for j in range(rings-2):
                q=1+j*segments+i;r=1+j*segments+(i+1)%segments
                fs.append((q,r,r+segments,q+segments))
            q=1+(rings-2)*segments+i;r=1+(rings-2)*segments+(i+1)%segments
            fs.append((q,r,top))
        self.add(vs,fs,color)
    def blade(self, root, angle, height, reach, width, shade, flat=False, segments=5):
        direction=Vector((math.cos(angle),math.sin(angle),0))
        lateral=Vector((-direction.y,direction.x,0))
        vs=[]
        for i in range(segments):
            t=i/segments
            # Diamond cross section yields closed, solid, faceted leaves.
            p=Vector(root)+direction*(reach*t*t if not flat else reach*t)
            p.z+=height*(math.sin(t*math.pi*.67) if not flat else math.sin(t*math.pi))
            w=width*(.17+.83*math.sin(math.pi*t))*(1-t*.7)
            thickness=.004*(1-t*.7)
            vs.extend([tuple(p-lateral*w),tuple(p+Vector((0,0,thickness))),tuple(p+lateral*w),tuple(p-Vector((0,0,thickness)))])
        tip=Vector(root)+direction*reach
        tip.z+=height*(math.sin(math.pi*.67) if not flat else .12)
        ti=len(vs);vs.append(tuple(tip))
        fs=[(3,2,1,0)];colors=[shade]
        for i in range(segments-1):
            for j in range(4):
                fs.append((i*4+j,i*4+(j+1)%4,(i+1)*4+(j+1)%4,(i+1)*4+j))
                colors.append(min(3,max(0,shade+(1 if i>1 else 0))))
        for j in range(4): fs.append(((segments-1)*4+j,(segments-1)*4+(j+1)%4,ti));colors.append(min(3,shade+1))
        self.add(vs,fs,colors)
    def object(self,name,material,dimensions=None):
        if dimensions:
            lo=[min(v[i] for v in self.v) for i in range(3)]
            hi=[max(v[i] for v in self.v) for i in range(3)]
            self.v=[tuple((v[i]-(lo[i]+hi[i])/2)*dimensions[i]/(hi[i]-lo[i]) if i<2 else (v[i]-lo[i])*dimensions[i]/(hi[i]-lo[i]) for i in range(3)) for v in self.v]
        me=bpy.data.meshes.new(name);me.from_pydata(self.v,[],self.f);me.update()
        for p,c in zip(me.polygons,self.c):p.material_index=c
        bm=bmesh.new();bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        bmesh.ops.triangulate(bm,faces=list(bm.faces))
        bm.to_mesh(me);bm.free();me.update()
        uv=me.uv_layers.new(name='UVMap')
        for p in me.polygons:
            band=p.material_index
            u=(band+.5)/8;v=.20+.60*((p.index*37)%101)/100
            for li,offset in zip(p.loop_indices,[(-.025,-.02),(.025,-.02),(0,.02)]):uv.data[li].uv=(u+offset[0],v+offset[1])
            p.material_index=0
        ob=bpy.data.objects.new(name,me);bpy.context.scene.collection.children['Export'].objects.link(ob)
        me.materials.append(material)
        return ob

def grass(lod,trampled):
    rng=random.Random(371 if not trampled else 817)
    m=Mesh()
    if not trampled:
        m.ellipsoid((0,0,.018),(.22,.18,.018),0,12,4)
        for i in range([30,16,8][lod]):
            a=rng.uniform(0,math.tau);r=rng.uniform(.015,.16)
            root=(r*math.cos(a),r*.8*math.sin(a),.012)
            m.blade(root,a+rng.uniform(-.5,.5),rng.uniform(.22,.42),rng.uniform(.16,.35),rng.uniform(.035,.07),rng.choice([1,1,2]),segments=[5,4,3][lod])
    else:
        m.ellipsoid((0,0,.018),(.64,.39,.018),0,16,4)
        n=[42,24,12][lod]
        for i in range(n):
            side=-1 if i%2 else 1
            root=(side*rng.uniform(.29,.43),rng.uniform(-.26,.24),.015)
            a=rng.uniform(0,math.tau)
            m.blade(root,a,rng.uniform(.16,.28),rng.uniform(.10,.23),rng.uniform(.025,.052),rng.choice([1,2]),segments=[5,4,3][lod])
        count=[20,10,6][lod]; columns=count//2
        for i in range(count):
            # Distinct lanes avoid nearly coplanar overlapping pressed leaves.
            root=(-.22+.44*(i%columns)/(columns-1),-.28+.28*(i//columns),.026)
            m.blade(root,math.pi/2,rng.uniform(.025,.038),.25,[.016,.026,.044][lod],2,flat=True,segments=[5,4,3][lod])
    return m

def bank(lod, collision=False):
    m=Mesh();n=1 if collision else [8,4,2][lod]
    vs=[]
    for j in range(n+1):
        for i in range(n+1):
            x=-2+4*i/n;y=-2+4*j/n;vs.append((x,y,.03+.30*j/n))
    fs=[];cs=[]
    rng=random.Random(11)
    for j in range(n):
        for i in range(n):
            a=j*(n+1)+i;fs.append((a,a+1,a+n+2,a+n+1));cs.append(rng.choice([5,6,6]))
    edge=list(range(n+1))+[j*(n+1)+n for j in range(1,n+1)]+[n*(n+1)+i for i in range(n-1,-1,-1)]+[j*(n+1) for j in range(n-1,0,-1)]
    lower=[]
    for idx in edge:lower.append(len(vs));vs.append((vs[idx][0],vs[idx][1],0))
    for i in range(len(edge)):
        k=(i+1)%len(edge);fs.append((edge[i],lower[i],lower[k],edge[k]));cs.append(4)
    center=len(vs);vs.append((0,0,0))
    for i in range(len(lower)):fs.append((center,lower[(i+1)%len(lower)],lower[i]));cs.append(4)
    m.add(vs,fs,cs)
    if not collision:
        for side in [-1,1]:
            for j in range([6,4,2][lod]):
                x=side*(1.74+rng.uniform(-.10,.04));y=-1.65+j*3.3/([6,4,2][lod]-1)
                z=.03+.30*(y+2)/4
                m.ellipsoid((x,y,z+.035),(.15+rng.random()*.07,.14+rng.random()*.06,.09),7,8,3)
            for y in [1.45,1.75]:
                z=.03+.30*(y+2)/4
                m.ellipsoid((side*1.69,y,z+.009),(.24,.20,.035),1,8,3)
    return m

def init_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc=bpy.context.scene;sc.unit_settings.system='METRIC';sc.unit_settings.scale_length=1
    for name in ['Export','Preview']:
        c=bpy.data.collections.new(name);sc.collection.children.link(c)
    sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True
    sc.render.resolution_x=1000;sc.render.resolution_y=800;sc.render.resolution_percentage=100
    sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGBA'
    sc.world=bpy.data.worlds.new('World');sc.world.use_nodes=True
    sc.world.node_tree.nodes.get('Background').inputs[0].default_value=(.22,.25,.29,1)
    sc.world.node_tree.nodes.get('Background').inputs[1].default_value=.5
    return sc

def beauty(ob,path):
    sc=bpy.context.scene;size=max(ob.dimensions);center=Vector((0,0,ob.dimensions.z*.4))
    for i,(p,power) in enumerate([((2,-3,5),700),((-3,-1,2),450),((0,3,4),800)]):
        light=bpy.data.lights.new('PreviewLight'+str(i),'AREA');light.energy=power*size*size;light.shape='DISK';light.size=size*3
        obj=bpy.data.objects.new(light.name,light);sc.collection.children['Preview'].objects.link(obj);obj.location=Vector(p)*size
        obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
    cam=bpy.data.cameras.new('PreviewCamera');cam.type='ORTHO';cam.ortho_scale=size*1.55
    co=bpy.data.objects.new('PreviewCamera',cam);sc.collection.children['Preview'].objects.link(co)
    co.location=center+Vector((1.2,-1.7,1.05))*size
    co.rotation_euler=(center-co.location).to_track_quat('-Z','Y').to_euler();sc.camera=co
    sc.render.film_transparent=True;sc.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)

def build():
    manifest={'blender':bpy.app.version_string,'unityVerified':False,'method':'Procedural mesh authored after reviewed AI three-view references','assets':[]}
    for stem,ref,dims in [('LowGrass','V01_low-grass.png',(.90,.70,.36)),('TrampledGrass','V02_trampled-grass.png',(1.50,.90,.28)),('StreamBank','V03_stream-bank.png',None)]:
        sc=init_scene();mat=palette_material();obs=[];qa={}
        for lod in range(3):
            m=bank(lod) if stem=='StreamBank' else grass(lod,stem=='TrampledGrass')
            ob=m.object('SM_'+stem+'_LOD'+str(lod),mat,dims);obs.append(ob)
            bpy.context.view_layer.update()
            report=qa_check.run(objects=[ob.name],profile='game',eps=.0002)
            qa[ob.name]=report
            (ROOT/'reports'/f'{ob.name}_qa.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            if not report['pass']:raise RuntimeError(f'{ob.name}: {report["errors"]}')
            ob.hide_render=lod>0;ob.hide_set(lod>0)
        collision=None
        if stem=='StreamBank':
            collision=bank(0,True).object('COL_StreamBank',mat)
            collision.hide_render=True;collision.hide_set(True)
            report=qa_check.run(objects=[collision.name],profile='game')
            qa[collision.name]=report
            if not report['pass']:raise RuntimeError(report['errors'])
        for ob in obs:
            ob.hide_set(False)
            export_asset.run(preset='unity',objects=[ob.name],out=str(ROOT/'models'/f'{ob.name}.fbx'),no_anim=True)
            export_asset.run(preset='gltf',objects=[ob.name],out=str(ROOT/'models'/f'{ob.name}.glb'),no_anim=True)
            ob.hide_set(ob!=obs[0])
        if collision:
            collision.hide_set(False)
            export_asset.run(preset='unity',objects=[collision.name],out=str(ROOT/'models/COL_StreamBank.fbx'),no_anim=True)
            collision.hide_set(True)
        for mode in ['material','wire']:
            review_shots.run(objects=[obs[0].name],out=str(ROOT/'previews'/f'{stem}_{mode}.png'),mode=mode,res=384)
        beauty(obs[0],ROOT/'previews'/f'{stem}_beauty.png')
        for im in bpy.data.images:
            if im.source=='FILE': im.filepath='//../textures/'+Path(im.filepath).name
        bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models'/f'{stem}.blend'))
        record={'name':stem,'reference':ref,'referenceSha256':hashlib.sha256((ROOT/'references'/ref).read_bytes()).hexdigest(),
            'dimensions':list(obs[0].dimensions),'lods':[{'name':ob.name,'triangles':len(ob.data.polygons),'materials':len(ob.material_slots)} for ob in obs],
            'qa':qa,'collision':'separate low-poly ramp mesh' if collision else 'none: decorative nonblocking foliage',
            'acceptedWarnings':'UVs deliberately share palette swatches; not a lightmap UV set. Generate UV2 in Unity if required.'}
        manifest['assets'].append(record)
        (ROOT/'reports/model-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('QINGXI_ASSETS_BUILT',flush=True)

if __name__=='__main__':build()
