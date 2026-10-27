"""Reimport the preview GLB and check that the three editable mesh modules survived."""

import pathlib
import bpy

root = pathlib.Path(__file__).resolve().parents[2]
source = root / "art/exports/heroine-01-face-module-v2-preview.glb"
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=str(source))
meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
names = {obj.name for obj in meshes}
required = {"SK_Heroine01_FaceStudy", "SK_Heroine01_Eyeball_L", "SK_Heroine01_Eyeball_R"}
if not required.issubset(names):
    raise RuntimeError(f"Preview GLB missing modules: {required - names}")
if any(not obj.data.uv_layers for obj in meshes):
    raise RuntimeError("Preview GLB lost a UV layer")
print("HEROINE_GLTF_ROUNDTRIP", len(meshes), "meshes", sum(len(o.data.polygons) for o in meshes), "faces")
