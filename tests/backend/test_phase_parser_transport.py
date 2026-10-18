"""Actual disposable-child IPC adversarial transport and wall-time regressions."""

from __future__ import annotations

import os
import struct
import time
from typing import Any

import pytest


def _invalid_json(_: Any, pipe: Any) -> None:
    pipe.send_bytes(b"not-json")
    pipe.close()


def _oversized(_: Any, pipe: Any) -> None:
    pipe.send_bytes(b"x" * 2048)
    pipe.close()


def _partial_frame(_: Any, pipe: Any) -> None:
    os.write(pipe.fileno(), struct.pack("!i", 1024) + b"{")
    time.sleep(10)


@pytest.mark.parametrize(
    "raw",
    [
        b"not-json",
        b"[]",
        b'{"ok":1}',
        b'{"ok":true,"result":{"kind":"execute"}}',
        b'{"ok":false,"error":[]}',
        b'{"ok":true,"result":{"kind":"image","image":{"width":"1","height":2}}}',
        b'{"ok":true,"result":{"kind":"document","pages":[1],"needs_ocr":false}}',
    ],
)
def test_untrusted_parser_json_envelope_rejects_malformed_payloads(raw: bytes) -> None:
    from vericommerce_core.uploads import decode_parser_result

    with pytest.raises(ValueError):
        decode_parser_result(raw)


@pytest.mark.parametrize("child", [_invalid_json, _oversized, _partial_frame])
def test_real_child_transport_cannot_escape_result_or_wall_budget(
    settings: Any, monkeypatch: Any, child: Any
) -> None:
    from vericommerce_core import uploads

    monkeypatch.setattr(uploads, "_child", child)
    bounded = settings.model_copy(update={"parser_timeout_seconds": 1, "parser_max_result_bytes": 1024})
    start = time.monotonic()
    with pytest.raises(ValueError):
        uploads.isolated_parse(b"{}", "application/json", bounded)
    assert time.monotonic() - start < 4
