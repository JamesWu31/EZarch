"""Read saved files, compare units/geometry and detect stale dependent outputs."""
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pymupdf as fitz

from .project import fingerprint, read_project, skill_root, write_json


def audit(source: Path, out: Path):
    project = read_project(source) if source.is_file() and source.suffix.lower() in {".yaml", ".yml"} else None
    root = source.parent / "outputs" if project else source
    expected_hash = fingerprint(project) if project else None
    checks = []

    def check(name, passed, detail):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    def check_bindings(data, owner):
        for binding in data.get("source_bindings", []):
            file = owner.parent / binding["file"]
            valid = file.is_file() and hashlib.sha256(file.read_bytes()).hexdigest() == binding.get("sha256")
            check("supplemental_source_version", valid, {"report": owner.name, "source": binding["file"]})

    scenes = list(root.rglob("scene.json"))
    for file in scenes:
        scene = json.loads(file.read_text(encoding="utf-8"))
        if "objects" not in scene:
            continue
        if expected_hash:
            check("model_source_version", scene["project_hash"] == expected_hash, file.name)
        expected_count = len(scene["objects"])
        expected_parts = {o["id"]: np.array([np.min(o["vertices"], 0), np.max(o["vertices"], 0)]) for o in scene["objects"]}

        def component_check(label, actual_parts, expected_parts=expected_parts):
            names_match = set(actual_parts) == set(expected_parts)
            errors = [float(np.max(np.abs(actual_parts[k] - expected_parts[k]))) for k in actual_parts if k in expected_parts]
            error = max(errors) if errors else float("inf")
            check(label, names_match and error < 1, {"components": len(actual_parts), "max_error_mm": error, "ids_match": names_match})
        for required in ["model.step", "model.glb", "model.3dm", "model.dae"]:
            check("model_export_present", (file.parent / required).is_file(), required)
        verts = np.asarray([p for obj in scene["objects"] for p in obj["vertices"]])
        target_bounds = np.array([verts.min(axis=0), verts.max(axis=0)])
        step = file.parent / "model.step"
        if step.exists():
            import cadquery as cq
            shape = cq.importers.importStep(str(step)).val()
            bb = shape.BoundingBox()
            actual = np.array([[bb.xmin, bb.ymin, bb.zmin], [bb.xmax, bb.ymax, bb.zmax]])
            error = float(np.max(np.abs(actual - target_bounds)))
            check("STEP_bounds_mm", error <= scene.get("mesh_tolerance_mm", 1) + .01, {"max_error_mm": error})
            check("STEP_valid", shape.isValid(), {"solids": len(shape.Solids())})
            expected_volume = sum(o["volume_mm3"] for o in scene["objects"])
            volume_error = abs(shape.Volume() - expected_volume) / max(expected_volume, 1)
            check("STEP_volume", volume_error < 1e-6, {"relative_error": volume_error})
        glb = file.parent / "model.glb"
        if glb.exists():
            import trimesh
            mesh = trimesh.load(glb, force="scene")
            error = float(np.max(np.abs(mesh.bounds * 1000 - target_bounds)))
            check("GLB_units_and_bounds", error < 1, {"max_error_mm": error, "units": "m"})
            check("GLB_components", len(mesh.geometry) == expected_count, {"objects": len(mesh.geometry)})
            glb_parts = {}
            for name in mesh.graph.nodes_geometry:
                transform, geometry_name = mesh.graph.get(name)
                points = trimesh.transform_points(mesh.geometry[geometry_name].vertices, transform) * 1000
                glb_parts[name] = np.array([points.min(0), points.max(0)])
            component_check("GLB_component_alignment", glb_parts)
        rhino = file.parent / "model.3dm"
        if rhino.exists():
            import rhino3dm as r
            doc = r.File3dm.Read(str(rhino))
            check("3DM_units", doc.Settings.ModelUnitSystem == r.UnitSystem.Millimeters, "millimetres")
            check("3DM_components", len(doc.Objects) == expected_count, {"objects": len(doc.Objects)})
            component_check("3DM_component_alignment", {obj.Attributes.Name: np.array([
                np.min([[v.X, v.Y, v.Z] for v in obj.Geometry.Vertices], 0),
                np.max([[v.X, v.Y, v.Z] for v in obj.Geometry.Vertices], 0)]) for obj in doc.Objects})
            points = np.array([[v.X, v.Y, v.Z] for obj in doc.Objects for v in obj.Geometry.Vertices])
            error = float(np.max(np.abs(np.array([points.min(0), points.max(0)]) - target_bounds)))
            check("3DM_bounds", error < 1, {"max_error_mm": error})
        dae = file.parent / "model.dae"
        if dae.exists():
            import collada
            doc = collada.Collada(str(dae))
            check("DAE_units", abs(doc.assetInfo.unitmeter - .001) < 1e-12, doc.assetInfo.unitmeter)
            check("DAE_components", len(doc.geometries) == expected_count, len(doc.geometries))
            dae_parts = {}
            for bound in doc.scene.objects("geometry"):
                points = np.concatenate([primitive.vertex for primitive in bound.primitives()])
                dae_parts[bound.original.name] = np.array([points.min(0), points.max(0)])
            component_check("DAE_component_alignment", dae_parts)
            points = np.concatenate([g.sourceById[next(iter(g.sourceById))].data for g in doc.geometries])
            error = float(np.max(np.abs(np.array([points.min(0), points.max(0)]) - target_bounds)))
            check("DAE_bounds", error < 1, {"max_error_mm": error})
    for geo in root.rglob("*.geometry.json"):
        data = json.loads(geo.read_text(encoding="utf-8"))
        if expected_hash:
            check("view_source_version", data["project_hash"] == expected_hash, geo.name)
        stem = geo.with_name(geo.name.replace(".geometry.json", ""))
        pdf, dxf = stem.with_suffix(".pdf"), stem.with_suffix(".dxf")
        check("view_exports_present", pdf.is_file() and dxf.is_file(), stem.name)
        if dxf.exists():
            import ezdxf
            doc = ezdxf.readfile(dxf)
            auditor = doc.audit()
            check("DXF_structure", not auditor.has_errors and not auditor.has_fixes, dxf.name)
            check("DXF_mm_units", doc.units == 4, {"file": dxf.name, "units": doc.units})
            visible = [np.array(list(e.get_points("xy"))) for e in doc.modelspace().query('LWPOLYLINE[layer=="A-VISIBLE"]')]
            lines = data["lines"]
            aligned = len(visible) == len(lines) and all(a.shape == np.asarray(b).shape and np.allclose(a, b, atol=.001, rtol=0) for a, b in zip(visible, lines))
            check("DXF_projection_alignment", aligned, {"file": dxf.name, "paths": len(visible), "tolerance_mm": .001})
            dims = [float(d.get_measurement()) for d in doc.modelspace().query("DIMENSION")]
            wanted = [v["measured_mm"] for v in data["dimensions"]]
            matches = len(dims) == len(wanted) and all(abs(a - b) < .01 for a, b in zip(dims, wanted))
            check("DXF_dimensions", matches, {"file": dxf.name, "read_mm": dims, "expected_mm": wanted})
        if pdf.exists():
            with fitz.open(pdf) as doc:
                page = doc[0]
                segments = data.get("scale_bar_segments", 5)
                bar_height = data.get("scale_bar_height_mm", .9)
                bars = [d["rect"] for d in page.get_drawings()
                        if abs(d["rect"].height * 25.4 / 72 - bar_height) < .002]
                # The last five little rectangles are the 5 metre scale control.
                bars = bars[-segments:]
                actual = (max(b.x1 for b in bars) - min(b.x0 for b in bars)) * 25.4 / 72 if len(bars) == segments else None
                want = data.get("scale_bar_model_mm", 5000) / data["scale"]
                check("PDF_physical_scale", actual is not None and abs(actual - want) < .01,
                      {"file": pdf.name, "bar_mm": actual, "expected_bar_mm": want})
                check("PDF_is_vector", len(page.get_drawings()) > 0, {"file": pdf.name, "paths": len(page.get_drawings())})
    scene_map = {obj["id"]: np.concatenate([np.min(obj["vertices"], axis=0), np.max(obj["vertices"], axis=0)]).tolist()
                 for f in scenes for obj in json.loads(f.read_text(encoding="utf-8")).get("objects", [])}
    for report in root.rglob("render-report.json"):
        data = json.loads(report.read_text(encoding="utf-8"))
        check_bindings(data, report)
        if expected_hash and data.get("source_project_hash"):
            check("render_source_version", data["source_project_hash"] == expected_hash, str(report.relative_to(root)))
        stored_bounds = data.get("source_bounds", [])
        if stored_bounds:
            from .environment import find_blender
            executable = find_blender()
            if not executable:
                raise RuntimeError("Saved BLEND verification requires Blender; prepare the render profile")
            saved_report = report.parent / "blend-readback.json"
            asset_report = report.parent / "blend-assets-readback.json"
            with (report.parent / "blend-readback.log").open("w", encoding="utf-8") as stream:
                subprocess.run([executable, "--background", "--factory-startup", "--disable-autoexec", "--python-exit-code", "1",
                                "--python", str(skill_root() / "scripts/blender_verify.py"), "--",
                                "--input", str(report.parent / "scene.blend"), "--report", str(saved_report),
                                "--asset-report", str(asset_report)],
                               stdout=stream, stderr=subprocess.STDOUT, check=True)
            stored_bounds = json.loads(saved_report.read_text(encoding="utf-8"))
            dependencies = json.loads(asset_report.read_text(encoding="utf-8"))
            check("BLEND_images_packed", dependencies["all_images_packed"], dependencies["images"])
            if data.get("public_assets"):
                check("BLEND_asset_instances", {a["id"] for a in dependencies["instances"]} ==
                      {a["id"] for a in data["public_assets"]}, {"count": len(dependencies["instances"])})
            check("BLEND_saved_components", {o["id"] for o in stored_bounds} == {o["id"] for o in data["source_bounds"]}, report.parent.name)
        errors = [float(np.max(np.abs(np.array(obj["bounds_mm"]) - scene_map[obj["id"]])))
                  for obj in stored_bounds if obj["id"] in scene_map]
        if errors:
            check("Blender_model_alignment", max(errors) < .01, {"max_error_mm": max(errors), "components": len(errors)})
        for image in data["images"]:
            from PIL import Image
            with Image.open(report.parent / image["file"]) as im:
                array = np.asarray(im.convert("RGB"))
                nonblank = float(array.std()) > 5
                check("render_nonblank", nonblank, {"file": image["file"], "stddev": float(array.std())})
    for report in root.rglob("*.report.json"):
        data = json.loads(report.read_text(encoding="utf-8"))
        check_bindings(data.get("metadata", {}), report)
        if expected_hash and data.get("metadata", {}).get("project_hash"):
            check("graphic_source_version", data["metadata"]["project_hash"] == expected_hash, report.name)
        if "text_overflow" in data:
            check("text_page_bounds", not data["text_overflow"], {"file": report.name, "overflow": data["text_overflow"]})
        if "geometry_overflow" in data:
            check("geometry_page_bounds", not data["geometry_overflow"], {"file": report.name, "overflow": data["geometry_overflow"]})
    for report in root.rglob("board-report.json"):
        for sheet in json.loads(report.read_text(encoding="utf-8")):
            for slot in sheet["slots"]:
                file = Path(slot["file"])
                matches = file.exists() and hashlib.sha256(file.read_bytes()).hexdigest() == slot["source_sha256"]
                check("board_asset_version", matches, slot["id"])
    result = {"scope": "Technical integrity only; architectural quality requires separate review",
              "architectural_quality": "not_assessed", "root": str(root), "checks": checks, "passed": bool(checks) and all(c["passed"] for c in checks),
              "check_count": len(checks), "visual_review": "required separately; numerical checks do not assess aesthetics"}
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "audit.json", result)
    lines = ["# EZarch quantitative audit", "", f"Checks: {len(checks)}; passed: {result['passed']}", "",
             "| Check | Result | Evidence |", "|---|---|---|"]
    lines += [f"| {c['name']} | {'PASS' if c['passed'] else 'FAIL'} | {json.dumps(c['detail'], ensure_ascii=False)} |" for c in checks]
    lines += ["", "Visual quality must be reviewed using the actual generated images."]
    (out / "audit.md").write_text("\n".join(lines), encoding="utf-8")
    if not result["passed"]:
        raise ValueError("Audit failed; inspect audit.json")
    return result
