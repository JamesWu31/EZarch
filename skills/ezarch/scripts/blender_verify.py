"""Read a saved BLEND and measure stored source meshes; never renders or writes it."""
import argparse
import json
import sys
from pathlib import Path

import bpy

parser = argparse.ArgumentParser()
parser.add_argument('--input', required=True)
parser.add_argument('--report', required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
bpy.ops.wm.open_mainfile(filepath=args.input)
records = []
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH' or 'ezarch_id' not in obj:
        continue
    points = [obj.matrix_world @ v.co for v in obj.data.vertices]
    lo = [min(p[i] for p in points) * 1000 for i in range(3)]
    hi = [max(p[i] for p in points) * 1000 for i in range(3)]
    records.append({'id': obj['ezarch_id'], 'bounds_mm': lo + hi})
Path(args.report).write_text(json.dumps(records, indent=2), encoding='utf-8')
