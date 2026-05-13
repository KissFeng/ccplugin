"""Cortex ledger CLI — append events + rebuild URI index.

Extracted from legacy `scripts/mcp/cortex_mcp.py` (Phase 2a). Algorithms
unchanged. Two ops:

    python3 ledger.py append --event '{"actor":"x","type":"y"}' [--date 2026-05-13]
    python3 ledger.py uri_index_rebuild
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.cortex_common import _err, _iso_now, _ok, _vault_or_err  # noqa: E402
from lib.frontmatter import parse as fm_parse  # noqa: E402
from lib.lock import file_lock  # noqa: E402


def cli_ledger_append(args: dict[str, Any]) -> dict[str, Any]:
    event = args.get("event")
    if not isinstance(event, dict):
        return _err(1, "event must be object")
    date = args.get("date") or _dt.datetime.now(tz=_dt.timezone.utc).strftime("%Y-%m-%d")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        return _err(1, f"invalid date: {date}")
    vault, err = _vault_or_err()
    if err:
        return err
    assert vault is not None
    path = vault / "记忆" / "L4-流水账" / "ledger" / f"{date}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"ts": _iso_now(), **event}
    line = json.dumps(record, ensure_ascii=False)
    with file_lock(path):
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    return _ok({"path": str(path), "appended": record})


def cli_uri_index_rebuild(args: dict[str, Any]) -> dict[str, Any]:
    vault, err = _vault_or_err()
    if err:
        return err
    assert vault is not None
    base = vault / "记忆"
    index: dict[str, dict[str, Any]] = {}
    if base.is_dir():
        for path in base.rglob("*.md"):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            fm, _body = fm_parse(text)
            uri = fm.get("uri")
            if not isinstance(uri, str) or not uri:
                continue
            index[uri] = {
                "path": str(path.relative_to(vault)),
                "level": fm.get("level"),
                "weight": fm.get("weight"),
                "recall_when": fm.get("recall_when", ""),
                "last_recalled": fm.get("last_recalled", ""),
            }
    out = vault / "_meta" / "uri-index.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {"rebuilt_at": _iso_now(), "count": len(index), "entries": index}
    with file_lock(out):
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return _ok({"path": str(out), "count": len(index)})


def main() -> None:
    parser = argparse.ArgumentParser(description="cortex ledger CLI")
    sub = parser.add_subparsers(dest="op", required=True)

    p_append = sub.add_parser("append")
    p_append.add_argument("--event", required=True, help="JSON object, or '-' for stdin")
    p_append.add_argument("--date", help="YYYY-MM-DD, default UTC today")

    sub.add_parser("uri_index_rebuild")

    ns = parser.parse_args()
    if ns.op == "append":
        raw = sys.stdin.read() if ns.event == "-" else ns.event
        event = json.loads(raw)
        result = cli_ledger_append({"event": event, "date": ns.date})
    elif ns.op == "uri_index_rebuild":
        result = cli_uri_index_rebuild({})
    else:
        result = _err(1, f"unknown op: {ns.op}")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
