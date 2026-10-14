"""Launch the bundled Blender worker; the caller never converts files manually."""
import json
import subprocess
from pathlib import Path

from .environment import find_blender, install_blender
from .project import skill_root


def render(source: Path, out: Path, camera=None, quality="preview", width=None, samples=None, source_units=None):
    if source.suffix.lower() in {".obj", ".ply", ".stl"} and not source_units:
        raise ValueError("Unitless mesh input requires explicit --source-units mm|m")
    if (width is not None and width < 64) or (samples is not None and samples < 1):
        raise ValueError("Render width must be at least 64 pixels and samples positive")
    executable = find_blender() or install_blender()
    command = [executable, "--background", "--factory-startup", "--disable-autoexec", "--python-exit-code", "1",
               "--python", str(skill_root() / "scripts/blender_scene.py"), "--",
               "--input", str(source), "--out", str(out), "--quality", quality]
    if camera:
        command += ["--camera", camera]
    if width:
        command += ["--width", str(width)]
    if samples:
        command += ["--samples", str(samples)]
    if source_units:
        command += ["--source-units", source_units]
    out.mkdir(parents=True, exist_ok=True)
    with (out / "blender.log").open("w", encoding="utf-8") as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=False)
    if result.returncode:
        raise RuntimeError(f"Blender failed ({result.returncode}); inspect {out / 'blender.log'}")
    report = out / "render-report.json"
    if not report.exists():
        raise RuntimeError("Blender exited without a render report")
    data = json.loads(report.read_text(encoding="utf-8"))
    for item in data["images"]:
        if not (out / item["file"]).is_file():
            raise RuntimeError(f"Missing rendered image: {item['file']}")
    return data
