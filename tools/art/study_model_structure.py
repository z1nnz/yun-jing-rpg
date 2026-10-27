"""Print only structure statistics from a local reference model; export nothing."""

import collections
import bpy

meshes = [o for o in bpy.data.objects if o.type == "MESH"]
print("STUDY_TOTAL", len(meshes), "meshes", sum(len(o.data.polygons) for o in meshes), "faces")
print("STUDY_COLLECTIONS", [(c.name, len(c.objects)) for c in bpy.data.collections if len(c.objects) > 5][:30])
terms = ("eye", "face", "head", "hair", "brow", "lash", "body", "skirt", "dress", "cloth")
for obj in meshes:
    if len(obj.data.polygons) >= 500 and (any(term in obj.name.lower() for term in terms) or len(obj.data.polygons) >= 1000):
        print("STUDY_PART", obj.name[:80], "verts", len(obj.data.vertices),
              "faces", len(obj.data.polygons), "uv", len(obj.data.uv_layers),
              "materials", len(obj.data.materials),
              "modifiers", collections.Counter(m.type for m in obj.modifiers))
