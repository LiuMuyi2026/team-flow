"""清洗与扫描（M0 最小版）。

完整规则见 plan 8.3；这里只实现原型需要的子集：
- 清洗：NFC、去不可见字符（Unicode Tags、零宽、BiDi 控制含 U+061C、变体选择符、蒙古文变体选择符 U+180E、
  组合字形连接符 U+034F、Hangul filler、U+2800）、行/段分隔符 U+2028/U+2029 换成换行、空白折叠。
- 扫描：少量高置信规则，外加微信 AppSecret（要有 appsecret/secret 上下文）和高熵 KEY=VALUE（白名单：
  commit SHA、UUID 等）。正文类写入命中返回 secret_detected（REST 422）；hooks 来源只遮蔽。
- agent 写的标题更严（plan 5.1 闸门表）：不许有网址、~/、绝对路径、管道或重定向符、反引号、$( / ${。
"""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from typing import Callable

SANITIZER_VER = 2

_INVISIBLE = re.compile(
    "["
    "\U000E0000-\U000E007F"  # Unicode Tags
    "\u200B-\u200F"  # 零宽、LRM/RLM
    "\u2060-\u2064"  # word joiner 等
    "\uFEFF"
    "\u202A-\u202E"  # BiDi 嵌入/覆盖
    "\u2066-\u2069"  # BiDi 隔离
    "\u061C"  # 阿拉伯字母标记（BiDi 控制）
    "\u180E"  # 蒙古文元音分隔符（旧版本里是零宽空白）
    "\u034F"  # 组合字形连接符（不可见）
    "\uFE00-\uFE0F"  # 变体选择符
    "\U000E0100-\U000E01EF"
    "\u115F\u1160\u3164\uFFA0"  # Hangul filler
    "\u2800"  # 盲文空白
    "\u00AD"  # 软连字符
    "]"
)
_LINE_SEPARATORS = re.compile("[\u2028\u2029]")  # 行分隔符、段分隔符：换成普通换行，再参与空白折叠
_MANY_NL = re.compile(r"\n{3,}")
_TRAILING_WS = re.compile(r"[ \t]+$", re.M)
_FULLWIDTH_SPACES = re.compile("\u3000{2,}")


def clean(text: str | None) -> str | None:
    if text is None:
        return None
    t = unicodedata.normalize("NFC", text)
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = _LINE_SEPARATORS.sub("\n", t)
    t = _INVISIBLE.sub("", t)
    t = _TRAILING_WS.sub("", t)
    t = _MANY_NL.sub("\n\n", t)
    t = _FULLWIDTH_SPACES.sub("\u3000", t)
    return t.strip()


def sha256(text: str | None) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Hit:
    rule: str
    pos: int


# ---------------------------------------------------------------------------
# 扫描规则
# ---------------------------------------------------------------------------

_HEX = re.compile(r"^[0-9a-fA-F]+$")
_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_SYSTEM_ID = re.compile(r"^[TB]-\d{1,6}$")
_SECRETISH_KEY = re.compile(r"(?i)key|secret|token|passw|pwd|auth|credential|private|signature|access")


def shannon_entropy(s: str) -> float:
    """每个字符的香农熵（bit）。随机 base64 约 4.5–5.5，英文单词约 3–3.5，十六进制最多 4。"""
    if not s:
        return 0.0
    n = len(s)
    return -sum(c / n * math.log2(c / n) for c in Counter(s).values())


def _high_entropy_kv(m: re.Match[str]) -> bool:
    """KEY=VALUE 里的 VALUE 是不是像密钥。白名单：UUID（键名不像密钥时）、commit SHA 与其他纯十六进制摘要
    （键名不像密钥时）、本系统 ID。"""
    key, value = m.group("k"), m.group("v").rstrip("=")
    secretish = bool(_SECRETISH_KEY.search(key))
    if _SYSTEM_ID.match(value):
        return False
    if _UUID.match(value):
        return secretish
    if _HEX.match(value):
        # commit SHA（7–40）、sha256 摘要等纯十六进制：只有键名像密钥、且至少 128 bit 时才算
        return secretish and len(value) >= 32
    if len(value) < 20 or value.startswith(("/", ".")):  # 路径、相对路径
        return False
    has_digit = any(ch.isdigit() for ch in value)
    has_upper = any(ch.isupper() for ch in value)
    has_lower = any(ch.islower() for ch in value)
    if secretish:
        # 键名像密钥：字母数字混排、熵不太低就算
        return has_digit and (has_upper or has_lower) and shannon_entropy(value) >= 3.0
    # 键名普通：随机串几乎都是大小写加数字混排；全小写的（路径、snake_case 配置值）不算
    return has_digit and has_upper and has_lower and shannon_entropy(value) >= 3.5


# (规则 id, 正则, 额外判定)。正则里有命名组 v 时，位置和遮蔽都只针对 v（键名、上下文保留）。
_RULES: list[tuple[str, re.Pattern[str], Callable[[re.Match[str]], bool] | None]] = [
    ("tencent_akid", re.compile(r"\bAKID[A-Za-z0-9]{13,40}\b"), None),
    ("aws_akia", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), None),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{10,}"), None),
    ("openai_key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9]{20,}"), None),
    ("github_pat", re.compile(r"\b(?:ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{22,})"), None),
    ("teamflow_pat", re.compile(r"\btf_pat_[A-Za-z0-9_]{6,}"), None),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), None),
    ("db_url_password", re.compile(r"\b[a-z][a-z0-9+]*://[^\s:/@]+:[^\s@/]+@[^\s/]+"), None),
    # 微信 AppSecret：32 位十六进制，前面 24 个字符以内要有 appsecret / app_secret / secret 字样
    (
        "wechat_appsecret",
        re.compile(r"(?i)(?:app[\s_\-]?secret|secret).{0,24}?(?<![0-9a-f])(?P<v>[0-9a-f]{32})(?![0-9a-f])"),
        None,
    ),
    # 高熵 KEY=VALUE（环境变量、配置行、URL 查询串里的 token=…）
    (
        "high_entropy_kv",
        re.compile(r"(?<![A-Za-z0-9_])(?P<k>[A-Za-z_][A-Za-z0-9_.\-]{0,63})\s?=\s?[\"']?(?P<v>[A-Za-z0-9+/_\-.]{16,}={0,2})"),
        _high_entropy_kv,
    ),
    ("cn_mobile", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), None),
    ("cn_id_card", re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"), None),
]
_ALLOW = {"13800138000"}


def _span(m: re.Match[str]) -> tuple[int, int]:
    if "v" in m.re.groupindex:
        return m.start("v"), m.end("v")
    return m.start(), m.end()


def _is_hit(m: re.Match[str], pred: Callable[[re.Match[str]], bool] | None) -> bool:
    s, e = _span(m)
    if m.string[s:e] in _ALLOW:
        return False
    return pred is None or pred(m)


def scan(text: str | None) -> Hit | None:
    if not text:
        return None
    for rule, pat, pred in _RULES:
        for m in pat.finditer(text):
            if _is_hit(m, pred):
                return Hit(rule, _span(m)[0])
    return None


def mask(text: str) -> tuple[str, list[str]]:
    """hooks 来源：命中就地遮蔽为「[已遮蔽:规则]」，不拒绝。有命名组 v 的规则只遮蔽值。"""
    rules: list[str] = []
    out = text
    for rule, pat, pred in _RULES:

        def _sub(m: re.Match[str], rule: str = rule, pred: Callable[[re.Match[str]], bool] | None = pred) -> str:
            if not _is_hit(m, pred):
                return m.group(0)
            rules.append(rule)
            s, e = _span(m)
            whole = m.group(0)
            return whole[: s - m.start()] + f"[已遮蔽:{rule}]" + whole[e - m.start() :]

        out = pat.sub(_sub, out)
    return out, rules


# ---------------------------------------------------------------------------
# agent 写的标题（plan 5.1 闸门表：标题是团队档下唯一不经接受就跨人送到 agent 的自由文本）
# ---------------------------------------------------------------------------

_PATH_LEAD = r"(?<![^\s\"'`(\[{<（【「『=:：,，;；])"  # 行首，或前面是空白/引号/括号/标点
_TITLE_RULES: list[tuple[str, str, re.Pattern[str]]] = [
    (
        "url",
        "网址",
        re.compile(
            r"[A-Za-z][A-Za-z0-9+.\-]*://"  # 任何 scheme://
            r"|(?i:(?<![A-Za-z0-9])www\.[A-Za-z0-9\-]+\.)"  # www.
            r"|" + _PATH_LEAD + r"//[A-Za-z0-9]"  # 协议相对 //host
            # 不带 scheme 的「域名/路径」，只认常见顶级域，避免把 node.js/react 这类写法当网址
            + r"|(?i:(?<![A-Za-z0-9\-.])[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*"
            r"\.(?:com|net|org|io|cn|dev|sh|xyz|example|app|ai|co|me|info|top|site|cc|ru|tk|link|zip)(?::\d+)?/)"
        ),
    ),
    ("home_path", "~/ 开头的路径", re.compile(r"~[A-Za-z0-9_.\-]*[/\\]")),
    ("env_path", "环境变量路径", re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*[/\\]")),
    (
        "abs_path",
        "绝对路径",
        re.compile(_PATH_LEAD + r"/[A-Za-z0-9._~\-]" + r"|(?<![A-Za-z0-9])[A-Za-z]:\\" + r"|" + _PATH_LEAD + r"\\\\[A-Za-z0-9]"),
    ),
    ("pipe_or_redirect", "管道或重定向符（| > <）", re.compile(r"[|<>]")),
    ("backtick", "反引号", re.compile(r"`")),
    ("command_subst", "命令替换（$( 或 ${）", re.compile(r"\$[({]")),
]


@dataclass(frozen=True)
class TitleHit:
    rule: str
    desc: str
    pos: int


def unsafe_title(text: str | None) -> TitleHit | None:
    """agent 来源的标题里有没有网址、路径或命令片段。返回第一处命中（按位置）。"""
    if not text:
        return None
    best: TitleHit | None = None
    for rule, desc, pat in _TITLE_RULES:
        m = pat.search(text)
        if m and (best is None or m.start() < best.pos):
            best = TitleHit(rule, desc, m.start())
    return best


_IDENT = re.compile(r"^[A-Za-z0-9._/@:-]{1,80}$")


def ident_or_hash(value: str | None) -> str | None:
    """标识类字段（分支名、仓库、会话 ID）：不匹配白名单正则的只存哈希。"""
    if value is None or value == "":
        return None
    if _IDENT.match(value):
        return value
    return "h:" + sha256(value)[:12]
