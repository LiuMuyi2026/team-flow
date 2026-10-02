"""HTTP 层鉴权：401 + WWW-Authenticate；human_only 403；DEV 端点默认关闭且要密钥（B1）、拒绝 PAT；
Origin；Cookie 被忽略；/mcp 先鉴权再读请求体、请求体上限 64KB（m7）；token 的表示（m2）；
应用内 REST 请求体上限 64KB（复审新问题 6）；TEAMFLOW_DEV_TOKENS 没有缺省令牌（复审新问题 8）。"""

from __future__ import annotations

import json

import httpx
import pytest

from teamflow_server import config
from teamflow_server.app import create_app
from teamflow_server.config import TokenRec, parse_tokens, token_id_of
from teamflow_server.gateway import MAX_MCP_BODY, MAX_REST_BODY, Gateway

from .conftest import ALICE, BOB, DEV_SECRET, TOKENS, agent, auth, dev_headers, read_log

MCP_BODY = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
MCP_HEADERS = {"accept": "application/json, text/event-stream", "mcp-protocol-version": "2025-06-18"}


@pytest.mark.parametrize("path", ["/mcp", "/mcp/"])
async def test_mcp_401_missing_token(client, path, log_path):
    r = await client.post(path, json=MCP_BODY, headers=MCP_HEADERS)
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == 'Bearer realm="teamflow"'
    assert r.json()["error"]["code"] == -32001
    rec = read_log(log_path)[-1]
    assert rec["st"] == 401 and rec["auth"] == "missing"
    assert "rpc" not in rec  # 未鉴权：请求体一个字节都没读（m7）


async def test_mcp_401_bad_token(client):
    r = await client.post("/mcp/", json=MCP_BODY, headers={**MCP_HEADERS, **auth("tf_pat_dev_mallory")})
    assert r.status_code == 401
    assert 'error="invalid_token"' in r.headers["www-authenticate"]


async def test_rest_401_and_shared_tokens(client):
    r = await client.get("/api/v1/me/inbox")
    assert r.status_code == 401 and r.headers["www-authenticate"].startswith("Bearer")
    assert r.json()["error"] == "unauthorized" and r.json()["message"]
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
    assert r.json()["error"] == "human_only"


async def test_dev_accept_rejects_pat_even_with_dev_header(client, svc):
    sec = {"x-teamflow-dev-secret": DEV_SECRET}
    full = {"v": 1, "sha": svc.tasks["T-52"].content_sha256, "seq": 1, "through": svc.page_view("T-52")["through"]}
    # DEV ONLY 端点：PAT 调用必须 403 human_only（即使密钥对）
    r = await client.post("/api/v1/dev/tasks/T-52:accept", headers={**auth(BOB), **sec}, json=full)
    assert r.status_code == 403 and r.json()["error"] == "human_only"
    r = await client.post("/api/v1/dev/tasks/T-52:accept", headers={**auth(BOB), **dev_headers("bob")}, json=full)
    assert r.status_code == 403 and r.json()["error"] == "human_only"
    # 无效的 PAT 也一样是 human_only，不泄露 token 是否有效
    r = await client.post("/api/v1/dev/tasks/T-52:accept", headers={**auth("tf_pat_x"), **dev_headers("bob")}, json=full)
    assert r.status_code == 403 and r.json()["error"] == "human_only"
    # 没有模拟的人类会话
    r = await client.post("/api/v1/dev/tasks/T-52:accept", headers=sec, json=full)
    assert r.status_code == 403 and r.json()["error"] == "human_only"
    assert svc.tasks["T-52"].assign_state == "pending"
    # 模拟的人类会话：成功
    r = await client.post("/api/v1/dev/tasks/T-52:accept", headers=dev_headers("bob"), json=full)
    assert r.status_code == 200, r.text
    assert svc.tasks["T-52"].assign_state == "accepted"


async def test_dev_endpoints_can_be_disabled(client, monkeypatch):
    monkeypatch.setenv("TEAMFLOW_DEV_ENDPOINTS", "0")
    r = await client.post("/api/v1/dev/tasks/T-52:accept", headers=dev_headers("bob"), json={})
    assert r.status_code == 404


# ---- B1：DEV 端点默认关闭、要密钥、dev/reset 同样受管 ----


def test_dev_switch_defaults_off(monkeypatch):
    monkeypatch.delenv("TEAMFLOW_DEV_ENDPOINTS", raising=False)
    monkeypatch.setenv("TEAMFLOW_DEV_SECRET", DEV_SECRET)
    assert config.dev_endpoints_enabled() is False
    assert config.dev_access_ok(DEV_SECRET) == (False, "closed")
    monkeypatch.setenv("TEAMFLOW_DEV_ENDPOINTS", "1")
    assert config.dev_access_ok(DEV_SECRET) == (True, "ok")
    assert config.dev_access_ok(None) == (False, "bad_secret")
    assert config.dev_access_ok(DEV_SECRET + "x") == (False, "bad_secret")
    monkeypatch.setenv("TEAMFLOW_DEV_SECRET", "")
    assert config.dev_access_ok("") == (False, "no_secret")
    monkeypatch.delenv("TEAMFLOW_DEV_SECRET")
    assert config.dev_access_ok(DEV_SECRET) == (False, "no_secret")


DEV_CALLS = [
    ("POST", "/api/v1/dev/tasks/T-52:accept"),
    ("POST", "/api/v1/dev/tasks/T-53:claim"),
    ("POST", "/api/v1/dev/tasks/T-51:forward"),
    ("POST", "/api/v1/dev/blockers/B-7:help"),
    ("GET", "/api/v1/dev/outbox"),
    ("GET", "/api/v1/dev/items/T-52"),
    ("POST", "/api/v1/dev/reset"),
]


@pytest.mark.parametrize("method,path", DEV_CALLS)
async def test_dev_endpoints_closed_by_default(client, svc, monkeypatch, log_path, method, path):
    """开关缺省：带着正确的密钥和人类头也是 404；dev/reset 不会清数据。"""
    monkeypatch.delenv("TEAMFLOW_DEV_ENDPOINTS", raising=False)
    svc.create_task(agent("alice", "claude_code"), "reset 之前的任务")
    before, n = svc.latest_event_id(), len(svc.tasks)
    r = await client.request(method, path, headers=dev_headers("bob"), json={})
    assert r.status_code == 404 and r.json()["error"] == "not_found"
    assert svc.latest_event_id() == before and len(svc.tasks) == n  # 没被 reset，也没发生别的人类动作
    assert read_log(log_path)[-1]["dev"] == "closed"


@pytest.mark.parametrize("method,path", DEV_CALLS)
async def test_dev_endpoints_need_secret(client, svc, monkeypatch, log_path, method, path):
    """开关打开，但没配密钥（一律 404）、没带密钥头或密钥不对（404）。"""
    before = svc.latest_event_id()
    r = await client.request(method, path, headers=dev_headers("bob", secret=None), json={})
    assert r.status_code == 404 and read_log(log_path)[-1]["dev"] == "bad_secret"
    r = await client.request(method, path, headers=dev_headers("bob", secret="guess"), json={})
    assert r.status_code == 404 and read_log(log_path)[-1]["dev"] == "bad_secret"
    monkeypatch.delenv("TEAMFLOW_DEV_SECRET")
    r = await client.request(method, path, headers=dev_headers("bob"), json={})
    assert r.status_code == 404 and read_log(log_path)[-1]["dev"] == "no_secret"
    assert svc.latest_event_id() == before
    assert DEV_SECRET not in log_path.read_text(encoding="utf-8")  # 密钥不进日志


async def test_dev_reset_guarded_by_switch_and_secret(client, svc):
    svc.create_task(agent("alice", "claude_code"), "会被 reset 清掉")
    n = len(svc.tasks)
    r = await client.post("/api/v1/dev/reset", headers=dev_headers("alice", secret="wrong"))
    assert r.status_code == 404 and len(svc.tasks) == n
    r = await client.post("/api/v1/dev/reset", headers={**dev_headers("alice"), **auth(ALICE)})
    assert r.status_code == 403 and len(svc.tasks) == n  # PAT 不能 reset
    r = await client.post("/api/v1/dev/reset", headers=dev_headers("alice"))
    assert r.status_code == 200 and len(svc.tasks) == n - 1


# ---- m7：/mcp 先鉴权再读请求体；请求体上限 64KB ----


class _Recv:
    """记录 receive() 有没有被调用的假 ASGI receive。"""

    def __init__(self, body: bytes, chunk: int = 0) -> None:
        self.calls = 0
        self.parts = [body[i : i + chunk] for i in range(0, len(body), chunk)] if chunk else [body]

    async def __call__(self):
        self.calls += 1
        if self.parts:
            part = self.parts.pop(0)
            return {"type": "http.request", "body": part, "more_body": bool(self.parts)}
        return {"type": "http.disconnect"}


async def _run_gateway(headers: dict[str, str], body: bytes, chunk: int = 0, path: str = "/mcp/"):
    reached = {"app": False, "after": None}

    async def app(scope, receive, send):  # 下游：读完请求体，回 200
        reached["app"] = True
        msg = await receive()
        assert msg["body"] == body and msg["more_body"] is False
        # 再调一次 receive（流式响应会这样等断开）：拿到的是原始 receive 的下一条，而不是无限递归回放
        reached["after"] = (await receive())["type"]
        await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"application/json")]})
        await send({"type": "http.response.body", "body": b"{}"})

    sent: list[dict] = []

    async def send(msg):
        sent.append(msg)

    recv = _Recv(body, chunk)
    scope = {
        "type": "http",
        "method": "POST",
        "path": path,
        "raw_path": path.encode(),
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": ("127.0.0.1", 1234),
    }
    await Gateway(app)(scope, recv, send)
    status = next(m["status"] for m in sent if m["type"] == "http.response.start")
    if reached["app"]:
        assert reached["after"] == "http.disconnect"
    return status, recv.calls, reached["app"]


async def test_mcp_unauthenticated_body_never_read():
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}).encode()
    for hdrs in ({}, {"authorization": "Bearer tf_pat_unknown"}):
        status, calls, reached = await _run_gateway({"content-length": str(len(body)), **hdrs}, body)
        assert status == 401 and calls == 0 and not reached


async def test_mcp_body_limit_64kb():
    big = b'{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{"pad":"' + b"x" * MAX_MCP_BODY + b'"}}'
    # Content-Length 超限：一个字节都不读，直接 413
    status, calls, reached = await _run_gateway({**auth(ALICE), "content-length": str(len(big))}, big)
    assert status == 413 and calls == 0 and not reached
    # 没有 Content-Length（分块传输）：读到超过 64KB 就 413
    status, calls, reached = await _run_gateway(auth(ALICE), big, chunk=8192)
    assert status == 413 and 0 < calls <= MAX_MCP_BODY // 8192 + 1 and not reached
    # 上限以内：照常交给下游
    ok = b'{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{"pad":"' + b"x" * (MAX_MCP_BODY - 200) + b'"}}'
    status, calls, reached = await _run_gateway({**auth(ALICE), "content-length": str(len(ok))}, ok, chunk=8192)
    assert status == 200 and reached


async def test_mcp_body_limit_end_to_end(client, log_path):
    pad = "x" * (MAX_MCP_BODY + 1)
    r = await client.post(
        "/mcp/",
        headers={**MCP_HEADERS, **auth(ALICE)},
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {"_meta": {"pad": pad}}},
    )
    assert r.status_code == 413 and r.json()["error"]["code"] == -32600
    assert read_log(log_path)[-1]["st"] == 413


# ---- 复审新问题 6：应用内 REST 请求体上限 64KB（先鉴权再读）----

REST_BODY_PATHS = [
    "/api/v1/tasks",
    "/api/v1/tasks/T-50:note",
    "/api/v1/tasks/T-50/comments",
    "/api/v1/blockers",
    "/api/v1/blockers/B-7:resolve",
    "/api/v1/hooks/session-start",
    "/api/v1/hooks/batch",
]


@pytest.mark.parametrize("path", REST_BODY_PATHS)
async def test_rest_body_limit_end_to_end(client, svc, log_path, path):
    big = {"title": "大请求体", "note": "x", "body": "x" * (MAX_REST_BODY + 1), "items": []}
    before = (svc.latest_event_id(), len(svc.tasks), len(svc.blockers))
    r = await client.post(path, json=big)  # 没带令牌：401，请求体一个字节都不读
    assert r.status_code == 401 and read_log(log_path)[-1]["auth"] == "missing"
    r = await client.post(path, headers=auth(BOB), json=big)
    assert r.status_code == 413
    body = r.json()
    assert body["error"] == "too_large" and body["max"] == MAX_REST_BODY == 64 * 1024 and "64KB" in body["message"]
    rec = read_log(log_path)[-1]
    assert rec["st"] == 413 and rec["body_limit"] == "content-length" and rec["tf_err"] == "too_large"
    assert (svc.latest_event_id(), len(svc.tasks), len(svc.blockers)) == before


async def test_rest_unauthenticated_body_never_read():
    body = json.dumps({"title": "x" * (MAX_REST_BODY + 1)}).encode()
    for hdrs in ({}, {"authorization": "Bearer tf_pat_unknown"}):
        status, calls, reached = await _run_gateway({"content-length": str(len(body)), **hdrs}, body, path="/api/v1/tasks")
        assert status == 401 and calls == 0 and not reached


async def test_rest_body_limit_chunked_and_within_limit():
    big = b'{"title": "x", "body": "' + b"x" * MAX_REST_BODY + b'"}'
    status, calls, reached = await _run_gateway({**auth(ALICE), "content-length": str(len(big))}, big, path="/api/v1/tasks")
    assert status == 413 and calls == 0 and not reached
    # 分块传输（没有 Content-Length）：读到超过 64KB 就 413，后面的块不再读
    status, calls, reached = await _run_gateway(auth(ALICE), big, chunk=8192, path="/api/v1/tasks")
    assert status == 413 and 0 < calls <= MAX_REST_BODY // 8192 + 1 and not reached
    # 上限以内：照常交给下游（分块读完后整段回放）
    ok = b'{"title": "x", "body": "' + b"x" * (MAX_REST_BODY - 100) + b'"}'
    status, calls, reached = await _run_gateway({**auth(ALICE), "content-length": str(len(ok))}, ok, chunk=8192, path="/api/v1/tasks")
    assert status == 200 and reached


async def test_dev_endpoint_body_limit_after_gate(client, svc, log_path):
    big = {"v": 1, "pad": "x" * (MAX_REST_BODY + 1)}
    r = await client.post("/api/v1/dev/tasks/T-52:accept", headers=dev_headers("bob", secret="wrong"), json=big)
    assert r.status_code == 404 and read_log(log_path)[-1]["dev"] == "bad_secret"  # 门没过：不读请求体
    r = await client.post("/api/v1/dev/tasks/T-52:accept", headers=dev_headers("bob"), json=big)
    assert r.status_code == 413 and r.json()["error"] == "too_large"
    assert svc.tasks["T-52"].assign_state == "pending"


async def test_normal_rest_bodies_unaffected(client, svc):
    r = await client.post("/api/v1/tasks", headers=auth(ALICE), json={"title": "正常大小", "body": "x" * 4000})
    assert r.status_code == 201, r.text
    items = [{"key": f"k{i}", "type": "turn_end", "session_id": "s-1", "repo": "github.com/acme/x"} for i in range(100)]
    r = await client.post("/api/v1/hooks/batch", headers=auth(BOB), json={"items": items})
    assert r.status_code == 200 and len(r.json()["results"]) == 100


# ---- 复审新问题 8：没有缺省令牌 ----


def test_no_default_tokens(monkeypatch):
    monkeypatch.delenv("TEAMFLOW_DEV_TOKENS")
    assert not hasattr(config, "DEFAULT_TOKENS")
    assert config.tokens() == {}
    hint = config.tokens_hint()
    assert hint and "TEAMFLOW_DEV_TOKENS" in hint and "401" in hint and "\n" not in hint and "tf_pat_dev" not in hint
    monkeypatch.setenv("TEAMFLOW_DEV_TOKENS", "  ")
    assert config.tokens() == {} and "没有设置" in config.tokens_hint()
    monkeypatch.setenv("TEAMFLOW_DEV_TOKENS", "garbage,tf_pat_x:alice,nope:bob:codex,tf_pat_y:bob:vim")
    assert config.tokens() == {} and "没有一条有效" in config.tokens_hint()
    monkeypatch.setenv("TEAMFLOW_DEV_TOKENS", TOKENS)
    assert config.tokens_hint() is None and len(config.tokens()) == 5


async def test_unset_tokens_means_all_401_and_startup_hint(monkeypatch, capsys):
    monkeypatch.delenv("TEAMFLOW_DEV_TOKENS")
    a = create_app()
    async with a.router.lifespan_context(a):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=a), base_url="http://127.0.0.1:8100") as c:
            for tok in ("tf_pat_dev_alice", "tf_pat_dev_bob", ALICE, BOB):  # 以前的缺省令牌也不行了
                r = await c.get("/api/v1/me/inbox", headers=auth(tok))
                assert r.status_code == 401 and r.json()["error"] == "unauthorized"
                r = await c.post("/api/v1/tasks", headers=auth(tok), json={"title": "冒用"})
                assert r.status_code == 401
                r = await c.post("/mcp/", json=MCP_BODY, headers={**MCP_HEADERS, **auth(tok)})
                assert r.status_code == 401
    err = capsys.readouterr().err
    lines = [line for line in err.splitlines() if "TEAMFLOW_DEV_TOKENS" in line]
    assert len(lines) == 1 and "401" in lines[0] and lines[0].startswith("teamflow-server:")
    assert "tf_pat_dev" not in err
    # 配好令牌就不提示
    monkeypatch.setenv("TEAMFLOW_DEV_TOKENS", TOKENS)
    a = create_app()
    async with a.router.lifespan_context(a):
        pass
    assert "TEAMFLOW_DEV_TOKENS" not in capsys.readouterr().err


# ---- m2：token 的表示 ----


def test_token_rec_repr_and_token_id_hide_token():
    recs = parse_tokens(TOKENS)
    for tok, rec in recs.items():
        assert tok not in repr(rec) and tok not in str(rec)
        assert rec.token_id == token_id_of(tok) and rec.token_id.startswith("tok_")
        assert tok[-6:] not in rec.token_id  # 不再用 token 末 6 位
    # 末 6 位相同的两枚 token 不会撞 token_id
    a, b = TokenRec("tf_pat_aaa_same12", "alice", "codex"), TokenRec("tf_pat_bbb_same12", "bob", "codex")
    assert a.token_id != b.token_id
    assert len({r.token_id for r in recs.values()}) == len(recs)


async def test_log_never_contains_tokens(client, log_path):
    await client.get("/api/v1/me/inbox", headers=auth(ALICE))
    await client.post("/mcp/", json=MCP_BODY, headers={**MCP_HEADERS, **auth(BOB)})
    await client.post("/mcp/", json=MCP_BODY, headers={**MCP_HEADERS, **auth("tf_pat_dev_mallory")})
    text = log_path.read_text(encoding="utf-8")
    for tok in (ALICE, BOB, "tf_pat_dev_mallory"):
        assert tok not in text


async def test_mcp_rejects_foreign_origin(client):
    r = await client.post("/mcp/", json=MCP_BODY, headers={**MCP_HEADERS, **auth(ALICE), "origin": "https://evil.example"})
    assert r.status_code == 403


async def test_mcp_ignores_cookie_header(client):
    # Cookie 不能替代 Bearer
    r = await client.post("/mcp/", json=MCP_BODY, headers={**MCP_HEADERS, "cookie": "tf_session=whatever"})
    assert r.status_code == 401
