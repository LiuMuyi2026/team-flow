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
