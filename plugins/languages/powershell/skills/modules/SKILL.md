---
name: powershell-modules
description: |
  PowerShell module authoring and distribution: .psd1 manifest, .psm1 root module,
  function/cmdlet/variable/alias export rules, scope (Script/Private/Global),
  PSResourceGet (Install-PSResource) replacing the legacy PowerShellGet v2,
  PSGallery publish workflow, semantic versioning, module layout (Public/Private
  folders + dot-source loader), binary modules basics, RequiredModules and
  CompatiblePSEditions. Use proactively when the user asks to "写 PowerShell 模块 /
  ps 模块发布 / Publish-PSResource / psgallery / module manifest". Also triggers on
  "psd1", "psm1", "Export-ModuleMember", "PSResourceGet", "Install-PSResource",
  "PowerShellGet", "PSGallery".
---

# PowerShell 模块规范

## 模块类型

| 类型 | 扩展 | 用途 |
|------|------|------|
| **脚本模块** | `.psm1` | 纯 PowerShell 函数，最常见 |
| **清单模块** | `.psd1` | 元数据 + 指向 .psm1 / .dll，发布必备 |
| **二进制模块** | `.dll` | C# 编译的 cmdlet |
| **manifest 模块** | `.psd1` only | 聚合多个模块 |

## 标准目录布局

```
MyModule/
├── MyModule.psd1               # 清单（版本/作者/导出列表）
├── MyModule.psm1               # 根模块，仅做加载
├── Public/                     # 公开函数（自动导出）
│   ├── Get-Foo.ps1
│   └── Set-Foo.ps1
├── Private/                    # 内部函数（不导出）
│   └── Get-Internal.ps1
├── Classes/
│   └── MyType.ps1
├── Tests/
│   └── MyModule.Tests.ps1      # Pester
├── en-US/
│   └── MyModule-help.xml       # MAML 帮助（可选）
├── README.md
└── LICENSE
```

## 根模块 `.psm1`（dot-source loader）

```powershell
#Requires -Version 7.4
Set-StrictMode -Version 3.0

$publicFunctions  = @(Get-ChildItem -Path "$PSScriptRoot/Public"  -Filter '*.ps1' -ErrorAction SilentlyContinue)
$privateFunctions = @(Get-ChildItem -Path "$PSScriptRoot/Private" -Filter '*.ps1' -ErrorAction SilentlyContinue)

foreach ($file in @($privateFunctions) + @($publicFunctions)) {
    try {
        . $file.FullName
    } catch {
        Write-Error "Failed to import $($file.FullName): $_"
    }
}

Export-ModuleMember -Function $publicFunctions.BaseName
```

## 清单 `.psd1`

```powershell
@{
    RootModule        = 'MyModule.psm1'
    ModuleVersion     = '1.2.0'
    GUID              = 'a1b2c3d4-...'         # New-Guid 生成一次
    Author            = 'Your Name'
    CompanyName       = 'Acme'
    Copyright         = '(c) 2026 Acme. All rights reserved.'
    Description       = 'One-line description'
    PowerShellVersion = '7.4'
    CompatiblePSEditions = @('Core')           # Desktop = WinPS 5.1
    RequiredModules   = @(
        @{ ModuleName = 'Microsoft.PowerShell.SecretManagement'; ModuleVersion = '1.1.2' }
    )
    FunctionsToExport = @('Get-Foo', 'Set-Foo')    # 显式列出，不要 '*'
    CmdletsToExport   = @()
    VariablesToExport = @()
    AliasesToExport   = @()
    PrivateData = @{
        PSData = @{
            Tags         = @('automation', 'devops')
            LicenseUri   = 'https://example.com/license'
            ProjectUri   = 'https://github.com/owner/repo'
            ReleaseNotes = 'See CHANGELOG.md'
        }
    }
}
```

**关键准则**：

- `FunctionsToExport` 显式枚举，禁 `'*'`（影响自动发现性能 + 安全）。
- `PowerShellVersion` 与 `CompatiblePSEditions` 必填，CI 据此选 runner。
- `RequiredModules` 写最小版本约束，让 `Install-PSResource` 自动拉。

## 作用域

| 作用域 | 语法 | 含义 |
|--------|------|------|
| `$script:var` | 模块内全局 | `.psm1` 内函数共享 |
| `$local:var` | 当前作用域 | 函数内默认 |
| `$private:var` | 仅当前作用域 | 子作用域不可见 |
| `$global:var` | session 全局 | **慎用**，污染调用者 |
| `$using:var` | `-Parallel` / Invoke-Command | 跨边界引入 |

> 模块函数默认无法直接读写调用者的变量；需要时显式 `param()` 传入。

## PSResourceGet（PowerShellGet v3，2026 主推）

PowerShellGet v2 已废弃；PSResourceGet 提供更快、独立的资源管理。

```powershell
# 安装 PSResourceGet（Win 11 / pwsh 7.4 已内置）
Install-Module Microsoft.PowerShell.PSResourceGet -Scope CurrentUser

# 配置仓库
Register-PSResourceRepository -Name PSGallery -Uri https://www.powershellgallery.com/api/v3 -Trusted
Get-PSResourceRepository

# 安装 / 卸载
Install-PSResource -Name Pester -Version '5.5.0' -Scope CurrentUser
Update-PSResource -Name Pester
Uninstall-PSResource -Name Pester

# 搜索
Find-PSResource -Name 'PSScriptAnalyzer'
```

## 发布到 PSGallery

```powershell
# 1. 在 https://www.powershellgallery.com/account/apikeys 创建 API key
$env:NUGET_API_KEY = '...'   # 或用 SecretManagement

# 2. 本地校验清单
Test-ModuleManifest -Path ./MyModule.psd1

# 3. 静态分析
Invoke-ScriptAnalyzer -Path . -Recurse -Severity Warning

# 4. 跑测试
Invoke-Pester ./Tests -Output Detailed

# 5. 发布
Publish-PSResource -Path ./MyModule -ApiKey $env:NUGET_API_KEY -Repository PSGallery
```

CI 模板（GitHub Actions）：

```yaml
- uses: PowerShell/PSResourceGet@v1
- shell: pwsh
  run: |
    Test-ModuleManifest ./MyModule.psd1
    Invoke-ScriptAnalyzer -Path . -Recurse -Severity Warning -EnableExit
    Invoke-Pester -CI
    if ($env:GITHUB_REF -like 'refs/tags/v*') {
        Publish-PSResource -Path ./MyModule -ApiKey $env:PSGALLERY_KEY
    }
```

## 版本管理（SemVer）

- `ModuleVersion` 走 SemVer `MAJOR.MINOR.PATCH`。
- 预发布走 `Prerelease` 字段（`PrivateData.PSData.Prerelease = 'beta1'`）→ 显示 `1.2.0-beta1`。
- 一次只更一处版本号，靠 `Update-ModuleManifest -ModuleVersion ...`。

## 模块加载与卸载

```powershell
Import-Module ./MyModule.psd1 -Force -Verbose
Get-Module MyModule | Remove-Module
Get-Command -Module MyModule
```

> `-Force` 强制重载，开发期常用。生产代码禁用 `-Force` 隐藏的副作用。

## 二进制模块（C# cmdlet）速览

```csharp
[Cmdlet(VerbsCommon.Get, "Greeting")]
public class GetGreetingCommand : PSCmdlet {
    [Parameter(Mandatory = true)]
    public string Name { get; set; } = "";

    protected override void ProcessRecord() {
        WriteObject($"Hello, {Name}!");
    }
}
```

`.csproj` 引用 `Microsoft.PowerShell.SDK`，build 产物 `.dll` 在 `.psd1` 的 `RootModule` 引用。

## 检查清单

- [ ] 目录布局：Public / Private / Tests
- [ ] `.psd1` 通过 `Test-ModuleManifest`
- [ ] `FunctionsToExport` 显式列出
- [ ] `CompatiblePSEditions` 与 `PowerShellVersion` 与目标匹配
- [ ] GUID 已生成且固定
- [ ] PSScriptAnalyzer 零警告
- [ ] Pester 测试覆盖
- [ ] PSResourceGet 安装/卸载流程验证
- [ ] CI 自动发布走 tag 触发

## 权威参考

- about_Modules — <https://learn.microsoft.com/powershell/module/microsoft.powershell.core/about/about_modules>
- PSResourceGet — <https://learn.microsoft.com/powershell/gallery/powershellget/overview>
- PSGallery — <https://www.powershellgallery.com/>
- Module manifest reference — <https://learn.microsoft.com/powershell/scripting/developer/module/how-to-write-a-powershell-module-manifest>
- about_Scopes — <https://learn.microsoft.com/powershell/module/microsoft.powershell.core/about/about_scopes>
