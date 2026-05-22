"""Unit tests for video_understand CLI pure helpers."""

from __future__ import annotations

import base64
import importlib.util
import sys
from pathlib import Path

import pytest

CLI_DIR = Path(__file__).resolve().parent.parent.parent / "scripts" / "cli"


@pytest.fixture(scope="module")
def vu_module():
    sys.path.insert(0, str(CLI_DIR))
    spec = importlib.util.spec_from_file_location(
        "video_understand", CLI_DIR / "video_understand.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_to_video_url_http(vu_module):
    assert vu_module.to_video_url("https://x/y.mp4") == "https://x/y.mp4"


def test_to_video_url_local_mp4(vu_module, tmp_path):
    v = tmp_path / "a.mp4"
    payload = b"\x00\x00\x00\x18fake-mp4"
    v.write_bytes(payload)
    result = vu_module.to_video_url(str(v))
    assert result.startswith("data:video/mp4;base64,")
    assert base64.b64decode(result.split(",", 1)[1]) == payload


def test_to_video_url_webm_mime(vu_module, tmp_path):
    v = tmp_path / "a.webm"
    v.write_bytes(b"fake-webm")
    assert vu_module.to_video_url(str(v)).startswith("data:video/webm;base64,")


def test_to_video_url_missing(vu_module):
    with pytest.raises(FileNotFoundError):
        vu_module.to_video_url("/nonexistent/x.mp4")


def test_to_image_data_url(vu_module, tmp_path):
    img = tmp_path / "f.jpg"
    img.write_bytes(b"jpegdata")
    url = vu_module.to_image_data_url(img)
    assert url.startswith("data:image/jpeg;base64,")
    assert base64.b64decode(url.split(",", 1)[1]) == b"jpegdata"


def test_build_messages_video_url(vu_module):
    msgs = vu_module.build_messages_video_url("hi", "https://x/y.mp4")
    assert msgs[0]["content"][0] == {"type": "text", "text": "hi"}
    assert msgs[0]["content"][1] == {
        "type": "video_url",
        "video_url": {"url": "https://x/y.mp4"},
    }


def test_build_messages_frames(vu_module, tmp_path):
    frames = []
    for i in range(3):
        f = tmp_path / f"f{i}.jpg"
        f.write_bytes(f"frame{i}".encode())
        frames.append(f)
    msgs = vu_module.build_messages_frames("describe", frames)
    content = msgs[0]["content"]
    assert content[0] == {"type": "text", "text": "describe"}
    assert len(content) == 4
    for c in content[1:]:
        assert c["type"] == "image_url"
        assert c["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_strip_json_fence(vu_module):
    assert vu_module.strip_json_fence('```json\n{"a":1}\n```') == '{"a":1}'
    assert vu_module.strip_json_fence('{"a":1}') == '{"a":1}'


def test_build_extract_prompt(vu_module):
    p = vu_module.build_extract_prompt('{"x":"int"}')
    assert "video" in p.lower()
    assert '{"x":"int"}' in p


def test_resolve_mode_override(vu_module):
    assert vu_module.resolve_mode({}, {}, "frames") == "frames"
    assert vu_module.resolve_mode({"mode": "video_url"}, {}, None) == "video_url"
    assert vu_module.resolve_mode({}, {"mode": "frames"}, None) == "frames"
    assert vu_module.resolve_mode({}, {}, None) == "video_url"


def test_resolve_frames_count(vu_module):
    assert vu_module.resolve_frames_count({"frames_count": 5}, {}, None) == 5
    assert vu_module.resolve_frames_count({}, {"frames_count": 12}, None) == 12
    assert vu_module.resolve_frames_count({}, {}, None) == 8
    assert vu_module.resolve_frames_count({"frames_count": 4}, {}, 20) == 20


def test_extract_text_string(vu_module):
    p = {"choices": [{"message": {"content": "yo"}}]}
    assert vu_module.extract_text(p) == "yo"


def test_extract_text_list(vu_module):
    p = {
        "choices": [
            {
                "message": {
                    "content": [
                        {"type": "text", "text": "a"},
                        {"type": "text", "text": "b"},
                    ]
                }
            }
        ]
    }
    assert vu_module.extract_text(p) == "ab"


def test_constants(vu_module):
    assert vu_module.CONFIG_FILE == "video-understand.yaml"
    assert vu_module.DEFAULTS["mode"] == "video_url"
    assert vu_module.DEFAULTS["frames_count"] == 8


def test_extract_frames_no_ffmpeg(monkeypatch, vu_module, tmp_path):
    monkeypatch.setattr(vu_module.shutil, "which", lambda _: None)
    with pytest.raises(RuntimeError, match="ffmpeg not found"):
        vu_module.extract_frames(tmp_path / "v.mp4", 4, tmp_path)
