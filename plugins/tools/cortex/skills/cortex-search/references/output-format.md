# cortex-search — 综合答复输出格式

> SKILL.md 入口的输出格式规范, 含引用渲染 + confidence 标记 + 稀疏命中提示。

## 综合答复格式

- 引用源: 每条用 `[[<rel-path>]]` + 行号 (从 simple_search context 或 ripgrep `:line:`)
- 提供 `obsidian://open?vault=<name>&file=<rel>` 可点击 URI (URL-encode 路径)
- **不超过 3 段** — 简明优先, 长答让用户追问
- 标注 confidence:
  - 高 — L1/L2 MCP 命中
  - 中 — L3 hot.md / index.md / SC
  - 低 — L3 rg / L4 rg

## 标准输出模板

```markdown
基于 vault 找到 N 条相关内容 (confidence: 中):

1. **<标题>** — [[知识库/领域/foo.md]] · obsidian://open?vault=...&file=...
   <一句话摘要>

2. ...
```

## 稀疏命中提示

若 L1-L4 总命中 < 3 且查询主题"看起来值得记" (含 `decision` / `architecture` / `config` / 中文 `决策` / `架构` 等) → 提示:

> 知识库里没找到相关内容。这次讨论结束后可用 `/cortex:save` 把要点落档。

## obsidian URI 渲染

```
obsidian://open?vault=<vault-name>&file=<rel-path-url-encoded>
```

- `<vault-name>` 取 `~/.cortex/config.json:.vault` basename
- `<rel-path-url-encoded>` 走 `urllib.parse.quote(path, safe='')`
- 路径含中文 / 空格全部 percent-encode

## 不做

- 不写 vault (查询专用)
- 不跳过 L1/L2 MCP 直接调 L3 search.sh (除非 MCP 探活失败)
- 不用 qmd MCP 或其他非 obsidian MCP 替代 (qmd 索引不全 cortex vault)
