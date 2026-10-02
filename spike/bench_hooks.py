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

TARGET_MS = {  # plan 11.2 S4 的通过标准
    "session-start": 1200,
    "prompt": 30,
    "stop": 100,
    "session-end": 100,
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
                                   "session-end": "SessionEnd"}[event]
        if event == "session-start":
            base["source"] = "startup"
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
    ap.add_argument("--events", default="session-start,prompt,stop,session-end")
    ap.add_argument("--bin", default=None, help="teamflow 可执行文件（默认 .venv/bin/teamflow 或 PATH 里的）")
    ap.add_argument("--shell", choices=("exec", "sh", "bash", "zsh", "login"), default="exec",
                    help="exec：Claude Code 的 exec form；sh/bash/zsh：Codex 用会话 shell -c；login：Codex 退回 $SHELL -lc")
    ap.add_argument("--cwd", default=REPO, help="hook 输入里的 cwd（影响 git 读取）")
    ap.add_argument("--no-spawn", action="store_true", help="不真正拉起分离 flush（只测 hook 本身）")
    ap.add_argument("--json", action="store_true", help="结果另外以 JSON 打印")
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
    env.update({"TEAMFLOW_STATE_DIR": os.path.join(tmp, "state"), "TEAMFLOW_FLUSH_BUDGET": "0", "HOME": tmp})
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

    rows = []
    # 基线：空解释器
    base = [timed([sys.executable, "-c", "pass"], b"")[0] for _ in range(a.n)]
    rows.append(("python -c pass", "-", base, None, None))

    for client in [c for c in a.clients.split(",") if c]:
        sid = "bench-%s-%d" % (client, os.getpid())
        # 预热：建立会话状态和缓存
        timed(argv_for(["hook", "session-start", "--client", client, "--cred", cred]),
              payload(client, "session-start", sid, a.cwd, 0))
        for event in [e for e in a.events.split(",") if e]:
            xs, nonempty = [], 0
            for i in range(a.n):
                s = sid if event != "session-end" else "%s-end-%d" % (sid, i)
                ms, p = timed(argv_for(["hook", event, "--client", client, "--cred", cred]),
                              payload(client, event, s, a.cwd, i + 1))
                xs.append(ms)
                nonempty += 1 if p.stdout.strip() else 0
            rows.append((event, client, xs, TARGET_MS.get(event), nonempty))
        hx = [timed(argv_for(["mcp-headers", "--client", client, "--cred", cred]), b"")[0] for _ in range(a.n)]
        rows.append(("mcp-headers", client, hx, None, None))

    mode = "api=%s" % api if a.api else "stub=%s" % a.stub
    print("teamflow hook 基准  %s  n=%d  执行方式=%s  spawn=%s" % (mode, a.n, a.shell, "off" if a.no_spawn else "on"))
    print("%-16s %-7s %8s %8s %8s %8s  %s" % ("命令", "客户端", "p50", "p95", "max", "目标", "有输出次数"))
    out = []
    for name, client, xs, target, nonempty in rows:
        p50, p95, mx = statistics.median(xs), pct(xs, 95), max(xs)
        flag = "" if target is None else ("通过" if p95 <= target else "超标")
        print("%-16s %-7s %8.1f %8.1f %8.1f %8s  %s %s" % (
            name, client, p50, p95, mx, target or "-", "" if nonempty is None else nonempty, flag))
        out.append({"cmd": name, "client": client, "p50": round(p50, 1), "p95": round(p95, 1), "max": round(mx, 1),
                    "target": target, "nonempty": nonempty})
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
