# cortex-refactor — rename / merge 子操作

> SKILL.md 入口的 rename + merge 详细行为。dry-run 默认, `--apply` 才落盘。

## rename — 改文件名 + 全 vault wikilink 同步

```bash
python3 ~/.claude/plugins/marketplaces/ccplugin-market/plugins/tools/cortex/scripts/refactor/rename.py \
  --vault <path> --from <old-rel> --to <new-rel> [--apply]
```

- 扫全 vault `[[old-stem]]` 与 `![[old-stem]]`, 替换为新 stem
- 不动 alias 字段 (用户决定是否保留)
- backup → `_meta/.cortex-backup/refactor-rename/<ts>/`

## merge — 两页合一

```bash
python3 ~/.claude/plugins/marketplaces/ccplugin-market/plugins/tools/cortex/scripts/refactor/merge.py \
  --vault <path> --from <src> --into <target> [--apply]
```

- `<src>` 内容 (去 frontmatter) 追加到 `<target>` 末尾, 用 H2 分隔
- 全 vault 反链 `[[<src-stem>]]` 重定向到 `<target-stem>`
- `<src>` 移到 `归档/`
- 时间戳前缀避免 archive 内重名

## migrate-locale — 切 vault.lang 时一次性 rename 业务目录

```bash
python3 ~/.claude/plugins/marketplaces/ccplugin-market/plugins/tools/cortex/scripts/refactor/migrate_locale.py \
  --vault <path> --from <lang> --to <lang> [--apply]
```

- 比对两个 lang 的 `dirs` map, 对每对差异计划 rename
- git repo 走 `git mv` (保留历史), 否则 `os.rename`
- 全 vault wikilink 替换 (path-prefixed)
- 写 `_meta/version.json:.lang = <to>` + `_meta/migrations/<ts>-migrate-locale.json`

## dedupe — TF-IDF 相似页对自动合并

| 子命令 | 签名 | 说明 |
|---|---|---|
| dedupe | `--vault P [--scope all\|concepts\|domains\|log] [--threshold 0.85] [--top-k 20] [--apply]` | 用 TF-IDF cosine 找 ≥ threshold 的候选页对; `--apply` 调 `merge.py` 合并 |

调用模板:

```bash
python3 ~/.claude/plugins/marketplaces/ccplugin-market/plugins/tools/cortex/scripts/refactor/dedupe.py \
  --vault "$VAULT" --scope concepts --threshold 0.85
```

## 输出示例 (rename dry-run)

```json
{
  "op": "rename",
  "from": "知识库/领域/foo.md",
  "to": "知识库/领域/foo-bar.md",
  "files_to_update": [
    { "file": "log/2026-05/10-1430-design.md", "replacements": 2 },
    { "file": "_assets/dashboards/concepts-dashboard.md", "replacements": 1 }
  ],
  "applied": false
}
```

dry-run 结束 (interactive 模式), **必须调 `AskUserQuestion`** 询问: "已扫描 N 个文件 M 处替换, 是否应用?" options: `应用 (--apply 重跑)` / `取消` / `仅看 diff`。

L3 写盘授权门: 涉及 ≥3 文件批量改写时, AskUserQuestion 列出受影响文件路径 (per-batch 单次授权); <3 文件 per-file 逐个授权。
