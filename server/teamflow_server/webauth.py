"""网页的人类会话（M0：只有本地开发模式的登录能发；M1 换成通行密钥登录的会话，plan D54）。

- 会话 cookie ``tf_web``：HttpOnly、SameSite=Strict、Path=/、12 小时；https 时另加 Secure（本机 http 试用不加，
  浏览器不给 http://127.0.0.1 存 Secure cookie 的情况各家不一）。服务端只存会话 ID 的 sha256，数据只在内存里，
  重启服务端即全部失效（数据本来也是内存里的）。
- CSRF：双提交。登录时另发 ``tf_csrf`` cookie（SameSite=Strict，不是 HttpOnly，页面能读），``GET /api/v1/web/me``
  也返回同一个值；所有写请求必须带 ``X-CSRF-Token``，值同时等于 cookie 和服务端会话里记的那个，
  并且 ``Origin`` 必须等于本站（``http://<Host>``）。
- 本地入口的门（``/dev/login`` 与 ``/api/v1/web/*`` 共用）：TEAMFLOW_DEV_ENDPOINTS=1、对端是本机地址、
  没有反向代理的转发头、Host 是本机名字（防 DNS rebinding）。不满足一律 404，和"没有这个端点"无法区分。
- 网页 API 永远不认 PAT：请求带了 ``Authorization`` 头就 403 ``human_only``（硬规则 1）。
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from starlette.datastructures import Headers
from starlette.requests import cookie_parser

from . import config

SESSION_COOKIE = "tf_web"
CSRF_COOKIE = "tf_csrf"
CSRF_HEADER = "x-csrf-token"
SESSION_TTL_S = 12 * 3600  # plan 7.2：电脑会话 12 小时过期
SAFE_METHODS = ("GET", "HEAD", "OPTIONS")
MAX_SESSIONS = 200


def _h(sid: str) -> str:
    return hashlib.sha256(sid.encode("utf-8")).hexdigest()


def _eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


@dataclass
class WebSession:
    handle: str
    csrf: str
    created: float
    expires: float
    via: str = "dev"  # 本地开发登录发的。M1 通行密钥登录的会话另有来源


class WebSessions:
    """内存里的会话表：sha256(会话 ID) → 会话。"""

    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self.clock = clock
        self._d: dict[str, WebSession] = {}
        self._lock = threading.Lock()

    def create(self, handle: str) -> tuple[str, WebSession]:
        sid = secrets.token_urlsafe(32)
        now = self.clock()
        sess = WebSession(handle, secrets.token_urlsafe(24), now, now + SESSION_TTL_S)
        with self._lock:
            for k, s in list(self._d.items()):
                if s.expires <= now:
                    del self._d[k]
            while len(self._d) >= MAX_SESSIONS:
                self._d.pop(next(iter(self._d)))
            self._d[_h(sid)] = sess
        return sid, sess

    def get(self, sid: str | None) -> WebSession | None:
        if not sid or len(sid) > 256:
            return None
        with self._lock:
            k = _h(sid)
            s = self._d.get(k)
            if s is not None and s.expires <= self.clock():
                del self._d[k]
                return None
            return s

    def delete(self, sid: str | None) -> None:
        if sid:
            with self._lock:
                self._d.pop(_h(sid), None)

    def clear(self) -> None:
        with self._lock:
            self._d.clear()


# ---------------------------------------------------------------------------
# 门与 CSRF
# ---------------------------------------------------------------------------


def local_gate(scope: dict[str, Any], headers: Headers) -> str | None:
    """本地入口的门。放行返回 None，否则返回原因（只进观测日志，调用方一律 404）。"""
    if not config.dev_endpoints_enabled():
        return "closed"
    client = scope.get("client")
    if not client or not config.is_loopback_ip(str(client[0])):
        return "not_local"
    if any(headers.get(h) is not None for h in config.FORWARDING_HEADERS):
        return "forwarded"
    if not config.loopback_host_header(headers.get("host")):
        return "host"
    return None


def own_origin(scope: dict[str, Any], headers: Headers) -> str:
    return f"{scope.get('scheme', 'http')}://{headers.get('host', '')}".lower()


def origin_ok(scope: dict[str, Any], headers: Headers) -> bool:
    """写请求必须来自本站页面。Host 已由 local_gate 限定为本机名字。

    - 有 Origin（不是 "null"）：必须等于本站 ``scheme://Host``；
    - Origin 缺失或是 "null"：只认浏览器自己加、页面脚本改不了的 ``Sec-Fetch-Site: same-origin``。
      页面的 Referrer-Policy 是 no-referrer 时，浏览器给同源的非 GET 请求发的就是 ``Origin: null``（Fetch 规范
      "append a request Origin header"），所以本站页面用 same-origin，这里再兜一层。"""
    o = (headers.get("origin") or "").strip().lower().rstrip("/")
    if o and o != "null":
        return o == own_origin(scope, headers)
    return (headers.get("sec-fetch-site") or "").strip().lower() == "same-origin"


def cookies(headers: Headers) -> dict[str, str]:
    return cookie_parser(headers.get("cookie", ""))


def csrf_problem(scope: dict[str, Any], headers: Headers, sess: WebSession) -> str | None:
    """写请求的 CSRF 检查：Origin 等于本站；X-CSRF-Token 同时等于 tf_csrf cookie 和会话里记的值。"""
    if not origin_ok(scope, headers):
        return "origin"
    tok = headers.get(CSRF_HEADER) or ""
    ck = cookies(headers).get(CSRF_COOKIE) or ""
    if not tok:
        return "missing"
    if not (_eq(tok, sess.csrf) and _eq(tok, ck)):
        return "mismatch"
    return None


# ---------------------------------------------------------------------------
# cookie
# ---------------------------------------------------------------------------


def _cookie(name: str, value: str, max_age: int, *, http_only: bool, secure: bool) -> str:
    parts = [f"{name}={value}", "Path=/", f"Max-Age={max_age}", "SameSite=Strict"]
    if http_only:
        parts.append("HttpOnly")
    if secure:
        parts.append("Secure")
    return "; ".join(parts)


def login_cookies(sid: str, sess: WebSession, *, secure: bool) -> list[str]:
    ttl = max(0, int(sess.expires - sess.created))
    return [
        _cookie(SESSION_COOKIE, sid, ttl, http_only=True, secure=secure),
        _cookie(CSRF_COOKIE, sess.csrf, ttl, http_only=False, secure=secure),
    ]


def clear_cookies(*, secure: bool) -> list[str]:
    return [
        _cookie(SESSION_COOKIE, "", 0, http_only=True, secure=secure),
        _cookie(CSRF_COOKIE, "", 0, http_only=False, secure=secure),
    ]
