"""Shared pytest fixtures + sys.path wiring for cortex-mcp tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_MCP_ROOT = Path(__file__).resolve().parent.parent
if str(_MCP_ROOT) not in sys.path:
    sys.path.insert(0, str(_MCP_ROOT))


@pytest.fixture()
def fake_vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a minimal vault skeleton and pin CORTEX_VAULT_PATH at it."""
    vault = tmp_path / "vault"
    (vault / ".obsidian").mkdir(parents=True)
    (vault / "wiki" / "10_concepts").mkdir(parents=True)
    (vault / "wiki" / "30_domains").mkdir(parents=True)
    (vault / "wiki" / "log").mkdir(parents=True)
    monkeypatch.setenv("CORTEX_VAULT_PATH", str(vault))
    return vault
