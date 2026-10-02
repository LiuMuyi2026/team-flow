"""业务错误。适配层负责把它映射成 MCP 的 isError 结果或 REST 的 HTTP 状态。"""

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
}


class DomainError(Exception):
    def __init__(self, code: str, msg: str, **extra: Any) -> None:
        super().__init__(msg)
        self.code = code
        self.msg = msg
        self.extra = {k: v for k, v in extra.items() if v is not None}

    @property
    def http_status(self) -> int:
        return HTTP_STATUS.get(self.code, 400)

    def to_dict(self) -> dict[str, Any]:
        return {"err": self.code, "msg": self.msg, **self.extra}
