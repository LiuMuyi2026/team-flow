"""UserPromptSubmit：完全忽略 prompt，永不联网，只读本地缓存。"""

import io
import json
import os
import socket
import subprocess
import sys
import time

import pytest
from tfhelpers import SID, stdin_for

from teamflow import cli, inbox


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
    # 没有缓存、也没有会话状态：不联网，也不拉起任何子进程
    rc, out = _run_inproc(
        monkeypatch, ["hook", "prompt", "--client", client, "--cred", env.cred], stdin_for(client, "prompt", "/tmp")
    )
    assert rc == 0 and out == b""
    assert no_network == []
    assert stub.requests == []
    assert env.spawned() == []


def _write_cache(env, client, age, data):
    os.makedirs(os.path.join(env.state, "cache", "team"), exist_ok=True)
    with open(os.path.join(env.state, "cache", "team", client + ".json"), "w") as f:
        json.dump({"fetched_at": time.time() - age, "data": data}, f)


def _write_state(env, client, announced, last_out):
    os.makedirs(os.path.join(env.state, "sessions"), exist_ok=True)
    with open(os.path.join(env.state, "sessions", "%s-%s.json" % (client, SID[client])), "w") as f:
        json.dump({"ws": "team", "announced": announced, "last_out": last_out, "turns": 0}, f)


BASE = {"v": 1, "me": "zhao", "doing": ["T-42"], "help_me": [{"id": "B-7", "by": "zhang"}]}
NEW = dict(BASE, to_accept=[{"id": "T-55", "by": "li", "bk": "agent", "client": "codex"}])
# (名字, 缓存年龄秒, 缓存数据, 是否应有输出)：S4 只测了第一条；I3 要求另外三条
PATHS = [
    ("fresh", 5, BASE, False),
    ("stale", 120, BASE, False),
    ("emit", 5, NEW, True),
    ("stale-emit", 120, NEW, True),
]


@pytest.mark.parametrize("client", ["claude", "codex"])
@pytest.mark.parametrize("name,age,data,emits", PATHS, ids=[p[0] for p in PATHS])
def test_prompt_paths_never_spawn(env, stub, monkeypatch, no_network, client, name, age, data, emits):
    """缓存过期也不拉起 refresh（Stop 每回合已经拉起 flush --refresh）；有新条目照样输出。"""
    env.write_cred(stub.url)
    _write_cache(env, client, age, data)
    _write_state(env, client, ["help:B-7"], 0)
    rc, out = _run_inproc(
        monkeypatch, ["hook", "prompt", "--client", client, "--cred", env.cred], stdin_for(client, "prompt", "/tmp")
    )
    assert rc == 0
    assert env.spawned() == []
    assert no_network == [] and stub.requests == []
    if not emits:
        assert out == b""
        return
    text = json.loads(out)["hookSpecificOutput"]["additionalContext"] if client == "claude" else out.decode()
    assert text.startswith(inbox.SENTINEL)
    assert "待您接受 T-55（来自 li 的 Codex），需您本人在 Team Flow 网页上接受" in text
    assert "B-7" not in text  # 已经通知过
    st = json.load(open(os.path.join(env.state, "sessions", "%s-%s.json" % (client, SID[client]))))
    assert st["announced"] == ["acc:T-55", "help:B-7"]
    assert st["last_out"] > time.time() - 60


_PROBE = r"""
import sys
before = set(sys.modules)
import io
from teamflow import cli
sys.stdin = io.TextIOWrapper(io.BytesIO(sys.argv[1].encode()), encoding="utf-8")
buf = io.BytesIO()
wrapper = io.TextIOWrapper(buf, encoding="utf-8")
sys.stdout = wrapper
rc = cli.main(sys.argv[2:])
wrapper.flush()
out = buf.getvalue().decode()
sys.stdout = sys.__stdout__
loaded = sorted(m for m in ("json", "subprocess", "re", "argparse", "threading", "teamflow.spool", "teamflow.detach")
                if m in sys.modules and m not in before)
import json
print(json.dumps({"rc": rc, "out": out, "loaded": loaded}))
"""


@pytest.mark.parametrize("client", ["claude", "codex"])
@pytest.mark.parametrize("name,age,data,emits", PATHS, ids=[p[0] for p in PATHS])
def test_prompt_paths_import_nothing_heavy(env, stub, client, name, age, data, emits):
    """四条路径都不导入 json / subprocess / re / argparse / threading，也不导入 spool / detach：
    输出用手写的最小 JSON，缓存路径在 common 里（每少一个模块省约 0.3ms 冷启动）。"""
    env.write_cred(stub.url)
    _write_cache(env, client, age, data)
    _write_state(env, client, ["help:B-7"], 0)
    payload = json.dumps(stdin_for(client, "prompt", "/tmp"))
    p = subprocess.run(
        [sys.executable, "-c", _PROBE, payload, "hook", "prompt", "--client", client, "--cred", env.cred],
        capture_output=True, env=env.environ(), timeout=30,
    )
    assert p.returncode == 0, p.stderr.decode()
    res = json.loads(p.stdout)
    assert res["rc"] == 0
    assert res["loaded"] == [], res
    assert bool(res["out"]) == emits
    if emits and client == "claude":
        obj = json.loads(res["out"])
        assert list(obj) == ["hookSpecificOutput"]
        assert obj["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"


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
