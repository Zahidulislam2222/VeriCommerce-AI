"""Build-only, hash-locked Debian patching; never performs a broad OS upgrade."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pwd
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class OSBuildLock:
    schema_version: int
    os_id: str
    os_codename: str
    architecture: str
    http_timeout_seconds: int
    command_timeout_seconds: int
    retries: int
    packages: list[dict[str, Any]]


def load_lock(path: Path) -> OSBuildLock:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 16384:
        raise ValueError("OS lock must be a bounded regular public build input")
    value = OSBuildLock(**json.loads(path.read_text()))
    if (
        type(value.schema_version) is not int
        or value.schema_version != 1
        or not all(
            isinstance(item, str) and re.fullmatch(r"[a-z][a-z0-9_-]*", item)
            for item in (value.os_id, value.os_codename, value.architecture)
        )
    ):
        raise ValueError("Invalid OS lock identity")
    for budget in (value.http_timeout_seconds, value.command_timeout_seconds):
        if type(budget) is not int or not 1 <= budget <= 600:
            raise ValueError("OS build timeouts must be bounded")
    if type(value.retries) is not int or value.retries != 0:
        raise ValueError("OS downloads must not retry automatically")
    if not isinstance(value.packages, list) or not 1 <= len(value.packages) <= 8:
        raise ValueError("OS package patch set must be bounded")
    names = set()
    for item in value.packages:
        if (
            not isinstance(item, dict)
            or set(item) != {"name", "version", "sha256", "bytes"}
            or not isinstance(item["name"], str)
            or not re.fullmatch(r"[a-z0-9][a-z0-9+.-]*", item["name"])
            or not isinstance(item["version"], str)
            or not re.fullmatch(r"[0-9A-Za-z.+:~_-]+", item["version"])
            or not isinstance(item["sha256"], str)
            or not re.fullmatch(r"[a-f0-9]{64}", item["sha256"])
            or type(item["bytes"]) is not int
            or not 0 < item["bytes"] <= 16777216
            or item["name"] in names
        ):
            raise ValueError("Invalid or duplicate OS package lock")
        names.add(item["name"])
    return value


def inventory(run: Callable[..., Any]) -> dict[str, str]:
    output = run(["dpkg-query", "-W", "-f=${Package}\t${Version}\n"]).stdout
    result = dict(line.split("\t", 1) for line in output.splitlines())
    if not result:
        raise RuntimeError("Missing base OS package inventory")
    return result


def install(
    lock: OSBuildLock, *, root: Path = Path("/"), runner: Callable[..., Any] = subprocess.run
) -> dict[str, Any]:
    values = dict(
        line.split("=", 1) for line in (root / "etc/os-release").read_text().splitlines() if "=" in line
    )
    if (
        os.geteuid() != 0
        or values.get("ID", "").strip('"') != lock.os_id
        or values.get("VERSION_CODENAME", "").strip('"') != lock.os_codename
    ):
        raise RuntimeError("OS distribution/build-user mismatch; no package commands executed")

    def run(command: list[str], **kwargs: Any) -> Any:
        return runner(
            command,
            check=True,
            text=True,
            capture_output=True,
            timeout=lock.command_timeout_seconds,
            **kwargs,
        )

    if run(["dpkg", "--print-architecture"]).stdout.strip() != lock.architecture:
        raise RuntimeError("OS architecture differs from locked package")
    before = inventory(run)
    if any(item["name"] not in before for item in lock.packages):
        raise RuntimeError("Only already-installed OS packages may be patched")
    apt = [
        "apt-get",
        "-o",
        "Acquire::AllowInsecureRepositories=false",
        "-o",
        "APT::Get::AllowUnauthenticated=false",
        "-o",
        "Acquire::AllowDowngradeToInsecureRepositories=false",
        "-o",
        "Acquire::Check-Valid-Until=true",
        "-o",
        "APT::Update::Error-Mode=any",
        "-o",
        f"Acquire::Retries={lock.retries}",
        "-o",
        f"Acquire::http::Timeout={lock.http_timeout_seconds}",
        "-o",
        f"Acquire::https::Timeout={lock.http_timeout_seconds}",
    ]
    receipts = []
    try:
        updated = run([*apt, "update"])
        sandbox = pwd.getpwnam("_apt")
        for item in lock.packages:
            with tempfile.TemporaryDirectory(prefix="vericommerce-os-build-", dir=root / "tmp") as temporary:
                directory = Path(temporary)
                os.chown(directory, sandbox.pw_uid, sandbox.pw_gid)
                directory.chmod(0o755)
                run([*apt, "download", item["name"] + "=" + item["version"]], cwd=directory)
                candidates = list(directory.glob("*.deb"))
                if len(candidates) != 1 or candidates[0].is_symlink() or not candidates[0].is_file():
                    raise RuntimeError("Expected exactly one regular downloaded Debian package")
                package = candidates[0]
                if (
                    package.stat().st_size != item["bytes"]
                    or hashlib.sha256(package.read_bytes()).hexdigest() != item["sha256"]
                ):
                    raise RuntimeError("Downloaded OS package hash/size differs from lock")
                control = run(
                    [
                        "dpkg-deb",
                        "--showformat=${Package}\t${Version}\t${Architecture}\n",
                        "--show",
                        str(package),
                    ]
                ).stdout.strip()
                if control != "\t".join([item["name"], item["version"], lock.architecture]):
                    raise RuntimeError("Debian package control identity differs from lock")
                run(["dpkg", "--install", str(package)])
                receipts.append({"name": item["name"], "version": item["version"], "sha256": item["sha256"]})
        run([*apt, "check"])
        after = inventory(run)
        expected = before | {item["name"]: item["version"] for item in lock.packages}
        if after != expected:
            raise RuntimeError("OS package inventory changed outside the locked patch set")
        return {
            "only_locked_os_packages_changed": True,
            "packages": receipts,
            "signed_apt_index_required": True,
            "apt_dependency_check": True,
            "apt_update_output_sha256": hashlib.sha256(updated.stdout.encode()).hexdigest(),
        }
    finally:
        lists = root / "var/lib/apt/lists"
        if lists.exists():
            shutil.rmtree(lists)
            lists.mkdir(mode=0o755)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    lock = load_lock(args.lock)
    print(
        json.dumps(install(lock) if args.execute else {"os_packages": len(lock.packages), "executed": False})
    )


if __name__ == "__main__":
    main()
