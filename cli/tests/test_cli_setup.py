"""setup 生成的配置结构；--home 指向临时目录，绝不写真实 HOME。"""

import json
import os
import shlex
import stat
import tomllib

import pytest

BIN = "/opt/tf/bin/teamflow"
REAL_HOME = os.path.expanduser("~")


def _snapshot_real_home():
    out = {}
    for rel in (".claude/settings.json", ".claude.json", ".codex/config.toml", ".codex/hooks.json",
                ".config/teamflow/credentials.json"):
        p = os.path.join(REAL_HOME, rel)
        try:
            st = os.stat(p)
            out[rel] = (st.st_mtime_ns, st.st_size)
        except OSError:
            out[rel] = None
    return out


@pytest.fixture
def home(env):
    before = _snapshot_real_home()
    yield env.home
    assert _snapshot_real_home() == before, "测试写了真实 HOME"


def _setup(env, home, *extra, **envx):
    return env.run(["setup", "--home", home, "--bin", BIN, "--api-url", "http://127.0.0.1:8100", *extra],
                   TEAMFLOW_PAT_CLAUDE="tf_pat_c1", TEAMFLOW_PAT_CODEX="tf_pat_x1", **envx)


def test_claude_settings_hooks_exec_form(env, home):
    p = _setup(env, home)
    assert p.returncode == 0, p.stderr.decode()
    cred = os.path.join(home, ".config", "teamflow", "credentials.json")
    s = json.load(open(os.path.join(home, ".claude", "settings.json")))
    hooks = s["hooks"]
    assert set(hooks) == {"SessionStart", "UserPromptSubmit", "Stop", "SessionEnd"}
    expect = {"SessionStart": ("session-start", 5), "UserPromptSubmit": ("prompt", 2), "Stop": ("stop", 5),
              "SessionEnd": ("session-end", None)}
    for event, (sub, timeout) in expect.items():
        grp = hooks[event][-1]
        if event == "SessionStart":
            assert grp["matcher"] == "startup|resume|clear|compact|fork"
        else:
            assert "matcher" not in grp
        (h,) = grp["hooks"]
        assert h["type"] == "command"
        assert h["command"] == BIN  # exec form：command 只是可执行文件
        assert h["args"] == ["hook", sub, "--client", "claude", "--cred", cred]
        assert h.get("timeout") == timeout
    assert "mcp__teamflow__*" in s["permissions"]["allow"]
    assert "Read(~/.config/teamflow/**)" in s["permissions"]["deny"]
    assert "Bash(teamflow mcp-headers:*)" in s["permissions"]["deny"]
    assert s["sandbox"]["enabled"] is True
    paths = {f["path"] for f in s["sandbox"]["credentials"]["files"]}
    assert "~/.config/teamflow/credentials.json" in paths and "~/.ssh" in paths


def test_claude_user_scope_mcp(env, home):
    _setup(env, home)
    cred = os.path.join(home, ".config", "teamflow", "credentials.json")
    cj = json.load(open(os.path.join(home, ".claude.json")))
    srv = cj["mcpServers"]["teamflow"]
    assert srv["type"] == "http"
    assert srv["url"] == "http://127.0.0.1:8100/mcp/"
    assert shlex.split(srv["headersHelper"]) == [BIN, "mcp-headers", "--client", "claude", "--cred", cred]
    assert stat.S_IMODE(os.stat(os.path.join(home, ".claude.json")).st_mode) == 0o600


def test_codex_config_toml(env, home):
    os.makedirs(os.path.join(home, ".codex"))
    with open(os.path.join(home, ".codex", "config.toml"), "w") as f:
        f.write('model = "gpt-5.5-codex"  # 用户自己的注释\n\n[mcp_servers.other]\ncommand = "other-mcp"\n')
    assert _setup(env, home).returncode == 0
    text = open(os.path.join(home, ".codex", "config.toml")).read()
    cfg = tomllib.loads(text)
    assert "# 用户自己的注释" in text  # tomlkit 保留原格式
    assert cfg["model"] == "gpt-5.5-codex"
    assert cfg["mcp_servers"]["other"] == {"command": "other-mcp"}
    t = cfg["mcp_servers"]["teamflow"]
    cred = os.path.join(home, ".config", "teamflow", "credentials.json")
    assert t["url"] == "http://127.0.0.1:8100/mcp/"
    assert shlex.split(t["http_headers_helper"]) == [BIN, "mcp-headers", "--client", "codex", "--cred", cred]
    assert t["startup_timeout_sec"] == 10 and t["tool_timeout_sec"] == 30
    assert set(t) == {"url", "http_headers_helper", "startup_timeout_sec", "tool_timeout_sec"}


def test_codex_hooks_json_appended_at_end(env, home):
    os.makedirs(os.path.join(home, ".codex"))
    mine = {"hooks": [{"type": "command", "command": "echo mine"}]}
    with open(os.path.join(home, ".codex", "hooks.json"), "w") as f:
        json.dump({"description": "我的 hooks", "hooks": {"Stop": [mine], "PreToolUse": [mine]}}, f)
    assert _setup(env, home).returncode == 0
    hj = json.load(open(os.path.join(home, ".codex", "hooks.json")))
    assert set(hj) == {"description", "hooks"}  # Codex 的 HooksFile 是 deny_unknown_fields
    assert hj["description"] == "我的 hooks"
    assert hj["hooks"]["Stop"][0] == mine  # 用户的组保持原位
    assert hj["hooks"]["PreToolUse"] == [mine]
    cred = os.path.join(home, ".config", "teamflow", "credentials.json")
    timeouts = {"SessionStart": 5, "UserPromptSubmit": 2, "Stop": 5, "SessionEnd": 2}
    subs = {"SessionStart": "session-start", "UserPromptSubmit": "prompt", "Stop": "stop", "SessionEnd": "session-end"}
    for event in timeouts:
        grp = hj["hooks"][event][-1]
        assert set(grp) == {"hooks"}
        (h,) = grp["hooks"]
        assert h["type"] == "command" and h["timeout"] == timeouts[event]
        assert shlex.split(h["command"]) == [BIN, "hook", subs[event], "--client", "codex", "--cred", cred]
    # 备份了原文件
    assert any(n.startswith("hooks.json.bak-") for n in os.listdir(os.path.join(home, ".codex")))


def test_rerun_is_idempotent(env, home):
    _setup(env, home)
    _setup(env, home)
    s = json.load(open(os.path.join(home, ".claude", "settings.json")))
    for event, arr in s["hooks"].items():
        assert len(arr) == 1, event
    assert s["permissions"]["allow"].count("mcp__teamflow__*") == 1
    hj = json.load(open(os.path.join(home, ".codex", "hooks.json")))
    for event, arr in hj["hooks"].items():
        assert len(arr) == 1, event
    p = _setup(env, home)
    assert "未变化" in p.stdout.decode()


def test_new_bin_path_replaces_old_group(env, home):
    _setup(env, home)
    env.run(["setup", "--home", home, "--bin", "/new/place/teamflow"])
    hj = json.load(open(os.path.join(home, ".codex", "hooks.json")))
    assert len(hj["hooks"]["Stop"]) == 1
    assert hj["hooks"]["Stop"][0]["hooks"][0]["command"].startswith("/new/place/teamflow ")


def test_credentials_created_0600_with_tokens(env, home):
    _setup(env, home)
    cred = os.path.join(home, ".config", "teamflow", "credentials.json")
    assert stat.S_IMODE(os.stat(cred).st_mode) == 0o600
    c = json.load(open(cred))
    assert c["default"] == "team"
    ws = c["workspaces"]["team"]
    assert ws["api_url"] == "http://127.0.0.1:8100"
    assert ws["tokens"] == {"claude": "tf_pat_c1", "codex": "tf_pat_x1"}
    assert ws["repo_patterns"] == []


def test_dry_run_writes_nothing(env, home):
    p = _setup(env, home, "--dry-run")
    assert p.returncode == 0
    out = p.stdout.decode()
    assert "将写入" in out and ".codex/hooks.json" in out
    assert os.listdir(home) == []


def test_headless_files_and_claude_flags(env, home):
    _setup(env, home)
    cfg = os.path.join(home, ".config", "teamflow")
    hs = json.load(open(os.path.join(cfg, "claude-headless-settings.json")))
    assert hs["permissions"]["allow"] == ["mcp__teamflow__*"]
    assert hs["hooks"]["SessionStart"][0]["hooks"][0]["command"] == BIN
    mj = json.load(open(os.path.join(cfg, "claude-mcp.json")))
    assert mj["mcpServers"]["teamflow"]["type"] == "http"
    p = env.run(["claude-flags", "--home", home])
    assert p.returncode == 0
    argv = p.stdout.decode().split()  # 模拟 $(teamflow claude-flags) 的分词
    assert argv == ["--settings", os.path.join(cfg, "claude-headless-settings.json"),
                    "--mcp-config", os.path.join(cfg, "claude-mcp.json"), "--allowedTools", "mcp__teamflow__*"]
    q = env.run(["claude-flags", "--home", home, "--quoted"]).stdout.decode()
    assert shlex.split(q) == argv


def test_no_hardening(env, home):
    _setup(env, home, "--no-hardening")
    s = json.load(open(os.path.join(home, ".claude", "settings.json")))
    assert "deny" not in s["permissions"] and "sandbox" not in s
    assert "mcp__teamflow__*" in s["permissions"]["allow"]


def test_existing_user_settings_preserved(env, home):
    os.makedirs(os.path.join(home, ".claude"))
    user = {
        "model": "opus",
        "permissions": {"allow": ["Bash(npm test)"], "deny": ["Read(./.env)"]},
        "sandbox": {"enabled": False},
        "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "say done"}]}]},
    }
    json.dump(user, open(os.path.join(home, ".claude", "settings.json"), "w"))
    _setup(env, home)
    s = json.load(open(os.path.join(home, ".claude", "settings.json")))
    assert s["model"] == "opus"
    assert s["permissions"]["allow"][0] == "Bash(npm test)"
    assert "Read(./.env)" in s["permissions"]["deny"]
    assert s["sandbox"]["enabled"] is False  # 用户明确关掉的不改
    assert s["hooks"]["Stop"][0] == user["hooks"]["Stop"][0]
    assert s["hooks"]["Stop"][-1]["hooks"][0]["command"] == BIN


def _quiet_shell(tmp_path):
    # 本机 /etc/profile.d/nvm.sh 会让 `sh -lc true` 输出 "nvm"（正是 doctor 要抓的问题），测试用一个安静的假 shell
    sh = tmp_path / "quiet.sh"
    sh.write_text("#!/bin/sh\nexit 0\n")
    sh.chmod(0o755)
    return str(sh)


def test_doctor_after_setup(env, home, tmp_path):
    _setup(env, home)
    p = env.run(["doctor", "--home", home, "--bin", BIN], PATH="/usr/bin:/bin", SHELL=_quiet_shell(tmp_path))
    out = p.stdout.decode()
    assert "失败" not in out, out
    assert p.returncode == 0
    assert "Codex Stop hook（在数组末尾）" in out


def test_doctor_reports_missing(env, home, tmp_path):
    p = env.run(["doctor", "--home", home, "--bin", BIN], PATH="/usr/bin:/bin", SHELL=_quiet_shell(tmp_path))
    assert p.returncode == 1
    assert "失败" in p.stdout.decode()


def test_doctor_flags_noisy_shell(env, home, tmp_path):
    _setup(env, home)
    noisy = tmp_path / "noisy.sh"
    noisy.write_text("#!/bin/sh\necho 'Welcome!'\nexec /bin/sh \"$@\"\n")
    noisy.chmod(0o755)
    p = env.run(["doctor", "--home", home, "--bin", BIN], PATH="/usr/bin:/bin", SHELL=str(noisy))
    assert p.returncode == 1
    assert "profile 有输出" in p.stdout.decode()
