# audio-understand 多 provider 配置

`<vault>/.cortex/config/audio-understand.yaml` 驱动。两种 mode 覆盖纯转录与对话理解。

## 完整模板

```yaml
providers:
  - name: zhipu-glm-asr
    endpoint: https://open.bigmodel.cn/api/paas/v4/audio/transcriptions
    model: glm-asr
    api_key_env: ZHIPU_API_KEY
    mode: asr
    trusted: true
    timeout_seconds: 120
    notes: "智谱 ASR (OpenAI 兼容 multipart)"

  - name: openai-whisper
    endpoint: https://api.openai.com/v1/audio/transcriptions
    model: whisper-1
    api_key_env: OPENAI_API_KEY
    mode: asr
    disabled: true
    notes: "Whisper 多语言, 文件 ≤ 25MB"

  - name: openai-gpt4o-audio
    endpoint: https://api.openai.com/v1/chat/completions
    model: gpt-4o-audio-preview
    api_key_env: OPENAI_API_KEY
    mode: chat
    disabled: true
    notes: "支持音频问答, content 走 input_audio"

  - name: qwen-audio
    endpoint: https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
    model: qwen-audio-turbo
    api_key_env: DASHSCOPE_API_KEY
    mode: chat
    disabled: true

defaults:
  random_selection: false
  default_provider: zhipu-glm-asr
  max_tokens: 1024
  temperature: 0.3
  mode: asr
  language: null     # null = provider 自动检测
```

## provider 字段语义

| key | 必填 | 说明 |
|---|---|---|
| `name` / `endpoint` / `model` / `api_key_env` / `trusted` / `disabled` / `timeout_seconds` / `extra_headers` / `extra_body` / `max_tokens` / `temperature` | — | 同 image-understand |
| `mode` | — | `asr`(默认) 或 `chat` |
| `response_format` | — | asr 模式: `json`(默认) / `text` / `verbose_json` (含 segments) |

## 已知坑

- **whisper**: 单文件 ≤ 25MB; 中文识别比 GLM-ASR 略弱; `language=zh` 提示能稳一些
- **zhipu glm-asr**: endpoint 走 `audio/transcriptions` (非 `chat/completions`); multipart 上传同 OpenAI 协议
- **gpt-4o-audio-preview**: 仅 preview, 价格高; 输入 base64 体积膨胀 33% 注意 token 上限
- **qwen-audio**: dashscope compatible-mode 不一定支持所有音频格式, m4a 偶发失败, 建议先转 wav
- **multipart 大文件**: stdlib urllib 不流式上传, 整 body 进内存 — 文件 > 50MB 建议分片
- **language 参数**: ISO 639-1, 例 `zh` / `en` / `ja`; 不传则 provider 自动检测 (whisper 偶尔识别成英文要警惕)

## 鉴权

```bash
export ZHIPU_API_KEY=...
export OPENAI_API_KEY=...
export DASHSCOPE_API_KEY=...
```
