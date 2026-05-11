# PRD — install.sh 幂等性 (config 复用 + cron 去重)

## 背景

用户跑 `bash plugins/tools/cortex/install.sh` 报 2 个 UX 问题:

1. **询问顺序错** — 先问 vault/lang/settings,**之后**才问 `~/.cortex/config.json` 是否覆盖。用户已选不覆盖,但前面的输入白填。
2. **cron 重复装** — 没检测当前 crontab/launchd 已有 cortex job,每次跑都重新问 + 重新输出 snippet。也不清理失效项 (脚本路径不存的 job)。

## 目标

install.sh 改幂等:已存在不重问,失效自动 prune。

## 范围

### 修改文件

- `plugins/tools/cortex/install.sh`
  - 反序 config 检测/询问 (line 264-317 重构)
  - 新增 `read_existing_config()` 解析 `~/.cortex/config.json` 字段
  - 新增 `detect_existing_cron()` 检测 crontab/launchd 中 cortex job
  - 新增 `prune_stale_cron()` 删失效 (wrapper 路径不存)
  - 改 cron 询问段 (line 384-399): 检测后再决策

### 不在范围

- `install_cron.sh` 不改 (它只打印 snippet,本就无副作用)
- launchd plist / GHA 检测 P2 留 backlog (当前只精化 crontab + launchd `launchctl list` 探测)
- 不动 P0-P6 已交付内容

## 详细规范

### 1. 反序流程

当前 (line 264-317):
```
detect_local_state                  # 设 CONFIG_EXISTS
... 收集字段 (prompt vault/lang/settings) ...
... 写 config 段 (调 should_overwrite_config 才问覆盖) ...
```

改后:
```
detect_local_state                  # 设 CONFIG_EXISTS
if [[ $CONFIG_EXISTS == 1 ]]; then
  if should_overwrite_config; then     # 提前到这里问
    OVERWRITE_CONFIG=1
    # 走原 prompt_value 收集字段
  else
    OVERWRITE_CONFIG=0
    read_existing_config              # 复用 VAULT/LANG/SETTINGS
    log_info "复用现有 config: vault=$VAULT lang=$LANG_CODE settings=$SETTINGS"
  fi
else
  OVERWRITE_CONFIG=1
  # 走 prompt_value
fi
```

`should_overwrite_config` 已存在 (line 273-278),保留逻辑不变,仅调用位置前移。

### 2. `read_existing_config()` 新函数

```bash
read_existing_config() {
  local cfg="$HOME/.cortex/config.json"
  [[ ! -f "$cfg" ]] && return 1
  # 用 python3 解析 (cortex 已依赖 python3)
  local out
  out=$(python3 -c "
import json, sys
try:
    d = json.load(open('$cfg'))
    print(d.get('vault_path', ''))
    print(d.get('lang', 'zh-CN'))
    print(d.get('settings_path', ''))
except Exception as e:
    sys.exit(1)
") || return 1
  VAULT=$(echo "$out" | sed -n '1p')
  LANG_CODE=$(echo "$out" | sed -n '2p')
  SETTINGS=$(echo "$out" | sed -n '3p')
  # settings 缺则用 default
  [[ -z "$SETTINGS" ]] && SETTINGS="$HOME/.claude/settings.json"
  return 0
}
```

字段名以现有 `scripts/cortex_config.py` 写入格式为准 (须读 cortex_config.py 确认 key)。

### 3. `detect_existing_cron()` 新函数

```bash
# 返 0 = 已有 cortex job (跳过装), 1 = 无 (走原流程)
detect_existing_cron() {
  # macOS launchd
  if command -v launchctl >/dev/null 2>&1; then
    if launchctl list 2>/dev/null | grep -qE '\bdev\.cortex\.|cortex\.'; then
      log_info "检测到 launchd 已注册 cortex job, 跳过 cron 装"
      return 0
    fi
  fi
  # crontab
  if command -v crontab >/dev/null 2>&1; then
    if crontab -l 2>/dev/null | grep -qE '~/.cortex/scripts/(lint|fold|dashboard)\.sh|cortex/scripts/cron/(lint|fold|dashboard)\.sh'; then
      log_info "检测到 crontab 已含 cortex job, 跳过 cron 装"
      return 0
    fi
  fi
  return 1
}
```

### 4. `prune_stale_cron()` 新函数

仅处理 crontab (launchd plist 改动重启风险大,留用户手动)。

```bash
# 删 crontab 中引用不存在脚本的行, 写回新 crontab
prune_stale_cron() {
  command -v crontab >/dev/null 2>&1 || return 0
  local current new
  current=$(crontab -l 2>/dev/null) || return 0
  [[ -z "$current" ]] && return 0
  new=$(echo "$current" | awk '
    /cortex\/scripts\/cron\// {
      # 提取 .sh 路径段
      match($0, /[^ ]*cortex\/scripts\/cron\/[a-z]+\.sh/)
      if (RSTART > 0) {
        path = substr($0, RSTART, RLENGTH)
        # gsub home expansion
        gsub("~", ENVIRON["HOME"], path)
        cmd = "test -f " path
        if (system(cmd) != 0) { next }  # 失效跳行
      }
    }
    { print }
  ')
  if [[ "$current" != "$new" ]]; then
    log_warn "prune crontab 失效 cortex job"
    echo "$new" | crontab -
  fi
}
```

### 5. cron 询问段重构 (line 384-399)

当前:
```bash
do_cron=0
if [[ "$NO_CRON" != "1" && "$NON_INTERACTIVE" != "1" ]]; then
  if prompt_yes_no "现在通过 wrapper 安装 cron snippet?" "n"; then
    do_cron=1
  fi
fi
```

改后:
```bash
do_cron=0
if [[ "$NO_CRON" != "1" ]]; then
  prune_stale_cron
  if detect_existing_cron; then
    log_info "已有 cortex 周期任务, 跳过 (--reinstall 强制重装)"
    [[ "$REINSTALL" == "1" ]] && do_cron=1
  elif [[ "$NON_INTERACTIVE" != "1" ]]; then
    prompt_yes_no "现在通过 wrapper 安装 cron snippet?" "n" && do_cron=1
  fi
fi
```

## 验收标准

1. **场景 1 — config 已存在选不覆盖**:
   ```
   ✓ ~/.cortex/config.json 已存在, 覆盖? [y/N]:
   < 用户输 n >
   ✓ 复用现有 config: vault=... lang=... settings=...
   ```
   **不再问** vault/lang/settings (除非用户输 y)
2. **场景 2 — config 已存在选覆盖**:
   ```
   ✓ ~/.cortex/config.json 已存在, 覆盖? [y/N]:
   < y >
   ✓ vault 路径 [...]:
   ... 原 prompt 流程
   ```
3. **场景 3 — config 不存在**:
   直接走原 prompt 流程,不问覆盖
4. **场景 4 — cron 已注册**:
   `crontab -l` 含 `~/.cortex/scripts/cron/lint.sh` → install.sh log "已有 cortex 周期任务, 跳过",**不**询问
5. **场景 5 — cron 含失效项**:
   crontab 含 `~/.cortex/scripts/cron/nonexist.sh` → install.sh log "prune crontab 失效 cortex job" → 该行被删
6. **场景 6 — `--reinstall`**:
   即使 cron 已注册也重新打印 snippet (do_cron=1)
7. `bash -n install.sh` 语法绿
8. 不回归:`bash plugins/tools/cortex/tests/run.sh` 全绿

## 不变量

- 纯 bash + python3 (已是依赖), 不引新工具
- `~/.cortex/config.json` 字段读写格式与 `scripts/cortex_config.py` 对齐
- launchd plist 不自动 prune (重启风险), 仅 crontab 处理
- `--non-interactive` 模式: config 已存在则自动复用 (除非 `--reinstall`), cron 已存在跳过
- `prompt_yes_no` / `prompt_value` / `log_*` 函数复用,不重写

## 风险

- **config.json 字段名漂移**: `cortex_config.py` 用 `vault_path` 还是 `vault`? **缓解**: implement 先读 `scripts/cortex_config.py` 实际 key 对齐
- **crontab awk gsub `~` 在 mawk vs gawk 行为差异**: macOS 默认 BSD awk, 用 ENVIRON["HOME"] 兼容
- **launchctl list 在 macOS 14+ 受限**: 非 root 可能看不全 system domain。**缓解**: 接受 false negative, 用户手动跑 install_cron.sh launchd 再确认
- **prune 误删用户手写 cortex 相关 cron**: 正则锚定 `cortex/scripts/cron/` 路径, 不删用户自定义任务
