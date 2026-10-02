"""组装：FastAPI（REST）+ FastMCP 4 无状态 HTTP app 挂在 /mcp（客户端 URL 用 /mcp/）+ HTTP 网关。

启动：``uvicorn teamflow_server.app:app --port 8100 --workers 1``

两代协议：FastMCP 4.0.10（底层官方 mcp 2.2.0 的 StreamableHTTPSessionManager）在同一个端点上按
``MCP-Protocol-Version`` 请求头分流——头缺失或是握手代版本（2024-11-05…2025-11-25）走旧代
无状态处理器（接受 initialize，不发 Mcp-Session-Id）；其余值（2026-07-28）走新代单次交换处理器
（server/discover、Mcp-Method/Mcp-Name 头校验、无 initialize）。不需要额外开关。
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import __version__, config
from .errors import DomainError, rest_error
from .gateway import Gateway
from .mcp_server import build_mcp
from .rest import router
from .seed import seed
from .service import Service


def create_app(service: Service | None = None, *, with_seed: bool = True) -> FastAPI:
    svc = service or Service()
    if with_seed:
        seed(svc)
    mcp = build_mcp(svc)
    mcp_app = mcp.http_app(path="/", stateless_http=True, json_response=config.mcp_json_response())

    app = FastAPI(
        title="Team Flow",
        version=__version__,
        lifespan=mcp_app.lifespan,  # FastMCP 的 session manager 必须由外层 app 的 lifespan 启动
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.router.redirect_slashes = False  # 不要任何尾斜杠 307；/mcp 由 Gateway 在应用内改写
    app.state.svc = svc
    app.state.mcp = mcp

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
        return JSONResponse(rest_error(code, str(exc.detail)), status_code=exc.status_code, headers=getattr(exc, "headers", None))

    app.include_router(router)
    app.mount("/mcp", mcp_app)
    app.add_middleware(Gateway)
    return app


app = create_app()
