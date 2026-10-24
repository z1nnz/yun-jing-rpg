"""Validate editable source and exported aptitude plaza without requiring Unity."""

import bpy
import hashlib
import json
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "art/source/aptitude-plaza-v1.blend"
FBX = ROOT / "apps/game/Assets/YunJing/Models/AptitudePlazaV1/aptitude-plaza-v1.fbx"
GLB = ROOT / "art/exports/aptitude-plaza-v1/aptitude-plaza-v1.glb"
REPORT = ROOT / "art/exports/aptitude-plaza-v1/report.json"
OUTPUT = ROOT / "art/exports/aptitude-plaza-v1/validation.json"

for path in (SOURCE, FBX, GLB, REPORT):
    assert path.is_file() and path.stat().st_size > 0, f"Missing model deliverable: {path}"

report = json.loads(REPORT.read_text(encoding="utf-8"))
reference = ROOT / report["reference"]["file"]
assert reference.is_file(), "Saved AI three-view is missing"
assert report["reference"]["reviewed_before_modeling"] is True
assert hashlib.sha256(reference.read_bytes()).hexdigest() == report["reference"]["sha256"]


def mesh_summary():
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    assert meshes
    triangles = 0
    points = []
    for obj in meshes:
        obj.data.calc_loop_triangles()
        triangles += len(obj.data.loop_triangles)
        points.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    minimum = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    maximum = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return {
        "mesh_objects": len(meshes),
        "triangles": triangles,
        "dimensions_m": [round(value, 4) for value in (maximum - minimum)],
        "minimum_m": [round(value, 4) for value in minimum],
        "maximum_m": [round(value, 4) for value in maximum],
    }


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
names = {obj.name for obj in bpy.context.scene.objects}
for required in ("Plaza_Base_Lower", "Plaza_Floor", "Aptitude_Crystal",
                 "Marker_East_Shaft", "Marker_West_Shaft", "Marker_North_Shaft", "Marker_South_Shaft"):
    assert required in names, f"Missing required source module: {required}"
assert "Preview-only ground" not in names, "Preview-only objects leaked into editable source"
source_summary = mesh_summary()
assert source_summary["triangles"] == report["triangles"]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(GLB))
glb_summary = mesh_summary()

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(FBX))
fbx_summary = mesh_summary()

for label, summary in (("glb", glb_summary), ("fbx", fbx_summary)):
    x, y, z = summary["dimensions_m"]
    assert 17.5 <= x <= 21.0 and 17.5 <= y <= 21.0, f"{label} scale invalid: {summary}"
    assert 3.4 <= z <= 4.2, f"{label} height invalid: {summary}"
    # Exports apply the non-destructive bevel modifiers kept in the editable
    # Blender source, so their evaluated triangle count is intentionally
    # higher than the base mesh count recorded in report.json.
    assert source_summary["triangles"] <= summary["triangles"] <= source_summary["triangles"] * 3, (
        f"{label} evaluated triangle count is outside the expected range: {summary['triangles']}"
    )

assert glb_summary["triangles"] == fbx_summary["triangles"], (
    f"Export formats disagree: GLB {glb_summary['triangles']} vs FBX {fbx_summary['triangles']}"
)
for glb_value, fbx_value in zip(glb_summary["dimensions_m"], fbx_summary["dimensions_m"]):
    assert abs(glb_value - fbx_value) <= 0.02, (
        f"Export dimensions disagree: GLB {glb_summary['dimensions_m']} vs FBX {fbx_summary['dimensions_m']}"
    )

validation = {
    "asset": "AptitudePlaza",
    "version": "v1",
    "blender": bpy.app.version_string,
    "reference_verified": True,
    "source": source_summary,
    "glb_roundtrip": glb_summary,
    "fbx_roundtrip": fbx_summary,
    "checks": {
        "required_modules": True,
        "preview_objects_excluded": True,
        "scale_preserved": True,
        "base_mesh_matches_report": True,
        "modifiers_applied_consistently": True,
        "export_dimensions_match": True,
    },
    "unity_verified": False,
}
OUTPUT.write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
print("APTITUDE_PLAZA_VALID " + json.dumps(validation, ensure_ascii=False))
