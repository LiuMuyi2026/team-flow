"""种子数据：alice、bob 两个成员和几条典型任务，方便验证。

结果（以 alice 视角）：
- T-49 bob 自己的任务，bob 的 Codex 在做；B-7 挂在上面，点名 alice（已确认）。
- T-50 alice 在做（她的 Claude Code 写过一条进度）。
- T-51 待认领，bob 的 Codex 发布：alice 的 agent 认领会得到 needs_human；正文对 alice withheld。
- T-52 alice 的 Claude Code 指派给 bob，待 bob 接受：bob 的 agent 读正文得到 withheld，认领得到 needs_accept。
- T-53 待认领，alice 的 Claude Code 发布：alice 的 agent 可以直接认领。
- T-54 bob 已完成。
- B-7 bob 的 Codex 报告的困难，bob 在手机上确认了点名 alice；上面有 bob 的 Codex 写的一条评论（对 alice 是 peer_agent，待转发）。

TEAMFLOW_DEV_TOKENS 里出现、但上面没有的 handle（比如本地试用时您自己的 handle 和模拟的队友）也登记成成员，
名字就用 handle；他们一开始没有任何任务。
"""

from __future__ import annotations

from datetime import timedelta

from . import config
from .service import HANDLE_RE, Actor, Service


def seed(svc: Service) -> None:
    real_clock = svc.clock
    base = real_clock()
    offset = {"v": timedelta(hours=6)}
    svc.clock = lambda: base - offset["v"]

    def at(**kw: float) -> None:
        offset["v"] = timedelta(**kw)

    try:
        svc.reset()
        svc.add_member("alice", "Alice", ["alice@example.com"])
        svc.add_member("bob", "Bob", ["bob@example.com"])
        svc.add_project("tf", "Team Flow", ["*team-flow*", "*team_flow*"])
        svc.add_project("pay", "支付", ["*payment*"])
        svc.next_task_no = 49
        svc.next_blocker_no = 7

        alice_h = Actor("alice", "human", None, None, "seed")
        bob_h = Actor("bob", "human", None, None, "seed")
        alice_cc = Actor("alice", "agent", "claude_code", "seed_alice_cc", "seed")
        bob_cx = Actor("bob", "agent", "codex", "seed_bob_cx", "seed")

        at(hours=5)
        svc.create_task(bob_h, "测试库迁移到新实例", "把 staging 测试库迁到新实例，迁完更新连接配置。", assignee="bob", project="tf")
        svc.claim_task(bob_cx, "T-49")

        at(hours=4)
        svc.create_task(alice_h, "首页骨架屏", "首页加载时先出骨架屏，接口回来再替换。", assignee="alice", project="tf")
        svc.claim_task(alice_cc, "T-50")
        at(hours=3, minutes=30)
        svc.update_task(alice_cc, "T-50", note="骨架屏组件已拆出来，正在接首页接口。")

        at(hours=3)
        svc.create_task(bob_cx, "首页加载慢", "首屏在 4G 下要 3 秒以上，先查接口瀑布再看图片体积。", project="tf")

        at(hours=2)
        svc.create_task(
            alice_cc,
            "支付回调重试",
            "回调失败时按指数退避重试 3 次，超过后记日志并提醒值班的人。",
            assignee="bob",
            project="pay",
        )

        at(hours=1, minutes=30)
        svc.create_task(alice_cc, "整理接口错误码", "把各接口的错误码收拢成一张表，写进文档。", project="tf")

        at(hours=1, minutes=20)
        svc.create_task(bob_h, "升级前端依赖", "升级到最新的小版本。", assignee="bob", project="tf")
        svc.claim_task(bob_cx, "T-54")
        at(hours=1, minutes=10)
        svc.update_task(bob_cx, "T-54", status="done", note="已升级并通过全部测试。")

        at(hours=1)
        svc.report_blocker(
            bob_cx,
            "测试库连不上",
            detail="新实例连接超时，怀疑安全组没有放行。",
            tried="重试 3 次；换了网络；本机 telnet 端口不通。",
            task="T-49",
            need="alice",
        )
        at(minutes=55)
        svc.human_ask(bob_h, "B-7")
        at(minutes=40)
        svc.comment(bob_cx, "B-7", "已确认是安全组规则的问题，需要有控制台权限的人加一条入站规则。")

        for h in config.token_handles():
            if h not in svc.members and HANDLE_RE.fullmatch(h):
                svc.add_member(h, h)
    finally:
        svc.clock = real_clock
