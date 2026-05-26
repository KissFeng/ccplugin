# 配置指南

Notify 插件的配置选项。

## 配置文件

### 文件位置

- 用户级: `~/.KissFeng/ccplugin/notify/config.yaml`
- 项目级: `<project>/.KissFeng/ccplugin/notify/config.yaml`

### 配置示例

```yaml
hooks:
  stop:
    enabled: true
    message: "{{ project_name }} 任务已完成"

  notification:
    permission_prompt:
      enabled: true
      message: "权限请求: {{ message | default('') }}"

  stop_failure:
    enabled: true
    message: "{{ project_name }} API 错误: {{ error | default('unknown') }}"
```

## 配置选项

### 通知选项

| 选项 | 类型 | 描述 |
|------|------|------|
| `enabled` | boolean | 是否启用通知 |
| `message` | string | 通知消息模板（支持 Jinja2 语法） |

### 工具过滤

```yaml
hooks:
  pre_tool_use:
    task:
      enabled: true
    bash:
      enabled: true
```

### 通知类型过滤

```yaml
hooks:
  notification:
    permission_prompt:
      enabled: true
    idle_prompt:
      enabled: true
```

## 跨平台支持

### 系统通知

| 平台 | 实现方式 | 要求 |
|------|---------|------|
| macOS | Swift/AppKit 无焦点浮层 | Xcode CLT (自动编译缓存) |
| Linux | Tkinter 浮层 | python3-tk |
| Windows | Tkinter 浮层 | python3-tk |
