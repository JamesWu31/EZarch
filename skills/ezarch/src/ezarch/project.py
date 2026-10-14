"""Portable project contracts. All design geometry is in millimetres."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import yaml
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator


class Material(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True)
    color: list[float] = Field(default_factory=lambda: [0.72, 0.72, 0.7])
    roughness: float = Field(default=0.6, ge=0, le=1)
    metallic: float = Field(default=0, ge=0, le=1)
    transmission: float = Field(default=0, ge=0, le=1)
    texture: str = "plain"
    scale: float = Field(default=1, gt=0)
    maps: dict[str, str] = Field(default_factory=dict)
    texture_size_m: float = Field(default=1, gt=0)
    normal_strength: float = Field(default=1, ge=0)


class Project(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True)
    schema_version: int = 1
    name: str
    subtitle: str = ""
    units: str = "mm"
    north_angle: float = 0
    materials: dict[str, Material]
    elements: list[dict[str, Any]]
    rooms: list[dict[str, Any]] = Field(default_factory=list)
    views: list[dict[str, Any]] = Field(default_factory=list)
    cameras: list[dict[str, Any]] = Field(default_factory=list)
    landscape: list[dict[str, Any]] = Field(default_factory=list)
    dimensions: list[dict[str, Any]] = Field(default_factory=list)
    annotations: list[dict[str, Any]] = Field(default_factory=list)
    brief: dict[str, Any] = Field(default_factory=dict)
    render: dict[str, Any] = Field(default_factory=dict)
    board: dict[str, Any] = Field(default_factory=dict)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    levels: list[dict[str, Any]] = Field(default_factory=list)
    site: dict[str, Any] = Field(default_factory=dict)
    assemblies: dict[str, Any] = Field(default_factory=dict)
    requirements: list[dict[str, Any]] = Field(default_factory=list)
    _base_dir: Path = PrivateAttr(default_factory=Path.cwd)

    @model_validator(mode="after")
    def validate_geometry_contract(self):
        if self.schema_version != 1 or self.units != "mm":
            raise ValueError("schema_version must be 1 and design units must be mm")
        ids = [e.get("id") for e in self.elements]
        if any(not x for x in ids) or len(ids) != len(set(ids)):
            raise ValueError("Every element needs a unique, non-empty id")
        def finite(value):
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("Project numbers must be finite")
            if isinstance(value, dict):
                for v in value.values():
                    finite(v)
            elif isinstance(value, list):
                for v in value:
                    finite(v)
        finite(self.model_dump())
        for group in [self.elements, self.views, self.cameras]:
            group_ids = [v.get("id", "") for v in group]
            if len(group_ids) != len(set(group_ids)) or any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", x) for x in group_ids):
                raise ValueError("Element/view/camera IDs must be unique safe filenames (letters, digits, _, -, .)")
        for view in self.views:
            if view.get("scale", 100) <= 0 or view.get("margin", 22) < 0:
                raise ValueError("View scale must be positive and margin nonnegative")
        for room in self.rooms:
            from shapely.geometry import Polygon
            polygon = Polygon(room["polygon"])
            if not polygon.is_valid or polygon.area <= 0:
                raise ValueError(f"Invalid room polygon: {room.get('id')}")
        level_ids = [level["id"] for level in self.levels]
        if len(level_ids) != len(set(level_ids)):
            raise ValueError("Duplicate level IDs")
        if self.levels:
            for room in self.rooms:
                if room.get("level") not in level_ids:
                    raise ValueError(f"Room {room.get('id')} needs a known level")
            for view in self.views:
                if view.get("kind") == "plan" and view.get("level") not in level_ids:
                    raise ValueError("Multi-level plans need an explicit level")
        for material in self.materials.values():
            if set(material.maps) - {"base_color", "roughness", "normal", "metallic"}:
                raise ValueError("Unsupported PBR map semantic")
        supported = {"box", "slab", "wall", "cylinder", "extrusion", "stair", "step", "dxf_extrusion"}
        for e in self.elements:
            if e.get("kind") not in supported:
                raise ValueError(f"{e['id']}: unsupported kind {e.get('kind')}")
            if e.get("material") not in self.materials:
                raise ValueError(f"{e['id']}: unknown material {e.get('material')}")
            if e.get("kind") == "wall":
                from math import dist
                length = dist(e["start"], e["end"])
                if length <= 0 or e["thickness"] <= 0 or e["height"] <= 0:
                    raise ValueError(f"{e['id']}: invalid wall dimensions")
                intervals = []
                for opening in e.get("openings", []):
                    a, b = opening["offset"], opening["offset"] + opening["width"]
                    if not 0 <= a < b <= length:
                        raise ValueError(f"{e['id']}: opening exceeds wall length")
                    if opening.get("sill", 0) < 0 or opening["height"] <= 0:
                        raise ValueError(f"{e['id']}: invalid opening height")
                    if opening.get("sill", 0) + opening["height"] > e["height"]:
                        raise ValueError(f"{e['id']}: opening exceeds wall height")
                    intervals.append((a, b))
                for left, right in zip(sorted(intervals), sorted(intervals)[1:]):
                    if left[1] > right[0]:
                        raise ValueError(f"{e['id']}: overlapping openings")
        for m in self.materials.values():
            if len(m.color) != 3 or any(not 0 <= c <= 1 for c in m.color):
                raise ValueError("Material colors must have three components in [0, 1]")
        return self


def read_project(path: Path | str) -> Project:
    path = Path(path).resolve()
    project = Project.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    project._base_dir = path.parent
    return project


def fingerprint(project: Project) -> str:
    data = project.model_dump()
    data["external_file_hashes"] = {
        e["file"]: hashlib.sha256((project._base_dir / e["file"]).read_bytes()).hexdigest()
        for e in project.elements if e["kind"] in {"step", "dxf_extrusion"}
    }
    dependencies = [path for m in project.materials.values() for path in m.maps.values()]
    dependencies += [view["font"] for view in project.views if view.get("font")]
    dependencies += [a["file"] for a in project.render.get("asset_instances", [])]
    if project.render.get("hdri"):
        dependencies.append(project.render["hdri"])
    # A GLTF header alone does not bind geometry or textures. Include local buffers
    # and images so changing a downloaded dependency invalidates stale outputs.
    for name in list(dependencies):
        file = project._base_dir / name
        if file.suffix.lower() == ".gltf":
            gltf = json.loads(file.read_text(encoding="utf-8"))
            for item in gltf.get("buffers", []) + gltf.get("images", []):
                uri = item.get("uri", "")
                if not uri or uri.startswith("data:"):
                    continue
                if urlparse(uri).scheme:
                    raise ValueError("Download remote GLTF dependencies before building the project")
                dependencies.append(Path(os.path.relpath(file.parent / unquote(uri), project._base_dir)).as_posix())
    for name in sorted(set(dependencies)):
        with (project._base_dir / name).open("rb") as stream:
            data["external_file_hashes"][name] = hashlib.file_digest(stream, "sha256").hexdigest()
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def write_json(path: Path, data: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def skill_root() -> Path:
    source_root = Path(__file__).resolve().parents[2]
    return source_root if (source_root / "assets").is_dir() else Path(__file__).resolve().parent / "resources"


def atomic_text(path: Path, data: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(data, encoding="utf-8")
    temporary.replace(path)
