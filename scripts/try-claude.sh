#!/usr/bin/env bash
# 用本地试用的隔离配置启动 Claude Code：
#   claude --settings .local/claude/settings.json --mcp-config .local/claude/mcp.json --strict-mcp-config
# 不改 ~/.claude、~/.claude.json：teamflow 的 5 个 hook 和 MCP 只在这次启动里生效，关掉就没了。
# 您平时的登录、用户设置照常生效；--strict-mcp-config 让这次会话只连 teamflow 这一个 MCP server。
set -euo pipefail

# shellcheck source=scripts/_lib.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/_lib.sh"
tf_check_root

case "${1:-}" in
  -h | --help)
    cat <<'EOF'
用法：scripts/try-claude.sh [项目目录] [claude 的其他参数…]
  项目目录默认是当前目录。其余参数原样交给 claude，例如：
    scripts/try-claude.sh ~/work/demo
    scripts/try-claude.sh ~/work/demo -p "看看板上有什么需要我处理的" < /dev/null
EOF
    exit 0
    ;;
esac

PROJ="$PWD"
if [ $# -gt 0 ] && [ "${1#-}" = "$1" ]; then
  PROJ="$1"
  shift
fi
[ "${1:-}" != "--" ] || shift
[ -d "$PROJ" ] || die "项目目录不存在：$PROJ"

SETTINGS="$TF_LOCAL/claude/settings.json"
MCP="$TF_LOCAL/claude/mcp.json"
[ -f "$SETTINGS" ] && [ -f "$MCP" ] || die "还没有隔离配置：请先运行 scripts/local-up.sh"
command -v claude >/dev/null 2>&1 || die "没找到 claude 命令。请先安装 Claude Code（https://docs.anthropic.com/claude-code）并登录一次。"

BASE="$(tf_base)"
if ! tf_health "$BASE"; then
  warn "服务端没有在 $BASE 运行，teamflow 的工具会连不上（hook 不受影响，照常 fail-open）。先运行 scripts/local-up.sh"
fi

tf_no_proxy
cd "$PROJ"
exec claude --settings "$SETTINGS" --mcp-config "$MCP" --strict-mcp-config "$@"
