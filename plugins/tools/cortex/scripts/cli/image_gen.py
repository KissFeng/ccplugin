#!/usr/bin/env python3
"""cortex image_gen — text-to-image CLI.

Driven by `<vault>/.cortex/config/image-gen.yaml` (multi-provider, OpenAI-compat).

Subcommands:
    probe   [--config NAME] [--all]      ping providers, mark untrusted ones disabled
    generate <prompt> [--config NAME] [--output PATH] [--size WxH] [--style S]
    list    [--all]                      tabulate providers

OUTPUT:
    JSON on stdout (for `probe` / `generate`); plaintext table (for `list`).

Network: stdlib `urllib` only. No new deps. `PyYAML` soft-required to load yaml.

Security:
    api_key_env > api_key fallback. When logging, keys are masked (80% middle).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any

from _provider_common import (
    active_providers,
    download,
    find_provider,
    http_request,
    load_provider_config,
    now_iso,
    probe_one,
    render_provider_table,
    resolve_api_key,
    resolve_vault,
    save_provider_config,
    select_provider,
    sha8,
)

TOOL = "image_gen"
CONFIG_FILE = "image-gen.yaml"
DEFAULTS = {"random_selection": True, "output_dir": "_assets/images"}


# ---------- probe ------------------------------------------------------------


def cmd_probe(args: argparse.Namespace) -> int:
    vault = resolve_vault()
    if vault is None:
        print('{"ok": false, "error": "vault not resolved"}')
        return 1
    cfg = load_provider_config(vault, CONFIG_FILE, DEFAULTS, TOOL)

    if args.config:
        p = find_provider(cfg, args.config)
        if p is None:
            print(f'{{"ok": false, "error": "provider not found: {args.config}"}}')
            return 1
        targets = [p]
    else:
        targets = active_providers(cfg, include_disabled=bool(args.all))

    healthy, disabled_now, errors = [], [], []
    for p in targets:
        r = probe_one(p)
        if r["ok"]:
            healthy.append(r["name"])
        else:
            errors.append(r)
            if p.get("disabled"):
                disabled_now.append(r["name"])

    if targets:
        save_provider_config(vault, CONFIG_FILE, cfg, TOOL)

    print(
        json.dumps(
            {
                "checked": len(targets),
                "healthy": healthy,
                "disabled_now": disabled_now,
                "errors": errors,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


# ---------- generate ---------------------------------------------------------


def cmd_generate(args: argparse.Namespace) -> int:
    vault = resolve_vault()
    if vault is None:
        print('{"ok": false, "error": "vault not resolved"}')
        return 1
    cfg = load_provider_config(vault, CONFIG_FILE, DEFAULTS, TOOL)
    provider = select_provider(cfg, args.config)
    if provider is None:
        print(json.dumps({"ok": False, "error": "no active provider available"}))
        return 1

    key, src = resolve_api_key(provider)
    if not key:
        print(
            json.dumps({"ok": False, "error": f"no api key for {provider.get('name')}"})
        )
        return 1

    body: dict[str, Any] = {
        "model": provider.get("model"),
        "prompt": args.prompt,
    }
    if args.size:
        body["size"] = args.size
    if args.style:
        body["style"] = args.style
    if isinstance(provider.get("extra_body"), dict):
        for k, v in provider["extra_body"].items():
            body.setdefault(k, v)
    body.setdefault("size", "1024x1024")

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if isinstance(provider.get("extra_headers"), dict):
        for k, v in provider["extra_headers"].items():
            headers[str(k)] = str(v)

    timeout = int(provider.get("timeout_seconds") or 60)
    status, raw, err = http_request(
        provider["endpoint"],
        method="POST",
        headers=headers,
        body=json.dumps(body).encode("utf-8"),
        timeout=timeout,
    )
    if err or not (200 <= status < 300):
        print(
            json.dumps(
                {
                    "ok": False,
                    "provider": provider.get("name"),
                    "status": status,
                    "error": err or raw.decode("utf-8", errors="replace")[:400],
                },
                ensure_ascii=False,
            )
        )
        return 1

    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": f"bad json: {e}"}))
        return 1

    items = payload.get("data") or []
    if not items:
        print(json.dumps({"ok": False, "error": "empty data[]", "payload": payload}))
        return 1
    item = items[0]
    img_url = item.get("url")
    img_b64 = item.get("b64_json")

    output_dir = (
        Path(args.output).parent
        if args.output
        else (vault / cfg.get("defaults", {}).get("output_dir", "_assets/images"))
    )
    date_str = _dt.datetime.now().strftime("%Y-%m-%d")
    sha = sha8(args.prompt + provider.get("name", "") + now_iso())
    filename = Path(args.output).name if args.output else f"{date_str}-{sha}.png"
    out_path = output_dir / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if img_url:
        ok, derr = download(img_url, out_path, timeout=timeout, ua="cortex-image-gen/1")
        if not ok:
            print(json.dumps({"ok": False, "error": f"download: {derr}"}))
            return 1
    elif img_b64:
        import base64

        out_path.write_bytes(base64.b64decode(img_b64))
    else:
        print(json.dumps({"ok": False, "error": "no url nor b64 in response"}))
        return 1

    md_path = out_path.with_suffix(".md")
    fm_lines = [
        "---",
        "type: image",
        f"title: {filename}",
        f"created: {now_iso()}",
        f"provider: {provider.get('name')}",
        f"model: {provider.get('model')}",
        f"size: {body['size']}",
        "prompt: |",
        *(f"  {ln}" for ln in args.prompt.splitlines()),
        "---",
        "",
        f"![[{filename}]]",
        "",
    ]
    md_path.write_text("\n".join(fm_lines), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "path": str(out_path),
                "sidecar": str(md_path),
                "provider": provider.get("name"),
                "model": provider.get("model"),
                "size": body["size"],
                "key_source": src,
            },
            ensure_ascii=False,
        )
    )
    return 0


# ---------- list -------------------------------------------------------------


def cmd_list(args: argparse.Namespace) -> int:
    vault = resolve_vault()
    if vault is None:
        print("vault not resolved", file=sys.stderr)
        return 1
    cfg = load_provider_config(vault, CONFIG_FILE, DEFAULTS, TOOL)
    print(render_provider_table(cfg, include_disabled=bool(args.all)))
    return 0


# ---------- main -------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="image_gen", description="cortex text-to-image CLI"
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_probe = sub.add_parser("probe", help="health check providers")
    p_probe.add_argument("--config", help="provider name (default: all active)")
    p_probe.add_argument(
        "--all", action="store_true", help="include disabled providers"
    )
    p_probe.set_defaults(func=cmd_probe)

    p_gen = sub.add_parser("generate", help="generate image from prompt")
    p_gen.add_argument("prompt", help="text prompt")
    p_gen.add_argument("--config", help="provider name (default: random active)")
    p_gen.add_argument(
        "--output",
        help="output file path (default: vault/<output_dir>/<date>-<sha>.png)",
    )
    p_gen.add_argument("--size", help="image size, e.g. 1024x1024")
    p_gen.add_argument("--style", help="provider-specific style (e.g. vivid / natural)")
    p_gen.set_defaults(func=cmd_generate)

    p_list = sub.add_parser("list", help="list configured providers")
    p_list.add_argument("--all", action="store_true", help="include disabled providers")
    p_list.set_defaults(func=cmd_list)

    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
