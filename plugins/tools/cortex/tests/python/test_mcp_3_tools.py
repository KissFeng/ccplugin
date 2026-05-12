"""Test 3 MCP tools full implementation: consolidate / promote / session_import."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PLUGIN / "mcp"))


def _vault(tmp_path: Path) -> Path:
    v = tmp_path / "vault"
    for d in [
        "_meta",
        ".obsidian",
        "记忆体系/L0-核心",
        "记忆体系/L1-长期/procedural",
        "记忆体系/L2-中期/semantic",
        "记忆体系/L3-短期/episodic",
        "记忆体系/L4-流水账/ledger",
        "记忆体系/L4-流水账/sessions",
        "记忆体系/views",
        "知识库/反思/连接",
    ]:
        (v / d).mkdir(parents=True, exist_ok=True)
    (v / "_meta/version.json").write_text('{"preset":"lyt","lang":"zh-CN"}', encoding="utf-8")
    (v / "_meta/uri-index.json").write_text(
        '{"version":1,"entries":[]}', encoding="utf-8"
    )
    return v


def _parse_result(r):
    """Extract dict from list[TextContent]."""
    assert isinstance(r, list) and r
    txt = r[0].text if hasattr(r[0], "text") else str(r[0])
    return json.loads(txt)


def _run(coro):
    return asyncio.run(coro)


def test_consolidate_empty_ledger(tmp_path, monkeypatch):
    import cortex_mcp

    v = _vault(tmp_path)
    monkeypatch.setenv("CORTEX_VAULT_PATH", str(v))
    monkeypatch.delenv("OBSIDIAN_VAULT", raising=False)
    r = _run(cortex_mcp.handle_memory_consolidate({}))
    d = _parse_result(r)
    assert d["ok"] is True
    assert d["data"]["events_read"] == 0
    assert d["data"]["candidates_added"] == 0


def test_consolidate_with_events(tmp_path, monkeypatch):
    import cortex_mcp
    import datetime as dt

    v = _vault(tmp_path)
    monkeypatch.setenv("CORTEX_VAULT_PATH", str(v))
    monkeypatch.delenv("OBSIDIAN_VAULT", raising=False)
    # write events into ledger for last week
    today = dt.datetime.now(tz=dt.timezone.utc).date()
    end = today + dt.timedelta(days=-1)
    start = end - dt.timedelta(days=6)
    ledger_dir = v / "记忆体系/L4-流水账/ledger"
    f = ledger_dir / f"{start.isoformat()}.jsonl"
    lines = []
    for _ in range(4):
        lines.append(json.dumps({"entity": "alice", "topic": "auth"}))
    for _ in range(3):
        lines.append(json.dumps({"entity": "bob", "topic": "review"}))
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")

    r = _run(cortex_mcp.handle_memory_consolidate({}))
    d = _parse_result(r)
    assert d["ok"] is True
    assert d["data"]["events_read"] == 7
    assert d["data"]["candidates_added"] >= 2  # alice freq=4, bob freq=3
    # consolidated file written
    assert d["data"]["consolidated_file"]
    assert (v / d["data"]["consolidated_file"]).is_file()
    # candidates.md exists
    assert (v / "记忆体系/views/candidates.md").is_file()


def test_promote_l3_to_l2_auto(tmp_path, monkeypatch):
    import cortex_mcp

    v = _vault(tmp_path)
    monkeypatch.setenv("CORTEX_VAULT_PATH", str(v))
    monkeypatch.delenv("OBSIDIAN_VAULT", raising=False)
    # URI scheme: L3://<rest> → L3-短期/episodic/<rest>.md (path doubles 'episodic')
    src = v / "记忆体系/L3-短期/episodic/2026-05-12/T0900-test.md"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text(
        "---\nuri: L3://2026-05-12/T0900-test\nlevel: L3\nweight: 0.5\n"
        "created: 2026-05-12T09:00:00Z\n---\n\n## brief\n\ntest\n",
        encoding="utf-8",
    )
    # also seed uri-index
    idx = v / "_meta/uri-index.json"
    idx.write_text(
        json.dumps({"version": 1, "entries": [
            {"uri": "L3://2026-05-12/T0900-test", "level": "L3",
             "path": "记忆体系/L3-短期/episodic/2026-05-12/T0900-test.md"}
        ]}, ensure_ascii=False),
        encoding="utf-8",
    )

    r = _run(cortex_mcp.handle_memory_promote({
        "uri": "L3://2026-05-12/T0900-test", "target_level": "L2"
    }))
    d = _parse_result(r)
    assert d["ok"] is True, d
    assert d["data"]["new_uri"] == "L2://2026-05-12/T0900-test"
    new_p = v / d["data"]["new_path"]
    assert new_p.is_file()
    assert not src.is_file()  # moved
    # frontmatter updated
    content = new_p.read_text(encoding="utf-8")
    assert "level: L2" in content
    assert "uri: L2://2026-05-12/T0900-test" in content
    # weight bumped
    assert "weight: 0.6" in content
    # uri-index updated
    idx_data = json.loads(idx.read_text(encoding="utf-8"))
    assert idx_data["entries"][0]["uri"] == "L2://2026-05-12/T0900-test"
    assert idx_data["entries"][0]["level"] == "L2"


def test_promote_l2_to_l1_needs_user(tmp_path, monkeypatch):
    import cortex_mcp

    v = _vault(tmp_path)
    monkeypatch.setenv("CORTEX_VAULT_PATH", str(v))
    monkeypatch.delenv("OBSIDIAN_VAULT", raising=False)
    f = v / "记忆体系/L2-中期/semantic/test.md"
    f.write_text(
        "---\nuri: L2://semantic/test\nlevel: L2\nweight: 0.6\n---\n",
        encoding="utf-8",
    )
    r = _run(cortex_mcp.handle_memory_promote({
        "uri": "L2://semantic/test", "target_level": "L1"
    }))
    d = _parse_result(r)
    assert d["ok"] is False
    assert d["code"] == 6


def test_promote_l1_to_l0_needs_user(tmp_path, monkeypatch):
    import cortex_mcp

    v = _vault(tmp_path)
    monkeypatch.setenv("CORTEX_VAULT_PATH", str(v))
    monkeypatch.delenv("OBSIDIAN_VAULT", raising=False)
    r = _run(cortex_mcp.handle_memory_promote({
        "uri": "L1://procedural/test", "target_level": "L0"
    }))
    d = _parse_result(r)
    assert d["ok"] is False
    assert d["code"] == 6


def test_session_import_basic(tmp_path, monkeypatch):
    import cortex_mcp

    v = _vault(tmp_path)
    monkeypatch.setenv("CORTEX_VAULT_PATH", str(v))
    monkeypatch.delenv("OBSIDIAN_VAULT", raising=False)

    transcript = tmp_path / "abc123.jsonl"
    transcript.write_text(
        json.dumps({"role": "user", "content": "hello",
                    "ts": "2026-05-12T10:00:00Z"}) + "\n"
        + json.dumps({"role": "assistant", "content": "hi",
                      "ts": "2026-05-12T10:00:01Z"}) + "\n",
        encoding="utf-8",
    )

    r = _run(cortex_mcp.handle_session_import({"transcript_path": str(transcript)}))
    d = _parse_result(r)
    assert d["ok"] is True
    assert d["data"]["turn_count"] == 2
    assert d["data"]["events_appended"] == 2
    # session file created
    sess = list((v / "记忆体系/L4-流水账/sessions").rglob("*.md"))
    assert len(sess) == 1
    assert sess[0].name == "abc123.md"
    # ledger appended
    ledger_files = list((v / "记忆体系/L4-流水账/ledger").rglob("*.jsonl"))
    assert ledger_files
    lines = ledger_files[0].read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    rec = json.loads(lines[0])
    assert rec["type"] == "session_event"
    assert rec["session_id"] == "abc123"


def test_session_import_missing_file(tmp_path, monkeypatch):
    import cortex_mcp

    v = _vault(tmp_path)
    monkeypatch.setenv("CORTEX_VAULT_PATH", str(v))
    monkeypatch.delenv("OBSIDIAN_VAULT", raising=False)
    r = _run(cortex_mcp.handle_session_import({
        "transcript_path": str(tmp_path / "nope.jsonl")
    }))
    d = _parse_result(r)
    assert d["ok"] is False
    assert d["code"] == 2
