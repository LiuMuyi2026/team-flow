# Direct open-source competitors (part A): Multica, Paperclip and Agor, compared feature by feature (as of 2026-10-03)

## Q1. Multica (multica-ai/multica): features, how agents connect, squads, blockers, review gates, chat-app integrations, cloud vs self-host, license, pricing, security

### Takeaway
Multica is an issue board where AI agents can be assignees. It is built by Index Labs (Hong Kong) Limited and had 51,861 stars on 2026-10-03, adding 3,000 to 5,000 a month. Each person's machine runs a `multica` daemon. The daemon claims runs and starts the agent CLI headless. Approvals are answered automatically, there is no sandbox, and Claude Code runs with `bypassPermissions`.

Multica does not attach to sessions people already run, and it has no hooks. Instead, an MIT-licensed "CLI skill" lets a person's own Claude Code or Codex drive the board using that person's full-account token.

The human side is well developed:
- owner/admin/member roles, plus per-agent access settings;
- squads (a leader agent routes work to agents and people);
- an in-app inbox;
- Feishu, DingTalk, WeCom, Slack and Telegram bots;
- Chinese documentation.

The weaknesses:
- "Review" is only a status, which agents can set themselves.
- "Blocked" is a status, not a link between issues.
- There are no approval objects and no prompt-injection controls.
- There is no SSO and no passkey support.
- No email notifications are documented.

The license is Apache-2.0 plus extra conditions. You may not host Multica for anyone outside your own organization without a commercial license, even for free, and you may not remove its branding.

### Cited Findings

#### How to read these notes (applies to Q1–Q4)
- **Evidence labels.** Each finding is tagged with the kind of source it comes from:
  - **[README]**: the repository README or marketing copy.
  - **[docs]**: product documentation shipped in the repo (Multica `apps/docs`, Agor `apps/agor-docs`).
  - **[spec]**: Paperclip's internal design and contract documents under `doc/`.
  - **[license]**: the license text.
  - **[registry]**: the npm registry, the Go module proxy, or the daily GitHub-ranking CSV.
  - **[prior notes]**: findings carried over from open_source.md or china_market.md without being re-checked.
- **Nothing was verified by running code.**
- **Source versions.** All files were fetched on 2026-10-03 from each project's default branch. The head commits at that time were:
  - Multica `main`: 2026-10-02T14:25:26Z — [Go proxy](https://proxy.golang.org/github.com/multica-ai/multica/@v/main.info)
  - Paperclip `master`: 2026-10-03T11:52:49Z — [Go proxy](https://proxy.golang.org/github.com/paperclipai/paperclip/@v/master.info)
  - Agor `main`: 2026-10-03T00:48:07Z — [Go proxy](https://proxy.golang.org/github.com/preset-io/agor/@v/main.info)
- **Blocked sources.** The egress proxy returned 403 for multica.ai, paperclip.ing, docs.paperclip.ing, agor.live, data.jsdelivr.com, github.com and api.github.com. As a result, pricing pages, terms of service, privacy policies, hosted docs and GitHub issue trackers were **not** read.

#### Identity, license and traction
- **Who makes it.** The license names "the producer" as "Index Labs (Hong Kong) Limited, the company that develops and distributes Multica", with copyright "© 2025-2026 Index Labs (Hong Kong) Limited". Commercial licenses are requested via multica.ai/contact-sales. [license] — [LICENSE](https://raw.githubusercontent.com/multica-ai/multica/main/LICENSE)
- **Team.** A four-person team led by Zhang Jiayuan (张佳圆), who previously worked at TikTok and created DevvAI. [prior notes; not re-checked] — [Tencent News 2026-04-26](https://news.qq.com/rain/a/20260426A02YC400)
- **Sister repo.** The same GitHub org owns `andrej-karpathy-skills`, which had 216,601 stars. [registry] — [Ranking 2026-10-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-10-03.csv)
- **Stars, forks, issues.** On 2026-10-03: 51,861 stars, 6,738 forks, 967 open issues. Language Go. GitHub description: "Make humans and AI agents work as one team — open-source and self-hostable." [registry] — [Ranking 2026-10-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-10-03.csv)
- **Star series.** Multica first appeared in the Go top-100 in July 2026: 38,884 on 07-03, 43,313 on 08-03, 48,659 on 09-03 and 51,861 on 10-03. That is +4,429, +5,346 and +3,202 per month. [registry] — [07-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-07-03.csv), [08-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-08-03.csv), [09-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-09-03.csv)
- **Earlier traction.** 22.7k stars and 2.8k forks by late April 2026, and 12k stars in its first week. [prior notes] — [Tencent News](https://news.qq.com/rain/a/20260426A02YC400)
- **Release dates.**
  - First tag v0.1.0 on 2026-01-15T18:26Z. The latest tag is v0.6.1 (2026-10-01T10:18Z), and there are 164 tags in total. [registry] — [Go proxy v0.1.0](https://proxy.golang.org/github.com/multica-ai/multica/@v/v0.1.0.info), [v0.6.1](https://proxy.golang.org/github.com/multica-ai/multica/@v/v0.6.1.info), [list](https://proxy.golang.org/github.com/multica-ai/multica/@v/list)
  - The README says "We release most weekdays, so `main` moves quickly". [README] — [README](https://raw.githubusercontent.com/multica-ai/multica/main/README.md)
  - **Conflict:** tags go back to 2026-01-15, but the Chinese press describes an April 2026 launch week. The public launch therefore appears to be about April 2026, after quieter pre-releases.
- **License structure.** The "Multica License" is the full Apache-2.0 text (Part II) plus "Additional Conditions" (Part I). Part I controls if the two conflict. [license] — [LICENSE](https://raw.githubusercontent.com/multica-ai/multica/main/LICENSE)
- **License condition 1a (hosting and embedding).** Without a commercial license you may not:
  - provide a hosted service to third parties, or embed Multica in a product that is sold or distributed;
  - run a hosted service even if free: "A publicly accessible instance operated for users outside your own organization requires a commercial license even when it is offered free of charge".

  What is allowed:
  - "Internal use within a single organization (including multiple workspaces) does not require a commercial license".
  - Publishing a fork's source is allowed, but each operator of a hosted service needs its own license.

  [license] — [LICENSE](https://raw.githubusercontent.com/multica-ai/multica/main/LICENSE)
- **License condition 1b (branding).** You may not remove or modify the Multica logo, name or copyright notices in any UI built from `apps/web`, `apps/desktop`, `apps/mobile`, `packages/views` or `packages/ui`, without a written branding waiver. [license] — [LICENSE](https://raw.githubusercontent.com/multica-ai/multica/main/LICENSE)
- **License condition 1c (backend-only use).** If you use only the backend, daemon or CLI, you must still state "built on Multica" with a link. [license] — [LICENSE](https://raw.githubusercontent.com/multica-ai/multica/main/LICENSE)
- **License condition 2 (contributions).** The producer "can adjust this Multica License to be more strict or relaxed", and contributions may be used commercially, including for its cloud business. [license] — [LICENSE](https://raw.githubusercontent.com/multica-ai/multica/main/LICENSE)
- **How the README describes the license.** It calls Multica "source-available" and summarises the license as "Apache License 2.0 plus additional conditions covering hosted services, commercial embedding, and branding". [README] — [README](https://raw.githubusercontent.com/multica-ai/multica/main/README.md)

#### Agent execution model
- **Architecture.**
  - Backend: Go (Chi router, sqlc, gorilla/websocket) with PostgreSQL 17.
  - Web: Next.js 16.
  - Desktop: Electron.
  - Mobile: Expo for iPhone and iPad.
  - An "Agent daemon … runs on your machine, next to your code" and "spawns" Claude Code, Codex, Cursor and others.

  [README] — [README](https://raw.githubusercontent.com/multica-ai/multica/main/README.md)
- **What the daemon does.** It "detects installed AI agent CLIs, registers them with the server, and executes tasks when agents are assigned work". Every person who wants to run agents locally installs the `multica` CLI and runs the daemon. [docs] — [SELF_HOSTING.md](https://raw.githubusercontent.com/multica-ai/multica/main/SELF_HOSTING.md)
- **Runtimes.** A runtime is one computer plus one AI coding tool. The server pushes a wake signal and the daemon also polls. Heartbeats go out every 15 s. A runtime is marked offline within about 3 minutes. By default a daemon runs at most 20 runs at once, and each agent at most 6. [docs] — [daemon-runtimes](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/daemon-runtimes.mdx)
- **Runtimes are private by default.** "only the runtime owner can create agents on it. Workspace owners and admins are no exception". Only the owner can make a runtime public. [docs] — [daemon-runtimes](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/daemon-runtimes.mdx)
- **Where code and data live.** Code, tool credentials and local directories stay on the connected computer. The server stores issues, comments, agent configuration, run context and run records, which "can include code snippets". An agent's custom environment variables and MCP configuration "live on the server" and are sent to the runtime when a run starts. [docs] — [daemon-runtimes](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/daemon-runtimes.mdx)
- **Runs are unattended.**
  - "Multica runs agents unattended, so approval prompts are answered automatically."
  - By default "Codex runs with `sandbox_mode = "danger-full-access"` and Claude Code with `--permission-mode bypassPermissions`".
  - The only exception is an explicit opt-in to Codex's native sandbox on Windows.

  [docs] — [security-model](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/security-model.mdx)
- **Agents are configurations, not processes.** An agent is "not a continuously running process. It is a reusable identity and configuration". It produces runs only when work arrives: an assignment, an @mention, a reply, a chat message, an autopilot or an automation. [docs] — [agents](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/agents.mdx)
- **26 supported CLIs.** The list includes Claude Code, Codex, Cursor Agent, GitHub Copilot CLI, OpenCode, Kimi, Qwen Code, Qoder CN, Trae CLI, CodeBuddy, DeepSeek Harness, MiniMax Code, Huawei Cloud CodeArts and DevEco Code. Multica "does not ship a model … Multica drives them; it doesn't ship them". [README] — [README](https://raw.githubusercontent.com/multica-ai/multica/main/README.md)
- **Per-provider features.** Claude Code and Codex both support session resumption, MCP managed by Multica, and skill injection (`.claude/skills/` and `$CODEX_HOME/skills/`). [docs] — [providers](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/providers.mdx)
- **Steering a running agent.** "Reply while it works and the message lands in the current run … Claude Code, Codex, and Grok today." [README] — [README](https://raw.githubusercontent.com/multica-ai/multica/main/README.md)
- **Connecting from your own session.** The MIT-licensed "Multica CLI Skill" (multica-ai/multica-cli, v1.1.0 on 2026-08-14) "teaches any local coding agent — Claude Code, Codex, Cursor … how to operate Multica through the authenticated `multica` CLI". It can read and triage issues, post comments and change status, and it says agents "should ask before making state changes". Permissions "come only from the user's local CLI login". [README of skill] — [multica-cli README](https://raw.githubusercontent.com/multica-ai/multica-cli/main/README.md), [Go proxy](https://proxy.golang.org/github.com/multica-ai/multica-cli/@v/main.info)
- **No hooks.** No Claude Code or Codex hook integration (SessionStart, PostToolUse, UserPromptSubmit, hooks.json) appears anywhere in the fetched Multica README or docs (grep on 2026-10-03). [docs]
- **Possible managed runtimes.** There are separate `mcn_` credentials for "Multica Cloud Node connections", managed by "Multica Cloud Fleet". This suggests a managed cloud-runtime offering, but it is not described. [docs] — [auth-tokens](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/auth-tokens.mdx)

#### Multi-human features
- **Roles.** Each workspace member is `owner`, `admin` or `member`. "Roles only control workspace settings and team management; day-to-day collaboration — creating issues, writing comments — is open to all members". Invitations are sent by email and are valid for 7 days. Only an owner can grant the owner role. [docs] — [members-roles](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/members-roles.mdx)
- **Agent access.** Each agent has an owner and an access setting: "Only me" (the default), "Entire workspace" or "Specific people". Owners and admins "cannot bypass Access to run someone else's 'Only me' agent". [docs] — [agents](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/agents.mdx)
- **Assigning work.**
  - An issue's assignee can be a member, an agent or a squad.
  - A member assignee owns the follow-up, and "no run is created".
  - An agent or squad assignee starts a run immediately, unless the issue is in `backlog`.

  [docs] — [issues](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/issues.mdx)
- **Statuses and who sets them.**
  - Built-in statuses: `backlog`, `todo`, `in_progress`, `in_review`, `blocked`, `done`, `cancelled`. Custom statuses are also allowed.
  - "There is no fixed flow between statuses — members and agents can change them directly."
  - Agents write status through the CLI. "`done` is usually a human confirmation, or the merge of the issue's linked PRs".

  [docs] — [issues](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/issues.mdx)
- **Blockers.**
  - `blocked` is a status meaning "Cannot continue for now".
  - A failed run can have the reason `agent_blocked` ("The agent reported it cannot proceed"); the fix is to "Provide what its comment asked for".
  - Issues can be related only as parent and sub-issue. Sub-issues can carry "stages": when every sub-issue in a stage is finished, the parent is notified, and if its assignee is an agent, that agent wakes up.
  - No dependency or "blocked-by" links between issues are documented.

  [docs] — [issues](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/issues.mdx), [tasks](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/tasks.mdx)
- **"Claim" is a machine action.** In Multica, "the daemon … claims runs". No human "claim this task" action is documented; a person assigns the issue to themselves. [docs] — [daemon-runtimes](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/daemon-runtimes.mdx)
- **Comments and @mentions.**
  - @mentioning an agent in a comment creates a run. A preview shows which agents will start.
  - Plain replies are routed to the agent already in that thread.
  - A comment starting with `/note` triggers no agent.
  - `@all` notifies members only.
  - Consecutive comments are merged into one pending run.

  [docs] — [mentioning-agents](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/mentioning-agents.mdx)
- **Squads.** A squad is "one leader agent and any number of members (agents or human members)".
  - The leader "posts one delegation comment" that @mentions the chosen members.
  - Most later comments wake the leader again.
  - The leader moves the parent issue to `in_review` when the goal is met. "`done` is left to a human reviewer or existing integrations".
  - "Any workspace member can create a squad". Archiving a squad "cannot be undone".

  [docs] — [squads](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/squads.mdx)
- **Real-time visibility.**
  - A WebSocket backend streams progress into an execution log that can replay "every tool call, command, and error, timestamped".
  - Usage analytics show "what each run cost, per agent and per issue".
  - Issue views: list, board, table, Gantt and swimlane.

  [README] — [README](https://raw.githubusercontent.com/multica-ai/multica/main/README.md); [docs] — [issues](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/issues.mdx)
- **Notifications.**
  - The in-app inbox covers assignments, comments, @mentions, status/priority/date changes, agent run failures and autopilot events.
  - Settings let you switch notification groups on or off.
  - "System and browser notifications control desktop banners".
  - Agents have no inbox.
  - No email, SMS or push notifications for humans are documented. Email is used for sign-in codes and invitations.

  [docs] — [inbox](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/inbox.mdx), [auth-setup](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/auth-setup.mdx)
- **Chat-app integrations are for talking to agents, not for notifying people.**
  - Feishu/Lark, Slack, DingTalk, WeCom and Telegram are supported. "Each Bot is bound to one Multica agent".
  - In group chats the bot responds only when @mentioned; DMs need no mention.
  - Commands: `/issue` creates an issue; `/new` and `/clear` manage chat context.
  - Senders must link their chat account to a workspace membership before the agent will run.

  [docs] — [channels](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/channels.mdx)
- **Chat-app caveats.**
  - "New connections are currently open only for mainland-China Feishu; existing international Lark connections keep working".
  - DingTalk, WeCom and Telegram are "community-maintained": they ship in every release but carry "no official support SLA". All three have been maintained since 2026-08.
  - WeCom accepts text only.
  - On self-hosted deployments with several server replicas, WeCom replies can be silently dropped unless Redis is configured.

  [docs] — [channels](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/channels.mdx), [community-maintained](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/community-maintained.mdx)
- **Other surfaces.**
  - Autopilots run "standups, audits, and reports on a cron".
  - Chat lets you "Ask your workspace a question".
  - Apps exist for web, desktop and mobile, but "the iOS app builds from source today, not yet on the App Store".
  - The CLI and API are scriptable.

  [README] — [README](https://raw.githubusercontent.com/multica-ai/multica/main/README.md)

#### Human-in-the-loop and security
- **Review gate.** The README says "Work lands in review, not in main. You decide what ships." [README] — [README](https://raw.githubusercontent.com/multica-ai/multica/main/README.md)

  Mechanically, though, review is the `in_review` status, and "members and agents can change [statuses] directly". The system itself changes status in only two cases: it rolls a failed run back to `todo`, and it moves an issue to `done` once all linked PRs are merged. [docs] — [issues](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/issues.mdx)
- **No approvals.** No approval objects, approver roles or per-action "ask first" gates are documented. The CLI tools' own approval prompts are answered automatically. [docs] — [security-model](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/security-model.mdx)
- **Agent tokens.**
  - Each run gets a temporary `mat_` token bound to "the current user, workspace, agent, and run", valid for at most 24 hours.
  - It "can't be used to reach sensitive operations restricted to users or owners", and requests made with it "are recorded as agent actions".
  - Agents can create issues, post comments and change status.

  [docs] — [auth-tokens](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/auth-tokens.mdx), [agents](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/agents.mdx)
- **Token caveat.** The run token sits in the runtime's environment, and "Any child process the runtime starts inherits all of them by default, including `MULTICA_TOKEN`". [docs] — [daemon-runtimes](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/daemon-runtimes.mdx)
- **Personal access tokens.** A personal token (`mul_`) "represents your account. It can access every workspace and API you have access to". The CLI and daemon use one, and it is renewed automatically. Only a hash is stored. [docs] — [auth-tokens](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/auth-tokens.mdx)
- **Sandbox boundary.** "The boundary is the daemon user"; "Multica makes no filesystem-sandbox guarantee". A run "can read your SSH keys, edit your shell profile, and delete your documents". The docs recommend running the daemon as a dedicated Unix user, in a container or in a VM. [docs] — [security-model](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/security-model.mdx)
- **Secrets.**
  - Agent environment variables and MCP configuration are stored on the server, with stricter read rules for values that may contain credentials.
  - On self-hosted deployments, chat-bot credentials are encrypted with a 32-byte key per platform.

  [docs] — [agents](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/agents.mdx), [channels](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/channels.mdx)
- **Prompt injection.** A grep of all fetched Multica docs for "prompt injection", "untrusted", "quarantine" or trust labels found nothing.
  - Replies from any member flow into the next run of the target agent ("the new information feeds into subsequent runs").
  - Any member who has access to an agent can trigger it with an @mention.

  [docs] — [agents](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/agents.mdx), [mentioning-agents](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/mentioning-agents.mdx)
- **Audit.** The README promises "an audit trail that includes the robots". The docs describe per-issue activity timelines and execution logs. No dedicated, exportable audit log is documented. [README] — [README](https://raw.githubusercontent.com/multica-ai/multica/main/README.md); [docs] — [issues](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/issues.mdx)
- **Sign-in.**
  - Users sign in with a 6-digit email code (valid for 10 minutes), and Google OAuth can be added.
  - The session cookie lasts 30 days, sliding.
  - Self-hosted instances can restrict signup with `ALLOW_SIGNUP` or an allowlist.
  - No SSO, SAML, OIDC or passkeys are documented.

  [docs] — [auth-setup](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/auth-setup.mdx), [auth-tokens](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/auth-tokens.mdx)
- **Telemetry.** A self-hosted server sends a daily anonymous snapshot to `telemetry.multica.ai`. The endpoint is "compiled into the server and cannot be redirected"; `DO_NOT_TRACK=1` turns it off. There is a separate PostHog integration (`ANALYTICS_DISABLED`). [docs] — [SELF_HOSTING.md](https://raw.githubusercontent.com/multica-ai/multica/main/SELF_HOSTING.md)

#### Deployment, pricing, data location and China
- **Three ways to run it.**
  - Cloud: "sign up at multica.ai. No terminal required".
  - Desktop app: connects the computer it runs on as a runtime.
  - Self-host: Docker Compose or Helm.

  [README] — [README](https://raw.githubusercontent.com/multica-ai/multica/main/README.md)
- **Self-host requirements.**
  - Install by piping `raw.githubusercontent.com/.../install.sh` to bash; images come from GHCR.
  - Production sign-in emails need a `RESEND_API_KEY`; without one, codes are only printed to the server log.
  - S3 storage is optional; the default region is `us-west-2`.
  - Redis is needed for multi-replica relay.

  [docs] — [SELF_HOSTING.md](https://raw.githubusercontent.com/multica-ai/multica/main/SELF_HOSTING.md), [environment-variables](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/environment-variables.mdx)
- **Pricing.** Not found. Neither the README nor the docs mention prices, and multica.ai was blocked. The license points to "contact-sales" for commercial licenses. [license] — [LICENSE](https://raw.githubusercontent.com/multica-ai/multica/main/LICENSE)
- **Cloud data location.** Not stated in any fetched file. The cloud API is `api.multica.ai`. [docs] — [auth-tokens](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/auth-tokens.mdx)
- **China fit.**
  - The README and VISION exist in Chinese, and the docs are also published in Chinese, Japanese, Korean and French.
  - Many Chinese agent CLIs are supported (Kimi, Qwen, Qoder CN, Trae, CodeBuddy, DeepSeek Harness, MiniMax, CodeArts, DevEco).
  - New Feishu connections are mainland-only, and DingTalk and WeCom bots are available.

  [README] — [README](https://raw.githubusercontent.com/multica-ai/multica/main/README.md); [docs] — [channels](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/channels.mdx)

#### Integrations
- **GitHub.** A GitHub App auto-links PRs by issue key and shows PR state, CI and mergeability on the card. It can move an issue to `done` when its PRs merge, and can add a `Co-authored-by: multica-agent` trailer to agent commits. It "only reads the repositories authorized at install time; it never pushes commits, comments, or status checks". [docs] — [github-integration](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/github-integration.mdx)
- **Self-hosted Git.** GitLab, Gitea and Forgejo are supported on self-hosted Multica only: "Multica Cloud does not offer this entry point". [docs] — [github-integration](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/github-integration.mdx)
- **Linear and Jira.** No integration exists. Neither appears in the docs page list, which includes Lark, Slack, DingTalk, Telegram, GitHub and VCS pages. [docs] — [meta.json](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/meta.json)

#### Documented limitations and caveats
- **Unsandboxed runs.** Runs are unsandboxed by default and use permission bypass. [docs] — [security-model](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/security-model.mdx)
- **Destructive actions.**
  - "Any workspace member can delete an issue"; deletion "cannot be undone". [docs] — [issues](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/issues.mdx)
  - Removing a member "deactivates the runtimes they own, archives the agents bound to them, and cancels runs". [docs] — [members-roles](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/members-roles.mdx)
- **Parallel runs collide.** Parallel runs "compete for machine capacity, tool account quota, and the same working directory". [docs] — [daemon-runtimes](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/daemon-runtimes.mdx)
- **Sign-in hazard.** Self-host docs warn against setting `MULTICA_DEV_VERIFICATION_CODE` on a public instance, because "anyone who knows an email address can then log in". [docs] — [SELF_HOSTING.md](https://raw.githubusercontent.com/multica-ai/multica/main/SELF_HOSTING.md)
- **Open issues.** 967 open GitHub issues on 2026-10-03; their contents were not readable. [registry] — [Ranking 2026-10-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-10-03.csv)

### Inferences
- **How agents connect.** Agents connect through a **local daemon that starts headless CLI runs**. Multica does not attach to interactive sessions.
  - The CLI skill is the only path from a person's own Claude Code or Codex. It is pull-based (the model must decide to call the CLI), not hook-based, and it runs with the person's full-account `mul_` token, not a reduced agent scope.
  - So Longtable's two mechanisms remain distinct: automatic reporting through SessionStart, PostToolUse and Stop hooks, and agent tokens that cannot perform commitment actions.
- **"Review gate" and "blockers" are weaker than the marketing suggests.**
  - Review is a status convention that agents can set themselves; `done` is a convention plus PR-merge automation.
  - Blockers are a status plus an agent comment. There is no "waiting on person X" object and no dependency graph.
  - Longtable's explicit "who is stuck / who is needed" and ask-for-help objects, and its human confirmation of commitments, are not matched.
- **Multica is clearly stronger on:**
  - breadth (26 CLIs, squads, autopilots, Gantt and swimlane views, desktop and mobile apps);
  - IM coverage for Chinese teams (Feishu, DingTalk, WeCom);
  - GitHub, GitLab, Gitea and Forgejo PR linking;
  - momentum (about 52k stars, near-daily releases).
- **Multica is clearly weaker on:**
  - security posture (unsandboxed bypass mode, no prompt-injection gate, no approvals, no SSO or passkeys);
  - human notification channels (in-app and desktop only; IM bots are agent front-ends, not notifiers).
- **License risk for anyone offering Multica to others.** The license forbids hosting Multica for third parties without a commercial license, even for free. A Longtable-like hosted service could not be built on Multica code.
- **Possible China + US overlap.** The producer is a Hong Kong company (as Longtable's server is in Hong Kong), so their cross-border positioning may overlap. Where the cloud data actually sits is unknown.

### Gaps
- **Pricing and plans.** Multica Cloud pricing and plan limits are unknown, along with any free tier and enterprise terms. multica.ai was blocked and the docs are silent.
- **Cloud details.** The cloud's data location, hosting provider, privacy policy and whether it is reachable from mainland China were not found.
- **Managed runtimes.** Whether "Multica Cloud Fleet / Cloud Node" offers managed cloud runtimes to customers is not documented.
- **Open issues.** The contents of the 967 open GitHub issues, and any known security issues or advisories, could not be read because GitHub was blocked.
- **Install reachability.** Whether the raw.githubusercontent.com and GHCR install path works reliably from mainland China was not tested.

## Q2. Paperclip (paperclipai/paperclip): what it is, approvals and "Ask first", blocker dependencies, human participation, agent runtime, security, license, hosting

### Takeaway
Paperclip is "the control plane for autonomous AI companies". It is MIT-licensed and had 96,372 stars on 2026-10-03, the fastest growth of the three (+16,475 in September 2026). In Paperclip, "every employee is an agent", organised in an org chart with goals and budgets. Humans act as "the board" that approves, reviews and overrides.

Paperclip runs agents itself through heartbeats: local CLI/session adapters (it "starts or resumes local coding-tool sessions"), process and HTTP adapters, and cloud sandboxes. It is not a peer board for a small human team. Its governance is, however, the deepest of the three:
- board approvals;
- tool-gateway "Ask first" confirmations that execute signed, stored arguments once;
- first-class `blockedByIssueIds` dependencies;
- agent writes attributed to a "responsible user";
- an activity log of every mutation;
- an opt-in `low_trust_review` containment preset aimed at prompt-injected input.

The managed GitHub connection depends on Paperclip Cloud even when self-hosted. Paperclip Cloud itself has only a waitlist.

### Cited Findings

#### Identity, license and traction
- **Who makes it.** The license is MIT, "Copyright (c) 2025 Paperclip AI". The README says it is "maintained by the Paperclip team" and has "merged over 2,700 pull requests". [license] — [LICENSE](https://raw.githubusercontent.com/paperclipai/paperclip/master/LICENSE); [README] — [README](https://raw.githubusercontent.com/paperclipai/paperclip/master/README.md)
- **npm package.** `paperclipai` was first published as 0.1.1 on 2026-03-03T19:42Z and has 1,677 versions. Its only npm maintainer is `dotta`. The `latest` tag (2026.1001.0) was published 2026-10-02T01:48Z, and the package was last modified 2026-10-03T12:15Z. [registry] — [npm](https://registry.npmjs.org/paperclipai)
  - **Correction to open_source.md:** that file dates 2026.1001.0 to 2026-10-03; npm's timestamp is 2026-10-02.
- **Stars and growth.** On 2026-10-03: 96,372 stars, 16,318 forks, 2,693 open issues. GitHub description: "The open-source app everyone uses to manage agents at work". [registry] — [Ranking 2026-10-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-10-03.csv)

  Monthly star series:

  | Snapshot | 04-03 | 05-03 | 06-03 | 07-03 | 08-03 | 09-03 | 10-03 |
  |---|---|---|---|---|---|---|---|
  | Stars | 45,260 | 61,807 | 68,830 | 72,597 | 75,461 | 79,897 | 96,372 |

  It reached 45k stars within about one month of its first npm publish. Open issues grew from 652 to 2,693 over the same six months. [registry] — [04-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-04-03.csv), [05-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-05-03.csv), [06-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-06-03.csv), [08-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-08-03.csv), [09-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-09-03.csv)
- **Last commit.** 2026-10-03T11:52Z on `master`. Note that the default branch is `master`; raw `main` URLs return 404. [registry] — [Go proxy](https://proxy.golang.org/github.com/paperclipai/paperclip/@v/master.info)
- **Open-core signals.**
  - The spec splits features into "Free / V1 default" and "Pro / Enterprise". For example, "Project/issue ACLs and reviewer-only channels" and a richer policy editor are Pro/Enterprise.
  - It refers to "Paperclip EE".

  [spec] — [SPEC-implementation](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/SPEC-implementation.md), [PRODUCT.md](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/PRODUCT.md)

#### What it is
- **The pitch.** "Paperclip is the app people use to manage AI agents for work … If OpenClaw is an *employee*, Paperclip is the *company*." It is "a Node.js server and React UI that orchestrates a team of AI agents to run a business". "Manage business goals, not pull requests." [README] — [README](https://raw.githubusercontent.com/paperclipai/paperclip/master/README.md)
- **Who it is for.** The README's "right for you if" list includes "You have 20 simultaneous Claude Code terminals open", "You want to build autonomous AI organizations" and agents "running autonomously 24/7". [README] — [README](https://raw.githubusercontent.com/paperclipai/paperclip/master/README.md)
- **Core concepts.** "Paperclip is the control plane for autonomous AI companies." "Every employee is an agent." Every task traces back to the company goal. Principles include "Control plane, not execution plane. Paperclip orchestrates. Agents run wherever they run and phone home." [spec] — [PRODUCT.md](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/PRODUCT.md)
- **V1 decisions.** The spec fixes "Board | Single human board operator per deployment" and "Communication | Tasks + comments only (no separate chat system)". The roadmap later marks "✅ Multiple Human Users", described as "a clearer path from solo operator to real human teams". [spec] — [SPEC-implementation](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/SPEC-implementation.md); [README] — [ROADMAP](https://raw.githubusercontent.com/paperclipai/paperclip/master/ROADMAP.md)

#### Agent execution model
- **Four ways to run a heartbeat.**
  1. Local CLI/session adapters: "Paperclip starts or resumes local coding-tool sessions such as Claude Code, Codex, Gemini, OpenCode, Pi, and Cursor, then tracks the run".
  2. Run a command (process adapter).
  3. "Fire and forget a request" to an external agent (HTTP adapter).
  4. External adapter plugins.

  [spec] — [PRODUCT.md](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/PRODUCT.md)
- **Built-in adapters.** Claude Code, Codex, Cursor, Gemini CLI, OpenCode, Pi, Hermes, Grok, Kimi Code, OpenClaw, plus process and HTTP integrations. [README] — [ROADMAP](https://raw.githubusercontent.com/paperclipai/paperclip/master/ROADMAP.md)
- **Where runs happen.**
  - Sandbox providers cover E2B, Cloudflare, Daytona, Modal, Novita and Kubernetes. [README] — [ROADMAP](https://raw.githubusercontent.com/paperclipai/paperclip/master/ROADMAP.md)
  - Workspaces can be isolated using "git worktrees, operator branches".
  - A native Paperclip Runner, written in Rust, is the self-hosted default when built from source.

  [README] — [README](https://raw.githubusercontent.com/paperclipai/paperclip/master/README.md)
- **Engine and sandbox defaults.**
  - The legacy Codex, Claude, Gemini and Kimi local adapters default to the ACP engine.
  - "Codex CLI defaults permit workspace writes and network access for Paperclip coordination without disabling its sandbox".
  - No `bypassPermissions` or `dangerously-skip-permissions` default was found in the fetched docs.

  [spec] — [SPEC-implementation §11.1](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/SPEC-implementation.md)
- **When agents wake.** For assigned work, follow-up messages, optional timer heartbeats and routines. "A mention alone does not assign work or wake another agent." [README] — [README](https://raw.githubusercontent.com/paperclipai/paperclip/master/README.md)
- **How agents talk to Paperclip.** The agent skill begins: "You run in **heartbeats** — short execution windows triggered by Paperclip". `PAPERCLIP_API_KEY` is "auto-injected as a short-lived run JWT". [spec] — [skills/paperclip/SKILL.md](https://raw.githubusercontent.com/paperclipai/paperclip/master/skills/paperclip/SKILL.md)
- **Connecting from your own session.** "Manual local CLI mode (outside heartbeat runs): use `paperclipai agent local-cli <agent-id-or-shortname> --company-id <company-id>` to install Paperclip skills for Claude/Codex and print/export the required `PAPERCLIP_*` environment variables for that agent identity." So a person's own interactive Claude Code or Codex can act as a Paperclip agent. [spec] — [SKILL.md](https://raw.githubusercontent.com/paperclipai/paperclip/master/skills/paperclip/SKILL.md)
- **No hooks.** No Claude Code or Codex hook integration was found in the fetched Paperclip files (grep, 2026-10-03).

#### Multi-human features
- **Deployment modes.**
  - `local_trusted`: "No login required", loopback only, for a "Single-operator local machine workflow".
  - `authenticated` (private or public): "Login required", using Better Auth sessions.
  - The network address can be bound to `loopback`, `lan`, `tailnet` or `custom`.

  [spec] — [DEPLOYMENT-MODES.md](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/DEPLOYMENT-MODES.md)
- **People and roles.** Paperclip offers "human roles and permissions … company memberships, and invite flows". The spec lists invites, join requests, instance roles (`instance_admin`), principal permission grants and board API keys. A "Viewer" board role exists. [README] — [README](https://raw.githubusercontent.com/paperclipai/paperclip/master/README.md); [spec] — [SPEC-implementation](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/SPEC-implementation.md), [DEPLOYMENT-MODES.md](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/DEPLOYMENT-MODES.md)
- **Assigning and claiming.**
  - "Assign tasks to agents or people." [README] — [README](https://raw.githubusercontent.com/paperclipai/paperclip/master/README.md)
  - Each task has a single assignee, and an "atomic checkout required for `in_progress` transition".
  - Assigning a task to a person requires that person to be an active member.

  [spec] — [SPEC-implementation](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/SPEC-implementation.md), [DEPLOYMENT-MODES.md](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/DEPLOYMENT-MODES.md)
- **Enforced status flow.**

  | From | Allowed next statuses |
  |---|---|
  | backlog | todo, cancelled |
  | todo | in_progress, blocked, cancelled |
  | in_progress | in_review, blocked, done, cancelled |
  | in_review | in_progress, done, cancelled |
  | blocked | todo, in_progress, cancelled |

  [spec] — [SPEC-implementation §8.2](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/SPEC-implementation.md)
- **Blocker dependencies.**
  - "First-class blockers (`blockedByIssueIds`)". Blocked issues "should stay idle while blockers remain unresolved". When the final blocker finishes, an `issue_blockers_resolved` wake starts the work.
  - A `cancelled` blocker "does not satisfy the dependency".
  - Escalation goes from agent to manager to the board.

  [spec] — [execution-semantics.md](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/execution-semantics.md), [SPEC-implementation §9.6](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/SPEC-implementation.md)
- **Work objects.** Tasks support comments, documents with revisions and anchored passage comments, attachments, work products, labels and company-wide search. [README] — [README](https://raw.githubusercontent.com/paperclipai/paperclip/master/README.md), [ROADMAP](https://raw.githubusercontent.com/paperclipai/paperclip/master/ROADMAP.md)
- **Notifications.**
  - Each person has an in-app inbox ("Mine") showing failed runs and issue activity.
  - Experimental chat and email connectors (Slack, Discord, Telegram, AgentMail, plus Microsoft Teams, GitHub and iMessage Photon) are entry points for conversations with agents.
  - No email or push notification channel for humans was found.

  [spec] — [SPEC-implementation §9.11](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/SPEC-implementation.md), [SKILL.md](https://raw.githubusercontent.com/paperclipai/paperclip/master/skills/paperclip/SKILL.md); [README] — [README](https://raw.githubusercontent.com/paperclipai/paperclip/master/README.md)
- **Visibility.** "board + all in-company agents can see all work objects by default". Project- and issue-level privacy is "deferred to Pro/Enterprise controls". [spec] — [SPEC-implementation §3, §9.5](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/SPEC-implementation.md)

#### Human-in-the-loop and security
- **Board approvals.**
  - Approvals of type `hire_agent` and `approve_ceo_strategy` move from `pending` to `approved`, `rejected` or `cancelled`.
  - Before the first strategy approval, the CEO agent "may only draft tasks".
  - The board can pause, terminate or reassign at any time.
  - Agents cannot "bypass approval gates", change company budgets or touch auth and keys. Approving is board-only.

  [spec] — [SPEC-implementation §9.2–9.3, §12](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/SPEC-implementation.md)
- **"Ask first" on tool calls.**
  - Each connection action is set to Allowed, Ask first or Off.
  - An Ask-first call creates a server-owned confirmation, and "No provider call runs while this review is pending". The default approval lifetime is one hour.
  - "Approve & run executes the signed, stored arguments once. Decline executes nothing."
  - "Always allow" saves a trust rule for that agent, connection and action, scoped to the project if there is one. A changed tool definition needs review again.
  - The agent cannot complete its task while a linked action is pending.

  [spec] — [TASK-REVIEWS.md](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/connections/TASK-REVIEWS.md), [SPEC-implementation §12.4](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/SPEC-implementation.md)
- **Agent permissions.**
  - Agent writes on visible issues (comment, update, create child, assign) are company-wide by default ("shared default-open issue writes").
  - Both the agent and the "responsible user" behind the run must be authorised.
  - A run may make at most 20 cross-issue writes.
  - "Agent @-mentions are context links only".
  - Comment attribution cannot be chosen by the client; "spoof attempts fail with an audited 422".

  [spec] — [SPEC-implementation §9.3.1](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/SPEC-implementation.md)
- **Prompt-injection containment (`low_trust_review`).** This is "an opt-in containment preset for automated work that may consume hostile or prompt-injected input, such as untrusted pull requests, external tickets, dependency diffs".
  - It "prevents raw untrusted output from being automatically promoted into higher-trust agent context".
  - It turns off reporting from child task to parent by default, because that is "a prompt-injection promotion path".
  - It requires the sandbox driver and an isolated workspace, rejects inline secrets, and forbids assigning work to board users.
  - Paperclip admits that injection during an authorised owner chat "remains a model-level risk".

  [spec] — [LOW-TRUST-PRESETS.md](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/LOW-TRUST-PRESETS.md)
- **Secrets.**
  - Company secrets and per-person secret values use encrypted storage and are supplied by reference.
  - Agent API keys are stored only as hashes.
  - Secrets are redacted in logs. [spec] — [SPEC-implementation §16](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/SPEC-implementation.md); [README] — [README](https://raw.githubusercontent.com/paperclipai/paperclip/master/README.md)
  - Exported company packages omit secret values, but "plain environment values and local paths can remain". [README] — [README](https://raw.githubusercontent.com/paperclipai/paperclip/master/README.md)
- **Audit.** "every mutation writes `activity_log`". Every issue update records the actor, responsible user, run and before/after values. [spec] — [SPEC-implementation §15.3, §9.3.1](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/SPEC-implementation.md)
- **Sign-in and bootstrap.**
  - Sign-in uses Better Auth sessions. Cloud-managed instances use Paperclip Cloud sign-in.
  - In authenticated/private mode, the first browser session to claim the instance becomes admin ("whichever path wins first").
  - Auth rate limiting is **off by default in private mode**.
  - "SSO" appears only in the README's marketing pillar table ("SSO, GRC, RBAC & cost controls"). No SSO or passkey mechanism was found in the fetched specs.

  [spec] — [DEPLOYMENT-MODES.md](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/DEPLOYMENT-MODES.md); [README] — [README](https://raw.githubusercontent.com/paperclipai/paperclip/master/README.md)
- **Telemetry.** Anonymous telemetry is enabled by default and can be disabled with `PAPERCLIP_TELEMETRY_DISABLED=1` or `DO_NOT_TRACK=1`. [README] — [README](https://raw.githubusercontent.com/paperclipai/paperclip/master/README.md)

#### Deployment, pricing, data location and China
- **Self-host.** "Open source. Self-hosted. No Paperclip account required." Install with `npx paperclipai@latest onboard --yes` (Node.js 24.11+).
  - Locally, "a single Node.js process manages an embedded Postgres and local file storage".
  - For a team, use authenticated mode on a private network such as Tailscale, or Docker.

  [README] — [README](https://raw.githubusercontent.com/paperclipai/paperclip/master/README.md)
- **Cloud.** There is a "Paperclip Cloud waitlist". [README] — [README](https://raw.githubusercontent.com/paperclipai/paperclip/master/README.md) The roadmap marks "🟡 Cloud deployments", saying multi-tenant isolation and cloud-managed bootstrap have shipped so far. [README] — [ROADMAP](https://raw.githubusercontent.com/paperclipai/paperclip/master/ROADMAP.md)
- **GitHub depends on Paperclip Cloud.** "GitHub is a Paperclip Cloud-managed GitHub App connection with an advanced PAT compatibility method. Cloud owns the fixed public OAuth callback and signed webhook inbox." "A self-hosted instance needs one Paperclip Cloud approval before its first managed connection." [spec] — [GITHUB.md](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/connections/GITHUB.md)
- **Pricing, data location, China.**
  - Pricing: not found.
  - Cloud data location: not found.
  - China: no China-specific channels or docs were found; a Kimi Code adapter exists. [README] — [ROADMAP](https://raw.githubusercontent.com/paperclipai/paperclip/master/ROADMAP.md)

#### Integrations
- **GitHub.**
  - The managed GitHub App connection covers repository tools, Git and `gh`.
  - A "GitHub Code Review Bot" is gated behind experimental chat connectors.
  - "Shared Agents Use Personal GitHub Identities": a shared agent resolves the GitHub identity of the person directing the work. If that identity is unavailable, "It never falls through to another person".

  [spec] — [GITHUB.md](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/connections/GITHUB.md)
- **Other connections.** Notion, Railway and custom MCP servers, with per-action Allowed / Ask first / Off. [README] — [README](https://raw.githubusercontent.com/paperclipai/paperclip/master/README.md)
- **Linear, Jira, Asana.** Not built. They are on the roadmap as "⚪ Bring-your-own-ticket-system (Asana / Linear / Jira as on-ramps)". [README] — [ROADMAP](https://raw.githubusercontent.com/paperclipai/paperclip/master/ROADMAP.md)

#### Documented limitations and caveats
- **Budget stops lag.** "Enforcement uses recorded spend; usage reporting and in-flight work can delay a stop." [README] — [README](https://raw.githubusercontent.com/paperclipai/paperclip/master/README.md)
- **Unfinished features.**
  - Agent Chat is experimental and "off by default"; the desktop app is not built yet ("⚪"). [README] — [ROADMAP](https://raw.githubusercontent.com/paperclipai/paperclip/master/ROADMAP.md)
  - Local stdio MCP "fail closed by default" on public deployments. [spec] — [DEPLOYMENT-MODES.md](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/DEPLOYMENT-MODES.md)
- **Design scope.** The product definition says "Do not build enterprise-grade RBAC first" and "Do not build a complete Jira/GitHub replacement". [spec] — [PRODUCT.md](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/PRODUCT.md)
- **Complexity and churn.**
  - The implementation spec is about 119 KB and the execution-semantics document about 133 KB of liveness and recovery rules.
  - 2,693 open issues and 1,677 npm versions in 7 months. [registry] — [npm](https://registry.npmjs.org/paperclipai), [Ranking 2026-10-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-10-03.csv)

### Inferences
- **It is AI-company orchestration, not a team board.**
  - Humans are supervisors ("board") and occasionally assignees. Agents are the employees.
  - A 2–5 person team would have to model each person's agent as an "employee" in an org chart and let Paperclip launch it.
  - The `agent local-cli` mode lets a person's interactive session act as such an agent, but there are no hooks, so progress reporting depends on the model calling the API.
- **Paperclip is stronger than Longtable on governance depth.**
  - Board approvals.
  - Ask-first confirmations that are signed and replay-safe.
  - Enforced status transitions and atomic checkout.
  - Real blocker dependencies with automatic wake.
  - A per-mutation activity log.
  - The only prompt-injection containment among the three: the `low_trust_review` preset and the block on promoting child output to the parent.
- **The trust models differ in where the gate sits.** Paperclip's gate is on agent capability: low-trust agents and sandboxed runs. Longtable's gate is on content: a recipient must accept text before their agent sees it. Paperclip has no per-message acceptance step, and nothing like a passkey.
- **Paperclip is weaker for a 2–5 person China+US team:**
  - It expects a single operator by default (V1 decision) and makes issues visible company-wide.
  - Human notifications are in-app only.
  - There are no WeChat, Feishu, DingTalk or WeCom channels.
  - Its GitHub connection depends on Paperclip Cloud, whose availability in China is unknown.
  - Setup is heavy: Node 24, Postgres, an org chart and budgets.

### Gaps
- **Pricing.** Paperclip Cloud pricing, launch date and region are unknown; paperclip.ing was blocked.
- **People behind it.** The founder or company identity beyond the npm handle `dotta` and "Paperclip AI" was not verified.
- **Who approves "Ask first".** It is unclear which human roles may approve Ask-first actions (any board non-viewer, or only certain roles?). The fetched docs say only "the human decision".
- **Claude Code permission mode.** The exact mode Paperclip uses when it launches Claude Code (ACP engine defaults) was not found.
- **SSO.** Whether SSO exists in Community Edition or only in EE or Cloud is unconfirmed.
- **Public docs.** The docs site's source (docs.paperclip.ing) is not in the repo, so user-facing guides (approvals, connector access model) were read only through internal specs.

## Q3. Agor (preset-io/agor): what it is, multiplayer features, agent runtime, BUSL-1.1 terms, hosting, security

### Takeaway
Agor is built by Preset, Inc. and led by Maxime Beauchemin (@mistercrunch), who is associated with Apache Superset and Airflow. Neither their title at Preset nor the size of the team was verified. It is a self-hosted, multiplayer web workspace in which agents run **inside Agor**. The daemon's executor starts Claude Code, Codex, Gemini, OpenCode or Copilot through their SDKs, on a git branch (worktree) with its own dev environment. People drive these sessions from the browser.

What Agor offers:
- **Collaboration:** Figma-style collaboration (live cursors, facepile, spatial comments, shared tmux terminals).
- **Permissions:** strong RBAC (board and branch roles, file-access tiers).
- **Credentials:** per-user credentials and per-user MCP OAuth.
- **Isolation:** a fail-closed bubblewrap filesystem sandbox on Linux.

What Agor lacks:
- task assignment to people, blockers and claims (work is organised by branch, and "cards" are moved around by AI teammates);
- email notifications;
- prompt-injection controls ("Nothing committed yet").

External Claude Code or Codex can connect to Agor's MCP server with a personal API key, but that key acts with the user's full authority.

The license is BUSL-1.1: production use is allowed except offering Agor as a commercial agent-orchestration service, and each version becomes Apache-2.0 by 2029-01-15 at the latest. Agor Cloud has been a private beta, with pricing to be decided, since 2025-11.

### Cited Findings

#### Identity, license and traction
- **Who makes it.**
  - The licensor is "Preset, Inc."; the license says "The Licensed Work is (c) 2025 Preset, Inc." [license] — [LICENSE](https://raw.githubusercontent.com/preset-io/agor/main/LICENSE)
  - The README says Agor was "Heavily prompted by @mistercrunch (Preset, Apache Superset, Apache Airflow), built by an army of Claudes and Codexes". [README] — [README](https://raw.githubusercontent.com/preset-io/agor/main/README.md)
  - npm lists the author as Maxime Beauchemin, with maintainers `mistercrunch` and `antonioriverocode`. [registry] — [npm](https://registry.npmjs.org/agor-live)
- **License terms (BUSL-1.1).**
  - Additional Use Grant: "You may make production use of the Licensed Work, provided that you may not use the Licensed Work for an Agor Offering".
  - An "Agor Offering" is "a commercial product or service offered to third parties whose primary purpose is to provide the functionality of the Licensed Work to orchestrate or manage AI coding agents", including hosted, managed or bundled offerings.
  - "Consulting, support, and integration services, including operating a deployment solely for a specific customer's own internal use, are not an Agor Offering."
  - Change Date: 2029-01-15, or the fourth anniversary of a version's first public release, whichever comes first. After that, the version becomes Apache-2.0.

  [license] — [LICENSE](https://raw.githubusercontent.com/preset-io/agor/main/LICENSE)
- **How the README describes the license.** "Agor is source-available, not open source, before the Change Date." [README] — [README](https://raw.githubusercontent.com/preset-io/agor/main/README.md)
- **Release history.**
  - The npm package `agor-live` was first published on 2025-10-27 as 0.3.7 and has 114 versions. The latest is 0.26.9 (2026-10-02T22:31Z). [registry] — [npm](https://registry.npmjs.org/agor-live)
  - The changelog's oldest entry is 0.10.0 (2025-12-14). [docs] — [CHANGELOG](https://raw.githubusercontent.com/preset-io/agor/main/CHANGELOG.md)
  - Last commit on `main`: 2026-10-03T00:48Z. [registry] — [Go proxy](https://proxy.golang.org/github.com/preset-io/agor/@v/main.info)
- **Stars.** Not obtained. Agor does not appear in any per-language top-100 list in the 2026-10-03 ranking. If its primary language is TypeScript (likely from the stack, not verified), it has fewer than 45,457 stars. This is a weak bound. [registry] — [Ranking 2026-10-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-10-03.csv)

#### What it is and its multiplayer features
- **The pitch.** "Team command center for all things agentic … a self-hosted, multiplayer-ready web workspace for running coding agents … on isolated git branches … Agents run in the browser instead of a terminal".
- **Core concepts.**
  - Branches: one branch is one feature or PR, with its own worktree and dev environment.
  - Sessions and trees: sessions can be forked or spawned.
  - Boards and zones: a Figma-like 2D canvas, where "Drop a branch into a zone to fire a templated prompt".

  [README] — [README](https://raw.githubusercontent.com/preset-io/agor/main/README.md)
- **Multiplayer.**
  - Live cursors update about every 100 ms.
  - A facepile shows who is online.
  - Spatial comments can be threaded and support `@username` mentions. They attach to a board, zone, branch or session.
  - An "attention pulse" highlights branches that need input.
  - Favicon status dots, and completion chimes for finished sessions.
  - Shared tmux terminals let people see each other's keystrokes.

  [docs] — [multiplayer-social](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/guide/multiplayer-social.mdx)
- **Home view.** Version 0.26.9 (2026-10-02) added a Home view with "Needs you" and "My work", plus a teammate directory. [docs] — [CHANGELOG](https://raw.githubusercontent.com/preset-io/agor/main/CHANGELOG.md)
- **Roles.**
  - Board roles: Viewer, Editor, Manager.
  - Branch roles: Viewer, Collaborator (can create and prompt sessions), Manager.
  - Branch file access: none, read or read/write, set per person or group.
  - Ownership can be transferred.
  - Account roles mentioned in the docs include viewer, member, admin and superadmin.

  [docs] — [permissions](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/guide/permissions.mdx), [internal-mcp](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/guide/internal-mcp.mdx)
- **Prompting someone else's session.** Collaborators may prompt another person's branch-home session only when both the workspace setting and the branch permissions allow it. "The task runs as the actual caller." [docs] — [permissions](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/guide/permissions.mdx)
- **No task workflow objects.**
  - Cards: "A card's zone is its status. No separate status field". Cards are created and moved by AI "teammates" through MCP, and "do not trigger automation or spawn sessions". Cards are in beta.
  - No assignee, blocker, claim or review-gate objects were found in the docs.
  - Review is modelled by zones with prompt triggers, for example a "Human PR Review" zone.

  [docs] — [cards](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/guide/cards.mdx), [internal-mcp](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/guide/internal-mcp.mdx)
- **AI teammates.** "Long-lived AI coworkers" with a knowledge-base memory namespace, skills, MCP tools, gateway channels and schedules. [README] — [README](https://raw.githubusercontent.com/preset-io/agor/main/README.md)
- **Message gateway.** Slack, Discord, GitHub (`@agor` mentions in issue and PR comments, picked up by polling), Shortcut and Microsoft Teams act as "portals into Agor sessions". The agent's reply is posted back to the thread. [docs] — [message-gateway](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/guide/message-gateway.mdx)
- **Notifications.** No email notification channel and no Chinese chat apps (Feishu, DingTalk, WeCom) were found. [docs] — [message-gateway](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/guide/message-gateway.mdx)

#### Agent execution model
- **Architecture.**
  - The daemon (FeathersJS) holds the database, services, WebSocket and MCP endpoint.
  - A "process-isolated" executor "spawns agents via their SDKs locally, inside the filesystem sandbox, or through a delegated external substrate".
  - Storage: LibSQL or Postgres (`~/.agor/agor.db`), with worktrees in `~/.agor/worktrees/`.

  [README] — [README](https://raw.githubusercontent.com/preset-io/agor/main/README.md)
- **Supported agents and their limits.**
  - Claude Code, Codex, Gemini (beta, AI Studio keys only), OpenCode, Copilot and Cursor (beta).
  - Permission requests work fully for Claude, are "Basic" for Codex and have "No Manual" option for Gemini.
  - Codex streams tool events only, not text.
  - Agor turns off Codex's native multi-agent feature.

  [docs] — [sdk-comparison](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/guide/sdk-comparison.mdx)
- **Tool approvals.** Permission modes are ask / auto (acceptEdits) / allow-all (bypassPermissions). Agor "shows interactive permission UI with approve/deny buttons". [docs] — [sdk-comparison](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/guide/sdk-comparison.mdx)
- **Execution modes.**

  | Mode | Isolation |
  |---|---|
  | `simple` | "none beyond daemon-user permissions" |
  | `sandbox` | "fail-closed bubblewrap filesystem mounts"; Linux only; "filesystem isolation, not network isolation" |
  | `delegated` | an operator-supplied substrate; Agor "does not claim to prove an external launcher's isolation" |

  [docs] — [multiplayer-unix-isolation](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/guide/multiplayer-unix-isolation.mdx)
- **Connecting from your own session.**
  - External Claude Code (`claude mcp add … -H 'X-API-Key: ${AGOR_API_KEY}'`) or Codex (`~/.codex/config.toml` with `env_http_headers`) can connect to `/mcp` using a personal API key.
  - "An external personal API key identifies you but does not imply an Agor session." You can add an `X-Agor-Session-Id` header.
  - "Anything a user can do in Agor, an agent can do too", including "invite new users".

  [docs] — [internal-mcp](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/guide/internal-mcp.mdx)
- **No hooks.** No Claude Code or Codex hook integration was found in the fetched Agor files (grep, 2026-10-03).

#### Human-in-the-loop and security
- **Credentials.**
  - Each user has encrypted environment variables (scoped Global or per Session) and their own credentials for each agent tool.
  - "Shared machine CLI login state is not used implicitly."
  - Each user authorises their own MCP OAuth grant, with PKCE and strict issuer checks.

  [docs] — [multiplayer-social](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/guide/multiplayer-social.mdx)
- **MCP session tokens.**
  - These are short-lived JWTs that act as the caller. Viewers never receive one.
  - "There is no revocation mechanics … The authorised blast radius of a leak is bounded by `exp` (default 24h)."

  [docs] — [internal-mcp](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/guide/internal-mcp.mdx)
- **Sign-in.**
  - Three strategies: local email and password (JWT), JWT, and API keys (`agor_sk_…`).
  - "On a fresh install with zero users, the daemon auto-creates an admin user", writing the password to `~/.agor/admin-credentials`.
  - No SSO, OIDC or passkeys were found in the fetched docs.

  [docs] — [architecture](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/guide/architecture.mdx)
- **Prompt injection.** The Agor Cloud post lists it as a risk ("Prompt injection risks when agents have filesystem access"). It is on the roadmap: "Prompt-injection guardrails. Exploring tooling … Nothing committed yet". [docs] — [blog/agor-cloud](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/blog/agor-cloud.mdx)
- **Audit log.** A formal audit log ("session creation, prompt submissions, branch changes, owner edits, and admin actions. Queryable, retained, exportable") is described as an **Agor Cloud** feature. The open-source docs say only that "Sessions capture every MCP action". [docs] — [blog/agor-cloud](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/blog/agor-cloud.mdx), [internal-mcp](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/guide/internal-mcp.mdx)
- **Recent security changes in the changelog.**
  - 0.26.2 (2026-09-07): "The authenticated-member open-access fallback is removed".
  - 0.26.0 (2026-08-30): tenant authority made "fail-closed end to end".
  - 0.26.4 (2026-09-20): MCP authorisation fails closed.
  - 0.17.0 (2026-04-23): "Stop leaking secrets via sudo argv and startup logs".

  [docs] — [CHANGELOG](https://raw.githubusercontent.com/preset-io/agor/main/CHANGELOG.md)
- **Terminal warning.** In the default `simple` mode, the web terminal "gives `member+` users access to daemon-readable files (config, DB, JWT secret)". [docs] — [multiplayer-social](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/guide/multiplayer-social.mdx)

#### Deployment, pricing, data location and China
- **Self-host.** `npm install -g agor-live`, then `agor init`, `agor daemon start` and `agor open` (Node ≥ 22.12). Homebrew and Docker are also supported. [README] — [README](https://raw.githubusercontent.com/preset-io/agor/main/README.md)
- **Agor Cloud.** "Opening a Private Beta" (blog post by Maxime Beauchemin dated 2025-11-23). Its isolation paragraph ("Agor does not manufacture isolation by creating host Unix accounts") matches the post-0.25 design, so the post appears to have been edited after publication. Whether the beta is still the current status on 2026-10-03 is unconfirmed.
  - A "managed single-tenant instance per team, hosted on our infrastructure".
  - "Managed Private Cloud" inside the customer's own AWS or GCP account.
  - Customers bring their own model keys ("We don't sell tokens").
  - "Pen-tested"; "SOC 2 Type II audit cycle in flight".
  - Pricing: "We're figuring this out during the private beta".

  [docs] — [blog/agor-cloud](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/blog/agor-cloud.mdx)
- **Run self-hosted Agor behind a VPN.** The same post advises self-hosters: "you should think carefully about where you put it (and probably run it behind a VPN)". [docs] — [blog/agor-cloud](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/blog/agor-cloud.mdx)
- **China.** Nothing China-specific was found.

#### Integrations
- **GitHub.** Through the gateway, `@agor` in issue and PR comments starts a session. Replies are posted as the app's bot, and "only the agent's final response is posted to GitHub". [docs] — [message-gateway](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/guide/message-gateway.mdx)
- **Other services.** Shortcut is a native gateway. Linear and other tools are reachable only as MCP servers the user connects ("Bring your tools (Slack, Linear, GitHub, HubSpot …)"). Jira appears only as an example of importing cards in bulk through MCP tools. [docs] — [multiplayer-social](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/guide/multiplayer-social.mdx), [cards](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/guide/cards.mdx)

#### Documented limitations and caveats
- **Teams gateway.** The Microsoft Teams gateway "fails closed on PostgreSQL" when several daemons run. [docs] — [message-gateway](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/guide/message-gateway.mdx)
- **Web terminals.** They lack the executor's continuous permission rechecks ("Closing that live-terminal parity gap requires separate terminal lifecycle work"). [docs] — [multiplayer-unix-isolation](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/guide/multiplayer-unix-isolation.mdx)
- **Cursor support.** Cursor is refused in per-branch SDK-home mode. [docs] — [multiplayer-unix-isolation](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/guide/multiplayer-unix-isolation.mdx)
- **README contradicts the docs.** The README still promises "Unix-level isolation", but the docs say "The former `strict` and `insulated` modes were removed in Agor 0.25. Agor no longer creates host users or groups". [README] — [README](https://raw.githubusercontent.com/preset-io/agor/main/README.md); [docs] — [multiplayer-unix-isolation](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/guide/multiplayer-unix-isolation.mdx)

### Inferences
- **Agor replaces the terminal; Longtable sits beside it.** Agents run where the Agor daemon and its worktrees live.
  - For a team spread across China and the US, that means one shared server holding repos and executing agents, or each person running a solo Agor, which gives no shared board.
  - The external MCP route lets a person's own Claude Code or Codex read and write Agor, but with their full user authority and without hooks.
- **Agor is clearly stronger than Longtable on:**
  - real-time presence and collaboration UX;
  - per-branch environments;
  - RBAC granularity;
  - per-user credential isolation;
  - fork and spawn session trees.
- **Agor is clearly weaker on:**
  - task-level coordination (no assigning work to people, no blockers, claims or ask-for-help);
  - human notifications (in-app only);
  - prompt-injection defence;
  - accountability for commitments (agents can do anything their user can, including inviting users).
- **License.** A Longtable-like hosted product built on Agor would be an "Agor Offering" and is barred until each version converts to Apache-2.0.

### Gaps
- **Stars and maintainers.** Star count, forks, open issues and contributor and team size are unknown (GitHub blocked; not in the ranking CSV).
- **Agor Cloud.** Price, regions and whether it has left private beta are unknown.
- **Who approves tool prompts.** It is unclear who may answer tool-permission prompts in a shared session: the session owner, or any Collaborator with prompt rights.
- **Audit log in open source.** Whether the open-source edition has any exportable audit log is unconfirmed.

## Q4. Would a 2–5 person team, each member running Claude Code or Codex locally, adopt these easily? What would change, and where is Longtable clearly weaker or stronger?

### Takeaway
None of the three fits "keep working in your own Claude Code or Codex session, and let the board update itself" without changing how people work. All three are built around the product running the agent:
- Multica: a headless daemon on each person's machine.
- Paperclip: server-driven heartbeats and runners.
- Agor: browser sessions on a shared host.

Each offers only a side door for a person's own session: Multica's CLI skill, Paperclip's `agent local-cli` and Agor's external MCP with a personal API key. None documents Claude Code or Codex hooks.

The easiest of the three for that team is Multica:
- It is a familiar issue board.
- It runs on local machines.
- It has Chinese chat bots.

But each person must install a daemon that runs agents unsandboxed with permission bypass, and must accept that agents can change statuses themselves.

Longtable is clearly stronger on:
- working inside existing sessions (hooks);
- human confirmation of commitments, with passkeys;
- gating others' text before an agent sees it;
- email and WeChat notifications.

Longtable is clearly weaker on breadth, execution features, GitHub integration and community.

### Cited Findings
- **Multica: per-person setup.**
  - Each member who runs agents installs the CLI and daemon. [docs] — [SELF_HOSTING.md](https://raw.githubusercontent.com/multica-ai/multica/main/SELF_HOSTING.md)
  - Work starts when an issue is assigned or an agent is @mentioned, and the daemon runs it unattended under `bypassPermissions`. [docs] — [security-model](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/security-model.mdx)
  - The docs recommend a dedicated Unix user, a container or a VM. [docs] — [security-model](https://raw.githubusercontent.com/multica-ai/multica/main/apps/docs/content/docs/security-model.mdx)
  - A person's own session can drive Multica through the CLI skill, which "should ask before making state changes". [README of skill] — [multica-cli](https://raw.githubusercontent.com/multica-ai/multica-cli/main/README.md)
- **Paperclip: built around heartbeats.**
  - Agents "run in **heartbeats** … triggered by Paperclip". [spec] — [SKILL.md](https://raw.githubusercontent.com/paperclipai/paperclip/master/skills/paperclip/SKILL.md)
  - The quickstart defaults to single-operator `local_trusted` mode. Teams need authenticated mode on a private network or Docker. [README] — [README](https://raw.githubusercontent.com/paperclipai/paperclip/master/README.md); [spec] — [DEPLOYMENT-MODES.md](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/DEPLOYMENT-MODES.md)
  - V1 assumes a "Single human board operator per deployment". [spec] — [SPEC-implementation](https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/SPEC-implementation.md)
- **Agor: agents run in Agor.** "Agents run in the browser instead of a terminal". The executor spawns the SDKs on the daemon host. [README] — [README](https://raw.githubusercontent.com/preset-io/agor/main/README.md) Self-hosters are advised to run behind a VPN, and Agor Cloud is a private beta. [docs] — [blog/agor-cloud](https://raw.githubusercontent.com/preset-io/agor/main/apps/agor-docs/content/blog/agor-cloud.mdx)
- **No hooks anywhere.** No hook-based (SessionStart, PostToolUse, Stop) integration appears in any fetched Multica, Paperclip or Agor file (grep on 2026-10-03). See the source lists in Q1–Q3.

### Inferences
- **What the team would have to change, per product:**
  - **Multica.**
    - Install the daemon (or Desktop app) on each machine and sign in.
    - Re-express work as issues, and agents as named "agent" identities bound to a runtime.
    - Accept unattended runs in daemon-managed workdirs instead of interactive pairing.
    - Isolate the daemon user.
    - Rely on in-app or desktop notifications. The chat bots answer only for agents.
    - Lowest friction of the three for a mixed China+US team, given the Chinese docs, Feishu/DingTalk/WeCom bots and Chinese CLIs.
  - **Paperclip.**
    - Adopt the "AI company" model: org chart, goals, budgets, heartbeats.
    - Self-host an authenticated instance reachable by everyone (for example over Tailscale), or wait for Cloud.
    - Use Paperclip Cloud approval for the managed GitHub connection.
    - Highest conceptual overhead. Its own pitch targets running "autonomous AI organizations" rather than coordinating 2–5 humans.
  - **Agor.**
    - Move coding from the terminal into Agor's browser sessions on a shared host that holds every repo and credential, or join the Agor Cloud beta.
    - Coordinate through branch cards, zones and comments, since there are no task, assignee or blocker objects.
    - Strongest real-time "see what everyone's agent is doing" experience, but the biggest change in daily workflow.

- **Where Longtable is clearly stronger or weaker.** "Longtable" means the design described by the caller. The verdicts are inferences from Q1–Q3.

  | Dimension | Multica | Paperclip | Agor | Verdict for Longtable |
  |---|---|---|---|---|
  | Agent model | Product spawns headless runs (local daemon) | Product runs heartbeats (adapters, runner, sandboxes) | Product runs SDK sessions (shared host) | **Stronger** for "keep my own session" teams: none of the three uses hooks |
  | Attaching your own session | CLI skill, using the person's full PAT, called by the model | `agent local-cli`, using an agent identity | External MCP, using the person's full API key | **Stronger**: automatic hook reporting plus restricted agent tokens |
  | Assigning work to a person | Yes (member assignee) | Yes (`assigneeUserId`) | No task objects | Parity with Multica and Paperclip |
  | Claiming work | Machine-level run claim | Atomic checkout and execution locks | None | Paperclip is **stronger** (locks); Longtable is at parity or better versus Multica and Agor |
  | Blockers and asking for help | Status and comment only | First-class `blockedByIssueIds` with auto-wake; escalation to manager or board | None | Longtable's "who is stuck / who is needed" is **stronger** than Multica and Agor; Paperclip's dependency graph is **stronger** on dependencies |
  | Review and commitment gates | `in_review` is only a convention; agents can change status | Board approvals, Ask-first with signed arguments, enforced status transitions | Tool approve/deny inside sessions | Paperclip is **stronger** on breadth of governance; Longtable's passkey confirmation of commitment actions is **unique** |
  | Prompt-injection controls | None documented | Opt-in `low_trust_review` containment | None ("Nothing committed yet") | Longtable's accept-before-your-agent-sees gate is **unique** in kind; Paperclip is the only one with any containment |
  | Sign-in | Email code + Google | Better Auth sessions; SSO claimed only in README | Email/password, API keys | **Stronger**, if passkeys ship |
  | Notifications for people | In-app inbox + desktop banners; chat bots are agent front-ends | In-app inbox; experimental agent chat connectors | In-app pulse, favicon, chimes | **Stronger** for China+US: email and WeChat |
  | Chinese chat apps and China fit | Feishu (new connections mainland only), DingTalk, WeCom; Hong Kong company; Chinese docs | None | None | Multica is **stronger** on Feishu, DingTalk and WeCom; Longtable has WeChat and a Hong Kong server |
  | Breadth | 26 CLIs, squads, autopilots, Gantt, mobile and desktop apps | Org charts, budgets, plugins, skills studio, sandboxes | Worktrees, dev environments, live cursors, shared terminals | Longtable is clearly **weaker** |
  | GitHub, Linear, Jira | GitHub, GitLab, Gitea, Forgejo PR linking; no Linear or Jira | Managed GitHub (needs Paperclip Cloud); Linear and Jira only on the roadmap | GitHub `@agor`; Linear only as an MCP server | Longtable is **weaker** unless it adds PR linking |
  | License for a hosted competitor | Hosting for others barred without a commercial license | MIT, unrestricted | BUSL forbids an "Agor Offering" until 2029-01-15 | n/a. Only Paperclip's code could legally be reused in a hosted service |
  | Traction (2026-10-03) | 51.9k stars, +3.2k per month | 96.4k stars, +16.5k per month | Unknown (likely under 45k) | Longtable is clearly **weaker** |

- **Biggest competitive risk.** Multica adding a hook-based "attach" mode, or limiting its CLI skill to restricted agent tokens. It already has the board, the China channels and the user base. Paperclip's governance machinery (signed Ask-first, low-trust containment) is the most advanced design to learn from or differentiate against.

### Gaps
- **No user reports.** No first-hand reports from small teams using any of the three were found (GitHub Discussions and Discord were inaccessible).
- **Untested claims.** None of the cross-product verdicts were checked by running the software. Behaviour claims come from READMEs, docs and specs.
- **China reachability untested.** Reachability from mainland China of multica.ai, Paperclip Cloud, the Agor Cloud beta, GHCR and the npm-based installers was not tested.
