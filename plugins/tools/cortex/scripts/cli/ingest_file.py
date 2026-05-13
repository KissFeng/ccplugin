"""`cortex_ingest_file` MCP tool — read local file, extract, save (P4)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Allow direct CLI invocation.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.extractors import docx as docx_extractor  # noqa: E402
from lib.extractors import epub as epub_extractor  # noqa: E402
from lib.extractors import pdf as pdf_extractor  # noqa: E402
from save import _save_internal  # noqa: E402

_SUPPORTED_EXTS = {".pdf", ".epub", ".docx", ".md", ".txt", ".markdown"}


def cli_ingest_file(args: dict) -> dict:
    args = args or {}
    raw_path = args.get("path")
    kind = args.get("kind")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError("cortex_ingest_file: 'path' required (non-empty string)")
    if kind not in ("concept", "domain", "log"):
        raise ValueError(
            "cortex_ingest_file: 'kind' must be one of concept/domain/log"
        )

    path = Path(os.path.expanduser(raw_path)).resolve()
    if not path.exists():
        raise OSError(f"cortex_ingest_file: file not found: {path}")
    if not path.is_file():
        raise OSError(f"cortex_ingest_file: not a regular file: {path}")
    if not os.access(path, os.R_OK):
        raise OSError(f"cortex_ingest_file: not readable: {path}")

    ext = path.suffix.lower()
    if ext not in _SUPPORTED_EXTS:
        raise ValueError(f"cortex_ingest_file: unsupported extension: {ext}")

    warnings: list[str] = []
    extracted_title: str | None = None

    if ext == ".pdf":
        result = pdf_extractor.extract(path)
        body = result["body"]
        extracted_title = result.get("title")
        warnings.extend(result.get("warnings") or [])
    elif ext == ".epub":
        result = epub_extractor.extract(path)
        body = result["body"]
        extracted_title = result.get("title")
        warnings.extend(result.get("warnings") or [])
    elif ext == ".docx":
        result = docx_extractor.extract(path)
        body = result["body"]
        extracted_title = result.get("title")
        warnings.extend(result.get("warnings") or [])
    else:  # .md, .markdown, .txt -- read directly
        try:
            body = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            body = path.read_text(encoding="utf-8", errors="replace")
            warnings.append("encoding-fallback")
        extracted_title = None

    if not body or not body.strip():
        raise RuntimeError("cortex_ingest_file: extracted body is empty")

    title = args.get("title") or extracted_title or path.stem

    save_res = _save_internal(
        kind=kind,
        title=title,
        body=body,
        tags=args.get("tags") or [],
        host=args.get("host"),
        org=args.get("org"),
        repo=args.get("repo"),
        source_meta={"file": str(path), "ext": ext},
    )

    result_obj = {
        "path": save_res["path"],
        "source_file": str(path),
        "block_ids": save_res["block_ids"],
        "hits": save_res["hits"],
        "warnings": warnings,
    }
    return result_obj


def main() -> None:
    parser = argparse.ArgumentParser(description="cortex_ingest_file CLI.")
    parser.add_argument("--path", required=True)
    parser.add_argument("--kind", required=True, choices=["concept", "domain", "log"])
    parser.add_argument("--title")
    parser.add_argument("--host")
    parser.add_argument("--org")
    parser.add_argument("--repo")
    parser.add_argument("--tags", default="", help="Comma-separated tags")
    ns = parser.parse_args()
    tags = [t.strip() for t in ns.tags.split(",") if t.strip()] if ns.tags else []
    result = cli_ingest_file(
        {
            "path": ns.path,
            "kind": ns.kind,
            "title": ns.title,
            "host": ns.host,
            "org": ns.org,
            "repo": ns.repo,
            "tags": tags,
        }
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
