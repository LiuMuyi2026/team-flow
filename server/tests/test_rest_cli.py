"""跨包约定：CLI 兜底命令走的三个 REST 端点（MCP 不可用时，plan 6.8 / instructions 里的 teamflow note / done）。

- POST /api/v1/tasks/{id}:note {"note": "..."}
- POST /api/v1/tasks/{id}:done {"note": "..."}
- POST /api/v1/blockers {"title", "detail?", "tried?", "task?", "need?"}
鉴权同其他 REST（Bearer PAT + X-Teamflow-Client）；成功返回 {id, st}，失败返回带错误码的 4xx JSON
{"error": "<code>", "message": "..."}。
"""

from __future__ import annotations

import pytest

from .conftest import ALICE, BOB, read_log


def h(token: str, client: str = "claude_code", **more: str) -> dict[str, str]:
    return {"authorization": f"Bearer {token}", "x-teamflow-client": client, **more}


def assert_error(r, status: int, code: str) -> dict:
    assert r.status_code == status, r.text
    body = r.json()
    assert body["error"] == code and isinstance(body["message"], str) and body["message"]
    assert "err" not in body and "detail" not in body
    return body


async def test_note_ok(client, svc, log_path):
    r = await client.post("/api/v1/tasks/T-50:note", headers=h(ALICE), json={"note": "骨架屏接上了首页接口"})
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "T-50" and body["st"] == "doing"
    ev = svc.events[-1]
    assert ev.type == "note" and ev.actor == "alice" and ev.actor_kind == "agent" and ev.via == "rest" and ev.client == "claude_code"
    rec = read_log(log_path)[-1]
    assert rec["tf_client"] == "claude_code" and rec["h"] == "alice" and rec["st"] == 200


async def test_done_ok_and_idempotent(client, svc):
    hdr = h(BOB, "codex", **{"idempotency-key": "done-T-49-1"})
    r = await client.post("/api/v1/tasks/T-49:done", headers=hdr, json={"note": "迁移完成，PR #12 已合并"})
    assert r.status_code == 200 and r.json()["id"] == "T-49" and r.json()["st"] == "done"
    r2 = await client.post("/api/v1/tasks/T-49:done", headers=hdr, json={"note": "迁移完成，PR #12 已合并"})
    assert r2.status_code == 200 and r2.json() == r.json() and r2.headers.get("idempotent-replayed") == "true"
    assert svc.tasks["T-49"].status == "done"
    done_at = svc.tasks["T-49"].done_at
    # 已完成再 done（CLI 重试、换了 Idempotency-Key）：不改状态，note 记为一条进度
    r3 = await client.post("/api/v1/tasks/T-49:done", headers=h(BOB, "codex"), json={"note": "补充：回滚脚本也合并了"})
    assert r3.status_code == 200 and r3.json()["st"] == "done" and svc.tasks["T-49"].done_at == done_at
    assert [e.type for e in svc.events if e.subject == "T-49"][-2:] == ["task.done", "note"]
    # 已取消的任务不能完成：带错误码的 4xx
    await client.post("/api/v1/tasks/T-53:cancel", headers=h(ALICE), json={"note": "不做了"})
    assert_error(await client.post("/api/v1/tasks/T-53:done", headers=h(ALICE), json={"note": "做完了"}), 400, "invalid")


async def test_blocker_ok(client, svc):
    payload = {"title": "测试库连不上新实例", "detail": "连接超时", "tried": "重试 3 次", "task": "T-50", "need": "bob"}
    r = await client.post("/api/v1/blockers", headers=h(ALICE), json=payload)
    assert r.status_code == 201
    body = r.json()
    assert body["id"].startswith("B-") and body["st"] == "open" and body["need_state"] == "proposed"
    b = svc.blockers[body["id"]]
    assert b.task_id == "T-50" and b.needs == "bob" and b.raised_by_kind == "agent"
    # 只有标题也行
    r = await client.post("/api/v1/blockers", headers=h(ALICE), json={"title": "等设计稿"})
    assert r.status_code == 201 and r.json()["st"] == "open"


@pytest.mark.parametrize(
    "path,payload,status,code",
    [
        ("/api/v1/tasks/T-50:note", {}, 400, "invalid"),  # note 不能为空
        ("/api/v1/tasks/T-50:note", {"note": ""}, 400, "invalid"),
        ("/api/v1/tasks/T-50:note", {"note": "x" * 501}, 422, "invalid"),  # 超长
        ("/api/v1/tasks/T-50:note", {"note": 123}, 422, "invalid"),  # 类型不对
        ("/api/v1/tasks/T-50:done", {}, 400, "invalid"),  # done 要附 note
        ("/api/v1/tasks/T-49:note", {"note": "不是我的"}, 403, "not_allowed"),
        ("/api/v1/tasks/T-49:done", {"note": "不是我的"}, 403, "not_allowed"),
        ("/api/v1/tasks/T-999:note", {"note": "没有"}, 404, "not_found"),
        ("/api/v1/tasks/T-999:done", {"note": "没有"}, 404, "not_found"),
        ("/api/v1/tasks/T-50:note", {"note": "token 是 sk-ant-api03-abcdefghijklmnop"}, 422, "secret_detected"),
        ("/api/v1/blockers", {}, 422, "invalid"),  # 缺 title
        ("/api/v1/blockers", {"title": "看 ~/.aws/credentials"}, 422, "invalid"),
        ("/api/v1/blockers", {"title": "卡住了", "need": "nobody"}, 400, "invalid"),
        ("/api/v1/blockers", {"title": "卡住了", "task": "T-999"}, 404, "not_found"),
        ("/api/v1/blockers", {"title": "卡住了", "detail": "AppSecret: 9f86d081884c7d659a2feaa0c55ad015"}, 422, "secret_detected"),
    ],
)
async def test_errors_have_code_and_message(client, path, payload, status, code):
    assert_error(await client.post(path, headers=h(ALICE), json=payload), status, code)


@pytest.mark.parametrize("path", ["/api/v1/tasks/T-50:note", "/api/v1/tasks/T-50:done", "/api/v1/blockers"])
async def test_auth_required(client, path):
    r = await client.post(path, headers={"x-teamflow-client": "claude_code"}, json={"note": "x", "title": "x"})
    assert_error(r, 401, "unauthorized")
    assert r.headers["www-authenticate"].startswith("Bearer")
    r = await client.post(path, headers=h("tf_pat_dev_nobody"), json={"note": "x", "title": "x"})
    assert_error(r, 401, "unauthorized")


async def test_unknown_routes_also_use_error_shape(client):
    assert_error(await client.post("/api/v1/tasks/T-50:fly", headers=h(ALICE), json={}), 404, "not_found")
    assert_error(await client.get("/api/v1/nope", headers=h(ALICE)), 404, "not_found")
    assert_error(await client.post("/api/v1/tasks/T-50:accept", headers=h(ALICE), json={}), 403, "human_only")
