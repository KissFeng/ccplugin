# Memory ↔ KB Bridge — 阶段 5b/5c/5d 详细规范

> cortex-digest 阶段 5 双向整合的子流程: **记忆 ↔ 知识库** 跨域转换 + backlink 同步 + 审计落痕。
> 阶段 5a (项目→领域) 见 [consolidate.md](consolidate.md)。

## 为什么要桥

| 现状 | 缺口 |
|---|---|
| Stage 4: 仅记忆内 L4→L3→L2→L1→L0 候选 | 记忆里沉淀的稳定语义/决策 **不会** 反哺到 `知识库/领域/` |
| Stage 5a: 仅 `知识库/项目/` → `知识库/领域/` | `知识库/领域/` 中高频被召回的概念 **不会** 具化成 operator 记忆 |
| 两侧 wikilink **单向** | 跨域 backlink 段不维护, 反向引用易腐化 |

桥的目标: **记忆 ↔ 知识库 双向流动 + 审计可回溯**。

## 5b. 记忆 → 知识库 (晋升 / promote-to-kb)

**触发条件** (AND):
- 记忆 level ∈ {L1, L2} (L0 永不动条目, L3/L4 太短未稳)
- `weight ≥ 0.7` AND `recall_count ≥ 5` (config: `digest.yaml:memory_to_kb.weight_threshold` / `recall_threshold`)
- frontmatter 不含 `kb_promoted: true` (已晋升过的不重做)
- 记忆 type ∈ {`semantic`, `skill`, `decision`, `principle`} (排除纯 `episodic`)

**算法**:

```
for each memory in 记忆/L1-长期/** ∪ 记忆/L2-中期/**:
  if hash in state/consolidate.json:processed_memories: skip
  if not (weight ≥ 0.7 and recall_count ≥ 5): skip
  if memory.fm.kb_promoted: skip
  if memory.fm.type not in {semantic, skill, decision, principle}: skip

  LLM 抽提: 把记忆中的稳定语义/方法/决策表达为**领域概念**:
    {name, aliases ≥3, definition, examples, suggested_domain, confidence_inherited: memory.confidence}

  domain = decide_domain(concept) (复用 5a 同一函数)
  既有 = search 知识库/领域/<domain>/ by name + aliases
  if 既有:
    patch 既有: append "## 例证 (来自记忆 <date>)" + 记忆 wikilink
    既有 frontmatter `sources` append `[[记忆/...]]` (去重)
  else:
    新建 知识库/领域/<domain>/<concept-slug>.md
    frontmatter:
      type: concept
      domain: <x>
      sources: [[[记忆/L1-长期/<slug>]]]
      score: min(7.0, memory.weight × 10)   # 继承记忆权重
      confidence: memory.confidence
      promoted_from_memory: <memory_uri>
      promoted_at: <YYYY-MM-DD>

  写回 memory 自身: frontmatter `kb_promoted: true` + `kb_target: <new_kb_path>`
  审计: append _meta/bridge.jsonl 一行 (见 §5d)
```

**统计**: `consolidate.memory_to_kb_promoted`

## 5c. 知识库 → 记忆 (具化 / materialize-to-memory)

**触发条件** (AND):
- 知识库 路径在 `知识库/领域/**`
- frontmatter `score ≥ 7` AND `importance ≥ 7`
- 反向 wikilink 引用次数 ≥ 3 (从 ledger / sessions 命中)
- 不存在对应 memory (即 `_meta/uri-index.json` 中无 `memory:` URI 指向同 concept)
- concept type ∈ {`method`, `pattern`, `principle`} (`concept`/`fact` 不具化)

**算法**:

```
for each kb in 知识库/领域/**:
  if hash in state/consolidate.json:processed_kb_for_memory: skip
  if not (score ≥ 7 and importance ≥ 7 and backref_count ≥ 3): skip
  if kb.fm.type not in {method, pattern, principle}: skip
  if exists memory with same concept: skip

  level = decide_level(kb):
    type == principle and importance ≥ 9 → L1
    type in {method, pattern} → L2
    else → 不具化 (skip)

  新建 记忆/<level>/<slug>.md
  frontmatter:
    type: <kb.type>  # method/pattern/principle 映射 skill/skill/principle
    weight: min(0.9, kb.score / 10)
    confidence: kb.confidence
    importance: kb.importance
    materialized_from_kb: <kb_path>
    materialized_at: <YYYY-MM-DD>
    aliases: kb.aliases
  body: 浓缩 kb 定义 + 1-2 操作要点 (LLM 抽提, ≤ 1500c for L1, ≤ 3000c for L2)

  写回 kb 自身: frontmatter `memory_materialized: true` + `memory_target: <memory_uri>`
  审计: append _meta/bridge.jsonl
```

**统计**: `consolidate.kb_to_memory_materialized`

## 5d. 双向 backlink 同步 + 审计

**5d-1 backlink 段维护**:

扫 5b/5c 本轮新生/patch 的所有文件 + 凡 frontmatter 含 `sources` / `promoted_from_memory` / `materialized_from_kb` / `kb_target` / `memory_target` 的文件:

```
for each pair (A, B) where A 引用 B (通过上述任一字段):
  确保 B 文件底部 ## Backlinks 段含 [[A]] wikilink
  缺则 append, 已有则跳
  保持顺序: 新加的追加在 ## Backlinks 列表末尾
```

**统计**: `consolidate.backlinks_synced`

**5d-2 审计落痕 (`_meta/bridge.jsonl`)**:

每次 5b/5c 转换写一行:

```json
{"ts":"<ISO>","kind":"memory_to_kb","src":"<memory_uri>","dst":"<kb_path>","action":"created|patched","domain":"<x>","concept":"<name>","score":<N>}
{"ts":"<ISO>","kind":"kb_to_memory","src":"<kb_path>","dst":"<memory_uri>","action":"created","level":"L1|L2","weight":<N>}
```

用途:
- 回滚: 用户发现错误转换, 按 ts + src + dst 反查
- evolution: 高频转换路径 → patterns.md 候选
- verify: stage 7 跨参 bridge.jsonl 找未同步的 backlink

## 配置 (`vault/.cortex/config/digest.yaml`)

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

## 增量游标 (state/consolidate.json 扩展)

```json
{
  "processed_files": {...},        // 5a 项目 md
  "processed_memories": {...},     // 5b 记忆 md hash → {hash, mtime, phase: "memory_to_kb"}
  "processed_kb_for_memory": {...},// 5c 领域 md hash → {hash, mtime, phase: "kb_to_memory"}
  "cursors": {
    "last_repo_path": "...",       // 5a
    "last_memory_path": "...",     // 5b
    "last_kb_path": "..."          // 5c
  }
}
```

## 输出 JSON 字段 (digest.consolidate 扩展)

```json
{
  "scanned": <N>,
  "concepts_extracted": <N>,
  "domain_created": <N>,
  "domain_enriched": <N>,
  "conflicts_recorded": <N>,
  "memory_to_kb_promoted": <N>,
  "memory_to_kb_skipped_threshold": <N>,
  "kb_to_memory_materialized": <N>,
  "kb_to_memory_skipped_exists": <N>,
  "backlinks_synced": <N>,
  "bridge_audit_rows": <N>
}
```

## 错误处理

- 5b/5c 任一 LLM 调用失败 → 重试 1 次, 仍失败跳该文件, 不写 hash (下次重处理)
- backlink 同步发现循环引用 (A↔B 互链已存在) → 跳过, 计 `backlinks_already_synced`
- bridge.jsonl 写盘失败 → 不阻塞 pipeline, stderr 报错
- `kb_promoted: true` 但 `kb_target` 路径不存在 → 标 `verify_issue: broken_promotion` (stage 7 捕获)

## 与其他阶段交互

| 上游依赖 | 下游影响 |
|---|---|
| 阶段 3 路由结果 (新 episodic / decision 写入 L3) | 影响 5b 候选池 |
| 阶段 4 cortex-memory 评分双路调结果 (weight/recall) | 决定 5b 是否触发 |
| 阶段 6 enrich tags/aliases | 5b/5c 创建的新文件下轮 enrich |
| 阶段 7 verify | 检 promoted/materialized 对应文件是否存在; broken → `verify_issue` |
| 阶段 8 evolution | bridge.jsonl 高频路径 → patterns.md |

## AUTO_MODE 契约

- 任一冲突 (5b 命中已有 KB 概念但定义对立) → 落 `知识库/收件箱/<date>-矛盾-bridge-<concept>.md`, 不动既有, 不询问
- 任一 LLM 输出不符 schema → 重试 1 次, 仍失败跳该文件 (不报"需人工")
- 配置文件缺失字段 → 用本文档默认值, 不询问
