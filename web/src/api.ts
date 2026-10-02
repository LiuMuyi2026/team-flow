// 网页 API 客户端：只认同源的人类会话 cookie；写请求带 X-CSRF-Token（双提交）。
// 错误一律变成 ApiError，message 是可以直接给人看的话（docs/web-api.md 第 5 节）。

import type { Home, Item, Me, TaskList, TaskView, Wechat } from "./types";

const BASE = "/api/v1/web";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly data: Record<string, unknown>;

  constructor(status: number, code: string, message: string, data: Record<string, unknown> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.data = data;
  }

  /** 409 conflict：页面上的版本已经旧了，要提示后重新拉详情。 */
  get isConflict(): boolean {
    return this.status === 409 && this.code === "conflict";
  }

  get isAuth(): boolean {
    return this.status === 401;
  }
}

export const CONFLICT_TEXT = "内容刚被修改，请重新查看。";

let csrfFromMe = "";
let authLost: (() => void) | null = null;

/** 任何请求收到 401（登录过期、登出、服务端重启）时调用：页面切到"请重新登录"。 */
export function onAuthLost(fn: (() => void) | null): void {
  authLost = fn;
}

export function setCsrf(token: string): void {
  csrfFromMe = token;
}

function readCookie(name: string): string {
  if (typeof document === "undefined") return "";
  for (const part of document.cookie.split(";")) {
    const i = part.indexOf("=");
    if (i < 0) continue;
    if (part.slice(0, i).trim() === name) return decodeURIComponent(part.slice(i + 1).trim());
  }
  return "";
}

function csrfToken(): string {
  return readCookie("tf_csrf") || csrfFromMe;
}

function str(v: unknown): string | undefined {
  return typeof v === "string" && v.trim() ? v : undefined;
}

/** 把服务端的错误变成人话。服务端的 message 本来就是中文，能用就用；几类常见的统一说法。 */
export function humanMessage(status: number, code: string, body: Record<string, unknown>): string {
  const server = str(body.message);
  if (status === 401) return "登录已过期，或者您已经登出。请在您自己的终端运行 scripts/login-link.sh 重新拿登录链接。";
  if (status === 403 && code === "csrf") return "页面已经过期，请刷新后再试。";
  if (status === 403 && code === "human_only") return "这个操作只能由您本人在网页上做。";
  if (status === 403) return server ?? "这个操作您现在不能做。";
  if (status === 404) return "没有找到这一项。可能编号不对，或者服务端刚重启过（重启后数据会清空）。";
  if (status === 409 && code === "conflict") return CONFLICT_TEXT;
  if (status === 409 && code === "taken") return server ?? "已经有人认领了。";
  if (status === 409 && code === "needs_accept") return server ?? "要先接受，才能开始或完成。";
  if (status === 409) return server ?? CONFLICT_TEXT;
  if (status === 413) return "内容太长了，请删减一些再提交。";
  if (status === 422 && code === "secret_detected") {
    const pos = typeof body.pos === "number" ? `（第 ${body.pos + 1} 个字起）` : "";
    return `您写的内容里像是有密钥或个人信息${pos}。请删掉这部分再提交，看板上不要放密钥、token 和个人信息。`;
  }
  if (status === 422) return "提交的内容格式不对，请刷新页面后再试。";
  if (status === 400) return server ?? "填写的内容不完整，请检查后再提交。";
  if (status === 429) return "操作太频繁了，请稍等一会儿再试。";
  if (status >= 500) return "服务端出错了，请稍后再试。一直这样的话，请看一下 .local/logs/server.log。";
  return server ?? `出了点问题（${status}），请刷新后再试。`;
}

async function request<T>(method: "GET" | "POST", path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  const init: RequestInit = { method, headers, credentials: "same-origin", cache: "no-store" };
  if (method !== "GET") {
    headers["Content-Type"] = "application/json";
    headers["X-CSRF-Token"] = csrfToken();
    init.body = JSON.stringify(body ?? {});
  }
  let res: Response;
  try {
    res = await fetch(BASE + path, init);
  } catch {
    throw new ApiError(0, "network", "连不上服务端。请确认 scripts/local-up.sh 启动的服务端还在运行，然后刷新页面。");
  }
  let data: unknown = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }
  if (!res.ok) {
    const obj = data && typeof data === "object" ? (data as Record<string, unknown>) : {};
    const code = str(obj.error) ?? `http_${res.status}`;
    if (res.status === 401 && authLost) authLost();
    throw new ApiError(res.status, code, humanMessage(res.status, code, obj), obj);
  }
  return data as T;
}

export function messageOf(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  return "出了点问题，请刷新后再试。";
}

// ---------------------------------------------------------------------------
// 读
// ---------------------------------------------------------------------------

export const api = {
  me: () => request<Me>("GET", "/me"),
  home: () => request<Home>("GET", "/home"),
  tasks: (view: TaskView, opts: { project?: string; q?: string; cursor?: string; limit?: number } = {}) => {
    const qs = new URLSearchParams({ view });
    if (opts.project) qs.set("project", opts.project);
    if (opts.q) qs.set("q", opts.q);
    if (opts.cursor) qs.set("cursor", opts.cursor);
    qs.set("limit", String(opts.limit ?? 20));
    return request<TaskList>("GET", `/tasks?${qs.toString()}`);
  },
  task: (id: string) => request<Item>("GET", `/tasks/${encodeURIComponent(id)}`),
  blocker: (id: string) => request<Item>("GET", `/blockers/${encodeURIComponent(id)}`),
  wechat: (limit = 50) => request<Wechat>("GET", `/wechat?limit=${limit}`),

  // -------------------------------------------------------------------------
  // 写：人类动作都带页面渲染时看到的值（v、sha、seq、through），见 docs/web-api.md 第 1 节
  // -------------------------------------------------------------------------

  createTask: (p: { title: string; body?: string; assignee?: string; project?: string; urgent?: boolean }) =>
    request<{ id: string; st: string; path: string }>("POST", "/tasks", p),
  taskAction: (id: string, action: string, body: Record<string, unknown> = {}) =>
    request<Record<string, unknown>>("POST", `/tasks/${encodeURIComponent(id)}:${action}`, body),
  blockerAction: (id: string, action: string, body: Record<string, unknown> = {}) =>
    request<Record<string, unknown>>("POST", `/blockers/${encodeURIComponent(id)}:${action}`, body),
  comment: (kind: "task" | "blocker", id: string, body: string) =>
    request<{ id: number }>("POST", `/${kind === "task" ? "tasks" : "blockers"}/${encodeURIComponent(id)}/comments`, { body }),
  logout: () => request<{ ok: boolean }>("POST", "/logout", {}),
};
