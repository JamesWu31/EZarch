"""Explicit module entry points. No hidden full-project pipeline."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import sys
import time
import traceback
from pathlib import Path

from .project import read_project, write_json


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ezarch")
    sub = parser.add_subparsers(dest="module", required=True)
    sub.add_parser("doctor")
    for name in ["brief", "reference", "asset", "model", "draft", "views", "diagram", "render", "board", "audit", "review", "exchange"]:
        command = sub.add_parser(name)
        command.add_argument("input", type=Path)
        command.add_argument("--out", type=Path, required=True)
        if name in ("draft", "views"):
            command.add_argument("--only", nargs="+")
        if name == "diagram":
            command.add_argument("--level")
        if name == "render":
            command.add_argument("--source-units", choices=["mm", "m"])
            command.add_argument("--camera", default=None)
            command.add_argument("--quality", choices=["preview", "final"], default="preview")
            command.add_argument("--width", type=int, default=None)
            command.add_argument("--samples", type=int, default=None)
        if name == "reference":
            command.add_argument("--known-mm", type=float)
            command.add_argument("--pixel-distance", type=float)
        if name == "exchange":
            command.add_argument("--formats", nargs="+", default=["3dm", "dae", "glb"])
    args = parser.parse_args(argv)
    from .environment import ensure_supported_platform
    ensure_supported_platform()
    if args.module == "doctor":
        from .environment import doctor
        print(json.dumps(doctor(), ensure_ascii=False, indent=2))
        return 0
    args.input = args.input.expanduser().resolve()
    args.out = args.out.expanduser().resolve()
    if not args.input.exists():
        parser.error(f"Input not found: {args.input}")
    args.out.mkdir(parents=True, exist_ok=True)
    started = time.time()
    log = {"module": args.module, "input": str(args.input), "output": str(args.out),
           "state": "running", "started_unix": started}
    log["runtime"] = {"python": sys.version.split()[0]}
    for name in ["ezarch", "ezdxf", "pymupdf", "cadquery", "rhino3dm"]:
        try:
            log["runtime"][name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            pass
    log_path = args.out / f"{args.module}-run.json"
    write_json(log_path, log)
    try:
        if args.module == "model":
            from .geometry import generate_model
            result = generate_model(read_project(args.input), args.out)
        elif args.module in ("draft", "views"):
            from .views import generate_views
            result = generate_views(read_project(args.input), args.out, args.only)
        elif args.module in ("brief", "reference"):
            from .intake import brief, reference
            result = brief(read_project(args.input), args.out) if args.module == "brief" else reference(
                args.input, args.out, args.known_mm, args.pixel_distance)
        elif args.module == "diagram":
            from .diagrams import generate_diagrams
            result = generate_diagrams(read_project(args.input), args.out, args.level)
        elif args.module == "render":
            from .render import render
            result = render(args.input, args.out, args.camera, args.quality, args.width, args.samples, args.source_units)
        elif args.module == "board":
            from .board import compose
            result = compose(args.input, args.out)
        elif args.module == "exchange":
            from .exchange import export_scene
            result = export_scene(json.loads(args.input.read_text(encoding="utf-8")), args.out, args.formats)
        elif args.module == "audit":
            from .audit import audit
            result = audit(args.input, args.out)
        elif args.module == "review":
            from .quality import review
            result = review(args.input, args.out)
        elif args.module == "asset":
            import yaml

            from .assets import fetch_polyhaven
            spec = yaml.safe_load(args.input.read_text(encoding="utf-8"))
            if spec.get("provider") != "polyhaven":
                raise ValueError("Built-in asset adapter: provider must be polyhaven")
            result = fetch_polyhaven(spec["id"], args.out, spec.get("kind", "model"), spec.get("resolution", "1k"))
        else:
            raise ValueError(args.module)
        log.update(state="succeeded", elapsed_s=round(time.time() - started, 3), result=result)
        write_json(log_path, log)
        print(json.dumps({"module": args.module, "state": log["state"], "elapsed_s": log["elapsed_s"], "report": str(log_path)}, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        log.update(state="failed", elapsed_s=round(time.time() - started, 3),
                   error_type=type(error).__name__, error=str(error))
        write_json(log_path, log)
        (args.out / f"{args.module}-error.log").write_text(traceback.format_exc(), encoding="utf-8")
        print(json.dumps(log, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
