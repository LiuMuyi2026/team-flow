"""Stop：只记录本人邮箱的新提交（最多 5 条），其他作者只计数；remote 去凭据。"""

import io
import json
import os
import subprocess

from tfhelpers import stdin_for

from teamflow import doctor, gitinfo, spool


def _git(repo, *args, email="me@example.com"):
    env = dict(os.environ, GIT_AUTHOR_NAME="x", GIT_AUTHOR_EMAIL=email, GIT_COMMITTER_NAME="x",
               GIT_COMMITTER_EMAIL=email, GIT_CONFIG_NOSYSTEM="1")
    return subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True, env=env, text=True).stdout


def _repo(tmp_path):
    repo = str(tmp_path / "repo")
    os.makedirs(repo)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "Me@Example.com")
    _git(repo, "remote", "add", "origin", "https://alice:ghp_SECRET123@github.com/acme/api.git?x=1")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "init")
    return repo


def test_stop_reports_own_commits_only(env, stub, tmp_path):
    env.write_cred(stub.url)
    repo = _repo(tmp_path)
    assert env.hook("session-start", "codex", stdin_for("codex", "session-start", repo)).returncode == 0
    body = [r for r in stub.requests if r["path"] == "/api/v1/hooks/session-start"][0]["body"]
    assert body["repo"] == "https://github.com/acme/api.git"
    assert body["branch"] == "main" and len(body["head"]) == 40
    for i in range(7):
        _git(repo, "commit", "-q", "--allow-empty", "-m", "我的提交 %d" % i)
    _git(repo, "commit", "-q", "--allow-empty", "-m", "别人的提交", email="other@example.com")
    assert env.hook("stop", "codex", stdin_for("codex", "stop", repo)).returncode == 0
    (rec,) = env.spool_records()
    item = rec["item"]
    assert rec["kind"] == "commit"
    assert [c["title"] for c in item["commits"]] == ["我的提交 %d" % i for i in (6, 5, 4, 3, 2)]
    assert item["own_more"] == 2
    assert item["other_commits"] == 1
    assert item["repo"] == "https://github.com/acme/api.git"
    # HEAD 已推进：下一回合没有新提交
    env.hook("stop", "codex", stdin_for("codex", "stop", repo, turn_id="turn-2"))
    recs = [r for r in env.spool_records() if r["item"]["turn"] == "turn-2"]
    assert recs[0]["item"]["commits"] == [] and recs[0]["kind"] == "heartbeat"


def test_first_stop_without_baseline_reports_nothing(env, stub, tmp_path):
    env.write_cred(stub.url)
    repo = _repo(tmp_path)
    env.hook("stop", "claude", stdin_for("claude", "stop", repo))
    (rec,) = env.spool_records()
    assert rec["item"]["commits"] == []


def test_strip_credentials():
    s = gitinfo.strip_credentials
    assert s("https://u:tok@github.com/a/b.git") == "https://github.com/a/b.git"
    assert s("https://tok@gitlab.example.com:8443/a/b?private_token=x#f") == "https://gitlab.example.com:8443/a/b"
    assert s("ssh://git@github.com/a/b.git") == "ssh://github.com/a/b.git"
    assert s("git@github.com:a/b.git") == "github.com:a/b.git"
    assert s("/srv/git/b.git") == "/srv/git/b.git"
    assert s(None) is None


def test_non_repo_cwd(tmp_path):
    assert gitinfo.session_info(str(tmp_path)) == {}
    assert gitinfo.head(str(tmp_path)) is None


def _doctor_line(isolated=False):
    out = io.StringIO()
    doctor.check_no_repo(doctor.Report(out), isolated=isolated)
    return out.getvalue()


def _bare_repo(tmp_path, name="demo"):
    repo = str(tmp_path / name)
    os.makedirs(repo)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "me@example.com")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "init")
    return os.path.realpath(repo)


def test_commits_in_repo_without_origin_are_reported(env, stub, tmp_path):
    """本地试用：演示仓库没有 origin 时提交被服务端悄悄丢掉。现在服务端回 st=no_repo，
    spool 按仓库记一条提醒，doctor 报出来；会话中途加上 origin 后，Stop 补读仓库地址，提交照常上报，提醒自动消失。"""
    env.write_cred(stub.url)
    repo = _bare_repo(tmp_path)
    env.hook("session-start", "claude", stdin_for("claude", "session-start", repo))
    _git(repo, "commit", "-q", "--allow-empty", "-m", "接口联调")
    env.hook("stop", "claude", stdin_for("claude", "stop", repo))
    (rec,) = env.spool_records()
    assert rec["item"]["repo"] is None and len(rec["item"]["commits"]) == 1
    assert rec["dir"] == repo and "dir" not in rec["item"]  # 仓库目录只在本地，不上传
    stub.item_extra[rec["key"]] = {"st": "no_repo", "dropped": 1}
    assert env.run(["flush"]).returncode == 0
    assert env.spool_records() == [] and env.dead_records() == []  # 心跳本身送到了，不进 dead-letter
    (nr,) = spool.unrecorded()
    assert nr["n"] == 1 and nr["name"] == "demo" and nr["dir"] == repo and nr["why"] == "no_repo"
    text = _doctor_line()
    assert text.startswith("失败  仓库 demo（%s）最近 7 天有 1 个提交没被服务端记下" % repo)
    assert "git remote add origin" in text and "和队友 clone 时同一个" in text
    assert "假地址" not in text and "随便" not in text  # 正式版的修法不教人写假地址
    assert "假地址" in _doctor_line(isolated=True) and "不要对它 push" in _doctor_line(isolated=True)
    assert "没有 origin" in env.log_text()

    # 补上 origin、还没有新提交：doctor 只给提示，不算失败（免得像是修了没用）
    _git(repo, "remote", "add", "origin", "https://example.com/me/tf-demo.git")
    out = io.StringIO()
    rep = doctor.Report(out)
    doctor.check_no_repo(rep)
    assert rep.failed == 0 and out.getvalue().startswith("提示  仓库 demo") and "下一次提交上报后" in out.getvalue()

    # 下一回合 Stop 补读地址，提交带着 repo 上报；成功后提醒清掉
    _git(repo, "commit", "-q", "--allow-empty", "-m", "补测试")
    env.hook("stop", "claude", stdin_for("claude", "stop", repo, prompt_id="550e8400-e29b-41d4-a716-446655440001"))
    (rec,) = env.spool_records()
    assert rec["item"]["repo"] == "https://example.com/me/tf-demo.git" and len(rec["item"]["commits"]) == 1
    assert env.run(["flush"]).returncode == 0
    assert spool.unrecorded() == []
    assert _doctor_line().startswith("通过  没有漏记的提交")


def test_notice_is_per_repo(env, stub, tmp_path):
    """红队：提醒原来是全局一份，别的仓库提交成功就清掉了。现在按仓库目录记，只清同一个仓库的。"""
    env.write_cred(stub.url)
    a = _bare_repo(tmp_path, "a-no-origin")
    b = _bare_repo(tmp_path, "b-with-origin")
    _git(b, "remote", "add", "origin", "https://example.com/me/b.git")
    sid_b = "0f0e8f6a-3c1d-4e55-9f43-2b1a7e5d9c11"
    env.hook("session-start", "claude", stdin_for("claude", "session-start", a))
    env.hook("session-start", "claude", stdin_for("claude", "session-start", b, session_id=sid_b))
    _git(a, "commit", "-q", "--allow-empty", "-m", "A 的提交")
    _git(b, "commit", "-q", "--allow-empty", "-m", "B 的提交")
    env.hook("stop", "claude", stdin_for("claude", "stop", a))
    env.hook("stop", "claude", stdin_for("claude", "stop", b, session_id=sid_b))
    for rec in env.spool_records():
        if rec["item"]["repo"] is None:
            stub.item_extra[rec["key"]] = {"st": "no_repo", "dropped": 1}
    assert env.run(["flush"]).returncode == 0
    (nr,) = spool.unrecorded()
    assert nr["dir"] == a  # B 的提交成功上报，没有清掉 A 的提醒
    assert "a-no-origin" in _doctor_line()


def test_lost_response_then_409_still_notes_no_repo(env, stub, tmp_path):
    """红队：服务端已经处理了 no_repo 那条，响应在路上丢了；重试拿到 409 dup。
    新服务端带回 was=no_repo 和 dropped；旧服务端什么都不带，没有 repo 的提交服务端一定没记，同样记提醒。"""
    env.write_cred(stub.url)
    repo = _bare_repo(tmp_path)
    env.hook("session-start", "codex", stdin_for("codex", "session-start", repo))
    for i in range(7):
        _git(repo, "commit", "-q", "--allow-empty", "-m", "提交 %d" % i)
    env.hook("stop", "codex", stdin_for("codex", "stop", repo))
    (rec,) = env.spool_records()
    assert rec["item"]["own_more"] == 2
    stub.item_status[rec["key"]] = 409
    stub.item_extra[rec["key"]] = {"st": "dup", "was": "no_repo", "dropped": 7}
    assert env.run(["flush"]).returncode == 0
    assert spool.unrecorded()[0]["n"] == 7

    # 旧服务端：409 不带任何说明，按 5 条加 own_more 2 条记
    env.hook("stop", "codex", stdin_for("codex", "stop", repo, turn_id="turn-2"))
    for i in range(7):
        _git(repo, "commit", "-q", "--allow-empty", "-m", "又一个提交 %d" % i)
    env.hook("stop", "codex", stdin_for("codex", "stop", repo, turn_id="turn-3"))
    recs = [r for r in env.spool_records() if r["item"]["turn"] == "turn-3"]
    stub.item_status[recs[0]["key"]] = 409
    assert env.run(["flush"]).returncode == 0
    assert spool.unrecorded()[0]["n"] == 14


def test_origin_of_another_workspace_added_mid_session_is_not_reported(env, stub, tmp_path):
    """红队 major：会话开始时仓库没有 origin，按 cwd 落到 default workspace 并钉住；中途补上的 origin 按
    repo_patterns 属于另一个 workspace。原来 Stop 补读后照样把提交 sha、标题、地址发给钉住的 workspace。
    现在这一回合的提交整条不报，记本地提醒，doctor 请用户重开会话；重开后按新 remote 选对 workspace，提醒消失。"""
    os.makedirs(os.path.dirname(env.cred), exist_ok=True)
    tok = {"claude": "tf_pat_claude_x", "codex": "tf_pat_codex_x"}
    with open(env.cred, "w") as f:
        json.dump({"default": "home", "workspaces": {
            "home": {"api_url": stub.url, "tokens": tok, "repo_patterns": []},
            "acme": {"api_url": stub.url, "tokens": tok, "repo_patterns": ["github.com/acme/*"]},
        }}, f)
    os.chmod(env.cred, 0o600)
    repo = _bare_repo(tmp_path, "api")
    env.hook("session-start", "claude", stdin_for("claude", "session-start", repo))
    _git(repo, "remote", "add", "origin", "git@github.com:acme/api.git")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "ACME 内部的提交标题")
    env.hook("stop", "claude", stdin_for("claude", "stop", repo))
    (rec,) = env.spool_records()
    assert rec["ws"] == "home" and rec["kind"] == "heartbeat"
    assert rec["item"]["commits"] == [] and rec["item"]["repo"] is None and rec["item"]["own_more"] == 0
    assert "ACME" not in json.dumps(rec, ensure_ascii=False)
    (nr,) = spool.unrecorded()
    assert nr["why"] == "other_ws" and nr["ws"] == "home" and nr["want_ws"] == "acme" and nr["n"] == 1
    text = _doctor_line()
    assert text.startswith("失败  仓库 api") and "workspace acme" in text and "重开会话" in text
    assert "workspace acme" in env.log_text()
    assert env.run(["flush"]).returncode == 0
    sent = [it for r in stub.requests if r["path"] == "/api/v1/hooks/batch" for it in r["body"]["items"]]
    assert all(not it.get("commits") and not it.get("repo") for it in sent)

    # 重开会话：按新的 remote 选到 acme，提交带着地址报给 acme，提醒消失
    sid2 = "0f0e8f6a-3c1d-4e55-9f43-2b1a7e5d9c12"
    env.hook("session-start", "claude", stdin_for("claude", "session-start", repo, session_id=sid2))
    _git(repo, "commit", "-q", "--allow-empty", "-m", "重开之后的提交")
    env.hook("stop", "claude", stdin_for("claude", "stop", repo, session_id=sid2))
    (rec,) = env.spool_records()
    assert rec["ws"] == "acme" and rec["item"]["repo"] == "github.com:acme/api.git" and len(rec["item"]["commits"]) == 1
    assert env.run(["flush"]).returncode == 0
    assert spool.unrecorded() == []


def test_unrecorded_notice_expires_after_7_days(env):
    spool.note_unrecorded("/x/demo", "demo", 2, "no_repo", 1000.0)
    spool.note_unrecorded("/x/demo", "demo", 3, "no_repo", 2000.0)
    assert spool.unrecorded(2000.0)[0]["n"] == 5
    assert spool.unrecorded(2000.0 + spool.NOTICE_TTL + 1) == []
