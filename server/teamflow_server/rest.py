"""REST 适配层（/api/v1，权威接口）。MCP 和 CLI 都映射到同一个 service。

端点都是同步函数：FastAPI 把它们放进线程池执行，service 的锁因此真正参与并发控制。

错误一律是 4xx JSON ``{"error": "<code>", "message": "..."}``（跨包约定），可能附带 id、by、rule 等结构化字段。

CLI 兜底命令（MCP 不可用时，plan 6.8）用到的三个端点：
- ``POST /api/v1/tasks/{id}:note``  ``{"note": "..."}`` → 200 ``{"id", "st", "new"}``
- ``POST /api/v1/tasks/{id}:done``  ``{"note": "..."}`` → 200 ``{"id", "st", "new"}``
- ``POST /api/v1/blockers`` ``{"title", "detail?", "tried?", "task?", "need?"}`` → 201 ``{"id", "st", "need_state", "suggest"}``
鉴权同其他 REST：``Authorization: Bearer tf_pat_…`` + ``X-Teamflow-Client``。
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable

from fastapi import APIRouter, Body, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

from . import __version__, config
from .errors import DomainError, rest_error
from .seed import seed
from .service import Actor, Service

router = APIRouter()

TASK_AGENT_ACTIONS = {"claim", "start", "note", "done", "release", "cancel", "edit", "update"}
TASK_HUMAN_ACTIONS = {"accept", "decline", "transfer", "forward", "reopen", "redact", "delete", "assign", "withdraw"}
BLOCKER_AGENT_ACTIONS = {"resolve"}
BLOCKER_HUMAN_ACTIONS = {"help", "ask", "edit", "forward", "reopen", "decline", "redact"}


def svc_of(request: Request) -> Service:
    return request.app.state.svc


def token_actor(request: Request, via: str = "rest") -> Actor:
    """PAT 一律按 agent 记账（H1）。gateway 已经校验过 token。不做会话归属（读接口和 hooks 用）。"""
    tok = (request.scope.get("state") or {}).get("tf_ident")
    if tok is None:
        raise DomainError("not_allowed", "未鉴权。")
    return Actor(tok.handle, "agent", tok.client, tok.token_id, via)


def agent_actor(request: Request) -> Actor:
    """写接口用：token 身份 + X-Teamflow-Session 头的会话归属（统一走 resolve_session：存在、未结束、同 token、
    同 client；不成立就是成员级并写审计）。读接口不产生事件，不做归属，免得每次读都写一条审计。"""
    actor = token_actor(request)
    sess = request.headers.get("x-teamflow-session")
    if sess:
        s = svc_of(request).resolve_session(actor.handle, actor.client, actor.token_id, sess, source="header", via="rest")
        if s is not None:
            return Actor(actor.handle, "agent", actor.client, actor.token_id, "rest", s.external_id, "exact", session_src="header")
    return actor


def human_only(request: Request) -> None:
    raise DomainError("human_only", "这个操作只能由本人在手机微信里完成，agent 和命令行都不行。")


def with_idem(request: Request, actor: Actor, payload: Any, fn: Callable[[], dict[str, Any]], status: int = 200) -> Response:
    """Idempotency-Key：同键同指纹重放原响应；处理中返回 409；指纹不同返回 422。"""
    key = request.headers.get("idempotency-key")
    svc = svc_of(request)
    if not key:
        return JSONResponse(fn(), status_code=status)
    owner = actor.token_id or actor.handle
    fp = hashlib.sha256(
        json.dumps({"m": request.method, "p": request.url.path, "b": payload}, sort_keys=True, ensure_ascii=False, default=str).encode()
    ).hexdigest()
    state, rec = svc.idem_begin("rest", owner, key, fp)
    if state == "replay" and rec is not None:
        return JSONResponse(rec.response, status_code=rec.status, headers={"Idempotent-Replayed": "true"})
    if state == "in_flight":
        raise DomainError("conflict", "同一个 Idempotency-Key 的请求还在处理中。")
    if state == "mismatch":
        return JSONResponse(rest_error("invalid", "Idempotency-Key 重复但请求内容不同。"), status_code=422)
    try:
        data = fn()
    except DomainError as e:
        svc.idem_finish("rest", owner, key, e.http_status, e.to_rest())
        raise
    except Exception:
        svc.idem_abort("rest", owner, key)
        raise
    svc.idem_finish("rest", owner, key, status, data)
    return JSONResponse(data, status_code=status)


# ---------------------------------------------------------------------------
# 健康检查
# ---------------------------------------------------------------------------


@router.get("/healthz")
def healthz(request: Request) -> dict[str, Any]:
    return {"ok": True, "v": __version__, "events": svc_of(request).latest_event_id()}


# ---------------------------------------------------------------------------
# 读
# ---------------------------------------------------------------------------


@router.get("/api/v1/me/inbox")
def me_inbox(request: Request, limit: int = Query(10, ge=1, le=20)) -> dict[str, Any]:
    return svc_of(request).inbox(token_actor(request), limit=limit)


@router.get("/api/v1/me/delta")
def me_delta(request: Request, response: Response, cursor: int = Query(0, ge=0)) -> Any:
    svc = svc_of(request)
    data = svc.delta(token_actor(request), cursor)
    snap = {k: v for k, v in data.items() if k not in ("items", "more", "cursor")}
    digest = hashlib.sha256(json.dumps(snap, sort_keys=True).encode()).hexdigest()[:12]
    etag = f'W/"{data["cursor"]}-{digest}"'
    if request.headers.get("if-none-match") == etag and not data["items"]:
        return Response(status_code=304, headers={"ETag": etag})
    response.headers["ETag"] = etag
    return data


@router.get("/api/v1/tasks")
def tasks_list(
    request: Request,
    view: str = "mine",
    project: str | None = None,
    q: str | None = None,
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
) -> dict[str, Any]:
    return svc_of(request).list_tasks(token_actor(request), view, project, q, limit, cursor)


@router.get("/api/v1/tasks/{tid}")
def task_get(request: Request, tid: str, events: int = Query(5, ge=0, le=10)) -> dict[str, Any]:
    if not tid.upper().startswith("T-"):
        raise DomainError("not_found", f"{tid} 不是任务编号。")
    return svc_of(request).get_item(token_actor(request), tid, events)


@router.get("/api/v1/blockers/{bid}")
def blocker_get(request: Request, bid: str, events: int = Query(5, ge=0, le=10)) -> dict[str, Any]:
    if not bid.upper().startswith("B-"):
        raise DomainError("not_found", f"{bid} 不是困难编号。")
    return svc_of(request).get_item(token_actor(request), bid, events)


@router.get("/api/v1/status")
def team_status(request: Request, project: str | None = None) -> dict[str, Any]:
    return svc_of(request).team_status(token_actor(request), project)


# ---------------------------------------------------------------------------
# 写（agent 和人都能用的命令）
# ---------------------------------------------------------------------------


class CreateTaskIn(BaseModel):
    title: str = Field(max_length=120)
    body: str | None = Field(None, max_length=4000)
    assignee: str | None = None
    project: str | None = None
    urgent: bool = False
    parent: str | None = None


class UpdateIn(BaseModel):
    note: str | None = Field(None, max_length=500)
    status: str | None = None
    title: str | None = Field(None, max_length=120)
    body: str | None = Field(None, max_length=4000)


class BlockerIn(BaseModel):
    title: str = Field(max_length=120)
    detail: str | None = Field(None, max_length=2000)
    tried: str | None = Field(None, max_length=1000)
    task: str | None = None
    need: str | None = None


class CommentIn(BaseModel):
    body: str = Field(max_length=2000)
    resolve: bool = False


@router.post("/api/v1/tasks")
def task_create(request: Request, payload: CreateTaskIn) -> Response:
    actor = agent_actor(request)
    svc = svc_of(request)
    p = payload.model_dump()
    return with_idem(request, actor, p, lambda: svc.create_task(actor, **p), status=201)


@router.post("/api/v1/tasks/{tid}:{action}")
def task_command(request: Request, tid: str, action: str, payload: dict[str, Any] | None = Body(None)) -> Response:
    if action in TASK_HUMAN_ACTIONS:
        human_only(request)  # 先判人类专属，再校验请求体
    if action not in TASK_AGENT_ACTIONS:
        raise DomainError("not_found", f"没有 :{action} 这个命令。")
    actor = agent_actor(request)
    svc = svc_of(request)
    try:
        p = UpdateIn.model_validate(payload or {}).model_dump()
    except ValidationError as e:
        first = e.errors()[0]
        loc = ".".join(str(x) for x in first.get("loc", ()))
        raise DomainError("invalid", f"请求体不合法：{loc} {first.get('msg')}", status=422) from None
    fixed = {"start": "in_progress", "done": "done", "release": "open", "cancel": "canceled"}
    status = fixed[action] if action in fixed else (p.get("status") if action == "update" else None)

    def run() -> dict[str, Any]:
        if action == "claim":
            return svc.claim_task(actor, tid)
        if action == "note" and not p.get("note"):
            raise DomainError("invalid", "note 不能为空。")
        if action == "edit" and p.get("title") is None and p.get("body") is None:
            raise DomainError("invalid", "编辑要给 title 或 body。")
        return svc.update_task(
            actor,
            tid,
            note=p.get("note"),
            status=status,
            title=p.get("title") if action in ("edit", "update") else None,
            body=p.get("body") if action in ("edit", "update") else None,
        )

    return with_idem(request, actor, {"tid": tid, "action": action, **p}, run)


@router.delete("/api/v1/tasks/{tid}")
def task_delete(request: Request, tid: str) -> None:
    human_only(request)


@router.post("/api/v1/blockers")
def blocker_create(request: Request, payload: BlockerIn) -> Response:
    actor = agent_actor(request)
    svc = svc_of(request)
    p = payload.model_dump()
    return with_idem(request, actor, p, lambda: svc.report_blocker(actor, **p), status=201)


@router.post("/api/v1/blockers/{bid}:{action}")
def blocker_command(request: Request, bid: str, action: str, payload: dict[str, Any] | None = Body(None)) -> Response:
    if action in BLOCKER_HUMAN_ACTIONS:
        human_only(request)
    if action not in BLOCKER_AGENT_ACTIONS:
        raise DomainError("not_found", f"没有 :{action} 这个命令。")
    actor = agent_actor(request)
    svc = svc_of(request)
    body = (payload or {}).get("body")
    if not isinstance(body, str) or not body.strip():
        raise DomainError("invalid", "标记已解决要写怎么解决的（body）。")
    return with_idem(request, actor, {"bid": bid, "body": body}, lambda: svc.comment(actor, bid, body, resolve=True))


@router.post("/api/v1/tasks/{tid}/comments")
def task_comment(request: Request, tid: str, payload: CommentIn) -> Response:
    actor = agent_actor(request)
    svc = svc_of(request)
    if payload.resolve:
        raise DomainError("invalid", "resolve 只用于困难。")
    return with_idem(request, actor, {"tid": tid, **payload.model_dump()}, lambda: svc.comment(actor, tid, payload.body), status=201)


@router.post("/api/v1/blockers/{bid}/comments")
def blocker_comment(request: Request, bid: str, payload: CommentIn) -> Response:
    actor = agent_actor(request)
    svc = svc_of(request)
    return with_idem(
        request, actor, {"bid": bid, **payload.model_dump()}, lambda: svc.comment(actor, bid, payload.body, payload.resolve), status=201
    )


# ---------------------------------------------------------------------------
# hooks
# ---------------------------------------------------------------------------


@router.post("/api/v1/hooks/session-start")
def hook_session_start(request: Request, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    # hooks 自己登记会话，不按请求头做会话归属（会话可能还没登记）
    return svc_of(request).hook_session_start(token_actor(request, "hook"), payload)


@router.post("/api/v1/hooks/batch")
def hook_batch(request: Request, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    items = payload.get("items")
    if not isinstance(items, list):
        raise DomainError("invalid", "items 必须是数组。")
    return svc_of(request).hook_batch(token_actor(request, "hook"), items)


# ---------------------------------------------------------------------------
# DEV ONLY：模拟"人在手机微信里操作"。M1 上线前删除。
# 默认关闭（TEAMFLOW_DEV_ENDPOINTS 缺省为 0）；打开时还要带 X-Teamflow-Dev-Secret，值等于 TEAMFLOW_DEV_SECRET，
# 未设置密钥则一律 404（gateway 先挡一次，这里再查一次）。带任何 Authorization（PAT）一律 403 human_only。
# 人类动作必须带页面上看到的值：接受 v、sha、seq、through；认领、帮忙 v、sha、through；转发 through（I1、复审新问题 1）。
# through 是详情页渲染时最大的动态编号：缺失 400 invalid；超过当前最大事件 ID 也是 400（与转发一致）。
# ---------------------------------------------------------------------------


class DevActionIn(BaseModel):
    v: int | None = None
    sha: str | None = None
    seq: int | None = None
    through: int | None = None


def dev_human(request: Request) -> Actor:
    ok, _ = config.dev_access_ok(request.headers.get("x-teamflow-dev-secret"))
    if not ok:
        raise DomainError("not_found", "没有这个端点。")
    if request.client is None or request.client.host not in ("127.0.0.1", "::1", "localhost"):
        raise DomainError("not_found", "没有这个端点。")
    if request.headers.get("authorization"):
        raise DomainError("human_only", "DEV ONLY：这是模拟手机上本人操作的端点，PAT 不能调用。")
    h = (request.headers.get("x-teamflow-dev-human") or "").strip().lower()
    if not h or h not in svc_of(request).members:
        raise DomainError("human_only", "DEV ONLY：缺少模拟的人类会话（X-Teamflow-Dev-Human: <handle>）。")
    return Actor(h, "human", None, None, "dev")


@router.get("/api/v1/dev/items/{oid}")
def dev_item(request: Request, oid: str) -> dict[str, Any]:
    """模拟手机详情页：表单里会带的 v、sha、seq（任务）和 through（页面渲染时最大的动态编号）。

    接受、认领、帮忙、转发都要把这里的 through 原样带回：页面渲染之后才出现的动态编号比它大，
    不会算作本人已看到，也就不会放给本人的 agent。"""
    dev_human(request)
    return svc_of(request).page_view(oid)


@router.get("/api/v1/dev/home")
def dev_home(request: Request) -> dict[str, Any]:
    """模拟手机首页（7.1）的结构化数据。「大家在做什么」里精确归属到会话的任务带会话短标签。"""
    actor = dev_human(request)
    return svc_of(request).home(actor.handle)


@router.post("/api/v1/dev/tasks/{tid}:{action}")
def dev_task(request: Request, tid: str, action: str, payload: DevActionIn | None = Body(None)) -> dict[str, Any]:
    actor = dev_human(request)
    svc = svc_of(request)
    p = payload or DevActionIn()
    if action == "accept":
        return svc.human_accept(actor, tid, v=p.v, sha=p.sha, seq=p.seq, through=p.through)
    if action == "claim":
        return svc.human_claim(actor, tid, v=p.v, sha=p.sha, through=p.through)
    if action == "forward":
        return svc.human_forward(actor, tid, through=p.through)
    raise DomainError("not_found", f"DEV 没有 :{action}。")


@router.post("/api/v1/dev/blockers/{bid}:{action}")
def dev_blocker(request: Request, bid: str, action: str, payload: DevActionIn | None = Body(None)) -> dict[str, Any]:
    actor = dev_human(request)
    svc = svc_of(request)
    p = payload or DevActionIn()
    if action == "help":
        return svc.human_help(actor, bid, v=p.v, sha=p.sha, through=p.through)
    if action == "ask":
        return svc.human_ask(actor, bid)
    if action == "forward":
        return svc.human_forward(actor, bid, through=p.through)
    raise DomainError("not_found", f"DEV 没有 :{action}。")


@router.get("/api/v1/dev/outbox")
def dev_outbox(request: Request, to: str | None = None) -> dict[str, Any]:
    dev_human(request)
    rows = [
        {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in n.items()}
        for n in svc_of(request).outbox
        if to is None or n["to"] == to
    ]
    return {"items": rows}


@router.post("/api/v1/dev/reset")
def dev_reset(request: Request) -> dict[str, Any]:
    """清空并重新播种。受同一个开关和密钥管。"""
    dev_human(request)
    svc = svc_of(request)
    seed(svc)
    return {"ok": True, "events": svc.latest_event_id()}
