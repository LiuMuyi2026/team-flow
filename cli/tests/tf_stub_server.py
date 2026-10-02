"""测试与基准共用的桩服务端（纯标准库）。

只实现 CLI 用到的几个端点，返回可配置的结构化数据，并记录收到的每个请求。
绑定 127.0.0.1 的临时端口（端口 0，由系统分配），不占用 8000/8100。
"""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SAMPLE_INBOX = {
    "v": 1,
    "me": "zhao",
    "doing": ["T-42", "T-45"],
    "todo": ["T-50"],
    "to_accept": [{"id": "T-52", "by": "li", "bk": "agent", "client": "claude_code"}],
    "help_me": [{"id": "B-7", "by": "zhang"}],
    "fwd": [{"id": "B-7", "n": 1, "by": "zhang"}],
    "proposed": [],
    "pool_new": 3,
    "repo_hint": ["T-42"],
}


class Stub:
    def __init__(self):
        self.inbox = json.loads(json.dumps(SAMPLE_INBOX))
        self.delay = 0.0
        self.status = {}  # path → 强制返回的状态码
        self.reply = {}  # path → (状态码, 响应体对象或 bytes)：完全自定义响应
        self.item_status = {}  # spool key → 逐条状态码
        self.item_extra = {}  # spool key → 逐条结果里多给的字段（如 {"st": "no_repo", "dropped": 1}）
        self.max_body = None  # 请求体字节数上限（模拟服务端/nginx 的 64KB）：超了返回 413
        self.requests = []
        self.etag = "W/\"1\""
        self.lock = threading.Lock()
        self.server = None
        self.thread = None

    @property
    def url(self):
        host, port = self.server.server_address[:2]
        return "http://%s:%d" % (host, port)

    def start(self):
        stub = self

        class H(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):
                pass

            def _body(self):
                n = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(n) if n else b""
                try:
                    return json.loads(raw) if raw else None
                except ValueError:
                    return raw

            def _send(self, code, obj=None, headers=None):
                if isinstance(obj, bytes):
                    data = obj
                else:
                    data = b"" if obj is None else json.dumps(obj, ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                for k, v in (headers or {}).items():
                    self.send_header(k, v)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                try:
                    self.end_headers()
                    if data:
                        self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass  # 客户端超时先走了（慢服务端场景）

            def _handle(self, method):
                body = self._body() if method == "POST" else None
                path = self.path.split("?", 1)[0]
                with stub.lock:
                    stub.requests.append(
                        {"method": method, "path": path, "full": self.path, "headers": dict(self.headers), "body": body}
                    )
                if stub.delay:
                    time.sleep(stub.delay)
                if stub.max_body is not None and int(self.headers.get("Content-Length") or 0) > stub.max_body:
                    return self._send(413, {"error": "too_large", "max": stub.max_body})
                if path in stub.status:
                    return self._send(stub.status[path], {"error": "forced"})
                if path in stub.reply:
                    code, obj = stub.reply[path]
                    return self._send(code, obj)
                # 兜底写命令（跨包约定）：POST /api/v1/tasks/{id}:note|done、POST /api/v1/blockers
                if method == "POST" and path.startswith("/api/v1/tasks/") and path.rsplit(":", 1)[-1] in ("note", "done"):
                    tid, action = path[len("/api/v1/tasks/"):].rsplit(":", 1)
                    return self._send(200, {"id": tid, "st": "doing" if action == "note" else "done"})
                if method == "POST" and path == "/api/v1/blockers":
                    return self._send(201, {"id": "B-9", "st": "proposed" if (body or {}).get("need") else "open"})
                if method == "POST" and path == "/api/v1/hooks/session-start":
                    return self._send(200, stub.inbox)
                if method == "POST" and path == "/api/v1/hooks/batch":
                    items = (body or {}).get("items") or []
                    res = [{"key": it.get("key"), "status": stub.item_status.get(it.get("key"), 200),
                            **stub.item_extra.get(it.get("key"), {})} for it in items]
                    return self._send(200, {"results": res})
                if method == "GET" and path == "/api/v1/me/delta":
                    if self.headers.get("If-None-Match") == stub.etag:
                        return self._send(304)
                    obj = dict(stub.inbox)
                    obj.pop("repo_hint", None)
                    obj["cursor"] = "c1"
                    return self._send(200, obj, {"ETag": stub.etag})
                if method == "GET" and path == "/api/v1/me/inbox":
                    return self._send(200, stub.inbox)
                return self._send(404, {"error": "not_found"})

            def do_GET(self):
                self._handle("GET")

            def do_POST(self):
                self._handle("POST")

        class Server(ThreadingHTTPServer):
            def handle_error(self, request, client_address):
                pass  # 慢服务端场景下客户端会先断开，不打印堆栈

        self.server = Server(("127.0.0.1", 0), H)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()

    def paths(self):
        with self.lock:
            return [r["path"] for r in self.requests]


def closed_port_url():
    """一个当前没人监听的本地端口（连接会被拒绝），模拟服务端不可达。"""
    import socket

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return "http://127.0.0.1:%d" % port
