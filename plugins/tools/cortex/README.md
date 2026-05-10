# Cortex

> Obsidian 知识库协作插件 — 让 Claude 在每个会话中以结构化、可观测、可演进的方式读写你的 vault。

## 能力速览

| 形态 | 内容 |
|------|------|
| Hooks | `SessionStart` 注入"先搜库"协作约定 + hot 摘要; `Stop` 自动归档非平凡技术发现 |
| Commands | `/cortex:install` `/cortex:new` `/cortex:search` `/cortex:save` `/cortex:lint` `/cortex:refactor` `/cortex:doctor` `/cortex:cron` `/cortex:canvas` `/cortex:dashboard` `/cortex:fold` `/cortex:uri` |
| Skills | `cortex-setup` `cortex-save` `cortex-query` `cortex-ingest` `cortex-lint` (+ v2 `cortex-bases` `cortex-canvas` `cortex-fold`) |
| Presets | LYT (默认) / Zettelkasten / PARA / blank |
| 模板 | concept · entity · domain · dashboard · question · source — 用 Obsidian callout + properties + Bases |

## 安装

通过 ccplugin marketplace:

```bash
# (待实现) /plugin install cortex
```

## 配置

vault 路径解析顺序:

1. `$OBSIDIAN_VAULT` 环境变量
2. `$XDG_CONFIG_HOME/cortex/config.json` 中 `.vault` 字段
3. `~/.config/cortex/config.json` 中 `.vault` 字段
4. 默认 `~/persons/knowledge/obsidian`
5. auto-detect: 扫 `~/Documents` 与 `~/Library` 找唯一 `.obsidian/` 目录

任意一项命中即停止。

## 5 分钟上手

```bash
# 1. 初始化 vault (LYT 默认)
/cortex:install

# 2. 诊断
/cortex:doctor

# 3. 新建概念页
/cortex:new concept "事件驱动架构"

# 4. 搜知识库
/cortex:search "auth middleware"

# 5. 收尾时自动落档 (Stop hook 触发, 也可手动)
/cortex:save
```

## 设计哲学

详见 `.trellis/tasks/05-10-obsidian-kb-plugin/prd.md`。

- **不依赖 `lib/`** — 自包含, 纯 bash + python stdlib
- **MCP 主, CLI 兜底** — `mcp__obsidian__*` 覆盖 95% CRUD; canvas/bases 才回退 `obsidian` CLI
- **callout 替代 HTML grid** — Obsidian + GitHub 双渲染兼容
- **Hook v2 wrapped JSON schema** — `hookSpecificOutput.{hookEventName,additionalContext}`
- **不写 noop hook** — 教训自 commit `07e713d4`

## License

AGPL-3.0-or-later
