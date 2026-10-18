"""Authenticated archives preserve originals and fail closed on tampering."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag

from infra.cloud.backup import decrypt_file, encrypt_file, retention_plan
from infra.cloud.settings import CloudSettings


@pytest.fixture
def backup(tmp_path: Path) -> tuple[Path, Path, Path, CloudSettings]:
    original = tmp_path / "backup.sql"
    original.write_bytes(b"-- fictional test backup\nSELECT 1;\n" * 100)
    key = tmp_path / "test-key.bin"
    key.write_bytes(bytes(range(32)))
    key.chmod(0o600)
    return original, tmp_path / "archive.vcbackup", key, replace(CloudSettings.load(), backup_chunk_bytes=64)


def test_encrypt_restore_exact_bytes_and_keep_original(
    backup: tuple[Path, Path, Path, CloudSettings],
) -> None:
    original, archive, key, settings = backup
    before = original.read_bytes()
    receipt = encrypt_file(original, archive, key, settings)
    assert receipt["encryption_verified"] and not receipt["database_restore_verified"]
    assert original.read_bytes() == before and before not in archive.read_bytes()
    output = original.with_name("restored.sql")
    result = decrypt_file(archive, output, key, settings)
    assert output.read_bytes() == before and result["plaintext_sha256"] == hashlib.sha256(before).hexdigest()
    with pytest.raises(ValueError):
        encrypt_file(original, archive, key, settings)
    assert output.read_bytes() == before


@pytest.mark.parametrize("damage", ["tag", "truncated", "trailing", "wrong-key", "header"])
def test_damaged_archive_never_publishes_plaintext(
    backup: tuple[Path, Path, Path, CloudSettings], damage: str
) -> None:
    original, archive, key, settings = backup
    encrypt_file(original, archive, key, settings)
    content = bytearray(archive.read_bytes())
    if damage == "tag":
        content[-1] ^= 1
    elif damage == "truncated":
        content = content[:-8]
    elif damage == "trailing":
        content.extend(b"trailing")
    elif damage == "wrong-key":
        key.write_bytes(bytes(reversed(range(32))))
    else:
        content[20] ^= 1
    archive.write_bytes(content)
    output = original.with_name("must-not-exist.sql")
    with pytest.raises((ValueError, InvalidTag)):
        decrypt_file(archive, output, key, settings)
    assert not output.exists() and original.exists()


def test_retention_is_non_destructive_proposal(backup: tuple[Path, Path, Path, CloudSettings]) -> None:
    original, archive, key, settings = backup
    for index in range(3):
        encrypt_file(original, archive.with_name(f"{index}.vcbackup"), key, settings)
    result = retention_plan(original.parent, replace(settings, backup_keep_count=1))
    assert len(result["keep"]) == 1 and len(result["older"]) == 2 and not result["deletion_enabled"]
    assert len(list(original.parent.glob("*.vcbackup"))) == 3


def test_backup_size_and_symlink_rejected(backup: tuple[Path, Path, Path, CloudSettings]) -> None:
    original, archive, key, settings = backup
    with pytest.raises(ValueError):
        encrypt_file(original, archive, key, replace(settings, backup_max_bytes=16))
    link = original.with_name("link.sql")
    link.symlink_to(original)
    with pytest.raises(ValueError):
        encrypt_file(link, archive, key, settings)


def test_public_key_file_is_refused(backup: tuple[Path, Path, Path, CloudSettings]) -> None:
    original, archive, key, settings = backup
    key.chmod(0o644)
    with pytest.raises(ValueError, match="current-user-owned and private"):
        encrypt_file(original, archive, key, settings)
    assert not archive.exists()
