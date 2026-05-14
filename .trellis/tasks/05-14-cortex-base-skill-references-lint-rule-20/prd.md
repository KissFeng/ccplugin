# cortex .base 格式硬契约 — SKILL/references 加约束 + lint rule 20

## Goal

cortex-ingest 生成 `.base` 文件时格式翻车, 用户 Obsidian 报错"无法解析数据库文件: 查询格式无效, 必须为 YAML 对象"。

vault 内实际 5 个 .base 文件 3 种错格式:
1. `知识库/项目/github.com/lazygophers/scode/_db.base` — markdown headers + tables (完全错)
2. `知识库/项目/persons/lyxamour/ai/_db.base` — Dataview DQL 语法 (TABLE/FROM, 错插件)
3. `仪表盘/meta/ops/dashboard.base` — 正确 YAML, 但内含 `wiki/` 路径残留 (用户数据, 不动)

Obsidian Bases (1.7+) 要求 `.base` 内容**顶层 YAML 对象** (`filters:` / `views:` / `formulas:` 等), 不接受 markdown / DQL。

**根因**: cortex-ingest references/knowledge-graph.md §9.1 给的模板是正确 YAML, 但 AI 主线落档时受 vault md-native 惯性把 `.base` 当 .md 写。SKILL 缺强约束。

本任务:
- **A**: SKILL/references 加 .base 格式硬契约 (顶层 YAML / 禁 markdown header / 禁 Dataview DQL)
- **B**: 加 lint rule 20 `base-format-yaml` 扫 .base 文件强制 YAML object 顶层

## What I already know

### vault truth (确认)

cortex 仓库内**无** .base 模板文件 (`find plugins/tools/cortex/ -name "*.base"` 空)。.base 全由 AI 主线在 ingest pipeline 生成。

### references 模板现状

`plugins/tools/cortex/skills/cortex-ingest/references/knowledge-graph.md` §9.1 L13-30 给的模板**是正确 YAML**:
```yaml
filters:
  and:
    - file.ext == "md"
views:
  - type: table
    name: all
    order: [file.name, type, maturity, score, updated]
```

问题不在模板, 而在 AI 没遵守 — 缺**强约束语言**禁 markdown / DQL。

### lint rules.json 现状

`plugins/tools/cortex/scripts/lint/rules.json` 现 19 条 (上批 PR 加 rule 19 skill-references-exists)。
本 PR 加 rule 20 → 20 条。

### lint run.py 现状

`plugins/tools/cortex/scripts/lint/run.py` 现有 check 函数: `_check_path_lang_mismatch` / `check_skill_references_exists` 等。本 PR 加 `check_base_format_yaml`。

### 不动 (排除)

- 用户 vault 内现有错 `.base` 文件 (是用户数据, 不属 cortex 仓库; 用户主动调 `ingest_remote.sh` 重 ingest 即可覆盖)
- `dashboard.base` 内 `wiki/` 路径残留 (同上, vault 数据)
- ingest_remote.py / refresh_projects.py 实现 (上批 PR 已落)

## Decision (ADR-lite)

**Context**: 用户报错"必须为 YAML 对象", 根因为 AI 落 .base 时格式错。Vault 数据不动, 仅修代码层防新错。

**Decision**:
- D1 强约束位置: `references/knowledge-graph.md §9.1` (而非 SKILL.md 主流程), 配新增"禁忌"小节
- D2 lint 严重度: warn (不阻断 ingest, 但 dashboard / vault audit 报警)
- D3 lint 检查范围: `vault/**/*.base` 全部, 排除 `.obsidian/` / `归档/` / `.trash/`
- D4 lint 检查内容:
  - 文件首行不能是 markdown header (`#` / `##` 开头)
  - 文件不能含 Dataview DQL 关键字 (`^TABLE\s` / `^LIST\s` / `^FROM\s` / `^WHERE\s` 等行首)
  - 文件能被 yaml.safe_load 解析为 dict (不是 list / string / None)
  - 解析后顶层至少含 `filters` / `views` / `formulas` 之一 (Bases schema 必有字段)
- D5 autofix: 不做 (用户 vault 内 .base 由用户 ingest 流程重生, 不直接 patch)

**Consequences**:
- vault audit `bash ~/.cortex/scripts/lint.sh` 后续会报错 .base 文件 (符合预期, 提醒用户重 ingest)
- 新 ingest 落 .base 后再过 lint rule 20 自检, AI 出错时立即被发现 (不需人眼检查)

## Requirements

### R1: references/knowledge-graph.md 加 .base 格式硬契约

读现有 `plugins/tools/cortex/skills/cortex-ingest/references/knowledge-graph.md` §9.1 (L13-30), 重写为:

```markdown
## 9.1 Bases 数据库视图 (`_db.base`)

落 `知识库/项目/<host>/<org>/<repo>/_db.base` (Obsidian 1.7+ JSON5 原生格式)。

### 硬契约 (PR 标 base-format-yaml)

**禁忌** (违反 = lint rule 20 fail):

1. **不是 markdown 文件** — 首行**禁** `#` / `##` 标题, 整个文件**禁**任何 markdown 语法 (header / table / list bullet / code fence)。即使文件扩展 `.base` 也不是 .md。
2. **不是 Dataview DQL** — 严禁 `TABLE` / `LIST` / `FROM "..."` / `WHERE` / `SORT` 行首关键字。Bases ≠ Dataview, 两套插件语法。
3. **顶层必须 YAML object** — 文件被 `yaml.safe_load(content)` 解析必须返回 `dict`, 不能是 list / string / None。
4. **顶层至少 1 个 Bases schema 字段** — `filters` / `views` / `formulas` / `properties` 任一。

### 最小可工作模板

\`\`\`yaml
filters:
  and:
    - file.ext == "md"
views:
  - type: table
    name: all
    order: [file.name, type, maturity, score, updated]
  - type: card
    name: by-type
    groupBy: type
    columns: [title, tags, score]
  - type: table
    name: stable-high
    filters:
      and:
        - maturity == "stable"
        - score >= 4
    order: [score, updated]
\`\`\`

字段对齐 `references/extract.md` §3 frontmatter schema (type / title / desc / created / updated / tags / source_url / version / when_to_read / score / maturity)。**不写 Dataview fallback** (用户保底 Obsidian ≥ 1.7)。

### 自检 (AI 落档后必跑)

```bash
python3 -c "import yaml; d = yaml.safe_load(open('<path>')); assert isinstance(d, dict), '.base 必须 YAML object'; assert any(k in d for k in ('filters','views','formulas','properties')), '.base 必须含 Bases schema 字段'"
```

不通过 = 重写。
```

### R2: lint rule 20 `base-format-yaml`

#### F2.1 `scripts/lint/rules.json` 加规则

```json
{
  "id": "base-format-yaml",
  "name": "base-format-yaml",
  "severity": "warn",
  "autofix": false,
  "description": ".base 文件必须顶层 YAML 对象 (Bases 1.7+ 原生格式), 禁 markdown / Dataview DQL"
}
```

#### F2.2 `scripts/lint/run.py` 加 check 函数

```python
import yaml

_DQL_KEYWORDS = re.compile(r"^\s*(TABLE|LIST|TASK|FROM|WHERE|SORT|GROUP BY|FLATTEN)\s", re.MULTILINE | re.IGNORECASE)

def check_base_format_yaml(rel: Path, content: str) -> list[Issue]:
    """rule 20: .base 顶层必须 YAML object + 禁 markdown/DQL."""
    issues = []
    if rel.suffix != ".base":
        return issues
    
    # 跳过 .obsidian / 归档 / .trash
    rel_str = str(rel)
    if any(p in rel_str for p in (".obsidian/", "归档/", ".trash/")):
        return issues
    
    # 检 1: 首行 markdown header
    first_line = content.split("\n", 1)[0].strip()
    if first_line.startswith("#"):
        issues.append(Issue(
            rule_id="base-format-yaml",
            rule_name="base-format-yaml",
            severity="warn",
            file=str(rel), line=1,
            message=f".base 文件首行不能是 markdown header (`{first_line[:30]}`), 必须 YAML object 顶层",
            autofix=None,
        ))
        return issues  # 已确认错, 不继续 yaml.safe_load (会再抛)
    
    # 检 2: Dataview DQL 关键字
    m = _DQL_KEYWORDS.search(content)
    if m:
        line_no = content[:m.start()].count("\n") + 1
        issues.append(Issue(
            rule_id="base-format-yaml",
            rule_name="base-format-yaml",
            severity="warn",
            file=str(rel), line=line_no,
            message=f".base 含 Dataview DQL 关键字 `{m.group(1)}`, Bases ≠ Dataview",
            autofix=None,
        ))
        return issues
    
    # 检 3: yaml.safe_load 解析
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        issues.append(Issue(
            rule_id="base-format-yaml",
            rule_name="base-format-yaml",
            severity="warn",
            file=str(rel), line=1,
            message=f".base YAML 解析失败: {e}",
            autofix=None,
        ))
        return issues
    
    if not isinstance(data, dict):
        issues.append(Issue(
            rule_id="base-format-yaml",
            rule_name="base-format-yaml",
            severity="warn",
            file=str(rel), line=1,
            message=f".base 顶层必须 YAML object (dict), 实际 {type(data).__name__}",
            autofix=None,
        ))
        return issues
    
    # 检 4: Bases schema 字段
    schema_keys = {"filters", "views", "formulas", "properties"}
    if not (set(data.keys()) & schema_keys):
        issues.append(Issue(
            rule_id="base-format-yaml",
            rule_name="base-format-yaml",
            severity="warn",
            file=str(rel), line=1,
            message=f".base 顶层缺 Bases schema 字段 (需 filters/views/formulas/properties 之一)",
            autofix=None,
        ))
    
    return issues
```

接入 `check_file()` 主循环 (与 rule 19 同位置)。

#### F2.3 测试 `tests/python/test_base_format_lint.py`

至少 8 case (tmp_path mock):

1. `test_base_yaml_valid` — 合法 YAML 模板 → 0 issue
2. `test_base_markdown_header` — `# Title` 首行 → 1 issue (markdown header)
3. `test_base_dataview_dql_table` — `TABLE file FROM "..."` → 1 issue (DQL)
4. `test_base_dataview_dql_list` — `LIST FROM ...` → 1 issue
5. `test_base_yaml_invalid` — 损坏 YAML (`key: : :`) → 1 issue
6. `test_base_yaml_list_top` — 顶层 list (`- item1`) → 1 issue (not dict)
7. `test_base_yaml_no_schema_field` — 合法 dict 但无 filters/views/formulas → 1 issue
8. `test_non_base_file_skip` — `.md` / `.json` 文件 → 0 issue
9. `test_obsidian_dir_skip` — `.obsidian/foo.base` → 0 issue
10. `test_archive_skip` — `归档/old.base` → 0 issue

### R3: docs/Lint 规则.md 同步

加 rule 20 描述行 + 修复方案小节 (调 ingest_remote 重 ingest 项目)。

### R4: AGENT.md / memory 资产计数

- AGENT.md (若有 lint 数字): 19 → 20
- `.claude/memory/cortex-plugin-2026-05-13.md`:
  - 资产计数表 Lint 规则 19 → 20
  - P6 节后加 P7 短注 (.base 格式硬契约)

## Acceptance Criteria

- [ ] knowledge-graph.md §9.1 加禁忌小节 + 自检命令
- [ ] rules.json rule 20 注册
- [ ] run.py check_base_format_yaml 实现 + 接入 check_file
- [ ] test_base_format_lint.py ≥ 8 case 全绿
- [ ] pytest 基线 389 → ≥ 397
- [ ] ruff check 干净
- [ ] docs/Lint 规则.md / AGENT.md / memory 同步
- [ ] lint smoke: 跑 `python3 plugins/tools/cortex/scripts/lint/run.py --rule base-format-yaml <vault>` 应能检出 user vault 内 2 错 .base (但 task 不改 vault, 仅验 lint 能检出)

## Definition of Done

- pytest 全绿
- ruff clean
- knowledge-graph.md 自检命令可手动跑通
- git commit (单 commit 即可)

## Out of Scope

- 不改用户 vault 内现有 .base 文件 (scode/_db.base / ai/_db.base / dashboard.base wiki/ 残留)
- 不加 autofix (D5, 用户主动调 ingest_remote 重 ingest 覆盖)
- 不改 ingest_remote.py / refresh_projects.py (上批 PR)
- 不破坏 389 测试基线

## Technical Notes

- yaml 解析: stdlib **不**自带 PyYAML, 但 cortex 已用 PyYAML (lint run.py 等), 检 imports 复用
- Bases schema 参考: https://help.obsidian.md/bases (Obsidian 1.7+ 官方)
- Dataview DQL 关键字参考 (排除): TABLE / LIST / TASK / FROM / WHERE / SORT / GROUP BY / FLATTEN

实际上检 PyYAML 是否已在依赖中:
- `grep -rn "import yaml" plugins/tools/cortex/scripts/lint/` 验
