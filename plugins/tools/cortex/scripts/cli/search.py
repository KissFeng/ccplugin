"""`cortex_search` CLI — multi-level fallback search over the vault.

Position in the wider search hierarchy (see `cortex-search` SKILL.md):

- L1/L2 (AI-facing): `mcp__obsidian__obsidian_simple_search` /
  `mcp__obsidian__obsidian_complex_search` — handled by the model, not here.
- **L3 (this CLI)**: invoked via `~/.cortex/scripts/search.sh` when MCP is
  unreachable. This CLI **cannot** call MCP itself (no protocol bridge from a
  Python subprocess), so it stays in the disk/REST fallback layer.
- L4: `rg` — last-ditch, also model-driven outside this CLI.

Internal fallback order (this CLI only):

1. `hot.md` grep — fast cache of recently-touched notes.
2. `index.md` grep — long-lived registry of canonical entries.
3. Smart Connections REST (`CORTEX_SC_URL`, default `http://127.0.0.1:27123`)
   semantic search if reachable within 1s.
4. `rg --json` over `知识库/`, capped at 50 hits.

Each hit is `{path, title, snippet, score, source}`. The tool returns a single
`TextContent` whose `.text` is the JSON-serialized list so models can parse it
deterministically.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# Allow direct `python3 search.py`: add this dir to sys.path so `from lib...` works.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.cortex_common import SCOPE_GLOB as _SCOPE_GLOB  # noqa: E402
from lib.vault_path import resolve_vault  # noqa: E402


def _title_from(path: Path) -> str:
    # Prefer first `# heading` if present, else filename stem.
    try:
        with path.open("r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if line.startswith("# "):
                    return line[2:].strip()
                # don't read forever
                if path.stat().st_size > 32_768:
                    break
    except OSError:
        pass
    return path.stem


def _snippet(text: str, query: str, ctx: int = 60) -> str:
    m = re.search(re.escape(query), text, re.IGNORECASE)
    if not m:
        return text[:ctx].replace("\n", " ")
    start = max(0, m.start() - ctx)
    end = min(len(text), m.end() + ctx)
    return text[start:end].replace("\n", " ")


def _grep_file(
    vault: Path, rel: str, query: str, source: str
) -> list[dict[str, Any]]:
    path = vault / rel
    if not path.is_file():
        return []
    hits: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    q = query.lower()
    for line in text.splitlines():
        if q in line.lower():
            hits.append(
                {
                    "path": str(path),
                    "title": _title_from(path),
                    "snippet": line.strip()[:240],
                    "score": 1.0,
                    "source": source,
                }
            )
    return hits


def _smart_connections(
    query: str, limit: int, base: str
) -> list[dict[str, Any]] | None:
    """Probe SC then POST /search. Return None if unreachable."""
    info_url = f"{base.rstrip('/')}/embeddings/info"
    try:
        urllib.request.urlopen(info_url, timeout=1.0).read()  # noqa: S310
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError):
        return None
    search_url = f"{base.rstrip('/')}/search"
    payload = json.dumps({"query": query, "top_k": limit}).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310
        search_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=5.0).read()  # noqa: S310
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError):
        return []
    try:
        data = json.loads(resp.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return []
    hits: list[dict[str, Any]] = []
    items = data.get("hits") or data.get("results") or data
    if not isinstance(items, list):
        return []
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        hits.append(
            {
                "path": item.get("path") or item.get("file") or "",
                "title": item.get("title") or item.get("name") or "",
                "snippet": (item.get("snippet") or item.get("text") or "")[:240],
                "score": float(item.get("score") or 0.0),
                "source": "smart-connections",
            }
        )
    return hits


def _ripgrep(vault: Path, scope_dir: str, query: str) -> list[dict[str, Any]]:
    target = vault / scope_dir
    if not target.is_dir():
        return []
    try:
        proc = subprocess.run(  # noqa: S603,S607
            ["rg", "--json", "-i", "--max-count", "1", query, str(target)],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    hits: list[dict[str, Any]] = []
    for raw in proc.stdout.splitlines():
        if len(hits) >= 50:
            break
        try:
            evt = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if evt.get("type") != "match":
            continue
        data = evt.get("data") or {}
        path = (data.get("path") or {}).get("text") or ""
        line_text = (data.get("lines") or {}).get("text") or ""
        if not path:
            continue
        p = Path(path)
        hits.append(
            {
                "path": path,
                "title": _title_from(p),
                "snippet": line_text.strip()[:240],
                "score": 0.5,
                "source": "ripgrep",
            }
        )
    return hits


def _load_local_rest_api_creds(vault: Path) -> tuple[str, str] | None:
    """Read Obsidian Local REST API plugin config.

    Returns (base_url, api_key) or None if plugin absent / config invalid.
    Prefers insecure HTTP port (no cert verification overhead) since this
    is localhost-only.
    """
    cfg = vault / ".obsidian" / "plugins" / "obsidian-local-rest-api" / "data.json"
    if not cfg.is_file():
        return None
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    key = data.get("apiKey")
    if not isinstance(key, str) or not key:
        return None
    port = data.get("insecurePort") if data.get("enableInsecureServer") else None
    if port:
        return (f"http://127.0.0.1:{int(port)}", key)
    sec_port = data.get("port") if data.get("enableSecureServer") else None
    if sec_port:
        return (f"https://127.0.0.1:{int(sec_port)}", key)
    return None


def _local_rest_api_search(
    query: str, limit: int, vault: Path
) -> list[dict[str, Any]] | None:
    """Obsidian Local REST API POST /search/simple/?query=<q>.

    Returns None if plugin unreachable / not configured. Empty list if
    reachable but 0 hits (caller should NOT fall back further on empty —
    means Obsidian's own search index found nothing).
    """
    creds = _load_local_rest_api_creds(vault)
    if not creds:
        return None
    base, key = creds
    import ssl  # noqa: PLC0415
    from urllib.parse import quote  # noqa: PLC0415
    url = f"{base}/search/simple/?query={quote(query)}&contextLength=120"
    req = urllib.request.Request(  # noqa: S310
        url,
        method="POST",
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
    )
    ctx = ssl._create_unverified_context() if base.startswith("https") else None
    try:
        resp = urllib.request.urlopen(req, timeout=3.0, context=ctx).read()  # noqa: S310
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError):
        return None
    try:
        data = json.loads(resp.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, list):
        return []
    hits: list[dict[str, Any]] = []
    for item in data[:limit * 3]:  # over-fetch for rerank
        if not isinstance(item, dict):
            continue
        filename = item.get("filename") or ""
        if not filename:
            continue
        matches = item.get("matches") or []
        snippet = ""
        if matches and isinstance(matches[0], dict):
            snippet = (matches[0].get("context") or "")[:240]
        path = vault / filename
        hits.append(
            {
                "path": str(path),
                "title": _title_from(path) if path.is_file() else Path(filename).stem,
                "snippet": snippet,
                "score": float(item.get("score") or 1.5),  # Obsidian's own = high
                "source": "obsidian-rest",
            }
        )
    return hits


def _omnisearch_search(
    query: str, limit: int, vault: Path
) -> list[dict[str, Any]] | None:
    """Omnisearch plugin HTTP API (if installed + REST API configured).

    Omnisearch exposes results via Local REST API plugin's `/omnisearch`
    endpoint when both plugins present.
    """
    creds = _load_local_rest_api_creds(vault)
    if not creds:
        return None
    base, key = creds
    om_dir = vault / ".obsidian" / "plugins" / "omnisearch"
    if not om_dir.is_dir():
        return None
    import ssl  # noqa: PLC0415
    from urllib.parse import quote  # noqa: PLC0415
    url = f"{base}/search/omnisearch?query={quote(query)}"
    req = urllib.request.Request(  # noqa: S310
        url,
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
    )
    ctx = ssl._create_unverified_context() if base.startswith("https") else None
    try:
        resp = urllib.request.urlopen(req, timeout=3.0, context=ctx).read()  # noqa: S310
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError):
        return None
    try:
        data = json.loads(resp.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    items = data if isinstance(data, list) else (data.get("results") or [])
    hits: list[dict[str, Any]] = []
    for item in items[:limit * 3]:
        if not isinstance(item, dict):
            continue
        path_rel = item.get("path") or item.get("filename") or ""
        if not path_rel:
            continue
        path = vault / path_rel
        hits.append(
            {
                "path": str(path),
                "title": item.get("basename") or _title_from(path) if path.is_file() else Path(path_rel).stem,
                "snippet": (item.get("excerpt") or "")[:240],
                "score": float(item.get("score") or 2.0),  # Omnisearch BM25-like = highest
                "source": "omnisearch",
            }
        )
    return hits


_STOPWORDS_ZH = {"的", "了", "是", "在", "和", "与", "或", "及", "等", "怎么", "如何", "什么", "为什么"}
_STOPWORDS_EN = {"the", "a", "an", "is", "are", "of", "to", "in", "on", "for", "and", "or", "how", "what", "why"}


def _tokenize(query: str) -> list[str]:
    """Split query into search-worthy tokens.

    Keep tokens ≥ 2 chars (zh) / ≥ 3 chars (en); drop stopwords.
    Result preserves order, deduplicated.
    """
    raw = re.split(r"[\s,;:/，、；：·]+", query.strip())
    seen: set[str] = set()
    out: list[str] = []
    for t in raw:
        t = t.strip("()[]{}\"'.,!?。，！？")
        if not t:
            continue
        low = t.lower()
        if low in _STOPWORDS_EN or t in _STOPWORDS_ZH:
            continue
        # zh: keep len>=2; en/digit: keep len>=3
        has_cjk = any("一" <= ch <= "鿿" for ch in t)
        if has_cjk and len(t) < 2:
            continue
        if not has_cjk and len(t) < 3:
            continue
        if low in seen:
            continue
        seen.add(low)
        out.append(t)
    return out


def _dedup(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Dedupe by path; keep best score across sources; merge sources list."""
    by_path: dict[str, dict[str, Any]] = {}
    for h in hits:
        path = h.get("path", "")
        if not path:
            continue
        # collect this hit's sources (prefer pre-set `sources` list, fall back to single `source`)
        h_srcs = h.get("sources") or ([h.get("source", "?")] if h.get("source") else [])
        prev = by_path.get(path)
        if prev is None:
            new = dict(h)
            new["sources"] = list(h_srcs)
            by_path[path] = new
            continue
        # merge: max score, append source
        if float(h.get("score", 0)) > float(prev.get("score", 0)):
            prev["score"] = h["score"]
            if h.get("snippet"):
                prev["snippet"] = h["snippet"]
        srcs = prev.setdefault("sources", [])
        for s in h_srcs:
            if s and s not in srcs:
                srcs.append(s)
    return sorted(by_path.values(), key=lambda x: -float(x.get("score", 0)))


def _run_all_layers(
    query: str, limit: int, scope: str, vault: Path
) -> list[dict[str, Any]]:
    """Invoke all search layers for a single query, return merged hits.

    Layers (each independent, all errors swallowed to empty):
    1. Omnisearch (HTTP, BM25-like) — highest base score
    2. Obsidian Local REST API simple search (HTTP) — high base
    3. hot.md grep (cached recent)
    4. index.md grep (canonical entries)
    5. Smart Connections REST (semantic, optional)
    6. ripgrep (cap 50)
    """
    hits: list[dict[str, Any]] = []
    om = _omnisearch_search(query, limit, vault)
    if om:
        hits.extend(om)
    rest = _local_rest_api_search(query, limit, vault)
    if rest:
        hits.extend(rest)
    if scope == "all":
        hits.extend(_grep_file(vault, "hot.md", query, "hot"))
    hits.extend(_grep_file(vault, "index.md", query, "index"))
    sc_base = os.environ.get("CORTEX_SC_URL", "http://127.0.0.1:27123")
    sc_hits = _smart_connections(query, limit, sc_base)
    if sc_hits:
        hits.extend(sc_hits)
    hits.extend(_ripgrep(vault, _SCOPE_GLOB[scope], query))
    return _dedup(hits)


def cli_search(args: dict) -> list[dict[str, Any]]:
    """CLI entry: returns hits list (deduped + ranked).

    Strategy: try full query across all layers; if 0 hits, tokenize and
    retry each token in parallel-spirit (sequential here), merge — aim
    is "尽可能不返回空".
    """
    query = (args or {}).get("query")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("cortex_search: 'query' required (non-empty string)")
    limit = int((args or {}).get("limit") or 10)
    scope = (args or {}).get("scope") or "all"
    if scope not in _SCOPE_GLOB:
        raise ValueError(f"cortex_search: invalid scope {scope!r}")

    vault = resolve_vault()

    # phase 1: full query across all layers
    hits = _run_all_layers(query, limit, scope, vault)
    if hits:
        return hits[:limit]

    # phase 2: tokenize + retry each token, merge, score-attenuated
    tokens = _tokenize(query)
    if len(tokens) <= 1:
        return []
    fallback: list[dict[str, Any]] = []
    for tok in tokens:
        sub = _run_all_layers(tok, limit, scope, vault)
        for h in sub:
            # attenuate: token match weaker than full-query match
            h = dict(h)
            h["score"] = float(h.get("score", 0)) * 0.6
            h["sources"] = (h.get("sources") or [h.get("source", "?")]) + [f"split:{tok}"]
            fallback.append(h)
    return _dedup(fallback)[:limit]


def main() -> None:
    parser = argparse.ArgumentParser(description="cortex_search CLI: multi-level fallback search over vault.")
    parser.add_argument("--query", required=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--scope", default="all", choices=list(_SCOPE_GLOB.keys()))
    ns = parser.parse_args()
    hits = cli_search({"query": ns.query, "limit": ns.limit, "scope": ns.scope})
    print(json.dumps(hits, ensure_ascii=False))


if __name__ == "__main__":
    main()
