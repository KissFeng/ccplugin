# cortex-image-understand 图理解 skill

## Goal

为 `plugins/tools/cortex` 添加图理解 skill, 与现有 `cortex-image` (文生图) 对称。
通过 OpenAI 兼容的 chat completions vision 格式调用 zhipu/openai/通义等多 provider, 完成图片描述、视觉问答、结构化提取。

## What I already know

- 镜像参考: `skills/cortex-image/` + `scripts/cli/image_gen.py` (505 行, 单文件 stdlib only, 多 provider yaml, probe/generate/list 三子命令, JSON 输出)
- Wrapper 通过 `scripts/install_wrappers.sh` 的 `emit_cli <name>` 自动生成, 同时需加入 EXPECTED 白名单
- vault 配置位于 `<vault>/.cortex/config/*.yaml`
- zhipu chat completions: `https://open.bigmodel.cn/api/paas/v4/chat/completions`, 模型 `glm-4v-plus` / `glm-4.5v`, OpenAI 兼容 messages 数组 + `content: [{type:"text"...}, {type:"image_url", image_url:{url:...}}]` 格式
- zhipu 支持 base64 (`data:image/png;base64,...`) 和 URL 两种 image_url
- openai vision: `gpt-4o` / `gpt-4o-mini`, 同 endpoint `/v1/chat/completions`
- 通义: dashscope OpenAI 兼容模式 `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`, 模型 `qwen-vl-plus` / `qwen-vl-max`

## Requirements

1. **新 CLI** `scripts/cli/image_understand.py`
   - 子命令: `probe` / `describe <image>` / `ask <image> <question>` / `extract <image> [--schema <json-or-path>]` / `list`
   - 输入图片支持本地路径 (自动 base64) 与 http(s) URL
   - 多 provider 选择 (--config / 默认随机 active)
   - stdlib only, 与 image_gen.py 风格一致
   - JSON 输出 (含 `ok / text / provider / model / usage`)

2. **新配置** `<vault>/.cortex/config/image-understand.yaml`
   - 由 `cortex-init` 或首次调用时生成模板, 包含 zhipu/openai/通义三个 provider 示例 (默认 disabled 除 zhipu 外, 或全部需用户填 key)
   - 字段对齐 image-gen.yaml: `name / endpoint / model / api_key_env / trusted / disabled / timeout_seconds / extra_headers / extra_body / max_tokens / temperature`

3. **新 skill** `skills/cortex-image-understand/SKILL.md` + `references/{providers,prompts,modes}.md`
   - 与 cortex-image 类似的 Junior Designer / AUTO_MODE / 反 slop 章节, 但聚焦理解侧
   - 模式: describe (通用描述) / VQA (问答) / OCR (文本提取) / structured (按 schema 抽字段)

4. **Wrapper 注册** `scripts/install_wrappers.sh`
   - `emit_cli image_understand`
   - `EXPECTED` 加 `image_understand.sh`
   - 注释 wrapper 数从 24 → 25; CLI 从 12 → 13

5. **Slash command** `commands/understand.md` (可选, 命名暂定; 也可不加, 走 skill 触发)
   - 决定: 暂不加 slash, 走 skill 自然触发 (`/cortex:understand` 占用空间, 用户通常说自然语言)

6. **Cortex init 模板** 同步 — 检查 `scripts/init.sh` 或 init 脚本是否生成 `.cortex/config/*.yaml`, 若是, 加 image-understand.yaml 模板

## Acceptance Criteria

- [ ] `bash ~/.cortex/scripts/image_understand.sh probe` 跑通, 返回 JSON
- [ ] `bash ~/.cortex/scripts/image_understand.sh describe <本地 png>` 调 zhipu 返回非空 text
- [ ] `bash ~/.cortex/scripts/image_understand.sh ask <url> "图里有什么"` 走 URL 模式成功
- [ ] `bash ~/.cortex/scripts/image_understand.sh extract <png> --schema '{"title":"str","date":"str"}'` 返回 JSON 含两字段
- [ ] `bash ~/.cortex/scripts/install_wrappers.sh` 安装后 wrappers 目录出现 `image_understand.sh`
- [ ] skill SKILL.md description 行可被 AI 正确触发 (跑 CLAUDE.md §代码质量检查规范 的 claude --settings 命令验证)
- [ ] `ruff check plugins/tools/cortex/scripts/cli/image_understand.py` 通过

## Definition of Done

- 单元覆盖: cli 内部纯函数 (b64 编码 / image_url 构造 / schema 注入 prompt) 加 pytest 用例
- ruff lint + format 干净
- skill description AI 触发测试通过
- README / AGENT.md 若提及 skill 列表则同步
- 不 git commit (按 CLAUDE.md, 暂存即可)

## Technical Approach

### CLI 设计

```
image_understand.py
  ├── probe       — 与 image_gen 同 (HEAD /v1/models)
  ├── describe    — POST chat/completions, content=[text="详细描述这张图", image_url=...]
  ├── ask         — content=[text=<question>, image_url=...]
  ├── extract     — content=[text="按以下 JSON Schema 提取字段, 仅输出纯 JSON: <schema>", image_url=...]
  │                 后处理 strip ```json 围栏 + 校验 json.loads
  └── list        — 与 image_gen 同
```

### 图片输入处理

```python
def _to_image_url(src: str) -> str:
    if src.startswith(("http://", "https://")):
        return src
    p = Path(src).expanduser().resolve()
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "webp": "image/webp", "gif": "image/gif"}.get(p.suffix.lstrip(".").lower(), "image/png")
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"
```

### Provider yaml 模板 (zhipu 优先)

```yaml
defaults:
  random_selection: false
  default_provider: zhipu-glm4v
  max_tokens: 1024
  temperature: 0.3

providers:
  - name: zhipu-glm4v
    endpoint: https://open.bigmodel.cn/api/paas/v4/chat/completions
    model: glm-4v-plus
    api_key_env: ZHIPU_API_KEY
    trusted: true
    timeout_seconds: 60

  - name: zhipu-glm45v
    endpoint: https://open.bigmodel.cn/api/paas/v4/chat/completions
    model: glm-4.5v
    api_key_env: ZHIPU_API_KEY
    disabled: true

  - name: openai-gpt4o
    endpoint: https://api.openai.com/v1/chat/completions
    model: gpt-4o-mini
    api_key_env: OPENAI_API_KEY
    disabled: true

  - name: qwen-vl
    endpoint: https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
    model: qwen-vl-plus
    api_key_env: DASHSCOPE_API_KEY
    disabled: true
```

## Decision (ADR-lite)

- **Context**: 需要在 cortex 体系内新增图理解能力, 与文生图对称
- **Decision**:
  1. 抽 `cli/_provider_common.py` 共享模块, image_gen + image_understand 复用; image_gen.py 同步重构
  2. zhipu 走 OpenAI 兼容 chat completions 路径 (zhipu API v4 已兼容), 不另起 zhipu 专用客户端
  3. 不加 slash command, 走 skill 自然触发减少命名空间噪音
  4. 提取模式不引入 jsonschema 依赖, 仅 prompt 注入 + json.loads 校验
  5. `--schema` 仅接文件路径 (不接内联 JSON 字符串), 强制 schema 用文件管理
- **Consequences**:
  - + 维护简单, 多 provider 自动支持
  - + 用户切 provider 零代码改动
  - - 对 provider 非 OpenAI 兼容字段 (如 zhipu thinking) 不暴露, 后续如需可加 extra_body

## Out of Scope

- 视频理解 (zhipu glm-4v 不支持视频, 后续单开)
- 流式输出 (chat completions stream — describe 场景一次返回够用)
- 函数调用 / tool use (本 skill 仅 text-out)
- 图片预处理 (resize / 压缩) — 由用户自己控制
- 与 vault 笔记的自动 sidecar 落档 (cortex-save 已有, 用户按需手动调)

## Technical Notes

- 参考: `plugins/tools/cortex/scripts/cli/image_gen.py:505` (整体骨架)
- 参考: `plugins/tools/cortex/skills/cortex-image/SKILL.md` (skill 模板)
- 参考: `plugins/tools/cortex/scripts/install_wrappers.sh:300-374` (wrapper 注册)
- zhipu 文档: https://docs.bigmodel.cn/api-reference/模型-api/对话补全
- 复用 image_gen.py 的 `_load_yaml / _resolve_vault / _resolve_api_key / _http_request / _active_providers / _find_by_name / _select_provider` 等 helper — 考虑抽到 `cli/_provider_common.py` 共享模块, 减少复制
