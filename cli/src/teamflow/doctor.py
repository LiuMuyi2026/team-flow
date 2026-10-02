"""`teamflow doctor`：基础检查。每项输出「通过」或「失败」，失败时给一行修复办法。"""

import os
import shlex
import shutil
import subprocess
import sys

from teamflow import common, setup_cmd, spool


class Report:
    def __init__(self):
        self.failed = 0

    def ok(self, name, detail=""):
        print("通过  %s%s" % (name, "：" + detail if detail else ""))

    def fail(self, name, fix):
        self.failed += 1
        print("失败  %s\n      修复：%s" % (name, fix))

    def info(self, name, detail):
        print("提示  %s：%s" % (name, detail))


def _version(cmd):
    exe = shutil.which(cmd)
    if not exe:
        return None
    try:
        out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=5)
        return (out.stdout or out.stderr).strip().splitlines()[0] if (out.stdout or out.stderr).strip() else "?"
    except (OSError, subprocess.TimeoutExpired):
        return "?"


def _shell_quiet(shell, flag):
    try:
        out = subprocess.run([shell, flag, "true"], capture_output=True, timeout=10, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, str(e)
    return out.stdout, None


def check_claude(r: Report, paths: setup_cmd.Paths, bin_path: str):
    s = common.read_json(paths.claude_settings)
    if not isinstance(s, dict):
        r.fail("Claude Code settings.json", "运行 teamflow setup --home %s" % shlex.quote(paths.home))
        return
    want = setup_cmd.claude_hook_groups(bin_path, paths.cred)
    hooks = s.get("hooks") if isinstance(s.get("hooks"), dict) else {}
    for event, grp in want.items():
        arr = hooks.get(event) if isinstance(hooks.get(event), list) else []
        ours = [g for g in arr if setup_cmd._is_teamflow_group(g)]
        if not ours:
            r.fail("Claude Code %s hook" % event, "运行 teamflow setup 重新写入")
        elif ours[-1] != grp:
            r.fail("Claude Code %s hook 命令串" % event, "与安装记录不一致，运行 teamflow setup 重新写入")
        else:
            r.ok("Claude Code %s hook" % event)
    allow = (s.get("permissions") or {}).get("allow") or []
    if setup_cmd.MCP_ALLOW in allow:
        r.ok("Claude Code 允许 mcp__teamflow__*")
    else:
        r.fail("Claude Code 允许 mcp__teamflow__*", "运行 teamflow setup")
    cj = common.read_json(paths.claude_json)
    srv = ((cj or {}).get("mcpServers") or {}).get("teamflow") if isinstance(cj, dict) else None
    if isinstance(srv, dict) and srv.get("type") == "http" and str(srv.get("url", "")).endswith("/mcp/"):
        if srv.get("headersHelper") == setup_cmd.helper_cmd(bin_path, "claude", paths.cred):
            r.ok("Claude Code user scope MCP", srv["url"])
        else:
            r.fail("Claude Code MCP headersHelper", "命令串与本机安装不一致，运行 teamflow setup")
    else:
        r.fail("Claude Code user scope MCP", "运行 teamflow setup（url 必须以 /mcp/ 结尾）")
    if os.path.exists(os.path.join(os.getcwd(), ".mcp.json")):
        mj = common.read_json(os.path.join(os.getcwd(), ".mcp.json"))
        if isinstance(mj, dict) and "teamflow" in (mj.get("mcpServers") or {}):
            r.fail("当前目录 .mcp.json 有同名 teamflow", "它会遮蔽 user scope 的配置；仓库里请改名为 teamflow-cloud")
    for p in (paths.headless_settings, paths.headless_mcp):
        if os.path.exists(p):
            r.ok("无头配置 %s" % os.path.basename(p))
        else:
            r.fail("无头配置 %s" % os.path.basename(p), "运行 teamflow setup")


def check_codex(r: Report, paths: setup_cmd.Paths, bin_path: str):
    import tomllib

    try:
        with open(paths.codex_config, "rb") as f:
            cfg = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        cfg = None
    srv = ((cfg or {}).get("mcp_servers") or {}).get("teamflow") if isinstance(cfg, dict) else None
    if isinstance(srv, dict) and str(srv.get("url", "")).endswith("/mcp/") and srv.get(
        "http_headers_helper"
    ) == setup_cmd.helper_cmd(bin_path, "codex", paths.cred):
        r.ok("Codex [mcp_servers.teamflow]", srv["url"])
    else:
        r.fail("Codex [mcp_servers.teamflow]", "运行 teamflow setup")
    hj = common.read_json(paths.codex_hooks)
    if not isinstance(hj, dict):
        r.fail("Codex hooks.json", "运行 teamflow setup")
        return
    extra = [k for k in hj if k not in ("description", "hooks")]
    if extra:
        r.fail("Codex hooks.json 顶层键", "只能有 description 和 hooks，去掉 %s" % extra)
    want = setup_cmd.codex_hook_groups(bin_path, paths.cred)
    hooks = hj.get("hooks") if isinstance(hj.get("hooks"), dict) else {}
    for event, grp in want.items():
        arr = hooks.get(event) if isinstance(hooks.get(event), list) else []
        if arr and arr[-1] == grp:
            r.ok("Codex %s hook（在数组末尾）" % event)
        elif any(setup_cmd._is_teamflow_group(g) for g in arr):
            r.fail("Codex %s hook" % event, "命令串不一致或不在数组末尾，运行 teamflow setup 后在 /hooks 重新信任")
        else:
            r.fail("Codex %s hook" % event, "运行 teamflow setup")
    r.info("Codex 信任状态", "doctor 不读 Codex 的信任记录；请在 Codex 的 /hooks 确认 4 条 teamflow hook 都是 Trusted")
    if os.path.isdir(os.path.join(os.getcwd(), ".codex")):
        r.info("仓库级 .codex", "交互会话里仓库级 hooks 可能不触发（openai/codex#17532），teamflow 只装用户级")


def run(ns) -> int:
    home = ns.home or os.path.expanduser("~")
    paths = setup_cmd.Paths(home, ns.cred)
    bin_path = os.path.abspath(ns.bin) if ns.bin else setup_cmd.default_bin()
    r = Report()

    from teamflow import __version__

    r.ok("teamflow %s" % __version__, bin_path)
    for cmd in ("claude", "codex"):
        v = _version(cmd)
        if v:
            r.ok("%s 版本" % cmd, v)
        else:
            r.info("%s" % cmd, "PATH 里没有找到")

    # 凭据
    try:
        creds = common.load_creds(paths.cred)
        mode = os.stat(paths.cred).st_mode & 0o777
        if mode & 0o077:
            r.fail("凭据文件权限 %o" % mode, "chmod 600 %s" % shlex.quote(paths.cred))
        else:
            r.ok("凭据文件", paths.cred)
        slug, ws = common.select_workspace(creds, os.getcwd())
        for c in common.CLIENTS:
            try:
                common.token_for(ws, c)
                r.ok("workspace %s 的 %s token" % (slug, c))
            except common.CredError:
                r.fail("workspace %s 的 %s token" % (slug, c), "填入 %s 或重新运行 setup" % paths.cred)
    except common.CredError as e:
        r.fail("凭据文件", "%s；运行 teamflow setup" % e)

    check_claude(r, paths, bin_path)
    check_codex(r, paths, bin_path)

    # shell 输出（Codex 用会话 shell -c 执行 hook，没有时退回 $SHELL -lc）
    shell = os.environ.get("SHELL")
    if not shell:
        r.info("$SHELL", "未设置，跳过 shell 输出检查")
    else:
        for flag in ("-c", "-lc"):
            out, err = _shell_quiet(shell, flag)
            name = "%s %s true 的 stdout 为空" % (shell, flag)
            if err:
                r.fail(name, "运行失败：%s" % err)
            elif out:
                shown = out[:40].decode("utf-8", "replace")  # out 是 bytes，别把 b'…' 显示给用户
                r.fail(name, "profile 有输出（%r…），会混进 Codex hook 的 stdout；把输出包进 [[ $- == *i* ]] 判断" % shown)
            else:
                r.ok(name)

    c = spool.counts()
    if c["pending"] > 50:
        r.fail("spool 积压 %d 条" % c["pending"], "检查网络后运行 teamflow flush")
    else:
        r.ok("spool 积压 %d 条" % c["pending"])
    if c["dead"]:
        r.fail("dead-letter %d 条" % c["dead"], "查看 %s 和日志 %s" % (os.path.join(spool.spool_dir(), "dead"), os.path.join(common.state_dir(), "log")))
    else:
        r.ok("dead-letter 0 条")
    print("\n%s" % ("全部通过" if not r.failed else "%d 项失败" % r.failed))
    sys.stdout.flush()
    return 0 if not r.failed else 1
