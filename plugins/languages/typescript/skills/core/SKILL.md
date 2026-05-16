---
name: typescript-core
description: TypeScript / JavaScript 核心开发规范，TS 6.0+ 严格模式优先，覆盖 tsconfig、Biome 2 / ESLint flat、pnpm 10 / Bun / Deno 2、Node 22-24 LTS、Vite 6 + Rolldown、Vitest 3、Zod 4。同时给出 JS-only 项目的 JSDoc + tsc --checkJs 兜底路径。Use when 新建 TS/JS 项目、配置 tsconfig、设置 linter/formatter、迁移 ESM、选型工具链，或用户提到 "TypeScript 规范"、"JS 规范"、"strict mode"、"tsconfig"、"biome"、"eslint"、"ESM"、"package manager"、"ES2025"。
user-invocable: true
---

# TypeScript / JavaScript 核心规范 (2026)

本 skill 同时覆盖 JavaScript 项目；**TypeScript 为首选**，JS-only 写法见各节末尾兜底说明。

适用范围：所有 `.ts` / `.tsx` / `.mts` / `.cts` / `.js` / `.jsx` 源码。

## 核心原则

类型安全 > 类型体操；编译期错误 > 运行期错误；显式 > 隐式。

### 必须遵守

1. **严格模式** — TS: `strict: true` + `noUncheckedIndexedAccess` + `noImplicitOverride` + `exactOptionalPropertyTypes`
2. **禁 `any`** — 用 `unknown` + 类型守卫，或 Zod 4 / Valibot 在边界验证
3. **运行时验证** — 所有外部输入 (HTTP / fs / env) 走 Zod 4 schema
4. **ESM 优先** — `"type": "module"` + TS 用 `import type` 分离类型导入
5. **`const` 优先, `let` 次之, 禁 `var`**
6. **非变异** — `.toSorted()` / `.toReversed()` / `.with()` / `structuredClone()`
7. **pnpm 10+** 或 **Bun 1.x** — 禁 npm install (除非项目历史约束)
8. **Vitest 3.x** — 替代 Jest (ESM 原生，类型测试)
9. **每文件 ≤ 500 行**，推荐 200~400

### 禁止行为

- `any`、`@ts-ignore`、`enum` (用 `as const` 对象代替)、`namespace`
- `var`、`require()` / `module.exports` (ESM only)
- 单行错误处理 (`if (err) return err`)
- 硬编码密钥 / URL
- `.eslintrc.js` (旧) → flat config 或 Biome
- `node-fetch` (Node 22+ 已内置 fetch)
- `React.FC` (隐式 children、泛型受限)
- 生产 `console.log` (用 pino 9 / `console.warn` / `console.error`)

## 版本与工具链 (2026-05)

| 项 | 推荐 | 说明 |
|----|------|------|
| TypeScript | **6.0** 稳定 | `target: ES2025`，strict 默认开 |
| TS 7.0 / tsgo | **CI type-check 可用** | Go 重写 10x；emit 未 GA；用 `@typescript/native-preview` |
| 语言 | ES2025 + ES2026 stage 3+ | 兼容 ES2024 |
| Node.js | **22 LTS / 24 Active LTS** | 原生 strip-types (22.18+)、原生 fetch、test runner |
| 运行时 | Node 22-24 / Bun 1.x / Deno 2 | 三选一 |
| 包管理 | pnpm 10 / Bun 1.x | 禁 npm 新项目 |
| Linter+Formatter | **Biome 2** 优先 / ESLint 9 flat (重 plugin 时) | Biome 2.3+ 423 规则 + 部分类型感知 |
| 测试 | Vitest 3.x | bench、type 测试、ESM 原生 |
| 构建 | Vite 6 (Rolldown) / tsdown / tsup | 库优先 tsdown |
| HTTP 框架 | Hono 4 / Fastify 5 | Express 5 (legacy) |
| 校验 | Zod 4 | Valibot / ArkType (小 bundle) |

## tsconfig.json 推荐基线 (TS 项目)

```json
{
  "compilerOptions": {
    "target": "ES2025",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "lib": ["ES2025"],

    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "noFallthroughCasesInSwitch": true,
    "exactOptionalPropertyTypes": true,

    "verbatimModuleSyntax": true,
    "isolatedModules": true,
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "skipLibCheck": true,

    "declaration": true,
    "sourceMap": true,
    "outDir": "./dist"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

## ES2025 / ES2026 关键特性 (TS 与 JS 通用)

```ts
// ES2025 - Iterator helpers
const evens = arr.values().filter(x => x % 2 === 0).take(10).toArray();

// ES2025 - Set methods
const u = a.union(b); const i = a.intersection(b); const d = a.difference(b);

// ES2025 - Object.groupBy / Map.groupBy
const byRole = Object.groupBy(users, u => u.role);

// ES2025 - Promise.try (同步异常进 Promise 链)
const p = Promise.try(() => mayThrowSync());

// ES2024 - Promise.withResolvers
const { promise, resolve, reject } = Promise.withResolvers();

// ES2025 - Array.fromAsync
const items = await Array.fromAsync(asyncIterable);

// ES2025 - RegExp /v flag
const re = /[\p{Emoji}--\p{ASCII}]/v;

// ES2026 stage 3 - using / await using
{
  using file = openFile('data.txt');
  await using db = await connectDB();
}

// Temporal (stage 3) - 替代 Date / moment
const now = Temporal.Now.zonedDateTimeISO();
```

## Biome 2 配置 (推荐新项目，TS / JS 通用)

```jsonc
// biome.json
{
  "$schema": "https://biomejs.dev/schemas/2.3.0/schema.json",
  "linter": {
    "enabled": true,
    "rules": {
      "recommended": true,
      "style": { "noVar": "error", "useConst": "error" },
      "suspicious": { "noConsole": "warn" }
    }
  },
  "formatter": { "enabled": true, "indentStyle": "space", "indentWidth": 2, "lineWidth": 100 },
  "javascript": { "formatter": { "quoteStyle": "double", "semicolons": "always" } }
}
```

```bash
pnpm dlx @biomejs/biome init
pnpm biome check --write .   # lint + format 一把梭
```

## ESLint 9 flat config (仅在依赖 typed-rules / 复杂 plugin 时)

```ts
// eslint.config.ts (TS 项目)
import eslint from "@eslint/js";
import tseslint from "typescript-eslint";

export default tseslint.config(
  eslint.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  {
    languageOptions: {
      parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname },
    },
    rules: {
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/consistent-type-imports": ["error", { prefer: "type-imports" }],
    },
  },
);
```

## 命名约定 (TS 与 JS 通用)

```ts
type UserDTO = { id: string };                  // 类型 PascalCase (禁 I 前缀)
type Status = "active" | "inactive";
const userName = "John";                        // 变量 camelCase
function getUserById(id: string) { /* ... */ } // 函数 camelCase
const MAX_RETRIES = 3;                          // 常量 UPPER_SNAKE_CASE
// 文件 kebab-case: user-service.ts

// as const 替代 enum
const Role = { Admin: "admin", User: "user" } as const;
type Role = (typeof Role)[keyof typeof Role];
```

## tsgo 试用 (TS 7 native preview)

```bash
pnpm add -D @typescript/native-preview
pnpm exec tsgo --noEmit          # CI 快速类型检查
# 注意：emit/decorators/older targets 尚未完整，构建仍用 tsc
```

## JS-only 兜底：从 JavaScript 渐进迁移到 TypeScript

若项目暂不切 TS，仍可获得 80% 类型保护：

```js
// package.json
{ "type": "module" }
```

```jsonc
// jsconfig.json (或 tsconfig.json with allowJs)
{
  "compilerOptions": {
    "target": "ES2025",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "allowJs": true,
    "checkJs": true,             // 对 .js 也跑类型检查
    "strict": true,
    "noEmit": true,
    "skipLibCheck": true
  },
  "include": ["src/**/*"]
}
```

```js
// 用 JSDoc 标注类型，tsc 当 linter 用
/**
 * @typedef {{ id: string; name: string; email: string }} User
 */

/**
 * @param {string} id
 * @returns {Promise<User>}
 */
export async function getUser(id) {
  const r = await fetch(`/api/users/${id}`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return /** @type {User} */ (await r.json());
}
```

```bash
# 类型检查 (零编译产物)
pnpm tsc --noEmit
```

Biome 2 / ESLint flat 对 JS 项目同样有效；JS 项目把上面 ESLint 示例去掉 `tseslint`，仅用 `@eslint/js`：

```js
// eslint.config.js
import js from '@eslint/js';
export default [
  js.configs.recommended,
  {
    files: ['src/**/*.{js,jsx}'],
    rules: {
      'no-var': 'error',
      'prefer-const': 'error',
      'no-console': ['warn', { allow: ['warn', 'error'] }],
    },
  },
];
```

**迁移路线**：JSDoc + `checkJs` → 文件级 `.ts` → 局部启 `strict` → 全量 strict。

## Red Flags

| 现象 | 问题 | 严重 |
|------|------|------|
| `any` | 类型安全漏洞 | 高 |
| `@ts-ignore` | 隐藏真实错误 (用 `@ts-expect-error` + 注释) | 高 |
| `var` / `require()` | ESM / `const` / `let` | 高 |
| `enum` | tree-shaking 不友好 | 中 |
| `.eslintrc.js` | 旧 schema | 中 |
| 文件 > 500 行 | 拆分信号 | 中 |
| `npm install` 新项目 | pnpm/Bun 更优 | 中 |
| Jest 配置 | Vitest 3.x 替代 | 中 |
| 生产 `console.log` | pino 结构化输出 | 中 |
| 无运行时校验 | Zod 4 边界校验 | 高 |
| `arr.sort()` 变异 | `arr.toSorted()` | 中 |

## 检查清单

- [ ] TS: `strict: true` + `noUncheckedIndexedAccess` + `exactOptionalPropertyTypes`
- [ ] TS: 无 `any` / `@ts-ignore`；JS: JSDoc + `checkJs: true`
- [ ] `as const` 替代 `enum`
- [ ] TS: `import type` 分离类型导入
- [ ] `"type": "module"`，ESM only
- [ ] `const`/`let`，无 `var`
- [ ] 非变异数组方法
- [ ] Biome 2 或 ESLint flat config (二选一)
- [ ] pnpm 10 / Bun 锁文件已提交
- [ ] Vitest 3.x，覆盖率 ≥ 80%
- [ ] Zod 校验外部数据
- [ ] 文件 ≤ 500 行

## 权威参考

- TC39: <https://github.com/tc39/proposals>
- TypeScript: <https://www.typescriptlang.org>
- Node.js: <https://nodejs.org/en/blog/release>
- Vite: <https://vite.dev>
- Biome 2: <https://biomejs.dev>
- Vitest 3: <https://vitest.dev>
