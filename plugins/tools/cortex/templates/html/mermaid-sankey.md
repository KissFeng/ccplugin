<!-- cortex-template-version: 1 -->
<!--
  mermaid-sankey.md — 桑基图 (用于固化流 L4→L3→L2→L1→L0)
  变量占位:
    {{TITLE}}  图标题
    {{FLOWS}}  流量定义, 每行形如 `源,目标,权重`
-->

---
template_version: 1
---

## {{TITLE}}

```mermaid
sankey-beta

{{FLOWS}}
%% 示例 (L4 → L0 固化流):
%% L4-流水账,L3-情节,120
%% L3-情节,L2-语义,45
%% L2-语义,L1-长期,12
%% L1-长期,L0-核心,2
```

<!-- TEMPLATE_END -->
