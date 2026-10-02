"""组装：FastAPI（REST）+ FastMCP 4 无状态 HTTP app 挂在 /mcp（客户端 URL 用 /mcp/）+ HTTP 网关。

启动：``TEAMFLOW_DEV_TOKENS="tf_pat_<随机>:alice:claude_code,..." uvicorn teamflow_server.app:app --port 8100 --workers 1``
（TEAMFLOW_DEV_TOKENS 没有缺省值：不设时没有任何有效令牌，启动时在 stderr 提示一行。）

两代协议：FastMCP 4.0.10（底层官方 mcp 2.2.0 的 StreamableHTTPSessionManager）在同一个端点上按
``MCP-Protocol-Version`` 请求头分流——头缺失或是握手代版本（2024-11-05…2025-11-25）走旧代
无状态处理器（接受 initialize，不发 Mcp-Session-Id）；其余值（2026-07-28）走新代单次交换处理器
（server/discover、Mcp-Method/Mcp-Name 头校验、无 initialize）。不需要额外开关。
"""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import __version__, config, devlogin, webauth
from .errors import DomainError, rest_error
from .gateway import Gateway
from .mcp_server import build_mcp
from .rest import router
from .seed import seed
from .service import Service
from .web import pages, spa_fallback, web


def create_app(service: Service | None = None, *, with_seed: bool = True) -> FastAPI:
    svc = service or Service()
    if with_seed:
        seed(svc)
    mcp = build_mcp(svc)
    mcp_app = mcp.http_app(path="/", stateless_http=True, json_response=config.mcp_json_response())

    @asynccontextmanager
    async def lifespan(app: Any) -> AsyncIterator[None]:
        # 启动时：没配令牌就在 stderr 打一行提示（不含任何令牌），否则所有请求 401 时不好查
        hint = config.tokens_hint()
        if hint:
            print(hint, file=sys.stderr, flush=True)
        if config.dev_endpoints_enabled():
            announce_login_links(svc)
        async with mcp_app.lifespan(app):  # FastMCP 的 session manager 必须由外层 app 的 lifespan 启动
            yield

    app = FastAPI(
        title="Team Flow",
        version=__version__,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.router.redirect_slashes = False  # 不要任何尾斜杠 307；/mcp 由 Gateway 在应用内改写
    app.state.svc = svc
    app.state.mcp = mcp
    app.state.web_sessions = webauth.WebSessions()

    # REST 错误一律 {"error": code, "message": ...}（跨包约定），包括请求体校验失败和路由级 404/405
    @app.exception_handler(DomainError)
    async def _domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(exc.to_rest(), status_code=exc.http_status)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        errs = exc.errors()
        first = errs[0] if errs else {}
        loc = ".".join(str(x) for x in first.get("loc", ()) if x != "body")
        msg = f"请求体不合法：{loc} {first.get('msg', '')}".strip()
        return JSONResponse(rest_error("invalid", msg, field=loc or None), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, f"http_{exc.status_code}")
        # no_route：没有这个接口（不是"没有这一项"）。本地试用里多半是网页更新了、在跑的服务端还是旧代码，网页据此提示重跑 local-up.sh
        extra = {"no_route": True} if exc.status_code == 404 else {}
        return JSONResponse(rest_error(code, str(exc.detail), **extra), status_code=exc.status_code, headers=getattr(exc, "headers", None))

    app.include_router(router)
    app.include_router(web)
    app.include_router(pages)
    app.mount("/mcp", mcp_app)
    # 没有任何路由匹配的 GET/HEAD（/api、/mcp、/dev、/healthz 以外）交给静态单页；405 等仍由 router 判
    app.router.default = spa_fallback(app.router.default)
    app.add_middleware(Gateway)
    return app


def announce_login_links(svc: Service) -> None:
    """本地开发模式启动时：每个成员一个一次性登录码，链接打到 stderr（码的 sha256 写进 TEAMFLOW_STATE）。

    有令牌的成员排在前面（按 TEAMFLOW_DEV_TOKENS 里的顺序）：第 1 个用 127.0.0.1、第 2 个用 localhost，
    本地试用时"您"和第一个模拟队友在同一个浏览器里就能同时登录。"""
    order = {h: i for i, h in enumerate(config.token_handles())}
    active = [m for m in svc.members.values() if m.active]
    active.sort(key=lambda m: order.get(m.handle, len(order)))  # sort 是稳定的：其余成员保持原顺序
    members = [(m.handle, m.name) for m in active]
    try:
        links = devlogin.startup(members)
    except OSError as e:
        print(f"teamflow-server: 本地登录码写不进 {config.state_dir()}（{e.__class__.__name__}），网页登录不可用。", file=sys.stderr, flush=True)
        return
    print(devlogin.banner(links), file=sys.stderr, flush=True)


app = create_app()
