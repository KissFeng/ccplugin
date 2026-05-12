# PRD — session_start 注入压缩

## 背景

当前 SessionStart hook 注入 1.7KB+ (干净 vault), 真实 vault 含 hot.md (5KB cap) + L0 (5KB cap) → 可达 12KB (~4K tokens)。挤压模型输出空间, 小上下文模型 (4-8K) 难用。

## 目标

总注入 hard cap **3KB** (~1K tokens), 干净 vault < 800 chars。

各段 cap:
| 段 | 当前 | 新 cap |
|----|------|--------|
| header | 100 B | 100 B (保) |
| stats | 200 B | 200 B (保) |
| L0 core | 5 KB | 1.5 KB (per-file 500B, total 1.5KB) |
| hot.md | 5 KB | 1 KB |
| behavior_contract | 700 B | 200 B |
| triggers | 350 B | 100 B (移引用 _meta/triggers.yaml) |
| collab | 500 B | 200 B |
| **总** | **~12 KB max** | **~3 KB max** |

### 不在范围
- 不动 hook 触发机制
- 不动 SKILL 内容
- 不动 memory-policy / 模板 / wrapper

## 设计

### 1. behavior_contract 极简版

3 locales (zh-CN/en/ja):
```yaml
behavior_contract: |
  ### ⚖️ 行为契约
  回答前必调: cortex_memory_recall + cortex_search。
  weight ≥0.7 必采; 0.4-0.7 标注; <0.4 可参考。
  用户说"记住" → cortex_memory_write L1; "永远" → L0 候选; "暂时" → L2;
  "忘了" → cortex_memory_forget。
  写后回 "✓ 已记 L<N>: <brief>"。
```

200 chars / 70 tokens。

### 2. default_triggers 一行

```yaml
default_triggers: "记住/忘了/remember/forget/偏好/项目/Go/Python/MySQL/React/金融/旅游/美食"
```

80 chars。详细分类移到 `_meta/triggers.yaml` (用户 vault 内)。

session_start 加注: `详细触发词: _meta/triggers.yaml`。

### 3. 协作约定 一行

```yaml
collab_compact: |
  落档: cortex-save (项目→domains/, 概念→concepts/); 
  写文件: L1 obsidian CLI → L2 mcp → L3 直写 (需授权); 
  自动加 ^cortex-<sha8>; Stop hook 归档技术发现。
```

180 chars。删原 4 长条 (L1/L2/L3 解释段已过细)。

### 4. L0 cap 缩

`load_l0_core`:
- per-file cap 1500 → 500 chars
- total cap 5000 → 1500 chars
- 仅取 brief 段, 跳过 full

### 5. hot cap 缩

`MAX_BYTES = 5000 → 1000`。用户 hot.md 应自维护精简。

### 6. 总 cap 缩

`if len(context.encode("utf-8")) > 15000 → 3000`。

### 7. 库存快照 (保留, 200B 内)

不变。

## 实施

单文件 + 3 locales:
1. `hooks/session_start.sh`:
   - `MAX_BYTES = 1000` (hot)
   - `load_l0_core(vault, cap_per_file=500, total_cap=1500)`
   - 末尾总 cap `15000 → 3000`
2. `locales/{zh-CN,en,ja}.yml`:
   - `behavior_contract` 极简版
   - `default_triggers` 一行
   - 新 key `collab_compact` (替 4 条 collab_*)
3. `hooks/session_start.sh` 拼装段:
   - 用 `collab_compact` 单条替原 4 条循环

## 验收

- [ ] 干净 vault 注入 ≤ 800 chars
- [ ] L0 含 5 文件 + hot 5KB 满载, 注入 ≤ 3000 chars
- [ ] behavior_contract 仍含 cortex_memory_recall / "记住" / weight 关键词
- [ ] triggers 仍含核心关键词 (记住/forget/Go/Python 等)
- [ ] 协作约定保留 cortex-save / 锚点 关键提示
- [ ] 235 python tests 不回归
- [ ] session_start 单测调整 cap 期望

## 风险

| 风险 | 缓解 |
|------|------|
| AI 失去详细规则 → 不照做 | 关键命令保留 (cortex_memory_recall/write/forget), 详细规则用户可问 SKILL |
| triggers 漏触发 | 用户可改 _meta/triggers.yaml 自定义 |
| L0 内容截断 | per-file cap 500 含 brief 段 + 提示读完整: `详细: cortex_memory_read("L0://...")` |

## 子任务

单 wave 单 agent 串行 (文件少 + 逻辑紧密)。
