---
name: typescript-async
description: TypeScript / JavaScript 异步编程规范，覆盖 async/await 错误处理、AbortController 取消与超时、Promise.all/allSettled/any/try/withResolvers、Streams API、Web Workers、Node worker_threads、scheduler.yield 长任务切片、async iterators、tRPC 类型安全 API、Effect-TS。Use when 编写异步逻辑、并发控制、流式数据、取消请求、超时、API 客户端、Web Worker offloading，或用户提到 "async"、"Promise"、"取消请求"、"AbortController"、"并发"、"超时"、"竞态"、"streaming"、"Web Worker"。
user-invocable: true
---

# TypeScript / JavaScript 异步编程规范

本 skill 同时覆盖 JavaScript 项目；示例以 TypeScript 为主，JS 项目去掉类型注解即可。

异步两条铁律：**显式取消** + **结构化错误**。

## 配套 skills

- `typescript-core` — 工具链与基线
- `typescript-security` — fetch 边界校验

## async/await 错误处理

```typescript
// ✅ 多行结构化, try-catch 内必 return await (错误才能进 catch)
async function getUser(id: string): Promise<User> {
  try {
    const r = await fetch(`/api/users/${id}`);
    if (!r.ok) throw new Error(`HTTP ${r.status}: ${r.statusText}`);
    const data: unknown = await r.json();
    return UserSchema.parse(data);                // Zod 边界验证
  } catch (e) {
    logger.error({ err: e, id }, 'getUser failed');
    throw e;
  }
}

// ✅ Promise.try (ES2025): 同步异常也进 Promise 链
const p = Promise.try(() => mayThrowSync());

// ❌ 单行
// if (err) return err;
```

## AbortController 取消 / 超时 / 清理

```typescript
// 超时 — Node 22+ / 现代浏览器内置
async function fetchWithTimeout(url: string, ms = 5000): Promise<Response> {
  const signal = AbortSignal.timeout(ms);
  return fetch(url, { signal });
}

// 组合多个 signal (ES2024)
const signal = AbortSignal.any([userSignal, timeoutSignal]);

// 竞态：取消过期请求
let inflight: AbortController | null = null;
async function search(q: string) {
  inflight?.abort();
  inflight = new AbortController();
  try {
    const r = await fetch(`/api/search?q=${q}`, { signal: inflight.signal });
    return await r.json();
  } catch (e) {
    if ((e as Error).name === 'AbortError') return;
    throw e;
  }
}

// 统一清理事件监听
function setup(el: HTMLElement) {
  const ctrl = new AbortController();
  const { signal } = ctrl;
  el.addEventListener('click', onClick, { signal });
  window.addEventListener('resize', onResize, { signal });
  return () => ctrl.abort();
}

// React 19 中取消
useEffect(() => {
  const ctrl = new AbortController();
  fetchData({ signal: ctrl.signal })
    .then(setData)
    .catch((err) => { if (!ctrl.signal.aborted) console.error(err); });
  return () => ctrl.abort();
}, []);
```

## 并发模式

```typescript
// Promise.all — 全成功 or 快速失败
const [users, posts] = await Promise.all([fetchUsers(), fetchPosts()]);

// Promise.allSettled — 容错并发 (推荐聚合)
const results = await Promise.allSettled([fetchA(), fetchB(), fetchC()]);
const ok = results
  .filter((r): r is PromiseFulfilledResult<Data> => r.status === "fulfilled")
  .map((r) => r.value);

// Promise.any — 任一成功 (fallback)
const fastest = await Promise.any([primary(), mirror1(), mirror2()]);

// 限并发 (无外部依赖)
async function pool<T, R>(items: T[], n: number, fn: (i: T) => Promise<R>): Promise<R[]> {
  const out: R[] = []; let i = 0;
  const workers = Array.from({ length: n }, async () => {
    while (i < items.length) {
      const idx = i++;
      out[idx] = await fn(items[idx]);
    }
  });
  await Promise.all(workers);
  return out;
}
```

## Promise.withResolvers (ES2024)

```typescript
// 替代手动 new Promise(...)
const { promise, resolve, reject } = Promise.withResolvers<string>();
element.addEventListener('click', () => resolve('clicked'), { once: true });
const value = await promise;
```

## Async Iterators (分页 / 流式)

```typescript
async function* fetchPages(base: string): AsyncGenerator<Page[]> {
  let cursor: string | null = null;
  do {
    const r = await fetch(`${base}?cursor=${cursor ?? ""}`);
    const data = await r.json();
    yield data.items;
    cursor = data.nextCursor;
  } while (cursor);
}

for await (const page of fetchPages("/api/items")) {
  for (const item of page) process(item);
}
```

## Streams API (前端 / Node 通用)

```typescript
// 流式 NDJSON 处理
async function* lines(stream: ReadableStream<Uint8Array>) {
  const reader = stream.pipeThrough(new TextDecoderStream()).getReader();
  let buf = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += value;
    const parts = buf.split('\n');
    buf = parts.pop()!;
    for (const p of parts) if (p) yield JSON.parse(p);
  }
  if (buf) yield JSON.parse(buf);
}

// TransformStream 管线
const res = await fetch(url);
await res.body!
  .pipeThrough(new TextDecoderStream())
  .pipeThrough(new TransformStream({ transform(c, ctl) { ctl.enqueue(c.toUpperCase()); } }))
  .pipeTo(writableSink);

// Array.fromAsync (ES2025)
const items = await Array.fromAsync(asyncGen(), x => x.id);
```

## Web Workers (ESM)

```typescript
const worker = new Worker(new URL('./worker.ts', import.meta.url), { type: 'module' });
worker.postMessage({ task: 'parse', payload: data });
worker.addEventListener('message', (e) => console.log(e.data), { once: true });
worker.addEventListener('error', console.error);
// worker.terminate();
```

## Node Worker threads (CPU-heavy)

```typescript
import { Worker } from 'node:worker_threads';
const w = new Worker(new URL('./heavy.ts', import.meta.url));
w.postMessage(data);
w.on('message', (r) => console.log(r));
```

## 长任务切片

```typescript
// scheduler.yield() (Chrome 129+, fallback setTimeout 0)
async function processBig<T>(items: T[]) {
  for (const item of items) {
    work(item);
    if ('scheduler' in globalThis && 'yield' in (globalThis as any).scheduler) {
      await (globalThis as any).scheduler.yield();
    } else {
      await new Promise(r => setTimeout(r, 0));
    }
  }
}
```

## tRPC 类型安全 API (TS 项目)

```typescript
import { initTRPC } from "@trpc/server";
import { z } from "zod";

const t = initTRPC.create();

export const appRouter = t.router({
  getUser: t.procedure
    .input(z.object({ id: z.uuid() }))
    .query(({ input }) => db.user.findUnique({ where: { id: input.id } })),
  createUser: t.procedure
    .input(CreateUserSchema)
    .mutation(({ input }) => db.user.create({ data: input })),
});

export type AppRouter = typeof appRouter;
// 客户端：完全类型推断
```

## Effect-TS (typed errors 进阶，TS 项目)

```typescript
import { Effect, pipe } from "effect";

const getUser = (id: string) =>
  pipe(
    Effect.tryPromise({
      try: () => fetch(`/api/users/${id}`),
      catch: () => new NetworkError(),
    }),
    Effect.flatMap((res) =>
      res.ok
        ? Effect.tryPromise({ try: () => res.json(), catch: () => new ParseError() })
        : Effect.fail(new HttpError(res.status)),
    ),
  );
// Effect<unknown, NetworkError | ParseError | HttpError>
```

## JS-only 兜底

上述模式全部适用于 JS 项目，直接去掉类型注解 / 泛型即可。tRPC 与 Effect-TS 强依赖 TS 推断，JS 项目建议改用 OpenAPI + Zod (JSDoc 提供 IDE 提示)：

```js
/** @type {(id: string) => Promise<User>} */
export async function getUser(id) {
  const r = await fetch(`/api/users/${id}`, { signal: AbortSignal.timeout(5000) });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return UserSchema.parse(await r.json());
}
```

## Red Flags

| 现象 | 问题 | 严重 |
|------|------|------|
| 顺序 await 独立请求 | 应 `Promise.all` 并发 | 高 |
| 未 catch / 漏 await | unhandled rejection | 高 |
| try 内 `return fetch(...)` 不 await | 错误逃出 try | 高 |
| 无超时 | 请求挂死 | 中 |
| 无 AbortController | 组件卸载继续请求 | 中 |
| `.then().catch()` 链 | async/await 更可读 | 低 |
| `Promise.all` 中混含可失败任务 | 用 `allSettled` | 中 |
| 手写 `new Promise((res,rej)=>...)` | 用 `withResolvers` | 低 |
| 大数组同步 `forEach` 阻塞主线程 | 切片 + scheduler.yield | 中 |
| 回调嵌套 | 换 async/await | 高 |

## 检查清单

- [ ] async/await (非 callback / 链式 then)
- [ ] 多行结构化错误处理，try-catch 内 `return await`
- [ ] 独立请求 `Promise.all` 并发；聚合用 `allSettled`
- [ ] 网络请求有 `AbortSignal.timeout`
- [ ] 用户输入触发的请求有 AbortController
- [ ] React useEffect / Vue onUnmounted 中 abort
- [ ] 事件监听经 `{ signal }` 统一清理
- [ ] 分页用 async iterator
- [ ] CPU 密集 → Web Worker / worker_threads
- [ ] 大流数据 → Streams，不 `JSON.parse` 整文件
- [ ] API 边界 Zod 校验
