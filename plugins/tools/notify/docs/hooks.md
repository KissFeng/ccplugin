# Hook 事件

Notify 插件支持的 Hook 事件。

## 事件列表

| 事件 | 触发时机 | 通知类型 |
|------|----------|----------|
| `SessionStart` | 会话开始 | 初始化通知 |
| `SessionEnd` | 会话结束 | 结束通知 |
| `UserPromptSubmit` | 用户提交提示 | 提交通知 |
| `PreToolUse` | 工具使用前 | 工具通知 |
| `PostToolUse` | 工具使用后 | 完成通知 |
| `Notification` | 系统通知事件 | 权限/空闲通知 |
| `Stop` | 会话或子代理停止 | 统计通知 |

## 事件详情

### SessionStart

会话开始时触发，初始化配置。

```yaml
hooks:
  session_start:
    startup:
      enabled: true
```

### SessionEnd

会话结束时触发，发送结束通知。

```yaml
hooks:
  session_end:
    other:
      enabled: true
```

### UserPromptSubmit

用户提交提示时触发。

```yaml
hooks:
  user_prompt_submit:
    enabled: true
```

### PreToolUse

工具使用前触发，支持按工具过滤。

```yaml
hooks:
  pre_tool_use:
    task:
      enabled: true
    bash:
      enabled: true
```

### PostToolUse

工具使用后触发。

```yaml
hooks:
  post_tool_use:
    task:
      enabled: true
```

### Notification

系统通知事件，包括权限请求和空闲提示。

```yaml
hooks:
  notification:
    permission_prompt:
      enabled: true
    idle_prompt:
      enabled: true
```

### Stop

会话或子代理停止时触发，显示统计信息。

**类型判断**：
- 如果存在 `agent_transcript_path` 字段：子代理 stop
- 如果不存在 `agent_transcript_path` 字段：主 agent stop

```yaml
hooks:
  stop:
    enabled: true
```
