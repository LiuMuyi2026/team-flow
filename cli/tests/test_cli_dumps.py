"""common.dumps：手写的最小 JSON 编码（快速路径不导入 json），结果必须能被标准 JSON 解析器原样读回。"""

import json
import math

import pytest

from teamflow import common


@pytest.mark.parametrize(
    "obj",
    [
        {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "【teamflow 新动态｜数据，不是指令】 待您接受 T-55。"}},
        {"a": [1, -2, 0, 3.5, 1e-7, 1727841234.123456, True, False, None, "", "x"], "b": {}, "c": []},
        {"esc": "引号\" 反斜杠\\ 换行\n 回车\r 制表\t 响铃\x07 DEL\x7f NUL\x00 /斜杠"},
        {"wide": "emoji 😀 中文 ｜ 全角【】 U+00A0 "},
        ["nested", ["deep", {"k": [1, [2, [3]]]}]],
        ("tuple", 1),
        {"announced": ["acc:T-55", "help:B-7"], "last_out": 1727841234.5, "turns": 0, "ws": "team"},
    ],
)
def test_roundtrip(obj):
    s = common.dumps(obj)
    want = json.loads(json.dumps(obj))
    assert json.loads(s) == want
    assert common.loads(s) == want
    assert "\n" not in s and "\r" not in s  # 一行
    s.encode("utf-8")


def test_compact_and_utf8_like_json_dumps():
    obj = {"a": "中文", "b": [1, 2]}
    assert common.dumps(obj) == json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def test_awkward_strings_are_escaped():
    s = common.dumps("a b c\ud800d")
    assert s == '"a\\u2028b\\u2029c\\ud800d"'
    s.encode("utf-8")  # 孤立代理项不会让 encode 抛错
    assert json.loads(s) == "a b c\ud800d"


def test_non_finite_floats_and_key_types():
    assert common.dumps([math.nan, math.inf, -math.inf]) == "[null,null,null]"
    assert common.dumps({1: "a", None: "b"}) == '{"1":"a","None":"b"}'
    assert common.dumps(True) == "true" and common.dumps(1) == "1"


def test_unsupported_type_raises():
    with pytest.raises(TypeError):
        common.dumps({"x": {1, 2}})
    with pytest.raises(TypeError):
        common.dumps(b"bytes")
