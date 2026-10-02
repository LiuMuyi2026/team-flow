#!/usr/bin/env bash
# 用本地试用的隔离目录启动 Codex：CODEX_HOME=.local/codex codex
# Codex 的配置、hooks、信任记录、会话记录、登录都只在 .local/codex 里，不碰 ~/.codex。
#
# 登录（codex-rs 源码确认，见 docs/local-trial.md「Codex 的登录」）：
# - CODEX_HOME 换了目录，登录就看 <CODEX_HOME>/auth.json（缺省的 file 存储）或钥匙串里按 CODEX_HOME 路径
#   区分的条目，所以第一次要在试用目录里单独登录一次；
# - 也可以选择把 .local/codex/auth.json 做成指向 ~/.codex/auth.json 的符号链接复用登录，但有风险（见下）。
set -euo pipefail

# shellcheck source=scripts/_lib.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/_lib.sh"
tf_check_root

usage() {
  cat <<'EOF'
用法：scripts/try-codex.sh [--login | --link-login | --api-key] [项目目录] [codex 的其他参数…]

  第一次运行时要在试用目录里有一份 Codex 登录，三选一：
    --login       单独登录一次（推荐）：CODEX_HOME=.local/codex codex login，和 ~/.codex 完全分开
    --link-login  复用您平时的登录：把 .local/codex/auth.json 做成指向 ~/.codex/auth.json 的符号链接。
                  风险：Codex 刷新令牌时会通过链接写回 ~/.codex/auth.json；在试用里执行 codex logout
                  会把这份登录在服务端作废，您平时的 Codex 也要重新登录
    --api-key     用环境变量 OPENAI_API_KEY 登录（codex login --with-api-key）
  在终端里运行又没选时，会问您。

  项目目录默认是当前目录；其余参数原样交给 codex。
EOF
}

MODE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --login) MODE=login; shift ;;
    --link-login) MODE=symlink; shift ;;
    --api-key) MODE=apikey; shift ;;
    -h | --help) usage; exit 0 ;;
    *) break ;;
  esac
done
PROJ="$PWD"
if [ $# -gt 0 ] && [ "${1#-}" = "$1" ]; then
  PROJ="$1"
  shift
fi
[ "${1:-}" != "--" ] || shift
[ -d "$PROJ" ] || die "项目目录不存在：$PROJ"

ISO="$TF_LOCAL/codex"
[ -f "$ISO/config.toml" ] && [ -f "$ISO/hooks.json" ] || die "还没有隔离配置：请先运行 scripts/local-up.sh"
command -v codex >/dev/null 2>&1 || die "没找到 codex 命令。请先安装 Codex（npm i -g @openai/codex，或 macOS 上 brew install codex）。"

# 您平时的 Codex 目录（只读）：自己设过 CODEX_HOME 的以它为准
USER_CODEX="${CODEX_HOME:-$HOME/.codex}"
case "$USER_CODEX" in "$TF_LOCAL"/*) USER_CODEX="$HOME/.codex" ;; esac
export CODEX_HOME="$ISO"

uses_keyring() {
  grep -Eq '^[[:space:]]*cli_auth_credentials_store[[:space:]]*=[[:space:]]*"(keyring|auto)"' "$ISO/config.toml" 2>/dev/null
}

link_login() {
  local src="$USER_CODEX/auth.json"
  if [ ! -f "$src" ]; then
    die "没有找到 $src。您平时的 Codex 可能把登录存在系统钥匙串里（cli_auth_credentials_store = keyring/auto），钥匙串按 CODEX_HOME 路径区分，复用不了；请用 --login 单独登录。"
  fi
  if uses_keyring; then
    warn "试用配置里 cli_auth_credentials_store 是 keyring/auto：Codex 会把登录搬进钥匙串、删掉这条链接，之后和 ~/.codex 就分开了。"
  fi
  ln -s "$src" "$ISO/auth.json"
  cat <<EOF
已把 $ISO/auth.json 链接到 $src（复用您平时的登录）。请留意：
  - Codex 刷新登录令牌时会通过这条链接写回 $src（和您平时用 Codex 时一样的写法）；
  - 不要在试用里执行 codex logout：它会在 OpenAI 那边作废这份登录，您平时的 Codex 也得重新登录；
  - 不想再共用：rm $ISO/auth.json（只删链接，不删原文件），然后 scripts/try-codex.sh --login。
EOF
}

have_login() {
  if [ -L "$ISO/auth.json" ] && [ ! -e "$ISO/auth.json" ]; then
    warn "$ISO/auth.json 是一条断开的符号链接（原文件不在了），删掉它重新选登录方式：rm $ISO/auth.json"
    return 1
  fi
  [ -e "$ISO/auth.json" ] && return 0
  # 钥匙串模式：auth.json 不在也可能已登录，交给 codex login status 判断（只读）
  if uses_keyring && codex login status >/dev/null 2>&1; then
    return 0
  fi
  return 1
}

if ! have_login; then
  if [ -z "$MODE" ]; then
    if [ ! -t 0 ]; then
      die "试用目录里还没有 Codex 登录。请在终端里运行 scripts/try-codex.sh --login（或 --link-login、--api-key，见 --help）。"
    fi
    cat <<EOF
试用目录（$ISO）里还没有 Codex 登录。选一种：
  1) 单独登录一次（推荐，和 ~/.codex 完全分开）
  2) 复用您平时的登录（符号链接到 $USER_CODEX/auth.json；令牌刷新会写回原文件，试用里不要 codex logout）
  3) 用环境变量 OPENAI_API_KEY 登录
  q) 先不启动
EOF
    printf '请选择 [1]: '
    read -r ans
    case "${ans:-1}" in
      1) MODE=login ;;
      2) MODE=symlink ;;
      3) MODE=apikey ;;
      *) say "没有启动 Codex。"; exit 0 ;;
    esac
  fi
  case "$MODE" in
    login) codex login ;;
    symlink) link_login ;;
    apikey)
      [ -n "${OPENAI_API_KEY:-}" ] || die "没有设置 OPENAI_API_KEY"
      printenv OPENAI_API_KEY | codex login --with-api-key
      ;;
  esac
  have_login || die "还是没有登录成功，请看上面 codex 的提示。"
fi

# 信任提示：Codex 把信任记在 CODEX_HOME/config.toml 的 [hooks.state]，键里带 hooks.json 的路径
TRUSTED="$("$TF_VPY" "$TF_ROOT/scripts/_trial.py" codex-trust "$ISO/config.toml" "$ISO/hooks.json" 2>/dev/null || echo 0)"
if [ "${TRUSTED:-0}" -lt 4 ]; then
  cat <<'EOF'
第一次在试用目录里用 Codex：进去后输入 /hooks，把 4 条 teamflow hook（SessionStart、UserPromptSubmit、
Stop、SessionEnd）都设为信任（Trusted），然后退出再用本脚本重新进入。没信任之前这 4 条不会运行：
看不到会话开始时的看板摘要，进度也不会上报（规划里的场景 7 就是这个样子）。
EOF
fi

BASE="$(tf_base)"
if ! tf_health "$BASE"; then
  warn "服务端没有在 $BASE 运行，teamflow 的工具会连不上。先运行 scripts/local-up.sh"
fi

tf_no_proxy
cd "$PROJ"
exec codex "$@"
