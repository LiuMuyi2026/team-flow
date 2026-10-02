#!/usr/bin/env python3
"""M0 S4：teamflow hook 冷启动 / 端到端延迟基准。

对每个 hook（以及 mcp-headers、空解释器基线）按真实方式起子进程 N 次，输出 p50 / p95 / max（毫秒）。

用法示例（在仓库根目录）：
  .venv/bin/python spike/bench_hooks.py --stub normal          # 内置桩服务端，正常
  .venv/bin/python spike/bench_hooks.py --stub slow            # 桩服务端每个请求慢 3 秒
  .venv/bin/python spike/bench_hooks.py --stub down            # 服务端不可达（连接被拒）
  .venv/bin/python spike/bench_hooks.py --api http://127.0.0.1:8100 \
        --token-claude tf_pat_... --token-codex tf_pat_...     # 打真实服务端
  .venv/bin/python spike/bench_hooks.py --stub normal --shell sh      # 模拟 Codex：sh -c 执行命令串
  .venv/bin/python spike/bench_hooks.py --stub normal --shell login   # 模拟 Codex 退回 $SHELL -lc
  $V/bin/python spike/bench_hooks.py --stub normal --events prompt --bin $V/bin/teamflow   # 只测 UserPromptSubmit 四条路径
  $V/bin/python spike/bench_hooks.py --stub normal --events tool --clients claude --bin $V/bin/teamflow  # 只测 PostToolUse

目标（plan 6.4；D48 放宽后）：SessionStart ≤1200ms，UserPromptSubmit ≤50ms（原 30ms），Stop、SessionEnd ≤100ms，
PostToolUse（tool，D40，只装在 Claude Code）≤100ms。tool 是同步 hook（不设 async，见 cli/src/teamflow/setup_cmd.py
TOOL_MATCHER 上方的说明），每次 teamflow 工具调用后都要等它跑完，所以和 Stop 用同一条线。
tool 的输入按 cc_hooks.md「PostToolUse input」和 S3 实测到的键构造，tool_response 约 2KB（teamflow 工具结果的量级），
每次一个新的 tool_use_id，所以每次都真正写一条 spool。Codex 不装这个 hook，不测。

UserPromptSubmit 测四条路径（M0 评审 I3：S4 原来只测了第一条）：
  prompt             SessionStart 刚预热完：缓存新鲜、没有新条目、不输出
  prompt:stale       缓存已过 60 秒、没有新条目（旧版 CLI 在这里拉起 flush --refresh）
  prompt:emit        缓存新鲜、有新的「需要我」条目、距上次输出超过 10 分钟：输出增量并写会话状态
  prompt:stale+emit  两者都有
后三条每次运行前都重写缓存和会话状态（并删掉旧版的 .spawned 标记，让旧版每次都走拉起分支，便于前后对比）。
「拉起」列是这一行里 hook 拉起分离进程的次数（TEAMFLOW_SPAWN_LOG 计数）；「写入」列只有 tool 行有，是这一行写进 spool 的
tool_map 条数（还在 spool 里的加上已被分离的 flush 传给桩服务端的），应当等于 n。

状态目录、凭据都放在临时目录里，不碰真实 HOME。分离出来的 flush 带 TEAMFLOW_FLUSH_BUDGET=0，不会在后台重试。
"""

import argparse
import json
import math
import os
import shlex
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "cli", "tests"))

TARGET_MS = {  # plan 11.2 S4 的通过标准；prompt 按 D48 放宽到 50ms；tool（PostToolUse，D40）与 Stop 相同
    "session-start": 1200,
    "prompt": 50,
    "stop": 100,
    "session-end": 100,
    "tool": 100,
}
CLAUDE_ONLY = ("tool",)
# PostToolUse 的 tool_response：teamflow 工具结果的量级（inbox / get_item 约 1–3KB）
TOOL_RESPONSE = [{"type": "text", "text": json.dumps(
    {"id": "T-42", "st": "doing", "t": {"t": "整理接口错误码" * 4, "by": "alice", "trust": "self_agent", "client": "claude_code"},
     "ev": [{"e": i, "ty": "comment", "by": "bob", "x": "x" * 40} for i in range(20)], "next": "get_item"},
    ensure_ascii=False)}]


# prompt 后三条路径的缓存数据：BASE 里的条目都已通知过；NEW 多一条待接受
PP_BASE = {"v": 1, "me": "zhao", "doing": ["T-42"], "help_me": [{"id": "B-7", "by": "zhang"}]}
PP_NEW = dict(PP_BASE, to_accept=[{"id": "T-55", "by": "li", "bk": "agent", "client": "codex"}])
PROMPT_PATHS = {  # 名字 → (缓存年龄秒, 缓存数据, 应有输出)
    "stale": (120, PP_BASE, False),
    "emit": (5, PP_NEW, True),
    "stale+emit": (120, PP_NEW, True),
}


def pct(xs, p):
    xs = sorted(xs)
    k = max(0, math.ceil(p / 100 * len(xs)) - 1)
    return xs[k]


def payload(client, event, sid, cwd, turn):
    base = {"session_id": sid, "cwd": cwd}
    if client == "claude":
        base["transcript_path"] = "/tmp/x.jsonl"
        base["hook_event_name"] = {"session-start": "SessionStart", "prompt": "UserPromptSubmit", "stop": "Stop",
                                   "session-end": "SessionEnd", "tool": "PostToolUse"}[event]
        if event == "session-start":
            base["source"] = "startup"
        elif event == "tool":
            base.update({"permission_mode": "default", "prompt_id": "p-%d" % turn, "effort": {"level": "high"},
                         "tool_name": "mcp__teamflow__claim_task", "tool_input": {"id": "T-42"},
                         "tool_response": TOOL_RESPONSE, "tool_use_id": "toolu_bench%08dXyZ" % turn,
                         "duration_ms": 87, "mcp_server": {"name": "teamflow", "source": "user"}})
        elif event == "prompt":
            base.update({"prompt": "bench", "prompt_id": "p-%d" % turn})
        elif event == "stop":
            base.update({"stop_hook_active": False, "last_assistant_message": "x", "prompt_id": "p-%d" % turn})
        else:
            base["reason"] = "other"
    else:
        base["transcript_path"] = None
        if event == "session-start":
            base.update({"hook_event_name": "SessionStart", "model": "m", "permission_mode": "default", "source": "startup"})
        elif event == "prompt":
            base.update({"hook_event_name": "UserPromptSubmit", "turn_id": "t-%d" % turn, "model": "m",
                         "permission_mode": "default", "prompt": "bench"})
        elif event == "stop":
            base.update({"hook_event_name": "Stop", "turn_id": "t-%d" % turn, "model": "m", "permission_mode": "default",
                         "stop_hook_active": False, "last_assistant_message": "x"})
        else:
            base.update({"hook_event_name": "SessionEnd", "reason": "other"})
    return json.dumps(base).encode()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--api", help="服务端地址，如 http://127.0.0.1:8100")
    src.add_argument("--stub", choices=("normal", "slow", "down"), default=None, help="用内置桩服务端")
    ap.add_argument("--token-claude", default=os.environ.get("TEAMFLOW_PAT_CLAUDE", "tf_pat_bench_claude"))
    ap.add_argument("--token-codex", default=os.environ.get("TEAMFLOW_PAT_CODEX", "tf_pat_bench_codex"))
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--clients", default="claude,codex")
    ap.add_argument("--events", default="session-start,prompt,stop,session-end,tool",
                    help="tool 只对 claude 测（Codex 不装 PostToolUse）")
    ap.add_argument("--bin", default=None, help="teamflow 可执行文件（默认 .venv/bin/teamflow 或 PATH 里的）")
    ap.add_argument("--shell", choices=("exec", "sh", "bash", "zsh", "login"), default="exec",
                    help="exec：Claude Code 的 exec form；sh/bash/zsh：Codex 用会话 shell -c；login：Codex 退回 $SHELL -lc")
    ap.add_argument("--cwd", default=REPO, help="hook 输入里的 cwd（影响 git 读取）")
    ap.add_argument("--no-spawn", action="store_true", help="不真正拉起分离 flush（只测 hook 本身）")
    ap.add_argument("--json", action="store_true", help="结果另外以 JSON 打印")
    ap.add_argument("--prompt-paths", default="stale,emit,stale+emit",
                    help="events 含 prompt 时另外测的 UserPromptSubmit 路径，逗号分隔（%s）；空串不测" % ",".join(PROMPT_PATHS))
    ap.add_argument("--gap", type=float, default=0.3, help="prompt 后三条路径每次运行之间的间隔秒数（不计时；给上一次拉起的进程收尾）")
    ap.add_argument("--tmp", default=None, help="临时目录放在哪里（默认系统临时目录）")
    a = ap.parse_args()
    if not a.api and not a.stub:
        a.stub = "normal"

    tf = a.bin or (os.path.join(REPO, ".venv", "bin", "teamflow") if os.path.exists(os.path.join(REPO, ".venv", "bin", "teamflow")) else shutil.which("teamflow"))
    if not tf:
        sys.exit("找不到 teamflow，可用 --bin 指定")

    stub = None
    if a.stub:
        from tf_stub_server import Stub, closed_port_url

        if a.stub == "down":
            api = closed_port_url()
        else:
            stub = Stub().start()
            stub.delay = 3.0 if a.stub == "slow" else 0.0
            api = stub.url
    else:
        api = a.api

    tmp = tempfile.mkdtemp(prefix="tf-bench-", dir=a.tmp)
    cred = os.path.join(tmp, "credentials.json")
    with open(cred, "w") as f:
        json.dump({"workspaces": {"bench": {"api_url": api, "tokens": {"claude": a.token_claude, "codex": a.token_codex},
                                            "repo_patterns": []}}, "default": "bench"}, f)
    os.chmod(cred, 0o600)
    env = dict(os.environ)
    state = os.path.join(tmp, "state")
    spawn_log = os.path.join(tmp, "spawn.log")
    env.update({"TEAMFLOW_STATE_DIR": state, "TEAMFLOW_FLUSH_BUDGET": "0", "HOME": tmp, "TEAMFLOW_SPAWN_LOG": spawn_log})
    if a.no_spawn:
        env["TEAMFLOW_NO_SPAWN"] = "1"

    def argv_for(args):
        if a.shell == "exec":
            return [tf, *args]
        cmd = " ".join(shlex.quote(x) for x in [tf, *args])
        if a.shell == "sh":
            return ["/bin/sh", "-c", cmd]
        if a.shell in ("bash", "zsh"):
            exe = shutil.which(a.shell)
            if not exe:
                sys.exit("本机没有 %s" % a.shell)
            return [exe, "-c", cmd]
        shell = os.environ.get("SHELL") or "/bin/sh"
        run_env_home = os.environ.get("HOME")  # 登录 shell 用真实 profile 才有意义（只读）
        env["HOME"] = run_env_home or tmp
        return [shell, "-lc", cmd]

    def timed(argv, stdin):
        t = time.perf_counter()
        p = subprocess.run(argv, input=stdin, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env)
        return (time.perf_counter() - t) * 1000, p

    def spawns():
        try:
            with open(spawn_log) as f:
                return sum(1 for _ in f)
        except OSError:
            return 0

    def tool_maps(sid):
        """这个会话写进 spool 的 tool_map 条数：还在 spool（含 dead/）里的，加上已经被分离的 flush 传给桩服务端的。"""
        ids = set()
        d = os.path.join(state, "spool")
        for sub in (d, os.path.join(d, "dead")):
            try:
                names = os.listdir(sub)
            except OSError:
                continue
            for n in names:
                if not n.endswith(".json") or n.startswith("."):
                    continue
                try:
                    with open(os.path.join(sub, n), encoding="utf-8") as f:
                        it = (json.load(f) or {}).get("item") or {}
                except (OSError, ValueError):
                    continue
                if it.get("type") == "tool_map" and it.get("session_id") == sid:
                    ids.add(it.get("tool_use_id"))
        if stub:
            with stub.lock:
                reqs = list(stub.requests)
            for r in reqs:
                if r["path"] == "/api/v1/hooks/batch" and isinstance(r["body"], dict):
                    for it in r["body"].get("items") or []:
                        if it.get("type") == "tool_map" and it.get("session_id") == sid:
                            ids.add(it.get("tool_use_id"))
        return len(ids)

    def prep_prompt_path(client, sid, age, data):
        cache = os.path.join(state, "cache", "bench", client + ".json")
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        with open(cache, "w") as f:
            json.dump({"fetched_at": time.time() - age, "data": data}, f)
        try:
            os.unlink(cache + ".spawned")  # 旧版 CLI 的 60 秒节流标记
        except OSError:
            pass
        sess = os.path.join(state, "sessions", "%s-%s.json" % (client, sid))
        os.makedirs(os.path.dirname(sess), exist_ok=True)
        with open(sess, "w") as f:
            json.dump({"ws": "bench", "announced": ["help:B-7"], "last_out": 0, "turns": 0}, f)

    rows = []
    # 基线：空解释器
    base = [timed([sys.executable, "-c", "pass"], b"")[0] for _ in range(a.n)]
    rows.append(("python -c pass", "-", base, None, None, None, None))
    pp_names = [x for x in a.prompt_paths.split(",") if x]
    bad = [x for x in pp_names if x not in PROMPT_PATHS]
    if bad:
        sys.exit("不认识的 --prompt-paths：%s" % bad)

    for client in [c for c in a.clients.split(",") if c]:
        sid = "bench-%s-%d" % (client, os.getpid())
        # 预热：建立会话状态和缓存
        timed(argv_for(["hook", "session-start", "--client", client, "--cred", cred]),
              payload(client, "session-start", sid, a.cwd, 0))
        for event in [e for e in a.events.split(",") if e]:
            if event in CLAUDE_ONLY and client != "claude":
                continue
            xs, nonempty, sp0 = [], 0, spawns()
            for i in range(a.n):
                s = sid if event != "session-end" else "%s-end-%d" % (sid, i)
                ms, p = timed(argv_for(["hook", event, "--client", client, "--cred", cred]),
                              payload(client, event, s, a.cwd, i + 1))
                xs.append(ms)
                nonempty += 1 if p.stdout.strip() else 0
            written = tool_maps(sid) if event == "tool" else None
            rows.append((event, client, xs, TARGET_MS.get(event), nonempty, spawns() - sp0, written))
            if event != "prompt":
                continue
            for name in pp_names:
                age, data, _ = PROMPT_PATHS[name]
                psid = "%s-pp-%s" % (sid, name.replace("+", "-"))
                xs, nonempty, sp = [], 0, 0
                for i in range(a.n):
                    prep_prompt_path(client, psid, age, data)
                    sp0 = spawns()
                    ms, p = timed(argv_for(["hook", "prompt", "--client", client, "--cred", cred]),
                                  payload(client, "prompt", psid, a.cwd, i + 1))
                    xs.append(ms)
                    nonempty += 1 if p.stdout.strip() else 0
                    time.sleep(a.gap)
                    sp += spawns() - sp0
                rows.append(("prompt:" + name, client, xs, TARGET_MS["prompt"], nonempty, sp, None))
        hx = [timed(argv_for(["mcp-headers", "--client", client, "--cred", cred]), b"")[0] for _ in range(a.n)]
        rows.append(("mcp-headers", client, hx, None, None, None, None))

    mode = "api=%s" % api if a.api else "stub=%s" % a.stub
    print("teamflow hook 基准  %s  n=%d  执行方式=%s  spawn=%s" % (mode, a.n, a.shell, "off" if a.no_spawn else "on"))
    print("%-18s %-7s %8s %8s %8s %6s  %-6s %-4s %-4s %s" % ("命令", "客户端", "p50", "p95", "max", "目标", "有输出", "拉起",
                                                          "写入", ""))
    out = []
    for name, client, xs, target, nonempty, spawned, written in rows:
        p50, p95, mx = statistics.median(xs), pct(xs, 95), max(xs)
        flag = "" if target is None else ("通过" if p95 <= target else "超标")
        print("%-18s %-7s %8.1f %8.1f %8.1f %6s  %-6s %-4s %-4s %s" % (
            name, client, p50, p95, mx, target or "-", "" if nonempty is None else nonempty,
            "" if spawned is None else spawned, "" if written is None else written, flag))
        row = {"cmd": name, "client": client, "p50": round(p50, 1), "p95": round(p95, 1), "max": round(mx, 1),
               "target": target, "nonempty": nonempty, "spawned": spawned}
        if written is not None:
            row["written"] = written
        out.append(row)
    if a.json:
        print(json.dumps({"mode": mode, "n": a.n, "shell": a.shell, "rows": out}, ensure_ascii=False))
    # 等分离出去的 flush 收尾（最多 10 秒），再停桩服务端、删临时目录
    lock = os.path.join(tmp, "state", "spool", ".lock")
    deadline = time.time() + 10
    while os.path.exists(lock) and time.time() < deadline:
        time.sleep(0.2)
    time.sleep(0.5)
    if stub:
        stub.stop()
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
