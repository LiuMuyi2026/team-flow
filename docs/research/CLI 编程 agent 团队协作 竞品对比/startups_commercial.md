# Startups & commercial products for managing / observing / coordinating multiple AI coding agents across a team (state as of 2026-10-03)

Method note: researched 2026-10-03. Most vendor sites (conductor.build, superset.sh, aq.dev, superconductor.com, charlielabs.ai, humanlayer docs, zed.dev, ycombinator.com, news.ycombinator.com, techcrunch.com, hn.algolia.com) were blocked by the egress proxy, so facts from them come from search-result snippets and carry lower confidence. Where possible I used primary sources on raw.githubusercontent.com (open-source READMEs, SECURITY docs, Warp's public docs repo). Another useful source was a competitor's dated analysis repo (Yep Anywhere's `docs/competitive/*`, snapshots 2026-02 to 2026-10-02). It is labelled as competitor-authored wherever I cite it. Big platforms (GitHub/Linear/Atlassian/Slack/Anthropic/OpenAI/Cursor/Google/Microsoft) are excluded except where needed for context, such as an acquisition.

## Q1. Which products exist in this space (what each does, target, agents, integration, team features, approval/security, deployment, pricing, traction, dates, weaknesses)?

### Takeaway
The space split into five groups by Oct 2026:
- **Local parallel-agent workbenches**, mostly solo-first: Conductor, Superset, Emdash, Sculptor, Nimbalyst, T3 Code, bb, Munder Difflin.
- **Remote/mobile supervisors**: Happy, Warp Remote Control, and Omnara before its pivot.
- **Cloud "background agent" services triggered from Slack/Linear/GitHub**: Devin, Factory, Tembo, Cyrus, Capy, Ona, Runtime, plus Charlie, Codegen and Terragon, which are now dead or absorbed.
- **A new 2026 "multiplayer AI" wave** where several humans share agent sessions, memory or boards: HumanLayer, Superconductor, AQ, Mosaic, Zed's Delta, Coshell, mpai, Glen and YC's open-source QM.
- **Warp's Oz/Factories platform**, which spans the groups above.

Very few products combine a cross-person task board with blockers/help requests and human-only commitment gates.

### Cited Findings

#### A. "Multiplayer" / team-first coordination products (closest to Longtable)

- **HumanLayer (YC F24, San Francisco)**
  - **Positioning:** now "The multiplayer control plane for your software factory" — [humanlayer.dev](https://www.humanlayer.dev/); YC F24 — [Work at a Startup](https://www.workatastartup.com/companies/humanlayer).
  - **Evolution:** started as a human-in-the-loop approval API for agents — [Launch YC](https://www.ycombinator.com/launches/M8e-humanlayer-human-in-the-loop-for-ai-agents-and-beyond). Then shipped CodeLayer, an open-source desktop IDE (Tauri + Go daemon) for running parallel Claude Code sessions with approval workflows — [HeyClaude](https://heyclau.de/entry/tools/humanlayer), [DeepWiki](https://deepwiki.com/humanlayer/humanlayer).
  - **Open-source status:** the old public repo now says "the code here is pretty much all deprecated - you can try the rebuild of humanlayer at https://humanlayer.com" — [GitHub humanlayer/humanlayer](https://github.com/humanlayer/humanlayer). The current product FAQ says it is not yet open source — [Yep Anywhere multiplayer review, 2026-09-30 (competitor-authored)](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/multiplayer-ai.md).
  - **What it does (as of Jul–Sep 2026):** a "multiplayer coding agent IDE and cloud" that combines shared tasks, agent sessions, plan artifacts, design reviews, code diffs, worktrees and remote workers across Claude Code, Codex and other harnesses — [vibecodinghub](https://vibecodinghub.org/tools/humanlayer). Supports parallel Claude Code sessions with your own keys, multi-repo worktrees, local and cloud daemons, and AWS Bedrock (July 2026) — search snippet via [HumanLayer release notes](https://docs.humanlayer.com/release-notes).
  - **Team features:**
    - Temporarily share a running session, attributed messages, "prompt together".
    - Shared response drafts with named cursors and presence.
    - Read-only viewing.
    - Multiplayer prompting released 2026-08-17; shared drafts 2026-09-12. Initial release required admin enablement.
    - The documented live-session grant bundles prompting, interrupting **and resolving approvals**.
    - Source: [Yep Anywhere multiplayer review](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/multiplayer-ai.md), citing [release notes](https://docs.humanlayer.com/release-notes).
  - **Pricing (search snippet, 2026):** Starter free (up to 3 team members, up to 200 sessions/month); Pro $100/user/month (BYOK for Claude Code and other models, unlimited tasks/sessions, multi-repo workspaces, remote daemons); Enterprise custom. Bring your own Claude/Codex subscriptions or keys, with no HumanLayer per-token bill — [devtune pricing](https://devtune.ai/verticals/coding-agent-orchestration/humanlayer/pricing), [vibecodinghub](https://vibecodinghub.org/tools/humanlayer).
  - **Funding:** only a ~$500K seed (2024) appears in aggregators (low confidence) — [Tracxn](https://tracxn.com/d/companies/humanlayer/__XZbhI_kKRufCd1LnFm62x7HgBSEk6EtN315vIthngyQ), [Latka](https://getlatka.com/companies/humanlayer.dev).
  - **Critique:** one critical review is titled "HumanLayer: The Context Engineering Framework That's Mostly Vapor" (it covers the old OSS repo) — [starlog](https://starlog.is/articles/ai-agents/humanlayer-humanlayer/).

- **Superconductor (Volition, Inc.; led by the Gradescope founders)**
  - **What it does:** "The multiplayer AI workspace for teams and coding agents" — [superconductor.com](https://www.superconductor.com/). CEO Arjun Singh co-founded Gradescope (acquired by Turnitin) — [Reach Capital](https://www.reachcapital.com/team/arjun-singh/). Sergey Karayev is a Volition co-founder — [Volition team](https://www.volition.co/team/).
  - **How it works:** runs many Claude Code, Codex and other agents in the company's **cloud sandboxes**. Teammates join shared agent sessions to observe or take control. It adds guided code review, live previews with automated QA checks, and GitHub and Slack integrations — [ai.engineer org page](https://ai.engineer/orgs/superconductor), [docs](https://www.superconductor.com/docs/).
  - **Supported agents:** Claude Code, Codex, OpenCode, Pi, Factory Droid, Grok Build, Amp, Cursor — [search snippet, superconductor.com](https://www.superconductor.com/).
  - **History:** early-access pitch in June 2025: "Manage an entire team of Claude Code agents… Write informal tickets • Spin up MANY agents for each ticket • Each agent has its own live app preview • One-click PR the best one" — [Sergey Karayev on X](https://x.com/sergeykarayev/status/1937903477050749126).
  - **Pricing (as of July 2026):** flat per-workspace tiers rather than per seat. Free for up to 4 members with capped compute; Pro $128/month flat for up to 32 members plus metered "sandbox hours" — [AQ vs Superconductor (competitor page, search snippet)](https://aq.dev/compare/aq-vs-superconductor/).
  - **Name collision:** an unrelated open-source "superconductor" desktop IDE also exists — [oscardobsonbrown/superconductor](https://github.com/oscardobsonbrown/superconductor).

- **AQ (aq.dev / agentqueue.dev), "the multiplayer coding harness"**
  - **What it does:** runs Claude Code, Codex, Cursor Agent, Kimi, Grok or plain shells as the real CLIs, in persistent tmux sessions on a VM you control, streamed live to the browser. Any teammate opens the same workspace and gets the same live terminal, editor and app preview, and "anyone can type". Sessions survive laptop close — [aq.dev](https://aq.dev/), [AgentQueue](https://www.agentqueue.dev/), [AQ guide: manage Claude Code sessions across a team](https://aq.dev/guides/manage-claude-code-sessions-across-a-team/).
  - **Pricing:** free on your own VM, or $100 per user per month for an AQ-run dedicated always-on team VM — [aq.dev (search snippet)](https://aq.dev/).
  - **Market signal:** an AQ builder publicly called YC's QM launch "validating" — [FounderBuilt](https://www.founderbuilt.ai/news/yc-qm-multiplayer-agent-harness).
  - **Unknowns:** founders, funding and launch date not found.

- **Mosaic (YC Summer 2026; founders Shubham Patil and Dorsa Rohani)**
  - **What it does:** "syncs every AI session your team runs — Claude Code, Codex, Cursor and more — into one shared place that any agent can use." It keeps a record of what was tried, what changed and why, so a teammate or agent can "pick up exactly where someone else left off" — [Launch YC: Mosaic](https://www.ycombinator.com/launches/T3K-mosaic-shared-memory-for-your-team-s-agents), [YC profile](https://www.ycombinator.com/companies/mosaic-inc).
  - **Traction:** ~2,000 installs and 37 orgs actively syncing (company claim at launch) — [Launch YC (search snippet)](https://www.ycombinator.com/launches/T3K-mosaic-shared-memory-for-your-team-s-agents).
  - **Product history:** began as a live shared environment for people and agents (live shared terminals, pair programming with agents), then focused on centralized sessions and shared agent memory — [Yep Anywhere multiplayer review](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/multiplayer-ai.md), [wavect review (title/snippet)](https://wavect.io/blog/mosaic-yc-s26-shared-agent-sessions-review/).

- **Delta, from Zed Industries**
  - **Timeline:** DeltaDB (an operation-level history store linking every edit to the agent conversation that produced it) was announced June 2026, Delta was announced 2026-08-12, and Delta entered **public beta on 2026-09-16** on desktop and web — [Yep Anywhere DeltaDB review (competitor-authored)](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/deltadb.md), [Zed blog: Delta public beta](https://zed.dev/blog/delta-public-beta).
  - **Team features:** invite teammates into the same agent thread; comment on conversation and code; ask the original agent questions; continue work after another participant leaves — [Yep Anywhere multiplayer review](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/multiplayer-ai.md).
  - **Unknowns:** as of 2026-09-15, no published pricing, self-host/open-source component, or list of supported providers — [DeltaDB review](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/deltadb.md).
  - **Zed's broader agent strategy:** Zed created the Agent Client Protocol (ACP) in Aug 2025. ACP runs Claude Code (via a Zed-built adapter), Codex and Gemini CLI inside the editor. Zed and JetBrains co-launched an ACP Registry in Jan 2026 — [Zed blog: Claude Code via ACP](https://zed.dev/blog/claude-code-via-acp), [danilchenko.dev](https://www.danilchenko.dev/posts/agent-client-protocol/).

- **Coshell**
  - **What it does:** several people prompt the same agent, with named, visible queued prompts, a separate session chat, presence/following and shared browser previews. Web and terminal clients reach a shared machine called a "drive" (it can be the team's own machine). Session visibility is private, selected teammates, or whole drive.
  - **Caveat:** built on open-source OpenCode, but no published source for the multiplayer layer was verified. Its chat assistant can relay prompts to the working agent.
  - Source: [Yep Anywhere multiplayer review](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/multiplayer-ai.md), [coshell docs](https://coshell.ai/docs).

- **mpai / multiplayer-ai (open source, MIT, public alpha)**
  - **What it does:** "Your teammate's AI session. On your terminal. Make existing Codex and Claude Code work multiplayer without moving the team into a new IDE." The host keeps using the native agent. A teammate sees the same persisted context and "can add a turn with their own name attached" (two-Mac demo dated 2026-08-02, v0.4.19). Requires macOS and Tailscale on both machines. Only explicitly shared sessions are exposed — [GitHub godfaddaai/multiplayer-ai](https://github.com/godfaddaai/multiplayer-ai).
  - **Permission model:** invites bind to the first Tailscale identity that uses them. Viewer and participant roles, revocation and an audit trail. **No remote approval endpoint**: Codex remote approvals are declined, and Claude remote turns deny operations needing interactive permission — [Yep Anywhere multiplayer review](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/multiplayer-ai.md), citing [mpai SECURITY](https://github.com/godfaddaai/multiplayer-ai/blob/main/SECURITY.md).

- **Glen (YC Summer 2026)** — markets organizational context, unified agent transcripts, **cross-harness handoff**, and multiplayer agents in early access. The profile does not show invitations or scoped prompting into one existing session — [Yep Anywhere multiplayer review](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/multiplayer-ai.md), [YC profile](https://www.ycombinator.com/companies/glen).

- **QM (open-sourced by Y Combinator on 2026-07-31; MIT)**
  - **What it is:** "A multiplayer agent harness for work. In Slack and on the web. Run it in your own cloud, with your own models and keys." Each person and each room gets its own scoped memory, files, keychain view, permissions, crons and durable sandbox. Pi, OpenCode, Codex and Claude Code all "drive the same core" — [GitHub yc-software/qm README](https://github.com/yc-software/qm).
  - **Security posture** (org-level; narrower scopes can only tighten it):
    - **Strict:** every tool call pauses for human approval.
    - **Auto** (default): blocks private-network access.
    - **Dangerous:** no approval gates.
    - **Content screening** (`off`/`observe`/`enforce`): `enforce` "quarantines flagged content pending release approval".
    - Source: [QM README](https://github.com/yc-software/qm).
  - **Reception:** 5,000+ GitHub stars in its first day and #2 on Hacker News with 500+ points — [Startup Fortune](https://startupfortune.com/y-combinator-open-sources-qm-the-ai-agent-harness-it-uses-to-run-itself/), [agentsai.fyi](https://agentsai.fyi/news/y-combinator-open-sources-qm-multi-agent-harness-2026-07-31).
  - **Limits:** general-purpose (accounting, legal, engineering), not a coding-team board. Its session-share links are read-only snapshots — [Yep Anywhere multiplayer review](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/multiplayer-ai.md).

- **Warp (Warp 2.x terminal → Oz platform → Factories)**
  - **Open-source client:** announced 2026-04-28, with OpenAI as founding sponsor. Company claims "nearly a million active developers" (Apr 2026) and "more than 800k active developers" in a 2026-09-27 talk. The repo had 65,341 stars on 2026-10-02 — [Yep Anywhere Warp review (competitor-authored, 2026-10-02)](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/warp.md), [Warp blog](https://www.warp.dev/blog/warp-is-now-open-source), [talk](https://www.youtube.com/watch?v=tUPPVhBBcoM&t=71s).
  - **Local CLI agents:** supports 15 named local CLI agents (Claude Code, Codex, OpenCode, Amp, Droid, Gemini CLI and more). Status comes from a Claude Code plugin emitting hook notifications (prompt submitted, permission request, stop, failure) mapped to running/blocked/success states — [Warp review](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/warp.md).
  - **Remote Control:** publishes a running Claude Code/Codex session to the cloud with one click. Teammates can "observe or collaborate", and "you control who can view and who can steer" — [Warp docs: Remote Control](https://github.com/warpdotdev/docs/blob/dbaf7ae2d45f714ce0585085b5708c19bfb6906a/src/content/docs/agents/cli-agents/remote-control.mdx).
  - **Oz cloud harnesses:** run Claude Code or Codex as cloud agents (Build plan or higher). "Claude Code and Codex each call their provider directly using credentials you supply"; Warp meters compute and platform credits — [Warp docs: harnesses](https://github.com/warpdotdev/docs/blob/dbaf7ae2d45f714ce0585085b5708c19bfb6906a/src/content/docs/platform/harnesses/index.mdx).
  - **Warp Factories** (Early Access, limited teams):
    - A "foreman" agent takes work from Slack, GitHub, GitLab, Linear, Jira, webhooks or a **Factory MCP** for local coding agents.
    - It dispatches Triage, Spec, Implement and Review agents.
    - It pauses for humans at three default points: **approving the spec**, **answering questions**, and **merging** (the first two are only prompt policy; merge gating relies on branch protection).
    - Source: [Warp docs: How Factories work](https://github.com/warpdotdev/docs/blob/dbaf7ae2d45f714ce0585085b5708c19bfb6906a/src/content/docs/factories/how-factories-work.mdx).
  - **Factory Inbox:** lists "Asked question / Spec review / PR review / Blocked / Failed" items. It is explicitly "a personal queue, not a team-wide feed: a teammate's task, even a blocked or failed one, never appears in your inbox" — [Warp docs: Factory inbox](https://github.com/warpdotdev/docs/blob/dbaf7ae2d45f714ce0585085b5708c19bfb6906a/src/content/docs/factories/factory-inbox.mdx).
  - **Pricing (2026-10-02):** Free $0, Build from $20/mo, Max $200/mo, Business $50/user/mo, Enterprise custom — [Warp review citing warp.dev/pricing](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/warp.md).
  - **Self-hosting:** `oz-agent-worker` runs tasks on customer infrastructure (Docker/K8s/Direct). Coordination, identity, transcripts and artifacts stay in Warp's control plane — [Warp review](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/warp.md).

- **Runtime (labelled "YC P26" in its Launch HN title)**
  - **What it does:** sandboxed coding agents for **everyone on a team, including non-engineers**, to ship with Claude Code, Codex and other agents "without engineering having to handhold every session". Engineering defines context once (system instructions, skills, scoped integrations). Runtime snapshots full environments (multi-service Docker Compose, Kafka, Redis, seeded DBs). Each session gets a shareable preview URL.
  - **Security:** secrets are injected through a managed proxy "so they never touch the agent directly". Guardrails run at the infrastructure level: command allow/deny lists, network egress controls, and RBAC scoped per human and per agent.
  - Source: [Launch HN: Runtime (search snippet)](https://news.ycombinator.com/item?id=48225040).

- **Conductor Teams/multiplayer.** Conductor (detailed under B) now sells "Conductor Cloud, multiplayer, and the API" on paid tiers:
  - Pro $50/month includes "live collaboration with up to 5 Pro users".
  - Teams $60/user/month adds live collaboration for any team size, an admin portal and centralized billing.
  - Company-wide multiplayer is reported as invite-only.
  - Source: [Conductor pricing (search snippet)](https://www.conductor.build/pricing), [vibecoding.app review](https://vibecoding.app/blog/conductor-review).

- **Nimbalyst Teams (formerly Crystal)**
  - "Nimbalyst Teams is multiplayer. Your whole team, Codex, and Claude Code in one shared workspace." Teams can edit the same docs, mockups and diagrams in real time and "plan the work on shared trackers agents update too" — [Nimbalyst team collaboration](https://nimbalyst.com/use-cases/team-collaboration/), [Nimbalyst for teams](https://nimbalyst.com/claude-code-for-teams/).
  - The repo (MIT) ships a session kanban, task trackers agents read and update, and an iOS companion ("see which agents need you… get a push when an agent is waiting"). The collaboration sync server (`wss://sync.nimbalyst.com`) is a separate, closed project — [GitHub Nimbalyst/nimbalyst](https://github.com/Nimbalyst/nimbalyst).

- **Vibe Kanban Cloud (Bloop) — dead.**
  - **Before shutdown:** let teams "plan work, either privately or with your team" and "create, prioritise, and assign issues on a kanban board" across 10+ agents (Claude Code, Codex, Gemini CLI, Copilot, Amp, Cursor, OpenCode, Droid…) — [GitHub BloopAI/vibe-kanban](https://github.com/BloopAI/vibe-kanban).
  - **Shutdown:** Bloop announced it on **2026-04-10**. Cloud features (shared kanban issues, comments, projects, organisations) were switched off 30 days later; the tool continues as a local-only community OSS project — [Goodbye bloop](https://www.vibekanban.com/blog/shutdown), [vibecoding.app review](https://vibecoding.app/blog/vibe-kanban-review).

- **Superset team features** (product detailed under B):
  - **Pages:** "Ask an agent to publish a Page. Teammates pin comments, and a watching agent can revise it at the same link."
  - Organization "hosts and members" for remote access.
  - Slack & Linear: "spin up workspaces from Slack messages or Linear issues".
  - Source: [GitHub superset-sh/superset README](https://github.com/superset-sh/superset).

#### B. Local parallel-agent workbenches (mostly one human running many agents)

- **Conductor (Melty Labs, YC S24)**
  - **What it does:** native Mac app that runs several Claude Code, Codex, Cursor or OpenCode agents, each in an isolated git worktree. Agents run "on a subscription you already hold" — [continuumcode guide](https://continuumcode.ai/guides/what-is-conductor/), [Yep Anywhere Conductor notes (2026-02-03)](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/conductor.md).
  - **Funding:** $22M Series A announced 2026-03-30, led by Ilya Sukhar (Matrix, also led the seed) and Nabeel Hyatt (Spark), with YC and the founders of Notion and Linear. Total disclosed ≈ $24.5M — [Charlie Holtz on X](https://x.com/charlieholtz/status/2039027121901957349), [Conductor blog](https://www.conductor.build/blog/series-a), [Dealroom](https://app.dealroom.co/news/feed/conductor-raises-22m-series-a-from-spark-and-matrix-for-ai-coding-platform), [continuumcode](https://continuumcode.ai/guides/what-is-conductor/).
  - **Traction:** "tenfold user growth since January" 2026; claims use by engineers at Google, Meta, Amazon, Spotify, HubSpot and Ramp — [Dealroom/Conductor blog (search snippet)](https://www.conductor.build/blog/series-a).
  - **Weakness:** Mac-only as of Sept 2026 (Windows on a waitlist, no Linux announced) — [vibecoding.app review](https://vibecoding.app/blog/conductor-review).

- **Superset (founders Kiet Ho, Avi Peltz, Satya Patel)**
  - **What it does:** desktop "IDE for the AI agents era". Runs Claude Code, Codex, Gemini CLI, Copilot, OpenCode, Pi and others in parallel git-worktree workspaces, with diff review, browser previews, scheduled automations, remote access, an iPhone app, a CLI, an SDK and an **MCP server** "to let Claude Code, Codex, Cursor, and other agents create and manage workspaces themselves". "Keep your existing agent subscriptions."
  - **License:** Elastic License 2.0 (source-available). "The desktop app is free forever… Anything we charge for will be an optional service on top." Mobile requires **Superset Pro**. Linux is experimental.
  - Source: [GitHub superset-sh/superset](https://github.com/superset-sh/superset).
  - **Funding and traction:** raised **$11M** "to build the platform for software factories" — [superset.sh/team](https://superset.sh/team). Claims 11K stars and "thousands of daily active users" — [founderland](https://www.founderland.ai/articles/superset-launches-ide-to-orchestrate-100-ai-coding-agents-in-mpz8db7u). #1 Product of the Day on Product Hunt, 2026-02-27 — [rywalker research](https://rywalker.com/research/superset). Founder began building it ~2025-12-20 — [Kiet on X](https://x.com/FlyaKiet/status/2002528729042727105). YC promoted the launch on 2026-04-07 — [YC on X](https://x.com/ycombinator/status/2041584855650312656).
  - **YC batch conflict:** described as "YC Spring 2026" — [rywalker](https://rywalker.com/research/superset); labelled "YC P25" — [bestofshowhn](https://bestofshowhn.com/yc-p25/superset); filed under "s26" — [yctierlist](https://yctierlist.com/s26/superset/).

- **Emdash (General Action, Inc., YC W26)**
  - **What it does:** free, Apache-2.0 desktop "Agentic Development Environment" for macOS, Windows and Linux. Each task runs in its own git worktree. Works with 25+ CLI agents, including Claude Code, Codex, Cursor, OpenCode, Amp, Devin, Droid and Copilot. Pulls tickets from Linear, GitHub, Jira, GitLab, Asana and others. Supports remote machines over SSH — [GitHub generalaction/emdash](https://github.com/generalaction/emdash).
  - **Integration:** "For agents with lifecycle-hook support, Emdash installs marker-tagged entries in the agent's user-level config. These hooks let Emdash track status, notifications, and resumable sessions" — [Emdash README](https://github.com/generalaction/emdash).
  - **Traction:** ~5.9k stars and 622 forks as of 2026-10-02; the site claims >1M downloads — [api-evangelist profile](https://github.com/api-evangelist/emdash).
  - **Critique:** a competitor's source review (2026-02-25) says it does not parse agent output ("essentially a multi-tab terminal with a task board bolted on") — [Yep Anywhere emdash review](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/emdash.md).

- **Sculptor (Imbue)**
  - **What it does:** desktop app for running coding agents in parallel, described as an "experimental research preview". Integrated Claude Code and Pi harnesses, plus "any terminal-based agents". The repo is now public but not yet accepting broad contributions — [GitHub imbue-ai/sculptor](https://github.com/imbue-ai/sculptor).
  - **Isolation conflict:** earlier descriptions say each agent runs in an isolated Docker container — [rywalker (June 2026)](https://rywalker.com/research/sculptor), [agi-cli landscape (2026-08-20)](https://github.com/phnx-labs/agi-cli/blob/main/.agents/artifacts/2026-08-20/landscape-cli-proxy-browser-computer.md). The current README describes workspaces as "isolated worktrees of your repo" — [README](https://github.com/imbue-ai/sculptor).
  - **Pricing:** free during beta, using your own Claude Code subscription or Anthropic API key — [rywalker](https://rywalker.com/research/sculptor). Launch post: [Imbue blog](https://imbue.com/blog/sculptor-announce).

- **Crystal → Nimbalyst (Stravu; founder Karl Wirth)**
  - Crystal (parallel Claude Code/Codex sessions in worktrees) was **deprecated in February 2026** and replaced by Nimbalyst — [GitHub stravu/crystal](https://github.com/stravu/crystal).
  - Nimbalyst: MIT-licensed desktop app (macOS/Windows/Linux) plus iOS, a "visual workspace" with WYSIWYG markdown, diagrams, mockups, a session kanban and task trackers. Supports Codex and Claude Code, with OpenCode and Copilot in alpha — [GitHub Nimbalyst/nimbalyst](https://github.com/Nimbalyst/nimbalyst).

- **T3 Code (T3 Tools Inc., Theo)**
  - An "agent harness control surface" with iOS/Android/web/Electron apps. "Works with your subscriptions on Claude Code, Codex, Cursor, Grok Build, OpenCode, and Google Antigravity." MIT. "Wait, what are you selling me? Nothing." — [GitHub pingdotgg/t3code](https://github.com/pingdotgg/t3code).
  - ~21.7k stars per a competitor table — [Yep Anywhere all-projects](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/all-projects.md).

- **bb (get-bb)** — MIT "agentic IDE that builds itself". Threads can be followed live, steered, "or hand[ed] off to another agent". Supports Claude, Codex, Pi and ACP agents — [GitHub get-bb/bb](https://github.com/get-bb/bb), [all-projects](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/all-projects.md).

- **Munder Difflin (independent; Chaitanya Giri)**
  - Free, MIT Electron app that wraps Claude Code, Codex, Gemini CLI and others and coordinates them "as a team". Each agent gets long-term memory, a mailbox and a desk in a pixel-art office. A "GOD agent adjudicates, assigns, and escalates only when it needs you", and changes flow into "an approvals queue you act on". Uses your existing subscriptions — [GitHub chaitanyagiri/munder-difflin](https://github.com/chaitanyagiri/munder-difflin), [Why we built it](https://munderdiffl.in/blog/why-we-built-munder-difflin/).
  - Paid Pro license "as low as $100 a year" — [README](https://github.com/chaitanyagiri/munder-difflin).
  - Star counts reported as 2,500+ — [coddykit](https://www.coddykit.com/pages/blog-detail?id=513014&slug=munder-difflin-the-open-source-multi-agent-harness-with-2-500-github-stars-that-) — and 8.2k — [skillsllm](https://skillsllm.com/skill/munder-difflin). The sources conflict; the project is growing fast.

- **Long tail of small local/OSS orchestrators and remotes**, listed for completeness with no deep verification:
  - Claude Squad, Conductor-alternatives such as CodeAgentSwarm, AgentsRoom, amux, Pane (Windows/Linux), Parallel Code, Codeman, vibefactory — [CodeAgentSwarm list](https://www.codeagentswarm.com/en/guides/best-tools-to-run-multiple-ai-coding-agents), [AgentsRoom](https://agentsroom.dev/claude-code-for-teams), [amux](https://amux.io/blog/best-multi-agent-orchestrators-2026/), [Pane](https://runpane.com/compare/vibe-kanban), [Parallel Code](https://parallelcode.app/compare/parallel-code-vs-vibe-kanban/), [Codeman](https://getcodeman.com/compare/codeman-vs-vibe-kanban), [vibefactory](https://www.vibefactory.dev/alternatives/vibe-kanban).
  - Remote supervisors: AionUi, Paseo, Yep Anywhere, CosmoRemote, Vicoa (free 50 msgs/mo; Pro $9.99/mo), kibbler.dev ($3.99/mo), and extendo-cli (human-in-the-loop decision cards via mobile push) — [Yep Anywhere all-projects](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/all-projects.md).

#### C. Remote/mobile supervision

- **Happy (happy.engineering; slopus)**
  - Free, MIT mobile/web/desktop client for Claude Code and Codex: `happy claude` / `happy codex`. Push notifications when permissions are needed. **End-to-end encryption**: the relay never receives the key, so it "can't decrypt your prompts, responses, code, or session context" — [GitHub slopus/happy](https://github.com/slopus/happy), [happy.engineering](https://happy.engineering/).
  - Show HN "Happy Coder" in 2025 — [HN](https://news.ycombinator.com/item?id=44904039). ~12.9k stars — [all-projects](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/all-projects.md). A multi-agent fork, "happier", exists — [happier-dev/happier](https://github.com/happier-dev/happier).

- **Omnara (YC S25) — pivoted.**
  - **Original product:** "Talk to Your AI Agents from Anywhere" / "mission control for your AI agents". Run `omnara` to sync a Claude Code session across terminal, web and mobile; agents ask questions and you approve or steer from your phone — [flumente/omnara](https://github.com/flumente/omnara), [Product Hunt](https://www.producthunt.com/products/omnara), [App Store](https://apps.apple.com/us/app/omnara-claude-codex-mobile/id6748426727).
  - **Launch HN pricing (Feb 2026):** free for 10 agent sessions/month, then $20/month — [Launch HN (search snippet)](https://news.ycombinator.com/item?id=46991591).
  - **Now:** the `omnara-ai/omnara` README describes "The API for production-grade agents": an Apache-2.0 managed-agents platform with sandboxes (Daytona, Modal, etc.), BYO models, RBAC and a Slack connector — [GitHub omnara-ai/omnara](https://github.com/omnara-ai/omnara).
  - **Conflicting account:** a competitor table says the OSS repo was archived Feb 2026 and pivoted to a proprietary voice-first platform — [all-projects](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/all-projects.md). A founder tweet on 2025-11-09 (date decoded from the post ID) announced a "voice-first coding agent" that "coordinates multiple agents" — [Ishaan Sehgal on X](https://x.com/IshSup/status/1987649869641908394).

#### D. Cloud background agents triggered from Slack/Linear/GitHub ("Jules-like")

- **Devin (Cognition) / Windsurf**
  - **Team plan:** lets "your entire team create, share and collaborate together in Devin sessions" with unlimited seats and Slack integration — [pensero/vp0 pricing guides](https://vp0.com/blogs/devin-ai-pricing-plans-2026). Reported at $500/month with 250 ACUs at $2/ACU and unlimited concurrent sessions — [usagebar](https://usagebar.com/blog/devin-pricing-and-rate-limits).
  - **2026 integration notes:** the Slack app gets canvas permissions; sessions started by Linear automations can start and manage child sessions (orchestrator playbooks) — [Devin release notes 2026](https://docs.devin.ai/release-notes/2026).
  - **Windsurf:** Cognition agreed to acquire Windsurf in July 2025. Windsurf was rebranded "Devin Desktop" on 2026-06-02 and windsurf.com redirects to devin.ai — [getcreatr](https://getcreatr.com/windsurf-pricing-2026), [agi-cli landscape](https://github.com/phnx-labs/agi-cli/blob/main/.agents/artifacts/2026-08-20/landscape-cli-proxy-browser-computer.md).
  - **Funding:** $1B+ at a $25B pre-money valuation (2026-05-27) — [TechCrunch](https://techcrunch.com/2026/05/27/ai-coding-startup-cognition-raises-1b-at-25b-pre-money-valuation/); $48B valuation (2026-09-08) — [TechCrunch](https://techcrunch.com/2026/09/08/cognition-hits-48b-valuation-signaling-investors-believe-ai-coding-is-far-from-a-winner-take-all-market/).
  - **Revenue:** Devin run-rate reportedly $492M (May 2026) rising to ~$900M (Sept 2026) — [enterprisedna](https://enterprisedna.co/resources/news/cognition-devin-1-billion-25-billion-valuation-2026/), [ecmsource](https://ecmsource.com/cognition-48b-series-e-2b-devin-900m-arr-september-2026/).
  - **Limitation:** single-vendor; its own agent, not your Claude Code/Codex.

- **Factory (Droids)**
  - **What it is:** its own agent ("Droid"), model-agnostic, deployable in cloud, on-prem or air-gapped. Customers include Nvidia, Blackstone, RBC, Palo Alto Networks, Adobe and T-Mobile.
  - **Funding:** $150M Series C in April 2026 at $1.5B — [tech-insider](https://tech-insider.org/factory-ai-150-million-series-c-khosla-coding-droids-2026/); then $200M on 2026-09-15 at $5B, with total funding >$400M — [TFN](https://techfundingnews.com/factory-jumps-to-5b-in-5-months-with-200m-for-its-ai-droids/).
  - **Pricing:** Pro $20, Plus $100, Max $200 per month — [theaiagentindex](https://theaiagentindex.com/agents/factory-ai).
  - **Teams plan conflict:** a self-serve plan for ≤10 developers, reported as "$60 per team per month plus $40 per seat" in one snippet but headlined "$46 per seat" — [alphasignal](https://alphasignal.ai/news/factory-launches-droids-teams-plan-for-small-developer-groups-at-46-per-seat).
  - **Controls:** Autonomy levels Off/Low/Medium/High set "the highest-risk work Droid can run without pausing for approval" — [Factory docs: Autonomy Level](https://docs.factory.ai/cli/user-guides/auto-run). Subagents are clamped to the org-managed `maxAutonomyLevel` — [Factory docs: subagents](https://docs.factory.ai/harness/subagents). "Droid Shield" does secret scanning and git guardrails locally — [Factory docs: privacy & data flows](https://docs.factory.ai/enterprise/privacy-and-data-flows).

- **Tembo**
  - **What it is:** "Run any coding agent in the cloud" (Claude Code, Codex, OpenCode, Amp, Cursor). Tag @Tembo in Slack, Linear, GitHub, Jira or Sentry; a background agent runs the task and opens a PR. Supports multi-repo changes and scheduled jobs — [tembo.io](https://www.tembo.io/), [Tembo docs: agents](https://docs.tembo.io/features/agents), [Tembo blog](https://www.tembo.io/blog/best-ai-for-coding).
  - **Pricing:** Free ($10 one-time usage allowance), Pro $60/mo (usage allowance, up to 5 users), Max $200/mo (up to 10 users) — [Tembo blog (search snippet)](https://www.tembo.io/blog/best-ai-for-coding).

- **Cyrus (Ceedar)**
  - **What it is:** "Your (Claude Code|Codex|Cursor|Gemini|Opencode) powered (Linear|GitHub|GitLab|Slack) agent." It monitors issues **assigned to it**, creates a git worktree per issue, runs the agent, and "streams detailed agent activity updates back to (Linear|GitHub), along with rich interactions like dropdown selects and approvals". BYOK, meaning your own keys or subscriptions — [GitHub cyrusagents/cyrus](https://github.com/cyrusagents/cyrus). Listed in Linear's integrations — [Linear integration](https://linear.app/integrations/cyrus).
  - **Deployment:** free fully self-hosted community edition; paid "self-hosted" mode, where Cyrus provides networking and integrations while your machine runs the agent.
  - **Pricing:** Pro $50/mo; Team $120/mo (up to 20 Linear workspace members, 10 active repos) — [Cyrus pricing](https://www.atcyrus.com/pricing).

- **Capy (YC F24)** — "Orchestrate an army of coding agents from one dashboard and ship entire sprints in parallel". Web IDE with up to 25 concurrent agents, each in an isolated Ubuntu VM. A "Captain" plans, Build agents execute and a Review agent checks; model-agnostic. Team of ~6 — [YC](https://ycombinator.com/companies/capy), [everydev](https://www.everydev.ai/tools/capy), [altss](https://altss.com/companies/yc/capy). Built a kanban-style triage agent on Trigger.dev — [Trigger.dev story](https://trigger.dev/customers/capy-customer-story).

- **Ona (formerly Gitpod)** — rebranded 2025-09-02 in a pivot to an AI agent platform ("task in, pull request out") — [The Register](https://www.theregister.com/2025/09/03/gitpod_rebrands_as_ona/). Core plan from $20/mo, billed in Ona Compute Units (OCUs) for up to 100 team members; extra OCUs $10 per 40. Enterprise adds VPC runners, SSO and audit — [infragap](https://infragap.com/tools/ona/).

- **Amp (Amp Frontier Corp.)** — spun out of Sourcegraph as a separate, profitable company in Dec 2025. Threads are shareable by URL and run on remote "orbs". "Teams" is now a seat-free workspace wrapper (pooled billing, SSO, shared BYOK) — [rywalker](https://rywalker.com/research/amp-sourcegraph), [tomrochette](https://tomrochette.com/agents/amp/), [whichcodingtools PR](https://github.com/benjamincanac/whichcodingtools/pull/95). Its own agent, not a Claude Code/Codex wrapper.

- **Terragon Labs — shut down.**
  - **What it was:** cloud orchestrator for Claude Code, Codex, Amp and Gemini. Sandboxes, BYO Claude/ChatGPT subscriptions, auto branches/PRs, a `terry` CLI for local task takeover plus an MCP server, and @-mentions from Slack/GitHub — [GitHub terragon-oss](https://github.com/terragon-labs/terragon-oss).
  - **Shutdown:** OSS snapshot dated 2026-01-16; service shut down 2026-02-09 because it "wasn't able to reach the level of traction needed"; recommends Claude Code Web / Codex Web — [Terragon shutdown doc](https://docs.terragonlabs.com/docs/resources/shutdown).

- **Charlie Labs — shutting down.** TypeScript-focused agent working across GitHub, Linear and Slack, with "Daemons" (standing agents; V2 shipped Spring 2026) — [Charlie 2025 recap](https://charlielabs.ai/blog/charlie-2025-a-recap-and-whats-next/). Shutdown announced ~2026-08-25; service available until **2026-10-05** — [Charlie blog (search snippet)](https://charlielabs.ai/blog/), [withpurple](https://www.withpurple.com/post/charlie-is-shutting-down-here-are-the-best-alternatives-in-2025).

- **Codegen — acquired.** ClickUp acquired Codegen on 2025-12-23, terms undisclosed. Codegen had raised $16.2M (2023) at a $60M last valuation. Founder Jay Hack became ClickUp head of AI. The standalone service was discontinued 2026-01-09 — [ClickUp blog](https://clickup.com/blog/clickup-codegen-acquisition/), [Codegen update](https://codegen.com/an-update-on-codegen/), [reworked](https://www.reworked.co/digital-workplace/clickup-acquires-codegen-to-power-project-management-work-management-super-agents/).

#### E. Adjacent names from the prompt

- **Graphite — acquired.** Cursor announced the acquisition of Graphite (stacked PRs / AI code review) on 2025-12-19 for cash and equity, reportedly "way over" Graphite's ~$290M last valuation. Graphite had 500+ customer companies and continues as an independent product — [Cursor blog](https://cursor.com/blog/graphite), [Fortune](https://fortune.com/2025/12/19/cursor-ai-coding-startup-graphite-competition-heats-up/), [Axios](https://www.axios.com/pro/enterprise-software-deals/2025/12/19/cursor-buys-code-review-platform-graphite).
- **Sweep — pivoted.** Deprecated its GitHub issue-to-PR bot and became a JetBrains-first autocomplete plus inline agent; open-weighted a 1.5B next-edit model in Feb 2026 — [tooljunction](https://www.tooljunction.io/ai-tools/sweep), [JetBrains plugin](https://plugins.jetbrains.com/plugin/26860-sweep-ai/versions/stable/776352).
- **Tuple** — searches found no Tuple product for coordinating coding agents (see Gaps).

### Inferences
- **Two meanings of "team":** most funded products are either (a) one developer driving many agents (Conductor, Superset, Emdash, Sculptor) or (b) a cloud agent that a team triggers from Slack/Linear (Devin, Factory, Tembo, Cyrus). The products where several humans coordinate around agents are mostly 2026 entrants: HumanLayer multiplayer (Aug 2026), Delta beta (Sept 2026), Mosaic (S26), Glen (S26), AQ, Superconductor, mpai, Coshell, QM (Jul 2026), and Conductor's paid multiplayer tier.
- **Warp Factories is the richest "blocker/question" model found**, but its inbox is explicitly personal. A team-wide view of "who is stuck / who is needed" across people appears to be an open niche.
- **Emdash and Warp use the same mechanism as Longtable's hooks.** Both install Claude Code/Codex hooks or plugins to get status (running/blocked/stopped). Emdash and Superset also expose MCP or CLI so agents can create work items. Hook+MCP integration is common and not a differentiator by itself; what agents may and may not do through it could be.

### Gaps
- Could not open most vendor pages or any Hacker News/Reddit thread directly (egress blocked; the web-search budget ran out mid-research). Pricing and traction for Superconductor, AQ, Conductor tiers, Tembo, HumanLayer and Omnara rest on search snippets.
- No founders, funding or launch date found for **AQ**; no funding found for Superconductor, Mosaic, Glen, Coshell, Runtime or Capy; no pricing found for Mosaic, Capy, Runtime, Glen, Coshell, Delta, Nimbalyst Teams or Superset Pro.
- **Tuple:** no evidence of an agent-coordination feature (the search returned nothing Tuple-specific). Absence was not confirmed on tuple.app.
- Not covered for lack of budget: Coder (Tasks / "mux"), OpenHands Cloud, Kilo Code / Roo Code / Cline team tiers, Augment remote agents, Cosine, Dagger container-use, Daytona/E2B (sandbox infra), MobSession ("drive Claude Code together", [mobsession.ai](https://mobsession.ai/), title only), and a "Claude Squad — Multiplayer AI Coding" landing page.

## Q2. Which truly target multi-human teams (vs one person running many agents), and which support both Claude Code and Codex (incl. the user's own subscriptions)?

### Takeaway
- **Built for several humans:** HumanLayer, Superconductor, AQ, Mosaic, Delta (Zed), Coshell, mpai, Glen, QM, Runtime, Warp (Remote Control sharing + Factories), plus paid tiers of Conductor, Nimbalyst and Superset. Vibe Kanban Cloud was also team-oriented but is gone.
- **Cross-vendor (Claude Code and Codex) and usually bring-your-own-subscription:** Conductor, Superset, Emdash, T3 Code, Nimbalyst, Happy, AQ, Superconductor, HumanLayer, Mosaic, QM, mpai, Cyrus, Tembo, Warp. Sculptor integrates Claude Code and Pi rather than Codex.
- **Single-vendor (their own agent):** Devin, Factory, Capy, Amp, Ona, Charlie and Codegen.

### Cited Findings

| Product | Built for multi-human teams? | Claude Code + Codex? | Own subscription? | Deployment | Status (2026-10-03) |
|---|---|---|---|---|---|
| HumanLayer | Yes: shared sessions, multiplayer prompting, shared drafts ([Yep review](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/multiplayer-ai.md)) | Yes ([vibecodinghub](https://vibecodinghub.org/tools/humanlayer)) | Yes, BYO subscription/keys ([devtune](https://devtune.ai/verticals/coding-agent-orchestration/humanlayer/pricing)) | Desktop IDE + cloud + local/remote daemons | Active |
| Superconductor | Yes: join or take control of teammates' sessions ([ai.engineer](https://ai.engineer/orgs/superconductor)) | Yes + 6 others ([superconductor.com](https://www.superconductor.com/)) | Not established | Vendor cloud sandboxes | Active |
| AQ | Yes: shared live terminals, "anyone can type" ([aq.dev](https://aq.dev/)) | Yes ([aq.dev](https://aq.dev/)) | Runs real CLIs on your VM ([aq.dev](https://aq.dev/)) | Your VM or AQ-hosted VM | Active |
| Mosaic (YC S26) | Yes: shared session memory and handoff ([Launch YC](https://www.ycombinator.com/launches/T3K-mosaic-shared-memory-for-your-team-s-agents)) | Yes + Cursor | N/A (syncs sessions) | SaaS (assumed) | Active |
| Delta (Zed) | Yes: invite teammates into agent thread ([Yep review](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/multiplayer-ai.md)) | Not published | Unknown | Desktop + web; public beta 2026-09-16 | Beta |
| mpai | Yes: join a teammate's existing session ([GitHub](https://github.com/godfaddaai/multiplayer-ai)) | Yes | Yes (native CLIs) | Local macOS + Tailscale; MIT alpha | Alpha |
| QM (YC OSS) | Yes: personal + shared rooms in Slack/web ([GitHub](https://github.com/yc-software/qm)) | Yes (+ Pi, OpenCode) | Own keys/models | Self-host in your cloud | Active (OSS) |
| Runtime (YC P26) | Yes: whole team incl. non-engineers ([Launch HN](https://news.ycombinator.com/item?id=48225040)) | Yes | Unknown | Vendor sandboxes | Active |
| Warp | Partly: session sharing with view/steer rights; Factories for teams; inbox is personal ([docs](https://github.com/warpdotdev/docs/blob/dbaf7ae2d45f714ce0585085b5708c19bfb6906a/src/content/docs/factories/factory-inbox.mdx)) | Yes (local + cloud harnesses) | Yes ("credentials you supply") ([docs](https://github.com/warpdotdev/docs/blob/dbaf7ae2d45f714ce0585085b5708c19bfb6906a/src/content/docs/platform/harnesses/index.mdx)) | Desktop + SaaS + self-hosted worker | Active |
| Conductor | Paid tiers: Pro live collab for ≤5, Teams any size ([pricing](https://www.conductor.build/pricing)) | Yes (+ Cursor, OpenCode) | Yes ([continuumcode](https://continuumcode.ai/guides/what-is-conductor/)) | Mac app (+ Conductor Cloud on paid tiers) | Active |
| Superset | Partly: org hosts/members, Pages with teammate comments, Slack/Linear ([GitHub](https://github.com/superset-sh/superset)) | Yes (+ many) | Yes ("Keep your existing agent subscriptions") | Mac app (Linux exp.), ELv2 | Active |
| Nimbalyst | Teams tier: shared workspace and trackers ([site](https://nimbalyst.com/use-cases/team-collaboration/)) | Yes | Yes | Desktop + iOS; MIT client, closed sync server | Active |
| Vibe Kanban | Was: shared issues/comments/orgs ([GitHub](https://github.com/BloopAI/vibe-kanban)) | Yes (+8) | Yes | Now local-only OSS | Company shut down 2026-04-10 |
| Emdash | No (solo ADE; ticket intake) ([GitHub](https://github.com/generalaction/emdash)) | Yes (25+) | Yes | Desktop, Apache-2.0 | Active |
| Sculptor | No | Claude Code + Pi + any terminal agent ([GitHub](https://github.com/imbue-ai/sculptor)) | Yes | Desktop | Research preview |
| Happy | No (personal remote) | Yes ([GitHub](https://github.com/slopus/happy)) | Yes | Local CLI + E2E relay + apps, MIT | Active |
| T3 Code | No | Yes (+4) ([GitHub](https://github.com/pingdotgg/t3code)) | Yes | Local server + apps, MIT | Active |
| Munder Difflin | No (one human, many agents) | Yes (+10) | Yes ([GitHub](https://github.com/chaitanyagiri/munder-difflin)) | Desktop, MIT + Pro | Active |
| Cyrus | Team-triggered (Linear/GitHub/Slack assignment) ([GitHub](https://github.com/cyrusagents/cyrus)) | Yes (+ Cursor, Gemini, OpenCode) | Yes (BYOK) | Self-host or hosted networking | Active |
| Tembo | Team-triggered (Slack/Linear/GitHub) ([tembo.io](https://www.tembo.io/)) | Yes (+ OpenCode, Amp, Cursor) | Unclear (plans bill a usage allowance) | Vendor cloud | Active |
| Devin | Team sessions + Slack ([pricing guide](https://vp0.com/blogs/devin-ai-pricing-plans-2026)) | No (own agent) | No | SaaS / enterprise VPC | Active |
| Factory | Teams plan ≤10 devs ([alphasignal](https://alphasignal.ai/news/factory-launches-droids-teams-plan-for-small-developer-groups-at-46-per-seat)) | No (own Droid; BYOK models) | Partly (BYOK) | SaaS / on-prem / air-gapped ([TFN](https://techfundingnews.com/factory-jumps-to-5b-in-5-months-with-200m-for-its-ai-droids/)) | Active |
| Terragon | Was team-triggerable via Slack/GitHub ([GitHub](https://github.com/terragon-labs/terragon-oss)) | Yes | Yes | Cloud | Shut down 2026-02-09 |

### Inferences
- **The niche between "solo workbench" and "enterprise agent platform" is crowded but young.** Small cross-vendor teams that keep their own Claude Code/Codex subscriptions and work across time zones are mostly 2026 launches with little disclosed traction. Mosaic's ~2,000 installs and 37 orgs is the only adoption figure I found for a product in this exact niche.
- **No product found targets China+US mixed teams** (e.g., WeChat notifications or China-reachable infrastructure). Every notification surface found is Slack, email, mobile push or Linear/GitHub.
- **Session-centric vs. board-centric:** most "multiplayer" products share a live session (AQ, Superconductor, mpai, Coshell, HumanLayer, Delta) or session memory (Mosaic, Glen). Few are organised around a task board with person-level assignment. The exceptions are Nimbalyst Teams' trackers, Vibe Kanban Cloud (dead), Cyrus (Linear assignment) and Warp Factories (work items, but routed to agents, not people).

### Gaps
- Whether Superconductor, Tembo and Runtime let users plug in their **personal Claude Max / ChatGPT Pro subscriptions** (rather than API keys or vendor-metered usage) was not established.
- Anthropic/OpenAI terms on using consumer subscriptions inside third-party hosted orchestrators were not researched here (big-platform scope). This could materially affect hosted products that rely on bring-your-own-subscription.

## Q3. Which have blockers / asking a teammate for help, cross-person handoff, or human confirmation gates? Which address prompt injection or data exposure?

### Takeaway
- **Blockers and "needs you" queues** exist, but they are almost always **agent → its own human**: Warp Factory Inbox (personal by design), Omnara/Happy/Nimbalyst push notifications, Munder Difflin escalations, Cyrus approvals in Linear.
- **Cross-person handoff** is being built through shared sessions or memory (HumanLayer, Delta, Mosaic, Glen, AQ, Superconductor, mpai), not through an explicit "ask a teammate / I'm blocked on X" object.
- **Closest analogue to Longtable's rule that agents may not perform commitment actions:** QM's design decision to keep admin grants, impersonation and command-approval decisions out of the agent's API. Also mpai's "no remote approval endpoint".
- **Closest analogue to the "accept before it reaches my agent" injection gate:** QM's `enforce` content screening, which quarantines flagged content pending release approval.

### Cited Findings
**Blockers / help / "needs you" signals**
- Warp Factory Inbox item kinds: "Asked question – An agent needs a decision from you", "Spec review", "PR review", "Blocked – A run stopped and needs attention", "Failed". "Inbox only shows work tied to tasks *you* started… a teammate's task, even a blocked or failed one, never appears in your inbox" — [Warp docs](https://github.com/warpdotdev/docs/blob/dbaf7ae2d45f714ce0585085b5708c19bfb6906a/src/content/docs/factories/factory-inbox.mdx).
- Warp's local supervision maps Claude Code hook events (permission request, question, stop, failure) to running/blocked/success states, with a desktop "mailbox" filtered by All/Unread/Errors — [Yep Anywhere Warp review](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/warp.md).
- Omnara (pre-pivot): "real-time visibility into what your agents are doing, and respond to their questions instantly from a single dashboard on web and mobile" — [Omnara GitHub (YC S25)](https://github.com/flumente/omnara).
- Happy: push notifications "when permissions are needed or errors occur" — [happy.engineering](https://happy.engineering/).
- Nimbalyst iOS: "See which agents need you… get a push when an agent is waiting" — [GitHub](https://github.com/Nimbalyst/nimbalyst).
- Munder Difflin: a GOD agent "escalates only when it needs you"; changes flow into "an approvals queue you act on" — [GitHub](https://github.com/chaitanyagiri/munder-difflin).
- Cyrus streams activity back to Linear/GitHub "along with rich interactions like dropdown selects and approvals" — [GitHub](https://github.com/cyrusagents/cyrus).

**Cross-person handoff**
- Mosaic: "Any teammate or agent picks up exactly where someone else left off instead of starting over" — [Launch YC](https://www.ycombinator.com/launches/T3K-mosaic-shared-memory-for-your-team-s-agents).
- Glen: "cross-harness handoff" (early access) — [Yep review](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/multiplayer-ai.md).
- Delta: teammates can "continue work after another participant leaves" — [Yep review](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/multiplayer-ai.md).
- YC's "Multiplayer AI" Request for Startups explicitly calls for teammates to "enter the same live agent session, observe, redirect, and hand off work" — [Yep review citing YC RFS](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/multiplayer-ai.md), [YC RFS](https://www.ycombinator.com/rfs#multiplayer-ai).
- Terragon (dead) had a `terry` CLI for "local task takeover and continuation" — [GitHub](https://github.com/terragon-labs/terragon-oss).
- Warp has local-to-cloud handoff that forks agent history and packages the working tree — [Yep Warp review](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/warp.md).
- bb threads can be handed "off to another agent" (agent-to-agent, not human-to-human) — [GitHub](https://github.com/get-bb/bb).

**Human confirmation gates / authority boundaries**
- QM excludes three actions from the agent self-API "even though the web portal offers them": admin grant changes, impersonation, and **command-approval decisions**. "Each is a decision that authorizes _future_ agent behavior, so the decision itself must come from outside the agent." Strict posture pauses every tool call for human approval — [QM SECURITY.md](https://github.com/yc-software/qm/blob/main/SECURITY.md), [QM README](https://github.com/yc-software/qm).
- Warp Factories pause for "approving the spec", "answering questions" and "merging". The first two "are workflow policy, written into the foreman's instructions". Merging "is enforced by your repository", so human-only merges need branch protection. The review agent's verdict "is advisory" — [Warp docs](https://github.com/warpdotdev/docs/blob/dbaf7ae2d45f714ce0585085b5708c19bfb6906a/src/content/docs/factories/how-factories-work.mdx).
- Warp counter-example: hidden local Claude child agents are launched with `--dangerously-skip-permissions`, and local Codex children with `--dangerously-bypass-approvals-and-sandbox` (product-gated), so they don't block on invisible prompts — [Yep Warp review](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/warp.md).
- HumanLayer's live-session grant lets a guest prompt, interrupt **and resolve approvals** (broader delegation) — [Yep review](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/multiplayer-ai.md).
- mpai: no remote approval endpoint; remote turns needing interactive permission are denied — [Yep review](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/multiplayer-ai.md).
- Factory: Autonomy Off/Low/Medium/High plus an org-managed `maxAutonomyLevel` clamp — [Factory docs](https://docs.factory.ai/cli/user-guides/auto-run), [subagents](https://docs.factory.ai/harness/subagents).
- Runtime: RBAC "scoped per human and per agent" plus command allow/deny lists — [Launch HN](https://news.ycombinator.com/item?id=48225040).
- Omnara's current managed-agents platform has RBAC separating who can manage access, configure, operate or only view agents — [GitHub](https://github.com/omnara-ai/omnara).

**Prompt injection / data exposure**
- QM content screening:
  - `observe` records verdicts; `enforce` "quarantines flagged content pending release approval".
  - "Surface and connector inputs are untrusted data. Authentication proves the source… it does not make the content safe."
  - Known limits: "Security screening is incomplete and heuristic… Classifier approval is not authorization and cannot guarantee prompt-injection resistance"; command policy "is a speed bump against mistakes and injection, not a sandbox boundary".
  - Sharing posture defaults to "Isolated" — [QM README](https://github.com/yc-software/qm), [SECURITY.md](https://github.com/yc-software/qm/blob/main/SECURITY.md).
- Runtime: secrets are injected via a managed proxy "so they never touch the agent directly"; network egress controls — [Launch HN](https://news.ycombinator.com/item?id=48225040).
- Happy: E2E encryption; the relay "can't decrypt your prompts, responses, code, or session context" — [happy.engineering](https://happy.engineering/).
- Warp: publishing a session uploads its content to Warp's service. Factory execution on self-hosted workers still sends code context to Warp's control plane via prompts, transcripts and artifacts — [Yep Warp review](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/warp.md).
- Warp doc conflict: the Remote Control page says teammates can view via link, while the detailed sharing contract says access follows invitation/team/link policy — [Yep Warp review](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/warp.md).
- Factory Droid Shield: local secret scanning and git guardrails; hooks only send data off-machine if configured to — [Factory docs](https://docs.factory.ai/enterprise/privacy-and-data-flows).
- Isolation by sandbox or container is the most common "security" claim: Superconductor cloud sandboxes, Capy per-agent VMs, Terragon sandboxes, Sculptor containers (per earlier descriptions). Worktree-based tools state that "Worktrees separate working files; they do not sandbox processes" — [Superset README](https://github.com/superset-sh/superset).

### Inferences
- **No product found has an explicit cross-person "help request" or "who is stuck / who is needed" object** on a shared board. Warp comes closest structurally but deliberately keeps blockers personal. Longtable's team-visible blockers plus "ask for help" appear differentiated (inferred from absence in the sources reviewed, not proven).
- **No product found gates teammate-authored text** behind recipient acceptance before it enters that recipient's agent context. QM's quarantine-pending-release (for external content flagged by a classifier) is the nearest mechanism. Several multiplayer products (AQ "anyone can type", HumanLayer guest prompting and approvals, Coshell multi-prompting) widen the injection surface instead.
- **Longtable's "commitment actions are human-only and passkey-confirmed on the web" matches QM's documented reasoning** (approvals and grants must come from outside the agent). That gives a citable precedent for the design rather than a novelty claim.

### Gaps
- Could not read HumanLayer's, Superconductor's, AQ's or Mosaic's security pages (blocked). Their handling of teammate-to-agent injection and data residency is unknown.
- No product found documents a passkey/WebAuthn confirmation step for agent-initiated actions. Absence is not verified.

## Q4. Pricing and traction; which shut down, pivoted, or were acquired (2025–2026)?

### Takeaway
- **Money concentrates in own-agent platforms:** Cognition ($48B valuation, Sept 2026) and Factory ($5B, Sept 2026).
- **BYO-subscription orchestrators are cheap or free**, and many died:
  - Terragon shut down (Feb 2026).
  - Bloop/Vibe Kanban shut down (Apr 2026).
  - Charlie is shutting down (service until 2026-10-05).
  - Codegen and Graphite were acquired (Dec 2025).
  - Omnara, Sweep, Gitpod→Ona and Crystal→Nimbalyst pivoted.
- **Survivors with fresh money:** Conductor ($22M A, Mar 2026) and Superset ($11M).
- **Team pricing clusters:** $50–$128 per user per month, or flat team plans.

### Cited Findings

| Product | Pricing (date) | Traction / funding (date) | Event |
|---|---|---|---|
| Conductor | Free local; Pro $50/mo; Teams $60/user/mo; Enterprise ([pricing](https://www.conductor.build/pricing), ~Sept 2026) | $22M Series A, 2026-03-30; ~$24.5M total; "10x user growth since January" ([X](https://x.com/charlieholtz/status/2039027121901957349), [Dealroom](https://app.dealroom.co/news/feed/conductor-raises-22m-series-a-from-spark-and-matrix-for-ai-coding-platform)) | — |
| Superset | Desktop free forever (ELv2); Pro for mobile, price n/a ([GitHub](https://github.com/superset-sh/superset)) | $11M raised; 11K stars, "thousands of DAU"; PH #1 2026-02-27 ([team](https://superset.sh/team), [founderland](https://www.founderland.ai/articles/superset-launches-ide-to-orchestrate-100-ai-coding-agents-in-mpz8db7u)) | — |
| Emdash | Free, Apache-2.0 | YC W26; ~5.9k stars; ">1M downloads" claim (2026-10-02) ([api-evangelist](https://github.com/api-evangelist/emdash)) | — |
| HumanLayer | Free ≤3 users/200 sessions; Pro $100/user/mo ([devtune](https://devtune.ai/verticals/coding-agent-orchestration/humanlayer/pricing)) | YC F24; ~$500K seed (2024, low confidence) ([Tracxn](https://tracxn.com/d/companies/humanlayer/__XZbhI_kKRufCd1LnFm62x7HgBSEk6EtN315vIthngyQ)) | Pivot: HITL API → CodeLayer → multiplayer; OSS deprecated ([GitHub](https://github.com/humanlayer/humanlayer)) |
| Superconductor | Free ≤4 members; Pro $128/mo flat ≤32 members + sandbox hours (Jul 2026) ([aq.dev compare](https://aq.dev/compare/aq-vs-superconductor/)) | n/a | — |
| AQ | Free on own VM; $100/user/mo hosted VM ([aq.dev](https://aq.dev/)) | n/a | — |
| Mosaic | n/a | YC S26; ~2,000 installs, 37 orgs syncing ([Launch YC](https://www.ycombinator.com/launches/T3K-mosaic-shared-memory-for-your-team-s-agents)) | Narrowed from live environment to shared sessions/memory |
| QM | Free OSS (MIT); 3rd-party hosted option ([GitHub](https://github.com/yc-software/qm)) | 5k+ stars day one; HN #2, 500+ pts (2026-07-31) ([Startup Fortune](https://startupfortune.com/y-combinator-open-sources-qm-the-ai-agent-harness-it-uses-to-run-itself/)) | Released 2026-07-31 |
| Warp | Free; Build $20+/mo; Max $200/mo; Business $50/user/mo (2026-10-02) ([Yep review](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/warp.md)) | 65k stars; "800k+ active developers" (company, 2026-09) | Client open-sourced 2026-04-28 |
| Cyrus | Pro $50/mo; Team $120/mo; community self-host free ([pricing](https://www.atcyrus.com/pricing)) | n/a | — |
| Tembo | Free ($10 one-time); Pro $60/mo ≤5 users; Max $200/mo ≤10 users ([Tembo blog](https://www.tembo.io/blog/best-ai-for-coding)) | n/a | — |
| Omnara | Free 10 sessions/mo, then $20/mo (Feb 2026) ([Launch HN](https://news.ycombinator.com/item?id=46991591)) | YC S25; ~2.6k stars ([all-projects](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/all-projects.md)) | Pivoted to managed-agents API ([GitHub](https://github.com/omnara-ai/omnara)) |
| Happy | Free, MIT | ~12.9k stars ([all-projects](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/all-projects.md)) | — |
| Sculptor | Free in beta ([rywalker](https://rywalker.com/research/sculptor)) | Imbue (research lab) | — |
| Devin | Team $500/mo incl. 250 ACUs (3rd-party) ([usagebar](https://usagebar.com/blog/devin-pricing-and-rate-limits)) | Cognition $1B @ $25B pre (2026-05-27); $48B valuation (2026-09-08); Devin ARR ~$492M→~$900M ([TechCrunch](https://techcrunch.com/2026/05/27/ai-coding-startup-cognition-raises-1b-at-25b-pre-money-valuation/), [TechCrunch](https://techcrunch.com/2026/09/08/cognition-hits-48b-valuation-signaling-investors-believe-ai-coding-is-far-from-a-winner-take-all-market/), [ecmsource](https://ecmsource.com/cognition-48b-series-e-2b-devin-900m-arr-september-2026/)) | Windsurf acquired (Jul 2025); renamed Devin Desktop 2026-06-02 ([getcreatr](https://getcreatr.com/windsurf-pricing-2026)) |
| Factory | Pro $20 / Plus $100 / Max $200; Teams ≤10 devs (price conflict) ([theaiagentindex](https://theaiagentindex.com/agents/factory-ai), [alphasignal](https://alphasignal.ai/news/factory-launches-droids-teams-plan-for-small-developer-groups-at-46-per-seat)) | $150M C @ $1.5B (Apr 2026); $200M @ $5B (2026-09-15); >$400M total ([TFN](https://techfundingnews.com/factory-jumps-to-5b-in-5-months-with-200m-for-its-ai-droids/)) | — |
| Ona | Core from $20/mo + OCUs ([infragap](https://infragap.com/tools/ona/)) | n/a | Gitpod → Ona, 2025-09-02 ([Register](https://www.theregister.com/2025/09/03/gitpod_rebrands_as_ona/)) |
| Terragon | — | — | **Shut down** 2026-02-09 ([docs](https://docs.terragonlabs.com/docs/resources/shutdown)) |
| Vibe Kanban (Bloop) | — | "Thousands of software engineers use Vibe Kanban every day" ([shutdown post](https://www.vibekanban.com/blog/shutdown)) | **Shut down** 2026-04-10; OSS continues local-only |
| Charlie Labs | — | — | **Shutting down**; service until 2026-10-05 ([withpurple](https://www.withpurple.com/post/charlie-is-shutting-down-here-are-the-best-alternatives-in-2025)) |
| Codegen | — | Raised $16.2M (2023); $60M last valuation | **Acquired** by ClickUp 2025-12-23; standalone off 2026-01-09 ([ClickUp](https://clickup.com/blog/clickup-codegen-acquisition/)) |
| Graphite | — | 500+ companies; ~$290M last valuation | **Acquired** by Cursor 2025-12-19 ([Cursor](https://cursor.com/blog/graphite), [Fortune](https://fortune.com/2025/12/19/cursor-ai-coding-startup-graphite-competition-heats-up/)) |
| Crystal | — | — | **Renamed/replaced** by Nimbalyst, Feb 2026 ([GitHub](https://github.com/stravu/crystal)) |
| Sweep | JetBrains plugin | — | **Pivoted** from GitHub bot to JetBrains assistant ([tooljunction](https://www.tooljunction.io/ai-tools/sweep)) |
| Amp | Hobby free; Individual $20; seat-free Teams ([rywalker](https://rywalker.com/research/amp-sourcegraph)) | "Profitable" at spin-out | **Spun out** of Sourcegraph, Dec 2025 |

- Vibe Kanban's own shutdown post gives the cause: "the vast majority are free users and we couldn't find a business model that we could get excited about" — [Goodbye bloop](https://www.vibekanban.com/blog/shutdown), quoted in [agi-cli landscape](https://github.com/phnx-labs/agi-cli/blob/main/.agents/artifacts/2026-08-20/landscape-cli-proxy-browser-computer.md).
- Terragon: "We weren't able to reach the level of traction needed to turn Terragon into a sustainable, long-term business" — [Terragon shutdown](https://docs.terragonlabs.com/docs/resources/shutdown).
- An Aug 2026 landscape analysis argues the orchestration layer's survivors (Conductor, Sculptor, container-use) "run no hosted backend". It says "everything in this layer that owned real cloud spend either died or was bought", while frontier labs absorb the function — Claude Code ships subagents and parallel agent teams — [agi-cli landscape (2026-08-20)](https://github.com/phnx-labs/agi-cli/blob/main/.agents/artifacts/2026-08-20/landscape-cli-proxy-browser-computer.md). It also notes that Claude Code "agent teams" (experimental, early 2026) coordinate multiple Claude instances through a shared task list — [SitePoint](https://www.sitepoint.com/anthropic-claude-code-agent-teams/).

### Inferences
- **Hosted-backend risk applies directly to Longtable.** Its shared board needs a hosted backend, exactly the profile that died (Terragon, Vibe Kanban Cloud) unless it is monetised. On the other hand, the team-seat price points in this market ($50–$128/user/mo; Superconductor's $128 flat for ≤32 members) show what small teams are being asked to pay.
- **First-party moves compress free-tier utilities.** Claude Code Remote Control (Feb 2026), agent teams, and Codex/Claude desktop apps undercut remote viewers and orchestrators. Team coordination with explicit human authority is less directly threatened so far.

### Gaps
- No revenue, paid-seat or retention numbers were found for any coordination-layer startup (Conductor, Superset, HumanLayer, Superconductor, AQ, Mosaic). Traction figures are stars, downloads or installs, or company claims.
- Factory Teams price conflict ($60/team + $40/seat vs "$46 per seat") is unresolved. Devin team pricing comes only from third-party blogs.
- No primary source confirms the exact date or wording of the Charlie Labs shutdown announcement (the blog was blocked).

## Q5. What are users praising and complaining about (reviews, HN/Reddit)?

### Takeaway
Direct HN/Reddit access was blocked and the search budget ran out, so the evidence is thin. Recurring themes:
- **Praise:** worktree isolation and "use the subscription I already have" (Conductor, Superset, Emdash); E2E privacy (Happy); fast traction for OSS multiplayer (QM).
- **Complaints:** price stacked on top of an existing Claude/Codex plan (Omnara HN); Mac-only availability (Conductor, Superset primary); shallow integrations ("just a terminal"); vapourware/deprecated OSS (HumanLayer); immature, bug-prone previews (Sculptor); shutdown risk (Terragon, Vibe Kanban, Charlie).

### Cited Findings
- **Omnara Launch HN (Feb 2026), pricing complaints:**
  - One commenter would pay $9, but adding $20 on top of Claude Max at $100 made them want to build an alternative.
  - Another: 10 free sessions is too few.
  - Another: $20 "seems overly expensive compared to open source alternatives like Happy", and they would consider it at $5.
  - Source: [Launch HN: Omnara (search snippet)](https://news.ycombinator.com/item?id=46991591).
- **Conductor:** "the real killer feature is the isolation via git worktrees" — [Korben](https://korben.info/en/conductor-run-ai-agents-parallel-codebase.html), [continuumcode](https://continuumcode.ai/guides/what-is-conductor/). Main complaints in reviews: Mac-only, and "company-wide multiplayer remains gated behind an invite-only paid tier" — [vibecoding.app review](https://vibecoding.app/blog/conductor-review).
- **Happy:** a commenter cited it as the cheaper open-source alternative to Omnara — [Launch HN snippet](https://news.ycombinator.com/item?id=46991591).
- **Emdash:** a competitor calls it "closer to iTerm2 with git worktree management than to a true agent supervisor" — [Yep Anywhere emdash review](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/emdash.md). This is competitor-authored and should be read as biased.
- **HumanLayer:** critical review title "The Context Engineering Framework That's Mostly Vapor" (about the older OSS) — [starlog](https://starlog.is/articles/ai-agents/humanlayer-humanlayer/). The old OSS repo is officially deprecated — [GitHub](https://github.com/humanlayer/humanlayer).
- **Sculptor:** its own README warns "Things will not be perfect. Expect mistakes and bugs… may change quickly and significantly" — [GitHub](https://github.com/imbue-ai/sculptor).
- **Vibe Kanban:** heavy free usage ("thousands… every day") but no viable business model — [shutdown post](https://www.vibekanban.com/blog/shutdown). There was an HN thread asking for "Alternatives to Terragon Labs" after its shutdown — [HN](https://news.ycombinator.com/item?id=46589735).
- **QM:** strong developer interest (HN #2, 500+ points; 5k stars in a day) — [Startup Fortune](https://startupfortune.com/y-combinator-open-sources-qm-the-ai-agent-harness-it-uses-to-run-itself/). The critical review title "Is Quartermaster Ready for Work?" suggests readiness doubts — [wavect](https://wavect.io/blog/qm-ai-agent-harness-review/) (title only).
- **Warp:** a competitor notes that star counts "are a weak attention signal, not evidence of authentic adoption". It also notes the unverified "800k active developers" claim has no activity window — [Yep Warp review](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/warp.md).

### Inferences
- **Users resist paying a second subscription for orchestration** on top of Claude/Codex plans, especially when OSS alternatives exist (Happy, Emdash, T3 Code). Paid value has to come from team and governance features, not from running agents in parallel.
- **The positive signal for Longtable's segment** is YC's explicit "Multiplayer AI" RFS and the rush of S26 entrants (Mosaic, Glen, Runtime) plus QM's reception. The negative signal is the 2026 death rate of thin hosted orchestrators.

### Gaps
- No direct reading of Reddit (r/ClaudeAI, r/ChatGPTCoding, r/ExperiencedDevs) or HN comment threads for Conductor, Superset, Superconductor, HumanLayer, Mosaic, AQ, Delta or QM. Sentiment above is a handful of snippets and competitor or own-vendor statements, so confidence is low.
- No G2/Product Hunt review text was read for team-tier products.
