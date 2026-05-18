# cortex-image — 排版/构图库

6 排版, 每条含: **用途 / prompt 模板 / 推荐风格组合 / 注意事项**。

排版关键词作为 final_prompt `<composition>` 段塞入。**画面级排版** ≠ HTML 排版 — 这里指模型能听懂的"主体如何放在画布上"。

## 1. single (单图主体)

- **用途**: 默认; 1 个主体居中或黄金分割位
- **prompt 模板**: `single subject centered, rule of thirds, clean background, ample negative space`
- **推荐风格**: 任意 (photo-realistic / studio-ghibli / cyberpunk 最稳)
- **注意**: 模型对"single subject"理解最好; 多主体易畸变

## 2. comparison (对比 / before-after)

- **用途**: 左右对比 / 状态演化 / before-after
- **prompt 模板**: `split composition, left side shows <A>, right side shows <B>, clear vertical divider in the middle, same lighting both sides`
- **推荐风格**: minimal-flat · isometric · line-art (易控制对称)
- **注意**: dall-e-3 对"split"理解一般; stability sdxl + sd-comfyui + regional prompter 更稳。生成失败可改成两张图各跑一次再 HTML 拼。

## 3. grid-2x2 (网格)

- **用途**: 4 个相关元素 / 4 视角 / 4 阶段
- **prompt 模板**: `2x2 grid layout, four panels showing <A>/<B>/<C>/<D>, equal cell size, thin white gutter between cells, consistent style across all four`
- **推荐风格**: pixel-art · minimal-flat · isometric · line-art
- **注意**: 高失败率, 模型常画成 1 张图四角放小图。dall-e-3 几乎不行, 走 SD/Comfy 更稳。备选: 跑 4 次 single 再拼。

## 4. timeline-horizontal (时间线 / 流程)

- **用途**: 流程 / 演化 / 时间线
- **prompt 模板**: `horizontal timeline composition, three stages from left to right, connected by an arrow, equal vertical alignment, <stage1> → <stage2> → <stage3>`
- **推荐风格**: minimal-flat · isometric · line-art
- **注意**: 文字渲染不可靠 — 关键词标签贴入后期 HTML 叠加, 不要指望模型把字写对。

## 5. info-card (信息卡)

- **用途**: 标题 + 主图 + 短描述 (卡片视觉)
- **prompt 模板**: `card layout, large title area at top, central illustration in the middle, short caption space below, rounded corners, soft shadow, white background`
- **推荐风格**: minimal-flat · watercolor · isometric
- **注意**: 文字依然交给 HTML 后期叠加 (用 _templates/html/card.html), 模型只画卡片结构 + 中央插图。

## 6. hero-banner (主视觉横幅)

- **用途**: 文章顶部主视觉 / 封面横幅
- **prompt 模板**: `wide cinematic banner 16:9, dramatic subject placement off-center (rule of thirds), atmospheric background fading to side, room for overlay text on the left third`
- **推荐风格**: cyberpunk · photo-realistic · studio-ghibli · watercolor
- **注意**: 用 `--size 1792x1024` (dall-e-3) 或 `1344x768` (SDXL); 自带"left third 留白"指引文字叠加位置。

---

## 选择启发式

| 用途 | 推荐排版 | 推荐风格组合 |
|---|---|---|
| 文章主视觉 / 封面 | hero-banner | cyberpunk + 16:9 / studio-ghibli + 16:9 |
| 单概念示意 | single | minimal-flat / isometric |
| A vs B 对比 | comparison | minimal-flat (跑成功率高) |
| 4 阶段/4 视角 | grid-2x2 (失败时降级 4× single) | pixel-art / isometric |
| 流程演化 | timeline-horizontal | minimal-flat / line-art |
| 笔记内嵌图卡 | info-card | watercolor / minimal-flat |

## 失败降级策略

1. **复杂排版 (grid/comparison/timeline) 失败率高** → 降级为多张 single, 后期用 HTML 拼接 (借 `_templates/html/card.html` / 自写 CSS grid)
2. **文字渲染** → 不要指望模型, 一律 HTML overlay
3. **多主体一致性** → 同一 provider 同一 seed 跑多次, 或用 SD + IPAdapter (本 skill 不覆盖, 文档级提示)
