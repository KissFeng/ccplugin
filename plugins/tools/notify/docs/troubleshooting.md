# 故障排除

Notify 插件的常见问题和解决方案。

## macOS 问题

### 未显示通知

**问题**：通知不显示

**解决方案**：

1. 检查系统通知设置中 Claude Code 的通知权限
2. 安装 terminal-notifier：

```bash
brew install terminal-notifier
```

3. 检查勿扰模式是否开启

## Linux 问题

### 未显示通知

**问题**：通知不显示

**解决方案**：

1. 安装 libnotify：

```bash
# Ubuntu/Debian
sudo apt-get install libnotify-bin

# Fedora
sudo dnf install libnotify
```

2. 测试通知：

```bash
notify-send "Test" "Hello, World!"
```

## Windows 问题

### 未显示通知

**问题**：通知不显示

**解决方案**：

1. 确保 PowerShell 版本 3.0 或更高
2. 检查 Windows 通知设置

## 通用问题

### 配置不生效

**问题**：配置修改后不生效

**解决方案**：

1. 检查配置文件路径
2. 检查 YAML 格式
3. 重启 Claude Code

### 通知延迟

**问题**：通知显示延迟

**解决方案**：

1. 检查系统负载
2. 减少通知频率
