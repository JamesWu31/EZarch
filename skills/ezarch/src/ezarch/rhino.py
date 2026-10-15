"""Native 3DM geometry, preserving curves/surfaces/BReps instead of flattening to meshes."""
from __future__ import annotations

import math
from pathlib import Path
from xml.sax.saxutils import escape

from .cad import check_source, destination, sha256


def write_geometry(objects, target, units='Millimeters', tolerance=.01):
    """Write iterable (geometry, attributes) pairs; accepts arbitrary rhino3dm geometry.

    Geometry construction is the caller's design decision: NURBS, curves, extrusions,
    Breps, meshes and instances need not pass through EZarch's Project schema.
    """
    import rhino3dm as r
    target = Path(target)
    if target.exists():
        raise FileExistsError(target)
    doc = r.File3dm()
    doc.Settings.ModelUnitSystem = getattr(r.UnitSystem, units)
    doc.Settings.ModelAbsoluteTolerance = tolerance
    for geometry, attributes in objects:
        if not geometry.IsValid:
            raise ValueError(geometry.IsValidWithLog)
        doc.Objects.Add(geometry, attributes)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not doc.Write(str(target), 8):
        raise RuntimeError('3DM write failed')
    reread = r.File3dm.Read(str(target))
    if reread is None or len(reread.Objects) != len(doc.Objects) or any(not o.Geometry.IsValid for o in reread.Objects):
        raise RuntimeError('3DM readback failed')
    return {'file': str(target), 'objects': len(reread.Objects), 'geometry': [type(o.Geometry).__name__ for o in reread.Objects]}


def edit(source, target, ids, move=None, name=None, expected=None):
    import uuid

    import rhino3dm as r
    source, target = destination(source, target)
    if target.suffix.lower() != '.3dm':
        raise ValueError('3DM edits require a .3dm output')
    before = check_source(source, expected)
    if move is not None and (len(move) != 3 or not all(math.isfinite(v) for v in move)):
        raise ValueError("Translation needs three finite source-unit values")
    doc = r.File3dm.Read(str(source))
    if doc is None:
        raise ValueError('Unreadable 3DM')
    selected = [doc.Objects.FindId(uuid.UUID(i)) for i in ids]
    if not selected or any(o is None for o in selected):
        raise ValueError('Selection contains missing object IDs')
    for obj in selected:
        geometry, attributes = obj.Geometry.Duplicate(), obj.Attributes
        if move is not None and not geometry.Translate(r.Vector3d(*move)):
            raise ValueError('Geometry translation failed')
        if name is not None:
            attributes.Name = name
        original_id = attributes.Id
        doc.Objects.Delete(original_id)
        new_id = doc.Objects.Add(geometry, attributes)
        if new_id != original_id:
            raise RuntimeError('Object ID changed unexpectedly')
    if not doc.Write(str(target), 8):
        raise RuntimeError('3DM write failed')
    return {'source_sha256': before, 'output_sha256': sha256(target), 'ids': ids, 'file': str(target)}


def planar_brep(shape):
    """Exact straight-edged prismatic solid, reconstructed as a capped native extrusion.

    Matching volume/containment verifies that the selected face really generates
    the source solid, including holes/notches. Mesh-to-BRep is deliberately avoided:
    rhino3dm 8.35 leaves invalid unset edge tolerances on that path.
    """
    import cadquery as cq
    import rhino3dm as r
    from OCP.BRep import BRep_Tool
    from OCP.BRepTools import BRepTools_WireExplorer
    if len(shape.Solids()) != 1 or any(f.geomType() != 'PLANE' for f in shape.Faces()) or any(e.geomType() != 'LINE' for e in shape.Edges()):
        raise ValueError('Exact 3DM adapter supports straight-edged prismatic solids; use native rhino3dm or precise STEP for other geometry; no mesh fallback is applied')
    solid = shape.Solids()[0]
    vertices = [v.Center() for v in solid.Vertices()]

    def curve(wire):
        explorer = BRepTools_WireExplorer(wire.wrapped)
        points = []
        while explorer.More():
            point = BRep_Tool.Pnt_s(explorer.CurrentVertex())
            points.append(r.Point3d(point.X(), point.Y(), point.Z()))
            explorer.Next()
        return r.PolylineCurve(points + points[:1])

    for face in solid.Faces():
        origin = face.Center()
        direction = face.normalAt().multiply(-1)
        depth = max((v - origin).dot(direction) for v in vertices)
        if depth <= 1e-9:
            continue
        candidate = cq.Solid.extrudeLinear(face.outerWire(), face.innerWires(), direction.multiply(depth))
        tolerance = max(1e-7, abs(solid.Volume()) * 1e-10)
        if abs(candidate.Volume() - solid.Volume()) > tolerance:
            continue
        if candidate.cut(solid).Volume() + solid.cut(candidate).Volume() > tolerance:
            continue
        plane = r.Plane(r.Point3d(*origin.toTuple()), r.Vector3d(*direction.toTuple()))
        extrusion = r.Extrusion.CreateWithPlane(curve(face.outerWire()), plane, depth, True)
        if extrusion is None:
            continue
        holes_ok = True
        for wire in face.innerWires():
            inner = curve(wire)
            inner.Transform(r.Transform.PlaneToPlane(plane, r.Plane.WorldXY()))
            holes_ok = extrusion.AddInnerProfile(inner) and holes_ok
        if not holes_ok:
            continue
        brep = extrusion.ToBrep(True)
        if brep and brep.IsValid and brep.IsSolid:
            return brep
    raise ValueError('Solid is not a supported exact prism; use native geometry or precise STEP; no mesh fallback is applied')


def export_parts(parts, materials, target):
    """Transfer prismatic OCCT solids to true closed Breps with named layers.

    Native profiles retain openings/notches. No curved surface is tessellated
    on this route. General STEP remains available for Rhino import.
    """
    import rhino3dm as r
    doc = r.File3dm()
    doc.Settings.ModelUnitSystem = r.UnitSystem.Millimeters
    layers = {}
    count = 0
    for part in parts:
        if part.category not in layers:
            layer = r.Layer()
            layer.Name = part.category
            layers[part.category] = doc.Layers.Add(layer)
        for i, solid in enumerate(part.shape.Solids()):
            brep = planar_brep(solid)
            attributes = r.ObjectAttributes()
            attributes.Name = part.id if len(part.shape.Solids()) == 1 else f'{part.id}/{i}'
            attributes.LayerIndex = layers[part.category]
            attributes.SetUserString('source_id', part.id)
            attributes.SetUserString('ezarch_id', part.id)
            attributes.ObjectColor = tuple(round(v * 255) for v in materials[part.material].color) + (255,)
            attributes.ColorSource = r.ObjectColorSource.ColorFromObject
            doc.Objects.AddBrep(brep, attributes)
            count += 1
    if not count:
        raise ValueError('No solids to export')
    if not doc.Write(str(target), 8):
        raise RuntimeError('3DM write failed')
    loaded = r.File3dm.Read(str(target))
    if loaded is None or len(loaded.Objects) != count or any(not o.Geometry.IsSolid for o in loaded.Objects):
        raise RuntimeError('Closed BRep readback failed')
    return {'file': Path(target).name, 'format': '3dm', 'units': 'mm', 'objects': count,
            'geometry': 'exact prismatic Breps with planar trimmed faces'}


def preview(source, target, handles=None, direction=(1, -1, .8), samples=80):
    """Inspectable wire view with source UUID per SVG group; no shaded/hidden-line claim."""
    import numpy as np
    import rhino3dm as r

    from .inspection import raster_svg
    doc = r.File3dm.Read(str(source))
    if doc is None:
        raise ValueError('Unreadable 3DM')
    forward = np.array(direction, dtype=float)
    if np.linalg.norm(forward) == 0:
        raise ValueError('Direction cannot be zero')
    forward /= np.linalg.norm(forward)
    up = np.array([0., 0., 1.]) if abs(forward[2]) < .99 else np.array([0., 1., 0.])
    right = np.cross(forward, up)
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    paths, warnings = [], []

    def collect(g, key, transforms=(), ancestry=()):
        if isinstance(g, r.InstanceReference):
            if str(g.ParentIdefId) in ancestry:
                warnings.append(f'{key}: cyclic instance reference')
                return
            definition = doc.InstanceDefinitions.FindId(g.ParentIdefId)
            if definition is None:
                warnings.append(f'{key}: missing instance definition')
                return
            for child_id in definition.GetObjectIds():
                child = doc.Objects.FindId(child_id)
                if child:
                    collect(child.Geometry, key + '/' + str(child_id), (g.Xform,) + transforms,
                            ancestry + (str(g.ParentIdefId),))
            return
        curves = []
        if isinstance(g, r.Extrusion):
            g = g.ToBrep(True)
        if isinstance(g, r.Brep):
            curves = list(g.Edges)
        elif isinstance(g, r.Curve):
            curves = [g]
        elif isinstance(g, r.Surface):
            curves = [g.IsoCurve(d, g.Domain(1 - d).T0) for d in (0, 1)]
            curves += [g.IsoCurve(d, g.Domain(1 - d).T1) for d in (0, 1)]
        elif isinstance(g, r.Mesh):
            for f in g.Faces:
                ids = list(f[:3]) if f[2] == f[3] else list(f)
                points = [g.Vertices[i] for i in ids + [ids[0]]]
                emit(points, key, transforms)
        else:
            warnings.append(f'{key}: {type(g).__name__} not represented in wire preview')
        for c in curves:
            if c is not None:
                d = c.Domain
                emit([c.PointAt(d.T0 + (d.T1 - d.T0) * i / samples) for i in range(samples + 1)], key, transforms)

    def emit(points, key, transforms):
        values = []
        for p in points:
            p = r.Point3d(p.X, p.Y, p.Z)
            for transform in transforms:
                p.Transform(transform)
            v = np.array([p.X, p.Y, p.Z])
            values.append([float(v @ right), -float(v @ up)])
        if values:
            paths.append((key, values))

    for obj in doc.Objects:
        if obj.Attributes.IsInstanceDefinitionObject:
            continue
        if handles and str(obj.Attributes.Id) not in handles:
            continue
        if not obj.Attributes.Visible or not doc.Layers[obj.Attributes.LayerIndex].Visible:
            continue
        collect(obj.Geometry, str(obj.Attributes.Id))
    if not paths:
        raise ValueError('No supported visible wire geometry')
    pts = np.array([p for _, path in paths for p in path])
    low, high = pts.min(0), pts.max(0)
    factor = 1120 / max(high - low)
    lines = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="900" viewBox="0 0 1200 900">', '<rect width="1200" height="900" fill="white"/>']
    factor = min(factor, 820 / max(float((high - low)[1]), .00001))
    for key, points in paths:
        values = [(np.array(p) - low) * factor + 40 for p in points]
        d = 'M ' + ' L '.join(f'{x:.4f},{y:.4f}' for x, y in values)
        lines.append(f'<path data-source-id="{escape(key)}" d="{d}" fill="none" stroke="#263645" stroke-width="1"/>')
    lines.append('</svg>')
    target = Path(target).with_suffix('.svg')
    target.write_text('\n'.join(lines), encoding='utf-8')
    return raster_svg(target) | {'warnings': warnings, 'direction': list(direction),
                                 'scope': 'Sampled wire view, source UUID in data-source-id; not a dimensioning or occlusion result'}
