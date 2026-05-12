# PRD — wrapper 全 auto 模式 (claude --bare 无交互)

## 背景

用户实测 `bash ~/.cortex/scripts/lint.sh --fix`:
- skill 工作流跑到 §交互修复 段
- 打出 "请选择: BATCH_MV / WHITELIST / PER_ITEM / CANCEL" 后 claude 退出
- **没人回答**(claude --bare -p 是单轮调用, 无 stdin 反馈机制)
- 用户终端只剩半成品报告

根因: cortex-lint / cortex-refactor / cortex-ingest 等 skill 设计假设**会话内**调用 (claude session 有 AskUserQuestion 工具)。但 wrapper 跑 `claude --bare -p` 是**一次性子进程**, 无后续交互。

## 目标

所有 wrapper 跑 claude 都是 **non-interactive auto 模式**:
- prompt 显式标识 "AUTO_MODE / non-interactive"
- 各 SKILL.md 检测此标识 → 跳 AskUserQuestion → 直执行默认动作

## 范围

### 修改

- `plugins/tools/cortex/scripts/install_wrappers.sh` — 4 wrapper (ingest / search / save / refactor) + lint.sh --fix prompt 加 "AUTO_MODE" 字样
- `plugins/tools/cortex/skills/cortex-lint/SKILL.md` — §交互修复 段加 AUTO_MODE 分支 (跳询问直 BATCH_MV)
- `plugins/tools/cortex/skills/cortex-ingest/SKILL.md` — 若有交互步骤,加 AUTO_MODE 分支 (自动判源类型, 直 ingest)
- `plugins/tools/cortex/skills/cortex-save/SKILL.md` — auto 模式跳确认直落
- `plugins/tools/cortex/skills/cortex-refactor/SKILL.md` — auto 模式: 默认 dry-run, --apply 才落

### 不在范围

- 不动 cortex-doctor (本就 read-only, 无交互)
- 不动 cortex-search (本就 read-only)
- 不动 mcp/ / hooks/ / install.sh / P0-P6

## 详细规范

### 1. wrapper prompt 加 AUTO_MODE 标识

所有 wrapper prompt **首行** 加:

```
[AUTO_MODE: non-interactive shell wrapper. 不要用 AskUserQuestion, 直接执行默认动作.]
```

举例 lint.sh --fix prompt:

```
[AUTO_MODE: non-interactive shell wrapper. 不要用 AskUserQuestion, 直接执行默认动作.]
对 cortex vault 跑 lint 并修复. 默认行为 (无询问):
- vault-structure-violation: 批量 mv 到 backup_root (BATCH_MV)
- rules.json autofix=true 项: 直接落盘
- 其它非 autofix 项: 列入报告但不动
```

举例 refactor.sh:

```
[AUTO_MODE: non-interactive shell wrapper. 不要用 AskUserQuestion.]
执行 cortex-refactor 子命令: $*. 
默认 dry-run, 仅当 args 含 --apply 才落盘. 无 --apply 时输出 plan JSON.
```

### 2. SKILL.md AUTO_MODE 分支

cortex-lint/SKILL.md §交互修复 段开头加:

```markdown
## 交互修复 (--fix 模式)

**AUTO_MODE 探测**: 若 user prompt 含 `[AUTO_MODE:` 或 `non-interactive`, 跳所有 AskUserQuestion,
直执行**默认动作**:
- structure_purge: BATCH_MV (批量 mv 到 backup_root)
- autofix=true 项: 直接落
- 其它: 列入报告输出

**Interactive 模式** (claude session 内 / 用户直跑 /cortex:cortex-lint): 走下述 AskUserQuestion 4 选项流程.

### Interactive (4 选项)
... (原有流程保留)
```

cortex-refactor / cortex-ingest / cortex-save 同模式: 检测 AUTO_MODE → 跳交互直执行默认。

### 3. 具体 wrapper prompt 改

```bash
# lint.sh (--fix 分支)
"[AUTO_MODE: non-interactive shell wrapper. 不要用 AskUserQuestion.]
对 cortex vault 跑 lint --fix. 自动执行: structure_purge → BATCH_MV (mv 到 backup_root);
autofix=true 项 → 直接落; 其它 → 列入报告输出. \$*"

# ingest.sh
"[AUTO_MODE: non-interactive shell wrapper. 不要用 AskUserQuestion.]
摄取以下源: \$* (自动判 url/file/git/dir, 直接 ingest 不询问). 按 cortex-ingest 流程
url_security → fetch/read → html_sanitize → masking → save (kind=log)."

# search.sh (本就 read-only, 加标识防过度交互)
"[AUTO_MODE: non-interactive shell wrapper.]
在 vault 搜索: \$*. 多级回退 (hot → index → SC → rg → MCP). 输出引用页 + 片段."

# save.sh
"[AUTO_MODE: non-interactive shell wrapper. 不要用 AskUserQuestion.]
落档到 vault: kind=\$KIND, title=\$TITLE. body 经 masking 后直接写盘, 不询问.

body:
\$BODY"

# refactor.sh
"[AUTO_MODE: non-interactive shell wrapper. 不要用 AskUserQuestion.]
执行 cortex-refactor 子命令: \$*. 默认 dry-run; 仅 args 含 --apply 才落. dry-run 输出 plan JSON."

# doctor.sh (本就 read-only, 加标识)
"[AUTO_MODE: non-interactive shell wrapper.]
运行 cortex 健康检查 (cortex-doctor skill). 报告 vault/config/links/dead-links 等问题, 输出可读结果. \$@"
```

## 验收

1. `bash ~/.cortex/scripts/lint.sh --fix` → claude 直接执行 BATCH_MV (mv 29 项到 backup), 不打 "请选择" 列表
2. `bash ~/.cortex/scripts/refactor.sh dedupe --threshold 0.85` → dry-run plan 输出, 不询问
3. `bash ~/.cortex/scripts/refactor.sh dedupe --threshold 0.85 --apply` → 落盘 (apply 是 args 显式)
4. `bash ~/.cortex/scripts/ingest.sh https://example.com` → 直接 ingest 不询问
5. `echo "x" | ~/.cortex/scripts/save.sh log "test"` → 直接落盘
6. claude session 内 `/cortex:cortex-lint --fix` (非 wrapper) → 仍走 interactive 4 选项 (向后兼容)
7. `bash -n install_wrappers.sh` 语法绿
8. tests/bash/test_install_wrappers.sh 加用例验证 wrapper prompt 含 "AUTO_MODE"
9. P0-P6 + Phase A 不回归

## 不变量

- AUTO_MODE 标识在 prompt **首行**, SKILL 探测 regex `\[AUTO_MODE:` 或 `non-interactive`
- interactive 模式 (claude session 内) 行为完全不变
- 默认动作明示 (BATCH_MV / dry-run / 直落)
- 不破坏现有 wrapper API
- bash 3.2 兼容

## 风险

- **AUTO 直 BATCH_MV 大量 mv**: 用户 vault 可能 29 项 mv 致 backup_root 巨大. **缓解**: backup 可恢复, mv 行为符合 "auto 期望"
- **SKILL 未检测 AUTO_MODE 标识**: 部分 SKILL 可能漏改, 仍调 AskUserQuestion. **缓解**: 全 4 SKILL 一致改, test 验证
- **AUTO 模式 vs CORTEX_DRY_RUN env**: 互不冲突 (env 是 cron run.sh 的 dry-run flag, prompt AUTO_MODE 是 skill 行为)
