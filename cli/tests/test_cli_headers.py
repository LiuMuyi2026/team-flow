"""mcp-headers：两端 helper 要的格式（字符串到字符串的 JSON 对象）；stdout 是终端时拒绝。"""

import json
import os
import pty
import subprocess
import sys

import pytest


@pytest.mark.parametrize("client,wire", [("claude", "claude_code"), ("codex", "codex")])
def test_headers_json(env, client, wire):
    env.write_cred("http://127.0.0.1:8100")
    p = env.run(["mcp-headers", "--client", client, "--cred", env.cred])
    assert p.returncode == 0, p.stderr
    obj = json.loads(p.stdout)
    assert obj == {"Authorization": "Bearer tf_pat_%s_x" % client, "X-Teamflow-Client": wire}
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in obj.items())


@pytest.mark.parametrize("client", ["claude", "codex"])
def test_never_sends_session_header(env, client):
    """M0 S3：helper 环境里的会话变量是从父进程继承来的（嵌套运行时是外层会话），两端都不发 X-Teamflow-Session。"""
    env.write_cred("http://127.0.0.1:8100")
    inherited = {
        "CLAUDE_CODE_SESSION_ID": "1a6941c0-21de-5c92-8067-c298f2345b24",  # S3 里外层容器会话的 ID
        "CLAUDECODE": "1",
        "CODEX_SESSION_ID": "019a2b3c-4d5e-7f60-8a9b-0c1d2e3f4a5b",
        "CODEX_THREAD_ID": "019a2b3c-4d5e-7f60-8a9b-0c1d2e3f4a5c",
    }
    p = env.run(["mcp-headers", "--client", client, "--cred", env.cred], **inherited)
    assert p.returncode == 0, p.stderr
    obj = json.loads(p.stdout)
    assert set(obj) == {"Authorization", "X-Teamflow-Client"}
    assert not any(v in p.stdout.decode() for v in inherited.values() if v != "1")


def test_debug_log_records_inherited_session_but_not_value(env):
    env.write_cred("http://127.0.0.1:8100")
    sid = "1a6941c0-21de-5c92-8067-c298f2345b24"
    p = env.run(["mcp-headers", "--client", "claude", "--cred", env.cred], CLAUDE_CODE_SESSION_ID=sid, TEAMFLOW_DEBUG="1")
    assert p.returncode == 0
    log = env.log_text()
    assert "session_env=yes (not sent)" in log
    assert sid not in log and "tf_pat" not in log


def test_refuses_tty(env):
    env.write_cred("http://127.0.0.1:8100")
    master, slave = pty.openpty()
    try:
        p = subprocess.run(
            [sys.executable, "-m", "teamflow", "mcp-headers", "--client", "claude", "--cred", env.cred],
            stdout=slave, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, env=env.environ(), timeout=20,
        )
        os.close(slave)
        slave = None
        data = b""
        try:
            while True:
                chunk = os.read(master, 4096)
                if not chunk:
                    break
                data += chunk
        except OSError:
            pass
    finally:
        if slave is not None:
            os.close(slave)
        os.close(master)
    assert p.returncode == 2
    assert b"tf_pat" not in data
    assert "拒绝输出凭据" in p.stderr.decode()


def test_bad_args_and_missing_cred(env, tmp_path):
    p = env.run(["mcp-headers", "--client", "claude", "--cred", "rel.json"])
    assert p.returncode == 2 and p.stdout == b""
    p = env.run(["mcp-headers", "--client", "claude", "--cred", str(tmp_path / "none.json")])
    assert p.returncode == 1 and p.stdout == b""


def test_codex_style_cleared_env(env):
    """Codex 运行 helper 前 env_clear()，只留 HOME、PATH 等：CLI 不依赖任何其他变量。"""
    env.write_cred("http://127.0.0.1:8100")
    clean = {"HOME": env.home, "PATH": os.environ.get("PATH", "/usr/bin:/bin")}
    p = subprocess.run(
        ["/bin/sh", "-c", "%s -m teamflow mcp-headers --client codex --cred %s" % (sys.executable, env.cred)],
        capture_output=True, env=clean, timeout=20,
    )
    assert p.returncode == 0, p.stderr
    assert json.loads(p.stdout)["Authorization"] == "Bearer tf_pat_codex_x"
