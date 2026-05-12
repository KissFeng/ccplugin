---
name: cortex-lint
description: 跑 15 条 vault lint (frontmatter/wikilink/orphan/命名/i18n) + autofix; --fix 才落盘。Triggers on "wiki audit", "lint", "vault 体检".
allowed-tools: Bash Read Glob mcp__obsidian__obsidian_list_files_in_vault mcp__obsidian__obsidian_list_files_in_dir mcp__obsidian__obsidian_get_file_contents mcp__obsidian__obsidian_patch_content
---

# cortex-lint

对 vault 跑 13 条 lint 规则, 输出 JSON 报告 (errors/warns/summary)。默认 dry-run。

## 触发场景

- 用户问"vault 健康吗 / wiki audit / 找 orphan"
- 显式 "/cortex:lint" 或 "lint the wiki"
- cron daily 任务

## 行为

1. 解析 vault 路径 (跑 `~/.claude/plugins/marketplaces/ccplugin-market/plugins/tools/cortex/hooks/_lib/resolve_vault.sh`); 不存在则报错
2. 调 `python3 ~/.claude/plugins/marketplaces/ccplugin-market/plugins/tools/cortex/lint/run.py --vault <path> [--fix] [--scope=<glob>]`
3. 解析 JSON 报告:
   - 报错块 (severity=error): rule#1 fm-missing-type, #3 dead-wikilink, #5 duplicate-alias, #10 filename-illegal, #11 block-id-duplicate
   - 警告块 (severity=warn): rule#2 fm-missing-created, #4 orphan-page, #6 hot-too-long, #7 log-too-long, #8 index-missing-section, #9 title-h1-mismatch, #12 callout-unknown-type, #13 path-naming-violation
4. 渲染 markdown 摘要 (按 rule 分组, 列前 20 条命中)
5. 如用户指定 `--fix`:
   - 在 `<vault>/_meta/.cortex-backup/lint/<ts>/` 写 backup
   - 仅对 `autofix:true` 规则改盘 (rule 1/2/6/8/9/11)
   - 其他规则需用户手工处理 (cortex-refactor 可协助 rename/merge)

## 13 条规则 (rules.json)

| #   | id                    | severity | autofix                                          |
| --- | --------------------- | -------- | ------------------------------------------------ |
| 1   | fm-missing-type       | error    | ✓ (按目录推断)                                   |
| 2   | fm-missing-created    | warn     | ✓ (用 mtime)                                     |
| 3   | dead-wikilink         | error    | ✗ (建议 cortex-new 创建 stub)                    |
| 4   | orphan-page           | warn     | ✗ (人工补 tag/链接)                              |
| 5   | duplicate-alias       | error    | ✗ (人工合并)                                     |
| 6   | hot-too-long          | warn     | ✓ (截断+落 folds/)                               |
| 7   | log-too-long          | warn     | ✗ (建议触发 cortex-historian agent §Fold 工作流) |
| 8   | index-missing-section | warn     | ✓ (自动补条目)                                   |
| 9   | title-h1-mismatch     | warn     | ✓ (以 frontmatter 为准)                          |
| 10  | filename-illegal      | error    | ✗ (cortex-refactor rename)                       |
| 11  | block-id-duplicate    | error    | ✓ (重哈希)                                       |
| 12  | callout-unknown-type  | warn     | ✗ (报告)                                         |
| 13  | path-naming-violation | warn     | ✗ (cortex-refactor rename)                       |

## 输出格式

返回给用户的 markdown 报告包含:

```
## cortex-lint 报告

vault: <abs path>
files scanned: N
errors: E   warns: W   fixed: F

### errors

| rule | file | line | msg |
| --- | --- | --- | --- |
...

### warns

(同上)
```

## 安全

- 默认 dry-run, 不动盘
- `--fix` 前在 `_meta/.cortex-backup/lint/<ts>/` 全量 backup 待修改文件
- backup 目录由 cortex 维护, 用户可手动 git ignore (`_meta/.cortex-backup/`)

## 交互修复 (--fix 模式 vault-structure-violation 专用)

run.py 的 python 进程不交互, 只输出 JSON 违规列表; **交互全在本 SKILL 流程内**。

cortex-lint --fix 输出 JSON 含 `vault-structure-violation` 违规时:

1. 解析违规列表 (`errors[]` 中 `rule == "vault-structure-violation"` 项)。每项含 `path` / `kind` (dir|file) / `reason`
2. 对每个违规, **必须** 用 `AskUserQuestion` 工具询问 (禁文本式提问), 4 个选项:
   - 选项 1: **移到允许目录** — 列 schema.root_dirs 候选 (LYT preset: `_meta`, `10_concepts`, `20_efforts`, `30_domains`, `40_anchors`, `50_calendar`, `60_journal`, `70_attachments`, `80_archive`, `90_inbox`, `folds`, `log`, `sessions` 等)
   - 选项 2: **删除** — 危险操作, **必须** 再次 `AskUserQuestion` 二次确认 (展示路径 + 建议先 backup)
   - 选项 3: **加白名单** — 写 `_meta/version.json:.lint_whitelist[]`, 后续 lint 跳过
   - 选项 4: **跳过** — 单次不动, 不写白名单
3. 按选择落操作:
   - **move**: obsidian CLI move 或 `mcp__obsidian` 或 `mv` (按 fallback 顺序)
   - **delete**: 二次 `AskUserQuestion` 确认 → `rm` / `rm -rf` (dir 需 -rf)。建议先 `cp -r` 到 `_meta/.cortex-backup/lint/<ts>/deleted/`
   - **whitelist**: 读 `_meta/version.json` (JSON), append `path` 到 `.lint_whitelist[]` (dir 含尾 `/`, file 不含), 写回
   - **skip**: 不动
4. 每个违规处理完后, 打 `[done]` 状态行 (rule + path + 选择)

完整 preset schema 见 `plugins/tools/cortex/lint/schemas.py` (LYT / PARA / flat 三套)。

白名单匹配规则: vault 根相对路径**精确串相等** (dir 加尾 `/`, file 不加), 不支持 glob。隐藏目录 `.obsidian` / `.trash` 默认 allowed, 无需白名单。
