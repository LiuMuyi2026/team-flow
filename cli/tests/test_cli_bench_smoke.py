"""spike/bench_hooks.py 的 UserPromptSubmit 四条路径（I3）：跑通、输出次数对、prompt 从不拉起子进程。"""

import json
import os
import subprocess
import sys

import pytest

BENCH = os.path.join(os.path.dirname(__file__), "..", "..", "spike", "bench_hooks.py")
TF = os.path.join(os.path.dirname(sys.executable), "teamflow")


@pytest.mark.skipif(not os.path.exists(BENCH) or not os.path.exists(TF), reason="没有 spike 脚本或 teamflow 入口")
def test_bench_prompt_paths(tmp_path):
    env = dict(os.environ)
    for k in ("TEAMFLOW_NO_SPAWN", "TEAMFLOW_SPAWN_LOG", "TEAMFLOW_STATE_DIR"):
        env.pop(k, None)
    p = subprocess.run(
        [sys.executable, BENCH, "--stub", "normal", "--n", "3", "--clients", "claude,codex", "--events", "prompt,stop",
         "--gap", "0", "--bin", TF, "--tmp", str(tmp_path), "--json"],
        capture_output=True, env=env, timeout=120,
    )
    assert p.returncode == 0, p.stderr.decode()
    res = json.loads(p.stdout.decode().strip().splitlines()[-1])
    rows = {(r["cmd"], r["client"]): r for r in res["rows"]}
    for client in ("claude", "codex"):
        assert rows[("prompt", client)]["nonempty"] == 0
        assert rows[("prompt:stale", client)]["nonempty"] == 0
        assert rows[("prompt:emit", client)]["nonempty"] == 3
        assert rows[("prompt:stale+emit", client)]["nonempty"] == 3
        for name in ("prompt", "prompt:stale", "prompt:emit", "prompt:stale+emit"):
            assert rows[(name, client)]["spawned"] == 0, name
            assert rows[(name, client)]["target"] == 30
        assert rows[("stop", client)]["spawned"] == 3  # Stop 每回合拉起 flush --refresh，缓存靠它刷新
