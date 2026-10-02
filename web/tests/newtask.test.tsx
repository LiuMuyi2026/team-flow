import { cleanup, fireEvent, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { NewTask } from "../src/pages/NewTask";
import { mockFetch, renderAs } from "./helpers";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("发布", () => {
  it("疑似密钥被拦下后，改了内容就收起旧的错误提示", async () => {
    mockFetch(() => ({ status: 422, body: { error: "secret_detected", message: "x", rule: "tencent_akid", pos: 9 } }));
    renderAs(<NewTask />);
    fireEvent.change(screen.getByLabelText("标题"), { target: { value: "核对支付回调的签名" } });
    fireEvent.change(screen.getByLabelText("内容（选填）"), { target: { value: "对方给的测试密钥是 AKID" + "x".repeat(20) } });
    fireEvent.click(screen.getByRole("button", { name: "发布" }));
    expect((await screen.findByRole("alert")).textContent).toContain("像是有密钥或个人信息");
    fireEvent.change(screen.getByLabelText("内容（选填）"), { target: { value: "密钥找值班的人要。" } });
    expect(screen.queryByRole("alert")).toBeNull();
  });
});
