from __future__ import annotations

import contextlib
import copy
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import tempfile
import uuid
from pathlib import Path, PurePosixPath


class HarborError(Exception):
    pass


def read_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise HarborError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=pairs)
    except (OSError, ValueError) as e:
        raise HarborError(f"Cannot read JSON {path}: {e}") from e


def atomic_bytes(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".osharbor-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def write_json(path, value):
    atomic_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def safe_path(root, relative):
    if not isinstance(relative, str) or "\\" in relative or ":" in relative:
        raise HarborError("Invalid relative path")
    p = PurePosixPath(relative)
    if p.is_absolute() or not p.parts or ".." in p.parts:
        raise HarborError("Path must remain inside root")
    root = Path(root).resolve()
    result = root.joinpath(*p.parts)
    if not result.resolve().is_relative_to(root):
        raise HarborError("Link/reparse point escapes root")
    return result


def run_ps(script):
    if os.name != "nt":
        raise HarborError("Windows host required")
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
        "$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[Text.UTF8Encoding]::new(); " + script],
        capture_output=True, encoding="utf-8", errors="replace", timeout=45)
    if result.returncode:
        raise HarborError(result.stderr.strip() or "PowerShell failed")
    return result.stdout.strip()


def inventory():
    raw = run_ps("@(Get-Volume | Select-Object UniqueId,DriveLetter,FileSystemLabel,FileSystem,"
                 "DriveType,SizeRemaining) | ConvertTo-Json -Depth 4 -Compress")
    data = json.loads(raw)
    return data if isinstance(data, list) else [data]


class WindowsVolumes:
    def __init__(self):
        self.volumes = inventory()

    def identify(self, path):
        path = Path(path).resolve(strict=True)
        matches = [v for v in self.volumes if v.get("DriveLetter") and
                   path.drive.casefold() == (v["DriveLetter"] + ":").casefold()]
        if len(matches) != 1:
            raise HarborError("Image must be on a uniquely identified local drive")
        v = matches[0]
        if v["FileSystem"] != "NTFS":
            raise HarborError("Prototype image storage requires NTFS")
        return {"volume_id": v["UniqueId"], "relative_path": path.relative_to(path.anchor).as_posix()}

    def resolve(self, system):
        matches = [v for v in self.volumes if v.get("UniqueId") == system["volume_id"] and v.get("DriveLetter")]
        if len(matches) != 1:
            raise HarborError(f"Volume unavailable or ambiguous: {system['volume_id']}")
        return safe_path(matches[0]["DriveLetter"] + ":/", system["relative_path"])


def registry(path):
    if not Path(path).exists():
        return {"schema_version": 1, "systems": []}
    data = read_json(path)
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("systems"), list):
        raise HarborError("Unsupported registry schema")
    seen = set()
    for s in data["systems"]:
        if not isinstance(s, dict) or not re.fullmatch(r"[a-z][a-z0-9-]{0,47}", str(s.get("id", ""))):
            raise HarborError("Invalid system ID")
        if s["id"] in seen:
            raise HarborError("Duplicate system ID")
        seen.add(s["id"])
        if s.get("type") not in ("windows", "omarchy") or not isinstance(s.get("name"), str) or not s["name"].strip():
            raise HarborError("Invalid system type/name")
        if not isinstance(s.get("volume_id"), str) or not s["volume_id"]:
            raise HarborError("Missing volume identity")
        safe_path(Path.cwd(), s.get("relative_path"))
    return data


def check_image(path, kind):
    path = Path(path)
    if not path.is_file():
        raise HarborError(f"Image missing: {path}")
    with path.open("rb") as f:
        if kind == "windows":
            if path.suffix.lower() != ".vhdx" or f.read(8) != b"vhdxfile":
                raise HarborError("Windows requires a VHDX with valid file signature")
        else:
            if not path.name.lower().endswith(".vhd.vtoy") or path.stat().st_size < 512:
                raise HarborError("Omarchy requires fixed VHD named *.vhd.vtoy")
            f.seek(-512, 2)
            footer = f.read(512)
            if footer[:8] != b"conectix" or struct.unpack(">I", footer[60:64])[0] != 2:
                raise HarborError("Omarchy VHD must be fixed, not dynamic/differencing")
            checksum = struct.unpack(">I", footer[64:68])[0]
            if checksum != (~sum(footer[:64] + b"\0" * 4 + footer[68:]) & 0xffffffff):
                raise HarborError("Invalid VHD footer checksum")
            size = struct.unpack(">Q", footer[48:56])[0]
            if size + 512 != path.stat().st_size:
                raise HarborError("Fixed VHD length does not match footer")
    return {"size": path.stat().st_size, "format_check": "passed", "boot": "pending"}


def register(path, volumes, image, identifier, name, kind):
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,47}", identifier) or not name.strip():
        raise HarborError("ID must start with a-z and contain only a-z, digits or hyphens; name required")
    data = registry(path)
    location = volumes.identify(image)
    check_image(image, kind)
    if any(s["id"] == identifier or (s["volume_id"] == location["volume_id"] and
           s["relative_path"].casefold() == location["relative_path"].casefold()) for s in data["systems"]):
        raise HarborError("System ID or image already registered")
    data["systems"].append({"id": identifier, "name": name, "type": kind, **location,
        "verification": {"boot": "pending", "experimental": kind == "omarchy", "records": []}})
    write_json(path, data)
    return data["systems"][-1]


def fingerprint(path):
    # Endpoint hash detects replacement without reading hundreds of GB on every command.
    path = Path(path)
    stat = path.stat()
    with path.open("rb") as f:
        first = f.read(65536)
        f.seek(max(0, stat.st_size - 65536))
        last = f.read(65536)
    return {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns,
            "ends_sha256": hashlib.sha256(first + last).hexdigest()}


def official_link(tool, source, destination):
    result = subprocess.run([str(Path(tool).resolve()), "-i", str(source), "-o", str(destination)],
                            capture_output=True, timeout=120)
    if result.returncode or not destination.is_file() or destination.stat().st_size == 0:
        raise HarborError("VentoyVlnk failed; check privileges and official tool version")


def build(registry_path, volumes, output, tool, tool_sha256, link_runner=official_link):
    data = registry(registry_path)
    if not data["systems"]:
        raise HarborError("Register at least one image before building")
    if digest(tool).lower() != tool_sha256.lower():
        raise HarborError("VentoyVlnk SHA256 mismatch")
    output = Path(output).resolve()
    if output.exists():
        raise HarborError("Build output must be a new directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="osharbor-build-", dir=output.parent) as tmp:
        root = Path(tmp)
        generation = uuid.uuid4().hex
        records, aliases = [], []
        for index, s in enumerate(data["systems"], 1):
            source = volumes.resolve(s)
            check_image(source, s["type"])
            before = fingerprint(source)
            suffix = "vhdx" if s["type"] == "windows" else "vtoy"
            relative = f"os-harbor/{generation}/{index:03d}-{s['id']}.vlnk.{suffix}"
            destination = safe_path(root, relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            link_runner(tool, source, destination)
            if before != fingerprint(source):
                raise HarborError("Image changed during build")
            records.append({"system": s, "source": before, "path": relative, "sha256": digest(destination)})
            aliases.append({"image": "/" + relative, "alias": s["name"] +
                            (" [实验性·待验证]" if s["type"] == "omarchy" else " [待验证]")})
        manifest = {"schema_version": 1, "generation": generation, "records": records,
                    "menu_alias": aliases, "tool": {"name": "VentoyVlnk", "sha256": digest(tool)}}
        write_json(root / "manifest.json", manifest)
        write_json(root / "ventoy.fragment.json", {"menu_alias": aliases})
        os.replace(root, output)
    return manifest


def validate_bundle(bundle, volumes):
    bundle = Path(bundle)
    m = read_json(bundle / "manifest.json")
    if not isinstance(m, dict) or m.get("schema_version") != 1 or not re.fullmatch(r"[a-f0-9]{32}", str(m.get("generation", ""))):
        raise HarborError("Invalid build manifest")
    records = m.get("records")
    if not isinstance(records, list) or not records:
        raise HarborError("Empty build manifest")
    expected_aliases = []
    paths = set()
    for i, r in enumerate(records, 1):
        s = r["system"]
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,47}", s["id"]) or s["type"] not in ("windows", "omarchy"):
            raise HarborError("Invalid manifest system")
        suffix = "vhdx" if s["type"] == "windows" else "vtoy"
        expected = f"os-harbor/{m['generation']}/{i:03d}-{s['id']}.vlnk.{suffix}"
        if r["path"] != expected or expected in paths:
            raise HarborError("Invalid managed link path")
        paths.add(expected)
        if digest(safe_path(bundle, r["path"])) != r["sha256"]:
            raise HarborError("Build link checksum mismatch")
        source = volumes.resolve(s)
        check_image(source, s["type"])
        if fingerprint(source) != r["source"]:
            raise HarborError("Image changed since build; regenerate links")
        expected_aliases.append({"image": "/" + expected, "alias": s["name"] +
            (" [实验性·待验证]" if s["type"] == "omarchy" else " [待验证]")})
    if m.get("menu_alias") != expected_aliases:
        raise HarborError("Manifest menu does not match records")
    return m


def validate_config(config):
    if not isinstance(config, dict):
        raise HarborError("Ventoy config must be an object")
    if any(k.startswith("menu_alias_") or k.startswith("image_list") or k.startswith("image_blacklist") for k in config):
        raise HarborError("Mode-specific aliases or image filters require manual reconciliation before deployment")
    aliases = config.get("menu_alias", [])
    if not isinstance(aliases, list) or any(not isinstance(a, dict) or not isinstance(a.get("alias"), str)
          or not isinstance(a.get("image", a.get("dir")), str) for a in aliases):
        raise HarborError("Malformed existing menu_alias")


def merge_config(config, manifest):
    validate_config(config)
    result = copy.deepcopy(config)
    result["menu_alias"] = [a for a in result.get("menu_alias", [])
                            if not a.get("image", "").startswith("/os-harbor/")] + manifest["menu_alias"]
    return result


def validate_usb(target):
    target = Path(target).resolve(strict=True)
    if os.name != "nt" or target != Path(target.anchor) or not re.fullmatch(r"[A-Za-z]:\\", str(target)):
        raise HarborError("Target must be a Windows drive root")
    letter = target.drive[0]
    info = json.loads(run_ps(f"$p=Get-Partition -DriveLetter '{letter}'; $d=$p | Get-Disk; "
        "$v=$p | Get-Volume; $e=@(Get-Partition -DiskNumber $d.Number | Get-Volume | "
        "Where-Object FileSystemLabel -eq 'VTOYEFI'); "
        "@{bus=[string]$d.BusType; boot=[bool]$d.IsBoot; system=[bool]$d.IsSystem; "
        "label=$v.FileSystemLabel; fs=$v.FileSystem; efi=$e.Count} | ConvertTo-Json -Compress"))
    if info["bus"] != "USB" or info["boot"] or info["system"] or info["label"] != "Ventoy" or info["efi"] != 1:
        raise HarborError("Target must be a non-system USB with Ventoy data label and sibling VTOYEFI")
    if info["fs"] not in ("exFAT", "NTFS"):
        raise HarborError("Unsupported Ventoy data filesystem")
    return target


@contextlib.contextmanager
def deploy_lock(target):
    path = safe_path(target, "ventoy/.osharbor.lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as e:
        raise HarborError("Deployment lock exists; see recovery guide") from e
    try:
        os.close(fd)
        yield
    finally:
        path.unlink()


def deploy(bundle, target, volumes, target_validator=validate_usb, before_commit=None):
    target = target_validator(target)
    m = validate_bundle(bundle, volumes)
    if any(volumes.resolve(r["system"]).resolve().is_relative_to(Path(target).resolve()) for r in m["records"]):
        raise HarborError("Source images must be on a different volume from Ventoy")
    plugin = safe_path(target, "ventoy/ventoy_vhdboot.img")
    if any(r["system"]["type"] == "windows" for r in m["records"]) and (not plugin.is_file() or plugin.stat().st_size == 0):
        raise HarborError("Missing /ventoy/ventoy_vhdboot.img; install official plugin first")
    with deploy_lock(target):
        config_path = safe_path(target, "ventoy/ventoy.json")
        original = config_path.read_bytes() if config_path.exists() else None
        config = read_json(config_path) if original is not None else {}
        merged = merge_config(config, m)
        backup = safe_path(target, "ventoy/os-harbor-backups/" + uuid.uuid4().hex)
        backup.mkdir(parents=True)
        write_json(backup / "recovery.json", {"config_existed": original is not None,
                   "generation": m["generation"], "status": "prepared"})
        if original is not None:
            atomic_bytes(backup / "ventoy.json", original)
        for r in m["records"]:
            dest = safe_path(target, r["path"])
            if dest.exists() and digest(dest) != r["sha256"]:
                raise HarborError("Existing generation differs; refusing overwrite")
            atomic_bytes(dest, safe_path(bundle, r["path"]).read_bytes())
        write_json(safe_path(target, f"os-harbor/{m['generation']}/manifest.json"), m)
        if before_commit:
            before_commit()
        if (config_path.read_bytes() if config_path.exists() else None) != original:
            raise HarborError("Ventoy configuration changed concurrently; retry")
        write_json(config_path, merged)
        write_json(backup / "recovery.json", {"config_existed": original is not None,
                   "generation": m["generation"], "status": "committed"})
    return {"generation": m["generation"], "backup": str(backup), "boot": "pending"}


def verify(bundle, target, volumes, target_validator=validate_usb):
    m = validate_bundle(bundle, volumes)
    if target:
        target = target_validator(target)
        cfg = read_json(safe_path(target, "ventoy/ventoy.json"))
        validate_config(cfg)
        managed = [a for a in cfg.get("menu_alias", []) if a.get("image", "").startswith("/os-harbor/")]
        if managed != m["menu_alias"]:
            raise HarborError("Deployed aliases differ from build")
        for r in m["records"]:
            if digest(safe_path(target, r["path"])) != r["sha256"]:
                raise HarborError("Deployed link checksum mismatch")
        if any(r["system"]["type"] == "windows" for r in m["records"]):
            plugin = safe_path(target, "ventoy/ventoy_vhdboot.img")
            if not plugin.is_file() or plugin.stat().st_size == 0:
                raise HarborError("Windows boot plugin missing")
    return {"consistency": "passed", "boot": "pending", "count": len(m["records"])}
