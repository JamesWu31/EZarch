"""Optional integrity checks for task-selected evidence; no prescribed review categories."""
from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from .project import write_json


def review(source: Path, out: Path):
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    problems, seen = [], set()
    if data.get("schema_version") != 1 or not data.get("task"):
        problems.append("Need schema_version: 1 and task")
    if not data.get("criteria"):
        problems.append("No evidence criteria supplied")
    for criterion in data.get("criteria", []):
        cid = criterion.get("id", "")
        if not cid or cid in seen:
            problems.append(f"Missing or duplicate criterion ID: {cid}")
        seen.add(cid)
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
    result = {"evidence_complete": not problems, "problems": problems,
              "scope": "Only the supplied evidence criteria; not an automatic design, visual or compliance judgement",
              "task": data.get("task"), "criteria": data.get("criteria", [])}
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "quality-report.json", result)
    lines = ["# Evidence review", "", result["scope"], ""]
    for c in data.get("criteria", []):
        lines += [f"- {c.get('id')}: **{c.get('status', 'pending')}** — {c.get('observation', '')}"]
    lines += ["", *[f"- ERROR: {p}" for p in problems]]
    (out / "quality-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if problems:
        raise ValueError("Quality review incomplete: " + "; ".join(problems))
    return result
