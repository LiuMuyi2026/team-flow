"""Stop：只记录本人邮箱的新提交（最多 5 条），其他作者只计数；remote 去凭据。"""

import os
import subprocess

from tfhelpers import stdin_for

from teamflow import gitinfo


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
