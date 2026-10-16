"""Optional file operations independent of the project schema."""
import argparse
import json
from pathlib import Path


def main(argv):
    from . import cad, inspection, rhino
    p = argparse.ArgumentParser(prog='ezarch')
    sub = p.add_subparsers(dest='operation', required=True)
    s = sub.add_parser('inspect', help='Inventory a raw document and optionally render it')
    s.add_argument('input', type=Path)
    s.add_argument('--out', type=Path, required=True)
    s.add_argument('--preview', action='store_true')
    s.add_argument('--scale', type=float)
    s.add_argument('--layout', default='Model')
    s.add_argument('--region', nargs=4, type=float)
    s.add_argument('--ids', nargs='+')
    s = sub.add_parser('query', help='Query a version-bound inspection without dumping all geometry')
    s.add_argument('index', type=Path)
    s.add_argument('--source', type=Path)
    for name in ['layer', 'kind', 'space', 'contains']:
        s.add_argument('--' + name)
    s.add_argument('--ids', nargs='+')
    s.add_argument('--region', nargs=4, type=float)
    s.add_argument('--section', choices=['objects', 'instances', 'layers', 'fonts', 'pages', 'dependencies',
                                       'collections', 'cameras', 'materials', 'node_groups', 'libraries'], default='objects')
    s.add_argument('--offset', type=int, default=0)
    s.add_argument('--limit', type=int, default=40)
    s = sub.add_parser('compare', help='Compare IDs/properties between two document inventories')
    s.add_argument('before', type=Path)
    s.add_argument('after', type=Path)
    s = sub.add_parser('convert', help='DWG/DXF conversion through externally installed ODA')
    s.add_argument('input', type=Path)
    s.add_argument('output', type=Path)
    s.add_argument('--version', default='ACAD2018')
    s.add_argument('--repair', action='store_true')
    s = sub.add_parser('edit', help='Selection edits retaining the native document; arbitrary APIs remain available')
    s.add_argument('input', type=Path)
    s.add_argument('output', type=Path)
    s.add_argument('--ids', nargs='+', required=True)
    s.add_argument('--move', type=float, nargs=3)
    s.add_argument('--text')
    s.add_argument('--name')
    s.add_argument('--expected-sha256')
    a = p.parse_args(argv)
    try:
        if a.operation == 'inspect':
            result = inspection.inspect(a.input, a.out, a.preview, a.scale, a.layout, a.region, a.ids)
        elif a.operation == 'query':
            result = inspection.query(a.index, a.source, a.ids, a.layer, a.kind, a.space, a.contains,
                                      a.region, a.offset, a.limit, a.section)
        elif a.operation == 'compare':
            result = inspection.compare(a.before, a.after)
            result['counts'] = {k: len(result[k]) for k in ('added', 'removed', 'changed')}
            result['listed_id_limit'] = 40
            for key in ('added', 'removed', 'changed'):
                result[key] = result[key][:40]
        elif a.operation == 'convert':
            result = cad.convert(a.input, a.output, a.version, a.repair)
        elif a.operation == 'edit':
            suffix = a.input.suffix.lower()
            if a.move is None and a.text is None and a.name is None:
                raise ValueError('Specify an edit operation')
            if suffix in {'.dwg', '.dxf'}:
                if a.name is not None:
                    raise ValueError('--name is a 3DM operation')
                result = cad.edit(a.input, a.output, a.ids, a.move, a.text, a.expected_sha256)
            elif suffix == '.3dm':
                if a.text is not None:
                    raise ValueError('3DM text editing needs the native annotation API')
                result = rhino.edit(a.input, a.output, a.ids, a.move, a.name, a.expected_sha256)
            elif suffix == '.svg':
                if a.name is not None:
                    raise ValueError('--name is a 3DM operation')
                result = edit_svg(a.input, a.output, a.ids, a.move, a.text, a.expected_sha256)
            else:
                raise ValueError('Helper edits DXF/DWG/3DM/SVG. Use Blender/OCCT APIs for other geometry operations.')
        print(json.dumps(inspection.serial(result), ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        print(json.dumps({'error': type(error).__name__, 'detail': str(error)}, ensure_ascii=False))
        return 1


def edit_svg(source, target, ids, move=None, text=None, expected=None):
    import xml.etree.ElementTree as ET

    from .cad import check_source, destination, sha256
    source, target = destination(source, target)
    if target.suffix.lower() != '.svg':
        raise ValueError('SVG output must retain .svg')
    before = check_source(source, expected)
    tree = ET.parse(source)
    selected = [node for i, node in enumerate(tree.getroot().iter()) if (node.get('id') or f'index:{i}') in ids]
    if len(selected) != len(set(ids)):
        raise ValueError('Missing or duplicate SVG element identifiers')
    if move and move[2] != 0:
        raise ValueError('SVG translation has no Z component')
    if text is not None and any(list(node) or node.tag.rsplit('}', 1)[-1] not in {'text', 'tspan'} for node in selected):
        raise ValueError('Text edit needs leaf text/tspan IDs, to preserve nested runs')
    for node in selected:
        if move:
            node.set('transform', f'translate({move[0]} {move[1]}) ' + node.get('transform', ''))
        if text is not None:
            node.text = text
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')
    tree.write(target, encoding='utf-8', xml_declaration=True)
    return {'source_sha256': before, 'output_sha256': sha256(target), 'ids': ids,
            'file': str(target), 'translation_basis': 'selected element parent coordinates'}
