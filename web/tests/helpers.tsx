import { render } from "@testing-library/react";
import { vi } from "vitest";
import { MeContext } from "../src/context";
import type { Me, TaskItem } from "../src/types";

export const ME: Me = {
  me: "bob",
  name: "Bob",
  csrf: "csrf-from-me",
  mode: "dev",
  expires: "2026-10-03T12:00:00+08:00",
  members: [
    { h: "alice", name: "Alice" },
    { h: "bob", name: "Bob" },
  ],
  projects: [{ key: "pay", name: "支付" }],
};

export function task(over: Partial<TaskItem> = {}): TaskItem {
  const v = over.v ?? 1;
  return {
    id: "T-52",
    kind: "task",
    t: { t: "支付回调重试", by: "alice", trust: "peer_agent", client: "claude_code", label: "alice 的 Claude Code" },
    st: "pending",
    st_text: "待接受",
    who: "bob",
    by: "alice",
    v,
    assign: { seq: 1, by: "alice", bk: "agent", client: "claude_code" },
    project: "pay",
    content: { t: "回调失败时按指数退避重试 3 次。", by: "alice", trust: "peer_agent", client: "claude_code", label: "alice 的 Claude Code" },
    ev: [
      { e: 7, ty: "task.created", by: "alice", trust: "peer_agent", client: "claude_code", at: "10-02 22:42", ts: "2026-10-02T22:42:47+08:00", what: "发布了任务" },
      {
        e: 9,
        ty: "comment",
        by: "alice",
        trust: "peer_agent",
        client: "claude_code",
        at: "10-02 22:50",
        ts: "2026-10-02T22:50:03+08:00",
        t: "日志在 callback 目录。",
        agent: false,
        what: "评论",
      },
    ],
    page: { id: "T-52", v, sha: `sha-v${v}`, through: 9, seq: 1 },
    agent: { content: "needs_accept", through: 0, unforwarded: 1 },
    created: "2026-10-02T22:42:47+08:00",
    can: ["accept", "decline", "forward", "comment"],
    path: "/task?w=team&id=T-52",
    ...over,
  };
}

export interface Call {
  method: string;
  url: string;
  headers: Record<string, string>;
  body: unknown;
}

type Handler = (call: Call) => { status: number; body: unknown };

/** 假的 fetch：按顺序记下每次请求，由 handler 决定返回什么。 */
export function mockFetch(handler: Handler) {
  const calls: Call[] = [];
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const call: Call = {
      method: init?.method ?? "GET",
      url: String(input),
      headers: (init?.headers as Record<string, string>) ?? {},
      body: init?.body ? JSON.parse(String(init.body)) : undefined,
    };
    calls.push(call);
    const res = handler(call);
    return new Response(JSON.stringify(res.body), { status: res.status, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fn);
  return calls;
}

export function renderAs(ui: React.ReactElement, me: Me = ME) {
  return render(<MeContext.Provider value={me}>{ui}</MeContext.Provider>);
}
