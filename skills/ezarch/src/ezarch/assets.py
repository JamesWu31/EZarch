"""Small public-asset client; downloads belong to projects, never the skill tree."""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .project import write_json


def fetch_polyhaven(asset_id: str, out: Path, kind="model", resolution="1k"):
    """Fetch one CC0 asset and its dependencies from the official public API.

    Respects API attribution and a distinct User-Agent. Never executes downloads.
    Network availability and catalogue coverage are not guaranteed.
    """
    if not re.fullmatch(r"[a-z0-9_]+", asset_id) or not re.fullmatch(r"[1248]k", resolution):
        raise ValueError("Invalid public asset ID or resolution")
    def get(url):
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in {"api.polyhaven.com", "dl.polyhaven.org"}:
            raise ValueError("Expected official Poly Haven HTTPS URL")
        for attempt in range(3):
            try:
                with urlopen(Request(url, headers={"User-Agent": "EZarch/0.2 public-architecture-skill"}), timeout=30) as response:
                    return response.read()
            except HTTPError as error:
                if error.code < 500 or attempt == 2:
                    raise
            except (URLError, TimeoutError):
                if attempt == 2:
                    raise
            time.sleep(attempt + 1)
    metadata = json.loads(get(f"https://api.polyhaven.com/files/{asset_id}"))
    selected = []
    if kind == "model":
        entry = metadata["gltf"][resolution]["gltf"]
        selected.append((Path(urlparse(entry["url"]).path).name, entry))
        selected.extend(entry.get("include", {}).items())
    elif kind == "texture":
        for semantic in ("Diffuse", "Rough", "nor_gl"):
            entry = metadata[semantic][resolution]["jpg"]
            selected.append((Path(urlparse(entry["url"]).path).name, entry))
    elif kind == "hdri":
        entry = metadata["hdri"][resolution]["hdr"]
        selected.append((Path(urlparse(entry["url"]).path).name, entry))
    else:
        raise ValueError("kind must be model, texture or hdri")
    out = out.resolve()
    files = []
    for relative, entry in selected:
        path = (out / relative).resolve()
        if not path.is_relative_to(out):
            raise ValueError("Dependency path escapes asset directory")
        content = path.read_bytes() if path.exists() else get(entry["url"])
        if hashlib.md5(content, usedforsecurity=False).hexdigest() != entry["md5"]:
            raise ValueError(f"Checksum mismatch: {relative}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        files.append({"file": relative, "url": entry["url"], "sha256": hashlib.sha256(content).hexdigest(),
                      "bytes": len(content)})
    result = {"asset_id": asset_id, "provider": "Poly Haven", "source_url": f"https://polyhaven.com/a/{asset_id}",
              "license": "CC0-1.0", "license_url": "https://polyhaven.com/license", "kind": kind,
              "resolution": resolution, "files": files, "model_units": "Inspect imported bounds; never assume size"}
    write_json(out / "asset-manifest.json", result)
    return result
