# PRD — Cortex P5 Vault Git Sync (Opt-In Auto-Commit)

## 背景

cortex vault 是用户的知识库,跨机使用刚需。当前无任何 sync 机制,用户手动 `git commit` + `git push`。kioku 有 `lib/git-history.mjs` + `lib/wiki-snapshot.mjs`,Stop 后自动 commit。

P5 落 **opt-in** auto-commit:vault 是 git repo 且 `_meta/version.json:.auto_commit=true` 时,Stop hook 末尾跑 `git add -A && git commit -m "auto: <date>"`。push 严格 opt-in (`.auto_push=true`),默认关。

## 目标

`hooks/_lib/git_sync.py` 新模块 + Stop hook 集成 + `_meta/version.json` 字段 + `cortex-install` 交互问询 + docs/sync-git.md 使用指南。

## 范围

### 新增文件

- `plugins/tools/cortex/hooks/_lib/git_sync.py` — 核心模块
- `plugins/tools/cortex/tests/python/test_git_sync.py`
- `plugins/tools/cortex/docs/sync-git.md` — 跨机指南

### 修改文件

- `plugins/tools/cortex/hooks/stop.sh` — 末尾调 `python3 ${PLUGIN_ROOT}/hooks/_lib/git_sync.py auto` (异步,不阻塞返回)
- `plugins/tools/cortex/skills/cortex-install/SKILL.md` — 安装末尾问询 auto_commit + auto_push
- `plugins/tools/cortex/AGENT.md` — 加 §Git Sync (P5) 段
- `plugins/tools/cortex/templates/vault/_meta/version.json` — 加 default `auto_commit: false`、`auto_push: false`(若模板文件存在)

### 不在范围

- 不引 PyGit2/dulwich,纯 `subprocess.run(["git", ...])`
- 不实现 rebase/merge 冲突解决
- 不动 push 行为(默认关,即使开也只 push,不 pull)
- 不动 P0-P4 已交付代码

## 详细规范

### 1. `hooks/_lib/git_sync.py`

```python
"""Vault git auto-sync — opt-in via _meta/version.json."""
from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

def read_vault_config(vault: Path) -> dict:
    """读 _meta/version.json. 缺则返 {}."""

def is_git_repo(vault: Path) -> bool:
    """vault/.git 存在 + git rev-parse 成功."""

def is_auto_commit_enabled(vault: Path) -> bool:
    """config.get('auto_commit', False) is True."""

def is_auto_push_enabled(vault: Path) -> bool:
    """config.get('auto_push', False) is True."""

def has_changes(vault: Path) -> bool:
    """git status --porcelain 非空."""

def auto_commit(vault: Path, message: Optional[str] = None) -> tuple[bool, str]:
    """
    返回 (ok, info).
    流程:
      1. is_git_repo 检测
      2. is_auto_commit_enabled 检测
      3. has_changes 检测 (无改动直接 OK 返 'no changes')
      4. git add -A
      5. git commit -m "<message or auto: YYYY-MM-DD HH:MM>"
      6. 若 is_auto_push_enabled, git push origin HEAD (timeout 30s)
    任何一步 git 调用失败,捕获 stderr, 返 (False, stderr).
    """

def main(argv: list[str]) -> int:
    """CLI: `git_sync.py auto` 或 `git_sync.py status`."""
```

约束:
- `subprocess.run([...], cwd=vault, timeout=30, capture_output=True, text=True)`,**禁** `shell=True`
- 所有 git 调用 timeout(commit 10s, push 30s)
- commit message 默认 `auto: YYYY-MM-DD HH:MM` (UTC),env `CORTEX_GIT_MESSAGE` 可覆盖
- push 失败不抛(网络问题),log 后返 (False, stderr)
- 任何异常 fail-soft 返 (False, repr(e)),**不阻塞 Stop hook**

### 2. `hooks/stop.sh` 集成

现有 `stop.sh` 末尾追加(异步,不影响返回):

```bash
# P5: vault auto-commit (opt-in)
if [ -n "${CORTEX_VAULT_PATH:-}" ]; then
  (
    python3 "${PLUGIN_ROOT}/hooks/_lib/git_sync.py" auto \
      "${CORTEX_VAULT_PATH}" 2>&1 \
      | logger -t cortex-git-sync
  ) &
fi
```

注意:Stop hook 本身 `async: true`(已设 plugin.json),里面再开 `&` 进一步隔离,防 git push 阻塞 30s。

### 3. `_meta/version.json` schema 扩展

```json
{
  "version": "0.x.y",
  "lang": "zh-CN",
  "vault_path": "/Users/x/Documents/vault",
  "preset": "lyt",
  "auto_commit": false,
  "auto_push": false
}
```

`cortex-install` skill 安装步骤末尾用 `AskUserQuestion`(用户硬规则:禁文本提问) 询问:

- "vault 是 git repo?启用 Stop hook 自动 commit?" [no / yes-commit-only / yes-commit-and-push]

### 4. `cortex-install/SKILL.md` 改动

在现有"安装完成"段前加:

```markdown
## 询问 git auto-sync (P5)

若 vault 是 git repo, 用 AskUserQuestion 询问:
- "启用 Stop hook 自动 git commit?" [关 / 仅 commit / commit + push]
- 写入 _meta/version.json:
  - 关 → auto_commit=false, auto_push=false
  - 仅 commit → auto_commit=true, auto_push=false
  - commit + push → auto_commit=true, auto_push=true
```

### 5. `docs/sync-git.md`

```markdown
# Cortex Vault Git Sync

## 模式

1. **手动**(默认): 用户自己 `git commit / push / pull`
2. **auto_commit**: Stop hook 触发 `git add -A && git commit -m 'auto: <date>'`
3. **auto_push**: 在 auto_commit 之上, 后追加 `git push origin HEAD`

## 启用

编辑 `<vault>/_meta/version.json`:
```json
{ "auto_commit": true, "auto_push": false }
```

或重跑 cortex-install 触发交互问询.

## 多机协同

- 推荐 GitHub/GitLab 私库托管
- 主机 A: auto_commit + auto_push
- 主机 B: 手动 `git pull` 后启动 claude (cortex 不自动 pull)
- 冲突: 用户 `git mergetool` 手动解, cortex 不介入

## 排错

- "vault 不是 git repo": Stop hook 静默跳过, 无副作用
- "push 失败 (网络/auth)": Stop hook 记 log, commit 已落本地, 下次重试
- "commit 失败": 检查 `git status` 与 hook 权限

## 风险

- secret 落 git: P0 masking 已在 ingest/save 写盘前过滤, 但 vault 内已有手动笔记可能含 secret. 启用 auto_push 前用户须自查.
```

### 6. `AGENT.md` §Git Sync (P5)

```markdown
## Git Sync (P5)

vault 是 git repo 时, Stop hook 可选触发 auto-commit:

| 模式 | 配置 | 行为 |
|------|------|------|
| 手动 | `auto_commit=false` (默认) | 无副作用 |
| 仅 commit | `auto_commit=true, auto_push=false` | Stop 后 git add -A + commit |
| commit + push | `auto_commit=true, auto_push=true` | 上述 + git push origin HEAD (30s timeout) |

注意:
- P0 masking 不能保证手写笔记中的 secret, 启 auto_push 前自查 vault
- push 失败不阻塞 hook, 本地 commit 已落
- cortex 不自动 pull, 多机协同靠用户手动 git pull

详见 docs/sync-git.md.
```

## 验收标准

1. `pytest plugins/tools/cortex/tests/python/test_git_sync.py` 全绿:
   - 非 git repo → `auto_commit` 返 (True, "not a git repo, skipped")
   - 未启用 auto_commit → 返 (True, "auto_commit disabled, skipped")
   - 无改动 → 返 (True, "no changes")
   - 有改动 + 启用 → git status 后 commit hash 存在
   - push 启用但远程不可达 → 返 (False, ...) 不抛
   - subprocess timeout → 返 (False, "timeout")
2. `bash -n plugins/tools/cortex/hooks/stop.sh` 语法绿
3. stop.sh 集成段在文件末尾,不影响原 hook 主体逻辑
4. `_meta/version.json` 加字段后 cortex-install 验证 JSON 合法
5. `docs/sync-git.md` 存在,内容覆盖 3 模式 + 启用步骤 + 多机 + 排错
6. AGENT.md §Git Sync (P5) 段存在
7. P0-P4 不回归:`bash plugins/tools/cortex/tests/run.sh` 全绿

## 不变量

- 纯 stdlib + subprocess git 调用,**禁** PyGit2/dulwich/gitpython
- 默认 `auto_commit=false` (opt-in 严格)
- push 行为完全 opt-in,即使 auto_commit=true 也不 push 除非 auto_push=true
- 所有 git 调用 timeout,subprocess **禁 shell=True**
- fail-soft:任何异常不阻塞 Stop hook

## 风险

- **secret 落 git push**:auto_push=true + vault 手写笔记含 secret = 公开仓泄漏。**缓解**:docs 警告 + 后续 P5.5 加 pre-commit hook 跑 masking 扫
- **git lock 冲突**:用户手动 `git commit` 与 hook 撞。**缓解**:`git add -A` 失败时 fail-soft,下次 hook 重试
- **commit storm**:每次 Stop 都 commit,journal 爆。**缓解**:`git diff --quiet` 优先,无改动跳过(`has_changes` 检测)
- **timezone 漂移**:commit message 用 UTC 还是 local?**决定**:UTC,跨机一致
- **大 vault git operation 慢**:5000+ 笔记 `git add -A` 秒级。**缓解**:Stop hook 已 async + 内部再 `&`
