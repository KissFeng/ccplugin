"""Tests for lib helpers: vault_path, frontmatter, wikilinks, lock."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from lib.frontmatter import dump, parse
from lib.lock import file_lock
from lib.vault_path import resolve_vault
from lib.wikilinks import add_block_ids, slugify


def test_resolve_vault_from_env(fake_vault: Path) -> None:
    assert resolve_vault() == fake_vault


def test_resolve_vault_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("CORTEX_VAULT_PATH", raising=False)
    monkeypatch.delenv("OBSIDIAN_VAULT", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
    with pytest.raises(RuntimeError):
        resolve_vault()


def test_frontmatter_roundtrip() -> None:
    text = dump(
        {"type": "concept", "title": "x", "tags": ["a", "b"], "aliases": []},
        "hello\n",
    )
    fm, body = parse(text)
    assert fm["type"] == "concept"
    assert fm["tags"] == ["a", "b"]
    assert fm["aliases"] == []
    assert body == "hello\n"


def test_frontmatter_no_fm() -> None:
    fm, body = parse("just body\n")
    assert fm == {}
    assert body == "just body\n"


def test_slugify_basic() -> None:
    assert slugify("Hello World!") == "hello-world"
    assert slugify("  spaced  out  ") == "spaced-out"
    assert slugify("") == "untitled"


def test_slugify_cjk_preserved() -> None:
    # Non-ASCII letters survive (Obsidian handles unicode paths fine).
    out = slugify("中文 标题")
    assert "中文" in out and "标题" in out


def test_add_block_ids_paragraphs() -> None:
    body = "Paragraph one.\n\nParagraph two with more text.\n"
    out, ids = add_block_ids(body)
    assert len(ids) == 2
    for bid in ids:
        assert bid.startswith("cortex-")
        assert f"^{bid}" in out


def test_add_block_ids_skips_headings_and_existing() -> None:
    body = "# Heading\n\nSome para. ^cortex-deadbeef\n\nAnother para.\n"
    out, ids = add_block_ids(body)
    # Heading skipped, existing block-id preserved, only third para gets new id.
    assert len(ids) == 1
    assert "^cortex-deadbeef" in out


def test_file_lock_serializes(tmp_path: Path) -> None:
    target = tmp_path / "x.lock"
    order: list[str] = []

    def worker(label: str, hold: float) -> None:
        with file_lock(str(target), timeout=5.0):
            order.append(f"in:{label}")
            time.sleep(hold)
            order.append(f"out:{label}")

    t1 = threading.Thread(target=worker, args=("a", 0.2))
    t2 = threading.Thread(target=worker, args=("b", 0.0))
    t1.start()
    time.sleep(0.05)
    t2.start()
    t1.join()
    t2.join()
    # 'a' must fully complete (in→out) before 'b' enters.
    assert order.index("out:a") < order.index("in:b")


def test_file_lock_timeout(tmp_path: Path) -> None:
    target = tmp_path / "y.lock"

    started = threading.Event()
    release = threading.Event()

    def holder() -> None:
        with file_lock(str(target), timeout=5.0):
            started.set()
            release.wait(timeout=5.0)

    th = threading.Thread(target=holder)
    th.start()
    started.wait(timeout=2.0)
    try:
        with pytest.raises(TimeoutError):
            with file_lock(str(target), timeout=0.2):
                pass
    finally:
        release.set()
        th.join()
