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
- /mcp 请求体超过 64KB 返回 413，不带令牌的大请求体直接 401（先鉴权再读请求体，m7）；
- 应用内 REST 同样：64KB 以上带令牌 413 too_large，不带令牌 401（复审新问题 6）；
- 令牌没有缺省值（复审新问题 8）：以前写在仓库里的 tf_pat_dev_alice 等一律 401（除非服务端显式配了它们）。
再用官方 mcp 2.2.0 客户端（auto 与 legacy 两种模式）交叉验证一次，并记录它见到的所有 HTTP 状态码。

Claude Code 会话归属（D40，只要 --token，它必须是 Claude Code 令牌）：hooks/session-start 登记一个新会话 → 带
_meta["claudecode/toolUseId"] 发布并开始一个指派给自己的任务（成员级）→ hooks/batch 上报 tool_map（PostToolUse 写的那条）
→ 这次调用的事件补成会话级；同 key 重放 409；格式不合格 422。给了 --peer-token 时再断言：对方的 /status 里能看到
"我 · Claude Code · 会话 xxxx 在做 T-xx"，对方 token 把映射挂到我的会话上 403 ignored。最后取消任务、结束会话。

可选的 DEV 段（复审新问题 1）：给了 --dev-secret 和 --peer-token 时，模拟"bob 打开 T-52 详情页 → alice 的 agent
写评论 → bob 点接受"：不带 through 400、through 超过最大事件 400、带页面上的 through 200；之后 bob 的 agent
读 T-52 能看到正文、看不到那条评论（peer_agent_text n=1）。最后 dev/reset 恢复种子数据。需要服务端用种子数据启动，
--token 是 alice 的 Claude Code 令牌、--peer-token 是 bob 的令牌，并打开 DEV 端点。

用法（令牌没有缺省值，必须显式给）：
  .venv/bin/python spike/smoke_mcp.py --base http://127.0.0.1:8190 --token "$TF_A" \\
      [--peer-token "$TF_B" --dev-secret "$TEAMFLOW_DEV_SECRET"] [--out spike/out/smoke_mcp.json]
  也可以用环境变量 TEAMFLOW_SMOKE_TOKEN、TEAMFLOW_SMOKE_PEER_TOKEN、TEAMFLOW_DEV_SECRET。
退出码：全部通过为 0，否则为 1（缺令牌为 2）。报告是 JSON（同时打印到 stdout），不含令牌和密钥。
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import secrets
import time
import uuid
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


async def rest_checks(raw: Raw, rep: Report, base: str, token_was_default: bool) -> None:
    """应用内 REST：请求体上限 64KB（先鉴权再读）；以前的缺省令牌不再有效。"""
    url = f"{base}/api/v1/tasks"
    big = {"title": "smoke 大请求体", "body": "x" * (MAX_MCP_BODY + 1)}
    r = await raw.c.post(url, json=big)
    raw.rep.http.append({"label": "rest-no-token-big", "url": url, "method": "POST", "status": r.status_code})
    rep.check("REST no token + 64KB+ body → 401 (auth before body)", r.status_code == 401, r.status_code)
    r = await raw.c.post(url, json=big, headers={"authorization": f"Bearer {raw.token}"})
    raw.rep.http.append({"label": "rest-big-body", "url": url, "method": "POST", "status": r.status_code})
    body = parse_body(r) or {}
    rep.check(
        "REST 64KB+ body → 413 too_large",
        r.status_code == 413 and body.get("error") == "too_large" and body.get("max") == MAX_MCP_BODY,
        {"status": r.status_code, "error": body.get("error"), "max": body.get("max")},
    )
    if not token_was_default:
        r = await raw.c.get(f"{base}/api/v1/me/inbox", headers={"authorization": "Bearer tf_pat_dev_alice"})
        rep.check("former default token tf_pat_dev_alice → 401", r.status_code == 401, r.status_code)


async def modern_call(c: httpx.AsyncClient, url: str, token: str, name: str, args: dict[str, Any]) -> dict[str, Any]:
    h = {
        "accept": ACCEPT,
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "mcp-protocol-version": "2026-07-28",
        "mcp-method": "tools/call",
        "mcp-name": name,
    }
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": args, "_meta": modern_meta()}}
    r = await c.post(url, json=body, headers=h)
    return ((parse_body(r) or {}).get("result")) or {}


async def modern_call_meta(c: httpx.AsyncClient, url: str, token: str, name: str, args: dict[str, Any], **meta: Any) -> dict[str, Any]:
    h = {
        "accept": ACCEPT,
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "mcp-protocol-version": "2026-07-28",
        "mcp-method": "tools/call",
        "mcp-name": name,
    }
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": args, "_meta": modern_meta(**meta)}}
    r = await c.post(url, json=body, headers=h)
    return ((parse_body(r) or {}).get("result")) or {}


async def tool_map_flow(raw: Raw, rep: Report, base: str, peer_token: str | None) -> None:
    """D40：PostToolUse 的 tool_map 把 Claude Code 的成员级调用补成会话级（跨包约定见 server/README.md）。"""
    c = raw.c
    mcp = f"{base}/mcp/"
    tok = {"authorization": f"Bearer {raw.token}"}
    sid = str(uuid.uuid4())
    tag = sid.replace("-", "")[:8]
    r = await c.post(f"{base}/api/v1/hooks/session-start", headers=tok, json={"client": "claude", "session_id": sid, "source": "startup"})
    me = (parse_body(r) or {}).get("me")
    rep.check("tool_map: session-start registers a Claude Code session", r.status_code == 200 and bool(me), r.status_code)
    if r.status_code != 200 or not me:
        return
    res = await modern_call(c, mcp, raw.token, "create_task", {"title": "smoke 会话归属", "assignee": me})
    tid = (res.get("structuredContent") or {}).get("id")
    rep.check("tool_map: create a task assigned to myself", res.get("isError") is False and bool(tid), res.get("structuredContent"))
    if not tid:
        return
    tu = "toolu_01" + secrets.token_hex(11)
    res = await modern_call_meta(c, mcp, raw.token, "claim_task", {"id": tid}, **{"claudecode/toolUseId": tu})
    rep.check("tool_map: claim_task with claudecode/toolUseId", res.get("isError") is False and (res.get("structuredContent") or {}).get("st") == "doing", res.get("structuredContent"))

    async def batch(token: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rr = await c.post(f"{base}/api/v1/hooks/batch", headers={"authorization": f"Bearer {token}"}, json={"items": items})
        return ((parse_body(rr) or {}).get("results")) or []

    async def my_sess() -> list[dict[str, Any]] | None:
        if not peer_token:
            return None
        rr = await c.get(f"{base}/api/v1/status", headers={"authorization": f"Bearer {peer_token}"})
        row = next((o for o in (parse_body(rr) or {}).get("others") or [] if o.get("h") == me), {})
        return row.get("sess")

    before = await my_sess()
    if before is not None:
        rep.check("tool_map: before the mapping the peer sees member level only", not [x for x in before if x.get("task") == tid], before)
        out = await batch(peer_token, [{"type": "tool_map", "key": f"smoke-forge-{tu}", "session_id": sid, "tool_use_id": tu, "tool": "claim_task"}])
        got = [(x.get("st"), x.get("status")) for x in out]
        rep.check("tool_map: peer token mapping onto my session → 403 ignored", got == [("ignored", 403)], got)
    key = f"smoke-tm-{tu}"
    item = {"type": "tool_map", "key": key, "session_id": sid, "tool_use_id": tu, "tool": "claim_task"}
    out = await batch(raw.token, [item])
    got = [(x.get("st"), x.get("status"), x.get("n")) for x in out]
    rep.check("tool_map: mapping upgrades the call's events to the session", got == [("ok", 200, 1)], got)
    out = await batch(raw.token, [item])
    got = [(x.get("st"), x.get("status")) for x in out]
    rep.check("tool_map: replay of the same key → 409 dup", got == [("dup", 409)], got)
    out = await batch(raw.token, [{**item, "key": key + "-bad", "tool_use_id": "toolu_x"}])
    got = [(x.get("st"), x.get("status"), x.get("err")) for x in out]
    rep.check("tool_map: malformed tool_use_id → 422 bad", got == [("bad", 422, "tool_use_id")], got)
    after = await my_sess()
    if after is not None:
        want = {"client": "claude_code", "s": tag, "task": tid}
        rep.check("tool_map: peer /status shows me · Claude Code · session tag · task", want in after, after)
    res = await modern_call(c, mcp, raw.token, "update_task", {"id": tid, "status": "canceled", "note": "smoke 用完取消"})
    rep.check("tool_map: cleanup cancels the task", res.get("isError") is False, res.get("structuredContent"))
    out = await batch(raw.token, [{"type": "end", "key": f"smoke-end-{sid}", "session_id": sid, "reason": "other"}])
    rep.check("tool_map: cleanup ends the session", [x.get("st") for x in out] == ["ok"], out)


async def dev_through_flow(raw: Raw, rep: Report, base: str, peer_token: str, secret: str) -> None:
    """复审新问题 1：页面渲染后、点按钮前对方 agent 写的评论不放给本人的 agent；through 必填。"""
    c = raw.c
    mcp = f"{base}/mcp/"
    bob = {"x-teamflow-dev-secret": secret, "x-teamflow-dev-human": "bob"}
    path = f"{base}/api/v1/dev/tasks/T-52:accept"
    r = await c.get(f"{base}/api/v1/dev/items/T-52", headers=bob)
    seen = parse_body(r) or {}
    rep.check(
        "DEV detail page T-52 gives v, sha, seq, through",
        r.status_code == 200 and {"v", "sha", "seq", "through"} <= set(seen) and isinstance(seen.get("through"), int),
        {"status": r.status_code, "keys": sorted(seen)},
    )
    if r.status_code != 200:
        return
    late = "smoke：页面渲染之后才写的评论"
    res = await modern_call(c, mcp, raw.token, "comment", {"target": "T-52", "body": late})
    rep.check("alice's agent comments on T-52 after bob's page rendered", res.get("isError") is False, res.get("structuredContent"))
    form = {k: seen.get(k) for k in ("v", "sha", "seq")}
    r = await c.post(path, headers=bob, json=form)
    body = parse_body(r) or {}
    rep.check("DEV accept without through → 400 invalid", r.status_code == 400 and body.get("error") == "invalid", {"status": r.status_code, "error": body.get("error")})
    latest = ((parse_body(await c.get(f"{base}/healthz")) or {}).get("events")) or 0
    r = await c.post(path, headers=bob, json={**form, "through": latest + 1})
    body = parse_body(r) or {}
    rep.check("DEV accept with through > latest → 400 invalid", r.status_code == 400 and body.get("error") == "invalid", {"status": r.status_code, "error": body.get("error")})
    r = await c.post(path, headers=bob, json={**form, "through": seen["through"]})
    rep.check("DEV accept with the page's through → 200", r.status_code == 200, r.status_code)
    res = await modern_call(c, mcp, peer_token, "get_item", {"id": "T-52", "events": 10})
    sc = res.get("structuredContent") or {}
    texts = " ".join(e.get("t", "") for e in sc.get("ev") or [])
    held = [e.get("n") for e in sc.get("ev") or [] if e.get("withheld") == "peer_agent_text"]
    rep.check(
        "bob's agent sees accepted body but not the comment written after render",
        "content" in sc and late not in texts and held == [1],
        {"content": "content" in sc, "late_visible": late in texts, "held": held},
    )
    r = await c.post(f"{base}/api/v1/dev/reset", headers=bob)
    rep.check("DEV reset restores seed", r.status_code == 200, r.status_code)


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
    ap.add_argument("--token", default=os.environ.get("TEAMFLOW_SMOKE_TOKEN"), help="alice 的 Claude Code 令牌（没有缺省值）")
    ap.add_argument("--peer-token", default=os.environ.get("TEAMFLOW_SMOKE_PEER_TOKEN"), help="bob 的令牌（DEV 段用）")
    ap.add_argument("--dev-secret", default=os.environ.get("TEAMFLOW_DEV_SECRET"), help="DEV 端点密钥（DEV 段用）")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "out" / "smoke_mcp.json"))
    args = ap.parse_args()
    if not args.token:
        print("smoke_mcp: 需要 --token 或 TEAMFLOW_SMOKE_TOKEN（服务端 TEAMFLOW_DEV_TOKENS 里配的令牌；没有缺省值）", file=sys.stderr)
        return 2
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
        await rest_checks(raw, rep, base, token_was_default=args.token == "tf_pat_dev_alice")
        skipped: list[str] = []
        await tool_map_flow(raw, rep, base, args.peer_token)
        if not args.peer_token:
            skipped.append("tool_map_flow 的对方视角与伪造用例（需要 --peer-token）")
        if args.peer_token and args.dev_secret:
            await dev_through_flow(raw, rep, base, args.peer_token, args.dev_secret)
        else:
            skipped.append("dev_through_flow（需要 --peer-token 和 --dev-secret）")
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
        "skipped": skipped,
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
