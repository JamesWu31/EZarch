"""Open exchange formats: named objects, explicit units, independent re-read."""
from __future__ import annotations

from pathlib import Path

from .project import write_json


def export_scene(scene, out: Path, formats):
    import numpy as np
    if scene.get("units") != "mm" or scene.get("schema_version") != 1:
        raise ValueError("Exchange requires schema 1 scene geometry in millimetres")
    if not scene.get("objects") or not formats or set(formats) - {"glb", "3dm", "dae"}:
        raise ValueError("Exchange needs nonempty geometry and supported formats (glb, 3dm, dae)")
    out.mkdir(parents=True, exist_ok=True)
    reports = []
    for fmt in formats:
        target = out / f"model.{fmt}"
        if fmt == "glb":
            import trimesh
            from trimesh.visual.material import PBRMaterial
            ts = trimesh.Scene()
            for obj in scene["objects"]:
                m = scene["materials"][obj["material"]]
                tm = trimesh.Trimesh(vertices=np.array(obj["vertices"]) / 1000,
                                     faces=obj["faces"], process=False)
                rgba = [round(c * 255) for c in m["color"]] + [255]
                tm.visual = trimesh.visual.TextureVisuals(material=PBRMaterial(
                    name=obj["material"], baseColorFactor=rgba,
                    roughnessFactor=m.get("roughness", .6), metallicFactor=m.get("metallic", 0)))
                ts.add_geometry(tm, node_name=obj["id"], geom_name=obj["id"])
            # glTF uses +Y up. Preserve the architectural Z-up basis through an
            # explicit node transform so conforming importers restore the orientation.
            basis = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]])
            ts.apply_transform(basis)
            ts.metadata["ezarch_up_axis"] = "Y"
            target.write_bytes(ts.export(file_type="glb"))
            loaded = trimesh.load(target, force="scene")
            count = len(loaded.geometry)
            if count != len(scene["objects"]):
                raise RuntimeError("GLB lost objects")
            loaded.apply_transform(basis.T)
            report = {"format": fmt, "units": "m", "objects": count, "up_axis": "Y",
                      "bounds_basis": "source_Z_up",
                      "bounds_mm": (loaded.bounds * 1000).tolist(), "geometry": "tessellated_mesh"}
        elif fmt == "3dm":
            import rhino3dm as r
            doc = r.File3dm()
            doc.Settings.ModelUnitSystem = r.UnitSystem.Millimeters
            layers = {}
            for category in sorted({o["category"] for o in scene["objects"]}):
                layer = r.Layer()
                layer.Name = category
                layers[category] = doc.Layers.Add(layer)
            for obj in scene["objects"]:
                mesh = r.Mesh()
                for v in obj["vertices"]:
                    mesh.Vertices.Add(*v)
                for f in obj["faces"]:
                    mesh.Faces.AddFace(*f)
                mesh.Normals.ComputeNormals()
                mesh.Compact()
                a = r.ObjectAttributes()
                a.Name = obj["id"]
                a.LayerIndex = layers[obj["category"]]
                a.SetUserString("ezarch_id", obj["id"])
                a.SetUserString("material", obj["material"])
                color = scene["materials"][obj["material"]]["color"]
                a.ObjectColor = tuple(round(v * 255) for v in color) + (255,)
                a.ColorSource = r.ObjectColorSource.ColorFromObject
                doc.Objects.AddMesh(mesh, a)
            if not doc.Write(str(target), 8):
                raise RuntimeError("Failed to write 3DM")
            loaded = r.File3dm.Read(str(target))
            if loaded is None or len(loaded.Objects) != len(scene["objects"]):
                raise RuntimeError("3DM re-read failed")
            report = {"format": fmt, "units": "mm", "objects": len(loaded.Objects),
                      "geometry": "editable named mesh objects; exact solids are in companion STEP"}
        elif fmt == "dae":
            import collada
            from collada import geometry, material, source
            from collada import scene as cs
            doc = collada.Collada()
            doc.assetInfo.unitname = "millimeter"
            doc.assetInfo.unitmeter = 0.001
            doc.assetInfo.upaxis = "Z_UP"
            nodes = []
            mats = {}
            for key, m in scene["materials"].items():
                effect = material.Effect(key + "-fx", [], "phong", diffuse=tuple(m["color"]) + (1,))
                mat = material.Material(key, key, effect)
                doc.effects.append(effect)
                doc.materials.append(mat)
                mats[key] = mat
            for i, obj in enumerate(scene["objects"]):
                sid = f"geom{i}"
                verts = source.FloatSource(sid + "-v", np.asarray(obj["vertices"], dtype=np.float32), ("X", "Y", "Z"))
                geo = geometry.Geometry(doc, sid, obj["id"], [verts])
                inputs = source.InputList()
                inputs.addInput(0, "VERTEX", "#" + sid + "-v")
                tris = geo.createTriangleSet(np.asarray(obj["faces"]).reshape(-1), inputs, "surface")
                geo.primitives.append(tris)
                doc.geometries.append(geo)
                mn = cs.MaterialNode("surface", mats[obj["material"]], inputs=[])
                nodes.append(cs.Node(obj["id"], children=[cs.GeometryNode(geo, [mn])]))
            root = cs.Scene("EZarch", nodes)
            doc.scenes.append(root)
            doc.scene = root
            doc.write(str(target))
            loaded = collada.Collada(str(target))
            if len(loaded.geometries) != len(scene["objects"]):
                raise RuntimeError("DAE re-read lost geometry")
            report = {"format": fmt, "units": "mm", "unitmeter": loaded.assetInfo.unitmeter,
                      "objects": len(loaded.geometries), "geometry": "named mesh nodes"}
        else:
            raise ValueError(f"Unsupported open exchange format: {fmt}")
        report["file"] = target.name
        reports.append(report)
    write_json(out / "exchange-report.json", reports)
    return reports
