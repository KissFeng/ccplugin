#!/usr/bin/env python3
"""cortex image_understand — image understanding CLI.

Driven by `<vault>/.cortex/config/image-understand.yaml` (OpenAI-compatible chat
completions w/ vision message format). Works with Zhipu (BigModel), OpenAI,
DashScope (Qwen-VL), or any OpenAI-compatible vision endpoint.

Subcommands:
    probe   [--config NAME] [--all]
    describe <image> [--config NAME] [--prompt TEXT]
    ask     <image> <question> [--config NAME]
    extract <image> --schema PATH [--config NAME]
    list    [--all]

Image input: local file path (base64-encoded) OR http(s) URL.

OUTPUT: JSON on stdout (probe / describe / ask / extract); table for list.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path
from typing import Any

from _provider_common import (
    active_providers,
    find_provider,
    http_request,
    load_provider_config,
    probe_one,
    render_provider_table,
    resolve_api_key,
    resolve_vault,
    save_provider_config,
    select_provider,
)

TOOL = "image_understand"
CONFIG_FILE = "image-understand.yaml"
DEFAULTS = {
    "random_selection": False,
    "default_provider": None,
    "max_tokens": 1024,
    "temperature": 0.3,
}

_MIME = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
    "bmp": "image/bmp",
}


# ---------- image input ------------------------------------------------------


def to_image_url(src: str) -> str:
    """Local path → data: URL; http(s) URL → passthrough."""
    if src.startswith(("http://", "https://", "data:")):
        return src
    p = Path(src).expanduser().resolve()
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"image not found: {src}")
    suffix = p.suffix.lstrip(".").lower()
    mime = _MIME.get(suffix, "image/png")
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def build_messages(prompt: str, image_url: str) -> list[dict]:
    return [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        }
    ]


def build_extract_prompt(schema_text: str) -> str:
    return (
        "Read the image and extract fields strictly matching the following JSON schema. "
        "Output ONLY a single JSON object — no prose, no markdown fences, no comments. "
        "Use null for any field not present in the image.\n\n"
        f"SCHEMA:\n{schema_text}"
    )


def strip_json_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t


# ---------- chat call --------------------------------------------------------


def call_chat(
    provider: dict, defaults: dict, messages: list[dict]
) -> tuple[dict | None, dict]:
    """Returns (response_dict_or_None, meta). meta has ok/status/error/usage."""
    key, src = resolve_api_key(provider)
    if not key:
        return None, {"ok": False, "error": f"no api key for {provider.get('name')}"}

    body: dict[str, Any] = {
        "model": provider.get("model"),
        "messages": messages,
    }
    max_tokens = provider.get("max_tokens") or defaults.get("max_tokens") or 1024
    temperature = provider.get("temperature")
    if temperature is None:
        temperature = defaults.get("temperature", 0.3)
    body["max_tokens"] = int(max_tokens)
    body["temperature"] = float(temperature)
    if isinstance(provider.get("extra_body"), dict):
        for k, v in provider["extra_body"].items():
            body.setdefault(k, v)

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
        body=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        timeout=timeout,
    )
    if err or not (200 <= status < 300):
        return None, {
            "ok": False,
            "status": status,
            "error": err or raw.decode("utf-8", errors="replace")[:400],
            "key_source": src,
        }
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        return None, {"ok": False, "error": f"bad json: {e}", "key_source": src}
    return payload, {"ok": True, "status": status, "key_source": src}


def extract_text(payload: dict) -> str:
    try:
        choice = (payload.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        content = msg.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            )
    except Exception:  # noqa: BLE001
        pass
    return ""


# ---------- subcommands ------------------------------------------------------


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


def _run_chat(args: argparse.Namespace, prompt: str) -> tuple[int, dict]:
    vault = resolve_vault()
    if vault is None:
        return 1, {"ok": False, "error": "vault not resolved"}
    cfg = load_provider_config(vault, CONFIG_FILE, DEFAULTS, TOOL)
    provider = select_provider(cfg, args.config)
    if provider is None:
        return 1, {"ok": False, "error": "no active provider available"}
    try:
        image_url = to_image_url(args.image)
    except FileNotFoundError as e:
        return 1, {"ok": False, "error": str(e)}

    messages = build_messages(prompt, image_url)
    payload, meta = call_chat(provider, cfg.get("defaults", {}), messages)
    if not meta.get("ok") or payload is None:
        meta.setdefault("provider", provider.get("name"))
        return 1, meta

    text = extract_text(payload)
    usage = payload.get("usage") or {}
    return 0, {
        "ok": True,
        "text": text,
        "provider": provider.get("name"),
        "model": provider.get("model"),
        "usage": usage,
        "key_source": meta.get("key_source"),
    }


def cmd_describe(args: argparse.Namespace) -> int:
    prompt = args.prompt or "请详细描述这张图片的内容、构图、风格和关键元素。"
    code, out = _run_chat(args, prompt)
    print(json.dumps(out, ensure_ascii=False))
    return code


def cmd_ask(args: argparse.Namespace) -> int:
    code, out = _run_chat(args, args.question)
    print(json.dumps(out, ensure_ascii=False))
    return code


def cmd_extract(args: argparse.Namespace) -> int:
    schema_path = Path(args.schema).expanduser()
    if not schema_path.exists() or not schema_path.is_file():
        print(
            json.dumps({"ok": False, "error": f"schema file not found: {args.schema}"})
        )
        return 1
    schema_text = schema_path.read_text(encoding="utf-8")
    prompt = build_extract_prompt(schema_text)
    code, out = _run_chat(args, prompt)
    if code != 0:
        print(json.dumps(out, ensure_ascii=False))
        return code

    raw_text = out.get("text", "")
    cleaned = strip_json_fence(raw_text)
    try:
        parsed = json.loads(cleaned)
        out["data"] = parsed
        out["raw_text"] = raw_text
    except json.JSONDecodeError as e:
        out["ok"] = False
        out["error"] = f"model output not valid JSON: {e}"
        out["raw_text"] = raw_text
        print(json.dumps(out, ensure_ascii=False))
        return 1
    print(json.dumps(out, ensure_ascii=False))
    return 0


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
        prog="image_understand", description="cortex image understanding CLI"
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_probe = sub.add_parser("probe", help="health check providers")
    p_probe.add_argument("--config", help="provider name (default: all active)")
    p_probe.add_argument(
        "--all", action="store_true", help="include disabled providers"
    )
    p_probe.set_defaults(func=cmd_probe)

    p_desc = sub.add_parser("describe", help="describe an image")
    p_desc.add_argument("image", help="local path or http(s) URL")
    p_desc.add_argument("--config", help="provider name")
    p_desc.add_argument("--prompt", help="override default describe prompt")
    p_desc.set_defaults(func=cmd_describe)

    p_ask = sub.add_parser("ask", help="ask a question about an image")
    p_ask.add_argument("image", help="local path or http(s) URL")
    p_ask.add_argument("question", help="natural-language question")
    p_ask.add_argument("--config", help="provider name")
    p_ask.set_defaults(func=cmd_ask)

    p_ext = sub.add_parser("extract", help="extract structured fields from an image")
    p_ext.add_argument("image", help="local path or http(s) URL")
    p_ext.add_argument(
        "--schema",
        required=True,
        help="path to a JSON schema file (informal shape allowed)",
    )
    p_ext.add_argument("--config", help="provider name")
    p_ext.set_defaults(func=cmd_extract)

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
