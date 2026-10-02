"""两代协议握手、9 个工具与 annotations、无 3xx、观测日志。"""

from __future__ import annotations

import json

import pytest

from teamflow_server.mcp_server import INSTRUCTIONS, TOOL_ORDER

from .conftest import ALICE, BOB, LegacyMcp, ModernMcp, parse_body, read_log

READ_TOOLS = {"inbox", "list_tasks", "get_item", "team_status"}
WRITE_TOOLS = {"create_task", "claim_task", "update_task", "report_blocker", "comment"}


def assert_tools(tools: list[dict]) -> None:
    assert [t["name"] for t in tools] == list(TOOL_ORDER)
    assert len(tools) == 9
    by = {t["name"]: t for t in tools}
    for name in READ_TOOLS:
        ann = by[name]["annotations"]
        assert ann["readOnlyHint"] is True
        assert ann["openWorldHint"] is False
        assert "idempotentHint" not in ann
    for name in WRITE_TOOLS:
        ann = by[name]["annotations"]
        assert ann["readOnlyHint"] is False
        assert ann["destructiveHint"] is False
        assert ann["openWorldHint"] is False
        assert ann.get("idempotentHint", False) is (name == "claim_task")
    for name, t in by.items():
        meta = t.get("_meta") or {}
        if name in ("inbox", "update_task"):
            assert meta == {"anthropic/alwaysLoad": True}
        else:
            assert "anthropic/alwaysLoad" not in meta
    # 关键参数
    assert set(by["list_tasks"]["inputSchema"]["properties"]["view"]["enum"]) == {"pool", "mine", "doing", "done", "all"}
    assert by["create_task"]["inputSchema"]["properties"]["title"]["maxLength"] == 120
    assert by["comment"]["inputSchema"]["required"] == ["target", "body"]


@pytest.mark.parametrize("path", ["/mcp", "/mcp/"])
async def test_legacy_handshake_list_call(client, path, log_path):
    m = LegacyMcp(client, ALICE, path=path)
    r = await m.initialize()
    assert r.status_code == 200, r.text
    res = parse_body(r)["result"]
    assert res["protocolVersion"] == "2025-06-18"
    assert res["serverInfo"]["name"] == "teamflow"
    assert res["instructions"] == INSTRUCTIONS
    assert "mcp-session-id" not in r.headers  # 无状态：不发会话 ID

    r = await m.rpc("tools/list")
    assert r.status_code == 200
    assert_tools(parse_body(r)["result"]["tools"])

    res = await m.call("inbox", {})
    assert res["isError"] is False
    assert res["structuredContent"]["me"] == "alice"

    log = read_log(log_path)
    init = [x for x in log if x.get("rpc") == "initialize"][-1]
    assert init["gen"] == "legacy" and init["pv"] == "2025-06-18" and init["pv_src"] == "initialize"
    assert init["ci"] == {"name": "pytest-legacy", "version": "1"}
    assert init["h"] == "alice" and init["path"] == path
    call = [x for x in log if x.get("rpc") == "tools/call"][-1]
    assert call["tool"] == "inbox" and call["route"] == "legacy" and call["hpv"] == "2025-06-18"
    assert call["ci_last"]["ci"]["name"] == "pytest-legacy"
    assert all(300 > x["st"] or x["st"] >= 400 for x in log)


@pytest.mark.parametrize("path", ["/mcp", "/mcp/"])
async def test_modern_discover_list_call(client, path, log_path):
    m = ModernMcp(client, BOB, path=path)
    r = await m.rpc("server/discover")
    assert r.status_code == 200, r.text
    res = parse_body(r)["result"]
    assert "2026-07-28" in res["supportedVersions"]
    assert res["instructions"] == INSTRUCTIONS
    assert res["_meta"]["io.modelcontextprotocol/serverInfo"]["name"] == "teamflow"

    r = await m.rpc("tools/list")
    assert r.status_code == 200
    res = parse_body(r)["result"]
    assert_tools(res["tools"])
    assert isinstance(res["ttlMs"], int) and res["cacheScope"] in ("private", "public")
    assert res["resultType"] == "complete"

    turn = {"session_id": "019a-sess", "thread_id": "019a-thread", "turn_id": "019a-turn", "repo_root": "/x"}
    res = await m.call("team_status", {}, meta={"callId": "call_123", "x-codex-turn-metadata": turn})
    assert res["isError"] is False
    assert res["structuredContent"]["others"][0]["h"] == "alice"

    log = read_log(log_path)
    disc = [x for x in log if x.get("rpc") == "server/discover"][-1]
    assert disc["gen"] == "modern" and disc["pv"] == "2026-07-28" and disc["pv_src"] == "meta" and disc["route"] == "modern"
    assert disc["h_method"] == "server/discover"
    call = [x for x in log if x.get("rpc") == "tools/call"][-1]
    assert call["tool"] == "team_status" and call["h_name"] == "team_status"
    assert call["call_id"] == "call_123"
    # m2：x-codex-turn-metadata 只留 session_id、thread_id、turn_id，repo_root 等丢弃
    assert call["codex_turn"] == {"session_id": "019a-sess", "thread_id": "019a-thread", "turn_id": "019a-turn"}
    assert "/x" not in json.dumps(log, ensure_ascii=False)
    assert "x-codex-turn-metadata" in call["meta_keys"]
    assert call["ci"] == {"name": "pytest-modern", "version": "1"}
    assert call["h"] == "bob" and call["tok_client"] == "codex"


async def test_no_redirects_any_path(client):
    for path in ("/mcp", "/mcp/"):
        for body in (
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "x", "version": "1"}}},
        ):
            r = await client.post(path, json=body, headers={"accept": "application/json, text/event-stream", "authorization": f"Bearer {ALICE}"})
            assert r.status_code == 200
            assert "location" not in r.headers


async def test_modern_header_mismatch_and_unsupported_version(client):
    m = ModernMcp(client, ALICE)
    r = await m.rpc("tools/call", {"name": "inbox", "arguments": {}}, name="get_item")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == -32020  # HeaderMismatch
    r = await m.rpc("tools/list", headers={"mcp-method": "tools/call"})
    assert r.status_code == 400 and r.json()["error"]["code"] == -32020
    r = await client.post(
        "/mcp/",
        headers={"accept": "application/json, text/event-stream", "authorization": f"Bearer {ALICE}", "mcp-protocol-version": "2099-01-01", "mcp-method": "tools/list"},
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {"_meta": {"io.modelcontextprotocol/protocolVersion": "2099-01-01", "io.modelcontextprotocol/clientCapabilities": {}}}},
    )
    assert r.status_code == 400
    err = r.json()["error"]
    assert err["code"] == -32022 and "2026-07-28" in err["data"]["supported"]


async def test_modern_rejects_initialize_without_meta(client):
    """新代头 + initialize 会被新代处理器拒绝（400），旧代客户端不会这样发。"""
    r = await client.post(
        "/mcp/",
        headers={"accept": "application/json, text/event-stream", "authorization": f"Bearer {ALICE}", "mcp-protocol-version": "2026-07-28", "mcp-method": "initialize"},
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2026-07-28", "capabilities": {}, "clientInfo": {"name": "x", "version": "1"}}},
    )
    assert r.status_code == 400


async def test_legacy_2025_11_25_also_served(client):
    m = LegacyMcp(client, ALICE, version="2025-11-25")
    r = await m.initialize()
    assert parse_body(r)["result"]["protocolVersion"] == "2025-11-25"
    r = await m.rpc("tools/list")
    assert len(parse_body(r)["result"]["tools"]) == 9


async def test_get_and_delete_on_mcp_not_redirected(client):
    r = await client.get("/mcp", headers={"accept": "text/event-stream", "authorization": f"Bearer {ALICE}"})
    assert r.status_code == 405
    r = await client.delete("/mcp/", headers={"authorization": f"Bearer {ALICE}"})
    assert r.status_code < 300 or r.status_code >= 400


async def test_tools_list_identical_across_eras_and_users(client):
    a = LegacyMcp(client, ALICE)
    await a.initialize()
    la = parse_body(await a.rpc("tools/list"))["result"]["tools"]
    b = ModernMcp(client, BOB)
    lb = parse_body(await b.rpc("tools/list"))["result"]["tools"]
    norm = lambda ts: [{k: v for k, v in t.items()} for t in ts]  # noqa: E731
    assert norm(la) == norm(lb)


async def test_official_client_both_modes(app):
    """用官方 mcp 2.2.0 客户端（in-process ASGI 传输）交叉验证 auto（新代）和 legacy 两种模式。"""
    import httpx2
    from mcp.client import Client
    from mcp.client.streamable_http import streamable_http_client

    for mode, expect in (("auto", "2026-07-28"), ("legacy", "2025-11-25")):
        http = httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), headers={"authorization": f"Bearer {ALICE}"})
        async with http:
            async with Client(streamable_http_client("http://127.0.0.1:8100/mcp/", http_client=http), mode=mode) as c:
                assert c.protocol_version == expect
                tools = await c.list_tools()
                assert len(tools.tools) == 9
                res = await c.call_tool("get_item", {"id": "T-50"})
                assert res.is_error is False
                assert res.structured_content["id"] == "T-50"


# ---- m6：两代协议的能力宣告与版本列表 ----

LEGACY_VERSIONS = {"2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"}


def _no_list_changed(obj) -> bool:
    if isinstance(obj, dict):
        return "listChanged" not in obj and all(_no_list_changed(v) for v in obj.values())
    if isinstance(obj, list):
        return all(_no_list_changed(v) for v in obj)
    return True


@pytest.mark.parametrize("version", ["2025-06-18", "2025-11-25"])
async def test_legacy_initialize_capabilities_only_tools_no_list_changed(client, version):
    m = LegacyMcp(client, ALICE, version=version)
    caps = parse_body(await m.initialize())["result"]["capabilities"]
    assert caps == {"tools": {}}
    assert _no_list_changed(caps)
    # GET（通知流）仍是 405：所以不能宣告 listChanged
    r = await client.get("/mcp/", headers={"accept": "text/event-stream", "authorization": f"Bearer {ALICE}", "mcp-protocol-version": version})
    assert r.status_code == 405


async def test_modern_discover_lists_both_eras_and_only_tools(client):
    m = ModernMcp(client, BOB)
    res = parse_body(await m.rpc("server/discover"))["result"]
    assert res["supportedVersions"][0] == "2026-07-28"
    assert LEGACY_VERSIONS <= set(res["supportedVersions"])
    caps = res["capabilities"]
    assert caps == {"tools": {}}
    for k in ("logging", "prompts", "resources", "extensions", "completions", "experimental"):
        assert k not in caps


async def test_unsupported_version_lists_both_eras(client, log_path):
    h = {"accept": "application/json, text/event-stream", "authorization": f"Bearer {ALICE}", "mcp-protocol-version": "2099-01-01"}
    meta = {"io.modelcontextprotocol/protocolVersion": "2099-01-01", "io.modelcontextprotocol/clientCapabilities": {}}
    # 请求
    r = await client.post("/mcp/", headers={**h, "mcp-method": "tools/list"}, json={"jsonrpc": "2.0", "id": 9, "method": "tools/list", "params": {"_meta": meta}})
    assert r.status_code == 400
    assert int(r.headers["content-length"]) == len(r.content)  # 改写后长度正确
    err = r.json()["error"]
    assert err["code"] == -32022 and r.json()["id"] == 9
    assert err["data"]["supported"][0] == "2026-07-28" and LEGACY_VERSIONS <= set(err["data"]["supported"])
    assert err["data"]["requested"] == "2099-01-01"
    rec = read_log(log_path)[-1]
    assert rec["st"] == 400 and rec["rpc_err"] == -32022
    # 通知（没有 id）
    r = await client.post("/mcp/", headers={**h, "mcp-method": "notifications/initialized"}, json={"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert r.status_code == 400
    assert LEGACY_VERSIONS <= set(r.json()["error"]["data"]["supported"])
    # 其他 400（-32020 头不一致）原样转发
    m = ModernMcp(client, ALICE)
    r = await m.rpc("tools/call", {"name": "inbox", "arguments": {}}, name="get_item")
    assert r.status_code == 400 and r.json()["error"]["code"] == -32020 and int(r.headers["content-length"]) == len(r.content)


def test_augment_unsupported_version_only_touches_32022():
    from teamflow_server.gateway import augment_unsupported_version

    assert augment_unsupported_version(b'{"jsonrpc":"2.0","id":1,"error":{"code":-32020,"message":"x"}}') is None
    assert augment_unsupported_version(b"not json") is None
    out = json.loads(augment_unsupported_version(b'{"jsonrpc":"2.0","id":1,"error":{"code":-32022,"message":"x","data":{"supported":["2026-07-28"],"requested":"x"}}}'))
    assert out["error"]["data"]["supported"] == ["2026-07-28", "2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"]
