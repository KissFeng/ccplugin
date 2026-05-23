"""Validate quickadd preset shipped in plugins/tools/cortex/presets/quickadd/data.json."""

from __future__ import annotations

import json
import re
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
PRESET = PLUGIN_ROOT / "presets" / "quickadd" / "data.json"
TPL_DIR = PLUGIN_ROOT / "presets" / "seed" / "_templates"


def _load_preset() -> dict:
    return json.loads(PRESET.read_text(encoding="utf-8"))


def test_preset_exists() -> None:
    assert PRESET.exists(), f"missing quickadd preset: {PRESET}"


def test_preset_is_valid_json() -> None:
    data = _load_preset()
    assert isinstance(data, dict)
    assert "choices" in data
    assert "templateFolderPath" in data


def test_template_folder_is_underscore_templates() -> None:
    data = _load_preset()
    assert data["templateFolderPath"] == "_templates"


def test_choices_have_required_fields() -> None:
    data = _load_preset()
    for c in data["choices"]:
        assert "name" in c
        assert "type" in c
        assert "id" in c
        assert c["type"] in {"Capture", "Template", "Macro", "Multi"}


def test_referenced_templates_exist_in_plugin() -> None:
    """Each Template-type choice must reference a real plugin preset template."""
    data = _load_preset()
    missing = []
    for c in data["choices"]:
        if c.get("type") != "Template":
            continue
        tpl = c.get("template", "")
        if not tpl.startswith("_templates/"):
            continue
        rel = tpl[len("_templates/"):]
        tpl_path = TPL_DIR / rel
        if not tpl_path.exists():
            missing.append((c.get("name"), tpl))
    assert not missing, f"quickadd references missing templates: {missing}"


def test_capture_format_has_required_frontmatter() -> None:
    """Capture-type choices write inline format with frontmatter — verify minimum fields."""
    data = _load_preset()
    for c in data["choices"]:
        if c.get("type") != "Capture":
            continue
        fmt = c.get("format", "")
        assert "---" in fmt, f"{c['name']} missing frontmatter delimiter"
        assert re.search(r"type:\s*\S+", fmt), f"{c['name']} missing type field"


def test_paths_use_vault_layout() -> None:
    """Paths should target 知识库/... (not legacy locations)."""
    data = _load_preset()
    for c in data["choices"]:
        path = c.get("path", "")
        if not path:
            continue
        assert path.startswith("知识库/") or path.startswith("knowledge/"), \
            f"{c['name']} path violates vault layout: {path}"
