"""HTTP 层网关（纯 ASGI 中间件）。REST 和 MCP 共用，agent 绕过 MCP 直接 curl 也走这里。

按顺序做五件事：
1. 路径规范化：``/mcp`` 在应用内改写成 ``/mcp/``（等价于 nginx 的内部改写），两者都不返回 3xx。
2. 鉴权：``Authorization: Bearer tf_pat_…``，来自 TEAMFLOW_DEV_TOKENS；缺失或错误返回 401 并带 WWW-Authenticate。
   ``/mcp/`` 和 ``/api/v1/hooks`` 完全忽略 Cookie 头；``/mcp/`` 上出现不在白名单的 Origin 返回 403。
3. 故障注入：TEAMFLOW_FAULT_DELAY_MS 让 ``/api/v1/hooks/*`` 和 ``/api/v1/me/*`` 延迟返回。
4. 把鉴权结果和解析出的 JSON-RPC 信息放进 ``scope["state"]``，供 REST 依赖和 MCP 工具读取。
5. 观测日志：每个请求往 TEAMFLOW_LOG 追加一行 JSON（不记请求体和查询串，只记协议元数据）。
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

from . import config
from .service import TZ

PV_KEY = "io.modelcontextprotocol/protocolVersion"
CI_KEY = "io.modelcontextprotocol/clientInfo"
CODEX_TURN_KEY = "x-codex-turn-metadata"

_log_lock = threading.Lock()
_last_init: dict[str, dict[str, Any]] = {}  # token_id → 最近一次 initialize 的 {pv, ci}（旧代后续请求不再带 clientInfo）
_MAX_CAPTURE = 256 * 1024
_MAX_BODY = 4 * 1024 * 1024  # 与 SDK 的默认请求体上限一致；鉴权前就要读请求体，所以先设上限
_MAX_LOG_VALUE = 4096


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
            info["codex_turn"] = meta[CODEX_TURN_KEY]  # 原样记录
        if "callId" in meta:
            info["call_id"] = meta["callId"]
        info["meta"] = meta  # 只放进 scope，不写日志
    return info


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
    if "err" in obj and isinstance(obj.get("err"), str):
        out["tf_err"] = obj["err"]
    return out


def _bearer(headers: Headers) -> str | None:
    auth = headers.get("authorization")
    if not auth:
        return None
    scheme, _, tok = auth.partition(" ")
    return tok.strip() if scheme.lower() == "bearer" and tok.strip() else ""


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

        # /mcp/ 与 /api/v1/hooks 完全忽略 Cookie
        if is_mcp or path.startswith("/api/v1/hooks"):
            scope["headers"] = [(k, v) for k, v in scope["headers"] if k.lower() != b"cookie"]

        # MCP 请求体要先读出来解析，再原样回放给下游
        body = b""
        if is_mcp and method == "POST":
            chunks: list[bytes] = []
            more = True
            total = 0
            while more:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                total += len(chunk)
                if total > _MAX_BODY:
                    await _send_json(send, 413, {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Request body too large"}})
                    rec.update({"st": 413, "ms": round((time.perf_counter() - t0) * 1000, 1)})
                    write_log(rec)
                    return
                chunks.append(chunk)
                more = message.get("more_body", False)
            body = b"".join(chunks)
            replayed = False

            async def replay() -> dict[str, Any]:
                nonlocal replayed
                if not replayed:
                    replayed = True
                    return {"type": "http.request", "body": body, "more_body": False}
                return await receive()

            receive = replay
            rpc = parse_rpc(body, headers)
            state["tf_rpc"] = rpc
            rec.update({k: (_cap(v) if k in ("ci", "codex_turn", "call_id") else v) for k, v in rpc.items() if k != "meta"})

        # 鉴权
        tok_rec = None
        needs_auth = (is_mcp or is_api) and not is_dev
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
                    payload = {"err": "unauthorized", "msg": msg}
                await _send_json(send, 401, payload, ((b"www-authenticate", www.encode()),))
                rec.update({"st": 401, "ms": round((time.perf_counter() - t0) * 1000, 1), "auth": "missing" if tok is None else "invalid"})
                write_log(rec)
                return
            state["tf_ident"] = tok_rec
            rec["h"] = tok_rec.handle
            rec["tok_client"] = tok_rec.client
            if is_mcp:
                rpc = state.get("tf_rpc") or {}
                if rpc.get("rpc") == "initialize":
                    _last_init[tok_rec.token_id] = {"pv": rpc.get("pv"), "ci": rpc.get("ci")}
                elif "ci" not in rpc and tok_rec.token_id in _last_init:
                    rec["ci_last"] = _last_init[tok_rec.token_id]
        elif is_dev:
            dh = headers.get("x-teamflow-dev-human")
            if dh:
                rec["dev_human"] = dh[:32]

        if is_mcp:
            origin = headers.get("origin")
            if origin and origin.rstrip("/") not in config.allowed_origins():
                await _send_json(send, 403, {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Origin not allowed"}})
                rec.update({"st": 403, "ms": round((time.perf_counter() - t0) * 1000, 1)})
                write_log(rec)
                return

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

        async def send_wrapper(message: dict[str, Any]) -> None:
            nonlocal size
            if message["type"] == "http.response.start":
                status_box["st"] = message["status"]
                for k, v in message.get("headers", []):
                    lk = k.lower()
                    if lk == b"content-type":
                        status_box["ctype"] = v.decode("latin-1")
                    elif lk == b"mcp-session-id":
                        status_box["resp_session"] = v.decode("latin-1")[:64]
                    elif lk == b"location":
                        status_box["location"] = v.decode("latin-1")[:200]
            elif message["type"] == "http.response.body" and capture and size < _MAX_CAPTURE:
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
