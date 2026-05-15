# cortex-refactor — split / extract / inline / graph-rebalance

> SKILL.md 入口的"拆分类"子操作详细行为。

## split — 一页按 H2 拆多页

```bash
python3 ~/.claude/plugins/marketplaces/ccplugin-market/plugins/tools/cortex/scripts/refactor/split.py \
  --vault <path> --from <src> [--out-dir <dir>] [--apply]
```

- 每个 H2 节生成一个新页 `<src-stem>--<slug>.md`
- 原页保留, 末尾追加 `> [!info] split into:` callout 列出子页
- 重名不覆盖 (跳过)

## extract — 抽 H2 节为独立 concept 页

```bash
python3 ~/.claude/plugins/marketplaces/ccplugin-market/plugins/tools/cortex/scripts/refactor/extract_inline.py \
  --vault <path> --page <rel> --section "<H2 title>" --direction extract \
  [--out-path <rel>] [--apply]
```

- 抽 H2 节为独立 concept 页
- 父页留 `![[child-stem]]` transclusion

## inline — 子页内联回父页

```bash
python3 ~/.claude/plugins/marketplaces/ccplugin-market/plugins/tools/cortex/scripts/refactor/extract_inline.py \
  --vault <path> --page <parent> --child <child> --direction inline \
  [--section <H2>] [--apply]
```

- 子页内联回父页 (指定 H2 注入或末尾追加)
- 子页归档到 `归档/`
- 全 vault wikilink 同步到父页

## graph-rebalance — orphan / hub 扫描

```bash
python3 ~/.claude/plugins/marketplaces/ccplugin-market/plugins/tools/cortex/scripts/refactor/graph_rebalance.py \
  --vault <path> [--hub-threshold 20] [--scope all] [--apply]
```

- 扫 orphan (无入链页) 与 hub (出/入度过高页)
- `--apply` 仅自动补 `link_gaps` (新增 wikilink 建议); hub 拆分仅提示

## 子命令矩阵

| 子命令 | 签名 | 说明 |
|---|---|---|
| split | `--vault P --from REL [--out-dir DIR] [--apply]` | H2 拆多页, 原页留 callout |
| extract | `extract_inline.py --vault P --page REL --section H2 --direction extract [--out-path REL] [--apply]` | 抽 H2 为独立页, 父页留 transclusion |
| inline | `extract_inline.py --vault P --page REL --child REL --direction inline [--section H2] [--apply]` | 子页内联父页, 子页归档 |
| graph-rebalance | `graph_rebalance.py --vault P [--hub-threshold 20] [--scope all] [--apply]` | orphan/hub 扫, 补 link_gaps |

输出 JSON 含 `op / applied`, dry-run 字段视子命令而定 (orphans / hubs / link_gaps / candidates)。
