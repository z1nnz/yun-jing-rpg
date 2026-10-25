"""Read-only inventory of the user-owned Tree Companion source Blender file."""
import json
from collections import Counter
from pathlib import Path

import bpy

meshes=[]
for ob in bpy.data.objects:
    if ob.type!='MESH':
        continue
    meshes.append({
        'name':ob.name,
        'verts':len(ob.data.vertices),
        'faces':len(ob.data.polygons),
        'collections':[c.name for c in ob.users_collection],
        'dimensions':[round(x,3) for x in ob.dimensions],
        'hidden_render':ob.hide_render,
    })
summary={
    'file':str(Path(bpy.data.filepath)),
    'objects':len(bpy.data.objects),
    'mesh_count':len(meshes),
    'collections':[c.name for c in bpy.data.collections],
    'image_count':len(bpy.data.images),
    'materials':len(bpy.data.materials),
    'total_faces':sum(m['faces'] for m in meshes),
    'mesh_examples':sorted(meshes,key=lambda m:-m['faces'])[:25],
    'names_matching_tree':[m for m in meshes if any(t in m['name'].lower() for t in ('樹','tree','trunk','leaf','crown'))][:80],
    'stage_groups':dict(Counter(m['name'].split('_')[0] for m in meshes)),
    'stage_four_names':[m['name'] for m in meshes if '階段_04' in m['name'] or '成樹' in m['name']][:80],
    'nonmesh_examples':[(o.name,o.type) for o in bpy.data.objects if o.type!='MESH'][:100],
    'stage_parent_counts':{o.name:len(o.children_recursive) for o in bpy.data.objects if o.name.startswith('生長階段_')},
    'collection_stats':{c.name:dict(Counter(o.type for o in c.objects)) for c in bpy.data.collections},
}
print('@@INVENTORY@@'+json.dumps(summary,ensure_ascii=False))
