"""本地试用脚本的离线测试：bash 语法、shellcheck（装了才跑）、_trial.py 的几个小工具。

不起服务端、不碰 HOME、不碰仓库的 .local/。运行：.venv/bin/pytest -q scripts/tests
"""

import json
import os
import shutil
import stat
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
sys.dont_write_bytecode = True
import _trial  # noqa: E402

SHELL_SCRIPTS = sorted(
    os.path.join(SCRIPTS, n) for n in os.listdir(SCRIPTS) if n.endswith(".sh")
)


@pytest.mark.parametrize("path", SHELL_SCRIPTS, ids=os.path.basename)
def test_bash_syntax(path):
    p = subprocess.run(["bash", "-n", path], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr


def test_shellcheck_clean():
    sc = shutil.which("shellcheck")
    if not sc:
        pytest.skip("没有 shellcheck")
    p = subprocess.run([sc, "-x", "-S", "style", *SHELL_SCRIPTS], capture_output=True, text=True, cwd=os.path.dirname(SCRIPTS))
    assert p.returncode == 0, p.stdout + p.stderr


def test_entry_scripts_executable():
    for n in ("local-up.sh", "local-down.sh", "local-reset.sh", "login-link.sh", "try-claude.sh", "try-codex.sh",
              "sim-teammate.py"):
        assert os.access(os.path.join(SCRIPTS, n), os.X_OK), n


def test_login_links_takes_last_banner(tmp_path):
    log = tmp_path / "server.log"
    code1, code2 = "a" * 32, "b" * 32  # 登录码样本运行时拼
    log.write_text(
        "teamflow-server: 本地试用登录链接（每个只能用一次，10 分钟内有效，重启服务端后作废）：\n"
        "teamflow-server:   me     http://127.0.0.1:8301/dev/login?code=%s&as=me\n"
        "INFO:     Application startup complete.\n"
        "teamflow-server: 本地试用登录链接（每个只能用一次，10 分钟内有效，重启服务端后作废）：\n"
        "teamflow-server:   me     http://127.0.0.1:8301/dev/login?code=%s&as=me\n"
        "teamflow-server:   bob    http://localhost:8301/dev/login?code=%s&as=bob\n"
        "teamflow-server: 两个人的链接分别用 127.0.0.1 和 localhost……\n" % (code1, code2, code1),
        encoding="utf-8",
    )
    links = _trial.login_links(str(log))
    assert [h for h, _ in links] == ["me", "bob"]
    assert links[0][1].endswith("code=%s&as=me" % code2)


def test_gen_env_and_dev_tokens(tmp_path):
    path = tmp_path / "tokens.env"
    _trial.gen_env(str(path), "me", ["bob", "carol"])
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    env = _trial.read_env(str(path))
    assert env["TF_MEMBERS"] == "me,bob,carol"
    toks = [v for k, v in env.items() if k.startswith("TF_TOKEN_")]
    assert len(toks) == 6 and len(set(toks)) == 6 and all(t.startswith("tf_pat_") and len(t) == 39 for t in toks)
    parts = _trial.dev_tokens(env).split(",")
    assert len(parts) == 6
    assert {tuple(p.split(":")[1:]) for p in parts} == {(h, c) for h in ("me", "bob", "carol") for c in ("claude_code", "codex")}


def test_import_codex_config_copies_only_allowlist(tmp_path):
    pytest.importorskip("tomlkit")
    import tomllib

    src = tmp_path / "config.toml"
    secret = "sk-" + "x" * 24  # 样本运行时拼
    src.write_text(
        'model = "gpt-5.5-codex"\n'
        'model_provider = "relay"\n'
        'notify = ["say", "done"]\n'
        "[model_providers.relay]\n"
        'name = "relay"\nbase_url = "https://relay.example/v1"\nenv_key = "RELAY_KEY"\n'
        "[mcp_servers.other]\n"
        'command = "other-mcp"\nenv = { TOKEN = "%s" }\n'
        "[features]\nhooks = false\nweb_search_request = true\n"
        '[hooks.state."/x/hooks.json:stop:0:0"]\ntrusted_hash = "sha256:1"\n'
        '[projects."/home/me/work"]\ntrust_level = "trusted"\n' % secret,
        encoding="utf-8",
    )
    dst = tmp_path / "out" / "config.toml"
    copied = _trial.import_codex_config(str(src), str(dst))
    assert stat.S_IMODE(os.stat(dst).st_mode) == 0o600
    out = tomllib.loads(dst.read_text(encoding="utf-8"))
    assert set(copied) == {"model", "model_provider", "model_providers", "features", "projects"}
    assert "mcp_servers" not in out and "hooks" not in out and "notify" not in out
    assert out["features"] == {"web_search_request": True}  # 试用要用 hooks：不抄 hooks = false
    assert secret not in dst.read_text(encoding="utf-8")


def test_codex_trust_counts_our_hooks(tmp_path):
    hooks = tmp_path / "codex" / "hooks.json"
    hooks.parent.mkdir()
    hooks.write_text("{}")
    cfg = tmp_path / "codex" / "config.toml"
    lines = []
    for label in ("session_start", "user_prompt_submit", "stop"):
        lines.append('[hooks.state."%s:%s:0:0"]\ntrusted_hash = "sha256:%s"\n' % (hooks, label, "0" * 8))
    lines.append('[hooks.state."/other/hooks.json:session_end:0:0"]\ntrusted_hash = "sha256:1"\n')
    lines.append('[hooks.state."%s:session_end:0:0"]\nenabled = true\n' % hooks)  # 没有 trusted_hash 不算
    cfg.write_text("".join(lines), encoding="utf-8")
    assert _trial.codex_trust(str(cfg), str(hooks)) == 3
    with open(cfg, "a", encoding="utf-8") as f:
        f.write('[hooks.state."%s:session_end:0:1"]\ntrusted_hash = "sha256:2"\n' % hooks)
    assert _trial.codex_trust(str(cfg), str(hooks)) == 4


def test_probe_members_includes_token_handles():
    pytest.importorskip("teamflow_server")
    p = subprocess.run([sys.executable, os.path.join(SCRIPTS, "_trial.py"), "probe-members", "me", "bob,carol"],
                       capture_output=True, text=True, timeout=60, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    assert p.returncode == 0, p.stderr
    members = p.stdout.strip().split(",")
    assert {"me", "bob", "carol"} <= set(members), members


def test_sim_teammate_help_without_local_env(tmp_path):
    """没有 .local 时给出中文提示，不抛异常（复制脚本到临时目录跑，不碰仓库的 .local）。"""
    d = tmp_path / "repo" / "scripts"
    d.mkdir(parents=True)
    for n in ("sim-teammate.py", "_trial.py"):
        shutil.copy(os.path.join(SCRIPTS, n), d / n)
    p = subprocess.run([sys.executable, str(d / "sim-teammate.py"), "status"], capture_output=True, text=True, timeout=30)
    assert p.returncode == 1
    assert "scripts/local-up.sh" in p.stderr
