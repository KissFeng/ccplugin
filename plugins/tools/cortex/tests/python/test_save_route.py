"""Test save._resolve_path routes for kind=project / domain (alias) / source."""
from __future__ import annotations

import datetime as _dt
import sys
import unittest
from pathlib import Path

CLI_DIR = Path(__file__).resolve().parent.parent.parent / "scripts" / "cli"
sys.path.insert(0, str(CLI_DIR))

import save  # noqa: E402


class ResolvePathTest(unittest.TestCase):
    def setUp(self) -> None:
        self.vault = Path("/tmp/cortex-test-vault")
        self.now = _dt.datetime(2026, 5, 13, 10, 30)

    def test_kind_project_github(self) -> None:
        target = save._resolve_path(
            self.vault,
            {"kind": "project", "title": "foo", "host": "github.com", "org": "lazygophers", "repo": "ccplugin"},
            self.now,
        )
        self.assertEqual(
            str(target).split("cortex-test-vault/")[-1],
            "知识库/项目/github.com/lazygophers/ccplugin/foo.md",
        )

    def test_kind_project_local(self) -> None:
        target = save._resolve_path(
            self.vault,
            {"kind": "project", "title": "foo", "host": "local", "org": "myproj"},
            self.now,
        )
        self.assertEqual(
            str(target).split("cortex-test-vault/")[-1],
            "知识库/项目/local/myproj/foo.md",
        )

    def test_kind_domain_alias_routes_to_项目(self) -> None:
        # backward-compat alias: domain → project path
        target = save._resolve_path(
            self.vault,
            {"kind": "domain", "title": "bar", "host": "gitlab.com", "org": "g", "repo": "h"},
            self.now,
        )
        self.assertEqual(
            str(target).split("cortex-test-vault/")[-1],
            "知识库/项目/gitlab.com/g/h/bar.md",
        )

    def test_kind_source_rejects_repo_host(self) -> None:
        with self.assertRaises(ValueError):
            save._resolve_path(
                self.vault,
                {"kind": "source", "title": "x", "host": "github.com"},
                self.now,
            )
        with self.assertRaises(ValueError):
            save._resolve_path(
                self.vault,
                {"kind": "source", "title": "x", "host": "gitlab.my-co.com"},
                self.now,
            )

    def test_kind_source_web_default_sub(self) -> None:
        target = save._resolve_path(
            self.vault,
            {"kind": "source", "title": "post", "host": "example.com"},
            self.now,
        )
        self.assertEqual(
            str(target).split("cortex-test-vault/")[-1],
            "知识库/来源/网页/example.com/post.md",
        )

    def test_kind_source_paper(self) -> None:
        target = save._resolve_path(
            self.vault,
            {"kind": "source", "title": "p", "host": "arxiv.org", "source_sub": "论文"},
            self.now,
        )
        self.assertEqual(
            str(target).split("cortex-test-vault/")[-1],
            "知识库/来源/论文/arxiv.org/p.md",
        )


if __name__ == "__main__":
    unittest.main()
