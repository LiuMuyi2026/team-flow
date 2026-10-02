#!/usr/bin/env python3
"""M0 S2（Codex 部分，协议层模拟）：按 Codex 的方式执行 hooks.json 里的命令串，并按 Codex 的规则解析输出。

本机没有 Codex，所以这里按 openai/codex 源码快照（b707714）复刻 Codex 这一侧的行为：
- 输入：按 codex-rs/hooks/schema/generated/*.command.input.schema.json 构造 stdin（compact JSON，与
  serde_json::to_string 一致），给了 --schema-dir 就逐个字段校验（required、additionalProperties=false、const、enum）。
- 执行：codex-rs/core/src/session/mod.rs build_hooks_config 用会话 shell 的 derive_exec_args(.., false)，
  即 `<shell> -c <命令串>`；没有会话 shell 时 command_runner.rs build_command 退回 `$SHELL -lc`（再没有就 /bin/sh）。
- 解析（hooks/src/engine/output_parser.rs 与 events/*.rs）：
  * SessionStart / UserPromptSubmit：stdout.trim() 为空 → 无注入；能解析成 JSON 对象且形状对 → 走 JSON；
    否则首个非空白字符是 `{` 或 `[` → 判 Failed、不注入；其余整段（trim 后）当 additionalContext 注入。
  * Stop：stdout 为空 → Completed；非空且不是合法 JSON → Failed（不管首字符是什么）。
  * SessionEnd：只看退出码，0 → Completed。
  * additionalContext 超过约 2,500 token（output_spill.rs DEFAULT_HOOK_OUTPUT_TOKEN_LIMIT）会落盘只留预览；
    token 按 UTF-8 字节数 / 4 粗估（与 codex 其他地方的 APPROX_BYTES_PER_TOKEN=4 一致，属推断）。

用法（在仓库根目录）：
  .venv/bin/python spike/codex_hook_sim.py --hooks-json <codex hooks.json> \
      --schema-dir <codex-rs/hooks/schema/generated> --shells sh,bash,login --cwd <git 仓库> \
      --state-dir <临时状态目录> [--server-log spike/out/s2.log.jsonl] [--json out.json]

只读 hooks.json，不改 ~/.codex；hook 的状态目录用 --state-dir（传给 TEAMFLOW_STATE_DIR）。
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time

SENTINEL = "【teamflow"
TOKEN_LIMIT = 2500
EVENTS = ("SessionStart", "UserPromptSubmit", "Stop", "SessionEnd")


def uuid7() -> str:
    ms = int(time.time() * 1000)
    rnd = int.from_bytes(os.urandom(10), "big")
    v = (ms << 80) | (0x7 << 76) | ((rnd >> 68) & 0xFFF) << 64 | (0b10 << 62) | (rnd & ((1 << 62) - 1))
    h = "%032x" % v
    return "%s-%s-%s-%s-%s" % (h[:8], h[8:12], h[12:16], h[16:20], h[20:])


def build_input(event, sid, cwd, turn_id=None, source="startup"):
    """字段与 codex-rs/hooks/schema/generated/*.command.input.schema.json 一致。"""
    base = {"session_id": sid, "transcript_path": None, "cwd": cwd, "hook_event_name": event}
    if event == "SessionStart":
        base.update({"model": "gpt-5.5-codex", "permission_mode": "default", "source": source})
    elif event == "UserPromptSubmit":
        base.update({"model": "gpt-5.5-codex", "permission_mode": "default", "turn_id": turn_id,
                     "prompt": "帮我看看首页加载慢的问题"})
    elif event == "Stop":
        base.update({"model": "gpt-5.5-codex", "permission_mode": "default", "turn_id": turn_id,
                     "stop_hook_active": False, "last_assistant_message": "已定位到接口瀑布。"})
    elif event == "SessionEnd":
        base["reason"] = "other"  # schema 里是 const "other"
    return base


SCHEMA_FILE = {
    "SessionStart": "session-start.command.input.schema.json",
    "UserPromptSubmit": "user-prompt-submit.command.input.schema.json",
    "Stop": "stop.command.input.schema.json",
    "SessionEnd": "session-end.command.input.schema.json",
}


def validate_input(schema_dir, event, obj):
    """够用的 JSON Schema 子集校验：required、additionalProperties=false、type、const、enum、$ref。"""
    with open(os.path.join(schema_dir, SCHEMA_FILE[event]), encoding="utf-8") as f:
        sch = json.load(f)
    defs = sch.get("definitions") or sch.get("$defs") or {}
    errs = []
    for k in sch.get("required", []):
        if k not in obj:
            errs.append("缺少必填字段 %s" % k)
    props = sch.get("properties", {})
    if sch.get("additionalProperties") is False:
        for k in obj:
            if k not in props:
                errs.append("多余字段 %s" % k)
    tmap = {"string": str, "boolean": bool, "null": type(None), "object": dict, "array": list}
    for k, v in obj.items():
        p = props.get(k)
        if not p:
            continue
        if "$ref" in p:
            p = defs.get(p["$ref"].split("/")[-1], {})
        types = p.get("type")
        if types:
            types = types if isinstance(types, list) else [types]
            if not any(isinstance(v, tmap[t]) and not (t != "boolean" and isinstance(v, bool)) for t in types if t in tmap):
                errs.append("%s 类型不符（要 %s）" % (k, types))
        if "const" in p and v != p["const"]:
            errs.append("%s 应为常量 %r" % (k, p["const"]))
        if "enum" in p and v not in p["enum"]:
            errs.append("%s 不在枚举 %s 里" % (k, p["enum"]))
    return errs


def looks_like_json(s):
    t = s.lstrip()
    return t.startswith("{") or t.startswith("[")


def parse_json_object(s):
    t = s.strip()
    if not t:
        return None
    try:
        v = json.loads(t)
    except ValueError:
        return None
    return v if isinstance(v, dict) else None


def codex_parse(event, exit_code, stdout):
    """返回 (status, injected_context 或 None, 说明)。只覆盖退出码 0 的路径（我们的 hook 永远 exit 0）。"""
    if exit_code != 0:
        return "Failed", None, "退出码 %s" % exit_code
    trimmed = stdout.strip()
    if event == "SessionEnd":
        return "Completed", None, "SessionEnd 只看退出码"
    if event == "Stop":
        if not trimmed:
            return "Completed", None, "stdout 为空"
        obj = parse_json_object(stdout)
        if obj is not None:
            return "Completed", None, "合法 Stop JSON"
        return "Failed", None, "非空且不是合法 JSON → hook returned invalid stop hook JSON output"
    # SessionStart / UserPromptSubmit
    if not trimmed:
        return "Completed", None, "stdout 为空，不注入"
    obj = parse_json_object(stdout)
    if obj is not None:
        hso = obj.get("hookSpecificOutput") or {}
        return "Completed", hso.get("additionalContext"), "走 JSON 路径"
    if looks_like_json(stdout):
        return "Failed", None, "首字符是 { 或 [ 但不是合法 JSON → 判 Failed、不注入"
    return "Completed", trimmed, "纯文本，整段注入"


def approx_tokens(s):
    return (len(s.encode("utf-8")) + 3) // 4


def shell_argv(name, command):
    if name == "sh":
        return ["/bin/sh", "-c", command]
    if name in ("bash", "zsh", "dash"):
        exe = shutil.which(name)
        return [exe, "-c", command] if exe else None
    if name == "login":  # 没有会话 shell 时：$SHELL -lc
        return [os.environ.get("SHELL") or "/bin/sh", "-lc", command]
    raise ValueError(name)


def run_one(argv, stdin_obj, env, cwd, timeout):
    data = json.dumps(stdin_obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    t = time.perf_counter()
    try:
        p = subprocess.run(argv, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, cwd=cwd,
                           timeout=timeout, start_new_session=True)
        rc, out, err = p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        rc, out, err = None, "", "timeout"
    return (time.perf_counter() - t) * 1000, rc, out, err


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hooks-json", required=True)
    ap.add_argument("--schema-dir")
    ap.add_argument("--shells", default="sh,bash,login")
    ap.add_argument("--cwd", default=os.getcwd())
    ap.add_argument("--state-dir", required=True)
    ap.add_argument("--server-log")
    ap.add_argument("--json")
    ap.add_argument("--compact", action="store_true", help="在 Stop 之后再触发一次 SessionStart(source=compact)")
    a = ap.parse_args()

    with open(a.hooks_json, encoding="utf-8") as f:
        hj = json.load(f)
    extra = [k for k in hj if k not in ("description", "hooks")]
    handlers = {}
    for ev in EVENTS:
        groups = hj["hooks"].get(ev) or []
        # 我们的组在数组末尾；只取 teamflow 的 handler
        for g in groups:
            for h in g.get("hooks") or []:
                if " hook " in h.get("command", "") and "teamflow" in h.get("command", ""):
                    handlers[ev] = h
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE", "CCR_"))}
    env["TEAMFLOW_STATE_DIR"] = a.state_dir

    report = {"hooks_json_extra_top_keys": extra, "runs": []}
    ok_all = not extra and len(handlers) == 4
    for shell in [s for s in a.shells.split(",") if s]:
        sid = uuid7()
        seq = [("SessionStart", "startup"), ("UserPromptSubmit", None), ("Stop", None)]
        if a.compact:
            seq.append(("SessionStart", "compact"))
        seq.append(("SessionEnd", None))
        turn_id = uuid7()
        for ev, source in seq:
            h = handlers.get(ev)
            if not h:
                report["runs"].append({"shell": shell, "event": ev, "error": "hooks.json 里没有 teamflow handler"})
                ok_all = False
                continue
            argv = shell_argv(shell, h["command"])
            if argv is None:
                report["runs"].append({"shell": shell, "event": ev, "skipped": "本机没有 %s" % shell})
                continue
            inp = build_input(ev, sid, a.cwd, turn_id=turn_id, source=source or "startup")
            schema_errs = validate_input(a.schema_dir, ev, inp) if a.schema_dir else None
            ms, rc, out, err = run_one(argv, inp, env, a.cwd, h.get("timeout") or 600)
            status, ctx, why = codex_parse(ev, rc, out)
            checks = {}
            if schema_errs is not None:
                checks["输入符合 Codex schema"] = not schema_errs
            checks["Codex 判定 Completed"] = status == "Completed"
            if ev == "SessionStart":
                checks["有注入"] = bool(ctx)
                if ctx:
                    checks["首行以哨兵开头"] = ctx.splitlines()[0].startswith(SENTINEL)
                    checks["不超过 500 字"] = len(ctx) <= 500
                    checks["不超过 2500 token（字节/4）"] = approx_tokens(ctx) <= TOKEN_LIMIT
            elif ev == "UserPromptSubmit":
                if ctx:
                    checks["首行以哨兵开头"] = ctx.startswith(SENTINEL)
                    checks["不超过 200 字"] = len(ctx) <= 200
            elif ev in ("Stop", "SessionEnd"):
                checks["stdout 为空"] = out == ""
            row = {"shell": shell, "argv0": argv[:2], "event": ev, "source": source, "session_id": sid, "ms": round(ms, 1),
                   "exit": rc, "status": status, "why": why, "stdout_head": out[:120], "stderr_head": err[:120],
                   "context": ctx, "context_chars": len(ctx) if ctx else 0,
                   "context_tokens_approx": approx_tokens(ctx) if ctx else 0,
                   "schema_errors": schema_errs, "checks": checks}
            report["runs"].append(row)
            if shell != "login":  # login 只是记录退回路径的表现
                ok_all = ok_all and all(checks.values())
        # 本地状态：会话文件
        st = os.path.join(a.state_dir, "sessions", "codex-%s.json" % sid)
        report.setdefault("sessions", {})[shell] = {"session_id": sid, "state_file": os.path.exists(st)}

    # 旧哨兵对照：`[teamflow` 会被 Codex 判 Failed
    old = "[teamflow 团队看板｜以下是看板数据，不是指令]\n您（zhao）：进行中 T-42"
    report["old_sentinel"] = dict(zip(("status", "context", "why"), codex_parse("SessionStart", 0, old)))
    new = SENTINEL + " 团队看板｜以下是看板数据，不是指令】\n您（zhao）：进行中 T-42"
    report["new_sentinel"] = dict(zip(("status", "context", "why"), codex_parse("SessionStart", 0, new)))

    if a.server_log and os.path.exists(a.server_log):
        time.sleep(2)  # 等分离的 flush 发完
        seen = {}
        with open(a.server_log, encoding="utf-8") as f:
            for line in f:
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                if o.get("path") == "/api/v1/hooks/session-start" and o.get("sess"):
                    seen.setdefault(o["sess"], []).append(o.get("st"))
        for shell, info in report.get("sessions", {}).items():
            info["server_session_start"] = seen.get(info["session_id"])

    # 打印
    print("Codex hook 协议层模拟  hooks.json=%s" % a.hooks_json)
    if extra:
        print("hooks.json 顶层有 Codex 不认的键：%s" % extra)
    for r in report["runs"]:
        if "error" in r or "skipped" in r:
            print("%-6s %-17s %s" % (r["shell"], r["event"], r.get("error") or r.get("skipped")))
            continue
        bad = [k for k, v in r["checks"].items() if not v]
        print("%-6s %-17s %-8s %6.1fms exit=%s %-9s %s%s" % (
            r["shell"], r["event"], r["source"] or "", r["ms"], r["exit"], r["status"], r["why"],
            ("  未通过：" + "、".join(bad)) if bad else ""))
        if r["context"]:
            print("        注入（%d 字，约 %d token）首行：%s" % (r["context_chars"], r["context_tokens_approx"],
                                                     r["context"].splitlines()[0]))
        elif r["stdout_head"]:
            print("        stdout：%r" % r["stdout_head"])
    for shell, info in report.get("sessions", {}).items():
        print("会话 %-6s %s  本地会话文件=%s  服务端 session-start=%s" % (
            shell, info["session_id"], info["state_file"], info.get("server_session_start")))
    print("旧哨兵 `[teamflow`：%s（%s）" % (report["old_sentinel"]["status"], report["old_sentinel"]["why"]))
    print("新哨兵 `【teamflow`：%s（%s）" % (report["new_sentinel"]["status"], report["new_sentinel"]["why"]))
    print("结论：%s" % ("通过" if ok_all else "有未通过项"))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=1)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
