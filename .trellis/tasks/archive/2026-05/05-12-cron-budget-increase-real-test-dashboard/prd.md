# PRD — cron budget 提升 + 真测 dashboard.sh

## 痛点
跑 `~/.cortex/scripts/dashboard.sh` 97s 后 exit 1, **无 result JSON** (claude 中途退)。诊断:
- `--max-budget-usd 0.30` 超限可能 (vault 1000+ md + 大 SKILL + dashboard 多页, token 量大)
- 或 SKILL 让 AI 漫游 (读 ledger jsonl 等大文件)

## 目标
1. 提 budget cron job 0.30 → 2.00 USD (覆盖大任务)
2. cortex-dashboard SKILL 精简, 仅刷新单 dashboard 一次 (避免循环大开销)
3. 真跑测 → exit 0

## 设计

### 1. budget 提升

`scripts/cron/run.sh` `--max-budget-usd 0.30` → `2.00`:
```bash
CMD=(claude
  --bare
  --no-session-persistence
  --settings "$SETTINGS"
  --max-budget-usd 2.00   # was 0.30
  -p "$FULL_PROMPT"
)
```

`install_wrappers.sh` user-facing 11 wrapper 同 `--max-budget-usd 2.00`。

### 2. cortex-dashboard SKILL 精简执行

加 AUTO_MODE 段说明:
```
AUTO_MODE 行为 (cron 调):
1. Glob 仪表盘/*.md 一次 (cap 20 页)
2. 每页只读 frontmatter (前 30 行), 不读全文
3. 按 view_query.kind:
   - memory: Glob 记忆/<level>/*.md 取 frontmatter, 不读 body
   - ledger: 仅 wc -l jsonl 取条数, 不读内容
   - knowledge: mcp__obsidian__obsidian_simple_search 限 top 10
4. 渲染 HTML 注入 <!-- DASH:BEGIN -->...<!-- DASH:END -->
5. 失败 stale_after 检查跳过, fail-fast
6. 输出 JSON: {refreshed: [...], skipped: M, errors: K}
```

强调 "不读大文件全文" — 避免 ledger.jsonl 全读爆 token。

### 3. 真跑测验证

```bash
~/.cortex/scripts/dashboard.sh
```
应 exit 0 + JSON 输出。如失败, 看 ~/.cache/cortex/cron/dashboard-*.err 排查。

## 实施

1. cron/run.sh budget 提
2. install_wrappers.sh 11 wrapper budget 提
3. cortex-dashboard SKILL 加严 AUTO_MODE 段
4. 真跑测
5. marketplace 同步

## 验收
- [ ] cron/run.sh budget=2.00
- [ ] 11 wrapper budget=2.00
- [ ] cortex-dashboard SKILL 限"不读大文件全文"
- [ ] **真跑 `~/.cortex/scripts/dashboard.sh` exit 0** (核心)
- [ ] 286 tests PASS
- [ ] marketplace 同步
