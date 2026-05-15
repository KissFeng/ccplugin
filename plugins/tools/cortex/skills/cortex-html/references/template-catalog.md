# cortex-html — 模板目录 + 渲染流程

> SKILL.md 入口的模板清单 + 解析 / 替换 / 输出流程 + 错误处理。

## 模板候选

- `badge` / `card` / `timeline` (`.html`)
- `mermaid-flowchart` / `mermaid-sankey` / `mermaid-mindmap` (`.md`, mermaid fence)
- `canvas-heatmap` (`.html`)
- `progressive-disclosure` (`.html`)

## 输入

- `template`: 片段名, 必填
- `data`: dict, key 匹配模板 `{{KEY}}` 占位 (必填项由模板顶部注释声明)
- `--out`: 可选, 写入文件路径 (默认 stdout)
- `--inline`: 可选, 输出去 HTML 注释 (节省 token)

## 流程

1. **解析模板路径**:
   - vault 内: `<vault>/_templates/html/<template>.{html,md}` (优先)
   - plugin fallback: `<PLUGIN_ROOT>/templates/html/<template>.{html,md}`
   - 不存在 → 输出可用模板列表 + 退出 1
2. **读模板**:
   - 顶部注释 `<!-- vars: TITLE, LABEL, COLOR -->` 声明必填 key
   - 缺 key → 输出 missing keys + 退出 1
3. **替换占位**:
   - 简单字符串替换 `{{KEY}}` → `data[KEY]`
   - HTML 转义 (除非 key 名以 `_RAW` 结尾, 用于嵌套 HTML/mermaid)
   - 列表/dict 类型 data: 调子模板循环 (`{{#each ITEMS}}...{{/each}}`)
4. **输出**:
   - `--out` 指定 → Write 到文件 (校验路径在 vault 内)
   - 默认 stdout 一行打印
5. **`--inline` 模式**: 折行去缩进, 紧凑输出

## 输出示例

```
[html] template=card  vars filled: 4/4
  <div class="cortex-card" style="...">
    <h3>{{TITLE}}</h3>
    ...
  </div>
```

或写入文件:

```
[html] template=mermaid-sankey  written: 仪表盘/固化流.md (replaced %%mermaid-block%%)
```

## 错误处理

- 模板不存在 → 列候选 + 退 1
- 必填 key 缺失 → 列 missing + 退 1
- 路径越界 (`--out`) → 拒
- HTML escape 失败 (非 str data) → 自动 repr, 加 warning
