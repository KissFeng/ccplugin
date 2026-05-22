# image-understand 多 provider 配置

`<vault>/.cortex/config/image-understand.yaml` 驱动。OpenAI 兼容 chat completions
+ vision messages 格式, 所有 provider 共享同一份代码路径。

## 完整模板

```yaml
# image-understand.yaml — cortex-image-understand / image_understand CLI 配置
# providers: 多 provider 数组, name 全局唯一; 推荐 api_key_env 而非 inline api_key
# probe 自动 ping /models 端点; 4xx 且 trusted=false → 自动 disabled
providers:
  - name: zhipu-glm4v
    endpoint: https://open.bigmodel.cn/api/paas/v4/chat/completions
    model: glm-4v-plus
    api_key_env: ZHIPU_API_KEY
    trusted: true
    disabled: false
    timeout_seconds: 60
    notes: "智谱 BigModel, OpenAI 兼容路径; 中文场景默认"

  - name: zhipu-glm45v
    endpoint: https://open.bigmodel.cn/api/paas/v4/chat/completions
    model: glm-4.5v
    api_key_env: ZHIPU_API_KEY
    trusted: true
    disabled: true
    timeout_seconds: 90
    notes: "智谱 4.5V, 更强推理, 价格略高"

  - name: openai-gpt4o
    endpoint: https://api.openai.com/v1/chat/completions
    model: gpt-4o-mini
    api_key_env: OPENAI_API_KEY
    trusted: false
    disabled: true
    timeout_seconds: 60

  - name: qwen-vl
    endpoint: https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
    model: qwen-vl-plus
    api_key_env: DASHSCOPE_API_KEY
    trusted: false
    disabled: true
    timeout_seconds: 60

defaults:
  random_selection: false        # 默认不随机, 用 default_provider
  default_provider: zhipu-glm4v  # 无 --config 时优先选这个
  max_tokens: 1024               # 模型最大返回 token
  temperature: 0.3               # 低温度, 视觉描述要稳
```

## provider 字段语义

| key | 必填 | 说明 |
|---|---|---|
| `name` | ✓ | kebab-case, 全局唯一 |
| `endpoint` | ✓ | 完整 chat completions URL (含 `/chat/completions`) |
| `model` | ✓ | provider 接受的 model 名 |
| `api_key_env` | xor api_key | 环境变量名, 优先级最高 |
| `api_key` | xor api_key_env | 字面 key, 警告 commit 风险 |
| `trusted` | — | true → probe 4xx 也不剔除 (zhipu /models 可能未实现, 建议 trusted=true) |
| `disabled` | — | true → 不参与 active 池 |
| `timeout_seconds` | — | urllib 超时 (默认 60) |
| `max_tokens` | — | 覆盖 defaults.max_tokens |
| `temperature` | — | 覆盖 defaults.temperature |
| `extra_headers` | — | map, 合并到请求 headers |
| `extra_body` | — | map, 合并到请求 body (例如 zhipu 的 `thinking={"type":"disabled"}`) |
| `notes` | — | 自由备注 |

## 已知坑

- **zhipu**: `/v1/models` 走 `https://open.bigmodel.cn/api/paas/v4/models`, probe 时
  会自动从 endpoint 推导。若返回非 200 但实际 chat 能用, 建议 `trusted: true`。
- **DashScope** (Qwen): 必须用 `compatible-mode/v1` 才是 OpenAI 兼容; 老 endpoint
  `dashscope.aliyuncs.com/api/v1/services/aigc/...` 是 dashscope 私有格式, 不能用。
- **OpenAI gpt-4o**: vision 输入限制 20MB / image; base64 编码后约 15MB 原文件上限。
- **图片 base64 大小**: provider 普遍限制 ~5-20MB; CLI 不做压缩, 用户自己 resize。

## 鉴权

API key 通过环境变量注入 wrapper:

```bash
export ZHIPU_API_KEY=...
export OPENAI_API_KEY=...
export DASHSCOPE_API_KEY=...
```

也可写在 yaml 里 (`api_key: xxx`), 但会触发 commit 风险 warning。
