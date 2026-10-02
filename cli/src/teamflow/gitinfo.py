"""git 读取：每个调用都有超时（默认 300ms），失败返回 None，不抛异常。"""

import os
import re

GIT_TIMEOUT = 0.3
_SHA_RE = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")


def _env():
    env = dict(os.environ)
    # 不弹任何交互、不读系统级 pager / 凭据助手
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env.pop("GIT_DIR", None)
    env.pop("GIT_WORK_TREE", None)
    return env


def _spawn(cwd: str, args: list):
    import subprocess

    return subprocess.Popen(
        ["git", "-C", cwd, *args],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=_env(),
        close_fds=True,
    )


def _finish(p, timeout: float):
    import subprocess

    try:
        out, _ = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        try:
            p.communicate(timeout=0.1)
        except Exception:
            pass
        return None
    if p.returncode != 0:
        return None
    return out.decode("utf-8", "replace")


def run(cwd: str, args: list, timeout: float = GIT_TIMEOUT):
    try:
        return _finish(_spawn(cwd, args), timeout)
    except OSError:
        return None


def strip_credentials(url: str | None) -> str | None:
    """去掉 remote URL 里的用户名、密码、query 和 fragment。"""
    if not url:
        return None
    url = url.strip()
    if "://" in url:
        from urllib.parse import urlsplit, urlunsplit

        try:
            u = urlsplit(url)
            host = u.hostname or ""
            if u.port:
                host = "%s:%d" % (host, u.port)
            return urlunsplit((u.scheme, host, u.path, "", ""))
        except ValueError:
            return None
    # scp 形式：user@host:path → host:path
    if "@" in url.split(":", 1)[0]:
        url = url.split("@", 1)[1]
    return url.split("?", 1)[0].split("#", 1)[0]


def session_info(cwd: str, timeout: float = GIT_TIMEOUT) -> dict:
    """并行读 remote、branch、HEAD，各自 300ms 超时。"""
    out = {}
    if not cwd or not os.path.isdir(cwd):
        return out
    try:
        p_rev = _spawn(cwd, ["rev-parse", "HEAD", "--abbrev-ref", "HEAD"])
        p_remote = _spawn(cwd, ["config", "--get", "remote.origin.url"])
    except OSError:
        return out
    rev = _finish(p_rev, timeout)
    remote = _finish(p_remote, timeout)
    if rev:
        lines = rev.split()
        if lines and _SHA_RE.fullmatch(lines[0]):
            out["head"] = lines[0]
        if len(lines) > 1 and lines[1] != "HEAD":
            out["branch"] = lines[1][:200]
    r = strip_credentials(remote.strip() if remote else None)
    if r:
        out["repo"] = r[:300]
    return out


def head(cwd: str, timeout: float = GIT_TIMEOUT):
    out = run(cwd, ["rev-parse", "HEAD"], timeout)
    if out:
        s = out.strip()
        if _SHA_RE.fullmatch(s):
            return s
    return None


def toplevel(cwd: str, timeout: float = GIT_TIMEOUT):
    """仓库根目录（只在本机用：按仓库记"没被服务端记下的提交"提醒，不上传）。"""
    out = run(cwd, ["rev-parse", "--show-toplevel"], timeout)
    s = out.strip() if out else ""
    return s if s and os.path.isabs(s) else None


def user_email(cwd: str, timeout: float = GIT_TIMEOUT):
    out = run(cwd, ["config", "--get", "user.email"], timeout)
    return out.strip().lower() if out and out.strip() else None


def new_commits(cwd: str, last: str, cur: str, emails: set, limit: int = 5, timeout: float = GIT_TIMEOUT):
    """last..cur 之间的提交：本人邮箱的最多 limit 条 (sha, 标题)，其他作者只计数。

    等价于 `git rev-list <last>..HEAD --author=<本人邮箱>`，只是邮箱做精确匹配（--author 是正则）。
    返回 (own_list, own_total, other_count)；读不到返回 None。
    """
    if not (_SHA_RE.fullmatch(last or "") and _SHA_RE.fullmatch(cur or "")):
        return None
    out = run(
        cwd,
        ["log", "--no-color", "--max-count=200", "--format=%H%x1f%ae%x1f%s", "%s..%s" % (last, cur)],
        timeout,
    )
    if out is None:
        return None
    own, own_total, other = [], 0, 0
    for line in out.splitlines():
        parts = line.split("\x1f", 2)
        if len(parts) != 3:
            continue
        sha, email, title = parts
        if email.strip().lower() in emails:
            own_total += 1
            if len(own) < limit:
                own.append({"sha": sha, "title": title[:200]})
        else:
            other += 1
    return own, own_total, other
