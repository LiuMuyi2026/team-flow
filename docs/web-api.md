# 网页 API（本地试用版）

给做前端的人照着做。服务端代码在 `server/teamflow_server/web.py`、`webauth.py`、`devlogin.py`，测试在 `server/tests/test_web.py`。

本地试用版里，浏览器登录成某个成员，以本人的身份做接受、拒绝、认领、转发、帮忙这些只有人能做的动作。正式版里人用通行密钥登录，每个人类动作再当场验证一次通行密钥（plan D54、D55），这一层到 M1 换掉：接口路径不变，按钮请求另带一次通行密钥断言。通知（邮件或微信，plan D61）只做提醒，不授予任何权限。

## 1. 先说清楚的几条规则

- **只在本地开发模式存在。** 服务端要设 `TEAMFLOW_DEV_ENDPOINTS=1`，请求要来自本机（127.0.0.1 或 ::1）、不带反向代理的转发头（`X-Forwarded-For`、`Forwarded` 等），`Host` 必须是 `127.0.0.1`、`localhost` 或 `[::1]`（可带端口）。任何一条不满足，`/dev/login` 和 `/api/v1/web/*` 一律返回 404，和"没有这个端点"分不出来。
- **只认人类会话 cookie。** 请求带了 `Authorization` 头（PAT 或别的）一律 403 `human_only`，不看它有效与否（硬规则 1）。反过来，网页会话 cookie 也不能调 `/api/v1/*` 的 PAT 接口（那边只认 Bearer，cookie 被忽略，返回 401）。
- **写请求要过 CSRF。** 除 GET/HEAD/OPTIONS 外，每个请求都要带：
  - `X-CSRF-Token`：值等于 `tf_csrf` cookie，也等于 `GET /api/v1/web/me` 返回的 `csrf`（双提交，服务端两边都核对）；
  - `Origin`：等于本站，即 `http://<当前地址栏的 host:port>`。浏览器的 `fetch` 同源 POST 会自动带。Origin 缺失或是 `null` 时，服务端只认浏览器自动加的 `Sec-Fetch-Site: same-origin`。
  不满足返回 403 `csrf`。
  **页面不要设 `<meta name="referrer" content="no-referrer">`**：那样浏览器给同源 POST 发 `Origin: null`。服务端给页面发的是 `Referrer-Policy: same-origin`，照样不把地址带给别的站。
- **人类动作带页面渲染时看到的值**（plan 5.1、7.2，H3）。详情接口的 `page` 里有 `v`、`sha`、`seq`（任务）、`through`，按钮请求原样带回：
  - 「接受」：`v`、`sha`、`seq`、`through`；
  - 「认领」（任务）、「认领」（困难，即帮忙）：`v`、`sha`、`through`；
  - 「转发给我的 agent」：`through`；
  - 「拒绝」：`seq` 和 `reason`。

  缺字段 400 `invalid`；`v`、`sha`、`seq` 与当前不一致 409 `conflict`（页面提示"内容刚被修改，请重新查看"，然后重新拉详情）；`through` 超过当前最大动态编号 400。
  **`through` 必须是页面渲染时的值，不要在点按钮前重新拉一次再填**：页面之后对方 agent 新写的评论编号比它大，本来就不该算"您已看过"。
- **GET 没有副作用。** 打开详情页不等于接受；正文给人看，但本人的 agent 仍然拿不到，直到点「接受」或「认领」。
- **链接用 `path`，不要用 `url`。** `url` 是给 agent 的绝对地址（按 `TEAMFLOW_PUBLIC_URL`，缺省 `http://127.0.0.1:8100`）；本地试用时第二个人登录在 `localhost` 上，跳到 `127.0.0.1` 会变成另一个人的会话。`path` 是站内相对路径，如 `/task?w=team&id=T-52`。

## 2. 登录流程

1. 服务端启动（本地开发模式）时，在 stderr 给每个成员打印一条一次性登录链接：
   ```text
   teamflow-server: 本地试用登录链接（每个只能用一次，10 分钟内有效，重启服务端后作废）：
   teamflow-server:   alice  http://127.0.0.1:8100/dev/login?code=<码>&as=alice
   teamflow-server:   bob    http://localhost:8100/dev/login?code=<码>&as=bob
   ```
   成员是种子数据里的 alice、bob，加上 `TEAMFLOW_DEV_TOKENS` 里出现的 handle；有令牌的人排在前面。第一个用 `127.0.0.1`、第二个用 `localhost`：两个地址的 cookie 互不影响，同一个浏览器里两个标签页就能同时当两个人。第三个人起用无痕窗口或另一个浏览器。
2. 链接过期或用过后，在终端重新生成（必须是有终端的 shell，agent 的 Bash 里不给生成）：
   ```bash
   python -m teamflow_server.devlogin --as bob          # 打印一条新链接（stdout 只有这一行）
   python -m teamflow_server.devlogin --as bob --open   # 顺便用默认浏览器打开
   ```
   参数：`--ttl <分钟>`（1–60，缺省 10）、`--host 127.0.0.1|localhost`（缺省按成员分开，见上）。它读 `TEAMFLOW_STATE` 下服务端写的 `server.json`，所以要和服务端用同一个 `TEAMFLOW_STATE`。
3. `GET /dev/login?code=&as=`：只显示一页"您将以 bob（Bob）的身份登录"和一个「登录」按钮，**不消耗登录码**。码无效、用过、过期、和 `as` 不一致时返回 403 页面，提示重新生成。
4. 点「登录」→ `POST /dev/login`（表单 `code`、`as`，`Origin` 必须是本站）：消耗登录码，发两个 cookie，303 跳到 `/`。同一个地址上换人登录，旧会话作废。
5. 前端启动时调 `GET /api/v1/web/me`：401 就显示"请在终端运行 `python -m teamflow_server.devlogin --as <handle>` 拿登录链接"；200 就记下 `csrf`（也可以从 `tf_csrf` cookie 读）。

cookie：

| 名字 | 属性 | 用途 |
|---|---|---|
| `tf_web` | `HttpOnly; SameSite=Strict; Path=/; Max-Age=43200`；https 时加 `Secure` | 人类会话。服务端只存它的 sha256，数据在内存里，重启服务端全部失效 |
| `tf_csrf` | `SameSite=Strict; Path=/; Max-Age=43200`（页面能读）；https 时加 `Secure` | 双提交 CSRF token |

会话 12 小时过期（plan 7.2 电脑会话）。服务端重启后会话和登录码都作废（数据本来也在内存里）。

## 3. 通用约定

- 前缀 `/api/v1/web`，请求体和响应都是 JSON（`Content-Type: application/json`），请求体上限 64KB（先查会话再读请求体，超了 413）。
- 响应头一律 `Cache-Control: no-store`、`X-Content-Type-Options: nosniff`。
- 错误统一 `{"error": "<code>", "message": "<给人看的中文>", ...}`，结构化字段平铺（如 `id`、`by`、`v`、`seq`、`latest`、`rule`、`pos`、`field`、`why`）。`message` 可以直接显示。
- 编号：任务 `T-42`，困难 `B-7`。路径里也接受纯数字（当任务）和小写。
- 时间：`at` 是北京时间 `MM-DD HH:MM`（直接显示），`ts` 是 ISO 8601 带 `+08:00`。

**标题和正文的"信封"**（和 agent 拿到的同一个函数、同一版清洗，plan 5.1）：

```json
{"t": "支付回调重试", "by": "alice", "trust": "peer_agent", "client": "claude_code", "label": "alice 的 Claude Code"}
```

- `trust`：`self_human`（您写的）、`self_agent`（您的 agent 写的）、`peer_human`（别人写的）、`peer_agent`（别人的 agent 写的）。
- `label`：作者标注，人写的是 `"alice"`，agent 写的是 `"alice 的 Claude Code"`。plan 7.1 要求详情页醒目标注"这段话由 alice 的 Claude Code 生成"。
- 文字是**纯文本**，不做 HTML 转义，由 React 输出层转义；绝不能用 `dangerouslySetInnerHTML`。

**状态**：`st` 是枚举，`st_text` 是中文。

| 对象 | `st` | `st_text` |
|---|---|---|
| 任务 | `pool` / `pending` / `todo` / `doing` / `done` / `canceled` | 待认领 / 待接受 / 待开始 / 进行中 / 已完成 / 已取消 |
| 困难 | `open` / `resolved` | 未解决 / 已解决 |

困难的点名：`need_state` = `none` / `proposed`（agent 提议，待主人确认）/ `asked`（已点名），`need_text` 是中文。

## 4. 端点清单

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/dev/login?code=&as=` | 登录确认页（HTML，不消耗码） |
| POST | `/dev/login` | 表单 `code`、`as`；消耗码，发 cookie，303 → `/` |
| GET | `/api/v1/web/me` | 我是谁、`csrf`、成员和项目 |
| GET | `/api/v1/web/home` | 首页：待我处理、困难、大家在做什么、项目计数 |
| GET | `/api/v1/web/tasks?view=` | 任务列表：`pool` / `doing` / `mine` / `done` / `all` |
| GET | `/api/v1/web/tasks/{id}` | 任务详情（给人看的清洗后正文、全部动态、`page`、`agent`、`can`） |
| POST | `/api/v1/web/tasks` | 发布任务（可指派他人、指派自己、留空待认领） |
| POST | `/api/v1/web/tasks/{id}:accept` | 接受 `{v, sha, seq, through}` |
| POST | `/api/v1/web/tasks/{id}:decline` | 拒绝 `{seq, reason}` |
| POST | `/api/v1/web/tasks/{id}:claim` | 认领 `{v, sha, through}` |
| POST | `/api/v1/web/tasks/{id}:start` | 开始 `{}` |
| POST | `/api/v1/web/tasks/{id}:done` | 完成 `{note?}` |
| POST | `/api/v1/web/tasks/{id}:release` | 取消认领 `{note?, to_pool?}` |
| POST | `/api/v1/web/tasks/{id}:forward` | 转发给我的 agent `{through}` |
| POST | `/api/v1/web/tasks/{id}/comments` | 评论 `{body}` |
| POST | `/api/v1/web/blockers` | 报告困难（人报的点名直接生效） |
| GET | `/api/v1/web/blockers/{id}` | 困难详情 |
| POST | `/api/v1/web/blockers/{id}:help` | 认领（帮忙）`{v, sha, through}` |
| POST | `/api/v1/web/blockers/{id}:ask` | 确认点名 `{}`（agent 提议的点名，主人确认） |
| POST | `/api/v1/web/blockers/{id}:resolve` | 已解决 `{body}` |
| POST | `/api/v1/web/blockers/{id}:forward` | 转发给我的 agent `{through}` |
| POST | `/api/v1/web/blockers/{id}/comments` | 评论 `{body}` |
| GET | `/api/v1/web/notifications` | 模拟通知：我会收到的通知 |
| POST | `/api/v1/web/logout` | 登出 |

所有 `/api/v1/web/*` 共有的错误：401 `unauthorized`（没登录或过期）、403 `human_only`（带了 Authorization）、403 `csrf`（写请求）、404 `not_found`（不是本地开发模式、不是本机来源、对象不存在）、413 `too_large`、422 `invalid`（请求体类型不对，带 `field`）。下面每个端点只列它特有的。

### GET /api/v1/web/me

```json
{
  "me": "bob",
  "name": "Bob",
  "csrf": "ipFEAOv6LIR7StpJUmuX3wwbSIyfpb2g",
  "mode": "dev",
  "expires": "2026-10-03T12:42:47+08:00",
  "members": [{"h": "alice", "name": "Alice"}, {"h": "bob", "name": "Bob", "agent": true}],
  "projects": [{"key": "pay", "name": "支付"}, {"key": "tf", "name": "Team Flow"}]
}
```

页面顶部要一直显示"您现在是 bob"：同时扮演两个人时很容易点错。

`members[].agent` 只在为 `true` 时出现：这个成员有 agent 令牌（`TEAMFLOW_DEV_TOKENS` 里有他）。本地试用里就是您本人和 `scripts/sim-teammate.py` 能模拟的队友；只在演示数据里出现的人（比如 alice）没有。「我」页"换成队友"的例子从带 `agent` 的队友里挑。

### GET /api/v1/web/home

plan 7.1 首页的四块。只放 ID，标题在 `titles` 里按 ID 取。**列表上不放「接受」**（plan 7.1），只给「查看更多」进详情页。下面的示例把几种情况拼在一起，好把字段都列出来，实际一个人不一定同时都有。

```json
{
  "me": "bob",
  "mine": {
    "to_accept": [{"id": "T-52", "by": "alice", "bk": "agent", "client": "claude_code"}],
    "help_me": [{"id": "B-7", "by": "bob"}],
    "proposed": [{"id": "B-8", "h": "alice", "client": "codex"}],
    "fwd": [{"id": "B-7", "n": 1, "by": "bob"}],
    "replies": [{"id": "T-52", "ev": "accepted", "by": "bob"}]
  },
  "blockers": [{"id": "B-7", "by": "bob", "task": "T-49", "since": "10-02 23:42", "stuck_min": 60, "need": "alice"}],
  "doing": [
    {"h": "bob", "id": "T-49", "client": "codex", "today": false},
    {"h": "alice", "id": "T-50", "client": "claude_code", "sess": [{"client": "claude_code", "s": "1a6941c0"}], "today": true}
  ],
  "counts": {"pool": 2, "pending": 1, "todo": 0, "doing": 2, "blockers": 1},
  "titles": {
    "T-52": {"t": "支付回调重试", "by": "alice", "trust": "peer_agent", "client": "claude_code", "label": "alice 的 Claude Code"},
    "B-7": {"t": "测试库连不上", "by": "bob", "trust": "self_agent", "client": "codex", "label": "bob 的 Codex"}
  },
  "projects": [
    {"key": "pay", "name": "支付", "counts": {"pool": 0, "pending": 1, "todo": 0, "doing": 0, "blockers": 0}},
    {"key": "tf", "name": "Team Flow", "counts": {"pool": 2, "pending": 0, "todo": 0, "doing": 2, "blockers": 1}}
  ]
}
```

- ① 待我处理：`to_accept` 待您接受（`bk` 是 `human` 或 `agent`，agent 时显示"alice 的 Claude Code 请您协作"）；`help_me` 请您帮忙；`proposed` 您的 agent 提议的点名（点进去确认）；`fwd` 待您转发（`n` 条，最近一条是 `by` 的 agent 写的）；`replies` 回音（`ev` = `accepted` / `declined` / `done`）。
- ② 困难：按卡住时长排（最早的在前），`stuck_min` 是已卡分钟数（显示成"已卡 3 小时"），`need` 只在已点名时有，`helper` 有人帮时有。
- ③ 大家在做什么：每个进行中的任务一行，"bob · Codex · 在做 T-49 · 今天有更新"（`today`）。精确到会话时有 `sess`，可显示"会话 1a6941c0"或按顺序叫"窗口 1"。**不显示分钟数、回合数**（plan 7.4）。
- ④ `counts` 全队计数，`projects[].counts` 按项目。

### GET /api/v1/web/tasks?view=pool&project=&q=&limit=20&cursor=

`view`：`pool` 待认领（缺省）、`doing` 进行中、`mine` 我的（我负责或我发布、未结束）、`done` 已完成、`all` 全部。`limit` 1–50；有下一页时 `next` 是下一页的 `cursor`。`q` 按标题或编号筛选。

```json
{
  "rows": [
    {
      "id": "T-53",
      "t": {"t": "整理接口错误码", "by": "alice", "trust": "peer_agent", "client": "claude_code", "label": "alice 的 Claude Code"},
      "st": "pool",
      "upd": "10-02 23:12",
      "st_text": "待认领",
      "path": "/task?w=team&id=T-53"
    },
    {
      "id": "T-49",
      "t": {"t": "测试库迁移到新实例", "by": "bob", "trust": "self_human", "client": null, "label": "bob"},
      "st": "doing",
      "who": "bob",
      "blk": ["B-7"],
      "upd": "10-02 23:42",
      "st_text": "进行中",
      "path": "/task?w=team&id=T-49"
    }
  ],
  "next": null
}
```

`who` 负责人（有才给），`blk` 挂着的未解决困难，`upd` 最近活动时间。错误：400 `invalid`（`view` 不认识、`cursor` 无效）。

### GET /api/v1/web/tasks/{id}

```json
{
  "id": "T-52",
  "kind": "task",
  "t": {"t": "支付回调重试", "by": "alice", "trust": "peer_agent", "client": "claude_code", "label": "alice 的 Claude Code"},
  "st": "pending",
  "st_text": "待接受",
  "who": "bob",
  "by": "alice",
  "v": 1,
  "assign": {"seq": 1, "by": "alice", "bk": "agent", "client": "claude_code"},
  "project": "pay",
  "content": {"t": "回调失败时按指数退避重试 3 次，超过后记日志并提醒值班的人。", "by": "alice", "trust": "peer_agent", "client": "claude_code", "label": "alice 的 Claude Code"},
  "ev": [
    {"e": 7, "ty": "task.created", "by": "alice", "trust": "peer_agent", "client": "claude_code", "at": "10-02 22:42", "ts": "2026-10-02T22:42:47+08:00", "label": "alice 的 Claude Code", "what": "发布了任务"},
    {"e": 8, "ty": "task.assigned", "by": "alice", "trust": "peer_agent", "client": "claude_code", "at": "10-02 22:42", "ts": "2026-10-02T22:42:47+08:00", "data": {"to": "bob"}, "label": "alice 的 Claude Code", "what": "指派给了您"},
    {"e": 9, "ty": "comment", "by": "alice", "trust": "peer_agent", "client": "claude_code", "at": "10-02 22:50", "ts": "2026-10-02T22:50:03+08:00", "t": "日志在支付服务的 callback 目录。", "agent": false, "label": "alice 的 Claude Code", "what": "评论"}
  ],
  "url": "http://127.0.0.1:8100/task?w=team&id=T-52",
  "page": {"id": "T-52", "v": 1, "sha": "40b06df599a76d0d1d91c2b9027b784930974c0169c876fa9613ba5a5624c09f", "through": 9, "seq": 1},
  "agent": {"content": "not_accepted", "through": 0, "unforwarded": 1},
  "created": "2026-10-02T22:42:47+08:00",
  "can": ["accept", "decline", "forward", "comment"],
  "path": "/task?w=team&id=T-52"
}
```

- `content`：给人看的清洗后正文，**就是 agent 接受后会拿到的那段**（plan 3.2 场景 2），没有正文时不给。显示时醒目标注 `content.label`。
- `ev`：全部动态（不分页），旧的在前。`what` 是可直接显示的中文（"指派给了您""拒绝了""取消认领，放回待认领"……），按看页面的人写：动态里提到的人（`to`、`need`）是本人时写「您」，别人写 handle（同一条指派，bob 看是"指派给了您"，alice 看是"指派给了 bob"）；有文字的动态带 `t`，并带 `agent`：您的 agent 现在能不能读到这条。`data` 只有 handle、编号和枚举（`to`、`need`、`reason`、`v`、`through`）。
- `page`：按钮要原样带回的值（见第 1 节）。
- `agent`：您的 agent 现在能看到什么。`content` = `visible`（能读正文）/ `not_accepted`（要您接受或认领后才给；和 agent 读到的 `withheld: "not_accepted"` 是同一个值）/ `none`（没有正文）；`through` 已转发到的动态编号；`unforwarded` 别人的 agent 写的、还没转发的文字条数。
  按钮旁边的话照 plan 7.1、7.2："转发后，您的 Claude Code / Codex 才能读到这些评论"；没接受过正文时加一句"正文要您点「接受」或「认领」后才给"。
- `can`：该显示哪些按钮（只是提示，服务端照样会拒）：`accept`、`decline`、`claim`、`start`、`done`、`release`、`forward`、`comment`。
- `assign` 只在待接受时有；`urgent` 只在紧急时有（`true`）。
- 防误点（plan 7.1）：正文超过 800 字时，滚到底部按钮才能点。

错误：404 `not_found`（编号不存在，或把困难编号放到 `/tasks/` 下）。

### POST /api/v1/web/tasks

```json
{"title": "支付对账差 3 条", "body": "对账文件比账单少 3 条。", "assignee": "bob", "project": "pay", "urgent": false}
```

`title` 必填（最多 120 字，人写的换行折成空格）；`body` 选填（最多 4000 字）；`assignee` 留空或不传就是待认领，填自己就是待开始，填别人就是待对方接受（对方收到"alice 请您协作：支付对账差 3 条（T-55）"）；`project` 取 `me.projects[].key`；`parent` 选填（上级任务编号）。

201：

```json
{"id": "T-55", "url": "http://127.0.0.1:8100/task?w=team&id=T-55", "st": "pending", "path": "/task?w=team&id=T-55"}
```

错误：400 `invalid`（标题空、超长、`assignee` 不是成员、`project` 不存在）；422 `secret_detected`（正文疑似密钥或个人信息，带 `rule`、`pos`）。同样的内容 10 分钟内重复发布会返回第一次的结果（防双击）。

### 任务按钮 POST /api/v1/web/tasks/{id}:{action}

| action | 请求体 | 成功 200 | 特有错误 |
|---|---|---|---|
| `accept` | `{"v", "sha", "seq", "through"}` | `{"id": "T-52", "st": "todo", "v": 1}` | 400 缺字段或 `through` 超限；409 `conflict`（版本变了，或已经不是待您接受） |
| `decline` | `{"seq": 1, "reason": "这周排满了"}` | `{"id": "T-52", "st": "todo", "who": "alice"}` | 400 缺 `seq` 或原因；409 `conflict` |
| `claim` | `{"v", "sha", "through"}` | `{"id": "T-51", "st": "todo", "v": 1}` | 409 `conflict`；409 `taken`（带 `by`、`at`："T-51 已被 alice 于 10:21 认领。可以在「待认领」里换一个。"） |
| `start` | `{}` | `{"id": "T-51", "st": "doing", "new": 4}` | 409 `needs_accept`（还没接受，或接受后正文又改了）；403 `not_allowed` |
| `done` | `{"note": "选填"}` | `{"id": "T-51", "st": "done", "new": 0}` | 403 `not_allowed`（不是负责人）；409 `needs_accept` |
| `release` | `{"note": "选填", "to_pool": false}` | `{"id": "T-51", "st": "todo", "new": 0}`；`to_pool: true` 时 `{"id": "T-51", "st": "pool"}` | 400（待开始的任务不放回待认领时："还没开始；不做了的话，请选「放回待认领」"）；403 `not_allowed` |
| `forward` | `{"through": 9}` | `{"id": "T-52", "through": 9}` | 400 缺 `through` 或超限 |

- 接受后：对方（指派人）收到回音"bob 接受了 T-52"，您的 agent 能读正文和截至 `through` 的评论。
- 拒绝：任务回到发布人手里（待开始），发布人收到"bob 没接 T-52"；原因记在动态里。拒绝框下面写"说一句原因，对方好另做安排"（plan 7.1）。
- 认领：同时完成认领和接受当前版本，之后是"待开始"，由您或您的 agent 开始。
- 取消认领：缺省只是把进行中改回待开始（负责人不变）；`to_pool: true` 放回待认领（负责人清空）。
- 转发：只推进"已看到的动态位置"，**不授予正文**：没接受过正文的，转发后 agent 拿到的正文仍是 `withheld: "not_accepted"`。
- 未知 action：404 `not_found`。

### POST /api/v1/web/tasks/{id}/comments、/api/v1/web/blockers/{id}/comments

```json
{"body": "我下午看。"}
```

201：`{"id": 19}`（这条评论的动态编号）。错误：400 `invalid`（空、超过 2000 字）；422 `secret_detected`。您写的评论，别人的 agent 要等那个人接受过正文、或把它转发给自己的 agent 之后才能读（闸门在服务端）。

### POST /api/v1/web/blockers

```json
{"title": "测试账号被锁", "detail": "登录提示账号已锁定。", "tried": "重置密码没用。", "task": "T-50", "need": "bob"}
```

只有 `title` 必填。人报的困难带 `need` 时直接点名，并通知对方"alice 请您帮忙看 B-8"（agent 报的点名要主人确认）。201：

```json
{"id": "B-8", "st": "open", "need_state": "asked", "suggest": [{"h": "bob", "why": "solved_before"}], "path": "/blocker?w=team&id=B-8"}
```

`suggest` 是谁可能帮得上（`why` = `solved_before` / `active_here` / `same_project` / `member`）。

### GET /api/v1/web/blockers/{id}

```json
{
  "id": "B-7",
  "kind": "blocker",
  "t": {"t": "测试库连不上", "by": "bob", "trust": "peer_agent", "client": "codex", "label": "bob 的 Codex"},
  "st": "open",
  "st_text": "未解决",
  "task": "T-49",
  "need": "alice",
  "need_state": "asked",
  "need_text": "已点名",
  "v": 1,
  "content": {
    "detail": {"t": "新实例连接超时，怀疑安全组没有放行。", "by": "bob", "trust": "peer_agent", "client": "codex", "label": "bob 的 Codex"},
    "tried": {"t": "重试 3 次；换了网络；本机 telnet 端口不通。", "by": "bob", "trust": "peer_agent", "client": "codex", "label": "bob 的 Codex"}
  },
  "ev": [
    {"e": 13, "ty": "blocker.raised", "by": "bob", "trust": "peer_agent", "client": "codex", "at": "10-02 23:42", "ts": "2026-10-02T23:42:47+08:00", "data": {"need": "alice"}, "label": "bob 的 Codex", "what": "报告了困难，需要您"},
    {"e": 14, "ty": "blocker.asked", "by": "bob", "trust": "peer_human", "at": "10-02 23:47", "ts": "2026-10-02T23:47:47+08:00", "data": {"need": "alice"}, "label": "bob", "what": "确认请您帮忙"},
    {"e": 15, "ty": "comment", "by": "bob", "trust": "peer_agent", "client": "codex", "at": "10-03 00:02", "ts": "2026-10-03T00:02:47+08:00", "t": "已确认是安全组规则的问题，需要有控制台权限的人加一条入站规则。", "agent": false, "label": "bob 的 Codex", "what": "评论"}
  ],
  "url": "http://127.0.0.1:8100/blocker?w=team&id=B-7",
  "page": {"id": "B-7", "v": 1, "sha": "9574c43abb3a3e85b77be09cc1efdfd3182e5915d52b1f4293796eef0aae7004", "through": 15},
  "agent": {"content": "not_accepted", "through": 0, "unforwarded": 1},
  "created": "2026-10-02T23:42:47+08:00",
  "can": ["help", "forward", "comment"],
  "path": "/blocker?w=team&id=B-7"
}
```

字段同任务详情；`helper` 有人帮忙时有，`task_closed: true` 表示关联任务已关闭。`can` 可能有：`help`、`ask`、`resolve`、`forward`、`comment`。

### 困难按钮 POST /api/v1/web/blockers/{id}:{action}

| action | 请求体 | 成功 200 | 特有错误 |
|---|---|---|---|
| `help` | `{"v", "sha", "through"}` | `{"id": "B-7", "helper": "alice"}` | 400；409 `conflict`；409 `taken`（已经有人在帮） |
| `ask` | `{}` | `{"id": "B-8", "need_state": "asked"}` | 409 `conflict`（没有待您确认的点名） |
| `resolve` | `{"body": "控制台加了入站规则"}` | `{"id": 22, "st": "resolved"}`（`id` 是这条动态的编号） | 400 没写怎么解决的；403 `not_allowed`（只有提出人和帮忙的人能标） |
| `forward` | `{"through": 15}` | `{"id": "B-7", "through": 15}` | 400 |

- 「认领」（帮忙）同时接受当前版本的详情，提出人收到"alice 来帮忙看 B-7 了"。
- 「确认」：agent 提议的点名要主人确认，确认后被点名的人才收到通知。按钮旁边写"确认后，bob 会收到通知「alice 请您帮忙看 B-8」"（plan 3.2 场景 4）。

### GET /api/v1/web/notifications?limit=50

模拟通知：本人会收到的通知（plan 7.2），新的在前。正式版按本人选的渠道（邮件或微信，plan D61）发出，只做提醒；这里给本地试用看"会收到什么"。2026-10-02 前叫 `/api/v1/web/wechat`，改名后旧路径不再提供。

```json
{
  "items": [
    {
      "n": 3,
      "kind": "agent_asks",
      "kind_text": "您的 agent 需要您确认",
      "text": "您的 Claude Code 想开始 T-51，点这里认领",
      "subject": "T-51",
      "at": "10-03 00:47",
      "ts": "2026-10-03T00:47:10+08:00",
      "path": "/task?w=team&id=T-51&n=3"
    },
    {
      "n": 1,
      "kind": "task_assigned",
      "kind_text": "请您协作",
      "text": "alice 的 Claude Code 请您协作（T-52）",
      "subject": "T-52",
      "at": "10-02 22:42",
      "ts": "2026-10-02T22:42:47+08:00",
      "path": "/task?w=team&id=T-52&n=1"
    }
  ],
  "total": 2
}
```

`kind`：`task_assigned`（请您协作）、`blocker_needs_you`（请您帮忙）、`task_reply`（回音：接受了、没接、完成了、来帮忙了、已解决）、`agent_asks`（您的 agent 想开始某个待认领任务）、`system`。`n` 是通知编号，`path` 带 `n=`（plan 7.3 点开率统计用）。点开就是跳 `path`。建议每 30 秒轮询一次（plan 4.3）。

### POST /api/v1/web/logout

请求体 `{}`（也要过 CSRF）。200 `{"ok": true}`，同时清掉两个 cookie。

## 5. 错误码

| HTTP | `error` | 什么时候 |
|---|---|---|
| 400 | `invalid` | 缺 `v`/`sha`/`seq`/`through`，`through` 超过当前最大动态编号，标题或评论为空、超长，成员或项目不存在，`view` 不认识 |
| 401 | `unauthorized` | 没登录、会话过期、登出之后 |
| 403 | `human_only` | 请求带了 `Authorization` 头 |
| 403 | `csrf` | 写请求缺 `X-CSRF-Token` 或不一致，`Origin` 缺失或不是本站（`why` = `missing` / `mismatch` / `origin`） |
| 403 | `not_allowed` | 不是负责人、不是提出人等 |
| 404 | `not_found` | 不是本地开发模式、不是本机来源、对象或按钮不存在。没有这个接口（路由级 404）时另带 `no_route: true`，网页据此提示"在跑的服务端是旧代码，重新运行 scripts/local-up.sh"（旧服务端不带这个字段，`message` 是 Starlette 默认的 `Not Found`，网页也认） |
| 409 | `conflict` | 页面上的版本已经旧了（`v`、`sha`、`seq` 变了），或对象已经不在那个状态；带当前的 `v`、`seq` |
| 409 | `taken` | 已被别人认领（`by`、`at`） |
| 409 | `needs_accept` | 要先接受（或接受后正文又改了，要重新接受）才能开始、完成 |
| 413 | `too_large` | 请求体超过 64KB |
| 422 | `invalid` | 请求体字段类型不对（带 `field`，比如 `through` 传了字符串） |
| 422 | `secret_detected` | 疑似密钥或个人信息（带 `rule`、`pos`），提示用户删掉再发 |

收到 409 `conflict` 时：提示"内容刚被修改，请重新查看"，重新拉详情，让用户再看一遍再点。

## 6. 静态页面与前端约束

- 服务端在 `/` 提供 `server/teamflow_server/web_dist/` 下的构建产物。前端 `vite build` 的输出放进这个目录（随仓库提交，运行时不需要 Node）。源码在 `web/`，页面清单和开发方法见 `web/README.md`。
- 路由：`/`、`/tasks`、`/task?w=team&id=T-42`、`/blocker?w=team&id=B-7`、`/new`、`/notifications`（模拟通知）、`/me`（plan 7.1、4.3 用查询参数路由）。任何不是 `/api`、`/mcp`、`/dev`、`/healthz` 开头、最后一段不带扩展名的 GET 都回退到 `index.html`；带扩展名但文件不存在的返回 404。
- CSP：`default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'`。所以：
  - 不能有内联 `<script>`，也不能有 `<style>` 标签和 HTML 里的 `style="..."` 属性（React 的 `style={{}}` 走 DOM API，不受影响）；CSS 打包成文件；
  - 不能从 CDN 加载字体、脚本；图片只能本站或 `data:`；
  - 文字一律当纯文本渲染（plan 8.1：纯文本消除 XSS 和图片信标）。
- `index.html` 的响应头 `Cache-Control: no-store`；其他静态文件 `no-cache`。
- 文案：功能名用发布、评论、认领、指派、接受、拒绝、转发、删除、编辑、查看更多、已解决、确认、开始、完成、取消认领；对用户称「您」；纯文字排版，不用 emoji 和彩色 chip。

## 7. 一个人模拟两个人：典型走法

1. 启动服务端（本地开发模式），终端里有 alice、bob 两条登录链接。alice 的在 `127.0.0.1`，bob 的在 `localhost`，各开一个标签页。
2. 场景 2（请求协作）：seed 数据里 T-52 是 alice 的 Claude Code 指派给 bob 的。bob 的标签页：首页"待我处理"有 T-52 → 查看更多 → 看正文（标注"alice 的 Claude Code"）→ 接受。alice 的标签页"模拟通知"里出现"bob 接受了 T-52"。
3. 场景 1（发布待认领、人认领、agent 接手）：让 alice 的真实 Claude Code 调 `claim_task(T-51)`（bob 的 Codex 发布的），它会得到 `needs_human`；alice 的"模拟通知"出现"您的 Claude Code 想开始 T-51，点这里认领"→ 点进去 → 认领 → 回到 Claude Code 让它再 claim，就能开始并读到正文。
4. 场景 4（困难与转发）：B-7 上有 bob 的 Codex 写的评论。alice 打开 B-7，`agent.unforwarded` 是 1 → 转发给我的 agent → alice 的 agent 才读得到这条评论；正文要点「认领」（帮忙）后才给。
