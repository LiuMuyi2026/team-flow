#!/usr/bin/env bash
# Team Flow 本地试用：一条命令在这台电脑上把服务端、teamflow 命令行和隔离配置准备好。
#
# 只写仓库里的 .local/（已在 .gitignore），绝不改 ~/.claude、~/.claude.json、~/.codex。
# 可以重复执行：已经在跑的服务端会保留（内存里的看板数据也保留），要重启加 --restart。
# 例外：仓库代码更新过（服务端代码或网页构建产物变了），在跑的还是旧代码，会自动重启，免得新旧两套说法混在一起。
set -euo pipefail

# shellcheck source=scripts/_lib.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/_lib.sh"
tf_check_root

usage() {
  cat <<'EOF'
用法：scripts/local-up.sh [选项]

  --port N           服务端口，默认 8100（也可以设环境变量 TEAMFLOW_LOCAL_PORT）
  --me HANDLE        您的 handle，默认 me
  --mates A,B        模拟队友的 handle，逗号分隔，默认 bob,carol
  --index-url URL    PyPI 镜像地址；也认环境变量 UV_DEFAULT_INDEX、UV_INDEX_URL、PIP_INDEX_URL
  --hardening        给试用的 Claude Code 加上加固（deny 规则 + 沙箱屏蔽凭据）。默认不加，
                     免得改变您平时跑命令的方式；正式版默认是加的
  --no-codex-import  不从您平时的 Codex 配置里抄模型、服务商设置
  --skip-install     不重装 Python 包（离线时重启用）
  --restart          服务端已经在跑也重启（内存里的看板数据会清空）。
                     更新过代码时不用加，脚本发现在跑的是旧代码会自动重启
  -h, --help         显示这段说明

handle 要求：小写字母开头，2–16 位小写字母、数字或下划线。
EOF
}

need_val() {
  [ $# -ge 2 ] && [ -n "$2" ] || die "$1 后面要跟一个值（scripts/local-up.sh --help 查看用法）"
}

PORT="${TEAMFLOW_LOCAL_PORT:-8100}"
ME="me"
MATES="bob,carol"
EXPLICIT_HANDLES=0
INDEX_URL=""
HARDENING=0
CODEX_IMPORT=1
SKIP_INSTALL=0
RESTART=0

while [ $# -gt 0 ]; do
  case "$1" in
    --port) need_val "$@"; PORT="$2"; shift 2 ;;
    --port=*) PORT="${1#*=}"; shift ;;
    --me) need_val "$@"; ME="$2"; EXPLICIT_HANDLES=1; shift 2 ;;
    --me=*) ME="${1#*=}"; EXPLICIT_HANDLES=1; shift ;;
    --mates) need_val "$@"; MATES="$2"; EXPLICIT_HANDLES=1; shift 2 ;;
    --mates=*) MATES="${1#*=}"; EXPLICIT_HANDLES=1; shift ;;
    --index-url) need_val "$@"; INDEX_URL="$2"; shift 2 ;;
    --index-url=*) INDEX_URL="${1#*=}"; shift ;;
    --hardening) HARDENING=1; shift ;;
    --no-codex-import) CODEX_IMPORT=0; shift ;;
    --skip-install) SKIP_INSTALL=1; shift ;;
    --restart) RESTART=1; shift ;;
    -h | --help) usage; exit 0 ;;
    *) die "不认识的参数：$1（scripts/local-up.sh --help 查看用法）" ;;
  esac
done

# ---------------------------------------------------------------- 参数检查

case "$PORT" in
  '' | *[!0-9]*) die "端口要是数字：$PORT" ;;
esac
if [ "$PORT" -lt 1024 ] || [ "$PORT" -gt 65535 ]; then
  die "端口要在 1024–65535 之间：$PORT"
fi
MATES="$(printf '%s' "$MATES" | tr -d ' ')"
IFS=, read -r -a MATE_LIST <<<"$MATES"
[ "${#MATE_LIST[@]}" -ge 1 ] || die "至少要有一位模拟队友（--mates bob,carol）"
for h in "$ME" ${MATE_LIST[@]+"${MATE_LIST[@]}"}; do
  [[ "$h" =~ $TF_HANDLE_RE ]] || die "handle 不合格：$h（小写字母开头，2–16 位小写字母、数字或下划线）"
done
for h in ${MATE_LIST[@]+"${MATE_LIST[@]}"}; do
  [ "$h" != "$ME" ] || die "队友的 handle 不能和您的一样：$h"
done
if [ "$(printf '%s\n' "${MATE_LIST[@]}" | sort | uniq -d)" != "" ]; then
  die "队友的 handle 有重复：$MATES"
fi

BASE="http://127.0.0.1:$PORT"
LOGS="$TF_LOCAL/logs"
TOKENS="$TF_LOCAL/tokens.env"
CONF="$TF_LOCAL/local.env"
umask 077
mkdir -p "$TF_LOCAL" "$LOGS"
chmod 700 "$TF_LOCAL"

say "Team Flow 本地试用：准备环境（只写 $TF_LOCAL）"

# 在 agent 里运行（Claude Code 的 Bash 设 CLAUDECODE，Codex 的 shell 设 CODEX_THREAD_ID / CODEX_SANDBOX）：
# 登录链接就等于您本人的身份，不打印给 agent 看
IN_AGENT=0
if [ -n "${CLAUDECODE:-}${CODEX_THREAD_ID:-}${CODEX_SANDBOX:-}" ]; then
  IN_AGENT=1
  warn "看起来是在 agent 里运行的。服务端照常启动，但不打印登录链接；请在您自己的终端里运行 scripts/login-link.sh。"
fi

# ---------------------------------------------------------------- 端口与已有的服务端

OLD_PORT="$(tf_env_get "$CONF" TF_PORT)"
OLD_CODE="$(tf_env_get "$CONF" TF_CODE)"
RUNNING_PID="$(tf_server_pid || true)"
[ -n "$RUNNING_PID" ] || rm -f "$TF_PIDFILE"
# 端口上是我们自己的试用服务端就不算占用；换端口时先查新端口，免得停了旧的才发现新的用不了
if [ -z "$RUNNING_PID" ] || [ "$OLD_PORT" != "$PORT" ]; then
  if tf_port_listening "$PORT"; then
    {
      say "端口 $PORT 已经被别的程序占用了（不是这个仓库的试用服务端，脚本不会去结束它）。"
      owner="$(tf_port_owner "$PORT")"
      if [ -n "$owner" ]; then
        say "占用它的进程："
        printf '%s\n' "$owner" | sed 's/^/  /'
      fi
      say "换一个端口再试，例如：scripts/local-up.sh --port $((PORT + 1))"
    } >&2
    exit 1
  fi
fi

# ---------------------------------------------------------------- Python 环境

index_from_env() {
  # 镜像：--index-url 优先；uv 自己认 UV_DEFAULT_INDEX / UV_INDEX_URL，pip 自己认 PIP_INDEX_URL，缺的那边帮它补上
  if [ -n "$INDEX_URL" ]; then
    printf '%s\n' "$INDEX_URL"
  elif [ "$1" = uv ] && [ -z "${UV_DEFAULT_INDEX:-}${UV_INDEX_URL:-}" ] && [ -n "${PIP_INDEX_URL:-}" ]; then
    printf '%s\n' "$PIP_INDEX_URL"
  elif [ "$1" = pip ] && [ -z "${PIP_INDEX_URL:-}" ] && [ -n "${UV_DEFAULT_INDEX:-${UV_INDEX_URL:-}}" ]; then
    printf '%s\n' "${UV_DEFAULT_INDEX:-${UV_INDEX_URL:-}}"
  fi
}

python_help() {
  cat >&2 <<'EOF'
需要 Python 3.11 或更新的版本。任选一种：
  1. 装 uv（推荐，会自动下载 Python 3.12）：
       curl -LsSf https://astral.sh/uv/install.sh | sh
     访问 GitHub 慢的话，可以用 PyPI 镜像装：
       python3 -m pip install --user -i https://pypi.tuna.tsinghua.edu.cn/simple uv
     uv 下载 Python 也可以走镜像：设置 UV_PYTHON_INSTALL_MIRROR（见 docs/local-trial.md「常见问题」）
  2. 直接装 Python 3.12：macOS 用 brew install python@3.12；Ubuntu/Debian 用 sudo apt install python3.12 python3.12-venv
装好后重新运行 scripts/local-up.sh。
EOF
}

UV="$(command -v uv 2>/dev/null || true)"
make_venv() {
  local py=""
  py="$(tf_find_python || true)"
  rm -rf "$TF_LOCAL/venv"
  if [ -n "$UV" ]; then
    if [ -n "$py" ]; then
      say "  用 uv 和 $py（$("$py" -c 'import platform;print(platform.python_version())')）建 .local/venv"
      "$UV" venv --quiet --python "$py" "$TF_LOCAL/venv"
    else
      say "  没找到 3.11 以上的 Python，用 uv 下载 Python 3.12（可设 UV_PYTHON_INSTALL_MIRROR 走镜像）"
      "$UV" venv --quiet --python 3.12 "$TF_LOCAL/venv" || { python_help; exit 1; }
    fi
  else
    if [ -z "$py" ]; then
      found="$(command -v python3 2>/dev/null || true)"
      if [ -n "$found" ]; then
        say "找到的 python3 版本太旧：$("$found" -c 'import platform;print(platform.python_version())' 2>/dev/null || echo 未知)" >&2
      fi
      python_help
      exit 1
    fi
    say "  用 $py 建 .local/venv"
    "$py" -m venv "$TF_LOCAL/venv" || {
      say "建虚拟环境失败。Ubuntu/Debian 上通常要先装 venv 模块：sudo apt install python3-venv（或 python3.12-venv）" >&2
      exit 1
    }
  fi
}

install_pkgs() {
  local idx
  if [ -n "$UV" ]; then
    idx="$(index_from_env uv)"
    local args=()
    [ -z "$idx" ] || args=(--index-url "$idx")
    say "  安装 teamflow-server 和 teamflow（uv${idx:+，镜像 $idx}）"
    # cli 不用 editable：hook 冷启动少约 19ms（cli/README.md）；--reinstall-package 让仓库更新后重跑就生效
    "$UV" pip install --quiet --python "$TF_VPY" ${args[@]+"${args[@]}"} \
      -e "$TF_ROOT/server" "$TF_ROOT/cli" --reinstall-package teamflow || install_failed
  else
    idx="$(index_from_env pip)"
    local args=(--disable-pip-version-check --quiet)
    [ -z "$idx" ] || args+=(-i "$idx")
    say "  安装 teamflow-server 和 teamflow（pip${idx:+，镜像 $idx}）"
    "$TF_VPY" -m pip install "${args[@]}" -e "$TF_ROOT/server" "$TF_ROOT/cli" || install_failed
    "$TF_VPY" -m pip install "${args[@]}" --no-deps --force-reinstall "$TF_ROOT/cli" || install_failed
  fi
}

install_failed() {
  cat >&2 <<'EOF'
安装 Python 包失败（详情见上面）。常见原因是连不上 PyPI，换个镜像再试：
  PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple scripts/local-up.sh
  或 scripts/local-up.sh --index-url https://mirrors.aliyun.com/pypi/simple/
EOF
  exit 1
}

if [ -x "$TF_VPY" ] && tf_py_ok "$TF_VPY"; then
  if [ "$SKIP_INSTALL" = 1 ]; then
    say "  沿用 .local/venv，不重装（--skip-install）"
  else
    install_pkgs
  fi
else
  [ "$SKIP_INSTALL" = 0 ] || die ".local/venv 还没建好，不能用 --skip-install"
  make_venv
  install_pkgs
fi
[ -x "$TF_LOCAL/venv/bin/teamflow" ] || die "安装后没找到 $TF_LOCAL/venv/bin/teamflow，请看上面的报错"
TRIAL=("$TF_VPY" "$TF_ROOT/scripts/_trial.py")
CODE="$("${TRIAL[@]}" code-fingerprint)" || die "没能算出代码指纹（见上面的报错）"

# ---------------------------------------------------------------- 令牌（只在第一次或成员变了时生成）

# 先核对服务端认不认这些 handle：成员从哪来（种子数据还是令牌里的 handle）由服务端决定。
# 不认的话：您明确指定过 --me/--mates 就停下说明；用的是默认值就改用服务端已有的成员，下次重跑结果一样。
SERVER_MEMBERS="$("${TRIAL[@]}" probe-members "$ME" "$MATES")" || die "没能读出服务端的成员（见上面的报错）"
MISSING=""
for h in "$ME" ${MATE_LIST[@]+"${MATE_LIST[@]}"}; do
  case ",$SERVER_MEMBERS," in *",$h,"*) ;; *) MISSING="${MISSING:+$MISSING,}$h" ;; esac
done
if [ -n "$MISSING" ]; then
  if [ "$EXPLICIT_HANDLES" = 1 ]; then
    die "这版服务端的成员是 $(printf '%s' "$SERVER_MEMBERS" | sed 's/,/、/g')，没有 $(printf '%s' "$MISSING" | sed 's/,/、/g')。请从这些成员里选 --me 和 --mates。"
  fi
  IFS=, read -r -a SERVER_LIST <<<"$SERVER_MEMBERS"
  [ "${#SERVER_LIST[@]}" -ge 2 ] || die "服务端只有 ${#SERVER_LIST[@]} 个成员（$SERVER_MEMBERS），至少要两个人才能试协作"
  ME="${SERVER_LIST[0]}"
  MATE_LIST=("${SERVER_LIST[@]:1:2}")
  MATES="$(IFS=,; printf '%s' "${MATE_LIST[*]}")"
  warn "这版服务端的成员是固定的（$(printf '%s' "$SERVER_MEMBERS" | sed 's/,/、/g')），本次试用里您是 $ME，模拟队友是 $(printf '%s' "$MATES" | sed 's/,/、/g')。"
fi

WANT_MEMBERS="$ME,$MATES"
HAVE_MEMBERS="$(tf_env_get "$TOKENS" TF_MEMBERS)"
TOKENS_CHANGED=0
if [ ! -s "$TOKENS" ] || [ "$HAVE_MEMBERS" != "$WANT_MEMBERS" ]; then
  "${TRIAL[@]}" gen-env "$TOKENS" "$ME" "$MATES"
  TOKENS_CHANGED=1
  say "  生成令牌：$WANT_MEMBERS 各两枚（Claude Code、Codex），写进 .local/tokens.env（0600）"
fi
chmod 600 "$TOKENS"
ME_UP="$(tf_upper "$ME")"
TOK_ME_CLAUDE="$(tf_env_get "$TOKENS" "TF_TOKEN_${ME_UP}_CLAUDE")"
TOK_ME_CODEX="$(tf_env_get "$TOKENS" "TF_TOKEN_${ME_UP}_CODEX")"

# 非机密的试用参数（sim-teammate.py、try-*.sh 读它）
cat >"$CONF" <<EOF
# Team Flow 本地试用的参数（scripts/local-up.sh 生成，可以重跑覆盖）
TF_PORT=$PORT
TF_BASE=$BASE
TF_ME=$ME
TF_MATES=$MATES
EOF

# ---------------------------------------------------------------- 服务端

stop_ours() {
  local pid="$1"
  kill "$pid" 2>/dev/null || true
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.5
  done
  if tf_server_pid >/dev/null; then
    kill -9 "$pid" 2>/dev/null || true
  fi
  rm -f "$TF_PIDFILE"
}

START=1
if [ -n "$RUNNING_PID" ]; then
  if [ "$RESTART" = 0 ] && [ "$TOKENS_CHANGED" = 0 ] && [ "$OLD_PORT" = "$PORT" ] && [ "$OLD_CODE" = "$CODE" ] && tf_health "$BASE"; then
    START=0
    say "  服务端已经在 $BASE 运行（进程 $RUNNING_PID），保留它和内存里的数据；要重启加 --restart"
  else
    if [ "$RESTART" = 0 ] && [ "$OLD_CODE" != "$CODE" ]; then
      # 旧进程会把磁盘上的新网页送出去，接口和 agent 看到的文字却还是旧的
      say "  代码更新过，在跑的服务端（进程 $RUNNING_PID）还是旧代码：重启它让新代码生效（看板数据会清空，和 --restart 一样）"
    else
      say "  重启服务端（进程 $RUNNING_PID）"
    fi
    stop_ours "$RUNNING_PID"
    if tf_port_listening "$PORT"; then
      die "端口 $PORT 被别的程序占用了，脚本不会去结束它。换一个：scripts/local-up.sh --port $((PORT + 1))"
    fi
  fi
fi

if [ "$START" = 1 ]; then
  DEV_TOKENS="$("${TRIAL[@]}" dev-tokens "$TOKENS")"
  [ -f "$LOGS/server.log" ] && mv -f "$LOGS/server.log" "$LOGS/server.log.1"
  mkdir -p "$TF_LOCAL/state"
  say "  启动服务端：$BASE（本地开发模式，日志 .local/logs/server.log）"
  (
    cd "$TF_LOCAL"
    # 不带 DEV 端点的密钥：本地试用的人类动作只走网页登录（一次性登录码 + cookie），不开 /api/v1/dev/*
    unset TEAMFLOW_DEV_SECRET TEAMFLOW_ALLOWED_ORIGINS TEAMFLOW_FAULT_DELAY_MS
    export TEAMFLOW_DEV_TOKENS="$DEV_TOKENS"
    export TEAMFLOW_DEV_ENDPOINTS=1
    export TEAMFLOW_STATE="$TF_LOCAL/state"
    export TEAMFLOW_LOG="$LOGS/server.log.jsonl"
    export TEAMFLOW_PUBLIC_URL="$BASE"
    # 不记访问日志：登录链接的一次性码在查询串里
    exec nohup "$TF_VPY" -m uvicorn teamflow_server.app:app --host 127.0.0.1 --port "$PORT" --workers 1 --no-access-log
  ) >>"$LOGS/server.log" 2>&1 </dev/null &
  SERVER_PID=$!
  printf '%s\n' "$SERVER_PID" >"$TF_PIDFILE"
  if ! "${TRIAL[@]}" wait-health "$BASE" 30 "$SERVER_PID"; then
    {
      say "服务端没有起来。日志最后几行（.local/logs/server.log）："
      tail -n 20 "$LOGS/server.log" | grep -v '/dev/login?code=' | sed 's/^/  /' || true
      if grep -q -i 'address already in use' "$LOGS/server.log" 2>/dev/null; then
        say "端口 $PORT 被占用了，换一个：scripts/local-up.sh --port $((PORT + 1))"
      fi
    } >&2
    if kill -0 "$SERVER_PID" 2>/dev/null; then stop_ours "$SERVER_PID"; fi
    rm -f "$TF_PIDFILE"
    exit 1
  fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    rm -f "$TF_PIDFILE"
    die "端口 $PORT 上应答的不是刚启动的服务端（它已经退出了），请看 .local/logs/server.log"
  fi
  RUNNING_PID="$SERVER_PID"
fi
# 在跑的服务端是哪一版代码：下次重跑对不上就重启
printf 'TF_CODE=%s\n' "$CODE" >>"$CONF"

# ---------------------------------------------------------------- 隔离配置

if [ "$CODEX_IMPORT" = 1 ] && [ ! -f "$TF_LOCAL/codex/config.toml" ]; then
  SRC_CODEX="${CODEX_HOME:-$HOME/.codex}"
  case "$SRC_CODEX" in "$TF_LOCAL"/*) SRC_CODEX="$HOME/.codex" ;; esac
  if [ -f "$SRC_CODEX/config.toml" ]; then
    mkdir -p "$TF_LOCAL/codex"
    if copied="$("${TRIAL[@]}" import-codex-config "$SRC_CODEX/config.toml" "$TF_LOCAL/codex/config.toml")"; then
      say "  从 $SRC_CODEX/config.toml 只读地抄了 Codex 设置：${copied:-（没有可抄的项）}"
    fi
  fi
fi
mkdir -p "$TF_LOCAL/codex"
chmod 700 "$TF_LOCAL/codex"

# settings.json、mcp.json 全是我们生成的：每次重写，--hardening 开关来回切也不会留下旧的加固项。
# Codex 的 config.toml 不删：Codex 把 /hooks 的信任记录、登录方式写在里面。
rm -f "$TF_LOCAL/claude/settings.json" "$TF_LOCAL/claude/mcp.json" "$TF_LOCAL/credentials.json"
SETUP=(setup --isolated "$TF_LOCAL" --bin "$TF_LOCAL/venv/bin/teamflow" --api-url "$BASE" --workspace local)
[ "$HARDENING" = 1 ] || SETUP+=(--no-hardening)
if ! TEAMFLOW_PAT_CLAUDE="$TOK_ME_CLAUDE" TEAMFLOW_PAT_CODEX="$TOK_ME_CODEX" \
  "$TF_LOCAL/venv/bin/teamflow" "${SETUP[@]}" >"$LOGS/setup.log" 2>&1; then
  sed 's/^/  /' "$LOGS/setup.log" >&2
  die "teamflow setup --isolated 失败（见上面）"
fi
grep '^注意：' "$LOGS/setup.log" || true
chmod 600 "$TF_LOCAL/codex/config.toml" 2>/dev/null || true  # 可能抄进了服务商的设置
say "  写好隔离配置：.local/claude/（settings.json 5 个 hook、mcp.json）、.local/codex/（config.toml、hooks.json 4 个 hook）、.local/credentials.json"

# doctor 只看失败项（shell 输出、沙箱依赖之类是提示，不拦）
if ! "$TF_LOCAL/venv/bin/teamflow" doctor --isolated "$TF_LOCAL" >"$LOGS/doctor.log" 2>&1; then
  warn "teamflow doctor 有失败项（完整结果见 .local/logs/doctor.log）："
  grep -A1 '失败' "$LOGS/doctor.log" | sed 's/^/  /' >&2 || true
fi

# ---------------------------------------------------------------- 下一步

# 服务端启动时给每个成员打印一条登录链接；这里只取您本人的那条。您固定用 127.0.0.1、队友用 localhost：
# 两个地址的 cookie 互不影响，同一个浏览器里能同时当您和一位队友（登录码不绑地址，换地址照样能用）。
ME_LINK=""
if [ "$START" = 1 ] && [ "$IN_AGENT" = 0 ]; then
  while IFS="$(printf '\t')" read -r h url; do
    if [ "$h" = "$ME" ]; then ME_LINK="$(printf '%s' "$url" | sed 's#://localhost:#://127.0.0.1:#')"; fi
  done <<EOF
$("${TRIAL[@]}" login-links "$LOGS/server.log")
EOF
fi

cat <<EOF

本地试用已就绪。
  服务端  $BASE（进程 $RUNNING_PID）
  成员    $ME（您）、$(printf '%s' "$MATES" | sed 's/,/、/g')（模拟队友）
  配置    $TF_LOCAL（您的 ~/.claude、~/.codex 没有任何改动）

1. 在浏览器里以您本人的身份登录（接受、认领、确认、转发都在网页上点）：
EOF
if [ -n "$ME_LINK" ]; then
  say "     $ME_LINK"
  say "     链接 10 分钟内有效、只能用一次。过期或用过了：scripts/login-link.sh"
else
  say "     运行 scripts/login-link.sh 拿登录链接（在您自己的终端里运行）"
fi
say "   想在浏览器里亲手当一回队友：scripts/login-link.sh ${MATE_LIST[0]}（用 localhost 地址，和您的登录互不影响）"
cat <<EOF

2. 用隔离配置启动您的 agent（第一次打开项目目录时它们会问是否信任）：
     scripts/try-claude.sh ~/您的项目
     scripts/try-codex.sh ~/您的项目      第一次要登录 Codex，并在 /hooks 里信任 4 条 teamflow hook

3. 扮演队友，按 docs/local-trial.md 的场景 1–7 走一遍，例如：
     scripts/sim-teammate.py assign-me      ${MATE_LIST[0]} 的 agent 请您协作
     scripts/sim-teammate.py status         看看板

停止：scripts/local-down.sh    清空数据重来：scripts/local-reset.sh    卸载：scripts/local-reset.sh --all
EOF
if [ -n "${http_proxy:-}${https_proxy:-}${HTTP_PROXY:-}${HTTPS_PROXY:-}${all_proxy:-}${ALL_PROXY:-}" ]; then
  case ",${NO_PROXY:-${no_proxy:-}}," in
    *,127.0.0.1,*) ;;
    *) say "
提示：这个终端设了代理。try-claude.sh / try-codex.sh 会自动让 127.0.0.1 不走代理；
     您自己另开的命令请先 export NO_PROXY=127.0.0.1,localhost（见 docs/local-trial.md「常见问题」）。" ;;
  esac
fi
