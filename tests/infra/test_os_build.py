"""Build-only Debian patch boundaries; every command uses a fake runner."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import build_os
import pytest


def fixture(tmp_path: Path, *, modified: bool = False):
    content = b"public fake deb fixture"
    value = {
        "schema_version": 1,
        "os_id": "debian",
        "os_codename": "trixie",
        "architecture": "amd64",
        "http_timeout_seconds": 30,
        "command_timeout_seconds": 180,
        "retries": 0,
        "packages": [
            {
                "name": "test-library",
                "version": "1.0+test2",
                "sha256": hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
            }
        ],
    }
    lock_path = tmp_path / "os.lock"
    lock_path.write_text(json.dumps(value))
    root = tmp_path / "root"
    (root / "etc").mkdir(parents=True)
    (root / "etc/os-release").write_text("ID=debian\nVERSION_CODENAME=trixie\n")
    (root / "tmp").mkdir()
    calls = []
    inventories = iter(
        [
            "test-library\t1.0+test1\nlibc6\t2.41\n",
            "test-library\t1.0+test2\nlibc6\t" + ("changed" if modified else "2.41") + "\n",
        ]
    )

    def runner(command, **kwargs):
        calls.append(command)
        output = ""
        if command[0] == "dpkg-query":
            output = next(inventories)
        elif command[:2] == ["dpkg", "--print-architecture"]:
            output = "amd64\n"
        elif "download" in command:
            (Path(kwargs["cwd"]) / "fixture.deb").write_bytes(content)
        elif command[0] == "dpkg-deb":
            output = "test-library\t1.0+test2\tamd64\n"
        return subprocess.CompletedProcess(command, 0, stdout=output, stderr="")

    return build_os.load_lock(lock_path), root, calls, runner


def test_signed_exact_patch_changes_only_locked_package(tmp_path: Path) -> None:
    lock, root, calls, runner = fixture(tmp_path)
    with (
        patch("build_os.os.geteuid", return_value=0),
        patch("build_os.os.chown"),
        patch("build_os.pwd.getpwnam", return_value=SimpleNamespace(pw_uid=1, pw_gid=1)),
    ):
        result = build_os.install(lock, root=root, runner=runner)
    assert result["only_locked_os_packages_changed"]
    apt = [command for command in calls if command[0] == "apt-get"]
    assert all(
        "Acquire::AllowInsecureRepositories=false" in command
        and "APT::Get::AllowUnauthenticated=false" in command
        for command in apt
    )
    assert any("test-library=1.0+test2" in command and "download" in command for command in apt)
    assert not any(
        "upgrade" in command or "dist-upgrade" in command or "install" in command for command in apt
    )


def test_hash_mismatch_refused_before_dpkg_install(tmp_path: Path) -> None:
    lock, root, calls, runner = fixture(tmp_path)
    lock.packages[0]["sha256"] = "0" * 64
    with (
        patch("build_os.os.geteuid", return_value=0),
        patch("build_os.os.chown"),
        patch("build_os.pwd.getpwnam", return_value=SimpleNamespace(pw_uid=1, pw_gid=1)),
        pytest.raises(RuntimeError, match="hash/size"),
    ):
        build_os.install(lock, root=root, runner=runner)
    assert not any(command[:2] == ["dpkg", "--install"] for command in calls)


def test_unrelated_package_version_change_refused(tmp_path: Path) -> None:
    lock, root, _, runner = fixture(tmp_path, modified=True)
    with (
        patch("build_os.os.geteuid", return_value=0),
        patch("build_os.os.chown"),
        patch("build_os.pwd.getpwnam", return_value=SimpleNamespace(pw_uid=1, pw_gid=1)),
        pytest.raises(RuntimeError, match="inventory"),
    ):
        build_os.install(lock, root=root, runner=runner)


def test_wrong_distribution_refused_before_apt(tmp_path: Path) -> None:
    lock, root, calls, runner = fixture(tmp_path)
    (root / "etc/os-release").write_text("ID=ubuntu\nVERSION_CODENAME=noble\n")
    with patch("build_os.os.geteuid", return_value=0), pytest.raises(RuntimeError, match="distribution"):
        build_os.install(lock, root=root, runner=runner)
    assert not calls


def test_debian_control_identity_mismatch_refused_before_install(tmp_path: Path) -> None:
    lock, root, calls, original = fixture(tmp_path)

    def runner(command, **kwargs):
        result = original(command, **kwargs)
        if command[0] == "dpkg-deb":
            result.stdout = "other-package\t1.0+test2\tamd64\n"
        return result

    with (
        patch("build_os.os.geteuid", return_value=0),
        patch("build_os.os.chown"),
        patch("build_os.pwd.getpwnam", return_value=SimpleNamespace(pw_uid=1, pw_gid=1)),
        pytest.raises(RuntimeError, match="control identity"),
    ):
        build_os.install(lock, root=root, runner=runner)
    assert not any(command[:2] == ["dpkg", "--install"] for command in calls)


def test_signed_index_failure_stops_before_download_or_install(tmp_path: Path) -> None:
    lock, root, calls, original = fixture(tmp_path)

    def runner(command, **kwargs):
        if "update" in command:
            calls.append(command)
            raise subprocess.CalledProcessError(100, command)
        return original(command, **kwargs)

    with patch("build_os.os.geteuid", return_value=0), pytest.raises(subprocess.CalledProcessError):
        build_os.install(lock, root=root, runner=runner)
    assert not any("download" in command or command[:2] == ["dpkg", "--install"] for command in calls)
