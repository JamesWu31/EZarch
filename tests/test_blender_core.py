"""Synthetic geometry regressions, not design templates or visual examples."""
import json
import os
from pathlib import Path

import numpy as np
import pytest
from ezarch.mesh_views import extract_mesh_view, save_mesh_view


def mesh_object(name, size, center):
    import trimesh
    mesh = trimesh.creation.box(size)
    mesh.apply_translation(center)
    return {'id': name, 'vertices': mesh.vertices.tolist(), 'faces': mesh.faces.tolist(), 'category': 'wall', 'material': 'm'}


def scene(*objects):
    return {'schema_version': 1, 'units': 'mm', 'objects': list(objects), 'materials': {'m': {'color': [.5, .5, .5]}}}


def test_mesh_plan_sections_match_dimensions_and_pdf_scale(tmp_path):
    import ezdxf
    import pymupdf
    data = scene(mesh_object('wall', [6000, 300, 3000], [3000, 150, 1500]))
    spec = {'id': 'cut', 'kind': 'plan', 'cut_z': 1200, 'scale': 100}
    view = extract_mesh_view(data, spec)
    assert sum(c['area_mm2'] for c in view['cuts']) == pytest.approx(1800000)
    assert view['warnings'] == []
    save_mesh_view(data, spec, tmp_path, ['dxf', 'pdf'])
    doc = ezdxf.readfile(tmp_path / 'cut.dxf')
    assert doc.units == 4
    paths = doc.modelspace().query('LWPOLYLINE[layer=="A-VISIBLE"]')
    assert max(v[0] for p in paths for v in p.get_points('xy')) == pytest.approx(6000)
    with pymupdf.open(tmp_path / 'cut.pdf') as pdf:
        lengths = [abs(item[2].x - item[1].x) * 25.4 / 72
                   for path in pdf[0].get_drawings() for item in path['items'] if item[0] == 'l']
        assert any(abs(length - 60) < .01 for length in lengths)


def test_hidden_line_removal_hides_back_object_and_splits_partial_overlap():
    front = mesh_object('front', [4000, 1000, 4000], [0, -2000, 0])
    back = mesh_object('back', [2000, 1000, 2000], [0, 1000, 0])
    view = extract_mesh_view(scene(front, back), {'kind': 'elevation'})
    # Fully hidden rear edges must not appear inside the foreground silhouette.
    assert all(abs(p[0]) == pytest.approx(2000) or abs(p[1]) == pytest.approx(2000)
               for line in view['lines'] for p in line)
    back = mesh_object('back', [4000, 1000, 2000], [2000, 1000, 0])
    view = extract_mesh_view(scene(front, back), {'kind': 'elevation'})
    horizontal = [line for line in view['lines'] if line[0][1] == line[1][1] == 1000]
    assert horizontal and min(p[0] for line in horizontal for p in line) == pytest.approx(2000)


def test_hollow_mesh_section_keeps_hole_and_excludes_triangulation_edges():
    # Closed square tube, with an inner void. Independent of any solid CAD kernel.
    outer = [(0, 0), (4000, 0), (4000, 4000), (0, 4000)]
    inner = [(1000, 1000), (3000, 1000), (3000, 3000), (1000, 3000)]
    vertices = [[x, y, z] for z in (0, 3000) for ring in (outer, inner) for x, y in ring]
    quads = []
    for i in range(4):
        j = (i + 1) % 4
        quads += [[i, j, j + 8, i + 8], [i + 4, i + 12, j + 12, j + 4],
                  [i, i + 4, j + 4, j], [i + 8, j + 8, j + 12, i + 12]]
    faces = [tri for a, b, c, d in quads for tri in ([a, b, c], [a, c, d])]
    model = scene({'id': 'tube', 'vertices': vertices, 'faces': faces})
    view = extract_mesh_view(model, {'kind': 'plan', 'cut_z': 1500})
    assert len(view['cuts']) == 1 and len(view['cuts'][0]['holes']) == 1
    assert view['cuts'][0]['area_mm2'] == pytest.approx(12000000)
    assert not view['warnings']


def test_open_cut_is_reported_and_degenerate_basis_rejected():
    model = scene({'id': 'surface', 'vertices': [[0, 0, 0], [2000, 0, 0], [2000, 0, 3000]], 'faces': [[0, 1, 2]]})
    assert extract_mesh_view(model, {'kind': 'plan'})['warnings']
    with pytest.raises(ValueError, match='parallel'):
        extract_mesh_view(model, {'normal': [1, 0, 0], 'xdir': [1, 0, 0]})


def test_dae_preserves_display_names_without_invalid_xml_ids(tmp_path):
    import collada
    from ezarch.exchange import export_scene
    model = scene(mesh_object('墙 / A-1', [100, 200, 300], [0, 0, 0]))
    model['materials']['玻璃 1'] = model['materials'].pop('m')
    model['objects'][0]['material'] = '玻璃 1'
    export_scene(model, tmp_path, ['dae'])
    loaded = collada.Collada(str(tmp_path / 'model.dae'))
    assert loaded.scene.nodes[0].id == 'node-0'
    assert loaded.scene.nodes[0].name == '墙 / A-1'
    assert loaded.materials[0].name == '玻璃 1'


@pytest.mark.skipif(os.environ.get('EZARCH_TEST_BLENDER') != '1', reason='Enable installed Blender integration explicitly')
def test_native_blender_script_instances_units_edit_and_exchange(tmp_path):
    import rhino3dm
    import trimesh
    from ezarch.blender import execute, export_blend, extract
    source = tmp_path / 'native scene.blend'
    script = tmp_path / 'create.py'
    script.write_text('''import bpy
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = .001
collection = bpy.data.collections.new('Editable')
bpy.context.scene.collection.children.link(collection)
bpy.ops.mesh.primitive_cube_add(size=2, location=(1000,2000,3000))
obj = bpy.context.object
obj.name = 'Original'
obj.scale = (500, 250, 1000)
for old in list(obj.users_collection): old.objects.unlink(obj)
collection.objects.link(obj)
mod = obj.modifiers.new('Repeated', 'ARRAY')
mod.count = 2
mod.relative_offset_displace = (2,0,0)
instance = bpy.data.objects.new('Placed', None)
instance.instance_type = 'COLLECTION'
instance.instance_collection = collection
instance.location = (10000,0,0)
bpy.context.scene.collection.objects.link(instance)
mat = bpy.data.materials.new('Retain')
mat.use_nodes = True
obj.data.materials.append(mat)
''', encoding='utf-8')
    execute(script, tmp_path / 'create-log', save=source)
    from ezarch.inspection import inspect, query
    inspect(source, tmp_path / 'inventory')
    assert query(tmp_path / 'inventory/inspection.json', section='materials')['objects'][0]['id'] == 'Retain'
    assert query(tmp_path / 'inventory/inspection.json', section='collections', ids=['Editable'])['matched'] == 1
    report = extract(source, tmp_path / 'geometry')
    snapshot = json.loads(Path(report['file']).read_text())
    assert len(snapshot['objects']) == 2
    bounds = np.array([o['bounds_mm'] for o in snapshot['objects']])
    assert bounds[:, 0].min() == pytest.approx(500)
    assert bounds[:, 3].max() == pytest.approx(13500)
    assert bounds[:, 5].max() == pytest.approx(4000)
    before = source.read_bytes()
    edit = tmp_path / 'edit.py'
    edit.write_text("import bpy\nbpy.data.objects['Placed'].location.y += 1000\n")
    edited = tmp_path / 'changed.blend'
    execute(edit, tmp_path / 'edit-log', source=source, save=edited)
    assert source.read_bytes() == before
    result = extract(edited, tmp_path / 'edited-geometry')
    changed = json.loads(Path(result['file']).read_text())
    original_before = next(o for o in snapshot['objects'] if o['id'] == 'Original')
    original_after = next(o for o in changed['objects'] if o['id'] == 'Original')
    assert original_before == original_after
    export_blend(edited, tmp_path / 'exchange', ['glb', '3dm', 'dae'])
    rhino = rhino3dm.File3dm.Read(str(tmp_path / 'exchange/model.3dm'))
    assert len(rhino.Objects) == 2
    glb = trimesh.load(tmp_path / 'exchange/model.glb', force='scene')
    # glTF is metres, Y-up. Validate scale, not just file existence.
    assert glb.bounds[1][0] == pytest.approx(13.5, abs=1e-5)
    assert glb.bounds[1][1] == pytest.approx(4, abs=1e-5)
    bad = tmp_path / 'bad.py'
    bad.write_text("raise RuntimeError('intentional validation failure')\n")
    with pytest.raises(RuntimeError, match='Blender failed'):
        execute(bad, tmp_path / 'failure-log', source=edited, save=tmp_path / 'should-not-exist.blend')
    assert not (tmp_path / 'should-not-exist.blend').exists()
