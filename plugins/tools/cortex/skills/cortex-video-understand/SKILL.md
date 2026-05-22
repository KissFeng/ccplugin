---
name: cortex-video-understand
description: 视频理解 — 多 provider VLM 视频分析。两种模式 video_url (zhipu glm-4v-plus / qwen-vl-max-video 原生视频) 与 frames (ffmpeg 抽帧走 image VLM, 兼容 openai gpt-4o)。从 vault/.cortex/config/video-understand.yaml 选 provider。Triggers on "看视频", "视频理解", "video understanding", "总结视频", "视频问答", "video QA", "/cortex:video-understand".
disable-model-invocation: false
allowed-tools: Bash Read Write
---

# cortex-video-understand

把视频喂给 VLM 拿文本结果。镜像 cortex-image-understand, 双模式适配不同 provider。

## 调用优先级 (P1)

1. **优先 CLI**: `bash ~/.cortex/scripts/video_understand.sh <subcommand> ...`
   - `describe <video> [--config NAME] [--prompt TEXT] [--mode video_url|frames] [--frames N]`
   - `ask <video> "<question>" [--config NAME] [--mode] [--frames N]`
   - `extract <video> --schema <path> [--config NAME] [--mode] [--frames N]`
   - `probe [--config NAME] [--all]`
   - `list [--all]`

2. 输入: 本地路径或 `http(s)://` URL (frames 模式仅本地)

3. JSON 输出: `{ok, text, provider, model, mode, frames_used?, usage}`

## 两种模式

| 模式 | 适用 provider | 原理 | 限制 |
|---|---|---|---|
| `video_url` | zhipu glm-4v-plus, qwen-vl-max-video, gemini | content array `{type:"video_url", video_url:{url:...}}` 直传 | provider 必须原生支持视频 |
| `frames` | openai gpt-4o, 任何 image VLM | ffmpeg 均匀抽 N 帧 → image_url 数组 | 需本地 ffmpeg; 静态帧丢失运动信息 |

provider 在 yaml 里写 `mode: video_url|frames`。`--mode` 临时覆盖。

## 触发场景

- 用户给视频 + 问"讲了啥 / 几个人 / 这段干嘛"
- 笔记需要视频摘要 (会议录屏 / 教程片段)
- 结构化提取 (片头/演讲人/章节切分 → extract + schema)

不触发: 纯文本 / 纯音频 (走 cortex-audio-understand) / 视频生成

## 决策树

```
1. 选模式
   ↓ provider 配 mode=video_url? → 直接走
   ↓ 否则 ffmpeg 在否?
       是 → frames 模式 (默认 8 帧)
       否 → 报错提示装 ffmpeg 或换 video_url provider
   ↓
2. 选 prompt
   describe → 默认中文总结 prompt
   ask     → user question
   extract → schema + 内置抽取 prompt
   ↓
3. 调 video_understand.sh
   ↓
4. 接 JSON 输出文本/结构化结果
```

## Provider 速查

| name | endpoint | model | mode |
|---|---|---|---|
| zhipu-glm4v | bigmodel.cn/api/paas/v4 | glm-4v-plus | video_url |
| openai-gpt4o-frames | api.openai.com/v1 | gpt-4o-mini | frames |
| qwen-vl-max-video | dashscope.aliyuncs.com/compatible-mode/v1 | qwen-vl-max | video_url |

详见 [references/providers.md](references/providers.md)。

## AUTO_MODE

- 不询问 mode / provider
- 默认 `default_provider` 或第一个 active
- frames 模式 ffmpeg 缺失 → 输出 JSON error, 不 fallback (避免静默切 provider 烧钱)

## 输出格式

```
✓ 视频理解完成
  provider: zhipu-glm4v (glm-4v-plus) mode=video_url
  usage:    prompt=4096 completion=512

  <text>
```

frames 模式额外 `frames_used: 8`。

## References

| 文件 | 内容 |
|---|---|
| [references/providers.md](references/providers.md) | provider 配置模板 + mode 字段 + frames 参数 |
| [references/prompts.md](references/prompts.md) | 视频描述 / 章节切分 / 字幕复刻 / 动作识别 prompt |
| [references/modes.md](references/modes.md) | video_url vs frames 决策 + ffmpeg 安装 + 已知坑 |

## 不做

- 不真跑 API 当用户只问 "能不能"
- 不流式输出
- 不剪辑 / 不合成 / 不抽音轨 (音频走 cortex-audio-understand)
- 不缓存帧
- 不 git commit
