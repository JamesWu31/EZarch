"""Regression checks for task-selected output and preservation of user choices."""
import math
import subprocess
import sys

import ezdxf
import pymupdf as fitz
import pytest
from ezarch.audit import audit
from ezarch.drafting import Drawing
from ezarch.geometry import generate_model
from ezarch.graphics import Canvas
from ezarch.project import Project, skill_root
from ezarch.views import generate_views


def simple_project():
    return Project(name='Export choice', materials={'a': {'color': [.5, .6, .7]}},
                   elements=[dict(id='part', kind='box', origin=[0, 0, 0], size=[4000, 2000, 3000], material='a')],
                   views=[dict(id='cut', kind='plan', cut_z=1200, scale=100)])


def test_drawing_without_frame_selected_formats_and_repeated_save(tmp_path):
    d = Drawing([0, 0, 10000, 5000], scale=100, title='Not a requested title')
    d.line([1000, 1000], [9000, 1000])
    d.save(tmp_path / 'plain', formats=['pdf'])
    assert not (tmp_path / 'plain.dxf').exists()
    assert not (tmp_path / 'plain.svg').exists()
    with fitz.open(tmp_path / 'plain.pdf') as pdf:
        assert pdf[0].get_text() == ''
        assert pdf[0].rect.height * 25.4 / 72 == pytest.approx(74, abs=.001)
        lengths = [abs(item[2].x - item[1].x) * 25.4 / 72
                   for path in pdf[0].get_drawings() for item in path['items'] if item[0] == 'l']
        assert any(abs(length - 80) < .001 for length in lengths)
    decorated = Drawing([0, 0, 10000, 5000], decoration=True, title='Optional footer')
    for name in ['one', 'two']:
        decorated.save(tmp_path / name, formats=['pdf'])
        with fitz.open(tmp_path / f'{name}.pdf') as pdf:
            assert pdf[0].get_text().count('Optional footer') == 1


def test_custom_font_and_oblique_text_remain_editable(tmp_path):
    c = Canvas(160, 100, font=skill_root() / 'assets/fonts/FandolFang-Regular.otf')
    c.text(40, 60, '倾斜标注 ABC', rotation=32, size=5)
    c.save(tmp_path / 'angle', formats=['pdf', 'svg'])
    with fitz.open(tmp_path / 'angle.pdf') as pdf:
        line = pdf[0].get_text('dict')['blocks'][0]['lines'][0]
        assert line['dir'] == pytest.approx([math.cos(math.radians(32)), -math.sin(math.radians(32))])
        assert '倾斜标注 ABC' in pdf[0].get_text().replace('\xa0', ' ')
        assert 'FandolFang' in line['spans'][0]['font']
    assert '<text ' in (tmp_path / 'angle.svg').read_text()
    assert not (tmp_path / 'angle.png').exists()


def test_symbol_parameters_reach_saved_geometry(tmp_path):
    d = Drawing([-2000, -2000, 12000, 12000], style={
        'axis_circle_diameter_mm': 10, 'index_circle_diameter_mm': 12,
        'north_circle_diameter_mm': 30, 'section_position_length_mm': 9,
        'section_direction_length_mm': 6, 'excluded_axis_labels': []})
    d.axis('I', 'x', 0, 0, 5000)
    d.index([4000, 4000], '1', '2')
    d.north([8000, 8000])
    d.section_mark([0, 8000], [4000, 8000], 'S')
    d.save(tmp_path / 'symbols', formats=['dxf'])
    ms = ezdxf.readfile(tmp_path / 'symbols.dxf').modelspace()
    assert sorted(c.dxf.radius for c in ms.query('CIRCLE')) == [500, 500, 600, 1500]
    lengths = [math.dist(*list(e.get_points('xy'))) for e in ms.query('LWPOLYLINE[layer=="A-CUT"]')]
    assert sorted(lengths) == [600, 600, 900, 900]


def test_selected_model_and_view_exports_audit_without_siblings(tmp_path):
    p = simple_project()
    generate_model(p, tmp_path / 'model', formats=['scene', 'glb'])
    assert not (tmp_path / 'model/model.step').exists()
    assert not (tmp_path / 'model/model.dae').exists()
    import trimesh
    glb = trimesh.load(tmp_path / 'model/model.glb', force='scene')
    assert glb.metadata['ezarch_up_axis'] == 'Y'
    assert glb.bounds.tolist() == [[0, 0, -2], [4, 3, 0]]
    assert audit(tmp_path / 'model', tmp_path / 'a')['passed']
    generate_views(p, tmp_path / 'views', formats=['pdf'])
    assert not (tmp_path / 'views/cut.dxf').exists()
    assert audit(tmp_path / 'views', tmp_path / 'b')['passed']
    (tmp_path / 'model/model.glb').unlink()
    with pytest.raises(ValueError, match='Audit failed'):
        audit(tmp_path / 'model', tmp_path / 'c')


def test_standalone_dxf_audit_does_not_impose_mm_or_project(tmp_path):
    doc = ezdxf.new()
    doc.units = ezdxf.units.M
    doc.modelspace().add_line([0, 0], [3, 0])
    file = tmp_path / 'existing.dxf'
    doc.saveas(file)
    report = audit(file, tmp_path / 'check')
    assert report['passed']
    assert report['checks'][0]['detail']['declared_units'] == ezdxf.units.M


def test_selected_exports_ignore_older_unselected_siblings(tmp_path):
    p = simple_project()
    generate_model(p, tmp_path / 'model', formats=['step', 'scene', 'glb', '3dm', 'dae'])
    p.elements[0]['size'][2] = 4000
    generate_model(p, tmp_path / 'model', formats=['scene', 'glb'])
    assert audit(tmp_path / 'model', tmp_path / 'check')['passed']
    p.elements[0]['size'][2] = 5000
    generate_model(p, tmp_path / 'model', formats=['step'])
    assert audit(tmp_path / 'model', tmp_path / 'check')['passed']


def test_native_examples_edit_and_cut_in_world_coordinates(tmp_path):
    examples = skill_root() / 'scripts/examples'
    doc = ezdxf.new()
    doc.units = ezdxf.units.MM
    text = doc.modelspace().add_text('Before', dxfattribs={'height': 100})
    doc.modelspace().add_line([0, 0], [6000, 0])
    doc.saveas(tmp_path / 'source.dxf')
    subprocess.run([sys.executable, str(examples / 'edit_dxf.py'), str(tmp_path / 'source.dxf'),
                    str(tmp_path / 'edited.dxf'), '--handle', text.dxf.handle, '--text', 'After',
                    '--pdf', str(tmp_path / 'edited.pdf'), '--scale', '100'], check=True)
    assert ezdxf.readfile(tmp_path / 'edited.dxf').entitydb[text.dxf.handle].dxf.text == 'After'
    with fitz.open(tmp_path / 'edited.pdf') as pdf:
        lengths = [abs(item[2].x - item[1].x) * 25.4 / 72
                   for path in pdf[0].get_drawings() for item in path['items'] if item[0] == 'l']
        assert any(abs(length - 60) < .01 for length in lengths)
    subprocess.run([sys.executable, str(examples / 'solid_section.py'), '--out', str(tmp_path / 'solid'),
                    '--cut-z', '1200'], check=True)
    section = ezdxf.readfile(tmp_path / 'solid/section.dxf')
    assert len(section.modelspace()) > 0
