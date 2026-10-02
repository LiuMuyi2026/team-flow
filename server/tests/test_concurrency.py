"""并发认领只有一人成功，失败方被告知"已被谁于几点认领"。"""

from __future__ import annotations

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor

from teamflow_server.errors import DomainError

from .conftest import ALICE, agent, dev_headers, human, vs


def test_threaded_claims_single_winner(svc):
    """32 个线程同时认领同一个待认领任务（人认领 + 发布人的 agent 认领混合）。"""
    a = agent("alice", "claude_code")
    tid = svc.create_task(a, "并发认领")["id"]
    ver = vs(svc, tid)
    barrier = threading.Barrier(32)
    actors = [human("bob") if i % 2 else (human("alice") if i % 4 == 0 else a) for i in range(32)]

    def go(actor):
        barrier.wait()
        try:
            if actor.kind == "human":
                svc.human_claim(actor, tid, **ver)
            else:
                svc.claim_task(actor, tid)
            return ("ok", actor.handle)
        except DomainError as e:
            return (e.code, e.msg)

    with ThreadPoolExecutor(32) as ex:
        results = list(ex.map(go, actors))
    winners = {h for st, h in results if st == "ok"}
    t = svc.tasks[tid]
    assert len(winners) == 1 and t.assignee in winners
    losers = [msg for st, msg in results if st == "taken"]
    assert losers and all(f"已被 {t.assignee} 于" in m for m in losers)
    # 同一个人的重复认领（幂等）不算第二个赢家；其他人一律 taken
    for st, info in results:
        assert st in ("ok", "taken")
    svc._check_task(t)


async def test_http_concurrent_human_claims(client, svc):
    ver = vs(svc, "T-53")

    async def claim(h):
        return await client.post("/api/v1/dev/tasks/T-53:claim", headers=dev_headers(h), json=ver)

    rs = await asyncio.gather(*[claim("alice" if i % 2 else "bob") for i in range(20)])
    codes = sorted(r.status_code for r in rs)
    assert codes.count(200) == 1
    assert codes.count(409) == 19
    winner = svc.tasks["T-53"].assignee
    for r in rs:
        if r.status_code == 409:
            body = r.json()
            assert body["error"] == "taken" and body["by"] == winner and f"已被 {winner} 于" in body["message"]


async def test_http_concurrent_agent_vs_human(client, svc):
    """alice 的 agent 认领自己发布的 T-53，同时 bob 在手机上认领：只有一个成功。"""

    async def agent_claim():
        return await client.post("/api/v1/tasks/T-53:claim", headers={"authorization": f"Bearer {ALICE}"})

    ver = vs(svc, "T-53")

    async def human_claim():
        return await client.post("/api/v1/dev/tasks/T-53:claim", headers=dev_headers("bob"), json=ver)

    rs = await asyncio.gather(*[agent_claim() if i % 2 else human_claim() for i in range(10)])
    ok_handles = set()
    for r in rs:
        if r.status_code == 200:
            ok_handles.add(svc.tasks["T-53"].assignee)
        else:
            assert r.status_code == 409 and r.json()["error"] == "taken"
    assert len(ok_handles) == 1
