"""hooks 接口：session-start 结构化返回、batch 去重/上限/遮蔽、delta 游标与 ETag、故障注入。"""

from __future__ import annotations

import json
import re
import time

from .conftest import ALICE, BOB, BOB_CX2, auth, dev_headers, read_log

SESSION_START_KEYS = {"v", "me", "doing", "todo", "to_accept", "help_me", "fwd", "proposed", "pool_new", "repo_hint", "cursor"}
ID = re.compile(r"^[TB]-\d{1,6}$")
HANDLE = re.compile(r"^[a-z][a-z0-9_]{1,15}$")
CLIENTS = {"claude_code", "codex", "cli", None}


def assert_structured_only(data):
    """H5：只有 ID、计数、handle、枚举值——不返回任何标题或成段文字。"""
    assert set(data) == SESSION_START_KEYS
    assert data["v"] == 1 and HANDLE.match(data["me"])
    for k in ("doing", "todo", "repo_hint"):
        assert all(ID.match(x) for x in data[k])
    for row in data["to_accept"]:
        assert set(row) == {"id", "by", "bk", "client"}
        assert ID.match(row["id"]) and HANDLE.match(row["by"]) and row["bk"] in ("human", "agent") and row["client"] in CLIENTS
    for row in data["help_me"]:
        assert ID.match(row["id"]) and HANDLE.match(row["by"])
    for row in data["fwd"]:
        assert ID.match(row["id"]) and isinstance(row["n"], int) and HANDLE.match(row["by"])
    for row in data["proposed"]:
        assert set(row) == {"id", "h", "client"} and ID.match(row["id"]) and HANDLE.match(row["h"]) and row["client"] in CLIENTS
    assert isinstance(data["pool_new"], int) and isinstance(data["cursor"], int)
    blob = json.dumps(data, ensure_ascii=False)
    assert not re.search(r"[一-鿿]", blob)  # 没有任何中文自由文本


async def test_session_start_structured(client, svc):
    r = await client.post(
        "/api/v1/hooks/session-start",
        headers=auth(BOB),
        json={"client": "codex", "session_id": "019a-thread", "source": "startup", "repo": "github.com/acme/payment-svc", "branch": "main", "interactive": True},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert_structured_only(data)
    assert data["me"] == "bob"
    assert data["to_accept"] == [{"id": "T-52", "by": "alice", "bk": "agent", "client": "claude_code"}]
    assert data["doing"] == ["T-49"]
    assert data["pool_new"] == 1  # T-53 是 alice 发布的；T-51 是 bob 自己发布的不算
    assert ("codex", "019a-thread") in svc.sessions
    # 第二次：已看过的待认领不再算新的
    r = await client.post("/api/v1/hooks/session-start", headers=auth(BOB), json={"client": "codex", "session": "019a-thread"})
    assert r.json()["pool_new"] == 0


async def test_session_start_alice_and_repo_hint(client):
    r = await client.post(
        "/api/v1/hooks/session-start",
        headers=auth(ALICE),
        json={"client": "claude", "session": "c0ffee", "repo": "github.com/acme/team-flow", "branch": "feat/x"},
    )
    data = r.json()
    assert_structured_only(data)
    assert data["help_me"] == [{"id": "B-7", "by": "bob"}]
    assert data["fwd"] == [{"id": "B-7", "n": 1, "by": "bob"}]
    assert data["repo_hint"] == ["T-50"]


async def test_session_hijack_ignored(client, svc):
    await client.post("/api/v1/hooks/session-start", headers=auth(BOB), json={"client": "codex", "session": "shared"})
    # 另一枚同 client 的 token（bob 的第二台机器）拿同一个会话 ID：忽略并写审计
    await client.post("/api/v1/hooks/session-start", headers=auth(BOB_CX2), json={"client": "codex", "session": "shared", "repo": "evil"})
    s = svc.sessions[("codex", "shared")]
    assert s.handle == "bob" and s.repo is None
    assert svc.audit[-1]["action"] == "session.token_mismatch"
    # 别的 client 的 token 自称 codex：client 强制取 token 的 client，碰不到 codex 那条会话
    await client.post("/api/v1/hooks/session-start", headers=auth(ALICE), json={"client": "codex", "session": "shared", "repo": "evil2"})
    assert svc.sessions[("codex", "shared")].repo is None
    assert svc.sessions[("claude_code", "shared")].handle == "alice"


async def test_batch_dedupe_mask_and_limits(client, svc):
    items = [
        {"key": "k1", "type": "turn_end", "client": "codex", "session_id": "s1", "ts": 1, "repo": "github.com/acme/x", "branch": "main",
         "commits": [{"sha": "abc1234", "title": "修复登录，联系 13912345678"}], "other_commits": 2},
        {"key": "k2", "type": "commit", "client": "codex", "session_id": "s1", "repo": "github.com/acme/x", "sha": "def5678", "title": "加重试"},
        {"key": "k3", "type": "nope"},
        {"type": "turn_end"},
        {"key": "k4", "type": "end", "client": "codex", "session_id": "s1", "reason": "logout"},
        {"k": "k5", "ev": "turn_end", "session": "s2"},  # 旧写法也接受
    ]
    r = await client.post("/api/v1/hooks/batch", headers=auth(BOB), json={"v": 1, "items": items})
    assert r.status_code == 200
    res = r.json()["results"]
    assert [x["st"] for x in res] == ["masked", "ok", "bad", "bad", "ok", "ok"]
    assert [x["status"] for x in res] == [200, 200, 422, 422, 200, 200]
    assert [x["key"] for x in res] == ["k1", "k2", "k3", None, "k4", "k5"]
    commits = {e.data["sha"]: e.text for e in svc.events if e.type == "commit"}
    assert "13912345678" not in commits["abc1234"] and "[已遮蔽:cn_mobile]" in commits["abc1234"]
    assert commits["def5678"] == "加重试"
    assert svc.sessions[("codex", "s1")].ended_at is not None
    r = await client.post("/api/v1/hooks/batch", headers=auth(BOB), json={"items": items[:2]})
    assert [(x["st"], x["status"]) for x in r.json()["results"]] == [("dup", 409), ("dup", 409)]
    # start 会把结束过的会话重新打开
    await client.post("/api/v1/hooks/batch", headers=auth(BOB), json={"items": [{"key": "k6", "type": "start", "session_id": "s1", "client": "codex"}]})
    assert svc.sessions[("codex", "s1")].ended_at is None
    r = await client.post("/api/v1/hooks/batch", headers=auth(BOB), json={"items": [{"key": f"x{i}", "type": "turn_end"} for i in range(101)]})
    assert r.status_code == 413 and r.json()["error"] == "too_many"


async def test_delta_cursor_and_etag(client):
    r = await client.post("/api/v1/hooks/session-start", headers=auth(BOB), json={"client": "codex", "session_id": "th-1"})
    cur0 = r.json()["cursor"]
    r = await client.get("/api/v1/me/delta", headers=auth(BOB), params={"cursor": 0})
    data = r.json()
    assert r.status_code == 200 and data["items"]
    assert all(set(i) == {"e", "ty", "id", "by", "bk", "client"} for i in data["items"])
    # delta 带与 session-start 同形的快照（CLI 用同一个校验函数）
    assert data["to_accept"] == [{"id": "T-52", "by": "alice", "bk": "agent", "client": "claude_code"}]
    assert data["cursor"] == cur0
    etag = r.headers["etag"]
    cur = data["cursor"]
    r = await client.get("/api/v1/me/delta", headers={**auth(BOB), "if-none-match": etag}, params={"cursor": cur})
    assert r.status_code == 304
    # alice 在 bob 的任务上评论 → bob 的增量里出现
    await client.post("/api/v1/tasks/T-49/comments", headers=auth(ALICE), json={"body": "我来看看安全组"})
    r = await client.get("/api/v1/me/delta", headers={**auth(BOB), "if-none-match": etag}, params={"cursor": cur})
    assert r.status_code == 200
    items = r.json()["items"]
    assert items[-1]["ty"] == "comment" and items[-1]["id"] == "T-49" and items[-1]["by"] == "alice" and items[-1]["bk"] == "agent"
    assert r.headers["etag"] != etag


async def test_fault_delay(client, monkeypatch, log_path):
    monkeypatch.setenv("TEAMFLOW_FAULT_DELAY_MS", "300")
    t0 = time.perf_counter()
    r = await client.get("/api/v1/me/inbox", headers=auth(ALICE))
    assert r.status_code == 200 and time.perf_counter() - t0 >= 0.3
    t0 = time.perf_counter()
    r = await client.post("/api/v1/hooks/session-start", headers=auth(ALICE), json={"client": "claude", "session": "x"})
    assert r.status_code == 200 and time.perf_counter() - t0 >= 0.3
    # 其他路径不受影响
    t0 = time.perf_counter()
    await client.get("/healthz")
    assert time.perf_counter() - t0 < 0.3
    assert read_log(log_path)[-2]["fault_delay_ms"] == 300


async def test_log_has_session_header_and_handle(client, log_path):
    await client.get("/api/v1/me/inbox", headers={**auth(ALICE), "x-teamflow-session": "cc-sess-1", "x-teamflow-client": "claude_code"})
    rec = read_log(log_path)[-1]
    assert rec["sess"] == "cc-sess-1" and rec["h"] == "alice" and rec["st"] == 200 and rec["path"] == "/api/v1/me/inbox"


async def test_dev_outbox_lists_simulated_notifications(client):
    r = await client.get("/api/v1/dev/outbox", headers=dev_headers("alice"), params={"to": "bob"})
    texts = [x["text"] for x in r.json()["items"]]
    assert "alice 的 Claude Code 请您协作（T-52）" in texts


async def test_commits_without_repo_are_reported_not_silently_dropped(client, svc):
    """本地试用：演示仓库没有 origin 时，turn_end 里的提交被悄悄丢掉、还返回 200 ok。
    现在会话照常登记，提交不记，逐条结果是 200 st=no_repo 加 dropped，CLI 据此报出来。"""
    sha = "ab" * 20
    items = [
        {"key": "nr1", "type": "turn_end", "client": "claude", "session_id": "nr-s", "ts": 1,
         "commits": [{"sha": sha, "title": "接口联调"}, {"sha": "cd" * 20, "title": "补测试"}]},
        {"key": "nr2", "type": "turn_end", "client": "claude", "session_id": "nr-s", "ts": 2},  # 没有提交的心跳不受影响
        {"key": "nr3", "type": "turn_end", "client": "claude", "session_id": "nr-s", "ts": 3, "repo": "example.com/demo/tf-demo.git",
         "commits": [{"sha": "ef" * 32, "title": "SHA-256 仓库的提交"}]},
        {"key": "nr4", "type": "commit", "client": "claude", "session_id": "nr-s", "sha": sha, "title": "旧写法"},
    ]
    r = await client.post("/api/v1/hooks/batch", headers=auth(ALICE), json={"v": 1, "items": items})
    res = r.json()["results"]
    assert res[0] == {"key": "nr1", "status": 200, "st": "no_repo", "dropped": 2}
    assert res[1] == {"key": "nr2", "status": 200, "st": "ok"}
    assert res[2] == {"key": "nr3", "status": 200, "st": "ok"}
    assert res[3]["status"] == 422 and res[3]["err"] == "repo"
    assert svc.sessions[("claude_code", "nr-s")].handle == "alice"  # 会话照常登记
    commits = {e.data["sha"] for e in svc.events if e.type == "commit"}
    assert sha not in commits and "ef" * 32 in commits
    assert [a for a in svc.audit if a["action"] == "hook.commits_no_repo"][-1]["n"] == 2


async def test_no_repo_survives_a_lost_response_and_counts_own_more(client, svc):
    """红队：第一次的响应在路上丢了，CLI 重试拿到 409 dup，原来结果里没有 no_repo，提醒又被悄悄吞掉。
    现在重放时带回 was=no_repo 和 dropped；本人超过 5 条的提交（own_more）同样没记，一并算进 dropped。"""
    commits = [{"sha": ("%02x" % i) * 20, "title": "提交 %d" % i} for i in range(5)]
    item = {"key": "lost1", "type": "turn_end", "client": "claude", "session_id": "nr-lost", "ts": 1,
            "commits": commits, "own_more": 3}
    body = {"v": 1, "items": [item]}
    first = (await client.post("/api/v1/hooks/batch", headers=auth(ALICE), json=body)).json()["results"][0]
    assert first == {"key": "lost1", "status": 200, "st": "no_repo", "dropped": 8}
    again = (await client.post("/api/v1/hooks/batch", headers=auth(ALICE), json=body)).json()["results"][0]
    assert again == {"key": "lost1", "status": 409, "st": "dup", "was": "no_repo", "dropped": 8}
    # 带着仓库地址记下的条目，重放时只是 dup，不带 was
    ok = {**item, "key": "lost2", "repo": "example.com/demo/tf-demo.git"}
    await client.post("/api/v1/hooks/batch", headers=auth(ALICE), json={"v": 1, "items": [ok]})
    dup = (await client.post("/api/v1/hooks/batch", headers=auth(ALICE), json={"v": 1, "items": [ok]})).json()["results"][0]
    assert dup == {"key": "lost2", "status": 409, "st": "dup"}
    # own_more 超出范围的不算
    bad = {**item, "key": "lost3", "own_more": 10**6}
    r = (await client.post("/api/v1/hooks/batch", headers=auth(ALICE), json={"v": 1, "items": [bad]})).json()["results"][0]
    assert r["dropped"] == 5
