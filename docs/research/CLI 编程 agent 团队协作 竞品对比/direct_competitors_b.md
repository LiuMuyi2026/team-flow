# Direct competitors B: Block's Buzz, OpenAI's Symphony, YC's qm, Feishu Project's AAMP (state as of 2026-10-03)

Method and evidence labels. Everything here was gathered on 2026-10-03. Primary sources are the repositories' own files, fetched from raw.githubusercontent.com (README, SECURITY, SPEC, ARCHITECTURE, VISION, docs, CHANGELOG, package READMEs). Citations point to the equivalent github.com/blob URLs. Activity and dates come from the Go module proxy (proxy.golang.org `@v/list`, `@v/<tag>.info`, `@v/main.info`). For tags, the "Time" field is the tagged commit's time, not the moment the tag was created. Release dates come from the npm and PyPI registries. Star counts come from the daily EvanLi/Github-Ranking CSVs. These only list the top 100 repos per language, so a repo that is absent is below that language's cutoff on that day. Unreachable from this sandbox (proxy 403, or the CONNECT was rejected): api.github.com, meshmail.ai, engineering.block.xyz, openai.com, qbitai.com. GitHub API metadata such as creation date, exact stars for qm and AAMP, and release timestamps was therefore unavailable. Nothing here was run or tested. A **[doc]** label means the claim comes from the project's own documentation, which is not verified behaviour. **[registry]** and **[ranking]** mean machine data. **[prior notes]** means a number reused from open_source.md, startups_commercial.md or china_market.md in this folder.

## Q1. Buzz (block/buzz): what it is, how humans and agents collaborate, runtime, security model

### Takeaway
Buzz is Block's self-hostable, Slack-like team workspace (desktop app + Nostr relay). Humans and agents are equal members of channels, and every action is a signed event in one audited log. Agents are separate processes that Buzz's own harness (`buzz-acp`) or the desktop app spawns: Goose, Codex via codex-acp, Claude Code via claude-agent-acp, and more. They have their own keypairs and respond to @mentions. Buzz does not attach to the Claude Code or Codex sessions people already run. Its security rests on identity (signatures, channel membership as the only ACL, a per-agent "who may talk to me" author gate, and a hash-chained audit log), not on content screening or human approval. Workflow approval gates, an issue tracker and push notifications are not shipped yet.

### Cited Findings

#### Identity, licence, popularity, activity
- Owner: "Built by Block, Inc."; licence Apache 2.0 — [README](https://github.com/block/buzz/blob/main/README.md)
- Stars **[ranking]**, Rust category (description "A hive mind communication platform"):

  | Date | Stars | Forks | Open issues |
  |---|---|---|---|
  | 2026-08-03 | not listed (Rust cutoff 23,938) | | |
  | 2026-08-10 | 25,721 | 3,041 | |
  | 2026-08-17 | 27,774 | 3,458 | |
  | 2026-08-24 | 30,190 | 3,835 | |
  | 2026-09-03 | 32,000 | 4,127 | 1,442 |
  | 2026-10-03 | 35,426 | 4,665 | 1,632 |

  That is about +9,700 stars from 2026-08-10 to 2026-10-03, and +3,426 in September 2026 (the same September figure as in prior notes). Sources: [08-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-08-03.csv), [08-10](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-08-10.csv), [08-17](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-08-17.csv), [08-24](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-08-24.csv), [09-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-09-03.csv), [10-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-10-03.csv)
- Releases:
  - **Earliest tags:** the oldest tag commits are test tags. `v0.0.1-test.3` and `v0.0.1-test.4` date from 2026-05-03 and `v0.0.0-test.1` from 2026-06-12. This corrects the prior notes, which gave the first tag as 2026-06-12.
  - **Go-proxy-visible tags:** 103 in total. The last plain semver tag is `v0.5.2`, with commit time 2026-07-29 — [Go proxy list](https://proxy.golang.org/github.com/block/buzz/@v/list), [v0.5.2 info](https://proxy.golang.org/github.com/block/buzz/@v/v0.5.2.info)
  - **Later desktop releases:** these use `desktop-vX.Y.Z` tags, which the Go proxy cannot index. The CHANGELOG's newest entry is v0.5.26 ("Compare desktop-v0.5.25...desktop-v0.5.26"), followed by an [Unreleased] section. The CHANGELOG has no dates, and its PR numbers run past #7,900 — [CHANGELOG](https://github.com/block/buzz/blob/main/CHANGELOG.md)
  - **Release lanes:** there are three independent lanes. Desktop (signed and notarized macOS, unsigned Windows, Linux), relay (container image `ghcr.io/block/buzz`) and mobile release-candidate tags — [RELEASING.md](https://github.com/block/buzz/blob/main/RELEASING.md)
- Last commit 2026-10-03T09:06:05Z — [Go proxy main.info](https://proxy.golang.org/github.com/block/buzz/@v/main.info)

#### What it is
- "A workspace where humans and agents build together, on a relay you own." It is a Nostr relay: "every message, reaction, workflow step, review approval, and git event is a signed event in one log". The project also says plainly: "Not finished. We will tell you what works and what doesn't." — [README](https://github.com/block/buzz/blob/main/README.md)
- **Works today [doc]:**
  - relay, channels, threads, DMs, canvases, media, search, audit log
  - Tauri + React desktop app
  - `buzz-cli` ("agent-first, JSON in / JSON out") and an ACP harness for Goose, Codex and Claude Code
  - YAML workflows (message, reaction, schedule and webhook triggers)
  - git events (NIP-34) and a git hosting backend
- **Being wired up:** mobile clients, workflow approval gates and huddle lifecycle events.
- **Planned, no code yet:** web-of-trust reputation and push notifications.
- Source for the three lists above — [README](https://github.com/block/buzz/blob/main/README.md)
- **Surfaces:** Home, Stream (Slack-like), Forum, DMs ("1:1 and group. Up to 9"), Agents ("Directory. Your agents. Job board."), Workflows and Search. Notifications default to zero: Stream and Forum are "Zero", DMs "URGENT only", Workflows "Approvals only". The design rule is "You opt in to noise, not out" — [VISION.md](https://github.com/block/buzz/blob/main/VISION.md)
- **"Branch as room":** opening a feature branch creates a channel where "patches, CI, review, and the merge decision live together" — [README](https://github.com/block/buzz/blob/main/README.md)
- **Forge layer status:** most of it is still at the design stage. These are 📋 Designed: "NIP-34 issues (kind:1621)" (where "Labels, assignees, milestones are nostr tags"), the merge coordinator, project binding and multi-repo projects. Approval gates are 🚧. Git hosting ✅ "ships today" — [VISION_PROJECTS.md](https://github.com/block/buzz/blob/main/VISION_PROJECTS.md)

#### Agent execution model (spawns agents; does not attach to existing sessions)
- **`buzz-acp` harness:**
  - It "listens for @mentions on the relay, prompts your agent, and the agent replies using the Buzz CLI".
  - It "spawns AI agent subprocesses (1–32, default 1)" and batches queued @mentions per channel into one ACP `session/prompt`. At most one prompt is in flight per channel, and crashed agents are respawned.
  - On startup it "replays all unprocessed @mentions since the last run".
  - Sources: [buzz-acp README](https://github.com/block/buzz/blob/main/crates/buzz-acp/README.md), [ARCHITECTURE.md](https://github.com/block/buzz/blob/main/ARCHITECTURE.md)
- **Supported agents:**
  - Goose (the default `BUZZ_ACP_AGENT_COMMAND`).
  - Codex via `@agentclientprotocol/codex-acp`, with `OPENAI_API_KEY` "required — use an OpenAI API key, not a ChatGPT subscription".
  - Claude Code via `@agentclientprotocol/claude-agent-acp` ("wraps the Claude Agent SDK"), with `ANTHROPIC_API_KEY`.
  - Source: [buzz-acp README](https://github.com/block/buzz/blob/main/crates/buzz-acp/README.md)
- **Desktop "managed agents":**
  - Tier-1 compiled-in runtimes are Goose, Claude Code, Codex and Buzz Agent, each with "auto-installers, auth probes, and first-class onboarding".
  - Tier-2 presets are Cursor, Oh My Pi, Pi, Grok Build, OpenCode, Kimi Code, Amp, Hermes Agent and OpenClaw.
  - "Bring Your Own Harness" accepts any ACP agent.
  - Source: [buzz-acp README](https://github.com/block/buzz/blob/main/crates/buzz-acp/README.md)
- **Buzz's own agent:** `buzz-agent` is an ACP agent supporting "up to 8 concurrent sessions". `buzz-dev-mcp` gives any agent "a shell and a file editor". "The shell runs at the operator's trust level, like bash itself." — [VISION_AGENT.md](https://github.com/block/buzz/blob/main/VISION_AGENT.md)
- **Remote agents:** deployment to remote infrastructure ("Kubernetes first") is 📋 "spec in review" — [VISION.md](https://github.com/block/buzz/blob/main/VISION.md)
- **Agent identity:** "Each agent needs a Nostr keypair". An operator registers it as a relay member with `buzz-admin add-member`, and `buzz-cli` authenticates with `BUZZ_PRIVATE_KEY` — [buzz-acp README](https://github.com/block/buzz/blob/main/crates/buzz-acp/README.md), [buzz-cli README](https://github.com/block/buzz/blob/main/crates/buzz-cli/README.md)
- **MCP surface: the docs disagree.**
  - VISION.md lists "✅ MCP server — full feature surface" and says agents read the Home feed "via MCP".
  - The crate map lists only `buzz-dev-mcp` (shell and file edit), and says `buzz-cli` "mirrors and extends the MCP surface".
  - Sources: [VISION.md](https://github.com/block/buzz/blob/main/VISION.md), [README](https://github.com/block/buzz/blob/main/README.md)

#### Multi-human features
- **Roles:** member roles are `Owner`, `Admin`, `Member`, `Guest` and `Bot`, with transactional role enforcement — [ARCHITECTURE.md](https://github.com/block/buzz/blob/main/ARCHITECTURE.md)
- **Agents as members:** "Agents are members, not bots. Add an agent to a channel the same way you add a person." — [README](https://github.com/block/buzz/blob/main/README.md)
- **Personas and teams:** "A persona bundles a model and a system prompt. A team is a named group of personas", shipped as desktop-managed built-in defaults — [VISION.md](https://github.com/block/buzz/blob/main/VISION.md)
- **Real-time state:** presence (kind 20001) and typing indicators that "Agents broadcast … too". There is also an agent activity feed, "the window into delegated work" — [ARCHITECTURE.md](https://github.com/block/buzz/blob/main/ARCHITECTURE.md), [VISION.md](https://github.com/block/buzz/blob/main/VISION.md)
- **Workflow approvals:** a workflow step `request_approval` names an approver (`from`) and has a default timeout of 24h. `buzz workflows approve --token <uuid> [--approved false --note …]` exists in the CLI. However, "runs that hit an approval gate are marked as failed (🚧 WF-08)" — [ARCHITECTURE.md](https://github.com/block/buzz/blob/main/ARCHITECTURE.md), [buzz-cli README](https://github.com/block/buzz/blob/main/crates/buzz-cli/README.md)
- **Merge approvals:** described as "Merges require the specified number of signed approval events (kind:46011) before the relay accepts the push" — [VISION_PROJECTS.md](https://github.com/block/buzz/blob/main/VISION_PROJECTS.md). Whether this is enforced today is unclear, because the same document marks the merge coordinator as "Designed".
- **Missing primitives:** no shipped task, assignee, claim, blocker or "ask for help" objects were found. Issues with assignees are 📋 Designed. The "Job board" and job kinds 43001–43006 ("Delegation trees") appear only in the vision documents — [VISION.md](https://github.com/block/buzz/blob/main/VISION.md), [VISION_PROJECTS.md](https://github.com/block/buzz/blob/main/VISION_PROJECTS.md)

#### Human-in-the-loop and security
- **Authentication:** NIP-42 challenge/response on every relay connection, and NIP-98 signed HTTP auth on REST — [SECURITY.md](https://github.com/block/buzz/blob/main/SECURITY.md)
- **Authorization:** "Channel membership is the **only** access control mechanism. There are no separate ACL lists or capability taxonomies." — [SECURITY.md](https://github.com/block/buzz/blob/main/SECURITY.md). The README frames agent scoping as "Scoped by identity, not by permission flags" — [README](https://github.com/block/buzz/blob/main/README.md)
- **Audit:** an "Append-only … tamper-evident audit log … SHA-256 hash chain. Because the chain is keyless, it is tamper-evident but not tamper-resistant … designed for SOX-grade compliance and eDiscovery" — [SECURITY.md](https://github.com/block/buzz/blob/main/SECURITY.md)
- **Secrets:** nsec keys for humans and every managed agent are stored in the OS keyring (macOS Keychain, Windows Credential Manager, Linux Secret Service), with a fallback to a `0o600` file. `BUZZ_PRIVATE_KEY` "always takes precedence … this is how harnessed agents and CI receive their identity" — [SECURITY.md](https://github.com/block/buzz/blob/main/SECURITY.md)
- **Inbound author gate (Buzz's provenance control):**
  - `--respond-to` takes `owner-only` (the default), `allowlist`, `anyone` or `nobody`.
  - "Events from disallowed authors are silently dropped" before reaching the agent.
  - Relay-signed workflow messages are attributed to their owner only after provenance is verified against the relay's NIP-11 `self` key.
  - Owner-only control commands are `!cancel`, `!rotate` and `!shutdown`.
  - Source: [buzz-acp README](https://github.com/block/buzz/blob/main/crates/buzz-acp/README.md)
- **Agents inherit owner rights:** via NIP-OA, "Add a maintainer, and all their authorized agents can push. Remove the maintainer, and all their agents lose access instantly" — [VISION_PROJECTS.md](https://github.com/block/buzz/blob/main/VISION_PROJECTS.md)
- **No sandbox:** the host launch-wrapper hook "does not enforce a sandbox or verify executable contents" — [buzz-acp README](https://github.com/block/buzz/blob/main/crates/buzz-acp/README.md)
- **No rate limiting:** "No Redis-backed rate limiter exists … rate limiting is not currently enforced" — [ARCHITECTURE.md](https://github.com/block/buzz/blob/main/ARCHITECTURE.md)
- **TLS:** "The relay itself does not enforce TLS"; it is terminated at a proxy — [SECURITY.md](https://github.com/block/buzz/blob/main/SECURITY.md)
- **Workflow inputs:** `call_webhook` has SSRF protection, and evalexpr conditions are sandboxed and time-bounded — [SECURITY.md](https://github.com/block/buzz/blob/main/SECURITY.md)
- **Prompt injection:** no content screening, quarantine or trust labels on message content were found in README, SECURITY, ARCHITECTURE or the ACP README.

#### Deployment, pricing, China reachability
- **Self-host for development:** Docker plus Hermit, with Postgres, Redis and S3/MinIO.
- **Self-host in production:** a single-node or VPS Compose bundle (`deploy/compose/`, with Postgres, Redis, MinIO and optional Caddy TLS).
- **Hosted options:** a one-click "Deploy on Railway". Block staff use an internal build "pre-wired to the Block relay and agent provider".
- **Desktop clients:** macOS, Linux and Windows. The Windows build is unsigned.
- Source for the four points above — [README](https://github.com/block/buzz/blob/main/README.md)
- **Multi-tenant hosting:** "A hosted operator can serve many communities behind many domains or subdomains" — [README](https://github.com/block/buzz/blob/main/README.md)
- **Scale target:** "10K humans + 50K agents" — [VISION.md](https://github.com/block/buzz/blob/main/VISION.md)
- **Pricing:** the software is free (Apache-2.0). No SaaS price list was found.
- **China reachability:** not tested. The relay URL is operator-chosen via `BUZZ_RELAY_URL` — [README](https://github.com/block/buzz/blob/main/README.md)

#### Integrations
- No GitHub, Linear, Jira, Slack or Feishu connectors appear in ARCHITECTURE.md. The only integration points are inbound workflow webhooks (`POST /hooks/{id}`, secret-authenticated) and outbound `call_webhook` — [ARCHITECTURE.md](https://github.com/block/buzz/blob/main/ARCHITECTURE.md)
- Buzz is itself the git host: smart-HTTP `git clone` and `git push` with NIP-34. "gitworkshop.dev renders it. ngit-cli works with it." — [VISION_PROJECTS.md](https://github.com/block/buzz/blob/main/VISION_PROJECTS.md)

#### Documented limitations
- **Approval gates:** "Approval gates not wired end-to-end" (WF-08) — [ARCHITECTURE.md](https://github.com/block/buzz/blob/main/ARCHITECTURE.md)
- **Stubbed workflow actions:** `send_dm` and `set_channel_topic` return NotImplemented (WF-07) — [ARCHITECTURE.md](https://github.com/block/buzz/blob/main/ARCHITECTURE.md)
- **Rate limiting:** not implemented — [ARCHITECTURE.md](https://github.com/block/buzz/blob/main/ARCHITECTURE.md)
- **Private channel membership:** "The relay doesn't yet have a REST/event API for managing channel members — this is a known gap" — [buzz-acp README](https://github.com/block/buzz/blob/main/crates/buzz-acp/README.md)
- **Codex login noise:** codex-acp "always attempts a ChatGPT WebSocket login first, which logs a `426 Upgrade Required` error" — [buzz-acp README](https://github.com/block/buzz/blob/main/crates/buzz-acp/README.md)
- **Maturity:** it is pre-1.0, with "no long-term support branches" — [SECURITY.md](https://github.com/block/buzz/blob/main/SECURITY.md)

### Inferences
- **Product category:** Buzz is a Slack-plus-forge replacement in which agents are channel members. It is not a task board. A team adopting it would move its chat, and eventually its git hosting, into Buzz.
- **No attach path:** nothing documents hooks into a person's running Claude Code or Codex session. An interactive session could in principle shell out to `buzz` CLI commands with an agent key, but that is undocumented and would not report progress automatically.
- **Cost model:** agents run on API keys. The Codex path explicitly needs an API key, not a ChatGPT subscription. Teams that work on Claude Max or ChatGPT subscriptions would pay twice, or would have to rely on desktop "auth probes", whose subscription support is unverified.
- **Trust model compared with Longtable:** Buzz's author gate filters by author (owner, allowlist or anyone), not by message. Once a teammate is on the allowlist, everything that teammate posts reaches the agent. Longtable's per-message "accept before it reaches my agent" is finer-grained.
- **Approval model:** Buzz has no passkey-style human confirmation for commitment actions. Signatures prove who acted; they do not gate what an agent may commit to.
- **Growth:** Buzz has the strongest momentum of the four (about +9.7k stars in roughly 8 weeks), and Block uses it internally. That makes it a credible "agents in the team chat" standard in the US. It is a weak fit for China+US teams that already live in WeChat or Feishu.

### Gaps
- **Public launch date:** unknown, because api.github.com and the Block engineering blog were blocked. Buzz was under 23,938 stars on 2026-08-03 and at 25,721 on 2026-08-10.
- **Release dates:** dates for desktop releases v0.5.3–v0.5.26 are unavailable, because the CHANGELOG has no dates and the GitHub releases API was blocked.
- **Desktop auth probes:** whether managed agents can reuse a local Claude Code or Codex subscription login was not verified.
- **Agent sandboxing:** whether managed agents run with any OS sandbox, or in which permission mode, was not verified.
- **Unread documents:** VISION_ACTIVITY.md and VISION_REMOTE_AGENTS.md were not read.

## Q2. Symphony (openai/symphony): what it is, how humans manage work, which agents, approvals, limits

### Takeaway
Symphony is OpenAI's spec plus Elixir reference implementation for a long-running daemon. It polls an issue tracker (Linear, GitHub Issues, Jira Cloud, Asana or GitLab), creates a workspace per issue, and runs **Codex app-server** there until the ticket reaches a handoff state such as "Human Review". Humans manage work entirely through tracker states, assignments and PR reviews. Symphony has no accounts, roles or UI of its own beyond an optional loopback dashboard. It supports only Codex. The default approval posture rejects approval requests, and the sample workflow runs with `approval_policy: never`. OpenAI calls it "a low-key engineering preview for testing in trusted environments" and recommends writing your own hardened version. Activity has slowed: the last commit was 2026-09-15, and only three tags exist.

### Cited Findings

#### Identity, licence, popularity, activity
- Owner: OpenAI (`openai/symphony`). Licence Apache-2.0. The spec status is "Draft v1 (language-agnostic)" — [README](https://github.com/openai/symphony/blob/main/README.md), [SPEC.md](https://github.com/openai/symphony/blob/main/SPEC.md)
- Stars and forks **[ranking]**, Elixir category:

  | Date | Stars | Forks |
  |---|---|---|
  | 2026-03-03 | not listed | |
  | 2026-03-05 | 1,749 | 109 |
  | 2026-03-07 | 7,818 | 508 |
  | 2026-03-09 | 9,720 | 681 |
  | 2026-03-11 | 10,869 | 801 |
  | 2026-03-13 | 12,020 | 916 |
  | 2026-03-17 | 13,064 | 1,020 |
  | 2026-04-03 | 14,477 [prior notes] | |
  | 2026-07-03 | 25,749 | 2,611 |
  | 2026-08-03 | 26,381 | 2,672 |
  | 2026-09-03 | 27,006 | 2,777 |
  | 2026-10-03 | 27,511 | 2,853 |

  The ranking lists 0 open issues. Sources: [03-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-03-03.csv), [03-05](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-03-05.csv), [03-17](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-03-17.csv), [07-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-07-03.csv), [09-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-09-03.csv), [10-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-10-03.csv)
- **Public launch:** about 2026-03-04, since the repo is absent from the 03-03 ranking and has 1,749 stars on 03-05.
- **Tags:** v0.0.1 (2026-07-18), v0.0.2 (2026-07-24) and v0.0.3 (2026-09-15) — [Go proxy list](https://proxy.golang.org/github.com/openai/symphony/@v/list)
- **Last commit:** 2026-09-15T22:12:07Z — [Go proxy main.info](https://proxy.golang.org/github.com/openai/symphony/@v/main.info)
- **Nightly builds:** a rolling `nightly` prerelease is built from each push to main — [elixir/README](https://github.com/openai/symphony/blob/main/elixir/README.md)

#### What it is and how it runs agents (spawns Codex; does not attach)
- **Positioning:** "Symphony turns project work into isolated, autonomous implementation runs, allowing teams to manage work instead of supervising coding agents." In the demo, it "monitors a Linear board for work and spawns agents … provide proof of work: CI status, PR review feedback, complexity analysis, and walkthrough videos. When accepted, the agents land the PR safely." — [README](https://github.com/openai/symphony/blob/main/README.md)
- **Two install paths:** "Make your own" (tell a coding agent to implement SPEC.md in any language), or use the "experimental reference implementation" in Elixir — [README](https://github.com/openai/symphony/blob/main/README.md)
- **Loop:** poll the tracker, create a workspace per issue, launch "Codex in App Server mode inside the workspace", send the workflow prompt, and "Keep Codex working on the issue until the work is done" — [elixir/README](https://github.com/openai/symphony/blob/main/elixir/README.md)
- **Agent support:** the only agent dependency is a "Coding-agent executable that supports the targeted Codex app-server mode". Claude Code is not supported by the spec or the reference implementation — [SPEC.md](https://github.com/openai/symphony/blob/main/SPEC.md)
- **Configuration:** a repo-owned `WORKFLOW.md` (YAML front matter plus a Liquid-style prompt), hot-reloaded on change.
  - `agent.max_concurrent_agents` (10 in the example).
  - `agent.max_turns` (default 20).
  - Workspace bootstrap via the `hooks.after_create` shell (for example `git clone`).
  - Source: [elixir/README](https://github.com/openai/symphony/blob/main/elixir/README.md)
- **Remote workers:** an optional SSH worker extension runs Codex app-server on remote hosts over SSH stdio, with the orchestrator as "the single source of truth for polling, claims, retries" — [SPEC.md Appendix A](https://github.com/openai/symphony/blob/main/SPEC.md)
- **State:** "Support tracker/filesystem-driven restart recovery without requiring a persistent database; exact in-memory scheduler state is not restored" — [SPEC.md](https://github.com/openai/symphony/blob/main/SPEC.md)
- **Prerequisites:** Symphony "works best in codebases that have adopted harness engineering" — [README](https://github.com/openai/symphony/blob/main/README.md)
- **Codex auth:** the live end-to-end test "mounts the host `~/.codex/auth.json` into each worker", so normal Codex CLI auth is reused — [elixir/README](https://github.com/openai/symphony/blob/main/elixir/README.md)

#### How humans manage work (multi-human features live in the tracker)
- **Out of scope:** a "Rich web UI or multi-tenant control plane" is a non-goal — [SPEC.md](https://github.com/openai/symphony/blob/main/SPEC.md)
- **Tracker adapters:** Linear, GitHub Issues, Jira Cloud, Asana and GitLab. Each exposes a provider-native tool to Codex (`linear_graphql`, `github_api`, `jira_rest`, `asana_api`, `gitlab_api`), executed host-side — [elixir/README](https://github.com/openai/symphony/blob/main/elixir/README.md)
- **Assignment routing:** Linear `assignee` ("a Linear user ID or `me`") limits dispatch to issues assigned to that user — [elixir/README](https://github.com/openai/symphony/blob/main/elixir/README.md)
- **Blockers:** an issue is dispatchable only if "a `Todo` issue has no non-terminal blocker" (Linear inverse `blocks` relations; Jira inward `Blocks` links) — [elixir/README](https://github.com/openai/symphony/blob/main/elixir/README.md)
- **Review gate in the sample workflow:** it needs custom Linear states "Rework", "Human Review" and "Merging".
  - `Human Review` means the PR "is attached and validated; waiting on human approval".
  - `Merging` means "approved by human; execute the `land` skill flow (do not call `gh pr merge` directly)".
  - `Rework` means "reviewer requested changes".
  - Every actionable reviewer comment is treated "as blocking".
  - Progress is kept in "a single persistent Linear comment" (`## Codex Workpad`).
  - Sources: [elixir/README](https://github.com/openai/symphony/blob/main/elixir/README.md), [elixir/WORKFLOW.md](https://github.com/openai/symphony/blob/main/elixir/WORKFLOW.md)
- **Operator controls:** edit `WORKFLOW.md`, or change tracker state. A terminal state stops the agent and cleans the workspace; a non-active state stops it without cleanup — [SPEC.md §14.4](https://github.com/openai/symphony/blob/main/SPEC.md)
- **"Claimed" is internal:** it is orchestrator state (the "set of issue IDs reserved/running/retrying"), not a human claim — [SPEC.md](https://github.com/openai/symphony/blob/main/SPEC.md)
- **Real-time progress:** an optional Phoenix LiveView dashboard and JSON API (`/api/v1/state` and others). The spec says it "SHOULD bind loopback by default" and describes no auth — [SPEC.md §13.7](https://github.com/openai/symphony/blob/main/SPEC.md), [elixir/README](https://github.com/openai/symphony/blob/main/elixir/README.md)
- **Notifications:** Symphony has no channel of its own. Humans see Linear comments and state changes (inferred from the design above).

#### Human-in-the-loop and security
- **Approval posture is implementation-defined:** "Approval requests and user-input-required events MUST NOT leave a run stalled indefinitely". The example "high-trust behavior" is to "Auto-approve command execution approvals … Auto-approve file-change approvals … Treat user-input-required turns as hard failure" — [SPEC.md §10.5](https://github.com/openai/symphony/blob/main/SPEC.md)
- **Reference defaults:**
  - `codex.approval_policy` defaults to rejecting sandbox approvals, rules and MCP elicitations.
  - `thread_sandbox` defaults to `workspace-write`.
  - If Codex asks for operator input or approval, "Symphony keeps the issue claimed and exposes it as blocked … Blocked entries are in memory only; restarting the orchestrator clears that blocked map".
  - Source: [elixir/README](https://github.com/openai/symphony/blob/main/elixir/README.md)
- **The sample `WORKFLOW.md` is permissive:** `approval_policy: never`, `networkAccess: true`, `shell_environment_policy.inherit=all`, with model `gpt-5.5` at `xhigh` reasoning — [elixir/WORKFLOW.md](https://github.com/openai/symphony/blob/main/elixir/WORKFLOW.md)
- **Secrets:** tracker tokens are executed host-side and "removes declared tracker-token environment variables from the Codex child". However, "the tool can access whatever the configured Linear token can access", and `linear_graphql` "adds no idempotency key, retry, scope guard, or rate-limit policy" — [elixir/README](https://github.com/openai/symphony/blob/main/elixir/README.md)
- **Prompt injection:**
  - There is no screening. The spec says only that implementations "SHOULD NOT assume that tracker data, repository contents, prompt inputs, or tool arguments are fully trustworthy".
  - It suggests filtering eligible issues and labels (e.g. `tracker.required_labels`), narrowing tools, and adding container or VM isolation.
  - Sources: [SPEC.md §15.5](https://github.com/openai/symphony/blob/main/SPEC.md), [elixir/README](https://github.com/openai/symphony/blob/main/elixir/README.md)
- **Isolation and audit:**
  - "Mandating strong sandbox controls beyond what the coding agent and host OS provide" is a non-goal.
  - Workspace hooks "are fully trusted configuration".
  - The audit trail is structured logs only.
  - Source: [SPEC.md](https://github.com/openai/symphony/blob/main/SPEC.md)

#### Deployment, pricing, China reachability
- **Where it runs:** on a machine the team controls. Self-contained Burrito binaries are built for macOS arm64/x86_64 and Linux arm64/x86_64, with no Windows build. They "still expect `codex`, `git`, and the selected tracker credentials on the target machine" — [elixir/README](https://github.com/openai/symphony/blob/main/elixir/README.md)
- **Pricing:** there is no hosted service and no price for Symphony itself. Costs are Codex usage plus the tracker subscription (inference).
- **China reachability:** not tested. A run needs the tracker API (for example the default `https://api.linear.app/graphql`) and Codex's model backend — [elixir/README](https://github.com/openai/symphony/blob/main/elixir/README.md)

#### Integrations
- **Trackers:** Linear, GitHub Issues, Jira Cloud, Asana and GitLab.
- **GitHub PR flow:** handled through repo skills (`commit`, `push`, `pull`, `land`) that use the `gh` CLI.
- **Not supported:** no Slack or Feishu integration.
- Sources: [elixir/README](https://github.com/openai/symphony/blob/main/elixir/README.md), [elixir/WORKFLOW.md](https://github.com/openai/symphony/blob/main/elixir/WORKFLOW.md)

#### Documented limitations
- "Symphony is a low-key engineering preview for testing in trusted environments" — [README](https://github.com/openai/symphony/blob/main/README.md)
- "Symphony Elixir is prototype software intended for evaluation only and is presented as-is. We recommend implementing your own hardened version based on `SPEC.md`." — [elixir/README](https://github.com/openai/symphony/blob/main/elixir/README.md)
- Blocked state is held in memory only. The sample workflow depends on non-standard Linear states. Raw tracker tools are not scoped to the project — [elixir/README](https://github.com/openai/symphony/blob/main/elixir/README.md)
- A known third-party port exists: "baton" uses GitHub Issues, worktrees and Claude Code. It is "Inspired by OpenAI's Symphony spec" and defaults to `acceptEdits` [prior notes] — [baton README](https://github.com/mraza007/baton)

### Inferences
- Symphony is the reverse of Longtable. Humans manage tickets, and autonomous Codex runs do the work in workspaces Symphony owns. Interactive sessions are explicitly what it wants to remove ("Engineers do not need to supervise Codex").
- A 2–5 person team could each run their own Symphony with `assignee: me`. The shared board would then be Linear, GitHub or Jira, not Symphony. Symphony adds no help-request, presence or cross-person coordination beyond what the tracker already has.
- On security posture, the reference is much more permissive than Longtable:
  - Approval prompts are rejected or never asked.
  - Ticket text flows straight into the prompt.
  - "Human Review → Merging" is a tracker state change that anyone with tracker permissions can make. There is no passkey or step-up confirmation.
- The activity slowdown (+505 stars in September 2026, 18 days without commits, three tags in total) and the "build your own from SPEC.md" stance make Symphony a reference pattern rather than a maintained product.

### Gaps
- **Merge permissions:** who may move an issue to `Merging` depends on tracker permissions; Symphony itself does not document this.
- **Model-provider reachability from mainland China and Hong Kong:** not checked, because openai.com was blocked here.
- **Issue tracking:** whether the 0 open issues means GitHub Issues is disabled was not confirmed (api.github.com blocked).
- **Unread document:** the "harness engineering" article (openai.com) was blocked.

## Q3. qm (yc-software/qm): what it is, `enforce` screening/quarantine, "approvals must come from outside the agent", multi-human features, hosting

### Takeaway
qm is Y Combinator's MIT-licensed "multiplayer agent harness for work", used in Slack and on the web. It is general-purpose, not a coding-team board. An organization deploys it into its own Fly.io or AWS account, or onto a single Docker host. A server-side core then runs the agent loop (harness: Pi by default, or OpenCode, Codex or Claude Code) for each person and room, inside per-scope durable cloud sandboxes. It does not attach to laptop sessions. qm has the most explicit security model of the four:
- Strict, Auto and Dangerous postures.
- Classifier-based content screening, where `enforce` quarantines flagged content pending release approval. It is off by default.
- An always-on command policy.
- A documented rule that three powers stay out of the agent's API: admin grant changes, impersonation and command-approval decisions.

Its documentation is unusually candid about where those controls fall short.

### Cited Findings

#### Identity, licence, popularity, activity
- Owner: Y Combinator (`yc-software` org). The npm maintainers are `reganbell` and `16francej`. Licence MIT. Node 24.15+, TypeScript, Fastify, Lit — [README](https://github.com/yc-software/qm/blob/main/README.md), [npm](https://registry.npmjs.org/@yc-software%2Fqm)
- **Stars:** no exact count was obtained. On 2026-10-03 qm was below the TypeScript top-100 cutoff of 45,457 [ranking] — [10-03](https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Data/github-ranking-2026-10-03.csv). Prior notes report "5,000+ GitHub stars in its first day and #2 on Hacker News with 500+ points" at the 2026-07-31 open-sourcing [prior notes] — [Startup Fortune](https://startupfortune.com/y-combinator-open-sources-qm-the-ai-agent-harness-it-uses-to-run-itself/)
- **Releases:**
  - npm `@yc-software/qm` was created 2026-07-29T23:29Z. It has 16 versions; the latest, 0.1.14, was published 2026-10-02T01:43Z — [npm](https://registry.npmjs.org/@yc-software%2Fqm)
  - Go-proxy-visible tags run from v0.1.2 (2026-07-30) through v0.1.5 (08-17), v0.1.6–0.1.9 (09-03 to 09-05), v0.1.10–0.1.11 (09-11/12), v0.1.12 (09-18), v0.1.13 (09-27) and v0.1.14 (10-02) — [Go proxy list](https://proxy.golang.org/github.com/yc-software/qm/@v/list)
- **Last commit:** 2026-10-03T06:52:53Z — [Go proxy main.info](https://proxy.golang.org/github.com/yc-software/qm/@v/main.info)
- **Contribution model:** "We take contributions as _human-written_ text, not code". Proposals go as `.txt` or `.md` files in `adrs/`, and the maintainers implement them — [CONTRIBUTING.md](https://github.com/yc-software/qm/blob/main/CONTRIBUTING.md)
- **Readiness doubts:** a third-party review is titled "Is Quartermaster Ready for Work?" (title only; suggests "qm" = Quartermaster) [prior notes] — [wavect](https://wavect.io/blog/qm-ai-agent-harness-review/)

#### What it is and how it runs agents (server-side harness; does not attach)
- **Positioning:** "QM is designed for startups. Employees each get their own isolated workspace, and can also collaborate with the agent in channels, group messages, and projects. Each person and each room has its own scoped memory, files, keychain view, permissions, crons, web apps, and durable sandbox." — [README](https://github.com/yc-software/qm/blob/main/README.md)
- **Use cases** include "Work in an existing repository: run tests, open PRs, monitor CI, check system logs" and "Track a project in a shared channel and post updates and follow-ups" — [README](https://github.com/yc-software/qm/blob/main/README.md)
- **Execution:**
  - "Every turn runs through a central core." "Pi, OpenCode, Codex, and Claude Code all drive the same core."
  - "The agent has a small, fixed tool surface; one of those tools is `execute`, which runs commands in the scope's own isolated sandbox — its durable computer."
  - Without `DATABASE_URL`/`SESSION_STORE=postgres`, "sessions live in process memory and vanish on restart".
  - Source: [README](https://github.com/yc-software/qm/blob/main/README.md)
- **Harness auth:**
  - The default is `HARNESS=pi`.
  - Codex and Claude Code can use "Subscription-backed harness auth": `CODEX_AUTH_CREDENTIAL` and `CLAUDE_AUTH_CREDENTIAL` point at a keychain credential, and "core refreshes it centrally and hands harnesses ephemeral derived material".
  - A local `~/.codex/auth.json` is "Local-dev fallback only … Not allowed in production".
  - API keys are the alternative (Anthropic, OpenAI, OpenRouter).
  - Source: [.env.example](https://github.com/yc-software/qm/blob/main/.env.example)
- **Sandbox backends:**
  - Local Docker (`sandbox.backend: "local"` for a single host).
  - Fly ("Fly Machines for agent computers").
  - AWS.
  - Superserve ("persistent workspace … Paused sandboxes resume on use").
  - The README also links docs for "blank Modal workers".
  - Sources: [cli/README](https://github.com/yc-software/qm/blob/main/cli/README.md), [docs/superserve.md](https://github.com/yc-software/qm/blob/main/docs/superserve.md), [README](https://github.com/yc-software/qm/blob/main/README.md)
- **Swarms:**
  - "durable agent pools", spawned through the agent self-API (`POST /v1/swarm`). They are feature-flagged per person and "off by default".
  - "the requesting human can allow or deny pending approvals" for workers in the web UI.
  - "Worker sessions never inherit the root session's command or security-screen approval grants".
  - Source: [docs/swarms.md](https://github.com/yc-software/qm/blob/main/docs/swarms.md)

#### Multi-human features
- **Surfaces:** "Slack and web. The same identity and configuration carries between Slack and the web app." Rooms include "Slack channels and projects" — [README](https://github.com/yc-software/qm/blob/main/README.md)
- **Identities:**
  - Sign-in is via Slack, an email magic link from the built-in `auth` broker (Resend or SMTP), or OIDC.
  - "Principal links" fold several sign-ins into one person.
  - "Org admins manage links … the agent cannot."
  - Sources: [docs/principal-links.md](https://github.com/yc-software/qm/blob/main/docs/principal-links.md), [docs/getting-started.md](https://github.com/yc-software/qm/blob/main/docs/getting-started.md)
- **Roles:** the org admin role is set with `ADMIN_GRANTS=<email>:org_admin` — [deployment template](https://github.com/yc-software/qm/blob/main/cli/templates/deployment/deployment.md)
- **Admin control:** "Set org-level configuration, security and sharing postures. Choose which harnesses and models are available." "Skills are scope-owned and shareable by grant, with admin-gated promotion to the whole org." — [README](https://github.com/yc-software/qm/blob/main/README.md)
- **Spend and rate limits:** `BUDGET_USD_PER_WINDOW=25`, `ORG_BUDGET_USD_PER_WINDOW=100` over `BUDGET_WINDOW_MS=86400000` (24h), and `RATE_LIMIT_PER_WINDOW=60` — [.env.example](https://github.com/yc-software/qm/blob/main/.env.example)
- **Background work:** "Crons, watches, and inbound webhooks work while you're away." — [README](https://github.com/yc-software/qm/blob/main/README.md)
- **Missing primitives:** no task, assignee, claim, blocker or help-request objects are documented. The closest item is the "Track a project in a shared channel" use case — [README](https://github.com/yc-software/qm/blob/main/README.md)
- **Share links:** "session-share links are read-only snapshots" [prior notes, competitor-authored] — [Yep Anywhere multiplayer review](https://github.com/kzahel/yepanywhere/blob/main/docs/competitive/multiplayer-ai.md)

#### Human-in-the-loop and security
- **Postures.** An org picks one, and "narrower scopes can only tighten" it:
  - "**Strict** — every harness tool call pauses for human approval, except the two no-effect turn enders."
  - "**Auto** (default) — blocks private-network access."
  - "**Dangerous** — no tool approval gates, and content screening only observes."
  - Source: [README](https://github.com/yc-software/qm/blob/main/README.md)
- **Content screening:**
  - `securityScreen.mode` is "`off` (default), `observe`, or `enforce`". The classifier is a built-in `model` or an external `proxy`.
  - "When on, it classifies external content under every posture. `observe` only records verdicts in the audit log. `enforce` quarantines flagged content pending release approval, except under Dangerous, which caps screening at `observe`."
  - Source: [README](https://github.com/yc-software/qm/blob/main/README.md)
- **Screening scope:**
  - "Auto screens supported, provenance-labelled external text and supported tool results. Command and background-process output, opaque or multimodal results, raw webhook payloads … are not all covered. Classifier approval is not authorization and cannot guarantee prompt-injection resistance."
  - "carried skills and their bundled files must pass screening before prompt inclusion or materialization".
  - Source: [SECURITY.md](https://github.com/yc-software/qm/blob/main/SECURITY.md)
- **Command policy:** "The predeclared command policy — approval rules and hard denials for things like recursive deletes or destructive SQL — applies in every posture, Dangerous included." — [README](https://github.com/yc-software/qm/blob/main/README.md). It is also "bypassable … a speed bump against mistakes and injection, not a sandbox boundary" — [SECURITY.md](https://github.com/yc-software/qm/blob/main/SECURITY.md)
- **Decisions kept outside the agent ("walls, not gaps"):**
  - "Three actions are intentionally excluded from the agent self-API, even though the web portal offers them": admin grant changes, impersonation, and command-approval decisions.
  - "Approving a gated command is a human judgment made on the approver's own turn. An agent-reachable approval route would collapse the human-in-the-loop gate into a single model decision."
  - "each is a decision that authorizes _future_ agent behavior, so the decision itself must come from outside the agent."
  - Source: [SECURITY.md](https://github.com/yc-software/qm/blob/main/SECURITY.md)
- **What an approval means:** "An approval means a human accepted the displayed action under the information available at that time, not that the resulting behavior is safe." — [SECURITY.md](https://github.com/yc-software/qm/blob/main/SECURITY.md)
- **Trust boundaries:**
  - "The agent and software it runs in a sandbox are not trusted to make authorization decisions."
  - "Surface and connector inputs are untrusted data. Authentication proves the source … it does not make the content safe."
  - Source: [SECURITY.md](https://github.com/yc-software/qm/blob/main/SECURITY.md)
- **Provenance in swarms:** "Auto screening receives host-verified swarm delegation provenance … Delegation does not authorize credential disclosure, permission changes, or overriding higher-priority instructions; those remain screened." — [docs/swarms.md](https://github.com/yc-software/qm/blob/main/docs/swarms.md)
- **Sharing posture:** "Isolated" by default. "Open" lets a speaker's opted-in personal resources be read in opted-in shared rooms. Included memories carry "source-scope labels" — [SECURITY.md](https://github.com/yc-software/qm/blob/main/SECURITY.md)
- **Secrets:**
  - Grants carry an "owner, audience, once-or-standing mode, expiry, revocation, and audit".
  - "Sandbox credentials are plaintext while in use."
  - "Credential purposes are not enforced authorization."
  - Source: [SECURITY.md](https://github.com/yc-software/qm/blob/main/SECURITY.md)
- **Audit and admin access:**
  - "records security-relevant actions".
  - "Admins can read sensitive content … audited, not separately consent-gated".
  - "request capture is on by default".
  - Source: [SECURITY.md](https://github.com/yc-software/qm/blob/main/SECURITY.md)
- **Supply chain:** a 7-day npm `min-release-age` cooldown — [SECURITY.md](https://github.com/yc-software/qm/blob/main/SECURITY.md)

#### Deployment, pricing, China reachability
- **Install:** `qm init . --org <slug> --target <fly-or-aws>` (the CLI also accepts `docker`). "Each deployment runs in the operator's own cloud account." The deploy skill "confirms the operator-owned account and billing before mutation" — [README](https://github.com/yc-software/qm/blob/main/README.md), [docs/getting-started.md](https://github.com/yc-software/qm/blob/main/docs/getting-started.md), [cli/README](https://github.com/yc-software/qm/blob/main/cli/README.md)
- **Region:** the deployment workflow asks for the "region and provider account or organization" — [deployment template](https://github.com/yc-software/qm/blob/main/cli/templates/deployment/deployment.md)
- **Hosted option:** "a 3rd-party hosted version of QM" at agent37.com/qm; its price was not obtained — [README](https://github.com/yc-software/qm/blob/main/README.md)
- **Pricing:** qm is free (MIT). Costs are cloud plus models.
- **China reachability:** not tested.

#### Integrations
- **Slack:** a first-class surface (Bolt plugin) — [README](https://github.com/yc-software/qm/blob/main/README.md)
- **Connectors:** configured on an Admin "connectors" page. Slack identity linking verifies the user's "Composio account ownership" — [deployment template](https://github.com/yc-software/qm/blob/main/cli/templates/deployment/deployment.md), [docs/principal-links.md](https://github.com/yc-software/qm/blob/main/docs/principal-links.md)
- **GitHub:** used through repo work ("open PRs, monitor CI").
- **Not documented:** connector lists for Linear, Jira and Feishu were not found.

#### Documented limitations (selection)
These come from SECURITY.md's "Known limitations" list — [SECURITY.md](https://github.com/yc-software/qm/blob/main/SECURITY.md):
- "early, experimental software"
- "not a hardened public or multi-tenant service boundary"
- "Browser actions sit outside some core gates"
- "Audience-floor filtering has known gaps"
- "Egress enforcement is conditional"
- "File artifacts have no expiry"
- "Published-app capability links are bearer authorization"
- portal sessions default to 8h and "cannot revoke an already copied session token"
- the OpenCode adapter "supplies its provider key to the supervised sidecar"
- "secret scanning on file write is not implemented"

### Inferences
- **Closest precedent for Longtable's commitment rule:** qm is the closest documented precedent for "agents' tokens cannot perform commitment actions; a person confirms". qm keeps approvals and grants in the portal on a human's own turn. Longtable goes further by requiring a passkey and covering team commitments (accept, claim someone else's task, forward), not only tool approvals.
- **qm's quarantine and Longtable's accept-gate are complementary:**
  - qm's quarantine is classifier-driven, off by default, and scoped to external or connector content.
  - Longtable's accept-gate is deterministic (every teammate-authored text needs the recipient's accept) and does not depend on a classifier.
  - Each covers a gap the other has.
- **Operating model differs from Longtable:** qm replaces the person's local Claude Code or Codex with a server-side agent in a cloud sandbox, reached from Slack or the web. It needs an org-run cloud deployment with Postgres, sign-in and email or Slack. For a 2–5 person China+US coding team that is heavy operations work, and it is Slack-centric.

### Gaps
- **Stars:** the exact star count and its growth since launch are unknown (api.github.com blocked).
- **Slack approvals:** whether Strict-mode approvals can be granted from Slack, or only in the web portal, was not confirmed.
- **Connectors:** the connector catalogue (GitHub, Linear, Jira) was not found. `docs/connectors.md` and plugin READMEs returned 404.
- **Third-party hosting:** agent37.com pricing and regions are unknown.

## Q4. AAMP (larksuite/aamp): message types, transport, implementers, trust/provenance, mapping to assign/claim/help/done

### Takeaway
AAMP (Agent Asynchronous Messaging Protocol, v1.1, spec dated 2026-05-22) is an MIT-licensed, email-native task protocol. It is published in the `larksuite` GitHub org and was announced as part of Feishu Project's 2026-04-23 "human + Agent" push.
- **Transport:** SMTP for delivery, JMAP for sync and push, and `X-AAMP-*` headers for semantics.
- **Intents:** `task.dispatch`, `task.ack`, `task.help_needed`, `task.result` (`completed` or `rejected`), `task.cancel`, `task.stream.opened`, plus pairing (`pair.request`/`pair.respond`) and capability cards.
- **How agents connect:** local bridges spawn a fresh headless agent run per dispatched task (Claude via ACP or `claude -p`, Codex via codex-acp or `codex exec`, Gemini, OpenClaw and others). Feishu and WeChat bot bridges also exist.
- **Trust model:** sender-level only. There is a receiver-side sender allowlist, optional exact-match dispatch-context rules, one-time pairing codes, and DKIM-based sender trust in the reference deployment. There are no per-message trust or provenance labels and no human accept step before the body reaches the agent.
- **Activity:** the repo and all packages have been quiet since 2026-07-28/29.

### Cited Findings

#### Identity, licence, popularity, activity
- **Repo and licence:** `larksuite/aamp`, MIT. SDKs exist for Node.js, Python and Go — [README](https://github.com/larksuite/aamp/blob/main/README.md)
- **Spec status:** "Specification - 22 May 2026 … This version reflects the AAMP 1.1 implementation baseline." — [AAMP_CORE_SPECIFICATION.md](https://github.com/larksuite/aamp/blob/main/docs/AAMP_CORE_SPECIFICATION.md)
- **Stars:** 121 [prior notes; exact date not recorded] — [GitHub larksuite/aamp](https://github.com/larksuite/aamp). AAMP is not in any ranking.
- **Release dates [registry]:**

  | Package | First published | Versions | Latest |
  |---|---|---|---|
  | `aamp-sdk` (npm) | 2026-03-25 | 25 | 0.1.30, 2026-07-28 |
  | `aamp-acp-bridge` | 2026-03-25 | 31 | 0.1.34, 2026-07-28 |
  | `aamp-openclaw-plugin` | 2026-03-25 | 41 | 0.1.50, 2026-07-28 |
  | `aamp-cli` | 2026-03-30 | 19 | 0.1.18, 2026-07-28 |
  | `aamp-feishu-bridge` | 2026-05-09 | 14 | 0.1.13, 2026-07-28 |
  | `aamp-wechat-bridge` | 2026-05-11 | 7 | 0.1.6, 2026-07-28 |
  | `aamp-cli-bridge` | 2026-05-13 | 14 | 0.1.13, 2026-07-28 |
  | `aamp-sdk` (PyPI) | 0.1.0 on 2026-04-13 | 3 | 0.1.2, 2026-07-28 |

  All npm packages have a single maintainer, `wadxm`. Sources: [npm aamp-sdk](https://registry.npmjs.org/aamp-sdk), [npm aamp-acp-bridge](https://registry.npmjs.org/aamp-acp-bridge), [npm aamp-cli](https://registry.npmjs.org/aamp-cli), [npm aamp-cli-bridge](https://registry.npmjs.org/aamp-cli-bridge), [npm aamp-feishu-bridge](https://registry.npmjs.org/aamp-feishu-bridge), [npm aamp-wechat-bridge](https://registry.npmjs.org/aamp-wechat-bridge), [npm aamp-openclaw-plugin](https://registry.npmjs.org/aamp-openclaw-plugin), [PyPI aamp-sdk](https://pypi.org/pypi/aamp-sdk/json)
- **Last commit and tags:** last commit 2026-07-29T02:59:33Z, with no tags — [Go proxy main.info](https://proxy.golang.org/github.com/larksuite/aamp/@v/main.info)
- **Go SDK import path:** the README's Go import path `github.com/aamp/aamp-core/packages/sdks/go/aamp` does not resolve on the Go proxy ("not found") — [README](https://github.com/larksuite/aamp/blob/main/README.md), [Go proxy](https://proxy.golang.org/github.com/aamp/aamp-core/@latest)
- **Announcement:** Feishu Project (飞书项目, international name Meegle) Ecosystem Day, Shanghai, 2026-04-23. It released MCP capabilities, an open-sourced Feishu Project CLI and "the open AAMP protocol", and positioned the product as a "human + Agent collaborative action system" [prior notes; news snippets] — [QbitAI](https://www.qbitai.com/2026/04/406026.html), [InfoQ CN](https://www.infoq.cn/article/ub0bHyfIRpbO61I876k2)

#### Message types, transport and state
- **Intents:** `task.dispatch`, `task.cancel`, `task.ack`, `task.help_needed`, `task.result`, `task.stream.opened`, `pair.request`, `pair.respond`, `card.query`, `card.response` — [README](https://github.com/larksuite/aamp/blob/main/README.md)
- **Semantics** — [spec §6](https://github.com/larksuite/aamp/blob/main/docs/AAMP_CORE_SPECIFICATION.md):
  - `task.dispatch` "creates a new task or adds clarifying input to an existing task thread".
  - `task.ack` "confirms that an executor has received and admitted the task … Acknowledgement does not imply completion … either automatically or explicitly".
  - `task.help_needed` means "the executor cannot safely continue without additional information, approval, or policy clarification", with optional `X-AAMP-SuggestedOptions`.
  - `task.result` is "the authoritative terminal response" with `X-AAMP-Status` `completed` or `rejected`.
  - `task.cancel` "withdraws a previously dispatched task".
- **Headers:**
  - Required on every message: `X-AAMP-Version`, `X-AAMP-Intent`, `X-AAMP-TaskId`.
  - Optional: `Priority` (urgent/high/normal), `Expires-At`, `Session-Key`, `Dispatch-Context`, `ParentTaskId`, `StructuredResult`, `ErrorMsg`, `Card-Summary`.
  - Source: [spec §5](https://github.com/larksuite/aamp/blob/main/docs/AAMP_CORE_SPECIFICATION.md)
- **Local states:** local projections "include pending, running, help_needed, cancelled, expired, or failed", but these "are not … additional wire-level intents" — [spec §8.3](https://github.com/larksuite/aamp/blob/main/docs/AAMP_CORE_SPECIFICATION.md)
- **Streaming (optional):** SSE events `text.delta`, `todo`, `tool_call`, `artifact` and `done`. "The control plane is authoritative. The optional stream does not replace the final `task.result`." — [spec §3, §9](https://github.com/larksuite/aamp/blob/main/docs/AAMP_CORE_SPECIFICATION.md)
- **Transport:**
  - "`SMTP` for durable message delivery, `JMAP` for mailbox sync, push, and attachment retrieval".
  - Discovery at `/.well-known/aamp`.
  - "It does not require a custom mail server". Reference deployments "commonly use a JMAP-capable server such as Stalwart".
  - Examples use `meshmail.ai` as the host.
  - The stated rationale: a workflow product needs to reach "a local or sandboxed agent runtime [that] cannot expose a public webhook".
  - Source: [README](https://github.com/larksuite/aamp/blob/main/README.md)
- **Human participation:** humans answer `help_needed` by replying in the thread. The diagram shows "Human / Policy Owner → reply in thread" — [README](https://github.com/larksuite/aamp/blob/main/README.md)

#### Who implements it (implementers and agents)
- **Dispatchers named in docs:**
  - "Meego / Feishu Project" (`meego@meshmail.ai` and `feishu-project@meshmail.ai`).
  - "Base / Lark Base" (`lark-base@meshmail.ai`).
  - "GitHub" (`github@meshmail.ai`).
  - A config example also allows `meegle-bot@meshmail.ai`.
  - Sources: [docs/AGENT_SETUP.md](https://github.com/larksuite/aamp/blob/main/docs/AGENT_SETUP.md), [aamp-cli-bridge README](https://github.com/larksuite/aamp/blob/main/packages/aamp-cli-bridge/README.md)
- **ACP bridge:** "If you already have an ACP-compatible agent on your machine, such as `claude`, `codex`, `gemini`, `cursor`, `copilot`, `openclaw`" — [README](https://github.com/larksuite/aamp/blob/main/README.md)
- **CLI bridge** has built-in profiles `claude`, `codex`, `coco`, `gemini` and `codem`:
  - claude: `claude -p "{{prompt}}" --resume "{{sessionKey}}"`
  - codex: `codex exec --session-id "{{sessionKey}}" --skip-git-repo-check "{{prompt}}"`
  - coco and codem run with `--yolo`.
  - Sources: [docs/AGENT_SETUP.md](https://github.com/larksuite/aamp/blob/main/docs/AGENT_SETUP.md), [aamp-cli-bridge README](https://github.com/larksuite/aamp/blob/main/packages/aamp-cli-bridge/README.md)
- **CLI bridge runtime contract:** "For each accepted `task.dispatch`, the bridge … builds a task prompt from AAMP headers, body, and attachments … starts the CLI process … sends `task.result`".
  - Output that starts with `HELP:` becomes `task.help_needed`.
  - `FILE:/abs/path` lines attach files.
  - Source: [aamp-cli-bridge README](https://github.com/larksuite/aamp/blob/main/packages/aamp-cli-bridge/README.md)
- **The bridge must be running:** "Without a live bridge, the mailbox exists but the agent cannot consume `pair.request` or `task.dispatch`" — [docs/AGENT_SETUP.md](https://github.com/larksuite/aamp/blob/main/docs/AGENT_SETUP.md)
- **IM bridges:**
  - The Feishu bridge "forwards Feishu direct messages or `@Bot` group messages to a target AAMP agent". It pairs using `dispatchContextRules={"source":["feishu"]}`.
  - The WeChat bridge forwards direct-message turns after "terminal QR scan".
  - Sources: [README](https://github.com/larksuite/aamp/blob/main/README.md), [aamp-feishu-bridge README](https://github.com/larksuite/aamp/blob/main/packages/aamp-feishu-bridge/README.md)
- **AAMP skill:** an agent skill (`skills/aamp`) lets a running agent use `aamp-cli` to "listen for incoming AAMP mail … dispatch a task, or reply with task.result / task.help_needed". It advises "prefer `listen` in a long-lived terminal session" — [skills/aamp/SKILL.md](https://github.com/larksuite/aamp/blob/main/skills/aamp/SKILL.md)

#### Trust, provenance and security
- **Sender policy:**
  - It is "A receiver-local authorization rule that decides which senders may dispatch work, optionally scoped by dispatch-context rules".
  - "omitted policies do not authorize anyone by default".
  - Rules can require exact-match `X-AAMP-Dispatch-Context` values (e.g. `project_key`, `user_key`).
  - Sources: [spec §2](https://github.com/larksuite/aamp/blob/main/docs/AAMP_CORE_SPECIFICATION.md), [aamp-cli-bridge README](https://github.com/larksuite/aamp/blob/main/packages/aamp-cli-bridge/README.md)
- **Dispatch context is not authentication:** "Dispatch context is not identity. A receiver MUST NOT rely solely on `X-AAMP-Dispatch-Context` for authenticity or authorization." — [spec §10](https://github.com/larksuite/aamp/blob/main/docs/AAMP_CORE_SPECIFICATION.md)
- **Pairing codes:** six random bytes, five-minute TTL, one-time use. "`pair.request` is the only intent that may bypass normal sender policy" — [README](https://github.com/larksuite/aamp/blob/main/README.md)
- **Sender trust:** "In the current reference deployment, external sender trust is grounded in successful DKIM verification at the mail transport layer." — [spec §10](https://github.com/larksuite/aamp/blob/main/docs/AAMP_CORE_SPECIFICATION.md)
- **Mailbox auth:** HTTP Basic, where the token is "equivalent to the base64 encoding of `email:smtpPassword`" — [spec §7.1.2](https://github.com/larksuite/aamp/blob/main/docs/AAMP_CORE_SPECIFICATION.md)
- **Credential storage:** `~/.aamp/<bridge>/credentials/` — [README](https://github.com/larksuite/aamp/blob/main/README.md)
- **Product senders are trusted wholesale:** the agent-facing setup doc says to "Tell the user that all requests from the named product are approved" when adding the Feishu Project, Base or GitHub senders — [docs/AGENT_SETUP.md](https://github.com/larksuite/aamp/blob/main/docs/AGENT_SETUP.md)
- **Prompt injection:**
  - The spec's Security Considerations cover transport TLS, dispatch context, pairing codes, DKIM and constrained registered-command nodes ("SHOULD avoid arbitrary shell evaluation").
  - There is no section on prompt injection, content trust labels or human acceptance of message bodies.
  - Privacy guidance is limited to retention, access control and encryption.
  - Source: [spec §10–11](https://github.com/larksuite/aamp/blob/main/docs/AAMP_CORE_SPECIFICATION.md)

#### Deployment, pricing, China reachability
- **Hosting options:** the hosted `meshmail.ai`, or any standards-compliant JMAP-capable mail server (self-host, e.g. Stalwart) — [README](https://github.com/larksuite/aamp/blob/main/README.md), [README.zh-CN](https://github.com/larksuite/aamp/blob/main/README.zh-CN.md)
- **Unverified here:** meshmail.ai was unreachable from this sandbox, so its pricing, operator and region could not be checked.
- **China reachability:** not tested. A Chinese README, a WeChat bridge and a Feishu bridge are provided — [README.zh-CN](https://github.com/larksuite/aamp/blob/main/README.zh-CN.md), [README](https://github.com/larksuite/aamp/blob/main/README.md)

### Inferences
- **Mapping to Longtable verbs:**

  | Longtable | AAMP | Notes |
  |---|---|---|
  | assign | `task.dispatch` to an agent mailbox | |
  | claim / accept | `task.ack` | Executor-side, usually automatic. There is no "claim someone else's task" and no human acceptance. |
  | ask-for-help / blocker | `task.help_needed` + `X-AAMP-SuggestedOptions` | A human answers by replying in the thread (a follow-up `task.dispatch`). |
  | done | `task.result completed` | `rejected` = declined or failed. |
  | withdraw | `task.cancel` | |
  | subtasks | `ParentTaskId` | |
  | live progress | stream `todo` / `tool_call` events | |

- **Gaps in the AAMP vocabulary:**
  - comments by other humans
  - multiple assignees
  - a shared board view
  - a "who is stuck / who is needed" roll-up
  - forwarding with consent
- **Tasks are addressed to agent mailboxes, not people:** humans appear as dispatchers or as answerers of `help_needed`.
- **Execution is headless:** each dispatch becomes a fresh headless run (`claude -p`, `codex exec`, or an ACP session) on the person's machine, kept alive by a bridge daemon. It is not injected into the interactive session the person is driving. The AAMP skill plus `aamp-cli listen` could let an interactive session take part, but that is not a hooks-style integration.
- **Trust is coarser than Longtable's gate:** trust is decided per sender (or per product such as Feishu Project), not per message. With the Feishu bridge, anyone able to DM or @ the bot effectively reaches the agent, subject to Feishu-side permissions and the bridge's sender policy. Longtable's per-message accept gate is strictly finer.
- **Strategic value for China teams:** AAMP is the most "China-native" of the four (Feishu Project, Lark Base and WeChat bridges, plus a Chinese README). An AAMP bridge (Longtable as dispatcher or executor, mapping assign / help / done) could be a cheap interop feature for Feishu-centric teams.
- **Maturity risk:** there has been no commit for about 2 months, the spec is v1.1, there is one npm maintainer, and the Go module path is broken.

### Gaps
- **Feishu Project as dispatcher:** whether Feishu Project's production UI actually dispatches to `meego@meshmail.ai` / `feishu-project@meshmail.ai`, and which work-item fields map to headers, was not verified. Only the AAMP docs name these senders.
- **meshmail.ai:** its operator (ByteDance or a third party), pricing, data residency and reachability from mainland China are unknown (blocked).
- **Permissions on headless runs:** the claude CLI profile passes no permission flags. How headless `claude -p` runs behave on tool-permission prompts in this bridge (deny, or fail) was not verified.
- **Stars:** the current count was not re-verified, because api.github.com was blocked.

## Q5. Adoption by a 2–5 person China+US team whose members each run Claude Code or Codex locally, and where Longtable is clearly weaker or stronger

### Takeaway
None of the four attaches to the interactive Claude Code or Codex sessions people already run. Each spawns or hosts its own agent runs:
- **Buzz:** ACP subprocesses on API keys.
- **Symphony:** Codex app-server per ticket.
- **qm:** a cloud-hosted harness per scope.
- **AAMP:** a headless run per emailed task.

Adopting any of them means changing where work happens, not just adding a board:
- **Buzz:** replace the team chat.
- **Symphony:** move to Linear, GitHub or Jira tickets plus autonomous Codex, and drop Claude Code.
- **qm:** deploy an org cloud service and work through Slack or the web.
- **AAMP:** run a bridge daemon and route tasks by email or Feishu.

Longtable is clearly stronger on "sits beside your existing sessions", per-message injection gating, passkey-confirmed commitments, and person-to-person blockers and help. It is clearly weaker on autonomy and automation, tracker integration, self-host and open-protocol story, and brand and momentum.

### Cited Findings
- **Buzz:**
  - The harness "spawns AI agent subprocesses" and answers @mentions — [buzz-acp README](https://github.com/block/buzz/blob/main/crates/buzz-acp/README.md)
  - Codex needs "an OpenAI API key, not a ChatGPT subscription" — [buzz-acp README](https://github.com/block/buzz/blob/main/crates/buzz-acp/README.md)
  - Approval gates and issues are not shipped — [ARCHITECTURE.md](https://github.com/block/buzz/blob/main/ARCHITECTURE.md), [VISION_PROJECTS.md](https://github.com/block/buzz/blob/main/VISION_PROJECTS.md)
- **Symphony:**
  - It requires a "Coding-agent executable that supports the targeted Codex app-server mode" and a tracker (Linear, GitHub Issues, Jira Cloud, Asana or GitLab) — [SPEC.md](https://github.com/openai/symphony/blob/main/SPEC.md), [elixir/README](https://github.com/openai/symphony/blob/main/elixir/README.md)
  - Recommended route: "We recommend implementing your own hardened version" — [elixir/README](https://github.com/openai/symphony/blob/main/elixir/README.md)
- **qm:**
  - It is deployed "in the operator's own cloud account" (Fly or AWS).
  - Work happens "In Slack and on the web", with commands in "the scope's own isolated sandbox".
  - Source: [README](https://github.com/yc-software/qm/blob/main/README.md)
- **AAMP:**
  - Bridges start "the CLI process" per accepted `task.dispatch` — [aamp-cli-bridge README](https://github.com/larksuite/aamp/blob/main/packages/aamp-cli-bridge/README.md)
  - A live bridge is required — [docs/AGENT_SETUP.md](https://github.com/larksuite/aamp/blob/main/docs/AGENT_SETUP.md)
- **Hooks or MCP-in-your-own-session reporting:** none of the four documents it, in any of the documents fetched above. The nearest options are:
  - Buzz's `buzz-cli` ("designed for LLM tool calls") — [README](https://github.com/block/buzz/blob/main/README.md)
  - AAMP's agent skill around `aamp-cli` — [SKILL.md](https://github.com/larksuite/aamp/blob/main/skills/aamp/SKILL.md)
  - qm's agent self-API, which is for its own hosted agents — [docs/swarms.md](https://github.com/yc-software/qm/blob/main/docs/swarms.md)

### Inferences

#### Per product: ease of adoption and required changes for the target team
- **Buzz:** medium-to-hard.
  - Self-host a relay (Docker Compose, or Railway) and install the desktop app everywhere.
  - Move team chat from WeChat, Feishu or Slack into Buzz.
  - Mint a keypair per agent, then run `buzz-acp` or desktop managed agents with Anthropic or OpenAI API keys.
  - Agents work when @mentioned, separately from each person's interactive session.
  - No task board, assignment or approval flow is shipped yet.
  - Best fit: a US team that wants agents inside chat and owns its infrastructure.
- **Symphony:** medium for a Codex-only team that already uses Linear, GitHub Issues or Jira; not viable for Claude Code users without a third-party port.
  - Write `WORKFLOW.md` and add custom tracker states.
  - Each person runs a daemon (optionally `assignee: me`).
  - Accept autonomous runs in Symphony-managed workspaces, with permissive approval settings in the sample.
  - Work shifts from pairing with an agent to reviewing PRs from tickets.
- **qm:** hard for this team.
  - It needs one org-level cloud deployment (Fly or AWS, Postgres, sign-in, optionally Slack) and an admin.
  - People do their agent work in qm's hosted sandboxes through Slack or the web, not in their local CLI.
  - It is general-purpose, with no coding-task board.
  - Its strengths are security postures and per-person isolation.
- **AAMP:** easy to try, narrow in scope.
  - Each person runs `npx aamp-acp-bridge init/start` on their machine, gets a mailbox, and pairs senders.
  - Tasks then arrive by email, from Feishu Project, or from Feishu or WeChat bots, and run headless.
  - There is no board, shared view or human workflow. It is a pipe, not a product.
  - Most attractive to Feishu or Feishu-Project-centric Chinese teams.

#### Feature matrix (synthesised from the cited findings in Q1–Q4; Longtable column from the brief)

| Dimension | Buzz | Symphony | qm | AAMP | Longtable (brief) |
|---|---|---|---|---|---|
| Who runs the agent | Buzz harness or desktop spawns ACP agents | Symphony spawns Codex app-server per issue | qm core plus cloud sandbox per scope | Local bridge spawns headless run per task | Never; attaches to user's own sessions |
| Agents | Goose, Codex, Claude Code, Buzz Agent, others via ACP | Codex only | Pi (default), OpenCode, Codex, Claude Code | Claude, Codex, Gemini, OpenClaw, others via ACP or CLI | Claude Code, Codex |
| Subscription vs API key | API keys (Codex: not ChatGPT sub) | Codex CLI auth | Either (keychain credential) | Whatever local CLI uses | Whatever user uses |
| Task board, assign, claim | No (issues designed) | Via external tracker | No | dispatch / ack only | Yes |
| Blocker or help request | No | Tracker blocks + "blocked" in memory | No | `task.help_needed` | Yes ("who is stuck / who is needed") |
| Review or approval gate | Signed approvals; workflow gates not wired | Human Review → Merging tracker states | Strict posture, command approvals | `help_needed` "approval" | Passkey confirm for commitments |
| Agent cannot self-approve | Not documented (approvals are token-based via `buzz workflows approve`; gates not wired); harness control commands are owner-only | Not addressed (auto-approve or reject) | Explicit: approvals, grants, impersonation portal-only | n/a | Yes (agent tokens barred) |
| Injection control | Per-author allowlist gate | None (filter eligible issues) | Classifier screening + quarantine (default off) | Per-sender policy + DKIM | Per-message accept gate |
| Audit | Signed events + hash chain | Logs | Audit records | Mail thread | (not specified) |
| Notifications | In-app; push planned | Tracker's own | Slack and web | Email, Feishu or WeChat bridges | Email, WeChat |
| Hosting | Self-host or Railway | Local or self-host | Operator cloud (Fly, AWS, Docker); 3rd-party host | meshmail.ai or self-host mail | HK-hosted service |
| Licence / price | Apache-2.0, free | Apache-2.0, free | MIT, free | MIT, free | (n/a) |
| Activity, 2026-10-03 | Very active (LC 10-03; 35.4k stars) | Slowing (LC 09-15; 27.5k) | Active (LC 10-03; 0.1.14) | Quiet (LC 07-29; ~121 stars) | — |

#### Where Longtable is clearly stronger (inferred from absence in the docs reviewed)
- It is the only option that leaves each person's own interactive Claude Code or Codex session in place. It adds hooks (SessionStart summary; PostToolUse/Stop progress and commit reports) and MCP, instead of replacing the session with a spawned or hosted agent.
- It supports mixed Claude Code and Codex teams with no API-key double billing. Symphony is Codex-only, and Buzz's Codex path requires an API key.
- Its per-message "accept before it reaches my agent" gate is deterministic. The others offer per-author (Buzz), per-sender (AAMP) or classifier-based screening that is off by default (qm).
- Passkey-confirmed commitment actions go beyond qm's "decisions must come from outside the agent". No product among the four uses WebAuthn step-up confirmation.
- First-class person-to-person blockers, "who is needed" and ask-for-help appear on a shared board. AAMP's `help_needed` is agent-to-dispatcher only, and Symphony's "blocked" state is in-memory and per run.
- China+US delivery (HK server, WeChat and email notifications) is designed for this team shape. Buzz, Symphony and qm are US-tooling-centric (Slack, Linear, Fly or AWS); only AAMP addresses Feishu and WeChat.

#### Where Longtable is clearly weaker
- **No autonomous execution:** no ticket-to-PR pipeline (Symphony), no crons, webhooks or swarms (qm), and no workflow engine (Buzz).
- **No tracker integration:** no native Linear, GitHub Issues or Jira integration. Symphony has five tracker adapters.
- **No self-host or open-protocol story:** Buzz, qm and Symphony are all self-hostable open source, and AAMP is an open protocol with a ByteDance-org imprimatur. Longtable is a hosted service.
- **Weaker audit and identity:** Buzz's signed events, NIP-42/98 auth and hash-chain audit, and qm's documented threat model, set a high bar for security documentation.
- **Brand and momentum:** Block, OpenAI and YC backing, with 27–35k stars for Buzz and Symphony.

### Gaps
- **No hands-on test:** none of the four was run, so behavioural claims rest on their own docs. Examples include Buzz's author gate, qm's quarantine flow and AAMP's bridge spawning.
- **China reachability:** not measured for any of them. Untested items include the Buzz relay (self-hosted, so it depends on placement), Symphony's dependencies (Codex model backend, Linear), qm's hosts (Fly or AWS regions, Slack) and meshmail.ai.
- **Hosted pricing:** no pricing exists or was found for any hosted variant (Railway costs for a Buzz relay, agent37.com for qm, meshmail.ai for AAMP).
