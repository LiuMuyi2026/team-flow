import { cleanup, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { switchExample } from "../src/App";
import { Notifications } from "../src/pages/Notifications";
import type { Me } from "../src/types";
import { seen } from "../src/unread";
import { ME, mockFetch, renderAs } from "./helpers";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.localStorage.clear();
});

describe("模拟通知", () => {
  it("读 /notifications，说明正式版按您选的渠道发，记下看到的最新编号", async () => {
    const calls = mockFetch((c) =>
      c.url.includes("/api/v1/web/notifications")
        ? {
            status: 200,
            body: {
              items: [
                {
                  n: 3,
                  kind: "blocker_needs_you",
                  kind_text: "请您帮忙",
                  text: "alice 请您帮忙看 B-8",
                  subject: "B-8",
                  at: "10-02 23:47",
                  ts: "2026-10-02T23:47:00+08:00",
                  path: "/blocker?w=team&id=B-8&n=3",
                },
              ],
              total: 1,
            },
          }
        : { status: 404, body: { error: "not_found" } },
    );
    renderAs(<Notifications />);
    await screen.findByText("alice 请您帮忙看 B-8");
    expect(screen.getByRole("heading", { name: "模拟通知" })).toBeTruthy();
    expect(screen.getByText(/正式版会按您选的渠道（邮件或微信）/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "详情" }).getAttribute("href")).toBe("/blocker?w=team&id=B-8&n=3");
    expect(calls.every((c) => c.url.includes("/api/v1/web/notifications?limit=50"))).toBe(true);
    // 页面上只在说明渠道时提到微信一次；不再说"手机微信"
    const text = document.body.textContent ?? "";
    expect(text).not.toContain("手机");
    expect(text.split("微信").length - 1).toBe(1);
    await waitFor(() => expect(seen(ME.me)).toBe(3));
  });
});

describe("「我」页：换成队友的例子", () => {
  const me = (members: Me["members"]): Me => ({ ...ME, me: "me", members });

  it("挑有 agent 令牌的队友，不挑只在演示数据里的 alice", () => {
    expect(
      switchExample(
        me([
          { h: "alice", name: "Alice" },
          { h: "bob", name: "Bob", agent: true },
          { h: "carol", name: "carol", agent: true },
          { h: "me", name: "me", agent: true },
        ]),
      ),
    ).toBe("bob");
  });

  it("没人带 agent 标记时退回第一位队友；只有自己时没有例子", () => {
    expect(switchExample(me([{ h: "alice", name: "Alice" }, { h: "me", name: "me" }]))).toBe("alice");
    expect(switchExample(me([{ h: "me", name: "me", agent: true }]))).toBeUndefined();
  });
});
