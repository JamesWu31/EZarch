"""Create a portable skill archive without environments or user project artifacts."""
import argparse
import hashlib
import tomllib
import zipfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
skill = root / 'skills/ezarch'
excluded = {'.venv', '.ezarch', '__pycache__', '.pytest_cache', '.ruff_cache', 'dist', 'build'}
args.out.mkdir(parents=True, exist_ok=True)
version = tomllib.loads((skill / 'pyproject.toml').read_text())['project']['version']
archive = args.out / f'ezarch-{version}-skill.zip'
files = [p for p in skill.rglob('*') if p.is_file() and not any(x in excluded for x in p.relative_to(skill).parts) and p.suffix not in {'.pyc', '.pyo'} and p.name != '.DS_Store']
with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as z:
    for file in sorted(files):
        z.write(file, Path('ezarch') / file.relative_to(skill))
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
archive.with_suffix('.zip.sha256').write_text(f'{digest}  {archive.name}\n')
print(f'{archive}: {len(files)} files, SHA256 {digest}')
