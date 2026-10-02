# shellcheck shell=bash
# 本地试用脚本共用的函数（被 local-up.sh 等 source，不单独运行）。
# 兼容 macOS 自带的 bash 3.2：不用关联数组、${var,,}、mapfile；空数组展开一律写成 ${a[@]+"${a[@]}"}。

TF_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
TF_LOCAL="$TF_ROOT/.local"
TF_VPY="$TF_LOCAL/venv/bin/python"
TF_PIDFILE="$TF_LOCAL/server.pid"
# shellcheck disable=SC2034  # 给 source 了本文件的脚本用
TF_HANDLE_RE='^[a-z][a-z0-9_]{1,15}$'

say() { printf '%s\n' "$*"; }
warn() { printf '注意：%s\n' "$*" >&2; }
die() {
  printf '%s\n' "$*" >&2
  exit 1
}

# 仓库根目录的样子不对就不干活（local-reset 要 rm -rf .local，路径算错了后果很重）
tf_check_root() {
  if [ ! -f "$TF_ROOT/AGENTS.md" ] || [ ! -d "$TF_ROOT/server" ] || [ ! -d "$TF_ROOT/cli" ]; then
    die "没找到 Team Flow 仓库根目录（算出来是 $TF_ROOT）。请从仓库里运行 scripts/ 下的脚本。"
  fi
}

# 本机有没有程序在监听这个端口。lsof 看得到就用它，看不到（别的用户的进程、没装 lsof）再试着连一下。
tf_port_listening() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    return 0
  fi
  if (exec 3<>"/dev/tcp/127.0.0.1/$port") >/dev/null 2>&1; then
    return 0
  fi
  return 1
}

# 占着端口的是谁（只用来提示，绝不结束它）
tf_port_owner() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | sed -n '2,4p'
  fi
}

# .local/server.pid 记的进程还活着、而且确实是我们起的服务端，才输出它的 pid
tf_server_pid() {
  local pid cmd
  [ -f "$TF_PIDFILE" ] || return 1
  pid="$(tr -cd '0-9' <"$TF_PIDFILE")"
  [ -n "$pid" ] || return 1
  kill -0 "$pid" 2>/dev/null || return 1
  cmd="$(ps -p "$pid" -o command= 2>/dev/null || true)"
  case "$cmd" in
    *teamflow_server.app:app*) printf '%s\n' "$pid" ;;
    *) return 1 ;;
  esac
}

tf_py_ok() {
  "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1
}

# 找一个 ≥3.11 的系统 Python（优先 3.12，和生产一致），输出它的路径；找不到返回 1
tf_find_python() {
  local c p
  for c in python3.12 python3.13 python3.11 python3; do
    p="$(command -v "$c" 2>/dev/null || true)"
    if [ -n "$p" ] && tf_py_ok "$p"; then
      printf '%s\n' "$p"
      return 0
    fi
  done
  return 1
}

# 读 KEY=VALUE 文件里的一个值（不 source，免得执行文件内容）
tf_env_get() {
  local file="$1" key="$2"
  [ -f "$file" ] || return 0
  sed -n "s/^${key}=//p" "$file" | tail -n 1
}

tf_upper() { printf '%s' "$1" | tr '[:lower:]' '[:upper:]'; }

# 让 127.0.0.1、localhost 不走代理（Claude Code、Codex、curl 都认 NO_PROXY / no_proxy）
tf_no_proxy() {
  local v="${NO_PROXY:-${no_proxy:-}}"
  case ",$v," in *,127.0.0.1,*) ;; *) v="${v:+$v,}127.0.0.1" ;; esac
  case ",$v," in *,localhost,*) ;; *) v="$v,localhost" ;; esac
  export NO_PROXY="$v" no_proxy="$v"
}

# 服务端在不在（不依赖 curl：curl 不加 --noproxy 时会把 127.0.0.1 也送进代理）
tf_health() {
  [ -x "$TF_VPY" ] || return 1
  "$TF_VPY" "$TF_ROOT/scripts/_trial.py" health "$1" >/dev/null 2>&1
}

tf_base() {
  local base
  base="$(tf_env_get "$TF_LOCAL/local.env" TF_BASE)"
  printf '%s\n' "${base:-http://127.0.0.1:8100}"
}
