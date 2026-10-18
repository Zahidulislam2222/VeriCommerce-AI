"""Authenticated bounded off-server archives; never deletes or overwrites backups."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import struct
import tempfile
from pathlib import Path
from typing import Any, BinaryIO

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .settings import CloudSettings

# Fixed versioned binary syntax, not environment-specific configuration.
MAGIC = b"VCBACKUP\x01"
NONCE_PREFIX_BYTES = 8
NONCE_COUNTER_BYTES = 4
KEY_BYTES = 32
TAG_BYTES = 16
INTEGER = struct.Struct(">I")


def regular(path: Path, maximum: int, *, private: bool = False) -> bytes:
    if path.is_symlink():
        raise ValueError("Backup inputs cannot be symlinks")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if private and (info.st_uid != os.getuid() or info.st_mode & 0o077):
            raise ValueError("Backup key must be current-user-owned and private")
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= maximum:
            raise ValueError("Backup input must be a nonempty bounded regular file")
        data = stream.read(maximum + 1)
        if len(data) != info.st_size:
            raise ValueError("Backup input changed or exceeded its size")
    return data


def read_key(path: Path) -> bytes:
    key = regular(path, KEY_BYTES, private=True)
    if len(key) != KEY_BYTES:
        raise ValueError("Backup requires an exact binary AES256 key")
    return key


def write_new(destination: Path, content: bytes) -> None:
    if destination.exists() or destination.is_symlink() or destination.parent.is_symlink():
        raise ValueError("Backup output must be a new regular path")
    descriptor, name = tempfile.mkstemp(prefix=".backup-", dir=destination.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        # Atomic no-clobber publication; originals and existing destinations survive.
        os.link(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def decrypt(content: bytes, key: bytes, settings: CloudSettings) -> bytes:
    from io import BytesIO

    stream = BytesIO(content)
    if stream.read(len(MAGIC)) != MAGIC:
        raise ValueError("Unsupported encrypted backup format")
    prefix = stream.read(NONCE_PREFIX_BYTES)
    length = read_length(stream)
    if length > settings.max_text_chars:
        raise ValueError("Encrypted header exceeds bound")
    header = stream.read(length)
    info = json.loads(header)
    if (
        not isinstance(info, dict)
        or set(info) != {"size", "sha256", "chunk_bytes"}
        or type(info["size"]) is not int
        or not 0 < info["size"] <= settings.backup_max_bytes
        or type(info["chunk_bytes"]) is not int
        or not 0 < info["chunk_bytes"] <= settings.backup_chunk_bytes
    ):
        raise ValueError("Invalid authenticated backup header")
    output = bytearray()
    cipher = AESGCM(key)
    sequence = 0
    while len(output) < info["size"]:
        size = read_length(stream)
        expected = min(info["chunk_bytes"], info["size"] - len(output)) + TAG_BYTES
        if size != expected:
            raise ValueError("Encrypted chunk size mismatch")
        encrypted = stream.read(size)
        if len(encrypted) != size:
            raise ValueError("Truncated encrypted backup")
        counter = sequence.to_bytes(NONCE_COUNTER_BYTES, "big")
        output.extend(cipher.decrypt(prefix + counter, encrypted, header + counter))
        sequence += 1
    if stream.read(1) or hashlib.sha256(output).hexdigest() != info["sha256"]:
        raise ValueError("Encrypted backup digest or trailing data mismatch")
    return bytes(output)


def read_length(stream: BinaryIO) -> int:
    value = stream.read(INTEGER.size)
    if len(value) != INTEGER.size:
        raise ValueError("Truncated encrypted backup length")
    return INTEGER.unpack(value)[0]


def encrypt_file(source: Path, destination: Path, key_file: Path, settings: CloudSettings) -> dict[str, Any]:
    plaintext = regular(source, settings.backup_max_bytes)
    key = read_key(key_file)
    hashed = hashlib.sha256(plaintext).hexdigest()
    header = json.dumps(
        {"size": len(plaintext), "sha256": hashed, "chunk_bytes": settings.backup_chunk_bytes}, sort_keys=True
    ).encode()
    prefix = os.urandom(NONCE_PREFIX_BYTES)
    output = bytearray(MAGIC + prefix + INTEGER.pack(len(header)) + header)
    cipher = AESGCM(key)
    for sequence, start in enumerate(range(0, len(plaintext), settings.backup_chunk_bytes)):
        counter = sequence.to_bytes(NONCE_COUNTER_BYTES, "big")
        encrypted = cipher.encrypt(
            prefix + counter, plaintext[start : start + settings.backup_chunk_bytes], header + counter
        )
        output.extend(INTEGER.pack(len(encrypted)) + encrypted)
    if decrypt(bytes(output), key, settings) != plaintext:
        raise ValueError("Backup encryption round-trip failed")
    write_new(destination, bytes(output))
    return {
        "plaintext_sha256": hashed,
        "archive_sha256": hashlib.sha256(output).hexdigest(),
        "plaintext_bytes": len(plaintext),
        "encrypted_bytes": len(output),
        "encryption_verified": True,
        "database_restore_verified": False,
        "original_retained": True,
    }


def decrypt_file(source: Path, destination: Path, key_file: Path, settings: CloudSettings) -> dict[str, Any]:
    # Format overhead is bounded by one tag/length per configured chunk plus header.
    maximum = (
        settings.backup_max_bytes
        + settings.max_text_chars
        + (settings.backup_max_bytes // settings.backup_chunk_bytes + 1) * (TAG_BYTES + INTEGER.size)
        + len(MAGIC)
        + NONCE_PREFIX_BYTES
        + INTEGER.size
    )
    plaintext = decrypt(regular(source, maximum), read_key(key_file), settings)
    write_new(destination, plaintext)
    return {
        "plaintext_sha256": hashlib.sha256(plaintext).hexdigest(),
        "plaintext_bytes": len(plaintext),
        "decrypted": True,
        "database_restore_verified": False,
    }


def retention_plan(directory: Path, settings: CloudSettings) -> dict[str, Any]:
    candidates = sorted(
        (path for path in directory.glob("*.vcbackup") if path.is_file() and not path.is_symlink()),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
        reverse=True,
    )
    return {
        "keep": [path.name for path in candidates[: settings.backup_keep_count]],
        "older": [path.name for path in candidates[settings.backup_keep_count :]],
        "deletion_enabled": False,
        "restore_verification_required": True,
        "owner_retention_policy_required": True,
    }
