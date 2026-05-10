---
name: cortex-session
description: 列 sessions/<cli>/<YYYY-MM>/ 备份, 解析 transcript, 重放摘要。Triggers on "list sessions", "session 备份".
allowed-tools: Bash Read Glob mcp__obsidian__obsidian_list_files_in_dir mcp__obsidian__obsidian_get_file_contents
---

# cortex-session

操作 vault 内的 session transcript 备份。

## 触发场景

- 用户问"上周哪些会话动了 auth 模块" → 列 sessions/, 找含关键词的 transcript
- 跨 CLI 审计 — 同一 vault 收 claude-code / codex / copilot 多源 session 备份
- 重放某次 session 摘要 (不依赖 ~/.claude/projects/ 原 jsonl, vault 自带副本即可)

## 子命令

| 子命令 | 行为 |
|--------|------|
| `cortex-session list [--cli <name>] [--month YYYY-MM]` | 列备份, 默认全部 cli, 默认本月 |
| `cortex-session show <path>` | 打印 transcript 关键摘要 (user prompt + assistant text + 文件引用) |
| `cortex-session search <query>` | grep transcript 内容, 返回 file:line + 上下文 |
| `cortex-session size` | 统计各 cli/月份占用, 提示是否需清理 |

## 数据布局

```
<vault>/sessions/
├── claude-code/
│   └── 2026-05/
│       ├── 11-1430-<slug>.jsonl       # 原始 transcript
│       └── 11-1430-<slug>.tar.gz      # 可选打包
├── codex/                # 未来扩展
└── copilot/
```

## 启用 / 禁用 transcript 备份

仅当 `_meta/version.json:.preserve_transcript == true` 时, Stop / SubagentStop / PostCompact hook 才复制原始 transcript 到 sessions/。默认 `false` (省盘)。

```bash
# 启用
cortex-locale 不能改这个; 直接编辑 _meta/version.json:
{"preset":"lyt","lang":"zh-CN","preserve_transcript":true,"created":"..."}
```

## 关键约束

1. **不写 transcript** — 本 skill 仅读 / 检索, 备份由 hook 自动处理。
2. **大小敏感** — 原始 transcript 易膨胀, 用户应自行轮转 (e.g. `cortex-refactor` 删旧月)。
3. **frontmatter 提炼版** — 提炼后笔记仍走 `log/`, 通过 `cli`/`cli_session` 字段反查原 transcript。

## 输出示例

```text
$ cortex-session list --cli claude-code --month 2026-05
2026-05 (claude-code) — 12 sessions, 4.2 MB
  11-1430 debug-auth-middleware.jsonl   (2.1k lines)
  11-1612 obsidian-vault-layout.jsonl   (1.8k lines)
  ...
```
