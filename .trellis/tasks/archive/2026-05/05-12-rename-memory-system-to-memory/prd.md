# PRD — 记忆体系 → 记忆 重命名

## 背景

User: 顶层目录 `记忆体系/` 太长, 改 `记忆/`。

42 文件含 `记忆体系` 引用 (plugin 内)。需机械替换 + 物理重命名目录/seed。

## 目标

全面重命名 `记忆体系` → `记忆`, 涵盖:
- presets/_structure.json (directories + seed_files)
- presets/seed/记忆体系/ → presets/seed/记忆/ (物理 mv)
- lint/schemas.py root_dirs
- 所有 SKILL.md 引用
- 所有 templates/ 引用
- agents/* 引用
- hooks/* 内字符串 (cortex_locale 等)
- locales/*.yml
- cron/*.sh
- install_wrappers.sh 生成 wrapper 内引用
- mcp/cortex_mcp.py resolve_uri (`<vault>/记忆体系/L<N>-<name>` → `<vault>/记忆/...`)
- 测试期望值
- 文档

## 设计

### 1. 物理重命名

```bash
git mv plugins/tools/cortex/presets/seed/记忆体系 plugins/tools/cortex/presets/seed/记忆
```

### 2. 全文字符串替换

```bash
grep -rln "记忆体系" plugins/tools/cortex/ | xargs sed -i '' 's/记忆体系/记忆/g'
```

注意:
- 不替换 .git/ / __pycache__/
- 不替换 .trellis/ 内 (任务存档保留历史)

### 3. URI scheme 保留 `L<N>://` 不变 (与目录名无关)

URI `L0://identity/me` 仍解析到 `<vault>/记忆/L0-核心/identity/me.md` (路径段改)。

### 4. 测试调整

`test_*.py` 含 `记忆体系` 字符串的也跟着改。

### 5. marketplace 缓存同步

rsync 同步。

## 验收

- [ ] grep `记忆体系` → 0 (除 .trellis/tasks/archive/)
- [ ] presets/seed/记忆/ 存在, presets/seed/记忆体系/ 不存在
- [ ] _structure.json directories 含 `记忆` 不含 `记忆体系`
- [ ] lint/schemas.py LYT root_dirs 含 `记忆`
- [ ] python -m lint.run 跑空 vault 创建 `记忆/L0-核心` 等 (不再 `记忆体系/`)
- [ ] mcp resolve_uri L0:// → 记忆/L0-核心/
- [ ] 278 tests PASS

## 风险

| 风险 | 缓解 |
|------|------|
| 部分 sed 误改非目录字符串 (e.g. SKILL 描述中"AI 记忆体系") | 检查后手动恢复; 或更精确 sed (仅 `/记忆体系/` 或 ` 记忆体系 ` 边界) |
| 老 vault 用户已有 `记忆体系/` 目录 | lint vault-misaligned + structure-missing 会建 `记忆/`, 老 `记忆体系/` 作 vault-structure-violation mv 到 backup; 用户应手动迁数据 |
| 测试期望字符串 | 跟着改, 重新跑 |

## 实施

单 agent 串行:
1. git mv 目录
2. sed -i '' 全文替换
3. 跑 lint + pytest 验证
4. rsync marketplace 缓存
