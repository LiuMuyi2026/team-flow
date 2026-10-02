"""清洗与扫描（M0 最小版）。

完整规则见 plan 8.3；这里只实现原型需要的子集：
- 清洗：NFC、去不可见字符（Unicode Tags、零宽、BiDi 控制、变体选择符、Hangul filler、U+2800）、空白折叠。
- 扫描：少量高置信规则。正文类写入命中返回 secret_detected（REST 422）；hooks 来源只遮蔽。
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass

SANITIZER_VER = 1

_INVISIBLE = re.compile(
    "["
    "\U000E0000-\U000E007F"  # Unicode Tags
    "\u200B-\u200F"  # 零宽、LRM/RLM
    "\u2060-\u2064"  # word joiner 等
    "\uFEFF"
    "\u202A-\u202E"  # BiDi 嵌入/覆盖
    "\u2066-\u2069"  # BiDi 隔离
    "\uFE00-\uFE0F"  # 变体选择符
    "\U000E0100-\U000E01EF"
    "\u115F\u1160\u3164\uFFA0"  # Hangul filler
    "\u2800"  # 盲文空白
    "\u00AD"  # 软连字符
    "]"
)
_MANY_NL = re.compile(r"\n{3,}")
_TRAILING_WS = re.compile(r"[ \t]+$", re.M)
_FULLWIDTH_SPACES = re.compile("\u3000{2,}")


def clean(text: str | None) -> str | None:
    if text is None:
        return None
    t = unicodedata.normalize("NFC", text)
    t = t.replace("\r\n", "\n").replace("\r", "\n")
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


_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("tencent_akid", re.compile(r"\bAKID[A-Za-z0-9]{13,40}\b")),
    ("aws_akia", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{10,}")),
    ("openai_key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9]{20,}")),
    ("github_pat", re.compile(r"\b(?:ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{22,})")),
    ("teamflow_pat", re.compile(r"\btf_pat_[A-Za-z0-9_]{6,}")),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("db_url_password", re.compile(r"\b[a-z][a-z0-9+]*://[^\s:/@]+:[^\s@/]+@[^\s/]+")),
    ("cn_mobile", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
    ("cn_id_card", re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")),
]
_ALLOW = {"13800138000"}


def scan(text: str | None) -> Hit | None:
    if not text:
        return None
    for rule, pat in _RULES:
        for m in pat.finditer(text):
            if m.group(0) in _ALLOW:
                continue
            return Hit(rule, m.start())
    return None


def mask(text: str) -> tuple[str, list[str]]:
    """hooks 来源：命中就地遮蔽为「[已遮蔽:规则]」，不拒绝。"""
    rules: list[str] = []
    out = text
    for rule, pat in _RULES:
        def _sub(m: re.Match[str], rule: str = rule) -> str:
            if m.group(0) in _ALLOW:
                return m.group(0)
            rules.append(rule)
            return f"[已遮蔽:{rule}]"

        out = pat.sub(_sub, out)
    return out, rules


_IDENT = re.compile(r"^[A-Za-z0-9._/@:-]{1,80}$")


def ident_or_hash(value: str | None) -> str | None:
    """标识类字段（分支名、仓库、会话 ID）：不匹配白名单正则的只存哈希。"""
    if value is None or value == "":
        return None
    if _IDENT.match(value):
        return value
    return "h:" + sha256(value)[:12]
