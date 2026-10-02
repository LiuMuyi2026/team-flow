"""UserPromptSubmit：完全忽略 prompt，永不联网，只读本地缓存。"""

import io
import json
import os
import socket
import sys
import time

import pytest
from tfhelpers import stdin_for

from teamflow import cli


class _NoNet(Exception):
    pass


@pytest.fixture
def no_network(monkeypatch):
    calls = []

    def boom(*a, **k):
        calls.append(a)
        raise _NoNet("network used")

    monkeypatch.setattr(socket, "create_connection", boom)
    monkeypatch.setattr(socket.socket, "connect", boom)
    monkeypatch.setattr(socket.socket, "connect_ex", boom)
    monkeypatch.setattr(socket, "getaddrinfo", boom)
    return calls


def _run_inproc(monkeypatch, args, payload):
    stdin = io.TextIOWrapper(io.BytesIO(json.dumps(payload).encode()), encoding="utf-8")
    out = io.BytesIO()
    stdout = io.TextIOWrapper(out, encoding="utf-8")
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(sys, "stdout", stdout)
    rc = cli.main(args)
    stdout.flush()
    return rc, out.getvalue()


@pytest.mark.parametrize("client", ["claude", "codex"])
def test_prompt_never_touches_network(env, stub, monkeypatch, no_network, client):
    env.write_cred(stub.url)
    # 没有缓存、也没有会话状态：照样不联网，只是拉起（这里被 TEAMFLOW_NO_SPAWN 拦下的）分离刷新
    rc, out = _run_inproc(
        monkeypatch, ["hook", "prompt", "--client", client, "--cred", env.cred], stdin_for(client, "prompt", "/tmp")
    )
    assert rc == 0 and out == b""
    assert no_network == []
    assert stub.requests == []
    assert any("flush --refresh --client %s" % client in s for s in env.spawned())


@pytest.mark.parametrize("client", ["claude", "codex"])
def test_prompt_with_stale_cache_spawns_refresh_once(env, stub, monkeypatch, no_network, client):
    env.write_cred(stub.url)
    os.makedirs(os.path.join(env.state, "cache", "team"), exist_ok=True)
    cache_path = os.path.join(env.state, "cache", "team", client + ".json")
    json.dump({"fetched_at": time.time() - 120, "data": {"me": "zhao", "todo": ["T-50"]}}, open(cache_path, "w"))
    args = ["hook", "prompt", "--client", client, "--cred", env.cred]
    rc, out = _run_inproc(monkeypatch, args, stdin_for(client, "prompt", "/tmp"))
    assert rc == 0
    text = out.decode()
    assert "您已接受 T-50，可以 claim_task 开始" in text  # 没有会话状态：缓存里的「需要我」都算新
    assert "T-99" not in text
    # 60 秒内再来一次：不再重复拉起刷新
    _run_inproc(monkeypatch, args, stdin_for(client, "prompt", "/tmp"))
    assert len([s for s in env.spawned() if "--refresh" in s]) == 1
    assert no_network == [] and stub.requests == []


def test_prompt_subprocess_no_requests(env, stub):
    env.write_cred(stub.url)
    for client in ("claude", "codex"):
        p = env.hook("prompt", client, stdin_for(client, "prompt", "/tmp"))
        assert p.returncode == 0
    assert stub.requests == []


def test_prompt_field_never_read(env, stub, monkeypatch, no_network):
    """prompt 里写什么都不影响输出，也不会被写进任何本地文件。"""
    env.write_cred(stub.url)
    payload = stdin_for("claude", "prompt", "/tmp", prompt="TOPSECRET-PROMPT T-1 B-2")
    _run_inproc(monkeypatch, ["hook", "prompt", "--client", "claude", "--cred", env.cred], payload)
    for root, _, files in os.walk(env.state):
        for n in files:
            with open(os.path.join(root, n), "rb") as f:
                assert b"TOPSECRET-PROMPT" not in f.read()
