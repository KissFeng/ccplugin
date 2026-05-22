# video-understand 多 provider 配置

`<vault>/.cortex/config/video-understand.yaml` 驱动。两种 mode 覆盖原生视频与抽帧两种路径。

## 完整模板

```yaml
providers:
  - name: zhipu-glm4v
    endpoint: https://open.bigmodel.cn/api/paas/v4/chat/completions
    model: glm-4v-plus
    api_key_env: ZHIPU_API_KEY
    mode: video_url
    trusted: true
    timeout_seconds: 120
    notes: "智谱 glm-4v-plus, 原生视频 (mp4 ≤ 25MB)"

  - name: openai-gpt4o-frames
    endpoint: https://api.openai.com/v1/chat/completions
    model: gpt-4o-mini
    api_key_env: OPENAI_API_KEY
    mode: frames
    frames_count: 8
    disabled: true
    notes: "gpt-4o 无原生视频, 走 ffmpeg 抽 8 帧"

  - name: qwen-vl-max-video
    endpoint: https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
    model: qwen-vl-max
    api_key_env: DASHSCOPE_API_KEY
    mode: video_url
    disabled: true

defaults:
  random_selection: false
  default_provider: zhipu-glm4v
  max_tokens: 1024
  temperature: 0.3
  mode: video_url
  frames_count: 8
```

## provider 字段语义

| key | 必填 | 说明 |
|---|---|---|
| `name` / `endpoint` / `model` / `api_key_env` / `trusted` / `disabled` / `timeout_seconds` / `extra_headers` / `extra_body` / `max_tokens` / `temperature` | — | 同 image-understand |
| `mode` | — | `video_url`(默认) 或 `frames` |
| `frames_count` | — | frames 模式抽帧数, 默认 8 |
| `frames_fps` | — | (保留) 按 fps 而非总帧数抽, 未启用 |

## 已知坑

- **zhipu**: video_url 支持 mp4 ≤ 25MB; 大于此走 frames 模式 或者切别的 provider
- **openai gpt-4o**: 不支持 video_url; 必须 frames; 8 帧约 4MB base64 上行, 注意 timeout 拉长 120s
- **qwen-vl-max-video**: dashscope `compatible-mode/v1`, 视频 URL 必须 https public 可访问 (data: 大概率超 limit)
- **ffmpeg 缺失**: macOS `brew install ffmpeg`; linux `apt install ffmpeg`; 不存在时 frames 模式 fail-soft 报错

## 鉴权

```bash
export ZHIPU_API_KEY=...
export OPENAI_API_KEY=...
export DASHSCOPE_API_KEY=...
```
