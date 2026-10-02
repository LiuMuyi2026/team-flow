"""业务错误。适配层负责把它映射成 MCP 的 isError 结果或 REST 的 HTTP 状态。

两种序列化：
- MCP（structuredContent）：短键 ``{"err": code, "msg": ..., ...}``；content 文本以错误码开头（``needs_human：…``）。
- REST（4xx JSON）：``{"error": code, "message": ..., ...}``，CLI 和其他 REST 调用方按 ``error`` 分支。
"""

from __future__ import annotations

from typing import Any

# 错误码 → REST HTTP 状态
HTTP_STATUS = {
    "taken": 409,
    "needs_human": 403,
    "needs_accept": 409,
    "human_only": 403,
    "not_allowed": 403,
    "rate_limited": 429,
    "secret_detected": 422,
    "not_found": 404,
    "invalid": 400,
    "conflict": 409,
    "too_many": 413,
    "unauthorized": 401,
}


class DomainError(Exception):
    def __init__(self, code: str, msg: str, *, status: int | None = None, **extra: Any) -> None:
        super().__init__(msg)
        self.code = code
        self.msg = msg
        self._status = status
        self.extra = {k: v for k, v in extra.items() if v is not None}

    @property
    def http_status(self) -> int:
        return self._status or HTTP_STATUS.get(self.code, 400)

    def to_dict(self) -> dict[str, Any]:
        """MCP structuredContent 用的短键形式。"""
        return {"err": self.code, "msg": self.msg, **self.extra}

    def to_rest(self) -> dict[str, Any]:
        """REST 4xx 响应体（跨包约定）：{"error": code, "message": ...}，附带结构化的 extra。"""
        return rest_error(self.code, self.msg, **self.extra)

    def text(self) -> str:
        """给模型看的 content 文本：以错误码开头，instructions 里按错误码下的指令才能对上（I5）。"""
        return error_text(self.code, self.msg)


def rest_error(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"error": code, "message": message, **{k: v for k, v in extra.items() if v is not None}}


def error_text(code: str | None, msg: str | None) -> str:
    return f"{code or 'error'}：{msg or ''}"
