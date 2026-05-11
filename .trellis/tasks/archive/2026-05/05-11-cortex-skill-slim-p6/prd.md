# PRD — Cortex P6 Skill Slim (删 cortex-fold + cortex-cron)

## 背景

cortex v2 14 skill,P4 加 cortex-ingest-bulk 后 15。skill description 池总长超 1500 软上限(实测 1521,部分口径 1984)。

`cortex-fold` 功能与 `agents/cortex-historian.md` 重叠(historian 也写 folds/);`cortex-cron` 运行期无重设需求,装机一次性问询即可,常驻 skill 浪费描述池。

P6 删 2 skill,功能并入 agent + install。

## 目标

skill 数 15 → 13(2 删),plugin.json + AGENT.md 同步更新,描述池回到 < 1500。

## 范围

### 删除

- `plugins/tools/cortex/skills/cortex-fold/` 整目录
- `plugins/tools/cortex/skills/cortex-cron/` 整目录

### 修改

- `.claude-plugin/plugin.json` — `skills` 数组移除 `./skills/cortex-fold` + `./skills/cortex-cron`
- `AGENT.md` — 删除 §Skills 设计原则 表中 `cortex-fold` + `cortex-cron` 行,skill 总数 14→12(不含 ingest-bulk)或 15→13(含 ingest-bulk)。对齐
- `plugins/tools/cortex/agents/cortex-historian.md` — 加 §Fold 工作流 段(吸收 cortex-fold 逻辑要点),允许 agent 直接 fold logs/
- `plugins/tools/cortex/skills/cortex-install/SKILL.md` — 加 §询问 cron (装机一次性) 段,用 `AskUserQuestion` 询问 cron 注册偏好;若用户选启用,SKILL 内联 cron 注册步骤(原 cortex-cron 的 install 流程精简版)

### 不在范围

- 不动 P0-P5 已交付代码
- 不动其它 11 个 skill
- 不动其它 7 个 agent
- 不删 cortex-historian 已有功能(只扩展)

## 详细规范

### 1. cortex-historian 扩展 §Fold 工作流

读原 `cortex-fold/SKILL.md` 提取核心逻辑:
- 扫描 `log/YYYY-MM/`
- 按月聚合到 `folds/YYYY-MM-fold-NNN.md`
- ASCII 排版,内容按 `vault.lang`
- `--apply` 落盘

写入 `agents/cortex-historian.md` §Fold 工作流 子段(在现有正文后追加),作为 agent 主动 fold 能力。

### 2. cortex-install 加 §询问 cron 段

参照 P5 的 §询问 git auto-sync (P5) 模式,用 `AskUserQuestion` 询问:

```
"是否注册 cortex 周期任务?"
选项:
- 不启用 (默认)
- launchd (macOS)
- cron (Linux/macOS)
- GitHub Actions (远程仓库)
```

若用户选启用,SKILL 内联指引(精简版,详细脚本 vendor 自 cortex-cron):
- launchd: 写 `~/Library/LaunchAgents/dev.cortex.plist`
- cron: append `~/.cortexrc.cron`
- GHA: 提示用户复制 `.github/workflows/cortex.yml` 模板

cron 任务:每周 lint + 每月 fold + 每日 dashboard 刷新。

### 3. plugin.json 改动

```jsonc
"skills": [
  "./skills/cortex-canvas",
  // 删除: "./skills/cortex-cron",
  "./skills/cortex-dashboard",
  "./skills/cortex-doctor",
  // 删除: "./skills/cortex-fold",
  "./skills/cortex-ingest",
  "./skills/cortex-ingest-bulk",  // P4 加
  "./skills/cortex-install",
  "./skills/cortex-lint",
  "./skills/cortex-locale",
  "./skills/cortex-new",
  "./skills/cortex-refactor",
  "./skills/cortex-save",
  "./skills/cortex-search",
  "./skills/cortex-session"
]
```

skill 数:15 → 13。

### 4. AGENT.md skill 表更新

5 自动 + 9 显式 → **5 自动 + 7 显式**(cortex-fold/cron 都是显式)。

更新 §Skills 设计原则 段:
- 删 cortex-cron / cortex-fold 表行
- 总长更新:"14 个 skill" → "13 个 skill"(若文档说 14 是不含 ingest-bulk;含则 "15 → 13")

实际跑命令算清当前数,文档对齐实际。

### 5. 描述池验证

跑:

```bash
python3 -c "
import re, pathlib
total = 0
for p in pathlib.Path('plugins/tools/cortex/skills').glob('*/SKILL.md'):
    text = p.read_text()
    m = re.search(r'^description:\s*(.+)$', text, re.M)
    if m and 'disable-model-invocation: true' not in text:
        total += len(m.group(1))
print(f'auto skill description pool: {total} chars')
"
```

预期 P6 后 < 1500。

## 验收标准

1. `plugins/tools/cortex/skills/cortex-fold/` 不存在
2. `plugins/tools/cortex/skills/cortex-cron/` 不存在
3. `plugin.json` skills 数组无 cortex-fold / cortex-cron,JSON 合法,长度 13
4. `agents/cortex-historian.md` 含 §Fold 工作流 段,描述 fold logs 能力
5. `skills/cortex-install/SKILL.md` 含 §询问 cron 段,**用 AskUserQuestion**
6. AGENT.md skill 表无 cortex-fold/cron 行,总数对齐实际(13)
7. 描述池总长 < 1500 字符(自动 skill,不含 `disable-model-invocation: true`)
8. P0-P5 不回归:`bash plugins/tools/cortex/tests/run.sh` 全绿
9. 没有任何 file 残留引用 `cortex-fold` / `cortex-cron`(允许 archive/log 历史引用,但活跃 source 不引):
   ```bash
   grep -rn "cortex-fold\|cortex-cron" plugins/tools/cortex/ --include='*.md' --include='*.json' --include='*.py' --include='*.sh' \
     | grep -v archive | grep -v fold/ | grep -v cron/
   ```
   预期空(或只剩 release notes / CHANGELOG / docs/changelog 类历史叙述)

## 不变量

- 删后所有功能仍可触达(historian agent 接 fold,cortex-install 接 cron 注册)
- AGENT.md skill 表数字与实际 plugin.json 一致
- 描述池字符数显著降(从 1521+ 降到 < 1500)

## 风险

- **cortex-fold 逻辑丢失**:删目录前需保 fold 算法到 historian agent。**缓解**:agent 段写明 fold 算法,不只是引用
- **cron 用户失去触发口**:原 `/cortex:cron` 没了。**缓解**:cortex-install 重跑可再次配置;用户手动编辑 plist/crontab 永远可行
- **AGENT.md 数字漂移**:14/15 是 P0 写的旧数,得用跑出来的实际数对齐
- **测试无影响**:2 skill 都是 markdown 无 python 测试,删除不破坏 pytest
