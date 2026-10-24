"""Refine Claude commit 70d3fa4 without modifying its source snapshot.
Run Blender --background --threads 8 --python-exit-code 1 --python this_file.
Optional arguments after --: paifang, layout, previews. Outputs are versioned.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view
BATCH=Path(__file__).resolve().parents[1]
ROOT=BATCH.parents[2]
SRC=BATCH/'SourceSnapshot'
sys.path.insert(0,str(Path(__file__).resolve().parent))
import style12
VIEWS=[('01_front',(0,-1,.15)),('02_right',(1,0,.15)),('03_rear',(0,1,.15)),('04_left',(-1,0,.15)),('05_front_right',(1,-1,.65)),('06_rear_right',(1,1,.65)),('07_rear_left',(-1,1,.65)),('08_front_left',(-1,-1,.65)),('09_top',(0,0,1)),('10_high_front',(0,-1,1.5))]

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')

def bounds(objects):
    dg=bpy.context.evaluated_depsgraph_get()
    pts=[e.matrix_world@v.co for o in objects if o.type=='MESH' for e in [o.evaluated_get(dg)] for v in e.data.vertices]
    return Vector([min(p[i] for p in pts) for i in range(3)]),Vector([max(p[i] for p in pts) for i in range(3)])

def pack_refs():
    for im in bpy.data.images:
        if im.source!='FILE': continue
        candidates=list((SRC/'ArtReferences').glob('*/'+Path(im.filepath).name))
        if not im.packed_file and candidates:
            folder=Path(im.filepath).parent.name
            p=SRC/'ArtReferences'/folder/Path(im.filepath).name
            if p.exists(): im.filepath=str(p); im.reload(); im.pack()
    for c in bpy.data.collections:
        if c.name.startswith('80_Concept'): c.hide_render=True

def settings():
    sc=bpy.context.scene
    bpy.context.preferences.filepaths.save_version=0
    sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=16;sc.cycles.use_denoising=True
    sc.render.threads_mode='FIXED';sc.render.threads=8
    sc.render.resolution_x=sc.render.resolution_y=1024;sc.render.resolution_percentage=100
    sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
    return sc

def export_save(aid,ver,objects):
    out=ROOT/'Models'/aid/ver;out.mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects: o.hide_set(False);o.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(out/f'{aid}_{ver}.fbx'),use_selection=True,object_types={'MESH','EMPTY'},add_leaf_bones=False,axis_forward='-Z',axis_up='Y',apply_unit_scale=True,bake_anim=False)
    pack_refs()
    bpy.ops.wm.save_as_mainfile(filepath=str(out/f'{aid}_{ver}.blend'))
    return out

def render_views(aid,ver,meshes):
    sc=settings(); cam=sc.camera
    lo,hi=bounds(meshes);centre=(lo+hi)/2
    cam.data.type='ORTHO';cam.data.ortho_scale=(hi-lo).length*1.1;cam.data.clip_end=2000
    folder=ROOT/'ArtLibrary/Turnarounds'/f'{aid}_{ver}';folder.mkdir(parents=True,exist_ok=True)
    records=[]
    dg=bpy.context.evaluated_depsgraph_get()
    corners=[e.matrix_world@Vector(v) for o in meshes for e in [o.evaluated_get(dg)] for v in e.bound_box]
    for name,d in VIEWS:
        cam.location=centre+Vector(d).normalized()*cam.data.ortho_scale*2
        cam.rotation_euler=(centre-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
        uv=[world_to_camera_view(sc,cam,p) for p in corners]
        assert all(.005<p.x<.995 and .005<p.y<.995 and p.z>0 for p in uv),(aid,name,'crop')
        sc.render.filepath=str(folder/(name+'.png'));bpy.ops.render.render(write_still=True)
        records.append({'file':name+'.png','direction':d,'camera_location':list(cam.location),'projection':'orthographic','framing_checked':True})
        print('VIEW_COMPLETE',aid,name,flush=True)
    write(folder/'views.json',{'asset':aid,'source':f'Models/{aid}/{ver}/{aid}_{ver}.blend','same_geometry':True,'views':records})

def paifang():
    bpy.ops.wm.open_mainfile(filepath=str(SRC/'Models/TownPaifang/v001/TownPaifang_v001.blend'))
    pack_refs();sc=settings()
    objects=list(bpy.data.collections['01_Editable_Asset'].objects)
    meshes=[o for o in objects if o.type=='MESH']
    before=bounds([o for o in meshes if o.name.startswith('Paifang_Drum_Base')])
    for o in meshes:
        mw=o.matrix_world.copy(); inv=mw.inverted(); cx=(bounds([o])[0].x+bounds([o])[1].x)/2
        o.data=o.data.copy()
        for v in o.data.vertices:
            p=mw@v.co
            if o.name.startswith('Paifang_Centre_Roof'): p.x*=5.7/3.9
            elif o.name.startswith('Paifang_Centre_Lintel_Low'): p.x*=4.4/2.6
            elif o.name.startswith('Paifang_Centre_Lintel'): p.x*=4.8/3.0
            elif o.name.startswith('Paifang_Plaque'): pass
            elif o.name.startswith('Paifang_Dougong_Bracket') and abs(cx)<1.3: p.x+=cx*(2.2/1.3-1)
            else: p.x+=.9 if cx>0 else -.9
            v.co=inv@p
        o.data.update()
    bpy.context.view_layer.update();lo,hi=bounds(meshes)
    root=next(o for o in objects if o.type=='EMPTY' and o.name.startswith('TownPaifang_ROOT'))
    root['revision']='v002: 3.60 m clear at central drum bases; 3.0 m street fits between supports'
    sc.camera.data.ortho_scale=(hi-lo).length*1.1
    sc.camera.location=(lo+hi)/2+Vector((1,-1,.65)).normalized()*25
    sc.camera.rotation_euler=((lo+hi)/2-sc.camera.location).to_track_quat('-Z','Y').to_euler()
    style12.apply();style12.studio(meshes,bounds)
    out=export_save('TownPaifang','v002',objects)
    info=json.loads((SRC/'Models/TownPaifang/v001/model_info.json').read_text())
    info.update(version='v002',style_reference='SectCore04',geometry_changed=True,dimensions_m=list(hi-lo),source_commit='70d3fa4d261bd9bbd7cc0cd7180ca08c6a7ba7cc',source_model='SourceSnapshot/Models/TownPaifang/v001/TownPaifang_v001.blend',clear_width_at_bases_m=3.6,centre_column_spacing_m=4.4,description='Expanded centre opening with unchanged column diameters and translated side bays; centre roof and lintels extended to match.',size_note='Central support spacing 4.4 m; clear drum-base opening 3.6 m.',concept_references='ArtLibrary/ExpansionBatches/TownRefinement12/SourceSnapshot/ArtReferences/TownPaifang_10Views',modeling_method='Revision of Claude v001 using its ten prior concept references; all ten packed in blend. Ten new renders use the revised geometry.')
    write(out/'model_info.json',info)
    render_views('TownPaifang','v002',meshes)

def remove_objects(objects):
    for o in list(objects): bpy.data.objects.remove(o,do_unlink=True)

def mat(name,rgb):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True
    m.diffuse_color=(*rgb,1);bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*rgb,1);bs.inputs['Roughness'].default_value=.83
    return m

def box(name,lo,hi,coll,material,bevel=0):
    lo,hi=Vector(lo),Vector(hi)
    bpy.ops.mesh.primitive_cube_add(size=1,location=(lo+hi)/2)
    o=bpy.context.object;o.name=name;o.dimensions=hi-lo;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for c in list(o.users_collection):c.objects.unlink(o)
    coll.objects.link(o);o.data.materials.append(material)
    if bevel:
        mod=o.modifiers.new('Soft_edges','BEVEL');mod.width=bevel;mod.segments=2
    return o

def patch(name,rect,coll):
    x0,y0,x1,y1=rect
    stone=mat('TR12_BlueGrey_Stone',(.29,.34,.34));grout=mat('TR12_Recessed_Grout',(.19,.23,.23))
    box(name+'_Bed',(x0,y0,1.12),(x1,y1,1.305),coll,grout)
    nx=max(1,math.ceil((x1-x0)/.7));ny=max(1,math.ceil((y1-y0)/.7))
    for i in range(nx):
        for j in range(ny):
            ax=x0+(x1-x0)*i/nx;bx=x0+(x1-x0)*(i+1)/nx
            ay=y0+(y1-y0)*j/ny;by=y0+(y1-y0)*(j+1)/ny
            box(name+'_Paver',(ax+.003,ay+.003,1.30),(bx-.003,by-.003,1.32),coll,stone,.002)

def layout():
    bpy.ops.wm.open_mainfile(filepath=str(SRC/'Models/TownLayout/v003/TownLayout_v003.blend'))
    pack_refs();sc=settings();report={}
    old=bpy.data.collections['TownPaifang_01']; remove_objects(old.objects)
    with bpy.data.libraries.load(str(ROOT/'Models/TownPaifang/v002/TownPaifang_v002.blend'),link=False) as (a,b):b.collections=['01_Editable_Asset']
    c=b.collections[0]
    for o in list(c.objects):old.objects.link(o)
    bpy.data.collections.remove(c)
    root=next(o for o in old.objects if o.name.startswith('TownPaifang_ROOT'));root.name='TownPaifang_v002_01_ROOT';root.location=(0,26.7,1.12)
    bpy.context.view_layer.update()
    for aid in ('TownRoadCrossroad','TownRoadTJunction','PondEdge','NoticeBoard','BambooBasket','WoodenCrate'):
        target=bpy.data.collections[aid+'_01']
        oldroot=next(o for o in target.objects if o.type=='EMPTY');transform=oldroot.matrix_world.copy()
        remove_objects(target.objects)
        with bpy.data.libraries.load(str(ROOT/'Models'/aid/'v002'/f'{aid}_v002.blend'),link=False) as (a,b):b.collections=['01_Editable_Asset']
        loaded=b.collections[0]
        for o in list(loaded.objects):target.objects.link(o)
        bpy.data.collections.remove(loaded)
        newroot=next(o for o in target.objects if o.type=='EMPTY');newroot.matrix_world=transform
    bpy.context.view_layer.update()
    # Align corner elbows to true fence corners before moving the garden east.
    corners=[('BambooFenceCorner_01',(15,25)),('BambooFenceCorner_02',(7,25)),('BambooFenceCorner_03',(7,33)),('BambooFenceCorner_04',(15,33))]
    for name,xy in corners:
        c=bpy.data.collections[name];posts=[o for o in c.objects if o.name.startswith('Corner_Post') and not o.name.startswith('Corner_Post_Cap')]
        elbow=posts[1];p=elbow.matrix_world.translation;root=next(o for o in c.objects if o.type=='EMPTY')
        root.location+=Vector((xy[0]-p.x,xy[1]-p.y,0))
    for c in bpy.data.collections:
        if c.name.startswith('BambooFence_'):
            root=next(o for o in c.objects if o.type=='EMPTY');post=next(o for o in c.objects if o.name.startswith('Fence_Post'))
            p=post.matrix_world.translation
            if abs(root.rotation_euler.z)<.1:root.location.y-=p.y-root.location.y
            else:root.location.x-=p.x-root.location.x
    for c in bpy.data.collections:
        if c.name.startswith(('BambooFence_','BambooFenceCorner_','FenceGate_','PondEdge_')):
            root=next(o for o in c.objects if o.type=='EMPTY');root.location.x+=3
    bpy.context.view_layer.update()
    # Keep a single post and cap at each shared joint. Gate pillars replace adjoining fence end posts.
    gate=bpy.data.collections['FenceGate_01'];gatepts=[o.matrix_world.translation.copy() for o in gate.objects if o.name.startswith('Gate_Post') and not o.name.startswith('Gate_Post_Base')]
    fence=[o for c in bpy.data.collections if c.name.startswith(('BambooFence_','BambooFenceCorner_')) for o in c.objects if o.type=='MESH']
    removed=[]
    for prefixes in [('Fence_Post','Corner_Post'),('Fence_Post_Cap','Corner_Post_Cap')]:
        candidates=[o for c in bpy.data.collections if c.name.startswith(('BambooFence_','BambooFenceCorner_')) for o in c.objects if o.type=='MESH' and o.name.startswith(prefixes) and ('Cap' in o.name)==('Cap' in prefixes[0])]
        kept=[]
        for o in sorted(candidates,key=lambda o:bounds([o])[1].z,reverse=True):
            p=o.matrix_world.translation
            if any((Vector((p.x,p.y))-Vector((q.x,q.y))).length<.065 for q in gatepts+kept):removed.append(o.name);bpy.data.objects.remove(o,do_unlink=True)
            else:kept.append(p.copy())
    report['duplicate_or_gate_adjacent_fence_parts_removed']=removed
    # Exact duplicate stone balustrade posts/caps at adjacent two-metre modules.
    seen=set();railremoved=[]
    for c in list(bpy.data.collections):
        if c.name.startswith('StoneRailing_'):
            for o in list(c.objects):
                if o.name.startswith(('Stone_Rail_Post','Stone_Rail_Lotus_Cap')):
                    key=(o.name.split('.')[0],tuple(round(v,4) for v in o.matrix_world.translation))
                    if key in seen:railremoved.append(o.name);bpy.data.objects.remove(o,do_unlink=True)
                    else:seen.add(key)
    report['duplicate_stone_rail_parts_removed']=railremoved
    # Open existing gate leaves inward; hinges stay fixed and every leaf part retains world geometry.
    for o in list(gate.objects):
        if o.name.startswith(('Gate_Leaf','Gate_Latch')):
            upper=o.matrix_world.translation.y>=29
            hinge=Vector((9.96,29.96 if upper else 28.04,1.12))
            transform=Matrix.Translation(hinge)@Matrix.Rotation(math.pi/2 if upper else -math.pi/2,4,'Z')@Matrix.Translation(-hinge)
            o.matrix_world=transform@o.matrix_world
    bpy.context.view_layer.update()
    latch=next((o for o in gate.objects if o.name.startswith('Gate_Latch')),None)
    if latch:
        pickets=[o for o in gate.objects if o.name.startswith('Gate_Leaf_Bamboo') and o.matrix_world.translation.y>29.3]
        end=max(pickets,key=lambda o:o.matrix_world.translation.x).matrix_world.translation
        mw=latch.matrix_world.copy();mw.translation.x=end.x;mw.translation.y=end.y-.03;latch.matrix_world=mw
    bpy.context.view_layer.update()
    coll=bpy.data.collections.new('13_Connected_Forecourts_v004');sc.collection.children.link(coll)
    patch('Inn_Forecourt',(-10.0,19.2,-9.0,23.7),coll)
    patch('Well_Approach',(9,19.95,10.5,21.45),coll)
    # Ramp gently from street to existing gate threshold, ending clear of pond stones.
    patch('Garden_Approach',(1.5,28.4,9.4,29.6),coll)
    patch('Garden_Landing',(9.4,28.4,11.0,29.6),coll)
    # Lower garden paving from street 1.32 to grass 1.12 in the final 1.6 m (12.5%).
    for o in coll.objects:
        if o.name.startswith('Garden_Landing'):
            for v in o.data.vertices:
                p=o.matrix_world@v.co
                if p.z>1.299:p.z-=.2*max(0,min(1,(p.x-9.4)/1.6))
                else:p.z=min(p.z,1.10)
                v.co=o.matrix_world.inverted()@p
    # Split the two east kerb pieces where the garden path crosses, preserving remaining curb.
    cut=[]
    for o in list(bpy.data.collections['MountainStonePath_02'].objects):
        if not o.name.startswith('Path_Kerb'):continue
        lo,hi=bounds([o])
        if lo.x>0 and lo.y<29.6 and hi.y>28.4:
            material=o.data.materials[0];cut.append(o.name)
            if lo.y<28.4:box('Garden_Curb_Return_S',lo,(hi.x,28.4,hi.z),coll,material,.005)
            if hi.y>29.6:box('Garden_Curb_Return_N',(lo.x,29.6,lo.z),hi,coll,material,.005)
            bpy.data.objects.remove(o,do_unlink=True)
    report['curb_opening_parts']=cut
    for name,loc in [('Inn_Entry_Feet',(-10,22.2,1.32)),('Garden_Gate_Feet',(9.8,29,1.27)),('Well_Square_Centre',(9.8,20.7,1.32))]:
        if name in bpy.data.objects:bpy.data.objects[name].location=loc
    # Remove the misleading north-exit marker at the closed side of the T junction.
    marker=bpy.data.objects.get('Town_Exit_North_v003')
    if marker:marker.name='North_T_Junction_Closed_Edge';marker['note']='Closed north edge; exits are west/east lane ends.'
    export=[o for o in sc.objects if o.type in ('MESH','EMPTY') and not any(c.name.startswith(('80_','90_')) for c in o.users_collection)]
    meshes=[o for o in export if o.type=='MESH']
    sc.camera.location=(39,-37,39);target=Vector((-2,13,3));sc.camera.rotation_euler=(target-sc.camera.location).to_track_quat('-Z','Y').to_euler();sc.camera.data.type='PERSP';sc.camera.data.lens=33
    report['style_materials']=style12.apply();style12.studio([o for o in meshes if not o.name.startswith('Terrain_Display')],bounds)
    for light in sc.objects:
        if light.type=='LIGHT':light.data.energy*=.35
    sc.view_settings.exposure=-.25
    report['scene_light_power_scale']=.35
    report['scene_exposure_ev']=-.25
    out=export_save('TownLayout','v004',export)
    report.update(source_commit='70d3fa4d261bd9bbd7cc0cd7180ca08c6a7ba7cc',source_scene='SourceSnapshot/Models/TownLayout/v003/TownLayout_v003.blend',version='v004',updated_asset='TownPaifang/v002',garden_translation_m=[3,0,0],garden_gate_leaves_open_degrees=90,garden_path_width_m=1.2,garden_ramp_grade=.125,mesh_objects=len(meshes),note='Prototype geometry and appearance; no collision, navigation, Unreal or full-town accessibility certification.')
    write(out/'layout_info.json',report)
    previews()
    render_views('TownLayout','v004',[o for o in meshes if not o.name.startswith('Terrain_Display')])

def repair_road_kerbs(aid,objects):
    import bmesh
    coll=bpy.data.collections['01_Editable_Asset']
    root=next(o for o in objects if o.type=='EMPTY' and o.name.startswith(aid+'_ROOT'))
    old=[o for o in objects if o.name.startswith('Road_Kerb')]
    material=old[0].data.materials[0]
    remove_objects(old)
    def prism(name,xy):
        n=len(xy);y_shift=-.005 if aid=='TownRoadTJunction' else 0
        verts=[(x,y+y_shift,z) for z in (0,.32) for x,y in xy]
        faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces)
        bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free()
        o=bpy.data.objects.new(name,me);coll.objects.link(o);o.parent=root;me.materials.append(material)
        mod=o.modifiers.new('Soft_edges','BEVEL');mod.width=.008;mod.segments=2
        o.modifiers.new('Weighted_normals','WEIGHTED_NORMAL')
    outline=[(1.5,1.5),(3,1.5),(3,1.75),(1.75,1.75),(1.75,3),(1.5,3)]
    for sx in [-1,1]:
        for sy in ([-1,1] if aid=='TownRoadCrossroad' else [1]):
            prism('Continuous_Corner_Kerb',[(sx*x,sy*y) for x,y in outline])
    if aid=='TownRoadTJunction':prism('Continuous_Straight_Kerb',[(-3,-1.75),(3,-1.75),(3,-1.5),(-3,-1.5)])
    bpy.context.view_layer.update()
    return list(coll.objects)

def style_assets():
    source=json.loads((SRC/'Models/TownLayout/v003/layout_info.json').read_text())
    ids=sorted(set(p['asset'] for p in source['placements'])-{'TownPaifang','MountainStonePath'})
    for aid in ids:
        out=ROOT/'Models'/aid/'v002'
        if (ROOT/'ArtLibrary/Turnarounds'/f'{aid}_v002'/'views.json').exists() and f'rebuild:{aid}' not in sys.argv:
            print('ALREADY_RENDERED',aid,flush=True);continue
        bpy.ops.wm.open_mainfile(filepath=str(SRC/'Models'/aid/'v001'/f'{aid}_v001.blend'))
        sc=settings();pack_refs();changed=style12.apply()
        objects=list(bpy.data.collections['01_Editable_Asset'].objects)
        if aid in ('TownRoadCrossroad','TownRoadTJunction'):objects=repair_road_kerbs(aid,objects)
        if aid=='PondEdge':
            water=next(o for o in objects if o.name.startswith('Pond_Water'))
            centre=(bounds([water])[0]+bounds([water])[1])/2
            pads=sorted([o for o in objects if o.name.startswith('Lotus_Pad')],key=lambda o:o.name)
            for o,(x,y) in zip(pads,[(-.8,.35),(-.55,-.35),(.1,.6),(.5,.2),(.9,-.55)]):
                c=(bounds([o])[0]+bounds([o])[1])/2
                o.location+=Vector((centre.x+x-c.x,centre.y+y-c.y,0))
            bpy.context.view_layer.update()
        if aid=='NoticeBoard':
            for o in objects:
                if o.name.startswith(('Notice_Paper_','Notice_Pin_')):
                    index=int(o.name.rsplit('_',1)[-1].split('.')[0]);o.location.y-=index*.002
        if aid=='BambooBasket':
            base=next(o for o in objects if o.name.startswith('Basket_Base'));c=(bounds([base])[0]+bounds([base])[1])/2
            bundles=sorted([o for o in objects if o.name.startswith('Basket_Herb_Bundle')],key=lambda o:o.name)
            for o,(x,y) in zip(bundles,[(-.11,-.07),(.11,-.07),(0,.125)]):
                p=(bounds([o])[0]+bounds([o])[1])/2;o.location+=Vector((c.x+x-p.x,c.y+y-p.y,0))
        if aid=='WoodenCrate':
            for o in objects:
                if not o.name.startswith('Crate_Frame'):continue
                lo,hi=bounds([o]);c=(lo+hi)/2;d=hi-lo;mw=o.matrix_world.copy();inv=mw.inverted()
                scale=Vector([1-.004/v for v in d])
                for v in o.data.vertices:v.co=inv@(c+(mw@v.co-c)*scale)
                o.data.update()
        bpy.context.view_layer.update()
        meshes=[o for o in objects if o.type=='MESH']
        style12.studio(meshes,bounds)
        out=export_save(aid,'v002',objects)
        info=json.loads((SRC/'Models'/aid/'v001'/'model_info.json').read_text())
        info.update(version='v002',style_reference='SectCore04',style_materials=changed,source_commit='70d3fa4d261bd9bbd7cc0cd7180ca08c6a7ba7cc',geometry_changed=aid in ('TownRoadCrossroad','TownRoadTJunction','PondEdge','NoticeBoard','BambooBasket','WoodenCrate'),dimensions_m=list(bounds(meshes)[1]-bounds(meshes)[0]),mesh_objects=len(meshes),concept_references=f'ArtLibrary/ExpansionBatches/TownRefinement12/SourceSnapshot/ArtReferences/{aid}_10Views',modeling_method='Claude source geometry retained; semantic materials and studio matched to SectCore04. Prior ten concept images packed; ten new renders of this revision.')
        if aid in ('TownRoadCrossroad','TownRoadTJunction'):
            info.update(modeling_method='Claude road paving retained; rebuilt continuous kerbs plus SectCore04 materials. Ten original references packed; ten new renders.',kerb_height_m=.32,geometry_revision='Replace intersecting corner bars with closed L-shaped kerbs; match adjacent straight-path kerb height. Road surface/connectors retained.')
        if aid=='PondEdge':info.update(geometry_revision='Separate five coplanar lotus pads to eliminate surface overlap and black render artifacts.',modeling_method='Claude pond retained with separated lotus pads and SectCore04 materials; ten references packed and ten revised renders.')
        if aid in ('NoticeBoard','BambooBasket','WoodenCrate'):info.update(geometry_revision='Remove coplanar overlap: stagger paper layers, separate herb bundles, or inset crate frames by 2 mm per face.',modeling_method='Claude geometry corrected locally to remove coplanar artifacts; SectCore04 materials and ten new renders with original ten references packed.')
        write(out/'model_info.json',info)
        render_views(aid,'v002',meshes)
        print('STYLE_ASSET_COMPLETE',aid,flush=True)

def previews():
    sc=settings();cam=sc.camera;out=ROOT/'Models/TownLayout/v004'
    sc.render.resolution_x=1600;sc.render.resolution_y=1100
    shots=[('01_town_overview.png','PERSP',(44,-42,45),(-2,13,2),31),('02_town_top_plan.png','ORTHO',(-2,13,90),(-2,13,0),85),('03_north_street_archway.png','PERSP',(2.5,13,3.2),(0,30,3.0),28),('04_garden_connection.png','PERSP',(4,20,7),(11.5,29,1.4),35)]
    for name,kind,loc,target,lens in shots:
        cam.data.type=kind
        if kind=='ORTHO':cam.data.ortho_scale=lens
        else:cam.data.lens=lens
        cam.data.clip_end=2000;cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
        sc.render.filepath=str(out/name);bpy.ops.render.render(write_still=True);print('PREVIEW',name,flush=True)

if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['paifang','layout']
    if 'paifang' in args:paifang()
    if 'style-assets' in args:style_assets()
    if 'layout' in args:layout()
    if 'previews' in args:
        bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Models/TownLayout/v004/TownLayout_v004.blend'));previews()
