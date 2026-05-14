"""Cortex memory CLI — L0-L4 memory read/write/recall/forget/consolidate/promote.

Extracted from legacy `scripts/mcp/cortex_mcp.py`. Algorithms unchanged;
only the MCP protocol wrapper was stripped. Each operation has a
`cli_memory_<op>` function returning a `{"ok", "code", "data"|"error"}`
dict, plus a top-level argparse dispatcher for shell invocation:

    python3 memory.py read --uri L2://semantic/go/goroutine
    python3 memory.py write --uri L2://... --level L2 --content - --weight 0.7
    python3 memory.py recall --query "channel" --top-k 5
    python3 memory.py forget --uri L3://...
    python3 memory.py consolidate [--week-offset -1]
    python3 memory.py promote --uri L3://... --target-level L2 [--user-approved]

Error codes:
  0  success
  1  generic failure
  2  resource not found
  3  vault not configured
  4  policy validation failed
  5  URI malformed
  6  needs_user_approval
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.cortex_common import (  # noqa: E402
    URI_RE,
    _LEVEL_DIRS,
    _err,
    _iso_now,
    _ok,
    _vault_or_err,
    resolve_uri,
)
from lib.frontmatter import dump as fm_dump  # noqa: E402
from lib.frontmatter import parse as fm_parse  # noqa: E402
from lib.lock import file_lock  # noqa: E402


# ── memory_read ─────────────────────────────────────────────────────


def cli_memory_read(args: dict[str, Any]) -> dict[str, Any]:
    uri = args.get("uri")
    if not isinstance(uri, str) or not uri:
        return _err(5, "missing uri")
    full = bool(args.get("full", False))
    vault, err = _vault_or_err()
    if err:
        return err
    assert vault is not None
    try:
        path = resolve_uri(uri, vault)
    except ValueError as e:
        return _err(5, str(e))
    except FileNotFoundError as e:
        return _err(2, str(e))
    if not path.is_file():
        return _err(2, f"file not found: {path}")
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        return _ok({"uri": uri, "path": str(path), "raw": text})
    fm, body = fm_parse(text)
    brief = fm.get("brief", "")
    if not brief:
        for para in body.strip().split("\n\n"):
            if para.strip():
                brief = para.strip().splitlines()[0][:200]
                break
    data: dict[str, Any] = {"uri": uri, "path": str(path), "frontmatter": fm, "brief": brief}
    if full:
        data["body"] = body
    return _ok(data)


# ── memory_write ────────────────────────────────────────────────────


def cli_memory_write(args: dict[str, Any]) -> dict[str, Any]:
    uri = args.get("uri")
    content = args.get("content")
    level = args.get("level")
    if not isinstance(uri, str) or not uri:
        return _err(5, "missing uri")
    if not isinstance(content, str):
        return _err(1, "missing content")
    if level not in ("L0", "L1", "L2", "L3", "L4"):
        return _err(4, f"invalid level: {level}")
    weight = float(args.get("weight", 0.5))
    recall_when = str(args.get("recall_when", ""))
    user_confirmed = bool(args.get("user_confirmed", False))

    if level == "L0" and not user_confirmed:
        return _err(4, "L0 write needs user_confirmed=true")
    if level == "L1" and weight < 0.8:
        return _err(4, f"L1 write requires weight >= 0.8, got {weight}")
    if level == "L2" and weight < 0.5:
        return _err(4, f"L2 write requires weight >= 0.5, got {weight}")

    vault, err = _vault_or_err()
    if err:
        return err
    assert vault is not None
    try:
        path = resolve_uri(uri, vault)
    except ValueError as e:
        return _err(5, str(e))

    if path.suffix == ".jsonl":
        return _err(4, "use ledger_append for L4://ledger/* writes")

    now = _iso_now()
    fm: dict[str, Any] = {
        "uri": uri,
        "level": level,
        "weight": weight,
        "recall_when": recall_when,
        "last_recalled": "",
        "recall_count": 0,
        "created": now,
        "promote_eligible": False,
        "archive_pending": False,
    }
    text = fm_dump(fm, content if content.startswith("\n") else "\n" + content)
    path.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(path):
        path.write_text(text, encoding="utf-8")
    return _ok({"uri": uri, "path": str(path), "written_at": now})


# ── memory_recall ───────────────────────────────────────────────────


def cli_memory_recall(args: dict[str, Any]) -> dict[str, Any]:
    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        return _err(1, "missing query")
    top_k = int(args.get("top_k", 5))
    levels = args.get("levels") or ["L0", "L1", "L2", "L3"]
    if not isinstance(levels, list):
        return _err(1, "levels must be list")

    vault, err = _vault_or_err()
    if err:
        return err
    assert vault is not None
    base = vault / "记忆"

    q_lower = query.lower()
    hits: list[dict[str, Any]] = []
    for lvl in levels:
        sub = _LEVEL_DIRS.get(lvl)
        if not sub:
            continue
        root = base / sub
        if not root.is_dir():
            continue
        for path in root.rglob("*.md"):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            fm, body = fm_parse(text)
            recall_when = str(fm.get("recall_when", ""))
            brief = str(fm.get("brief", ""))
            score = 0
            hay = f"{recall_when}\n{brief}\n{body}\n{path.name}".lower()
            if q_lower in hay:
                score += 1
                if q_lower in recall_when.lower():
                    score += 3
                if q_lower in brief.lower():
                    score += 2
            if score > 0:
                hits.append(
                    {
                        "uri": str(fm.get("uri", "")),
                        "level": lvl,
                        "path": str(path),
                        "brief": brief or body.strip().splitlines()[0][:200] if body.strip() else "",
                        "score": score,
                        "weight": float(fm.get("weight", 0)) if fm.get("weight") else 0.0,
                    }
                )
    hits.sort(key=lambda h: (-h["score"], -h["weight"]))
    return _ok({"query": query, "hits": hits[:top_k]})


# ── memory_forget ───────────────────────────────────────────────────


def cli_memory_forget(args: dict[str, Any]) -> dict[str, Any]:
    uri = args.get("uri")
    criteria = args.get("criteria")
    if not uri and not criteria:
        return _err(1, "provide uri or criteria")
    vault, err = _vault_or_err()
    if err:
        return err
    assert vault is not None

    targets: list[Path] = []
    if uri:
        try:
            targets.append(resolve_uri(uri, vault))
        except ValueError as e:
            return _err(5, str(e))
        except FileNotFoundError as e:
            return _err(2, str(e))
    elif isinstance(criteria, dict):
        lvl = criteria.get("level")
        older = int(criteria.get("older_than_days", 0))
        sub = _LEVEL_DIRS.get(str(lvl)) if lvl else None
        roots = [vault / "记忆" / sub] if sub else [vault / "记忆"]
        cutoff = (
            _dt.datetime.now(tz=_dt.timezone.utc) - _dt.timedelta(days=older)
            if older
            else None
        )
        for root in roots:
            if not root.is_dir():
                continue
            for path in root.rglob("*.md"):
                if cutoff:
                    mtime = _dt.datetime.fromtimestamp(path.stat().st_mtime, tz=_dt.timezone.utc)
                    if mtime > cutoff:
                        continue
                targets.append(path)

    marked: list[str] = []
    for path in targets:
        if not path.is_file() or path.suffix != ".md":
            continue
        text = path.read_text(encoding="utf-8")
        fm, body = fm_parse(text)
        fm["archive_pending"] = True
        with file_lock(path):
            path.write_text(fm_dump(fm, body if body.startswith("\n") else "\n" + body), encoding="utf-8")
        marked.append(str(path))
    return _ok({"marked_count": len(marked), "marked": marked})


# ── memory_consolidate ──────────────────────────────────────────────


def cli_memory_consolidate(args: dict[str, Any]) -> dict[str, Any]:
    """Aggregate last week's ledger events → views + reflection links."""
    week_offset = int(args.get("week_offset", -1))
    vault, err = _vault_or_err()
    if err:
        return err
    assert vault is not None

    today = _dt.datetime.now(tz=_dt.timezone.utc).date()
    end = today + _dt.timedelta(days=7 * week_offset + 6)
    start = end - _dt.timedelta(days=6)

    ledger_dir = vault / "记忆" / "L4-流水账" / "ledger"
    entity_freq: dict[str, int] = {}
    topic_freq: dict[str, int] = {}
    entity_topics: dict[str, set[str]] = {}

    events_read = 0
    if ledger_dir.is_dir():
        for i in range(7):
            d = start + _dt.timedelta(days=i)
            f = ledger_dir / f"{d.isoformat()}.jsonl"
            if not f.is_file():
                continue
            try:
                for raw in f.read_text(encoding="utf-8").splitlines():
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        evt = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    events_read += 1
                    entity = (
                        evt.get("entity")
                        or evt.get("subject")
                        or evt.get("actor")
                        or evt.get("session_id")
                    )
                    topic = (
                        evt.get("topic")
                        or evt.get("type")
                        or evt.get("kind")
                        or evt.get("category")
                    )
                    if isinstance(entity, str) and entity:
                        entity_freq[entity] = entity_freq.get(entity, 0) + 1
                    if isinstance(topic, str) and topic:
                        topic_freq[topic] = topic_freq.get(topic, 0) + 1
                    if isinstance(entity, str) and isinstance(topic, str) and entity and topic:
                        entity_topics.setdefault(entity, set()).add(topic)
            except OSError:
                continue

    iso_year, iso_week, _ = end.isocalendar()
    week_tag = f"{iso_year}-W{iso_week:02d}"

    candidates = []
    for k, v in entity_freq.items():
        if v >= 3:
            candidates.append(("entity", k, v))
    for k, v in topic_freq.items():
        if v >= 3:
            candidates.append(("topic", k, v))

    views_dir = vault / "记忆" / "views"
    views_dir.mkdir(parents=True, exist_ok=True)
    cand_path = views_dir / "candidates.md"
    cand_added = 0
    if candidates:
        header_needed = not cand_path.is_file()
        with file_lock(str(cand_path)):
            with cand_path.open("a", encoding="utf-8") as fp:
                if header_needed:
                    fp.write("# 晋级候选\n\n| week | kind | name | freq |\n|---|---|---|---|\n")
                for kind, name, freq in candidates:
                    fp.write(f"| {week_tag} | {kind} | {name} | {freq} |\n")
                    cand_added += 1

    conn_added = 0
    cross = [(e, sorted(ts)) for e, ts in entity_topics.items() if len(ts) >= 3]
    if cross:
        conn_dir = views_dir / "connections"
        conn_dir.mkdir(parents=True, exist_ok=True)
        conn_path = conn_dir / f"{week_tag}.md"
        with file_lock(str(conn_path)):
            with conn_path.open("a", encoding="utf-8") as fp:
                if conn_path.stat().st_size == 0:
                    fp.write(f"# 连接 {week_tag}\n\n")
                for entity, topics in cross:
                    fp.write(f"- **{entity}** ↔ {', '.join(topics)}\n")
                    conn_added += 1

    top_entities = sorted(entity_freq.items(), key=lambda kv: -kv[1])[:20]
    top_topics = sorted(topic_freq.items(), key=lambda kv: -kv[1])[:20]
    cons_dir = views_dir / "consolidated"
    cons_dir.mkdir(parents=True, exist_ok=True)
    cons_path = cons_dir / f"{week_tag}.md"
    consolidated_file: str | None = None
    if top_entities or top_topics or events_read:
        with file_lock(str(cons_path)):
            lines = [f"# Consolidated {week_tag}", "",
                     f"period: {start.isoformat()} → {end.isoformat()}",
                     f"events: {events_read}", "", "## Top Entities", ""]
            for name, freq in top_entities:
                lines.append(f"- {name} ({freq})")
            lines += ["", "## Top Topics", ""]
            for name, freq in top_topics:
                lines.append(f"- {name} ({freq})")
            lines.append("")
            cons_path.write_text("\n".join(lines), encoding="utf-8")
        consolidated_file = str(cons_path.relative_to(vault))

    return _ok({
        "consolidated_file": consolidated_file,
        "candidates_added": cand_added,
        "connections_added": conn_added,
        "events_read": events_read,
        "week": week_tag,
    })


# ── memory_promote ──────────────────────────────────────────────────


def _do_promote(uri: str, target_level: str, vault: Path) -> dict[str, Any]:
    """Move file to new level dir, update frontmatter + uri-index."""
    m = URI_RE.match(uri)
    if not m:
        return _err(5, f"URI invalid: {uri}")
    rest = m.group(2)
    try:
        src_path = resolve_uri(uri, vault)
    except (ValueError, FileNotFoundError) as e:
        return _err(2, f"resolve src failed: {e}")
    if not src_path.is_file():
        return _err(2, f"uri not found: {uri}")

    new_uri = f"{target_level}://{rest}"
    try:
        new_path = resolve_uri(new_uri, vault)
    except ValueError as e:
        return _err(5, f"resolve target failed: {e}")

    text = src_path.read_text(encoding="utf-8")
    fm, body = fm_parse(text)
    if not fm:
        return _err(1, "invalid or missing frontmatter")

    fm["uri"] = new_uri
    fm["level"] = target_level
    fm["promoted_at"] = _iso_now()
    try:
        weight = float(fm.get("weight", 0.5) or 0.5)
    except (TypeError, ValueError):
        weight = 0.5
    fm["weight"] = min(1.0, weight + 0.1)

    new_path.parent.mkdir(parents=True, exist_ok=True)
    new_text = fm_dump(fm, body)
    new_path.write_text(new_text, encoding="utf-8")
    if src_path.resolve() != new_path.resolve():
        try:
            src_path.unlink()
        except OSError:
            pass

    idx_path = vault / "_meta" / "uri-index.json"
    if idx_path.is_file():
        try:
            idx = json.loads(idx_path.read_text(encoding="utf-8"))
            entries = idx.get("entries", [])
            for e in entries:
                if e.get("uri") == uri:
                    e["uri"] = new_uri
                    e["level"] = target_level
                    e["path"] = str(new_path.relative_to(vault))
                    break
            idx["entries"] = entries
            idx_path.write_text(
                json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except (json.JSONDecodeError, OSError):
            pass

    return _ok({
        "new_uri": new_uri,
        "new_path": str(new_path.relative_to(vault)),
        "old_uri": uri,
    })


def cli_memory_promote(args: dict[str, Any]) -> dict[str, Any]:
    uri = args.get("uri")
    target = args.get("target_level")
    user_approved = bool(args.get("user_approved", False))
    if not isinstance(uri, str):
        return _err(5, "missing uri")
    if target not in ("L0", "L1", "L2", "L3"):
        return _err(4, f"invalid target_level: {target}")
    if target in ("L0", "L1") and not user_approved:
        return _err(6, f"promote to {target} needs user_approved=true")
    vault, err = _vault_or_err()
    if err:
        return err
    assert vault is not None
    return _do_promote(uri, target, vault)


# ── CLI dispatcher ──────────────────────────────────────────────────


def _read_content(value: str | None) -> str:
    if value is None:
        return ""
    if value == "-":
        return sys.stdin.read()
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="cortex memory CLI")
    sub = parser.add_subparsers(dest="op", required=True)

    p_read = sub.add_parser("read")
    p_read.add_argument("--uri", required=True)
    p_read.add_argument("--full", action="store_true")

    p_write = sub.add_parser("write")
    p_write.add_argument("--uri", required=True)
    p_write.add_argument("--level", required=True, choices=["L0", "L1", "L2", "L3", "L4"])
    p_write.add_argument("--content", help="content string, or '-' for stdin")
    p_write.add_argument("--weight", type=float, default=0.5)
    p_write.add_argument("--recall-when", dest="recall_when", default="")
    p_write.add_argument("--user-confirmed", dest="user_confirmed", action="store_true")

    p_recall = sub.add_parser("recall")
    p_recall.add_argument("--query", required=True)
    p_recall.add_argument("--top-k", dest="top_k", type=int, default=5)
    p_recall.add_argument("--levels", default="L0,L1,L2,L3", help="comma-separated")

    p_forget = sub.add_parser("forget")
    p_forget.add_argument("--uri")
    p_forget.add_argument("--criteria", help="JSON criteria, e.g. '{\"level\":\"L3\",\"older_than_days\":90}'")

    p_consolidate = sub.add_parser("consolidate")
    p_consolidate.add_argument("--week-offset", dest="week_offset", type=int, default=-1)

    p_promote = sub.add_parser("promote")
    p_promote.add_argument("--uri", required=True)
    p_promote.add_argument("--target-level", dest="target_level", required=True, choices=["L0", "L1", "L2", "L3"])
    p_promote.add_argument("--user-approved", dest="user_approved", action="store_true")

    ns = parser.parse_args()
    if ns.op == "read":
        result = cli_memory_read({"uri": ns.uri, "full": ns.full})
    elif ns.op == "write":
        result = cli_memory_write(
            {
                "uri": ns.uri,
                "level": ns.level,
                "content": _read_content(ns.content),
                "weight": ns.weight,
                "recall_when": ns.recall_when,
                "user_confirmed": ns.user_confirmed,
            }
        )
    elif ns.op == "recall":
        levels = [s.strip() for s in ns.levels.split(",") if s.strip()]
        result = cli_memory_recall({"query": ns.query, "top_k": ns.top_k, "levels": levels})
    elif ns.op == "forget":
        crit = json.loads(ns.criteria) if ns.criteria else None
        result = cli_memory_forget({"uri": ns.uri, "criteria": crit})
    elif ns.op == "consolidate":
        result = cli_memory_consolidate({"week_offset": ns.week_offset})
    elif ns.op == "promote":
        result = cli_memory_promote(
            {"uri": ns.uri, "target_level": ns.target_level, "user_approved": ns.user_approved}
        )
    else:
        result = _err(1, f"unknown op: {ns.op}")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
