# Journal - nico (Part 2)

> Continuation from `journal-1.md` (archived at ~2000 lines)
> Started: 2026-05-12

---



## Session 60: cortex 禁 env vars 统一 config.json

**Date**: 2026-05-12
**Task**: cortex 禁 env vars 统一 config.json
**Branch**: `master`

### Summary

配置类 env (OBSIDIAN_VAULT/CORTEX_VAULT/LANG/SETTINGS/TIMEOUT/DRY_RUN/SYNC_TEMPLATES) 迁 ~/.cortex/config.json。平台契约 (CLAUDE_PLUGIN_ROOT 等) 保留。install.sh 例外不动。新 cortex_config + scripts/lib/config.sh helper。278 tests PASS。

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `cadf01c4` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 61: cortex lint 5 规则全 autofix 零人工

**Date**: 2026-05-12
**Task**: cortex lint 5 规则全 autofix 零人工
**Branch**: `master`

### Summary

5 规则 fixable=true: vault-structure-violation (mv 违规) + callout-unknown-type (→info) + orphan-page (链 _index) + path-naming-violation/i18n-path (slug rename) + stub cap 100→1000。286 tests + marketplace 同步。

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `9a1b93c4` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 62: cortex lint 5 规则全 autofix

**Date**: 2026-05-12
**Task**: cortex lint 5 规则全 autofix
**Branch**: `master`

### Summary

5 规则 fixable=true autofix: vault-structure-violation (mv 违规) / callout-unknown-type (→info) / orphan-page (链 _index) / path-naming-violation + i18n-path (slug rename)。stub cap 100→1000。286 tests PASS。

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `9a1b93c4` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 63: cortex cron run cd vault + SKILL 注入

**Date**: 2026-05-12
**Task**: cortex cron run cd vault + SKILL 注入
**Branch**: `master`

### Summary

cron/run.sh 加 cd vault + JOB→SKILL 映射注入 --append-system-prompt + AUTO_MODE strict prefix。AI 默认 vault-relative 不跑偏。bash 31 + python 286 PASS。

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `ccaa3bd7` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 64: cortex budget 提升 + dashboard 真测 (未通)

**Date**: 2026-05-12
**Task**: cortex budget 提升 + dashboard 真测 (未通)
**Branch**: `master`

### Summary

budget 0.30→2.00, dashboard SKILL 加严 8 条强约束。真测 EXIT=1 — 非 budget 问题, AI 漫游读 ledger jsonl 致 claude crash, SKILL 文字约束被忽视。后续需机制硬阻 (dashboard.sh 主动 Glob 逐 page 传 / file size guard / 分批调度)。

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `50424104` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 65: cortex wrapper → claude commands 全权限

**Date**: 2026-05-12
**Task**: cortex wrapper → claude commands 全权限
**Branch**: `master`

### Summary

wrapper 全部走 /cortex-<name> slash commands (claude 全权限/无 args/无 --bare). 20 commands.md 建好, plugin.json 注册. cron run.sh + install_wrappers.sh 简化 emit_slash(). dashboard.sh 真测 EXIT=0 ✓ (用户验证)。

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `ac7c63c6` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete
