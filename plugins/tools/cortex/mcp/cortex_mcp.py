"""Cortex memory MCP tools — L0-L4 memory system + URI addressing.

This module adds 10 new MCP tools on top of the existing search/save/ingest
suite, implementing the dual-namespace memory model defined in
`.trellis/tasks/05-12-cortex-namespace/prd.md` §4.5.

Tools:
  cortex_memory_read         L<N>://path → frontmatter + brief / full
  cortex_memory_write        write a memory file with policy validation
  cortex_memory_recall       query across L0-L3 (progressive disclosure)
  cortex_memory_forget       mark archive_pending by uri or criteria
  cortex_memory_consolidate  ledger → views consolidation (stub)
  cortex_memory_promote      level up; L2→L1 and L1→L0 require user approval
  cortex_ledger_append       append JSONL line to L4-流水账/ledger
  cortex_session_import      import Claude Code transcript (stub)
  cortex_uri_index_rebuild   scan 记忆体系/**/*.md → _meta/uri-index.json
  cortex_html_render         render an HTML template fragment with {{VAR}} subs

Return shape (uniform): {"ok": bool, "code": int, "data"?: dict, "error"?: str}

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

import datetime as _dt
import json
import re
from pathlib import Path
from typing import Any

from mcp.types import TextContent, Tool

from lib.frontmatter import dump as fm_dump
from lib.frontmatter import parse as fm_parse
from lib.lock import file_lock
from lib.vault_path import resolve_vault

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
    base = vault / "记忆体系"
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


# ── Common helpers ──────────────────────────────────────────────────


def _ok(data: dict[str, Any] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"ok": True, "code": 0}
    if data is not None:
        out["data"] = data
    return out


def _err(code: int, msg: str) -> dict[str, Any]:
    return {"ok": False, "code": code, "error": msg}


def _wrap(result: dict[str, Any]) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]


def _vault_or_err() -> tuple[Path | None, dict[str, Any] | None]:
    try:
        return resolve_vault(), None
    except RuntimeError as e:
        return None, _err(3, str(e))


def _iso_now() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Tool: cortex_memory_read ────────────────────────────────────────

MEMORY_READ_TOOL = Tool(
    name="cortex_memory_read",
    description="读记忆: 解析 L<N>:// URI → 返回 frontmatter + brief (默认) 或 full",
    inputSchema={
        "type": "object",
        "properties": {
            "uri": {"type": "string", "description": "L<N>://<path> 形如 L2://semantic/go/goroutine"},
            "full": {"type": "boolean", "default": False, "description": "true 返回完整 body, false 仅返 brief"},
        },
        "required": ["uri"],
    },
)


async def handle_memory_read(args: dict[str, Any]) -> list[TextContent]:
    uri = args.get("uri")
    if not isinstance(uri, str) or not uri:
        return _wrap(_err(5, "missing uri"))
    full = bool(args.get("full", False))
    vault, err = _vault_or_err()
    if err:
        return _wrap(err)
    assert vault is not None
    try:
        path = resolve_uri(uri, vault)
    except ValueError as e:
        return _wrap(_err(5, str(e)))
    except FileNotFoundError as e:
        return _wrap(_err(2, str(e)))
    if not path.is_file():
        return _wrap(_err(2, f"file not found: {path}"))
    text = path.read_text(encoding="utf-8")
    # L4 ledger is JSONL, not frontmatter — return raw
    if path.suffix == ".jsonl":
        return _wrap(_ok({"uri": uri, "path": str(path), "raw": text}))
    fm, body = fm_parse(text)
    brief = fm.get("brief", "")
    if not brief:
        # Fallback: first non-empty paragraph
        for para in body.strip().split("\n\n"):
            if para.strip():
                brief = para.strip().splitlines()[0][:200]
                break
    data: dict[str, Any] = {"uri": uri, "path": str(path), "frontmatter": fm, "brief": brief}
    if full:
        data["body"] = body
    return _wrap(_ok(data))


# ── Tool: cortex_memory_write ───────────────────────────────────────

MEMORY_WRITE_TOOL = Tool(
    name="cortex_memory_write",
    description="写记忆: 按 policy.levels.<L>.write 校验; L0 写入要求 user confirm",
    inputSchema={
        "type": "object",
        "properties": {
            "uri": {"type": "string"},
            "content": {"type": "string", "description": "记忆 body (markdown)"},
            "level": {"type": "string", "enum": ["L0", "L1", "L2", "L3", "L4"]},
            "weight": {"type": "number", "default": 0.5},
            "recall_when": {"type": "string", "default": ""},
            "user_confirmed": {"type": "boolean", "default": False, "description": "L0 写入需 true"},
        },
        "required": ["uri", "content", "level"],
    },
)


async def handle_memory_write(args: dict[str, Any]) -> list[TextContent]:
    uri = args.get("uri")
    content = args.get("content")
    level = args.get("level")
    if not isinstance(uri, str) or not uri:
        return _wrap(_err(5, "missing uri"))
    if not isinstance(content, str):
        return _wrap(_err(1, "missing content"))
    if level not in ("L0", "L1", "L2", "L3", "L4"):
        return _wrap(_err(4, f"invalid level: {level}"))
    weight = float(args.get("weight", 0.5))
    recall_when = str(args.get("recall_when", ""))
    user_confirmed = bool(args.get("user_confirmed", False))

    # Policy: L0 needs user confirm
    if level == "L0" and not user_confirmed:
        return _wrap(_err(4, "L0 write needs user_confirmed=true"))
    # Policy: L1 min weight 0.8 / L2 min weight 0.5
    if level == "L1" and weight < 0.8:
        return _wrap(_err(4, f"L1 write requires weight >= 0.8, got {weight}"))
    if level == "L2" and weight < 0.5:
        return _wrap(_err(4, f"L2 write requires weight >= 0.5, got {weight}"))

    vault, err = _vault_or_err()
    if err:
        return _wrap(err)
    assert vault is not None
    try:
        path = resolve_uri(uri, vault)
    except ValueError as e:
        return _wrap(_err(5, str(e)))

    # L4 ledger uses append, not this path — reject
    if path.suffix == ".jsonl":
        return _wrap(_err(4, "use cortex_ledger_append for L4://ledger/* writes"))

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
    return _wrap(_ok({"uri": uri, "path": str(path), "written_at": now}))


# ── Tool: cortex_memory_recall ──────────────────────────────────────

MEMORY_RECALL_TOOL = Tool(
    name="cortex_memory_recall",
    description="召回: 跨 L0-L3 渐进披露 (返 brief + 子节点)",
    inputSchema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "top_k": {"type": "integer", "default": 5},
            "levels": {
                "type": "array",
                "items": {"type": "string"},
                "default": ["L0", "L1", "L2", "L3"],
            },
        },
        "required": ["query"],
    },
)


_LEVEL_DIRS = {
    "L0": "L0-核心",
    "L1": "L1-长期",
    "L2": "L2-中期",
    "L3": "L3-短期",
    "L4": "L4-流水账",
}


async def handle_memory_recall(args: dict[str, Any]) -> list[TextContent]:
    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        return _wrap(_err(1, "missing query"))
    top_k = int(args.get("top_k", 5))
    levels = args.get("levels") or ["L0", "L1", "L2", "L3"]
    if not isinstance(levels, list):
        return _wrap(_err(1, "levels must be list"))

    vault, err = _vault_or_err()
    if err:
        return _wrap(err)
    assert vault is not None
    base = vault / "记忆体系"

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
            # Score: lowercased substring in recall_when / brief / body / path
            score = 0
            hay = f"{recall_when}\n{brief}\n{body}\n{path.name}".lower()
            if q_lower in hay:
                score += 1
                # Boost for matches in recall_when
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
    return _wrap(_ok({"query": query, "hits": hits[:top_k]}))


# ── Tool: cortex_memory_forget ──────────────────────────────────────

MEMORY_FORGET_TOOL = Tool(
    name="cortex_memory_forget",
    description="标记记忆 archive_pending (不删除); uri 或 criteria 二选一",
    inputSchema={
        "type": "object",
        "properties": {
            "uri": {"type": "string"},
            "criteria": {
                "type": "object",
                "description": '如 {"level": "L3", "older_than_days": 90}',
            },
        },
    },
)


async def handle_memory_forget(args: dict[str, Any]) -> list[TextContent]:
    uri = args.get("uri")
    criteria = args.get("criteria")
    if not uri and not criteria:
        return _wrap(_err(1, "provide uri or criteria"))
    vault, err = _vault_or_err()
    if err:
        return _wrap(err)
    assert vault is not None

    targets: list[Path] = []
    if uri:
        try:
            targets.append(resolve_uri(uri, vault))
        except ValueError as e:
            return _wrap(_err(5, str(e)))
        except FileNotFoundError as e:
            return _wrap(_err(2, str(e)))
    elif isinstance(criteria, dict):
        lvl = criteria.get("level")
        older = int(criteria.get("older_than_days", 0))
        sub = _LEVEL_DIRS.get(str(lvl)) if lvl else None
        roots = [vault / "记忆体系" / sub] if sub else [vault / "记忆体系"]
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
    return _wrap(_ok({"marked_count": len(marked), "marked": marked}))


# ── Tool: cortex_memory_consolidate (stub) ──────────────────────────

MEMORY_CONSOLIDATE_TOOL = Tool(
    name="cortex_memory_consolidate",
    description="触发 ledger → views 巩固 (cortex-consolidate skill 等价)",
    inputSchema={"type": "object", "properties": {}},
)


async def handle_memory_consolidate(args: dict[str, Any]) -> list[TextContent]:
    """Aggregate last week's ledger events → views + reflection links.

    week_offset = -1 (last week) by default. Reads
    `L4-流水账/ledger/<date>.jsonl` for the 7-day window and produces:
      - `views/candidates.md`: rows for entity/topic seen ≥3 times (promotion candidates)
      - `知识库/反思/连接/<YYYY-Wnn>.md`: cross-domain connections (≥3 freq)
      - `views/consolidated/<YYYY-Wnn>.md`: top-20 entities/topics for the week
    """
    week_offset = int(args.get("week_offset", -1))
    vault, err = _vault_or_err()
    if err:
        return _wrap(err)
    assert vault is not None

    today = _dt.datetime.now(tz=_dt.timezone.utc).date()
    # Anchor at week_offset weeks ago, take 7 days
    end = today + _dt.timedelta(days=7 * week_offset + 6)
    start = end - _dt.timedelta(days=6)

    ledger_dir = vault / "记忆体系" / "L4-流水账" / "ledger"
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

    # 1) candidates (freq ≥ 3)
    candidates = []
    for k, v in entity_freq.items():
        if v >= 3:
            candidates.append(("entity", k, v))
    for k, v in topic_freq.items():
        if v >= 3:
            candidates.append(("topic", k, v))

    views_dir = vault / "记忆体系" / "views"
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

    # 2) cross-domain connections (entity touching ≥3 topics)
    conn_added = 0
    cross = [(e, sorted(ts)) for e, ts in entity_topics.items() if len(ts) >= 3]
    if cross:
        conn_dir = vault / "知识库" / "反思" / "连接"
        conn_dir.mkdir(parents=True, exist_ok=True)
        conn_path = conn_dir / f"{week_tag}.md"
        with file_lock(str(conn_path)):
            with conn_path.open("a", encoding="utf-8") as fp:
                if conn_path.stat().st_size == 0:
                    fp.write(f"# 连接 {week_tag}\n\n")
                for entity, topics in cross:
                    fp.write(f"- **{entity}** ↔ {', '.join(topics)}\n")
                    conn_added += 1

    # 3) top-20 consolidated view
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

    return _wrap(_ok({
        "consolidated_file": consolidated_file,
        "candidates_added": cand_added,
        "connections_added": conn_added,
        "events_read": events_read,
        "week": week_tag,
    }))


# ── Tool: cortex_memory_promote ─────────────────────────────────────

MEMORY_PROMOTE_TOOL = Tool(
    name="cortex_memory_promote",
    description="晋级记忆: AUTO 可 L4→L3/L3→L2; L2→L1 / L1→L0 需 user_approval",
    inputSchema={
        "type": "object",
        "properties": {
            "uri": {"type": "string"},
            "target_level": {"type": "string", "enum": ["L0", "L1", "L2", "L3"]},
            "user_approved": {"type": "boolean", "default": False},
        },
        "required": ["uri", "target_level"],
    },
)


async def handle_memory_promote(args: dict[str, Any]) -> list[TextContent]:
    uri = args.get("uri")
    target = args.get("target_level")
    user_approved = bool(args.get("user_approved", False))
    if not isinstance(uri, str):
        return _wrap(_err(5, "missing uri"))
    if target not in ("L0", "L1", "L2", "L3"):
        return _wrap(_err(4, f"invalid target_level: {target}"))
    # L2→L1 and L1→L0 need approval
    if target in ("L0", "L1") and not user_approved:
        return _wrap(_err(6, f"promote to {target} needs user_approved=true"))
    vault, err = _vault_or_err()
    if err:
        return _wrap(err)
    assert vault is not None
    return _wrap(_do_promote(uri, target, vault))


def _do_promote(uri: str, target_level: str, vault: Path) -> dict[str, Any]:
    """Actually move file to new level dir, update frontmatter + uri-index."""
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

    # update uri-index.json
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


# ── Tool: cortex_ledger_append ──────────────────────────────────────

LEDGER_APPEND_TOOL = Tool(
    name="cortex_ledger_append",
    description="append 一行 JSON 到 记忆体系/L4-流水账/ledger/<date>.jsonl",
    inputSchema={
        "type": "object",
        "properties": {
            "event": {"type": "object", "description": "任意 JSON 对象, 会加 ts/event_id"},
            "date": {"type": "string", "description": "YYYY-MM-DD; 默认 UTC 今天"},
        },
        "required": ["event"],
    },
)


async def handle_ledger_append(args: dict[str, Any]) -> list[TextContent]:
    event = args.get("event")
    if not isinstance(event, dict):
        return _wrap(_err(1, "event must be object"))
    date = args.get("date") or _dt.datetime.now(tz=_dt.timezone.utc).strftime("%Y-%m-%d")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        return _wrap(_err(1, f"invalid date: {date}"))
    vault, err = _vault_or_err()
    if err:
        return _wrap(err)
    assert vault is not None
    path = vault / "记忆体系" / "L4-流水账" / "ledger" / f"{date}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"ts": _iso_now(), **event}
    line = json.dumps(record, ensure_ascii=False)
    with file_lock(path):
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    return _wrap(_ok({"path": str(path), "appended": record}))


# ── Tool: cortex_session_import (stub) ──────────────────────────────

SESSION_IMPORT_TOOL = Tool(
    name="cortex_session_import",
    description="导入 claude code transcript → sessions/<cli>/YYYY-MM/<sid>.md + ledger",
    inputSchema={
        "type": "object",
        "properties": {
            "transcript_path": {"type": "string"},
            "cli": {"type": "string", "default": "claude-code"},
        },
        "required": ["transcript_path"],
    },
)


async def handle_session_import(args: dict[str, Any]) -> list[TextContent]:
    """Import a Claude Code transcript (.jsonl) into the vault.

    Writes `L4-流水账/sessions/<cli>/<YYYY-MM>/<sid>.md` with summary +
    appends per-turn events to `L4-流水账/ledger/<date>.jsonl`. Caps at 200
    turns to avoid log explosions.
    """
    transcript_path = args.get("transcript_path")
    cli = args.get("cli") or "claude-code"
    if not isinstance(transcript_path, str) or not transcript_path:
        return _wrap(_err(1, "missing transcript_path"))
    src = Path(transcript_path).expanduser()
    if not src.is_file():
        return _wrap(_err(2, f"transcript not found: {transcript_path}"))
    if src.suffix not in (".jsonl", ".ndjson"):
        return _wrap(_err(1, f"expect .jsonl: {transcript_path}"))

    vault, err = _vault_or_err()
    if err:
        return _wrap(err)
    assert vault is not None

    # Parse turns
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
        return _wrap(_err(1, f"read transcript: {e}"))

    if not turns:
        return _wrap(_err(1, "empty transcript"))

    CAP = 200
    capped = turns[:CAP]

    # Derive metadata
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

    # Date for directory + ledger from started_at (best-effort)
    try:
        started_dt = _dt.datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    except ValueError:
        started_dt = _dt.datetime.now(tz=_dt.timezone.utc)
    yyyy_mm = started_dt.strftime("%Y-%m")
    ledger_date = started_dt.strftime("%Y-%m-%d")

    sessions_dir = vault / "记忆体系" / "L4-流水账" / "sessions" / cli / yyyy_mm
    sessions_dir.mkdir(parents=True, exist_ok=True)
    sess_path = sessions_dir / f"{sid}.md"

    # Build summary body: first ~20 turns previews
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

    # Append per-turn events to ledger
    ledger_path = vault / "记忆体系" / "L4-流水账" / "ledger" / f"{ledger_date}.jsonl"
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

    return _wrap(_ok({
        "session_uri": sess_uri,
        "session_path": str(sess_path.relative_to(vault)),
        "events_appended": appended,
        "turn_count": len(turns),
        "capped": len(turns) > CAP,
    }))


# ── Tool: cortex_uri_index_rebuild ──────────────────────────────────

URI_INDEX_REBUILD_TOOL = Tool(
    name="cortex_uri_index_rebuild",
    description="扫 记忆体系/**/*.md 提取 frontmatter.uri → 重建 _meta/uri-index.json",
    inputSchema={"type": "object", "properties": {}},
)


async def handle_uri_index_rebuild(args: dict[str, Any]) -> list[TextContent]:
    vault, err = _vault_or_err()
    if err:
        return _wrap(err)
    assert vault is not None
    base = vault / "记忆体系"
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
    return _wrap(_ok({"path": str(out), "count": len(index)}))


# ── Tool: cortex_html_render ────────────────────────────────────────

HTML_RENDER_TOOL = Tool(
    name="cortex_html_render",
    description="读 _templates/html/<template>.{html,md} → 替换 {{VAR}} → 返回字符串",
    inputSchema={
        "type": "object",
        "properties": {
            "template": {"type": "string", "description": "模板名 (无扩展)"},
            "data": {"type": "object", "description": "{VAR: value} 字典"},
        },
        "required": ["template"],
    },
)


_TEMPLATE_NAME_RE = re.compile(r"^[A-Za-z0-9_\-]+$")


async def handle_html_render(args: dict[str, Any]) -> list[TextContent]:
    template = args.get("template")
    data = args.get("data") or {}
    if not isinstance(template, str) or not _TEMPLATE_NAME_RE.match(template):
        return _wrap(_err(5, f"invalid template name: {template!r}"))
    if not isinstance(data, dict):
        return _wrap(_err(1, "data must be object"))
    vault, err = _vault_or_err()
    if err:
        return _wrap(err)
    assert vault is not None
    tpl_dir = vault / "_templates" / "html"
    src: Path | None = None
    for ext in (".html", ".md"):
        cand = tpl_dir / f"{template}{ext}"
        if cand.is_file():
            src = cand
            break
    if src is None:
        return _wrap(_err(2, f"template not found: {template}"))
    text = src.read_text(encoding="utf-8")

    def _sub(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        val = data.get(key, match.group(0))
        return str(val)

    rendered = re.sub(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}", _sub, text)
    return _wrap(_ok({"template": template, "path": str(src), "rendered": rendered}))


# ── Public registry ────────────────────────────────────────────────

MEMORY_TOOLS: list[Tool] = [
    MEMORY_READ_TOOL,
    MEMORY_WRITE_TOOL,
    MEMORY_RECALL_TOOL,
    MEMORY_FORGET_TOOL,
    MEMORY_CONSOLIDATE_TOOL,
    MEMORY_PROMOTE_TOOL,
    LEDGER_APPEND_TOOL,
    SESSION_IMPORT_TOOL,
    URI_INDEX_REBUILD_TOOL,
    HTML_RENDER_TOOL,
]

HANDLERS = {
    MEMORY_READ_TOOL.name: handle_memory_read,
    MEMORY_WRITE_TOOL.name: handle_memory_write,
    MEMORY_RECALL_TOOL.name: handle_memory_recall,
    MEMORY_FORGET_TOOL.name: handle_memory_forget,
    MEMORY_CONSOLIDATE_TOOL.name: handle_memory_consolidate,
    MEMORY_PROMOTE_TOOL.name: handle_memory_promote,
    LEDGER_APPEND_TOOL.name: handle_ledger_append,
    SESSION_IMPORT_TOOL.name: handle_session_import,
    URI_INDEX_REBUILD_TOOL.name: handle_uri_index_rebuild,
    HTML_RENDER_TOOL.name: handle_html_render,
}
