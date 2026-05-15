# cortex-save — 写入流程

## P0 masking 前置

写盘前必经 `masking.py` 脱敏 (AWS/OpenAI/Anthropic/GitHub PAT/JWT/PEM/Slack token → `<REDACTED:*>`)。`save_session.py` 已内置, 手写 body 时先:

```bash
SAFE_BODY="$(python3 ~/.claude/plugins/marketplaces/ccplugin-market/plugins/tools/cortex/scripts/hooks/_lib/masking.py <<< "$BODY")"
```

绕过 (仅测试): `CORTEX_SKIP_SANITIZE=1`, 生产禁用。

## 写入工具链

1. **L1 优先**: `mcp__obsidian__obsidian_put_content` / `obsidian_append_content`
2. **L2 fallback**: 官方 obsidian CLI
3. **L3 兜底**: 直接 `Write`
4. **检 obsidian-git**: `<vault>/.obsidian/plugins/obsidian-git/data.json` 存在 → **不**自动 git commit, 文件末尾加注释 `<!-- cortex-pending-commit -->`

## block-id 自动注入

- 每个 H2 / H3 段落末尾追加 ` ^cortex-<sha8>`
- `sha8 = sha256(<rel-path>::<UTC-iso>::<section-index>::<heading>)[:8]`
- 冲突 → seed 加序号重哈希; 检查 `<vault>/知识库/日记/日/` 已有 `^cortex-` 防重复

## 更新索引

- `<vault>/index.md` — type 章节加新条目 (无则创建章节)
- `<vault>/hot.md` — `## 最近落档` 段顶部插入新 wikilink, 保留前 5 条
- `<vault>/log/_index.md` — log 类型必同步

## 反向 wikilink 回填

```bash
python3 ~/.claude/plugins/marketplaces/ccplugin-market/plugins/tools/cortex/scripts/hooks/_lib/backlink_sync.py \
  --vault "$VAULT" --source "<rel-path>"
```

- JSON stdout: `{updated: [...], skipped: [...], missing: [...]}`
- `updated` — 已在目标页 `## Backlinks` 追加 `- [[<new-page>]] (cortex-auto)`
- `skipped` — 已含同源 backlink, 幂等跳过
- `missing` — wikilink 指向不存在页 (lint rule #3 另行报 dead link)
- 失败仅日志, 不阻断 (退出码恒 0)
- save_session.py 写入后自动调用 backlink_sync.py, skill 手写时无需重复

## save_session.py 快捷调用 (--from-session)

```bash
python3 ~/.claude/plugins/marketplaces/ccplugin-market/plugins/tools/cortex/scripts/hooks/_lib/save_session.py \
  --vault "$VAULT" \
  --transcript "$CLAUDE_TRANSCRIPT_PATH" \
  --reason manual \
  --force \
  --title "用户给的标题"
```

stdout 即落档绝对路径; 退出码 0=成功, 1=失败, 2=未触发 (force 模式不会出现)。

## 输出范例

```
✅ 落档成功
路径: /Users/x/knowledge/log/2026-05/10-1432-cortex-stop-hook.md
相对: log/2026-05/10-1432-cortex-stop-hook (vault 内)
URI: obsidian://open?vault=knowledge&file=log%2F2026-05%2F10-1432-cortex-stop-hook
backlinks 回填: 2 处 ([[obsidian-hooks]] / [[claude-code-plugin]])
未命中 wikilink: 1 (留待 cortex-lint)
注: 检测到 obsidian-git, 已加 cortex-pending-commit 标记, 不主动 git commit
```
