# cortex-config — schema

完整 schema, 与 `scripts/validate_config.py` 内嵌定义保持一致。修改任一文件必须双改对方。

## `~/.cortex/config.json`

JSON 对象, 根类型必须为 dict。

| key | type | required | default | range / 约束 | 互斥 | 用途 |
|---|---|---|---|---|---|---|
| `vault` | str | ✓ | — | abs path, exists 时校验通过 | — | cortex 所有 skill 入口 |
| `lang` | str | — | `zh-CN` | `^[a-zA-Z]{2,3}(-[A-Z]{2})?$` ISO 639/3166 | — | cortex-locale, digest, save 文案语言 |
| `settings` | str | — | — | abs path, exists | — | cron 注入 claude --settings |
| `install_path` | str | (install.sh 自动写) | — | abs path, exists | — | wrappers 找 plugin 根 |
| `timeout_default` | int | — | 600 | 60-7200 (秒) | — | cron wrapper 超时 |

未知 key → validate error。

## `<vault>/.cortex/config/digest.yaml`

```yaml
stages:
  consolidate: true
  enrich: true
  verify: true
incremental_max_age_days: 30
domain_aliases: {}
```

| key (dotted) | type | required | default | range | 读取方 |
|---|---|---|---|---|---|
| `stages.consolidate` | bool | — | true | true/false | cortex-digest 阶段 5 |
| `stages.enrich` | bool | — | true | true/false | cortex-digest 阶段 6 |
| `stages.verify` | bool | — | true | true/false | cortex-digest 阶段 7 |
| `incremental_max_age_days` | int | — | 30 | 1-365 | cortex-digest state 失效阈值 |
| `domain_aliases` | map<str,str> | — | `{}` | key 长度 1-64, value 非空 | cortex-digest 阶段 5 域名归一 |

文件不存在 → 所有字段取默认值, validate ok。

## `<vault>/.cortex/config/enrich.yaml`

```yaml
mermaid_whitelist:
  - flowchart
  - timeline
  - mindmap
  - sequenceDiagram
  - classDiagram
skip_paths:
  - .obsidian
  - _meta
  - _templates
  - _assets
  - 归档
  - .cortex
  - .trash
```

| key | type | required | default | range | 读取方 |
|---|---|---|---|---|---|
| `mermaid_whitelist` | list<str> | — | 见上 | 子集 of `{flowchart, sequenceDiagram, classDiagram, stateDiagram, erDiagram, journey, gantt, pie, mindmap, timeline, gitGraph, requirementDiagram, c4Context, quadrantChart, sankey, xychart}` | digest 阶段 6 |
| `skip_paths` | list<str> | — | 见上 | 相对 vault root, 非空 | digest 阶段 6 跳过路径 |

## `<vault>/.cortex/config/tags.yaml`

```yaml
alias_synonyms: {}
tag_naming: kebab-case
```

| key | type | required | default | range | 读取方 |
|---|---|---|---|---|---|
| `alias_synonyms` | map<str,list<str>> | — | `{}` | key 非空, value 列表非空, 元素 str | digest 阶段 6 alias 归一 / lint |
| `tag_naming` | enum<str> | — | `kebab-case` | `kebab-case` \| `snake_case` | lint tag 命名约定 |

## `<vault>/.cortex/config/image-gen.yaml`

```yaml
providers:
  - name: openai-dalle3
    endpoint: https://api.openai.com/v1/images/generations
    api_key_env: OPENAI_API_KEY
    model: dall-e-3
    trusted: false
    disabled: false
    last_check: null
    last_status: null
    notes: ""
    extra_headers: {}
    extra_body: {}
    timeout_seconds: 60
defaults:
  random_selection: true
  output_dir: _assets/images
```

### `providers[]` 字段

| key | type | required | default | range / 约束 | 读取方 |
|---|---|---|---|---|---|
| `name` | str | ✓ | — | kebab-case, 全局唯一 | image_gen probe/list/generate |
| `endpoint` | str | ✓ | — | https:// (http warn; 其他 reject) | image_gen probe (`/models`) / generate POST |
| `model` | str | ✓ | — | 非空 | request body.model |
| `api_key_env` | str | (xor api_key) | — | 环境变量名 | os.environ 读 (优先) |
| `api_key` | str | (xor api_key_env) | — | 字面值, 警告 commit 风险 | inline 兜底 |
| `trusted` | bool | — | false | — | probe: true → 4xx 也不剔除 |
| `disabled` | bool | — | false | — | probe 自动写; active 过滤 |
| `last_check` | str | — | null | UTC ISO | probe 写 |
| `last_status` | int | — | null | HTTP code | probe 写 |
| `notes` | str | — | "" | 自由文本 | 用户备注 |
| `extra_headers` | map<str,str> | — | `{}` | — | request headers 合并 |
| `extra_body` | map | — | `{}` | — | request body 合并 (size/style/seed) |
| `timeout_seconds` | int | — | 60 | 1-300 | urllib timeout |

### `defaults` 字段

| key | type | default | range | 读取方 |
|---|---|---|---|---|
| `random_selection` | bool | true | — | generate 无 --config 时是否随机选 |
| `output_dir` | str | `_assets/images` | 相对 vault 根, 非空 | generate 落盘目录 |

### 校验规则 (validate_config.py `validate_image_gen_yaml`)

1. providers 必须 list
2. 每条必含 name / endpoint / model
3. name 全局唯一 (重复 → error)
4. endpoint scheme: https → ok, http → warn, 其他 → error
5. api_key_env XOR api_key (都缺 → error; 都有 → warn env 生效)
6. inline api_key → warn (commit 风险)
7. trusted / disabled bool 类型
8. timeout_seconds int 1-300
9. extra_headers / extra_body 必须 mapping
10. 未知字段 → warn

## `<vault>/.cortex/config/image-understand.yaml`

```yaml
providers:
  - name: zhipu-glm4v
    endpoint: https://open.bigmodel.cn/api/paas/v4/chat/completions
    api_key_env: ZHIPU_API_KEY
    model: glm-4v-plus
    trusted: true
    disabled: false
    timeout_seconds: 60
    max_tokens: 1024
    temperature: 0.3
    extra_headers: {}
    extra_body: {}
    notes: ""
defaults:
  random_selection: false
  default_provider: zhipu-glm4v
  max_tokens: 1024
  temperature: 0.3
```

### `providers[]` 字段

| key | type | required | default | range / 约束 | 读取方 |
|---|---|---|---|---|---|
| `name` | str | ✓ | — | kebab-case, 全局唯一 | image_understand probe/list/* |
| `endpoint` | str | ✓ | — | https:// (http warn; 其他 reject); 含 `/chat/completions` | chat POST |
| `model` | str | ✓ | — | 非空 | request body.model |
| `api_key_env` | str | (xor api_key) | — | 环境变量名 | os.environ |
| `api_key` | str | (xor api_key_env) | — | 字面值, warn commit 风险 | inline 兜底 |
| `trusted` | bool | — | false | — | probe: true → 4xx 不剔除 |
| `disabled` | bool | — | false | — | probe 自动写; active 过滤 |
| `last_check` | str | — | null | UTC ISO | probe 写 |
| `last_status` | int | — | null | HTTP code | probe 写 |
| `timeout_seconds` | int | — | 60 | 1-300 | urllib timeout |
| `max_tokens` | int | — | (defaults) | 1-32768 | request body.max_tokens |
| `temperature` | float | — | (defaults) | 0.0-2.0 | request body.temperature |
| `extra_headers` | map<str,str> | — | `{}` | — | request headers 合并 |
| `extra_body` | map | — | `{}` | — | request body 合并 (provider 私有字段) |
| `notes` | str | — | "" | 自由文本 | 用户备注 |

### `defaults` 字段

| key | type | default | range | 读取方 |
|---|---|---|---|---|
| `random_selection` | bool | false | — | 无 --config 时是否随机选 |
| `default_provider` | str | null | provider name | 无 --config + random=false 时优先 |
| `max_tokens` | int | 1024 | 1-32768 | provider 未覆盖时生效 |
| `temperature` | float | 0.3 | 0.0-2.0 | provider 未覆盖时生效 |

### 校验规则 (validate_config.py `validate_image_understand_yaml`)

同 image-gen 1-10 条; 额外:
11. max_tokens int 1-32768
12. temperature float 0.0-2.0
13. default_provider 若设置必须存在于 providers[] (warn if missing)

## `<vault>/.cortex/config/video-understand.yaml`

字段同 image-understand, 额外:

| key | type | default | 说明 |
|---|---|---|---|
| `mode` | enum | `video_url` | `video_url` 直传 vs `frames` ffmpeg 抽帧 |
| `frames_count` | int | 8 | frames 模式抽帧数, 1-64 |
| `frames_fps` | float | null | (保留) 按 fps 抽, 未启用 |
| `defaults.mode` / `defaults.frames_count` | — | — | provider 未覆盖时生效 |

### 校验规则 (validate_video_understand_yaml)

同 image-understand 1-13 条; 额外:
14. mode ∈ {video_url, frames}
15. frames_count int 1-64
16. defaults.mode ∈ {video_url, frames}

## `<vault>/.cortex/config/audio-understand.yaml`

字段同 image-understand, 额外:

| key | type | default | 说明 |
|---|---|---|---|
| `mode` | enum | `asr` | `asr` Whisper-style multipart vs `chat` chat completions w/ input_audio |
| `response_format` | str | `json` | asr 时: `json` / `text` / `verbose_json` |
| `defaults.mode` / `defaults.language` | — | — | provider 未覆盖时生效; `language` 是 ISO 639-1 |

### 校验规则 (validate_audio_understand_yaml)

同 image-understand 1-13 条; 额外:
14. mode ∈ {asr, chat}
15. defaults.mode ∈ {asr, chat}

## validate_config.py 输出 JSON

```json
{
  "ok": true,
  "errors": [
    {"file": "digest.yaml", "key": "incremental_max_age_days", "issue": "expected int 1-365, got 'abc'"}
  ],
  "warnings": [
    {"file": "tags.yaml", "key": "tag_naming", "issue": "unknown enum 'PascalCase', falling back to default"}
  ]
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `ok` | bool | true = 无 error (warning 允许) |
| `errors` | list<dict> | 拒写级别问题 |
| `warnings` | list<dict> | 提示级 (会话不阻塞) |

每条 issue: `{file, key, issue}`, file 可为 `~/.cortex/config.json` 或 vault yaml 文件名。

## migration

schema 升级流程 (未来):
- 新增字段: 加 default, 兼容老配置 (不报 error)
- 删字段: 在 validate 中标 warning, 一个版本后转 error
- 改默认值: 老配置显式设旧值即可保留
