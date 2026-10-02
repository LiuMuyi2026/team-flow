"""`teamflow mcp-headers`：给 Claude Code 的 headersHelper 和 Codex 的 http_headers_helper 输出请求头。

两端要求的格式相同：stdout 是一个「字符串 → 字符串」的 JSON 对象。
- Claude Code（cc_mcp.md「Use dynamic headers for custom authentication」）：在 shell 里运行，10 秒超时，
  每次连接都重新运行、不缓存；只文档化了 CLAUDE_CODE_MCP_SERVER_NAME / _URL / CLAUDE_PLUGIN_ROOT 三个变量。
- Codex（codex-rs/rmcp-client/src/http_headers.rs run_helper / parse_helper_output）：`sh -c` 运行，
  env_clear 后只留 HOME、PATH、SHELL 等少数变量，stdout 必须是 JSON 对象、不得有重名或保留头。
"""

import os
import sys

from teamflow import common

SESSION_ENV = {"claude": "CLAUDE_CODE_SESSION_ID", "codex": "CODEX_SESSION_ID"}


def build(client: str, cred: str, ws_slug: str | None = None, env=None) -> dict:
    from teamflow.hooks import valid_sid

    env = os.environ if env is None else env
    creds = common.load_creds(cred)
    wss = creds["workspaces"]
    if ws_slug and isinstance(wss.get(ws_slug), dict):
        ws = wss[ws_slug]
    else:
        _, ws = common.select_workspace(creds, os.getcwd())
    token = common.token_for(ws, client)
    hdr = {"Authorization": "Bearer " + token, "X-Teamflow-Client": common.WIRE_CLIENT[client]}
    sid = valid_sid(env.get(SESSION_ENV[client]))
    if sid:
        hdr["X-Teamflow-Session"] = sid
    if env.get("TEAMFLOW_DEBUG") == "1":
        # S3 用：只记录有没有拿到会话 ID，不记录值和 token
        common.log("mcp-headers client=%s session_env=%s" % (client, "yes" if sid else "no"))
    return hdr


def _json_str(s: str) -> str:
    out = ['"']
    for c in s:
        o = ord(c)
        if c in '"\\' or o < 0x20 or o > 0x7E:
            out.append("\\u%04x" % o if o <= 0xFFFF else "".join("\\u%04x" % u for u in _utf16(o)))
        else:
            out.append(c)
    out.append('"')
    return "".join(out)


def _utf16(o):
    o -= 0x10000
    return (0xD800 + (o >> 10), 0xDC00 + (o & 0x3FF))


def _json_obj(d: dict) -> str:
    """只含字符串的扁平对象；手写编码，免得为一行输出导入 json。"""
    return "{" + ",".join("%s:%s" % (_json_str(k), _json_str(v)) for k, v in d.items()) + "}"


def run(client: str, cred: str, ws_slug: str | None = None) -> int:
    try:
        tty = sys.stdout.isatty()
    except (ValueError, OSError):
        tty = False
    if tty:
        sys.stderr.write(
            "teamflow mcp-headers：标准输出是终端，拒绝输出凭据。"
            "这个命令只给 Claude Code / Codex 在连接 MCP 时调用。\n"
        )
        return 2
    try:
        hdr = build(client, cred, ws_slug)
    except common.CredError as e:
        sys.stderr.write("teamflow mcp-headers：%s\n" % e)
        common.log("mcp-headers cred error: %s" % e)
        return 1
    sys.stdout.write(_json_obj(hdr))
    sys.stdout.flush()
    return 0
