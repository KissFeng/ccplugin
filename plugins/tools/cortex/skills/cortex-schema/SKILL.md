---
name: cortex-schema
description: 读 _meta/frontmatter-schema.yaml, 解析每目录 frontmatter + tag 规范, 供其他 SKILL/Agent 调用 (read/validate/fill 3 verb)
disable-model-invocation: false
allowed-tools: Bash Read Edit Glob
---

# cortex-schema

按 vault `_meta/frontmatter-schema.yaml` 提供目录-级 frontmatter + tag 规范的查询/校验/补缺。

## 触发场景
- cortex-save / ingest / memory / new 等 SKILL 需按目录填正确 frontmatter
- cortex-curator agent 跑 audit 时校验
- 用户手动校验某文件

## 输入
- verb: `read <vault-rel-path>` | `validate <file>` | `fill <file>`

## 流程

### `read <path>`
1. 读 `<vault>/_meta/frontmatter-schema.yaml` (fallback plugin templates/)
2. 按 path namespaces 嵌套 longest-prefix 匹配
3. 输出对应段 (required/optional/defaults/tags_required/tags_optional)

### `validate <file>`
1. read 该文件 schema
2. parse 文件 frontmatter
3. 列差异:
   - 缺 required 字段 → ❌
   - 缺 tags_required prefix → ❌
   - 多余字段 → ℹ️
4. 输出 JSON {ok, violations: [...]}

### `fill <file>`
1. validate 找差异
2. 用 defaults 补缺 required
3. 加缺 tags_required (placeholder 用通配, 用户后续填)
4. 写回 (备份原文件)

## 输出
- read: 该路径 schema YAML 段
- validate: violations 列表
- fill: 修改文件 + 报告改了什么

## 错误处理
- schema 文件缺 → 报警 + 提示跑 lint --fix (meta-missing 会补)
- 路径不匹配任一 namespace → 跳过 (info, 不报错)

## AUTO_MODE 兼容
全 AUTO. 不调 AskUserQuestion。
