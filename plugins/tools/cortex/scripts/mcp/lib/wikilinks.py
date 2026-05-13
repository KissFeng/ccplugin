"""Helpers for `[[wikilink]]` and `^block-id` markers."""

from __future__ import annotations

import hashlib
import re
import unicodedata

_BLOCK_ID_LINE = re.compile(r"\s\^[a-zA-Z0-9-]+\s*$")
_PUNCT_RE = re.compile(r"[^\w\s-]", re.UNICODE)
_SPACE_RE = re.compile(r"[\s_]+")
_DASH_RE = re.compile(r"-+")


def slugify(title: str) -> str:
    """ASCII-best-effort slug; preserves non-ASCII letters (CJK ok)."""
    norm = unicodedata.normalize("NFKC", title).strip()
    norm = _PUNCT_RE.sub(" ", norm)
    norm = _SPACE_RE.sub("-", norm).strip("-")
    norm = _DASH_RE.sub("-", norm)
    return norm.lower() or "untitled"


def _sha8(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]


def add_block_ids(body: str) -> tuple[str, list[str]]:
    """Append `^cortex-<sha8>` to each paragraph that lacks a block-id.

    Paragraphs are separated by blank lines. Code fences and YAML blocks are
    skipped entirely. Headings (lines starting with `#`) are skipped — Obsidian
    uses heading anchors for those.
    """
    lines = body.splitlines(keepends=False)
    out: list[str] = []
    ids: list[str] = []
    paragraph: list[str] = []
    in_fence = False

    def flush() -> None:
        if not paragraph:
            return
        joined = "\n".join(paragraph)
        text = joined.rstrip()
        head = paragraph[0].lstrip()
        skip = (
            not text
            or head.startswith("#")
            or head.startswith("```")
            or head.startswith("|")
        )
        if skip:
            out.extend(paragraph)
            paragraph.clear()
            return
        last = paragraph[-1]
        if _BLOCK_ID_LINE.search(last):
            out.extend(paragraph)
        else:
            bid = f"cortex-{_sha8(text)}"
            ids.append(bid)
            paragraph[-1] = f"{last} ^{bid}"
            out.extend(paragraph)
        paragraph.clear()

    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("```"):
            # toggle fence; keep current paragraph open so fenced block joins it
            paragraph.append(line)
            in_fence = not in_fence
            continue
        if in_fence:
            paragraph.append(line)
            continue
        if line.strip() == "":
            flush()
            out.append(line)
            continue
        paragraph.append(line)
    flush()
    return "\n".join(out), ids
