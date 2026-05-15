# cortex-dashboard — 数据源查询 (8 kind)

`view_query.kind` 8 枚举: `memory / knowledge / ledger / cron / bridge / distribution / promotion / warden`。每 kind 真实 Bash 查, 严禁占位。`VAULT` 为 vault 根绝对路径。

## kind=memory

`view_query.level` 必须 (L0-L4)。

```bash
# 总数
total=$(find "$VAULT/记忆/<level>-"* -name "*.md" -type f 2>/dev/null | wc -l | tr -d ' ')
# 本周新增 (mtime<7d)
weekly=$(find "$VAULT/记忆/<level>-"* -name "*.md" -type f -mtime -7 2>/dev/null | wc -l | tr -d ' ')
# 过期 (mtime>30d)
stale=$(find "$VAULT/记忆/<level>-"* -name "*.md" -type f -mtime +30 2>/dev/null | wc -l | tr -d ' ')
# Top-N by weight: 复用 memory.sh recall
bash ~/.cortex/scripts/memory.sh recall --query "" --levels <level> --top-k 10 --format json
```

路径 `$VAULT/记忆/<level>-*` 不存在 → error, 跳过该 dashboard。

## kind=knowledge

```bash
total=$(find "$VAULT/知识库" -name "*.md" -type f 2>/dev/null | wc -l | tr -d ' ')
# Top-N 复用 search.sh:
bash ~/.cortex/scripts/search.sh --query "" --scope knowledge --top-k 10 --format json
```

## kind=ledger

`view_query.level` 通常 L4。

```bash
# L4 sessions 总数 (jsonl 行数和)
total=$(find "$VAULT/记忆/L4-流水账/sessions" -name "*.jsonl" 2>/dev/null -exec wc -l {} + | tail -1 | awk '{print $1}')
# 30d 内 sessions:
recent=$(find "$VAULT/记忆/L4-流水账/sessions" -name "*.jsonl" -mtime -30 2>/dev/null | wc -l | tr -d ' ')
# 按日聚合 (heatmap 数据):
find "$VAULT/记忆/L4-流水账/sessions" -name "*.jsonl" -mtime -30 2>/dev/null -printf "%TY-%Tm-%Td\n" | sort | uniq -c
```

## kind=cron

```bash
# 9 job 状态:
for f in ~/.cache/cortex/cron/*.json; do
  [ -f "$f" ] && jq -r '"\(.job)|\(.last_run)|\(.duration_sec)|\(.exit_code)"' "$f"
done
# 成功 24h 内:
ok=$(for f in ~/.cache/cortex/cron/*.json; do
  jq -r 'select(.exit_code==0) | .last_run' "$f" 2>/dev/null
done | wc -l | tr -d ' ')
```

`~/.cache/cortex/cron/` 不存在 → error。

## kind=bridge

```bash
# 记忆→知识库 ref:
m2k=$(rg "^ref:" "$VAULT/记忆" --no-heading -c 2>/dev/null | wc -l | tr -d ' ')
# 知识库→记忆 ref:
k2m=$(rg "^ref:" "$VAULT/知识库" --no-heading -c 2>/dev/null | wc -l | tr -d ' ')
# 双向 (jq aggregate):
rg "^ref:" "$VAULT/记忆" "$VAULT/知识库" --json 2>/dev/null | \
  jq -s 'group_by(.data.path.text) | map({path:.[0].data.path.text, refs:length})'
```

## kind=distribution

```bash
# 各领域计数:
for d in "$VAULT"/知识库/领域/*/; do
  name=$(basename "$d")
  cnt=$(find "$d" -name "*.md" -type f | wc -l | tr -d ' ')
  echo "$name:$cnt"
done
# 月增量:
for d in "$VAULT"/知识库/领域/*/; do
  name=$(basename "$d")
  cnt=$(find "$d" -name "*.md" -type f -mtime -30 | wc -l | tr -d ' ')
  echo "$name:$cnt"
done
```

## kind=promotion

```bash
PROM="$VAULT/记忆/views/promotion.jsonl"
[ -f "$PROM" ] || exit_error  # 该 dashboard 报 error, 不写 DASH
# 流量聚合 (from_level → to_level):
jq -s 'group_by(.from_level + "→" + .to_level) | map({pair:.[0].from_level+"→"+.[0].to_level, n:length})' "$PROM"
# 候选总数 (candidates.md):
[ -f "$VAULT/记忆/views/candidates.md" ] && grep -c "^|" "$VAULT/记忆/views/candidates.md"
```

## kind=warden

```bash
WARDEN="$VAULT/记忆/views/warden.jsonl"
[ -f "$WARDEN" ] || exit_error  # 该 dashboard 报 error, 不写 DASH
# 待审条目:
pending=$(jq -s '[.[] | select(.status=="pending")] | length' "$WARDEN")
# kind 分布 (hallucination / drift):
jq -s 'group_by(.kind) | map({kind:.[0].kind, n:length})' "$WARDEN"
```
