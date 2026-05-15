"""cortex refresh_projects CLI — 批量扫 知识库/项目/, 增量更新 git/website (PR2).

仅增量 (no full-mode flag):
  - git repo: shallow clone tmp → `git rev-parse HEAD` 对比 frontmatter
    `last_commit_sha` → 一致跳过 / 不一致 diff 仅 ingest 变动文件
  - website: 重 crawl sitemap → 每页 SHA256 对比 `content_hash`
    → 一致跳过 / 不一致重写

复用 `lib/remote.py` helpers (parse_git_url / route_target /
ingest_git / ingest_website / crawl_sitemap)。本 CLI 仅做扫 + dispatch。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.remote import (  # noqa: E402
    GIT_TIMEOUT,
    discover_urls,
    dump_fm,
    fetch_bytes,
    load_filter_module,
    run_git,
    slugify,
    utc_now,
)
from lib.vault_path import resolve_vault  # noqa: E402

PROJECTS_REL = ("知识库", "项目")

__all__ = [
    "PROJECTS_REL",
    "scan_projects",
    "refresh_git_project",
    "refresh_website_project",
    "revalue_maturity",
    "main",
]


def revalue_maturity(
    old_maturity: str,
    hash_change_count: int,
    days_since_last_change: int,
) -> str:
    """内容 hash 变 → maturity 重评 (D5 锁定: 不动 score/confidence/source_credibility).

    Rules (顺序敏感):
      - hash_change_count >= 2 且 days < 30 → "draft" (频繁变动)
      - hash_change_count == 1 且 old == "stable" → "review" (从 stable 回退)
      - hash_change_count == 0 且 days >= 180 → "deprecated" (极久不变候选)
      - hash_change_count == 0 且 days >= 90 → "stable" (长期不变)
      - 其他 → 保持 old_maturity
    """
    if hash_change_count >= 2 and days_since_last_change < 30:
        return "draft"
    if hash_change_count == 1 and old_maturity == "stable":
        return "review"
    if hash_change_count == 0 and days_since_last_change >= 180:
        return "deprecated"
    if hash_change_count == 0 and days_since_last_change >= 90:
        return "stable"
    return old_maturity


def _days_since(iso_str: str | None) -> int:
    """parse ISO 8601 UTC, 返回距今天数. 解析失败 / 空值返 0."""
    if not iso_str or not isinstance(iso_str, str):
        return 0
    try:
        s = iso_str.rstrip("Z")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        return max(0, delta.days)
    except (ValueError, TypeError):
        return 0


def _patch_index_maturity(
    index_md: Path,
    new_maturity: str,
) -> None:
    """Rewrite `_index.md` frontmatter with new maturity + bumped last_ingested_at.

    Uses the same minimal line-based fm parser used elsewhere in this module:
    preserves unrelated keys verbatim, updates/adds maturity + last_ingested_at.
    """
    try:
        text = index_md.read_text(encoding="utf-8")
    except OSError:
        return
    m = _FM_RE.match(text)
    if not m:
        return
    fm_block = m.group(1)
    body = text[m.end():]
    lines = fm_block.splitlines()
    have_mat = False
    have_last = False
    new_iso = utc_now()
    out: list[str] = []
    for line in lines:
        if ":" not in line:
            out.append(line)
            continue
        key = line.split(":", 1)[0].strip()
        if key == "maturity":
            out.append(f"maturity: {new_maturity}")
            have_mat = True
        elif key == "last_ingested_at":
            out.append(f"last_ingested_at: {new_iso}")
            have_last = True
        else:
            out.append(line)
    if not have_mat:
        out.append(f"maturity: {new_maturity}")
    if not have_last:
        out.append(f"last_ingested_at: {new_iso}")
    new_text = "---\n" + "\n".join(out) + "\n---\n" + body
    try:
        index_md.write_text(new_text, encoding="utf-8")
    except OSError:
        pass


_FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)


def _parse_fm(text: str) -> dict:
    """Minimal frontmatter parser — strict ``key: value`` per line, no nesting."""
    m = _FM_RE.match(text)
    if not m:
        return {}
    out: dict = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        out[k.strip()] = v.strip()
    return out


def _read_fm_from_file(p: Path) -> dict:
    try:
        return _parse_fm(p.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return {}


def _read_index_meta(repo_dir: Path) -> dict | None:
    """读 `<repo_dir>/_index.md` frontmatter; 不存在则扫子目录任一 .md 取 source_url。"""
    idx = repo_dir / "_index.md"
    if idx.is_file():
        fm = _read_fm_from_file(idx)
        if fm.get("source_url"):
            return fm
    # Fallback: 任一 .md 文件
    for md in repo_dir.rglob("*.md"):
        fm = _read_fm_from_file(md)
        if fm.get("source_url"):
            return fm
    return None


def _scope_match(parts: tuple[str, str, str], scope: str | None) -> bool:
    if not scope:
        return True
    want = scope.strip("/").split("/")
    return tuple(parts[: len(want)]) == tuple(want)


def scan_projects(
    vault: Path, scope: str | None = None
) -> tuple[list[dict], list[str]]:
    """扫 vault/知识库/项目/<host>/<org>/<repo>/, 返 (projects, warnings)。"""
    root = vault.joinpath(*PROJECTS_REL)
    projects: list[dict] = []
    warnings: list[str] = []
    if not root.is_dir():
        return projects, warnings
    for host_dir in sorted(root.iterdir()):
        if not host_dir.is_dir():
            continue
        for org_dir in sorted(host_dir.iterdir()):
            if not org_dir.is_dir():
                continue
            for repo_dir in sorted(org_dir.iterdir()):
                if not repo_dir.is_dir():
                    continue
                parts = (host_dir.name, org_dir.name, repo_dir.name)
                if not _scope_match(parts, scope):
                    continue
                fm = _read_index_meta(repo_dir)
                rel_path = "/".join(("知识库", "项目", *parts))
                if not fm or not fm.get("source_url"):
                    warnings.append(f"{rel_path}: no source_url in _index.md")
                    continue
                projects.append(
                    {
                        "path": rel_path,
                        "abs_path": str(repo_dir),
                        "host": host_dir.name,
                        "org": org_dir.name,
                        "repo": repo_dir.name,
                        "source_url": fm.get("source_url", ""),
                        "source_type": fm.get("source_type", "website"),
                        "last_commit_sha": fm.get("last_commit_sha"),
                        "content_hash": fm.get("content_hash"),
                        "last_ingested_at": fm.get("last_ingested_at"),
                    }
                )
    return projects, warnings


def _write_index(repo_dir: Path, fm: dict, body: str) -> None:
    idx = repo_dir / "_index.md"
    idx.write_text(dump_fm(fm, body), encoding="utf-8")


def refresh_git_project(project: dict, vault: Path, dry_run: bool) -> dict:
    """git project 增量更新 — shallow clone, diff sha, 仅 ingest 变动文件。"""
    url = project["source_url"]
    repo_dir = Path(project["abs_path"])
    old_sha = project.get("last_commit_sha") or ""

    if dry_run:
        return {
            "status": "dry_run",
            "source_type": project["source_type"],
            "old_sha": old_sha,
        }

    tmpdir = Path(tempfile.mkdtemp(prefix="cortex-refresh-"))
    try:
        proc = run_git(["clone", "--depth=50", url, str(tmpdir)], timeout=GIT_TIMEOUT)
        if proc.returncode != 0:
            return {
                "status": "error",
                "errors": [f"git clone failed: {proc.stderr.strip()[:200]}"],
            }
        sha_proc = run_git(["rev-parse", "HEAD"], cwd=tmpdir)
        new_sha = sha_proc.stdout.strip() if sha_proc.returncode == 0 else ""
        if not new_sha:
            return {"status": "error", "errors": ["cannot resolve HEAD sha"]}
        if new_sha == old_sha:
            return {
                "status": "skip",
                "reason": "no_change",
                "files_changed": 0,
                "last_commit_sha": new_sha,
            }

        changed: list[str] = []
        if old_sha:
            diff_proc = run_git(["diff", "--name-only", old_sha, new_sha], cwd=tmpdir)
            if diff_proc.returncode == 0:
                changed = [
                    line.strip()
                    for line in diff_proc.stdout.splitlines()
                    if line.strip()
                ]
        # No old_sha = 视为首次, 全量计为变动 (但本 CLI 不重做全 ingest, 只 mark)。

        errors: list[str] = []
        ingested_n = 0
        for rel in changed:
            src = tmpdir / rel
            if not src.is_file():
                # 删除的文件 — 略过 (保守, 不删 vault)
                continue
            dest = repo_dir / "源" / (rel + ".md")
            try:
                content = src.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                errors.append(f"{rel}: {exc}")
                continue
            fm = {
                "source_url": url,
                "source_type": project["source_type"],
                "source_path": rel,
                "last_commit_sha": new_sha,
                "last_ingested_at": utc_now(),
            }
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(
                dump_fm(fm, f"# {rel}\n\n```\n{content}\n```\n"),
                encoding="utf-8",
            )
            ingested_n += 1

        # 更新 _index.md sha + maturity 重评 (D5: hash 变 → maturity 重评)
        repo_dir.mkdir(parents=True, exist_ok=True)
        old_idx_fm = _read_fm_from_file(repo_dir / "_index.md")
        old_maturity = old_idx_fm.get("maturity", "draft") or "draft"
        days = _days_since(old_idx_fm.get("last_ingested_at"))
        new_maturity = revalue_maturity(old_maturity, ingested_n, days)
        idx_fm = {
            "source_url": url,
            "source_type": project["source_type"],
            "last_commit_sha": new_sha,
            "last_ingested_at": utc_now(),
            "maturity": new_maturity,
        }
        _write_index(
            repo_dir,
            idx_fm,
            f"# {project['org']}/{project['repo']}\n\n"
            f"Refreshed at `{utc_now()}` (sha=`{new_sha[:8]}`).\n",
        )
        result: dict = {
            "status": "updated",
            "files_changed": ingested_n,
            "last_commit_sha": new_sha,
            "errors": errors,
        }
        if new_maturity != old_maturity:
            result["maturity_changed"] = {"old": old_maturity, "new": new_maturity}
        return result
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "errors": [f"git clone timeout after {GIT_TIMEOUT}s"],
        }
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def refresh_website_project(project: dict, vault: Path, dry_run: bool) -> dict:
    """website project 增量更新 — sitemap re-crawl, 每页 SHA256 对比。"""
    base_url = project["source_url"]
    repo_dir = Path(project["abs_path"])

    if dry_run:
        return {"status": "dry_run", "source_type": "website"}

    url_security = load_filter_module("url_security.py", "cortex_url_security")
    safe, reason = url_security.is_safe(base_url)
    if not safe:
        return {"status": "error", "errors": [f"url_security rejected: {reason}"]}

    html_sanitize = load_filter_module("html_sanitize.py", "cortex_html_sanitize")
    masking = load_filter_module("masking.py", "cortex_masking")

    try:
        urls = discover_urls(base_url, depth=2, url_security=url_security)
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "errors": [f"crawl error: {exc}"]}
    if not urls:
        urls = [base_url]

    # 读已存页 hash map: slug → hash
    existing: dict[str, dict] = {}
    for md in repo_dir.glob("*.md"):
        if md.name == "_index.md":
            continue
        fm = _read_fm_from_file(md)
        src = fm.get("source_url")
        if src:
            existing[src] = {"path": md, "hash": fm.get("content_hash")}

    changed = 0
    new = 0
    errors: list[str] = []
    seen_urls: set[str] = set()
    for page_url in urls:
        seen_urls.add(page_url)
        try:
            raw, ct = fetch_bytes(page_url)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{page_url}: fetch error: {exc}")
            continue
        if "html" not in (ct or "").lower():
            continue
        body_text = raw.decode("utf-8", errors="replace")
        sanitized = html_sanitize.sanitize(body_text)
        masked, _hits = masking.mask(sanitized)
        new_hash = hashlib.sha256(masked.encode("utf-8")).hexdigest()
        prior = existing.get(page_url)
        if prior and prior["hash"] == new_hash:
            continue
        page_slug = slugify(urllib.parse.urlparse(page_url).path or "/")
        dest = repo_dir / f"{page_slug}.md"
        fm = {
            "source_url": page_url,
            "source_type": "website",
            "content_hash": new_hash,
            "last_ingested_at": utc_now(),
        }
        try:
            dest.write_text(dump_fm(fm, masked), encoding="utf-8")
        except OSError as exc:
            errors.append(f"{page_url}: write error: {exc}")
            continue
        if prior is None:
            new += 1
        else:
            changed += 1

    orphans = sorted(set(existing.keys()) - seen_urls)
    status = "updated" if (changed or new) else "skip"

    # D5: project-level maturity 重评 (基于本轮 hash 变化总数)
    hash_change_count = changed + new
    index_md = repo_dir / "_index.md"
    maturity_changed = None
    if index_md.is_file():
        old_idx_fm = _read_fm_from_file(index_md)
        old_maturity = old_idx_fm.get("maturity", "draft") or "draft"
        days = _days_since(old_idx_fm.get("last_ingested_at"))
        new_maturity = revalue_maturity(old_maturity, hash_change_count, days)
        if new_maturity != old_maturity:
            _patch_index_maturity(index_md, new_maturity)
            maturity_changed = {"old": old_maturity, "new": new_maturity}

    result: dict = {
        "status": status,
        "files_changed": changed,
        "files_new": new,
        "orphans": orphans,
        "errors": errors,
    }
    if maturity_changed is not None:
        result["maturity_changed"] = maturity_changed
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="cortex refresh_projects — 批量增量刷新 知识库/项目/"
    )
    parser.add_argument("--vault", help="vault 根路径 (默认 resolve_vault)")
    parser.add_argument(
        "--scope",
        help="限定 host / host/org / host/org/repo (默认全扫)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="仅扫不更新, 输出待变动列表"
    )
    parser.add_argument(
        "--json", action="store_true", default=True, help="输出 JSON (default on)"
    )
    ns = parser.parse_args()

    try:
        vault = Path(ns.vault) if ns.vault else resolve_vault()
    except RuntimeError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1

    projects, warnings = scan_projects(vault, ns.scope)
    results: list[dict] = []
    for p in projects:
        if p["source_type"] in ("github", "gitlab"):
            r = refresh_git_project(p, vault, ns.dry_run)
        else:
            r = refresh_website_project(p, vault, ns.dry_run)
        results.append({"project": p["path"], **r})

    summary = {
        "projects_scanned": len(projects),
        "projects_updated": sum(1 for r in results if r.get("status") == "updated"),
        "files_changed": sum(r.get("files_changed", 0) for r in results),
        "files_new": sum(r.get("files_new", 0) for r in results),
        "errors": sum(len(r.get("errors") or []) for r in results),
        "warnings": warnings,
        "results": results,
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
