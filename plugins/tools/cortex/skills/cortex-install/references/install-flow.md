# cortex-install — vault 结构与安装流程

## 顶层结构

```
vault/
├── _meta/                       元数据 (version/policy/lint-baseline/uri-index/migrations)
├── _templates/                  模板 (含 html/ memory/ knowledge/ 子目录 + 8 既有 _index/concept/...)
├── _assets/                     图片/svg/HTML 复用资源
├── 主页.md                      全局入口 (HTML 二维仪表盘)
├── 焦点.md                      当前焦点 working set
├── 知识库/                      人类组织维度
├── 记忆/                        AI URI 寻址 + L0-L4 分级
├── 仪表盘/                      格式化看板 (HTML)
└── 归档/                        冷藏
```

## 知识库 (人类视角, 仅 4 子目录)

```
知识库/
├── 项目/<host>/<org>/<repo>/             github/gitlab + 本地项目 (本地走相对 $HOME 路径策略, 不足 3 段补 `_local`)
├── 领域/<域>/                            域名由用户/AI 自决创建 (创作/学习/工作/技术/生活/金融/未分类/...; 域下结构自由)
├── 日记/日/<YYYY-MM>/<YYYY-MM-DD>.md     仅日维度 (周/月/年 已废弃 — 历史数据归档到 归档/日记/<YYYY-QN>.md 季度桶)
└── 收件箱/                               落档兜底, 等 digest 分发到 项目/笔记 或 领域/<域>
```

域名不固化, 用户/AI 落档时自决创建。

## 记忆 (AI URI 寻址 L0-L4)

```
记忆/
├── L0-核心/                     不可篡改 (identity/values/...) — 写入需 user confirm + git tag
├── L1-长期/{procedural,semantic-stable}/   高 weight, 仅用户显式删除
├── L2-中期/semantic/            365 天未召回 → archive
├── L3-短期/episodic/            90 天未召回 → archive
├── L4-流水账/{ledger,sessions}/ append-only; 30 天后 gzip
├── working/                     当前 session (volatile)
└── views/{consolidated}/        派生视图 (recent/hot/candidates/alerts)
```

URI scheme: `L0://identity/me` / `L1://procedural/git-flow` / `L2://semantic/go/goroutine` / `L3://episodic/2026-05-12/T1430` / `L4://ledger/2026-05-12` / `L4://session/claude-code/sess-x`。

## 写共享根 (固定项)

- `_meta/version.json` — `{"lang": "<from Q2>", "preserve_transcript": true, "created": "<UTC ISO>"}`
- `_meta/lint-baseline.json` — `{"exempt": []}`
- `_meta/memory-policy.yaml` — 从 `<PLUGIN_ROOT>/templates/memory-policy.yaml` 复制; 定义 L0-L4 写入/遗忘/晋级 + recall + 9 cron 配置
- `_meta/uri-index.json` — 空骨架 `{"version": 1, "rebuilt_at": "<UTC ISO>", "count": 0, "entries": {}}`
- `_meta/template-manifest.json` — 复制 `<PLUGIN_ROOT>/templates/_manifest.json`
- `_meta/triggers.yaml` — 复制 `<PLUGIN_ROOT>/templates/triggers.yaml` (session_start hook 触发关键词基线)
- `_meta/frontmatter-schema.yaml` — 复制 `<PLUGIN_ROOT>/templates/frontmatter-schema.yaml`
- `_meta/migrations/` — `mkdir -p` (放 `.gitkeep`)
- `_templates/` — 完整复制 `<PLUGIN_ROOT>/templates/`:
  - 既有: `concept.md` / `entity.md` / `domain.md` / `dashboard.md` / `question.md` / `source.md` / `_index.md`
  - `html/` 子目录 (8 文件): `badge.html` / `card.html` / `timeline.html` / `canvas-heatmap.html` / `progressive-disclosure.html` / `mermaid-flowchart.md` / `mermaid-sankey.md` / `mermaid-mindmap.md`
  - `memory/` 子目录 (6 文件): `L0-core.md` / `L1-procedural.md` / `L1-semantic-stable.md` / `L2-semantic.md` / `L3-episodic.md` / `L4-session.md`
  - `knowledge/` 子目录 (15 文件): `project.md` / `source-{repo,web,paper,book}.md` / `domain-{concept,fact,method}.md` / `journal-{day,week,month,year}.md` / `reflection-{insight,connection,question}.md`
- `index.md` / `hot.md` — 空骨架 (frontmatter `type: meta`)

## 写业务结构

读 `<PLUGIN_ROOT>/presets/_structure.json` (44 seed_files):

**顶层 mkdir**: `知识库/` / `记忆/` / `仪表盘/` / `归档/` / `_assets/`

**知识库子目录**: 项目/ / 领域/ / 日记/日/ / 收件箱/ (见上文 4 子目录)

**记忆子目录**:
- `记忆/L0-核心/`
- `记忆/L1-长期/{procedural,semantic-stable}/`
- `记忆/L2-中期/semantic/`
- `记忆/L3-短期/episodic/`
- `记忆/L4-流水账/{ledger,sessions}/`
- `记忆/working/`
- `记忆/views/{consolidated}/`

**Seed files (44 按 `_structure.json:seed_files[]` 复制)**:
- 根入口 2: `主页.md` / `焦点.md` (`dst_key="."`)
- `_meta/memory-policy.yaml` 1
- 知识库 `_index.md` × 各层 (项目/领域/日记/收件箱)
- 记忆 `_index.md` × 5 (L0/L1/L2/L3/L4 顶层)
- 仪表盘 stub × 12: `总览.md` / `知识库分布.md` / `记忆-L0..L4.md` / `记忆-晋级候选.md` / `记忆-腐化监控.md` / `知识-记忆 桥接.md` / `记忆-cron 状态.md` / `固化流.md`
