---
name: powershell-testing
description: |
  PowerShell testing with Pester 5.x (Describe/Context/It, BeforeAll/AfterAll/BeforeEach,
  Should -Be / -Throw / -Match / -BeOfType, Mock with parameter filter, InModuleScope,
  TestDrive/TestRegistry, tags & filters, code coverage, NUnit XML output) and static
  analysis with PSScriptAnalyzer (custom rules, Invoke-ScriptAnalyzer -EnableExit,
  Settings.psd1). Covers CI integration (-CI flag), test discovery layout, fixtures,
  and migration notes from Pester 4 to 5. Use proactively when the user asks "写
  PowerShell 测试 / pester 用例 / mock cmdlet / 静态分析 / PSScriptAnalyzer". Also
  triggers on "Pester", "Should", "Mock", "InModuleScope", "TestDrive",
  "Invoke-ScriptAnalyzer", "PSSA".
---

# PowerShell 测试规范

## 工具

| 工具 | 角色 | 安装 |
|------|------|------|
| **Pester 5.x** | BDD 测试框架 | `Install-PSResource Pester` |
| **PSScriptAnalyzer** | 静态分析 | `Install-PSResource PSScriptAnalyzer` |

Pester 5 是 2026 主流，与 Pester 4 不向后兼容（行为差异详见迁移指南）。

## Pester 5 文件骨架

`Tests/MyModule.Tests.ps1`：

```powershell
#Requires -Modules @{ ModuleName = 'Pester'; ModuleVersion = '5.5.0' }

BeforeAll {
    $modulePath = Join-Path $PSScriptRoot '..' 'MyModule.psd1'
    Import-Module $modulePath -Force
}

AfterAll {
    Remove-Module MyModule -ErrorAction SilentlyContinue
}

Describe 'Get-Foo' -Tag 'Unit' {

    Context 'when input is valid' {
        BeforeEach {
            $script:fixture = @{ Name = 'alpha' }
        }

        It 'returns the expected object' {
            $result = Get-Foo -Name $fixture.Name
            $result | Should -Not -BeNullOrEmpty
            $result.Name | Should -Be 'alpha'
        }

        It 'has correct type' {
            Get-Foo -Name $fixture.Name | Should -BeOfType [pscustomobject]
        }
    }

    Context 'when input is invalid' {
        It 'throws ArgumentException' {
            { Get-Foo -Name '' } | Should -Throw -ExceptionType ([System.ArgumentException])
        }
    }
}
```

## Should 断言常用

| 断言 | 含义 |
|------|------|
| `Should -Be 5` | 严格相等 |
| `Should -BeExactly 'Foo'` | 区分大小写 |
| `Should -Not -BeNullOrEmpty` | 非空 |
| `Should -BeOfType [int]` | 类型 |
| `Should -Match 'pattern'` | 正则 |
| `Should -Contain 'item'` | 集合包含 |
| `Should -HaveCount 3` | 集合长度 |
| `Should -Throw` | 抛异常 |
| `Should -Throw -ExceptionType ([IOException])` | 抛指定类型 |
| `Should -Invoke -CommandName X -Times 1` | mock 调用次数 |
| `Should -InvokeVerifiable` | 全部 verifiable mock 都被调 |

## Mock

```powershell
Describe 'Send-Notification' {
    BeforeAll {
        Mock -CommandName Invoke-RestMethod -ModuleName MyModule -MockWith {
            return @{ ok = $true }
        }
    }

    It 'calls REST endpoint once' {
        Send-Notification -Message 'hi'
        Should -Invoke Invoke-RestMethod -Times 1 -Exactly -ModuleName MyModule
    }

    It 'mocks with parameter filter' {
        Mock Invoke-RestMethod -ParameterFilter { $Uri -like '*api/v1/*' } -MockWith {
            return @{ filtered = $true }
        }
        # ...
    }
}
```

**关键点**：

- mock 模块内函数必须 `-ModuleName`，否则 mock 不生效。
- `-ParameterFilter` 用脚本块匹配特定参数组合。
- `-Verifiable` 标记后用 `Should -InvokeVerifiable` 一次性验证。

## InModuleScope（测试 Private 函数）

```powershell
InModuleScope MyModule {
    Describe 'Internal helpers' {
        It 'normalizes path' {
            Get-NormalizedPath '/tmp//foo/' | Should -Be '/tmp/foo'
        }
    }
}
```

## TestDrive / TestRegistry

```powershell
It 'writes to disk' {
    $path = Join-Path $TestDrive 'out.txt'
    Set-Content -Path $path -Value 'hi'
    Get-Content $path | Should -Be 'hi'
    # 测试结束自动清理 TestDrive
}
```

`TestRegistry` 同理但作用 Windows 注册表。

## 标签与过滤

```powershell
Describe 'integration' -Tag 'Integration', 'Slow' { ... }

# 跑特定标签
Invoke-Pester -Tag Unit
Invoke-Pester -ExcludeTag Slow
```

## 配置文件（Pester 5）

```powershell
$config = New-PesterConfiguration
$config.Run.Path = './Tests'
$config.Run.Exit = $true                    # 失败时进程非零退出
$config.Output.Verbosity = 'Detailed'
$config.TestResult.Enabled = $true
$config.TestResult.OutputFormat = 'NUnitXml'
$config.TestResult.OutputPath  = 'testResults.xml'
$config.CodeCoverage.Enabled = $true
$config.CodeCoverage.Path = './Public', './Private'
$config.CodeCoverage.OutputFormat = 'JaCoCo'
$config.CodeCoverage.OutputPath = 'coverage.xml'

Invoke-Pester -Configuration $config
```

CI 一行：

```powershell
Invoke-Pester -CI         # 等价启用 Exit / NUnitXml / 覆盖率
```

## PSScriptAnalyzer

### `PSScriptAnalyzerSettings.psd1`

```powershell
@{
    Severity     = @('Error', 'Warning')
    IncludeRules = @('PS*')
    ExcludeRules = @(
        'PSUseShouldProcessForStateChangingFunctions'   # 视项目放宽
    )
    Rules = @{
        PSAvoidUsingCmdletAliases = @{ Whitelist = @('cd', 'ls') }
        PSPlaceOpenBrace = @{
            Enable             = $true
            OnSameLine         = $true
            NewLineAfter       = $true
            IgnoreOneLineBlock = $true
        }
        PSPlaceCloseBrace = @{
            Enable             = $true
            NewLineAfter       = $true
            IgnoreOneLineBlock = $true
            NoEmptyLineBefore  = $false
        }
        PSUseConsistentIndentation = @{
            Enable          = $true
            IndentationSize = 4
            Kind            = 'space'
        }
    }
}
```

### 调用

```powershell
Invoke-ScriptAnalyzer -Path . -Recurse `
    -Settings ./PSScriptAnalyzerSettings.psd1 `
    -Severity Warning `
    -EnableExit                  # CI：发现告警即非零退出
```

### 常见规则

| 规则 | 含义 |
|------|------|
| PSAvoidUsingWriteHost | 数据走 Write-Output |
| PSUseShouldProcessForStateChangingFunctions | 修改状态需 -WhatIf 支持 |
| PSUseApprovedVerbs | 函数动词在 Get-Verb 列表 |
| PSAvoidUsingPositionalParameters | 显式参数名 |
| PSAvoidUsingPlainTextForPassword | 用 SecureString |
| PSUseDeclaredVarsMoreThanAssignments | 死代码 |
| PSAvoidGlobalVars | 不污染 $global: |

## 目录布局

```
MyModule/
├── Public/Get-Foo.ps1
├── Private/Get-Internal.ps1
├── Tests/
│   ├── MyModule.Tests.ps1
│   ├── Get-Foo.Tests.ps1
│   └── Helpers/
│       └── TestHelpers.psm1
└── PSScriptAnalyzerSettings.psd1
```

约定：每个 Public 函数对应一个 `*.Tests.ps1`，或汇总到 `MyModule.Tests.ps1`。

## CI 模板（GitHub Actions）

```yaml
- name: Lint
  shell: pwsh
  run: |
    Install-PSResource PSScriptAnalyzer -TrustRepository
    Invoke-ScriptAnalyzer -Path . -Recurse -Settings ./PSScriptAnalyzerSettings.psd1 -EnableExit

- name: Test
  shell: pwsh
  run: |
    Install-PSResource Pester -TrustRepository
    Invoke-Pester -CI

- uses: actions/upload-artifact@v4
  with: { name: test-results, path: testResults.xml }
```

## Pester 4 → 5 迁移要点

- `Describe`/`Context`/`It` 语法保留，但内部块（`BeforeAll` 等）作用域更严。
- `It` 内只跑断言；fixtures 全挪到 `BeforeAll/BeforeEach`。
- Mock 默认仅当前 `Describe/Context` 范围。
- 用 `New-PesterConfiguration`，不再传 hashtable 给 `Invoke-Pester`。
- 详见 <https://pester.dev/docs/migrations/v4-to-v5>。

## 检查清单

- [ ] Pester 5.x（不混用 4.x）
- [ ] `BeforeAll/BeforeEach` 而非 `It` 内做 setup
- [ ] mock 模块函数加 `-ModuleName`
- [ ] Private 函数用 `InModuleScope` 测
- [ ] 文件 IO 走 `$TestDrive`
- [ ] `PSScriptAnalyzerSettings.psd1` 入版本控
- [ ] CI 跑 `Invoke-Pester -CI` + `Invoke-ScriptAnalyzer -EnableExit`
- [ ] 覆盖率 ≥ 80%（视项目）
- [ ] 测试与 Public 函数 1:1 对应

## 权威参考

- Pester 5 Docs — <https://pester.dev/>
- Pester 4→5 Migration — <https://pester.dev/docs/migrations/v4-to-v5>
- PSScriptAnalyzer — <https://learn.microsoft.com/powershell/utility-modules/psscriptanalyzer/overview>
- PSSA Rules — <https://learn.microsoft.com/powershell/utility-modules/psscriptanalyzer/rules/readme>
