"""Convert Eli-0731's reviewed GLB-only deliveries (C01-C08 return corner, Q01-Q04 village signs)
to Unity FBX without editing meshes.

Run from the repository root with Blender 5.2:
  blender -b --factory-startup --python-exit-code 1 -P tools/art/import_qingxi_return_c_to_unity.py
The original GLBs, three-views and author records stay in art/exports.
"""

import json
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[2]
AUTHOR = "Eli-0731 / Codex"
SETS = [
    (ROOT / "art/exports/qingxi-return-c", ROOT / "apps/game/Assets/YunJing/Models/VillageReturnC", [f"C0{i}" for i in range(1, 9)]),
    (ROOT / "art/exports/qingxi-village-signs-v1", ROOT / "apps/game/Assets/YunJing/Models/VillageSignsC", [f"Q0{i}" for i in range(1, 5)]),
    # PR #47: the assembled 3 × 5 m water-council corner (table, buckets, damp boards, flags) for Plaza_WaterCouncil.
    (ROOT / "art/exports/qingxi-water-report-c/variants", ROOT / "apps/game/Assets/YunJing/Models/VillageReportC", ["VillageCorner-a"]),
]


def mesh_stats():
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in meshes)
    return len(meshes), tris


def bounds():
    import mathutils
    lo = mathutils.Vector((1e9, 1e9, 1e9)); hi = -lo
    for o in bpy.context.scene.objects:
        if o.type != "MESH":
            continue
        for corner in o.bound_box:
            w = o.matrix_world @ mathutils.Vector(corner)
            lo = mathutils.Vector(map(min, lo, w)); hi = mathutils.Vector(map(max, hi, w))
    return [round(v, 3) for v in hi - lo]


def convert(SOURCE, DEST, asset_id):
    source = SOURCE / f"{asset_id}.glb"
    if source.read_bytes()[:4] != b"glTF":
        raise RuntimeError(f"Missing full Git LFS source: {source}")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))
    imported, size = mesh_stats(), bounds()
    if imported[0] == 0:
        raise RuntimeError(f"No mesh in {source}")
    # Unity does not pick up FBX-embedded images here, so write the GLB's packed textures beside the FBX
    # (prefixed with the asset id) and reference them by relative path.
    textures = DEST / "Textures"
    textures.mkdir(exist_ok=True)
    for image in [i for i in bpy.data.images if i.size[0] > 0]:
        name = f"{asset_id}_{image.name}.png"
        image.filepath_raw = str(textures / name)
        image.file_format = "PNG"
        image.save()
        image.name = name
    target = DEST / f"{asset_id}.fbx"
    bpy.ops.export_scene.fbx(
        filepath=str(target), use_selection=False, object_types={"MESH", "EMPTY"},
        axis_forward="-Z", axis_up="Y", apply_scale_options="FBX_SCALE_ALL",
        bake_space_transform=True, use_mesh_modifiers=True, mesh_smooth_type="FACE",
        add_leaf_bones=False, bake_anim=False, path_mode="RELATIVE", embed_textures=False,
    )
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(target))
    returned, back = mesh_stats(), bounds()
    if imported != returned or target.stat().st_size < 1000 or max(abs(a - b) for a, b in zip(sorted(size), sorted(back))) > 0.01:
        raise RuntimeError(f"Roundtrip mismatch for {asset_id}: {imported} {size} -> {returned} {back}")
    return {"id": asset_id, "originalAuthor": AUTHOR, "source": str(source.relative_to(ROOT)).replace("\\", "/"),
            "fbx": str(target.relative_to(ROOT)).replace("\\", "/"), "meshes": imported[0], "triangles": imported[1],
            "size_m": size, "bytes": target.stat().st_size, "roundtrip": True}


for source_dir, dest_dir, ids in SETS:
    dest_dir.mkdir(parents=True, exist_ok=True)
    result = [convert(source_dir, dest_dir, i) for i in ids]
    (dest_dir / "conversion-report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("QINGXI_RETURN_C_FBX_OK", dest_dir.name, json.dumps(result, ensure_ascii=False))
