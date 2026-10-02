"""领域规则：信封与 trust、"看见"闸门（withheld）、needs_human、needs_accept、taken 文案、回归路径、扫描、幂等。"""

from __future__ import annotations

import re

import pytest

from teamflow_server.errors import DomainError

from .conftest import ALICE, BOB, LegacyMcp, ModernMcp, agent, dev_headers, human, vs

ENVELOPE_KEYS = {"t", "by", "trust", "client"}
TRUSTS = {"self_human", "self_agent", "peer_human", "peer_agent"}


def walk_envelopes(obj):
    if isinstance(obj, dict):
        if "trust" in obj and "t" in obj:
            yield obj
        for v in obj.values():
            yield from walk_envelopes(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_envelopes(v)


def test_envelope_format_and_trust_values(svc):
    alice = agent("alice", "claude_code")
    rows = svc.list_tasks(alice, view="all")["rows"]
    trusts = {}
    for r in rows:
        env = r["t"]
        assert set(env) == ENVELOPE_KEYS
        assert env["trust"] in TRUSTS
        trusts[r["id"]] = (env["trust"], env["client"])
    assert trusts["T-50"] == ("self_human", None)  # alice 本人写的
    assert trusts["T-53"] == ("self_agent", "claude_code")  # alice 的 Claude Code 写的
    assert trusts["T-49"] == ("peer_human", None)  # bob 本人写的
    assert trusts["T-51"] == ("peer_agent", "codex")  # bob 的 Codex 写的


def test_gate_withholds_peer_body_until_accept(svc):
    bob = agent("bob", "codex")
    item = svc.get_item(bob, "T-52")
    assert item["withheld"] == "needs_accept"
    assert "content" not in item
    assert item["t"]["trust"] == "peer_agent"  # 标题默认可见（团队信任档），但在信封里
    # 人在手机上接受（版本、sha、seq 一致）
    svc.human_accept(
        human("bob"), "T-52", v=item["v"], sha=svc.tasks["T-52"].content_sha256, seq=item["assign"]["seq"], through=svc.page_view("T-52")["through"]
    )
    item = svc.get_item(bob, "T-52")
    assert "withheld" not in item
    assert item["content"]["trust"] == "peer_agent"
    assert item["content"]["by"] == "alice" and item["content"]["client"] == "claude_code"
    assert item["content"]["t"].startswith("回调失败时")


def test_accept_with_stale_version_conflicts(svc):
    ok = vs(svc, "T-52", seq=True)
    for bad in ({"v": 99}, {"sha": "0" * 64}, {"seq": 7}):
        with pytest.raises(DomainError) as e:
            svc.human_accept(human("bob"), "T-52", **{**ok, **bad})
        assert e.value.code == "conflict" and e.value.http_status == 409 and "重新查看" in e.value.msg
        assert svc.tasks["T-52"].assign_state == "pending"


def test_gate_on_blocker_and_peer_agent_comments(svc):
    alice = agent("alice", "claude_code")
    item = svc.get_item(alice, "B-7")
    assert item["withheld"] == "needs_accept"
    held = [e for e in item["ev"] if e.get("withheld") == "peer_agent_text"]
    assert held == [{"withheld": "peer_agent_text", "by": "bob", "n": 1, "url": held[0]["url"]}]
    assert all("t" not in e for e in item["ev"])
    assert svc.inbox(alice)["fwd"] == [{"id": "B-7", "n": 1, "by": "bob"}]
    # alice 在手机上认领这个困难（帮忙）：写 acceptance，through 到当前
    svc.human_help(human("alice"), "B-7", **vs(svc, "B-7"))
    item = svc.get_item(alice, "B-7")
    assert "withheld" not in item
    assert item["content"]["detail"]["trust"] == "peer_agent"
    texts = [e["t"] for e in item["ev"] if "t" in e]
    assert any("安全组" in t for t in texts)
    # 之后 bob 的 agent 再写一条评论：超出 through，仍然 withheld，直到转发
    svc.comment(agent("bob", "codex"), "B-7", "我这边也试了换端口，还是不通。")
    item = svc.get_item(alice, "B-7")
    assert [e for e in item["ev"] if e.get("withheld") == "peer_agent_text"][0]["n"] == 1
    svc.human_forward(human("alice"), "B-7", through=svc.latest_event_id())
    item = svc.get_item(alice, "B-7")
    assert not [e for e in item["ev"] if e.get("withheld")]


def test_agent_claim_of_peer_pool_task_needs_human(svc):
    alice = agent("alice", "claude_code")
    with pytest.raises(DomainError) as e:
        svc.claim_task(alice, "T-51")
    assert e.value.code == "needs_human"
    assert "微信" in e.value.msg and "认领" in e.value.msg
    assert svc.tasks["T-51"].assignee is None
    asks = [n for n in svc.outbox if n["to"] == "alice" and n["kind"] == "agent_asks"]
    assert asks and asks[-1]["text"] == "您的 Claude Code 想开始 T-51，点这里认领"
    # 人在手机上认领后，agent 再 claim 就能开始，并能读到正文
    svc.human_claim(human("alice"), "T-51", **vs(svc, "T-51"))
    assert svc.tasks["T-51"].label == "todo"
    res = svc.claim_task(alice, "T-51")
    assert res["st"] == "doing"
    assert svc.get_item(alice, "T-51")["content"]["trust"] == "peer_agent"


def test_needs_accept_for_pending_assignment(svc):
    with pytest.raises(DomainError) as e:
        svc.claim_task(agent("bob", "codex"), "T-52")
    assert e.value.code == "needs_accept"
    assert "接受" in e.value.msg


def test_agent_cannot_accept_or_claim_as_human(svc):
    a = agent("bob", "codex")
    calls = [
        lambda: svc.human_accept(a, "T-52", **vs(svc, "T-52", seq=True)),
        lambda: svc.human_claim(a, "T-51", **vs(svc, "T-51")),
        lambda: svc.human_help(a, "B-7", **vs(svc, "B-7")),
        lambda: svc.human_forward(a, "B-7", through=svc.latest_event_id()),
        lambda: svc.human_ask(a, "B-7"),
    ]
    for call in calls:
        with pytest.raises(DomainError) as e:
            call()
        assert e.value.code == "human_only"


def test_taken_message_names_who_and_when(svc):
    svc.human_claim(human("bob"), "T-53", **vs(svc, "T-53"))
    with pytest.raises(DomainError) as e:
        svc.claim_task(agent("alice", "claude_code"), "T-53")
    assert e.value.code == "taken"
    assert re.search(r"T-53 已被 bob 于 \d\d:\d\d 认领", e.value.msg)
    assert e.value.extra["by"] == "bob"


def test_regression_agent_create_claim_release_claim(svc):
    a = agent("alice", "claude_code")
    tid = svc.create_task(a, "回归：agent 发布再认领", "正文")["id"]
    assert svc.claim_task(a, tid)["st"] == "doing"
    with pytest.raises(DomainError) as e:
        svc.update_task(a, tid, status="open")
    assert e.value.code == "invalid" and "交接说明" in e.value.msg
    assert svc.update_task(a, tid, status="open", note="做到一半，交给下一位")["st"] == "todo"
    assert svc.claim_task(a, tid)["st"] == "doing"
    assert svc.claim_task(a, tid)["st"] == "doing"  # 幂等
    assert svc.update_task(a, tid, status="done", note="PR #1 已合并")["st"] == "done"


def test_assign_to_peer_is_pending_and_notifies_without_free_text(svc):
    a = agent("alice", "claude_code")
    res = svc.create_task(a, "请看一下 7788999 号问题", "详情", assignee="bob")
    assert res["st"] == "pending"
    n = svc.outbox[-1]
    assert n["to"] == "bob" and n["text"] == f"alice 的 Claude Code 请您协作（{res['id']}）"
    t = svc.tasks[res["id"]]
    assert (t.assignee, t.assign_state, t.assign_seq) == ("bob", "pending", 1)


def test_agent_reported_need_is_only_a_proposal(svc):
    res = svc.report_blocker(agent("alice", "claude_code"), "要一个控制台权限", need="bob", tried="问过运维")
    assert res["need_state"] == "proposed" and res["st"] == "open"
    assert {"h": "bob", "why": "solved_before"} in res["suggest"] or res["suggest"][0]["h"] == "bob"
    assert svc.inbox(agent("alice", "claude_code"))["proposed"] == [{"id": res["id"], "h": "bob", "client": "claude_code"}]
    assert not [n for n in svc.outbox if n["subject"] == res["id"]]  # 没通知 bob


def test_proposed_need_stays_out_of_named_persons_feeds_until_owner_confirms(svc):
    """m1：agent 点名只进主人的增量；主人确认（ask）之前，被点名的人的增量、fwd、收件箱里都没有它。"""
    bob = agent("bob", "codex")
    alice = agent("alice", "claude_code")
    cur = svc.latest_event_id()
    res = svc.report_blocker(bob, "要一个控制台权限", detail="安全组要加规则", need="alice")
    bid = res["id"]
    svc.comment(bob, bid, "我先看看别的办法。")
    # 被点名的 alice：增量、fwd、收件箱、hook 快照里都没有
    d = svc.delta(alice, cur)
    assert not [i for i in d["items"] if i["id"] == bid]
    assert not [r for r in d["fwd"] if r["id"] == bid]
    ib = svc.inbox(alice, advance=False)
    assert not [r for r in ib["fwd"] if r["id"] == bid] and not [r for r in ib["help_me"] if r["id"] == bid]
    assert svc.new_count(alice) == len(svc._relevant_events("alice", svc.cursors.get(alice.token_id, 0)))
    assert not [e for e in svc._relevant_events("alice", cur) if e.subject == bid]
    # 主人 bob 自己的增量和"待我处理"里有
    assert svc.inbox(bob, advance=False)["proposed"] == [{"id": bid, "h": "alice", "client": "codex"}]
    # 主人在手机上确认后才进 alice 的增量、收件箱和 fwd
    svc.human_ask(human("bob"), bid)
    d = svc.delta(alice, cur)
    assert {i["ty"] for i in d["items"] if i["id"] == bid} >= {"blocker.raised", "comment", "blocker.asked"}
    assert {"id": bid, "by": "bob"} in d["help_me"]
    assert [r for r in d["fwd"] if r["id"] == bid] == [{"id": bid, "n": 1, "by": "bob"}]


def test_secret_detected(svc):
    with pytest.raises(DomainError) as e:
        svc.comment(agent("alice", "claude_code"), "T-50", "密钥是 AKIDabcdefghijklmnopqrstu")
    assert e.value.code == "secret_detected" and e.value.http_status == 422
    assert e.value.extra["rule"] == "tencent_akid"


def test_invariants_hold_after_seed(svc):
    for t in svc.tasks.values():
        svc._check_task(t)


def test_sanitizer_strips_invisible(svc):
    a = agent("alice", "claude_code")
    tid = svc.create_task(a, "标题\u200b\u202e带不可见\U000E0041字符")["id"]
    assert svc.tasks[tid].title == "标题带不可见字符"


# ---- 通过 MCP 走一遍（isError + structuredContent） ----


async def test_mcp_errors_are_iserror_with_actionable_text(client):
    m = ModernMcp(client, ALICE)
    res = await m.call("claim_task", {"id": "T-51"})
    assert res["isError"] is True
    sc = res["structuredContent"]
    assert sc["err"] == "needs_human" and "微信" in sc["msg"]
    # I5：出错时模型只看得到 content，content 要以错误码开头，instructions 的指令才对得上
    text = res["content"][0]["text"]
    assert text.startswith("needs_human：") and "微信" in text
    res = await m.call("get_item", {"id": "T-999"})
    assert res["isError"] is True and res["structuredContent"]["err"] == "not_found"
    assert res["content"][0]["text"].startswith("not_found：")


@pytest.mark.parametrize("era", ["legacy", "modern"])
async def test_mcp_error_content_starts_with_code_both_eras_and_replay(client, era):
    """I5：两代协议、needs_accept / taken / invalid，以及 callId 重放出来的错误，content 都以错误码开头。"""
    m = LegacyMcp(client, BOB) if era == "legacy" else ModernMcp(client, BOB)
    if era == "legacy":
        await m.initialize()
    res = await m.call("claim_task", {"id": "T-52"})
    assert res["isError"] is True and res["content"][0]["text"].startswith("needs_accept：")
    res = await m.call("claim_task", {"id": "T-50"})
    assert res["content"][0]["text"].startswith("taken：")
    for _ in range(2):  # 第二次是 callId 重放
        res = await m.call("create_task", {"title": "看 /etc/hosts"}, meta={"callId": f"c-{era}"})
        assert res["isError"] is True and res["content"][0]["text"].startswith("invalid：")


async def test_mcp_withheld_and_accept_flow(client):
    bob = LegacyMcp(client, BOB)
    await bob.initialize()
    res = await bob.call("get_item", {"id": "T-52"})
    assert res["isError"] is False and res["structuredContent"]["withheld"] == "needs_accept"
    res = await bob.call("claim_task", {"id": "T-52"})
    assert res["isError"] is True and res["structuredContent"]["err"] == "needs_accept"
    page = (await client.get("/api/v1/dev/items/T-52", headers=dev_headers("bob"))).json()
    r = await client.post("/api/v1/dev/tasks/T-52:accept", headers=dev_headers("bob"), json={k: page[k] for k in ("v", "sha", "seq", "through")})
    assert r.status_code == 200, r.text
    res = await bob.call("claim_task", {"id": "T-52"})
    assert res["isError"] is False and res["structuredContent"]["st"] == "doing"
    res = await bob.call("get_item", {"id": "T-52"})
    assert res["structuredContent"]["content"]["trust"] == "peer_agent"
    res = await bob.call("update_task", {"id": "T-52", "status": "done", "note": "PR #318 已合并"})
    assert res["structuredContent"]["st"] == "done"
    # alice 收到回音
    alice = ModernMcp(client, ALICE)
    ib = (await alice.call("inbox", {}))["structuredContent"]
    assert {"id": "T-52", "ev": "done", "by": "bob"} in ib["replies"]


async def test_mcp_call_id_idempotency(client, svc):
    m = ModernMcp(client, BOB)
    before = svc.next_task_no
    r1 = await m.call("create_task", {"title": "幂等测试"}, meta={"callId": "call_A"})
    r2 = await m.call("create_task", {"title": "幂等测试"}, meta={"callId": "call_A"})
    assert r1["structuredContent"] == r2["structuredContent"]
    assert svc.next_task_no == before + 1
    r3 = await m.call("create_task", {"title": "换了参数"}, meta={"callId": "call_A"})
    assert r3["isError"] is True and r3["structuredContent"]["err"] == "invalid"


async def test_codex_meta_gives_exact_attribution(client, svc):
    """Codex：_meta.x-codex-turn-metadata.session_id 对上 hooks 登记的会话才算 exact（m3、I2）；
    thread_id 只记为子线程。没登记过的会话不能凭 _meta 自称 exact（原来的用例把这种伪造写成了期望）。"""
    m = ModernMcp(client, BOB)
    turn = {"session_id": "s-1", "thread_id": "th-1", "turn_id": "tu-1"}
    # 没登记过 s-1：降为成员级，并写审计
    await m.call("comment", {"target": "T-49", "body": "进度：迁移脚本写好了"}, meta={"callId": "c0", "x-codex-turn-metadata": turn})
    ev = svc.events[-1]
    assert ev.type == "comment" and ev.session is None and ev.thread == "th-1"
    assert svc.audit[-1]["action"] == "session.resolve" and svc.audit[-1]["reason"] == "unknown"
    # hooks 登记 s-1 之后：exact，session 是 session_id，不是 thread_id
    r = await client.post("/api/v1/hooks/session-start", headers={"authorization": f"Bearer {BOB}"}, json={"client": "codex", "session_id": "s-1"})
    assert r.status_code == 200
    await m.call("comment", {"target": "T-49", "body": "进度：迁移脚本跑通了"}, meta={"callId": "c1", "x-codex-turn-metadata": turn})
    ev = svc.events[-1]
    assert ev.type == "comment" and ev.session == "s-1" and ev.thread == "th-1"
    # 主线程（thread_id 与 session_id 相同）不重复记子线程
    same = {"session_id": "s-1", "thread_id": "s-1", "turn_id": "tu-2"}
    await m.call("comment", {"target": "T-49", "body": "进度：回滚脚本也写好了"}, meta={"callId": "c2", "x-codex-turn-metadata": same})
    assert svc.events[-1].session == "s-1" and svc.events[-1].thread is None


async def test_rest_mirrors_mcp(client):
    r = await client.post("/api/v1/tasks/T-51:claim", headers={"authorization": f"Bearer {ALICE}"})
    assert r.status_code == 403 and r.json()["error"] == "needs_human"
    r = await client.post("/api/v1/tasks/T-53:claim", headers={"authorization": f"Bearer {ALICE}", "idempotency-key": "k1"})
    assert r.status_code == 200 and r.json()["st"] == "doing"
    r2 = await client.post("/api/v1/tasks/T-53:claim", headers={"authorization": f"Bearer {ALICE}", "idempotency-key": "k1"})
    assert r2.json() == r.json() and r2.headers.get("idempotent-replayed") == "true"
    r = await client.post("/api/v1/tasks", headers={"authorization": f"Bearer {ALICE}"}, json={"title": "评论里带密钥", "body": "sk-ant-api03-abcdefghijklmnop"})
    assert r.status_code == 422 and r.json()["error"] == "secret_detected"


async def test_rest_note_does_not_change_status(client, svc):
    h = {"authorization": f"Bearer {ALICE}"}
    r = await client.post("/api/v1/tasks/T-50:note", headers=h, json={"note": "接口接上了", "status": "done"})
    assert r.status_code == 200 and r.json()["st"] == "doing"
    r = await client.post("/api/v1/tasks/T-50:done", headers=h, json={})
    assert r.status_code == 400 and r.json()["error"] == "invalid" and "note" in r.json()["message"]
    r = await client.post("/api/v1/tasks/T-50:done", headers=h, json={"note": "PR #2 已合并"})
    assert r.status_code == 200 and r.json()["st"] == "done"
    assert svc.tasks["T-50"].done_at is not None
