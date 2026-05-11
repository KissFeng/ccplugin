"""Minimal YAML frontmatter read/write (stdlib only).

We deliberately do not pull PyYAML: the cortex frontmatter schema is flat
(scalars + simple string lists) and round-tripping our own writes is enough.
For external notes with richer YAML, `parse` falls back to returning the raw
block as a single `_raw` key so callers can preserve it.
"""

from __future__ import annotations

import re
from typing import Any

_FM_RE = re.compile(r"\A---\n(.*?)\n---\n?(.*)\Z", re.DOTALL)


def _scalar(value: str) -> Any:
    v = value.strip()
    if v in ("true", "True"):
        return True
    if v in ("false", "False"):
        return False
    if v.startswith(("'", '"')) and v.endswith(v[0]) and len(v) >= 2:
        return v[1:-1]
    return v


def parse(text: str) -> tuple[dict[str, Any], str]:
    """Return `(frontmatter_dict, body)`. Missing fm → `({}, text)`."""
    m = _FM_RE.match(text)
    if not m:
        return {}, text
    block, body = m.group(1), m.group(2)
    fm: dict[str, Any] = {}
    current_list_key: str | None = None
    for raw_line in block.splitlines():
        if not raw_line.strip():
            current_list_key = None
            continue
        if raw_line.startswith("  - ") and current_list_key:
            fm.setdefault(current_list_key, []).append(_scalar(raw_line[4:]))
            continue
        if ":" not in raw_line:
            current_list_key = None
            continue
        key, _, rest = raw_line.partition(":")
        key = key.strip()
        rest = rest.strip()
        if rest == "":
            current_list_key = key
            fm.setdefault(key, [])
        elif rest == "[]":
            current_list_key = None
            fm[key] = []
        else:
            current_list_key = None
            fm[key] = _scalar(rest)
    return fm, body


def _dump_value(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return str(v)


def dump(fm: dict[str, Any], body: str) -> str:
    """Serialize `fm` as YAML frontmatter prepended to `body`."""
    lines = ["---"]
    for key, value in fm.items():
        if isinstance(value, list):
            if not value:
                lines.append(f"{key}: []")
            else:
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {_dump_value(item)}")
        else:
            lines.append(f"{key}: {_dump_value(value)}")
    lines.append("---")
    tail = body if body.startswith("\n") else "\n" + body
    return "\n".join(lines) + tail
