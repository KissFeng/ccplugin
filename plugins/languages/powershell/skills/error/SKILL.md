---
name: powershell-error
description: |
  PowerShell error handling: terminating vs non-terminating errors,
  $ErrorActionPreference levels (Continue/Stop/SilentlyContinue/Ignore/Inquire),
  -ErrorAction parameter scope, try/catch/finally with typed catches, ErrorRecord
  anatomy ($_.Exception/$_.CategoryInfo/$_.TargetObject), throw vs Write-Error,
  trap statement, $LASTEXITCODE for native commands, $PSNativeCommandUseErrorActionPreference
  (7.3+), $? boolean, exit codes, custom exception classes. Use proactively when the
  user asks "PowerShell 错误处理 / try-catch / ErrorAction / 退出码 / LASTEXITCODE /
  terminating error". Also triggers on "throw", "trap", "$Error", "ErrorRecord",
  "$ErrorActionPreference", "终止错误", "非终止错误".
---

# PowerShell 错误处理规范

PowerShell 错误分两类，行为差异是大多 bug 的根因。

## Terminating vs Non-terminating

| 类型 | 触发 | 默认行为 | 能 catch？ |
|------|------|---------|-----------|
| **Terminating** | `throw` / `[CmdletBinding()]` 致命错误 / `$ErrorActionPreference='Stop'` | 中断管道 | ✅ |
| **Non-terminating** | `Write-Error` / cmdlet 局部失败 | 写入 `$Error`，继续 | ❌（除非 `-ErrorAction Stop`） |

## `$ErrorActionPreference`

```powershell
$ErrorActionPreference = 'Stop'   # 推荐脚本默认
```

| 值 | 行为 |
|----|------|
| `Continue`（默认） | 打印错误，继续 |
| `Stop` | 转 terminating，可 catch |
| `SilentlyContinue` | 静默，仅记 `$Error` |
| `Ignore` | 不记 `$Error`，慎用 |
| `Inquire` | 询问（交互式） |
| `Break` (7.0+) | 进调试器 |

**作用域**：脚本顶层设置仅影响当前脚本；模块函数内独立。

## 原生命令错误传播（7.3+）

```powershell
$PSNativeCommandUseErrorActionPreference = $true
```

启用后，`git`、`cmake`、`pytest` 等原生命令非零 `$LASTEXITCODE` 也会触发 `$ErrorActionPreference`。**强烈推荐脚本头部启用**。

## try / catch / finally

```powershell
try {
    $data = Invoke-RestMethod -Uri $url -ErrorAction Stop
    Process-Data $data
}
catch [System.Net.Http.HttpRequestException] {
    Write-Warning "Network: $($_.Exception.Message)"
    return
}
catch [System.IO.IOException] {
    Write-Warning "IO: $($_.Exception.Message)"
    throw                # 重新抛出
}
catch {
    Write-Error "Unexpected: $_"
    throw
}
finally {
    Cleanup-Resources
}
```

类型化 catch 块按顺序匹配；最后的无类型 catch 兜底。`$_` 是 `ErrorRecord`。

## ErrorRecord 结构

```powershell
catch {
    $_.Exception.Message         # 异常文本
    $_.Exception.GetType().FullName
    $_.CategoryInfo              # 分类（NotSpecified / InvalidArgument...）
    $_.FullyQualifiedErrorId     # 唯一 ID（适合自动化匹配）
    $_.TargetObject              # 出错对象
    $_.ScriptStackTrace          # 调用栈
    $_.InvocationInfo.PositionMessage   # 行号 / 上下文
}
```

## throw / Write-Error / $PSCmdlet.ThrowTerminatingError

```powershell
# 简单
throw "Invalid input: $name"

# 强类型（推荐）
throw [System.ArgumentException]::new('name cannot be empty', 'Name')

# 自定义异常类（PowerShell 5+ class）
class MyAppException : System.Exception {
    MyAppException([string]$m) : base($m) { }
}
throw [MyAppException]::new('boom')

# 在 advanced function 内：ThrowTerminatingError 给调用方更好的栈帧
$err = [System.Management.Automation.ErrorRecord]::new(
    [InvalidOperationException]::new('failed'),
    'MyApp.Failed',
    [System.Management.Automation.ErrorCategory]::InvalidOperation,
    $null
)
$PSCmdlet.ThrowTerminatingError($err)

# Write-Error：非终止，调用方可决定是否升级
Write-Error -Message 'soft warn' -Category InvalidData -ErrorId 'MyApp.SoftWarn'
```

## trap（不推荐，仅维护旧脚本）

```powershell
trap {
    Write-Warning "caught: $_"
    continue        # 跳过当前语句继续
}
```

> 新代码用 try/catch；trap 是早期遗物，作用域语义令人困惑。

## `$LASTEXITCODE` 与原生命令

```powershell
git status
if ($LASTEXITCODE -ne 0) {
    throw "git failed: $LASTEXITCODE"
}

# 推荐 7.3+ 启用 $PSNativeCommandUseErrorActionPreference 后这步可省
```

## `$?` 与 `$Error`

```powershell
Some-Cmdlet
if (-not $?) { Write-Warning 'last command failed' }

$Error[0]            # 最近一次错误
$Error.Clear()       # 清空
```

> `$?` 只是布尔，信息少；优先 `try/catch`。

## 错误的 -ErrorAction 局部覆盖

```powershell
Get-Item /nope -ErrorAction Stop                 # 这一调用变 terminating
Get-Item /nope -ErrorAction SilentlyContinue     # 静默
Get-Item /nope -ErrorVariable myErr              # 捕获到变量（不抑制）
Get-Item /nope -ErrorAction Stop -ErrorVariable +allErrs   # 累积
```

## 退出码

```powershell
exit 0    # 成功
exit 1    # 通用失败
exit 2    # 用法错误（约定俗成）
```

调用方通过 `$LASTEXITCODE`（pwsh）或 `$?` / `%ERRORLEVEL%`（cmd）读取。脚本应文档化退出码语义。

## 检查清单

- [ ] 文件头 `$ErrorActionPreference = 'Stop'`
- [ ] 7.3+ 启用 `$PSNativeCommandUseErrorActionPreference = $true`
- [ ] try/catch 处理具体异常类型，而非裸 catch
- [ ] catch 中重新 `throw` 或包装抛出（保留原异常）
- [ ] cmdlet 调用关键路径加 `-ErrorAction Stop`
- [ ] 模块函数内用 `$PSCmdlet.ThrowTerminatingError`，不用 `throw "string"`
- [ ] 原生命令检查 `$LASTEXITCODE`（或用 preference 变量自动）
- [ ] 错误信息含上下文（文件/操作/输入），不只 `"failed"`
- [ ] `FullyQualifiedErrorId` 唯一，便于自动化匹配

## 权威参考

- about_Try_Catch_Finally — <https://learn.microsoft.com/powershell/module/microsoft.powershell.core/about/about_try_catch_finally>
- about_Throw — <https://learn.microsoft.com/powershell/module/microsoft.powershell.core/about/about_throw>
- about_Preference_Variables — <https://learn.microsoft.com/powershell/module/microsoft.powershell.core/about/about_preference_variables>
- ErrorRecord class — <https://learn.microsoft.com/dotnet/api/system.management.automation.errorrecord>
