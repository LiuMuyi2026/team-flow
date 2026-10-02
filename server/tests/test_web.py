"""网页人类会话与网页 API（本地开发模式）。

- 本地登录：一次性、过期、绑定成员、Origin、非本机来源 / 转发头 / 非本机 Host 一律 404、生产配置 404；
  登录码只存 sha256；devlogin 命令要终端。
- 网页 API：只认人类会话 cookie；带 PAT（任何 Authorization 头）403 human_only；没会话 401；
  写请求 CSRF（Origin + X-CSRF-Token 双提交）不过 403 csrf；cookie 属性。
- 人类动作走 service 的同一套规则：缺字段 400、旧版本 409、through 只放页面渲染时看到的动态。
- 静态单页：/ 与前端路由回退 index.html，CSP script-src 'self'；/api 未知路径仍是 JSON 404、405 不变。
"""

from __future__ import annotations

import json
import os
import stat
import sys
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from teamflow_server import config, devlogin, webauth
from teamflow_server.app import create_app

from .conftest import ALICE, BOB, agent, auth

BASE = "http://127.0.0.1:8100"
LOCAL = ("127.0.0.1", 50123)


def mk(app, base: str = BASE, client: tuple[str, int] = LOCAL) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=client), base_url=base, follow_redirects=False)


async def login(c: httpx.AsyncClient, handle: str, base: str = BASE) -> dict[str, str]:
    """用一次性登录码登录，返回写请求要带的头（Origin + X-CSRF-Token）。"""
    code = devlogin.issue(handle)
    r = await c.post("/dev/login", data={"code": code, "as": handle}, headers={"origin": base})
    assert r.status_code == 303, r.text
    me = await c.get("/api/v1/web/me")
    assert me.status_code == 200, me.text
    assert me.json()["me"] == handle
    return {"origin": base, "x-csrf-token": me.json()["csrf"]}


@pytest.fixture
async def web_as(app):
    made: list[httpx.AsyncClient] = []

    async def make(handle: str, base: str = BASE) -> tuple[httpx.AsyncClient, dict[str, str]]:
        c = mk(app, base)
        made.append(c)
        return c, await login(c, handle, base)

    yield make
    for c in made:
        await c.aclose()


def page_fields(detail: dict[str, Any], *names: str) -> dict[str, Any]:
    return {k: detail["page"][k] for k in names}


def set_cookie_attrs(r: httpx.Response) -> dict[str, dict[str, str | bool]]:
    out: dict[str, dict[str, str | bool]] = {}
    for raw in r.headers.get_list("set-cookie"):
        parts = [p.strip() for p in raw.split(";")]
        name, _, value = parts[0].partition("=")
        attrs: dict[str, str | bool] = {"value": value}
        for p in parts[1:]:
            k, eq, v = p.partition("=")
            attrs[k.lower()] = v if eq else True
        out[name] = attrs
    return out


# ---------------------------------------------------------------------------
# 本地登录
# ---------------------------------------------------------------------------


async def test_startup_prints_links_and_stores_only_hashes(monkeypatch, capsys, tmp_path):
    state = tmp_path / "fresh-state"
    monkeypatch.setenv("TEAMFLOW_STATE", str(state))
    a = create_app()
    async with a.router.lifespan_context(a):
        err = capsys.readouterr().err
        links = {}
        for line in err.splitlines():
            if "/dev/login?" in line:
                url = line.split()[-1]
                q = parse_qs(urlsplit(url).query)
                links[q["as"][0]] = (url, q["code"][0])
        assert set(links) == {"alice", "bob"}
        assert all(line.startswith("teamflow-server:") for line in err.splitlines() if "/dev/login" in line)
        # 两个人分别用 127.0.0.1 和 localhost：同一个浏览器里 cookie 互不影响
        assert urlsplit(links["alice"][0]).hostname == "127.0.0.1"
        assert urlsplit(links["bob"][0]).hostname == "localhost"
        assert urlsplit(links["bob"][0]).port == 8100
        # 状态目录：0700、自带 .gitignore；登录码文件 0600，只存 sha256，没有明文
        assert stat.S_IMODE(state.stat().st_mode) == 0o700
        assert (state / ".gitignore").read_text(encoding="utf-8").strip().endswith("*")
        codes_file = state / devlogin.CODES_FILE
        assert stat.S_IMODE(codes_file.stat().st_mode) == 0o600
        text = codes_file.read_text(encoding="utf-8")
        for _, code in links.values():
            assert code not in text
        assert len(json.loads(text)["codes"]) == 2
        info = json.loads((state / devlogin.SERVER_FILE).read_text(encoding="utf-8"))
        assert stat.S_IMODE((state / devlogin.SERVER_FILE).stat().st_mode) == 0o600
        assert info["members"] == ["alice", "bob"] and info["base"] == BASE and info["pid"] == os.getpid()
        # 打印出来的链接能直接用（bob 的是 localhost）
        async with mk(a, "http://localhost:8100") as c:
            r = await c.get("/dev/login", params={"code": links["bob"][1], "as": "bob"})
            assert r.status_code == 200 and "bob（Bob）" in r.text
            r = await c.post("/dev/login", data={"code": links["bob"][1], "as": "bob"}, headers={"origin": "http://localhost:8100"})
            assert r.status_code == 303 and r.headers["location"] == "/"
            assert (await c.get("/api/v1/web/me")).json()["me"] == "bob"
    # 重启服务端：旧码全部作废
    a2 = create_app()
    async with a2.router.lifespan_context(a2):
        async with mk(a2) as c:
            r = await c.post("/dev/login", data={"code": links["alice"][1], "as": "alice"}, headers={"origin": BASE})
            assert r.status_code == 403


async def test_base_url_follows_port(monkeypatch):
    monkeypatch.delenv("TEAMFLOW_PUBLIC_URL", raising=False)
    monkeypatch.delenv("UVICORN_PORT", raising=False)
    assert devlogin.guess_base(["uvicorn", "teamflow_server.app:app", "--port", "8123"]) == "http://127.0.0.1:8123"
    assert devlogin.guess_base(["uvicorn", "x", "--port=8124"]) == "http://127.0.0.1:8124"
    assert devlogin.guess_base(["uvicorn", "x"]) == "http://127.0.0.1:8100"
    monkeypatch.setenv("TEAMFLOW_PUBLIC_URL", "http://127.0.0.1:8200/")
    assert devlogin.guess_base(["--port", "1"]) == "http://127.0.0.1:8200"


async def test_login_code_is_one_time(client, svc):
    code = devlogin.issue("bob")
    # 打开链接：只显示确认页，不消耗登录码（GET 不产生副作用）
    for _ in range(2):
        r = await client.get("/dev/login", params={"code": code, "as": "bob"})
        assert r.status_code == 200
        assert "content-security-policy" in r.headers and r.headers["referrer-policy"] == "same-origin"
        assert r.headers["cache-control"] == "no-store"
        assert 'method="post" action="/dev/login"' in r.text and "登录" in r.text
        assert "<strong>bob（Bob）</strong>" in r.text
        assert "set-cookie" not in r.headers
    r = await client.post("/dev/login", data={"code": code, "as": "bob"}, headers={"origin": BASE})
    assert r.status_code == 303 and r.headers["location"] == "/"
    # 用过即失效：页面和提交都不行
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=client._transport.app), base_url=BASE) as other:  # type: ignore[attr-defined]
        r = await other.get("/dev/login", params={"code": code, "as": "bob"})
        assert r.status_code == 403 and "已经用过" in r.text
        r = await other.post("/dev/login", data={"code": code, "as": "bob"}, headers={"origin": BASE})
        assert r.status_code == 403 and "set-cookie" not in r.headers
        assert (await other.get("/api/v1/web/me")).status_code == 401
    assert any(a["action"] == "web.login" and a["result"] == "rejected" for a in svc.audit)


async def test_login_code_expires(client):
    code = devlogin.issue("alice", ttl_s=0)
    r = await client.get("/dev/login", params={"code": code, "as": "alice"})
    assert r.status_code == 403
    r = await client.post("/dev/login", data={"code": code, "as": "alice"}, headers={"origin": BASE})
    assert r.status_code == 403 and "set-cookie" not in r.headers
    assert devlogin.check(code, "alice", consume=False) == devlogin.UNKNOWN  # 过期的顺手清掉了
    assert devlogin.check(devlogin.issue("alice", ttl_s=60), "alice", consume=False, now=10**12) == devlogin.EXPIRED


async def test_login_code_is_bound_to_member(client):
    code = devlogin.issue("bob")
    r = await client.post("/dev/login", data={"code": code, "as": "alice"}, headers={"origin": BASE})
    assert r.status_code == 403
    for who in ("mallory", ""):
        r = await client.post("/dev/login", data={"code": code, "as": who}, headers={"origin": BASE})
        assert r.status_code == 403
    # as 打错了不消耗：用对的身份还能登
    r = await client.post("/dev/login", data={"code": code, "as": "bob"}, headers={"origin": BASE})
    assert r.status_code == 303


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"origin": "https://evil.example"},
        {"origin": "http://127.0.0.1:9999"},
        {"origin": "http://localhost:8100"},  # 另一个本机地址也不是本站
        {"origin": "null"},
        {"origin": "null", "sec-fetch-site": "cross-site"},
        {"origin": "null", "sec-fetch-site": "same-site"},
        {"origin": "https://evil.example", "sec-fetch-site": "same-origin"},  # 有真 Origin 就只看 Origin
    ],
)
async def test_login_post_requires_same_origin(client, headers):
    code = devlogin.issue("alice")
    r = await client.post("/dev/login", data={"code": code, "as": "alice"}, headers=headers)
    assert r.status_code == 403 and "set-cookie" not in r.headers
    assert devlogin.check(code, "alice", consume=False) == devlogin.OK  # 没被消耗


@pytest.mark.parametrize("origin", [None, "null"])
async def test_same_origin_fetch_metadata_when_origin_is_null(app, origin):
    """页面 Referrer-Policy 是 no-referrer 时，浏览器给同源 POST 发 Origin: null（或不发）：这时认 Sec-Fetch-Site。"""
    headers = {"sec-fetch-site": "same-origin", **({"origin": origin} if origin else {})}
    async with mk(app) as c:
        code = devlogin.issue("alice")
        r = await c.post("/dev/login", data={"code": code, "as": "alice"}, headers=headers)
        assert r.status_code == 303
        csrf = (await c.get("/api/v1/web/me")).json()["csrf"]
        r = await c.post("/api/v1/web/tasks/T-53/comments", headers={**headers, "x-csrf-token": csrf}, json={"body": "同源"})
        assert r.status_code == 201
        r = await c.post("/api/v1/web/tasks/T-53/comments", headers={"origin": "null", "x-csrf-token": csrf}, json={"body": "不同源"})
        assert r.status_code == 403 and r.json()["error"] == "csrf"


@pytest.mark.parametrize(
    "client_addr,base,extra",
    [
        (("203.0.113.9", 5000), BASE, {}),  # 非本机来源
        (("10.0.0.2", 5000), BASE, {}),
        (LOCAL, BASE, {"x-forwarded-for": "203.0.113.9"}),  # 经过反向代理（M0 评审 B1）
        (LOCAL, BASE, {"forwarded": "for=203.0.113.9"}),
        (LOCAL, BASE, {"host": "evil.example:8100"}),  # DNS rebinding：Host 不是本机名字
        (LOCAL, "http://evil.example:8100", {}),
    ],
)
async def test_local_entrances_404_for_non_local(app, client_addr, base, extra):
    code = devlogin.issue("alice")
    # 先在本机正常登录拿到会话，再从"外面"带着它来
    async with mk(app) as good:
        h = await login(good, "alice")
        sess_cookie = good.cookies.get(webauth.SESSION_COOKIE)
        csrf = h["x-csrf-token"]
    async with mk(app, base, client_addr) as c:
        c.cookies.set(webauth.SESSION_COOKIE, sess_cookie)
        c.cookies.set(webauth.CSRF_COOKIE, csrf)
        hdr = {**extra, "origin": base, "x-csrf-token": csrf}
        r = await c.get("/dev/login", params={"code": code, "as": "alice"}, headers=extra)
        assert r.status_code == 404 and r.json()["error"] == "not_found"
        r = await c.post("/dev/login", data={"code": code, "as": "alice"}, headers=hdr)
        assert r.status_code == 404
        for method, path in (("GET", "/api/v1/web/me"), ("GET", "/api/v1/web/home"), ("POST", "/api/v1/web/logout")):
            r = await c.request(method, path, headers=hdr)
            assert r.status_code == 404, (method, path, r.status_code)
    assert devlogin.check(code, "alice", consume=False) == devlogin.OK


@pytest.mark.parametrize("value", [None, "0", "false"])
async def test_production_config_is_404(app, monkeypatch, value, tmp_path, capsys):
    async with mk(app) as c:
        h = await login(c, "alice")  # 开发模式下登录过
        code = devlogin.issue("bob")
        if value is None:
            monkeypatch.delenv("TEAMFLOW_DEV_ENDPOINTS")
        else:
            monkeypatch.setenv("TEAMFLOW_DEV_ENDPOINTS", value)
        r = await c.get("/dev/login", params={"code": code, "as": "bob"})
        assert r.status_code == 404
        r = await c.post("/dev/login", data={"code": code, "as": "bob"}, headers={"origin": BASE})
        assert r.status_code == 404 and "set-cookie" not in r.headers
        for method, path in (
            ("GET", "/api/v1/web/me"),
            ("GET", "/api/v1/web/tasks/T-52"),
            ("POST", "/api/v1/web/tasks/T-53:claim"),
            ("POST", "/api/v1/web/logout"),
        ):
            r = await c.request(method, path, headers=h, json={})
            assert r.status_code == 404 and r.json()["error"] == "not_found", (method, path)
    # 生产配置启动：不打印登录链接，不写状态目录
    state = tmp_path / "prod-state"
    monkeypatch.setenv("TEAMFLOW_STATE", str(state))
    monkeypatch.delenv("TEAMFLOW_DEV_ENDPOINTS", raising=False)
    capsys.readouterr()
    a = create_app()
    async with a.router.lifespan_context(a):
        pass
    assert "/dev/login" not in capsys.readouterr().err
    assert not state.exists()


async def test_cookie_attributes(app):
    async with mk(app) as c:
        code = devlogin.issue("alice")
        r = await c.post("/dev/login", data={"code": code, "as": "alice"}, headers={"origin": BASE})
        ck = set_cookie_attrs(r)
        s, x = ck[webauth.SESSION_COOKIE], ck[webauth.CSRF_COOKIE]
        assert s["httponly"] is True and s["samesite"] == "Strict" and s["path"] == "/" and s["max-age"] == "43200"
        assert "secure" not in s  # 本机 http 试用不加 Secure
        assert x["samesite"] == "Strict" and x["path"] == "/" and "httponly" not in x  # 页面要能读（双提交）
        assert len(str(s["value"])) >= 40 and s["value"] != x["value"]
        assert r.headers["cache-control"] == "no-store"
        me = (await c.get("/api/v1/web/me")).json()
        assert me["csrf"] == x["value"]
    # https 时加 Secure
    async with mk(app, "https://127.0.0.1:8100") as c:
        code = devlogin.issue("bob")
        r = await c.post("/dev/login", data={"code": code, "as": "bob"}, headers={"origin": "https://127.0.0.1:8100"})
        ck = set_cookie_attrs(r)
        assert ck[webauth.SESSION_COOKIE]["secure"] is True and ck[webauth.CSRF_COOKIE]["secure"] is True


async def test_server_keeps_only_session_hash(app, web_as):
    c, _ = await web_as("alice")
    sid = c.cookies.get(webauth.SESSION_COOKIE)
    store: webauth.WebSessions = app.state.web_sessions
    assert sid not in store._d and store.get(sid) is not None


def test_session_expires():
    now = {"t": 1000.0}
    store = webauth.WebSessions(clock=lambda: now["t"])
    sid, sess = store.create("alice")
    assert store.get(sid) is sess
    now["t"] += webauth.SESSION_TTL_S - 1
    assert store.get(sid) is sess
    now["t"] += 2
    assert store.get(sid) is None
    assert store.get("") is None and store.get("x" * 300) is None


async def test_relogin_on_same_host_replaces_session(app):
    async with mk(app) as c:
        await login(c, "alice")
        old = c.cookies.get(webauth.SESSION_COOKIE)
        await login(c, "bob")
        assert (await c.get("/api/v1/web/me")).json()["me"] == "bob"
        assert app.state.web_sessions.get(old) is None


# ---------------------------------------------------------------------------
# 网页 API 的鉴权
# ---------------------------------------------------------------------------

WEB_CALLS = [
    ("GET", "/api/v1/web/me"),
    ("GET", "/api/v1/web/home"),
    ("GET", "/api/v1/web/tasks"),
    ("GET", "/api/v1/web/tasks/T-52"),
    ("GET", "/api/v1/web/blockers/B-7"),
    ("GET", "/api/v1/web/notifications"),
    ("POST", "/api/v1/web/tasks"),
    ("POST", "/api/v1/web/tasks/T-52:accept"),
    ("POST", "/api/v1/web/tasks/T-53:claim"),
    ("POST", "/api/v1/web/tasks/T-51:forward"),
    ("POST", "/api/v1/web/tasks/T-52/comments"),
    ("POST", "/api/v1/web/blockers/B-7:help"),
    ("POST", "/api/v1/web/blockers/B-7:forward"),
    ("POST", "/api/v1/web/logout"),
]


@pytest.mark.parametrize("method,path", WEB_CALLS)
async def test_web_api_rejects_pat(web_as, svc, method, path):
    """硬规则 1：网页 API 只认人类会话。带 PAT（有效、无效、甚至同时带着有效 cookie）一律 403 human_only。"""
    c, h = await web_as("bob")
    before = svc.latest_event_id()
    for tok in (BOB, ALICE, "tf_pat_" + "nope"):
        r = await c.request(method, path, headers={**h, **auth(tok)}, json={})
        assert r.status_code == 403 and r.json()["error"] == "human_only", (tok, r.text)
    async with mk(c._transport.app) as bare:  # type: ignore[attr-defined]
        r = await bare.request(method, path, headers=auth(BOB), json={})
        assert r.status_code == 403 and r.json()["error"] == "human_only"
        r = await bare.request(method, path, headers={"authorization": "Basic Ym9iOng="}, json={})
        assert r.status_code == 403
    assert svc.latest_event_id() == before


@pytest.mark.parametrize("method,path", WEB_CALLS)
async def test_web_api_needs_session(app, method, path):
    async with mk(app) as c:
        r = await c.request(method, path, json={}, headers={"origin": BASE})
        assert r.status_code == 401 and r.json()["error"] == "unauthorized"
        assert "devlogin" in r.json()["message"]
        c.cookies.set(webauth.SESSION_COOKIE, "forged-session-id")
        r = await c.request(method, path, json={}, headers={"origin": BASE})
        assert r.status_code == 401


WRITE_CALLS = [(m, p) for m, p in WEB_CALLS if m == "POST"]


@pytest.mark.parametrize("method,path", WRITE_CALLS)
async def test_web_writes_need_csrf_and_origin(web_as, svc, method, path):
    c, h = await web_as("bob")
    before = (svc.latest_event_id(), len(svc.tasks))
    good_tok, good_origin = h["x-csrf-token"], h["origin"]
    bad = [
        {"origin": good_origin},  # 缺 X-CSRF-Token
        {"origin": good_origin, "x-csrf-token": ""},
        {"origin": good_origin, "x-csrf-token": good_tok + "x"},
        {"x-csrf-token": good_tok},  # 缺 Origin
        {"origin": "https://evil.example", "x-csrf-token": good_tok},
        {"origin": "http://localhost:8100", "x-csrf-token": good_tok},  # 另一个本机地址也不是本站
        {"origin": "null", "x-csrf-token": good_tok},
    ]
    for hdr in bad:
        r = await c.request(method, path, headers=hdr, json={"v": 1})
        assert r.status_code == 403 and r.json()["error"] == "csrf", (hdr, r.text)
    # token 对、但 cookie 被换掉（双提交两边不一致）
    c.cookies.set(webauth.CSRF_COOKIE, "other")
    r = await c.request(method, path, headers=h, json={})
    assert r.status_code == 403 and r.json()["error"] == "csrf"
    assert (svc.latest_event_id(), len(svc.tasks)) == before
    assert c.cookies.get(webauth.SESSION_COOKIE)  # 会话还在


async def test_web_get_needs_no_csrf_and_has_no_side_effects(web_as, svc):
    c, _ = await web_as("bob")
    before = (svc.latest_event_id(), dict(svc.acceptances), len(svc.outbox))
    for path in ("/api/v1/web/me", "/api/v1/web/home", "/api/v1/web/tasks?view=all", "/api/v1/web/tasks/T-52", "/api/v1/web/blockers/B-7", "/api/v1/web/notifications"):
        r = await c.get(path)
        assert r.status_code == 200, (path, r.text)
        assert r.headers["cache-control"] == "no-store" and r.headers["x-content-type-options"] == "nosniff"
    assert (svc.latest_event_id(), dict(svc.acceptances), len(svc.outbox)) == before
    # bob 在网页上看过 T-52 的正文，他的 agent 仍然拿不到（看不等于接受）
    assert svc.get_item(agent("bob", "codex"), "T-52")["withheld"] == "not_accepted"


async def test_unknown_web_route_says_no_route(web_as):
    """没有这个接口（比如旧地址 /api/v1/web/wechat）和"没有这一项"分开：路由级 404 带 no_route，
    网页据此提示"在跑的服务端是旧代码，重新运行 scripts/local-up.sh"（红队：原来提示"编号不对或服务端刚重启过"）。"""
    c, _ = await web_as("bob")
    r = await c.get("/api/v1/web/wechat")
    assert r.status_code == 404 and r.json()["error"] == "not_found" and r.json()["no_route"] is True
    r = await c.get("/api/v1/web/tasks/T-999")
    assert r.status_code == 404 and "no_route" not in r.json()


async def test_web_cookie_never_authenticates_pat_endpoints(web_as):
    c, h = await web_as("bob")
    for method, path in (("GET", "/api/v1/me/inbox"), ("POST", "/api/v1/tasks/T-52:accept"), ("POST", "/api/v1/tasks")):
        r = await c.request(method, path, headers=h, json={})
        assert r.status_code == 401 and r.json()["error"] == "unauthorized"


async def test_get_item_for_human_refuses_agents(svc):
    from teamflow_server.errors import DomainError

    with pytest.raises(DomainError) as e:
        svc.get_item(agent("bob", "codex"), "T-52", for_human=True)
    assert e.value.code == "human_only"


async def test_logout(web_as, svc):
    c, h = await web_as("alice")
    sid = c.cookies.get(webauth.SESSION_COOKIE)
    r = await c.post("/api/v1/web/logout", headers={"origin": BASE})
    assert r.status_code == 403  # 登出也要过 CSRF
    r = await c.post("/api/v1/web/logout", headers=h)
    assert r.status_code == 200 and r.json() == {"ok": True}
    ck = set_cookie_attrs(r)
    assert ck[webauth.SESSION_COOKIE]["max-age"] == "0" and ck[webauth.CSRF_COOKIE]["max-age"] == "0"
    async with mk(c._transport.app) as other:  # type: ignore[attr-defined]
        other.cookies.set(webauth.SESSION_COOKIE, sid)
        assert (await other.get("/api/v1/web/me")).status_code == 401


async def test_web_body_limit_after_session(web_as, app):
    c, h = await web_as("alice")
    big = {"title": "大", "body": "字" * 40000}
    r = await c.post("/api/v1/web/tasks", headers=h, json=big)
    assert r.status_code == 413 and r.json()["error"] == "too_large"
    async with mk(app) as anon:
        r = await anon.post("/api/v1/web/tasks", headers={"origin": BASE}, json=big)
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# 人类动作：版本、through、闸门
# ---------------------------------------------------------------------------


async def test_web_accept_stale_version_409_and_missing_400(web_as, svc):
    c, h = await web_as("bob")
    d = (await c.get("/api/v1/web/tasks/T-52")).json()
    assert d["can"][:2] == ["accept", "decline"] and d["agent"]["content"] == "not_accepted"
    assert d["content"]["label"] == "alice 的 Claude Code" and d["assign"]["bk"] == "agent"
    full = page_fields(d, "v", "sha", "seq", "through")
    for drop in ("v", "sha", "seq", "through"):
        r = await c.post("/api/v1/web/tasks/T-52:accept", headers=h, json={k: v for k, v in full.items() if k != drop})
        assert r.status_code == 400 and r.json()["error"] == "invalid", drop
    for bad in ({"v": full["v"] + 1}, {"sha": "0" * 64}, {"seq": full["seq"] + 1}):
        r = await c.post("/api/v1/web/tasks/T-52:accept", headers=h, json={**full, **bad})
        assert r.status_code == 409 and r.json()["error"] == "conflict", bad
    r = await c.post("/api/v1/web/tasks/T-52:accept", headers=h, json={**full, "through": full["through"] + 50})
    assert r.status_code == 400
    r = await c.post("/api/v1/web/tasks/T-52:accept", headers=h, json={**full, "through": str(full["through"])})
    assert r.status_code == 422 and r.json()["error"] == "invalid"
    # 页面渲染之后、点「接受」之前，alice 的 agent 改了正文：旧版本 409
    svc.update_task(agent("alice", "claude_code"), "T-52", body="改过的正文：先查日志再重试。")
    r = await c.post("/api/v1/web/tasks/T-52:accept", headers=h, json=full)
    assert r.status_code == 409 and r.json()["error"] == "conflict" and "重新查看" in r.json()["message"]
    assert svc.tasks["T-52"].assign_state == "pending"
    # 重新打开页面再接受：成功，bob 的 agent 拿到的是新正文
    d2 = (await c.get("/api/v1/web/tasks/T-52")).json()
    assert d2["content"]["t"] == "改过的正文：先查日志再重试。"
    r = await c.post("/api/v1/web/tasks/T-52:accept", headers=h, json=page_fields(d2, "v", "sha", "seq", "through"))
    assert r.status_code == 200 and r.json()["st"] == "todo"
    assert svc.get_item(agent("bob", "codex"), "T-52")["content"]["t"] == "改过的正文：先查日志再重试。"
    # alice 收到回音
    alice_msgs = [n for n in svc.outbox if n["to"] == "alice"]
    assert alice_msgs[-1]["text"] == "bob 接受了 T-52"


async def test_web_claim_stale_version_409_then_taken(web_as, svc):
    c, h = await web_as("bob")
    d = (await c.get("/api/v1/web/tasks/T-53")).json()
    assert "claim" in d["can"] and d["st"] == "pool"
    form = page_fields(d, "v", "sha", "through")
    svc.update_task(agent("alice", "claude_code"), "T-53", body="正文改了")
    r = await c.post("/api/v1/web/tasks/T-53:claim", headers=h, json=form)
    assert r.status_code == 409 and r.json()["error"] == "conflict"
    assert svc.tasks["T-53"].assignee is None
    form = page_fields((await c.get("/api/v1/web/tasks/T-53")).json(), "v", "sha", "through")
    # alice 在网页上先认领：bob 再点就是 taken（"已被 alice 于 … 认领"）
    ca, ha = await web_as("alice")
    r = await ca.post("/api/v1/web/tasks/T-53:claim", headers=ha, json=form)
    assert r.status_code == 200 and r.json()["st"] == "todo"
    r = await c.post("/api/v1/web/tasks/T-53:claim", headers=h, json=form)
    assert r.status_code == 409 and r.json()["error"] == "taken" and r.json()["by"] == "alice"


async def test_scenario1_agent_asks_then_human_claims(web_as, client, svc):
    """场景 1：bob 的 Codex 发布 T-51；alice 的 agent 认领 → needs_human + 模拟通知；alice 在网页上认领后 agent 接手。"""
    r = await client.post("/api/v1/tasks/T-51:claim", headers=auth(ALICE))
    assert r.status_code == 403 and r.json()["error"] == "needs_human"
    c, h = await web_as("alice")
    wx = (await c.get("/api/v1/web/notifications")).json()
    top = wx["items"][0]
    assert top["kind"] == "agent_asks" and top["text"] == "您的 Claude Code 想开始 T-51，点这里认领"
    assert top["path"] == f"/task?w=team&id=T-51&n={top['n']}" and top["kind_text"] == "您的 agent 需要您确认"
    assert all(n["to"] == "alice" for n in svc.outbox if n["text"] in {i["text"] for i in wx["items"]})
    d = (await c.get("/api/v1/web/tasks/T-51")).json()
    assert "claim" in d["can"] and d["agent"]["content"] == "not_accepted"
    assert d["t"]["label"] == "bob 的 Codex" and d["content"]["t"].startswith("首屏在 4G 下")
    r = await c.post("/api/v1/web/tasks/T-51:claim", headers=h, json=page_fields(d, "v", "sha", "through"))
    assert r.status_code == 200 and r.json()["st"] == "todo"
    r = await client.post("/api/v1/tasks/T-51:claim", headers=auth(ALICE))
    assert r.status_code == 200 and r.json()["st"] == "doing"
    r = await client.get("/api/v1/tasks/T-51", headers=auth(ALICE))
    assert r.json()["content"]["trust"] == "peer_agent"


async def test_forward_only_releases_what_the_page_showed(web_as, svc):
    """转发和认领帮忙都只放页面渲染时看到的动态；页面之后对方 agent 写的评论仍待转发。转发不授予正文。"""
    alice_cc = agent("alice", "claude_code")
    c, h = await web_as("alice")
    d = (await c.get("/api/v1/web/blockers/B-7")).json()
    assert d["agent"] == {"content": "not_accepted", "through": 0, "unforwarded": 1}
    assert set(d["can"]) >= {"help", "forward", "comment"}
    comment = [e for e in d["ev"] if e["ty"] == "comment"][0]
    assert comment["agent"] is False and comment["label"] == "bob 的 Codex" and comment["what"] == "评论"
    seen = d["page"]["through"]
    svc.comment(agent("bob", "codex"), "B-7", "补充：控制台入口在网络与安全组页面。")  # 页面渲染之后才写的
    r = await c.post("/api/v1/web/blockers/B-7:forward", headers=h, json={})
    assert r.status_code == 400
    r = await c.post("/api/v1/web/blockers/B-7:forward", headers=h, json={"through": seen})
    assert r.status_code == 200 and r.json()["through"] == seen
    item = svc.get_item(alice_cc, "B-7", 10)
    assert item["withheld"] == "not_accepted"  # 转发不授予正文
    texts = [e.get("t") for e in item["ev"] if e.get("ty") == "comment"]
    assert texts == ["已确认是安全组规则的问题，需要有控制台权限的人加一条入站规则。"]
    assert [e for e in item["ev"] if e.get("withheld") == "peer_agent_text"][0]["n"] == 1
    # 认领帮忙：带的还是旧页面的 through，新评论仍然不放
    r = await c.post("/api/v1/web/blockers/B-7:help", headers=h, json=page_fields(d, "v", "sha", "through"))
    assert r.status_code == 200 and r.json()["helper"] == "alice"
    item = svc.get_item(alice_cc, "B-7", 10)
    assert "content" in item and [e for e in item["ev"] if e.get("withheld") == "peer_agent_text"][0]["n"] == 1
    d = (await c.get("/api/v1/web/blockers/B-7")).json()
    assert d["agent"]["unforwarded"] == 1 and "forward" in d["can"] and "help" not in d["can"]


async def test_decline(web_as, svc):
    c, h = await web_as("bob")
    d = (await c.get("/api/v1/web/tasks/T-52")).json()
    r = await c.post("/api/v1/web/tasks/T-52:decline", headers=h, json={"seq": d["page"]["seq"]})
    assert r.status_code == 400 and "原因" in r.json()["message"]
    r = await c.post("/api/v1/web/tasks/T-52:decline", headers=h, json={"reason": "这周排满了"})
    assert r.status_code == 400
    r = await c.post("/api/v1/web/tasks/T-52:decline", headers=h, json={"seq": d["page"]["seq"] + 1, "reason": "这周排满了"})
    assert r.status_code == 409
    r = await c.post("/api/v1/web/tasks/T-52:decline", headers=h, json={"seq": d["page"]["seq"], "reason": "这周排满了"})
    assert r.status_code == 200 and r.json() == {"id": "T-52", "st": "todo", "who": "alice"}
    t = svc.tasks["T-52"]
    assert (t.assignee, t.assign_state, t.status) == ("alice", "accepted", "open")
    ca, _ = await web_as("alice")
    wx = (await ca.get("/api/v1/web/notifications")).json()["items"]
    assert wx[0]["text"] == "bob 没接 T-52" and wx[0]["kind"] == "task_reply"
    ev = [e for e in (await ca.get("/api/v1/web/tasks/T-52")).json()["ev"] if e["ty"] == "task.declined"][0]
    assert ev["t"] == "这周排满了" and ev["what"] == "拒绝了" and ev["label"] == "bob"
    # 再点一次：已经不是待接受了
    r = await c.post("/api/v1/web/tasks/T-52:decline", headers=h, json={"seq": d["page"]["seq"], "reason": "x"})
    assert r.status_code == 409


async def test_start_done_release(web_as, svc):
    c, h = await web_as("bob")
    d = (await c.get("/api/v1/web/tasks/T-52")).json()
    assert (await c.post("/api/v1/web/tasks/T-52:start", headers=h, json={})).json()["error"] == "needs_accept"
    await c.post("/api/v1/web/tasks/T-52:accept", headers=h, json=page_fields(d, "v", "sha", "seq", "through"))
    d = (await c.get("/api/v1/web/tasks/T-52")).json()
    assert set(d["can"]) >= {"start", "done", "release"}
    r = await c.post("/api/v1/web/tasks/T-52:start", headers=h, json={})
    assert r.status_code == 200 and r.json()["st"] == "doing"
    r = await c.post("/api/v1/web/tasks/T-52:release", headers=h, json={"note": "先放一放"})
    assert r.status_code == 200 and r.json()["st"] == "todo" and svc.tasks["T-52"].assignee == "bob"
    r = await c.post("/api/v1/web/tasks/T-52:release", headers=h, json={})
    assert r.status_code == 400 and "放回待认领" in r.json()["message"]
    seq = svc.tasks["T-52"].assign_seq
    r = await c.post("/api/v1/web/tasks/T-52:release", headers=h, json={"to_pool": True})
    assert r.status_code == 200 and r.json()["st"] == "pool"
    t = svc.tasks["T-52"]
    assert t.assignee is None and t.assign_seq == seq + 1
    ev = (await c.get("/api/v1/web/tasks/T-52")).json()["ev"][-1]
    assert ev["what"] == "取消认领，放回待认领"
    # alice 不是负责人：不能完成、不能取消认领
    ca, ha = await web_as("alice")
    assert (await ca.post("/api/v1/web/tasks/T-50:release", headers=ha, json={"to_pool": True})).status_code == 200
    r = await ca.post("/api/v1/web/tasks/T-49:done", headers=ha, json={})
    assert r.status_code == 403 and r.json()["error"] == "not_allowed" and "您不能" in r.json()["message"]
    # bob 再认领回来、完成：alice（发布人）收到回音
    d = (await c.get("/api/v1/web/tasks/T-52")).json()
    assert (await c.post("/api/v1/web/tasks/T-52:claim", headers=h, json=page_fields(d, "v", "sha", "through"))).status_code == 200
    r = await c.post("/api/v1/web/tasks/T-52:done", headers=h, json={})
    assert r.status_code == 200 and r.json()["st"] == "done"
    assert [n["text"] for n in svc.outbox if n["to"] == "alice"][-1] == "您发布的 T-52 已由 bob 完成"
    assert (await c.post("/api/v1/web/tasks/T-52:fly", headers=h, json={})).status_code == 404


async def test_create_task_and_comments(web_as, svc):
    ca, ha = await web_as("alice")
    r = await ca.post("/api/v1/web/tasks", headers=ha, json={"title": "看一下\n支付对账", "body": "对账文件比账单少 3 条。", "assignee": "bob", "project": "pay"})
    assert r.status_code == 201
    tid = r.json()["id"]
    assert r.json()["st"] == "pending" and r.json()["path"] == f"/task?w=team&id={tid}"
    assert svc.tasks[tid].title == "看一下 支付对账"  # 人写的标题折成一行
    cb, hb = await web_as("bob")
    wx = (await cb.get("/api/v1/web/notifications")).json()["items"][0]
    assert wx["text"] == f"alice 请您协作：看一下 支付对账（{tid}）" and wx["kind"] == "task_assigned"
    r = await ca.post("/api/v1/web/tasks", headers=ha, json={"title": "补监控", "assignee": ""})
    assert r.status_code == 201 and r.json()["st"] == "pool"
    r = await ca.post("/api/v1/web/tasks", headers=ha, json={"title": "我自己来", "assignee": "alice"})
    assert r.json()["st"] == "todo"
    r = await ca.post("/api/v1/web/tasks", headers=ha, json={"title": "x", "assignee": "mallory"})
    assert r.status_code == 400 and r.json()["error"] == "invalid"
    r = await ca.post("/api/v1/web/tasks", headers=ha, json={"body": "没标题"})
    assert r.status_code == 422 and r.json()["error"] == "invalid"
    # 评论：人写的；评论区标注作者，标出本人的 agent 能不能读到
    r = await cb.post(f"/api/v1/web/tasks/{tid}/comments", headers=hb, json={"body": "我下午看。"})
    assert r.status_code == 201
    d = (await ca.get(f"/api/v1/web/tasks/{tid}")).json()
    ev = [e for e in d["ev"] if e["ty"] == "comment"][0]
    assert ev["t"] == "我下午看。" and ev["label"] == "bob" and ev["what"] == "评论"
    # 扫描照样生效
    leaked = "token 是 " + "sk-" + "ant-" + "api03-" + "abcdefghijklmnop"
    r = await cb.post(f"/api/v1/web/tasks/{tid}/comments", headers=hb, json={"body": leaked})
    assert r.status_code == 422 and r.json()["error"] == "secret_detected"
    r = await cb.post("/api/v1/web/blockers/B-7/comments", headers=hb, json={"body": "我去问问运维。"})
    assert r.status_code == 201
    r = await cb.post("/api/v1/web/tasks/B-7/comments", headers=hb, json={"body": "放错地方"})
    assert r.status_code == 404


async def test_blocker_ask_help_resolve(web_as, svc):
    svc.report_blocker(agent("bob", "codex"), "构建机磁盘满了", detail="清理缓存后还是满。", need="alice")
    bid = max(svc.blockers, key=lambda k: svc.blockers[k].no)
    cb, hb = await web_as("bob")
    home = (await cb.get("/api/v1/web/home")).json()
    assert home["mine"]["proposed"][0] == {"id": bid, "h": "alice", "client": "codex"}
    assert home["titles"][bid]["label"] == "bob 的 Codex"
    assert {b["id"] for b in home["blockers"]} >= {bid, "B-7"} and all("stuck_min" in b for b in home["blockers"])
    d = (await cb.get(f"/api/v1/web/blockers/{bid}")).json()
    assert "ask" in d["can"] and d["need_text"] == "待您确认点名"
    assert not [n for n in svc.outbox if n["to"] == "alice" and n["subject"] == bid]  # 确认之前不通知
    r = await cb.post(f"/api/v1/web/blockers/{bid}:ask", headers=hb, json={})
    assert r.status_code == 200 and r.json()["need_state"] == "asked"
    ca, ha = await web_as("alice")
    wx = (await ca.get("/api/v1/web/notifications")).json()["items"][0]
    assert wx["text"] == f"bob 请您帮忙看 {bid}" and wx["path"].startswith(f"/blocker?w=team&id={bid}&n=")
    d = (await ca.get(f"/api/v1/web/blockers/{bid}")).json()
    r = await ca.post(f"/api/v1/web/blockers/{bid}:help", headers=ha, json=page_fields(d, "v", "sha", "through"))
    assert r.status_code == 200
    r = await ca.post(f"/api/v1/web/blockers/{bid}:resolve", headers=ha, json={})
    assert r.status_code == 400
    r = await ca.post(f"/api/v1/web/blockers/{bid}:resolve", headers=ha, json={"body": "清了 docker 镜像"})
    assert r.status_code == 200 and svc.blockers[bid].status == "resolved"
    # 人报告困难：带 need 直接点名并通知
    r = await ca.post("/api/v1/web/blockers", headers=ha, json={"title": "测试账号被锁", "need": "bob", "task": "T-50"})
    assert r.status_code == 201 and r.json()["need_state"] == "asked"
    assert [n["text"] for n in svc.outbox if n["to"] == "bob"][-1] == f"alice 请您帮忙看 {r.json()['id']}"


async def test_home_and_lists(web_as):
    c, _ = await web_as("alice")
    h = (await c.get("/api/v1/web/home")).json()
    assert h["me"] == "alice" and set(h["mine"]) == {"to_accept", "help_me", "proposed", "fwd", "replies"}
    assert h["mine"]["help_me"] == [{"id": "B-7", "by": "bob"}] and h["mine"]["fwd"][0]["id"] == "B-7"
    assert {p["key"] for p in h["projects"]} == {"tf", "pay"} and "counts" in h["projects"][0]
    assert {d["id"] for d in h["doing"]} == {"T-49", "T-50"} and h["titles"]["T-49"]["t"] == "测试库迁移到新实例"
    for view, ids in (("pool", {"T-51", "T-53"}), ("doing", {"T-49", "T-50"})):
        rows = (await c.get("/api/v1/web/tasks", params={"view": view})).json()["rows"]
        assert {r["id"] for r in rows} == ids
        assert all(r["st_text"] and r["t"]["label"] and r["path"].startswith("/task?") for r in rows)
    r = await c.get("/api/v1/web/tasks", params={"view": "nope"})
    assert r.status_code == 400
    me = (await c.get("/api/v1/web/me")).json()
    assert me["members"] == [{"h": "alice", "name": "Alice", "agent": True}, {"h": "bob", "name": "Bob", "agent": True}] and me["mode"] == "dev"
    assert (await c.get("/api/v1/web/tasks/T-999")).status_code == 404
    assert (await c.get("/api/v1/web/blockers/T-52")).status_code == 404


async def test_event_words_call_the_viewer_you(web_as):
    """动态里被提到的人是看页面的本人时写「您」，不写他的 handle（对用户称「您」）；别人照旧写 handle。"""
    def words(d):
        return {e["ty"]: e["what"] for e in d["ev"] if "what" in e}

    bob, _ = await web_as("bob")
    assert words((await bob.get("/api/v1/web/tasks/T-52")).json())["task.assigned"] == "指派给了您"
    b7 = words((await bob.get("/api/v1/web/blockers/B-7")).json())
    assert b7["blocker.raised"] == "报告了困难，需要 alice" and b7["blocker.asked"] == "确认请 alice 帮忙"
    alice, _ = await web_as("alice")
    assert words((await alice.get("/api/v1/web/tasks/T-52")).json())["task.assigned"] == "指派给了 bob"
    b7 = words((await alice.get("/api/v1/web/blockers/B-7")).json())
    assert b7["blocker.raised"] == "报告了困难，需要您" and b7["blocker.asked"] == "确认请您帮忙"


# ---------------------------------------------------------------------------
# 静态单页
# ---------------------------------------------------------------------------


async def test_static_spa_and_csp(client):
    for path in ("/", "/task?w=team&id=T-52", "/tasks", "/blocker?w=team&id=B-7", "/new", "/me"):
        r = await client.get(path)
        assert r.status_code == 200, path
        assert r.headers["content-type"].startswith("text/html")
        csp = r.headers["content-security-policy"]
        assert "script-src 'self'" in csp and "unsafe-inline" not in csp and "frame-ancestors 'none'" in csp
        assert r.headers["x-content-type-options"] == "nosniff" and r.headers["referrer-policy"] == "same-origin"
        assert r.headers["cache-control"] == "no-store"
        assert "Team Flow" in r.text
    r = await client.head("/")
    assert r.status_code == 200
    for path in ("/assets/missing.js", "/favicon.ico", "/.gitignore", "/../server/README.md"):
        r = await client.get(path)
        assert r.status_code == 404, path
    # 保留路径不回退到页面：JSON 404 / 405 照旧
    r = await client.get("/api/v1/nope", headers=auth(ALICE))
    assert r.status_code == 404 and r.json()["error"] == "not_found"
    r = await client.get("/dev/other")
    assert r.status_code == 404 and r.json()["error"] == "not_found"
    r = await client.post("/somewhere", json={})
    assert r.status_code == 404 and r.json()["error"] == "not_found"
    r = await client.get("/api/v1/hooks/batch", headers=auth(ALICE))
    assert r.status_code == 405


def test_static_serves_files_inside_dist_only(tmp_path):
    from teamflow_server.web import static_response

    (tmp_path / "index.html").write_text("<!doctype html><title>x</title>", encoding="utf-8")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app-1a2b.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path.parent / "secret.txt").write_text("no", encoding="utf-8")
    r = static_response("/assets/app-1a2b.js", tmp_path)
    assert r is not None and r.media_type.startswith("text/javascript") and r.headers["cache-control"] == "no-cache"
    assert "script-src 'self'" in r.headers["content-security-policy"]
    assert static_response("/../secret.txt", tmp_path) is None
    assert static_response("/assets/../../secret.txt", tmp_path) is None
    assert str(static_response("/task", tmp_path).path).endswith("index.html")  # type: ignore[union-attr]
    (tmp_path / "index.html").unlink()
    assert static_response("/", tmp_path) is None


# ---------------------------------------------------------------------------
# devlogin 命令
# ---------------------------------------------------------------------------


class _Stdin:
    def __init__(self, tty: bool) -> None:
        self.tty = tty

    def isatty(self) -> bool:
        return self.tty


async def test_devlogin_command(app, monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", _Stdin(False))
    assert devlogin.main(["--as", "bob"]) == 2
    assert "终端" in capsys.readouterr().err
    monkeypatch.setattr(sys, "stdin", _Stdin(True))
    assert devlogin.main(["--as", "mallory"]) == 2
    assert "可选的有：alice、bob" in capsys.readouterr().err
    assert devlogin.main(["--as", "@Bob", "--ttl", "5"]) == 0
    out = capsys.readouterr()
    url = out.out.strip()
    assert "\n" not in url and "5 分钟" in out.err
    parts = urlsplit(url)
    q = parse_qs(parts.query)
    assert parts.hostname == "localhost" and parts.path == "/dev/login" and q["as"] == ["bob"]
    assert q["code"][0] not in (config.state_dir() / devlogin.CODES_FILE).read_text(encoding="utf-8")
    async with mk(app, f"http://localhost:{parts.port}") as c:
        r = await c.post("/dev/login", data={"code": q["code"][0], "as": "bob"}, headers={"origin": f"http://localhost:{parts.port}"})
        assert r.status_code == 303
    assert devlogin.main(["--as", "alice", "--host", "localhost"]) == 0
    assert urlsplit(capsys.readouterr().out.strip()).hostname == "localhost"
    monkeypatch.setenv("TEAMFLOW_STATE", str(config.state_dir() / "elsewhere"))
    assert devlogin.main(["--as", "alice"]) == 1
    assert "server.json" in capsys.readouterr().err


async def test_login_with_pat_is_refused_and_log_has_no_secrets(app, log_path):
    code = devlogin.issue("alice")
    async with mk(app) as c:
        for method in ("GET", "POST"):
            r = await c.request(
                method, "/dev/login", params={"code": code, "as": "alice"}, data={"code": code, "as": "alice"},
                headers={**auth(ALICE), "origin": BASE},
            )
            assert r.status_code == 403 and r.json()["error"] == "human_only"
        assert devlogin.check(code, "alice", consume=False) == devlogin.OK
        h = await login(c, "alice")
        await c.get("/dev/login", params={"code": code, "as": "alice"})
        await c.post("/api/v1/web/tasks/T-53/comments", headers=h, json={"body": "看看"})
        sid = c.cookies.get(webauth.SESSION_COOKIE)
    text = log_path.read_text(encoding="utf-8")
    for secret in (code, sid, h["x-csrf-token"]):
        assert secret and secret not in text
    recs = [json.loads(line) for line in text.splitlines()]
    assert any(r.get("path") == "/api/v1/web/tasks/T-53/comments" and r.get("h") == "alice" and r.get("web") == "ok" for r in recs)


async def test_token_handles_become_members_and_lead_the_banner(monkeypatch, capsys, tmp_path):
    """本地试用用自己的 handle：令牌里的 handle 种子时登记成成员；登录链接里有令牌的人排前面。"""
    monkeypatch.setenv("TEAMFLOW_STATE", str(tmp_path / "s"))
    toks = ",".join(
        f"tf_pat_{h}{i}" + "x" * 8 + f":{h}:{c}" for i, (h, c) in enumerate([("yang", "claude_code"), ("yang", "codex"), ("bob", "codex"), ("carol", "codex"), ("Bad-Handle", "codex")])
    )
    monkeypatch.setenv("TEAMFLOW_DEV_TOKENS", toks)
    a = create_app()
    svc = a.state.svc
    assert list(svc.members) == ["alice", "bob", "yang", "carol"] and svc.members["yang"].name == "yang"
    capsys.readouterr()
    async with a.router.lifespan_context(a):
        err = capsys.readouterr().err
        order = [line.split()[1] for line in err.splitlines() if "/dev/login?" in line]
        assert order == ["yang", "bob", "carol", "alice"]
        hosts = {line.split()[1]: urlsplit(line.split()[-1]).hostname for line in err.splitlines() if "/dev/login?" in line}
        assert hosts["yang"] == "127.0.0.1" and hosts["bob"] == "localhost"
        async with mk(a) as c:
            # 名字就是 handle 时，确认页只写一次（不写成 "yang（yang）"）
            page = (await c.get("/dev/login", params={"code": devlogin.issue("yang"), "as": "yang"})).text
            assert "<strong>yang</strong>" in page and "yang（yang）" not in page
            await login(c, "yang")
            home = (await c.get("/api/v1/web/home")).json()
            assert home["me"] == "yang" and home["mine"]["to_accept"] == []
            # 有令牌的成员带 agent: true；只在演示数据里的 alice 没有（「我」页"换成队友"的例子不挑她）
            members = {m["h"]: m.get("agent", False) for m in (await c.get("/api/v1/web/me")).json()["members"]}
            assert members == {"alice": False, "bob": True, "carol": True, "yang": True}
    # dev/reset 重新播种后成员还在
    svc.reset()
    from teamflow_server.seed import seed

    seed(svc)
    assert "yang" in svc.members and "carol" in svc.members
