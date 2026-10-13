"""Versioned, platform-aware runtime discovery and optional local installation."""
from __future__ import annotations

import hashlib
import importlib.metadata
import os
import platform
import plistlib
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path

from .project import skill_root, write_json

BLENDER_VERSION = "4.5.11"
BLENDER_RELEASE = "https://mirror.blender.org/release/Blender4.5/"
BLENDER_FILES = {
    "Darwin-arm64": ("blender-4.5.11-macos-arm64.dmg", "1fad76c7da9451c7d6db99f1a5ed3c0a1a461d0aa07bf2b639e2fb4804ca4f13"),
    "Darwin-x86_64": ("blender-4.5.11-macos-x64.dmg", "d5b0e77ab3baf3cfdf8a80847b3b716ec7448ecd8e299564b7f5a934427224fc"),
    "Windows-AMD64": ("blender-4.5.11-windows-x64.zip", "e11d3a8e4d4249be5a7db4a9325c1f670037d4233467c3b0bda181001efe44d3"),
}


def ensure_supported_platform():
    if platform.system() not in ("Darwin", "Windows"):
        raise RuntimeError("EZarch releases support Windows and macOS only")


def install_font():
    """Install only EZarch's uniquely named open font in the current user's scope."""
    ensure_supported_platform()
    source = skill_root() / "assets/fonts/EZarchFang.ttf"
    folder = (Path.home() / "Library/Fonts" if platform.system() == "Darwin" else
              Path(os.environ["LOCALAPPDATA"]) / "Microsoft/Windows/Fonts")
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / source.name
    if target.exists() and target.read_bytes() != source.read_bytes():
        raise RuntimeError(f"A different font already occupies {target}; refusing to replace it")
    if not target.exists():
        shutil.copy2(source, target)
    if platform.system() == "Windows":
        import ctypes
        import winreg
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows NT\CurrentVersion\Fonts") as key:
            winreg.SetValueEx(key, "EZarch Fang Regular (TrueType)", 0, winreg.REG_SZ, str(target))
        ctypes.windll.gdi32.AddFontResourceW(str(target))
        result = ctypes.c_size_t()
        ctypes.windll.user32.SendMessageTimeoutW(0xffff, 0x001D, 0, 0, 2, 1000, ctypes.byref(result))
    return str(target)


def find_blender() -> str | None:
    candidates = [os.environ.get("EZARCH_BLENDER"), shutil.which("blender")]
    cache = skill_root() / ".ezarch/tools"
    candidates += [str(p) for p in cache.glob("**/blender.exe")]
    candidates += [str(p) for p in cache.glob("**/Blender.app/Contents/MacOS/Blender")]
    candidates += ["/Applications/Blender.app/Contents/MacOS/Blender",
                   str(Path.home() / "Applications/Blender.app/Contents/MacOS/Blender")]
    for variable in ("ProgramFiles", "ProgramFiles(x86)"):
        root = os.environ.get(variable)
        if root:
            candidates += [str(p) for p in Path(root).glob("Blender Foundation/Blender*/blender.exe")]
    for value in candidates:
        if not value or not Path(value).is_file():
            continue
        try:
            first = subprocess.check_output([value, "--version"], text=True, timeout=20).splitlines()[0]
            if first.startswith("Blender 4.5."):
                return value
        except (OSError, subprocess.SubprocessError):
            continue
    return None


def install_blender() -> str:
    ensure_supported_platform()
    existing = find_blender()
    if existing:
        return existing
    key = f"{platform.system()}-{platform.machine()}"
    if key not in BLENDER_FILES:
        raise RuntimeError(f"No tested Blender installation profile for {key}")
    filename, expected = BLENDER_FILES[key]
    destination = skill_root() / ".ezarch/tools" / f"blender-{BLENDER_VERSION}"
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / filename
    if not archive.exists() or hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
        temporary = archive.with_suffix(archive.suffix + ".part")
        request = urllib.request.Request(BLENDER_RELEASE + filename, headers={"User-Agent": "EZarch/0.1"})
        with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as stream:
            shutil.copyfileobj(response, stream)
        if hashlib.sha256(temporary.read_bytes()).hexdigest() != expected:
            temporary.unlink()
            raise RuntimeError("Blender download SHA-256 mismatch")
        temporary.replace(archive)
    if filename.endswith(".zip"):
        with zipfile.ZipFile(archive) as z:
            for member in z.infolist():
                if not (destination / member.filename).resolve().is_relative_to(destination.resolve()):
                    raise RuntimeError("Unsafe archive member")
            z.extractall(destination)
    else:
        attached = subprocess.check_output(["hdiutil", "attach", "-nobrowse", "-readonly", "-plist", str(archive)])
        entries = plistlib.loads(attached)["system-entities"]
        mount = next(Path(v["mount-point"]) for v in entries if "mount-point" in v)
        try:
            app = next(mount.glob("*.app"))
            subprocess.run(["ditto", str(app), str(destination / "Blender.app")], check=True)
        finally:
            subprocess.run(["hdiutil", "detach", str(mount)], check=True)
    executable = find_blender()
    if not executable:
        raise RuntimeError("Blender installed but version probe failed; inspect OS launch authorization")
    return executable


def doctor(out: Path | None = None):
    packages = {}
    for name in ("ezarch", "ezdxf", "pymupdf", "cadquery", "cadquery-ocp", "rhino3dm", "trimesh", "pycollada"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    result = {"system": platform.system(), "architecture": platform.machine(),
              "python": platform.python_version(), "blender": find_blender(), "packages": packages,
              "native_apps": "deferred", "ifc": "deferred"}
    if out:
        write_json(out, result)
    return result
