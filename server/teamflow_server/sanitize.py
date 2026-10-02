"""清洗与扫描（M0 最小版）。

完整规则见 plan 8.3；这里只实现原型需要的子集：
- 清洗：NFC、去不可见字符（Unicode Tags、零宽、BiDi 控制含 U+061C、变体选择符、蒙古文变体选择符 U+180E、
  组合字形连接符 U+034F、Hangul filler、U+2800、高棉文固有元音 U+17B4/17B5、已废弃的格式符 U+206A–206F、
  行间注释符 U+FFF9–FFFB、速记格式符 U+1BCA0–1BCA3、乐谱格式符 U+1D159、U+1D173–1D17A）、
  各种换行（U+2028/U+2029、NEL、VT、FF、U+001C–001E）换成 \\n、空白折叠。
- 扫描：少量高置信规则（含 Slack xox[abpr]-、Google AIza、Stripe、JWT），外加微信 AppSecret（要有
  appsecret/secret 上下文）、高熵 KEY=VALUE（白名单：commit SHA、UUID 等）和键名像密钥的 ``key: value``
  冒号写法。正文类写入命中返回 secret_detected（REST 422）；hooks 来源只遮蔽。
- 标题（plan 5.1 闸门表、I6）：所有标题一律单行；agent 写的标题更严，规则见本文件"标题"一节和 server/README.md。
"""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from typing import Callable

SANITIZER_VER = 4

_INVISIBLE = re.compile(
    "["
    "\U000E0000-\U000E007F"  # Unicode Tags
    "\u200B-\u200F"  # 零宽、LRM/RLM
    "\u2060-\u206F"  # word joiner 等、BiDi 隔离 U+2066–2069、已废弃的格式符 U+206A–206F
    "\uFEFF"
    "\u202A-\u202E"  # BiDi 嵌入/覆盖
    "\u061C"  # 阿拉伯字母标记（BiDi 控制）
    "\u180E"  # 蒙古文元音分隔符（旧版本里是零宽空白）
    "\u034F"  # 组合字形连接符（不可见）
    "\u17B4\u17B5"  # 高棉文固有元音（不可见）
    "\uFE00-\uFE0F"  # 变体选择符
    "\U000E0100-\U000E01EF"
    "\u115F\u1160\u3164\uFFA0"  # Hangul filler
    "\u2800"  # 盲文空白
    "\u00AD"  # 软连字符
    "\uFFF9-\uFFFB"  # 行间注释锚点/分隔/终止符
    "\U0001BCA0-\U0001BCA3"  # 速记格式控制符
    "\U0001D159"  # 乐谱：空音符头（不可见）
    "\U0001D173-\U0001D17A"  # 乐谱：连梁、连线、乐句等格式符
    "\u180B-\u180D\u180F"  # 蒙古文自由变体选择符（不可见，默认可忽略）
    "\u0600-\u0605\u06DD\u070F\u0890\u0891\u08E2\U000110BD\U000110CD"  # 数字前置符号等格式控制符
    "\U00013430-\U0001343F"  # 埃及象形文字格式控制符
    "]"
)


def _strip_invisible(t: str) -> str:
    """去掉不可见字符：上面列出的，再加上所有 Unicode 格式控制符（Cf）兜底。

    第三轮复审：U+180B 这类没列到的字符能把 evil.com 拆成 evil.c᠋om 绕过标题规则，也能拆开令牌躲过扫描。
    以后 Unicode 新增的格式控制符靠 Cf 兜住，不用再一个个补。"""
    t = _INVISIBLE.sub("", t)
    if not t.isascii():
        t = "".join(ch for ch in t if unicodedata.category(ch) != "Cf")
    return t
# 各种换行：CR、行分隔符、段分隔符、NEL、VT、FF、文件/组/记录分隔符，统一换成 \n 再参与空白折叠
_LINE_SEPARATORS = re.compile("\r\n|[\r\u2028\u2029\x85\x0b\x0c\x1c\x1d\x1e]")
_MANY_NL = re.compile(r"\n{3,}")
_TRAILING_WS = re.compile(r"[ \t]+$", re.M)
_FULLWIDTH_SPACES = re.compile("\u3000{2,}")


def clean(text: str | None) -> str | None:
    if text is None:
        return None
    t = unicodedata.normalize("NFC", text)
    t = _LINE_SEPARATORS.sub("\n", t)
    t = _strip_invisible(t)
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


def _secret_colon_kv(m: re.Match[str]) -> bool:
    """``key: value`` 冒号写法（YAML、JSON、HTTP 头、口头转述）：只认键名像密钥的，避免 ``branch: …`` 之类误杀。"""
    return bool(_SECRETISH_KEY.search(m.group("k"))) and _high_entropy_kv(m)


def _bearer(m: re.Match[str]) -> bool:
    v = m.group("v")
    return any(ch.isdigit() for ch in v) and any(ch.isalpha() for ch in v) and shannon_entropy(v) >= 3.0


# (规则 id, 正则, 额外判定)。正则里有命名组 v 时，位置和遮蔽都只针对 v（键名、上下文保留）。
_RULES: list[tuple[str, re.Pattern[str], Callable[[re.Match[str]], bool] | None]] = [
    ("tencent_akid", re.compile(r"\bAKID[A-Za-z0-9]{13,40}\b"), None),
    ("aws_akia", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), None),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{10,}"), None),
    ("openai_key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9]{20,}"), None),
    ("github_pat", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{22,})"), None),
    ("slack_token", re.compile(r"\bxox[abpr]-[A-Za-z0-9\-]{10,}"), None),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}"), None),
    ("stripe_key", re.compile(r"\b[rsp]k_(?:live|test)_[A-Za-z0-9]{16,}"), None),
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
    # 冒号写法：token: value、"secret": "value"、api_key：value（全角冒号）。只认键名像密钥的
    (
        "high_entropy_kv",
        re.compile(
            r"(?<![A-Za-z0-9_])(?P<k>[A-Za-z_][A-Za-z0-9_.\-]{0,63})[\"']?[ \t]*[:：][ \t]*[\"']?"
            r"(?P<v>[A-Za-z0-9+/_\-.]{16,}={0,2})"
        ),
        _secret_colon_kv,
    ),
    ("bearer_token", re.compile(r"(?i)\bbearer[ \t]+(?P<v>[A-Za-z0-9._~+/\-]{20,}=*)"), _bearer),
    # JWT：三段 base64url，头部固定以 eyJ（'{"'）开头
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{16,}"), None),
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
# 标题（plan 5.1 闸门表、I6：团队档下标题是唯一不经接受就跨人送到 agent 的自由文本）
#
# 所有标题一律单行：人写的标题把换行（含 U+2028/2029、NEL 等）折成空格；agent 写的标题带换行直接 422。
#
# agent 写的标题，先算"检查用骨架"再匹配：NFKC（全角 ｈｔｔｐｓ：／／ → https://）→ 把形似 / \ : ~ | 的字符
# 折回 ASCII（∕ ⁄ ⧸ ╱ → /，∖ ⧵ → \，∶ ꞉ → :，〜 ∼ → ~，∣ │ → |）→ 去掉组合附加符号和不可见字符。
# 只用骨架判定，存的仍是清洗后的原文（不把中文全角标点改成半角）。命中下面任一条就拒绝：
#
# - multiline 换行。
# - url 网址或域名：任何 scheme://（含 https:\\、hxxp://），常见 scheme 的变体（https: //、http:/x），
#   javascript:、data:mime/，www.，行首或空白后的 //host，localhost:端口，IPv4 带端口或路径，
#   以及**裸域名**：ASCII 标签 + 常见顶级域（com net org cn io ai co me tv xyz top icu club shop site website
#   tech biz mobi gov edu ru uk jp kr hk tw sg de fr eu au ca tk ga cf gq example localhost onion xn--…），
#   标签之间可以是 . 或 。；中文顶级域（中国 公司 网络 在线 …）的标签可以是中文。
#   与文件扩展名、代码写法冲突的后缀（md py sh rs dev app zip cc info in …）不算裸域名，
#   只在后面紧跟 / 或 :端口 时才算（evil.sh/x、foo.dev:8080）。点开头的文件名（.env.example）不算域名。
#   白名单：asp.net、ado.net、vb.net、system.net、socket.io。
# - home_path ~/ 或 ~user/ 开头的路径；env_path $VAR/；env_var %VAR%、$env:VAR。
# - abs_path 绝对路径：行首或空白、标点后的 /x；任意位置的 /etc /root /tmp /var /usr /proc /sys /opt /boot
#   /mnt /srv 和 /home/ /Users/ /Library/ 等系统目录；C:\ 与 C:/；\\server。
# - dot_path 相对的点目录路径：.aws/、.ssh/、.config/、./、../（点目录后面要跟 / 或 \）。
# - pipe_or_redirect：管道 |；重定向 >>、2>、&>、>&、>|、>(、<<、<(、<&，以及 > 或 < 后面紧跟路径、~、$VAR、
#   %VAR% 或文件名（out.txt、.env）；<字母（像标签）。"p95 > 300ms"、"错误率 < 1%" 这类比较放行，
#   箭头 -> => 也放行。
# - backtick 反引号；command_subst $( 或 ${。
#
# 不拦：不含斜杠的单个文件名（report.md、install.sh、.env），版本号（1.2.3），比较（>、<、>=）。
# ---------------------------------------------------------------------------

_LINE_BREAK = re.compile("[\n\r\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029]")
_SPACES = re.compile("[ \t]+")


def one_line(text: str | None) -> str | None:
    """标题一律单行：所有换行（\\n、\\r、U+2028/2029、NEL、VT、FF…）折成空格，连续的空格和制表符折成一个。"""
    if text is None:
        return None
    return _SPACES.sub(" ", _LINE_BREAK.sub(" ", text)).strip()


_CONFUSABLE = str.maketrans(
    {
        # 斜杠：除号斜杠、分数斜杠、大斜杠、制表符斜线、数学斜线、菲律宾文标点
        "\u2215": "/",
        "\u2044": "/",
        "\u29F8": "/",
        "\u2571": "/",
        "\u27CB": "/",
        "\u1735": "/",
        # 反斜杠
        "\u2216": "\\",
        "\u29F5": "\\",
        "\u29F9": "\\",
        "\u2572": "\\",
        "\u27CD": "\\",
        # 冒号
        "\u2236": ":",
        "\uA789": ":",
        "\u02F8": ":",
        "\u05C3": ":",
        "\u205A": ":",
        "\u0589": ":",
        # 波浪号
        "\u301C": "~",
        "\u223C": "~",
        "\u2053": "~",
        # 竖线
        "\u2223": "|",
        "\u01C0": "|",
        "\u05C0": "|",
        "\u2502": "|",
    }
)


def title_skeleton(text: str) -> tuple[str, list[int]]:
    """检查用骨架：逐字 NFKC → 形似字符折回 ASCII → 去组合附加符号和不可见字符。

    返回 (骨架, 下标表)：骨架第 k 个字符来自原文第 idx[k] 个字符，命中位置据此报回原文。
    """
    out: list[str] = []
    idx: list[int] = []
    for i, ch in enumerate(text):
        if ch.isascii():
            s = ch
        else:
            s = unicodedata.normalize("NFKC", ch).translate(_CONFUSABLE)
            s = "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))
            s = _strip_invisible(s)
        out.append(s)
        idx.extend([i] * len(s))
    idx.append(len(text))
    return "".join(out), idx


_PATH_LEAD = r"(?<![^\s\"'`(\[{<（【「『=:：,，;；])"  # 行首，或前面是空白/引号/括号/标点
_DOM_START = r"(?<![A-Za-z0-9\-])(?:(?<!\.)|(?<=\.\.))"  # 前面不是字母数字；单个 . 开头的是点文件名，不算
_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?"
_TLD_BARE = (
    r"com|net|org|cn|io|ai|co|me|tv|xyz|top|icu|club|shop|site|website|tech|biz|mobi|gov|edu"
    r"|ru|uk|jp|kr|hk|tw|sg|de|fr|eu|au|ca|tk|ga|cf|gq|example|localhost|onion|xn--[a-z0-9\-]+"
)
# 与文件扩展名或代码写法冲突的后缀：只在后面紧跟 / 或 :端口 时才算网址
_TLD_PATH = _TLD_BARE + r"|dev|app|sh|zip|cc|info|link|live|cloud|store|online|vip|work|fun|ink|wang|ltd|space"
_TLD_CJK = (
    "中国|中國|公司|网络|網絡|网址|网站|网店|在线|商城|商店|中文网|集团|移动|手机|我爱你|香港|台湾|台灣|新加坡"
    "|信息|购物|游戏|企业|娱乐|时尚|微博|商标|慈善|政务|公益|广东|佛山"
)
_DOMAIN_ALLOW = {"asp.net", "ado.net", "vb.net", "system.net", "socket.io"}

# 重定向目标：路径、~、$VAR、%VAR%、./、../、盘符，或像文件名的词（out.txt、.env）
_FILEISH = r"(?:\.?[A-Za-z0-9_\-]+\.[A-Za-z][A-Za-z0-9]{0,9}(?![A-Za-z0-9])|\.[A-Za-z_][A-Za-z0-9_.\-]*)"
_REDIR_TARGET = r"(?:[~/\\]|\$[A-Za-z_{(]|%[A-Za-z_]|\.{1,2}[/\\]|[A-Za-z]:[\\/]|" + _FILEISH + ")"

_TitlePred = Callable[[re.Match[str]], bool] | None


def _not_allowed_domain(m: re.Match[str]) -> bool:
    return m.group(0).replace("\u3002", ".").lower() not in _DOMAIN_ALLOW


_TITLE_RULES: list[tuple[str, str, re.Pattern[str], _TitlePred]] = [
    ("multiline", "换行（标题只能一行）", _LINE_BREAK, None),
    (
        "url",
        "网址或域名",
        re.compile(
            r"[A-Za-z][A-Za-z0-9+.\-]*:[/\\]{2}"  # 任何 scheme://（含 https:\\）
            r"|(?i:(?<![A-Za-z0-9])(?:https?|hxxps?|ftps?|sftp|wss?|file|ssh|git|svn|smb)\s*:\s*[/\\])"  # https: //、http:/x
            r"|(?i:(?<![A-Za-z0-9])(?:javascript|vbscript):(?=[A-Za-z(/])|(?<![A-Za-z0-9])data:[a-z]+/[a-z0-9.+\-]+[;,])"
            r"|(?i:(?<![A-Za-z0-9])www[.\u3002][A-Za-z0-9\-])"  # www.
            r"|" + _PATH_LEAD + r"//[A-Za-z0-9]"  # 协议相对 //host
            r"|(?i:(?<![A-Za-z0-9\-.])localhost(?::\d|/))"
            r"|(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?::\d{1,5}(?!\d)|/)"  # IPv4 带端口或路径
        ),
        None,
    ),
    (
        "url",
        "网址或域名",
        re.compile(  # 裸域名：常见顶级域，标签之间是 . 或 。
            r"(?i:" + _DOM_START + r"(?:" + _LABEL + r"[.\u3002])+(?:" + _TLD_BARE + r")"
            r"(?![A-Za-z0-9\-]|[.\u3002][A-Za-z0-9]))"
        ),
        _not_allowed_domain,
    ),
    (
        "url",
        "网址或域名",
        re.compile(  # 域名后面跟 / 或 :端口（后缀范围更宽）
            r"(?i:" + _DOM_START + r"(?:" + _LABEL + r"[.\u3002])+(?:" + _TLD_PATH + r")(?::\d{1,5}(?!\d)|[/\\]))"
        ),
        None,
    ),
    ("url", "网址或域名", re.compile(r"(?<![\w\-.])(?:[\w\-]+\.)+(?:" + _TLD_CJK + ")"), None),  # 中文顶级域
    ("home_path", "~/ 开头的路径", re.compile(r"~[A-Za-z0-9_.\-]*[/\\]"), None),
    ("env_path", "环境变量路径（$VAR/）", re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*[/\\]"), None),
    ("env_var", "环境变量（%VAR% 或 $env:VAR）", re.compile(r"%[A-Za-z_][A-Za-z0-9_()]*%|(?i:\$env:[A-Za-z_])"), None),
    (
        "abs_path",
        "绝对路径",
        re.compile(
            _PATH_LEAD + r"/[A-Za-z0-9._~\-]"
            r"|(?<![A-Za-z0-9._\-~])/(?:etc|root|tmp|var|usr|proc|sys|opt|boot|mnt|srv)(?![A-Za-z0-9_\-])"
            r"|(?<![A-Za-z0-9._\-~])/(?:home|Users|Library|Volumes|private|System|Applications|dev|run|lib|bin|sbin)/"
            r"|(?<![A-Za-z0-9])[A-Za-z]:[\\/]"  # C:\ 与 C:/
            r"|(?<!\\)\\\\[A-Za-z0-9.$?]"  # \\server\share
        ),
        None,
    ),
    (
        "dot_path",
        "点目录路径（.aws/、.ssh/、../）",
        re.compile(r"(?<![A-Za-z0-9_\-])\.[A-Za-z0-9_][A-Za-z0-9_.\-]*[/\\]|(?<![A-Za-z0-9_.\-])\.{1,2}[/\\]"),
        None,
    ),
    (
        "pipe_or_redirect",
        "管道或重定向（| >> 2> > 文件）",
        re.compile(
            r"\|"
            r"|>>|(?<![A-Za-z0-9_.])[0-9]>|&>|>&|>\||>\("
            r"|(?<![-=])>\s*" + _REDIR_TARGET  # 箭头 -> => 不算
            + r"|<<|<\(|<&|<[A-Za-z!/?]"
            r"|<\s*" + _REDIR_TARGET
        ),
        None,
    ),
    ("backtick", "反引号", re.compile(r"`"), None),
    ("command_subst", "命令替换（$( 或 ${）", re.compile(r"\$[({]"), None),
]


@dataclass(frozen=True)
class TitleHit:
    rule: str
    desc: str
    pos: int


def unsafe_title(text: str | None) -> TitleHit | None:
    """agent 来源的标题里有没有换行、网址、路径或命令片段。在 NFKC 骨架上匹配，返回原文里最靠前的一处命中。"""
    if not text:
        return None
    sk, idx = title_skeleton(text)
    best: TitleHit | None = None
    for rule, desc, pat, pred in _TITLE_RULES:
        for m in pat.finditer(sk):
            if pred is None or pred(m):
                pos = idx[m.start()]
                if best is None or pos < best.pos:
                    best = TitleHit(rule, desc, pos)
                break
    return best


_IDENT = re.compile(r"^[A-Za-z0-9._/@:-]{1,80}$")


def ident_or_hash(value: str | None) -> str | None:
    """标识类字段（分支名、仓库、会话 ID）：不匹配白名单正则的只存哈希。"""
    if value is None or value == "":
        return None
    if _IDENT.match(value):
        return value
    return "h:" + sha256(value)[:12]
