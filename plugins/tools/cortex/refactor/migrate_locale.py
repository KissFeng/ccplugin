#!/usr/bin/env python3
"""cortex refactor: migrate-locale — rename business dirs from one lang's dirs map to another.

Usage:
    migrate_locale.py --vault PATH --from LANG --to LANG [--apply]

- Default: dry-run (prints plan as JSON).
- --apply: rename dirs (git mv if vault is a git worktree, else os.rename),
  rewrite all wikilinks via _common.rewrite_wikilinks,
  update _meta/version.json:.lang,
  log to _meta/migrations/<ts>.json.

stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks" / "_lib"))

from _common import iter_md_files, make_backup_ts  # noqa: E402
from cortex_locale import load_locale  # noqa: E402

PLUGIN_ROOT = Path(__file__).resolve().parent.parent


def _is_git_repo(vault: Path) -> bool:
    return (vault / ".git").exists()


def _git_mv(vault: Path, src: Path, dst: Path) -> bool:
    try:
        subprocess.run(
            ["git", "-C", str(vault), "mv", str(src.relative_to(vault)), str(dst.relative_to(vault))],
            check=True, capture_output=True,
        )
        return True
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", required=True)
    ap.add_argument("--from", dest="src_lang", required=True)
    ap.add_argument("--to", dest="dst_lang", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    vault = Path(args.vault).expanduser().resolve()
    if not vault.is_dir():
        print(json.dumps({"error": f"vault not found: {vault}"}), file=sys.stderr)
        return 2

    src_loc = load_locale(PLUGIN_ROOT, vault, args.src_lang)
    dst_loc = load_locale(PLUGIN_ROOT, vault, args.dst_lang)
    src_dirs = src_loc.get_dirs()
    dst_dirs = dst_loc.get_dirs()
    if not src_dirs or not dst_dirs:
        print(json.dumps({"error": "missing locale dirs map"}), file=sys.stderr)
        return 2

    # Plan: for each key, if src_name != dst_name and src_name dir exists -> rename
    plan: list[dict] = []
    for key, src_name in src_dirs.items():
        dst_name = dst_dirs.get(key)
        if not dst_name or dst_name == src_name:
            continue
        src_dir = vault / src_name
        dst_dir = vault / dst_name
        if not src_dir.is_dir():
            continue
        if dst_dir.exists():
            plan.append({"key": key, "from": src_name, "to": dst_name, "skip": "target exists"})
            continue
        plan.append({"key": key, "from": src_name, "to": dst_name})

    actionable = [p for p in plan if "skip" not in p]

    if not args.apply:
        print(json.dumps({"dry_run": True, "plan": plan, "vault_lang_after": args.dst_lang}, ensure_ascii=False, indent=2))
        return 0

    # apply
    ts = make_backup_ts()
    git = _is_git_repo(vault)
    rename_map: dict[str, str] = {}  # for wikilink rewrite (basename keys)

    for item in actionable:
        src_dir = vault / item["from"]
        dst_dir = vault / item["to"]
        ok = False
        if git:
            ok = _git_mv(vault, src_dir, dst_dir)
        if not ok:
            try:
                os.rename(src_dir, dst_dir)
                ok = True
            except Exception as e:
                item["error"] = str(e)
                continue
        item["ok"] = True
        rename_map[item["from"]] = item["to"]

    # rewrite wikilinks across vault
    rewrites = 0
    if rename_map:
        # build basename-level mapping for any md inside renamed dirs
        # also rewrite path-prefixed wikilinks
        for md in iter_md_files(vault):
            try:
                text = md.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            new_text = text
            for src_name, dst_name in rename_map.items():
                # path-prefixed wikilink replace (rare): [[src_name/foo]] -> [[dst_name/foo]]
                new_text = new_text.replace(f"[[{src_name}/", f"[[{dst_name}/")
                new_text = new_text.replace(f"![[{src_name}/", f"![[{dst_name}/")
            if new_text != text:
                md.write_text(new_text, encoding="utf-8")
                rewrites += 1

    # update _meta/version.json:.lang
    vfile = vault / "_meta" / "version.json"
    if vfile.is_file():
        try:
            data = json.loads(vfile.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        data["lang"] = args.dst_lang
        vfile.parent.mkdir(parents=True, exist_ok=True)
        vfile.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # log migration
    mig_dir = vault / "_meta" / "migrations"
    mig_dir.mkdir(parents=True, exist_ok=True)
    log = {
        "op": "migrate-locale",
        "ts": ts,
        "from": args.src_lang,
        "to": args.dst_lang,
        "plan": plan,
        "wikilink_rewrites": rewrites,
    }
    (mig_dir / f"{ts}-migrate-locale.json").write_text(
        json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )

    print(json.dumps({"applied": True, "renamed": len(rename_map), "rewrites": rewrites,
                      "plan": plan, "log": str((mig_dir / f"{ts}-migrate-locale.json").relative_to(vault))},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
