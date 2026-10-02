#!/usr/bin/env bash
# 清空本地试用的数据重来，或者整个卸载。只删仓库里的 .local/，不碰 ~/.claude、~/.claude.json、~/.codex
# 和仓库里的其他文件。
set -euo pipefail

# shellcheck source=scripts/_lib.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/_lib.sh"
tf_check_root

usage() {
  cat <<EOF
用法：
  scripts/local-reset.sh [local-up.sh 的参数]
      停服务，删掉 .local/ 里的试用数据（令牌、凭据、登录码、hook 的 spool 和缓存、日志、模拟队友的登录），
      然后重新运行 local-up.sh。保留 .local/venv（省得重装）和 .local/claude、.local/codex
      （Codex 的登录和 /hooks 信任记录还能接着用）。
  scripts/local-reset.sh --all [-y]
      卸载：停服务，删掉整个 $TF_LOCAL。-y 不再确认。

两种都只删 $TF_LOCAL 里的东西。
EOF
}

ALL=0
YES=0
PASS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --all) ALL=1; shift ;;
    -y | --yes) YES=1; shift ;;
    -h | --help) usage; exit 0 ;;
    *) PASS+=("$1"); shift ;;
  esac
done

# 删之前再核一遍路径：必须是 <仓库根>/.local，不是符号链接
case "$TF_LOCAL" in
  "$TF_ROOT/.local") ;;
  *) die "算出来的试用目录不对：$TF_LOCAL" ;;
esac
if [ -L "$TF_LOCAL" ]; then
  die "$TF_LOCAL 是一个符号链接，为了安全不删它，请手动处理"
fi

"$TF_ROOT/scripts/local-down.sh"

if [ "$ALL" = 1 ]; then
  [ "${#PASS[@]}" -eq 0 ] || die "--all 不接受其他参数：${PASS[*]}"
  if [ ! -e "$TF_LOCAL" ]; then
    say "$TF_LOCAL 不存在，没有要删的。"
    exit 0
  fi
  if [ "$YES" = 0 ]; then
    if [ ! -t 0 ]; then
      die "要删除整个 $TF_LOCAL，请加 -y 确认（或在终端里运行）"
    fi
    printf '将删除整个 %s（虚拟环境、配置、令牌、Codex 在试用里的登录和会话记录）。\n' "$TF_LOCAL"
    printf '不会碰 ~/.claude、~/.claude.json、~/.codex。确认删除？[y/N] '
    read -r ans
    case "$ans" in y | Y | yes | YES) ;; *) say "没有删除。"; exit 0 ;; esac
  fi
  # .local/codex/auth.json 如果是指向 ~/.codex/auth.json 的符号链接，rm 只删链接本身，不删您原来的登录文件
  rm -rf "$TF_LOCAL"
  say "已删除 $TF_LOCAL。Team Flow 本地试用已卸载；您的 ~/.claude、~/.codex 一直没有被改过。"
  exit 0
fi

for p in tokens.env local.env credentials.json state cli-state logs sim server.pid; do
  rm -rf "${TF_LOCAL:?}/$p"
done
say "已清空 .local/ 里的试用数据（保留 venv、claude/、codex/）。重新启动："
exec "$TF_ROOT/scripts/local-up.sh" ${PASS[@]+"${PASS[@]}"}
