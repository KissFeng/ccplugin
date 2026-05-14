"""Tests for cortex/scripts/cli/ingest_remote.py (PR1)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
CLI = PLUGIN_ROOT / "scripts" / "cli" / "ingest_remote.py"
CLI_DIR = PLUGIN_ROOT / "scripts" / "cli"
sys.path.insert(0, str(CLI_DIR))

from lib import remote  # noqa: E402
import ingest_remote as ir  # noqa: E402


# ─────────── host detection (4) ───────────


def test_detect_source_type_github() -> None:
    assert ir.detect_source_type("https://github.com/foo/bar") == "github"


def test_detect_source_type_gitlab() -> None:
    assert ir.detect_source_type("https://gitlab.com/foo/bar") == "gitlab"


def test_detect_source_type_github_io() -> None:
    # github.io 静态站点 → website
    assert ir.detect_source_type("https://foo.github.io/site") == "website"


def test_detect_source_type_other() -> None:
    assert ir.detect_source_type("https://example.com/path") == "website"


# ─────────── git URL parse (3) ───────────


def test_parse_git_url_https() -> None:
    assert ir.parse_git_url("https://github.com/foo/bar") == (
        "github.com",
        "foo",
        "bar",
    )


def test_parse_git_url_https_dot_git() -> None:
    assert ir.parse_git_url("https://github.com/foo/bar.git") == (
        "github.com",
        "foo",
        "bar",
    )


def test_parse_git_url_ssh() -> None:
    assert ir.parse_git_url("git@github.com:foo/bar.git") == (
        "github.com",
        "foo",
        "bar",
    )


# ─────────── route_target (3) ───────────


def test_route_target_github(tmp_path: Path) -> None:
    target = ir.route_target("github", "https://github.com/foo/bar", tmp_path)
    assert target == tmp_path / "知识库" / "项目" / "github.com" / "foo" / "bar"


def test_route_target_website_no_author(tmp_path: Path) -> None:
    target = ir.route_target("website", "https://example.com/", tmp_path)
    assert (
        target == tmp_path / "知识库" / "项目" / "example.com" / "_site" / "example.com"
    )


def test_route_target_website_with_path(tmp_path: Path) -> None:
    target = ir.route_target("website", "https://example.com/docs/intro", tmp_path)
    assert target == tmp_path / "知识库" / "项目" / "example.com" / "_site" / "docs"


# ─────────── dry-run / JSON output (3) ───────────


def _run_cli(args: list[str]) -> tuple[int, dict]:
    res = subprocess.run(
        [sys.executable, str(CLI), *args],
        capture_output=True,
        text=True,
        timeout=20,
    )
    try:
        payload = (
            json.loads(res.stdout.strip().splitlines()[-1])
            if res.stdout.strip()
            else {}
        )
    except json.JSONDecodeError:
        payload = {"_raw": res.stdout}
    return res.returncode, payload


def test_dry_run_github_no_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "HOME", str(tmp_path)
    )  # no vault config -> fallback /tmp synthetic
    rc, out = _run_cli(["https://github.com/foo/bar", "--dry-run"])
    assert rc == 0, out
    assert out.get("ok") is True
    assert out.get("source_type") == "github"
    assert out.get("dry_run") is True
    assert "foo/bar" in out.get("target", "") or out.get("target", "").endswith("bar")
    # no vault files created under tmp_path
    assert not any(tmp_path.rglob("知识库")), "dry-run must not write vault"


def test_dry_run_website_no_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    rc, out = _run_cli(["https://example.com", "--dry-run"])
    assert rc == 0, out
    assert out.get("ok") is True
    assert out.get("source_type") == "website"
    assert out.get("dry_run") is True


def test_json_output_schema() -> None:
    rc, out = _run_cli(["https://github.com/foo/bar", "--dry-run"])
    assert rc == 0
    for key in ("ok", "source_type", "target"):
        assert key in out, f"missing key {key} in {out}"


# ─────────── url_security gate (1) ───────────


def test_url_security_reject_intranet(tmp_path: Path) -> None:
    # http://127.0.0.1 should fail url_security inside ingest_website.
    target = tmp_path / "out"
    result = remote.ingest_website("http://127.0.0.1/", target, depth=1, dry_run=False)
    assert result.get("ok") is False
    assert "url_security" in result.get("error", "")


# ─────────── git clone failure fail-soft (1) ───────────


def test_ingest_git_clone_failure_fail_soft(tmp_path: Path) -> None:
    # Use a bogus host that resolves to a non-existent repo to trigger git failure.
    fake_url = "https://github.com/__cortex_nonexistent_org__/__nonexistent_repo__"
    with mock.patch.object(remote, "run_git") as m_git:
        # First call = clone (fail), no further calls expected.
        m_git.return_value = subprocess.CompletedProcess(
            args=["git", "clone"],
            returncode=128,
            stdout="",
            stderr="repository not found",
        )
        result = remote.ingest_git(fake_url, tmp_path / "out", dry_run=False)
    assert result.get("ok") is False
    assert "git clone failed" in result.get("error", "")


# ─────────── route_target integration via dry-run (1) ───────────


def test_route_target_in_dry_run_output() -> None:
    rc, out = _run_cli(["https://example.com/docs", "--dry-run"])
    assert rc == 0
    # website target should include _site placeholder
    assert "_site" in out.get("target", ""), out


# ─────────── --help works (1, smoke) ───────────


def test_help_works() -> None:
    res = subprocess.run(
        [sys.executable, str(CLI), "--help"], capture_output=True, text=True, timeout=10
    )
    assert res.returncode == 0
    assert "usage" in res.stdout.lower()
