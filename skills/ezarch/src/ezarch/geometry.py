"""One exact geometry source for model exchange, cuts and rendering meshes."""
from __future__ import annotations

from dataclasses import dataclass, field
from math import atan2, degrees, dist
from pathlib import Path
from typing import Any

from .project import Project, fingerprint, write_json


@dataclass
class Part:
    id: str
    shape: Any
    material: str
    category: str
    metadata: dict = field(default_factory=dict)


def box(origin, size):
    import cadquery as cq
    if any(float(v) <= 0 for v in size):
        raise ValueError(f"Non-positive box size: {size}")
    return cq.Solid.makeBox(*map(float, size), cq.Vector(*origin))


def build(project: Project) -> list[Part]:
    import cadquery as cq
    result: list[Part] = []
    for e in project.elements:
        kind, eid, material = e["kind"], e["id"], e["material"]
        category = e.get("category", kind)
        meta = {"source_id": eid, "kind": kind, **{k: e[k] for k in
                ("level", "assembly", "type_code", "provenance") if k in e}}
        if kind == "step":
            shape = cq.importers.importStep(str(project._base_dir / e["file"])).val()
            if not shape.Solids():
                raise ValueError(f"{eid}: STEP contains no solids")
            shape = shape.translate(e.get("origin", [0, 0, 0]))
        elif kind == "dxf_extrusion":
            import ezdxf
            from shapely.geometry import Polygon
            drawing = ezdxf.readfile(project._base_dir / e["file"])
            if drawing.units == 0:
                raise ValueError("Unitless DXF: assign its documented source units before import")
            factor = ezdxf.units.conversion_factor(drawing.units, ezdxf.units.MM)
            profiles = []
            for entity in drawing.modelspace().query("LWPOLYLINE"):
                if entity.dxf.layer != e["layer"]:
                    continue
                if not entity.closed or any(abs(p[4]) > 1e-12 for p in entity.get_points()):
                    raise ValueError("DXF extrusion requires closed straight LWPOLYLINE profiles; resolve arcs/open paths explicitly")
                if abs(entity.dxf.elevation) > .001 or tuple(entity.dxf.extrusion) != (0, 0, 1):
                    raise ValueError("DXF profiles must be on the world XY plane")
                pts = [(p[0] * factor, p[1] * factor) for p in entity.get_points()]
                polygon = Polygon(pts)
                if not polygon.is_valid or polygon.area <= 0:
                    raise ValueError("Invalid DXF boundary")
                profiles.append((polygon, pts))
            if not profiles:
                raise ValueError(f"No profiles found on layer {e['layer']}")
            for i, (polygon, _) in enumerate(profiles):
                if any(polygon.intersects(other) for other, _ in profiles[i + 1:]):
                    raise ValueError("Nested/overlapping DXF profiles need explicit hole/union semantics")
            shapes = [cq.Workplane("XY").polyline(pts).close().extrude(e["height"]).val() for _, pts in profiles]
            shape = cq.Compound.makeCompound(shapes).translate(e.get("origin", [0, 0, 0]))
        elif kind in ("box", "slab"):
            shape = box(e["origin"], e["size"])
        elif kind == "cylinder":
            if e["radius"] <= 0 or e["height"] <= 0:
                raise ValueError(f"{eid}: invalid cylinder")
            shape = cq.Solid.makeCylinder(e["radius"], e["height"], cq.Vector(*e["origin"]))
        elif kind == "extrusion":
            poly = e["polygon"]
            shape = cq.Workplane("XY").polyline(poly).close().extrude(e["height"]).val()
            shape = shape.translate((0, 0, e.get("z", 0)))
        elif kind == "stair":
            count = int(e["steps"])
            if count < 1:
                raise ValueError(f"{eid}: staircase requires at least one step")
            rise, run, width = e["rise"], e["run"], e["width"]
            steps = [box((i * run, 0, 0), (run, width, (i + 1) * rise)) for i in range(count)]
            shape = cq.Compound.makeCompound(steps)
            shape = shape.rotate((0, 0, 0), (0, 0, 1), e.get("rotation", 0))
            shape = shape.translate(e["origin"])
            meta.update(steps=count, rise=rise, run=run)
        elif kind == "wall":
            start, end = e["start"], e["end"]
            length, thickness = dist(start, end), e["thickness"]
            height, z = e["height"], e.get("z", 0)
            angle = degrees(atan2(end[1] - start[1], end[0] - start[0]))

            def placed(s, angle=angle, start=start, z=z):
                return s.rotate((0, 0, 0), (0, 0, 1), angle).translate((*start, z))

            shape = box((0, -thickness / 2, 0), (length, thickness, height))
            for i, opening in enumerate(e.get("openings", [])):
                offset, width = opening["offset"], opening["width"]
                sill, oh = opening.get("sill", 0), opening["height"]
                void = box((offset, -thickness / 2 - 1, sill), (width, thickness + 2, oh))
                shape = shape.cut(void)
                opening_kind = opening.get("type", "passage")
                if opening_kind == "passage":
                    continue
                oid = f"{eid}-opening-{i}"
                frame = opening.get("frame", 42)
                depth = opening.get("depth", 65)
                frame_material = opening.get("frame_material", material)
                # Accurate frames and mullions are real geometry, not painted textures.
                members = [((offset, -depth / 2, sill), (frame, depth, oh)),
                           ((offset + width - frame, -depth / 2, sill), (frame, depth, oh)),
                           ((offset, -depth / 2, sill + oh - frame), (width, depth, frame))]
                if opening_kind == "window":
                    members.append(((offset, -depth / 2, sill), (width, depth, frame)))
                panels = max(1, int(opening.get("panels", 1)))
                for n in range(1, panels):
                    members.append(((offset + width * n / panels - frame / 2, -depth / 2, sill),
                                    (frame, depth, oh)))
                for n, (origin, size) in enumerate(members):
                    result.append(Part(f"{oid}-frame-{n}", placed(box(origin, size)),
                                       frame_material, "frame", {**meta, "opening": opening}))
                if opening_kind in ("window", "glass_door"):
                    gm = opening.get("glass_material", "glass")
                    if gm not in project.materials:
                        raise ValueError(f"{oid}: missing glass material {gm}")
                    for n in range(panels):
                        panel_width = width / panels - frame
                        glass = box((offset + n * width / panels + frame / 2, -4, sill + frame),
                                    (panel_width, 8, oh - 2 * frame))
                        result.append(Part(f"{oid}-glass-{n}", placed(glass), gm, "glass", meta))
                elif opening_kind == "door":
                    leaf = box((offset + frame, -20, sill), (width - 2 * frame, 40, oh - frame))
                    result.append(Part(f"{oid}-leaf", placed(leaf),
                                       opening.get("leaf_material", material), "door", meta))
            shape = placed(shape)
            meta.update(length_mm=length, thickness_mm=thickness, height_mm=height)
        else:
            raise ValueError(f"Unsupported element: {eid}")
        for cutter in e.get("cuts", []):
            if cutter["kind"] == "box":
                tool = box(cutter["origin"], cutter["size"])
            elif cutter["kind"] == "cylinder":
                tool = cq.Solid.makeCylinder(cutter["radius"], cutter["height"], cq.Vector(*cutter["origin"]))
            else:
                raise ValueError(f"Unsupported Boolean cutter: {cutter['kind']}")
            shape = shape.cut(tool)
        if e.get("fillet_mm"):
            shape = shape.fillet(float(e["fillet_mm"]), shape.Edges())
        if kind != "stair" and e.get("rotation"):
            origin = e.get("origin", [0, 0, 0])
            shape = shape.rotate(origin, [origin[0], origin[1], origin[2] + 1], e["rotation"])
        if not shape.isValid():
            raise ValueError(f"Invalid exact geometry: {eid}")
        result.append(Part(eid, shape, material, category, meta))
    return result


def bounds(shape) -> list[float]:
    b = shape.BoundingBox()
    return [b.xmin, b.ymin, b.zmin, b.xmax, b.ymax, b.zmax]


def mesh_scene(project: Project, parts: list[Part], tolerance=1.0) -> dict:
    objects = []
    for part in parts:
        verts, faces = part.shape.tessellate(tolerance, 0.08)
        objects.append({"id": part.id, "material": part.material, "category": part.category,
                        "vertices": [list(v.toTuple()) for v in verts],
                        "faces": [list(f) for f in faces], "bounds_mm": bounds(part.shape),
                        "volume_mm3": part.shape.Volume(), "metadata": part.metadata})
    materials = {k: v.model_dump() for k, v in project.materials.items()}
    for spec in materials.values():
        spec["maps"] = {k: str((project._base_dir / p).resolve()) for k, p in spec.get("maps", {}).items()}
    render = dict(project.render)
    if render.get("hdri"):
        render["hdri"] = str((project._base_dir / render["hdri"]).resolve())
    render["asset_instances"] = [{**a, "file": str((project._base_dir / a["file"]).resolve())}
                                 for a in render.get("asset_instances", [])]
    return {"schema_version": 1, "name": project.name, "units": "mm",
            "project_hash": fingerprint(project), "mesh_tolerance_mm": tolerance,
            "materials": materials,
            "objects": objects, "cameras": project.cameras, "landscape": project.landscape,
            "render": render}


def generate_model(project: Project, out: Path, formats=None) -> dict:
    import cadquery as cq

    from .exchange import export_scene
    out.mkdir(parents=True, exist_ok=True)
    parts = build(project)
    scene = mesh_scene(project, parts)
    write_json(out / "scene.json", scene)
    assembly = cq.Assembly(name="EZarch")
    for part in parts:
        color = project.materials[part.material].color
        assembly.add(part.shape, name=part.id, color=cq.Color(*color))
    assembly.export(str(out / "model.step"))
    exports = export_scene(scene, out, formats or ["glb", "3dm", "dae"])
    result = {"module": "model", "project_hash": fingerprint(project), "parts": len(parts),
              "exact_geometry": "model.step", "scene": "scene.json", "exports": exports,
              "total_volume_mm3": sum(p.shape.Volume() for p in parts),
              "geometry_valid": all(p.shape.isValid() for p in parts)}
    write_json(out / "model-report.json", result)
    return result
