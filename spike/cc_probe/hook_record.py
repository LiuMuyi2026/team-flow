#!/usr/bin/env python3
"""M0 S3/S6 探针：记录 hook 的 stdin 关键字段和环境里的会话 ID，不输出任何内容（不注入）。

Claude Code 配置（exec form）：{"type":"command","command":"/abs/spike/cc_probe/hook_record.py","args":["<标签>"]}
记录写到 ${TF_PROBE_OUT:-/tmp/teamflow-probe}/hook_record.jsonl。不记录 prompt、tool_input、tool_response 等正文。
"""
import json
import os
import sys
import time

out = os.environ.get("TF_PROBE_OUT") or "/tmp/teamflow-probe"
os.makedirs(out, exist_ok=True)
try:
    data = json.loads(sys.stdin.read() or "{}")
except Exception as e:  # noqa: BLE001
    data = {"_parse_error": str(e)}
rec = {
    "ts": time.time(),
    "argv": sys.argv[1:],
    "event": data.get("hook_event_name"),
    "stdin_session_id": data.get("session_id"),
    "source": data.get("source"),
    "tool_use_id": data.get("tool_use_id"),
    "tool_name": data.get("tool_name"),
    "env_CLAUDE_CODE_SESSION_ID": os.environ.get("CLAUDE_CODE_SESSION_ID"),
    "stdin_keys": sorted(data.keys()),
}
with open(os.path.join(out, "hook_record.jsonl"), "a", encoding="utf-8") as f:
    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
