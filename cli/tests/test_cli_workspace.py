"""凭据文件：按 cwd / remote 匹配 repo_patterns 选 workspace，匹配不到用 default。"""

import pytest

from teamflow import common

CREDS = {
    "workspaces": {
        "acme": {"api_url": "http://a", "tokens": {"claude": "tf_pat_a"}, "repo_patterns": ["/work/acme", "github.com/acme/*"]},
        "home": {"api_url": "http://h", "tokens": {"claude": "tf_pat_h"}, "repo_patterns": ["~/side/*"]},
        "team": {"api_url": "http://t", "tokens": {"claude": "tf_pat_t"}, "repo_patterns": []},
    },
    "default": "team",
}


@pytest.mark.parametrize(
    "cwd,remote,want",
    [
        ("/work/acme", None, "acme"),
        ("/work/acme/svc/api", None, "acme"),
        ("/work/acmeX", None, "team"),
        ("/elsewhere", "https://github.com/acme/api.git", "acme"),
        ("/elsewhere", "https://github.com/other/api.git", "team"),
        ("/elsewhere", None, "team"),
    ],
)
def test_select(cwd, remote, want):
    assert common.select_workspace(CREDS, cwd, remote)[0] == want


def test_tilde_pattern(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert common.select_workspace(CREDS, str(tmp_path / "side" / "proj"))[0] == "home"


def test_no_default():
    with pytest.raises(common.CredError):
        common.select_workspace({"workspaces": {"a": {}, "b": {}}}, "/x")
    assert common.select_workspace({"workspaces": {"only": {}}}, "/x")[0] == "only"


def test_token_and_api_checks():
    with pytest.raises(common.CredError):
        common.token_for({"tokens": {"claude": "sk-ant-xxx"}}, "claude")
    with pytest.raises(common.CredError):
        common.api_base({"api_url": "file:///etc/passwd"})
    assert common.api_base({"api_url": "http://127.0.0.1:8100/"}) == "http://127.0.0.1:8100"


def test_relative_cred_rejected():
    with pytest.raises(common.CredError):
        common.load_creds("credentials.json")


@pytest.mark.parametrize(
    "remote,norm",
    [
        ("https://u:tok@GitHub.com/acme/api.git", "github.com/acme/api"),
        ("git@github.com:acme/api.git", "github.com/acme/api"),
        ("ssh://git@git.example.com:2222/acme/api", "git.example.com:2222/acme/api"),
        ("github.com:acme/api/", "github.com/acme/api"),
    ],
)
def test_normalize_remote(remote, norm):
    assert common.normalize_remote(remote) == norm
    if norm.startswith("github.com/acme/api"):
        assert common.select_workspace(CREDS, "/elsewhere", remote)[0] == "acme"
