"""兜底写命令：`teamflow note` / `teamflow done` / `teamflow block`。

MCP 不可用时（plan 6.8），agent 或成员在终端里用它们写进度、完成任务、报告困难。都走 REST（跨包约定）：

- `POST /api/v1/tasks/{id}:note`  {"note": "..."}
- `POST /api/v1/tasks/{id}:done`  {"note": "..."}
- `POST /api/v1/blockers`         {"title", "detail?", "tried?", "task?", "need?"}

鉴权同其他 REST：`Authorization: Bearer <PAT>` + `X-Teamflow-Client`，每次带新的 `Idempotency-Key`
（网络错误时用同一个键重试一次，服务端会重放而不是重复写）。成功返回 `{id, st}`；
失败是 4xx JSON `{"error": "<code>", "message": "..."}`（也认 M0 服务端的 `{"err", "msg"}`）。

输出：默认一两行精简中文；`--json` 输出一行机器可读的 JSON（成功 `{"ok": true, ...}`，失败 `{"ok": false, "error": ...}`）。
错误行以错误码开头（如 `needs_accept：…`），和 MCP 工具的 isError 文本一致，server instructions 按错误码下的指令才对得上。
返回码：0 成功；1 服务端拒绝、网络或凭据问题；2 参数不对（没发请求）。
"""

import os
import sys

from teamflow import common

NOTE_MAX = 500  # 服务端 UpdateIn.note
TITLE_MAX = 120  # BlockerIn.title
DETAIL_MAX = 2000
TRIED_MAX = 1000
TIMEOUT = 5.0
MESSAGE_MAX = 200

# 服务端的任务状态标签（Task.label）→ 中文；不认识的不显示
ST_LABEL = {
    "pool": "待认领",
    "pending": "待接受",
    "todo": "待开始",
    "doing": "进行中",
    "done": "已完成",
    "canceled": "已取消",
}

# 服务端没给说明时用的兜底文字（错误码见 server/teamflow_server/errors.py）
ERROR_TEXT = {
    "needs_human": "这个操作要您本人在手机微信里处理，已发到您的微信。",
    "needs_accept": "要等本人在手机上接受后才能继续，已发到微信。",
    "human_only": "这个操作只能由本人在手机微信里完成，agent 和命令行都不行。",
    "not_allowed": "您的 agent 没有权限做这个操作。",
    "not_found": "找不到这一项。",
    "invalid": "请求内容不合法。",
    "secret_detected": "内容里像是有密钥或个人信息，没有提交；去掉后重试。",
    "rate_limited": "提交得太频繁了，请稍后再试。",
    "taken": "已经有人认领了。",
    "conflict": "和别的操作冲突了，请稍后重试。",
    "too_many": "内容太长或数量太多。",
    "unauthorized": "token 无效或已吊销，请重新运行 teamflow setup。",
}


class UsageError(Exception):
    pass


# ---------------------------------------------------------------- 参数


def detect_client(env=None) -> str:
    """没给 --client 时按环境猜：只有 Codex 的会话变量就是 codex，其余按 claude。

    Claude Code 给 Bash 设 CLAUDECODE=1；Codex 给 shell 设 CODEX_SESSION_ID / CODEX_THREAD_ID
    （codex-rs/core/src/exec_env.rs）。嵌套时两边的变量都在，分不清，按 claude 处理，可用 --client 指定。
    """
    env = os.environ if env is None else env
    if env.get("CLAUDECODE") != "1" and (env.get("CODEX_SESSION_ID") or env.get("CODEX_THREAD_ID")):
        return "codex"
    return "claude"


def task_id(raw) -> str:
    from teamflow import inbox

    s = (raw or "").strip()
    if s[:2] == "t-":
        s = "T-" + s[2:]
    if not (inbox.valid_id(s) and s[0] == "T"):
        raise UsageError("任务编号要写成 T-42 这样（收到 %r）" % (raw if len(str(raw)) <= 20 else str(raw)[:20] + "…"))
    return s


def handle(raw) -> str:
    from teamflow import inbox

    s = (raw or "").strip().lstrip("@")
    if not inbox.valid_handle(s):
        raise UsageError("--need 要写对方的 handle，小写字母开头，2–16 位字母、数字或下划线")
    return s


def text(raw, what: str, limit: int, required: bool = True):
    s = (raw or "").strip()
    if not s:
        if required:
            raise UsageError("%s不能为空" % what)
        return None
    if len(s) > limit:
        raise UsageError("%s最多 %d 字（现在 %d 字）" % (what, limit, len(s)))
    return s


# ---------------------------------------------------------------- 请求


def _clean(s, limit=MESSAGE_MAX) -> str:
    """服务端说明只留一行可见字符，截到 limit。"""
    out = []
    for c in str(s):
        o = ord(c)
        if c in "\r\n\t":
            out.append(" ")
        elif o < 0x20 or o == 0x7F or 0x80 <= o < 0xA0 or 0x200B <= o <= 0x200F or 0x202A <= o <= 0x202E \
                or 0x2066 <= o <= 0x2069 or o in (0x061C, 0xFEFF, 0x2028, 0x2029):
            continue
        else:
            out.append(c)
    s = " ".join("".join(out).split())
    return s if len(s) <= limit else s[: limit - 1] + "…"


def _code(x) -> str | None:
    if isinstance(x, str) and 0 < len(x) <= 32 and all(c.islower() and c.isascii() or c == "_" for c in x):
        return x
    return None


def _status_code(status: int) -> str:
    if status == 401:
        return "unauthorized"
    if status == 404:
        return "not_found"
    if status == 429:
        return "rate_limited"
    if status == 422:
        return "invalid"
    if status >= 500:
        return "server_error"
    return "http_%d" % status


class Result:
    def __init__(self, ok: bool, status: int = 0, data=None, error: str | None = None, message: str = ""):
        self.ok = ok
        self.status = status
        self.data = data if isinstance(data, dict) else {}
        self.error = error
        self.message = message


class CredFileError(common.CredError):
    """凭据文件本身读不到（不存在、格式不对、被沙箱屏蔽）。"""


def call(cred: str, client: str, ws_slug: str | None, path: str, body: dict) -> Result:
    """发一个 POST；凭据问题抛 common.CredError（文件读不到时是 CredFileError），其余都变成 Result。"""
    from teamflow import net

    try:
        creds = common.load_creds(cred)
    except common.CredError as e:
        raise CredFileError(str(e)) from None
    wss = creds["workspaces"]
    if ws_slug:
        if not isinstance(wss.get(ws_slug), dict):
            raise common.CredError("凭据文件里没有 workspace %s" % ws_slug)
        ws = wss[ws_slug]
    else:
        from teamflow import gitinfo

        cwd = os.getcwd()
        _, ws = common.select_workspace(creds, cwd, gitinfo.session_info(cwd).get("repo"))
    token = common.token_for(ws, client)
    base = common.api_base(ws)
    headers = net.api_headers(token, common.WIRE_CLIENT[client], idem=os.urandom(16).hex())
    err = None
    for _ in range(2):  # 网络错误用同一个 Idempotency-Key 重试一次
        try:
            status, _, raw = net.request("POST", base + path, headers=headers, body=body, timeout=TIMEOUT)
            break
        except net.NetError as e:
            err = e
    else:
        return Result(False, 0, error="network", message="连不上服务端（%s），没有提交，请稍后重试。" % _clean(err, 120))
    data = net.parse_json(raw)
    data = data if isinstance(data, dict) else {}
    if 200 <= status < 300:
        return Result(True, status, data)
    code = _code(data.get("error")) or _code(data.get("err")) or _status_code(status)
    msg = data.get("message")
    if not isinstance(msg, str):
        msg = data.get("msg")
    msg = _clean(msg) if isinstance(msg, str) and msg.strip() else ""
    if not msg:
        msg = ERROR_TEXT.get(code) or "服务端返回 %d。" % status
    return Result(False, status, data, error=code, message=msg)


# ---------------------------------------------------------------- 输出


def _ok_fields(data: dict) -> dict:
    """只留白名单字段：编号和状态枚举。"""
    from teamflow import inbox

    out = {}
    i = inbox.valid_id(data.get("id"))
    if i:
        out["id"] = i
    for k in ("st", "need_state"):
        v = _code(data.get(k))
        if v:
            out[k] = v
    return out


def _emit(cmd: str, res: Result, as_json: bool, ok_text) -> int:
    if as_json:
        if res.ok:
            obj = {"ok": True}
            obj.update(_ok_fields(res.data))
        else:
            obj = {"ok": False, "error": res.error, "status": res.status, "message": res.message}
        sys.stdout.write(common.dumps(obj) + "\n")
        return 0 if res.ok else 1
    if res.ok:
        sys.stdout.write(ok_text(_ok_fields(res.data)) + "\n")
        return 0
    sys.stderr.write("teamflow %s：%s：%s\n" % (cmd, res.error, res.message))
    return 1


def _usage_fail(cmd: str, msg: str, as_json: bool) -> int:
    if as_json:
        sys.stdout.write(common.dumps({"ok": False, "error": "usage", "status": 0, "message": msg}) + "\n")
    else:
        sys.stderr.write("teamflow %s：%s\n" % (cmd, msg))
    return 2


def _cred_fail(cmd: str, e: Exception, as_json: bool) -> int:
    msg = str(e)
    if isinstance(e, CredFileError):
        # plan 6.4 的加固会让沙箱里的命令读不到凭据文件（M0 评审 m5）
        msg += "。如果是在 Claude Code 的沙箱里运行，凭据文件会被屏蔽，请在您自己的终端里运行这条命令"
    if as_json:
        sys.stdout.write(common.dumps({"ok": False, "error": "credentials", "status": 0, "message": msg}) + "\n")
    else:
        sys.stderr.write("teamflow %s：%s\n" % (cmd, msg))
    return 1


def _st_text(f: dict) -> str:
    label = ST_LABEL.get(f.get("st") or "")
    return "，当前状态：%s" % label if label else ""


def run(ns) -> int:
    cmd = ns.cmd
    as_json = bool(getattr(ns, "json", False))
    try:
        if cmd in ("note", "done"):
            tid = task_id(ns.task)
            note = text(ns.text, "进度" if cmd == "note" else "完成说明", NOTE_MAX)
            path = "/api/v1/tasks/%s:%s" % (tid, cmd)
            body = {"note": note}
        else:
            tid = task_id(ns.task) if ns.task else None
            body = {"title": text(ns.title, "标题", TITLE_MAX)}
            for k, v in (
                ("detail", text(ns.detail, "详情", DETAIL_MAX, required=False)),
                ("tried", text(ns.tried, "已经试过的", TRIED_MAX, required=False)),
                ("task", tid),
                ("need", handle(ns.need) if ns.need else None),
            ):
                if v:
                    body[k] = v
            path = "/api/v1/blockers"
    except UsageError as e:
        return _usage_fail(cmd, str(e), as_json)

    client = ns.client or detect_client()
    try:
        res = call(ns.cred, client, ns.ws, path, body)
    except common.CredError as e:
        return _cred_fail(cmd, e, as_json)

    if cmd == "note":
        return _emit(cmd, res, as_json, lambda f: "已记录 %s 的进度%s。" % (f.get("id") or tid, _st_text(f)))
    if cmd == "done":
        return _emit(cmd, res, as_json, lambda f: "%s 已标记为完成。" % (f.get("id") or tid))

    def blocked(f):
        bid = f.get("id")
        line = "已报告困难 %s。" % bid if bid else "已报告困难。"
        if body.get("need"):
            line += "请 %s 帮忙只是提议，等您在手机上确认后才会通知对方。" % body["need"]
        return line

    return _emit(cmd, res, as_json, blocked)
