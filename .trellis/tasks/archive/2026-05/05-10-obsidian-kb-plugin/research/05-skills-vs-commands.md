# Research: Skills vs Slash Commands in Claude Code

- **Query**: skills 与 slash commands 的边界 / 加载机制 / frontmatter 字段语义差异
- **Scope**: mixed (官方 docs + 本地 marketplace + 本仓库 cortex)
- **Date**: 2026-05-10

## TL;DR — 用户论断的修正

| 用户论断 | 真实情况 (官方 docs 2025-Q1+) | 证据 |
|---|---|---|
| 「Skills 由模型自动加载」 | ✅ 正确,但仅当 `disable-model-invocation: false` (默认) 时;skill 的 description **始终** 在 context 中,full body 在被调用时才注入 | docs/claude-code/skills §"Control who invokes a skill" |
| 「Commands 仅由用户显式触发」 | ⚠️ **过时**。Claude Code 已正式声明:**"Custom commands have been merged into skills"**。`.claude/commands/*.md` 与 `.claude/skills/<name>/SKILL.md` 都注册同名 `/<name>`,**两者都可被模型自动调用**,除非加 `disable-model-invocation: true`。"仅用户触发" 需通过 frontmatter 显式声明,不是 command 的天然属性。 | docs §"Skills" 开头第 2 段;§"Control who invokes" |
| 「skill 与 command 是两种东西」 | ❌ 在 Claude Code 里 **是同一种东西的两种文件布局**;skill (目录形态) 多了 supporting-files / scripts 能力,frontmatter 完全互通 | 官方原文:"A file at `.claude/commands/deploy.md` and a skill at `.claude/skills/deploy/SKILL.md` both create `/deploy` and **work the same way**" |

**结论给 cortex**:不应再以 "skill = 自动 / command = 手动" 二分论作为分工依据。真正的分工依据是 **`disable-model-invocation` 与 `user-invocable`** 两个字段,以及 **是否需要 supporting files / scripts 同目录**。

---

## 一、官方权威来源

| 来源 | 链接 | 关键章节 |
|---|---|---|
| Skills (Claude Code) | https://docs.claude.com/en/docs/claude-code/skills | Frontmatter reference / Control who invokes / Skill content lifecycle |
| Slash commands | https://docs.claude.com/en/docs/claude-code/slash-commands | **当前重定向到 Skills 页面** (本研究 curl 验证 1.7MB body 与 skills 页一致) |
| Plugins | https://docs.claude.com/en/docs/claude-code/plugins | When to use plugins, namespacing |
| Agent Skills overview | https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview | (curl 失败 — 非阻塞,Claude Code 自有规范覆盖足够) |

---

## 二、Frontmatter 字段全表 (来源: docs §Frontmatter reference)

| 字段 | 必填 | 默认 | skill (`SKILL.md`) | command (`.md`) | 说明 |
|---|---|---|---|---|---|
| `name` | No | 目录/文件名 | ✅ | ✅ | 小写字母+数字+连字符 ≤64 字符;命令是 `/<plugin>:<name>` |
| `description` | **Recommended** | 首段正文 | ✅ | ✅ | **决定模型何时自动调用**;`description + when_to_use` 合并 ≤1536 字符,超出截断 |
| `when_to_use` | No | — | ✅ | ✅ | 触发短语/示例;追加到 description 后,共享 1536 上限 |
| `argument-hint` | No | — | ✅ | ✅ | 自动补全提示,如 `[issue-number]`;**在 skill 与 command 上字段名完全一致** |
| `arguments` | No | — | ✅ | ✅ | 命名位置参数 (`$name` 替换),空格分隔字符串或 YAML list |
| `disable-model-invocation` | No | `false` | ✅ | ✅ | **核心字段**:`true` → 仅用户可触发,且不进入主 context 描述池 |
| `user-invocable` | No | `true` | ✅ | ✅ | `false` → 不在 `/` 菜单显示,只供 Claude 自动调用 (背景知识型) |
| `allowed-tools` | No | — | ✅ | ✅ | **空格分隔字符串 OR YAML list** (官方原文);`Bash(git add *)` 此类带括号的子串需空格分,逗号会被解析进字符串 |
| `model` | No | — | ✅ | ✅ | 同 `/model` 取值 + `inherit`;只对当前 turn 生效 |
| `effort` | No | inherit | ✅ | ✅ | low / medium / high / xhigh / max |
| `context` | No | — | ✅ | ✅ | `fork` 时进入 subagent;否则 inline 注入主 context |
| `agent` | No | general-purpose | ✅ | ✅ | 配合 `context: fork`,选 Explore / Plan / 自定义 |
| `hooks` | No | — | ✅ | ✅ | skill-scoped lifecycle hooks |
| `paths` | No | — | ✅ | ✅ | glob 列表,只在匹配文件存在时自动激活 |
| `shell` | No | bash | ✅ | ✅ | bash / powershell |
| `memory` | — | — | ❌ | ⚠️ | **未在官方 frontmatter reference 中列出**;本仓库 `git/commands/commit.md` 出现 `memory: project` — 疑为非官方扩展或旧字段。需要核实,**不建议在 cortex 里用**。 |

**关键澄清**:
1. `allowed-tools` **官方仅说 "space-separated string or YAML list"**,逗号格式来自旧 commands 文档约定。当前文档中 skill 与 command 都接受同一种语法。本仓库现状是 skill 用空格、command 用逗号 — 二者都能工作,但**统一用空格更符合最新 spec**。
2. **没有 "skill 专属字段" 也没有 "command 专属字段"** — 在 Claude Code 中字段集完全互通;`argument-hint` 在 skill 上同样合法 (官方 frontmatter table 明确列了 skill 字段含 `argument-hint`)。
3. `description` 上限 **1536 字符**,过长会被静默截断 — 这是关键运维细节。

---

## 三、加载与触发机制 (官方原文摘录)

### 3.1 描述池 (default skills)

> *"In a regular session, skill descriptions are loaded into context so Claude knows what's available, but full skill content only loads when invoked."*

→ Claude 看到的是一张 "skill 名 + description" 清单 (类似工具签名),由 LLM 自己判断哪个匹配当前需求 → 触发 → 才把 SKILL.md body 注入 conversation。**不是 RAG / 向量检索,是 LLM 在 system prompt 注入的 listing 上做语义匹配。**

### 3.2 三种触发路径

| 触发方 | 路径 | 限制条件 |
|---|---|---|
| 用户显式 | 输入 `/<plugin>:<name> [args]` | 必须 `user-invocable: true` (默认) |
| 模型自动 | LLM 读到 description 后调用 Skill 工具 | 必须 `disable-model-invocation: false` (默认);受 `Skill(name)` permission 规则约束 |
| 文件路径自动 | `paths: ["**/*.tsx"]` 等 glob 命中当前编辑文件 | 自动加载,无需用户/模型决定 |

### 3.3 主 agent 能否自己 "输出 `/cortex:save`" 自调用?

**不能直接通过输出文本触发**。Slash 命令是 Claude Code CLI 在用户输入解析阶段处理的;LLM 在助手消息里写出 `/cortex:save` 只会作为字符串显示给用户,不会被宿主截获重新解析。

**但 LLM 可以通过 Skill 工具调用同一逻辑**:Claude Code 暴露 `Skill` 工具 (见 docs §"Restrict Claude's skill access" 中提到 `# Add to deny rules: Skill`),`disable-model-invocation: false` 的 skill/command 都可被 Skill 工具触发。所以"主 agent 自动调用 /cortex:save" 的实现路径是:

1. `/cortex:save` 命令对应的 skill `cortex-save` 保持 `disable-model-invocation: false` (默认)
2. `cortex-save/SKILL.md` 的 description 写明触发场景
3. LLM 在合适时机通过 Skill 工具调用 → 等价效果

**Hook 中能否触发 skill/command?** 官方 docs 未明确支持;hook 是宿主侧 shell 脚本,可以输出指令文本,但**输出 `/skill-name` 不会被自动执行**(同上)。Hook 的作用是 *deterministic* 行为注入,与 skill *probabilistic* 触发互补。

### 3.4 Skill body 生命周期 (重要,用于 description 写作)

> *"When you or Claude invoke a skill, the rendered SKILL.md content enters the conversation as a single message and stays there for the rest of the session. Claude Code does not re-read the skill file on later turns."*

→ skill body 是一次性注入持续驻留 → 写 standing instructions,而不是 step-by-step。
→ Auto-compaction 后只保留最近一次调用的前 5000 token,所有 skills 共享 25000 token 预算。

---

## 四、本地实证:四个 marketplace 的 frontmatter 风格对比

| 库 | skill 数量 | 风格特征 | 字段使用 |
|---|---|---|---|
| `claude-obsidian-marketplace` | 11 (wiki, save, autoresearch, defuddle, canvas, wiki-query, wiki-fold, wiki-lint, wiki-ingest, obsidian-markdown, obsidian-bases) | 长 description + 显式 `Triggers on: <短语列表>` | 仅 `name + description (+ allowed-tools 偶尔)` |
| `megaphone-tokyo/kioku` | 5 (wiki-ingest, wiki-ingest-all, setup-guide, marketing-release-handoff, kioku-delegation-handoff) | 日文长描述,内嵌 `/skill-name <args>` 启动语法说明 | 仅 `name + description` (极简) |
| `obsidian-skills` | 5 | 同 obsidian-markdown 系列 | 同上 |
| `claude-code-warp / superpowers / ralph` | 多 | 混合 | 多样 |

**关键模式 — Triggers on**:

```yaml
description: "Strip clutter from web pages before ingesting into the wiki. ...
  Triggers on: defuddle, clean this page, strip this url, fetch and clean,
  clean web content before ingesting, strip ads, remove clutter,
  clean URL content, readable markdown from URL."
```

→ 直接把 *用户可能说的话* 列在 description 里,LLM 做模糊匹配时命中率高。
→ kioku 风格则把 `/skill <args>` 的启动方式写进 description 内,起到双向提示。

---

## 五、Skill vs Command 设计原则 (基于以上证据)

### 5.1 何时用 skill 目录形式

| 场景 | 理由 |
|---|---|
| 需要 supporting files (templates / examples / reference) | **command 不支持目录**,只能单 .md |
| 需要 scripts (`scripts/helper.py`) | 同上 |
| 内容 >500 行,想拆成 reference.md / examples.md | 官方建议 SKILL.md ≤500 行,溢出拆文件 |
| 想用 `paths:` glob 自动激活 | 字段在 command 也合法,但 skill 目录更适合维护 |

### 5.2 何时用 command 单文件形式

| 场景 | 理由 |
|---|---|
| 纯 prompt template,无 supporting | 一文件即可,不需要目录 |
| 与现存 `.claude/commands/` 兼容 | 官方明确保留兼容 |
| 强调 "用户触发的动作" 心智模型 | 文件位置在 `commands/` 下传达意图 (社区惯例,非技术约束) |

### 5.3 双形态共存 (薄壳 command 调 skill)

不需要。Claude Code 中 `/<plugin>:<name>` 已经统一,**没有 "command 调 skill" 的间接路径**;两者就是同一个 `/name`。社区里偶见 `commands/foo.md` 内只写 `Use the foo skill.` 的写法,但这反而让模型读两层 prompt,**增加 token 成本,无收益**,应避免。

### 5.4 description 写作模板

**自动调用型 (skill / command 默认)**:

```yaml
description: >
  <一句动词开头描述做什么>。<可选: 关键差异化能力>。
  Triggers on: "<触发短语 1>", "<短语 2>", ..., "/<plugin>:<name>", "<中文短语>".
```

**仅用户触发型 (有副作用 / 破坏性)**:

```yaml
description: <动词开头描述做什么 + 何种参数>
disable-model-invocation: true
argument-hint: "<arg1> [arg2]"
```

**背景知识型 (隐形)**:

```yaml
description: <知识范围>。Reference this when <场景>.
user-invocable: false
```

---

## 六、cortex 现状评估

读取 `plugins/tools/cortex/{skills,commands}/` 后发现:**skill 与 command 严重重复 (4 skills + 6 commands,且 setup ↔ install / search ↔ query 等多对同义)**。这是 "skill = 自动 / command = 手动" 旧二分论的产物,在新规范下应整合。

### 6.1 现状映射表

| skill (`SKILL.md`) | command (`.md`) | description 风格 | `allowed-tools` 分隔 | 重复度 |
|---|---|---|---|---|
| `cortex-ingest` | `cortex-ingest.md` | skill: 「摄取... Triggers on ...」 / cmd: 「把外部源摄取进...」 | skill 空格 / cmd 逗号 | 99% 同义 |
| `cortex-query` | `cortex-search.md` | 同样三级回退描述 | skill 空格 / cmd 逗号 | 99% 同义 |
| `cortex-save` | `cortex-save.md` | 同样落档描述 | skill 空格 / cmd 逗号 | 99% 同义 |
| `cortex-setup` | `cortex-install.md` | skill: 「初始化或升级...」 / cmd: 「安装 cortex 标准布局...」 | skill 空格 / cmd 逗号 | 95% 同义 (命名错位:setup ↔ install) |
| — | `cortex-doctor.md` | 「诊断...」 | 逗号 | command-only |
| — | `cortex-new.md` | 「新建一篇笔记...」 | 逗号 | command-only |

### 6.2 反模式定位

| file:line | 问题 | 类别 |
|---|---|---|
| `skills/cortex-ingest/SKILL.md:3` | description 既描述行为又内嵌 "Triggers on" — 长度逼近 1536 | description 风格混乱 |
| `commands/cortex-ingest.md:2` | description 与 skill 几乎重复;无 `disable-model-invocation` 也无差异化定位 | 与 skill 100% 重复 |
| `commands/cortex-search.md:2` vs `skills/cortex-query/SKILL.md:3` | **命名不一致** (search vs query) — 用户触发 `/cortex:search` 与 LLM 自动调 `cortex-query` 走两条路径 | 命名漂移 |
| `commands/cortex-install.md:2` vs `skills/cortex-setup/SKILL.md:3` | 同上 (install vs setup) | 命名漂移 |
| 全部 6 个 command | `allowed-tools: Bash, Read, ...` 用逗号 | 与官方推荐 (空格) 不一致;与 skill 内部不一致 |
| 4 个 skill | description 含 `/cortex:install`、`/cortex:search` 字面量,但同名 command 才是真正路径 | 引用与实现命名漂移 |
| 6 个 command | 全部缺 `disable-model-invocation`,即 LLM 也会自动触发 → **与 skill 的描述池构成重复条目,占用 1536 字符上限两次,挤占其他 skill 描述空间** | context 浪费 |

### 6.3 修订建议 (具体 file:line + 改前/改后)

#### 建议 A:以 skill 为主,command 退化为薄壳 → **不推荐** (5.3 已论证无收益)

#### 建议 B (推荐):**skill ↔ command 二选一,删冗余**

按"是否需要 supporting files"决定:

| 功能 | 决策 | 操作 |
|---|---|---|
| ingest | 保留 skill (后期可挂 templates/) | 删 `commands/cortex-ingest.md` |
| query/search | 保留 skill,**重命名**为 `cortex-search` 与 cmd 对齐 | 删 `commands/cortex-search.md` |
| save | 保留 skill | 删 `commands/cortex-save.md` |
| setup/install | 保留 skill,重命名 `cortex-install` 与 cmd 对齐 | 删 `commands/cortex-install.md` |
| doctor | 转 skill (`skills/cortex-doctor/SKILL.md`),加 `disable-model-invocation: true` (诊断不应被自动触发) | 移除 `commands/cortex-doctor.md` 后新建 skill |
| new | 转 skill `skills/cortex-new/`,加 `argument-hint`,**保留** `disable-model-invocation: true` (创建文件有副作用) | 移除 cmd 后新建 |

最终结构:**6 个 skill,0 个 command**,与 task plugin (`plugins/tools/task/skills/{adjust,align,done,exec,explore,flow,plan,resume,verify}` 9 skill 0 command) 对齐 — 这是本仓库已有的"全 skill"先例,内部一致。

#### 建议 C:逐字段修订 (保留双形态时使用,但与 B 互斥)

如果保留 commands,以下是字段层修订:

```yaml
# commands/cortex-ingest.md:1-5  改前
---
description: 把外部源 (本地文件 / URL / 目录) 摄取进 Obsidian vault, 自动抽实体/概念 / 套模板 / 重名检测 / 反向 wikilink 回填 / 同步索引
argument-hint: "<file|url|dir> [--type concept|source|entity] [--depth N] [--dry-run]"
allowed-tools: Bash, Read, Write, Edit, Glob, WebFetch, mcp__obsidian__obsidian_get_file_contents, mcp__obsidian__obsidian_append_content, mcp__obsidian__obsidian_simple_search
---

# 改后
---
description: 把外部源 (本地文件 / URL / 目录) 摄取进 Obsidian vault — 抽实体/概念 / 套模板 / 重名检测 / 反向 wikilink 回填 / 同步索引
argument-hint: "<file|url|dir> [--type concept|source|entity] [--depth N] [--dry-run]"
disable-model-invocation: true
allowed-tools: Bash Read Write Edit Glob WebFetch mcp__obsidian__obsidian_get_file_contents mcp__obsidian__obsidian_append_content mcp__obsidian__obsidian_simple_search
---
```

要点:
1. 加 `disable-model-invocation: true` — 让 command 真正成为"仅用户触发",**腾出 description 池给 skill**
2. `allowed-tools` 改空格分隔 — 与官方 spec 与 skill 一致
3. description 收紧,不再重复 skill 的 Triggers on 部分

对应的 skill 改动:

```yaml
# skills/cortex-ingest/SKILL.md:1-5  改前
---
name: cortex-ingest
description: 把外部源 (单文件 / URL / 目录) 摄取进 Obsidian vault — 抽实体/概念 / 套模板 / 重名检测 / 反向 wikilink 回填 / 同步索引。Triggers on "ingest", "process this source", "add this to the wiki", "/cortex:ingest", "batch ingest", "ingest this url", "摄取", "导入到知识库", "把这篇文章存到 obsidian".
allowed-tools: Bash Read Write Edit Glob WebFetch mcp__obsidian__obsidian_get_file_contents mcp__obsidian__obsidian_append_content mcp__obsidian__obsidian_simple_search
---

# 改后 (动作描述更短,Triggers 更密)
---
name: cortex-ingest
description: >
  把外部源 (本地文件 / URL / 目录) 摄取进 Obsidian vault — 抽实体 / 套模板 / 重名检测 / 反向 wikilink 回填 / 同步索引。
  Triggers on: "ingest", "process this source", "add this to the wiki", "batch ingest",
  "ingest this url", "摄取", "导入到知识库", "把这篇文章存到 obsidian", "归档这篇网页".
allowed-tools: Bash Read Write Edit Glob WebFetch mcp__obsidian__obsidian_get_file_contents mcp__obsidian__obsidian_append_content mcp__obsidian__obsidian_simple_search
---
```

要点:**移除 `/cortex:ingest` 字面量** — 字面 slash command 不影响 LLM 自动调用 skill,反而占用 description 字符额度;让 skill 描述聚焦在"何时该用",command 文件本身负责 slash 路径。

类似改动套用至其余三对 (query/search、save、setup/install)。

### 6.4 命名漂移修复

| 现状 | 改后 |
|---|---|
| `skills/cortex-query` ↔ `commands/cortex-search` | 统一为 `cortex-search` (search 是用户更自然的口令) |
| `skills/cortex-setup` ↔ `commands/cortex-install` | 统一为 `cortex-install` (与社区 `obsidian-skills` 等 install 命名对齐) |

---

## 七、设计原则总结 (写在 cortex 的 AGENT.md 里)

1. **能用 skill 就用 skill**;只有当 1) 内容极短 (<30 行) 且 2) 永久无 supporting file 时才用单文件 command。
2. **`description` 写法两套模板**:自动型必须含 *Triggers on:* 列表 (中英混排,覆盖用户口语);手动型加 `disable-model-invocation: true` 并以动词起头描述动作。
3. **`allowed-tools` 一律空格分隔** (符合官方最新 spec)。
4. **`description + when_to_use` 总长 ≤1536 字符**,溢出被截断;不要在 description 里塞 `/plugin:cmd` 字面量。
5. **skill 与 command 不重复同义**;命名必须与 slash 路径完全一致 (`skill name == command file basename`)。
6. **副作用型 (deploy / commit / install / new file)** 一律 `disable-model-invocation: true`,防止 LLM 自动触发。
7. Hook 不是 skill/command 的触发通道;hook 输出 `/skill-name` 文本不会被宿主重新解析。要在 hook 中"自动行为"必须直接写 shell 逻辑,不能委托给 skill。

---

## Caveats / Not Found

- **`memory: project` 字段**:本仓库 `commands/git/commit.md` 等使用此字段,但官方 frontmatter reference 未列出,可能是早期 commands 专属字段被废弃 / 或第三方 fork 扩展。**不建议在 cortex 新建文件中使用**,等官方明确;现有用法可保留。
- Slash-commands 独立文档已重定向 / 内容合并到 skills 页 (curl 1.7MB body 与 skills 页一致),意味着**官方将 commands 视为 skills 的子集**,本研究的所有"二者一致"结论由此印证。
- Agent Skills overview (`/en/docs/agents-and-tools/agent-skills/overview`) curl 失败,推测 SSR 限速;但 Claude Code 文档自身已包含完整规范,不影响结论。
- Hook 中触发 skill 的能力:官方文档未禁止也未确认;实际行为以 SubagentStop / SessionStart 输出测试为准 — 本研究无实证条件。
