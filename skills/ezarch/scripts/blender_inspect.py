"""Bounded scene metadata from Blender, without running embedded file scripts."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

p = argparse.ArgumentParser()
p.add_argument('--source', required=True)
p.add_argument('--out', required=True)
a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
bpy.ops.wm.open_mainfile(filepath=a.source, load_ui=False, use_scripts=False)
dg = bpy.context.evaluated_depsgraph_get()
objects = []
for obj in bpy.data.objects:
    evaluated = obj.evaluated_get(dg)
    local_bounds = list(evaluated.bound_box)
    corners = [evaluated.matrix_world @ Vector(v) for v in local_bounds] if any(tuple(v) != (-1, -1, -1) for v in local_bounds) else []
    objects.append({'id': obj.name, 'type': obj.type, 'data': obj.data.name if obj.data else None,
                    'collections': [c.name for c in obj.users_collection],
                    'matrix_world': [list(row) for row in evaluated.matrix_world],
                    'bounds': ([min(v[i] for v in corners) for i in range(3)] + [max(v[i] for v in corners) for i in range(3)]) if corners else None,
                    'modifiers': [{'name': m.name, 'type': m.type, 'viewport': m.show_viewport, 'render': m.show_render} for m in obj.modifiers],
                    'materials': [s.material.name if s.material else None for s in obj.material_slots],
                    'hide_render': obj.hide_render, 'hide_viewport': obj.hide_viewport,
                    'original_vertices': len(obj.data.vertices) if obj.type == 'MESH' else None,
                    'evaluated_vertices': len(evaluated.data.vertices) if evaluated.type == 'MESH' else None})
instances = [{'object': i.object.original.name, 'parent': i.parent.original.name if i.parent else None,
              'matrix_world': [list(row) for row in i.matrix_world]} for i in dg.object_instances if i.is_instance]
dependencies = [{'path': im.filepath, 'packed': bool(im.packed_file),
                 'exists': Path(bpy.path.abspath(im.filepath)).exists()} for im in bpy.data.images if im.filepath]
result = {'objects': objects, 'instances': instances, 'dependencies': dependencies,
          'units': {'system': bpy.context.scene.unit_settings.system, 'scale_length_m': bpy.context.scene.unit_settings.scale_length},
          'frame': bpy.context.scene.frame_current, 'camera': bpy.context.scene.camera.name if bpy.context.scene.camera else None,
          'source_sha256': hashlib.sha256(Path(a.source).read_bytes()).hexdigest(),
          'warnings': ['Bounds/vertex counts use evaluated viewport dependency graph at current frame. Render modifiers may differ. Names are file-version-bound; linked libraries and shared mesh data need deliberate editing.']}
Path(a.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
