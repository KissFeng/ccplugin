---
description: 跑 cortex vault lint --fix 强制对齐 (无入参, AUTO_MODE strict)
---

# /cortex:lint

[AUTO_MODE strict: 禁止询问用户决策, AskUserQuestion 视为不可用, 全自动 fail-fast]

对 cortex vault 跑 lint 强制对齐 (autofix all rules)。

**必须**第一步用 Bash 工具执行:

```bash
CONFIG="$HOME/.cortex/config.json"
INSTALL_PATH="$(jq -r .install_path "$CONFIG")"
VAULT="$(jq -r .vault "$CONFIG")"
cd "$INSTALL_PATH" && PYTHONPATH=. python3 -m lint.run --vault "$VAULT" --fix
```

解析 JSON 输出。检查 exit code:
- 0 → 报告 fixed 数 + 各 rule hit 详情
- != 0 → 列出错误信息

## 严格禁止 (违反 = 命令失败)

下列内容 **任一出现** 视为契约违反, 必须立即终止输出, 不得发出:

1. **任何包含"修复建议"/"建议"/"推荐操作"的章节、表格、列表**
   - 例如 `## 修复建议`, `### 建议`, `| 类型 | 操作 |` 这种格式
2. **任何形式的用户确认问句**
   - "需确认?" / "是否执行?" / "需要 --fix 吗?" / "要继续吗?" / "ok?" / 末尾问号
3. **AskUserQuestion 工具调用** (允许工具列表已排除, 调用会失败)
4. **"下一步" / "后续" / "建议跑..." / "建议人工补..." 这类导引语**
5. **任何针对未 autofix 规则的人工操作建议** (dead-wikilink / orphan-page / vault-structure-violation 等非 autofix 规则的处理提示)

## 唯一允许输出 (除此之外都禁止)

```
fixed: <N>
rules_hit: [<rule>: <count>, ...]
errors_remaining: <N>   # 仅当 > 0 才显示
```

完成. 无追问, 无建议, 无下一步。
