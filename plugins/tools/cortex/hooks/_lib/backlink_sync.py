#!/usr/bin/env python3
"""backlink_sync.py — cortex 反向 wikilink 回填工具。

由 cortex-save / cortex-ingest skill / save_session.py 复用。

输入:
  --vault PATH       Obsidian vault 绝对路径 (必需)
  --source REL       源页 vault 相对路径 (必需), 例如 "log/2026-05/10-1430-foo.md"
  --dry-run          不写盘, 只打印计划
  --quiet            不打印 JSON, 仅退出码

行为:
  1. 解析 <source> 中所有 [[X]] / [[X|Y]] / [[X#h]] / [[X^b]] 链接
     (忽略 transclusion ![[X]] 与代码块内的 wikilink)
  2. 对每个目标 X (规范化, 去 anchor):
       - 找 <vault>/**/<X>.md  (大小写不敏感, basename 优先)
       - 否则扫所有 .md 的 frontmatter aliases 命中
  3. 命中目标页 → 在末尾 `## Backlinks` 段追加 `- [[<source>]]`
       - 段不存在则建
       - 已存在同 source 行则跳过
  4. 输出 JSON: {"updated":[...], "skipped":[...], "missing":[...]}
  5. 退出 0 (失败仅日志, 不阻断调用方)

仅依赖 python stdlib。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BACKLINKS_HEADER = "## Backlinks"
AUTO_TAG = "(cortex-auto)"

# [[X]] [[X|Y]] [[X#h]] [[X^b]] — 不含 ! 前缀 (transclusion)
WIKILINK_RE = re.compile(r"(?<!\!)\[\[([^\[\]\n|#^]+)(?:[#^][^\[\]\n|]*)?(?:\|[^\[\]\n]*)?\]\]")

# 简易代码块剥离 (fenced ``` and ~~~)
FENCE_RE = re.compile(r"^(```|~~~)", re.MULTILINE)


def strip_code_blocks(text: str) -> str:
    """剥离 fenced code block 内容, 防止误识别 wikilink。"""
    out: list[str] = []
    in_fence = False
    fence_marker = ""
    for line in text.splitlines():
        stripped = line.lstrip()
        if not in_fence and (stripped.startswith("```") or stripped.startswith("~~~")):
            in_fence = True
            fence_marker = stripped[:3]
            continue
        if in_fence and stripped.startswith(fence_marker):
            in_fence = False
            continue
        if not in_fence:
            out.append(line)
    return "\n".join(out)


def extract_wikilinks(text: str) -> list[str]:
    """提取所有 [[X]] 目标名 (规范化, 去 anchor)。"""
    cleaned = strip_code_blocks(text)
    seen: dict[str, None] = {}
    for m in WIKILINK_RE.finditer(cleaned):
        target = m.group(1).strip()
        if not target:
            continue
        # normalize: 去掉 .md / 末尾 /
        if target.lower().endswith(".md"):
            target = target[:-3]
        target = target.strip()
        if target and target not in seen:
            seen[target] = None
    return list(seen.keys())


def parse_frontmatter_titles(md_text: str) -> tuple[str | None, list[str]]:
    """从 frontmatter 抽 title 与 aliases (容错, 支持单行 list)。"""
    if not md_text.startswith("---"):
        return None, []
    end = md_text.find("\n---", 3)
    if end < 0:
        return None, []
    fm = md_text[3:end]
    title: str | None = None
    aliases: list[str] = []
    for line in fm.splitlines():
        s = line.strip()
        if s.startswith("title:"):
            t = s[len("title:"):].strip().strip("\"'")
            if t:
                title = t
        elif s.startswith("aliases:"):
            rest = s[len("aliases:"):].strip()
            if rest.startswith("[") and rest.endswith("]"):
                inner = rest[1:-1]
                for part in inner.split(","):
                    a = part.strip().strip("\"'")
                    if a:
                        aliases.append(a)
            # else: yaml 多行 list, 简化不处理
    return title, aliases


def parse_aliases(md_text: str) -> list[str]:
    """向后兼容: 仅返 aliases。"""
    return parse_frontmatter_titles(md_text)[1]


def index_vault(vault: Path) -> tuple[dict[str, Path], dict[str, Path]]:
    """扫 vault, 建 basename → path 与 alias → path 索引。

    basename 索引 key 用 lower-case stem。
    alias 索引 key 用 lower-case alias。
    """
    by_name: dict[str, Path] = {}
    by_alias: dict[str, Path] = {}
    for md in vault.rglob("*.md"):
        # 排除 _meta/ .obsidian/ _templates/
        rel = md.relative_to(vault)
        parts = rel.parts
        if parts and parts[0] in ("_meta", ".obsidian", "_templates"):
            continue
        stem = md.stem.lower()
        # 第一次命中优先 (浅路径自然先到? rglob 不保证顺序, 这里就近用)
        by_name.setdefault(stem, md)
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        title, aliases = parse_frontmatter_titles(text)
        if title:
            by_alias.setdefault(title.lower(), md)
        for alias in aliases:
            by_alias.setdefault(alias.lower(), md)
    return by_name, by_alias


def resolve_target(
    target: str, by_name: dict[str, Path], by_alias: dict[str, Path]
) -> Path | None:
    key = target.lower()
    # 支持 [[folder/page]] — 取 basename
    if "/" in key:
        key_base = key.rsplit("/", 1)[1]
    else:
        key_base = key
    p = by_name.get(key_base)
    if p:
        return p
    return by_alias.get(key)


def append_backlink(target_path: Path, source_rel: str, dry_run: bool) -> str:
    """在 target_path 末尾 `## Backlinks` 段追加 `- [[source_rel]]`。

    返回 "added" / "skipped" / "error"。
    """
    bullet = f"- [[{source_rel}]] {AUTO_TAG}"
    bullet_no_tag = f"- [[{source_rel}]]"
    try:
        text = target_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return "error"

    if BACKLINKS_HEADER in text:
        head, _, tail = text.partition(BACKLINKS_HEADER)
        # 检查是否已有该 source
        for line in tail.splitlines():
            if line.strip() == bullet.strip() or line.strip() == bullet_no_tag.strip():
                return "skipped"
            # 也匹配带不同尾部空格的同源
            if line.strip().startswith(bullet_no_tag):
                return "skipped"
        new_tail = tail.rstrip() + f"\n{bullet}\n"
        new_text = head + BACKLINKS_HEADER + new_tail
    else:
        sep = "" if text.endswith("\n") else "\n"
        new_text = f"{text}{sep}\n{BACKLINKS_HEADER}\n\n{bullet}\n"

    if dry_run:
        return "added"
    try:
        target_path.write_text(new_text, encoding="utf-8")
    except Exception:
        return "error"
    return "added"


def main() -> int:
    ap = argparse.ArgumentParser(description="cortex backlink sync")
    ap.add_argument("--vault", required=True)
    ap.add_argument("--source", required=True, help="vault 相对路径")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    vault = Path(args.vault).expanduser().resolve()
    if not vault.is_dir():
        print(f"vault not found: {vault}", file=sys.stderr)
        return 0

    source_rel = args.source.lstrip("./")
    source_abs = vault / source_rel
    if not source_abs.is_file():
        print(f"source not found: {source_abs}", file=sys.stderr)
        return 0

    try:
        source_text = source_abs.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"read source failed: {e}", file=sys.stderr)
        return 0

    targets = extract_wikilinks(source_text)
    if not targets:
        if not args.quiet:
            print(json.dumps({"updated": [], "skipped": [], "missing": []}))
        return 0

    by_name, by_alias = index_vault(vault)

    # 把源页本身从候选剔除 (自引用)
    self_stem = source_abs.stem.lower()

    updated_set: set[str] = set()
    skipped_set: set[str] = set()
    missing: list[str] = []

    for tgt in targets:
        tgt_key = tgt.lower()
        tgt_base = tgt_key.rsplit("/", 1)[-1]
        if tgt_base == self_stem:
            continue
        path = resolve_target(tgt, by_name, by_alias)
        if path is None:
            missing.append(tgt)
            continue
        # 不要回填到自身
        if path.resolve() == source_abs.resolve():
            continue
        rel_t = str(path.relative_to(vault))
        if rel_t in updated_set or rel_t in skipped_set:
            continue
        result = append_backlink(path, source_rel, args.dry_run)
        if result == "added":
            updated_set.add(rel_t)
        elif result == "skipped":
            skipped_set.add(rel_t)
        # error 不计 — 视作 missing 调用方易误解, 静默

    if not args.quiet:
        print(
            json.dumps(
                {
                    "updated": sorted(updated_set),
                    "skipped": sorted(skipped_set),
                    "missing": missing,
                }
            )
        )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"unexpected: {e}", file=sys.stderr)
        sys.exit(0)
