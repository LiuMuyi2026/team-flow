#!/bin/sh
# M0 S3 探针：包在 teamflow mcp-headers 外面的 headersHelper。
# 只记录与会话相关的环境变量（不记录 token 和凭据值），再把参数原样交给 teamflow mcp-headers。
# 用法（Claude Code 的 MCP 配置里）：
#   "headersHelper": "/abs/spike/cc_probe/helper_wrap.sh --client claude --cred /abs/credentials.json"
# 记录写到 ${TF_PROBE_OUT:-/tmp/teamflow-probe}/hh_env.jsonl。TEAMFLOW_BIN 可指定 teamflow 路径。
OUT="${TF_PROBE_OUT:-/tmp/teamflow-probe}"
mkdir -p "$OUT"
PY="$(command -v python3 || command -v python)"
"$PY" - >> "$OUT/hh_env.jsonl" <<'PY'
import json, os, time
keys = ["TF_S_LABEL", "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_MCP_SERVER_NAME", "CLAUDE_CODE_MCP_SERVER_URL",
        "CLAUDECODE", "CLAUDE_CODE_CHILD_SESSION", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CONFIG_DIR",
        "CODEX_SESSION_ID", "CODEX_THREAD_ID", "MCP_PROTOCOL_NEGOTIATION", "MCP_SDK_GENERATION"]
rec = {"ts": time.time(), "pid": os.getpid(), "ppid": os.getppid(), "cwd": os.getcwd(), "n_env": len(os.environ)}
rec.update({k: os.environ.get(k) for k in keys})
print(json.dumps(rec, ensure_ascii=False))
PY
exec "${TEAMFLOW_BIN:-teamflow}" mcp-headers "$@"
