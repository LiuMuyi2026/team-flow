#!/usr/bin/env python3
"""MCP 两代协议冒烟测试（plan 9.3、M0 S1 的服务端部分）。

用 httpx 手写 JSON-RPC，分别按两代协议对 <base>/mcp 和 <base>/mcp/ 做 list 与 call：
- 旧代 2025-06-18：initialize → notifications/initialized → tools/list → tools/call（带 MCP-Protocol-Version 头）
- 新代 2026-07-28：server/discover → tools/list → tools/call（无 initialize；_meta 带版本/能力/clientInfo；
  头带 MCP-Protocol-Version、Mcp-Method、Mcp-Name），断言 tools/list 有 ttlMs 和 cacheScope
断言：9 个工具、名字与顺序、annotations、alwaysLoad、所有请求都不出现 3xx、两代 tools/list 完全一致。
另外断言评审修复后的协议行为：
- 能力宣告只有 tools，两代都不宣告 listChanged（m6）；discover 与 -32022 的 supported 同时列出两代版本（m6）；
- 业务错误的 content 文本以错误码开头（I5）；
- /mcp 请求体超过 64KB 返回 413，不带令牌的大请求体直接 401（先鉴权再读请求体，m7）。
再用官方 mcp 2.2.0 客户端（auto 与 legacy 两种模式）交叉验证一次，并记录它见到的所有 HTTP 状态码。

用法：
  .venv/bin/python spike/smoke_mcp.py --base http://127.0.0.1:8190 [--token tf_pat_dev_alice] [--out spike/out/smoke_mcp.json]
退出码：全部通过为 0，否则为 1。报告是 JSON（同时打印到 stdout）。
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx

EXPECTED_TOOLS = [
    "inbox",
    "list_tasks",
    "get_item",
    "team_status",
    "create_task",
    "claim_task",
    "update_task",
    "report_blocker",
    "comment",
]
READ_TOOLS = {"inbox", "list_tasks", "get_item", "team_status"}
ALWAYS_LOAD = {"inbox", "update_task"}
ACCEPT = "application/json, text/event-stream"
LEGACY_VERSIONS = {"2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"}
MAX_MCP_BODY = 64 * 1024
PV_KEY = "io.modelcontextprotocol/protocolVersion"
CAPS_KEY = "io.modelcontextprotocol/clientCapabilities"
CI_KEY = "io.modelcontextprotocol/clientInfo"


class Report:
    def __init__(self) -> None:
        self.checks: list[dict[str, Any]] = []
        self.http: list[dict[str, Any]] = []

    def check(self, name: str, ok: bool, detail: Any = None) -> bool:
        item: dict[str, Any] = {"name": name, "ok": bool(ok)}
        if detail is not None:
            item["detail"] = detail
        self.checks.append(item)
        return bool(ok)

    @property
    def ok(self) -> bool:
        return all(c["ok"] for c in self.checks)


def parse_body(r: httpx.Response) -> Any:
    ctype = r.headers.get("content-type", "")
    if "text/event-stream" in ctype:
        last = None
        for line in r.text.splitlines():
            if line.startswith("data:"):
                try:
                    cand = json.loads(line[5:].strip())
                except ValueError:
                    continue
                if isinstance(cand, dict) and ("result" in cand or "error" in cand):
                    last = cand
        return last
    if not r.content:
        return None
    try:
        return r.json()
    except ValueError:
        return None


def tools_problems(tools: list[dict[str, Any]]) -> list[str]:
    probs: list[str] = []
    names = [t.get("name") for t in tools]
    if names != EXPECTED_TOOLS:
        probs.append(f"names/order {names}")
    for t in tools:
        n = t.get("name")
        ann = t.get("annotations") or {}
        meta = t.get("_meta") or {}
        if n in READ_TOOLS:
            if ann.get("readOnlyHint") is not True or ann.get("openWorldHint") is not False:
                probs.append(f"{n} read annotations {ann}")
        else:
            if ann.get("readOnlyHint") is not False or ann.get("destructiveHint") is not False or ann.get("openWorldHint") is not False:
                probs.append(f"{n} write annotations {ann}")
            if (ann.get("idempotentHint") is True) != (n == "claim_task"):
                probs.append(f"{n} idempotentHint {ann.get('idempotentHint')}")
        if (meta.get("anthropic/alwaysLoad") is True) != (n in ALWAYS_LOAD):
            probs.append(f"{n} alwaysLoad {meta}")
    return probs


def tools_hash(tools: list[dict[str, Any]]) -> str:
    return hashlib.sha256(json.dumps(tools, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


class Raw:
    """手写 JSON-RPC。follow_redirects=False，记录每个响应的状态码。"""

    def __init__(self, client: httpx.AsyncClient, rep: Report, token: str) -> None:
        self.c, self.rep, self.token = client, rep, token
        self._id = 0

    async def post(self, label: str, url: str, body: dict[str, Any], headers: dict[str, str]) -> httpx.Response:
        t0 = time.perf_counter()
        r = await self.c.post(url, json=body, headers=headers)
        self.rep.http.append(
            {"label": label, "url": url, "method": body.get("method"), "status": r.status_code, "ms": round((time.perf_counter() - t0) * 1000, 1), "location": r.headers.get("location")}
        )
        return r

    def nid(self) -> int:
        self._id += 1
        return self._id


async def legacy_flow(raw: Raw, rep: Report, url: str, version: str = "2025-06-18") -> list[dict[str, Any]] | None:
    tag = f"legacy[{version}] {url}"
    base_h = {"accept": ACCEPT, "content-type": "application/json", "authorization": f"Bearer {raw.token}"}
    r = await raw.post(tag, url, {"jsonrpc": "2.0", "id": raw.nid(), "method": "initialize", "params": {"protocolVersion": version, "capabilities": {}, "clientInfo": {"name": "teamflow-smoke-legacy", "version": "0.1"}}}, base_h)
    body = parse_body(r)
    res = (body or {}).get("result") or {}
    rep.check(f"{tag} initialize 200", r.status_code == 200, r.status_code)
    rep.check(f"{tag} initialize protocolVersion", res.get("protocolVersion") == version, res.get("protocolVersion"))
    rep.check(f"{tag} instructions present", bool(res.get("instructions")), len(res.get("instructions") or ""))
    sid = r.headers.get("mcp-session-id")
    rep.check(f"{tag} stateless (no Mcp-Session-Id)", sid is None, sid)
    caps = res.get("capabilities")
    rep.check(f"{tag} capabilities only tools, no listChanged", caps == {"tools": {}}, caps)
    h = {**base_h, "mcp-protocol-version": version}
    if sid:
        h["mcp-session-id"] = sid
    r = await raw.post(tag, url, {"jsonrpc": "2.0", "method": "notifications/initialized"}, h)
    rep.check(f"{tag} notifications/initialized 202", r.status_code == 202, r.status_code)
    r = await raw.post(tag, url, {"jsonrpc": "2.0", "id": raw.nid(), "method": "tools/list", "params": {}}, h)
    tools = (((parse_body(r) or {}).get("result")) or {}).get("tools") or []
    probs = tools_problems(tools)
    rep.check(f"{tag} tools/list 9 tools + annotations", r.status_code == 200 and not probs, probs or len(tools))
    r = await raw.post(tag, url, {"jsonrpc": "2.0", "id": raw.nid(), "method": "tools/call", "params": {"name": "inbox", "arguments": {"limit": 5}}}, h)
    res = ((parse_body(r) or {}).get("result")) or {}
    sc = res.get("structuredContent") or {}
    rep.check(f"{tag} tools/call inbox", r.status_code == 200 and res.get("isError") is False and "me" in sc, {"isError": res.get("isError"), "me": sc.get("me")})
    r = await raw.post(tag, url, {"jsonrpc": "2.0", "id": raw.nid(), "method": "tools/call", "params": {"name": "get_item", "arguments": {"id": "T-999999"}}}, h)
    res = ((parse_body(r) or {}).get("result")) or {}
    rep.check(f"{tag} tools/call business error is isError", res.get("isError") is True and (res.get("structuredContent") or {}).get("err") == "not_found", res.get("structuredContent"))
    text = ((res.get("content") or [{}])[0]).get("text") or ""
    rep.check(f"{tag} error content starts with code", text.startswith("not_found："), text[:40])
    return tools


def modern_meta(**more: Any) -> dict[str, Any]:
    return {PV_KEY: "2026-07-28", CAPS_KEY: {}, CI_KEY: {"name": "teamflow-smoke-modern", "version": "0.1"}, **more}


async def modern_flow(raw: Raw, rep: Report, url: str) -> list[dict[str, Any]] | None:
    tag = f"modern[2026-07-28] {url}"

    def hdr(method: str, name: str | None = None) -> dict[str, str]:
        h = {"accept": ACCEPT, "content-type": "application/json", "authorization": f"Bearer {raw.token}", "mcp-protocol-version": "2026-07-28", "mcp-method": method}
        if name:
            h["mcp-name"] = name
        return h

    r = await raw.post(tag, url, {"jsonrpc": "2.0", "id": raw.nid(), "method": "server/discover", "params": {"_meta": modern_meta()}}, hdr("server/discover"))
    res = ((parse_body(r) or {}).get("result")) or {}
    rep.check(f"{tag} server/discover 200", r.status_code == 200, r.status_code)
    rep.check(f"{tag} discover supportedVersions has 2026-07-28", "2026-07-28" in (res.get("supportedVersions") or []), res.get("supportedVersions"))
    rep.check(f"{tag} discover supportedVersions lists legacy too", LEGACY_VERSIONS <= set(res.get("supportedVersions") or []), res.get("supportedVersions"))
    rep.check(f"{tag} discover capabilities only tools", res.get("capabilities") == {"tools": {}}, res.get("capabilities"))
    rep.check(f"{tag} discover instructions present", bool(res.get("instructions")), len(res.get("instructions") or ""))
    rep.check(f"{tag} no Mcp-Session-Id", r.headers.get("mcp-session-id") is None, r.headers.get("mcp-session-id"))
    r = await raw.post(tag, url, {"jsonrpc": "2.0", "id": raw.nid(), "method": "tools/list", "params": {"_meta": modern_meta()}}, hdr("tools/list"))
    res = ((parse_body(r) or {}).get("result")) or {}
    tools = res.get("tools") or []
    probs = tools_problems(tools)
    rep.check(f"{tag} tools/list 9 tools + annotations", r.status_code == 200 and not probs, probs or len(tools))
    rep.check(f"{tag} tools/list ttlMs + cacheScope", isinstance(res.get("ttlMs"), int) and res.get("cacheScope") in ("public", "private"), {"ttlMs": res.get("ttlMs"), "cacheScope": res.get("cacheScope")})
    turn = {"session_id": "smoke-session", "thread_id": "smoke-thread", "turn_id": "smoke-turn"}
    r = await raw.post(
        tag,
        url,
        {"jsonrpc": "2.0", "id": raw.nid(), "method": "tools/call", "params": {"name": "get_item", "arguments": {"id": "T-50", "events": 2}, "_meta": modern_meta(callId="smoke-call-1", **{"x-codex-turn-metadata": turn})}},
        hdr("tools/call", "get_item"),
    )
    res = ((parse_body(r) or {}).get("result")) or {}
    sc = res.get("structuredContent") or {}
    rep.check(f"{tag} tools/call get_item", r.status_code == 200 and res.get("isError") is False and sc.get("id") == "T-50", {"isError": res.get("isError"), "id": sc.get("id")})
    r = await raw.post(tag, url, {"jsonrpc": "2.0", "id": raw.nid(), "method": "tools/call", "params": {"name": "inbox", "arguments": {}, "_meta": modern_meta()}}, hdr("tools/call", "get_item"))
    err = ((parse_body(r) or {}).get("error")) or {}
    rep.check(f"{tag} Mcp-Name mismatch → 400 HeaderMismatch", r.status_code == 400 and err.get("code") == -32020, {"status": r.status_code, "code": err.get("code")})
    bad_meta = {**modern_meta(), PV_KEY: "2099-01-01"}
    h = {**hdr("tools/list"), "mcp-protocol-version": "2099-01-01"}
    r = await raw.post(tag, url, {"jsonrpc": "2.0", "id": raw.nid(), "method": "tools/list", "params": {"_meta": bad_meta}}, h)
    err = ((parse_body(r) or {}).get("error")) or {}
    supported = (err.get("data") or {}).get("supported") or []
    rep.check(
        f"{tag} unsupported version → -32022 listing both eras",
        r.status_code == 400 and err.get("code") == -32022 and "2026-07-28" in supported and LEGACY_VERSIONS <= set(supported),
        {"status": r.status_code, "code": err.get("code"), "supported": supported},
    )
    return tools


async def negative_auth(raw: Raw, rep: Report, url: str) -> None:
    r = await raw.c.post(url, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}, headers={"accept": ACCEPT, "mcp-protocol-version": "2025-06-18"})
    raw.rep.http.append({"label": "no-token", "url": url, "method": "tools/list", "status": r.status_code, "location": r.headers.get("location")})
    rep.check(f"no token {url} → 401 + WWW-Authenticate", r.status_code == 401 and r.headers.get("www-authenticate", "").startswith("Bearer"), {"status": r.status_code, "www": r.headers.get("www-authenticate")})
    big = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {"_meta": {"pad": "x" * (MAX_MCP_BODY + 1)}}}
    r = await raw.c.post(url, json=big, headers={"accept": ACCEPT, "mcp-protocol-version": "2025-06-18"})
    raw.rep.http.append({"label": "no-token-big", "url": url, "method": "tools/list", "status": r.status_code, "location": r.headers.get("location")})
    rep.check(f"no token + 64KB+ body {url} → 401 (auth before body)", r.status_code == 401, r.status_code)
    r = await raw.c.post(url, json=big, headers={"accept": ACCEPT, "mcp-protocol-version": "2025-06-18", "authorization": f"Bearer {raw.token}"})
    raw.rep.http.append({"label": "big-body", "url": url, "method": "tools/list", "status": r.status_code, "location": r.headers.get("location")})
    rep.check(f"64KB+ body {url} → 413", r.status_code == 413, r.status_code)


async def official_client(rep: Report, url: str, token: str, mode: str) -> dict[str, Any]:
    import httpx2
    from mcp.client import Client
    from mcp.client.streamable_http import streamable_http_client

    seen: list[int] = []

    async def on_response(resp: httpx2.Response) -> None:
        seen.append(resp.status_code)

    out: dict[str, Any] = {"url": url, "mode": mode}
    try:
        http = httpx2.AsyncClient(
            headers={"authorization": f"Bearer {token}"},
            timeout=httpx2.Timeout(30, read=60),
            event_hooks={"response": [on_response]},
        )
        async with http:
            async with Client(streamable_http_client(url, http_client=http), mode=mode) as c:
                out["protocol_version"] = c.protocol_version
                si = c.server_info
                out["server_info"] = {"name": si.name, "version": si.version} if si else None
                lt = await c.list_tools()
                names = [t.name for t in lt.tools]
                out["tools"] = len(names)
                res = await c.call_tool("team_status", {})
                out["call_is_error"] = res.is_error
                out["call_keys"] = sorted((res.structured_content or {}).keys())
    except Exception as e:  # noqa: BLE001
        out["error"] = f"{type(e).__name__}: {e}"
    out["http_statuses"] = seen
    expect = "2026-07-28" if mode == "auto" else None
    ok = (
        "error" not in out
        and out.get("tools") == 9
        and out.get("call_is_error") is False
        and not any(300 <= s < 400 for s in seen)
        and (expect is None or out.get("protocol_version") == expect)
        and (mode != "legacy" or out.get("protocol_version") in ("2025-06-18", "2025-11-25"))
    )
    rep.check(f"official mcp client mode={mode} {url}", ok, {k: v for k, v in out.items() if k != "url"})
    return out


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="http://127.0.0.1:8190")
    ap.add_argument("--token", default="tf_pat_dev_alice")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "out" / "smoke_mcp.json"))
    args = ap.parse_args()
    base = args.base.rstrip("/")
    urls = [f"{base}/mcp", f"{base}/mcp/"]
    rep = Report()
    hashes: dict[str, str] = {}
    async with httpx.AsyncClient(follow_redirects=False, timeout=30) as c:
        r = await c.get(f"{base}/healthz")
        rep.check("healthz", r.status_code == 200, r.json() if r.status_code == 200 else r.status_code)
        raw = Raw(c, rep, args.token)
        for url in urls:
            lt = await legacy_flow(raw, rep, url)
            if lt:
                hashes[f"legacy {url}"] = tools_hash(lt)
            mt = await modern_flow(raw, rep, url)
            if mt:
                hashes[f"modern {url}"] = tools_hash(mt)
            await negative_auth(raw, rep, url)
    rep.check("tools/list identical across eras and URLs", len(set(hashes.values())) == 1, hashes)
    redirects = [h for h in rep.http if 300 <= h["status"] < 400]
    rep.check("no 3xx on any raw request", not redirects, redirects or len(rep.http))
    official = []
    for url in urls:
        for mode in ("auto", "legacy"):
            official.append(await official_client(rep, url, args.token, mode))
    report = {
        "base": base,
        "ok": rep.ok,
        "passed": sum(c["ok"] for c in rep.checks),
        "failed": [c for c in rep.checks if not c["ok"]],
        "tools_sha256": next(iter(hashes.values()), None),
        "checks": rep.checks,
        "http": rep.http,
        "official_client": official,
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if rep.ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
