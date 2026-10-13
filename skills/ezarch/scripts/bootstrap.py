"""Install locked dependencies for the selected module; no global Python changes."""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--profile", choices=["core", "model", "draft", "render", "all", "dev"], default="core")
parser.add_argument("--install-blender", action="store_true")
args = parser.parse_args()
if sys.platform not in ("win32", "darwin"):
    raise SystemExit("EZarch releases support Windows and macOS only.")
uv = shutil.which("uv") or str(root / ".ezarch/tools" / ("uv.exe" if os.name == "nt" else "uv"))
state_file = root / ".ezarch/profiles.json"
state = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {"extras": []}
extras = set(state["extras"])
if args.profile in ("model", "draft", "all", "dev"):
    extras.add("model")
if args.profile == "dev":
    extras.add("dev")
# Add capabilities incrementally: selecting board/core later must not remove CAD.
command = [uv, "sync", "--project", str(root), "--python", "3.12", "--frozen", "--inexact"]
for extra in sorted(extras):
    command += ["--extra", extra]
subprocess.run(command, check=True)
state_file.parent.mkdir(parents=True, exist_ok=True)
state_file.write_text(json.dumps({"extras": sorted(extras)}), encoding="utf-8")
python = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
subprocess.run([str(python), "-c", "from ezarch.environment import install_font; print(install_font())"], check=True)
if args.install_blender or args.profile in ("render", "all"):
    subprocess.run([str(python), "-c", "from ezarch.environment import install_blender; print(install_blender())"], check=True)
subprocess.run([str(python), "-c", "import json; from ezarch.environment import doctor; print(json.dumps(doctor(),indent=2))"], check=True)
