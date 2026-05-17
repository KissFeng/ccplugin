---
name: powershell-windows-shell
description: |
  Windows cmd.exe and batch script (.bat / .cmd) compatibility subset for cases when
  PowerShell is unavailable or wrappers must run under legacy contexts. Covers
  setlocal / endlocal, enabledelayedexpansion (!var! vs %var%), %~dp0 /
  %~nx0 / %~f0 modifiers, errorlevel checks, FOR /F loops, doskey limits,
  argument quoting hazards, .bat vs .cmd differences, and decision rules for when
  to fall back to batch versus invoking pwsh. Use proactively when the user asks
  "写 batch 脚本 / cmd 脚本 / .bat / .cmd / Windows 批处理 / 调用 cmd". Also
  triggers on "cmd.exe", "batch", "setlocal", "errorlevel", "%~dp0", "doskey".
---

# Windows Shell：cmd.exe + Batch 兼容子集

PowerShell 是 Windows 自动化首选。**仅在以下场景退回 batch**：

- 引导脚本：要在没装 pwsh 的最小 Windows 镜像上跑（容器 / WinPE / RE / 老 Win Server）。
- 安装器子步骤：MSI / setup.exe 调用上下文。
- 经典 CI runner / task scheduler 的 legacy step。
- 一行启动器（双击运行 → 启 pwsh）。

> 任何复杂逻辑（数组 / 字典 / 错误处理）都不要写 batch；写 `.ps1` 后用 `.cmd` wrapper 启动。

## `.bat` vs `.cmd`

| 差异 | `.bat` | `.cmd` |
|------|--------|--------|
| 出身 | DOS 4DOS | Windows NT |
| `ERRORLEVEL` 在内部命令后行为 | 不更新 | 更新 |
| 兼容性 | 老系统也认 | NT 起 |

**新脚本一律 `.cmd`**。`.bat` 只为最大兼容性（极少需要）。

## 必备头部模板

```bat
@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul                 :: UTF-8（处理中文输出更稳）
set "SCRIPT_DIR=%~dp0"          :: 脚本所在目录（带尾部 \）
set "SCRIPT_NAME=%~nx0"
```

- `@echo off`：抑制命令回显（脚本第一行）。
- `setlocal`：把变量作用域限制到当前脚本（结束时自动 endlocal）。
- `EnableDelayedExpansion`：开启 `!var!` 实时展开，循环内必备。
- `chcp 65001`：UTF-8 代码页（Win 10 1903+ 稳定）。

## 参数与路径修饰符

```
%0      脚本名（如调用方式中所写）
%~0     去除引号
%~f0    完整路径
%~d0    驱动器（C:）
%~p0    路径（不含驱动器）
%~dp0   驱动器 + 路径（脚本所在目录，**最常用**）
%~n0    文件名（不含扩展）
%~x0    扩展名
%~nx0   文件名 + 扩展
%~s0    短 8.3 路径
%~a0    属性
%~t0    修改时间
%~z0    大小
```

参数 `%1` `%2` ... 同理可叠加修饰符。`%*` 是全部参数。

## 变量与延迟展开

```bat
set "name=alpha"
echo %name%                     :: 解析时展开

setlocal EnableDelayedExpansion
for %%i in (a b c) do (
    set "current=%%i"
    echo %current%              :: ❌ 永远空（解析时一次性展开）
    echo !current!              :: ✅ 运行时展开
)
```

**记住**：`%var%` 在**解析整段块**时展开一次；`!var!` 在**每次执行**时展开。FOR / IF 块内总用 `!`。

## errorlevel

```bat
some_command.exe
if errorlevel 1 (
    echo failed
    exit /b 1
)

:: 等价显式
some_command.exe
if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%
```

注意：`if errorlevel N` 测试 **>=N**，不是 `==N`。精确比较用 `%ERRORLEVEL% equ N`。

## FOR /F 循环

```bat
:: 遍历文件行
for /f "usebackq tokens=1,2 delims=:" %%a in ("config.txt") do (
    echo key=%%a value=%%b
)

:: 捕获命令输出
for /f "usebackq delims=" %%i in (`git rev-parse HEAD`) do set "sha=%%i"
echo %sha%
```

| 选项 | 含义 |
|------|------|
| `usebackq` | 反引号执行命令 / 双引号是字符串 |
| `tokens=1,2` | 取第 1、2 段 |
| `delims=:` | 分隔符 |
| `skip=1` | 跳过开头 N 行 |
| `eol=#` | 行注释起始字符 |

## 函数（标签 + call）

```bat
@echo off
call :greet "world"
exit /b 0

:greet
setlocal
set "name=%~1"
echo Hello, %name%!
endlocal
exit /b 0
```

`call :label` 进函数，`exit /b N` 返回并设 errorlevel。

## 启动 PowerShell（推荐模式）

```bat
@echo off
:: 任何超过 20 行的逻辑：写 .ps1，这里只做 wrapper
where pwsh >nul 2>nul && (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0script.ps1" %*
) || (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0script.ps1" %*
)
exit /b %ERRORLEVEL%
```

- `pwsh` 是 PowerShell 7+，`powershell` 是 Windows PowerShell 5.1。
- `-NoProfile` 避免加载用户 profile（启动快、行为可预测）。
- `-ExecutionPolicy Bypass` 仅对当前进程，不改系统策略。

## 引号陷阱

batch 的引号处理极其反直觉：

```bat
set "var=hello world"           :: ✅ 推荐：等号紧贴变量名，引号包整体
set var="hello world"           :: ❌ var 的值真的含引号

if "%var%"=="hello" (...)       :: ✅ 标准比较

:: 含空格的路径
"%~dp0bin\tool.exe" arg1 arg2   :: ✅
%~dp0bin\tool.exe arg1 arg2     :: ❌ 空格断行
```

## doskey 限制

`doskey` 定义 cmd 别名 **仅当前 cmd 会话有效**，且无法在 batch 内供后续行使用。**别想用 doskey 写脚本**。Windows 上"持久别名"的方案：

- PowerShell：`Set-Alias` + `$PROFILE`。
- cmd：用 AutoRun 注册表项 + doskey macrofile，复杂且不推荐。

## 常见反模式

| 反模式 | 修正 |
|--------|------|
| 复杂逻辑用 batch | 改 `.ps1` + `.cmd` wrapper |
| `goto :EOF` 当函数返回 | OK，但配合 `call :label` 与 `exit /b` 更明确 |
| 循环内忘记 `EnableDelayedExpansion` | 顶部加 setlocal |
| 引号 `set var="x"` 包含引号 | `set "var=x"` |
| 用 `%var%` 期望循环内更新 | 改 `!var!` |
| 忽略 errorlevel | 每个关键命令后 `if errorlevel 1 exit /b 1` |
| 硬编码 `C:\...` | `%~dp0` 相对脚本 |
| 不设代码页 | 中文乱码；加 `chcp 65001` |

## 退回 batch 的决策表

| 需求 | batch 够？ | 推荐 |
|------|-----------|------|
| 启动一个程序 + 设环境变量 | ✅ | batch wrapper |
| 解析 JSON / 调用 REST | ❌ | PowerShell |
| 错误恢复 / 复杂控制流 | ❌ | PowerShell |
| 数组 / 字典 | ❌ | PowerShell |
| 跨主版本兼容（XP+）启动器 | ✅ | batch |
| 调用 MSI 安装 | ✅ | batch |
| 文件批量处理 ≤ 5 行 | ✅ | batch / forfiles |
| 调用 git / docker 流水 | △ | 倾向 PowerShell |

## 调试

```bat
:: 临时回显
@echo on

:: 步进
pause                           :: 等用户按键
echo DEBUG: var=[%var%]         :: 打印中间状态

:: 完整 trace
cmd /c "yourscript.cmd args" 2>&1 | tee trace.log
```

## 检查清单

- [ ] 文件扩展 `.cmd`（除非真需 `.bat`）
- [ ] 头部 `@echo off` + `setlocal EnableExtensions EnableDelayedExpansion`
- [ ] 路径用 `%~dp0` 相对脚本
- [ ] 引号 `set "var=value"`
- [ ] 循环内用 `!var!`
- [ ] 每个关键命令后查 errorlevel
- [ ] 复杂逻辑提取到 `.ps1`，batch 仅 wrapper
- [ ] UTF-8 输出加 `chcp 65001`
- [ ] 退出码用 `exit /b N`

## 权威参考

- Windows Commands Reference — <https://learn.microsoft.com/windows-server/administration/windows-commands/windows-commands>
- cmd.exe Reference — <https://learn.microsoft.com/windows-server/administration/windows-commands/cmd>
- SS64 cmd Reference — <https://ss64.com/nt/>
- DosTips Forum (batch 技巧) — <https://www.dostips.com/>
- "Variable Substitution" docs — <https://ss64.com/nt/syntax-args.html>
