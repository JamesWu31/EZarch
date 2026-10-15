"""Whole-document CAD operations; source coordinates and object handles survive edits."""
from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check_source(source, expected=None):
    actual = sha256(source)
    if expected and actual != expected:
        raise ValueError('Source changed since inspection; inspect the latest file before using old object selections')
    return actual


def destination(source, target):
    source, target = Path(source).resolve(), Path(target).resolve()
    if source == target:
        raise ValueError('Choose a separate output file; this helper preserves the source')
    if target.exists():
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    return source, target


def find_oda():
    from .project import skill_root
    candidates = [os.environ.get('EZARCH_ODA'), shutil.which('ODAFileConverter')]
    roots = [skill_root() / '.ezarch/tools', Path.home() / 'Applications', Path('/Applications')]
    if os.environ.get('ProgramFiles'):
        roots.append(Path(os.environ['ProgramFiles']) / 'ODA')
    for root in roots:
        if root.is_dir():
            candidates.extend(str(p) for p in root.glob('**/ODAFileConverter.exe'))
            candidates.extend(str(p) for p in root.glob('**/ODAFileConverter.app/Contents/MacOS/ODAFileConverter'))
    return next((str(Path(p).resolve()) for p in candidates if p and Path(p).is_file()), None)


def convert(source, target, version='ACAD2018', repair=False, timeout=180):
    """Isolate one file, never audit/repair silently, check the actual output signature."""
    source, target = destination(source, target)
    if source.suffix.lower() not in {'.dwg', '.dxf'} or target.suffix.lower() not in {'.dwg', '.dxf'}:
        raise ValueError('ODA adapter accepts DWG/DXF only')
    executable = find_oda()
    if not executable:
        raise RuntimeError('ODA File Converter missing. Run bootstrap.py --install-oda or set EZARCH_ODA; ezdxf alone cannot read DWG')
    from ezdxf.addons.odafc import VALID_VERSIONS, map_version
    version = map_version(version)
    if version not in VALID_VERSIONS:
        raise ValueError(f'Unsupported ODA version: {version}')
    with tempfile.TemporaryDirectory(prefix='ezarch-oda-') as tmp:
        root = Path(tmp)
        incoming, outgoing = root / 'in', root / 'out'
        incoming.mkdir()
        outgoing.mkdir()
        # A neutral isolated name also handles Unicode, glob characters and unrelated files.
        copied = incoming / ('source' + source.suffix.lower())
        shutil.copy2(source, copied)
        command = [executable, str(incoming), str(outgoing), version, target.suffix[1:].upper(),
                   '0', '1' if repair else '0', copied.name]
        startup = {'creationflags': subprocess.CREATE_NO_WINDOW} if platform.system() == 'Windows' else {}
        run = subprocess.run(command, capture_output=True, text=True, errors='replace', timeout=timeout, **startup)
        result = outgoing / ('source' + target.suffix.lower())
        if run.returncode or not result.is_file() or result.stat().st_size == 0:
            raise RuntimeError(f'ODA conversion failed ({run.returncode}): {(run.stderr or run.stdout)[-1800:]}')
        if target.suffix.lower() == '.dxf':
            import ezdxf
            ezdxf.readfile(result)  # Conversion success is not a completeness/compliance claim.
        elif not result.read_bytes()[:6].startswith(b'AC10'):
            raise ValueError('ODA result has no DWG signature')
        shutil.copy2(result, target)
    return {'source_sha256': sha256(source), 'output_sha256': sha256(target), 'file': str(target),
            'version': version, 'repair_requested': repair, 'converter': 'ODA File Converter',
            'scope': 'Conversion and parse/signature only; compare content and target application behavior'}


def read(source, cache=None):
    import ezdxf
    source = Path(source)
    if source.suffix.lower() == '.dxf':
        return ezdxf.readfile(source), source
    if source.suffix.lower() != '.dwg':
        raise ValueError('Expected DWG or DXF')
    if cache is None:
        raise ValueError('DWG reading needs a project-local conversion directory')
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / f'{source.stem}-{sha256(source)[:16]}.dxf'
    metadata = target.with_suffix('.conversion.json')
    if not target.exists():
        result = convert(source, target)
        metadata.write_text(json.dumps(result, indent=2), encoding='utf-8')
    elif metadata.exists():
        result = json.loads(metadata.read_text(encoding='utf-8'))
        if result['source_sha256'] != sha256(source) or result['output_sha256'] != sha256(target):
            raise ValueError('Converted working copy changed; choose it explicitly as the new source or use a fresh conversion directory')
    else:
        raise ValueError('Existing conversion has no version record; choose a fresh output directory')
    doc = ezdxf.readfile(target)
    doc.filename = str(source)  # Relative dependencies remain rooted at the supplied file.
    return doc, target


def plot(doc, output, scale=None, layout_name='Model', handles=None, region=None, dpi=150):
    """Render via ezdxf's full frontend, with optional isolation/crop; never line-only tracing."""
    import ezdxf
    import pymupdf as fitz
    from ezdxf.addons.drawing import Frontend, RenderContext, layout, pymupdf
    from ezdxf.addons.drawing.config import BackgroundPolicy, Configuration
    from ezdxf.math import BoundingBox2d
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    class BatchedRenderer(pymupdf.PyMuPdfRenderBackend):
        def draw_solid_lines(self, lines, properties):
            from itertools import islice
            iterator = iter(lines)
            while batch := list(islice(iterator, 500)):
                super().draw_solid_lines(batch, properties)

    class BatchedBackend(pymupdf.PyMuPdfBackend):
        @staticmethod
        def make_backend(page, settings):
            return BatchedRenderer(page, settings)

    backend = BatchedBackend()
    warnings = []

    class ReportingFrontend(Frontend):
        def skip_entity(self, entity, msg):
            warnings.append({'handle': entity.dxf.handle, 'type': entity.dxftype(), 'reason': msg})
            super().skip_entity(entity, msg)

    selected = set(handles or [])
    from ezdxf import bbox
    source_layout = doc.layouts.get(layout_name)
    candidates = [e for e in source_layout if not selected or e.dxf.handle in selected]
    estimate = BoundingBox2d([(region[0], region[1]), (region[2], region[3])]) if region else bbox.extents(candidates, fast=True)
    estimate_size = max(estimate.size) if estimate.has_data else 1
    paper_factor = ezdxf.units.conversion_factor(doc.units, ezdxf.units.MM) / scale if scale and doc.units else 270 / max(estimate_size, 1e-9)
    frontend = ReportingFrontend(RenderContext(doc), backend,
        config=Configuration(background_policy=BackgroundPolicy.WHITE,
                             max_flattening_distance=.02 / paper_factor,
                             min_dash_length=.05 / paper_factor,
                             min_hatch_line_distance=.05 / paper_factor))
    frontend.draw_layout(doc.layouts.get(layout_name), filter_func=(lambda e: e.dxf.handle in selected) if selected else None)
    bounds = BoundingBox2d([(region[0], region[1]), (region[2], region[3])]) if region else backend.player().bbox()
    if not bounds.has_data or min(bounds.size) <= 0:
        raise ValueError('Empty/degenerate view; inspect layout, visibility and selected objects')
    if scale is not None:
        if scale <= 0 or doc.units == 0:
            raise ValueError('Print scale needs positive scale and known source units; do not guess unitless CAD')
        factor = ezdxf.units.conversion_factor(doc.units, ezdxf.units.MM) / scale
    else:
        factor = 270 / max(bounds.size)  # Preview size only, not a claimed drawing scale.
    width, height = [math.ceil((v * factor + 20) * 10) / 10 for v in bounds.size]
    page = layout.Page(width, height, margins=layout.Margins.all(10))
    correction = max(width, height) * 72 / 25.4 / pymupdf.get_coordinate_output_space(page)
    content = backend.get_pdf_bytes(page, settings=layout.Settings(scale=factor * correction, fit_page=False), render_box=bounds)
    pdf = output.with_suffix('.pdf')
    pdf.write_bytes(content)
    with fitz.open(pdf) as rendered:
        rendered[0].get_pixmap(dpi=dpi, alpha=False).save(output.with_suffix('.png'))
    return {'pdf': str(pdf), 'png': str(output.with_suffix('.png')), 'layout': layout_name,
            'source_region': [*bounds.extmin, *bounds.extmax], 'scale': scale, 'skipped': warnings,
            'display_tolerance_paper_mm': .02, 'minimum_dash_hatch_spacing_paper_mm': .05,
            'scope': '2D frontend; inspect proxy/3D entities, fonts, xrefs and viewport support separately'}


def edit(source, target, handles, move=None, text=None, expected=None):
    """Small selection edit. Native ezdxf API remains available for arbitrary design changes."""
    source, target = destination(source, target)
    before = check_source(source, expected)
    if move is not None and (len(move) != 3 or not all(math.isfinite(v) for v in move)):
        raise ValueError('Translation needs three finite source-unit values')
    if target.suffix.lower() not in {'.dxf', '.dwg'}:
        raise ValueError('CAD output must be DWG or DXF')
    with tempfile.TemporaryDirectory(prefix='ezarch-edit-') as tmp:
        doc, _ = read(source, Path(tmp))
        entities = [doc.entitydb.get(h) for h in handles]
        if not entities or any(e is None or not e.is_alive for e in entities):
            raise ValueError('Selection contains missing handles')
        if text is not None and any(e.dxftype() not in {'TEXT', 'MTEXT'} for e in entities):
            raise ValueError('Text replacement requires TEXT/MTEXT entities')
        for entity in entities:
            if move is not None:
                entity.translate(*move)
            if text is not None:
                if entity.dxftype() == 'TEXT':
                    entity.dxf.text = text
                else:
                    entity.text = text
        intermediate = Path(tmp) / 'edited.dxf'
        doc.saveas(intermediate)
        if target.suffix.lower() == '.dwg':
            convert(intermediate, target, version=doc.dxfversion)
        else:
            shutil.copy2(intermediate, target)
    return {'source_sha256': before, 'output_sha256': sha256(target), 'handles': handles, 'file': str(target),
            'roundtrip_note': 'DWG conversion may normalize text extent caches, spline tolerances and numeric serialization; compare actual geometry, properties and views' if target.suffix.lower() == '.dwg' else None}
