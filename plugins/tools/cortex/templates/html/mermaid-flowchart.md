<!-- cortex-template-version: 1 -->
<!--
  mermaid-flowchart.md — flowchart 模板
  变量占位:
    {{TITLE}}  图标题 (markdown H2 上方)
    {{NODES}}  节点定义 (由 cortex-html 注入, 形如 A[开始] --> B{判断})
---
template_version: 1
---

-->

## {{TITLE}}

```mermaid
flowchart TD
    {{NODES}}
    %% 示例:
    %% Start([开始]) --> Check{条件?}
    %% Check -->|是| DoA[操作 A]
    %% Check -->|否| DoB[操作 B]
    %% DoA --> End([结束])
    %% DoB --> End
```

<!-- TEMPLATE_END -->
