"""Cloud adapters reject malicious packages and bind immutable synthetic content."""

from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import subprocess
import sys
import zipfile
from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx
import pytest

import infra.cloud.package as packages
from infra.cloud.benchmark import Benchmark, app
from infra.cloud.package import LAMBDA_FILES, package_lambda, package_static
from infra.cloud.settings import CloudSettings
from infra.cloud.validator import handler, sha256, validate_archive


def package(*, body: str | None = None, extra: bool = False) -> bytes:
    quote = "Fictional headphones have a graphite finish."
    draft = {
        "product_id": "fictional-headphones",
        "body": body or quote,
        "evidence": [{"source_id": "synthetic-source", "quote": quote, "sha256": sha256(quote.encode())}],
    }
    data = json.dumps(draft).encode()
    manifest = {"schema_version": 1, "classification": "synthetic-public", "draft_sha256": sha256(data)}
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr("draft.json", data)
        if extra:
            archive.writestr("../outside.txt", "test-only")
    return output.getvalue()


def test_same_lambda_and_local_validator_contract() -> None:
    content = package()
    result = validate_archive(content, CloudSettings.load())
    assert result["valid"] and result["evidence_count"] == 1
    assert handler({"archive_base64": base64.b64encode(content).decode()}, None) == result


@pytest.mark.parametrize(
    "content",
    [
        b"not a zip",
        package(extra=True),
        package(body="Unsupported product assertion"),
        package(body="secret password test-only"),
        b"",
    ],
)
def test_lambda_refuses_invalid_untrusted_packages(content: bytes) -> None:
    assert handler({"archive_base64": base64.b64encode(content).decode()}, None) == {
        "valid": False,
        "error": "invalid_synthetic_archive",
    }


def test_duplicate_names_and_high_compression_are_rejected() -> None:
    source = io.BytesIO(package())
    with zipfile.ZipFile(source, "a") as archive:
        with pytest.warns(UserWarning):
            archive.writestr("draft.json", "{}")
    with pytest.raises(ValueError):
        validate_archive(source.getvalue(), CloudSettings.load())
    settings = replace(CloudSettings.load(), max_archive_bytes=32)
    with pytest.raises(ValueError):
        validate_archive(package(), settings)


def test_high_ratio_zip_rejected_before_decompression() -> None:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", " " * 100000)
        archive.writestr("draft.json", "{}")
    with pytest.raises(ValueError, match="Unsafe archive member"):
        validate_archive(stream.getvalue(), CloudSettings.load())


def test_snapshot_hash_mutation_blocks_engine(tmp_path: Path) -> None:
    settings = CloudSettings.load()
    source = Path("infra/cloud")
    (tmp_path / settings.snapshot_file).write_bytes((source / settings.snapshot_file).read_bytes() + b" ")
    (tmp_path / settings.snapshot_sha256_file).write_bytes(
        (source / settings.snapshot_sha256_file).read_bytes()
    )
    with pytest.raises(ValueError, match="hash mismatch"):
        Benchmark(settings, tmp_path)


def test_real_asgi_requests_bound_input_abstain_and_do_not_echo_private_query() -> None:
    async def exercise() -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://example.test"
        ) as client:
            ready = await client.get("/health")
            assert ready.status_code == 200 and ready.json()["ready"]
            found = await client.post("/benchmark", json={"query": "graphite headphones", "limit": 3})
            assert found.status_code == 200 and found.json()["results"][0]["id"] == "sample-headphones"
            absent = await client.post("/benchmark", json={"query": "absentXYZ", "limit": 1})
            assert absent.json()["abstained"]
            private = await client.post("/benchmark", json={"query": "password test-only", "limit": 1})
            assert private.status_code == 400 and "password" not in private.text
            unbounded = await client.post("/benchmark", json={"query": "headphones", "limit": 999})
            assert unbounded.status_code == 400
            unexpected = await client.post(
                "/benchmark", json={"query": "headphones", "limit": 1, "tenant": "x"}
            )
            assert unexpected.status_code == 400
            assert (await client.get("/private")).status_code == 404

    asyncio.run(exercise())


def test_settings_reject_boolean_budget_and_unsafe_snapshot(tmp_path: Path) -> None:
    for changed in ({"http_port": True}, {"snapshot_file": "../private.json"}, {"http_host": "192.0.2.1"}):
        values: dict[str, Any] = {**vars(CloudSettings.load()), **changed}
        config = tmp_path / "settings.json"
        config.write_text(json.dumps(values))
        with pytest.raises(ValueError):
            CloudSettings.load(config)


def test_allowlisted_lambda_and_static_packages_exclude_credentials(tmp_path: Path) -> None:
    settings = CloudSettings.load()
    archive = tmp_path / "lambda.zip"
    first = package_lambda(archive, settings)
    second = package_lambda(tmp_path / "same.zip", settings)
    assert first == second and not first["cloud_deployed"]
    with zipfile.ZipFile(archive) as package_zip:
        assert set(package_zip.namelist()) == {
            "infra/__init__.py",
            *("infra/cloud/" + name for name in (*LAMBDA_FILES, "config.json")),
        }
        assert (
            json.loads(package_zip.read("infra/cloud/config.json"))["fixture_label"] == settings.fixture_label
        )
    static = tmp_path / "static"
    result = package_static(static, settings)
    assert not result["cloud_deployed"] and result["files"] == 7
    assert not any(".env" in name or "backup" in name for name in result["manifest"])
    with pytest.raises(ValueError):
        package_lambda(archive, settings)
    with pytest.raises(ValueError):
        package_static(static, settings)


def test_real_lambda_zip_invocation_outside_checkout(tmp_path: Path) -> None:
    archive = tmp_path / "lambda.zip"
    package_lambda(archive, CloudSettings.load())
    request = json.dumps({"archive_base64": base64.b64encode(package()).decode()})
    code = (
        "import json,sys; from infra.cloud.validator import handler; "
        "print(json.dumps(handler(json.load(sys.stdin), None)))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        input=request,
        text=True,
        capture_output=True,
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(archive)},
        timeout=10,
        check=True,
    )
    verdict = json.loads(result.stdout)
    assert verdict["valid"] and verdict["evidence_count"] == 1


def test_container_context_is_bounded_allowlisted_and_includes_shared_build_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not send repository credentials or merchant records to a Docker builder."""
    original = Path(packages.__file__).parent
    repository = tmp_path / "source"
    cloud = repository / "infra/cloud"
    cloud.mkdir(parents=True)
    public_files = {"Dockerfile", "__init__.py", "settings.py", "validator.py", "benchmark.py",
                    "runtime-requirements.lock", "snapshot.json", "snapshot.sha256"}
    for name in public_files:
        (cloud / name).write_bytes((original / name).read_bytes())
    (cloud.parent / "__init__.py").write_bytes((original.parent / "__init__.py").read_bytes())
    backend = repository / "backend"
    backend.mkdir()
    build_lock = Path(__file__).resolve().parents[2] / "backend/build-requirements.lock"
    for name in packages.CONTAINER_BUILD_INPUTS:
        (backend / name).write_bytes((build_lock.parent / name).read_bytes())
    for name in (".env", "CREDENTIALS.md", "backend/merchant.json", "infra/cloud/private-key.pem"):
        (repository / name).write_text("test-key-private-only")
    monkeypatch.setattr(packages, "__file__", str(cloud / "package.py"))
    settings = CloudSettings.load()
    destination = tmp_path / "context"
    result = packages.package_container(destination, settings)
    expected = {*("infra/cloud/" + name for name in public_files),
                "infra/cloud/config.json", "infra/__init__.py",
                *("backend/" + name for name in packages.CONTAINER_BUILD_INPUTS)}
    files = {str(path.relative_to(destination)): path.read_bytes()
             for path in destination.rglob("*") if path.is_file()}
    assert set(files) == set(result["manifest"]) == expected
    assert all(sha256(content) == result["manifest"][name] for name, content in files.items())
    for name in packages.CONTAINER_BUILD_INPUTS:
        assert files["backend/" + name] == (build_lock.parent / name).read_bytes()
    assert b"test-key-private-only" not in b"".join(files.values())
    assert not result["cloud_deployed"]
    with pytest.raises(ValueError):
        packages.package_container(destination, settings)
    link = tmp_path / "symlink-context"
    link.symlink_to(destination, target_is_directory=True)
    with pytest.raises(ValueError):
        packages.package_container(link, settings)
    bounded = tmp_path / "over-budget"
    with pytest.raises(ValueError):
        packages.package_container(bounded, replace(settings, max_members=1))
    assert not bounded.exists()


@pytest.mark.parametrize("health_path", ["/healthz", "/readyz", "/_ah/health", "/health?x=1"])
def test_cloud_health_configuration_rejects_reserved_paths(tmp_path: Path, health_path: str) -> None:
    values = {**vars(CloudSettings.load()), "benchmark_health_path": health_path}
    path = tmp_path / "config.json"
    path.write_text(json.dumps(values))
    with pytest.raises(ValueError, match="provider-reserved"):
        CloudSettings.load(path)
