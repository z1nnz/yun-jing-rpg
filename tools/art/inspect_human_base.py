import bpy
from mathutils import Vector

for obj in bpy.data.objects:
    if obj.type != "MESH":
        continue
    if not (obj.name.startswith("GEO-head_") or obj.name == "Head - Generic Topology"):
        continue
    verts = obj.data.vertices
    if not verts:
        continue
    coords = [v.co for v in verts]
    lo = [min(c[i] for c in coords) for i in range(3)]
    hi = [max(c[i] for c in coords) for i in range(3)]
    print("BASE", obj.name, "verts", len(verts), "polys", len(obj.data.polygons),
          "bounds", tuple(round(x, 4) for x in lo), tuple(round(x, 4) for x in hi),
          "uv", len(obj.data.uv_layers), "hidden", obj.hide_viewport,
          "location", tuple(round(x, 4) for x in obj.location),
          "scale", tuple(round(x, 4) for x in obj.scale),
          "mods", [(m.name, m.type) for m in obj.modifiers],
          "materials", [(m.name if m else None) for m in obj.data.materials],
          "material_faces", {i: sum(p.material_index == i for p in obj.data.polygons)
                             for i in set(p.material_index for p in obj.data.polygons)})
