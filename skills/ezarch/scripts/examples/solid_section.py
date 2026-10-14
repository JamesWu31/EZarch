"""Native CadQuery example: loft, subtract an opening, export STEP and a true section.

The specimen demonstrates operations, not a prescribed architectural form.
"""
import argparse
from pathlib import Path

import cadquery as cq


def build(width, depth, height):
    shape = (cq.Workplane('XY').ellipse(width / 2, depth / 2)
             .workplane(offset=height).ellipse(width * .38, depth * .34).loft())
    void = cq.Workplane('XY').box(width * .24, depth * 2, height * .65, centered=(True, True, False))
    return shape.cut(void)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--width', type=float, default=6000)
    p.add_argument('--depth', type=float, default=4000)
    p.add_argument('--height', type=float, default=3000)
    p.add_argument('--cut-z', type=float, default=1200)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    model = build(a.width, a.depth, a.height)
    if not model.val().isValid():
        raise ValueError('Invalid solid')
    cq.exporters.export(model, str(a.out / 'solid.step'))
    # loft leaves the workplane at its upper profile; section height here is world Z.
    section = cq.Workplane('XY').newObject([model.val()]).section(a.cut_z)
    if not section.val().Edges():
        raise ValueError('The selected cut plane does not intersect the solid')
    cq.exporters.export(section, str(a.out / 'section.dxf'))


if __name__ == '__main__':
    main()
