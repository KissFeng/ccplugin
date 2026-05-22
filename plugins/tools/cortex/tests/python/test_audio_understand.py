"""Unit tests for audio_understand CLI pure helpers."""

from __future__ import annotations

import base64
import importlib.util
import sys
from pathlib import Path

import pytest

CLI_DIR = Path(__file__).resolve().parent.parent.parent / "scripts" / "cli"


@pytest.fixture(scope="module")
def au_module():
    sys.path.insert(0, str(CLI_DIR))
    spec = importlib.util.spec_from_file_location(
        "audio_understand", CLI_DIR / "audio_understand.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_detect_audio_format_wav(au_module):
    mime, fmt = au_module.detect_audio_format("a.wav")
    assert mime == "audio/wav"
    assert fmt == "wav"


def test_detect_audio_format_mp3(au_module):
    mime, fmt = au_module.detect_audio_format("a.MP3")
    assert mime == "audio/mpeg"
    assert fmt == "mp3"


def test_detect_audio_format_m4a(au_module):
    mime, fmt = au_module.detect_audio_format("path/to/a.m4a")
    assert mime == "audio/mp4"
    assert fmt == "m4a"


def test_detect_audio_format_unknown_defaults_wav(au_module):
    mime, fmt = au_module.detect_audio_format("a.xyz")
    assert mime == "audio/wav"
    assert fmt == "wav"


def test_read_audio_b64(au_module, tmp_path):
    a = tmp_path / "a.wav"
    payload = b"RIFFfake-wav-data"
    a.write_bytes(payload)
    raw, mime, fmt = au_module.read_audio_b64(str(a))
    assert raw == payload
    assert mime == "audio/wav"
    assert fmt == "wav"


def test_read_audio_b64_missing(au_module):
    with pytest.raises(FileNotFoundError):
        au_module.read_audio_b64("/nonexistent/a.wav")


def test_build_messages_audio(au_module):
    msgs = au_module.build_messages_audio("hi", "AAAA", "wav")
    assert msgs == [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "hi"},
                {
                    "type": "input_audio",
                    "input_audio": {"data": "AAAA", "format": "wav"},
                },
            ],
        }
    ]


def test_extract_asr_text_top_level(au_module):
    assert au_module.extract_asr_text({"text": "hello"}) == "hello"


def test_extract_asr_text_nested_data(au_module):
    assert au_module.extract_asr_text({"data": {"text": "world"}}) == "world"


def test_extract_asr_text_missing(au_module):
    assert au_module.extract_asr_text({}) == ""
    assert au_module.extract_asr_text({"foo": "bar"}) == ""


def test_extract_chat_text_string(au_module):
    p = {"choices": [{"message": {"content": "yo"}}]}
    assert au_module.extract_chat_text(p) == "yo"


def test_extract_chat_text_list(au_module):
    p = {
        "choices": [
            {
                "message": {
                    "content": [
                        {"type": "text", "text": "x"},
                        {"type": "audio", "transcript": "skip"},
                        {"type": "text", "text": "y"},
                    ]
                }
            }
        ]
    }
    assert au_module.extract_chat_text(p) == "xy"


def test_resolve_mode(au_module):
    assert au_module.resolve_mode({}, {}, "chat") == "chat"
    assert au_module.resolve_mode({"mode": "chat"}, {}, None) == "chat"
    assert au_module.resolve_mode({}, {"mode": "asr"}, None) == "asr"
    assert au_module.resolve_mode({}, {}, None) == "asr"


def test_constants(au_module):
    assert au_module.CONFIG_FILE == "audio-understand.yaml"
    assert au_module.DEFAULTS["mode"] == "asr"


def test_audio_b64_roundtrip(au_module, tmp_path):
    a = tmp_path / "x.mp3"
    payload = b"\xff\xfbmp3-data"
    a.write_bytes(payload)
    raw, _, fmt = au_module.read_audio_b64(str(a))
    assert fmt == "mp3"
    b64 = base64.b64encode(raw).decode("ascii")
    assert base64.b64decode(b64) == payload
