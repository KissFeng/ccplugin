# video 模式决策

## video_url vs frames

```
你的 provider 原生支持视频?
  └─ 是 (zhipu glm-4v-plus / qwen-vl-max-video / gemini)
       └─ 用 video_url, content array 直传
  └─ 否 (openai gpt-4o / claude-3 vision / 任何 image VLM)
       └─ 用 frames, ffmpeg 抽 N 帧 → image_url 数组
```

## frames 抽帧数选择

| 视频时长 | 推荐 frames | 说明 |
|---|---|---|
| < 30s | 4-6 | 帧密度足够 |
| 30s-3min | 8 (默认) | 平衡 token 与覆盖 |
| 3-10min | 12-16 | 增加帧捕捉转场 |
| > 10min | 20+ | 但要警惕 token 上限; 考虑切片处理 |

抽帧策略 = 均匀采样 (interval = duration / count, 取每段中点)。

## ffmpeg 安装

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# 验证
ffmpeg -version
ffprobe -version
```

## 子命令决策

| 用户输入 | 子命令 | 备注 |
|---|---|---|
| 给视频, 无具体问题 | describe | 默认中文总结 prompt |
| 带具体问题 ("视频里有几个人") | ask | question 即 prompt |
| 要抽字段 (章节/演讲人/教程步骤) | extract --schema | 必须有 schema 文件 |
| 要时间轴/字幕 | ask + prompts.md §3 模板 | 字幕在脚本里更稳 |

## 已知坑

- video_url base64 编码后体积膨胀 33%, zhipu mp4 ≤ 25MB 原文件指**编码后**, 实际原文件约 18MB
- frames 模式调用前 `ffprobe` 拿不到时长会报错 — 视频可能损坏
- frames 临时目录 `/tmp/cortex-video-*`, 调用后自动清理
- HTTP URL 模式下 provider 必须能从公网拉到视频, 内网 URL 失败

## 何时不用 video_understand

- 视频 > 10min 且要逐句字幕 → 先用 cortex-audio-understand 抽音轨 ASR, 再用 video_understand 看关键帧
- 视频生成 → 不属本 skill (cortex 无生成视频 skill)
- 实时直播流 → 不支持
