# PRD — cortex-install 硬编码 LYT preset

## 背景

用户:
> install 现在让用户选择结构, 我希望结构固定, 而不是选择 文件夹和文件的结构

现 cortex-install skill 输入含 `preset ∈ {lyt, zettel, para, blank}` (default lyt),让用户选。用户要**固定 LYT**,不再询问。

## 目标

`cortex-install` 流程移除 preset 询问/选择,硬编码 `preset=lyt`。schemas.py 多 preset 支持保留 (lint 兼容性),仅 install 不暴露选项。

## 范围

### 修改

- `plugins/tools/cortex/skills/cortex-install/SKILL.md` — 删 preset 选项/参数/询问段,硬编码 lyt

### 不在范围

- 不动 `lint/schemas.py` (LYT/PARA/flat schema 保留, lint 仍按 vault config preset 走)
- 不动 `_meta/version.json` schema (preset 字段保留写 "lyt")
- 不动 hooks / install.sh / mcp/ / P0-P6 / Phase A

## 详细规范

### SKILL.md 改动

1. **frontmatter description** — 删 preset 选项列举:

```diff
- description: 初始化 vault — 共享根 + preset (lyt/zettel/para/blank) + lang (zh-CN/en/ja); 询问 cron。仅显式触发 ("init vault" / "安装 cortex")。
+ description: 初始化 vault — 共享根 + 固定 LYT 结构 + lang (zh-CN/en/ja); 询问 cron。仅显式触发 ("init vault" / "安装 cortex")。
```

2. **§触发场景** — 删 "切换 preset" 行:

```diff
- 切换 preset (lyt ↔ para ↔ zettel ↔ blank)
```

3. **§输入** — 删 preset 字段:

```diff
- - `preset` ∈ `{lyt, zettel, para, blank}`, 默认 `lyt`
- - vault 路径来自 ...
+ - vault 路径来自 ...
+ - preset 固定 `lyt` (不可选, 用户期望唯一结构)
```

4. **§流程 step 2 校验 preset** — 改为直接硬编码:

```diff
- 2. **校验 preset** — 不在白名单则报错并退出
+ 2. **设 preset=lyt** — 固定结构, 不询问用户
```

5. **§流程 step 4 写 preset 业务目录** — 表述去 "blank preset" 兜底:

```diff
- - blank preset 的 directories/seed_files 均为空, 跳过即可
+ (移除该行, lyt 总有目录)
```

6. **§异常处理** — 删 preset 名错检测 (不再接受用户输入):

```diff
- - preset 名错: 立即退出并列出 4 个有效值
+ (整行删除)
```

7. **任何 "询问 preset" / "AskUserQuestion preset" 段** — 删

### 不需要改的

- `lint/schemas.py` 保留 LYT/PARA/flat,lint 跑时仍读 `_meta/version.json:.preset` 走对应 schema。**lint 仍向后兼容**老 vault 用 para/zettel/flat。
- install 总写 `preset: lyt`,新 vault 一律 LYT 结构。
- 老 vault 若已是 para/zettel,lint 仍按 vault config 走,但 install 不会再切换。

## 验收

1. cortex-install/SKILL.md 全文 grep "preset" → 仅剩 "preset=lyt"/"固定" 等说明性语句,无 "AskUserQuestion preset" 或选项列举
2. install 流程文档不含 preset 选项询问
3. `_meta/version.json` 总写 `preset: "lyt"`
4. lint 仍能识别老 vault 的 para/zettel/flat (schemas.py 保留)
5. `bash plugins/tools/cortex/tests/run.sh` 不回归

## 不变量

- preset=lyt 硬编码 (install 入口)
- lint schemas.py 多 preset 保留 (向后兼容)
- 无新文件 / 无 mcp 改动

## 风险

- **老用户 vault 已是 para/zettel**:install 重跑写 `preset: "lyt"` 但目录结构仍是 para → schema 不一致 lint 报大量违规. **缓解**:install 文档加说明 "重跑不改既有目录,仅更新 _meta/_templates";或 install 检测既有 vault `_meta/version.json:.preset` 非 lyt 时跳过覆盖 (保留原 preset)
