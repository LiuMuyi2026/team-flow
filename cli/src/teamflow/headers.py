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

# 不发 X-Teamflow-Session（M0 S3）：
# - Claude Code 不给 headersHelper 设置 CLAUDE_CODE_SESSION_ID，helper 看到的是父进程原样的环境。嵌套运行
#   （在 Claude Code 的 Bash 里跑 claude -p、脚本、workflow）时那是外层会话的 ID，会把子会话的 MCP 调用
#   精确地记到外层会话上；顶层运行时根本没有这个变量。helper 也只在连接时跑一次，/clear 换了 ID 也不会更新。
# - Codex 运行 helper 前 env_clear()，CODEX_SESSION_ID 本来就到不了这里；服务端改用 tools/call 的
#   _meta["x-codex-turn-metadata"].session_id 匹配 hook 登记的会话（两者都来自 Codex 的 sess.session_id()）。
# 所以两端的 MCP 请求头都只带身份，会话归属交给服务端；拿不到可信会话时服务端按成员级记账。


def build(client: str, cred: str, ws_slug: str | None = None, env=None) -> dict:
    env = os.environ if env is None else env
    creds = common.load_creds(cred)
    wss = creds["workspaces"]
    if ws_slug and isinstance(wss.get(ws_slug), dict):
        ws = wss[ws_slug]
    else:
        _, ws = common.select_workspace(creds, os.getcwd())
    token = common.token_for(ws, client)
    hdr = {"Authorization": "Bearer " + token, "X-Teamflow-Client": common.WIRE_CLIENT[client]}
    if env.get("TEAMFLOW_DEBUG") == "1":
        # S3 用：只记录有没有继承到会话变量（我们不会发它），不记录值和 token
        var = "CLAUDE_CODE_SESSION_ID" if client == "claude" else "CODEX_SESSION_ID"
        common.log("mcp-headers client=%s session_env=%s (not sent)" % (client, "yes" if env.get(var) else "no"))
    return hdr


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
    sys.stdout.write(common.dumps(hdr))
    sys.stdout.flush()
    return 0
