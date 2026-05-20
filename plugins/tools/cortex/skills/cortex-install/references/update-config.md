# cortex-install — 用户态 wrapper / 卸载 / 输出格式

## 用户态 wrapper (24 个)

`install_wrappers.sh` 在 `~/.cortex/scripts/` 生成 23 个用户入口:

- **slash 委托 (10)**: `lint.sh` / `dashboard.sh` / `doctor.sh` / `init.sh` / `promote.sh` / `forget.sh` / `digest.sh` / `recall.sh` / `refactor.sh` / `ingest.sh`
- **shell only (2)**: `install_cron.sh` / `config.sh`
- **CLI 直接调 (11)**: `save.sh` / `search.sh` / `deep_search.sh` / `ingest_url.sh` / `ingest_file.sh` / `ingest_remote.sh` / `refresh_projects.sh` / `memory.sh` / `ledger.sh` / `session.sh` / `html_render.sh`

每个 slash wrapper 内部走 `python3 <abs>/cortex_stream.py -- claude --settings ... -p "/cortex:<name> auto"` (`auto` 后缀触发 AUTO_MODE 跳询问)。

## git auto-sync 询问 (P5)

`<vault>/.git` 存在时**必须**用 `AskUserQuestion` (禁文本式提问) 1 single-choice:

- 问: "vault 是 git repo, 是否启用 Stop hook 自动 commit?"
- 选项:
  - `关` (默认) → 写 `_meta/version.json`: `auto_commit=false, auto_push=false`
  - `仅 commit` → `auto_commit=true, auto_push=false`
  - `commit + push` → `auto_commit=true, auto_push=true`

提示用户: 启用 `commit + push` 前请自查 vault 不含 secret (P0 masking 只覆盖 ingest/save, 不护手写笔记)。详见 `docs/sync-git.md`。

vault 不是 git repo → 跳过, 不写两字段。

## 输出格式

```
解析 vault: /Users/.../knowledge/obsidian (源: env)
lang: zh-CN

[共享根]
✅ 写入 _meta/version.json (lang=zh-CN)
✅ 写入 _meta/lint-baseline.json
✅ 写入 _meta/memory-policy.yaml
✅ 写入 _meta/uri-index.json (空骨架)
✅ 写入 _meta/template-manifest.json
✅ 复制 _meta/triggers.yaml
✅ 复制 _meta/frontmatter-schema.yaml
✅ 创建 _meta/migrations/
✅ 复制 _templates/concept.md ... _index.md (7 既有)
✅ 复制 _templates/html/ (8 片段)
✅ 复制 _templates/memory/ (6 模板)
✅ 复制 _templates/knowledge/ (15 模板)
✅ 写入 index.md / hot.md

[知识库 namespace]
✅ 创建 项目/<host>/<org>/<repo>/
✅ 创建 领域/{创作,学习,工作,技术,生活,金融}/
✅ 创建 日记/日/ 收件箱/
✅ 复制 各层 _index.md

[记忆 namespace]
✅ 创建 L0-核心/ L1-长期/{procedural,semantic-stable}/ L2-中期/semantic/
✅ 创建 L3-短期/episodic/ L4-流水账/{ledger,sessions}/ working/ views/{consolidated}/
✅ 复制 5 个 L<N> _index.md

[仪表盘]
✅ 复制 总览.md / 知识库分布.md / 记忆-L0..L4 / 晋级候选 / 腐化监控 / 桥接 / cron 状态 / 固化流 (12 stub)

[根入口]
✅ 复制 主页.md (HTML 二维仪表盘骨架)
✅ 复制 焦点.md

[git auto-sync]
✅ auto_commit=false, auto_push=false (用户选 `关`)

[cron 注册]
✅ 已注册 launchd: lint / memory-promote / memory-forget (3 项)
⏭️  未选: dashboard / memory-compact / digest / memory-warden / memory-archive

[wrapper]
✅ 已生成 24 个 wrapper 到 ~/.cortex/scripts/

总结: 68 项写入, 5 项跳过, 0 项失败
下一步:
  - /cortex:doctor 验证 + 跑 `bash ~/.cortex/scripts/ledger.sh uri_index_rebuild` 初始化索引
  - 记忆 CRUD: ~/.cortex/scripts/memory.sh read|write|update|forget <uri>
  - 渐进召回: ~/.cortex/scripts/recall.sh <query>
  - 晋级检测: ~/.cortex/scripts/promote.sh [--dry-run]
  - 周报巩固: ~/.cortex/scripts/digest.sh [--week N]
```
