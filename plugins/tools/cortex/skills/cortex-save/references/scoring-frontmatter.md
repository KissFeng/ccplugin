# cortex-save — 评分字段 + frontmatter schema

## 评分字段 (强制 frontmatter, 落档时 AI 自评)

参考权威定义: `skills/cortex-ingest/references/extract.md §3`

### 知识库落档 (kind=concept|domain|log|reflection|source|project)

强制 4 字段, 全 0.0-10.0 浮点:

- `score`: 内容质量 (覆盖度 / 深度 / 准确性)
- `confidence`: AI 对内容的把握度
- `source_credibility`: host 白名单查表 (见 `scripts/cli/lib/remote.py:_HOST_CREDIBILITY`)
- `maturity`: `draft | review | stable | deprecated` enum

### 记忆落档 (kind=memory, 落 `记忆/L0-L4/`)

强制 2 字段:

- `importance`: 重要程度 (核心约束 = 10, 流水账 = 1-3)
- `confidence`: 可信度 (用户明确肯定 = 10, AI 推测 = 4-6, 失败 episode = 0-3)

参考: `skills/cortex-memory/references/scoring.md`

### CLI override

```bash
bash ~/.cortex/scripts/save.sh ... \
  --score=N \
  --confidence=N \
  --source-credibility=N \
  --maturity=stable
```

覆盖 AI 自评。

## Frontmatter 规范 (按目标目录)

落档前调 cortex-lint 内联 schema 校验 (PR1: cortex-schema 已合入 cortex-lint):

`read <target-path>` 取该目录 schema, 按 required + defaults 自动填 frontmatter 和 tags_required (含 placeholder, 由 lint --fix 后续完善)。

例:

- 落 `知识库/项目/<host>/<org>/<repo>/_index.md` → 自动加 `type:project` / `host:<host>` / `org:<org>` / `repo:<repo>` / `tags:[type/project, host/<host>, org/<org>, repo/<repo>]`
- 落 `记忆/L1-长期/procedural/<skill>.md` → 自动加 `level:L1` / `tags:[memory/L1, memory/procedural]`

schema 源: `<vault>/_meta/frontmatter-schema.yaml` (fallback plugin `templates/frontmatter-schema.yaml`)。

缺 `tags_required` prefix 时由 lint rule `frontmatter-schema-violation` 报警 + autofix。

## 套模板

读 `<vault>/_templates/<type>.md` (不存在则读 plugin presets `<plugin>/presets/seed/_templates/<type>.md`):

- 替换 `{{TITLE}}` / `{{CREATED}}` / `{{UPDATED}}` (UTC `YYYY-MM-DD`)
- tags 自动加 `[cortex-auto]` 标记
- AI 自评 4 评分字段时, 用启发式: 见 `skills/cortex-ingest/references/extract.md §3.1`
