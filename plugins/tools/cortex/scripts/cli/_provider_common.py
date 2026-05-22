"""Shared provider helpers for cortex image_gen / image_understand CLIs.

OpenAI-compatible multi-provider configuration loaded from
`<vault>/.cortex/config/<file>.yaml`.

Public surface:
    resolve_vault()                  — env CORTEX_VAULT > ~/.cortex/config.json
    load_yaml(path) / dump_yaml(...) — soft PyYAML; ruamel optional
    load_provider_config(...)        — read + defaults seed
    save_provider_config(...)
    resolve_api_key(provider)        — env > inline; returns (key, source)
    mask(s)                          — for logs
    active_providers(cfg, all=False)
    find_provider(cfg, name)
    select_provider(cfg, name|None)  — explicit | random | first active
    http_request(...)                — stdlib urllib wrapper, returns (status, body, err)
    models_url(endpoint)             — derive `/v1/models` for probe
    probe_one(provider)              — mutates last_check/last_status/disabled
    now_iso() / sha8(s)              — small utils
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import random
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


# ---------- yaml IO ----------------------------------------------------------


def load_yaml(path: Path) -> tuple[Any, str | None]:
    if not path.exists():
        return None, None
    try:
        import yaml  # type: ignore
    except ImportError:
        return None, "PyYAML not installed (pip install pyyaml)"
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:  # noqa: BLE001
        return None, f"yaml parse error: {e}"
    return data, None


def dump_yaml(path: Path, data: Any) -> tuple[bool, str | None]:
    try:
        from ruamel.yaml import YAML  # type: ignore

        yml = YAML()
        yml.preserve_quotes = True
        with path.open("w", encoding="utf-8") as f:
            yml.dump(data, f)
        return True, None
    except ImportError:
        pass
    try:
        import yaml  # type: ignore
    except ImportError:
        return False, "PyYAML not installed"
    try:
        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
        return True, "ruamel.yaml absent — comments not preserved"
    except Exception as e:  # noqa: BLE001
        return False, f"yaml dump error: {e}"


# ---------- vault / config ---------------------------------------------------


def resolve_vault() -> Path | None:
    v = os.environ.get("CORTEX_VAULT") or os.environ.get("CORTEX_VAULT_PATH")
    if v:
        return Path(v).expanduser()
    cfg = Path.home() / ".cortex" / "config.json"
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("vault"):
                return Path(data["vault"]).expanduser()
        except Exception:  # noqa: BLE001
            pass
    return None


def load_provider_config(
    vault: Path,
    filename: str,
    default_defaults: dict | None = None,
    tool_label: str = "provider",
) -> dict:
    path = vault / ".cortex" / "config" / filename
    data, err = load_yaml(path)
    if err:
        print(f"[{tool_label}] {err}", file=sys.stderr)
        sys.exit(1)
    if data is None:
        return {"providers": [], "defaults": dict(default_defaults or {})}
    if not isinstance(data, dict):
        print(f"[{tool_label}] {filename} root must be mapping", file=sys.stderr)
        sys.exit(1)
    data.setdefault("providers", [])
    data.setdefault("defaults", {})
    for k, v in (default_defaults or {}).items():
        data["defaults"].setdefault(k, v)
    return data


def save_provider_config(
    vault: Path, filename: str, data: dict, tool_label: str = "provider"
) -> None:
    path = vault / ".cortex" / "config" / filename
    ok, warn = dump_yaml(path, data)
    if not ok:
        print(f"[{tool_label}] save config failed: {warn}", file=sys.stderr)
        sys.exit(1)
    if warn:
        print(f"[{tool_label}] {warn}", file=sys.stderr)


# ---------- helpers ----------------------------------------------------------


def mask(s: str) -> str:
    if not s or len(s) < 8:
        return "***"
    keep = max(2, len(s) // 10)
    return f"{s[:keep]}***{s[-keep:]}"


def resolve_api_key(p: dict) -> tuple[str | None, str | None]:
    env_name = p.get("api_key_env")
    if env_name:
        v = os.environ.get(env_name)
        if v:
            return v, "env"
    inline = p.get("api_key")
    if inline:
        return inline, "inline"
    return None, None


def active_providers(cfg: dict, include_disabled: bool = False) -> list[dict]:
    out = []
    for p in cfg.get("providers", []):
        if not isinstance(p, dict):
            continue
        if not include_disabled and p.get("disabled"):
            continue
        out.append(p)
    return out


def find_provider(cfg: dict, name: str) -> dict | None:
    for p in cfg.get("providers", []):
        if isinstance(p, dict) and p.get("name") == name:
            return p
    return None


def select_provider(cfg: dict, name: str | None) -> dict | None:
    if name:
        p = find_provider(cfg, name)
        if p and not p.get("disabled"):
            return p
        return None
    active = active_providers(cfg)
    if not active:
        return None
    defaults = cfg.get("defaults", {}) or {}
    default_name = defaults.get("default_provider")
    if default_name:
        p = find_provider(cfg, default_name)
        if p and not p.get("disabled"):
            return p
    if defaults.get("random_selection", True):
        return random.choice(active)
    return active[0]


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha8(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]


def http_request(
    url: str,
    method: str = "GET",
    headers: dict | None = None,
    body: bytes | None = None,
    timeout: int = 30,
) -> tuple[int, bytes, str | None]:
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(), None
    except urllib.error.HTTPError as e:
        try:
            data = e.read()
        except Exception:  # noqa: BLE001
            data = b""
        return e.code, data, None
    except socket.timeout:
        return 0, b"", "timeout"
    except urllib.error.URLError as e:
        return 0, b"", f"network: {e.reason}"
    except Exception as e:  # noqa: BLE001
        return 0, b"", f"error: {e}"


def download(
    url: str, dst: Path, timeout: int = 60, ua: str = "cortex-cli/1"
) -> tuple[bool, str | None]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        return True, None
    except Exception as e:  # noqa: BLE001
        return False, str(e)


# ---------- probe ------------------------------------------------------------


def models_url(endpoint: str) -> str:
    u = urlparse(endpoint)
    parts = u.path.rstrip("/").split("/")
    while parts and parts[-1] in ("generations", "images", "completions", "chat"):
        parts.pop()
    base = parts or [""]
    new_path = "/".join(base) + "/models"
    if not new_path.startswith("/"):
        new_path = "/" + new_path
    return f"{u.scheme}://{u.netloc}{new_path}"


def probe_one(p: dict) -> dict:
    name = p.get("name", "?")
    timeout = int(p.get("timeout_seconds") or 30)
    key, _src = resolve_api_key(p)
    headers = {"Accept": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    if isinstance(p.get("extra_headers"), dict):
        for k, v in p["extra_headers"].items():
            headers[str(k)] = str(v)

    endpoint = p.get("endpoint") or ""
    status, _data, err = http_request(
        models_url(endpoint), method="GET", headers=headers, timeout=timeout
    )

    p["last_check"] = now_iso()
    p["last_status"] = status

    auth_error_codes = (401, 403, 404)
    is_healthy = 200 <= status < 300
    is_auth_err = status in auth_error_codes

    if is_healthy:
        if p.get("disabled"):
            p["disabled"] = False
        return {"name": name, "status": status, "ok": True, "error": None}

    if is_auth_err and not p.get("trusted"):
        p["disabled"] = True

    return {
        "name": name,
        "status": status,
        "ok": False,
        "error": err or f"http {status}",
    }


def render_provider_table(cfg: dict, include_disabled: bool = False) -> str:
    providers = active_providers(cfg, include_disabled=include_disabled)
    if not providers:
        return "(no providers configured)"
    cols = ("name", "host", "model", "trusted", "disabled", "last_status", "last_check")
    rows = []
    for p in providers:
        host = urlparse(p.get("endpoint") or "").netloc or "-"
        rows.append(
            (
                p.get("name", "-"),
                host,
                p.get("model", "-"),
                str(bool(p.get("trusted"))),
                str(bool(p.get("disabled"))),
                str(p.get("last_status") or "-"),
                str(p.get("last_check") or "-"),
            )
        )
    widths = [max(len(c), *(len(r[i]) for r in rows)) for i, c in enumerate(cols)]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    out = [fmt.format(*cols), fmt.format(*("-" * w for w in widths))]
    out.extend(fmt.format(*r) for r in rows)
    return "\n".join(out)
