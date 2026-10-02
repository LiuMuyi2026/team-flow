"""fail-open：服务端不可达、慢、报错，输入或凭据坏掉，hook 都 exit 0 且不输出（或只输出缓存）。"""

import json
import os
import time

import pytest
from tfhelpers import stdin_for
from tf_stub_server import closed_port_url

from teamflow import inbox


@pytest.mark.parametrize("client", ["claude", "codex"])
def test_unreachable_no_cache_silent(env, client):
    env.write_cred(closed_port_url())
    p = env.hook("session-start", client, stdin_for(client, "session-start", "/tmp"))
    assert p.returncode == 0
    assert p.stdout == b"" and p.stderr == b""
    assert "session-start net" in env.log_text()
    # 会话登记放进 spool，下次 flush 补发
    recs = env.spool_records()
    assert [r["item"]["type"] for r in recs] == ["start"]


@pytest.mark.parametrize("client", ["claude", "codex"])
def test_unreachable_uses_cache_with_time(env, stub, client):
    env.write_cred(stub.url)
    assert env.hook("session-start", client, stdin_for(client, "session-start", "/tmp")).stdout
    env.write_cred(closed_port_url())
    p = env.hook("session-start", client, stdin_for(client, "session-start", "/tmp", session_id="sess-2"))
    assert p.returncode == 0
    out = p.stdout.decode()
    if client == "claude":
        out = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    hhmm = time.strftime("%H:%M")
    assert out.startswith(inbox.SENTINEL)
    assert "缓存于 " in out.splitlines()[0]
    assert out.splitlines()[0].endswith("】")
    assert hhmm[:2] in out.splitlines()[0]
    assert "本仓库相关" not in out  # 缓存里不带与仓库相关的提示


def test_stale_cache_over_24h_not_used(env, stub):
    env.write_cred(stub.url)
    env.hook("session-start", "codex", stdin_for("codex", "session-start", "/tmp"))
    cache_path = os.path.join(env.state, "cache", "team", "codex.json")
    cache = json.load(open(cache_path))
    cache["fetched_at"] = time.time() - 25 * 3600
    json.dump(cache, open(cache_path, "w"))
    env.write_cred(closed_port_url())
    p = env.hook("session-start", "codex", stdin_for("codex", "session-start", "/tmp"))
    assert p.returncode == 0 and p.stdout == b""


def test_slow_server_times_out_fast(env, stub):
    env.write_cred(stub.url)
    stub.delay = 3.0
    t = time.time()
    p = env.hook("session-start", "claude", stdin_for("claude", "session-start", "/tmp"))
    elapsed = time.time() - t
    assert p.returncode == 0 and p.stdout == b""
    assert elapsed < 2.0, elapsed


@pytest.mark.parametrize("status", [500, 401, 404])
def test_server_error_status(env, stub, status):
    env.write_cred(stub.url)
    stub.status["/api/v1/hooks/session-start"] = status
    p = env.hook("session-start", "codex", stdin_for("codex", "session-start", "/tmp"))
    assert p.returncode == 0 and p.stdout == b""
    assert "http %d" % status in env.log_text()
    # 只有 5xx 才进 spool 补发；4xx 不重试
    assert len(env.spool_records()) == (1 if status >= 500 else 0)


@pytest.mark.parametrize("event", ["session-start", "prompt", "stop", "session-end", "tool"])
@pytest.mark.parametrize("stdin", [b"not json{", b"[1,2,3]", b"\xff\xfe", b""])
def test_bad_stdin(env, stub, event, stdin):
    env.write_cred(stub.url)
    p = env.run(["hook", event, "--client", "claude", "--cred", env.cred], stdin)
    assert p.returncode == 0 and p.stdout == b"" and p.stderr == b""


@pytest.mark.parametrize("event", ["session-start", "prompt", "stop", "session-end"])
def test_missing_or_broken_creds(env, event, tmp_path):
    missing = str(tmp_path / "nope.json")
    p = env.hook(event, "codex", stdin_for("codex", event, "/tmp"), cred=missing)
    assert p.returncode == 0 and p.stdout == b"" and p.stderr == b""
    broken = tmp_path / "broken.json"
    broken.write_text("{")
    p = env.hook(event, "codex", stdin_for("codex", event, "/tmp"), cred=str(broken))
    assert p.returncode == 0 and p.stdout == b""
    assert "CredError" in env.log_text()


@pytest.mark.parametrize(
    "args",
    [
        ["hook", "session-start", "--client", "claude", "--cred", "relative.json"],
        ["hook", "tool", "--client", "claude", "--cred", "relative.json"],
        ["hook", "tool", "--client", "gemini", "--cred", "/x.json"],
        ["hook", "bogus", "--client", "claude", "--cred", "/x.json"],
        ["hook", "prompt", "--client", "gemini", "--cred", "/x.json"],
        ["hook", "stop", "--client"],
        ["hook"],
    ],
)
def test_bad_args_fail_open(env, args):
    p = env.run(args, b"{}")
    assert p.returncode == 0 and p.stdout == b"" and p.stderr == b""


def test_missing_token_fail_open(env, stub):
    env.write_cred(stub.url)
    data = json.load(open(env.cred))
    data["workspaces"]["team"]["tokens"] = {"claude": "not-a-pat"}
    json.dump(data, open(env.cred, "w"))
    p = env.hook("session-start", "claude", stdin_for("claude", "session-start", "/tmp"))
    assert p.returncode == 0 and p.stdout == b""
    assert stub.requests == []
