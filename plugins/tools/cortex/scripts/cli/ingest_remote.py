"""`cortex_ingest_remote` CLI — github/gitlab clone + website crawl 远程入口 (PR1).

Thin shim over `lib/remote.py` helpers. Pipeline (host-routed):

  github.com / gitlab.com -> shallow clone -> per-file note + _index.md
  其他 host (含 github.io)   -> sitemap / BFS crawl -> sanitize + mask + hash

落档:
  github/gitlab -> <vault>/知识库/项目/<host>/<org>/<repo>/
  website      -> <vault>/知识库/项目/<host>/_site/<slug>/

本 PR 仅落 CLI + wrapper + 测试; install_wrappers/install_cron/SKILL/docs 留 PR3。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.remote import (  # noqa: E402
    DEFAULT_DEPTH,
    detect_source_type,
    ingest_git,
    ingest_website,
    parse_git_url,  # re-export for tests
    route_target,
)
from lib.vault_path import resolve_vault  # noqa: E402

__all__ = [
    "DEFAULT_DEPTH",
    "detect_source_type",
    "parse_git_url",
    "route_target",
    "ingest_git",
    "ingest_website",
    "cli_ingest_remote",
    "main",
]


def cli_ingest_remote(args: dict) -> dict:
    url = args.get("url")
    if not isinstance(url, str) or not url.strip():
        raise ValueError("cortex_ingest_remote: 'url' required (non-empty string)")
    source_type = detect_source_type(url)
    try:
        vault = resolve_vault()
    except RuntimeError:
        if args.get("dry_run"):
            vault = Path("/tmp/cortex-no-vault")
        elif args.get("target"):
            vault = Path(args["target"])  # synthetic; route_target unused below
        else:
            raise
    target = (
        Path(args["target"])
        if args.get("target")
        else route_target(source_type, url, vault)
    )
    depth = int(args.get("depth") or DEFAULT_DEPTH)
    dry_run = bool(args.get("dry_run"))

    if source_type in ("github", "gitlab"):
        return ingest_git(url, target, dry_run)
    return ingest_website(url, target, depth, dry_run)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="cortex ingest_remote — github/gitlab clone + website crawl 远程入口"
    )
    parser.add_argument("url", help="github/gitlab repo URL 或 website URL")
    parser.add_argument(
        "--target", help="显式 vault 落档路径覆盖 (默认按 host 自动路由)"
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=DEFAULT_DEPTH,
        help="website crawl 深度 (default 3)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="仅识别 + 输出预期路径, 不写盘"
    )
    parser.add_argument(
        "--json", action="store_true", default=True, help="输出 JSON (default on)"
    )
    ns = parser.parse_args()
    try:
        result = cli_ingest_remote(
            {
                "url": ns.url,
                "target": ns.target,
                "depth": ns.depth,
                "dry_run": ns.dry_run,
            }
        )
    except (ValueError, RuntimeError) as exc:
        result = {"ok": False, "error": str(exc)}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
