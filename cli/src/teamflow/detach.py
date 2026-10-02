"""拉起与 hook 完全分离的子进程（plan 6.4 实现规则 1）。

stdin/stdout/stderr 全部接 /dev/null、关闭其余 fd、新开会话：
子进程不继承 hook 的输出管道，Claude Code / Codex 不会等它的网络请求结束。
"""

import os
import sys


def flush_argv(client: str | None = None, cred: str | None = None, ws: str | None = None, refresh: bool = False):
    argv = [sys.executable, "-m", "teamflow", "flush"]
    if refresh:
        argv.append("--refresh")
    if client:
        argv += ["--client", client]
    if cred:
        argv += ["--cred", cred]
    if ws:
        argv += ["--ws", ws]
    return argv


def spawn_detached(argv: list) -> bool:
    if os.environ.get("TEAMFLOW_NO_SPAWN") == "1":  # 测试与基准用：只记录不拉起
        _record(argv)
        return False
    import subprocess

    try:
        subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            start_new_session=True,
            cwd="/",
        )
        _record(argv)
        return True
    except OSError:
        from teamflow.common import log_exc

        log_exc("spawn")
        return False


def _record(argv):
    path = os.environ.get("TEAMFLOW_SPAWN_LOG")
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(" ".join(argv[1:]) + "\n")
    except OSError:
        pass
