"""Validate explicitly selected wheel files before Hatch reads their contents."""
import tomllib
from pathlib import Path, PurePosixPath

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        if self.target_name != "wheel":
            return
        root = Path(self.root).resolve()
        metadata = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        wheel = metadata["tool"]["hatch"]["build"]["targets"]["wheel"]
        names = [*wheel["only-include"], *wheel["force-include"], *metadata["project"]["license-files"]]
        for name in names:
            relative = PurePosixPath(name)
            if (relative.is_absolute() or relative.as_posix() != name or ".." in relative.parts
                    or "\\" in name or ":" in name):
                raise ValueError(f"Unsafe wheel file: {name}")
            path = root
            for part in relative.parts:
                path = path / part
                if path.is_symlink() or path.is_junction():
                    raise ValueError(f"Wheel files cannot use symlinks or junctions: {name}")
            if not path.is_file() or not path.resolve().is_relative_to(root):
                raise ValueError(f"Missing or invalid wheel file: {name}")
