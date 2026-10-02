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
| `teamflow hook session-start\|prompt\|stop\|session-end\|tool --client claude\|codex --cred <绝对路径>` | hook 执行体，永远 fail-open（出错不输出、exit 0，错误写 `${TEAMFLOW_STATE_DIR:-~/.local/state/teamflow}/log`）。`tool` 是 PostToolUse，只装在 Claude Code（D40），`--client codex` 直接退出 0 |
| `teamflow mcp-headers --client claude\|codex --cred <绝对路径> [--ws <slug>]` | 输出请求头 JSON（只有 `Authorization`、`X-Teamflow-Client`，不发会话头，见下）；stdout 是终端时拒绝 |
| `teamflow flush [--refresh] [--client c] [--cred p] [--ws slug]` | 上传 spool；`--refresh` 拉 `/api/v1/me/delta` 写缓存 |
| `teamflow inbox` | MCP 不可用时的兜底查看（只有编号和计数） |
| `teamflow note T-42 "<一句话>"` | 兜底：写一句进度 → `POST /api/v1/tasks/T-42:note` |
| `teamflow done T-42 "<说明>"` | 兜底：标记完成 → `POST /api/v1/tasks/T-42:done` |
| `teamflow block --title "…" [--task T-42] [--need handle] [--detail …] [--tried …]` | 兜底：报告困难 → `POST /api/v1/blockers`；`--need` 只是提议 |
| `teamflow claude-flags [--home d] [--quoted]` | 给 `claude --bare -p $(teamflow claude-flags)` 用 |
| `teamflow setup --home <d> [--dry-run] [--no-hardening] [--bin p] [--cred p]` | 写两端的 hooks 与 MCP 配置（Claude Code 5 个 hook，比 Codex 多一个 PostToolUse；Codex 4 个）；实验和测试必须用临时目录。已有 teamflow 的 hook 就原地更新、没有才追加一组到末尾；绝不删除、挪动别人的组和 handler（Codex 信任键带组序号和 handler 序号）：和别人同组时只换我们那一条，重复的只删不影响别人序号的那些，删空的组留 `{"hooks": []}` 占位，删不了的打印「注意」。`--dry-run` 不打印整份文件，只列 teamflow 相关键的改动前→改动后，并遮蔽一切像密钥、token、邮箱的值（`redact.py`） |
| `teamflow setup --isolated <绝对路径> [--bin p] [--api-url u] [--workspace w] [--no-hardening] [--dry-run]` | 本地试用（`scripts/local-up.sh` 用）：全部写进这个目录，一个字节都不写 HOME。`claude/settings.json`（5 个 hook，给 `claude --settings`）、`claude/mcp.json`（给 `--mcp-config`，配合 `--strict-mcp-config`）、`codex/config.toml` 与 `codex/hooks.json`（这个目录就是试用时的 `CODEX_HOME`）、`credentials.json`（0600）、`bin/teamflow`（sh 包装：把 `TEAMFLOW_STATE_DIR` 固定为 `<dir>/cli-state` 再 exec `--bin` 指的真正 teamflow）。hook 和 helper 的命令串规则不变（`<bin> hook <事件> --client … --cred <绝对路径>`），只是 bin 换成包装；状态目录写在包装里，因为 Codex 运行 helper 前清空环境、命令串又不能多加参数。不能和 `--home`、`--cred` 同用。合并规则同上：重跑逐字节不变，Codex 写进 `config.toml` 的信任记录保留 |
| `teamflow doctor --home <d>` | 基础检查：hook 组「存在且命令串一致」（不要求在末尾；Claude Code 查 5 个、Codex 查 4 个；SessionStart、SessionEnd、PostToolUse 还查所在组的 matcher；teamflow 的 handler 设了 `async` / `asyncRewake` 算失败）；Linux 上 `sandbox.enabled` 为 true 时检查 `bwrap`、`socat`，缺了标失败。另查最近 7 天有没有服务端没记下的提交（仓库没有 `origin` 时，见下方 hooks/batch 的 `no_repo`）。`--isolated <dir>` 检查本地试用目录：另查包装脚本和它指向的 teamflow，MCP 查 `<dir>/claude/mcp.json`，spool 查 `<dir>/cli-state`，跑 `codex --version` 时带 `CODEX_HOME=<dir>/codex`（codex 每次启动都会在 `CODEX_HOME/tmp/arg0` 建目录，不带就建到 `~/.codex`） |

`note` / `done` / `block` 都接受 `--client claude|codex`（默认按环境判断：只有 Codex 的会话变量时用 codex，否则 claude）、
`--cred`、`--ws`、`--json`。默认输出一两行中文；失败时 stderr 以错误码开头（如 `teamflow note：needs_accept：…`），
和 MCP 工具的错误文本一致；`--json` 输出一行 `{"ok": true, "id": …, "st": …}` 或 `{"ok": false, "error": …, "status": …, "message": …}`。
返回码 0 成功、1 服务端拒绝或网络/凭据问题、2 参数不对（不发请求）。
读不到凭据时（含 `inbox`）输出 `credentials：<问题>`，下面每行一条修复办法：文件不存在、是空的或没有权限
（Claude Code 沙箱屏蔽了凭据文件时就是后两种）、缺 token、workspace 不对，各给对应的办法；不输出 token。

hook、mcp-headers、flush 三条快速路径只用标准库，并且不导入 `json`/`re`
（读 JSON 用 C 实现的 `_json` 扫描器，写 JSON 用 `common.dumps` 手写的最小编码），HTTP 用 `http.client`（回环地址永远直连，不跟随重定向）。

UserPromptSubmit 只读本地缓存：不联网、不拉起子进程，也不导入 `spool`。缓存由 Stop 每回合拉起的
`flush --refresh` 和 SessionStart 刷新。

**PostToolUse（`hook tool`，只装在 Claude Code，D40）**：把每次 teamflow 工具调用对到具体会话。
setup 写的组是 `{"matcher": "^mcp__teamflow__.*", "hooks": [{"type": "command", "command": <bin>, "args": ["hook", "tool",
"--client", "claude", "--cred", <abs>], "timeout": 2}]}`：exec form，同步、2 秒超时，不设 `async`
（cc_hooks.md「Run hooks in the background」：`claude -p` 收尾时会杀掉还在跑的 async hook，最后一次调用的映射会丢）。
hook 只认 `tool_name` 以 `mcp__teamflow__` 开头、`session_id` 和 `tool_use_id` 合格的输入（`tool_use_id` 是 `toolu_`
加 8–80 个字母、数字、下划线，与服务端校验 `_meta["claudecode/toolUseId"]` 的规则一致），往 spool 写一条
`tool_map`；不读 `tool_input` / `tool_response`，不联网、不拉起进程、不写会话状态、不输出。
上报靠下一次 Stop / SessionEnd 拉起的 flush。`tool_use_id` 与同一次 tools/call 的 `_meta["claudecode/toolUseId"]`
相等（`spike/results/S3.md` 结论 3），服务端据此把成员级的调用补成会话级。
工具返回错误（isError）时 Claude Code 触发的是 PostToolUseFailure、不是 PostToolUse，这类调用仍是成员级。

## 两端 hook 的输入输出

| | Claude Code | Codex |
|---|---|---|
| 执行方式 | exec form（`command` + `args`），不经过 shell | 命令串交给会话 shell `-c`，没有时 `$SHELL -lc` |
| 输入字段（我们用到的） | `session_id`、`cwd`、`source`、`prompt_id`、`reason`；PostToolUse 另用 `tool_name`、`tool_use_id` | `session_id`、`cwd`、`source`、`turn_id`、`reason` |
| 从不读取/上传 | `prompt`、`last_assistant_message`、`transcript_path`、`tool_input`、`tool_response` | 同左（没有 PostToolUse） |
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

**`POST /api/v1/hooks/batch`**：`{"v":1,"items":[…]}`，最多 100 条、请求体不超过 64KB（`flush` 按条数和编码后的字节数切批，每批不超过 60KB；仍然 413 时对半拆开重发，只有单条就超限的才进 dead-letter）；每条都有 `key`（幂等键）和 `type`：

- `turn_end`：`session_id, client, ts, turn, cwd_name, repo, branch, head, commits[{sha,title}]（本人最多 5 条）, own_more, other_commits`
- `end`：`session_id, client, ts, reason`（`clear|resume|logout|prompt_input_exit|other`）
- `start`：session-start 联网失败时补发的会话登记，字段同 session-start 请求体
- `tool_map`（只有 Claude Code）：`key, session_id, tool_use_id, tool`。`key` 是 hash(client, session_id, tool_use_id)，
  `tool` 是去掉 `mcp__teamflow__` 前缀的工具名（如 `claim_task`）；不带 `client`、`ts`，client 一律取 token 的

返回 `{"results":[{"key":"…","status":200}]}`。逐条 2xx 或 409（已存在）算成功；5xx/408/425/429 按 5 秒到 5 分钟指数退避；
其余 4xx 进 dead-letter（`spool/dead/`）。整批非 2xx 同理。同一会话按写入顺序上报：更早的记录还在退避时，同会话后写的
记录（比如 SessionEnd 的 `end`）等它到期一起发；否则 `end` 先到，服务端会把迟到的 `tool_map` 判成"会话已结束"（403）。

逐条结果 `{"status":200,"st":"no_repo","dropped":N}`：这一回合带了提交，但没有 `repo`（仓库没有 `origin`），服务端登记了
会话、没记提交（`dropped` 含 `own_more`）。记录照常算成功（不重试、不进 dead-letter），另在状态目录的
`notices/unrecorded.json` 按仓库根目录记条数和时间（不记提交标题；目录只在本机，spool 记录里的 `dir` 字段不上传）。
第一次的响应丢了、重试拿到 409 时，服务端带回 `was: "no_repo"` 和 `dropped`；旧服务端不带，没有 `repo` 的提交也按没记处理。
`teamflow doctor` 逐个仓库报"最近 7 天有 N 个提交没被服务端记下"和修法；已经补上 `origin` 的只给提示。同一个仓库之后带
`repo` 的提交上报成功，只清这个仓库的那一项，别的仓库的提醒留着。

Stop 有提交要报、会话状态里又没有 `repo` 时，会重新读一次 `origin`，会话中途补上的地址当场生效。但 workspace 是会话开始时
按 cwd 和当时的 remote 选的：补上的 `origin` 按 `repo_patterns` 属于另一个 workspace 时，这一回合的提交整条不发（sha、标题、
地址都不发给会话开始时钉住的那个 workspace），会话照常发心跳；doctor 报"请在这个仓库里重开会话"，重开后按新的 remote 选对
workspace，提交照常上报，提醒消失。

## 凭据文件

```json
{"workspaces":{"team":{"api_url":"http://127.0.0.1:8100","tokens":{"claude":"tf_pat_…","codex":"tf_pat_…"},
 "repo_patterns":["/home/me/work/acme","github.com/acme/*"],"git_emails":["me@example.com"]}},"default":"team"}
```

`repo_patterns`：以 `/` 或 `~` 开头的按目录匹配 cwd（含子目录）；其余按 `host/path` 形式匹配 git remote。
匹配不到用 `default`。`git_emails` 可选，setup 会写入 `git config --global user.email`。
