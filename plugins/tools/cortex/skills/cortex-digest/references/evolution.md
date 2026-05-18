# Evolution 抽取 (阶段 8a)

> 借鉴 agent-playbook self-improving-agent 多 memory 架构。cortex 现 episodic (sessions/jsonl) + working (hot.md), 本阶段补 **semantic 层** — 抽复发 pattern → 写 `记忆/L0-核心/patterns.md` → 阈值过线时生 proposal 到 `_assets/evolution-proposals/`, 用户通过 cortex-refactor 单次确认 → patch SKILL/AGENT (PR4)。

## 调用入口

```bash
bash ~/.cortex/scripts/digest.sh evolution --lookback-days 7 --json
# 直接 exec: python3 plugins/tools/cortex/scripts/cli/digest.py evolution --lookback-days 7 --json
```

CLI 选项:
- `--lookback-days N` — 扫描天数 (默认 7)
- `--vault PATH` — 覆盖 vault 路径 (默认走 `lib/vault_path.py:resolve_vault`)
- `--dry-run` — 仅扫不写盘
- `--compact` — compact JSON (单行)

## 输入

`记忆/L4-流水账/sessions/<cli>/<YYYY>/<MM>/<DD>/*.jsonl` 近 `lookback_days` 天 (mtime ≥ now - N*86400)。

jsonl 格式兼容: 单行 JSON 对象, 含 `role`+`content` 或嵌套 `{"message": {"role": ..., "content": ...}}`; `content` 支持 string 或 Anthropic-style content blocks list (`[{"type": "text", "text": "..."}]`)。

## 6 Category

| category | 含义 | 触发关键词 |
|----------|------|------------|
| `vault-write-contract` | vault 写契约违反 (没走 MCP) | `mcp__obsidian` / `vault 写` / `vault write` / `write 工具` |
| `ingest-failure` | ingest 失败模式 | `ingest` / `摄取` / `WebFetch` / `defuddle` |
| `digest-routing` | digest 路由翻车 | `digest` / `路由` / `routing` / `归属` |
| `skill-trigger` | skill 错触发 / 漏触发 (兜底 category) | `skill` / `触发` / `trigger` |
| `frontmatter-schema` | fm schema 缺字段 | `frontmatter` / `fm-` / `schema` |
| `user-correction` | 用户纠正模式 (含 negative feedback) | (由 negative tokens 路由) |

## Pattern Signature 抽取规则

1. 遍历 jsonl entries, 按角色拆 `prev_assistant` / `user_text`。
2. 若 `user_text` 命中 `NEGATIVE_FEEDBACK_TOKENS` (`不对` / `不是` / `应该是` / `改成` / `错了` / `wrong` / `incorrect` / `that's not` / `no, `), signature = `prev_assistant[:200] + " | " + user_text[:200]`, 标 `is_negative=True`。
3. 否则 signature = `user_text[:300]`。
4. `signature_key` 归一化: 切词 (中英 word chars 长度 ≥ 2) → 取前 8 token → 排序 → `<category>|<tokens>`, 截 200 字符。
5. bucket key: `(category, signature_key)` 聚合, applications = unique sessions count。

## Confidence 公式

- `is_negative` (含纠正语) → base = 0.9
- 其他 → base = 0.5 + 0.05 × applications (上限 +0.4)
- 最终 confidence = `min(1.0, base)`, 保留 2 位小数

## 阈值 (硬编码 D4)

- `MIN_APPLICATIONS = 3` — pattern 候选最低 application 数
- `MIN_CONFIDENCE = 0.8` — 生 proposal 的最低 confidence

两条件同时满足才入 proposal 队列。

不暴露 `_meta/version.json` 配置 (D4 锁定, 调阈值需改代码重发布)。

## patterns.md Schema

`记忆/L0-核心/patterns.md` (D1 single markdown 文件), 多 section 按 category 组织, 每 pattern 为 `### pat-<date>-<sha6> <name>` 三级标题 + yaml fence 块 + 4 个 markdown 字段 (Pattern / Problem / Solution / Sources)。

更新策略:
- 既有同 id pattern → applications 取 `max(old+1, new)`, confidence 取 max, updated=today; 原 section 删除, 新 section append 到 category 末尾
- 新 pattern → append 到对应 category section, 替换占位 `(空)`
- 首次跑 patterns.md 不存在 → 创建 6 category 空骨架后填入

## Proposal Schema

`_assets/evolution-proposals/<YYYY-MM-DD>-<slug>.md`:

```
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

# Proposal: <name>

## Pattern
...

## Problem
...

## Suggested Patch (unified diff)

(unified diff block with placeholder context)

## Episodic Sources

- [[<rel>]] — episodic source
```

target_skill 由 category 推断 (`_guess_target_skills`):

| category | target_skills |
|----------|---------------|
| vault-write-contract | `skills/cortex-save/SKILL.md`, `AGENT.md` |
| ingest-failure | `skills/cortex-ingest/SKILL.md` |
| digest-routing | `skills/cortex-digest/SKILL.md` |
| skill-trigger | `AGENT.md` |
| frontmatter-schema | `skills/cortex-save/SKILL.md`, `skills/cortex-lint/SKILL.md` |
| user-correction | `AGENT.md` |

## 输出 (JSON)

```json
{
  "vault": "/Users/foo/Documents/MyVault",
  "lookback_days": 7,
  "dry_run": false,
  "sessions_scanned": 14,
  "patterns_candidates": 6,
  "patterns_added": 3,
  "patterns_updated": 1,
  "proposals_generated": [
    "_assets/evolution-proposals/2026-05-14-vault-写漏走-mcp.md"
  ]
}
```

## 错误处理

- sessions 目录不存在 → 返空 `episodes` list, 不抛
- jsonl 行 JSON 解析失败 → 跳过该行
- patterns.md 写盘失败 → stderr 报 warn, 继续生 proposal
- proposal 写盘失败 → stderr 报 warn, 继续下一 proposal

## 安全门 (PR4 范围)

PR3 仅生 proposal markdown, **不实际 patch SKILL/AGENT**。PR4 patch 流程将强制:

- patch 前 `cd plugins/tools/cortex && git status --porcelain` 必须为空 (working tree clean), 否则拒绝并提示先 commit
- patch target 仅限 `skills/**/SKILL.md` 或 `AGENT.md`, 禁 `commands/*.md` / `scripts/**/*.py` / `*.sh`
- AskUserQuestion 弹窗 (options: `接受 patch` / `拒绝 patch`); 拒绝则保留 proposal 文件不动 SKILL

## 调度

`cortex-digest` 阶段 6 内联调 (daily cron 03:00)。
用户主动单跑: `bash ~/.cortex/scripts/digest.sh evolution`。

## 与 4 类抽取的关系

evolution 是 cortex-digest 阶段 8a, **与 4 类语义抽取 (反思/连接/矛盾/决策, 阶段 2-3 处理) 维度正交**:

- 4 类语义抽取关注**内容** → 落知识库 (项目/领域/收件箱)
- evolution 关注**行为复发** (用户纠正 / skill 失败模式) → 落 semantic 层 (`记忆/L0-核心/patterns.md`) + proposal 队列

不重复抽取, 不互相覆盖。
