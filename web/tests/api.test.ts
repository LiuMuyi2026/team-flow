import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, CONFLICT_TEXT, humanMessage, setCsrf, STALE_SERVER_TEXT } from "../src/api";

afterEach(() => {
  vi.unstubAllGlobals();
  document.cookie = "tf_csrf=; Max-Age=0";
});

describe("错误变人话", () => {
  it("409 conflict 一律是「内容刚被修改，请重新查看。」", () => {
    expect(humanMessage(409, "conflict", { message: "T-52 当前不是待您接受的状态（待开始）。" })).toBe(CONFLICT_TEXT);
  });
  it("409 taken 用服务端的说法（带谁、几点）", () => {
    expect(humanMessage(409, "taken", { message: "T-51 已被 alice 于 10:21 认领。可以在「待认领」里换一个。" })).toContain("alice");
  });
  it("422 疑似密钥给位置，不复述内容", () => {
    const m = humanMessage(422, "secret_detected", { rule: "tencent_akid", pos: 10 });
    expect(m).toContain("第 11 个字起");
    expect(m).not.toContain("tencent_akid");
  });
  it("401、403 csrf、404、500 各有固定说法", () => {
    expect(humanMessage(401, "unauthorized", {})).toContain("scripts/login-link.sh");
    expect(humanMessage(403, "csrf", {})).toContain("刷新");
    expect(humanMessage(404, "not_found", {})).toContain("没有找到");
    // 没有这个接口：在跑的服务端是旧代码（新服务端带 no_route，旧服务端只有 Starlette 默认的 "Not Found"）
    expect(humanMessage(404, "not_found", { message: "Not Found", no_route: true })).toBe(STALE_SERVER_TEXT);
    expect(humanMessage(404, "not_found", { message: "Not Found" })).toContain("scripts/local-up.sh");
    expect(humanMessage(404, "not_found", { message: "没有 T-99。" })).toContain("没有找到");
    expect(humanMessage(500, "http_500", {})).toContain("服务端出错了");
  });
});

describe("请求", () => {
  it("写请求带 X-CSRF-Token（优先读 tf_csrf cookie）和 JSON 请求体", async () => {
    document.cookie = "tf_csrf=from-cookie";
    setCsrf("from-me");
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ id: "T-52" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await api.taskAction("T-52", "accept", { v: 1, sha: "s", seq: 1, through: 9 });
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/web/tasks/T-52:accept");
    expect(init.method).toBe("POST");
    expect((init.headers as Record<string, string>)["X-CSRF-Token"]).toBe("from-cookie");
    expect(JSON.parse(String(init.body))).toEqual({ v: 1, sha: "s", seq: 1, through: 9 });
    expect(init.credentials).toBe("same-origin");
  });

  it("连不上服务端时说人话", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("Failed to fetch"))));
    const err = await api.home().catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).message).toContain("连不上服务端");
  });

  it("409 conflict 抛 ApiError，isConflict 为真", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ error: "conflict", message: "x", v: 2 }), { status: 409 })));
    const err = (await api.taskAction("T-52", "accept", {}).catch((e: unknown) => e)) as ApiError;
    expect(err.isConflict).toBe(true);
    expect(err.message).toBe(CONFLICT_TEXT);
    expect(err.data.v).toBe(2);
  });
});
