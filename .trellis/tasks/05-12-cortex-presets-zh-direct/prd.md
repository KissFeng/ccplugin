# PRD — presets directories_keys 直接中文 (i18n 解耦)

## 背景

用户:
> directories_keys 直接使用中文, 不考虑 i18n

现 `_structure.json` directories_keys 是英文 key (concepts/entities/...), install 时经 `locales/zh-CN.yml:dirs` 映射为中文目录名 (概念/实体/...)。

用户要直接中文, 跳过映射。

## 目标

`_structure.json` directories_keys 直接列中文目录名,seed_files dst_key 同步中文,seed/ 子目录 rename 为中文,install 不再 locales 映射。

## 范围

### 修改

- `plugins/tools/cortex/presets/_structure.json`:
  - directories_keys[] 英文 → 中文 (概念/实体/领域/来源/问题/仪表盘/临时/归档)
  - seed_files[] dst_key 同步中文
- `plugins/tools/cortex/presets/seed/` 子目录 rename (git mv):
  - concepts/ → 概念/
  - entities/ → 实体/
  - domains/ → 领域/
  - sources/ → 来源/
  - questions/ → 问题/
  - dashboards/ → 仪表盘/
  - fleeting/ → 临时/
  - archive/ → 归档/
- `plugins/tools/cortex/lint/schemas.py`:
  - LYT preset root_dirs 加中文目录 (8 项)
- `plugins/tools/cortex/skills/cortex-install/SKILL.md`:
  - §流程 step 4 删 locales 映射逻辑,directories_keys 直用

### 不在范围

- 不删 `locales/*.yml` (legacy 保留, 其它代码可能依赖)
- 不删 `hooks/_lib/cortex_locale.py` (legacy)
- 不删 `cortex-translator` agent / `cortex-locale` skill
- 不动 hooks 主流程 / mcp/ / install.sh / P0-P6 / Phase A
- 不动 `lint/schemas.py` PARA/flat preset

后续可单独 task 清 i18n 整套。

## 详细规范

### 1. _structure.json

```json
{
  "version": "2.2",
  "description": "cortex vault 骨架 — 8-bucket + MOC。目录名直接中文 (不经 i18n 映射)。",
  "directories_keys": [
    "概念", "实体", "领域", "来源",
    "问题", "仪表盘", "临时", "归档"
  ],
  "seed_files": [
    {"src": "seed/moc/home.md", "dst_key": ".", "name": "home.md", "desc": "..."},
    {"src": "seed/moc/topics-moc.md", "dst_key": ".", "name": "topics-moc.md", "desc": "..."},
    {"src": "seed/moc/projects-moc.md", "dst_key": ".", "name": "projects-moc.md", "desc": "..."},
    {"src": "seed/概念/_index.md", "dst_key": "概念", "name": "_index.md", "desc": "..."},
    {"src": "seed/实体/_index.md", "dst_key": "实体", "name": "_index.md", "desc": "..."},
    {"src": "seed/领域/_index.md", "dst_key": "领域", "name": "_index.md", "desc": "..."},
    {"src": "seed/来源/_index.md", "dst_key": "来源", "name": "_index.md", "desc": "..."},
    {"src": "seed/问题/_index.md", "dst_key": "问题", "name": "_index.md", "desc": "..."},
    {"src": "seed/仪表盘/_index.md", "dst_key": "仪表盘", "name": "_index.md", "desc": "..."},
    {"src": "seed/临时/_index.md", "dst_key": "临时", "name": "_index.md", "desc": "..."},
    {"src": "seed/归档/_index.md", "dst_key": "归档", "name": "_index.md", "desc": "..."}
  ]
}
```

desc 字段保留 (上一 task 已加)。

### 2. seed/ rename

```bash
cd plugins/tools/cortex/presets/
git mv seed/concepts seed/概念
git mv seed/entities seed/实体
git mv seed/domains seed/领域
git mv seed/sources seed/来源
git mv seed/questions seed/问题
git mv seed/dashboards seed/仪表盘
git mv seed/fleeting seed/临时
git mv seed/archive seed/归档
```

### 3. lint/schemas.py LYT 调整

```python
"LYT": {
    "root_dirs": {
        "_meta",
        # 原 10_concepts/20_efforts/... 编号目录 (legacy, 保留)
        "10_concepts", "20_efforts", "30_domains",
        "40_anchors", "50_calendar", "60_journal",
        "70_attachments", "80_archive", "90_inbox",
        # 新中文目录 (直接 directories_keys 落, 不经 locales 映射)
        "概念", "实体", "领域", "来源",
        "问题", "仪表盘", "临时", "归档",
        "folds", "log", "sessions",
        ".obsidian", ".trash",
    },
    "root_files": {
        "hot.md", "index.md", "README.md",
        "dashboard.md", "index-map.md",
        "home.md", "topics-moc.md", "projects-moc.md",
    },
},
```

兼容老 vault (编号目录 + locale 渲染过的) 与新 vault (直接中文)。

### 4. cortex-install/SKILL.md

§流程 step 4 删 "经 locales/<lang>.yml:dirs 映射" 段:

```diff
- 4. **写 preset 业务目录** — 读 _structure.json directories_keys, 经
-    locales/<lang>.yml:dirs 映射为实际目录名 ...
+ 4. **写 LYT 业务目录** — 读 _structure.json directories_keys (现直
+    接中文, 不再 locale 映射), 在 vault 下创对应目录, 并落 seed_files.
+    dst_key="." 的直落 vault 根.
```

### 5. 业务 _index.md 内容兼容

8 个 `seed/<中文dir>/_index.md` 内容不变 (rename 不改内容)。

## 验收

1. `_structure.json` directories_keys 8 项全中文,JSON 合法
2. `ls presets/seed/` 含 `概念/` `实体/` `领域/` `来源/` `问题/` `仪表盘/` `临时/` `归档/` (中文目录) + `moc/`,不含原英文目录
3. `lint/schemas.py` LYT root_dirs 含 8 中文目录 + 原编号目录 (兼容老 vault)
4. `cortex-install/SKILL.md` §流程 step 4 删 locales 映射段
5. install 新 vault 见 `<vault>/概念/_index.md` 等中文目录
6. lint 现新 vault 中文目录不报违规
7. bash plugins/tools/cortex/tests/run.sh 不回归

## 不变量

- _structure.json directories_keys 8 项全中文
- seed/ 8 子目录中文命名
- lint LYT root_dirs 含中文 + 编号 (双兼容)
- locales/*.yml + cortex_locale.py 保留 (legacy)
- 不破坏其它 skill/agent (cortex-translator 等仍可用 i18n module)

## 风险

- **老 vault 已用 locales 渲染**:install 重跑写新中文目录,但老目录 (概念/ 或 10_concepts/) 共存. **缓解**:install 不覆盖已存在目录,老 vault 不动
- **lint root_dirs 同时含 编号 + 中文**:vault-structure-violation 兼容,但若 vault 混杂可能误报较少. **缓解**:用户走 lint_whitelist
- **测试 fixture 用英文 dir**:test_install / test_lint 可能 fixture 引用 "concepts" 等. **缓解**:实施时 grep 改
- **i18n 代码仍存但 _structure 不用**:cortex_locale.py 可能跑空 (dirs map 找不到中文 key). **缓解**:legacy 路径不强制,新 install 不走
