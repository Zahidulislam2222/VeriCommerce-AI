"""Deterministic public artifacts contain explicitly allowlisted source/data only."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Any

from .backup import regular, write_new
from .benchmark import Benchmark
from .settings import CloudSettings
from .validator import sha256

# The code/package file set is a fixed protocol boundary, not customer data.
LAMBDA_FILES = ("__init__.py", "settings.py", "validator.py")
STATIC_FILES = ("index.html", "style.css", "app.js", "staticwebapp.config.json")
CONTAINER_FILES = (
    "Dockerfile", "__init__.py", "settings.py", "validator.py", "benchmark.py", "runtime-requirements.lock",
)
CONTAINER_SNAPSHOTS = ("snapshot.json", "snapshot.sha256")
CONTAINER_BUILD_INPUTS = ("build-requirements.lock", "os-requirements.lock", "build_os.py")


def package_container(destination: Path, settings: CloudSettings) -> dict[str, Any]:
    root = Path(__file__).parent
    if (destination.exists() or destination.is_symlink()
            or any(path.is_symlink() for path in destination.parents)):
        raise ValueError("Container destination must be new with no symlink ancestors")
    if (settings.snapshot_file, settings.snapshot_sha256_file) != CONTAINER_SNAPSHOTS:
        raise ValueError("Container snapshot names must match the fixed Docker package contract")
    engine = Benchmark(settings, root)
    contents = {
        "infra/__init__.py": regular(root.parent / "__init__.py", settings.max_expanded_bytes),
        **{"backend/" + name: regular(root.parent.parent / "backend" / name, settings.max_expanded_bytes)
           for name in CONTAINER_BUILD_INPUTS},
        **{"infra/cloud/" + name: regular(root / name, settings.max_expanded_bytes)
           for name in (*CONTAINER_FILES, *CONTAINER_SNAPSHOTS)},
        "infra/cloud/config.json": json.dumps(vars(settings), sort_keys=True).encode(),
    }
    if len(contents) > settings.max_members or sum(map(len, contents.values())) > settings.max_expanded_bytes:
        raise ValueError("Container context exceeds configured file or byte budget")
    destination.mkdir(mode=0o700)
    for name, content in contents.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        write_new(path, content)
    return {
        "files": len(contents), "bytes": sum(map(len, contents.values())),
        "snapshot_sha256": engine.snapshot_sha256,
        "manifest": {name: sha256(content) for name, content in contents.items()}, "cloud_deployed": False,
    }


def package_lambda(destination: Path, settings: CloudSettings) -> dict[str, Any]:
    root = Path(__file__).parent
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        parent = zipfile.ZipInfo("infra/__init__.py")
        parent.compress_type = zipfile.ZIP_DEFLATED
        parent.external_attr = 0o100644 << 16
        archive.writestr(parent, regular(root.parent / "__init__.py", settings.max_expanded_bytes))
        for name in (*LAMBDA_FILES, "config.json"):
            content = (
                json.dumps(vars(settings), sort_keys=True).encode()
                if name == "config.json"
                else regular(root / name, settings.max_expanded_bytes)
            )
            item = zipfile.ZipInfo("infra/cloud/" + name)
            item.compress_type = zipfile.ZIP_DEFLATED
            item.external_attr = 0o100644 << 16
            archive.writestr(item, content)
    content = output.getvalue()
    write_new(destination, content)
    return {
        "lambda_package_sha256": sha256(content),
        "bytes": len(content),
        "files": len(LAMBDA_FILES) + 2,
        "cloud_deployed": False,
    }


def package_static(destination: Path, settings: CloudSettings) -> dict[str, Any]:
    root = Path(__file__).parent
    engine = Benchmark(settings, root)
    if destination.exists() or destination.is_symlink():
        raise ValueError("Static destination must be new")
    contents = {name: regular(root / "static" / name, settings.max_expanded_bytes) for name in STATIC_FILES}
    contents["config.json"] = json.dumps(vars(settings), sort_keys=True).encode()
    contents[settings.snapshot_file] = regular(root / settings.snapshot_file, settings.max_expanded_bytes)
    contents[settings.snapshot_sha256_file] = regular(
        root / settings.snapshot_sha256_file, settings.max_text_chars
    )
    destination.mkdir(mode=0o700)
    for name, content in contents.items():
        write_new(destination / name, content)
    return {
        "files": len(contents),
        "snapshot_sha256": engine.snapshot_sha256,
        "manifest": {name: sha256(content) for name, content in contents.items()},
        "cloud_deployed": False,
    }
