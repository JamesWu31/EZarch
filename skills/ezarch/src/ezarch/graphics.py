"""Deterministic vector composition in physical millimetres, SVG + vector PDF."""
from __future__ import annotations

import base64
import html
import math
from pathlib import Path

import pymupdf as fitz

from .project import skill_root, write_json

PT = 72 / 25.4


def rgb(value):
    if value is None or value == "none":
        return None
    if isinstance(value, str):
        value = value.lstrip("#")
        return tuple(int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return tuple(value)


class Canvas:
    """Page coordinates: x right, y down, sizes in mm; text y is the baseline."""

    def __init__(self, width, height, background="#ffffff"):
        self.width, self.height = float(width), float(height)
        self.items = []
        self.rect(0, 0, width, height, fill=background, stroke=None)

    def poly(self, points, stroke="#30332f", width=0.18, fill=None, close=False, dash=None, tag=""):
        self.items.append(dict(kind="poly", points=[list(p) for p in points], stroke=stroke,
                               width=width, fill=fill, close=close, dash=dash, tag=tag))

    def line(self, x1, y1, x2, y2, **kwargs):
        self.poly([(x1, y1), (x2, y2)], **kwargs)

    def rect(self, x, y, w, h, **kwargs):
        self.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], close=True, **kwargs)

    def circle(self, x, y, radius, **kwargs):
        self.poly([(x + radius * math.cos(i * math.tau / 64),
                    y + radius * math.sin(i * math.tau / 64)) for i in range(64)], close=True, **kwargs)

    def text(self, x, y, text, size=3.0, color="#30332f", align="left", bold=False, tag="", rotation=0):
        if rotation not in (0, 90, 180, 270):
            raise ValueError("Text rotation must be a multiple of 90 degrees")
        self.items.append(dict(kind="text", x=x, y=y, text=str(text), size=size, color=color,
                               align=align, bold=bold, tag=tag, rotation=rotation))

    def image(self, path, x, y, w, h):
        self.items.append(dict(kind="image", path=str(Path(path).resolve()), x=x, y=y, w=w, h=h))

    def text_box(self, x, y, w, h, text, size=3, leading=None, **kwargs):
        """Measured wrapping for mixed CJK/Latin text; reject overflow, never shrink."""
        leading = leading or size * 1.55
        font = fitz.Font(fontfile=str(skill_root() / "assets/fonts/EZarchFang.ttf"))
        latin = fitz.Font("hebo" if kwargs.get("bold") else "helv")
        def width(value):
            primary = font if any(ord(c) > 255 for c in value) else latin
            return sum((primary if primary.has_glyph(ord(c)) else latin)
                       .text_length(c, fontsize=size) for c in value)
        lines = []
        for paragraph in str(text).split("\n"):
            line = ""
            for char in paragraph:
                if width(line + char) > w and line:
                    # Prefer an existing Latin word boundary when possible.
                    split = line.rfind(" ")
                    if char.isascii() and char.isalnum() and split > len(line) / 2:
                        lines.append(line[:split])
                        line = line[split + 1:] + char
                    else:
                        lines.append(line.rstrip())
                        line = char.lstrip()
                else:
                    line += char
            lines.append(line)
        used = size + max(0, len(lines) - 1) * leading
        if used > h + .01 or any(width(line) > w + .01 for line in lines):
            raise ValueError(f"Text box overflow: {str(text)[:50]}")
        for i, line in enumerate(lines):
            self.text(x, y + size + i * leading, line, size=size, **kwargs)
        return {"lines": len(lines), "used_height_mm": used}

    def pdf(self, path, x, y, w, h, page=0):
        self.items.append(dict(kind="pdf", path=str(Path(path).resolve()), x=x, y=y, w=w, h=h,
                               page=page))

    def save(self, stem: Path, dpi=120, metadata=None):
        stem.parent.mkdir(parents=True, exist_ok=True)
        font_path = skill_root() / "assets/fonts/EZarchFang.ttf"
        if not font_path.exists():
            raise FileNotFoundError(f"Bundled FangSong font missing: {font_path}")
        cjk_font = fitz.Font(fontfile=str(font_path))
        regular_font, bold_font = fitz.Font("helv"), fitz.Font("hebo")
        doc = fitz.open()
        page = doc.new_page(width=self.width * PT, height=self.height * PT)
        page.insert_font(fontname="FangSong", fontfile=str(font_path)) if font_path.exists() else None
        # Embed MuPDF's supplied Latin outlines too: PDF viewers otherwise choose
        # different system substitutes for the unembedded Base-14 fonts.
        page.insert_font(fontname="EZLatin", fontbuffer=regular_font.buffer)
        page.insert_font(fontname="EZBold", fontbuffer=bold_font.buffer)
        svg = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
               f'width="{self.width}mm" height="{self.height}mm" viewBox="0 0 {self.width} {self.height}">']
        if font_path.exists():
            encoded = base64.b64encode(font_path.read_bytes()).decode()
            svg.append('<defs><style>@font-face{font-family:FandolFang;src:url(data:font/ttf;base64,'
                       + encoded + ')}</style></defs>')
        overflow, geometry_overflow = [], []
        # Batch adjacent paths: committing each triangle makes MuPDF rescan growing page streams.
        # Flush at text/media boundaries to preserve painter order.
        path_batch = None
        for item in self.items:
            k = item["kind"]
            if k != "poly" and path_batch is not None:
                path_batch.commit()
                path_batch = None
            if k == "poly":
                points = item["points"]
                if len(points) < 2:
                    continue
                if any(x < -.1 or x > self.width + .1 or y < -.1 or y > self.height + .1 for x, y in points):
                    geometry_overflow.append({"bounds_mm": [min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)]})
                if path_batch is None:
                    path_batch = page.new_shape()
                sh = path_batch
                sh.draw_polyline([fitz.Point(x * PT, y * PT) for x, y in points])
                dashes = None if not item["dash"] else "[" + " ".join(str(v * PT) for v in item["dash"]) + "] 0"
                sh.finish(color=rgb(item["stroke"]), fill=rgb(item["fill"]),
                          width=item["width"] * PT, closePath=item["close"], dashes=dashes)
                tag = "polygon" if item["close"] else "polyline"
                dash_attr = '' if not item["dash"] else f' stroke-dasharray="{",".join(map(str, item["dash"]))}"'
                svg.append(f'<{tag} points="' + " ".join(f"{x:.5f},{y:.5f}" for x, y in points)
                           + f'" fill="{item["fill"] or "none"}" stroke="{item["stroke"] or "none"}" '
                             f'stroke-width="{item["width"]}" stroke-linejoin="round"{dash_attr}/>')
            elif k == "text":
                text = item["text"]
                cjk = any(ord(c) > 255 for c in text)
                font = cjk_font if cjk else bold_font if item["bold"] else regular_font
                fontname = "FangSong" if cjk else "EZBold" if item["bold"] else "EZLatin"
                runs = []
                for char in text:
                    if font.has_glyph(ord(char)):
                        run_font, run_name = font, fontname
                    elif regular_font.has_glyph(ord(char)):
                        run_font, run_name = regular_font, "EZLatin"
                    else:
                        raise ValueError(f"No bundled font glyph for {char!r} (U+{ord(char):04X}); choose an appropriate project font")
                    if runs and runs[-1][0] == run_name:
                        runs[-1][2] += char
                    else:
                        runs.append([run_name, run_font, char])
                length = sum(f.text_length(t, fontsize=item["size"]) for _, f, t in runs)
                angle = math.radians(item["rotation"])
                offset = length / 2 if item["align"] == "center" else length if item["align"] == "right" else 0
                x, y = item["x"] - offset * math.cos(angle), item["y"] + offset * math.sin(angle)
                corners = [(x + u * math.cos(angle) + v * math.sin(angle), y - u * math.sin(angle) + v * math.cos(angle)) for u in (0, length) for v in (-item["size"], 0)]
                bounds = [min(p[0] for p in corners), min(p[1] for p in corners), max(p[0] for p in corners), max(p[1] for p in corners)]
                if bounds[0] < -.1 or bounds[2] > self.width + .1 or bounds[3] > self.height + .1 or bounds[1] < -.1:
                    overflow.append({"text": text, "box_mm": bounds})
                advance = 0
                for run_name, run_font, run_text in runs:
                    page.insert_text(((x + advance * math.cos(angle)) * PT, (y - advance * math.sin(angle)) * PT),
                                     run_text, fontsize=item["size"] * PT, fontname=run_name,
                                     color=rgb(item["color"]), rotate=item["rotation"])
                    advance += run_font.text_length(run_text, fontsize=item["size"])
                anchor = {"left": "start", "center": "middle", "right": "end"}[item["align"]]
                family = "FandolFang, Helvetica, Arial, serif" if cjk else "Helvetica, Arial, sans-serif"
                svg.append(f'<text x="{item["x"]}" y="{item["y"]}" transform="rotate({-item["rotation"]} {item["x"]} {item["y"]})" font-size="{item["size"]}" '
                           f'font-family="{family}" font-weight="{"bold" if item["bold"] else "normal"}" '
                           f'text-anchor="{anchor}" fill="{item["color"]}">{html.escape(text)}</text>')
            elif k in ("image", "pdf"):
                rect = fitz.Rect(item["x"] * PT, item["y"] * PT,
                                 (item["x"] + item["w"]) * PT, (item["y"] + item["h"]) * PT)
                if k == "image":
                    page.insert_image(rect, filename=item["path"], keep_proportion=True)
                    encoded = base64.b64encode(Path(item["path"]).read_bytes()).decode()
                    mime = "image/jpeg" if Path(item["path"]).suffix.lower() in (".jpg", ".jpeg") else "image/png"
                    svg.append(f'<image x="{item["x"]}" y="{item["y"]}" width="{item["w"]}" '
                               f'height="{item["h"]}" preserveAspectRatio="xMidYMid meet" '
                               f'xlink:href="data:{mime};base64,{encoded}"/>')
                else:
                    with fitz.open(item["path"]) as source:
                        source_page = source[item["page"]]
                        page.show_pdf_page(rect, source, pno=item["page"], keep_proportion=True)
                        raw_svg = source_page.get_svg_image(text_as_path=True)
                        # Nest the source SVG to preserve vector content and its own viewBox.
                        raw_svg = raw_svg.replace('<svg ', f'<svg x="{item["x"]}" y="{item["y"]}" ', 1)
                        import re
                        raw_svg = re.sub(r'width="[^"]+"', f'width="{item["w"]}"', raw_svg, count=1)
                        raw_svg = re.sub(r'height="[^"]+"', f'height="{item["h"]}"', raw_svg, count=1)
                        # Each imported PDF has its own IDs; namespace them across the board.
                        prefix = f"slot{len(svg)}_"
                        ids = re.findall(r'\bid="([^"]+)"', raw_svg)
                        for ident in sorted(set(ids), key=len, reverse=True):
                            raw_svg = raw_svg.replace(f'id="{ident}"', f'id="{prefix}{ident}"')
                            raw_svg = raw_svg.replace(f'#{ident}"', f'#{prefix}{ident}"').replace(f'#{ident})', f'#{prefix}{ident})')
                        svg.append(raw_svg)
        if path_batch is not None:
            path_batch.commit()
        svg.append("</svg>")
        stem.with_suffix(".svg").write_text("\n".join(svg), encoding="utf-8")
        doc.set_metadata({"title": (metadata or {}).get("title", stem.stem), "producer": "EZarch"})
        doc.subset_fonts()
        doc.save(str(stem.with_suffix(".pdf")), garbage=4, deflate=True)
        page.get_pixmap(dpi=dpi, alpha=False).save(str(stem.with_suffix(".png")))
        report = {"width_mm": self.width, "height_mm": self.height, "text_overflow": overflow,
                  "geometry_overflow": geometry_overflow,
                  "vector_paths": len(page.get_drawings()), "images": len(page.get_images()),
                  "metadata": metadata or {}}
        write_json(stem.with_suffix(".report.json"), report)
        doc.close()
        return report
