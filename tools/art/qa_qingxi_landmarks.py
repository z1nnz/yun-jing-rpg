"""Run: blender -b art/source/<asset>.blend -P tools/art/qa_qingxi_landmarks.py -- bridge|tree"""
import json, os, sys
from pathlib import Path

import bpy

asset = sys.argv[-1]
collection_name = {"bridge": "ASSET_TimberBridge_low", "tree": "ASSET_SacredTree_low"}[asset]
skill = Path(os.environ.get("CODEX_HOME", str(Path.home()/".codex"))) / "skills" / "blender-asset-qa" / "scripts"
if not (skill / "qa_check.py").exists():
    raise FileNotFoundError("Install blender-asset-qa skill or set CODEX_HOME: " + str(skill))
sys.path.insert(0, str(skill))
import qa_check

objects = [o.name for o in bpy.data.collections[collection_name].objects]
report = qa_check.run(objects=objects, profile="game", tol=.02)
summary={"asset":asset,"pass":report["pass"],"source_meshes":len(objects),
    "error_count":len(report["errors"]),"errors":report["errors"],
    "warning_count":len(report["warnings"]),"warnings":report["warnings"],
    "ground_z":report["ground_z"]}
destination=Path(__file__).resolve().parents[2] / "art" / "exports" / "qingxi-world-v1" / (asset+"-qa-report.json")
destination.write_text(json.dumps(summary,indent=2),encoding="utf-8")
print("@@QA@@"+json.dumps(summary))
