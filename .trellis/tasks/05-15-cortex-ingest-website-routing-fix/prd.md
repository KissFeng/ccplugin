# cortex ingest 网页路由统一 — website 全落 项目/<host>/_site/<slug>/

## Goal

修复 `/cortex:ingest <url>` 把 website URL 错落到 `知识库/收件箱/` 的 bug。统一所有 ingest 入口 (`ingest_url.py` / `ingest_remote.py`) 把 website 落到 `知识库/项目/<host>/_site/<slug>/`, 与 memo 单源真相 + ingest_remote 现有行为一致。

## Bug 复现 (用户反馈 2026-05-15)

用户运行 `/cortex:ingest https://code.claude.com/docs/zh-CN/overview`, 写盘确认时表达 "不是应该作为一个 website 落知识库吗", AskUserQuestion 仍写到 `知识库/收件箱/code.claude.com-docs-zh-cn-overview.md` — 错误。

## What I already know

### 当前 3 处不一致

| 路径 | 实际 | 应该 |
|---|---|---|
| `ingest_url.py` L77, L94, _save_internal 路由 | website → `收件箱/<host>-<slug>.md` | `项目/<host>/_site/<slug>/<slug>.md` |
| `ingest_remote.py` (website crawl) | ✅ 已落 `项目/<host>/_site/<slug>/` | ✅ |
| `skills/cortex-ingest/references/pipeline.md` L51/57/103/107 | 文档化 website→收件箱 | 文档化 website→项目/<host>/_site/<slug>/ |
| memo `cortex-plugin-2026-05-13.md` | "website 无 author 补 _site" → 项目/<host>/_site/ | ✅ 单源真相 |

### 设计意图

- `收件箱/` 保留给纯笔记 (fleeting / journal / question / 用户随手记) — **非外部源**
- `项目/<host>/_site/<slug>/` 是 website 的合法家 (与 github/gitlab repo 同级, _site 占位代替 org)
- digest 后续可从 项目/_site 提取笔记落 `领域/`, 但起点是 项目/

## Requirements

### MVP

1. **`ingest_url.py` 路由修复**:
   - 任意外部 URL (单页 / arxiv / docs / blog) → `知识库/项目/<host>/_site/<slug>/<slug>.md`
   - frontmatter `kind: source`, `source_type: website`, `source_url: <url>`, `host: <host>`
   - 不再有 `kind=inbox` 默认路由 (用户显式 `--kind=inbox` 才落 收件箱, 但这是非典型用法)

2. **`references/pipeline.md` 文档同步**:
   - L51/57: 删 "source (URL/文章 非 repo) → 收件箱"
   - L103/107: 改 "网页 → 项目/<host>/_site/<slug>/<slug>.md, tags: `[type/source, source/web, host/<host>]`"
   - L108: arxiv → 项目/arxiv.org/_site/<slug>/<slug>.md

3. **`SKILL.md` 决策树**: 入口决策树第 X 步明确 "URL → 项目/<host>/_site/<slug>/" (≤80 行内)

4. **AskUserQuestion 行为修正**: 写盘确认提示包含**实际目标路径**, 用户回答"非"/"应该是 X" 时 skill 必须**重新评估路由**而非默认 yes 提交

5. **路径生成规则** (slug 派生):
   - URL = `https://<host>/<path1>/<path2>/...`
   - slug = path 全段连字符化 (`<path1>-<path2>...`), 去查询参数, 去 trailing slash, 限 80 字符
   - 落: `项目/<host>/_site/<slug>/<slug>.md`
   - 多页同 host: 共享 `项目/<host>/_site/` 目录, 各 slug 子目录

### Out of Scope

- 不改 `ingest_remote.py` (已正确)
- 不改 `ingest_file.py` (本地文件场景)
- 不动 github/gitlab 路由 (`项目/<host>/<org>/<repo>/`)
- 不迁移现存 `知识库/收件箱/` 的外部源 (留给用户手动或 digest 处理)
- 不动 cron / wrapper

## Acceptance Criteria

- [ ] `/cortex:ingest https://code.claude.com/docs/zh-CN/overview` → 落 `知识库/项目/code.claude.com/_site/docs-zh-cn-overview/docs-zh-cn-overview.md`
- [ ] frontmatter `kind=source`, `source_type=website`, `host=code.claude.com`
- [ ] 不再有任何 URL 默认走 收件箱
- [ ] `references/pipeline.md` 全部 website→收件箱 引用替换为 →项目/
- [ ] `SKILL.md` 决策树含 "URL → 项目/<host>/_site/<slug>/" 提示
- [ ] AskUserQuestion 写盘确认时显示完整目标路径, 用户否决 → 重新评估
- [ ] `ingest_url.py` 单测 (existing) 通过 + 新增 website→项目 路由测试
- [ ] glm-4.7-flash 识别 SKILL.md 修改后行为正确

## Definition of Done

- 测试: pytest 全过
- ingest_url.py 真实跑 `/cortex:ingest <url>` 验证目标路径
- pipeline.md / SKILL.md 文档一致
- 不动 ingest_remote.py
- 提交分 1 PR (scope 小, 文件 3-4 个)

## Technical Approach

按 memo 单源真相 routing。文件改动:

| 文件 | 改动 |
|---|---|
| `scripts/cli/ingest_url.py` | _save_internal 路径生成 + kind 默认 source / website; 删 inbox 默认 |
| `skills/cortex-ingest/references/pipeline.md` | website 路由文档化 项目/_site/ |
| `skills/cortex-ingest/SKILL.md` | 决策树补 URL→项目 (≤80 行内) |
| `tests/python/cli/test_ingest_url.py` (如存在) | 加 website→项目 case |

## Decision (ADR-lite)

**Context**: ingest_url 把外部 URL 默认落收件箱, 与 memo (website → 项目/_site/) + ingest_remote 现有行为 不一致, 用户 AskUserQuestion 修正被忽略。

**Decision**: 统一所有 ingest 入口 → website 落 项目/<host>/_site/<slug>/。收件箱仅留给纯笔记 (fleeting / journal / question)。

**Consequences**:
- ✅ memo 单源真相 + ingest_remote / ingest_url 行为一致
- ✅ website 有合法家, 不依赖 digest 后续迁移
- ⚠️ 现存收件箱里的 website 文件 (历史) 需手工 / digest 迁, 但 out-of-scope
- ⚠️ kind=inbox 仍可显式用 (非典型), 兼容性保留

## Technical Notes

- ingest_remote.py L70 `ingest_website(url, target, depth, dry_run)` 已用 `项目/<host>/_site/<slug>/`, ingest_url.py 应复用相同 path 生成器
- 检查 `scripts/cli/lib/remote.py` 是否有共享 `derive_website_path()` 函数, 复用; 否则提取共享
- slug 生成可能已有 lib (查 `lib/path.py` 或 `lib/url.py`)
