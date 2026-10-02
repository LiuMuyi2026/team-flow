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
    assert hit is not None and hit.rule == "high_entropy_kv", (text, hit)
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
