# cortex-image — 风格库

10 风格, 每条含: **关键词 / 适用场景 / prompt 模板 / 反风格词 / 示例描述**。

风格关键词作为 final_prompt `<style>` 段塞入。

## 1. photo-realistic (写实摄影)

- **关键词**: photographic, realistic photography, DSLR, sharp focus
- **适用**: 产品图 / 人像 / 新闻类图片 / 物体写实记录
- **prompt 模板**: `<subject>, photorealistic, shot on 35mm, natural lighting, shallow depth of field`
- **反风格词**: cartoon, illustration, painting, anime, low-poly
- **示例描述**: 一只猫坐在窗台, 自然光, 浅景深, 真实毛发质感

## 2. anime (二次元)

- **关键词**: anime style, cel shading, vibrant colors, soft outline
- **适用**: 角色 / 概念插画 / 漫画封面
- **prompt 模板**: `<subject>, anime illustration, cel-shaded, expressive lineart, vibrant palette`
- **反风格词**: 3d render, photorealistic, gritty, low contrast
- **示例描述**: 少年站在天台逆光, cel shading 二段阴影, 风吹动衣摆

## 3. cyberpunk (赛博朋克)

- **关键词**: cyberpunk illustration, neon accents, high contrast, futuristic
- **适用**: 科技主题 / 未来场景 / 终端/代码主视觉
- **prompt 模板**: `<subject>, cyberpunk, neon magenta/cyan accents, rain-soaked street, low-key lighting`
- **反风格词**: pastel, daylight, vintage, sepia
- **示例描述**: 程序员在霓虹反射的窗前, 紫青配色, 雨夜

## 4. minimal-flat (极简扁平)

- **关键词**: minimal flat design, geometric shapes, limited palette
- **适用**: 信息图 / 概念图标 / 海报
- **prompt 模板**: `<subject>, minimal flat illustration, 3-color palette, geometric, no gradient, no shadow`
- **反风格词**: realistic, textured, gradient, complex detail
- **示例描述**: 三色平面化的笔记本 + 笔, 几何块面, 无渐变

## 5. watercolor (水彩)

- **关键词**: watercolor painting, soft edges, paper texture, gentle washes
- **适用**: 怀旧 / 日记封面 / 自然主题 / 温柔氛围
- **prompt 模板**: `<subject>, watercolor on cold-press paper, soft wash, gentle edges, muted palette`
- **反风格词**: sharp outline, digital, neon, glossy
- **示例描述**: 山间小屋, 浅蓝灰湿染, 纸纹可见

## 6. ink-wash (中国水墨)

- **关键词**: Chinese ink wash painting, sumi-e, monochrome, brushstroke
- **适用**: 东方主题 / 哲思 / 极简意境
- **prompt 模板**: `<subject>, traditional Chinese ink wash, monochrome black on rice paper, expressive brushstrokes, negative space`
- **反风格词**: color, photorealistic, busy, 3d
- **示例描述**: 远山一笔, 近石数点, 大片留白

## 7. pixel-art (像素风)

- **关键词**: pixel art, 16-bit / 32-bit, limited palette, dithering
- **适用**: 游戏图标 / 怀旧 / 程序员主题
- **prompt 模板**: `<subject>, 32x32 pixel art, 16-color palette, crisp pixels, retro game vibe`
- **反风格词**: smooth, anti-aliased, high resolution, blurred
- **示例描述**: 像素化的猫咪精灵, 16 色, 1990s 街机美术

## 8. isometric (等距投影)

- **关键词**: isometric illustration, 30-degree projection, axonometric
- **适用**: 科技产品 / 架构图 / 系统/办公场景
- **prompt 模板**: `<subject>, isometric illustration, 30-degree projection, soft shadows, clean vector lines`
- **反风格词**: perspective, fisheye, photographic, gritty
- **示例描述**: 等距投影的办公桌 + 显示器 + 键盘, 干净矢量线

## 9. line-art (线稿)

- **关键词**: line art, single-weight ink lines, no fill, minimal
- **适用**: 概念图 / 教学示意 / 装饰元素
- **prompt 模板**: `<subject>, clean line art, single-weight black ink on white, no shading, no color`
- **反风格词**: color, shaded, painterly, photographic
- **示例描述**: 单线条的咖啡杯轮廓, 无填色

## 10. studio-ghibli (吉卜力风)

- **关键词**: Studio Ghibli inspired, hand-painted, lush nature, soft palette
- **适用**: 治愈 / 自然 / 童年回忆 / 故事开篇插图
- **prompt 模板**: `<subject>, Studio Ghibli inspired hand-painted illustration, lush foreground, warm soft palette, painterly clouds`
- **反风格词**: photographic, dark, gritty, low detail
- **示例描述**: 田野上奔跑的少女, 云朵厚涂, 温柔黄昏光

---

## 选择启发式

| 用户主题词 | 推荐风格 |
|---|---|
| 程序员 / 代码 / 终端 / 黑客 | cyberpunk · isometric · pixel-art |
| 自然 / 治愈 / 童年 / 旅行 | watercolor · studio-ghibli · photo-realistic |
| 产品图 / 真实物体 / 食物 | photo-realistic |
| 概念图 / 系统架构 / 信息图 | minimal-flat · isometric · line-art |
| 角色 / 漫画 / 二次元 | anime · studio-ghibli |
| 东方 / 极简意境 / 茶/书法 | ink-wash · minimal-flat |
| 怀旧 / 游戏 / 复古 | pixel-art · watercolor |
