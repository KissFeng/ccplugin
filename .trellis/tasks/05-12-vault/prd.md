# PRD — vault 强制对齐 (任意偏差强制覆盖)

## 背景

User 明确: **不是迁移老 vault, 也不是兼容**, 而是 vault 因任意原因 (人为/意外/编辑/同步漂移) 偏离 plugin 预期结构时, **强制对齐**。

现有部分对齐机制 (3 规则, autofix=true):
- `structure-missing` — 缺目录补
- `seed-missing` — 缺 seed 文件补 (skip 已存在)
- `meta-missing` — 缺 _meta 文件补 (skip 已存在)

漏: 文件**存在但被改过** (内容偏离 plugin 源) — 无强制覆盖。

## 目标

加规则 `vault-misaligned` (autofix=true), 检测 + 强制覆盖:
- vault 内 plugin-managed 文件 (seed_files 列出 + `_meta/*` 模板) 内容 sha 与 plugin 源不一致 → 覆盖 (复用 TEMPLATE_END 拼接策略保留用户尾段)
- 已 backup 到 backup_dir

类似 `template-outdated` / `seed-outdated`, 但语义升级:
- `template-outdated`: 版本号迁移 (template_version 比对) — 仅在 plugin 升级时触发
- `seed-outdated`: 同上
- **新 `vault-misaligned`**: sha 比对, **任何偏差** 都强制 (即使版本号相同, 用户改过也覆盖)

## 设计

### 1. 新规则 `vault-misaligned`

`lint/run.py` 加:

```python
def _check_vault_misaligned(vault, plugin_root) -> list[dict]:
    """对比 vault 内 plugin-managed 文件 vs plugin 源, sha 不一致即报."""
    findings = []
    # 来源: _structure.json seed_files + 固定 _meta 文件
    # 复用现有 _load_manifest / template-manifest / presets-manifest
    
    # 1. seed 文件 (从 _structure.json seed_files 解析)
    sf = plugin_root / "presets" / "_structure.json"
    if sf.exists():
        d = json.loads(sf.read_text())
        for s in d.get("seed_files", []):
            dst_key = s.get("dst_key", ".")
            name = s.get("name")
            rel = name if dst_key == "." else f"{dst_key}/{name}"
            src = plugin_root / "presets" / s["src"]
            dst = vault / rel
            if not (src.exists() and dst.exists()):
                continue  # seed-missing 处理缺失
            # 跑 TEMPLATE_END 拼接对比 (保留用户尾段)
            if _sha256_normalized_part(src, "head") != _sha256_normalized_part(dst, "head"):
                findings.append(_f(
                    "vault-misaligned", "warn", rel, 1,
                    f"vault 文件 {rel} 头部 (TEMPLATE_END 之前) 与 plugin 源不一致",
                    True,
                ))
    
    # 2. _meta 文件 (memory-policy.yaml / triggers.yaml / template-manifest.json / frontmatter-schema.yaml)
    meta_pairs = [
        ("_meta/memory-policy.yaml", plugin_root / "presets/seed/_meta/memory-policy.yaml"),
        ("_meta/triggers.yaml", plugin_root / "templates/triggers.yaml"),
        ("_meta/frontmatter-schema.yaml", plugin_root / "templates/frontmatter-schema.yaml"),
    ]
    for rel, src in meta_pairs:
        dst = vault / rel
        if not (src.exists() and dst.exists()):
            continue
        if _sha256_normalized(src) != _sha256_normalized(dst):
            findings.append(_f(
                "vault-misaligned", "warn", rel, 1,
                f"vault _meta 文件 {rel} 与 plugin 源不一致 (强制对齐覆盖)",
                True,
            ))
    
    # 3. _templates/* (复用 template-outdated 已查, 但补 vault 改过的检测)
    tpl_dir = plugin_root / "templates"
    for src in tpl_dir.rglob("*"):
        if not src.is_file():
            continue
        if src.name == "_manifest.json":
            continue
        rel_tpl = src.relative_to(tpl_dir)
        dst = vault / "_templates" / rel_tpl
        if not dst.is_file():
            continue
        if _sha256_normalized(src) != _sha256_normalized(dst):
            findings.append(_f(
                "vault-misaligned", "warn", f"_templates/{rel_tpl}", 1,
                f"vault _templates/{rel_tpl} 与 plugin 源不一致",
                True,
            ))
    
    return findings

def _sha256_normalized_part(p, part="head"):
    """sha for TEMPLATE_END 之前 (head) 或之后 (tail) 部分."""
    txt = p.read_bytes().replace(b'\r\n', b'\n')
    MARKER = b"<!-- TEMPLATE_END -->"
    if MARKER not in txt:
        return hashlib.sha256(txt).hexdigest()
    head, _, tail = txt.partition(MARKER)
    if part == "head":
        return hashlib.sha256(head + MARKER).hexdigest()
    return hashlib.sha256(tail).hexdigest()

def _fix_vault_misaligned(finding, vault, plugin_root, backup_dir) -> bool:
    """强制对齐: 用 TEMPLATE_END 拼接保留用户尾段, 头部覆盖."""
    rel = finding["file"]
    dst = vault / rel
    if not dst.is_file():
        return False

    # 反查 plugin 源
    src = _resolve_plugin_source(rel, plugin_root)
    if not src or not src.exists():
        return False
    
    # backup
    bak = backup_dir / rel
    bak.parent.mkdir(parents=True, exist_ok=True)
    bak.write_bytes(dst.read_bytes())
    
    # TEMPLATE_END 拼接 (复用现有 _fix_seed_outdated 逻辑)
    MARKER = "<!-- TEMPLATE_END -->"
    src_text = src.read_text()
    dst_text = dst.read_text()
    if MARKER in src_text:
        src_head = src_text.split(MARKER, 1)[0] + MARKER
    else:
        src_head = src_text
    if MARKER in dst_text:
        dst_tail = dst_text.split(MARKER, 1)[1]
    else:
        dst_tail = ""
    dst.write_text(src_head + dst_tail)
    return True


def _resolve_plugin_source(rel, plugin_root):
    """vault rel path → plugin 源路径反查."""
    # _meta/<f> → presets/seed/_meta/<f> 或 templates/<f>
    if rel.startswith("_meta/"):
        name = rel[len("_meta/"):]
        for cand in [plugin_root / "presets/seed/_meta" / name,
                     plugin_root / "templates" / name]:
            if cand.exists():
                return cand
    if rel.startswith("_templates/"):
        return plugin_root / "templates" / rel[len("_templates/"):]
    # seed_files 反查
    sf = plugin_root / "presets" / "_structure.json"
    if sf.exists():
        d = json.loads(sf.read_text())
        for s in d.get("seed_files", []):
            dst_key = s.get("dst_key", ".")
            name = s.get("name")
            cand_rel = name if dst_key == "." else f"{dst_key}/{name}"
            if cand_rel == rel:
                return plugin_root / "presets" / s["src"]
    return None
```

接入主流程 + FIX_MAP。priority=4 (在 structure/meta/seed 之后, 因这些缺失先补)。

### 2. lint --align 旗 (可选别名)

`lint --align` 等同 `lint --fix --rules vault-misaligned,structure-missing,seed-missing,meta-missing,template-outdated,seed-outdated`。便捷一键。

cron wrapper `lint.sh --sync-templates` 现有可扩展 `--align` (相同效果)。

### 3. install SKILL 提示

`cortex-install` SKILL 流程末尾加: "lint --align 可随时强制对齐 vault 到 plugin 当前结构 (备份后覆盖)"。

### 4. 测试

`tests/python/test_lint_vault_misaligned.py`:
- mock vault 已含 seed 文件 + 用户改了头部内容
- 跑 lint --fix vault-misaligned
- 验证: 头部恢复 plugin 源, TEMPLATE_END 后用户内容保留
- 备份到 backup_dir 含原 vault 内容

## 验收

- [ ] lint 加 `vault-misaligned` 规则 (autofix=true)
- [ ] mock vault: 改 _meta/memory-policy.yaml → lint 检出 → --fix 覆盖
- [ ] mock vault: 改 seed 文件头部 → --fix 头部恢复, 尾部 (TEMPLATE_END 后) 保留
- [ ] mock vault: 改 _templates/html/badge.html → --fix 覆盖
- [ ] backup 完整
- [ ] 264 + 新测试 PASS

## 风险

| 风险 | 缓解 |
|------|------|
| 强制覆盖用户头部修改 | TEMPLATE_END 拼接保留尾部; backup 完整 |
| seed 无 TEMPLATE_END (老文件) | 全文覆盖 (backup 保留原始) |
| 高频跑大量 sha 计算 | 复用 _sha256_normalized cache 简单实现, 单次跑无大开销 |
| 用户故意改 _meta 自定义 | 暂不区分 — 用户应通过 vault _meta 加新文件 (不冲突), 不该改 plugin-managed 内容 |

## 子任务
单 trellis-implement 串行。
