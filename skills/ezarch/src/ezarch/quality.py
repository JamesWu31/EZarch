"""Evidence validation, deliberately separate from professional/visual judgement."""
from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from .project import write_json

DIMENSIONS = {"conformance", "completeness", "design", "presentation"}


def review(source: Path, out: Path):
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    problems, seen, dimensions = [], set(), set()
    if data.get("schema_version") != 1 or not data.get("task") or not data.get("modules"):
        problems.append("Need schema_version: 1, task and selected modules")
    for criterion in data.get("criteria", []):
        cid = criterion.get("id", "")
        if not cid or cid in seen:
            problems.append(f"Missing or duplicate criterion ID: {cid}")
        seen.add(cid)
        dim = criterion.get("dimension")
        dimensions.add(dim)
        if dim not in DIMENSIONS:
            problems.append(f"{cid}: unknown quality dimension")
        for field in ["requirement", "basis", "observation"]:
            if not str(criterion.get(field, "")).strip():
                problems.append(f"{cid}: missing {field}")
        status = criterion.get("status", "pending")
        if status not in {"pass", "not_applicable"}:
            problems.append(f"{cid}: {status}")
        evidence = criterion.get("evidence", [])
        if status == "pass" and not evidence:
            problems.append(f"{cid}: pass requires evidence")
        for item in evidence:
            file = source.parent / item.get("file", "")
            if not file.is_file():
                problems.append(f"{cid}: missing evidence {item.get('file')}")
                continue
            with file.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            if item.get("sha256") != digest:
                problems.append(f"{cid}: stale/unbound evidence {item.get('file')}")
    for dim in sorted(DIMENSIONS - dimensions):
        problems.append(f"Missing quality dimension: {dim}")
    result = {"evidence_complete": not problems, "problems": problems,
              "scope": "Evidence integrity only; conclusions are authored architectural/visual review",
              "task": data.get("task"), "criteria": data.get("criteria", [])}
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "quality-report.json", result)
    lines = ["# Architectural quality review", "", result["scope"], ""]
    for c in data.get("criteria", []):
        lines += [f"- {c.get('id')}: **{c.get('status', 'pending')}** — {c.get('observation', '')}"]
    lines += ["", *[f"- ERROR: {p}" for p in problems]]
    (out / "quality-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if problems:
        raise ValueError("Quality review incomplete: " + "; ".join(problems))
    return result
