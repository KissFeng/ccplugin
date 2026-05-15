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

## tags 强制 ≥ 10 (rule 17 fm-missing-tags)

`tags[]` ≥ 10, 严禁占位 (`<待填>` / `placeholder/N` / `TODO` / `TBD`)。至少覆盖 10 类:

1. 来源类型 `source/{repo|web|paper|book|local}` (必含)
2. 主题域 `topic/<领域>` (必含)
3. 技术栈 `stack/<语言或框架>` (必含)
4. 来源元数据 `host/<host>` / `org/<org>` / `repo/<repo>`
5. 语言 `lang/<zh-CN|en|...>`
6. 质量评分 `score/<1-5>`
7. 成熟度 `maturity/<draft|review|stable|deprecated>`
8. 时间 `created/<YYYY>`
9. 类型 `type/<concept|domain|log|...>`
10. 关键词 `keyword/<词>` (h1/h2/正文派生, 中文 2-4 字或英文 PascalCase)

autofix 读 fm + 正文派生; 不足由 AI 二次补, 严禁占位。tag 命名: kebab-case, 斜杠分层, 全小写。

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
