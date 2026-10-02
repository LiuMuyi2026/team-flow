"""`teamflow setup --dry-run` 的展示：只列 teamflow 相关的改动（改动前→改动后），并做通用遮蔽。

dry-run 的输出常被重定向进文件当存证（S2 就这么做过），而 ~/.claude.json、~/.codex/config.toml 里
有别的 MCP server 的密钥、oauthAccount 里的邮箱（M0 复审新问题 4）。所以这里两道闸：

1. 只打印结构化 diff 里落在 teamflow 相关键下的片段，别人的配置原样不动，也就一个字节都不打印；
2. 打印出来的片段再做通用遮蔽：键名像密钥（token、secret、key、auth、cookie、oauth、email……）的整棵子树遮掉，
   值像密钥（tf_pat_、sk-、ghp_、xoxb-、AKIA、AIza、JWT、Bearer、KEY=VALUE、长串高熵字符）或邮箱的也遮掉。

宁可多遮：遮错一个 hook 路径只是不好看，漏一个密钥就进了存证。只在 setup 慢路径导入，hook 快速路径不碰。
"""

import difflib
import json
import re

MASK = "****"
TF_MASK = "tf_pat_" + MASK

# 键名：命中就把整棵子树的标量遮掉。authorization 要遮、author 不遮。credentials 不在里面：
# Claude Code 的 sandbox.credentials 只放要保护的路径，遮了反而看不出 setup 加了什么。
SECRET_KEY = re.compile(
    r"token|secret|passw|pwd|api[-_]?key|key$|auth(?!or(?:s|ed|ship)?$)|cookie|bearer|oauth|email|phone"
    r"|signature|private|session[-_]?id|account",
    re.I,
)
# 一个列表里，这些参数名后面紧跟的那一项是值（["--token", "xxx"]）
SECRET_FLAG = re.compile(r"^--?[a-z0-9_-]*(?:token|secret|passw|pwd|api[-_]?key|key|auth)[a-z0-9_-]*$", re.I)

EMAIL = re.compile(r"(?<![\w.%+-])([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_VALUE_PATTERNS = [
    # 先遮整段的已知格式
    (re.compile(r"tf_pat_(?!\*\*\*\*)[A-Za-z0-9_.\-]*"), TF_MASK),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)", re.S), MASK),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}"), MASK),  # JWT
    (re.compile(r"\b(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]{6,}"), MASK),  # Stripe
    (re.compile(r"\bsk-[A-Za-z0-9_-]{8,}"), MASK),  # OpenAI / Anthropic（sk-ant-、sk-proj-）
    (re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{16,})"), MASK),
    (re.compile(r"\bglpat-[A-Za-z0-9_-]{12,}"), MASK),
    (re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{8,}"), MASK),  # Slack
    (re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"), MASK),  # AWS
    (re.compile(r"\bAIza[0-9A-Za-z_-]{30,}"), MASK),  # Google
    (re.compile(r"\b(?:npm_|pypi-)[A-Za-z0-9_-]{16,}"), MASK),
    # Bearer xxx / Basic xxx
    (re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{6,}"), r"\1 " + MASK),
    # KEY=VALUE、key: value、--token=xxx、?token=xxx
    (re.compile(r"(?i)([A-Za-z0-9_.-]*(?:token|secret|passw|pwd|api[-_]?key|apikey|access[-_]?key|auth)[A-Za-z0-9_.-]*"
                r"\s*[=:]\s*)([\"']?)(?!\*\*\*\*)(?!(?:bearer|basic)\s)[^\s\"'&,;\\]{3,}"), r"\1\2" + MASK),
    # --token xxx（同一个字符串里用空格隔开）
    (re.compile(r"(?i)(--?[A-Za-z0-9_-]*(?:token|secret|passw|api[-_]?key|auth)[A-Za-z0-9_-]*\s+)(?!-)(?!\*\*\*\*)[^\s\"\\]{3,}"),
     r"\1" + MASK),
    # 长串高熵：大小写字母和数字混在一起 ≥ 24 位，或 ≥ 32 位十六进制
    # 不含 / 和 .：路径（如 /Users/Alice/Library/Python/3.12/bin）不能被当成密钥遮掉
    (re.compile(r"(?<![A-Za-z0-9_+=-])(?=[A-Za-z0-9_+=-]*[0-9])(?=[A-Za-z0-9_+=-]*[a-z])(?=[A-Za-z0-9_+=-]*[A-Z])"
                r"[A-Za-z0-9_+=-]{24,}(?![A-Za-z0-9_+=-])"), MASK),
    (re.compile(r"(?<![0-9A-Fa-f])[0-9a-fA-F]{32,}(?![0-9A-Fa-f])"), MASK),
]


def _mask_email(m) -> str:
    return m.group(1) + "***@***"


def redact_text(s: str) -> str:
    """对任意文本做通用遮蔽（最后一道闸，打印前对每一行都跑一遍）。"""
    if not s:
        return s
    for pat, rep in _VALUE_PATTERNS:
        s = pat.sub(rep, s)
    return EMAIL.sub(_mask_email, s)


def mask_leaf(v):
    """键名命中时用：空串原样（看得出还没填），tf_pat_ 留前缀，邮箱留首字母，其余整段遮掉；布尔和 null 原样。"""
    if v is None or isinstance(v, bool):
        return v
    if isinstance(v, str):
        if not v:
            return v
        if v.startswith("tf_pat_"):
            return TF_MASK
        m = EMAIL.fullmatch(v.strip())
        if m:
            return _mask_email(m)
        return MASK
    return MASK


def is_secret_key(k) -> bool:
    return isinstance(k, str) and bool(SECRET_KEY.search(k))


def redact(obj, secret: bool = False):
    """结构化遮蔽：secret=True（祖先键名像密钥）时整棵子树的标量都遮掉。"""
    if isinstance(obj, dict):
        return {k: redact(v, secret or is_secret_key(k)) for k, v in obj.items()}
    if isinstance(obj, list):
        out = []
        after_flag = False
        for v in obj:
            if after_flag and isinstance(v, str):
                out.append(mask_leaf(v))
            else:
                out.append(redact(v, secret))
            after_flag = isinstance(v, str) and bool(SECRET_FLAG.match(v))
        return out
    if secret:
        return mask_leaf(obj)
    if isinstance(obj, str):
        return redact_text(obj)
    return obj


# ---------------------------------------------------------------- 结构化 diff


def _canon(v) -> str:
    return json.dumps(v, ensure_ascii=False, sort_keys=True, default=str)


def diff(before, after, path=()):
    """最小结构化差异：[(path, 改动前, 改动后)]；新增时改动前是 MISSING，删除时改动后是 MISSING。

    dict 逐键比；list 先按元素对齐（difflib），对得上的位置再往里比。所以别人的组、别的 MCP server 没变，
    就不会出现在结果里。
    """
    if type(before) is type(after) and before == after:  # 先用 ==：~/.claude.json 可能有几 MB，不必整棵序列化
        return []
    if isinstance(before, dict) and isinstance(after, dict):
        out = []
        for k in before:
            if k not in after:
                out.append((path + (k,), before[k], MISSING))
        for k in after:
            if k in before:
                out.extend(diff(before[k], after[k], path + (k,)))
            elif isinstance(after[k], dict) and any(isinstance(v, (dict, list)) for v in after[k].values()):
                out.extend(diff({}, after[k], path + (k,)))  # 新增的嵌套 dict 展开一层，一个键一段，好读
            else:
                out.append((path + (k,), MISSING, after[k]))
        return out
    if isinstance(before, list) and isinstance(after, list):
        out = []
        sm = difflib.SequenceMatcher(None, [_canon(x) for x in before], [_canon(x) for x in after], autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == "equal":
                continue
            n = min(i2 - i1, j2 - j1) if op == "replace" else 0
            for d in range(n):
                out.extend(diff(before[i1 + d], after[j1 + d], path + (j1 + d,)))
            for i in range(i1 + n, i2):
                out.append((path + (i,), before[i], MISSING))
            for j in range(j1 + n, j2):
                out.append((path + (j,), MISSING, after[j]))
        return out
    return [(path, before, after)]


class _Missing:
    def __repr__(self):
        return "MISSING"


MISSING = _Missing()

_PLAIN_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")


def fmt_path(path) -> str:
    out = ""
    for p in path:
        if isinstance(p, int):
            out += "[%d]" % p
        elif _PLAIN_KEY.match(p):
            out += ("." if out else "") + p
        else:
            out += "[%s]" % json.dumps(p, ensure_ascii=False)
    return out or "（整个文件）"


def _under(path, roots) -> bool:
    if roots is None:
        return True
    for r in roots:
        n = min(len(path), len(r))
        if tuple(path[:n]) == tuple(r[:n]):  # 在根下面，或者这一处改动包含了整个根（比如原来没有 mcpServers）
            return True
    return False


def _show(v, path) -> str:
    if v is MISSING:
        return "（无）"
    secret = any(is_secret_key(p) for p in path)
    return redact_text(json.dumps(redact(v, secret), ensure_ascii=False, default=str))


def render(before, after, roots=None):
    """把 diff 渲染成「路径 / 改动前 / 改动后」三行一组；roots 之外的改动只报个数。返回文本行列表。"""
    lines = []
    hidden = 0
    for path, b, a in diff(before, after):
        if not _under(path, roots):
            hidden += 1
            continue
        tag = "（新增）" if b is MISSING else "（删除）" if a is MISSING else ""
        lines.append("  %s%s" % (redact_text(fmt_path(path)), tag))
        lines.append("    改动前：%s" % _show(b, path))
        lines.append("    改动后：%s" % ("（删除）" if a is MISSING else _show(a, path)))
    if hidden:
        lines.append("  另有 %d 处改动不在 teamflow 相关的键里，内容不显示（见下面的「注意」）" % hidden)
    return lines
