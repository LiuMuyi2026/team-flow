"""`teamflow setup` 与 `teamflow claude-flags`。

生成并合并写入（plan 6.4、6.8）：
- Claude Code：<home>/.claude/settings.json（hooks 用 exec form：command + args）、
  <home>/.claude.json 顶层 mcpServers.teamflow（user scope，type http，headersHelper）；
- Codex：<home>/.codex/config.toml 的 [mcp_servers.teamflow]，<home>/.codex/hooks.json
  （顶层只有 description 和 hooks；我们的组追加在每个事件数组末尾）；
- 无头：<home>/.config/teamflow/claude-headless-settings.json 与 claude-mcp.json。

--home 必须能指向临时目录；测试绝不写真实 HOME。改已有文件前先备份。
"""

import copy
import json
import os
import shlex
import shutil
import sys
import time

from teamflow import common

DEFAULT_API = "http://127.0.0.1:8100"
SESSION_START_MATCHER = "startup|resume|clear|compact|fork"
# (事件名, 子命令, Claude timeout, Codex timeout)；Claude 的 SessionEnd 不设 timeout，用 1.5s 总预算
HOOK_SPECS = (
    ("SessionStart", "session-start", 5, 5),
    ("UserPromptSubmit", "prompt", 2, 2),
    ("Stop", "stop", 5, 5),
    ("SessionEnd", "session-end", None, 2),
)
CODEX_HOOKS_DESC = "teamflow（由 teamflow setup 生成，请勿手改）"
MCP_ALLOW = "mcp__teamflow__*"


# ---------------------------------------------------------------- 路径


class Paths:
    def __init__(self, home: str, cred: str | None = None):
        self.home = os.path.abspath(os.path.expanduser(home))
        self.cfg_dir = os.path.join(self.home, ".config", "teamflow")
        self.cred = os.path.abspath(cred) if cred else os.path.join(self.cfg_dir, "credentials.json")
        self.claude_settings = os.path.join(self.home, ".claude", "settings.json")
        self.claude_json = os.path.join(self.home, ".claude.json")
        self.codex_config = os.path.join(self.home, ".codex", "config.toml")
        self.codex_hooks = os.path.join(self.home, ".codex", "hooks.json")
        self.headless_settings = os.path.join(self.cfg_dir, "claude-headless-settings.json")
        self.headless_mcp = os.path.join(self.cfg_dir, "claude-mcp.json")

    def tilde(self, path: str) -> str:
        """权限规则里的路径写法：home 下用 ~/，其余用 //绝对路径。"""
        rel = os.path.relpath(path, self.home)
        if not rel.startswith(".."):
            return "~/" + rel
        return "/" + path


def default_bin() -> str:
    a0 = sys.argv[0] if sys.argv else ""
    if os.path.basename(a0) == "teamflow" and os.path.exists(a0):
        return os.path.abspath(a0)
    found = shutil.which("teamflow")
    if found:
        return os.path.abspath(found)
    cand = os.path.join(os.path.dirname(sys.executable), "teamflow")
    return cand


# ---------------------------------------------------------------- 片段生成


def mcp_url(api_url: str) -> str:
    return api_url.rstrip("/") + "/mcp/"  # 一律带尾斜杠：Codex 配了 helper 不跟随 307


def helper_cmd(bin_path: str, client: str, cred: str) -> str:
    return " ".join(shlex.quote(x) for x in (bin_path, "mcp-headers", "--client", client, "--cred", cred))


def claude_hook_groups(bin_path: str, cred: str) -> dict:
    out = {}
    for event, sub, ctimeout, _ in HOOK_SPECS:
        h = {"type": "command", "command": bin_path, "args": ["hook", sub, "--client", "claude", "--cred", cred]}
        if ctimeout:
            h["timeout"] = ctimeout
        grp = {"hooks": [h]}
        if event == "SessionStart":
            grp = {"matcher": SESSION_START_MATCHER, "hooks": [h]}
        out[event] = grp
    return out


def codex_hook_command(bin_path: str, sub: str, cred: str) -> str:
    return " ".join(shlex.quote(x) for x in (bin_path, "hook", sub, "--client", "codex", "--cred", cred))


def codex_hook_groups(bin_path: str, cred: str) -> dict:
    out = {}
    for event, sub, _, xtimeout in HOOK_SPECS:
        out[event] = {"hooks": [{"type": "command", "command": codex_hook_command(bin_path, sub, cred), "timeout": xtimeout}]}
    return out


def claude_mcp_entry(api_url: str, bin_path: str, cred: str) -> dict:
    return {"type": "http", "url": mcp_url(api_url), "headersHelper": helper_cmd(bin_path, "claude", cred)}


def _is_teamflow_handler(h) -> bool:
    if not isinstance(h, dict):
        return False
    cmd = h.get("command")
    if not isinstance(cmd, str):
        return False
    args = h.get("args")
    if isinstance(args, list):
        return os.path.basename(cmd) == "teamflow" and bool(args) and args[0] == "hook"
    try:
        toks = shlex.split(cmd)
    except ValueError:
        return False
    return len(toks) >= 2 and os.path.basename(toks[0]) == "teamflow" and toks[1] == "hook"


def _is_teamflow_group(g) -> bool:
    return isinstance(g, dict) and any(_is_teamflow_handler(h) for h in (g.get("hooks") or []))


def _append_groups(hooks: dict, groups: dict) -> dict:
    for event, grp in groups.items():
        arr = hooks.get(event)
        arr = [g for g in arr if not _is_teamflow_group(g)] if isinstance(arr, list) else []
        arr.append(grp)
        hooks[event] = arr
    return hooks


def _add_unique(lst: list, items):
    for x in items:
        if x not in lst:
            lst.append(x)
    return lst


def merge_claude_settings(existing: dict | None, paths: Paths, bin_path: str, hardening: bool = True) -> dict:
    s = copy.deepcopy(existing) if isinstance(existing, dict) else {}
    perms = s.get("permissions") if isinstance(s.get("permissions"), dict) else {}
    s["permissions"] = perms
    perms["allow"] = _add_unique(perms.get("allow") if isinstance(perms.get("allow"), list) else [], [MCP_ALLOW])
    if hardening:
        cred_dir = paths.tilde(os.path.dirname(paths.cred))
        deny = [
            "Read(%s/**)" % cred_dir,
            "Grep(%s/**)" % cred_dir,
            "Bash(teamflow mcp-headers:*)",
            "Bash(%s mcp-headers:*)" % bin_path,
        ]
        perms["deny"] = _add_unique(perms.get("deny") if isinstance(perms.get("deny"), list) else [], deny)
        sb = s.get("sandbox") if isinstance(s.get("sandbox"), dict) else {}
        s["sandbox"] = sb
        sb.setdefault("enabled", True)  # 用户明确关掉的不改
        cr = sb.get("credentials") if isinstance(sb.get("credentials"), dict) else {}
        sb["credentials"] = cr
        files = cr.get("files") if isinstance(cr.get("files"), list) else []
        have = {f.get("path") for f in files if isinstance(f, dict)}
        for p in (paths.tilde(paths.cred), "~/.ssh", "~/.aws/credentials"):
            if p not in have:
                files.append({"path": p, "mode": "deny"})
        cr["files"] = files
    hooks = s.get("hooks") if isinstance(s.get("hooks"), dict) else {}
    s["hooks"] = _append_groups(hooks, claude_hook_groups(bin_path, paths.cred))
    return s


def merge_claude_json(existing: dict | None, api_url: str, bin_path: str, cred: str) -> dict:
    s = copy.deepcopy(existing) if isinstance(existing, dict) else {}
    servers = s.get("mcpServers") if isinstance(s.get("mcpServers"), dict) else {}
    servers["teamflow"] = claude_mcp_entry(api_url, bin_path, cred)
    s["mcpServers"] = servers
    return s


def merge_codex_hooks(existing, bin_path: str, cred: str) -> tuple[dict, list]:
    warnings = []
    ex = existing if isinstance(existing, dict) else {}
    extra = [k for k in ex if k not in ("description", "hooks")]
    if extra:
        warnings.append("hooks.json 里有 Codex 不认的顶层键 %s，已去掉（否则整个文件加载失败）" % extra)
    desc = ex.get("description") if isinstance(ex.get("description"), str) and ex.get("description") else CODEX_HOOKS_DESC
    hooks = ex.get("hooks") if isinstance(ex.get("hooks"), dict) else {}
    hooks = _append_groups(copy.deepcopy(hooks), codex_hook_groups(bin_path, cred))
    return {"description": desc, "hooks": hooks}, warnings


def merge_codex_config(text: str | None, api_url: str, bin_path: str, cred: str) -> str:
    import tomllib

    import tomlkit

    doc = tomlkit.parse(text) if text else tomlkit.document()
    servers = doc.get("mcp_servers")
    if servers is None:
        servers = tomlkit.table(is_super_table=True)
        doc["mcp_servers"] = servers
    t = tomlkit.table()
    t["url"] = mcp_url(api_url)
    t["http_headers_helper"] = helper_cmd(bin_path, "codex", cred)
    t["startup_timeout_sec"] = 10
    t["tool_timeout_sec"] = 30
    servers["teamflow"] = t
    out = tomlkit.dumps(doc)
    tomllib.loads(out)  # 写出前确认仍是合法 TOML
    return out


def headless_settings(paths: Paths, bin_path: str) -> dict:
    return {"permissions": {"allow": [MCP_ALLOW]}, "hooks": {k: [v] for k, v in claude_hook_groups(bin_path, paths.cred).items()}}


def headless_mcp(api_url: str, bin_path: str, cred: str) -> dict:
    return {"mcpServers": {"teamflow": claude_mcp_entry(api_url, bin_path, cred)}}


# ---------------------------------------------------------------- 写文件


def _git_email(home: str):
    import subprocess

    env = dict(os.environ)
    env["HOME"] = home
    env.pop("GIT_CONFIG_GLOBAL", None)
    try:
        out = subprocess.run(
            ["git", "config", "--global", "--get", "user.email"],
            capture_output=True, text=True, timeout=2, env=env,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    e = out.stdout.strip().lower()
    return e or None


class Plan:
    """收集要写的文件，dry-run 只打印。"""

    def __init__(self, dry_run: bool):
        self.dry_run = dry_run
        self.items = []  # (path, text, mode)

    def add(self, path, text, mode=0o644):
        self.items.append((path, text, mode))

    def apply(self, out=sys.stdout):
        stamp = time.strftime("%Y%m%d%H%M%S")
        for path, text, mode in self.items:
            if self.dry_run:
                out.write("=== 将写入 %s ===\n%s\n" % (path, text.rstrip("\n")))
                continue
            common.ensure_dir(os.path.dirname(path))
            if os.path.exists(path):
                with open(path, "rb") as f:
                    old = f.read()
                if old == text.encode("utf-8"):
                    out.write("未变化 %s\n" % path)
                    continue
                bak = "%s.bak-%s" % (path, stamp)
                with open(bak, "wb") as f:
                    f.write(old)
                os.chmod(bak, os.stat(path).st_mode & 0o777)
            tmp = "%s.tmp-%d" % (path, os.getpid())
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
            with os.fdopen(fd, "wb") as f:
                f.write(text.encode("utf-8"))
            os.chmod(tmp, mode)
            os.replace(tmp, path)
            out.write("已写入 %s\n" % path)


def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def run(ns) -> int:
    home = ns.home or os.path.expanduser("~")
    paths = Paths(home, ns.cred)
    bin_path = os.path.abspath(ns.bin) if ns.bin else default_bin()
    clients = [c.strip() for c in (ns.clients or "").split(",") if c.strip()]
    bad = [c for c in clients if c not in common.CLIENTS]
    if bad:
        sys.stderr.write("teamflow setup：不认识的客户端 %s\n" % bad)
        return 2
    plan = Plan(ns.dry_run)
    warnings = []

    # 1. 凭据文件（M0 还没有设备码流程：不存在就写一个模板，token 从环境变量取）
    creds = common.read_json(paths.cred)
    if not isinstance(creds, dict) or not isinstance(creds.get("workspaces"), dict):
        slug = ns.workspace or "team"
        api_url = ns.api_url or DEFAULT_API
        creds = {
            "workspaces": {
                slug: {
                    "api_url": api_url,
                    "tokens": {
                        "claude": os.environ.get("TEAMFLOW_PAT_CLAUDE", ""),
                        "codex": os.environ.get("TEAMFLOW_PAT_CODEX", ""),
                    },
                    "repo_patterns": [],
                }
            },
            "default": slug,
        }
        new_creds = True
    else:
        new_creds = False
        try:
            slug, _ = common.select_workspace(creds, home)
        except common.CredError:
            slug = next(iter(creds["workspaces"]), "team")
        api_url = ns.api_url or creds["workspaces"].get(slug, {}).get("api_url") or DEFAULT_API
    email = _git_email(paths.home)
    ws = creds["workspaces"].get(slug)
    if email and isinstance(ws, dict):
        emails = ws.get("git_emails") if isinstance(ws.get("git_emails"), list) else []
        if email not in emails:
            ws["git_emails"] = emails + [email]
            new_creds = True
    if new_creds:
        plan.add(paths.cred, _dump(creds), 0o600)
    elif not ns.dry_run:
        try:
            os.chmod(paths.cred, 0o600)
        except OSError:
            pass
    tokens = (ws or {}).get("tokens") or {}
    for c in clients:
        if not str(tokens.get(c, "")).startswith("tf_pat_"):
            warnings.append("凭据文件里还没有 %s 的 token：请设置环境变量 TEAMFLOW_PAT_%s 后重跑，或手动填入 %s" % (c, c.upper(), paths.cred))

    # 2. Claude Code
    if "claude" in clients:
        s = merge_claude_settings(common.read_json(paths.claude_settings), paths, bin_path, hardening=not ns.no_hardening)
        plan.add(paths.claude_settings, _dump(s))
        cj = common.read_json(paths.claude_json)
        plan.add(paths.claude_json, _dump(merge_claude_json(cj, api_url, bin_path, paths.cred)), 0o600)
        plan.add(paths.headless_settings, _dump(headless_settings(paths, bin_path)))
        plan.add(paths.headless_mcp, _dump(headless_mcp(api_url, bin_path, paths.cred)))

    # 3. Codex
    if "codex" in clients:
        text = None
        if os.path.exists(paths.codex_config):
            with open(paths.codex_config, encoding="utf-8") as f:
                text = f.read()
        plan.add(paths.codex_config, merge_codex_config(text, api_url, bin_path, paths.cred))
        hj, w = merge_codex_hooks(common.read_json(paths.codex_hooks), bin_path, paths.cred)
        warnings.extend(w)
        plan.add(paths.codex_hooks, _dump(hj))

    plan.apply()
    for w in warnings:
        sys.stdout.write("注意：%s\n" % w)
    if "codex" in clients:
        sys.stdout.write("下一步：在 Codex 里打开 /hooks，信任 4 条 teamflow hook（命令串变了就要重新信任）。\n")
    if not ns.dry_run:
        sys.stdout.write("然后运行 teamflow doctor --home %s 检查。\n" % shlex.quote(paths.home))
    return 0


# ---------------------------------------------------------------- claude-flags


def claude_flags(home: str | None, quoted: bool = False) -> int:
    paths = Paths(home or os.path.expanduser("~"))
    argv = ["--settings", paths.headless_settings, "--mcp-config", paths.headless_mcp, "--allowedTools", MCP_ALLOW]
    if quoted:
        sys.stdout.write(" ".join(shlex.quote(a) for a in argv) + "\n")
        return 0
    if any(c.isspace() for a in argv for c in a):
        sys.stderr.write("teamflow claude-flags：路径里有空白，$(...) 展开会断开；请用 --quoted 配合 eval。\n")
        return 1
    # 给 $(teamflow claude-flags) 用：命令替换不处理引号，所以这里不加引号
    sys.stdout.write(" ".join(argv) + "\n")
    return 0
