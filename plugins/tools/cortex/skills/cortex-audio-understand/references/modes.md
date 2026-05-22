# audio 模式决策

## asr vs chat

| 需求 | 模式 | 子命令 | 备注 |
|---|---|---|---|
| 完整逐字转录 | asr | `transcribe` | Whisper / GLM-ASR; 输出 plain text |
| 内容概述 | chat | `describe` | 模型听完总结, 比"先转录后总结"省一步 |
| 带具体问题 | chat | `ask` | "有几个产品名 / 哪段在抱怨" |
| 字幕生成 (含时间戳) | asr (`response_format=verbose_json`) + 后处理 | 走 extra_body 配 |

## 子命令路由

```
用户输入音频 + ?
  │
  ├─ "转文字" / "字幕" / "转录"          → transcribe (asr 模式, 不需要 prompt)
  ├─ 没问题, 只想概述                   → describe (chat 模式, 默认 prompt)
  ├─ 带具体问题                         → ask <question> (chat 模式)
```

子命令决定模式后内部不再读 provider.mode 字段。这意味着即使你给 chat provider 跑 `transcribe`, 也会走 ASR 多部分上传 — 此时调用会失败 (endpoint 不对)。**所以 provider yaml 的 mode 字段是用来告诉系统"这个 provider 默认能干什么"的提示**, 真正路由由子命令拍板。

## 长音频策略

| 时长 | 推荐 |
|---|---|
| < 30s | 任意模式直接传 |
| 30s-5min | asr 推荐 (chat 模式 token 跑光险); describe 也 OK |
| 5-15min | 先 transcribe → 用 cortex-search/llm 总结 |
| > 15min | ffmpeg 切片 10min 一段, 循环 transcribe, 后处理拼接 |

切片命令:
```bash
ffmpeg -i in.wav -f segment -segment_time 600 -c copy out_%03d.wav
```

## 文件格式坑

- whisper 接受 mp3/mp4/mpeg/mpga/m4a/wav/webm/flac/ogg
- gpt-4o-audio chat 模式仅接受 wav / mp3 (其他需先转码)
- m4a 在通义偶尔报错, 转 wav 最稳: `ffmpeg -i in.m4a -ar 16000 -ac 1 out.wav`
- opus 一些 provider 不支持, 推荐统一转 wav

## 何时不用 audio_understand

- 实时直播流 (本 skill 走完整文件)
- 仅要语音合成 (TTS, 暂无对应 skill)
- 音频指纹 / 音乐识别 (需专门服务)
- 视频内的音轨 — 先 `ffmpeg -i in.mp4 -vn -acodec copy out.aac` 抽轨再喂
