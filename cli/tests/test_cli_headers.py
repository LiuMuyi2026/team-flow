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


@pytest.mark.parametrize("client,var", [("claude", "CLAUDE_CODE_SESSION_ID"), ("codex", "CODEX_SESSION_ID")])
def test_session_header_from_env(env, client, var):
    env.write_cred("http://127.0.0.1:8100")
    p = env.run(["mcp-headers", "--client", client, "--cred", env.cred], **{var: "abc-123"})
    assert json.loads(p.stdout)["X-Teamflow-Session"] == "abc-123"
    # 只认本客户端的变量
    other = "CODEX_SESSION_ID" if client == "claude" else "CLAUDE_CODE_SESSION_ID"
    p = env.run(["mcp-headers", "--client", client, "--cred", env.cred], **{other: "zzz"})
    assert "X-Teamflow-Session" not in json.loads(p.stdout)
    # 不合法的值（可做头注入）直接丢弃
    p = env.run(["mcp-headers", "--client", client, "--cred", env.cred], **{var: "a b\tc"})
    assert "X-Teamflow-Session" not in json.loads(p.stdout)


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
