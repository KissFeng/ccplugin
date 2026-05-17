# cortex-search — 多级搜索 L1-L4 详细流程

> SKILL.md 入口的四级回退 (MCP first) 详细 fallback 行为, 包含 deep mode 与 tag filter。

## L1 — `mcp__obsidian__obsidian_simple_search` (首选)

```python
mcp__obsidian__obsidian_simple_search(
    query="<关键词>",
    context_length=200,
)
```

- 直接调 Obsidian 内置 search engine, 索引 frontmatter + 正文 + tags
- 返 hits 含 path / context 段落
- 命中阈值: ≥ 1 hit 即视为成功, 综合答复并跳到 §综合答复
- 失败原因 (MCP 不可达 / Obsidian Local REST API 27123/27124 不通) → 走 L2 仍可能成功; L1/L2 都失败才走 L3

## L2 — `mcp__obsidian__obsidian_complex_search` (复杂查询)

```python
mcp__obsidian__obsidian_complex_search(
    query={
        "and": [
            {"glob": ["知识库/项目/<host>/<org>/<repo>/**/*.md", {"var": "path"}]},
            {"in": ["<keyword>", {"var": "content"}]}
        ]
    }
)
```

- JsonLogic 语法, 支持按 path / tag / frontmatter 字段过滤
- 用于: 限项目内搜 / 按 tag 找 / 按 score ≥ N 过滤

## L3 — `bash ~/.cortex/scripts/search.sh` (CLI fallback)

**仅 L1/L2 MCP 不可达时调用**。CLI 内部 6 层并行 + 拆词回退 (实现 `scripts/cli/search.py`):

```bash
bash ~/.cortex/scripts/search.sh --query "<keyword>" [--scope <all|concepts|domains|log>] [--limit N]
```

### 内部并行 6 层 (所有层独立跑, 结果合并 + dedupe + 按 score 排序)

| 层 | 来源 | 实现 | 备注 |
|---|---|---|---|
| 1 | **Omnisearch HTTP** | `GET <base>/search/omnisearch?query=` | 若装 omnisearch 插件; BM25-like, 基础分 2.0 |
| 2 | **Obsidian Local REST API** | `POST <base>/search/simple/?query=` | 凭据 `<vault>/.obsidian/plugins/obsidian-local-rest-api/data.json` (apiKey + insecurePort/port); Obsidian 内置索引; 基础分 1.5 |
| 3 | hot.md grep | 本地文件扫 | 最近 10 条快速命中 |
| 4 | index.md grep | 本地文件扫 | 长存条目 |
| 5 | Smart Connections REST | `POST {CORTEX_SC_URL}/search` | 语义搜索 (若装 SC 插件) |
| 6 | ripgrep | `rg --json` cap 50 | 全 vault 兜底 |

凭据自动读取: `data.json` 的 `apiKey` + `insecurePort` (default 27123, http) 或 `port` (default 27124, https + 自签证书跳过验证)。无凭据 → HTTP 层静默跳, 走本地 grep + rg。

### 拆词回退 (phase 2)

完整 query 6 层全空 → tokenize (按空白/逗号/中文标点拆 + 停用词过滤, zh ≥ 2 字 / en ≥ 3 字) → 每 token 跑一次 6 层, 结果 score × 0.6 衰减后合并。目标: **尽可能不返回空**。

```bash
# 输出: 结构化 JSON (stdout), schema:
# [{path, title, snippet, score, source, sources: [str]}, ...]
# - score 高者排前; source 单值兼容; sources 列所有命中来源
# - phase 2 命中: sources 末尾含 "split:<token>" 标记
```

## L4 — `ripgrep` (最后兜底)

L3 也失败时调用. AI 直接跑:

```bash
rg --type md -n -C 2 --max-count 5 -i "<pattern>" "$VAULT/知识库/" \
   --glob '!_meta/**' --glob '!_templates/**' --glob '!.obsidian/**'
```

- 仅关键词正则匹配, 无语义
- 关键词转 OR 正则 (`a|b|c`)

### 解析 vault

```bash
VAULT="$(bash ~/.claude/plugins/marketplaces/ccplugin-market/plugins/tools/cortex/scripts/hooks/_lib/resolve_vault.sh)"
```

L3/L4 需要 VAULT 路径; L1/L2 走 MCP 不需要 (Obsidian 自管 vault)。

## Deep Mode

触发条件: 用户输入含 "深度搜索" / "--deep" / `depth=deep` / 复杂多轮研究场景。

```
bash ~/.cortex/scripts/deep_search.sh --query "<q>" --mode hybrid --iter-max 3 --limit 15
```

三种 mode:

- `iterative` — 多轮 hit-reflect-rehit, 适合"逐步收敛复杂主题"
- `subgraph` — backlink/forward 邻居展开, 适合"找与某概念图相邻的页"
- `hybrid` (默认) — SC + rg + BM25 重排, 适合"一次性高质量综合检索"

返回 JSON 含 `iterations`, `subgraph_expanded`, `degraded` (SC 不可达时 true)。

回退: MCP 不可达时退回 L1-L4 流程。

## Tag filter

支持 `tag:<prefix>/<value>` 语法过滤, 利用 schema tags_required 命名约定 (`_meta/frontmatter-schema.yaml`):

- `tag:domain/技术/Go` → 仅返 Go 领域笔记
- `tag:type/project` → 仅返项目 (git repo + 本地项目)
- `tag:memory/L1` → 仅返 L1 长期记忆
- `tag:project/<slug>` → 项目相关
- 多 tag AND 组合: `tag:type/project tag:host/github.com`

实现走 frontmatter.tags 数组 prefix match, 与 query 文本检索并行交集后返回。

## 不读 (硬性排除)

- `<vault>/_templates/` — 模板, 不是内容
- `<vault>/_meta/migrations/` — 操作日志, 非知识
- `<vault>/.obsidian/` — Obsidian 配置

## 错误处理

- vault 不存在 → 提示用户跑 `/cortex:install` 或配 `OBSIDIAN_VAULT`
- L1-L4 全失败 → 仍输出 "无命中" 而不是抛错
- ripgrep 缺失 → 跳过 L4, 报告但不阻断
