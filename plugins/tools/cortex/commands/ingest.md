---
description: 深度分析当前目录摄取到 cortex vault (无入参; 自动识别 git repo / 普通项目)
---

# /cortex:ingest

[AUTO_MODE persistent: 禁询问, 禁中止, AI 自决执行]

**默认行为**: 深度分析**当前工作目录** ($PWD) 摄取到 cortex vault。

## 强制流程

1. 从 `~/.cortex/config.json` 读 `vault`
2. **判定目录类型** (按下表自决, 禁问):

   | 检测 | 类型 | 落档位置 |
   |------|------|---------|
   | `git remote get-url origin` 命中 `github.com[:/]<org>/<repo>` 或 `<host>/<org>/<repo>.git` 模式 | **代码仓库** | `知识库/来源/代码仓库/<host>/<org>/<repo>.md` (主条目) + `知识库/领域/<host>/<org>/<repo>/<topic>.md` (子文档) |
   | `git remote get-url origin` 命中 `gitlab.com` / 自建 GitLab (host 含 `gitlab`) | **代码仓库** | 同上 (host=gitlab.com 或对应自建 host) |
   | 有 `.git` 但 origin 非 github/gitlab (如纯本地 git) | **代码仓库** | `知识库/来源/代码仓库/local/<basename>.md` |
   | 无 `.git`, 有 `pyproject.toml` / `package.json` / `Cargo.toml` / `go.mod` 等项目文件 | **项目** | `知识库/项目/<basename>/index.md` (主) + `知识库/项目/<basename>/<topic>.md` (子) |
   | 其余 (普通目录) | **项目** (按目录名兜底) | `知识库/项目/<basename>/index.md` |

3. **深度分析当前目录** (由 AI 自决执行, 用工具组合):
   - `Bash` 列结构: `find . -maxdepth 3 -type f \( -name '*.md' -o -name 'README*' -o -name '*.toml' -o -name '*.json' -o -name 'Makefile' \) | head -50`
   - `Read` README/docs/核心配置文件
   - `Glob` + `Read` 关键源码入口 (按语言识别: src/, lib/, cmd/, main.* )
   - `git log --oneline -20` 看近期演进 (若是 git repo)
   - 综合产出: 项目/仓库**主条目** (架构 / 关键概念 / 入口点 / 依赖) + 若干**子文档** (具体模块/决策/陷阱)

4. **落档** (用 MCP `cortex_save` 或直接 Write):
   - 代码仓库: `kind=domain`, `host`/`org`/`repo` 填好, frontmatter `source_kind: repo`, `tags: [source/repo, host/<host>]`
   - 项目: `kind=concept` 或 `domain` (按内容自决), 主条目 + 子文档双层

5. 摄取完成后 **直接给最终报告** (无问句):

   ```
   target_type: <repo|project>
   location: <落档根路径>
   files_ingested: <N>
   main_doc: <主条目路径>
   sub_docs: [<路径>, ...]
   ```

## 显式 args 走传统路径

若 wrapper 异常带入 args (url / file / git url / 远程 dir 等): auto-detect 类型, 按 cortex-ingest SKILL 标准流程处理 (url_security → fetch → html_sanitize → masking → save)。

## AUTO_MODE (shell wrapper 触发, persistent)

**核心原则**: "禁问" ≠ "中止". AI 必须**自决并执行直至任务完成**。遇歧义按推荐默认值执行; 工具不熟悉则尝试其他工具组合 (Bash/Edit/Write/MCP/WebSearch/WebFetch/Read 现有样本); 禁报"需人工"/"AI 不会"/"建议后续处理"。

### 严禁 (任一出现 = 契约违反)

| # | 禁止 |
|---|------|
| 1 | 任何"修复建议"/"建议"/"推荐操作" 章节/表格/列表 (`## 修复建议`, `\| 类型 \| 操作 \|`) |
| 2 | 用户确认问句 (`需确认?`, `是否执行?`, `要继续吗?`, `ok?`, 末尾问号) |
| 3 | AskUserQuestion 调用 (allowed-tools 已禁) |
| 4 | "下一步"/"后续"/"如需"/"可选" 导引 |
| 5 | "需人工"/"待人工"/"建议人工" 推卸辞令 |
| 6 | "AI 能力不足"/"无法自动" 类借口 |
| 7 | 报状态后停 (除非工具客观失败: 磁盘只读/权限拒绝/git lock) |
