import bpy

print("STUDY_LIBRARIES", [library.filepath for library in bpy.data.libraries])
print("STUDY_IMAGES", [image.filepath for image in bpy.data.images if image.source == "FILE"])

for obj in bpy.data.objects:
    if obj.type != "MESH":
        continue
    local = [v.co for v in obj.data.vertices]
    world = [obj.matrix_world @ v.co for v in obj.data.vertices]
    print("STUDY", obj.name, "parent", obj.parent.name if obj.parent else None,
          "location", tuple(round(v, 4) for v in obj.location),
          "world x", (round(min(v.x for v in world), 4), round(max(v.x for v in world), 4)),
          "world y", (round(min(v.y for v in world), 4), round(max(v.y for v in world), 4)),
          "world z", (round(min(v.z for v in world), 4), round(max(v.z for v in world), 4)),
          "materials", [m.name for m in obj.data.materials],
          "faces", {i: sum(p.material_index == i for p in obj.data.polygons)
                    for i in set(p.material_index for p in obj.data.polygons)})
