#!/usr/bin/env python3
"""cortex-refactor evolution-apply — proposal 列举 + safety gate + 清理.

AI 主线流程 (SKILL.md 描述):
  1. list_proposals → pending proposal JSON
  2. AI 用 AskUserQuestion 逐条询问 (接受/拒绝/推迟)
  3. check_safety_gate → (ok, message/diff)
  4. AI 应用 unified diff (Edit / MCP)
  5. delete_proposal → 清 markdown

本 CLI 仅"列 + 验证 + 清", **不**自己 patch SKILL/AGENT.

Safety gates: target 白名单 + 黑名单 + git working tree clean + frontmatter 可解析.
属 python CLI 例外 (AGENT.md §协作约定 3): 走文件 IO.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

PROPOSALS_REL_DIR = "_assets/evolution-proposals"

WHITELIST_PREFIXES = (
    "plugins/tools/cortex/skills/",
    "plugins/tools/cortex/agents/",
    "skills/",
    "agents/",
)
WHITELIST_EXACT = ("plugins/tools/cortex/AGENT.md", "AGENT.md")
BLACKLIST_FRAGMENTS = (
    "/commands/", "/scripts/", "/_meta/", "/_templates/",
    "commands/", "scripts/", "_meta/", "_templates/",
)
PLUGIN_REL = "plugins/tools/cortex"


def _parse_frontmatter(text: str) -> dict | None:
    """Lightweight YAML frontmatter parser. 返 dict 或 None."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    fm: dict = {}
    cur: str | None = None
    for line in text[3:end].strip("\n").splitlines():
        if not line.strip():
            continue
        s = line.lstrip()
        if s.startswith("- ") and cur:
            if fm.get(cur) is None:
                fm[cur] = []
            if isinstance(fm[cur], list):
                fm[cur].append(s[2:].strip().strip("\"'"))
            continue
        if line.startswith(" ") and cur:
            continue
        if ":" in line:
            k, _, v = line.partition(":")
            k, v = k.strip(), v.strip()
            cur = k
            if not v:
                fm[k] = None
            elif v.startswith("[") and v.endswith("]"):
                fm[k] = [p.strip().strip("\"'") for p in v[1:-1].split(",") if p.strip()]
            else:
                fm[k] = v.strip("\"'")
    return fm


def _extract_diff_block(text: str) -> str | None:
    m = re.search(r"```diff\n(.*?)\n```", text, re.S)
    return m.group(1) if m else None


def _diff_summary(diff: str) -> str:
    for line in diff.splitlines():
        if line.startswith("@@"):
            return line.strip()[:80]
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            return f"+ {line[1:].strip()[:78]}"
    return "(no visible hunk)"


def list_proposals(vault: Path) -> list[dict]:
    """List pending proposals under <vault>/_assets/evolution-proposals/."""
    d = vault / PROPOSALS_REL_DIR
    if not d.is_dir():
        return []
    out: list[dict] = []
    for p in sorted(d.glob("*.md")):
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        fm = _parse_frontmatter(text) or {}
        diff = _extract_diff_block(text) or ""
        out.append({
            "path": str(p.relative_to(vault)),
            "abs_path": str(p),
            "pattern_id": fm.get("pattern_id", ""),
            "target_skill": fm.get("target_skill", ""),
            "confidence": fm.get("confidence", ""),
            "applications": fm.get("applications", ""),
            "category": fm.get("category", ""),
            "diff_summary": _diff_summary(diff) if diff else "(no diff block)",
        })
    return out


def _is_target_whitelisted(target: str) -> tuple[bool, str]:
    if not target:
        return False, "target_skill 字段为空"
    norm = target.lstrip("./")
    for frag in BLACKLIST_FRAGMENTS:
        if frag in norm:
            return False, f"target 命中黑名单 '{frag}': {target}"
    if norm in WHITELIST_EXACT:
        return True, "ok"
    for pref in WHITELIST_PREFIXES:
        if norm.startswith(pref):
            return True, "ok"
    return False, f"target 不在白名单 (SKILL/agents/AGENT.md/references): {target}"


def _git_repo_clean(repo_root: Path, sub_rel: str) -> tuple[bool, str]:
    """检查 sub_rel 下 git working tree 是否 clean. 非 repo → clean.
    env CORTEX_SKIP_GIT_GATE=1 跳过 (测试).
    """
    if os.environ.get("CORTEX_SKIP_GIT_GATE") == "1":
        return True, "ok (skip env)"
    if not (repo_root / ".git").exists():
        return True, "ok (not a git repo)"
    try:
        r = subprocess.run(
            ["git", "status", "--porcelain", "--", sub_rel],
            cwd=str(repo_root), capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"git status failed: {e}"
    if r.returncode != 0:
        return False, f"git status rc={r.returncode}: {r.stderr.strip()}"
    if r.stdout.strip():
        return False, (
            f"git working tree dirty under {sub_rel}, 请先 commit:\n"
            f"{r.stdout.strip()[:400]}"
        )
    return True, "ok"


def _resolve_repo_root() -> Path:
    env = os.environ.get("CORTEX_REPO_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / PLUGIN_REL).is_dir() and (parent / ".git").exists():
            return parent
    return here.parents[4] if len(here.parents) >= 5 else here.parent


def check_safety_gate(
    proposal_path: Path, repo_root: Path | None = None,
) -> tuple[bool, str, str]:
    """检查 proposal 可否应用.

    返回 (ok, message, diff):
      ok=True → message="ok", diff=unified diff
      ok=False → message=reason, diff=""
    """
    if not proposal_path.is_file():
        return False, f"proposal 文件不存在: {proposal_path}", ""
    try:
        text = proposal_path.read_text(encoding="utf-8")
    except OSError as e:
        return False, f"读 proposal 失败: {e}", ""
    fm = _parse_frontmatter(text)
    if fm is None:
        return False, "proposal yaml frontmatter 解析失败", ""
    target = str(fm.get("target_skill", ""))
    ok, reason = _is_target_whitelisted(target)
    if not ok:
        return False, reason, ""
    diff = _extract_diff_block(text)
    if not diff:
        return False, "proposal 缺 ```diff fenced block", ""
    if repo_root is None:
        repo_root = _resolve_repo_root()
    clean_ok, clean_msg = _git_repo_clean(repo_root, PLUGIN_REL)
    if not clean_ok:
        return False, clean_msg, ""
    return True, "ok", diff


def delete_proposal(proposal_path: Path) -> bool:
    """删 proposal. 不存在视作成功 (idempotent)."""
    if not proposal_path.exists():
        return True
    try:
        proposal_path.unlink()
        return True
    except OSError as e:
        print(f"warn: delete proposal failed: {e}", file=sys.stderr)
        return False


def _resolve_vault(arg_vault: str | None) -> Path:
    if arg_vault:
        return Path(os.path.expanduser(arg_vault)).resolve()
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks" / "_lib"))
        from cortex_config import load_config  # type: ignore
        v = load_config().get("vault")
        if v:
            return Path(os.path.expanduser(v)).resolve()
    except Exception:
        pass
    raise RuntimeError("vault 未指定且 ~/.cortex/config.json 无 vault 字段")


def _resolve_proposal_path(arg: str, vault: Path) -> Path:
    p = Path(os.path.expanduser(arg))
    return p.resolve() if p.is_absolute() else (vault / arg).resolve()


def _cmd_list(args: argparse.Namespace) -> int:
    try:
        vault = _resolve_vault(args.vault)
    except RuntimeError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 2
    items = list_proposals(vault)
    print(json.dumps(items, ensure_ascii=False, indent=2))
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    try:
        vault = _resolve_vault(args.vault)
    except RuntimeError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 2
    pp = _resolve_proposal_path(args.proposal, vault)
    ok, msg, diff = check_safety_gate(pp)
    out = {"ok": ok, "message": msg, "proposal": str(pp), "diff": diff if ok else ""}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def _cmd_delete(args: argparse.Namespace) -> int:
    try:
        vault = _resolve_vault(args.vault)
    except RuntimeError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 2
    pp = _resolve_proposal_path(args.proposal, vault)
    ok = delete_proposal(pp)
    print(json.dumps({"ok": ok, "proposal": str(pp)}, ensure_ascii=False))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="evolution_apply",
        description="cortex-refactor evolution-apply — list / check / delete proposals",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="列 _assets/evolution-proposals/*.md")
    p_list.add_argument("--vault", default=None)
    p_list.add_argument("--json", action="store_true", default=True)
    p_list.set_defaults(func=_cmd_list)

    p_check = sub.add_parser("check", help="safety gate, 通过返 unified diff")
    p_check.add_argument("proposal")
    p_check.add_argument("--vault", default=None)
    p_check.add_argument("--json", action="store_true", default=True)
    p_check.set_defaults(func=_cmd_check)

    p_del = sub.add_parser("delete", help="删 proposal (接受/拒绝后清理)")
    p_del.add_argument("proposal")
    p_del.add_argument("--vault", default=None)
    p_del.add_argument("--json", action="store_true", default=True)
    p_del.set_defaults(func=_cmd_delete)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
