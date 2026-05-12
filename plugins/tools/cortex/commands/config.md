---
description: 查看/编辑 cortex 配置 (~/.cortex/config.json) (无入参 → 列当前)
---

# /cortex:config

[AUTO_MODE strict: 禁询问, fail-fast, 仅列不改]

读取并展示 cortex 配置。

**必须**用 Bash 工具执行:

```bash
INSTALL_PATH="$(jq -r .install_path ~/.cortex/config.json)"
python3 "$INSTALL_PATH/scripts/cortex_config.py"
```

输出: 当前 `~/.cortex/config.json` 解析结果 (vault / lang / settings / install_path / timeout_default 等)。

若 config 不存在, 提示用户跑 `install.sh` 初始化。

## 严格禁止 (违反 = 契约失败)

shell wrapper 触发, 禁:

1. **任何"修复建议"/"建议"/"推荐操作"章节、表格、列表** (`## 修复建议`, `| 类型 | 操作 |`, `### 建议`)
2. **任何用户确认问句** (`需确认?`, `是否执行?`, `要继续吗?`, `ok?`, 末尾问号)
3. **AskUserQuestion 调用** (allowed-tools 已禁)
4. **"下一步" / "后续" / "如需" / "可选"导引语**
5. **针对未 autofix / 非自动项的人工操作引导**

遇歧义按**推荐默认值**直接执行, 不询问用户。
