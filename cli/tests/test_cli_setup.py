"""setup 生成的配置结构；--home 指向临时目录，绝不写真实 HOME。"""

import json
import os
import shlex
import stat
import sys
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


MINE = {"hooks": [{"type": "command", "command": "echo mine"}]}
OTHER = {"hooks": [{"type": "command", "command": "/usr/local/bin/other-tool notify"}]}


def test_rerun_keeps_every_group_position(env, home):
    """I7：别人的组在我们后面时，重跑 setup 不改变任何组的位置（Codex 的信任键带组序号）。"""
    os.makedirs(os.path.join(home, ".codex"))
    os.makedirs(os.path.join(home, ".claude"))
    with open(os.path.join(home, ".codex", "hooks.json"), "w") as f:
        json.dump({"description": "我的 hooks", "hooks": {"Stop": [MINE]}}, f)
    with open(os.path.join(home, ".claude", "settings.json"), "w") as f:
        json.dump({"hooks": {"Stop": [MINE]}}, f)
    assert _setup(env, home).returncode == 0
    # 之后别人（或成员自己）又在我们后面追加了组
    hj = json.load(open(os.path.join(home, ".codex", "hooks.json")))
    s = json.load(open(os.path.join(home, ".claude", "settings.json")))
    for event in ("SessionStart", "UserPromptSubmit", "Stop", "SessionEnd"):
        hj["hooks"][event].append(OTHER)
        s["hooks"][event].append(OTHER)
    json.dump(hj, open(os.path.join(home, ".codex", "hooks.json"), "w"))
    json.dump(s, open(os.path.join(home, ".claude", "settings.json"), "w"))

    assert _setup(env, home).returncode == 0
    hj2 = json.load(open(os.path.join(home, ".codex", "hooks.json")))
    s2 = json.load(open(os.path.join(home, ".claude", "settings.json")))
    assert hj2["hooks"] == hj["hooks"]  # 一个组都没挪
    assert s2["hooks"] == s["hooks"]
    assert hj2["hooks"]["Stop"][0] == MINE and hj2["hooks"]["Stop"][2] == OTHER
    assert hj2["hooks"]["SessionStart"][-1] == OTHER

    # 换了可执行文件路径：我们的组原地替换，序号不变
    assert env.run(["setup", "--home", home, "--bin", "/new/place/teamflow"]).returncode == 0
    hj3 = json.load(open(os.path.join(home, ".codex", "hooks.json")))
    assert hj3["hooks"]["Stop"][0] == MINE and hj3["hooks"]["Stop"][2] == OTHER
    assert hj3["hooks"]["Stop"][1]["hooks"][0]["command"].startswith("/new/place/teamflow hook stop ")
    s3 = json.load(open(os.path.join(home, ".claude", "settings.json")))
    assert s3["hooks"]["Stop"][1]["hooks"][0]["command"] == "/new/place/teamflow"
    assert s3["hooks"]["Stop"][2] == OTHER


def test_upsert_collapses_duplicate_teamflow_groups():
    from teamflow import setup_cmd

    old = {"hooks": [{"type": "command", "command": "/old/teamflow hook stop --client codex --cred /c"}]}
    new = {"hooks": [{"type": "command", "command": "/new/teamflow hook stop --client codex --cred /c"}]}
    hooks = {"Stop": [MINE, old, OTHER, old]}
    # 末尾那组重复的删空了，后面没有别人的组，直接去掉；别人的组位置不变
    assert setup_cmd._upsert_groups(hooks, {"Stop": new}) == ({"Stop": [MINE, new, OTHER]}, [])
    assert setup_cmd._upsert_groups({}, {"Stop": new}) == ({"Stop": [new]}, [])
    assert setup_cmd._upsert_groups({"Stop": [MINE]}, {"Stop": new}) == ({"Stop": [MINE, new]}, [])


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
    # 首次运行：token 来自环境变量，计划里的凭据文件要遮蔽
    assert "tf_pat_c1" not in out and "tf_pat_x1" not in out
    assert ('  workspaces.team.tokens（新增）\n    改动前：（无）\n    改动后：{"claude": "tf_pat_****", "codex": "tf_pat_****"}\n'
            in out)


def _write_existing_creds(home, tokens):
    cfg = os.path.join(home, ".config", "teamflow")
    os.makedirs(cfg, exist_ok=True)
    cred = os.path.join(cfg, "credentials.json")
    with open(cred, "w") as f:
        json.dump({"workspaces": {"team": {"api_url": "http://127.0.0.1:8100", "tokens": tokens, "repo_patterns": []},
                                  "side": {"api_url": "http://127.0.0.1:8101", "tokens": {"claude": "tf_pat_SIDE_secret"}}},
                   "default": "team"}, f)
    os.chmod(cred, 0o600)
    return cred


def test_dry_run_masks_existing_tokens_when_new_git_email(env, home):
    """I4 复现：凭据已存在、.gitconfig 里有新邮箱 → 凭据文件进写入计划；dry-run 不能打出明文 PAT。"""
    cred = _write_existing_creds(home, {"claude": "tf_pat_SECRET_claude_123", "codex": "not-a-pat-SECRET"})
    with open(os.path.join(home, ".gitconfig"), "w") as f:
        f.write("[user]\n\temail = Me@Example.com\n")
    before = open(cred).read()
    p = env.run(["setup", "--home", home, "--bin", BIN, "--dry-run"])
    assert p.returncode == 0, p.stderr.decode()
    out = p.stdout.decode()
    assert "credentials.json（修改" in out  # 确实打印了凭据文件的计划
    assert "SECRET" not in out
    # 只列改动：tokens 没变，不打印；新邮箱按键名遮蔽（复审新问题 4：邮箱也算个人信息）
    assert "tokens" not in out
    assert "  workspaces.team.git_emails（新增）\n    改动前：（无）\n    改动后：[\"m***@***\"]\n" in out
    assert "me@example.com" not in out and "example.com" not in out
    assert open(cred).read() == before  # dry-run 不写
    # 真正写入时 token 原样保留
    assert env.run(["setup", "--home", home, "--bin", BIN]).returncode == 0
    c = json.load(open(cred))
    assert c["workspaces"]["team"]["tokens"] == {"claude": "tf_pat_SECRET_claude_123", "codex": "not-a-pat-SECRET"}
    assert c["workspaces"]["side"]["tokens"] == {"claude": "tf_pat_SIDE_secret"}
    assert c["workspaces"]["team"]["git_emails"] == ["me@example.com"]


def test_scrub_tokens_safety_net():
    from teamflow import setup_cmd

    assert setup_cmd.scrub_tokens('x "tf_pat_abc-1.2_z" tf_pat_**** tf_pat_') == 'x "tf_pat_****" tf_pat_**** tf_pat_****'
    assert setup_cmd.mask_token("") == "" and setup_cmd.mask_token(None) is None


def test_deny_rules_cover_setup_and_python_m(env, home):
    """I4：deny 规则补上 setup 和 python -m 写法（cc_perm.md：`:*` 只能放在末尾，等价于空格加 *）。"""
    _setup(env, home)
    deny = json.load(open(os.path.join(home, ".claude", "settings.json")))["permissions"]["deny"]
    for rule in (
        "Bash(teamflow mcp-headers:*)",
        "Bash(%s mcp-headers:*)" % BIN,
        "Bash(python -m teamflow mcp-headers:*)",
        "Bash(python3 -m teamflow mcp-headers:*)",
        "Bash(teamflow setup:*)",
        "Bash(%s setup:*)" % BIN,
        "Bash(python -m teamflow setup:*)",
        "Read(~/.config/teamflow/**)",
        "Grep(~/.config/teamflow/**)",
    ):
        assert rule in deny, rule
    for rule in deny:
        if rule.startswith("Bash("):
            inner = rule[5:-1]
            assert inner.endswith(":*") and inner.count(":*") == 1 and "*" not in inner[:-2], rule
    _setup(env, home)
    again = json.load(open(os.path.join(home, ".claude", "settings.json")))["permissions"]["deny"]
    assert again == deny  # 重跑不重复


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


def _fake_bin(tmp_path, names=("bwrap", "socat")):
    """一个只含假 bwrap / socat 的目录，接到 PATH 前面；doctor 只检查它们在不在。"""
    d = tmp_path / "fakebin"
    d.mkdir(parents=True, exist_ok=True)
    for n in names:
        f = d / n
        f.write_text("#!/bin/sh\nexit 0\n")
        f.chmod(0o755)
    return str(d)


def _doctor(env, home, tmp_path, deps=("bwrap", "socat"), system_path=True, **extra):
    # system_path=False：PATH 里只有假目录，免得本机真装了 bwrap / socat 时测不出「缺失」
    path = _fake_bin(tmp_path, deps) + (":/usr/bin:/bin" if system_path else "")
    return env.run(["doctor", "--home", home, "--bin", BIN], PATH=path, SHELL=_quiet_shell(tmp_path), **extra)


def _quiet_shell(tmp_path):
    # 本机 /etc/profile.d/nvm.sh 会让 `sh -lc true` 输出 "nvm"（正是 doctor 要抓的问题），测试用一个安静的假 shell
    sh = tmp_path / "quiet.sh"
    sh.write_text("#!/bin/sh\nexit 0\n")
    sh.chmod(0o755)
    return str(sh)


def test_doctor_after_setup(env, home, tmp_path):
    _setup(env, home)
    p = _doctor(env, home, tmp_path)
    out = p.stdout.decode()
    assert "失败" not in out, out
    assert p.returncode == 0
    assert "通过  Codex Stop hook" in out and "通过  Claude Code Stop hook" in out
    assert "通过  Claude Code 沙箱依赖：bwrap、socat 都在" in out
    assert "\033[" not in out  # 不是终端就不加颜色


def test_doctor_accepts_group_not_at_end(env, home, tmp_path):
    """I7：doctor 只要求「存在且命令串一致」，不再要求在数组末尾。"""
    _setup(env, home)
    path = os.path.join(home, ".codex", "hooks.json")
    hj = json.load(open(path))
    for arr in hj["hooks"].values():
        arr.append(OTHER)
    json.dump(hj, open(path, "w"))
    p = _doctor(env, home, tmp_path)
    assert p.returncode == 0, p.stdout.decode()


def test_doctor_flags_command_mismatch_and_duplicates(env, home, tmp_path):
    _setup(env, home)
    path = os.path.join(home, ".codex", "hooks.json")
    hj = json.load(open(path))
    hj["hooks"]["Stop"][0]["hooks"][0]["command"] = hj["hooks"]["Stop"][0]["hooks"][0]["command"].replace(BIN, "/old/teamflow")
    hj["hooks"]["SessionEnd"].append(hj["hooks"]["SessionEnd"][0])
    json.dump(hj, open(path, "w"))
    sp = os.path.join(home, ".claude", "settings.json")
    s = json.load(open(sp))
    s["hooks"]["Stop"][0]["hooks"][0]["args"][-1] = "/elsewhere/credentials.json"
    json.dump(s, open(sp, "w"))
    p = _doctor(env, home, tmp_path)
    out = p.stdout.decode()
    assert p.returncode == 1
    assert "失败  Codex Stop hook 命令串" in out
    assert "失败  Codex SessionEnd hook" in out and "有 2 组 teamflow hook" in out
    assert "失败  Claude Code Stop hook 命令串" in out
    assert "通过  Codex SessionStart hook" in out


def test_doctor_sandbox_deps_missing_on_linux(env, home, tmp_path):
    """S6：Linux 上 sandbox.enabled=true 但缺 bwrap / socat → 标红，说明凭据保护不生效。"""
    _setup(env, home)
    if not sys.platform.startswith("linux"):
        pytest.skip("只在 Linux 上检查")
    p = _doctor(env, home, tmp_path, deps=("socat",), system_path=False)
    out = p.stdout.decode()
    assert p.returncode == 1
    assert "失败  Claude Code 沙箱依赖：缺少 bwrap" in out
    assert "沙箱不会生效，凭据保护等于没有" in out
    assert "sudo apt-get install bubblewrap socat" in out
    p = _doctor(env, home, tmp_path / "none", deps=(), system_path=False)
    assert "缺少 bwrap、socat" in p.stdout.decode()


def test_doctor_sandbox_check_rules():
    import io

    from teamflow import doctor

    def run(settings, platform, have):
        out = io.StringIO()
        r = doctor.Report(out)
        doctor.check_sandbox(r, settings, platform=platform, which=lambda n: "/usr/bin/" + n if n in have else None)
        return r.failed, out.getvalue()

    on = {"sandbox": {"enabled": True}}
    assert run(on, "linux", ())[0] == 1
    assert run(on, "linux", ("bwrap", "socat")) == (0, "通过  Claude Code 沙箱依赖：bwrap、socat 都在\n")
    assert run(on, "darwin", ())[0] == 0  # macOS 用 Seatbelt，不需要这两个
    failed, text = run({"sandbox": {"enabled": False}}, "linux", ())
    assert failed == 0 and "没有开启" in text  # 用户明确关掉的：只提示
    assert run({}, "linux", ())[0] == 0


def test_doctor_failures_red_on_tty(monkeypatch):
    import io

    from teamflow import doctor

    class Tty(io.StringIO):
        def isatty(self):
            return True

    monkeypatch.delenv("NO_COLOR", raising=False)
    out = Tty()
    r = doctor.Report(out)
    r.fail("x", "y")
    r.ok("z")
    assert out.getvalue().startswith("\033[31m失败\033[0m  x")
    assert "通过  z" in out.getvalue()
    monkeypatch.setenv("NO_COLOR", "1")
    out = Tty()
    doctor.Report(out).fail("x", "y")
    assert "\033[" not in out.getvalue()


def test_doctor_reports_missing(env, home, tmp_path):
    p = _doctor(env, home, tmp_path)
    assert p.returncode == 1
    assert "失败" in p.stdout.decode()


def test_doctor_flags_noisy_shell(env, home, tmp_path):
    _setup(env, home)
    noisy = tmp_path / "noisy.sh"
    noisy.write_text("#!/bin/sh\necho 'Welcome!'\nexec /bin/sh \"$@\"\n")
    noisy.chmod(0o755)
    p = env.run(["doctor", "--home", home, "--bin", BIN], PATH=_fake_bin(tmp_path) + ":/usr/bin:/bin", SHELL=str(noisy))
    assert p.returncode == 1
    assert "profile 有输出" in p.stdout.decode()
