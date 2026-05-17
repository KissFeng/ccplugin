所有 PowerShell / pwsh / batch 代码必须遵守以下 Skills 规范：
- Skill(powershell-core) - 核心规范：PowerShell 7.4 LTS / 5.1、Verb-Noun、advanced function、pipeline、$PSStyle
- Skill(powershell-modules) - 模块规范：.psd1 / .psm1、PSResourceGet、PSGallery 发布
- Skill(powershell-error) - 错误处理规范：terminating / non-terminating、try-catch、$ErrorActionPreference、$LASTEXITCODE
- Skill(powershell-testing) - 测试规范：Pester 5.x、PSScriptAnalyzer
- Skill(powershell-windows-shell) - Windows shell：cmd / batch (.bat / .cmd) 兼容子集

每一个 `*.ps1` / `*.psm1` / `*.psd1` / `*.Tests.ps1` 文件都不得超过 600 行，推荐 200~400 行。
