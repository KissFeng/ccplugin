# PRD — session_start 强化主动检索

## 背景

诊断: session_start hook 注入弱建议 ("非通用问题先调 cortex-search"), AI 默认跳过。

具体缺陷:
1. 语义模糊 — "非通用" AI 判定主观
2. 没强制时机 — 无"回答前必"约束
3. 没触发关键词清单
4. 没主动展示库存 — AI 不知库里有啥
5. **记忆体系完全缺位** — 未提 cortex-memory / cortex-recall (L0-L4)
6. **L0 核心未注入** — 性格/偏好/硬约束应每会话强制读
7. 协作约定段只 5 弱条目

## 目标

session_start 注入升级, 让 AI **主动**且**强制**检索知识库 + 记忆体系:
- L0 核心记忆**直接注入** (AI 无需调用就有)
- 库存 KPI 显示 (AI 知道库里有内容)
- 行为契约**命令式**强约束 + 触发关键词清单
- 涵盖知识库 + 记忆体系 双 namespace 工具

### 不在范围
- 不改 hook 触发机制 (仍是 SessionStart event)
- 不改 SKILL 内容
- 不改 MCP 工具实现
- 不强制 AI 总调用 (用户可手动 disable)

## 设计

### 1. session_start.sh 注入结构 (新)

```
## Cortex 已连接 (lang=zh-CN, vault=<>, preset=lyt)

### 📊 库存快照
- 知识库: 项目 N / 来源 N / 领域 N / 日记 N / 反思 N
- 记忆体系: L0 N · L1 N · L2 N · L3 N · L4 N
- 最近 7 天 新增 top 5: <list>
- 活跃域 top 3: <domain1 / domain2 / domain3>

### 🔒 L0 核心记忆 (always-loaded)
<vault>/记忆体系/L0-核心/*.md 全量拼接 (frontmatter + brief)

### 🔥 hot.md
<existing 5KB cap>

### ⚖️ 行为契约 (硬性, 不可跳过)
1. **回答前必先召回**:
   - 用户提问含触发关键词 → 立即 `mcp__cortex__cortex_memory_recall(query, top_k=5)`
   - 涉及技术/项目/概念 → 立即 `mcp__cortex__cortex_search(query, scope=knowledge)`
   - 不调用直接答 = 违反契约
2. **召回结果采纳规则**:
   - weight ≥ 0.7: 必须采纳, 视为事实
   - weight 0.4-0.7: 引用 + 标注 "记忆来源"
   - weight < 0.4: 可参考, 不强采
3. **写入规则**:
   - 用户新观点/偏好/硬约束 → `cortex_memory_write` 落 L1 (weight ≥ 0.8)
   - 升 L0 必须用户审批 (不可自动)
4. **触发关键词** (匹配则强制召回):
   {{TRIGGERS_LIST}}
5. hot.md 条目优先信任 (高频访问)

### 📚 协作约定 (现有 5 条保留)
1-5. <现有>
```

### 2. L0 核心注入

`session_start.sh` python 段加:

```python
def load_l0_core(vault: Path, cap_per_file: int = 1500) -> str:
    """读 记忆体系/L0-核心/*.md, 拼接 frontmatter + brief 段."""
    l0_dir = vault / "记忆体系" / "L0-核心"
    if not l0_dir.is_dir():
        return ""
    out = []
    for p in sorted(l0_dir.glob("*.md")):
        if p.name.startswith("_"):
            continue  # _index 等
        text = p.read_text(errors="ignore")
        # 取 frontmatter + 第一段 (brief)
        fm_match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.S)
        if fm_match:
            fm, body = fm_match.group(1), fm_match.group(2)
        else:
            fm, body = "", text
        # body 取 brief 段 (## brief 到 ## full 之间, 没的话取前 cap_per_file)
        bm = re.search(r"^##\s+brief\s*\n(.*?)(?:^##|\Z)", body, re.S | re.M)
        brief = bm.group(1).strip() if bm else body[:cap_per_file]
        out.append(f"#### {p.stem}\n\n{brief}")
    return "\n\n".join(out)
```

整体 L0 注入 cap ~5KB (5 个 .md × 1KB)。

### 3. 库存 KPI

`session_start.sh` python 段加:

```python
def stats_snapshot(vault: Path) -> dict:
    s = {}
    # 知识库
    kb = vault / "知识库"
    if kb.is_dir():
        s["kb_projects"] = sum(1 for _ in (kb / "项目").rglob("*.md")) if (kb / "项目").is_dir() else 0
        s["kb_sources"] = sum(1 for _ in (kb / "来源").rglob("*.md")) if (kb / "来源").is_dir() else 0
        s["kb_domains"] = sum(1 for _ in (kb / "领域").rglob("*.md")) if (kb / "领域").is_dir() else 0
        s["kb_journal"] = sum(1 for _ in (kb / "日记").rglob("*.md")) if (kb / "日记").is_dir() else 0
        s["kb_reflect"] = sum(1 for _ in (kb / "反思").rglob("*.md")) if (kb / "反思").is_dir() else 0
    # 记忆
    mem = vault / "记忆体系"
    for lvl in ["L0-核心", "L1-长期", "L2-中期", "L3-短期", "L4-流水账"]:
        s[f"mem_{lvl[:2]}"] = sum(1 for _ in (mem / lvl).rglob("*.md")) if (mem / lvl).is_dir() else 0
    return s

def recent_top(vault: Path, days: int = 7, top_n: int = 5) -> list[str]:
    """近 N 天 mtime 最新 top_n 文件相对路径."""
    import time
    cutoff = time.time() - days * 86400
    items = []
    for root in [vault / "知识库", vault / "记忆体系"]:
        if not root.is_dir():
            continue
        for p in root.rglob("*.md"):
            try:
                if p.stat().st_mtime > cutoff:
                    items.append((p.stat().st_mtime, str(p.relative_to(vault))))
            except Exception:
                pass
    items.sort(reverse=True)
    return [r for _, r in items[:top_n]]
```

### 4. 触发关键词机制

新建 `<vault>/_meta/triggers.yaml`:
```yaml
# 用户偏好/项目/技术触发词, 命中则 session_start 强制 AI 召回
keywords:
  user_pref: [偏好, prefer, "I like", 习惯, 喜好]
  project: [项目, 仓库, repo, 工程]
  tech: [Go, Python, MySQL, React, ...]
  domain: [金融, 投资, 美食, 旅游, ...]
```

`session_start.sh` python 读这个文件, 拼到 `{{TRIGGERS_LIST}}`。若不存在, 退化为默认列表 (写在 locales 里)。

install 阶段 cortex-install SKILL 复制 `<plugin>/templates/triggers.yaml` 到 `<vault>/_meta/triggers.yaml` 作为基线。

### 5. locales 更新

`locales/{zh-CN, en, ja}.yml`:
- 删 `search_first` (用 behavior_contract 替)
- 新 `behavior_contract` (多行, 完整命令式契约)
- 新 `stats_header` ("库存快照")
- 新 `l0_header` ("L0 核心记忆 (always-loaded)")
- 新 `triggers_header` ("触发关键词清单")
- 保留 `collab_save / collab_no_direct / collab_block_id / collab_stop_hook`

### 6. 总注入预算

| 段 | 上限 |
|----|------|
| header | 200 B |
| stats snapshot | 500 B |
| L0 核心 (5 文件 × 1KB) | 5 KB |
| hot.md | 5 KB (现有) |
| 行为契约 + 触发词 | 1 KB |
| 协作约定 | 300 B |
| 总计 | ~12 KB |

Anthropic 实测 additionalContext 上限 ~10-15KB, 在上限内。

## 实施步骤

### 步骤 1: locales 加新 keys (3 文件)

`locales/{zh-CN, en, ja}.yml`:
- behavior_contract (多行)
- stats_header / l0_header / triggers_header
- default_triggers (默认关键词清单, vault 无 triggers.yaml 时 fallback)

### 步骤 2: session_start.sh 升级

加 3 函数: `load_l0_core` / `stats_snapshot` / `recent_top` / `load_triggers`.
重写 context 拼接逻辑, 按设计 §1 顺序输出。

### 步骤 3: triggers.yaml 模板

新建 `plugins/tools/cortex/templates/triggers.yaml` (默认骨架, 用户可改)。

### 步骤 4: cortex-install SKILL 更新

§4 共享根写入加 `_meta/triggers.yaml` 复制项。

### 步骤 5: 测试

新建 `plugins/tools/cortex/tests/python/test_session_start_v2.py`:
- 测试 stats_snapshot 计数正确
- 测试 L0 核心拼接 (mock vault)
- 测试 hot.md 注入未回归
- 测试 triggers.yaml 不存在时 fallback 到 locale 默认

## 验收

- [ ] session_start.sh 注入按设计 §1 6 段
- [ ] L0 核心 5 .md 全注入 (mock 测试)
- [ ] stats_snapshot 知识库 + 记忆 计数准确
- [ ] recent_top 近 7 天 top 5 显示
- [ ] triggers.yaml 模板存在 + install SKILL 复制项
- [ ] locales 3 语言新 keys 全译
- [ ] session_start hook bash -n + python 编译 PASS
- [ ] 217 + 新单元测试 PASS
- [ ] 总注入大小 < 15KB (实测 vault 干净状态)

## 风险

| 风险 | 缓解 |
|------|------|
| L0 太大爆 token | per-file cap 1.5KB + 总 cap 5KB |
| hot.md + L0 + stats 一起超额 | 整体 cap 15KB, 超时截断 hot |
| triggers.yaml 用户改坏 | yaml.safe_load 兼容; 解析失败 fallback locale |
| python 计数慢 (rglob 大 vault) | 加 timeout 2s + cap 1000 文件; 失败 stats 段省略 |
| L0 含敏感数据被泄 | L0 是用户偏好/约束, 设计上就是要 AI 看; 不属敏感 |

## 子任务

5 步骤串行, 单 trellis-implement。
