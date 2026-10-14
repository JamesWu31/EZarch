"""Standard-library SVG edit: replace text of one named leaf without flattening paths or groups."""
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--id', required=True)
    p.add_argument('--text', required=True)
    a = p.parse_args()
    if a.input.resolve() == a.output.resolve():
        raise ValueError('This example saves a separate edited copy')
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True, insert_pis=True))
    tree = ET.parse(a.input, parser=parser)
    targets = [e for e in tree.iter() if e.get('id') == a.id]
    if len(targets) != 1 or targets[0].tag.rsplit('}', 1)[-1] not in {'text', 'tspan'} or len(targets[0]):
        raise ValueError('Select a unique text/tspan leaf; adapt the example for rich text')
    targets[0].text = a.text
    a.output.parent.mkdir(parents=True, exist_ok=True)
    tree.write(a.output, encoding='utf-8', xml_declaration=True)


if __name__ == '__main__':
    main()
