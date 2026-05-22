---
name: cortex-audio-understand
description: 音频理解 — ASR 转录 + 音频问答。多 provider (openai whisper / zhipu glm-asr / openai gpt-4o-audio / qwen-audio); 两种模式 asr (Whisper 风格 multipart 转录) 与 chat (OpenAI gpt-4o-audio / 通义 qwen-audio 问答)。从 vault/.cortex/config/audio-understand.yaml 选 provider。Triggers on "转录", "转写", "听音频", "audio transcription", "ASR", "音频问答", "音频理解", "听这段录音", "/cortex:audio-understand".
disable-model-invocation: false
allowed-tools: Bash Read Write
---

# cortex-audio-understand

把音频喂给 ASR / 音频 LLM 拿文本结果。镜像 cortex-image-understand, 双模式适配转录与问答两类需求。

## 调用优先级 (P1)

1. **优先 CLI**: `bash ~/.cortex/scripts/audio_understand.sh <subcommand> ...`
   - `transcribe <audio> [--config NAME] [--language LANG]` — ASR 纯转录
   - `describe <audio> [--config NAME] [--prompt TEXT]` — 概述音频
   - `ask <audio> "<question>" [--config NAME]` — 音频问答
   - `probe [--config NAME] [--all]`
   - `list [--all]`

2. 输入: 本地文件路径 (mp3/wav/m4a/webm/flac/ogg/opus)

3. JSON 输出: `{ok, text, provider, model, mode, usage}`

## 两种模式

| 模式 | 子命令 | provider 例 | 原理 |
|---|---|---|---|
| `asr` | `transcribe` | openai whisper-1, zhipu glm-asr | multipart upload `/v1/audio/transcriptions` |
| `chat` | `describe / ask` | openai gpt-4o-audio-preview, qwen-audio, zhipu glm-4-voice | chat completions + `input_audio` content |

provider yaml 里写 `mode: asr|chat`。`transcribe` 强制 asr, `describe/ask` 强制 chat — 不需要手 override。

## 触发场景

- 录音转文字 (会议 / 访谈 / 语音笔记) → transcribe
- 听完总结 ("讲了啥") → describe
- 带问题听 ("说了几个产品名") → ask

不触发: TTS (本 skill 不合成) / 实时流 / 说话人分离

## 决策树

```
用户给音频文件 + ?
  │
  ├─ "转成文字" / "转录" / "字幕"        → transcribe (asr 模式)
  ├─ 想要内容概述, 无具体问题            → describe (chat 模式)
  ├─ 带具体问题 ("说了什么/几个人/几次")  → ask (chat 模式)
```

## Provider 速查

| name | endpoint | model | mode | 备注 |
|---|---|---|---|---|
| openai-whisper | api.openai.com/v1/audio/transcriptions | whisper-1 | asr | 业界标杆, 多语言强 |
| zhipu-glm-asr | bigmodel.cn/api/paas/v4/audio/transcriptions | glm-asr | asr | 中文场景默认推荐 |
| openai-gpt4o-audio | api.openai.com/v1/chat/completions | gpt-4o-audio-preview | chat | 支持问答 + 推理 |
| qwen-audio | dashscope.aliyuncs.com/compatible-mode/v1/chat/completions | qwen-audio-turbo | chat | 中文 + 多任务 |

完整模板见 [references/providers.md](references/providers.md)。

## 文件格式

支持 mp3 / wav / m4a / webm / flac / ogg / opus。MIME 按后缀自动判定。

- whisper 上限 25MB / 文件; 超出建议先切片 (`ffmpeg -i in.wav -t 600 -ss 0 out.wav`)
- chat 模式走 base64, 上限通常更紧 (~10MB), 注意 timeout

## AUTO_MODE

- 不询问 mode (子命令决定)
- 不询问 provider, 用 `default_provider` 或第一个 active
- transcribe 无 `--language` 时由 provider 自动检测

## 输出格式

```
✓ 音频转录完成
  provider: openai-whisper (whisper-1) mode=asr
  text:
  <transcript>
```

## References

| 文件 | 内容 |
|---|---|
| [references/providers.md](references/providers.md) | 4 provider 配置模板 + asr/chat 模式字段 + language |
| [references/prompts.md](references/prompts.md) | describe / 摘要 / 说话人区分 / 时间戳标注 prompt |
| [references/modes.md](references/modes.md) | asr vs chat 决策 + 子命令路由 + 文件格式坑 |

## 不做

- 不真跑 API 当用户只问 "能不能"
- 不流式 ASR (实时转录需 websocket, 本 skill 走完整文件上传)
- 不 TTS (语音合成不属本 skill)
- 不说话人分离 (diarization)
- 不 git commit
