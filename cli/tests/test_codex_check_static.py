"""spike/codex_check.sh 的静态检查（成员电脑补测用）与 setup 的「原地替换」一致（M0 评审 I7）。

setup 已有 teamflow 组时原地替换、不挪位置（Codex 的信任键带组序号），所以别人后来在我们后面加了组，
我们的组就不在末尾了；自检脚本不能因此报失败。它只要求每个事件只有一组 teamflow hook。
"""

import json
import os
import shutil
import subprocess
import sys

import pytest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPT = os.path.join(REPO, "spike", "codex_check.sh")
TF = os.path.join(os.path.dirname(sys.executable), "teamflow")
EVENTS = ("SessionStart", "UserPromptSubmit", "Stop", "SessionEnd")

pytestmark = pytest.mark.skipif(
    not (os.path.exists(SCRIPT) and os.path.exists(TF) and shutil.which("bash")),
    reason="没有 spike/codex_check.sh、teamflow 入口或 bash",
)


def _env(home):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("TEAMFLOW_", "CODEX_"))}
    env.pop("SHELL", None)  # 不测 profile 输出（那一项取决于机器）
    env.update({"HOME": str(home), "PATH": os.path.dirname(TF) + os.pathsep + "/usr/bin:/bin",
                "TEAMFLOW_STATE_DIR": str(home / "state")})
    return env


def _setup(home):
    env = dict(_env(home), TEAMFLOW_PAT_CODEX="tf_pat_test_codex_check")
    p = subprocess.run([TF, "setup", "--home", str(home), "--clients", "codex", "--api-url", "http://127.0.0.1:9",
                        "--bin", TF], capture_output=True, env=env, timeout=60)
    assert p.returncode == 0, p.stderr.decode()
    return home / ".codex" / "hooks.json"


def _static(home, out):
    p = subprocess.run(["bash", SCRIPT, "--skip-exec", "--codex-home", str(home / ".codex"),
                        "--cred", str(home / ".config" / "teamflow" / "credentials.json"), "--out", str(out)],
                       capture_output=True, env=_env(home), timeout=120)
    assert p.returncode in (0, 1), p.stderr.decode()
    text = p.stdout.decode()
    assert "tf_pat_test_codex_check" not in text  # 脚本不打印 token
    rows = json.loads((out / "static.json").read_text(encoding="utf-8"))["rows"]
    return {r["name"]: r for r in rows}, text


def _foreign_group(n):
    return {"hooks": [{"type": "command", "command": "/usr/local/bin/other-tool hook %d" % n, "timeout": 3}]}


def test_group_not_at_end_is_fine(tmp_path):
    hj_path = _setup(tmp_path)
    hj = json.loads(hj_path.read_text(encoding="utf-8"))
    for i, ev in enumerate(EVENTS):
        hj["hooks"][ev].append(_foreign_group(i))  # 用户后来在我们后面加了别的组
    hj_path.write_text(json.dumps(hj), encoding="utf-8")

    rows, text = _static(tmp_path, tmp_path / "out")
    assert "数组末尾" not in text
    for ev in EVENTS:
        r = rows["%s 只有一组 teamflow hook" % ev]
        assert r["ok"] is True, r
        assert "第 1/2 组" in r["detail"]
        assert rows["%s 命令串与本机 teamflow setup 生成的一致" % ev]["ok"] is True


def test_rerun_setup_keeps_position_and_check_passes(tmp_path):
    """别人的组在前、我们的在中间、别人的在后：重跑 setup 后位置不变，自检照样通过。"""
    hj_path = _setup(tmp_path)
    hj = json.loads(hj_path.read_text(encoding="utf-8"))
    for i, ev in enumerate(EVENTS):
        hj["hooks"][ev] = [_foreign_group(10 + i), *hj["hooks"][ev], _foreign_group(20 + i)]
    hj_path.write_text(json.dumps(hj), encoding="utf-8")
    _setup(tmp_path)  # 重跑

    rows, _ = _static(tmp_path, tmp_path / "out")
    for ev in EVENTS:
        r = rows["%s 只有一组 teamflow hook" % ev]
        assert r["ok"] is True and "第 2/3 组" in r["detail"], r


def test_duplicate_groups_fail(tmp_path):
    hj_path = _setup(tmp_path)
    hj = json.loads(hj_path.read_text(encoding="utf-8"))
    hj["hooks"]["Stop"].append(json.loads(json.dumps(hj["hooks"]["Stop"][0])))  # 手动复制出第二组
    hj_path.write_text(json.dumps(hj), encoding="utf-8")

    rows, _ = _static(tmp_path, tmp_path / "out")
    r = rows["Stop 只有一组 teamflow hook"]
    assert r["ok"] is False and "有 2 组" in r["detail"], r
    assert rows["SessionStart 只有一组 teamflow hook"]["ok"] is True
