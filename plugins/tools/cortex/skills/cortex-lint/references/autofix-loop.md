# cortex-lint — --fix 循环 + 自决执行路径

## 强制循环 (loop until stable)

1. Bash 跑 `lint.run --fix`
2. 解 JSON: `errors_remaining == 0 && structure_purge.violation_count == 0` → 退出
3. 否则按"自选执行路径"用工具修每条命中
4. 回 1, 直至稳定 或 同一规则连 5 轮无进展 (穷尽所有工具路径后才允许停)

## 自选执行路径 (AI 自决, 禁问)

| 规则 (非 autofix) | AI 必须执行 |
|---|---|
| dead-wikilink | lint 解析器已自动剥离 fenced/inline code 内 `[[...]]`; 残留命中即正文 dead link → `Write` 创 stub 到 `知识库/收件箱/<target>.md`, 最小 frontmatter (type 按目录推断, `created` 用 `YYYY-MM-DD`) |
| duplicate-alias | `Edit` 改其中一 frontmatter alias 加目录后缀; 或 Read+Write 合并两文件后删源 |
| orphan-page | Read 正文行数: ≤ 3 行 (空 stub) `git rm` 删除; 否则 `Edit` 加 `tags: [orphan]` 或在最近邻 `_index.md` 插反链 (`bash ~/.cortex/scripts/search.sh` 找邻) |
| filename-illegal / path-naming-violation | `git mv` 改: 长度 ≤ 50 字符, kebab-case, ASCII + 数字 + 连字符; 超长用 `<prefix>-<sha8>.md` (前 30 字符 + content sha 8 位); grep+Edit 改所有引用 |
| callout-unknown-type | `Edit` 替成最近已知 callout (note/tip/warning/info) |
| log-too-long | digest 自动归档 (无需 lint 介入) |
| i18n-path-not-in-locale | 比对 `_meta/version.json:.lang` 与 `locales/<lang>.yml:.dirs` 顶层名; 顶层名不在 locale dirs → `git mv` 改为标准名 |
| vault-misaligned | 单步 `python3 <abs>/scripts/lint/run.py --vault <vault> --sync-templates` 同步 `_templates/`, 再回主循环 |
| frontmatter-schema-violation | run.py --fix 补 type/created; 其余字段 AI 启发式补 (见 schema-validate.md) |
| vault-structure-violation (`structure_purge`) | **BATCH_MV 默认**: `mkdir -p <backup_root>` → 遍历 `mv_plan[]` mv 到 backup_root, **无 AskUserQuestion** |

## 工具优先级 (依次尝试)

1. Bash + Edit/Write 本地直改
2. cortex CLI: `bash ~/.cortex/scripts/save.sh` / `search.sh` / `memory.sh write`
3. cortex-refactor 脚本 (复杂 rename)
4. WebSearch / WebFetch (规则模糊时查文档)
5. Read 同 vault 合规样本复制结构

## 严禁 (任一出现 = 契约违反)

| # | 禁止模式 | 反例 |
|---|---|---|
| 1 | "修复建议" / "建议" / "推荐操作" 章节 | `## 修复建议`, `\| 类型 \| 操作 \|` |
| 2 | 用户确认问句 | `需确认?`, `是否执行?`, `要继续吗?`, 末尾问号 |
| 3 | "需人工"/"待人工处理"/"建议人工" | — |
| 4 | AskUserQuestion 调用 | (allowed-tools 已禁) |
| 5 | "下一步"/"后续"/"如需"导引 | — |
| 6 | 报 errors_remaining > 0 然后停 | **必须继续修, 不许停** |
| 7 | "AI 能力不足"/"无法自动" 推卸辞令 | — |

写盘前不需二次确认 (AUTO_MODE 隐含已授权)。

## 终态输出 (仅两种)

**clean**:

```
fixed_total: <N>
rounds: <N>
final_state: clean
```

**stuck** (仅工具客观失败 — 磁盘只读 / git lock / 权限拒绝; 禁用作"我不会"借口):

```
fixed_total: <N>
rounds: <N>
stuck_on: <rule>:<count>
attempted_paths: [...]
```

## 结构违规 4 选 (Interactive 模式)

cortex-lint --fix JSON 含 `structure_purge.violation_count > 0` 时, 用 `AskUserQuestion` 一次性总体确认, 4 选项:

- **BATCH_MV (推荐)**: 全部 mv 到 `<backup_root>/` (非真删, 可恢复)
- **BATCH_WHITELIST**: 全部追加 `_meta/version.json:.lint_whitelist[]`
- **PER_ITEM**: 逐个 4 选项 (向后兼容)
- **CANCEL**: 取消, 本次不动

落操作详见原 SKILL.md (PR2 拆分前内容)。AUTO_MODE 自动走 BATCH_MV。

## 非 AUTO_MODE (Interactive)

IDE 内手动调 `/cortex:lint --skill` interactive: 主流程及"手动修复建议"段适用, 可输出建议 + 询问。
