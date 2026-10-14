"""Native ezdxf example: edit selected entities, retain the document, optionally plot in mm.

Copy/adapt this small operation for the task; it is not a building template.
"""
import argparse
import math
from pathlib import Path

import ezdxf


def plot(doc, output, scale):
    from ezdxf.addons.drawing import Frontend, RenderContext, layout, pymupdf
    from ezdxf.addons.drawing.config import BackgroundPolicy, Configuration
    if scale <= 0 or doc.units == 0:
        raise ValueError("Plotting needs a positive scale and known source units")
    backend = pymupdf.PyMuPdfBackend()
    Frontend(RenderContext(doc), backend, config=Configuration(background_policy=BackgroundPolicy.WHITE)).draw_layout(doc.modelspace())
    bounds = backend.player().bbox()
    if not bounds.has_data:
        raise ValueError('No visible geometry to plot; inspect entities, layers and the selected plane')
    factor = ezdxf.units.conversion_factor(doc.units, ezdxf.units.MM) / scale
    # ezdxf 1.4.4 rounds the final page to 0.1 mm, then truncates to integer PDF
    # points. Compensate that coordinate mapping without changing the source DXF.
    pt = 72 / 25.4
    width, height = [math.ceil((v * factor + 20) * 10) / 10 for v in bounds.size]
    page = layout.Page(width, height, margins=layout.Margins.all(10))
    correction = max(width, height) * pt / pymupdf.get_coordinate_output_space(page)
    output.write_bytes(backend.get_pdf_bytes(page,
                                           settings=layout.Settings(scale=factor * correction, fit_page=False)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--handle', required=True)
    p.add_argument('--move', type=float, nargs=2)
    p.add_argument('--text')
    p.add_argument('--pdf', type=Path)
    p.add_argument('--scale', type=float, default=100)
    a = p.parse_args()
    if a.input.resolve() == a.output.resolve():
        raise ValueError("This example saves a separate edited copy")
    doc = ezdxf.readfile(a.input)
    entity = doc.entitydb[a.handle]
    if a.move:
        entity.translate(*a.move, 0)
    if a.text is not None:
        if entity.dxftype() not in {'TEXT', 'MTEXT'}:
            raise ValueError("Select a TEXT or MTEXT handle for text edits")
        if entity.dxftype() == 'TEXT':
            entity.dxf.text = a.text
        else:
            entity.text = a.text
    a.output.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(a.output)
    if a.pdf:
        a.pdf.parent.mkdir(parents=True, exist_ok=True)
        plot(doc, a.pdf, a.scale)


if __name__ == '__main__':
    main()
