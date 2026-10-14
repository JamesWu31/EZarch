"""Read a saved BLEND and measure stored source meshes; never renders or writes it."""
import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

parser = argparse.ArgumentParser()
parser.add_argument('--input', required=True)
parser.add_argument('--report', required=True)
parser.add_argument('--asset-report')
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

if args.asset_report:
    instances = []
    for root in bpy.context.scene.objects:
        if root.instance_type != 'COLLECTION' or not root.instance_collection:
            continue
        points = [root.matrix_world @ obj.matrix_world @ Vector(p)
                  for obj in root.instance_collection.all_objects if obj.type == 'MESH'
                  for p in obj.bound_box]
        if points:
            instances.append({'id': root.name, 'bounds_mm':
                [min(p[i] for p in points) * 1000 for i in range(3)] +
                [max(p[i] for p in points) * 1000 for i in range(3)]})
    images = [{'name': image.name, 'packed': bool(image.packed_file or len(image.packed_files))}
              for image in bpy.data.images if image.source in {'FILE', 'TILED'}]
    Path(args.asset_report).write_text(json.dumps({'instances': instances, 'images': images,
        'all_images_packed': all(image['packed'] for image in images)}, indent=2), encoding='utf-8')
