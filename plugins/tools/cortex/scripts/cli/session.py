"""Cortex session CLI — import claude-code transcript into vault.

Extracted from legacy `scripts/mcp/cortex_mcp.py` (Phase 2a). Algorithm
unchanged. Writes `L4-流水账/sessions/<cli>/<YYYY-MM>/<sid>.md` with a
summary and appends per-turn events to `L4-流水账/ledger/<date>.jsonl`.

Usage:

    python3 session.py import --transcript-path <path.jsonl> [--cli claude-code]
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.cortex_common import _err, _iso_now, _ok, _vault_or_err  # noqa: E402
from lib.frontmatter import dump as fm_dump  # noqa: E402
from lib.lock import file_lock  # noqa: E402


def cli_session_import(args: dict[str, Any]) -> dict[str, Any]:
    """Import a Claude Code transcript (.jsonl) into the vault.

    Caps at 200 turns to avoid log explosions.
    """
    transcript_path = args.get("transcript_path")
    cli = args.get("cli") or "claude-code"
    if not isinstance(transcript_path, str) or not transcript_path:
        return _err(1, "missing transcript_path")
    src = Path(transcript_path).expanduser()
    if not src.is_file():
        return _err(2, f"transcript not found: {transcript_path}")
    if src.suffix not in (".jsonl", ".ndjson"):
        return _err(1, f"expect .jsonl: {transcript_path}")

    vault, err = _vault_or_err()
    if err:
        return err
    assert vault is not None

    turns: list[dict[str, Any]] = []
    try:
        for raw in src.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                turns.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    except OSError as e:
        return _err(1, f"read transcript: {e}")

    if not turns:
        return _err(1, "empty transcript")

    CAP = 200
    capped = turns[:CAP]

    sid = (
        capped[0].get("session_id")
        or capped[0].get("sessionId")
        or src.stem
    )
    sid = str(sid)

    def _ts(t: dict[str, Any]) -> str | None:
        for k in ("ts", "timestamp", "time", "created_at"):
            v = t.get(k)
            if isinstance(v, str) and v:
                return v
        return None

    started_at = _ts(capped[0]) or _iso_now()
    ended_at = _ts(capped[-1]) or started_at

    try:
        started_dt = _dt.datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    except ValueError:
        started_dt = _dt.datetime.now(tz=_dt.timezone.utc)
    yyyy_mm = started_dt.strftime("%Y-%m")
    ledger_date = started_dt.strftime("%Y-%m-%d")

    sessions_dir = vault / "记忆" / "L4-流水账" / "sessions" / cli / yyyy_mm
    sessions_dir.mkdir(parents=True, exist_ok=True)
    sess_path = sessions_dir / f"{sid}.md"

    PREVIEW_N = 20
    PREVIEW_LEN = 200
    body_lines = [f"# Session {sid}", "", f"- cli: {cli}", f"- started: {started_at}",
                  f"- ended: {ended_at}", f"- turns: {len(turns)} (imported: {len(capped)})",
                  f"- source: {src}", "", "## 摘要 (前 20 条)", ""]
    for i, t in enumerate(capped[:PREVIEW_N]):
        role = t.get("role") or t.get("type") or "?"
        content = t.get("content") or t.get("text") or t.get("message") or ""
        if isinstance(content, (list, dict)):
            content = json.dumps(content, ensure_ascii=False)[:PREVIEW_LEN]
        else:
            content = str(content)[:PREVIEW_LEN]
        body_lines.append(f"### turn {i} · {role}")
        body_lines.append("")
        body_lines.append(content)
        body_lines.append("")

    sess_uri = f"L4://session/{cli}/{sid}"
    fm = {
        "uri": sess_uri,
        "level": "L4",
        "cli": cli,
        "session_id": sid,
        "started_at": started_at,
        "ended_at": ended_at,
        "turn_count": len(turns),
        "source_path": str(src),
        "created": _iso_now(),
    }
    sess_path.write_text(fm_dump(fm, "\n".join(body_lines) + "\n"), encoding="utf-8")

    ledger_path = vault / "记忆" / "L4-流水账" / "ledger" / f"{ledger_date}.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    appended = 0
    with file_lock(str(ledger_path)):
        with ledger_path.open("a", encoding="utf-8") as fp:
            for idx, t in enumerate(capped):
                role = t.get("role") or t.get("type") or "?"
                content = t.get("content") or t.get("text") or t.get("message") or ""
                if isinstance(content, (list, dict)):
                    preview = json.dumps(content, ensure_ascii=False)[:160]
                else:
                    preview = str(content)[:160]
                rec = {
                    "ts": _ts(t) or _iso_now(),
                    "type": "session_event",
                    "session_id": sid,
                    "cli": cli,
                    "turn_idx": idx,
                    "role": role,
                    "content_preview": preview,
                }
                fp.write(json.dumps(rec, ensure_ascii=False) + "\n")
                appended += 1

    return _ok({
        "session_uri": sess_uri,
        "session_path": str(sess_path.relative_to(vault)),
        "events_appended": appended,
        "turn_count": len(turns),
        "capped": len(turns) > CAP,
    })


def main() -> None:
    parser = argparse.ArgumentParser(description="cortex session import CLI")
    sub = parser.add_subparsers(dest="op", required=True)

    p_import = sub.add_parser("import")
    p_import.add_argument("--transcript-path", dest="transcript_path", required=True)
    p_import.add_argument("--cli", default="claude-code")

    ns = parser.parse_args()
    if ns.op == "import":
        result = cli_session_import({"transcript_path": ns.transcript_path, "cli": ns.cli})
    else:
        result = _err(1, f"unknown op: {ns.op}")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
