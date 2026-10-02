"""`teamflow setup` 与 `teamflow claude-flags`。

生成并合并写入（plan 6.4、6.8）：
- Claude Code：<home>/.claude/settings.json（hooks 用 exec form：command + args）、
  <home>/.claude.json 顶层 mcpServers.teamflow（user scope，type http，headersHelper）；
- Codex：<home>/.codex/config.toml 的 [mcp_servers.teamflow]，<home>/.codex/hooks.json
  （顶层只有 description 和 hooks）；
- 两端的 hook 组：已有 teamflow 的 handler 就原地更新，没有才追加一组到事件数组末尾；绝不删除、挪动别人的
  handler 和组（详见 _merge_event）。Codex 的信任键里带着组序号和 handler 序号
  （codex-rs/hooks/src/lib.rs hook_key），挪动位置会让我们和别人的 hook 都要重新信任；
- Claude Code 比 Codex 多一个 PostToolUse（D40，见 CLAUDE_ONLY_SPECS），Codex 仍是 4 个；
- 无头：<home>/.config/teamflow/claude-headless-settings.json 与 claude-mcp.json。

--home 必须能指向临时目录；测试绝不写真实 HOME。改已有文件前先备份。--dry-run 只打印 teamflow 相关键的
改动前→改动后，并做通用遮蔽（redact.py）。
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
# Claude Code 独有的 hook（D40）：(事件名, 子命令, timeout 秒, matcher)。
# PostToolUse 把每次 teamflow 工具调用对到会话：hook 输入的 tool_use_id 等于 tools/call 的
# _meta["claudecode/toolUseId"]（spike/results/S3.md 结论 3）。
# - matcher：cc_hooks.md「Matcher patterns」——含字母、数字、_ - 空格 , | 以外字符的按 JavaScript 正则、
#   不锚定地匹配 tool_name，要整串匹配就自己加 ^ $；「Match MCP tools」——MCP 工具名是 mcp__<server>__<tool>，
#   匹配一个 server 的全部工具写 `mcp__<server>__.*`（只含字母、数字、下划线的 `mcp__teamflow` 会被当成精确
#   字符串，一个都匹配不上）。再加 ^ 只认开头：名字中间恰好含 mcp__teamflow__ 的别家工具（如插件打包的
#   mcp__plugin_<插件>_<server>__…）不会命中；保留 .* 后缀，即使按整串匹配也成立。hook 里再按前缀核一遍。
# - 不设 async：cc_hooks.md「Run hooks in the background」——`claude -p` 收尾时会杀掉还在跑的 async hook
#   （outcome cancelled），最后一次工具调用的映射就丢了；async 也不受 timeout 约束。改为同步 + 2 秒超时：
#   hook 只写本地 spool，p95 在几十毫秒（spike/bench_hooks.py 的 tool 行），只在 teamflow 的工具调用后触发。
TOOL_MATCHER = "^mcp__teamflow__.*"
CLAUDE_ONLY_SPECS = (("PostToolUse", "tool", 2, TOOL_MATCHER),)
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
    for event, sub, ctimeout, matcher in CLAUDE_ONLY_SPECS:
        h = {"type": "command", "command": bin_path, "args": ["hook", sub, "--client", "claude", "--cred", cred],
             "timeout": ctimeout}
        out[event] = {"matcher": matcher, "hooks": [h]}
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


def _handlers(g):
    hs = g.get("hooks") if isinstance(g, dict) else None
    return hs if isinstance(hs, list) else None


# 我们装的事件里，这几个看组的 matcher（codex-rs/hooks/src/events/common.rs matcher_pattern_for_event；
# cc_hooks.md「Matcher patterns」：UserPromptSubmit、Stop 没有 matcher，PostToolUse 按 tool_name 匹配）。
# PostToolUse 只装在 Claude Code。
MATCHER_EVENTS = ("SessionStart", "SessionEnd", "PostToolUse")

# 删掉 teamflow handler 之后组变空时，留一个 {"hooks": []} 占位，后面组的序号就不变。两端都确认过空组合法：
# - Codex：codex-rs/config/src/hook_config.rs 的 MatcherGroup.hooks 是 #[serde(default)] Vec，discovery.rs 对空组
#   只是不产出 handler；hooks/src/engine/mod_tests.rs 有「an empty matcher group should not prevent ... loading」；
# - Claude Code：cc_hooks.md 没写；本机 2.1.287 的设置 schema 是 {matcher: string().optional(), hooks: array(...)}，
#   没有最小长度。
# 某一端将来不认空组，把它改成 False：那样的组整组保留不动，只打印警告。
EMPTY_GROUP_OK = {"claude": True, "codex": True}


def _norm_matcher(m):
    return None if m in (None, "", "*") else m


def _merge_event(arr, grp: dict, event: str, where: str, empty_ok: bool):
    """一个事件数组的合并。返回 (新数组, 警告)。

    规则（M0 复审新问题 3）：绝不删除、挪动别人的 handler 和组。
    - 没有 teamflow handler：我们的组追加到末尾。
    - 第一个 teamflow handler 所在的组原地更新：整组都是 teamflow 的就整组换成新的；和别人混在一组时只换这一个
      handler，组的 matcher 等字段不动（改了 Codex 对别人那条的哈希也变，要重新信任）。
    - 其余 teamflow handler 是重复的，要删掉；但 Codex 的信任键是「组序号:handler 序号」（hooks/src/lib.rs
      hook_key），删掉排在别人 handler 前面的那条，别人的 handler 序号会前移，所以只删「后面再没有别人的 handler」
      的那些，删不了的保留并警告。组删空了留 {"hooks": []} 占位（在数组末尾的不必占位，直接去掉）。
    """
    warnings = []
    arr = list(arr) if isinstance(arr, list) else []
    hits = [(gi, hi) for gi, g in enumerate(arr) for hi, h in enumerate(_handlers(g) or []) if _is_teamflow_handler(h)]
    if not hits:
        arr.append(copy.deepcopy(grp))
        return arr, warnings
    g0, h0 = hits[0]
    by_group = {}
    for gi, hi in hits:
        by_group.setdefault(gi, []).append(hi)
    emptied = {}
    for gi, his in by_group.items():
        g = arr[gi]
        hs = list(_handlers(g))
        if gi == g0 and len(his) == len(hs):
            arr[gi] = copy.deepcopy(grp)  # 整组都是我们的
            continue
        drop = set(his)
        if gi == g0:
            drop.discard(h0)
            hs[h0] = copy.deepcopy(grp["hooks"][0])
            if event in MATCHER_EVENTS and _norm_matcher(g.get("matcher")) != _norm_matcher(grp.get("matcher")):
                warnings.append(
                    "%s 的 %s：teamflow 的 hook 和别的 hook 在同一组（第 %d 组），这一组的 matcher 是 %s，teamflow 需要 %s；"
                    "为了不影响别人的 hook 没有改，请手动把 teamflow 那条移到单独的一组后重跑 setup"
                    % (where, event, gi + 1, json.dumps(g.get("matcher"), ensure_ascii=False),
                       json.dumps(grp.get("matcher"), ensure_ascii=False)))
        removable = set()
        for i in range(len(hs) - 1, -1, -1):  # 只删末尾连续的那几条
            if i not in drop:
                break
            removable.add(i)
        stuck = sorted(drop - removable)
        if stuck:
            warnings.append(
                "%s 的 %s：第 %d 组里有重复的 teamflow hook（第 %s 条）排在别的 hook 前面，删掉会让后面那条换序号"
                "（Codex 按序号记信任），所以没有动；会重复执行，请手动删掉后重跑 setup"
                % (where, event, gi + 1, "、".join(str(i + 1) for i in stuck)))
        new_hs = [h for i, h in enumerate(hs) if i not in removable]
        if new_hs:
            arr[gi] = dict(g, hooks=new_hs)
        else:
            emptied[gi] = g  # 先不动，看它后面还有没有组
    while arr and len(arr) - 1 in emptied:  # 末尾删空的组后面没有别人的组，直接去掉，谁的序号都不变
        del emptied[len(arr) - 1]
        arr.pop()
    for gi, g in sorted(emptied.items()):
        if empty_ok:
            arr[gi] = dict(g, hooks=[])
        else:
            warnings.append(
                "%s 的 %s：第 %d 组是重复的 teamflow hook，这一端不认空组，删掉它后面的组会前移，所以没有动；"
                "会重复执行，请手动处理" % (where, event, gi + 1))
    return arr, warnings


def _upsert_groups(hooks: dict, groups: dict, where: str = "", empty_ok: bool = True):
    """每个事件按 _merge_event 合并；返回 (hooks, 警告)。不挪动任何别人的组和 handler。"""
    warnings = []
    for event, grp in groups.items():
        hooks[event], w = _merge_event(hooks.get(event), grp, event, where, empty_ok)
        warnings.extend(w)
    return hooks, warnings


def _add_unique(lst: list, items):
    for x in items:
        if x not in lst:
            lst.append(x)
    return lst


# 会把 token 打到输出里的子命令：mcp-headers 输出请求头；setup --dry-run 打印写入计划（已遮蔽，仍一并拦下，
# 也免得 agent 自己重跑 setup 改 hooks 和权限）。
SECRET_SUBCOMMANDS = ("mcp-headers", "setup")


def deny_rules(paths: Paths, bin_path: str) -> list:
    """Claude Code 的 deny 规则（cc_perm.md）。

    `Bash(<前缀>:*)` 与 `Bash(<前缀> *)` 等价，也匹配不带参数的裸命令；deny 规则能越过开头的环境变量赋值
    和 timeout / nice 等包装命令。Bash 规则只按命令文本匹配，不是安全边界（`sh -c '…'`、换个解释器路径都
    拦不住），所以这里只覆盖常见写法，真正的屏障是沙箱的 credentials 屏蔽。
    """
    cred_dir = paths.tilde(os.path.dirname(paths.cred))
    out = ["Read(%s/**)" % cred_dir, "Grep(%s/**)" % cred_dir]
    for sub in SECRET_SUBCOMMANDS:
        for prefix in ("teamflow", bin_path, "python -m teamflow", "python3 -m teamflow"):
            out.append("Bash(%s %s:*)" % (prefix, sub))
    return out


def merge_claude_settings(existing: dict | None, paths: Paths, bin_path: str, hardening: bool = True,
                          warnings: list | None = None) -> dict:
    s = copy.deepcopy(existing) if isinstance(existing, dict) else {}
    perms = s.get("permissions") if isinstance(s.get("permissions"), dict) else {}
    s["permissions"] = perms
    perms["allow"] = _add_unique(perms.get("allow") if isinstance(perms.get("allow"), list) else [], [MCP_ALLOW])
    if hardening:
        perms["deny"] = _add_unique(perms.get("deny") if isinstance(perms.get("deny"), list) else [], deny_rules(paths, bin_path))
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
    s["hooks"], w = _upsert_groups(hooks, claude_hook_groups(bin_path, paths.cred), "Claude Code settings.json",
                                   EMPTY_GROUP_OK["claude"])
    if warnings is not None:
        warnings.extend(w)
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
    hooks, w = _upsert_groups(copy.deepcopy(hooks), codex_hook_groups(bin_path, cred), "Codex hooks.json",
                              EMPTY_GROUP_OK["codex"])
    warnings.extend(w)
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


TOKEN_PREFIX = "tf_pat_"
MASK = TOKEN_PREFIX + "****"


def mask_token(v):
    """tf_pat_ 开头的只留前缀；空串原样（让人看出还没填）；其他非空值整段遮掉。"""
    if not isinstance(v, str) or not v:
        return v
    return MASK if v.startswith(TOKEN_PREFIX) else "****"


def scrub_tokens(text: str) -> str:
    """兜底：任何地方漏出来的 tf_pat_xxx 都换成 tf_pat_****。"""
    import re

    return re.sub(r"tf_pat_(?!\*\*\*\*)[A-Za-z0-9_.\-]*", MASK, text)


def _parse(text: str, fmt: str):
    if fmt == "toml":
        import tomllib

        return tomllib.loads(text)
    return json.loads(text)


# dry-run 只显示这些键下面的改动（None：整个文件都是 teamflow 的）
ROOTS_CLAUDE_SETTINGS = (("permissions",), ("sandbox",), ("hooks",))
ROOTS_CLAUDE_JSON = (("mcpServers", "teamflow"),)
ROOTS_CODEX_CONFIG = (("mcp_servers", "teamflow"),)
ROOTS_CODEX_HOOKS = (("description",), ("hooks",))


class Plan:
    """收集要写的文件。

    dry-run 不打印整份文件（M0 复审新问题 4：~/.claude.json、config.toml 里有别的 MCP server 的密钥、
    oauthAccount 里的邮箱，而 dry-run 输出常被重定向进存证文件）：只按结构比对现有文件和将要写入的内容，
    列出 teamflow 相关键下的「改动前→改动后」，再做通用遮蔽（redact.py）。
    """

    def __init__(self, dry_run: bool):
        self.dry_run = dry_run
        self.items = []  # (path, text, mode, fmt, roots)

    def add(self, path, text, mode=0o644, fmt="json", roots=None):
        """fmt：json 或 toml（dry-run 比对用）；roots：dry-run 只显示这些键路径下的改动，None 表示全显示。"""
        self.items.append((path, text, mode, fmt, roots))

    @staticmethod
    def preview(path, text, fmt="json", roots=None) -> list:
        from teamflow import redact

        try:
            with open(path, "rb") as f:
                old_raw = f.read()
        except FileNotFoundError:
            old_raw = None
        except OSError as e:
            return ["=== 将写入 %s（现有文件读不了：%s）===" % (path, e.strerror or e)]
        if old_raw is not None and old_raw == text.encode("utf-8"):
            return ["=== 不变 %s ===" % path]
        if old_raw is None:
            before, head = {}, "新建"
        else:
            try:
                before, head = _parse(old_raw.decode("utf-8"), fmt), "修改，只列 teamflow 相关的改动"
            except (ValueError, UnicodeDecodeError):
                before, head = None, "现有文件解析不了，将整体替换，原文件会先备份"
        lines = ["=== 将写入 %s（%s）===" % (path, head)]
        body = redact.render(before, _parse(text, fmt), roots)
        return lines + (body or ["  （内容不变，只有格式变化）"])

    def apply(self, out=sys.stdout):
        stamp = time.strftime("%Y%m%d%H%M%S")
        for path, text, mode, fmt, roots in self.items:
            if self.dry_run:
                from teamflow import redact

                for line in self.preview(path, text, fmt, roots):
                    out.write(redact.redact_text(scrub_tokens(line)) + "\n")
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
        plan.add(paths.cred, _dump(creds), 0o600)  # tokens、git_emails 在 dry-run 里按键名遮蔽
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
        s = merge_claude_settings(common.read_json(paths.claude_settings), paths, bin_path,
                                  hardening=not ns.no_hardening, warnings=warnings)
        plan.add(paths.claude_settings, _dump(s), roots=ROOTS_CLAUDE_SETTINGS)
        cj = common.read_json(paths.claude_json)
        plan.add(paths.claude_json, _dump(merge_claude_json(cj, api_url, bin_path, paths.cred)), 0o600,
                 roots=ROOTS_CLAUDE_JSON)
        plan.add(paths.headless_settings, _dump(headless_settings(paths, bin_path)))
        plan.add(paths.headless_mcp, _dump(headless_mcp(api_url, bin_path, paths.cred)))

    # 3. Codex
    if "codex" in clients:
        text = None
        if os.path.exists(paths.codex_config):
            with open(paths.codex_config, encoding="utf-8") as f:
                text = f.read()
        plan.add(paths.codex_config, merge_codex_config(text, api_url, bin_path, paths.cred), fmt="toml",
                 roots=ROOTS_CODEX_CONFIG)
        hj, w = merge_codex_hooks(common.read_json(paths.codex_hooks), bin_path, paths.cred)
        warnings.extend(w)
        plan.add(paths.codex_hooks, _dump(hj), roots=ROOTS_CODEX_HOOKS)

    plan.apply()
    from teamflow import redact

    for w in warnings:
        sys.stdout.write("注意：%s\n" % redact.redact_text(w))
    if "codex" in clients:
        sys.stdout.write("下一步：在 Codex 里打开 /hooks，信任 %d 条 teamflow hook（命令串变了就要重新信任）。\n"
                         % len(HOOK_SPECS))
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
