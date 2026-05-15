# cortex-save — 目录路由 + lang 对齐

## type → 路径模板

| type | 路径模板 |
|------|---------|
| concept | `知识库/领域/<域>/<kebab>.md` (--domain 可选; 缺则 `领域/未分类/`. AI 自决 6 域: 创作/学习/工作/技术/生活/金融) |
| entity | 若属 repo → `知识库/项目/<host>/<org>/<repo>/<entity-kebab>.md`; 独立 → `知识库/领域/<域>/<entity-kebab>.md` |
| project | `知识库/项目/<host>/<org>/<repo>/<slug>.md` (本地 fallback: 相对 $HOME 拆段, 不足 3 段补 `_local`) |
| domain | (alias of project) `知识库/项目/<host>/<org>/<repo>/<slug>.md` |
| source | `知识库/收件箱/<host>-<slug>.md` (repo host 严禁走此, 必须 kind=project; arxiv/网页/书籍统一落收件箱待 digest 分发) |
| reflection | `知识库/日记/日/<YYYY-MM>/<YYYY-MM-DD>-反思-<slug>.md` (作日记一项) |
| question / fleeting | `知识库/收件箱/<slug>.md` (待 digest 分发) |
| inbox | `知识库/收件箱/<host>-<slug>.md` (host 提供时) 或 `知识库/收件箱/<slug>.md` |
| dashboard | `_assets/dashboards/<topic>-dashboard.md` |
| journal / log | `知识库/日记/日/<YYYY-MM>/<YYYY-MM-DD>.md` (仅日, 周/月/年 已废弃) |

## entity / concept 域选择 (--domain 缺时 AI 自决)

读 body 前 500 字, 匹配 6 域:

- **创作**: 写作 / 小说 / 诗 / 剧本 / 设计 / 音乐
- **学习**: 笔记 / 课程 / 读书 / 语言 / 教材
- **工作**: 任务 / 会议 / 项目管理 / 沟通 / OKR
- **技术**: 代码 / 编程 / 算法 / 工具 / 协议 / 框架
- **生活**: 日常 / 食物 / 旅行 / 健康 / 家居
- **金融**: 股票 / 投资 / 财务 / 税务

无匹配 → `领域/未分类/`. 允许创建子目录 (如 `创作/写作/`, `技术/分布式系统/`)。

## 文件名 stem lang 对齐 (lint rule 20 path-lang-mismatch)

- **`vault.lang=zh-CN`**: 文件名 stem 用中文 (`架构.md` 而非 `architecture.md`); 已知专名 (项目名 / repo 名 / 配置名 / 协议名 / API 端点) 保 ASCII (如 `README.md` / `pyproject.md` / `OAuth2.md`)
- **`vault.lang=en`**: 文件名 stem 用英文; 不可翻译专名保原文 → 加 frontmatter `path_lang_exempt: true`
- `知识库/项目/<host>/<org>/<repo>/` 前 3 层路径段 (host/org/repo) 由 git remote 决定, 不受 lang 约束 (lint 已豁免)
- 不确定时 (中英混排 / 行业专名) frontmatter 加 `path_lang_exempt: true` 显式豁免

## 写入策略

- 默认**不覆盖**已存在文件 — 文件名冲突时追加 `-2`, `-3`...
- frontmatter `updated` 字段每次写入更新; `created` 仅首次设置
- 一次落档失败不阻断其它步骤 (e.g. backlink 失败 → 仅记录, 主文件已写)
