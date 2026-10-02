"""本地 spool：hook 只写文件，分离的 `teamflow flush` 负责上传。

- 每条记录一个文件，文件名就是幂等键 hash(client, session, event, turn)；
  先写临时文件再 os.link 到最终名（目标已存在就失败，等价 O_EXCL），所以重复写入天然去重。
- 已成功上传的键留一个空的 sent/<key> 标记 8 天，防止同一事件被重新写入后再发一遍。
- flush 用 O_EXCL 创建的锁文件保证同一时间只有一个上传者。
- 5xx、429、408、网络错误：指数退避 5 秒到 5 分钟；其他 4xx：移进 dead/，不再重试。
- 同一会话按写入顺序上报：更早的记录还在退避时，同会话后写的记录等它到期一起发（_due），
  免得 end 先到、服务端把迟到的 tool_map 判成"会话已结束"。
- 一批最多 BATCH_MAX 条、编码后不超过 BATCH_BYTES：服务端和 nginx 的请求体上限都是 64KB，超了整批 413。
  万一还是 413（服务端上限更小），对半拆开重发；只有单条就超限的才进 dead/。
- 心跳类记录 24 小时后丢弃，提交类记录保留 7 天。
- 服务端逐条结果 ``st: "no_repo"``（重放时是 409 加 ``was: "no_repo"``）：这一回合的提交服务端认不出是哪个仓库
  （仓库没有 origin），会话照常登记，提交一条没记。按仓库目录记到 notices/unrecorded.json（条数、目录、时间、原因），
  teamflow doctor 逐个仓库报出来；同一个仓库之后带着仓库地址成功上报了提交，只清掉这个仓库的那一项。
  Stop 发现补上的 origin 属于另一个 workspace 时，提交不发，也记在这里（原因 other_ws，见 hooks.stop）。
"""

import os
import time

from teamflow import common

BATCH_MAX = 100
BATCH_BYTES = 60 * 1024  # 服务端 /api/* 与 nginx 的请求体上限是 64KB，留出 {"v":1,"items":[]} 和余量
BACKOFF_MIN = 5
BACKOFF_MAX = 300
HEARTBEAT_TTL = 24 * 3600
COMMIT_TTL = 7 * 24 * 3600
SENT_TTL = 8 * 24 * 3600
LOCK_STALE = 600
DEFAULT_BUDGET = 60.0
MAX_RETRIES = 3
RETRYABLE = (408, 425, 429)
NOTICE_TTL = 7 * 24 * 3600
NOTICE_MAX_DIRS = 20
UNRECORDED_FILE = "unrecorded.json"


def spool_dir() -> str:
    return os.path.join(common.state_dir(), "spool")


def _sha256(data: bytes):
    """sha256 对象。先用 CPython 内置的 _sha2（3.12+）/_sha256（3.11）：import hashlib 会加载 OpenSSL 的 _hashlib，
    冷启动多约 3ms，而 PostToolUse 是同步 hook，每次 teamflow 工具调用都要跑一次。摘要与 hashlib 完全相同。"""
    try:
        from _sha2 import sha256
    except ImportError:
        try:
            from _sha256 import sha256
        except ImportError:
            from hashlib import sha256
    return sha256(data)


def idem_key(client: str, session: str, event: str, turn: str) -> str:
    raw = "\x1f".join((client, session, event, turn)).encode("utf-8", "replace")
    return _sha256(raw).hexdigest()[:40]


def write(rec: dict) -> bool:
    """写一条记录；同一个幂等键已经在 spool 里或已发送过，返回 False。"""
    key = rec["key"]
    d = common.ensure_dir(spool_dir())
    if os.path.exists(os.path.join(d, "sent", key)):
        return False
    final = os.path.join(d, key + ".json")
    tmp = os.path.join(d, ".tmp-%d-%s" % (os.getpid(), os.urandom(4).hex()))
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(common.dumps(rec).encode("utf-8"))
        try:
            os.link(tmp, final)
        except FileExistsError:
            return False
        return True
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def notices_dir() -> str:
    """提醒放在 spool 目录外面：spool 目录里的 *.json 都会被当成待上传的记录。"""
    return os.path.join(common.state_dir(), "notices")


def _unrecorded_path() -> str:
    return os.path.join(notices_dir(), UNRECORDED_FILE)


def _load_unrecorded(now: float) -> dict:
    data = common.read_json(_unrecorded_path())
    dirs = data.get("dirs") if isinstance(data, dict) else None
    out = {}
    for k, v in (dirs.items() if isinstance(dirs, dict) else ()):
        if (isinstance(k, str) and k and isinstance(v, dict) and type(v.get("n")) is int and v["n"] > 0
                and now - float(v.get("last") or 0) <= NOTICE_TTL):
            out[k] = v
    return out


def _save_unrecorded(dirs: dict) -> None:
    try:
        if dirs:
            common.write_json_atomic(os.path.join(common.ensure_dir(notices_dir()), UNRECORDED_FILE), {"v": 2, "dirs": dirs})
        else:
            os.unlink(_unrecorded_path())
    except OSError:
        pass


def unrecorded(now: float | None = None) -> list:
    """最近 7 天里没被服务端记下的提交，按仓库目录分开，最近的在前：
    [{"dir", "name", "n", "first", "last", "why", "ws", "want_ws"}]。why 是 no_repo 或 other_ws。"""
    now = time.time() if now is None else now
    dirs = _load_unrecorded(now)
    return [dict(v, dir=k) for k, v in sorted(dirs.items(), key=lambda kv: -float(kv[1].get("last") or 0))]


def note_unrecorded(dir_key: str, name: str, n: int, why: str, now: float | None = None, ws=None, want_ws=None) -> None:
    """记一笔没被服务端记下的提交（只有条数、目录、时间、workspace 名，不记提交标题）。"""
    now = time.time() if now is None else now
    if not isinstance(dir_key, str) or not dir_key or n <= 0:
        return
    dirs = _load_unrecorded(now)
    old = dirs.get(dir_key) or {}
    dirs[dir_key] = {
        "name": (name if isinstance(name, str) else "")[:80],
        "n": int(old.get("n") or 0) + int(n),
        "first": old.get("first") or now,
        "last": now,
        "why": why,
        "ws": ws if isinstance(ws, str) else None,
        "want_ws": want_ws if isinstance(want_ws, str) else None,
    }
    if len(dirs) > NOTICE_MAX_DIRS:
        for k, _ in sorted(dirs.items(), key=lambda kv: float(kv[1].get("last") or 0))[: len(dirs) - NOTICE_MAX_DIRS]:
            del dirs[k]
    _save_unrecorded(dirs)


def clear_unrecorded(dir_key: str) -> None:
    """这个仓库带着仓库地址成功上报了提交：只清它自己的那一项，别的仓库的提醒留着。"""
    dirs = _load_unrecorded(time.time())
    if dir_key in dirs:
        del dirs[dir_key]
        _save_unrecorded(dirs)


def _rec_dir(rec) -> str:
    """提醒按哪个目录记：Stop 写进记录的仓库根目录（只在本地，不上传）；旧记录没有就用目录名。"""
    d = rec.get("dir")
    if isinstance(d, str) and d:
        return d
    name = (rec.get("item") or {}).get("cwd_name")
    return name if isinstance(name, str) and name else "?"


def _note_no_repo(rec, dropped, now):
    item = rec.get("item") or {}
    name = item.get("cwd_name") if isinstance(item.get("cwd_name"), str) else ""
    note_unrecorded(_rec_dir(rec), name, dropped, "no_repo", now, ws=rec.get("ws"))
    common.log("spool: 服务端没记下 %d 个提交：仓库 %s 没有 origin，认不出是哪个仓库" % (dropped, name or "?"))


def _commit_count(rec) -> int:
    """这条记录里本人的提交数：发出去的（最多 5 条）加 own_more。"""
    item = rec.get("item") or {}
    commits = item.get("commits")
    n = sum(1 for c in commits if isinstance(c, dict)) if isinstance(commits, list) else 0
    more = item.get("own_more")
    return n + more if n and type(more) is int and 0 < more <= 1000 else n


def counts() -> dict:
    d = spool_dir()

    def n(path):
        try:
            return sum(1 for x in os.listdir(path) if x.endswith(".json"))
        except OSError:
            return 0

    return {"pending": n(d), "dead": n(os.path.join(d, "dead"))}


# ---------------------------------------------------------------- lock


class Lock:
    def __init__(self, d: str):
        self.path = os.path.join(d, ".lock")
        self.held = False

    def _try(self) -> bool:
        try:
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            return False
        with os.fdopen(fd, "w") as f:
            f.write("%d %d" % (os.getpid(), int(time.time())))
        self.held = True
        return True

    def _stale(self) -> bool:
        try:
            st = os.stat(self.path)
            with open(self.path) as f:
                pid = int((f.read().split() or ["0"])[0])
        except (OSError, ValueError):
            return True
        if time.time() - st.st_mtime > LOCK_STALE:
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return True
            except PermissionError:
                return False
        return False

    def acquire(self, wait: float = 3.0) -> bool:
        deadline = time.time() + wait
        while True:
            if self._try():
                return True
            if self._stale():
                try:
                    os.unlink(self.path)
                except OSError:
                    pass
                continue
            if time.time() >= deadline:
                return False
            time.sleep(0.1)

    def release(self):
        if self.held:
            try:
                os.unlink(self.path)
            except OSError:
                pass
            self.held = False


# ---------------------------------------------------------------- flush


def _load(d):
    out = []
    try:
        names = os.listdir(d)
    except OSError:
        return out
    for name in names:
        if not name.endswith(".json") or name.startswith("."):
            continue
        path = os.path.join(d, name)
        rec = common.read_json(path)
        if not isinstance(rec, dict) or not isinstance(rec.get("item"), dict):
            _move(path, os.path.join(d, "dead"), "unreadable")
            continue
        out.append((path, rec))
    return out


def _move(path, dest_dir, reason):
    try:
        common.ensure_dir(dest_dir)
        os.replace(path, os.path.join(dest_dir, os.path.basename(path)))
    except OSError:
        pass
    common.log("spool dead-letter %s: %s" % (os.path.basename(path), reason))


def _done(d, path, rec):
    try:
        sent = common.ensure_dir(os.path.join(d, "sent"))
        open(os.path.join(sent, rec["key"]), "a").close()
    except OSError:
        pass
    try:
        os.unlink(path)
    except OSError:
        pass


def _retry(path, rec, now, why):
    rec["attempts"] = int(rec.get("attempts") or 0) + 1
    delay = min(BACKOFF_MAX, BACKOFF_MIN * (2 ** (rec["attempts"] - 1)))
    rec["next_try"] = now + delay
    rec["last_error"] = why[:200]
    try:
        common.write_json_atomic(path, rec)
    except OSError:
        pass


def _order_key(rec):
    sid = (rec.get("item") or {}).get("session_id")
    if not isinstance(sid, str) or not sid:
        return None
    return (rec.get("cred") or "", rec.get("ws") or "", rec.get("client") or "", sid)


def _due(recs, now):
    """这一轮可以发的记录，按写入时间排序。

    同一会话按写入顺序上报：同会话里更早写的记录还在退避时，后写的也先不发，等它到期一起发。
    否则 Stop 那一轮连不上服务端、tool_map 进了退避，服务端恢复后 SessionEnd 的 end 会先单独送到，
    服务端把迟到的 tool_map 判成"会话已结束"（403 ignored），映射丢了还进 dead-letter（D40）。
    同一批里的先后由服务端处理（tool_map 放到最后），这里只保证它们落在同一批或按写入顺序到达。"""
    held = {}
    for _, r in recs:
        if float(r.get("next_try") or 0) > now:
            k = _order_key(r)
            if k is not None:
                c = float(r.get("created") or 0)
                held[k] = min(held.get(k, c), c)
    out = []
    for p, r in recs:
        if float(r.get("next_try") or 0) > now:
            continue
        k = _order_key(r)
        if k in held and float(r.get("created") or 0) >= held[k]:
            continue
        out.append((p, r))
    out.sort(key=lambda e: float(e[1].get("created") or 0))
    return out


def _expired(rec, now) -> bool:
    ttl = COMMIT_TTL if rec.get("kind") == "commit" else HEARTBEAT_TTL
    return now - float(rec.get("created") or 0) > ttl


def _chunks(entries, max_items=BATCH_MAX, max_bytes=BATCH_BYTES):
    """按条数和编码后的字节数切批（M0 第三轮复审：100 条带长提交标题的条目能到 90KB，整批 413 后全进 dead/）。
    单条就超过 max_bytes 的自成一批，由服务端判定（413 就进 dead/）。"""
    out, cur, size = [], [], 0
    for e in entries:
        n = len(common.dumps(e[1].get("item")).encode("utf-8")) + 1
        if cur and (len(cur) >= max_items or size + n > max_bytes):
            out.append(cur)
            cur, size = [], 0
        cur.append(e)
        size += n
    if cur:
        out.append(cur)
    return out


def _send_group(d, cred, ws_slug, client, entries, now):
    """entries: [(path, rec)]，同一个 (凭据, workspace, client)。"""
    from teamflow import net

    try:
        creds = common.load_creds(cred)
        ws = creds["workspaces"].get(ws_slug)
        if not isinstance(ws, dict):
            raise common.CredError("workspace %s 不在凭据文件里" % ws_slug)
        token = common.token_for(ws, client)
        base = common.api_base(ws)
    except common.CredError as e:
        for path, _ in entries:
            _move(path, os.path.join(d, "dead"), "cred: %s" % e)
        return
    queue = _chunks(entries)
    while queue:
        chunk = queue.pop(0)
        keys = [rec["key"] for _, rec in chunk]
        batch_key = idem_key(client, ws_slug, "batch", ",".join(sorted(keys)))
        body = {"v": 1, "items": [rec["item"] for _, rec in chunk]}
        try:
            status, _, raw = net.request(
                "POST",
                base + "/api/v1/hooks/batch",
                headers=net.api_headers(token, common.WIRE_CLIENT[client], idem=batch_key),
                body=body,
                timeout=10.0,
            )
        except net.NetError as e:
            for path, rec in chunk:
                _retry(path, rec, now, "net: %s" % e)
            continue
        if status >= 500 or status in RETRYABLE:
            for path, rec in chunk:
                _retry(path, rec, now, "http %d" % status)
            continue
        if status == 413 and len(chunk) > 1:  # 服务端上限比我们估的小：对半拆开重发，不整批丢
            mid = len(chunk) // 2
            queue[:0] = [chunk[:mid], chunk[mid:]]
            continue
        if not 200 <= status < 300:
            for path, _ in chunk:
                _move(path, os.path.join(d, "dead"), "http %d" % status)
            continue
        resp = net.parse_json(raw)
        results = {}
        if isinstance(resp, dict) and isinstance(resp.get("results"), list):
            for r in resp["results"]:
                if isinstance(r, dict) and isinstance(r.get("key"), str) and type(r.get("status")) is int:
                    results[r["key"]] = r
        for path, rec in chunk:
            r = results.get(rec["key"]) or {}
            st = r.get("status", 200)  # 没有逐条结果：整批 2xx 视为都成功
            if 200 <= st < 300 or st == 409:  # 409：服务端已有这条（幂等重放）
                _done(d, path, rec)
                has_repo = bool((rec.get("item") or {}).get("repo"))
                ncommits = _commit_count(rec)
                # 409 重放：第一次的响应丢了。服务端会带回 was；旧服务端不带，但没有 repo 的提交服务端一定没记
                if r.get("st") == "no_repo" or r.get("was") == "no_repo" or (st == 409 and ncommits and not has_repo):
                    n = r.get("dropped")
                    _note_no_repo(rec, n if type(n) is int and 0 < n <= 1100 else max(1, ncommits), now)
                elif ncommits and has_repo:
                    clear_unrecorded(_rec_dir(rec))  # 这个仓库带着地址的提交记下了：只清它自己的提醒
            elif st >= 500 or st in RETRYABLE:
                _retry(path, rec, now, "item %d" % st)
            else:
                _move(path, os.path.join(d, "dead"), "item %d" % st)


def _prune_sent(d, now):
    sd = os.path.join(d, "sent")
    try:
        for name in os.listdir(sd):
            p = os.path.join(sd, name)
            try:
                if now - os.stat(p).st_mtime > SENT_TTL:
                    os.unlink(p)
            except OSError:
                pass
    except OSError:
        pass


def flush(budget: float | None = None, max_retries: int = MAX_RETRIES) -> dict:
    """上传 spool。返回统计 {sent, retry, dead, locked}。

    budget：本次调用里愿意为退避重试等待的总秒数（默认 60；环境变量 TEAMFLOW_FLUSH_BUDGET 覆盖）。
    """
    if budget is None:
        try:
            budget = float(os.environ.get("TEAMFLOW_FLUSH_BUDGET", DEFAULT_BUDGET))
        except ValueError:
            budget = DEFAULT_BUDGET
    d = common.ensure_dir(spool_dir())
    lock = Lock(d)
    if not lock.acquire():
        return {"locked": True}
    start = time.time()
    try:
        for rnd in range(max_retries + 1):
            now = time.time()
            recs = []
            for path, rec in _load(d):
                if _expired(rec, now):
                    try:
                        os.unlink(path)
                    except OSError:
                        pass
                    common.log("spool expired %s" % rec.get("key"))
                    continue
                recs.append((path, rec))
            due = _due(recs, now)
            groups = {}
            for p, r in due:
                k = (r.get("cred") or "", r.get("ws") or "", r.get("client") or "")
                groups.setdefault(k, []).append((p, r))
            for (cred, ws_slug, client), entries in groups.items():
                if client not in common.WIRE_CLIENT:
                    for p, _ in entries:
                        _move(p, os.path.join(d, "dead"), "bad client")
                    continue
                _send_group(d, cred, ws_slug, client, entries, now)
            pending = [r for _, r in _load(d)]
            if not pending or rnd == max_retries:
                break
            # 只看还在退避的记录：被 _due 压住的同会话记录 next_try 是 0，要等压住它们的那条到期
            t = time.time()
            later = [float(r.get("next_try") or 0) for r in pending if float(r.get("next_try") or 0) > t]
            wait = (min(later) - t) if later else 0.0
            if wait > budget - (time.time() - start):
                break
            if wait > 0:
                time.sleep(wait)
        _prune_sent(d, time.time())
    finally:
        lock.release()
    c = counts()
    return {"locked": False, "pending": c["pending"], "dead": c["dead"]}


# ---------------------------------------------------------------- cache


cache_path = common.cache_path


def save_cache(ws_slug: str, client: str, data: dict, etag=None, cursor=None) -> None:
    rec = {"fetched_at": time.time(), "data": data}
    if isinstance(etag, str) and len(etag) < 200:
        rec["etag"] = etag
    if isinstance(cursor, (str, int)) and len(str(cursor)) < 200:
        rec["cursor"] = str(cursor)
    common.write_json_atomic(cache_path(ws_slug, client), rec)


def refresh(cred: str, client: str, ws_slug: str | None = None) -> bool:
    """GET /api/v1/me/delta，把校验过的数据写进本地缓存。"""
    from urllib.parse import quote

    from teamflow import inbox, net

    creds = common.load_creds(cred)
    wss = creds["workspaces"]
    if ws_slug and isinstance(wss.get(ws_slug), dict):
        ws = wss[ws_slug]
    else:
        ws_slug, ws = common.select_workspace(creds, os.getcwd())
    token = common.token_for(ws, client)
    path = cache_path(ws_slug, client)
    cache = common.read_json(path) or {}
    url = common.api_base(ws) + "/api/v1/me/delta"
    if cache.get("cursor"):
        url += "?cursor=" + quote(str(cache["cursor"]), safe="")
    headers = net.api_headers(token, common.WIRE_CLIENT[client])
    if cache.get("etag") and isinstance(cache.get("data"), dict):
        headers["If-None-Match"] = cache["etag"]
    status, h, raw = net.request("GET", url, headers=headers, timeout=5.0)
    if status == 304 and isinstance(cache.get("data"), dict):
        cache["fetched_at"] = time.time()
        common.write_json_atomic(path, cache)
        return True
    if status != 200:
        common.log("refresh http %d" % status)
        return False
    resp = net.parse_json(raw)
    if not isinstance(resp, dict):
        common.log("refresh bad json")
        return False
    save_cache(ws_slug, client, inbox.validate(resp), etag=h.get("etag"), cursor=resp.get("cursor"))
    return True
