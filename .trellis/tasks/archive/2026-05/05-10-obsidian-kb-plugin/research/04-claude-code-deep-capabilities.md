# Research 04 — Claude Code 深度能力调研 (for `cortex` plugin)

- Query: 穷尽 CC plugin 平台所有可用钩子 / 扩展点 / 字段, 输出 cortex 的增量补丁
- Scope: 内部 (`~/.claude/plugins/marketplaces/*`, 本仓库 `plugins/`) + 外部 (官方 docs)
- Date: 2026-05-10
- Caveat: 本调研以**本地真实安装样本**为主依据;远程官方 docs URL 在断网/未访问情况下用 path-only 引用. 字段未在样本中出现的标记 ⚠ 推断.

---

## A. Hook 事件全集与 payload schema

### A.1 事件清单 (按本仓库 `plugins/tools/notify/.claude-plugin/plugin.json:20-260` 实证 + 官方 plugin 样本佐证)

| # | Event | 触发时机 | matcher 支持 | 已知 payload 字段 (stdin JSON) | 已知输出影响 | Source |
|---|---|---|---|---|---|---|
| 1 | `SessionStart` | 会话启动/恢复/clear/compact 后 | `startup` / `resume` / `clear` / `compact` (`|` 拼接) | `hook_event_name`, `session_id`, `transcript_path`, `cwd`, `matcher`(=trigger), `source` | `hookSpecificOutput.additionalContext` 注入到 system prompt | `claude-obsidian-marketplace/hooks/hooks.json:5` (matcher `startup|resume`); `claude-code-warp/.../hooks.json:5`; kioku injector code line 3-9 |
| 2 | `SessionEnd` | 会话主动退出 (≠ Stop) | 无 (空 matcher) | `session_id`, `transcript_path`, `reason` | 仅副作用 (无 additionalContext) | `~/.claude/settings.json` SessionEnd 块 |
| 3 | `UserPromptSubmit` | 用户回车后, LLM 处理前 | 无 | `prompt`, `session_id`, `cwd`, `transcript_path` | `hookSpecificOutput.additionalContext` 追加; 非 0 退出码可阻断提交 (推断⚠) | `hookify/hooks.json:37`; `caveman/hooks.json` UserPromptSubmit |
| 4 | `PreToolUse` | 工具调用前 | 工具名(`Bash`/`Edit`/`Write`/`MultiEdit`) 或 `|` 拼接 或 MCP `mcp__server__tool` glob | `tool_name`, `tool_input`, `session_id`, `cwd`, `transcript_path` | `permissionDecision`: `allow`/`deny`/`ask`; `permissionDecisionReason`; 也可只副作用记录 | `~/.claude/settings.json` PreToolUse Bash matcher; `hookify/hooks.json:4` |
| 5 | `PostToolUse` | 工具返回后 | 同 PreToolUse | 上述 + `tool_response` | `additionalContext` 追加; blocking 决策⚠ | `~/.claude/settings.json` PostToolUse `Bash|Edit|Write|MultiEdit` |
| 6 | `Stop` | 主 agent 决定停止时 | 无 | `session_id`, `transcript_path`, `stop_hook_active` | 输出文本 → 提示给主 agent (循环触发可) | `omob/hooks.json:5`; `claude-obsidian-marketplace/hooks.json:40` |
| 7 | `SubagentStop` | sub-agent 完成 | 无 | + `subagent_id`/`subagent_name` (推断⚠) | 同 Stop | `notify/.claude-plugin/plugin.json:116` |
| 8 | `SubagentStart` | sub-agent 开始 | 无 | 同上 | 仅观察 | `notify/.claude-plugin/plugin.json:104` |
| 9 | `PreCompact` | 自动/手动压缩前 | 无 | `session_id`, `transcript_path`, `trigger`(`auto`/`manual`) | 输出文本以指导压缩重点 (推断⚠) | `notify/.claude-plugin/plugin.json:248` |
| 10 | `PostCompact` | 压缩后 | 无 | `session_id`, `transcript_path` | `hookSpecificOutput.additionalContext` 用于注入 hot cache | kioku injector注释 line 3-9; `claude-obsidian-marketplace/hooks.json:18` |
| 11 | `Notification` | LLM 等待用户/idle | `idle_prompt` (warp 用) ⚠ | `message`, `session_id` | 仅副作用 (terminal bell 等) | `claude-code-warp/.../hooks.json` Notification |
| 12 | `PermissionRequest` | 工具需要授权时 | 无 | `tool_name`, `tool_input` | 仅观察 (UI 侧主决策) | `claude-code-warp/.../hooks.json`; `notify/.claude-plugin/plugin.json:56` |
| 13 | `PostToolUseFailure` ⚠ | 工具执行失败 | (推断同 PreToolUse) | + `error` | 副作用 | `notify/.claude-plugin/plugin.json:80` (本地 fork 自定义⚠ — 官方可能未公布) |
| 14 | `StopFailure` ⚠ | Stop 钩子失败 | 无 | — | 副作用 | `notify/.../plugin.json:140` (同上) |
| 15 | `TeammateIdle` ⚠ | Agent Teams 模式空闲 | 无 | — | 副作用 | `notify/.../plugin.json:152` (实验性, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`) |
| 16 | `TaskCompleted` ⚠ | Task 工具完成 | 无 | — | 副作用 | `notify/.../plugin.json:164` |
| 17 | `InstructionsLoaded` ⚠ | CLAUDE.md/AGENTS.md 加载完毕 | 无 | — | 副作用 | `notify/.../plugin.json:176` |
| 18 | `ConfigChange` ⚠ | settings.json 改动 | 无 | — | 副作用 | `notify/.../plugin.json:188` |
| 19 | `CwdChanged` ⚠ | cwd 切换 | 无 | — | 副作用 | `notify/.../plugin.json:200` |
| 20 | `FileChanged` ⚠ | 文件状态变 | 无 | — | 副作用 | `notify/.../plugin.json:212` |
| 21 | `WorktreeCreate` / `WorktreeRemove` ⚠ | sub-agent worktree 隔离 | 无 | — | 副作用 | `notify/.../plugin.json:224,236` |

> ⚠ 标记: notify 插件登记的事件名超出官方 docs 公开范围, 可能为 experimental 或本地 fork 自定义. cortex MVP 只用 1-12 (其中 1,3,4,5,6,7,9,10 为重点), 其余仅文档化备查.

### A.2 hook 输出协议 (v2 wrapped JSON)

```json
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart" | "PostCompact" | "UserPromptSubmit",
    "additionalContext": "..."
  }
}
```

`PreToolUse` 增量字段 (推断 + warp 实证):

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow" | "deny" | "ask",
    "permissionDecisionReason": "..."
  }
}
```

约束 (来自 kioku injector code 注释 line 1-9, 13-15, 56-62):

- v2 必须 wrap; v1 flat `{additionalContext: "..."}` 在 v2 CLI 不识别
- `additionalContext` 内部 cap ≈ 10KB, 末尾 truncate (kioku 用 `MAX_INDEX_CHARS=10000` 给 hot.md 让位)
- exit 0 是 success; exit ≠ 0 视事件而异 (PreToolUse 非 0 = deny; UserPromptSubmit 非 0 = block prompt — 推断⚠)
- stderr 走调试 (kioku 用 `KIOKU_DEBUG` env 控制)
- `suppress` / `blocking` 字段在公开样本中**未观察到**, 不可依赖

### A.3 hook 配置项 (`hooks.json` schema)

```jsonc
{
  "description": "...",         // optional
  "hooks": {
    "<EventName>": [
      {
        "matcher": "Bash|Edit", // optional, 仅 PreToolUse/PostToolUse/SessionStart 有意义
        "hooks": [
          {
            "type": "command" | "prompt",   // command=shell, prompt=注入文本
            "command": "...",                // type=command 时, 支持 ${CLAUDE_PLUGIN_ROOT}
            "prompt": "...",                 // type=prompt 时
            "timeout": 10,                   // 秒, 默认?
            "async": true,                   // 后台 fire-and-forget
            "statusMessage": "..."           // CLI 加载提示
          }
        ]
      }
    ]
  }
}
```

证据: `hookify/hooks.json:9-12` (timeout 10), `git/.claude-plugin/plugin.json:30-36` (async + timeout 500), `caveman/.claude-plugin/plugin.json` (statusMessage), `claude-obsidian-marketplace/hooks.json:11-14` (`type: "prompt"` 注入文本).

---

## B. Plugin manifest 完整字段

### B.1 `.claude-plugin/plugin.json` 字段表

| 字段 | 类型 | 必需 | 用途 | 实证 |
|---|---|---|---|---|
| `name` | string | ✅ | 插件 id (`/cortex:foo` 中的 `cortex`) | 全部样本 |
| `version` | string | ✅ | semver | `task/.claude-plugin/plugin.json:3` |
| `description` | string | ✅ | UI / install 描述 | 全部 |
| `author` | object `{name,email?,url?}` | 推荐 | — | 全部 |
| `license` | string | 推荐 | SPDX | `task/.../plugin.json:12` |
| `homepage` | string (url) | 可选 | — | `task/...:11` |
| `repository` | string (url) | 可选 | — | `task/...:12` |
| `keywords` | string[] | 可选 | marketplace 搜索 | `task/...:13-22` |
| `agents` | string[] (paths) 或 dir glob | 可选 | sub-agent .md 文件列表 | `task/...:23-29` |
| `skills` | string (dir path) | 可选 | skill 根目录, 自动扫描子目录 SKILL.md | `task/...:30` (`"./skills/"`) |
| `commands` | string[] (paths) | 可选 | slash command .md 列表 | `git/...:22-24` |
| `hooks` | object 或 string (file path) | 可选 | 内联 或 指向 `hooks/hooks.json` | `task/...:31-42` 内联;  其他用 `./hooks/hooks.json` |
| `mcpServers` | string (path to .mcp.json) | 可选 | plugin 自带 MCP server 声明 | `template/.../plugin.json:28` (`"./.mcp.json"`) |
| `outputStyles` | string (dir) | 可选 | 输出样式 .md 目录 | `template/.../plugin.json:29` |
| `lspServers` | string (path) | 可选 ⚠ | LSP 服务声明 | `template/.../plugin.json:30` (本仓库扩展;官方未确认) |
| `statusLine` ⚠ | object/string | 可选 | 状态行脚本, **样本未见在 plugin.json 内声明**, 仅在 user `settings.json` | 反向证据: 全部 plugin 样本均无此字段 |

### B.2 内置环境变量

| 变量 | 含义 | 用法实证 |
|---|---|---|
| `${CLAUDE_PLUGIN_ROOT}` | 当前 plugin 根目录绝对路径 | `hookify/hooks.json:9`; `template/.../plugin.json:37`; 全部样本 |
| `CLAUDE_HOOK_EVENT` ⚠ | 当前 hook 事件名 | kioku injector resolveHookEvent fallback (line 30-34) |
| `KIOKU_NO_LOG`, plugin-specific | plugin 自定义 env | `~/.claude/settings.json` SessionEnd block |

⚠ payload 主推荐用 stdin JSON, env 变量仅 fallback.

### B.3 Skill 目录约定

每个 skill = `<skill-dir>/SKILL.md`, frontmatter:

```yaml
---
name: save                      # skill id (与目录名匹配推荐)
description: >                  # 触发文案 — 多行 YAML, 含触发词
  Save the current conversation ...
  Triggers on: "save this", "/save", "file this", ...
allowed-tools: Read Write Edit Glob Grep   # 空格分隔, 收紧工具集
---
```

实证: `claude-obsidian-marketplace/skills/save/SKILL.md:1-10`, `caveman/skills/caveman-help/SKILL.md:1-7`.

要点 (从样本归纳):

- `description` 内的 "Triggers on: ..." 列出明确字面触发词 — 是 Claude 自动激活 skill 的关键信号
- `allowed-tools` 限定 skill 内可调工具子集; 越窄越易自动激活 (主 agent 评估"能否做"时的判据)
- `references/`, `assets/` 等子目录可被 skill 自身 Read 加载 (kepano `obsidian-skills` 约定)

### B.4 Agent (sub-agent) frontmatter

```yaml
---
name: cavecrew-investigator
description: >
  Read-only code locator. Returns file:line table for ...
tools: Read, Grep, Glob, Bash
model: haiku                    # 可指定 haiku / sonnet / opus
color: cyan                     # UI 显示色 (omob 样本)
---
```

实证: `caveman/agents/cavecrew-investigator.md:1-9`, `omob/agents/transcript-summarizer.md:1-6`.

要点:

- `tools` 字段**逗号分隔** (与 skill `allowed-tools` 空格分隔不同 — 注意!)
- `model: haiku` 强制 sub-agent 用 haiku 降本 (`cavecrew-*` 全部 haiku)
- agent 输出回主 agent: 通过 stdout (主线 Task tool 拿到 final message)
- agent 内**不可调用 AskUserQuestion** 的限制由 plugin 作者在 prompt 中显式声明 (omob `socratic-interviewer.md:24-26`); 平台层不强制
- agent 嵌套: agent 内是否能 spawn agent 未在样本中确认; CLAUDE.md 用户规则约束 "并行 ≤ 2"

### B.5 Command frontmatter

```yaml
---
description: "Search and recall past documents..."
argument-hint: "<query>"             # CLI 提示
allowed-tools: Bash, Read, Glob, Grep, AskUserQuestion, Agent
model: haiku                          # ⚠ 可选, 让命令以 haiku 跑
---

## Context
- VAR: !`shell command`               # 内联 shell, 结果注入 prompt
- ${CLAUDE_PLUGIN_ROOT} 可用

## Your Task

... {{ARGUMENTS}} ...                 # 整体参数
$1 $2 ...                              # 位置参数 (官方 docs;样本中较少)
```

实证: `omob/commands/recall.md:1-9` (含 `!`...`` 内联 shell + `{{ARGUMENTS}}`), `omob/commands/refactor.md:1-7` (`AskUserQuestion, Agent` 在 allowed-tools 内).

要点:

- `allowed-tools` **逗号分隔** (与 skill 空格分隔不同 — 平台不一致, 易踩坑)
- `!`...`` 在 Context 节内联 shell, 输出嵌入到 system prompt — 比 hook 更轻量, 无需独立脚本
- `{{ARGUMENTS}}` 整体参数; `$1 $2` 位置参数 (官方 docs, 样本未见)
- `argument-hint`: 推荐格式 `<required>` `[optional]` `[recent N | from YYYY-MM-DD to ...]` (omob `restore-history.md:3`)
- 命令内**没有 import skill 语法**; 实践是直白写 "Read the `wiki` skill. Then run ..." (`claude-obsidian-marketplace/commands/wiki.md:5`)

---

## C. MCP server 与 plugin 的关系

| 维度 | 实证 | 备注 |
|---|---|---|
| plugin.json 内声明 | `template/.../plugin.json:28` `"mcpServers": "./.mcp.json"` | 字段值是**指向文件的路径**, 不是内联对象 |
| `.mcp.json` schema | 与全局 `~/.mcp.json` 同 — `{mcpServers: {name: {command, args, env}}}` | 用户 `~/.claude/.mcp.json` 实证 (305B 文件) |
| prompts / resources / tools | MCP server 自身决定; plugin 仅声明 server, **不在 plugin.json 里再描述具体 prompt/resource** | obsidian MCP server 实证 (mcp__obsidian__obsidian_*) |
| 调用名空间 | `mcp__<server-name>__<tool-name>` | 当前 session 工具列表 |
| 命令/skill 调用 MCP | 通过 `allowed-tools: mcp__obsidian__obsidian_get_file_contents, ...` 显式列出 | omob 命令样本 |

cortex 含义:

- 直接复用 user-level `~/.claude/.mcp.json` 中已配置的 obsidian server (推荐)
- 也可在 `cortex/.mcp.json` 自带一份, 安装时覆盖 (但需用户已启动 obsidian + REST API 插件)

---

## D. Skill 触发机制

来自样本与 `~/.claude/CLAUDE.md` 用户规则推断:

1. 主 agent 在每轮决策时, 把"已加载 skill 列表"(`name + description`) 作为可选项
2. 自然语言 / slash 命令命中 `description` 中的触发词 → 激活
3. 激活后 SKILL.md 全文加载, `allowed-tools` 收紧工具集
4. 跨 skill 调用: 在 SKILL.md 文末 "Read the `<other-skill>` skill" 触发链式加载 (claude-obsidian `wiki.md` pattern)

边界:

- **skill** = 知识 + 流程模板, 主 agent 自决调用, 持续到任务结束
- **command** = 用户显式 `/foo`, 一次性, 内可声明 `allowed-tools`
- **agent** = 隔离上下文 + 独立 model, 主 agent 通过 Task 工具调度, 输出回流

---

## E. Agent 系统细节

| 维度 | 实证/约定 |
|---|---|
| 调度 | 主 agent 用 `Task` 工具 spawn; sub-agent 启动后是独立 conversation |
| context isolation | sub-agent 不见主对话历史 — 必须 self-contained prompt (`~/.claude/CLAUDE.md` 上下文闸) |
| 输出回传 | sub-agent 最终 message 文本 = Task 工具返回值 |
| `tools: A, B` | 收紧可用工具 (caveman `cavecrew-builder` 无 Bash → 无法 push/rm) |
| `model: haiku` | 强制小模型, 适合 reviewer/locator (caveman 三件套全用 haiku) |
| 嵌套 | 平台未禁止, 用户规则建议 ≤ 2 并发 (`~/.claude/CLAUDE.md` 硬性约束) |
| worktree 隔离 ⚠ | `notify` 插件含 `WorktreeCreate`/`WorktreeRemove` hook, 暗示 sub-agent 可在 git worktree 跑 (实验性) |
| AskUserQuestion 在 agent 内 | 平台未禁; 用户规则 "Agent 内用 AskUserQuestion" (`~/.claude/CLAUDE.md`) |
| `color` | UI 显示色, omob 用 `cyan`/`blue`/`yellow` 区分角色 |

---

## F. Slash command 高级特性

汇总 (参 §B.5 + 实证):

| 特性 | 写法 | 来源 |
|---|---|---|
| `argument-hint` | `<query>` / `[topic]` / `[recent N \| from YYYY-MM-DD to ...]` | omob `recall.md:3`, `restore-history.md:3` |
| `$ARGUMENTS` / `{{ARGUMENTS}}` | 整体参数注入 prompt | omob `recall.md:14` |
| `$1 $2` | 位置参数 | 官方 docs (样本少见, 推断⚠) |
| `allowed-tools` | 逗号分隔, 含 MCP `mcp__server__tool` | omob commands |
| `model:` | frontmatter 指定模型 | 官方 docs (样本少见) |
| 内联 shell | `!\`cmd\`` 在 `## Context` 节, 输出嵌入 prompt | omob commands 全部 |
| 调用 skill | "Read the `<skill>` skill. Then ..." 自然语言 | claude-obsidian `wiki.md:5` |
| 调用 agent | `allowed-tools: ..., Agent` + 在 prompt 中描述 spawn 哪个 agent | omob `refactor.md:5` |
| `${CLAUDE_PLUGIN_ROOT}` | 命令体可用 | template plugin |
| permissions 交互 | `allowed-tools` 列表绕过 ask;否则按 user `settings.json#permissions` | `~/.claude/settings.json:23-26` `defaultMode: "bypassPermissions"` |

---

## G. settings.json 三层 + 字段表

层级 (从低到高优先):

1. `~/.claude/settings.json` (user) — `~/.claude/settings.json` 实证 5.7K
2. `<project>/.claude/settings.json` (project, checked in)
3. `<project>/.claude/settings.local.json` (project local, gitignored)

主字段:

| 字段 | 类型 | 用法 | 实证 |
|---|---|---|---|
| `env` | object | 进程级环境变量, e.g. `ANTHROPIC_BASE_URL` | `~/.claude/settings.json:2-15` |
| `permissions.deny` | string[] | 黑名单工具/path | `~/.claude/settings.json:24` |
| `permissions.defaultMode` | `bypassPermissions`/`ask`/`acceptEdits`/`plan` | 默认权限态度 | `~/.claude/settings.json:25` |
| `hooks` | object (与 plugin hooks.json 同结构) | user 级 hook | `~/.claude/settings.json:27-100+` |
| `statusLine` | `{type:"command", command:"..."}` | 状态行脚本 | 推断 (官方 docs) |
| `fileSuggestion` | `{type, command}` | tab 补全 | `~/.claude/settings.json:16-19` |
| `cleanupPeriodDays` | number | session 保留 | `~/.claude/settings.json:20` |
| `attribution`, `includeCoAuthoredBy` | git 提交署名 | `~/.claude/settings.json:21-22` |

cortex 触碰策略:

- 只读 user / project settings (诊断用)
- **不写** user settings (避免污染); plugin 自带 `hooks.json` 自动激活
- project `settings.local.json` 仅 `/cortex:install` 在用户同意后写 (例: 锁定 `OBSIDIAN_VAULT_PATH`)

---

## H. 较新功能盘点

来自当前 session injected reminders 与 ToolSearch deferred tools 列表:

| 功能 | 触发/形态 | cortex 关联 |
|---|---|---|
| **Background tasks / SubagentStop** | `Task` spawn + `SubagentStop` hook | cortex 可在 SubagentStop 触发 mini save |
| **Output styles** | plugin 字段 `outputStyles: "./styles/"` + SessionStart 注入 | cortex 可提供 "wiki-mode" output style |
| **Memory system / CLAUDE.md 三层** | user `~/.claude/CLAUDE.md` + project `CLAUDE.md` + local | cortex 不应改 user 层, 可建议在 project CLAUDE.md 注入 vault 提示 |
| **Extended thinking** | model-side, plugin 不直接控 | n/a |
| **Computer use / Browser tools** | 当前 env 含 `chrome-devtools-mcp` skills | n/a (cortex 不需要) |
| **Deferred tools (ToolSearch)** | `ENABLE_TOOL_SEARCH=true` 见 `~/.claude/settings.json:11`. 调用前 ToolSearch 加载 schema | cortex 可声明 obsidian MCP 为 deferred 减少冷启动 token |
| **CronCreate / ScheduleWakeup** ⚠ | 推断为 deferred tools, 调研 session 未直接列出 schema | cortex `/cortex:cron` 可优先用此而非外部 launchd (若 GA) |
| **EnterPlanMode** | 与 `CLAUDE_CODE_PLAN_MODE_REQUIRED=true` 联动 (`~/.claude/settings.json:9`) | cortex `/cortex:refactor` 可强制 plan mode |
| **SendMessage** ⚠ | Agent Teams 间通信 (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`) | n/a 暂不用 |
| **File-state tracking** | Read 后才能 Edit (硬约束) | cortex skill 必须先 Read vault 文件再 Edit |
| **Persisted output (>10KB)** | tool result > 10KB 自动落盘成临时文件 | cortex `/cortex:lint` 大报告天然适配 |
| **Agent Teams** | 实验性, env flag | cortex MVP 不用 |

---

## I. 本地参考交叉表

| Source | Path | 用途 |
|---|---|---|
| 用户全局规则 | `~/.claude/CLAUDE.md` | Agent 选择五道闸 / 硬性约束 |
| 工具路由 | `~/.claude/TOOLS.md` | code search / web / 知识管理 工具映射 |
| user settings 模板 | `~/.claude/settings.json` | hooks 实例 + env + permissions |
| obsidian MCP 配置 | `~/.claude/.mcp.json` (305B) | mcp__obsidian__* 来源 |
| kioku 实战 hook | `~/.claude/plugins/cache/megaphone-tokyo/kioku/0.7.0/hooks/wiki-context-injector.mjs` | v2 wrapped JSON output 教科书 |
| claude-obsidian hooks | `~/.claude/plugins/marketplaces/claude-obsidian-marketplace/hooks/hooks.json` | SessionStart/PostCompact/Stop/PostToolUse 全套范式 |
| omob hook + agent | `~/.claude/plugins/marketplaces/omob/{hooks/hooks.json,agents/*.md,commands/*.md}` | command frontmatter / agent JSON 输出 / 动态 Context |
| caveman | `~/.claude/plugins/marketplaces/caveman/{hooks/hooks.json,agents/*.md,skills/*/SKILL.md}` | skill description 触发词 + agent tools 收紧 + statusMessage |
| 官方 explanatory style | `~/.claude/plugins/marketplaces/claude-plugins-official/plugins/explanatory-output-style/hooks-handlers/session-start.sh` | output style = SessionStart 注入 (无独立 outputStyles 文件) |
| hookify | `~/.claude/plugins/marketplaces/claude-plugins-official/plugins/hookify/hooks/hooks.json` | timeout 字段 + 4 类基础 hook |
| warp | `~/.claude/plugins/marketplaces/claude-code-warp/plugins/warp/hooks/hooks.json` | matcher: `idle_prompt` for Notification |
| 本仓库 task | `plugins/tools/task/.claude-plugin/plugin.json:23-42` | hooks 内联声明范式 |
| 本仓库 git | `plugins/tools/git/.claude-plugin/plugin.json:30-36` | `async: true, timeout: 500` |
| 本仓库 notify | `plugins/tools/notify/.claude-plugin/plugin.json:20-260` | hook 事件清单 (含未公开⚠) |
| 本仓库 template | `plugins/template/.claude-plugin/plugin.json:28-30` | mcpServers / outputStyles / lspServers 字段实证 |
| 本仓库 memory docs | `plugins/memory/docs/hooks.md:1-74` | hooks 用途中文文档范式 |

---

## J. 对 cortex PRD §3-§4 的增量补丁

> 以下 ≥12 条 patch, 按 PRD 章节序号锚定. 每条 = `[位置] 补丁内容 — 依据`

### Patch 1 — `plugin.json` 全字段化

`plugins/tools/cortex/.claude-plugin/plugin.json` 新增字段:

```jsonc
{
  "agents": ["./agents/cortex-curator.md"],   // 新增 sub-agent 见 Patch 7
  "skills": "./skills/",
  "commands": ["./commands/cortex-install.md", "./commands/cortex-new.md", ...],
  "outputStyles": "./styles/",                // 见 Patch 9
  "mcpServers": "./.mcp.json",                // 见 Patch 12 (可选)
  "hooks": "./hooks/hooks.json"               // 改用文件引用而非内联, 利于复杂逻辑
}
```

依据: `plugins/template/.claude-plugin/plugin.json:23-30` 全字段实证.

### Patch 2 — SessionStart 拆 matcher 三态

`hooks/hooks.json` SessionStart 节拆成两个 entry:

```jsonc
"SessionStart": [
  { "matcher": "startup|resume",
    "hooks": [{ "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session_start.sh" }] },
  { "matcher": "clear|compact",
    "hooks": [{ "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/restore_hot.sh" }] }
]
```

依据: `claude-obsidian-marketplace/hooks/hooks.json:5` matcher `startup|resume` 与 PostCompact 分离;  `clear|compact` matcher 推断⚠ 但 PostCompact 已在 §A.1 #10 实证.

### Patch 3 — 增加 PostCompact 注入

PRD §3.1 缺 PostCompact. 补:

```jsonc
"PostCompact": [{
  "matcher": "",
  "hooks": [{ "type": "prompt",
    "prompt": "Hook context lost on compact. If <vault>/wiki/hot.md exists, silently re-read to restore. Do not announce." }]
}]
```

依据: `claude-obsidian-marketplace/hooks/hooks.json:18-28` 直接复用.

### Patch 4 — Stop 之外加 SessionEnd 双保险

PRD §3 仅 Stop, 但 Stop 可能被循环阻断. 补 SessionEnd hook 触发 git commit + cortex-save:

```jsonc
"SessionEnd": [
  { "hooks": [
    { "type": "command",
      "command": "[ \"${CORTEX_NO_LOG:-0}\" = \"1\" ] || ${CLAUDE_PLUGIN_ROOT}/hooks/session_end.sh" }
  ]}
]
```

依据: `~/.claude/settings.json` SessionEnd 块 (kioku auto-commit pattern), 与 Stop 互补.

### Patch 5 — PreToolUse 拦截危险 obsidian 操作 (二次确认)

```jsonc
"PreToolUse": [{
  "matcher": "mcp__obsidian__obsidian_delete_file|mcp__obsidian__obsidian_patch_content",
  "hooks": [{ "type": "command",
    "command": "${CLAUDE_PLUGIN_ROOT}/hooks/guard_destructive.sh" }]
}]
```

`guard_destructive.sh` 检测 `tool_input.path` 命中 `wiki/index.md|wiki/hot.md|.obsidian/`, 输出:

```json
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"cortex: deletion of pinned vault file"}}
```

依据: §A.2 PreToolUse permissionDecision 字段; matcher 支持 `mcp__server__tool` glob (notify plugin 实证).

### Patch 6 — PostToolUse 微 lint

`mcp__obsidian__obsidian_*` 写入后跑 frontmatter / wikilink lint:

```jsonc
"PostToolUse": [{
  "matcher": "mcp__obsidian__obsidian_put_content|mcp__obsidian__obsidian_patch_content",
  "hooks": [{ "type": "command", "async": true, "timeout": 30,
    "command": "${CLAUDE_PLUGIN_ROOT}/hooks/micro_lint.sh" }]
}]
```

`async: true` 见 `git/.claude-plugin/plugin.json:33`.

### Patch 7 — 新增 sub-agent `cortex-curator`

`agents/cortex-curator.md`:

```yaml
---
name: cortex-curator
description: >
  Read-only vault auditor. Returns structured findings (orphan pages, dead wikilinks,
  stale claims, missing frontmatter). Refuses to fix.
  Triggers on "/cortex:lint --deep", "audit my vault".
tools: Read, Grep, Glob, Bash
model: haiku
---
```

并在 SubagentStop 触发 `cortex-save` 写入 `wiki/log/`:

```jsonc
"SubagentStop": [{ "hooks": [{ "type": "command",
  "command": "${CLAUDE_PLUGIN_ROOT}/hooks/save_subagent_findings.sh" }] }]
```

依据: `caveman/agents/cavecrew-investigator.md:1-9` haiku read-only 范式; §A.1 #7 SubagentStop 实证.

### Patch 8 — skill `allowed-tools` 全量收紧

| skill | 当前 PRD | 修订 `allowed-tools` |
|---|---|---|
| `setup` | (未指定) | `Bash Read Write Edit Glob` |
| `save` | (未指定) | `Read Write Edit mcp__obsidian__obsidian_put_content mcp__obsidian__obsidian_get_file_contents` |
| `query` | (未指定) | `Read Grep Glob mcp__obsidian__obsidian_simple_search mcp__obsidian__obsidian_complex_search` |
| `ingest` | (未指定) | `Read Write Edit WebFetch mcp__obsidian__obsidian_put_content` |
| `lint` | (未指定) | `Read Grep Glob Bash mcp__obsidian__obsidian_get_file_contents` |

依据: `claude-obsidian-marketplace/skills/save/SKILL.md:8` `allowed-tools: Read Write Edit Glob Grep` (空格分隔).

### Patch 9 — 提供 output style "cortex-wiki-mode"

`styles/cortex-wiki-mode.md` (frontmatter 推断⚠):

```yaml
---
name: cortex-wiki-mode
description: Pre-prompt assistant to always cite vault pages with [[wikilinks]] and check wiki/index.md before answering.
---
You are operating with a connected Obsidian vault at $OBSIDIAN_VAULT.
Before answering knowledge questions, read wiki/index.md and wiki/hot.md.
Cite sources via [[wikilink]] in markdown.
```

激活仍由 SessionStart 注入 (因官方 explanatory 实测就是 SessionStart hack — 见 §H 与本地 `explanatory-output-style/hooks-handlers/session-start.sh`).

### Patch 10 — slash command `argument-hint` 标准化

| Command | argument-hint |
|---|---|
| `/cortex:install` | `[lyt|zettel|para|blank] [--vault=PATH]` |
| `/cortex:new` | `<type> <title>` |
| `/cortex:lint` | `[--fix] [--scope=<glob>] [--deep]` |
| `/cortex:refactor` | `<rename|merge|split|fold> [args...]` |
| `/cortex:cron` | `<install|status|run> [job]` |
| `/cortex:search` | `<query>` |
| `/cortex:save` | `[topic]` |
| `/cortex:doctor` | `[--verbose]` |

`allowed-tools` 全部**逗号分隔**. 含 `AskUserQuestion, Agent` 当需交互或 spawn agent (omob `refactor.md:5` 范式).

### Patch 11 — 不写 user `settings.json`, 仅 project `settings.local.json` 可选

`/cortex:install` 流程:

1. plugin 自带 `hooks.json` 已生效, 无需写 user settings
2. 询问: "锁定 `OBSIDIAN_VAULT` 到本仓库?" → yes 才写 `<repo>/.claude/settings.local.json` 的 `env.OBSIDIAN_VAULT`
3. 永不触碰 `~/.claude/settings.json`

依据: §G 三层模型 + 用户规则 "禁主动 git commit" (settings 写入也类比为污染).

### Patch 12 — `.mcp.json` 自带 obsidian server 声明 (可选 fallback)

`plugins/tools/cortex/.mcp.json`:

```jsonc
{
  "mcpServers": {
    "obsidian": {
      "command": "uvx",
      "args": ["mcp-obsidian"],
      "env": { "OBSIDIAN_API_KEY": "${OBSIDIAN_API_KEY}", "OBSIDIAN_HOST": "127.0.0.1" }
    }
  }
}
```

`plugin.json` 加 `"mcpServers": "./.mcp.json"`. 用户已有 `~/.claude/.mcp.json` 时优先级如何 — 实测推断⚠ user 层覆盖. 装机文档需提示.

依据: `template/.claude-plugin/plugin.json:28`; `~/.claude/.mcp.json` 305B 实证.

### Patch 13 — Notification hook idle_prompt 提醒

PRD 未提. 补 (轻量, 可选):

```jsonc
"Notification": [{
  "matcher": "idle_prompt",
  "hooks": [{ "type": "command",
    "command": "${CLAUDE_PLUGIN_ROOT}/hooks/idle_remind.sh" }]
}]
```

`idle_remind.sh` 检查 `wiki/log/` 当日是否已有落档, 否则在 stderr 提示 (不阻塞).

依据: `claude-code-warp/.../hooks.json` Notification + `idle_prompt` matcher 实证.

### Patch 14 — UserPromptSubmit 注入"先搜库"提示 (cold start)

PRD §3 SessionStart 已注入, 但 PostCompact 后用户接续输入易绕过. 补:

```jsonc
"UserPromptSubmit": [{
  "hooks": [{ "type": "command",
    "command": "[ -f wiki/hot.md ] && [ \"$(stat -f %m wiki/hot.md)\" -lt $(($(date +%s)-1800)) ] && echo '{\"hookSpecificOutput\":{\"hookEventName\":\"UserPromptSubmit\",\"additionalContext\":\"Reminder: hot.md stale >30min, consider re-reading.\"}}' || true",
    "timeout": 3 }]
}]
```

依据: §A.1 #3 + `caveman/.claude-plugin/plugin.json` UserPromptSubmit 范式.

### Patch 15 — 持久化输出 + file-state 约束写入 skill 文档

`skills/save/SKILL.md` / `skills/ingest/SKILL.md` 在 "## Workflow" 显式声明:

> 1. **必先 Read** 目标文件再 Edit (CC file-state tracking 硬约束)
> 2. lint 输出 > 10KB 时, CC 自动落盘到临时文件 — skill 应感知并把路径回报用户

依据: §H "File-state tracking" + "Persisted output (>10KB)" 实证.

---

## Caveats / Not Found

1. `notify` plugin 列出的 `PostToolUseFailure` / `StopFailure` / `TeammateIdle` / `TaskCompleted` / `InstructionsLoaded` / `ConfigChange` / `CwdChanged` / `FileChanged` / `WorktreeCreate` / `WorktreeRemove` 在官方公开 docs 未直接确认, **可能是本地 fork 自定义或实验性**. cortex MVP 不依赖.
2. `permissionDecision: ask` 的 UI 真实行为 (是否 popup) 未在样本中实测, 仅 PRD/docs 描述.
3. `$1 $2` 位置参数 vs `{{ARGUMENTS}}` 在样本中**几乎全用后者**, 前者推断⚠.
4. `outputStyles` 字段虽在 `template/.claude-plugin/plugin.json:29` 出现, 但**对应目录与文件 schema 在两个 official 样本里都没出现** — official `*-output-style` 插件实际是用 SessionStart additionalContext hack. cortex Patch 9 同采用此实战路径, 不依赖未验证的 `outputStyles` 自动加载.
5. CronCreate / ScheduleWakeup / SendMessage / EnterPlanMode 这类 deferred tools 当前 session 上下文中**未直接列出 schema**, 推断为 ENABLE_TOOL_SEARCH 触发后才加载. cortex Patch (cron) 仍优先 launchd/cron 外部触发 + 内置 `/cortex:cron` 脚本生成.
6. 远程官方 docs (docs.claude.com / docs.anthropic.com) 在本调研未直接 fetch, 全部依据本地真实安装 + session env 推断. 任何 ⚠ 标记字段在落地前需用 `claude --settings ... -p` 实测验证 (CLAUDE.md §代码质量检查规范).

字数: ~4400.
