"""最小 HTTP 客户端：http.client + 环境变量代理，按需导入。

不用 urllib.request：它导入更慢，而且在只设了 https_proxy、没设 no_proxy 时会把
127.0.0.1 的请求也送进代理。这里回环地址永远直连；不跟随重定向（3xx 原样返回）。
"""

import os

from teamflow import common

MAX_BODY = 256 * 1024


class NetError(Exception):
    """网络层失败（连不上、超时、读不完）。HTTP 状态码不算 NetError。"""


def _bypass_proxy(host: str) -> bool:
    h = host.strip("[]").lower()
    if h in ("localhost", "::1") or h.startswith("127.") or h.endswith(".localhost"):
        return True
    raw = os.environ.get("no_proxy") or os.environ.get("NO_PROXY") or ""
    for entry in raw.split(","):
        e = entry.strip().lower()
        if not e:
            continue
        if e == "*":
            return True
        if "/" in e:
            try:
                import ipaddress

                if ipaddress.ip_address(h) in ipaddress.ip_network(e, strict=False):
                    return True
            except ValueError:
                pass
            continue
        e = e.lstrip("*")
        if e.startswith("."):
            if h.endswith(e) or h == e[1:]:
                return True
        elif h == e or h.endswith("." + e):
            return True
    return False


def _proxy_for(scheme: str, host: str):
    if _bypass_proxy(host):
        return None
    if scheme == "https":
        p = os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY")
    else:
        p = os.environ.get("http_proxy") or os.environ.get("HTTP_PROXY")
    return p or None


def request(method: str, url: str, *, headers: dict | None = None, body=None, timeout: float = 1.0):
    """发一个请求，返回 (status, headers_dict_lower, body_bytes)。

    body 是 dict/list 时按 JSON 发送。网络错误抛 NetError。
    """
    import http.client
    from urllib.parse import urlsplit

    u = urlsplit(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        raise NetError("bad url")
    host = u.hostname
    port = u.port or (443 if u.scheme == "https" else 80)
    path = u.path or "/"
    if u.query:
        path += "?" + u.query
    hdrs = {"User-Agent": "teamflow-cli", "Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    data = None
    if body is not None:
        data = body if isinstance(body, bytes) else common.dumps(body).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")

    proxy = _proxy_for(u.scheme, host)
    try:
        if u.scheme == "https":
            import ssl

            ctx = ssl.create_default_context()
            if proxy:
                pu = urlsplit(proxy if "://" in proxy else "http://" + proxy)
                conn = http.client.HTTPSConnection(pu.hostname, pu.port or 8080, timeout=timeout, context=ctx)
                tunnel_headers = {}
                if pu.username:
                    import base64

                    cred = "%s:%s" % (pu.username, pu.password or "")
                    tunnel_headers["Proxy-Authorization"] = "Basic " + base64.b64encode(cred.encode()).decode()
                conn.set_tunnel(host, port, headers=tunnel_headers)
            else:
                conn = http.client.HTTPSConnection(host, port, timeout=timeout, context=ctx)
        else:
            if proxy:
                pu = urlsplit(proxy if "://" in proxy else "http://" + proxy)
                conn = http.client.HTTPConnection(pu.hostname, pu.port or 8080, timeout=timeout)
                path = url  # 走 HTTP 代理时请求行用绝对 URL
            else:
                conn = http.client.HTTPConnection(host, port, timeout=timeout)
        try:
            conn.request(method, path, body=data, headers=hdrs)
            resp = conn.getresponse()
            raw = resp.read(MAX_BODY + 1)
            if len(raw) > MAX_BODY:
                raise NetError("response too large")
            rh = {k.lower(): v for k, v in resp.getheaders()}
            return resp.status, rh, raw
        finally:
            conn.close()
    except NetError:
        raise
    except (OSError, http.client.HTTPException, ValueError) as e:
        raise NetError("%s: %s" % (type(e).__name__, e)) from None


def api_headers(token: str, wire_client: str, session: str | None = None, idem: str | None = None) -> dict:
    h = {"Authorization": "Bearer " + token, "X-Teamflow-Client": wire_client}
    if session:
        h["X-Teamflow-Session"] = session
    if idem:
        h["Idempotency-Key"] = idem
    return h


def parse_json(raw: bytes):
    try:
        return common.loads(raw)
    except (UnicodeDecodeError, ValueError):
        return None
