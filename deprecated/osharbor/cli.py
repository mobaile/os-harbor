import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path

from . import __version__
from .core import (HarborError, WindowsVolumes, build, check_image, deploy, digest,
                   register, registry, run_ps, verify, write_json)


def parser():
    p = argparse.ArgumentParser(prog="osharbor", description="Ventoy image manager — boot verification remains manual")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--registry", type=Path, default=Path("state/systems.json"))
    sub = p.add_subparsers(dest="command", required=True)
    d = sub.add_parser("doctor", help="Read-only host and image diagnostics")
    d.add_argument("--report", type=Path)
    d.add_argument("--target", type=Path)
    d.add_argument("--vlnk-tool", type=Path)
    r = sub.add_parser("register", help="Register an already prepared image")
    r.add_argument("image", type=Path)
    r.add_argument("--id", required=True)
    r.add_argument("--name", required=True)
    r.add_argument("--type", choices=["windows", "omarchy"], required=True)
    sub.add_parser("list")
    b = sub.add_parser("build", help="Generate actual vlnk files with official tool")
    b.add_argument("--output", required=True, type=Path)
    b.add_argument("--vlnk-tool", required=True, type=Path)
    b.add_argument("--tool-sha256", required=True)
    d = sub.add_parser("deploy")
    d.add_argument("--bundle", required=True, type=Path)
    d.add_argument("--target", required=True, type=Path)
    v = sub.add_parser("verify")
    v.add_argument("--bundle", required=True, type=Path)
    v.add_argument("--target", type=Path)
    return p


def doctor(args):
    report = {"version": __version__, "python": platform.python_version(),
              "platform": platform.platform(), "checks": [], "boot": "pending"}
    def check(name, action):
        try:
            value = action()
            report["checks"].append({"name": name, "status": "passed", "detail": value})
        except (HarborError, OSError, ValueError) as e:
            report["checks"].append({"name": name, "status": "blocked", "detail": str(e)})
    def firmware():
        value = run_ps("(Get-ComputerInfo -Property BiosFirmwareType).BiosFirmwareType.ToString()")
        if value != "Uefi":
            raise HarborError(f"UEFI required; detected {value}")
        return value
    check("firmware", firmware)
    check("volumes", lambda: WindowsVolumes().volumes)
    for s in registry(args.registry)["systems"]:
        check(s["id"], lambda s=s: check_image(WindowsVolumes().resolve(s), s["type"]))
    if not registry(args.registry)["systems"]:
        report["checks"].append({"name": "images", "status": "blocked", "detail": "No registered images"})
    if args.vlnk_tool:
        check("VentoyVlnk", lambda: {"path": str(args.vlnk_tool), "sha256": digest(args.vlnk_tool)})
    else:
        report["checks"].append({"name": "VentoyVlnk", "status": "blocked", "detail": "Provide --vlnk-tool"})
    if args.target:
        from .core import validate_usb
        check("usb", lambda: str(validate_usb(args.target)))
        check("windows_plugin", lambda: digest(args.target / "ventoy/ventoy_vhdboot.img"))
    if args.report:
        write_json(args.report, report)
    return report


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "list":
            result = registry(args.registry)
        elif args.command == "doctor":
            result = doctor(args)
        elif args.command == "register":
            result = register(args.registry, WindowsVolumes(), args.image, args.id, args.name, args.type)
        elif args.command == "build":
            result = build(args.registry, WindowsVolumes(), args.output, args.vlnk_tool, args.tool_sha256)
        elif args.command == "deploy":
            result = deploy(args.bundle, args.target, WindowsVolumes())
        else:
            result = verify(args.bundle, args.target, WindowsVolumes())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if args.command == "doctor" and any(c["status"] == "blocked" for c in result["checks"]) else 0
    except (HarborError, OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as e:
        print(f"osharbor: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
