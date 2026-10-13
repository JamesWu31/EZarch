"""Standalone board composition from arbitrary PDF/images and a physical template."""
import hashlib
from pathlib import Path

import pymupdf as fitz
import yaml
from PIL import Image

from .graphics import Canvas
from .project import write_json


def compose(template: Path, out: Path):
    data = yaml.safe_load(template.read_text(encoding="utf-8"))
    out.mkdir(parents=True, exist_ok=True)
    reports = []
    final = fitz.open()
    for i, sheet in enumerate(data["sheets"]):
        width, height = sheet.get("size_mm", [594, 841])
        canvas = Canvas(width, height, sheet.get("background", "#ffffff"))
        slots, image_checks = [], []
        for item in sheet["items"]:
            kind = item["type"]
            x, y = item["x"], item["y"]
            if kind == "text":
                lines = str(item["text"]).split("\n")
                size = item.get("size", 3)
                for n, line in enumerate(lines):
                    canvas.text(x, y + n * item.get("leading", size * 1.55), line, size=size,
                                color=item.get("color", "#343930"), bold=item.get("bold", False),
                                align=item.get("align", "left"))
                continue
            if kind == "line":
                canvas.line(x, y, item["x2"], item["y2"], stroke=item.get("color", "#a7ad9f"), width=item.get("width", .2))
                continue
            w, h = item["w"], item["h"]
            if x < 0 or y < 0 or x + w > width + .01 or y + h > height + .01:
                raise ValueError(f"Board slot exceeds physical page: {item.get('id', kind)}")
            if kind == "rect":
                canvas.rect(x, y, w, h, fill=item.get("fill", "#f1f0e8"), stroke=item.get("stroke"))
                continue
            source = (template.parent / item["file"]).resolve()
            if not source.is_file():
                raise FileNotFoundError(source)
            slot = {"id": item.get("id", source.stem), "file": str(source), "rect_mm": [x, y, w, h],
                    "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
            for previous in slots:
                px, py, pw, ph = previous["rect_mm"]
                if not item.get("allow_overlap", False) and min(x + w, px + pw) - max(x, px) > .01 and min(y + h, py + ph) - max(y, py) > .01:
                    raise ValueError(f"Board content slots overlap: {slot['id']} / {previous['id']}")
            if kind == "pdf":
                with fitz.open(source) as doc:
                    pg = doc[item.get("page", 0)]
                    pw, ph = pg.rect.width * 25.4 / 72, pg.rect.height * 25.4 / 72
                fit = min(w / pw, h / ph)
                slot["source_scale_factor"] = fit
                if item.get("scale_lock", False) and abs(fit - 1) > .0001:
                    raise ValueError(f"Scaled drawing would change scale in slot {slot['id']}: factor {fit}")
                canvas.pdf(source, x, y, w, h, item.get("page", 0))
            elif kind == "image":
                with Image.open(source) as image:
                    iw, ih = image.size
                factor = min(w / iw, h / ih)
                effective_ppi = 25.4 / factor
                check = {"id": slot["id"], "effective_ppi": round(effective_ppi, 2),
                         "minimum_ppi": item.get("minimum_ppi", 100)}
                image_checks.append(check)
                if effective_ppi < check["minimum_ppi"]:
                    raise ValueError(f"Image resolution too low for {slot['id']}: {effective_ppi:.1f} PPI")
                canvas.image(source, x, y, w, h)
            else:
                raise ValueError(f"Unsupported board content type {kind}")
            slots.append(slot)
        stem = out / f"board-{i + 1:02d}"
        report = canvas.save(stem, dpi=data.get("preview_dpi", 100), metadata={"title": sheet.get("title", data.get("title", "EZarch"))})
        report.update(slots=slots, image_checks=image_checks)
        if report["text_overflow"]:
            raise ValueError(f"Board text overflow: {report['text_overflow']}")
        if report["geometry_overflow"]:
            raise ValueError("Board linework extends beyond the page")
        with fitz.open(stem.with_suffix(".pdf")) as page_pdf:
            final.insert_pdf(page_pdf)
        reports.append(report)
    final.save(out / "presentation.pdf", garbage=4, deflate=True)
    final.close()
    write_json(out / "board-report.json", reports)
    return {"pages": len(reports), "pdf": "presentation.pdf", "sheets": reports}
