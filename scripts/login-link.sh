#!/usr/bin/env bash
# 给本地试用的网页生成一次性登录链接（10 分钟内有效，只能用一次）。
# 请在您自己的终端里运行：登录码就是"手机上的您"在网页上的身份，服务端不给没有终端的进程（比如 agent）发码。
set -euo pipefail

# shellcheck source=scripts/_lib.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/_lib.sh"
tf_check_root

case "${1:-}" in
  -h | --help)
    cat <<'EOF'
用法：scripts/login-link.sh [handle] [--open] [--host 127.0.0.1|localhost] [--ttl 分钟]
  handle 默认是您本人（local-up.sh 的 --me）。扮演队友时写队友的 handle。
  --open 生成后直接用默认浏览器打开。
  您本人的链接用 127.0.0.1，队友的用 localhost：同一个浏览器里这两个地址的登录互不影响。
  同时当两位队友时，第二位请用无痕窗口或另一个浏览器。
EOF
    exit 0
    ;;
esac

[ -x "$TF_VPY" ] || die "还没有本地试用环境：请先运行 scripts/local-up.sh"
HANDLE="$(tf_env_get "$TF_LOCAL/local.env" TF_ME)"
if [ $# -gt 0 ] && [ "${1#-}" = "$1" ]; then
  HANDLE="$1"
  shift
fi
[ -n "$HANDLE" ] || die "不知道给谁生成：scripts/login-link.sh <handle>"
BASE="$(tf_base)"
tf_health "$BASE" || die "服务端没有在 $BASE 运行：先运行 scripts/local-up.sh"

# 您本人用 127.0.0.1、队友用 localhost（cookie 按地址分开，同一个浏览器里两个人互不影响）；--host 可以改
HOST_ARGS=()
case " $* " in
  *" --host "* | *" --host="*) ;;
  *)
    if [ "$HANDLE" = "$(tf_env_get "$TF_LOCAL/local.env" TF_ME)" ]; then
      HOST_ARGS=(--host 127.0.0.1)
    else
      HOST_ARGS=(--host localhost)
    fi
    ;;
esac
TEAMFLOW_STATE="$TF_LOCAL/state" exec "$TF_VPY" -m teamflow_server.devlogin --as "$HANDLE" ${HOST_ARGS[@]+"${HOST_ARGS[@]}"} "$@"
