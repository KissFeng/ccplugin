---
name: cortex-image-understand
description: 图理解 — 调多 provider VLM (zhipu glm-4v / openai gpt-4o / qwen-vl) 完成图片描述、视觉问答、OCR、结构化抽取。从 vault/.cortex/config/image-understand.yaml 选 provider。Triggers on "看图", "识图", "图理解", "VQA", "vision", "describe image", "看看这张图", "图里写了什么", "提取图中文字", "OCR", "/cortex:understand".
disable-model-invocation: false
allowed-tools: Bash Read Write
---

# cortex-image-understand

把图片喂给 VLM 拿到文本结果。与 `cortex-image` (文生图) 对称, OpenAI 兼容 chat completions vision 格式, 走多 provider 配置驱动。

## 调用优先级 (P1)

1. **优先 CLI**: `bash ~/.cortex/scripts/image_understand.sh <subcommand> ...`
   - `describe <image> [--config NAME] [--prompt TEXT]` — 通用描述
   - `ask <image> "<question>" [--config NAME]` — 视觉问答
   - `extract <image> --schema <path> [--config NAME]` — 按 JSON schema 抽字段
   - `probe [--config NAME] [--all]` — 健康检查
   - `list [--all]` — 列已配 provider

2. `<image>` 输入支持: 本地路径 (自动 base64 编码) 或 `http(s)://` URL

3. 输出 JSON: `{ok, text, provider, model, usage, key_source}` (extract 额外含 `data` + `raw_text`)

## 触发场景

- 用户给图 + 问"这是什么 / 写了啥 / 帮我看看"
- 笔记里有截图需要转文字 (OCR/表格识别)
- 需要按字段抽取 (发票/海报/简历) → `extract` 模式 + schema 文件
- 多张图批量描述 (循环调 describe, 写入 vault sidecar md)

不触发: 纯文本任务 / 文生图 (走 `cortex-image`) / 图像编辑生成 (本 skill 仅读不画)

## 决策树

```
1. 解析输入                  user 给的是路径 / URL / 屏幕截图 / 多张?
   ↓
2. 选模式                    通用描述 → describe
                            带问题   → ask
                            要结构化 → extract (须有 schema 文件)
                            纯 OCR   → ask "把图中所有文字按原始版式输出, 用 markdown"
   ↓
3. 选 provider               用户指定 ? --config : 默认 (default_provider 或第一个 active)
                            详见 references/providers.md
   ↓
4. 调 image_understand.sh
   ↓
5. 接 JSON                   验 ok=true; extract 额外验 data 非空
   ↓
6. 反馈给用户                文字结果直接展示; 结构化结果格式化为 table / yaml
```

## Provider 速查

| name | endpoint | model | 适合 |
|---|---|---|---|
| zhipu-glm4v | bigmodel.cn/api/paas/v4 | glm-4v-plus | 中文场景, 默认推荐 |
| zhipu-glm45v | 同上 | glm-4.5v | 更强推理, 复杂图 |
| openai-gpt4o | api.openai.com/v1 | gpt-4o-mini | 英文 / 通用 |
| qwen-vl | dashscope.aliyuncs.com/compatible-mode/v1 | qwen-vl-plus | 中文 + 长图 |

完整配置模板见 [references/providers.md](references/providers.md)。

## extract 模式 schema 文件

`--schema <path>` 接一个 schema 文件 (非内联字符串), 内容通常是 JSON Schema 或简化 shape:

```json
{
  "title": "string",
  "date": "YYYY-MM-DD",
  "amount": "number",
  "items": [{"name": "string", "qty": "integer"}]
}
```

模型按此结构输出纯 JSON, CLI 后处理剥 ```json 围栏 + `json.loads` 校验。

## AUTO_MODE

- 不询问 provider, 用 `defaults.default_provider` 或第一个 active
- 不预询问 prompt (describe 用默认中文描述 prompt)
- 失败自动 fallback: `probe` → 选下一个 active provider 重跑 1 次

## 输出格式

成功 (describe / ask):
```
✓ 图理解完成
  provider: zhipu-glm4v (glm-4v-plus)
  usage:    prompt=512 completion=180

  <text 直接展示>
```

成功 (extract):
```
✓ 结构化抽取完成 (provider: zhipu-glm4v)

  {
    "title": "...",
    ...
  }
```

失败: 输出 stderr error JSON + 建议 `bash ~/.cortex/scripts/image_understand.sh probe` 排查。

## References

| 文件 | 内容 |
|---|---|
| [references/providers.md](references/providers.md) | 4 provider 配置模板 + endpoint / model / 鉴权 / extra_body 字段 |
| [references/prompts.md](references/prompts.md) | describe / OCR / VQA / 表格识别 / 海报抽取 prompt 模板 |
| [references/modes.md](references/modes.md) | 4 模式 (describe/ask/extract/OCR) 决策表 + 何时用哪个 |

## 不做

- 不真跑 API 当用户只问 "能不能" — 先确认意图
- 不流式输出 (chat completions 一次返回够用)
- 不自动落 sidecar md (用户需要走 cortex-save 显式归档)
- 不 git commit (wrapper trap 自动处理)
- 不处理视频 (zhipu glm-4v plus 不支持视频帧序列, 后续单开)
