---
name: cortex-image
description: 文生图 — 从 vault/.cortex/config/image-gen.yaml 多 provider 选 (随机或 --config 指定), 内置 10 风格 / 6 排版库; 自动写 frontmatter md + 落 _assets/images/。Triggers on "生成图", "做张图", "text to image", "image gen", "AI 画图", "render image", "/cortex:image".
disable-model-invocation: false
allowed-tools: Bash Read Write Edit
---

# cortex-image

把"想画的画面"变成可贴入 vault 的图片 + 同名 frontmatter md。**HTML/Mermaid 是默认表达**, 文生图只在用户**显式想要照片/插画/封面/物体渲染**时启用 — 不主动塞图替代信息表达。

## 调用优先级 (P1)

1. **优先 CLI**: `bash ~/.cortex/scripts/image_gen.sh generate "<final_prompt>" [--config <provider>] [--size <WxH>] [--style <vivid|natural>]`
   返回 `{ok, path, sidecar, provider, model, size}` JSON
2. probe 检查 provider 健康度: `bash ~/.cortex/scripts/image_gen.sh probe`
3. 列已配 provider: `bash ~/.cortex/scripts/image_gen.sh list [--all]`

## 触发场景

- 用户显式 "画 X" / "生成一张 X 图" / "做张 X 封面" / `/cortex:image <prompt>`
- 文章/笔记需要主视觉/概念图/封面图, 用户主动要求时
- 不触发: 信息表达类需求 (架构图/流程/数据) — 这些走 mermaid/HTML

## 决策树

```
1. 解析 prompt 主体     subject / scene / object 三要素先抽出
   ↓
2. 选风格              用户指定 ? 用户选 : 推断 (技术 → isometric; 怀旧 → watercolor; 默认 photo-realistic)
   见 references/styles.md (10 风格)
   ↓
3. 选排版              单图 / 对比 / 网格 / timeline / 信息卡 / hero banner
   见 references/layouts.md (6 排版)
   ↓
4. 合成 final_prompt   主体 + 风格关键词 + 排版 + 镜头 + 光照 + 色调 + 负面词
   ↓
5. (Junior Designer 模式) 先报假设 + reasoning + 占位描述给用户; 用户确认风格再实际跑 (省 token / 省 API)
   AUTO_MODE 跳此步, 直接用默认风格 photo-realistic + 16:9
   ↓
6. 调 bash ~/.cortex/scripts/image_gen.sh generate "..."
   ↓
7. 接 JSON, 验证 path 存在, 输出 wikilink `![[filename]]` + sidecar md 路径
```

## Junior Designer 工作流 (交互模式)

借鉴 huashu-design 思路: **先思考再跑 API**。

1. **报假设**: "我理解你要 X 主体, Y 场景, 推荐 Z 风格 + W 排版, 原因是 ..."
2. **给 reasoning + 占位描述**: 把 final_prompt 完整列出, 标注每段意图
3. **询问确认**: 用 AskUserQuestion (Interactive 模式; AUTO_MODE 跳此问)
4. 确认后才调 image_gen.sh

**省 token / 省 API**: 跑一次 dall-e-3 hd 约 \$0.08, 风格选错重跑就是浪费。先文本对齐再花钱。

## 反 AI slop 清单

- 禁堆 cliché: "sunset", "ultra realistic", "8k", "trending on artstation", "bokeh" — 这些是 SEO prompt 不是好 prompt
- 禁堆 modifier 长链 (>15 词非主体词); modifier 互相打架时模型自己挑, 结果不稳
- 主体必须明确: 一句话能讲清"画面里有什么", 否则模型按平均长相输出
- 反风格词 (negative prompt) 用于排除不想要的, 不要拿来"激励"模型
- 不写"masterpiece" / "best quality" — DALL-E / Stability 都不认这套 SD prompt 黑话

## final_prompt 模板

```
<subject + action>, <scene/context>, <style>, <composition/layout>,
<lens/camera>, <lighting>, <color palette>,
--negative <unwanted attributes>
```

示例 (用户: "画一只在终端前调试的赛博朋克程序员"):

```
A focused programmer debugging code in a neon-lit terminal,
sitting in a small studio at night,
cyberpunk illustration with high-contrast neon accents,
single subject centered, medium shot,
35mm cinematic angle, low-key lighting with magenta/cyan rim light,
purple + teal palette,
--negative: extra fingers, blurry text on screen, generic stock photo look
```

## AUTO_MODE

- **不调** AskUserQuestion
- 默认 style: photo-realistic; 默认 size: 1024x1024 (provider 不支持时自动 fallback)
- 默认 provider: random (defaults.random_selection=true) 或 list 中第一个 active
- 失败重试: 第一次失败 → 自动 probe → 选下一个 active provider 重跑 1 次; 仍败 → 输出 stderr JSON error + exit 1
- 不询问是否落档 — 直接写 _assets/images/ + sidecar md

## 输出格式

成功:

```
✓ 图片已生成
  path: <vault>/_assets/images/2026-05-18-abc12345.png
  md:   <vault>/_assets/images/2026-05-18-abc12345.md
  provider: openai-dalle3 (model=dall-e-3, size=1024x1024)

  贴入笔记:
  ![[2026-05-18-abc12345.png]]
```

失败: 列出 stderr error JSON + 提示 `bash ~/.cortex/scripts/image_gen.sh probe` 排查。

## References

| 文件 | 内容 |
|---|---|
| [references/styles.md](references/styles.md) | 10 风格库: 名称 / 关键词 / 适用场景 / prompt 模板 / 反风格词 / 示例描述 |
| [references/layouts.md](references/layouts.md) | 6 排版/构图: 单图 / 对比 / 网格 / timeline / 信息卡 / hero banner |
| [references/providers.md](references/providers.md) | provider 类型 (OpenAI/Stability/SiliconFlow/Replicate/SD WebUI/Comfy) + endpoint 模板 + probe 策略 + 安全建议 |

## 不做

- 不真跑 API 当用户只是问"能不能" — 先报方案再确认
- 不替代 mermaid/HTML 信息表达 (架构/流程/数据可视化继续走 mermaid)
- 不 git commit (wrapper trap 自动处理)
- 不 inline base64 嵌 md (一律落盘 + wikilink)
