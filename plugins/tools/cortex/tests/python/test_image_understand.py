"""Unit tests for image_understand CLI pure helpers."""

from __future__ import annotations

import base64
import importlib.util
import json
import sys
from pathlib import Path

import pytest

CLI_DIR = Path(__file__).resolve().parent.parent.parent / "scripts" / "cli"


@pytest.fixture(scope="module")
def iu_module():
    sys.path.insert(0, str(CLI_DIR))
    spec = importlib.util.spec_from_file_location(
        "image_understand", CLI_DIR / "image_understand.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_to_image_url_http_passthrough(iu_module):
    url = "https://example.com/foo.png"
    assert iu_module.to_image_url(url) == url


def test_to_image_url_data_passthrough(iu_module):
    data_url = "data:image/png;base64,iVBORw0K"
    assert iu_module.to_image_url(data_url) == data_url


def test_to_image_url_local_file_b64(iu_module, tmp_path):
    img = tmp_path / "x.png"
    payload = b"\x89PNG\r\n\x1a\nfakepng"
    img.write_bytes(payload)
    result = iu_module.to_image_url(str(img))
    assert result.startswith("data:image/png;base64,")
    b64 = result.split(",", 1)[1]
    assert base64.b64decode(b64) == payload


def test_to_image_url_jpeg_mime(iu_module, tmp_path):
    img = tmp_path / "x.jpeg"
    img.write_bytes(b"fakejpeg")
    assert iu_module.to_image_url(str(img)).startswith("data:image/jpeg;base64,")


def test_to_image_url_missing_file(iu_module):
    with pytest.raises(FileNotFoundError):
        iu_module.to_image_url("/nonexistent/abc.png")


def test_build_messages_structure(iu_module):
    msgs = iu_module.build_messages("hello", "https://x/y.png")
    assert msgs == [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "hello"},
                {"type": "image_url", "image_url": {"url": "https://x/y.png"}},
            ],
        }
    ]


def test_build_extract_prompt_includes_schema(iu_module):
    schema = '{"title":"string","date":"YYYY-MM-DD"}'
    prompt = iu_module.build_extract_prompt(schema)
    assert "JSON" in prompt
    assert schema in prompt
    assert "ONLY" in prompt or "only" in prompt.lower()


def test_strip_json_fence_with_fence(iu_module):
    raw = '```json\n{"a":1}\n```'
    assert iu_module.strip_json_fence(raw) == '{"a":1}'


def test_strip_json_fence_no_fence(iu_module):
    assert iu_module.strip_json_fence('{"a":1}') == '{"a":1}'


def test_strip_json_fence_generic_fence(iu_module):
    raw = '```\n{"a":1}\n```'
    assert iu_module.strip_json_fence(raw) == '{"a":1}'


def test_extract_text_string_content(iu_module):
    payload = {"choices": [{"message": {"content": "hello world"}}]}
    assert iu_module.extract_text(payload) == "hello world"


def test_extract_text_list_content(iu_module):
    payload = {
        "choices": [
            {
                "message": {
                    "content": [
                        {"type": "text", "text": "part1 "},
                        {"type": "text", "text": "part2"},
                        {"type": "other", "text": "skipped"},
                    ]
                }
            }
        ]
    }
    assert iu_module.extract_text(payload) == "part1 part2"


def test_extract_text_missing_choices(iu_module):
    assert iu_module.extract_text({}) == ""


def test_constants(iu_module):
    assert iu_module.CONFIG_FILE == "image-understand.yaml"
    assert "default_provider" in iu_module.DEFAULTS
    assert iu_module.DEFAULTS["temperature"] == 0.3


def test_json_roundtrip_of_extract_helpers(iu_module):
    schema = json.dumps({"name": "string", "qty": "integer"})
    prompt = iu_module.build_extract_prompt(schema)
    # ensure prompt is a single non-empty string
    assert isinstance(prompt, str) and len(prompt) > 0
