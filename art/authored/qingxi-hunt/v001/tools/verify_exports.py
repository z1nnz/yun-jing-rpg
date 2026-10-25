"""Fresh-process verification of saved Blender sources and FBX/GLB exports."""
import bpy, json, sys, os, math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
SKILLS=Path(os.environ.get('QINGXI_SKILLS',str(Path.home()/'.codex/skills')))
for sub in ['blender-asset-qa','blender-export-pipelines']:
    sys.path.insert(0,str(SKILLS/sub/'scripts'))
import qa_check,review_shots,export_asset
assert bpy.app.background
manifest=json.loads((ROOT/'reports/model-manifest.json').read_text())
results=[]
for asset in manifest['assets']:
    stem=asset['name']
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models'/f'{stem}.blend'))
    images=[im for im in bpy.data.images if im.source=='FILE' and im.name.startswith('T_')]
    assert images and all(Path(bpy.path.abspath(im.filepath)).is_file() for im in images)
    source={}
    for lod in asset['lods']:
        ob=bpy.data.objects[lod['name']];source[ob.name]=list(ob.dimensions)
        assert len(ob.data.polygons)==lod['triangles']
        # LOD contact sheets complement the LOD0 material and wire review.
        if not ob.name.endswith('LOD0'):
            review_shots.run(objects=[ob.name],out=str(ROOT/'previews'/f'{ob.name}_review.png'),mode='material',res=256)
    if stem=='StreamBank':source['COL_StreamBank']=list(bpy.data.objects['COL_StreamBank'].dimensions)
    for name,expected in source.items():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        path=ROOT/'models'/f'{name}.fbx'
        assert path.stat().st_size>1024
        assert bpy.ops.import_scene.fbx(filepath=str(path))=={'FINISHED'}
        objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
        assert len(objects)==1,(name,len(objects))
        ob=objects[0];bpy.context.view_layer.update()
        pts=[ob.matrix_world@Vector(c) for c in ob.bound_box]
        actual=[max(p[i] for p in pts)-min(p[i] for p in pts) for i in range(3)]
        assert all(abs(a-b)<.001 for a,b in zip(actual,expected)),(name,actual,expected)
        assert all(abs(v-1)<.0001 for v in ob.scale),(name,list(ob.scale))
        assert len(ob.data.uv_layers)>0 and len(ob.material_slots)==1
        report=qa_check.run(objects=[ob.name],profile='game',eps=.0002)
        assert report['pass'],(name,report['errors'])
        material_images=[n.image for m in ob.data.materials for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]
        assert material_images and all(Path(bpy.path.abspath(im.filepath)).is_file() for im in material_images),(name,'missing texture')
        glb=None
        if name.startswith('SM_'):
            glb=export_asset.glb_summary(str(ROOT/'models'/f'{name}.glb'))
            assert glb['meshes']==1 and glb['materials']==1 and glb['images']==1
        results.append({'file':path.name,'pass':True,'dimensions_m':actual,'scale':list(ob.scale),'qa':report,'glb':glb})
report={'status':'passed','blender':bpy.app.version_string,'fbxRoundTrips':len(results),'blendReopened':len(manifest['assets']),
        'unityTested':False,'results':results}
(ROOT/'reports/export-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('QINGXI_EXPORT_VERIFICATION_PASSED',len(results))
