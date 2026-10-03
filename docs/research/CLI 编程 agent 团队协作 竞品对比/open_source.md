# Open-source tools that coordinate CLI coding agents (Claude Code, Codex, Gemini CLI, ...) across sessions, worktrees and people — state as of 2026-10-03

## Q1. Which projects exist, and what are the hard facts for each?

### Takeaway
About 44 distinct repositories were examined on 2026-10-03 (46 README fetches; steveyegge/gastown and gastownhall/gastown, and ruvnet/claude-flow and ruvnet/ruflo, resolve to the same README). They fall into six groups: (A) server-backed team boards that treat agents as teammates (Paperclip, Multica, Agor, qm, Buzz, Vibe Kanban, agent-kanban, kandev, Symphony, Cyrus, ccpm, Squad); (B) git- or Dolt-native task stores (beads, Gas Town, Backlog.md, Task Master, GNAP); (C) coordination primitives over MCP, CLI or hooks, which mostly run on one machine (MCP Agent Mail, Concord MCP, two unrelated "dibs" projects, foremerge, guild, hcom, Cyclops, Swarm Protocol, AMP, Ruflo); (D) Claude Code <-> Codex handoff and bridge tools (batonpass, AgentBridge, RightSeat); (E) single-developer parallel-session managers (claude-squad, ccmanager, uzi, Crystal (now Nimbalyst), container-use, HelmMate); (F) adjacent or deprecated projects. The highest star counts belong to team-oriented "agents at work" platforms. On 2026-10-03: Paperclip 96,372, Ruflo 73,746, Multica 51,861, Buzz 35,426, Vibe Kanban 28,249, Symphony 27,511.

### Cited Findings

#### Metric definitions and data sources (needed to read the numbers below)
- **Stars, forks, open issues, last push:** from the daily [EvanLi/Github-Ranking CSV for 2026-10-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-10-03.csv), which lists the top 100 repos per language. Older snapshots use the same URL pattern (…/github-ranking-2026-09-03.csv, -07-03, -04-03, -01-03, 2025-10-03). The rank-100 cutoffs on 2026-10-03 were Go 29,259, TypeScript 45,457, Python 57,564, Rust 25,966, JavaScript 35,255, Shell 11,717 and Elixir 1,260 — [Ranking 2026-10-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-10-03.csv)
- **Secondary star source:** [jqueryscript/awesome-claude-code](https://github.com/jqueryscript/awesome-claude-code). It says "Star counts are static and represent the numbers at the time the resource was recorded in this list", and its changelog records "Updated GitHub star counts" on June 14, 2026. Below these are labelled "(list, ~2026-06-14)".
- **"Last commit" (LC):** the commit timestamp of the default-branch head (main, falling back to master), resolved through the Go module proxy on 2026-10-03, e.g. [proxy.golang.org/github.com/steveyegge/beads/@v/main.info](https://proxy.golang.org/github.com/steveyegge/beads/@v/main.info) returned `"Time":"2026-10-03T11:18:14Z"`.
- **"First release":** the first Go tag (via `/@v/list`), or the first npm, PyPI or crates.io publish. This approximates the public launch date, not the repo creation date.
- **Discovery:** [andyrewlee/awesome-agent-orchestrators](https://github.com/andyrewlee/awesome-agent-orchestrators) (cited as "AAO" below). It keeps a "Resting" watchlist of "projects without a push in the last few months (checked 2026-07-28)".

#### A. Team boards / "agents as teammates" (multi-human, server-backed)

**Multica** (multica-ai/multica)
- What it does: "Agents that show up on the board." It is "a source-available workspace where you assign work to AI coding agents the way you'd assign it to a teammate — they pick up the issue, report progress, raise blockers, and hand it back for review." The agent "comments as it goes". — [README](https://github.com/multica-ai/multica)
- Mechanism: the agent runtime is "a daemon on your laptop or cloud box. Code never leaves it". Self-hosting uses "Docker Compose or Helm", and there is also a cloud quickstart. "Autopilots" run standups and audits on a cron. A self-hosted server "sends one anonymous, deployment-level snapshot a day". — [README](https://github.com/multica-ai/multica)
- Humans and governance: roles are `owner`, `admin` and `member`, plus per-agent access scopes. Review gates: "Work lands in review, not in main. You decide what ships." — [README](https://github.com/multica-ai/multica)
- Agents named in the README: Claude Code, Codex, Cursor, Copilot, OpenCode, Kiro, Qwen, Pi — [README](https://github.com/multica-ai/multica)
- License: the "Multica License" is Apache-2.0 "subject to the additional conditions in Part I" — [LICENSE](https://github.com/multica-ai/multica/blob/main/LICENSE)
- Stars 51,861, forks 6,738, open issues 967, language Go (2026-10-03). Description: "Make humans and AI agents work as one team — open-source and self-hostable." — [Ranking](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-10-03.csv)
- First tag v0.1.0 on 2026-01-15 (164 tags). LC 2026-10-02T14:25Z — [Go proxy](https://proxy.golang.org/github.com/multica-ai/multica/@v/main.info)

**Paperclip** (paperclipai/paperclip)
- What it does: "Open-source orchestration for teams of AI agents." It is "a Node.js server and React UI that orchestrates a team of AI agents to run a business." It has a mixed human-and-agent "Org Chart for Agents — Roles, permissions & boundaries for humans and agents." — [README](https://github.com/paperclipai/paperclip)
- Work system: "atomic checkout with execution locks, first-class blocker dependencies, comments, documents, attachments"; "A single assignee and execution locks prevent competing runs from claiming the same task." — [README](https://github.com/paperclipai/paperclip)
- Governance and security: "Approval gates are enforced, config changes are revisioned, and bad changes can be rolled back safely." Connector "gateway actions" can be set to "Allowed, Ask first, or Off". It offers "Two deployment modes (trusted local or authenticated), human roles and permissions, agent API keys, short-lived run JWTs, company memberships, and invite flows". Company templates are exported "with secret scrubbing". — [README](https://github.com/paperclipai/paperclip)
- Agents "wake on heartbeats to claim tickets, governed by org charts, budgets, and approval gates" — [AAO](https://github.com/andyrewlee/awesome-agent-orchestrators)
- Agents named: Claude Code, Codex, Gemini, Cursor, OpenCode. There is a "Paperclip Cloud waitlist". — [README](https://github.com/paperclipai/paperclip)
- MIT. The npm package `paperclipai` was first published 2026-03-03 and has 1,677 versions; the latest, 2026.1001.0, was published 2026-10-03 — [npm](https://registry.npmjs.org/paperclipai)
- Stars 96,372, forks 16,318, open issues 2,693, last push 2026-10-03T03:50Z — [Ranking](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-10-03.csv)

**Agor** (preset-io/agor)
- What it does: "Team command center for all things agentic … a self-hosted, multiplayer-ready web workspace for running coding agents — Claude Code, Codex, Gemini, and others — on isolated git branches … Agents run in the browser instead of a terminal … Run it solo in a few minutes; turn on multiplayer and Unix-level isolation when you bring your team." — [README](https://github.com/preset-io/agor)
- Multiplayer features: the board shows "branches as cards, zones as regions, agent sessions, and — optionally — teammates present live", with "live cursors, comments, and shared sessions/environments". It is "MCP-native": "sessions are auto-issued a token". A scheduler "Powers teammate heartbeats, standups, and automated audits." — [README](https://github.com/preset-io/agor)
- Security: "Branch-scoped permission tiers, per-user credentials and env vars, and explicit execution modes (simple / sandbox / delegated)"; "trusted local, fail-closed sandbox, or delegated external execution" — [README](https://github.com/preset-io/agor)
- Agents: Claude Code, Codex, Gemini, OpenCode, Copilot, Cursor (beta) — [README](https://github.com/preset-io/agor)
- License: BUSL-1.1 with "Change Date: 2029-01-15", after which it becomes Apache-2.0 — [LICENSE](https://github.com/preset-io/agor/blob/main/LICENSE). The npm package `agor-live` was first published 2025-10-27 and has 114 versions; 0.26.9 was published 2026-10-02 — [npm](https://registry.npmjs.org/agor-live). LC 2026-10-03T00:48Z — [Go proxy](https://proxy.golang.org/github.com/preset-io/agor/@v/main.info)

**Vibe Kanban** (BloopAI/vibe-kanban)
- Status: the README banner reads "Vibe Kanban is sunsetting. Read the announcement." and links to vibekanban.com/blog/shutdown — [README](https://github.com/BloopAI/vibe-kanban)
- What it does: "Use kanban issues to plan work, either privately or with your team." Each workspace gives an agent "a branch, a terminal, and a dev server". You can "Review diffs and leave inline comments" that go back to the agent. Self-hosting "Vibe Kanban Cloud" is supported via Docker. — [README](https://github.com/BloopAI/vibe-kanban)
- Agents: Claude Code, Codex, Gemini, Cursor, Copilot, OpenCode, Amp, Droid, Qwen — [README](https://github.com/BloopAI/vibe-kanban)
- License Apache-2.0 — [LICENSE](https://github.com/BloopAI/vibe-kanban/blob/main/LICENSE)
- npm first published 2025-06-20. 0.1.44 came out 2026-04-24, then nothing until 0.1.45-permtest.0 on 2026-09-16 and 0.1.45 on 2026-09-19 — [npm](https://registry.npmjs.org/vibe-kanban). LC 2026-09-19 — [Go proxy](https://proxy.golang.org/github.com/!bloop!a!i/vibe-kanban/@v/main.info)
- Stars 28,249, forks 3,030, open issues 388 (2026-10-03) — [Ranking](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-10-03.csv). AAO's "Resting" list shows its last commit as 2026-04 (as checked 2026-07-28) — [AAO](https://github.com/andyrewlee/awesome-agent-orchestrators)

**agent-kanban** (saltbo/agent-kanban)
- What it does: "a mission-control board for autonomous software agents. It takes humans out of the execution loop without removing human control: people observe work, inspect execution, and make review decisions." "Human review gates — submitted work must be accepted or rejected by an …" (the line was cut off in extraction; "authorized humans" appears elsewhere in the README). "Verified execution provenance — a Task Claim records the exact runtime". Sessions are carried by "the Agent's signed binding". It integrates through a GitHub App. — [README](https://github.com/saltbo/agent-kanban)
- AAO describes it as a "Leader-worker task board with cryptographic agent identity. Claude Code, Codex, Gemini CLI." — [AAO](https://github.com/andyrewlee/awesome-agent-orchestrators)
- License FSL-1.1-ALv2 (Functional Source License with an Apache 2.0 future license) — [LICENSE](https://github.com/saltbo/agent-kanban/blob/main/LICENSE). First tag v1.1.0 on 2026-03-22 (73 tags); LC 2026-09-13 — [Go proxy](https://proxy.golang.org/github.com/saltbo/agent-kanban/@v/main.info)

**kandev** (kdlbs/kandev)
- A kanban workbench where you "customize workflows, agent profiles, runtimes, prompts, and review gates", and "Define workflows once, share them across the team". It can "Publish redacted task conversation snapshots as secret GitHub Gists". An "Office mode" is in progress: "agent instances with roles and permissions, dashboards, inbox/approvals". — [README](https://github.com/kdlbs/kandev)
- "multi-step workflows assign a different agent per step behind human gates" — [AAO](https://github.com/andyrewlee/awesome-agent-orchestrators)
- AGPL-3.0-only. npm first published 2026-01-18 (133 versions); 0.96.0 published 2026-09-27 — [npm](https://registry.npmjs.org/kandev). LC 2026-10-03T15:58Z — [Go proxy](https://proxy.golang.org/github.com/kdlbs/kandev/@v/main.info)

**qm** (yc-software/qm)
- What it does: "A multiplayer agent harness for work. In Slack and on the web. Run it in your own cloud, with your own models and keys." "Each person and each room has its own scoped memory, files, keychain view, permissions, crons, web apps, and durable sandbox." State is persisted in Postgres; without it, "sessions live in process memory and vanish on restart". — [README](https://github.com/yc-software/qm)
- Security postures: **Strict**, where "every harness tool call pauses for human approval"; **Auto** (the default), which "blocks private-network access"; **Dangerous**, with "no tool approval gates, and content screening only observes". Content screening `securityScreen.mode` can be off (the default), observe or enforce; "`enforce` quarantines flagged content pending release approval". A "predeclared command policy — approval rules and hard denials for things like recursive deletes or destructive SQL — applies in every posture". — [README](https://github.com/yc-software/qm)
- MIT. npm `@yc-software/qm` first published 2026-07-29; 0.1.14 published 2026-10-02 — [npm](https://registry.npmjs.org/@yc-software%2Fqm). LC 2026-10-03 — [Go proxy](https://proxy.golang.org/github.com/yc-software/qm/@v/main.info)

**Buzz** (block/buzz)
- What it does: "A workspace where humans and agents build together, on a relay you own." It is a Nostr relay: "every message, reaction, workflow step, review approval, and git event is a signed event in one log". "Agents have their own keys, their own channel memberships, and their own audit trail. Scoped by identity". The model is "Branch as room", with YAML workflows. It is self-hostable and names Claude Code, Codex and Goose. — [README](https://github.com/block/buzz)
- Apache-2.0 — [LICENSE](https://github.com/block/buzz/blob/main/LICENSE). First tag 2026-06-12 (103 tags); LC 2026-10-03 — [Go proxy](https://proxy.golang.org/github.com/block/buzz/@v/main.info)
- Stars 32,000 on 2026-09-03 and 35,426 on 2026-10-03 (Rust) — [Ranking 09-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-09-03.csv), [Ranking 10-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-10-03.csv)

**ox / SageOx** (sageox/ox)
- What it does: "The hivemind for human-agent teams." It "loads your team's decisions, conventions, and session history into every coding agent session automatically" and records sessions. "Secrets are stripped locally before anything uploads" using `[REDACTED_*]` markers. However, "there is no self-hosted or local-only ledger", and "Enterprise self-hosted deployment isn't available today". — [README](https://github.com/sageox/ox)
- The CLI is MIT. First tag v0.1.0 on 2026-02-18; latest v0.20.0; LC 2026-10-03 — [Go proxy](https://proxy.golang.org/github.com/sageox/ox/@v/main.info)

**Symphony** (openai/symphony)
- What it does: "Symphony turns project work into isolated, autonomous implementation runs, allowing teams to manage work instead of supervising coding agents." In the demo it monitors a Linear board and spawns agents that provide proof of their work. The README warns it is "a low-key engineering preview for testing in trusted environments". — [README](https://github.com/openai/symphony)
- Apache-2.0, written in Elixir. Stars 27,511, forks 2,853 (2026-10-03) — [Ranking](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-10-03.csv). First tag v0.0.1 on 2026-07-18, although the repo was already in the 2026-04-03 ranking. LC 2026-09-15 — [Go proxy](https://proxy.golang.org/github.com/openai/symphony/@v/main.info)

**Cyrus** (cyrusagents/cyrus)
- What it does: "Cyrus monitors (Linear|GitHub|GitLab|Slack) issues assigned to it, creates isolated Git worktrees for each issue". It works with Claude Code, Codex, Cursor, Gemini and OpenCode and is "a BYOK platform". It is configured through the dashboard at app.atcyrus.com, with community and paid self-hosting and "Pro & Team Plans". — [README](https://github.com/cyrusagents/cyrus)
- License conflict: the README says Apache-2.0 but npm `cyrus-ai` metadata says MIT — [README](https://github.com/cyrusagents/cyrus), [npm](https://registry.npmjs.org/cyrus-ai). npm first published 2025-06-12; 0.2.73 published 2026-09-30. LC 2026-10-02 — [Go proxy](https://proxy.golang.org/github.com/cyrusagents/cyrus/@v/main.info)

**ccpm** (automazeio/ccpm)
- What it does: GitHub Issues act as the "Single source of truth … Issue state is project state. Comments are the audit trail." It goes from PRD to epic to sub-issues, with a dedicated worktree per epic. "Team collaboration — multiple agents (or humans) work on the same project simultaneously. Progress is visible in real-time through issue comments." Agents named: Claude Code, Codex, Cursor, OpenCode, Amp, Droid. — [README](https://github.com/automazeio/ccpm)
- MIT. LC 2026-03-18 — [Go proxy](https://proxy.golang.org/github.com/automazeio/ccpm/@v/main.info). Stars 8.2k (list, ~2026-06-14) — [jq list](https://github.com/jqueryscript/awesome-claude-code)

**Squad** (bradygaster/squad)
- What it does: "Human-led AI agent teams for any project … a human-directed AI development team through GitHub Copilot". The specialist agents "live in your repo as files" in `.squad/` team state, which `squad upgrade` never touches. "People stay accountable for priorities, approvals, and final changes." The SDK offers "hook pipelines, file-write guards, PII scrubbing, reviewer lockout". In its gh-aw auto-implementation mode (opt-in), "Human review and merge are always required". However, the quickstart recommends `--yolo` because "Without it, Copilot will prompt you to approve each one." The README has a Chinese edition. — [README](https://github.com/bradygaster/squad)
- The only runtime the README names is GitHub Copilot; Claude Code and Codex are not mentioned — [README](https://github.com/bradygaster/squad)
- MIT. npm `@bradygaster/squad-cli` and `@bradygaster/squad-sdk` were first published 2026-02-21; 1.0.0 was published 2026-10-03 — [npm](https://registry.npmjs.org/@bradygaster%2Fsquad-cli). LC 2026-10-03T06:46Z — [Go proxy](https://proxy.golang.org/github.com/bradygaster/squad/@v/main.info)

#### B. Git- or Dolt-native task stores

**beads / `bd`** (steveyegge/beads; npm and PyPI metadata now point to gastownhall/beads)
- What it does: "Distributed graph issue tracker for AI agents, powered by Dolt." Embedded Dolt is the default and is a "single writer". `bd init --server` connects to an external `dolt sql-server` "for multiple concurrent writers". "Cross-machine sync uses `bd dolt push` / `bd dolt pull` against `refs/dolt/data` on your git remote", and "`.beads/issues.jsonl` is an export … not the source of truth". "Hash-based IDs (`bd-a1b2`) prevent merge collisions in multi-agent/multi-branch workflows". `bd update <id> --claim` will "Atomically claim a task (sets assignee + in_progress)". — [README](https://github.com/steveyegge/beads)
- MIT. First Go tag v0.9.1 on 2025-10-14 (134 tags) — [Go proxy list](https://proxy.golang.org/github.com/steveyegge/beads/@v/list). `beads-mcp` on PyPI was first released 2025-10-15 (117 releases) — [PyPI](https://pypi.org/pypi/beads-mcp/json). npm `@beads/bd` was first published 2025-11-03; 1.3.1 was published 2026-10-01 — [npm](https://registry.npmjs.org/@beads%2Fbd). The CHANGELOG lists 1.3.0 on 2026-09-15 — [CHANGELOG](https://github.com/steveyegge/beads/blob/main/CHANGELOG.md). LC 2026-10-03T11:18Z — [Go proxy](https://proxy.golang.org/github.com/steveyegge/beads/@v/main.info)
- There is now a fork ecosystem: the MCP Agent Mail installer "Installs Beads Rust (`br`), a Rust reimplementation … and creates a `bd` shell alias … This replaces any existing `bd` (Go) installation" — [Agent Mail README](https://github.com/Dicklesworthstone/mcp_agent_mail)

**Gas Town** (gastownhall/gastown; the steveyegge/gastown raw path serves the same README)
- What it does: "Multi-agent orchestration system for Claude Code, GitHub Copilot, and other AI agents with persistent work tracking", with "Built-in mailboxes, identities, and handoffs". "Work persists in git-backed hooks". Here a Gas Town "hook" is "Git worktree-based persistent storage", not a Claude Code hook. The Refinery is a "Per-rig merge queue processor … Bors-style bisecting queue". Escalations "route through Deacon -> Mayor -> Overseer based on severity". Humans get "Crew" workspaces via `gt crew add yourname`. "Wasteland" is a "Federated work coordination network linking Gas Towns through DoltHub. Rigs post wanted items, claim work from other towns, submit completion evidence, and earn portable reputation". The Copilot preset uses `--yolo`. — [README](https://github.com/gastownhall/gastown)
- AAO says it "Scales to 20-30 agents with a coordinator, git-backed issue tracking, health watchdogs, and a Bors-style merge queue" — [AAO](https://github.com/andyrewlee/awesome-agent-orchestrators)
- MIT. First tag v0.1.1 on 2026-01-02; latest v1.2.1. LC 2026-07-23 — [Go proxy](https://proxy.golang.org/github.com/gastownhall/gastown/@v/main.info)

**Backlog.md** (MrLesk/Backlog.md)
- What it does: "Markdown‑native Task Manager & Kanban visualizer for any Git repository". Tasks are plain files in the repo. `backlog browser` serves a local web Kanban. The MCP connector configures Claude Code, Codex, Gemini CLI, Kiro or Cursor. "Local-first -- no server, no account, no telemetry". Approval happens by prompt convention ("Wait for my approval before coding"), and conflicts are avoided by "One task at a time … one PR per task". — [README](https://github.com/MrLesk/Backlog.md)
- MIT. npm first published 2025-06-13 (232 versions); 1.53.0 published 2026-09-24 — [npm](https://registry.npmjs.org/backlog.md). The Go proxy could not build a module zip because some filenames contain apostrophes, so the LC is unknown. npm shows activity in September 2026.

**Taskmaster** (eyaltoledano/claude-task-master)
- What it does: AI task management through an MCP server for Cursor, Claude Code, Codex, Gemini and Windsurf. The docs live on tryhamster.com and include "Team Collaboration". The MCP config needs provider API keys. — [README](https://github.com/eyaltoledano/claude-task-master)
- License: MIT plus Commons Clause ("MIT WITH Commons-Clause" on npm) — [LICENSE](https://github.com/eyaltoledano/claude-task-master/blob/main/LICENSE), [npm](https://registry.npmjs.org/task-master-ai)
- npm first published 2025-03-22. 1.0.0-rc.0 came out 2026-02-14 and rc.1 on 2026-02-18; the last publish was 0.43.1 on 2026-03-31 — [npm](https://registry.npmjs.org/task-master-ai). LC on main 2026-04-23 and on next 2026-03-31 — [Go proxy main](https://proxy.golang.org/github.com/eyaltoledano/claude-task-master/@v/main.info), [Go proxy next](https://proxy.golang.org/github.com/eyaltoledano/claude-task-master/@v/next.info)

**GNAP** (farol-team/gnap)
- "coordinate AI agents with just git … Four JSON files. That's the entire protocol." "Git history IS the audit log." "humans and AI agents are both first-class participants". MIT. LC 2026-03-17 — [README](https://github.com/farol-team/gnap), [Go proxy](https://proxy.golang.org/github.com/farol-team/gnap/@v/main.info). Listed under AAO "Resting" — [AAO](https://github.com/andyrewlee/awesome-agent-orchestrators)

#### C. Coordination primitives over MCP, CLI or hooks

**MCP Agent Mail** (Dicklesworthstone/mcp_agent_mail)
- What it does: "A mail-like coordination layer for coding agents, exposed as an HTTP-only FastMCP server". It provides identities, an inbox and outbox, searchable threads and "voluntary file reservation 'leases'". It is "backed by Git (for human-auditable artifacts) and SQLite (for indexing and queries)". — [README](https://github.com/Dicklesworthstone/mcp_agent_mail)
- Trust and access: "The server enforces per-project isolation by default and adds an optional consent layer". Under `contacts_only`, agents "require an approved contact link first", and the example shows `Contact Policy: open`. Auth is a bearer token or JWT+JWKS. However, "GET pages in the UI are not gated by the RBAC middleware (it classifies POSTed MCP calls only)", and there is an `HTTP_ALLOW_LOCALHOST_UNAUTHENTICATED` option. The "Human Overseer" web composer adds "an automatic preamble" that tells agents to "Pause current work" and "Prioritize the human's request". A commercial iOS companion stack exists. — [README](https://github.com/Dicklesworthstone/mcp_agent_mail)
- Agents named: Claude Code, Codex, Gemini CLI, Factory Droid, OpenCode, Cline, Windsurf — [README](https://github.com/Dicklesworthstone/mcp_agent_mail)
- License: "MIT License (with OpenAI/Anthropic Rider)", which includes an "ADDITIONAL RIDER / RESTRICTION (OpenAI / Anthropic)". The rider text was not fully reviewed. — [LICENSE](https://github.com/Dicklesworthstone/mcp_agent_mail/blob/main/LICENSE). LC 2026-09-29 — [Go proxy](https://proxy.golang.org/github.com/!dicklesworthstone/mcp_agent_mail/@v/main.info)
- The PyPI package named `mcp-agent-mail` belongs to a fork (jleechanorg/mcp_agent_mail), not to this repo — [PyPI](https://pypi.org/pypi/mcp-agent-mail/json)

**Concord MCP** (Get-Concord-AI/concord-mcp)
- What it does: "Let Claude Code, Codex, Cursor, Gemini CLI, and Grok Build talk to each other. The open-source, local-first communication and coordination layer". It lets agents "detect overlapping work before agents edit, share decisions, and hand off tasks with evidence - through one MCP server". `start_work` "registers presence, claims or accepts one task, and reports scope overlaps before editing". — [README](https://github.com/Get-Concord-AI/concord-mcp)
- Concurrency and acceptance: "If two agents act on the same version, only the first transition succeeds. Assignment leaves work in `assigned` until the named agent uses `transfer_work` with `action: "accept"`; a handoff offer likewise keeps ownership with the sender until the recipient accepts. Every ownership change is retained in an append-only audit history." It also writes a human-readable HANDOFF.md. It is "**Not** an orchestrator, code reviewer, hosted sync service". — [README](https://github.com/Get-Concord-AI/concord-mcp)
- MIT. npm first published 2026-07-17 (19 versions); 0.10.5 published 2026-09-23 — [npm](https://registry.npmjs.org/@concord-ai%2Fconcord-mcp). LC 2026-09-25 — [Go proxy](https://proxy.golang.org/github.com/!get-!concord-!a!i/concord-mcp/@v/main.info)

**Swarm Protocol** (phuryn/swarm-protocol)
- What it does: "Coordination protocol for agent-first teams. No UI. No sprints. No Jira. Just state sync." It is a headless MCP server with 19 tools on a "Single PostgreSQL instance". Intents move through `draft → open → claimed → done`, and it detects file conflicts. It contrasts itself with Claude Code Agent Teams, which "coordinates agents within a single session … Intra-session". Status is "Alpha". — [README](https://github.com/phuryn/swarm-protocol)
- MIT. LC 2026-03-15 — [Go proxy](https://proxy.golang.org/github.com/phuryn/swarm-protocol/@v/main.info). Listed under AAO "Resting" — [AAO](https://github.com/andyrewlee/awesome-agent-orchestrators)

**dibs (polymatx)** (polymatx/dibs)
- What it does: "Call dibs on files. Run parallel coding agents without collisions." A claim is a JSON lease (TTL 30m by default, 24h max) stored in the git common dir, so it is "visible to all worktrees immediately, without commits". It uses an advisory lock, a JSONL journal, broadcast notes with per-agent read tracking, and "lessons" stored as markdown under `.dibs/lessons/`, which are committed and shared "via `git pull`". It also runs a stdio MCP server. — [README](https://github.com/polymatx/dibs)
- Enforcement: a Claude Code `PreToolUse` hook blocks a colliding edit with exit code 2, and a git pre-commit hook covers other agents. "Both hooks fail open". It is a "Cooperative trust model … not a security boundary". "Live claims are per machine … Cross-machine live coordination is on the roadmap." — [README](https://github.com/polymatx/dibs)
- MIT. v0.1.0 tagged 2026-08-04. LC 2026-09-01 — [Go proxy](https://proxy.golang.org/github.com/polymatx/dibs/@v/main.info)

**dibs (abevz)**, a different project with the same name (abevz/dibs)
- What it does: "a shared ready queue and an atomic claim: one gets the lease". A daemon is the "single writer to a local SQLite database", and the CLI and MCP wrapper reach it over HTTP on a Unix socket. "It runs on one machine and does not sync leases across machines." The `dibs watch` TUI shows ready, blocked, in-progress and deferred work, plus a STALE lane. Claude Code and Codex hooks show ready work when a session starts. — [README](https://github.com/abevz/dibs)
- GitHub Issues: it imports and publishes issues through the user's own `gh`, and "dibs stores no GitHub token". "Imported titles and bodies are task data, not instructions for the agent". The lease token should be kept private. — [README](https://github.com/abevz/dibs)
- Apache-2.0. v0.1.0-rc.1 tagged 2026-09-25. LC 2026-10-02 — [Go proxy](https://proxy.golang.org/github.com/abevz/dibs/@v/main.info)

**foremerge** (naw103/foremerge)
- What it does: "the open-source coordination protocol for coding agents, built above Git. Agents keep isolated worktrees while sharing intent". It consists of an "MCP server, SQLite store, deterministic conflict detector". `resolve_conflict` records an audited resolution. Work accepted without verification is "recorded as `UNVERIFIED`". The README also states limits: "it is not a remote identity signature or distributed consensus", "Foremerge does not sandbox them", and "The MVP does not replicate SQLite across machines". — [README](https://github.com/naw103/foremerge)
- Apache-2.0. The crate was created 2026-08-25 — [crates.io](https://crates.io/api/v1/crates/foremerge). npm 0.5.1 was published 2026-10-03 — [npm](https://registry.npmjs.org/foremerge). LC 2026-10-03 — [Go proxy](https://proxy.golang.org/github.com/naw103/foremerge/@v/main.info)

**guild** (mathomhaus/guild)
- What it does: "a single compiled Go binary containing a first-class MCP server backed by embedded SQLite. State lives strictly on local host". It offers "Atomic claims, no collisions" and BM25 plus vector search, while "Guildmasters (us humans) stay in the loop for important decisions". Agents named: Claude Code, Codex, Cursor. — [README](https://github.com/mathomhaus/guild)
- Apache-2.0. v0.1.0 tagged 2026-04-20. LC 2026-08-26 — [Go proxy](https://proxy.golang.org/github.com/mathomhaus/guild/@v/main.info)

**hcom** (aannoo/hcom)
- What it does: "a CLI that agents use to message, watch, and spawn each other across terminals". "Hooks record activity to a local SQLite database and deliver messages from it." It can "Connect agents across machines via MQTT relay" with a pre-shared key. Agents: Claude Code, Codex, Gemini, Cursor, Copilot, OpenCode, Pi. — [README](https://github.com/aannoo/hcom)
- Stated security limits: "`hcom relay` is one trust domain for one operator's devices … no scoped roles, read-only peers, or per-device permissions"; "Sender identity is routing metadata, not authorization"; "Prompt injection from an authenticated peer. Enrollment is total trust — a peer can launch, kill, and drive agents via RPC". — [README](https://github.com/aannoo/hcom)
- MIT. First PyPI release 2025-08-01; 70 releases, the latest on 2026-10-01 — [PyPI](https://pypi.org/pypi/hcom/json). LC 2026-10-01 — [Go proxy](https://proxy.golang.org/github.com/aannoo/hcom/@v/main.info)

**Cyclops** (cyclops-team/cyclops)
- What it does: it "coordinates coding agents that run in tmux. It gives them a durable mailbox, a one-line doorbell into the recipient's pane, and an optional workspace where a human can see and control the whole team." Its motivation is that raw `tmux send-keys` "has no durable acceptance, sender identity, ordering, claim, or receipt, and it types over whatever a human has half-written in the composer". — [README](https://github.com/cyclops-team/cyclops)
- AAO lists "FIFO delivery per recipient, and fail-closed human-composer protection" — [AAO](https://github.com/andyrewlee/awesome-agent-orchestrators)
- MIT. First tag v0.2.0-beta on 2026-08-27. LC 2026-09-06 — [Go proxy](https://proxy.golang.org/github.com/cyclops-team/cyclops/@v/main.info)

**Agent Messaging Protocol (AMP)** (agentmessaging/protocol)
- What it does: "A federated protocol enabling AI agents to discover, authenticate, and message each other across different systems and providers." It uses "Ed25519 signatures" and "Trust annotations — External messages marked for prompt injection defense". Its reference implementation is AI Maestro (23blocks-OS/ai-maestro). — [README](https://github.com/agentmessaging/protocol)
- Trust levels in the spec: `verified` (same tenant, signature valid) passes through "without wrapping". `external` (cross-tenant, signature valid) "MUST wrap with `<external-content>` tags", in the form `<external-content source="agent" sender="…" trust="external">`. `untrusted` covers "Unverified, missing signature, or anomalous" messages. — [spec/07-security.md](https://github.com/agentmessaging/protocol/blob/main/spec/07-security.md)
- Message `security` object: `trust_level` and `injection_flags` (e.g. `["instruction_override"]`). "Recipients MUST verify signatures before trusting a message". `thread_id` is excluded from the signature, so recipients should not trust it from the wire. — [spec/04-messages.md](https://github.com/agentmessaging/protocol/blob/main/spec/04-messages.md)
- Apache-2.0. LC 2026-10-03 — [Go proxy](https://proxy.golang.org/github.com/agentmessaging/protocol/@v/main.info)

**Ruflo, formerly claude-flow** (ruvnet/ruflo)
- Described as "The original agent harness. Deploy intelligent multi-player swarms…" — [Ranking](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-10-03.csv). It installs as an MCP server in Claude Code (`claude mcp add claude-flow -- npx ruflo@latest mcp start`). Federation claims: "Zero-trust federation — Remote agents start untrusted. Identity proven via mTLS + ed25519 challenge-response" and "PII-gated data flow — 14-type detection pipeline … Per-trust-level policies: BLOCK, REDACT, HASH, or PASS". — [README](https://github.com/ruvnet/ruflo)
- MIT. npm `claude-flow` was first published 2025-06-10 and has 849 versions; 3.51.1 was published 2026-10-02 — [npm](https://registry.npmjs.org/claude-flow). npm `ruflo` was first published 2026-02-16 — [npm](https://registry.npmjs.org/ruflo). LC 2026-10-03T15:56Z — [Go proxy](https://proxy.golang.org/github.com/ruvnet/ruflo/@v/main.info)
- Stars 73,746, forks 8,761, open issues 690 (2026-10-03) — [Ranking](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-10-03.csv); 59.4k (list, ~2026-06-14) — [jq list](https://github.com/jqueryscript/awesome-claude-code)

#### D. Claude Code <-> Codex handoff and bridges

**batonpass** (solsebb/batonpass)
- What it does: "Automatic, local, verbatim session handoff between Codex and Claude Code." A `Stop` hook "reads the new lines of the session transcript, removes secrets, stores the dialogue in a local SQLite ledger (`~/.baton/baton.db`)". A `SessionStart` hook "injects the latest brief, about 2,000 tokens … No network call, no model call". A `PreCompact` hook also captures context. Sessions are grouped by git remote, so worktrees share history. "The brief is framed as prior context, not instructions." The ledger directory is mode 0700 and the database 0600, and "Tool outputs are never stored". — [README](https://github.com/solsebb/batonpass)
- Its own recall evaluation over 64 questions scored the default brief at 71.9% on its own and 95.3% with one search; no context scored 0% — [README](https://github.com/solsebb/batonpass)
- MIT. A single tag, v0.1.0, on 2026-09-26, which equals the LC — [Go proxy](https://proxy.golang.org/github.com/solsebb/batonpass/@v/main.info)

**AgentBridge** (raysonmeng/agent-bridge)
- What it does: a "Local bridge for bidirectional communication between Claude Code and Codex inside the same working session". A daemon forwards between a Claude Code MCP channel and the Codex app-server protocol. It routes by markers (`[IMPORTANT]`, `[STATUS]`). It has a Chinese README and is discussed on LINUX DO. — [README](https://github.com/raysonmeng/agent-bridge)
- Default security posture: "`abg claude` launches with `--dangerously-skip-permissions` and `abg codex` launches with `--yolo` by default"; you can opt out with `--safe` — [README](https://github.com/raysonmeng/agent-bridge)
- MIT. First tag 2026-03-20; npm first published 2026-03-29; 0.1.31 — [npm](https://registry.npmjs.org/@raysonmeng%2Fagentbridge). LC 2026-09-12 — [Go proxy](https://proxy.golang.org/github.com/raysonmeng/agent-bridge/@v/main.info)

**RightSeat** (sergiobuilds/rightseat)
- What it does: "puts a visible AI operator beside any terminal AI worker" running in tmux. The operator "seat" can "answer prompts, submit drafts, request evidence, or stop". Decisions are written to a JSONL audit log, and "the worker's own 'done' claim is never treated as proof". It "does not auto-pick a worker". It targets Claude, Codex and other terminal agents, and supports tmux only. — [README](https://github.com/sergiobuilds/rightseat)
- MIT. LC 2026-08-15 — [Go proxy](https://proxy.golang.org/github.com/sergiobuilds/rightseat/@v/main.info)

Also listed in AAO without individual verification: "handoff (dazuiba/handoff) — Delegates a task to DeepSeek, Codex, or Claude from inside your current Claude Code or Codex session"; "agent-console — Rust TUI that finds Codex and Claude Code sessions from the providers' own transcripts" — [AAO](https://github.com/andyrewlee/awesome-agent-orchestrators)

#### E. Single-developer parallel-session managers and isolation

- **claude-squad** (smtg-ai/claude-squad): a terminal app that manages Claude Code, Codex, Gemini and Aider sessions using "tmux to create isolated terminal sessions" and "git worktrees". It can run tasks "in the background (including yolo / auto-accept mode!)" — [README](https://github.com/smtg-ai/claude-squad). AGPL-3.0 — [LICENSE](https://github.com/smtg-ai/claude-squad/blob/main/LICENSE). First tag 2025-03-30; main's head is v1.0.20, dated 2026-08-20 — [Go proxy](https://proxy.golang.org/github.com/smtg-ai/claude-squad/@v/main.info). Stars 7.8k (list, ~2026-06-14) — [jq list](https://github.com/jqueryscript/awesome-claude-code)
- **ccmanager** (kbwo/ccmanager): manages sessions for "Claude Code, Gemini CLI, Codex CLI, Cursor Agent, Copilot CLI, Cline CLI, OpenCode, Kimi CLI" across worktrees. It has an experimental "Auto Approval" feature that "approve[s] safe prompts using AI verification". It criticises claude-squad's AutoYes for bypassing "Claude Code's built-in security". — [README](https://github.com/kbwo/ccmanager). MIT. npm first published 2025-06-09 (159 versions); 4.4.4 published 2026-09-27 — [npm](https://registry.npmjs.org/ccmanager). Stars 1.1k (list, ~2026-06-14) — [jq list](https://github.com/jqueryscript/awesome-claude-code)
- **uzi** (devflowinc/uzi): uses worktrees and tmux; "uzi auto automatically presses Enter to confirm all tool calls" — [README](https://github.com/devflowinc/uzi). MIT. v0.0.1 tagged 2025-06-02. LC 2025-06-04 — [Go proxy](https://proxy.golang.org/github.com/devflowinc/uzi/@v/main.info)
- **Crystal → Nimbalyst** (stravu/crystal): "Crystal … has been deprecated and replaced by Nimbalyst. Deprecated: February 2026." — [README](https://github.com/stravu/crystal). LC 2026-02-26. Stars 3.1k (list, ~2026-06-14) — [jq list](https://github.com/jqueryscript/awesome-claude-code). **Nimbalyst** (nimbalyst/nimbalyst) is a desktop workspace with parallel sessions "each isolated in its own git worktree" and "Visual diff review … tap to approve". "The collaboration sync server (talked to at `wss://sync.nimbalyst.com`) is a separate project." MIT. LC 2026-09-30 — [README](https://github.com/nimbalyst/nimbalyst), [Go proxy](https://proxy.golang.org/github.com/nimbalyst/nimbalyst/@v/main.info)
- **container-use** (dagger/container-use): an MCP server and CLI in which "Each agent gets a fresh container in its own git branch". It works with Claude Code, Cursor, Goose and other MCP clients. — [README](https://github.com/dagger/container-use). Apache-2.0. First tag 2025-06-09. LC 2026-08-12 — [Go proxy](https://proxy.golang.org/github.com/dagger/container-use/@v/main.info)
- **HelmMate** (ShaoXiangChien/helmmate): a "local launch console" that turns product asks into agent tickets for Claude Code, Codex and opencode, with worktree-aware runs. "Finished work stops at human review. Pull requests are handoffs, not automatic approvals." It has "No required database … and no auto-merge path". The roadmap includes "clearer dangerous-permission visibility". — [README](https://github.com/ShaoXiangChien/helmmate). MIT. LC 2026-06-05 — [Go proxy](https://proxy.golang.org/github.com/!shao!xiang!chien/helmmate/@v/main.info). The README says `npx helmmate`, but no npm package of that name exists (registry 404) — [npm](https://registry.npmjs.org/helmmate)
- **baton** (mraza007/baton): polls GitHub Issues, creates worktrees and runs Claude Code "hands-free". It was "Inspired by OpenAI's Symphony spec", and its default `permission_mode` is `acceptEdits` — [README](https://github.com/mraza007/baton). MIT. LC 2026-03-27 — [Go proxy](https://proxy.golang.org/github.com/mraza007/baton/@v/main.info)
- **Multi-Agent Observability** (disler/claude-code-hooks-multi-agent-observability): sends Claude Code hook events (PreToolUse, PostToolUse, PermissionRequest, Notification, SessionEnd …) to a local server and web UI, and supports Claude Code Agent Teams through `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` — [README](https://github.com/disler/claude-code-hooks-multi-agent-observability). No LICENSE file was found under standard names. LC 2026-02-08 — [Go proxy](https://proxy.golang.org/github.com/disler/claude-code-hooks-multi-agent-observability/@v/main.info). Stars 1.5k (list, ~2026-06-14) — [jq list](https://github.com/jqueryscript/awesome-claude-code)

#### F. Adjacent or deprecated
- **wshobson/agents** is a content library, not a coordinator: an "Agentic Plugin Marketplace: 94 plugins, 202 agents, 184 skills, 105 commands — built for Claude Code and consumed natively by OpenAI Codex CLI, Cursor, OpenCode, the Antigravity CLI, GitHub Copilot, and Pi" — [README](https://github.com/wshobson/agents). MIT. LC 2026-09-29 — [Go proxy](https://proxy.golang.org/github.com/wshobson/agents/@v/main.info). Stars 24,171 on 2026-01-03 — [Ranking 01-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-01-03.csv); 36.7k (list, ~2026-06-14) — [jq list](https://github.com/jqueryscript/awesome-claude-code)
- **HumanLayer** (humanlayer/humanlayer), formerly an open-source human-in-the-loop approval SDK: its README now says "the code here is pretty much all deprecated - you can try the rebuild of humanlayer at https://humanlayer.com" — [README](https://github.com/humanlayer/humanlayer). The last npm publish was 2025-11-25 — [npm](https://registry.npmjs.org/humanlayer)

#### G. Other relevant names from AAO (one-liners, not verified individually)
- These come from [AAO](https://github.com/andyrewlee/awesome-agent-orchestrators):
  - **Multi-human or shared-workspace tools:** "qm … Multiplayer harness where each teammate gets an isolated workspace"; "centaur (paradigmxyz) — Multiplayer self-hosted agents with Slack-native conversations"; "Traycer — … agent-to-agent messaging, shareable boards, and cross-device sync"; "Podium ADE — A shared task system"; "5dive — Named agents on a shared org chart and backlog hand work to each other and escalate to a human over Telegram"; "shire — Persistent team workspaces with inter-agent mailboxes"; "ai-maestro — Dashboard spanning multiple machines … agent-to-agent messaging"; "ClawTeam (HKUDS) — … file-based or P2P inboxes across tmux worktrees".
  - **Coordination protocols and locking:** "NXTG-Forge — … file locking"; "NEEDLE — shared bead queue (SQLite, atomic claims)"; "wit — Locks individual functions rather than files via Tree-sitter" (Resting).
  - **Approval and permission inboxes:** "octomux — one unified permission inbox across agents"; "Calyx — approval inbox for permission prompts"; "Garcon — mobile approvals, … cross-agent transfers"; "Fletch — gates every step on tests or your approval"; "Taskuary — … approval-gate[d] runs"; "Archon (coleam00) — … validation gates, approvals, and isolated git worktrees".
  - **Other:** "openkanban (TechDufus) — Kanban board … in the terminal" (AGPL, LC 2026-06-12 per [Go proxy](https://proxy.golang.org/github.com/!tech!dufus/openkanban/@v/main.info)); "scion (GoogleCloudPlatform) — … parallel isolated containers with dynamic coordination".

### Inferences
- No examined project combines all of Longtable's pieces. Those pieces are: a shared board for 2–5 humans; Claude Code and Codex hooks that auto-report progress from each person's own interactive sessions; agents barred from commitment actions, with human confirmation; and a human "accept" gate before someone else's text reaches your agent.
- The closest analogs each cover one slice:
  - **Multica** has the board, blockers, review gates, roles and an agent daemon.
  - **Paperclip** has approval gates, "Ask first" actions, blocker dependencies and comments.
  - **Agor** has multiplayer, RBAC and per-user credentials.
  - **Concord MCP** requires the recipient to accept before ownership changes hands.
  - **AMP** defines trust labels and wraps external content.
  - **qm** screens content and quarantines it pending release approval.
  - **batonpass** and **abevz/dibs** use SessionStart hooks and frame injected text as "data, not instructions".
- Multica and Paperclip appear to dispatch agents through their own runtimes or heartbeats rather than by hooking into the session a human is already using interactively. This is inferred from the README language ("picks it up on its own", "wake on heartbeats"); the source code was not checked.
- Licensing is a real differentiator. Several prominent "open" options are source-available rather than OSI open source: Multica (Multica License), Agor (BUSL-1.1 until 2029-01-15), agent-kanban (FSL-1.1-ALv2), Taskmaster (Commons Clause) and MCP Agent Mail (MIT plus an "ADDITIONAL RIDER / RESTRICTION (OpenAI / Anthropic)", whose full text was not reviewed).

### Gaps
- **Blocked sources:** the GitHub REST API answered 403 "GitHub access to this repository is not enabled for this session" for every third-party repo, and github.com HTML was also 403. shields.io, ungh.cc, OSS Insight, ecosyste.ms, deps.dev, OpenSSF Scorecard, star-history, vibekanban.com and augmentcode.com were all blocked by the egress proxy. The session's WebSearch quota ran out after one query. Because of this, HN threads, author blogs (e.g. Steve Yegge on beads or Gas Town) and the Vibe Kanban shutdown post could not be read.
- **Stars:** not obtained for beads, Gas Town, MCP Agent Mail, Backlog.md, Taskmaster, Agor, Squad, Concord MCP, agent-kanban, AgentBridge, qm, ox, Cyrus, hcom, Cyclops, guild, foremerge, dibs (both), batonpass, RightSeat, HelmMate, container-use, uzi, Swarm Protocol, GNAP or kandev. The only bound available is that repos absent from the ranking are below their language's rank-100 cutoff (e.g. a Go repo is under 29,259 stars), which is a weak bound.
- **Contributor counts:** not obtained for any repo.
- **Creation dates:** exact repo creation dates are unknown; first-tag and first-publish dates are proxies.
- **Not checked:** source code was not inspected, so all security behaviour above is as claimed in READMEs and specs.
- **Unread papers:** arXiv items surfaced by the one search were not read: "AgentRoom: Concurrent Multi-Agent Coding in a CRDT-Backed Shared Workspace" ([arXiv 2608.23740](https://arxiv.org/pdf/2608.23740)), "AgentRadio: Passive Awareness for Long-Horizon Multi-Agent Collaboration" ([arXiv 2607.28430](https://arxiv.org/pdf/2607.28430)) and "Before the Pull Request: Mining Multi-Agent Coordination" ([arXiv 2606.19616](https://arxiv.org/pdf/2606.19616)).

## Q2. Which are built for several humans sharing state, and which for one developer running many agents?

### Takeaway
Team-level designs are a minority and usually need a server. Server-backed examples are Multica, Paperclip, Agor, qm, Buzz, Vibe Kanban Cloud and the hosted ox. Git- or Dolt-synced examples are beads, Gas Town, Backlog.md, ccpm, Squad and GNAP. Most CLI-native coordination tools explicitly limit themselves to one operator or one machine: MCP Agent Mail, Concord MCP, both dibs, foremerge, guild, hcom, Cyclops, claude-squad, ccmanager, batonpass and AgentBridge.

### Cited Findings
- **Explicitly multi-human:**
  - Multica: roles `owner`, `admin`, `member`; "Multica puts those agents and your teammates in one workspace" — [README](https://github.com/multica-ai/multica)
  - Paperclip: "human roles and permissions … company memberships, and invite flows" — [README](https://github.com/paperclipai/paperclip)
  - Agor: "turn on multiplayer and Unix-level isolation when you bring your team"; "live cursors, comments" — [README](https://github.com/preset-io/agor)
  - qm: "Each person and each room has its own scoped memory … permissions" — [README](https://github.com/yc-software/qm)
  - Buzz: "People and agents building together in the same room" — [README](https://github.com/block/buzz)
  - Vibe Kanban: "privately or with your team" — [README](https://github.com/BloopAI/vibe-kanban)
  - ox: "The hivemind for human-agent teams" — [README](https://github.com/sageox/ox)
  - ccpm: "multiple agents (or humans) work on the same project simultaneously" — [README](https://github.com/automazeio/ccpm)
  - Cyrus: "Pro & Team Plans" — [README](https://github.com/cyrusagents/cyrus)
- **Multi-human through git or Dolt:**
  - beads: cross-machine sync via `bd dolt push/pull`, and server mode for "multiple concurrent writers" — [README](https://github.com/steveyegge/beads)
  - Gas Town: per-person "Crew" workspaces, plus "Wasteland" federation between Gas Towns through DoltHub — [README](https://github.com/gastownhall/gastown)
  - Backlog.md: tasks are "legible to you, your team, and the next agent" — [README](https://github.com/MrLesk/Backlog.md)
  - Squad: team state committed in `.squad/` — [README](https://github.com/bradygaster/squad)
  - polymatx/dibs: lessons only, shared via `git pull` — [README](https://github.com/polymatx/dibs)
- **Explicitly single-operator or single-machine:**
  - abevz/dibs: "runs on one machine and does not sync leases across machines" — [README](https://github.com/abevz/dibs)
  - polymatx/dibs: "Machine-local coordination" — [README](https://github.com/polymatx/dibs)
  - foremerge: "The MVP does not replicate SQLite across machines" — [README](https://github.com/naw103/foremerge)
  - guild: "State lives strictly on local host" — [README](https://github.com/mathomhaus/guild)
  - hcom: "one trust domain for one operator's devices" — [README](https://github.com/aannoo/hcom)
  - Concord MCP: "local-first … **Not** … hosted sync service" — [README](https://github.com/Get-Concord-AI/concord-mcp)
  - batonpass: "Transcripts never leave your machine" — [README](https://github.com/solsebb/batonpass)
- **Intra-session coordination** (Anthropic's built-in, closed source): Swarm Protocol's README describes "Claude Code Agent Teams" as coordinating "agents within a single session — one lead, parallel teammates, shared task list. Intra-session." — [README](https://github.com/phuryn/swarm-protocol)
- **Cross-org federation claims:** Ruflo describes federated agents as "Remote agents start untrusted" — [README](https://github.com/ruvnet/ruflo). Gas Town's Wasteland describes "portable reputation" across towns — [README](https://github.com/gastownhall/gastown)

### Inferences
- The "2–5 humans, each with their own Claude Code or Codex" niche falls between two groups. CLI-native tools assume one operator. Team platforms either run the agents themselves (Multica's daemon, Paperclip's heartbeats, Agor's browser sessions, Cyrus and Symphony picking up tickets) or live in Slack or the web (qm, Buzz). None of the team platforms advertises hook-based reporting from the agent sessions people already use.
- ox is the clearest precedent for "inject team context at session start and record sessions" across a team. It is hosted only ("no self-hosted or local-only ledger"), which may matter for China plus US teams; that is an inference, since network and data-residency questions were not researched.

### Gaps
- Real-world use by multiple humans (user counts, case studies) could not be verified because search was unavailable. Only Gas Town's README mentions a production team, and only indirectly; GNAP says it "coordinates the AI team at Farol Labs — 4 agents" — [README](https://github.com/farol-team/gnap).

## Q3. How do they store and sync state, and how do they handle concurrent edits and conflicts?

### Takeaway
Storage ranges from plain files committed to the repo (Backlog.md, Squad, GNAP, dibs lessons), to local SQLite behind a daemon or MCP server (batonpass, abevz/dibs, hcom, guild, foremerge, Agent Mail's index), to Dolt for versioned SQL with push and pull (beads, Gas Town), to server databases (Postgres in qm and Swarm Protocol; the Paperclip, Multica and Agor servers), to a signed Nostr event log (Buzz). Conflicts are handled in three ways:
- **Avoid them** through worktree or container isolation.
- **Serialize them** through leases, atomic claims, optimistic versions or execution locks.
- **Detect or merge them** through deterministic intent-collision checks, hash IDs with Dolt cell-level merge, or a Bors-style merge queue.

### Cited Findings
- **Files in the repo:**
  - Backlog.md: "tasks are plain files in your repo, and remote Git operations are optional" — [README](https://github.com/MrLesk/Backlog.md)
  - GNAP: "Four JSON files"; "Git history IS the audit log" — [README](https://github.com/farol-team/gnap)
  - polymatx/dibs: lessons stored as markdown under `.dibs/lessons/` — [README](https://github.com/polymatx/dibs)
  - Squad: `.squad/` team state — [README](https://github.com/bradygaster/squad)
- **Uncommitted state in the git common dir:** polymatx/dibs claims are JSON files "visible to all worktrees immediately, without commits, and never appears in `git status`". "Conflict checks run under an advisory lock; expiry is evaluated lazily at read time." — [README](https://github.com/polymatx/dibs)
- **Local SQLite:**
  - batonpass: `~/.baton/baton.db` — [README](https://github.com/solsebb/batonpass)
  - abevz/dibs: a daemon as "single writer to a local SQLite database", reached over HTTP on a Unix socket — [README](https://github.com/abevz/dibs)
  - hcom: "Hooks record activity to a local SQLite database" — [README](https://github.com/aannoo/hcom)
  - guild: "embedded SQLite" — [README](https://github.com/mathomhaus/guild)
  - foremerge: "SQLite store, deterministic conflict detector" — [README](https://github.com/naw103/foremerge)
  - MCP Agent Mail: "Git (for human-auditable artifacts) and SQLite (for indexing and queries)" — [README](https://github.com/Dicklesworthstone/mcp_agent_mail)
- **Dolt:** beads uses embedded Dolt as a single writer or a `dolt sql-server` for concurrent writers, syncs through `refs/dolt/data` on the git remote, and offers "cell-level merge". It says the JSONL file is "not the source of truth" — [README](https://github.com/steveyegge/beads). Gas Town's Wasteland federates "through DoltHub" — [README](https://github.com/gastownhall/gastown)
- **Server databases:**
  - qm: Postgres via `DATABASE_URL`/`SESSION_STORE=postgres` — [README](https://github.com/yc-software/qm)
  - Swarm Protocol: "Single PostgreSQL instance" — [README](https://github.com/phuryn/swarm-protocol)
  - Paperclip: "Node.js server and React UI" — [README](https://github.com/paperclipai/paperclip)
  - Multica: self-host with "Docker Compose or Helm" — [README](https://github.com/multica-ai/multica)
  - Nimbalyst: a separate collaboration sync server at `wss://sync.nimbalyst.com` — [README](https://github.com/nimbalyst/nimbalyst)
  - ox: hosted SageOx ledger — [README](https://github.com/sageox/ox)
- **Signed event log:** in Buzz, "every message, reaction, workflow step, review approval, and git event is a signed event in one log" — [README](https://github.com/block/buzz)
- **Issue trackers as the database:**
  - ccpm: "Issue state is project state" — [README](https://github.com/automazeio/ccpm)
  - abevz/dibs: imports and publishes GitHub issues — [README](https://github.com/abevz/dibs)
  - Cyrus: Linear, GitHub, GitLab and Slack issues — [README](https://github.com/cyrusagents/cyrus)
  - Symphony: watches a Linear board — [README](https://github.com/openai/symphony)
  - baton: GitHub Issues — [README](https://github.com/mraza007/baton)
- **Concurrency mechanisms:**
  - **Leases with TTL:**
    - polymatx/dibs: default 30m, maximum 24h; "Leases, not locks" — [README](https://github.com/polymatx/dibs)
    - abevz/dibs: the lease expires if the worker disappears — [README](https://github.com/abevz/dibs)
    - MCP Agent Mail: advisory file reservations, `FILE_RESERVATION_CONFLICT` — [README](https://github.com/Dicklesworthstone/mcp_agent_mail)
  - **Atomic claims:**
    - beads: `bd update --claim` — [README](https://github.com/steveyegge/beads)
    - guild: "Atomic claims, no collisions" — [README](https://github.com/mathomhaus/guild)
  - **Optimistic versioning:** Concord MCP uses `expected_version`, so only the first transition succeeds — [README](https://github.com/Get-Concord-AI/concord-mcp)
  - **Execution locks:** Paperclip offers "Atomic task checkout" — [README](https://github.com/paperclipai/paperclip)
  - **Merge queue:** Gas Town's Refinery is a "Bors-style bisecting queue" — [README](https://github.com/gastownhall/gastown)
  - **Intent-collision detection before writing:** foremerge — [README](https://github.com/naw103/foremerge)
  - **Isolation by worktree or container:**
    - claude-squad — [README](https://github.com/smtg-ai/claude-squad)
    - container-use — [README](https://github.com/dagger/container-use)
    - Agor — [README](https://github.com/preset-io/agor)
    - Vibe Kanban — [README](https://github.com/BloopAI/vibe-kanban)
  - **Hash IDs to avoid ID collisions across branches:** beads — [README](https://github.com/steveyegge/beads)

### Inferences
- For a shared board across machines and countries, the open-source landscape offers either a central server (Paperclip, Multica, Agor, qm) or git- or Dolt-mediated sync (beads, Backlog.md). The single-machine lease tools are good references for claim semantics (TTL, heartbeats, handoff on failure, STALE lanes) but do not solve cross-machine state.
- beads' move to Dolt, with JSONL demoted to "an export", suggests that plain JSONL in git caused merge pain for multiple writers. This is inferred from the README wording; the migration rationale was not read.

### Gaps
- No examined README documents how its server-based board resolves simultaneous human edits to the same task (e.g. last-write-wins versus CRDT). Paperclip and Multica do not describe it in their READMEs. The CRDT approach exists only in an unread arXiv paper (AgentRoom).

## Q4. Do any implement human approval gates, trust labels on text written by other agents, or other prompt-injection defenses?

### Takeaway
Human gates on merges and PRs are common: Multica, Paperclip, agent-kanban, HelmMate, Squad, kandev and Nimbalyst all have them. Explicit defenses against prompt injection between agents or people are rare. The strongest examples are:
- **AMP's spec**: verified, external and untrusted trust levels, mandatory `<external-content>` wrapping, and `injection_flags`.
- **qm's content screening**: in enforce mode it quarantines flagged content pending release approval.
- **"Data, not instructions" framing** in abevz/dibs and batonpass.

hcom openly lists injection from authenticated peers as unprotected. MCP Agent Mail's Human Overseer does the opposite of a gate: it injects a preamble telling agents to prioritise the human's message. None of the 46 READMEs mention passkeys, WebAuthn or FIDO. Several tools bypass permission prompts by default.

### Cited Findings
- **Trust labels and injection defense:**
  - AMP: "Trust annotations — External messages marked for prompt injection defense" — [README](https://github.com/agentmessaging/protocol). External messages "MUST wrap with `<external-content>` tags", and untrusted means "Unverified, missing signature, or anomalous" — [spec/07-security.md](https://github.com/agentmessaging/protocol/blob/main/spec/07-security.md). Messages carry `trust_level` and `injection_flags` — [spec/04-messages.md](https://github.com/agentmessaging/protocol/blob/main/spec/04-messages.md)
  - qm: "`enforce` quarantines flagged content pending release approval", but screening is `off` by default — [README](https://github.com/yc-software/qm)
  - Ruflo: "Remote agents start untrusted … Per-trust-level policies: BLOCK, REDACT, HASH, or PASS" — [README](https://github.com/ruvnet/ruflo)
  - abevz/dibs: "Imported titles and bodies are task data, not instructions for the agent" — [README](https://github.com/abevz/dibs)
  - batonpass: "The brief is framed as prior context, not instructions" — [README](https://github.com/solsebb/batonpass)
  - Cyclops: protects a human's half-written input from agent keystrokes. Raw `tmux send-keys` "types over whatever a human has half-written in the composer. Cyclops adds the missing boundaries", and AAO calls this "fail-closed human-composer protection". This guards human input, not message content. — [README](https://github.com/cyclops-team/cyclops), [AAO](https://github.com/andyrewlee/awesome-agent-orchestrators)
- **Explicit non-defenses:**
  - hcom: "Prompt injection from an authenticated peer. Enrollment is total trust" — [README](https://github.com/aannoo/hcom)
  - polymatx/dibs: "not a security boundary"; hooks "fail open" — [README](https://github.com/polymatx/dibs)
  - foremerge: "Foremerge does not sandbox them" — [README](https://github.com/naw103/foremerge)
  - MCP Agent Mail: the Overseer preamble tells agents to "Pause current work … Prioritize the human's request" — [README](https://github.com/Dicklesworthstone/mcp_agent_mail)
- **Acceptance before transfer:** Concord MCP keeps an assignment in `assigned` "until the named agent uses `transfer_work` with `action: "accept"`" — [README](https://github.com/Get-Concord-AI/concord-mcp)
- **Human approval gates:**
  - Paperclip: "Approval gates are enforced"; connector actions "Allowed, Ask first, or Off" — [README](https://github.com/paperclipai/paperclip)
  - qm Strict: "every harness tool call pauses for human approval"; the command policy has "hard denials for things like recursive deletes or destructive SQL" — [README](https://github.com/yc-software/qm)
  - Multica: "Work lands in review, not in main" — [README](https://github.com/multica-ai/multica)
  - agent-kanban: "Human review gates" — [README](https://github.com/saltbo/agent-kanban)
  - HelmMate: "Pull requests are handoffs, not automatic approvals" — [README](https://github.com/ShaoXiangChien/helmmate)
  - Squad: "Human review and merge are always required" in gh-aw mode — [README](https://github.com/bradygaster/squad)
  - kandev: human gates between steps — [AAO](https://github.com/andyrewlee/awesome-agent-orchestrators)
  - Backlog.md: prompt-level "Wait for my approval before coding" — [README](https://github.com/MrLesk/Backlog.md)
- **Identity and signing:**
  - Buzz: agents have "their own keys" and events are signed — [README](https://github.com/block/buzz)
  - agent-kanban: "signed binding" — [README](https://github.com/saltbo/agent-kanban)
  - AMP: Ed25519 — [README](https://github.com/agentmessaging/protocol)
  - Ruflo: "mTLS + ed25519 challenge-response" — [README](https://github.com/ruvnet/ruflo)
  - Paperclip: "short-lived run JWTs" — [README](https://github.com/paperclipai/paperclip)
- **Secrets:**
  - batonpass: "Everything stored passes a secret redactor first" — [README](https://github.com/solsebb/batonpass)
  - ox: "Secrets are stripped locally before anything uploads" — [README](https://github.com/sageox/ox)
  - Paperclip: "secret scrubbing" on template export — [README](https://github.com/paperclipai/paperclip)
  - kandev: "redacted task conversation snapshots" — [README](https://github.com/kdlbs/kandev)
  - Squad SDK: "PII scrubbing" — [README](https://github.com/bradygaster/squad)
  - Agor: "per-user credentials and env vars" — [README](https://github.com/preset-io/agor)
  - abevz/dibs: "stores no GitHub token" — [README](https://github.com/abevz/dibs)
- **Default permission bypass (weaknesses):**
  - AgentBridge: `--dangerously-skip-permissions` and `--yolo` by default — [README](https://github.com/raysonmeng/agent-bridge)
  - Squad: recommends `--yolo` — [README](https://github.com/bradygaster/squad)
  - claude-squad: "yolo / auto-accept mode" — [README](https://github.com/smtg-ai/claude-squad)
  - uzi: "automatically presses Enter to confirm all tool calls" — [README](https://github.com/devflowinc/uzi)
  - Gas Town: Copilot preset uses `--yolo` — [README](https://github.com/gastownhall/gastown)
  - ccmanager: experimental AI "Auto Approval" — [README](https://github.com/kbwo/ccmanager)
  - qm: a "Dangerous" posture is available — [README](https://github.com/yc-software/qm)
- **Passkeys:** a case-insensitive search for "passkey", "webauthn", "fido" and "yubikey" across every README fetched for this inventory (the repos linked in Q1) found no matches. This is a negative result from this research's own scan.

### Inferences
- Requiring a human to accept another person's or agent's text before it reaches their own agent appears to be unique among the examined projects. AMP has the closest standard, but it labels and wraps text automatically rather than asking a human; Concord MCP gates on acceptance, but for ownership transfer, not content.
- Passkey-confirmed commitment actions were not found anywhere. Paperclip's "Ask first" and qm's Strict posture are the nearest equivalents, and both use ordinary in-app approval.
- Defaulting to permission bypass is widespread among single-developer tools. That is a security contrast Longtable could state explicitly.

### Gaps
- The security claims (AMP, qm, Ruflo, Paperclip) were not validated against source code or audits. The Ruflo claims in particular were not independently verified.

## Q5. Which are growing fastest, and which are abandoned?

### Takeaway
Star growth is concentrated in team-scale "agents at work" platforms. Paperclip gained +16,475 stars from 2026-09-03 to 2026-10-03. Over the same month, Ruflo gained +3,472, Buzz +3,426 and Multica +3,202, while Symphony slowed to +505 and Vibe Kanban to +254 (Vibe Kanban is sunsetting). Several earlier single-developer or task-manager tools are dormant or deprecated: uzi has had no commits since 2025-06, Crystal was deprecated in 2026-02, Taskmaster has been idle since 2026-04, ccpm, Swarm Protocol and GNAP since 2026-03, and HumanLayer's code is deprecated.

### Cited Findings
- **Star series:**

  | Repo | Earlier snapshots | 2026-09-03 | 2026-10-03 |
  |---|---|---|---|
  | Paperclip | 45,260 (04-03), 72,597 (07-03) | 79,897 | 96,372 |
  | Ruflo | 62,688 (07-03) | 70,274 | 73,746 |
  | Multica | 38,884 (07-03) | 48,659 | 51,861 |
  | Buzz | — | 32,000 | 35,426 |
  | Symphony | 14,477 (04-03), 25,749 (07-03) | 27,006 | 27,511 |
  | Vibe Kanban | 24,280 (04-03), 27,248 (07-03) | 27,995 | 28,249 |

  Sources: [04-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-04-03.csv), [07-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-07-03.csv), [09-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-09-03.csv), [10-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-10-03.csv)
- **Release cadence as an activity signal:**
  - paperclipai: 1,677 npm versions since 2026-03-03 — [npm](https://registry.npmjs.org/paperclipai)
  - claude-flow: 849 versions since 2025-06-10 — [npm](https://registry.npmjs.org/claude-flow)
  - backlog.md: 232 versions, latest 2026-09-24 — [npm](https://registry.npmjs.org/backlog.md)
  - Multica: 164 Go tags since 2026-01-15 — [Go proxy](https://proxy.golang.org/github.com/multica-ai/multica/@v/list)
  - beads: 134 tags since 2025-10-14 — [Go proxy](https://proxy.golang.org/github.com/steveyegge/beads/@v/list)
  - Buzz: 103 tags since 2026-06-12 — [Go proxy](https://proxy.golang.org/github.com/block/buzz/@v/list)
- **Active, with a commit within about 7 days of 2026-10-03:**
  - beads, Squad, Ruflo, Agor, qm, ox, Buzz, AMP, foremerge and kandev (all 2026-10-03)
  - abevz/dibs and Cyrus (2026-10-02); Multica (2026-10-02)
  - hcom (2026-10-01); Nimbalyst (2026-09-30)
  - MCP Agent Mail and wshobson/agents (2026-09-29); ccmanager (2026-09-27); batonpass (2026-09-26)

  Sources: the Go proxy `@v/main.info` links in Q1; Paperclip's last push of 2026-10-03 is from [Ranking](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-10-03.csv)
- **Slowing, idle or deprecated, with last commit dates:**
  - uzi: 2025-06-04 (about 16 months idle) — [Go proxy](https://proxy.golang.org/github.com/devflowinc/uzi/@v/main.info)
  - disler observability: 2026-02-08 — [Go proxy](https://proxy.golang.org/github.com/disler/claude-code-hooks-multi-agent-observability/@v/main.info)
  - Crystal: 2026-02-26, deprecated — [README](https://github.com/stravu/crystal)
  - Swarm Protocol: 2026-03-15 — [Go proxy](https://proxy.golang.org/github.com/phuryn/swarm-protocol/@v/main.info)
  - GNAP: 2026-03-17 — [Go proxy](https://proxy.golang.org/github.com/farol-team/gnap/@v/main.info)
  - ccpm: 2026-03-18 — [Go proxy](https://proxy.golang.org/github.com/automazeio/ccpm/@v/main.info)
  - baton: 2026-03-27 — [Go proxy](https://proxy.golang.org/github.com/mraza007/baton/@v/main.info)
  - Taskmaster: 2026-04-23; the 1.0.0-rc from February 2026 was never released as final — [npm](https://registry.npmjs.org/task-master-ai)
  - HelmMate: 2026-06-05 — [Go proxy](https://proxy.golang.org/github.com/!shao!xiang!chien/helmmate/@v/main.info)
  - HumanLayer: code deprecated — [README](https://github.com/humanlayer/humanlayer)
  - Gas Town: 2026-07-23 — [Go proxy](https://proxy.golang.org/github.com/gastownhall/gastown/@v/main.info)
  - container-use: 2026-08-12 — [Go proxy](https://proxy.golang.org/github.com/dagger/container-use/@v/main.info)
  - Vibe Kanban: "sunsetting"; one release on 2026-09-19 after a gap since 2026-04-24 — [README](https://github.com/BloopAI/vibe-kanban), [npm](https://registry.npmjs.org/vibe-kanban)
- **AAO "Resting" list (checked 2026-07-28):** 1code ("archived"), CodexMonitor, GNAP, Swarm Protocol, subtask, Vibe Kanban, wit, clawe, antfarm, opengoat, ralphy and wreckit — [AAO](https://github.com/andyrewlee/awesome-agent-orchestrators)
- **Very new projects in the coordination niche:**
  - Concord MCP (first npm 2026-07-17) — [npm](https://registry.npmjs.org/@concord-ai%2Fconcord-mcp)
  - polymatx/dibs (v0.1.0 2026-08-04) — [Go proxy](https://proxy.golang.org/github.com/polymatx/dibs/@v/list)
  - foremerge (crate 2026-08-25) — [crates.io](https://crates.io/api/v1/crates/foremerge)
  - Cyclops (2026-08-27) — [Go proxy](https://proxy.golang.org/github.com/cyclops-team/cyclops/@v/list)
  - abevz/dibs (rc.1 2026-09-25) — [Go proxy](https://proxy.golang.org/github.com/abevz/dibs/@v/list)
  - batonpass (v0.1.0 2026-09-26) — [Go proxy](https://proxy.golang.org/github.com/solsebb/batonpass/@v/list)

### Inferences
- Attention, measured in stars, has moved from single-developer "parallel session managers" (claude-squad at 7.8k and ccmanager at 1.1k as of about 2026-06-14) to team or company orchestration platforms (Paperclip, Multica, Buzz). That supports Longtable's team framing. It also means the large, well-funded players are server platforms that run agents rather than boards that sit beside each person's own CLI sessions.
- The coordination-primitive niche (claims, handoff, messaging over MCP and hooks) is crowded with small projects launched from July to September 2026. Lifespans are short: GNAP, Swarm Protocol and wit went idle within roughly 1–3 months of their spring 2026 activity.

### Gaps
- Star series are only available for repos in the per-language top 100. Growth for mid-size repos (beads, Gas Town, Agent Mail, Backlog.md, Agor, Squad) could not be measured.
- The date and reason for Vibe Kanban's sunset announcement could not be read (vibekanban.com is blocked). The npm gap from 2026-04-24 to 2026-09-16 suggests it came around April or May 2026, but that is unconfirmed.
