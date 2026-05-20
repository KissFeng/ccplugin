---
name: cortex-digest
description: 全量深度 digest — log/session 数据 + 全 vault 深读 (8 阶段, 默认 deep, 无 depth 参数), 增量游标 (vault/.cortex/state/*.json) 自动跳已处理。L4 全清单向漏斗, L0/L1 永不删条目。stage 5 含记忆↔知识库双向桥。触发: daily cron 03:00 / 用户显式 "digest" / "巩固记忆" / "consolidate"。
disable-model-invocation: false
allowed-tools: Bash Read Write Edit Glob Grep Skill
---

# cortex-digest

[AUTO_MODE persistent: 禁询问, 自决执行, 禁中止]

**全量深度模式 — 默认 deep, 无 depth 参数**。每日跑一次完整 8 阶段, 增量游标驱动避免重复处理。全量跑可能数小时, 不中止 / 不分批。

## 触发场景

- daily cron 03:00 自动 (`~/.cortex/scripts/digest.sh` → `/cortex:digest auto`)
- 用户显式 "digest" / "巩固记忆" / "整合 ledger" / "consolidate"
- 会话内 `/cortex:digest` 走交互模式 (行为同 auto)

## 8 阶段速查表 (顺序严格, 一次跑完)

| # | 阶段 | 行为 | 状态文件 |
|---|---|---|---|
| 1 | 读 (Read) 增量扫 | 读 `.cortex/state/digest.json` cursor; 扫 inbox + log + sessions + L4 中 mtime > cursor; hash 命中 processed_files 则跳 | 读 state/digest.json |
| 2 | 析 (Analyze) 深度 | LLM 深读全文 (非启发式), 抽 4 类候选 (反思/连接/矛盾/决策) + 实体 + 概念 + repo 6 信号归属 | — |
| 3 | 处 (Process) 路由 | 路由 4 类 → 项目/<host>/<org>/<repo>/ 或 收件箱/; 概念/实体 → 领域/<域>/; episodic → L3 | 写新文件 |
| 4 | 维护 | 委派 `Skill(cortex-memory)` 跑维护扫 (整理 / 升级候选 / 补充 / forget / 评分双路调) | cortex-memory 内部 |
| 5 | 整合 (Consolidate) 双向 | **5a** 项目→领域; **5b** 记忆→KB 晋升; **5c** KB→记忆 具化; **5d** 双向 backlink + `_meta/bridge.jsonl` 审计 | 写 state/consolidate.json + bridge.jsonl |
| 6 | 优化 (Enrich) 图表+tags | LLM 判每 md 适合图表 (flow/timeline/mindmap), 注 mermaid; 重抽 tags/aliases (≥3 alias, ≥5 keyword, 中英对) | 写 state/enrich.json |
| 7 | 验证 (Verify) search 多次 | 高 weight 记忆 / 重要 KB 条目 search 多次 (不同关键词组合); 无反链 / 无相似 → frontmatter 标 `verify_issue` | 写 state/verify.json |
| 8 | Evolution + 清理 | sessions pattern 抽取 → patterns.md + proposals; L4 全清 (promote/archive/delete); L3 90d w<0.3 删; 收件箱 ≥30d 复扫 | 写 patterns.md, 清 L4 |

**L0/L1 永不删条目** (硬约束)。L4 单向漏斗。各阶段独立 cursor, 单阶段失败不影响其他。

## 输入参数 (wrapper 注入)

- `--vault <path>` (必须, 由 wrapper 传入)
- `--lang <code>` (可选, 默认 vault `_meta/version.json:lang` 或 zh-CN)
- `--dry-run` (可选, 仅分析不写盘 + state)

**不接受 `--depth` 参数** (硬约束: 默认 deep, 增量游标处理性能, 不降级深度)。

## AUTO_MODE 契约 (硬约束)

**核心原则**: "禁问" ≠ "中止". AI 必须**自决并执行直至任务完成**。遇歧义按推荐默认值; 工具不熟悉则尝试其他工具组合 (Bash/Edit/Write/MCP/Read 既有样本); 禁报"需人工"/"AI 不会"/"建议后续处理"。

### 严禁清单

| # | 禁止 |
|---|------|
| 1 | "修复建议"/"建议"/"推荐操作" 章节/表格/列表 |
| 2 | 用户确认问句 (`需确认?`, `是否执行?`, `要继续吗?`, `ok?`, 末尾问号) |
| 3 | AskUserQuestion 调用 (allowed-tools 已禁) |
| 4 | "下一步"/"后续"/"如需"/"可选" 导引 |
| 5 | "需人工"/"待人工"/"建议人工" 推卸辞令 |
| 6 | "AI 能力不足"/"无法自动" 类借口 |
| 7 | 报状态后停 (除非客观失败: 磁盘只读/权限拒绝/git lock) |

### `/cortex:digest auto` vs `/cortex:digest`

行为一致:
- 跳所有 `AskUserQuestion` (allowed-tools 已禁)
- 8 阶段顺序 + 默认参数 (lookback=7, update-scores=on, dry-run=off)
- 任一阶段失败 → 重试一次, 仍失败 → stderr 报错继续下一阶段, 不中止 pipeline
- 全量跑数小时是预期, **不分批 / 不报 "建议人工"**

## 级别边界速查 (L0-L4)

| level | 边界 | digest 行为 |
|-------|------|------------|
| L0 | 性格/价值观/硬约束, ≤1500c | 仅交叉参照, 永不改 |
| L1 | 技能/稳定语义, ≤5000c | weight bump + append 新例证; L2→L1 候选扫 |
| L2 | 语义, ≤3000c, 365 天时效 | weight bump + append; L3→L2 候选; 365d 未召回且 recall<5 → `archive_pending` |
| L3 | 情节, ≤2000c, 90 天时效 | append; 90d weight<0.3 删; 90d 未召回且 recall<3 → `archive_pending` |
| L4 | ledger/sessions, single-pass | 全清 (promote/archive/delete); freq≥3 自动 L4→L3 |

**独立 cron 仍保留** (digest 不接管破坏性操作):
- `memory-archive` (月度 1st 06:00) — 执行 archive_pending 实际归档
- `memory-compact` (周日 04:00) — L4 ledger gzip
- `memory-warden` (1st/15th 05:00) — 腐化检测

## 评分双路调 (digest 内联)

- **使用信号**: `log10(召回次数 + wikilink 反向引用 + 1) - 0.1 自然衰减` → importance ↑
- **反馈信号**: 用户 "不对/错了" → confidence -= 1.0, "对的/正确" → confidence += 0.5
- 实现: `scripts/cli/lib/evolution.py:update_doc_scores` + digest evolution `--update-scores` 默认开

---

# 阶段详解

每阶段开始读 `.cortex/state/<stage>.json` 拿 cursor + processed_files hash 集; 阶段结束写回累计 stats + 新 cursor。

## 阶段 1 · 读 (Read) 增量扫

**新增数据 (将在阶段 8 清空)**:
- `记忆/L4-流水账/**/*` 任意类型 (md/jsonl/json/yaml/js/ts/sh/py/txt/log) — mtime > `cursors.log_last_date` (首次跑 = 全量)
- `知识库/日记/日/<YYYY-MM>/` mtime > cursor
- `知识库/收件箱/*.md` mtime > `cursors.inbox_last_mtime`

**既有知识 (用于交叉参照 + 学习更新, 永不移除条目)**:
- `记忆/L0-核心/**` · `L1-长期/**` · `L2-中期/**` · `L3-短期/**` 全量索引
- `知识库/领域/**` · `知识库/项目/**` · `知识库/收件箱/**` 全量索引
- `_meta/uri-index.json` · `views/candidates.md` · `views/consolidated/*.md`

**增量跳过**: 计算 sha256, 若 `state/digest.json:processed_files[<rel>].hash` 命中则跳。

**读策略**: jsonl 按行; json/yaml 按结构; 其他按段落。

## 阶段 2 · 析 (Analyze)

LLM 深读全文 (非启发式 keyword 扫), 抽 4 类候选 + 实体 + 概念 + repo 6 信号归属。

### 4 类候选

| 类型 | 触发 |
|---|---|
| 反思 | 含 "?" / "怎么/为何" 段落 |
| 连接 | 同事件类型 ≥ 5 → 抽象为 L2 语义候选; 高频实体 wikilink |
| 矛盾 | 与既有条目矛盾 |
| 决策 | 含 "决定/决策/选择/采纳" 段落 |

### 新增 vs 既有交叉

| 命中 | 标记 |
|---|---|
| 既有 L1/L2/L3 概念 | `update_target` (阶段 3 加深) |
| 既有 知识库/领域 概念 | `enrich_target` (阶段 3 补例/补连) |
| 与既有条目矛盾 | `conflict` (阶段 3 写反思页, 不动既有) |
| 既有疑问页反向链接 ≥ 3 | `concretize` (阶段 8 清理) |

### repo 归属识别 (6 信号)

4 类候选必跑, 任一命中即归属:

| # | 信号 | 强度 | 示例 |
|---|------|------|------|
| 1 | frontmatter `host` / `org` / `repo` 三字段齐 | 强 | `host: github.com, org: anthropics, repo: claude-code` |
| 2 | frontmatter `source_url` 含 repo 模式 | 强 | `github.com/<org>/<repo>` · `gitlab.*/<org>/<repo>` |
| 3 | 正文 wikilink `[[知识库/项目/<host>/<org>/<repo>/...]]` 或 `[[<repo-name>]]` 命中已知 repo | 中 | `[[ccplugin]]` 命中 `知识库/项目/persons/lyxamour/ccplugin/` |
| 4 | 正文含 git URL | 中 | `git@github.com:<org>/<repo>.git` |
| 5 | tag `repo/<name>` · `host/<host>` · `org/<org>` | 中 | `tags: [repo/ccplugin, org/lyxamour]` |
| 6 | 关键词匹配 `<repo-name>` ≥ 3 次 | 弱 | "ccplugin" 在正文出现 ≥3 次 |

识别结果落候选元数据: `route_target = 知识库/项目/<host>/<org>/<repo>/` 或 `route_target = inbox`。多 repo 命中按**强信号优先** (1 > 2 > 3 > 4 > 5 > 6) 选首要, 余者保留为次要 (阶段 3 加 backlink)。

## 阶段 3 · 处 (Process) 路由

### 路由表 (新写, 反思/连接/矛盾/决策 4 类)

| 候选类型 | 命中 repo (`route_target` ≠ inbox) | 未命中 (fallback inbox) |
|---|---|---|
| 反思 | `知识库/项目/<host>/<org>/<repo>/笔记/<YYYY-MM-DD>-反思-<topic>.md` | `知识库/日记/日/<YYYY-MM>/<YYYY-MM-DD>-反思-<topic>.md` |
| 连接 | a/b 同 repo: `知识库/项目/<repo>/笔记/<YYYY-MM-DD>-连接-<a-b>.md`; 跨 repo: 落 a 端 (首要), b 端写 backlink | `知识库/收件箱/<date>-连接-<a-b>.md` |
| 矛盾 | `知识库/项目/<repo>/笔记/<YYYY-MM-DD>-矛盾-<topic>.md` (frontmatter 列既有条目 path) | `知识库/收件箱/<date>-矛盾-<topic>.md` |
| 决策 | `知识库/项目/<repo>/主题/决策.md` append 新段 (文件不存在则新建) | `知识库/收件箱/<date>-决策-<topic>.md` |

其他新写:
- `记忆/views/consolidated/<YYYY-MM-DD>.md` 当日摘要
- 概念候选 → `记忆/views/candidates.md` (待 cortex-promote 审批)

### Fallback 规则

- **多 repo 候选**: 路由首要 repo, 其他 repo 各加 backlink 兜底
- **repo 目录不存在**: 自动 `mkdir -p` + 若 `_index.md` 不存在则建 minimal stub (5 字段 + 1 行说明)
- **笔记目录不存在**: 自动 `mkdir -p`
- **弱信号防误判**: 信号 6 (keyword) 单独命中且无其他强信号 → 不路由, 留 inbox

### 更新既有 (学习 + 完善, 不删原文)

- `update_target` (L1/L2/L3 命中) → `bash ~/.cortex/scripts/memory.sh write --uri <u> --content <c> --level <l>` append 新例证/新连接, weight += 0.05 (cap 1.0)
- `enrich_target` (知识库/领域 命中) → patch 文件追加 `## 新增例证 <YYYY-MM-DD>` + 加 `[[wikilink]]`
- `conflict` → 新建 `知识库/收件箱/<date>-矛盾-<topic>.md` 列对照 (不动既有)

## 阶段 4 · 维护 (Maintenance)

### 4a. 知识库引用

- 更新 `index.md` / `hot.md` 引用 (新生 consolidated/reflection 加入索引)

### 4b. 委派 cortex-memory 跑维护扫

调 `Skill(cortex-memory)` 无 verb (默认维护扫), digest 不重复维护逻辑:

1. 整理: uri-index 重建 + frontmatter 校验 + URI 唯一性
2. 升级候选: L4→L3 自动 (freq ≥ 3) + L3→L2 / L2→L1 / L1→L0 候选写 `记忆/views/candidates.md`
3. 补充 (enrich): 弱条目 (weight < 0.3 / examples=0) 交叉引用 + sessions 例证 append
4. forget 标记 (非破坏): L3 90d / L2 365d 未召回 → frontmatter `archive_pending: true`
5. 评分双路调: 召回 + wikilink 反链 → `importance ↑`; 用户反馈 → `confidence ↑↓`

cortex-memory 输出 stats JSON 合并到 digest `updated` 字段。

> 实际归档由独立 cron 执行; digest 不接管这三类破坏性操作。

## 阶段 5 · 整合 (Consolidate) — 双向

读 `state/consolidate.json` cursor + processed_{files,memories,kb_for_memory} hash 三组。

### 5a. 项目 → 领域 (KB 内提炼)

把 `知识库/项目/<host>/<org>/<repo>/**` 内**通用概念** (跨项目可复用的技术/方法/模式) 抽到 `知识库/领域/<域>/`, 项目层只留**项目专属事实**。

**算法**:

```
for each md in 知识库/项目/**:
  if hash in processed_files: skip
  LLM 深读 md → [{name, aliases, definition, examples, type: concept|method|pattern|fact}]
  filter: type == fact → 跳 (留项目层)
  for each concept:
    domain = decide_domain(concept)
    既有 = search 知识库/领域/<domain>/ by name + aliases
    if 既有 命中:
      patch 既有: append "## 例证 <YYYY-MM-DD>" + 项目 backlink
      若定义不一致: 落 知识库/收件箱/<date>-矛盾-<concept>.md
    else:
      新建 知识库/领域/<domain>/<concept-slug>.md
  写 hash 到 state/consolidate.json:processed_files
```

**域名决策** (decide_domain):
1. `config/digest.yaml:domain_aliases.<concept_kw>` 强映射命中 → 取映射值
2. concept frontmatter / tags 含 `domain: <x>` → 取 x
3. LLM 自决: 候选域 = `[技术, 创作, 学习, 工作, 生活, 金融, 未分类]` + vault 已存在的 `知识库/领域/<域>/` 目录名

未分类降级: LLM 不确定时归 `未分类/`, 不强分。

**合并冲突处理** (与既有概念**定义对立** / score 差 ≥ 2 / aliases 完全不交):
1. 不动既有文件
2. 落 `知识库/收件箱/<YYYY-MM-DD>-矛盾-<concept>.md`, frontmatter `type: conflict` / `concept` / `existing` / `new_source`
3. body 列对照表 (既有 vs 新, 含出处)
4. 累加 `consolidate.conflicts_recorded`

**合并 (非冲突)**:
1. patch 既有文件: 文末 append `## 例证 <YYYY-MM-DD>` + 项目 backlink
2. `examples_count += 1` / `sources` 数组 append 项目相对路径 (去重)
3. weight bump: `importance += 0.05` (cap 10.0)

### 5b. 记忆 → 知识库 (晋升)

**触发条件** (AND):
- 记忆 level ∈ {L1, L2}
- `weight ≥ 0.7` AND `recall_count ≥ 5` (config: `digest.yaml:memory_to_kb.weight_threshold` / `recall_threshold`)
- frontmatter 不含 `kb_promoted: true`
- 记忆 type ∈ {`semantic`, `skill`, `decision`, `principle`} (排除纯 `episodic`)

**算法**:

```
for each memory in 记忆/L1-长期/** ∪ 记忆/L2-中期/**:
  if hash in state/consolidate.json:processed_memories: skip
  if 不满足触发条件: skip

  LLM 抽提稳定语义为领域概念:
    {name, aliases ≥3, definition, examples, suggested_domain,
     confidence_inherited: memory.confidence}

  domain = decide_domain(concept)   # 复用 5a 同一函数
  既有 = search 知识库/领域/<domain>/ by name + aliases
  if 既有:
    patch 既有: append "## 例证 (来自记忆 <date>)" + 记忆 wikilink
    既有 frontmatter `sources` append `[[记忆/...]]` (去重)
  else:
    新建 知识库/领域/<domain>/<concept-slug>.md
    frontmatter:
      type: concept / domain: <x>
      sources: [[[记忆/L1-长期/<slug>]]]
      score: min(7.0, memory.weight × 10)
      confidence: memory.confidence
      promoted_from_memory: <memory_uri>
      promoted_at: <YYYY-MM-DD>

  回写 memory frontmatter: kb_promoted: true / kb_target: <new_kb_path>
  审计 append _meta/bridge.jsonl
```

### 5c. 知识库 → 记忆 (具化)

**触发条件** (AND):
- 知识库 路径在 `知识库/领域/**`
- frontmatter `score ≥ 7` AND `importance ≥ 7`
- 反向 wikilink 引用次数 ≥ 3 (从 ledger / sessions 命中)
- 不存在对应 memory (即 `_meta/uri-index.json` 中无 `memory:` URI 指向同 concept)
- concept type ∈ {`method`, `pattern`, `principle`}

**算法**:

```
for each kb in 知识库/领域/**:
  if hash in state/consolidate.json:processed_kb_for_memory: skip
  if 不满足触发条件: skip

  level = decide_level(kb):
    type == principle and importance ≥ 9 → L1
    type in {method, pattern} → L2
    else → 不具化 (skip)

  新建 记忆/<level>/<slug>.md
  frontmatter:
    type: <kb.type>  (method/pattern/principle 映射 skill/skill/principle)
    weight: min(0.9, kb.score / 10)
    confidence: kb.confidence
    importance: kb.importance
    materialized_from_kb: <kb_path>
    materialized_at: <YYYY-MM-DD>
    aliases: kb.aliases
  body: 浓缩 kb 定义 + 1-2 操作要点 (LLM 抽提, L1 ≤1500c, L2 ≤3000c)

  回写 kb frontmatter: memory_materialized: true / memory_target: <memory_uri>
  审计 append _meta/bridge.jsonl
```

### 5d. 双向 backlink 同步 + 审计

**backlink 段维护**:

扫 5a/5b/5c 本轮新生/patch 的所有文件 + 凡 frontmatter 含 `sources` / `promoted_from_memory` / `materialized_from_kb` / `kb_target` / `memory_target` 的文件:

```
for each pair (A, B) where A 引用 B (通过上述任一字段):
  确保 B 文件底部 ## Backlinks 段含 [[A]] wikilink
  缺则 append, 已有则跳
```

**审计落痕** (`_meta/bridge.jsonl`):

每次 5b/5c 转换写一行:

```json
{"ts":"<ISO>","kind":"memory_to_kb","src":"<memory_uri>","dst":"<kb_path>","action":"created|patched","domain":"<x>","concept":"<name>","score":<N>}
{"ts":"<ISO>","kind":"kb_to_memory","src":"<kb_path>","dst":"<memory_uri>","action":"created","level":"L1|L2","weight":<N>}
```

用途: 回滚 (按 ts+src+dst 反查) / evolution (高频转换 → patterns.md) / verify (stage 7 跨参找未同步 backlink)。

### 5e. 配置 (`vault/.cortex/config/digest.yaml`)

```yaml
memory_to_kb:
  enabled: true
  weight_threshold: 0.7
  recall_threshold: 5
  allowed_types: [semantic, skill, decision, principle]

kb_to_memory:
  enabled: true
  score_threshold: 7
  importance_threshold: 7
  backref_threshold: 3
  allowed_types: [method, pattern, principle]
  level_rules:
    principle_to_L1_min_importance: 9
    method_pattern_default_level: L2
```

任一 `enabled: false` 跳过该子阶段。

### 5f. 错误 / 桥的硬约束

- L0 永不参与桥的两侧 (硬约束)
- 5b/5c 任一 LLM 调用失败 → 重试 1 次, 仍失败跳该文件, 不写 hash
- backlink 同步发现循环引用 (A↔B 互链已存在) → 跳过, 计 `backlinks_already_synced`
- bridge.jsonl 写盘失败 → 不阻塞 pipeline, stderr 报错
- `kb_promoted: true` 但 `kb_target` 路径不存在 → 标 `verify_issue: broken_promotion` (stage 7 捕获)

## 阶段 6 · 优化 (Enrich) — 图表 + tags/aliases

LLM 判每 md 适合的图表类型, 注 mermaid 块; 重抽 tags/aliases (中英对) 补 frontmatter。

### 输入

- state: `vault/.cortex/state/enrich.json`
- 扫描范围: vault 内全部 md, **排除** 以下路径:
  - `_meta/**` · `_templates/**` · `_assets/**` · `.cortex/**`
  - `归档/**` · `.obsidian/**` · `.trash/**` · `仪表盘/**`
  - frontmatter `enrich: false` 标记的单文件

### 算法

```
for each md not in skip_paths:
  if hash in processed_files: skip
  LLM 读 md → {mermaid_type, mermaid_block, aliases, keywords, reason}
  if mermaid_type != none AND mermaid_type in config.mermaid_whitelist:
    inject mermaid block (frontmatter 后, 正文前)
  merge aliases / keywords 到 frontmatter (去重, 既有优先)
  写 hash 到 state/enrich.json
```

### mermaid 类型判定

| 适合 | 内容特征 |
|---|---|
| `flowchart` | 含步骤序列 / 决策分支 / "→" / "if/then" |
| `timeline` | 含日期序列 / 历史事件 / "<YYYY>" 多次出现 |
| `mindmap` | 概念列表 + 子项嵌套, 无明显时序 |
| `table` | 已有对比项 — 谨慎用 (mermaid 不一定胜过 md table) |
| `none` | 纯叙述 / 短笔记 / 已含图表 — 跳 |

config 白名单 `enrich.yaml:mermaid_whitelist` (默认 `[flowchart, timeline, mindmap]`) 控制可注入。

### 注入位置 + 格式

```markdown
---
<frontmatter>
---

## 关系图

```mermaid
<生成的 mermaid 源>
```

<原正文 (不动)>
```

**硬约束**:
- 不动原正文一行
- 已存在 `## 关系图` / 已含 mermaid fence → 跳过
- mermaid 源 ≤ 30 行, 节点 ≤ 20 (超出降级为 mindmap 或 none)

### tags / aliases 重抽

- aliases: ≥3, 中英对 (例 `["事件驱动", "event-driven", "EDA"]`)
- keywords: ≥5, 同概念不同表达
- 合并: 既有 `aliases` / `tags` 保留; 新候选 append (去重, case-insensitive); `config/tags.yaml:alias_synonyms` 同义词归一
- 上限: aliases ≤ 10, tags ≤ 15

### 跳过条件

| 条件 | 行为 |
|---|---|
| 路径在 skip_paths | 不读不写 |
| frontmatter `enrich: false` | 不读不写 |
| `type: dashboard` / `type: meta` | 跳 mermaid 注入, 仍重抽 tags |
| md < 200 字 | 跳 mermaid, 仍重抽 tags |
| 已含 `## 关系图` 或 mermaid fence | 跳 mermaid 注入 |

### 失败 / 回滚

- mermaid 注入后简单语法 lint 验证 — 失败则不注入, stderr 报 warn
- tags/aliases merge 失败 (frontmatter 解析坏) → 跳该文件, 不写 hash
- 单文件失败不中止阶段

## 阶段 7 · 验证 (Verify) — search 多次交叉

对高 weight 记忆 / 重要 KB 条目, 用多组关键词跑 search, 检测 orphan / 冲突 / 反向无引用, 落 `verify_issue` frontmatter 标记 (非破坏)。

### 输入

- state: `vault/.cortex/state/verify.json`
- 扫描范围 (二选一即纳入):
  - **高 weight 记忆**: `记忆/L1-长期/**` · `L2-中期/**` 中 `weight ≥ 0.7` 或 `importance ≥ 7`
  - **重要知识库**: `知识库/领域/**` 中 `score ≥ 7` 或 `importance ≥ 7`

### 算法

```
for each entry in scan_targets:
  if hash in processed_files: skip
  kw_combos = build_keyword_combos(entry)   # 3-5 组
  results = []
  for combo in kw_combos:
    r = search(combo, scope="vault")        # 优先 mcp__obsidian__obsidian_simple_search
    results.append((combo, r))
  issue = diagnose(entry, results)
  if issue:
    patch frontmatter: verify_issue: <issue>, verify_checked_at: <UTC>
  写 hash 到 state/verify.json
```

### keyword combo 构造

- combo 1: concept name (规范名)
- combo 2: 主要 alias (frontmatter `aliases[0]`)
- combo 3: name + 首个 tag (AND)
- combo 4 (可选): 英文 alias 单独
- combo 5 (可选): 反向 — 用 entry 内容中高频实体反查

### diagnose 规则

| 条件 | issue |
|---|---|
| 5 combo 全部无反向链接 (`[[<entry_name>]]` 引用本条) | `orphan` |
| 命中同名 / 同 alias 概念但 score 差 ≥ 3 或 definition LLM 判矛盾 | `conflict_<conflicting_path>` |
| 仅自身命中 (search 结果只有 entry 自己) | `no_backlink` |
| 无问题 | (不写 verify_issue, 清除既有 verify_issue 字段) |

多 issue 时优先级: `conflict > orphan > no_backlink`。

### frontmatter patch

```yaml
verify_issue: orphan   # 或 conflict_<path> 或 no_backlink
verify_checked_at: <UTC ISO>
verify_combos: 5
```

正常情况 (无 issue) 也写 `verify_checked_at` 但不写 verify_issue, 同时**删除**既有 verify_issue 字段 (修复后清标)。

### search 工具优先级

1. `mcp__obsidian__obsidian_simple_search`
2. `mcp__obsidian__obsidian_complex_search` (combo 含 tag 限定时)
3. `bash ~/.cortex/scripts/search.sh <query>` (MCP 不可达)
4. ripgrep (`rg -l "<term>" <vault>`) — 兜底

### 问题分级

| issue | 严重度 | 建议处理 |
|---|---|---|
| `conflict_*` | 高 | 人工审, 落收件箱矛盾页 |
| `orphan` | 中 | digest 下次跑 enrich 尝试加 backlink |
| `no_backlink` | 低 | 自然现象, 多跑几次会自然补 |

**digest 本阶段不自动修复 issue** — 仅标记, 留给后续阶段或人工。

## 阶段 8 · Evolution + 清理

### 8a. Evolution

调 `bash ~/.cortex/scripts/digest.sh evolution --lookback-days 7 --json` (直 exec python CLI), 输出 JSON 含 `sessions_scanned` / `patterns_candidates` / `patterns_added` / `patterns_updated` / `proposals_generated`。

**proposal 阈值**: `confidence ≥ 0.8 AND applications ≥ 3` 才生。反写 SKILL/AGENT **不在 digest 内自动执行** — 仅生 proposal 列表, 用户调 cortex-refactor `evolution-apply` 单独消化。

#### 6 Category

| category | 含义 | 触发关键词 |
|----------|------|------------|
| `vault-write-contract` | vault 写契约违反 (没走 MCP) | `mcp__obsidian` / `vault 写` / `write 工具` |
| `ingest-failure` | ingest 失败模式 | `ingest` / `摄取` / `WebFetch` / `defuddle` |
| `digest-routing` | digest 路由翻车 | `digest` / `路由` / `routing` / `归属` |
| `skill-trigger` | skill 错触发 / 漏触发 (兜底) | `skill` / `触发` / `trigger` |
| `frontmatter-schema` | fm schema 缺字段 | `frontmatter` / `fm-` / `schema` |
| `user-correction` | 用户纠正模式 | (由 negative tokens 路由) |

#### Pattern Signature 抽取

1. 遍历 jsonl entries, 按角色拆 `prev_assistant` / `user_text`
2. 若 `user_text` 命中 `NEGATIVE_FEEDBACK_TOKENS` (`不对` / `不是` / `应该是` / `改成` / `错了` / `wrong` / `incorrect` / `that's not` / `no, `), signature = `prev_assistant[:200] + " | " + user_text[:200]`, 标 `is_negative=True`
3. 否则 signature = `user_text[:300]`
4. `signature_key` 归一化: 切词 → 取前 8 token → 排序 → `<category>|<tokens>`, 截 200 字符
5. bucket key: `(category, signature_key)` 聚合, applications = unique sessions count

#### Confidence 公式

- `is_negative` (含纠正语) → base = 0.9
- 其他 → base = 0.5 + 0.05 × applications (上限 +0.4)
- 最终 confidence = `min(1.0, base)`, 2 位小数

#### 阈值 (硬编码 D4)

- `MIN_APPLICATIONS = 3` / `MIN_CONFIDENCE = 0.8`

不暴露 `_meta/version.json` 配置 (D4 锁定, 调阈值需改代码重发布)。

#### patterns.md Schema

`记忆/L0-核心/patterns.md` (D1 single markdown), 多 section 按 category, 每 pattern 为 `### pat-<date>-<sha6> <name>` 三级标题 + yaml fence + 4 字段 (Pattern / Problem / Solution / Sources)。

更新策略:
- 既有同 id pattern → applications 取 `max(old+1, new)`, confidence 取 max, updated=today; 原 section 删除, 新 section append 到 category 末尾
- 新 pattern → append 到对应 category section, 替换占位 `(空)`
- 首次跑 patterns.md 不存在 → 创建 6 category 空骨架后填入

#### Proposal Schema

`_assets/evolution-proposals/<YYYY-MM-DD>-<slug>.md`:

```yaml
---
pattern_id: pat-2026-05-14-abc123
target_skill: skills/cortex-save/SKILL.md
target_section: (reviewer to fill)
confidence: 0.85
applications: 5
category: vault-write-contract
sources:
  - 记忆/L4-流水账/sessions/claude-code/2026/05/13/abc.jsonl
---
```

target_skill 由 category 推断:

| category | target_skills |
|----------|---------------|
| vault-write-contract | `skills/cortex-save/SKILL.md`, `AGENT.md` |
| ingest-failure | `skills/cortex-ingest/SKILL.md` |
| digest-routing | `skills/cortex-digest/SKILL.md` |
| skill-trigger | `AGENT.md` |
| frontmatter-schema | `skills/cortex-save/SKILL.md`, `skills/cortex-lint/SKILL.md` |
| user-correction | `AGENT.md` |

#### Evolution 安全门 (PR4 范围)

PR3 仅生 proposal markdown, **不实际 patch SKILL/AGENT**。PR4 patch 流程强制:
- patch 前 `cd plugins/tools/cortex && git status --porcelain` 必须为空, 否则拒绝
- patch target 仅限 `skills/**/SKILL.md` 或 `AGENT.md`, 禁 `commands/*.md` / `scripts/**/*.py` / `*.sh`
- AskUserQuestion 弹窗 (options: `接受 patch` / `拒绝 patch`); 拒绝则保留 proposal 不动 SKILL

### 8b. 清理 + 归档

- **L4-流水账强制全清** (无时间窗例外, 单向漏斗): 阶段 1 读取的每个 L4 文件必须出 L4 (三选一):
  - **升 L3**: 高频/概念化潜力 → `bash ~/.cortex/scripts/memory.sh promote --uri <u> --target-level L3`
  - **归档**: 历史价值无升级潜力 → mv 到 `归档/L4-<YYYY>/<原相对路径>`
  - **删**: 无价值 (debug 噪音/纯重复/已聚合) → `git rm`
  - 处理后 `记忆/L4-流水账/**` 必须 0 文件残留
- **L3-短期**: 删 > 90 天且 weight < 0.3
- **知识库/收件箱**: 已被概念化 (反向链接 ≥ 3) 的疑问/连接条目 → 删
- **收件箱 ≥30 天复扫识别 (强制)**: 对 `知识库/收件箱/` 内 mtime ≥ 30 天文件逐一重跑阶段 2 repo 识别 6 信号 — 命中则迁移到 `知识库/项目/<host>/<org>/<repo>/笔记/`, 仍无命中则归档季度桶 `归档/收件箱-<YYYY-QN>.md` (append, idempotent), 处理后该批 0 残留
- **知识库/日记/日**: > 7 天文件转存 `归档/日记/<YYYY-QN>.md` (累积季度桶, idempotent)
- **不动** `记忆/L0-核心` / `L1-长期` 条目 (仅 weight bump 由阶段 3 update_target 处理)

#### Evolution 调用入口

```bash
bash ~/.cortex/scripts/digest.sh evolution --lookback-days 7 --json
# 直 exec: python3 scripts/cli/digest.py evolution --lookback-days 7 --json
```

CLI 选项:
- `--lookback-days N` — 扫描天数 (默认 7)
- `--vault PATH` — 覆盖 vault 路径
- `--dry-run` — 仅扫不写盘
- `--compact` — compact JSON (单行)

#### evolution 输入

`记忆/L4-流水账/sessions/<cli>/<YYYY>/<MM>/<DD>/*.jsonl` 近 `lookback_days` 天。jsonl 格式兼容: 单行 JSON 对象, 含 `role`+`content` 或嵌套 `{"message": {"role", "content"}}`; `content` 支持 string 或 Anthropic-style content blocks list。

---

# 状态与配置

## State 文件目录

```
<vault>/.cortex/state/
├── digest.json        # 阶段 1 读 + 整体 last_run
├── consolidate.json   # 阶段 5 双向整合 (5a 项目→领域 / 5b 记忆→KB / 5c KB→记忆 / 5d backlink+audit)
├── enrich.json        # 阶段 6 md 图表/tags 优化
└── verify.json        # 阶段 7 search 多次验证
```

是否 commit: 用户自决。推荐**不 commit** state/ (runtime 状态, 每机器独立), commit config/。

## State Schema (统一)

```json
{
  "schema_version": 1,
  "last_run": "<UTC ISO>",
  "processed_files": {
    "<rel_path_from_vault_root>": {
      "hash": "<sha256 hex>",
      "mtime": "<UTC ISO>",
      "phase": "<stage_name>"
    }
  },
  "cursors": {
    "inbox_last_mtime": "<UTC ISO>",
    "log_last_date": "<YYYY-MM-DD>",
    "session_last_id": "<id>",
    "last_repo_path": "<rel path of last processed repo>"
  },
  "stats": {
    "<阶段名>": <int>
  }
}
```

### state/consolidate.json 扩展 (5b/5c)

```json
{
  "processed_files": {...},          // 5a 项目 md
  "processed_memories": {...},       // 5b 记忆 md hash
  "processed_kb_for_memory": {...},  // 5c 领域 md hash
  "cursors": {
    "last_repo_path": "...",         // 5a
    "last_memory_path": "...",       // 5b
    "last_kb_path": "..."            // 5c
  }
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `schema_version` | int | 是 | 当前 1; migration 时 +1 |
| `last_run` | UTC ISO | 是 | null = 从未跑 |
| `processed_files` | dict | 是 | key=vault 相对路径, value={hash,mtime,phase} |
| `cursors` | dict | 是 | 各类 mtime/id 游标; null = 全量 |
| `stats` | dict | 是 | 累计计数 (跨多次跑) |

### 阶段 cursor 字段映射

| 阶段 | state 文件 | 主要 cursor 字段 |
|---|---|---|
| 1 读 | digest.json | `inbox_last_mtime` / `log_last_date` / `session_last_id` |
| 5 整合 | consolidate.json | `last_repo_path` (5a) / `last_memory_path` (5b) / `last_kb_path` (5c) |
| 6 优化 | enrich.json | `processed_files` (hash-based) |
| 7 验证 | verify.json | `processed_files` (hash-based) |

## 配置文件 (`vault/.cortex/config/`)

- `digest.yaml` — 各阶段开关 (consolidate/enrich/verify) + 增量失效阈值 + 域名强映射 + memory_to_kb / kb_to_memory 桥阈值
- `enrich.yaml` — mermaid 类型白名单 + 跳过路径
- `tags.yaml` — tag 命名约定 + alias 同义词表

缺省 (文件不存在 / 字段缺) 按 skill 默认值跑。

## 增量游标失效 / 重置

| 条件 | 行为 |
|---|---|
| `last_run` > 30 天 | 清 processed_files, 全量重处理 (cursors 保留作为窗口下限) |
| `schema_version` 高于代码已知 | stderr 报 warn, 按代码已知 schema 读 (forward compat) |
| 单文件 hash 在 state 但实际文件已删 | 阶段结束扫一遍 `processed_files` keys, 删不存在的 entry (GC) |
| JSON 损坏 | stderr 报 warn, 备份到 `<file>.corrupt.<timestamp>`, 重建空骨架 |

## 读写规约

**读 (阶段开头)**:
1. 文件不存在 → 初始化空骨架 (`schema_version: 1`, `last_run: null`, `processed_files: {}`, `cursors: {}`, `stats: {}`), 视为首次跑
2. JSON 损坏 → 备份 + 重建空骨架
3. `state.last_run` 距今 > `incremental_max_age_days` (config, 默认 30) → 视为首次跑, **清空 processed_files**, 全量重处理

**写 (阶段结尾)**:
1. 阶段成功 → 更新 `last_run`, append `processed_files`, 更新 `cursors`, `stats.<阶段> += <new>`
2. 阶段失败 (重试 1 次仍失败) → 不写 cursor, **不写 processed_files** (下次跑重处理), 仅累加 `stats.<阶段>_failures`
3. 原子写: 先写 `<file>.tmp`, fsync, mv 替换原文件
4. 并发: 配合 `cron run.sh` flock; skill 内多阶段并发用 file_lock per file

## 阶段间数据流

- 阶段 1 输出文件清单 → 阶段 2 输入
- 阶段 2 输出候选 → 阶段 3 路由
- 阶段 3 写盘 → 阶段 5/6 扫描时纳入
- 阶段 4 维护扫并发于 5-7 (cortex-memory 独立 IO, 不抢锁)
- 阶段 5/6/7 各自独立 state, 互不依赖 (单个失败不影响他者)
- 阶段 8 evolution 输入 L4 sessions (清理前快照), 清理在 8b 紧随其后

## 错误处理

- ledger 行 JSON 解析失败 → 跳过该行, 末尾汇总 invalid_lines count
- session 文件 frontmatter 缺失 → 视为纯文本仅参与 entity 提取
- `views/candidates.md` 不存在 → 自动创建空骨架
- `.cortex/state/<stage>.json` 不存在 / JSON 损坏 → 视为首次跑, 全量重处理 + 重建 state
- `state.last_run` 距今 > `incremental_max_age_days` (默认 30) → 视为首次跑, 全量重处理
- 写盘并发冲突 → 配合 file_lock (cron run.sh 已提供 flock)
- write 失败 → 重试一次, 仍失败则 stderr 报错并继续下一目标 (不中止 pipeline)
- 单阶段 (5/6/7) 失败 → 重试 1 次, 仍失败 stderr 报错继续下一阶段, 该 stage state 不更新 cursor

---

# 输出 JSON Schema (compact)

```json
{
  "date": "<YYYY-MM-DD>",
  "incremental": {
    "state_age_days": <N>, "reset_to_full": <bool>,
    "skipped_by_hash": {"read": <N>, "consolidate": <N>, "enrich": <N>, "verify": <N>}
  },
  "read": {
    "ledger": <N>, "sessions": <N>, "logs": <N>, "inbox": <N>, "l4_other": <N>,
    "existing_L0": <N>, "existing_L1": <N>, "existing_L2": <N>, "existing_L3": <N>, "existing_kb": <N>
  },
  "analyzed": {
    "patterns": <N>, "entities": <N>, "decisions": <N>, "questions": <N>,
    "update_targets": <N>, "enrich_targets": <N>, "conflicts": <N>, "concretize_targets": <N>
  },
  "written": {
    "consolidated": "<path>", "candidates": <N>, "reflection": <N>, "connection": <N>, "conflict": <N>
  },
  "updated": {
    "uri_index": <N>, "L4_to_L3": <N>,
    "L1_enriched": <N>, "L2_enriched": <N>, "L3_enriched": <N>, "kb_enriched": <N>, "weights_bumped": <N>,
    "promote_candidates_L3_to_L2": <N>, "promote_candidates_L2_to_L1": <N>, "promote_candidates_L1_to_L0": <N>,
    "forget_marked_L2": <N>, "forget_marked_L3": <N>
  },
  "consolidate": {
    "scanned": <N>, "concepts_extracted": <N>, "domain_created": <N>, "domain_enriched": <N>, "conflicts_recorded": <N>,
    "memory_to_kb_promoted": <N>, "memory_to_kb_skipped_threshold": <N>,
    "kb_to_memory_materialized": <N>, "kb_to_memory_skipped_exists": <N>,
    "backlinks_synced": <N>, "bridge_audit_rows": <N>
  },
  "enrich": {
    "scanned": <N>, "mermaid_injected": <N>, "tags_updated": <N>, "aliases_updated": <N>, "skipped_path": <N>
  },
  "verify": {
    "scanned": <N>, "issues_orphan": <N>, "issues_conflict": <N>, "issues_no_backlink": <N>, "issues_cleared": <N>
  },
  "evolution": {
    "sessions_scanned": <N>, "patterns_added": <N>, "patterns_updated": <N>,
    "proposals_generated": ["<path>"]
  },
  "cleaned": {
    "l4_promoted": <N>, "l4_archived": <N>, "l4_deleted": <N>,
    "L3_purged": <N>, "questions_purged": <N>,
    "inbox_classified": <N>, "inbox_archived": <N>, "inbox_deleted": <N>
  }
}
```

---

# 调度

- 每日 03:00 cron 自动跑 `~/.cortex/scripts/digest.sh` (wrapper) → `/cortex:digest auto` (slash) → 本 skill
- 用户手动: `bash ~/.cortex/scripts/digest.sh` 或会话内 `/cortex:digest`
- evolution 单独跑: `bash ~/.cortex/scripts/digest.sh evolution --lookback-days 7 --json` (直调 python CLI, 不走 claude session)
