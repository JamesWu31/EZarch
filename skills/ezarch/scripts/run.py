"""Agent-facing entry point; selects the already prepared isolated runtime."""
import os
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
python = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
if not python.exists():
    raise SystemExit("This launcher needs the skill .venv. Use the platform bootstrap, "
                     "or run python -m ezarch.cli in another environment with ezarch installed.")
raise SystemExit(subprocess.call([str(python), "-m", "ezarch.cli", *sys.argv[1:]]))
