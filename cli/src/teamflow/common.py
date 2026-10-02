"""快速路径共用的小工具：状态目录、错误日志、凭据、原子写文件。

只导入 os / sys / time。连 json 都不导入：`import json` 会带进 re、enum，冷启动要多花约 9ms，
而 UserPromptSubmit 的目标是 p95 ≤ 30ms。读 JSON 直接用 C 实现的 _json 扫描器（json.loads 内部用的就是它），
写 JSON 用下面手写的 dumps（快速路径只写 dict/list/str/数字/bool/None）。
"""

import os
import sys
import time

CLIENTS = ("claude", "codex")
# --client 的短名 → 服务端的 client 枚举（api_token.client）
WIRE_CLIENT = {"claude": "claude_code", "codex": "codex"}
LOG_MAX_BYTES = 512 * 1024


def state_dir() -> str:
    d = os.environ.get("TEAMFLOW_STATE_DIR")
    if not d:
        d = os.path.join(os.path.expanduser("~"), ".local", "state", "teamflow")
    return d


def ensure_dir(path: str) -> str:
    os.makedirs(path, mode=0o700, exist_ok=True)
    return path


def log(msg: str) -> None:
    """写错误日志；本身永不抛异常。不要把 token 写进来。"""
    try:
        d = ensure_dir(state_dir())
        path = os.path.join(d, "log")
        try:
            if os.path.getsize(path) > LOG_MAX_BYTES:
                os.replace(path, path + ".1")
        except OSError:
            pass
        line = "%s pid=%d %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), os.getpid(), msg)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.write(fd, line.encode("utf-8", "replace"))
        finally:
            os.close(fd)
    except Exception:
        pass


def log_exc(where: str) -> None:
    et, ev, _ = sys.exc_info()
    tb = ev.__traceback__ if ev is not None else None
    loc = ""
    while tb is not None:
        loc = "%s:%d" % (os.path.basename(tb.tb_frame.f_code.co_filename), tb.tb_lineno)
        tb = tb.tb_next
    log("%s error %s: %s @%s" % (where, et.__name__ if et else "?", ev, loc))


class _ScanCtx:
    # _json.make_scanner 从这个对象上读这些属性（与 json.JSONDecoder 相同）
    strict = True
    object_hook = None
    object_pairs_hook = None
    parse_float = float
    parse_int = int
    parse_constant = float  # NaN / Infinity / -Infinity
    memo = {}


_scanner = None


def loads(data):
    """json.loads 的快速版：bytes 按 UTF-8 解码；语法错误一律抛 ValueError。"""
    global _scanner
    if isinstance(data, (bytes, bytearray)):
        data = bytes(data).decode("utf-8")
    if _scanner is None:
        try:
            import _json

            _scanner = _json.make_scanner(_ScanCtx())
        except (ImportError, AttributeError):
            import json

            return json.loads(data)
    start = len(data) - len(data.lstrip(" \t\n\r"))
    try:
        obj, end = _scanner(data, start)
    except StopIteration:
        raise ValueError("JSON 为空或无法解析") from None
    except Exception as e:  # noqa: BLE001 - C 扫描器报错时会尝试导入 json.decoder，类型不稳定
        raise ValueError("JSON 无法解析：%s" % e) from None
    if data[end:].strip(" \t\n\r"):
        raise ValueError("JSON 后面还有多余内容")
    return obj


def _str(s: str) -> str:
    # 与 json.dumps(ensure_ascii=False) 相同，另外把 U+2028/2029、DEL 和孤立代理项转成 \u 转义：
    # 前者让 JS 系解析器也安全，后者否则在 encode("utf-8") 时抛错（"\ud800" 这种输入能从 JSON 里解出来）。
    out = ['"']
    for c in s:
        o = ord(c)
        if c == '"' or c == "\\":
            out.append("\\" + c)
        elif o < 0x20 or o == 0x7F or 0xD800 <= o <= 0xDFFF or o == 0x2028 or o == 0x2029:
            out.append("\\u%04x" % o)
        else:
            out.append(c)
    out.append('"')
    return "".join(out)


def dumps(obj) -> str:
    """紧凑 JSON 编码，不导入 json。只认 dict / list / tuple / str / int / float / bool / None。

    hook 输出、会话状态、spool、请求体都只用这几种类型。键一律转成 str；
    非有限浮点数写成 null（JSON 没有 NaN）；其他类型抛 TypeError。
    """
    t = type(obj)
    if t is str:
        return _str(obj)
    if obj is None:
        return "null"
    if obj is True:
        return "true"
    if obj is False:
        return "false"
    if t is int:
        return str(obj)
    if t is float:
        return repr(obj) if obj - obj == 0 else "null"
    if t is dict:
        return "{" + ",".join("%s:%s" % (_str(str(k)), dumps(v)) for k, v in obj.items()) + "}"
    if t is list or t is tuple:
        return "[" + ",".join([dumps(v) for v in obj]) + "]"
    raise TypeError("dumps 不支持 %s" % t.__name__)


def read_json(path: str, default=None):
    try:
        with open(path, "rb") as f:
            return loads(f.read())
    except (OSError, ValueError):
        return default


def write_json_atomic(path: str, data, mode: int = 0o600) -> None:
    d = os.path.dirname(path)
    ensure_dir(d)
    tmp = os.path.join(d, ".tmp-%d-%s" % (os.getpid(), os.urandom(4).hex()))
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(dumps(data).encode("utf-8"))
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def cache_path(ws_slug: str, client: str) -> str:
    """收件箱缓存文件。放在 common 里：UserPromptSubmit 只读缓存，不必为一个路径导入 spool。"""
    return os.path.join(state_dir(), "cache", safe_name(ws_slug), client + ".json")


def safe_name(s: str, limit: int = 64) -> str:
    """把会话 ID、workspace slug 之类变成安全的文件名片段。"""
    out = "".join(c if (c.isascii() and (c.isalnum() or c in "-_.")) else "_" for c in str(s))
    out = out.strip(".") or "_"
    return out[:limit]


# ---------------------------------------------------------------- credentials


class CredError(Exception):
    pass


def load_creds(path: str) -> dict:
    if not path or not os.path.isabs(path):
        raise CredError("--cred 必须是绝对路径")
    data = read_json(path)
    if not isinstance(data, dict) or not isinstance(data.get("workspaces"), dict):
        raise CredError("凭据文件不存在或格式不对：%s" % path)
    return data


def _pattern_matches(pattern: str, cwd: str, remote: str | None) -> bool:
    import fnmatch

    pat = os.path.expanduser(pattern)
    if pat.startswith("/"):
        # 路径式：目录本身和它下面的任何子目录都算
        p = pat.rstrip("/") or "/"
        return fnmatch.fnmatchcase(cwd, p) or fnmatch.fnmatchcase(cwd, p.rstrip("/") + "/*")
    # 不是路径：当作 git remote 的匹配式，写成 host/path（如 github.com/acme/* 或 github.com/acme/api）
    norm = normalize_remote(remote)
    if not norm:
        return False
    pat = pat.rstrip("/")
    if "*" in pat or "?" in pat:
        return fnmatch.fnmatchcase(norm, pat)
    return norm == pat or norm.startswith(pat + "/")


def normalize_remote(remote: str | None) -> str | None:
    """https://u@github.com/acme/api.git、git@github.com:acme/api.git → github.com/acme/api"""
    if not remote:
        return None
    r = remote.strip()
    if "://" in r:
        r = r.split("://", 1)[1]
        host, _, path = r.partition("/")
        host = host.rsplit("@", 1)[-1]
        r = host + "/" + path
    else:
        head, sep, path = r.partition(":")
        if sep and "/" not in head:
            r = head.rsplit("@", 1)[-1] + "/" + path
    r = r.split("?", 1)[0].split("#", 1)[0].rstrip("/")
    if r.endswith(".git"):
        r = r[:-4]
    return r.lower() or None


def select_workspace(creds: dict, cwd: str | None, remote: str | None = None):
    """按 cwd（以及可选的 git remote）匹配 repo_patterns 选 workspace，匹配不到用 default。

    返回 (slug, ws_dict)；没有可用 workspace 时抛 CredError。
    """
    wss = creds.get("workspaces") or {}
    cwd = os.path.abspath(cwd) if cwd else os.getcwd()
    for slug, ws in wss.items():
        if not isinstance(ws, dict):
            continue
        for pat in ws.get("repo_patterns") or []:
            if isinstance(pat, str) and pat and _pattern_matches(pat, cwd, remote):
                return slug, ws
    slug = creds.get("default")
    if isinstance(slug, str) and isinstance(wss.get(slug), dict):
        return slug, wss[slug]
    if len(wss) == 1:
        slug = next(iter(wss))
        if isinstance(wss[slug], dict):
            return slug, wss[slug]
    raise CredError("凭据文件里没有可用的 workspace")


def token_for(ws: dict, client: str) -> str:
    tok = (ws.get("tokens") or {}).get(client)
    if not isinstance(tok, str) or not tok.startswith("tf_pat_"):
        raise CredError("缺少 %s 的 token" % client)
    # 只允许 URL 安全字符：既防请求头注入，也避免 http.client 把整段 token 写进异常信息再落进日志
    if len(tok) > 256 or not all(c.isascii() and (c.isalnum() or c in "_-.") for c in tok):
        raise CredError("%s 的 token 含有非法字符" % client)
    return tok


def api_base(ws: dict) -> str:
    url = ws.get("api_url")
    if not isinstance(url, str) or not (url.startswith("http://") or url.startswith("https://")):
        raise CredError("api_url 无效")
    return url.rstrip("/")


def machine_id() -> str:
    path = os.path.join(state_dir(), "machine_id")
    try:
        with open(path) as f:
            mid = f.read().strip()
        if mid:
            return mid
    except OSError:
        pass
    mid = os.urandom(8).hex()
    try:
        ensure_dir(state_dir())
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(mid)
    except FileExistsError:
        with open(path) as f:
            return f.read().strip() or mid
    except OSError:
        pass
    return mid
