"""M0 复审新问题 3：setup 合并 hooks 时绝不删除、挪动别人的 handler 和组。

- 别人的组在中间、末尾：重跑 setup 后位置和内容逐字节不变；
- 混合组（同组里既有别人的 handler 又有 teamflow 的）：只换 teamflow 那一条，组的其他字段不动；
- 多个 teamflow 组：保留第一个原地更新，其余组里只删 teamflow handler；删空的组留 {"hooks": []} 占位
  （Codex：codex-rs/config/src/hook_config.rs MatcherGroup.hooks 是 serde(default) 的 Vec；Claude Code 2.1.287
  的设置 schema 里 hooks 是不限长度的数组），末尾的空组直接去掉；
- Codex 的信任键是「组序号:handler 序号」（hooks/src/lib.rs hook_key），所以排在别人 handler 前面的重复 handler
  不删，打印警告。

两端（~/.codex/hooks.json 和 ~/.claude/settings.json）同样处理。--home 指向临时目录。
"""

import json
import os

import pytest

from teamflow import setup_cmd

BIN = "/opt/tf/bin/teamflow"
NEW_BIN = "/new/place/teamflow"
EVENTS = ("SessionStart", "UserPromptSubmit", "Stop", "SessionEnd")


def _setup(env, home, bin_path=BIN):
    p = env.run(["setup", "--home", home, "--bin", bin_path, "--api-url", "http://127.0.0.1:8100"],
                TEAMFLOW_PAT_CLAUDE="tf_pat_c1", TEAMFLOW_PAT_CODEX="tf_pat_x1")
    assert p.returncode == 0, p.stderr.decode()
    return p.stdout.decode()


def _paths(home):
    return {"codex": os.path.join(home, ".codex", "hooks.json"), "claude": os.path.join(home, ".claude", "settings.json")}


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")  # 和 setup 写出的格式一样


def _bytes(obj) -> str:
    """保留键顺序的序列化：两次结果相同就是逐字节相同。"""
    return json.dumps(obj, ensure_ascii=False)


def _foreign(client, tag):
    """别人的 handler：Claude 用 exec form，Codex 用命令串；带上各种字段，确认原样保留。"""
    if client == "claude":
        return {"type": "command", "command": "/usr/local/bin/other-tool", "args": ["notify", tag], "timeout": 7,
                "statusMessage": "其他工具 %s" % tag}
    return {"type": "command", "command": "/usr/local/bin/other-tool notify %s" % tag, "timeout": 7,
            "statusMessage": "其他工具 %s" % tag}


def _fgroup(client, tag, matcher=None):
    g = {"hooks": [_foreign(client, tag)]}
    if matcher is not None:
        g = {"matcher": matcher, "hooks": g["hooks"]}
    return g


def _is_tf(h):
    return setup_cmd._is_teamflow_handler(h)


def _assert_foreign_same(before, after, idx):
    for i in idx:
        assert _bytes(after[i]) == _bytes(before[i]), (i, before[i], after[i])


def _rewrite(home, fn):
    """对两端每个事件数组调用 fn(client, event, arr) → 新数组，写回；返回写回后的内容。"""
    out = {}
    for client, path in _paths(home).items():
        obj = _load(path)
        for ev in EVENTS:
            obj["hooks"][ev] = fn(client, ev, obj["hooks"][ev])
        _save(path, obj)
        out[client] = obj
    return out


def test_foreign_groups_middle_and_end_byte_identical(env, tmp_path):
    home = env.home
    _setup(env, home)
    # 别人的组：一个在我们前面、一个在中间（我们后面）、一个在末尾；末尾那个带 matcher
    before = _rewrite(home, lambda c, ev, arr: [_fgroup(c, "a"), arr[0], _fgroup(c, "mid"), _fgroup(c, "end", "*")])

    out = _setup(env, home, NEW_BIN)  # 换了可执行文件路径：我们的 handler 要更新
    assert "注意：" not in out
    for client, path in _paths(home).items():
        after = _load(path)
        for ev in EVENTS:
            b, a = before[client]["hooks"][ev], after["hooks"][ev]
            assert len(a) == 4
            _assert_foreign_same(b, a, (0, 2, 3))
            (h,) = a[1]["hooks"]
            assert h["command"].startswith(NEW_BIN)  # 原地更新，序号不变
    # 再跑一次：一个字节都不变
    raw = {c: open(p, "rb").read() for c, p in _paths(home).items()}
    out = _setup(env, home, NEW_BIN)
    assert out.count("未变化") >= 2
    assert {c: open(p, "rb").read() for c, p in _paths(home).items()} == raw


def test_mixed_group_only_teamflow_handler_replaced(env, tmp_path):
    home = env.home
    _setup(env, home)

    def mixed(c, ev, arr):
        ours = arr[0]
        g = {"hooks": [_foreign(c, "x"), ours["hooks"][0], _foreign(c, "y")]}
        if "matcher" in ours:
            g = {"matcher": ours["matcher"], "hooks": g["hooks"], "extra": "别人的字段"}
        return [_fgroup(c, "a"), g, _fgroup(c, "z")]

    before = _rewrite(home, mixed)
    out = _setup(env, home, NEW_BIN)
    assert "matcher" not in out  # matcher 一致，不需要警告
    for client, path in _paths(home).items():
        after = _load(path)
        for ev in EVENTS:
            b, a = before[client]["hooks"][ev], after["hooks"][ev]
            assert len(a) == 3
            _assert_foreign_same(b, a, (0, 2))
            hs_b, hs_a = b[1]["hooks"], a[1]["hooks"]
            assert len(hs_a) == 3
            assert _bytes(hs_a[0]) == _bytes(hs_b[0]) and _bytes(hs_a[2]) == _bytes(hs_b[2])  # 别人的 handler 原样
            assert _is_tf(hs_a[1]) and hs_a[1]["command"].startswith(NEW_BIN)
            assert {k: v for k, v in a[1].items() if k != "hooks"} == {k: v for k, v in b[1].items() if k != "hooks"}
            assert list(a[1]) == list(b[1])  # 组的字段和顺序都不变


def test_mixed_group_with_other_matcher_warns_and_keeps_matcher(env, tmp_path):
    home = env.home
    _setup(env, home)
    path = _paths(home)["codex"]
    hj = _load(path)
    tf = hj["hooks"]["SessionStart"][0]["hooks"][0]
    hj["hooks"]["SessionStart"] = [{"matcher": "startup", "hooks": [_foreign("codex", "x"), tf]}]
    _save(path, hj)
    out = _setup(env, home)
    assert "注意：Codex hooks.json 的 SessionStart：teamflow 的 hook 和别的 hook 在同一组（第 1 组）" in out
    assert "matcher 是 \"startup\"" in out
    g = _load(path)["hooks"]["SessionStart"][0]
    assert g["matcher"] == "startup" and len(g["hooks"]) == 2  # 没改别人的 matcher，也没拆组


def test_duplicate_teamflow_groups_keep_first_and_placeholder(env, tmp_path):
    home = env.home
    _setup(env, home)
    # [别人a, 我们, 别人b, 重复的我们, 别人c, 重复的我们]
    before = _rewrite(home, lambda c, ev, arr: [_fgroup(c, "a"), arr[0], _fgroup(c, "b"),
                                                json.loads(json.dumps(arr[0])), _fgroup(c, "c"),
                                                json.loads(json.dumps(arr[0]))])
    out = _setup(env, home, NEW_BIN)
    assert "注意：" not in out
    for client, path in _paths(home).items():
        after = _load(path)
        for ev in EVENTS:
            b, a = before[client]["hooks"][ev], after["hooks"][ev]
            assert len(a) == 5, a  # 末尾的重复组去掉；中间的留空组占位，别人的组序号不变
            _assert_foreign_same(b, a, (0, 2, 4))
            assert a[1]["hooks"][0]["command"].startswith(NEW_BIN)
            assert a[3]["hooks"] == []
            assert {k: v for k, v in a[3].items() if k != "hooks"} == {k: v for k, v in b[3].items() if k != "hooks"}
            assert sum(_is_tf(h) for g in a for h in g["hooks"]) == 1
    raw = {c: open(p, "rb").read() for c, p in _paths(home).items()}
    _setup(env, home, NEW_BIN)
    assert {c: open(p, "rb").read() for c, p in _paths(home).items()} == raw  # 占位组也稳定


def test_duplicate_handlers_inside_foreign_groups(env, tmp_path):
    """重复的 teamflow handler 在别人的组里：排在别人后面的删掉；排在前面的删了会让别人换序号，保留并警告。"""
    home = env.home
    _setup(env, home)

    def layout(c, ev, arr):
        tf = arr[0]["hooks"][0]
        return [arr[0], {"hooks": [_foreign(c, "p"), dict(tf)]}, {"hooks": [dict(tf), _foreign(c, "q")]}]

    before = _rewrite(home, layout)
    out = _setup(env, home, NEW_BIN)
    for client, path in _paths(home).items():
        where = "Codex hooks.json" if client == "codex" else "Claude Code settings.json"
        assert "注意：%s 的 Stop：第 3 组里有重复的 teamflow hook（第 1 条）排在别的 hook 前面" % where in out
        after = _load(path)
        for ev in EVENTS:
            b, a = before[client]["hooks"][ev], after["hooks"][ev]
            assert len(a) == 3
            assert a[0]["hooks"][0]["command"].startswith(NEW_BIN)
            assert _bytes(a[1]) == _bytes({"hooks": [b[1]["hooks"][0]]})  # 别人后面的那条删掉
            assert _bytes(a[2]) == _bytes(b[2])  # 删了会挪动别人的 handler：整组不动


def _tf(prefix):
    return {"type": "command", "command": "%s/teamflow hook stop --client codex --cred /c" % prefix}


def _o(n):
    return {"type": "command", "command": "/usr/bin/other %d" % n}


NEW = {"hooks": [_tf("/new")]}


@pytest.mark.parametrize("arr, want", [
    # 没有 teamflow：追加到末尾
    ([{"hooks": [_o(1)]}], [{"hooks": [_o(1)]}, NEW]),
    # 别人的组在中间和末尾
    ([{"hooks": [_o(1)]}, {"hooks": [_tf("/old")]}, {"hooks": [_o(2)]}],
     [{"hooks": [_o(1)]}, NEW, {"hooks": [_o(2)]}]),
    # 混合组：只换我们那一条
    ([{"hooks": [_o(1), _tf("/old"), _o(2)]}], [{"hooks": [_o(1), _tf("/new"), _o(2)]}]),
    # 重复组在中间：留空组占位；在末尾：去掉
    ([{"hooks": [_tf("/old")]}, {"hooks": [_tf("/old")]}, {"hooks": [_o(3)]}, {"hooks": [_tf("/x")]}],
     [NEW, {"hooks": []}, {"hooks": [_o(3)]}]),
    # 第一组是混合组，后面同组里还有一条重复的（在末尾，可以删）
    ([{"hooks": [_o(1), _tf("/old"), _tf("/old")]}], [{"hooks": [_o(1), _tf("/new")]}]),
    # 已经有的空组（别人的或以前留下的占位）不动
    ([{"hooks": []}, {"hooks": [_tf("/old")]}], [{"hooks": []}, NEW]),
])
def test_merge_event_table(arr, want):
    before = json.loads(json.dumps(arr))
    got, warnings = setup_cmd._merge_event(arr, NEW, "Stop", "X", True)
    assert got == want
    assert warnings == []
    assert arr == before  # 不改调用方的列表


def test_merge_event_when_empty_groups_not_allowed():
    """某一端将来不认空组（EMPTY_GROUP_OK 改成 False）：中间删空的组整组保留并警告；末尾的照样去掉。"""
    arr = [{"hooks": [_o(1)]}, {"hooks": [_tf("/old")]}, {"hooks": [_o(2)]}, {"hooks": [_tf("/old")]},
           {"hooks": [_o(3)]}, {"hooks": [_tf("/old")]}]
    got, warnings = setup_cmd._merge_event(arr, NEW, "Stop", "Codex hooks.json", False)
    assert got == [{"hooks": [_o(1)]}, NEW, {"hooks": [_o(2)]}, {"hooks": [_tf("/old")]}, {"hooks": [_o(3)]}]
    (w,) = warnings
    assert w.startswith("Codex hooks.json 的 Stop：第 4 组是重复的 teamflow hook，这一端不认空组")


def test_empty_group_ok_both_clients():
    # 两端都确认过空组合法（见 setup_cmd.EMPTY_GROUP_OK 的注释）；改成 False 要同时改这里
    assert setup_cmd.EMPTY_GROUP_OK == {"claude": True, "codex": True}


def _doctor(env, home, tmp_path):
    d = tmp_path / "fakebin"
    d.mkdir(exist_ok=True)
    for n in ("bwrap", "socat"):
        (d / n).write_text("#!/bin/sh\nexit 0\n")
        (d / n).chmod(0o755)
    sh = tmp_path / "quiet.sh"
    sh.write_text("#!/bin/sh\nexit 0\n")
    sh.chmod(0o755)
    return env.run(["doctor", "--home", home, "--bin", BIN], PATH=str(d) + ":/usr/bin:/bin", SHELL=str(sh))


def test_doctor_accepts_mixed_group_and_placeholder(env, tmp_path):
    home = env.home
    _setup(env, home)
    _rewrite(home, lambda c, ev, arr: [{"hooks": []}, {**arr[0], "hooks": [_foreign(c, "x"), arr[0]["hooks"][0]]},
                                       _fgroup(c, "z")])
    p = _doctor(env, home, tmp_path)
    out = p.stdout.decode()
    assert p.returncode == 0, out
    assert "通过  Codex SessionStart hook" in out and "通过  Claude Code Stop hook" in out


def test_doctor_flags_same_group_duplicates_and_matcher(env, tmp_path):
    home = env.home
    _setup(env, home)
    path = _paths(home)["codex"]
    hj = _load(path)
    tf = hj["hooks"]["Stop"][0]["hooks"][0]
    hj["hooks"]["Stop"][0]["hooks"] = [tf, dict(tf)]
    ss = hj["hooks"]["SessionStart"][0]["hooks"][0]
    hj["hooks"]["SessionStart"] = [{"matcher": "startup", "hooks": [_foreign("codex", "x"), ss]}]
    _save(path, hj)
    out = _doctor(env, home, tmp_path).stdout.decode()
    assert "失败  Codex Stop hook" in out and "同一组里有 2 条 teamflow hook" in out
    assert "失败  Codex SessionStart hook matcher" in out
