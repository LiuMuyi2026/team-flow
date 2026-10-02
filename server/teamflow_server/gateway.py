"""HTTP 层网关（纯 ASGI 中间件）。REST 和 MCP 共用，agent 绕过 MCP 直接 curl 也走这里。

按顺序做这几件事：
1. 路径规范化：``/mcp`` 在应用内改写成 ``/mcp/``（等价于 nginx 的内部改写），两者都不返回 3xx。
2. DEV 端点的门（B1）：``/api/v1/dev/*`` 默认关闭；打开（TEAMFLOW_DEV_ENDPOINTS=1）时还要带
   ``X-Teamflow-Dev-Secret``，值等于 TEAMFLOW_DEV_SECRET；未设置密钥、密钥不对、开关没开，一律 404。
   本地网页入口（``/dev/login``、``/api/v1/web/*``）另有一道门（``webauth.local_gate``）：开关打开、对端是本机、
   没有转发头、Host 是本机名字，否则 404。网页 API 只认人类会话 cookie：带 ``Authorization`` 一律 403
   ``human_only``，没有有效会话 401，写请求要过 CSRF（Origin + X-CSRF-Token 双提交）否则 403 ``csrf``。
3. 鉴权：``Authorization: Bearer tf_pat_…``，只来自 TEAMFLOW_DEV_TOKENS（没有缺省令牌）；缺失或错误返回 401 并带 WWW-Authenticate。
   ``/mcp/`` 和 ``/api/v1/hooks`` 完全忽略 Cookie 头；``/mcp/`` 上出现不在白名单的 Origin 返回 403。
   **先鉴权再读请求体**（m7）：未鉴权的请求一个字节的请求体都不读。
4. 请求体上限 64KB（``/mcp/`` 和应用内 REST ``/api/*`` 都是）：Content-Length 超了直接 413，分块传输读到超过也 413。
   ``/mcp/`` 返回 JSON-RPC 错误，REST 返回 ``{"error": "too_large", ...}``。同样是鉴权（DEV 端点是开关和密钥）
   通过之后才读，未鉴权的大请求体直接 401/404。生产 nginx 也设 ``client_max_body_size 64k``，这里是兜底。
5. 故障注入：TEAMFLOW_FAULT_DELAY_MS 让 ``/api/v1/hooks/*`` 和 ``/api/v1/me/*`` 延迟返回。
6. 把鉴权结果和解析出的 JSON-RPC 信息放进 ``scope["state"]``，供 REST 依赖和 MCP 工具读取。
7. 新代 -32022（版本不支持）的 ``data.supported`` 补上旧代版本：SDK 的传输层写死只列新代（m6）。
8. 观测日志：每个请求往 TEAMFLOW_LOG 追加一行 JSON（不记请求体和查询串，只记协议元数据；
   x-codex-turn-metadata 只留 session_id、thread_id、turn_id）。
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
from datetime import datetime
from typing import Any

from mcp_types.version import HANDSHAKE_PROTOCOL_VERSIONS, MODERN_PROTOCOL_VERSIONS
from starlette.datastructures import Headers

from . import config, webauth
from .errors import rest_error
from .service import TZ, tool_use_id

PV_KEY = "io.modelcontextprotocol/protocolVersion"
CI_KEY = "io.modelcontextprotocol/clientInfo"
CODEX_TURN_KEY = "x-codex-turn-metadata"
CLAUDE_TOOL_USE_KEY = "claudecode/toolUseId"  # Claude Code 的 tools/call 带；等于 PostToolUse 的 tool_use_id（S3）

_log_lock = threading.Lock()
_last_init: dict[str, dict[str, Any]] = {}  # token_id → 最近一次 initialize 的 {pv, ci}（旧代后续请求不再带 clientInfo）
_MAX_CAPTURE = 256 * 1024
MAX_BODY = 64 * 1024  # 请求体上限：9 个工具、REST 正文最长 4000 字，64KB 绰绰有余（SDK 默认 4MB）
MAX_MCP_BODY = MAX_BODY
MAX_REST_BODY = MAX_BODY
_BODY_METHODS = ("POST", "PUT", "PATCH", "DELETE")
_MAX_LOG_VALUE = 4096
UNSUPPORTED_PROTOCOL_VERSION = -32022


def _cap(value: Any) -> Any:
    """客户端提供的结构（clientInfo、x-codex-turn-metadata）原样记录，但单项超过 4KB 就截断成字符串。"""
    try:
        raw = json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)[:_MAX_LOG_VALUE]
    return value if len(raw) <= _MAX_LOG_VALUE else raw[:_MAX_LOG_VALUE] + "…[truncated]"


def write_log(rec: dict[str, Any]) -> None:
    path = config.log_path()
    line = json.dumps(rec, ensure_ascii=False, separators=(",", ":"), default=str)
    try:
        with _log_lock:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except OSError:
        pass  # 观测日志写失败不能影响请求


def _era(pv: str | None) -> str | None:
    if pv in MODERN_PROTOCOL_VERSIONS:
        return "modern"
    if pv in HANDSHAKE_PROTOCOL_VERSIONS:
        return "legacy"
    return None if pv is None else "unknown"


def parse_rpc(body: bytes, headers: Headers) -> dict[str, Any]:
    """从请求体和头里推断协议代际与版本、clientInfo、method、工具名、_meta 键。"""
    info: dict[str, Any] = {}
    hpv = headers.get("mcp-protocol-version")
    # SDK 按 MCP-Protocol-Version 头分流：头缺失或是握手代版本 → 旧代处理器；其他值 → 新代处理器
    info["route"] = "modern" if (hpv is not None and hpv not in HANDSHAKE_PROTOCOL_VERSIONS) else "legacy"
    try:
        msg = json.loads(body) if body else None
    except (ValueError, RecursionError):
        info["parse_error"] = True
        return info
    if isinstance(msg, list):
        info["batch"] = len(msg)
        msg = msg[0] if msg and isinstance(msg[0], dict) else None
    if not isinstance(msg, dict):
        return info
    method = msg.get("method")
    if method is None and ("result" in msg or "error" in msg):
        method = "<response>"
    info["rpc"] = method
    if "id" in msg:
        info["rpc_id"] = msg.get("id")
    params = msg.get("params") if isinstance(msg.get("params"), dict) else {}
    meta = params.get("_meta") if isinstance(params.get("_meta"), dict) else None
    if method == "tools/call":
        info["tool"] = params.get("name")
    pv: Any = None
    ci: Any = None
    if method == "initialize":
        pv, src, ci = params.get("protocolVersion"), "initialize", params.get("clientInfo")
    elif meta is not None and PV_KEY in meta:
        pv, src, ci = meta.get(PV_KEY), "meta", meta.get(CI_KEY)
    elif hpv:
        pv, src = hpv, "header"
    else:
        src = "none"
    info["pv"] = pv
    info["pv_src"] = src
    info["gen"] = _era(pv if isinstance(pv, str) else None) or ("legacy" if src == "none" else None)
    if hpv is not None:
        info["hpv"] = hpv
    if ci is not None:
        info["ci"] = ci
    if meta is not None:
        info["meta_keys"] = sorted(meta.keys())
        if CODEX_TURN_KEY in meta:
            info["codex_turn"] = codex_turn_fields(meta[CODEX_TURN_KEY])  # 只留 session_id、thread_id、turn_id
        if "callId" in meta:
            info["call_id"] = meta["callId"]
        if CLAUDE_TOOL_USE_KEY in meta:
            tu = meta[CLAUDE_TOOL_USE_KEY]
            if tool_use_id(tu):
                info["tool_use_id"] = tu  # 不透明 ID，记进日志方便和 hooks 上报的 tool_map 对照
            else:
                info["tool_use_bad"] = True
        info["meta"] = meta  # 只放进 scope，不写日志
    return info


def codex_turn_fields(turn: Any) -> dict[str, Any] | None:
    """plan 6.5：x-codex-turn-metadata（对象或 JSON 字符串）只保留 session_id、thread_id、turn_id，
    repo_root 等其余字段丢弃。日志和 MCP 归属共用。"""
    if isinstance(turn, str):
        try:
            turn = json.loads(turn)
        except (ValueError, RecursionError):
            return None
    if not isinstance(turn, dict):
        return None
    return {k: str(turn[k])[:128] for k in ("session_id", "thread_id", "turn_id") if isinstance(turn.get(k), (str, int))}


def augment_unsupported_version(body: bytes) -> bytes | None:
    """-32022 的 data.supported 补上旧代（握手代）版本，新代在前。不是 -32022 就返回 None（原样转发）。

    规范示例里双代服务端列出两代（basic/versioning：``"supported": ["2026-07-28", "2025-11-25"]``）；
    mcp 2.2.0 的 streamable HTTP 传输层写死只列 MODERN_PROTOCOL_VERSIONS，没有配置项，所以在网关里补。
    """
    try:
        obj = json.loads(body)
    except (ValueError, UnicodeDecodeError, RecursionError):
        return None
    if not isinstance(obj, dict) or not isinstance(obj.get("error"), dict):
        return None
    err = obj["error"]
    data = err.get("data")
    if err.get("code") != UNSUPPORTED_PROTOCOL_VERSION or not isinstance(data, dict) or not isinstance(data.get("supported"), list):
        return None
    merged = list(data["supported"])
    for v in (*reversed(MODERN_PROTOCOL_VERSIONS), *reversed(HANDSHAKE_PROTOCOL_VERSIONS)):
        if v not in merged:
            merged.append(v)
    data["supported"] = merged
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _summarize_response(ctype: str, body: bytes) -> dict[str, Any]:
    """从响应里抽出 JSON-RPC 错误码、isError、我们的业务错误码、协商出的版本。"""
    obj: Any = None
    try:
        if "application/json" in ctype:
            obj = json.loads(body)
        elif "text/event-stream" in ctype:
            for line in body.decode("utf-8", "replace").splitlines():
                if line.startswith("data:"):
                    try:
                        cand = json.loads(line[5:].strip())
                    except ValueError:
                        continue
                    if isinstance(cand, dict) and ("result" in cand or "error" in cand):
                        obj = cand
    except (ValueError, UnicodeDecodeError):
        return {}
    out: dict[str, Any] = {}
    if not isinstance(obj, dict):
        return out
    if isinstance(obj.get("error"), dict):
        out["rpc_err"] = obj["error"].get("code")
    res = obj.get("result")
    if isinstance(res, dict):
        if "isError" in res:
            out["is_error"] = res["isError"]
        sc = res.get("structuredContent")
        if isinstance(sc, dict) and "err" in sc:
            out["tf_err"] = sc["err"]
        if "protocolVersion" in res:
            out["pv_resp"] = res["protocolVersion"]
        if "supportedVersions" in res:
            out["supported"] = res["supportedVersions"]
    if isinstance(obj.get("error"), str):  # REST：{"error": code, "message": ...}
        out["tf_err"] = obj["error"]
    return out


def _bearer(headers: Headers) -> str | None:
    auth = headers.get("authorization")
    if not auth:
        return None
    scheme, _, tok = auth.partition(" ")
    return tok.strip() if scheme.lower() == "bearer" and tok.strip() else ""


# 网页 API 的响应一律不缓存、不嗅探类型
WEB_HEADERS: tuple[tuple[bytes, bytes], ...] = ((b"cache-control", b"no-store"), (b"x-content-type-options", b"nosniff"))


def _web_sessions(scope: dict[str, Any]) -> webauth.WebSessions | None:
    app = scope.get("app")
    store = getattr(getattr(app, "state", None), "web_sessions", None)
    return store if isinstance(store, webauth.WebSessions) else None


async def _send_json(send: Any, status: int, body: dict[str, Any], extra_headers: tuple[tuple[bytes, bytes], ...] = ()) -> None:
    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = [(b"content-type", b"application/json"), (b"content-length", str(len(raw)).encode())] + list(extra_headers)
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": raw})


class Gateway:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        t0 = time.perf_counter()
        orig_path = scope["path"]
        path = orig_path
        if path == "/mcp":
            path = "/mcp/"
            scope["path"] = path
            scope["raw_path"] = b"/mcp/"
        is_mcp = path == "/mcp/" or path.startswith("/mcp/")
        is_api = path.startswith("/api/")
        is_dev = path.startswith("/api/v1/dev/")
        is_web = path == "/api/v1/web" or path.startswith("/api/v1/web/")
        is_login = path == "/dev/login"
        method = scope.get("method", "GET")
        headers = Headers(scope=scope)
        state = scope.setdefault("state", {})

        rec: dict[str, Any] = {
            "ts": datetime.now(TZ).isoformat(timespec="milliseconds"),
            "m": method,
            "path": orig_path,
        }
        if orig_path != path:
            rec["rewritten"] = path
        for hk, rk in (
            ("x-teamflow-session", "sess"),
            ("x-teamflow-client", "tf_client"),
            ("user-agent", "ua"),
            ("mcp-method", "h_method"),
            ("mcp-name", "h_name"),
            ("mcp-session-id", "h_session"),
            ("origin", "origin"),
        ):
            v = headers.get(hk)
            if v is not None:
                rec[rk] = v[:200]

        def done(st: int, **more: Any) -> None:
            rec.update({"st": st, "ms": round((time.perf_counter() - t0) * 1000, 1), **more})
            write_log(rec)

        # /mcp/ 与 /api/v1/hooks 完全忽略 Cookie
        if is_mcp or path.startswith("/api/v1/hooks"):
            scope["headers"] = [(k, v) for k, v in scope["headers"] if k.lower() != b"cookie"]

        # DEV 端点的门（B1）：开关、密钥任一不满足都 404，和"没有这个端点"无法区分
        if is_dev:
            ok, why = config.dev_access_ok(headers.get("x-teamflow-dev-secret"))
            if not ok:
                await _send_json(send, 404, rest_error("not_found", "没有这个端点。"))
                done(404, dev=why)
                return
            dh = headers.get("x-teamflow-dev-human")
            if dh:
                rec["dev_human"] = dh[:32]

        # 本地网页入口（/dev/login、/api/v1/web/*）：开关、本机来源、没有转发头、Host 是本机名字，否则 404
        if is_web or is_login:
            why = webauth.local_gate(scope, headers)
            if why:
                await _send_json(send, 404, rest_error("not_found", "没有这个端点。"))
                done(404, web=why)
                return
        if is_login and headers.get("authorization") is not None:
            # 带着 PAT 来要人类会话的只可能是 agent（浏览器打开登录链接不会带 Authorization）
            await _send_json(send, 403, rest_error("human_only", "登录链接只给本人在浏览器里打开，PAT 不能换成网页会话。"))
            done(403, web="pat", tf_err="human_only")
            return
        if is_web:
            # 硬规则 1：网页 API 只认人类会话，PAT（任何 Authorization 头）一律 403，不看它是否有效
            if headers.get("authorization") is not None:
                await _send_json(
                    send,
                    403,
                    rest_error("human_only", "网页接口只认您本人登录后的网页会话；PAT 和 Authorization 头一律不行。"),
                    WEB_HEADERS,
                )
                done(403, web="pat", tf_err="human_only")
                return
            store = _web_sessions(scope)
            web_sess = store.get(webauth.cookies(headers).get(webauth.SESSION_COOKIE)) if store else None
            if web_sess is None:
                await _send_json(
                    send,
                    401,
                    rest_error(
                        "unauthorized",
                        "还没登录，或者登录已过期。请在您自己的终端运行 python -m teamflow_server.devlogin --as <handle> 拿登录链接。",
                    ),
                    WEB_HEADERS,
                )
                done(401, web="no_session", tf_err="unauthorized")
                return
            if method not in webauth.SAFE_METHODS:
                prob = webauth.csrf_problem(scope, headers, web_sess)
                if prob:
                    await _send_json(
                        send,
                        403,
                        rest_error("csrf", "这个请求没通过 CSRF 检查：写操作要从本站页面发出，并带上 X-CSRF-Token。", why=prob),
                        WEB_HEADERS,
                    )
                    done(403, web=f"csrf_{prob}", tf_err="csrf")
                    return
            state["tf_web"] = web_sess
            rec["h"] = web_sess.handle
            rec["web"] = "ok"

        # 鉴权：先于读请求体（m7）
        tok_rec = None
        needs_auth = (is_mcp or is_api) and not is_dev and not is_web
        if needs_auth:
            tok = _bearer(headers)
            tok_rec = config.tokens().get(tok) if tok else None
            if tok_rec is None:
                if tok is None:
                    www = 'Bearer realm="teamflow"'
                    msg = "缺少令牌：请求头需要 Authorization: Bearer tf_pat_…"
                else:
                    www = 'Bearer realm="teamflow", error="invalid_token", error_description="unknown or revoked token"'
                    msg = "令牌无效或已停用，请运行 teamflow doctor 检查。"
                if is_mcp:
                    payload: dict[str, Any] = {"jsonrpc": "2.0", "id": None, "error": {"code": -32001, "message": msg}}
                else:
                    payload = rest_error("unauthorized", msg)
                await _send_json(send, 401, payload, ((b"www-authenticate", www.encode()),))
                done(401, auth="missing" if tok is None else "invalid")
                return
            state["tf_ident"] = tok_rec
            rec["h"] = tok_rec.handle
            rec["tok_client"] = tok_rec.client

        if is_mcp:
            origin = headers.get("origin")
            if origin and origin.rstrip("/") not in config.allowed_origins():
                await _send_json(send, 403, {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Origin not allowed"}})
                done(403)
                return

        # 请求体：鉴权通过后才读，读出来（MCP 还要解析），再原样回放给下游；/mcp/ 与 /api/* 都是上限 64KB
        if (is_mcp and method == "POST") or (is_api and method in _BODY_METHODS):
            if is_mcp:
                too_large: dict[str, Any] = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32600, "message": "Request body too large (max 64KB)"},
                }
                limit = MAX_MCP_BODY
            else:
                limit = MAX_REST_BODY
                too_large = rest_error("too_large", "请求体超过 64KB 上限，请精简后重试。", max=limit)
            try:
                declared = int(headers.get("content-length") or 0)
            except ValueError:
                declared = 0
            err_tag = {} if is_mcp else {"tf_err": "too_large"}
            if declared > limit:
                await _send_json(send, 413, too_large)
                done(413, body_limit="content-length", **err_tag)
                return
            chunks: list[bytes] = []
            more = True
            total = 0
            while more:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                total += len(chunk)
                if total > limit:
                    await _send_json(send, 413, too_large)
                    done(413, body_limit="stream", **err_tag)
                    return
                chunks.append(chunk)
                more = message.get("more_body", False)
            body = b"".join(chunks)
            replayed = False
            orig_receive = receive

            async def replay() -> dict[str, Any]:
                nonlocal replayed
                if not replayed:
                    replayed = True
                    return {"type": "http.request", "body": body, "more_body": False}
                return await orig_receive()

            receive = replay

        if is_mcp and method == "POST":
            rpc = parse_rpc(body, headers)
            state["tf_rpc"] = rpc
            rec.update({k: (_cap(v) if k in ("ci", "codex_turn", "call_id") else v) for k, v in rpc.items() if k != "meta"})
            if tok_rec is not None:
                if rpc.get("rpc") == "initialize":
                    _last_init[tok_rec.token_id] = {"pv": rpc.get("pv"), "ci": rpc.get("ci")}
                elif "ci" not in rpc and tok_rec.token_id in _last_init:
                    rec["ci_last"] = _last_init[tok_rec.token_id]

        # 故障注入
        if path.startswith("/api/v1/hooks/") or path.startswith("/api/v1/me/"):
            delay = config.fault_delay_ms()
            if delay:
                rec["fault_delay_ms"] = delay
                await asyncio.sleep(delay / 1000)

        status_box: dict[str, Any] = {"st": None, "ctype": "", "resp_session": None}
        captured: list[bytes] = []
        size = 0
        capture = is_mcp or is_api
        held: dict[str, Any] = {"start": None, "body": []}  # /mcp 的 400 JSON 响应先扣下，可能要改写 -32022

        async def send_wrapper(message: dict[str, Any]) -> None:
            nonlocal size
            if message["type"] == "http.response.start":
                if is_web:
                    have = {k.lower() for k, _ in message.get("headers", [])}
                    extra = [(k, v) for k, v in WEB_HEADERS if k not in have]
                    if extra:
                        message = {**message, "headers": [*message.get("headers", []), *extra]}
                status_box["st"] = message["status"]
                for k, v in message.get("headers", []):
                    lk = k.lower()
                    if lk == b"content-type":
                        status_box["ctype"] = v.decode("latin-1")
                    elif lk == b"mcp-session-id":
                        status_box["resp_session"] = v.decode("latin-1")[:64]
                    elif lk == b"location":
                        status_box["location"] = v.decode("latin-1")[:200]
                if is_mcp and message["status"] == 400 and "application/json" in status_box["ctype"]:
                    held["start"] = message
                    return
            elif message["type"] == "http.response.body":
                if held["start"] is not None:
                    held["body"].append(message.get("body", b""))
                    if message.get("more_body", False):
                        return
                    raw = b"".join(held["body"])
                    new = augment_unsupported_version(raw)
                    start_msg = held["start"]
                    held["start"] = None
                    if new is not None:
                        raw = new
                        hdrs = [(k, v) for k, v in start_msg.get("headers", []) if k.lower() != b"content-length"]
                        hdrs.append((b"content-length", str(len(raw)).encode()))
                        start_msg = {**start_msg, "headers": hdrs}
                    if capture:
                        captured.append(raw[:_MAX_CAPTURE])
                        size += len(raw)
                    await send(start_msg)
                    await send({"type": "http.response.body", "body": raw, "more_body": False})
                    return
                if capture and size < _MAX_CAPTURE:
                    chunk = message.get("body", b"")
                    captured.append(chunk[: _MAX_CAPTURE - size])
                    size += len(chunk)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            status_box["st"] = status_box["st"] or 500
            raise
        finally:
            rec["st"] = status_box["st"]
            rec["ms"] = round((time.perf_counter() - t0) * 1000, 1)
            if status_box.get("location"):
                rec["location"] = status_box["location"]
            if status_box["resp_session"]:
                rec["resp_mcp_session_id"] = status_box["resp_session"]
            if capture and captured:
                rec.update(_summarize_response(status_box["ctype"], b"".join(captured)))
            write_log(rec)
