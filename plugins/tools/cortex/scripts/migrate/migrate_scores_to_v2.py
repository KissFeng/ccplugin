#!/usr/bin/env python3
"""cortex score v2 一次性迁移 (PR6).

迁移内容:
1. 知识库 .md (`知识库/**`, 排除 `知识库/收件箱/`):
   - 旧 `score: 1-5 整数` → `score: <old> * 2.0` (0-10 浮点)
   - 缺 confidence / source_credibility → 加 stub 0.0
   - 缺 maturity → 加 stub "draft"
2. 记忆 .md (`记忆/L0-`, L1-, L2-, L3-):
   - 缺 importance / confidence → 加 stub 0.0
3. patterns.md (`记忆/L0-核心/patterns.md`):
   - 旧 confidence (0.0-1.0) → × 10 (0.85 → 8.5)
4. 跳过 `.obsidian/` / `归档/` / `.trash/` / `_meta/` / `_templates/` / `_assets/`

CLI:
    migrate_scores_to_v2.py --vault PATH [--dry-run] [--no-backup] [--json]

stdlib + 项目内 frontmatter helper (不依赖 PyYAML)。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any

# 让 `python3 migrate_scores_to_v2.py` 直跑也能 import lib.frontmatter
_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent.parent / "cli"))

from lib.frontmatter import dump as _fm_dump  # noqa: E402
from lib.frontmatter import parse as _fm_parse  # noqa: E402

_SKIP_TOPS = (".obsidian/", "归档/", ".trash/", "_meta/", "_templates/", "_assets/")
_KB_PREFIX = "知识库/"
_KB_INBOX_PREFIX = "知识库/收件箱/"
_MEM_PREFIXES = ("记忆/L0-", "记忆/L1-", "记忆/L2-", "记忆/L3-")
_PATTERNS_REL = "记忆/L0-核心/patterns.md"
_MATURITY_ENUM = {"draft", "review", "stable", "deprecated"}

_KB_REQUIRED = ("score", "confidence", "source_credibility", "maturity")
_MEM_REQUIRED = ("importance", "confidence")


def _classify(rel: str) -> str:
    """Return one of: 'kb', 'mem', 'patterns', 'skip'."""
    p = rel.replace("\\", "/")
    if any(p.startswith(t) for t in _SKIP_TOPS):
        return "skip"
    if p == _PATTERNS_REL:
        return "patterns"
    if p.startswith(_KB_PREFIX) and not p.startswith(_KB_INBOX_PREFIX):
        return "kb"
    if any(p.startswith(t) for t in _MEM_PREFIXES):
        return "mem"
    return "skip"


def _coerce_score_value(val: Any) -> tuple[Any, bool, bool]:
    """Return (new_val, was_score_migrated, type_ok).

    - 整数 1-5 → × 2.0 (was_score_migrated=True)
    - 已 float / 字符串数 0-10 → 转 float (type_ok=True)
    - 越界 → clamp
    - bool / 非数 → 0.0 (type_ok=False)
    """
    if isinstance(val, bool):
        return 0.0, False, False
    if isinstance(val, int):
        if 1 <= val <= 5:
            return float(val) * 2.0, True, True
        v = float(val)
        if v < 0:
            return 0.0, False, True
        if v > 10:
            return 10.0, False, True
        return v, False, True
    if isinstance(val, float):
        if val < 0:
            return 0.0, False, True
        if val > 10:
            return 10.0, False, True
        return val, False, True
    if isinstance(val, str):
        try:
            v = float(val.strip())
        except (ValueError, AttributeError):
            return 0.0, False, False
        if 1 <= v <= 5 and v == int(v):
            return v * 2.0, True, True
        if v < 0:
            return 0.0, False, True
        if v > 10:
            return 10.0, False, True
        return v, False, True
    return 0.0, False, False


def _migrate_kb(
    fm: dict[str, Any], stats: dict[str, int]
) -> tuple[dict[str, Any], bool]:
    changed = False
    # score 迁移 / 校正
    if "score" in fm:
        new_val, migrated, ok = _coerce_score_value(fm["score"])
        if migrated:
            fm["score"] = new_val
            stats["score_migrated"] += 1
            changed = True
        elif not ok or not isinstance(fm["score"], float):
            if fm["score"] != new_val:
                fm["score"] = new_val
                changed = True
    else:
        fm["score"] = 0.0
        stats["fields_added"] += 1
        changed = True
    # 其他 3 字段缺 → stub
    for f in ("confidence", "source_credibility"):
        if f not in fm:
            fm[f] = 0.0
            stats["fields_added"] += 1
            changed = True
        else:
            new_val, _mig, ok = _coerce_score_value(fm[f])
            if not ok or not isinstance(fm[f], float) or fm[f] != new_val:
                fm[f] = new_val
                changed = True
    if "maturity" not in fm:
        fm["maturity"] = "draft"
        stats["fields_added"] += 1
        changed = True
    elif not isinstance(fm["maturity"], str) or fm["maturity"] not in _MATURITY_ENUM:
        fm["maturity"] = "draft"
        changed = True
    return fm, changed


def _migrate_mem(
    fm: dict[str, Any], stats: dict[str, int]
) -> tuple[dict[str, Any], bool]:
    changed = False
    for f in _MEM_REQUIRED:
        if f not in fm:
            fm[f] = 0.0
            stats["fields_added"] += 1
            changed = True
        else:
            new_val, _mig, ok = _coerce_score_value(fm[f])
            if not ok or not isinstance(fm[f], float) or fm[f] != new_val:
                fm[f] = new_val
                changed = True
    return fm, changed


_PATTERNS_CONF_RE = re.compile(r"^(\s*confidence:\s*)([0-9]*\.?[0-9]+)\s*$", re.M)


def _migrate_patterns_text(text: str, stats: dict[str, int]) -> tuple[str, bool]:
    """patterns.md 内 yaml fence block 内 `confidence: 0.85` → 8.5.

    仅当原值 ≤ 1.0 视为旧 schema; > 1.0 视为已新 schema 跳过。
    """
    changed = False

    def _repl(m: re.Match[str]) -> str:
        nonlocal changed
        prefix, val = m.group(1), m.group(2)
        try:
            v = float(val)
        except ValueError:
            return m.group(0)
        if 0.0 <= v <= 1.0:
            new_v = round(v * 10, 2)
            stats["patterns_migrated"] += 1
            changed = True
            return f"{prefix}{new_v}"
        return m.group(0)

    new_text = _PATTERNS_CONF_RE.sub(_repl, text)
    return new_text, changed


def _backup_vault(vault: Path) -> Path:
    ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path("/tmp") / f"cortex-migration-backup-{ts}.tar.gz"
    try:
        with tarfile.open(out, "w:gz") as tar:
            tar.add(str(vault), arcname=vault.name)
    except (OSError, tarfile.TarError) as e:
        # fallback: 调系统 tar (大 vault 走二进制更省内存)
        try:
            subprocess.run(
                [
                    "tar",
                    "czf",
                    str(out),
                    "-C",
                    str(vault.parent),
                    vault.name,
                ],
                check=True,
                capture_output=True,
            )
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"backup failed: {e}; tar fallback: {exc}") from exc
    return out


def migrate(
    vault: Path,
    *,
    dry_run: bool = False,
    backup: bool = True,
) -> dict[str, Any]:
    """主入口。返回 JSON-ready dict。"""
    result: dict[str, Any] = {
        "vault": str(vault),
        "dry_run": dry_run,
        "backup_path": None,
        "files_scanned": 0,
        "files_changed": 0,
        "fields_added": 0,
        "score_migrated": 0,
        "patterns_migrated": 0,
        "errors": [],
    }
    if not vault.is_dir():
        result["errors"].append(f"vault not found: {vault}")
        return result

    stats = {
        "fields_added": 0,
        "score_migrated": 0,
        "patterns_migrated": 0,
    }

    # backup
    if backup and not dry_run:
        try:
            bpath = _backup_vault(vault)
            result["backup_path"] = str(bpath)
        except RuntimeError as e:
            result["errors"].append(str(e))
            return result

    for md in vault.rglob("*.md"):
        try:
            rel = md.relative_to(vault).as_posix()
        except ValueError:
            continue
        kind = _classify(rel)
        if kind == "skip":
            continue
        result["files_scanned"] += 1
        try:
            text = md.read_text(encoding="utf-8")
        except OSError as e:
            result["errors"].append(f"{rel}: read error: {e}")
            continue

        if kind == "patterns":
            new_text, changed = _migrate_patterns_text(text, stats)
            if changed:
                result["files_changed"] += 1
                if not dry_run:
                    try:
                        md.write_text(new_text, encoding="utf-8")
                    except OSError as e:
                        result["errors"].append(f"{rel}: write error: {e}")
            continue

        fm, body = _fm_parse(text)
        if not fm:
            # 无 frontmatter — 不动 (其他 lint rule 已覆盖)
            continue
        if kind == "kb":
            new_fm, changed = _migrate_kb(fm, stats)
        else:
            new_fm, changed = _migrate_mem(fm, stats)
        if not changed:
            continue
        result["files_changed"] += 1
        if dry_run:
            continue
        try:
            md.write_text(_fm_dump(new_fm, body), encoding="utf-8")
        except OSError as e:
            result["errors"].append(f"{rel}: write error: {e}")

    result["fields_added"] = stats["fields_added"]
    result["score_migrated"] = stats["score_migrated"]
    result["patterns_migrated"] = stats["patterns_migrated"]
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    ap.add_argument("--vault", required=True, help="vault root path")
    ap.add_argument(
        "--to",
        default="v2",
        help="target schema version (only 'v2' supported)",
    )
    ap.add_argument("--dry-run", action="store_true", help="scan only, no writes")
    ap.add_argument(
        "--no-backup",
        action="store_true",
        help="skip tar.gz backup (默认开)",
    )
    ap.add_argument("--json", action="store_true", default=True, help="JSON output")
    ns = ap.parse_args()
    if ns.to != "v2":
        print(
            json.dumps({"error": f"unsupported --to={ns.to}; only 'v2' is supported"}),
            file=sys.stderr,
        )
        return 2
    vault = Path(ns.vault).expanduser().resolve()
    result = migrate(
        vault,
        dry_run=ns.dry_run,
        backup=not ns.no_backup,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not result.get("errors") else 1


if __name__ == "__main__":
    sys.exit(main())
