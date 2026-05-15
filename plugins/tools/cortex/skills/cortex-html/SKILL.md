---
name: cortex-html
description: 生成 HTML 片段 — badge/card/timeline/mermaid/heatmap/disclosure 模板替换 {{VAR}} 占位。Triggers on "render html", "生成 HTML 片段", "render badge", "render card", "render timeline".
disable-model-invocation: false
allowed-tools: Read Write
---

# cortex-html

读 `_templates/html/<template>.{html,md}` 片段, 用传入 data dict 替换 `{{VAR}}` 占位, 输出 HTML 字符串 (stdout) 或写入指定文件。

## 触发场景

- cortex-dashboard 内部拼装看板时调用
- cortex-summarizer 生成 HTML callout 时调用
- 用户显式 "render html badge" / "生成 timeline"

## 关键决策树

```
1. 解析模板路径
   vault 内 _templates/html/<template>.{html,md} → 优先
   plugin templates/html/<template>.{html,md} → fallback
   不存在 → 输出候选列表 + 退 1
2. 读模板顶部 <!-- vars: ... --> 注释取必填 key
3. data 缺 key → 输出 missing + 退 1
4. 替换 {{KEY}} → data[KEY] (HTML escape, _RAW 后缀例外)
5. --out 指定 → Write 文件 (校验 in-vault); 否则 stdout
6. --inline → 折行紧凑输出
```

输出 HTML 必符合 Grok Live Artifacts 风格契约 (首字符 `<div`, 全 inline style, 禁 markdown 符号)。详见 references/render-spec.md。

## AUTO_MODE (wrapper / cron 传 `auto` 后缀触发)

- 纯渲染 skill, 无交互, AUTO_MODE 行为与交互模式一致
- 无候选模板时不询问, 直接 fallback 空模板 + warning (禁中止)
- persistent: error 自决降级 / 重试, 禁询问, 禁中止

## References (按需加载)

| 文件 | 用途 |
|---|---|
| [`references/template-catalog.md`](references/template-catalog.md) | 模板候选清单 + 解析/替换/输出流程 + 错误处理 |
| [`references/render-spec.md`](references/render-spec.md) | Grok Live Artifacts 风格硬约束 + 视觉 token + 输出例 |
