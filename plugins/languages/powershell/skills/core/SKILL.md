---
name: powershell-core
description: |
  PowerShell core conventions covering PowerShell 7.4 LTS (cross-platform pwsh) vs
  Windows PowerShell 5.1 (built-in legacy), Verb-Noun cmdlet naming with approved
  verbs, advanced functions ([CmdletBinding()] / param blocks / SupportsShouldProcess),
  pipeline semantics (ValueFromPipeline, process/begin/end blocks), strict mode
  (Set-StrictMode -Version 3.0), $ErrorActionPreference, $PSStyle ANSI formatting,
  ForEach-Object -Parallel, ConvertFrom-Json -AsHashtable. Use proactively when the
  user asks to "写 PowerShell 脚本 / pwsh 脚本 / Windows 自动化 / cmdlet 开发". Also
  triggers on "powershell", "pwsh", "ps1", "cmdlet", "advanced function",
  "Verb-Noun", "$PSStyle", "Set-StrictMode", "powershell 规范".
---

# PowerShell 核心规范

PowerShell 是面向对象的 shell + 脚本语言。本文是其它 powershell skill 的基线。

## 版本矩阵

| 版本 | 平台 | 状态 | 用途 |
|------|------|------|------|
| **PowerShell 7.4 LTS** (pwsh) | Windows / Linux / macOS | 2026 主流 | 新项目默认 |
| **PowerShell 7.5** | 跨平台 | Current channel | 尝鲜 |
| **Windows PowerShell 5.1** | Windows 内置 | 维护，不演进 | 兼容旧脚本 / 无 pwsh 环境 |
| PowerShell 6.x | 跨平台 | EOL | 升 7.x |

**默认策略**：新代码目标 7.4 LTS；维护脚本若必须 5.1，文件头注明并避开 7+ 独有特性（`??` / `?.` / 三元 / `ForEach-Object -Parallel`）。

## 与其它 skill 的关系

| 主题 | 跳转 |
|------|------|
| 模块 / PSGallery / manifest | `powershell-modules` |
| 错误处理 / try-catch / `$ErrorActionPreference` | `powershell-error` |
| Pester 测试 / PSScriptAnalyzer | `powershell-testing` |
| cmd.exe / 批处理兼容 | `powershell-windows-shell` |

## 强制约定

1. **文件头模板**：shebang（跨平台）→ `#Requires` → `Set-StrictMode -Version 3.0` → `$ErrorActionPreference = 'Stop'`。
2. **Verb-Noun 命名**：函数名严格 `Get-Foo` / `Set-Foo` / `Test-Foo`，动词必须在 `Get-Verb` 输出列表内。
3. **PascalCase**：函数、参数、cmdlet、类全部 PascalCase；变量 `$camelCase`。
4. **Advanced function**：所有可重用函数加 `[CmdletBinding()]` + `param()` 块。
5. **类型注解**：参数 `[string]$Name`、`[int]$Count`、`[ValidateSet(...)]` 等属性。
6. **管道支持**：可流式处理的函数实现 `process { }` 块 + `ValueFromPipeline`。
7. **`Write-*` 分级**：`Write-Verbose` / `Write-Warning` / `Write-Error` / `Write-Information`；禁 `Write-Host` 当数据输出。
8. **`Set-StrictMode -Version 3.0`**：拒绝未声明变量、未定义属性、数组越界。
9. **PSScriptAnalyzer 零警告**：CI 必跑 `Invoke-ScriptAnalyzer`。
10. **跨平台路径**：用 `Join-Path` / `[IO.Path]::Combine`，禁硬编码 `\`。

## 脚本头模板

```powershell
#!/usr/bin/env pwsh
#Requires -Version 7.4
<#
.SYNOPSIS
    一句话描述
.DESCRIPTION
    详细描述
.PARAMETER Name
    参数说明
.EXAMPLE
    ./script.ps1 -Name foo
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateNotNullOrEmpty()]
    [string]$Name,

    [ValidateRange(1, 100)]
    [int]$Count = 10
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true   # 7.3+: 原生命令非零退出码也 throw
```

## Advanced function

```powershell
function Get-LargeFile {
    [CmdletBinding()]
    [OutputType([System.IO.FileInfo])]
    param(
        [Parameter(Mandatory, ValueFromPipeline, ValueFromPipelineByPropertyName)]
        [Alias('FullName', 'PSPath')]
        [string[]]$Path,

        [ValidateRange(1, [long]::MaxValue)]
        [long]$MinBytes = 1MB
    )

    begin {
        Write-Verbose "Scanning for files >= $MinBytes bytes"
        $count = 0
    }

    process {
        foreach ($p in $Path) {
            Get-ChildItem -LiteralPath $p -File -Recurse -ErrorAction SilentlyContinue |
                Where-Object Length -ge $MinBytes |
                ForEach-Object {
                    $count++
                    $_
                }
        }
    }

    end {
        Write-Verbose "Total: $count files"
    }
}
```

## Pipeline 语义

| 块 | 作用 | 调用次数 |
|----|------|---------|
| `begin` | 初始化 | 1 |
| `process` | 处理每个管道项 | N |
| `end` | 收尾 | 1 |
| `clean` (7.3+) | 类 finally，即使中断也跑 | 1 |

```powershell
1..5 | ForEach-Object { $_ * 2 }                # 内联
1..1000 | ForEach-Object -Parallel { $_ * 2 } -ThrottleLimit 8   # 7.0+ 并行
```

## SupportsShouldProcess（-WhatIf / -Confirm）

```powershell
function Remove-OldLog {
    [CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
    param([string]$Path)

    if ($PSCmdlet.ShouldProcess($Path, 'Remove')) {
        Remove-Item -LiteralPath $Path -Force
    }
}

Remove-OldLog -Path /tmp/old.log -WhatIf       # 仅打印不执行
Remove-OldLog -Path /tmp/old.log -Confirm      # 询问确认
```

## `$PSStyle`（7.2+ ANSI 颜色与渲染）

```powershell
$PSStyle.OutputRendering = 'Host'        # 仅 host，重定向时去 ANSI
$PSStyle.Formatting.Error = $PSStyle.Foreground.Red + $PSStyle.Bold
Write-Host "$($PSStyle.Foreground.Cyan)done$($PSStyle.Reset)"
```

## 字符串与参数展开

```powershell
$name = 'world'
"Hello, $name"                    # 插值
'Hello, $name'                    # 字面
"Hello, $($obj.Property)"         # 子表达式
@"
multi-line
$name
"@                                # here-string 双引号（插值）

# 拼接尽量用插值或 -f 操作符，不要 +
'Result: {0} / {1}' -f $a, $b
```

## 比较与逻辑

| 操作符 | 含义 |
|--------|------|
| `-eq` / `-ne` | 等 / 不等 |
| `-lt` / `-le` / `-gt` / `-ge` | 数值比较 |
| `-like` / `-notlike` | 通配符 `*` `?` |
| `-match` / `-notmatch` | 正则；填充 `$Matches` |
| `-contains` / `-in` | 集合成员 |
| `-is` / `-as` | 类型测试 / 转换 |
| `??` / `??=` (7.0+) | null 合并 |
| `?.` / `?[]` (7.0+) | null 条件访问 |

> 默认大小写不敏感；用 `-ceq` / `-cmatch` 等 `-c` 前缀强制敏感。

## 集合与 JSON

```powershell
# JSON ↔ 对象
$obj = Get-Content config.json | ConvertFrom-Json -AsHashtable -Depth 32
$obj | ConvertTo-Json -Depth 32 -Compress | Set-Content out.json

# 高效集合
$list = [System.Collections.Generic.List[string]]::new()
$list.Add('a')

# 数组追加性能差（每次新建），用 List 或 ArrayList
```

## 常见反模式

| 反模式 | 修正 |
|--------|------|
| `Write-Host` 当数据输出 | `Write-Output` / 直接 `$obj` |
| `function foo { ... }` 无 `[CmdletBinding()]` | 加 advanced function 框架 |
| `+=` 数组拼接大循环 | `[List[T]]::new()` + `.Add()` |
| `Invoke-Expression` 字符串 | 拆参数 + splat |
| 硬编码 `\` 路径 | `Join-Path` |
| 大写动词不在 `Get-Verb` | 用近义已批准动词 |
| 直接 throw 字符串 | `throw [ArgumentException]::new('msg')` |
| 没有 `Set-StrictMode` | 文件头加上 |

## 检查清单

- [ ] `#Requires -Version` 声明
- [ ] `Set-StrictMode -Version 3.0` + `$ErrorActionPreference = 'Stop'`
- [ ] 函数 Verb-Noun，动词在 `Get-Verb` 列表
- [ ] 所有 public 函数 `[CmdletBinding()]` + `param()` + 类型 + 校验
- [ ] 注释帮助（`.SYNOPSIS` / `.PARAMETER` / `.EXAMPLE`）齐全
- [ ] 跨平台脚本无硬编码 `\` 或 `C:\`
- [ ] `Invoke-ScriptAnalyzer` 零警告
- [ ] 测试覆盖（见 powershell-testing）

## 权威参考

- PowerShell Docs — <https://learn.microsoft.com/powershell/scripting/>
- Approved Verbs — <https://learn.microsoft.com/powershell/scripting/developer/cmdlet/approved-verbs-for-windows-powershell-commands>
- PowerShell Practice & Style — <https://poshcode.gitbook.io/powershell-practice-and-style/>
- `$PSStyle` 文档 — <https://learn.microsoft.com/powershell/module/microsoft.powershell.core/about/about_ansi_terminals>
- PowerShell 7.4 What's New — <https://learn.microsoft.com/powershell/scripting/whats-new/what-s-new-in-powershell-74>
