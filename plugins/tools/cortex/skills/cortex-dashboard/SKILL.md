---
name: cortex-dashboard
description: 渲染仪表盘 — 读 frontmatter view_query (dict) 查记忆/知识库/cron 数据源, 渲染 KPI + 图表 + Top-N + Legend, 注入 DASH:BEGIN/END 区, 不破坏正文。触发: "build dashboard" / "刷新仪表盘" / "仪表盘" / "dashboard" / daily cron。
disable-model-invocation: true
allowed-tools: Bash Read Write Edit Glob
---

# cortex-dashboard

读 `仪表盘/<page>.md` frontmatter `view_query` (dict) → 走对应 Bash 数据查询 → 按 `view_chart` 渲染 (KPI callout + chart + Top-N + Legend) → 注入 `<!-- DASH:BEGIN -->...<!-- DASH:END -->` 区, 不动正文与其他 frontmatter 字段。

**单一真相**: 本 SKILL 是 cron + slash 唯一规范, `scripts/cron/dashboard.sh` 与 `commands/dashboard.md` 只 thin 委托。

## 触发场景

- daily cron `dashboard.sh` (02:30) 或用户显式 "build dashboard" / "刷新仪表盘" / "/cortex:dashboard"
- cortex-cartographer agent 调用

## 关键决策树

1. **扫目标**: `Glob "仪表盘/*.md"` (cap 20)
2. **解 frontmatter**: 读前 60 行 yaml → 提取 `view_query{kind, level?, limit?, window?}` + `view_chart` + `view_kpi[]` + `view_legend` + `view_stale_after` (默认 24h)
3. **stale 判定**: 找 DASH:BEGIN 注释 `rendered_at`, now - rendered_at < stale_after → skip (除 --force)
4. **数据查询**: 按 `view_query.kind` 走 [references/data-sources.md](references/data-sources.md) 8 种枚举 (memory / knowledge / ledger / cron / bridge / distribution / promotion / warden)
5. **数据源不存在** → errors[], 不写 DASH 区, 保留上次渲染; **数据源空** → 计数 0 正常渲染; **严禁** `N/A` / `—` / 占位
6. **渲染**: KPI callout → chart → Top-N table → LEGEND callout, 顺序固定; chart 模板见 [references/chart-templates.md](references/chart-templates.md)
7. **注入**: 替换 `<!-- DASH:BEGIN rendered_at=<ISO> query_hash=<sha-8> -->...<!-- DASH:END -->` 整段; 不存在则末尾追加
8. **输出**: 单行 JSON `{refreshed:[...], skipped:N, errors:[{path,reason}]}`

## AUTO_MODE (wrapper / cron 传 `auto` 后缀)

- **不调** AskUserQuestion (wrapper allowed-tools 已禁)
- persistent: 任何 page error 自决降级, 继续下一页, 禁询问禁中止
- 默认决策: `--force=false` (stale 跳过), `cap=20`, 数据源缺 → errors[] continue 不阻断
- 写盘不需二次确认
- 终态: 输出汇总 JSON, 即使 errors 非空也算 task complete

## References

| 文件 | 内容 |
|---|---|
| [references/data-sources.md](references/data-sources.md) | 8 种 `view_query.kind` 对应的 Bash 查询模板 |
| [references/chart-templates.md](references/chart-templates.md) | pie/sankey/heatmap/timeline/mindmap/table/grid 6 种 chart 模板 + fallback |
| [references/dash-section.md](references/dash-section.md) | DASH:BEGIN/END 区完整结构 + query_hash 计算 + AUTO_MODE 流程细节 |

## 错误处理

- frontmatter 缺 view_query / kind 不在 8 枚举 → errors[], continue
- 数据源路径不存在 → errors[], 不写 DASH, 保留上次渲染
- 单页渲染异常 → errors[], 不影响后续页

## 不做

- 不读 vault 外文件 (`~/.cache/cortex/` 例外, 仅 cron kind)
- 不读 vault 内 .jsonl / .md 全文 (除 frontmatter 前 60 行)
