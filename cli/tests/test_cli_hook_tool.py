"""`teamflow hook tool`：Claude Code 的 PostToolUse（D40），把每次 teamflow 工具调用对到会话。

跨包约定：spool 写一条 {"type":"tool_map","key":hash(client,session,tool_use_id),"session_id","tool_use_id","tool"}，
由 Stop / SessionEnd 拉起的 flush 经 POST /api/v1/hooks/batch 上报。hook 不联网、不拉起进程、不输出、永远 fail-open；
不读 tool_input / tool_response。--client codex 直接退出 0。
"""

import io
import json
import os
import socket
import subprocess
import sys

import pytest
from tfhelpers import SID, TOOL_USE_ID, stdin_for

from teamflow import cli, hooks, spool

CWD = "/tmp"
ITEM_KEYS = {"type", "key", "session_id", "tool_use_id", "tool"}


def _tool(env, payload=None, client="claude", **extra):
    return env.hook("tool", client, payload if payload is not None else stdin_for(client, "tool", CWD), **extra)


def _all_state_bytes(env) -> bytes:
    out = b""
    for root, _, files in os.walk(env.state):
        for n in files:
            with open(os.path.join(root, n), "rb") as f:
                out += f.read()
    return out


@pytest.fixture
def no_network(monkeypatch):
    calls = []

    def boom(*a, **k):
        calls.append(a)
        raise OSError("network used")

    monkeypatch.setattr(socket, "create_connection", boom)
    monkeypatch.setattr(socket.socket, "connect", boom)
    monkeypatch.setattr(socket, "getaddrinfo", boom)
    return calls


def _run_inproc(monkeypatch, args, stdin):
    out = io.BytesIO()
    stdout = io.TextIOWrapper(out, encoding="utf-8")
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(sys, "stdout", stdout)
    rc = cli.main(args)
    stdout.flush()
    return rc, out.getvalue()


def test_writes_one_tool_map_record(env, stub):
    env.write_cred(stub.url)
    p = _tool(env)
    assert p.returncode == 0
    assert p.stdout == b"" and p.stderr == b""  # 不输出任何内容（同步 hook 的 stdout 会被当 JSON 解析）
    (rec,) = env.spool_records()
    item = rec["item"]
    assert set(item) == ITEM_KEYS  # 按跨包约定，不多带字段
    assert item == {
        "type": "tool_map",
        "key": spool.idem_key("claude", SID["claude"], "tool_map", TOOL_USE_ID),
        "session_id": SID["claude"],
        "tool_use_id": TOOL_USE_ID,
        "tool": "claim_task",  # 去掉 mcp__teamflow__ 前缀
    }
    assert rec["key"] == item["key"] and len(item["key"]) == 40
    assert rec["client"] == "claude" and rec["ws"] == "team" and rec["cred"] == env.cred
    assert rec["kind"] == "heartbeat"
    assert stub.requests == []  # 不联网
    assert env.spawned() == []  # 不拉起 flush，等 Stop / SessionEnd
    assert env.log_text() == ""


def test_tool_input_and_response_never_stored(env, stub):
    env.write_cred(stub.url)
    assert _tool(env).returncode == 0
    blob = _all_state_bytes(env)
    assert b"TOOL-INPUT-SECRET" not in blob and b"TOOL-RESPONSE-SECRET" not in blob
    assert b"aws" not in blob and b"transcript" not in blob and b"scratchpad" not in blob
    assert b"T-42" not in blob  # 工具入参里的任务编号也不记：只有会话和 tool_use_id


def test_tool_handler_only_reads_three_fields(env, stub, monkeypatch, no_network):
    """read_stdin 先丢掉 tool_input / tool_response；tool() 只取 tool_name、session_id、tool_use_id（和 cwd）。"""
    env.write_cred(stub.url)
    seen = []
    real = hooks.tool

    class Spy(dict):
        def get(self, k, default=None):
            seen.append(k)
            return super().get(k, default)

        def __getitem__(self, k):
            seen.append(k)
            return super().__getitem__(k)

    monkeypatch.setitem(hooks.HANDLERS, "tool", lambda payload, client, cred: real(Spy(payload), client, cred))
    stdin = io.TextIOWrapper(io.BytesIO(json.dumps(stdin_for("claude", "tool", CWD)).encode()), encoding="utf-8")
    rc, out = _run_inproc(monkeypatch, ["hook", "tool", "--client", "claude", "--cred", env.cred], stdin)
    assert rc == 0 and out == b""
    assert set(seen) <= {"tool_name", "session_id", "tool_use_id", "cwd"}, seen
    assert no_network == []
    assert len(env.spool_records()) == 1


def test_codex_exits_without_reading_stdin(env, stub, monkeypatch, no_network):
    env.write_cred(stub.url)

    touched = []

    class Untouchable:  # hook 会吞掉一切异常，所以记下访问再抛，最后断言没人碰过
        def __getattr__(self, name):
            touched.append(name)
            raise OSError("读了 stdin：%s" % name)

    rc, out = _run_inproc(monkeypatch, ["hook", "tool", "--client", "codex", "--cred", env.cred], Untouchable())
    assert rc == 0 and out == b""
    assert touched == []
    # 对照：--client claude 确实会读 stdin
    rc, out = _run_inproc(monkeypatch, ["hook", "tool", "--client", "claude", "--cred", env.cred], Untouchable())
    assert rc == 0 and out == b"" and touched
    touched.clear()
    assert env.spool_records() == [] and env.log_text() == ""
    # 子进程里也一样：合格的输入照样什么都不写
    p = _tool(env, client="codex")
    assert p.returncode == 0 and p.stdout == b"" and p.stderr == b""
    assert env.spool_records() == []
    assert not os.path.exists(os.path.join(env.state, "spool"))


@pytest.mark.parametrize("name", [
    "Bash", "mcp__other__claim_task", "mcp__teamflowx__claim_task", "xmcp__teamflow__claim_task",
    "mcp__plugin_tf_teamflow__claim_task", "mcp__teamflow-cloud__claim_task", None, 42,
])
def test_other_tools_ignored_silently(env, stub, name):
    env.write_cred(stub.url)
    p = _tool(env, stdin_for("claude", "tool", CWD, tool_name=name))
    assert p.returncode == 0 and p.stdout == b"" and p.stderr == b""
    assert env.spool_records() == []
    assert env.log_text() == ""  # matcher 漏进来的别家工具：不当错误记日志


@pytest.mark.parametrize("name", [
    "mcp__teamflow__", "mcp__teamflow__Claim_task", "mcp__teamflow__claim-task", "mcp__teamflow__claim_task;rm",
    "mcp__teamflow___x", "mcp__teamflow__1x", "mcp__teamflow__" + "a" * 65, "mcp__teamflow__认领",
])
def test_bad_teamflow_tool_names_rejected(env, stub, name):
    env.write_cred(stub.url)
    p = _tool(env, stdin_for("claude", "tool", CWD, tool_name=name))
    assert p.returncode == 0 and p.stdout == b""
    assert env.spool_records() == []
    assert "tool: bad tool name" in env.log_text()


@pytest.mark.parametrize("tuid", [None, "", "toolu_1", "toolu_1234567", "toolu_" + "a" * 81, "toolu_01 ABCDEFGH",
                                  "toolu_01/../xyzab", "toolu_01ABCDEFGH\n", "toolu_01-ABCDEFGH", "toolu_0１ABCDEFGH",
                                  "TOOLU_012HDfH2mEGmyGFoKMDw5GJw", "call-8f2a_x9Zq1w2e3", "x" * 20, 12345678,
                                  ["toolu_012HDfH2mEGmyGFoKMDw5GJw"]])
def test_bad_tool_use_id_rejected(env, stub, tuid):
    env.write_cred(stub.url)
    over = {"tool_use_id": tuid} if tuid is not None else {}
    payload = stdin_for("claude", "tool", CWD, **over)
    if tuid is None:
        payload.pop("tool_use_id")
    p = _tool(env, payload)
    assert p.returncode == 0 and p.stdout == b"" and p.stderr == b""
    assert env.spool_records() == []
    assert "tool: missing or bad tool_use_id" in env.log_text()


@pytest.mark.parametrize("tuid", ["toolu_012HDfH2mEGmyGFoKMDw5GJw", "toolu_018mtaXS32pXAsBn1eDV31wG",
                                  "toolu_bdrk_01AbCdEfGh", "toolu_vrtx_01AbCdEfGhIj", "toolu_12345678", "toolu_" + "a" * 80])
def test_good_tool_use_ids_accepted(env, stub, tuid):
    """规则与服务端校验 _meta["claudecode/toolUseId"] 的一致：toolu_ 加 8–80 个字母、数字、下划线
    （一方 API、Bedrock 的 toolu_bdrk_…、Vertex 的 toolu_vrtx_…）。服务端匹配不上的不写，免得进 dead-letter。"""
    env.write_cred(stub.url)
    assert _tool(env, stdin_for("claude", "tool", CWD, tool_use_id=tuid)).returncode == 0
    (rec,) = env.spool_records()
    assert rec["item"]["tool_use_id"] == tuid


@pytest.mark.parametrize("sid", [None, "", "a b", "x" * 129, 7])
def test_bad_session_id_rejected(env, stub, sid):
    env.write_cred(stub.url)
    p = _tool(env, stdin_for("claude", "tool", CWD, session_id=sid))
    assert p.returncode == 0 and p.stdout == b""
    assert env.spool_records() == []
    assert "tool: missing or bad session_id" in env.log_text()


def test_idempotent_per_tool_use_id(env, stub):
    env.write_cred(stub.url)
    for _ in range(3):
        assert _tool(env).returncode == 0
    assert len(env.spool_records()) == 1
    assert _tool(env, stdin_for("claude", "tool", CWD, tool_use_id="toolu_018mtaXS32pXAsBn1eDV31wG")).returncode == 0
    assert len(env.spool_records()) == 2
    # 同一个 tool_use_id、另一个会话（嵌套会话之类）：是另一条
    assert _tool(env, stdin_for("claude", "tool", CWD, session_id="99999999-9999-4999-8999-999999999990")).returncode == 0
    keys = {r["key"] for r in env.spool_records()}
    assert len(keys) == 3


def test_parallel_tool_calls_all_recorded(env, stub):
    """Claude 并行调用多个工具时 PostToolUse 并发触发（cc_hooks.md「PostToolBatch」）：一条都不能丢，也不能重复。"""
    env.write_cred(stub.url)
    procs = []
    for i in range(8):
        payload = stdin_for("claude", "tool", CWD, tool_use_id="toolu_par_%02d_abcdef" % i)  # toolu_ 后 13 个字符
        for _ in range(2):  # 每个 tool_use_id 同时来两次
            p = subprocess.Popen([sys.executable, "-m", "teamflow", "hook", "tool", "--client", "claude", "--cred", env.cred],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env.environ())
            procs.append((p, json.dumps(payload).encode()))
    for p, data in procs:
        out, err = p.communicate(data, timeout=30)
        assert p.returncode == 0 and out == b"" and err == b""
    recs = env.spool_records()
    assert sorted(r["item"]["tool_use_id"] for r in recs) == ["toolu_par_%02d_abcdef" % i for i in range(8)]
    assert not [n for n in os.listdir(os.path.join(env.state, "spool")) if n.startswith(".tmp")]


def test_flush_uploads_tool_map_with_claude_token(env, stub):
    env.write_cred(stub.url)
    _tool(env)
    env.hook("stop", "claude", stdin_for("claude", "stop", CWD))
    p = env.run(["flush"])
    assert p.returncode == 0, p.stderr
    (batch,) = [r for r in stub.requests if r["path"] == "/api/v1/hooks/batch"]
    assert batch["headers"]["Authorization"] == "Bearer tf_pat_claude_x"
    assert batch["headers"]["X-Teamflow-Client"] == "claude_code"
    items = {it["type"]: it for it in batch["body"]["items"]}
    assert set(items) == {"tool_map", "turn_end"}
    tm = items["tool_map"]
    assert set(tm) == ITEM_KEYS
    assert (tm["session_id"], tm["tool_use_id"], tm["tool"]) == (SID["claude"], TOOL_USE_ID, "claim_task")
    assert tm["session_id"] == items["turn_end"]["session_id"]  # 和 hooks 登记的会话同一个 ID
    raw = json.dumps(batch["body"], ensure_ascii=False)
    assert "SECRET" not in raw and "T-42" not in raw
    assert env.spool_records() == []
    # 发送过的再写一次：被 sent 标记挡住
    _tool(env)
    assert env.spool_records() == []


def test_uses_session_workspace(env, stub, tmp_path):
    """多个 workspace 时跟着会话走（SessionStart 记下的 ws）：会话是用那个 workspace 的 token 登记的，
    映射也得用同一个 token 报，服务端的 resolve_session 才认。"""
    env.write_cred(stub.url)
    data = json.load(open(env.cred))
    data["workspaces"]["side"] = {"api_url": stub.url, "tokens": {"claude": "tf_pat_side_claude"}, "repo_patterns": []}
    json.dump(data, open(env.cred, "w"))
    os.makedirs(os.path.join(env.state, "sessions"), exist_ok=True)
    with open(os.path.join(env.state, "sessions", "claude-%s.json" % SID["claude"]), "w") as f:
        json.dump({"ws": "side", "turns": 0}, f)
    before = open(os.path.join(env.state, "sessions", "claude-%s.json" % SID["claude"]), "rb").read()
    _tool(env)
    (rec,) = env.spool_records()
    assert rec["ws"] == "side"
    # 不写会话状态（并行的 PostToolUse 会互相覆盖）
    assert open(os.path.join(env.state, "sessions", "claude-%s.json" % SID["claude"]), "rb").read() == before
    env.run(["flush"])
    (batch,) = [r for r in stub.requests if r["path"] == "/api/v1/hooks/batch"]
    assert batch["headers"]["Authorization"] == "Bearer tf_pat_side_claude"


@pytest.mark.parametrize("stdin", [b"not json{", b"[1,2,3]", b"\xff\xfe", b"", b"null"])
def test_bad_stdin_fail_open(env, stub, stdin):
    env.write_cred(stub.url)
    p = env.run(["hook", "tool", "--client", "claude", "--cred", env.cred], stdin)
    assert p.returncode == 0 and p.stdout == b"" and p.stderr == b""
    assert env.spool_records() == []


def test_missing_or_broken_creds_fail_open(env, tmp_path):
    p = _tool(env, cred=str(tmp_path / "nope.json"))
    assert p.returncode == 0 and p.stdout == b"" and p.stderr == b""
    assert env.spool_records() == []
    assert "CredError" in env.log_text()


def test_unwritable_state_dir_fail_open(env, stub, tmp_path):
    env.write_cred(stub.url)
    blocker = tmp_path / "file-not-dir"
    blocker.write_text("x")
    p = _tool(env, TEAMFLOW_STATE_DIR=str(blocker / "state"))
    assert p.returncode == 0 and p.stdout == b"" and p.stderr == b""


_PROBE = r"""
import sys
before = set(sys.modules)
import io
from teamflow import cli
sys.stdin = io.TextIOWrapper(io.BytesIO(sys.argv[1].encode()), encoding="utf-8")
buf = io.BytesIO()
wrapper = io.TextIOWrapper(buf, encoding="utf-8")
sys.stdout = wrapper
rc = cli.main(sys.argv[2:])
wrapper.flush()
out = buf.getvalue().decode()
sys.stdout = sys.__stdout__
watch = ("json", "subprocess", "re", "argparse", "threading", "hashlib", "http.client", "socket",
         "teamflow.detach", "teamflow.net", "teamflow.inbox", "teamflow.gitinfo")
loaded = sorted(m for m in watch if m in sys.modules and m not in before)
import json
print(json.dumps({"rc": rc, "out": out, "loaded": loaded}))
"""


def test_fast_path_imports_nothing_heavy(env, stub):
    """快速路径只用标准库、不导入 json；不碰网络和子进程模块。sha256 用内置的 _sha2/_sha256，不加载 OpenSSL。"""
    env.write_cred(stub.url)
    payload = json.dumps(stdin_for("claude", "tool", CWD))
    p = subprocess.run([sys.executable, "-c", _PROBE, payload, "hook", "tool", "--client", "claude", "--cred", env.cred],
                       capture_output=True, env=env.environ(), timeout=30)
    assert p.returncode == 0, p.stderr.decode()
    res = json.loads(p.stdout)
    assert res["rc"] == 0 and res["out"] == ""
    builtin_sha = any(_importable(m) for m in ("_sha2", "_sha256"))
    assert res["loaded"] == ([] if builtin_sha else ["hashlib"]), res
    assert len(env.spool_records()) == 1


def _importable(name):
    try:
        __import__(name)
        return True
    except ImportError:
        return False


def test_idem_key_matches_hashlib():
    import hashlib

    raw = "\x1f".join(("claude", "s1", "tool_map", TOOL_USE_ID)).encode()
    assert spool.idem_key("claude", "s1", "tool_map", TOOL_USE_ID) == hashlib.sha256(raw).hexdigest()[:40]
    assert spool.idem_key("claude", "s1", "tool_map", "t") != spool.idem_key("claude", "s1", "turn_end", "t")


def test_argparse_help_lists_tool():
    p = subprocess.run([sys.executable, "-m", "teamflow", "hook", "--help"], capture_output=True, timeout=30)
    assert p.returncode == 0
    assert "tool" in p.stdout.decode()
