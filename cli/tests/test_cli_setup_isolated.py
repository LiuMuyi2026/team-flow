"""setup --isolated：本地试用把全部配置写进一个目录（scripts/local-up.sh 用 <仓库>/.local），一个字节都不写 HOME。

断言：
- 文件只落在 <dir> 里（claude/settings.json、claude/mcp.json、codex/config.toml、codex/hooks.json、credentials.json、
  bin/teamflow），临时 HOME 和真实 HOME 都没有变化；
- 命令串规则和 --home 完全一样（Claude Code 5 条 exec form、Codex 4 条 shell 串），只是 bin 换成隔离包装；
- 包装把 TEAMFLOW_STATE_DIR 固定到 <dir>/cli-state：hook 的 spool 落在隔离目录里，即使环境里没有这个变量；
- 重跑逐字节不变，Codex 写进 config.toml 的信任记录保留；
- doctor --isolated 认这套布局。
"""

import json
import os
import shlex
import stat
import subprocess
import sys
import tomllib

import pytest

from tfhelpers import SID, stdin_for

REAL_HOME = os.path.expanduser("~")
API = "http://127.0.0.1:8301"
# 像 token 的样本运行时拼接，不在源码里写成整串
TOK_C = "tf_pat_" + "iso" + "c" * 8
TOK_X = "tf_pat_" + "iso" + "x" * 8


def _real_home_snapshot():
    out = {}
    for rel in (".claude", ".claude.json", ".codex", ".config/teamflow", ".local/state/teamflow"):
        p = os.path.join(REAL_HOME, rel)
        try:
            st = os.stat(p)
            out[rel] = (st.st_mtime_ns, st.st_size)
        except OSError:
            out[rel] = None
    return out


def _tree(root):
    out = []
    for dp, dn, fn in os.walk(root):
        for n in fn:
            out.append(os.path.relpath(os.path.join(dp, n), root))
    return sorted(out)


@pytest.fixture
def iso(env, tmp_path):
    before = _real_home_snapshot()
    d = str(tmp_path / "repo" / ".local")
    yield d
    assert _real_home_snapshot() == before, "测试写了真实 HOME"
    assert _tree(env.home) == [], "隔离模式往 HOME 里写了东西：%s" % _tree(env.home)


@pytest.fixture
def real_bin(tmp_path):
    """假装是 venv 里的 teamflow：一个 exec 当前解释器 -m teamflow 的脚本。"""
    p = tmp_path / "venv" / "bin" / "teamflow"
    p.parent.mkdir(parents=True)
    p.write_text("#!/bin/sh\nexec %s -m teamflow \"$@\"\n" % shlex.quote(sys.executable))
    p.chmod(0o755)
    return str(p)


def _setup(env, iso, real_bin, *extra, **envx):
    return env.run(["setup", "--isolated", iso, "--bin", real_bin, "--api-url", API, "--workspace", "local", *extra],
                   TEAMFLOW_PAT_CLAUDE=TOK_C, TEAMFLOW_PAT_CODEX=TOK_X, **envx)


def test_writes_only_into_isolated_dir(env, iso, real_bin):
    p = _setup(env, iso, real_bin)
    assert p.returncode == 0, p.stderr.decode()
    assert _tree(iso) == sorted([
        "bin/teamflow", "claude/mcp.json", "claude/settings.json", "codex/config.toml", "codex/hooks.json",
        "credentials.json",
    ])
    out = p.stdout.decode()
    assert "--strict-mcp-config" in out and "CODEX_HOME=" in out and "doctor --isolated" in out
    assert TOK_C not in out and TOK_X not in out
    # 凭据 0600，内容是试用 workspace
    cred = os.path.join(iso, "credentials.json")
    assert stat.S_IMODE(os.stat(cred).st_mode) == 0o600
    c = json.load(open(cred))
    assert c["default"] == "local"
    assert c["workspaces"]["local"]["api_url"] == API
    assert c["workspaces"]["local"]["tokens"] == {"claude": TOK_C, "codex": TOK_X}


def test_command_strings_follow_same_rule_as_home(env, iso, real_bin):
    from teamflow import setup_cmd

    assert _setup(env, iso, real_bin).returncode == 0
    wrapper = os.path.join(iso, "bin", "teamflow")
    cred = os.path.join(iso, "credentials.json")
    s = json.load(open(os.path.join(iso, "claude", "settings.json")))
    want = setup_cmd.claude_hook_groups(wrapper, cred)
    assert set(s["hooks"]) == {"SessionStart", "UserPromptSubmit", "Stop", "SessionEnd", "PostToolUse"}
    for event, grp in want.items():
        assert s["hooks"][event] == [grp]
        (h,) = grp["hooks"]
        assert h["command"] == wrapper and os.path.basename(h["command"]) == "teamflow"
        assert h["args"][0] == "hook" and h["args"][2:] == ["--client", "claude", "--cred", cred]
        assert "async" not in h
    assert s["hooks"]["PostToolUse"][0]["matcher"] == "^mcp__teamflow__.*"
    assert setup_cmd.MCP_ALLOW in s["permissions"]["allow"]
    # 加固默认开：deny 规则和沙箱屏蔽指向隔离目录里的凭据
    assert any(r.startswith("Read(") and iso.lstrip("/") in r for r in s["permissions"]["deny"])
    assert any(f["path"].endswith(os.path.join(".local", "credentials.json")) for f in s["sandbox"]["credentials"]["files"])

    mj = json.load(open(os.path.join(iso, "claude", "mcp.json")))
    assert mj == {"mcpServers": {"teamflow": {"type": "http", "url": API + "/mcp/",
                                              "headersHelper": setup_cmd.helper_cmd(wrapper, "claude", cred)}}}

    cfg = tomllib.load(open(os.path.join(iso, "codex", "config.toml"), "rb"))
    srv = cfg["mcp_servers"]["teamflow"]
    assert srv["url"] == API + "/mcp/"
    assert srv["http_headers_helper"] == shlex.join([wrapper, "mcp-headers", "--client", "codex", "--cred", cred])
    hj = json.load(open(os.path.join(iso, "codex", "hooks.json")))
    assert set(hj) == {"description", "hooks"}
    assert set(hj["hooks"]) == {"SessionStart", "UserPromptSubmit", "Stop", "SessionEnd"}  # Codex 4 个
    for event, sub, _, xt in setup_cmd.HOOK_SPECS:
        (grp,) = hj["hooks"][event]
        (h,) = grp["hooks"]
        assert h["command"] == shlex.join([wrapper, "hook", sub, "--client", "codex", "--cred", cred])
        assert h["timeout"] == xt


def test_no_hardening_in_isolated(env, iso, real_bin):
    assert _setup(env, iso, real_bin, "--no-hardening").returncode == 0
    s = json.load(open(os.path.join(iso, "claude", "settings.json")))
    assert "sandbox" not in s and "deny" not in s["permissions"]


def test_wrapper_pins_state_dir(env, iso, real_bin, tmp_path):
    assert _setup(env, iso, real_bin).returncode == 0
    wrapper = os.path.join(iso, "bin", "teamflow")
    assert os.access(wrapper, os.X_OK)
    from teamflow import setup_cmd

    assert setup_cmd.wrapper_target(wrapper) == real_bin
    # 不带 TEAMFLOW_STATE_DIR 运行（Codex 运行 helper 前清空环境）：状态仍然落在 <dir>/cli-state
    e = env.environ()
    e.pop("TEAMFLOW_STATE_DIR")
    proj = tmp_path / "proj"
    proj.mkdir()
    payload = json.dumps(stdin_for("claude", "tool", str(proj))).encode()
    cred = os.path.join(iso, "credentials.json")
    p = subprocess.run([wrapper, "hook", "tool", "--client", "claude", "--cred", cred], input=payload,
                       capture_output=True, env=e, timeout=30)
    assert p.returncode == 0 and p.stdout == b""
    spool = os.path.join(iso, "cli-state", "spool")
    recs = [json.load(open(os.path.join(spool, n))) for n in os.listdir(spool) if n.endswith(".json")]
    assert len(recs) == 1 and recs[0]["item"]["type"] == "tool_map"
    assert recs[0]["item"]["session_id"] == SID["claude"] and recs[0]["cred"] == cred
    assert not os.path.exists(env.state)  # 环境里那个状态目录没被用到
    # 参数原样转交
    p = subprocess.run([wrapper, "--version"], capture_output=True, env=e, timeout=30)
    assert p.returncode == 0 and p.stdout.decode().startswith("teamflow ")


def test_rerun_is_byte_identical_and_keeps_codex_trust(env, iso, real_bin):
    assert _setup(env, iso, real_bin).returncode == 0
    cfg = os.path.join(iso, "codex", "config.toml")
    # Codex 在 /hooks 里信任之后会往 CODEX_HOME/config.toml 写 [hooks.state."<key>"]（codex-rs/config/src/hook_config.rs）
    key = "%s:session_start:0:0" % os.path.join(iso, "codex", "hooks.json")
    with open(cfg, "a") as f:
        f.write('\n[hooks.state."%s"]\ntrusted_hash = "sha256:%s"\n' % (key, "0" * 64))
    snap = {n: open(os.path.join(iso, n), "rb").read() for n in _tree(iso)}
    p = _setup(env, iso, real_bin)
    assert p.returncode == 0, p.stderr.decode()
    assert {n: open(os.path.join(iso, n), "rb").read() for n in _tree(iso)} == snap
    assert "已写入" not in p.stdout.decode()
    assert tomllib.load(open(cfg, "rb"))["hooks"]["state"][key]["trusted_hash"] == "sha256:" + "0" * 64


def test_port_change_updates_mcp_url_in_place(env, iso, real_bin):
    assert _setup(env, iso, real_bin).returncode == 0
    p = env.run(["setup", "--isolated", iso, "--bin", real_bin, "--api-url", "http://127.0.0.1:8302"])
    assert p.returncode == 0, p.stderr.decode()
    mj = json.load(open(os.path.join(iso, "claude", "mcp.json")))
    assert mj["mcpServers"]["teamflow"]["url"] == "http://127.0.0.1:8302/mcp/"
    cfg = tomllib.load(open(os.path.join(iso, "codex", "config.toml"), "rb"))
    assert cfg["mcp_servers"]["teamflow"]["url"] == "http://127.0.0.1:8302/mcp/"


def test_dry_run_writes_nothing_and_masks(env, iso, real_bin):
    p = _setup(env, iso, real_bin, "--dry-run")
    assert p.returncode == 0, p.stderr.decode()
    assert not os.path.exists(iso)
    out = p.stdout.decode()
    assert "teamflow 包装脚本" in out
    assert TOK_C not in out and TOK_X not in out


@pytest.mark.parametrize("extra", [["--home", "/tmp/x"], ["--cred", "/tmp/c.json"]])
def test_isolated_rejects_home_and_cred(env, iso, real_bin, extra):
    p = _setup(env, iso, real_bin, *extra)
    assert p.returncode == 2 and "--isolated" in p.stderr.decode()
    assert not os.path.exists(iso)


def test_isolated_requires_absolute_path(env, real_bin, tmp_path):
    p = env.run(["setup", "--isolated", "rel/.local", "--bin", real_bin])
    assert p.returncode == 2 and "绝对路径" in p.stderr.decode()


def test_bin_pointing_at_wrapper_reuses_its_target(env, iso, real_bin):
    assert _setup(env, iso, real_bin).returncode == 0
    wrapper = os.path.join(iso, "bin", "teamflow")
    p = env.run(["setup", "--isolated", iso, "--bin", wrapper, "--api-url", API])
    assert p.returncode == 0, p.stderr.decode()
    from teamflow import setup_cmd

    assert setup_cmd.wrapper_target(wrapper) == real_bin  # 没有变成 exec 自己


def test_doctor_isolated(env, iso, real_bin, tmp_path):
    assert _setup(env, iso, real_bin).returncode == 0
    # 假的 codex：记下它看到的 CODEX_HOME。真 codex 连 --version 都会在 CODEX_HOME/tmp/arg0 建目录，
    # 不设 CODEX_HOME 就建到 ~/.codex 里（本机实测 codex-cli 0.160.0）。PATH 里不放真的 claude / codex。
    fake = tmp_path / "fakebin"
    fake.mkdir()
    seen = tmp_path / "codex_home_seen"
    (fake / "codex").write_text("#!/bin/sh\nprintf '%%s' \"$CODEX_HOME\" > %s\necho codex-cli 0.0.0\n" % shlex.quote(str(seen)))
    (fake / "codex").chmod(0o755)
    p = env.run(["doctor", "--isolated", iso], NO_COLOR="1", SHELL="/bin/sh", PATH="%s:/usr/bin:/bin" % fake)
    out = p.stdout.decode()
    assert seen.read_text() == os.path.join(iso, "codex")
    assert "通过  codex 版本：codex-cli 0.0.0" in out
    assert "通过  隔离包装" in out
    for event in ("SessionStart", "UserPromptSubmit", "Stop", "SessionEnd", "PostToolUse"):
        assert "通过  Claude Code %s hook" % event in out
    for event in ("SessionStart", "UserPromptSubmit", "Stop", "SessionEnd"):
        assert "通过  Codex %s hook" % event in out
    assert "通过  Claude Code MCP（mcp.json）" in out
    assert "通过  Codex [mcp_servers.teamflow]" in out
    assert "无头配置" not in out
    assert "失败  凭据" not in out and "失败  workspace" not in out
    # 包装丢了：doctor 指出来
    os.remove(os.path.join(iso, "bin", "teamflow"))
    p = env.run(["doctor", "--isolated", iso], NO_COLOR="1", SHELL="/bin/sh", PATH="/usr/bin:/bin")
    assert p.returncode == 1 and "失败  隔离包装" in p.stdout.decode()
