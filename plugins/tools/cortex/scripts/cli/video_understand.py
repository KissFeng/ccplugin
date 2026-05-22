#!/usr/bin/env python3
"""cortex video_understand — video understanding CLI.

Driven by `<vault>/.cortex/config/video-understand.yaml`. Two modes:
    mode=video_url  — content array uses {type:"video_url", video_url:{url:...}}
                      (zhipu glm-4v-plus, qwen-vl-max-video, gemini compat).
    mode=frames     — ffmpeg samples N frames, content array becomes multiple
                      image_url entries (openai gpt-4o, any image-only VLM).

Subcommands:
    probe   [--config NAME] [--all]
    describe <video> [--config NAME] [--prompt TEXT] [--frames N]
    ask     <video> <question> [--config NAME] [--frames N]
    extract <video> --schema PATH [--config NAME] [--frames N]
    list    [--all]

Video input: local file path OR http(s) URL. frames mode requires ffmpeg.
"""

from __future__ import annotations

import argparse
import base64
import json
import shutil
import subprocess
import sys
import tempfile
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

TOOL = "video_understand"
CONFIG_FILE = "video-understand.yaml"
DEFAULTS = {
    "random_selection": False,
    "default_provider": None,
    "max_tokens": 1024,
    "temperature": 0.3,
    "mode": "video_url",
    "frames_count": 8,
}

_VIDEO_MIME = {
    "mp4": "video/mp4",
    "mov": "video/quicktime",
    "webm": "video/webm",
    "mkv": "video/x-matroska",
    "avi": "video/x-msvideo",
}


# ---------- input ------------------------------------------------------------


def to_video_url(src: str) -> str:
    if src.startswith(("http://", "https://", "data:")):
        return src
    p = Path(src).expanduser().resolve()
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"video not found: {src}")
    mime = _VIDEO_MIME.get(p.suffix.lstrip(".").lower(), "video/mp4")
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def to_image_data_url(frame: Path) -> str:
    b64 = base64.b64encode(frame.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def ffprobe_duration(video: Path) -> float:
    """Return duration seconds via ffprobe; 0.0 on failure."""
    if not shutil.which("ffprobe"):
        return 0.0
    try:
        out = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(video),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        return float(out.stdout.strip() or 0.0)
    except (subprocess.CalledProcessError, ValueError, subprocess.TimeoutExpired):
        return 0.0


def extract_frames(video: Path, count: int, tmp_dir: Path) -> list[Path]:
    """Sample `count` frames evenly. Raises RuntimeError if ffmpeg missing/fails."""
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found in PATH — required for frames mode")
    duration = ffprobe_duration(video)
    if duration <= 0:
        raise RuntimeError(f"ffprobe could not read duration of {video}")
    if count < 1:
        count = 1
    interval = duration / count
    frames: list[Path] = []
    for i in range(count):
        ts = interval * (i + 0.5)
        out = tmp_dir / f"frame_{i:03d}.jpg"
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    f"{ts:.3f}",
                    "-i",
                    str(video),
                    "-vframes",
                    "1",
                    "-q:v",
                    "3",
                    str(out),
                ],
                capture_output=True,
                timeout=60,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"ffmpeg failed at t={ts:.2f}s: {e.stderr.decode('utf-8', 'replace')[:200]}"
            )
        if out.exists():
            frames.append(out)
    if not frames:
        raise RuntimeError("ffmpeg extracted 0 frames")
    return frames


# ---------- content build ----------------------------------------------------


def build_messages_video_url(prompt: str, video_url: str) -> list[dict]:
    return [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "video_url", "video_url": {"url": video_url}},
            ],
        }
    ]


def build_messages_frames(prompt: str, frames: list[Path]) -> list[dict]:
    content: list[dict] = [{"type": "text", "text": prompt}]
    for f in frames:
        content.append(
            {"type": "image_url", "image_url": {"url": to_image_data_url(f)}}
        )
    return [{"role": "user", "content": content}]


def build_extract_prompt(schema_text: str) -> str:
    return (
        "Watch the video and extract fields strictly matching the JSON schema. "
        "Output ONLY a single JSON object — no prose, no markdown fences. "
        "Use null for any field not observable.\n\n"
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


# ---------- run --------------------------------------------------------------


def resolve_mode(provider: dict, defaults: dict, override: str | None) -> str:
    if override:
        return override
    return provider.get("mode") or defaults.get("mode") or "video_url"


def resolve_frames_count(provider: dict, defaults: dict, override: int | None) -> int:
    if override and override > 0:
        return override
    n = provider.get("frames_count") or defaults.get("frames_count") or 8
    return int(n)


def _run_chat(args: argparse.Namespace, prompt: str) -> tuple[int, dict]:
    vault = resolve_vault()
    if vault is None:
        return 1, {"ok": False, "error": "vault not resolved"}
    cfg = load_provider_config(vault, CONFIG_FILE, DEFAULTS, TOOL)
    provider = select_provider(cfg, args.config)
    if provider is None:
        return 1, {"ok": False, "error": "no active provider available"}

    defaults = cfg.get("defaults", {})
    mode = resolve_mode(provider, defaults, getattr(args, "mode", None))

    tmp_dir = None
    frames_used = 0
    try:
        if mode == "frames":
            frames_count = resolve_frames_count(
                provider, defaults, getattr(args, "frames", None)
            )
            src = args.video
            if src.startswith(("http://", "https://")):
                return 1, {
                    "ok": False,
                    "error": "frames mode requires local file (URL not supported)",
                }
            video_path = Path(src).expanduser().resolve()
            if not video_path.exists():
                return 1, {"ok": False, "error": f"video not found: {src}"}
            tmp_dir = Path(tempfile.mkdtemp(prefix="cortex-video-"))
            try:
                frames = extract_frames(video_path, frames_count, tmp_dir)
            except RuntimeError as e:
                return 1, {"ok": False, "error": str(e), "mode": "frames"}
            frames_used = len(frames)
            messages = build_messages_frames(prompt, frames)
        else:
            try:
                video_url = to_video_url(args.video)
            except FileNotFoundError as e:
                return 1, {"ok": False, "error": str(e)}
            messages = build_messages_video_url(prompt, video_url)

        payload, meta = call_chat(provider, defaults, messages)
    finally:
        if tmp_dir and tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)

    if not meta.get("ok") or payload is None:
        meta.setdefault("provider", provider.get("name"))
        meta["mode"] = mode
        return 1, meta

    text = extract_text(payload)
    usage = payload.get("usage") or {}
    out: dict[str, Any] = {
        "ok": True,
        "text": text,
        "provider": provider.get("name"),
        "model": provider.get("model"),
        "mode": mode,
        "usage": usage,
        "key_source": meta.get("key_source"),
    }
    if mode == "frames":
        out["frames_used"] = frames_used
    return 0, out


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


def cmd_describe(args: argparse.Namespace) -> int:
    prompt = args.prompt or "请详细总结这段视频的关键内容、场景与人物动作。"
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
    code, out = _run_chat(args, build_extract_prompt(schema_text))
    if code != 0:
        print(json.dumps(out, ensure_ascii=False))
        return code
    raw_text = out.get("text", "")
    cleaned = strip_json_fence(raw_text)
    try:
        out["data"] = json.loads(cleaned)
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


def _add_chat_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--config", help="provider name")
    p.add_argument(
        "--mode", choices=["video_url", "frames"], help="override provider mode"
    )
    p.add_argument("--frames", type=int, help="frames count (frames mode)")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="video_understand", description="cortex video understanding CLI"
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_probe = sub.add_parser("probe", help="health check providers")
    p_probe.add_argument("--config")
    p_probe.add_argument("--all", action="store_true")
    p_probe.set_defaults(func=cmd_probe)

    p_desc = sub.add_parser("describe", help="describe a video")
    p_desc.add_argument("video", help="local path or http(s) URL")
    p_desc.add_argument("--prompt", help="override default describe prompt")
    _add_chat_args(p_desc)
    p_desc.set_defaults(func=cmd_describe)

    p_ask = sub.add_parser("ask", help="ask about a video")
    p_ask.add_argument("video", help="local path or http(s) URL")
    p_ask.add_argument("question", help="natural-language question")
    _add_chat_args(p_ask)
    p_ask.set_defaults(func=cmd_ask)

    p_ext = sub.add_parser("extract", help="extract structured fields")
    p_ext.add_argument("video", help="local path or http(s) URL")
    p_ext.add_argument("--schema", required=True, help="JSON schema file path")
    _add_chat_args(p_ext)
    p_ext.set_defaults(func=cmd_extract)

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
