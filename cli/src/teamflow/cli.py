"""命令入口。

hook / mcp-headers / flush 走手写参数解析的快速路径（不导入 argparse），
其余命令和 --help 走 argparse。
"""

import os
import sys

FAST = ("hook", "mcp-headers", "flush")
HOOK_EVENTS = ("session-start", "prompt", "stop", "session-end")


def _parse_fast(args, valued=("--client", "--cred", "--ws"), flags=("--refresh",)):
    pos, opts = [], {}
    i = 0
    while i < len(args):
        a = args[i]
        if a in valued:
            if i + 1 >= len(args):
                raise ValueError("%s 缺少参数值" % a)
            opts[a[2:]] = args[i + 1]
            i += 2
            continue
        if "=" in a and a.split("=", 1)[0] in valued:
            k, v = a.split("=", 1)
            opts[k[2:]] = v
        elif a in flags:
            opts[a[2:]] = True
        elif a.startswith("-"):
            raise ValueError("未知参数 %s" % a)
        else:
            pos.append(a)
        i += 1
    return pos, opts


def _hook(args) -> int:
    from teamflow import common

    try:
        pos, opts = _parse_fast(args)
        event = pos[0] if pos else ""
        client = opts.get("client", "")
        cred = opts.get("cred", "")
        if event not in HOOK_EVENTS or client not in common.CLIENTS:
            raise ValueError("hook 参数无效：%r --client %r" % (event, client))
        if not os.path.isabs(cred):
            raise ValueError("--cred 必须是绝对路径")
    except BaseException:  # noqa: BLE001 - hook 永远 fail-open
        common.log_exc("hook args")
        return 0
    from teamflow import hooks

    return hooks.run(event, client, cred)


def _mcp_headers(args) -> int:
    from teamflow import common

    try:
        pos, opts = _parse_fast(args)
    except ValueError as e:
        sys.stderr.write("teamflow mcp-headers：%s\n" % e)
        return 2
    client = opts.get("client", "")
    cred = opts.get("cred", "")
    if pos or client not in common.CLIENTS or not os.path.isabs(cred):
        sys.stderr.write("用法：teamflow mcp-headers --client claude|codex --cred <绝对路径>\n")
        return 2
    from teamflow import headers

    return headers.run(client, cred, opts.get("ws"))


def _flush(args) -> int:
    from teamflow import common

    try:
        pos, opts = _parse_fast(args)
        if pos:
            raise ValueError("多余的参数 %s" % pos)
        client = opts.get("client")
        if client is not None and client not in common.CLIENTS:
            raise ValueError("--client 只能是 claude 或 codex")
    except ValueError as e:
        sys.stderr.write("teamflow flush：%s\n" % e)
        return 2
    from teamflow import hooks, spool

    rc = 0
    try:
        res = spool.flush()
        if res.get("locked"):
            common.log("flush: another flush holds the lock")
    except Exception:  # noqa: BLE001
        common.log_exc("flush")
        rc = 1
    if opts.get("refresh"):
        cred = opts.get("cred") or default_cred()
        clients = [client] if client else list(common.CLIENTS)
        for c in clients:
            try:
                spool.refresh(cred, c, opts.get("ws"))
            except common.CredError as e:
                if client:  # 只在明确指定了客户端时才算错
                    common.log("refresh %s: %s" % (c, e))
                    rc = 1
            except Exception:  # noqa: BLE001
                common.log_exc("refresh %s" % c)
                rc = 1
    try:
        hooks.prune_sessions()
    except Exception:  # noqa: BLE001
        pass
    return rc


def default_cred(home: str | None = None) -> str:
    home = home or os.path.expanduser("~")
    return os.path.join(home, ".config", "teamflow", "credentials.json")


# ---------------------------------------------------------------- argparse 慢路径


def _common_opts(p, ws=True):
    p.add_argument("--client", choices=("claude", "codex"),
                   help="用哪个 agent 的 token（默认按环境判断：在 Codex 里是 codex，其余是 claude）")
    p.add_argument("--cred", help="credentials.json 的绝对路径")
    if ws:
        p.add_argument("--ws", help="指定 workspace（默认按当前目录匹配，匹配不到用 default）")
        p.add_argument("--json", action="store_true", help="输出一行机器可读的 JSON")


def _build_parser():
    import argparse

    from teamflow import __version__

    p = argparse.ArgumentParser(
        prog="teamflow",
        description="Team Flow 命令行：Claude Code / Codex 的 hook 执行体、MCP 凭据 helper 和兜底命令。",
    )
    p.add_argument("--version", action="version", version="teamflow " + __version__)
    sub = p.add_subparsers(dest="cmd", metavar="<命令>")

    h = sub.add_parser("hook", help="hook 执行体（由 Claude Code / Codex 调用，永远 fail-open）")
    h.add_argument("event", choices=HOOK_EVENTS)
    h.add_argument("--client", choices=("claude", "codex"), required=True)
    h.add_argument("--cred", required=True, help="credentials.json 的绝对路径")

    m = sub.add_parser("mcp-headers", help="输出 MCP 请求头（headersHelper / http_headers_helper 调用）")
    m.add_argument("--client", choices=("claude", "codex"), required=True)
    m.add_argument("--cred", required=True, help="credentials.json 的绝对路径")
    m.add_argument("--ws", help="指定 workspace（默认按当前目录匹配，匹配不到用 default）")

    f = sub.add_parser("flush", help="上传本地 spool；--refresh 同时刷新收件箱缓存")
    f.add_argument("--refresh", action="store_true")
    f.add_argument("--client", choices=("claude", "codex"))
    f.add_argument("--cred", help="credentials.json 的绝对路径")
    f.add_argument("--ws")

    i = sub.add_parser("inbox", help="在终端查看与您有关的看板事项（只显示编号和计数）")
    _common_opts(i, ws=False)

    n = sub.add_parser("note", help="给任务写一句进度（MCP 不可用时的兜底）",
                       description="给任务写一句进度，200 字以内为宜（最多 500 字）。例：teamflow note T-42 \"接口联调通过\"")
    n.add_argument("task", help="任务编号，如 T-42")
    n.add_argument("text", help="一句话进度")
    _common_opts(n)

    dn = sub.add_parser("done", help="把任务标记为完成，附一句说明（MCP 不可用时的兜底）",
                        description="把任务标记为完成。例：teamflow done T-42 \"做了什么 + PR 链接\"")
    dn.add_argument("task", help="任务编号，如 T-42")
    dn.add_argument("text", help="做了什么，最好带上 PR 链接")
    _common_opts(dn)

    b = sub.add_parser("block", help="报告困难（MCP 不可用时的兜底）",
                       description="报告困难：卡住超过 20 分钟，或需要别人做决定、给权限。"
                       "--need 只是提议请谁帮忙，用户在手机上确认后才通知对方。"
                       "例：teamflow block --task T-42 --title \"测试库连不上\" --need zhang")
    b.add_argument("--title", required=True, help="一句话说清卡在哪（最多 120 字）")
    b.add_argument("--task", help="相关任务编号，如 T-42")
    b.add_argument("--need", help="想请谁帮忙（对方的 handle）；只是提议")
    b.add_argument("--detail", help="详情（最多 2000 字）")
    b.add_argument("--tried", help="已经试过什么（最多 1000 字）")
    _common_opts(b)

    c = sub.add_parser("claude-flags", help="输出无头运行 claude -p 需要的参数")
    c.add_argument("--home", help="用这个目录代替 HOME（测试用）")
    c.add_argument("--quoted", action="store_true", help="输出 shell 引号形式，给 eval 用")

    s = sub.add_parser("setup", help="生成 Claude Code 与 Codex 的 hooks、MCP 配置")
    s.add_argument("--home", help="用这个目录代替 HOME（测试和实验必须用临时目录）")
    s.add_argument("--dry-run", action="store_true", help="不写文件，只打印 teamflow 相关配置的改动前→改动后（密钥、邮箱一律遮蔽）")
    s.add_argument("--cred", help="credentials.json 的绝对路径（默认 <home>/.config/teamflow/credentials.json）")
    s.add_argument("--api-url", help="凭据文件不存在时写入的服务地址（默认 http://127.0.0.1:8100）")
    s.add_argument("--workspace", default="team", help="凭据文件不存在时写入的 workspace 名")
    s.add_argument("--bin", help="teamflow 可执行文件的绝对路径（默认取当前命令）")
    s.add_argument("--clients", default="claude,codex", help="要配置的客户端，逗号分隔")
    s.add_argument("--no-hardening", action="store_true", help="不写 Claude Code 的 deny 规则与沙箱凭据屏蔽")

    d = sub.add_parser("doctor", help="检查配置、命令串、shell 输出和 spool 积压")
    d.add_argument("--home", help="用这个目录代替 HOME")
    d.add_argument("--cred", help="credentials.json 的绝对路径")
    d.add_argument("--bin", help="teamflow 可执行文件的绝对路径")
    return p


def _slow(argv) -> int:
    p = _build_parser()
    ns = p.parse_args(argv)
    if ns.cmd is None:
        p.print_help()
        return 0
    if ns.cmd == "hook":
        return _hook(argv[1:])
    if ns.cmd == "mcp-headers":
        return _mcp_headers(argv[1:])
    if ns.cmd == "flush":
        return _flush(argv[1:])
    if ns.cmd == "inbox":
        from teamflow import board_cmd, inbox_cmd

        return inbox_cmd.run(ns.client or board_cmd.detect_client(), ns.cred or default_cred())
    if ns.cmd in ("note", "done", "block"):
        from teamflow import board_cmd

        ns.cred = ns.cred or default_cred()
        return board_cmd.run(ns)
    if ns.cmd == "claude-flags":
        from teamflow import setup_cmd

        return setup_cmd.claude_flags(ns.home, quoted=ns.quoted)
    if ns.cmd == "setup":
        from teamflow import setup_cmd

        return setup_cmd.run(ns)
    if ns.cmd == "doctor":
        from teamflow import doctor

        return doctor.run(ns)
    p.print_help()
    return 2


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv and argv[0] in FAST and not any(a in ("-h", "--help") for a in argv[1:]):
        if argv[0] == "hook":
            try:
                return _hook(argv[1:])
            except BaseException:  # noqa: BLE001 - 连导入失败也不让 hook 报错
                return 0
        if argv[0] == "mcp-headers":
            return _mcp_headers(argv[1:])
        return _flush(argv[1:])
    return _slow(argv)
