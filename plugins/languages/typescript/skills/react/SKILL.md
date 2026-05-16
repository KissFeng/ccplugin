---
name: typescript-react
description: TypeScript / JavaScript React 开发规范，覆盖 React 19 Server Components / Server Actions / use() hook / useActionState / useOptimistic / useFormStatus / Suspense、Next.js 15 App Router、Route Handlers、React Compiler 自动 memo、TanStack Query 5、TanStack Router、Zustand 状态、自定义 hook AbortController 模板。Use when 开发 React 组件、页面路由、SSR、状态管理、表单处理、数据获取，或用户提到 "React"、"Next.js"、"Server Components"、"use client"、"Server Actions"、"useState"、"JSX"、"App Router"。
user-invocable: true
---

# TypeScript / JavaScript React 开发规范 (2026)

本 skill 同时覆盖 JavaScript 项目；示例以 TS 为主，JS 项目去掉类型即可。

React 19 默认 Server Components；`"use client"` 是边界标记，不滥用。

## 配套 skills

- `typescript-core` — 工具链与基线
- `typescript-async` — AbortController, Suspense 配合
- `typescript-security` — XSS, dangerouslySetInnerHTML

## React Compiler (默认启用)

React 19 Compiler 自动记忆化组件、hooks、JSX，**手写 `useMemo` / `useCallback` / `memo` 改为可选**。仅在 profiler 证实瓶颈时手动优化。

```typescript
// ❌ React 18 手写 (Compiler 启用后冗余)
const v = useMemo(() => compute(data), [data]);
const onClick = useCallback(() => f(id), [id]);
export default React.memo(MyComp);

// ✅ React 19 + Compiler
const v = compute(data);
const onClick = () => f(id);
export default MyComp;
```

## React 19 核心特性

### Server Components (默认)

```typescript
// app/users/page.tsx
import { db } from "@/lib/db";

export default async function UsersPage() {
  const users = await db.user.findMany();
  return <ul>{users.map((u) => <li key={u.id}>{u.name}</li>)}</ul>;
}
```

### Server Actions

```typescript
// app/actions.ts
"use server";
import { z } from "zod";
import { revalidatePath } from "next/cache";

const CreateUserSchema = z.object({
  name: z.string().min(1).max(100),
  email: z.email(),
});

export async function createUser(_: unknown, formData: FormData) {
  const r = CreateUserSchema.safeParse({
    name: formData.get("name"),
    email: formData.get("email"),
  });
  if (!r.success) return { errors: z.flattenError(r.error).fieldErrors };
  await db.user.create({ data: r.data });
  revalidatePath("/users");
  return { ok: true as const };
}
```

### use() Hook + Suspense

```typescript
import { use, Suspense } from "react";

function UserProfile({ userPromise }: { userPromise: Promise<User> }) {
  const user = use(userPromise);   // suspend
  return <div>{user.name}</div>;
}

<Suspense fallback={<Loading />}>
  <UserProfile userPromise={fetchUser(id)} />
</Suspense>
```

### useActionState / useOptimistic / useFormStatus

```typescript
"use client";
import { useActionState, useOptimistic } from "react";
import { useFormStatus } from "react-dom";

function CreateUserForm() {
  const [state, action, isPending] = useActionState(createUser, null);
  return (
    <form action={action}>
      <input name="name" required />
      <input name="email" type="email" required />
      {state?.errors && <p>{JSON.stringify(state.errors)}</p>}
      <SubmitButton />
    </form>
  );
}

function SubmitButton() {
  const { pending } = useFormStatus();
  return <button disabled={pending}>{pending ? "..." : "Create"}</button>;
}

// 乐观更新
const [optimistic, addOptimistic] = useOptimistic(
  messages,
  (prev, next) => [...prev, { ...next, sending: true }],
);

// document metadata 原生
<title>{post.title}</title>
<meta name="description" content={post.excerpt} />
```

## 函数组件

```typescript
// ✅ 普通函数
type UserCardProps = {
  user: User;
  onSelect?: (id: string) => void;
};

export function UserCard({ user, onSelect }: UserCardProps) {
  return (
    <div onClick={() => onSelect?.(user.id)}>
      <h3>{user.name}</h3>
    </div>
  );
}

// ❌ 禁 React.FC (隐式 children、泛型不友好)
```

## 自定义 Hook (AbortController 模板)

```typescript
export function useFetch<T>(url: string) {
  const [state, setState] = useState<AsyncState<T>>({ status: "idle" });

  useEffect(() => {
    const ctrl = new AbortController();
    setState({ status: "loading" });
    fetch(url, { signal: ctrl.signal })
      .then((r) => r.json() as Promise<T>)
      .then((data) => setState({ status: "success", data }))
      .catch((error: unknown) => {
        if (!ctrl.signal.aborted) setState({ status: "error", error: error as Error });
      });
    return () => ctrl.abort();
  }, [url]);

  return state;
}
```

## 数据获取

| 场景 | 推荐 |
|------|------|
| Next.js App Router | Server Components + `fetch()` + revalidate |
| Vite SPA | TanStack Query 5 (`useSuspenseQuery` + Suspense) |
| Realtime / 订阅 | WebSocket / SSE in `useEffect` + AbortController |
| 表单 | Server Actions / TanStack Form |

```typescript
// TanStack Query 5 + Suspense
import { useSuspenseQuery } from '@tanstack/react-query';
function User({ id }: { id: string }) {
  const { data } = useSuspenseQuery({
    queryKey: ['user', id],
    queryFn: ({ signal }) => fetch(`/api/users/${id}`, { signal }).then(r => r.json()),
  });
  return <div>{data.name}</div>;
}
```

## Next.js 15 App Router

```typescript
// app/layout.tsx
import type { Metadata } from "next";
export const metadata: Metadata = { title: "App", description: "..." };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}

// app/api/users/route.ts
import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const body: unknown = await request.json();
  const r = CreateUserSchema.safeParse(body);
  if (!r.success) {
    return NextResponse.json({ errors: z.flattenError(r.error) }, { status: 400 });
  }
  const user = await db.user.create({ data: r.data });
  return NextResponse.json(user, { status: 201 });
}
```

## 路由 (非 Next.js)

- **Vite SPA**: TanStack Router (type-safe) 或 React Router 7 (data router 模式)
- 永远 lazy import 路由级模块

```typescript
import { lazy, Suspense } from 'react';
const Dashboard = lazy(() => import('./pages/Dashboard'));
<Suspense fallback={<Spinner />}><Dashboard /></Suspense>
```

## 状态管理

- 本地: `useState` / `useReducer`
- URL: search params (Next: `useSearchParams`, TanStack Router: typed)
- 跨组件全局: Zustand 5 (轻) / Jotai (atomic) / Redux Toolkit (复杂)
- 服务端缓存: TanStack Query / RSC + revalidate

## JS-only 兜底

所有 React 19 API 在 JS 项目同样可用，去掉类型注解即可。JS 项目用 JSDoc 标注 props：

```js
/**
 * @param {{ user: User; onSelect?: (id: string) => void }} props
 */
export function UserCard({ user, onSelect }) {
  return <div onClick={() => onSelect?.(user.id)}><h3>{user.name}</h3></div>;
}
```

## Red Flags

| 现象 | 问题 | 严重 |
|------|------|------|
| `React.FC` | 隐式 children、泛型受限 | 中 |
| class 组件 | 函数组件 + Hooks | 高 |
| `useEffect` 内 fetch (无 abort) | TanStack Query 或加 AbortController | 中 |
| `"use client"` 顶层滥用 | 应最小化 client 边界 | 中 |
| 无 Suspense 边界 | 异步组件需 fallback | 高 |
| Server Actions 无 Zod | 服务端必须验证 | 高 |
| 手写 memo (Compiler 已开) | 冗余 | 低 |
| 无 `key` / index as key | 稳定 ID 作 key | 高 |
| 依赖数组缺失 | Biome/ESLint react-hooks 修复 | 高 |
| `dangerouslySetInnerHTML` 无清理 | DOMPurify | 高 |

## 检查清单

- [ ] 函数组件 + Hooks (非 `React.FC`)
- [ ] 默认 Server Components；`"use client"` 仅边界
- [ ] React 19 Compiler 启用 (`react-compiler` babel plugin)
- [ ] 数据获取在 Server Component 或 TanStack Query
- [ ] 表单用 Server Actions + `useActionState`
- [ ] Suspense + ErrorBoundary 包数据边界
- [ ] AbortController 在 useEffect 清理
- [ ] 路由级 lazy + Suspense
- [ ] Zod 校验 Server Action 输入
- [ ] 启用 React Compiler 后避免手写 memo

## 参考

- React 19: <https://react.dev/blog/2024/12/05/react-19>
- Next.js 15: <https://nextjs.org/docs>
- TanStack Query 5: <https://tanstack.com/query/latest>
