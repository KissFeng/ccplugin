# 4 模式决策

| 模式 | 子命令 | 何时用 | prompt 来源 | 输出 |
|---|---|---|---|---|
| 通用描述 | `describe` | 用户给图无具体问题, 只想知道"这是什么" | 默认中文 prompt 或 `--prompt` 覆盖 | text |
| 视觉问答 | `ask` | 用户带具体问题 ("几个人/什么颜色/哪行错") | 用户 question 即 prompt | text |
| 结构化抽取 | `extract` | 需要把图字段塞进系统 (发票/海报/简历/表格) | schema 文件 + 内置抽取 prompt | text + 解析后 `data` JSON |
| OCR | `ask` + OCR prompt | 单纯要文字稿 (截图转 md) | references/prompts.md §2 OCR 模板 | text (markdown) |

## 决策流

```
用户输入是图 + ?
  │
  ├─ 没问题, 只丢图        → describe (默认 prompt)
  ├─ 有自然语言问题       → ask <question>
  ├─ 要"提取/抽字段/转结构" → extract --schema (必须先有 schema 文件)
  └─ 要"文字稿/OCR/复刻"   → ask + OCR prompt 模板
```

## extract 何时不要用

- 用户只想看图里写啥 → describe 或 OCR ask 更省 token
- schema 字段 ≤ 2 个 → 直接 ask 问到的更稳
- 图片非结构化 (例如风景照) → 没意义

## 多图

CLI 当前一次一图。批量场景:
1. shell 循环: `for f in *.png; do bash ~/.cortex/scripts/image_understand.sh describe "$f"; done`
2. 或写小脚本调 CLI 后聚合 JSON

未来若加 multi-image, 走 `--images img1 img2` (尚未实现)。

## 与其他 skill 联动

- `cortex-save`: 用户说 "把这张图理解结果存进笔记" → 拿 describe 结果 → 调 cortex-save 落档
- `cortex-ingest`: 截图入 vault 时, 可先 OCR 拿文字再 ingest
- `cortex-image`: 反向 — 文生图; 与本 skill 不混淆 (本 skill 不画图)
