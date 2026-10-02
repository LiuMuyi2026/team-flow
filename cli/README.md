# teamflow 命令行（M0 原型）

`teamflow` 同时是 Claude Code / Codex 的 hook 执行体、MCP 凭据 helper 和兜底命令。

```bash
uv pip install --python .venv/bin/python -e cli     # 开发
.venv/bin/pytest cli -q                              # 测试
.venv/bin/python spike/bench_hooks.py --stub normal  # S4 延迟基准（--stub slow|down，或 --api <地址>）
```

测延迟要用非 editable 安装的独立 venv（`uv venv v && uv pip install --python v/bin/python ./cli`），
共享 `.venv` 里的 editable finder 每次启动多约 19ms。

## 命令

| 命令 | 说明 |
|---|---|
| `teamflow hook session-start\|prompt\|stop\|session-end --client claude\|codex --cred <绝对路径>` | hook 执行体，永远 fail-open（出错不输出、exit 0，错误写 `${TEAMFLOW_STATE_DIR:-~/.local/state/teamflow}/log`） |
| `teamflow mcp-headers --client claude\|codex --cred <绝对路径> [--ws <slug>]` | 输出请求头 JSON（只有 `Authorization`、`X-Teamflow-Client`，不发会话头，见下）；stdout 是终端时拒绝 |
| `teamflow flush [--refresh] [--client c] [--cred p] [--ws slug]` | 上传 spool；`--refresh` 拉 `/api/v1/me/delta` 写缓存 |
| `teamflow inbox` | MCP 不可用时的兜底查看（只有编号和计数） |
| `teamflow note T-42 "<一句话>"` | 兜底：写一句进度 → `POST /api/v1/tasks/T-42:note` |
| `teamflow done T-42 "<说明>"` | 兜底：标记完成 → `POST /api/v1/tasks/T-42:done` |
| `teamflow block --title "…" [--task T-42] [--need handle] [--detail …] [--tried …]` | 兜底：报告困难 → `POST /api/v1/blockers`；`--need` 只是提议 |
| `teamflow claude-flags [--home d] [--quoted]` | 给 `claude --bare -p $(teamflow claude-flags)` 用 |
| `teamflow setup --home <d> [--dry-run] [--no-hardening] [--bin p] [--cred p]` | 写两端的 hooks 与 MCP 配置；实验和测试必须用临时目录。已有 teamflow 组就原地替换、没有才追加到末尾（Codex 信任键带组序号，不挪位置）；`--dry-run` 打印的凭据一律遮蔽成 `tf_pat_****` |
| `teamflow doctor --home <d>` | 基础检查：hook 组「存在且命令串一致」（不要求在末尾）；Linux 上 `sandbox.enabled` 为 true 时检查 `bwrap`、`socat`，缺了标失败 |

`note` / `done` / `block` 都接受 `--client claude|codex`（默认按环境判断：只有 Codex 的会话变量时用 codex，否则 claude）、
`--cred`、`--ws`、`--json`。默认输出一两行中文；失败时 stderr 以错误码开头（如 `teamflow note：needs_accept：…`），
和 MCP 工具的错误文本一致；`--json` 输出一行 `{"ok": true, "id": …, "st": …}` 或 `{"ok": false, "error": …, "status": …, "message": …}`。
返回码 0 成功、1 服务端拒绝或网络/凭据问题、2 参数不对（不发请求）。

hook、mcp-headers、flush 三条快速路径只用标准库，并且不导入 `json`/`re`
（读 JSON 用 C 实现的 `_json` 扫描器，写 JSON 用 `common.dumps` 手写的最小编码），HTTP 用 `http.client`（回环地址永远直连，不跟随重定向）。

UserPromptSubmit 只读本地缓存：不联网、不拉起子进程，也不导入 `spool`。缓存由 Stop 每回合拉起的
`flush --refresh` 和 SessionStart 刷新。

## 两端 hook 的输入输出

| | Claude Code | Codex |
|---|---|---|
| 执行方式 | exec form（`command` + `args`），不经过 shell | 命令串交给会话 shell `-c`，没有时 `$SHELL -lc` |
| 输入字段（我们用到的） | `session_id`、`cwd`、`source`、`prompt_id`、`reason` | `session_id`、`cwd`、`source`、`turn_id`、`reason` |
| 从不读取/上传 | `prompt`、`last_assistant_message`、`transcript_path` | 同左 |
| 输出 | `{"hookSpecificOutput":{"hookEventName":…,"additionalContext":…}}` | 纯文本，首行以哨兵 `【teamflow` 开头 |

哨兵用全角 `【`：Codex 把首个非空白字符是 `{` 或 `[` 的 stdout 当 JSON 解析，解析失败就把这次 hook 判为失败、
不注入（`codex-rs/hooks/src/engine/output_parser.rs` 的 `looks_like_json`）。plan 6.6 原来的 `[teamflow` 会被拒。

## 与服务端的约定（M0 草案，服务端实现时以此为准或回改这里）

通用请求头：`Authorization: Bearer tf_pat_…`、`X-Teamflow-Client: claude_code|codex`、所有 POST 带 `Idempotency-Key`。
`X-Teamflow-Session` 只在 session-start 请求里带，值就是 hook 输入的 `session_id`；
MCP 请求（mcp-headers）和兜底命令都不带（M0 S3：headersHelper 拿到的是继承来的外层会话 ID）。

会话匹配：hook 上报的 `session_id`（session-start 请求体和头、batch 条目）原样取自 hook 输入。
Codex 的 hook `session_id` 和 tools/call 的 `_meta["x-codex-turn-metadata"].session_id` 都来自 Codex 的
`sess.session_id()`，服务端用后者匹配前者；CLI 从不用 `CODEX_THREAD_ID`、`turn_id` 代替。

**兜底写命令**：`POST /api/v1/tasks/{id}:note {"note"}`、`POST /api/v1/tasks/{id}:done {"note"}`、
`POST /api/v1/blockers {"title","detail?","tried?","task?","need?"}`；成功返回 `{id, st}`，
失败是 4xx JSON `{"error":"<code>","message":"…"}`（CLI 也认 M0 的 `{"err","msg"}`）。网络错误用同一个
`Idempotency-Key` 重试一次。CLI 只输出编号和状态枚举；服务端说明压成一行、去掉控制字符、截到 200 字。

**`POST /api/v1/hooks/session-start`**（CLI 整体 1 秒超时）

```json
{"v":1,"session_id":"…","client":"codex","source":"startup","cwd_name":"api","repo":"https://github.com/acme/api.git",
 "branch":"main","head":"<40位sha>","interactive":false,"machine_id":"<16位hex>","cli":"0.1.0"}
```

返回 200 + 结构化数据（只认下列字段，其余忽略；不合格的值丢弃）：

```json
{"v":1,"me":"zhao","doing":["T-42"],"todo":["T-50"],
 "to_accept":[{"id":"T-52","by":"li","bk":"agent","client":"claude_code"}],
 "help_me":[{"id":"B-7","by":"zhang"}],"fwd":[{"id":"B-7","n":1,"by":"zhang"}],
 "proposed":[{"id":"B-9","h":"zhang","client":"codex"}],"pool_new":3,"repo_hint":["T-42"],"cursor":"…"}
```

ID `^[TB]-[0-9]{1,6}$`；handle `^[a-z][a-z0-9_]{1,15}$`；`client` ∈ `claude_code|codex|cli|cloud`；`bk` ∈ `human|agent`；
计数是 0–9999 的整数；每个列表最多取 10 项。

**`GET /api/v1/me/delta?cursor=<c>`**：带 `If-None-Match`；返回与上面相同形状的快照（可含新的 `cursor`、`ETag`），
未变化返回 304。CLI 在本地比对「需要我」的条目（todo、to_accept、help_me、fwd、proposed）决定增量。

**`POST /api/v1/hooks/batch`**：`{"v":1,"items":[…]}`，最多 100 条；每条都有 `key`（幂等键）和 `type`：

- `turn_end`：`session_id, client, ts, turn, cwd_name, repo, branch, head, commits[{sha,title}]（本人最多 5 条）, own_more, other_commits`
- `end`：`session_id, client, ts, reason`（`clear|resume|logout|prompt_input_exit|other`）
- `start`：session-start 联网失败时补发的会话登记，字段同 session-start 请求体

返回 `{"results":[{"key":"…","status":200}]}`。逐条 2xx 或 409（已存在）算成功；5xx/408/425/429 按 5 秒到 5 分钟指数退避；
其余 4xx 进 dead-letter（`spool/dead/`）。整批非 2xx 同理。

## 凭据文件

```json
{"workspaces":{"team":{"api_url":"http://127.0.0.1:8100","tokens":{"claude":"tf_pat_…","codex":"tf_pat_…"},
 "repo_patterns":["/home/me/work/acme","github.com/acme/*"],"git_emails":["me@example.com"]}},"default":"team"}
```

`repo_patterns`：以 `/` 或 `~` 开头的按目录匹配 cwd（含子目录）；其余按 `host/path` 形式匹配 git remote。
匹配不到用 `default`。`git_emails` 可选，setup 会写入 `git config --global user.email`。
