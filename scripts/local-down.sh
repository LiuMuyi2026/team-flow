#!/usr/bin/env bash
# 停掉本地试用的服务端。只结束 .local/server.pid 里记的、确认是本仓库试用服务端的那个进程，别的一概不碰。
set -euo pipefail

# shellcheck source=scripts/_lib.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/_lib.sh"
tf_check_root

case "${1:-}" in
  -h | --help)
    say "用法：scripts/local-down.sh    停掉本地试用的服务端（内存里的看板数据随之清空，.local/ 里的配置和登录都保留）"
    exit 0
    ;;
  '') ;;
  *) die "不认识的参数：$1" ;;
esac

PID="$(tf_server_pid || true)"
if [ -z "$PID" ]; then
  if [ -f "$TF_PIDFILE" ]; then
    rm -f "$TF_PIDFILE"
    say "记录里的服务端进程已经不在了（或者不是试用服务端），清掉了 .local/server.pid。"
  else
    say "本地试用的服务端没有在运行。"
  fi
  exit 0
fi

kill "$PID" 2>/dev/null || true
for _ in 1 2 3 4 5 6 7 8 9 10; do
  kill -0 "$PID" 2>/dev/null || break
  sleep 0.5
done
if tf_server_pid >/dev/null; then
  # 还是同一个进程、还是试用服务端，才强制结束
  kill -9 "$PID" 2>/dev/null || true
fi
rm -f "$TF_PIDFILE"
say "已停止本地试用的服务端（进程 $PID）。内存里的看板数据随之清空；.local/ 里的配置、令牌和 Codex 登录都还在。"
say "再启动：scripts/local-up.sh"
