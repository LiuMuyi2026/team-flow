"""M0 复审 m5：兜底命令（inbox / note / done / block）读不到凭据时，给出明确的中文说明和修复办法。

setup 的加固让 Claude Code 沙箱屏蔽凭据文件（sandbox.credentials），agent 从 Bash 跑兜底命令就读不到它：
被屏蔽的文件读出来是空的，或者没有权限。命令串不变，只改输出。输出里永远没有 token。
"""

import builtins
import json
import os

import pytest

from teamflow import board_cmd, common

CMDS = {
    "note": ["note", "T-42", "进度"],
    "done": ["done", "T-42", "完成"],
    "block": ["block", "--title", "测试库连不上"],
    "inbox": ["inbox"],
}


def _empty_cred(tmp_path):
    p = tmp_path / "masked" / "credentials.json"
    p.parent.mkdir()
    p.write_bytes(b"")  # 被沙箱屏蔽的文件可能读出来是空的
    return str(p)


@pytest.mark.parametrize("cmd", sorted(CMDS))
def test_masked_by_sandbox_in_claude_code(env, tmp_path, cmd):
    cred = _empty_cred(tmp_path)
    p = env.run([*CMDS[cmd], "--cred", cred], CLAUDECODE="1")
    assert p.returncode == 1
    err = p.stderr.decode()
    assert err.startswith("teamflow %s：credentials：凭据文件 %s 是空的\n" % (cmd, cred))
    assert "这条命令是在 Claude Code 里运行的" in err and "沙箱屏蔽了凭据文件" in err
    assert "MCP 工具" in err and "在沙箱外重跑这条命令" in err and "自己的终端里运行同一条命令" in err
    assert p.stdout == b""


def test_masked_outside_claude_code_still_hints(env, tmp_path):
    cred = _empty_cred(tmp_path)
    p = env.run(["note", "T-42", "进度", "--cred", cred])
    err = p.stderr.decode()
    assert "如果是在 Claude Code 的沙箱里运行的" in err
    assert "不是在沙箱里的话：重跑 teamflow setup 重新生成" in err


def test_json_output_carries_fix(env, tmp_path):
    cred = _empty_cred(tmp_path)
    p = env.run(["done", "T-42", "完成", "--json", "--cred", cred], CLAUDECODE="1")
    assert p.returncode == 1
    obj = json.loads(p.stdout)
    assert obj["ok"] is False and obj["error"] == "credentials" and obj["status"] == 0
    first, *rest = obj["message"].split("\n")
    assert first == "凭据文件 %s 是空的" % cred
    assert any("在沙箱外重跑" in x for x in rest)


def test_permission_denied(monkeypatch, tmp_path):
    """macOS 的 Seatbelt 是「没有权限」；容器里是 root，chmod 000 挡不住，直接模拟 open 报错。"""
    cred = str(tmp_path / "credentials.json")
    real = builtins.open

    def fake_open(path, *a, **kw):
        if path == cred:
            raise PermissionError(1, "Operation not permitted")
        return real(path, *a, **kw)

    monkeypatch.setattr(builtins, "open", fake_open)
    lines = board_cmd.cred_help(cred, "claude", board_cmd.CredFileError("x"), env={"CLAUDECODE": "1"})
    assert lines[0] == "没有权限读取凭据文件 %s" % cred
    assert any("沙箱屏蔽了凭据文件" in x for x in lines)
    assert lines[-1].startswith("不是在沙箱里的话：检查文件的属主和权限")


def test_not_json_and_missing_workspaces(env, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    p = env.run(["note", "T-42", "进度", "--cred", str(bad)])
    err = p.stderr.decode()
    assert "内容不对（不是 JSON，或者没有 workspaces）" in err and "重跑 teamflow setup" in err
    assert "沙箱" not in err
    bad.write_text(json.dumps({"default": "team"}))
    assert "内容不对" in env.run(["inbox", "--cred", str(bad)]).stderr.decode()


def test_missing_token_names_env_var_and_never_prints_tokens(env, tmp_path):
    env.write_cred("http://127.0.0.1:9")
    data = json.load(open(env.cred))
    data["workspaces"]["team"]["tokens"] = {"claude": "tf_pat_only_claude_SECRET"}
    json.dump(data, open(env.cred, "w"))
    for args in (["note", "T-42", "进度", "--client", "codex"], ["inbox", "--client", "codex"]):
        p = env.run([*args, "--cred", env.cred])
        err = p.stderr.decode()
        assert p.returncode == 1
        assert "credentials：凭据文件里还没有 codex 的 token" in err
        assert "设置环境变量 TEAMFLOW_PAT_CODEX 后重跑 teamflow setup" in err
        assert "tf_pat" not in err and "SECRET" not in err
        assert "沙箱" not in err  # 文件读得到，不是沙箱的问题


def test_bad_api_url_and_relative_cred():
    lines = board_cmd.cred_help("/abs/c.json", "claude", common.CredError("api_url 无效"), env={})
    assert lines[0] == "api_url 无效" and "http:// 或 https://" in lines[1]
    lines = board_cmd.cred_help("rel/c.json", "claude", common.CredError("--cred 必须是绝对路径"), env={})
    assert lines[0].startswith("--cred 必须是绝对路径") and lines[1].startswith("修复：")
    lines = board_cmd.cred_help("/abs/c.json", "claude", common.CredError("凭据文件里没有可用的 workspace"), env={})
    assert "--ws" in lines[1]


def test_unreadable_other_oserror(tmp_path):
    d = tmp_path / "adir"
    d.mkdir()
    lines = board_cmd.cred_help(str(d), "claude", board_cmd.CredFileError("x"), env={})
    assert lines[0].startswith("读不了凭据文件 %s（" % d)


def test_command_strings_unchanged():
    """不改命令串：兜底命令名和参数还是 server instructions 里写的那些。"""
    from teamflow import cli

    p = cli._build_parser()
    for argv in (["note", "T-1", "x"], ["done", "T-1", "x"], ["block", "--title", "x"], ["inbox"]):
        assert p.parse_args(argv).cmd == argv[0]
    assert os.path.basename(cli.default_cred("/h")) == "credentials.json"
