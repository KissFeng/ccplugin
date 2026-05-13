"""Shared helpers for the cortex CLI memory/ledger/session/html-render modules.

Extracted from the legacy `scripts/mcp/cortex_mcp.py` MCP module so the
business logic survives the MCP removal (Phase 2a refactor). Algorithms
are unchanged — only the MCP protocol layer was stripped.
"""

from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path
from typing import Any

from .vault_path import resolve_vault

# ── URI parsing ─────────────────────────────────────────────────────

URI_RE = re.compile(r"^(L\d)://(.+)$")


def resolve_uri(uri: str, vault: Path) -> Path:
    """Resolve a `L<N>://...` URI to an absolute filesystem path under vault.

    Raises ValueError on malformed URI / unknown level.
    Raises FileNotFoundError when L4 session lookup cannot find a match.
    """
    m = URI_RE.match(uri)
    if not m:
        raise ValueError(f"URI invalid: {uri}")
    level, path = m.group(1), m.group(2)
    base = vault / "记忆"
    if level == "L0":
        return base / "L0-核心" / f"{path}.md"
    if level == "L1":
        return base / "L1-长期" / f"{path}.md"
    if level == "L2":
        return base / "L2-中期" / "semantic" / f"{path}.md"
    if level == "L3":
        return base / "L3-短期" / "episodic" / f"{path}.md"
    if level == "L4":
        if path.startswith("ledger/"):
            return base / "L4-流水账" / "ledger" / f"{path[7:]}.jsonl"
        if path.startswith("session/"):
            parts = path.split("/", 2)
            if len(parts) < 3:
                raise ValueError(f"L4 session URI malformed: {uri}")
            cli, sid = parts[1], parts[2]
            sessions_dir = base / "L4-流水账" / "sessions" / cli
            if sessions_dir.is_dir():
                for f in sessions_dir.glob(f"*/{sid}.md"):
                    return f
            raise FileNotFoundError(f"session not found: {uri}")
        raise ValueError(f"L4 path prefix unknown: {path}")
    raise ValueError(f"Unknown level: {level}")


# ── Common return helpers (replace MCP TextContent wrapping) ────────


def _ok(data: dict[str, Any] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"ok": True, "code": 0}
    if data is not None:
        out["data"] = data
    return out


def _err(code: int, msg: str) -> dict[str, Any]:
    return {"ok": False, "code": code, "error": msg}


def _vault_or_err() -> tuple[Path | None, dict[str, Any] | None]:
    try:
        return resolve_vault(), None
    except RuntimeError as e:
        return None, _err(3, str(e))


def _iso_now() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_LEVEL_DIRS = {
    "L0": "L0-核心",
    "L1": "L1-长期",
    "L2": "L2-中期",
    "L3": "L3-短期",
    "L4": "L4-流水账",
}
