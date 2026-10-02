"""spool：幂等、批量上传、退避、dead-letter、锁。"""

import json
import os
import subprocess
import sys
import time

import pytest
from tfhelpers import stdin_for
from tf_stub_server import closed_port_url

from teamflow import spool


def test_same_turn_written_once(env, stub):
    env.write_cred(stub.url)
    payload = stdin_for("codex", "stop", "/tmp")
    for _ in range(3):
        assert env.hook("stop", "codex", payload).returncode == 0
    assert len(env.spool_records()) == 1
    # 另一个回合是新记录
    env.hook("stop", "codex", stdin_for("codex", "stop", "/tmp", turn_id="turn-2"))
    assert len(env.spool_records()) == 2


def test_idem_key_depends_on_all_parts():
    k = spool.idem_key("claude", "s1", "turn_end", "t1")
    assert k == spool.idem_key("claude", "s1", "turn_end", "t1")
    assert len({k, spool.idem_key("codex", "s1", "turn_end", "t1"), spool.idem_key("claude", "s2", "turn_end", "t1"),
                spool.idem_key("claude", "s1", "end", "t1"), spool.idem_key("claude", "s1", "turn_end", "t2")}) == 5


def test_flush_success_then_duplicate_skipped(env, stub):
    env.write_cred(stub.url)
    payload = stdin_for("claude", "stop", "/tmp")
    env.hook("stop", "claude", payload)
    env.hook("session-end", "claude", stdin_for("claude", "session-end", "/tmp"))
    p = env.run(["flush"])
    assert p.returncode == 0, p.stderr
    batches = [r for r in stub.requests if r["path"] == "/api/v1/hooks/batch"]
    assert len(batches) == 1
    b = batches[0]
    assert b["headers"]["Authorization"] == "Bearer tf_pat_claude_x"
    assert b["headers"]["X-Teamflow-Client"] == "claude_code"
    assert b["headers"].get("Idempotency-Key")
    assert {it["type"] for it in b["body"]["items"]} == {"turn_end", "end"}
    assert env.spool_records() == []
    # 已发送过的同一事件再写一次：被 sent 标记挡住
    env.hook("stop", "claude", payload)
    assert env.spool_records() == []


def test_flush_4xx_item_goes_dead_letter(env, stub):
    env.write_cred(stub.url)
    env.hook("stop", "codex", stdin_for("codex", "stop", "/tmp"))
    key = env.spool_records()[0]["key"]
    stub.item_status[key] = 422
    env.run(["flush"])
    assert env.spool_records() == []
    assert env.dead_records() == [key + ".json"]
    assert "dead-letter" in env.log_text()


def test_flush_whole_batch_4xx_dead_letter(env, stub):
    env.write_cred(stub.url)
    env.hook("stop", "codex", stdin_for("codex", "stop", "/tmp"))
    stub.status["/api/v1/hooks/batch"] = 401
    env.run(["flush"])
    assert env.spool_records() == [] and len(env.dead_records()) == 1


@pytest.mark.parametrize("mode", ["503", "429", "net"])
def test_flush_retryable_backoff(env, stub, mode):
    if mode == "net":
        env.write_cred(closed_port_url())
    else:
        env.write_cred(stub.url)
        stub.status["/api/v1/hooks/batch"] = int(mode)
    env.hook("stop", "codex", stdin_for("codex", "stop", "/tmp"))
    before = time.time()
    env.run(["flush"])
    recs = env.spool_records()
    assert len(recs) == 1 and env.dead_records() == []
    assert recs[0]["attempts"] == 1
    assert recs[0]["next_try"] >= before + spool.BACKOFF_MIN
    # 还没到 next_try：再 flush 不会重发
    n = len(stub.requests)
    env.run(["flush"])
    assert len(stub.requests) == n
    assert env.spool_records()[0]["attempts"] == 1


def test_backoff_schedule(env, tmp_path):
    path = str(tmp_path / "r.json")
    rec = {"key": "k", "attempts": 0}
    delays = []
    for _ in range(9):
        now = 1000.0
        spool._retry(path, rec, now, "x")
        delays.append(rec["next_try"] - now)
    assert delays[:7] == [5, 10, 20, 40, 80, 160, 300]
    assert max(delays) == 300


def test_flush_retries_within_call_when_budget_allows(env, stub, monkeypatch):
    """预算内会在本次调用里等到 next_try 再试（有限次）。"""
    env.write_cred(stub.url)
    env.hook("stop", "codex", stdin_for("codex", "stop", "/tmp"))
    stub.status["/api/v1/hooks/batch"] = 503
    monkeypatch.setattr(spool, "BACKOFF_MIN", 0.05)
    sleeps = []
    real_sleep = time.sleep

    def rec_sleep(s):
        sleeps.append(s)
        real_sleep(s)

    monkeypatch.setattr(spool.time, "sleep", rec_sleep)
    res = spool.flush(budget=10, max_retries=3)
    assert res["pending"] == 1
    assert len([r for r in stub.requests if r["path"] == "/api/v1/hooks/batch"]) == 4  # 1 次 + 3 次重试
    assert len(sleeps) == 3


def test_expired_heartbeat_dropped(env, stub):
    env.write_cred(stub.url)
    env.hook("session-end", "codex", stdin_for("codex", "session-end", "/tmp"))
    rec = env.spool_records()[0]
    rec["created"] = time.time() - 25 * 3600
    path = os.path.join(env.state, "spool", rec["key"] + ".json")
    json.dump(rec, open(path, "w"))
    env.run(["flush"])
    assert env.spool_records() == [] and stub.requests == []


def test_lock_held_by_live_process(env, stub):
    env.write_cred(stub.url)
    env.hook("stop", "codex", stdin_for("codex", "stop", "/tmp"))
    d = spool.spool_dir()
    holder = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        with open(os.path.join(d, ".lock"), "w") as f:
            f.write("%d %d" % (holder.pid, int(time.time())))
        t = time.time()
        res = spool.flush(budget=0)
        assert res == {"locked": True}
        assert time.time() - t < 5
        assert stub.requests == []
    finally:
        holder.kill()
        holder.wait()
    # 持锁进程已退出：锁被判定为过期，可以接手
    res = spool.flush(budget=0)
    assert res["locked"] is False and res["pending"] == 0


def test_refresh_writes_cache_and_uses_etag(env, stub):
    env.write_cred(stub.url)
    p = env.run(["flush", "--refresh", "--client", "codex", "--cred", env.cred])
    assert p.returncode == 0, p.stderr
    cache = json.load(open(os.path.join(env.state, "cache", "team", "codex.json")))
    assert cache["data"]["me"] == "zhao" and cache["cursor"] == "c1"
    first = cache["fetched_at"]
    time.sleep(0.01)
    env.run(["flush", "--refresh", "--client", "codex", "--cred", env.cred])
    delta = [r for r in stub.requests if r["path"] == "/api/v1/me/delta"]
    assert delta[1]["headers"].get("If-None-Match") == stub.etag
    assert "cursor=c1" in delta[1]["full"]
    cache2 = json.load(open(os.path.join(env.state, "cache", "team", "codex.json")))
    assert cache2["fetched_at"] > first and cache2["data"] == cache["data"]


# --- 第三轮复审：一批超过服务端 64KB 上限时整批 413、全进 dead/ ---

def _big_records(n, title_chars, commits=2):
    """直接写 n 条带长提交标题的 turn_end 记录（结构同 hooks.py 的 turn_end 条目）。"""
    keys = []
    for i in range(n):
        key = spool.idem_key("claude", "s-big", "turn_end", str(i))
        item = {"type": "turn_end", "key": key, "session_id": "s-big", "client": "claude_code", "ts": int(time.time()),
                "turn": str(i), "cwd_name": "team-flow", "repo": "github.com/acme/team-flow", "branch": "main",
                "head": "%040x" % i, "own_more": 0, "other_commits": 0,
                "commits": [{"sha": "%040x" % (i * 10 + j), "title": "修" * title_chars} for j in range(commits)]}
        assert spool.write({"key": key, "kind": "commit", "created": time.time(), "attempts": 0, "next_try": 0,
                            "cred": None, "ws": "team", "client": "claude", "item": item})
        keys.append(key)
    return keys


def _fix_cred(env, path):
    d = os.path.join(env.state, "spool")
    for n in os.listdir(d):
        if n.endswith(".json"):
            p = os.path.join(d, n)
            rec = json.load(open(p))
            rec["cred"] = path
            json.dump(rec, open(p, "w"))


def test_flush_splits_batches_by_bytes_under_server_limit(env, stub):
    cred = env.write_cred(stub.url)
    stub.max_body = 64 * 1024
    keys = _big_records(100, 150)  # 每条约 1KB+，100 条约 100KB：按条数切只有 1 批，必然 413
    _fix_cred(env, cred)
    p = env.run(["flush"])
    assert p.returncode == 0, p.stderr
    batches = [r for r in stub.requests if r["path"] == "/api/v1/hooks/batch"]
    assert len(batches) >= 2
    assert all(int(r["headers"]["Content-Length"]) <= spool.BATCH_BYTES + 64 for r in batches)
    sent = [it["key"] for r in batches for it in r["body"]["items"]]
    assert sorted(sent) == sorted(keys)
    assert env.spool_records() == [] and env.dead_records() == []


def test_flush_413_halves_and_dead_letters_only_oversized_item(env, stub):
    cred = env.write_cred(stub.url)
    stub.max_body = 6 * 1024  # 服务端上限比 CLI 估的小：靠 413 对半拆开
    small = _big_records(8, 100, commits=1)  # 每条约 0.5KB
    big = spool.idem_key("claude", "s-big", "turn_end", "huge")
    item = {"type": "turn_end", "key": big, "session_id": "s-big", "client": "claude_code", "ts": int(time.time()),
            "turn": "huge", "commits": [{"sha": "%040x" % j, "title": "长" * 800} for j in range(5)]}  # 约 12KB
    spool.write({"key": big, "kind": "commit", "created": time.time(), "attempts": 0, "next_try": 0, "cred": None,
                 "ws": "team", "client": "claude", "item": item})
    _fix_cred(env, cred)
    env.run(["flush"])
    batches = [r for r in stub.requests if r["path"] == "/api/v1/hooks/batch"]
    rejected = [r for r in batches if int(r["headers"]["Content-Length"]) > stub.max_body]
    ok = [it["key"] for r in batches if r not in rejected for it in r["body"]["items"]]
    assert any(len(r["body"]["items"]) > 1 for r in rejected)  # 确实有多条的批被 413，走到了对半拆开
    assert set(small) <= set(ok)  # 小条目最终都送达
    assert env.dead_records() == [big + ".json"]  # 只有单条就超限的那条进 dead/
    assert env.spool_records() == []


def test_chunks_respects_count_and_bytes():
    entries = [("p%d" % i, {"item": {"k": "x" * 100}}) for i in range(250)]
    by_count = spool._chunks(entries, max_items=100, max_bytes=10**9)
    assert [len(c) for c in by_count] == [100, 100, 50]
    by_bytes = spool._chunks(entries, max_items=100, max_bytes=1100)
    assert all(len(c) <= 10 for c in by_bytes) and sum(len(c) for c in by_bytes) == 250
    assert spool._chunks([("p", {"item": {"k": "x" * 5000}})], max_bytes=1000) == [[("p", {"item": {"k": "x" * 5000}})]]


# ---------------------------------------------------------------- 同一会话按写入顺序上报（D40 验证阶段发现）


def _set(env, key, **fields):
    path = os.path.join(env.state, "spool", key + ".json")
    rec = json.load(open(path))
    rec.update(fields)
    json.dump(rec, open(path, "w"))


def _batches(stub):
    return [[it["type"] for it in r["body"]["items"]] for r in stub.requests if r["path"] == "/api/v1/hooks/batch"]


def test_end_waits_for_same_session_tool_map_in_backoff(env, stub):
    """Stop 那一轮没连上、tool_map 在退避时，SessionEnd 的 end 不能先单独送到：否则服务端把迟到的
    tool_map 判成"会话已结束"（403 ignored），映射丢了还进 dead-letter。end 要等它到期、一起发。"""
    env.write_cred(stub.url)
    env.hook("tool", "claude", stdin_for("claude", "tool", "/tmp"))
    env.hook("stop", "claude", stdin_for("claude", "stop", "/tmp"))
    age = {"tool_map": 6, "turn_end": 5}
    for r in env.spool_records():
        _set(env, r["key"], attempts=1, next_try=time.time() + 60, created=time.time() - age[r["item"]["type"]])
    env.hook("session-end", "claude", stdin_for("claude", "session-end", "/tmp"))
    env.run(["flush"])
    assert _batches(stub) == []  # end 被同会话退避中的记录压住
    assert sorted(r["item"]["type"] for r in env.spool_records()) == ["end", "tool_map", "turn_end"]
    for r in env.spool_records():
        if r["item"]["type"] != "end":
            _set(env, r["key"], next_try=0)
    env.run(["flush"])
    assert _batches(stub) == [["tool_map", "turn_end", "end"]]  # 同一批，按写入顺序
    assert env.spool_records() == [] and env.dead_records() == []


def test_other_sessions_not_held_back(env, stub):
    env.write_cred(stub.url)
    env.hook("tool", "claude", stdin_for("claude", "tool", "/tmp"))
    _set(env, env.spool_records()[0]["key"], attempts=1, next_try=time.time() + 60)
    other = "11111111-2222-4333-8444-555555555555"
    env.hook("session-end", "claude", stdin_for("claude", "session-end", "/tmp", session_id=other))
    env.run(["flush"])
    assert _batches(stub) == [["end"]]
    assert [r["item"]["type"] for r in env.spool_records()] == ["tool_map"]


def test_older_due_record_still_sent_while_newer_one_backs_off(env, stub):
    """只压住比退避中那条更晚写的；更早写、已到期的照常发。"""
    env.write_cred(stub.url)
    env.hook("tool", "claude", stdin_for("claude", "tool", "/tmp"))
    env.hook("stop", "claude", stdin_for("claude", "stop", "/tmp"))
    by_type = {r["item"]["type"]: r for r in env.spool_records()}
    _set(env, by_type["tool_map"]["key"], created=time.time() - 10)
    _set(env, by_type["turn_end"]["key"], created=time.time() - 5, attempts=1, next_try=time.time() + 60)
    env.run(["flush"])
    assert _batches(stub) == [["tool_map"]]


def test_flush_waits_for_blocking_record_within_budget(env, stub, monkeypatch):
    """预算内会等压住 end 的那条退避到期，然后两条一起发，不白白空转几轮就退出。"""
    env.write_cred(stub.url)
    env.hook("tool", "claude", stdin_for("claude", "tool", "/tmp"))
    _set(env, env.spool_records()[0]["key"], attempts=1, next_try=time.time() + 0.3, created=time.time() - 5)
    env.hook("session-end", "claude", stdin_for("claude", "session-end", "/tmp"))
    res = spool.flush(budget=5, max_retries=3)
    assert res["pending"] == 0 and res["dead"] == 0
    assert _batches(stub) == [["tool_map", "end"]]
