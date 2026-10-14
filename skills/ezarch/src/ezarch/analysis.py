"""Small, inspectable analytical helpers. No implied regulatory certification."""
from __future__ import annotations

import math
from datetime import datetime, timezone


def solar_position(latitude: float, longitude: float, when: datetime) -> dict:
    """NOAA fractional-year approximation; azimuth clockwise from geographic north.

    https://gml.noaa.gov/grad/solcalc/solareqns.PDF
    UTC-aware input removes local clock/DST ambiguity. No refraction correction.
    """
    if when.tzinfo is None or when.utcoffset() is None:
        raise ValueError("Solar calculation needs timezone-aware datetime")
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("Invalid geographic coordinates")
    t = when.astimezone(timezone.utc)
    year_days = 366 if t.year % 4 == 0 and (t.year % 100 != 0 or t.year % 400 == 0) else 365
    hour = t.hour + t.minute / 60 + t.second / 3600
    gamma = 2 * math.pi / year_days * (t.timetuple().tm_yday - 1 + (hour - 12) / 24)
    eq = 229.18 * (.000075 + .001868 * math.cos(gamma) - .032077 * math.sin(gamma)
                   - .014615 * math.cos(2 * gamma) - .040849 * math.sin(2 * gamma))
    dec = (.006918 - .399912 * math.cos(gamma) + .070257 * math.sin(gamma)
           - .006758 * math.cos(2 * gamma) + .000907 * math.sin(2 * gamma)
           - .002697 * math.cos(3 * gamma) + .00148 * math.sin(3 * gamma))
    ha = math.radians(((hour * 60 + eq + 4 * longitude) % 1440) / 4 - 180)
    lat = math.radians(latitude)
    cosz = math.sin(lat) * math.sin(dec) + math.cos(lat) * math.cos(dec) * math.cos(ha)
    altitude = 90 - math.degrees(math.acos(max(-1, min(1, cosz))))
    azimuth = (math.degrees(math.atan2(math.sin(ha), math.cos(ha) * math.sin(lat)
                                      - math.tan(dec) * math.cos(lat))) + 180) % 360
    return {"altitude_deg": altitude, "azimuth_deg": azimuth, "datetime": when.isoformat(),
            "latitude": latitude, "longitude": longitude,
            "method": "NOAA fractional-year approximation; no refraction"}


def shadow_vector(height_mm: float, sun: dict) -> list[float] | None:
    """Horizontal ground shadow offset in world x=east, y=north, in mm."""
    if height_mm < 0:
        raise ValueError("Height must be nonnegative")
    if sun["altitude_deg"] <= 0:
        return None
    length = height_mm / math.tan(math.radians(sun["altitude_deg"]))
    az = math.radians(sun["azimuth_deg"])
    return [-length * math.sin(az), -length * math.cos(az)]


def check_clearances(zones: list[dict], obstacles: list[dict], rooms: dict | None = None) -> dict:
    """Check explicitly defined operational polygons. Geometry in millimetres.

    A zone may ignore its owning furniture IDs. Boundary contact is allowed;
    positive intersected area over tolerance_mm2 is an interference.
    """
    from shapely.geometry import Polygon
    results = []
    for zone in zones:
        p = Polygon(zone["polygon"])
        if not p.is_valid or p.area <= 0:
            raise ValueError(f"Invalid clearance polygon {zone['id']}")
        hits = []
        for obstacle in obstacles:
            if obstacle["id"] in zone.get("ignore", []):
                continue
            if obstacle.get("level") != zone.get("level"):
                continue
            area = p.intersection(Polygon(obstacle["polygon"])).area
            if area > zone.get("tolerance_mm2", 1):
                hits.append({"id": obstacle["id"], "overlap_mm2": area})
        outside = 0
        if zone.get("room"):
            if not rooms or zone["room"] not in rooms:
                raise ValueError(f"Unknown room {zone['room']}")
            outside = p.difference(Polygon(rooms[zone["room"]])).area
        results.append({"id": zone["id"], "conflicts": hits, "outside_mm2": outside,
                        "passed": not hits and outside <= zone.get("tolerance_mm2", 1)})
    return {"assessed": bool(zones), "passed": bool(zones) and all(r["passed"] for r in results),
            "scope": "Only supplied zones, obstacles and room boundaries; not full code compliance",
            "checks": results}


def swing_envelope(hinge, radius_mm, closed_angle_deg, opening_angle_deg=90):
    """Plan polygon swept by one hinged leaf; feed it to check_clearances.

    Does not apply to sliding doors. Angles are counter-clockwise from world X.
    """
    if radius_mm <= 0 or not 0 < abs(opening_angle_deg) <= 180:
        raise ValueError("Need positive leaf radius and a nonzero swing up to 180 degrees")
    count = max(24, math.ceil(abs(opening_angle_deg)))
    arc = []
    for i in range(count + 1):
        a = math.radians(closed_angle_deg + opening_angle_deg * i / count)
        arc.append([hinge[0] + radius_mm * math.cos(a), hinge[1] + radius_mm * math.sin(a)])
    return [list(hinge), *arc, list(hinge)]


def oriented_footprint(size_mm, position_mm, rotation_z_deg=0):
    """Conservative XY envelope for a centre-bottom anchored imported asset.

    Use the measured, uniformly scaled dimensions from the render/import report,
    not a catalogue name. The rotated rectangle can be tested against walls,
    indoor exclusion polygons or circulation using check_clearances.
    """
    if len(size_mm) < 2 or len(position_mm) < 2:
        raise ValueError("Need at least XY size and position")
    w, d = size_mm[:2]
    if not all(math.isfinite(v) for v in [w, d, *position_mm[:2], rotation_z_deg]) or min(w, d) <= 0:
        raise ValueError("Asset footprint needs finite positive dimensions")
    a = math.radians(rotation_z_deg)
    return [[position_mm[0] + x * math.cos(a) - y * math.sin(a),
             position_mm[1] + x * math.sin(a) + y * math.cos(a)]
            for x, y in [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)]]
