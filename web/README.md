# Team Flow 网页（本地试用版）

浏览器里以成员本人的身份登录：接受、拒绝、认领、转发、确认点名、帮忙这些只有人能做的事在这里点。
Vite + React + TypeScript 单页，不用 UI 组件库，手写 CSS；手机优先，宽屏时居中一列 480px。

**用的人不需要 Node。** 构建产物在 `server/teamflow_server/web_dist/`，随仓库提交，服务端直接在 `/` 提供。
只有改前端的人才需要 Node（22.12 以上）和这个目录。

接口契约见 `docs/web-api.md`，页面要求见 `docs/plan.md` 7.1、7.2。

## 页面

| 路由 | 页面 | 按钮 |
|---|---|---|
| `/` | 首页：待我处理（待接受、请我帮忙、我的 agent 提议的点名、待转发、回音）、困难（按卡住时长）、大家在做什么、项目计数 | 只有「查看更多」，列表上不放「接受」 |
| `/tasks?view=pool\|doing\|mine\|all` | 任务：待认领 / 进行中 / 我的 / 全部 | 发布、查看更多、加载更多 |
| `/task?w=team&id=T-52` | 任务详情：清洗后的纯文本正文（和 agent 拿到的一致）、作者标注、风险高亮、全部动态和评论（标作者类别、标您的 agent 能不能读到） | 接受、拒绝（必填原因）、认领、开始、完成、取消认领、转发给我的 agent、评论 |
| `/blocker?w=team&id=B-7` | 困难详情：卡在哪、已经试过什么、需要谁、谁在帮、评论 | 认领（来帮忙）、确认（agent 提议的点名）、已解决（必填怎么解决的）、转发给我的 agent、评论 |
| `/new` | 发布：标题、内容（选填）、指派给（留空就是待认领）、项目、紧急 | 发布 |
| `/notifications` | 模拟通知：正式版按各人选的渠道（邮件或微信）发出的通知，点「详情」打开对应页面；导航上带未读数 | 详情 |
| `/me` | 我是谁、登录到期时间、怎么换人（例子优先挑 `scripts/sim-teammate.py` 能模拟的队友，即 `/me` 里带 `agent` 的成员；一个都没有时挑第一位队友） | 登出 |

顶部一直显示"您现在是 bob"和"本地试用"；没登录、登录过期、服务端不是本地开发模式时，各有一页说清楚怎么办。

## 几条硬要求怎么落实的

- **人类动作带页面渲染时看到的值。** 接受带 `v`、`sha`、`seq`、`through`，认领和帮忙带 `v`、`sha`、`through`，转发带 `through`，
  拒绝带 `seq` 和原因，全取自当前显示的那份详情的 `page`（`src/pages/TaskDetail.tsx`、`BlockerDetail.tsx`）。
- **409 时提示"内容刚被修改，请重新查看"并刷新。** `src/components/useDetail.ts`：任何 409 都重新拉详情；
  `conflict` 一律用这句话，`taken`、`needs_accept` 用服务端的说法。
- **30 秒轮询不偷换内容。** 详情页每 30 秒刷新：版本（`v`、`sha`、`seq`）没变就直接换上新数据（新评论会出现，`through`
  跟着显示的走）；版本变了只提示"内容刚被修改，请重新查看"，点「重新查看」才换。页面在后台时暂停轮询。
- **防误点。** 正文超过 800 字时，正文末尾的标记进入视野之前，按钮不能点（`src/components/ReadToEnd.ts`）；
  内容换了版本要重新看到底。
- **风险高亮**（`src/risk.ts`，不依赖 LLM）：`~/.ssh`、`.aws`、`.env` 和环境变量、token / 密码 / 密钥、`curl … | sh`、
  `rm -rf`、48 位以上的编码串、外部网址、"忽略 / 无视…指令"。只提示，不拦截；密钥和个人信息由服务端拦（422）。
- **纯文本渲染。** 所有文字由 React 当文本输出，没有 `dangerouslySetInnerHTML`；符合服务端的 CSP（`script-src 'self'`、
  `style-src 'self'`，没有内联脚本和内联样式）。
- **错误说人话**（`src/api.ts` 的 `humanMessage`）：401 告诉您在终端运行 `scripts/login-link.sh`，403 csrf 让您刷新，
  422 疑似密钥只说位置，连不上服务端时提示确认 `scripts/local-up.sh` 还在运行。
- **文案**：功能名用发布、评论、认领、指派、接受、拒绝、转发、查看更多、已解决、确认、开始、完成、取消认领；
  对用户称「您」；不用 emoji 和彩色标签。展开的输入框用「收起」关上，不用「取消」，免得和「取消认领」挨在一起看错。
  不提具体通知渠道：按钮旁边写"bob 会收到通知「…」"，不写"收到微信"；通知按各人选的渠道（邮件或微信）发，
  只在「模拟通知」页的说明里提一次（plan D54、D60、D61）。

## 开发

```bash
cd web
npm ci
npm run dev        # http://127.0.0.1:5173，接口转给 http://127.0.0.1:8100（TEAMFLOW_WEB_BACKEND 可改）
npm run build      # tsc 检查 + 构建到 ../server/teamflow_server/web_dist/（产物要提交）
npm test           # vitest：接受带版本、409 提示、轮询不偷换内容、拒绝必填、长正文、风险高亮、错误说法、模拟通知、换人的例子
npm run e2e        # Playwright：起一个本地开发模式的服务端，用 iPhone 尺寸走一遍典型场景
npm run shots      # 同上，另外逐页截图到 ../docs/local-trial-shots/
```

`npm run dev` 时登录：先用 `scripts/local-up.sh` 起服务端，打开它给的登录链接（`http://127.0.0.1:8100/dev/login?...`）点「登录」，
再打开 `http://127.0.0.1:5173`。cookie 按主机名、不按端口区分，所以两边是同一个登录。

`npm run e2e` / `npm run shots`：

- 端口用 `TF_E2E_PORT`（缺省 8302）。端口被占用就退出，不会去结束别人的进程；服务端是脚本自己起的子进程，结束时只关它。
- 服务端用仓库的 `.venv` 或 `.local/venv` 里的 Python（`TF_PY` 可指定），状态目录是临时目录，跑完删除。
- 令牌和登录码都在运行时随机生成；登录码直接调 `teamflow_server.devlogin.issue`，代替"您自己的终端"。
- 需要 Playwright 的 Chromium（`npx playwright install chromium`；已经装在别处就设 `PLAYWRIGHT_BROWSERS_PATH`）。
- 每页都自查：横向溢出、被截断的文字、矮于 32px 或被挡住点不到的按钮；最后在 320px 宽的屏幕上再查一遍。

## 目录

```text
src/
  api.ts              接口客户端、CSRF、错误变人话
  router.ts           查询参数路由（/task?w=team&id=T-52）
  hooks.ts            30 秒轮询
  labels.ts           作者标注、作者类别、中文排版的空格
  risk.ts             风险高亮规则
  components/         详情页共用：useDetail（版本、409、提示）、ReadToEnd（防误点）、Events、Forms、RiskText、Notice
  pages/              首页、任务、任务详情、困难详情、发布、模拟通知
tests/                vitest（jsdom）
e2e/run.mjs           Playwright 端到端 + 截图
```
