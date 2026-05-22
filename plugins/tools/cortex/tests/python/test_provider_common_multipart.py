"""Smoke test http_multipart payload construction."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

CLI_DIR = Path(__file__).resolve().parent.parent.parent / "scripts" / "cli"


@pytest.fixture(scope="module")
def pc_module():
    sys.path.insert(0, str(CLI_DIR))
    spec = importlib.util.spec_from_file_location(
        "_provider_common", CLI_DIR / "_provider_common.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_http_multipart_payload_structure(pc_module):
    captured = {}

    def fake_http_request(url, method, headers, body, timeout):
        captured["url"] = url
        captured["method"] = method
        captured["headers"] = headers
        captured["body"] = body
        return 200, b'{"ok":true}', None

    with patch.object(pc_module, "http_request", side_effect=fake_http_request):
        status, raw, err = pc_module.http_multipart(
            "https://api.example.com/v1/audio/transcriptions",
            headers={"Authorization": "Bearer test"},
            fields={"model": "whisper-1", "language": "zh"},
            files=[("file", "a.wav", b"audio-data", "audio/wav")],
            timeout=30,
        )

    assert status == 200
    assert err is None
    assert captured["method"] == "POST"
    ctype = captured["headers"]["Content-Type"]
    assert ctype.startswith("multipart/form-data; boundary=")
    assert captured["headers"]["Authorization"] == "Bearer test"
    body = captured["body"]
    assert b'name="model"' in body
    assert b"whisper-1" in body
    assert b'name="language"' in body
    assert b"zh" in body
    assert b'name="file"; filename="a.wav"' in body
    assert b"Content-Type: audio/wav" in body
    assert b"audio-data" in body
    assert body.endswith(b"--\r\n")


def test_http_multipart_empty_fields(pc_module):
    captured = {}

    def fake_http_request(url, method, headers, body, timeout):
        captured["body"] = body
        return 200, b"{}", None

    with patch.object(pc_module, "http_request", side_effect=fake_http_request):
        pc_module.http_multipart(
            "https://x",
            files=[("file", "a.wav", b"X", "audio/wav")],
        )
    assert b'name="file"; filename="a.wav"' in captured["body"]
