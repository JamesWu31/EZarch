"""Editable architectural linework and paper-sized symbols, independent of 3D.

Geometry is world millimetres, Y up. Pen widths, text and symbol sizes are paper
millimetres. Helpers implement a documented drawing convention, not code approval.
"""
from __future__ import annotations

import math
from pathlib import Path

import ezdxf
import yaml
from ezdxf.enums import TextEntityAlignment

from .graphics import Canvas
from .project import skill_root, write_json

INK = "#26312e"
PENS = yaml.safe_load((skill_root() / "assets/drafting/china-conventions.yml").read_text(encoding="utf-8"))["pens_mm"]


class Drawing:
    def __init__(self, bounds, scale=100, title="", number="", margin=12):
        if scale <= 0 or len(bounds) != 4 or bounds[2] <= bounds[0] or bounds[3] <= bounds[1]:
            raise ValueError("Positive scale and valid drawing bounds required")
        self.bounds, self.scale, self.margin = list(bounds), float(scale), float(margin)
        self.title, self.number = title, number
        self.width = (bounds[2] - bounds[0]) / scale + margin * 2
        self.height = (bounds[3] - bounds[1]) / scale + margin * 2 + 19
        self.canvas = Canvas(self.width, self.height)
        self.doc = ezdxf.new("R2010")
        self.doc.units = ezdxf.units.MM
        self.doc.header["$MEASUREMENT"] = 1
        self.doc.styles.new("EZARCH", dxfattribs={"font": "EZarchFang.ttf"})
        self.doc.linetypes.new("EZ-GRID", dxfattribs={"description": "Axis centre line",
                               "pattern": [16 * scale, 10 * scale, -2 * scale, 2 * scale, -2 * scale]})
        for name, pen in PENS.items():
            self.doc.layers.new(name, dxfattribs={"color": 7, "lineweight": round(pen * 100)})
        self.ms = self.doc.modelspace()
        self.dimensions, self.symbols = [], []

    def paper(self, p):
        return [self.margin + (p[0] - self.bounds[0]) / self.scale,
                self.margin + (self.bounds[3] - p[1]) / self.scale]

    def poly(self, points, layer="A-VISIBLE", close=False, fill=None, color=INK, width=None, dash=None):
        points = [list(p) for p in points]
        if len(points) < 2:
            return
        self.canvas.poly([self.paper(p) for p in points], close=close, fill=fill,
                         stroke=color, width=width if width is not None else PENS[layer], dash=dash)
        attrs = {"layer": layer}
        if dash:
            attrs["linetype"] = "EZ-GRID"
        self.ms.add_lwpolyline(points, close=close, dxfattribs=attrs)
        if fill and close:
            hatch = self.ms.add_hatch(color=7, dxfattribs={"layer": layer})
            hatch.paths.add_polyline_path(points, is_closed=True)

    def line(self, a, b, **kw):
        self.poly([a, b], **kw)

    def rect(self, x, y, w, h, **kw):
        self.poly([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], close=True, **kw)

    def circle(self, centre, radius, layer="A-ANNOTATION", color=INK, width=None):
        x, y = self.paper(centre)
        self.canvas.circle(x, y, radius / self.scale, stroke=color, width=width or PENS[layer])
        self.ms.add_circle(centre, radius, dxfattribs={"layer": layer})

    def text(self, point, text, size=2.5, align="center", color=INK, rotation=0, layer="A-ANNOTATION"):
        x, y = self.paper(point)
        self.canvas.text(x, y + (size * .32 if not rotation else 0), text, size=size,
                         align=align, color=color, rotation=rotation)
        alignment = {"left": TextEntityAlignment.MIDDLE_LEFT, "center": TextEntityAlignment.MIDDLE_CENTER,
                     "right": TextEntityAlignment.MIDDLE_RIGHT}[align]
        self.ms.add_text(str(text), dxfattribs={"height": size * self.scale, "style": "EZARCH",
                         "layer": layer, "rotation": rotation}).set_placement(point, align=alignment)

    def axis(self, name, orientation, at, start, end, bubbles="both"):
        if str(name) in {"I", "O", "Z"}:
            raise ValueError("I, O and Z are not used as Chinese drawing grid labels")
        s = self.scale
        if orientation == "x":  # constant x, vertical line
            a, b = [at, start], [at, end]
        elif orientation == "y":
            a, b = [start, at], [end, at]
        else:
            raise ValueError("Axis orientation x or y required")
        self.line(a, b, layer="A-GRID", color="#929996", dash=[10, 2, 2, 2])
        for p, end_name in [(a, "start"), (b, "end")]:
            if bubbles in ("both", end_name):
                self.circle(p, 4 * s)
                self.text(p, name, 3.5)
        self.symbols.append({"kind": "axis", "name": name, "orientation": orientation, "at_mm": at})

    def dimension(self, a, b, base, text_size=2.5):
        s = self.scale
        if abs(a[1] - b[1]) < .001:
            angle, aa, bb = 0, [a[0], base[1]], [b[0], base[1]]
            text_at, rot = [(a[0] + b[0]) / 2, base[1] + 1.8 * s], 0
        elif abs(a[0] - b[0]) < .001:
            angle, aa, bb = 90, [base[0], a[1]], [base[0], b[1]]
            text_at, rot = [base[0] - 1.8 * s, (a[1] + b[1]) / 2], 90
        else:
            raise ValueError("Use ezdxf adapter for non-orthogonal dimensions")
        for p, q in [(a, aa), (b, bb)]:
            v = [q[i] - p[i] for i in range(2)]
            length = math.hypot(*v)
            if length:
                unit = [c / length for c in v]
                self.canvas.poly([self.paper([p[i] + unit[i] * 2 * s for i in range(2)]),
                                  self.paper([q[i] + unit[i] * 2 * s for i in range(2)])], width=.13)
        self.canvas.poly([self.paper(aa), self.paper(bb)], width=.13)
        for p in [aa, bb]:
            self.canvas.poly([self.paper([p[0] - s, p[1] - s]), self.paper([p[0] + s, p[1] + s])], width=.25)
        value = math.dist(a, b)
        x, y = self.paper(text_at)
        self.canvas.text(x, y, f"{value:.0f}", size=text_size, align="center", rotation=rot)
        dimension = self.ms.add_linear_dim(base=base, p1=a, p2=b, angle=angle, override={
            "dimtxt": text_size * s, "dimasz": 2 * s, "dimexo": 2 * s,
            "dimexe": 2 * s, "dimdec": 0, "dimtad": 1, "dimblk": "ARCHTICK", "dimtxsty": "EZARCH"},
            dxfattribs={"layer": "A-DIM"})
        dimension.render()
        self.dimensions.append({"p1": a, "p2": b, "base": base, "measured_mm": value})

    def chain(self, values, fixed, base, orientation="x"):
        for a, b in zip(values, values[1:]):
            if orientation == "x":
                self.dimension([a, fixed], [b, fixed], [0, base])
            elif orientation == "y":
                self.dimension([fixed, a], [fixed, b], [base, 0])
            else:
                raise ValueError("Chain orientation x or y required")

    def level(self, point, value_mm, size=3, label=None):
        x, y = point
        u = size * self.scale
        self.poly([[x, y], [x - u, y + u], [x + u, y + u]], close=True, layer="A-ANNOTATION")
        self.line([x - u, y + u], [x + 5 * u, y + u], layer="A-ANNOTATION")
        value = label or ("±0.000" if abs(value_mm) < .001 else f"{value_mm / 1000:.3f}")
        self.text([x + 2 * u, y + u + 1.8 * self.scale], value, 2.5)
        self.symbols.append({"kind": "level", "value_mm": value_mm, "at": point})

    def north(self, point, angle=0):
        s = self.scale
        a = math.radians(angle)
        def p(x, y):
            return [point[0] + s * (x * math.cos(a) - y * math.sin(a)),
                    point[1] + s * (x * math.sin(a) + y * math.cos(a))]
        self.circle(point, 12 * s)
        self.poly([p(0, 12), p(-1.5, -9), p(0, -6)], close=True, fill=INK, layer="A-ANNOTATION")
        self.poly([p(0, 12), p(1.5, -9), p(0, -6)], close=True, layer="A-ANNOTATION")
        self.text(p(0, 16), "N", 3.5)
        self.symbols.append({"kind": "north", "angle": angle})

    def section_mark(self, a, b, name, direction=1):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        if length <= 0:
            raise ValueError("Section endpoints must differ")
        t, n, s = [dx / length, dy / length], [-dy / length * direction, dx / length * direction], self.scale
        for p, sign in [(a, 1), (b, -1)]:
            self.line(p, [p[i] + t[i] * sign * 7 * s for i in range(2)], layer="A-CUT")
            self.line(p, [p[i] + n[i] * 5 * s for i in range(2)], layer="A-CUT")
            self.text([p[i] + n[i] * 8 * s for i in range(2)], name, 3.5)
        self.symbols.append({"kind": "section", "name": name, "a": a, "b": b, "direction": direction})

    def index(self, point, detail, sheet, radius=5):
        x, y = point
        r = radius * self.scale
        self.circle(point, r)
        self.line([x - r, y], [x + r, y], layer="A-ANNOTATION")
        self.text([x, y + r * .45], detail, 2.5)
        self.text([x, y - r * .45], sheet, 2.5)
        self.symbols.append({"kind": "index", "detail": detail, "sheet": sheet})

    def leader(self, points, text, size=3):
        self.poly(points, layer="A-ANNOTATION")
        self.circle(points[0], .5 * self.scale, width=.2)
        self.text([points[-1][0], points[-1][1] + 1.8 * self.scale], text, size, align="left")

    def furniture(self, kind, origin, size, rotation=0):
        """Ordinary simplified symbols, NOT prescribed national-standard furniture."""
        w, d = size
        if min(w, d) <= 0:
            raise ValueError("Furniture footprint must be positive")
        a = math.radians(rotation)
        def world(p):
            return [origin[0] + p[0] * math.cos(a) - p[1] * math.sin(a),
                    origin[1] + p[0] * math.sin(a) + p[1] * math.cos(a)]
        def line(pts, close=False):
            self.poly([world(p) for p in pts], layer="A-FURNITURE", close=close)
        def rect(x, y, ww, dd):
            line([[x, y], [x + ww, y], [x + ww, y + dd], [x, y + dd]], True)
        rect(0, 0, w, d)
        if kind in {"chair", "sofa"}:
            rect(w * .07, d * .07, w * .86, d * .67)
            line([[0, d * .8], [w, d * .8]])
            if kind == "sofa":
                for f in (1/3, 2/3):
                    line([[w * f, d * .08], [w * f, d * .74]])
        elif kind == "bed":
            rect(w * .07, d * .7, w * .38, d * .22)
            rect(w * .55, d * .7, w * .38, d * .22)
            line([[0, d * .62], [w, d * .62]])
        elif kind in {"cabinet", "shelf"}:
            for i in range(1, max(2, round(w / 600))):
                f = i / max(2, round(w / 600))
                line([[w * f, 0], [w * f, d]])
        elif kind in {"sink", "wc"}:
            line([[w * (.5 + .32 * math.cos(t)), d * (.5 + .36 * math.sin(t))]
                  for t in [i * math.tau / 48 for i in range(48)]], True)
            if kind == "wc":
                rect(w * .08, d * .77, w * .84, d * .2)
        elif kind == "shower":
            line([[0, 0], [w, d]])
            line([[w, 0], [0, d]])
        elif kind not in {"table", "counter", "equipment"}:
            raise ValueError(f"Unknown furniture symbol {kind}; add a project-local custom symbol")
        self.symbols.append({"kind": "furniture", "type": kind, "origin": origin,
                             "size": size, "rotation": rotation})

    def save(self, stem: Path, dpi=150, metadata=None):
        import shutil
        font_dir = stem.parent / "fonts"
        font_dir.mkdir(parents=True, exist_ok=True)
        for filename in ["EZarchFang.ttf", "COPYING", "SOURCE.md"]:
            shutil.copy2(skill_root() / "assets/fonts" / filename, font_dir / filename)
        y = self.height - 13
        self.canvas.line(self.margin, y - 5, self.width - self.margin, y - 5, width=.18)
        self.canvas.text(self.margin, y, f"{self.number}  {self.title}", size=4)
        self.canvas.text(self.width - self.margin, y, f"1:{self.scale:g} / mm", size=2.5, align="right")
        bar_model = min(5000, max(100, math.floor((self.width - 2 * self.margin) * self.scale / 500) * 100))
        length = bar_model / self.scale
        for i in range(4):
            self.canvas.rect(self.margin + i * length / 4, y + 4, length / 4, 1,
                             fill=INK if i % 2 == 0 else "#ffffff", width=.13)
        self.canvas.text(self.margin + length + 2, y + 5.5, f"{bar_model / 1000:g} m", size=2.5)
        meta = {**(metadata or {}), "title": self.title, "scale": self.scale, "dimensions": self.dimensions,
                "symbols": self.symbols, "scale_bar_model_mm": bar_model, "scale_bar_paper_mm": length}
        report = self.canvas.save(stem, dpi=dpi, metadata=meta)
        if self.doc.audit().has_errors:
            raise ValueError("Invalid DXF")
        self.doc.set_modelspace_vport(height=self.bounds[3] - self.bounds[1],
            center=((self.bounds[0] + self.bounds[2]) / 2, (self.bounds[1] + self.bounds[3]) / 2))
        self.doc.saveas(stem.with_suffix(".dxf"))
        write_json(stem.with_suffix(".draft.json"), meta)
        return report
