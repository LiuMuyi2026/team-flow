"""环境变量配置。每次读取都现取环境变量，方便测试里 monkeypatch。"""

from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_TOKENS = "tf_pat_dev_alice:alice:claude_code,tf_pat_dev_bob:bob:codex"
DEFAULT_LOG = str(Path(__file__).resolve().parents[2] / "spike" / "out" / "server.log.jsonl")

CLIENTS = ("claude_code", "codex", "cli", "cloud")


@dataclass(frozen=True)
class TokenRec:
    token: str = field(repr=False)  # 明文 token 永不出现在 repr / 日志里
    handle: str
    client: str

    @property
    def token_id(self) -> str:
        """日志、事件、会话里用的 token 标识：sha256 前缀，不含 token 的任何明文片段（plan 8.3 服务端只存哈希）。"""
        return token_id_of(self.token)


def token_id_of(token: str) -> str:
    return "tok_" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]


def parse_tokens(raw: str | None) -> dict[str, TokenRec]:
    """解析 TEAMFLOW_DEV_TOKENS="token:handle:client,..."。格式不对的项直接跳过。"""
    out: dict[str, TokenRec] = {}
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        bits = part.split(":")
        if len(bits) != 3:
            continue
        tok, handle, client = (b.strip() for b in bits)
        if not tok.startswith("tf_pat_") or client not in CLIENTS:
            continue
        out[tok] = TokenRec(tok, handle, client)
    return out


def tokens() -> dict[str, TokenRec]:
    return parse_tokens(os.environ.get("TEAMFLOW_DEV_TOKENS", DEFAULT_TOKENS))


def log_path() -> str:
    return os.environ.get("TEAMFLOW_LOG", DEFAULT_LOG)


def fault_delay_ms() -> int:
    try:
        return max(0, int(os.environ.get("TEAMFLOW_FAULT_DELAY_MS", "0") or 0))
    except ValueError:
        return 0


def dev_endpoints_enabled() -> bool:
    """DEV ONLY 端点（模拟"人在手机上操作"）。默认关闭，只在 TEAMFLOW_DEV_ENDPOINTS=1 时打开；M1 上线前整组删除。"""
    return os.environ.get("TEAMFLOW_DEV_ENDPOINTS", "0").strip().lower() in ("1", "true", "yes")


def dev_secret() -> str | None:
    """DEV 端点的共享密钥（TEAMFLOW_DEV_SECRET）。未设置或为空时 DEV 端点一律 404。"""
    v = os.environ.get("TEAMFLOW_DEV_SECRET", "")
    return v or None


def dev_access_ok(header_value: str | None) -> tuple[bool, str]:
    """DEV 端点的门：开关打开、配置了密钥、请求头 X-Teamflow-Dev-Secret 与之相等（常量时间比较）。

    返回 (是否放行, 原因)。原因只写进观测日志，不返回给调用方（调用方一律看到 404）。
    """
    if not dev_endpoints_enabled():
        return False, "closed"
    secret = dev_secret()
    if secret is None:
        return False, "no_secret"
    if not header_value or not hmac.compare_digest(header_value.encode("utf-8"), secret.encode("utf-8")):
        return False, "bad_secret"
    return True, "ok"


def public_url() -> str:
    return os.environ.get("TEAMFLOW_PUBLIC_URL", "http://127.0.0.1:8100").rstrip("/")


def allowed_origins() -> set[str]:
    raw = os.environ.get("TEAMFLOW_ALLOWED_ORIGINS", "")
    return {o.strip().rstrip("/") for o in raw.split(",") if o.strip()}


def mcp_json_response() -> bool:
    """MCP 响应用 application/json（默认）还是 SSE。两代协议都允许，客户端两种都必须支持。"""
    return os.environ.get("TEAMFLOW_MCP_JSON_RESPONSE", "1") not in ("0", "false", "no")
