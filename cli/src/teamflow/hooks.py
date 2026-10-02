"""hook 的执行体：两端共有的 session-start、prompt、stop、session-end，加上 Claude Code 独有的 tool。

规则（plan 6.4）：
- 永远 fail-open：任何异常都不输出、exit 0，错误写进状态目录的 log。
- 输出只由 inbox.py 的常量模板生成；Claude Code 用固定形状 JSON，Codex 用纯文本（首行是哨兵）。
- prompt 完全忽略 prompt 字段、永不联网、永不拉起子进程（缓存由 Stop 每回合拉起的 flush --refresh 刷新）；
  stop / session-end 只写本地 spool，再拉起分离的 flush。
- tool（PostToolUse，D40）只装在 Claude Code：只认 mcp__teamflow__ 开头的工具，往 spool 写一条
  (session_id, tool_use_id, 工具名) 的映射，不联网、不拉起进程、不输出；由下一次 Stop / SessionEnd 拉起的 flush 上报。
  --client codex 直接退出（Codex 的 tools/call 自带 _meta 会话，不装这个 hook）。
- 不上传 transcript_path、prompt、last_assistant_message、工具入参和工具结果（tool_input、tool_response）。
"""

import os
import sys
import time

from teamflow import common

EVENT_NAMES = {
    "session-start": "SessionStart",
    "prompt": "UserPromptSubmit",
    "stop": "Stop",
    "session-end": "SessionEnd",
    "tool": "PostToolUse",
}
SOURCES = ("startup", "resume", "clear", "compact", "fork")
END_REASONS = ("clear", "resume", "logout", "prompt_input_exit", "other")
STDIN_MAX = 16 * 1024 * 1024
SESSION_START_HTTP_TIMEOUT = 1.0
CACHE_MAX_AGE = 24 * 3600
PROMPT_MIN_INTERVAL = 600
SESSION_STATE_TTL = 7 * 24 * 3600
_SID_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.:")
# PostToolUse：只认我们自己 server 的工具（mcp__<server>__<tool>，cc_hooks.md「Match MCP tools」）。
# 工具名是服务端的常量（6.2，snake_case）。tool_use_id 形如 toolu_012HDfH2mEGmyGFoKMDw5GJw（S3 证据）；
# Bedrock、Vertex 是 toolu_bdrk_…、toolu_vrtx_…。规则与服务端校验 _meta["claudecode/toolUseId"] 的一致
# （server/teamflow_server/service.py TOOL_USE_RE：toolu_ 加 8–80 个字母、数字、下划线）：服务端本来就匹配不上的
# 不写进 spool，免得上报时逐条 422 进 dead-letter。
TOOL_PREFIX = "mcp__teamflow__"
TOOL_NAME_MAX = 64
TOOL_USE_PREFIX = "toolu_"
_TOOL_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_")
_TUID_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")


# ---------------------------------------------------------------- 小工具


def read_stdin() -> dict:
    stdin = sys.stdin
    if stdin is None:
        return {}
    try:
        if stdin.isatty():
            return {}
    except (ValueError, OSError):
        return {}
    raw = stdin.buffer.read(STDIN_MAX + 1)
    if len(raw) > STDIN_MAX:
        raise ValueError("stdin too large")
    data = common.loads(raw) if raw.strip() else None
    if not isinstance(data, dict):
        raise ValueError("hook 输入不是 JSON 对象")
    # 这些字段一律不碰、不留在内存里往下传
    for k in ("prompt", "last_assistant_message", "transcript_path", "tool_input", "tool_response"):
        data.pop(k, None)
    return data


def valid_sid(x):
    if isinstance(x, str) and 0 < len(x) <= 128 and all(c in _SID_CHARS for c in x):
        return x
    return None


def valid_tool_use_id(x):
    if not isinstance(x, str) or not x.startswith(TOOL_USE_PREFIX):
        return None
    rest = x[len(TOOL_USE_PREFIX):]
    if 8 <= len(rest) <= 80 and all(c in _TUID_CHARS for c in rest):
        return x
    return None


def teamflow_tool(name):
    """mcp__teamflow__claim_task → claim_task；不是我们的工具或名字不合格返回 None。"""
    if not isinstance(name, str) or not name.startswith(TOOL_PREFIX):
        return None
    t = name[len(TOOL_PREFIX):]
    if 0 < len(t) <= TOOL_NAME_MAX and "a" <= t[0] <= "z" and all(c in _TOOL_CHARS for c in t):
        return t
    return None


def _cwd(payload) -> str:
    c = payload.get("cwd")
    if isinstance(c, str) and os.path.isabs(c):
        return c
    return os.getcwd()


def emit(client: str, event: str, text: str | None) -> None:
    if not text:
        return
    if client == "claude":
        # 手写的 common.dumps，不导入 json（UserPromptSubmit 输出路径也要守住 30ms）
        out = common.dumps({"hookSpecificOutput": {"hookEventName": EVENT_NAMES[event], "additionalContext": text}})
    else:
        out = text
    data = out.encode("utf-8")
    try:
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()
    except (OSError, ValueError):
        pass


def _state_path(client: str, sid: str) -> str:
    return os.path.join(common.state_dir(), "sessions", "%s-%s.json" % (client, common.safe_name(sid, 128)))


def load_state(client: str, sid: str | None) -> dict:
    if not sid:
        return {}
    st = common.read_json(_state_path(client, sid))
    return st if isinstance(st, dict) else {}


def save_state(client: str, sid: str | None, st: dict) -> None:
    if not sid:
        return
    st["updated"] = time.time()
    common.write_json_atomic(_state_path(client, sid), st)


def _pick_ws(creds: dict, st: dict, cwd: str, remote=None):
    slug = st.get("ws")
    if isinstance(slug, str) and isinstance(creds["workspaces"].get(slug), dict):
        return slug, creds["workspaces"][slug]
    return common.select_workspace(creds, cwd, remote)


def _interactive() -> bool:
    """plan 6.4：能打开 /dev/tty 记为 interactive。

    注意：Claude Code 文档写明 hook 运行在没有控制终端的独立会话里（打不开 /dev/tty），
    Codex 也以 NewSession 方式拉起 hook，所以这个探测在两端多半恒为 False，待 M0 S2/S6 实测。
    """
    try:
        fd = os.open("/dev/tty", os.O_RDONLY | getattr(os, "O_NOCTTY", 0))
    except OSError:
        return False
    os.close(fd)
    return True


def _spawn_flush(client, cred, ws_slug, refresh):
    from teamflow import detach

    detach.spawn_detached(detach.flush_argv(client=client, cred=cred, ws=ws_slug, refresh=refresh))


def _base_item(kind_type: str, key: str, sid: str, client: str) -> dict:
    return {
        "type": kind_type,
        "key": key,
        "session_id": sid,
        "client": common.WIRE_CLIENT[client],
        "ts": int(time.time()),
    }


# ---------------------------------------------------------------- session-start


def _post_session_start(url, headers, body, timeout):
    """整个 HTTP 往返（含 DNS）都限制在 timeout 内：放进守护线程，超时就不等了。"""
    import threading

    from teamflow import net

    box = {}

    def work():
        try:
            box["resp"] = net.request("POST", url, headers=headers, body=body, timeout=timeout)
        except Exception as e:  # noqa: BLE001 - 线程里什么都可能抛
            box["err"] = e

    t = threading.Thread(target=work, daemon=True)
    t.start()
    t.join(timeout + 0.05)
    if "resp" in box:
        return box["resp"], None
    return None, box.get("err") or TimeoutError("session-start timeout")


def session_start(payload: dict, client: str, cred: str) -> None:
    from teamflow import gitinfo, inbox, net, spool

    sid = valid_sid(payload.get("session_id"))
    cwd = _cwd(payload)
    source = payload.get("source") if payload.get("source") in SOURCES else "startup"
    creds = common.load_creds(cred)
    g = gitinfo.session_info(cwd)
    slug, ws = common.select_workspace(creds, cwd, g.get("repo"))
    token = common.token_for(ws, client)
    base = common.api_base(ws)
    nonce = str(int(time.time() * 1000))
    body = {
        "v": 1,
        "session_id": sid,
        "client": common.WIRE_CLIENT[client],
        "source": source,
        "cwd_name": os.path.basename(cwd.rstrip("/"))[:80],
        "repo": g.get("repo"),
        "branch": g.get("branch"),
        "head": g.get("head"),
        "interactive": _interactive(),
        "machine_id": common.machine_id(),
        "cli": _version(),
    }
    key = spool.idem_key(client, sid or "-", "session_start", nonce)
    headers = net.api_headers(token, common.WIRE_CLIENT[client], session=sid, idem=key)
    resp, err = _post_session_start(base + "/api/v1/hooks/session-start", headers, body, SESSION_START_HTTP_TIMEOUT)

    data = None
    cached_at = None
    retry_later = False
    if resp is not None:
        status, _, raw = resp
        if status == 200:
            parsed = net.parse_json(raw)
            if isinstance(parsed, dict):
                data = inbox.validate(parsed)
                cache_data = dict(data)
                cache_data.pop("repo_hint", None)  # 与仓库相关，不进跨仓库的缓存
                spool.save_cache(slug, client, cache_data, cursor=parsed.get("cursor"))
            else:
                common.log("session-start bad json")
        else:
            common.log("session-start http %d" % status)
            retry_later = status >= 500 or status in spool.RETRYABLE
    else:
        common.log("session-start net: %s" % (err,))
        retry_later = True

    if data is None:
        cache = common.read_json(spool.cache_path(slug, client))
        if isinstance(cache, dict) and isinstance(cache.get("data"), dict):
            fetched = float(cache.get("fetched_at") or 0)
            if 0 <= time.time() - fetched <= CACHE_MAX_AGE:
                data = inbox.validate(cache["data"])
                data.pop("repo_hint", None)
                cached_at = time.strftime("%H:%M", time.localtime(fetched))
        if retry_later and sid:
            # 服务端暂时不可达：把会话登记放进 spool，下次 flush 补发
            item = _base_item("start", key, sid, client)
            item.update({k: v for k, v in body.items() if k not in ("v", "session_id", "client")})
            spool.write(
                {"key": key, "kind": "heartbeat", "created": time.time(), "attempts": 0, "next_try": 0,
                 "cred": cred, "ws": slug, "client": client, "item": item}
            )

    text = inbox.render_session_start(data, cached_at) if data is not None else None
    st = load_state(client, sid)
    st.update(
        {
            "ws": slug,
            "nonce": nonce,
            "cwd": cwd,
            "repo": g.get("repo"),
            "branch": g.get("branch"),
            # resume / compact 时保留上次 Stop 记下的 HEAD，免得漏报这之间的提交
            "head": st.get("head") or g.get("head"),
            "announced": sorted(inbox.need_me_keys(data)) if data is not None else st.get("announced", []),
            "last_out": time.time() if text else st.get("last_out", 0),
        }
    )
    st.setdefault("turns", 0)
    save_state(client, sid, st)
    emit(client, "session-start", text)


def _version():
    from teamflow import __version__

    return __version__


# ---------------------------------------------------------------- prompt


def prompt(payload: dict, client: str, cred: str) -> None:
    """只读本地缓存：永不联网，也永不拉起子进程（M0 复测：缓存过期时拉起 refresh 让 p95 到了约 70ms）。

    缓存由 Stop 每回合拉起的 `flush --refresh` 和 SessionStart 刷新，这里读到的最多旧一个回合。
    prompt 字段在 read_stdin 里就已丢弃。
    """
    from teamflow import inbox  # 不导入 spool：缓存路径在 common 里

    sid = valid_sid(payload.get("session_id"))
    cwd = _cwd(payload)
    creds = common.load_creds(cred)
    st = load_state(client, sid)
    slug, _ = _pick_ws(creds, st, cwd)
    cache = common.read_json(common.cache_path(slug, client))
    now = time.time()
    fetched = float(cache.get("fetched_at") or 0) if isinstance(cache, dict) else 0
    if not isinstance(cache, dict) or not isinstance(cache.get("data"), dict) or now - fetched > CACHE_MAX_AGE:
        return
    keys = inbox.need_me_keys(inbox.validate(cache["data"]))
    announced = set(st.get("announced") or [])
    new = [k for k in keys if k not in announced]
    if not new:
        return
    if now - float(st.get("last_out") or 0) < PROMPT_MIN_INTERVAL:
        return
    text = inbox.render_delta([keys[k] for k in new])
    st["ws"] = slug
    st["announced"] = sorted(keys)
    st["last_out"] = now
    save_state(client, sid, st)
    emit(client, "prompt", text)


# ---------------------------------------------------------------- stop


def stop(payload: dict, client: str, cred: str) -> None:
    from teamflow import gitinfo, spool

    sid = valid_sid(payload.get("session_id"))
    if not sid:
        common.log("stop: missing session_id")
        return
    cwd = _cwd(payload)
    creds = common.load_creds(cred)
    st = load_state(client, sid)
    slug, ws = _pick_ws(creds, st, cwd)
    if not st.get("nonce"):
        st["nonce"] = str(int(time.time() * 1000))

    # 回合标识：Codex 有 turn_id；Claude Code 有 prompt_id（v2.1.196+）；都没有就用本地计数
    turn = valid_sid(payload.get("turn_id")) or valid_sid(payload.get("prompt_id"))
    if not turn:
        st["turns"] = int(st.get("turns") or 0) + 1
        turn = "%s:%d" % (st["nonce"], st["turns"])

    own, own_total, other = [], 0, 0
    cur = gitinfo.head(cwd)
    last = st.get("head")
    if cur and last and cur != last:
        emails = {e.lower() for e in (ws.get("git_emails") or []) if isinstance(e, str)}
        me = gitinfo.user_email(cwd)
        if me:
            emails.add(me)
        res = gitinfo.new_commits(cwd, last, cur, emails) if emails else None
        if res:
            own, own_total, other = res
    if cur:
        st["head"] = cur
    if cwd != st.get("cwd"):
        st["cwd"] = cwd

    key = spool.idem_key(client, sid, "turn_end", turn)
    item = _base_item("turn_end", key, sid, client)
    item.update(
        {
            "turn": turn,
            "cwd_name": os.path.basename(cwd.rstrip("/"))[:80],
            "repo": st.get("repo"),
            "branch": st.get("branch"),
            "head": cur,
            "commits": own,
            "own_more": max(0, own_total - len(own)),
            "other_commits": other,
        }
    )
    spool.write(
        {"key": key, "kind": "commit" if own else "heartbeat", "created": time.time(), "attempts": 0,
         "next_try": 0, "cred": cred, "ws": slug, "client": client, "item": item}
    )
    st["ws"] = slug
    save_state(client, sid, st)
    _spawn_flush(client, cred, slug, refresh=True)


# ---------------------------------------------------------------- session-end


def session_end(payload: dict, client: str, cred: str) -> None:
    from teamflow import spool

    sid = valid_sid(payload.get("session_id"))
    if not sid:
        common.log("session-end: missing session_id")
        return
    reason = payload.get("reason") if payload.get("reason") in END_REASONS else "other"
    cwd = _cwd(payload)
    creds = common.load_creds(cred)
    st = load_state(client, sid)
    slug, _ = _pick_ws(creds, st, cwd)
    nonce = st.get("nonce") or str(int(time.time() // 60))
    key = spool.idem_key(client, sid, "end", nonce)
    item = _base_item("end", key, sid, client)
    item["reason"] = reason
    spool.write(
        {"key": key, "kind": "heartbeat", "created": time.time(), "attempts": 0, "next_try": 0,
         "cred": cred, "ws": slug, "client": client, "item": item}
    )
    st["ws"] = slug
    st["ended"] = time.time()
    save_state(client, sid, st)
    _spawn_flush(client, cred, slug, refresh=False)


# ---------------------------------------------------------------- tool（PostToolUse，只装在 Claude Code）


def tool(payload: dict, client: str, cred: str) -> None:
    """把这次 teamflow 工具调用对到会话（D40）。

    hook 输入（cc_hooks.md「PostToolUse input」）：session_id、tool_name、tool_use_id，另有 tool_input、
    tool_response、transcript_path 等。只用前三个和 cwd：tool_input / tool_response 在 read_stdin 里就丢掉了，
    不读、不记日志、不上传。tool_use_id 等于同一次 tools/call 的 _meta["claudecode/toolUseId"]
    （spike/results/S3.md 结论 3），服务端据此把成员级的调用补成会话级。

    只写 spool：不联网、不拉起进程、不写会话状态（并行的工具调用会并发触发 PostToolUse，写状态会互相覆盖）、
    不输出。幂等键 hash(client, session_id, tool_use_id)（spool.idem_key，事件位固定为 tool_map，和别的记录分开）：
    同一次调用重放只记一条。
    """
    name = teamflow_tool(payload.get("tool_name"))
    if name is None:
        if isinstance(payload.get("tool_name"), str) and payload["tool_name"].startswith(TOOL_PREFIX):
            common.log("tool: bad tool name")
        return  # 不是 teamflow 的工具：matcher 正常时到不了这里，什么都不做
    sid = valid_sid(payload.get("session_id"))
    tuid = valid_tool_use_id(payload.get("tool_use_id"))
    if not sid or not tuid:
        common.log("tool: missing or bad %s" % ("session_id" if not sid else "tool_use_id"))
        return
    from teamflow import spool

    creds = common.load_creds(cred)
    slug, _ = _pick_ws(creds, load_state(client, sid), _cwd(payload))
    key = spool.idem_key(client, sid, "tool_map", tuid)
    item = {"type": "tool_map", "key": key, "session_id": sid, "tool_use_id": tuid, "tool": name}
    spool.write(
        {"key": key, "kind": "heartbeat", "created": time.time(), "attempts": 0, "next_try": 0,
         "cred": cred, "ws": slug, "client": client, "item": item}
    )


HANDLERS = {"session-start": session_start, "prompt": prompt, "stop": stop, "session-end": session_end, "tool": tool}
CLAUDE_ONLY = ("tool",)


def run(event: str, client: str, cred: str) -> int:
    if event in CLAUDE_ONLY and client != "claude":
        return 0  # Codex 不装 PostToolUse：连 stdin 都不读
    try:
        payload = read_stdin()
        HANDLERS[event](payload, client, cred)
    except BaseException:  # noqa: BLE001 - fail-open：什么异常都吞掉
        common.log_exc("hook %s %s" % (event, client))
    return 0


def prune_sessions(now: float | None = None) -> None:
    now = now or time.time()
    d = os.path.join(common.state_dir(), "sessions")
    try:
        for name in os.listdir(d):
            p = os.path.join(d, name)
            try:
                if now - os.stat(p).st_mtime > SESSION_STATE_TTL:
                    os.unlink(p)
            except OSError:
                pass
    except OSError:
        pass
