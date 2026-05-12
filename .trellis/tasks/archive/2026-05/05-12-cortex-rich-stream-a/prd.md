# PRD — Cortex Phase A: stream parser rich 化

## 背景

当前 `scripts/lib/stream_progress.sh` 用 jq filter + 心跳后台进程 + bash ANSI codes 实现 wrapper 进度可见。jq filter 内嵌 ANSI 字面量难维护,心跳与 stream 输出交错偶有视觉撕裂,无法表达多行结构 (tool input JSON 折叠 / markdown text 高亮 / progress bar)。

`rich` 是 Python 富文本 lib,提供 `Live` / `Spinner` / `Panel` / `Markdown` / `Progress`,远胜 jq + ANSI 手工拼。

## 目标

`cortex_stream_runner` (bash) 改 `python3 ${PLUGIN_ROOT}/scripts/lib/cortex_stream.py --label "$LABEL" -- <claude cmd>`,所有 stream-json parse + step + 心跳 + 收尾全由 python+rich 渲染。

## 范围

### 新增

- `plugins/tools/cortex/scripts/lib/cortex_stream.py` — rich-based stream parser entry
- `plugins/tools/cortex/mcp/tests/test_cortex_stream.py` — 单元测试

### 修改

- `plugins/tools/cortex/scripts/lib/stream_progress.sh` — `cortex_stream_runner` body 改为 exec python3 cortex_stream.py
- `plugins/tools/cortex/mcp/pyproject.toml` — 加 `rich>=13.0,<15.0` 依赖

### 不在范围

- 不动 hook .sh (协议层)
- 不动 P0-P5 模块
- 不动 install.sh 主流程 (pipx install --force 自然带 rich)
- 不动 run.sh tty 检测分支 (上层逻辑已稳)
- Phase B/C (cortex CLI / install.sh rich 化) 留独立 task

## 详细规范

### 1. cortex_stream.py 入口

CLI 签名:

```bash
python3 cortex_stream.py --label cortex-doctor -- <full claude command>
```

`--` 后是要包装跑的命令 (含 `claude --bare -p --append-system-prompt ...`)。脚本自动注入 `--output-format stream-json --verbose`。

行为:
1. fork subprocess: claude + 流式 stdout (line-buffered)
2. rich Live 区域显示: spinner + step + tool calls 历史 (压缩后) + 心跳 elapsed
3. 解析每行 NDJSON:
   - `assistant.message.content[].type=="text"` → 增量打 rich Markdown 段
   - `assistant.message.content[].type=="tool_use"` → Panel(input[:120], title=f"tool: {name}", style="yellow")
   - `result.is_error==true` → 红 Panel
   - `result.is_error==false` → 绿 `[OK] done`
4. 心跳: rich Spinner + `elapsed Ns`,合入 Live 而非单独 print
5. claude 退出: stop Live,打最终 `[label] OK` / `[label] FAILED: exit code N`
6. 透传 stdout NDJSON 到 stdout (供 run.sh 后续 jq result-line 提取); 若 `CORTEX_STREAM_TEE_FILE` 设, tee 到该文件

### 2. 关键代码骨架

```python
#!/usr/bin/env python3
"""cortex_stream — rich-rendered wrapper for claude stream-json."""
from __future__ import annotations
import argparse, json, os, subprocess, sys, time
from pathlib import Path

from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.console import Group


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--label", default="cortex")
    p.add_argument("cmd", nargs=argparse.REMAINDER)
    return p.parse_args()


def main():
    args = parse_args()
    cmd = args.cmd
    # strip leading `--` separator if present
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        print("cortex_stream: missing command", file=sys.stderr)
        return 4

    label = args.label
    tee_file = os.environ.get("CORTEX_STREAM_TEE_FILE")

    # inject stream-json + verbose
    cmd = list(cmd) + ["--output-format", "stream-json", "--verbose"]

    err_console = Console(file=sys.stderr, force_terminal=sys.stderr.isatty())

    # step 1
    err_console.print(f"[bold cyan][{label}][/] step 1/2: 启动 claude (stream-json 模式)")
    err_console.print(f"[bold cyan][{label}][/] step 2/2: 等待 claude 输出...")

    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1,
    )

    start = time.monotonic()
    tee_fp = open(tee_file, "w") if tee_file else None
    history: list = []  # 最近 5 个 tool/text 摘要

    def render():
        elapsed = int(time.monotonic() - start)
        spinner = Spinner("dots", text=f"[dim]still working... ({elapsed}s elapsed)[/]")
        items = history[-5:]  # rolling
        body = Group(*items, spinner) if items else spinner
        return body

    with Live(render(), console=err_console, refresh_per_second=4, transient=False) as live:
        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue
            # tee raw NDJSON
            if tee_fp:
                tee_fp.write(line + "\n")
                tee_fp.flush()
            # also stdout passthrough for run.sh result-line parse
            sys.stdout.write(line + "\n")
            sys.stdout.flush()

            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue

            etype = evt.get("type")
            if etype == "assistant":
                msg = evt.get("message", {})
                for blk in msg.get("content", []):
                    btype = blk.get("type")
                    if btype == "text":
                        txt = (blk.get("text") or "").lstrip("\n")[:200]
                        if txt:
                            history.append(Text(f"[text] {txt}", style="green"))
                    elif btype == "tool_use":
                        name = blk.get("name", "?")
                        inp = json.dumps(blk.get("input", {}))[:120]
                        history.append(Panel(Text(inp, style="yellow"),
                                             title=f"tool: {name}",
                                             border_style="yellow",
                                             padding=(0, 1)))
            elif etype == "result":
                ok = not evt.get("is_error", False)
                history.append(
                    Text("[OK] done", style="bold green") if ok
                    else Text(f"[FAILED] {evt.get('result', 'unknown')[:200]}",
                              style="bold red")
                )

            live.update(render())

    rc = proc.wait()
    if tee_fp:
        tee_fp.close()

    if rc == 0:
        err_console.print(f"[bold green][{label}] OK[/]")
    else:
        err_console.print(f"[bold red][{label}] FAILED: exit code {rc}[/]")
    return rc


if __name__ == "__main__":
    sys.exit(main())
```

### 3. stream_progress.sh 简化

`cortex_stream_runner` 整个 body 替换为:

```bash
cortex_stream_runner() {
  local label="${CORTEX_JOB_LABEL:-cortex}"
  local stream_py="${CORTEX_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/lib/cortex_stream.py"
  if [[ ! -f "$stream_py" ]]; then
    # fallback: raw exec (no progress)
    "$@" --output-format stream-json --verbose
    return $?
  fi
  exec python3 "$stream_py" --label "$label" -- "$@"
}
```

注意:`exec` 替换当前 shell, claude 与 python 输出顺序保。如果上下文有后续 bash 操作不能 exec,改 `python3 ... "$@"` 不 exec。**实际**:`cortex_stream_runner` 被 wrapper / run.sh 调用,call site 之后可能有逻辑 (run.sh result-line parse),**不能** exec。改无 exec 版本:

```bash
cortex_stream_runner() {
  local label="${CORTEX_JOB_LABEL:-cortex}"
  local stream_py="${CORTEX_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/lib/cortex_stream.py"
  if [[ ! -f "$stream_py" ]]; then
    "$@" --output-format stream-json --verbose
    return $?
  fi
  python3 "$stream_py" --label "$label" -- "$@"
}
```

保留 `cortex_check_jq` 与 ANSI 颜色变量 (其它脚本可能复用),但 `_cortex_heartbeat` 函数及 jq filter 字符串可移除 (rich 接管心跳)。

### 4. pyproject.toml 加 rich

```toml
[project]
dependencies = [
    "mcp>=1.0.0,<2.0.0",
    "pypdf>=4.0",
    "ebooklib>=0.18",
    "python-docx>=1.1",
    "rich>=13.0,<15.0",  # ← 新
]
```

`pipx install --force plugins/tools/cortex/mcp/` 重装后 rich 进 venv。

### 5. python3 在 pipx venv 内的解析

`scripts/lib/cortex_stream.py` 用 `python3` 而非 `cortex-mcp` console-script。但 `python3` 是系统 python, 不进 pipx venv,**找不到 rich**。

解决:
- 选项 A: `cortex_stream.py` 写 shebang `#!/usr/bin/env -S python3 -S` + sys.path insert pipx venv site-packages
- 选项 B: 装 rich 到用户 site-packages: `pip install --user rich`
- 选项 C: cortex_stream.py 作 cortex-mcp 子命令暴露,wrapper 调 `cortex-mcp stream --label ...`

**推荐 C**:在 `mcp/pyproject.toml` 加新 console-script `cortex-stream = "cortex_stream:main"` (或类似)。但 cortex_stream.py 位置在 `scripts/lib/`,要么搬入 `mcp/` 作 module,要么让 pyproject.toml 包含 `scripts/lib/` 路径。

最简单:**搬** `cortex_stream.py` 到 `mcp/cortex_stream.py` (mcp package 内),`mcp/pyproject.toml` 加 entry:

```toml
[project.scripts]
cortex-mcp = "server:main"
cortex-stream = "cortex_stream:main"
```

bash 调 `cortex-stream --label "$label" -- "$@"` (pipx 已把 console-scripts 暴露在 PATH)。

stream_progress.sh:

```bash
cortex_stream_runner() {
  local label="${CORTEX_JOB_LABEL:-cortex}"
  if command -v cortex-stream >/dev/null 2>&1; then
    cortex-stream --label "$label" -- "$@"
  else
    # fallback: raw exec, log warn
    echo "[${label}] cortex-stream not in PATH (pipx install cortex-mcp), no progress UI" >&2
    "$@" --output-format stream-json --verbose
    return $?
  fi
}
```

### 6. tee 行为保留

run.sh 现有 `CORTEX_STREAM_TEE_FILE=$TMP_NDJSON` 路由,cortex_stream.py 读 env 变量,写 NDJSON 到 tee file 同时 stdout 透传。两条路径都得保。

## 验收

1. `pipx install --force plugins/tools/cortex/mcp/` 后 `which cortex-stream` 返绝对路径 (~/.local/bin/cortex-stream)
2. `bash ~/.cortex/scripts/lint.sh` 交互终端见 rich Live: spinner + 历史 5 条 (tool/text) + 心跳 elapsed,收尾 `[label] OK` / `FAILED` 高对比
3. cron 模式 (非 tty): rich 自动降级为 plain text (Console force_terminal 自动检测)
4. `CORTEX_STREAM_TEE_FILE=/tmp/foo bash -c 'cortex-stream --label test -- echo "..."'` 后 /tmp/foo 含原始 NDJSON
5. cortex-stream 不存在时 fallback: stream_progress.sh 退化为原 exec, 不崩
6. `pytest plugins/tools/cortex/mcp/tests/test_cortex_stream.py` 全绿 (覆盖 cli args / event parse / tee / fallback)
7. P0-P6 不回归: `bash plugins/tools/cortex/tests/run.sh` 全绿
8. `ruff check plugins/tools/cortex/mcp/cortex_stream.py` 全绿
9. `python3 -m py_compile mcp/cortex_stream.py` ok

## 不变量

- 纯 rich + stdlib, 禁外部 dep (除已声明的 mcp/pypdf/ebooklib/python-docx/rich)
- cron 模式 (非 tty) 行为不变 (rich auto-detect)
- stdout NDJSON 透传保留 (run.sh result-line parse 依赖)
- `CORTEX_STREAM_TEE_FILE` env 行为保留
- `cortex-stream` 不存在 → bash fallback 不阻塞
- 不破坏 stream_progress.sh 现有 `cortex_check_jq` / 颜色变量 API (其它脚本可能复用)
- python ≥ 3.10

## 风险

- **rich Live 非 tty 行为**:默认 rich Console 自动检测 isatty,非 tty 简化输出。验证 cron 模式日志干净
- **pipx venv python3 vs 系统 python3**:cortex-stream 作 console-script 由 pipx wrapper 启动,**自动**用 venv python,无 sys.path 问题
- **stream-json schema 漂移**:try/except JSONDecodeError 容错; 未知 event type 静默跳过
- **subprocess.Popen unbuffered**:`bufsize=1, text=True` 行级缓冲, claude `--verbose` 保证持续输出
- **history rolling 5 条**:可能丢早期 tool calls。**缓解**:tee_file 保完整 NDJSON, 用户可后查
- **PYTHONPATH 污染 pipx venv**:不应发生 (pipx 隔离)
