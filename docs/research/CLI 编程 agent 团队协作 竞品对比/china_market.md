# China market: AI coding agents and team collaboration around them (as of 2026-10-03)

Research notes. Many vendor and press sites, including most Chinese sites, were blocked by the egress proxy (HTTP 403 / no connect). The WebSearch budget also ran out partway through. Facts marked "(snippet)" come from search-result snippets only, because the page itself could not be opened. Treat those as medium or low confidence. GitHub pages, the npm registry, anthropic.com and code.claude.com could be read directly. npm data was pulled on 2026-10-03.

## Q1. Domestic coding agents (CLI/IDE) and their team features

### Takeaway
Every big Chinese vendor now ships an agentic IDE plus a terminal CLI that copies Claude Code: Tencent CodeBuddy Code, Alibaba Qoder / Qoder CN CLI / Qwen Code, Kimi Code, MiniMax Code, Zhipu ZCode and ByteDance TRAE SOLO. Their "team" features are almost all enterprise admin features: seats, pooled credits, SSO, audit and shared Skills. The one real "assign work to an agent and watch progress" product is **Tencent CodeBuddy NPC** (launched 2026-07-23). It is a cloud agent that you @mention inside Issues and PRs on Tencent's CNB platform, and it can run multi-role "NPC teams". None of these vendors offers a vendor-neutral board where several humans and their own local agents coordinate. The market is consolidating fast: iFlow CLI shut down, Tongyi Lingma became Qoder CN, Comate was folded into DuMate, and Kimi CLI was archived.

### Cited Findings

#### Market size and share
- IDC's China AI-coding market-share report (published around 2026-07-16) puts the 2025 market at RMB 399M, forecast to reach RMB 1.173B by end-2026. Shares: Alibaba (Qoder) 47.6%, Zhipu CodeGeeX 11.5%, SenseTime Raccoon 10.5%, Tencent CodeBuddy 6.9%, Baidu Comate 6.0%. Alibaba's share exceeds #2 to #5 combined. — [Sina Finance](https://finance.sina.com.cn/roll/2026-07-16/doc-inihyiyk1295527.shtml); [36Kr newsflash](https://36kr.com/newsflashes/3897689181243265); [STCN](https://www.stcn.com/article/detail/4022475.html) (snippets)
  - Note: this is paid domestic market share. It does not measure usage of foreign tools.

#### Tencent CodeBuddy (IDE, plugin, CLI "CodeBuddy Code"; NPC cloud agent)
- CodeBuddy comes in three forms: IDE, plugin and CLI. CodeBuddy Code (CLI) is aimed at DevOps, SRE and senior developers. — [Tencent Cloud docs](https://www.tencentcloud.com/document/product/1300/80639); [Baidu Baike EN](https://baike.baidu.com/en/item/CodeBuddy/1432154) (snippets)
- January 2026: CodeBuddy Code 2.0 added Plan Mode, ACP (Agent Client Protocol) support, an open SDK, an isolated sandbox and Skills. — [Baidu Baike EN](https://baike.baidu.com/en/item/CodeBuddy/1432154) (snippet)
- The CLI is very actively released. npm `@tencent-ai/codebuddy-code` was first published 2025-08-05. The latest version is 2.161.1 (2026-10-01), and there are 1,355 versions in total. — [npm registry](https://registry.npmjs.org/@tencent-ai%2fcodebuddy-code)
- Team Edition costs $40/seat/month or $480/seat/year. Each seat gets 1,000 credits/month, shared in a team pool. — [Tencent Cloud price details](https://www.tencentcloud.com/document/product/1256/77270) (snippet)
- The Enterprise Edition lists 20+ capabilities, including Tencent unified identity authentication, R&D-efficiency measurement, security audit, and hosting and distribution of organizational knowledge assets. — [Baidu Baike EN](https://baike.baidu.com/en/item/CodeBuddy/1432154) (snippet)
- **CodeBuddy NPC** was released 2026-07-23. It is a cloud R&D agent running on Tencent's CNB (Cloud Native Build) platform. You invoke it in an Issue, PR or comment with `@NPC` "like mentioning a colleague". It plans the work, writes the code, opens the PR, runs the tests and self-fixes from CI results. It works alongside existing Git, build and TAPD tooling, so tasks can be "dispatched to NPC within the original workflow". — [IT之家](https://www.ithome.com/0/980/633.htm); [Sina Tech 2026-07-23](https://finance.sina.com.cn/tech/digi/2026-07-23/doc-iniiuskx1439418.shtml); [InfoQ CN](https://www.infoq.cn/article/w6DHDb3QUYPLC1vaU8z1); [AIbase](https://news.aibase.com/news/29840) (snippets)
- NPC supports multi-role "NPC Teams". In Tencent's demo, a Project-Manager NPC broke down requirements and assigned tasks to scripting, art, music and voice NPCs, and Code-Review and Test NPCs did the final verification. Tencent also says first-round token use fell by more than 90% (about 20,000 tokens down to about 2,000). — [163/网易](https://www.163.com/dy/article/L2HI90JF0511B8LM.html); [AIbase](https://news.aibase.com/news/29840); [BigGo Finance](https://finance.biggo.com/news/11712f69-5132-44f7-82e9-507c397365e7) (snippets)
- CodeBuddy's international version quietly removed Claude models before 2025-10-01. — [Sina Finance 2025-11-05](https://finance.sina.com.cn/roll/2025-11-05/doc-infwisms9490043.shtml); [Lanjinger](https://www.lanjinger.com/d/1762306186514657180) (snippets)

#### ByteDance TRAE (TRAE CN vs TRAE international; SOLO)
- "The New SOLO" was announced as a beta on the TRAE blog. The post slug ends in "0331", and third-party reviews date the new SOLO to March/April 2026; the year was not confirmed on the page itself. **Beta.** — [trae.ai blog](https://www.trae.ai/blog/new_solo_beta_0331) (title/snippet only); [TRAE review (third-party)](https://aiagentsquare.com/agents/trae)
- TRAE CN (the China edition) opened SOLO free to all users (late 2025). It includes SOLO Coder, Plan mode, parallel multi-tasking, DiffView and context compression. The China edition has only SOLO Coder with no integrated deployment. The international edition has Builder + Coder and integrates more services. — [阮一峰 2025-11](https://www.ruanyifeng.com/blog/2025/11/trae-solo.html); [Volcengine developer community](https://developer.volcengine.com/articles/7598410727946682418); [TRAE CN official FAQ](https://forum.trae.cn/t/topic/53) (snippets)
- TRAE Enterprise SOLO supports Skills. These let a company package its internal coding standards, test flows and deployment standards so SOLO follows them. — [Zhihu](https://zhuanlan.zhihu.com/p/2004590797450921359) (snippet)
- TRAE's 2025 annual report (2025-12-26): 6M registered users in about 200 countries and 1.6M MAU. In China, about 3 in 10 users use SOLO. — [CSDN](https://www.csdn.net/article/2025-12-26/156311742); [Sohu](https://www.sohu.com/a/970562408_211762) (snippets)
  - A claim of 12M users after TRAE 2.0 comes from a low-quality review site and is unverified. — [aitoollab](https://www.aitoollab.cn/articles/trae-2-0-solo-agent-deep-review-202606/)
- ByteDance banned third-party AI coding tools internally from 2025-06-30, including Cursor and Windsurf, and replaced them with TRAE. Reasons given: data in personal accounts, and tools such as Claude "not formally served in China". More than 80% of internal engineers had adopted TRAE. — [Tencent News](https://news.qq.com/rain/a/20250528A0508A00); [Sina](https://finance.sina.com.cn/wm/2025-05-28/doc-ineyayzf0648667.shtml) (snippets)
- TRAE international told users by email on 2025-11-04 that Claude models were removed. It now offers GPT-5, GPT-4.1, Gemini-2.5-Pro and Grok-4. TRAE CN uses Doubao-Seed-1.6, Qwen-3-Coder, Kimi-K2 and others. — [Guancha](https://www.guancha.cn/economy/2025_11_06_796015.shtml); [Sina](https://finance.sina.com.cn/roll/2025-11-05/doc-infwisms9490043.shtml) (snippets)
- Team features: third-party reviews say the free plan has no team collaboration and paid plans (from about $7.5/month) add it. **Low confidence; no official source seen.** — [aiagentslist](https://aiagentslist.com/agents/trae); [aigearbase](https://aigearbase.com/tool/trae)

#### Alibaba: Qoder / Qoder CN (formerly Tongyi Lingma), Qwen Code, iFlow CLI (shut down)
- Qoder is an agentic coding platform: desktop IDE, CLI and JetBrains plugin. It can bill through Alibaba Cloud Model Studio pay-as-you-go, Coding Plan, Token Plan Personal or **Token Plan Team**. — [Alibaba Cloud docs](https://www.alibabacloud.com/help/en/model-studio/qoder-agent)
- **Qoder Teams** launched 2025-12-15 with team management and resource sharing. It is reported at $40/seat for 3,000 credits, with SSO, an admin dashboard and centralized billing. — [Baidu Baike EN](https://baike.baidu.com/en/item/Qoder/1427525); [StackPick](https://stackpick.net/tools/qoder/) (snippets; third-party for pricing)
- Qoder "Expert Mode" reportedly assembles a team of AI specialists (frontend, backend, QA) working in parallel. "Quest Mode" is the autonomous mode. — [ToolCenter](https://www.toolcenter.ai/en/articles/qoder-review-2026) (snippet; third-party)
- **Tongyi Lingma was renamed "Qoder CN" at 23:00 Beijing time on 2026-05-20.** Billing moved to credits, and the personal Pro tier went from free to RMB 59/month. The product line is now "1+3": Qoder CN (coding), QoderWork CN (office), Qoder CN CLI and Qoder CN Mobile. — [Alibaba Cloud developer community](https://developer.aliyun.com/article/1740785); [Sina](https://k.sina.cn/article_7524305485_1c07bca4d00101hcoi.html); [CSDN](https://blog.csdn.net/hanzhixintianxia/article/details/161263361); [Alibaba Cloud help: Qoder CN 系列 (Lingma)](https://help.aliyun.com/zh/lingma/product-overview/introduction-of-lingma) (snippets)
- Qoder CLI on npm: `@qoder-ai/qodercli` was first published 2025-09-24. The latest is 1.1.65 (2026-09-30). — [npm registry](https://registry.npmjs.org/@qoder-ai%2fqodercli)
- **Qwen Code** is an open-source CLI (Apache-2.0) with 28.3k stars and 3.2k forks. It supports OpenAI, Anthropic, Gemini and Qwen API protocols as well as local models. It advertises Auto-Memory, Auto-Skills, SubAgents, "Agent Teams", MCP, VS Code/JetBrains/Zed plugins and headless mode. — [GitHub QwenLM/qwen-code](https://github.com/QwenLM/qwen-code). The latest npm version is 0.24.7 (2026-09-29). — [npm registry](https://registry.npmjs.org/@qwen-code%2fqwen-code)
- The free Qwen OAuth tier for Qwen Code (formerly 2,000 requests/day) was discontinued on 2026-04-15. Users now need an API key or a coding plan such as Alibaba Cloud Coding Plan. — [InventiveHQ](https://inventivehq.com/blog/qwen-code-still-free-2026-shutdown); [Qwen Code auth docs](https://qwenlm.github.io/qwen-code-docs/en/users/configuration/auth/) (snippets)
- **iFlow CLI** (Alibaba 心流, once called "China's Claude Code" and free) stopped maintenance on 2026-03-20. The iFlow API and model services shut down on 2026-04-17, and users were invited to migrate to Qoder. — [iFlow community letter](https://vibex.iflow.cn/t/topic/4819); [Zhihu](https://zhuanlan.zhihu.com/p/2026252828843230993) (snippets). The last npm release, 0.5.19, is dated 2026-04-25. — [npm registry](https://registry.npmjs.org/@iflow-ai%2fiflow-cli)

#### Baidu Comate (文心快码) → folded into DuMate (百度搭子)
- Comate runs a multi-agent setup (Zulu / Plan / Architect). It also has "AgentS (team coordination)" and the Comate Agent Hub, which manages Agents, Plugins, Skills, MCP, Rules and Commands. — [Juejin](https://juejin.cn/post/7656414036670087168) (snippet; third-party)
- On 2026-09-07 Comate was merged into DuMate (百度搭子), Baidu's general agent platform, as a core capability module. Comate is said to serve more than 10M developers. By end-2025, AI-generated code at Baidu reportedly exceeded human-written code. — [Sina Tech](https://finance.sina.com.cn/tech/2026-09-07/doc-iniqyvrz0383318.shtml); [Tencent News](https://news.qq.com/rain/a/20260907A0AUKO00) (snippets)

#### Zhipu (CodeGeeX, ZCode, GLM Coding Plan)
- **GLM Coding Plan has team and enterprise tiers:**
  - Team edition: self-service, with organization management, enterprise data security and centralized billing. — [Zhipu docs: 团队版权益](https://docs.bigmodel.cn/cn/coding-plan/team) (snippet)
  - Enterprise edition: launched 2025-10-21 (on GLM-4.6). — [Zhipu release notes](https://docs.bigmodel.cn/cn/update/new-releases) (snippet)
- GLM Coding Plan subscriptions "returned" on a transparent points system starting at RMB 118/month. Annual and quarterly discounts ran until 2026-08-15. — [IT之家](https://www.ithome.com/0/983/934.htm) (snippet)
- ZCode, Zhipu's own harness for GLM, added Goal, Subagents, **Remote Control** and idle tasks. — [163/网易](https://www.163.com/dy/article/L42CPLTJ0511B8LM.html) (snippet)
- GLM-5.3 launched 2026-08-14 in Coding Plan and ZCode, with 1M-token context. — [51allai](https://51allai.com/posts/2026/08/zhipu-glm-53-coding-plan/) (snippet)

#### Moonshot (Kimi Code / Kimi CLI)
- The original **Kimi CLI** (MoonshotAI/kimi-cli, 11.4k stars, Apache-2.0) was archived on 2026-09-23. Its replacement is **Kimi Code CLI** (MoonshotAI/kimi-code): 7.8k stars, MIT, single binary. Kimi Code CLI features:
  - ACP for Zed/JetBrains
  - MCP
  - subagents (coder / explore / plan)
  - lifecycle hooks ("for automation and notifications")
  - video input
  - login via Kimi Code OAuth or a Moonshot API key

  — [GitHub kimi-cli](https://github.com/MoonshotAI/kimi-cli); [GitHub kimi-code](https://github.com/MoonshotAI/kimi-code)
- **On 2026-07-19 Kimi paused new consumer subscriptions because of a compute shortage after the K3 launch.** New signups were still closed in late August. Moonshot plans to split Kimi main benefits from Kimi Code benefits for future subscribers. — [36Kr](https://36kr.com/p/3903312040052611); [Guancha 2026-07-21](https://www.guancha.cn/economy/2026_07_21_824589.shtml); [Moonshot statement on Zhihu](https://zhuanlan.zhihu.com/p/2062309593640866843) (snippets)
- Kimi Code plan pricing conflicts between sources:
  - Free / Go RMB 49 / Plus 99 / Pro 199 / Max 699 per month, with use from "Kimi CLI / Claude Code / Roo Code". — [codingplan.org](https://codingplan.org/en/plans/kimi) (third-party)
  - Contradicted by Moderato RMB 99 / Allegro RMB 699. — [wmpeng/codingplan](https://github.com/wmpeng/codingplan)
- K2.7-Code model targets token efficiency in agentic coding. — [DevOps.com](https://devops.com/moonshot-ais-kimi-k2-7-code-targets-token-efficiency-in-agentic-coding/) (snippet)

#### MiniMax, DeepSeek, others
- MiniMax open-sourced the **MiniMax Code CLI** in September 2026 (v0.4.12, MIT). It has a TUI, headless mode for CI and ACP, and accepts bring-your-own API keys or third-party endpoints. The desktop app is separate and closed. — [TechNode 2026-09-21](https://technode.com/2026/09/21/minimax-open-sources-minimax-code-terminal-coding-agent/); [GitHub MiniMax-AI/minimax-code docs](https://github.com/MiniMax-AI/minimax-code/blob/main/docs/installation.md) (snippets)
- DeepSeek has no first-party CLI agent (none found). Instead it documents running Claude Code against its Anthropic-compatible endpoint `https://api.deepseek.com/anthropic` (e.g. model `deepseek-v4-pro`). — [DeepSeek API docs](https://api-docs.deepseek.com/quick_start/agent_integrations/claude_code/) (snippet)
- SenseTime Raccoon (商汤小浣熊) holds 10.5% paid share per IDC (see above). No team-feature details were researched.

### Inferences
- **Who has multi-person collaboration, task assignment or agent progress visibility?**
  - Only CodeBuddy NPC truly does: Issue/PR-driven assignment, progress through PR and CI, and multi-role agent teams. But it is cloud-run and tied to Tencent CNB/TAPD.
  - Qoder Teams, TRAE Enterprise, GLM Coding Plan Team and CodeBuddy Team/Enterprise are seat, billing, SSO, audit and shared-Skills products. There is no evidence of a shared human+agent task board.
  - Qwen Code "Agent Teams", Comate "AgentS" and Qoder "Expert Mode" are one user's agent swarm, not multi-human coordination.
- Chinese CLIs widely support **ACP** (CodeBuddy Code 2.0, Kimi Code, MiniMax Code) and **MCP** (all of them). A Longtable integration built on MCP tools works across most of them. Hooks-based auto-reporting is confirmed only for Claude Code and Kimi Code here; other CLIs' hook support was not verified (see Gaps).
- Churn risk is high: iFlow was shut down, Kimi CLI archived, Lingma renamed, Comate merged, and Kimi and Zhipu froze new signups. A board that pins to one domestic vendor is fragile. Vendor neutrality, which is Longtable's stance, fits the China market.

### Gaps
- No official, readable source for TRAE's team or collaboration plan contents. Third-party reviews only.
- Qoder Teams' collaboration semantics are unclear beyond admin and billing: shared sessions? task handoff?
- Whether CodeBuddy Code, Qoder CLI, Qwen Code or MiniMax Code support Claude-Code-style lifecycle hooks (needed for auto-reporting) was not verified.
- CodeBuddy NPC pricing and availability outside the CNB platform (e.g. GitHub) were not found.
- Current authoritative coding-plan prices: snapshots conflict (early-2026 comparison articles vs the 2026-09-24 wmpeng table) and official pricing pages were blocked.

## Q2. Collaboration platforms adding agents (Feishu/Lark, DingTalk, WeCom/WeChat, CODING/CNB, TAPD, Gitee, PingCode/Worktile, Teambition)

### Takeaway
**Feishu (ByteDance) is furthest along.** Its official CLI, "built for humans and AI Agents", has 17.5k stars and ships 26 Agent Skills. Alongside it are an official OpenAPI MCP, an official Meegle (Feishu Project) CLI, and an open email-based agent task protocol, **AAMP**, with task.dispatch / ack / help_needed / result intents. Feishu Project explicitly repositions itself as a "human + Agent collaborative action system" (2026-04-23). The aily agent, renamed 豆包工作伙伴 on 2026-08-13, can take tasks and report progress in chat. DingTalk open-sourced a CLI that natively targets Claude Code and Qoder. WeCom and personal WeChat offer official bot channels with long connections, so no public IP is needed. Personal WeChat is limited to 1:1. Gitee and TAPD have MCP servers. Tencent CODING is being shut down in favour of CNB + TAPD. Hooking Claude Code or Codex into Feishu, DingTalk or WeCom chats is a large community genre: cc-connect (15.7k stars) and lark-coding-agent-bridge (2.6k stars, featured on Feishu's own site).

### Cited Findings

#### Feishu / Lark (ByteDance)
- On 2026-03-19 Feishu released several enterprise Agents, covering personal 智能伙伴 (personal agents) and business systems. — [QbitAI](https://www.qbitai.com/2026/03/389311.html); [Xinhua](http://www.news.cn/tech/20260319/e76a237bb21645b6a6f9ced193222cdd/c.html) (snippets)
- Feishu aily is renamed **豆包工作伙伴** from 2026-08-13.
  - Employees can give it tasks in Feishu chat, add requirements and check progress.
  - Custom aily agents can remember project progress, assign tasks to employees and generate periodic project reports.

  — [aily / 豆包工作伙伴](https://aily.feishu.cn/); [Feishu help](https://www.feishu.cn/hc/zh-CN/articles/790732948604-%E5%BF%AB%E9%80%9F%E4%BA%86%E8%A7%A3%E8%B1%86%E5%8C%85%E5%B7%A5%E4%BD%9C%E4%BC%99%E4%BC%B4); [Feishu article](https://www.feishu.cn/content/article/7631864469689240764) (snippets)
- **Feishu Project (飞书项目, international name Meegle) Ecosystem Day, Shanghai, 2026-04-23.** Releases:
  - new MCP capabilities
  - an open-sourced **Feishu Project CLI** "to help individuals or AI tools access and operate Feishu Project data"
  - AI assistant and AI apps
  - the open **AAMP** protocol

  Stated direction: move project management from "recording and tracking" to a "**human + Agent collaborative action system**". — [QbitAI](https://www.qbitai.com/2026/04/406026.html); [InfoQ CN](https://www.infoq.cn/article/ub0bHyfIRpbO61I876k2); [China.com](https://m.tech.china.com/redian/2026/0423/042026_1853950.html); [Tencent News](https://news.qq.com/rain/a/20260428A05T5100) (snippets). Feishu Project can also call MCP servers through its plugin system. — [Feishu Project help center](https://project.feishu.cn/b/helpcenter/1p8d7djs/73n2upf3) (snippet)
- **AAMP (Agent Asynchronous Messaging Protocol), larksuite/aamp:**
  - Built on SMTP (delivery), JMAP (sync/push/attachments) and `X-AAMP-*` headers.
  - Intents: `task.dispatch`, `task.ack`, `task.help_needed`, `task.result`, `task.cancel`, `task.stream.opened`.
  - Humans can answer `help_needed` by replying to the email.
  - It avoids NAT and inbound-webhook problems for local agents.
  - SDKs in Node, Python and Go. Bridges for ACP agents, CLIs and OpenClaw.

  Maturity: protocol v1.1, 121 stars. **Early.** — [GitHub larksuite/aamp](https://github.com/larksuite/aamp)
- **Official Lark/Feishu CLI** (larksuite/cli), tagline "Built for humans and AI Agents":
  - 17.5k stars.
  - 26 Agent Skills (IM, docs, base, sheets, calendar, tasks, approval, …).
  - User or bot identity via `--as`. DPoP on by default.
  - `im +messages-send --chat-id … --text …` for messages.
  - Warns about prompt-injection risk when agents act as the user.

  npm `@larksuite/cli` was first published 2026-03-28; the latest is 1.0.97 (2026-09-28). — [GitHub larksuite/cli](https://github.com/larksuite/cli); [npm registry](https://registry.npmjs.org/@larksuite%2fcli)
- Other official larksuite repos:
  - Lark OpenAPI MCP: 839 stars.
  - **Meegle CLI** ("manage work items" in Lark Project): 241 stars, updated 2026-09-24.
  - OpenClaw-Lark ("飞书官方出品的 OpenClaw 飞书/Lark Channel 插件", Feishu's official OpenClaw channel plugin): 2.4k stars.

  — [GitHub larksuite org](https://github.com/larksuite)
- **lark-coding-agent-bridge** (community, by zarazhangrui; 2.6k stars, 419 forks, MIT) is a Feishu/Lark bot that bridges a *local* Claude Code or Codex CLI.
  - Setup: scan a QR code to bind a PersonalAgent app.
  - Streaming cards; per-chat/topic/doc-comment-thread sessions.
  - Group use via @bot. Private by default, with `/invite user|group|admin`.
  - Message queueing; doc-comment integration.

  — [GitHub](https://github.com/zarazhangrui/lark-coding-agent-bridge). Feishu's official site published a tutorial titled "Claude Code/Codex 接入飞书教程：Lark Coding Agent Bridge 实践". — [feishu.cn](https://www.feishu.cn/content/article/7647408304896953549) (title via search; page blocked)
- Community Feishu MCP (cso1z/Feishu-MCP) covers docs and **Feishu task management**. It has MCP and CLI+Skill modes for Cursor and Claude Code. — [GitHub](https://github.com/cso1z/feishu-mcp) (snippet)

#### DingTalk (Alibaba) and Teambition
- **DingTalk CLI was open-sourced** (QbitAI, 2026-03) with a first batch of 10 core product capabilities. It treats AI as the first use case and natively supports Qoder, Claude Code and Cursor. — [QbitAI](https://www.qbitai.com/2026/03/392828.html) (snippet)
- open-dingtalk publishes `dingtalk-mcp` (26 stars) and Stream Mode bot SDKs (Python, Node, Java, Go). Stream Mode is described as easier than webhooks, with no public endpoint needed. — [GitHub open-dingtalk](https://github.com/open-dingtalk)
- Community examples of DingTalk bots driving Claude Code or Qoder CLI: [Alibaba Cloud developer article](https://developer.aliyun.com/article/1739514); [V2EX "把 Claude Code 装进钉钉"](https://www.v2ex.com/t/1221811) (snippets)
- Teambition (钉钉项目) AI uses Qwen and DeepSeek. It extracts tasks from chat, auto-assigns owners, batch-dispatches tasks, and writes weekly reports. These are human tasks. There is no evidence of coding-agent assignment or MCP. — [Alibaba Cloud developer article](https://developer.aliyun.com/article/1653150) (snippet)

#### WeCom / WeChat (Tencent)
- WeCom "智能机器人" (intelligent robot) offers an official WebSocket long connection (`wss://openws.work.weixin.qq.com`, 30s heartbeat). Credentials come from Admin console → 应用管理 → 智能机器人. Community relay clawrelay-wecom-server (19 stars) bridges this to Claude Code. — [GitHub](https://github.com/wxkingstar/clawrelay-wecom-server)
- **WeChat ClawBot** was launched by Tencent on 2026-03-22. It connects the user's own OpenClaw agent to WeChat as a *private 1:1* channel: others cannot add it and it cannot join groups. It needs WeChat Android 8.0.69 / iOS 8.0.70 or later. — [Zhihu](https://zhuanlan.zhihu.com/p/2019118125963059386); [CSDN](https://blog.csdn.net/youcans/article/details/158261361) (snippets). The installer `@tencent-weixin/openclaw-weixin-cli` was first published on npm 2026-03-21. — [npm registry](https://registry.npmjs.org/@tencent-weixin%2fopenclaw-weixin-cli)
- **cc-connect** (15.7k stars; v1.5.0 stable, v1.5.1-beta.1) bridges 10+ coding agents to 13 chat platforms. Agents include Claude Code, Codex, Cursor Agent, Gemini CLI, Qoder CLI, OpenCode, iFlow CLI, Kimi CLI and any ACP agent.
  - Feishu/Lark: WebSocket.
  - DingTalk: Stream.
  - WeCom: WebSocket or webhook.
  - Personal Weixin: iLink HTTP long-polling, 1:1 only.
  - Also WPS 协作, QQ and others.
  - Most need no public IP. Group support; `admin_from` for privileged commands.

  — [GitHub chenhg5/cc-connect](https://github.com/chenhg5/cc-connect); [README](https://raw.githubusercontent.com/chenhg5/cc-connect/main/README.md)
- weixin_claude_code is a WeChat Channel plugin for Claude Code: two-way messaging via MCP. — [GitHub](https://github.com/Dcatfly/weixin_claude_code) (snippet)

#### Tencent CODING → CNB + TAPD
- CODING DevOps is being retired:
  - new team registration stopped 2025-07-01
  - free standard edition ended 2025-09-01
  - new purchases stopped 2025-09-30
  - full shutdown 2028-09-30

  Successors: CNB for code, artifacts and CI/CD; TAPD for project collaboration. — [Tencent Cloud developer article](https://cloud.tencent.com/developer/article/2535421); [IT之家](https://www.ithome.com/0/838/632.htm); [蓝点网](https://www.landian.news/archives/109537.html) (snippets)
- TAPD (Tencent's agile management tool): MCP servers exist. One has 210 tools across 26 modules covering requirements, defects and iterations, including updating status, comments and assignee. They work with Claude Code and Cursor. There is also `tapd-ai-cli`, "a TAPD CLI built for AI Agents". These appear community-built; it is unclear whether any is official. — [GitHub xihe-lab/tapd-mcp-server](https://github.com/xihe-lab/tapd-mcp-server); [Tencent Cloud developer article](https://cloud.tencent.com/developer/article/2656683); [Tencent SkillHub listing](https://skillhub.cloud.tencent.com/mcp/mcp-server-tapd) (snippets)

#### Gitee, PingCode/Worktile
- Gitee has an **official MCP Server** (open source; first release reported March 2025) covering repos, Issues, PRs, comments, PR review and merge. Gitee blog posts:
  - "Gitee MCP Server For Enterprise" (2026-01-23)
  - remote hosted MCP needing no local deployment (2026-01-26)
  - a post dated 2026-01-22 on the official MCP

  — [Gitee blog 01-22](https://blog.gitee.com/2026/01/22/gitee-official-mcp-server-ai-code-repo/); [Gitee blog 01-23](https://blog.gitee.com/2026/01/23/gitee-enterprise-mcp-server-launch-ai-in-enterprise-rd-management/); [Gitee blog 01-26](https://blog.gitee.com/2026/01/26/gitee-mcp-support-remote-access-no-local-deployment-ai-assistant-plug-and-play/); [OSCHINA](https://www.oschina.net/news/338794/gitee-mcp-server) (snippets; release-date wording differs between sources)
- PingCode AI lists agents for task generation and review, workflow management, knowledge management and team culture. — [PingCode AI](https://pingcode.com/ai) (snippet)

### Inferences
- Feishu Project's "human + Agent" positioning and AAMP's dispatch / ack / help_needed / result vocabulary map closely onto Longtable's assign / claim / ask-for-help / done. This validates the concept in China. It also means a Feishu-centric Chinese team may expect agent work items to live in Feishu Project rather than a separate board. An AAMP bridge or Feishu Project sync could be a differentiator later. AAMP being email-based also fits Longtable's email notifications.
- For notifications, every major Chinese IM now has a **no-public-IP long-connection bot mode**: Feishu WebSocket, DingTalk Stream, WeCom 智能机器人 WebSocket. A Hong-Kong-hosted server could also use webhooks.
- Personal WeChat is the constrained one. Official agent channels (ClawBot / iLink) are 1:1 only, with no groups. So "optional WeChat notifications" realistically means per-person 1:1 pushes, or WeCom for teams.
- The large number of chat-to-Claude-Code bridges (cc-connect, lark bridge, DingTalk/WeCom relays) shows Chinese developers already drive Claude Code and Codex from IM. Longtable's notification and "ask-for-help" flows should land in the IM those teams already use (Feishu/WeCom/DingTalk), not only email.

### Gaps
- Feishu Project MCP tool list and whether its agents can be *assigned* work items as assignees: not confirmed (pages blocked).
- DingTalk AI 助理 / 钉钉 AI agents: whether they can be assigned tasks or connected via MCP to Claude Code was not verified beyond the CLI.
- WeCom group-robot webhook and WeChat Official Account (公众号) template/subscription messages as notification channels: not verified, and no sources gathered.
- Worktile: nothing found. PingCode MCP support: not found.
- Whether TAPD has an *official* MCP server: unclear.

## Q3. How Chinese developers use Claude Code / Codex in 2026 (restrictions, relays, domestic-model substitution, popularity)

### Takeaway
Anthropic and OpenAI both exclude **mainland China, Hong Kong and Macau**. Anthropic since 2025-09 also bars any company more than 50% owned or controlled from China, including overseas subsidiaries. In 2026 this escalated:
- Reported covert China-detection in Claude Code (from v2.1.91, April 2026).
- A ban wave on Chinese users around 2026-06-28.
- FT-reported crackdowns on ByteDance/Ant workarounds (July 2026).
- Alibaba banning Claude Code internally (effective 2026-07-10).

Chinese developers still use Claude Code and Codex heavily. They reach them through VPN plus foreign payment, relays (中转) or shared accounts (拼车), all of which carry ban and ToS risk. Increasingly they keep the Claude Code *harness* but point `ANTHROPIC_BASE_URL` at domestic Anthropic-compatible endpoints (GLM, Kimi, DeepSeek, Qwen/Bailian, Volcengine Ark, MiniMax). cc-switch, a provider switcher with about 140k stars, is the clearest popularity signal.

### Cited Findings

#### Policy and enforcement
- Anthropic's supported-countries list excludes mainland China, Hong Kong and Macau; Taiwan and Singapore are supported. Anthropic "reserves the right to not provide its products or services to entities whose majority direct or indirect ownership is attributable to nations other than those listed". — [Anthropic supported countries](https://www.anthropic.com/supported-countries)
- 2025-09-04 policy: Anthropic prohibits companies "whose ownership structures subject them to control from jurisdictions where our products are not permitted, like China" (more than 50%, direct or indirect). This explicitly includes subsidiaries incorporated abroad. — [Anthropic announcement](https://www.anthropic.com/news/updating-restrictions-of-sales-to-unsupported-regions). Anthropic estimated the revenue impact at "low hundreds of millions of dollars". — [Tom's Hardware](https://www.tomshardware.com/tech-industry/anthropic-blocks-chinese-firms-from-claude); [The Decoder](https://the-decoder.com/anthropic-bans-companies-majority-controlled-by-china-russia-iran-and-north-korea-from-claude/) (snippets)
- Anthropic Consumer Terms (effective 2025-10-08):
  - "You may not share your Account login information, Anthropic API key, or Account credentials with anyone else. You also may not make your Account available to anyone else."
  - Reselling the Services is prohibited.

  Both directly cover 拼车 and 中转 resale. — [Anthropic Consumer Terms](https://www.anthropic.com/legal/consumer-terms)
- Claude Code docs say Anthropic "doesn't endorse, maintain, or audit third-party gateway products, and doesn't support routing Claude Code to non-Claude models through any gateway". Admins can pin `ANTHROPIC_BASE_URL` with `allowedProviders: ["customEndpoint"]` (v2.1.285+). — [Claude Code docs: LLM gateways](https://code.claude.com/docs/en/llm-gateway)
- In a 2026-06-10 letter to US senators, Anthropic accused Alibaba's Qwen lab of a distillation campaign: about 25,000 fraudulent accounts and more than 28.8M interactions between 04-22 and 06-05. — [Tom's Hardware](https://www.tomshardware.com/tech-industry/artificial-intelligence/alibaba-bans-anthropics-claude-code-after-an-alleged-hidden-china-detection-backdoor-is-uncovered-employees-told-to-switch-to-qoder-as-the-rift-between-the-firms-widens); [CNBC 2026-07-06](https://www.cnbc.com/2026/07/06/alibaba-anthropic-ai-ban-claude-china.html) (snippets)
- Reverse engineers found a covert China-user detection mechanism in Claude Code starting v2.1.91 (April 2026). Claude Code engineer Thariq Shihipar called it "an experiment we launched in March" against unauthorized resellers and distillation. — [Tom's Hardware](https://www.tomshardware.com/tech-industry/artificial-intelligence/alibaba-bans-anthropics-claude-code-after-an-alleged-hidden-china-detection-backdoor-is-uncovered-employees-told-to-switch-to-qoder-as-the-rift-between-the-firms-widens); [TNW](https://thenextweb.com/news/alibaba-bans-claude-code-anthropic-tracking-chinese-users) (snippets)
  - Chinese community write-ups claim the signals include the system timezone (Asia/Shanghai), relay domains in `ANTHROPIC_BASE_URL`, date-format changes and Unicode steganography. They also report a mass ban wave around 2026-06-28 even for users on US IPs with TUN mode. **These are community claims, not confirmed by Anthropic in detail.** — [KamaCoder notes 06-28](https://notes.kamacoder.com/llm/news/claude-crazy-0628.html); [KamaCoder](https://notes.kamacoder.com/llm/news/claude_code_china_ip_ban.html); [Tencent Cloud developer community](https://developer.cloud.tencent.com/article/2702795); [Alibaba Cloud developer community](https://developer.aliyun.com/article/1744772) (snippets)
- **Alibaba banned employees from using Claude Code from 2026-07-10.** Staff had to uninstall Anthropic model products and switch to Qoder. — [TechCrunch 2026-07-04](https://techcrunch.com/2026/07/04/alibaba-reportedly-bans-employees-from-using-claude-code/); [CNBC](https://www.cnbc.com/2026/07/06/alibaba-anthropic-ai-ban-claude-china.html) (snippets)
- FT reporting (July 2026):
  - Ant Group gave employees corporate Claude accounts through its Singapore entity.
  - ByteDance engineers used personal Claude subscriptions over VPN and expensed them.
  - Anthropic tightened detection: time zones, network traffic, suspicious account activity.
  - These practices broke Anthropic's ToS but not US or Chinese law.

  — [Digitimes 2026-07-03](https://www.digitimes.com/news/a20260703PD230/anthropic-claude-bytedance-ant-group.html); [Investing.com (FT)](https://www.investing.com/news/stock-market-news/anthropic-targets-loopholes-used-by-chinese-firms-to-access-claude-ft-reports-4774998) (snippets)
- OpenAI: mainland China, Hong Kong and Macau are unsupported. OpenAI began blocking API traffic from these regions on 2024-07-09. As of August 2026 they are still not on the supported list, and ChatGPT is unavailable to +852 numbers and HK IPs. — [SCMP](https://www.scmp.com/tech/policy/article/3267971/tech-war-openai-further-block-access-mainland-china-hong-kong-based-developers); [The Register](https://www.theregister.com/2024/06/25/openai_unsupported_countries/); [HK AI Podcast](https://hongkongaipodcast.com/blog/hk-ai-wall); [Digital in Asia tracker](https://digitalinasia.com/which-llms-work-asia-accessibility-tracker/) (snippets)

#### How people actually get access
- Chinese Codex tutorials (2026) describe logging into Codex CLI with a ChatGPT Plus/Business/Pro account. The main obstacle is the network. — [Zhihu tutorial](https://zhuanlan.zhihu.com/p/2044378239750100938); [SegmentFault](https://segmentfault.com/a/1190000047903124) (snippets)
- A community anti-ban guide (Fishason/Claude-anti-ban; 174 stars; v1.0 2026-06-23) lists the ban triggers as:
  - non-US IP
  - Stripe card risk scoring
  - KYC
  - shared accounts across IPs or devices
  - compromised reseller accounts
  - automated behaviour

  It ranks the access options as:
  1. personal US card + VPN
  2. pre-made reseller accounts (RMB 80–200)
  3. shared accounts (RMB 30–100, "extremely high" ban risk)
  4. third-party API proxies
  5. self-hosted overseas VPS + dedicated Max subscription (RMB 800–1,300, "most stable")

  Payment routes it mentions: US cards, App Store gift cards, and virtual cards (it notes WildCard/Bewildcard were discontinued). — [GitHub](https://github.com/Fishason/Claude-anti-ban)
- **claude-relay-service** (CRS; 12.7k stars) is self-hosted 中转 that pools Claude subscription accounts with per-user keys and usage dashboards. Upstreams include Claude OAuth, Codex/OpenAI and Gemini.
  - It warns that use "may violate Anthropic's service terms" and that the author is not responsible for bans.
  - It recommends a US VPS "to avoid Cloudflare blocking".
  - Versions ≤1.1.248 had an admin-auth-bypass vulnerability.

  — [GitHub Wei-Shaw/claude-relay-service](https://github.com/Wei-Shaw/claude-relay-service)

#### Domestic-model substitution (same harness, different model)
- **cc-switch** (139.8k stars) gives one-click provider switching for Claude Code, Claude Desktop, Codex, Gemini CLI, OpenCode, OpenClaw and others, plus MCP/Skills/prompt management. It ships 90+ presets, including Zhipu GLM, Kimi, Qwen/Bailian, DeepSeek, MiniMax and Volcengine/Doubao, and many Chinese relay services (PackyCode, ZetaAPI, AICodeMirror…). — [GitHub farion1231/cc-switch](https://github.com/farion1231/cc-switch)
- **claude-code-router** (37.5k stars; v3.1.0) is a local gateway that routes Claude Code, Codex, Kimi CLI and others to DeepSeek, SiliconFlow, Moonshot, GLM, Qwen, Gemini and more. Its sponsors include Kimi, Zhipu/Z.ai and Qiniu Cloud. — [GitHub musistudio/claude-code-router](https://github.com/musistudio/claude-code-router)
- Anthropic-compatible endpoints:
  - Z.ai (Zhipu international) for Claude Code: `ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic` with a GLM Coding Plan key. A separate OpenAI-compatible coding endpoint serves Cline/Roo. — [Layer3 Labs guide](https://www.layer3labs.io/guides/how-to-use-z-ai-with-claude-code); [codingplan.run](https://codingplan.run/guides/claude-code-with-glm) (snippets)
  - DeepSeek: `https://api.deepseek.com/anthropic`. — [DeepSeek docs](https://api-docs.deepseek.com/quick_start/agent_integrations/claude_code/) (snippet)
- Early-2026 domestic "Coding Plan" snapshot (prices change often):
  - Alibaba Bailian Lite: RMB 40/month (first month 7.9), 18k requests/month; Pro RMB 200. Bailian aggregates Qwen, GLM, Kimi and MiniMax.
  - Volcengine Ark Lite: RMB 40 (first month 8.91); Pro RMB 200. Native Anthropic protocol and "Auto" model routing, pitched at "Claude Code heavy users".
  - Zhipu GLM Lite: RMB 49, 24k requests; Pro RMB 149. Supports 20+ clients and includes MCP tools.

  — [Juejin 2026 Coding Plan comparison](https://juejin.cn/post/7615892857225035830); [iamle 2026-02](https://www.iamle.com/archives/2999.html); [Zhihu](https://zhuanlan.zhihu.com/p/2011036064391915427) (snippets; exact per-row attribution among these three was not checkable)
- Later snapshot (wmpeng/codingplan, updated 2026-09-24; 37 platforms, 99 plans, 1.1k stars):
  - Zhipu Lite RMB 118, Pro 538
  - MiniMax Basic 49, Premium 469
  - Kimi 99 / 699
  - Ark 40 / 200
  - Bailian Token Plan 198, Max 1,398
  - Baidu Qianfan 9.9 / 600

  It notes "Zhipu and Kimi temporarily stopped accepting new signups". — [GitHub wmpeng/codingplan](https://github.com/wmpeng/codingplan)

#### Popularity indicators
- GitHub stars, as a proxy for Chinese developer interest in using foreign agent harnesses:
  - cc-switch: 139.8k
  - claude-code-router: 37.5k
  - cc-connect: 15.7k
  - claude-relay-service: 12.7k
  - lark-coding-agent-bridge: 2.6k

  — GitHub pages linked above
- A usage-tracker sample of 368 Chinese developers over 30 days: Claude Code used by 83%, Codex 78%, OpenCode and OpenClaw about 27%. **Self-selected sample; page blocked, snippet only.** — [VibeCafe](https://vibecafe.ai/blogs/cn-coding-tools-2026)
- Chinese discussion of moving between Codex and Claude after the ban waves: [KamaCoder: "国内开发者怎么在Codex和Opus 4.8之间切换"](https://notes.kamacoder.com/llm/news/claude-crazy-0628.html) (title/snippet)
- Release cadence (npm, as of 2026-10-02/03):
  - Claude Code 2.1.288 (2026-10-02)
  - Codex CLI 0.160.0 (2026-10-01)

  — [npm @anthropic-ai/claude-code](https://registry.npmjs.org/@anthropic-ai%2fclaude-code); [npm @openai/codex](https://registry.npmjs.org/@openai%2fcodex)

### Inferences
- A China+US team using Longtable will often be **heterogeneous under the hood**. The China members may run Claude Code pointed at GLM, Kimi, DeepSeek, Ark or Qwen, or run Codex through a relay. The US members run first-party Claude Code or Codex. Longtable's MCP tools and hooks must not depend on Anthropic- or OpenAI-account identity, specific model names, or Anthropic-only beta features. Identity should come from Longtable's own auth (passkey), not from `claude` login state.
- **Entity eligibility matters for the customer, not just the user.** If the team's company is more than 50% Chinese-owned, Anthropic's terms bar it from Claude entirely, wherever it is incorporated. Longtable should not position itself as "for Claude Code teams" only. It should support Codex and domestic CLIs (Qwen Code, Kimi Code, CodeBuddy Code, Qoder CLI, MiniMax Code) through the same MCP surface.
- Hooks that auto-report commits and progress should be robust to custom `ANTHROPIC_BASE_URL` and timezone settings. They should not send anything that looks like account sharing; for example, one Longtable server must never proxy LLM traffic for several users. Longtable should stay out of the model-traffic path entirely to avoid the 中转 and ToS risk category.
- Both Anthropic and OpenAI treat Hong Kong as unsupported. Any *server-side* LLM feature Longtable might add (summaries, triage) cannot call those APIs from an HK server. It would need a US region, or domestic models for the China side.

### Gaps
- No official numbers on how many Chinese developers use Claude Code or Codex. Only self-selected samples and GitHub stars. npm download counts could not be fetched (API blocked).
- OpenAI's policy on Chinese-*controlled* entities (as opposed to geography) was not found.
- Anthropic has not publicly detailed the Claude Code detection signals. The community claims (timezone, Unicode steganography) are unverified.
- Domestic Anthropic-compatible base URLs for the mainland endpoints of Zhipu (bigmodel.cn), Moonshot, Bailian and Ark were not verified from official docs (blocked).

## Q4. China-specific requirements for a team tool (notifications, ICP, data transfer, 等保, payments, reachability)

### Takeaway
- **ICP filing:** a Hong-Kong-hosted service needs no ICP filing. Mainland hosting requires ICP before launch.
- **Latency:** HK has good mainland latency on premium routes (CN2 GIA / CMI), but Anthropic and OpenAI both block HK as a region.
- **Cross-border data:** CAC's 2024 provisions exempt small transfers. Non-CIIO operators sending personal information of fewer than 100k people per year are exempt from security assessment, standard contract and certification. Employee HR data under labour rules is also exempt. A 2–5-person-team product is far under the threshold.
- **Notifications:** Feishu, DingTalk and WeCom all offer no-public-IP bot connections. Personal WeChat agent channels are 1:1 only.
- **Passkeys:** passkeys on Android are documented around Credential Manager and providers like Google Password Manager. Mainland Android phones without Google services may lack them, which is not verified. Plan a fallback.
- Payments, 等保 and email reachability could not be verified in this run.

### Cited Findings
- ICP: "使用中国香港的服务器开办网站/APP 不需要备案；如果使用中国境内的服务器…则必须先办理 ICP 备案" (a site or app on a Hong Kong server needs no filing; one on a mainland server must complete ICP filing first). — [Tencent Cloud ICP docs](https://cloud.tencent.com/document/product/243/19630) (snippet)
- CAC 《促进和规范数据跨境流动规定》 (Provisions on Promoting and Regulating Cross-Border Data Flows, 2024-03-22). Cross-border PI transfers are exempt from security assessment, standard contract and certification when any of these applies:
  1. necessary to conclude or perform a contract to which the individual is a party
  2. necessary for cross-border HR management of **employees** under lawful labour rules
  3. emergencies
  4. a non-CIIO provides PI of **fewer than 100,000 people** (excluding sensitive PI) cumulatively since Jan 1 of the year

  — [CAC provisions](https://www.cac.gov.cn/2024-03/22/c_1712776611775634.htm) (snippet); CAC policy Q&A updated October 2025: [CAC Q&A](https://www.cac.gov.cn/2025-10/31/c_1763633376984070.htm) (title only)
- HK to mainland latency (provider/affiliate claims): via CN2 GIA about 20–35 ms to Beijing, 15–25 ms to Shanghai, under 10 ms to Guangzhou/Shenzhen. CN2 GT hands off to the congested 163 network domestically, while CN2 GIA stays on AS4809 end-to-end. — [GitHub hong-kong-cn2-gia](https://github.com/yvbqza1/hong-kong-cn2-gia); [DMIT HK](https://www.dmit.io/pages/location/hong-kong) (snippets; low-quality sources)
- Neither Anthropic nor OpenAI supports Hong Kong. — [Anthropic supported countries](https://www.anthropic.com/supported-countries); [HK AI Podcast](https://hongkongaipodcast.com/blog/hk-ai-wall)
- claude-relay-service recommends a US-region VPS "to avoid Cloudflare blocking". This is anecdotal evidence that Asian or HK IPs get blocked for Claude traffic. — [GitHub](https://github.com/Wei-Shaw/claude-relay-service)
- IM notification transports with no public IP needed (see Q2 for details):
  - Feishu: WebSocket
  - DingTalk: Stream
  - WeCom 智能机器人: WebSocket
  - Personal Weixin: iLink long-poll, 1:1 only
  - WeChat ClawBot: 1:1, no groups, requires OpenClaw

  — [cc-connect README](https://raw.githubusercontent.com/chenhg5/cc-connect/main/README.md); [clawrelay-wecom-server](https://github.com/wxkingstar/clawrelay-wecom-server); [Zhihu on ClawBot](https://zhuanlan.zhihu.com/p/2019118125963059386)
- The Feishu CLI can send chat messages as a bot or as the user: `im +messages-send`. — [GitHub larksuite/cli](https://github.com/larksuite/cli)
- Passkeys on Android: "Credential Manager's passkeys implementation works on devices running Android 9 (API level 28) and higher". The private key is stored "on a credential provider like Google Password Manager". — [Android Developers: passkeys](https://developer.android.com/identity/passkeys)
- Multica's Chinese README says its IM integrations include Feishu/Lark, DingTalk and WeCom. DingTalk, WeCom and Telegram are community-maintained, and the README carries a mainland-deployment caveat for Feishu (exact wording not verified). — [Multica README.zh](https://raw.githubusercontent.com/multica-ai/multica/main/README.zh.md)
- Payments, indirect evidence only: Chinese guides list US cards, App Store gift cards and virtual cards (some discontinued) as ways to pay for Claude. Domestic coding plans are priced and sold in RMB. — [Claude-anti-ban](https://github.com/Fishason/Claude-anti-ban); [wmpeng/codingplan](https://github.com/wmpeng/codingplan)

### Inferences
- **HK hosting is a reasonable middle ground.** It needs no ICP and gives low mainland latency if the host uses CN2 GIA or CMI routes; cheap CN2 GT routes congest at peak. US members will see higher latency than to a US region, but that was not measured here.
- A 2–5-person team falls under the CAC "<100k people" exemption. Employee data may also fall under the HR exemption. PIPL notice and consent still apply. Not legal advice; confirm with counsel.
- **Passkey confirmation** for commitment actions needs a fallback for China-side members whose Android phones lack Google Play services. Options include WeChat/WeCom confirmation links, TOTP, or hardware keys. iPhones are likely fine through iCloud Keychain (not verified for China).
- For "optional WeChat", the realistic paths are WeCom (group-capable, official) or 1:1 personal pushes. Feishu and DingTalk bots are first-class for teams that already live there. Email alone may be a weak channel for China-side members, but its deliverability and reachability were not verified (see Gaps). Test delivery to QQ/163 mailboxes before relying on it.

### Gaps
- **Payments:** Stripe/Paddle support for Alipay/WeChat Pay *recurring* subscriptions, and HK merchant options, could not be verified (sites blocked; search budget exhausted).
- **等保 2.0 (MLPS)** applicability to an HK-hosted SaaS used by mainland staff, and whether Chinese enterprise buyers would demand it: not researched.
- **Generative-AI service filing (大模型/算法备案):** not researched. It probably matters only if Longtable itself serves generated content to mainland users.
- Passkey support on HarmonyOS NEXT and on GMS-less Chinese Android ROMs: not verified.
- Email deliverability to QQ/163/corporate mailboxes from an HK server, and Gmail reachability: not verified.
- GitHub reachability and stability from the mainland in 2026, which matters for commit-reporting hooks and webhooks: no source found.
- WeChat Official Account (公众号) template or subscription messages for an overseas entity: not verified.

## Q5. Is anyone in China doing "a shared board for humans plus their coding agents"? How mature?

### Takeaway
Yes. The strongest example is **Multica**: open source, 51.9k stars, founded by a four-person team led by ex-TikTok engineer Zhang Jiayuan (张佳圆), with a Chinese README and Feishu, DingTalk and WeCom integrations. It is a kanban where humans assign issues to agents (Claude Code, Codex, Kimi, Qwen and 26+ CLIs). Agents run in local daemons, claim tasks, comment, report blockers and stream progress; work passes review gates; humans and agents form "squads". It overlaps heavily with Longtable.

Other activity:
- Big platforms are moving the same way: Feishu Project's "human + Agent" system with the AAMP protocol, and Tencent's CodeBuddy NPC @-mentioned in Issues.
- Smaller open-source efforts exist: OpenAgents Workspace (4.2k stars; shared threads where people @ Claude Code and Codex), plus many early Chinese multi-agent MCP projects (collab-mcp, 51team, codexmcp).

None of these targets "2–5 person cross-border team where each human brings their own agent, and commitments are human-confirmed with a passkey".

### Cited Findings
- **Multica** (multica-ai/multica): "Make humans and AI agents work as one team — open-source and self-hostable". 51.9k stars, 6.7k forks; license is Apache 2.0 plus additional conditions; Chinese README available. — [GitHub](https://github.com/multica-ai/multica)
  - Board and agent workflow:
    - Kanban board; assign issues to agents "like you'd assign to a colleague".
    - Agents have profiles, appear on the board, post comments, create issues and "report blockers proactively".
    - Task lifecycle enqueue → claim → start → complete/fail, with WebSocket progress streaming.
    - Review gates before merge.
  - Teams and automation:
    - **Squads** of agents and humans with a leader that delegates.
    - Reusable Skills.
    - Autopilots (cron).
    - Execution logs with tool-call replay.
  - Runtime and integrations:
    - Local daemon runtime, so code stays on the user's machine.
    - 26+ agent CLIs, including Claude Code, Codex, Cursor, Copilot, OpenCode, Kimi and Qwen.
    - GitHub, GitLab, Gitea, Forgejo.
    - Slack, Feishu/Lark, DingTalk, WeCom, Telegram.
  - Access and deployment:
    - Owner/admin/member roles.
    - Web, desktop and iOS clients.
    - Cloud (multica.ai) or self-host (Docker Compose / Helm).

  — [GitHub](https://github.com/multica-ai/multica); [README.zh](https://raw.githubusercontent.com/multica-ai/multica/main/README.zh.md); [search summary of README](https://github.com/multica-ai/multica)
- Multica's team and traction:
  - Four-person team led by Zhang Jiayuan (张佳圆), formerly at TikTok and creator of DevvAI.
  - Gained 12k stars in its first week and topped GitHub Trending.
  - Reached 22.7k stars and 2.8k forks by late April 2026.
  - Open-sourced right after Anthropic released its Managed Agents product.

  — [Tencent News 2026-04-26](https://news.qq.com/rain/a/20260426A02YC400); [PingWest](https://www.pingwest.com/a/313471); [163/网易](https://www.163.com/dy/article/KSG8QGRG0556BT2D.html); Zhihu headline "斩获14.1k Star！Claude Managed Agents开源版，多人与多Agent协作实时可见" (14.1k stars; an open-source Claude Managed Agents; humans and multiple agents collaborating, visible in real time). This is likely about Multica but was not opened: [Zhihu](https://zhuanlan.zhihu.com/p/2028512176076235854) (snippets)
- **Feishu Project** (2026-04-23) positions itself as a "人+Agent协同的行动系统" (human + Agent collaborative action system). AAMP standardizes platform→agent and agent→agent task dispatch, ack, help_needed and result over email. Humans can reply in-thread. — [QbitAI](https://www.qbitai.com/2026/04/406026.html); [GitHub larksuite/aamp](https://github.com/larksuite/aamp)
- **Tencent CodeBuddy NPC** (2026-07-23): @NPC in Issue/PR/comments on CNB, and multi-role NPC teams with a PM NPC assigning tasks. — [IT之家](https://www.ithome.com/0/980/633.htm); [163/网易](https://www.163.com/dy/article/L2HI90JF0511B8LM.html) (snippets)
- **OpenAgents Workspace** (openagents-org/openagents; 4.2k stars; Apache 2.0):
  - shared threads where you @mention Claude Code, Codex and others
  - shared files and a shared browser
  - a Launcher that installs and manages agents
  - no account needed; self-host or cloud
  - some agent integrations in beta

  It was launched to Chinese developers on V2EX and cnblogs (2026-04). — [GitHub](https://github.com/openagents-org/openagents); [cnblogs 2026-04-18](https://www.cnblogs.com/itech/p/19889215); [V2EX](https://www.v2ex.com/t/1202103)
- **collab-mcp** (pwdh2026), a Chinese README project: file-driven, multi-machine Claude collaboration through a shared folder. It has 56 MCP tools (tasks, messages, teammate registration, gates, deliverables), human review gates (`review_required`, `approve_task` / `request_changes`) and `force_assign`. Despite being at v3.36.4 it has **0 stars and 5 commits** (very early); GPL-3.0. — [GitHub](https://github.com/pwdh2026/collab-mcp)
- Other Chinese multi-agent projects:
  - **51team**: MCP + tmux framework where several Claude Code agents message each other; optimized for DeepSeek V4. — [GitHub](https://github.com/jackleeson-beep/51team) (snippet)
  - **Multi-Agent MCP**: a leader splits tasks across tmux member agents. — [Glama](https://glama.ai/mcp/servers/davidzong1/Mult-Agent-MCP) (snippet)
  - **codexmcp** (GuDaStudio; 2.0k stars; Chinese-first README): Claude Code orchestrates Codex via MCP; built for a single developer, with no multi-person features. — [GitHub](https://github.com/GuDaStudio/codexmcp)
  - **feishu-agent-communication**: multiple bots @-mention each other in Feishu groups (CherryStudio / WorkBuddy / OpenClaw). — [GitHub](https://github.com/zhouxin121/feishu-agent-communication) (snippet)
- Qwen Code advertises "Agent Teams" (multi-agent, single user). — [GitHub QwenLM/qwen-code](https://github.com/QwenLM/qwen-code)

### Inferences
- **Multica is Longtable's most direct competitor and is popular in China.** It already covers board, assign, claim, blockers, comments, squads, local runtimes, Feishu/DingTalk/WeCom notifications and self-hosting. Longtable's differentiation needs to be explicit on several fronts:
  1. Agents act through MCP plus hooks inside the user's own Claude Code/Codex session, not through a daemon that spawns agents. This is lighter and "your agent, your account".
  2. Humans confirm commitment actions with a passkey, an accountability model Multica does not emphasize.
  3. Designed for small cross-border teams: HK hosting, mainland reachability, bilingual UI, WeChat/email notifications.
  4. Simplicity for 2–5 people versus Multica's squads, autopilots and 26-provider breadth.
- The pattern is maturing quickly. Big Chinese platforms (Feishu Project, Tencent CNB) are adding human+agent work items natively. Longtable risks being a feature of the IM or PM suite a Chinese team already uses, so interoperability matters: Feishu/Meegle sync, AAMP, Gitee/TAPD MCP.
- Many Chinese open-source multi-agent coordination projects exist, but most are single-developer orchestration (tmux, MCP routers) with little adoption. The "multi-human + their agents" framing is mostly occupied by Multica and OpenAgents.

### Gaps
- Multica's cloud pricing, and whether its cloud is reachable and hosted for mainland users: not found.
- Multica's exact license restrictions ("additional conditions") and their implications: not read.
- Whether any Chinese SaaS (not open source) offers a hosted human+agent board for small cross-border teams: none found. The search budget ran out before checking 36Kr and 机器之心 for startup coverage.
- A search snippet mentioned Alibaba Cloud launching "AgentTeams" (multi-agent collaboration governance, leader–worker) in July 2026. The source page was not opened, so this is **unverified**.
