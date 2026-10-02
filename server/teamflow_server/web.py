"""网页：本地登录（/dev/login）、网页 API（/api/v1/web/*）、静态单页（/）。

- 网页 API 只认人类会话 cookie（gateway 已经查过：本地开发模式、本机来源、没带 Authorization、会话有效、
  写请求过了 CSRF），这里只把会话变成 ``Actor(handle, "human", via="web")`` 交给 service。业务规则全在 service：
  接受、拒绝、认领、转发、帮忙要带页面渲染时的 v、sha、seq、through，缺字段 400、版本不一致 409。
- 这里只做"给人看"的装饰：作者标注（"bob" 或 "bob 的 Codex"）、状态和动态的中文说法、按钮提示 ``can``。
  ``can`` 只是提示，真正的守卫在 service。
- 静态单页：``web_dist/`` 下的构建产物；不是文件的路径回退到 index.html（React Router）；CSP ``script-src 'self'``。
- 接口说明见 docs/web-api.md。
"""

from __future__ import annotations

import html
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from fastapi import APIRouter, Body, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, ConfigDict, StrictBool, StrictInt, StrictStr
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import FileResponse

from . import devlogin, webauth
from .errors import DomainError
from .service import TZ, WS, Actor, Blocker, Service, Task, client_name, mdhm

WEB_DIST = Path(__file__).resolve().parent / "web_dist"

CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; "
    "connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
)
LOGIN_CSP = "default-src 'none'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
# Referrer-Policy 用 same-origin 而不是 no-referrer：no-referrer 时浏览器给同源的 POST 发 "Origin: null"，
# 写请求的 Origin 校验就过不去了。same-origin 照样不把地址（含登录码）带给别的站。
PAGE_HEADERS = {
    "Referrer-Policy": "same-origin",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-Robots-Tag": "noindex",
}
MAX_LOGIN_BODY = 4096

ST_TEXT = {
    "pool": "待认领",
    "pending": "待接受",
    "todo": "待开始",
    "doing": "进行中",
    "done": "已完成",
    "canceled": "已取消",
    "open": "未解决",
    "resolved": "已解决",
}
NEED_TEXT = {"none": "没有点名", "proposed": "待您确认点名", "asked": "已点名"}
KIND_TEXT = {
    "task_assigned": "请您协作",
    "blocker_needs_you": "请您帮忙",
    "task_reply": "回音",
    "agent_asks": "您的 agent 需要您确认",
    "system": "系统",
}

web = APIRouter(prefix="/api/v1/web")
pages = APIRouter()


# ---------------------------------------------------------------------------
# 公共
# ---------------------------------------------------------------------------


def svc_of(request: Request) -> Service:
    return request.app.state.svc


def sessions_of(request: Request) -> webauth.WebSessions:
    return request.app.state.web_sessions


def me_actor(request: Request) -> Actor:
    """gateway 放进 scope 的人类会话 → 人的 Actor。成员停用了就当没登录。"""
    sess = (request.scope.get("state") or {}).get("tf_web")
    if not isinstance(sess, webauth.WebSession):
        raise DomainError("unauthorized", "还没登录，或者登录已过期。", status=401)
    m = svc_of(request).members.get(sess.handle)
    if m is None or not m.active:
        raise DomainError("unauthorized", "这个成员已停用，请重新登录。", status=401)
    return Actor(sess.handle, "human", None, None, "web")


def who_label(by: str | None, trust: str | None, client: str | None) -> str:
    """作者标注：人写的是 "bob"，agent 写的是 "bob 的 Codex"。"""
    if not by:
        return "系统"
    if trust and trust.endswith("_agent"):
        return f"{by} 的 {client_name(client) or 'agent'}"
    return by


def _label_env(env: Any) -> Any:
    if isinstance(env, dict) and "trust" in env:
        env["label"] = who_label(env.get("by"), env.get("trust"), env.get("client"))
    return env


def path_of(oid: str, n: int | None = None) -> str:
    kind = "task" if oid.startswith("T-") else "blocker"
    return f"/{kind}?w={WS}&id={oid}" + (f"&n={n}" if n else "")


def _you(h: str | None, viewer: str | None) -> str | None:
    """动态里被提到的人：是看页面的本人就叫「您」，其他人用 handle 两边各空一格。"""
    if not h:
        return None
    return "您" if viewer and h == viewer else f" {h} "


def event_words(ev: dict[str, Any], viewer: str | None = None) -> str:
    """动态的中文说法（给页面直接显示）。只用 handle、编号和枚举，不拼自由文本。

    被提到的人是看页面的本人时写「您」（"指派给了您"），不写他的 handle。"""
    ty, data = ev.get("ty", ""), ev.get("data") or {}
    to, need = _you(data.get("to"), viewer), _you(data.get("need"), viewer)
    words = {
        "task.created": "发布了任务",
        "task.assigned": f"指派给了{to}".rstrip() if to else "指派了任务",
        "task.accepted": "接受了",
        "task.declined": "拒绝了",
        "task.claimed": "认领了",
        "task.started": "开始做了",
        "task.released": "取消认领，放回待认领" if data.get("reason") == "to_pool" else "取消认领",
        "task.done": "完成了",
        "task.canceled": "取消了任务",
        "task.reopened": "重新打开了",
        "task.edited": "编辑了内容",
        "note": "写了进度",
        "comment": "评论",
        "blocker.raised": "报告了困难" + (f"，需要{need}".rstrip() if need else ""),
        "blocker.asked": f"确认请{need}帮忙" if need else "确认了点名",
        "blocker.helped": "认领帮忙",
        "blocker.resolved": "标记已解决",
        "blocker.reopened": "重新打开了",
        "acceptance.forwarded": "转发给了自己的 agent",
    }
    return words.get(ty, ty)


def _decorate_item(item: dict[str, Any], viewer: str | None = None) -> dict[str, Any]:
    _label_env(item.get("t"))
    c = item.get("content")
    if isinstance(c, dict) and "trust" in c:
        _label_env(c)
    elif isinstance(c, dict):
        for v in c.values():
            _label_env(v)
    for ev in item.get("ev") or []:
        if "by" in ev:
            ev["label"] = who_label(ev.get("by"), ev.get("trust"), ev.get("client"))
        ev["what"] = event_words(ev, viewer)
    st = item.get("st")
    if st in ST_TEXT:
        item["st_text"] = ST_TEXT[st]
    if item.get("kind") == "blocker" and item.get("need_state") in NEED_TEXT:
        item["need_text"] = NEED_TEXT[item["need_state"]]
    item["path"] = path_of(item["id"])
    return item


def _task_can(me: str, t: Task, unforwarded: int) -> list[str]:
    """按钮提示（守卫在 service，这里只决定显示哪些按钮）。"""
    can: list[str] = []
    live = t.status in ("open", "in_progress")
    if live and t.assignee == me and t.assign_state == "pending":
        can += ["accept", "decline"]
    if t.status == "open" and t.assignee is None:
        can.append("claim")
    if live and t.assignee == me and t.assign_state == "accepted":
        if t.status == "open":
            can.append("start")
        can.append("done")
        can.append("release")
    if unforwarded:
        can.append("forward")
    can.append("comment")
    return can


def _blocker_can(me: str, b: Blocker, unforwarded: int) -> list[str]:
    can: list[str] = []
    if b.status == "open":
        if b.helper is None and b.raised_by != me:
            can.append("help")
        if b.raised_by == me and b.need_state == "proposed":
            can.append("ask")
        if me in (b.raised_by, b.helper):
            can.append("resolve")
    if unforwarded:
        can.append("forward")
    can.append("comment")
    return can


def _norm(svc: Service, raw: str, prefix: str) -> str:
    oid = svc._norm_id(raw)
    if not oid.startswith(prefix):
        raise DomainError("not_found", f"{raw} 不是{'任务' if prefix == 'T-' else '困难'}编号。")
    return oid


def _detail(request: Request, raw: str, prefix: str) -> dict[str, Any]:
    actor, svc = me_actor(request), svc_of(request)
    oid = _norm(svc, raw, prefix)
    with svc.lock:
        item = svc.get_item(actor, oid, for_human=True)
        unfwd = item["agent"]["unforwarded"]
        if prefix == "T-":
            item["can"] = _task_can(actor.handle, svc.tasks[oid], unfwd)
        else:
            item["can"] = _blocker_can(actor.handle, svc.blockers[oid], unfwd)
    return _decorate_item(item, actor.handle)


class ActionIn(BaseModel):
    """所有按钮共用的请求体。各按钮要哪些字段见 docs/web-api.md；缺了由 service 返回 400 invalid。"""

    model_config = ConfigDict(extra="ignore")
    v: StrictInt | None = None
    sha: StrictStr | None = None
    seq: StrictInt | None = None
    through: StrictInt | None = None
    reason: StrictStr | None = None
    note: StrictStr | None = None
    body: StrictStr | None = None
    to_pool: StrictBool = False


class CreateTaskIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: StrictStr
    body: StrictStr | None = None
    assignee: StrictStr | None = None
    project: StrictStr | None = None
    urgent: StrictBool = False
    parent: StrictStr | None = None


class BlockerIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: StrictStr
    detail: StrictStr | None = None
    tried: StrictStr | None = None
    task: StrictStr | None = None
    need: StrictStr | None = None


class CommentIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    body: StrictStr


def _blank(v: str | None) -> str | None:
    return v if v is not None and v.strip() else None


# ---------------------------------------------------------------------------
# 读
# ---------------------------------------------------------------------------


@web.get("/me")
def web_me(request: Request) -> dict[str, Any]:
    """我是谁、CSRF token、成员和项目（发布页的下拉框用）。"""
    actor, svc = me_actor(request), svc_of(request)
    sess: webauth.WebSession = request.scope["state"]["tf_web"]
    with svc.lock:
        members = [{"h": m.handle, "name": m.name} for m in sorted(svc.members.values(), key=lambda m: m.handle) if m.active]
        projects = [{"key": p.key, "name": p.name} for p in sorted(svc.projects.values(), key=lambda p: p.key)]
        name = svc.members[actor.handle].name
    return {
        "me": actor.handle,
        "name": name,
        "csrf": sess.csrf,
        "mode": "dev",
        "expires": datetime.fromtimestamp(sess.expires, TZ).isoformat(timespec="seconds"),
        "members": members,
        "projects": projects,
    }


@web.get("/home")
def web_home(request: Request) -> dict[str, Any]:
    """首页（plan 7.1）：待我处理、困难（按卡住时长）、大家在做什么、项目计数。复用 Service.home，另附标题。"""
    actor, svc = me_actor(request), svc_of(request)
    with svc.lock:
        h = svc.home(actor.handle)
        now = svc.now()
        ids: set[str] = set()
        for rows in h["mine"].values():
            ids.update(r["id"] for r in rows)
        ids.update(b["id"] for b in h["blockers"])
        ids.update(d["id"] for d in h["doing"])
        for b in h["blockers"]:
            obj = svc.blockers.get(b["id"])
            if obj is not None:
                b["stuck_min"] = max(0, int((now - obj.created_at).total_seconds() // 60))
                if obj.needs and obj.need_state == "asked":
                    b["need"] = obj.needs
                if obj.helper:
                    b["helper"] = obj.helper
        titles = svc.titles(actor.handle, sorted(ids))
        projects = []
        for p in sorted(svc.projects.values(), key=lambda p: p.key):
            projects.append({"key": p.key, "name": p.name, "counts": svc.team_status(actor, project=p.key)["counts"]})
    h["titles"] = {k: _label_env(v) for k, v in titles.items()}
    h["projects"] = projects
    return h


@web.get("/tasks")
def web_tasks(
    request: Request,
    view: str = "pool",
    project: str | None = None,
    q: str | None = None,
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
) -> dict[str, Any]:
    """任务列表：view = pool（待认领）/ doing（进行中）/ mine（我的）/ done / all（全部）。"""
    actor, svc = me_actor(request), svc_of(request)
    out = svc.list_tasks(actor, view, project, q, limit, cursor)
    for r in out["rows"]:
        _label_env(r.get("t"))
        r["st_text"] = ST_TEXT.get(r.get("st"), r.get("st"))
        r["path"] = path_of(r["id"])
    return out


@web.get("/tasks/{tid}")
def web_task(request: Request, tid: str) -> dict[str, Any]:
    return _detail(request, tid, "T-")


@web.get("/blockers/{bid}")
def web_blocker(request: Request, bid: str) -> dict[str, Any]:
    return _detail(request, bid, "B-")


@web.get("/wechat")
def web_wechat(request: Request, limit: int = Query(50, ge=1, le=200)) -> dict[str, Any]:
    """"模拟微信"：本人会收到的模板消息（来自 outbox），新的在前。正式版里这些发到手机微信。"""
    actor, svc = me_actor(request), svc_of(request)
    with svc.lock:
        rows = [(i, n) for i, n in enumerate(svc.outbox, 1) if n.get("to") == actor.handle]
    rows.reverse()
    items = []
    for i, n in rows[:limit]:
        at = n.get("at")
        items.append(
            {
                "n": i,
                "kind": n.get("kind"),
                "kind_text": KIND_TEXT.get(n.get("kind", ""), n.get("kind")),
                "text": n.get("text"),
                "subject": n.get("subject"),
                "at": mdhm(at) if isinstance(at, datetime) else None,
                "ts": at.astimezone(TZ).isoformat(timespec="seconds") if isinstance(at, datetime) else None,
                "path": path_of(n["subject"], i) if n.get("subject") else None,
            }
        )
    return {"items": items, "total": len(rows)}


# ---------------------------------------------------------------------------
# 写
# ---------------------------------------------------------------------------


@web.post("/tasks", status_code=201)
def web_task_create(request: Request, payload: CreateTaskIn) -> dict[str, Any]:
    """发布：指派给别人（对方要本人接受）、指派给自己（直接待开始），或留空等人认领。"""
    actor, svc = me_actor(request), svc_of(request)
    p = payload.model_dump()
    for k in ("body", "assignee", "project", "parent"):
        p[k] = _blank(p[k])
    res = svc.create_task(actor, **p)
    return {**res, "path": path_of(res["id"])}


@web.post("/tasks/{tid}:{action}")
def web_task_action(request: Request, tid: str, action: str, payload: ActionIn | None = Body(None)) -> dict[str, Any]:
    actor, svc = me_actor(request), svc_of(request)
    p = payload or ActionIn()
    oid = _norm(svc, tid, "T-")
    if action == "accept":
        return svc.human_accept(actor, oid, v=p.v, sha=p.sha, seq=p.seq, through=p.through)
    if action == "decline":
        return svc.human_decline(actor, oid, seq=p.seq, reason=p.reason)
    if action == "claim":
        return svc.human_claim(actor, oid, v=p.v, sha=p.sha, through=p.through)
    if action == "start":
        return svc.update_task(actor, oid, status="in_progress")
    if action == "done":
        return svc.update_task(actor, oid, status="done", note=_blank(p.note))
    if action == "release":
        return svc.human_release(actor, oid, note=_blank(p.note), to_pool=p.to_pool)
    if action == "forward":
        return svc.human_forward(actor, oid, through=p.through)
    raise DomainError("not_found", f"没有 :{action} 这个按钮。")


@web.post("/tasks/{tid}/comments", status_code=201)
def web_task_comment(request: Request, tid: str, payload: CommentIn) -> dict[str, Any]:
    actor, svc = me_actor(request), svc_of(request)
    return svc.comment(actor, _norm(svc, tid, "T-"), payload.body)


@web.post("/blockers", status_code=201)
def web_blocker_create(request: Request, payload: BlockerIn) -> dict[str, Any]:
    """人报告困难：带 need 时直接点名并通知对方（agent 报的点名要主人确认，人报的不用）。"""
    actor, svc = me_actor(request), svc_of(request)
    p = payload.model_dump()
    for k in ("detail", "tried", "task", "need"):
        p[k] = _blank(p[k])
    res = svc.report_blocker(actor, **p)
    return {**res, "path": path_of(res["id"])}


@web.post("/blockers/{bid}:{action}")
def web_blocker_action(request: Request, bid: str, action: str, payload: ActionIn | None = Body(None)) -> dict[str, Any]:
    actor, svc = me_actor(request), svc_of(request)
    p = payload or ActionIn()
    oid = _norm(svc, bid, "B-")
    if action == "help":
        return svc.human_help(actor, oid, v=p.v, sha=p.sha, through=p.through)
    if action == "ask":
        return svc.human_ask(actor, oid)
    if action == "resolve":
        body = _blank(p.body)
        if body is None:
            raise DomainError("invalid", "标记已解决要写一句是怎么解决的（body）。")
        return {**svc.comment(actor, oid, body, resolve=True), "st": "resolved"}
    if action == "forward":
        return svc.human_forward(actor, oid, through=p.through)
    raise DomainError("not_found", f"没有 :{action} 这个按钮。")


@web.post("/blockers/{bid}/comments", status_code=201)
def web_blocker_comment(request: Request, bid: str, payload: CommentIn) -> dict[str, Any]:
    actor, svc = me_actor(request), svc_of(request)
    return svc.comment(actor, _norm(svc, bid, "B-"), payload.body)


@web.post("/logout")
def web_logout(request: Request) -> Response:
    sid = webauth.cookies(request.headers).get(webauth.SESSION_COOKIE)
    sessions_of(request).delete(sid)
    resp = JSONResponse({"ok": True})
    for c in webauth.clear_cookies(secure=request.url.scheme == "https"):
        resp.headers.append("set-cookie", c)
    return resp


# ---------------------------------------------------------------------------
# 本地登录页（gateway 已查过：本地开发模式、本机来源、Host 是本机名字；否则 404）
# ---------------------------------------------------------------------------


def _login_page(status: int, title: str, paras: list[str], form: tuple[str, str, str] | None = None) -> HTMLResponse:
    body = [f"<h1>{html.escape(title)}</h1>"]
    body += [f"<p>{p}</p>" for p in paras]
    if form:
        code, handle, label = form
        body.append(
            '<form method="post" action="/dev/login">'
            f'<input type="hidden" name="code" value="{html.escape(code, quote=True)}">'
            f'<input type="hidden" name="as" value="{html.escape(handle, quote=True)}">'
            f"<button type=\"submit\">{html.escape(label)}</button></form>"
        )
    doc = (
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>Team Flow 本地登录</title></head><body>{''.join(body)}</body></html>"
    )
    headers = {**PAGE_HEADERS, "Content-Security-Policy": LOGIN_CSP, "Cache-Control": "no-store"}
    return HTMLResponse(doc, status_code=status, headers=headers)


BAD_LINK = [
    "这个登录链接无效、已经用过或已经过期。",
    "请在您自己的终端运行 <code>python -m teamflow_server.devlogin --as &lt;handle&gt;</code> 重新生成一个。",
]


def _norm_handle(raw: str | None) -> str:
    return (raw or "").strip().lstrip("@").lower()


@pages.get("/dev/login")
def dev_login_page(request: Request, code: str | None = None, as_: str | None = Query(None, alias="as")) -> HTMLResponse:
    """打开登录链接：只显示"您将以谁的身份登录"和一个「登录」按钮，不消耗登录码（GET 不产生副作用）。"""
    svc = svc_of(request)
    handle = _norm_handle(as_)
    m = svc.members.get(handle)
    if m is None or not m.active or devlogin.check(code, handle, consume=False) != devlogin.OK:
        return _login_page(403, "登录链接不能用", BAD_LINK)
    who = html.escape(m.handle) if not m.name or m.name == m.handle else f"{html.escape(m.handle)}（{html.escape(m.name)}）"
    return _login_page(
        200,
        "Team Flow 本地试用",
        [
            f"您将以 <strong>{who}</strong> 的身份登录这台电脑上的试用版。",
            "登录链接只能用一次。这个页面只在本机打开；正式版里，您的身份来自手机微信。",
        ],
        form=(code or "", handle, "登录"),
    )


async def _read_small_body(request: Request, limit: int) -> bytes | None:
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > limit:
            return None
        chunks.append(chunk)
    return b"".join(chunks)


@pages.post("/dev/login")
async def dev_login_submit(request: Request) -> Response:
    """点「登录」：Origin 必须是本站；登录码一次性消耗；发人类会话 cookie 和 CSRF cookie，303 回首页。"""
    headers = request.headers
    if not webauth.origin_ok(request.scope, headers):
        return _login_page(403, "登录没有完成", ["请从登录页点「登录」按钮。"])
    raw = await _read_small_body(request, MAX_LOGIN_BODY)
    if raw is None:
        return _login_page(413, "登录没有完成", ["请求太大。"])
    try:
        form = parse_qs(raw.decode("utf-8"), max_num_fields=8)
    except (UnicodeDecodeError, ValueError):
        form = {}
    code = (form.get("code") or [""])[0]
    handle = _norm_handle((form.get("as") or [""])[0])
    svc = svc_of(request)
    m = svc.members.get(handle)
    if m is None or not m.active:
        return _login_page(403, "登录链接不能用", BAD_LINK)
    why = await run_in_threadpool(devlogin.check, code, handle, consume=True)
    if why != devlogin.OK:
        svc._audit("web.login", Actor(handle, "human", None, None, "web"), "rejected", reason=why)
        return _login_page(403, "登录链接不能用", BAD_LINK)
    store = sessions_of(request)
    store.delete(webauth.cookies(headers).get(webauth.SESSION_COOKIE))  # 同一个地址换人登录：旧会话作废
    sid, sess = store.create(handle)
    svc._audit("web.login", Actor(handle, "human", None, None, "web"), "ok", via="dev")
    resp = RedirectResponse("/", status_code=303, headers={**PAGE_HEADERS, "Cache-Control": "no-store"})
    for c in webauth.login_cookies(sid, sess, secure=request.url.scheme == "https"):
        resp.headers.append("set-cookie", c)
    return resp


# ---------------------------------------------------------------------------
# 静态单页（router 的兜底：只有没有任何路由匹配时才到这里）
# ---------------------------------------------------------------------------

RESERVED = ("/api", "/mcp", "/dev", "/healthz")
_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".txt": "text/plain; charset=utf-8",
    ".map": "application/json",
}


def _reserved(path: str) -> bool:
    return any(path == p or path.startswith(p + "/") for p in RESERVED)


def _static_headers(html_page: bool) -> dict[str, str]:
    return {**PAGE_HEADERS, "Content-Security-Policy": CSP, "Cache-Control": "no-store" if html_page else "no-cache"}


def static_response(path: str, root: Path = WEB_DIST) -> Response | None:
    """路径对应 web_dist 里的文件就给文件；不像文件（最后一段没有扩展名）的回退到 index.html；否则 None（404）。"""
    rel = path.strip("/")
    parts = rel.split("/") if rel else []
    if any(p in ("", ".", "..") or p.startswith(".") or "\\" in p for p in parts):
        return None
    base = root.resolve()
    if parts:
        cand = (base / rel).resolve()
        if base in cand.parents and cand.is_file():
            ctype = _TYPES.get(cand.suffix.lower()) or mimetypes.guess_type(cand.name)[0] or "application/octet-stream"
            return FileResponse(cand, media_type=ctype, headers=_static_headers(cand.suffix.lower() == ".html"))
        if "." in parts[-1]:
            return None
    index = base / "index.html"
    if not index.is_file():
        return None
    return FileResponse(index, media_type=_TYPES[".html"], headers=_static_headers(True))


def spa_fallback(not_found: Any) -> Any:
    """包一层 router 的 not_found：GET/HEAD、不是 /api /mcp /dev /healthz 的路径交给静态单页，其余照旧 404。"""

    async def app(scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] == "http" and scope.get("method") in ("GET", "HEAD") and not _reserved(scope.get("path", "")):
            resp = static_response(scope.get("path", "/"))
            if resp is not None:
                await resp(scope, receive, send)
                return
            if "app" in scope:
                raise StarletteHTTPException(status_code=404, detail="没有这个页面。")
        await not_found(scope, receive, send)

    return app
