"""D40：Claude Code 的 PostToolUse 映射把成员级的 MCP 调用补成会话级。

跨包约定：PostToolUse hook 在 spool 写 {"type":"tool_map","key","session_id","tool_use_id","tool"}，Stop 拉起的
flush 经 POST /api/v1/hooks/batch 上报；tool_use_id 等于 tools/call 的 _meta["claudecode/toolUseId"]（S3）。

服务端：
- MCP 读写工具都把校验过格式的 toolUseId 记到这次调用产生的事件上（和 token_id 一起），归属仍按现规则；
- tool_map 的会话要过 resolve_session（同一 token、client=claude_code 登记、未结束），否则 ignored 并写审计；
- 只把"同一 token_id、tool_use_id 相同、当前是成员级"的事件补成 exact，幂等；认领/开始类事件设置 current_task；
- 映射先于调用到达时先存着，调用到达时直接判 exact；映射保留 24 小时；
- A 的 token 绝不能通过映射改写 B 的事件，也不能把映射挂到别人登记的会话上。
"""

from __future__ import annotations

import secrets
from datetime import timedelta

import pytest

from teamflow_server import mcp_server
from teamflow_server.config import token_id_of
from teamflow_server.service import READ_TOOL_NAMES, TOOL_NAMES, TOOL_USE_RE, Actor, session_tag, tool_use_id

from .conftest import ALICE, ALICE2, BOB, BOB_CC, LegacyMcp, ModernMcp, auth, dev_headers, human, read_log, vs

TU_KEY = "claudecode/toolUseId"


def new_tu() -> str:
    """运行时生成的 toolUseId（形如 toolu_01…，字母数字）。"""
    return "toolu_01" + secrets.token_hex(11)


async def start(c, token: str, sid: str, client_name: str = "claude") -> None:
    r = await c.post("/api/v1/hooks/session-start", headers=auth(token), json={"client": client_name, "session_id": sid})
    assert r.status_code == 200, r.text


async def tool_map(c, token: str, sid: str | None, tuid, tool: str | None = "claim_task", key: str | None = None, **more):
    item = {"type": "tool_map", "key": key or f"tm-{secrets.token_hex(6)}", "tool_use_id": tuid, **more}
    if sid is not None:
        item["session_id"] = sid
    if tool is not None:
        item["tool"] = tool
    r = await c.post("/api/v1/hooks/batch", headers=auth(token), json={"items": [item]})
    assert r.status_code == 200, r.text
    return r.json()["results"][0]


async def end(client, token: str, sid: str) -> None:
    r = await client.post(
        "/api/v1/hooks/batch", headers=auth(token), json={"items": [{"key": f"end-{sid}-{secrets.token_hex(3)}", "type": "end", "session_id": sid}]}
    )
    assert r.json()["results"][0]["st"] == "ok"


def call_events(svc, tuid: str):
    return [e for e in svc.events if e.tool_use == tuid]


def audits(svc, action: str):
    return [a for a in svc.audit if a["action"] == action]


# ---- 格式与常量 ----


def test_tool_names_match_mcp_server():
    assert mcp_server.TOOL_ORDER == TOOL_NAMES
    assert mcp_server.WRITE_TOOLS == set(TOOL_NAMES) - READ_TOOL_NAMES


@pytest.mark.parametrize(
    "raw,ok",
    [
        ("toolu_012HDfH2mEGmyGFoKMDw5GJw", True),  # S3 实测的样子
        ("toolu_" + "bdrk_" + "01ABCdefGHIJ", True),  # Bedrock 带下划线
        ("toolu_" + "vrtx_" + "01ABCdefGHIJ", True),  # Vertex
        ("toolu_" + "a" * 80, True),
        ("toolu_" + "a" * 81, False),
        ("toolu_short", False),
        ("call_012HDfH2mEGmyGFoKMDw5GJw", False),
        ("toolu_012HDfH2-mEGmyGFoKMDw5GJw", False),
        ("toolu_012HDfH2mEGmyGFoKMDw5GJw\n", False),
        ("toolu_０１２ＨＤｆＨ２ｍＥＧｍｙ", False),  # 全角
        (" toolu_012HDfH2mEGmyGFoKMDw5GJw", False),
        (12345678, False),
        (None, False),
        (["toolu_012HDfH2mEGmyGFoKMDw5GJw"], False),
    ],
)
def test_tool_use_id_format(raw, ok):
    assert (tool_use_id(raw) is not None) is ok
    if ok:
        assert TOOL_USE_RE.fullmatch(raw)


def test_session_tag():
    from teamflow_server.service import AgentSession

    assert session_tag(AgentSession("claude_code", "1a6941c0-21de-5c92-8067-c298f2345b24", "alice", "t")) == "1a6941c0"
    assert session_tag(AgentSession("claude_code", "h:abcdef123456", "alice", "t")) == "abcdef12"


# ---- MCP：toolUseId 记到事件上，归属不变 ----


@pytest.mark.parametrize("era", ["legacy", "modern"])
async def test_mcp_write_records_tool_use_with_token(client, svc, era, log_path):
    m = LegacyMcp(client, ALICE) if era == "legacy" else ModernMcp(client, ALICE)
    if era == "legacy":
        await m.initialize()
    tu = new_tu()
    res = await m.call("comment", {"target": "T-50", "body": f"{era} 进度"}, meta={TU_KEY: tu})
    assert res["isError"] is False
    ev = svc.events[-1]
    assert ev.type == "comment" and ev.tool_use == tu and ev.token_id == token_id_of(ALICE)
    # 归属仍按现规则：Claude Code 没有会话头，是成员级
    assert ev.session is None and ev.attribution == "member" and ev.session_src is None
    rec = [r for r in read_log(log_path) if r.get("tool") == "comment"][-1]
    assert rec["tool_use_id"] == tu
    # 格式不合格的丢弃：不记、不匹配；日志里只留一个标记
    bad = "toolu_" + "x" * 3
    await m.call("comment", {"target": "T-50", "body": f"{era} 第二条"}, meta={TU_KEY: bad})
    assert svc.events[-1].tool_use is None
    rec = [r for r in read_log(log_path) if r.get("tool") == "comment"][-1]
    assert rec.get("tool_use_bad") is True and "tool_use_id" not in rec


async def test_mcp_without_tool_use_and_rest_never_carry_it(client, svc):
    m = ModernMcp(client, ALICE)
    await m.call("comment", {"target": "T-50", "body": "没有 toolUseId"})
    assert svc.events[-1].tool_use is None and svc.events[-1].attribution == "member"
    r = await client.post("/api/v1/tasks/T-50/comments", headers={**auth(ALICE), TU_KEY: new_tu()}, json={"body": "REST 不读 _meta"})
    assert r.status_code == 201 and svc.events[-1].tool_use is None


async def test_read_tools_carry_tool_use_but_emit_nothing(client, svc):
    m = ModernMcp(client, ALICE)
    await start(client, ALICE, "cc-read")
    before, audit_n = svc.latest_event_id(), len(svc.audit)
    for name, args in (("inbox", {}), ("get_item", {"id": "T-50"}), ("list_tasks", {}), ("team_status", {})):
        tu = new_tu()
        res = await m.call(name, args, meta={TU_KEY: tu})
        assert res["isError"] is False
        # 读工具的映射：确认收下，不存（读不产生事件），也不写审计
        r = await tool_map(client, ALICE, "cc-read", tu, tool=name)
        assert (r["st"], r["status"], r["n"]) == ("ok", 200, 0)
        assert (token_id_of(ALICE), tu) not in svc.tool_maps
    assert svc.latest_event_id() == before and len(svc.audit) == audit_n


# ---- 映射在调用之后到达（常规路径） ----


@pytest.mark.parametrize("era", ["legacy", "modern"])
async def test_tool_map_after_call_upgrades_claim_and_sets_current_task(client, svc, era):
    await start(client, ALICE, "cc-1")
    m = LegacyMcp(client, ALICE) if era == "legacy" else ModernMcp(client, ALICE)
    if era == "legacy":
        await m.initialize()
    tu = new_tu()
    res = await m.call("claim_task", {"id": "T-53"}, meta={TU_KEY: tu})
    assert res["isError"] is False and res["structuredContent"]["st"] == "doing"
    evs = call_events(svc, tu)
    assert [e.type for e in evs] == ["task.claimed", "task.started"]
    assert all(e.session is None and e.attribution == "member" for e in evs)
    s = svc.sessions[("claude_code", "cc-1")]
    assert s.current_task is None
    # bob 看 alice：只到成员级，没有会话
    st = svc.team_status(Actor("bob", "agent", "codex", "tok_b", "mcp"))
    alice = next(o for o in st["others"] if o["h"] == "alice")
    assert "T-53" in alice["doing"] and alice["sess"] == []

    r = await tool_map(client, ALICE, "cc-1", tu, key="k-1")
    assert (r["st"], r["status"], r["n"]) == ("ok", 200, 2)
    assert all(e.session == "cc-1" and e.attribution == "exact" and e.session_src == "tool_map" for e in evs)
    assert s.current_task == "T-53" and s.current_task_ev == evs[-1].id

    # 读接口：bob 的 team_status、首页都能拼出"alice · Claude Code · 会话 cc1 在做 T-53"
    st = svc.team_status(Actor("bob", "agent", "codex", "tok_b", "mcp"))
    alice = next(o for o in st["others"] if o["h"] == "alice")
    assert alice["sess"] == [{"client": "claude_code", "s": "cc1", "task": "T-53"}]
    r2 = await client.get("/api/v1/status", headers=auth(BOB))
    assert next(o for o in r2.json()["others"] if o["h"] == "alice")["sess"] == alice["sess"]

    # 幂等：同一个 key 重放是 dup；同一映射换个 key 再来一次，不再补任何事件
    r = await tool_map(client, ALICE, "cc-1", tu, key="k-1")
    assert (r["st"], r["status"]) == ("dup", 409)
    r = await tool_map(client, ALICE, "cc-1", tu, key="k-1b")
    assert (r["st"], r["n"]) == ("ok", 0)
    assert all(e.session == "cc-1" for e in evs) and s.current_task == "T-53"


async def test_tool_map_upgrades_every_write_tool(client, svc):
    await start(client, ALICE, "cc-1")
    m = ModernMcp(client, ALICE)
    calls = [
        ("create_task", {"title": "整理发布清单"}),
        ("update_task", {"id": "T-50", "note": "接口接好了"}),
        ("report_blocker", {"title": "缺一个测试账号", "task": "T-50"}),
        ("comment", {"target": "B-7", "body": "我来看看安全组"}),
    ]
    tus = []
    for name, args in calls:
        tu = new_tu()
        res = await m.call(name, args, meta={TU_KEY: tu})
        assert res["isError"] is False, res
        assert call_events(svc, tu), name
        tus.append((name, tu))
    # 一批上报，顺序无关
    items = [{"type": "tool_map", "key": f"k-{tu}", "session_id": "cc-1", "tool_use_id": tu, "tool": name} for name, tu in reversed(tus)]
    r = await client.post("/api/v1/hooks/batch", headers=auth(ALICE), json={"items": items})
    assert [x["st"] for x in r.json()["results"]] == ["ok"] * 4
    for _, tu in tus:
        assert all(e.session == "cc-1" and e.attribution == "exact" for e in call_events(svc, tu))
    # 不是认领/开始类事件，不设置 current_task
    assert svc.sessions[("claude_code", "cc-1")].current_task is None


async def test_update_task_start_via_mcp_sets_current_task(client, svc):
    """update_task(status=in_progress) 也是开始类：任务由 alice 进行中时，映射设置 current_task。"""
    await start(client, ALICE, "cc-1")
    svc.human_claim(human("alice"), "T-53", **vs(svc, "T-53"))  # 人认领后是"待开始"
    m = ModernMcp(client, ALICE)
    tu = new_tu()
    res = await m.call("update_task", {"id": "T-53", "status": "in_progress"}, meta={TU_KEY: tu})
    assert res["isError"] is False and res["structuredContent"]["st"] == "doing"
    assert [e.type for e in call_events(svc, tu)] == ["task.started"]
    r = await tool_map(client, ALICE, "cc-1", tu, tool="update_task")
    assert r["n"] == 1 and svc.sessions[("claude_code", "cc-1")].current_task == "T-53"


# ---- 映射先于调用到达 ----


async def test_tool_map_before_call_is_exact_on_arrival(client, svc):
    await start(client, ALICE, "cc-1")
    tu = new_tu()
    r = await tool_map(client, ALICE, "cc-1", tu)
    assert (r["st"], r["n"]) == ("ok", 0)
    assert svc.tool_maps[(token_id_of(ALICE), tu)].session == "cc-1"
    audit_n = len(audits(svc, "session.resolve"))
    m = ModernMcp(client, ALICE)
    res = await m.call("claim_task", {"id": "T-53"}, meta={TU_KEY: tu})
    assert res["isError"] is False
    evs = call_events(svc, tu)
    assert [e.type for e in evs] == ["task.claimed", "task.started"]
    assert all(e.session == "cc-1" and e.attribution == "exact" and e.session_src == "tool_map" for e in evs)
    assert svc.sessions[("claude_code", "cc-1")].current_task == "T-53"
    assert len(audits(svc, "session.resolve")) == audit_n  # 成功不写审计


async def test_tool_map_before_call_but_session_ended_meanwhile(client, svc):
    await start(client, ALICE, "cc-1")
    tu = new_tu()
    await tool_map(client, ALICE, "cc-1", tu, tool="comment")
    await end(client, ALICE, "cc-1")
    m = ModernMcp(client, ALICE)
    await m.call("comment", {"target": "T-50", "body": "会话结束之后才到的调用"}, meta={TU_KEY: tu})
    ev = svc.events[-1]
    assert ev.tool_use == tu and ev.session is None and ev.attribution == "member"
    a = audits(svc, "session.resolve")[-1]
    assert (a["reason"], a["source"]) == ("ended", "tool_map")


async def test_tool_map_and_end_in_one_batch(client, svc):
    """flush 按 spool 顺序上报：tool_map 在 end 之前，先补成 exact、设置 current_task，再被 end 清掉。"""
    await start(client, ALICE, "cc-1")
    tu = new_tu()
    await ModernMcp(client, ALICE).call("claim_task", {"id": "T-53"}, meta={TU_KEY: tu})
    items = [
        {"type": "tool_map", "key": "a1", "session_id": "cc-1", "tool_use_id": tu, "tool": "claim_task"},
        {"type": "end", "key": "a2", "session_id": "cc-1", "reason": "prompt_input_exit"},
    ]
    r = await client.post("/api/v1/hooks/batch", headers=auth(ALICE), json={"items": items})
    assert [x["st"] for x in r.json()["results"]] == ["ok", "ok"]
    assert all(e.session == "cc-1" for e in call_events(svc, tu))
    assert svc.sessions[("claude_code", "cc-1")].current_task is None

async def test_tool_map_after_end_in_same_batch_still_counts(client, svc):
    """CLI 的 spool 不保证顺序：同一批里 end 排在 tool_map 前面时，这枚 token 自己刚结束的会话仍然认
    （PostToolUse 一定发生在 SessionEnd 之前），但不再设置 current_task。结果按条目原顺序返回。"""
    await start(client, ALICE, "cc-2")
    tu = new_tu()
    await ModernMcp(client, ALICE).call("claim_task", {"id": "T-53"}, meta={TU_KEY: tu})
    items = [
        {"type": "end", "key": "b1", "session_id": "cc-2"},
        {"type": "tool_map", "key": "b2", "session_id": "cc-2", "tool_use_id": tu, "tool": "claim_task"},
        {"type": "tool_map", "key": "b2", "session_id": "cc-2", "tool_use_id": tu, "tool": "claim_task"},  # 同批重复
    ]
    r = await client.post("/api/v1/hooks/batch", headers=auth(ALICE), json={"items": items})
    assert [(x["key"], x["st"], x.get("n")) for x in r.json()["results"]] == [("b1", "ok", None), ("b2", "ok", 2), ("b2", "dup", None)]
    assert all(e.session == "cc-2" and e.attribution == "exact" for e in call_events(svc, tu))
    s = svc.sessions[("claude_code", "cc-2")]
    assert s.ended_at is not None and s.current_task is None
    # 上一批就结束了的会话：不认
    tu2 = new_tu()
    await ModernMcp(client, ALICE).call("comment", {"target": "T-50", "body": "结束之后的映射"}, meta={TU_KEY: tu2})
    r = await tool_map(client, ALICE, "cc-2", tu2, tool="comment")
    assert (r["st"], r["err"]) == ("ignored", "session")
    assert audits(svc, "session.resolve")[-1]["reason"] == "ended"


async def test_tool_map_before_start_in_same_batch(client, svc):
    """SessionStart 时服务端不可达，会话登记（start）进了 spool：同一批里排在后面也先登记、再处理映射。"""
    tu = new_tu()
    await ModernMcp(client, ALICE).call("claim_task", {"id": "T-53"}, meta={TU_KEY: tu})
    items = [
        {"type": "tool_map", "key": "c1", "session_id": "cc-off", "tool_use_id": tu, "tool": "claim_task"},
        {"type": "turn_end", "key": "c2", "session_id": "cc-off"},
        {"type": "start", "key": "c3", "session_id": "cc-off", "source": "startup"},
    ]
    r = await client.post("/api/v1/hooks/batch", headers=auth(ALICE), json={"items": items})
    assert [(x["key"], x["st"]) for x in r.json()["results"]] == [("c1", "ok"), ("c2", "ok"), ("c3", "ok")]
    assert svc.sessions[("claude_code", "cc-off")].current_task == "T-53"


async def test_same_batch_end_relaxation_never_covers_other_tokens(client, svc):
    """同批 end 的放宽只对这枚 token 自己结束的会话：对别人会话的 end 本来就整条忽略，后面的映射照样忽略。"""
    await start(client, BOB_CC, "cc-bob")
    await start(client, ALICE2, "cc-alice2")
    tu = new_tu()
    await ModernMcp(client, ALICE).call("comment", {"target": "T-50", "body": "alice 的调用"}, meta={TU_KEY: tu})
    for sid in ("cc-bob", "cc-alice2"):
        items = [
            {"type": "end", "key": f"e-{sid}", "session_id": sid},
            {"type": "tool_map", "key": f"m-{sid}", "session_id": sid, "tool_use_id": tu, "tool": "comment"},
        ]
        r = await client.post("/api/v1/hooks/batch", headers=auth(ALICE), json={"items": items})
        assert [(x["st"], x.get("err")) for x in r.json()["results"]] == [("ignored", "session")] * 2
        assert svc.sessions[("claude_code", sid)].ended_at is None
    assert call_events(svc, tu)[0].session is None


def test_tool_map_arriving_mid_call_attaches_at_emit(svc):
    """映射在 _attribution 之后、写事件之前到达（调用途中）：_emit 时直接挂上，认领也设置 current_task。"""
    alice_hook = Actor("alice", "agent", "claude_code", "tok_alice_cc", "hook")
    svc.hook_session_start(alice_hook, {"session_id": "cc-1"})
    tu = new_tu()
    member = Actor("alice", "agent", "claude_code", "tok_alice_cc", "mcp", tool_use=tu)  # 归属时还是成员级
    r = svc.hook_batch(alice_hook, [{"type": "tool_map", "key": "m1", "session_id": "cc-1", "tool_use_id": tu, "tool": "claim_task"}])
    assert (r["results"][0]["st"], r["results"][0]["n"]) == ("ok", 0)
    svc.claim_task(member, "T-53")
    evs = call_events(svc, tu)
    assert [(e.type, e.session, e.session_src) for e in evs] == [("task.claimed", "cc-1", "tool_map"), ("task.started", "cc-1", "tool_map")]
    assert svc.sessions[("claude_code", "cc-1")].current_task == "T-53"
    # 另一枚 token 的同一个 tool_use_id 不会被这条映射挂上
    other = Actor("alice", "agent", "claude_code", "tok_alice_cc2", "mcp", tool_use=tu)
    svc.comment(other, "T-50", "另一台机器")
    assert svc.events[-1].session is None and svc.events[-1].attribution == "member"


# ---- 伪造：A 的 token 碰不到 B 的事件，映射挂不到别人登记的会话上 ----


async def test_tool_map_cannot_rewrite_other_tokens_events(client, svc):
    """bob 的 Claude Code 调用带 toolUseId X；alice 知道 X，也拿自己的会话上报 X：bob 的事件不变。"""
    await start(client, ALICE, "cc-alice")
    await start(client, BOB_CC, "cc-bob")
    tu = new_tu()
    bob = ModernMcp(client, BOB_CC)
    res = await bob.call("comment", {"target": "T-49", "body": "bob 的进度"}, meta={TU_KEY: tu})
    assert res["isError"] is False
    bob_ev = call_events(svc, tu)[0]
    assert bob_ev.actor == "bob" and bob_ev.token_id == token_id_of(BOB_CC)

    r = await tool_map(client, ALICE, "cc-alice", tu, tool="comment")
    assert (r["st"], r["n"]) == ("ok", 0)  # 映射只按 alice 自己的 token 存
    assert bob_ev.session is None and bob_ev.attribution == "member"
    # alice 的另一枚 token、bob 的 Codex token 也一样碰不到
    await start(client, ALICE2, "cc-alice2")
    r = await tool_map(client, ALICE2, "cc-alice2", tu, tool="comment")
    assert r["n"] == 0 and bob_ev.session is None
    # alice 存下的映射也不会让 bob 之后同一个 toolUseId 的调用挂到 alice 的会话上
    await bob.call("comment", {"target": "T-49", "body": "bob 的第二条"}, meta={TU_KEY: tu})
    assert svc.events[-1].actor == "bob" and svc.events[-1].session is None
    # bob 自己的映射才有用
    r = await tool_map(client, BOB_CC, "cc-bob", tu, tool="comment")
    assert r["n"] == 2 and all(e.session == "cc-bob" for e in call_events(svc, tu) if e.actor == "bob")
    assert not [e for e in svc.events if e.session == "cc-alice"]


async def test_tool_map_cannot_hijack_other_members_session(client, svc):
    """alice 的 token 把自己的调用映射到 bob 登记的会话上：整条忽略、写审计，事件保持成员级，bob 的会话不变。"""
    await start(client, BOB_CC, "cc-bob")
    svc.sessions[("claude_code", "cc-bob")].current_task = "T-49"
    tu = new_tu()
    await ModernMcp(client, ALICE).call("claim_task", {"id": "T-53"}, meta={TU_KEY: tu})
    r = await tool_map(client, ALICE, "cc-bob", tu)
    assert (r["st"], r["status"], r["err"]) == ("ignored", 403, "session")
    a = audits(svc, "session.resolve")[-1]
    assert (a["reason"], a["source"], a["h"]) == ("token_mismatch", "tool_map", "alice")
    assert all(e.session is None and e.attribution == "member" for e in call_events(svc, tu))
    s = svc.sessions[("claude_code", "cc-bob")]
    assert s.current_task == "T-49" and s.handle == "bob" and s.ended_at is None
    assert (token_id_of(ALICE), tu) not in svc.tool_maps


@pytest.mark.parametrize("case", ["same_member_other_token", "unknown", "ended", "codex_session_id"])
async def test_tool_map_session_must_be_registered_by_same_token(client, svc, case):
    tu = new_tu()
    await ModernMcp(client, ALICE).call("comment", {"target": "T-50", "body": f"调用 {case}"}, meta={TU_KEY: tu})
    sid, reason = {
        "same_member_other_token": ("cc-a2", "token_mismatch"),  # alice 第二台机器登记的会话
        "unknown": ("never-registered", "unknown"),
        "ended": ("cc-a1", "ended"),
        "codex_session_id": ("019a-sess", "unknown"),  # bob 的 Codex 会话：client 是主键的一部分
    }[case]
    if case == "same_member_other_token":
        await start(client, ALICE2, sid)
    elif case == "ended":
        await start(client, ALICE, sid)
        await end(client, ALICE, sid)
    elif case == "codex_session_id":
        await start(client, BOB, sid, "codex")
    # 条目自称 codex 也没用：client 强制取 token 的
    r = await tool_map(client, ALICE, sid, tu, tool="comment", client="codex")
    assert (r["st"], r["status"], r["err"]) == ("ignored", 403, "session")
    a = audits(svc, "session.resolve")[-1]
    assert (a["reason"], a["source"]) == (reason, "tool_map")
    assert call_events(svc, tu)[0].session is None
    if case == "codex_session_id":
        assert svc.sessions[("codex", sid)].ended_at is None


async def test_tool_map_from_codex_token_is_ignored(client, svc):
    """只有 Claude Code 装 PostToolUse。Codex token 即使伪造 claudecode/toolUseId，映射也整条忽略。"""
    await start(client, BOB, "019a-sess", "codex")
    tu = new_tu()
    await ModernMcp(client, BOB).call("comment", {"target": "T-49", "body": "codex 的进度"}, meta={TU_KEY: tu})
    ev = svc.events[-1]
    assert ev.tool_use == tu and ev.session is None  # 记下来了，但不会被映射
    r = await tool_map(client, BOB, "019a-sess", tu, tool="comment")
    assert (r["st"], r["status"], r["err"]) == ("ignored", 403, "client")
    assert audits(svc, "tool_map.client")[-1]["client"] == "codex"
    assert ev.session is None and svc.tool_maps == {}


async def test_tool_map_conflict_first_session_wins(client, svc):
    await start(client, ALICE, "cc-1")
    await start(client, ALICE, "cc-2")
    tu = new_tu()
    await ModernMcp(client, ALICE).call("claim_task", {"id": "T-53"}, meta={TU_KEY: tu})
    assert (await tool_map(client, ALICE, "cc-1", tu))["st"] == "ok"
    r = await tool_map(client, ALICE, "cc-2", tu)
    assert (r["st"], r["err"]) == ("ignored", "conflict")
    assert audits(svc, "tool_map.conflict")
    assert all(e.session == "cc-1" for e in call_events(svc, tu))
    assert svc.sessions[("claude_code", "cc-1")].current_task == "T-53"
    assert svc.sessions[("claude_code", "cc-2")].current_task is None


async def test_tool_map_never_overrides_exact_events(client, svc):
    """已经 exact 的事件（例如带了自己的会话头）不被映射改写；映射只补成员级的。"""
    await start(client, ALICE, "cc-1")
    await start(client, ALICE, "cc-2")
    tu = new_tu()
    m = ModernMcp(client, ALICE, extra={"x-teamflow-session": "cc-1"})
    await m.call("comment", {"target": "T-50", "body": "带会话头"}, meta={TU_KEY: tu})
    ev = svc.events[-1]
    assert (ev.session, ev.session_src) == ("cc-1", "header")
    r = await tool_map(client, ALICE, "cc-2", tu, tool="comment")
    assert (r["st"], r["n"]) == ("ok", 0)
    assert (ev.session, ev.session_src) == ("cc-1", "header")


@pytest.mark.parametrize(
    "item,err",
    [
        ({"tool_use_id": "toolu_x"}, "tool_use_id"),
        ({"tool_use_id": "call_" + "a" * 20}, "tool_use_id"),
        ({"tool_use_id": None}, "tool_use_id"),
        ({"tool_use_id": "<TU>", "session_id": None}, "session"),
        ({"tool_use_id": "<TU>", "tool": "Bash"}, "tool"),
        ({"tool_use_id": "<TU>", "tool": "mcp__teamflow__comment"}, "tool"),  # hook 要去掉前缀
    ],
)
async def test_tool_map_bad_items(client, svc, item, err):
    await start(client, ALICE, "cc-1")
    it = {"type": "tool_map", "key": "bad-1", "session_id": "cc-1", "tool": "comment", **item}
    if it.get("tool_use_id") == "<TU>":
        it["tool_use_id"] = new_tu()
    it = {k: v for k, v in it.items() if v is not None}
    r = await client.post("/api/v1/hooks/batch", headers=auth(ALICE), json={"items": [it]})
    res = r.json()["results"][0]
    assert (res["st"], res["status"], res["err"]) == ("bad", 422, err)
    assert svc.tool_maps == {}


# ---- current_task 的规则 ----


async def test_tool_map_current_task_only_while_member_still_doing_it(client, svc):
    await start(client, ALICE, "cc-1")
    m = ModernMcp(client, ALICE)
    tu = new_tu()
    await m.call("claim_task", {"id": "T-53"}, meta={TU_KEY: tu})
    await m.call("update_task", {"id": "T-53", "status": "open", "note": "先交回去，接口还没定"})
    r = await tool_map(client, ALICE, "cc-1", tu)
    assert r["n"] == 2 and all(e.session == "cc-1" for e in call_events(svc, tu))
    assert svc.sessions[("claude_code", "cc-1")].current_task is None  # 已经不在进行中


async def test_tool_map_late_mapping_does_not_steal_newer_start(client, svc):
    """会话 1 开始 T-53 → 交回 → 会话 2（成员级、映射先到）再开始：会话 1 迟到的映射不能把 T-53 指回会话 1。"""
    await start(client, ALICE, "cc-1")
    await start(client, ALICE, "cc-2")
    m = ModernMcp(client, ALICE)
    tu1, tu2 = new_tu(), new_tu()
    await m.call("claim_task", {"id": "T-53"}, meta={TU_KEY: tu1})
    await m.call("update_task", {"id": "T-53", "status": "open", "note": "换个终端接着做"})
    await tool_map(client, ALICE, "cc-2", tu2)
    await m.call("claim_task", {"id": "T-53"}, meta={TU_KEY: tu2})
    assert svc.sessions[("claude_code", "cc-2")].current_task == "T-53"
    r = await tool_map(client, ALICE, "cc-1", tu1)
    assert r["n"] == 2
    assert svc.sessions[("claude_code", "cc-1")].current_task is None
    assert svc.sessions[("claude_code", "cc-2")].current_task == "T-53"


async def test_tool_map_late_mapping_keeps_newer_pointer_of_same_session(client, svc):
    """同一会话先开始 T-53（成员级）再开始 T-50 的新任务（映射已到）：T-53 迟到的映射不覆盖较新的指向。"""
    await start(client, ALICE, "cc-1")
    m = ModernMcp(client, ALICE)
    tu1, tu2 = new_tu(), new_tu()
    await m.call("claim_task", {"id": "T-53"}, meta={TU_KEY: tu1})
    res = await m.call("create_task", {"title": "补首页埋点", "assignee": "alice"})
    tid = res["structuredContent"]["id"]
    await tool_map(client, ALICE, "cc-1", tu2)
    await m.call("claim_task", {"id": tid}, meta={TU_KEY: tu2})
    s = svc.sessions[("claude_code", "cc-1")]
    assert s.current_task == tid
    await tool_map(client, ALICE, "cc-1", tu1)
    assert s.current_task == tid
    assert all(e.session == "cc-1" for e in call_events(svc, tu1))


# ---- 保留期 24 小时 ----


def test_tool_map_retention_24h(svc):
    base = svc.clock()
    off = {"v": timedelta(0)}
    svc.clock = lambda: base + off["v"]
    alice = Actor("alice", "agent", "claude_code", "tok_alice_cc", "hook")
    svc.hook_session_start(alice, {"session_id": "cc-1"})

    # 映射先到，25 小时后调用才到：映射已过期，成员级
    tu = new_tu()
    assert svc.hook_batch(alice, [{"type": "tool_map", "key": "r1", "session_id": "cc-1", "tool_use_id": tu, "tool": "comment"}])["results"][0]["st"] == "ok"
    off["v"] = timedelta(hours=25)
    svc.hook_session_start(alice, {"session_id": "cc-1"})  # 会话还活着
    svc.comment(Actor("alice", "agent", "claude_code", "tok_alice_cc", "mcp", tool_use=tu), "T-50", "隔天才到的调用")
    assert svc.events[-1].tool_use == tu and svc.events[-1].session is None

    # 调用先到，映射 25 小时后才到：不再补
    tu2 = new_tu()
    svc.comment(Actor("alice", "agent", "claude_code", "tok_alice_cc", "mcp", tool_use=tu2), "T-50", "这次调用的映射迟到了")
    ev = svc.events[-1]
    off["v"] = timedelta(hours=50)
    svc.hook_session_start(alice, {"session_id": "cc-1"})
    r = svc.hook_batch(alice, [{"type": "tool_map", "key": "r2", "session_id": "cc-1", "tool_use_id": tu2, "tool": "comment"}])
    assert r["results"][0]["n"] == 0 and ev.session is None
    # 过期的映射和索引都清掉了
    assert ("tok_alice_cc", tu) not in svc.tool_maps
    assert ("tok_alice_cc", tu2) not in svc.call_events

    # 24 小时以内：照常补
    tu3 = new_tu()
    svc.comment(Actor("alice", "agent", "claude_code", "tok_alice_cc", "mcp", tool_use=tu3), "T-50", "当天的调用")
    off["v"] += timedelta(hours=23)
    svc.hook_session_start(alice, {"session_id": "cc-1"})
    r = svc.hook_batch(alice, [{"type": "tool_map", "key": "r3", "session_id": "cc-1", "tool_use_id": tu3, "tool": "comment"}])
    assert r["results"][0]["n"] == 1 and svc.events[-1].session == "cc-1"


# ---- 读接口：首页数据 ----


async def test_home_shows_session_tag_only_when_exact(client, svc):
    await start(client, ALICE, "1a6941c0-21de-5c92-8067-c298f2345b24")
    tu = new_tu()
    await ModernMcp(client, ALICE).call("claim_task", {"id": "T-53"}, meta={TU_KEY: tu})
    r = await client.get("/api/v1/dev/home", headers=dev_headers("bob"))
    assert r.status_code == 200, r.text
    home = r.json()
    rows = {row["id"]: row for row in home["doing"]}
    assert rows["T-53"] == {"h": "alice", "id": "T-53", "client": "claude_code", "today": True}  # 成员级：没有 sess
    assert rows["T-49"]["h"] == "bob" and "sess" not in rows["T-49"]
    assert set(home) == {"me", "mine", "blockers", "doing", "counts"} and home["me"] == "bob"
    assert home["mine"]["to_accept"] == [{"id": "T-52", "by": "alice", "bk": "agent", "client": "claude_code"}]
    assert home["blockers"][0]["id"] == "B-7" and home["counts"]["doing"] == 3

    await tool_map(client, ALICE, "1a6941c0-21de-5c92-8067-c298f2345b24", tu)
    rows = {row["id"]: row for row in (await client.get("/api/v1/dev/home", headers=dev_headers("bob"))).json()["doing"]}
    assert rows["T-53"]["sess"] == [{"client": "claude_code", "s": "1a6941c0"}]
    # 只有 ID、handle、枚举值和短标签，没有标题、仓库、分支
    assert set(rows["T-53"]) == {"h", "id", "client", "sess", "today"}
    # 任务交回之后，会话不再指向它
    await ModernMcp(client, ALICE).call("update_task", {"id": "T-53", "status": "open", "note": "先放一放"})
    rows = {row["id"]: row for row in (await client.get("/api/v1/dev/home", headers=dev_headers("bob"))).json()["doing"]}
    assert "T-53" not in rows
    st = svc.team_status(Actor("bob", "agent", "codex", "tok_b", "mcp"))
    assert next(o for o in st["others"] if o["h"] == "alice")["sess"] == []


async def test_codex_exact_session_shows_in_team_status(client, svc):
    """Codex 的 _meta 精确归属本来就设置 current_task；读接口同样给出会话短标签。"""
    await start(client, BOB, "019a2b3c-sess", "codex")
    svc.human_claim(human("bob"), "T-51", **vs(svc, "T-51"))
    m = ModernMcp(client, BOB)
    res = await m.call("claim_task", {"id": "T-51"}, meta={"x-codex-turn-metadata": {"session_id": "019a2b3c-sess"}})
    assert res["isError"] is False
    started = [e for e in svc.events if e.type == "task.started" and e.subject == "T-51"][-1]
    assert (started.session, started.session_src, started.attribution) == ("019a2b3c-sess", "codex_meta", "exact")
    r = await client.get("/api/v1/status", headers=auth(ALICE))
    bob = next(o for o in r.json()["others"] if o["h"] == "bob")
    assert bob["sess"] == [{"client": "codex", "s": "019a2b3c", "task": "T-51"}]
    m2 = ModernMcp(client, ALICE)
    res = await m2.call("team_status", {})
    assert next(o for o in res["structuredContent"]["others"] if o["h"] == "bob")["sess"] == bob["sess"]
