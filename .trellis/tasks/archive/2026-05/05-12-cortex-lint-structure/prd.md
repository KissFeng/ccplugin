# PRD — cortex-lint vault 结构强校验 + 交互修复

## 背景

用户跑 `/cortex:cortex-lint --fix` 后 vault 仍有不规范文件/文件夹存在。现 15 条 lint rule 只查 frontmatter / wikilink / orphan / 命名等**单页**问题,**不查** vault 根目录/文件夹整体结构合法性。

用户预期:**vault 必须严格按 preset (LYT/PARA/flat) 规范**,任何不在 schema 内的文件/文件夹都标违规,逐个手动处理 (移 / 删 / 白名单)。

## 目标

新 rule `vault-structure-violation` (severity=error),配合 cortex-lint skill 交互修复流程:
- 扫 vault 根 + 子树,任何不在 preset schema 内的路径 → 违规
- `--fix` 模式下,LLM 拿违规列表逐个 `AskUserQuestion` 询问处理 (move / delete / whitelist / skip)
- 白名单写 `_meta/version.json:.lint_whitelist[]`,后续 lint 跳过

## 范围

### 新增

- `plugins/tools/cortex/lint/schemas.py` — preset 合规结构定义 (LYT/PARA/flat allowed dirs + root files)

### 修改

- `plugins/tools/cortex/lint/rules.json` — 加 rule #16 `vault-structure-violation`
- `plugins/tools/cortex/lint/run.py` — 实现 `vault-structure-violation` 检查
- `plugins/tools/cortex/skills/cortex-lint/SKILL.md` — 加 §交互修复 章, --fix 流程明示 AskUserQuestion 逐个处理

### 不在范围

- 不动其它 15 rule
- 不动 P0-P6 / Phase A 已交付内容
- 不动 hooks / install.sh / mcp/ (除 run.py 已有逻辑)

## 详细规范

### 1. schemas.py — preset 合规结构

```python
"""Vault structure schemas per preset.

Each schema defines:
- root_dirs: allowed top-level directories
- root_files: allowed top-level files
- All other paths at vault root → vault-structure-violation
"""
from __future__ import annotations
from typing import TypedDict


class VaultSchema(TypedDict):
    root_dirs: set[str]
    root_files: set[str]


SCHEMAS: dict[str, VaultSchema] = {
    "LYT": {
        "root_dirs": {
            "_meta",          # 配置 + backup + 元数据
            "10_concepts",    # 概念
            "20_efforts",     # 项目
            "30_domains",     # 领域
            "40_anchors",     # 锚点 / MOC
            "50_calendar",    # 日程
            "60_journal",     # 日记
            "70_attachments", # 附件
            "80_archive",     # 归档
            "90_inbox",       # 收件箱
            "folds",          # fold 后日志
            "log",            # 滚动日志
            "sessions",       # 会话备份
            ".obsidian",      # Obsidian 配置 (隐藏)
            ".trash",         # Obsidian 回收站 (隐藏)
        },
        "root_files": {
            "hot.md",         # 热缓存
            "index.md",       # 索引
            "README.md",      # 可选 README
            "dashboard.md",   # 仪表盘 (可选)
            "index-map.md",   # 脑图 (可选)
        },
    },
    "PARA": {
        "root_dirs": {
            "_meta",
            "1_projects",
            "2_areas",
            "3_resources",
            "4_archives",
            "log",
            "sessions",
            ".obsidian",
            ".trash",
        },
        "root_files": {"hot.md", "index.md", "README.md"},
    },
    "flat": {
        "root_dirs": {
            "_meta",
            "concepts",
            "domains",
            "log",
            "sessions",
            ".archive",
            ".obsidian",
            ".trash",
        },
        "root_files": {"hot.md", "index.md", "README.md"},
    },
}


def get_schema(preset: str) -> VaultSchema:
    """Return schema or LYT default."""
    return SCHEMAS.get(preset, SCHEMAS["LYT"])
```

### 2. rules.json 加新规则

```json
{
  "id": "vault-structure-violation",
  "severity": "error",
  "description": "vault 根或子目录含非 preset schema 允许的文件/文件夹 (需交互修复)",
  "autofix": false
}
```

### 3. run.py 实现 check

新函数:

```python
def check_vault_structure(vault: Path, preset: str,
                          whitelist: set[str]) -> list[dict]:
    """Return list of violations.

    Each violation: {
        "rule": "vault-structure-violation",
        "path": str (relative to vault),
        "kind": "dir"|"file",
        "reason": str,
    }
    """
    from .schemas import get_schema
    schema = get_schema(preset)
    allowed_dirs = schema["root_dirs"]
    allowed_files = schema["root_files"]
    violations = []

    for entry in vault.iterdir():
        rel = str(entry.relative_to(vault))
        if rel in whitelist:
            continue
        if entry.is_dir():
            if entry.name not in allowed_dirs:
                violations.append({
                    "rule": "vault-structure-violation",
                    "path": rel,
                    "kind": "dir",
                    "reason": f"目录 '{entry.name}' 不在 {preset} preset 允许列表",
                })
        elif entry.is_file():
            if entry.name not in allowed_files:
                violations.append({
                    "rule": "vault-structure-violation",
                    "path": rel,
                    "kind": "file",
                    "reason": f"文件 '{entry.name}' 不在 {preset} preset 允许列表",
                })

    return violations
```

`whitelist` 读自 `_meta/version.json:.lint_whitelist[]`,缺则空 set。

挂入主 lint 流程:

```python
def main(...):
    ...
    preset = config.get("preset", "LYT")
    whitelist = set(config.get("lint_whitelist", []))
    violations = check_vault_structure(vault, preset, whitelist)
    for v in violations:
        report["errors"].append(v)
```

`--fix` 模式下 **不在 python 内**直接交互 (python 进程无 AskUserQuestion 能力),仅输出违规列表,交给 cortex-lint skill (LLM) 处理。

### 4. SKILL.md 加交互修复章节

```markdown
## 交互修复 (--fix 模式 vault-structure-violation 专用)

cortex-lint --fix 输出 JSON 含 `vault-structure-violation` 违规时:

1. 解析违规列表 (errors[] 中 rule=vault-structure-violation 项)
2. 对每个违规, **必须** 用 `AskUserQuestion` 工具询问 (禁文本式提问):
   - 选项 1: 移到允许目录 (列 schema.root_dirs 候选)
   - 选项 2: 删除 (危险操作, 二次确认)
   - 选项 3: 加白名单 (写 _meta/version.json:.lint_whitelist[])
   - 选项 4: 跳过 (单次, 不写白名单)
3. 按选择落操作:
   - move: obsidian CLI move 或 mcp__obsidian 或 mv (按 fallback 顺序)
   - delete: **必须** 二次 AskUserQuestion 确认, 路径含 backup 提示
   - whitelist: 读 _meta/version.json, append `.lint_whitelist[]`, write
   - skip: 不动
4. 每个违规处理完后, 打 [done] 状态行

允许目录 (LYT preset):
- _meta, 10_concepts, 20_efforts, 30_domains, 40_anchors, 50_calendar,
  60_journal, 70_attachments, 80_archive, 90_inbox, folds, log, sessions

完整 schema 见 plugins/tools/cortex/lint/schemas.py.
```

### 5. 白名单读写

`_meta/version.json` 增字段 (向后兼容,缺则默认空):

```json
{
  "version": "0.x.y",
  "preset": "LYT",
  "lang": "zh-CN",
  "lint_whitelist": [
    ".DS_Store",
    "custom-tool-output/"
  ]
}
```

path 为 vault 根相对路径 (含尾 `/` 表目录)。匹配规则:精确串相等。

## 验收

1. `lint/schemas.py` 含 3 preset × root_dirs/root_files 定义
2. `rules.json` 加 vault-structure-violation (severity=error)
3. `run.py` 调 check_vault_structure 挂主流程,违规入 errors[]
4. mock vault (LYT preset 含 1 个非法 dir + 1 个非法 file) → JSON 报告 errors[] 含 2 项, rule=vault-structure-violation
5. mock vault `_meta/version.json:.lint_whitelist=["foo/"]` + 含 `foo/` dir → 不报违规
6. `.obsidian` + `.trash` 隐藏目录 → 不报违规 (在 allowed_dirs)
7. SKILL.md §交互修复 段存在,明示 AskUserQuestion 工具 + 4 选项
8. pytest 新增 ≥4 用例 (3 preset 各 1 正例 + whitelist + 隐藏目录跳过)
9. P0-P6 / Phase A 不回归

## 不变量

- 纯 stdlib python, 禁外部 dep
- python 不做交互, 只输出 JSON 违规列表
- 交互全在 SKILL.md LLM 流程内 (AskUserQuestion 硬规则)
- 隐藏目录 (`.obsidian`/`.trash`) 默认 allowed (Obsidian 必需)
- 白名单是路径精确匹配, 不支持 glob (简洁)

## 风险

- **schemas 与实际 vault 现状漂移**:用户 vault 可能已有大量非规范文件。**缓解**: 首次跑预期大量违规, 白名单一次性收容
- **删除操作不可逆**:SKILL.md 明示二次 AskUserQuestion 确认 + 建议先 backup
- **PARA/flat preset 的 schema 不完整**:仅列常见目录, 用户自定义需走白名单
- **大 vault 性能**:iterdir() 仅扫根, O(1) 级别, 无性能问题 (非递归)
