"""M0 复审新问题 4：setup --dry-run 不再打印整份文件。

只打印 teamflow 相关键的「改动前→改动后」，并对输出做通用遮蔽（像 token / secret / key 的值、邮箱、oauthAccount）。
下面所有「像密钥」的样本都在运行时拼接，源码里不出现完整字面量（GitHub 推送保护会拦）。
"""

import json
import os

from teamflow import redact

BIN = "/opt/tf/bin/teamflow"


def _j(*parts):
    return "".join(parts)


# 各家密钥的假样本（运行时拼接）
SECRETS = {
    "anthropic": _j("sk-", "ant-", "api03-", "Qw7Zr2Lm9Kp4Xv1Nb8Tc3Hd6Fg0Js5Ye"),
    "openai": _j("sk-", "proj-", "Zx9Cv8Bn7Mm6Lk5Jh4Gf3Dd2Ss1Aa0Qq"),
    "github": _j("gh", "p_", "R4nD0mGh1tHubT0k3nV4lu3Xy9Zz8Ww7Vv6"),
    "github_pat": _j("github_", "pat_", "11ABCDEFG0", "abcdefghijklmnopqrstuvwxyz0123"),
    "slack": _j("xo", "xb-", "123456789012", "-", "1234567890123", "-", "AbCdEfGhIjKlMnOpQrStUvWx"),
    "stripe": _j("rk", "_live_", "51Hx", "AbCdEfGhIjKlMnOpQrStUvWxYz0123"),
    "stripe_sk": _j("sk", "_test_", "4eC39Hq", "LyjWDarjtT1zdp7dc"),
    "aws": _j("AK", "IA", "QWERTYUIOPASDFGH"),
    "aws_secret": _j("wJalrXUtnFEMI", "/K7MDENG/", "bPxRfiCYzEXAMPLEKEY"),
    "google": _j("AI", "za", "SyD-1234567890abcdefghijklmnopqrstu"),
    "jwt": _j("ey", "JhbGciOiJIUzI1NiJ9", ".", "eyJzdWIiOiIxMjM0NTY3ODkwIn0", ".", "dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"),
    "gitlab": _j("gl", "pat-", "AbCdEfGhIjKlMnOpQrSt"),
    "hexkey": _j("9f8e7d6c5b4a", "39281706f5e4d3c2", "b1a0f9e8d7c6b5a4"),
    "dbpass": _j("hunter", "2-Very-", "Secret"),
}
EMAIL = _j("someone.private", "@", "corp-example", ".com")


def _write_existing(home):
    os.makedirs(os.path.join(home, ".codex"), exist_ok=True)
    os.makedirs(os.path.join(home, ".claude"), exist_ok=True)
    cj = {
        "numStartups": 12,
        "userID": SECRETS["hexkey"],
        "oauthAccount": {"accountUuid": "123e4567-e89b-12d3-a456-426614174000", "emailAddress": EMAIL,
                         "organizationName": "Corp"},
        "mcpServers": {
            "github": {"type": "http", "url": "https://api.githubcopilot.example/mcp/",
                       "headers": {"Authorization": "Bearer " + SECRETS["github"]}},
            "anth": {"type": "stdio", "command": "npx", "args": ["-y", "some-mcp", "--api-key", SECRETS["anthropic"]],
                     "env": {"ANTHROPIC_API_KEY": SECRETS["anthropic"], "SLACK_BOT_TOKEN": SECRETS["slack"]}},
            "pay": {"type": "stdio", "command": "pay-mcp", "env": {"STRIPE_KEY": SECRETS["stripe"],
                                                                   "AWS_ACCESS_KEY_ID": SECRETS["aws"],
                                                                   "AWS_SECRET_ACCESS_KEY": SECRETS["aws_secret"]}},
            "gl": {"type": "http", "url": "https://gitlab.example/api/mcp?private_token=" + SECRETS["gitlab"]},
        },
        "projects": {"/home/u/repo": {"mcpServers": {"db": {"command": "db-mcp",
                                                              "args": ["postgres://app:" + SECRETS["dbpass"] + "@db/x"]}}}},
    }
    with open(os.path.join(home, ".claude.json"), "w", encoding="utf-8") as f:
        json.dump(cj, f, ensure_ascii=False, indent=2)
    toml = (
        'model = "gpt-5.5-codex"\n'
        "\n[mcp_servers.other]\n"
        'command = "other-mcp"\n'
        'env = { OPENAI_API_KEY = "%s", GOOGLE_API_KEY = "%s" }\n'
        "\n[mcp_servers.remote]\n"
        'url = "https://remote.example/mcp"\n'
        'http_headers = { Authorization = "Bearer %s", "X-Api-Key" = "%s" }\n'
        "\n[mcp_servers.jwtsrv]\n"
        'url = "https://jwt.example/mcp"\n'
        'bearer_token = "%s"\n'
    ) % (SECRETS["openai"], SECRETS["google"], SECRETS["github_pat"], SECRETS["stripe_sk"], SECRETS["jwt"])
    with open(os.path.join(home, ".codex", "config.toml"), "w", encoding="utf-8") as f:
        f.write(toml)
    # 别人的 hook 和 settings 里也放密钥
    settings = {"env": {"GITHUB_TOKEN": SECRETS["github"]},
                "hooks": {"Stop": [{"hooks": [{"type": "command",
                                               "command": "curl -H 'Authorization: Bearer %s' https://x" % SECRETS["openai"]}]}]}}
    with open(os.path.join(home, ".claude", "settings.json"), "w", encoding="utf-8") as f:
        json.dump(settings, f)
    with open(os.path.join(home, ".codex", "hooks.json"), "w", encoding="utf-8") as f:
        json.dump({"description": "mine", "hooks": {"Stop": [{"hooks": [
            {"type": "command", "command": "notify --token %s" % SECRETS["slack"]}]}]}}, f)


def _snapshot(home):
    out = {}
    for root, _, files in os.walk(home):
        for n in files:
            p = os.path.join(root, n)
            with open(p, "rb") as f:
                out[p] = f.read()
    return out


def _assert_clean(out):
    for name, v in SECRETS.items():
        assert v not in out, name
        # 片段也不能出现（防止只遮掉一半）
        assert v[-12:] not in out, name
    assert EMAIL not in out and "corp-example" not in out
    assert "oauthAccount" not in out and "emailAddress" not in out


def test_dry_run_hides_other_servers_secrets(env):
    home = env.home
    _write_existing(home)
    before = _snapshot(home)
    p = env.run(["setup", "--home", home, "--bin", BIN, "--dry-run"],
                TEAMFLOW_PAT_CLAUDE=_j("tf_pat_", "abcDEF123"), TEAMFLOW_PAT_CODEX=_j("tf_pat_", "xyzXYZ789"))
    assert p.returncode == 0, p.stderr.decode()
    out = p.stdout.decode()
    _assert_clean(out)
    assert "abcDEF123" not in out and "xyzXYZ789" not in out
    # 别的 MCP server、别人的 hook 一个字都不打印
    for name in ("github", "anth", "pay", "remote", "jwtsrv", "other-mcp", "numStartups", "projects", "notify",
                 "curl", "GITHUB_TOKEN", "model"):
        assert name not in out, name
    # 只列 teamflow 相关的键
    assert "=== 将写入 %s（修改，只列 teamflow 相关的改动）===" % os.path.join(home, ".claude.json") in out
    assert "  mcpServers.teamflow（新增）\n    改动前：（无）\n" in out
    assert "  mcp_servers.teamflow（新增）\n    改动前：（无）\n" in out
    assert "  hooks.SessionStart（新增）" in out and "  hooks.Stop[1]（新增）" in out
    assert "  permissions（新增）" in out or "  permissions.allow（新增）" in out
    assert _snapshot(home) == before  # dry-run 不写


def test_dry_run_masks_secrets_inside_teamflow_fragments(env):
    """teamflow 自己的条目被手改过、塞了别的凭据：改动前那一栏照样遮蔽。"""
    home = env.home
    os.makedirs(os.path.join(home, ".codex"))
    with open(os.path.join(home, ".claude.json"), "w") as f:
        json.dump({"oauthAccount": {"emailAddress": EMAIL},
                   "mcpServers": {"teamflow": {"type": "http", "url": "http://old/mcp/",
                                               "headers": {"Authorization": "Bearer " + SECRETS["github"],
                                                           "X-Contact": EMAIL}}}}, f)
    with open(os.path.join(home, ".codex", "config.toml"), "w") as f:
        f.write('[mcp_servers.teamflow]\nurl = "http://old/mcp/"\nenv = { API_TOKEN = "%s" }\n' % SECRETS["openai"])
    p = env.run(["setup", "--home", home, "--bin", BIN, "--dry-run"])
    out = p.stdout.decode()
    _assert_clean(out)
    assert "  mcpServers.teamflow.headers（删除）\n    改动前：{\"Authorization\": \"****\", \"X-Contact\": \"s***@***\"}" in out
    assert "  mcpServers.teamflow.url\n    改动前：\"http://old/mcp/\"\n    改动后：\"http://127.0.0.1:8100/mcp/\"" in out
    assert "  mcp_servers.teamflow.env（删除）\n    改动前：{\"API_TOKEN\": \"****\"}" in out


def test_dry_run_after_setup_shows_only_changes(env):
    home = env.home
    _write_existing(home)
    assert env.run(["setup", "--home", home, "--bin", BIN]).returncode == 0
    p = env.run(["setup", "--home", home, "--bin", BIN, "--dry-run"])
    out = p.stdout.decode()
    assert "改动前" not in out  # 什么都不变
    assert out.count("=== 不变 ") >= 6
    _assert_clean(out)
    # 换了可执行文件路径：只列 hook 命令和 deny 规则这些改动
    p = env.run(["setup", "--home", home, "--bin", "/new/place/teamflow", "--dry-run"])
    out = p.stdout.decode()
    _assert_clean(out)
    assert "  hooks.Stop[1].hooks[0].command\n    改动前：\"/opt/tf/bin/teamflow\"\n    改动后：\"/new/place/teamflow\"\n" in out
    assert "  mcpServers.teamflow.headersHelper\n" in out
    assert "curl" not in out and "notify" not in out  # 别人的组没变，不出现


def test_redact_text_patterns():
    for name, v in SECRETS.items():
        if name in ("dbpass", "aws_secret"):
            continue  # 这两种没有固定格式，靠键名或 KEY=VALUE 遮
        assert v not in redact.redact_text("x %s y" % v), name
    assert redact.redact_text("Authorization: Bearer " + SECRETS["dbpass"]) == "Authorization: Bearer ****"
    assert redact.redact_text("Bearer " + SECRETS["dbpass"]) == "Bearer ****"
    assert redact.redact_text("AWS_SECRET_ACCESS_KEY=" + SECRETS["aws_secret"]) == "AWS_SECRET_ACCESS_KEY=****"
    assert redact.redact_text("run --api-key " + SECRETS["dbpass"] + " now") == "run --api-key **** now"
    assert redact.redact_text("https://h/x?access_token=" + SECRETS["dbpass"] + "&a=1") == "https://h/x?access_token=****&a=1"
    assert redact.redact_text("mail " + EMAIL) == "mail s***@***"
    assert redact.redact_text(_j("tf_pat_", "abc")) == "tf_pat_****"
    assert redact.redact_text("tf_pat_****") == "tf_pat_****"  # 幂等


def test_redact_keeps_teamflow_paths_readable():
    """遮蔽不能误伤路径和命令串：dry-run 要让人看得懂我们写了什么。"""
    for s in ("/Users/Alice/Library/Python/3.12/bin/teamflow hook session-start --client codex --cred "
              "/Users/Alice/.config/teamflow/credentials.json",
              "/tmp/pytest-of-root/pytest-12/test_dry_run_hides_other_servers_0/home/.config/teamflow/credentials.json",
              "http://127.0.0.1:8100/mcp/", "startup|resume|clear|compact|fork", "Bash(teamflow mcp-headers:*)",
              "mcp__teamflow__*", "~/.aws/credentials", "123e4567-e89b-12d3-a456-426614174000"):
        assert redact.redact_text(s) == s, s
    entry = {"type": "http", "url": "http://127.0.0.1:8100/mcp/", "headersHelper": "/opt/tf/bin/teamflow mcp-headers"}
    assert redact.redact(entry) == entry
    sb = {"enabled": True, "credentials": {"files": [{"path": "~/.ssh", "mode": "deny"}]}}
    assert redact.redact(sb) == sb  # sandbox.credentials 是要保护的路径，不是密钥


def test_redact_structural_keys():
    obj = {"oauthAccount": {"emailAddress": EMAIL, "accountUuid": "u-1", "n": 3, "ok": True},
           "env": {"MY_SERVICE_KEY": "plainvalue", "DEBUG": "1"},
           "tokens": {"claude": _j("tf_pat_", "x1"), "codex": "", "other": "abc"},
           "git_emails": [EMAIL],
           "args": ["--token", "plain-but-secret", "--verbose"]}
    assert redact.redact(obj) == {
        "oauthAccount": {"emailAddress": "s***@***", "accountUuid": "****", "n": "****", "ok": True},
        "env": {"MY_SERVICE_KEY": "****", "DEBUG": "1"},
        "tokens": {"claude": "tf_pat_****", "codex": "", "other": "****"},
        "git_emails": ["s***@***"],
        "args": ["--token", "****", "--verbose"],
    }


def test_diff_lists_only_changed_fragments():
    other = {"hooks": [{"type": "command", "command": "mine"}]}
    old = {"hooks": {"Stop": [other, {"hooks": [{"command": "/a/teamflow", "args": ["hook"]}]}]}, "model": "x"}
    new = {"hooks": {"Stop": [other, {"hooks": [{"command": "/b/teamflow", "args": ["hook"]}]}, {"hooks": []}]},
           "model": "x"}
    got = redact.diff(old, new)
    assert got == [(("hooks", "Stop", 1, "hooks", 0, "command"), "/a/teamflow", "/b/teamflow"),
                   (("hooks", "Stop", 2), redact.MISSING, {"hooks": []})]
    lines = redact.render(old, dict(new, model="y"), roots=(("hooks",),))
    assert lines[-1] == "  另有 1 处改动不在 teamflow 相关的键里，内容不显示（见下面的「注意」）"
    assert "model" not in "\n".join(lines)
