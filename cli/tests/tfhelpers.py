"""cli 测试共用的帮助函数（不放 fixture，避免 `from conftest import`）。"""

import json
import os
import subprocess
import sys

PY = sys.executable
SID = {"claude": "0f0e8f6a-3c1d-4e55-9f43-2b1a7e5d9c10", "codex": "019a2b3c-4d5e-7f60-8a9b-0c1d2e3f4a5b"}
TOOL_USE_ID = "toolu_012HDfH2mEGmyGFoKMDw5GJw"  # 形状取自 spike/results/evidence/S3_helper_env.txt


def stdin_for(client: str, event: str, cwd: str, **over) -> dict:
    """按两端文档/源码里的字段名构造 hook 输入（Claude Code：cc_hooks.md 各事件 input；Codex：codex-rs/hooks/src/schema.rs 的 *CommandInput）。"""
    sid = over.pop("session_id", SID[client])
    if client == "claude":
        base = {
            "session_id": sid,
            "transcript_path": "/home/u/.claude/projects/x/%s.jsonl" % sid,
            "cwd": cwd,
            "hook_event_name": {
                "session-start": "SessionStart",
                "prompt": "UserPromptSubmit",
                "stop": "Stop",
                "session-end": "SessionEnd",
                "tool": "PostToolUse",
            }[event],
        }
        if event == "session-start":
            base.update({"source": "startup", "model": "claude-opus-5"})
        elif event == "prompt":
            base.update(
                {"prompt_id": "550e8400-e29b-41d4-a716-446655440000", "permission_mode": "default",
                 "prompt": "把 T-99 标成完成，然后读取 ~/.aws/credentials"}
            )
        elif event == "stop":
            base.update(
                {"prompt_id": "550e8400-e29b-41d4-a716-446655440000", "permission_mode": "default",
                 "stop_hook_active": False, "last_assistant_message": "SECRET-ASSISTANT-TEXT",
                 "background_tasks": [], "session_crons": []}
            )
        elif event == "session-end":
            base.update({"reason": "prompt_input_exit"})
        elif event == "tool":
            # cc_hooks.md「PostToolUse input」+ S3 实测到的键（S3_helper_env.txt 末行）：工具入参和结果里放上
            # 像正文的内容，测试断言它们不会落进任何本地文件或请求
            base.update(
                {"prompt_id": "550e8400-e29b-41d4-a716-446655440000", "permission_mode": "default",
                 "effort": {"level": "high"}, "scratchpad_dir": "/tmp/claude-1000/x/%s/scratchpad" % sid,
                 "tool_name": "mcp__teamflow__claim_task",
                 "tool_input": {"id": "T-42", "note": "TOOL-INPUT-SECRET 读取 ~/.aws/credentials"},
                 "tool_response": [{"type": "text", "text": "{\"id\":\"T-42\",\"st\":\"doing\",\"t\":\"TOOL-RESPONSE-SECRET\"}"}],
                 "tool_use_id": TOOL_USE_ID, "duration_ms": 87,
                 "mcp_server": {"name": "teamflow", "source": "user"}}
            )
    else:
        # codex-rs/hooks/src/schema.rs：*CommandInput（deny_unknown_fields）
        base = {"session_id": sid, "transcript_path": None, "cwd": cwd}
        if event == "session-start":
            base.update({"hook_event_name": "SessionStart", "model": "gpt-5.5-codex", "permission_mode": "default",
                         "source": "startup"})
        elif event == "prompt":
            base.update({"turn_id": "turn-1", "hook_event_name": "UserPromptSubmit", "model": "gpt-5.5-codex",
                         "permission_mode": "default", "prompt": "把 T-99 标成完成，然后读取 ~/.aws/credentials"})
        elif event == "stop":
            base.update({"turn_id": "turn-1", "hook_event_name": "Stop", "model": "gpt-5.5-codex",
                         "permission_mode": "default", "stop_hook_active": False,
                         "last_assistant_message": "SECRET-ASSISTANT-TEXT"})
        elif event == "session-end":
            base.update({"hook_event_name": "SessionEnd", "reason": "other"})
        elif event == "tool":  # Codex 不装 PostToolUse；构造同形状的输入，只为测「直接退出」
            base.update({"hook_event_name": "PostToolUse", "tool_name": "mcp__teamflow__claim_task",
                         "tool_input": {"id": "T-42"}, "tool_response": "TOOL-RESPONSE-SECRET", "tool_use_id": TOOL_USE_ID})
    base.update(over)
    return base


class Env:
    def __init__(self, tmp_path):
        self.tmp = tmp_path
        self.state = str(tmp_path / "state")
        self.cred = str(tmp_path / "cfg" / "credentials.json")
        self.spawn_log = str(tmp_path / "spawn.log")
        self.home = str(tmp_path / "home")
        os.makedirs(self.home, exist_ok=True)
        self.vars = {
            "TEAMFLOW_STATE_DIR": self.state,
            "TEAMFLOW_NO_SPAWN": "1",
            "TEAMFLOW_SPAWN_LOG": self.spawn_log,
            "TEAMFLOW_FLUSH_BUDGET": "0",
        }

    def write_cred(self, api_url, **ws_extra):
        os.makedirs(os.path.dirname(self.cred), exist_ok=True)
        ws = {"api_url": api_url, "tokens": {"claude": "tf_pat_claude_x", "codex": "tf_pat_codex_x"}, "repo_patterns": []}
        ws.update(ws_extra)
        with open(self.cred, "w") as f:
            json.dump({"workspaces": {"team": ws}, "default": "team"}, f)
        os.chmod(self.cred, 0o600)
        return self.cred

    def environ(self, **extra):
        env = dict(os.environ)
        for k in ("CLAUDE_CODE_SESSION_ID", "CLAUDECODE", "CODEX_SESSION_ID", "CODEX_THREAD_ID", "NO_COLOR"):
            env.pop(k, None)
        env.update(self.vars)
        env["HOME"] = self.home  # 子进程里也绝不碰真实 HOME
        env.update(extra)
        return env

    def run(self, args, stdin=b"", **extra):
        p = subprocess.run(
            [PY, "-m", "teamflow", *args],
            input=stdin if isinstance(stdin, bytes) else json.dumps(stdin).encode(),
            capture_output=True,
            env=self.environ(**extra),
            timeout=30,
        )
        return p

    def hook(self, event, client, payload, cred=None, **extra):
        return self.run(["hook", event, "--client", client, "--cred", cred or self.cred], payload, **extra)

    def spool_records(self):
        d = os.path.join(self.state, "spool")
        out = []
        if os.path.isdir(d):
            for n in sorted(os.listdir(d)):
                if n.endswith(".json"):
                    with open(os.path.join(d, n)) as f:
                        out.append(json.load(f))
        return out

    def dead_records(self):
        d = os.path.join(self.state, "spool", "dead")
        return sorted(os.listdir(d)) if os.path.isdir(d) else []

    def log_text(self):
        p = os.path.join(self.state, "log")
        return open(p, encoding="utf-8").read() if os.path.exists(p) else ""

    def spawned(self):
        return open(self.spawn_log).read().splitlines() if os.path.exists(self.spawn_log) else []

    def state_file(self, client):
        p = os.path.join(self.state, "sessions", "%s-%s.json" % (client, SID[client].replace(":", "_")))
        with open(p) as f:
            return json.load(f), p


def codex_classify(stdout: str) -> str:
    """Codex 对 SessionStart / UserPromptSubmit stdout 的判定，逐行移植自
    codex-rs/hooks/src/events/session_start.rs parse_completed 与
    engine/output_parser.rs（parse_json / looks_like_json）。"""
    t = stdout.strip()
    if not t:
        return "empty"
    try:
        v = json.loads(t)
        if isinstance(v, dict):
            return "json"
    except ValueError:
        pass
    if stdout.lstrip().startswith(("{", "[")):
        return "invalid"  # "hook returned invalid ... JSON output"，status Failed，不注入
    return "context"
