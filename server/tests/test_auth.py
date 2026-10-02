"""HTTP 层鉴权：401 + WWW-Authenticate；human_only 403；DEV 端点拒绝 PAT；Origin；Cookie 被忽略。"""

from __future__ import annotations

import pytest

from .conftest import ALICE, BOB, auth, dev_headers, read_log

MCP_BODY = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
MCP_HEADERS = {"accept": "application/json, text/event-stream", "mcp-protocol-version": "2025-06-18"}


@pytest.mark.parametrize("path", ["/mcp", "/mcp/"])
async def test_mcp_401_missing_token(client, path, log_path):
    r = await client.post(path, json=MCP_BODY, headers=MCP_HEADERS)
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == 'Bearer realm="teamflow"'
    assert r.json()["error"]["code"] == -32001
    rec = read_log(log_path)[-1]
    assert rec["st"] == 401 and rec["auth"] == "missing" and rec["rpc"] == "tools/list"


async def test_mcp_401_bad_token(client):
    r = await client.post("/mcp/", json=MCP_BODY, headers={**MCP_HEADERS, **auth("tf_pat_dev_mallory")})
    assert r.status_code == 401
    assert 'error="invalid_token"' in r.headers["www-authenticate"]


async def test_rest_401_and_shared_tokens(client):
    r = await client.get("/api/v1/me/inbox")
    assert r.status_code == 401 and r.headers["www-authenticate"].startswith("Bearer")
    assert r.json()["err"] == "unauthorized"
    r = await client.get("/api/v1/me/inbox", headers={"authorization": "Basic Zm9vOmJhcg=="})
    assert r.status_code == 401
    r = await client.get("/api/v1/me/inbox", headers=auth(BOB))
    assert r.status_code == 200 and r.json()["me"] == "bob"
    r = await client.post("/api/v1/hooks/session-start", json={"client": "codex", "session": "s1"})
    assert r.status_code == 401


async def test_healthz_is_public(client):
    r = await client.get("/healthz")
    assert r.status_code == 200 and r.json()["ok"] is True


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", "/api/v1/tasks/T-52:accept"),
        ("POST", "/api/v1/tasks/T-52:decline"),
        ("POST", "/api/v1/tasks/T-52:transfer"),
        ("POST", "/api/v1/tasks/T-51:forward"),
        ("DELETE", "/api/v1/tasks/T-53"),
        ("POST", "/api/v1/blockers/B-7:help"),
        ("POST", "/api/v1/blockers/B-7:ask"),
    ],
)
async def test_human_only_endpoints_reject_pat(client, method, path):
    r = await client.request(method, path, headers=auth(BOB), json={})
    assert r.status_code == 403
    assert r.json()["err"] == "human_only"


async def test_dev_accept_rejects_pat_even_with_dev_header(client, svc):
    # DEV ONLY 端点：PAT 调用必须 403 human_only
    r = await client.post("/api/v1/dev/tasks/T-52:accept", headers=auth(BOB), json={})
    assert r.status_code == 403 and r.json()["err"] == "human_only"
    r = await client.post("/api/v1/dev/tasks/T-52:accept", headers={**auth(BOB), **dev_headers("bob")}, json={})
    assert r.status_code == 403 and r.json()["err"] == "human_only"
    # 无效的 PAT 也一样是 human_only，不泄露 token 是否有效
    r = await client.post("/api/v1/dev/tasks/T-52:accept", headers={**auth("tf_pat_x"), **dev_headers("bob")}, json={})
    assert r.status_code == 403 and r.json()["err"] == "human_only"
    # 没有模拟的人类会话
    r = await client.post("/api/v1/dev/tasks/T-52:accept", json={})
    assert r.status_code == 403 and r.json()["err"] == "human_only"
    assert svc.tasks["T-52"].assign_state == "pending"
    # 模拟的人类会话：成功
    r = await client.post("/api/v1/dev/tasks/T-52:accept", headers=dev_headers("bob"), json={"v": 1, "seq": 1})
    assert r.status_code == 200, r.text
    assert svc.tasks["T-52"].assign_state == "accepted"


async def test_dev_endpoints_can_be_disabled(client, monkeypatch):
    monkeypatch.setenv("TEAMFLOW_DEV_ENDPOINTS", "0")
    r = await client.post("/api/v1/dev/tasks/T-52:accept", headers=dev_headers("bob"), json={})
    assert r.status_code == 404


async def test_mcp_rejects_foreign_origin(client):
    r = await client.post("/mcp/", json=MCP_BODY, headers={**MCP_HEADERS, **auth(ALICE), "origin": "https://evil.example"})
    assert r.status_code == 403


async def test_mcp_ignores_cookie_header(client):
    # Cookie 不能替代 Bearer
    r = await client.post("/mcp/", json=MCP_BODY, headers={**MCP_HEADERS, "cookie": "tf_session=whatever"})
    assert r.status_code == 401
