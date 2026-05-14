"""Cortex HTML render CLI — substitute `{{VAR}}` in vault templates.

Usage:

    python3 html_render.py --template <name> [--data '{"X":"v"}']

Reads `_templates/html/<name>.{html,md}` under the vault, substitutes
`{{VAR}}` placeholders from --data, prints the rendered text.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.cortex_common import _err, _ok, _vault_or_err  # noqa: E402


_TEMPLATE_NAME_RE = re.compile(r"^[A-Za-z0-9_\-]+$")


def cli_html_render(args: dict[str, Any]) -> dict[str, Any]:
    template = args.get("template")
    data = args.get("data") or {}
    if not isinstance(template, str) or not _TEMPLATE_NAME_RE.match(template):
        return _err(5, f"invalid template name: {template!r}")
    if not isinstance(data, dict):
        return _err(1, "data must be object")
    vault, err = _vault_or_err()
    if err:
        return err
    assert vault is not None
    tpl_dir = vault / "_templates" / "html"
    src: Path | None = None
    for ext in (".html", ".md"):
        cand = tpl_dir / f"{template}{ext}"
        if cand.is_file():
            src = cand
            break
    if src is None:
        return _err(2, f"template not found: {template}")
    text = src.read_text(encoding="utf-8")

    def _sub(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        val = data.get(key, match.group(0))
        return str(val)

    rendered = re.sub(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}", _sub, text)
    return _ok({"template": template, "path": str(src), "rendered": rendered})


def main() -> None:
    parser = argparse.ArgumentParser(description="cortex html render CLI")
    parser.add_argument("--template", required=True)
    parser.add_argument("--data", default="{}", help="JSON object, or '-' for stdin")
    ns = parser.parse_args()
    raw = sys.stdin.read() if ns.data == "-" else ns.data
    data = json.loads(raw) if raw else {}
    result = cli_html_render({"template": ns.template, "data": data})
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
