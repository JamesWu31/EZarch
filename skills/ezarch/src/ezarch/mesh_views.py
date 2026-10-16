"""Orthographic sections and analytical hidden-line removal for polygonal models.

Coordinates/tolerances are millimetres. Results describe the supplied mesh, not
an exact CAD surface, and do not infer architectural symbols or compliance.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import numpy as np
from shapely import STRtree
from shapely.geometry import LineString, Polygon
from shapely.ops import polygonize, unary_union

from .project import write_json


def basis(spec):
    kind = spec.get('kind', 'plan')
    if kind == 'plan':
        normal, xdir, origin = [0, 0, 1], [1, 0, 0], [0, 0, spec.get('cut_z', 1200)]
    elif kind == 'section':
        axis = spec.get('axis', 'y')
        if axis not in ('x', 'y'):
            raise ValueError('section axis must be x or y; use explicit normal/origin for other planes')
        normal = [1, 0, 0] if axis == 'x' else [0, -1, 0]
        xdir = [0, 1, 0] if axis == 'x' else [1, 0, 0]
        origin = [spec.get('at', 0), 0, 0] if axis == 'x' else [0, spec.get('at', 0), 0]
    elif kind in ('elevation', 'axon'):
        normal = [0, -1, 0] if kind == 'elevation' else [1, -1, 1]
        xdir = [1, 0, 0] if kind == 'elevation' else [1, 1, 0]
        origin = [0, 0, 0]
    else:
        raise ValueError('kind must be plan, section, elevation or axon')
    n = np.asarray(spec.get('normal', normal), dtype=float)
    x = np.asarray(spec.get('xdir', xdir), dtype=float)
    origin = np.asarray(spec.get('origin', origin), dtype=float)
    if any(v.shape != (3,) or not np.isfinite(v).all() for v in (n, x, origin)) or np.linalg.norm(n) < 1e-12:
        raise ValueError('Invalid view basis')
    n /= np.linalg.norm(n)
    x -= n * np.dot(x, n)
    if np.linalg.norm(x) < 1e-12:
        raise ValueError('xdir is parallel to view normal')
    x /= np.linalg.norm(x)
    return kind, origin, np.array([x, np.cross(n, x), n])


def clipped(points, axis, at, keep_below=True):
    result = []
    sign = 1 if keep_below else -1
    for a, b in zip(points, [*points[1:], points[0]]):
        da, db = (a[axis] - at) * sign, (b[axis] - at) * sign
        if da <= 0:
            result.append(a)
        if (da < 0 < db) or (db < 0 < da):
            result.append(a + (b - a) * da / (da - db))
    return result


def _pieces(geometry):
    if geometry.is_empty:
        return []
    if geometry.geom_type == 'LineString':
        return [geometry]
    return [g for p in getattr(geometry, 'geoms', []) for g in _pieces(p)]


def extract_mesh_view(scene, spec):
    if scene.get('units') != 'mm':
        raise ValueError('Mesh view adapter requires millimetre geometry')
    tolerance = float(spec.get('tolerance_mm', .05))
    if not np.isfinite(tolerance) or tolerance <= 0:
        raise ValueError('tolerance_mm must be finite and positive')
    kind, origin, frame = basis(spec)
    if kind == 'plan' and spec.get('floor_z') is not None:
        if not np.allclose(frame[2], [0, 0, 1]) or float(spec['floor_z']) >= origin[2]:
            raise ValueError('floor_z requires a horizontal plan with floor_z below the cut origin')
    cut = kind in ('plan', 'section') or bool(spec.get('clip'))
    crease = np.cos(np.radians(float(spec.get('crease_degrees', 25))))
    edges, cut_segments, surfaces, planes = defaultdict(list), defaultdict(list), [], []
    selected = [o for o in scene['objects'] if o['id'] not in spec.get('exclude_ids', [])
                and o.get('category') not in spec.get('exclude', [])]
    count = sum(len(o['faces']) for o in selected)
    maximum = int(spec.get('max_triangles', 200000))
    if count > maximum:
        raise ValueError(f'{count} triangles exceeds this helper limit {maximum}; select relevant objects or explicitly raise max_triangles')
    for obj in selected:
        verts = (np.asarray(obj['vertices'], dtype=float) - origin) @ frame.T
        owner = obj.get('metadata', {}).get('instance_key', obj['id'])
        for face in obj['faces']:
            if len(face) != 3:
                raise ValueError('Triangulate evaluated polygons before this adapter')
            tri = verts[face]
            normal = np.cross(tri[1] - tri[0], tri[2] - tri[0])
            length = np.linalg.norm(normal)
            if length < 1e-12:
                continue
            normal /= length
            if cut:
                intersections = []
                for a, b in zip(tri, np.roll(tri, -1, axis=0)):
                    if abs(a[2]) <= tolerance * .01:
                        intersections.append(a[:2])
                    if a[2] * b[2] < 0:
                        intersections.append((a + (b - a) * a[2] / (a[2] - b[2]))[:2])
                distinct = {tuple(np.round(p / tolerance).astype(int)) for p in intersections}
                if len(distinct) == 2:
                    cut_segments[owner].append(LineString([np.array(p) * tolerance for p in sorted(distinct)]))
            poly = clipped(list(tri), 2, 0) if cut else list(tri)
            if kind == 'plan' and spec.get('floor_z') is not None:
                poly = clipped(poly, 2, float(spec['floor_z']) - origin[2], False) if poly else []
            if len(poly) < 3:
                continue
            for a, b in zip(poly, [*poly[1:], poly[0]]):
                ka, kb = tuple(np.round(a / tolerance).astype(int)), tuple(np.round(b / tolerance).astype(int))
                if ka != kb:
                    edges[(owner, *sorted([ka, kb]))].append(normal)
            polygon = Polygon([p[:2] for p in poly])
            if polygon.area > tolerance ** 2 * .01:
                # Plane z = ax + by + c; projected triangle is non-degenerate.
                coefficients = np.linalg.solve(np.column_stack((tri[:, :2], np.ones(3))), tri[:, 2])
                surfaces.append(polygon)
                planes.append(coefficients)
    tree = STRtree(surfaces)
    visible, seen = [], set()
    for (_, ka, kb), normals in edges.items():
        boundary = len(normals) == 1
        sharp = any(np.dot(normals[0], n) < crease for n in normals[1:])
        silhouette = min(n[2] for n in normals) < -1e-9 < max(n[2] for n in normals)
        if not (boundary or sharp or silhouette):
            continue
        a, b = np.array(ka) * tolerance, np.array(kb) * tolerance
        direction = b[:2] - a[:2]
        denominator = np.dot(direction, direction)
        if denominator < tolerance ** 2:
            continue
        segment = LineString([a[:2], b[:2]])
        hidden = []
        for index in tree.query(segment, predicate='intersects'):
            overlap = segment.intersection(surfaces[index])
            coeff = planes[index]
            for part in _pieces(overlap):
                points = np.asarray(part.coords)
                ts = sorted(float(np.dot(p - a[:2], direction) / denominator) for p in (points[0], points[-1]))
                lo, hi = max(0., ts[0]), min(1., ts[1])
                def delta(t, a=a, b=b, coeff=coeff):
                    q = a + (b - a) * t
                    return np.dot(coeff, [q[0], q[1], 1]) - q[2] - tolerance * 2
                dl, dh = delta(lo), delta(hi)
                if dl <= 0 and dh <= 0:
                    continue
                if dl * dh < 0:
                    crossing = lo + (hi - lo) * dl / (dl - dh)
                    if dl > 0:
                        hi = crossing
                    else:
                        lo = crossing
                if hi > lo:
                    hidden.append(LineString([a[:2] + direction * lo, a[:2] + direction * hi]))
        remain = segment.difference(unary_union(hidden)) if hidden else segment
        for piece in _pieces(remain):
            if piece.length <= tolerance:
                continue
            points = [list(piece.coords[0]), list(piece.coords[-1])]
            keys = tuple(tuple(round(c / tolerance) for c in p) for p in points)
            key = min(keys, keys[::-1])
            if key not in seen:
                seen.add(key)
                visible.append(points)
    cuts, warnings = [], []
    for owner, lines in cut_segments.items():
        polygons = list(polygonize(unary_union(lines)))
        # polygonize emits both an annulus and its inner cell; retain odd nesting.
        shells = [Polygon(p.exterior) for p in polygons]
        accepted = [p for i, p in enumerate(polygons)
                    if sum(s.contains(p.representative_point()) for j, s in enumerate(shells) if j != i) % 2 == 0]
        for p in accepted:
            cuts.append({'id': owner, 'category': 'mesh', 'outer': list(map(list, p.exterior.coords)),
                         'holes': [list(map(list, r.coords)) for r in p.interiors], 'area_mm2': p.area})
        closed = unary_union([p.boundary for p in polygons])
        if unary_union(lines).difference(closed.buffer(tolerance)).length > tolerance:
            warnings.append(f'{owner}: open section contours; inspect non-manifold surfaces or selection')
    return {'kind': kind, 'lines': visible, 'cuts': cuts, 'normal': frame[2].tolist(),
            'xdir': frame[0].tolist(), 'up': frame[1].tolist(), 'origin': origin.tolist(),
            'warnings': warnings, 'tolerance_mm': tolerance,
            'scope': 'Polygonal geometry sections and opaque-surface visibility; architectural symbols and annotations are separate.'}


def save_mesh_view(scene, spec, out, formats=('dxf', 'pdf')):
    import shutil

    from .project import Project, skill_root
    from .views import save_view
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    spec = dict(spec)
    spec.setdefault('id', 'view')
    if Path(spec['id']).name != spec['id'] or any(c in spec['id'] for c in '/\\:') or spec['id'] in ('.', '..'):
        raise ValueError('View id must be a filename stem')
    if not formats or set(formats) - {'dxf', 'pdf', 'svg', 'png'}:
        raise ValueError('Choose dxf/pdf/svg/png view formats')
    # Validate numeric options independently of the user's object names or project schema.
    if float(spec.get('scale', 100)) <= 0 or not np.isfinite(float(spec.get('scale', 100))):
        raise ValueError('View scale must be finite and positive')
    data = extract_mesh_view(scene, spec)
    data.update(source=scene.get('source'), source_sha256=scene.get('source_sha256'))
    project = Project.model_validate({'name': 'Blender view', 'materials': {}, 'elements': []})
    result = save_view(project, data, spec, out / spec['id'], formats)
    if 'dxf' in formats:
        (out / 'fonts').mkdir(exist_ok=True)
        for name in ('EZarchFang.ttf', 'COPYING', 'SOURCE.md'):
            shutil.copy2(skill_root() / 'assets/fonts' / name, out / 'fonts' / name)
    write_json(out / (spec['id'] + '.mesh-geometry.json'), data)
    return {'drawing': result, 'geometry': spec['id'] + '.mesh-geometry.json',
            'warnings': data['warnings'], 'source': scene.get('source'),
            'source_sha256': scene.get('source_sha256')}
