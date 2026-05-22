#!/usr/bin/env python3
"""cortex audio_understand — audio understanding CLI.

Driven by `<vault>/.cortex/config/audio-understand.yaml`. Two modes:
    mode=asr   — Whisper-style multipart upload to /v1/audio/transcriptions.
                 Output: transcribed text only.
    mode=chat  — OpenAI-compatible chat completions with audio content
                 (gpt-4o-audio-preview, qwen-audio, zhipu glm-4-voice).
                 Output: free-form text (supports ask/describe).

Subcommands:
    probe   [--config NAME] [--all]
    transcribe <audio> [--config NAME] [--language LANG]   (asr mode preferred)
    describe   <audio> [--config NAME] [--prompt TEXT]     (chat mode preferred)
    ask        <audio> <question> [--config NAME]          (chat mode preferred)
    list       [--all]

Audio input: local file path (base64 / multipart upload).
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
    http_multipart,
    http_request,
    load_provider_config,
    probe_one,
    render_provider_table,
    resolve_api_key,
    resolve_vault,
    save_provider_config,
    select_provider,
)

TOOL = "audio_understand"
CONFIG_FILE = "audio-understand.yaml"
DEFAULTS = {
    "random_selection": False,
    "default_provider": None,
    "max_tokens": 1024,
    "temperature": 0.3,
    "mode": "asr",
    "language": None,
}

_AUDIO_MIME = {
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "m4a": "audio/mp4",
    "mp4": "audio/mp4",
    "webm": "audio/webm",
    "flac": "audio/flac",
    "ogg": "audio/ogg",
    "opus": "audio/opus",
}

_OPENAI_FORMAT = {
    "wav": "wav",
    "mp3": "mp3",
    "m4a": "m4a",
    "mp4": "mp4",
    "webm": "webm",
    "flac": "flac",
    "ogg": "ogg",
    "opus": "opus",
}


# ---------- input ------------------------------------------------------------


def detect_audio_format(src: str) -> tuple[str, str]:
    """Return (mime, openai_format_token) from filename suffix."""
    suffix = Path(src).suffix.lstrip(".").lower()
    mime = _AUDIO_MIME.get(suffix, "audio/wav")
    fmt = _OPENAI_FORMAT.get(suffix, "wav")
    return mime, fmt


def read_audio_b64(src: str) -> tuple[bytes, str, str]:
    """Read local file → (raw_bytes, mime, openai_format)."""
    p = Path(src).expanduser().resolve()
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"audio not found: {src}")
    mime, fmt = detect_audio_format(src)
    return p.read_bytes(), mime, fmt


# ---------- content build (chat mode) ----------------------------------------


def build_messages_audio(prompt: str, audio_b64: str, fmt: str) -> list[dict]:
    """OpenAI gpt-4o-audio style: input_audio with base64 data + format token."""
    return [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "input_audio",
                    "input_audio": {"data": audio_b64, "format": fmt},
                },
            ],
        }
    ]


# ---------- chat call --------------------------------------------------------


def call_chat(
    provider: dict, defaults: dict, messages: list[dict]
) -> tuple[dict | None, dict]:
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

    timeout = int(provider.get("timeout_seconds") or 120)
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


def extract_chat_text(payload: dict) -> str:
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


# ---------- asr call (multipart) ---------------------------------------------


def call_asr(
    provider: dict,
    defaults: dict,
    audio_bytes: bytes,
    filename: str,
    language: str | None,
) -> tuple[dict | None, dict]:
    key, src = resolve_api_key(provider)
    if not key:
        return None, {"ok": False, "error": f"no api key for {provider.get('name')}"}

    headers = {
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }
    if isinstance(provider.get("extra_headers"), dict):
        for k, v in provider["extra_headers"].items():
            headers[str(k)] = str(v)

    fields: dict[str, Any] = {"model": provider.get("model")}
    if language:
        fields["language"] = language
    elif defaults.get("language"):
        fields["language"] = defaults["language"]
    fields.setdefault("response_format", "json")
    if isinstance(provider.get("extra_body"), dict):
        for k, v in provider["extra_body"].items():
            fields.setdefault(k, v)

    mime = _AUDIO_MIME.get(Path(filename).suffix.lstrip(".").lower(), "audio/wav")
    timeout = int(provider.get("timeout_seconds") or 120)
    status, raw, err = http_multipart(
        provider["endpoint"],
        headers=headers,
        fields=fields,
        files=[("file", filename, audio_bytes, mime)],
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


def extract_asr_text(payload: dict) -> str:
    if isinstance(payload, dict):
        if isinstance(payload.get("text"), str):
            return payload["text"]
        if isinstance(payload.get("data"), dict) and isinstance(
            payload["data"].get("text"), str
        ):
            return payload["data"]["text"]
    return ""


# ---------- run helpers ------------------------------------------------------


def resolve_mode(provider: dict, defaults: dict, override: str | None) -> str:
    if override:
        return override
    return provider.get("mode") or defaults.get("mode") or "asr"


def _run(
    args: argparse.Namespace, prompt: str | None, forced_mode: str | None
) -> tuple[int, dict]:
    vault = resolve_vault()
    if vault is None:
        return 1, {"ok": False, "error": "vault not resolved"}
    cfg = load_provider_config(vault, CONFIG_FILE, DEFAULTS, TOOL)
    provider = select_provider(cfg, args.config)
    if provider is None:
        return 1, {"ok": False, "error": "no active provider available"}

    defaults = cfg.get("defaults", {})
    mode = resolve_mode(provider, defaults, forced_mode or getattr(args, "mode", None))

    try:
        audio_bytes, _mime, fmt = read_audio_b64(args.audio)
    except FileNotFoundError as e:
        return 1, {"ok": False, "error": str(e)}
    filename = Path(args.audio).name

    if mode == "asr":
        language = getattr(args, "language", None)
        payload, meta = call_asr(provider, defaults, audio_bytes, filename, language)
        if not meta.get("ok") or payload is None:
            meta.setdefault("provider", provider.get("name"))
            meta["mode"] = mode
            return 1, meta
        text = extract_asr_text(payload)
        return 0, {
            "ok": True,
            "text": text,
            "provider": provider.get("name"),
            "model": provider.get("model"),
            "mode": "asr",
            "usage": payload.get("usage") or {},
            "key_source": meta.get("key_source"),
        }
    # chat mode
    if prompt is None:
        return 1, {
            "ok": False,
            "error": "chat mode requires a prompt (use describe/ask)",
        }
    audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
    messages = build_messages_audio(prompt, audio_b64, fmt)
    payload, meta = call_chat(provider, defaults, messages)
    if not meta.get("ok") or payload is None:
        meta.setdefault("provider", provider.get("name"))
        meta["mode"] = mode
        return 1, meta
    text = extract_chat_text(payload)
    return 0, {
        "ok": True,
        "text": text,
        "provider": provider.get("name"),
        "model": provider.get("model"),
        "mode": "chat",
        "usage": payload.get("usage") or {},
        "key_source": meta.get("key_source"),
    }


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


def cmd_transcribe(args: argparse.Namespace) -> int:
    code, out = _run(args, prompt=None, forced_mode="asr")
    print(json.dumps(out, ensure_ascii=False))
    return code


def cmd_describe(args: argparse.Namespace) -> int:
    prompt = args.prompt or "请概述这段音频的核心内容、说话人语气与关键信息。"
    code, out = _run(args, prompt=prompt, forced_mode="chat")
    print(json.dumps(out, ensure_ascii=False))
    return code


def cmd_ask(args: argparse.Namespace) -> int:
    code, out = _run(args, prompt=args.question, forced_mode="chat")
    print(json.dumps(out, ensure_ascii=False))
    return code


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
        prog="audio_understand", description="cortex audio understanding CLI"
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_probe = sub.add_parser("probe", help="health check providers")
    p_probe.add_argument("--config")
    p_probe.add_argument("--all", action="store_true")
    p_probe.set_defaults(func=cmd_probe)

    p_t = sub.add_parser("transcribe", help="transcribe audio (ASR)")
    p_t.add_argument("audio", help="local file path")
    p_t.add_argument("--config")
    p_t.add_argument("--language", help="ISO 639-1 (e.g. zh, en)")
    p_t.set_defaults(func=cmd_transcribe)

    p_d = sub.add_parser("describe", help="describe audio content (chat)")
    p_d.add_argument("audio", help="local file path")
    p_d.add_argument("--config")
    p_d.add_argument("--prompt", help="override default describe prompt")
    p_d.set_defaults(func=cmd_describe)

    p_a = sub.add_parser("ask", help="ask about audio (chat)")
    p_a.add_argument("audio", help="local file path")
    p_a.add_argument("question", help="natural-language question")
    p_a.add_argument("--config")
    p_a.set_defaults(func=cmd_ask)

    p_list = sub.add_parser("list", help="list configured providers")
    p_list.add_argument("--all", action="store_true")
    p_list.set_defaults(func=cmd_list)

    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
