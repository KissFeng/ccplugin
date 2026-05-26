# 版本号管理插件

> 一个完整的 Semantic Versioning (SemVer) 版本管理解决方案，为 Claude Code 项目提供自动和手动版本号管理功能。

## 安装

```bash
# 推荐：一键安装
uvx --from git+https://github.com/KissFeng/ccplugin.git@master install KissFeng/ccplugin version@ccplugin-market

# 或：传统方式
claude plugin marketplace add KissFeng/ccplugin
claude plugin install version@ccplugin-market
```

## 功能特性

- ✨ **完整的 SemVer 支持** - 支持 Major.Minor.Patch.Build 四部分版本号
- 🤖 **自动版本更新** - 通过 Claude Code Hooks 自动检测任务完成并更新版本
- 🎯 **灵活的版本控制** - 支持手动 bump 和自动更新两种模式
- 📝 **Git 集成** - 智能检测 .version 文件的 Git 提交状态
- 🔧 **CLI 工具** - 支持本地脚本运行

## 快速开始

### 基本用法

```bash
# 显示当前版本
/version show

# 显示版本详情（包括 Git 状态）
/version info

# 自动更新版本
/version bump build     # 构建版本 +1
/version bump patch     # 补丁版本 +1
/version bump minor     # 次版本 +1
/version bump major     # 主版本 +1

# 手动设置版本
/version set 1.0.0.0
```

## 版本号含义

采用 Semantic Versioning 标准，格式为 `X.Y.Z.W`：

| 部分 | 名称 | 何时增加 |
|------|------|----------|
| **X** | Major | 不兼容的 API 变更或重大功能 |
| **Y** | Minor | 向后兼容的新功能 |
| **Z** | Patch | bug 修复和性能优化 |
| **W** | Build | 完成任务和小改进 |

## 命令详解

### /version show

显示项目当前版本号。

### /version info

显示版本详细信息，包括各部分数值和 Git 提交状态。

### /version bump \<level\>

根据指定级别自动更新版本号，高级别重置时自动清零低级别。

```bash
/version bump build    # 1.2.3.4 → 1.2.3.5
/version bump patch    # 1.2.3.5 → 1.2.4.0
/version bump minor    # 1.2.4.0 → 1.3.0.0
/version bump major    # 1.3.0.0 → 2.0.0.0
```

### /version set \<version\>

手动设置版本号到指定值。

```bash
/version set 1.0.0.0
/version set 2.0       # 自动补全为 2.0.0.0
```

## 最佳实践

### 何时更新各级版本

**Major 版本**：不兼容的 API 修改、架构重构

**Minor 版本**：新增功能模块、向后兼容的功能增强

**Patch 版本**：Bug 修复、性能优化、安全补丁

**Build 版本**：完成单个任务、代码小改进

## 许可证

AGPL-3.0-or-later
