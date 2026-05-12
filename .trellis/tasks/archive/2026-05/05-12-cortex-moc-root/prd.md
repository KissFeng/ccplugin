# PRD — MOC 移到 vault 根目录

## 背景

用户:
> 我希望 moc 的部分应该在根目录

现 cortex preset 把 MOC 文件放 `<vault>/moc/{home,topics-moc,projects-moc}.md` 子目录 (按 vault.lang 渲染目录名)。用户要直接放 vault 根。

理由:MOC 是顶级导航地图,放根目录访问更直观, vault 一进来就见 home.md。

## 目标

```
<vault>/
├── home.md           ← 原 moc/home.md (顶级 MOC)
├── topics-moc.md     ← 原 moc/topics-moc.md
├── projects-moc.md   ← 原 moc/projects-moc.md
├── hot.md
├── index.md
├── README.md
├── 10_concepts/
├── 30_domains/
... (其它业务目录)
```

`moc/` 子目录消失。

### 目标 2: 非 MOC 业务目录专用模板

用户:
> presets/seed 缺少非 moc 的模板

现 8 业务目录全复用同一 `seed/_index.md` 通用模板。改:各目录专用 `_index.md` 含该 bucket 用途说明 + 用法引导。

```
presets/seed/
├── home.md / topics-moc.md / projects-moc.md  (MOC, 直落 root)
├── concepts/_index.md     ← 概念目录: 抽象知识单元
├── entities/_index.md     ← 实体目录: 具体人/组织/产品/工具
├── domains/_index.md      ← 领域目录: host/org/repo 分层
├── sources/_index.md      ← 来源目录: URL/文献摄取
├── questions/_index.md    ← 问题目录: 未解决疑问
├── dashboards/_index.md   ← 仪表盘: Dataview/Bases 聚合
├── fleeting/_index.md     ← 临时笔记: 收件箱
└── archive/_index.md      ← 归档: 过时/合并内容
```

通用 `seed/_index.md` 删 (或保留作 fallback)。

## 范围

### 修改

- `plugins/tools/cortex/presets/_structure.json`:
  - `directories_keys[]` 删 `moc`
  - `seed_files[]` 3 个 moc 项 `dst_key` 改为 root sentinel (`"."` 或 `null` 或 `"root"`,选一个明确)
  - 也可分两段:`seed_dirs[]` (按 dst_key 落业务目录) + `seed_root_files[]` (直落 vault 根)
- `plugins/tools/cortex/lint/schemas.py`:
  - LYT preset `root_files` 加 `home.md`, `topics-moc.md`, `projects-moc.md`
  - 移除 `moc` (若在 root_dirs 内)
- `plugins/tools/cortex/skills/cortex-install/SKILL.md`:
  - 流程示例从 `00_MOC/topics-moc.md` 改为 `topics-moc.md`
  - 落 MOC 文件到 root, 不创 moc/ 目录

### 不在范围

- 不动 `locales/*.yml` `dirs.moc` 映射 (保留兼容,虽不再用)
- 不动 hooks / install.sh / mcp/ / P0-P6 / Phase A
- 不动 `lint/schemas.py` PARA/flat preset (它们自己定义,LYT only 改)

## 详细规范

### 1. _structure.json 结构改

方案 A:`dst_key` 加 sentinel `"."` 表示 vault 根

```json
"seed_files": [
  {"src": "seed/moc/home.md", "dst_key": ".", "name": "home.md", "desc": "MOC 总入口 — vault 顶层导航地图..."},
  {"src": "seed/moc/topics-moc.md", "dst_key": ".", "name": "topics-moc.md", "desc": "主题 MOC..."},
  {"src": "seed/moc/projects-moc.md", "dst_key": ".", "name": "projects-moc.md", "desc": "项目 MOC..."},
  {"src": "seed/_index.md", "dst_key": "concepts", "name": "_index.md", "desc": "..."},
  ...
]
```

`directories_keys` 删 `moc`:

```diff
"directories_keys": [
- "moc",
  "concepts",
  "entities",
  "domains",
  "sources",
  "questions",
  "dashboards",
  "fleeting",
  "archive"
]
```

cortex-install skill 流程理解 `dst_key = "."` 时,直落 vault 根 (不经 locales/<lang>.yml:dirs 映射)。

### 2. lint/schemas.py LYT 调整

```python
"LYT": {
    "root_dirs": {
        "_meta",
        "10_concepts", "20_efforts", "30_domains",
        "40_anchors", "50_calendar", "60_journal",
        "70_attachments", "80_archive", "90_inbox",
        "folds", "log", "sessions",
        ".obsidian", ".trash",
    },
    "root_files": {
        "hot.md", "index.md", "README.md",
        "dashboard.md", "index-map.md",
        "home.md", "topics-moc.md", "projects-moc.md",  # 新加 3 MOC
    },
},
```

注意:LYT 现 root_dirs 已无 `moc/` (因为编号目录 `40_anchors/` 才是 anchors/MOC 容器)。检查:确认 LYT root_dirs 不含 moc-related 目录。

或考虑:LYT 编号 buckets `40_anchors/` 即原 MOC 容器(LYT 方法学 "Anchor Notes" = MOC)。但用户要 root,绕开此约定。

实施:加 3 MOC 到 root_files 即可,不动 root_dirs。

### 3. cortex-install/SKILL.md 流程更新

```diff
- ✅ 复制 00_MOC/topics-moc.md
+ ✅ 复制 topics-moc.md (vault 根)
```

§流程 step 4 写明:`dst_key="."` 的 seed_files 直落 vault 根,不进 locales dirs 映射。

## 验收

1. `_structure.json` directories_keys 不含 moc
2. seed_files 3 个 moc 项 dst_key="."
3. lint/schemas.py LYT root_files 含 home.md / topics-moc.md / projects-moc.md
4. install 新 vault:`ls <vault>/` 见 home.md / topics-moc.md / projects-moc.md 在根, 无 moc/ 子目录
5. lint 现新 vault 不报这 3 文件为 vault-structure-violation
6. bash plugins/tools/cortex/tests/run.sh 不回归

## 不变量

- vault 根含 3 MOC 文件,无 moc/ 子目录
- _structure.json seed_files dst_key="." 表 root (新 sentinel)
- LYT schemas root_files 含 3 MOC
- locales/*.yml dirs.moc 保留 (legacy, 但不再用)
- 老 vault 已有 moc/ 子目录:install 重跑不动 (向后兼容)

## 风险

- **老 vault 已建 moc/ 子目录**:install 重跑创新根 MOC 但老 moc/ 仍在 → lint 报 moc/ 为违规. **缓解**:lint vault-structure-violation 已有白名单机制,用户可加 moc/ 进白名单;或手动 mv
- **dst_key="." sentinel 与现有 install 流程不兼容**:cortex-install/SKILL.md 处理逻辑需明示 "."
- **测试 fixture 假设 moc/ 子目录**:grep test 内 moc 引用,同步改
