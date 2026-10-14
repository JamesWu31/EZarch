"""Run inside Blender: move one named object and save a copy without restyling the scene."""
import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--input', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--object', required=True)
p.add_argument('--move', type=float, nargs=3, required=True, help='World offset in Blender scene units')
a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
if a.input.resolve() == a.output.resolve():
    raise ValueError('This example saves a separate edited copy')
bpy.ops.wm.open_mainfile(filepath=str(a.input.resolve()))
obj = bpy.data.objects[a.object]
matrix = obj.matrix_world.copy()
matrix.translation += Vector(a.move)
obj.matrix_world = matrix
a.output.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(a.output.resolve()))
