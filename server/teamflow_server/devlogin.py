"""本地试用的一次性登录码（只在本地开发模式 TEAMFLOW_DEV_ENDPOINTS=1 下有用）。

正式版里人用通行密钥登录，每个人类动作再验证一次（plan D54、D55）。本地试用不做通行密钥，就由坐在这台电脑前的人
用一次性登录码登进网页，以成员本人的身份做接受、认领、转发等动作。规则：

- 服务端启动时（只在本地开发模式）给每个成员各生成一个登录码，在 stderr 打印登录链接
  ``http://127.0.0.1:<port>/dev/login?code=<码>&as=<handle>``；码**绑定成员**，``as`` 必须和它一致。
- 码只能用一次，缺省 10 分钟过期；用过、过期、重启服务端后都作废。重新生成：
  ``python -m teamflow_server.devlogin --as alice``（要在您自己的终端里运行）。
- 状态文件在 TEAMFLOW_STATE 目录（缺省为仓库根目录的 ``.local/state``，目录里自带 ``.gitignore``）：
  ``devlogin.json``（0600）**只存码的 sha256**、成员和过期时间，明文码只出现在终端里；
  ``server.json``（0600）记服务端地址和成员名单，给本命令用。
- 第二个成员的链接用 ``localhost``、第一个用 ``127.0.0.1``：两个地址的 cookie 互不影响，
  同一个浏览器里就能同时登录两个人（第三个人起请用无痕窗口或另一个浏览器）。

只用标准库：本命令在终端里随手就跑，不导入 FastAPI。
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
import webbrowser
from collections.abc import Iterator, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlsplit, urlunsplit

from . import config

CODES_FILE = "devlogin.json"
SERVER_FILE = "server.json"
LOCK_FILE = "devlogin.lock"
DEFAULT_TTL_MIN = 10
MAX_TTL_MIN = 60
MAX_CODES = 50  # 同时有效的码最多留这么多条（多了从最早的丢）
MAX_CODE_LEN = 128

# check() 的结果
OK, MISSING, UNKNOWN, EXPIRED, WRONG_HANDLE = "ok", "missing", "unknown", "expired", "handle"


def _digest(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _write_private(path: Path, text: str) -> None:
    """原子写入、权限 0600（先写同目录的临时文件再改名）。"""
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def ensure_state(state: Path | None = None) -> Path:
    """建好状态目录：新建的目录权限 0700（已有的目录不改权限，比如有人把它指到别处）；放一个 .gitignore。"""
    state = Path(state or config.state_dir())
    if not state.exists():
        state.mkdir(parents=True, mode=0o700)
    gi = state / ".gitignore"
    if not gi.exists():
        gi.write_text("# teamflow 本地试用的状态（登录码的哈希、服务端地址），不要提交\n*\n", encoding="utf-8")
    return state


@contextlib.contextmanager
def _locked(state: Path) -> Iterator[None]:
    """服务端消费码、本命令写码，可能同时发生：用一把文件锁串起来（macOS、Linux 都有 fcntl）。"""
    try:
        import fcntl
    except ImportError:  # pragma: no cover - 只支持 macOS、Linux、WSL
        fcntl = None  # type: ignore[assignment]
    fd = os.open(state / LOCK_FILE, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        if fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        if fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _load(state: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads((state / CODES_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    codes = data.get("codes") if isinstance(data, dict) else None
    if not isinstance(codes, list):
        return []
    return [
        c
        for c in codes
        if isinstance(c, dict)
        and isinstance(c.get("sha256"), str)
        and isinstance(c.get("as"), str)
        and isinstance(c.get("exp"), (int, float))
    ]


def _save(state: Path, codes: list[dict[str, Any]]) -> None:
    body = {"v": 1, "note": "一次性登录码：只存 sha256，明文只在终端里出现；用过即删", "codes": codes[-MAX_CODES:]}
    _write_private(state / CODES_FILE, json.dumps(body, ensure_ascii=False, indent=1) + "\n")


def issue(handle: str, *, ttl_s: float = DEFAULT_TTL_MIN * 60, state: Path | None = None, now: float | None = None) -> str:
    """生成一个绑定 handle 的一次性登录码，返回明文（只给调用方打印，不落盘）。"""
    st = ensure_state(state)
    code = secrets.token_urlsafe(24)
    t = time.time() if now is None else now
    with _locked(st):
        codes = [c for c in _load(st) if c["exp"] > t]
        codes.append({"sha256": _digest(code), "as": handle, "exp": t + ttl_s, "made": t})
        _save(st, codes)
    return code


def check(code: str | None, handle: str | None, *, consume: bool, state: Path | None = None, now: float | None = None) -> str:
    """核对登录码：ok / missing / unknown / expired / handle（和绑定的成员不一致）。

    consume=True 时成功即删（一次性）；顺手清掉过期的。as 不一致时不删（打错了还能用对的链接再试）。"""
    if not code or not handle or len(code) > MAX_CODE_LEN:
        return MISSING
    st = Path(state or config.state_dir())
    if not (st / CODES_FILE).exists():
        return UNKNOWN
    d = _digest(code)
    t = time.time() if now is None else now
    with _locked(st):
        codes = _load(st)
        hit = None
        for c in codes:
            if hmac.compare_digest(c["sha256"], d):
                hit = c
        if hit is None:
            return UNKNOWN
        if hit["exp"] <= t:
            if consume:
                _save(st, [c for c in codes if c["exp"] > t])
            return EXPIRED
        if hit["as"] != handle:
            return WRONG_HANDLE
        if consume:
            _save(st, [c for c in codes if c is not hit and c["exp"] > t])
        return OK


def clear(state: Path | None = None) -> None:
    """作废全部登录码（服务端启动时调用：重启之后旧码一律不认）。"""
    st = ensure_state(state)
    with _locked(st):
        _save(st, [])


# ---------------------------------------------------------------------------
# 链接与 server.json
# ---------------------------------------------------------------------------


def _argv_port(argv: Sequence[str]) -> int | None:
    for i, a in enumerate(argv):
        if a == "--port" and i + 1 < len(argv):
            v = argv[i + 1]
        elif a.startswith("--port="):
            v = a.split("=", 1)[1]
        else:
            continue
        if v.isdigit():
            return int(v)
    return None


def guess_base(argv: Sequence[str] | None = None) -> str:
    """服务端自己的地址：TEAMFLOW_PUBLIC_URL；没设时从 uvicorn 的 --port（或 UVICORN_PORT）推断，缺省 8100。"""
    if config.public_url_set():
        return config.public_url()
    port = _argv_port(sys.argv if argv is None else argv)
    env_port = os.environ.get("UVICORN_PORT", "")
    if port is None and env_port.isdigit():
        port = int(env_port)
    return f"http://127.0.0.1:{port or 8100}"


def preferred_host(index: int, base: str) -> str | None:
    """第 1 个成员用 127.0.0.1、第 2 个用 localhost：两个地址的 cookie 分开，同一个浏览器里能同时登录两个人。"""
    host = (urlsplit(base).hostname or "").lower()
    if host not in ("127.0.0.1", "localhost"):
        return None
    return ("127.0.0.1", "localhost")[index % 2]


def login_url(base: str, code: str, handle: str, host: str | None = None) -> str:
    parts = urlsplit(base)
    netloc = parts.netloc
    if host:
        netloc = host + (f":{parts.port}" if parts.port else "")
    return urlunsplit((parts.scheme or "http", netloc, "/dev/login", urlencode({"code": code, "as": handle}), ""))


def write_server_info(base: str, members: list[str], hosts: dict[str, str | None], state: Path | None = None) -> None:
    st = ensure_state(state)
    info = {
        "base": base,
        "members": members,
        "hosts": {h: v for h, v in hosts.items() if v},
        "pid": os.getpid(),
        "started": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    _write_private(st / SERVER_FILE, json.dumps(info, ensure_ascii=False, indent=1) + "\n")


def read_server_info(state: Path | None = None) -> dict[str, Any] | None:
    try:
        data = json.loads((Path(state or config.state_dir()) / SERVER_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def startup(
    members: list[tuple[str, str]], *, base: str | None = None, state: Path | None = None, ttl_s: float = DEFAULT_TTL_MIN * 60
) -> list[tuple[str, str, str]]:
    """服务端启动时调用：作废旧码、写 server.json、每个成员一个新码。返回 [(handle, 姓名, 登录链接)]。"""
    st = ensure_state(state)
    b = base or guess_base()
    hosts = {h: preferred_host(i, b) for i, (h, _) in enumerate(members)}
    clear(st)
    write_server_info(b, [h for h, _ in members], hosts, st)
    return [(h, name, login_url(b, issue(h, ttl_s=ttl_s, state=st), h, hosts[h])) for h, name in members]


def banner(links: list[tuple[str, str, str]], ttl_min: int = DEFAULT_TTL_MIN) -> str:
    """服务端启动时打到 stderr 的几行（每行都以 teamflow-server: 开头）。"""
    out = [f"teamflow-server: 本地试用登录链接（每个只能用一次，{ttl_min} 分钟内有效，重启服务端后作废）："]
    width = max((len(h) for h, _, _ in links), default=0)
    for h, name, url in links:
        out.append(f"teamflow-server:   {h.ljust(width)}  {url}")
    out.append(
        "teamflow-server: 两个人的链接分别用 127.0.0.1 和 localhost，同一个浏览器里能同时登录；"
        "过期或用过后，在您自己的终端运行 python -m teamflow_server.devlogin --as <handle> 重新生成。"
    )
    return "\n".join(out)


def _pid_alive(pid: Any) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m teamflow_server.devlogin",
        description="给本机试用的网页生成一次性登录链接（只在 TEAMFLOW_DEV_ENDPOINTS=1 的本地开发模式下有用）。",
    )
    ap.add_argument("--as", dest="handle", required=True, help="以哪个成员的身份登录，例如 alice")
    ap.add_argument("--ttl", type=int, default=DEFAULT_TTL_MIN, help=f"有效分钟数，1–{MAX_TTL_MIN}，默认 {DEFAULT_TTL_MIN}")
    ap.add_argument("--host", choices=("127.0.0.1", "localhost"), help="链接用哪个地址（缺省按成员分开，见说明）")
    ap.add_argument("--open", action="store_true", help="生成后用默认浏览器打开")
    args = ap.parse_args(argv)

    # 登录码等于"本人在网页上的身份"。agent（Claude Code 的 Bash）里没有终端，不给它发。
    # 这只是减速带：Codex 的 exec 工具能申请伪终端，同一系统用户的进程也能读服务端的 stderr。
    if not sys.stdin.isatty():
        print(
            "devlogin：请在您自己的终端里运行。登录码就是您在网页上的身份，不要让 agent 替您生成。",
            file=sys.stderr,
        )
        return 2
    state = config.state_dir()
    info = read_server_info(state)
    if info is None:
        print(
            f"devlogin：没找到 {state / SERVER_FILE}。请先用 TEAMFLOW_DEV_ENDPOINTS=1 启动服务端，"
            "并确认这里的 TEAMFLOW_STATE 和服务端一致。",
            file=sys.stderr,
        )
        return 1
    handle = args.handle.strip().lstrip("@").lower()
    members = [m for m in info.get("members") or [] if isinstance(m, str)]
    if handle not in members:
        print(f"devlogin：没有叫 {args.handle} 的成员。可选的有：{'、'.join(members) or '（无）'}。", file=sys.stderr)
        return 2
    if not _pid_alive(info.get("pid")):
        print("devlogin：注意，记录里的服务端进程已经不在了；先启动服务端，链接才能用。", file=sys.stderr)
    ttl = max(1, min(int(args.ttl), MAX_TTL_MIN))
    code = issue(handle, ttl_s=ttl * 60, state=state)
    host = args.host or (info.get("hosts") or {}).get(handle)
    url = login_url(str(info.get("base") or guess_base([])), code, handle, host)
    print(url)
    print(f"devlogin：{handle} 的登录链接 {ttl} 分钟内有效，只能用一次。", file=sys.stderr)
    if args.open:
        webbrowser.open(url)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
