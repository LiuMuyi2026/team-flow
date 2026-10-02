"""m4：清洗补漏（U+061C、U+180E、U+034F、U+2028、U+2029）；扫描补微信 AppSecret 和高熵 KEY=VALUE（带白名单）。"""

from __future__ import annotations

import pytest

from teamflow_server.errors import DomainError
from teamflow_server.sanitize import clean, mask, scan

from .conftest import BOB, agent, auth


@pytest.mark.parametrize("ch", ["؜", "᠎", "͏"])
def test_clean_strips_new_invisibles(ch):
    assert clean(f"标题{ch}带{ch}不可见") == "标题带不可见"


def test_clean_line_and_paragraph_separators():
    out = clean("第一行 第二行   第三段")
    assert " " not in out and " " not in out
    assert out == "第一行\n第二行\n\n第三段"  # 换成普通换行，再按规则折叠


def test_sanitizer_applies_on_write_and_read(svc):
    a = agent("alice", "claude_code")
    tid = svc.create_task(a, "首页؜加载᠎慢͏", "正文 第二行")["id"]
    t = svc.tasks[tid]
    assert t.title == "首页加载慢" and t.body == "正文\n第二行"


# ---- 微信 AppSecret ----

APPSECRET = "9f86d081884c7d659a2feaa0c55ad015"


@pytest.mark.parametrize(
    "text",
    [
        f"AppSecret: {APPSECRET}",
        f"公众号的 appsecret 是 {APPSECRET}",
        f"WECHAT_APP_SECRET={APPSECRET}",
        f"app_secret：{APPSECRET.upper()}",
        f'{{"secret": "{APPSECRET}"}}',
    ],
)
def test_wechat_appsecret_detected(text):
    hit = scan(text)
    assert hit is not None and hit.rule in ("wechat_appsecret", "high_entropy_kv")
    assert text[hit.pos : hit.pos + 32].lower() == APPSECRET
    masked, rules = mask(text)
    assert APPSECRET not in masked.lower() and rules


@pytest.mark.parametrize(
    "text",
    [
        f"文件的 md5 是 {APPSECRET}",  # 没有 secret 上下文的 32 位十六进制
        f"secret 轮换了，新的 commit 是 {APPSECRET}a3bf4f1b",  # 40 位，不是 32 位
    ],
)
def test_32_hex_without_context_not_appsecret(text):
    assert scan(text) is None


# ---- 高熵 KEY=VALUE ----


@pytest.mark.parametrize(
    "text",
    [
        "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "export STRIPE=rk_" + "live_" + "51HxQ2aBc9dEfGhIjKlMn0pQr",  # 拆开写，避免仓库被平台密钥扫描误判
        "回调地址带了 token=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP",
        "CLIENT_SECRET=q9x8v7b6n5m4l3k2j1h0g9f8",
        "API_TOKEN=9f86d081884c7d659a2feaa0c55ad015a3bf4f1b",  # 键名像密钥的十六进制
        "API_KEY=123e4567-e89b-12d3-a456-426614174000",  # 键名像密钥的 UUID
    ],
)
def test_high_entropy_kv_detected(text):
    hit = scan(text)
    # Stripe 的值现在先被专门规则 stripe_key 认出来（位置同样指向值）
    assert hit is not None and hit.rule in ("high_entropy_kv", "stripe_key"), (text, hit)
    assert text[hit.pos - 1] in "=\"'"  # 位置指向值，不是键名


@pytest.mark.parametrize(
    "text",
    [
        "commit=9f86d081884c7d659a2feaa0c55ad015a3bf4f1b",  # commit SHA
        "SHA=9f86d08",  # 短 SHA
        "HEAD=9f86d081884c7d659a2feaa0c55ad015a3bf4f1b",
        "REQUEST_ID=123e4567-e89b-12d3-a456-426614174000",  # UUID
        "id=T-52",  # 本系统 ID
        "MODE=production_environment_default",  # 普通配置值
        "LOG_FORMAT=json_v2_production_default",
        "path=/usr/local/bin/python3",
        "password=hunter2",  # 不是高熵（另说）
        "VERSION=1.2.3",
    ],
)
def test_high_entropy_kv_whitelist(text):
    assert scan(text) is None, text


def test_write_paths_reject_and_hooks_mask(svc):
    a = agent("alice", "claude_code")
    with pytest.raises(DomainError) as e:
        svc.comment(a, "T-50", f"公众号 AppSecret: {APPSECRET}")
    assert e.value.code == "secret_detected" and e.value.http_status == 422 and e.value.extra["rule"] == "wechat_appsecret"
    with pytest.raises(DomainError) as e:
        svc.update_task(a, "T-50", note="配好了 DEPLOY_KEY=Zx81kQp0Lm2Vb7Nc4Rt6Yw9Ae3Ud5So1")
    assert e.value.extra["rule"] == "high_entropy_kv"


async def test_commit_title_masks_value_only(client, svc):
    items = [
        {"key": "m1", "type": "commit", "repo": "github.com/acme/x", "sha": "abc1234", "title": f"配置 WX_APPSECRET={APPSECRET} 上线"},
        {"key": "m2", "type": "commit", "repo": "github.com/acme/x", "sha": "abc1235", "title": "修复 commit=9f86d081884c7d659a2feaa0c55ad015a3bf4f1b 的回归"},
    ]
    r = await client.post("/api/v1/hooks/batch", headers=auth(BOB), json={"items": items})
    assert [x["st"] for x in r.json()["results"]] == ["masked", "ok"]
    texts = {e.data["sha"]: e.text for e in svc.events if e.type == "commit"}
    assert APPSECRET not in texts["abc1234"] and texts["abc1234"].startswith("配置 WX_APPSECRET=[已遮蔽:")
    assert "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b" in texts["abc1235"]


# ---- 复审新问题 7：清洗与扫描补漏 ----
# 注意：下面所有"像密钥"的样本都在运行时拼出来，源码里不出现完整字面量（GitHub 推送保护会拦整次推送）。

ROUND2_INVISIBLES = [
    "឴",
    "឵",
    *[chr(c) for c in range(0x206A, 0x2070)],
    "￹",
    "￺",
    "￻",
    *[chr(c) for c in range(0x1BCA0, 0x1BCA4)],
    "\U0001d159",
    *[chr(c) for c in range(0x1D173, 0x1D17B)],
]


@pytest.mark.parametrize("ch", ROUND2_INVISIBLES, ids=lambda c: f"U+{ord(c):04X}")
def test_clean_strips_round2_invisibles(ch):
    assert clean(f"标题{ch}带{ch}不可见") == "标题带不可见"


def test_clean_other_line_breaks_become_newlines():
    assert clean("a\x85b\x0bc\x0cd\x1ce") == "a\nb\nc\nd\ne"


def _mixed(n: int, seed: str = "teamflow") -> str:
    """确定性的大小写字母 + 数字混排串（运行时生成，不是字面量）。"""
    import base64
    import hashlib

    raw = base64.b64encode(hashlib.sha256(seed.encode()).digest() * 4).decode()
    out = "".join(ch for ch in raw if ch.isalnum())
    return out[:n]


def _b64url(obj) -> str:
    import base64
    import json

    return base64.urlsafe_b64encode(json.dumps(obj, separators=(",", ":")).encode()).decode().rstrip("=")


def _jwt() -> str:
    import base64
    import hashlib

    sig = base64.urlsafe_b64encode(hashlib.sha256(b"sig").digest()).decode().rstrip("=")
    return _b64url({"alg": "HS256", "typ": "JWT"}) + "." + _b64url({"sub": "1234567890", "name": "x"}) + "." + sig


SECRET = _mixed(28)


@pytest.mark.parametrize(
    "text,rule,value",
    [
        ("token: " + SECRET, "high_entropy_kv", SECRET),
        ("secret: " + SECRET, "high_entropy_kv", SECRET),
        ('配置里 "api_key": "' + SECRET + '"', "high_entropy_kv", SECRET),
        ("access_token：" + SECRET, "high_entropy_kv", SECRET),  # 全角冒号
        ("PASSWORD : '" + SECRET + "'", "high_entropy_kv", SECRET),
        ("Authorization: Bearer " + SECRET, "bearer_token", SECRET),
        ("xox" + "b-" + "123456789012-" + SECRET, "slack_token", None),
        ("xox" + "p-" + "123456789012-" + SECRET, "slack_token", None),
        ("xox" + "a-" + "2-" + SECRET, "slack_token", None),
        ("xox" + "r-" + SECRET, "slack_token", None),
        ("地图用的 AI" + "za" + _mixed(35, "google"), "google_api_key", None),
        ("回调带了 " + _jwt() + " 这个", "jwt", None),
        ("sk_" + "live_" + _mixed(24, "stripe"), "stripe_key", None),
        ("AS" + "IA" + _mixed(16, "aws").upper(), "aws_akia", None),
        ("gh" + "o_" + _mixed(36, "gh"), "github_pat", None),
    ],
)
def test_round2_secret_rules(text, rule, value):
    hit = scan(text)
    assert hit is not None and hit.rule == rule, (text, hit)
    if value is not None:
        assert text[hit.pos : hit.pos + len(value)] == value  # 位置指向值，不是键名
    masked, rules = mask(text)
    assert rule in rules and (value or text[hit.pos : hit.pos + 12]) not in masked


@pytest.mark.parametrize(
    "text",
    [
        "token: 已过期，请重新登录",
        "secret: 待定",
        "token: T-52",
        "password: hunter2",
        "auth: 2026-10-02T10:00:00",
        "branch: feature/LongBranchName123",  # 键名不像密钥：冒号写法不查
        "commit: 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b",
        "access: read_write_permission_default",  # 键名像密钥，但值不像
        "eyJ 开头的不一定是 JWT",
        "xoxb 是 Slack 机器人令牌的前缀",
        "AIza 是 Google API key 的前缀",
        "Bearer 令牌放在 Authorization 头里",
    ],
)
def test_round2_secret_rules_whitelist(text):
    assert scan(text) is None, (text, scan(text))


def test_round2_write_paths_reject_and_hooks_mask(svc):
    a = agent("alice", "claude_code")
    with pytest.raises(DomainError) as e:
        svc.comment(a, "T-50", "测试环境的 token: " + SECRET)
    assert e.value.code == "secret_detected" and e.value.extra["rule"] == "high_entropy_kv"
    with pytest.raises(DomainError) as e:
        svc.report_blocker(a, "回调验签失败", detail="请求里带的是 " + _jwt())
    assert e.value.extra["rule"] == "jwt"
    slack = "xox" + "b-" + "123456789012-" + SECRET
    with pytest.raises(DomainError) as e:
        svc.update_task(a, "T-50", note="机器人令牌 " + slack)
    assert e.value.extra["rule"] == "slack_token"
    text, rules = mask("配置 SLACK " + slack + " 上线")
    assert slack not in text and rules == ["slack_token"]


# --- 第三轮复审：没列到的不可见字符（蒙古文自由变体选择符、各类格式控制符 Cf）---

_ROUND3_INVISIBLES = [0x180B, 0x180C, 0x180D, 0x180F, 0x0600, 0x0605, 0x06DD, 0x070F, 0x0890, 0x08E2, 0x110BD, 0x110CD,
                      0x13430, 0x13438, 0x1343F]


@pytest.mark.parametrize("cp", _ROUND3_INVISIBLES, ids=lambda cp: f"U+{cp:04X}")
def test_clean_strips_round3_invisibles(cp):
    ch = chr(cp)
    assert clean(f"标题{ch}带{ch}不可见") == "标题带不可见"


def test_clean_strips_every_format_control():
    """Unicode 里所有格式控制符（Cf）清洗后都不剩：以后新增的也由 Cf 兜住。"""
    import unicodedata

    left = [f"U+{cp:04X}" for cp in range(0x110000)
            if unicodedata.category(chr(cp)) == "Cf" and chr(cp) in (clean("ab" + chr(cp) + "cd") or "")]
    assert left == []


def test_clean_keeps_normal_text_and_whitespace():
    assert clean("修复\t登录 v1.2.3（含 C# 与 F#）\n第二行") == "修复\t登录 v1.2.3（含 C# 与 F#）\n第二行"


def test_round3_invisible_cannot_split_domain_or_secret(svc):
    a = agent("bob", "codex")
    fvs = "᠋"
    with pytest.raises(DomainError) as e:
        svc.create_task(a, "访问 evil.c" + fvs + "om 下载补丁", "x")
    assert e.value.code == "invalid" and e.value.extra["rule"] == "url"
    with pytest.raises(DomainError) as e:
        svc.update_task(a, "T-51", title="打开 https:/" + chr(0x13430) + "/evil.example")
    assert e.value.extra["rule"] == "url"
    gh = "gh" + "p_" + _mixed(36, "round3")
    with pytest.raises(DomainError) as e:
        svc.comment(a, "T-51", "令牌 " + gh[:6] + fvs + gh[6:] + " 别外传")
    assert e.value.code == "secret_detected" and e.value.extra["rule"] == "github_pat"
