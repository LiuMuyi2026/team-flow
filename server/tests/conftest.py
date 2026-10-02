from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest

from teamflow_server.app import create_app
from teamflow_server.service import Actor, Service
from teamflow_server.seed import seed

ALICE = "tf_pat_dev_alice"
BOB = "tf_pat_dev_bob"
ACCEPT = "application/json, text/event-stream"

PV_KEY = "io.modelcontextprotocol/protocolVersion"
CAPS_KEY = "io.modelcontextprotocol/clientCapabilities"
CI_KEY = "io.modelcontextprotocol/clientInfo"


@pytest.fixture(autouse=True)
def _env(tmp_path, monkeypatch):
    monkeypatch.setenv("TEAMFLOW_LOG", str(tmp_path / "server.log.jsonl"))
    monkeypatch.setenv("TEAMFLOW_DEV_TOKENS", "tf_pat_dev_alice:alice:claude_code,tf_pat_dev_bob:bob:codex")
    monkeypatch.delenv("TEAMFLOW_FAULT_DELAY_MS", raising=False)
    monkeypatch.delenv("TEAMFLOW_DEV_ENDPOINTS", raising=False)
    monkeypatch.delenv("TEAMFLOW_ALLOWED_ORIGINS", raising=False)
    yield


@pytest.fixture
def log_path(tmp_path):
    return tmp_path / "server.log.jsonl"


def read_log(path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


@pytest.fixture
def svc() -> Service:
    s = Service()
    seed(s)
    return s


@pytest.fixture
async def app(svc):
    """lifespan 在一个专门的任务里进出（anyio 的 task group 必须在同一个任务里进入和退出）。"""
    a = create_app(svc, with_seed=False)
    started, stop = asyncio.Event(), asyncio.Event()

    async def runner() -> None:
        async with a.router.lifespan_context(a):
            started.set()
            await stop.wait()

    task = asyncio.create_task(runner())
    await asyncio.wait_for(started.wait(), 10)
    yield a
    stop.set()
    await task


@pytest.fixture
async def client(app) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:8100", follow_redirects=False) as c:
        yield c


def agent(handle: str, client: str) -> Actor:
    return Actor(handle, "agent", client, f"tok_{handle}", "mcp")


def human(handle: str) -> Actor:
    return Actor(handle, "human", None, None, "dev")


def parse_body(r: httpx.Response) -> Any:
    ctype = r.headers.get("content-type", "")
    if "text/event-stream" in ctype:
        last = None
        for line in r.text.splitlines():
            if line.startswith("data:"):
                last = json.loads(line[5:].strip())
        return last
    return r.json()


class LegacyMcp:
    """2025-06-18：initialize（无状态，不带 Mcp-Session-Id）→ notifications/initialized → 后续请求带 MCP-Protocol-Version 头。"""

    def __init__(self, client: httpx.AsyncClient, token: str, path: str = "/mcp/", version: str = "2025-06-18", extra: dict[str, str] | None = None):
        self.c, self.token, self.path, self.version = client, token, path, version
        self.extra = extra or {}
        self.session_id: str | None = None
        self._id = 0

    def _headers(self, with_version: bool) -> dict[str, str]:
        h = {"accept": ACCEPT, "content-type": "application/json", "authorization": f"Bearer {self.token}", **self.extra}
        if with_version:
            h["mcp-protocol-version"] = self.version
        if self.session_id:
            h["mcp-session-id"] = self.session_id
        return h

    async def initialize(self) -> httpx.Response:
        self._id += 1
        r = await self.c.post(
            self.path,
            headers=self._headers(False),
            json={
                "jsonrpc": "2.0",
                "id": self._id,
                "method": "initialize",
                "params": {"protocolVersion": self.version, "capabilities": {}, "clientInfo": {"name": "pytest-legacy", "version": "1"}},
            },
        )
        self.session_id = r.headers.get("mcp-session-id")
        await self.c.post(self.path, headers=self._headers(True), json={"jsonrpc": "2.0", "method": "notifications/initialized"})
        return r

    async def rpc(self, method: str, params: dict[str, Any] | None = None) -> httpx.Response:
        self._id += 1
        return await self.c.post(
            self.path, headers=self._headers(True), json={"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}}
        )

    async def call(self, name: str, args: dict[str, Any] | None = None, meta: dict[str, Any] | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"name": name, "arguments": args or {}}
        if meta:
            params["_meta"] = meta
        r = await self.rpc("tools/call", params)
        assert r.status_code == 200, r.text
        return parse_body(r)["result"]


class ModernMcp:
    """2026-07-28：无 initialize；每个请求 _meta 带版本与能力，HTTP 头带 MCP-Protocol-Version、Mcp-Method、Mcp-Name。"""

    def __init__(self, client: httpx.AsyncClient, token: str, path: str = "/mcp/", extra: dict[str, str] | None = None):
        self.c, self.token, self.path = client, token, path
        self.extra = extra or {}
        self._id = 0

    def meta(self, **more: Any) -> dict[str, Any]:
        return {PV_KEY: "2026-07-28", CAPS_KEY: {}, CI_KEY: {"name": "pytest-modern", "version": "1"}, **more}

    async def rpc(self, method: str, params: dict[str, Any] | None = None, name: str | None = None, headers: dict[str, str] | None = None) -> httpx.Response:
        self._id += 1
        p = dict(params or {})
        p.setdefault("_meta", self.meta())
        h = {
            "accept": ACCEPT,
            "content-type": "application/json",
            "authorization": f"Bearer {self.token}",
            "mcp-protocol-version": "2026-07-28",
            "mcp-method": method,
            **self.extra,
        }
        if name is not None:
            h["mcp-name"] = name
        if headers:
            h.update(headers)
        return await self.c.post(self.path, headers=h, json={"jsonrpc": "2.0", "id": self._id, "method": method, "params": p})

    async def call(self, name: str, args: dict[str, Any] | None = None, meta: dict[str, Any] | None = None) -> dict[str, Any]:
        r = await self.rpc("tools/call", {"name": name, "arguments": args or {}, "_meta": self.meta(**(meta or {}))}, name=name)
        assert r.status_code == 200, r.text
        return parse_body(r)["result"]


def dev_headers(handle: str) -> dict[str, str]:
    return {"x-teamflow-dev-human": handle}


def auth(token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {token}"}
