"""环境变量配置。每次读取都现取环境变量，方便测试里 monkeypatch。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TOKENS = "tf_pat_dev_alice:alice:claude_code,tf_pat_dev_bob:bob:codex"
DEFAULT_LOG = str(Path(__file__).resolve().parents[2] / "spike" / "out" / "server.log.jsonl")

CLIENTS = ("claude_code", "codex", "cli", "cloud")


@dataclass(frozen=True)
class TokenRec:
    token: str
    handle: str
    client: str

    @property
    def token_id(self) -> str:
        # 不把明文 token 写进日志或事件；用短前缀作 token_id。
        return "tok_" + self.token[-6:]


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
    """DEV ONLY 端点（模拟"人在手机上操作"）。M0 默认开启；M1 上线前必须删除。"""
    return os.environ.get("TEAMFLOW_DEV_ENDPOINTS", "1") not in ("0", "false", "no")


def public_url() -> str:
    return os.environ.get("TEAMFLOW_PUBLIC_URL", "http://127.0.0.1:8100").rstrip("/")


def allowed_origins() -> set[str]:
    raw = os.environ.get("TEAMFLOW_ALLOWED_ORIGINS", "")
    return {o.strip().rstrip("/") for o in raw.split(",") if o.strip()}


def mcp_json_response() -> bool:
    """MCP 响应用 application/json（默认）还是 SSE。两代协议都允许，客户端两种都必须支持。"""
    return os.environ.get("TEAMFLOW_MCP_JSON_RESPONSE", "1") not in ("0", "false", "no")
