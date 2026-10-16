"""Blender-only worker for native scripts and evaluated mesh interchange."""
import argparse
import hashlib
import json
import math
import runpy
import struct
import sys
from pathlib import Path

import bpy


def normalize_glb_units(target, factor):
    """glTF exporter writes Blender coordinates, independent of scene Unit Scale.

    Add a scene-root transform in the interchange copy, preserving meshes, UVs,
    materials, object relationships and the untouched .blend master.
    """
    raw = target.read_bytes()
    magic, version, _ = struct.unpack_from('<4sII', raw)
    if magic != b'glTF' or version != 2:
        raise ValueError('Unexpected GLB header')
    size, kind = struct.unpack_from('<II', raw, 12)
    if kind != 0x4E4F534A:
        raise ValueError('GLB has no leading JSON chunk')
    doc = json.loads(raw[20:20 + size])
    nodes = doc.setdefault('nodes', [])
    for scene in doc.get('scenes', []):
        root = len(nodes)
        nodes.append({'name': 'EZarch metre conversion', 'scale': [factor] * 3, 'children': scene.get('nodes', [])})
        scene['nodes'] = [root]
    for camera in doc.get('cameras', []):
        settings = camera.get(camera['type'], {})
        for key in ('znear', 'zfar', 'xmag', 'ymag'):
            if key in settings:
                settings[key] *= factor
    for light in doc.get('extensions', {}).get('KHR_lights_punctual', {}).get('lights', []):
        if 'range' in light:
            light['range'] *= factor
    encoded = json.dumps(doc, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    encoded += b' ' * (-len(encoded) % 4)
    rest = raw[20 + size:]
    target.write_bytes(struct.pack('<4sII', b'glTF', 2, 20 + len(encoded) + len(rest)) +
                       struct.pack('<II', len(encoded), 0x4E4F534A) + encoded + rest)


def selected(obj, request):
    return ((not request.get('objects') or obj.name in request['objects']) and
            (not request.get('collections') or
             bool(set(request['collections']) & {c.name for c in obj.users_collection})))


def scale(request):
    value = request.get('unit_scale_m')
    if value is None:
        if bpy.context.scene.unit_settings.system == 'NONE':
            raise ValueError('Scene units are unspecified; supply --unit-scale-m from known dimensions')
        value = bpy.context.scene.unit_settings.scale_length
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError('unit_scale_m must be finite and positive')
    return value


def extract(request):
    factor = scale(request) * 1000
    dg = bpy.context.evaluated_depsgraph_get()
    objects, materials, omitted = [], {}, []
    counts = {}
    for inst in dg.object_instances:
        obj, original = inst.object, inst.object.original
        owner = inst.parent.original if inst.is_instance and inst.parent else original
        if not selected(owner, request) or not inst.show_self:
            continue
        if obj.type in {'EMPTY', 'CAMERA', 'LIGHT', 'ARMATURE', 'SPEAKER'}:
            continue
        if obj.type not in {'MESH', 'CURVE', 'SURFACE', 'FONT', 'META'}:
            omitted.append({'object': original.name, 'type': obj.type})
            continue
        mesh = obj.to_mesh(preserve_all_data_layers=True, depsgraph=dg)
        if mesh is None:
            omitted.append({'object': original.name, 'reason': 'no evaluated mesh'})
            continue
        try:
            mesh.calc_loop_triangles()
            if not mesh.loop_triangles:
                omitted.append({'object': original.name, 'reason': 'no surface triangles'})
                continue
            matrix = inst.matrix_world.copy()
            vertices = [list((matrix @ v.co) * factor) for v in mesh.vertices]
            # Reflected instances need reversed winding after baking their transform.
            reflected = matrix.to_3x3().determinant() < 0
            groups = {}
            for tri in mesh.loop_triangles:
                face = list(tri.vertices)
                groups.setdefault(tri.material_index, []).append(face[::-1] if reflected else face)
            base = original.name if not inst.is_instance else owner.name + '/' + original.name
            counts[base] = counts.get(base, 0) + 1
            identifier = base + (f'@{counts[base]}' if counts[base] > 1 else '')
            for material_index, faces in groups.items():
                mat = mesh.materials[material_index] if material_index < len(mesh.materials) else None
                key = mat.name if mat else '__default__'
                color, roughness, metallic = ([.65, .65, .65], .6, 0.)
                if mat:
                    color = list(mat.diffuse_color[:3])
                    if mat.use_nodes:
                        bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
                        if bsdf:
                            color = list(bsdf.inputs['Base Color'].default_value[:3])
                            roughness = bsdf.inputs['Roughness'].default_value
                            metallic = bsdf.inputs['Metallic'].default_value
                materials[key] = {'color': color, 'roughness': roughness, 'metallic': metallic}
                used = sorted({v for f in faces for v in f})
                remap = {v: i for i, v in enumerate(used)}
                verts = [vertices[i] for i in used]
                category = str(original.get('category') or (original.users_collection[0].name if original.users_collection else 'Geometry'))
                objects.append({'id': identifier + (f'/material-{material_index}' if len(groups) > 1 else ''),
                                'material': key, 'category': category, 'vertices': verts,
                                'faces': [[remap[v] for v in f] for f in faces],
                                'bounds_mm': [min(v[i] for v in verts) for i in range(3)] +
                                             [max(v[i] for v in verts) for i in range(3)],
                                'metadata': {'source_object': original.name, 'instance_owner': owner.name, 'instance_key': identifier,
                                             'collections': [c.name for c in original.users_collection]}})
        finally:
            obj.to_mesh_clear()
    if not objects:
        raise ValueError('No selected evaluated surface geometry')
    target = Path(request['target'])
    target.parent.mkdir(parents=True, exist_ok=True)
    data = {'schema_version': 1, 'units': 'mm', 'objects': objects, 'materials': materials,
            'source': request['source'], 'source_sha256': hashlib.sha256(Path(request['source']).read_bytes()).hexdigest(),
            'frame': bpy.context.scene.frame_current,
            'notes': ['Evaluated active viewport geometry; render-only modifiers/visibility can differ.',
                      'Basic material colors only in this geometry snapshot; use native GLB export for UV/PBR.'],
            'omitted': omitted}
    target.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    return {'file': str(target), 'objects': len(objects), 'triangles': sum(len(o['faces']) for o in objects),
            'omitted': omitted, 'notes': data['notes']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', required=True)
    parser.add_argument('--report', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    request = json.loads(Path(args.request).read_text(encoding='utf-8'))
    if request.get('source'):
        bpy.ops.wm.open_mainfile(filepath=request['source'], load_ui=False, use_scripts=False)
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    action = request['action']
    if action == 'run':
        script = request['script']
        sys.path.insert(0, str(Path(script).parent))
        sys.argv = [script, '--', *request.get('arguments', [])]
        runpy.run_path(script, run_name='__main__')
        if request.get('save'):
            target = Path(request['save'])
            target.parent.mkdir(parents=True, exist_ok=True)
            bpy.ops.wm.save_as_mainfile(filepath=str(target))
        result = {'script': script, 'saved': request.get('save'), 'objects': len(bpy.context.scene.objects)}
    elif action == 'extract':
        result = extract(request)
    elif action == 'glb':
        unit_scale = scale(request)
        bpy.context.scene.unit_settings.system = 'METRIC'
        bpy.context.scene.unit_settings.scale_length = unit_scale
        for obj in bpy.context.view_layer.objects:
            obj.select_set(selected(obj, request) and obj.visible_get())
        target = Path(request['target'])
        target.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.export_scene.gltf(filepath=str(target), export_format='GLB', use_selection=True,
                                  export_apply=True, export_extras=True, export_yup=True)
        if not target.is_file():
            raise RuntimeError('GLB exporter did not create output')
        if unit_scale != 1:
            normalize_glb_units(target, unit_scale)
        result = {'file': str(target), 'format': 'glb', 'bytes': target.stat().st_size,
                  'materials': 'Native Blender glTF exporter; supported PBR/UV only, no automatic shader baking'}
    else:
        raise ValueError(action)
    result['blender_version'] = bpy.app.version_string
    Path(args.report).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
