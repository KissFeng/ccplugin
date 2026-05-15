# cortex-html — Grok Live Artifacts 风格契约

> SKILL.md 入口的输出 HTML 硬约束 + 视觉 token + 示例。

参考 [Grok Live Artifacts 提示词](https://linux.do/t/topic/2163779)。所有模板 v2 与 cortex-dashboard 注入的 HTML 必符合下述硬约束。

## 硬约束

1. **首字符**: 响应必以 `<div` 开头, 严禁前导文字 / Emoji / 换行
2. **全 inline style**: 严禁 `<style>` 块, 所有样式写在标签 `style="..."` 内
3. **禁裸文本**: 文本必 wrap `<span>` / `<p>` / `<h2>` / `<h3>` / `<div>`
4. **禁 Markdown 符号**: 严禁 `#` / `**` / `- ` 等符号 (mermaid 围栏除外)
5. **单一流**: 整个响应连续 HTML 字符串, 不留空行
6. **公式保留**: `$...$` 或 `$$...$$` 不转 HTML

## 视觉 token

- 主容器: `background:#ffffff; border:1px solid #eef0f2; border-radius:16px; padding:24px; box-shadow:0 10px 15px -3px rgba(0,0,0,0.1); font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; color:#1a202c;`
- 标题: `border-left:4px solid #3182ce; padding-left:12px; font-size:1.5rem; font-weight:700;`
- 卡片: `border:1px solid #edf2f7; border-radius:12px; padding:16px;`
- grid: `display:grid; grid-template-columns:repeat(N,1fr); gap:12px;`
- 主色: 蓝`#3182ce` / 绿`#16a34a` / 红`#dc2626` / 橙`#ea580c` / 黄`#ca8a04` / 灰`#6b7280`
- 字体: sans-serif; 文字色: `#1a202c`; 次要文字: `#4a5568` / `#718096`

## 输出例

```html
<div style="background:#ffffff;border:1px solid #eef0f2;border-radius:16px;padding:24px;box-shadow:0 10px 15px -3px rgba(0,0,0,0.1);font-family:-apple-system,sans-serif;color:#1a202c;">
<h2 style="font-size:1.5rem;font-weight:700;border-left:4px solid #3182ce;padding-left:12px;margin:0 0 16px 0;">{{TITLE}}</h2>
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">
<div style="border:1px solid #edf2f7;border-radius:12px;padding:16px;"><span style="font-weight:600;">{{LABEL}}</span><p style="margin:8px 0 0 0;color:#4a5568;">{{VALUE}}</p></div>
</div>
</div>
```
