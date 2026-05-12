<!-- cortex-template-version: 1 -->
<!--
  mermaid-mindmap.md — 思维导图
  变量占位:
    {{ROOT}}    根节点文本
    {{BRANCHES}} 分支节点 (缩进表示层级)
-->

---
template_version: 1
---

## {{TITLE}}

```mermaid
mindmap
  root(({{ROOT}}))
    {{BRANCHES}}
    %% 示例:
    %% 知识库
    %%   项目
    %%   来源
    %%     代码仓库
    %%     网页
    %% 记忆体系
    %%   L0-核心
    %%   L1-长期
```

<!-- TEMPLATE_END -->
