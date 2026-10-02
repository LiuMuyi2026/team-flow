# Team Flow 开发约定

团队 agent 协作台：人和 Claude Code / Codex 共用的任务、进度、困难与协作请求云服务。
规划全文在 `docs/plan.md`，是需求和决策的唯一来源；改动设计前先改那里的决策记录。

## 目录

- `server/`：FastAPI 单体，`/api/v1` REST（权威接口）+ `/mcp/` 远程 MCP（FastMCP，无状态，兼容 2025-06-18 与 2026-07-28 两代协议）
- `cli/`：`teamflow` 命令行，同时是 Claude Code / Codex 的 hook 执行体、MCP 凭据 helper 和兜底命令
- `spike/`：M0 可行性验证脚本与结果，结论汇总在 `docs/m0.md`
- `docs/`：规划与验证记录

## 技术约定

- Python ≥ 3.11（生产 3.12），用 uv 管理依赖；测试用 pytest。
- 本地服务端口 8100；e2e 地址用 `TEAMFLOW_E2E_BASE` 指定。机器上别的端口（如 8000）可能被其他项目占用，不要杀别人的进程。
- 技术标识 `teamflow` 已冻结：hook 命令串、MCP server 名、token 前缀 `tf_pat_` 发布后永不改（改了 Codex 要全员重新信任 hooks）。行为变化只放进 CLI 包。
- hook 快速路径只用标准库，冷启动不超过 80ms；永远 fail-open（出错不输出、exit 0）。
- 不要在开发机或容器里改真实的 `~/.claude`、`~/.codex` 配置做实验；用 `--settings`、`--mcp-config`、临时目录。

## 安全硬规则（服务端强制，任何设置都不能改）

1. 所有 PAT 都按 agent 记账；接受、拒绝、转交、转发、认领他人任务等人类动作只认人类网页会话，并且每次都要一次绑定该动作的通行密钥断言（`docs/plan.md` 8.2 H1–H3、D54–D56）。PAT 一律返回 403 `human_only`。微信和邮件只是通知渠道，不授予任何权限。本地试用的一次性登录只在 `TEAMFLOW_DEV_ENDPOINTS=1` 且来自本机时可用，生产配置下返回 404。
2. 他人写的正文要本人接受后才给本人的 agent；他人 agent 写的评论类文字要本人转发后才给。
3. hooks、通知、AGENTS.md 只放 ID、计数、handle 和枚举值；注入文字由 CLI 内置模板生成，服务端只返回结构化数据。
4. 正文类写入命中密钥或个人信息扫描返回 422；工具名、工具描述、server instructions 都是常量，永不拼接用户内容。
5. 鉴权、限流、确认都实现在 HTTP 层，不只在 MCP 层（agent 可以绕过 MCP 直接 curl）。

## 文案约定

- 功能名用微信、朋友圈里大家已经熟悉的词：发布、评论、认领、指派、接受、拒绝、转交、转发、删除、编辑、查看更多。不自创叫法。
- 按钮上的词要通用，按钮旁边的话要像人说的；对用户称「您」。
- UI 纯文字排版，不用 emoji 和彩色 chip 装饰；icon 只在承载状态或功能语义时用。
