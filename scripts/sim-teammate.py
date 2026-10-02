#!/usr/bin/env python3
"""扮演队友：一个人在本地试用里模拟团队里的其他人和他们的 agent。

- 队友的 agent 写入（发布、指派、报困难、评论、完成）用队友的令牌走 REST /api/v1，和真实的 agent 一样受服务端规则约束；
- 队友本人的动作（接受、认领、帮忙、确认点名）只有本人在网页上才能做，令牌做不了（硬规则 1）。这里用队友的
  一次性登录码登进网页接口，等于您替队友在网页上点按钮。所以这几个子命令只能在您自己的终端里运行：
  登录码由 python -m teamflow_server.devlogin 生成，它不给没有终端的进程（比如 agent）发码。

子命令一览：scripts/sim-teammate.py --help
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_VENV = os.path.join(os.path.dirname(_HERE), ".local", "venv")
_VPY = os.path.join(_VENV, "bin", "python")

# 用试用环境里的 Python 运行（系统自带的 python3 可能太旧，macOS 上是 3.9）
if os.path.realpath(sys.prefix) != os.path.realpath(_VENV):
    if not os.path.exists(_VPY):
        sys.stderr.write("还没有本地试用环境：请先运行 scripts/local-up.sh\n")
        sys.exit(1)
    os.execv(_VPY, [_VPY, os.path.abspath(__file__)] + sys.argv[1:])

import argparse  # noqa: E402
import json  # noqa: E402
import random  # noqa: E402
import secrets  # noqa: E402
import subprocess  # noqa: E402
import urllib.parse  # noqa: E402
import uuid  # noqa: E402

sys.dont_write_bytecode = True  # 不在 scripts/ 里留 __pycache__
sys.path.insert(0, _HERE)
import _trial  # noqa: E402

CLIENT_NAME = _trial.CLIENT_NAMES
# 样本标题和演示数据（T-49～T-54、B-7）、手册场景里让您的 agent 发布的标题都不重名，免得两件不同的事看起来像重复任务
POOL_SAMPLES = [
    ("登录页加验证码频率限制", "同一个手机号 1 分钟内最多发 1 次，10 分钟内最多 5 次。"),
    ("清理过期的功能开关", "列出上线超过 30 天的开关，确认后删掉代码分支。"),
    ("给下单接口加慢查询日志", "超过 500 毫秒的查询记一条日志，带上接口名和耗时，不记参数。"),
    ("补齐退款流程的文档", "把退款的几种状态和触发条件写进文档，配一张状态图。"),
]
ASSIGN_SAMPLES = [
    ("核对优惠券过期逻辑", "优惠券在过期当天 23:59 之前都应该能用，看一下时区处理对不对。"),
    ("查一下轮播图埋点少报", "轮播图点击的埋点在安卓上少报，看看是不是事件名写错了。"),
    ("修复导出表格的中文乱码", "用 Excel 打开导出的 CSV，中文是乱码，应该是少了 BOM。"),
]
BLOCKER_SAMPLES = [
    ("连不上测试环境的消息队列", "本地连测试环境的消息队列一直超时，怀疑白名单没有加。", "换了两个网络；确认了地址和端口；本机 telnet 端口不通。"),
    ("单测在 CI 上随机失败", "订单模块的两个用例在 CI 上偶尔失败，本地跑不出来。", "重跑了 5 次；对比了依赖版本；加了日志还没看到原因。"),
]
# 评论按对象分开：困难下面的评论像是在帮忙排查，任务下面的像是在讨论做法
COMMENT_SAMPLES = {
    "tasks": [
        "这块我之前踩过坑，重试要带幂等键，不然会重复记账。",
        "我看了一下，可以先把最慢的那个接口拆出来单独优化，别的先不动。",
    ],
    "blockers": [
        "我看了一下，是权限配置漏了一步，已经帮您加上了，您再试一次；不行把报错贴一下。",
        "这个我之前遇到过，配置改完要重启一次服务才生效，您重启后再试试。",
    ],
}
DONE_NOTE = "已完成，PR #318 已合并，测试全部通过。"


class Fail(Exception):
    pass


# ---------------------------------------------------------------------------
# 队友的 agent：令牌 + REST
# ---------------------------------------------------------------------------


class Agent:
    def __init__(self, trial, handle, client):
        self.trial, self.handle, self.client = trial, handle, client
        self.token = trial.token(handle, client)

    @property
    def label(self):
        return "%s 的 %s" % (self.handle, CLIENT_NAME[self.client])

    def call(self, method, path, body=None, ok=(200, 201)):
        headers = {"Authorization": "Bearer " + self.token, "X-Teamflow-Client": self.client, "Accept": "application/json"}
        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if method == "POST":
            headers["Idempotency-Key"] = str(uuid.uuid4())
        try:
            r = _trial.request(method, self.trial.base + path, headers=headers, body=data)
        except OSError as e:
            raise Fail("连不上服务端 %s（%s）。先运行 scripts/local-up.sh" % (self.trial.base, e)) from None
        js = r.json()
        if r.status not in ok:
            raise Fail(err_text(r.status, js))
        return js


def err_text(status, js):
    if isinstance(js, dict):
        code = js.get("error") or js.get("err") or "http_%d" % status
        msg = js.get("message") or js.get("msg") or ""
        if not msg:  # 说明里通常已经写了规则和位置；没有说明时才把结构化字段带上
            msg = "，".join("%s=%s" % (k, js[k]) for k in ("rule", "pos", "why", "field") if k in js)
        return "%s：%s" % (code, msg)
    return "HTTP %d" % status


# ---------------------------------------------------------------------------
# 队友本人：一次性登录码 → 网页会话（cookie + CSRF）
# ---------------------------------------------------------------------------


class Human:
    """以队友本人的身份调网页接口 /api/v1/web/*（和浏览器里点按钮一样：cookie、Origin、X-CSRF-Token）。

    会话存在 .local/sim/<handle>.json（0600），12 小时内复用；服务端重启后自动重新登录。"""

    def __init__(self, trial, handle):
        self.trial, self.handle = trial, handle
        self.path = _trial.local_path("sim", "%s.json" % handle)
        self.sess = None

    def _require_tty(self):
        if not sys.stdin.isatty():
            raise Fail(
                "这一步是 %s 本人在网页上的操作，要用他的登录码登进网页。请在您自己的终端里运行"
                "（登录码等于本人身份，不交给 agent）。" % self.handle
            )

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                s = json.load(f)
            if s.get("base") == self.trial.base and s.get("tf_web") and s.get("tf_csrf"):
                return s
        except (OSError, ValueError):
            pass
        return None

    def _mint_code(self):
        """python -m teamflow_server.devlogin --as <handle>：它自己检查 stdin 是不是终端。"""
        env = dict(os.environ, TEAMFLOW_STATE=_trial.local_path("state"))
        p = subprocess.run(
            [_VPY, "-m", "teamflow_server.devlogin", "--as", self.handle, "--host", "127.0.0.1", "--ttl", "2"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=30,
        )
        url = p.stdout.decode("utf-8", "replace").strip().splitlines()
        if p.returncode != 0 or not url:
            raise Fail("没能给 %s 生成登录码：%s" % (self.handle, p.stderr.decode("utf-8", "replace").strip()))
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(url[-1]).query)
        code = (q.get("code") or [""])[0]
        if not code:
            raise Fail("devlogin 的输出里没有登录码")
        return code

    def _login(self):
        self._require_tty()
        code = self._mint_code()
        form = urllib.parse.urlencode({"code": code, "as": self.handle}).encode()
        r = _trial.request("POST", self.trial.base + "/dev/login", body=form, headers={
            "Content-Type": "application/x-www-form-urlencoded", "Origin": self.trial.base})
        jar = {}
        for c in r.headers.get_all("Set-Cookie") or []:
            name, _, rest = c.partition("=")
            jar[name.strip()] = rest.split(";", 1)[0]
        if r.status not in (302, 303) or not jar.get("tf_web") or not jar.get("tf_csrf"):
            raise Fail("以 %s 的身份登录网页没成功（HTTP %d）。本地开发模式开着吗？看 .local/logs/server.log" % (self.handle, r.status))
        s = {"base": self.trial.base, "handle": self.handle, "tf_web": jar["tf_web"], "tf_csrf": jar["tf_csrf"]}
        _trial.write_private(self.path, json.dumps(s) + "\n")
        return s

    def _send(self, method, path, body=None):
        s = self.sess
        headers = {"Cookie": "tf_web=%s; tf_csrf=%s" % (s["tf_web"], s["tf_csrf"]), "Accept": "application/json"}
        data = None
        if method != "GET":
            headers.update({"Origin": self.trial.base, "X-CSRF-Token": s["tf_csrf"], "Content-Type": "application/json"})
            data = json.dumps(body or {}, ensure_ascii=False).encode("utf-8")
        return _trial.request(method, self.trial.base + path, headers=headers, body=data)

    def call(self, method, path, body=None):
        self._require_tty()
        self.sess = self.sess or self._load() or self._login()
        r = self._send(method, path, body)
        if r.status == 401:  # 会话过期或服务端重启过：重新登录一次
            self.sess = self._login()
            r = self._send(method, path, body)
        js = r.json()
        if r.status not in (200, 201):
            raise Fail(err_text(r.status, js))
        return js

    def page(self, oid):
        kind = "tasks" if oid.startswith("T-") else "blockers"
        return self.call("GET", "/api/v1/web/%s/%s" % (kind, oid))


# ---------------------------------------------------------------------------
# 子命令
# ---------------------------------------------------------------------------


def norm_id(raw, prefix=None):
    oid = raw.strip().upper()
    if oid[:2] not in ("T-", "B-") or not oid[2:].isdigit():
        raise Fail("编号要像 T-42 或 B-7：%s" % raw)
    if prefix and not oid.startswith(prefix):
        raise Fail("这里要%s编号（%s…）：%s" % ("任务" if prefix == "T-" else "困难", prefix, raw))
    return oid


def title_of(env):
    if isinstance(env, dict):
        return env.get("t") or ""
    return env or ""


def pick(samples, given):
    return given if given else random.choice(samples)


def cmd_publish_pool(trial, a):
    ag = Agent(trial, a.as_, a.client)
    title, body = (a.title, a.body) if a.title else pick(POOL_SAMPLES, None)
    res = ag.call("POST", "/api/v1/tasks", {"title": title, "body": body if a.body is None else a.body})
    print("%s 发布了待认领任务 %s「%s」。" % (ag.label, res["id"], title))
    print("接下来：您的 agent 在下次会话开始时只会看到「新的待认领」的个数；让它查一下待认领、认领 %s，"
          "它会得到 needs_human，网页「模拟通知」里出现「您的 Claude Code 想开始 %s，点这里认领」（用 Codex 就写 Codex），"
          "点开看过正文后点「认领」。" % (res["id"], res["id"]))


def cmd_assign_me(trial, a):
    ag = Agent(trial, a.as_, a.client)
    title, body = (a.title, a.body) if a.title else pick(ASSIGN_SAMPLES, None)
    res = ag.call("POST", "/api/v1/tasks", {"title": title, "body": body if a.body is None else a.body, "assignee": trial.me})
    print("%s 请您协作：%s「%s」，状态是待接受。" % (ag.label, res["id"], title))
    print("接下来：网页「待我处理」和「模拟通知」里会出现这条；打开详情页看过正文后点「接受」。"
          "接受之前，您的 agent 读正文只会拿到 withheld（not_accepted）。")


def cmd_blocker_need_me(trial, a):
    ag = Agent(trial, a.as_, a.client)
    title, detail, tried = pick(BLOCKER_SAMPLES, None)
    body = {"title": a.title or title, "detail": detail, "tried": tried, "need": trial.me}
    if a.task:
        body["task"] = norm_id(a.task, "T-")
    res = ag.call("POST", "/api/v1/blockers", body)
    print("%s 报告了困难 %s「%s」，提议请您帮忙（need_state=%s）。" % (ag.label, res["id"], body["title"], res.get("need_state")))
    print("agent 的点名要 %s 本人确认后才会通知您。扮演 %s 确认：scripts/sim-teammate.py confirm-as-owner %s"
          % (a.as_, a.as_, res["id"]))


def owner_of(trial, bid, fallback):
    ag = Agent(trial, fallback, "claude_code")
    js = ag.call("GET", "/api/v1/blockers/%s" % bid)
    by = (js.get("t") or {}).get("by") if isinstance(js.get("t"), dict) else None
    return by or fallback


def cmd_confirm_as_owner(trial, a):
    bid = norm_id(a.id, "B-")
    owner = a.as_ if a.as_given else owner_of(trial, bid, a.as_)
    if owner == trial.me:
        raise Fail("%s 是您自己报的，请在网页上点「确认」。" % bid)
    if owner not in trial.mates:
        raise Fail("%s 的提出人是 %s，不是模拟队友。" % (bid, owner))
    h = Human(trial, owner)
    res = h.call("POST", "/api/v1/web/blockers/%s:ask" % bid)
    print("%s 本人确认了点名（%s，need_state=%s）。" % (owner, bid, res.get("need_state")))
    print("接下来：您的「模拟通知」里会出现「%s 请您帮忙看 %s」；打开 %s 看过之后点「认领」去帮忙。" % (owner, bid, bid))


def cmd_comment(trial, a):
    oid = norm_id(a.id)
    ag = Agent(trial, a.as_, a.client)
    kind = "tasks" if oid.startswith("T-") else "blockers"
    ag.call("POST", "/api/v1/%s/%s/comments" % (kind, oid), {"body": a.body or random.choice(COMMENT_SAMPLES[kind])})
    print("%s 在 %s 上写了一条评论。" % (ag.label, oid))
    print("接下来：您的 agent 只会看到「%s 有 %s 评论 1 条，待您转发」，读不到内容；"
          "在网页上看过之后点「转发给我的 agent」，它才读得到。" % (oid, ag.label))


def cmd_accept(trial, a):
    tid = norm_id(a.id, "T-")
    h = Human(trial, a.as_)
    pg = h.page(tid)["page"]
    res = h.call("POST", "/api/v1/web/tasks/%s:accept" % tid, {k: pg[k] for k in ("v", "sha", "seq", "through")})
    print("%s 本人接受了 %s（状态 %s）。之后他的 agent 才能读正文、开始做。" % (a.as_, tid, res.get("st")))
    return res


def cmd_claim(trial, a):
    tid = norm_id(a.id, "T-")
    h = Human(trial, a.as_)
    pg = h.page(tid)["page"]
    h.call("POST", "/api/v1/web/tasks/%s:claim" % tid, {k: pg[k] for k in ("v", "sha", "through")})
    ag = Agent(trial, a.as_, a.client)
    res = ag.call("POST", "/api/v1/tasks/%s:claim" % tid)
    print("%s 本人认领了 %s，%s 开始做（状态 %s）。" % (a.as_, tid, ag.label, res.get("st")))


def cmd_help(trial, a):
    bid = norm_id(a.id, "B-")
    h = Human(trial, a.as_)
    pg = h.page(bid)["page"]
    h.call("POST", "/api/v1/web/blockers/%s:help" % bid, {k: pg[k] for k in ("v", "sha", "through")})
    print("%s 本人认领了 %s，来帮忙了。想让他的 agent 留个评论：scripts/sim-teammate.py comment %s --as %s"
          % (a.as_, bid, bid, a.as_))


def cmd_done(trial, a):
    tid = norm_id(a.id, "T-")
    ag = Agent(trial, a.as_, a.client)
    t = ag.call("GET", "/api/v1/tasks/%s" % tid)
    if t.get("who") != a.as_:
        raise Fail("%s 的负责人是 %s，不是 %s。先让您的 agent 把它指派给 %s（create_task 带 assignee）。"
                   % (tid, t.get("who") or "（没有）", a.as_, a.as_))
    st = t.get("st")
    if st == "pending":
        print("%s 还没接受 %s，先替他在网页上点「接受」……" % (a.as_, tid))
        cmd_accept(trial, argparse.Namespace(id=tid, as_=a.as_))
        st = "todo"
    if st in ("todo",):
        ag.call("POST", "/api/v1/tasks/%s:claim" % tid)
    elif st not in ("doing",):
        raise Fail("%s 现在是 %s，没法完成。" % (tid, st))
    res = ag.call("POST", "/api/v1/tasks/%s:done" % tid, {"note": a.note or DONE_NOTE})
    print("%s 完成了 %s（状态 %s）。" % (ag.label, tid, res.get("st")))
    print("接下来：您的「模拟通知」里会有「%s 接受了 %s」和「您请 %s 做的 %s 已完成」；让您的 agent 看一下收件箱，"
          "replies 里有这两条（本地版会话开始的摘要里不列回音）。" % (a.as_, tid, a.as_, tid))


def cmd_scan_test(trial, a):
    oid = norm_id(a.id)
    ag = Agent(trial, a.as_, a.client)
    kind = "tasks" if oid.startswith("T-") else "blockers"
    # 像腾讯云 SecretId 的样本：运行时拼出来，仓库里不出现整串
    fake = "AK" + "ID" + "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(32))
    try:
        ag.call("POST", "/api/v1/%s/%s/comments" % (kind, oid), {"body": "配置是 %s，您试试" % fake})
    except Fail as e:
        print("服务端拦下了 %s 贴进评论的疑似密钥：%s" % (ag.label, e))
        print("被拦下的文字没有写进看板，也不会出现在任何人的 agent 里。")
        return
    print("注意：这条带疑似密钥的评论没有被拦下，请把这个结果反馈给开发。")


def cmd_status(trial, a):
    ag = Agent(trial, a.as_, a.client)
    st = ag.call("GET", "/api/v1/status")
    rows = ag.call("GET", "/api/v1/tasks?view=all&limit=50").get("rows", [])
    print("看板（以 %s 的视角；标题是看板数据）" % ag.label)
    c = st.get("counts") or {}
    print("  计数：待认领 %s · 待接受 %s · 待开始 %s · 进行中 %s · 困难 %s"
          % (c.get("pool", 0), c.get("pending", 0), c.get("todo", 0), c.get("doing", 0), c.get("blockers", 0)))
    print("  大家在做什么：")
    others = st.get("others") or []
    for o in others:
        sess = {s.get("task"): s for s in o.get("sess") or []}
        doing = []
        for tid in o.get("doing") or []:
            s = sess.get(tid)
            if s:
                doing.append("%s（%s · 会话 %s）" % (tid, CLIENT_NAME.get(s.get("client"), s.get("client")), s.get("s")))
            else:
                doing.append(tid)
        line = "在做 " + "、".join(doing) if doing else "没有进行中的任务"
        if o.get("blockers"):
            line += "；报告的困难 " + "、".join(o["blockers"])
        print("    %s · %s" % (o.get("h"), line))
    labels = {"pool": "待认领", "pending": "待接受", "todo": "待开始", "doing": "进行中", "done": "已完成", "canceled": "已取消"}
    if rows:
        print("  任务：")
        for r in rows:
            who = " · %s" % r["who"] if r.get("who") else ""
            blk = " · 困难 %s" % "、".join(r["blk"]) if r.get("blk") else ""
            print("    %s %s「%s」%s%s · %s" % (r["id"], labels.get(r.get("st"), r.get("st")), title_of(r.get("t")), who, blk, r.get("upd", "")))
    print("  网页上「模拟通知」里能看到发给您的通知；队友收到的：scripts/sim-teammate.py notifications --as <队友>")


def cmd_notifications(trial, a):
    h = Human(trial, a.as_)
    js = h.call("GET", "/api/v1/web/notifications?limit=10")
    items = js.get("items") or []
    print("%s 的模拟通知（最新 %d 条，共 %s 条）：" % (a.as_, len(items), js.get("total", len(items))))
    for it in items:
        print("  %s  %s  %s" % (it.get("at") or "", it.get("kind_text") or it.get("kind"), it.get("text") or ""))
    if not items:
        print("  （还没有）")


COMMANDS = [
    ("publish-pool", cmd_publish_pool, "队友的 agent 发布一个待认领任务（场景 1）", 0, []),
    ("assign-me", cmd_assign_me, "队友的 agent 指派给您一个任务，请您协作（场景 2）", 0, []),
    ("blocker-need-me", cmd_blocker_need_me, "队友的 agent 报一个困难并提议请您帮忙（场景 4）", 1, ["task"]),
    ("confirm-as-owner", cmd_confirm_as_owner, "扮演报困难的队友本人，在网页上确认点名（场景 4）", 1, ["id"]),
    ("comment", cmd_comment, "队友的 agent 在任务或困难上写一条评论（场景 4）", 0, ["id", "body"]),
    ("done", cmd_done, "队友完成您请他做的任务；还没接受的先替他接受（场景 5）", 0, ["id", "note"]),
    ("accept", cmd_accept, "扮演队友本人接受您指派给他的任务（场景 2 反过来）", 0, ["id"]),
    ("claim", cmd_claim, "扮演队友本人认领您发布的待认领任务，他的 agent 接着开始做（场景 1 反过来）", 0, ["id"]),
    ("help", cmd_help, "扮演队友本人认领您的困难，来帮忙（场景 4 反过来）", 0, ["id"]),
    ("scan-test", cmd_scan_test, "队友的 agent 在评论里贴一段像密钥的字符串，看服务端拦截（场景 6）", 0, ["id"]),
    ("status", cmd_status, "打印当前看板（以队友 agent 的视角）", 0, []),
    ("notifications", cmd_notifications, "看某个队友收到的模拟通知（正式版按他选的渠道发邮件或微信）", 0, []),
]


def build_parser(trial):
    p = argparse.ArgumentParser(
        prog="scripts/sim-teammate.py",
        description="扮演队友和他们的 agent，在本地试用里走一遍规划 3.2 的场景。队友：%s；您：%s。"
        % ("、".join(trial.mates), trial.me),
        epilog="确认点名、接受、认领、帮忙、看模拟通知是队友本人的操作，要在您自己的终端里运行。",
    )
    sub = p.add_subparsers(dest="cmd", metavar="<子命令>")
    for name, fn, helptext, mate_idx, extra in COMMANDS:
        s = sub.add_parser(name, help=helptext, description=helptext)
        default_as = trial.mates[min(mate_idx, len(trial.mates) - 1)]
        s.add_argument("--as", dest="as_", default=None, help="扮演哪位队友（默认 %s）" % default_as)
        s.add_argument("--client", choices=("claude", "codex"), help="队友用的 agent（默认按队友轮流：第 1 位 Claude Code，第 2 位 Codex）")
        if "id" in extra:
            s.add_argument("id", help="编号，如 T-42 或 B-7")
        if name in ("publish-pool", "assign-me", "blocker-need-me"):
            s.add_argument("--title", help="标题（agent 写的标题不能带网址、路径、命令）")
        if name in ("publish-pool", "assign-me"):
            s.add_argument("--body", help="内容")
        if "body" in extra:
            s.add_argument("--body", help="评论内容")
        if "task" in extra:
            s.add_argument("--task", help="挂在哪个任务上，如 T-42")
        if "note" in extra:
            s.add_argument("--note", help="完成说明")
        s.set_defaults(fn=fn, mate_idx=mate_idx)
    return p


def main(argv):
    trial = _trial.Trial()
    if not trial.mates:
        print("local.env 里没有模拟队友，请重跑 scripts/local-up.sh", file=sys.stderr)
        return 1
    p = build_parser(trial)
    a = p.parse_args(argv)
    if not getattr(a, "cmd", None):
        p.print_help()
        return 0
    a.as_given = a.as_ is not None
    if a.as_ is None:
        a.as_ = trial.mates[min(a.mate_idx, len(trial.mates) - 1)]
    a.as_ = a.as_.strip().lstrip("@").lower()
    if a.as_ not in trial.mates:
        print("%s 不是模拟队友（可选：%s）。您本人的操作请在网页上点。" % (a.as_, "、".join(trial.mates)), file=sys.stderr)
        return 2
    if a.client:
        a.client = "claude_code" if a.client == "claude" else "codex"
    else:
        a.client = ("claude_code", "codex")[trial.mates.index(a.as_) % 2]
    if not _trial.health(trial.base):
        print("服务端没有在 %s 运行：先运行 scripts/local-up.sh" % trial.base, file=sys.stderr)
        return 1
    try:
        a.fn(trial, a)
    except Fail as e:
        print("没成功：%s" % e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
