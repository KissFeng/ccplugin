# PowerShell 开发插件

> PowerShell 开发插件提供高质量的脚本开发指导、调试和性能优化支持，覆盖 PowerShell 7.4 LTS 跨平台、Windows PowerShell 5.1 以及 cmd / batch wrapper

## 安装

```bash
# 推荐：一键安装
uvx --from git+https://github.com/lazygophers/ccplugin.git@master install lazygophers/ccplugin powershell@ccplugin-market

# 或：传统方式
claude plugin marketplace add lazygophers/ccplugin
claude plugin install powershell@ccplugin-market
```

## 功能特性

### 核心功能

- **PowerShell 开发专家代理** — 提供专业的 pwsh / Windows PowerShell 脚本开发支持
  - Strict mode (`Set-StrictMode -Version 3.0` + `$ErrorActionPreference = 'Stop'`) 模板
  - Advanced function (`[CmdletBinding()]` + `param()` + 类型 + 校验)
  - Pipeline 感知（`process { }` 块 + `ValueFromPipeline`）
  - Verb-Noun 命名（动词必在 `Get-Verb` 列表）

- **开发规范指导** — 完整的现代 PowerShell 开发规范
  - PowerShell 7.4 LTS 跨平台特性（`??` / `?.` / `ForEach-Object -Parallel` / `$PSStyle`）
  - Windows PowerShell 5.1 兼容（无 7+ 独有语法）
  - 模块发布（.psd1 / .psm1 / PSResourceGet / PSGallery）
  - 错误处理（terminating vs non-terminating / try-catch 类型化）

- **工具链集成** — 业界标准工具
  - Pester 5.x（测试框架）
  - PSScriptAnalyzer（静态分析）
  - PSResourceGet（PowerShellGet v3，模块管理）
  - PowerShell extension for VS Code（IDE / 调试）

- **Windows shell 兼容** — cmd.exe / 批处理（.bat / .cmd）
  - `setlocal EnableDelayedExpansion` / `!var!` vs `%var%`
  - `%~dp0` 等路径修饰符
  - `errorlevel` 检查 / `FOR /F` 循环
  - 何时退回 batch（仅 wrapper / 引导脚本）

### 包含组件

| 组件类型 | 名称 | 描述 |
|---------|------|------|
| Agent | `powershell-dev` | PowerShell 开发专家 |
| Agent | `powershell-debug` | 脚本调试专家 |
| Agent | `powershell-perf` | 性能优化专家 |
| Skill | `powershell-core` | 核心规范：Verb-Noun / advanced function / pipeline |
| Skill | `powershell-modules` | 模块：.psd1 / .psm1 / PSResourceGet / PSGallery |
| Skill | `powershell-error` | 错误处理：try-catch / $ErrorActionPreference / $LASTEXITCODE |
| Skill | `powershell-testing` | 测试：Pester 5 / PSScriptAnalyzer |
| Skill | `powershell-windows-shell` | cmd / batch 兼容子集 |

## 前置工具

```powershell
# 跨平台（推荐）
# Windows: winget install Microsoft.PowerShell
# macOS:   brew install --cask powershell
# Linux:   见 https://learn.microsoft.com/powershell/scripting/install/

# 模块
Install-PSResource Pester              -Scope CurrentUser
Install-PSResource PSScriptAnalyzer    -Scope CurrentUser

# 验证
$PSVersionTable.PSVersion              # ≥ 7.4
Get-Module Pester              -ListAvailable
Get-Module PSScriptAnalyzer    -ListAvailable
```

## 核心规范

### 必须遵守

1. **Strict Mode** — 脚本头部 `Set-StrictMode -Version 3.0` + `$ErrorActionPreference = 'Stop'`
2. **Verb-Noun** — 函数动词在 `Get-Verb`，PascalCase 单数名词
3. **Advanced function** — `[CmdletBinding()]` + `param()` + 类型 + `[Validate*()]`
4. **错误类型化** — try/catch 按异常类型；`throw [ArgumentException]::new(...)`
5. **静态检查** — `Invoke-ScriptAnalyzer -EnableExit` 零警告

### 禁止行为

- `Write-Host` 当数据输出（用 `Write-Output`）
- `Invoke-Expression` 字符串（拆参数 / splat）
- `$arr += $x` 大循环（用 `[List[T]]`）
- 硬编码 `\` 或 `C:\` 路径（用 `Join-Path`）
- 函数动词不在 `Get-Verb` 列表
- 直接 `throw "string"`（用强类型异常）
- batch 写复杂逻辑（提取到 `.ps1`，batch 仅 wrapper）

## 最佳实践

### 脚本模板

```powershell
#!/usr/bin/env pwsh
#Requires -Version 7.4
<#
.SYNOPSIS
    简短描述
.PARAMETER Name
    参数说明
.EXAMPLE
    ./script.ps1 -Name foo
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)]
    [ValidateNotNullOrEmpty()]
    [string]$Name
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true   # 7.3+

function Main {
    [CmdletBinding()]
    param([string]$Name)

    try {
        Write-Verbose "Processing $Name"
        # ... 业务逻辑 ...
    }
    catch [System.IO.IOException] {
        Write-Error "IO error: $($_.Exception.Message)"
        throw
    }
}

Main -Name $Name
```

### 模块发布流程

```powershell
Test-ModuleManifest ./MyModule.psd1
Invoke-ScriptAnalyzer -Path . -Recurse -Settings ./PSScriptAnalyzerSettings.psd1 -EnableExit
Invoke-Pester -CI
Publish-PSResource -Path ./MyModule -ApiKey $env:PSGALLERY_KEY -Repository PSGallery
```

## 参考资源

- [PowerShell Documentation](https://learn.microsoft.com/powershell/scripting/) — 官方文档
- [Approved Verbs](https://learn.microsoft.com/powershell/scripting/developer/cmdlet/approved-verbs-for-windows-powershell-commands) — Verb-Noun 动词表
- [Pester](https://pester.dev/) — 测试框架
- [PSScriptAnalyzer](https://learn.microsoft.com/powershell/utility-modules/psscriptanalyzer/overview) — 静态分析
- [PowerShell Practice & Style](https://poshcode.gitbook.io/powershell-practice-and-style/) — 风格指南
- [SS64 cmd reference](https://ss64.com/nt/) — Windows cmd / batch 参考

## 许可证

AGPL-3.0-or-later
