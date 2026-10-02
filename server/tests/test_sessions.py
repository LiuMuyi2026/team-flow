"""I2：会话归属不能伪造（plan 6.5、H7）。

统一的 resolve_session：会话存在、未结束、token_id 与当前 token 相同、client 与 token 的 client 相同，
才算精确归属；否则降为成员级并写审计。hooks batch 条目 token 不符整条忽略，条目 client 强制取 token 的。
"""

from __future__ import annotations

import pytest

from .conftest import ALICE, ALICE2, BOB, BOB_CC, BOB_CX2, LegacyMcp, ModernMcp, auth, human, vs

CODEX_TURN = "x-codex-turn-metadata"


async def _start_session(client, token: str, sid: str, client_name: str = "claude") -> None:
    r = await client.post("/api/v1/hooks/session-start", headers=auth(token), json={"client": client_name, "session_id": sid})
    assert r.status_code == 200, r.text


def _last_resolve_audit(svc):
    rows = [a for a in svc.audit if a["action"] == "session.resolve"]
    return rows[-1] if rows else None


# ---- resolve_session 本身 ----


def test_resolve_session_reasons(svc):
    from teamflow_server.service import Actor

    alice = Actor("alice", "agent", "claude_code", "tok_a1", "hook")
    svc.hook_session_start(alice, {"session_id": "c-1"})
    assert svc.resolve_session("alice", "claude_code", "tok_a1", "c-1", source="header").external_id == "c-1"
    cases = [
        (("alice", "claude_code", "tok_a1", "nope"), "unknown"),
        (("alice", "claude_code", "tok_a2", "c-1"), "token_mismatch"),  # 同一个人的另一枚 token
        (("alice", "claude_code", None, "c-1"), "token_mismatch"),
        (("alice", "codex", "tok_a1", "c-1"), "unknown"),  # client 是主键的一部分
    ]
    for args, reason in cases:
        assert svc.resolve_session(*args, source="header") is None
        a = _last_resolve_audit(svc)
        assert a["reason"] == reason and a["result"] == "member" and a["source"] == "header"
    # 会话记录被篡改成别的 client（防御）：client_mismatch
    svc.sessions[("claude_code", "c-1")].client = "codex"
    assert svc.resolve_session("alice", "claude_code", "tok_a1", "c-1", source="header") is None
    assert _last_resolve_audit(svc)["reason"] == "client_mismatch"
    svc.sessions[("claude_code", "c-1")].client = "claude_code"
    # 结束之后不再 exact
    svc.hook_batch(alice, [{"key": "e1", "type": "end", "session_id": "c-1"}])
    assert svc.resolve_session("alice", "claude_code", "tok_a1", "c-1", source="header") is None
    assert _last_resolve_audit(svc)["reason"] == "ended"


# ---- X-Teamflow-Session 请求头（REST 与 MCP）----


async def test_rest_session_header_needs_same_token(client, svc):
    await _start_session(client, ALICE, "c-1")
    # alice 的第二枚 token 借用第一枚 token 登记的会话去认领：成功，但只是成员级，不设 current_task
    r = await client.post("/api/v1/tasks/T-53:claim", headers={**auth(ALICE2), "x-teamflow-session": "c-1"})
    assert r.status_code == 200 and r.json()["st"] == "doing"
    started = [e for e in svc.events if e.type == "task.started" and e.subject == "T-53"][-1]
    assert started.session is None
    assert svc.sessions[("claude_code", "c-1")].current_task is None
    assert _last_resolve_audit(svc)["reason"] == "token_mismatch"
    # 登记它的 token 自己用：exact，并设置 current_task
    await client.post("/api/v1/tasks/T-53:release", headers={**auth(ALICE2)}, json={"note": "交回去"})
    r = await client.post("/api/v1/tasks/T-53:claim", headers={**auth(ALICE), "x-teamflow-session": "c-1"})
    assert r.status_code == 200
    started = [e for e in svc.events if e.type == "task.started" and e.subject == "T-53"][-1]
    assert started.session == "c-1"
    assert svc.sessions[("claude_code", "c-1")].current_task == "T-53"


async def test_rest_session_header_other_member_or_client(client, svc):
    await _start_session(client, ALICE, "c-1")
    # bob 的 Claude Code token 带 alice 的会话头
    r = await client.post("/api/v1/tasks/T-49/comments", headers={**auth(BOB_CC), "x-teamflow-session": "c-1"}, json={"body": "我看看"})
    assert r.status_code == 201
    assert svc.events[-1].session is None and _last_resolve_audit(svc)["reason"] == "token_mismatch"
    # bob 的 Codex token 带 claude 会话的 ID：client 不同，查不到
    r = await client.post("/api/v1/tasks/T-49/comments", headers={**auth(BOB), "x-teamflow-session": "c-1"}, json={"body": "我也看看"})
    assert r.status_code == 201
    assert svc.events[-1].session is None and _last_resolve_audit(svc)["reason"] == "unknown"


async def test_rest_session_header_ended_session_is_member(client, svc):
    await _start_session(client, ALICE, "c-1")
    r = await client.post("/api/v1/hooks/batch", headers=auth(ALICE), json={"items": [{"key": "e1", "type": "end", "session_id": "c-1"}]})
    assert r.json()["results"][0]["st"] == "ok"
    await client.post("/api/v1/tasks/T-50/comments", headers={**auth(ALICE), "x-teamflow-session": "c-1"}, json={"body": "收尾"})
    assert svc.events[-1].session is None and _last_resolve_audit(svc)["reason"] == "ended"


@pytest.mark.parametrize("era", ["legacy", "modern"])
async def test_mcp_session_header_needs_same_token(client, svc, era):
    await _start_session(client, ALICE, "c-1")
    extra = {"x-teamflow-session": "c-1"}
    for token, expect in ((ALICE2, None), (ALICE, "c-1")):
        m = LegacyMcp(client, token, extra=extra) if era == "legacy" else ModernMcp(client, token, extra=extra)
        if era == "legacy":
            await m.initialize()
        res = await m.call("comment", {"target": "T-50", "body": f"{era} 进度 {token[-3:]}"})
        assert res["isError"] is False
        assert svc.events[-1].session == expect


# ---- Codex：_meta.x-codex-turn-metadata ----


async def test_codex_meta_cannot_borrow_someone_elses_session(client, svc):
    await _start_session(client, BOB, "019a-sess", "codex")
    turn = {"session_id": "019a-sess", "thread_id": "019a-sub", "turn_id": "t1"}
    # alice 的 Claude token 带上 bob 的 Codex 会话：成员级
    m = ModernMcp(client, ALICE)
    res = await m.call("report_blocker", {"title": "缺一个控制台权限"}, meta={CODEX_TURN: turn})
    assert res["isError"] is False
    raised = [e for e in svc.events if e.type == "blocker.raised"][-1]
    assert raised.actor == "alice" and raised.session is None
    # bob 的第二枚 Codex token 也不行
    m2 = ModernMcp(client, BOB_CX2)
    await m2.call("comment", {"target": "T-49", "body": "第二台机器上的进度"}, meta={CODEX_TURN: turn})
    assert svc.events[-1].session is None and _last_resolve_audit(svc)["reason"] == "token_mismatch"
    # 登记它的 token：exact；子线程只记录
    m3 = ModernMcp(client, BOB)
    await m3.call("comment", {"target": "T-49", "body": "主会话的进度"}, meta={CODEX_TURN: turn})
    assert svc.events[-1].session == "019a-sess" and svc.events[-1].thread == "019a-sub"


async def test_codex_meta_as_json_string_and_claim_sets_current_task(client, svc):
    import json

    await _start_session(client, BOB, "019a-sess", "codex")
    m = ModernMcp(client, BOB)
    meta = {CODEX_TURN: json.dumps({"session_id": "019a-sess", "thread_id": "019a-sess", "turn_id": "t1", "repo_root": "/secret"})}
    svc.human_claim(human("bob"), "T-53", **vs(svc, "T-53"))
    res = await m.call("claim_task", {"id": "T-53"}, meta=meta)
    assert res["isError"] is False and res["structuredContent"]["st"] == "doing"
    assert svc.sessions[("codex", "019a-sess")].current_task == "T-53"


# ---- hooks batch ----


async def test_batch_end_from_other_token_is_ignored(client, svc):
    """bob 的 token 不能结束 alice 的会话，也不能清它的 current_task（原来 end 条目会无条件清）。"""
    await _start_session(client, ALICE, "c-1")
    await client.post("/api/v1/tasks/T-53:claim", headers={**auth(ALICE), "x-teamflow-session": "c-1"})
    assert svc.sessions[("claude_code", "c-1")].current_task == "T-53"
    items = [
        {"key": "x1", "type": "end", "client": "claude", "session_id": "c-1", "reason": "logout"},
        {"key": "x2", "type": "turn_end", "client": "claude", "session_id": "c-1", "repo": "github.com/acme/x",
         "commits": [{"sha": "abc1234", "title": "伪造的提交"}]},
    ]
    r = await client.post("/api/v1/hooks/batch", headers=auth(BOB_CC), json={"items": items})
    assert r.status_code == 200
    assert [(x["st"], x["status"], x.get("err")) for x in r.json()["results"]] == [("ignored", 403, "session")] * 2
    s = svc.sessions[("claude_code", "c-1")]
    assert s.current_task == "T-53" and s.ended_at is None and s.handle == "alice"
    assert not [e for e in svc.events if e.type == "commit" and e.data.get("sha") == "abc1234"]
    assert [a for a in svc.audit if a["action"] == "session.token_mismatch"]
    # 同一个人的第二枚 token 也不行
    r = await client.post("/api/v1/hooks/batch", headers=auth(ALICE2), json={"items": [{"key": "y1", "type": "end", "session_id": "c-1"}]})
    assert r.json()["results"][0]["st"] == "ignored"
    assert svc.sessions[("claude_code", "c-1")].current_task == "T-53"
    # 登记它的 token 自己结束：清 current_task
    r = await client.post("/api/v1/hooks/batch", headers=auth(ALICE), json={"items": [{"key": "z1", "type": "end", "session_id": "c-1"}]})
    assert r.json()["results"][0]["st"] == "ok"
    assert svc.sessions[("claude_code", "c-1")].current_task is None


async def test_batch_item_client_forced_to_token_client(client, svc):
    await _start_session(client, BOB, "shared", "codex")
    svc.sessions[("codex", "shared")].current_task = "T-49"
    # alice 的 Claude token 自称 codex 去结束 bob 的 codex 会话：client 强制成 claude_code，碰不到 bob 的会话
    r = await client.post(
        "/api/v1/hooks/batch",
        headers=auth(ALICE),
        json={"items": [{"key": "k1", "type": "end", "client": "codex", "session_id": "shared"}]},
    )
    assert r.json()["results"][0]["st"] == "ok"
    bob_s = svc.sessions[("codex", "shared")]
    assert bob_s.ended_at is None and bob_s.current_task == "T-49"
    assert svc.sessions[("claude_code", "shared")].handle == "alice"
    assert [a for a in svc.audit if a["action"] == "hook.client_mismatch" and a["claimed"] == "codex"]
    # session-start 同样强制
    await client.post("/api/v1/hooks/session-start", headers=auth(BOB), json={"client": "claude", "session_id": "only-codex"})
    assert ("codex", "only-codex") in svc.sessions and ("claude_code", "only-codex") not in svc.sessions


async def test_reads_do_not_resolve_sessions(client, svc):
    """读接口不产生事件，不做会话归属，也就不会每次读都写一条审计（CLI 每轮提问都会读增量）。"""
    hdr = {**auth(ALICE), "x-teamflow-session": "never-registered"}
    for path in ("/api/v1/me/inbox", "/api/v1/me/delta", "/api/v1/tasks", "/api/v1/tasks/T-50", "/api/v1/blockers/B-7", "/api/v1/status"):
        r = await client.get(path, headers=hdr)
        assert r.status_code == 200, (path, r.text)
    m = ModernMcp(client, BOB, extra={"x-teamflow-session": "never-registered"})
    await m.call("inbox", {}, meta={CODEX_TURN: {"session_id": "never-registered"}})
    await m.call("get_item", {"id": "T-49"}, meta={CODEX_TURN: {"session_id": "never-registered"}})
    assert _last_resolve_audit(svc) is None
    # 写接口才归属：降为成员级并写审计
    await client.post("/api/v1/tasks/T-50/comments", headers=hdr, json={"body": "写一条"})
    assert _last_resolve_audit(svc)["reason"] == "unknown"
