# PRD — Cortex Deep Search + Deep Refactor

## 背景

`cortex_search` MCP tool 当前是单轮多级回退 (hot → index → SC → rg),点查快但有两类盲区:

- **推理深度不足**:复杂问题需要多轮 hit-reflect-rehit 才能收敛;单轮 rg 无法找到"通过中间概念相关"的页面
- **图邻盲区**:找到一个概念节点后,与其相连的 backlink / forward-link 邻居完全未被检索,知识图谱利用率低
- **排序质量低**:语义 (SC) 和关键词 (rg) 各自输出,无统一重排,高相关页可能因来源不同而被截断

`cortex-refactor` 现有 5 子命令处理单页/小范围操作,缺失 vault 级能力:
- 无法整体迁移目录结构 (flat ↔ LYT ↔ PARA)
- 无法批量识别并合并语义重复页
- 无法双向抽提/内联 section 与 concept 页
- 无法基于图谱结构分析孤儿/hub,给出再平衡建议

这两条线天然耦合:**dedupe / restructure 等深度重构均需先用深度检索找候选**,因此合为单 task 并行交付,重构模块调用检索模块。

## 目标

1. 新增 `mcp/tools/deep_search.py` — MCP tool `cortex_deep_search`,内置 iterative / subgraph / hybrid 3 模式
2. 新增 4 类重构子命令:restructure / dedupe / extract+inline / graph-rebalance (共 5 个新 CLI 脚本,extract+inline 合为一脚本双方向)
3. 升级 cortex-researcher / cortex-archivist / cortex-linker 三个 agent 工作流,注入 `cortex_deep_search` 调用
4. 更新 `cortex-search/SKILL.md` 加 deep mode 触发;更新 `cortex-refactor/SKILL.md` 追加新子命令

## 范围

### 新增文件

```
plugins/tools/cortex/
├── mcp/tools/deep_search.py          # cortex_deep_search MCP tool
├── refactor/restructure.py           # vault 结构预设迁移
├── refactor/dedupe.py                # 语义去重合并
├── refactor/extract_inline.py        # section 抽提 / 内联 (双方向)
└── refactor/graph_rebalance.py       # backlink 打分 + 补链建议
```

### 修改文件

| 文件 | 改动摘要 |
|------|---------|
| `mcp/server.py` | 注册 `DEEP_SEARCH_TOOL` + `handle_deep_search` |
| `skills/cortex-refactor/SKILL.md` | 追加 5 个新子命令的 CLI 签名和行为描述 |
| `skills/cortex-search/SKILL.md` | 新增 §Deep Mode: depth=deep 或 `--deep` 触发 `cortex_deep_search` |
| `agents/cortex-researcher.md` | 工作流 step 1 注入 deep_search iterative (depth=deep 时) |
| `agents/cortex-archivist.md` | 工作流 step 2 注入 deep_search hybrid 查重复候选 |
| `agents/cortex-linker.md` | 工作流 step 1 改用 deep_search subgraph 替代 SC REST 直调 |

### 不改

- P0 安全模块 (`hooks/_lib/masking.py`, `url_security.py`, `html_sanitize.py`)
- P5 `git_sync` tool
- `hooks/*.sh` / `install.sh`
- 现有 5 个 refactor 子命令实现 (rename / merge / split / fold / migrate-locale)

## 详细规范

### 1. `mcp/tools/deep_search.py` — `cortex_deep_search`

**Tool 定义**

```python
DEEP_SEARCH_TOOL = Tool(
    name="cortex_deep_search",
    description="深度检索 vault: iterative(多轮RAG) | subgraph(图邻扩展) | hybrid(语义+关键词+BM25重排)",
    inputSchema={
        "type": "object",
        "properties": {
            "query":    {"type": "string"},
            "mode":     {"type": "string",
                         "enum": ["iterative", "subgraph", "hybrid"],
                         "default": "hybrid"},
            "max_hops": {"type": "integer", "default": 2,
                         "minimum": 1, "maximum": 3},
            "iter_max": {"type": "integer", "default": 3,
                         "minimum": 1, "maximum": 3},
            "limit":    {"type": "integer", "default": 15, "minimum": 1},
            "scope":    {"type": "string",
                         "enum": ["all", "concepts", "domains", "log"],
                         "default": "all"},
        },
        "required": ["query"],
    },
)
```

**返回结构** (TextContent.text 为 JSON 字符串)

```json
{
  "query": "原始查询",
  "mode": "hybrid",
  "hits": [
    {"path": "wiki/10_concepts/foo.md", "title": "Foo",
     "snippet": "...", "score": 0.92, "source": "sc"}
  ],
  "iterations": 2,
  "subgraph_expanded": 0,
  "degraded": false
}
```

**依赖复用**:`deep_search.py` 从 `tools.search` import `_smart_connections`, `_ripgrep`, `_dedup`, `_title_from` (同包私有函数,不修改 `search.py`)。`iter_md_files`, `WIKILINK_RE` 从 `lib.vault_path` / `lib._common` 获取,或在 `deep_search.py` 内以 `sys.path` 调整后 import `refactor._common`。

**Mode: iterative**

```
prev_paths = set()
hits = _base_search(query, limit)           # hot + index + SC + rg 同 search.py
for i in range(iter_max):
    if _jaccard(paths(hits), prev_paths) >= 0.8:
        break                               # 收敛退出
    prev_paths = paths(hits)
    gap_query = _extract_gap_tokens(hits, query)   # hits snippets token 差集 top-3
    new_hits  = _base_search(gap_query, limit)
    hits      = _dedup(hits + new_hits)[:limit]
return hits, iterations=i+1
```

- `_extract_gap_tokens`: 从所有 hit snippet 提取 tokens,与 query tokens 做差集,取高频 top-3 拼新查询
- `_jaccard(A, B)`: `len(A & B) / len(A | B)`,集合为 path 字符串集
- `iter_max` 硬上限 3,防 token 失控

**Mode: subgraph**

```
seed_hits = _base_search(query, limit)
expanded  = {h["path"] for h in seed_hits}
hop_score = {p: 1.0 for p in expanded}

for hop in range(1, max_hops+1):
    new_paths = set()
    for p in list(expanded):
        new_paths |= _backlinks(vault, Path(p))    # 扫全 vault WIKILINK_RE
        new_paths |= _forward_links(vault, Path(p)) # 读 p 内 [[]] 引用
    new_paths -= expanded
    for p in new_paths:
        hop_score[p] = 1.0 / (hop * 2)            # hop-1→0.5, hop-2→0.25
    expanded |= new_paths

hits = [_path_to_hit(vault, p, hop_score[p]) for p in expanded]
hits.sort(key=lambda h: h["score"], reverse=True)
return hits[:limit], subgraph_expanded=len(expanded)-len(seed_hits)
```

- `_backlinks(vault, path)`: `iter_md_files(vault)` + `WIKILINK_RE` (复用 `refactor._common`) 找引用 `path.stem` 的文件
- `_forward_links(vault, path)`: 读 `path` 内容,提取所有 `[[target]]` 引用 → 解析为 vault 内绝对路径

**Mode: hybrid**

```
sc_hits  = _smart_connections(query, limit*2, sc_base) or []
rg_hits  = _ripgrep(vault, scope_dir, query)
merged   = sc_hits + rg_hits
reranked = _bm25_rerank(merged, query)
result   = _dedup(reranked)[:limit]
# SC 不可达时 sc_hits=[], degraded=True, 仅 rg+BM25
```

**BM25 重排** (纯 stdlib,内联于 `deep_search.py`):

```python
import math
from collections import Counter

def _bm25_rerank(hits, query, k1=1.5, b=0.75):
    tokens = query.lower().split()
    docs = [(h, (h.get("snippet","") + " " + h.get("title","")).lower())
            for h in hits]
    avgdl = sum(len(d.split()) for _, d in docs) / max(len(docs), 1)
    scored = []
    for h, doc in docs:
        tf = Counter(doc.split())
        dl = len(doc.split())
        bm25 = sum(
            tf[t] * (k1+1) / (tf[t] + k1*(1-b+b*dl/avgdl))
            for t in tokens
        )
        scored.append((bm25 + h.get("score", 0.0), h))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [h for _, h in scored]
```

### 2. `refactor/restructure.py` — vault 结构预设迁移

**CLI**

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/refactor/restructure.py \
  --vault <path> --from <preset> --to <preset> [--apply]
# preset: flat | LYT | PARA
```

**预设定义** (内联 dict,禁 pyyaml):

```python
PRESETS = {
    "flat": {
        "concepts": "concepts", "domains": "domains",
        "log": "log", "archive": ".archive",
    },
    "LYT": {
        "concepts": "10_concepts", "domains": "30_domains",
        "log": "log", "archive": "80_archive",
    },
    "PARA": {
        "concepts": "1_projects", "domains": "2_areas",
        "log": "4_archives/log", "archive": "4_archives",
    },
}
```

**算法**

```
mv_plan, link_plan, warnings = [], [], []
for role in PRESETS[from_preset]:
    src_dir = vault / PRESETS[from_preset][role]
    dst_dir = vault / PRESETS[to_preset][role]
    if src_dir == dst_dir or not src_dir.is_dir(): continue
    for md in src_dir.rglob("*.md"):
        dst = dst_dir / md.relative_to(src_dir)
        if dst.exists():
            dst = dst.with_name(dst.stem + f".restructure-{ts}" + dst.suffix)
            warnings.append(f"collision → renamed: {dst}")
        mv_plan.append({"from": str(md.relative_to(vault)),
                        "to":   str(dst.relative_to(vault))})
        link_plan.append({"old_stem": md.stem,
                          "new_rel":  str(dst.relative_to(vault))})

output = {"op": "restructure", "from": from_preset, "to": to_preset,
          "mv_plan": mv_plan, "link_plan": link_plan,
          "warnings": warnings, "applied": False}

if apply:
    ts = make_backup_ts()
    for mv in mv_plan:
        backup_file(vault, "restructure", ts, vault/mv["from"])
        (vault/mv["to"]).parent.mkdir(parents=True, exist_ok=True)
        (vault/mv["from"]).rename(vault/mv["to"])
    mapping = {e["old_stem"]: e["new_rel"] for e in link_plan}
    for md in iter_md_files(vault):
        text = md.read_text(encoding="utf-8", errors="replace")
        new_text, n = rewrite_wikilinks(text, mapping)
        if n: md.write_text(new_text, encoding="utf-8")
    output["applied"] = True
```

### 3. `refactor/dedupe.py` — 语义近似页去重合并

**CLI**

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/refactor/dedupe.py \
  --vault <path> [--scope concepts] [--threshold 0.85] \
  [--top-k 20] [--apply]
```

**算法**

```
pages = list(iter_md_files(vault / scope_dir))
candidates = []
for page in pages:
    title   = _title_from(page)
    body200 = page.read_text()[:200]
    # deep_search hybrid (通过直接调用 Python 函数, 不走 MCP 进程)
    hits = _hybrid_search(vault, f"{title} {body200}", limit=top_k)
    for h in hits:
        if h["path"] == str(page): continue
        other = Path(h["path"])
        score = _cosine(page.read_text(), other.read_text())
        if score >= threshold:
            candidates.append({
                "pages": [str(page.relative_to(vault)),
                          str(other.relative_to(vault))],
                "score": round(score, 4),
                "suggestion": f"merge {page.stem} into {other.stem}",
            })
# 去重 pair (双向)
seen, deduped = set(), []
for c in candidates:
    key = frozenset(c["pages"])
    if key not in seen:
        seen.add(key); deduped.append(c)

output = {"op": "dedupe", "threshold": threshold,
          "candidates": deduped, "applied": False}

if apply:
    for c in deduped:
        subprocess.run(["python3", refactor_dir/"merge.py",
                        "--vault", vault,
                        "--from", c["pages"][0],
                        "--into", c["pages"][1],
                        "--apply"], check=True)
    output["applied"] = True
```

`_hybrid_search` 直接调用 `_smart_connections` + `_ripgrep` (从 `tools.search` import 或内联),BM25 重排,SC 不可达时降级为 rg-only。

**TF-IDF 余弦** (纯 stdlib,内联于 `dedupe.py`):

```python
from collections import Counter
import math

def _cosine(text_a: str, text_b: str) -> float:
    def tfidf(text):
        tokens = text.lower().split()
        tf = Counter(tokens)
        total = max(len(tokens), 1)
        return {t: c/total for t, c in tf.items()}
    va, vb = tfidf(text_a), tfidf(text_b)
    keys = set(va) & set(vb)
    dot  = sum(va[k] * vb[k] for k in keys)
    na   = math.sqrt(sum(v**2 for v in va.values()))
    nb   = math.sqrt(sum(v**2 for v in vb.values()))
    return dot / (na * nb) if na and nb else 0.0
```

### 4. `refactor/extract_inline.py` — section 抽提 / 内联

**CLI**

```bash
# extract: H2 section → 独立 concept 页
python3 ${CLAUDE_PLUGIN_ROOT}/refactor/extract_inline.py \
  --vault <path> --page <rel> --section <H2-title> \
  --direction extract [--out-path <rel>] [--apply]

# inline: 子页内联回父页 (extract 精确逆向)
python3 ${CLAUDE_PLUGIN_ROOT}/refactor/extract_inline.py \
  --vault <path> --page <rel> --child <child-rel> \
  --direction inline [--section <H2-title>] [--apply]
```

**extract 算法**

```
1. 读 page, 用正则定位 ## <section> 段落 (到下一个 ## 或 EOF)
2. out_path = out-path 参数 或 vault/10_concepts/<slugify(section)>.md
3. 若 out_path 已存在 → 输出 error, dry-run 终止 (不覆盖)
4. child_frontmatter = {type: concept, source: [[page-stem]], tags: 继承父页 tags}
5. child_body = section 内容 (去 ## 标题行)
6. 父页修改: 删除 section body → 替换为 ![[child-stem]] (transclusion)
7. output: {op, page, child_path, section, applied}
```

**inline 算法** (extract 精确逆向)

```
1. 读 child 内容 (去 frontmatter)
2. 在 page 内找 ![[child-stem]] 或 [[child-stem]]
   → 替换为 "## <child-title>\n<child-body>"
3. 若 child 内含嵌套 ![[]] → warnings["nested_transclusion"], 继续 (不阻塞)
4. backup child → 移至 80_archive/ (LYT) 或 .archive/ (其他)
5. 全 vault rewrite_wikilinks({child-stem: page-stem}) (复用 _common.py)
6. output: {op, page, child, applied, warnings}
```

### 5. `refactor/graph_rebalance.py` — 知识图谱再平衡

**CLI**

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/refactor/graph_rebalance.py \
  --vault <path> [--hub-threshold 20] [--scope all] [--apply]
```

**算法**

```
# 1. 构建 backlink 索引 (复用 iter_md_files + WIKILINK_RE)
backlinks: dict[str, set[str]] = defaultdict(set)   # stem → 引用它的文件集合
forward:   dict[str, set[str]] = defaultdict(set)   # stem → 它引用的文件集合
for md in iter_md_files(vault):
    text = md.read_text()
    for m in WIKILINK_RE.finditer(text):
        target_stem = m.group(1).strip().split("/")[-1]
        if target_stem.lower().endswith(".md"):
            target_stem = target_stem[:-3]
        backlinks[target_stem].add(str(md.relative_to(vault)))
        forward[md.stem].add(target_stem)

# 2. 分类
all_pages = list(iter_md_files(vault))
# 性能 cap: 5000+ 页时 orphan link_gaps 分析限前 50
orphans = [p for p in all_pages
           if len(backlinks[p.stem])==0 and len(forward[p.stem])==0]
hubs    = [p for p in all_pages
           if len(backlinks[p.stem]) >= hub_threshold]

# 3. link_gaps (rg 快速找候选, 不依赖 MCP)
link_gaps = []
for orphan in orphans[:50]:
    title = _title_from(orphan)
    rg_hits = _ripgrep_simple(vault, title[:40])  # 内联简化 rg 调用
    if rg_hits:
        link_gaps.append({"orphan": str(orphan.relative_to(vault)),
                          "candidates": [h["path"] for h in rg_hits[:3]]})

output = {
    "op": "graph_rebalance",
    "orphans": [{"path": str(p.relative_to(vault)),
                 "forward_count": len(forward[p.stem])} for p in orphans],
    "hubs": [{"path": str(p.relative_to(vault)),
              "backlink_count": len(backlinks[p.stem]),
              "suggestion": "consider splitting"} for p in hubs],
    "link_gaps": link_gaps,
    "applied": False,
}

# --apply: 仅写 link_gaps 建议的链接 (append 到候选页末尾)
if apply:
    for gap in link_gaps:
        for candidate in gap["candidates"][:1]:   # 每 orphan 最多加 1 链
            cpath = vault / candidate
            backup_file(vault, "graph-rebalance", ts, cpath)
            with cpath.open("a", encoding="utf-8") as f:
                f.write(f"\n相关: [[{Path(gap['orphan']).stem}]]\n")
    output["applied"] = True
# hub 拆分和批量孤儿处理不自动执行, 仅输出提示
```

注:`_ripgrep_simple` 为轻量版 `rg --json -i -l` 调用 (仅需文件名列表),内联于 `graph_rebalance.py`。

## 集成点

### MCP server 注册

```python
# mcp/server.py — 追加两行:
from tools.deep_search import DEEP_SEARCH_TOOL, handle_deep_search

# list_tools: return [..., DEEP_SEARCH_TOOL]
# call_tool:  if name == DEEP_SEARCH_TOOL.name: return await handle_deep_search(arguments)
```

### cortex-researcher 工作流更新

Step 1 (查 vault 已有内容) 改为:

```
if depth == "deep":
    → mcp__cortex__cortex_deep_search(query=topic, mode=iterative,
                                       iter_max=3, limit=15)
else:
    → mcp__cortex__cortex_search (原逻辑不变)
```

deep_search 返回的 hits 同样列入"已知"段落。

### cortex-archivist 工作流更新

Step 2 (价值评分) 注入查重步骤:

```
对每个候选页: mcp__cortex__cortex_deep_search(
  query=<title + body[:100]>, mode=hybrid, limit=5
)
若 hits 中存在同 stem 不同路径的页面 → remarks 列加注 "疑似重复 [[X]]"
```

### cortex-linker 工作流更新

Step 1 改为优先 deep_search subgraph (替换原 SC REST `/find_similar` 直调):

```
mcp__cortex__cortex_deep_search(
  query=<target title + 前200字>, mode=subgraph,
  max_hops=2, limit=top_k
)
# 后续过滤已有 wikilink、self-link 逻辑不变
```

SC 不可达时 deep_search 内部自动降级,不需要 linker 另外处理。

### cortex-search SKILL.md — §Deep Mode

新增节:

```
## Deep Mode
触发条件: 用户输入含 "深度搜索" / "--deep" / "depth=deep" / 多轮研究场景
执行: mcp__cortex__cortex_deep_search(query=<q>, mode=hybrid, iter_max=3)
回退: 若 MCP 不可达 → 原 L1-L5 流程
```

### cortex-refactor SKILL.md — 新增子命令

```
## 新增子命令

| 子命令 | 签名 | 说明 |
|--------|------|------|
| restructure | `--from <preset> --to <preset> [--apply]` | vault 目录预设迁移 (flat/LYT/PARA) |
| dedupe | `[--scope <dir>] [--threshold 0.85] [--apply]` | 语义近似页检测并合并 |
| extract | `--page <rel> --section <H2> [--out-path <rel>] [--apply]` | 抽 H2 节为独立 concept |
| inline | `--page <rel> --child <rel> [--section <H2>] [--apply]` | 子页内联回父页 |
| graph-rebalance | `[--hub-threshold 20] [--apply]` | 扫孤儿/hub, 补链建议 |
```

## 验收标准

| 范围 | 用例 | 通过条件 |
|------|------|---------|
| deep_search iterative | `iter_max=3`, 重叠度高时 | ≤3 轮后输出 `iterations<3` (收敛);SC 不可达时 `degraded=true` 且有 rg hits |
| deep_search subgraph | `max_hops=1` | 仅 seed + 直接邻居;hop-2 节点不出现 |
| deep_search hybrid | SC 在线 | sc + rg 双通道合并;BM25 改变了纯 SC 排序 |
| restructure dry-run | flat→LYT | `mv_plan` 含所有 `.md`;`link_plan` 条目数 = mv_plan 条目数 |
| restructure apply | LYT→PARA | 目录迁移后 wikilinks 全部指向新路径 |
| dedupe dry-run | 两页 cosine ≥ 0.85 | `candidates` 非空;`applied=false` |
| dedupe apply | 确认候选后 | 调 `merge.py --apply`;source 页移至 archive |
| extract apply | 有效 H2 节 | 新 concept 页存在;父页含 `![[child-stem]]` |
| inline apply | 有 `![[child]]` 的父页 | child 内容展开至父页;child 移至 archive;全 vault 反链更新 |
| graph-rebalance dry-run | vault 有孤儿页 | `orphans` 非空;`link_gaps` 含候选 |
| graph-rebalance apply | orphan + candidate 存在 | candidate 末尾追加 `相关: [[orphan-stem]]` |
| researcher depth=deep | `depth=deep` 触发 | 调 `cortex_deep_search`;hits 列入"已知"段 |
| archivist 查重注入 | fleeting 与 concepts 有近似页 | 提案 remarks 列含 "疑似重复 [[X]]" |
| linker subgraph | target + `max_hops=2` | hop-1/2 候选正确出现;已有 wikilink 被过滤 |

## 不变量

1. **stdlib only**:禁 numpy / scipy / requests / pyyaml;BM25 / TF-IDF cosine 均内联纯 Python
2. **dry-run 默认**:所有 refactor 子命令无 `--apply` 时仅输出 JSON plan, 不写盘
3. **backup 先于 apply**:所有写盘操作前调 `backup_file()` (复用 `refactor._common`)
4. **不覆盖已存在目标**:restructure / extract 遇目标已存在 → 跳过 + `warnings[]`, 不 abort
5. **masking 复用**:写 vault 内容前走 `hooks/_lib/masking.py` (现有机制, 不新增逻辑)
6. **iter_max ≤ 3**:deep_search iterative 硬上限, 防 token 链路失控
7. **hub 拆分非自动**:graph-rebalance `--apply` 只落 link_gaps 链接, hub 拆分和孤儿删除仅文字提示
8. **不改 git 历史**:refactor 脚本不调 `git mv` (与现有 migrate-locale 区分, 后者可选 git mv)

## 风险

| 风险 | 等级 | 缓解方案 |
|------|------|---------|
| SC REST 不可达 (27123 端口未启动) | 中 | hybrid / subgraph 自动降级为 rg-only;iterative 用 rg 替代 SC;输出 `degraded=true` |
| iterative token 失控 (大 vault 多轮) | 中 | `iter_max=3` 硬上限;Jaccard ≥ 0.8 收敛提前退出 |
| restructure 路径冲突 (如 LYT→PARA 时 `30_domains` → `2_areas` 与既存目录) | 高 | 碰撞检测 → suffix `.restructure-<ts>`;写入 `warnings[]`;不 abort 整体流程 |
| dedupe 误合并 (threshold 偏低) | 高 | 默认 threshold=0.85 (偏高保守);dry-run 输出候选后须用户逐组确认才 `--apply` |
| graph-rebalance 大 vault 性能 (5000+ 页) | 中 | backlink 扫描 O(n×avg_links) 约 5k×5=25k 次正则匹配, 可接受;link_gaps 分析 cap orphans[:50] |
| extract 嵌套 transclusion (child 含 `![[]]`) | 低 | 检测到嵌套 → `warnings["nested_transclusion"]` 记录, 继续执行 (不阻塞) |
