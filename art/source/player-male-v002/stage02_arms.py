"""Stage 02: extrude connected arm/sleeve topology from approved torso study.
No face, hands, lower body, rig or export is produced in this checkpoint.
"""
import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parents[1]/'previews/player-male-v002/stage02'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Male_Stage01_TorsoAndCollar.blend'))
scene=bpy.context.scene
col=bpy.data.collections.new('03_Arms_Sleeves_Study');scene.collection.children.link(col)

def extend_side(ob,sign,garment=False):
    bm=bmesh.new();bm.from_mesh(ob.data)
    # Excise one shoulder patch and extrude its actual boundary. No intersecting
    # cylinder is joined to the torso, and no voxel remeshing destroys the cage.
    selected=[]
    for f in bm.faces:
        c=f.calc_center_median()
        if sign*c.x>(.164 if garment else .163) and 1.305<c.z<1.475:
            selected.append(f)
    assert selected,'Shoulder patch not found'
    selected_set=set(selected)
    edges=[e for e in bm.edges if sum(f in selected_set for f in e.link_faces)==1 and len(e.link_faces)==2]
    assert edges,'No shoulder perimeter'
    links={}
    for e in edges:
        for v in e.verts:links.setdefault(v,[]).append(e.other_vert(v))
    assert all(len(n)==2 for n in links.values()),'Shoulder boundary must be one cycle'
    start=next(iter(links));loop=[start];prev=None;cur=start
    while True:
        nxt=next(v for v in links[cur] if v!=prev)
        if nxt==start:break
        loop.append(nxt);prev,cur=cur,nxt
        assert len(loop)<=len(links)
    assert len(loop)==len(links),'Multiple shoulder boundary islands'
    bmesh.ops.delete(bm,geom=selected,context='FACES_ONLY')
    # Remove only newly unused interior edges/vertices, preserving the boundary.
    bmesh.ops.delete(bm,geom=[e for e in bm.edges if not e.link_faces and e not in edges],context='EDGES')
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_edges],context='VERTS')
    base=Vector((sign*.195,0,1.395))
    direction=Vector((sign*.64,0,-.768)).normalized()
    u=Vector((0,-1,0));v=direction.cross(u).normalized()
    # Preserve boundary vertex order while mapping its uneven perimeter to a
    # smooth elliptical section. Angles are computed from the anatomical plane.
    coords=[vert.co.copy() for vert in loop]
    centroid=sum(coords,Vector())/len(coords)
    projected=[Vector(((p-centroid).dot(u),(p-centroid).dot(v))) for p in coords]
    winding=sum(projected[i].x*projected[(i+1)%len(coords)].y-projected[(i+1)%len(coords)].x*projected[i].y for i in range(len(coords)))
    orientation=1 if winding>=0 else -1
    lengths=[(coords[(i+1)%len(coords)]-p).length for i,p in enumerate(coords)]
    perimeter=sum(lengths);distance=0
    startangle=math.atan2(projected[0].y,projected[0].x)
    angles=[]
    for length in lengths:
        angles.append(startangle+orientation*math.tau*distance/perimeter)
        distance+=length
    last=loop;rows=32 if garment else 48
    length=.295 if garment else .51
    uv=bm.loops.layers.uv.active or bm.loops.layers.uv.new('ConstructionUV')
    for j in range(1,rows+1):
        t=j/rows
        center=base+direction*(length*t)
        if garment:
            depth=.079+.006*t
            radius=.086+.019*t
            sag=Vector((0,0,-.012*t))
        else:
            if t<.45:r=.055-.019*(t/.45)
            elif t<.68:r=.036+.009*math.sin((t-.45)/.23*math.pi/2)
            else:r=.045-.020*((t-.68)/.32)
            depth=r*.86;radius=r;sag=Vector((0,0,0))
        blend=min(1,t/.22);blend=blend*blend*(3-2*blend)
        ring=[]
        for k,a in enumerate(angles):
            fold=(.0025*math.sin(6*a+2*t)+.001*math.sin(11*a-4*t))*math.sin(math.pi*t) if garment else 0
            q=center+sag+u*(math.cos(a)*(depth+fold))+v*(math.sin(a)*(radius+fold))
            q=(coords[k]+direction*(length*t)).lerp(q,blend)
            ring.append(bm.verts.new(q))
        for k in range(len(ring)):
            f=bm.faces.new((last[k],last[(k+1)%len(ring)],ring[(k+1)%len(ring)],ring[k]))
            if garment and t>.86:f.material_index=1
            for l,co in zip(f.loops,[(k/len(ring),(j-1)/rows),((k+1)/len(ring),(j-1)/rows),((k+1)/len(ring),j/rows),(k/len(ring),j/rows)]):l[uv].uv=co
        last=ring
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
    bm.to_mesh(ob.data);bm.free();ob.data.update()
    for p in ob.data.polygons:p.use_smooth=True

body=bpy.data.objects['Torso_ContinuousCage']
coat=bpy.data.objects['OuterRobe_UpperShell']
coat.data.materials.append(bpy.data.materials['M_IvoryBinding_Study'])
for modifier in coat.modifiers:
    if modifier.type=='SOLIDIFY':modifier.use_even_offset=False
for sign in [-1,1]:
    extend_side(body,sign)
    extend_side(coat,sign,True)
# Relax the irregular shoulder boundary while preserving the sleeve cuff and torso waist.
bm=bmesh.new();bm.from_mesh(coat.data)
shoulder=[v for v in bm.verts if .135<abs(v.co.x)<.34 and v.co.z>1.255]
for iteration in range(18):
    bmesh.ops.smooth_vert(bm,verts=shoulder,factor=.55,use_axis_x=True,use_axis_y=True,use_axis_z=True)
bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(coat.data);bm.free();coat.data.update()
# Fit the concealed anatomy inside the sleeve envelope without masking objects.
for vert in body.data.vertices:
    q=vert.co
    q.y*=.90
    if abs(q.x)>.165:
        sign=1 if q.x>0 else -1
        axis=Vector((sign*.64,0,-.768)).normalized();origin=Vector((sign*.195,0,1.395))
        t=max(0,(q-origin).dot(axis));center=origin+axis*t
        amount=.18*min(1,(abs(q.x)-.165)/.06)
        vert.co=q.lerp(center,amount)
body.data.update()
body.name='Torso_ConnectedArms_Cage';coat.name='OuterRobe_ConnectedSleeves'
body['pending']='Wrist attachment and hand topology; shoulder deformation tests not performed.'
coat['pending']='Cloth pattern refinement and arm-motion collision tests not performed.'

def mesh(name,verts,faces,mat,thick=.001):
    me=bpy.data.meshes.new(name+'_Cage');me.from_pydata(verts,[],faces);me.update()
    o=bpy.data.objects.new(name,me);col.objects.link(o);me.materials.append(mat)
    for p in me.polygons:p.use_smooth=True
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free()
    mod=o.modifiers.new('EditableSurface','SUBSURF');mod.levels=1
    mod=o.modifiers.new('ClothThickness','SOLIDIFY');mod.thickness=thick;mod.offset=-1
    return o

def tube(name,sign,start,end,r0,r1,mat,fold=False):
    verts=[];faces=[];direction=Vector((sign*.64,0,-.768)).normalized()
    u=Vector((0,-1,0));v=direction.cross(u).normalized();base=Vector((sign*.195,0,1.395))
    rows=24;n=48
    for j in range(rows+1):
        t=j/rows;dist=start+(end-start)*t;r=r0+(r1-r0)*t
        for i in range(n):
            a=i/n*math.tau
            ripple=.0013*math.sin(t*math.pi*9+2*a) if fold else 0
            verts.append(base+direction*dist+u*(math.cos(a)*(r*.90+ripple))+v*(math.sin(a)*(r+ripple)))
    for j in range(rows):
        for i in range(n):faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    return mesh(name,verts,faces,mat)

ivory=bpy.data.materials['M_IvoryBinding_Study'];dark=bpy.data.materials['M_InnerCharcoal_Study'];tan=bpy.data.materials['M_TanSash_Study']
for sign,suffix in [(-1,'R'),(1,'L')]:
    tube('InnerSleeve_'+suffix,sign,.265,.365,.061,.047,ivory,True)
    tube('ForearmWrap_'+suffix,sign,.345,.495,.047,.030,dark,True)
    tube('WristBinding_'+suffix,sign,.488,.510,.031,.027,ivory)
    direction=Vector((sign*.64,0,-.768)).normalized();base=Vector((sign*.195,0,1.395))
    u=Vector((0,-1,0));v=direction.cross(u).normalized()
    verts=[];faces=[];n=220
    for j in range(n+1):
        t=j/n;dist=.355+.124*t;a=math.tau*3*t
        r=.047-.014*t+.0035
        for k in [-1,1]:
            verts.append(base+direction*(dist+k*.0024)+u*(math.cos(a)*r*.90)+v*(math.sin(a)*r))
    for j in range(n):a=j*2;faces.append((a,a+1,a+3,a+2))
    mesh('WrapStrap_'+suffix,verts,faces,tan,.0008)

# Neutral clay remains an anatomy study, not final skin shading.
for name in ['front','side','rear','three-quarter']:
    camera=bpy.data.objects['Camera_'+name];camera.data.ortho_scale=1.32
    target=Vector((0,0,1.24))
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.resolution_x=1400;scene.render.resolution_y=1050
scene.camera=bpy.data.objects['Camera_three-quarter']
scene['stage']='02 connected arms and sleeves; local proportion study, not game ready'
scene['next_stage']='Hands, lower garment and legs after staged visual review; face remains last.'
scene['reference_approval']='User-approved male five-view and detail sheets; no PR.'
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Male_Stage02_ArmsAndSleeves.blend'))
for name in ['front','side','rear','three-quarter']:
    scene.camera=bpy.data.objects['Camera_'+name]
    scene.render.filepath=str(OUT/('upperbody-'+name+'.png'))
    bpy.ops.render.render(write_still=True)
report={'stage':'02 upper body; not final character','blender':bpy.app.version_string,'objects':[],'unverified':['shoulder deformation','cloth collisions during movement','final UV','rig','Unity']}
for o in bpy.data.objects:
    if o.type=='MESH':report['objects'].append({'name':o.name,'verts':len(o.data.vertices),'tris':sum(len(p.vertices)-2 for p in o.data.polygons)})
(OUT/'build-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('@@STAGE02_DONE@@')
