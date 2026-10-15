"""Synthetic API regressions, not architectural templates or visual examples."""
import json
from pathlib import Path

import ezdxf
import pymupdf as fitz
import pytest
from ezarch import cad, inspection, rhino
from ezarch.file_cli import edit_svg


def test_cad_document_preserved_selection_and_real_curve_preview(tmp_path):
    doc = ezdxf.new('R2018')
    doc.units = ezdxf.units.M
    doc.layers.new('REFERENCE')
    block = doc.blocks.new('CURVED')
    block.add_lwpolyline([(0, 0, 1), (2, 0, 0)], format='xyb', close=True)
    hatch = block.add_hatch()
    hatch.paths.add_polyline_path([(0,0),(1,0),(1,1),(0,1)])
    inserted = doc.modelspace().add_blockref('CURVED', (4, 3), dxfattribs={'rotation': 32, 'xscale': 2, 'yscale': 2})
    label = doc.modelspace().add_text('Original', dxfattribs={'height': .15})
    retained = doc.modelspace().add_line((0, 0), (6, 0), dxfattribs={'layer': 'REFERENCE'})
    layout = doc.layouts.new('Sheet')
    layout.add_text('Keep layout', dxfattribs={'height': 2.5})
    doc.saveas(tmp_path / 'original.dxf')
    source = tmp_path / 'original.dxf'
    inspection.inspect(source, tmp_path / 'before', preview=True, scale=100)
    index = tmp_path / 'before/inspection.json'
    record = inspection.query(index, ids=[inserted.dxf.handle])['objects'][0]
    assert record['block'] == 'CURVED' and record['bounds'] is not None
    assert inspection.query(index, kind='LWPOLYLINE')['objects'][0]['has_arc']
    assert (tmp_path / 'before/view.png').stat().st_size > 500
    with fitz.open(tmp_path / 'before/view.pdf') as pdf:
        paths = pdf[0].get_drawings()
        assert any(path['fill'] is not None for path in paths)
        assert any(abs(abs(item[2].x - item[1].x) * 25.4 / 72 - 60) < .02
                   for path in paths for item in path['items'] if item[0] == 'l')
    cad.edit(source, tmp_path / 'edited.dxf', [label.dxf.handle], text='Changed', expected=cad.sha256(source))
    edited = ezdxf.readfile(tmp_path / 'edited.dxf')
    assert edited.units == doc.units
    assert edited.entitydb[label.dxf.handle].dxf.text == 'Changed'
    assert edited.entitydb[retained.dxf.handle].dxf.end == retained.dxf.end
    assert len(edited.blocks['CURVED']) == 2 and len(edited.layouts.get('Sheet')) == 1
    inspection.inspect(tmp_path / 'edited.dxf', tmp_path / 'after')
    diff = inspection.compare(index, tmp_path / 'after/inspection.json')
    assert diff['changed'] == [label.dxf.handle] and not diff['removed'] and not diff['added']
    source.write_bytes(source.read_bytes() + b'\n')
    with pytest.raises(ValueError, match='Source changed'):
        inspection.query(index)
    with pytest.raises(ValueError, match='Source changed'):
        cad.edit(source, tmp_path / 'wrong.dxf', [label.dxf.handle], expected='old')
    assert not (tmp_path / 'wrong.dxf').exists()


def test_exact_rhino_objects_read_edit_preserve_ids(tmp_path):
    import rhino3dm as r
    curve = r.Circle(r.Point3d(0, 0, 0), 1200).ToNurbsCurve()
    extrusion = r.Extrusion.Create(curve, 3200, True)
    assert extrusion.AddInnerProfile(r.Circle(r.Point3d(0, 0, 0), 900).ToNurbsCurve())
    attrs = r.ObjectAttributes()
    attrs.Name = 'hollow'
    surface = r.NurbsSurface.CreateFromSphere(r.Sphere(r.Point3d(5000, 0, 0), 800))
    source = tmp_path / 'native.3dm'
    rhino.write_geometry([(extrusion, attrs), (surface, r.ObjectAttributes()), (curve, r.ObjectAttributes())], source)
    report = inspection.inspect(source, tmp_path / 'read', preview=True)
    assert report['types'] == {'Extrusion': 1, 'NurbsSurface': 1, 'NurbsCurve': 1}
    doc = r.File3dm.Read(str(source))
    selected = str(doc.Objects[0].Attributes.Id)
    rhino.edit(source, tmp_path / 'edited.3dm', [selected], move=[400, 200, 0], expected=cad.sha256(source))
    inspection.inspect(tmp_path / 'edited.3dm', tmp_path / 'read2')
    diff = inspection.compare(tmp_path / 'read/inspection.json', tmp_path / 'read2/inspection.json')
    assert diff['changed'] == [selected] and not diff['added'] and not diff['removed']
    result = r.File3dm.Read(str(tmp_path / 'edited.3dm'))
    import uuid
    moved = result.Objects.FindId(uuid.UUID(selected)).Geometry
    assert moved.IsSolid and moved.ProfileCount == 2
    assert moved.GetBoundingBox().Min.X == pytest.approx(-800)
    assert doc.Objects[1].Geometry.Encode() == result.Objects.FindId(doc.Objects[1].Attributes.Id).Geometry.Encode()


def test_exact_polyhedral_brep_and_no_faceting_of_curves(tmp_path):
    import cadquery as cq
    import rhino3dm as r
    shape = cq.Workplane().box(6000, 300, 3000).cut(cq.Workplane().box(1200, 500, 2000)) .val()
    shape = shape.rotate((0, 0, 0), (0, 0, 1), 31).translate((1000000.123456, 2000000.654321, 0))
    brep = rhino.planar_brep(shape)
    assert brep.IsValid and brep.IsSolid
    assert all(f.IsPlanar() for f in brep.Faces)
    assert sum(len(f.Loops) == 2 for f in brep.Faces) == 2  # Both caps retain the opening.
    assert brep.GetBoundingBox().Min.X == pytest.approx(shape.BoundingBox().xmin, abs=1e-7, rel=0)
    assert brep.GetBoundingBox().Min.Y == pytest.approx(shape.BoundingBox().ymin, abs=1e-7, rel=0)
    rhino.write_geometry([(brep, r.ObjectAttributes())], tmp_path / 'solid.3dm')
    assert r.File3dm.Read(str(tmp_path / 'solid.3dm')).Objects[0].Geometry.IsSolid
    with pytest.raises(ValueError, match='no mesh fallback'):
        rhino.planar_brep(cq.Solid.makeCylinder(1200, 3000))


def test_svg_keeps_defs_transforms_and_text_runs(tmp_path):
    source = tmp_path / 'source.svg'
    source.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><clipPath id="clip"><rect width="60" height="60"/></clipPath></defs><g transform="rotate(15)"><text id="label"><tspan id="leaf">Before</tspan></text><path id="keep" d="M0,0 L40,20"/></g></svg>')
    inspection.inspect(source, tmp_path / 'index')
    edit_svg(source, tmp_path / 'changed.svg', ['leaf'], text='After', expected=cad.sha256(source))
    result = (tmp_path / 'changed.svg').read_text()
    assert 'clipPath' in result and 'rotate(15)' in result and 'M0,0 L40,20' in result
    assert '>After<' in result
    inspection.inspect(tmp_path / 'changed.svg', tmp_path / 'after')
    assert inspection.compare(tmp_path / 'index/inspection.json', tmp_path / 'after/inspection.json')['changed'] == ['leaf']
    with pytest.raises(ValueError, match='leaf'):
        edit_svg(source, tmp_path / 'bad.svg', ['label'], text='Flattened')


def test_query_pagination_and_unknown_bounds_not_zero(tmp_path):
    source = tmp_path / 'source.txt'
    source.write_text('fixed')
    index = tmp_path / 'inspection.json'
    index.write_text(json.dumps({'source': str(source), 'sha256': cad.sha256(source),
                                'objects': [{'id': str(i), 'type': 'unknown', 'bounds': None} for i in range(7)]}))
    result = inspection.query(index, limit=3, offset=3)
    assert [o['id'] for o in result['objects']] == ['3', '4', '5']
    assert result['next_offset'] == 6 and result['matched'] == 7
    assert inspection.query(index, region=[0,0,10,10])['matched'] == 0


def test_oda_not_bundled_and_new_modules_distributed():
    root = Path(__file__).resolve().parents[1]
    manifest = (root / 'tools/skill-files.txt').read_text()
    assert 'scripts/examples/' not in manifest
    for name in ['cad', 'inspection', 'rhino', 'file_cli']:
        assert f'src/ezarch/{name}.py' in manifest
    assert '.ezarch/tools' not in manifest


def test_svg_preview_respects_css_nested_transform_clip_and_physical_units(tmp_path):
    from PIL import Image
    source = tmp_path / 'clip.svg'
    source.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="100mm" viewBox="0 0 100 100"><style>.area{fill:#ff0000}</style><defs><clipPath id="cut"><rect width="20" height="20"/></clipPath></defs><g transform="translate(30 0)" clip-path="url(#cut)"><rect class="area" x="-100" y="-100" width="300" height="300"/></g></svg>')
    inspection.inspect(source, tmp_path / 'preview', preview=True)
    with Image.open(tmp_path / 'preview/view.png') as im:
        assert im.size == (2400, 2400)
        assert im.convert('RGB').getpixel((35 * 24, 10 * 24)) == (255, 0, 0)
        assert im.convert('RGB').getpixel((10 * 24, 10 * 24)) == (255, 255, 255)
        assert im.convert('RGB').getpixel((60 * 24, 10 * 24)) == (255, 255, 255)


def test_3dm_instance_world_bounds_and_preview_map_to_source_ids(tmp_path):
    import rhino3dm as r
    doc = r.File3dm()
    geometry = r.Brep.CreateFromBoundingBox(r.BoundingBox(0, 0, 0, 200, 300, 400))
    definition_index = doc.InstanceDefinitions.Add('Unit', '', '', '', r.Point3d(0,0,0), (geometry,), (r.ObjectAttributes(),))
    definition = doc.InstanceDefinitions.FindIndex(definition_index)
    transform = r.Transform.Translation(1000, 2000, 3000)
    object_id = doc.Objects.AddInstanceObject(r.InstanceReference(definition.Id, transform), r.ObjectAttributes())
    source = tmp_path / 'instance.3dm'
    assert doc.Write(str(source), 8)
    inspection.inspect(source, tmp_path / 'view', preview=True)
    record = inspection.query(tmp_path / 'view/inspection.json', ids=[str(object_id)])['objects'][0]
    assert record['bounds'] == [1000, 2000, 3000, 1200, 2300, 3400]
    assert record['transform'][0][3] == 1000
    assert str(object_id) in (tmp_path / 'view/view.svg').read_text()
