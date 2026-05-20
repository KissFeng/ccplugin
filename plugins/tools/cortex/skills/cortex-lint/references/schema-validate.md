# cortex-lint — schema 校验 + 白名单

## frontmatter-schema-violation 启发式补字段

`run.py --fix` 自动补 `type` / `created`; 其余字段 AI 启发式:

| 字段 | 启发式 |
|---|---|
| `desc` | H1 + 首段 ≤ 100 字 |
| `source_url` | git remote / 原始 URL / "N/A" |
| `version` | git sha / pkg version / fetch date |
| `when_to_read` | "当用户问 <topic> 时" |
| `score` | 0.0-10.0 (上游活跃度, 无信号 = 5.0) |
| `confidence` | 0.0-10.0 (AI 自评把握度) |
| `source_credibility` | host 白名单查表 (见 `scripts/cli/lib/remote.py:_HOST_CREDIBILITY`) |
| `maturity` | 按目录: 项目/ 收件箱/ = draft; 领域/ = stable; 日记/ = review |

## 评分字段强制 (rule 21 frontmatter-required-scores)

知识库 .md 必含 4 字段 (全 0.0-10.0 浮点):

- `score` / `confidence` / `source_credibility` / `maturity` (enum draft|review|stable|deprecated)

记忆 .md 必含 2 字段:

- `importance` / `confidence`

autofix: 缺字段时写 stub 值 (score=5.0 / confidence=5.0 / source_credibility=5.0 / maturity=draft / importance=5.0)。AI 后续 ingest_remote/save 自动重评。

## tags 派生策略 (rule 17 fm-missing-tags)

仅校验 tags 字段存在 + 类型 list (无数量下限)。派生**语义** tag (内容相关), 严禁占位 (`<待填>` / `placeholder/N` / `TODO` / `TBD`)。

**派生来源** (优先级):
1. frontmatter `aliases` (高质量, 直接采)
2. h1/h2 标题词 slug (中文 2-4 字 / 英文 PascalCase 小写化)
3. 正文 500 字内的高频中文 2-4 字短语 + 英文 PascalCase
4. 概念名

**不要派生**结构/元数据/分类前缀 tag (`type/x` / `source/x` / `topic/x` / `host/x` / `org/x` / `repo/x` / `lang/x` / `stack/x` / `score/x` / `maturity/x` / `created/x` / `year/x` / `keyword/x` / `memory/Lx` 等)。这些信息已在 frontmatter 字段, 不需重复成 tag。schema v2 已移除 `tags_required` 字段, lint 不再校验 hierarchical 前缀缺失。

**lint 禁令**: `fm-banned-tags` 禁裸结构 (`index/meta/template/_index/stub`) + 裸时间 (`YYYY[-MM[-DD]]/YYYY-Q[1-4]/YYYY-W##`); hierarchical `xxx/yyy` lint **不禁** (允许用户/特定场景手动加), 但**派生侧不主动生**。

tag 命名: kebab-case, 全小写; 单 tag 优于斜杠分层。

## 白名单匹配规则

完整 vault schema 见 `plugins/tools/cortex/scripts/lint/schemas.py` (单一 4 子目录布局)。

- vault 根**相对路径精确串相等** (dir 加尾 `/`, file 不加), 不支持 glob
- 隐藏目录 `.obsidian` / `.trash` 默认 allowed, 无需白名单
- 模板/示例文件可加 frontmatter `lint-skip: true` 跳过全部 lint

## structure_purge 字段格式

run.py 输出 JSON 含:

- `structure_purge.violation_count`: int
- `structure_purge.backup_root`: 相对 vault 根的 backup 目录 (如 `_meta/.cortex-backup/structure/<ts>/`)
- `structure_purge.mv_plan[]`: `[{from, to}]` 待移项
- 同步 `errors[]` 中 `vault-structure-violation` 项含 `path` / `kind` / `reason` / `backup_target`

run.py 不交互, 只输出违规列表 + mv_plan; **交互全在 SKILL 流程内**, 实际 mv 也在此执行。
