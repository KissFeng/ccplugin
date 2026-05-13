# cortex CLI 模块

cortex 自研 MCP server 已废弃 (Phase 2a)。原 `scripts/mcp/tools/*.py` 的业务
逻辑 (masking / frontmatter / BM25 / 子图扩展 / 记忆策略 / ledger / session
import 等) 全部保留, 改为独立 CLI 模块, 算法 100% 不变 — 只剥离 MCP 协议层。

业务通过 `~/.cortex/scripts/` 下的 bash 包装薄壳 (Phase 2c) 调用本目录 python 入口。

## 入口列表

| 文件                 | 子命令 / 说明                                                                |
| -------------------- | ---------------------------------------------------------------------------- |
| `save.py`            | 单 entry: `--kind {concept,domain,log} --title --body ...` → 落档 vault     |
| `search.py`          | 单 entry: `--query --limit --scope` → 多级回退检索 (hot/index/SC/rg)        |
| `deep_search.py`     | 单 entry: `--query --mode {iterative,subgraph,hybrid} ...`                  |
| `ingest_url.py`      | 单 entry: `--url --kind ...` → SSRF gate + fetch + extract + save           |
| `ingest_file.py`     | 单 entry: `--path --kind ...` → pdf/epub/docx/md/txt extract + save         |
| `memory.py`          | 子命令: `read / write / recall / forget / consolidate / promote`            |
| `ledger.py`          | 子命令: `append / uri_index_rebuild`                                        |
| `session.py`         | 子命令: `import`                                                            |
| `html_render.py`     | 单 entry: `--template --data '<json>'`                                      |

## 统一返回格式

所有 CLI 都把单行 JSON 打印到 stdout:

```json
{"ok": true,  "code": 0, "data": {...}}
{"ok": false, "code": <N>, "error": "<msg>"}
```

错误码:

- `0` success
- `1` 通用错误
- `2` 资源未找到
- `3` vault 未配置
- `4` 策略校验失败 (如 L0 写需 user_confirmed)
- `5` URI 格式不合法
- `6` 需用户批准 (晋级 L0/L1 等)

`search.py` / `deep_search.py` 出于历史兼容直接打印 hits 数组 / 结果对象 (无
ok/code 包裹)。

## 内部布局

```
scripts/cli/
├── lib/
│   ├── cortex_common.py    URI 解析 + 返回包装 + LEVEL_DIRS
│   ├── frontmatter.py      YAML frontmatter parse/dump
│   ├── lock.py             flock 文件锁
│   ├── vault_path.py       vault 解析 (~/.cortex/config.json)
│   ├── wikilinks.py        slug + block-id 注入
│   └── extractors/         html/pdf/docx/epub 抽取器
├── save.py, search.py, deep_search.py, ingest_url.py, ingest_file.py
├── memory.py, ledger.py, session.py, html_render.py
```

每个 entry 文件顶层都 `sys.path.insert(0, here)` 让 `from lib...` 在 `python3
scripts/cli/<name>.py` 直接调用时也能解析。
