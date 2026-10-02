# teamflow-server（M0 原型）

FastAPI 单体：`/api/v1` REST（权威接口）+ `/mcp/` 远程 MCP（FastMCP 4.0.10 / mcp 2.2.0，无状态，同一个 URL 兼容
2025-06-18 起的旧代握手协议和 2026-07-28 新代协议）。数据只在内存里。

```bash
uv pip install -e 'server[test]'
uvicorn teamflow_server.app:app --port 8100 --workers 1
pytest -q server
python spike/smoke_mcp.py --base http://127.0.0.1:8100   # 两代协议冒烟
```

## 环境变量

| 变量 | 缺省 | 说明 |
|---|---|---|
| `TEAMFLOW_DEV_TOKENS` | alice/bob 两枚开发令牌 | `token:handle:client,...`，client ∈ claude_code / codex / cli / cloud |
| `TEAMFLOW_LOG` | `spike/out/server.log.jsonl` | 观测日志（不记请求体、查询串和令牌） |
| `TEAMFLOW_DEV_ENDPOINTS` | `0`（关） | DEV ONLY 端点开关，见下 |
| `TEAMFLOW_DEV_SECRET` | 无 | DEV 端点的密钥；未设置时 DEV 端点一律 404 |
| `TEAMFLOW_FAULT_DELAY_MS` | `0` | 让 `/api/v1/hooks/*`、`/api/v1/me/*` 延迟返回 |
| `TEAMFLOW_ALLOWED_ORIGINS` | 空 | `/mcp/` 上允许的 Origin |
| `TEAMFLOW_MCP_JSON_RESPONSE` | `1` | MCP 响应用 JSON（`0` 用 SSE） |

## DEV ONLY 端点（模拟"人在手机微信里操作"，M1 上线前整组删除）

- 默认关闭。要用时同时设置 `TEAMFLOW_DEV_ENDPOINTS=1` 和一个随机的 `TEAMFLOW_DEV_SECRET`，请求带
  `X-Teamflow-Dev-Secret: <密钥>` 和 `X-Teamflow-Dev-Human: <handle>`。开关没开、没配密钥、密钥不对，一律 404
  （和"没有这个端点"无法区分）；带任何 `Authorization`（PAT）一律 403 `human_only`。`dev/reset` 受同一个开关和密钥管。
- 密钥不要放进 agent 能读到的地方（shell profile、仓库、`.env`）。同一系统用户下的进程仍能读
  `/proc/<uvicorn pid>/environ`，所以在有真实 agent 的机器上做实验时，用完就关掉开关。
- 人类动作必须带上页面上看到的版本（H3）：
  - `GET /api/v1/dev/items/{id}`：模拟详情页，返回表单会带的 `v`、`sha`、`seq`（任务）、`through`（页面上最大的动态编号）。
  - `POST /api/v1/dev/tasks/{id}:accept` `{v, sha, seq, through?}`；`:claim` `{v, sha, through?}`；`:forward` `{through}`。
  - `POST /api/v1/dev/blockers/{id}:help` `{v, sha, through?}`；`:ask`；`:forward` `{through}`。
  - 缺字段 400 `invalid`；与当前不一致 409 `conflict`（"内容刚被修改，请重新查看"）；`through` 不能超过当前最大事件 ID。
  - 「转发」只推进"已看到的动态位置"，绝不授予或升级正文可见性：没接受过正文的人转发之后，agent 拿到的正文仍是 withheld。

## REST 错误格式与 CLI 兜底端点

所有 REST 错误都是 `{"error": "<code>", "message": "...", ...}`（可能附带 `id`、`by`、`rule`、`pos` 等结构化字段），
包括请求体校验失败（422 `invalid`）和路由级 404/405。MCP 的 isError 结果里 structuredContent 仍是短键
`{"err", "msg", ...}`，content 文本以错误码开头（`needs_human：已发到您的微信……`）。

CLI 兜底命令（MCP 不可用时）用这三个端点，鉴权同其他 REST（`Authorization: Bearer tf_pat_…` + `X-Teamflow-Client`），
支持 `Idempotency-Key`：

| 命令 | 端点 | 成功 |
|---|---|---|
| `teamflow note` | `POST /api/v1/tasks/{id}:note` `{"note": "..."}` | 200 `{"id", "st", "new"}` |
| `teamflow done` | `POST /api/v1/tasks/{id}:done` `{"note": "..."}` | 200 `{"id", "st", "new"}` |
| 报告困难 | `POST /api/v1/blockers` `{"title", "detail?", "tried?", "task?", "need?"}` | 201 `{"id", "st", "need_state", "suggest"}` |

## 会话归属（plan 6.5）

写操作的会话归属统一走 `Service.resolve_session`：会话必须存在、未结束、`token_id` 等于当前 token、`client` 等于
token 的 client，才算 exact；否则降为成员级并写审计（`session.resolve`）。读操作不做归属。

- Codex：`_meta["x-codex-turn-metadata"].session_id` 匹配 hooks 登记的会话（hook 输入的 session_id 与它相同）；
  `thread_id` 只记在事件的 `thread` 上（子线程），不参与匹配。日志里这个字段只留 session_id、thread_id、turn_id。
- `X-Teamflow-Session` 请求头同样要过 `resolve_session`。注意 S3：嵌套的 Claude Code 会把外层会话 ID 继承给
  headersHelper，如果外层会话也是同一枚 token 登记的，服务端无法分辨——这一条要靠 CLI 不再发这个头解决。
- hooks：条目里的 client 一律取 token 的 client；条目指向的会话属于别的 token 时整条忽略（返回 403 `ignored`，
  不记提交、不改会话、`end` 也不清对方会话的 `current_task`）。
- token 在日志、事件、会话里只以 `token_id`（token 的 sha256 前缀）出现；`TokenRec` 的 repr 不含 token。

## 已知协议偏差

已经修掉的（m6）：

- 两代都只宣告 `{"tools": {}}`：不宣告 `listChanged`（工具清单是常量；旧代无状态 GET 返回 405，没有通知流），
  不宣告没实现的 logging、prompts、resources、completions 和 `io.modelcontextprotocol/ui` 扩展（M0 评审：宣告了
  prompts/resources 的话，客户端每次连接会多发 prompts/list、resources/list 两个请求）。
- `server/discover` 的 `supportedVersions` 与 -32022 的 `data.supported` 都列出两代：
  `["2026-07-28", "2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"]`（新到旧，同规范示例）。

SDK 做不到、只能绕开或保留的：

1. **能力宣告和 discover 没有公开开关。** FastMCP 4.0.10 的 `LowLevelServer.get_capabilities` 无条件加 ui 扩展，
   prompts/resources/logging 按"注册了处理器"推导，旧代 `listChanged` 写死为 true。我们在 `mcp_server._honest_capabilities`
   里替换了实例的 `get_capabilities`，并用 `add_request_handler` 换掉 `server/discover`。升级 FastMCP/mcp 时要复核，
   `tests/test_mcp_protocol.py` 和 smoke 都断言了结果。
2. **没宣告的方法仍会应答。** FastMCP 照样注册 `prompts/list`、`resources/list`、`resources/templates/list`、
   `logging/setLevel` 等处理器，客户端硬要调用时返回空列表，而不是 -32601。
3. **-32022 的 `supported` 是网关改写出来的。** mcp 2.2.0 streamable HTTP 传输层（`_streamable_http_modern`）用
   `MODERN_PROTOCOL_VERSIONS` 生成 -32022，没有配置项；网关扣下 `/mcp/` 的 400 JSON 响应，只在错误码是 -32022 时补上
   旧代版本并改 Content-Length，其余 400（如 -32020）原样转发。stdio/双代流式循环里的 -32022（`runner._initialize_after_modern_data`）
   我们不用，未处理。
4. **旧代 GET `/mcp/` 返回 405。** 无状态模式没有服务端发起的 SSE 流（规范允许）；因此不宣告 `listChanged`。
   新代也不提供 `subscriptions/listen`。
5. **请求体上限。** FastMCP 的 `http_app()` 不暴露 SDK 的 `max_request_body_size`（SDK 内部仍是 4MB）；
   网关在鉴权之后、交给 SDK 之前先按 64KB 截断（Content-Length 超限直接 413，分块传输读到超限也 413）。
   生产 nginx 的 `/mcp/` 也应设 `client_max_body_size 64k`。
6. **新代头 + initialize 返回 400**（SDK 的新代处理器不接受握手），旧代客户端不会这样发；这是 SDK 的规范行为。
