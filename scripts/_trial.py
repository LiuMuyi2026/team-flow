"""本地试用脚本共用的小工具（scripts/local-up.sh 等调用它的子命令，sim-teammate.py 导入它）。

只用标准库（import-codex-config 另用 cli 依赖的 tomlkit），由 .local/venv 里的 Python 运行。
所有 HTTP 都直连 127.0.0.1，绝不走代理：系统里设了 http_proxy / HTTPS_PROXY 时，urllib 默认会把
127.0.0.1 也送进代理（见 docs/local-trial.md「常见问题」）。

子命令（给 bash 脚本用，输出尽量是一行）：
  wait-health <base> <秒> [pid]      等服务端 /healthz 通；pid 先退出就失败
  health <base>                       /healthz 通就 exit 0
  login-links <日志>                  从服务端日志里取最近一次启动打印的登录链接：每行 "handle<TAB>链接"
  gen-token                           打印一个随机的 tf_pat_ 令牌
  gen-env <tokens.env> <me> <mates>   生成令牌文件（0600）
  dev-tokens <tokens.env>             拼 TEAMFLOW_DEV_TOKENS 的值
  import-codex-config <源> <目标>     从您平时的 Codex 配置里只读地抄模型、服务商等设置（不抄 MCP 和 hooks）
  codex-trust <config.toml> <hooks.json>  数一数 Codex 已经记录信任的 teamflow hook 条数
  probe-members <me> <mates>          用这些 handle 的一次性令牌在进程里构造一次服务端，打印它的成员，逗号分隔
"""

from __future__ import annotations

import json
import os
import re
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL = os.path.join(ROOT, ".local")
HANDLE_RE = re.compile(r"^[a-z][a-z0-9_]{1,15}$")
CLIENTS = ("claude_code", "codex")
CLIENT_NAMES = {"claude_code": "Claude Code", "codex": "Codex"}


def local_path(*parts: str) -> str:
    return os.path.join(LOCAL, *parts)


# ---------------------------------------------------------------------------
# 配置文件：KEY=VALUE（bash 也能 source）
# ---------------------------------------------------------------------------


def read_env(path: str) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                v = v.strip()
                if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
                    v = v[1:-1]
                out[k.strip()] = v
    except OSError:
        pass
    return out


def write_private(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    tmp = "%s.tmp-%d" % (path, os.getpid())
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def token_key(handle: str, client: str) -> str:
    return "TF_TOKEN_%s_%s" % (handle.upper(), "CLAUDE" if client == "claude_code" else "CODEX")


def gen_token() -> str:
    return "tf_pat_" + secrets.token_hex(16)


def gen_env(path: str, me: str, mates: list[str]) -> None:
    lines = [
        "# Team Flow 本地试用的令牌（scripts/local-up.sh 生成，权限 0600）。",
        "# 只给这台电脑上的试用服务端用：不要提交，不要发给别人。重来一遍：scripts/local-reset.sh",
        "TF_MEMBERS=%s" % ",".join([me] + mates),
    ]
    for h in [me] + mates:
        for c in CLIENTS:
            lines.append("%s=%s" % (token_key(h, c), gen_token()))
    write_private(path, "\n".join(lines) + "\n")


def dev_tokens(env: dict[str, str]) -> str:
    parts = []
    for h in [m for m in env.get("TF_MEMBERS", "").split(",") if m]:
        for c in CLIENTS:
            tok = env.get(token_key(h, c))
            if tok:
                parts.append("%s:%s:%s" % (tok, h, c))
    return ",".join(parts)


class Trial:
    """读 .local/local.env（端口、成员，非机密）和 .local/tokens.env（令牌）。"""

    def __init__(self) -> None:
        self.conf = read_env(local_path("local.env"))
        self.tokens = read_env(local_path("tokens.env"))
        if not self.conf or not self.tokens:
            raise SystemExit("还没有本地试用环境：请先运行 scripts/local-up.sh")
        self.base = self.conf.get("TF_BASE") or "http://127.0.0.1:%s" % self.conf.get("TF_PORT", "8100")
        self.me = self.conf.get("TF_ME", "me")
        self.mates = [m for m in self.conf.get("TF_MATES", "").split(",") if m]

    def token(self, handle: str, client: str) -> str:
        tok = self.tokens.get(token_key(handle, client))
        if not tok:
            raise SystemExit("tokens.env 里没有 %s 的 %s 令牌；成员改过的话请运行 scripts/local-reset.sh" % (handle, CLIENT_NAMES[client]))
        return tok


# ---------------------------------------------------------------------------
# HTTP：直连、不跟随重定向
# ---------------------------------------------------------------------------


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **kw):  # noqa: ANN002, ANN003
        return None


_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())


class Resp:
    def __init__(self, status: int, headers, body: bytes) -> None:  # noqa: ANN001
        self.status = status
        self.headers = headers
        self.body = body

    def json(self):  # noqa: ANN201
        try:
            return json.loads(self.body.decode("utf-8") or "null")
        except ValueError:
            return None


def request(method: str, url: str, *, headers: dict[str, str] | None = None, body: bytes | None = None,
            timeout: float = 10) -> Resp:
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with _OPENER.open(req, timeout=timeout) as r:
            return Resp(r.status, r.headers, r.read())
    except urllib.error.HTTPError as e:
        return Resp(e.code, e.headers, e.read() if e.fp else b"")


def health(base: str) -> bool:
    try:
        r = request("GET", base.rstrip("/") + "/healthz", timeout=2)
    except (OSError, ValueError):
        return False
    data = r.json()
    return r.status == 200 and isinstance(data, dict) and data.get("ok") is True


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def wait_health(base: str, seconds: float, pid: int | None) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if health(base):
            return True
        if pid and not _pid_alive(pid):
            return False
        time.sleep(0.25)
    return health(base)


LINK_RE = re.compile(r"^teamflow-server:\s+([a-z][a-z0-9_]{1,15})\s+(https?://\S+/dev/login\?\S+)\s*$")
BANNER_RE = re.compile(r"^teamflow-server: .*登录链接")


def login_links(log_path: str) -> list[tuple[str, str]]:
    """服务端启动时在 stderr 打印的登录链接（server/teamflow_server/devlogin.py banner）：只取最后一次启动的那一组。"""
    try:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return []
    out: list[tuple[str, str]] = []
    for line in lines:
        if BANNER_RE.match(line):
            out = []
            continue
        m = LINK_RE.match(line)
        if m:
            out.append((m.group(1), m.group(2)))
    return out


# ---------------------------------------------------------------------------
# Codex：只读地抄您平时的模型设置；数信任记录
# ---------------------------------------------------------------------------

# 抄这些顶层键：模型、服务商（含中转）、登录方式、审批和沙箱习惯、项目信任。
# 不抄 mcp_servers（试用只连 teamflow，也免得把别的 MCP 密钥复制一份）、hooks（只跑 teamflow 的 4 条）、notify。
CODEX_KEYS = (
    "model", "model_provider", "model_providers", "model_reasoning_effort", "model_reasoning_summary",
    "model_verbosity", "model_supports_reasoning_summaries", "model_context_window", "model_auto_compact_token_limit",
    "profile", "profiles", "preferred_auth_method", "forced_login_method", "forced_chatgpt_workspace_id",
    "chatgpt_base_url", "openai_base_url", "cli_auth_credentials_store", "approval_policy", "sandbox_mode",
    "sandbox_workspace_write", "shell_environment_policy", "web_search", "tools", "projects", "features",
    "personality", "file_opener", "hide_agent_reasoning", "show_raw_agent_reasoning", "tui",
)


def import_codex_config(src: str, dst: str) -> list[str]:
    import tomllib

    import tomlkit

    with open(src, "rb") as f:
        data = tomllib.load(f)
    doc = tomlkit.document()
    doc.add(tomlkit.comment("本地试用的 Codex 配置（CODEX_HOME=.local/codex）。下面几项由 scripts/local-up.sh"))
    doc.add(tomlkit.comment("从您平时的 Codex 配置里只读地抄过来；原文件没有任何改动。teamflow 的部分由 setup 写入。"))
    copied = []
    for k in CODEX_KEYS:
        if k not in data:
            continue
        v = data[k]
        if k == "features" and isinstance(v, dict):
            v = {fk: fv for fk, fv in v.items() if fk not in ("hooks", "codex_hooks")}  # 试用要用 hooks
            if not v:
                continue
        doc[k] = v
        copied.append(k)
    write_private(dst, tomlkit.dumps(doc))
    return copied


HOOK_LABELS = ("session_start", "user_prompt_submit", "stop", "session_end")


def codex_trust(config_path: str, hooks_path: str) -> int:
    """Codex 把信任记在 CODEX_HOME/config.toml 的 [hooks.state."<hooks.json 路径>:<事件>:<组>:<条>"]
    （codex-rs/hooks/src/lib.rs hook_key、codex-rs/config/src/hook_config.rs）。只数 4 个事件里有 trusted_hash 的；
    哈希对不对得上要 Codex 自己算（不对时 /hooks 里显示 Modified）。"""
    import tomllib

    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    except (OSError, ValueError):
        return 0
    state = ((data.get("hooks") or {}).get("state") or {}) if isinstance(data.get("hooks"), dict) else {}
    real = os.path.realpath(hooks_path)
    seen = set()
    for key, val in state.items():
        if not isinstance(val, dict) or not val.get("trusted_hash"):
            continue
        for label in HOOK_LABELS:
            for prefix in (hooks_path, real):
                if key.startswith(prefix + ":" + label + ":"):
                    seen.add(label)
    return len(seen)


def probe_members(handles: list[str]) -> list[str]:
    """不起端口，只在进程里按启动时同样的环境构造一次服务端，看它有哪些成员。

    成员从哪来是服务端的事（种子数据、令牌里的 handle……），local-up.sh 只核对自己要的 handle 在不在里面。
    令牌是这里临时生成、用完即弃的；构造时不写日志、不写状态目录（登录码在服务端真正启动时才生成）。"""
    os.environ["TEAMFLOW_DEV_TOKENS"] = ",".join("%s:%s:%s" % (gen_token(), h, c) for h in handles for c in CLIENTS)
    os.environ["TEAMFLOW_DEV_ENDPOINTS"] = "1"
    os.environ["TEAMFLOW_LOG"] = os.devnull
    import contextlib
    import io

    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        from teamflow_server import app as appmod

        svc = appmod.app.state.svc
        return [m.handle for m in svc.members.values() if getattr(m, "active", True)]


# ---------------------------------------------------------------------------


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd, args = argv[0], argv[1:]
    if cmd == "wait-health":
        pid = int(args[2]) if len(args) > 2 and args[2].isdigit() else None
        return 0 if wait_health(args[0], float(args[1]), pid) else 1
    if cmd == "health":
        return 0 if health(args[0]) else 1
    if cmd == "login-links":
        for h, url in login_links(args[0]):
            print("%s\t%s" % (h, url))
        return 0
    if cmd == "gen-token":
        print(gen_token())
        return 0
    if cmd == "gen-env":
        me, mates = args[1], [m for m in args[2].split(",") if m]
        bad = [h for h in [me] + mates if not HANDLE_RE.match(h)]
        if bad or len(set([me] + mates)) != len(mates) + 1:
            print("handle 不合格或重复：%s（要求小写字母开头，2–16 位小写字母、数字、下划线）" % ",".join(bad or [me] + mates),
                  file=sys.stderr)
            return 2
        gen_env(args[0], me, mates)
        return 0
    if cmd == "dev-tokens":
        print(dev_tokens(read_env(args[0])))
        return 0
    if cmd == "import-codex-config":
        try:
            copied = import_codex_config(args[0], args[1])
        except (OSError, ValueError) as e:
            print("没能读取 %s（%s），Codex 用缺省设置" % (args[0], e.__class__.__name__), file=sys.stderr)
            return 1
        print("、".join(copied))
        return 0
    if cmd == "probe-members":
        print(",".join(probe_members([args[0]] + [m for m in args[1].split(",") if m])))
        return 0
    if cmd == "codex-trust":
        print(codex_trust(args[0], args[1]))
        return 0
    print("未知子命令 %s" % cmd, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
