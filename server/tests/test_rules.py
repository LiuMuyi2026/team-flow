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
    assert item["withheld"] == "not_accepted"
    assert "content" not in item
    assert item["t"]["trust"] == "peer_agent"  # 标题默认可见（团队信任档），但在信封里
    # 人在网页上接受（版本、sha、seq 一致）
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
    assert item["withheld"] == "not_accepted"
    held = [e for e in item["ev"] if e.get("withheld") == "peer_agent_text"]
    assert held == [{"withheld": "peer_agent_text", "by": "bob", "n": 1, "url": held[0]["url"]}]
    assert all("t" not in e for e in item["ev"])
    assert svc.inbox(alice)["fwd"] == [{"id": "B-7", "n": 1, "by": "bob"}]
    # alice 在网页上认领这个困难（帮忙）：写 acceptance，through 到当前
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
    assert "已通知您" in e.value.msg and "Team Flow 网页" in e.value.msg and "认领" in e.value.msg
    assert svc.tasks["T-51"].assignee is None
    asks = [n for n in svc.outbox if n["to"] == "alice" and n["kind"] == "agent_asks"]
    assert asks and asks[-1]["text"] == "您的 Claude Code 想开始 T-51，点这里认领"
    # 人在网页上认领后，agent 再 claim 就能开始，并能读到正文
    svc.human_claim(human("alice"), "T-51", **vs(svc, "T-51"))
    assert svc.tasks["T-51"].label == "todo"
    res = svc.claim_task(alice, "T-51")
    assert res["st"] == "doing"
    assert svc.get_item(alice, "T-51")["content"]["trust"] == "peer_agent"


def test_needs_accept_for_pending_assignment(svc):
    with pytest.raises(DomainError) as e:
        svc.claim_task(agent("bob", "codex"), "T-52")
    assert e.value.code == "needs_accept"
    assert "接受" in e.value.msg and "Team Flow 网页" in e.value.msg
    assert "已通知" not in e.value.msg  # 这次调用没有发通知，不能这么说


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
    assert "bob" not in [x["h"] for x in res["suggest"]]  # 已经点名的人不再出现在建议里
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
    # 主人在网页上确认后才进 alice 的增量、收件箱和 fwd
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
    assert sc["err"] == "needs_human" and "已通知您" in sc["msg"] and "Team Flow 网页" in sc["msg"]
    # I5：出错时模型只看得到 content，content 要以错误码开头，instructions 的指令才对得上
    text = res["content"][0]["text"]
    assert text.startswith("needs_human：") and "已通知您" in text
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
    assert res["isError"] is False and res["structuredContent"]["withheld"] == "not_accepted"
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


# ---- 本地试用发现的问题（2026-10-02） ----


def test_suggest_excludes_the_person_already_named(svc):
    """report_blocker 的建议人选不含已经点名的人；没点名时同一个人照样会被建议。"""
    for h in ("carol", "dan"):
        svc.add_member(h, h)
    a = agent("alice", "claude_code")
    named = svc.report_blocker(a, "要一个控制台权限", need="bob", tried="问过运维")
    hs = [x["h"] for x in named["suggest"]]
    assert "bob" not in hs and "alice" not in hs and set(hs) == {"carol", "dan"}
    free = svc.report_blocker(a, "测试账号被锁", tried="重置密码没用")
    assert {x["h"] for x in free["suggest"]} == {"bob", "carol", "dan"}  # 没点名时 bob 照样在建议里


def test_withheld_reason_is_not_an_error_code_and_reading_sends_nothing(svc):
    """get_item 的扣留原因不和人类动作的错误码同名，读取也不发任何通知（本地试用：agent 读到 withheld 就说"已发到您的微信"）。"""
    from teamflow_server.errors import HTTP_STATUS
    from teamflow_server.service import WITHHELD_NOT_ACCEPTED, WITHHELD_PEER_AGENT_TEXT

    assert WITHHELD_NOT_ACCEPTED == "not_accepted"
    assert WITHHELD_NOT_ACCEPTED not in HTTP_STATUS and WITHHELD_PEER_AGENT_TEXT not in HTTP_STATUS
    before = len(svc.outbox)
    for who, oid in ((agent("bob", "codex"), "T-52"), (agent("alice", "claude_code"), "T-51"), (agent("alice", "claude_code"), "B-7")):
        item = svc.get_item(who, oid)
        assert item["withheld"] == WITHHELD_NOT_ACCEPTED, oid
    assert len(svc.outbox) == before  # 读取不触发通知


def test_agent_visible_text_does_not_name_a_channel(svc):
    """agent 看得到的常量和错误说明不提具体通知渠道（D54、D60、D61：微信只是可选通知渠道，默认邮件；人的确认在网页上）。"""
    from teamflow_server.mcp_server import DESCRIPTIONS, INSTRUCTIONS
    from teamflow_server.service import HUMAN_ONLY_MSG

    texts = [INSTRUCTIONS, *DESCRIPTIONS.values(), HUMAN_ONLY_MSG]
    for fn, args in (
        (svc.claim_task, (agent("alice", "claude_code"), "T-51")),  # needs_human
        (svc.claim_task, (agent("bob", "codex"), "T-52")),  # needs_accept
        (svc.claim_task, (agent("bob", "codex"), "T-54")),  # 已完成
        (svc.human_accept, (agent("bob", "codex"), "T-52")),  # human_only
    ):
        with pytest.raises(DomainError) as e:
            fn(*args, **({"v": 1, "sha": "x", "seq": 1, "through": 0} if fn == svc.human_accept else {}))
        texts.append(e.value.msg)
    for t in texts:
        assert "微信" not in t and "手机" not in t, t
    # withheld 单列一条、按值说：读取不会通知任何人，不能说已经通知；每个扣留原因都有对应的说法
    from teamflow_server.service import WITHHELD_REASONS

    rule = [line for line in INSTRUCTIONS.splitlines() if "withheld" in line]
    assert len(rule) == 1 and "读取不会通知任何人" in rule[0] and "Team Flow 网页" in rule[0]
    assert "needs_human" not in rule[0] and "needs_accept" not in rule[0]
    for reason in WITHHELD_REASONS:
        assert reason in rule[0], reason
    assert "不要请他再确认一次" in rule[0]  # pending_effect：已经确认过，只是还没到生效时间
    # "不替用户操作"单列一条，覆盖 needs_*、withheld、human_only（红队：原来只写在 needs_* 那一条里）
    hands_off = [line for line in INSTRUCTIONS.splitlines() if "不要自己打开或操作 Team Flow 网页" in line]
    assert len(hands_off) == 1 and "withheld" not in hands_off[0] and "needs_" not in hands_off[0]
    for word in ("接受", "认领", "转发", "确认", "通行密钥", "设备密码", "PIN"):
        assert word in hands_off[0], word
    assert "不要替用户打开网页" in HUMAN_ONLY_MSG
    assert len(INSTRUCTIONS) <= 1500


# 网页上真有的按钮（「」里的词）→ 网页 API 的动作。评论在 /comments，不走 :action
WEB_BUTTONS = {"接受": "accept", "拒绝": "decline", "认领": "claim", "开始": "start", "完成": "done",
               "取消认领": "release", "转发": "forward", "帮忙": "help", "评论": None}


def test_agent_texts_only_point_to_buttons_the_web_has(svc):
    """红队：错误说明让用户去网页上"编辑""取消""重新打开"，本地网页没有这些按钮，用户去找会扑空。
    agent 看得到的文字里「」引起来的按钮都要在网页上真有；不许笼统地说"在网页上操作 / 编辑"。"""
    import inspect
    import re

    from teamflow_server import web
    from teamflow_server.mcp_server import DESCRIPTIONS, INSTRUCTIONS
    from teamflow_server.service import HUMAN_ONLY_MSG

    src = inspect.getsource(web.web_task_action) + inspect.getsource(web.web_blocker_action)
    for label, action in WEB_BUTTONS.items():
        assert action is None or f'action == "{action}"' in src, label

    texts = [INSTRUCTIONS, *DESCRIPTIONS.values(), HUMAN_ONLY_MSG]
    bob = agent("bob", "codex")
    t = svc.create_task(bob, title="小改动", assignee="alice")["id"]
    svc.human_accept(human("alice"), t, **vs(svc, t, seq=True))  # alice 接受过：bob 的 agent 不能再改、不能取消
    for fn, kw in (
        (svc.claim_task, {"raw_id": "T-54"}),  # 已完成：不能重新打开
        (svc.update_task, {"raw_id": t, "title": "改个标题"}),  # 已被接受：agent 不能编辑
        (svc.update_task, {"raw_id": t, "status": "canceled", "note": "不做了"}),  # 已被接受：agent 不能取消
    ):
        with pytest.raises(DomainError) as e:
            fn(bob if fn == svc.update_task else agent("alice", "claude_code"), **kw)
        msg = e.value.msg
        assert "转告用户本人处理" in msg and "还没有" in msg, msg
        texts.append(msg)
    for tx in texts:
        for label in re.findall(r"「([^」]+)」", tx):
            assert label in WEB_BUTTONS, (label, tx)
        assert "网页上操作" not in tx and "网页上编辑" not in tx, tx
