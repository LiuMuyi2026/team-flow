#!/usr/bin/env bash
# M0 S2（Codex 部分）：成员在自己电脑上跑的自检脚本。
#
# 检查四件事：
#   1. ~/.codex/hooks.json 里 4 条 teamflow hook 都在、每个事件只有一条（位置不限、可以和别人的 hook 同组，setup 原地更新）、命令串与 setup 生成的一致；
#   2. ~/.codex/config.toml 的 [hooks.state] 里这 4 条都有 trusted_hash（即在 /hooks 里信任过）；
#   3. $SHELL -c / -lc 的 stdout 为空（Codex 用会话 shell -c 跑 hook，没有会话 shell 时退回 $SHELL -lc）；
#   4. 在临时 git 目录里跑一次 `codex exec --json`：模型能复述 teamflow 注入的第一行；hook 登记的会话
#      就是 thread.started 里的 thread_id；Stop / SessionEnd 写的 spool 已被服务端收下。
#
# 用法（在 team-flow 仓库根目录）：
#   bash spike/codex_check.sh [选项] [-- <传给 codex exec 的额外参数>]
#
# 选项：
#   --cred <path>           凭据文件（默认 ~/.config/teamflow/credentials.json）
#   --codex-home <dir>      Codex 配置目录（默认 $CODEX_HOME 或 ~/.codex）
#   --server-log <path>     本机 M0 服务端的观测日志（如 spike/out/server.log.jsonl）；给了就按日志比对会话
#   --out <dir>             结果目录（默认 spike/out/codex_check-<时间>）
#   --timeout <秒>          codex exec 最长等待（默认 240）
#   --skip-exec             只做静态检查，不跑 codex exec
#   --save-baseline <file>  把 hooks 命令串与信任状态的指纹存下来（升级 CLI 前跑一次）
#   --baseline <file>       与之前存的指纹比对（升级 CLI 并重跑 teamflow setup 之后跑）
#   --starts <session_id>   只统计服务端日志里该会话的 session-start 次数（配合 /compact 手测，需 --server-log）
#
# 例子：
#   bash spike/codex_check.sh --server-log spike/out/server.log.jsonl
#   bash spike/codex_check.sh -- -c features.mcp_2026_07_28=true
#
# 脚本只读 Codex 与 teamflow 的配置，不改任何文件（结果只写到 --out 目录）；不打印 token。
# 退出码：0 全部通过；1 有未通过项；2 用法或环境错误。

set -u

CRED="${HOME}/.config/teamflow/credentials.json"
CODEX_DIR="${CODEX_HOME:-${HOME}/.codex}"
SERVER_LOG=""
OUT=""
EXEC_TIMEOUT=240
SKIP_EXEC=0
SAVE_BASELINE=""
BASELINE=""
STARTS=""
CODEX_ARGS=()

die() { echo "codex_check：$*" >&2; exit 2; }

while [ $# -gt 0 ]; do
  case "$1" in
    --cred) CRED="$2"; shift 2 ;;
    --codex-home) CODEX_DIR="$2"; shift 2 ;;
    --server-log) SERVER_LOG="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --timeout) EXEC_TIMEOUT="$2"; shift 2 ;;
    --skip-exec) SKIP_EXEC=1; shift ;;
    --save-baseline) SAVE_BASELINE="$2"; shift 2 ;;
    --baseline) BASELINE="$2"; shift 2 ;;
    --starts) STARTS="$2"; shift 2 ;;
    -h|--help) sed -n '2,32p' "$0"; exit 0 ;;
    --) shift; CODEX_ARGS=("$@"); break ;;
    *) die "不认识的参数 $1（用 --help 查看用法）" ;;
  esac
done

HERE="$(cd "$(dirname "$0")" && pwd)"
[ -n "$OUT" ] || OUT="$HERE/out/codex_check-$(date +%Y%m%d-%H%M%S)"

# ---------------------------------------------------------------- 找 teamflow 与它自带的 Python（≥3.11，有 tomllib）
TF="$(command -v teamflow || true)"
[ -n "$TF" ] || die "PATH 里没有 teamflow；先按 docs/plan.md 6.8 安装（uv tool install …）"
PY=""
shebang="$(head -1 "$TF" 2>/dev/null | sed -n 's/^#!//p' | awk '{print $1}')"
case "$shebang" in */python*) [ -x "$shebang" ] && PY="$shebang" ;; esac
if [ -z "$PY" ]; then
  real="$(python3 -c 'import os,sys;print(os.path.realpath(sys.argv[1]))' "$TF" 2>/dev/null || echo "$TF")"
  [ -x "$(dirname "$real")/python" ] && PY="$(dirname "$real")/python"
fi
[ -n "$PY" ] || PY="$(command -v python3 || true)"
"$PY" -c 'import teamflow, tomllib' 2>/dev/null || die "找不到能 import teamflow 的 Python（试过 $PY）"

CODEX="$(command -v codex || true)"
export TF PY CRED CODEX_DIR SERVER_LOG OUT SAVE_BASELINE BASELINE STARTS CODEX

# ---------------------------------------------------------------- 只统计 session-start 次数（compact 手测用）
if [ -n "$STARTS" ]; then
  [ -n "$SERVER_LOG" ] || die "--starts 需要 --server-log"
  "$PY" - <<'EOF'
import json, os
sid = os.environ["STARTS"]; n = 0
for line in open(os.environ["SERVER_LOG"], encoding="utf-8"):
    try:
        o = json.loads(line)
    except ValueError:
        continue
    if o.get("path") == "/api/v1/hooks/session-start" and o.get("sess") == sid:
        n += 1
        print(o.get("ts"), o.get("st"))
print("会话 %s 的 session-start 共 %d 次（/compact 之后再发一条消息，次数应当 +1）" % (sid, n))
EOF
  exit 0
fi

# ---------------------------------------------------------------- 1–3：静态检查
mkdir -p "$OUT" || die "建不了结果目录 $OUT"
"$PY" - <<'EOF' | tee "$OUT/static.txt"
import hashlib, json, os, subprocess, sys, tomllib
from teamflow import common, setup_cmd

out = os.environ["OUT"]; cred = os.path.abspath(os.path.expanduser(os.environ["CRED"]))
codex_dir = os.path.abspath(os.path.expanduser(os.environ["CODEX_DIR"]))
tf = os.environ["TF"]
rows = []
def rep(ok, name, detail=""):
    rows.append({"ok": ok, "name": name, "detail": detail})
    print("%s  %s%s" % ({True: "通过", False: "失败", None: "信息"}[ok], name, ("：" + detail) if detail else ""))

# 版本
codex = os.environ.get("CODEX") or ""
if codex:
    v = subprocess.run([codex, "--version"], capture_output=True, text=True).stdout.strip()
    rep(None, "codex 版本", v or "?")
else:
    rep(False, "codex", "PATH 里没有 codex")
import teamflow
rep(None, "teamflow", "%s（%s，Python %s）" % (teamflow.__version__, tf, sys.version.split()[0]))

# 凭据（只读 api_url，不打印 token）
creds = common.read_json(cred)
if isinstance(creds, dict) and isinstance(creds.get("workspaces"), dict):
    slug = creds.get("default") or next(iter(creds["workspaces"]), "")
    ws = creds["workspaces"].get(slug) or {}
    rep(True, "凭据文件", "%s；default=%s api_url=%s；codex token %s" % (
        cred, slug, ws.get("api_url"), "已填" if str((ws.get("tokens") or {}).get("codex", "")).startswith("tf_pat_") else "未填"))
else:
    rep(False, "凭据文件", "%s 读不了或格式不对" % cred)

# hooks.json
hj_path = os.path.join(codex_dir, "hooks.json")
hj = common.read_json(hj_path)
events = [("SessionStart", "session-start", "session_start", 5), ("UserPromptSubmit", "prompt", "user_prompt_submit", 2),
          ("Stop", "stop", "stop", 5), ("SessionEnd", "session-end", "session_end", 2)]
found = {}
if not isinstance(hj, dict):
    rep(False, "hooks.json", "%s 不存在或不是 JSON；先运行 teamflow setup" % hj_path)
else:
    extra = [k for k in hj if k not in ("description", "hooks")]
    rep(not extra, "hooks.json 顶层只有 description 和 hooks", ("多余的键 %s 会让 Codex 整个文件加载失败" % extra) if extra else hj_path)
    hooks = hj.get("hooks") or {}
    for ev, sub, label, tmo in events:
        arr = hooks.get(ev) or []
        idx = [(gi, hi, h) for gi, g in enumerate(arr) for hi, h in enumerate((g or {}).get("hooks") or [])
               if setup_cmd._is_teamflow_handler(h)]
        if not idx:
            rep(False, "%s 有 teamflow hook" % ev, "没找到；重跑 teamflow setup")
            continue
        gi, hi, h = idx[0]  # setup 保留并原地更新第一条
        found[ev] = (gi, hi, h, label)
        # 不要求在末尾（M0 评审 I7）：setup 已有的原地更新、不挪位置，因为 Codex 的信任键带组序号和 handler 序号；
        # 也允许和别人的 handler 同组（复审新问题 3：setup 不拆别人的组）。只要求整个事件里只有一条 teamflow handler
        groups = sorted({g for g, _, _ in idx})
        if len(idx) == 1:
            detail = "第 %d/%d 组（位置不限）" % (gi + 1, len(arr))
            if len((arr[gi] or {}).get("hooks") or []) > 1:
                detail += "，和别的 hook 同组，是第 %d 条" % (hi + 1)
        elif len(groups) > 1:
            detail = ("有 %d 组（第 %s 组），会重复执行；重跑 teamflow setup 会去掉多余的，去不掉的它会提示手动处理"
                      % (len(groups), "、".join(str(g + 1) for g in groups)))
        else:
            detail = "第 %d 组里有 %d 条，会重复执行；重跑 teamflow setup" % (gi + 1, len(idx))
        rep(len(idx) == 1, "%s 只有一组 teamflow hook" % ev, detail)
        want = setup_cmd.codex_hook_command(tf, sub, cred)
        same = h.get("command") == want
        rep(same if same else None, "%s 命令串与本机 teamflow setup 生成的一致" % ev,
            "" if same else "现有：%s；按当前 PATH 生成：%s（路径不同不一定错，以第 4 步实测为准）" % (h.get("command"), want))
        rep(h.get("timeout") == tmo, "%s timeout=%s" % (ev, tmo), "现有 %r" % h.get("timeout"))

# 信任状态：config.toml [hooks.state."<hooks.json 路径>:<事件>:<组>:<handler>"].trusted_hash
cfg_path = os.path.join(codex_dir, "config.toml")
state = {}
try:
    with open(cfg_path, "rb") as f:
        cfg = tomllib.load(f)
    state = ((cfg.get("hooks") or {}).get("state") or {})
    mcp = (cfg.get("mcp_servers") or {}).get("teamflow")
    rep(isinstance(mcp, dict) and str(mcp.get("url", "")).endswith("/mcp/"), "config.toml [mcp_servers.teamflow]",
        str((mcp or {}).get("url")))
except FileNotFoundError:
    rep(False, "config.toml", "%s 不存在" % cfg_path)
except tomllib.TOMLDecodeError as e:
    rep(False, "config.toml", "解析失败：%s" % e)
trust = {}
for ev, (gi, hi, h, label) in found.items():
    key = "%s:%s:%d:%d" % (hj_path, label, gi, hi)
    st = state.get(key)
    if st is None:  # 路径写法可能不同（符号链接等），按后缀再找一次
        cands = [k for k in state if k.endswith(":%s:%d:%d" % (label, gi, hi)) and "hooks.json" in k]
        st = state.get(cands[0]) if cands else None
        key = cands[0] if cands else key
    th = (st or {}).get("trusted_hash")
    en = (st or {}).get("enabled")
    trust[ev] = {"key": key, "trusted_hash": th, "enabled": en}
    ok = bool(th) and en is not False
    rep(ok, "%s 已信任" % ev, ("trusted_hash=%s" % th) if ok else
        ("没有 trusted_hash：在 Codex 里打开 /hooks 信任这条" if not th else "被禁用（enabled=false）"))
rep(None, "说明", "trusted_hash 是否等于当前命令串的哈希只能由 Codex 判断；第 4 步实测注入成功才算真的 Trusted")

# shell 输出
sh = os.environ.get("SHELL") or ""
try:
    import pwd
    login_shell = pwd.getpwuid(os.getuid()).pw_shell
except Exception:  # noqa: BLE001
    login_shell = "?"
rep(None, "shell", "$SHELL=%s，账户登录 shell=%s；Codex 用会话 shell 的 `-c`，没有会话 shell 时退回 `$SHELL -lc`" % (sh or "未设置", login_shell))
for flag in ("-c", "-lc"):
    if not sh:
        break
    p = subprocess.run([sh, flag, "true"], capture_output=True, stdin=subprocess.DEVNULL, timeout=20)
    o = p.stdout.decode("utf-8", "replace")
    rep(o == "", "%s %s true 的 stdout 为空" % (sh, flag),
        "" if o == "" else "有输出 %r：会混进 hook 的 stdout（Stop 会被 Codex 判失败，注入首行不再是哨兵）；把 profile 里的输出包进交互判断" % o[:60])

# 指纹（升级 CLI 前后比对）
fp = {ev: {"command": found[ev][2].get("command"), "timeout": found[ev][2].get("timeout"),
           "trusted_hash": trust.get(ev, {}).get("trusted_hash")} for ev in found}
fp_hash = hashlib.sha256(json.dumps(fp, sort_keys=True).encode()).hexdigest()[:16]
rep(None, "hooks 指纹", fp_hash)
if os.environ.get("SAVE_BASELINE"):
    with open(os.environ["SAVE_BASELINE"], "w", encoding="utf-8") as f:
        json.dump(fp, f, ensure_ascii=False, indent=1)
    rep(None, "已保存指纹", os.environ["SAVE_BASELINE"])
if os.environ.get("BASELINE"):
    with open(os.environ["BASELINE"], encoding="utf-8") as f:
        base = json.load(f)
    for ev in base:
        same_cmd = base[ev].get("command") == fp.get(ev, {}).get("command") and base[ev].get("timeout") == fp.get(ev, {}).get("timeout")
        rep(same_cmd, "升级后 %s 命令串与 timeout 未变" % ev, "" if same_cmd else "变了：Codex 会把它标成 Modified，需要重新信任")
        same_tr = base[ev].get("trusted_hash") == fp.get(ev, {}).get("trusted_hash")
        rep(same_tr, "升级后 %s 的 trusted_hash 未变" % ev)

with open(os.path.join(out, "static.json"), "w", encoding="utf-8") as f:
    json.dump({"rows": rows, "fingerprint": fp, "trust": trust}, f, ensure_ascii=False, indent=1)
EOF

if [ "$SKIP_EXEC" = 1 ]; then
  echo "（--skip-exec：跳过 codex exec）"
else
  # ---------------------------------------------------------------- 4：codex exec 实测
  [ -n "$CODEX" ] || die "PATH 里没有 codex"
  WORK="$(mktemp -d "${TMPDIR:-/tmp}/tf-codex-check.XXXXXX")"
  git -C "$WORK" init -q 2>/dev/null
  PROMPT='这是 teamflow 的安装自检。请把你在本次会话开始时收到的、以「【teamflow」开头的那段上下文的第一行原样输出，只输出那一行；如果没有收到这样的上下文，就只输出 NONE。不要调用任何工具，不要运行任何命令。'
  date +%s > "$OUT/exec_started_at"
  echo "运行：codex exec --skip-git-repo-check --json ${CODEX_ARGS[*]+${CODEX_ARGS[*]}} <自检提示>（目录 $WORK，最多 ${EXEC_TIMEOUT}s）"
  ( cd "$WORK" && exec "$CODEX" exec --skip-git-repo-check --json ${CODEX_ARGS[@]+"${CODEX_ARGS[@]}"} "$PROMPT" \
      >"$OUT/events.jsonl" 2>"$OUT/codex_stderr.txt" </dev/null ) &
  pid=$!; t=0
  while kill -0 "$pid" 2>/dev/null; do
    sleep 1; t=$((t + 1))
    if [ "$t" -ge "$EXEC_TIMEOUT" ]; then kill "$pid" 2>/dev/null; echo "codex exec 超时，已停止" >>"$OUT/codex_stderr.txt"; break; fi
  done
  wait "$pid"; echo "$?" > "$OUT/exec_rc"
  export WORK
  "$PY" - <<'EOF' | tee "$OUT/exec.txt"
import glob, json, os, time
from teamflow import common, spool

out = os.environ["OUT"]
rows = []
def rep(ok, name, detail=""):
    rows.append({"ok": ok, "name": name, "detail": detail})
    print("%s  %s%s" % ({True: "通过", False: "失败", None: "信息"}[ok], name, ("：" + detail) if detail else ""))

rc = open(os.path.join(out, "exec_rc")).read().strip()
started = float(open(os.path.join(out, "exec_started_at")).read().strip())
thread_id, answer, errors = None, None, []
for line in open(os.path.join(out, "events.jsonl"), encoding="utf-8", errors="replace"):
    try:
        o = json.loads(line)
    except ValueError:
        continue
    if o.get("type") == "thread.started":
        thread_id = o.get("thread_id")
    elif o.get("type") == "item.completed" and (o.get("item") or {}).get("type") == "agent_message":
        answer = (o["item"].get("text") or "").strip()
    elif o.get("type") in ("turn.failed", "error"):
        errors.append(json.dumps(o, ensure_ascii=False)[:200])
rep(rc == "0", "codex exec 退出码 0", rc)
for e in errors:
    rep(False, "codex exec 报错", e)
rep(bool(thread_id), "thread.started 里有 thread_id", thread_id or "没有")
first = (answer or "").splitlines()[0] if answer else ""
rep(first.startswith("【teamflow"), "模型复述的第一行以【teamflow 开头（SessionStart 注入生效）", repr(first[:80]))

# 等分离的 flush 发完（最多 20 秒）
sd = common.state_dir()
lock = os.path.join(sd, "spool", ".lock")
deadline = time.time() + 20
while time.time() < deadline and (os.path.exists(lock) or glob.glob(os.path.join(sd, "spool", "*.json"))):
    time.sleep(0.5)

# hook 登记的会话
mine = sorted((p for p in glob.glob(os.path.join(sd, "sessions", "codex-*.json")) if os.stat(p).st_mtime >= started - 1),
              key=lambda p: os.stat(p).st_mtime)
ids = [os.path.basename(p)[len("codex-"):-len(".json")] for p in mine]
rep(None, "本次运行期间 hook 登记的 Codex 会话", "、".join(ids) or "无")
hit = thread_id and thread_id in ids
rep(bool(hit), "hook 输入里的 session_id 等于 thread_id", "" if hit else "不一致或 hook 没运行：hooks 未信任、hooks 功能被关，或 session_id 与 thread_id 不同（把上一行的 ID 贴回来）")
st = common.read_json(os.path.join(sd, "sessions", "codex-%s.json" % thread_id)) if hit else None
sent_dir = os.path.join(sd, "spool", "sent")
new_sent = [n for n in (os.listdir(sent_dir) if os.path.isdir(sent_dir) else [])
            if os.stat(os.path.join(sent_dir, n)).st_mtime >= started - 1]
rep(len(new_sent) >= 1, "本次有上报被服务端收下（新增 spool/sent 标记，Stop 的 turn_end 与 SessionEnd 的 end 各一个）", "%d 个" % len(new_sent))
if isinstance(st, dict):
    ended = "ended" in st
    rep(None, "SessionEnd hook 运行过", "是" if ended else "否（codex exec 退出时是否触发 SessionEnd 以此为准，请贴回）")
    if ended:
        end_key = spool.idem_key("codex", thread_id, "end", st.get("nonce") or "")
        rep(os.path.exists(os.path.join(sent_dir, end_key)), "SessionEnd 的上报已被服务端收下（spool/sent 有标记）", end_key)
pend = spool.counts()
rep(pend["pending"] == 0 and pend["dead"] == 0, "spool 无积压、无 dead-letter", "pending=%d dead=%d" % (pend["pending"], pend["dead"]))
try:
    logtail = open(os.path.join(sd, "log"), encoding="utf-8", errors="replace").read().splitlines()[-20:]
except OSError:
    logtail = []
recent = [l for l in logtail if l[:19] >= time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(started))]
rep(not recent, "teamflow 错误日志在本次运行期间为空", " | ".join(recent)[:300])

# 服务端日志比对（本机 M0 服务端）
slog = os.environ.get("SERVER_LOG")
if slog and thread_id:
    from datetime import datetime
    starts, batches = 0, 0
    for line in open(slog, encoding="utf-8", errors="replace"):
        try:
            o = json.loads(line)
            if datetime.fromisoformat(o["ts"]).timestamp() < started - 1:
                continue  # 只看本次运行之后的记录
        except (ValueError, KeyError, TypeError):
            continue
        if o.get("path") == "/api/v1/hooks/session-start" and o.get("sess") == thread_id:
            starts += 1 if o.get("st") == 200 else 0
        if o.get("path") == "/api/v1/hooks/batch" and o.get("tf_client") == "codex" and o.get("st") == 200:
            batches += 1
    rep(starts >= 1, "服务端日志里有该 thread_id 的 session-start（200）", "%d 次" % starts)
    rep(batches >= 1, "服务端日志里有 Codex 的 hooks/batch（200）", "本次运行后共 %d 次（日志不记条目内容，逐条以 spool/sent 为准）" % batches)
elif not slog:
    rep(None, "服务端日志", "没给 --server-log，跳过日志比对（spool/sent 标记已能说明服务端收下）")

with open(os.path.join(out, "exec.json"), "w", encoding="utf-8") as f:
    json.dump({"thread_id": thread_id, "answer": answer, "session_ids": ids, "rows": rows}, f, ensure_ascii=False, indent=1)
EOF
  rm -rf "$WORK"
fi

# ---------------------------------------------------------------- 汇总
fails=$(cat "$OUT"/static.txt "$OUT"/exec.txt 2>/dev/null | grep -c '^失败')
echo
echo "结果目录：$OUT（把 static.txt、exec.txt 贴回 spike/results/S2.md）"
if [ "$fails" -eq 0 ]; then echo "结论：通过"; exit 0; else echo "结论：$fails 项失败"; exit 1; fi
